"""Conservative mono-attribute deck sampler from verified catalog names."""
import random
from .catalog import normalize


def build_random_deck(catalog, attribute=None, rng=None):
    rng = rng or random.Random()
    pools = catalog.random_pool['bakugan']
    if attribute:
        attribute = next((a for a in pools if normalize(a) == normalize(attribute)), None)
        if not attribute:
            raise ValueError('Choose Aquos, Pyrus, Ventus, Subterra, Haos or Darkus.')
    else:
        attribute = rng.choice(list(pools))
    pool = pools[attribute]
    bakugan = [rng.choice(pool['guardian']), *rng.sample(pool['generic'], 2)]
    abilities = [c for c in catalog.cards if c['type'] == 'Normal Ability' and c['attributes'] == [attribute]
                 and not c['bakugan'] and c['status'] != 'removed' and c['name'] in catalog.images]
    commands = [c for c in catalog.cards if c['type'] == 'Command Gate' and c['status'] != 'removed'
                and c['name'] in catalog.images]
    gate = catalog.lookup(attribute + ' Gate')
    if not gate or gate['type'] != 'Attribute Gate' or len(abilities) < 6 or len(commands) < 2:
        raise ValueError('Not enough verified cards for this attribute.')
    selected = rng.sample(abilities, 6)
    gates = [gate, *rng.sample(commands, 2)]
    names = [c['name'] for c in selected + gates]
    if len(set(map(normalize, names))) != 9:
        raise ValueError('Generated duplicate card names.')
    return {'attribute': attribute, 'bakugan': bakugan, 'abilities': selected, 'gates': gates,
            'note': 'Sampled from confirmed names. Check current card text and site legality before play.'}
