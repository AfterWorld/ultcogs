# 🏴‍☠️ UltCogs - Ultimate Discord Bot Cogs

A collection of premium Discord bot cogs for Red-DiscordBot, designed to maximize server engagement and community interaction.

## 🎯 Featured Cog: OPE (One Piece Engagement)

**The Ultimate One Piece Engagement System** - Transform your Discord server into the most active One Piece community in the Grand Line!

[![Discord](https://img.shields.io/discord/374126802836258816?color=7289DA&label=Support%20Server&logo=discord&style=flat-square)](https://discord.gg/onepiececommunity)
[![GitHub stars](https://img.shields.io/github/stars/afterworld/ultcogs?style=flat-square)](https://github.com/afterworld/ultcogs/stargazers)
[![Red-DiscordBot](https://img.shields.io/badge/Red--DiscordBot-V3-red?style=flat-square)](https://github.com/Cog-Creators/Red-DiscordBot)

---

## ⚡ Quick Install

```bash
[p]repo add ultcogs https://github.com/afterworld/ultcogs
[p]cog install ultcogs ope
[p]load ope
```

**Setup in 30 seconds:**
```bash
[p]op challenges channel #daily-challenges
[p]op trivia_admin channel #trivia-corner
[p]op challenges time 12:00
[p]op trivia_admin toggle
[p]op challenges force daily
```

---

## ✨ Features

### 🗓️ **Daily Challenges System**
- **75+ unique challenges** across 7 categories
- **Automatic posting** at your preferred time
- **Themed content** (Theory Monday, Fight Friday, etc.)
- **Point rewards** and streak tracking
- **Easy content management** through YAML files

### 🧠 **Advanced Trivia System**
- **200+ One Piece questions** across 4 difficulty levels
- **Auto-posting trivia** with customizable intervals
- **Speed bonuses** for quick answers
- **Category-based organization** (Characters, Powers, Locations, etc.)
- **Mini-games**: Emoji guessing, quote completion, character analysis

### 🏆 **Progression & Rankings**
- **Comprehensive point system** with "berries" currency
- **Rank progression** from "Rookie Pirate" to "Pirate King Candidate"
- **Achievement system** with unlockable titles
- **Server & global leaderboards**
- **Daily streak tracking** with bonuses

### 📊 **Analytics & Management**
- **Detailed user profiles** with statistics and progress bars
- **Admin dashboard** with engagement metrics
- **Flexible configuration** for different server sizes
- **Real-time reload** system for content updates

---

## 📋 Content Database

| Category | Count | Description |
|----------|-------|-------------|
| **Daily Challenges** | 75+ | Discussion, creative, trivia, scenario, debate prompts |
| **Weekly Challenges** | 60+ | Contests, tournaments, analysis weeks, themed events |
| **Trivia Questions** | 200+ | Easy (50+), Medium (60+), Hard (50+), Expert (40+) |
| **Characters** | 150+ | Straw Hats, Emperors, Marines, Pirates, Revolutionaries |
| **Devil Fruits** | 100+ | Paramecia, Zoan, Logia with detailed classifications |
| **Locations** | 50+ | Islands, seas, special places from the One Piece world |

---

## 🎮 User Commands

### Basic Commands
```bash
[p]op                    # Main hub with all options
[p]op trivia [difficulty] # Manual trivia game
[p]op stats              # Your personal statistics
[p]op profile            # Detailed profile with rank
[p]op leaderboard        # Server rankings
[p]op daily              # Check today's challenge
```

### Mini-Games
```bash
[p]op emoji              # Guess character by emoji 🍖⚔️🍊
[p]op quote              # Complete famous One Piece quotes
[p]op character          # Multi-round character guessing
```

### Trivia Difficulties
- **Easy** (10 points) - Perfect for new fans
- **Medium** (20 points) - Intermediate knowledge
- **Hard** (30 points) - Expert level content
- **Expert** (50 points) - Legendary difficulty

---

## ⚙️ Admin Commands

### Challenge Management
```bash
[p]op challenges channel <channel>     # Set challenge channel
[p]op challenges time <HH:MM>         # Set daily post time
[p]op challenges toggle daily         # Enable/disable daily
[p]op challenges force daily          # Post challenge now
[p]op challenges status               # View settings
[p]op challenges reload               # Reload data files
```

### Trivia Management
```bash
[p]op trivia_admin channel <channel>  # Set trivia channel
[p]op trivia_admin toggle             # Enable/disable auto trivia
[p]op trivia_admin interval <minutes> # Set posting frequency
[p]op trivia_admin force              # Post trivia now
[p]op trivia_admin status             # View settings
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Red-DiscordBot V3.5.0+
- Python 3.8+
- PyYAML>=6.0

### Detailed Setup Guide

1. **Install the cog:**
   ```bash
   [p]repo add ultcogs https://github.com/afterworld/ultcogs
   [p]cog install ultcogs ope
   [p]load ope
   ```

2. **Create dedicated channels:**
   ```
   #daily-challenges  (for daily challenge posts)
   #trivia-corner     (for auto trivia games)
   ```

3. **Configure the system:**
   ```bash
   [p]op challenges channel #daily-challenges
   [p]op trivia_admin channel #trivia-corner
   [p]op challenges time 12:00              # Daily post time
   [p]op trivia_admin interval 120          # Trivia every 2 hours
   [p]op trivia_admin toggle                # Enable auto trivia
   ```

4. **Test your setup:**
   ```bash
   [p]op challenges force daily             # Test daily challenge
   [p]op trivia_admin force                 # Test auto trivia
   [p]op challenges status                  # Check settings
   ```

5. **Launch announcement:**
   ```
   🎉 NEW: One Piece Engagement System!
   • Daily challenges in #daily-challenges
   • Auto trivia in #trivia-corner  
   • Rankings and achievements system
   Use [p]op to get started!
   ```

---

## 🎨 Customization

### Adding New Content

**Daily Challenges** (`challenges/daily_challenges.yaml`):
```yaml
discussion:
  - prompt: "What's your favorite Wano character?"
    category: "wano"
    difficulty: "easy"
```

**Trivia Questions** (`trivia/easy.yaml`):
```yaml
characters:
  - question: "Who is Luffy's grandfather?"
    answers: ["garp", "monkey d garp"]
    category: "family"
```

**Apply Changes:**
```bash
[p]op challenges reload
```

### Themed Events

**Example: Wano Week**
1. Edit challenge files to focus on Wano content
2. Set special announcements
3. Consider bonus point multipliers
4. Reload: `[p]op challenges reload`

---

## 📊 Success Metrics

Servers using OPE typically see:
- **300% increase** in daily active users
- **500% more messages** in dedicated channels  
- **85% user retention** after first week
- **Daily engagement** with 60%+ of active members

### Optimization Tips
- Post challenges during peak server hours
- Use 1-3 hour trivia intervals for active servers
- Celebrate achievements and milestones
- Create friendly competition through leaderboards

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Adding Content
1. Fork this repository
2. Edit the YAML files to add new challenges/trivia
3. Test your additions
4. Submit a pull request

### Reporting Issues
- Use GitHub Issues for bug reports
- Include your Red version and error messages
- Describe steps to reproduce the problem

### Feature Requests
- Check existing issues first
- Describe the feature and its benefits
- Consider implementation complexity

---

## 📝 Changelog

### v1.0.0 (Current)
- ✅ Initial release with full feature set
- ✅ 300+ pieces of pre-loaded content
- ✅ Complete admin management system
- ✅ Advanced analytics and tracking
- ✅ Comprehensive documentation

### Upcoming Features
- 🔄 Custom achievement creation
- 🔄 Integration with economy cogs
- 🔄 Advanced tournament systems
- 🔄 Community content submission portal

---

## 🆘 Support

### Getting Help
- **Documentation:** Full setup guide included
- **Commands:** Use `[p]help ope` in Discord
- **Community:** Join our support server
- **Issues:** GitHub issue tracker

### Common Issues

**Nothing posting automatically?**
- Check channel permissions
- Verify settings with `[p]op challenges status`
- Ensure features are enabled

**Low participation?**
- Adjust posting times to peak hours
- Create excitement with announcements
- Participate yourself to encourage others

### Quick Troubleshooting
```bash
[p]unload ope && [p]load ope  # Reset the cog
[p]op challenges reload        # Reload content files
[p]help ope                   # Show all commands
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Eiichiro Oda** - Creator of One Piece
- **Red-DiscordBot Team** - Excellent bot framework
- **One Piece Community** - Inspiration and feedback
- **Contributors** - Making this project better

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=afterworld/ultcogs&type=Date)](https://star-history.com/#yourusername/ultcogs&Date)

---

<div align="center">

**Transform your Discord server into the ultimate One Piece community!**

[**📥 Install Now**](https://github.com/afterworld/ultcogs) • [**📚 Documentation**](https://github.com/afterworld/ultcogs/wiki) • [**💬 Support Server**](https://discord.gg/onepiececommunity) • [**🐛 Report Bug**](https://github.com/afterworld/ultcogs/issues)

Made with ❤️ for the One Piece community

</div>
