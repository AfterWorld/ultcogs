import discord
from redbot.core import commands, Config
import random
import asyncio

class DavyBackFight:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def start_davy_back_fight(self, ctx, opponent: discord.Member):
        if opponent.bot:
            await ctx.send("You can't challenge a bot to a Davy Back Fight!")
            return

        await ctx.send(f"{opponent.mention}, {ctx.author.mention} has challenged you to a Davy Back Fight! Do you accept? (yes/no)")

        def check(m):
            return m.author == opponent and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("The challenge has timed out.")
            return

        if msg.content.lower() == 'no':
            await ctx.send("The challenge was declined.")
            return

        await ctx.send("The Davy Back Fight begins! There will be three rounds: Donut Race, Groggy Ring, and Combat.")

        challenger_wins = 0
        opponent_wins = 0

        # Donut Race
        await ctx.send("Round 1: Donut Race!")
        if await self.donut_race(ctx, ctx.author, opponent):
            challenger_wins += 1
        else:
            opponent_wins += 1

        # Groggy Ring
        await ctx.send("Round 2: Groggy Ring!")
        if await self.groggy_ring(ctx, ctx.author, opponent):
            challenger_wins += 1
        else:
            opponent_wins += 1

        # Combat
        await ctx.send("Final Round: Combat!")
        if await self.combat(ctx, ctx.author, opponent):
            challenger_wins += 1
        else:
            opponent_wins += 1

        # Determine overall winner
        if challenger_wins > opponent_wins:
            winner = ctx.author
            loser = opponent
        else:
            winner = opponent
            loser = ctx.author

        await ctx.send(f"{winner.mention} has won the Davy Back Fight!")
        await self.transfer_crew_member(ctx, winner, loser)

    async def donut_race(self, ctx, player1, player2):
        await ctx.send("The Donut Race is a test of speed and navigation!")
        p1_speed = (await self.config.member(player1).speed()) * random.uniform(0.8, 1.2)
        p2_speed = (await self.config.member(player2).speed()) * random.uniform(0.8, 1.2)
        
        winner = player1 if p1_speed > p2_speed else player2
        await ctx.send(f"{winner.mention} wins the Donut Race!")
        return winner == player1

    async def groggy_ring(self, ctx, player1, player2):
        await ctx.send("The Groggy Ring is a test of strength and teamwork!")
        p1_strength = (await self.config.member(player1).strength()) * random.uniform(0.8, 1.2)
        p2_strength = (await self.config.member(player2).strength()) * random.uniform(0.8, 1.2)
        
        winner = player1 if p1_strength > p2_strength else player2
        await ctx.send(f"{winner.mention} wins the Groggy Ring!")
        return winner == player1

    async def combat(self, ctx, player1, player2):
        await ctx.send("The Combat round is a direct battle between the two players!")
        p1_combat = (await self.config.member(player1).strength() + await self.config.member(player1).defense()) * random.uniform(0.8, 1.2)
        p2_combat = (await self.config.member(player2).strength() + await self.config.member(player2).defense()) * random.uniform(0.8, 1.2)
        
        winner = player1 if p1_combat > p2_combat else player2
        await ctx.send(f"{winner.mention} wins the Combat round!")
        return winner == player1

    async def transfer_crew_member(self, ctx, winner, loser):
        winner_crew = await self.config.member(winner).crew()
        loser_crew = await self.config.member(loser).crew()

        if not winner_crew or not loser_crew:
            await ctx.send("Both participants must be in a crew for a member transfer.")
            return

        crews = await self.config.guild(ctx.guild).crews()
        if len(crews[loser_crew]["members"]) <= 1:
            await ctx.send(f"{loser.mention}'s crew doesn't have enough members to transfer.")
            return

        transferring_member_id = random.choice([m for m in crews[loser_crew]["members"] if m != loser.id])
        transferring_member = ctx.guild.get_member(transferring_member_id)

        crews[loser_crew]["members"].remove(transferring_member_id)
        crews[winner_crew]["members"].append(transferring_member_id)

        await self.config.guild(ctx.guild).crews.set(crews)
        await self.config.member(transferring_member).crew.set(winner_crew)

        await ctx.send(f"{transferring_member.mention} has been transferred from {loser_crew} to {winner_crew}!")