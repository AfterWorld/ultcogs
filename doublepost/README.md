# ConsecutiveFilter

A Red Discord Bot cog that prevents users from posting consecutive messages in specific channels. Ideal for advertising channels where you want to ensure users don't post multiple ads in a row.

## Features

- Prevent users from posting consecutive messages in specific channels
- Customizable message count threshold (default is 2 - the second consecutive message gets deleted)
- Option for time-based cooldown or requiring another user to post in between
- Automatic message deletion with customizable notification messages
- Notification channel for moderators
- Bypass options for moderators and bots
- Comprehensive configuration commands

## Installation

To install this cog, run the following commands:

```
[p]load downloader
[p]repo add consecutivefilter https://github.com/AfterWorld/ultcogs/consecutivefilter
[p]cog install consecutivefilter consecutivefilter
[p]load consecutivefilter
```

## Usage

### Basic Setup

1. Enable the cog: `[p]consecutivefilter toggle true`
2. Add a channel to monitor: `[p]consecutivefilter addchannel #channel-name`
3. Set a notification channel (optional): `[p]consecutivefilter notificationchannel #mod-log`

### Commands

All commands start with `[p]consecutivefilter` or the shortcut `[p]cf`.

- `toggle [true/false]` - Enable or disable the filter
- `addchannel [channels...]` - Add channels to monitor
- `removechannel [channels...]` - Remove channels from monitoring
- `notificationchannel [channel]` - Set a channel where notifications will be sent
- `cooldown [minutes]` - Set the cooldown time between messages from the same user
- `messagecount [count]` - Set how many consecutive messages will trigger the filter
- `modbypass [true/false]` - Set whether moderators bypass the filter
- `botbypass [true/false]` - Set whether bots bypass the filter
- `deletemessage [message]` - Set the message sent to users when their message is deleted
- `notificationmessage [message]` - Set the notification sent to the notification channel
- `settings` - Display current settings

### Examples

**Require another user to post between a user's messages:**
```
[p]cf cooldown 0
```

**Set a 30-minute cooldown between posts from the same user:**
```
[p]cf cooldown 30
```

**Allow a user to post 3 messages in a row before deletion:**
```
[p]cf messagecount 3
```

**Change the notification message:**
```
[p]cf notificationmessage {member} attempted to post multiple times in {channel}. Content: {message}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
