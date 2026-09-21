import copy

import pytest

from aetherbound import engine as g
from aetherbound.content import GEAR_SETS, RUNES
from aetherbound.presentation import channel_embed, inventory_embed, sets_embed
from aetherbound.store import Store

from .test_engine import graduate


def hero():
    p = graduate(level=6)
    p.update(gold=10000, materials={"iron": 100, "essence": 100})
    return p


def test_set_thresholds_removal_and_rating():
    p = hero()
    pieces = [
        g.forge_set(p, slot, "dawnward") for slot in ("head", "chest", "hands", "legs", "feet")
    ]
    for n, i in enumerate(pieces, 1):
        g.equip(p, i["id"])
        plain = copy.deepcopy(p)
        for gear in plain["inventory"].values():
            gear.pop("set_id", None)
        actual, base = g.attributes(p), g.attributes(plain)
        assert actual["vitality"] - base["vitality"] == (3 if n >= 2 else 0)
        assert actual["strength"] - base["strength"] == (4 if n >= 4 else 0)
        if n >= 2:
            assert g.loadout_rating(p) > g.loadout_rating(plain)
    p["equipped"].pop("head")
    p["equipped"].pop("chest")
    assert g.set_counts(p) == {"dawnward": 3}


def test_socket_cost_effect_binding_and_removal():
    p = hero()
    i = g.forge_set(p, "head", "starweave")
    g.equip(p, i["id"])
    base = g.attributes(p)
    gold, essence = p["gold"], p["materials"]["essence"]
    g.socket(p, i["id"], "stone")
    assert g.attributes(p)["vitality"] == base["vitality"] + 2
    assert p["gold"] == gold - 75 and p["materials"]["essence"] == essence - 4
    assert i["bound"]
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.socket(p, i["id"], "ember")
    assert p == before
    g.unsocket(p, i["id"])
    assert g.attributes(p) == base and i["bound"] and not i["sockets"]
    assert p["gold"] == gold - 100


@pytest.mark.parametrize("invalid", ["battle", "locked", "poor", "level", "rune", "tutorial"])
def test_socket_rejections_are_atomic(invalid):
    p = hero()
    i = g.forge_set(p, "head", "moonstep")
    rune = "gale"
    if invalid == "battle":
        g.begin(p, "slime")
    elif invalid == "locked":
        i["locked"] = True
    elif invalid == "poor":
        p["materials"]["essence"] = 0
    elif invalid == "level":
        i["level"] = 1
    elif invalid == "rune":
        rune = "invalid"
    else:
        p["tutorial"] = 5
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.socket(p, i["id"], rune)
    assert p == before


def test_legacy_and_full_bag():
    p = hero()
    base = g.stats(p)
    for i in p["inventory"].values():
        i.pop("sockets", None)
        i.pop("set_id", None)
    assert g.stats(p) == base
    while len(p["inventory"]) < 200:
        i = g.make_item("head")
        p["inventory"][i["id"]] = i
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.forge_set(p, "head", "dawnward")
    assert p == before


@pytest.mark.asyncio
async def test_persistence_and_switch(tmp_path):
    store = Store(tmp_path / "gear.db")
    await store.initialize()
    p = hero()
    await store.change(1, 2, lambda old, c: p, create=True)
    # Store create callbacks return the character; subsequent callbacks mutate it.
    await store.settings(1, {"features": {"sets": False}})
    with pytest.raises(g.RuleError):
        await store.change(1, 2, lambda p, c: g.forge_set(p, "head", "dawnward"), feature="sets")
    await store.settings(1, {"features": {"sets": True}})
    i = await store.change(1, 2, lambda p, c: g.forge_set(p, "head", "dawnward"), feature="sets")
    await store.change(1, 2, lambda p, c: g.socket(p, i["id"], "ember"), feature="sockets")
    store = Store(tmp_path / "gear.db")
    await store.initialize()
    saved = await store.player(1, 2)
    assert saved["inventory"][i["id"]]["sockets"] == ["ember"]
    assert saved["inventory"][i["id"]]["set_id"] == "dawnward"


def test_code_boxes_and_embed_limits():
    p = hero()
    settings = {
        "channels": {
            k: n for n, k in enumerate(("guide", "adventures", "spawns", "trading", "tavern"), 1)
        }
    }
    embeds = [channel_embed(k, settings, "!") for k in settings["channels"]]
    embeds += [sets_embed(p, "!"), inventory_embed(p, 1, "!")[0]]
    for e in embeds:
        assert len(e) <= 6000
        assert all(len(f.value) <= 1024 for f in e.fields)
        text = (e.description or "") + "\n".join(f.value for f in e.fields)
        assert "```text\n" in text
        assert text.count("```") % 2 == 0
    assert len(GEAR_SETS) == 3 and len(RUNES) == 5


@pytest.mark.parametrize("set_id", list(GEAR_SETS))
def test_each_set_and_rune_composes(set_id):
    p = hero()
    for slot, rune in zip(("head", "chest", "hands", "legs", "feet"), RUNES):
        i = g.forge_set(p, slot, set_id)
        g.socket(p, i["id"], rune)
        g.equip(p, i["id"])
    plain = copy.deepcopy(p)
    for i in plain["inventory"].values():
        i["set_id"] = None
        i["sockets"] = []
    expected = g.attributes(plain)
    for attr in RUNES.values():
        expected[attr] += 2
    for bonuses in GEAR_SETS[set_id]["bonuses"].values():
        for attr, value in bonuses.items():
            expected[attr] += value
    assert g.attributes(p) == expected
    # Mixing two collections grants each 2-piece bonus, not either 4-piece bonus.
    other = next(x for x in GEAR_SETS if x != set_id)
    for slot in ("head", "chest"):
        p["inventory"][p["equipped"][slot]]["set_id"] = other
    assert g.set_counts(p) == {other: 2, set_id: 3}
    expected = g.attributes(plain)
    for attr in RUNES.values():
        expected[attr] += 2
    for key in (other, set_id):
        for attr, value in GEAR_SETS[key]["bonuses"][2].items():
            expected[attr] += value
    assert g.attributes(p) == expected
