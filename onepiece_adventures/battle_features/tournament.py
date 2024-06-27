import asyncio
import discord
from redbot.core import commands

class Tournament:
    def __init__(self, participants):
        self.participants = participants
        self.rounds = []
        self.winner = None

    async def run(self, ctx, opcbattle):
        await ctx.send(f"Tournament starting with {len(self.participants)} participants!")
        current_round = self.participants
        round_num = 1

        while len(current_round) > 1:
            await ctx.send(f"Round {round_num} starting!")
            next_round = []
            for i in range(0, len(current_round), 2):
                if i + 1 < len(current_round):
                    winner = await opcbattle.battle(ctx, current_round[i], current_round[i+1])
                    next_round.append(winner)
                else:
                    next_round.append(current_round[i])
            
            self.rounds.append(current_round)
            current_round = next_round
            round_num += 1
            await asyncio.sleep(5)  # Short break between rounds

        self.winner = current_round[0]
        await ctx.send(f"Tournament ended! The winner is {self.winner.mention}!")

async def start_tournament(self, ctx, *participants: discord.Member):
    """Start a battle tournament with multiple participants."""
    if len(participants) < 2:
        return await ctx.send("You need at least 2 participants for a tournament.")
    
    tournament = Tournament(list(participants))
    await tournament.run(ctx, self.opcbattle)
