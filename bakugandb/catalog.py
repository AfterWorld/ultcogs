"""Validated, read-only catalog and search logic; no Discord dependency."""
import difflib
import json
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).parent / 'data'
ATTRIBUTES = {'aquos', 'pyrus', 'ventus', 'subterra', 'haos', 'darkus', 'null', 'omni'}


def normalize(value):
    value = unicodedata.normalize('NFKD', value).casefold()
    return re.sub(r'[^a-z0-9]+', '', value)


class Catalog:
    def __init__(self, directory=DATA):
        self.cards = self._read(directory / 'cards.json', list)
        self.bakugan = self._read(directory / 'bakugan.json', list)
        self.rules = self._read(directory / 'rules.json', dict)
        self.patch_history = self._read(directory / 'patch_history.json', dict)
        self.images = self._read(directory / 'images.json', dict)
        self.random_pool = self._read(directory / 'random_pool.json', dict)
        for name, image in self.images.items():
            if not isinstance(name, str) or not isinstance(image, dict) or not str(image.get('url', '')).startswith('https://'):
                raise ValueError('Malformed card image mapping')
        names = set()
        for card in self.cards:
            if not isinstance(card, dict) or not isinstance(card.get('name'), str) or not card['name'].strip():
                raise ValueError('Card without a name')
            if not isinstance(card.get('requires'), list) or not isinstance(card.get('attributes'), list) or not isinstance(card.get('bakugan'), list):
                raise ValueError('Malformed card: ' + card['name'])
            names.add(normalize(card['name']))
        for card in self.cards:
            card['unresolved_requires'] = [n for n in card['requires'] if normalize(n) not in names]

    @staticmethod
    def _read(path, expected):
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, expected):
            raise ValueError(f'{path.name} must be {expected.__name__}')
        return value

    def lookup(self, name, collection=None):
        entries = collection if collection is not None else self.cards
        key = normalize(name)
        if not key:
            return None
        exact = [c for c in entries if normalize(c['name']) == key]
        if exact:
            return exact[0]
        partial = [c for c in entries if key in normalize(c['name'])]
        if len(partial) == 1:
            return partial[0]
        return None

    def suggest(self, name, collection=None):
        entries = collection if collection is not None else self.cards
        lookup = {normalize(c['name']): c['name'] for c in entries}
        matches = difflib.get_close_matches(normalize(name), lookup, n=5, cutoff=.5)
        return [lookup[k] for k in matches]

    def filter(self, query, gates=False):
        words = [normalize(w) for w in query.split() if normalize(w)]
        entries = [c for c in self.cards if ('gate' in c['type'].lower()) == gates]
        def fields(c):
            return [c['name'], c['type'], *(c['attributes']), *(c['bakugan']), *(c['requires'])]
        def match(c, word):
            if word in ('fusion','signature','normal','trap','reactor','attribute','character','command'):
                return word in normalize(c['type'])
            return any(word in normalize(v) for v in fields(c))
        return [c for c in entries if all(match(c, w) for w in words)]

    def search(self, query):
        words = [normalize(w) for w in query.split() if normalize(w)]
        return [c for c in self.cards if all(w in normalize(' '.join(str(c.get(k) or '') for k in ('name','effect','excerpt','type','requires'))) for w in words)]

    def fusion(self, query):
        key = normalize(query)
        return [c for c in self.cards if 'fusion' in c['type'].lower() and (key in normalize(c['name']) or any(key in normalize(n) for n in c['requires']))]
