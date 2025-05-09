# OPTCG Installation Guide

This guide will help you set up the One Piece TCG Game cog properly on your Red Discord bot.

## Prerequisites

- Red-DiscordBot v3.5+
- Python 3.8+ 
- Admin/owner permissions on your bot

## Installation Steps

1. **Install Required Dependencies**

   First, install the Pillow library which is needed for image processing:
   ```
   [p]pip install pillow
   ```

2. **Install the Cog**

   You have two options:

   **Option A**: Install from a repository (if hosted)
   ```
   [p]repo add optcg-cog https://github.com/AfterWorld/ultcogs
   [p]cog install optcg-cog optcg
   ```

   **Option B**: Manual installation
   - Download the cog files
   - Place them in a folder called `optcg` inside your Red bot's cogs directory
   - Install directly with:
   ```
   [p]cog install optcg
   ```

3. **Load the Cog**
   ```
   [p]load optcg
   ```

## Initial Setup

1. **Enable the Game in a Channel**
   ```
   [p]optcg enable #channel-name
   ```
   This sets the channel where cards will randomly spawn.

2. **Test the Setup**
   ```
   [p]optcg spawn
   ```
   This admin command forces a card to spawn to make sure everything is working correctly.

3. **Optional Configuration**
   - Adjust spawn rate: `[p]optcg admin spawnrate 0.2` (sets to 20%)
   - Change spawn cooldown: `[p]optcg admin cooldown 120` (sets to 2 minutes)

## Common Issues

### Cards Not Spawning

- Make sure the cog is enabled: `[p]cog list`
- Verify the spawn channel is set: `[p]optcg enable #channel-name`
- Check that the bot has proper permissions in the channel
- Try increasing the spawn rate temporarily for testing: `[p]optcg admin spawnrate 0.5`

### Image Processing Issues

If you see error messages related to image processing (silhouette creation):
- Make sure Pillow is properly installed: `[p]pip install pillow --upgrade`
- Cards will still spawn with regular images if silhouette processing fails

### Claim Button Not Working

- Ensure the bot has permissions to create and use message components
- Update your bot to the latest version as button support requires newer Discord.py versions

## Updating

To update the cog when new versions are available:
```
[p]cog update optcg
```

## Need Help?

If you encounter any issues during installation or usage:
- Check the full documentation in the README.md file
- Join the Red Discord for community support
- Contact the cog developer for specific help

Enjoy collecting and battling with One Piece cards!
