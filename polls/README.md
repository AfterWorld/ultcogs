# V2Poll

A Red-DiscordBot cog that creates interactive polls using Discord's Components V2 feature.

## Features

- Create interactive polls with up to 10 options
- Real-time vote tracking
- Customizable poll duration
- Automatic results when polls end
- Modern UI using Discord's Components V2

## Requirements

- Red-DiscordBot 3.5.0+
- Discord.py 2.0+ (with Components V2 support)
- Python 3.8+

## Installation

1. Make sure your bot has Components V2 support (Discord.py 2.0+ with the Components V2 PR merged)
2. Add the repository to your bot:
   ```
   [p]repo add v2poll-cog [repository URL]
   ```
3. Install the cog:
   ```
   [p]cog install v2poll-cog v2poll
   ```
4. Load the cog:
   ```
   [p]load v2poll
   ```

## Commands

### Poll Management

- `[p]poll create "Question" [duration] option1 option2 ...` - Create a new poll
- `[p]poll list` - List all active polls on the server
- `[p]poll end <message_id>` - End a poll early and display results
- `[p]quickpoll "Question" option1 option2 ...` - Create a poll with default duration

### Settings

- `[p]poll settings` - Show current poll settings
- `[p]poll settings duration <minutes>` - Set the default poll duration

## Examples

Create a simple 30-minute poll:
```
[p]poll create "What's your favorite color?" 30 Red Blue Green Yellow
```

Create a quick poll with the server's default duration:
```
[p]quickpoll "Best movie?" "The Matrix" "Star Wars" "Inception"
```

Set the default poll duration to 2 hours:
```
[p]poll settings duration 120
```

## Notes

- Components V2 is a new Discord feature, so older versions of Discord.py may not support it
- The cog will automatically provide a fallback message if Components V2 is not available
- Users can vote by clicking the "Vote" button next to their preferred option
- Users can change their vote at any time before the poll ends

## License

This cog is released under the MIT License. See LICENSE file for details.

## Credits

- Developed by UltPanda
- Based on Discord Components V2 API
- Made for Red-DiscordBot community
