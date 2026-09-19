import time

import pytest

from staffapplications.store import Store, UserError


@pytest.fixture
def store(tmp_path):
    value = Store(tmp_path / "applications.sqlite3")
    value.configure(1, open=True, review_channel=3, reviewer_role=4, questions=["Why?", "When?"])
    yield value
    value.close()


def filled(store, guild=1, user=10):
    app = store.start(guild, user, "Moderator")
    for n in range(len(app["questions"])):
        app = store.answer(app["id"], user, n, f"Answer {n}", app["revision"])
    return app


def pending(store):
    app = filled(store)
    app = store.submit(app["id"], app["user"])
    app.update(status="pending", message=100)
    return store.save(app)


def test_draft_and_settings_survive_restart(tmp_path):
    path = tmp_path / "db"
    s = Store(path)
    s.configure(1, open=True, review_channel=3, reviewer_role=4)
    app = s.start(1, 10, "Moderator")
    s.answer(app["id"], 10, 0, "Saved", 0)
    s.close()
    restored = Store(path)
    assert restored.get(app["id"])["answers"][0] == "Saved"
    assert restored.settings(1)["open"]
    restored.close()


def test_closed_configuration_and_invalid_position(store):
    store.configure(1, open=False)
    with pytest.raises(UserError, match="closed"):
        store.start(1, 10, "Moderator")
    store.configure(1, open=True)
    with pytest.raises(UserError, match="position"):
        store.start(1, 10, "Unknown")
    store.configure(1, reviewer_role=None)
    with pytest.raises(UserError, match="configured"):
        store.start(1, 10, "Moderator")


def test_double_start_returns_one_application(store):
    a = store.start(1, 10, "Moderator")
    b = store.start(1, 10, "Helper")
    assert a["id"] == b["id"]
    assert len(store.all()) == 1


def test_snapshots_and_servers_are_isolated(store):
    a = store.start(1, 10, "Moderator")
    store.configure(1, questions=["New question"])
    assert store.get(a["id"])["questions"] == ["Why?", "When?"]
    store.configure(2, open=True, review_channel=13, reviewer_role=14, positions=["Helper"])
    b = store.start(2, 10, "Helper")
    assert a["id"] != b["id"]
    assert store.latest(1, 10)["id"] == a["id"]


@pytest.mark.parametrize("answer", ["", "   ", "x" * 2001])
def test_answer_validation(store, answer):
    a = store.start(1, 10, "Moderator")
    with pytest.raises(UserError):
        store.answer(a["id"], 10, 0, answer, 0)


def test_stale_form_and_wrong_owner(store):
    a = store.start(1, 10, "Moderator")
    store.answer(a["id"], 10, 0, "First", 0)
    with pytest.raises(UserError, match="out of date"):
        store.answer(a["id"], 10, 0, "Overwritten", 0)
    with pytest.raises(UserError, match="another member"):
        store.answer(a["id"], 99, 0, "Intruder", 1)
    assert store.get(a["id"])["answers"][0] == "First"


def test_submit_requires_all_answers_and_freezes_destination(store):
    a = store.start(1, 10, "Moderator")
    with pytest.raises(UserError, match="every question"):
        store.submit(a["id"], 10)
    a = filled(store)
    store.submit(a["id"], 10)
    store.configure(1, review_channel=999)
    assert store.get(a["id"])["delivery_channel"] == 3
    with pytest.raises(UserError, match="already"):
        store.submit(a["id"], 10)
    with pytest.raises(UserError, match="editable"):
        store.answer(a["id"], 10, 0, "Late edit", a["revision"])


def test_cancel_and_closed_draft_preserved(store):
    a = filled(store)
    store.configure(1, open=False)
    with pytest.raises(UserError, match="closed"):
        store.submit(a["id"], 10)
    assert store.get(a["id"])["answers"]
    assert store.cancel(a["id"], 10)["status"] == "cancelled"


def test_claim_self_review_and_decision_conflicts(store):
    a = pending(store)
    with pytest.raises(UserError, match="own application"):
        store.decide(a["id"], 10, "claim")
    store.decide(a["id"], 20, "claim")
    with pytest.raises(UserError, match="Another reviewer"):
        store.decide(a["id"], 30, "accepted", "Welcome")
    with pytest.raises(UserError, match="message"):
        store.decide(a["id"], 20, "declined")
    a = store.decide(a["id"], 20, "accepted", "Welcome")
    assert a["notify"] and a["ui_dirty"]
    with pytest.raises(UserError, match="not awaiting"):
        store.decide(a["id"], 20, "declined", "Second decision")


def test_reapplication_cooldown(store):
    a = pending(store)
    store.decide(a["id"], 20, "declined", "Try later")
    with pytest.raises(UserError, match="wait"):
        store.start(1, 10, "Moderator")
    store.configure(1, cooldown_hours=0)
    assert store.start(1, 10, "Moderator")["id"] != a["id"]


def test_retention_excludes_active_reviews_and_pending_notifications(store):
    a = pending(store)
    store.db.execute("UPDATE applications SET updated=0")
    # JSON is authoritative; explicitly age each saved record for this test.
    a["updated"] = 0
    import json

    store.db.execute("UPDATE applications SET data=? WHERE id=?", (json.dumps(a), a["id"]))
    store.db.commit()
    assert store.expired() == []
    a = store.decide(a["id"], 20, "accepted", "Welcome")
    a.update(updated=time.time() - 100 * 86400, notify=False)
    store.db.execute("UPDATE applications SET data=? WHERE id=?", (json.dumps(a), a["id"]))
    store.db.commit()
    assert [v["id"] for v in store.expired()] == [a["id"]]
