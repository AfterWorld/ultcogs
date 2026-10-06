"""Active gathering rules for Aetherbound."""

import time

from .economy import utc_day\nfrom .engine import RuleError, idle

SKILLS = {
    "foraging": {"label": "Foraging", "loot": "essence", "base": 0.65},
    "mining": {"label": "Mining", "loot": "iron", "base": 0.60},
    "thieving": {"label": "Thieving", "loot": "gold", "base": 0.55},
}
REGIONS = {
    "glimmerwood": {
        "label": "Glimmerwood",
        "level": 1,
        "bonus": 1,
        "item_cap": 2,
        "gold_cap": 5,
    },
    "embervein": {
        "label": "Embervein",
        "level": 8,
        "bonus": 2,
        "item_cap": 3,
        "gold_cap": 8,
    },
}
COOLDOWN = 15
DAILY_SESSIONS = 8


def xp_needed(level):
    return 60 + 40 * level


def resolve(player, skill, region, rng, now=None):
    """Resolve one short, active gathering session and persist its progression."""
    idle(player)
    if player.get("tutorial", 0) < 6:
        raise RuleError("Finish the tutorial before gathering.")
    skill, region = skill.lower(), region.lower()
    if skill not in SKILLS:
        raise RuleError("Choose foraging, mining, or thieving.")
    if region not in REGIONS:
        raise RuleError("Choose glimmerwood or embervein.")
    node = REGIONS[region]
    if player["level"] < node["level"]:
        raise RuleError(f"{node['label']} gathering unlocks at hero level {node['level']}.")

    now = time.time() if now is None else now
    day = utc_day(now)
    used = player.get("gathering_day") == day and player.get("gathering_used", 0) or 0
    if used >= DAILY_SESSIONS:
        raise RuleError(
            f"You've used all {DAILY_SESSIONS} gathering sessions today. "
            "Your allotment resets at 00:00 UTC."
        )
    remaining = COOLDOWN - (now - player.get("last_gather_at", 0))
    if remaining > 0:
        raise RuleError(f"Take a breath—gather again in {remaining:.0f} seconds.")

    skills = player.setdefault("gathering", {})
    state = skills.setdefault(skill, {"level": 1, "xp": 0})
    old_level = state["level"]
    attempts = min(7, 3 + (old_level - 1) // 4)
    chance = min(0.85, SKILLS[skill]["base"] + 0.01 * (old_level - 1))
    successes = sum(rng.random() < chance for _ in range(attempts))
    bonus = sum(rng.random() < 0.12 for _ in range(successes))
    amount = min(node["item_cap"], successes * node["bonus"] + bonus)
    xp = attempts * 10 + successes * 8
    state["xp"] += xp
    while state["level"] < 20 and state["xp"] >= xp_needed(state["level"]):
        state["xp"] -= xp_needed(state["level"])
        state["level"] += 1
    if state["level"] >= 20:
        state["xp"] = 0
    player["last_gather_at"] = now
    player["gathering_day"] = day
    player["gathering_used"] = used + 1

    if SKILLS[skill]["loot"] == "gold":
        gold = min(node["gold_cap"], (successes + bonus) * 2)
        player["gold"] += gold
        reward = {"gold": gold}
    else:
        material = SKILLS[skill]["loot"]
        player.setdefault("materials", {})[material] = (
            player.setdefault("materials", {}).get(material, 0) + amount
        )
        reward = {material: amount}

    return {
        "skill": skill,
        "region": region,
        "attempts": attempts,
        "successes": successes,
        "reward": reward,
        "xp": xp,
        "old_level": old_level,
        "level": state["level"],
        "skill_xp": state["xp"],
        "next_xp": 0 if state["level"] >= 20 else xp_needed(state["level"]),
        "sessions_left": DAILY_SESSIONS - player["gathering_used"],
    }
