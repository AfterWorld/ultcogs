import asyncio
from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import discord
from PIL import Image
import pytest

from mrwhite.engine import Role, RuleError
from mrwhite.graphics import render_banner
from mrwhite.mrwhite import MrWhite, TIMEOUTS
from mrwhite.session import Session
from mrwhite.views import EntryModal, GameView
from mrwhite.words import DEFAULT_PAIRS


def member(uid, mod=False):
    return NS(id=uid, display_name=f"Crew {uid}", bot=False,
              guild_permissions=NS(manage_guild=mod), send=AsyncMock())


def session():
    message = NS(attachments=[], jump_url="https://discord.com/channels/1/2/3")
    message.edit = AsyncMock(return_value=message)
    ctx = NS(author=member(1), channel=NS(id=2, permissions_for=lambda _: NS(attach_files=False)),
             guild=NS(id=1, me=object()), send=AsyncMock(return_value=message))
    bot = NS(is_owner=AsyncMock(return_value=False),
             allowed_by_whitelist_blacklist=AsyncMock(return_value=True),
             cog_disabled_in_guild=AsyncMock(return_value=False))
    cog = NS(games={}, bot=bot)
    s = Session(cog,ctx,{"pairs":deepcopy(DEFAULT_PAIRS),"timeouts":deepcopy(TIMEOUTS)})
    cog.games[2] = s
    return s


async def begun(n=4):
    s = session()
    for p in range(2,n+1):
        s.game.join(p,f"Crew {p}")
    await s.act(member(1),"begin")
    return s


@pytest.mark.asyncio
async def test_host_guards_transfer_and_kick():
    s = session()
    try:
        await s.act(member(2),"join")
        await s.act(member(3),"join")
        with pytest.raises(RuleError):
            await s.act(member(2),"begin")
        with pytest.raises(RuleError):
            await s.act(member(2),"end")
        await s.act(member(1),"transfer",2)
        await s.act(member(2),"kick",1)
        assert 1 not in s.game.players
        await s.act(member(99,True),"end")
        assert not s.active and not s.cog.games
    finally:
        s.close()


@pytest.mark.asyncio
async def test_simultaneous_begin_and_old_modal():
    s = session()
    s.game.join(2,"Two")
    s.game.join(3,"Three")
    results = await asyncio.gather(s.act(member(1),"begin"),s.act(member(1),"begin"),return_exceptions=True)
    try:
        assert sum(isinstance(r,RuleError) for r in results) == 1
        assert s.game.round == 1
        epoch = s.game.epoch
        s.game.expire()
        with pytest.raises(RuleError,match="expired"):
            await s.act(member(1),"say","clue",epoch)
        assert not s.game.clues
    finally:
        s.close()


@pytest.mark.asyncio
async def test_simultaneous_last_votes_resolve_once():
    s = await begun(4)
    try:
        s.game.open_vote()
        epoch = s.game.epoch
        target = next(p for p,r in s.game.roles.items() if r == Role.CIVILIAN)
        voters = [p for p in s.game.alive if p != target]
        s.game.vote(target,voters[0])
        await asyncio.gather(*(s.act(member(p),"vote",target,epoch) for p in voters))
        assert s.game.eliminated == {target}
        assert s.game.round == 2
        with pytest.raises(RuleError):
            await s.act(member(voters[0]),"vote",target,epoch)
    finally:
        s.close()


@pytest.mark.asyncio
async def test_absolute_deadline_does_not_extend_and_stale_timer():
    s = await begun()
    try:
        deadline = s.deadline
        await s.act(member(1),"say","rope")
        assert deadline == s.deadline
        old_epoch = s.game.epoch
        s.game.expire()
        await s.publish()
        await s.wait_deadline(old_epoch,0)
        assert s.game.phase == "voting"
        s.deadline = 1
        with pytest.raises(RuleError,match="deadline"):
            await s.act(member(2),"vote",1)
        assert s.game.phase == "ended" and not s.cog.games
    finally:
        s.close()


@pytest.mark.asyncio
async def test_send_failure_closes_session_and_end_is_idempotent():
    s = await begun()
    s.message.edit.side_effect = discord.Forbidden(NS(status=403,reason="Forbidden"),"no permission")
    with pytest.raises(discord.Forbidden):
        await s.act(member(1),"say","rope")
    assert not s.active and not s.cog.games and s.view.is_finished()
    s.close()
    await asyncio.sleep(0)
    assert s.timer.done()


@pytest.mark.asyncio
async def test_role_private_outsider_and_closed_dm():
    s = await begun()
    try:
        with pytest.raises(RuleError):
            await s.act(member(99),"role")
        interaction = NS(user=member(1),channel_id=2,guild=s.ctx.guild,
                         response=NS(defer=AsyncMock()),followup=NS(send=AsyncMock()))
        before = s.ctx.send.call_count
        await s.interact(interaction,"role",epoch=s.game.epoch)
        assert interaction.followup.send.call_args.kwargs["ephemeral"] is True
        assert s.ctx.send.call_count == before
        s.ctx.author.send.side_effect = discord.Forbidden(NS(status=403,reason="Forbidden"),"DM closed")
        await MrWhite.role.callback(s.cog,s.ctx)
        assert "My secret dossier" in s.ctx.send.call_args.args[0]
        for message in s.ctx.send.call_args_list:
            assert s.game.pair[0] not in str(message) and s.game.pair[1] not in str(message)
    finally:
        s.close()


@pytest.mark.asyncio
async def test_red_disabled_component_and_empty_pairs():
    s = session()
    try:
        s.settings["pairs"] = []
        with pytest.raises(RuleError,match="No word pairs"):
            await s.act(member(1),"begin")
        s.cog.bot.cog_disabled_in_guild.return_value = True
        interaction = NS(user=member(2),channel_id=2,guild=s.ctx.guild,
                         response=NS(defer=AsyncMock()),followup=NS(send=AsyncMock()))
        await s.interact(interaction,"join")
        assert 2 not in s.game.players
    finally:
        s.close()


@pytest.mark.asyncio
async def test_maximum_ui_limits_no_secret_and_full_clues():
    s = await begun(25)
    try:
        for p in s.game.players:
            s.game.players[p] = "*"*40
            s.game.clues[p] = "*"*80
        embed = s.embed()
        assert len(embed) <= 6000
        assert all(len(f.value)<=1024 for f in embed.fields)
        assert s.game.pair[0] not in str(embed.to_dict())
        s.game.open_vote()
        view = GameView(s)
        ballot = next(i for i in view.children if isinstance(i,discord.ui.Select))
        assert len(ballot.options) == 25
        assert EntryModal(s,"say",s.game.epoch).entry.max_length == 80
        view.stop()
    finally:
        s.close()


@pytest.mark.asyncio
async def test_unload_cancels_sessions():
    s = await begun()
    await MrWhite.cog_unload(s.cog)
    assert not s.cog.games and s.timer.done() and s.view.is_finished()


def test_compatibility_commands_and_config_identifier(monkeypatch):
    config = MagicMock()
    monkeypatch.setattr("mrwhite.mrwhite.Config.get_conf",config)
    cog = MrWhite(NS())
    assert config.call_args.kwargs["identifier"] == 1234567890
    defaults = config.return_value.register_guild.call_args.kwargs
    assert "words" in defaults and "pairs" in defaults
    commands = {c.name for c in cog.mrwhite.commands}
    assert {"start","join","begin","say","vote","guess","end","addword","removeword","words"} <= commands
    assert "mw" in cog.mrwhite.aliases
    assert cog.mrwhite.get_command("s") is cog.say
    assert cog.mrwhite.get_command("new") is cog.start


@pytest.mark.parametrize("phase",["joining","playing","voting","guessing","ended"])
def test_graphics_png(phase):
    image = Image.open(BytesIO(render_banner(phase)))
    assert image.size == (1000,475) and image.format == "PNG"
