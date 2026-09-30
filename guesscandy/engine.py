"""Small pure functions for matching, season boundaries, and scoring."""
import re
import unicodedata
import random
from datetime import datetime, timedelta, timezone

from .content import CANDIES, SIZES


def local_time(now, offset):
    return now.astimezone(timezone(timedelta(minutes=offset)))


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text).casefold())


def season(now, offset, october_only):
    local = local_time(now, offset)
    return str(local.year) if not october_only or local.month == 10 else None


def matches(text, candy):
    return normalize(text) in {normalize(a) for a in candy["aliases"]}


def is_finale(now, offset, enabled=True):
    local = local_time(now, offset)
    return enabled and (local.month, local.day) == (10, 31)


def eligible_candies(finale):
    return {key: candy for key, candy in CANDIES.items() if finale or not candy["finale_only"]}


def catch_points(base, size, finale=False):
    # Round half points upward, and double only the catch itself on Halloween.
    return max(1, int(base * SIZES[size]["multiplier"] + 0.5)) * (2 if finale else 1)


def cooldown_delay(base, jitter):
    fraction = jitter / 100
    return random.uniform(base * (1 - fraction), base * (1 + fraction))


def daily_goals(day):
    """Same goals for everyone; date-seeded private RNG does not affect spawns."""
    options = [
        dict(id="chocolate", label="Catch 3 chocolate candies", target=3, bonus=60),
        dict(id="fruity", label="Catch 3 fruity candies", target=3, bonus=60),
        dict(id="unique", label="Catch 4 different candies", target=4, bonus=80),
        dict(id="total", label="Catch 5 candies", target=5, bonus=80),
    ]
    return [dict(id="starter", label="Catch your first candy today", target=1, bonus=20)] + random.Random(day).sample(options, 2)


def goal_progress(goal, daily):
    bag = daily.get("bag", {})
    if goal["id"] in ("starter", "total"):
        return sum(bag.values())
    if goal["id"] == "unique":
        return len([key for key, count in bag.items() if count])
    return sum(count for key, count in bag.items() if CANDIES.get(key, {}).get("category") == goal["id"])


def tally(record, candy_id, points, milestones, *, day=None, size="regular", sets=None):
    record["points"] += points
    record["caught"] += 1
    bag = record["bag"]
    bag[candy_id] = bag.get(candy_id, 0) + 1
    sizes = record.setdefault("sizes", {})
    sizes[size] = sizes.get(size, 0) + 1
    earned = []
    for key, reward in sorted(milestones.items(), key=lambda item: int(item[0])):
        count = bag.get(reward["candy"], 0) if reward["candy"] != "any" else record["caught"]
        if count >= reward["count"] and key not in record["earned"]:
            record["earned"].append(key)
            record["points"] += reward["bonus"]
            earned.append(reward)
    if sets is not None:
        completed = record.setdefault("sets", [])
        for key, reward in sets.items():
            if key not in completed and all(bag.get(candy, 0) for candy in reward["candies"]):
                completed.append(key)
                record["points"] += reward["bonus"]
                label = f"Set complete: {reward['label']}"
                if reward.get("prize"):
                    label += f" — {reward['prize']} (staff-delivered)"
                earned.append(dict(label=label, bonus=reward["bonus"]))
    if day:
        daily = record.get("daily")
        if not daily or daily["date"] != day:
            daily = record["daily"] = dict(date=day, bag={}, earned=[])
        daily["bag"][candy_id] = daily["bag"].get(candy_id, 0) + 1
        for goal in daily_goals(day):
            if goal["id"] not in daily["earned"] and goal_progress(goal, daily) >= goal["target"]:
                daily["earned"].append(goal["id"])
                record["points"] += goal["bonus"]
                earned.append(dict(label=f"Daily goal: {goal['label']}", bonus=goal["bonus"]))
    return earned


def standings(records):
    return [dict(user=uid, points=record["points"], caught=record["caught"])
            for uid, record in sorted(records.items(), key=lambda item: (-item[1]["points"], -item[1]["caught"], int(item[0])))]
