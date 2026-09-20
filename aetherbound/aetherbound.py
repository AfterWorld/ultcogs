"""Aetherbound: an active, persistent Red aether RPG."""

import asyncio
import io
import json
import logging
import random
import time
from collections import defaultdict

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.data_manager import cog_data_path

from . import economy
from . import engine as game
from .art import artwork
from .content import ATTRS, CLASSES, MONSTERS, QUESTS, SLOTS
from .loot import BOSS_DROPS, RARITIES, UNIQUES, rarity_label
from .presentation import quest_embed, shop_embed, tutorial_embed
from .setup_server import provision, refresh_panels
from .store import Store
from .views import BattleView, GuideView, ProfileLauncher, RoleView, SpawnView, battle_embed

log = logging.getLogger("red.aetherbound")


class Aetherbound(commands.Cog):
    """Create a hero, learn combat, forge equipment and explore Hoshifall."""

    def __init__(self, bot):
        self.bot = bot
        self.store = Store(cog_data_path(self) / "aetherbound.sqlite3")
        self.rng = random.Random()
        self.views = set()
        self.guild_locks = defaultdict(asyncio.Lock)
        self.role_locks = defaultdict(asyncio.Lock)

    async def cog_load(self):
        await self.store.initialize()
        self.bot.add_view(GuideView(self))
        for row in await self.store.rows("players"):
            p = json.loads(row["data"])
            b = p.get("battle")
            if b and b.get("message"):
                self.bot.add_view(BattleView(self, row["user"], p), message_id=b["message"])
        for row in await self.store.rows("spawns"):
            if not row["claimed"] and row["expires"] > time.time() and row["message"]:
                self.bot.add_view(SpawnView(self, row["id"]), message_id=row["message"])
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()
        for v in list(self.views):
            v.stop()
        self.views.clear()

    async def cog_command_error(self, ctx, error):
        cause = getattr(error, "original", error)
        if isinstance(cause, game.RuleError):
            await ctx.send(str(cause), allowed_mentions=discord.AllowedMentions.none())
        elif isinstance(cause, (discord.Forbidden, discord.NotFound)):
            await ctx.send(
                "A game channel/role is missing or inaccessible. An admin can repair it with aetherset setup."
            )
        elif isinstance(cause, commands.UserInputError):
            await ctx.send_help()
        elif isinstance(cause, commands.CheckFailure):
            await ctx.send("You do not have permission to run that command here.")
        else:
            log.exception("Aetherbound command failed", exc_info=error)
            await ctx.send(
                "That action failed. Saved battles can be restored with aether resume; ask an admin to check the bot logs."
            )

    async def require(self, ctx):
        p = await self.store.player(ctx.guild.id, ctx.author.id)
        if not p:
            raise game.RuleError("Create your character: aether create vanguard Your Name")
        return p

    async def cog_before_invoke(self, ctx):
        settings = await self.store.settings(ctx.guild.id)
        if ctx.channel.id == settings.get("channels", {}).get("trading"):
            raise game.RuleError(
                "Use game commands in the adventures channel. The trading post is for offers only."
            )

    async def mutate(self, ctx, fn):
        return await self.store.change(ctx.guild.id, ctx.author.id, lambda p, c: fn(p))

    async def action(self, guild, user, bid, turn, action):
        return await self.store.change(
            guild, user, lambda p, c: game.act(p, bid, turn, action, self.rng)
        )

    async def publish_battle(self, channel, guild, user):
        p = await self.store.player(guild, user)
        if not p or not p["battle"]:
            raise game.RuleError("No active battle.")
        b = p["battle"]
        view = BattleView(self, user, p)
        embed = battle_embed(p)
        art = artwork(embed, b["monster"])
        message = await channel.send(
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
            **art,
        )

        def save(p, c):
            if p["battle"] and p["battle"]["id"] == b["id"]:
                p["battle"]["message"] = message.id
                p["battle"]["channel"] = channel.id
                p["battle"]["art"] = bool(art)

        await self.store.change(guild, user, save)
        return message

    @commands.group(name="aether", invoke_without_command=True)
    @commands.guild_only()
    async def adventure(self, ctx, *item_ids: str):
        """Aetherbound: create, tutorial, profile, explore, inventory, forge, dungeon."""
        if item_ids:
            await self.equip_items(ctx, item_ids)
        else:
            await ctx.send_help()

    @adventure.command()
    async def create(self, ctx, character_class: str, *, name: str):
        """Create once per server: aether create strider Your Name."""
        p = await self.store.change(
            ctx.guild.id,
            ctx.author.id,
            lambda p, c: game.new_player(name, character_class.lower()),
            create=True,
        )
        await ctx.send(
            embed=tutorial_embed(p, ctx.clean_prefix),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @adventure.command()
    async def tutorial(self, ctx):
        """Resume the rewarded, action-based tutorial."""
        await ctx.send(
            embed=tutorial_embed(await self.require(ctx), ctx.clean_prefix),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @adventure.command()
    async def skills(self, ctx):
        """Explain your class's abilities, attributes, and combat resources."""
        p = await self.require(ctx)
        descriptions = {
            "vanguard": "Cleave: 165% attack. Guard Break: interrupts a charged move and exposes the target. Iron Guard: guard plus a barrier worth 35% max HP, with a light counterstrike.",
            "strider": "Twin Strike: 135% attack plus two bleeding ticks. Mark Prey: interrupts and exposes the target for longer. Evasive Step: guard plus a 20% HP barrier; your next damaging action gains 25% damage.",
            "arcanist": "Spark Bolt: 185% attack. Frost Bind: interrupts, exposes, and chills the target (20% less incoming damage). Aether Ward: guard plus a 30% HP barrier and a light strike.",
        }
        await ctx.send(
            descriptions[p["cls"]]
            + "\nAll skills cost 12 energy and require two intervening turns before reuse. Attack restores 7 energy; Guard restores 10 and reduces incoming attack damage by 65%. Potions heal 40% of battle max HP and consume a turn.\nYour class damage attribute is "
            + CLASSES[p["cls"]]["stat"]
            + ". Vitality adds HP and armor; Dexterity adds critical chance; Willpower adds energy capacity. Other damage attributes support future specializations."
        )

    @adventure.command()
    async def profile(self, ctx):
        """Open your private character sheet; the temporary button disappears in 30s."""
        await self.require(ctx)
        await ctx.send(
            "Your profile is private. Click below within 30 seconds. You can also use **My profile** on any game channel guide.",
            view=ProfileLauncher(self, ctx.author.id),
            delete_after=30,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        # Remove only the invoking command when Discord allows it.
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @adventure.command()
    async def appearance(self, ctx, *, description: str):
        """Set a cosmetic character description (max 200 characters)."""
        if len(description) > 200 or "@" in description:
            raise game.RuleError("Use up to 200 characters without mentions.")
        await self.mutate(ctx, lambda p: p.update(appearance=description))
        await ctx.tick()

    @adventure.command()
    async def inventory(self, ctx, page: int = 1):
        """List item IDs, gold, materials, and equipped markers."""
        p = await self.require(ctx)
        items = list(p["inventory"].values())
        pages = max(1, (len(items) + 9) // 10)
        if not 1 <= page <= pages:
            raise game.RuleError(f"Choose page 1–{pages}.")
        lines = [
            f"`{i['id']}` {rarity_label(i['rarity'])} **{i['name']}** +{i['upgrade']} • {i['slot']} • Lv{i['level']} {'[equipped]' if i['id'] in p['equipped'].values() else ''}"
            for i in items[(page - 1) * 10 : page * 10]
        ]
        await ctx.send(
            f"**Inventory {page}/{pages}** • {p['gold']} gold • {p['potions']} potions\n"
            + "\n".join(lines)
            + "\nMaterials: "
            + str(p["materials"])
            + f"\nOverflow: {len(p.get('unclaimed_loot', []))} items — `{ctx.clean_prefix}aether loot`"
            + f"\nEquip several: `{ctx.clean_prefix}aether equip ID1 ID2 ID3` (replace IDs above; one per slot).",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @adventure.command(name="item")
    async def item_info(self, ctx, item_id: str):
        """Inspect an item and compare its slot with your current gear."""
        p = await self.require(ctx)
        i = game.item(p, item_id)
        current = p["inventory"].get(p["equipped"].get(i["slot"]))
        await ctx.send(
            f"**{i['name']}** • {i['rarity']} • {i['slot']} • level {i['level']}\nPower {i['power']} + upgrade {i['upgrade'] * 2}; modifiers {i['bonuses']}\nUnique: {i['unique'] or 'none'} • Two-handed: {i['twohand']}\nCurrently equipped: {current['name'] if current else 'nothing'}\nUnique effects: wayfarer heals 3 on guard; spiritward reduces guarded damage by 15%; emberblade adds 3 damage once per attack."
        )

    async def equip_items(self, ctx, item_ids):
        result = await self.mutate(ctx, lambda p: game.equip_many(p, list(item_ids)))
        p = await self.require(ctx)
        await ctx.send(result, allowed_mentions=discord.AllowedMentions.none())
        if p["tutorial"] < 6:
            await ctx.send(
                embed=tutorial_embed(p, ctx.clean_prefix),
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @adventure.command()
    async def equip(self, ctx, *item_ids: str):
        """Equip 1–11 items: aether equip ID1 ID2 ID3. Slots are automatic."""
        await self.equip_items(ctx, item_ids)

    @adventure.command()
    async def unequip(self, ctx, slot: str):
        """Remove equipment without destroying it."""

        def fn(p):
            game.idle(p)
            if slot not in SLOTS:
                raise game.RuleError("Unknown equipment slot.")
            p["equipped"].pop(slot, None)

        await self.mutate(ctx, fn)
        await ctx.tick()

    @adventure.command()
    async def allocate(self, ctx, attribute: str, amount: int = 1):
        """Spend attribute points: strength/dexterity/intelligence/vitality/willpower."""

        def fn(p):
            game.idle(p)
            if attribute not in ATTRS or amount < 1 or amount > p["points"]:
                raise game.RuleError(
                    "Choose a valid attribute and an available positive number of points."
                )
            p["attrs"][attribute] += amount
            p["points"] -= amount

        await self.mutate(ctx, fn)
        await ctx.tick()

    @adventure.command()
    async def respec(self, ctx):
        """Refund allocated attribute points for free in Phase 1."""

        def fn(p):
            game.idle(p)
            p["points"] += sum(p["attrs"].values())
            p["attrs"] = {a: 0 for a in ATTRS}

        await self.mutate(ctx, fn)
        await ctx.tick()

    @adventure.command()
    async def recipes(self, ctx):
        """Show forging, upgrade, and unique boss recipe costs."""
        await ctx.send(
            "Forge any slot: 4 iron + 2 essence + (30 + 5 × (level − 1)) gold.\n"
            "Boss recipes add 2 spirit_core (tsukara) or ember_core (raizen) and double gold.\n"
            "Upgrade: 2 iron + 25 × (current upgrade + 1) gold. Guaranteed; cap +5.\n"
            "Slots: "
            + ", ".join(SLOTS)
            + "\nUse aether forge main, or aether forge relic tsukara. Add true after the recipe for a two-handed main weapon: aether forge main normal true."
        )

    @adventure.command()
    async def forge(self, ctx, slot: str, recipe: str = "normal", twohand: bool = False):
        """Forge equipment: slot [normal|tsukara|raizen] [twohand]."""
        i = await self.mutate(
            ctx, lambda p: game.forge(p, slot, None if recipe == "normal" else recipe, twohand)
        )
        p = await self.require(ctx)
        await ctx.send(
            f"Forged **{i['name']}**. Equip with `{ctx.clean_prefix}aether equip {i['id']}`.",
            embed=tutorial_embed(p, ctx.clean_prefix) if p["tutorial"] < 6 else None,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @adventure.command()
    async def upgrade(self, ctx, item_id: str):
        """Upgrade an item with iron and gold; never destroys it."""
        await ctx.send(await self.mutate(ctx, lambda p: game.upgrade(p, item_id)))

    @adventure.command()
    async def salvage(self, ctx, item_id: str):
        """Destroy an unequipped item for 2 iron and 1 essence."""
        await ctx.send(await self.mutate(ctx, lambda p: game.salvage(p, item_id)))

    @adventure.command()
    async def potion(self, ctx):
        """Buy a 40% healing potion for 15 gold outside combat."""

        def fn(p):
            game.idle(p)
            if p["tutorial"] < 5:
                raise game.RuleError(
                    "Finish the forging lesson first; save your starter gold for its recipe."
                )
            if p["gold"] < 15:
                raise game.RuleError("A potion costs 15 gold.")
            p["gold"] -= 15
            p["potions"] += 1

        await self.mutate(ctx, fn)
        await ctx.send("Bought a potion. Use its button during combat.")

    @adventure.command()
    async def practice(self, ctx):
        """Safe tutorial fight; use Attack, Guard and a Skill, then win."""

        def fn(p):
            if p["tutorial"] != 1:
                raise game.RuleError("Practice is the second tutorial step. Use aether tutorial.")
            return game.begin(p, "slime", practice=True)

        await self.mutate(ctx, fn)
        await self.publish_battle(ctx.channel, ctx.guild.id, ctx.author.id)

    @adventure.command()
    async def explore(self, ctx, region: str = "glimmerwood"):
        """Start an active hunt in Glimmerwood or Embervein."""

        def fn(p):
            if p["run"]:
                raise game.RuleError("Continue your dungeon or use aether abandon first.")
            return game.begin(p, game.choose_monster(p, region.lower(), self.rng))

        await self.mutate(ctx, fn)
        await self.publish_battle(ctx.channel, ctx.guild.id, ctx.author.id)

    @adventure.command()
    async def resume(self, ctx):
        """Restore battle controls after a restart or deleted message."""
        await self.publish_battle(ctx.channel, ctx.guild.id, ctx.author.id)

    @adventure.command()
    async def dungeon(self, ctx):
        """Enter/continue the four-room Hollow Trail (level 6+)."""

        def fn(p):
            game.idle(p)
            if p["level"] < 6 or p["tutorial"] < 6:
                raise game.RuleError("The Hollow Trail needs level 6 and a completed tutorial.")
            if not p["run"]:
                p["run"] = {"room": 0, "hp": game.stats(p)["hp"]}
            keys = ("wolf", "moth", "sentinel", "tsukara")
            return game.begin(
                p, keys[p["run"]["room"]], carry=min(p["run"]["hp"], game.stats(p)["hp"])
            )

        await self.mutate(ctx, fn)
        await self.publish_battle(ctx.channel, ctx.guild.id, ctx.author.id)

    @adventure.command()
    async def abandon(self, ctx):
        """Leave a dungeon between rooms without losing gear."""

        def fn(p):
            game.idle(p)
            p["run"] = None

        await self.mutate(ctx, fn)
        await ctx.tick()

    @adventure.command()
    async def quests(self, ctx, action: str = "", key: str = ""):
        """Quest board: quests accept <key>, then quests claim <key> after the objective."""
        if action:
            if action in QUESTS and not key:
                key, action = action, "claim"  # Preserve the original claim shorthand.
            if action not in ("accept", "claim") or key not in QUESTS:
                raise game.RuleError(
                    f"Use `{ctx.clean_prefix}aether quests` to see accept/claim commands."
                )
            fn = game.accept_quest if action == "accept" else game.claim_quest
            await ctx.send(
                await self.mutate(ctx, lambda p: fn(p, key)),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        await ctx.send(embed=quest_embed(await self.require(ctx), ctx.clean_prefix))

    @adventure.command()
    async def payday(self, ctx):
        """Claim daily gold once per UTC day after finishing the tutorial."""
        await ctx.send(await self.mutate(ctx, economy.payday))

    @adventure.command(aliases=["tavern"])
    async def shop(self, ctx):
        """Browse your rotating tavern offers; restocks at 00:00 UTC."""
        offers = await self.mutate(ctx, lambda p: economy.shop(p, ctx.guild.id, ctx.author.id))
        p = await self.require(ctx)
        await ctx.send(embed=shop_embed(offers, p["gold"], ctx.clean_prefix))

    @adventure.command()
    async def buy(self, ctx, offer_code: str):
        """Buy a daily shop offer using its complete dated code from aether shop."""
        await ctx.send(
            await self.mutate(
                ctx, lambda p: economy.buy(p, ctx.guild.id, ctx.author.id, offer_code)
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @adventure.command()
    async def loot(self, ctx):
        """Collect equipment saved in overflow when your bag was full."""
        await ctx.send(await self.mutate(ctx, game.claim_loot))

    @adventure.command()
    async def rarities(self, ctx):
        """Explain every item tier, acquisition level and unique effects."""
        await ctx.send(
            "**Hoshifall's item tiers**\n"
            + "\n".join(
                f"{rarity_label(k)} — rank {v['rank']}; drops/shop unlock at level {v['level']}"
                for k, v in RARITIES.items()
                if k != "unique"
            )
            + "\n🌟 **Unique** — named encounter-only items with a special effect; Epic-sized stat budget. Repeated copies of an effect never stack. Boss signatures and Unique items are not sold in the shop.\nHigher rarity adds bounded stats; level, slot and your class still matter."
        )

    @adventure.command()
    async def bestiary(self, ctx, monster: str = ""):
        """List all enemies, or inspect one by key for its portrait and special loot."""
        if monster:
            if monster not in MONSTERS:
                raise game.RuleError("Unknown monster key. Use aether bestiary.")
            m = MONSTERS[monster]
            e = discord.Embed(
                title=m["name"],
                description=f"Level {m['level']} · {m['region']} · {'Boss' if m['boss'] else 'Monster'}\nMaterial: {m['material']}\n{game.INTENTS[m['behavior']]}",
                color=0x836FFF,
            )
            if monster in BOSS_DROPS:
                e.add_field(
                    name="Guaranteed signature drop (one per victory)",
                    value="\n".join(name for _, name in BOSS_DROPS[monster]),
                    inline=False,
                )
            if monster in UNIQUES:
                e.add_field(
                    name="Rare unique drop",
                    value=f"{UNIQUES[monster]['name']} — {'3%' if m['boss'] else '0.5%'} additional chance per victory. Effect: {UNIQUES[monster]['effect']}.",
                    inline=False,
                )
            kwargs = artwork(e, monster)
            await ctx.send(embed=e, **kwargs)
            return
        await ctx.send(
            "\n".join(
                f"`{k}` {'BOSS ' if m['boss'] else ''}**{m['name']}** — Lv{m['level']} • {m['region']}"
                for k, m in MONSTERS.items()
            )
            + f"\nInspect art and drops: `{ctx.clean_prefix}aether bestiary tsukara`"
        )

    @adventure.command()
    async def notifications(self, ctx):
        """Toggle trading, boss, and aether notification roles."""
        await ctx.send("Choose your optional notifications:", view=RoleView(self))

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def aetherset(self, ctx):
        """Admin setup, repair, spawn timing, and category placement."""
        await ctx.send_help()

    @aetherset.command()
    async def setup(self, ctx):
        """Create/repair game channels and roles; preserve existing game data."""
        async with self.guild_locks[ctx.guild.id]:
            async with ctx.typing():
                s = await provision(self, ctx.guild)
        await ctx.send(
            f"Aetherbound is ready: <#{s['channels']['guide']}>. Spawns every {s['spawn_minutes']} minutes. Roles are opt-in. Active shortcuts: {', '.join(ctx.clean_prefix + a for a in self.adventure.aliases) or 'none (already used by other cogs)'}."
        )

    @aetherset.command()
    async def guides(self, ctx):
        """Refresh channel examples and the welcome embed without changing permissions."""
        async with self.guild_locks[ctx.guild.id]:
            settings = await self.store.settings(ctx.guild.id)
            if not settings.get("channels"):
                raise game.RuleError(f"Run `{ctx.clean_prefix}aetherset setup` first.")
            await refresh_panels(self, ctx.guild, settings)
        await ctx.send(
            "Updated the game channel guides. Missing channels can be restored with setup."
        )

    @aetherset.command()
    async def position(self, ctx, index: int):
        """Place game category at a 1-based category index, minimum 2 when others exist."""
        s = await self.store.settings(ctx.guild.id)
        cat = ctx.guild.get_channel(s.get("category", 0))
        if not cat:
            raise game.RuleError("Run setup first.")
        others = sorted(
            [c for c in ctx.guild.categories if c.id != cat.id], key=lambda c: c.position
        )
        if not max(1, min(2, len(others) + 1)) <= index <= len(others) + 1:
            raise game.RuleError(f"Choose category index {2 if others else 1}–{len(others) + 1}.")
        if others:
            if index - 1 < len(others):
                await cat.move(before=others[index - 1])
            else:
                await cat.move(after=others[-1])
        await ctx.tick()

    @aetherset.command()
    async def spawns(self, ctx, enabled: bool, minutes: int = 30):
        """Enable/disable ambient spawns and set interval (5–1440 minutes)."""
        if not 5 <= minutes <= 1440:
            raise game.RuleError("Interval must be 5–1440 minutes.")
        async with self.guild_locks[ctx.guild.id]:
            s = await self.store.settings(ctx.guild.id)
            if not s.get("category"):
                raise game.RuleError("Run setup first.")
            s.update(enabled=enabled, spawn_minutes=minutes, next_spawn=time.time() + minutes * 60)
            await self.store.settings(ctx.guild.id, s)
        await ctx.tick()

    @aetherset.command()
    async def spawn(self, ctx, monster: str = ""):
        """Spawn a monster by bestiary key, or choose randomly."""
        if monster and monster not in MONSTERS:
            raise game.RuleError("Keys: " + ", ".join(MONSTERS))
        async with self.guild_locks[ctx.guild.id]:
            await self.spawn_one(ctx.guild, monster or None)
        await ctx.tick()

    async def spawn_one(self, guild, key=None):
        s = await self.store.settings(guild.id)
        channel = guild.get_channel(s.get("channels", {}).get("spawns", 0))
        if not channel:
            raise game.RuleError("Spawn channel missing. Run aetherset setup.")
        active = [
            r
            for r in await self.store.rows("spawns")
            if r["guild"] == guild.id and not r["claimed"] and r["expires"] > time.time()
        ]
        if active:
            raise game.RuleError("An encounter is already waiting in the spawn channel.")
        if not key:
            is_boss = self.rng.random() < 0.15
            pool = [k for k, m in MONSTERS.items() if m["boss"] == is_boss]
            key = self.rng.choice(pool or list(MONSTERS))
        m = MONSTERS[key]
        spawn_id = game.uid()
        expires = time.time() + 15 * 60
        await self.store.transaction(
            lambda c: c.execute(
                "INSERT INTO spawns VALUES(?,?,?,?,?,?,0)",
                (spawn_id, guild.id, channel.id, 0, key, expires),
            )
        )
        role = guild.get_role(s.get("roles", {}).get("boss" if m["boss"] else "adventures", 0))
        content = (
            (f"{role.mention} " if role else "")
            + f"**{'BOSS: ' if m['boss'] else ''}{m['name']}** • Level {m['level']} • {m['region']}\nPress Engage to claim a solo encounter. Expires <t:{int(expires)}:R>. Minimum level {max(1, m['level'] - 4)}."
        )
        embed = discord.Embed(
            title=m["name"],
            description="Press Engage below to begin your solo encounter.",
            color=0xE8C66A if m["boss"] else 0x836FFF,
        )
        try:
            message = await channel.send(
                content,
                embed=embed,
                **artwork(embed, key),
                view=SpawnView(self, spawn_id),
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=[role] if role else []
                ),
            )
        except Exception:
            await self.store.transaction(
                lambda c: c.execute("DELETE FROM spawns WHERE id=?", (spawn_id,))
            )
            raise
        await self.store.transaction(
            lambda c: c.execute("UPDATE spawns SET message=? WHERE id=?", (message.id, spawn_id))
        )

    async def claim_spawn(self, i, spawn_id):
        settings = await self.store.settings(i.guild.id)
        channel = i.guild.get_channel(settings.get("channels", {}).get("adventures", 0))
        if not channel:
            raise game.RuleError("Adventure channel missing; ask an admin to repair setup.")

        def claim(p, c):
            row = c.execute(
                "SELECT * FROM spawns WHERE id=? AND guild=?", (spawn_id, i.guild.id)
            ).fetchone()
            if not row or row["claimed"] or row["expires"] <= time.time():
                raise game.RuleError("This encounter was claimed or expired.")
            if p["run"]:
                raise game.RuleError("Finish or abandon your dungeon first.")
            game.begin(p, row["monster"])
            c.execute("UPDATE spawns SET claimed=1 WHERE id=?", (spawn_id,))

        await self.store.change(i.guild.id, i.user.id, claim)
        try:
            message = await self.publish_battle(channel, i.guild.id, i.user.id)
            await i.followup.send(f"Your battle is ready: {message.jump_url}", ephemeral=True)
        except discord.HTTPException:
            await i.followup.send(
                "Encounter claimed and saved. Use aether resume to restore its controls.",
                ephemeral=True,
            )

    @tasks.loop(seconds=60)
    async def spawn_loop(self):
        await self.recover_trades()
        for row in await self.store.rows("settings"):
            guild = self.bot.get_guild(row["guild"])
            if not guild or await self.bot.cog_disabled_in_guild(self, guild):
                continue
            async with self.guild_locks[guild.id]:
                s = await self.store.settings(guild.id)
                if not s.get("enabled") or s.get("next_spawn", 0) > time.time():
                    continue
                try:
                    await self.spawn_one(guild)
                except game.RuleError:
                    pass
                except discord.HTTPException:
                    log.exception("Spawn delivery failed in guild %s", guild.id)
                s["next_spawn"] = time.time() + s.get("spawn_minutes", 30) * 60
                await self.store.settings(guild.id, s)
        await self.store.transaction(
            lambda c: c.execute("DELETE FROM spawns WHERE expires<?", (time.time() - 86400,))
        )

    async def recover_trades(self):
        for row in await self.store.rows("trades"):
            if row["thread"] or row["created"] > time.time() - 30:
                continue
            settings = await self.store.settings(row["guild"])
            channel = self.bot.get_channel(settings.get("channels", {}).get("trading", 0))
            if channel:
                try:
                    await self.moderate_trade(await channel.fetch_message(row["message"]))
                except discord.NotFound:
                    await self.store.transaction(
                        lambda c, mid=row["message"]: c.execute(
                            "DELETE FROM trades WHERE message=?", (mid,)
                        )
                    )
                except discord.HTTPException:
                    log.exception("Pending trade recovery failed")

    @spawn_loop.before_loop
    async def before_spawns(self):
        await self.bot.wait_until_red_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.moderate_trade(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if not payload.guild_id or "content" not in payload.data:
            return
        settings = await self.store.settings(payload.guild_id)
        if payload.channel_id != settings.get("channels", {}).get("trading"):
            return
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            try:
                await self.moderate_trade(await channel.fetch_message(payload.message_id))
            except discord.NotFound:
                pass
            except discord.HTTPException:
                log.exception("Cannot moderate edited trade")

    async def moderate_trade(self, message):
        if (
            not message.guild
            or message.author.bot
            or await self.bot.cog_disabled_in_guild(self, message.guild)
        ):
            return
        s = await self.store.settings(message.guild.id)
        if message.channel.id != s.get("channels", {}).get("trading"):
            return  # Thread conversation is intentionally allowed.
        offer = game.trade_offer(message.content)
        try:
            if not offer or message.attachments:
                await message.delete()
                await message.channel.send(
                    "Offers only: `trading iron sword for crystal staff`. Continue conversations in offer threads or the tavern.",
                    delete_after=10,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return

            def reserve(c):
                existing = c.execute(
                    "SELECT * FROM trades WHERE message=?", (message.id,)
                ).fetchone()
                if existing:
                    if not existing["thread"] and existing["created"] < time.time() - 30:
                        c.execute(
                            "UPDATE trades SET created=? WHERE message=?", (time.time(), message.id)
                        )
                        return "recover"
                    return False
                recent = c.execute(
                    "SELECT 1 FROM trades WHERE guild=? AND user=? AND created>?",
                    (message.guild.id, message.author.id, time.time() - 300),
                ).fetchone()
                if recent:
                    raise game.RuleError(
                        "One new offer every five minutes; use your existing thread."
                    )
                c.execute(
                    "INSERT INTO trades VALUES(?,?,?,?,?)",
                    (message.id, message.guild.id, message.author.id, 0, time.time()),
                )
                return "new"

            try:
                reserved = await self.store.transaction(reserve)
            except game.RuleError:
                await message.delete()
                return
            if not reserved:
                return
            try:
                thread = None
                if reserved == "recover":
                    try:
                        candidate = await self.bot.fetch_channel(message.id)
                        if isinstance(candidate, discord.Thread):
                            thread = candidate
                    except discord.NotFound:
                        pass
                if not thread:
                    thread = await message.create_thread(
                        name=f"Trade: {offer[0]} → {offer[1]}"[:100],
                        auto_archive_duration=1440,
                        reason="Aetherbound trade offer",
                    )
            except discord.HTTPException:
                await self.store.transaction(
                    lambda c: c.execute("DELETE FROM trades WHERE message=?", (message.id,))
                )
                raise
            await self.store.transaction(
                lambda c: c.execute(
                    "UPDATE trades SET thread=? WHERE message=?", (thread.id, message.id)
                )
            )
            await thread.send(
                "Negotiate this offer here. Phase 1 provides discussion threads; automated item transfers arrive in a later phase.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            role = message.guild.get_role(s.get("roles", {}).get("trading", 0))
            # Batch market notifications: at most one ping per 15 minutes per server.
            async with self.guild_locks[message.guild.id]:
                current = await self.store.settings(message.guild.id)
                if role and time.time() - current.get("last_trade_ping", 0) > 900:
                    current["last_trade_ping"] = time.time()
                    await self.store.settings(message.guild.id, current)
                    await message.channel.send(
                        f"{role.mention} New offer: {thread.mention}",
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False, users=False, roles=[role]
                        ),
                    )
        except discord.HTTPException:
            log.exception("Trade moderation/thread creation failed in guild %s", message.guild.id)

    async def red_delete_data_for_user(self, *, requester, user_id):
        await self.store.delete_user(user_id)
        for view in list(self.views):
            if getattr(view, "owner", None) == user_id:
                view.stop()
                self.views.discard(view)

    async def red_get_data_for_user(self, *, user_id):
        records = [r for r in await self.store.rows("players") if r["user"] == user_id]
        trades = [r for r in await self.store.rows("trades") if r["user"] == user_id]
        return {
            "aetherbound.json": io.BytesIO(
                json.dumps({"characters": records, "trade_threads": trades}, indent=2).encode()
            )
        }
