# Report Cog

An advanced user reporting system for Red-DiscordBot that provides comprehensive moderation tools with staff quick-action buttons.

## Features

### 🚨 Dual Reporting Methods
- **Command-based**: `[p]report @user reason` 
- **Reply Support**: Reply to a message and use the report command to include context
- **Context Menu**: *Coming in future Red versions with context menu support*

### ⚡ Staff Quick Actions
Interactive buttons on each report for immediate moderation:
- **Caution**: Add warning points that integrate with the Cautions cog system
- **Mute 1h**: Timeout the reported user for 1 hour
- **Ban**: Permanently ban the reported user
- **Blacklist Reporter**: Prevent false reporters from using the system
- **Dismiss**: Mark the report as reviewed without action

### 🛡️ Anti-Abuse Protection
- **Cooldown System**: Configurable cooldown between reports (default: 5 minutes)
- **Blacklist Management**: Block users who abuse the reporting system
- **Input Validation**: Sanitize and validate all user inputs
- **Permission Checks**: Only staff can use action buttons

### 📊 Comprehensive Logging
- **Action Logging**: All moderation actions are logged to a dedicated channel
- **User Statistics**: Track total reports per user
- **Detailed Reports**: Include message content, links, and metadata

## Installation

1. Add the repo: `[p]repo add ultcogs https://github.com/AfterWorld/ultcogs`
2. Install the cog: `[p]cog install ultcogs report`
3. Load the cog: `[p]load report`

## Setup Guide

### 1. Basic Configuration
```
[p]reportset channel #reports
[p]reportset staffrole add @Moderators
[p]reportset logchannel #mod-logs
```

### 2. Optional Settings
```
[p]reportset cooldown 300          # 5 minute cooldown
[p]reportset toggle                # Enable/disable system
```

### 3. View Configuration
```
[p]reportset status               # Show current settings
```

## Commands

### User Commands
- `[p]report @user reason` - Report a user with a reason
- `[p]report reason` - When replying to a message, auto-detects the user
- `[p]report @user` - When replying to a message, uses message as context
- `[p]report` - When replying to a message, uses message content as reason

### Admin Commands (Requires Administrator)
- `[p]reportset channel [#channel]` - Set/view report channel
- `[p]reportset staffrole <add/remove/list> [@role]` - Manage staff roles
- `[p]reportset logchannel [#channel]` - Set/view log channel
- `[p]reportset cooldown <seconds>` - Set cooldown between reports
- `[p]reportset toggle` - Enable/disable the system
- `[p]reportset blacklist <add/remove/list> [@user]` - Manage blacklist
- `[p]reportset status` - Show configuration overview

## Usage Examples

### Reporting a User
```
# Standard method
[p]report @BadUser They were spamming inappropriate content

# Reply method (auto-detects user from replied message)
Reply to the problematic message → [p]report Inappropriate content
Reply to the problematic message → [p]report @BadUser (uses message as context)
Reply to the problematic message → [p]report (uses message content as reason)
```

### Staff Actions
When a report is received, staff see an embed with action buttons:
- Click "Caution" to add warning points via the Cautions cog system
- Click "Mute 1h" for quick timeout
- Click "Ban" for immediate ban
- Click "Blacklist Reporter" if report is false/malicious
- Click "Dismiss" to mark as reviewed

**Caution Integration**: The Caution button requires the Cautions cog to be loaded. It will:
- Add configurable warning points to the user
- Automatically trigger threshold actions (mute, timeout, kick, ban)
- Use the same expiry and logging system as the Cautions cog
- Respect all Cautions cog configuration settings

### Administrative Setup
```
# Initial setup
[p]reportset channel #staff-reports
[p]reportset staffrole add @Moderators
[p]reportset staffrole add @Admins
[p]reportset logchannel #mod-actions

# View current config
[p]reportset status

# Manage problematic users
[p]reportset blacklist add @FalseReporter
[p]reportset blacklist list
```

## Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `channel` | Channel where reports are sent | None |
| `staffroles` | Roles that get pinged on reports | Empty |
| `logchannel` | Channel for logging actions | None |
| `cooldown` | Seconds between reports per user | 300 (5 min) |
| `enabled` | Whether system is active | True |
| `blacklist` | Users blocked from reporting | Empty |

## Security Features

### Input Validation
- Sanitizes user input to prevent injection
- Limits reason length to 1000 characters
- Removes control characters

### Permission Checks
- Only staff can use action buttons
- Administrators only for configuration
- Prevents self-reporting and bot reporting

### Anti-Abuse Measures
- Cooldown system prevents spam
- Blacklist system for persistent abusers
- Comprehensive logging for accountability

## Troubleshooting

### Common Issues

**Reports not being logged?**
- Check if log channel is set: `[p]reportset logchannel #your-log-channel`
- Ensure bot has permission to send messages in log channel
- Verify the log channel still exists and wasn't deleted
- Check `[p]reportset status` to see current configuration
**Reports not appearing in report channel?**
- Ensure bot has permission to send messages in report channel
- Verify the system is enabled: `[p]reportset toggle`

**Staff not getting pinged?**
- Add staff roles: `[p]reportset staffrole add @YourRole`
- Check role permissions and hierarchy
- Verify roles are mentionable

**Action buttons not working?**
- Ensure staff have "Moderate Members" permission
- Check bot has necessary permissions (timeout, ban, etc.)
- Verify user isn't higher in role hierarchy
- For Caution button: Ensure Cautions cog is loaded (`[p]load cautions`)

**Caution button shows error?**
- Load the Cautions cog: `[p]load cautions`
- Configure Cautions cog: `[p]cautionset` and `[p]setupmute`
- Check that warning thresholds are properly set up

**Context menu missing?**
- Context menus are not supported in older Red versions
- Use the reply method instead: Reply to the problematic message and use `[p]report @user reason`
- This provides the same functionality with message context

## Prerequisites

### Required Cogs
- **Cautions Cog** (optional but recommended): For the Caution button functionality
  - If not loaded, the Caution button will show an error message
  - Provides automatic threshold actions based on warning points
  - Handles warning expiry and comprehensive logging

### Bot Permissions
**Bot Permissions:**
- Send Messages (report channel)
- Embed Links (for report embeds)
- Moderate Members (for timeout action)
- Ban Members (for ban action)
- Manage Messages (for cleanup)
- Manage Roles (for Cautions cog mute integration)

**User Permissions:**
- None required for reporting
- Moderate Members required for action buttons
- Administrator required for configuration

## Integration with Cautions Cog

The Report cog seamlessly integrates with the Cautions cog to provide a comprehensive moderation workflow:

### Setup Integration
1. Install both cogs: `[p]cog install ultcogs report` and `[p]cog install ultcogs cautions`
2. Load both cogs: `[p]load report` and `[p]load cautions`
3. Configure Cautions: `[p]setupmute` and `[p]cautionset`
4. Configure Reports: `[p]reportset`

### How It Works
- **Caution Button**: When staff click "Caution" on a report, it opens a modal to add warning points
- **Automatic Thresholds**: Warning points are added to the user's total from the Cautions cog
- **Threshold Actions**: If the user reaches a configured threshold, automatic actions trigger (mute, timeout, kick, ban)
- **Unified Logging**: All actions are logged through the Cautions cog logging system
- **Expiry System**: Warnings added via reports follow the same expiry rules as the Cautions cog

### Benefits
- **Streamlined Workflow**: Handle reports and warnings in one interface
- **Consistent Enforcement**: All warnings use the same point system and thresholds
- **Automatic Escalation**: Problem users automatically face increasing consequences
- **Complete Audit Trail**: All actions are logged with case numbers and details

## Advanced Features
### Custom Cooldowns
```
[p]reportset cooldown 0      # No cooldown
[p]reportset cooldown 180    # 3 minutes
[p]reportset cooldown 600    # 10 minutes
```

### Multiple Staff Roles
Add multiple roles for comprehensive coverage:
```
[p]reportset staffrole add @Moderators
[p]reportset staffrole add @Admins
[p]reportset staffrole add @SeniorStaff
```

### Blacklist Management
Manage users who abuse the system:
```
[p]reportset blacklist add @Abuser      # Block from reporting
[p]reportset blacklist remove @Reformed # Unblock user
[p]reportset blacklist list             # View all blacklisted
```

## Data Storage

The cog stores:
- **Guild Settings**: Channel IDs, role IDs, configuration
- **User Data**: Last report time, total reports made, blacklist status
- **No Personal Data**: Only Discord IDs and report metadata

## Support

For issues or feature requests:
- GitHub: https://github.com/AfterWorld/ultcogs
- Create an issue with detailed description
- Include error logs if applicable

## Changelog

### v1.0.0
- Initial release
- Command and context menu reporting
- Staff quick action buttons
- Comprehensive configuration system
- Anti-abuse protection
- Detailed logging system
