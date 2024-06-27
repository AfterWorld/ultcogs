async def team_battle(self, ctx, *members: discord.Member):
    """Start a team battle. Separate teams with 'vs', e.g., @user1 @user2 vs @user3 @user4"""
    teams = ' '.join(m.mention for m in members).split(' vs ')
    if len(teams) != 2:
        return await ctx.send("Please specify two teams separated by 'vs'.")
    
    team1 = [ctx.guild.get_member(int(m.strip('<@!>'))) for m in teams[0].split()]
    team2 = [ctx.guild.get_member(int(m.strip('<@!>'))) for m in teams[1].split()]

    await ctx.send(f"Team Battle: {' '.join(m.name for m in team1)} VS {' '.join(m.name for m in team2)}")
    # Implement team battle logic here
    # You'll need to modify your battle system to handle teams