"""Read-only drift report for the website's public deck-builder catalog assets."""
import json
import re
from pathlib import Path

SITE = 'https://bakuganbrawl.online'
DATA = Path(__file__).parent / 'data'


def imported_asset(source, prefix):
    match = re.search(r'(?:\./|/assets/)(' + re.escape(prefix) + r'-[A-Za-z0-9_-]+\.js)', source)
    if not match:
        raise ValueError(f'Website asset {prefix} could not be located.')
    return '/assets/' + match.group(1)


def parse_catalogs(source):
    arrays = re.findall(r'\w+=JSON\.parse\(`(\[.*?\])`\)', source, re.S)
    if len(arrays) < 3:
        raise ValueError('Website card catalog format changed.')
    return dict(zip(('bakugan', 'abilities', 'gates'), (json.loads(raw) for raw in arrays[:3])))


def parse_restrictions(guardian_js, banned_js, release_js):
    guardian = {key: value.lower() for key, value in re.findall(r'(\w+):t\.(\w+)', guardian_js)}
    match = re.search(r'new Set\(\[(.*?)\]\)', banned_js)
    release = re.search(r'u=new Set\(\[(.*?)\]\)', release_js)
    deadline = re.search(r'd=Date\.parse\(`([^`]+)`\)', release_js)
    if not guardian or not match or not release or not deadline:
        raise ValueError('Website deck restriction format changed.')
    return {'guardian_required_attribute': guardian,
            'banned_bakugan_ids': re.findall(r'`([^`]+)`', match.group(1)),
            'release_locked_bakugan_ids': re.findall(r'`([^`]+)`', release.group(1)),
            'release_locked_until': deadline.group(1)}


def compare(current, restrictions):
    saved = json.loads((DATA / 'site_catalog.json').read_text(encoding='utf-8'))
    old_rules = json.loads((DATA / 'site_legality.json').read_text(encoding='utf-8'))
    changes = []
    for kind in ('bakugan', 'abilities', 'gates'):
        old = {entry['id']: entry for entry in saved[kind]}
        new = {entry['id']: entry for entry in current[kind]}
        for identifier in sorted(new.keys() - old.keys()):
            changes.append(f'{kind}: new {identifier}')
        for identifier in sorted(old.keys() - new.keys()):
            changes.append(f'{kind}: removed {identifier}')
        fields = ('name', 'gs', 'guardian', 'hidden', 'trap') if kind == 'bakugan' else ('name', 'category', 'hidden', 'textEn', 'attributes', 'attribute', 'bakuganIds')
        for identifier in sorted(old.keys() & new.keys()):
            before, after = old[identifier], new[identifier]
            for field in fields:
                if before.get(field) != after.get(field):
                    changes.append(f'{kind}/{identifier}: {field} changed')
            if kind == 'bakugan' and before.get('available_attributes', []) != sorted(after.get('variants', after.get('attributes', {}))):
                changes.append(f'{kind}/{identifier}: available attributes changed')
    for key, value in restrictions.items():
        before = old_rules[key]
        if isinstance(value, list):
            if set(value) != set(before):
                changes.append(f'restrictions/{key}: added {sorted(set(value)-set(before))}; removed {sorted(set(before)-set(value))}')
        elif value != before:
            changes.append(f'restrictions/{key}: changed')
    return {'snapshot': saved['snapshot'], 'counts': {key: len(current[key]) for key in current}, 'changes': changes}


async def check_website(session):
    async def get(path):
        async with session.get(SITE + path, timeout=25) as response:
            response.raise_for_status()
            return await response.text()

    page = await get('/deck-builder')
    builder = await get(imported_asset(page, 'DeckBuilder'))
    manager = await get(imported_asset(builder, 'assetManager'))
    catalog = parse_catalogs(await get(imported_asset(manager, 'catalogs')))
    deck_hook = await get(imported_asset(builder, 'useDeck'))
    guardian = await get(imported_asset(deck_hook, 'guardianAttributes'))
    banned = await get(imported_asset(deck_hook, 'bannedBakugans'))
    release = await get(imported_asset(deck_hook, 'releaseEvent'))
    return compare(catalog, parse_restrictions(guardian, banned, release))
