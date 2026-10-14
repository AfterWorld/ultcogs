# OnePieceGuess

A Red-DiscordBot cog for timed One Piece image guessing rounds. The bot posts a blurred or pixelated image from the One Piece Wiki. Players answer with a slash/prefix command or the **Make a Guess** button, which opens a Discord modal.

## Install

```text
[p]repo add ults https://github.com/AfterWorld/ultcogs
[p]cog install ults onepieceguess
[p]load onepieceguess
[p]opguess setchannel #one-piece-game
[p]opguess toggle true
```

Requires Red 3.5.24+, Python 3.11+, `aiohttp`, and Pillow 10+.

## Play

- `[p]guess Monkey D. Luffy` or `/guess Monkey D. Luffy`
- Or press **Make a Guess** on the round embed and submit your answer in the modal.
- `[p]opguess stats [member]` shows wins; `[p]opguess top` shows the server leaderboard.

The cog supports character, Devil Fruit, and ship pools. Each server keeps its own settings, pools, active round, and leaderboard. Its timer state survives a bot restart; an active round resumes with the remaining time.

## Admin commands

`opguess` commands require Administrator permission.

| Command | What it does |
| --- | --- |
| `opguess` | Show current settings and active round |
| `opguess toggle [true/false]` | Enable or pause new rounds |
| `opguess setchannel <channel>` | Set where rounds are posted |
| `opguess mode <character/fruit/ship>` | Choose the pool to play |
| `opguess setinterval <seconds>` | Set delay after a round (30–86400) |
| `opguess setroundtime <seconds>` | Set answer deadline (15–3600) |
| `opguess setreward <amount>` | Set BeriCore reward; zero chooses a random configured amount |
| `opguess setberirange <min> <max>` | Configure random Beri reward range |
| `opguess blur <gaussian/pixelate> [strength]` | Set image effect |
| `opguess requireimage [true/false]` | Require an image in the current mode |
| `opguess hints [true/false]` | Enable or disable custom clues |
| `opguess char [add/remove/aliases] ...` | View or manage the current mode's pool |
| `opguess clue <entry> <text>` | Set a spoiler-safe custom clue |
| `opguess import` | Replace the current pool from an attached JSON file |
| `opguess export` | Download the current pool as JSON |
| `opguess forcepost [entry]` | Start a round immediately |
| `opguess end` | End the current round and reveal the answer |

JSON import accepts a list of names, or an object such as:

```json
{
  "entries": ["Monkey D. Luffy", "Roronoa Zoro"],
  "aliases": {"Monkey D. Luffy": ["Luffy", "Straw Hat"]},
  "hints": {"Monkey D. Luffy": "A rubber-powered captain."}
}
```

## Notes

- Fandom/Wiki API availability and the quality of its page images vary. The cog retries missing images and can be configured to skip image-less entries.
- The game does not show the wiki introduction as a clue because it often gives away the answer. Only configured custom clues are shown.
- Beri rewards are optional and require the `BeriCore` cog to be loaded. Without it, wins still count and the game continues normally.
