import json
from pathlib import Path

import importlib.util

spec = importlib.util.spec_from_file_location("bakugandb_catalog", Path(__file__).parents[1] / "catalog.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Catalog, normalize = module.Catalog, module.normalize


def test_catalog():
    catalog = Catalog()
    assert catalog.lookup('blue squall')['name'] == 'Blue Squall'
    assert catalog.lookup('bluesquall')['name'] == 'Blue Squall'
    assert catalog.lookup('squall')['name'] == 'Blue Squall'
    assert 'Blue Squall' in catalog.suggest('blue sqall')
    assert any(c['name'] == 'Blue Squall' for c in catalog.fusion('blue stealth'))
    assert any(c['name'] == 'Blue Squall' for c in catalog.filter('normal aquos')) is False
    assert any(c['name'] == 'Blue Squall' for c in catalog.filter('fusion aquos'))
    assert catalog.images['Blue Squall']['url'].endswith('ability_fusion_blue_squall.webp')
    assert normalize('Blue Squall') == normalize('BlueSquall')


def test_bad_data(tmp_path):
    for name, value in [('cards.json', [{}]), ('bakugan.json', []), ('rules.json', {}), ('patch_history.json', {}), ('images.json', {}), ('random_pool.json', {})]:
        (tmp_path / name).write_text(json.dumps(value))
    try:
        Catalog(tmp_path)
    except ValueError as exc:
        assert 'Card without a name' in str(exc)
    else:
        raise AssertionError('Malformed card accepted')


def test_random_deck():
    import random
    import sys
    # Load the pure sampler without importing discord.py from the cog package.
    parent = Path(__file__).parents[1]
    package = type(sys)("bakugandb")
    package.__path__ = [str(parent)]
    sys.modules.setdefault("bakugandb", package)
    sys.modules.setdefault("bakugandb.catalog", module)
    sampler_spec = importlib.util.spec_from_file_location("bakugandb.random_deck", parent / "random_deck.py")
    sampler = importlib.util.module_from_spec(sampler_spec)
    sampler_spec.loader.exec_module(sampler)
    catalog = Catalog()
    for attribute in catalog.random_pool['bakugan']:
        deck = sampler.build_random_deck(catalog, attribute, random.Random(5))
        assert len(deck['bakugan']) == 3
        assert len(deck['abilities']) == 6
        assert len(deck['gates']) == 3
        assert deck['gates'][0]['type'] == 'Attribute Gate'
        assert len({normalize(c['name']) for c in deck['abilities'] + deck['gates']}) == 9
