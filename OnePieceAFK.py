import discord # type: ignore
from redbot.core import commands, Config, bank # type: ignore
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS # type: ignore
from redbot.core.utils.chat_formatting import box, pagify # type: ignore
from redbot.core.utils.predicates import MessagePredicate # type: ignore
from discord.ext import tasks # type: ignore
from datetime import datetime, timedelta
import asyncio
import random
from typing import Dict, List, Tuple

class QuestStep:
    def __init__(self, description: str, choices: List[str], outcomes: Dict[str, str]):
        self.description = description
        self.choices = choices
        self.outcomes = outcomes

    async def resolve(self, choice: str) -> str:
        return self.outcomes.get(choice, "Invalid choice. Nothing happens.")

class Quest:
    def __init__(self, name: str, steps: List[QuestStep], rewards: Dict[str, int]):
        self.name = name
        self.steps = steps
        self.rewards = rewards

    async def complete(self, ctx, user_data: Dict[str, any]) -> Dict[str, int]:
        exp_gain = self.rewards.get("exp", 0)
        bounty_gain = self.rewards.get("bounty", 0)
        beli_gain = self.rewards.get("beli", 0)

        user_data["daily_exp"] += exp_gain
        user_data["bounty"] += bounty_gain
        await bank.deposit_credits(ctx.author, beli_gain)

        return {"exp": exp_gain, "bounty": bounty_gain, "beli": beli_gain}

class Island:
    def __init__(self, name: str, quests: List[Quest], difficulty: int):
        self.name = name
        self.quests = quests
        self.difficulty = difficulty

class CombatSystem:
    def __init__(self, player: Dict[str, any], opponent: Dict[str, any]):
        self.player = player
        self.opponent = opponent

    async def calculate_damage(self, attacker: Dict[str, any], attack_type: str) -> int:
        base_damage = random.randint(10, 20)
        if attack_type == "Special Attack":
            base_damage *= 1.5
        elif attack_type == "Haki-infused Attack":
            base_damage *= 2

        return int(base_damage * (1 + attacker["haki_level"] * 0.1))

    async def battle(self, ctx) -> bool:
        await ctx.send(f"Battle started between {self.player['name']} and {self.opponent['name']}!")

        while self.player["hp"] > 0 and self.opponent["hp"] > 0:
            await self.player_turn(ctx)
            if self.opponent["hp"] <= 0:
                break
            await self.opponent_turn(ctx)

        winner = self.player if self.player["hp"] > 0 else self.opponent
        await ctx.send(f"{winner['name']} wins the battle!")
        return winner == self.player

    async def player_turn(self, ctx):
        attacks = ["Normal Attack", "Special Attack", "Haki-infused Attack"]
        attack_msg = await ctx.send(f"Choose your attack: {', '.join(attacks)}")
        
        def check(m):
            return m.author == ctx.author and m.content in attacks

        try:
            choice = await ctx.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Normal Attack chosen by default.")
            choice = discord.Object()
            choice.content = "Normal Attack"

        damage = await self.calculate_damage(self.player, choice.content)
        self.opponent["hp"] -= damage
        await ctx.send(f"You dealt {damage} damage to {self.opponent['name']}!")

    async def opponent_turn(self, ctx):
        attacks = ["Normal Attack", "Special Attack", "Haki-infused Attack"]
        choice = random.choice(attacks)
        damage = await self.calculate_damage(self.opponent, choice)
        self.player["hp"] -= damage
        await ctx.send(f"{self.opponent['name']} used {choice} and dealt {damage} damage to you!")

class SkillTree:
    def __init__(self):
        self.skills = {
            "Swordsman": ["One-Sword Style", "Two-Sword Style", "Three-Sword Style"],
            "Navigator": ["Weather Prediction", "Sea Current Mastery", "Cartography"],
            "Cook": ["Kick Techniques", "Food Buffs", "Flame Techniques"]
        }

    def get_next_skill(self, character_class: str, current_skills: List[str]) -> str:
        class_skills = self.skills.get(character_class, [])
        for skill in class_skills:
            if skill not in current_skills:
                return skill
        return None

class SeasonalEvent:
    def __init__(self, name: str, duration: int, special_quests: List[Quest]):
        self.name = name
        self.duration = duration
        self.special_quests = special_quests
        self.start_time = None

    async def start(self, bot):
        self.start_time = datetime.utcnow()
        await bot.send_to_all_channels(f"The {self.name} event has started! It will last for {self.duration} days.")

    def is_active(self) -> bool:
        if not self.start_time:
            return False
        return (datetime.utcnow() - self.start_time).days < self.duration

class OnePieceAFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_member = {
            "on_adventure": False,
            "log_pose": None,
            "jolly_roger": None,
            "departure_time": None,
            "bounty": 0,
            "crew": None,
            "devil_fruit": None,
            "last_bounty_update": 0,
            "haki_level": 0,
            "last_haki_training": 0,
            "daily_exp": 0,
            "last_exp_reset": 0,
            "character_class": None,
            "skills": [],
            "inventory": {},
            "exploration_count": 0,
            "hp": 100
        }
        default_crew = {
            "members": [],
            "total_bounty": 0,
            "allies": []
        }
        self.config.register_member(**default_member)
        self.config.register_custom("CREW", **default_crew)

        self.islands = self.initialize_islands()
        self.skill_tree = SkillTree()
        self.current_event = None

        self.world_government_intervention.start()
        self.check_seasonal_events.start()

    def initialize_islands(self) -> Dict[str, Island]:
        islands = {
        "dawn": Island("Dawn Island", [
            Quest("Mountain Bandit Trouble", [
                QuestStep("You encounter mountain bandits terrorizing Foosha Village. What do you do?",
                          ["Fight", "Negotiate", "Run"],
                          {"Fight": "You defeat the bandits and save the village!",
                           "Negotiate": "You manage to convince the bandits to leave peacefully.",
                           "Run": "You escape, but the village suffers..."})
            ], {"exp": 100, "bounty": 1000000, "beli": 10000}),
            Quest("Garp's Training", [
                QuestStep("Vice Admiral Garp offers to train you. Do you accept?",
                          ["Accept", "Decline"],
                          {"Accept": "You undergo grueling training but become stronger!",
                           "Decline": "You miss out on valuable training."})
            ], {"exp": 200, "bounty": 2000000, "beli": 20000})
        ], 1),
        "shells": Island("Shells Town", [
            Quest("Marine Base Infiltration", [
                QuestStep("You need to sneak into the Marine base. How do you proceed?",
                          ["Disguise", "Stealth", "Frontal Assault"],
                          {"Disguise": "You successfully infiltrate the base disguised as a Marine.",
                           "Stealth": "You sneak in undetected through a back entrance.",
                           "Frontal Assault": "You're spotted! Prepare for a tough fight!"})
            ], {"exp": 150, "bounty": 1500000, "beli": 15000}),
            Quest("Rescue Zoro", [
                QuestStep("You find Zoro tied up. What's your plan?",
                          ["Cut the ropes", "Steal the key", "Convince him to join your crew"],
                          {"Cut the ropes": "You free Zoro, but attract attention!",
                           "Steal the key": "You successfully free Zoro without being noticed.",
                           "Convince him to join your crew": "Zoro agrees to join if you retrieve his swords!"})
            ], {"exp": 250, "bounty": 2500000, "beli": 25000})
        ], 2),
        "orange": Island("Orange Town", [
            Quest("Buggy's Treasure Hunt", [
                QuestStep("You're searching for Buggy's treasure. Where do you look?",
                          ["Pet Food Shop", "Mayor's House", "Tavern"],
                          {"Pet Food Shop": "You find a small stash of treasure!",
                           "Mayor's House": "You find important town documents, but no treasure.",
                           "Tavern": "You encounter some of Buggy's crew!"})
            ], {"exp": 200, "bounty": 2000000, "beli": 20000})
        ], 2),
        "syrup": Island("Syrup Village", [
            Quest("Protect Kaya", [
                QuestStep("Kuro is after Kaya! How do you protect her?",
                          ["Direct Confrontation", "Set a Trap", "Evacuate Kaya"],
                          {"Direct Confrontation": "You face Kuro head-on in a fierce battle!",
                           "Set a Trap": "Your trap works, catching Kuro off guard!",
                           "Evacuate Kaya": "You safely escort Kaya away, but Kuro is still at large."})
            ], {"exp": 250, "bounty": 2500000, "beli": 25000})
        ], 2),
        "baratie": Island("Baratie", [
            Quest("Cook-off Challenge", [
                QuestStep("Sanji challenges you to a cooking contest. What dish do you prepare?",
                          ["Sea King Steak", "All Blue Soup", "Grand Line Pasta"],
                          {"Sea King Steak": "Your steak impresses the judges!",
                           "All Blue Soup": "Sanji is intrigued by your unique flavors.",
                           "Grand Line Pasta": "The judges find your pasta too exotic."})
            ], {"exp": 300, "bounty": 3000000, "beli": 30000})
        ], 3),
        "arlong": Island("Arlong Park", [
            Quest("Liberate Cocoyasi Village", [
                QuestStep("Arlong has taken over the village. How do you approach the situation?",
                          ["Challenge Arlong Directly", "Destroy the Map Room", "Rally the Villagers"],
                          {"Challenge Arlong Directly": "You engage in an intense battle with Arlong!",
                           "Destroy the Map Room": "You cripple Arlong's operations, weakening his control.",
                           "Rally the Villagers": "The villagers join you in overthrowing Arlong's rule!"})
            ], {"exp": 400, "bounty": 4000000, "beli": 40000})
        ], 4),
        "loguetown": Island("Loguetown", [
            Quest("Race to the Execution Platform", [
                QuestStep("Buggy is about to execute someone on the platform! What's your move?",
                          ["Charge Through the Crowd", "Use a Shortcut", "Create a Diversion"],
                          {"Charge Through the Crowd": "You push through but arrive barely in time!",
                           "Use a Shortcut": "Your shortcut leads you straight to the platform!",
                           "Create a Diversion": "Your diversion works, but now Buggy is after you!"})
            ], {"exp": 350, "bounty": 3500000, "beli": 35000})
        ], 4),
        "whiskey_peak": Island("Whiskey Peak", [
            Quest("Survive the Welcoming Party", [
                QuestStep("The townspeople are suspiciously friendly. What do you do?",
                          ["Enjoy the Party", "Stay Alert", "Fake Drunkenness"],
                          {"Enjoy the Party": "You fall into their trap!",
                           "Stay Alert": "You notice the townspeople are bounty hunters in disguise!",
                           "Fake Drunkenness": "You fool the bounty hunters and catch them off guard!"})
            ], {"exp": 450, "bounty": 4500000, "beli": 45000})
        ], 5),
        "little_garden": Island("Little Garden", [
            Quest("Dinosaur Hunt", [
                QuestStep("You encounter a T-Rex! How do you handle it?",
                          ["Fight", "Tame", "Distract and Run"],
                          {"Fight": "You defeat the T-Rex in an epic battle!",
                           "Tame": "Surprisingly, you manage to befriend the T-Rex!",
                           "Distract and Run": "You narrowly escape, but the T-Rex is still roaming."})
            ], {"exp": 500, "bounty": 5000000, "beli": 50000})
        ], 5),
        "drum": Island("Drum Island", [
            Quest("Climb the Drum Rockies", [
                QuestStep("You need to reach the castle at the top. How do you climb?",
                          ["Bare Hands", "Climbing Gear", "Ride a Lapahn"],
                          {"Bare Hands": "A grueling climb, but you make it!",
                           "Climbing Gear": "You climb efficiently and reach the top quickly.",
                           "Ride a Lapahn": "A wild ride, but you reach the castle in record time!"})
            ], {"exp": 550, "bounty": 5500000, "beli": 55000})
        ], 6),
    }
        return islands

    @commands.command(name="explore_island", aliases=["explore"])
    async def explore_island(self, ctx, island_name: str):
        """
        Explore a specific island in the world of One Piece.

        This command allows you to embark on an adventure to a chosen island.
        You'll encounter various quests and challenges based on the island's theme.

        Parameters:
        island_name (str): The name of the island you want to explore.

        Example:
        !explore_island dawn
        """
        island = self.islands.get(island_name.lower())
        if not island:
            return await ctx.send("Island not found. Available islands: " + ", ".join(self.islands.keys()))
        
        user_data = await self.config.member(ctx.author).all()
        difficulty = await self.get_encounter_difficulty(ctx.author)
        
        if difficulty < island.difficulty:
            return await ctx.send(f"This island is too dangerous for you! Try exploring easier islands first.")

        quest = random.choice(island.quests)
        await ctx.send(f"You've started the quest: {quest.name}")
        
        for step in quest.steps:
            await ctx.send(step.description)
            choice = await self.get_user_choice(ctx, step.choices)
            result = await step.resolve(choice)
            await ctx.send(result)
        
        rewards = await quest.complete(ctx, user_data)
        await self.config.member(ctx.author).set(user_data)
        
        reward_msg = f"Quest completed! You gained:\n"
        reward_msg += f"EXP: {rewards['exp']}\n"
        reward_msg += f"Bounty: {rewards['bounty']} Belly\n"
        reward_msg += f"Beli: {rewards['beli']}"
        await ctx.send(reward_msg)

        user_data["exploration_count"] += 1
        await self.config.member(ctx.author).exploration_count.set(user_data["exploration_count"])

    async def get_user_choice(self, ctx, choices: List[str]) -> str:
        """Helper function to get user choice from a list of options."""
        choice_msg = await ctx.send(f"Choose an option: {', '.join(choices)}")
        
        def check(m):
            return m.author == ctx.author and m.content in choices

        try:
            choice = await self.bot.wait_for("message", check=check, timeout=30.0)
            return choice.content
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Random choice selected.")
            return random.choice(choices)

    @commands.command(name="crew_battle", aliases=["cb"])
    async def crew_battle(self, ctx, opponent_crew: str):
        """
        Initiate a battle between your crew and another crew.

        This command allows you to challenge another crew to a battle.
        The outcome is determined by the total strength of each crew.

        Parameters:
        opponent_crew (str): The name of the crew you want to challenge.

        Example:
        !crew_battle "Straw Hat Pirates"
        """
        player_crew = await self.config.member(ctx.author).crew()
        if not player_crew:
            return await ctx.send("You're not in a crew!")
        
        opponent_crew_data = await self.config.custom("CREW", opponent_crew).all()
        if not opponent_crew_data:
            return await ctx.send("Opponent crew not found.")
        
        player_crew_data = await self.config.custom("CREW", player_crew).all()
        
        player_strength = sum(await self.config.member_from_ids(ctx.guild.id, member_id).bounty() for member_id in player_crew_data["members"])
        opponent_strength = opponent_crew_data["total_bounty"]
        
        battle_result = random.random() < (player_strength / (player_strength + opponent_strength))
        
        if battle_result:
            bounty_gain = int(opponent_strength * 0.1)
            await self.config.custom("CREW", player_crew).total_bounty.set(player_crew_data["total_bounty"] + bounty_gain)
            await ctx.send(f"Your crew emerged victorious! You've gained {bounty_gain} total bounty!")
        else:
            bounty_loss = int(player_strength * 0.05)
            await self.config.custom("CREW", player_crew).total_bounty.set(max(0, player_crew_data["total_bounty"] - bounty_loss))
            await ctx.send(f"Your crew was defeated. You've lost {bounty_loss} total bounty.")

    @commands.command(name="trade")
    async def trade(self, ctx, partner: discord.Member, item: str):
        """
        Trade an item with another user.

        This command allows you to initiate a trade with another user.
        Both users must confirm the trade for it to be completed.

        Parameters:
        partner (discord.Member): The user you want to trade with.
        item (str): The name of the item you want to trade.

        Example:
        !trade @username "Log Pose"
        """
        if partner.bot:
            return await ctx.send("You can't trade with bots!")
        
        user_inventory = await self.config.member(ctx.author).inventory()
        if item not in user_inventory:
            return await ctx.send("You don't have that item!")
        
        await ctx.send(f"{partner.mention}, {ctx.author.mention} wants to trade their {item} with you. Do you accept? (yes/no)")
        
        def check(m):
            return m.author == partner and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Trade offer timed out.")

        if msg.content.lower() == 'yes':
            partner_inventory = await self.config.member(partner).inventory()
            user_inventory.remove(item)
            partner_inventory.append(item)
            await self.config.member(ctx.author).inventory.set(user_inventory)
            await self.config.member(partner).inventory.set(partner_inventory)
            await ctx.send(f"Trade successful! {partner.mention} received {item} from {ctx.author.mention}.")
        else:
            await ctx.send("Trade offer declined.")

    @commands.command(name="learn_skill", aliases=["learn"])
    async def learn_skill(self, ctx):
        """
        Learn a new skill based on your character class.

        This command allows you to learn the next available skill for your character class.
        Skills are learned in a specific order and require previous skills to be mastered.

        Example:
        !learn_skill
        """
        user_class = await self.config.member(ctx.author).character_class()
        if not user_class:
            return await ctx.send("You need to choose a character class first! Use the !choose_class command.")

        user_skills = await self.config.member(ctx.author).skills()
        next_skill = self.skill_tree.get_next_skill(user_class, user_skills)
        
        if not next_skill:
            return await ctx.send("You've learned all available skills for your class!")

        user_skills.append(next_skill)
        await self.config.member(ctx.author).skills.set(user_skills)
        await ctx.send(f"Congratulations! You've learned the {next_skill} skill!")

    @commands.command(name="choose_class", aliases=["class"])
    async def choose_class(self, ctx, class_name: str):
        """
        Choose your character class.

        This command allows you to select your character's class, which determines
        the skills you can learn.

        Parameters:
        class_name (str): The name of the class you want to choose.

        Available classes: Swordsman, Navigator, Cook

        Example:
        !choose_class Swordsman
        """
        if class_name not in self.skill_tree.skills:
            return await ctx.send(f"Invalid class. Choose from: {', '.join(self.skill_tree.skills.keys())}")

        await self.config.member(ctx.author).character_class.set(class_name)
        await ctx.send(f"You are now a {class_name}! You can start learning skills with the !learn_skill command.")

    async def transfer_crew_member(self, from_crew, to_crew, ctx):
        from_crew_data = await self.config.custom("CREW", from_crew).all()
        to_crew_data = await self.config.custom("CREW", to_crew).all()
    
        if len(from_crew_data["members"]) <= 1:
            await ctx.send(f"{from_crew} doesn't have enough members to transfer!")
            return False
    
        transferring_member_id = random.choice(from_crew_data["members"])
        from_crew_data["members"].remove(transferring_member_id)
        to_crew_data["members"].append(transferring_member_id)
    
        await self.config.custom("CREW", from_crew).members.set(from_crew_data["members"])
        await self.config.custom("CREW", to_crew).members.set(to_crew_data["members"])
    
        transferring_member = ctx.guild.get_member(transferring_member_id)
        if transferring_member:
            await self.config.member(transferring_member).crew.set(to_crew)
            await ctx.send(f"{transferring_member.mention} has been transferred from {from_crew} to {to_crew}!")
    
        return True

    @commands.command(name="davy_back_fight", aliases=["davy"])
    async def davy_back_fight(self, ctx, opponent: discord.Member):
        """
        Challenge another user to a Davy Back Fight.

        This command initiates a Davy Back Fight, a series of mini-games
        where the winner can claim a crew member from the loser.

        Parameters:
        opponent (discord.Member): The user you want to challenge.

        Example:
        !davy_back_fight @username
        """
        if opponent.bot:
            return await ctx.send("You can't challenge bots to a Davy Back Fight!")
    
        await ctx.send(f"{opponent.mention}, {ctx.author.mention} challenges you to a Davy Back Fight! Do you accept? (yes/no)")
    
        def check(m):
            return m.author == opponent and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Challenge timed out.")

        if msg.content.lower() == 'no':
            return await ctx.send("Challenge declined.")

        games = ["Donut Race", "Groggy Ring", "Roller Race"]
        scores = {ctx.author.id: 0, opponent.id: 0}

        for game in games:
            await ctx.send(f"Next game: {game}")
            winner = random.choice([ctx.author, opponent])
            scores[winner.id] += 1
            await ctx.send(f"{winner.mention} wins the {game}!")

        overall_winner = ctx.author if scores[ctx.author.id] > scores[opponent.id] else opponent
        loser = opponent if overall_winner == ctx.author else ctx.author

        await ctx.send(f"{overall_winner.mention} wins the Davy Back Fight!")

        winner_crew = await self.config.member(overall_winner).crew()
        loser_crew = await self.config.member(loser).crew()

        if winner_crew and loser_crew and winner_crew != loser_crew:
            if await self.transfer_crew_member(loser_crew, winner_crew, ctx):
                await ctx.send(f"{overall_winner.mention} has claimed a crew member from {loser.mention}!")
            else:
                # If transfer fails (e.g., not enough crew members), just update bounty
                winner_bounty = await self.config.member(overall_winner).bounty()
                new_bounty = winner_bounty + 10000000
                await self.config.member(overall_winner).bounty.set(new_bounty)
                await ctx.send(f"{overall_winner.mention}'s bounty increased by 10,000,000 to {new_bounty:,} Belly!")
        else:
            # If crews are not set up properly, just update bounty
            winner_bounty = await self.config.member(overall_winner).bounty()
            new_bounty = winner_bounty + 10000000
            await self.config.member(overall_winner).bounty.set(new_bounty)
            await ctx.send(f"{overall_winner.mention}'s bounty increased by 10,000,000 to {new_bounty:,} Belly!")

    @commands.command(name="form_alliance", aliases=["alliance"])
    async def form_alliance(self, ctx, ally_crew: str):
        """
        Form an alliance with another crew.

        This command allows you to form an alliance with another crew,
        which can provide benefits in certain situations.

        Parameters:
        ally_crew (str): The name of the crew you want to ally with.

        Example:
        !form_alliance "Heart Pirates"
        """
        user_crew = await self.config.member(ctx.author).crew()
        if not user_crew:
            return await ctx.send("You're not in a crew!")
        
        if user_crew == ally_crew:
            return await ctx.send("You can't form an alliance with your own crew!")

        async with self.config.custom("CREW", user_crew).allies() as allies:
            if ally_crew in allies:
                return await ctx.send("You're already allied with that crew.")
            
            allies.append(ally_crew)
            await ctx.send(f"Alliance formed with {ally_crew}!")

        # Reciprocate the alliance
        async with self.config.custom("CREW", ally_crew).allies() as ally_allies:
            if user_crew not in ally_allies:
                ally_allies.append(user_crew)

    @commands.command(name="leaderboard")
    async def show_leaderboard(self, ctx, category: str = "bounty"):
        """
        Display the leaderboard for a specific category.

        This command shows the top 10 users in the server for the chosen category.

        Parameters:
        category (str): The category to display. 
                        Options: bounty, crew_strength, haki_level, exploration_count
                        Default: bounty

        Example:
        !leaderboard haki_level
        """
        categories = ["bounty", "crew_strength", "haki_level", "exploration_count"]
        if category not in categories:
            return await ctx.send(f"Invalid category. Choose from: {', '.join(categories)}")
        
        all_members = await self.config.all_members(ctx.guild)
        if category == "crew_strength":
            all_crews = await self.config.custom("CREW").all()
            sorted_data = sorted(all_crews.items(), key=lambda x: x[1]['total_bounty'], reverse=True)[:10]
            title = "Top 10 Strongest Crews"
            value_prefix = "Total Bounty: "
        else:
            sorted_data = sorted(all_members.items(), key=lambda x: x[1][category], reverse=True)[:10]
            title = f"Top 10 - {category.replace('_', ' ').title()}"
            value_prefix = ""

        embed = discord.Embed(title=title, color=discord.Color.gold())
        for i, (id, data) in enumerate(sorted_data, 1):
            if category == "crew_strength":
                name = data['name']
                value = data['total_bounty']
            else:
                member = ctx.guild.get_member(id)
                name = member.name if member else f"Unknown User ({id})"
                value = data[category]
            embed.add_field(name=f"{i}. {name}", value=f"{value_prefix}{value:,}", inline=False)
        
        await ctx.send(embed=embed)

    async def get_encounter_difficulty(self, user):
        """Calculate the difficulty of encounters based on user stats."""
        user_data = await self.config.member(user).all()
        base_difficulty = 1.0
        difficulty_modifiers = {
            "bounty": 0.1,
            "haki_level": 0.05,
            "exploration_count": 0.01
        }
        
        for stat, modifier in difficulty_modifiers.items():
            base_difficulty += user_data[stat] * modifier / 1000000  # Adjusted to prevent extreme difficulty

        return min(base_difficulty, 5.0)  # Cap difficulty at 5x

    @commands.command(name="train_haki", aliases=["haki"])
    async def train_haki(self, ctx):
        """
        Train your Haki to increase its level.

        This command allows you to train your Haki, which can improve
        your performance in battles and increase your bounty.

        Training Haki has a cooldown and a chance of success based on your current level.

        Example:
        !train_haki
        """
        user_data = await self.config.member(ctx.author).all()
        current_time = datetime.utcnow().timestamp()
        
        if current_time - user_data['last_haki_training'] < 3600:  # 1 hour cooldown
            remaining_time = 3600 - (current_time - user_data['last_haki_training'])
            return await ctx.send(f"You need to rest before training Haki again. Try in {remaining_time:.0f} seconds.")

        success_chance = 0.5 / (1 + user_data['haki_level'] * 0.1)  # Harder to improve at higher levels
        if random.random() < success_chance:
            user_data['haki_level'] += 1
            bounty_increase = random.randint(1000000, 5000000) * user_data['haki_level']
            user_data['bounty'] += bounty_increase
            await ctx.send(f"Your Haki training was successful! Your Haki is now level {user_data['haki_level']}. "
                           f"Your bounty increased by {bounty_increase:,} to {user_data['bounty']:,} Belly!")
        else:
            await ctx.send("Your Haki training was unsuccessful this time. Keep trying!")

        user_data['last_haki_training'] = current_time
        await self.config.member(ctx.author).set(user_data)

    @commands.command(name="use_devil_fruit", aliases=["eat"])
    async def use_devil_fruit(self, ctx, fruit_name: str):
        """
        Use a Devil Fruit to gain its power.

        This command allows you to consume a Devil Fruit in your inventory,
        granting you its unique ability but preventing you from swimming.

        Parameters:
        fruit_name (str): The name of the Devil Fruit you want to use.

        Example:
        !use_devil_fruit "Gomu Gomu no Mi"
        """
        user_data = await self.config.member(ctx.author).all()
        inventory = user_data['inventory']
        
        if fruit_name not in inventory:
            return await ctx.send(f"You don't have the {fruit_name} in your inventory.")
        
        if user_data['devil_fruit']:
            return await ctx.send("You've already eaten a Devil Fruit! You can't eat another one.")

        inventory.remove(fruit_name)
        user_data['devil_fruit'] = fruit_name
        await self.config.member(ctx.author).set(user_data)

        bounty_increase = random.randint(50000000, 200000000)
        user_data['bounty'] += bounty_increase
        await self.config.member(ctx.author).bounty.set(user_data['bounty'])

        await ctx.send(f"You've eaten the {fruit_name}! You can now use its power, but you can no longer swim. "
                       f"Your bounty has increased by {bounty_increase:,} to {user_data['bounty']:,} Belly!")

    @tasks.loop(hours=6)
    async def world_government_intervention(self):
        """Periodic world events that affect all users."""
        events = [
            ("Buster Call", "A Buster Call has been initiated! All pirates lose 10% of their bounty."),
            ("New Bounty Issuance", "The World Government has issued new bounties! All pirates gain 5-15% bounty increase."),
            ("Marine Headquarters Relocation", "The Marine HQ is on the move! Reduced Marine presence for 24 hours."),
            ("Cipher Pol Operation", "Cipher Pol agents are conducting covert operations. Beware of surprise attacks!"),
            ("Revolutionary Army Activity", "The Revolutionary Army is stirring up trouble. Chance to gain allies or make enemies."),
            ("Celestial Dragon Visit", "A Celestial Dragon is visiting nearby. High risk, high reward opportunities available."),
            ("Sea King Migration", "Sea Kings are migrating through the area. Travel between islands is dangerous!"),
            ("New Weapon Development", "The Marines have developed a new weapon. Increased difficulty in marine encounters."),
            ("Pirate Summit", "A summit of powerful pirates is occurring. Opportunity for alliances and increased bounties.")
        ]
        event, description = random.choice(events)
        
        all_members = await self.config.all_members()
        for guild_id, guild_data in all_members.items():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            for user_id, user_data in guild_data.items():
                if event == "Buster Call":
                    user_data['bounty'] = int(user_data['bounty'] * 0.9)
                elif event == "New Bounty Issuance":
                    increase = random.uniform(1.05, 1.15)
                    user_data['bounty'] = int(user_data['bounty'] * increase)
                # Marine HQ Relocation doesn't directly affect user stats

                await self.config.member_from_ids(guild_id, user_id).set(user_data)

            channel = guild.system_channel or guild.text_channels[0]
            await channel.send(f"World Government Event: {event}\n{description}")

    @tasks.loop(hours=24)
    async def check_seasonal_events(self):
        """Check for and manage seasonal events."""
        if self.current_event and not self.current_event.is_active():
            await self.bot.send_to_all_channels(f"The {self.current_event.name} event has ended!")
            self.current_event = None

        if not self.current_event and random.random() < 0.2:  # 20% chance to start a new event
            event_options = [
                SeasonalEvent("Pirate Festival", 7, [
                    Quest("Festival Games", [
                        QuestStep("Participate in the eating contest!", 
                                  ["Eat Fast", "Eat Slow", "Cheat"],
                                  {"Eat Fast": "You win the contest!", 
                                   "Eat Slow": "You enjoy the food but don't win.", 
                                   "Cheat": "You're caught cheating and disqualified!"})
                    ], {"exp": 1000, "bounty": 5000000, "beli": 100000})
                ]),
                SeasonalEvent("Marine Training Exercise", 5, [
                    Quest("Infiltrate Marine Base", [
                        QuestStep("Sneak past the guards.", 
                                  ["Use Disguise", "Climb Wall", "Create Diversion"],
                                  {"Use Disguise": "You successfully infiltrate the base.", 
                                   "Climb Wall": "You're spotted while climbing!", 
                                   "Create Diversion": "Your diversion works perfectly."})
                    ], {"exp": 2000, "bounty": 10000000, "beli": 200000})
                ])
            ]
            self.current_event = random.choice(event_options)
            await self.current_event.start(self.bot)

    @commands.command(name="inventory")
    async def show_inventory(self, ctx):
        """
        Display your current inventory.

        This command shows all the items you currently possess.

        Example:
        !inventory
        """
        user_data = await self.config.member(ctx.author).all()
        inventory = user_data['inventory']
        
        if not inventory:
            return await ctx.send("Your inventory is empty.")
        
        embed = discord.Embed(title=f"{ctx.author.name}'s Inventory", color=discord.Color.blue())
        for item, count in inventory.items():
            embed.add_field(name=item, value=f"x{count}", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="profile")
    async def show_profile(self, ctx, member: discord.Member = None):
        """
        Display your or another user's profile.

        This command shows detailed information about a user's progress and stats.

        Parameters:
        member (discord.Member): The user whose profile you want to see. If not specified, shows your own profile.

        Example:
        !profile
        !profile @username
        """
        if member is None:
            member = ctx.author
        
        user_data = await self.config.member(member).all()
        
        embed = discord.Embed(title=f"{member.name}'s Pirate Profile", color=member.color)
        embed.set_thumbnail(url=member.avatar_url)
        
        embed.add_field(name="Bounty", value=f"{user_data['bounty']:,} Belly", inline=False)
        embed.add_field(name="Crew", value=user_data['crew'] or "No Crew", inline=True)
        embed.add_field(name="Character Class", value=user_data['character_class'] or "Not Chosen", inline=True)
        embed.add_field(name="Devil Fruit", value=user_data['devil_fruit'] or "None", inline=True)
        embed.add_field(name="Haki Level", value=user_data['haki_level'], inline=True)
        embed.add_field(name="Exploration Count", value=user_data['exploration_count'], inline=True)
        
        skills = ", ".join(user_data['skills']) if user_data['skills'] else "None"
        embed.add_field(name="Skills", value=skills, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="onepieceh")
    async def custom_help(self, ctx):
        """
        Display help information for the One Piece AFK game.

        This command provides an overview of all available commands and game mechanics.

        Example:
        !help_onepiece
        """
        embed = discord.Embed(title="One Piece AFK Game Help", color=discord.Color.blue())
        
        embed.add_field(name="Core Commands", value="""
        `!explore_island <island>` - Explore an island for adventures
        `!crew_battle <opponent_crew>` - Initiate a battle between crews
        `!train_haki` - Train your Haki to increase its level
        `!learn_skill` - Learn a new skill based on your character class
        `!use_devil_fruit <fruit_name>` - Use a Devil Fruit from your inventory
        """, inline=False)
        
        embed.add_field(name="Information Commands", value="""
        `!profile [member]` - View your or another user's profile
        `!inventory` - View your inventory
        `!leaderboard [category]` - View the leaderboard for a specific category
        """, inline=False)
        
        embed.add_field(name="Other Commands", value="""
        `!trade <partner> <item>` - Trade an item with another user
        `!form_alliance <ally_crew>` - Form an alliance with another crew
        `!davy_back_fight <opponent>` - Challenge another user to a Davy Back Fight
        `!choose_class <class_name>` - Choose your character class
        """, inline=False)
        
        embed.add_field(name="Game Mechanics", value="""
        - Explore islands to gain experience, bounty, and items
        - Train your Haki and learn skills to become stronger
        - Form or join a crew to participate in crew battles
        - Find and use Devil Fruits for unique powers
        - Watch out for World Government interventions and seasonal events!
        """, inline=False)
        
        await ctx.send(embed=embed)

    # Error Handling
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided: {error}")
        else:
            await ctx.send(f"An error occurred: {error}")

    # Utility methods
    async def add_item_to_inventory(self, user, item):
        async with self.config.member(user).inventory() as inventory:
            if item in inventory:
                inventory[item] += 1
            else:
                inventory[item] = 1

    async def remove_item_from_inventory(self, user, item):
        async with self.config.member(user).inventory() as inventory:
            if item in inventory:
                inventory[item] -= 1
                if inventory[item] <= 0:
                    del inventory[item]
                return True
            return False

    def cog_unload(self):
        self.world_government_intervention.cancel()
        self.check_seasonal_events.cancel()

def setup(bot):
    bot.add_cog(OnePieceAFK(bot))
