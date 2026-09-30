"""Conservative random-deck checks from the supplied rules and site restrictions."""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).parent / 'data'


def available_bakugan(entry, attribute, restrictions, now=None):
    """Art assets can exist for unreleased or otherwise unavailable models."""
    if entry.get('hidden') or entry.get('trap') or attribute not in entry.get('available_attributes', []):
        return False
    release = datetime.fromisoformat(restrictions['release_locked_until'])
    if entry['id'] in restrictions['release_locked_bakugan_ids'] and (now or datetime.now(timezone.utc)) < release:
        return False
    return True


def check_random_export(export, site):
    """Return issues; random decks use generic attribute Normals only."""
    restrictions = json.loads((DATA / 'site_legality.json').read_text(encoding='utf-8'))
    rules = json.loads((DATA / 'rules.json').read_text(encoding='utf-8'))['deck_constraints']
    bakugan = {item['id']: item for item in site['bakugan']}
    abilities = {item['id']: item for item in site['abilities']}
    gates = {item['id']: item for item in site['gates']}
    members, cards, gate_ids = export['bakugans'], export['abilities'], export['gates']
    issues = []
    for key, actual, expected in [('Bakugan', len(members), rules['bakugan_count']),
                                  ('Abilities', len(cards), rules['ability_count']),
                                  ('Gates', len(gate_ids), rules['gate_count'])]:
        if actual != expected:
            issues.append(f'{key}: expected {expected}, got {actual}')
    if len({(b['id'], b['attribute']) for b in members}) != len(members):
        issues.append('Duplicate Bakugan and attribute')
    if len(set(cards)) != len(cards) or len(set(gate_ids)) != len(gate_ids):
        issues.append('Duplicate card ID')
    if any(b['id'] not in bakugan for b in members) or any(c not in abilities for c in cards) or any(g not in gates for g in gate_ids):
        return issues + ['Unknown website ID']
    selected = [bakugan[b['id']] for b in members]
    if sum(bool(b['guardian']) for b in selected) > rules['max_guardian_bakugan']:
        issues.append('More than one Guardian')
    bans = set(restrictions['banned_bakugan_ids'])
    for member, entry in zip(members, selected):
        if not available_bakugan(entry, member['attribute'], restrictions):
            issues.append(f"Unavailable Bakugan: {entry['name']}")
        if member['id'] in bans:
            issues.append(f"Banned Bakugan: {entry['name']}")
        required = restrictions['guardian_required_attribute'].get(member['id'])
        if required and member['attribute'] != required:
            issues.append(f"Guardian {entry['name']} requires {required}")
    attribute_set = {b['attribute'] for b in members}
    for identifier in cards:
        ability = abilities[identifier]
        if identifier in restrictions['banned_ability_ids'] or set(ability.get('bakuganIds', [])).intersection(bans):
            issues.append(f"Banned ability: {ability['name']}")
        if ability.get('hidden') or ability['category'] != 'normal' or ability.get('bakuganIds'):
            issues.append(f"Restricted ability: {ability['name']}")
        if not attribute_set.intersection(ability.get('attributes', [])):
            issues.append(f"Unusable attribute: {ability['name']}")
        if len(attribute_set) == 1 and len(ability.get('attributes', [])) > 1:
            issues.append(f"{ability['name']} needs multiple attributes")
    selected_gates = [gates[g] for g in gate_ids]
    if any(g in restrictions['banned_gate_ids'] for g in gate_ids):
        issues.append('Banned Gate')
    if not any(g['category'] in ('attribute', 'reactor') for g in selected_gates):
        issues.append('Attribute or Reactor Gate required')
    if any(g.get('hidden') for g in selected_gates):
        issues.append('Hidden Gate')
    names = [abilities[c]['name'].casefold() for c in cards] + [g['name'].casefold() for g in selected_gates]
    if len(names) != len(set(names)):
        issues.append('Duplicate card name')
    return issues


def validate_export(export, site):
    """Check an imported website deck against documented and captured site rules."""
    if not isinstance(export, dict) or export.get('version') != 1:
        return ['Expected a version 1 website deck export.']
    members, card_ids, gate_ids = (export.get(key) for key in ('bakugans', 'abilities', 'gates'))
    if not isinstance(members, list) or not isinstance(card_ids, list) or not isinstance(gate_ids, list):
        return ['The export must contain Bakugan, Ability and Gate lists.']
    if any(not isinstance(b, dict) or not isinstance(b.get('id'), str) or not isinstance(b.get('attribute'), str) for b in members):
        return ['A Bakugan entry is malformed.']
    if any(not isinstance(x, str) for x in card_ids + gate_ids):
        return ['An Ability or Gate ID is malformed.']
    restrictions = json.loads((DATA / 'site_legality.json').read_text(encoding='utf-8'))
    rules = json.loads((DATA / 'rules.json').read_text(encoding='utf-8'))['deck_constraints']
    bakugan = {item['id']: item for item in site['bakugan']}
    abilities = {item['id']: item for item in site['abilities']}
    gates = {item['id']: item for item in site['gates']}
    issues = []
    for label, entries, count in [('Bakugan', members, rules['bakugan_count']),
                                  ('Abilities', card_ids, rules['ability_count']),
                                  ('Gates', gate_ids, rules['gate_count'])]:
        if len(entries) != count:
            issues.append(f'{label}: {len(entries)}/{count} required')
    if len({(b['id'], b['attribute']) for b in members}) != len(members):
        issues.append('Duplicate Bakugan in the same attribute')
    if len(set(card_ids)) != len(card_ids) or len(set(gate_ids)) != len(gate_ids):
        issues.append('Duplicate card ID')
    unknown = [x for x in [b['id'] for b in members] if x not in bakugan]
    unknown += [x for x in card_ids if x not in abilities]
    unknown += [x for x in gate_ids if x not in gates]
    if unknown:
        return issues + ['Unknown website IDs: ' + ', '.join(sorted(set(unknown))[:8])]
    selected_bakugan = [bakugan[b['id']] for b in members]
    selected_abilities = [abilities[c] for c in card_ids]
    selected_gates = [gates[g] for g in gate_ids]
    if sum(bool(b['guardian']) for b in selected_bakugan) > rules['max_guardian_bakugan']:
        issues.append('Only one Guardian is allowed')
    banned = set(restrictions['banned_bakugan_ids'])
    for member, entry in zip(members, selected_bakugan):
        if not available_bakugan(entry, member['attribute'], restrictions):
            issues.append(f"{entry['name']} ({member['attribute']}) is unavailable or locked")
        if entry['id'] in banned:
            issues.append(f"{entry['name']} is banned")
        required = restrictions['guardian_required_attribute'].get(entry['id'])
        if required and required != member['attribute']:
            issues.append(f"{entry['name']} requires {required.title()}")
    names = [c['name'].casefold() for c in selected_abilities + selected_gates]
    if len(names) != len(set(names)):
        issues.append('Duplicate card name')
    if sum(c['category'] == 'trap' for c in selected_abilities) > rules['max_trap_abilities']:
        issues.append('Only one Trap Ability is allowed')
    attribute_set = {b['attribute'] for b in members}
    member_ids = {b['id'] for b in members}
    for card in selected_abilities:
        if card.get('hidden') or card['id'] in restrictions['banned_ability_ids'] or set(card.get('bakuganIds', [])).intersection(banned):
            issues.append(f"{card['name']} is hidden or banned")
        if card.get('attributes') and not set(card['attributes']).issubset(attribute_set):
            issues.append(f"{card['name']} needs {', '.join(card['attributes'])} Bakugan")
        if card.get('bakuganIds') and not member_ids.intersection(card['bakuganIds']):
            issues.append(f"{card['name']} needs its Bakugan")
        if card['category'] == 'fusion' and card.get('requiredAbilityId') not in card_ids:
            issues.append(f"{card['name']} needs its Signature prerequisite")
        partner = card.get('evolvedFrom') or card.get('evolvesTo')
        if partner and partner in card_ids:
            issues.append(f"{card['name']} conflicts with its evolution pair")
    if not any(g['category'] in ('attribute', 'reactor') for g in selected_gates):
        issues.append('At least one Attribute or Reactor Gate is required')
    for gate in selected_gates:
        if gate.get('hidden') or gate['id'] in restrictions['banned_gate_ids'] or set(gate.get('bakuganIds', [])).intersection(banned):
            issues.append(f"{gate['name']} Gate is hidden or banned")
    signatures = [c for c in selected_abilities if c['category'] == 'signature']
    slots = [b['id'] for b in members]
    def assign(index, taken):
        if index == len(signatures):
            return True
        for slot, identifier in enumerate(slots):
            if slot not in taken and identifier in signatures[index].get('bakuganIds', []):
                if assign(index + 1, taken | {slot}):
                    return True
        return False
    if not assign(0, set()):
        issues.append('Signature Abilities exceed the available Bakugan slots')
    return list(dict.fromkeys(issues))
