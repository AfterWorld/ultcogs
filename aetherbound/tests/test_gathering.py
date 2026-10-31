import pytest

from aetherbound import engine
from aetherbound import gathering


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def player(level=1):
    p = engine.new_player("Gatherer", "strider")
    p["tutorial"] = 6
    p["level"] = level
    return p


def test_active_gathering_awards_materials_and_skill_xp():
    p = player()
    result = gathering.resolve(p, "mining", "glimmerwood", FixedRng(0.15), now=100)

    assert result["attempts"] == 3
    assert result["successes"] == 3
    assert result["reward"] == {"iron": 2}
    assert p["materials"]["iron"] == 2
    assert p["gathering"]["mining"]["xp"] == result["xp"]


def test_failed_attempts_still_grant_skill_practice():
    p = player()
    result = gathering.resolve(p, "foraging", "glimmerwood", FixedRng(0.99), now=100)

    assert result["successes"] == 0
    assert result["reward"] == {"essence": 0}
    assert result["xp"] > 0


def test_embervein_requires_hero_level_eight():
    with pytest.raises(engine.RuleError, match="level 8"):
        gathering.resolve(player(7), "mining", "embervein", FixedRng(0.15), now=100)


def test_gathering_is_blocked_during_battle():
    p = player()
    p["battle"] = {"id": "active"}
    with pytest.raises(engine.RuleError, match="Battle in progress"):
        gathering.resolve(p, "thieving", "glimmerwood", FixedRng(0.15), now=100)


def test_repeat_gathering_obeys_short_cooldown():
    p = player()
    gathering.resolve(p, "thieving", "glimmerwood", FixedRng(0.15), now=100)
    with pytest.raises(engine.RuleError, match="gather again"):
        gathering.resolve(p, "thieving", "glimmerwood", FixedRng(0.15), now=102)

def test_session_rewards_are_capped_by_region():
    p = player(level=8)
    result = gathering.resolve(p, "mining", "embervein", FixedRng(0.15), now=100)

    assert result["reward"]["iron"] == 3


def test_daily_session_limit_and_utc_reset():
    p = player()
    for session in range(gathering.DAILY_SESSIONS):
        result = gathering.resolve(
            p, "mining", "glimmerwood", FixedRng(0.15), now=100 + session * 16
        )
    assert result["sessions_left"] == 0
    with pytest.raises(engine.RuleError, match="all 8 gathering sessions"):
        gathering.resolve(p, "mining", "glimmerwood", FixedRng(0.15), now=300)

    next_day = gathering.resolve(
        p, "mining", "glimmerwood", FixedRng(0.15), now=86400 + 100
    )
    assert next_day["sessions_left"] == gathering.DAILY_SESSIONS - 1
