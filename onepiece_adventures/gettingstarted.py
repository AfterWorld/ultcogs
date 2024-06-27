import discord
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

class GettingStarted:
    def __init__(self, bot):
        self.bot = bot

    async def show_guide(self, ctx):
        """Display the One Piece Adventures guide."""
        pages = self.create_guide_pages()
        await menu(ctx, pages, DEFAULT_CONTROLS, timeout=60)

    def create_guide_pages(self):
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

        # Page 5: World Events
        embed = discord.Embed(title="World Events", color=discord.Color.red())
        embed.add_field(name="Random Events", value="World events occur randomly and offer unique challenges and rewards.", inline=False)
        embed.add_field(name="Event Cooldown", value="There's a cooldown between world events to prevent spam.", inline=False)
        embed.add_field(name=".event_status", value="Check the status of the current world event", inline=False)
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

        # Add a new page for all available commands
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

        # Update the World Events page to include timestamps
        embed = discord.Embed(title="World Events and Raids", color=discord.Color.red())
        embed.add_field(name="Random Events", value="World events occur randomly and offer unique challenges and rewards.", inline=False)
        embed.add_field(name="Event Cooldown", value="There's a cooldown between world events to prevent spam.", inline=False)
        embed.add_field(name=".event_status", value="Check the status of the current world event", inline=False)
        
        # Add timestamps for last event and raid
        last_event_time = ctx.cog.world_events.last_event_time
        last_raid_time = ctx.cog.raid_boss_system.last_raid_time
        
        if last_event_time:
            embed.add_field(name="Last World Event", value=f"<t:{int(last_event_time)}:R>", inline=False)
        else:
            embed.add_field(name="Last World Event", value="No events yet", inline=False)
        
        if last_raid_time:
            embed.add_field(name="Last Raid Boss", value=f"<t:{int(last_raid_time)}:R>", inline=False)
        else:
            embed.add_field(name="Last Raid Boss", value="No raids yet", inline=False)
        
        pages.append(embed)

        return pages

        return pages
