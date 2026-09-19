"""Durable application state. One bot process must own this SQLite database."""

import json
import sqlite3
import time
import uuid
from copy import deepcopy

from .presets import LEGACY_TEMPLATE, ONE_PIECE_TEMPLATE

DEFAULTS = {
    "open": False,
    "template_version": 2,
    "review_channel": None,
    "error_channel": None,
    "reviewer_role": None,
    "panel_channel": None,
    "panel_message": None,
    "manage_panel_visibility": False,
    "cooldown_hours": 168,
    "retention_days": 90,
    **deepcopy(ONE_PIECE_TEMPLATE),
}
ACTIVE = {"draft", "queued", "pending", "under_review"}
FINAL = {"accepted", "declined", "cancelled"}


class UserError(Exception):
    """An expected, safe-to-display validation failure."""


class PanelUnavailable(UserError):
    """Safe, fixed diagnostics for a panel that requires administrator repair."""

    REASONS = {
        "unconfigured": "No application panel channel is configured. Run staffapp setup.",
        "missing": "The configured application channel was deleted. Run staffapp setup with an existing channel.",
        "forbidden": "The bot cannot access or edit the application panel. Restore View Channel, Send Messages and Embed Links, then run staffapp panel.",
        "invalid": "The configured panel is not a text channel in this server. Run staffapp setup.",
    }

    def __init__(self, reason, channel_id=None):
        self.reason = reason
        self.channel_id = channel_id
        super().__init__(self.REASONS[reason])


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (guild INTEGER PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY, guild INTEGER NOT NULL, user INTEGER NOT NULL,
                status TEXT NOT NULL, updated REAL NOT NULL, data TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_application
                ON applications(guild, user)
                WHERE status IN ('draft','queued','pending','under_review');
        """)

        self.migrate_template()

    def migrate_template(self):
        """Upgrade untouched v1 defaults once; keep custom settings and all draft snapshots."""
        for guild, raw in self.db.execute("SELECT guild, data FROM settings").fetchall():
            data = json.loads(raw)
            if data.get("template_version", 0) >= 2:
                continue
            for key, previous in LEGACY_TEMPLATE.items():
                if data.get(key, previous) == previous:
                    data[key] = deepcopy(ONE_PIECE_TEMPLATE[key])
            data["template_version"] = 2
            with self.db:
                self.db.execute(
                    "UPDATE settings SET data=? WHERE guild=?", (json.dumps(data), guild)
                )

    def submitted_count(self, guild):
        rows = self.db.execute("SELECT data FROM applications WHERE guild=?", (guild,))
        return sum("submitted" in json.loads(row[0]) for row in rows)

    def close(self):
        self.db.close()

    def settings(self, guild):
        row = self.db.execute("SELECT data FROM settings WHERE guild=?", (guild,)).fetchone()
        return {**deepcopy(DEFAULTS), **(json.loads(row[0]) if row else {})}

    def configure(self, guild, **changes):
        value = {**self.settings(guild), **changes}
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO settings VALUES (?,?)", (guild, json.dumps(value))
            )
        return value

    def guilds(self):
        return [r[0] for r in self.db.execute("SELECT guild FROM settings")]

    def get(self, app_id):
        row = self.db.execute("SELECT data FROM applications WHERE id=?", (app_id,)).fetchone()
        if not row:
            raise UserError("This application no longer exists. Start from the server panel.")
        return json.loads(row[0])

    def save(self, app):
        app["updated"] = time.time()
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO applications VALUES (?,?,?,?,?,?)",
                (
                    app["id"],
                    app["guild"],
                    app["user"],
                    app["status"],
                    app["updated"],
                    json.dumps(app),
                ),
            )
        return app

    def all(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT data FROM applications")]

    def latest(self, guild, user):
        row = self.db.execute(
            "SELECT data FROM applications WHERE guild=? AND user=? ORDER BY updated DESC LIMIT 1",
            (guild, user),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def start(self, guild, user, position):
        cfg = self.settings(guild)
        prior = self.latest(guild, user)
        if prior and prior["status"] in ACTIVE:
            return prior
        if not cfg["open"]:
            raise UserError("Applications are currently closed.")
        if not cfg["review_channel"] or not cfg["reviewer_role"]:
            raise UserError("Applications are not configured yet. Please contact an administrator.")
        if position not in cfg["positions"]:
            raise UserError("That position is no longer available. Reopen the application panel.")
        if prior and prior["status"] in {"accepted", "declined"}:
            remaining = prior["decided_at"] + cfg["cooldown_hours"] * 3600 - time.time()
            if remaining > 0:
                raise UserError(
                    f"Please wait {int(remaining / 3600) + 1} hour(s) before reapplying."
                )
        return self.save(
            {
                "id": uuid.uuid4().hex,
                "guild": guild,
                "user": user,
                "position": position,
                "status": "draft",
                "created": time.time(),
                "questions": list(cfg["questions"]),
                "answers": [""] * len(cfg["questions"]),
                "revision": 0,
                "reviewer": None,
                "message": None,
                "delivery_channel": None,
                "attempted": False,
                "next_retry": 0,
                "attempts": 0,
                "ui_dirty": False,
                "notify": False,
                "dm_message": None,
                "dm_channel": None,
            }
        )

    def owned(self, app_id, user, draft=False):
        app = self.get(app_id)
        if app["user"] != user:
            raise UserError("This application belongs to another member.")
        if draft and app["status"] != "draft":
            raise UserError("This application is no longer editable.")
        return app

    def answer(self, app_id, user, index, answer, revision):
        app = self.owned(app_id, user, draft=True)
        if revision != app["revision"]:
            raise UserError(
                "This form is out of date. Use Continue to reopen the current question."
            )
        if not 0 <= index < len(app["questions"]):
            raise UserError("That question does not exist.")
        answer = answer.strip()
        if not 1 <= len(answer) <= 2000:
            raise UserError("Please enter between 1 and 2,000 characters.")
        app["answers"][index] = answer
        app["revision"] += 1
        return self.save(app)

    def submit(self, app_id, user):
        app = self.owned(app_id, user)
        if app["status"] != "draft":
            raise UserError("This application was already submitted or closed.")
        if not all(app["answers"]):
            raise UserError("Please answer every question before submitting.")
        cfg = self.settings(app["guild"])
        if not cfg["open"]:
            raise UserError("Applications are currently closed. Your draft is saved.")
        if not cfg["review_channel"]:
            raise UserError("No review channel is configured. Your draft is saved.")
        app.update(status="queued", delivery_channel=cfg["review_channel"], submitted=time.time())
        return self.save(app)

    def cancel(self, app_id, user):
        app = self.owned(app_id, user, draft=True)
        app["status"] = "cancelled"
        return self.save(app)

    def decide(self, app_id, reviewer, action, reason=""):
        app = self.get(app_id)
        if app["status"] not in {"pending", "under_review"}:
            raise UserError("This application is not awaiting review.")
        if reviewer == app["user"]:
            raise UserError("You cannot review your own application.")
        if app["reviewer"] not in (None, reviewer):
            raise UserError("Another reviewer has claimed this application.")
        if action not in {"claim", "under_review", "accepted", "declined"}:
            raise UserError("Unknown review action.")
        if action in {"accepted", "declined"} and not reason.strip():
            raise UserError("Please provide a decision message for the applicant.")
        app["reviewer"] = reviewer
        if action != "claim":
            app["status"] = action
        if action in {"accepted", "declined"}:
            app.update(reason=reason.strip()[:1000], decided_at=time.time(), notify=True)
        app["ui_dirty"] = True
        return self.save(app)

    def remove(self, app_id):
        with self.db:
            self.db.execute("DELETE FROM applications WHERE id=?", (app_id,))

    def expired(self):
        now = time.time()
        return [
            a
            for a in self.all()
            if a["status"] in FINAL | {"draft"}
            and not a["notify"]
            and now - a["updated"] > self.settings(a["guild"])["retention_days"] * 86400
        ]
