import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
import random
import asyncio
import traceback

DEVIL_FRUITS = [
    {"name": "Gomu Gomu no Mi", "image": "https://i.pngimg.me/thumb/f/720/comhiclipartficgr.jpg"},
    {"name": "Mera Mera no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/8/8c/Mera_Mera_no_Mi_Infobox.png"},
    {"name": "Hie Hie no Mi", "image": "https://static.wikia.nocookie.net/grand-piece-online/images/7/7f/819439725621936148.v3.png"},
    {"name": "Pika Pika no Mi", "image": "https://static.wikia.nocookie.net/mineminenomi/images/2/24/Pika_Pika_no_Mi.png"},
    {"name": "Gura Gura no Mi", "image": "https://static.wikia.nocookie.net/oproleplaying/images/f/fd/Gura_Gura_Infobox.png"},
    {"name": "Magu Magu no Mi", "image": "https://static.wikia.nocookie.net/grand-piece-online/images/8/8a/Magu-new-fruit-pngpng.png"},
    {"name": "Yami Yami no Mi", "image": "https://static.wikia.nocookie.net/oproleplaying/images/f/f5/Yami_Yami_no_Mi_Infobox.png"},
    {"name": "Ope Ope no Mi", "image": "https://ih1.redbubble.net/image.4593188434.6206/raf,360x360,075,t,fafafa:ca443f4786.jpg"},
    {"name": "Ito Ito no Mi", "image": "https://ih1.redbubble.net/image.1665161227.2240/st,small,507x507-pad,600x600,f8f8f8.jpg"},
    {"name": "Bari Bari no Mi", "image": "https://static.wikia.nocookie.net/oproleplaying/images/b/b0/BariBari.png"},
    {"name": "Bomu Bomu no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/1/1a/Bomu_Bomu_no_Mi_Infobox.png"},
    {"name": "Doku Doku no Mi", "image": "https://static.wikia.nocookie.net/oproleplaying/images/d/dc/Doku_Doku_no_Mi.png"},
    {"name": "Goro Goro no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/d/d2/Goro_Goro_no_Mi_Infobox.png"},
    {"name": "Hana Hana no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/2/21/Hana_Hana_no_Mi_Infobox.png"},
    {"name": "Horo Horo no Mi", "image": "https://static.wikia.nocookie.net/oproleplaying/images/3/38/Horo.png"},
    {"name": "Kilo Kilo no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/8/89/Kiro_Kiro_no_Mi_Infobox.png"},
    {"name": "Moku Moku no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/8/8d/Moku_Moku_no_Mi_Infobox.png"},
    {"name": "Neko Neko no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/9/98/Neko_Neko_no_Mi%2C_Model_Leopard_Infobox.png"},
    {"name": "Tori Tori no Mi", "image": "https://static.wikia.nocookie.net/onepiecefanon/images/6/68/Phoenix_Infobox.jpeg"},
    {"name": "Ushi Ushi no Mi", "image": "https://static.wikia.nocookie.net/onepiece/images/b/bf/Ushi_Ushi_no_Mi%2C_Model_Bison_Infobox.png"},
    {"name": "Zou Zou no Mi", "image": "https://static.wikia.nocookie.net/oproleplaying/images/9/9e/One_Piece_Zou_Zou_no_Mi_Model_Brufaldi.png"},
    {"name": "Yuki Yuki no Mi", "image": "https://static.wikia.nocookie.net/mineminenomi/images/9/96/Yuki_Yuki_no_Mi.png"},
    {"name": "Zushi Zushi no Mi", "image": "https://static.wikia.nocookie.net/grand-piece-online/images/9/9a/Zushi-new-fruit-pngpng.png"},
]

RARE_TITLE_NAMES = {
    "Emperor": ["Big Mom", "Kaido", "Shanks", "Blackbeard"],
    "Pirate King": ["Gol D. Roger"],
    "Admiral": ["Kizaru", "Akainu", "Aokiji", "Fujitora"],
    "Fleet Admiral": ["Sengoku"],
    "Gorosei": ["Saint Jaygarcia Saturn", "Saint Shepherd Ju Peter", "Saint Ethanbaron V. Nasujuro", "Saint Topman Valkyrie", "Saint Marcus Mars"]
}

PIRATE_TITLES = [
    "Chore Boy", "Seaman Recruit", "Seaman Apprentice", "Seaman First Class", "Petty Officer", "Chief Petty Officer",
    "Master Chief Petty Officer", "Warrant Officer", "Ensign", "Lieutenant Junior Grade", "Lieutenant",
    "Lieutenant Commander", "Commander", "Captain", "Rear Admiral", "Vice Admiral", "Admiral", "Fleet Admiral",
    "Commander n Cheif", "Cypher Pol", "Aegis: Cp0", "SWORD", "God Knights", "Kong", "Gorosei", "Imu",
    "Apprentice", "Combatant", "Officers", "Chief of Staff", "First Mate", "Pirate Captain", "Super Nova", "Warlords",
    "Worst Generation", "Emperor", "Pirate King"
]

MARINE_TITLES = [
    "Chore Boy", "Seaman Recruit", "Seaman Apprentice", "Seaman First Class", "Petty Officer", "Chief Petty Officer",
    "Master Chief Petty Officer", "Warrant Officer", "Ensign", "Lieutenant Junior Grade", "Lieutenant",
    "Lieutenant Commander", "Commander", "Captain", "Rear Admiral", "Vice Admiral", "Admiral", "Fleet Admiral",
    "Commander n Cheif", "Cypher Pol", "Aegis: Cp0", "SWORD", "God Knights", "Kong", "Gorosei", "Imu"
]

RARE_TITLES = {
    "Pirate": ["Pirate King", "Emperor"],
    "Marine": ["Imu", "Gorosei", "Kong", "God Knights"]
}

DEFAULT_BOUNTY_EMOJI = ":moneybag:"
DEFAULT_STAR_EMOJI = ":star:"
SEAS = ["East Blue", "West Blue", "North Blue", "South Blue", "Grand Line", "New World"]

SPECIAL_USER_ID = 238475762724896774  # Replace with the actual special user ID
LOG_CHANNEL_ID = 748451591958429809  # Replace with the actual log channel ID

class OnePieceCog(commands.Cog):
    """A comprehensive One Piece themed cog for Red's Discord bot, including battles."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_member = {
            "faction": None,
            "stats": {
                "strength": 0,
                "agility": 0,
                "intelligence": 0,
            },
            "title": None,
            "devil_fruit": None,
            "haki": {
                "observation": 0,
                "armament": 0,
                "conqueror": 0,
            },
            "race": None,
            "profile_locked": False,
            "sea": None,
            "wins": 0,
            "bounty": 0,
            "stars": 0,
            "mentor": None,
        }
        self.config.register_member(**default_member)
        self.config.register_guild(battle_channel=None, bounty_emoji=DEFAULT_BOUNTY_EMOJI, star_emoji=DEFAULT_STAR_EMOJI, bounty_milestone_channel=None)
        
        self.health = {}
        self.attacker = None
        self.defender = None
        self.battle_in_progress = False
        self.blackbeard_taken = False
        self.sun_god_nika_taken = False

    async def log_error(self, ctx, error):
        """Log error messages to the designated log channel."""
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            await log_channel.send(f"Error in {ctx.command}:\n{''.join(tb)}")

    @commands.command(name="status")
    async def check_status(self, ctx, member: discord.Member = None):
        """Check your faction and stats."""
        try:
            member = member or ctx.author
            if not await self.config.member(member).profile_locked():
                await ctx.send(f"{member.display_name} has not started their journey yet. Use `.setsail` to begin.")
                return

            faction = await self.config.member(member).faction()
            stats = await self.config.member(member).stats()
            title = await self.config.member(member).title()
            devil_fruit = await self.config.member(member).devil_fruit()
            haki = await self.config.member(member).haki()
            race = await self.config.member(member).race()
            sea = await self.config.member(member).sea()
            wins = await self.config.member(member).wins()
            mentor = await self.config.member(member).mentor()
            bounty_emoji = await self.config.guild(ctx.guild).bounty_emoji()
            star_emoji = await self.config.guild(ctx.guild).star_emoji()

            embed = discord.Embed(title=f"{member.display_name}'s Status")
            if faction == "Marine":
                embed.color = discord.Color.blue()
                embed.set_thumbnail(url="https://i.imgur.com/8K8xDBu.png")
            elif faction == "Pirate":
                embed.color = discord.Color.red()
                embed.set_thumbnail(url="https://i.imgur.com/1JgImnJ.png")
            else:
                embed.color = discord.Color.default()

            embed.add_field(name="🏴‍☠️ Faction", value=faction if faction else "None", inline=True)
            embed.add_field(name="🏅 Title", value=title if title else "None", inline=True)
            embed.add_field(name="🍇 Devil Fruit", value=devil_fruit if devil_fruit else "None", inline=True)
            embed.add_field(name="🧠 Intelligence", value=stats["intelligence"], inline=True)
            embed.add_field(name="💪 Strength", value=stats["strength"], inline=True)
            embed.add_field(name="⚡ Agility", value=stats["agility"], inline=True)
            embed.add_field(name="👁️ Observation Haki", value=haki["observation"], inline=True)
            embed.add_field(name="🛡️ Armament Haki", value=haki["armament"], inline=True)
            embed.add_field(name="⚔️ Conqueror's Haki", value=haki["conqueror"], inline=True)
            embed.add_field(name="🏹 Race", value=race if race else "None", inline=True)
            embed.add_field(name="🌊 Sea", value=sea if sea else "None", inline=True)
            embed.add_field(name="🏆 Wins", value=wins, inline=True)

            if faction == "Pirate":
                bounty = await self.config.member(member).bounty()
                embed.add_field(name="\u200b", value="\u200b", inline=True)
                embed.add_field(name="💰 Bounty", value=f"{bounty} {bounty_emoji}", inline=False)
                embed.add_field(name="\u200b", value="\u200b", inline=True)
            else:
                stars = await self.config.member(member).stars()
                embed.add_field(name="\u200b", value="\u200b", inline=True)
                embed.add_field(name="⭐ Stars", value=f"{stars} {star_emoji}", inline=False)
                embed.add_field(name="\u200b", value="\u200b", inline=True)

            embed.set_footer(text=f"🧙 Mentor: {mentor if mentor else 'None'}")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="setsail")
    async def new_journey(self, ctx):
        """Start a new journey with randomized settings."""
        try:
            profile_locked = await self.config.member(ctx.author).profile_locked()
            if profile_locked:
                await ctx.send("Your profile is already set. Check your status with `.status`.")
                return

            faction = random.choice(["Pirate", "Marine"])

            # Special handling for the user with ID SPECIAL_USER_ID
            if ctx.author.id == SPECIAL_USER_ID:
                faction = "Pirate"
                stats = {
                    "strength": 150,
                    "agility": 50,
                    "intelligence": 100,
                }
                title = "Mihawk"
                race = "Lunarian"
                haki = {
                    "observation": "Future Sight",
                    "armament": "Internal Destruction",
                    "conqueror": "Observation Killing"
                }
                await self.config.member(ctx.author).faction.set(faction)
                await self.config.member(ctx.author).stats.set(stats)
                await self.config.member(ctx.author).title.set(title)
                await self.config.member(ctx.author).race.set(race)
                await self.config.member(ctx.author).haki.set(haki)
                await self.config.member(ctx.author).profile_locked.set(True)
                await self.config.member(ctx.author).mentor.set("Mihawk")
                await self.config.member(ctx.author).sea.set("West Blue")
                await ctx.send("You are now Mihawk with high stats, the title of Emperor, and the Lunarian race. You cannot gain new titles or Devil Fruits.")
                return
            
            stats = {
                "strength": random.randint(1, 20),
                "agility": random.randint(1, 20),
                "intelligence": random.randint(1, 20),
            }
            haki = {
                "observation": "Future Sight",
                "armament": random.choice(["Spiritual Armor", "Hardening", "Imbuement", "Emission", "Internal Destruction", "Tribal Haki"]),
                "conqueror": random.choice(["Infusion", "Observation Killing"]),
            }
            race = random.choice(["Human", "Fishman", "Merfolk", "Giant", "Dwarf", "Mink", "Lunarian", "Skypiean", "Longarm Tribe", "Longleg Tribe"])

            await self.config.member(ctx.author).faction.set(faction)
            await self.config.member(ctx.author).stats.set(stats)
            await self.config.member(ctx.author).haki.set(haki)
            await self.config.member(ctx.author).race.set(race)
            await self.config.member(ctx.author).profile_locked.set(True)

            await self.assign_roles(ctx, ctx.author)
            
            await ctx.send(f"{ctx.author.display_name}, your new journey has begun! Check your status with `.status`.")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="resetprofile")
    @checks.is_owner()
    async def reset_profile(self, ctx, member: discord.Member):
        """Reset a user's profile. Bot owner only."""
        try:
            await self.config.member(member).clear()
            await self.remove_roles(ctx, member)
            await ctx.send(f"{member.display_name}'s profile has been reset. They can now start a new journey.")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="assignroles")
    @checks.admin_or_permissions(manage_guild=True)
    async def assign_roles(self, ctx, member: discord.Member = None):
        """Assign custom roles based on faction and title to a member or all members with profiles."""
        try:
            if member:
                await self.assign_role_to_member(ctx, member)
            else:
                all_members = await self.config.all_members(ctx.guild)
                for member_id in all_members:
                    member = ctx.guild.get_member(member_id)
                    if member:
                        await self.assign_role_to_member(ctx, member)
        except Exception as e:
            await self.log_error(ctx, e)

    async def assign_role_to_member(self, ctx, member: discord.Member):
        """Assign a custom role based on faction and title to a single member."""
        faction = await self.config.member(member).faction()
        title = await self.config.member(member).title()

        if not faction or not title:
            return

        role_name = f"{faction} {title}"
        role_color = discord.Color.blue() if faction == "Marine" else discord.Color.red()
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            role = await ctx.guild.create_role(name=role_name, color=role_color, hoist=True)

        await self.remove_roles(ctx, member)
        await member.add_roles(role)

    async def remove_roles(self, ctx, member: discord.Member):
        """Remove all custom roles from the user."""
        try:
            roles_to_remove = []
            for role in member.roles:
                if role.name.startswith("Pirate") or role.name.startswith("Marine"):
                    roles_to_remove.append(role)
            
            await member.remove_roles(*roles_to_remove)
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="setbattlechannel")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_battle_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where battles can take place."""
        try:
            await self.config.guild(ctx.guild).battle_channel.set(channel.id)
            await ctx.send(f"Battle channel set to {channel.mention}.")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="joinsea")
    async def join_sea(self, ctx, *, sea: str):
        """Join a sea and get ready for battles."""
        try:
            sea = sea.title()
            if sea not in SEAS:
                await ctx.send(f"Invalid sea! Choose from: {', '.join(SEAS)}")
                return

            await self.config.member(ctx.author).sea.set(sea)
            await ctx.send(f"{ctx.author.display_name} has joined the {sea}!")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="battle")
    async def battle(self, ctx, opponent: discord.Member = None):
        """Initiate a turn-based battle."""
        try:
            battle_channel_id = await self.config.guild(ctx.guild).battle_channel()
            if battle_channel_id and ctx.channel.id != battle_channel_id:
                await ctx.send(f"Battles can only be initiated in the designated channel.")
                return

            if self.battle_in_progress:
                await ctx.send("A battle is already in progress! ⏳")
                return

            if not opponent:
                potential_opponents = [member for member in ctx.guild.members if member != ctx.author and await self.config.member(member).profile_locked()]
                if not potential_opponents:
                    await ctx.send("No available opponents found.")
                    return
                opponent = random.choice(potential_opponents)

            if ctx.author.id == opponent.id:
                await ctx.send("You cannot battle yourself! 🤦")
                return

            if ctx.author in self.health or opponent in self.health:
                await ctx.send("A battle is already in progress! ⏳")
                return

            author_sea = await self.config.member(ctx.author).sea()
            opponent_sea = await self.config.member(opponent).sea()
            if author_sea is None or opponent_sea is None:
                await ctx.send("Both participants must join a sea using the `.joinsea` command first!")
                return

            self.health[ctx.author] = 100
            self.health[opponent] = 100
            self.attacker = ctx.author
            self.defender = opponent
            self.battle_in_progress = True

            await self.auto_battle(ctx)
        except Exception as e:
            await self.log_error(ctx, e)

    def create_health_bar(self, health):
        """Create a One Piece-themed health bar."""
        health = max(0, health)  # Ensure health does not go below 0
        total_blocks = 10
        filled_blocks = int(health / 10)
        empty_blocks = total_blocks - filled_blocks

        filled_emoji = "🍖"
        empty_emoji = "🦴"

        return f"{filled_emoji * filled_blocks}{empty_emoji * empty_blocks} {health}/100"

    async def auto_battle(self, ctx):
        """Simulate a turn-based battle until one player's HP reaches 0."""
        try:
            embed = discord.Embed(title="⚔️ Battle in Progress ⚔️", color=discord.Color.blue())
            embed.add_field(name=f"{self.attacker.display_name} vs. {self.defender.display_name}",
                            value=f"{self.attacker.display_name} HP: {self.create_health_bar(self.health[self.attacker])}\n"
                                  f"{self.defender.display_name} HP: {self.create_health_bar(self.health[self.defender])}",
                            inline=False)
            message = await ctx.send(embed=embed)

            while self.battle_in_progress:
                await asyncio.sleep(1)  # Wait for 1 second between each turn

                # Check if the attacker or defender uses Haki
                attacker_uses_haki = random.choice([True, False])
                defender_uses_haki = random.choice([True, False])

                # Calculate base damage
                base_damage = random.randint(10, 20)
                
                # Special attack and defense for SPECIAL_USER_ID
                if self.attacker.id == SPECIAL_USER_ID:
                    attack_ability_description = f"{self.attacker.display_name} swung his Yoru ⚔️ dealing {base_damage} damage."
                else:
                    attack_ability_description = f"{self.attacker.display_name} attacked ⚔️ dealing {base_damage} damage."

                # Apply special user attack bonus
                if self.attacker.id == SPECIAL_USER_ID:
                    base_damage *= 1.5

                # Attacker uses Haki for attack
                if attacker_uses_haki:
                    base_damage += random.randint(5, 10)
                    attack_ability_description = f"{self.attacker.display_name} has landed a hit by coating their weapon with Armament Haki 🗡️ dealing {base_damage} damage."

                # Defender uses Haki for defense
                if defender_uses_haki:
                    base_damage_reduction = random.randint(1, 5)
                    base_damage -= base_damage_reduction
                    defense_ability_description = f"{self.defender.display_name} defended by coating themselves in Armament Haki 🛡️ reducing damage by {base_damage_reduction}!"
                    # Chance to negate the attack entirely
                    if random.random() < 0.2:  # 20% chance to negate
                        base_damage = 0
                        defense_ability_description = f"{self.defender.display_name} defended perfectly with Armament Haki 🛡️ negating all damage!"
                else:
                    # Special defense for SPECIAL_USER_ID
                    if self.defender.id == SPECIAL_USER_ID:
                        defense_ability_description = f"{self.defender.display_name} blocked with his Yoru 🛡️."
                    else:
                        defense_ability_description = f"{self.defender.display_name} defended 🛡️."

                # Calculate hit type (regular, crit, or massive)
                hit_type = random.choices(["Regular", "Crit", "Massive"], weights=[0.85, 0.1, 0.05], k=1)[0]
                if hit_type == "Regular":
                    damage = base_damage
                elif hit_type == "Crit":
                    damage = base_damage * 2
                    attack_ability_description = f"{self.attacker.display_name} attacked with a CRIT ⚔️⚡️ dealing {damage}damage."
                else:  # Massive
                    damage = base_damage * 3
                    await ctx.send(f"{self.attacker.display_name} has landed a MASSIVE CRITICAL HIT 💥 by using Conqueror's Haki on {self.defender.display_name} dealing {damage}!")

                # Apply special user defense penalty
                if self.defender.id == SPECIAL_USER_ID:
                    damage *= 1.5

                self.health[self.defender] -= damage

                embed.set_field_at(0, name=f"⚔️ {self.attacker.display_name} vs. {self.defender.display_name} ⚔️",
                                   value=f"{attack_ability_description}\n"
                                         f"{defense_ability_description}\n\n"
                                         f"{self.attacker.display_name} HP: {self.create_health_bar(self.health[self.attacker])}\n"
                                         f"{self.defender.display_name} HP: {self.create_health_bar(self.health[self.defender])}",
                                   inline=False)
                await message.edit(embed=embed)

                if self.health[self.defender] <= 0:
                    winner = self.attacker
                    loser = self.defender
                    await self.update_wins(winner)
                    await self.handle_winner(ctx, winner, loser)
                    self.battle_in_progress = False
                    self.reset_battle()
                    return

                # Switch attacker and defender
                self.attacker, self.defender = self.defender, self.attacker
        except Exception as e:
            await self.log_error(ctx, e)

    async def handle_winner(self, ctx, winner, loser):
        """Handle the victory process for the winner."""
        try:
            faction = await self.config.member(winner).faction()
            current_title = await self.config.member(winner).title()
            wins = await self.config.member(winner).wins()
            current_bounty = await self.config.member(winner).bounty()
            stars = await self.config.member(winner).stars()
            bounty_emoji = await self.config.guild(ctx.guild).bounty_emoji()
            star_emoji = await self.config.guild(ctx.guild).star_emoji()
            bounty_milestone_channel_id = await self.config.guild(ctx.guild).bounty_milestone_channel()
            bounty_milestone_channel = ctx.guild.get_channel(bounty_milestone_channel_id)

            bounty_increase = 0  # Initialize bounty_increase
            new_bounty = current_bounty  # Initialize new_bounty with current bounty

            if faction is None:
                faction = "Pirate"  # Default faction if not set
                await self.config.member(winner).faction.set(faction)

            # Calculate bounty or star increase
            if faction == "Pirate":
                if wins < 10:
                    bounty_increase = random.randint(50, 100)
                elif wins < 20:
                    bounty_increase = random.randint(100, 200)
                elif wins < 30:
                    bounty_increase = random.randint(300, 500)
                else:
                    bounty_increase = random.randint(500, 1000)

                new_bounty = current_bounty + bounty_increase
                await self.config.member(winner).bounty.set(new_bounty)

                # Log the bounty if it hits milestones
                if new_bounty % 1000 == 0 and bounty_milestone_channel:
                    embed = discord.Embed(title="Bounty Milestone! 🎉", description=f"{winner.display_name} has reached a bounty of {new_bounty} {bounty_emoji}!", color=discord.Color.gold())
                    await bounty_milestone_channel.send(embed=embed)
            else:
                if wins < 10:
                    stars += 1 if random.random() < 0.5 else 0
                elif wins < 20:
                    stars += 1 if random.random() < 0.3 else 0
                elif wins < 30:
                    stars += 1 if random.random() < 0.2 else 0
                elif wins < 40:
                    stars += 1 if random.random() < 0.1 else 0
                elif wins < 50:
                    stars += 1 if random.random() < 0.05 else 0
                elif wins >= 50:
                    stars += 1 if random.random() < 0.01 else 0
                stars = min(stars, 2000)  # Cap stars at 2000
                await self.config.member(winner).stars.set(stars)
                # Log the stars if they hit milestones
                if stars > 0 and bounty_milestone_channel:
                    embed = discord.Embed(title="Star Milestone! 🌟", description=f"{winner.display_name} has earned a new star! They now have {stars} {star_emoji}!", color=discord.Color.blue())
                    await bounty_milestone_channel.send(embed=embed)

            # Assign new title based on bounty and wins
            new_title = None
            if faction == "Pirate":
                if wins == 1 and new_bounty < 100:
                    new_title = "Apprentice"
                elif wins >= 10 and new_bounty >= 1000:
                    new_title = "Combatant"
                elif wins >= 20 and new_bounty >= 2000:
                    new_title = "Officers"
                elif wins >= 30 and new_bounty >= 3000:
                    new_title = "Chief of Staff"
                elif wins >= 40 and new_bounty >= 4000:
                    new_title = "First Mate"
                elif wins >= 50 and new_bounty >= 5000:
                    new_title = "Pirate Captain"
                elif wins > 50 and new_bounty > 10000 and random.random() < 0.05:
                    new_title = "Super Nova"
                elif wins > 60 and new_bounty > 20000 and random.random() < 0.05:
                    new_title = "Warlords"
                elif wins > 70 and new_bounty > 30000 and random.random() < 0.05:
                    new_title = "Worst Generation"
                elif wins > 80 and new_bounty >= 3000000000 and new_bounty <= 5000000000 and random.random() < 0.05:
                    new_title = "Emperor"
                elif wins > 90 and new_bounty >= 5564800000 and random.random() < 0.05:
                    new_title = "Pirate King"
            else:
                if wins == 1 and stars < 10:
                    new_title = "Chore Boy"
                elif wins >= 10 and stars >= 10:
                    new_title = "Seaman Recruit"
                elif wins >= 20 and stars >= 20:
                    new_title = "Seaman Apprentice"
                elif wins >= 30 and stars >= 30:
                    new_title = "Seaman First Class"
                elif wins >= 40 and stars >= 40:
                    new_title = "Petty Officer"
                elif wins >= 50 and stars >= 50:
                    new_title = "Chief Petty Officer"
                elif wins > 50 and stars > 100 and random.random() < 0.05:
                    new_title = "Master Chief Petty Officer"
                elif wins > 60 and stars > 200 and random.random() < 0.05:
                    new_title = "Warrant Officer"
                elif wins > 70 and stars > 300 and random.random() < 0.05:
                    new_title = "Ensign"
                elif wins > 80 and stars > 400 and random.random() < 0.05:
                    new_title = "Lieutenant Junior Grade"
                elif wins > 90 and stars > 500 and random.random() < 0.05:
                    new_title = "Lieutenant"
                elif wins > 100 and stars > 600 and random.random() < 0.05:
                    new_title = "Lieutenant Commander"
                elif wins > 110 and stars > 700 and random.random() < 0.05:
                    new_title = "Commander"
                elif wins > 120 and stars > 800 and random.random() < 0.05:
                    new_title = "Captain"
                elif wins > 130 and stars > 900 and random.random() < 0.05:
                    new_title = "Rear Admiral"
                elif wins > 140 and stars > 1000 and random.random() < 0.05:
                    new_title = "Vice Admiral"
                elif wins > 150 and stars > 1100 and random.random() < 0.05:
                    new_title = "Admiral"
                elif wins > 160 and stars > 1200 and random.random() < 0.05:
                    new_title = "Fleet Admiral"
                elif wins > 170 and stars > 1300 and random.random() < 0.05:
                    new_title = "Commander n Cheif"
                elif wins > 180 and stars > 1400 and random.random() < 0.05:
                    new_title = "Cypher Pol"
                elif wins > 190 and stars > 1500 and random.random() < 0.05:
                    new_title = "Aegis: Cp0"
                elif wins > 200 and stars > 1600 and random.random() < 0.05:
                    new_title = "SWORD"
                elif wins > 210 and stars > 1700 and random.random() < 0.05:
                    new_title = "God Knights"
                elif wins > 220 and stars > 1800 and random.random() < 0.05:
                    new_title = "Kong"
                elif wins > 230 and stars > 1900 and random.random() < 0.005:
                    new_title = "Gorosei"
                elif wins > 240 and stars > 2000 and random.random() < 0.0005:
                    new_title = "Imu"

            if new_title and new_title != current_title:
                await self.config.member(winner).title.set(new_title)
                await self.remove_roles(ctx, winner)  # Remove old role
                await self.assign_roles(ctx, winner)  # Assign new role

            # Assign devil fruit only on first win
            if wins == 1 and winner.id != SPECIAL_USER_ID:
                devil_fruit = random.choice(DEVIL_FRUITS)
                await self.config.member(winner).devil_fruit.set(devil_fruit["name"])
                await self.send_first_victory_embed(ctx, winner, loser, bounty_increase, new_bounty, new_title, devil_fruit["name"], devil_fruit["image"], bounty_emoji)
            else:
                await self.send_victory_embed(ctx, winner, loser, bounty_increase, new_bounty, new_title, bounty_emoji)

            if new_title in RARE_TITLES.get(faction, []):
                await self.assign_rare_title(winner, new_title)

            # Update stats based on wins
            await self.update_stats(winner)
        except Exception as e:
            await self.log_error(ctx, e)

    async def update_stats(self, winner):
        """Update stats based on wins."""
        try:
            wins = await self.config.member(winner).wins()
            stats = await self.config.member(winner).stats()

            if wins < 10:
                stat_increase = random.randint(1, 2)
            elif wins < 20:
                stat_increase = random.randint(2, 3)
            elif wins < 30:
                stat_increase = random.randint(3, 4)
            else:
                stat_increase = random.randint(4, 5)

            stats["strength"] += stat_increase
            stats["agility"] += stat_increase
            stats["intelligence"] += stat_increase

            await self.config.member(winner).stats.set(stats)
        except Exception as e:
            await self.log_error(ctx, e)

    async def assign_rare_title(self, winner, title):
        """Assign a rare title to the winner if eligible."""
        try:
            faction = await self.config.member(winner).faction()
            if title in RARE_TITLES.get(faction, []):
                mentor_list = RARE_TITLE_NAMES[title]
                if title == "Emperor" and not self.blackbeard_taken and random.randint(1, 4) == 1:
                    await self.config.member(winner).devil_fruit.set("Yami Yami no Mi, Gura Gura no Mi")
                    self.blackbeard_taken = True
                    await self.config.member(winner).mentor.set("Blackbeard")
                elif title == "Emperor" and not self.sun_god_nika_taken and random.randint(1, 4) == 1:
                    await self.config.member(winner).devil_fruit.set("Gomu Gomu no Mi (Awakened)")
                    self.sun_god_nika_taken = True
                    await self.config.member(winner).mentor.set("Sun God Nika")
                else:
                    available_mentors = [m for m in mentor_list if m not in (await self.get_all_mentors(title))]
                    if available_mentors:
                        mentor = random.choice(available_mentors)
                        await self.config.member(winner).mentor.set(mentor)
        except Exception as e:
            await self.log_error(ctx, e)

    async def get_all_mentors(self, title):
        """Get all mentors for a given title."""
        try:
            all_members = await self.config.all_members()
            mentors = []
            for member_id in all_members:
                member_data = all_members[member_id]
                if member_data.get("title") == title and member_data.get("mentor"):
                    mentors.append(member_data["mentor"])
            return mentors
        except Exception as e:
            await self.log_error(ctx, e)
            return []

    async def send_first_victory_embed(self, ctx, winner, loser, bounty_increase, new_bounty, new_title, devil_fruit, devil_fruit_image, bounty_emoji):
        """Send a victory embed for the first win with a random Devil Fruit, title, and bounty."""
        try:
            embed = discord.Embed(title="🏆 Battle Over 🏆", description=f"{winner.display_name} has become victorious by defeating {loser.display_name}!", color=discord.Color.gold())
            reward_message = f"{winner.display_name} has been awarded the title: **{new_title}** 🏅, the Devil Fruit: **{devil_fruit}** 🍇"
            if bounty_increase > 0:
                reward_message += f"Bounty has increased by {bounty_increase} {bounty_emoji} totaling their new bounty at {new_bounty} {bounty_emoji}"
            embed.add_field(name="Reward", value=reward_message)
            embed.set_thumbnail(url=devil_fruit_image)
            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

    async def send_victory_embed(self, ctx, winner, loser, bounty_increase, new_bounty, new_title, bounty_emoji):
        """Send a victory embed for subsequent wins with bounty increase."""
        try:
            embed = discord.Embed(title="🏆 Battle Over 🏆", description=f"{winner.display_name} has become victorious by defeating {loser.display_name}!", color=discord.Color.gold())

            reward_message = ""
            if new_title and new_title != await self.config.member(winner).title():
                reward_message += f"{winner.display_name} has been awarded the title: **{new_title}** 🏅"
            if bounty_increase > 0:
                reward_message += f"Bounty has increased by {bounty_increase} {bounty_emoji} totaling their new bounty at {new_bounty} {bounty_emoji}"

            embed.add_field(name="Reward", value=reward_message)
            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

    async def update_wins(self, winner):
        """Update the win count for the winner."""
        try:
            current_wins = await self.config.member(winner).wins()
            await self.config.member(winner).wins.set(current_wins + 1)
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="bustercall")
    @checks.is_owner()
    async def buster_call(self, ctx, member: discord.Member = None):
        """Reset the title, Devil Fruit, and wins of a member, or all members if no member is specified."""
        try:
            if member:
                await self.config.member(member).clear()
                await self.remove_roles(ctx, member)
                await ctx.send(f"{member.display_name}'s title, Devil Fruit, and wins have been reset.")
            else:
                all_members = await self.config.all_members(ctx.guild)
                for member_id in all_members:
                    await self.config.member_from_ids(ctx.guild.id, member_id).clear()
                await ctx.send("All profiles have been wiped.")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="setbountyemoji")
    @checks.admin_or_permissions(manage_guild=True)
    async def set_bounty_emoji(self, ctx, emoji: str):
        """Set the custom emoji for bounty."""
        try:
            await self.config.guild(ctx.guild).bounty_emoji.set(emoji)
            await ctx.send(f"Bounty emoji set to {emoji}")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="setstaremoji")
    @checks.admin_or_permissions(manage_guild=True)
    async def set_star_emoji(self, ctx, emoji: str):
        """Set the custom emoji for stars."""
        try:
            await self.config.guild(ctx.guild).star_emoji.set(emoji)
            await ctx.send(f"Star emoji set to {emoji}")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="setbountymilestonechannel")
    @checks.admin_or_permissions(manage_guild=True)
    async def set_bounty_milestone_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where bounty milestones will be announced."""
        try:
            await self.config.guild(ctx.guild).bounty_milestone_channel.set(channel.id)
            await ctx.send(f"Bounty milestone channel set to {channel.mention}.")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="mostwanted")
    async def most_wanted(self, ctx, category: str):
        """Display the top users by bounty or stars."""
        try:
            if category.lower() not in ["pirates", "marines"]:
                await ctx.send("Invalid category! Use `pirates` or `marines`.")
                return

            all_members = await self.config.all_members(ctx.guild)
            if category.lower() == "pirates":
                sorted_members = sorted([m for m in all_members.items() if m[1].get("faction") == "Pirate"], key=lambda x: x[1].get("bounty", 0), reverse=True)
                bounty_emoji = await self.config.guild(ctx.guild).bounty_emoji()
                embed = discord.Embed(title="Top Pirates by Bounty", color=discord.Color.gold())
                for idx, (member_id, data) in enumerate(sorted_members[:10], 1):
                    member = ctx.guild.get_member(member_id)
                    if member:
                        embed.add_field(name=f"{idx}. {member.display_name}", value=f"Bounty: {data.get('bounty', 0)} {bounty_emoji}", inline=True)
            else:
                sorted_members = sorted([m for m in all_members.items() if m[1].get("faction") == "Marine"], key=lambda x: x[1].get("stars", 0), reverse=True)
                star_emoji = await self.config.guild(ctx.guild).star_emoji()
                embed = discord.Embed(title="Top Marines by Stars", color=discord.Color.blue())
                for idx, (member_id, data) in enumerate(sorted_members[:10], 1):
                    member = ctx.guild.get_member(member_id)
                    if member:
                        embed.add_field(name=f"{idx}. {member.display_name}", value=f"Stars: {data.get('stars', 0)} {star_emoji}", inline=True)

            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="openbeta")
    @checks.is_owner()
    async def open_beta(self, ctx):
        """Wipe the channel clean and erase all user data for a fresh start."""
        try:
            await ctx.send("The channel will be wiped clean, and all user data will be erased. This will take a few moments...")
            
            # Clear the channel
            await ctx.channel.purge(limit=None)

            # Wipe all user data
            all_members = await self.config.all_members(ctx.guild)
            for member_id in all_members:
                await self.config.member_from_ids(ctx.guild.id, member_id).clear()
            
            await ctx.send("The channel has been wiped clean, and all user data has been erased. Welcome to the open beta!")
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="fix_titles")
    @checks.is_owner()
    async def fix_titles(self, ctx):
        """Fix the titles for all users based on their wins and bounty/stars."""
        try:
            all_members = await self.config.all_members(ctx.guild)
            for member_id, data in all_members.items():
                member = ctx.guild.get_member(member_id)
                if member:
                    await self.fix_title_for_member(ctx, member, data)
            await ctx.send("All titles have been fixed based on current wins and bounty/stars.")
        except Exception as e:
            await self.log_error(ctx, e)

    async def fix_title_for_member(self, ctx, member: discord.Member, data):
        """Fix a user's title based on their wins and bounty/stars."""
        try:
            wins = data.get("wins", 0)
            bounty = data.get("bounty", 0)
            stars = data.get("stars", 0)
            faction = data.get("faction", "")
            current_title = data.get("title", "")
            new_title = None

            if faction == "Pirate":
                if wins == 1 and bounty < 100:
                    new_title = "Apprentice"
                elif wins >= 10 and bounty >= 1000:
                    new_title = "Combatant"
                elif wins >= 20 and bounty >= 2000:
                    new_title = "Officers"
                elif wins >= 30 and bounty >= 3000:
                    new_title = "Chief of Staff"
                elif wins >= 40 and bounty >= 4000:
                    new_title = "First Mate"
                elif wins >= 50 and bounty >= 5000:
                    new_title = "Pirate Captain"
                elif wins > 50 and bounty > 10000 and random.random() < 0.05:
                    new_title = "Super Nova"
                elif wins > 60 and bounty > 20000 and random.random() < 0.05:
                    new_title = "Warlords"
                elif wins > 70 and bounty > 30000 and random.random() < 0.05:
                    new_title = "Worst Generation"
                elif wins > 80 and bounty >= 3000000000 and bounty <= 5000000000 and random.random() < 0.05:
                    new_title = "Emperor"
                elif wins > 90 and bounty >= 5564800000 and random.random() < 0.05:
                    new_title = "Pirate King"
            else:
                if wins == 1 and stars < 10:
                    new_title = "Chore Boy"
                elif wins >= 10 and stars >= 10:
                    new_title = "Seaman Recruit"
                elif wins >= 20 and stars >= 20:
                    new_title = "Seaman Apprentice"
                elif wins >= 30 and stars >= 30:
                    new_title = "Seaman First Class"
                elif wins >= 40 and stars >= 40:
                    new_title = "Petty Officer"
                elif wins >= 50 and stars >= 50:
                    new_title = "Chief Petty Officer"
                elif wins > 50 and stars > 100 and random.random() < 0.05:
                    new_title = "Master Chief Petty Officer"
                elif wins > 60 and stars > 200 and random.random() < 0.05:
                    new_title = "Warrant Officer"
                elif wins > 70 and stars > 300 and random.random() < 0.05:
                    new_title = "Ensign"
                elif wins > 80 and stars > 400 and random.random() < 0.05:
                    new_title = "Lieutenant Junior Grade"
                elif wins > 90 and stars > 500 and random.random() < 0.05:
                    new_title = "Lieutenant"
                elif wins > 100 and stars > 600 and random.random() < 0.05:
                    new_title = "Lieutenant Commander"
                elif wins > 110 and stars > 700 and random.random() < 0.05:
                    new_title = "Commander"
                elif wins > 120 and stars > 800 and random.random() < 0.05:
                    new_title = "Captain"
                elif wins > 130 and stars > 900 and random.random() < 0.05:
                    new_title = "Rear Admiral"
                elif wins > 140 and stars > 1000 and random.random() < 0.05:
                    new_title = "Vice Admiral"
                elif wins > 150 and stars > 1100 and random.random() < 0.05:
                    new_title = "Admiral"
                elif wins > 160 and stars > 1200 and random.random() < 0.05:
                    new_title = "Fleet Admiral"
                elif wins > 170 and stars > 1300 and random.random() < 0.05:
                    new_title = "Commander n Cheif"
                elif wins > 180 and stars > 1400 and random.random() < 0.05:
                    new_title = "Cypher Pol"
                elif wins > 190 and stars > 1500 and random.random() < 0.05:
                    new_title = "Aegis: Cp0"
                elif wins > 200 and stars > 1600 and random.random() < 0.05:
                    new_title = "SWORD"
                elif wins > 210 and stars > 1700 and random.random() < 0.05:
                    new_title = "God Knights"
                elif wins > 220 and stars > 1800 and random.random() < 0.05:
                    new_title = "Kong"
                elif wins > 230 and stars > 1900 and random.random() < 0.005:
                    new_title = "Gorosei"
                elif wins > 240 and stars > 2000 and random.random() < 0.0005:
                    new_title = "Imu"

            if new_title and new_title != current_title:
                await self.config.member(member).title.set(new_title)
                await self.assign_roles(ctx, member)  # Assign new role

        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="opcsettings")
    async def opc_settings(self, ctx):
        """Show the current settings."""
        try:
            guild_settings = await self.config.guild(ctx.guild).all()
            embed = discord.Embed(title="One Piece Cog Settings", color=discord.Color.blue())
            embed.add_field(name="Battle Channel", value=f"<#{guild_settings['battle_channel']}>" if guild_settings['battle_channel'] else "Not set", inline=False)
            embed.add_field(name="Bounty Milestone Channel", value=f"<#{guild_settings['bounty_milestone_channel']}>" if guild_settings['bounty_milestone_channel'] else "Not set", inline=False)
            embed.add_field(name="Bounty Emoji", value=guild_settings['bounty_emoji'], inline=False)
            embed.add_field(name="Star Emoji", value=guild_settings['star_emoji'], inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="opcset")
    @checks.admin_or_permissions(manage_guild=True)
    async def opc_set(self, ctx, target: str, *, value: str):
        """Set various One Piece Cog settings."""
        try:
            if target.lower() == "battlechannel":
                channel = discord.utils.get(ctx.guild.channels, mention=value) or discord.utils.get(ctx.guild.channels, id=int(value.strip('<>#')))
                if channel:
                    await self.config.guild(ctx.guild).battle_channel.set(channel.id)
                    await ctx.send(f"Battle channel set to {channel.mention}.")
                else:
                    await ctx.send("Channel not found.")
            elif target.lower() == "bountymilestonechannel":
                channel = discord.utils.get(ctx.guild.channels, mention=value) or discord.utils.get(ctx.guild.channels, id=int(value.strip('<>#')))
                if channel:
                    await self.config.guild(ctx.guild).bounty_milestone_channel.set(channel.id)
                    await ctx.send(f"Bounty milestone channel set to {channel.mention}.")
                else:
                    await ctx.send("Channel not found.")
            elif target.lower() == "bountyemoji":
                await self.config.guild(ctx.guild).bounty_emoji.set(value)
                await ctx.send(f"Bounty emoji set to {value}")
            elif target.lower() == "staremoji":
                await self.config.guild(ctx.guild).star_emoji.set(value)
                await ctx.send(f"Star emoji set to {value}")
            else:
                await ctx.send("Invalid target. Valid targets are: battlechannel, bountymilestonechannel, bountyemoji, staremoji.")
        except Exception as e:
            await self.log_error(ctx, e)

    def reset_battle(self):
        """Reset the battle state."""
        self.health = {}
        self.attacker = None
        self.defender = None
        self.battle_in_progress = False

    @commands.command(name="battlehelp")
    async def battle_help(self, ctx):
        """Display help for One Piece Cog commands."""
        try:
            embed = discord.Embed(title="One Piece Cog Commands", color=discord.Color.gold())
            embed.add_field(name=".setsail", value="Start a new journey with randomized settings.", inline=False)
            embed.add_field(name=".status [@user]", value="Check your faction and stats.", inline=False)
            embed.add_field(name=".assignroles", value="Assign custom roles based on faction and title to all members with profiles. Admins only.", inline=False)
            embed.add_field(name=".setbattlechannel <channel>", value="Set the channel where battles can take place.", inline=False)
            embed.add_field(name=".joinsea <sea>", value="Join a sea and get ready for battles.", inline=False)
            embed.add_field(name=".battle [@opponent|random]", value="Initiate a turn-based battle.", inline=False)
            embed.add_field(name=".bustercall [member]", value="Reset the title, Devil Fruit, and wins of a member, or all members if no member is specified. Bot owner only.", inline=False)
            embed.add_field(name=".setbountyemoji <emoji>", value="Set the custom emoji for bounty.", inline=False)
            embed.add_field(name=".setstaremoji <emoji>", value="Set the custom emoji for stars.", inline=False)
            embed.add_field(name=".setbountymilestonechannel <channel>", value="Set the channel where bounty milestones will be announced.", inline=False)
            embed.add_field(name=".mostwanted <pirates/marines>", value="Display the top users by bounty (Pirates) or stars (Marines).", inline=False)
            embed.add_field(name=".openbeta", value="Wipe the channel clean and erase all user data for a fresh start. Bot owner only.", inline=False)
            embed.add_field(name=".fix_titles", value="Fix the titles for all users based on their wins and bounty/stars. Bot owner only.", inline=False)
            embed.add_field(name=".opcsettings", value="Show the current One Piece Cog settings.", inline=False)
            embed.add_field(name=".opcset <target name> <output>", value="Set various One Piece Cog settings. Valid targets: battlechannel, bountymilestonechannel, bountyemoji, staremoji.", inline=False)
            embed.add_field(name=".top", value="Show the top users by wins/bounties.", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

    @commands.command(name="top")
    async def top_users(self, ctx, category: str):
        """Display the top users by wins or bounty."""
        try:
            if category.lower() not in ["wins", "bounty"]:
                await ctx.send("Invalid category! Use `wins` or `bounty`.")
                return

            all_members = await self.config.all_members(ctx.guild)
            if category.lower() == "wins":
                sorted_members = sorted(all_members.items(), key=lambda x: x[1].get("wins", 0), reverse=True)
                embed = discord.Embed(title="Top Users by Wins", color=discord.Color.gold())
                for idx, (member_id, data) in enumerate(sorted_members[:10], 1):
                    member = ctx.guild.get_member(member_id)
                    if member:
                        embed.add_field(name=f"{idx}. {member.display_name}", value=f"Wins: {data.get('wins', 0)}", inline=True)
            else:
                sorted_members = sorted(all_members.items(), key=lambda x: x[1].get("bounty", 0), reverse=True)
                bounty_emoji = await self.config.guild(ctx.guild).bounty_emoji()
                embed = discord.Embed(title="Top Users by Bounty", color=discord.Color.gold())
                for idx, (member_id, data) in enumerate(sorted_members[:10], 1):
                    member = ctx.guild.get_member(member_id)
                    if member:
                        embed.add_field(name=f"{idx}. {member.display_name}", value=f"Bounty: {data.get('bounty', 0)} {bounty_emoji}", inline=True)

            await ctx.send(embed=embed)
        except Exception as e:
            await self.log_error(ctx, e)

async def setup(bot: Red):
    await bot.add_cog(OnePieceCog(bot))
