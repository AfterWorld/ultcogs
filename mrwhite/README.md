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

## Installation

1. Copy the entire cog folder to your Red bot's cogs directory
2. Load the cog: `[p]load mrwhite`

## Commands

- `[p]mrwhite start` - Start a new game in the current channel
- `[p]mrwhite join` - Join the current game
- `[p]mrwhite begin` - Begin the game (minimum 3 players required)
- `[p]mrwhite say <word>` - Say your word association during a round
- `[p]mrwhite vote @player` - Vote for who you think is Mr. White
- `[p]mrwhite guess <word>` - Mr. White's final guess (only for Mr. White)
- `[p]mrwhite end` - End the current game
- `[p]mrwhite addword <word>` - Add a word to the word pool
- `[p]mrwhite removeword <word>` - Remove a word from the word pool
- `[p]mrwhite words` - View all available words

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
