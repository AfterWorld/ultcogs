import discord
from redbot.core import commands, Config
import random
import asyncio
import logging

class WorldEvents:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.event_channel_id = 425068612542398476  # Your specified channel ID
        self.active_event = None
        self.participants = set()
        self.last_event_time = 0
        self.event_cooldown = 3600  # 1 hour cooldown
        self.logger = logging.getLogger("red.onepiece_adventures.world_events")

        # Event-specific attributes
        self.defenders = 0
        self.pirates = 0
        self.time_remaining = 0
        self.clues_solved = 0
        self.current_leader = None
        self.monster_hp = 1000
        self.top_damager = None
        self.explored_locations = []
        self.remaining_explorations = 5
        self.bowing = 0
        self.defying = 0
        self.legendary_pirate = None
        self.challengers = []
        self.ancient_weapon = None
        self.research_progress = 0

    async def spawn_random_event(self):
        try:
            channel = self.bot.get_channel(self.event_channel_id)
            if not channel or self.active_event:
                return

            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_event_time < self.event_cooldown:
                return

            events = [
                self.pirate_invasion,
                self.treasure_hunt,
                self.sea_monster_appearance,
                self.mysterious_island,
                self.celestial_dragon_visit,
                self.legendary_pirate_showdown,
                self.ancient_weapon_discovery
            ]
            
            event = random.choice(events)
            self.active_event = event.__name__
            self.last_event_time = current_time
            await event(channel)
        except Exception as e:
            self.logger.error(f"Error in spawn_random_event: {e}")

    async def start_event_loop(self):
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                if random.random() < 0.1:  # 10% chance to spawn an event
                    await self.spawn_random_event()
            except Exception as e:
                self.logger.error(f"Error in event loop: {e}")

    async def trigger_event_by_message(self, message):
        if random.random() < 0.001:  # 0.1% chance per message
            await self.spawn_random_event()

    async def pirate_invasion(self, channel):
        await channel.send("🏴‍☠️ A pirate fleet has been spotted! Defend the island or join their ranks! React with 🛡️ to defend or ⚔️ to join.")
        message = await channel.send("Participants:")
        
        self.defenders = 0
        self.pirates = 0
        self.time_remaining = 300  # 5 minutes

        def check(reaction, user):
            return user != self.bot.user and str(reaction.emoji) in ['🛡️', '⚔️']

        try:
            while self.time_remaining > 0:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=self.time_remaining, check=check)
                if user.id not in self.participants:
                    self.participants.add(user.id)
                    if str(reaction.emoji) == '🛡️':
                        self.defenders += 1
                    else:
                        self.pirates += 1
                    await message.edit(content=f"Participants: {', '.join([f'<@{uid}>' for uid in self.participants])}\nDefenders: {self.defenders} | Pirates: {self.pirates}")
                self.time_remaining = max(0, self.time_remaining - 10)
        except asyncio.TimeoutError:
            pass

        if self.defenders > self.pirates:
            await channel.send("The island has been successfully defended! All participants gain 100 exp and 1000 berries.")
            for uid in self.participants:
                await self.award_reward(self.bot.get_user(uid), 1000, 100, {'marine': 50})
        else:
            await channel.send("The pirates have taken over the island! Pirate participants gain 150 exp and 1500 berries.")
            for uid in self.participants:
                await self.award_reward(self.bot.get_user(uid), 1500, 150, {'pirate': 50})

        self.participants.clear()
        self.active_event = None

    async def treasure_hunt(self, channel):
        await channel.send("🗺️ A mysterious map has been discovered! The hunt for treasure begins! Use .solve_clue to progress.")
        clues = [
            "The treasure lies where the sun sets",
            "Look for the tallest palm tree",
            "X marks the spot near the lagoon"
        ]
        
        self.clues_solved = 0
        self.current_leader = None

        for i, clue in enumerate(clues, 1):
            await channel.send(f"Clue {i}: {clue}")
            
            def check(m):
                return m.channel == channel and m.content.lower().startswith('.solve_clue')

            try:
                message = await self.bot.wait_for('message', timeout=120.0, check=check)
                self.clues_solved += 1
                self.current_leader = message.author.name
                await channel.send(f"{message.author.mention} has solved the clue!")
                await self.award_reward(message.author, 1000, 50, {'pirate': 10})
            except asyncio.TimeoutError:
                await channel.send("Time's up! Moving to the next clue.")

        await channel.send(f"The treasure hunt is over! {self.current_leader} gets 5000 berries and a rare item!")
        if self.current_leader:
            leader = discord.utils.get(channel.guild.members, name=self.current_leader)
            if leader:
                await self.award_reward(leader, 5000, 200, {'pirate': 100})
        self.active_event = None

    async def sea_monster_appearance(self, channel):
        await channel.send("🐙 A giant sea monster has emerged from the depths! Band together to defeat it! Use !attack to join the battle.")
        self.monster_hp = 1000
        damage_dealt = {}
        
        while self.monster_hp > 0:
            def check(m):
                return m.channel == channel and m.content.lower() == '.attack'

            try:
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                damage = random.randint(50, 150)
                self.monster_hp -= damage
                damage_dealt[message.author.id] = damage_dealt.get(message.author.id, 0) + damage
                self.top_damager = max(damage_dealt, key=damage_dealt.get)
                await channel.send(f"{message.author.mention} deals {damage} damage to the sea monster! Monster HP: {max(0, self.monster_hp)}")
            except asyncio.TimeoutError:
                await channel.send("The sea monster attacks! All participants lose 50 HP.")

        await channel.send("The sea monster has been defeated! All participants gain 200 exp and 2000 berries.")
        for user_id, damage in damage_dealt.items():
            user = self.bot.get_user(user_id)
            if user:
                await self.award_reward(user, 2000, 200, {'pirate': 50})
        
        top_damager_user = self.bot.get_user(self.top_damager)
        if top_damager_user:
            await channel.send(f"{top_damager_user.mention} dealt the most damage and receives an additional 1000 berries!")
            await self.award_reward(top_damager_user, 1000, 100, {'pirate': 25})
        
        self.active_event = None

    async def mysterious_island(self, channel):
        await channel.send("🏝️ A mysterious island has appeared through the mist! Use .explore <location> to investigate its secrets.")
        locations = ["beach", "jungle", "cave", "ruins", "volcano"]
        treasures = {loc: random.choice(["rare fruit", "ancient weapon", "treasure map", "nothing"]) for loc in locations}
        
        self.explored_locations = []
        self.remaining_explorations = 5

        while self.remaining_explorations > 0:
            def check(m):
                return m.channel == channel and m.content.lower().startswith('!explore')

            try:
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
                location = message.content.split()[1].lower() if len(message.content.split()) > 1 else random.choice(locations)
                if location in locations and location not in self.explored_locations:
                    self.explored_locations.append(location)
                    found = treasures[location]
                    await channel.send(f"{message.author.mention} explores the {location} and finds: {found}!")
                    if found != "nothing":
                        await self.award_reward(message.author, 2000, 100, {'pirate': 20})
                elif location in self.explored_locations:
                    await channel.send(f"{message.author.mention}, that location has already been explored.")
                else:
                    await channel.send(f"{message.author.mention}, that location doesn't exist on this island.")
                self.remaining_explorations -= 1
            except asyncio.TimeoutError:
                await channel.send("The mist thickens, and the island disappears...")
                break

        await channel.send("The mysterious island fades away. The exploration is over!")
        self.active_event = None

    async def celestial_dragon_visit(self, channel):
        await channel.send("⚠️ A Celestial Dragon is visiting the island! This is a rare opportunity for immense rewards... or severe punishment. React with 🙇 to bow or 🤬 to defy.")
        message = await channel.send("Participants:")
        
        self.bowing = 0
        self.defying = 0
        participants = set()

        def check(reaction, user):
            return user != self.bot.user and str(reaction.emoji) in ['🙇', '🤬']

        try:
            for _ in range(50):  # Allow up to 50 participants
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                if user.id not in participants:
                    participants.add(user.id)
                    if str(reaction.emoji) == '🙇':
                        self.bowing += 1
                    else:
                        self.defying += 1
                    await message.edit(content=f"Participants: {', '.join([f'<@{uid}>' for uid in participants])}\nBowing: {self.bowing} | Defying: {self.defying}")
        except asyncio.TimeoutError:
            pass

        if self.bowing > self.defying:
            await channel.send("The Celestial Dragon is pleased with your respect. All participants receive a generous reward!")
            for uid in participants:
                user = self.bot.get_user(uid)
                if user:
                    await self.award_reward(user, 50000, 1000, {'world_government': 200})
        else:
            await channel.send("The Celestial Dragon is outraged! A Navy Admiral has been called to punish the defilers!")
            for uid in participants:
                user = self.bot.get_user(uid)
                if user:
                    await self.award_reward(user, -25000, 500, {'world_government': -200, 'revolutionary': 100})

        self.active_event = None

    async def legendary_pirate_showdown(self, channel):
        legendary_pirates = ["Gol D. Roger", "Whitebeard", "Big Mom", "Kaido", "Shanks"]
        self.legendary_pirate = random.choice(legendary_pirates)
        await channel.send(f"⚔️ The legendary pirate {self.legendary_pirate} has challenged the strongest pirates to a duel! Use !challenge to face them in combat.")

        self.challengers = []
        winner = None

        def check(m):
            return m.channel == channel and m.content.lower() == '!challenge'

        try:
            for _ in range(5):  # Allow up to 5 challengers
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
                self.challengers.append(message.author)
                await channel.send(f"{message.author.mention} has stepped up to challenge {self.legendary_pirate}!")
        except asyncio.TimeoutError:
            pass

        if self.challengers:
            winner = random.choice(self.challengers)
            await channel.send(f"After an epic battle, {winner.mention} emerges victorious against {self.legendary_pirate}!")
            await self.award_reward(winner, 100000, 5000, {'pirate': 500})
            for challenger in self.challengers:
                if challenger != winner:
                    await self.award_reward(challenger, 10000, 1000, {'pirate': 100})
        else:
            await channel.send(f"No one dared to challenge {self.legendary_pirate}. The legendary pirate leaves, disappointed.")

        self.active_event = None

    async def ancient_weapon_discovery(self, channel):
        weapons = ["Pluton", "Poseidon", "Uranus"]
        self.ancient_weapon = random.choice(weapons)
        await channel.send(f"🏛️ Ruins containing information about the ancient weapon {self.ancient_weapon} have been discovered! Teams of archaeologists and pirates race to uncover its secrets. Use !research to join the expedition.")

        researchers = set()
        self.research_progress = 0

        def check(m):
            return m.channel == channel and m.content.lower() == '!research'

        try:
            while self.research_progress < 100:
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                if message.author.id not in researchers:
                    researchers.add(message.author.id)
                self.research_progress += random.randint(5, 15)
                await channel.send(f"{message.author.mention} contributes to the research! Progress: {min(self.research_progress, 100)}%")
        except asyncio.TimeoutError:
            pass

        if self.research_progress >= 100:
            await channel.send(f"The secrets of {self.ancient_weapon} have been uncovered! All researchers gain immense knowledge and rewards!")
            for uid in researchers:
                user = self.bot.get_user(uid)
                if user:
                    await self.award_reward(user, 75000, 2500, {'archaeological': 300, 'world_government': -100, 'revolutionary': 100})
        else:
            await channel.send(f"The World Government intervenes and seals away the information about {self.ancient_weapon}. The expedition is a failure.")

        self.active_event = None

    async def award_reward(self, user, berries, exp, reputation=None):
        user_data = await self.config.member(user).all()
        user_data['berries'] = user_data.get('berries', 0) + berries
        user_data['exp'] = user_data.get('exp', 0) + exp
        if reputation:
            user_data['reputation'] = user_data.get('reputation', {})
            for faction, value in reputation.items():
                user_data['reputation'][faction] = user_data['reputation'].get(faction, 0) + value
        await self.config.member(user).set(user_data)

    async def solve_clue(self, ctx, solution):
        # Implement clue solving logic here
        # This is a simplified version; you might want to make it more complex
        if random.random() < 0.3:  # 30% chance of correct answer
            await self.award_reward(ctx.author, 1000, 50, {'pirate': 10})
            await ctx.send("Correct! You've solved the clue.")
            self.clues_solved += 1
            self.current_leader = ctx.author.name
        else:
            await ctx.send("That's not the correct solution. Try again!")

    async def attack_monster(self, ctx):
        damage = random.randint(50, 150)
        self.monster_hp -= damage
        await ctx.send(f"You dealt {damage} damage to the sea monster!")
        if self.monster_hp <= 0:
            await self.award_reward(ctx.author, 5000, 200, {'pirate': 50})
            await ctx.send("You've defeated the sea monster!")
            self.active_event = None

    async def explore_location(self, ctx, location):
        if location in ["beach", "jungle", "cave", "ruins", "volcano"] and location not in self.explored_locations:
            self.explored_locations.append(location)
            treasure = random.choice(["rare fruit", "ancient weapon", "treasure map", "nothing"])
            if treasure != "nothing":
                await self.award_reward(ctx.author, 2000, 100, {'pirate': 20})
            await ctx.send(f"You explored the {location} and found: {treasure}!")
            self.remaining_explorations -= 1
        elif location in self.explored_locations:
            await ctx.send("That location has already been explored.")
        else:
            await ctx.send("That location doesn't exist on this island.")

    async def event_status(self, ctx):
        if not self.active_event:
            await ctx.send("There's no active world event right now.")
        else:
            event_type = self.active_event
            status_message = f"Current event: {event_type}\n"
            
            if event_type == "pirate_invasion":
                status_message += f"Defenders: {self.defenders}\n"
                status_message += f"Pirates: {self.pirates}\n"
                status_message += f"Time remaining: {self.time_remaining} seconds"
            elif event_type == "treasure_hunt":
                status_message += f"Clues solved: {self.clues_solved}/3\n"
                status_message += f"Current leader: {self.current_leader}"
            elif event_type == "sea_monster_appearance":
                status_message += f"Sea Monster HP: {self.monster_hp}/1000\n"
                status_message += f"Top damager: {self.top_damager}"
            elif event_type == "mysterious_island":
                status_message += f"Locations explored: {', '.join(self.explored_locations)}\n"
                status_message += f"Remaining exploration attempts: {self.remaining_explorations}"
            elif event_type == "celestial_dragon_visit":
                status_message += f"Bowing: {self.bowing}\n"
                status_message += f"Defying: {self.defying}"
            elif event_type == "legendary_pirate_showdown":
                status_message += f"Legendary Pirate: {self.legendary_pirate}\n"
                status_message += f"Challengers: {', '.join([c.name for c in self.challengers])}"
            elif event_type == "ancient_weapon_discovery":
                status_message += f"Ancient Weapon: {self.ancient_weapon}\n"
                status_message += f"Research Progress: {self.research_progress}%"
            
            await ctx.send(status_message)

    async def manual_trigger_event(self, ctx):
        """Manually trigger a random world event (for testing)."""
        await self.spawn_random_event()
        await ctx.send("A world event has been manually triggered.")
