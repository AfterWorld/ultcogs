from redbot.core import commands
from discord.ext import commands as discord_commands
from discord import ButtonStyle, Interaction, Embed, Member
from discord.ui import Button, View
import random
from datetime import datetime, timedelta

class OnePieceRPG(commands.Cog):
    """One Piece RPG game for solo players."""

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.devil_fruits = [
            "kilo fruit", "spin fruit", "chop fruit", "spring fruit", "bomb fruit", "smoke fruit", "spike fruit",
            "flame fruit", "falcon fruit", "ice fruit", "sand fruit", "dark fruit", "revive fruit", "daimond fruit",
            "light fruit", "love fruit", "rubber fruit", "barrier fruit", "tremor fruit", "buddha fruit",
            "door fruit", "rumble fruit", "paw fruit", "blizzard fruit", "gravity fruit",
            "dough fruit", "shadow fruit", "control fruit", "spirit fruit", "dragon fruit", "leopard fruit", "venom fruit",
            "hollow fruit", "invisable fruit", "human fruit", "sing fruit", "slow fruit", "Nika no mi", "lightning fruit",
            "gas fruit", "snow fruit", "magnet fruit", "T rex fruit", "spino fruit", "bronto fruit", "soap fruit",
            "giraffe fruit", "wax fruit", "flower fruit", "face swap fruit", "sword fruit", "mira mira no mi", "mera mera no mi",
            "yami yami no mi", "gomu gomu no mi", "hie hie no mi", "magu magu no mi", "pika pika no mi", "tori tori no mi",
            "zushi zushi no mi", "ushi ushi no mi", "moku moku no mi", "suna suna no mi", "gura gura no mi", "ope ope no mi",
            "horo horo no mi", "bara bara no mi", "bari bari no mi", "mushi mushi no mi", "noro noro no mi", "baku baku no mi",
            "bomu bomu no mi", "doru doru no mi", "kilo kilo no mi", "kilo kilo no mi", "mato mato no mi", "mosa mosa no mi",
            "nagi nagi no mi", "noro noro no mi", "ori ori no mi", "sabi sabi no mi", "suke suke no mi", "tama tama no mi",
            "ton ton no mi", "yomi yomi no mi", "zushi zushi no mi"
        ]
        self.islands = [
            {"name": "Skypiea", "boss": "Enel", "level": 30, "weapon": {"name": "Golden Staff", "drop_rate": 0.2, "stats": {"Haki": 10}}},
            {"name": "Dressrosa", "boss": "Doflamingo", "level": 50, "weapon": {"name": "String String Fruit", "drop_rate": 0.15, "stats": {"Devil Fruit": 15}}},
            {"name": "Whole Cake Island", "boss": "Big Mom", "level": 70, "weapon": {"name": "Napoleon", "drop_rate": 0.1, "stats": {"Sword": 20}}},
            {"name": "Wano Country", "boss": "Kaido", "level": 90, "weapon": {"name": "Kanabo", "drop_rate": 0.05, "stats": {"Haki": 25}}},
            {"name": "Alabasta", "boss": "Crocodile", "level": 40, "weapon": {"name": "Hook", "drop_rate": 0.2, "stats": {"Devil Fruit": 10}}},
            {"name": "Fishman Island", "boss": "Hody Jones", "level": 20, "weapon": {"name": "Kiribachi", "drop_rate": 0.25, "stats": {"Sword": 5}}},
            {"name": "Punk Hazard", "boss": "Caesar Clown", "level": 35, "weapon": {"name": "Gas Gas Fruit", "drop_rate": 0.2, "stats": {"Devil Fruit": 10}}},
            {"name": "Zou", "boss": "Jack", "level": 45, "weapon": {"name": "Scythe", "drop_rate": 0.2, "stats": {"Sword": 10}}},
            {"name": "Sabaody Archipelago", "boss": "Kizaru", "level": 60, "weapon": {"name": "Light Light Fruit", "drop_rate": 0.15, "stats": {"Devil Fruit": 15}}},
            {"name": "Marineford", "boss": "Akainu", "level": 80, "weapon": {"name": "Magma Magma Fruit", "drop_rate": 0.1, "stats": {"Devil Fruit": 20}}},
            {"name": "Enies Lobby", "boss": "Rob Lucci", "level": 25, "weapon": {"name": "Rokushiki", "drop_rate": 0.25, "stats": {"Haki": 5}}},
            {"name": "Water 7", "boss": "Franky", "level": 15, "weapon": {"name": "Franky Shogun", "drop_rate": 0.3, "stats": {"Gun": 5}}},
            {"name": "Thriller Bark", "boss": "Moria", "level": 55, "weapon": {"name": "Shadow Shadow Fruit", "drop_rate": 0.15, "stats": {"Devil Fruit": 15}}},
            {"name": "Jaya", "boss": "Bellamy", "level": 10, "weapon": {"name": "Spring Spring Fruit", "drop_rate": 0.3, "stats": {"Devil Fruit": 5}}},
            {"name": "Little Garden", "boss": "Mr. 3", "level": 5, "weapon": {"name": "Wax Wax Fruit", "drop_rate": 0.3, "stats": {"Devil Fruit": 5}}},
            {"name": "Drum Island", "boss": "Wapol", "level": 10, "weapon": {"name": "Baku Baku no Mi", "drop_rate": 0.3, "stats": {"Devil Fruit": 5}}},
            {"name": "Loguetown", "boss": "Smoker", "level": 20, "weapon": {"name": "Smoke Smoke Fruit", "drop_rate": 0.25, "stats": {"Devil Fruit": 10}}},
            {"name": "Reverse Mountain", "boss": "Laboon", "level": 5, "weapon": {"name": "Whale Attack", "drop_rate": 0.3, "stats": {"Haki": 5}}},
            {"name": "Whiskey Peak", "boss": "Mr. 5", "level": 10, "weapon": {"name": "Bomb Bomb Fruit", "drop_rate": 0.3, "stats": {"Devil Fruit": 5}}},
            {"name": "Long Ring Long Land", "boss": "Foxy", "level": 15, "weapon": {"name": "Slow Slow Beam", "drop_rate": 0.3, "stats": {"Devil Fruit": 5}}},
            {"name": "Baltigo", "boss": "Dragon", "level": 85, "weapon": {"name": "Revolutionary Army", "drop_rate": 0.1, "stats": {"Haki": 20}}},
            {"name": "Raftel", "boss": "Gol D. Roger", "level": 100, "weapon": {"name": "Supreme King Haki", "drop_rate": 0.05, "stats": {"Haki": 30}}}
        ]
        self.weapons = [
            "Katana", "Pistol", "Rifle", "Cannon", "Cutlass", "Saber", "Trident", "Naginata", "Scythe", "Club",
            "Dagger", "Sling", "Bow", "Crossbow", "Halberd", "Axe", "Mace", "Spear", "Whip", "Flail"
        ]
        self.quests = [
            {"name": "Defeat 10 Pirates", "reward": 100, "type": "battle", "target": "Pirate", "count": 10},
            {"name": "Sail to 5 Islands", "reward": 50, "type": "sail", "count": 5},
            {"name": "Find 3 Devil Fruits", "reward": 150, "type": "df", "count": 3},
        ]
        self.guilds = {}
        self.daily_rewards = [
            {"day": 1, "reward": "100 currency"},
            {"day": 2, "reward": "1 random weapon"},
            {"day": 3, "reward": "1 random devil fruit"},
            {"day": 4, "reward": "200 currency"},
            {"day": 5, "reward": "1 rare item"},
        ]
        self.crafting_recipes = {
            "Ultimate Sword": {"ingredients": ["Katana", "Saber", "Haki Essence"], "stats": {"Sword": 50}},
            "Ultimate Gun": {"ingredients": ["Pistol", "Rifle", "Gunpowder"], "stats": {"Gun": 50}},
        }
        self.titles = ["Pirate King", "Fleet Admiral", "Sword Master", "Gun Master", "Devil Fruit Master", "Haki Master"]
        self.badges = ["First Blood", "Treasure Hunter", "Boss Slayer", "PvP Champion", "Quest Master"]
        self.companions = ["Chopper", "Zoro", "Sanji", "Nami", "Robin", "Franky", "Brook", "Jinbe"]
        self.housing_items = ["Bed", "Table", "Chair", "Lamp", "Bookshelf", "Carpet", "Painting", "Plant"]

    @commands.command()
    async def beginsail(self, ctx):
        """Begin your journey as a Marine or Pirate."""
        view = View()
        view.add_item(Button(label="Marine", style=ButtonStyle.primary, custom_id="marine"))
        view.add_item(Button(label="Pirate", style=ButtonStyle.danger, custom_id="pirate"))

        async def button_callback(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("This is not your journey!", ephemeral=True)
                return

            path = interaction.custom_id
            self.players[ctx.author.id] = {
                "path": path,
                "level": 5,
                "exp": 0,
                "stats": {"Sword": 0, "Gun": 0, "Devil Fruit": 0, "Haki": 0},
                "inventory": [],
                "last_trained": None,
                "quests": [],
                "currency": 0,
                "skills": {},
                "guild": None,
                "daily_login": None,
                "titles": [],
                "badges": [],
                "companions": [],
                "housing": []
            }
            if path == "marine":
                await interaction.response.send_message("You have chosen the path of a Marine! Your goal is to become Fleet Admiral and stop the pirates.")
            else:
                await interaction.response.send_message("You have chosen the path of a Pirate! Your goal is to become the King of the Pirates.")

        for item in view.children:
            item.callback = button_callback

        await ctx.send("Choose your path:", view=view)

    @commands.command()
    async def sail(self, ctx):
        """Sail to a new island."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        island = random.choice(self.islands)
        self.players[ctx.author.id]["exp"] += 5
        await ctx.send(f"You have sailed to {island['name']}!")

    @commands.command()
    async def battle(self, ctx):
        """Battle against a random enemy."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        path = self.players[ctx.author.id]["path"]
        if path == "marine":
            enemies = ["Pirate", "Revolutionary", "Yonko"]
        else:
            enemies = ["Marine", "Cipher Pol", "Admiral"]

        enemy = random.choice(enemies)
        result = random.choice(["won", "lost"])
        if result == "won":
            self.players[ctx.author.id]["exp"] += 10
            weapon = random.choice(self.weapons)
            self.players[ctx.author.id]["inventory"].append(weapon)
            await ctx.send(f"You encountered a {enemy} and you {result} the battle! You found a {weapon}.")
        else:
            await ctx.send(f"You encountered a {enemy} and you {result} the battle!")

    @commands.command()
    async def raid(self, ctx):
        """Raid as a Pirate."""
        if ctx.author.id not in self.players or self.players[ctx.author.id]["path"] != "pirate":
            await ctx.send("You need to be a Pirate to raid. Start your journey with `.beginsail` first.")
            return
        self.players[ctx.author.id]["exp"] += 20
        await ctx.send("You have successfully raided a village!")

    @commands.command()
    async def plunder(self, ctx):
        """Plunder as a Pirate."""
        if ctx.author.id not in self.players or self.players[ctx.author.id]["path"] != "pirate":
            await ctx.send("You need to be a Pirate to plunder. Start your journey with `.beginsail` first.")
            return
        self.players[ctx.author.id]["exp"] += 15
        await ctx.send("You have plundered a treasure chest!")

    @commands.command()
    async def defend(self, ctx):
        """Defend as a Marine."""
        if ctx.author.id not in self.players or self.players[ctx.author.id]["path"] != "marine":
            await ctx.send("You need to be a Marine to defend. Start your journey with `.beginsail` first.")
            return
        self.players[ctx.author.id]["exp"] += 20
        await ctx.send("You have defended the town from pirates!")

    @commands.command()
    async def df(self, ctx):
        """Find a Devil Fruit."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        fruit = random.choice(self.devil_fruits)
        self.players[ctx.author.id]["inventory"].append(fruit)
        self.players[ctx.author.id]["exp"] += 25
        await ctx.send(f"You have found a {fruit}!")

    @commands.command()
    async def pstats(self, ctx):
        """View and allocate stats."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        embed = Embed(title=f"{ctx.author.name}'s Stats", description="Allocate your points wisely!")
        embed.add_field(name="Level", value=player["level"])
        embed.add_field(name="EXP", value=player["exp"])
        for stat, value in player["stats"].items():
            embed.add_field(name=stat, value=value)

        view = View()
        for stat in player["stats"]:
            view.add_item(Button(label=f"Increase {stat}", style=ButtonStyle.secondary, custom_id=stat))

        async def button_callback(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("These are not your stats!", ephemeral=True)
                return

            stat = interaction.custom_id
            player["stats"][stat] += 1
            await interaction.response.edit_message(embed=embed, view=view)

        for item in view.children:
            item.callback = button_callback

        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def inventory(self, ctx):
        """View your inventory."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        inventory = player["inventory"]
        if not inventory:
            await ctx.send("Your inventory is empty.")
            return

        embed = Embed(title=f"{ctx.author.name}'s Inventory")
        for item in inventory:
            embed.add_field(name=item, value="")

        await ctx.send(embed=embed)

    @commands.command()
    async def boss(self, ctx):
        """Fight the boss of the current island."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        island = random.choice(self.islands)
        if player["level"] < island["level"]:
            await ctx.send(f"You need to be level {island['level']} to fight {island['boss']} on {island['name']}.")
            return

        result = random.choice(["won", "lost"])
        if result == "won":
            self.players[ctx.author.id]["exp"] += 50
            if random.random() < island["weapon"]["drop_rate"]:
                self.players[ctx.author.id]["inventory"].append(island["weapon"]["name"])
                for stat, value in island["weapon"]["stats"].items():
                    self.players[ctx.author.id]["stats"][stat] += value
                await ctx.send(f"You have defeated {island['boss']} on {island['name']} and obtained {island['weapon']['name']}!")
            else:
                await ctx.send(f"You have defeated {island['boss']} on {island['name']} but did not obtain their weapon.")
        else:
            await ctx.send(f"You were defeated by {island['boss']} on {island['name']}.")

    @commands.command()
    async def train(self, ctx):
        """Train to increase a stat point once a day."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        now = datetime.now()
        if player["last_trained"] and now - player["last_trained"] < timedelta(days=1):
            await ctx.send("You can only train once a day. Try again later.")
            return

        player["last_trained"] = now
        view = View()
        for stat in player["stats"]:
            view.add_item(Button(label=f"Train {stat}", style=ButtonStyle.secondary, custom_id=stat))

        async def button_callback(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("These are not your stats!", ephemeral=True)
                return

            stat = interaction.custom_id
            player["stats"][stat] += 1
            await interaction.response.send_message(f"You have trained your {stat} stat!")

        for item in view.children:
            item.callback = button_callback

        await ctx.send("Choose a stat to train:", view=view)

    @commands.command()
    async def quest(self, ctx):
        """View and accept quests."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        embed = Embed(title="Available Quests")
        for quest in self.quests:
            embed.add_field(name=quest["name"], value=f"Reward: {quest['reward']} EXP")

        view = View()
        for quest in self.quests:
            view.add_item(Button(label=f"Accept {quest['name']}", style=ButtonStyle.primary, custom_id=quest["name"]))

        async def button_callback(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("This is not your quest!", ephemeral=True)
                return

            quest_name = interaction.custom_id
            for quest in self.quests:
                if quest["name"] == quest_name:
                    player["quests"].append(quest)
                    await interaction.response.send_message(f"You have accepted the quest: {quest_name}")

        for item in view.children:
            item.callback = button_callback

        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def guild(self, ctx, action: str, name: str = None):
        """Manage your guild."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        if action == "create":
            if name in self.guilds:
                await ctx.send("A guild with this name already exists.")
                return
            self.guilds[name] = {"members": [ctx.author.id], "level": 1, "exp": 0}
            player["guild"] = name
            await ctx.send(f"Guild {name} created successfully!")
        elif action == "join":
            if name not in self.guilds:
                await ctx.send("This guild does not exist.")
                return
            self.guilds[name]["members"].append(ctx.author.id)
            player["guild"] = name
            await ctx.send(f"You have joined the guild {name}!")
        elif action == "leave":
            if not player["guild"]:
                await ctx.send("You are not in a guild.")
                return
            guild_name = player["guild"]
            self.guilds[guild_name]["members"].remove(ctx.author.id)
            player["guild"] = None
            await ctx.send(f"You have left the guild {guild_name}.")
        else:
            await ctx.send("Invalid action. Use `create`, `join`, or `leave`.")

    @commands.command()
    async def pvp(self, ctx, opponent: Member):
        """Challenge another player to a PvP battle."""
        if ctx.author.id not in self.players or opponent.id not in self.players:
            await ctx.send("Both players need to start their journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        opponent_player = self.players[opponent.id]

        result = random.choice(["won", "lost"])
        if result == "won":
            player["exp"] += 30
            await ctx.send(f"{ctx.author.name} has won the PvP battle against {opponent.name}!")
        else:
            opponent_player["exp"] += 30
            await ctx.send(f"{opponent.name} has won the PvP battle against {ctx.author.name}!")

    @commands.command()
    async def event(self, ctx):
        """Participate in a special event."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        event_type = random.choice(["treasure hunt", "boss raid", "holiday event"])
        if event_type == "treasure hunt":
            reward = random.choice(self.weapons)
            self.players[ctx.author.id]["inventory"].append(reward)
            await ctx.send(f"You participated in a treasure hunt and found a {reward}!")
        elif event_type == "boss raid":
            boss = random.choice(self.islands)["boss"]
            result = random.choice(["won", "lost"])
            if result == "won":
                self.players[ctx.author.id]["exp"] += 100
                await ctx.send(f"You participated in a boss raid and defeated {boss}!")
            else:
                await ctx.send(f"You participated in a boss raid and were defeated by {boss}.")
        else:
            reward = random.choice(["holiday item", "special currency"])
            self.players[ctx.author.id]["inventory"].append(reward)
            await ctx.send(f"You participated in a holiday event and received a {reward}!")

    @commands.command()
    async def skills(self, ctx):
        """View and upgrade skills."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        embed = Embed(title=f"{ctx.author.name}'s Skills")
        for skill, level in player["skills"].items():
            embed.add_field(name=skill, value=f"Level: {level}")

        view = View()
        for skill in ["Sword Mastery", "Gun Mastery", "Devil Fruit Mastery", "Haki Mastery"]:
            view.add_item(Button(label=f"Upgrade {skill}", style=ButtonStyle.secondary, custom_id=skill))

        async def button_callback(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("These are not your skills!", ephemeral=True)
                return

            skill = interaction.custom_id
            if skill not in player["skills"]:
                player["skills"][skill] = 1
            else:
                player["skills"][skill] += 1
            await interaction.response.send_message(f"You have upgraded your {skill} to level {player['skills'][skill]}!")

        for item in view.children:
            item.callback = button_callback

        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def achievements(self, ctx):
        """View your achievements."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        embed = Embed(title=f"{ctx.author.name}'s Achievements")
        for achievement in player.get("achievements", []):
            embed.add_field(name=achievement, value="Completed")

        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx):
        """View the leaderboard."""
        leaderboard = sorted(self.players.items(), key=lambda x: x[1]["exp"], reverse=True)
        embed = Embed(title="Leaderboard")
        for i, (player_id, player_data) in enumerate(leaderboard[:10], 1):
            user = self.bot.get_user(player_id)
            embed.add_field(name=f"{i}. {user.name}", value=f"Level: {player_data['level']} - EXP: {player_data['exp']}")

        await ctx.send(embed=embed)

    @commands.command()
    async def daily(self, ctx):
        """Claim your daily reward."""
        if ctx.author.id not in self.players:
            await ctx.send("You need to start your journey with `.beginsail` first.")
            return

        player = self.players[ctx.author.id]
        now = datetime.now()
        if player["daily_login"] and now - player["daily_login"] < timedelta(days=1):
            await ctx.send("You have already claimed your daily reward. Try again tomorrow.")
            return

        player["daily_login"] = now
        day = (now - player["daily_login"]).days % len(self.daily_rewards) + 1
        reward = self.daily_rewards[day - 1]["reward"]
        if "currency" in reward:
            player["currency"] += int(reward.split()[0])
        elif "weapon" in reward:
            player["inventory"].append(random.choice(self.weapons))
        elif "devil fruit" in reward:
            player["inventory"].append(random.choice(self.devil_fruits))
        else:
            player["inventory"].append(reward)

        await ctx.send(f"You have claimed your daily reward: {reward}!")
