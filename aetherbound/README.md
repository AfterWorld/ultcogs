# Aetherbound — Phase 1

An active, original anime-themed adventure for Red. Characters explore Hoshifall's
Glimmerwood and Embervein regions, fight with buttons, acquire equipment and forge
better builds. Progress comes from completed encounters, not time spent online.

## Install and first setup

Requires Red 3.5.24+, Python 3.11, and the discord.py version supported by Red.
No additional production Python packages are required. Do not install the dev
requirements over a running Red instance.

Install through Red's Downloader:

```text
[p]cog install <your-ultcogs-repo-name> aetherbound
[p]load aetherbound
[p]aetherset setup
```

`[p]` means your actual prefix, for example `.`. Root commands are **aether** and **aetherset**. **ae** and **a** are added as
shortcuts when free. GobCog/Adventure already uses **a**; Aetherbound preserves
that command rather than preventing either cog from loading. Setup reports which
shortcuts were registered. All examples also work under an available shortcut.
This build uses prefix commands and persistent buttons; it does not register
slash commands or replace `.help`.

Setup is admin-only (`manage_guild` or Red's admin check). The bot needs:

- Manage Channels, Manage Roles, Manage Messages, Manage Threads.
- View Channels, Send Messages, Embed Links, Attach Files, Read Message History.
- Create Public Threads and Send Messages in Threads.
- Mention Everyone, used exclusively to ping explicitly selected notification
  roles through restrictive `AllowedMentions`; no `@everyone`/`@here` is sent.
- Message Content Intent enabled in both the bot configuration and Developer Portal.

The bot's highest role must remain above its three notification roles.

**Loading the cog does not create Discord resources.** Running setup does. Setup
creates these resources, records their IDs after each successful creation, and
repairs/reuses them on subsequent runs:

| Channel | Purpose | Member messages |
|---|---|---|
| start-here | Tutorial entry instructions and notification buttons | Disabled |
| adventures | Game commands and combat messages | Allowed |
| monster-spawns | Monster/boss announcements with Engage buttons | Disabled |
| trading-post | Explicit trade offers, automatically threaded | Moderated |
| tavern | General conversation | Allowed |

The `✦ Aetherbound` category is initially placed roughly one-third down the
category list, below at least one existing category when possible. Setup repairs
only recorded game channels; it does not repurpose unrelated channels with the
same name. It replaces overwrites on its managed channels to restore the game
policy. Server administrators retain Discord's normal permission bypass.

```text
[p]aetherset position 3
[p]aetherset spawns true 30
[p]aetherset spawns false
[p]aetherset spawn tsukara
[p]aetherset spawn raizen
```

Position is a 1-based **category** index. Existing servers cannot select the very
top position. Setup leaves an existing category's placement unchanged. Automatic
spawns start after setup; default interval 30 minutes, configurable 5–1440.

## Updating an existing game

```text
[p]cog update aetherbound
[p]reload aetherbound
[p]aetherset guides
```

The last command updates the existing welcome message in place and creates or
refreshes one example embed in each recorded game channel. Use `[p]aetherset setup`
instead if channels or roles need repairing. Saved heroes and tutorial rewards
are preserved. Neither command deletes player progress. Guides use your current
server prefix; refresh them after changing it.

All five guides have persistent **My next step** and **My profile** buttons that
privately show the clicking player's saved data. Players without a character see
creation instructions. The welcome guide also keeps the three opt-in alert buttons.
Example encounters are clearly labeled; only real spawn posts have Engage buttons.

## Rewarded tutorial

```text
[p]aether create vanguard Your Name
[p]aether tutorial
[p]aether inventory
```

Classes: Vanguard (strength), Strider (dexterity), Arcanist (intelligence).
One character per user per server. Characters, economies, encounters and settings
are isolated between servers.

The tutorial requires actual actions, with one-time rewards:

1. Creation grants a class weapon, off-hand item and two potions. Equip the weapon.
2. Win safe practice after using Attack, Guard **and** a skill. Receive six armor
   pieces, 60 gold, four iron and two essence.
3. Equip the chest piece. Other armor can be equipped too.
4. Forge `ring1` for 30 gold, four iron and two essence.
5. Equip that forged ring.
6. Win a real exploration encounter. Receive the Wayfarer Star relic, 100 gold
   and two more potions.

After all six steps, review the completion instructions and continue quests or the dungeon.
Lessons provide copyable, prefix-aware commands with your actual equipment IDs.
Practice battles show an action checklist and tutorial battle endings show the
next lesson automatically. Reopen your current step with `[p]aether tutorial`.

Starter materials cannot be spent on upgrades or alternate recipes before the
forging lesson. Tutorial gear cannot be salvaged before graduation. Reopening
the tutorial or replaying a click never grants the same reward twice.

## Player commands

| Command (after `[p]aether`) | What it does |
|---|---|
| `tutorial` | Resume your current lesson |
| `profile` | Temporary button opens your private character sheet |
| `appearance <description>` | Cosmetic description, up to 200 characters |
| `skills` | Class abilities, costs, attributes and mechanics |
| `inventory [page]` | Items with IDs, equipped markers, materials and gold |
| `item <id>` | Equipment details and current slot occupant |
| `equip <id> [id ...]` / `unequip <slot>` | Equip up to 11 items automatically by slot, or remove a slot |
| `allocate <attribute> [amount]` / `respec` | Allocate level-up points or refund them |
| `practice` | Tutorial training encounter |
| `explore [glimmerwood\|embervein]` | Personal, immediately available encounter |
| `resume` | Restore your saved battle controls |
| `recipes` | Crafting and upgrade costs |
| `forge <slot> [normal\|tsukara\|raizen] [twohand]` | Forge equipment; `twohand` is a boolean |
| `upgrade <id>` | Guaranteed upgrade, capped at +5 |
| `salvage <id>` | Permanently destroy unequipped gear for materials |
| `potion` | Buy a combat healing potion for 15 gold |
| `bestiary [monster-key]` | List enemies or inspect a portrait and special loot |
| `quests [accept\|claim] [quest-key]` | View the board, accept a quest or claim a completed quest |
| `payday` | Claim daily gold, once per UTC day after tutorial graduation |
| `shop` / `tavern` | Browse personal daily gear and supplies |
| `buy <dated-offer-code>` | Buy the displayed item at its displayed price |
| `rarities` | Explain all seven rarity labels and drop unlocks |
| `loot` | Collect overflow equipment after freeing bag space |
| `dungeon` | Enter/continue Hollow Trail, level 6+ |
| `abandon` | Leave a dungeon between rooms |
| `notifications` | Toggle trading, boss and adventure role subscriptions |

### Private character sheets

Use **My profile** on any game channel guide to open a private Components V2
character sheet. **Overview**, **Combat** and **Equipment** tabs separate your
progress, stats and loadout. Each tab and **Refresh** reloads your saved stats
and edits the same private message. Controls expire after three minutes of
inactivity; open the profile again to continue. No image-generation dependency
or profile image upload is required.

Prefix messages cannot be ephemeral. `[p]aether profile` therefore posts only a
small owner-only **Open my private profile** button, automatically deleted after
30 seconds. Clicking it opens the private sheet. The invoking command is also
deleted when the bot has permission; if it cannot be deleted, no character stats
are exposed. Other players cannot use that launch button to view your character.
Existing persistent guide buttons pick up this behavior after reloading the cog.

### Combat and progression

Personal encounters select fixed-level monsters near the player's level in the
chosen region. Embervein unlocks at level 8. Shared spawns choose bosses with a
15% probability; within normal/boss pools selection is uniform. All 15 enemies
can spawn, even if some players are not ready for them. Encounters disclose their
level and expire after 15 minutes; at most one unclaimed shared spawn is active
per server. Claiming requires being no more than four levels below the enemy.

**Engage claims a solo encounter**, then posts its battle in adventures. Public
cooperative fights are Phase 3. Shared spawn claims and player battle creation
are one SQLite transaction, so two users cannot claim the same encounter.

Choose Attack, Guard, a class skill, Potion or Flee. Charged attacks are announced
before they resolve. Only the battle owner may act. Every action checks the saved
battle ID and turn number, rejecting stale/double clicks. Defeat loses no gear or
EXP; fleeing grants no victory rewards. Personal encounters begin at full health.
Hollow Trail preserves health between its four rooms and permits saving between
rooms; defeating its final boss completes the dungeon.

The level cap is 20. Each level grants two allocatable attribute points. The next
level costs `80 + 35L + 8L²` EXP. Normal equal-level wins award `24 + 8L` EXP;
boss rewards are larger. Old, trivial enemies give sharply reduced EXP/gold.
There is no energy timer outside combat, idle EXP, daily streak or paid system.

See [BALANCE.md](BALANCE.md) for 15,750 seeded encounter simulations, assumptions,
class outcomes and leveling pace. This is a baseline, **not a claim that human
playtesting has been completed**.

### Equipment

Eleven slots: main hand, off hand, head, chest, hands, legs, feet, neck, two
independent rings and a relic. Two-handed main weapons remove the off hand;
re-equipping an off-hand item requires removing the two-handed weapon first.

Equip multiple items using `[p]aether equip ID1 ID2 ID3` or the shorthand
`[p]aether ID1 ID2 ID3`. Replace the example IDs with IDs from inventory. Input
order does not matter. A batch must contain one item per equipment slot, with
separate ring1/ring2 items. Duplicate IDs, conflicting slots, missing items,
level restrictions and incompatible two-handed/off-hand combinations reject the
entire batch. Nothing changes on failure. A two-handed weapon by itself returns
an equipped off-hand to the bag; replacing it with a one-handed weapon and an
off-hand in one batch works in either order.

Each item instance has a unique ID, level, rarity, a bounded affix budget,
rolled attribute bonuses and upgrade level. Rare boss recipes grant spiritward
or emberblade; the tutorial relic grants wayfarer. Identical unique effects do
not stack. Inventory capacity is 200; excess combat drops wait in loot overflow. Collect them
with `[p]aether loot` after freeing space. New encounters stop when 20 or more
overflow items are waiting (a final two-drop victory can bring the total to 21).
All rarity affix points are distributed from a fixed budget. Critical chance
is capped at 35%, armor at 100, upgrades at +5 and energy capacity at 80.

Forge any slot from iron, essence and gold. Boss recipes also require two boss
cores. Further monster-specific uses for fangs, wood, crystal and ember, plus
sockets, enchanting, specializations and expanded weapon types, are later phases.
The schema includes an unused socket field for those extensions. There is no
socket/enchant command in Phase 1.

## Quests: accept, complete, claim

```text
[p]aether quests
[p]aether quests accept first_hunts
[p]aether explore
[p]aether quests claim first_hunts
```

For a new character, accepting **Clear the Path** starts its three-win counter;
complete three non-practice victories after acceptance, then claim. The other
keys are `guardian` (defeat Tsukara) and `trail` (complete Hollow Trail). Each pays
once. The board shows objectives, progress, rewards and the exact next command.
The old `[p]aether quests <key>` claim shorthand still works. Existing characters
have unclaimed quests accepted with a zero baseline during the additive migration,
so progress earned before this update is preserved. Existing claimed quests stay
claimed. Practice does not count; accepted quests do not expire.

## Rarities, named gear and boss rewards

| Tier | Minimum drop/shop level | Power rank | Normal loot chance at level 20 |
|---|---:|---:|---:|
| Common | 1 | 1 | 60% |
| Uncommon | 1 | 2 | 26% |
| Rare | 3 | 3 | 10% |
| Epic | 6 | 4 | 3.2% |
| Legendary | 10 | 5 | 0.7% |
| Mythic | 16 | 6 | 0.1% |
| Unique | Encounter-specific | 4 | Additional roll; see below |

Locked-tier probability is folded into Common. Higher tiers add modest power and
a capped attribute budget: at most four affix rolls, each `1 + level // 5` points.
Unique is a named special-effect category with an Epic-sized stat budget, not a
stronger tier than Mythic. Effects are the existing bounded Wayfarer, Spiritward
and Emberblade effects and do not stack with duplicate copies. Forging retains its
existing Uncommon normal / Rare boss recipe tiers.

Generic gear now has names such as **Moonlit Signet**, **Dawnsteel Blade** and
**Starwoven Hood of First Light**. Rarity and IDs display separately. Old generic
names are migrated deterministically; IDs, equipped slots, upgrades, affixes and
power do not change. Named starter/relic gear keeps its name.

Boss wins guarantee one signature item, at least Rare:

- **Tsukara:** Hollow Antler Pendant, Rootsong Aegis or Moonbark Mantle.
- **Raizen:** Furnace Warden's Edge, Cinderlord Grasp or Crucible Striders.

Boss tier weights before level gates are 5% Common, 20% Uncommon, 40% Rare,
25% Epic, 8.5% Legendary and 1.5% Mythic; Common/Uncommon rolls are promoted to
Rare for signature drops. Each boss additionally has a **3%** unique chance:
**Tsukara's Living Antler** or **Raizen's Final Ember**. Lantern Slime, Mossfang
Wolf, Hollow Mask and Riftbound Ronin each have a **0.5%** additional unique roll
for their own item. Other monsters use the standard loot pool. Inspect an enemy
with `[p]aether bestiary <key>` to see its signature/unique names and chances.
Full bags preserve both standard and unique rewards in overflow.

## Daily payday and Lantern Tavern shop

```text
[p]aether payday
[p]aether shop
[p]aether buy <copy-the-dated-code-from-the-shop>
```

After graduation, payday grants **40 + 3 × character level** gold, once per UTC
calendar day (43–100 gold). It grants no EXP, requires an explicit claim, and has
no streak or missed-day penalty. Both payday and shop rotation use **00:00 UTC**.
No Red-bank/Adventure currency is touched.

Each player has personal daily stock within their server. There is one equipment
offer per unlocked ordinary rarity, with a minimum of three equipment offers.
Each equipment offer has one purchase available. Two potion pouches (three potions
for 40 gold each) and two forging bundles (4 iron + 2 essence for 70 gold each)
are also available. Equipment costs `(25 + 10 × level) × rank²` gold.
Unique items and boss signatures are encounter-only.

Offers are generated reproducibly per server/player/date and saved on first view;
restarts and leveling up do not reroll today's items or refill stock. Tomorrow's
offers use the new level. Dated codes reject stale purchases across midnight.
Purchase validation, gold deduction, stock use and item delivery share one SQLite
transaction. Full bags, insufficient gold, tutorial restrictions and active combat
reject purchases without charging the player. The shop preview shows slot, level,
rarity, power, bonuses, price and remaining stock before purchase.

The persistent **Tavern shop** button in channel guides opens a private preview.
Run `[p]aetherset setup` after updating to repair Attach Files permissions and
refresh the guides; `[p]aetherset guides` is sufficient if permissions are ready.

## Monster artwork and design reference

All 13 monsters and two bosses have original AI-generated portraits bundled in
`assets/monsters/`. They appear in spawn posts, battles and individual bestiary
entries. No external scraping or image download happens at runtime. Existing
pre-update battles gain their image when resumed; combat turns retain the uploaded
attachment. The asset README records the generation method and prompts.

[GobCog](https://github.com/aikaterna/gobcog) was reviewed for named equipment,
rarity progression, readable stats and merchant ideas. This implementation uses
original content and rules, per-server characters and individual active battles;
it does not import its shared adventures, rebirth economy, item code or artwork.

## Trading and notifications

Accepted offer grammar is intentionally explicit:

```text
trading iron sword for crystal staff
trade two potions for iron
wtt iron sword for item
```

Offers must start with trading/trade/wtt and contain ` for `. Links, mass/user
mentions, attachments and multiline offers are rejected. Ordinary messages in
the trading post are deleted, including ordinary messages posted by moderators.
Bot messages are ignored. The bot opens a public thread attached to each valid
offer; normal conversation is allowed **inside** those threads. Edited offers are
checked again. This is syntax-based moderation, not AI understanding of every
possible sentence, and it does not validate ownership or appraisal of offered
items. Staff can still moderate misleading offers.

One new offer per user every five minutes. Threads auto-archive after 24 hours of
inactivity. Pending thread creation is recoverable after restart, and duplicate
message events do not create duplicate threads.

**Phase 1 trading is negotiation only. It does not transfer items.** Atomic item
exchanges, confirmations, listings and player markets belong to Phase 3.

Three separate, permission-free, opt-in roles are created: Aetherbound • Trading,
Aetherbound • Bosses, Aetherbound • Adventures. Buttons toggle only these stored
roles. Trading role alerts are limited to one per 15 minutes per server; boss and
adventure roles are pinged for their corresponding ambient spawns. No role is
automatically assigned on character creation. A repurposed privileged notification
role is never granted through a button.

## Persistence, recovery, and operation

SQLite lives under Red's cog data directory (`aetherbound.sqlite3`), outside the
installed code. Transactions include state and rewards together. Unloading or
updating the cog does not reset progress. Persistent views are restored on load;
`[p]aether resume` also recovers a battle whose message was deleted or could not be
updated. Background tasks and views stop on unload.

Back up the database using SQLite's backup API or while the bot is stopped. Do
not copy only the main file from a live WAL database. Restore into the same cog
data path with the bot stopped. Newer database schema versions are rejected
rather than silently downgraded.

Red user-data export/deletion includes all servers' character records and stored
trade message/thread references. Existing Discord posts, notification roles and
thread content remain Discord-managed; deleting a character record does not
purge server history or remove notification subscriptions.

Automated checks use mocked Discord network calls. The operational checklist below
covers server permissions and live Discord behavior; source updates do not reload
your running bot or change its channels automatically.

## Validation

Use a separate Python 3.11 environment:

```sh
python -m pip install -r aetherbound/requirements-dev.txt
python -m ruff check --config aetherbound/ruff.toml aetherbound
python -m ruff format --check --config aetherbound/ruff.toml aetherbound
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -c aetherbound/pytest.ini --confcutdir=aetherbound/tests aetherbound/tests -q
python -m aetherbound.balance
```

Tests use the real Red 3.5.24 and discord.py 2.7.1 classes with mocked network I/O.
They cover full tutorials for all classes, caps, reward idempotency, cross-server
isolation, concurrent clicks/claims, restoration, role opt-in and privilege
checks, setup/repair/placement, trading moderation and pending-thread recovery.

### Live smoke-test checklist

- Load alongside the existing Adventure cog; `.help aether` works.
- Run setup twice; verify five channels/three roles without duplicates and the
  category's actual sidebar position. Delete a managed channel and rerun setup.
- As a non-admin member, confirm no typing in start-here/monster-spawns; buttons
  work and trade thread replies are allowed.
- Finish the tutorial, including a restart midway through training and a stale
  battle button click. Verify the starter rewards are granted only once.
- Post an offer, ordinary chat, an edited invalid offer, and replies in its thread.
- Toggle each notification role and verify only its opt-in subscribers are pinged.
- Complete Hollow Trail, a boss spawn and a boss recipe; inspect real play pacing.
- Delete a battle message, use resume, unload/reload and confirm progress survives.

## Next phases

2. Specializations, expanded skills, sockets/enchanting, more gear and regions.
3. Parties, cooperative dungeons, guilds and confirmed item exchanges.
4. Raids, endgame crafting, world events and optional PvP.
