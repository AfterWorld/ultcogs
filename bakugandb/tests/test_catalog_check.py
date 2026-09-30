"""The drift report detects changes without editing the snapshot."""
import importlib.util
import json
from pathlib import Path

root = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('bakugandb_catalog_check', root / 'catalog_check.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_catalog_drift():
    snapshot = json.loads((root / 'data' / 'site_catalog.json').read_text())
    current = {kind: [dict(entry) for entry in snapshot[kind]] for kind in ('bakugan', 'abilities', 'gates')}
    for entry in current['bakugan']:
        entry['variants'] = {attribute: '' for attribute in entry['available_attributes']}
    restrictions = json.loads((root / 'data' / 'site_legality.json').read_text())
    selected = {key: restrictions[key] for key in ('guardian_required_attribute', 'banned_bakugan_ids', 'release_locked_bakugan_ids', 'release_locked_until')}
    assert not module.compare(current, selected)['changes']
    current['bakugan'][0]['hidden'] = not current['bakugan'][0].get('hidden', False)
    assert any('hidden changed' in line for line in module.compare(current, selected)['changes'])
    assert module.imported_asset('from"./catalogs-abc_12.js"', 'catalogs') == '/assets/catalogs-abc_12.js'
    assert len(module.parse_catalogs('x=JSON.parse(`[{}]`),y=JSON.parse(`[{}]`),z=JSON.parse(`[{}]`)')['gates']) == 1
