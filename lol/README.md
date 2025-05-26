# 🎮 Advanced League of Legends Cog

> **The most comprehensive League of Legends integration for Red-DiscordBot**

[![Red-DiscordBot](https://img.shields.io/badge/Red--DiscordBot-V3.4+-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![League of Legends](https://img.shields.io/badge/League%20of%20Legends-API%20v5-gold.svg)](https://developer.riotgames.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Transform your Discord server into a **professional-grade League of Legends community hub** with advanced analytics, real-time monitoring, achievement systems, and seamless League Client integration.

---

## ✨ Features Overview

### 🧠 **Advanced Analytics Engine**
- **Real-time win probability calculations** with 15+ analytical factors
- **Team composition analysis** (scaling, synergies, damage distribution)
- **Game phase intelligence** with strategic insights
- **Champion meta strength** integration
- **Objective control predictions**

### 🏆 **Community Engagement System**
- **25+ achievements** across 6 rarity tiers (Common → Mythic)
- **Server leaderboards** with multiple competitive statistics
- **User progression** with levels, XP, and point systems
- **Achievement tracking** with automatic detection and rewards
- **Community challenges** and seasonal events

### 🎨 **Professional Discord Integration**
- **5 customizable themes** (Gaming, Dark, Light, Professional, Default)
- **Interactive embeds** with reaction-based navigation
- **Visual progress bars** and performance indicators
- **Color-coded displays** with role emojis and rank styling
- **Paginated content** for complex data presentation

### 🔗 **League Client (LCU) Integration**
- **Auto-accept matchmaking queue** when away from computer
- **Real-time champion select monitoring** with suggestions
- **Live game state tracking** and notifications
- **WebSocket event handling** for instant updates
- **Secure local-only connection** with no external data transmission

---

## 📦 Installation

### Prerequisites
- **Red-DiscordBot v3.4.0+** installed and configured
- **Python 3.8+** with pip
- **Riot Games API Key** ([Get one here](https://developer.riotgames.com/))
- **League of Legends** installed (optional, for LCU features)

### Quick Installation

1. **Download the cog:**
   ```bash
   # Method 1: Direct download
   [p]repo add advanced-lol https://github.com/AfterWorld/ultcogs/tree/main/lol
   [p]cog install advanced-lol AdvancedLoL
   
   # Method 2: Manual installation
   # Place all files in: [botdir]/cogs/AdvancedLoL/
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Load the cog:**
   ```bash
   [p]load AdvancedLoL
   ```

4. **Configure API key:**
   ```bash
   [p]lol setkey RGAPI-your-api-key-here
   ```

### File Structure
```
AdvancedLoL/
├── __init__.py           # Package initializer
├── advancedlol.py        # Main cog file
├── analytics.py          # Analytics engine
├── lcu_client.py         # League Client integration
├── community.py          # Community features
├── embeds.py            # Enhanced embed builder
├── requirements.txt      # Dependencies
├── info.json            # Cog metadata
└── README.md            # This file
```

---

## ⚙️ Configuration

### 🔑 **API Key Setup**
1. Visit [Riot Developer Portal](https://developer.riotgames.com/)
2. Create an account and generate a **Personal API Key**
3. Set the key using: `[p]lol setkey RGAPI-your-key-here`

> **⚠️ Important:** Personal API keys expire every 24 hours. For production use, apply for a production key.

### 🎨 **Theme Configuration**
```bash
# Available themes: gaming, dark, light, professional, default
[p]lol theme gaming

# Preview current theme
[p]lol theme
```

### 📺 **Server Setup (Moderators)**
```bash
# Set up live game notifications channel
[p]lol setup #league-live-games

# Start monitoring specific players
[p]lol monitor "Faker" kr
[p]lol monitor "Doublelift" na

# Configure auto-update interval (default: 30 seconds)
[p]set guild lol auto_update_interval 60
```

---

## 🚀 Usage Guide

### 📊 **Core Commands**

#### **Player Profiles**
```bash
# Enhanced summoner profiles with analytics
[p]lol profile "Riot Phreak" na
[p]lol p "Faker" kr
[p]lol summoner "G2 Caps" euw

# Aliases: profile, summoner, p
```

**Example Output:**
```
🎮 Riot Phreak
📊 Profile Info                🏆 Ranked Status
Level: 523                     💎 Solo/Duo Queue
Region: NA                     ├ Diamond III (67 LP)
Account: abc123def...          └ 156W / 144L (52.0%)

⭐ Champion Mastery
💜 1. Jinx ⚔️
├ Level 7
└ 234,567 mastery points
```

#### **Live Game Analysis**
```bash
# Advanced live game monitoring with win probability
[p]lol live "TSM Bjergsen" na
[p]lol current "Faker" kr
[p]lol spectate "Doublelift" na

# Aliases: live, current, spectate, l
```

**Features:**
- 🎯 **Real-time win probability** (Blue 67.3% vs Red 32.7%)
- 📈 **Game phase analysis** (Early/Mid/Late game insights)
- ⚔️ **Team composition breakdown** (scaling, synergies, weaknesses)
- 🏆 **Player performance indicators** based on recent history
- 📊 **Interactive navigation** with detailed statistics

#### **Match History**
```bash
# Enhanced match analysis
[p]lol matches "Summoner Name" na 5
[p]lol history "Player" euw 10

# Shows: KDA, performance ratings, builds, achievements
```

### 🏆 **Community Features**

#### **Your Profile**
```bash
# View your community profile and achievements
[p]lol community profile
[p]lol c me

# View another user's profile
[p]lol community profile @username
```

**Profile Includes:**
- 📊 **Progress tracking** (Level, Points, Achievements)
- 🎯 **League information** (Summoner, Region, Main champion)
- 🏅 **Recent achievements** with timestamps
- 📅 **Activity timeline** and statistics

#### **Server Leaderboards**
```bash
# Various leaderboard types
[p]lol community leaderboard total_points
[p]lol c lb live_games_checked
[p]lol c top matches_analyzed

# Available stats: total_points, live_games_checked, 
# matches_analyzed, profiles_checked, achievements_count
```

#### **Achievement System**
```bash
# View achievement progress
[p]lol community achievements
[p]lol c progress

# Check another user's achievements
[p]lol c achievements @username
```

**Achievement Categories:**
- 🎮 **Profile & Setup** - First Steps, Region Explorer, Summoner Sleuth
- 🔴 **Live Games** - Live Game Hunter, Spectator Supreme, Challenger Spotter
- 📊 **Match Analysis** - Match Analyst, Pentakill Witness, Perfect Game Finder
- 👥 **Community** - Helpful Member, Community Leader, Knowledge Sharer
- ⭐ **Special** - Early Adopter, Dedication, Night Owl, Weekend Warrior
- 🎯 **Advanced** - Meta Observer, Trend Setter, Data Enthusiast

### 🔗 **League Client Integration**

#### **Setup & Connection**
```bash
# Connect to your local League Client
[p]lol lcu connect

# Check connection status
[p]lol lcu status

# Enable auto-accept feature
[p]lol lcu autoaccept
```

**LCU Features:**
- ⚡ **Auto-accept queue** when away from computer
- 🎯 **Champion select monitoring** with real-time updates
- 📱 **Discord notifications** when queue pops
- 🔄 **Automatic reconnection** if League restarts
- 🛡️ **Secure local connection** (no external data sharing)

**Requirements:**
- League of Legends must be running
- Bot and League on same computer
- Windows/Mac/Linux supported

---

## 📚 Command Reference

### **Core Commands**
| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `profile` | `summoner`, `p` | Enhanced summoner profile | `[p]lol p "Faker" kr` |
| `live` | `current`, `spectate`, `l` | Live game analysis | `[p]lol live "Doublelift" na` |
| `matches` | `history`, `match` | Match history analysis | `[p]lol matches "Player" euw 5` |
| `rank` | `ranked` | Detailed rank information | `[p]lol rank "Summoner" na` |

### **Community Commands**
| Command | Aliases | Description | Access |
|---------|---------|-------------|--------|
| `community profile` | `c me` | Your community profile | Everyone |
| `community leaderboard` | `c lb` | Server leaderboards | Everyone |
| `community achievements` | `c progress` | Achievement tracking | Everyone |
| `community stats` | `c stats` | Detailed statistics | Everyone |

### **LCU Commands**
| Command | Description | Requirements |
|---------|-------------|--------------|
| `lcu connect` | Connect to League Client | League running |
| `lcu status` | Connection status | - |
| `lcu autoaccept` | Toggle auto-accept | Connected |
| `lcu disconnect` | Disconnect from client | Connected |

### **Admin Commands**
| Command | Description | Permission |
|---------|-------------|------------|
| `setkey` | Set Riot API key | Bot Owner |
| `setup` | Configure live channel | Manage Guild |
| `monitor` | Monitor summoner | Manage Guild |
| `theme` | Change embed theme | Manage Guild |

---

## 🛠️ Advanced Configuration

### **Environment Variables**
```bash
# Optional: Set default region
export LOL_DEFAULT_REGION=na

# Optional: Enable debug logging
export LOL_DEBUG=true

# Optional: Custom champion icons URL
export LOL_CHAMPION_ICONS_URL=https://your-cdn.com/icons/
```

### **Database Configuration**
The cog automatically creates and manages SQLite databases:
- `community.db` - User profiles, achievements, statistics
- Auto-backup and migration included

### **Performance Tuning**
```python
# In Red's config (advanced users)
[p]set global lol rate_limit_buffer 2.0
[p]set global lol cache_duration 300
[p]set global lol max_concurrent_requests 5
```

### **Custom Champion Icons**
Place custom icons in the repository structure:
```
championicons/
├── 1.png     # Annie
├── 2.png     # Olaf
├── 3.png     # Galio
└── ...
```

---

## 🎯 Usage Examples

### **Live Game Scenario**
```
User: [p]lol live "Faker" kr

Bot Response:
🔴 Live Game Analysis - Ranked Solo/Duo
⏱️ Duration: 23m 45s
🌙 Game Phase: Late Game

📊 Win Probability
🔵 Blue Team: 67.3% ████████████████████░░
🔴 Red Team: 32.7%  ████████████░░░░░░░░░░

🔵 Blue Team - 67.3% Win Rate
🌳 Scaling: Late Game
⚔️ Engage: ⭐⭐⭐⭐⭐ (8/10)
🛡️ Peel: ⭐⭐⭐⭐ (7/10)

🔥 Yasuo ⚔️        💎 Challenger 1,891 LP
TSM Bjergsen       Mid Lane Legend
Recent: 8W-2L      Champion WR: 73.5%

[Achievement Unlocked!]
🎉 Challenger Spotter (+100 points)
```

### **Community Profile**
```
User: [p]lol community profile

Bot Response:
🎮 Username's Community Profile

📊 Progress                 🎯 League Info
Level: 15                   Summoner: Faker (KR)
Total Points: 2,450         Main: Yasuo
Achievements: 12            Rank: Diamond II

🏅 Recent Achievements (5)
💎 Challenger Spotter (2d ago)
⭐ Pentakill Witness (1w ago)
📊 Match Analyst (2w ago)
🔴 Live Game Hunter (3w ago)
🎮 First Steps (1m ago)

📅 Activity
Joined: Nov 15, 2024
Last Active: Dec 20, 2024
```

---

## 🔧 Troubleshooting

### **Common Issues**

#### **"Summoner not found" Error**
```bash
# Possible causes and solutions:
1. Check spelling and region
2. Include Riot ID tag: "Summoner#TAG"
3. Verify summoner exists on op.gg
4. Try different region codes (na, euw, kr, etc.)
```

#### **API Key Issues**
```bash
# Symptoms: API errors, rate limiting
1. Verify key: [p]lol profile "Riot Phreak" na
2. Check expiration (Personal keys expire daily)
3. Regenerate key on Riot Developer Portal
4. Ensure key has correct permissions
```

#### **LCU Connection Failed**
```bash
# Troubleshooting steps:
1. Restart League of Legends completely
2. Run League as administrator (Windows)
3. Check firewall/antivirus settings
4. Verify bot and League on same machine
5. Try: [p]lol lcu connect (after restart)
```

#### **Database Errors**
```bash
# If community features fail:
1. Check file permissions in cog directory
2. Restart the bot completely
3. Clear cache: [p]lol admin clear_cache
4. Rebuild database: [p]lol admin rebuild_db
```

### **Performance Issues**

#### **Slow Response Times**
- Check your internet connection
- Verify Riot API status
- Reduce concurrent users
- Consider production API key

#### **Memory Usage**
- Restart bot periodically
- Clear champion data cache
- Limit live game monitoring

### **Getting Help**

1. **Check logs:** Look for error messages in bot logs
2. **Test basic functionality:** `[p]lol profile "Riot Phreak" na`
3. **Update dependencies:** `pip install -r requirements.txt --upgrade`
4. **Join support server:** [Discord Support Server](#)
5. **Open an issue:** [GitHub Issues](#)

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### **Development Setup**
```bash
# Fork and clone the repository
git clone https://github.com/YourUsername/advanced-lol-cog.git
cd advanced-lol-cog

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### **Contribution Guidelines**
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Follow** code style guidelines (PEP 8, type hints)
4. **Add** tests for new functionality
5. **Update** documentation as needed
6. **Commit** changes (`git commit -m 'Add amazing feature'`)
7. **Push** to branch (`git push origin feature/amazing-feature`)
8. **Open** a Pull Request

### **Code Style**
- Follow **PEP 8** guidelines
- Use **type hints** for all functions
- Add **docstrings** for public methods
- Include **unit tests** for new features
- Update **documentation** for user-facing changes

### **Priority Areas**
- 🎯 **Additional achievements** and challenges
- 📊 **More analytics** and statistics
- 🎨 **UI/UX improvements** for embeds
- 🔗 **Enhanced LCU integration**
- 🌍 **Internationalization** support

---

## 📈 Roadmap

### **Version 2.1** (Next Release)
- [ ] **Tournament integration** with bracket support
- [ ] **Voice channel integration** for team coordination
- [ ] **Advanced statistics** with ML predictions
- [ ] **Mobile app companion** (React Native)
- [ ] **Webhook support** for external integrations

### **Version 2.2** (Future)
- [ ] **Multi-game support** (TFT, Valorant, LoR)
- [ ] **Custom dashboard** web interface
- [ ] **Advanced coaching features** with replay analysis
- [ ] **Team management** tools for competitive play
- [ ] **Streaming integration** with OBS overlays

### **Version 3.0** (Long-term)
- [ ] **AI-powered coaching** with personalized recommendations
- [ ] **Professional tournament** hosting capabilities
- [ ] **Monetization features** for community servers
- [ ] **Advanced security** with OAuth integration
- [ ] **Enterprise features** for large organizations

---

## 📄 License & Legal

### **License**
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### **Riot Games Legal**
This product is not endorsed, certified or otherwise approved in any way by Riot Games, Inc. or any of its affiliates.

**Riot Games Legal Compliance:**
- ✅ Uses official Riot Games API
- ✅ Respects rate limits and ToS
- ✅ Non-commercial use
- ✅ Proper attribution included
- ✅ No reverse engineering

### **Data Privacy**
- **User data:** Discord IDs, summoner names, achievement progress
- **Storage:** Local SQLite database only
- **Sharing:** No data shared with third parties
- **Deletion:** Users can request data deletion
- **API keys:** Stored locally, never transmitted

### **Third-Party Libraries**
This project uses several open-source libraries:
- **Red-DiscordBot** - Discord bot framework
- **aiohttp** - Async HTTP client
- **websockets** - WebSocket client
- **psutil** - System monitoring
- See `requirements.txt` for complete list

---

## 🙏 Acknowledgments

- **Riot Games** for the comprehensive League of Legends API
- **Red-DiscordBot** team for the amazing bot framework
- **Community contributors** who help improve this cog
- **Discord.py** developers for the Discord integration
- **Champion icon repository** maintainers
- **Beta testers** who helped identify issues and improvements

---

## 📞 Support

### **Get Help**
- 📖 **Documentation:** Read this README thoroughly
- 💬 **Discord Support:** [Join our Discord server](#)
- 🐛 **Bug Reports:** [Open an issue on GitHub](#)
- 💡 **Feature Requests:** [Submit enhancement ideas](#)
- 📧 **Email Support:** advanced-lol-cog@example.com

### **Quick Links**
- [🎮 Riot Developer Portal](https://developer.riotgames.com/)
- [🤖 Red-DiscordBot Documentation](https://docs.discord.red/)
- [📊 Champion Statistics](https://u.gg/)
- [🔧 Discord.py Documentation](https://discordpy.readthedocs.io/)

---

<div align="center">

**⭐ Star this repository if you found it helpful!**

Made with ❤️ for the League of Legends community

[🏠 Home](#-advanced-league-of-legends-cog) • [📦 Installation](#-installation) • [🚀 Usage](#-usage-guide) • [🤝 Contributing](#-contributing) • [📄 License](#-license--legal)

</div>
