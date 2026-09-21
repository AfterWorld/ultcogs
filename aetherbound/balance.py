"""Reproducible encounter simulation: python -m aetherbound.balance.

This is a regression baseline, not a substitute for human balance playtesting.
"""

import random
from statistics import mean

from . import engine as g
from .content import CLASSES, GEAR_SETS, MONSTERS, SLOTS


def actor(cls, level, gear, seed):
    p = g.new_player("Simulator", cls)
    p.update(level=level, tutorial=6, inventory={}, equipped={}, potions=0)
    p["attrs"][CLASSES[cls]["stat"]] = level - 1
    p["attrs"]["vitality"] = level - 1
    rng = random.Random(seed)
    for slot in SLOTS:
        item_level = 1 if gear == "starter" else level
        i = g.make_item(slot, item_level, "common" if gear == "starter" else gear, rng)
        p["inventory"][i["id"]] = i
        p["equipped"][slot] = i["id"]
    return p


def simulate(cls, key, gear, seed, smart=True, customization=None):
    level = MONSTERS[key]["level"]
    p = actor(cls, level, gear, seed)
    if customization:
        set_id, rune = customization
        for slot in SLOTS[2:7]:
            p["inventory"][p["equipped"][slot]]["set_id"] = set_id
        if rune:
            for i in p["inventory"].values():
                i["sockets"] = [rune]
    g.begin(p, key)
    rng = random.Random(seed)
    turns = 0
    while p["battle"]:
        b = p["battle"]
        action = "attack"
        if smart:
            if b["turn"] % 3 == 2:
                action = (
                    "skill2"
                    if not b["cooldowns"].get("skill2") and b["energy"] >= g.skill_cost(p, "skill2")
                    else "guard"
                )
            elif not b["cooldowns"].get("skill1") and b["energy"] >= g.skill_cost(p, "skill1"):
                action = "skill1"
        if smart == "identity":

            def ready(key):
                return not b["cooldowns"].get(key) and b["energy"] >= g.skill_cost(p, key)

            if b["turn"] % 3 == 2 and ready("skill3"):
                action = "skill3"
            elif cls == "arcanist" and b.get("resource", 0) < 2 and b["turn"] % 3 != 2:
                action = "attack"
            elif cls == "strider" and action == b["last"]:
                action = (
                    "attack" if b["last"] != "attack" else "skill2" if ready("skill2") else "guard"
                )
        g.act(p, b["id"], b["turn"], action, rng)
        turns += 1
    return bool(p["wins"]), turns


def report(samples=50):
    rows = []
    for cls in CLASSES:
        for key in MONSTERS:
            for gear in ("starter", "common", "uncommon", "rare", "epic", "legendary", "mythic"):
                outcomes = [simulate(cls, key, gear, seed) for seed in range(samples)]
                rows.append(
                    (cls, key, gear, mean(w for w, t in outcomes), mean(t for w, t in outcomes))
                )
    lines = [
        "# Class identity balance baseline",
        "",
        f"{len(rows) * samples:,} seeded solo simulations; fixed monster level, equally leveled player, no potions. Each player allocates one point/level to their class stat and one to vitality. The scripted strategy interrupts charged attacks and uses its damage skill when available. Starter gear is level 1 in every slot; all other gear matches the player level. Higher-tier cases are stress tests even at levels where those tiers cannot drop; Unique effects have separate regression tests.",
        "",
        "These checks establish bounds, not final balance. They do not simulate human mistakes, party combat, or the full acquisition economy. Live Discord playtesting is still required.",
        "",
        "| Class | Gear | Normal win rate | Boss win rate | Mean normal turns | Mean boss turns |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for cls in CLASSES:
        for gear in ("starter", "common", "uncommon", "rare", "epic", "legendary", "mythic"):
            normal = [
                r for r in rows if r[0] == cls and r[2] == gear and not MONSTERS[r[1]]["boss"]
            ]
            bosses = [r for r in rows if r[0] == cls and r[2] == gear and MONSTERS[r[1]]["boss"]]
            lines.append(
                f"| {cls} | {gear} | {mean(r[3] for r in normal):.1%} | {mean(r[3] for r in bosses):.1%} | {mean(r[4] for r in normal):.1f} | {mean(r[4] for r in bosses):.1f} |"
            )
    lines += [
        "",
        "## Individual boss outcomes",
        "",
        "| Class | Boss | Gear | Win rate | Mean turns |",
        "|---|---|---|---:|---:|",
    ]
    for cls, key, gear, win, turns in rows:
        if MONSTERS[key]["boss"]:
            lines.append(f"| {cls} | {key} | {gear} | {win:.1%} | {turns:.1f} |")
    lines += [
        "",
        "## Boss strategy comparison",
        "",
        "50 seeds per case, no potions; 1,800 additional fights. Starter gear stays at level 1. "
        "Identity rotates defensive skills, banks Arcanist charges and avoids repeated Strider attacks. These policies are not optimal play.",
        "",
        "| Class | Boss | Gear | Strategy | Win rate | Mean turns |",
        "|---|---|---|---|---:|---:|",
    ]
    for cls in CLASSES:
        for boss in ("tsukara", "raizen"):
            for gear in ("starter", "common"):
                for label, policy in (
                    ("Attack only", False),
                    ("Interrupt", True),
                    ("Identity", "identity"),
                ):
                    outcomes = [
                        simulate(cls, boss, gear, seed, smart=policy) for seed in range(samples)
                    ]
                    lines.append(
                        f"| {cls} | {boss} | {gear} | {label} | {mean(w for w, t in outcomes):.1%} | {mean(t for w, t in outcomes):.1f} |"
                    )
    lines += [
        "",
        "## Experience pacing",
        "",
        "| Current level | EXP to next | Same-level normal wins (rounded up) |",
        "|---|---:|---:|",
    ]
    for level in (1, 5, 10, 15, 19):
        xp = g.xp_needed(level)
        reward = 24 + 8 * level
        lines.append(f"| {level} | {xp} | {(xp + reward - 1) // reward} |")
    return "\n".join(lines) + "\n"


def customization_report(samples=50):
    lines = [
        "# Sets and sockets balance checks",
        "",
        "3 classes × 2 bosses × 4 loadouts × 3 rune configurations × 50 seeds = 3,600 fights. "
        "Same-level rare gear, no potions, interrupt policy. All five armor slots carry the selected set; "
        "rune cases fill all 11 slots with the class damage rune or stone (+22 vitality). "
        "This tests maximum stacking, not acquisition speed or human mistakes. Existing plain-gear reports remain unchanged.",
        "",
        "| Class | Boss | Set | Runes | Win rate | Mean turns |",
        "|---|---|---|---|---:|---:|",
    ]
    for cls in CLASSES:
        damage_rune = {"vanguard": "ember", "strider": "gale", "arcanist": "aether"}[cls]
        for boss in ("tsukara", "raizen"):
            for set_id in (None, *GEAR_SETS):
                for rune in (None, damage_rune, "stone"):
                    outcomes = [
                        simulate(cls, boss, "rare", seed, customization=(set_id, rune))
                        for seed in range(samples)
                    ]
                    lines.append(
                        f"| {cls} | {boss} | {set_id or 'none'} | {rune or 'none'} | {mean(w for w, t in outcomes):.1%} | {mean(t for w, t in outcomes):.1f} |"
                    )
    return "\n".join(lines) + "\n"


def armor_report(samples=50):
    lines = [
        "# Armor cap audit",
        "",
        "Fully equipped Vanguard; same-level gear in all 11 slots, one vitality point per level, no upgrades. "
        "50 seeds per row. Higher tiers below their unlock level are stress tests. "
        "The final column counts builds where adding +1 upgrade to the chest produces no armor gain.",
        "",
        "| Level | Rarity | Mean armor | Above soft threshold | Wasted chest upgrade |",
        "|---|---|---:|---:|---:|",
    ]
    for level in (1, 3, 5, 6, 8, 10, 15, 20):
        for rarity in ("common", "uncommon", "rare", "epic", "legendary", "mythic"):
            armor, capped, wasted = [], 0, 0
            for seed in range(samples):
                p = actor("vanguard", level, rarity, seed)
                before = g.stats(p)["armor"]
                armor.append(before)
                capped += before > 100
                p["inventory"][p["equipped"]["chest"]]["upgrade"] = 1
                wasted += g.stats(p)["armor"] == before
            lines.append(
                f"| {level} | {rarity} | {mean(armor):.1f} | {capped / samples:.0%} | {wasted / samples:.0%} |"
            )
    lines += [
        "",
        "Effective armor equals raw armor up to 100, then 100 + 50 * ln(1 + (raw - 100) / 50). "
        "Damage reduction still uses 100 / (100 + effective armor). Every extra point of raw armor "
        "increases effective armor, though integer damage rounding can hide a small gain on an individual hit.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--armor", action="store_true", help="Report cap saturation without changing combat"
    )
    parser.add_argument(
        "--customization", action="store_true", help="Compare sets and maximum rune stacking"
    )
    args = parser.parse_args()
    print(
        customization_report()
        if args.customization
        else armor_report()
        if args.armor
        else report(),
        end="",
    )
