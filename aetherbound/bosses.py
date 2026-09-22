"""Shared HP around personal combat; called inside the player's SQLite transaction."""

import json
import time

from . import engine as game
from .content import MONSTERS


def enabled(c, guild):
    row = c.execute("SELECT data FROM settings WHERE guild=?", (guild,)).fetchone()
    return not row or json.loads(row[0]).get("features", {}).get("shared_bosses", True)


def get(c, guild, pool_id):
    row = c.execute("SELECT * FROM boss_pools WHERE id=? AND guild=?", (pool_id, guild)).fetchone()
    if not row:
        raise game.RuleError("This shared boss is no longer available.")
    return row


def create(c, pool_id, guild, monster, expires):
    hp = int((80 + 30 * MONSTERS[monster]["level"]) * 3) * 2
    c.execute(
        "INSERT INTO boss_pools VALUES(?,?,?,?,?,?,0)", (pool_id, guild, monster, hp, hp, expires)
    )


def join(p, c, guild, user, pool_id, now=None):
    now = time.time() if now is None else now
    pool = get(c, guild, pool_id)
    if not enabled(c, guild):
        raise game.RuleError("Shared bosses are temporarily disabled.")
    if pool["hp"] <= 0 or pool["expires"] <= now:
        raise game.RuleError("This shared boss was defeated or expired.")
    if p["run"] or p["tutorial"] < 6:
        raise game.RuleError("Finish the tutorial and finish or abandon your dungeon first.")
    if c.execute("SELECT 1 FROM boss_members WHERE pool=? AND user=?", (pool_id, user)).fetchone():
        raise game.RuleError(
            "One attempt per shared boss. Use aether resume for an active attempt, or aether boss claim after victory."
        )
    if c.execute("SELECT COUNT(*) FROM boss_members WHERE pool=?", (pool_id,)).fetchone()[0] >= 20:
        raise game.RuleError("This encounter already has 20 participants.")
    b = game.begin(p, pool["monster"])
    b["shared_pool"] = pool_id
    c.execute("INSERT INTO boss_members VALUES(?,?,?,?,0,0)", (pool_id, guild, user, p["level"]))
    return b


def act(p, c, guild, user, battle_id, turn, action, rng, now=None):
    now = time.time() if now is None else now
    b = p.get("battle")
    if not b or b["id"] != battle_id or b["turn"] != turn:
        raise game.RuleError(
            "That turn already resolved. Use the newest controls or aether resume."
        )
    pool_id = b["shared_pool"]
    pool = c.execute("SELECT * FROM boss_pools WHERE id=? AND guild=?", (pool_id, guild)).fetchone()
    if not pool or pool["hp"] <= 0 or pool["expires"] <= now:
        p["battle"] = None
        p["last_result"] = (
            "The shared boss was defeated! Use aether boss claim " + pool_id
            if pool and pool["hp"] <= 0
            else "The shared boss expired. No rewards; your character is safe."
        )
        return p["last_result"]
    if action != "flee" and not enabled(c, guild):
        raise game.RuleError(
            "Shared boss combat is paused. You may Flee; rewards already earned remain claimable."
        )
    before = b["enemy_hp"]
    result = game.act(p, battle_id, turn, action, rng)
    damage = min(pool["hp"], max(0, before - b["enemy_hp"]))
    c.execute(
        "UPDATE boss_members SET damage=damage+? WHERE pool=? AND user=?", (damage, pool_id, user)
    )
    remaining = pool["hp"] - damage
    c.execute(
        "UPDATE boss_pools SET hp=?, defeated=? WHERE id=?",
        (remaining, now if remaining == 0 else 0, pool_id),
    )
    if remaining == 0:
        c.execute("UPDATE spawns SET claimed=1 WHERE id=?", (pool_id,))
        p["battle"] = None
        result = (
            "Shared boss defeated! Everyone who dealt at least 5% may claim once: aether boss claim "
            + pool_id
        )
    else:
        result += f"\nShared HP: {remaining:,}/{pool['maxhp']:,}. Your damage stays credited even if your attempt ends."
        if p["battle"]:
            p["battle"]["log"].append(
                f"Shared HP: {remaining:,}/{pool['maxhp']:,} (at your last action)."
            )
    if not p["battle"]:
        p["last_result"] = result
    return result


def claim(p, c, guild, user, pool_id, rng, now=None):
    now = time.time() if now is None else now
    pool = get(c, guild, pool_id)
    member = c.execute(
        "SELECT * FROM boss_members WHERE pool=? AND user=?", (pool_id, user)
    ).fetchone()
    if pool["hp"] > 0 or not pool["defeated"]:
        raise game.RuleError("Rewards unlock only when the shared boss is defeated before expiry.")
    if now > pool["expires"] + 7 * 86400:
        raise game.RuleError("The seven-day claim window has ended.")
    if not member or member["claimed"] or member["damage"] * 20 < pool["maxhp"]:
        raise game.RuleError(
            "Already claimed or below the 5% damage requirement. No rewards granted."
        )
    b = p.get("battle")
    if b and b.get("shared_pool") != pool_id:
        raise game.RuleError("Finish your current battle before claiming boss rewards.")
    if len(p.get("unclaimed_loot", [])) > 18:
        raise game.RuleError("Free loot overflow space first; this reward may contain two items.")
    p["battle"] = None
    share = min(1, 2 * member["damage"] / pool["maxhp"])
    result = game.reward(p, {"monster": pool["monster"], "practice": False}, rng, share=share)
    c.execute("UPDATE boss_members SET claimed=1 WHERE pool=? AND user=?", (pool_id, user))
    p["last_result"] = f"Shared boss reward ({share:.0%} gold/EXP rate). " + result
    return p["last_result"]
