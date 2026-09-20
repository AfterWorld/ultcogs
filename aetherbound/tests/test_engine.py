import copy
import random

import pytest

from aetherbound import engine as g
from aetherbound.content import MONSTERS, SLOTS


def graduate(cls="vanguard", level=1):
    p = g.new_player("Tester", cls)
    g.equip(p, next(i["id"] for i in p["inventory"].values() if i["slot"] == "main"))
    g.begin(p, "slime", practice=True)
    for action in ["guard", "skill1"] + ["attack"] * 20:
        if not p["battle"]:
            break
        b = p["battle"]
        g.act(p, b["id"], b["turn"], action, random.Random(1))
    assert p["tutorial"] == 2
    for i in list(p["inventory"].values()):
        g.equip(p, i["id"])
    i = g.forge(p, "ring1")
    g.equip(p, i["id"])
    assert p["tutorial"] == 5
    g.begin(p, "slime")
    while p["battle"]:
        b = p["battle"]
        g.act(p, b["id"], b["turn"], "attack", random.Random(1))
    assert p["tutorial"] == 6
    p["level"] = level
    return p


def test_roster():
    assert len(MONSTERS) == 15
    assert sum(m["boss"] for m in MONSTERS.values()) == 2
    assert len(SLOTS) == 11


@pytest.mark.parametrize("cls", ["vanguard", "strider", "arcanist"])
def test_entire_tutorial(cls):
    p = graduate(cls)
    before = copy.deepcopy(p)
    for _ in range(20):
        g.advance_tutorial(p)
    assert p == before
    assert p["trained"]
    assert any(i["unique"] == "wayfarer" for i in p["inventory"].values())


def test_training_requires_all_actions():
    p = g.new_player("Trainer", "vanguard")
    g.equip(p, next(iter(p["inventory"])))
    g.begin(p, "slime", practice=True)
    while p["battle"]:
        b = p["battle"]
        g.act(p, b["id"], b["turn"], "attack", random.Random(2))
    assert p["tutorial"] == 1 and not p["trained"]
    assert p["gold"] == 0


def test_equip_twohand_and_combat_lock():
    p = graduate()
    weapon = g.make_item("main", twohand=True)
    p["inventory"][weapon["id"]] = weapon
    g.equip(p, weapon["id"])
    assert "off" not in p["equipped"]
    off = next(i for i in p["inventory"].values() if i["slot"] == "off")
    with pytest.raises(g.RuleError):
        g.equip(p, off["id"])
    g.begin(p, "slime")
    with pytest.raises(g.RuleError):
        g.equip(p, weapon["id"])
    with pytest.raises(g.RuleError):
        g.upgrade(p, weapon["id"])


def test_upgrade_and_level_caps():
    p = graduate()
    p["gold"] = 100000
    p["materials"]["iron"] = 100
    key = p["equipped"]["main"]
    for _ in range(5):
        g.upgrade(p, key)
    with pytest.raises(g.RuleError):
        g.upgrade(p, key)
    g.grant_xp(p, 10000000)
    assert p["level"] == 20 and p["points"] == 38 and p["xp"] == 0


def test_cannot_double_resolve_turn():
    p = graduate()
    g.begin(p, "slime")
    bid = p["battle"]["id"]
    g.act(p, bid, 0, "guard", random.Random(1))
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.act(p, bid, 0, "attack", random.Random(1))
    assert p == before


def test_quest_one_time():
    p = graduate()
    g.accept_quest(p, "first_hunts")
    p["wins"] = 4
    g.claim_quest(p, "first_hunts")
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.claim_quest(p, "first_hunts")
    assert p == before


def test_unique_does_not_stack():
    p = graduate()
    for slot in ("ring1", "ring2"):
        i = g.make_item(slot, unique="emberblade")
        p["inventory"][i["id"]] = i
        g.equip(p, i["id"])
    assert game_uniques(p).count("emberblade") == 1


def game_uniques(p):
    return list(g.stats(p)["uniques"])


@pytest.mark.parametrize(
    "text",
    [
        "hello everyone",
        "what are you trading?",
        "trading sword",
        "trading @everyone for sword",
        "trading sword for https://x.com",
        "trading sword for item\nhello",
    ],
)
def test_nonoffers_rejected(text):
    assert g.trade_offer(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "trading iron sword for crystal staff",
        "WTT iron sword for item",
        "trade two potions for iron",
    ],
)
def test_trade_grammar(text):
    assert g.trade_offer(text)


def test_category_never_top_with_others():
    for n in range(1, 50):
        assert 1 <= g.category_index(n) <= n
    assert g.category_index(0) == 0


def test_trivial_rewards_reduced():
    low = graduate(level=1)
    high = graduate(level=20)
    b = {"practice": False, "monster": "slime"}
    a = low["gold"]
    z = high["gold"]
    g.reward(low, b, random.Random(1))
    g.reward(high, b, random.Random(1))
    assert high["gold"] - z < low["gold"] - a


def test_tutorial_resources_cannot_be_spent_early():
    p = g.new_player("Student", "vanguard")
    p["gold"] = 60
    p["materials"] = {"iron": 4, "essence": 2}
    with pytest.raises(g.RuleError):
        g.forge(p, "main")
    with pytest.raises(g.RuleError):
        g.upgrade(p, next(iter(p["inventory"])))
    assert p["gold"] == 60


def test_guardian_quest_requires_correct_boss():
    p = graduate()
    g.accept_quest(p, "guardian")
    p["boss_wins"] = 1
    p["kills"] = {"raizen": 1}
    with pytest.raises(g.RuleError):
        g.claim_quest(p, "guardian")
    p["kills"]["tsukara"] = 1
    g.claim_quest(p, "guardian")
    assert "guardian" in p["quests"]


def test_no_reward_for_flee_and_one_reward_per_dungeon():
    p = graduate(level=10)
    g.begin(p, "slime")
    gold = p["gold"]
    g.act(p, p["battle"]["id"], 0, "flee", random.Random(1))
    assert p["gold"] == gold and p["battle"] is None
    p["run"] = {"room": 3, "hp": g.stats(p)["hp"]}
    g.begin(p, "tsukara")
    p["battle"]["enemy_hp"] = 1
    bid = p["battle"]["id"]
    g.act(p, bid, 0, "attack", random.Random(1))
    assert p["dungeons"] == 1 and p["run"] is None
    with pytest.raises(g.RuleError):
        g.act(p, bid, 0, "attack", random.Random(1))
    assert p["dungeons"] == 1


def test_invalid_action_does_not_change_state():
    p = graduate()
    g.begin(p, "slime")
    p["battle"]["energy"] = 0
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.act(p, p["battle"]["id"], 0, "skill1", random.Random(1))
    assert p == before


def test_encounter_balance_bounds():
    from aetherbound.balance import simulate

    for cls in ("vanguard", "strider", "arcanist"):
        for key in MONSTERS:
            results = [simulate(cls, key, "common", seed) for seed in range(10)]
            assert sum(won for won, _ in results) >= 8
            assert all(2 <= turns < 30 for _, turns in results)


def test_batch_equip_final_loadout_and_rejection():
    p = graduate()
    weapon = g.make_item("main", twohand=True)
    p["inventory"][weapon["id"]] = weapon
    g.equip(p, weapon["id"])
    onehand = next(i for i in p["inventory"].values() if i["slot"] == "main" and not i["twohand"])
    off = next(i for i in p["inventory"].values() if i["slot"] == "off")
    g.equip_many(p, [off["id"], onehand["id"]])
    assert p["equipped"]["off"] == off["id"]
    assert p["equipped"]["main"] == onehand["id"]
    high = g.make_item("head", level=20)
    p["inventory"][high["id"]] = high
    for ids in (
        [weapon["id"], off["id"]],
        [onehand["id"], weapon["id"]],
        [off["id"], off["id"]],
        [weapon["id"], "missing"],
        [weapon["id"], high["id"]],
        [],
    ):
        before = copy.deepcopy(p)
        with pytest.raises(g.RuleError):
            g.equip_many(p, ids)
        assert p == before


def test_batch_starter_gear_progress_and_no_double_rewards():
    p = g.new_player("Hero", "strider")
    g.equip_many(p, list(p["inventory"]))
    assert p["tutorial"] == 1
    before = copy.deepcopy(p)
    g.equip_many(p, list(p["inventory"]))
    assert p == before
    g.begin(p, "slime", practice=True)
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.equip_many(p, list(p["inventory"]))
    assert p == before


def test_tutorial_commands_contain_real_ids_and_prefix():
    p = g.new_player("Hero", "arcanist")
    text = g.tutorial(p, "!")
    assert "!aether equip " + " ".join(p["inventory"]) in text
    assert "Step 1/6" in text
    g.equip_many(p, list(p["inventory"]))
    g.begin(p, "slime", practice=True)
    assert "`!aether resume`" in g.tutorial(p, "!")
