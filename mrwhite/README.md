# Mr. White — Secret Seas

A full Civilian / Undercover / Mr. White party game for **3–25 players**, built on the original MrWhite cog and command group. Original procedural cartoon pirate/secret-agent art uses black, ivory and red. No external images, avatars, One Piece assets or characters are used.

## Quick start

Validated target: **Python 3.11.15, Red-DiscordBot 3.5.24, discord.py 2.7.1**. Pillow is the cog's only additional runtime requirement; Red Downloader installs it from `info.json`. For a manual installation, install Pillow in the bot's own environment before loading `mrwhite`.

1. Install this repository's feature branch using Red Downloader (or copy the complete `mrwhite` folder into your configured cog path), then `[p]load mrwhite`.
2. `[p]mrwhite start` opens a lobby and joins its creator as captain.
3. Friends click **Join crew**. The captain clicks **Set sail** with at least three players.
4. Every player opens **My secret dossier**, an ephemeral reply only they can see. Closed DMs are supported. `[p]mrwhite role` is an optional DM fallback.
5. Give one clue each through the modal or `[p]mrwhite say <clue>`. Clues appear on the card. Then select a suspect on the ballot.
6. Follow eliminations, revotes and Mr. White's final-guess prompt until a faction wins.

Bot permissions: View Channel, Send Messages (Send Messages in Threads for threads), Embed Links. Attach Files enables generated cards; without it, text embeds still work. Prefix commands require the normal Red message-content setup. No reaction permissions or Manage Messages are required.

## Rules

Civilians receive the same word; Undercover receives a related word; Mr. White receives no word. Word-pair orientation is randomized once per game; your word stays unchanged across rounds. Players are told their own faction, never other players' factions until elimination/end. Each living player can give one 1–80 character clue per round, in any order. Submitting either exact secret word is rejected. Do not deliberately reveal your word in chat.

| Players | Undercover | Mr. White | Civilians |
| --- | --- | --- | --- |
| 3 | 0 | 1 | 2 |
| 4–11 | floor(players / 4), minimum 1 | 1 | remainder |
| 12–25 | floor(players / 4) | 2 | remainder |

- **Civilian victory:** all Undercover and Mr. White players have been eliminated.
- **Undercover victory:** surviving Undercover count is at least the combined count of all other survivors.
- **Mr. White victory:** correctly guess the Civilian word after elimination, or survive to the final two. Final-two survival takes priority over Undercover parity. Multiple Whites share the faction win; each eliminated White gets their own single final guess.
- An eliminated White gets their guess **before** checking any other victory. A wrong/expired guess continues the game if other infiltrators remain.
- The unique highest ballot total eliminates a player. Votes may change until all living players vote or the deadline expires. No self-votes. Eliminated players and spectators cannot vote or give clues.
- A tie triggers one revote among tied candidates, with all living players eligible to vote. A second tie eliminates nobody and starts another clue round. There is no arbitrary random elimination.
- Missing clues are skipped. Missing votes abstain; zero votes ends the game in a draw. The game ends in a draw after 20 rounds.

## Commands and controls

The earlier open upgrade PR #13 was also inspected; its short aliases are retained: `mw`, `new`, `j`, `b`, `s`, `v`, `g`, `stop`. This feature branch is based on current main and includes the overlapping improvements.

All original commands remain: `start`, `join`, `begin`, `say`, `vote`, `guess`, `end`, `addword`, `removeword`, `words` under `[p]mrwhite`.

| Command | Use |
| --- | --- |
| `start` / `join` / `leave` | Create, join, or leave a lobby |
| `begin` / `end` | Captain or Manage Server moderator (or bot owner) starts/ends |
| `transfer @member` | Captain/moderator transfers control to a surviving participant |
| `kick @member` | Captain/moderator removes a lobby participant; transfer before removing captain |
| `role` | DM your own dossier; use the private button if DMs are closed |
| `say <clue>` / `vote @member` / `guess <word>` | Legacy gameplay inputs; typed commands are public |
| `status` / `rules` | Current card link or complete game rules |
| `words [page]` | Playable pairs and preserved legacy single words, 15 entries per page |
| `addpair word \| related word` / `removepair word \| related word` | Manage Server/admin: edit playable pairs |
| `addword <word>` / `removeword <word>` | Manage Server/admin: preserve/edit original single-word pool |
| `addword word \| related word` | Also accepts the new pair format |
| `timeout <phase> <seconds>` | Manage Server/admin: set 30–900 seconds for future lobbies |

The captain cannot leave without transferring or ending the lobby. Mid-game departure/kicking is intentionally unavailable: missing players are handled by deadlines and a moderator can end a stalled voyage. A captain who leaves the server can be replaced by a Manage Server moderator through `transfer`.

Default deadlines: lobby (`joining`) 300s, clues (`playing`) 120s, ballot/revote (`voting`) 90s, final guess (`guessing`) 45s. Deadlines are absolute and clicks never extend them. Config changes apply to **new lobbies**, not games already underway.

## Upgrade and data compatibility

The original Red Config identifier **1234567890** and guild `words` key are unchanged. Existing single words are preserved without guessing unrelated partners. Games use the new `pairs` key, seeded with 60 curated pairs; use `addpair` to pair a legacy custom word. Removing a legacy word does not remove any playable pair. The word/pair lists are bounded at 500 entries for new additions. No migration overwrites existing data.

Guild word lists, pairs and deadlines persist in Red Config. Player IDs, display names, secrets, clues and ballots exist only in active session memory. There are no persistent user statistics. Discord messages remain in channel history. Red's deletion hook closes any session containing the requested user and clears its live player records/current card; it does not purge historical Discord messages or remove words manually added to guild configuration.

Restart/reload ends games. Views are not persistent across restarts; use `start` again. Unload stops views and cancels timers. Channel/thread/guild removal releases sessions. A failed Discord update closes the affected game and frees its channel. Graphics failure falls back to text.

## Implementation and validation

`engine.py` owns pure game rules. `session.py` serializes buttons, commands and deadlines through one lock per channel game. Lobby creation has a separate lock. Phase generations reject old ballots/modals, and registry identity checks prevent an old game from controlling a replacement. `views.py` uses buttons, a select with at most 25 options, and short-lived entry modals. Private roles are never placed in public cards or graphic metadata. All game sends suppress mentions and escape player text. Components honor Red allow/block lists and disabled-cog settings.

`graphics.py` draws five public phase banners entirely in Pillow. Rendering runs off the event loop, with a bounded cache. Font lookup has a bundled Pillow fallback.

From the repository root, in an isolated Python 3.11.15 environment:

```sh
python -m pip install -r mrwhite/requirements-dev.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -c mrwhite/pytest.ini --confcutdir=mrwhite/tests mrwhite/tests -q
```

PowerShell: set `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'` before the same `python -m pytest ...` command. Isolation avoids importing unrelated cogs from this repository's root `__init__.py` or Red's own pytest plugin. GitHub Actions runs this suite on changes to the cog.

Tests cover role scaling, all victory paths, multiple Whites, final-guess priority, restricted revotes, empty/partial ballots, absolute and stale deadlines, simultaneous starts/votes, stale controls, host restrictions, failed Discord updates, closed DMs, Config preservation and atomic pair edits, UI limits, unload cleanup, 50 simulated games, and all five PNG renderers.

### Live Discord acceptance check

Automated tests use real installed Discord/Red libraries with mocked Discord transport. Before deploying broadly, run a real 3-player and 4+ player game: verify private dossiers with closed DMs; button/modal/select behavior; tied voting; final guesses; host transfer; timeout advancement; a second game in the same channel; reload cleanup; and the no-Attach-Files fallback. A live bot token or server session is not required for the automated suite.
