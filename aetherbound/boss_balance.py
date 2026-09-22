"""Seeded shared-pool group simulation: python -m aetherbound.boss_balance."""

import random
import sqlite3
from statistics import mean

from . import bosses
from . import engine as g
from .balance import actor
from .content import MONSTERS


def simulate(monster, size, underleveled, seed):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE settings(guild INTEGER,data TEXT);
    CREATE TABLE spawns(id TEXT,claimed INTEGER);
    CREATE TABLE boss_pools(id TEXT PRIMARY KEY,guild INTEGER,monster TEXT,hp INTEGER,maxhp INTEGER,expires REAL,defeated REAL);
    CREATE TABLE boss_members(pool TEXT,guild INTEGER,user INTEGER,level INTEGER,damage INTEGER,claimed INTEGER,PRIMARY KEY(pool,user));
    """)
    bosses.create(c, "pool", 1, monster, 2000)
    level = MONSTERS[monster]["level"] - (4 if underleveled else 0)
    players = [
        actor(("vanguard", "strider", "arcanist")[(user + seed) % 3], level, "rare", seed + user)
        for user in range(size)
    ]
    rng = random.Random(seed)
    for user, p in enumerate(players):
        bosses.join(p, c, 1, user, "pool", now=1000)
    turns = 0
    for round_number in range(80):
        for user, p in enumerate(players):
            if not p["battle"]:
                continue
            b = p["battle"]
            skill = "skill2" if b["turn"] % 3 == 2 else "skill1"
            action = (
                skill
                if not b["cooldowns"].get(skill) and b["energy"] >= g.skill_cost(p, skill)
                else "guard"
                if b["turn"] % 3 == 2
                else "attack"
            )
            bosses.act(p, c, 1, user, b["id"], b["turn"], action, rng, now=1001 + round_number)
            turns += 1
        if all(not p["battle"] for p in players):
            break
    pool = bosses.get(c, 1, "pool")
    members = c.execute("SELECT * FROM boss_members").fetchall()
    assert sum(m["damage"] for m in members) == pool["maxhp"] - pool["hp"]
    assert all(p["gold"] == 0 and p["wins"] == 0 for p in players)
    eligible = sum(m["damage"] * 20 >= pool["maxhp"] for m in members) if pool["hp"] == 0 else 0
    won = pool["hp"] == 0
    c.close()
    return won, eligible, turns


def report(samples=50):
    lines = [
        "# Shared boss balance",
        "",
        "600 seeded groups: 2 bosses × 3 party sizes × 2 level bands × 50 seeds. Rare gear, no potions, rotated class mix, interrupt policy, round-robin actions. The shared pool has twice normal boss HP; each player can contribute at most one normal boss HP bar. Damage conservation and absence of personal victory rewards are asserted in every run. This models combat, not real-world participation or response speed.",
        "",
        "| Boss | Players | Level band | Group win rate | Mean eligible claimants | Mean total actions |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for monster in ("tsukara", "raizen"):
        for size in (2, 3, 6):
            for underleveled in (False, True):
                outcomes = [simulate(monster, size, underleveled, seed) for seed in range(samples)]
                lines.append(
                    f"| {monster} | {size} | {'minimum entry' if underleveled else 'boss level'} | {mean(x[0] for x in outcomes):.1%} | {mean(x[1] for x in outcomes):.1f} | {mean(x[2] for x in outcomes):.1f} |"
                )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(report(), end="")
