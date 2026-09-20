"""Reproducible encounter simulation: python -m aetherbound.balance.

This is a regression baseline, not a substitute for human balance playtesting.
"""

import random
from statistics import mean

from . import engine as g
from .content import CLASSES, MONSTERS, SLOTS


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


def simulate(cls, key, gear, seed, smart=True):
    level = MONSTERS[key]["level"]
    p = actor(cls, level, gear, seed)
    g.begin(p, key)
    rng = random.Random(seed)
    turns = 0
    while p["battle"]:
        b = p["battle"]
        action = "attack"
        if smart:
            if b["turn"] % 3 == 2:
                action = (
                    "skill2" if not b["cooldowns"].get("skill2") and b["energy"] >= 12 else "guard"
                )
            elif not b["cooldowns"].get("skill1") and b["energy"] >= 12:
                action = "skill1"
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
        "# Phase 1 balance baseline",
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


if __name__ == "__main__":
    print(report(), end="")
