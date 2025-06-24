# Suggestion System v2.0

A modern, feature-rich suggestion system for Discord communities built for Red-DiscordBot. This cog provides a comprehensive solution for collecting, voting on, and managing community suggestions with a sleek button-based interface.

## ✨ Features

### 🗳️ **Modern Button Voting**
- Interactive upvote/downvote buttons (no more emoji reactions!)
- Real-time vote count updates
- Users can change their votes by clicking buttons again
- Authors cannot vote on their own suggestions
- Persistent buttons that work even after bot restarts

### 👨‍⚖️ **Staff Management**
- Approve/deny suggestions with dedicated staff buttons
- Optional reason modals for approval/denial decisions
- Automatic notification system (DM users when suggestions are processed)
- Bulk denial commands for cleanup
- Comprehensive logging system

### 🛡️ **Moderation Tools**
- User blacklisting system with reasons and timestamps
- Configurable suggestion length limits
- User cooldowns to prevent spam
- Message cleanup in suggestion channels
- Anonymous suggestion support

### 📊 **Analytics & Tracking**
- Detailed suggestion statistics per user
- Server-wide analytics dashboard
- Search functionality across all suggestions
- Vote tracking and approval rate calculations
- Activity monitoring and reporting

### ⚙️ **Highly Configurable**
- Customizable upvote thresholds for staff review
- Flexible channel setup (suggestion, staff, logging)
- Optional features (DM notifications, cleanup, anonymous suggestions)
- Length limits and cooldown periods
- Comprehensive settings overview

## 🚀 Installation

### Prerequisites
- Red-DiscordBot v3.5.0 or higher
- Python 3.8+

### Installation Steps

1. **Add the repository**:
   ```
   [p]repo add ultcogs https://github.com/AfterWorld/ultcogs
   [p]cog install ultcogs suggestion
   ```

2. **Or load directly** (if you have the files):
   ```
   [p]load suggestion
   ```

3. **Initial Setup**:
   ```
   [p]suggestionset channel #suggestions
   [p]suggestionset staffchannel #staff-review
   ```

## 📖 Quick Start Guide

### Basic Setup
```bash
# Set the suggestion channel
[p]suggestionset channel #suggestions

# Set the staff review channel
[p]suggestionset staffchannel #staff-review

# Optional: Set a logging channel
[p]suggestionset logchannel #suggestion-logs

# Configure vote threshold (default: 5)
[p]suggestionset threshold 10
```

### User Commands
```bash
# Submit a suggestion
[p]suggest Add a music channel for sharing songs

# View suggestion help
[p]suggesthelp

# Check your suggestion stats
[p]suggestionstats

# View a specific suggestion
[p]showsuggestion 5

# List all suggestions
[p]listsuggestions

# Search suggestions
[p]searchsuggestions music channel
```

### Staff Commands
```bash
# Approve a suggestion
[p]approve 5 Great idea! We'll implement this soon.

# Deny a suggestion  
[p]deny 5 This doesn't fit our current plans.

# Delete a suggestion completely
[p]deletesuggestion 5 Inappropriate content

# Bulk deny multiple suggestions
[p]bulkdeny 1 2 3 4 5 Cleaning up old suggestions

# View system analytics
[p]suggestioninfo
```

### Blacklist Management
```bash
# Add user to blacklist
[p]suggestblacklist add @user Spam/inappropriate suggestions

# Remove user from blacklist
[p]suggestblacklist remove @user

# View blacklisted users
[p]suggestblacklist list

# Check blacklist info for specific user
[p]suggestblacklist info @user
```

## ⚙️ Configuration Options

### Channel Settings
- **Suggestion Channel**: Where suggestions are posted for voting
- **Staff Channel**: Where approved suggestions go for staff review
- **Log Channel**: Where all system actions are logged

### Voting & Approval
- **Upvote Threshold**: Number of upvotes needed to send to staff (1-50)
- **Require Reason**: Whether staff must provide reasons for approval/denial

### Content Limits
- **Min Length**: Minimum characters required (5-4000)
- **Max Length**: Maximum characters allowed (5-4000)
- **Cooldown**: Time between suggestions per user (0-86400 seconds)

### Optional Features
- **Cleanup**: Auto-delete non-suggestion messages in suggestion channel
- **DM Notifications**: Send users DMs when suggestions are processed
- **Anonymous Suggestions**: Allow users to submit suggestions anonymously

### View All Settings
```bash
[p]suggestionset settings
```

## 🎯 How It Works

### 1. **Suggestion Submission**
Users submit suggestions using `[p]suggest <content>`. The bot validates the content and creates an embed with voting buttons.

### 2. **Community Voting**
Users vote using **Upvote** and **Downvote** buttons. Vote counts are tracked and displayed in real-time.

### 3. **Staff Review**
When a suggestion reaches the upvote threshold, it's automatically forwarded to the staff channel with approve/deny buttons.

### 4. **Processing**
Staff can approve or deny suggestions using buttons (with optional reasons) or commands. The original suggestion is updated with the decision.

### 5. **Notifications**
Users are notified via DM when their suggestions are processed (if enabled).

## 🔧 Advanced Configuration Examples

### High-Traffic Server Setup
```bash
[p]suggestionset threshold 20        # Higher threshold
[p]suggestionset cooldown 900        # 15-minute cooldown
[p]suggestionset minlength 50        # Longer minimum length
[p]suggestionset cleanup true        # Keep channel clean
```

### Casual Community Setup
```bash
[p]suggestionset threshold 3         # Lower threshold
[p]suggestionset cooldown 300        # 5-minute cooldown
[p]suggestionset minlength 10        # Shorter minimum
[p]suggestionset requirereason false # Optional reasons
```

### Anonymous Suggestion Setup
```bash
[p]suggestionset anonymous true      # Allow anonymous suggestions
[p]suggestionset dmnotifications false # Disable DMs for anonymous
```

## 📊 Analytics Dashboard

The `[p]suggestioninfo` command provides comprehensive analytics:

- **Statistics**: Total suggestions, approval rates, vote counts
- **System Health**: Channel setup status, feature status
- **Top Contributors**: Most active suggestion submitters  
- **Recent Activity**: New suggestions in the last 7 days
- **Moderation Stats**: Blacklisted user count

## 🛠️ Troubleshooting

### Common Issues

**Buttons not working after bot restart**
- This is normal - the bot uses persistent views that automatically reconnect

**Users can't vote**
- Check bot permissions in suggestion channel
- Ensure users have "Use External Emojis" permission

**Staff buttons not responding**
- Verify staff have "Manage Guild" or "Administrator" permissions
- Check bot permissions in staff channel

**Suggestions not forwarding to staff**
- Verify staff channel is set: `[p]suggestionset staffchannel #channel`
- Check upvote threshold: `[p]suggestionset settings`

### Required Permissions

**Suggestion Channel:**
- Send Messages
- Embed Links  
- Read Message History
- Use External Emojis

**Staff Channel:**
- Send Messages
- Embed Links

**Log Channel:**
- Send Messages
- Embed Links

## 🔄 Migration from v1.x

If upgrading from a reaction-based version:

1. **Existing suggestions** will automatically work with the new button system
2. **Vote counts** are preserved during the transition
3. **Configuration** remains the same (some new options available)
4. **No database migration** required

## 📝 Changelog

### v2.0.0 - Button Interface Modernization
- **NEW**: Complete button-based voting system
- **NEW**: Interactive staff approval buttons
- **NEW**: Persistent views that survive bot restarts
- **NEW**: Real-time vote count updates
- **NEW**: Enhanced vote tracking with user IDs
- **REMOVED**: Emoji reaction-based voting
- **IMPROVED**: Modern Discord UI standards
- **IMPROVED**: Better permission handling
- **IMPROVED**: Enhanced analytics and search

### v1.x - Legacy Reaction System
- Emoji reaction-based voting
- Basic staff commands
- Core suggestion functionality

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:

- Bug fixes
- Feature enhancements  
- Documentation improvements
- Performance optimizations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💬 Support

For support, questions, or feature requests:

- Open an issue on GitHub
- Join the Red-DiscordBot support server
- Check the Red-DiscordBot documentation

## 🙏 Credits

- Built for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot)
- Utilizes Discord.py's modern UI components
- Inspired by community feedback and modern Discord UX patterns

---

**Made with ❤️ for the Discord community**
