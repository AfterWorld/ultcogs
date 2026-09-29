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
    for name, value in [('cards.json', [{}]), ('bakugan.json', []), ('rules.json', {}), ('patch_history.json', {}), ('images.json', {})]:
        (tmp_path / name).write_text(json.dumps(value))
    try:
        Catalog(tmp_path)
    except ValueError as exc:
        assert 'Card without a name' in str(exc)
    else:
        raise AssertionError('Malformed card accepted')
