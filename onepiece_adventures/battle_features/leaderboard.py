import discord

async def battle_leaderboard(self, ctx):
    """Display the battle leaderboard."""
    all_members = await self.config.all_members(ctx.guild)
    sorted_members = sorted(all_members.items(), key=lambda x: x[1].get("wins", 0), reverse=True)
    
    embed = discord.Embed(title="Battle Leaderboard", color=discord.Color.gold())
    for i, (member_id, data) in enumerate(sorted_members[:10], 1):
        member = ctx.guild.get_member(member_id)
        if member:
            embed.add_field(name=f"{i}. {member.name}", value=f"Wins: {data.get('wins', 0)}", inline=False)
    
    await ctx.send(embed=embed)