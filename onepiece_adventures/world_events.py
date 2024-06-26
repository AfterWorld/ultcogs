import discord # type: ignore
from redbot.core import commands, Config # type: ignore
import random
import asyncio

class WorldEvents:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.event_channel_id = 425068612542398476  # Your specified channel ID
        self.active_event = None
        self.participants = set()

    async def spawn_random_event(self):
        channel = self.bot.get_channel(self.event_channel_id)
        if not channel or self.active_event:
            return

        events = [
            self.pirate_invasion,
            self.treasure_hunt,
            self.sea_monster_appearance,
            self.mysterious_island
        ]
        event = random.choice(events)
        self.active_event = event.__name__
        await event(channel)

    async def pirate_invasion(self, channel):
        await channel.send("🏴‍☠️ A pirate fleet has been spotted! Defend the island or join their ranks! React with 🛡️ to defend or ⚔️ to join.")
        message = await channel.send("Participants:")
        
        def check(reaction, user):
            return user != self.bot.user and str(reaction.emoji) in ['🛡️', '⚔️']

        try:
            while len(self.participants) < 10:  # Limit to 10 participants
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                if user.id not in self.participants:
                    self.participants.add(user.id)
                    await message.edit(content=f"Participants: {', '.join([f'<@{uid}>' for uid in self.participants])}")
        except asyncio.TimeoutError:
            pass

        defenders = sum(1 for _ in self.participants if random.choice([True, False]))  # Randomly assign roles
        pirates = len(self.participants) - defenders
        
        if defenders > pirates:
            await channel.send("The island has been successfully defended! All participants gain 100 exp and 1000 berries.")
        else:
            await channel.send("The pirates have taken over the island! Pirate participants gain 150 exp and 1500 berries.")

        # Reward participants (you'll need to implement this based on your user data structure)
        for uid in self.participants:
            # Reward user with exp and berries
            pass

        self.participants.clear()
        self.active_event = None

    async def treasure_hunt(self, channel):
        await channel.send("🗺️ A mysterious map has been discovered! The hunt for treasure begins! Use !solve_clue to progress.")
        clues = [
            "The treasure lies where the sun sets",
            "Look for the tallest palm tree",
            "X marks the spot near the lagoon"
        ]
        
        for i, clue in enumerate(clues, 1):
            await channel.send(f"Clue {i}: {clue}")
            
            def check(m):
                return m.channel == channel and m.content.lower().startswith('.solve_clue')

            try:
                message = await self.bot.wait_for('message', timeout=120.0, check=check)
                await channel.send(f"{message.author.mention} has solved the clue!")
            except asyncio.TimeoutError:
                await channel.send("Time's up! Moving to the next clue.")

        await channel.send("The treasure hunt is over! The first to solve all clues gets 5000 berries and a rare item!")
        self.active_event = None

    async def sea_monster_appearance(self, channel):
        await channel.send("🐙 A giant sea monster has emerged from the depths! Band together to defeat it! Use !attack to join the battle.")
        monster_hp = 1000
        
        while monster_hp > 0:
            def check(m):
                return m.channel == channel and m.content.lower() == '.attack'

            try:
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                damage = random.randint(50, 150)
                monster_hp -= damage
                await channel.send(f"{message.author.mention} deals {damage} damage to the sea monster! Monster HP: {max(0, monster_hp)}")
            except asyncio.TimeoutError:
                await channel.send("The sea monster attacks! All participants lose 50 HP.")

        await channel.send("The sea monster has been defeated! All participants gain 200 exp and 2000 berries.")
        self.active_event = None

    async def mysterious_island(self, channel):
        await channel.send("🏝️ A mysterious island has appeared through the mist! Use !explore to investigate its secrets.")
        locations = ["beach", "jungle", "cave", "ruins", "volcano"]
        treasures = {loc: random.choice(["rare fruit", "ancient weapon", "treasure map", "nothing"]) for loc in locations}
        
        for _ in range(5):  # Allow 5 exploration attempts
            def check(m):
                return m.channel == channel and m.content.lower().startswith('.explore')

            try:
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
                location = message.content.split()[1].lower() if len(message.content.split()) > 1 else random.choice(locations)
                if location in locations:
                    found = treasures[location]
                    await channel.send(f"{message.author.mention} explores the {location} and finds: {found}!")
                    if found != "nothing":
                        # Add the found item to the user's inventory
                        pass
                else:
                    await channel.send(f"{message.author.mention}, that location doesn't exist on this island.")
            except asyncio.TimeoutError:
                await channel.send("The mist thickens, and the island disappears...")
                break

        # Add more event methods as needed

        await channel.send("The mysterious island fades away. The exploration is over!")
        self.active_event = None

    async def start_event_loop(self):
        while True:
            await asyncio.sleep(3600)  # Wait for 1 hour
            if random.random() < 0.5:  # 50% chance to spawn an event
                await self.spawn_random_event()