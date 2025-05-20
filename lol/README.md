# League of Legends Discord Bot

A comprehensive League of Legends integration for Red-DiscordBot using the official Riot Games API with intelligent endpoint-specific rate limiting and enhanced visual features.

## 🚀 Features

### Player Data
- **Enhanced Summoner Lookup**: Detailed information with emojis, rank colors, and visual indicators
- **Champion Mastery**: Top champion masteries with scores and last played dates
- **Match History**: Recent match history with enhanced KDA displays, damage stats, and items
- **Live Games**: Check if a summoner is currently in a live game with detailed match info
- **Detailed Ranks**: Comprehensive ranked information with win rates, streaks, and special status indicators
- **Performance Analysis**: Deep analysis of summoner performance over last 20 games
- **Summoner Comparison**: Compare stats and performance between two summoners

### Champion & Game Data
- **Champion Info**: Detailed champion information with splash art, stats, abilities, and lore
- **Champion Rotations**: Current free champion rotations for all players and new players
- **Enhanced Visual Embeds**: Rich embeds with custom emojis, progress bars, and role indicators

### Monitoring Features
- **Live Game Notifications**: Get notified when monitored summoners start/end games
- **Multi-Summoner Monitoring**: Monitor multiple summoners across different channels
- **Persistent Monitoring**: Database-backed monitoring that persists across bot restarts

### Account Management
- **Account Linking**: Link Discord accounts to League summoners for quick access
- **Lookup History**: Track your recent summoner lookups
- **User Preferences**: Customizable settings per user

### General Features
- **Multi-Region Support**: Support for all League of Legends regions
- **Intelligent Rate Limiting**: Endpoint-specific rate limiting ensuring optimal API usage
- **Smart Caching**: Reduce API calls with intelligent caching system
- **Usage Statistics**: Track API usage, cache performance, and command statistics

### Quick Commands for Linked Accounts
- `[p]lol me` - Your enhanced profile
- `[p]lol mymastery` - Your champion mastery
- `[p]lol mymatches` - Your match history

## 📦 Installation

1. **Install the cog:**
   ```bash
   [p]repo add ultcogs https://github.com/AfterWorld/ultcogs
   [p]cog install ultcogs lol
   [p]load lol
   ```

2. **Get a Riot Games API key** from [developer.riotgames.com](https://developer.riotgames.com/)

3. **Set your API key** (bot owner only):
   ```bash
   [p]lolset apikey <your_api_key>
   ```

4. **Test the API connection:**
   ```bash
   [p]lolset testapi
   ```

5. **Set a default region** for your server:
   ```bash
   [p]lolset region na
   ```

## 📋 Commands

### 👤 Player Commands

| Command | Description |
|---------|-------------|
| `[p]lol summoner <region> <summoner#tag>` | Enhanced summoner profile with visual indicators |
| `[p]lol rank <region> <summoner#tag>` | Detailed rank information with streaks |
| `[p]lol mastery <region> <summoner#tag>` | Champion mastery with visual progress |
| `[p]lol matches <region> <summoner#tag>` | Enhanced match history with detailed stats |
| `[p]lol live <region> <summoner#tag>` | Check if in a live game with match details |
| `[p]lol analyze <region> <summoner#tag>` | Deep performance analysis (20 games) |
| `[p]lol compare <summoner1> <summoner2> [region]` | Compare two summoners side by side |

### 🎮 Champion & Game Data

| Command | Description |
|---------|-------------|
| `[p]lol champion <champion_name>` | Detailed champion info with splash art |
| `[p]lol rotations [region]` | Current free champion rotations |

### 🔔 Monitoring Commands

| Command | Description |
|---------|-------------|
| `[p]lol notify <region> <summoner#tag>` | Monitor summoner for live games |
| `[p]lol unnotify <region> <summoner#tag>` | Stop monitoring summoner |
| `[p]lol monitored` | List all monitored summoners in server |

### 🔗 Account Management

| Command | Description |
|---------|-------------|
| `[p]lol link <region> <summoner#tag>` | Link your Discord account |
| `[p]lol unlink` | Unlink your account |
| `[p]lol me` | Your linked profile (enhanced) |
| `[p]lol mymastery` | Your champion mastery |
| `[p]lol mymatches` | Your match history |
| `[p]lol history` | Your recent summoner lookups |

### 🌐 General Commands

| Command | Description |
|---------|-------------|
| `[p]lol status` | Check rate limit status |
| `[p]lol usage` | Show bot usage statistics (owner only) |

### ⚙️ Admin Commands

| Command | Description |
|---------|-------------|
| `[p]lolset apikey <key>` | Set the Riot API key (owner only) |
| `[p]lolset region <region>` | Set default region for the server |
| `[p]lolset settings` | Show current settings | # Instead of info
| `[p]lolset testapi` | Test API connection (owner only) |
| `[p]lolset ratelimits` | Show all endpoint rate limits |
| `[p]lolset clearcache` | Clear all cached data (owner only) |
| `[p]lolset cleanup` | Clean up old database entries (owner only) |
| `[p]lolset backup` | Create database backup (owner only) |
| `[p]lolset monitor` | Show monitoring system status (owner only) |
| `[p]lolset version` | Show cog version and information |

## 🎨 Visual Enhancements

### Enhanced Embeds
- **Custom Rank Emojis**: Each rank tier has its own emoji (🥉 Iron, 🏆 Challenger)
- **Color-Coded Displays**: Embed colors change based on highest rank
- **Win Rate Indicators**: Visual indicators (🟢 Good, 🟡 Average, 🔴 Poor)
- **Status Indicators**: Hot streaks 🔥, Veteran status ⭐, Inactivity 💤

### Champion Features
- **Role Emojis**: Each champion role has a unique emoji (⚔️ Fighter, 🔮 Mage)
- **Difficulty Bars**: Visual progress bars showing champion difficulty
- **Splash Art**: Full champion splash art in embeds
- **Enhanced Stats**: Detailed stat displays with emojis and formatting

### Match Display
- **Win/Loss Colors**: Green for victories, red for defeats
- **Enhanced KDA**: Highlighted kills/assists with ratios
- **Game Mode Icons**: Unique icons for different game modes
- **Performance Metrics**: Damage, vision score, and items shown

## 🚦 Rate Limiting

This cog implements intelligent endpoint-specific rate limiting based on Riot's official API limits:

### Endpoint-Specific Limits
- **Summoner API**: 1,600 requests per minute
- **Account API**: 1,000/minute + 20,000/10s + 1,200,000/10min
- **Match API**: 2,000 requests per 10 seconds
- **Champion Mastery**: 20,000/10s + 1,200,000/10min
- **Champion Rotations**: 30/10s + 500/10min
- **League Entries**: 100 requests per minute
- **Status API**: 20,000/10s + 1,200,000/10min
- **Clash API**: Various limits for teams, tournaments, and players

> 💡 The rate limiter automatically manages these limits to ensure your API key never gets rate limited.

## 🌍 Supported Regions

| Region Code | Region Name |
|-------------|-------------|
| `na` | North America |
| `euw` | Europe West |
| `eune` | Europe Nordic & East |
| `kr` | Korea |
| `br` | Brazil |
| `jp` | Japan |
| `ru` | Russia |
| `oc` | Oceania |
| `tr` | Turkey |
| `lan` | Latin America North |
| `las` | Latin America South |
| `me` | Middle East |
| `sg` | Singapore |
| `tw` | Taiwan |
| `vn` | Vietnam |

## 🔔 Monitoring System

### Live Game Notifications
- **Real-time Monitoring**: Checks every 5 minutes for game status changes
- **Game Start Alerts**: Notifications when monitored summoners start games
- **Game End Alerts**: Notifications when games finish
- **Multi-Channel Support**: Different channels can monitor different summoners
- **Persistent Storage**: Monitoring settings survive bot restarts

## 💾 Data Management

### Database Features
- **SQLite Storage**: Lightweight, persistent data storage
- **Match Caching**: Cache match data to reduce API calls (24-hour TTL)
- **User Preferences**: Store linked accounts and user settings
- **Lookup History**: Track summoner lookup history per user
- **Monitoring Data**: Persistent summoner monitoring across restarts

### Cache System
- **Smart Caching**: Multiple cache layers (5min general, 1hour champions)
- **Cache Statistics**: Track hit/miss ratios for performance monitoring
- **Automatic Cleanup**: Expired cache entries are automatically removed

## ⚠️ Error Handling

The cog includes comprehensive error handling for:
- ❌ Invalid summoner names with helpful suggestions
- 🕒 API rate limits with automatic retry mechanisms
- 🌐 Network issues with graceful degradation
- 🗺️ Invalid regions with list of valid options
- 🔑 Missing API keys with setup instructions
- 📊 API errors with user-friendly messages

## 🔒 Privacy & Security

- 🔐 API keys are automatically deleted from chat after being set
- 💾 User data is stored securely in Red's config system
- 📋 GDPR compliance with automatic data deletion (`[p]mydatafor` support)
- 🔓 Users can unlink their accounts at any time
- 🗄️ Database connections are properly managed and secured

## 🏗️ Architecture

### Modular Design
The cog uses a modular architecture for better maintainability:

- **core.py**: Main cog class with dependency injection
- **api.py**: Riot API manager with intelligent rate limiting
- **embeds.py**: Discord embed factory for visual consistency
- **notifications.py**: Live game monitoring system
- **database.py**: SQLite operations with async handling
- **commands.py**: User command implementations
- **settings.py**: Admin commands and configuration
- **errors.py**: Centralized error handling
- **constants.py**: Configuration and constants

### Performance Features
- **Parallel API Processing**: Batched requests for match analysis
- **Multi-layer Caching**: Memory + database caching
- **Async Database Operations**: Non-blocking SQLite operations
- **Intelligent Rate Limiting**: Per-endpoint limit management

## 📋 Requirements

- ![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
- ![Red-DiscordBot](https://img.shields.io/badge/Red--DiscordBot-3.5.0+-red)
- ![aiohttp](https://img.shields.io/badge/aiohttp-library-green)
- ![aiosqlite](https://img.shields.io/badge/aiosqlite-library-blue)
- ![Riot API Key](https://img.shields.io/badge/Riot%20API-Key%20Required-orange)

## 🤝 Support

For issues, feature requests, or questions:
- 🐛 [Open an issue](https://github.com/AfterWorld/ultcogs/issues)
- 💬 Join the Red-DiscordBot support server
- 📖 Check the [Red-DiscordBot documentation](https://docs.discord.red/)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Riot Games](https://www.riotgames.com/) for providing the League of Legends API
- [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) community for the framework
- All contributors and users of this cog

---

<div align="center">

**Made with ❤️ for the League of Legends community**

[![GitHub stars](https://img.shields.io/github/stars/Afterworld/ultcogs?style=social)](https://github.com/Afterworld/ultcogs/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Afterworld/ultcogs?style=social)](https://github.com/Afterworld/ultcogs/network/members)

</div>
