
# README.md content for the cog
# Buckshot Cog

A comprehensive strategic Russian Roulette-style game cog for Red-DiscordBot featuring intense 1v1 multiplayer matches with strategic item usage.

## Features

### 🎯 Core Gameplay
- **Strategic Russian Roulette**: Players take turns with a shotgun containing live and blank bullets
- **Item System**: 5 unique items that can completely change the game's outcome
- **Smart Turn Logic**: Shooting yourself with a blank lets you keep your turn
- **Dynamic Chamber**: Each round has 4-8 randomly generated bullets

### 🎒 Items
- **🥫 Skip**: Discard the current bullet without firing
- **🔍 Magnifier**: Reveal what the next bullet is
- **🧤 Gloves**: Skip your opponent's next turn
- **🪚 Saw**: Next live bullet deals 2 damage instead of 1
- **🍾 Beer**: Heal 1 heart (maximum 5 hearts)

### 📊 Statistics & Progression
- Comprehensive player statistics tracking
- Server leaderboards with win rates
- Global statistics for bot owners
- Achievement-style progression tracking

### ⚙️ Admin Controls
- Enable/disable per server
- Channel restrictions
- User banning system
- Game management tools
- Configurable timeouts

### 🎮 User Experience
- Beautiful embedded displays
- Real-time game status updates
- Intuitive reaction-based controls
- Comprehensive help system
- Spectator-friendly interface

## Commands

### Player Commands
- `[p]buckshot challenge @user` - Challenge someone to a game
- `[p]buckshot shoot` - Fire the gun (choose target)
- `[p]buckshot item <item>` - Use an item strategically
- `[p]buckshot status` - View current game state
- `[p]buckshot surrender` - Give up the current game
- `[p]buckshot stats [@user]` - View statistics
- `[p]buckshot leaderboard` - Server leaderboard
- `[p]buckshot rules` - Complete game rules

### Admin Commands
- `[p]buckshot admin enable/disable` - Toggle Buckshot
- `[p]buckshot admin setchannel/removechannel` - Manage allowed channels
- `[p]buckshot admin ban/unban` - Manage user access
- `[p]buckshot admin endgame` - Force end games
- `[p]buckshot admin config` - View configuration
- `[p]buckshot admin resetstats` - Reset user stats

### Owner Commands
- `[p]buckshot global settimeout` - Set game timeout
- `[p]buckshot global setmaxgames` - Set max games per channel
- `[p]buckshot global stats` - Global statistics

## Installation

1. Add the cog to your Red instance:
   ```
   [p]repo add ultcogs https://github.com/AfterWorld/ultcogs
   [p]cog install ultcogs buckshot
   [p]load buckshot
   ```

2. Configure permissions (optional):
   ```
   [p]buckshot admin setchannel #games
   ```

3. Start playing:
   ```
   [p]buckshot challenge @friend
   ```

## Game Strategy Tips

1. **Use the Magnifier wisely** - Knowing the next bullet can save your life
2. **Save healing items** - Beer is most valuable when you're low on health
3. **Saw timing is crucial** - Only use it when you're confident about a live bullet
4. **Gloves for momentum** - Skip opponent turns when you have good information
5. **Risk vs Reward** - Shooting yourself with blanks keeps your turn but is risky

## Technical Details

- **Performance Optimized**: Efficient memory usage and async operations
- **Error Handling**: Comprehensive error handling and recovery
- **Data Persistence**: Uses Red's Config API for reliable data storage
- **Scalability**: Supports multiple concurrent games across servers
- **Security**: Input validation and permission checks throughout

## Support

For issues, suggestions, or contributions, please visit the [UltCogs Repository](https://github.com/AfterWorld/ultcogs).

---

*Made with ❤️ by UltPanda*