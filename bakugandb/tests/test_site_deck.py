"""Website export IDs resolve against the bundled catalog snapshot."""
import importlib.util
import json
from pathlib import Path
import sys
import types

package = types.ModuleType('bakugandb')
package.__path__ = [str(Path(__file__).parents[1])]
sys.modules.setdefault('bakugandb', package)
spec = importlib.util.spec_from_file_location('bakugandb.site_deck', Path(__file__).parents[1] / 'site_deck.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_resolve_site_export():
    catalog = json.loads((Path(__file__).parents[1] / 'data' / 'site_catalog.json').read_text())
    bakugan = catalog['bakugan'][:3]
    abilities = catalog['abilities'][:6]
    gates = catalog['gates'][:3]
    exported = {'version': 1, 'name': 'Example',
                'bakugans': [{'id': b['id'], 'attribute': 'aquos'} for b in bakugan],
                'abilities': [c['id'] for c in abilities], 'gates': [c['id'] for c in gates]}
    deck, images, art = module.resolve_deck(json.dumps(exported).encode())
    assert [b['name'] + ' (Aquos)' for b in bakugan] == deck['bakugan']
    assert [c['name'] for c in abilities] == [c['name'] for c in deck['abilities']]
    assert deck['heading'] == 'WEBSITE DECK'
    assert isinstance(images.images, dict) and isinstance(art, dict)
    exported['abilities'][0] = 'unknown-site-card'
    try:
        module.resolve_deck(json.dumps(exported).encode())
    except ValueError as exc:
        assert 'catalog snapshot' in str(exc)
    else:
        raise AssertionError('Unknown website ID accepted')


def test_random_site_deck():
    import random
    from bakugandb.deck_legality import validate_export
    site = json.loads((Path(__file__).parents[1] / 'data' / 'site_catalog.json').read_text())
    abilities = {c['id']: c for c in site['abilities']}
    for attribute in module.ATTRIBUTES:
        deck, images, art, exported = module.random_site_deck(attribute, random.Random(7))
        assert len(deck['bakugan']) == 3 and len(deck['abilities']) == 6 and len(deck['gates']) == 3
        assert deck['bakugan_roles'] == ['GUARDIAN', 'GENERIC', 'GENERIC']
        assert len({c['name'] for c in deck['abilities'] + deck['gates']}) == 9
        assert all(name in art for name in deck['bakugan'])
        assert all(c['name'] in images.images for c in deck['abilities'] + deck['gates'][1:])
        imported, _, _ = module.resolve_deck(json.dumps(exported).encode())
        assert imported['bakugan'] == deck['bakugan']
        assert imported['abilities'] == deck['abilities']
        assert imported['gates'] == deck['gates']
        assert exported['name'] == f'Random {attribute.title()} Balanced Deck'
        assert [abilities[c]['category'] for c in exported['abilities']] == ['signature'] * 3 + ['normal'] * 3
        for member, identifier in zip(exported['bakugans'], exported['abilities'][:3]):
            assert member['id'] in abilities[identifier]['bakuganIds']
        assert not validate_export(exported, site)


def test_random_deck_restrictions():
    import random
    from bakugandb.deck_legality import validate_export
    site = json.loads((Path(__file__).parents[1] / 'data' / 'site_catalog.json').read_text())
    for attribute in module.ATTRIBUTES:
        _, _, _, exported = module.random_site_deck(attribute, random.Random(9))
        assert not validate_export(exported, site)
        exported['bakugans'][0] = {'id': 'alpha_hydranoid', 'attribute': 'aquos'}
        assert any('banned' in issue for issue in validate_export(exported, site))
    _, _, _, exported = module.random_site_deck('aquos', random.Random(2))
    exported['abilities'][1] = exported['abilities'][0]
    assert any('Duplicate card' in issue for issue in validate_export(exported, site))
    _, _, _, exported = module.random_site_deck('aquos', random.Random(3))
    exported['bakugans'][1] = {'id': 'hammersaur', 'attribute': 'aquos'}
    assert any('Hammersaur' in issue and 'unavailable' in issue for issue in validate_export(exported, site))
    exported['bakugans'][1] = {'id': 'delta_dragonoid', 'attribute': 'aquos'}
    problems = validate_export(exported, site)
    assert any('Delta Dragonoid is banned' in issue for issue in problems)
    assert any('requires Pyrus' in issue for issue in problems)
    exported['bakugans'][1] = {'id': 'baliton', 'attribute': 'aquos'}
    assert any('Baliton' in issue and 'unavailable' in issue for issue in validate_export(exported, site))


def test_themed_decks_and_validation():
    import random
    from bakugandb.deck_legality import validate_export
    site = json.loads((Path(__file__).parents[1] / 'data' / 'site_catalog.json').read_text())
    generated = 0
    for attribute in module.ATTRIBUTES:
        for style in ('balanced', 'offense', 'defense', 'control'):
            try:
                _, _, _, export = module.random_site_deck(attribute, random.Random(15), style)
            except ValueError as exc:
                assert style != 'balanced' and 'Not enough' in str(exc)
                continue
            assert not validate_export(export, site)
            assert export['name'].endswith(style.title() + ' Deck')
            generated += 1
    assert generated >= 18
    _, _, _, export = module.random_site_deck('aquos', random.Random(1))
    export['abilities'][0] = export['abilities'][1]
    assert 'Duplicate card ID' in validate_export(export, site)
    export['abilities'] = []
    assert any('Abilities: 0/6' in issue for issue in validate_export(export, site))
    _, _, _, export = module.random_site_deck('aquos', random.Random(1))
    export['abilities'][0] = 'aquos_and_haos_contrast'
    assert any('needs aquos, haos' in issue for issue in validate_export(export, site))
    export['abilities'][0] = 'blue_squall'
    assert any('Blue Squall needs its Signature prerequisite' in issue for issue in validate_export(export, site))
