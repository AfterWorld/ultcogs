"""Persistent controls. Battle IDs and turn versions reject stale/double clicks."""

import logging

import discord

from . import economy
from .art import ART_VERSION, thumbnail
from .content import CLASSES, MONSTERS
from .engine import RuleError, intent
from .presentation import channel_embed, guild_prefix, profile_embed, shop_embed, tutorial_embed

log = logging.getLogger("red.aetherbound")


def battle_embed(p):
    b = p["battle"]
    m = MONSTERS[b["monster"]]
    e = discord.Embed(title=f"{p['name']} vs {m['name']}", color=0x836FFF)
    e.description = (
        f"**Your HP:** {b['hp']}/{b['maxhp']} • Energy {b['energy']}\n"
        f"**Enemy HP:** {b['enemy_hp']}/{b['enemy_maxhp']} • Level {m['level']}\n"
        f"**Intent:** {intent(b)}\n\n" + "\n".join(b["log"])
    )
    e.add_field(
        name="Skills",
        value="\n".join(
            f"{n + 1}. {name} — 12 energy; cooldown {b['cooldowns'].get(f'skill{n + 1}', 0)}"
            for n, name in enumerate(CLASSES[p["cls"]]["skills"])
        ),
        inline=False,
    )
    if b["practice"]:
        e.add_field(
            name="Training checklist",
            value=" · ".join(
                f"{'✓' if key in b['used'] else '○'} {label}"
                for key, label in (("guard", "Guard"), ("attack", "Attack"), ("skill", "Any skill"))
            )
            + "\nUse each once, then win. Start with Guard → Attack → your first skill.",
            inline=False,
        )
    e.set_footer(
        text=f"Turn {b['turn'] + 1} • Attack +7 energy • Guard +10 • Progress saves after each action"
    )
    if b.get("art") == ART_VERSION:
        thumbnail(e, b["monster"])
    return e


class SafeView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        cog.views.add(self)

    async def interaction_check(self, i):
        if not i.guild or await self.cog.bot.cog_disabled_in_guild(self.cog, i.guild):
            await i.response.send_message("Aetherbound is unavailable here.", ephemeral=True)
            return False
        if not await self.cog.bot.allowed_by_whitelist_blacklist(i.user):
            await i.response.send_message("You cannot use this bot.", ephemeral=True)
            return False
        return True

    async def on_error(self, i, error, item):
        log.exception("Aetherbound interaction failed", exc_info=error)
        send = i.followup.send if i.response.is_done() else i.response.send_message
        await send(
            "That action could not finish. Your saved state is safe; use aether resume.",
            ephemeral=True,
        )


class BattleView(SafeView):
    def __init__(self, cog, user, p):
        super().__init__(cog)
        self.owner = user
        b = p["battle"]
        for n, (key, label) in enumerate(
            (
                ("attack", "Attack"),
                ("guard", "Guard"),
                ("skill1", CLASSES[p["cls"]]["skills"][0]),
                ("skill2", CLASSES[p["cls"]]["skills"][1]),
                ("skill3", CLASSES[p["cls"]]["skills"][2]),
                ("potion", "Potion"),
                ("flee", "Flee"),
            )
        ):
            btn = discord.ui.Button(
                label=label,
                custom_id=f"ab:combat:{b['id']}:{b['turn']}:{key}",
                row=n // 4,
                style=discord.ButtonStyle.danger
                if key == "flee"
                else discord.ButtonStyle.secondary,
            )

            async def callback(i, action=key, bid=b["id"], turn=b["turn"]):
                if i.user.id != self.owner:
                    await i.response.send_message(
                        "This is another adventurer’s battle.", ephemeral=True
                    )
                    return
                await i.response.defer()
                try:
                    before = await self.cog.store.player(i.guild.id, i.user.id)
                    result = await self.cog.action(i.guild.id, i.user.id, bid, turn, action)
                    player = await self.cog.store.player(i.guild.id, i.user.id)
                    if player["battle"]:
                        await i.edit_original_response(
                            embed=battle_embed(player),
                            view=BattleView(self.cog, self.owner, player),
                        )
                    else:
                        await i.edit_original_response(
                            content=result,
                            embed=None,
                            attachments=[],
                            view=None,
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    if not player["battle"] and before["tutorial"] < 6:
                        prefix = await guild_prefix(self.cog.bot, i.guild)
                        await i.followup.send(embed=tutorial_embed(player, prefix), ephemeral=True)
                    self.stop()
                    self.cog.views.discard(self)
                except RuleError as e:
                    await i.followup.send(str(e), ephemeral=True)

            btn.callback = callback
            self.add_item(btn)


class SpawnView(SafeView):
    def __init__(self, cog, spawn_id):
        super().__init__(cog)
        btn = discord.ui.Button(
            label="Engage", style=discord.ButtonStyle.danger, custom_id=f"ab:spawn:{spawn_id}"
        )

        async def callback(i):
            await i.response.defer(ephemeral=True)
            try:
                await self.cog.claim_spawn(i, spawn_id)
                btn.disabled = True
                await i.message.edit(view=self)
                self.stop()
                self.cog.views.discard(self)
            except RuleError as e:
                await i.followup.send(str(e), ephemeral=True)

        btn.callback = callback
        self.add_item(btn)


class RoleView(SafeView):
    def __init__(self, cog):
        super().__init__(cog)
        for key, label in (
            ("trading", "Trading alerts"),
            ("boss", "Boss alerts"),
            ("adventures", "Adventure alerts"),
        ):
            btn = discord.ui.Button(label=label, custom_id=f"ab:role:{key}")

            async def callback(i, k=key):
                await i.response.defer(ephemeral=True)
                settings = await self.cog.store.settings(i.guild.id)
                role = i.guild.get_role(settings.get("roles", {}).get(k, 0))
                if not role:
                    await i.followup.send(
                        "Role is missing. Ask an admin to rerun aetherset setup.", ephemeral=True
                    )
                    return
                # Never grant a role that was repurposed into a privileged role.
                if role.permissions.value or role.managed or role >= i.guild.me.top_role:
                    await i.followup.send(
                        "This role is no longer a safe notification role. Ask an admin to repair setup.",
                        ephemeral=True,
                    )
                    return
                async with self.cog.role_locks[(i.guild.id, i.user.id)]:
                    member = await i.guild.fetch_member(i.user.id)
                    if role in member.roles:
                        await member.remove_roles(role, reason="Aetherbound notification opt-out")
                        message = f"Unsubscribed from {role.name}."
                    else:
                        await member.add_roles(role, reason="Aetherbound notification opt-in")
                        message = f"Subscribed to {role.name}."
                await i.followup.send(message, ephemeral=True)

            btn.callback = callback
            self.add_item(btn)


class GuideView(RoleView):
    """Persistent, read-only personal help; never creates example rewards or battles."""

    def __init__(self, cog, include_roles=True):
        super().__init__(cog)
        if not include_roles:
            self.clear_items()
        for key, label in (
            ("tutorial", "My next step"),
            ("profile", "My profile"),
            ("shop", "Tavern shop"),
        ):
            button = discord.ui.Button(
                label=label,
                custom_id=f"ab:guide:{key}",
                style=discord.ButtonStyle.primary,
                row=1 if include_roles else 0,
            )

            async def callback(i, kind=key):
                await i.response.defer(ephemeral=True)
                prefix = await guild_prefix(self.cog.bot, i.guild)
                p = await self.cog.store.player(i.guild.id, i.user.id)
                if p:
                    if kind == "profile":
                        await i.followup.send(
                            view=ProfileView(self.cog, i.user.id, p, prefix),
                            ephemeral=True,
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                        return
                    if kind == "shop":
                        offers = await self.cog.store.change(
                            i.guild.id,
                            i.user.id,
                            lambda p, c: economy.shop(p, i.guild.id, i.user.id),
                        )
                        p = await self.cog.store.player(i.guild.id, i.user.id)
                        embed = shop_embed(offers, p["gold"], prefix)
                    else:
                        embed = tutorial_embed(p, prefix)
                else:
                    settings = await self.cog.store.settings(i.guild.id)
                    embed = channel_embed("guide", settings, prefix)
                await i.followup.send(
                    embed=embed, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
                )

            button.callback = callback
            self.add_item(button)


class ProfileView(discord.ui.LayoutView):
    """Private Components V2 character sheet; all tabs reload the saved character."""

    def __init__(self, cog, owner, player, prefix):
        super().__init__(timeout=180)
        self.cog = cog
        self.owner = owner
        self.page = "Overview"
        cog.views.add(self)
        self.render(player, prefix)

    async def interaction_check(self, i):
        if i.user.id != self.owner:
            await i.response.send_message("Open your own profile using My profile.", ephemeral=True)
            return False
        return await SafeView.interaction_check(self, i)

    async def on_timeout(self):
        self.cog.views.discard(self)

    async def on_error(self, i, error, item):
        log.exception("Private profile interaction failed", exc_info=error)
        send = i.followup.send if i.response.is_done() else i.response.send_message
        await send(
            "Could not refresh your profile. Open it again using My profile.", ephemeral=True
        )

    def render(self, player, prefix):
        sheet = profile_embed(player, prefix)
        self.clear_items()
        panel = discord.ui.Container(accent_colour=0x836FFF)
        panel.add_item(discord.ui.TextDisplay(f"## {sheet.title}\n{sheet.description}"))
        panel.add_item(discord.ui.Separator())
        nav = discord.ui.ActionRow()
        for name in ("Overview", "Combat", "Equipment", "Refresh"):
            button = discord.ui.Button(
                label=name,
                style=discord.ButtonStyle.primary
                if name == self.page
                else discord.ButtonStyle.secondary,
            )

            async def callback(i, page=name):
                await i.response.defer()
                p = await self.cog.store.player(i.guild.id, self.owner)
                if not p:
                    await i.followup.send(
                        "Your character no longer exists. Create a new hero to open a profile.",
                        ephemeral=True,
                    )
                    self.stop()
                    self.cog.views.discard(self)
                    return
                if page != "Refresh":
                    self.page = page
                prefix = await guild_prefix(self.cog.bot, i.guild)
                self.render(p, prefix)
                await i.edit_original_response(
                    view=self, allowed_mentions=discord.AllowedMentions.none()
                )

            button.callback = callback
            nav.add_item(button)
        panel.add_item(nav)
        fields = {
            "Overview": {"✧ Journey", "◈ Supplies & feats", "Next move"},
            "Combat": {"⚔ Combat", "✦ Attributes", "✺ Active gear effects"},
            "Equipment": {"⚔ Weapons", "⛨ Armor", "✧ Accessories", "✺ Active gear effects"},
        }[self.page]
        for field in sheet.fields:
            if field.name in fields:
                panel.add_item(discord.ui.Separator())
                panel.add_item(discord.ui.TextDisplay(f"### {field.name}\n{field.value}"))
        if self.page == "Equipment":
            panel.add_item(
                discord.ui.TextDisplay(
                    f"-# Manage gear in adventures: `{prefix}aether inventory` then `{prefix}aether equip ID1 ID2`."
                )
            )
        if self.page == "Combat":
            panel.add_item(discord.ui.TextDisplay(f"-# {sheet.footer.text}"))
        panel.add_item(
            discord.ui.TextDisplay(
                "-# Only you can see this • Tabs refresh saved stats • Controls expire after 3 minutes of inactivity; reopen with My profile"
            )
        )
        self.add_item(panel)


class ProfileLauncher(SafeView):
    """Prefix commands cannot reply ephemerally; this temporary button can."""

    def __init__(self, cog, owner):
        super().__init__(cog)
        self.owner = owner
        self.timeout = 30
        button = discord.ui.Button(
            label="Open my private profile", style=discord.ButtonStyle.primary
        )

        async def callback(i):
            await i.response.defer(ephemeral=True)
            player = await self.cog.store.player(i.guild.id, self.owner)
            if not player:
                await i.followup.send(
                    "Create a character first, then open your profile.", ephemeral=True
                )
                return
            prefix = await guild_prefix(self.cog.bot, i.guild)
            await i.followup.send(
                view=ProfileView(cog, self.owner, player, prefix),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        button.callback = callback
        self.add_item(button)

    async def interaction_check(self, i):
        if i.user.id != self.owner:
            await i.response.send_message(
                "Use My profile on a channel guide to open your own character.", ephemeral=True
            )
            return False
        return await super().interaction_check(i)

    async def on_timeout(self):
        self.cog.views.discard(self)
