import discord # type: ignore
from redbot.core import commands, Config, checks, bank # type: ignore
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS # type: ignore
from redbot.core.utils.chat_formatting import box, pagify # type: ignore
from redbot.core.utils.predicates import MessagePredicate # type: ignore
from discord.ext import tasks # type: ignore
from datetime import datetime, timedelta
import asyncio
import random
import math
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

        user_data["exp"] += exp_gain
        user_data["bounty"] += bounty_gain
        user_data["berries"] += beli_gain

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

    async def battle(self, ctx) -> bool:
        battle_log = [f"⚔️ {self.player['name']} vs {self.opponent['name']} ⚔️"]

        while self.player['hp'] > 0 and self.opponent['hp'] > 0:
            # Player's turn
            damage = self.calculate_damage(self.player, self.opponent)
            self.opponent['hp'] -= damage
            battle_log.append(f"{self.player['name']} deals {damage} damage to {self.opponent['name']}!")

            if self.opponent['hp'] <= 0:
                break

            # Opponent's turn
            damage = self.calculate_damage(self.opponent, self.player)
            self.player['hp'] -= damage
            battle_log.append(f"{self.opponent['name']} deals {damage} damage to {self.player['name']}!")

        winner = self.player if self.opponent['hp'] <= 0 else self.opponent
        battle_log.append(f"\n🏆 {winner['name']} wins the battle!")

        await ctx.send("\n".join(battle_log))
        return winner == self.player

    def calculate_damage(self, attacker, defender):
        base_damage = attacker['strength'] - defender['defense'] // 2
        crit_chance = attacker['speed'] / (attacker['speed'] + defender['speed'])
        if random.random() < crit_chance:
            base_damage *= 2
        return max(1, int(base_damage))

class SkillTree:
    def __init__(self):
        self.skills = {
            "Swordsman": ["One-Sword Style", "Two-Sword Style", "Three-Sword Style"],
            "Navigator": ["Weather Prediction", "Sea Current Mastery", "Cartography"],
            "Cook": ["Kick Techniques", "Food Buffs", "Flame Techniques"],
            "Doctor": ["First Aid", "Surgical Precision", "Miracle Worker"],
            "Sniper": ["Precise Shot", "Explosive Ammunition", "Observation Haki Boost"]
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

class OnePieceAdventure(commands.Cog):
    """
    One Piece Adventure Cog

    This cog provides an immersive One Piece-themed adventure game for Discord servers.
    Players can explore islands, battle other users, join crews, train their abilities,
    and experience various events from the One Piece world.

    Key Features:
    - Island exploration and quests
    - Character progression with levels, stats, and skills
    - Crew system with crew battles and Davy Back Fights
    - Combat system
    - Devil Fruit powers and Haki abilities
    - Shop system with inventory management
    - Random events during chat
    - Leaderboards and player profiles

    Enjoy your grand adventure in the world of One Piece!
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_global = {
            "crews": {},
            "islands": {},
            "market_items": {}
        }
        default_member = {
            "bounty": 0,
            "crew": None,
            "devil_fruit": None,
            "devil_fruit_awakened": False,
            "haki_level": 0,
            "haki_specialization": None,
            "marine_rank": None,
            "ship": None,
            "fleet": [],
            "inventory": {},
            "legendary_weapon": None,
            "poneglyphs_deciphered": 0,
            "island_base": None,
            "exp": 0,
            "level": 1,
            "strength": 10,
            "defense": 10,
            "speed": 10,
            "hp": 100,
            "max_hp": 100,
            "stamina": 100,
            "max_stamina": 100,
            "berries": 1000,
            "skills": [],
            "character_class": None
        }
        self.config.register_global(**default_global)
        self.config.register_member(**default_member)
        
        self.MARINE_RANKS = [
            "Chore Boy", "Seaman", "Petty Officer", "Lieutenant", "Commander",
            "Captain", "Commodore", "Rear Admiral", "Vice Admiral", "Admiral"
        ]
        
        self.LEGENDARY_WEAPONS = {
            "Yoru": {"type": "sword", "power": 100},
            "Murakumogiri": {"type": "naginata", "power": 95},
            "Kikoku": {"type": "nodachi", "power": 90},
        }
        
        self.DEVIL_FRUITS = [
            "Gomu Gomu no Mi", "Mera Mera no Mi", "Gura Gura no Mi", "Ope Ope no Mi",
            "Yami Yami no Mi", "Hito Hito no Mi", "Moku Moku no Mi", "Suna Suna no Mi"
        ]
        
        self.islands = self.initialize_islands()
        self.skill_tree = SkillTree()
        self.current_event = None

        self.bounty_hunter_check.start()
        self.weather_update.start()
        self.market_update.start()
        self.world_government_intervention.start()
        self.check_seasonal_events.start()

    def cog_unload(self):
        self.bounty_hunter_check.cancel()
        self.weather_update.cancel()
        self.market_update.cancel()
        self.world_government_intervention.cancel()
        self.check_seasonal_events.cancel()

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

    @tasks.loop(minutes=30)
    async def bounty_hunter_check(self):
        for guild in self.bot.guilds:
            channel = guild.get_channel(425068612542398476)  # Replace with your channel ID
            if channel:
                for member in channel.members:
                    if random.random() < 0.1:  # 10% chance
                        await self.bounty_hunter_encounter(member, channel)

    async def bounty_hunter_encounter(self, member, channel):
        user_data = await self.config.member(member).all()
        if user_data['bounty'] < 50000000:  # Only encounter if bounty is over 50 million
            return

        hunter_strength = random.randint(int(user_data['bounty'] * 0.8), int(user_data['bounty'] * 1.2))
        
        await channel.send(f"🏴‍☠️ {member.mention}, a bounty hunter has found you! Their strength is {hunter_strength:,}. Will you fight or run? (fight/run)")
        
        def check(m):
            return m.author == member and m.channel == channel and m.content.lower() in ['fight', 'run']
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await channel.send(f"{member.mention} hesitated and the bounty hunter got away!")
        
        if msg.content.lower() == 'fight':
            if user_data['strength'] * 10000 + user_data['bounty'] > hunter_strength:
                reward = random.randint(1000000, 10000000)
                user_data['bounty'] += reward
                await self.config.member(member).set(user_data)
                await channel.send(f"💥 {member.mention} defeated the bounty hunter! Their bounty increased by {reward:,} to {user_data['bounty']:,}!")
            else:
                loss = random.randint(10000000, 50000000)
                user_data['bounty'] = max(0, user_data['bounty'] - loss)
                await self.config.member(member).set(user_data)
                await channel.send(f"💔 {member.mention} was defeated by the bounty hunter! Their bounty decreased by {loss:,} to {user_data['bounty']:,}.")
        else:
            escape_chance = random.random()
            if escape_chance > 0.5:
                await channel.send(f"🏃‍♂️ {member.mention} managed to escape the bounty hunter!")
            else:
                loss = random.randint(5000000, 20000000)
                user_data['bounty'] = max(0, user_data['bounty'] - loss)
                await self.config.member(member).set(user_data)
                await channel.send(f"🚓 {member.mention} couldn't escape! The bounty hunter caught them. Their bounty decreased by {loss:,} to {user_data['bounty']:,}.")

    @tasks.loop(hours=1)
    async def weather_update(self):
        weathers = [
            ("Clear skies", "Perfect weather for sailing!"),
            ("Storm", "The seas are rough, be careful!"),
            ("Fog", "Visibility is low, watch out for obstacles."),
            ("Knock-Up Stream", "A powerful upward current appears!"),
            ("Calm Belt", "No wind at all, beware of Sea Kings!")
        ]
        weather, description = random.choice(weathers)
        for guild in self.bot.guilds:
            channel = guild.get_channel(425068612542398476)  # Replace with your channel ID
            if channel:
                await channel.send(f"🌤️ Weather Update: {weather}\n{description}")

    @tasks.loop(hours=12)
    async def market_update(self):
        items = [
            {"name": "Log Pose", "price": random.randint(1000000, 5000000)},
            {"name": "Eternal Pose", "price": random.randint(5000000, 20000000)},
            {"name": "Vivre Card", "price": random.randint(10000000, 50000000)},
            {"name": "Poneglyph Rubbing", "price": random.randint(50000000, 200000000)},
            {"name": "Sea Prism Stone", "price": random.randint(30000000, 100000000)},
        ]
        await self.config.market_items.set(random.sample(items, 3))

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
            await channel.send(f"🌐 World Government Event: {event}\n{description}")

    @tasks.loop(hours=24)
    async def check_seasonal_events(self):
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

    @commands.command()
    async def explore(self, ctx, island_name: str):
        """🏝️ Explore a specific island in the One Piece world."""
        island = self.islands.get(island_name.lower())
        if not island:
            return await ctx.send("🌊 Island not found. Available islands: " + ", ".join(self.islands.keys()))
        
        user_data = await self.config.member(ctx.author).all()
        difficulty = await self.get_encounter_difficulty(ctx.author)
        
        if difficulty < island.difficulty:
            return await ctx.send(f"⚠️ This island is too dangerous for you! Try exploring easier islands first.")

        quest = random.choice(island.quests)
        await ctx.send(f"🗺️ You've started the quest: {quest.name}")
        
        for step in quest.steps:
            await ctx.send(step.description)
            choice = await self.get_user_choice(ctx, step.choices)
            result = await step.resolve(choice)
            await ctx.send(result)
        
        rewards = await quest.complete(ctx, user_data)
        await self.config.member(ctx.author).set(user_data)
        
        reward_msg = f"🎉 Quest completed! You gained:\n"
        reward_msg += f"✨ EXP: {rewards['exp']}\n"
        reward_msg += f"💰 Bounty: {rewards['bounty']} Belly\n"
        reward_msg += f"💵 Beli: {rewards['beli']}"
        await ctx.send(reward_msg)

    async def get_user_choice(self, ctx, choices: List[str]) -> str:
        """Helper function to get user choice from a list of options."""
        choice_msg = await ctx.send(f"Choose an option: {', '.join(choices)}")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in choices

        try:
            choice = await self.bot.wait_for("message", check=check, timeout=30.0)
            return choice.content
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Random choice selected.")
            return random.choice(choices)

    @commands.command()
    async def train(self, ctx, attribute: str):
        """💪 Train a specific attribute (strength, defense, speed)."""
        valid_attributes = ['strength', 'defense', 'speed']
        if attribute.lower() not in valid_attributes:
            return await ctx.send(f"❌ Invalid attribute. Choose from: {', '.join(valid_attributes)}")

        user_data = await self.config.member(ctx.author).all()
        stamina_cost = 20
        if user_data['stamina'] < stamina_cost:
            return await ctx.send("😴 You don't have enough stamina to train. Rest to recover stamina.")

        increase = random.randint(1, 3)
        user_data[attribute.lower()] += increase
        user_data['stamina'] -= stamina_cost
        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"🏋️ You trained your {attribute}. It increased by {increase} points!")

    @commands.command()
    async def rest(self, ctx):
        """😴 Rest to recover HP and stamina."""
        user_data = await self.config.member(ctx.author).all()
        recovery = random.randint(20, 50)
        user_data['hp'] = min(user_data['max_hp'], user_data['hp'] + recovery)
        user_data['stamina'] = min(user_data['max_stamina'], user_data['stamina'] + recovery)
        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"💤 You rested and recovered {recovery} HP and stamina!")

    @commands.command()
    async def battle(self, ctx, opponent: discord.Member):
        """⚔️ Engage in a battle with another user."""
        if opponent == ctx.author:
            return await ctx.send("❌ You can't battle yourself!")

        player = await self.config.member(ctx.author).all()
        enemy = await self.config.member(opponent).all()

        combat = CombatSystem(player, enemy)
        result = await combat.battle(ctx)

        if result:
            bounty_transfer = int(enemy['bounty'] * 0.1)
            player['bounty'] += bounty_transfer
            enemy['bounty'] = max(0, enemy['bounty'] - bounty_transfer)
            await ctx.send(f"🏆 {ctx.author.mention} wins and gains {bounty_transfer} bounty from {opponent.mention}!")
        else:
            bounty_transfer = int(player['bounty'] * 0.1)
            enemy['bounty'] += bounty_transfer
            player['bounty'] = max(0, player['bounty'] - bounty_transfer)
            await ctx.send(f"🏆 {opponent.mention} wins and gains {bounty_transfer} bounty from {ctx.author.mention}!")

        await self.config.member(ctx.author).set(player)
        await self.config.member(opponent).set(enemy)

    @commands.command()
    async def createcrew(self, ctx, *, name: str):
        """🏴‍☠️ Create a new pirate crew."""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Only administrators can create crews.")
        
        crews = await self.config.crews()
        if len(crews) >= 4:
            return await ctx.send("❌ Maximum number of crews (4) reached.")
        if name in crews:
            return await ctx.send("❌ A crew with that name already exists.")
        
        crews[name] = {"members": []}
        await self.config.crews.set(crews)
        await ctx.send(f"🏴‍☠️ Crew '{name}' created!")

    @commands.command()
    async def joincrew(self, ctx, *, name: str):
        """🚢 Join a pirate crew."""
        crews = await self.config.crews()
        if name not in crews:
            return await ctx.send("❌ That crew doesn't exist.")
        if await self.config.member(ctx.author).crew():
            return await ctx.send("❌ You're already in a crew and can't leave.")
        
        crews[name]["members"].append(ctx.author.id)
        await self.config.crews.set(crews)
        await self.config.member(ctx.author).crew.set(name)
        await ctx.send(f"🎉 You've joined the {name} crew!")

    @commands.command()
    async def crew(self, ctx, *, name: str = None):
        """ℹ️ Display information about a crew."""
        if name is None:
            name = await self.config.member(ctx.author).crew()
            if name is None:
                return await ctx.send("You're not in a crew. Specify a crew name to get info.")
        
        crews = await self.config.crews()
        if name not in crews:
            return await ctx.send("That crew doesn't exist.")
        
        members = [ctx.guild.get_member(member_id) for member_id in crews[name]["members"] if ctx.guild.get_member(member_id)]
        total_bounty = sum(await self.config.member(member).bounty() for member in members)
        
        embed = discord.Embed(title=f"🏴‍☠️ Crew: {name}", color=discord.Color.gold())
        embed.add_field(name="Members", value="\n".join(member.display_name for member in members) or "No members")
        embed.add_field(name="Total Bounty", value=f"💰 {total_bounty:,} Belly")
        await ctx.send(embed=embed)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        """👤 Display your or another user's profile."""
        if member is None:
            member = ctx.author

        user_data = await self.config.member(member).all()
        embed = discord.Embed(title=f"{member.name}'s Profile", color=discord.Color.blue())
        embed.set_thumbnail(url=member.avatar.url)

        embed.add_field(name="💰 Bounty", value=f"{user_data['bounty']:,} Belly", inline=True)
        embed.add_field(name="💵 Berries", value=f"{user_data['berries']:,}", inline=True)
        embed.add_field(name="🏴‍☠️ Crew", value=user_data['crew'] or "None", inline=True)
        embed.add_field(name="🍎 Devil Fruit", value=user_data['devil_fruit'] or "None", inline=True)
        embed.add_field(name="✨ Haki Level", value=user_data['haki_level'], inline=True)
        embed.add_field(name="📜 Poneglyphs Deciphered", value=user_data['poneglyphs_deciphered'], inline=True)

        stats = f"💪 Strength: {user_data['strength']}\n"
        stats += f"🛡️ Defense: {user_data['defense']}\n"
        stats += f"⚡ Speed: {user_data['speed']}\n"
        stats += f"❤️ HP: {user_data['hp']}/{user_data['max_hp']}\n"
        stats += f"⚡ Stamina: {user_data['stamina']}/{user_data['max_stamina']}"
        embed.add_field(name="Stats", value=stats, inline=False)

        if user_data['character_class']:
            embed.add_field(name="🏅 Class", value=user_data['character_class'], inline=True)
            embed.add_field(name="🎭 Skills", value=", ".join(user_data['skills']) or "None", inline=True)

        await ctx.send(embed=embed)

    @commands.command()
    async def top(self, ctx, category: str = "bounty"):
        """🏆 View the leaderboard for a specific category."""
        categories = ["bounty", "haki", "poneglyphs", "strength", "defense", "speed"]
        if category not in categories:
            return await ctx.send(f"❌ Invalid category. Choose from: {', '.join(categories)}")
        
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(all_members.items(), key=lambda x: x[1][category], reverse=True)[:10]
        
        embed = discord.Embed(title=f"🏆 Top 10 - {category.capitalize()}", color=discord.Color.gold())
        for i, (member_id, data) in enumerate(sorted_members, 1):
            member = ctx.guild.get_member(member_id)
            if member:
                embed.add_field(name=f"{i}. {member.display_name}", value=f"{data[category]:,}", inline=False)
        
        await ctx.send(embed=embed)

    async def add_exp(self, user_id, exp_amount):
        user_data = await self.config.member_from_ids(None, user_id).all()
        user_data['exp'] += exp_amount
        
        # Check for level up
        new_level = int(math.sqrt(user_data['exp'] / 100))
        if new_level > user_data['level']:
            user_data['level'] = new_level
            user_data['max_hp'] += 10
            user_data['max_stamina'] += 5
            await self.config.member_from_ids(None, user_id).set(user_data)
            return exp_amount, True
        
        await self.config.member_from_ids(None, user_id).set(user_data)
        return exp_amount, False

    @commands.command()
    async def level(self, ctx, member: discord.Member = None):
        """📊 Display your or another user's level and experience."""
        if member is None:
            member = ctx.author

        user_data = await self.config.member(member).all()
        embed = discord.Embed(title=f"📊 {member.name}'s Level", color=discord.Color.green())
        embed.add_field(name="🏅 Level", value=user_data['level'], inline=True)
        embed.add_field(name="✨ Experience", value=f"{user_data['exp']:,}", inline=True)
        embed.add_field(name="🎯 Next Level", value=f"{(user_data['level'] + 1) ** 2 * 100:,}", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def inventory(self, ctx):
        """🎒 Display your inventory."""
        user_data = await self.config.member(ctx.author).all()
        inventory = user_data['inventory']
        
        if not inventory:
            return await ctx.send("🎒 Your inventory is empty!")
        
        embed = discord.Embed(title=f"🎒 {ctx.author.name}'s Inventory", color=discord.Color.blue())
        for item, count in inventory.items():
            embed.add_field(name=item, value=f"x{count}", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def shop(self, ctx):
        """🛒 Display the shop items."""
        shop_items = [
            {"name": "Small Health Potion", "price": 1000, "effect": "Restore 20 HP", "emoji": "🧪"},
            {"name": "Medium Health Potion", "price": 2500, "effect": "Restore 50 HP", "emoji": "🧪"},
            {"name": "Large Health Potion", "price": 5000, "effect": "Restore 100 HP", "emoji": "🧪"},
            {"name": "Small Stamina Potion", "price": 1000, "effect": "Restore 20 Stamina", "emoji": "⚡"},
            {"name": "Medium Stamina Potion", "price": 2500, "effect": "Restore 50 Stamina", "emoji": "⚡"},
            {"name": "Large Stamina Potion", "price": 5000, "effect": "Restore 100 Stamina", "emoji": "⚡"},
        ]
        
        embed = discord.Embed(title="🛒 Shop", description="Available items for purchase:", color=discord.Color.gold())
        for item in shop_items:
            embed.add_field(name=f"{item['emoji']} {item['name']}", value=f"Price: {item['price']} Berries\nEffect: {item['effect']}", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def buy(self, ctx, *, item_name: str):
        """💰 Buy an item from the shop."""
        shop_items = {
            "Small Health Potion": {"price": 1000, "effect": 20, "type": "hp", "emoji": "🧪"},
            "Medium Health Potion": {"price": 2500, "effect": 50, "type": "hp", "emoji": "🧪"},
            "Large Health Potion": {"price": 5000, "effect": 100, "type": "hp", "emoji": "🧪"},
            "Small Stamina Potion": {"price": 1000, "effect": 20, "type": "stamina", "emoji": "⚡"},
            "Medium Stamina Potion": {"price": 2500, "effect": 50, "type": "stamina", "emoji": "⚡"},
            "Large Stamina Potion": {"price": 5000, "effect": 100, "type": "stamina", "emoji": "⚡"},
        }
        
        if item_name not in shop_items:
            return await ctx.send("❌ That item is not available in the shop.")
        
        item = shop_items[item_name]
        user_data = await self.config.member(ctx.author).all()
        
        if user_data['berries'] < item['price']:
            return await ctx.send("❌ You don't have enough Berries to buy this item!")
        
        user_data['berries'] -= item['price']
        user_data['inventory'][item_name] = user_data['inventory'].get(item_name, 0) + 1
        await self.config.member(ctx.author).set(user_data)
        
        await ctx.send(f"✅ You've bought {item['emoji']} {item_name} for {item['price']} Berries!")

    @commands.command()
    async def use(self, ctx, *, item_name: str):
        """🔧 Use an item from your inventory."""
        user_data = await self.config.member(ctx.author).all()
        
        if item_name not in user_data['inventory'] or user_data['inventory'][item_name] == 0:
            return await ctx.send("❌ You don't have that item in your inventory!")
        
        shop_items = {
            "Small Health Potion": {"effect": 20, "type": "hp", "emoji": "🧪"},
            "Medium Health Potion": {"effect": 50, "type": "hp", "emoji": "🧪"},
            "Large Health Potion": {"effect": 100, "type": "hp", "emoji": "🧪"},
            "Small Stamina Potion": {"effect": 20, "type": "stamina", "emoji": "⚡"},
            "Medium Stamina Potion": {"effect": 50, "type": "stamina", "emoji": "⚡"},
            "Large Stamina Potion": {"effect": 100, "type": "stamina", "emoji": "⚡"},
        }
        
        if item_name not in shop_items:
            return await ctx.send("❌ That item cannot be used.")
        
        item = shop_items[item_name]
        if item['type'] == 'hp':
            user_data['hp'] = min(user_data['max_hp'], user_data['hp'] + item['effect'])
            await ctx.send(f"✅ You used {item['emoji']} {item_name} and restored {item['effect']} HP!")
        elif item['type'] == 'stamina':
            user_data['stamina'] = min(user_data['max_stamina'], user_data['stamina'] + item['effect'])
            await ctx.send(f"✅ You used {item['emoji']} {item_name} and restored {item['effect']} Stamina!")
        
        user_data['inventory'][item_name] -= 1
        if user_data['inventory'][item_name] == 0:
            del user_data['inventory'][item_name]
        
        await self.config.member(ctx.author).set(user_data)

    @commands.command()
    async def pick(self, ctx, class_name: str):
        """
        🏅 Choose your character class.

        This command allows you to select your character's class, which determines
        the skills you can learn.

        Parameters:
        class_name (str): The name of the class you want to choose.

        Available classes: Swordsman, Navigator, Cook, Doctor, Sniper

        Example:
        .pick Swordsman
        """
        if class_name not in self.skill_tree.skills:
            return await ctx.send(f"❌ Invalid class. Choose from: {', '.join(self.skill_tree.skills.keys())}")

        await self.config.member(ctx.author).character_class.set(class_name)
        await ctx.send(f"🎉 You are now a {class_name}! You can start learning skills with the .learn_skill command.")

    @commands.command()
    async def learn(self, ctx):
        """
        📚 Learn a new skill based on your character class.

        This command allows you to learn the next available skill for your character class.
        Skills are learned in a specific order and require previous skills to be mastered.

        Example:
        .learn
        """
        user_data = await self.config.member(ctx.author).all()
        if not user_data['character_class']:
            return await ctx.send("❌ You need to choose a character class first! Use the .choose_class command.")

        next_skill = self.skill_tree.get_next_skill(user_data['character_class'], user_data['skills'])
        
        if not next_skill:
            return await ctx.send("✨ You've learned all available skills for your class!")

        user_data['skills'].append(next_skill)
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"🎉 Congratulations! You've learned the {next_skill} skill!")

    @commands.command()
    async def skill(self, ctx, *, skill_name: str):
        """
        🔧 Use one of your learned skills.

        This command allows you to use a skill you've learned, which can have various effects
        depending on the skill and your class.

        Parameters:
        skill_name (str): The name of the skill you want to use.

        Example:
        .skill "One-Sword Style"
        """
        user_data = await self.config.member(ctx.author).all()
        if skill_name not in user_data['skills']:
            return await ctx.send("❌ You haven't learned that skill yet!")

        # Implement skill effects here. For now, we'll just acknowledge the skill use.
        await ctx.send(f"💥 You used {skill_name}! (Skill effects not yet implemented)")

    @commands.command()
    async def ophelp(self, ctx):
        """📚 Display help for One Piece Adventure commands."""
        embed = discord.Embed(title="📚 One Piece Adventure Help", description="Available commands:", color=discord.Color.blue())
        
        commands = {
            "explore": "🏝️ Explore a specific island for adventures",
            "train": "💪 Train a specific attribute (strength, defense, speed)",
            "rest": "😴 Rest to recover HP and stamina",
            "battle": "⚔️ Engage in a battle with another user",
            "createcrew": "🏴‍☠️ Create a new pirate crew (admin only)",
            "joincrew": "🚢 Join an existing pirate crew",
            "crew": "ℹ️ Display information about a crew",
            "profile": "👤 Display your or another user's profile",
            "top": "🏆 View the leaderboard for a specific category",
            "pick": "🏅 Choose your character class",
            "learn": "📚 Learn a new skill based on your character class",
            "skill": "🔧 Use one of your learned skills",
            "level": "📊 Display your or another user's level and experience",
            "inventory": "🎒 Display your inventory",
            "shop": "🛒 Display the shop items",
            "buy": "💰 Buy an item from the shop",
            "use": "🔧 Use an item from your inventory"
        }
        
        for command, description in commands.items():
            embed.add_field(name=f".{command}", value=description, inline=False)
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id in self.active_channels:
            exp_gain = random.randint(10, 100)
            exp_gained, leveled_up = await self.add_exp(message.author.id, exp_gain)
            if exp_gained > 0 and random.random() < 0.1:  # 10% chance to show exp gain message
                await message.channel.send(f"✨ {message.author.mention} gained {exp_gained} exp from activity!")
            if leveled_up:
                await message.channel.send(f"🎉 Congratulations {message.author.mention}! You've leveled up!")

            # Random events
            if random.random() < 0.05:  # 5% chance for a random event
                event = random.choice([
                    self.random_treasure_event,
                    self.random_sea_king_encounter,
                    self.random_marine_encounter,
                    self.random_pirate_encounter
                ])
                await event(message)

    async def random_treasure_event(self, message):
        treasure_value = random.randint(1000, 10000)
        await message.channel.send(f"💎 {message.author.mention} stumbled upon a hidden treasure worth {treasure_value} Berries!")
        user_data = await self.config.member(message.author).all()
        user_data['berries'] += treasure_value
        await self.config.member(message.author).set(user_data)

    async def random_sea_king_encounter(self, message):
        await message.channel.send(f"🌊 A Sea King suddenly appears near {message.author.mention}'s ship! What will you do? (fight/flee/negotiate)")

        def check(m):
            return m.author == message.author and m.channel == message.channel and m.content.lower() in ['fight', 'flee', 'negotiate']

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            if response.content.lower() == 'fight':
                if random.random() < 0.5:
                    await message.channel.send(f"💥 You successfully defeated the Sea King! Your bounty increases!")
                    user_data = await self.config.member(message.author).all()
                    user_data['bounty'] += 5000000
                    await self.config.member(message.author).set(user_data)
                else:
                    await message.channel.send("💔 The Sea King was too strong! You barely escaped with your life.")
            elif response.content.lower() == 'flee':
                await message.channel.send("🏃‍♂️ You managed to escape from the Sea King, but gained nothing.")
            else:
                await message.channel.send("🗣️ Surprisingly, you managed to negotiate with the Sea King! It swims away peacefully.")
        except asyncio.TimeoutError:
            await message.channel.send("⏳ You hesitated and the Sea King swam away.")

    async def random_marine_encounter(self, message):
        marine_ranks = ["Ensign", "Lieutenant", "Captain", "Commodore", "Vice Admiral"]
        rank = random.choice(marine_ranks)
        await message.channel.send(f"⚓ A Marine {rank} spots {message.author.mention}! What's your move? (fight/bribe/disguise)")

        def check(m):
            return m.author == message.author and m.channel == message.channel and m.content.lower() in ['fight', 'bribe', 'disguise']

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            if response.content.lower() == 'fight':
                if random.random() < 0.4:
                    bounty_increase = random.randint(1000000, 10000000)
                    await message.channel.send(f"💥 You defeated the Marine {rank}! Your bounty increases by {bounty_increase:,} Belly!")
                    user_data = await self.config.member(message.author).all()
                    user_data['bounty'] += bounty_increase
                    await self.config.member(message.author).set(user_data)
                else:
                    await message.channel.send(f"💔 The Marine {rank} was too strong! You managed to escape, but it was close.")
            elif response.content.lower() == 'bribe':
                bribe_amount = random.randint(100000, 1000000)
                await message.channel.send(f"💰 You bribed the Marine {rank} with {bribe_amount:,} Belly. They look the other way, for now.")
                user_data = await self.config.member(message.author).all()
                user_data['berries'] = max(0, user_data['berries'] - bribe_amount)
                await self.config.member(message.author).set(user_data)
            else:
                if random.random() < 0.6:
                    await message.channel.send(f"🕵️ Your disguise fooled the Marine {rank}! You slip away unnoticed.")
                else:
                    await message.channel.send(f"😅 Your disguise didn't fool the Marine {rank}! You had to make a quick escape!")
        except asyncio.TimeoutError:
            await message.channel.send("⏳ You hesitated and the Marine grew suspicious. You quickly leave the area.")

    async def random_pirate_encounter(self, message):
        rival_crew_names = ["Blackbeard Pirates", "Big Mom Pirates", "Beast Pirates", "Red Hair Pirates"]
        rival_crew = random.choice(rival_crew_names)
        await message.channel.send(f"🏴‍☠️ {message.author.mention} encounters the {rival_crew}! What will you do? (alliance/battle/avoid)")

        def check(m):
            return m.author == message.author and m.channel == message.channel and m.content.lower() in ['alliance', 'battle', 'avoid']

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            if response.content.lower() == 'alliance':
                if random.random() < 0.3:
                    await message.channel.send(f"🤝 Incredibly, the {rival_crew} agree to a temporary alliance! Your influence grows.")
                    user_data = await self.config.member(message.author).all()
                    user_data['bounty'] += 20000000
                    await self.config.member(message.author).set(user_data)
                else:
                    await message.channel.send(f"😅 The {rival_crew} laugh at your offer of alliance. You quickly leave before things escalate.")
            elif response.content.lower() == 'battle':
                if random.random() < 0.2:
                    bounty_increase = random.randint(10000000, 50000000)
                    await message.channel.send(f"💥 Against all odds, you emerged victorious against the {rival_crew}! Your bounty skyrockets by {bounty_increase:,} Belly!")
                    user_data = await self.config.member(message.author).all()
                    user_data['bounty'] += bounty_increase
                    await self.config.member(message.author).set(user_data)
                else:
                    await message.channel.send(f"💔 The {rival_crew} were too powerful! You're lucky to escape with your life.")
            else:
                if random.random() < 0.7:
                    await message.channel.send(f"🏃‍♂️ You successfully avoided a confrontation with the {rival_crew}. Wise choice!")
                else:
                    await message.channel.send(f"😰 Despite your attempts to avoid them, the {rival_crew} spotted you! You narrowly escape.")
        except asyncio.TimeoutError:
            await message.channel.send(f"⏳ While you hesitated, the {rival_crew} lost interest and sailed away.")

    @commands.command()
    async def fishing(self, ctx):
        """🎣 Go fishing for resources and treasures."""
        user_data = await self.config.member(ctx.author).all()
        stamina_cost = 15
        if user_data['stamina'] < stamina_cost:
            return await ctx.send("😴 You don't have enough stamina to go fishing. Rest to recover stamina.")

        user_data['stamina'] -= stamina_cost
        await self.config.member(ctx.author).set(user_data)

        catch = random.choices(['fish', 'treasure', 'junk', 'nothing'], weights=[0.6, 0.1, 0.2, 0.1])[0]

        if catch == 'fish':
            fish_value = random.randint(100, 1000)
            user_data['berries'] += fish_value
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"🐟 You caught a fish worth {fish_value} Berries!")
        elif catch == 'treasure':
            treasure_value = random.randint(1000, 10000)
            user_data['berries'] += treasure_value
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"💎 You found a treasure chest worth {treasure_value} Berries!")
        elif catch == 'junk':
            await ctx.send("🗑️ You fished out some junk. Better luck next time!")
        else:
            await ctx.send("😕 You didn't catch anything this time.")

    @commands.command()
    async def craft(self, ctx, *, item_name: str):
        """🔨 Craft an item using resources."""
        recipes = {
            "Log Pose": {"wood": 5, "metal": 3},
            "Basic Sword": {"wood": 2, "metal": 5},
            "Fishing Rod": {"wood": 4, "string": 2},
        }

        if item_name not in recipes:
            return await ctx.send(f"❌ That item cannot be crafted. Available recipes: {', '.join(recipes.keys())}")

        user_data = await self.config.member(ctx.author).all()
        recipe = recipes[item_name]

        for material, amount in recipe.items():
            if user_data['inventory'].get(material, 0) < amount:
                return await ctx.send(f"❌ You don't have enough {material} to craft {item_name}.")

        for material, amount in recipe.items():
            user_data['inventory'][material] -= amount

        user_data['inventory'][item_name] = user_data['inventory'].get(item_name, 0) + 1
        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"🔨 You successfully crafted {item_name}!")

    @commands.command()
    async def daily(self, ctx):
        """📅 Claim your daily reward."""
        user_data = await self.config.member(ctx.author).all()
        current_time = datetime.utcnow().timestamp()

        if 'last_daily' not in user_data or current_time - user_data['last_daily'] >= 86400:  # 24 hours in seconds
            reward = random.randint(1000, 5000)
            user_data['berries'] += reward
            user_data['last_daily'] = current_time
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"📅 You've claimed your daily reward of {reward} Berries!")
        else:
            time_left = 86400 - (current_time - user_data['last_daily'])
            hours, remainder = divmod(int(time_left), 3600)
            minutes, _ = divmod(remainder, 60)
            await ctx.send(f"⏳ You've already claimed your daily reward. You can claim again in {hours} hours and {minutes} minutes.")

    @commands.command()
    async def upgrade_base(self, ctx):
        """🏰 Upgrade your island base."""
        user_data = await self.config.member(ctx.author).all()
        if not user_data['island_base']:
            return await ctx.send("❌ You need to establish a base first! Use the .explore_island command to find a suitable location.")

        current_level = user_data.get('base_level', 1)
        upgrade_cost = current_level * 100000

        if user_data['berries'] < upgrade_cost:
            return await ctx.send(f"❌ You need {upgrade_cost} Berries to upgrade your base to level {current_level + 1}.")

        user_data['berries'] -= upgrade_cost
        user_data['base_level'] = current_level + 1
        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"🏰 You've upgraded your base on {user_data['island_base']} to level {current_level + 1}!")

    @commands.command()
    async def trade(self, ctx, partner: discord.Member, item: str, quantity: int):
        """💱 Trade items with another player."""
        if partner.bot:
            return await ctx.send("❌ You can't trade with bots!")

        user_data = await self.config.member(ctx.author).all()
        partner_data = await self.config.member(partner).all()

        if item not in user_data['inventory'] or user_data['inventory'][item] < quantity:
            return await ctx.send("❌ You don't have enough of that item to trade!")

        await ctx.send(f"{partner.mention}, do you accept this trade of {quantity} {item}? (yes/no)")

        def check(m):
            return m.author == partner and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("⏳ Trade offer timed out.")

        if response.content.lower() == 'yes':
            user_data['inventory'][item] -= quantity
            partner_data['inventory'][item] = partner_data['inventory'].get(item, 0) + quantity

            if user_data['inventory'][item] == 0:
                del user_data['inventory'][item]

            await self.config.member(ctx.author).set(user_data)
            await self.config.member(partner).set(partner_data)

            await ctx.send(f"🤝 Trade successful! {ctx.author.mention} gave {quantity} {item} to {partner.mention}.")
        else:
            await ctx.send("❌ Trade declined.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.HTTPException):
                await ctx.send(f"There was an error communicating with Discord. Please try again later.")
            else:
                await ctx.send(f"An unexpected error occurred: {original.__class__.__name__}")
            print(f"Error in {ctx.command.name}:", type(original).__name__, str(original))
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore command not found errors
        else:
            await ctx.send(f"An error occurred: {error}")
            print(f"Error in {ctx.command.name}:", type(error).__name__, str(error))

def setup(bot):
    bot.add_cog(OnePieceAdventure(bot))