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
        assert exported['name'] == f'Random {attribute.title()} Deck'
        assert not module.check_random_export(exported, json.loads((Path(__file__).parents[1] / 'data' / 'site_catalog.json').read_text()))


def test_random_deck_restrictions():
    import random
    site = json.loads((Path(__file__).parents[1] / 'data' / 'site_catalog.json').read_text())
    for attribute in module.ATTRIBUTES:
        _, _, _, exported = module.random_site_deck(attribute, random.Random(9))
        assert not module.check_random_export(exported, site)
        exported['bakugans'][0] = {'id': 'alpha_hydranoid', 'attribute': 'aquos'}
        assert any('Banned Bakugan' in issue for issue in module.check_random_export(exported, site))
    _, _, _, exported = module.random_site_deck('aquos', random.Random(2))
    exported['abilities'][1] = exported['abilities'][0]
    assert any('Duplicate card' in issue for issue in module.check_random_export(exported, site))
