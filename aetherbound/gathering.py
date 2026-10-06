"""Active gathering rules for Aetherbound."""

import time

from .engine import RuleError, idle

SKILLS = {
    "foraging": {"label": "Foraging", "loot": "essence", "base": 0.65},
    "mining": {"label": "Mining", "loot": "iron", "base": 0.60},
    "thieving": {"label": "Thieving", "loot": "gold", "base": 0.55},
}
REGIONS = {
    "glimmerwood": {"label": "Glimmerwood", "level": 1, "bonus": 1},
    "embervein": {"label": "Embervein", "level": 8, "bonus": 2},
}
COOLDOWN = 5


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
    amount = successes * node["bonus"] + bonus
    xp = attempts * 10 + successes * 8
    state["xp"] += xp
    while state["level"] < 20 and state["xp"] >= xp_needed(state["level"]):
        state["xp"] -= xp_needed(state["level"])
        state["level"] += 1
    if state["level"] >= 20:
        state["xp"] = 0
    player["last_gather_at"] = now

    if SKILLS[skill]["loot"] == "gold":
        player["gold"] += amount * 3
        reward = {"gold": amount * 3}
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
    }
