import discord

class BattleQuest:
    def __init__(self, description, required_wins, reward):
        self.description = description
        self.required_wins = required_wins
        self.reward = reward

battle_quests = [
    BattleQuest("Win 3 battles", 3, 100),
    BattleQuest("Win a battle using only special moves", 1, 150),
    BattleQuest("Win a battle without using items", 1, 200),
]

async def view_battle_quests(self, ctx):
    """View available battle quests."""
    embed = discord.Embed(title="Battle Quests", color=discord.Color.green())
    for quest in battle_quests:
        embed.add_field(name=quest.description, value=f"Reward: {quest.reward} Berries", inline=False)
    await ctx.send(embed=embed)

# You'll need to implement quest tracking and completion in your battle system