# OnePieceFruit 🍎

A Red-DiscordBot companion cog for [vertyco's LevelUp](https://github.com/vertyco/vrt-cogs). It assigns Devil Fruits as members level up, tracks awakenings, supports Beri rerolls and duels, and includes a Pirate Rep leaderboard.

## Requirements

- Red-DiscordBot 3.5 or newer
- vertyco's LevelUp cog (needed for automatic fruit assignment)
- Red's built-in bank, or an installed Beri economy cog
- Python package `pydantic>=2.0`

## Installation

```text
[p]repo add ults https://github.com/AfterWorld/ultcogs
[p]cog install ults onepiecefruit
[p]load onepiecefruit
```

## Fruit progression

The cog listens for LevelUp's `on_levelup` event (`bot.dispatch("levelup", guild, member, level, channel)`). Level jumps are handled, so members who pass a milestone between events still receive the relevant rewards.

| Level | Reward |
|---|---|
| 5 | Random Devil Fruit |
| 50 | Stage 1 Awakening |
| 100 | Full Awakening |

Rarity weights are Paramecia 50%, Zoan 25%, Logia 15%, Ancient Zoan 7%, Mythical Zoan 2.5%, and Legendary 0.5%. Rerolls use an escalating Beri cost; some current fruit types grant discounts or daily stipends. Fruit abilities are profile flavor text and do not modify combat stats.

## Commands

Replace `[p]` with your configured Red prefix. The `df` alias is available for `devilfruit`.

### Member commands

| Command | Description |
|---|---|
| `[p]df info [member]` | View a Devil Fruit and Pirate Rep profile |
| `[p]df toggle [on\|off]` | Show or hide your fruit card after LevelUp profile commands |
| `[p]df search <term>` | Search the fruit catalog |
| `[p]df browse [rarity\|event]` | Browse a rarity or active event pool |
| `[p]df types` | Show rarity weights and fruit counts |
| `[p]df reroll` | Confirm and pay to replace your fruit |
| `[p]df rerollcost [member]` | Preview upcoming base reroll costs |
| `[p]df list` | List the server's Devil Fruit users |
| `[p]df duel <member> [wager]` | Challenge a fruit owner; the target must accept a wager |
| `[p]df rep [member]` | View a Pirate Rep card |
| `[p]df top` | Show the Pirate Rep leaderboard |
| `[p]df weekly` | Show this week's message leaderboard |
| `[p]df streak` | Show active Pirate Rep streaks |
| `[p]rollchar` | Roll a permanent, standalone One Piece character sheet |
| `[p]mychar` | View your character sheet |
| `[p]charinfo <member>` | View another member's character sheet |

Pirate Rep counts at most one message per member every 30 seconds. The bot does not store message text.

The character generator is a standalone roleplay roll. Its Devil Fruit result does not change or follow the member's `[p]df` assignment or rerolls.

### Administrator commands

The `[p]df admin` group requires Administrator permission or the matching Red permissions.

| Command | Description |
|---|---|
| `[p]df admin assign <member> [fruit|rolls]` | Assign a named fruit, or randomly roll and reveal the result (default 6 steps; set 2–10 steps with a number) |
| `[p]df admin reset <member>` | Remove a member's fruit record |
| `[p]df admin awaken <member> <0\|1\|2>` | Set awakening stage |
| `[p]df admin resetrerolls <member>` | Reset the reroll count and price tier |
| `[p]df admin setrep <member> <rep>` | Set Pirate Rep |
| `[p]df admin setrank <member> <rank>` | Set Rep to a rank's minimum |
| `[p]df admin resetrep <member>` | Remove a member's Rep history |
| `[p]df admin rankchannel [#channel]` | Set or view rank-up announcements |
| `[p]df admin event [name\|off]` | Set or clear the event fruit pool |
| `[p]df admin giveaway <amount> [winners] [rarity]` | Give Beri to random eligible fruit owners |
| `[p]df admin audit [member] [limit]` | View recent administrative audit entries |
| `[p]df admin clearaudit` | Confirm and clear this server's audit entries |
| `[p]df admin bulkassign` | Backfill fruit and awakening data from LevelUp |
| `[p]df admin info <member>` | View detailed fruit, Rep, and audit data |
| `[p]chardelete <member>` | Delete a character sheet and allow a new roll |

## Data

Fruit progression and audit data are stored in the cog data directory; Pirate Rep uses a separate file, and character sheets use Red Config. Red's user-data deletion request removes a user's records from these stores. The cog stores user IDs, progression choices, reroll history, message counts and dates, and audit actions; it does not store message content.
