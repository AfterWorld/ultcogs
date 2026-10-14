# OnePieceGuess

A Red-DiscordBot cog for timed One Piece image guessing rounds. The bot loads a blurred or pixelated image and page intro from the One Piece Wiki. Every round requires a successfully loaded image. Players answer with the bot’s prefix command; the round embed includes a hint and no buttons.

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

- `[p]guess Monkey D. Luffy`
- `[p]opguess stats [member]` shows wins; `[p]opguess top` shows the server leaderboard.
- When enabled, correct guesses award points to the winner's team through the installed `Teams` cog.

The cog supports character, Devil Fruit, and ship pools. Each server keeps its own settings, pools, active round, and leaderboard. Its timer state survives a bot restart; an active round resumes with the remaining time. Existing server pools from the original `GuessEngine` config are reused, and entries from the first recreation are merged into them on upgrade.

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
| `opguess requireimage` | Confirm image-only posting is enforced in every mode |
| `opguess hints [true/false]` | Enable or disable custom clues (wiki intro is used when no custom clue is set) |
| `opguess teamapi` | Show team scoring settings |
| `opguess teamapi toggle [true/false]` | Enable or disable team points through the `Teams` cog |
| `opguess teamapi setpoints <points> [timeout_points]` | Set points for correct guesses and timeouts |
| `opguess char [add/remove/aliases] ...` | View or manage the current mode's pool |
| `opguess clue <entry> <text>` | Set a spoiler-safe custom clue |
| `opguess import` | Replace the current pool from an attached JSON file |
| `opguess export` | Download the current pool as JSON |
| `opguess forcepost [entry]` | Start a round immediately |
| `opguess testimage [entry]` | Test Fandom lookup and image processing from the bot host |
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

- Fandom/Wiki API availability and page image quality vary. The cog checks several pool entries and skips the round if it cannot fetch and process an image; it never posts an image-less question. Admins can run `[p]opguess testimage <entry>` to diagnose API or image-host access from the bot host.
- If no custom clue is configured, the game uses a short wiki intro hint and removes the answer and configured aliases when possible. Custom clues give admins control over spoiler safety.
- Beri rewards are optional and require the `BeriCore` cog. Team scoring is separately configured and uses the `Teams` cog (and `BeriAmplifier` when available).
