"""UTC daily rewards and reproducible personal shop offers, mutated transactionally."""

import copy
import hashlib
import random
import time
from datetime import datetime, timezone

from .content import SLOTS
from .engine import RuleError, idle, make_item, uid
from .loot import RARITIES, item_name


def utc_day(now=None):
    return (
        datetime.fromtimestamp(time.time() if now is None else now, timezone.utc).date().isoformat()
    )


def payday(p, now=None):
    day = utc_day(now)
    if p["tutorial"] < 6:
        raise RuleError("Finish the tutorial to unlock daily gold.")
    if p.get("payday_day", "") >= day:
        raise RuleError("Today's gold is already claimed. Payday resets at 00:00 UTC.")
    amount = 40 + 3 * min(20, p["level"])
    p["gold"] += amount
    p["payday_day"] = day
    return f"Claimed **{amount} gold**. Next payday: 00:00 UTC. No streaks or missed-day penalties."


def shop(p, guild_id, user_id, now=None):
    day = utc_day(now)
    saved = p.get("shop", {})
    if saved.get("day", "") > day:
        raise RuleError(
            "Server clock moved backwards. Shop rotation will resume when time catches up."
        )
    if saved.get("day") == day:
        return saved
    level = p["level"]
    seed = f"aetherbound-shop-v1:{guild_id}:{user_id}:{day}"
    rng = random.Random(hashlib.sha256(seed.encode()).digest())
    tiers = [k for k, v in RARITIES.items() if k != "unique" and level >= v["level"]]
    offers = []
    # One offer of each unlocked tier, with at least three equipment offers.
    for index in range(max(3, len(tiers))):
        rarity = tiers[index % len(tiers)]
        slot = rng.choice(SLOTS)
        i = make_item(slot, level, rarity, rng)
        i["id"] = hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()[:12]
        i["name"] = item_name(slot, rarity, i["id"])
        rank = RARITIES[rarity]["rank"]
        price = (25 + 10 * level) * rank * rank
        offers.append(
            dict(code=f"{day}-{index + 1}", item=i, name=i["name"], price=price, stock=1, bought=0)
        )
    offers.extend(
        [
            dict(
                code=f"{day}-potions",
                name="Potion pouch ×3",
                price=40,
                stock=2,
                bought=0,
                potions=3,
            ),
            dict(
                code=f"{day}-materials",
                name="Forge bundle · 4 iron + 2 essence",
                price=70,
                stock=2,
                bought=0,
                materials={"iron": 4, "essence": 2},
            ),
        ]
    )
    p["shop"] = dict(day=day, level=level, offers=offers)
    return p["shop"]


def buy(p, guild_id, user_id, code, now=None):
    idle(p)
    if p["tutorial"] < 6:
        raise RuleError(
            "Finish the tutorial before shopping; keep your starter resources for training."
        )
    current = shop(p, guild_id, user_id, now)
    offer = next((o for o in current["offers"] if o["code"] == code), None)
    if not offer:
        raise RuleError(
            "That offer has expired or does not exist. Open aether shop for today's codes."
        )
    if offer["bought"] >= offer["stock"]:
        raise RuleError("You bought all of this offer's daily stock.")
    if p["gold"] < offer["price"]:
        raise RuleError(f"You need {offer['price']} gold for that offer.")
    if "item" in offer and len(p["inventory"]) >= 200:
        raise RuleError("Your bag is full. Salvage an item before buying equipment.")
    p["gold"] -= offer["price"]
    offer["bought"] += 1
    result = f"Bought **{offer['name']}** for {offer['price']} gold."
    if "item" in offer:
        i = copy.deepcopy(offer["item"])
        i["id"] = uid()
        p["inventory"][i["id"]] = i
        result += f" Item ID: `{i['id']}`."
    if "potions" in offer:
        p["potions"] += offer["potions"]
    for key, count in offer.get("materials", {}).items():
        p["materials"][key] = p["materials"].get(key, 0) + count
    return result
