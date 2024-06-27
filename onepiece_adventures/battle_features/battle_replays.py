import asyncio
import discord
from redbot.core import commands


async def save_battle_log(self, battle_id, log):
    async with self.config.battle_logs() as battle_logs:
        battle_logs[battle_id] = log

async def battle_replay(self, ctx, battle_id: int):
    """Watch a replay of a past battle."""
    battle_logs = await self.config.battle_logs()
    if battle_id not in battle_logs:
        return await ctx.send("Battle not found.")
    
    log = battle_logs[battle_id]
    for entry in log:
        await ctx.send(entry)
        await asyncio.sleep(2)  # Delay between actions for readability
