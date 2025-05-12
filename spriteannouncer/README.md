# SpriteAnnouncer Usage Guide

## Overview

SpriteAnnouncer is a Red-DiscordBot cog that creates interactive topic starters and announcements using character sprites from your GitHub repository. The cog randomly selects a sprite character and pairs it with a topic or announcement, presenting it to users with interactive buttons in a designated channel.

## Features

- **Random Timing**: Announcements appear at randomized intervals you can configure
- **Character Sprites**: Uses sprites from your GitHub repository
- **Interactive Buttons**: Users can request new topics or view character information
- **Customizable Content**: Add your own topics and announcements
- **Sprite Management**: Enable/disable specific sprites

## Installation

1. Make sure you have Red-DiscordBot V3.5+ installed
2. Install the cog repository:
   ```
   [p]repo add ultcogs https://github.com/AfterWorld/ultcogs
   ```
3. Install the SpriteAnnouncer cog:
   ```
   [p]cog install ultcogs spriteannouncer
   ```
4. Load the cog:
   ```
   [p]load spriteannouncer
   ```

## Initial Setup

1. **Set the announcement channel**:
   ```
   [p]spriteannouncer channel #your-channel
   ```

2. **Add some discussion topics**:
   ```
   [p]spriteannouncer topics add What's your favorite game and why?
   [p]spriteannouncer topics add If you could have any superpower for just 24 hours, what would you choose?
   [p]spriteannouncer topics add Share something interesting you learned recently.
   ```

3. **Add some announcements**:
   ```
   [p]spriteannouncer announcements add Welcome to our server's weekend event! Everyone is invited to join.
   [p]spriteannouncer announcements add Don't forget to check out our #rules channel for important server information.
   [p]spriteannouncer announcements add A friendly reminder that we have a movie night this Friday at 8 PM!
   ```

4. **Configure the announcement frequency**:
   ```
   [p]spriteannouncer frequency 60 240
   ```
   This sets announcements to appear randomly between 1-4 hours.

5. **Enable the announcer**:
   ```
   [p]spriteannouncer toggle true
   ```

## Command Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `[p]spriteannouncer toggle [true/false]` | Enable or disable the sprite announcer |
| `[p]spriteannouncer channel [#channel]` | Set the channel for announcements |
| `[p]spriteannouncer frequency [min] [max]` | Set min/max minutes between announcements |
| `[p]spriteannouncer trigger` | Manually trigger an announcement |
| `[p]spriteannouncer status` | Show current configuration status |

### Topic Management

| Command | Description |
|---------|-------------|
| `[p]spriteannouncer topics list` | List all configured topics |
| `[p]spriteannouncer topics add <text>` | Add a new discussion topic |
| `[p]spriteannouncer topics remove <index>` | Remove a topic by index number |

### Announcement Management

| Command | Description |
|---------|-------------|
| `[p]spriteannouncer announcements list` | List all configured announcements |
| `[p]spriteannouncer announcements add <text>` | Add a new announcement |
| `[p]spriteannouncer announcements remove <index>` | Remove an announcement by index number |

### Sprite Management

| Command | Description |
|---------|-------------|
| `[p]spriteannouncer sprites list` | List all enabled sprites |
| `[p]spriteannouncer sprites add <name>` | Add a sprite to the enabled list |
| `[p]spriteannouncer sprites remove <name>` | Remove a sprite from the enabled list |
| `[p]spriteannouncer sprites reset` | Reset to default sprite list |

## User Interaction

When an announcement is posted, users will see two buttons:

1. **New Topic**: Generates a new random topic immediately
2. **Character Info**: Shows information about the sprite character

These buttons make the announcements interactive and engage users in conversation.

## Sprite Files

The cog will use character sprites from your GitHub repository at `https://github.com/AfterWorld/ultcogs/tree/main/Character%20Sprite/`. 

By default, it will look for the following files:
- cat_sprite.png
- dog_sprite.png
- ghost_sprite.png
- robot_sprite.png
- slime_sprite.png

You can add more sprites to your repository, and they will be available for use in the cog.

## Tips and Best Practices

1. **Topic Quality**: Create engaging, open-ended topics that encourage conversation
2. **Frequency**: Find a balance that works for your server - too frequent and they become annoying, too infrequent and they lose impact
3. **Channel Selection**: Use a general chat channel where conversation naturally flows
4. **Sprite Variety**: Use a diverse set of character sprites to keep announcements visually interesting
5. **Regular Updates**: Add new topics and announcements periodically to keep content fresh

## Troubleshooting

If you encounter issues:

1. Ensure the bot has permission to send messages, embed links, and use external emojis in the designated channel
2. Check if the bot has access to your GitHub repository by triggering a manual announcement
3. Verify the correct setup with `[p]spriteannouncer status`
4. If sprites aren't loading, make sure your image filenames match exactly what you've configured

## Support

If you need assistance with this cog, please contact AfterWorld on Discord or open an issue in the GitHub repository.
