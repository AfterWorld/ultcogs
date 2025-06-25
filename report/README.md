# AdvancedReport - Comprehensive Discord Reporting System

A sophisticated Red-DiscordBot cog that provides a complete reporting system with both traditional commands and modern Discord context menus, featuring staff quick-action buttons and detailed logging.

## ✨ Features

### 🎯 Multiple Report Methods
- **Text Command**: `[p]report @user reason` - Traditional command-based reporting
- **Message ID**: `[p]reportmsg <message_id> reason` - Report specific messages by ID
- **Context Menu**: Right-click any message → Apps → "Report Message" - Modern Discord UI

### 🚀 Staff Quick Actions
Interactive buttons on every report for instant moderation:
- **🔇 Mute**: Timeout user (uses Discord's built-in timeout system)
- **🔨 Ban**: Permanently ban the reported user
- **⚠️ Caution**: Issue cautions using integrated Cautions cog system (with points, thresholds, auto-actions)
- **🚫 Blacklist Reporter**: Block false reporters
- **✅ Dismiss**: Mark report as resolved

### 🔗 Advanced Integrations
- **Cautions Cog Integration**: Seamlessly integrates with the Cautions cog for advanced warning systems
  - Uses point-based caution system with configurable thresholds
  - Automatic escalation actions (mute, timeout, kick, ban)
  - Warning expiry and detailed logging
  - Fallback system if Cautions cog is not available
- **Message Links**: Direct jump links to reported messages
- **Staff Pinging**: Configurable role notifications
- **Comprehensive Logging**: Detailed action history
- **Blacklist System**: Prevent abuse from repeat false reporters

## 📋 Installation

### From Git Repository
```bash
[p]repo add ultcogs https://github.com/AfterWorld/ultcogs
[p]cog install ultcogs AdvancedReport
[p]load AdvancedReport
```

### Manual Installation
1. Download the cog files to your Red instance
2. Place in `[red_data_path]/cogs/AdvancedReport/`
3. Load with `[p]load AdvancedReport`

## ⚙️ Configuration

### Required Setup
```bash
# Set the channel where reports are sent
[p]reportset channel #reports

# Add staff roles that can handle reports
[p]reportset staffroles @Moderator @Admin

# Optional: Set up logging
[p]reportset logchannel #mod-logs
```

### Advanced Configuration
```bash
# Configure default mute duration (in minutes)
[p]reportset muteduration 60

# Set default caution points for reports (requires Cautions cog)
[p]reportset cautionpoints 2

# Check integration status with other cogs
[p]reportset integration

# View all current settings
[p]reportset view
```

### Cautions Cog Integration
If you have the Cautions cog installed, the report system will automatically integrate:

```bash
# Install and configure Cautions cog first
[p]load cautions
[p]cautionset expiry 30  # Cautions expire after 30 days
[p]cautionset setthreshold 3 mute 60  # Mute for 60 minutes at 3 points
[p]cautionset setthreshold 5 timeout 120  # Timeout for 2 hours at 5 points
[p]cautionset setthreshold 10 kick  # Kick at 10 points

# Then configure report system integration
[p]reportset cautionpoints 2  # Each report caution gives 2 points
```

## 🎮 Usage

### For Regular Users

#### Text Commands
```bash
# Report a user with reason
[p]report @BadUser They were spamming the chat

# Report a specific message by ID
[p]reportmsg 123456789012345678 This message contains inappropriate content
```

#### Context Menu (Recommended)
1. Right-click on any message
2. Select "Apps" → "Report Message"
3. Fill in the reason in the popup modal
4. Submit the report

### For Staff Members

#### Handling Reports
When a report is submitted, staff will see an embed with:
- **Report ID**: Unique identifier for tracking
- **Reported User**: Full user details and mention
- **Reporter**: Who submitted the report
- **Reason**: Detailed explanation
- **Message Link**: Direct link to the reported content (if applicable)
- **Quick Action Buttons**: Instant moderation tools

#### Quick Actions
Click any button on a report to take immediate action:
- **Mute**: Applies Discord timeout (duration configurable)
- **Ban**: Permanently removes user from server
- **Caution**: Issues caution with points (integrates with Cautions cog if available)
- **Blacklist Reporter**: Prevents user from making future reports
- **Dismiss**: Marks report as resolved

#### Integration Commands
```bash
# Check integration status with other cogs
[p]reportset integration

# Check a user's caution history (staff only)
[p]reportcautions @user

# Configure caution points for reports
[p]reportset cautionpoints 2
```

#### Administrative Commands
```bash
# Configure system settings
[p]reportset channel #new-reports-channel
[p]reportset staffroles @NewRole @AnotherRole
[p]reportset logchannel #audit-log

# View configuration
[p]reportset view

# Set mute duration (uses Discord timeout)
[p]reportset muteduration 120  # 2 hours
```

## 🔧 Advanced Configuration

### Permission Requirements
- **Bot Permissions**: 
  - Send Messages, Embed Links, Manage Messages
  - Moderate Members (for timeout functionality)
  - Ban Members (for ban functionality)

- **Staff Permissions**:
  - Must have configured staff roles OR Administrator permission
  - Individual permissions checked for each action

### Database Schema
The cog stores data in Red's Config system and integrates with Cautions cog:

#### Guild Settings
```python
{
    "report_channel": 123456789,      # Channel ID for reports
    "staff_roles": [123, 456],        # List of staff role IDs
    "log_channel": 987654321,         # Channel for action logs
    "default_mute_duration": 60,      # Minutes for timeouts
    "blacklisted_users": [789],       # Users blocked from reporting
    "ping_staff": true,               # Whether to ping staff roles
    "require_reason": true,           # Require reason for reports
    "default_caution_points": 1       # Points per caution (Cautions integration)
}
```

#### Member Data (Compatible with Cautions cog)
```python
{
    "warnings": [                     # Caution/warning history
        {
            "reason": "Report: Spam",
            "moderator": 123456,       # Moderator ID
            "timestamp": "2024-01-01T12:00:00+00:00",
            "report_id": "RPT-000001"
        }
    ],
    "report_count": 5,                # Number of reports made by user
    "total_points": 8,                # Total caution points (Cautions integration)
    "applied_thresholds": [3, 5]      # Applied thresholds (Cautions integration)
}
```

## 🛡️ Security Features

### Anti-Abuse Measures
- **Blacklist System**: Prevents repeat false reporters
- **Self-Report Protection**: Users cannot report themselves
- **Bot Protection**: Prevents reporting of bot accounts
- **Staff Protection**: Staff members cannot be reported through the system

### Data Privacy
- **Ephemeral Responses**: Error messages are private
- **Command Cleanup**: Original report commands are deleted
- **DM Confirmations**: Users receive private confirmations

### Audit Trail
- **Comprehensive Logging**: All actions logged with timestamps
- **Moderator Attribution**: Every action tracks who performed it
- **Report IDs**: Unique identifiers for tracking and appeals

## 🔄 Workflow Example

1. **User Reports**: Uses context menu or command to report inappropriate behavior
2. **Staff Notification**: Configured staff roles are pinged with report details
3. **Quick Action**: Staff member clicks appropriate button (mute, ban, caution, etc.)
4. **Automatic Processing**: 
   - Action is performed (user muted/banned/cautioned)
   - **Cautions Integration**: If Cautions cog is loaded, points are added and thresholds checked
   - User is notified via DM (for cautions)
   - Action is logged to audit channel
   - Report is marked as processed
5. **Threshold Actions**: If using Cautions cog, automatic escalation may trigger (additional mute, kick, ban)
6. **Follow-up**: Additional actions can be taken manually if needed

## 🐛 Troubleshooting

### Common Issues

#### Reports Not Appearing
- Verify report channel is set: `[p]reportset view`
- Check bot permissions in report channel
- Ensure bot can see the configured channel

#### Buttons Not Working
- Verify user has staff role configured in `[p]reportset staffroles`
- Check bot permissions for the intended action
- Ensure target user is still in the server

#### Context Menu Missing
- Restart Discord client
- Verify bot has application command permissions
- Check if command is disabled in server settings

### Error Messages
- **"You are blacklisted"**: User has been blocked from reporting
- **"Cannot report staff members"**: Target has staff permissions
- **"Message not found"**: Message ID is invalid or bot cannot access it
- **"No permission"**: Bot lacks required permissions for the action

#### Cautions Integration Issues
- **"Cautions cog not available"**: Install the Cautions cog for advanced warning features
- **"Error accessing caution data"**: Check if Cautions cog is properly configured
- **Points not applying**: Verify Cautions cog settings with `[p]cautionset showthresholds`

#### Integration Status
- **Check integration**: Use `[p]reportset integration` to see what cogs are available
- **Cautions not detected**: Ensure Cautions cog is loaded with `[p]load cautions`

## 📝 Changelog

### Version 1.1.0
- **🔗 Cautions Cog Integration**: Seamless integration with existing Cautions warning system
- **📊 Point-Based Cautions**: Configurable caution points for reports with automatic threshold actions
- **🔍 Enhanced User Lookup**: `[p]reportcautions` command to check user caution history
- **⚙️ Integration Status**: `[p]reportset integration` to check available cog integrations
- **🔄 Intelligent Fallback**: Automatic fallback to simple warning system if Cautions cog unavailable
- **🎯 Configurable Points**: `[p]reportset cautionpoints` to set default points per report
- **⏰ Discord Timeout Integration**: Uses Discord's built-in timeout system instead of mute roles

### Version 1.0.0
- Initial release with core reporting functionality
- Context menu and command-based reporting
- Staff quick action buttons
- Comprehensive configuration system
- Warning and blacklist systems
- Audit logging capabilities

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve this cog at: https://github.com/AfterWorld/ultcogs

## 📄 License

This cog is provided under the same license as Red-DiscordBot.

---

*For additional support, please refer to the Red-DiscordBot documentation or community Discord server.*
