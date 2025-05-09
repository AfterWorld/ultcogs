# One Piece TCG Game (OPTCG)

A Discord bot cog for Red-DiscordBot that creates a Pokemon-inspired card collection game using One Piece Trading Card Game cards. Collect cards, build decks, and battle other players!

## Features

- **Card Collection**: Collect One Piece TCG cards that randomly spawn in your server
- **Silhouette System**: Cards initially appear as silhouettes, making it a fun guessing game
- **Battle System**: Build a deck with your collected cards and battle other players
- **Card Database**: Search for cards by name and view detailed card information
- **Starter Pack**: New players can claim a starter pack to begin their collection
- **Admin Controls**: Server admins can configure spawn rates, channels, and more

## Installation

To install this cog, you need to have a running Red-DiscordBot instance (v3.5+).

1. Install required libraries:
```
[p]pip install pillow
```

2. Add the repository to your bot:
```
[p]repo add optcg-cog [https://github.com/AfterWorld/ultcogs]
```

3. Install the cog:
```
[p]cog install optcg-cog optcg
```

4. Load the cog:
```
[p]load optcg
```

## Dependencies

This cog requires:
- Red-DiscordBot v3.5+
- Pillow (for image processing)
- aiohttp (comes with Red)

## Commands

### Basic Commands

- `.optcg` - Shows the help menu for all OPTCG commands
- `.optcg enable [channel]` - Enable card spawning in a specific channel (admin only)
- `.optcg disable` - Disable card spawning in the server (admin only)
- `.optcg claim` - Claim the currently spawned card
- `.optcg starter` - Claim your starter pack (one-time)
- `.optcg collection [user]` - View your card collection or another user's
- `.optcg card <card_id>` - View detailed information about a specific card
- `.optcg search <name>` - Search for cards by name

### Battle System

- `.optcg deck <card_ids...>` - Set up your battle deck (up to 5 cards)
- `.optcg viewdeck [user]` - View your battle deck or another user's
- `.optcg battle <user>` - Challenge another user to a battle
- `.optcg stats [user]` - View battle statistics

### Admin Commands

- `.optcg admin spawnrate <rate>` - Set the card spawn rate (0.0 to 1.0)
- `.optcg admin cooldown <seconds>` - Set the cooldown between card spawns
- `.optcg admin reset <user>` - Reset a user's OPTCG data (use with caution!)
- `.optcg spawn` - Force spawn a card (admin only)

## Getting Started

1. Enable the cog in your server: `.optcg enable #channel-name`
2. Claim your starter pack: `.optcg starter`
3. Cards will randomly spawn in the designated channel - claim them with the button or `.optcg claim`
4. Build your collection and create a battle deck: `.optcg deck <card_ids...>`
5. Challenge other players to battles: `.optcg battle @user`

## About Card Spawning

Cards will spawn randomly when users chat in the designated channel. The default spawn rate is 15% per message with a 60-second cooldown between spawns.

When a card spawns, it appears as a silhouette. Users must react quickly to claim it using the button or the `.optcg claim` command. Once claimed, the full card is revealed and added to the claimer's collection.

## Card Battles

Battles are turn-based and use card stats derived from the One Piece TCG properties:
- **Attack**: Based on the card's power value and rarity
- **Defense**: Derived from counter value or a percentage of attack
- **Health**: Based on cost and other card properties

Each battle consists of multiple rounds where cards from each player's deck are matched against each other.

## Credits

- Data provided by [API TCG](https://apitcg.com/api/one-piece/cards)
- Card images are property of Bandai/One Piece TCG
- Inspired by Pokecord and similar Discord bot games

## Support and Feedback

If you encounter any issues or have suggestions for improvements, please open an issue on GitHub or contact the developer on Discord.

Enjoy collecting and battling with One Piece cards!
