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
