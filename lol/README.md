A comprehensive League of Legends integration for Red-DiscordBot using the official Riot Games API with intelligent endpoint-specific rate limiting.

## 🚀 Features

### Player Data
- **Summoner Lookup**: Get detailed information about any summoner including rank, level, and stats
- **Champion Mastery**: View top champion masteries with scores and last played dates
- **Match History**: Recent match history with KDA, champions played, and results
- **Live Games**: Check if a summoner is currently in a live game
- **Detailed Ranks**: Comprehensive ranked information with win rates and streaks

### General Features
- **Champion Rotations**: Check current free champion rotations
- **Account Linking**: Link Discord accounts to League summoners for quick access
- **Multi-Region Support**: Support for all League of Legends regions
- **Intelligent Rate Limiting**: Endpoint-specific rate limiting ensuring optimal API usage

### Quick Commands for Linked Accounts
- `[p]lol me` - Your profile
- `[p]lol mymastery` - Your champion mastery
- `[p]lol mymatches` - Your match history

## 📦 Installation

1. **Install the cog:**
   ```bash
   [p]repo add mylol-repo https://github.com/AfterWorld/ultcogs
   [p]cog install mylol-repo lol
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
| `[p]lol summoner <region> <summoner#tag>` | Look up a summoner's profile |
| `[p]lol rank <region> <summoner#tag>` | Detailed rank information |
| `[p]lol mastery <region> <summoner#tag>` | Champion mastery data |
| `[p]lol matches <region> <summoner#tag>` | Recent match history |
| `[p]lol live <region> <summoner#tag>` | Check if in a live game |

### 🌐 General Commands

| Command | Description |
|---------|-------------|
| `[p]lol rotations [region]` | Current champion rotations |
| `[p]lol status` | Check rate limit status |

### 🔗 Account Management

| Command | Description |
|---------|-------------|
| `[p]lol link <region> <summoner#tag>` | Link your Discord account |
| `[p]lol unlink` | Unlink your account |
| `[p]lol me` | Your linked profile |
| `[p]lol mymastery` | Your champion mastery |
| `[p]lol mymatches` | Your match history |

### ⚙️ Admin Commands

| Command | Description |
|---------|-------------|
| `[p]lolset apikey <key>` | Set the Riot API key (owner only) |
| `[p]lolset region <region>` | Set default region for the server |
| `[p]lolset info` | Show current settings |
| `[p]lolset testapi` | Test API connection (owner only) |
| `[p]lolset ratelimits` | Show all endpoint rate limits |

## 🚦 Rate Limiting

This cog implements intelligent endpoint-specific rate limiting based on Riot's official API limits:

- **Summoner API**: 1,600 requests per minute
- **Match API**: 2,000 requests per 10 seconds
- **Account API**: 1,000 requests per minute + 20,000 requests per 10 seconds
- **Champion Rotations**: 30 requests per 10 seconds
- And many more...

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

## ⚠️ Error Handling

The cog includes comprehensive error handling for:
- ❌ Invalid summoner names
- 🕒 API rate limits
- 🌐 Network issues
- 🗺️ Invalid regions
- 🔑 Missing API keys

## 🔒 Privacy & Security

- 🔐 API keys are automatically deleted from chat after being set
- 💾 User data is stored securely in Red's config system
- 📋 GDPR compliance with automatic data deletion
- 🔓 Users can unlink their accounts at any time

## 📋 Requirements

- ![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
- ![Red-DiscordBot](https://img.shields.io/badge/Red--DiscordBot-3.5.0+-red)
- ![aiohttp](https://img.shields.io/badge/aiohttp-library-green)
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

<div align=\"center\">

**Made with ❤️ for the League of Legends community**

[![GitHub stars](https://img.shields.io/github/stars/Afterworld/ultcogs?style=social)](https://github.com/Afterworld/ultcogs/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Afterworld/ultcogs?style=social)](https://github.com/Afterworld/ultcogs/network/members)
