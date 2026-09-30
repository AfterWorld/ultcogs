import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('bakugandb_public_decks', Path(__file__).parents[1] / 'public_decks.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_search_decks():
    posts = [
        {'title': 'Aquos Defense', 'author_name': 'Adam', 'attribute': 'aquos', 'search_text': 'Preyas Water Veil'},
        {'title': 'Pyrus Attack', 'author_name': 'Sam', 'attribute': 'pyrus', 'search_text': 'Drago Fire Tornado'},
    ]
    assert [p['title'] for p in module.search_decks(posts, 'aquos preyas')[0]] == ['Aquos Defense']
    assert [p['title'] for p in module.search_decks(posts, 'author:adam')[0]] == ['Aquos Defense']
    assert module.search_decks(posts, 'page:2')[1] == 2
    assert module.search_decks(posts, '2')[1] == 2
    assert module.search_decks(posts, '')[0][0]['title'] == 'Pyrus Attack'
