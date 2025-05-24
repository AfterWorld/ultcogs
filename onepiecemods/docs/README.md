# 🏴‍☠️ One Piece Mods - Advanced Discord Moderation

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/afterworld/onepiecemods)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Red-DiscordBot](https://img.shields.io/badge/Red--DiscordBot-3.5+-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An advanced, feature-rich Discord moderation cog for Red-DiscordBot with complete One Piece theming. Transform your server moderation into an epic pirate adventure!

## ✨ Features

### 🎭 One Piece Themed Moderation
- **Luffy Kick**: Kick users with Gomu Gomu no power
- **Shanks Ban**: Ban users with Yonko-level authority  
- **Law's Room**: Mute users with Sea Prism Stone
- **Bounty System**: Warning system with escalating bounties
- **Impel Down**: Multi-level punishment system (6 levels)
- **Automatic Release**: Background task for punishment expiration

### 🔧 Advanced Configuration
- **Interactive Setup Wizard**: Easy first-time configuration
- **Flexible Settings**: Customizable cooldowns, escalation rules, and limits
- **Configuration Import/Export**: Backup and share server settings
- **Real-time Validation**: Automatic configuration health checks
- **Migration System**: Seamless updates between versions

### 📊 Enhanced Logging & Analytics
- **Webhook Integration**: Advanced logging to Discord webhooks
- **Detailed Statistics**: Comprehensive moderation analytics
- **Escalation Tracking**: Monitor automatic punishment escalations
- **Error Logging**: Automatic error reporting and debugging
- **Performance Monitoring**: Rate limiting and queue management

### 🛡️ Security & Reliability
- **Hierarchy Validation**: Comprehensive permission and role checks
- **Rate Limiting**: Prevent command spam and abuse
- **Error Recovery**: Graceful handling of API failures
- **Backup System**: Automatic data backup and restoration
- **Audit Logging**: Detailed moderation action tracking

### 🎨 User Experience
- **Paginated History**: Browse moderation records easily
- **Rich Embeds**: Beautiful, informative message formatting
- **Progress Indicators**: Visual feedback for long operations
- **Intelligent Cooldowns**: Context-aware command limiting
- **Comprehensive Help**: Detailed command documentation

## 📋 Requirements

- Python 3.8+
- Red-DiscordBot 3.5+
- Discord.py 2.3+

## 🚀 Installation

### Red's Cog Manager 
```bash
# Add the repository
[p]repo add onepiecemods https://github.com/AfterWorld/ultcogs/tree/main/onepiecemods

# Install the cog
[p]cog install onepiecemods onepiecemods

# Load the cog
[p]load onepiecemods
```

2. Install the cog:
```bash
[p]load onepiecemods
```
## ⚙️ Setup

### Quick Setup (Recommended)
Use the interactive setup wizard:
```
[p]opm setup
```

This will guide you through:
- Creating/setting the mute role
- Configuring the log channel
- Setting up escalation preferences
- Testing webhook integration

### Manual Setup
```bash
# Set the mute role (creates automatically if none specified)
[p]opm setmuterole

# Set the log channel (uses current channel if none specified)  
[p]opm setlogchannel

# Configure webhook logging (optional)
[p]opm webhook set https://discord.com/api/webhooks/...

# Test your configuration
[p]opm validate
```

## 📖 Commands

### 🛠️ Setup & Configuration
| Command | Description | Example |
|---------|-------------|---------|
| `[p]opm setup` | Interactive setup wizard | `!opm setup` |
| `[p]opm config` | View current settings | `!opm config` |
| `[p]omp set <setting> <value>` | Change a setting | `!opm set warning_cooldown 60` |
| `[p]opm validate` | Check configuration health | `!opm validate` |
| `[p]opm export` | Export settings to JSON | `!opm export` |
| `[p]opm import` | Import settings from file | `!opm import` |

### ⚔️ Moderation Commands
| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `[p]luffykick` | `zoroshove`, `strawhatpunch` | Kick a user | `!luffykick @user reason` |
| `[p]shanksban` | `garpfist`, `admiralban` | Ban a user | `!shanksban @user reason` |
| `[p]lawroom` | `seaprism`, `calmcalm` | Mute a user | `!lawroom @user 1h30m reason` |
| `[p]bountyset` | `marinealert`, `poster` | Warn a user | `!bountyset @user reason` |
| `[p]impeldown` | `imprison` | Send to Impel Down | `!impeldown @user 3 2h reason` |
| `[p]liberate` |  `breakout` | Release from punishment | `!liberate @user reason` |

### 🔍 Information Commands
| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `[p]bountycheck` | `checkbounty` | Check user's warnings | `!bountycheck @user` |
| `[p]crewhistory` | `history`, `mlogs` | View moderation history | `!crewhistory @user` |
| `[p]nakama` | `crewinfo` | Server information | `!nakama` |
| `[p]modstats` | `stats` | Moderation statistics | `!modstats 30` |
| `[p]advancedstats` | `astats` | Detailed analytics | `!astats 7` |

### 🔧 Advanced Features
| Command | Description | Example |
|---------|-------------|---------|
| `[p]opm webhook test` | Test webhook configuration | `!opm webhook test` |
| `[p]opm backup` | Create data backup | `!opm backup` |
| `[p]opm reset <setting>` | Reset setting to default | `!opm reset auto_escalation` |
| `[p]opm migrate` | Migrate between versions | `!opm migrate 1.0 2.0` |

## 🏭 Impel Down System

The signature feature of One Piece Mods is the multi-level Impel Down punishment system:

### Level 1: Crimson Hell
- **Duration**: 10 minutes default
- **Restrictions**: Send messages, add reactions
- **Use Case**: Minor infractions, first-time offenders

### Level 2: Wild Beast Hell  
- **Duration**: 30 minutes default
- **Restrictions**: Send messages, add reactions, speak in voice
- **Use Case**: Repeated minor infractions

### Level 3: Starvation Hell
- **Duration**: 1 hour default
- **Restrictions**: All above + view channels
- **Use Case**: Serious violations, escalated warnings

### Level 4: Burning Hell
- **Duration**: 2 hours default  
- **Restrictions**: All Level 3 restrictions
- **Use Case**: Major infractions, harassment

### Level 5: Freezing Hell
- **Duration**: 4 hours default
- **Restrictions**: Complete server isolation
- **Use Case**: Severe violations, repeated major infractions

### Level 6: Eternal Hell
- **Duration**: 12 hours default (max 7 days)
- **Restrictions**: Maximum security isolation  
- **Use Case**: Most serious violations, ban alternatives

## 📈 Escalation System

Automatic escalation triggers based on warning levels:

| Warning Level | Auto-Escalation | Duration |
|---------------|-----------------|----------|
| 3 warnings | Impel Down Level 1 | 30 minutes |
| 5 warnings | Impel Down Level 3 | 1 hour |
| 7+ warnings | Impel Down Level 5 | 2+ hours |

*Escalation can be customized or disabled per server*

## 🎛️ Configuration Options

### Core Settings
- `mute_role`: Sea Prism Stone role for muting
- `log_channel`: Marine HQ channel for moderation logs
- `warning_cooldown`: Time between warnings (5-3600 seconds)
- `auto_escalation`: Enable automatic escalation (true/false)
- `max_warning_level`: Maximum warning level (1-10)

### Advanced Settings
- `escalation_levels`: Custom escalation thresholds
- `audit_log_format`: Template for audit log entries
- `backup_enabled`: Enable automatic backups
- `webhook_url`: Discord webhook for advanced logging
- `dm_on_punishment`: Send DMs to punished users

### Example Configuration
```json
{
  "warning_cooldown": 30,
  "auto_escalation": true,
  "max_warning_level": 6,
  "escalation_levels": {
    "3": {"level": 1, "duration": 30},
    "5": {"level": 3, "duration": 60},
    "7": {"level": 5, "duration": 120}
  },
  "audit_log_format": "One Piece Mods: {moderator} | {reason}",
  "backup_enabled": true
}
```

## 🔗 Webhook Integration

Advanced logging via Discord webhooks provides:

- **Real-time Notifications**: Instant moderation alerts
- **Rich Formatting**: Detailed, colorful log embeds  
- **Error Tracking**: Automatic error reporting
- **System Events**: Configuration changes, escalations
- **Performance Monitoring**: Rate limits, queue status

### Setting Up Webhooks
1. Create a webhook in your desired channel
2. Configure the webhook URL: `[p]opm webhook set <url>`
3. Test the configuration: `[p]omp webhook test`

## 🧪 Testing

Run the test suite:
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=onepiecemods tests/
```

## 🐛 Troubleshooting

### Common Issues

**Bot not responding to commands:**
- Verify the cog is loaded: `[p]cogs`
- Check bot permissions in the channel
- Ensure proper Red-DiscordBot setup

**Mute not working:**
- Verify mute role exists: `[p]opm config`
- Check role hierarchy (bot role above mute role)
- Ensure bot has Manage Roles permission

**Webhook errors:**
- Test webhook configuration: `[p]opm webhook test`
- Verify webhook URL format
- Check webhook channel permissions

**Configuration validation errors:**
- Run validation check: `[p]opm validate`
- Reset problematic settings: `[p]opm reset <setting>`
- Use setup wizard: `[p]opm setup`

### Debug Mode
Enable detailed logging:
```python
import logging
logging.getLogger("red.onepiecemods").setLevel(logging.DEBUG)
```

### Getting Help
1. Check the [Issues](https://github.com/afterworld/onepiecemods/issues) page
2. Join the [Red-DiscordBot Support Server](https://discord.gg/red)
3. Read the [Red Documentation](https://docs.discord.red/)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Code Standards
- Follow PEP 8 style guidelines
- Use Black for code formatting
- Add type hints where possible
- Write comprehensive docstrings
- Include unit tests for new features

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **One Piece** by Eiichiro Oda - for the incredible world and characters
- **Red-DiscordBot Team** - for the amazing bot framework
- **Discord.py Team** - for the excellent Discord API library
- **Contributors** - for making this project better

## 🔗 Links

- [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [One Piece Wiki](https://onepiece.fandom.com/)

---

*Navigate the Grand Line of Discord moderation with the power of the Straw Hat Pirates! 🏴‍☠️*
