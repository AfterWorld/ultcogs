# TikTok Live Notifications

Get instant Discord notifications when your favorite TikTok creators go live! This Red-DiscordBot cog uses the powerful TikTokLive library for real-time WebSocket monitoring with beautiful embeds, role mentions, and comprehensive statistics.

## ✨ Features

### 🎯 **Core Functionality**
- **Real-time live stream detection** - Near-instant notifications (<5 seconds)
- **WebSocket connections** - Direct monitoring of TikTok live streams
- **Beautiful Discord notifications** - Customizable embeds with TikTok branding
- **Multi-server support** - Independent configuration per Discord server
- **Automatic reconnection** - Robust error handling and recovery

### 🎨 **Customization Options**
- **Role mentions** - Notify specific roles when users go live
- **Custom embed colors** - TikTok pink, hex codes, or color names
- **Custom messages** - Add personalized text to notifications
- **Auto-delete** - Configurable timeout for automatic message cleanup
- **Notification types** - Toggle connect/disconnect notifications

### 📊 **Monitoring & Management**
- **Connection status tracking** - Real-time monitoring of connection health
- **Detailed statistics** - Track notifications sent and user activity
- **Force reconnection** - Manual reconnect for troubleshooting
- **System status** - Comprehensive monitoring dashboard
- **Error reporting** - Detailed logging and error tracking

## 🚀 Installation

### Prerequisites
1. **Red-DiscordBot** - Version 3.5.0 or higher
2. **Python** - Version 3.8 or higher
3. **TikTokLive Library** - Installed via pip

### Step 1: Install TikTokLive Library
```bash
pip install TikTokLive
```

### Step 2: Install the Cog
#### Option A: From Red Index (Recommended)
```
[p]repo add ultcogs https://github.com/AfterWorld/ultcogs
[p]cog install ultcogs tiktok
[p]load tiktok
```

#### Option B: Manual Installation
1. Download the cog files to your Red cogs directory
2. Load the cog: `[p]load tiktok`

## ⚙️ Quick Setup

### Basic Configuration
```
# Set notification channel
[p]tiktok channel #live-notifications

# Add TikTok users to monitor
[p]tiktok add charlidamelio
[p]tiktok add mrbeast

# Optional: Set role to mention
[p]tiktok role @TikTok Live

# Test your setup
[p]tiktok test
```

### Advanced Configuration
```
# Customize embed color
[p]tiktok color #ff0050

# Add custom message
[p]tiktok message 🎉 Someone is live! Come watch!

# Auto-delete notifications after 5 minutes
[p]tiktok timeout 300

# Configure notification types
[p]tiktok notifications connect true
[p]tiktok notifications disconnect false
```

## 📋 Command Reference

### Basic Commands
| Command | Description | Permission |
|---------|-------------|------------|
| `[p]tiktok add <username>` | Add user to monitor | Admin |
| `[p]tiktok remove <username>` | Remove user from monitoring | Admin |
| `[p]tiktok list` | Show all monitored users | Any |
| `[p]tiktok channel [#channel]` | Set notification channel | Admin |
| `[p]tiktok role [@role]` | Set mention role | Admin |

### Configuration Commands
| Command | Description | Permission |
|---------|-------------|------------|
| `[p]tiktok config` | Show current settings | Admin |
| `[p]tiktok color <color>` | Set embed color | Admin |
| `[p]tiktok message <text>` | Set custom message | Admin |
| `[p]tiktok timeout <seconds>` | Auto-delete timeout | Admin |
| `[p]tiktok notifications <type> <bool>` | Toggle notification types | Admin |

### Monitoring Commands
| Command | Description | Permission |
|---------|-------------|------------|
| `[p]tiktok status [username]` | Show detailed status | Any |
| `[p]tiktok reconnect <username>` | Force reconnect user | Admin |
| `[p]tiktok test` | Send test notification | Admin |
| `[p]tiktok info` | Show cog information | Any |

### Owner Commands
| Command | Description | Permission |
|---------|-------------|------------|
| `[p]tiktok restart` | Restart all monitoring | Owner |
| `[p]tiktok global <setting> <value>` | Global configuration | Owner |

## 🎨 Customization Examples

### Color Options
```bash
# TikTok brand colors
[p]tiktok color tiktok      # TikTok pink (#ff0050)

# Standard colors
[p]tiktok color red         # Red (#ff0000)
[p]tiktok color green       # Green (#00ff00)
[p]tiktok color blue        # Blue (#0000ff)

# Custom hex colors
[p]tiktok color #9146ff     # Twitch purple
[p]tiktok color #1da1f2     # Twitter blue
```

### Custom Messages
```bash
# Simple message
[p]tiktok message 🔴 LIVE NOW!

# Detailed message
[p]tiktok message 🎉 Someone just went live on TikTok! Drop everything and go watch! 📱

# Clear message
[p]tiktok message none
```

### Notification Types
```bash
# Enable live start notifications
[p]tiktok notifications connect true

# Enable stream end notifications  
[p]tiktok notifications disconnect true

# Disable stream end notifications
[p]tiktok notifications disconnect false
```

## 📊 Status Indicators

The cog provides real-time status indicators for monitored users:

- 🔴 **LIVE** - User is currently streaming
- 🟢 **Connected** - Monitoring active, ready to detect
- 🟡 **Connecting** - Establishing connection
- 🔄 **Retrying** - Reconnecting after error
- ❌ **Failed** - Max retries exceeded
- ⚫ **Offline** - Not connected

## 🛠️ Troubleshooting

### Common Issues

#### TikTokLive Library Not Found
**Error**: `TikTokLive library not found!`
**Solution**: Install the library with `pip install TikTokLive`

#### Connection Failures
**Symptoms**: Users showing "Failed" status
**Solutions**:
1. Check internet connectivity
2. Verify TikTok username exists
3. Use `[p]tiktok reconnect <username>` to retry
4. Check Red logs for detailed error messages

#### No Notifications Received
**Checklist**:
1. ✅ Notification channel set: `[p]tiktok channel`
2. ✅ Users added: `[p]tiktok add username`
3. ✅ Bot has send permissions in channel
4. ✅ User is actually going live
5. ✅ Test notifications work: `[p]tiktok test`

### Advanced Troubleshooting

#### Force Restart All Monitoring
```bash
[p]tiktok restart
```

#### Check System Status
```bash
[p]tiktok status
```

#### View Detailed User Status
```bash
[p]tiktok status username
```

#### Adjust Global Settings (Owner Only)
```bash
# Increase retry attempts
[p]tiktok global retries 10

# Increase retry delay
[p]tiktok global delay 60

# Disable auto-reconnect
[p]tiktok global reconnect false
```

## 🔧 Technical Details

### Architecture
- **Library**: TikTokLive by Isaac Kogan
- **Connection Method**: WebSocket (real-time)
- **Detection Latency**: <5 seconds typically
- **Resource Usage**: Minimal CPU and memory
- **Scalability**: Handles hundreds of monitored users

### Performance Considerations
- Each monitored user requires one WebSocket connection
- Connections automatically reconnect on failures
- Background tasks handle monitoring efficiently
- Memory usage scales linearly with monitored users

### Security & Privacy
- No TikTok account credentials required
- Only public live stream data accessed
- No personal data stored beyond usernames
- All data stored locally in Red's config system

## 📚 API Reference

### Events Handled
- **ConnectEvent** - User goes live
- **DisconnectEvent** - User stops streaming
- **LiveEndEvent** - Live stream ends

### Configuration Structure
```python
# Global settings
{
    "reconnect_on_disconnect": True,
    "max_retries": 5,
    "retry_delay": 30,
    "monitoring_enabled": True
}

# Per-guild settings
{
    "notification_channel": 123456789,
    "monitored_users": ["user1", "user2"],
    "mention_role": 987654321,
    "embed_color": 0xff0050,
    "custom_message": "🔴 LIVE NOW!",
    "notify_on_connect": True,
    "notify_on_disconnect": False,
    "notification_timeout": 300
}
```

## 🤝 Contributing

Contributions are welcome! Please feel free to:
- Report bugs in GitHub Issues
- Suggest new features
- Submit pull requests
- Improve documentation

### Development Setup
1. Fork the repository
2. Install development dependencies: `pip install TikTokLive`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This cog is part of the UltCogs collection and follows Red-DiscordBot's licensing terms.

## 👨‍💻 Author

**UltPanda**
- GitHub: [@AfterWorld](https://github.com/AfterWorld)
- Repository: [ultcogs](https://github.com/AfterWorld/ultcogs)

## 🙏 Credits

- **Isaac Kogan** - Creator of the TikTokLive library
- **Red-DiscordBot Team** - Framework and foundation
- **TikTok** - Platform and inspiration

## 📞 Support

Need help? Here are your options:
1. Check this README first
2. Search GitHub Issues
3. Join the Red-DiscordBot Discord server
4. Create a new GitHub Issue

---

*Made with ❤️ for the Red-DiscordBot community*
