# Guess the Candy 🎃

A Red Discord Bot cog for a chat-driven October candy hunt. People talk in #general, a real candy photograph appears, and the first person to type its name collects it and earns points. Includes **36 candy photos**, four size tiers, rotating daily goals, five collection sets, randomized spawns, and a Halloween finale. No bank integration or extra runtime dependencies.

Upgrading the original cog preserves its existing yearly points, bags, milestones, and settings. Daily/size/set fields are added on the next catch; past catches are not assigned fictional sizes or daily progress. Previously collected candies count toward sets, evaluated on the next catch. New defaults enable 30% cooldown variation and the Halloween finale. After updating the repository, reload `guesscandy` on your bot.

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
[p]candyset setreward chocolate 250 Chocolate Lovers badge — contact staff
```

Enable the **Message Content Intent** for your bot in Discord's Developer Portal and Red. The bot needs View Channel, Send Messages, Embed Links, and Attach Files in the hunt channel. Server admins or members with Manage Server can configure it.

## Default behavior

- October-only, using Eastern/New York local time with automatic daylight saving adjustment. Opens October 1 at midnight and closes November 1 at midnight each year. Use `[p]candyset timezone Eastern` or `[p]candyset timezone EST` for fixed UTC−05:00.
- A spawn requires 12 eligible messages from at least 3 distinct people and a randomly chosen cooldown. The default 10-minute base with 30% variation gives **7–13 minutes**. The first cooldown starts when the first eligible message arrives; its delay is sampled once, not on every message. A later message triggers the spawn once both gates are met. No activity means no spawn.
- One eligible contribution per person every 20 seconds. Bot/webhook messages, valid commands, Red-disabled cogs, and users denied by Red's allow/block lists do not contribute. Edit events do not count.
- One active candy per server, in the chosen channel. Guess window: 120 seconds, shortened at local midnight. Exact aliases ignoring case, spaces and punctuation are accepted; whole sentences and guesses posted before the photo do not win. Guess the candy name; its size is shown and does not need to be included in the answer.
- No points lost for wrong guesses. First correct guess wins exactly once, including simultaneous guesses. Collecting duplicates adds to the bag.
- Photos upload from disk with a neutral attachment name. Sources, license links and resizing notes are revealed when a round finishes. Photo credit is shown immediately.
- Points, bags and earned milestones persist in Red Config. Each year has a separate leaderboard; previous years remain available. Off-season testing shares that year's tally, so use a test server to avoid affecting event scores.
- Active rounds and chat activity are temporary. Reloads/restarts clear them, preserving points and collections. An old photo after a restart cannot be claimed. A new message can trigger the next round after the cooldown/activity gates.

The catalog has 34 ordinary candies and two October 31 exclusives. Recognizable treats such as candy corn and Skittles are worth fewer base points; harder unwrapped bars and rare Chunky assortments are worth more. Use `[p]candy catalog` for the full catalog, accepted aliases, base points, and normal spawn percentages. Percentages are calculated from rarity weights; the finale has a different pool.

| Size tier | Catch multiplier | Tier chance |
|---|---:|---:|
| Fun-size | 0.5× | 35% |
| Regular | 1× | 45% |
| King-size | 2× | 18% |
| Jackpot | 5× | 2% |

Size is a game reward tier drawn independently of the candy. Each tier uses the same real identification photo; photographs are not presented as separate physical product sizes. Half points round upward. The photographed Kit Kat Chunky assortment also has its own candy ID and aliases: `kit kat chunky` is accepted there; `kit kat` identifies the standard bar.

## Daily goals and collection sets

Each local date gives everyone the same three goals: a first-catch goal worth 20 bonus points, plus two rotating goals for chocolate catches, fruity catches, different candies, or total catches. Bonuses are automatic and awarded once per goal per day. Only current-day progress is stored; changing days resets progress without removing earned points or the yearly collection. Off-season testing also awards goals.

Collect at least one of every candy in a set to complete it once per year:

| Set ID | Collection | Default bonus |
|---|---|---:|
| chocolate | Chocolate Lovers: Kit Kat, Snickers, Reese's cups, Hershey's bar, Twix | 250 |
| fruity | Fruit Basket: gummy bears, jelly beans, Skittles, Starburst, Sour Patch Kids | 200 |
| halloween | Halloween Classics: candy corn, Nerds, Tootsie Roll, Blow Pop | 150 |
| retro | Old-School Treats: butterscotch, Dots, SweeTarts, Gobstoppers | 200 |
| bigbars | Big Bar Brigade: Kit Kat Chunky, Butterfinger, 3 Musketeers, PayDay | 300 |

Admins can change a set's bonus and add a custom prize description using `candyset setreward`. Bonus changes apply to future completions. Custom prizes are staff-delivered using the winners list; there is no claiming or redemption system.

## Halloween finale

By default, October 31 in the configured local time zone brings **double catch points** and exclusive Reese's Big Cup and Chocolate Gold Coins spawns. Daily, set, and custom milestone bonuses are not doubled. The finale announcement posts once per year.

When October ends, a background calendar check (once per minute) saves the full ranking and announces the top ten. Active guesses stop at the midnight boundary immediately; announcement delivery can take up to a minute. Final standings remain available with `candy finals`, independently of later off-season scores. Failed announcements retry, and missed finals recover after bot downtime. Disable the finale with `candyset finale false` to disable its boost, exclusives, and automatic final announcements. Custom prize delivery remains manual.

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
[p]candy daily              Today's goals and your progress
[p]candy sets               Collection sets and missing candies
[p]candy finals             Most recent saved October standings
[p]candy finals 2026        Saved standings for a specific year
```

## Admin commands

```text
[p]candyset                         View current settings
[p]candyset channel #general        Choose spawn/guess channel
[p]candyset enabled true            Enable (false pauses and ends active round)
[p]candyset october true            October only (false permits off-season tests)
[p]candyset timezone Eastern        Eastern time, including daylight saving
[p]candyset offset -300             Optional fixed UTC offset in minutes
[p]candyset pace 12 3 600 120        Messages, distinct users, cooldown seconds, guess seconds
[p]candyset jitter 30               Cooldown variation percent, 0–80 (0 means fixed)
[p]candyset finale true             October 31 boost, exclusives and final announcements
[p]candyset value snickers 100      Set future Snickers catches to 100 points
[p]candyset spawn                   Immediate real round; bypass activity/cooldown
[p]candyset reward corn 10 100 Corn Champion
[p]candyset reward any 50 500 Candy Collector
[p]candyset unreward 1              Remove milestone #1; earned points remain
[p]candyset winners 2 2026          List users who earned milestone #2 for staff prize delivery
[p]candyset setreward chocolate 300 Chocolate collector prize — contact staff
[p]candyset winners set:chocolate 2026    List completed-set winners for custom prize delivery
```

Milestones target a particular candy or `any` total catches. Bonus points are automatic, once per player per milestone ID per year. Labels describe custom prizes/badges; **staff deliver custom prizes manually**, using the winners command. Points are a tally, not spendable currency. No role assignment, redemption shop, or bank payments. A newly added milestone is evaluated on the next successful catch; a user who already meets its target receives it then. Removing and re-adding a milestone creates a new ID and therefore a new opportunity to earn its bonus. Up to 50 milestones per server. Value edits apply to future spawns; active round values remain fixed.

## Photos and credits

36 Wikimedia Commons photographs are bundled. The original six and several additions retain original bytes; the remaining additions are standard 960px Wikimedia previews. `photos/credits.json` includes creators, source pages, original/download URLs, licenses, resizing disclosures, and SHA-256 checksums. `content.py` contains the catalog and runtime credits. Gummy bears retain CC BY-SA 2.5; jelly beans, Tootsie Roll, and butterscotch retain CC BY-SA 3.0, including applicable share-alike terms for resized previews. Other photographs are public domain or CC0. Photo licenses apply independently of the code. `download_photos.py` is an optional maintainer utility; installations need no downloads.

Compatibility source: https://github.com/Cog-Creators/Red-DiscordBot/releases/tag/3.5.24

## Verification and limits

Install `guesscandy/requirements-dev.txt`, then run `python guesscandy/test_game.py` from the repository root. The tests use real Discord command registration and a small Red Config stand-in: alias collisions, all 36 photo checksums/licenses, sizes, October/finale boundaries, daily resets, set/milestone bonuses, randomized cooldowns, simultaneous winners, expired guesses, spam filtering, denied users, data deletion, reload persistence, failed uploads, final snapshots, retry behavior, and downtime recovery. A dedicated GitHub Actions workflow runs these checks on cog changes. Loading and playing a round on your live Red bot remains the deployment smoke test.

Uses one server lock to serialize catches and settings changes. Scores are stored per server/year in Red Config, appropriate for a normal community event; a very large server may need per-member storage. Red's user data deletion clears that user's tallies and identifiers in temporary activity tracking. It does not delete already posted Discord messages.

### Embeds and Eastern schedule

Player commands, admin replies, round results and announcements use Halloween-themed embeds. Daily goals include progress bars and leaderboard winners receive medal icons. Existing command names still work.

The default clock is `America/New_York` (Eastern local time), including daylight saving changes. October opens at midnight October 1 and ends at midnight November 1 in that zone. Use `[p]candyset timezone Eastern` to select it explicitly, `[p]candyset timezone EST` for fixed UTC−5, or `[p]candyset offset` for a custom fixed offset. The former default −300 offset migrates to Eastern on load; custom offsets and all tallies are preserved.

At each local midnight, active rounds expire and daily goals reset. Season points, collections and earned milestones remain. A spawn near midnight displays the shortened deadline. Discord timestamps display in each viewer's own local time.
