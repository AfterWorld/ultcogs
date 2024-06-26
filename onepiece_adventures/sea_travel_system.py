import discord 
from redbot.core import commands, Config 
import random
import asyncio

class SeaTravelSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def explore_current_island(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        current_island = user_data.get("current_island", "Unknown")

        events = [
            self.find_treasure,
            self.encounter_enemy,
            self.discover_secret_location,
            self.meet_npc
        ]
        event = random.choice(events)
        await event(ctx, current_island)

    async def travel_to_island(self, ctx, destination):
        user_data = await self.config.member(ctx.author).all()
        current_island = user_data.get("current_island", "Unknown")

        islands = await self.config.guild(ctx.guild).islands()
        if destination not in islands:
            return await ctx.send("That island doesn't exist or hasn't been discovered yet.")

        if current_island == destination:
            return await ctx.send("You're already on that island!")

        distance = self.calculate_distance(current_island, destination)
        travel_time = distance * 10  # 10 seconds per unit of distance
        travel_cost = distance * 100  # 100 berries per unit of distance

        if user_data.get("berries", 0) < travel_cost:
            return await ctx.send(f"You don't have enough berries to make this journey. You need {travel_cost} berries.")

        await ctx.send(f"Embarking on a journey to {destination}. This will take {travel_time} seconds and cost {travel_cost} berries.")

        user_data["berries"] -= travel_cost
        await self.config.member(ctx.author).set(user_data)

        await asyncio.sleep(travel_time)

        if random.random() < 0.3:  # 30% chance of encounter
            await self.sea_encounter(ctx)

        user_data["current_island"] = destination
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"You have arrived at {destination}!")

    async def find_treasure(self, ctx, island):
        treasure_value = random.randint(1000, 10000)
        user_data = await self.config.member(ctx.author).all()
        user_data["berries"] = user_data.get("berries", 0) + treasure_value
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"You found a treasure chest containing {treasure_value} berries!")

    async def encounter_enemy(self, ctx, island):
        enemy_strength = random.randint(50, 200)
        user_data = await self.config.member(ctx.author).all()
        user_strength = user_data.get("strength", 0) + user_data.get("defense", 0) + user_data.get("speed", 0)

        if user_strength > enemy_strength:
            reward = random.randint(500, 5000)
            user_data["berries"] = user_data.get("berries", 0) + reward
            user_data["exp"] = user_data.get("exp", 0) + 50
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"You defeated an enemy! You gained {reward} berries and 50 exp.")
        else:
            loss = random.randint(100, 1000)
            user_data["berries"] = max(0, user_data.get("berries", 0) - loss)
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"You were defeated by an enemy and lost {loss} berries.")

    async def discover_secret_location(self, ctx, island):
        await ctx.send("You discovered a secret location on the island! You can now access new quests and resources here.")

    async def meet_npc(self, ctx, island):
        npcs = ["Mysterious Old Man", "Friendly Shopkeeper", "Shady Pirate", "Marine Scout"]
        npc = random.choice(npcs)
        await ctx.send(f"You met a {npc}. They shared some interesting information with you about the island.")

    async def sea_encounter(self, ctx):
        encounters = ["Sea King", "Rival Pirate Ship", "Marine Patrol", "Calm Belt"]
        encounter = random.choice(encounters)
        await ctx.send(f"During your journey, you encountered a {encounter}!")

        if encounter == "Sea King":
            await self.sea_king_battle(ctx)
        elif encounter == "Rival Pirate Ship":
            await self.pirate_ship_encounter(ctx)
        elif encounter == "Marine Patrol":
            await self.marine_patrol_encounter(ctx)
        else:  # Calm Belt
            await self.calm_belt_encounter(ctx)

    def calculate_distance(self, island1, island2):
        # Placeholder: replace with actual distance calculation based on island coordinates
        return random.randint(1, 10)

    async def sea_king_battle(self, ctx):
        sea_king_strength = random.randint(100, 500)
        user_data = await self.config.member(ctx.author).all()
        user_strength = user_data.get("strength", 0) + user_data.get("defense", 0) + user_data.get("speed", 0)

        await ctx.send("A massive Sea King has appeared! Prepare for battle!")
        await asyncio.sleep(2)

        if user_strength > sea_king_strength:
            reward = random.randint(1000, 10000)
            user_data["berries"] = user_data.get("berries", 0) + reward
            user_data["exp"] = user_data.get("exp", 0) + 100
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"You defeated the Sea King! You gained {reward} berries and 100 exp.")
        else:
            loss = random.randint(500, 5000)
            user_data["berries"] = max(0, user_data.get("berries", 0) - loss)
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"The Sea King was too strong! You lost {loss} berries in the encounter.")

    async def pirate_ship_encounter(self, ctx):
        pirate_strength = random.randint(50, 300)
        user_data = await self.config.member(ctx.author).all()
        user_strength = user_data.get("strength", 0) + user_data.get("defense", 0) + user_data.get("speed", 0)

        await ctx.send("A rival pirate ship has spotted you! What will you do? (fight/flee)")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['fight', 'flee']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to decide. The pirate ship has fled.")

        if msg.content.lower() == 'fight':
            if user_strength > pirate_strength:
                reward = random.randint(5000, 20000)
                user_data["berries"] = user_data.get("berries", 0) + reward
                user_data["exp"] = user_data.get("exp", 0) + 200
                user_data["reputation"] = user_data.get("reputation", {})
                user_data["reputation"]["pirate"] = user_data["reputation"].get("pirate", 0) + 50
                await self.config.member(ctx.author).set(user_data)
                await ctx.send(f"You defeated the rival pirates! You gained {reward} berries, 200 exp, and 50 pirate reputation.")
            else:
                loss = random.randint(1000, 10000)
                user_data["berries"] = max(0, user_data.get("berries", 0) - loss)
                await self.config.member(ctx.author).set(user_data)
                await ctx.send(f"The rival pirates were too strong! You lost {loss} berries in the battle.")
        else:
            await ctx.send("You managed to flee from the rival pirate ship!")

    async def marine_patrol_encounter(self, ctx):
        marine_strength = random.randint(75, 400)
        user_data = await self.config.member(ctx.author).all()
        user_strength = user_data.get("strength", 0) + user_data.get("defense", 0) + user_data.get("speed", 0)

        await ctx.send("A Marine patrol ship has spotted you! What will you do? (fight/flee/surrender)")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['fight', 'flee', 'surrender']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to decide. The Marine ship has engaged you!")

        if msg.content.lower() == 'fight':
            if user_strength > marine_strength:
                reward = random.randint(10000, 30000)
                user_data["berries"] = user_data.get("berries", 0) + reward
                user_data["exp"] = user_data.get("exp", 0) + 300
                user_data["reputation"] = user_data.get("reputation", {})
                user_data["reputation"]["pirate"] = user_data["reputation"].get("pirate", 0) + 100
                user_data["reputation"]["marine"] = max(0, user_data["reputation"].get("marine", 0) - 100)
                await self.config.member(ctx.author).set(user_data)
                await ctx.send(f"You defeated the Marine patrol! You gained {reward} berries, 300 exp, and 100 pirate reputation. Your Marine reputation decreased by 100.")
            else:
                loss = random.randint(5000, 20000)
                user_data["berries"] = max(0, user_data.get("berries", 0) - loss)
                user_data["reputation"] = user_data.get("reputation", {})
                user_data["reputation"]["marine"] = max(0, user_data["reputation"].get("marine", 0) - 50)
                await self.config.member(ctx.author).set(user_data)
                await ctx.send(f"The Marine patrol was too strong! You lost {loss} berries and 50 Marine reputation.")
        elif msg.content.lower() == 'flee':
            if random.random() < 0.6:  # 60% chance to escape
                await ctx.send("You managed to escape from the Marine patrol!")
            else:
                loss = random.randint(2000, 10000)
                user_data["berries"] = max(0, user_data.get("berries", 0) - loss)
                user_data["reputation"] = user_data.get("reputation", {})
                user_data["reputation"]["marine"] = max(0, user_data["reputation"].get("marine", 0) - 25)
                await self.config.member(ctx.author).set(user_data)
                await ctx.send(f"You failed to escape! The Marines caught up and fined you {loss} berries. Your Marine reputation decreased by 25.")
        else:  # surrender
            fine = random.randint(1000, 5000)
            user_data["berries"] = max(0, user_data.get("berries", 0) - fine)
            user_data["reputation"] = user_data.get("reputation", {})
            user_data["reputation"]["marine"] = user_data["reputation"].get("marine", 0) + 25
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"You surrendered to the Marine patrol. They fined you {fine} berries but your Marine reputation increased by 25.")

    async def calm_belt_encounter(self, ctx):
        await ctx.send("You've entered the Calm Belt! This area is known for its lack of winds and abundance of Sea Kings.")
        
        user_data = await self.config.member(ctx.author).all()
        ship_quality = user_data.get("ship_quality", 1)  # Assume a default ship quality of 1 if not set
        
        # Check if the user has a method to navigate the Calm Belt
        has_seastone = "seastone_coating" in user_data.get("ship_upgrades", [])
        has_paddles = "paddles" in user_data.get("ship_upgrades", [])
        
        if has_seastone:
            await ctx.send("Your ship's Seastone coating keeps the Sea Kings at bay, allowing for safe passage.")
            return
        
        if has_paddles:
            await ctx.send("You use your ship's paddles to slowly and quietly navigate through the Calm Belt.")
            if random.random() < 0.3:  # 30% chance of encounter even with paddles
                await self.sea_king_battle(ctx)
            return
        
        # If no special upgrades, face the dangers of the Calm Belt
        await ctx.send("Without wind or special equipment, you're at the mercy of the Calm Belt's dangers.")
        
        danger_level = random.random()
        
        if danger_level < 0.4:  # 40% chance of minor setback
            delay = random.randint(1, 5)
            await ctx.send(f"You manage to avoid any major dangers, but your journey is delayed by {delay} hours.")
        elif danger_level < 0.7:  # 30% chance of moderate danger
            await self.sea_king_battle(ctx)
        else:  # 30% chance of severe danger
            damage = random.randint(1000, 5000)
            user_data["berries"] = max(0, user_data.get("berries", 0) - damage)
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"A massive Sea King attacks your ship! You barely escape, but suffer {damage} berries worth of damage to your ship.")
            
            if random.random() < 0.5:  # 50% chance of additional crew injury
                injury_cost = random.randint(500, 2000)
                user_data["berries"] = max(0, user_data.get("berries", 0) - injury_cost)
                await self.config.member(ctx.author).set(user_data)
                await ctx.send(f"One of your crew members is injured in the attack. Medical expenses cost you an additional {injury_cost} berries.")

    async def dock_at_port(self, ctx, island_name: str):
        user_data = await self.config.member(ctx.author).all()
        islands = await self.config.guild(ctx.guild).islands()
        
        if island_name not in islands:
            return await ctx.send("That island doesn't exist or hasn't been discovered yet.")
        
        if 'Port' not in islands[island_name].get('developments', []):
            return await ctx.send("This island doesn't have a port to dock at.")
        
        docking_fee = 500  # Example fee
        if user_data.get('berries', 0) < docking_fee:
            return await ctx.send(f"You don't have enough berries to pay the docking fee of {docking_fee}.")
        
        user_data['berries'] = user_data.get('berries', 0) - docking_fee
        user_data['current_island'] = island_name
        await self.config.member(ctx.author).set(user_data)
        
        await ctx.send(f"You've docked at {island_name} and paid {docking_fee} berries in fees. Welcome!")

    async def start_fishing(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('current_island') == "At Sea":
            return await ctx.send("You need to be docked at an island to go fishing.")
        
        fish_types = ["Tuna", "Sea King", "Flying Fish", "Blue-Finned Elephant Tuna", "Neptunian Squid"]
        caught_fish = random.choice(fish_types)
        value = random.randint(100, 1000)
        
        user_data['inventory'] = user_data.get('inventory', {})
        user_data['inventory'][caught_fish] = user_data['inventory'].get(caught_fish, 0) + 1
        await self.config.member(ctx.author).set(user_data)
        
        await ctx.send(f"You caught a {caught_fish}! It's worth approximately {value} berries.")

    async def upgrade_ship(self, ctx, upgrade: str):
        valid_upgrades = ["cannons", "sails", "hull", "figurehead", "wheel", "seastone_coating", "paddles"]
        if upgrade not in valid_upgrades:
            return await ctx.send(f"Invalid upgrade. Choose from: {', '.join(valid_upgrades)}")
        
        user_data = await self.config.member(ctx.author).all()
        cost = 5000  # Example cost
        if user_data.get('berries', 0) < cost:
            return await ctx.send(f"You don't have enough berries. The upgrade costs {cost}.")
        
        user_data['berries'] = user_data.get('berries', 0) - cost
        user_data['ship_upgrades'] = user_data.get('ship_upgrades', [])
        if upgrade not in user_data['ship_upgrades']:
            user_data['ship_upgrades'].append(upgrade)
        await self.config.member(ctx.author).set(user_data)
        
        await ctx.send(f"You've upgraded your ship with improved {upgrade}!")

    async def view_ship(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        ship_upgrades = user_data.get('ship_upgrades', [])
        
        if not ship_upgrades:
            await ctx.send("Your ship currently has no upgrades.")
        else:
            upgrades_list = ", ".join(ship_upgrades)
            await ctx.send(f"Your ship has the following upgrades: {upgrades_list}")

    async def check_island(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        current_island = user_data.get('current_island', "Unknown")
        
        islands = await self.config.guild(ctx.guild).islands()
        if current_island in islands:
            island_info = islands[current_island]
            developments = ", ".join(island_info.get('developments', ["None"]))
            await ctx.send(f"You are currently on {current_island}. Island developments: {developments}")
        else:
            await ctx.send(f"You are currently on {current_island}. No additional information available.")

    async def list_islands(self, ctx):
        islands = await self.config.guild(ctx.guild).islands()
        island_list = "\n".join(islands.keys())
        await ctx.send(f"Known islands:\n{island_list}")

    async def create_island(self, ctx, island_name: str):
        if not await self.bot.is_owner(ctx.author):
            return await ctx.send("Only the bot owner can create new islands.")
        
        islands = await self.config.guild(ctx.guild).islands()
        if island_name in islands:
            return await ctx.send("This island already exists.")
        
        islands[island_name] = {"developments": []}
        await self.config.guild(ctx.guild).islands.set(islands)
        await ctx.send(f"Island {island_name} has been created.")

    async def add_island_development(self, ctx, island_name: str, development: str):
        if not await self.bot.is_owner(ctx.author):
            return await ctx.send("Only the bot owner can add island developments.")
        
        islands = await self.config.guild(ctx.guild).islands()
        if island_name not in islands:
            return await ctx.send("This island doesn't exist.")
        
        if development not in self.development_options:
            return await ctx.send(f"Invalid development. Choose from: {', '.join(self.development_options.keys())}")
        
        if development not in islands[island_name]['developments']:
            islands[island_name]['developments'].append(development)
            await self.config.guild(ctx.guild).islands.set(islands)
            await ctx.send(f"{development} has been added to {island_name}.")
        else:
            await ctx.send(f"{island_name} already has {development}.")
            
    async def check_weather(self, ctx):
        weather_conditions = ["Clear", "Stormy", "Foggy", "Calm"]
        current_weather = random.choice(weather_conditions)
        await ctx.send(f"The current weather is: {current_weather}")

    async def train_navigation(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        navigation_skill = user_data.get('navigation_skill', 0)
        if navigation_skill < 100:
            user_data['navigation_skill'] = navigation_skill + 1
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"You've improved your navigation skill! Current level: {navigation_skill + 1}")
        else:
            await ctx.send("Your navigation skill is already at maximum level!")

    async def repair_ship(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        repair_cost = 1000
        if user_data.get('berries', 0) < repair_cost:
            return await ctx.send(f"You don't have enough berries to repair your ship. Cost: {repair_cost} berries")
        user_data['berries'] -= repair_cost
        user_data['ship_health'] = 100
        await self.config.member(ctx.author).set(user_data)
        await ctx.send("Your ship has been fully repaired!")

    async def create_sea_chart(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if 'sea_chart' in user_data.get('inventory', {}):
            return await ctx.send("You already have a sea chart.")
        cost = 5000
        if user_data.get('berries', 0) < cost:
            return await ctx.send(f"You don't have enough berries to create a sea chart. Cost: {cost} berries")
        user_data['berries'] -= cost
        user_data['inventory'] = user_data.get('inventory', {})
        user_data['inventory']['sea_chart'] = 1
        await self.config.member(ctx.author).set(user_data)
        await ctx.send("You've created a sea chart! This will help you navigate more efficiently.")

    # You might want to add more methods here for other sea travel related functionalities