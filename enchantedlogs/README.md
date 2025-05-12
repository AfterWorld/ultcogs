# EnhancedModlog Cog for Red-DiscordBot

A enhanced moderation logging cog for Red-DiscordBot v3 that adds rich embeds and interactive buttons to your moderation logs.

## Features

- **Rich Moderation Log Embeds**: Beautifully formatted embeds for all moderation actions
- **Interactive Buttons**: Perform moderation actions directly from log messages
  - Unban users with a single click
  - Unmute users with a single click
  - View a user's complete moderation history
- **Customizable**: Configure log channels, colors, and included information
- **Works with existing moderation commands**: Seamlessly enhances Red's built-in moderation functionality

## Installation

To install the cog, use the following commands:

```
[p]repo add enhanced-modlog https://github.com/AfterWorld/ultcogs
[p]cog install enhanced-modlog
[p]load enhancedmodlog
```

## Setup

1. Set the channel to send enhanced modlogs to:
   ```
   [p]enhancedmodlog channel #your-modlog-channel
   ```

2. Toggle interactive buttons (enabled by default):
   ```
   [p]enhancedmodlog buttons true
   ```

3. View your current settings:
   ```
   [p]enhancedmodlog settings
   ```

## Usage

Once set up, the cog will automatically enhance all moderation cases with rich embeds and interactive buttons in your designated modlog channel.

### Available Buttons

- **Unban User**: Available on ban cases, instantly unbans the user
- **Unmute User**: Available on mute cases, instantly unmutes the user
- **Voice Unmute**: Available on voice mute cases, instantly unmutes the user in voice
- **View User Modlogs**: Available on all cases, shows a summary of the user's moderation history

## Permissions

Moderators need the appropriate permissions to use the interactive buttons:
- To use unban/unmute buttons: Ban Members permission or the bot's Moderator role
- To view user modlogs: No special permissions required, but the information is shown only to the user who clicked the button

## Support

If you encounter any issues or have suggestions, please open an issue on the GitHub repository.

## License

Released under the MIT License. See the LICENSE file for details.
