import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import asyncio
import random
from typing import Dict, List, Any
from .battle_features import (
    Tournament, start_tournament,
    team_battle,
    save_battle_log, battle_replay,
    battle_leaderboard,
    BattleQuest, battle_quests, view_battle_quests,
    BattleArena, join_arena, leave_arena,
    end_battle
)

from .op_welcome import OPWelcome  # Import the new class
from .opcbattle import OPCBattle
from .character_customization import CharacterCustomization
from .crew_battles import CrewBattleSystem
from .davy_back_fight import DavyBackFight
from .devil_fruit_system import DevilFruitSystem
from .island_development import IslandDevelopment
from .marine_career import MarineCareerSystem
from .sea_travel_system import SeaTravelSystem
from .training_system import TrainingSystem
from .treasure_maps import TreasureMapSystem
from .raid_boss_system import RaidBossSystem
from .economy_trading_system import EconomyTradingSystem
from .reputation_system import ReputationSystem
from .world_events import WorldEvents
from .gettingstarted import GettingStarted

class OnePieceAdventures(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        default_global = {
            "islands": {},
            "devil_fruits": {},
            "seasonal_events": {}
        }
        default_guild = {
            "crews": {},
            "marine_bases": {},
            "pvp_arenas": {},
            "market_listings": {},
            "islands": {},
            "enabled": False,
            "welcome_channel": None,
            "welcome_enabled": False
        }
        default_member = {
            "level": 1,
            "exp": 0,
            "berries": 1000,
            "strength": 10,
            "defense": 10,
            "speed": 10,
            "haki_level": 0,
            "devil_fruit": None,
            "crew": None,
            "ship": None,
            "inventory": {},
            "reputation": {"pirate": 0, "marine": 0, "revolutionary": 0},
            "current_island": "Foosha Village",
            "training_counts": {"strength": 0, "defense": 0, "speed": 0},
            "last_daily": 0,
            "ship_upgrades": []
        }
        
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        
        # Initialize subsystems
        self.opwelcome = OPWelcome(bot, self.config)  # Initialize the OPWelcome class
        self.battle_arena = BattleArena()
        self.opcbattle = OPCBattle(self.bot, self.config)
        self.character_customization = CharacterCustomization(self.bot, self.config)
        self.crew_battle_system = CrewBattleSystem(self.bot, self.config)
        self.davy_back_fight = DavyBackFight(self.bot, self.config)
        self.devil_fruit_system = DevilFruitSystem(self.bot, self.config)
        self.island_development = IslandDevelopment(self.bot, self.config)
        self.marine_career_system = MarineCareerSystem(self.bot, self.config)
        self.sea_travel_system = SeaTravelSystem(self.bot, self.config)
        self.training_system = TrainingSystem(self.bot, self.config)
        self.treasure_map_system = TreasureMapSystem(self.bot, self.config)
        self.raid_boss_system = RaidBossSystem(self.bot, self.config)
        self.economy_trading_system = EconomyTradingSystem(self.bot, self.config)
        self.reputation_system = ReputationSystem(self.bot, self.config)
        self.world_events = WorldEvents(self.bot, self.config)
        self.getting_started = GettingStarted(self.bot)
        
        self.bg_task = self.bot.loop.create_task(self.world_events.start_event_loop())

    def cog_unload(self):
        self.bg_task.cancel()
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.world_events.trigger_event_by_message(message)

     @commands.Cog.listener()
     async def on_member_join(self, member):
        await self.opwelcome.on_member_join(member)

    # Add the opwelcome command group
    opwelcome = commands.Group(name="opwelcome", invoke_without_command=True)

    @opwelcome.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        await self.opwelcome.channel(ctx, channel)

    @opwelcome.command()
    async def toggle(self, ctx):
        await self.opwelcome.toggle(ctx)

    @opwelcome.command()
    async def test(self, ctx):
        await self.opwelcome.test(ctx)

    @commands.command()
    @commands.is_owner()
    async def trigger_world_event(self, ctx):
        """Manually trigger a world event (Owner only)"""
        await self.world_events.manual_trigger_event(ctx)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        """View your or another user's profile."""
        if member is None:
            member = ctx.author
        
        user_data = await self.config.member(member).all()
        embed = discord.Embed(title=f"{member.name}'s Profile", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="Level", value=user_data['level'])
        embed.add_field(name="Exp", value=user_data['exp'])
        embed.add_field(name="Berries", value=user_data['berries'])
        embed.add_field(name="Strength", value=user_data['strength'])
        embed.add_field(name="Defense", value=user_data['defense'])
        embed.add_field(name="Speed", value=user_data['speed'])
        embed.add_field(name="Haki Level", value=user_data['haki_level'])
        embed.add_field(name="Devil Fruit", value=user_data['devil_fruit'] or "None")
        embed.add_field(name="Crew", value=user_data['crew'] or "None")
        embed.add_field(name="Current Island", value=user_data['current_island'])
        
        await ctx.send(embed=embed)

    @commands.command()
    async def train(self, ctx, attribute: str):
        """Train a specific attribute (strength, defense, speed)."""
        await self.training_system.train_attribute(ctx, attribute)

    @commands.command()
    async def guide(self, ctx):
        """Display the One Piece Adventures guide."""
        await self.getting_started.show_guide(ctx)

    @commands.command()
    async def explore(self, ctx):
        """Explore the current island for adventures and treasures."""
        await self.sea_travel_system.explore_current_island(ctx)

    @commands.command()
    async def travel(self, ctx, destination: str):
        """Travel to a different island."""
        await self.sea_travel_system.travel_to_island(ctx, destination)

    @commands.command()
    async def create_crew(self, ctx, name: str):
        """Create a new pirate crew."""
        await self.crew_battle_system.create_crew(ctx, name)

    @commands.command()
    async def join_crew(self, ctx, crew_name: str):
        """Join an existing pirate crew."""
        await self.crew_battle_system.join_crew(ctx, crew_name)

    @commands.command()
    async def crew_battle(self, ctx, opponent_crew: str):
        """Initiate a battle between crews."""
        await self.crew_battle_system.initiate_crew_battle(ctx, opponent_crew)

    @commands.command()
    async def davy_back_fight(self, ctx, opponent: discord.Member):
        """Challenge another user to a Davy Back Fight."""
        if opponent == ctx.author:
            return await ctx.send("You can't challenge yourself to a Davy Back Fight!")
        await self.davy_back_fight.start_davy_back_fight(ctx, opponent)

    @commands.command()
    async def eat_devil_fruit(self, ctx, fruit_name: str):
        """Eat a Devil Fruit to gain its powers."""
        await self.devil_fruit_system.eat_devil_fruit(ctx, fruit_name)

    @commands.command()
    async def join_marines(self, ctx):
        """Join the Marines faction."""
        await self.marine_career_system.join_marines(ctx)

    @commands.command()
    async def marine_mission(self, ctx):
        """Undertake a Marine mission."""
        await self.marine_career_system.marine_mission(ctx)

    @commands.command()
    async def invest_island(self, ctx, island_name: str, development: str):
        """Invest in island development."""
        await self.island_development.invest_in_island(ctx, island_name, development)

    @commands.command()
    async def find_treasure_map(self, ctx):
        """Search for a treasure map."""
        await self.treasure_map_system.find_treasure_map(ctx)

    @commands.command()
    async def use_treasure_map(self, ctx):
        """Use a treasure map to find treasure."""
        await self.treasure_map_system.use_treasure_map(ctx)

    @commands.command()
    async def spawn_raid(self, ctx):
        """Spawns the raid boss"""
        await self.raid_boss_system.spawn_raid_boss(ctx)

    @commands.command()
    async def join_raid(self, ctx):
        """Join the active raid boss battle."""
        await self.raid_boss_system.join_raid(ctx)

    @commands.command()
    async def attack_raid_boss(self, ctx):
        """Attack the active raid boss."""
        await self.raid_boss_system.attack_raid_boss(ctx)

    @commands.command()
    async def create_listing(self, ctx, item: str, price: int, quantity: int):
        """Create a market listing to sell an item."""
        await self.economy_trading_system.create_market_listing(ctx, item, price, quantity)

    @commands.command()
    async def buy_listing(self, ctx, listing_id: int):
        """Buy an item from the market."""
        await self.economy_trading_system.buy_market_listing(ctx, listing_id)

    @commands.command()
    async def view_market(self, ctx):
        """View current market listings."""
        await self.economy_trading_system.view_market_listings(ctx)

    @commands.command()
    async def view_reputation(self, ctx):
        """View your reputation with different factions."""
        await self.reputation_system.view_reputation(ctx)

    @commands.command()
    async def reputation_rewards(self, ctx):
        """View rewards for your current reputation levels."""
        await self.reputation_system.reputation_rewards(ctx)

    @commands.command()
    async def event_status(self, ctx):
        """Check the status of the current world event."""
        await self.world_events.event_status(ctx)

    @commands.command()
    async def challenge(self, ctx):
        """Challenge the legendary pirate in a showdown."""
        if self.world_events.active_event == "legendary_pirate_showdown":
            await self.world_events.challenge(ctx)
        else:
            await ctx.send("There's no legendary pirate to challenge right now.")

    @commands.command()
    async def research(self, ctx):
        """Contribute to the research of an ancient weapon."""
        if self.world_events.active_event == "ancient_weapon_discovery":
            await self.world_events.research(ctx)
        else:
            await ctx.send("There's no ongoing research expedition right now.")

    @commands.command()
    @commands.is_owner()
    async def create_island(self, ctx, *, island_name: str):
        """Create a new island (Bot owner only)."""
        await self.sea_travel_system.create_island(ctx, island_name)

    @commands.command()
    async def islands(self, ctx):
        """List all known islands."""
        await self.sea_travel_system.list_islands(ctx)

    @commands.command()
    async def raid_status(self, ctx):
        """Check the status of the current raid."""
        await self.raid_boss_system.raid_status(ctx)

    @commands.command()
    async def create_crew(self, ctx, *, name: str):
        """Create a new crew (requires a specific role)."""
        await self.crew_battle_system.create_crew(ctx, name)

    @commands.command()
    async def join_crew(self, ctx, *, crew_name: str):
        """Join an existing crew (requires a specific role)."""
        await self.crew_battle_system.join_crew(ctx, crew_name)

    @commands.command()
    async def crew_info(self, ctx, *, crew_name: str = None):
        """View information about a crew."""
        await self.crew_battle_system.crew_info(ctx, crew_name)

    @commands.command()
    async def list_crews(self, ctx):
        """List all crews in the server."""
        await self.crew_battle_system.list_crews(ctx)

    @commands.command()
    async def df_ultimate(self, ctx):
        """Use your awakened Devil Fruit's ultimate ability."""
        await self.devil_fruit_system.devil_fruit_ultimate(ctx)

    @commands.command()
    async def df_mastery(self, ctx):
        """View your Devil Fruit mastery progress."""
        await self.devil_fruit_system.devil_fruit_mastery(ctx)

    @commands.command()
    async def davy_back_stats(self, ctx, member: discord.Member = None):
        """View Davy Back Fight stats for yourself or another member."""
        member = member or ctx.author
        user_data = await self.config.member(member).all()
        wins = user_data.get('davy_back_wins', 0)
        losses = user_data.get('davy_back_losses', 0)
        await ctx.send(f"{member.name}'s Davy Back Fight Record: {wins} wins, {losses} losses")

    @commands.command()
    async def inventory(self, ctx):
        """View your inventory."""
        user_data = await self.config.member(ctx.author).all()
        inventory = user_data.get('inventory', {})
        if not inventory:
            await ctx.send("Your inventory is empty.")
        else:
            inv_list = "\n".join([f"{item}: {quantity}" for item, quantity in inventory.items()])
            await ctx.send(f"Your inventory:\n{inv_list}")

    @commands.command()
    async def buffs(self, ctx):
        """View your active buffs."""
        user_data = await self.config.member(ctx.author).all()
        temp_buffs = user_data.get('temp_buffs', {})
        current_time = ctx.message.created_at.timestamp()
        active_buffs = {buff: (expiry - current_time) / 3600 for buff, expiry in temp_buffs.items() if expiry > current_time}
        if not active_buffs:
            await ctx.send("You have no active buffs.")
        else:
            buff_list = "\n".join([f"{buff}: {hours:.1f} hours remaining" for buff, hours in active_buffs.items()])
            await ctx.send(f"Your active buffs:\n{buff_list}")

    @commands.command()
    async def balance(self, ctx):
        """Check your Berry balance."""
        user_data = await self.config.member(ctx.author).all()
        berries = user_data.get('berries', 0)
        await ctx.send(f"You have {berries} Berries.")

    @commands.command()
    async def devil_fruit_info(self, ctx, *, fruit_name: str = None):
        """Get information about Devil Fruits."""
        await self.devil_fruit_system.devil_fruit_info(ctx, fruit_name)

    @commands.command()
    async def battle(self, ctx, opponent: discord.Member):
        """Start a battle with another player."""
        await self.opcbattle.battle(ctx, opponent)

    @commands.command()
    async def battlestatus(self, ctx):
        """Check the status of your current battle."""
        await self.opcbattle.battlestatus(ctx)

    @commands.command()
    async def choose_class(self, ctx, class_name: str):
        """Choose your character class."""
        await self.character_customization.choose_class(ctx, class_name)

    @commands.command()
    async def choose_fighting_style(self, ctx, *, style: str):
        """Choose your fighting style."""
        await self.character_customization.choose_fighting_style(ctx, style)

    @commands.command()
    async def customize_appearance(self, ctx, *, description: str):
        """Customize your character's appearance."""
        await self.character_customization.customize_appearance(ctx, description=description)

    @commands.command()
    async def character_info(self, ctx):
        """View your character information."""
        await self.character_customization.character_info(ctx)

    @commands.command()
    async def buy_item(self, ctx, item: str, quantity: int = 1):
        """Buy battle items."""
        await self.character_customization.buy_item(ctx, item, quantity)

    @commands.command()
    async def inventory(self, ctx):
        """View your inventory."""
        await self.character_customization.inventory(ctx)

    @commands.command()
    async def use_item(self, ctx, item: str):
        """Use an item from your inventory."""
        await self.character_customization.use_item(ctx, item)

    @commands.command()
    async def surrender(self, ctx):
        """Surrender from your current battle."""
        await self.opcbattle.surrender(ctx)

    @commands.command()
    @commands.is_owner()
    async def clearbattles(self, ctx):
        """Clear all ongoing battles. Use this if battles are stuck."""
        await self.opcbattle.clearbattles(ctx)

    @commands.command()
    async def start_tournament(self, ctx, *participants: discord.Member):
        """Start a battle tournament with multiple participants."""
        await start_tournament(self, ctx, *participants)
    
    @commands.command()
    async def battle_replay(self, ctx, battle_id: int):
        """Watch a replay of a past battle."""
        await battle_replay(self, ctx, battle_id)
    
    @commands.command()
    async def battle_leaderboard(self, ctx):
        """Display the battle leaderboard."""
        await battle_leaderboard(self, ctx)
    
    @commands.command()
    async def battle_quests(self, ctx):
        """View available battle quests."""
        await view_battle_quests(self, ctx)
    
    @commands.command()
    async def join_arena(self, ctx):
        """Join the battle arena queue."""
        await join_arena(self, ctx)
    
    @commands.command()
    async def leave_arena(self, ctx):
        """Leave the battle arena queue."""
        await leave_arena(self, ctx)

    @commands.command()
    async def wins(self, ctx, member: discord.Member = None):
        """Check the number of wins for yourself or another member."""
        if member is None:
            member = ctx.author
        
        user_data = await self.config.member(member).all()
        wins_count = user_data.get('wins', 0)
        await ctx.send(f"{member.name} has {wins_count} battle wins!")
    
    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        """View your or another user's profile."""
        if member is None:
            member = ctx.author

    @commands.command()
    async def teambattle(self, ctx, *members: discord.Member):
        """Start a team battle."""
        await team_battle(self.bot, self.config, ctx, *members)
        
        user_data = await self.config.member(member).all()
        embed = discord.Embed(title=f"{member.name}'s Profile", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)  # Use display_avatar.url instead of avatar_url
        
        embed.add_field(name="Level", value=user_data['level'])
        embed.add_field(name="Exp", value=user_data['exp'])
        embed.add_field(name="Berries", value=user_data['berries'])
        embed.add_field(name="Strength", value=user_data['strength'])
        embed.add_field(name="Defense", value=user_data['defense'])
        embed.add_field(name="Speed", value=user_data['speed'])
        embed.add_field(name="Haki Level", value=user_data['haki_level'])
        embed.add_field(name="Devil Fruit", value=user_data['devil_fruit'] or "None")
        embed.add_field(name="Crew", value=user_data['crew'] or "None")
        embed.add_field(name="Current Island", value=user_data['current_island'])
        
        await ctx.send(embed=embed)

    @commands.command()
    async def help_onepiece(self, ctx):
        """Display help for One Piece Adventures commands."""
        pages = self.create_help_pages()
        await menu(ctx, pages, DEFAULT_CONTROLS, timeout=60)

    def create_help_pages(self):
        pages = []

        # Basic Commands
        embed = discord.Embed(title="One Piece Adventures Help - Basic Commands", color=discord.Color.blue())
        commands = [
            ("profile [member]", "View your or another user's profile"),
            ("train <attribute>", "Train a specific attribute (strength, defense, speed)"),
            ("explore", "Explore the current island for adventures and treasures"),
            ("travel <destination>", "Travel to a different island"),
            ("guide", "Display the One Piece Adventures guide"),
            ("balance", "Check your Berry balance"),
            ("inventory", "View your inventory"),
            ("buffs", "View your active buffs")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Crew Commands
        embed = discord.Embed(title="One Piece Adventures Help - Crew Commands", color=discord.Color.gold())
        commands = [
            ("create_crew <name>", "Create a new pirate crew"),
            ("join_crew <crew_name>", "Join an existing pirate crew"),
            ("crew_battle <opponent_crew>", "Initiate a battle between crews"),
            ("crew_info [crew_name]", "View information about a crew"),
            ("list_crews", "List all crews in the server")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Devil Fruit Commands
        embed = discord.Embed(title="One Piece Adventures Help - Devil Fruit Commands", color=discord.Color.purple())
        commands = [
            ("eat_devil_fruit <fruit_name>", "Eat a Devil Fruit to gain its powers"),
            ("devil_fruit_info [fruit_name]", "Get information about Devil Fruits"),
            ("df_ultimate", "Use your awakened Devil Fruit's ultimate ability"),
            ("df_mastery", "View your Devil Fruit mastery progress")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Marine Commands
        embed = discord.Embed(title="One Piece Adventures Help - Marine Commands", color=discord.Color.blue())
        commands = [
            ("join_marines", "Join the Marines faction"),
            ("marine_mission", "Undertake a Marine mission")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Island and Treasure Commands
        embed = discord.Embed(title="One Piece Adventures Help - Island and Treasure Commands", color=discord.Color.green())
        commands = [
            ("invest_island <island_name> <development>", "Invest in island development"),
            ("find_treasure_map", "Search for a treasure map"),
            ("use_treasure_map", "Use a treasure map to find treasure"),
            ("islands", "List all known islands"),
            ("create_island <island_name>", "Create a new island (Bot owner only)")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Raid Boss Commands
        embed = discord.Embed(title="One Piece Adventures Help - Raid Boss Commands", color=discord.Color.red())
        commands = [
            ("spawn_raid", "Spawns the raid boss"),
            ("join_raid", "Join the active raid boss battle"),
            ("attack_raid_boss", "Attack the active raid boss"),
            ("raid_status", "Check the status of the current raid")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Economy and Trading Commands
        embed = discord.Embed(title="One Piece Adventures Help - Economy and Trading Commands", color=discord.Color.green())
        commands = [
            ("create_listing <item> <price> <quantity>", "Create a market listing to sell an item"),
            ("buy_listing <listing_id>", "Buy an item from the market"),
            ("view_market", "View current market listings")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Reputation and Event Commands
        embed = discord.Embed(title="One Piece Adventures Help - Reputation and Event Commands", color=discord.Color.teal())
        commands = [
            ("view_reputation", "View your reputation with different factions"),
            ("reputation_rewards", "View rewards for your current reputation levels"),
            ("event_status", "Check the status of the current world event"),
            ("challenge", "Challenge the legendary pirate in a showdown"),
            ("research", "Contribute to the research of an ancient weapon"),
            ("trigger_world_event", "Manually trigger a world event (Owner only)")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # Davy Back Fight Commands
        embed = discord.Embed(title="One Piece Adventures Help - Davy Back Fight Commands", color=discord.Color.orange())
        commands = [
            ("davy_back_fight <opponent>", "Challenge another user to a Davy Back Fight"),
            ("davy_back_stats [member]", "View Davy Back Fight stats for yourself or another member")
        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        # advance battle Fight Commands
        embed = discord.Embed(title="One Piece Adventures Help - Advanced Battle Features", color=discord.Color.red())
        commands = [
            ("start_tournament <participants>", "Start a battle tournament"),
            ("team_battle <team1> vs <team2>", "Start a team battle"),
            ("battle_replay <battle_id>", "Watch a replay of a past battle"),
            ("battle_leaderboard", "Display the battle leaderboard"),
            ("battle_quests", "View available battle quests"),
            ("join_arena", "Join the battle arena queue"),
            ("leave_arena", "Leave the battle arena queue")
            ("battle <opponent>", "Start a battle with another player"),
            ("wins [member]", "Check the number of wins for yourself or another member"),

        ]
        for cmd, desc in commands:
            embed.add_field(name=f".{cmd}", value=desc, inline=False)
        pages.append(embed)

        return pages

def setup(bot):
    bot.add_cog(OnePieceAdventures(bot))
