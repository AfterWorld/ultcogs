import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from redbot.core import Config
from redbot.core._drivers.json import JsonDriver

from mrwhite import setup
from mrwhite.mrwhite import MrWhite


@pytest.mark.asyncio
async def test_real_config_legacy_preserved_and_pair_edits_atomic(tmp_path, monkeypatch):
    name = "MrWhiteTest" + uuid4().hex
    driver = JsonDriver(name, "1234567890", data_path_override=tmp_path)
    config = Config(name, "1234567890", driver, force_registration=True)
    config.register_guild(words=[])
    await config.guild_from_id(123).words.set(["old custom word"])
    monkeypatch.setattr(Config, "get_conf", lambda *a, **k: config)
    cog = MrWhite(NS())
    ctx = NS(guild=NS(id=123), send=AsyncMock())
    await asyncio.gather(cog.edit_pair(ctx,"saffron | cinnamon",False),
                         cog.edit_pair(ctx,"cinnamon | saffron",False))
    pairs = await config.guild(ctx.guild).pairs()
    assert sum(set(p)=={"saffron","cinnamon"} for p in pairs) == 1
    assert await config.guild(ctx.guild).words() == ["old custom word"]
    assert await config.guild_from_id(456).words() != ["old custom word"]
    await cog.edit_pair(ctx,"saffron | cinnamon",True)
    assert not any(set(p)=={"saffron","cinnamon"} for p in await config.guild(ctx.guild).pairs())
    assert "old custom word" in driver.data_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_setup_and_simultaneous_lobby_start(monkeypatch):
    from mrwhite.tests.test_session import session
    from unittest.mock import MagicMock

    config = MagicMock()
    monkeypatch.setattr(Config,"get_conf",config)
    bot = NS(add_cog=AsyncMock())
    await setup(bot)
    cog = bot.add_cog.call_args.args[0]
    s = session()
    config.return_value.guild.return_value.all = AsyncMock(return_value=s.settings)
    await asyncio.gather(MrWhite.start.callback(cog,s.ctx),MrWhite.start.callback(cog,s.ctx))
    assert len(cog.games) == 1
    assert any(c.args and "already running" in c.args[0] for c in s.ctx.send.call_args_list)
    await cog.cog_unload()
