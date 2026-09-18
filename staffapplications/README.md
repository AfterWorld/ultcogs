# Staff Applications

A Red-DiscordBot cog for private, resumable staff applications. A public recruitment
panel starts a DM application; complete submissions go to a private review channel.
Unexpected errors and Discord delivery failures generate sanitized bot-owner DMs
and private error-channel alerts.

This is a new `staffapplications` cog. No existing application cog was present in
`AfterWorld/ultcogs` main at baseline `21233c638843cfd18429fb7d157345008f910509`.
No unrelated cog or existing cog data is replaced. If a different application cog
is installed on your bot, unload it and retire its old panel separately; its data
is not automatically migrated.

## Install and setup

Requires Red **3.5.24+**, Python **3.11**, and the discord.py version bundled with
that supported Red release. Tested with discord.py **2.7.1**. Do not independently
upgrade discord.py over a running Red environment. There are no extra runtime
packages to install.

Replace `[p]` with your bot prefix and `ultcogs` with your configured repository name.

```text
[p]cog install ultcogs staffapplications
[p]load staffapplications
```

To have the bot create channels (requires Manage Channels):

```text
[p]staffapp createchannels @ApplicationReviewers
```

Or use three existing channels:

```text
[p]staffapp setup #staff-applications #application-reviews #application-errors @ApplicationReviewers
```

Setup starts with applications closed. The review and error channels must deny
View Channel to `@everyone`. Audit other role/member overwrites too: setup checks
`@everyone`, not every possible member's effective permissions. Server administrators
can always access private channels. The review role needs access to the review channel.

The bot needs View Channel, Send Messages, and Embed Links in configured channels;
the review channel also requires Attach Files and Read Message History for complete
submissions and recovery. Ordinary applicants do not need to send messages in the
public panel channel. This workflow does not read ordinary DM messages: written
answers are submitted through forms.

```text
[p]staffapp positions Moderator | Helper | Event Host
[p]staffapp questions What is your timezone? | When can you help? | Why do you want to join? | How would you handle an argument?
[p]staffapp requirements Be respectful, know the server rules, and answer honestly.
[p]staffapp appearance #5865F2 Join Our Staff Team | Help support our community. Apply privately through DMs.
[p]staffapp testerror
[p]staffapp open true
```

`testerror` actually sends clearly labeled test alerts. Check **both** the configured
Red bot owner's DMs and error channel. Bot owners come from Red's `owner_ids`/`owner_id`,
with the Discord application's owner as fallback; this is not the server owner role.
Configure Red ownership correctly. A blocked owner DM does not prevent the channel
alert and vice versa. Failure of both routes is still recorded in the bot log.

## Applicant experience

1. **Apply Now** → choose a position → receive the application in DMs.
2. **Continue** opens a question form. Each submitted answer is immediately saved.
3. **Edit an Answer** changes a saved answer. **Review Answers** provides an in-Discord
   page reader. **Cancel** asks for confirmation.
4. **Submit** freezes the answers and queues a durable staff delivery.
5. **My Application** resumes a draft or shows saved/queued, delivered, under-review,
   accepted, declined, or cancelled status. Closed applications retain existing drafts.

One active application is allowed per member per server. Questions and positions
are snapshotted when a draft starts, so administrative edits cannot scramble it.
The default reapplication cooldown is seven days after a final decision. DMs blocked?
The panel gives instructions; enable DMs, then click **My Application** to retry.
Forms already open during a bot restart must be reopened using the persistent DM
buttons or public panel; previously submitted answers survive.

## Staff experience

A private review card contains applicant ID, position, submission time, status,
reviewer, and an attachment with all answers. **View Answers** reads them inside
Discord. **Claim**, **Under Review**, **Accept**, and **Decline** require the configured
reviewer role, Manage Server, or Red bot ownership, plus access to the review channel.
Staff cannot review their own application. Once claimed, another reviewer cannot
overwrite it. Acceptance/decline asks for a message that is sent to the applicant;
that field is **not an internal note**. Roles are not automatically granted.

Decisions save before notification. A failed card update cannot prevent the decision
DM from being attempted. If applicant DMs are blocked, the decision remains visible
through **My Application** and the owner is alerted. After the user enables DMs,
use `staffapp retry APPLICATION_ID` to retry a failed notification.

## Administration

All `staffapp` commands require Red admin access or Manage Server and run in a server.

| Command | Purpose |
| --- | --- |
| `staffapp settings` | Show channels, reviewer role, limits and state counts |
| `staffapp panel` | Recreate a missing public panel or refresh its appearance |
| `staffapp open true/false` | Open or close new applications and submissions |
| `staffapp errorchannel #channel` | Set a separate private error destination |
| `staffapp testerror` | Attempt owner DM and channel test alerts; 60-second cooldown |
| `staffapp positions A \| B` | 1–25 positions; each at most 100 characters |
| `staffapp questions Q1 \| Q2` | 1–20 questions; each at most 100 characters |
| `staffapp requirements TEXT` | At most 1,800 characters |
| `staffapp appearance COLOR Title \| Description` | Panel color, title and description |
| `staffapp limits HOURS DAYS` | Reapply cooldown 0–8,760 hours; retention 1–365 days |
| `staffapp retry APPLICATION_ID` | Clear delivery/update retry delay or retry blocked decision DM |
| `staffapp reroute APPLICATION_ID #channel` | Move a queued application only if its original channel was deleted |
| `staffapp delete APPLICATION_ID true` | Delete application data and its tracked review/DM messages |

Changing setup closes applications until explicitly reopened. Existing queued
submissions keep their original destination so retries cannot accidentally post to
both the old and new channel. Restore original permissions and retry when possible.

## Errors and recovery

Alerts cover this cog's commands, components/forms and background delivery/cleanup;
they do not install a global error handler for other cogs. Each alert includes an
incident ID, operation, server/application IDs, exception class, filename/function/
line stack locations, and Discord HTTP status/code when available. Exception text,
source lines, locals, tokens, and application answers are deliberately excluded.

Identical incidents are suppressed for five minutes per server/operation/stack, with
a bounded cache. Every occurrence still writes a sanitized local log entry. Both
alert routes are attempted independently, with timeouts and no recursive error
alerts. Discord outages, disabled DMs, process crashes, or failed storage can prevent
real-time notification; this is best-effort reporting, not external uptime monitoring.

SQLite stores application state under Red's cog data directory. The delivery worker
checks every ten seconds and retries transient failures with bounded exponential
backoff. After an ambiguous review-message send, it scans the original channel's
history for the unique application marker before resending. If history cannot be
read, it retains the application instead of blindly resending. This reduces duplicates;
Discord and local SQLite cannot form an atomic distributed transaction. Decision
DMs are at-least-once: a crash after a successful send but before the local save can
cause a duplicate notification. Run only one bot process against this database.

## Privacy and retention

Default retention is 90 days for inactive drafts and closed applications; active
reviews and undelivered submissions are retained. Outstanding decision notifications
are not automatically discarded. Deletion removes the tracked staff message and its
answer attachment before deleting the database record. If Discord deletion fails,
the record stays in a non-editable `deleting` state and cleanup retries, retaining the
message references. Red's `red_delete_data_for_user` hook removes an applicant's
records and anonymizes their reviewer ID in other applications.

The bot cannot erase downloaded attachments, messages copied by people, old untracked
DM panels, already-sent decision DMs, or ephemeral answer previews. Avoid requesting
unnecessary personal information. Restrict filesystem access to the database and
backups; SQLite is not encrypted by this cog. Back up Red data before bot upgrades.

## Tests and release checks

Use an isolated Python 3.11 environment:

```sh
python -m pip install -r staffapplications/requirements-dev.txt
python -m ruff check --config staffapplications/ruff.toml staffapplications
python -m ruff format --check --config staffapplications/ruff.toml staffapplications
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -c staffapplications/pytest.ini --confcutdir=staffapplications/tests staffapplications/tests -q
```

Tests use real Red/discord.py classes and a real temporary SQLite database, with
Discord network calls mocked. Coverage includes restart recovery, stale forms,
authorization, guild separation, double submissions, competing decisions, blocked
DMs, independent alert routes, suppression, redaction, ambiguous delivery recovery,
retry backoff, persistent components, and deletion/delivery races. GitHub Actions
runs the same checks for changes to this cog.

Before production use in your server:

- Load the cog, configure channels, run `testerror`, and verify both alert destinations.
- Apply with a non-staff test account, edit answers, restart the bot, and resume.
- Submit and verify the full answer attachment and View Answers pagination on mobile.
- Try reviewer buttons from an unauthorized account; then claim and decide as a reviewer.
- Block applicant DMs, confirm the owner alert and panel status, then retry after unblocking.
- Remove review-channel permissions, submit, restore permissions, and confirm one recovered submission.
- Verify channel overwrites and retention/deletion on test records.

Automated tests are not a substitute for live Discord permission and interaction checks.
No live Discord account or bot token is required for the automated suite.
