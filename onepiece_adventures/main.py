import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import asyncio
import random
from typing import Dict, List, Any

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
            "market_listings": {}
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
        
        self.bg_task = self.bot.loop.create_task(self.world_events.start_event_loop())

    def cog_unload(self):
        self.bg_task.cancel()

    @commands.command()
    async def ophelp(self, ctx):
        """Display help for One Piece Adventures commands."""
        embed = discord.Embed(title="One Piece AFK Game Help", color=discord.Color.blue())
        
        core_commands = (
            "`.explore_island <island>` - Explore an island for adventures\n"
            "`.crew_battle <opponent_crew>` - Initiate a battle between crews\n"
            "`.train_haki` - Train your Haki to increase its level\n"
            "`.learn_skill` - Learn a new skill based on your character class\n"
            "`.use_devil_fruit <fruit_name>` - Use a Devil Fruit from your inventory"
        )
        embed.add_field(name="Core Commands", value=core_commands, inline=False)
        
        info_commands = (
            "`.profile [member]` - View your or another user's profile\n"
            "`.inventory` - View your inventory\n"
            "`.leaderboard [category]` - View the leaderboard for a specific category"
        )
        embed.add_field(name="Information Commands", value=info_commands, inline=False)
        
        other_commands = (
            "`.trade <partner> <item>` - Trade an item with another user\n"
            "`.form_alliance <ally_crew>` - Form an alliance with another crew\n"
            "`.davy_back_fight <opponent>` - Challenge another user to a Davy Back Fight\n"
            "`.choose_class <class_name>` - Choose your character class"
        )
        embed.add_field(name="Other Commands", value=other_commands, inline=False)
        
        game_mechanics = (
            "• Explore islands to gain experience, bounty, and items\n"
            "• Train your Haki and learn skills to become stronger\n"
            "• Form or join a crew to participate in crew battles\n"
            "• Find and use Devil Fruits for unique powers\n"
            "• Watch out for World Government interventions and seasonal events!"
        )
        embed.add_field(name="Game Mechanics", value=game_mechanics, inline=False)
        
        await ctx.send(embed=embed)

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
    async def explore_island(self, ctx, island: str):
        """Explore an island for adventures."""
        await self.sea_travel_system.explore_current_island(ctx)

    @commands.command()
    async def train_haki(self, ctx):
        """Train your Haki to increase its level."""
        # Implement haki training logic here
        await ctx.send("You've trained your Haki. It's becoming stronger!")

    @commands.command()
    async def learn_skill(self, ctx):
        """Learn a new skill based on your character class."""
        # Implement skill learning logic here
        await ctx.send("You've learned a new skill!")

    @commands.command()
    async def use_devil_fruit(self, ctx, fruit_name: str):
        """Use a Devil Fruit from your inventory."""
        await self.devil_fruit_system.eat_devil_fruit(ctx, fruit_name)

    @commands.command()
    async def inventory(self, ctx):
        """View your inventory."""
        # Implement inventory viewing logic here
        await ctx.send("Here's your inventory: [Placeholder for inventory items]")

    @commands.command()
    async def leaderboard(self, ctx, category: str = "bounty"):
        """View the leaderboard for a specific category."""
        # Implement leaderboard logic here
        await ctx.send(f"Here's the leaderboard for {category}: [Placeholder for leaderboard]")

    @commands.command()
    async def trade(self, ctx, partner: discord.Member, item: str):
        """Trade an item with another user."""
        # Implement trading logic here
        await ctx.send(f"You've initiated a trade with {partner.name} for {item}.")

    @commands.command()
    async def form_alliance(self, ctx, ally_crew: str):
        """Form an alliance with another crew."""
        # Implement alliance formation logic here
        await ctx.send(f"You've formed an alliance with {ally_crew}!")

    @commands.command()
    async def choose_class(self, ctx, class_name: str):
        """Choose your character class."""
        # Implement class selection logic here
        await ctx.send(f"You've chosen the {class_name} class!")

    @commands.command()
    async def train(self, ctx, attribute: str):
        """Train a specific attribute (strength, defense, speed)."""
        await self.training_system.train_attribute(ctx, attribute)

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
        """Challenge another player to a Davy Back Fight."""
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
    async def dock(self, ctx, island_name: str):
        """Dock your ship at an island with a port."""
        await self.sea_travel_system.dock_at_port(ctx, island_name)

    @commands.command()
    async def fish(self, ctx):
        """Go fishing while docked at an island."""
        await self.sea_travel_system.start_fishing(ctx)

    @commands.command()
    async def upgrade_ship(self, ctx, upgrade: str):
        """Upgrade a part of your ship."""
        await self.sea_travel_system.upgrade_ship(ctx, upgrade)

    @commands.command()
    async def view_ship(self, ctx):
        """View your ship's current upgrades."""
        await self.sea_travel_system.view_ship(ctx)

    @commands.command()
    async def check_island(self, ctx):
        """Check information about your current island."""
        await self.sea_travel_system.check_island(ctx)

    @commands.command()
    async def list_islands(self, ctx):
        """List all known islands."""
        await self.sea_travel_system.list_islands(ctx)

    @commands.command()
    @commands.is_owner()
    async def create_island(self, ctx, island_name: str):
        """Create a new island (Bot owner only)."""
        await self.sea_travel_system.create_island(ctx, island_name)

    @commands.command()
    @commands.is_owner()
    async def add_island_development(self, ctx, island_name: str, development: str):
        """Add a development to an island (Bot owner only)."""
        await self.sea_travel_system.add_island_development(ctx, island_name, development)

def setup(bot):
    bot.add_cog(OnePieceAdventures(bot))
