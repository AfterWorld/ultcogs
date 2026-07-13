import discord
from redbot.core import commands, Config
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import random
import asyncio
from typing import Optional, List, Dict

class MrWhite(commands.Cog):
    """A social deduction word game - find Mr. White!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {
            "words": [
                "football", "basketball", "tennis", "pizza", "hamburger",
                "computer", "phone", "car", "plane", "tree", "flower",
                "ocean", "mountain", "river", "coffee", "tea", "music",
                "movie", "book", "cat", "dog", "bird", "fish", "house"
            ]
        }
        self.config.register_guild(**default_guild)
        self.games: Dict[int, 'Game'] = {}
    
    @commands.group(aliases=["mw"])
    @commands.guild_only()
    async def mrwhite(self, ctx):
        """Mr. White game commands"""
        pass

    @mrwhite.command(aliases=["new"])
    async def start(self, ctx):
        """Start a new Mr. White game"""
        if ctx.channel.id in self.games:
            await ctx.send("A game is already running in this channel!")
            return

        game = Game(ctx, self.config)
        self.games[ctx.channel.id] = game
        await game.start()

    @mrwhite.command(aliases=["j"])
    async def join(self, ctx):
        """Join the current game"""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is running in this channel!")
            return

        game = self.games[ctx.channel.id]
        await game.add_player(ctx.author)

    @mrwhite.command(aliases=["b"])
    async def begin(self, ctx):
        """Begin the game (minimum 3 players)"""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is running in this channel!")
            return

        game = self.games[ctx.channel.id]
        await game.begin_game()

    @mrwhite.command(aliases=["s"])
    async def say(self, ctx, *, word: str):
        """Say your word association"""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is running in this channel!")
            return

        game = self.games[ctx.channel.id]
        await game.player_say(ctx.author, word)

    @mrwhite.command(aliases=["v"])
    async def vote(self, ctx, member: discord.Member):
        """Vote for who you think is Mr. White"""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is running in this channel!")
            return

        game = self.games[ctx.channel.id]
        await game.vote(ctx.author, member)

    @mrwhite.command(aliases=["g"])
    async def guess(self, ctx, *, word: str):
        """Mr. White's final guess (only if you're Mr. White)"""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is running in this channel!")
            return

        game = self.games[ctx.channel.id]
        await game.mr_white_guess(ctx.author, word)

    @mrwhite.command(aliases=["stop"])
    async def end(self, ctx):
        """End the current game"""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is running in this channel!")
            return

        game = self.games[ctx.channel.id]

        is_participant = ctx.author == game.host or ctx.author in game.players
        is_mod = ctx.author.guild_permissions.manage_guild or await self.bot.is_mod(ctx.author)
        if not (is_participant or is_mod):
            await ctx.send(
                f"{ctx.author.mention} Only the game host, a player in the game, or a mod can end this game!"
            )
            return

        await game.end_game(f"Game ended by {ctx.author.display_name}")
    
    @mrwhite.command()
    async def addword(self, ctx, *, word: str):
        """Add a word to the word list"""
        async with self.config.guild(ctx.guild).words() as words:
            if word.lower() in [w.lower() for w in words]:
                await ctx.send(f"'{word}' is already in the word list!")
                return
            words.append(word.lower())
        await ctx.send(f"Added '{word}' to the word list!")
    
    @mrwhite.command()
    async def removeword(self, ctx, *, word: str):
        """Remove a word from the word list"""
        async with self.config.guild(ctx.guild).words() as words:
            try:
                words.remove(word.lower())
                await ctx.send(f"Removed '{word}' from the word list!")
            except ValueError:
                await ctx.send(f"'{word}' is not in the word list!")
    
    @mrwhite.command()
    async def words(self, ctx):
        """Show all available words"""
        words = await self.config.guild(ctx.guild).words()
        pages = []
        words_per_page = 20
        
        for i in range(0, len(words), words_per_page):
            page_words = words[i:i+words_per_page]
            embed = discord.Embed(
                title="Available Words",
                description=", ".join(page_words),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Page {i//words_per_page + 1}/{(len(words)-1)//words_per_page + 1} | Total: {len(words)} words")
            pages.append(embed)
        
        if pages:
            await menu(ctx, pages, DEFAULT_CONTROLS)
        else:
            await ctx.send("No words in the list!")


class Game:
    SAY_TIMEOUT = 180  # seconds to give word associations before auto-advancing to voting
    VOTE_TIMEOUT = 120  # seconds to vote before auto-processing whatever votes came in
    GUESS_TIMEOUT = 90  # seconds for Mr. White's final guess before it's forfeited

    def __init__(self, ctx, config):
        self.ctx = ctx
        self.config = config
        self.host: discord.Member = ctx.author
        self.players: List[discord.Member] = []
        self.mr_white: Optional[discord.Member] = None
        self.word: str = ""
        self.state = "joining"  # joining, playing, voting, guessing, ended
        self.round = 0
        self.eliminated: List[discord.Member] = []
        self.votes: Dict[discord.Member, discord.Member] = {}
        self.has_spoken: List[discord.Member] = []
        self.runoff_candidates: List[discord.Member] = []
        self.phase_id = 0
        self.timeout_task: Optional[asyncio.Task] = None

    def _schedule_timeout(self, seconds, callback):
        """(Re)schedule a timeout tied to the current phase_id; stale firings are ignored."""
        if self.timeout_task is not None:
            self.timeout_task.cancel()
        phase_id = self.phase_id

        async def runner():
            await asyncio.sleep(seconds)
            if self.phase_id == phase_id and self.state != "ended":
                await callback()

        self.timeout_task = asyncio.create_task(runner())

    def _cancel_timeout(self):
        if self.timeout_task is not None:
            self.timeout_task.cancel()
            self.timeout_task = None

    async def start(self):
        """Start the game lobby"""
        embed = discord.Embed(
            title="🎮 Mr. White Game Starting!",
            description=(
                "A social deduction word game!\n\n"
                "**How to play:**\n"
                "• Players receive a secret word (villagers) or no word (Mr. White)\n"
                "• Each round, say a word associated with YOUR word\n"
                "• After the round, vote for who you think is Mr. White\n"
                "• If Mr. White is found, they get one guess at the word\n"
                "• If they guess correctly, Mr. White wins!\n"
                "• If not, villagers win!\n\n"
                f"Use `{self.ctx.prefix}mrwhite join` to join!\n"
                f"Use `{self.ctx.prefix}mrwhite begin` to start (min 3 players)"
            ),
            color=discord.Color.green()
        )
        await self.ctx.send(embed=embed)
    
    async def add_player(self, member: discord.Member):
        """Add a player to the game"""
        if self.state != "joining":
            await self.ctx.send(f"{member.mention} The game has already started!")
            return
        
        if member in self.players:
            await self.ctx.send(f"{member.mention} You're already in the game!")
            return
        
        self.players.append(member)
        await self.ctx.send(f"{member.mention} has joined! ({len(self.players)} players)")
    
    async def begin_game(self):
        """Begin the actual game"""
        if self.state != "joining":
            await self.ctx.send("The game has already started!")
            return
        
        if len(self.players) < 3:
            await self.ctx.send("Need at least 3 players to start!")
            return
        
        # Assign roles
        self.mr_white = random.choice(self.players)
        words = await self.config.guild(self.ctx.guild).words()
        self.word = random.choice(words)
        
        # DM players their roles
        for player in self.players:
            try:
                if player == self.mr_white:
                    await player.send(
                        f"🎭 **You are Mr. White!**\n"
                        f"You don't know the word. Try to blend in and figure it out!"
                    )
                else:
                    await player.send(
                        f"👥 **You are a Villager!**\n"
                        f"Your word is: **{self.word}**\n"
                        f"Give clues to help other villagers, but don't be too obvious!\n"
                        f"*(This word stays the same for the whole game — every round, keep giving clues about it.)*"
                    )
            except discord.Forbidden:
                await self.ctx.send(f"⚠️ Couldn't DM {player.mention}! Make sure your DMs are open.")
        
        self.state = "playing"
        await self.start_round()
    
    async def start_round(self):
        """Start a new round"""
        self.state = "playing"
        self.round += 1
        self.has_spoken = []
        self.runoff_candidates = []
        self.phase_id += 1

        alive_players = [p for p in self.players if p not in self.eliminated]

        embed = discord.Embed(
            title=f"📢 Round {self.round}",
            description=(
                f"**Players alive:** {len(alive_players)}\n"
                f"**Players:** {', '.join([p.mention for p in alive_players])}\n\n"
                f"Say your word association using `{self.ctx.prefix}mrwhite say <word>`"
            ),
            color=discord.Color.blue()
        )
        if self.round > 1:
            embed.set_footer(text="Reminder: the secret word is the same as round 1 — check your DMs if you forgot it.")
        await self.ctx.send(embed=embed)
        self._schedule_timeout(self.SAY_TIMEOUT, self._say_timeout)

    async def _say_timeout(self):
        """Auto-advance to voting if some players never spoke"""
        alive_players = [p for p in self.players if p not in self.eliminated]
        silent = [p for p in alive_players if p not in self.has_spoken]
        if silent:
            names = ", ".join(p.mention for p in silent)
            await self.ctx.send(f"⏰ Time's up! {names} didn't say anything and will be skipped this round.")
        await self.start_voting()
    
    async def player_say(self, member: discord.Member, word: str):
        """Player says their word"""
        if self.state != "playing":
            await self.ctx.send(f"{member.mention} Not the right time to speak!")
            return
        
        if member not in self.players:
            await self.ctx.send(f"{member.mention} You're not in this game!")
            return
        
        if member in self.eliminated:
            await self.ctx.send(f"{member.mention} You've been eliminated!")
            return
        
        if member in self.has_spoken:
            await self.ctx.send(f"{member.mention} You've already spoken this round!")
            return
        
        self.has_spoken.append(member)
        await self.ctx.send(f"**{member.display_name}** says: *{word}*")
        
        alive_players = [p for p in self.players if p not in self.eliminated]
        
        if len(self.has_spoken) == len(alive_players):
            await self.start_voting()
    
    async def start_voting(self):
        """Start the voting phase"""
        self.state = "voting"
        self.votes = {}
        self.runoff_candidates = []
        self.phase_id += 1

        alive_players = [p for p in self.players if p not in self.eliminated]

        embed = discord.Embed(
            title="🗳️ Voting Time!",
            description=(
                f"Vote for who you think is Mr. White!\n"
                f"Use `{self.ctx.prefix}mrwhite vote @player`\n\n"
                f"**Alive players:** {', '.join([p.mention for p in alive_players])}"
            ),
            color=discord.Color.orange()
        )
        await self.ctx.send(embed=embed)
        self._schedule_timeout(self.VOTE_TIMEOUT, self._vote_timeout)

    async def _vote_timeout(self):
        """Auto-process votes if some players never voted"""
        alive_players = [p for p in self.players if p not in self.eliminated]
        missing = [p for p in alive_players if p not in self.votes]
        if missing:
            names = ", ".join(p.mention for p in missing)
            await self.ctx.send(f"⏰ Time's up! {names} didn't vote in time.")
        if not self.votes:
            await self.ctx.send("No votes were cast — no one is eliminated this round.")
            await self.start_round()
            return
        await self.process_votes()
    
    async def vote(self, voter: discord.Member, target: discord.Member):
        """Cast a vote"""
        if self.state != "voting":
            await self.ctx.send(f"{voter.mention} Not voting time!")
            return
        
        if voter not in self.players or voter in self.eliminated:
            await self.ctx.send(f"{voter.mention} You can't vote!")
            return

        if target not in self.players or target in self.eliminated:
            await self.ctx.send(f"{voter.mention} That player isn't in the game!")
            return

        if voter == target:
            await self.ctx.send(f"{voter.mention} You can't vote for yourself!")
            return

        if self.runoff_candidates and target not in self.runoff_candidates:
            names = ", ".join(p.mention for p in self.runoff_candidates)
            await self.ctx.send(f"{voter.mention} This is a runoff — you must vote for one of: {names}")
            return

        self.votes[voter] = target
        await self.ctx.send(f"{voter.mention} voted! ({len(self.votes)}/{len([p for p in self.players if p not in self.eliminated])})")
        
        alive_players = [p for p in self.players if p not in self.eliminated]
        
        if len(self.votes) == len(alive_players):
            await self.process_votes()
    
    async def process_votes(self):
        """Process the votes"""
        vote_counts = {}
        for target in self.votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1

        max_votes = max(vote_counts.values())
        tied = [p for p, v in vote_counts.items() if v == max_votes]

        vote_summary = "\n".join([f"**{target.display_name}**: {count} votes"
                                  for target, count in sorted(vote_counts.items(),
                                                             key=lambda x: x[1],
                                                             reverse=True)])

        embed = discord.Embed(
            title="📊 Vote Results",
            description=vote_summary,
            color=discord.Color.red()
        )
        await self.ctx.send(embed=embed)

        alive_players = [p for p in self.players if p not in self.eliminated]

        if len(tied) > 1:
            if self.runoff_candidates or len(alive_players) <= 2:
                # Already had one runoff (or a runoff can't break the tie with only 2 voters) - break randomly
                eliminated_player = random.choice(tied)
                self.runoff_candidates = []
                names = ", ".join(p.display_name for p in tied)
                await self.ctx.send(
                    f"⚖️ Still tied between **{names}** — randomly eliminating **{eliminated_player.display_name}**."
                )
            else:
                self.runoff_candidates = tied
                self.state = "voting"
                self.votes = {}
                self.phase_id += 1
                names = ", ".join(p.mention for p in tied)
                await self.ctx.send(
                    f"🤝 **It's a tie!** {names} are tied. Everyone votes again — "
                    f"this time only for one of the tied players, using `{self.ctx.prefix}mrwhite vote @player`."
                )
                self._schedule_timeout(self.VOTE_TIMEOUT, self._vote_timeout)
                return
        else:
            eliminated_player = tied[0]
            self.runoff_candidates = []

        self.eliminated.append(eliminated_player)
        
        await self.ctx.send(f"**{eliminated_player.display_name}** has been eliminated!")
        
        # Check if eliminated player was Mr. White
        if eliminated_player == self.mr_white:
            await self.ctx.send(f"🎭 **{eliminated_player.display_name}** was Mr. White!")
            await self.mr_white_final_guess()
        else:
            await self.ctx.send(f"👥 **{eliminated_player.display_name}** was a Villager!")
            
            alive_players = [p for p in self.players if p not in self.eliminated]
            
            # Check if Mr. White is in last 2
            if len(alive_players) == 2 and self.mr_white in alive_players:
                await self.ctx.send("🏆 **Mr. White survived to the final 2!**")
                await self.end_game(f"Mr. White ({self.mr_white.mention}) wins by survival!")
            elif self.mr_white not in alive_players:
                await self.end_game("Villagers win! Mr. White was eliminated earlier!")
            else:
                await self.start_round()
    
    async def mr_white_final_guess(self):
        """Mr. White gets to make a final guess"""
        self.state = "guessing"
        self.phase_id += 1

        await self.ctx.send(
            f"🎯 **{self.mr_white.mention}**, you have one chance to guess the word!\n"
            f"Use `{self.ctx.prefix}mrwhite guess <word>` to make your guess!"
        )
        self._schedule_timeout(self.GUESS_TIMEOUT, self._guess_timeout)

    async def _guess_timeout(self):
        """Forfeit Mr. White's guess if they take too long"""
        await self.end_game(
            f"⏰ **{self.mr_white.mention}** ran out of time to guess!\n"
            f"👥 **Villagers win!** The word was: **{self.word}**"
        )

    async def mr_white_guess(self, member: discord.Member, guess: str):
        """Mr. White makes their guess"""
        if self.state != "guessing":
            await self.ctx.send(f"{member.mention} Not guessing time!")
            return
        
        if member != self.mr_white:
            await self.ctx.send(f"{member.mention} You're not Mr. White!")
            return
        
        if guess.lower() == self.word.lower():
            await self.end_game(
                f"🎉 **Mr. White wins!**\n"
                f"{self.mr_white.mention} correctly guessed: **{self.word}**"
            )
        else:
            await self.end_game(
                f"❌ **Villagers win!**\n"
                f"{self.mr_white.mention} guessed: *{guess}*\n"
                f"The word was: **{self.word}**"
            )
    
    async def end_game(self, message: str):
        """End the game"""
        self.state = "ended"
        self._cancel_timeout()

        embed = discord.Embed(
            title="🎮 Game Over!",
            description=message,
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Players",
            value="\n".join([f"{'🎭' if p == self.mr_white else '👥'} {p.display_name}" 
                           for p in self.players]),
            inline=False
        )
        
        await self.ctx.send(embed=embed)
        
        # Remove game from active games
        if self.ctx.channel.id in self.ctx.cog.games:
            del self.ctx.cog.games[self.ctx.channel.id]
