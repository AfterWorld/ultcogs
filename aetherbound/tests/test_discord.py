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
