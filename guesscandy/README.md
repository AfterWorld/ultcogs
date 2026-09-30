# Guess the Candy 🎃

A Red Discord Bot cog for a chat-driven October candy hunt. People talk in #general, a real candy photograph appears, and the first person to type its name collects it and earns points. No bank integration or extra runtime dependencies.

## Install and launch

Target: Red **3.5.24**, the latest stable release checked September 30, 2026. Red manages its own discord.py dependency (2.6.3 in this release); do not independently upgrade discord.py inside your Red environment. Python 3.11 or later, within Red's supported Python versions.

Copy this entire `guesscandy` folder, including `photos`, into your existing cog repository. For a local installation, put the folder in a directory registered with Red's `[p]addpath` command, then load it. `[p]` means your bot's command prefix.

```text
[p]load guesscandy
[p]candyset channel #general
[p]candyset enabled true
[p]candyset reward corn 10 100 Candy Corn Champion
[p]candyset reward any 25 250 Halloween Collector
[p]candyset reward chunky 3 500 Big Candy Prize — contact staff
```

Enable the **Message Content Intent** for your bot in Discord's Developer Portal and Red. The bot needs View Channel, Send Messages, Embed Links, and Attach Files in the hunt channel. Server admins or members with Manage Server can configure it.

## Default behavior

- October-only, using UTC−05:00 (Chicago's October offset). Opens October 1 at midnight and closes November 1 at midnight each year. Set `[p]candyset offset <minutes>` for another fixed UTC offset. There is no automatic daylight-saving adjustment.
- A spawn requires 12 eligible messages from at least 3 distinct people and a 10-minute cooldown. The first cooldown starts when the first eligible message arrives; a later message triggers the spawn once both gates are met. No activity means no spawn.
- One eligible contribution per person every 20 seconds. Bot/webhook messages, valid commands, Red-disabled cogs, and users denied by Red's allow/block lists do not contribute. Edit events do not count.
- One active candy per server, in the chosen channel. Guess window: 120 seconds. Exact aliases ignoring case, spaces and punctuation are accepted; whole sentences and guesses posted before the photo do not win.
- No points lost for wrong guesses. First correct guess wins exactly once, including simultaneous guesses. Collecting duplicates adds to the bag.
- Photos upload from disk with a neutral attachment name. Sources and license links are revealed when a round finishes. Photo credit is shown immediately.
- Points, bags and earned milestones persist in Red Config. Each year has a separate leaderboard; previous years remain available. Off-season testing shares that year's tally, so use a test server to avoid affecting event scores.
- Active rounds and chat activity are temporary. Reloads/restarts clear them, preserving points and collections. An old photo after a restart cannot be claimed. A new message can trigger the next round after the cooldown/activity gates.

| Candy ID | Candy | Points | Spawn chance |
|---|---|---:|---:|
| corn | Candy corn | 10 | 30% |
| bears | Gummy bears | 15 | 25% |
| beans | Jelly beans | 20 | 20% |
| kitkat | Kit Kat | 30 | 15% |
| snickers | Snickers | 40 | 8% |
| chunky | Kit Kat Chunky assortment | 75 | 2% |

The rare bigger candy has its own photo and aliases. Guess `kit kat chunky` for that assortment; `kit kat` applies to the standard bar.

## Player commands

```text
[p]candy                    Rules
[p]candy bag                My collection and earned milestone IDs
[p]candy bag @member 2026    Someone's collection in a specific year
[p]candy top                Top 10 by points, then catches
[p]candy top 2026           Previous year's standings
[p]candy hint               Current round's clue (once per 10s per channel)
[p]candy rewards            Custom collection goals
[p]candy catalog            Candy IDs, aliases, points and photo credits
```

## Admin commands

```text
[p]candyset                         View current settings
[p]candyset channel #general        Choose spawn/guess channel
[p]candyset enabled true            Enable (false pauses and ends active round)
[p]candyset october true            October only (false permits off-season tests)
[p]candyset offset -300             UTC offset in minutes
[p]candyset pace 12 3 600 120        Messages, distinct users, cooldown seconds, guess seconds
[p]candyset value snickers 100      Set future Snickers catches to 100 points
[p]candyset spawn                   Immediate real round; bypass activity/cooldown
[p]candyset reward corn 10 100 Corn Champion
[p]candyset reward any 50 500 Candy Collector
[p]candyset unreward 1              Remove milestone #1; earned points remain
[p]candyset winners 2 2026          List users who earned milestone #2 for staff prize delivery
```

Milestones target a particular candy or `any` total catches. Bonus points are automatic, once per player per milestone ID per year. Labels describe custom prizes/badges; **staff deliver custom prizes manually**, using the winners command. Points are a tally, not spendable currency. No role assignment, redemption shop, or bank payments. A newly added milestone is evaluated on the next successful catch; a user who already meets its target receives it then. Removing and re-adding a milestone creates a new ID and therefore a new opportunity to earn its bonus. Up to 50 milestones per server. Value edits apply to future spawns; active round values remain fixed.

## Photos and credits

Six original Wikimedia Commons photographs are bundled, unmodified. `photos/credits.json` includes creators, source pages, licenses, original URLs and SHA-256 checksums. `content.py` contains the catalogue and runtime credits. The gummy bears and jelly beans photographs retain CC BY-SA 2.5 and CC BY-SA 3.0 licenses respectively; the other photographs are public domain or CC0. Those photo licenses apply to the images independently of the code. `download_photos.py` is an optional maintainer utility, not required when installing.

Compatibility source: https://github.com/Cog-Creators/Red-DiscordBot/releases/tag/3.5.24

## Verification and limits

Run `python guesscandy/test_game.py` from the parent directory with discord.py and Pillow installed. The tests use real Discord command registration and a small Red Config stand-in: aliases, October boundaries, once-only milestones, photo decoding/checksums, simultaneous winners, old/expired guesses, activity thresholds, spam filtering, denied users, data deletion, reload persistence, and failed uploads. No live Discord server or installed Red instance was available here, so loading and playing a round on your bot remains the deployment smoke test.

Uses one server lock to serialize catches and settings changes. Scores are stored per server/year in Red Config, appropriate for a normal community event; a very large server may need per-member storage. Red's user data deletion clears that user's tallies and identifiers in temporary activity tracking. It does not delete already posted Discord messages.
