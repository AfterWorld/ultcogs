# OPC Server Supporters

A custom Discord bot cog specifically designed for the **One Piece Community** server to track and announce when members show their support by:

- Using the **OPC** clan tag 
- Adding **discord.gg/onepiececommunity** to their custom status

**Based on the original ServerSupporters cog by [AAA3A](https://github.com/AAA3A-AAA3A/AAA3A-cogs)** - modified for One Piece Community with no external dependencies.

## Features

🎉 **Automatic Announcements** - Beautiful embed messages when users start/stop supporting  
🔍 **Real-time Tracking** - Monitors clan tags and status changes instantly  
📊 **Live Statistics** - Real-time counts of supporters with engagement percentages  
🚫 **No Role Management** - Simple announcement-only system  
⚡ **Anti-Spam Protection** - Smart caching prevents duplicate announcements  
📋 **Supporter Lists** - Commands to view current supporters by type  

## Installation

1. **Load the cog**:
   ```
   [p]load opcsupporters
   ```

2. **Configure announcement channel**:
   ```
   [p]setopcsupporters announcementchannel #supporters-log
   ```

3. **Enable the system**:
   ```
   [p]setopcsupporters enabled True
   ```

4. **Initialize tracking** (important - run this once):
   ```
   [p]setopcsupporters scan
   ```

## Commands

### Setup Commands
- `[p]setopcsupporters` - Main configuration command group
- `[p]setopcsupporters announcementchannel <channel>` - Set where announcements are posted
- `[p]setopcsupporters enabled <True/False>` - Enable/disable the system
- `[p]setopcsupporters scan` - Scan all members to initialize tracking (run once after setup)

### Information Commands  
- `[p]setopcsupporters supportercount` (aliases: `count`, `stats`) - Show detailed statistics and counts of all supporters
- `[p]setopcsupporters listsupporters tag` - List all OPC clan tag supporters
- `[p]setopcsupporters listsupporters status` - List all invite link status supporters
- `[p]setopcsupporters showsettings` - View current configuration

## How It Works

### OPC Clan Tag Detection
The bot monitors when members:
- ✅ Add the "OPC" clan tag to their profile
- ❌ Remove the "OPC" clan tag from their profile

### Status Invite Detection  
The bot watches for these patterns in custom status:
- `discord.gg/onepiececommunity`
- `discord.com/invite/onepiececommunity` 
- `discordapp.com/invite/onepiececommunity`
- And other Discord invite variations

### Announcement Examples

**New Supporter:**
```
🎉 New OPC Supporter!
@Username is now supporting One Piece Community by using **OPC** clan tag!

Supporting with: OPC clan tag
OPC Supporters: 45 Tags • 23 Status • One Piece Community
```

**Supporter Departed:**
```
😔 OPC Supporter Departed  
@Username is no longer supporting One Piece Community with **discord.gg/onepiececommunity** in their status.

OPC Supporters: 45 Tags • 22 Status • One Piece Community
```

### Statistics Dashboard

Use `[p]setopcsupporters supportercount` to get detailed statistics:

```
🏴‍☠️ OPC Supporter Statistics

📋 OPC Clan Tag        💬 Status Invite      👥 Total Unique
**45** supporters      **23** supporters     **58** supporters

📊 Engagement Rate
**12.3%** of members are supporters
• Tag supporters: 9.5%
• Status supporters: 4.9%

📈 What We Track
• **OPC** clan tag usage
• **discord.gg/onepiececommunity** in status  
• Real-time changes and updates
```

## Permissions Required

- **Manage Guild** - To access configuration commands
- **Send Messages** - For the bot to post announcements
- **Embed Links** - To send rich embed announcements
- **Read Message History** - Standard bot permission

## Important Notes

⚠️ **Always run the scan command** after initial setup to avoid false announcements  
⚠️ **Anti-spam protection** prevents multiple announcements during rapid changes  
⚠️ **Hardcoded values** - This cog is specifically for One Piece Community server  
✅ **No external dependencies** - Runs with just Red-DiscordBot core (AAA3A_utils removed)  
🙏 **Based on AAA3A's work** - Core functionality inspired by the original ServerSupporters cog  

## Troubleshooting

**No announcements appearing?**
1. Check if the system is enabled: `[p]setopcsupporters showsettings`
2. Verify announcement channel is set and bot has permissions
3. Make sure you ran the initial scan command

**Getting spam announcements?**
- This usually happens if you didn't run the scan command first
- Run `[p]setopcsupporters scan` to initialize proper tracking

## File Structure

```
opcsupporters/
├── __init__.py          # Cog loader
├── opcsupporters.py     # Main cog code  
├── info.json           # Cog metadata
└── README.md           # This file
```

## Credits

This cog is heavily based on the original **ServerSupporters** cog by **[AAA3A](https://github.com/AAA3A-AAA3A)**:
- **Original Repository**: https://github.com/AAA3A-AAA3A/AAA3A-cogs
- **Original Cog**: ServerSupporters
- **Inspiration**: Core logic, event listeners, caching system, and embed design
- **Modifications**: Removed AAA3A_utils dependency, hardcoded OPC values, announcement-only functionality

Special thanks to AAA3A for creating the original comprehensive server supporters tracking system that inspired this implementation. The core concepts, anti-spam protection, member scanning logic, and overall architecture are based on their excellent work.

### Original AAA3A Features Adapted:
- ✅ Real-time presence and member update monitoring
- ✅ Smart caching system to prevent API spam
- ✅ Efficient member scanning and counting
- ✅ Robust error handling and logging
- ✅ Clean embed design and formatting
- ✅ Change detection to prevent false announcements

### Our OPC-Specific Modifications:
- 🔧 Removed external AAA3A_utils dependency 
- 🔧 Hardcoded OPC clan tag and invite detection
- 🔧 Simplified to announcement-only (no role management)
- 🔧 Added live statistics dashboard
- 🔧 Custom embed styling for One Piece Community