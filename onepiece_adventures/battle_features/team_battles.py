import random
import discord
from redbot.core import commands, Config
import logging

logger = logging.getLogger(__name__)

async def team_battle(bot, config, ctx, *members: discord.Member):
    """Start a team battle. Separate teams with 'vs', e.g., @user1 @user2 vs @user3 @user4"""
    logger.info(f"Starting team battle with members: {', '.join([m.name for m in members])}")
    teams = ' '.join(m.mention for m in members).split(' vs ')
    if len(teams) != 2:
        return await ctx.send("Please specify two teams separated by 'vs'.")
    
    team1 = [ctx.guild.get_member(int(m.strip('<@!>'))) for m in teams[0].split()]
    team2 = [ctx.guild.get_member(int(m.strip('<@!>'))) for m in teams[1].split()]

    if len(team1) != len(team2):
        return await ctx.send("Teams must have an equal number of members.")

    await ctx.send(f"Team Battle: {' '.join(m.name for m in team1)} VS {' '.join(m.name for m in team2)}")

    team1_hp = sum(await get_max_hp(config, m) for m in team1)
    team2_hp = sum(await get_max_hp(config, m) for m in team2)

    while team1_hp > 0 and team2_hp > 0:
        # Team 1's turn
        for attacker in team1:
            defender = random.choice(team2)
            damage = await calculate_damage(config, attacker, defender)
            team2_hp -= damage
            await ctx.send(f"{attacker.name} attacks {defender.name} for {damage} damage!")
            if team2_hp <= 0:
                break

        if team2_hp <= 0:
            break

        # Team 2's turn
        for attacker in team2:
            defender = random.choice(team1)
            damage = await calculate_damage(config, attacker, defender)
            team1_hp -= damage
            await ctx.send(f"{attacker.name} attacks {defender.name} for {damage} damage!")
            if team1_hp <= 0:
                break

    if team1_hp > team2_hp:
        winners, losers = team1, team2
    else:
        winners, losers = team2, team1

    await ctx.send(f"The battle is over! {' '.join(m.name for m in winners)} are victorious!")
    
    for winner in winners:
        await update_wins(config, winner)
    
    logger.info(f"Team battle ended. Winners: {', '.join([w.name for w in winners])}")

async def get_max_hp(config, member):
    user_data = await config.member(member).all()
    return 100 + (user_data['defense'] * 5)  # Base HP + defense bonus

async def calculate_damage(config, attacker, defender):
    attacker_data = await config.member(attacker).all()
    defender_data = await config.member(defender).all()
    
    base_damage = attacker_data['strength'] + random.randint(1, 10)
    defense = defender_data['defense']
    
    return max(1, base_damage - defense)

async def update_wins(config, member):
    async with config.member(member).all() as user_data:
        user_data['wins'] = user_data.get('wins', 0) + 1
    logger.info(f"Updated wins for {member.name}. New win count: {user_data['wins']}")

@commands.command()
async def wins(self, ctx, member: discord.Member = None):
    """Check the number of wins for yourself or another member."""
    if member is None:
        member = ctx.author
    
    user_data = await self.config.member(member).all()
    wins = user_data.get('wins', 0)
    await ctx.send(f"{member.name} has {wins} battle wins!")
