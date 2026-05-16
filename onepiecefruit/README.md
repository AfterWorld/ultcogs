# OnePieceFruit 🍎

A Red-DiscordBot companion cog for [vertyco's LevelUp](https://github.com/vertyco/vrt-cogs).

Assigns Devil Fruits to users as they level up, tracks awakenings, and lets users reroll using your server's Beri economy.

---

## Requirements

- Red-DiscordBot v3.5+
- vertyco's `LevelUp` cog installed and loaded
- Red's built-in `bank` (economy) system

---

## Installation

```
[p]repo add ults https://github.com/AfterWorld/ultcogs
[p]cog install ults onepiecefruit
[p]load onepiecefruit
```

---

## How It Works

The cog listens for LevelUp's `on_levelup` event, which is dispatched as:

```python
bot.dispatch("levelup", guild, member, level, channel)
```

### Devil Fruit Milestones

| Level | Event |
|-------|-------|
| 5     | 🍎 Random Devil Fruit assigned |
| 50    | ⚡ Stage 1 Awakening unlocked |
| 100   | 🌟 Full Awakening achieved |

### Rarity Tiers

| Tier | Drop Chance | Count |
|------|-------------|-------|
| 🔵 Paramecia | 50% | 34 fruits |
| 🟢 Zoan | 25% | 7 fruits |
| 🟠 Logia | 15% | 11 fruits |
| 🟤 Ancient Zoan | 7% | 6 fruits |
| 🟣 Mythical Zoan | 2.5% | 6 fruits |
| ⭐ Legendary | 0.5% | 5 fruits |

### Reroll Costs (Beri)

| Reroll # | Cost |
|----------|------|
| 1st | 10,000 |
| 2nd | 25,000 |
| 3rd | 50,000 |
| 4th | 100,000 |
| 5th | 200,000 |
| 6th | 350,000 |
| 7th | 500,000 |
| 8th | 750,000 |
| 9th | 1,000,000 |
| 10th | 1,500,000 |

Costs continue rising by about ×1.5 after the 10th reroll.

Rerolling **resets awakening stage to 0** — you start fresh with the new fruit.

---

## Commands

### User Commands

| Command | Description |
|---------|-------------|
| `[p]df info [member]` | Show your (or another's) Devil Fruit |
| `[p]df toggle [on/off]` | Enable or disable your fruit embed on `[p]profile` / `[p]pf` |
| `[p]df reroll` | Reroll your fruit for Beri |
| `[p]df list` | Show all fruit users in the server |
| `[p]df types` | Show rarity tiers and drop chances |
| `[p]df browse [rarity]` | Browse fruits by rarity type |

Aliases: `[p]devilfruit` = `[p]df`

### Admin Commands (requires Administrator)

| Command | Description |
|---------|-------------|
| `[p]df admin assign <member> [fruit_name]` | Assign a specific or random fruit |
| `[p]df admin reset <member>` | Remove a member's fruit data |
| `[p]df admin awaken <member> <0\|1\|2>` | Manually set awakening stage |
| `[p]df admin resetrerolls <member>` | Reset reroll counter to 0 |

---

## Notes

- Users cannot have two Devil Fruits — rerolling replaces the old one permanently.
- Awakening stage is tied to the **current fruit** — rerolling resets it.
- The cog stores data in `cog_data_path/onepiecefruit.json`.
- Fruit descriptions are flavor text only — no actual game mechanics are modified.
