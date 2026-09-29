"""Resolve a user-exported deck against a dated public site catalog snapshot."""
import json
from pathlib import Path
from types import SimpleNamespace

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
