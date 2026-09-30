"""Run: python guesscandy/test_game.py. Real discord.py, lightweight Red Config stand-in."""
import asyncio
import copy
import hashlib
import json
import sys
import time
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from discord.ext import commands

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))


class Value:
    def __init__(self, data, key=None):
        self.data, self.key = data, key

    def __call__(self):
        return self

    def __await__(self):
        async def read():
            await asyncio.sleep(0)
            return copy.deepcopy(self.data if self.key is None else self.data[self.key])
        return read().__await__()

    async def __aenter__(self):
        return self.data if self.key is None else self.data[self.key]

    async def __aexit__(self, *args):
        return False

    async def set(self, value):
        self.data[self.key] = value


class Group:
    def __init__(self, data):
        self.data = data

    def all(self):
        return Value(self.data)

    def get_attr(self, key):
        return Value(self.data, key)

    def __getattr__(self, key):
        return Value(self.data, key)


class FakeConfig:
    @classmethod
    def get_conf(cls, *args, **kwargs):
        return cls()

    def register_guild(self, **defaults):
        self.defaults = defaults
        self.guilds = {}

    def guild_from_id(self, guild_id):
        return Group(self.guilds.setdefault(guild_id, copy.deepcopy(self.defaults)))

    def guild(self, guild):
        return self.guild_from_id(guild.id)

    async def all_guilds(self):
        return copy.deepcopy(self.guilds)


# Only the Red-specific surfaces are replaced; Discord command registration is real.
commands.admin_or_permissions = lambda **permissions: commands.has_guild_permissions(**permissions)
red = types.ModuleType("redbot")
core = types.ModuleType("redbot.core")
core.Config, core.commands = FakeConfig, commands
utils = types.ModuleType("redbot.core.utils")
formatting = types.ModuleType("redbot.core.utils.chat_formatting")
formatting.pagify = lambda text: [text]
sys.modules.update({"redbot": red, "redbot.core": core, "redbot.core.utils": utils,
                    "redbot.core.utils.chat_formatting": formatting})

from guesscandy.content import CANDIES
from guesscandy.engine import matches, season, tally
from guesscandy.guesscandy import EMPTY, GuessCandy


class Rules(unittest.TestCase):
    def test_aliases_and_no_substring_win(self):
        self.assertTrue(matches("KIT-KAT!", CANDIES["kitkat"]))
        self.assertTrue(matches("gummi bears", CANDIES["bears"]))
        self.assertFalse(matches("I think it is kit kat", CANDIES["kitkat"]))
        self.assertFalse(matches("kit kat", CANDIES["chunky"]))

    def test_october_local_boundaries(self):
        dt = lambda date: datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        self.assertIsNone(season(dt("2026-10-01T04:59:59"), -300, True))
        self.assertEqual(season(dt("2026-10-01T05:00:00"), -300, True), "2026")
        self.assertEqual(season(dt("2026-11-01T04:59:59"), -300, True), "2026")
        self.assertIsNone(season(dt("2026-11-01T05:00:00"), -300, True))
        self.assertEqual(season(dt("2027-01-01T12:00:00"), -300, False), "2027")

    def test_milestones_exactly_once_and_specific_candy(self):
        record = copy.deepcopy(EMPTY)
        rewards = {"1": dict(candy="corn", count=2, bonus=100, label="Corn champion"),
                   "2": dict(candy="any", count=3, bonus=50, label="Collector")}
        self.assertEqual(tally(record, "corn", 10, rewards), [])
        self.assertEqual(len(tally(record, "corn", 10, rewards)), 1)
        self.assertEqual(len(tally(record, "bears", 15, rewards)), 1)
        self.assertEqual(tally(record, "corn", 10, rewards), [])
        self.assertEqual(record["points"], 195)
        self.assertEqual(record["bag"], {"corn": 3, "bears": 1})

    def test_photos_and_nonoverlapping_answers(self):
        from PIL import Image
        credits = json.loads((ROOT / "photos" / "credits.json").read_text())
        for candy in CANDIES.values():
            with Image.open(ROOT / "photos" / candy["file"]) as photo:
                photo.verify()
        for credit in credits:
            self.assertEqual(hashlib.sha256((ROOT / "photos" / credit["filename"]).read_bytes()).hexdigest(), credit["sha256"])
        self.assertEqual(sum(c["weight"] for c in CANDIES.values()), 100)
        for key, candy in CANDIES.items():
            for other, other_candy in CANDIES.items():
                if key != other:
                    self.assertFalse(any(matches(a, other_candy) for a in candy["aliases"]))


class Listener(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = types.SimpleNamespace(cog_disabled_in_guild=AsyncMock(return_value=False),
            allowed_by_whitelist_blacklist=AsyncMock(return_value=True),
            get_context=AsyncMock(return_value=types.SimpleNamespace(valid=False)))
        self.cog = GuessCandy(self.bot)
        self.guild = types.SimpleNamespace(id=1, me=object())
        self.channel = types.SimpleNamespace(id=2, guild=self.guild, send=AsyncMock(),
            permissions_for=lambda member: types.SimpleNamespace(view_channel=True, send_messages=True, embed_links=True, attach_files=True))
        self.channel.send.return_value = types.SimpleNamespace(id=100, edit=AsyncMock())
        self.settings = self.cog.config.guild(self.guild).data
        self.settings.update(enabled=True, channel=2, october_only=False, users=2, messages=2, cooldown=30)

    async def asyncTearDown(self):
        self.cog.cog_unload()
        await asyncio.sleep(0)

    def message(self, user=10, content="candy corn", mid=200):
        return types.SimpleNamespace(guild=self.guild, channel=self.channel, id=mid, content=content,
            webhook_id=None, author=types.SimpleNamespace(id=user, bot=False, mention=f"<@{user}>"))

    async def make_round(self):
        await self.cog.spawn(self.channel, self.settings)
        self.cog.rounds[1].update(candy=CANDIES["corn"], candy_id="corn", points=10)

    async def test_simultaneous_winners(self):
        await self.make_round()
        await asyncio.gather(self.cog.on_message(self.message()), self.cog.on_message(self.message(user=11)))
        records = next(iter(self.settings["seasons"].values()))
        self.assertEqual(sum(r["caught"] for r in records.values()), 1)
        self.assertEqual(sum(r["points"] for r in records.values()), 10)
        self.assertNotIn(1, self.cog.rounds)

    async def test_expired_and_old_messages_cannot_win(self):
        await self.make_round()
        await self.cog.on_message(self.message(mid=99))
        self.assertEqual(self.settings["seasons"], {})
        self.cog.rounds[1]["deadline"] = time.monotonic() - 1
        await self.cog.on_message(self.message())
        self.assertEqual(self.settings["seasons"], {})
        self.assertNotIn(1, self.cog.rounds)

    async def test_activity_requires_distinct_users_and_ignores_spam(self):
        self.cog.activity[1] = dict(count=0, speakers=set(), last={}, started=time.monotonic()-31)
        await self.cog.on_message(self.message(content="hello"))
        await self.cog.on_message(self.message(content="hello"))
        self.assertEqual(self.cog.activity[1]["count"], 1)
        self.assertNotIn(1, self.cog.rounds)
        await self.cog.on_message(self.message(user=11, content="hello"))
        self.assertIn(1, self.cog.rounds)

    async def test_disabled_and_blocked_users(self):
        await self.make_round()
        self.bot.allowed_by_whitelist_blacklist.return_value = False
        await self.cog.on_message(self.message())
        self.bot.allowed_by_whitelist_blacklist.return_value = True
        self.bot.cog_disabled_in_guild.return_value = True
        await self.cog.on_message(self.message())
        self.assertEqual(self.settings["seasons"], {})

    async def test_deletion_and_reload_persistence(self):
        await self.make_round()
        await self.cog.on_message(self.message())
        self.cog.cog_unload()
        reloaded = GuessCandy(self.bot)
        reloaded.config = self.cog.config
        self.assertEqual(next(iter(self.settings["seasons"].values()))["10"]["points"], 10)
        self.assertEqual(reloaded.rounds, {})
        await reloaded.red_delete_data_for_user(requester="discord_deleted_user", user_id=10)
        self.assertTrue(all("10" not in records for records in self.settings["seasons"].values()))

    async def test_upload_failure_does_not_create_round(self):
        import discord
        self.channel.send.side_effect = discord.Forbidden(types.SimpleNamespace(status=403, reason="Forbidden"), "No uploads")
        with self.assertLogs("red.guesscandy", level="WARNING"):
            self.assertFalse(await self.cog.spawn(self.channel, self.settings))
        self.assertEqual(self.cog.rounds, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
