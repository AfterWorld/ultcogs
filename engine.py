"""Small pure functions for matching, season boundaries, and scoring."""
import re
import unicodedata
from datetime import datetime, timedelta, timezone


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text).casefold())


def season(now, offset, october_only):
    local = now.astimezone(timezone(timedelta(minutes=offset)))
    return str(local.year) if not october_only or local.month == 10 else None


def matches(text, candy):
    return normalize(text) in {normalize(a) for a in candy["aliases"]}


def tally(record, candy_id, points, milestones):
    record["points"] += points
    record["caught"] += 1
    bag = record["bag"]
    bag[candy_id] = bag.get(candy_id, 0) + 1
    earned = []
    for key, reward in sorted(milestones.items(), key=lambda item: int(item[0])):
        count = bag.get(reward["candy"], 0) if reward["candy"] != "any" else record["caught"]
        if count >= reward["count"] and key not in record["earned"]:
            record["earned"].append(key)
            record["points"] += reward["bonus"]
            earned.append(reward)
    return earned
