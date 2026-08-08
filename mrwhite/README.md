# Mr. White - Discord Game Cog

A social deduction word game for Red Discord Bot where players try to identify "Mr. White" who doesn't know the secret word.

## Game Rules

1. Players receive roles:
   - **Villagers**: Get a secret word
   - **Mr. White**: Gets nothing

2. Each round, players say a word associated with their secret word
   - Villagers try to give clues without being too obvious
   - Mr. White tries to blend in and figure out the word

3. After the round, everyone votes for who they think is Mr. White

4. If a villager is eliminated, they're out and the game continues

5. **Winning conditions:**
   - If Mr. White is voted out, they get ONE final guess at the word
     - If correct: Mr. White wins!
     - If wrong: Villagers win!
   - If Mr. White survives to the final 2 players: Mr. White wins!

6. **Tie votes:** if the vote is tied between two or more players (and more than 2 players are alive), everyone re-votes among just the tied players. If it's still tied after that (or only 2 players are alive), the tie is broken randomly and announced.

7. **Turn timers:** each phase auto-advances if players don't respond in time, so one AFK player can't stall the game forever — say phase (3 min), vote phase (2 min), and Mr. White's final guess (1.5 min) all have timeouts. Players who miss the window are skipped/counted as not voting.

## Installation

1. Copy the entire cog folder to your Red bot's cogs directory
2. Load the cog: `[p]load mrwhite`

## Commands

The `mrwhite` group can be shortened to `mw`, and each command below has a short alias so you don't have to type the full word every round.

- `[p]mrwhite start` (`new`) - Start a new game in the current channel
- `[p]mrwhite join` (`j`) - Join the current game
- `[p]mrwhite begin` (`b`) - Begin the game (minimum 3 players required)
- `[p]mrwhite say <word>` (`s`) - Say your word association during a round
- `[p]mrwhite vote @player` (`v`) - Vote for who you think is Mr. White
- `[p]mrwhite guess <word>` (`g`) - Mr. White's final guess (only for Mr. White)
- `[p]mrwhite end` (`stop`) - End the current game (game host, a player in the game, or a mod only)
- `[p]mrwhite addword <word>` - Add a word to the word pool
- `[p]mrwhite removeword <word>` - Remove a word from the word pool
- `[p]mrwhite words` - View all available words

For example, during a round you can just type `[p]mw s goal` instead of `[p]mrwhite say goal`.

## The Secret Word

The secret word is drawn once per game and stays the same for every round — villagers keep giving fresh clues about that one word until Mr. White is caught or survives. It's not supposed to change round to round; that's normal Mr. White gameplay, not a bug. Villagers get a DM reminder of the word when the game starts, and the round announcement notes it hasn't changed after round 1.

## Gameplay Flow

1. Someone starts a game: `[p]mrwhite start`
2. Players join: `[p]mrwhite join`
3. Host begins: `[p]mrwhite begin` (needs 3+ players)
4. Everyone gets DM'd their role and word (if villager)
5. Round starts - players say associations: `[p]mrwhite say goal`
6. When everyone has spoken, voting begins
7. Players vote: `[p]mrwhite vote @player`
8. Voted player is eliminated
9. If Mr. White, they get to guess the word
10. If not Mr. White, next round begins (or game ends if conditions met)

## Requirements

- Red-DiscordBot v3.5+
- discord.py 2.6.3+
- Python 3.11+

## Example Game

```
Player1: [p]mrwhite start
Bot: Game starting! Use [p]mrwhite join to join!

Player1: [p]mrwhite join
Player2: [p]mrwhite join
Player3: [p]mrwhite join
Bot: 3 players joined!

Player1: [p]mrwhite begin
Bot: Game starting! Check your DMs for your role!

[DMs sent - word is "football"]

Bot: Round 1! Say your associations!
Player1: [p]mrwhite say goal
Player2: [p]mrwhite say Messi
Player3: [p]mrwhite say shoot

Bot: Voting time!
Player1: [p]mrwhite vote @Player3
Player2: [p]mrwhite vote @Player3
Player3: [p]mrwhite vote @Player1

Bot: Player3 eliminated! Player3 was Mr. White!
Bot: Mr. White, make your final guess!

Player3: [p]mrwhite guess football
Bot: 🎉 Mr. White wins! Correct guess: football
```

## Notes

- Players must have DMs enabled to receive their roles
- Only one game can run per channel at a time
- The cog comes with a default word list that can be customized
