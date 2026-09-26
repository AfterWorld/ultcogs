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

To have the bot create channels (requires Manage Channels and Manage Roles):

```text
[p]staffapp createchannels @ApplicationReviewers
```

All three generated channels start private, accessible to the bot, the configured
reviewer role, and server administrators. `staffapp open true` makes only the
application panel channel visible to everyone. `staffapp open false` hides that
channel again. Review and error channels remain private throughout. Keep the bot's
Manage Roles permission so it can change the panel's visibility. Existing drafts
remain saved while closed and can still be continued through their DM controls.

Or use three existing channels:

```text
[p]staffapp setup #staff-applications #application-reviews #application-errors @ApplicationReviewers
```

For manually supplied channels, `setup` preserves their visibility; configure their
permissions yourself. Automatic visibility applies to channels created by this version
of `createchannels`, and is retained if you rerun setup with the same panel channel.
Channels created by version 1.0 retain their existing manual visibility behavior.

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

## One Piece moderator preset

Version 1.2 preloads the One Piece recruitment message and these ten questions:

1. Why do you want to become a moderator for this server?
2. What experience do you have moderating Discord servers or other communities?
3. How would you handle a conflict between two members in the server?
4. What is your availability for moderation duties? (e.g., hours per day or time zones)
5. How old are you?
6. How would you improve the community experience as a moderator?
7. Are you familiar with moderation tools (e.g., Discord bots like MEE6, Dyno, or Automod)? If so, which ones?
8. Can you share an example of how you’ve resolved a challenging situation in a team or community setting?
9. What qualities or skills do you think make a great moderator?
10. How would you handle a situation where another staff member breaks the rules?

The panel includes Requirements, What Happens Next?, an Applications Submitted
count, and a green Apply Now button. The count reflects submissions still stored
for this server, including queued submissions; deleting or expiring records reduces
it. It refreshes on the worker's next successful cycle (normally about ten seconds).
No example submission count is fabricated or imported from the reference image.

For an existing installation:

```text
[p]cog update staffapplications
[p]reload staffapplications
[p]staffapp preset onepiece
```

The preset applies the panel text, requirements, gold accent, Moderator position,
and all ten questions, then refreshes the existing panel. Channels, open/closed
state, privacy settings, error destinations, and existing draft/submitted question
snapshots are preserved. New applications use the new questions; an applicant
with an older draft can cancel that draft and start again to use the new set.

On upgrade, untouched original default text/questions migrate automatically once;
custom settings remain intact. Use the preset command above to explicitly replace
custom copy/questions as well. Full questions are displayed in the modal body,
including questions longer than 100 characters.

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

## Preview a test application

```text
[p]staffapp testapplication
```

An administrator can run this even while applications are closed. It sends the
command invoker a clearly labeled DM preview of the first question and posts a
completed fictional application in the configured private review channel. The
sample uses your configured questions and first configured position. The ten
built-in moderator questions have matching sample answers; custom questions get
an explicitly generic fictional response.

Use **Review Answers** in the DM or **View Answers** on the staff preview to read
sample answers inside Discord. Review-channel readers still need reviewer access.
The other buttons are disabled: this is a visual preview, not a real submission
or an end-to-end acceptance test. Sample controls expire after 15 minutes;
an opened answer reader lasts five minutes. The review attachment remains available.

No application record is saved, no applicant cooldown changes, and the submission
count stays unchanged. A 60-second command cooldown limits repeated previews.
Your DMs must be enabled, and the review channel must be configured and private.
Delete the demo DM and review message manually when done; they are not managed by
application retention because no application record is created.

## Staff experience

A private review card contains applicant ID, position, submission time, status,
reviewer, and an attachment with all answers. **View Answers** reads them inside
Discord. **Claim**, **Under Review**, **Accept**, and **Decline** require the configured
reviewer role, Manage Server, or Red bot ownership, plus access to the review channel.
Staff cannot review their own application. Once claimed, another reviewer cannot
overwrite it. Acceptance/decline asks for a message that is sent to the applicant;
that field is **not an internal note**. Roles are not automatically granted.

| Button | What it does |
| --- | --- |
| View Answers | Opens a private, paginated reader of the applicant's answers. |
| Claim | Assigns you as the reviewer without changing the status. Other reviewers cannot take over or decide it. |
| Under Review | Assigns you if unclaimed and marks the application as being considered. It does not send a decision DM. |
| Accept | Opens a required message form. Submitting saves the final acceptance and queues a DM to the applicant. |
| Decline | Opens the same required message form, saves the final decline, and queues a DM to the applicant. |

Choose one reviewer to handle the final decision. Use a thread under the original
review card for each case so Warlords and other staff can discuss it together before
that reviewer decides. Threads use Discord's normal permissions; give participating
staff access to the review channel and its threads. Channel visibility alone does
not grant button access: reviewers also need the role or permissions listed above.
Final decisions disable the action buttons; View Answers remains available.

### Accepted application copies (1.5)

New acceptances in server `374126802836258816` also copy the accepted card and full
answer attachment to channel `1417172494598668369`. The original review card stays
in place. The copy has no decision controls and can be used for follow-up discussion.
Declined applications, fictional previews, previously accepted records, and other
servers are not forwarded.

The destination must be a private text channel in that server, with View Channel
denied to `@everyone`. Grant the intended staff roles access. The bot needs View
Channel, Send Messages, Embed Links, Attach Files, and Read Message History there.
Copies use the existing background worker, normally within about ten seconds.
Failures are reported and retried with backoff; `staffapp retry APPLICATION_ID`
can retry sooner after permissions are fixed. History recovery avoids blindly
duplicating a copy after an uncertain send or restart. Copy failures do not undo
acceptance or stop the applicant DM. No old acceptances are backfilled.

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
| `staffapp open true/false` | Open/close applications; show/hide the bot-created panel channel |
| `staffapp errorchannel #channel` | Set a separate private error destination |
| `staffapp testerror` | Attempt owner DM and channel test alerts; 60-second cooldown |
| `staffapp positions A \| B` | 1–25 positions; each at most 100 characters |
| `staffapp questions Q1 \| Q2` | 1–20 questions; each at most 500 characters |
| `staffapp requirements TEXT` | At most 1,800 characters |
| `staffapp appearance COLOR Title \| Description` | Panel color, title and description |
| `staffapp limits HOURS DAYS` | Reapply cooldown 0–8,760 hours; retention 1–365 days |
| `staffapp retry APPLICATION_ID` | Clear delivery/update retry delay or retry blocked decision DM |
| `staffapp reroute APPLICATION_ID #channel` | Move a queued application only if its original channel was deleted |
| `staffapp delete APPLICATION_ID true` | Delete application data and its tracked review/DM messages |

Changing setup closes applications until explicitly reopened. Existing queued
submissions keep their original destination so retries cannot accidentally post to
both the old and new channel. Restore original permissions and retry when possible.

## Recreate deleted channels automatically (1.3)

```text
[p]staffapp repairchannels
```

This checks all three saved channel IDs directly with Discord and recreates only
channels confirmed deleted (or never configured). Existing channels are preserved.
The saved reviewer role is reused; if that role no longer exists, supply a current role:

```text
[p]staffapp repairchannels @YourStaffRole
```

The bot needs Manage Channels and Manage Roles. Replacement channels start private,
applications close during repair, and a surviving bot-managed panel is hidden.
Use `[p]staffapp open true` when ready. A new panel channel receives the existing
recruitment template and buttons automatically. No manual channel creation is needed.

Permission failures and Discord outages do **not** trigger replacement channels.
Each successful creation is saved immediately, so rerunning after a partial failure
keeps the channels already created. No channels or application records are deleted.
Only configured channel IDs are reused: an unrelated channel with the same name is
not silently adopted.

This repairs configuration and the public panel, not the contents of a deleted
review/error channel. Previously queued applications retain their original delivery
channel for duplicate protection. For those, use
`[p]staffapp reroute APPLICATION_ID #application-reviews` after repair. Existing
review messages that Discord deleted cannot be restored by this command; their
application records remain saved.

## Panel-refresh recovery (1.2.1)

A panel channel missing from the bot's local cache is now fetched directly from
Discord before being considered unavailable. This also applies when opening or
closing a managed panel channel after a reload.

If Discord confirms that a configured channel was deleted or is inaccessible,
automatic refresh pauses for that channel/message configuration and sends one
sanitized alert with a fixed explanation and recovery command. Application data
and channel IDs are retained. Fix permissions and run `[p]staffapp panel` to retry;
if the channel was deleted, run `[p]staffapp repairchannels` to recreate it privately.
Successful manual repair resumes refresh. Changing the panel configuration also
allows another attempt. The pause resets on cog reload, which allows one fresh check.
Transient Discord/network errors instead retry after at least 60 seconds.

A deleted panel message is recreated only when Discord reports Unknown Message;
an Unknown Channel response no longer triggers an attempted post to a deleted channel.

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
reviews, undelivered submissions, and pending accepted copies are retained. Outstanding decision notifications
are not automatically discarded. Deletion removes the tracked staff message and its
answer attachment, including the accepted copy, before deleting the database record. If Discord deletion fails,
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
- Verify all generated channels start hidden; opening exposes only the panel and closing hides it again.
- Verify channel overwrites and retention/deletion on test records.

Visibility toggling changes the panel’s `@everyone` overwrite and preserves its other
permissions. Additional role/member View Channel overrides added manually can grant
access while closed; keep these limited to staff.

Automated tests are not a substitute for live Discord permission and interaction checks.
No live Discord account or bot token is required for the automated suite.

