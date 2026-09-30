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
from unittest.mock import AsyncMock, Mock, patch

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
formatting.pagify = lambda text: [text[start:start+1900] for start in range(0, len(text), 1900)]
sys.modules.update({"redbot": red, "redbot.core": core, "redbot.core.utils": utils,
                    "redbot.core.utils.chat_formatting": formatting})

from guesscandy.content import CANDIES, SETS, SIZES
from guesscandy.engine import (catch_points, cooldown_delay, daily_goals, eligible_candies,
    goal_progress, is_finale, matches, season, standings, tally)
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
            self.assertLess((ROOT / "photos" / candy["file"]).stat().st_size, 8_000_000)
            with Image.open(ROOT / "photos" / candy["file"]) as photo:
                photo.verify()
        for credit in credits:
            self.assertEqual(hashlib.sha256((ROOT / "photos" / credit["filename"]).read_bytes()).hexdigest(), credit["sha256"])
        self.assertEqual(len(CANDIES), 36)
        self.assertEqual({c["file"] for c in CANDIES.values()}, {c["filename"] for c in credits})
        self.assertEqual(len(credits), 36)
        self.assertTrue(all(c["weight"] > 0 for c in CANDIES.values()))
        by_file = {c["filename"]: c for c in credits}
        for candy in CANDIES.values():
            self.assertEqual(candy["license"], by_file[candy["file"]]["license"])
        for key, candy in CANDIES.items():
            for other, other_candy in CANDIES.items():
                if key != other:
                    self.assertFalse(any(matches(a, other_candy) for a in candy["aliases"]))

    def test_sizes_and_finale_only_double_catch(self):
        self.assertEqual(catch_points(15, "fun"), 8)
        self.assertEqual(catch_points(10, "regular"), 10)
        self.assertEqual(catch_points(10, "king"), 20)
        self.assertEqual(catch_points(10, "jackpot", True), 100)
        self.assertEqual(catch_points(1, "fun"), 1)
        self.assertEqual(sum(s["weight"] for s in SIZES.values()), 100)

    def test_finale_boundaries_and_exclusive_pool(self):
        date = lambda stamp: datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)
        self.assertFalse(is_finale(date("2026-10-31T04:59:59"), -300))
        self.assertTrue(is_finale(date("2026-10-31T05:00:00"), -300))
        self.assertTrue(is_finale(date("2026-11-01T04:59:59"), -300))
        self.assertFalse(is_finale(date("2026-11-01T05:00:00"), -300))
        self.assertFalse(is_finale(date("2026-10-31T12:00:00"), -300, False))
        self.assertNotIn("bigcup", eligible_candies(False))
        self.assertIn("bigcup", eligible_candies(True))
        self.assertIn("goldcoins", eligible_candies(True))

    def test_random_cooldown_is_bounded_and_sampled_once(self):
        with patch("guesscandy.engine.random.uniform", return_value=700) as uniform:
            self.assertEqual(cooldown_delay(600, 30), 700)
            uniform.assert_called_once_with(420.0, 780.0)
        self.assertEqual(cooldown_delay(600, 0), 600)

    def test_daily_goals_once_and_reset_on_local_day(self):
        record = copy.deepcopy(EMPTY)
        first = tally(record, "corn", 10, {}, day="2026-10-10")
        self.assertEqual(record["points"], 30)
        self.assertEqual(len(first), 1)
        self.assertEqual(tally(record, "corn", 10, {}, day="2026-10-10"), [])
        self.assertEqual(tally(record, "corn", 10, {}, day="2026-10-11")[0]["bonus"], 20)
        self.assertEqual(record["daily"]["bag"], {"corn": 1})
        self.assertEqual(record["bag"]["corn"], 3)
        self.assertEqual(record["points"], 70)
        self.assertEqual(daily_goals("2026-10-10"), daily_goals("2026-10-10"))
        goals = daily_goals("2026-10-10")
        self.assertEqual(len(goals), 3)
        self.assertEqual(len({goal["id"] for goal in goals}), 3)

    def test_category_and_unique_goal_counts(self):
        daily = dict(bag={"bears": 4, "snickers": 2, "kitkat": 1})
        self.assertEqual(goal_progress(dict(id="unique"), daily), 3)
        self.assertEqual(goal_progress(dict(id="chocolate"), daily), 3)
        self.assertEqual(goal_progress(dict(id="fruity"), daily), 4)
        self.assertEqual(goal_progress(dict(id="total"), daily), 7)

    def test_legacy_bag_set_completion_preserves_points(self):
        record = copy.deepcopy(EMPTY)
        record.update(points=500, caught=4, bag={key: 1 for key in SETS["chocolate"]["candies"][:-1]})
        self.assertEqual(len(tally(record, "twix", 35, {}, sets=SETS)), 1)
        self.assertEqual(record["points"], 785)
        self.assertEqual(record["sets"], ["chocolate"])
        self.assertEqual(tally(record, "twix", 35, {}, sets=SETS), [])
        self.assertEqual(record["sizes"]["regular"], 2)

    def test_daily_and_sets_are_independent_of_finale_multiplier(self):
        record = copy.deepcopy(EMPTY)
        tally(record, "corn", catch_points(10, "jackpot", True), {}, day="2026-10-31")
        self.assertEqual(record["points"], 120)  # 100 catch, 20 daily, not 40.

    def test_final_standings_sort_and_are_independent_snapshot(self):
        records = {"2": dict(points=50, caught=3), "1": dict(points=50, caught=3), "3": dict(points=50, caught=4)}
        rows = standings(records)
        self.assertEqual([row["user"] for row in rows], ["3", "1", "2"])
        records["3"]["points"] = 999
        self.assertEqual(rows[0]["points"], 50)


class Listener(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = types.SimpleNamespace(cog_disabled_in_guild=AsyncMock(return_value=False),
            allowed_by_whitelist_blacklist=AsyncMock(return_value=True),
            get_context=AsyncMock(return_value=types.SimpleNamespace(valid=False)))
        self.cog = GuessCandy(self.bot)
        self.guild = types.SimpleNamespace(id=1, me=object(), get_member=lambda uid: None)
        self.channel = types.SimpleNamespace(id=2, guild=self.guild, send=AsyncMock(),
            permissions_for=lambda member: types.SimpleNamespace(view_channel=True, send_messages=True, embed_links=True, attach_files=True))
        self.channel.send.return_value = types.SimpleNamespace(id=100, edit=AsyncMock())
        self.guild.get_channel = lambda channel_id: self.channel if channel_id == 2 else None
        self.bot.get_guild = lambda guild_id: self.guild if guild_id == 1 else None
        self.cog.now = Mock(return_value=datetime(2026, 10, 10, 12, tzinfo=timezone.utc))
        self.settings = self.cog.config.guild(self.guild).data
        self.settings.update(enabled=True, channel=2, october_only=False, users=2, messages=2, cooldown=30, jitter=0)

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
        self.assertEqual(sum(r["points"] for r in records.values()), 30)
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
        self.cog.activity[1] = self.cog.fresh_activity(self.settings)
        self.cog.activity[1]["ready"] = time.monotonic() - 1
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
        self.assertEqual(next(iter(self.settings["seasons"].values()))["10"]["points"], 30)
        self.assertEqual(reloaded.rounds, {})
        await reloaded.red_delete_data_for_user(requester="discord_deleted_user", user_id=10)
        self.assertTrue(all("10" not in records for records in self.settings["seasons"].values()))

    async def test_upload_failure_does_not_create_round(self):
        import discord
        self.channel.send.side_effect = discord.Forbidden(types.SimpleNamespace(status=403, reason="Forbidden"), "No uploads")
        with self.assertLogs("red.guesscandy", level="WARNING"):
            self.assertFalse(await self.cog.spawn(self.channel, self.settings))
        self.assertEqual(self.cog.rounds, {})

    async def test_halloween_announces_once_and_survives_reload(self):
        now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
        await self.cog.event_tick(now)
        await self.cog.event_tick(now)
        self.assertEqual(self.channel.send.await_count, 1)
        self.assertTrue(self.settings["announcements"]["2026"]["finale"])
        reloaded = GuessCandy(self.bot)
        reloaded.config = self.cog.config
        await reloaded.event_tick(now)
        self.assertEqual(self.channel.send.await_count, 1)

    async def test_final_announcements_retry_and_freeze_snapshot(self):
        self.settings["seasons"] = {"2026": {"10": dict(points=123, caught=7)}}
        now = datetime(2026, 11, 1, 5, tzinfo=timezone.utc)
        with patch.object(self.cog, "send", AsyncMock(return_value=None)):
            await self.cog.event_tick(now)
        self.assertNotIn("final", self.settings["announcements"].get("2026", {}))
        self.assertEqual(self.settings["final_standings"]["2026"][0]["points"], 123)
        self.settings["seasons"]["2026"]["10"]["points"] = 999
        await self.cog.event_tick(now)
        await self.cog.event_tick(now)
        self.assertEqual(self.channel.send.await_count, 1)
        self.assertIn("123", self.channel.send.call_args.args[0])
        self.assertTrue(self.settings["announcements"]["2026"]["final"])
        await self.cog.red_delete_data_for_user(requester="user", user_id=10)
        self.assertEqual(self.settings["final_standings"]["2026"], [])

    async def test_finale_disabled_and_red_disabled_do_not_announce(self):
        self.settings["finale"] = False
        now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
        await self.cog.event_tick(now)
        self.settings["finale"] = True
        self.bot.cog_disabled_in_guild.return_value = True
        await self.cog.event_tick(now)
        self.channel.send.assert_not_awaited()

    async def test_midnight_cannot_award_previous_day_round(self):
        self.cog.now.return_value = datetime(2026, 10, 31, 4, 59, 59, tzinfo=timezone.utc)
        await self.make_round()
        self.assertLessEqual(self.cog.rounds[1]["timeout"], 1)
        self.cog.now.return_value = datetime(2026, 10, 31, 5, 0, 0, tzinfo=timezone.utc)
        await self.cog.on_message(self.message())
        self.assertEqual(self.settings["seasons"], {})
        self.assertNotIn(1, self.cog.rounds)

    async def test_new_year_recovers_missed_finals(self):
        self.settings["seasons"] = {"2026": {"10": dict(points=100, caught=5)}}
        await self.cog.event_tick(datetime(2027, 1, 1, 12, tzinfo=timezone.utc))
        self.assertTrue(self.settings["announcements"]["2026"]["final"])

    async def test_configured_set_prize_awards_once(self):
        record = copy.deepcopy(EMPTY)
        record.update(points=500, caught=4, bag={key: 1 for key in SETS["chocolate"]["candies"][:-1]})
        self.settings["seasons"] = {"2026": {"10": record}}
        self.settings["set_rewards"] = {"chocolate": dict(bonus=350, prize="Chocolate Champion prize")}
        await self.make_round()
        self.cog.rounds[1].update(candy=CANDIES["twix"], candy_id="twix", points=35)
        await self.cog.on_message(self.message(content="twix"))
        self.assertEqual(record["points"], 905)  # existing 500 + catch 35 + set 350 + daily 20
        self.assertIn("chocolate", record["sets"])
        text = "\n".join(call.args[0] or "" for call in self.channel.send.call_args_list)
        self.assertIn("Chocolate Champion prize", text)
        self.assertEqual(tally(record, "twix", 35, {}, sets=self.cog.collection_rewards(self.settings)), [])

    async def test_new_player_daily_goal_does_not_copy_another_player(self):
        await self.make_round()
        await self.cog.on_message(self.message(user=10))
        await self.make_round()
        await self.cog.on_message(self.message(user=11))
        records = self.settings["seasons"]["2026"]
        self.assertEqual(records["10"]["points"], 30)
        self.assertEqual(records["11"]["points"], 30)
        self.assertIsNot(records["10"]["daily"], records["11"]["daily"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
