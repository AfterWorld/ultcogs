"""Resolve a user-exported deck against a dated public site catalog snapshot."""
import json
from pathlib import Path
from types import SimpleNamespace

from .deck_legality import check_random_export

SITE = 'https://bakuganbrawl.online'
DATA = Path(__file__).parent / 'data' / 'site_catalog.json'
ATTRIBUTES = {'aquos', 'pyrus', 'ventus', 'subterra', 'haos', 'darkus'}


def resolve_deck(raw):
    if len(raw) > 1_000_000:
        raise ValueError('The deck file is too large.')
    try:
        exported = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError('Attach the JSON file exported by the website.') from exc
    if not isinstance(exported, dict) or exported.get('version') != 1:
        raise ValueError('This is not a supported website deck export (version 1).')
    with DATA.open(encoding='utf-8') as stream:
        site = json.load(stream)
    lookup = {kind: {item['id']: item for item in site[kind]} for kind in ('bakugan', 'abilities', 'gates')}
    chosen = {kind: exported.get('bakugans' if kind == 'bakugan' else kind) for kind in lookup}
    if any(not isinstance(items, list) for items in chosen.values()):
        raise ValueError('The deck file is missing Bakugan, Ability, or Gate lists.')
    if [len(chosen[k]) for k in lookup] != [3, 6, 3]:
        raise ValueError('Share a complete website deck: 3 Bakugan, 6 Abilities, and 3 Gates.')
    names, images, art, roles = [], {}, {}, []
    for item in chosen['bakugan']:
        if not isinstance(item, dict) or item.get('id') not in lookup['bakugan'] or item.get('attribute') not in ATTRIBUTES:
            raise ValueError('A Bakugan or its attribute is missing from the site catalog snapshot.')
        entry = lookup['bakugan'][item['id']]
        title = f"{entry['name']} ({item['attribute'].title()})"
        names.append(title)
        roles.append('GUARDIAN' if entry['guardian'] else 'GENERIC')
        url = entry.get('art', {}).get(item['attribute'])
        if url:
            art[title] = url if url.startswith('https://') else SITE + url
    cards = {}
    for kind in ('abilities', 'gates'):
        cards[kind] = []
        for identifier in chosen[kind]:
            if not isinstance(identifier, str) or identifier not in lookup[kind]:
                raise ValueError('A card ID is missing from the site catalog snapshot. The catalog may need refreshing.')
            entry = lookup[kind][identifier]
            cards[kind].append({'name': entry['name'], 'category': entry.get('category', kind)})
            url = entry.get('image')
            if url:
                images[entry['name']] = {'url': url if url.startswith('https://') else SITE + url}
    primary = chosen['bakugan'][0]['attribute'].title()
    deck = {'attribute': primary, 'bakugan': names, 'bakugan_roles': roles, 'heading': 'WEBSITE DECK', **cards,
            'note': 'Website deck export · catalog snapshot ' + site['snapshot'] + ' · check current site rules'}
    return deck, SimpleNamespace(images=images), art


def random_site_deck(attribute=None, rng=None):
    """Build a simple mono-attribute image deck from website IDs and artwork."""
    import random
    rng = rng or random.Random()
    if attribute is not None:
        attribute = attribute.lower().strip()
        if attribute not in ATTRIBUTES:
            raise ValueError('Choose Aquos, Pyrus, Ventus, Subterra, Haos or Darkus.')
    else:
        attribute = rng.choice(sorted(ATTRIBUTES))
    with DATA.open(encoding='utf-8') as stream:
        site = json.load(stream)
    restrictions = json.loads((DATA.parent / 'site_legality.json').read_text(encoding='utf-8'))
    banned = set(restrictions['banned_bakugan_ids'])
    banned_abilities = set(restrictions['banned_ability_ids'])
    banned_gates = set(restrictions['banned_gate_ids'])
    locks = restrictions['guardian_required_attribute']
    guardians = [b for b in site['bakugan'] if b['guardian'] and b['id'] not in banned
                 and (not locks.get(b['id']) or locks[b['id']] == attribute) and b.get('art', {}).get(attribute)]
    generic = [b for b in site['bakugan'] if not b['guardian'] and b['id'] not in banned
               and b.get('art', {}).get(attribute)]
    normal = [c for c in site['abilities'] if c['category'] == 'normal' and c['id'] not in banned_abilities and not c.get('hidden')
              and not c.get('bakuganIds') and attribute in c.get('attributes', []) and c.get('image')]
    command = [g for g in site['gates'] if g['category'] == 'command' and g['id'] not in banned_gates
               and not g.get('hidden') and g.get('image')]
    attribute_gates = [g for g in site['gates'] if g['category'] in ('attribute', 'reactor')
                       and g.get('attribute') == attribute and g['id'] not in banned_gates and not g.get('hidden')]
    if not guardians or len(generic) < 2 or len(normal) < 6 or len(command) < 2 or not attribute_gates:
        raise ValueError('The website catalog has too few cards for that attribute.')
    bakugan = [rng.choice(guardians), *rng.sample(generic, 2)]
    export = {'version': 1, 'name': f'Random {attribute.title()} Deck', 'description': '',
              'bakugans': [{'id': b['id'], 'attribute': attribute} for b in bakugan],
              'abilities': [c['id'] for c in rng.sample(normal, 6)],
              'gates': [rng.choice(attribute_gates)['id'], *[g['id'] for g in rng.sample(command, 2)]]}
    issues = check_random_export(export, site)
    if issues:
        raise ValueError('Could not generate a legal deck: ' + '; '.join(issues))
    deck, catalog, art = resolve_deck(json.dumps(export).encode())
    deck['heading'] = 'RANDOM DECK'
    deck['note'] = 'Cards and artwork: Bakugan Brawl Online · catalog ' + site['snapshot']
    return deck, catalog, art, export
