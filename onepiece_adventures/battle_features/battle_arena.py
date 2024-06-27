import discord
from redbot.core import commands

class BattleArena:
    def __init__(self):
        self.queue = []

    def add_player(self, player):
        if player not in self.queue:
            self.queue.append(player)
            return True
        return False

    def remove_player(self, player):
        if player in self.queue:
            self.queue.remove(player)
            return True
        return False

    def get_match(self):
        if len(self.queue) >= 2:
            return self.queue.pop(0), self.queue.pop(0)
        return None, None

async def join_arena(self, ctx):
    """Join the battle arena queue."""
    if self.battle_arena.add_player(ctx.author):
        await ctx.send(f"{ctx.author.mention} has joined the arena queue!")
        if len(self.battle_arena.queue) >= 2:
            player1, player2 = self.battle_arena.get_match()
            await ctx.send(f"A match has been found! {player1.mention} vs {player2.mention}")
            await self.opcbattle.battle(ctx, player1, player2)
    else:
        await ctx.send("You're already in the queue!")

async def leave_arena(self, ctx):
    """Leave the battle arena queue."""
    if self.battle_arena.remove_player(ctx.author):
        await ctx.send(f"{ctx.author.mention} has left the arena queue.")
    else:
        await ctx.send("You're not in the queue!")
