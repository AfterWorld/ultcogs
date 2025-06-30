# NekoInteractions 🌸

A comprehensive anime-style interaction cog for Red-DiscordBot featuring beautiful GIFs from the nekos.best API. Spread the love (or slaps) with detailed statistics tracking!

## 🎯 Features

- **18+ Interaction Types**: Hug, kiss, slap, poke, pat, cuddle, feed, tickle, and more!
- **Beautiful Embeds**: Customizable colors with anime GIFs and engaging descriptions
- **Statistics Tracking**: Detailed per-user and server-wide interaction statistics
- **Smart Counting**: Tracks interactions between specific users (e.g., "Ult slapped Janus 3 times")
- **Cooldown System**: Configurable cooldowns to prevent spam
- **Admin Controls**: Full server configuration with easy toggle commands
- **Performance Optimized**: Efficient API usage with proper error handling

## 🚀 Installation

### Prerequisites
- Red-DiscordBot V3.5.0+
- Python 3.8+
- `aiohttp>=3.8.0` (automatically installed)

### Install from UltCogs Repository

1. Add the repository:
```
[p]repo add ultcogs https://github.com/AfterWorld/ultcogs
```

2. Install the cog:
```
[p]cog install ultcogs nekosinteract
```

3. Load the cog:
```
[p]load nekosinteract
```

### Manual Installation

1. Download the cog files to your Red cogs directory
2. Install using `[p]cog install local nekosinteract`
3. Load with `[p]load nekosinteract`

## 📖 Commands

### 💕 Interaction Commands

| Command | Description | Example |
|---------|-------------|---------|
| `[p]hug` | Give someone a warm hug | `[p]hug @friend` |
| `[p]kiss` | Give someone a sweet kiss | `[p]kiss @crush` |
| `[p]slap` | Playfully slap someone | `[p]slap @annoying_friend` |
| `[p]poke` | Poke someone for attention | `[p]poke @sleepy_user` |
| `[p]pat` | Give headpats | `[p]pat @good_user` |
| `[p]cuddle` | Cuddle with someone | `[p]cuddle @bestie` |
| `[p]feed` | Feed someone delicious food | `[p]feed @hungry_friend` |
| `[p]tickle` | Tickle someone playfully | `[p]tickle @giggly_person` |
| `[p]punch` | Anime-style punch | `[p]punch @rival` |
| `[p]bite` | Playfully bite someone | `[p]bite @nom_target` |

**And 8 more interactions!** Use `[p]nekohelp` to see the complete list.

### 📊 Statistics Commands

| Command | Description |
|---------|-------------|
| `[p]nekostats` | View your interaction statistics |
| `[p]nekostats user @user` | View another user's stats |
| `[p]nekostats server` | View server-wide statistics |

### ⚙️ Admin Commands

| Command | Description |
|---------|-------------|
| `[p]nekoset` | View current server settings |
| `[p]nekoset toggle` | Enable/disable interactions |
| `[p]nekoset color <color>` | Set embed color |
| `[p]nekoset cooldown <seconds>` | Set cooldown duration |

### ❓ Help Command

| Command | Description |
|---------|-------------|
| `[p]nekohelp` | Show all available commands with emojis |

## 🎨 Usage Examples

### Basic Interaction
```
Ult: .hug Janus
Bot: 🤗 Ult hugged Janus (1 time)!
[Displays cute anime hug GIF]
```

### Repeated Interactions
```
Ult: .slap Janus
Bot: 👋 Ult slapped Janus (3 times)!
[Shows anime slap GIF with updated count]
```

### Statistics Viewing
```
User: .nekostats
Bot: [Beautiful embed showing:]
📊 Overview
Given: 47 | Received: 23 | Total: 70

⭐ Favorite Action
🤗 Hug

🎯 Top Given          💝 Top Received
🤗 Hug: 15           🤗 Hug: 8
👋 Slap: 12          👉 Poke: 6
👉 Poke: 10          ✋ Pat: 4
```

## ⚙️ Configuration

### Server Settings

Administrators can customize the cog behavior:

- **Toggle On/Off**: Enable or disable all interactions
- **Embed Colors**: Customize the color scheme for your server
- **Cooldowns**: Set per-user cooldown periods (0-60 seconds recommended)
- **Statistics Display**: Show/hide interaction counts

### Default Settings
- Interactions: **Enabled**
- Embed Color: **Hot Pink (#FF69B4)**
- Cooldown: **3 seconds**
- Statistics: **Enabled**

## 🔧 Technical Details

### API Integration
- **Source**: nekos.best API (https://nekos.best/)
- **Rate Limiting**: Built-in request throttling
- **Error Handling**: Graceful fallbacks for API failures
- **Caching**: Minimal API calls through smart request management

### Data Storage
- **Hierarchical Config**: Global, guild, and member scopes
- **Statistics Tracking**: Per-user interaction counts and preferences
- **Performance**: Optimized database queries with atomic operations
- **Privacy**: Only Discord user IDs stored, no personal information

### Supported Interactions
The cog supports 18 different interaction types from the nekos.best API:

- **Affectionate**: hug, kiss, cuddle, pat, feed
- **Playful**: poke, tickle, nom, wink, smile
- **Aggressive**: slap, punch, bite
- **Social**: wave, highfive, handhold, stare, blush

## 🛠️ Development

### File Structure
```
nekosinteract/
├── __init__.py          # Cog entry point
├── nekosinteract.py     # Main cog implementation
├── info.json           # Cog metadata
└── README.md           # This documentation
```

### Key Features for Developers
- **Modular Design**: Clean separation of concerns
- **Type Hints**: Full typing support for better IDE integration
- **Error Handling**: Comprehensive exception management
- **Logging**: Detailed logging for debugging
- **Async/Await**: Proper async implementation throughout

## 🐛 Troubleshooting

### Common Issues

**Interactions not working?**
- Check if the cog is enabled: `[p]nekoset`
- Verify bot permissions in the channel
- Ensure nekos.best API is accessible

**Statistics not updating?**
- Check bot database permissions
- Restart the bot if issues persist
- Contact support with error logs

**API errors?**
- nekos.best API may be temporarily down
- Check your internet connection
- The cog will retry automatically

### Support

If you encounter issues:

1. Check the Red-DiscordBot logs for errors
2. Verify all prerequisites are met
3. Create an issue on the [GitHub repository](https://github.com/AfterWorld/ultcogs)
4. Include relevant error messages and Red version

## 📝 Changelog

### Version 1.0.0
- Initial release with 18 interaction types
- Statistics tracking system
- Customizable embeds and settings
- Cooldown management
- Admin configuration commands

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Follow Red-DiscordBot coding standards
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the repository for details.

## 🙏 Credits

- **nekos.best API**: For providing beautiful anime GIFs
- **Red-DiscordBot**: For the amazing bot framework
- **UltPanda**: Creator and maintainer
- **Discord.py**: For Discord API integration

## 💝 Support the Project

If you enjoy this cog:
- ⭐ Star the repository
- 🐛 Report bugs and suggest features
- 💬 Share with your Discord communities
- ☕ Consider supporting UltPanda's work

---

*Made with 💖 by UltPanda | Powered by nekos.best API*
