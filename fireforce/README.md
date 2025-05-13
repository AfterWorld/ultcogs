# Fire Force

A Discord Red Bot cog that implements a complete RPG game system inspired by the Fire Force anime/manga series.

## Overview

Fire Force is a game system where users create characters with pyrokinetic abilities, join fire fighting companies, and battle against infernals (fire demons). The game features:

- Character creation with random abilities and stats
- Turn-based combat system with cooldowns
- PvP battles between players
- Server-wide events and cooperative missions
- Character progression through experience and levels
- Squadron system for team identity
- Leaderboards and competitive gameplay

## Installation

To install this cog, you need a running instance of [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) V3.5 or later.

```
[p]repo add fireforce https://github.com/AfterWorld/ultcogs
[p]cog install fireforce fireforce
[p]load fireforce
```

Note: The Pillow library is required for creating visual elements:
```
pip install Pillow
```

## Commands

### User Commands

| Command | Description |
| ------- | ----------- |
| `[p]fireforce create <name>` | Create a new Fire Force character |
| `[p]fireforce info [user]` | Display character information |
| `[p]fireforce battle` | Battle against a randomly generated Infernal |
| `[p]fireforce pvp <user>` | Challenge another player to a PvP battle |
| `[p]fireforce squadron [number]` | View information about your squadron or a specific squadron |
| `[p]fireforce engage` | Battle against a server-wide Infernal event |
| `[p]fireforce tutorial` | View a tutorial on how to play |
| `[p]fireforce leaderboard` | View the server's leaderboard |

### Event Commands

| Command | Description |
| ------- | ----------- |
| `[p]fireforce summon` | Summon a powerful Infernal for everyone to fight (1-hour cooldown) |
| `[p]fireforce squad` | Start a squadron mission for all members (24-hour guild cooldown) |
| `[p]fireforce status` | Check the status of active Infernals and server events |

### Admin Commands

| Command | Description |
| ------- | ----------- |
| `[p]fireforce reset [user]` | Reset a user's character data (Owner only) |

## Game Mechanics

### Character System

Characters are created with random:
- Squadron assignment (1-8)
- Ability tier (Common to Secret)
- Starting abilities (1-3 based on tier)
- Base stats influenced by tier and squadron

### Ability Tiers

- **Common** (50% chance): Basic fire abilities
- **Uncommon** (30% chance): Improved fire control
- **Rare** (15% chance): Advanced pyrokinesis
- **Epic** (4% chance): Powerful flame techniques
- **Legendary** (1% chance): Extraordinary abilities
- **Secret** (0.1% chance): Unique powers like Adolla Burst

### Combat System

Battles are turn-based with reaction controls:
1. Player selects an ability by reacting with a number
2. Ability damage is calculated based on stats
3. Special ability effects are applied
4. Opponent (Infernal or player) takes their turn
5. Battle continues until one side is defeated

### Progression System

- Experience is awarded after winning battles
- Higher-level opponents grant more experience
- Experience needed for level-up increases with each level
- Stats improve automatically on level-up
- Defeating higher-level opponents grants bonus experience

### Server Events

- **Infernal Summon**: Creates a server-wide event where multiple players can battle the same powerful Infernal
- **Squadron Missions**: Cooperative events where all players work together for rewards

## Customization

Server admins can consider customizing aspects of the game by modifying the code:
- Adjust ability rarities and power levels
- Modify squadron bonuses
- Add custom boss encounters
- Create new types of missions

## Acknowledgements

This cog is inspired by the Fire Force (En'en no Shouboutai) anime/manga created by Atsushi Ōkubo.

## Feedback and Support

For issues, suggestions, or feedback, please open an issue in the repository or contact the developer.

## License

This cog is licensed under the MIT License.
