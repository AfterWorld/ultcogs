import discord
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from datetime import datetime

class GettingStarted:
    def __init__(self, bot):
        self.bot = bot

    async def show_guide(self, ctx):
        """Display the One Piece Adventures guide."""
        pages = self.create_guide_pages(ctx)
        await menu(ctx, pages, DEFAULT_CONTROLS, timeout=60)

    def create_guide_pages(self, ctx):
        pages = []

        # Page 1: Introduction
        embed = discord.Embed(title="One Piece Adventures Guide", color=discord.Color.blue())
        embed.add_field(name="Welcome!", value="Embark on your own grand adventure in the world of One Piece! This guide will help you get started and explain the main features of the game.", inline=False)
        pages.append(embed)

        # Page 2: Basic Commands
        embed = discord.Embed(title="Basic Commands", color=discord.Color.green())
        embed.add_field(name=".profile", value="View your character's stats and information", inline=False)
        embed.add_field(name=".train <attribute>", value="Train a specific attribute (strength, defense, speed)", inline=False)
        embed.add_field(name=".explore", value="Explore your current island for adventures", inline=False)
        embed.add_field(name=".travel <island>", value="Travel to a different island", inline=False)
        pages.append(embed)

        # Page 3: Crew System
        embed = discord.Embed(title="Crew System", color=discord.Color.gold())
        embed.add_field(name=".create_crew <name>", value="Create a new pirate crew", inline=False)
        embed.add_field(name=".join_crew <name>", value="Join an existing crew", inline=False)
        embed.add_field(name=".crew_info", value="View information about your crew", inline=False)
        embed.add_field(name=".crew_battle <opponent_crew>", value="Initiate a battle between crews", inline=False)
        pages.append(embed)

        # Page 4: Devil Fruits
        embed = discord.Embed(title="Devil Fruits", color=discord.Color.purple())
        embed.add_field(name=".eat_devil_fruit <fruit_name>", value="Consume a Devil Fruit to gain its powers", inline=False)
        embed.add_field(name=".devil_fruit_info", value="View information about Devil Fruits", inline=False)
        embed.add_field(name=".train_devil_fruit", value="Train your Devil Fruit abilities", inline=False)
        pages.append(embed)

        # Page 5: World Events and Raids
        embed = discord.Embed(title="World Events and Raids", color=discord.Color.red())
        embed.add_field(name="Random Events", value="World events occur randomly and offer unique challenges and rewards.", inline=False)
        embed.add_field(name="Event Cooldown", value="There's a cooldown between world events to prevent spam.", inline=False)
        embed.add_field(name=".event_status", value="Check the status of the current world event", inline=False)
        
        # Add timestamps for last event and raid
        last_event_time = getattr(ctx.cog.world_events, 'last_event_time', None)
        last_raid_time = getattr(ctx.cog.raid_boss_system, 'last_raid_time', None)
        
        if last_event_time:
            embed.add_field(name="Last World Event", value=f"<t:{int(last_event_time)}:R>", inline=False)
        else:
            embed.add_field(name="Last World Event", value="No events yet", inline=False)
        
        if last_raid_time:
            embed.add_field(name="Last Raid Boss", value=f"<t:{int(last_raid_time)}:R>", inline=False)
        else:
            embed.add_field(name="Last Raid Boss", value="No raids yet", inline=False)
        
        pages.append(embed)

        # Page 6: Economy and Trading
        embed = discord.Embed(title="Economy and Trading", color=discord.Color.green())
        embed.add_field(name=".balance", value="Check your Berry balance", inline=False)
        embed.add_field(name=".inventory", value="View your inventory", inline=False)
        embed.add_field(name=".create_listing <item> <price> <quantity>", value="Create a market listing", inline=False)
        embed.add_field(name=".buy_listing <listing_id>", value="Buy an item from the market", inline=False)
        pages.append(embed)

        # Page 7: Davy Back Fight
        embed = discord.Embed(title="Davy Back Fight", color=discord.Color.orange())
        embed.add_field(name=".davy_back_fight <opponent>", value="Challenge another player to a Davy Back Fight", inline=False)
        embed.add_field(name="Rounds", value="1. Donut Race\n2. Groggy Ring\n3. Combat", inline=False)
        embed.add_field(name="Rewards", value="The winner receives a valuable prize!", inline=False)
        pages.append(embed)

        # Page 8: Tips and Tricks
        embed = discord.Embed(title="Tips and Tricks", color=discord.Color.teal())
        embed.add_field(name="Balance Your Training", value="Don't focus on just one attribute. A well-rounded character is more versatile.", inline=False)
        embed.add_field(name="Explore Regularly", value="Exploring islands can lead to valuable discoveries and experiences.", inline=False)
        embed.add_field(name="Participate in Events", value="World events offer unique rewards and experiences. Don't miss out!", inline=False)
        embed.add_field(name="Trade Wisely", value="Keep an eye on market prices and trade smartly to increase your wealth.", inline=False)
        pages.append(embed)

        # Page 9: Enhanced Battle System
        embed = discord.Embed(title="Enhanced Battle System", color=discord.Color.red())
        embed = discord.Embed(title="Enhanced Battle System", color=discord.Color.red())
        embed.add_field(name="Turn-Based Combat", value="In battles, you can choose to attack, defend, use your class ability, perform a special move, or use an item each turn.", inline=False)
        embed.add_field(name="Stamina System", value="Special moves consume stamina. Manage your stamina wisely!", inline=False)
        embed.add_field(name="Environmental Effects", value="Battles take place in different environments that can affect combat.", inline=False)
        embed.add_field(name="Battle Items", value="Use items during battle for various effects, such as healing or boosting stamina.", inline=False)
        embed.add_field(name="Class Abilities", value="Each class has a unique ability:\n"
                                                      "• Swordsman: Three Sword Style (increased damage)\n"
                                                      "• Sniper: Precision Shot (high damage, chance to miss)\n"
                                                      "• Navigator: Evasion Boost (increased dodge chance)\n"
                                                      "• Cook: Quick Meal (heal based on strength)\n"
                                                      "• Doctor: Medical Knowledge (strong heal)", inline=False)
        embed.add_field(name="Critical Hits & Dodges", value="Battles now include chances for critical hits and dodges based on your speed stat.", inline=False)
        embed.add_field(name="Fighting Styles", value="Your chosen fighting style provides bonuses in battle.", inline=False)
        pages.append(embed)

        # New page for Advanced Battle Features
        embed = discord.Embed(title="Advanced Battle Features", color=discord.Color.red())
        embed.add_field(name="Tournaments", value="Participate in multi-player tournaments using `.start_tournament`", inline=False)
        embed.add_field(name="Team Battles", value="Engage in team vs team battles with `.team_battle`", inline=False)
        embed.add_field(name="Battle Replays", value="Watch past battles using `.battle_replay`", inline=False)
        embed.add_field(name="Leaderboard", value="Check the top battlers with `.battle_leaderboard`", inline=False)
        embed.add_field(name="Battle Quests", value="Complete battle-related quests for rewards using `.battle_quests`", inline=False)
        embed.add_field(name="Battle Arena", value="Join the arena for quick matches with `.join_arena`", inline=False)
        embed.add_field(name="Individual Battles", value="Challenge others to 1v1 battles using `.battle`", inline=False)
        embed.add_field(name="Win Tracking", value="Your battle wins are tracked. Check them with `.wins`", inline=False)
        pages.append(embed)

        # Page 10: All Available Commands
        embed = discord.Embed(title="All Available Commands", color=discord.Color.blue())
        commands_list = [
            ".profile", ".train", ".explore", ".travel", 
            ".create_crew", ".join_crew", ".crew_info", ".crew_battle",
            ".eat_devil_fruit", ".devil_fruit_info", ".train_devil_fruit",
            ".event_status", ".balance", ".inventory",
            ".create_listing", ".buy_listing", ".davy_back_fight",
            ".guide"
        ]
        embed.description = "\n".join(commands_list)
        pages.append(embed)
         # Update the All Available Commands page
        all_commands_embed = pages[-1]  # Assuming it's the last page
        new_commands = [
            ".start_tournament", ".team_battle", ".battle_replay",
            ".battle_leaderboard", ".battle_quests", ".join_arena", ".leave_arena"
        ]
        all_commands_embed.description += "\n" + "\n".join(new_commands)

        return pages
