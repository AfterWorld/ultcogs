# 🏹 Hunger Games Battle Royale Bot

A comprehensive **One Piece themed** Hunger Games battle royale game for Discord servers. Watch as your server members fight to become the ultimate Pirate King in randomly generated, dramatic battles across the Grand Line!

## 📋 Table of Contents
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Commands](#-commands)
- [Configuration](#-configuration)
- [Arena Conditions](#-arena-conditions)
- [Game Mechanics](#-game-mechanics)
- [Examples](#-examples)
- [Troubleshooting](#-troubleshooting)
- [Support](#-support)

## ✨ Features

### 🎮 **Core Game Features**
- **Randomized PvP Battle Royale** - Pure chance-based combat system
- **One Piece Themed Events** - Sea Kings, Devil Fruits, Marine encounters
- **Dynamic Arena Conditions** - 10+ weather/environmental conditions that change gameplay
- **Sponsor Revival System** - Eliminated players can be brought back to life
- **Alliance System** - Temporary partnerships and dramatic betrayals
- **District Assignment** - Players represent different themed districts
- **Detailed Statistics** - Win/loss tracking, kill counts, and leaderboards

### 🌊 **Grand Line Arena Conditions**
- **Calm Belt** - Sea King attacks increase, Devil Fruit users struggle
- **Marine Blockade** - World Government interference and capture events
- **Devil Fruit Aura** - Power malfunctions and ability chaos
- **Raging Typhoon** - Lightning strikes and drowning events
- **New World Chaos** - Yonko-level destruction and impossible weather
- **Ancient Weapon Energy** - World-ending devastation events
- *...and 4 more unique conditions!*

### 📊 **Advanced Features**
- **Poll System** - Democratic game starting with button voting
- **Custom Images** - Upload custom arena backgrounds for events
- **GIF Integration** - Automatic GIF selection based on game context
- **Statistics Dashboard** - Detailed player performance tracking
- **Admin Controls** - Comprehensive management and testing tools
- **Economy Integration** - Automatic credit rewards for winners

## 🚀 Installation

### Prerequisites
- **Red-DiscordBot v3.4.0+** (Tested on Red v3.5+)
- **Python 3.8+**
- Basic Discord bot permissions (Send Messages, Embed Links, Add Reactions)

### Method 1: Direct Installation (Recommended)
```bash
# Add the repository
[p]repo add ultcogs https://github.com/AfterWorld/ultcogs

# Install the Hunger Games cog
[p]cog install ultcogs hg

# Load the cog
[p]load hg
```

### Method 2: Manual Installation
1. Download the cog files from: https://github.com/AfterWorld/ultcogs/tree/main/hg
2. Extract to your Red bot's cogs directory: `[botdir]/cogs/hg/`
3. Load the cog: `[p]load hg`

### Method 3: Git Clone
```bash
cd /path/to/your/redbot/cogs/
git clone https://github.com/AfterWorld/ultcogs.git
cd ultcogs
[p]cog install local hg
[p]load hg
```

## ⚡ Quick Start

1. **Install the cog** using one of the methods above
2. **Start your first game**: `[p]he 60` (60 second countdown)
3. **React with 🏹** to join the battle royale
4. **Watch the chaos unfold** as players fight across the Grand Line!

### Basic Setup Commands
```bash
# Set base reward for winners
[p]hungergames set reward 1000

# Set sponsor revival chance
[p]hungergames set sponsor 20

# Set poll threshold for democratic starts
[p]hungergames set pollthreshold 8
```

## 📖 Commands

### 🎮 **Game Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `[p]he [countdown]` | Start a battle royale with reaction signup | `[p]he 90` |
| `[p]hg [threshold/poll]` | Start with threshold or poll system | `[p]hg 5` or `[p]hg poll` |
| `[p]poll [threshold]` | Create a button-based poll to start | `[p]poll 10` |

### 📊 **Information Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `[p]hungergames alive` | Show current alive players | `[p]hg alive` |
| `[p]hungergames status` | Check game status and stats | `[p]hg status` |
| `[p]hungergames stats [member]` | View player statistics | `[p]hg stats @user` |
| `[p]hungergames leaderboard [stat]` | View server leaderboards | `[p]hg lb wins` |
| `[p]hungergames config` | View current server settings | `[p]hg config` |

### ⚙️ **Configuration Commands** (Admin Only)

| Command | Description | Default | Range |
|---------|-------------|---------|--------|
| `[p]hungergames set reward <amount>` | Set base winner reward | 500 | 100-100,000 |
| `[p]hungergames set sponsor <chance>` | Set revival chance % | 15% | 1-50% |
| `[p]hungergames set interval <seconds>` | Set event timing | 30s | 10-120s |
| `[p]hungergames set pollthreshold <number>` | Set poll minimum | None | 2-50 |
| `[p]hungergames set pollpingrole <role>` | Set role to ping for polls | None | Any role |
| `[p]hungergames set blacklistrole <role> <add/remove>` | Manage role blacklist | None | Any role |
| `[p]hungergames set tempban <member> <duration>` | Temporarily ban players | None | 1m-30d |

### 🌊 **Arena Conditions** (Admin Only)

| Command | Description | Example |
|---------|-------------|---------|
| `[p]hungergames condition info` | Show current arena condition | `[p]hg condition info` |
| `[p]hungergames condition list` | List all available conditions | `[p]hg condition list` |
| `[p]hungergames condition test [name]` | Force test a condition | `[p]hg condition test calm_belt` |

### 🔧 **Management Commands** (Admin Only)

| Command | Description |
|---------|-------------|
| `[p]hungergames stop` | Force stop current game |
| `[p]hungergames debug` | Show debug information |
| `[p]hungergames test` | Test all event types |

## ⚙️ Configuration

### 🎯 **Essential Settings**

#### **Poll System Setup**
```bash
# Set minimum players needed for polls
[p]hungergames set pollthreshold 8

# Set role to ping when polls start (optional)
[p]hungergames set pollpingrole @HungerGames

# Players can then use:
[p]poll          # Uses server threshold
[p]hg poll       # Advanced poll with buttons
```

#### **Reward Configuration**
```bash
# Base reward (scales with game size automatically)
[p]hungergames set reward 1500

# Sponsor revival chance (higher = more revivals)
[p]hungergames set sponsor 25
```

#### **Game Timing**
```bash
# Time between event rounds (lower = faster games)
[p]hungergames set interval 25
```

### 🛡️ **Moderation Settings**

#### **Role Management**
```bash
# Prevent certain roles from participating
[p]hungergames set blacklistrole @Banned add
[p]hungergames set blacklistrole @Timeout add

# Remove roles from blacklist
[p]hungergames set blacklistrole @Banned remove
```

#### **Player Bans**
```bash
# Temporary bans from participating
[p]hungergames set tempban @user 1d      # 1 day
[p]hungergames set tempban @user 2h30m   # 2 hours 30 minutes
[p]hungergames set tempban @user remove  # Remove ban
```

## 🌊 Arena Conditions

Arena conditions dynamically change the battlefield and event probabilities, making each game unique!

### 🌀 **Condition Types**

| Condition | Effects | Theme |
|-----------|---------|-------|
| **🌊 Calm Belt** | +40% Sea King events, +20% Devil Fruit weakness | Deadly stillness |
| **⛈️ Raging Typhoon** | +50% drowning, +30% lightning deaths | Massive storms |
| **👹 Devil Fruit Aura** | +25% power events, +15% sponsor chance | Mystical energy |
| **🚢 Marine Blockade** | +35% government events, -20% survival | Military presence |
| **🌪️ Knock Up Stream** | +40% falling deaths, +25% aerial combat | Chaotic currents |
| **🌀 Deadly Whirlpools** | +45% drowning, +30% ship collisions | Spinning death |
| **🏔️ Red Line Cliffs** | +40% climbing deaths, +50% fall damage | Towering heights |
| **👻 Florian Triangle** | +50% ghost events, +40% reduced visibility | Supernatural mist |
| **🔥 New World Chaos** | +35% Haki storms, +40% island destruction | Ultimate chaos |
| **⚡ Ancient Power** | +60% mass destruction, +50% devastation | World-ending force |

### 📅 **Condition Timing**
- **Conditions change every 6 rounds** or with 15% random chance per round
- **Early Game** (Rounds 1-5): Basic conditions like storms and whirlpools
- **Mid Game** (Rounds 6-15): Supernatural conditions like Devil Fruit energy  
- **End Game** (Final 5): Epic conditions like Ancient Weapon energy

## 🎮 Game Mechanics

### ⚔️ **Combat System**
- **Fully Randomized** - No player skill involved, pure chance
- **Event-Based** - Deaths occur through dramatic story events
- **Environmental Kills** - Arena hazards can eliminate players
- **Player vs Player** - Direct combat between participants
- **Multi-Kills** - Rare events can eliminate multiple players

### 💰 **Reward System**
Automatic credit rewards scale with performance:
- **Base Reward**: Set by admins (default: 500)
- **Kill Bonus**: +50 credits per elimination
- **Survival Bonus**: +10 credits per round survived (max 500)
- **Game Size Multiplier**: Larger games = bigger rewards

### 📈 **Statistics Tracking**
- **Wins**: Total victories achieved
- **Deaths**: Times eliminated from games  
- **Kills**: Total eliminations made
- **Revives**: Times brought back by sponsors
- **Games Played**: Total participation count
- **Win Rate**: Percentage of games won

### 🏆 **Ranking System**
Players earn titles based on performance:
- **🌟 Legendary Champion** (10+ wins)
- **👑 Elite Victor** (5+ wins)
- **🥇 Veteran Survivor** (3+ wins)
- **🏹 Arena Survivor** (1+ wins)
- **💀 Battle-Hardened** (5+ games, no wins)
- **🆕 Fresh Tribute** (New players)

## 💡 Examples

### 🎬 **Example Game Flow**

```
🗳️ UltPanda started a Hunger Games poll!
Target: 8 players | Current: 3 players
[Join Game] [Leave Game] [Start Now]

✅ Threshold reached! Starting game...

🌊 The wind dies completely... the ocean becomes unnaturally still. 
Sea Kings sense weakness below the surface.

📍 Current Condition: 🌊 Calm Belt
Eerie stillness falls over the Grand Line - Sea Kings lurk below

🎺 LET THE GAMES BEGIN! 🎺
8 tributes enter the arena!

👥 THE TRIBUTES
🏹 Luffy the Ambitious - The Neon Metropolis
🏹 Zoro the Deadly - The Frozen Wasteland  
🏹 Nami the Clever - The Floating Islands
🏹 Sanji the Swift - The Underground Caverns
🏹 Robin the Wise - The Savage Jungle
🏹 Franky the Strong - The Desert Oasis
🏹 Brook the Silent - The Sky Fortress
🏹 Jinbe the Noble - The Sunken City

🌊 ROUND 1 - GRAND LINE CHAOS 🌊

⚔️ THE PIRATE BATTLE BEGINS! Pirates scramble for weapons 
and Devil Fruits as the chaos erupts!

In the deadly silence of the Calm Belt, Luffy the Ambitious 
pushed ~~Zoro the Deadly~~ into the waters where massive 
Sea Kings devoured them instantly!

🏴‍☠️ Nami the Clever discovered a buried treasure chest on the beach!

👑 PIRATE KING OF THE GRAND LINE 👑
Luffy the Ambitious has conquered the Grand Line!

🎊 Victory Moment: 🏆 WINNER!
📊 Final Stats: 3 eliminations, 1 revival, District 1, 8 rounds survived
```

### 📊 **Example Commands**

```bash
# Starting games
User: [p]he 120
Bot: 🏹 THE HUNGER GAMES 🏹
     A deadly battle royale is about to begin!
     React with 🏹 to enter the arena!

# Checking stats  
User: [p]hg stats @Luffy
Bot: 📊 Luffy's Hunger Games Stats
     🏆 Victories: 15
     ⚔️ Total Kills: 47  
     📈 Win Rate: 78.9%
     🎭 Rank: 🌟 Legendary Champion

# Server leaderboard
User: [p]hg leaderboard kills
Bot: ⚔️ Kill Leaderboard
     🥇 Luffy - 47 kills (K/D: 2.35)
     🥈 Zoro - 38 kills (K/D: 1.90)
     🥉 Sanji - 29 kills (K/D: 1.45)

# Arena conditions
User: [p]hg condition info  
Bot: 🌊 CURRENT ARENA CONDITION 🌊
     📍 Condition: 🌊 Calm Belt
     ⏰ Duration: 3 rounds remaining
     📝 Description: Eerie stillness falls over the Grand Line
     ⚡ Active Effects:
     • Sea King Events: +40%
     • Devil Fruit Weakness: +20%
```

## 🔧 Troubleshooting

### ❓ **Common Issues**

**Q: The bot doesn't respond to commands**
- Ensure the cog is loaded: `[p]load hg`
- Check bot permissions: Send Messages, Embed Links, Add Reactions
- Verify command prefix: `[p]help hungergames`

**Q: Players can't join games**
- Check for role blacklists: `[p]hg config`
- Verify user isn't temp-banned: `[p]hg set tempban @user remove`
- Ensure reactions are working on the recruitment message

**Q: Games end immediately**
- Check for minimum 2 players before starting
- Verify no errors in bot console/logs
- Try `[p]hg debug` for diagnostic info

**Q: Arena conditions not showing**
- Conditions were added in recent update - may need cog reload
- Check `[p]hg condition list` to verify system is working
- Use `[p]hg condition test` to force test conditions

**Q: Poll system not working**
- Ensure poll threshold is set: `[p]hg set pollthreshold 5`
- Check button interactions are enabled for the bot
- Verify users have permission to use application commands

### 🐛 **Error Reporting**

If you encounter bugs:
1. Check Red's console for error messages
2. Try `[p]hg debug` for diagnostic information
3. Report issues with full error logs and reproduction steps
4. Include your Red version and any other relevant cogs

### 🔄 **Updates**

To update the cog:
```bash
[p]repo update ultcogs
[p]cog update hg
[p]reload hg
```

## 🛠️ **Advanced Setup**

### 🖼️ **Custom Images (Optional)**
Enable custom round display images:
1. Place template image at: `[datadir]/cogs/hg/Images/eventsmockup.png`
2. Images will overlay round numbers, events, and player counts
3. Use `[p]hg debug` to verify image system status

### 🎞️ **GIF Integration (Optional)**
Add animated GIFs for enhanced experience:
1. Create directory structure: `[datadir]/cogs/hg/gifs/`
2. Organize GIFs by category: `victory/`, `death/`, `sponsor/`, etc.
3. System auto-selects appropriate GIFs based on context

### 📱 **Discord Integration**
- **Rich Presence**: Shows current game status
- **Button Interactions**: Modern poll system with buttons
- **Embed Formatting**: Beautiful, themed message displays
- **Reaction Monitoring**: Real-time join/leave tracking

## 🏴‍☠️ **Themed Content**

This cog features **One Piece** themed content throughout:

### 🌊 **World Building**
- **Grand Line** setting with authentic weather
- **Marine** interference and World Government presence
- **Devil Fruit** powers and weaknesses
- **Sea Kings** and oceanic dangers
- **Pirate crews** and legendary battles

### ⚔️ **Events & Flavor**
- **200+ unique death events** with pirate themes
- **Sea-based survival** scenarios
- **Treasure hunting** and supply gathering
- **Crew alliances** and betrayals
- **Epic final battles** for the Pirate King title

### 🏆 **Terminology**
- Players are **"Pirates"** and **"Tributes"**
- Winners become the **"Pirate King"**
- Deaths are **"eliminations"** by sea creatures, Marines, etc.
- Districts represent different **islands** and **regions**

## 📞 Support

### 🔗 **Links**
- **GitHub Repository**: https://github.com/AfterWorld/ultcogs
- **Red-DiscordBot**: https://github.com/Cog-Creators/Red-DiscordBot
- **Discord Server**: [Join our support server](https://discord.gg/onepiececommunity)

### 💬 **Getting Help**
- Check this README first for common solutions
- Use `[p]help hungergames` for command-specific help
- Join our Discord server for live support
- Report bugs on GitHub with detailed reproduction steps

### 🤝 **Contributing**
We welcome contributions! Feel free to:
- Submit bug reports and feature requests
- Create pull requests for improvements  
- Suggest new arena conditions or events
- Help with documentation and examples

---

## 📜 **Credits**

**Original Creator**: UltPanda  
**Theme**: One Piece by Eiichiro Oda  
**Platform**: Red-DiscordBot Framework  
**Version**: 2.1.0 with Arena Conditions  

*May the odds be ever in your favor on the Grand Line! 🏴‍☠️*
