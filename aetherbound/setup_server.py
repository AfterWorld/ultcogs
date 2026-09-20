"""Idempotent, checkpointed server provisioning; touches only recorded resources."""

import discord

from .engine import RuleError, category_index
from .presentation import channel_embed, guild_prefix
from .views import GuideView

CHANNELS = {
    "guide": (
        "start-here",
        False,
        "Create your adventurer, learn the game, and choose notification roles.",
    ),
    "adventures": ("adventures", True, "Game commands, exploration, and battle controls."),
    "spawns": (
        "monster-spawns",
        False,
        "Read-only encounter board. Press Engage to fight; no chat.",
    ),
    "trading": (
        "trading-post",
        True,
        "Offers only: trading iron sword for crystal staff. Discussions belong in the automatically created thread. Other messages are deleted. No item transfers are automated in Phase 1.",
    ),
    "tavern": ("tavern", True, "General conversation and adventure planning."),
}
REQUIRED = (
    "manage_channels",
    "manage_roles",
    "manage_messages",
    "create_public_threads",
    "send_messages_in_threads",
    "manage_threads",
    "view_channel",
    "send_messages",
    "embed_links",
    "read_message_history",
    "mention_everyone",
)


async def provision(cog, guild):
    missing = [p for p in REQUIRED if not getattr(guild.me.guild_permissions, p)]
    if missing:
        raise RuleError("Bot needs these server permissions: " + ", ".join(missing))
    if not cog.bot.intents.message_content:
        raise RuleError("Enable Message Content Intent before setup; trade moderation requires it.")
    s = await cog.store.settings(guild.id)
    s.setdefault("roles", {})
    s.setdefault("channels", {})
    s.setdefault("panels", {})
    s.setdefault("enabled", False)
    s.setdefault("spawn_minutes", 30)
    s.setdefault("next_spawn", 0)
    for key, name in (
        ("trading", "Aetherbound • Trading"),
        ("boss", "Aetherbound • Bosses"),
        ("adventures", "Aetherbound • Adventures"),
    ):
        role = guild.get_role(s["roles"].get(key, 0))
        if role and (role.permissions.value or role.managed or role >= guild.me.top_role):
            raise RuleError(
                f"{role.name} is privileged or above the bot. Restore its empty permissions/hierarchy before setup."
            )
        if not role:
            role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                mentionable=False,
                reason="Aetherbound setup",
            )
            s["roles"][key] = role.id
            await cog.store.settings(guild.id, s)
    category = guild.get_channel(s.get("category", 0))
    if category and not isinstance(category, discord.CategoryChannel):
        raise RuleError("Saved category ID is not a category.")
    if not category:
        others = sorted(guild.categories, key=lambda c: c.position)
        category = await guild.create_category("✦ Aetherbound", reason="Aetherbound setup")
        s["category"] = category.id
        await cog.store.settings(guild.id, s)
        index = category_index(len(others))
        if others:
            if index < len(others):
                await category.move(
                    before=others[index], reason="Place Aetherbound in upper-middle"
                )
            else:
                await category.move(
                    after=others[-1], reason="Place Aetherbound below existing categories"
                )
    for key, (name, talk, topic) in CHANNELS.items():
        channel = guild.get_channel(s["channels"].get(key, 0))
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=talk,
                send_messages_in_threads=talk,
                create_public_threads=False,
                create_private_threads=False,
                add_reactions=False,
                mention_everyone=False,
                attach_files=(key not in ("trading", "spawns", "guide")),
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                embed_links=True,
                read_message_history=True,
                manage_messages=True,
                create_public_threads=True,
                send_messages_in_threads=True,
                manage_threads=True,
                mention_everyone=True,
            ),
        }
        if channel and not isinstance(channel, discord.TextChannel):
            raise RuleError(f"Saved {key} channel has the wrong type.")
        if channel:
            await channel.edit(
                category=category,
                overwrites=overwrites,
                topic=topic,
                slowmode_delay=15 if key == "trading" else 0,
                reason="Repair Aetherbound channel",
            )
        else:
            channel = await guild.create_text_channel(
                name,
                category=category,
                overwrites=overwrites,
                topic=topic,
                slowmode_delay=15 if key == "trading" else 0,
                reason="Aetherbound setup",
            )
            s["channels"][key] = channel.id
            await cog.store.settings(guild.id, s)
    await refresh_panels(cog, guild, s)
    s["enabled"] = True
    await cog.store.settings(guild.id, s)
    return s


async def refresh_panels(cog, guild, settings):
    """Update recorded panels in place, checkpointing each new message for retries."""
    prefix = await guild_prefix(cog.bot, guild)
    settings.setdefault("panels", {})
    for key in CHANNELS:
        channel = guild.get_channel(settings["channels"].get(key, 0))
        if not channel:
            continue
        panel = None
        if settings["panels"].get(key):
            try:
                panel = await channel.fetch_message(settings["panels"][key])
            except discord.NotFound:
                pass
        kwargs = dict(
            content=None,
            embed=channel_embed(key, settings, prefix),
            view=GuideView(cog, include_roles=key == "guide"),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        if panel:
            await panel.edit(**kwargs)
        else:
            panel = await channel.send(**kwargs)
            settings["panels"][key] = panel.id
            await cog.store.settings(guild.id, settings)
