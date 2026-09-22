import asyncio
import time
from collections import defaultdict
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from aetherbound import engine as g
from aetherbound.aetherbound import Aetherbound
from aetherbound.setup_server import provision
from aetherbound.store import Store
from aetherbound.views import BattleView, RoleView

from .test_engine import graduate


@pytest.fixture
async def cog(tmp_path):
    c = object.__new__(Aetherbound)
    c.store = Store(tmp_path / "test.db")
    await c.store.initialize()
    c.bot = NS(
        cog_disabled_in_guild=AsyncMock(return_value=False),
        allowed_by_whitelist_blacklist=AsyncMock(return_value=True),
        intents=NS(message_content=True),
        get_valid_prefixes=AsyncMock(return_value=["."]),
    )
    c.views = set()
    c.guild_locks = defaultdict(asyncio.Lock)
    c.role_locks = defaultdict(asyncio.Lock)
    import random

    c.rng = random.Random(1)
    yield c
    for v in c.views:
        v.stop()


def interaction(uid=5, gid=1):
    return NS(
        user=NS(id=uid),
        guild=NS(id=gid),
        response=NS(defer=AsyncMock(), send_message=AsyncMock()),
        followup=NS(send=AsyncMock()),
        edit_original_response=AsyncMock(),
    )


async def test_view_rejects_other_player(cog):
    p = graduate()
    g.begin(p, "slime")
    view = BattleView(cog, 5, p)
    i = interaction(uid=6)
    await view.children[0].callback(i)
    i.response.send_message.assert_awaited_once()
    i.response.defer.assert_not_awaited()


async def test_view_respects_disabled_cog(cog):
    p = graduate()
    g.begin(p, "slime")
    view = BattleView(cog, 5, p)
    cog.bot.cog_disabled_in_guild.return_value = True
    assert not await view.interaction_check(interaction())


async def test_real_red_registration():
    # Verify command decorators are actual Red objects and no names collide internally.
    names = [c.qualified_name for c in Aetherbound.__cog_commands__]
    assert len(names) == len(set(names))
    assert "aetherset setup" in names and "aether tutorial" in names


async def test_spawn_claim_once(cog):
    for user in (5, 6):
        await cog.store.change(1, user, lambda p, c: graduate(), create=True)
    await cog.store.settings(1, {"channels": {"adventures": 11}})
    await cog.store.transaction(
        lambda c: c.execute(
            "INSERT INTO spawns VALUES(?,?,?,?,?,?,0)",
            ("spawn", 1, 10, 55, "slime", time.time() + 300),
        )
    )
    cog.publish_battle = AsyncMock(return_value=NS(jump_url="https://discord.com/test"))

    async def claim(user):
        i = interaction(user)
        i.guild.get_channel = lambda cid: NS(id=11)
        await cog.claim_spawn(i, "spawn")

    results = await asyncio.gather(claim(5), claim(6), return_exceptions=True)
    assert sum(isinstance(x, g.RuleError) for x in results) == 1
    assert sum([bool((await cog.store.player(1, u))["battle"]) for u in (5, 6)]) == 1


async def test_spawn_failure_does_not_consume_claim(cog):
    await cog.store.change(1, 5, lambda p, c: g.new_player("Newbie", "vanguard"), create=True)
    await cog.store.settings(1, {"channels": {"adventures": 11}})
    await cog.store.transaction(
        lambda c: c.execute(
            "INSERT INTO spawns VALUES(?,?,?,?,?,?,0)",
            ("spawn", 1, 10, 55, "slime", time.time() + 300),
        )
    )
    i = interaction()
    i.guild.get_channel = lambda cid: NS(id=11)
    with pytest.raises(g.RuleError):
        await cog.claim_spawn(i, "spawn")
    assert (await cog.store.rows("spawns"))[0]["claimed"] == 0


async def trade_message(cog, content, mid=8, cid=10):
    await cog.store.settings(1, {"channels": {"trading": 10}})
    thread = NS(id=100, mention="<#100>", send=AsyncMock())
    return NS(
        id=mid,
        guild=NS(id=1, get_role=lambda _: None),
        channel=NS(id=cid, send=AsyncMock()),
        author=NS(id=5, bot=False),
        content=content,
        attachments=[],
        delete=AsyncMock(),
        create_thread=AsyncMock(return_value=thread),
    )


async def test_trade_opens_single_thread(cog):
    m = await trade_message(cog, "trading iron sword for item")
    await asyncio.gather(cog.moderate_trade(m), cog.moderate_trade(m))
    m.create_thread.assert_awaited_once()
    m.delete.assert_not_awaited()
    assert (await cog.store.rows("trades"))[0]["thread"] == 100


async def test_normal_chat_deleted_but_thread_chat_allowed(cog):
    m = await trade_message(cog, "hey how are you?")
    await cog.moderate_trade(m)
    m.delete.assert_awaited_once()
    m.create_thread.assert_not_awaited()
    m = await trade_message(cog, "hey how are you?", cid=100)
    await cog.moderate_trade(m)
    m.delete.assert_not_awaited()


async def test_trade_edit_to_chatter_deleted(cog):
    m = await trade_message(cog, "trading iron sword for item")
    await cog.moderate_trade(m)
    m.content = "hello everyone"
    await cog.moderate_trade(m)
    m.delete.assert_awaited_once()


async def test_role_never_grants_privileges(cog):
    await cog.store.settings(1, {"roles": {"trading": 25}})
    role = NS(permissions=discord.Permissions(administrator=True), managed=False)
    i = interaction()
    i.guild.get_role = lambda _: role
    v = RoleView(cog)
    await v.children[0].callback(i)
    assert "safe notification role" in i.followup.send.call_args.args[0]


class FakeRole:
    def __init__(self, rid, name="role"):
        self.id = rid
        self.name = name
        self.mention = f"<@&{rid}>"
        self.permissions = discord.Permissions.none()
        self.managed = False

    def __ge__(self, other):
        return self.id == 9999


class FakeGuild:
    def __init__(self):
        self.id = 1
        self.default_role = FakeRole(1)
        self.me = FakeRole(2)
        self.me.top_role = FakeRole(999)
        self.me.guild_permissions = discord.Permissions.all()
        self.channels = {}
        self.roles = {}
        self.categories = []
        self.counter = 10
        for position in range(6):
            cat = MagicMock(spec=discord.CategoryChannel, id=position + 1000, position=position)
            self.categories.append(cat)

    def get_channel(self, cid):
        return self.channels.get(cid)

    def get_role(self, rid):
        return self.roles.get(rid)

    async def create_role(self, **kwargs):
        self.counter += 1
        r = FakeRole(self.counter, kwargs["name"])
        self.roles[r.id] = r
        return r

    async def create_category(self, *args, **kwargs):
        self.counter += 1
        cat = MagicMock(spec=discord.CategoryChannel, id=self.counter, position=10)
        cat.move = AsyncMock()
        self.channels[cat.id] = cat
        self.categories.append(cat)
        return cat

    async def create_text_channel(self, *args, **kwargs):
        self.counter += 1
        channel = MagicMock(spec=discord.TextChannel, id=self.counter)
        channel.edit = AsyncMock()
        message = NS(id=self.counter + 100, edit=AsyncMock())
        channel.send = AsyncMock(return_value=message)
        channel.fetch_message = AsyncMock(return_value=message)
        channel.initial = kwargs
        self.channels[channel.id] = channel
        return channel


async def test_setup_idempotent_permissions_and_position(cog):
    guild = FakeGuild()
    first = await provision(cog, guild)
    ids = dict(first["channels"])
    roleids = dict(first["roles"])
    category = guild.get_channel(first["category"])
    assert category.move.call_args.kwargs["before"].position == 2
    spawn = guild.get_channel(ids["spawns"])
    ow = spawn.initial["overwrites"][guild.default_role]
    assert ow.send_messages is False and ow.view_channel is True
    trade = guild.get_channel(ids["trading"])
    assert trade.initial["overwrites"][guild.default_role].send_messages_in_threads is True
    second = await provision(cog, guild)
    assert second["channels"] == ids and second["roles"] == roleids
    assert len(guild.roles) == 3
    del guild.channels[ids["spawns"]]
    third = await provision(cog, guild)
    assert third["channels"]["spawns"] != ids["spawns"]
    assert third["channels"]["trading"] == ids["trading"]


async def test_missing_permissions_no_partial_setup(cog):
    guild = FakeGuild()
    guild.me.guild_permissions = discord.Permissions.none()
    with pytest.raises(g.RuleError):
        await provision(cog, guild)
    assert not guild.roles and not guild.channels


async def test_root_commands_do_not_collide_with_existing_adventure():
    names = {c.name for c in Aetherbound.__cog_commands__ if c.parent is None}
    assert names == {"aether", "aetherset"}


async def test_role_opt_in_and_out(cog):
    await cog.store.settings(1, {"roles": {"trading": 25}})
    role = FakeRole(25, "Trading")
    member = NS(roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
    i = interaction()
    i.guild.get_role = lambda _: role
    i.guild.me = NS(top_role=FakeRole(999))
    i.guild.fetch_member = AsyncMock(return_value=member)
    v = RoleView(cog)
    await v.children[0].callback(i)
    member.add_roles.assert_awaited_once()
    member.roles = [role]
    await v.children[0].callback(i)
    member.remove_roles.assert_awaited_once()


async def test_restore_view_uses_saved_turn(cog):
    p = graduate()
    g.begin(p, "slime")
    g.act(p, p["battle"]["id"], 0, "guard", cog.rng)
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    restored = await cog.store.player(1, 5)
    view = BattleView(cog, 5, restored)
    assert all(f":{p['battle']['id']}:1:" in button.custom_id for button in view.children)
    i = interaction()
    await view.children[0].callback(i)
    assert (await cog.store.player(1, 5))["battle"]["turn"] == 2
    i.edit_original_response.assert_awaited_once()


async def test_pending_trade_reuses_existing_discord_thread(cog):
    m = await trade_message(cog, "trading iron sword for item")
    await cog.store.transaction(
        lambda c: c.execute(
            "INSERT INTO trades VALUES(?,?,?,?,?)", (m.id, 1, 5, 0, time.time() - 100)
        )
    )
    thread = MagicMock(spec=discord.Thread, id=m.id)
    thread.send = AsyncMock()
    cog.bot.fetch_channel = AsyncMock(return_value=thread)
    await cog.moderate_trade(m)
    m.create_thread.assert_not_awaited()
    assert (await cog.store.rows("trades"))[0]["thread"] == m.id


async def test_spawn_delivery_failure_keeps_battle_recoverable(cog):
    await cog.store.change(1, 5, lambda p, c: graduate(), create=True)
    await cog.store.settings(1, {"channels": {"adventures": 11}})
    await cog.store.transaction(
        lambda c: c.execute(
            "INSERT INTO spawns VALUES(?,?,?,?,?,?,0)",
            ("spawn", 1, 10, 55, "slime", time.time() + 300),
        )
    )
    cog.publish_battle = AsyncMock(
        side_effect=discord.Forbidden(NS(status=403, reason="Forbidden"), "denied")
    )
    i = interaction()
    i.guild.get_channel = lambda _: NS(id=11)
    await cog.claim_spawn(i, "spawn")
    assert (await cog.store.player(1, 5))["battle"] is not None
    assert "resume" in i.followup.send.call_args.args[0]


async def test_channel_panels_upgrade_in_place_and_private_live_help(cog):
    from aetherbound.setup_server import refresh_panels
    from aetherbound.views import GuideView

    guild = FakeGuild()
    cog.bot.get_valid_prefixes.return_value = ["<@123> ", "!"]
    s = await provision(cog, guild)
    assert set(s["panels"]) == set(s["channels"])
    for key, cid in s["channels"].items():
        channel = guild.get_channel(cid)
        kwargs = channel.send.call_args.kwargs
        assert isinstance(kwargs["embed"], discord.Embed)
        assert len(kwargs["embed"]) < 6000
        assert all(len(f.value) <= 1024 for f in kwargs["embed"].fields)
        assert len(kwargs["view"].children) == (6 if key == "guide" else 3)
    await refresh_panels(cog, guild, s)
    for cid in s["channels"].values():
        channel = guild.get_channel(cid)
        channel.send.assert_awaited_once()
        assert channel.fetch_message.return_value.edit.call_args.kwargs["content"] is None
    await cog.store.change(1, 5, lambda p, c: g.new_player("Hero", "vanguard"), create=True)
    view = GuideView(cog, include_roles=False)
    i = interaction()
    await view.children[0].callback(i)
    kwargs = i.followup.send.call_args.kwargs
    assert kwargs["ephemeral"] is True
    p = await cog.store.player(1, 5)
    assert "!aether equip " + " ".join(p["inventory"]) in kwargs["embed"].description
    assert p["tutorial"] == 0
    i = interaction(uid=99)
    await view.children[1].callback(i)
    assert "Welcome" in i.followup.send.call_args.kwargs["embed"].title
    assert await cog.store.player(1, 99) is None


async def test_batch_equipment_store_rolls_back(cog):
    p = g.new_player("Hero", "vanguard")
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    with pytest.raises(g.RuleError):
        await cog.store.change(
            1, 5, lambda p, c: g.equip_many(p, [next(iter(p["inventory"])), "missing"])
        )
    assert await cog.store.player(1, 5) == p


async def test_profile_live_stats_and_level_cap():
    from aetherbound.presentation import profile_embed

    p = graduate(level=20)
    g.begin(p, "raizen")
    p["battle"]["hp"] = 25
    embed = profile_embed(p, "!")
    assert "MAX LEVEL" in embed.fields[0].value
    assert "HP **25/" in embed.fields[1].value
    assert "!aether resume" in embed.fields[-1].value
    assert sum("Empty" in f.value for f in embed.fields) > 0
    assert len(embed) < 6000


@pytest.mark.parametrize("subcommand", ["", "equip "])
async def test_root_shorthand_dispatches_all_ids(cog, subcommand):
    # Exercise discord.py Group.invoke, including its rewind of unknown subcommands.
    from discord.ext.commands.view import StringView

    p = g.new_player("Hero", "vanguard")
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    root = cog.adventure.copy()
    root.cog = cog
    root.can_run = AsyncMock(return_value=True)
    root.call_before_hooks = AsyncMock()
    root.call_after_hooks = AsyncMock()
    for child in root.commands:
        child.cog = cog
        child.can_run = AsyncMock(return_value=True)
        child.call_before_hooks = AsyncMock()
        child.call_after_hooks = AsyncMock()
    cog.cog_before_invoke = AsyncMock()
    cog.bot.can_run = AsyncMock(return_value=True)
    cog.bot.dispatch = MagicMock()
    ctx = NS(
        view=StringView(subcommand + " ".join(p["inventory"])),
        guild=NS(id=1),
        author=NS(id=5),
        channel=NS(id=10),
        clean_prefix=".",
        send=AsyncMock(),
        send_help=AsyncMock(),
        bot=cog.bot,
        message=NS(attachments=[]),
        command=None,
        interaction=None,
        invoked_with="aether",
        invoked_parents=[],
        command_failed=False,
    )
    await root.invoke(ctx)
    saved = await cog.store.player(1, 5)
    assert set(saved["equipped"]) == {"main", "off"}
    assert saved["tutorial"] == 1


async def test_deleted_guide_recreated_without_duplicate_other_panels(cog):
    from aetherbound.setup_server import refresh_panels

    guild = FakeGuild()
    s = await provision(cog, guild)
    channel = guild.get_channel(s["channels"]["spawns"])
    channel.fetch_message.side_effect = discord.NotFound(NS(status=404, reason="Not Found"), "gone")
    channel.send.return_value = NS(id=999, edit=AsyncMock())
    await refresh_panels(cog, guild, s)
    saved = await cog.store.settings(guild.id)
    assert saved["panels"]["spawns"] == 999
    assert channel.send.await_count == 2
    for key, cid in s["channels"].items():
        if key != "spawns":
            guild.get_channel(cid).send.assert_awaited_once()


async def test_private_profile_v2_tabs_refresh_and_owner(cog):
    from aetherbound.views import ProfileView

    p = graduate()
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    view = ProfileView(cog, 5, p, ".")
    assert isinstance(view, discord.ui.LayoutView)
    assert not await view.interaction_check(interaction(uid=6))
    assert await view.interaction_check(interaction())
    await cog.store.change(1, 5, lambda p, c: p.update(gold=9876))
    nav = next(x for x in view.walk_children() if isinstance(x, discord.ui.ActionRow))
    i = interaction()
    await nav.children[3].callback(i)
    text = "\n".join(
        x.content for x in view.walk_children() if isinstance(x, discord.ui.TextDisplay)
    )
    assert "9,876" in text
    assert i.edit_original_response.call_args.kwargs["view"] is view
    assert "embed" not in i.edit_original_response.call_args.kwargs
    nav = next(x for x in view.walk_children() if isinstance(x, discord.ui.ActionRow))
    await nav.children[2].callback(interaction())
    text = "\n".join(
        x.content for x in view.walk_children() if isinstance(x, discord.ui.TextDisplay)
    )
    assert "Main hand" in text and "Ring II" in text and "Relic" in text
    assert "Journey" not in text
    assert len(text) < 4000
    assert len(list(view.walk_children())) < 40
    assert view.to_components()[0]["type"] == 17
    await view.on_timeout()
    assert view not in cog.views


async def test_guide_profile_is_ephemeral_components(cog):
    from aetherbound.views import GuideView, ProfileView

    await cog.store.change(1, 5, lambda _, c: graduate(), create=True)
    view = GuideView(cog, include_roles=False)
    i = interaction()
    await view.children[1].callback(i)
    kwargs = i.followup.send.call_args.kwargs
    assert kwargs["ephemeral"] is True
    assert isinstance(kwargs["view"], ProfileView)
    assert "embed" not in kwargs and "content" not in kwargs


@pytest.mark.parametrize("can_delete", [True, False])
async def test_prefix_profile_never_posts_character_and_launcher_private(cog, can_delete):
    from aetherbound.views import ProfileLauncher, ProfileView

    await cog.store.change(1, 5, lambda _, c: graduate(), create=True)
    delete = AsyncMock()
    if not can_delete:
        delete.side_effect = discord.Forbidden(NS(status=403, reason="Forbidden"), "denied")
    ctx = NS(guild=NS(id=1), author=NS(id=5), send=AsyncMock(), message=NS(delete=delete))
    await Aetherbound.profile.callback(cog, ctx)
    kwargs = ctx.send.call_args.kwargs
    assert kwargs["delete_after"] == 30 and "embed" not in kwargs
    launcher = kwargs["view"]
    assert isinstance(launcher, ProfileLauncher)
    assert launcher.timeout == 30
    assert not await launcher.interaction_check(interaction(uid=6))
    i = interaction()
    assert await launcher.interaction_check(i)
    await launcher.children[0].callback(i)
    kwargs = i.followup.send.call_args.kwargs
    assert kwargs["ephemeral"] is True and isinstance(kwargs["view"], ProfileView)
    delete.assert_awaited_once()


async def test_private_profile_deleted_character_and_disabled_cog(cog):
    from aetherbound.views import ProfileView

    view = ProfileView(cog, 5, graduate(), ".")
    cog.bot.cog_disabled_in_guild.return_value = True
    assert not await view.interaction_check(interaction())
    nav = next(x for x in view.walk_children() if isinstance(x, discord.ui.ActionRow))
    i = interaction()
    await nav.children[1].callback(i)
    assert i.followup.send.call_args.kwargs["ephemeral"] is True
    i.edit_original_response.assert_not_awaited()
    assert view not in cog.views


async def test_battle_art_attached_saved_retained_and_removed(cog):
    from aetherbound.views import battle_embed

    p = graduate()
    g.begin(p, "slime")
    assert not battle_embed(p).thumbnail.url  # pre-update battles have no attachment
    p["battle"]["art"] = True  # Legacy AI attachment must not receive artist credit.
    assert not battle_embed(p).thumbnail.url
    assert "Redshrike" not in battle_embed(p).footer.text
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    channel = NS(id=11, send=AsyncMock(return_value=NS(id=333)))
    await cog.publish_battle(channel, 1, 5)
    kwargs = channel.send.call_args.kwargs
    assert kwargs["file"].filename == "slime.jpg"
    assert kwargs["embed"].thumbnail.url == "attachment://slime.jpg"
    kwargs["file"].close()
    saved = await cog.store.player(1, 5)
    assert saved["battle"]["art"] == "redshrike-v2"
    assert battle_embed(saved).thumbnail.url == "attachment://slime.jpg"
    await cog.store.change(1, 5, lambda p, c: p["battle"].update(enemy_hp=1))
    view = BattleView(cog, 5, saved)
    i = interaction()
    await view.children[0].callback(i)
    assert i.edit_original_response.call_args.kwargs["attachments"] == []
    assert (await cog.store.player(1, 5))["battle"] is None


async def test_tavern_button_private_and_repeatable(cog):
    from aetherbound.views import GuideView

    await cog.store.change(1, 5, lambda _, c: graduate(), create=True)
    view = GuideView(cog, include_roles=False)
    i = interaction()
    await view.children[2].callback(i)
    saved = await cog.store.player(1, 5)
    await view.children[2].callback(interaction())
    assert await cog.store.player(1, 5) == saved
    assert i.followup.send.call_args.kwargs["ephemeral"] is True
    assert "Daily wares" in i.followup.send.call_args.kwargs["embed"].title


async def test_spawn_art_uploaded(cog):
    guild = FakeGuild()
    s = await provision(cog, guild)
    await cog.spawn_one(guild, "slime")
    kwargs = guild.get_channel(s["channels"]["spawns"]).send.call_args.kwargs
    assert kwargs["embed"].thumbnail.url == "attachment://slime.jpg"
    assert kwargs["file"].filename == "slime.jpg"
    kwargs["file"].close()


async def test_aliases_register_with_real_command_dispatch(cog):
    from discord.ext import commands as dc

    from aetherbound import configure_aliases

    bot = dc.Bot(command_prefix=".", intents=discord.Intents.none())
    configure_aliases(bot, cog)
    bot.add_command(cog.adventure)
    assert bot.get_command("ae equip") is bot.get_command("aether equip")
    assert bot.get_command("a shop") is bot.get_command("aether shop")
    bot.remove_command("aether")
    await bot.close()


async def test_spawn_without_matching_art(cog):
    guild = FakeGuild()
    s = await provision(cog, guild)
    await cog.spawn_one(guild, "tsukara")
    kwargs = guild.get_channel(s["channels"]["spawns"]).send.call_args.kwargs
    assert "file" not in kwargs
    assert kwargs["embed"].thumbnail.url is None
    assert kwargs["view"] is not None


async def test_inventory_buttons_reload_clamp_restrict_and_expire(cog):
    from aetherbound.views import InventoryView

    p = graduate()
    for _ in range(23):
        item = g.make_item("main", rarity="rare")
        p["inventory"][item["id"]] = item
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    view = InventoryView(cog, 5, p, ".")
    assert view.children[0].disabled
    assert not view.children[2].disabled
    stranger = interaction(uid=6)
    await view.children[2].callback(stranger)
    stranger.response.defer.assert_not_awaited()
    assert view.page == 1
    click = interaction()
    await view.children[2].callback(click)
    assert view.page == 2
    assert "Page 2/" in click.edit_original_response.call_args.kwargs["embed"].footer.text
    await cog.store.change(1, 5, lambda p, c: p.update(inventory={}, equipped={}))
    await view.children[1].callback(interaction())
    assert view.page == 1
    assert view.children[0].disabled and view.children[2].disabled
    assert view.embed.fields[0].name == "Your bag is empty"
    view.message = NS(edit=AsyncMock())
    await view.on_timeout()
    assert all(button.disabled for button in view.children)
    assert view not in cog.views
    view.message.edit.assert_awaited_once()


def test_inventory_stats_and_full_bag_embed_limits():
    from aetherbound.loot import RARITIES
    from aetherbound.presentation import inventory_embed

    p = graduate()
    p["inventory"] = {}
    for n in range(200):
        item = g.make_item("main", level=20, rarity="mythic", twohand=True, unique="emberblade")
        item.update(upgrade=5, bonuses={"strength": 5, "vitality": 10})
        p["inventory"][item["id"]] = item
    p["equipped"] = {"main": next(iter(p["inventory"]))}
    for page in range(1, 21):
        embed, actual, pages = inventory_embed(p, page, ".")
        assert actual == page and pages == 20
        assert len(embed) < 6000
        assert all(len(f.name) <= 256 and len(f.value) <= 1024 for f in embed.fields)
        first = embed.fields[0]
        assert RARITIES["mythic"]["icon"] in first.name
        assert "Mythic" not in first.name
        assert "Power 38" in first.value
        assert "Strength +5" in first.value and "Vitality +10" in first.value
        assert "Two-handed" in first.value and "Emberblade" in first.value
        if page == 1:
            assert "Equipped" in first.value


async def test_loot_buttons_equip_and_salvage_preview_revalidates(cog):
    from aetherbound.views import GearActionView

    p = graduate()
    gear = g.make_item("ring2", rarity="rare")
    p["inventory"][gear["id"]] = gear
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    view = GearActionView(cog, 5, [gear["id"]], player=p)
    other = interaction(uid=6)
    await view.children[0].callback(other)
    other.response.defer.assert_not_awaited()
    await cog.store.settings(1, {"features": {"loot_equip": False}})
    await view.children[0].callback(interaction())
    assert (await cog.store.player(1, 5))["equipped"].get("ring2") != gear["id"]
    await cog.store.settings(1, {})
    await view.children[0].callback(interaction())
    assert (await cog.store.player(1, 5))["equipped"]["ring2"] == gear["id"]
    fresh = g.make_item("head")
    await cog.store.change(1, 5, lambda p, c: p["inventory"].update({fresh["id"]: fresh}))
    preview = GearActionView(cog, 5, [fresh["id"]], salvage=True)
    await cog.store.change(1, 5, lambda p, c: g.lock_items(p, [fresh["id"]], True))
    await preview.children[0].callback(interaction())
    assert fresh["id"] in (await cog.store.player(1, 5))["inventory"]
    await cog.store.change(1, 5, lambda p, c: g.lock_items(p, [fresh["id"]], False))
    await preview.children[0].callback(interaction())
    assert fresh["id"] not in (await cog.store.player(1, 5))["inventory"]
    before = await cog.store.player(1, 5)
    await preview.children[0].callback(interaction())
    assert await cog.store.player(1, 5) == before


async def test_cancelled_salvage_cannot_be_confirmed(cog):
    from aetherbound.views import GearActionView

    p = graduate()
    gear = g.make_item("head")
    p["inventory"][gear["id"]] = gear
    await cog.store.change(1, 5, lambda _, c: p, create=True)
    view = GearActionView(cog, 5, [gear["id"]], salvage=True)
    await view.children[1].callback(interaction())
    await view.children[0].callback(interaction())
    assert await cog.store.player(1, 5) == p


async def test_inventory_equip_best_button_owner_and_switch(cog):
    from aetherbound.views import InventoryView

    p = graduate(level=10)
    gear = g.make_item("main", 10, "mythic")
    p["inventory"][gear["id"]] = gear
    await cog.store.change(1, 5, lambda old, c: p, create=True)
    view = InventoryView(cog, 5, p, ".")
    button = next(x for x in view.children if x.label == "Equip best")
    await button.callback(interaction(uid=6))
    assert (await cog.store.player(1, 5))["equipped"] == p["equipped"]
    await cog.store.settings(1, {"features": {"loot_equip": False}})
    await button.callback(interaction())
    assert (await cog.store.player(1, 5))["equipped"] == p["equipped"]
    await cog.store.settings(1, {"features": {"loot_equip": True}})
    i = interaction()
    await button.callback(i)
    saved = await cog.store.player(1, 5)
    assert saved["equipped"]["main"] == gear["id"]
    assert saved["inventory"][gear["id"]]["bound"]
    i.edit_original_response.assert_awaited_once()


async def test_shared_spawn_multiple_players_and_claim_buttons(cog):
    from aetherbound.views import SpawnView

    guild = FakeGuild()
    settings = await provision(cog, guild)
    for uid in (5, 6):
        await cog.store.change(guild.id, uid, lambda old, c: graduate(level=10), create=True)
    guild.get_channel(settings["channels"]["adventures"]).send.return_value = NS(
        id=987, jump_url="https://discord.com/channels/1/2/987"
    )
    cog.boss_refresh_times = {}
    cog.bot.get_channel = guild.get_channel
    channel = guild.get_channel(settings["channels"]["spawns"])
    channel.get_partial_message = MagicMock(return_value=NS(edit=AsyncMock()))
    await cog.spawn_one(guild, "tsukara")
    spawn = (await cog.store.rows("spawns"))[0]
    view = channel.send.call_args.kwargs["view"]
    assert isinstance(view, SpawnView)
    assert [x.label for x in view.children] == ["Engage", "Claim reward"]
    for uid in (5, 6):
        i = interaction(uid=uid, gid=guild.id)
        i.guild = guild
        await cog.claim_spawn(i, spawn["id"])
    assert len(await cog.store.rows("boss_members")) == 2
    assert not (await cog.store.rows("spawns"))[0]["claimed"]
    p = await cog.store.player(guild.id, 5)
    await cog.action(guild.id, 5, p["battle"]["id"], 0, "attack")
    pool = (await cog.store.rows("boss_pools"))[0]
    assert pool["hp"] < pool["maxhp"]
