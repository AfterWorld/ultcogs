import asyncio
import copy
import random
from types import SimpleNamespace as NS

import discord
import pytest

from aetherbound import configure_aliases
from aetherbound import economy as e
from aetherbound import engine as g
from aetherbound.art import ART_DIR, ART_KEYS, artwork, thumbnail
from aetherbound.content import MONSTERS, SLOTS
from aetherbound.loot import BOSS_DROPS, RARITIES, UNIQUES, migrate_names, roll_rarity
from aetherbound.presentation import quest_embed, shop_embed
from aetherbound.store import Store

from .test_engine import graduate

DAY = 1789862400  # fixed UTC boundary, independent of wall clock


def test_payday_daily_cap_tutorial_gate_and_rollback_clock():
    p = g.new_player("Hero", "vanguard")
    with pytest.raises(g.RuleError):
        e.payday(p, DAY)
    p = graduate(level=20)
    gold = p["gold"]
    e.payday(p, DAY)
    assert p["gold"] == gold + 100
    for now in (DAY, DAY + 86399, DAY - 86400):
        with pytest.raises(g.RuleError):
            e.payday(p, now)
    e.payday(p, DAY + 86400)
    assert p["gold"] == gold + 200


def test_shop_persists_day_and_level_and_rotates():
    p = graduate(level=10)
    offers = copy.deepcopy(e.shop(p, 1, 5, DAY))
    p["level"] = 20
    assert e.shop(p, 1, 5, DAY + 2) == offers
    recreated = graduate(level=10)
    assert e.shop(recreated, 1, 5, DAY) == offers
    assert e.shop(graduate(level=10), 2, 5, DAY) != offers
    assert e.shop(graduate(level=10), 1, 6, DAY) != offers
    p["gold"] = 100000
    old = offers["offers"][0]["code"]
    with pytest.raises(g.RuleError):
        e.buy(p, 1, 5, old, DAY + 86400)
    assert p["gold"] == 100000
    assert p["shop"]["day"] != offers["day"]
    assert p["shop"]["level"] == 20
    assert {o["item"]["rarity"] for o in p["shop"]["offers"] if "item" in o} == set(RARITIES) - {
        "unique"
    }


def test_shop_buy_exact_offer_and_no_duplicates():
    p = graduate(level=20)
    p["gold"] = 100000
    offer = e.shop(p, 1, 5, DAY)["offers"][0]
    before = set(p["inventory"])
    e.buy(p, 1, 5, offer["code"], DAY)
    added = (set(p["inventory"]) - before).pop()
    assert p["inventory"][added]["name"] == offer["name"]
    assert p["inventory"][added]["bonuses"] == offer["item"]["bonuses"]
    assert added != offer["item"]["id"]
    assert p["gold"] == 100000 - offer["price"]
    snapshot = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        e.buy(p, 1, 5, offer["code"], DAY)
    assert p == snapshot
    pouch = p["shop"]["offers"][-2]
    potions = p["potions"]
    e.buy(p, 1, 5, pouch["code"], DAY)
    assert p["potions"] == potions + 3
    pack = p["shop"]["offers"][-1]
    iron = p["materials"]["iron"]
    e.buy(p, 1, 5, pack["code"], DAY)
    assert p["materials"]["iron"] == iron + 4


def test_shop_rejects_full_bag_poverty_combat_training():
    p = graduate()
    offer = e.shop(p, 1, 5, DAY)["offers"][0]
    p["gold"] = 0
    with pytest.raises(g.RuleError):
        e.buy(p, 1, 5, offer["code"], DAY)
    assert offer["bought"] == 0
    p["gold"] = 99999
    while len(p["inventory"]) < 200:
        i = g.make_item("head")
        p["inventory"][i["id"]] = i
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        e.buy(p, 1, 5, offer["code"], DAY)
    assert p == before
    p["tutorial"] = 2
    with pytest.raises(g.RuleError):
        e.buy(p, 1, 5, p["shop"]["offers"][-1]["code"], DAY)
    p["tutorial"] = 6
    g.begin(p, "slime")
    with pytest.raises(g.RuleError):
        e.buy(p, 1, 5, p["shop"]["offers"][-1]["code"], DAY)


async def test_economy_atomic_across_store_instances(tmp_path):
    s = Store(tmp_path / "test.db")
    await s.initialize()
    other = Store(s.path)
    p = graduate()
    p["gold"] = 9999
    code = e.shop(p, 1, 5, DAY)["offers"][0]["code"]
    await s.change(1, 5, lambda _, c: p, create=True)
    for fn in (lambda p: e.payday(p, DAY), lambda p: e.buy(p, 1, 5, code, DAY)):
        results = await asyncio.gather(
            s.change(1, 5, lambda p, c: fn(p)),
            other.change(1, 5, lambda p, c: fn(p)),
            return_exceptions=True,
        )
        assert sum(isinstance(x, g.RuleError) for x in results) == 1
    saved = await other.player(1, 5)
    assert saved["shop"]["offers"][0]["bought"] == 1
    assert saved["payday_day"] == e.utc_day(DAY)
    gold = saved["gold"]
    with pytest.raises(g.RuleError):
        await s.change(1, 5, lambda p, c: e.buy(p, 1, 5, "expired", DAY + 86400))
    assert (await s.player(1, 5))["gold"] == gold
    assert (await s.player(1, 5))["shop"]["day"] == e.utc_day(DAY)


@pytest.mark.parametrize("rarity", RARITIES)
def test_all_tiers_bounded_and_equippable(rarity):
    p = graduate(level=20)
    for slot in SLOTS:
        i = g.make_item(slot, 20, rarity, random.Random(7))
        assert sum(i["bonuses"].values()) <= 20
        assert i["power"] <= 28
        assert "Ring1" not in i["name"] and "Ring2" not in i["name"]
        p["inventory"][i["id"]] = i
        g.equip(p, i["id"])
    stats = g.stats(p)
    assert stats["crit"] <= 0.35 and 100 < stats["armor"] < 250 and stats["energy"] <= 80


def test_loot_level_gates_and_all_rarities_reachable():
    rng = random.Random(17)
    for level in (1, 3, 6, 10, 16, 20):
        seen = {roll_rarity(level, False, rng) for _ in range(20000)}
        assert seen == {k for k, v in RARITIES.items() if k != "unique" and v["level"] <= level}


class UniqueRoll(random.Random):
    def random(self):
        return 0.0


@pytest.mark.parametrize("key", UNIQUES)
def test_unique_drop_tables_and_full_bag_overflow(key):
    p = graduate(level=20)
    while len(p["inventory"]) < 200:
        i = g.make_item("head")
        p["inventory"][i["id"]] = i
    g.reward(p, {"monster": key, "practice": False}, UniqueRoll(1))
    drops = p["unclaimed_loot"]
    assert len(drops) == 2
    assert drops[-1]["name"] == UNIQUES[key]["name"] and drops[-1]["rarity"] == "unique"
    if key in BOSS_DROPS:
        assert drops[0]["name"] in {name for _, name in BOSS_DROPS[key]}
        assert RARITIES[drops[0]["rarity"]]["rank"] >= 3
    old_ids = {i["id"] for i in drops}
    for item_id in [k for k in p["inventory"] if k not in p["equipped"].values()][:2]:
        del p["inventory"][item_id]
    g.claim_loot(p)
    assert old_ids <= set(p["inventory"]) and not p["unclaimed_loot"]
    p["unclaimed_loot"] = [g.make_item("head") for _ in range(20)]
    with pytest.raises(g.RuleError):
        g.begin(p, "slime")


def test_accept_before_progress_and_claim_once():
    p = graduate()
    p["wins"] = 50
    assert g.quest_progress(p, "first_hunts") == 0
    with pytest.raises(g.RuleError):
        g.claim_quest(p, "first_hunts")
    g.accept_quest(p, "first_hunts")
    assert g.quest_progress(p, "first_hunts") == 0
    with pytest.raises(g.RuleError):
        g.accept_quest(p, "first_hunts")
    p["wins"] += 3
    g.claim_quest(p, "first_hunts")
    with pytest.raises(g.RuleError):
        g.claim_quest(p, "first_hunts")


async def test_legacy_migration_preserves_gear_stats_and_progress(tmp_path):
    s = Store(tmp_path / "legacy.db")
    await s.initialize()
    p = graduate()
    p.pop("accepted_quests")
    p["wins"] = 3
    i = g.make_item("ring1", rarity="uncommon")
    i["name"] = "Uncommon Ring1 of Hoshifall"
    p["inventory"][i["id"]] = i
    p["equipped"]["ring1"] = i["id"]
    before = g.stats(p)
    await s.change(1, 5, lambda _, c: p, create=True)
    await s.initialize()
    saved = await s.player(1, 5)
    assert g.stats(saved) == before
    assert saved["equipped"] == p["equipped"]
    assert saved["inventory"][i["id"]]["name"] != i["name"]
    assert g.quest_progress(saved, "first_hunts") == 3
    await s.initialize()
    assert await s.player(1, 5) == saved
    await s.change(1, 5, lambda p, c: g.claim_quest(p, "first_hunts"))


def test_custom_names_preserved():
    p = graduate()
    before = copy.deepcopy(p)
    migrate_names(p)
    assert p == before


def test_alias_registration_respects_other_cogs():
    cog = NS(adventure=NS(aliases=[]))
    configure_aliases(NS(get_command=lambda _: None), cog)
    assert cog.adventure.aliases == ["ae", "a"]
    configure_aliases(NS(get_command=lambda key: object() if key == "a" else None), cog)
    assert cog.adventure.aliases == ["ae"]


def test_all_art_bundled_and_quest_shop_embed_limits():
    assert {p.stem for p in ART_DIR.glob("*.jpg")} == ART_KEYS
    assert ART_KEYS <= set(MONSTERS)
    for key in ART_KEYS:
        embed = discord.Embed()
        kwargs = artwork(embed, key)
        assert embed.thumbnail.url == f"attachment://{key}.jpg"
        assert kwargs["file"].filename == f"{key}.jpg"
        kwargs["file"].close()
        thumbnail(embed, key)
        assert embed.footer.text.count("Redshrike") == 1
    for key in set(MONSTERS) - ART_KEYS:
        embed = discord.Embed()
        assert artwork(embed, key) == {}
        thumbnail(embed, key)
        assert embed.thumbnail.url is None
    p = graduate(level=20)
    for embed in (quest_embed(p, "!"), shop_embed(e.shop(p, 1, 5, DAY), p["gold"], "!")):
        assert len(embed) < 6000
        assert all(len(f.value) <= 1024 for f in embed.fields)
    assert "!aether quests accept" in quest_embed(p, "!").fields[0].value


def test_retired_art_is_ignored_even_if_left_on_disk(tmp_path, monkeypatch):
    import aetherbound.art as art

    monkeypatch.setattr(art, "ART_DIR", tmp_path)
    (tmp_path / "tsukara.jpg").write_bytes(b"retired portrait")
    embed = discord.Embed()
    assert art.artwork(embed, "tsukara") == {}
    art.thumbnail(embed, "tsukara")
    assert embed.thumbnail.url is None
