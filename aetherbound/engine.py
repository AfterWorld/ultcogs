"""Discord-free game rules. All mutations run inside a Store transaction."""

import random
import re
import uuid

from .content import ATTRS, CLASSES, INTENTS, MONSTERS, QUESTS, SLOTS
from .loot import BOSS_DROPS, RARITIES, UNIQUES, item_name, rarity_label, roll_rarity


class RuleError(ValueError):
    pass


def uid():
    return uuid.uuid4().hex[:12]


def xp_needed(level):
    return 80 + 35 * level + 8 * level * level


def grant_xp(p, amount):
    if p["level"] >= 20:
        p["xp"] = 0
        return
    p["xp"] += max(0, int(amount))
    while p["level"] < 20 and p["xp"] >= xp_needed(p["level"]):
        p["xp"] -= xp_needed(p["level"])
        p["level"] += 1
        p["points"] += 2
    if p["level"] == 20:
        p["xp"] = 0


def make_item(slot, level=1, rarity="common", rng=None, name=None, unique=None, twohand=False):
    rng = rng or random.Random()
    level = max(1, min(20, level))
    rank = RARITIES[rarity]["rank"]
    bonuses = {}
    # A fixed affix budget, distributed rather than multiplied per attribute.
    for _ in range(min(4, rank - 1)):
        stat = rng.choice(ATTRS)
        bonuses[stat] = bonuses.get(stat, 0) + 1 + level // 5
    power = 2 + level + rank
    item_id = uid()
    return dict(
        id=item_id,
        name=name or item_name(slot, rarity, item_id),
        slot=slot,
        level=level,
        rarity=rarity,
        power=power,
        bonuses=bonuses,
        upgrade=0,
        unique=unique,
        twohand=twohand,
        sockets=[],
    )


def new_player(name, cls):
    if cls not in CLASSES:
        raise RuleError("Choose vanguard, strider, or arcanist.")
    if not 2 <= len(name.strip()) <= 32 or re.search(r"[@<>\n\r]", name):
        raise RuleError("Use a name of 2–32 characters without mentions or line breaks.")
    weapon = make_item("main", name=CLASSES[cls]["weapon"])
    off = make_item("off", name="Apprentice Focus" if cls == "arcanist" else "Traveler Buckler")
    return dict(
        name=name.strip(),
        cls=cls,
        level=1,
        xp=0,
        gold=0,
        points=0,
        attrs={a: 0 for a in ATTRS},
        inventory={i["id"]: i for i in (weapon, off)},
        equipped={},
        materials={},
        potions=2,
        tutorial=0,
        trained=False,
        forged=[],
        wins=0,
        boss_wins=0,
        dungeons=0,
        quests=[],
        accepted_quests={},
        battle=None,
        run=None,
        appearance="A new adventurer of Hoshifall",
        last_result="",
    )


def stats(p):
    attrs = {a: 4 + p["level"] + p["attrs"][a] for a in ATTRS}
    weapon = armor = 0
    uniques = set()
    for item_id in set(p["equipped"].values()):
        i = p["inventory"][item_id]
        for a, value in i["bonuses"].items():
            attrs[a] += value
        power = i["power"] + i["upgrade"] * 2
        if i["slot"] == "main":
            weapon += power * (1.5 if i["twohand"] else 1)
        else:
            armor += power
        if i["unique"]:
            uniques.add(i["unique"])
    return dict(
        hp=90 + p["level"] * 10 + attrs["vitality"] * 3,
        attack=12 + p["level"] * 2 + attrs[CLASSES[p["cls"]]["stat"]] * 1.5 + weapon,
        armor=min(100, armor + attrs["vitality"] * 0.5),
        crit=min(0.35, 0.05 + attrs["dexterity"] * 0.002),
        energy=min(80, 40 + attrs["willpower"]),
        uniques=uniques,
    )


def idle(p):
    if p["battle"]:
        raise RuleError("Finish or flee your current battle first.")


def item(p, item_id):
    if item_id not in p["inventory"]:
        raise RuleError("That item is not in your inventory. Use its item ID.")
    return p["inventory"][item_id]


def equip(p, item_id):
    return equip_many(p, [item_id])


def equip_many(p, item_ids):
    """Validate the final loadout before changing gear or granting tutorial rewards."""
    idle(p)
    if not 1 <= len(item_ids) <= len(SLOTS):
        raise RuleError("Choose 1–11 item IDs from your inventory.")
    if len(set(item_ids)) != len(item_ids):
        raise RuleError("Each item ID should appear only once. No equipment changed.")
    items = [item(p, key) for key in item_ids]
    slots = [i["slot"] for i in items]
    if len(set(slots)) != len(slots):
        raise RuleError(
            "Choose only one item per slot. Rings use ring1 and ring2. No equipment changed."
        )
    for i in items:
        if i["level"] > p["level"]:
            raise RuleError(f"{i['name']} requires level {i['level']}. No equipment changed.")
    loadout = dict(p["equipped"])
    loadout.update({i["slot"]: i["id"] for i in items})
    main = p["inventory"].get(loadout.get("main"), {})
    removed = None
    if main.get("twohand"):
        if "off" in slots:
            raise RuleError(
                "A two-handed weapon cannot be used with an off-hand item. No equipment changed."
            )
        removed = loadout.pop("off", None)
    p["equipped"] = loadout
    advance_tutorial(p)
    result = "\n".join(f"Equipped {i['name']} → {i['slot']}." for i in items)
    if removed:
        result += "\nOff-hand returned to your inventory (two-handed weapon)."
    return result


def advance_tutorial(p):
    stage = p["tutorial"]
    if stage == 0 and "main" in p["equipped"]:
        p["tutorial"] = 1
    elif stage == 1 and p["trained"]:
        p["tutorial"] = 2
        for slot in ("head", "chest", "hands", "legs", "feet", "neck"):
            i = make_item(slot, name=f"Traveler {slot.title()}")
            p["inventory"][i["id"]] = i
        p["gold"] += 60
        p["materials"]["iron"] = p["materials"].get("iron", 0) + 4
        p["materials"]["essence"] = p["materials"].get("essence", 0) + 2
    elif stage == 2 and "chest" in p["equipped"]:
        p["tutorial"] = 3
    elif stage == 3 and p["forged"]:
        p["tutorial"] = 4
    elif stage == 4 and any(x in p["equipped"].values() for x in p["forged"]):
        p["tutorial"] = 5
    elif stage == 5 and p["wins"]:
        p["tutorial"] = 6
        i = make_item("relic", name="Wayfarer Star", unique="wayfarer")
        p["inventory"][i["id"]] = i
        p["gold"] += 100
        p["potions"] += 2
    if p["tutorial"] != stage:
        advance_tutorial(p)


def forge(p, slot, boss=None, twohand=False):
    idle(p)
    if p["tutorial"] < 3:
        raise RuleError(
            "Equip your training weapon and armor, then follow aether tutorial before forging."
        )
    if p["tutorial"] < 5 and (slot != "ring1" or boss or twohand or p["forged"]):
        raise RuleError("Your first recipe is ring1. Equip that ring to finish the forging lesson.")
    if slot not in SLOTS:
        raise RuleError("Valid slots: " + ", ".join(SLOTS))
    if twohand and slot != "main":
        raise RuleError("Only main-hand weapons can be two-handed.")
    costs = {"iron": 4, "essence": 2}
    gold = 30 + 5 * (p["level"] - 1)
    unique = None
    if boss:
        if boss not in ("tsukara", "raizen"):
            raise RuleError("Boss recipes: tsukara or raizen.")
        costs[MONSTERS[boss]["material"]] = 2
        unique = "spiritward" if boss == "tsukara" else "emberblade"
        gold *= 2
    if p["gold"] < gold or any(p["materials"].get(k, 0) < v for k, v in costs.items()):
        raise RuleError(f"Requires {gold} gold and {costs}.")
    if len(p["inventory"]) >= 200:
        raise RuleError("Inventory full (200). Salvage an item first.")
    p["gold"] -= gold
    for k, v in costs.items():
        p["materials"][k] -= v
    i = make_item(slot, p["level"], "rare" if boss else "uncommon", unique=unique, twohand=twohand)
    if boss:
        i["name"] = f"{boss.title()}’s {item_name(slot, 'common', i['id'])}"
    p["inventory"][i["id"]] = i
    p["forged"].append(i["id"])
    advance_tutorial(p)
    return i


def upgrade(p, item_id):
    idle(p)
    if p["tutorial"] < 5:
        raise RuleError("Finish the forging lesson before spending starter materials on upgrades.")
    i = item(p, item_id)
    cost = 25 * (i["upgrade"] + 1)
    if i["upgrade"] >= 5:
        raise RuleError("Phase 1 upgrade cap is +5.")
    if p["gold"] < cost or p["materials"].get("iron", 0) < 2:
        raise RuleError(f"Requires {cost} gold and 2 iron. Guaranteed success.")
    p["gold"] -= cost
    p["materials"]["iron"] -= 2
    i["upgrade"] += 1
    return f"Upgraded {i['name']} to +{i['upgrade']}."


def salvage(p, item_id):
    idle(p)
    if item_id in p["equipped"].values():
        raise RuleError("Unequip that item first.")
    i = item(p, item_id)
    if p["tutorial"] < 6 and (i["slot"] in ("main", "chest") or item_id in p["forged"]):
        raise RuleError("Keep tutorial equipment until graduation.")
    del p["inventory"][item_id]
    p["materials"]["iron"] = p["materials"].get("iron", 0) + 2
    p["materials"]["essence"] = p["materials"].get("essence", 0) + 1
    return "Salvaged for 2 iron and 1 essence."


def begin(p, monster_key, practice=False, carry=None):
    idle(p)
    if not practice and p["tutorial"] < 5:
        raise RuleError("Finish the training and forging tutorial first: aether tutorial.")
    if len(p.get("unclaimed_loot", [])) >= 20:
        raise RuleError("Claim your loot overflow before starting another battle: aether loot.")
    m = MONSTERS[monster_key]
    if not practice and p["level"] < m["level"] - 4:
        raise RuleError(
            f"Requires at least level {max(1, m['level'] - 4)}. This enemy is level {m['level']}."
        )
    s = stats(p)
    level = m["level"]
    mhp = (80 + 30 * level) * (3.0 if m["boss"] else 1)
    p["battle"] = dict(
        id=uid(),
        monster=monster_key,
        hp=carry if carry is not None else s["hp"],
        maxhp=s["hp"],
        enemy_hp=int(mhp),
        enemy_maxhp=int(mhp),
        energy=s["energy"],
        turn=0,
        cooldowns={},
        effects={},
        used=[],
        practice=practice,
        message=0,
        channel=0,
        last="",
        log=["Read intent before choosing an action."],
    )
    if practice:
        p["battle"]["enemy_hp"] = p["battle"]["enemy_maxhp"] = 130
    return p["battle"]


def choose_monster(p, region, rng):
    if region not in ("glimmerwood", "embervein"):
        raise RuleError("Regions: glimmerwood or embervein.")
    if region == "embervein" and p["level"] < 8:
        raise RuleError("Embervein unlocks at level 8.")
    options = [
        k
        for k, m in MONSTERS.items()
        if m["region"] == region and not m["boss"] and m["level"] <= p["level"] + 2
    ]
    # Prefer relevant targets; fixed levels still allow revisiting lower content.
    weights = [1 / (1 + abs(MONSTERS[k]["level"] - p["level"])) for k in options]
    return rng.choices(options, weights=weights)[0]


def intent(b):
    m = MONSTERS[b["monster"]]
    if b["turn"] % 3 == 2:
        return INTENTS[m["behavior"]]
    return "A measured strike. Recover energy with a basic attack or prepare your skills."


def reward(p, b, rng):
    if b["practice"]:
        p["trained"] = all(a in b["used"] for a in ("attack", "guard", "skill"))
        advance_tutorial(p)
        return (
            "Training passed! Armor, gold and materials awarded."
            if p["trained"]
            else "Practice again: use Attack, Guard and a Skill before winning."
        )
    m = MONSTERS[b["monster"]]
    scale = max(0.1, min(1, (m["level"] + 2) / p["level"]))
    if p["level"] - m["level"] >= 5:
        scale *= 0.3
    xp = int((24 + m["level"] * 8) * (2.5 if m["boss"] else 1) * scale)
    gold = int((12 + m["level"] * 3) * (2 if m["boss"] else 1) * scale)
    grant_xp(p, xp)
    p["gold"] += gold
    p["wins"] += 1
    p["boss_wins"] += int(m["boss"])
    kills = p.setdefault("kills", {})
    kills[b["monster"]] = kills.get(b["monster"], 0) + 1
    for mat in ("iron", "essence", m["material"]):
        p["materials"][mat] = p["materials"].get(mat, 0) + 1
    level = min(p["level"], m["level"])
    rarity = roll_rarity(level, m["boss"], rng)
    if m["boss"]:
        slot, name = rng.choice(BOSS_DROPS[b["monster"]])
        # Boss signatures are at least Rare; top tiers still obey level gates.
        if RARITIES[rarity]["rank"] < 3:
            rarity = "rare"
        drop = make_item(slot, level, rarity, rng, name=name)
    else:
        drop = make_item(rng.choice(SLOTS), level, rarity, rng)
    drops = [drop]
    if b["monster"] in UNIQUES and rng.random() < (0.03 if m["boss"] else 0.005):
        spec = UNIQUES[b["monster"]]
        drops.append(
            make_item(spec["slot"], level, "unique", rng, name=spec["name"], unique=spec["effect"])
        )
    messages = []
    for drop in drops:
        if len(p["inventory"]) < 200:
            p["inventory"][drop["id"]] = drop
            messages.append(
                f"{rarity_label(drop['rarity'])} **{drop['name']}** — ID `{drop['id']}`"
            )
        else:
            p.setdefault("unclaimed_loot", []).append(drop)
            messages.append(
                f"{drop['name']} is waiting in your loot overflow. Use aether loot after freeing bag space."
            )
    loot = "Loot: " + "\n".join(messages)
    advance_tutorial(p)
    return f"Victory! +{xp} EXP, +{gold} gold, materials. {loot}"


def act(p, battle_id, turn, action, rng):
    b = p["battle"]
    if not b or b["id"] != battle_id or b["turn"] != turn:
        raise RuleError(
            "That turn has already resolved. Use the newest battle message or aether resume."
        )
    if action not in ("attack", "guard", "skill1", "skill2", "skill3", "potion", "flee"):
        raise RuleError("Unknown action.")
    if action == "flee":
        p["battle"] = p["run"] = None
        p["last_result"] = "Retreated safely. No encounter rewards."
        return p["last_result"]
    s = stats(p)
    m = MONSTERS[b["monster"]]
    heavy = b["turn"] % 3 == 2
    log = []
    guarding = action == "guard"
    interrupt = action == "skill2"
    mult = 1.0
    if action.startswith("skill"):
        if b["cooldowns"].get(action, 0):
            raise RuleError("That skill is cooling down.")
        if b["energy"] < 12:
            raise RuleError("Not enough energy. Attack or guard to recover.")
        b["energy"] -= 12
        b["cooldowns"][action] = 3
        b["used"].append("skill")
        mult = 1.65 if action == "skill1" else 1.05
        if action == "skill3":
            b["effects"]["shield"] = int(s["hp"] * 0.20)
            mult = 0.45
            guarding = True
        if action == "skill2":
            b["effects"]["exposed"] = 2
        if p["cls"] == "strider":
            if action == "skill1":
                mult = 1.35
                b["effects"]["enemy_bleed"] = 2
            elif action == "skill2":
                b["effects"]["exposed"] = 3
            else:
                b["effects"]["riposte"] = True
        elif p["cls"] == "arcanist":
            if action == "skill1":
                mult = 1.85
            elif action == "skill2":
                mult = 0.8
                b["effects"]["chill"] = 2
            else:
                b["effects"]["shield"] = int(s["hp"] * 0.30)
        elif action == "skill3":
            b["effects"]["shield"] = int(s["hp"] * 0.35)
    elif action == "potion":
        if p["potions"] <= 0:
            raise RuleError("No potions. Buy one in town: aether potion.")
        p["potions"] -= 1
        b["hp"] = min(b["maxhp"], b["hp"] + int(b["maxhp"] * 0.40))
        mult = 0
    elif action == "guard":
        mult = 0
        b["used"].append("guard")
        b["energy"] = min(s["energy"], b["energy"] + 10)
    else:
        b["used"].append("attack")
        b["energy"] = min(s["energy"], b["energy"] + 7)
    dmg = int(s["attack"] * mult * rng.uniform(0.9, 1.1))
    if mult and action != "skill3" and b["effects"].pop("riposte", False):
        dmg = int(dmg * 1.25)
    if b["effects"].get("exposed", 0):
        dmg = int(dmg * 1.20)
    if m["behavior"] == "armor" and not heavy and not interrupt:
        dmg = int(dmg * 0.65)
    if b["effects"].pop("blind", False) and rng.random() < 0.25:
        dmg = 0
        log.append("Blinding dust caused a miss.")
    if dmg and rng.random() < s["crit"]:
        dmg = int(dmg * 1.5)
        log.append("Critical!")
    if "emberblade" in s["uniques"] and dmg:
        dmg += 3  # Unique effect occurs once, regardless of equipped copies.
    b["enemy_hp"] = max(0, b["enemy_hp"] - dmg)
    log.append(f"You dealt {dmg} damage.")
    if b["effects"].get("enemy_bleed", 0):
        bleed = max(2, int(s["attack"] * 0.12))
        b["enemy_hp"] = max(0, b["enemy_hp"] - bleed)
        b["effects"]["enemy_bleed"] -= 1
        log.append(f"Enemy bleeds for {bleed}.")
    if b["enemy_hp"] <= 0:
        result = reward(p, b, rng)
        p["battle"] = None
        if p["run"] and not b["practice"]:
            p["run"]["room"] += 1
            p["run"]["hp"] = b["hp"]
            if p["run"]["room"] >= 4:
                p["dungeons"] += 1
                p["gold"] += 60
                p["run"] = None
                result += " Hollow Trail cleared! +60 gold."
            else:
                result += " Room cleared. Continue with aether dungeon."
        p["last_result"] = result
        return result
    incoming = (8 + m["level"] * 2.1) * (1.3 if m["boss"] else 1)
    if b["effects"].get("chill", 0):
        incoming *= 0.8
        b["effects"]["chill"] -= 1
    if heavy:
        if interrupt:
            incoming *= 0.35
            log.append("You interrupted the special attack!")
        else:
            incoming *= 1.8
            behavior = m["behavior"]
            if behavior in ("bleed", "burn", "roots"):
                b["effects"]["dot"] = 2
            if behavior == "dust":
                b["effects"]["blind"] = True
            if behavior == "drain":
                b["enemy_hp"] = min(b["enemy_maxhp"], b["enemy_hp"] + int(incoming * 0.5))
            if behavior == "absorb":
                incoming += b["effects"].pop("shield", 0) * 0.5
            if behavior in ("overheat", "armor"):
                b["effects"]["exposed"] = 3
    if m["behavior"] == "counter" and b["last"] == action and mult:
        incoming *= 1.4
        log.append("The Ronin countered your repeated action.")
    if m["boss"] and b["enemy_hp"] < b["enemy_maxhp"] * 0.5:
        incoming *= 1.15
        log.append("Boss phase II!")
    armor = s["armor"]
    if m["behavior"] == "alternate" and b["turn"] % 2:
        armor *= 0.5
        log.append("The mask's magical strike pierces half your armor.")
    incoming *= 100 / (100 + armor)
    if guarding:
        incoming *= 0.35
    if "spiritward" in s["uniques"] and guarding:
        incoming *= 0.85
    if "wayfarer" in s["uniques"] and action == "guard":
        b["hp"] = min(b["maxhp"], b["hp"] + 3)
    shield = b["effects"].pop("shield", 0)
    incoming = max(1, int(incoming) - shield)
    if b["practice"]:
        incoming = min(4, incoming)
    b["hp"] = max(0, b["hp"] - incoming)
    log.append(f"Enemy dealt {incoming} damage.")
    if b["effects"].get("dot", 0):
        b["hp"] = max(0, b["hp"] - max(2, m["level"] // 2))
        b["effects"]["dot"] -= 1
        log.append("Lingering damage ticks.")
    b["effects"]["exposed"] = max(0, b["effects"].get("exposed", 0) - 1)
    b["cooldowns"] = {k: max(0, v - 1) for k, v in b["cooldowns"].items()}
    b["turn"] += 1
    b["last"] = action
    b["log"] = log
    if b["hp"] <= 0 or b["turn"] >= 80:
        p["battle"] = p["run"] = None
        p["last_result"] = "Rescued to Hoshifall. No EXP or equipment lost; no victory rewards."
        return p["last_result"]
    return "\n".join(log)


def objective_total(p, key):
    if key == "guardian":
        return p.get("kills", {}).get("tsukara", 0)
    return p[QUESTS[key]["field"]]


def accept_quest(p, key):
    idle(p)
    if key not in QUESTS:
        raise RuleError("Unknown quest. Use aether quests to see the board.")
    accepted = p.setdefault("accepted_quests", {})
    if key in p["quests"] or key in accepted:
        raise RuleError("That quest is already accepted or claimed.")
    accepted[key] = objective_total(p, key)
    return f"Accepted **{QUESTS[key]['name']}**. New victories now count toward this quest."


def claim_quest(p, key):
    idle(p)
    if key not in QUESTS:
        raise RuleError("Unknown quest.")
    if key not in p.get("accepted_quests", {}):
        raise RuleError(f"Accept this quest first: aether quests accept {key}")
    q = QUESTS[key]
    if key in p["quests"] or quest_progress(p, key) < q["goal"]:
        raise RuleError("Quest already claimed or objective incomplete.")
    p["quests"].append(key)
    p["gold"] += q["gold"]
    grant_xp(p, q["xp"])
    return f"Claimed {q['name']}: {q['gold']} gold, {q['xp']} EXP."


def quest_progress(p, key):
    if key in p["quests"]:
        return QUESTS[key]["goal"]
    baseline = p.get("accepted_quests", {}).get(key)
    return max(0, objective_total(p, key) - baseline) if baseline is not None else 0


def claim_loot(p):
    idle(p)
    waiting = p.get("unclaimed_loot", [])
    count = min(200 - len(p["inventory"]), len(waiting))
    if count <= 0:
        raise RuleError(
            "No overflow loot to collect, or your bag is full. Salvage unwanted gear first."
        )
    for i in waiting[:count]:
        p["inventory"][i["id"]] = i
    p["unclaimed_loot"] = waiting[count:]
    return f"Collected {count} items. {len(p['unclaimed_loot'])} still waiting."


def tutorial(p, prefix="."):
    """One actionable lesson using this character's real item IDs."""
    cmd = f"{prefix}aether"
    stage = p["tutorial"]

    def equip_command(slots=None, ids=None):
        keys = (
            ids
            if ids is not None
            else [
                next((i["id"] for i in p["inventory"].values() if i["slot"] == slot), None)
                for slot in slots
            ]
        )
        keys = [k for k in keys if k in p["inventory"] and k not in p["equipped"].values()]
        return f"`{cmd} equip {' '.join(keys)}`" if keys else f"`{cmd} inventory`"

    lessons = [
        (
            "Equip your starter gear",
            "Your weapon and off-hand are already in your bag. Copy this command to wear both:",
            equip_command(["main", "off"]),
            "Items automatically go into their matching equipment slots.",
        ),
        (
            "Learn the battle buttons",
            "Start a safe practice battle:",
            f"`{cmd} practice`",
            "Click **Guard**, then **Attack**, then your first **Skill**. Keep attacking until you win. Use all three at least once. Reward: armor, 60 gold and forging materials.",
        ),
        (
            "Put on your armor",
            "Training earned you six armor pieces. Equip the full kit at once:",
            equip_command(["head", "chest", "hands", "legs", "feet", "neck"]),
            "Equipping the chest completes this step. Your other armor improves your defense too.",
        ),
        (
            "Forge your first ring",
            "Spend the materials you just earned to make a ring:",
            f"`{cmd} forge ring1`",
            "Cost: **4 iron + 2 essence + 30 gold**. You already have everything you need.",
        ),
        (
            "Wear your ring",
            "Forging puts the ring in your bag. Equip it to gain its bonuses:",
            equip_command(ids=p["forged"][:1]),
            "Gear can only be changed outside battle.",
        ),
        (
            "Win your first hunt",
            "You are ready for Glimmerwood:",
            f"`{cmd} explore glimmerwood`",
            "Use the combat buttons and read enemy intent. Guard charged attacks. Win to earn a **Wayfarer Star relic, 100 gold and 2 potions**, plus your battle loot.",
        ),
        (
            "Tutorial complete",
            "Your adventure begins! Equip your Wayfarer Star if it is still in your bag:",
            equip_command(
                ids=[i["id"] for i in p["inventory"].values() if i["unique"] == "wayfarer"][:1]
            ),
            f"**Hunt:** `{cmd} explore`\n**Quest rewards:** `{cmd} quests`\n**Your hero:** `{cmd} profile`\nThe Hollow Trail dungeon unlocks at level 6. Tutorial rewards are awarded once.",
        ),
    ]
    title, instruction, command, help_text = lessons[stage]
    heading = f"Step {stage + 1}/6 • {title}" if stage < 6 else title
    if p["battle"]:
        instruction = "Your battle is still active. Use its buttons, or restore them here:"
        command = f"`{cmd} resume`"
    return f"**{heading}**\n{instruction}\n\n{command}\n\n{help_text}"


def trade_offer(text):
    """Deliberately explicit grammar; no claim of understanding arbitrary conversation."""
    if len(text) > 300 or "\n" in text or re.search(r"https?://|<@|@everyone|@here", text, re.I):
        return None
    match = re.fullmatch(
        r"\s*(?:trading|trade|wtt)\s+(.{2,100}?)\s+for\s+(.{2,100}?)\s*", text, re.I
    )
    return (match[1].strip(), match[2].strip()) if match else None


def category_index(count):
    return min(count, max(1, round(count / 3))) if count else 0
