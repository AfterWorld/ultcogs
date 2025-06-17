# Grilled - Dramatic Ban Cog

**Part of the [UltCogs](https://github.com/AfterWorld/ultcogs) collection by AfterWorld**

A simple Red-DiscordBot v3 cog that adds dramatic flair to your moderation with a 10-second countdown before banning users.

## Features

- 🔥 **Dramatic Countdown**: Fixed 10-second countdown before banning
- 💥 **Rich Embeds**: Beautiful embed messages with visual countdown
- 🛡️ **Safety Checks**: Comprehensive permission and hierarchy validation
- 🚫 **Spam Protection**: Prevents multiple simultaneous grill sessions
- ❌ **Cancellation**: Moderators can type "cancel" during countdown to abort
- ⚡ **Simple**: No configuration needed - just install and use

## Installation

1. Add the repo: `[p]repo add ultcogs https://github.com/AfterWorld/ultcogs`
2. Install the cog: `[p]cog install ultcogs grilled`
3. Load the cog: `[p]load grilled`

## Commands

### Main Command
- `[p]grill <member> [reason]` - Ban a member with dramatic 10-second countdown
  - Requires: Ban Members permission
  - Bot needs: Ban Members permission
  - Cooldown: 30 seconds per guild

## Examples

```
# Basic usage
[p]grill @baduser

# With custom reason
[p]grill @spammer Spam and harassment
```

## How It Works

1. **Initial Message**: Shows grill protocol initiated
2. **Countdown**: 10-second countdown with visual timer
3. **Cancellation Window**: Type "cancel" anytime to abort
4. **Final Message**: Dramatic "grilled" message
5. **Ban Execution**: User gets banned with specified reason
6. **Confirmation**: Brief confirmation message

## Safety Features

- Cannot grill server owner
- Cannot grill users with equal/higher roles
- Cannot grill the bot itself
- Cannot grill yourself
- Respects Discord's role hierarchy
- Comprehensive error handling
- Prevents duplicate grill sessions

## Permissions Required

**For Users:**
- Ban Members permission OR Administrator permission

**For Bot:**
- Ban Members permission
- Send Messages permission
- Embed Links permission
- Use External Emojis permission

## Troubleshooting

**"I don't have permission to ban this member!"**
- Check that the bot has Ban Members permission
- Ensure the target user's highest role is below the bot's highest role

**Countdown seems stuck**
- Check for network lag or Discord API issues
- Ensure the bot has permission to edit messages

**Command not working**
- Verify you have Ban Members permission
- Check that the bot is loaded: `[p]cog list`

## Support

For support, feature requests, or bug reports, please create an issue at: https://github.com/AfterWorld/ultcogs/issues

## Changelog

### v1.0.0
- Initial release
- 10-second countdown dramatic bans
- Safety checks and error handling
- Cancellation support during countdown
