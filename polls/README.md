# V2Poll

A Red-DiscordBot cog that creates interactive polls with dropdown voting.

## Features

- Create interactive polls with up to 10 options
- Real-time vote tracking
- Customizable poll duration
- Automatic results when polls end

## Requirements

- Red-DiscordBot 3.5.24+
- Python 3.8.1 to 3.11, as required by Red 3.5.24

## Installation

1. Add the repository to your bot:
   ```
   [p]repo add v2poll-cog [[repository URL]](https://github.com/AfterWorld/ultcogs)
   ```
2. Install the cog:
   ```
   [p]cog install v2poll-cog v2poll
   ```
3. Load the cog:
   ```
   [p]load v2poll
   ```

## Commands

### Poll Management

- `[p]poll create "Question" [duration] option1 option2 ...` - Create a new poll
- `[p]poll list` - List all active polls on the server
- `[p]poll end <message_id>` - End a poll early and display results

### Settings

- `[p]poll settings` - Show current poll settings
- `[p]poll settings duration <minutes>` - Set the default poll duration

### Slash commands

`/poll create`, `/poll dropdown`, `/poll sprite`, `/poll list`, `/poll sprites` and `/poll end` are also available as slash commands. A bot owner enables them with `[p]slash enablecog polls`, then `[p]slash sync`. All other commands are prefix-only.

`/poll create` takes up to 10 options. `/poll dropdown` takes up to 23, because Discord limits a slash command to 25 parameters; the prefix version still takes 25. On Discord every option appears optional, and the "at least 2 options" check runs when the command is submitted.

## Examples

Create a simple 30-minute poll:
```
[p]poll create "What's your favorite color?" 30 Red Blue Green Yellow
```

Set the default poll duration to 2 hours:
```
[p]poll settings duration 120
```

## Notes

- Users can vote by choosing their preferred option from the poll's dropdown menu
- Users can change their vote at any time before the poll ends

## License

This cog is released under the MIT License. See LICENSE file for details.

## Credits

- Developed by UltPanda
- Made for Red-DiscordBot community
