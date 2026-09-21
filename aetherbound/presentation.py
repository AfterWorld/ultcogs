"""Player-facing embeds shared by commands and persistent channel guides."""

import re

import discord

from . import engine as game
from .content import CLASSES, GEAR_SETS, MECHANICS, RUNES, SLOTS
from .loot import rarity_label

COLOR = 0x836FFF
SLOT_NAMES = dict(
    zip(
        SLOTS,
        (
            "Main hand",
            "Off hand",
            "Head",
            "Chest",
            "Hands",
            "Legs",
            "Feet",
            "Neck",
            "Ring I",
            "Ring II",
            "Relic",
        ),
    )
)


def command_boxes(text, prefix):
    """Box only complete command examples, leaving IDs and prose inline."""
    pattern = r"`(" + re.escape(prefix) + r"(?:aether|ae|a)(?: [^`\n]+)?)`"
    text = re.sub(pattern, lambda m: "\n```text\n" + m[1] + "\n```\n", text)
    return re.sub(r"\n```\n\s*(?:·\s*)?\n```text\n", "\n", text).strip()


def tidy_commands(embed, prefix):
    if embed.description:
        embed.description = command_boxes(embed.description, prefix)
    for n, field in enumerate(embed.fields):
        embed.set_field_at(
            n, name=field.name, value=command_boxes(field.value, prefix), inline=field.inline
        )
    return embed


def customization_detail(i):
    lines = []
    if i.get("set_id") in GEAR_SETS:
        lines.append("Set: " + GEAR_SETS[i["set_id"]]["name"])
    runes = i.get("sockets", [])
    if runes:
        lines.append(
            "Rune: " + ", ".join(f"{x.title()} (+2 {RUNES[x]})" for x in runes if x in RUNES)
        )
    elif i["level"] >= 6:
        lines.append("Rune socket: empty")
    return "\n".join(lines)


def sets_embed(p, prefix):
    e = discord.Embed(
        title="✧ Sets & rune sockets",
        color=COLOR,
        description="Unlock at level 6 after the tutorial. Any class can wear any set. Bonuses stack at 2 and 4 different armor pieces; a fifth piece adds no extra set bonus.",
    )
    counts = game.set_counts(p)
    for key, data in GEAR_SETS.items():
        bonuses = "\n".join(
            f"{n} pieces: " + ", ".join(f"+{v} {a}" for a, v in bonus.items())
            for n, bonus in data["bonuses"].items()
        )
        e.add_field(
            name=f"{data['name']} · {counts.get(key, 0)}/5 equipped",
            value=bonuses + f"\n`{prefix}aether setforge head {key}`",
            inline=False,
        )
    e.add_field(
        name="Forge a set piece",
        value="Slots: head, chest, hands, legs, feet. Each piece costs 8 iron + 4 essence + (100 + 10 × your level) gold. Rare gear at your current level; binds on equip.",
        inline=False,
    )
    e.add_field(
        name="Add a rune",
        value="\n".join(f"**{key}**: +2 {attr}" for key, attr in RUNES.items())
        + f"\n`{prefix}aether socket ITEM_ID ember`\n75 gold + 2 iron + 4 essence. One rune per level 6+ item. Socketing binds the item. Guaranteed; no rerolls.",
        inline=False,
    )
    e.add_field(
        name="Change a rune",
        value=f"`{prefix}aether unsocket ITEM_ID confirm`\n25 gold. Destroys the rune, with no material refund. Then socket your new choice. Unlock locked items first; no changes during combat.",
        inline=False,
    )
    return tidy_commands(e, prefix)


async def guild_prefix(bot, guild):
    prefixes = await bot.get_valid_prefixes(guild)
    return next((p for p in prefixes if not p.startswith("<@")), prefixes[0])


def tutorial_embed(p, prefix):
    e = discord.Embed(
        title="✦ Your path to Hoshifall", description=game.tutorial(p, prefix), color=COLOR
    )
    e.set_footer(text=f"Copy the whole command • {prefix}aether tutorial brings you back here")
    return tidy_commands(e, prefix)


def profile_embed(p, prefix):
    s = game.stats(p)
    battle = p["battle"]
    rank = (
        "Initiate"
        if p["tutorial"] < 6
        else (
            "Riftwalker" if p["level"] >= 15 else "Pathfinder" if p["level"] >= 6 else "Adventurer"
        )
    )
    e = discord.Embed(
        title=f"✦ {discord.utils.escape_markdown(p['name'])} • {rank}",
        description=f"**Level {p['level']} {p['cls'].title()}** · Hoshifall\n{discord.utils.escape_markdown(p['appearance'])}",
        color=COLOR,
    )
    if p["level"] >= 20:
        progress = "▰" * 10 + " **MAX LEVEL**"
    else:
        needed = game.xp_needed(p["level"])
        bars = min(10, p["xp"] * 10 // needed)
        progress = (
            "▰" * bars
            + "▱" * (10 - bars)
            + f"\n**{p['xp']:,} / {needed:,} EXP** to level {p['level'] + 1}"
        )
    e.add_field(name="✧ Journey", value=progress, inline=False)
    hp = f"{battle['hp']}/{battle['maxhp']}" if battle else str(s["hp"])
    energy = f"{battle['energy']}/{s['energy']}" if battle else str(s["energy"])
    mechanic = MECHANICS[p["cls"]]
    e.add_field(
        name="⚔ Combat",
        value=f"HP **{hp}**\nEnergy **{energy}**\nAttack **{s['attack']:.1f}**\nArmor **{s['armor']:.1f}** · Crit **{s['crit']:.0%}**",
    )
    e.add_field(
        name="Class mechanic",
        value=f"**{mechanic['name']} {battle.get('resource', 0) if battle else 0}/{mechanic['cap']}**\n{mechanic['description']}",
        inline=False,
    )
    attrs = game.attributes(p)
    e.add_field(
        name="✦ Attributes",
        value="\n".join(
            f"{a.title()} **{v}**{' ★' if a == CLASSES[p['cls']]['stat'] else ''}"
            for a, v in attrs.items()
        )
        + f"\n**{p['points']}** points unspent",
    )
    e.add_field(
        name="◈ Supplies & feats",
        value=f"Gold **{p['gold']:,}** · Potions **{p['potions']}**\nVictories **{p['wins']}**\nBosses **{p['boss_wins']}** · Dungeons **{p['dungeons']}**\nQuests claimed **{len(p['quests'])}**",
    )
    for title, slots in (
        ("⚔ Weapons", SLOTS[:2]),
        ("⛨ Armor", SLOTS[2:7]),
        ("✧ Accessories", SLOTS[7:]),
    ):
        lines = []
        for slot in slots:
            i = p["inventory"].get(p["equipped"].get(slot))
            detail = (
                f"{i['name']} **+{i['upgrade']}** · {rarity_label(i['rarity'])}" if i else "— Empty"
            )
            lines.append(f"**{SLOT_NAMES[slot]}** · {detail}")
        e.add_field(name=title, value="\n".join(lines), inline=False)
    counts = game.set_counts(p)
    if counts:
        e.add_field(
            name="✧ Set bonuses",
            value="\n".join(
                f"**{GEAR_SETS[key]['name']}** · {count}/5 · "
                + (
                    "; ".join(
                        f"+{v} {a}"
                        for n, bonus in GEAR_SETS[key]["bonuses"].items()
                        if count >= n
                        for a, v in bonus.items()
                    )
                    or "Collect 2 pieces for a bonus"
                )
                for key, count in counts.items()
            ),
            inline=False,
        )
    if s["uniques"]:
        effects = {
            "wayfarer": "Wayfarer: heal 3 HP when guarding",
            "spiritward": "Spiritward: 15% less guarded damage",
            "emberblade": "Emberblade: +3 attack damage",
        }
        e.add_field(
            name="✺ Active gear effects",
            value="\n".join(effects.get(k, k) for k in sorted(s["uniques"])),
            inline=False,
        )
    if battle:
        next_step = f"Battle in progress · `{prefix}aether resume`"
    elif p["tutorial"] < 6:
        next_step = f"Tutorial step {p['tutorial'] + 1}/6 · `{prefix}aether tutorial`"
    elif p["run"]:
        next_step = f"Hollow Trail · room {p['run']['room'] + 1}/4 · `{prefix}aether dungeon`"
    else:
        next_step = f"Ready to explore · `{prefix}aether explore`"
    e.add_field(name="Next move", value=next_step, inline=False)
    e.set_footer(
        text="★ Class damage attribute • Outside combat, HP and energy show encounter starting values"
    )
    return tidy_commands(e, prefix)


def channel_embed(key, settings, prefix):
    c = f"{prefix}aether"
    channels = settings["channels"]
    adventure = f"<#{channels['adventures']}>"
    e = discord.Embed(color=COLOR)
    if key == "guide":
        e.title = "✦ Welcome to Aetherbound"
        e.description = "**Hoshifall awaits. Choose your class. Write your story.**\nAn active adventure: fight, collect gear and grow stronger by playing."
        e.add_field(
            name="1 · Choose your class",
            value="**Vanguard** — strength & guarded strikes\n**Strider** — dexterity & bleeding attacks\n**Arcanist** — intelligence & spellcraft",
            inline=False,
        )
        e.add_field(
            name="2 · Create your hero",
            value=f"In {adventure}, copy this and replace `Your Name`:\n`{c} create vanguard Your Name`\nYou can replace `vanguard` with `strider` or `arcanist`.",
            inline=False,
        )
        e.add_field(
            name="3 · Learn as you play",
            value=f"`{c} tutorial`\nSix short steps teach gear, battle and forging. Earn starter equipment, materials and a relic.",
            inline=False,
        )
        e.add_field(
            name="Find your place",
            value=f"**Battles & commands:** {adventure}\n**Encounters:** <#{channels['spawns']}> · press Engage\n**Trade offers:** <#{channels['trading']}> · discussion threads only; item transfers are not available yet\n**Chat & planning:** <#{channels['tavern']}>",
            inline=False,
        )
        e.add_field(
            name="Make it yours",
            value="Use **My next step** for your current lesson and **My profile** for your hero. Alert buttons below toggle optional roles.",
            inline=False,
        )
    elif key == "adventures":
        e.title = "⚔ Adventures · Play here"
        e.description = "Type game commands here. Battles use clickable buttons."
        e.add_field(
            name="Start or continue",
            value=f"`{c} create vanguard Your Name`\n`{c} tutorial`\n`{c} explore`\n`{c} resume` — restore an unfinished battle",
            inline=False,
        )
        e.add_field(
            name="Example · Equip a loadout",
            value=f"`{c} inventory` — find your item IDs\n`{c} equip ID1 ID2 ID3`\nOr: `{c} ID1 ID2 ID3`\nReplace each ID with one from your bag. Slots are automatic; use one item per slot.",
            inline=False,
        )
        e.add_field(
            name="Example · A battle turn",
            value="Enemy charging? Click **Guard** or your interrupt skill.\n**Attack** restores energy. **Skills** spend energy.\nUse **Potion** to heal; **Flee** leaves without rewards.",
            inline=False,
        )
        e.add_field(
            name="Grow your hero",
            value=f"`{c} profile` · `{c} quests` · `{c} recipes`\n`{c} forge ring1` — make a ring after the armor lesson",
            inline=False,
        )
    elif key == "spawns":
        e.title = "✺ Encounter board · Watch for monsters"
        e.description = "Live monster and boss encounters appear below. This channel is read-only."
        e.add_field(
            name="Example · Lantern Slime, level 1",
            value=f"On an **actual encounter post**, press **Engage** to claim a solo fight. Follow its link to {adventure} and use the battle buttons.\nThis guide is an example, not a claimable encounter.",
            inline=False,
        )
        e.add_field(
            name="Before you engage",
            value="Finish the tutorial. Be within four levels below the enemy. One player claims each spawn; unclaimed encounters expire after 15 minutes.",
            inline=False,
        )
        e.add_field(
            name="Play whenever you want",
            value=f"No need to wait for a spawn. Use `{c} explore` in {adventure}. Choose Boss or Adventure alerts in start-here.",
            inline=False,
        )
    elif key == "trading":
        e.title = "◈ Trading post · Offers only"
        e.description = "Post an offer here. Discuss it in the thread the bot opens."
        e.add_field(
            name="Copyable example",
            value="```text\ntrading iron sword for crystal staff\n```\nNo command prefix needed. Replace the item names with your offer.",
            inline=False,
        )
        e.add_field(
            name="Keep the market tidy",
            value=f"One new offer every five minutes. Ordinary chat, links, mentions and attachments are removed. General conversation belongs in <#{channels['tavern']}>.",
            inline=False,
        )
        e.add_field(
            name="Current trading scope",
            value="Threads support negotiation only. Items and gold cannot be transferred between players yet. Posting an offer does not exchange anything.",
            inline=False,
        )
    else:
        e.title = "☕ Tavern · Rest by the lanterns"
        e.description = "Share your loot, discuss builds and ask other adventurers for help. Normal conversation is welcome here."
        e.add_field(
            name="Conversation starter",
            value="“I just forged my first ring. What should I upgrade next?”",
            inline=False,
        )
        e.add_field(
            name="Your next adventure",
            value=f"Use `{c} profile` to inspect your hero or `{c} skills` to learn your class. Continue battles in {adventure}.",
            inline=False,
        )
    if key in ("adventures", "tavern"):
        e.add_field(
            name="Sets & runes · level 6+",
            value=f"`{c} sets`\nBrowse collections, crafting costs and rune instructions.",
            inline=False,
        )
    if key in ("guide", "adventures", "tavern"):
        e.add_field(
            name="Quest board & daily supplies",
            value=f"`{c} quests` — accept quests and claim rewards\n`{c} payday` — daily gold after graduation\n`{c} shop` — today's tavern wares\nUse the **Tavern shop** button for private browsing.\nShortcuts: `{prefix}ae` / `{prefix}a` when those aliases are available.",
            inline=False,
        )
    e.set_footer(
        text="Live help • Buttons read your saved character • Examples use this server’s prefix"
    )
    return tidy_commands(e, prefix)


def quest_embed(p, prefix):
    from .content import QUESTS

    e = discord.Embed(
        title="✦ Hoshifall quest board",
        description="**1. Accept → 2. Complete the objective → 3. Claim your reward**\nNew quests track victories earned after acceptance. Older characters keep their already tracked progress.",
        color=COLOR,
    )
    objectives = {
        "first_hunts": "Win 3 non-practice fights",
        "guardian": "Defeat Tsukara once",
        "trail": "Complete the Hollow Trail once (level 6+)",
    }
    for key, q in QUESTS.items():
        claimed = key in p["quests"]
        accepted = key in p.get("accepted_quests", {})
        progress = min(q["goal"], game.quest_progress(p, key))
        status = (
            "Claimed ✓"
            if claimed
            else "Ready to claim"
            if accepted and progress >= q["goal"]
            else "Active"
            if accepted
            else "Available"
        )
        action = "claim" if accepted else "accept"
        instruction = (
            "Reward already collected." if claimed else f"`{prefix}aether quests {action} {key}`"
        )
        e.add_field(
            name=f"{q['name']} · {status}",
            value=f"{objectives[key]} · **{progress}/{q['goal']}**\nReward: **{q['gold']} gold + {q['xp']} EXP**\n{instruction}",
            inline=False,
        )
    e.set_footer(
        text="Each quest pays once • Practice battles do not count • Accepting never costs gold"
    )
    return tidy_commands(e, prefix)


def shop_embed(shop, gold, prefix):
    from .loot import rarity_label

    e = discord.Embed(
        title="☕ The Lantern Tavern · Daily wares",
        description=f"**{gold:,} gold** · Offers for {shop['day']} (UTC)\nYour personal stock rotates at **00:00 UTC**. Today's equipment stays at level {shop['level']} even if you level up. Finish the tutorial to buy.",
        color=0xD8A35D,
    )
    for offer in shop["offers"]:
        i = offer.get("item")
        detail = ""
        if i:
            bonuses = (
                ", ".join(f"{k} +{v}" for k, v in i["bonuses"].items()) or "no attribute bonuses"
            )
            detail = f"{rarity_label(i['rarity'])} · {SLOT_NAMES[i['slot']]} · Lv{i['level']}\nPower {i['power']} · {bonuses}\n"
        e.add_field(
            name=f"{offer['name']} · {offer['price']:,} gold",
            value=detail
            + f"Remaining: **{offer['stock'] - offer['bought']}**\n`{prefix}aether buy {offer['code']}`",
            inline=False,
        )
    e.set_footer(
        text="Codes include the date to prevent buying a different item after rotation • Unique loot comes from combat"
    )
    return tidy_commands(e, prefix)


def inventory_embed(p, page, prefix):
    items = list(p["inventory"].values())
    pages = max(1, (len(items) + 9) // 10)
    page = max(1, min(page, pages))
    e = discord.Embed(
        title=f"{p['name']}'s inventory",
        description=(
            f"**{p['gold']:,} gold** · {p['potions']} potions · {len(items)}/200 items\n"
            f"Equip or inspect an item:\n`{prefix}aether equip ID1 ID2`\n`{prefix}aether item ID`"
        ),
        color=COLOR,
    )
    for i in items[(page - 1) * 10 : page * 10]:
        power = i["power"] + i["upgrade"] * 2
        bonus = " · ".join(f"{k.title()} {v:+d}" for k, v in i["bonuses"].items())
        equipped = " · Equipped" if i["id"] in p["equipped"].values() else ""
        upgrade = f" +{i['upgrade']}" if i["upgrade"] else ""
        details = (
            f"`{i['id']}` · {SLOT_NAMES[i['slot']]} · Lv{i['level']}{equipped}\n"
            f"{'🔒 Locked · ' if i.get('locked') else ''}{'Bound' if i.get('bound') else 'Unbound'}\n"
            f"**Power {power}**" + (f" · {bonus}" if bonus else "")
        )
        extra = customization_detail(i)
        if extra:
            details += "\n" + extra
        if i["twohand"]:
            details += "\nTwo-handed · ×1.5 weapon power"
        if i["unique"]:
            effect = {
                "wayfarer": "Wayfarer — heal 3 HP when guarding",
                "spiritward": "Spiritward — 15% less damage when guarding",
                "emberblade": "Emberblade — +3 damage per attack",
            }.get(i["unique"], i["unique"])
            details += f"\n{effect}"
        e.add_field(
            name=f"{rarity_label(i['rarity'])} {i['name']}{upgrade}", value=details, inline=False
        )
    if not items:
        e.add_field(name="Your bag is empty", value="Continue the tutorial or fight to earn gear.")
    materials = " · ".join(f"{k.title()} {v:,}" for k, v in p["materials"].items()) or "None"
    e.add_field(name="Materials", value=materials, inline=False)
    if p.get("unclaimed_loot"):
        e.add_field(
            name="Unclaimed loot", value=f"{len(p['unclaimed_loot'])} items · `{prefix}ae loot`"
        )
    e.set_footer(
        text=f"Page {page}/{pages} · Power includes upgrades · Controls expire after 3 minutes"
    )
    return tidy_commands(e, prefix), page, pages
