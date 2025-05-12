# OnePieceEvents

A specialized Red Discord Bot cog for managing One Piece themed events in your server. Schedule and organize watch parties, manga discussions, theory crafting sessions, and more!

## Features

- **One Piece Themed Events**: Choose from 12 different One Piece specific event types
- **Automated Reminders**: 30-minute reminders before events start
- **Role Mentions**: Optionally mention roles when events are starting
- **Event Management**: Create, edit, cancel, and view event information
- **Participant Tracking**: See who's attending your events with reaction-based joining
- **DM Notifications**: Participants receive DM reminders about events

## Event Types

- **Watch Party**: Gather your crew to watch episodes together
- **Manga Discussion**: Discuss the latest manga chapters
- **Theory Crafting**: Share and debate theories about One Piece
- **Quiz Night**: Test your knowledge of the One Piece universe
- **Character Analysis**: Deep dive into specific characters
- **Devil Fruit Discussion**: Talk about various Devil Fruits and their powers
- **Bounty Predictions**: Predict future bounty changes
- **Cosplay Showcase**: Share One Piece cosplays
- **AMV Sharing**: Share Anime Music Videos
- **Episode Release**: Discuss newly released episodes
- **Manga Chapter Release**: Discuss newly released manga chapters
- **Other**: For any other One Piece related events

## Commands

- `[p]events create <event_type> <name> <time> [description]` - Create a new event
- `[p]events list` - List all upcoming events
- `[p]events join <event_id>` - Join an event
- `[p]events leave <event_id>` - Leave an event
- `[p]events cancel <event_id>` - Cancel an event
- `[p]events info <event_id>` - Get detailed information about an event
- `[p]events edit <event_id> <field> <new_value>` - Edit an event

## Setup

1. Install the cog with `[p]repo add onepieceevents https://github.com/AfterWorld/ultcogs`
2. Install the cog with `[p]cog install onepieceevents`
3. Load the cog with `[p]load onepieceevents`

## Examples

### Creating a Watch Party

```
[p]events create "Watch Party" "Whole Cake Island Arc" "15/05/2025 19:30" Join us as we watch episodes 783-800!
```

### Creating a Manga Discussion

```
[p]events create "Manga Discussion" "Chapter 1000 Analysis" "20/05/2025 20:00" Let's talk about this milestone chapter and its revelations!
```

### Editing an Event

```
[p]events edit 1 time 21/05/2025 19:00
```

## Permission Requirements

- Moderators or users with the manage_events permission can create, edit, and cancel events
- Regular users can join and leave events, and view event information

## Notes

- Event times are in 24-hour format (HH:MM)
- Event dates are in DD/MM/YYYY format
- Reminders are sent 30 minutes before events start
- Past events are automatically cleaned up 1 hour after they end
