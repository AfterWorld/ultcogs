import json
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

from staffapplications.presets import LEGACY_TEMPLATE, ONE_PIECE_TEMPLATE
from staffapplications.staffapplications import StaffApplications
from staffapplications.store import Store
from staffapplications.tests.test_workflow import cog as cog
from staffapplications.tests.test_workflow import draft, queued
from staffapplications.views import AnswerModal, panel


def test_ten_exact_questions_and_moderator_default(tmp_path):
    store = Store(tmp_path / "db")
    expected = [
        "Why do you want to become a moderator for this server?",
        "What experience do you have moderating Discord servers or other communities?",
        "How would you handle a conflict between two members in the server?",
        "What is your availability for moderation duties? (e.g., hours per day or time zones)",
        "How old are you?",
        "How would you improve the community experience as a moderator?",
        "Are you familiar with moderation tools (e.g., Discord bots like MEE6, Dyno, or Automod)? If so, which ones?",
        "Can you share an example of how you’ve resolved a challenging situation in a team or community setting?",
        "What qualities or skills do you think make a great moderator?",
        "How would you handle a situation where another staff member breaks the rules?",
    ]
    assert store.settings(1)["questions"] == expected
    assert store.settings(1)["positions"] == ["Moderator"]
    store.close()


def test_migration_preserves_customizations_and_old_drafts(tmp_path):
    path = tmp_path / "db"
    store = Store(path)
    old = {
        **deepcopy(LEGACY_TEMPLATE),
        "open": True,
        "review_channel": 3,
        "reviewer_role": 4,
        "panel_channel": 2,
        "manage_panel_visibility": True,
    }
    with store.db:
        store.db.execute("INSERT INTO settings VALUES (?,?)", (1, json.dumps(old)))
        store.db.execute(
            "INSERT INTO settings VALUES (?,?)",
            (2, json.dumps({**old, "title": "Custom", "questions": ["Custom question?"]})),
        )
    app = store.start(1, 10, "Moderator")
    store.answer(app["id"], 10, 0, "Saved answer", 0)
    store.close()
    restored = Store(path)
    assert restored.settings(1)["questions"] == ONE_PIECE_TEMPLATE["questions"]
    assert restored.settings(1)["open"] and restored.settings(1)["manage_panel_visibility"]
    assert restored.settings(2)["title"] == "Custom"
    assert restored.settings(2)["questions"] == ["Custom question?"]
    assert restored.get(app["id"])["questions"] == LEGACY_TEMPLATE["questions"]
    assert restored.get(app["id"])["answers"][0] == "Saved answer"
    restored.configure(1, title="Later custom title")
    restored.close()
    restored = Store(path)
    assert restored.settings(1)["title"] == "Later custom title"
    restored.close()


async def test_preset_preserves_channels_visibility_and_drafts(cog):
    app = draft(cog)
    before = cog.store.settings(1)
    cog.publish_panel = AsyncMock()
    ctx = NS(guild=NS(id=1), send=AsyncMock())
    await StaffApplications.preset_command.callback(cog, ctx, "onepiece")
    after = cog.store.settings(1)
    for key in ("open", "review_channel", "error_channel", "manage_panel_visibility"):
        assert before[key] == after[key]
    assert after["questions"] == ONE_PIECE_TEMPLATE["questions"]
    assert cog.store.get(app["id"])["questions"] == app["questions"]


async def test_all_ten_question_modals_show_full_text(cog):
    cog.store.configure(1, **ONE_PIECE_TEMPLATE)
    app = draft(cog)
    for index, question in enumerate(app["questions"]):
        modal = AnswerModal(cog, app, index)
        data = modal.to_dict()
        assert data["components"][0]["type"] == 10
        assert data["components"][0]["content"] == question
        assert data["components"][1]["type"] == 18
        assert len(data["components"][1]["label"]) <= 45


async def test_panel_sections_and_real_server_specific_count(cog):
    draft(cog, user=11)
    app = queued(cog, user=10)
    cog.store.configure(2, open=True, review_channel=9, reviewer_role=4)
    other = cog.store.start(2, 20, "Moderator")
    for index in range(len(other["questions"])):
        other = cog.store.answer(other["id"], 20, index, "Answer", other["revision"])
    cog.store.submit(other["id"], 20)
    payload = panel(cog, 1)["view"].to_components()
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "Requirements" in encoded and "What Happens Next?" in encoded
    assert "Applications Submitted\\n1" in encoded
    assert cog.store.submitted_count(1) == 1
    cog.store.remove(app["id"])
    assert cog.store.submitted_count(1) == 0


async def test_questions_command_accepts_full_long_questions(cog):
    ctx = NS(guild=NS(id=1), tick=AsyncMock())
    await StaffApplications.questions_command.callback(
        cog, ctx, questions=" | ".join(ONE_PIECE_TEMPLATE["questions"])
    )
    assert cog.store.settings(1)["questions"] == ONE_PIECE_TEMPLATE["questions"]


async def test_counter_refreshes_only_when_count_changes(cog):
    cog.store.configure(1, panel_channel=2, panel_message=3)
    cog._panel_counts[1] = 0
    app = queued(cog)
    app["status"] = "pending"
    cog.store.save(app)

    async def published(guild_id):
        cog._panel_counts[guild_id] = cog.store.submitted_count(guild_id)

    cog.publish_panel = AsyncMock(side_effect=published)
    await cog.cycle()
    cog.publish_panel.assert_awaited_once_with(1)
    await cog.cycle()
    assert cog.publish_panel.await_count == 1
