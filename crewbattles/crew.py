from redbot.core import commands, Config
import discord
import random
import asyncio
import aiohttp

# --- Helper Classes ---
class CrewButton(discord.ui.Button):
    def __init__(self, crew_name, crew_emoji, cog):
        super().__init__(label=f"Join {crew_name}", style=discord.ButtonStyle.primary)
        self.crew_name = crew_name
        self.crew_emoji = crew_emoji
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        crew = self.cog.crews[self.crew_name]

        if member.id in crew["members"]:
            await interaction.response.send_message("❌ You are already in this crew.", ephemeral=True)
            return

        for other_crew in self.cog.crews.values():
            if member.id in other_crew["members"]:
                await interaction.response.send_message("❌ You cannot switch crews once you join one.", ephemeral=True)
                return

        crew["members"].append(member.id)
        await member.edit(nick=f"{self.crew_emoji} {member.display_name}")
        await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`!", ephemeral=True)
        await self.cog.update_crew_message(interaction.message, self.crew_name)

class CrewView(discord.ui.View):
    def __init__(self, crew_name, crew_emoji, cog):
        super().__init__(timeout=None)
        self.add_item(CrewButton(crew_name, crew_emoji, cog))

class JoinTournamentButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Join Tournament", style=discord.ButtonStyle.primary)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        tournament = self.cog.tournaments[self.tournament_name]

        for crew in self.cog.crews.values():
            if member.id in crew["members"] and crew["name"] not in tournament["crews"]:
                tournament["crews"].append(crew["name"])
                await interaction.response.send_message(f"✅ Your crew `{crew['name']}` has joined the tournament `{self.tournament_name}`!", ephemeral=True)
                await self.cog.update_tournament_message(interaction.message, self.tournament_name)
                return

        await interaction.response.send_message("❌ You are not in any crew or your crew is already in the tournament.", ephemeral=True)

class StartTournamentButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Start Tournament", style=discord.ButtonStyle.success)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        tournament = self.cog.tournaments[self.tournament_name]
        if tournament["creator"] != interaction.user.id:
            await interaction.response.send_message("❌ Only the creator of the tournament can start it.", ephemeral=True)
            return

        if len(tournament["crews"]) < 2:
            await interaction.response.send_message("❌ Tournament needs at least 2 crews to start.", ephemeral=True)
            return

        tournament["started"] = True
        await interaction.response.send_message(f"✅ Tournament `{self.tournament_name}` has started!", ephemeral=True)
        await self.cog.run_tournament(interaction.message.channel, self.tournament_name)

class TournamentView(discord.ui.View):
    def __init__(self, tournament_name, cog):
        super().__init__(timeout=None)
        self.add_item(JoinTournamentButton(tournament_name, cog))
        self.add_item(StartTournamentButton(tournament_name, cog))

# --- Main Cog ---
class CrewTournament(commands.Cog):
    """A cog for managing crew-related tournaments."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {"crews": {}, "tournaments": {}}
        self.config.register_guild(**default_guild)
        self.crews = {}
        self.tournaments = {}
        self.active_channels = set()

    # --- Crew Commands ---
    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name="createcrew")
    async def create_crew(self, ctx: commands.Context, crew_name: str, crew_emoji: str, captain: discord.Member):
        """Create a new crew. Only admins can use this command."""
        if crew_name in self.crews:
            await ctx.send(f"❌ A crew with the name `{crew_name}` already exists.")
            return

        guild = ctx.guild
        captain_role = await guild.create_role(name=f"{crew_name} Captain")
        vice_captain_role = await guild.create_role(name=f"{crew_name} Vice Captain")

        self.crews[crew_name] = {
            "emoji": crew_emoji,
            "members": [captain.id],
            "captain_role": captain_role.id,
            "vice_captain_role": vice_captain_role.id,
        }
        await self.config.guild(ctx.guild).crews.set(self.crews)
        await captain.add_roles(captain_role)
        await ctx.send(f"✅ Crew `{crew_name}` created with {captain_role.mention} and {vice_captain_role.mention} roles.")

    async def send_crew_message(self, ctx: commands.Context, crew_name: str, crew_emoji: str):
        """Send a message with a button to join the crew."""
        embed = discord.Embed(
            title=f"Crew: {crew_name}",
            description=f"Join the crew by clicking the button below!",
            color=0x00FF00,
        )
        view = CrewView(crew_name, crew_emoji, self)
        await ctx.send(embed=embed, view=view)

    async def update_crew_message(self, message: discord.Message, crew_name: str):
        """Update the crew message with the current number of members."""
        crew = self.crews[crew_name]
        members = [message.guild.get_member(mid) for mid in crew["members"]]

        embed = discord.Embed(
            title=f"Crew: {crew_name}",
            description=f"Members: {len(members)}",
            color=0x00FF00,
        )
        embed.add_field(name="Members", value="\n".join([m.display_name for m in members if m]), inline=False)
        await message.edit(embed=embed)

    @commands.guild_only()
    @commands.command(name="viewcrew")
    async def view_crew(self, ctx: commands.Context, crew_name: str):
        """View the details of a crew."""
        if crew_name not in self.crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return

        crew = self.crews[crew_name]
        members = [ctx.guild.get_member(mid) for mid in crew["members"]]
        captain_role = ctx.guild.get_role(crew["captain_role"])
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
        captain = next((m for m in members if captain_role in m.roles), None)
        vice_captain = next((m for m in members if vice_captain_role in m.roles), None)

        embed = discord.Embed(
            title=f"Crew: {crew_name}",
            description=f"Members: {len(members)}",
            color=0x00FF00,
        )
        embed.add_field(name="Captain", value=captain.display_name if captain else "None", inline=False)
        embed.add_field(name="Vice Captain", value=vice_captain.display_name if vice_captain else "None", inline=False)
        embed.add_field(name="Members", value="\n".join([m.display_name for m in members if m not in [captain, vice_captain]]), inline=False)
        view = CrewView(crew_name, crew["emoji"], self)
        await ctx.send(embed=embed, view=view)

    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name="crews")
    async def list_crews(self, ctx: commands.Context):
        """List all available crews for users to join."""
        if not self.crews:
            await ctx.send("❌ No crews available.")
            return

        embed = discord.Embed(
            title="Available Crews",
            description="Click the button below to join a crew.",
            color=0x00FF00,
        )
        for crew_name, crew_data in self.crews.items():
            embed.add_field(name=crew_name, value=f"Emoji: {crew_data['emoji']}", inline=False)

        view = discord.ui.View()
        for crew_name, crew_data in self.crews.items():
            view.add_item(CrewButton(crew_name, crew_data["emoji"], self))

        await ctx.send(embed=embed, view=view)

    @commands.guild_only()
    @commands.command(name="assignvicecaptain")
    async def assign_vice_captain(self, ctx: commands.Context, crew_name: str, member: discord.Member):
        """Assign a vice-captain to the crew. Only the captain can use this command."""
        if crew_name not in self.crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return

        crew = self.crews[crew_name]
        captain_role = ctx.guild.get_role(crew["captain_role"])
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])

        if captain_role not in ctx.author.roles:
            await ctx.send("❌ Only the captain can assign a vice-captain.")
            return

        await member.add_roles(vice_captain_role)
        await ctx.send(f"✅ {member.display_name} has been assigned as the vice-captain of `{crew_name}`.")

    @commands.guild_only()
    @commands.command(name="kickmember")
    async def kick_member(self, ctx: commands.Context, crew_name: str, member: discord.Member):
        """Kick a member from the crew. Only the captain or vice-captain can use this command."""
        if crew_name not in self.crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return

        crew = self.crews[crew_name]
        captain_role = ctx.guild.get_role(crew["captain_role"])
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])

        if captain_role not in ctx.author.roles and vice_captain_role not in ctx.author.roles:
            await ctx.send("❌ Only the captain or vice-captain can kick members.")
            return

        if member.id not in crew["members"]:
            await ctx.send(f"❌ {member.display_name} is not a member of `{crew_name}`.")
            return

        crew["members"].remove(member.id)
        await self.config.guild(ctx.guild).crews.set(self.crews)
        await member.edit(nick=member.display_name.replace(f"{crew['emoji']} ", ""))
        await ctx.send(f"✅ {member.display_name} has been kicked from `{crew_name}`.")

    async def fetch_custom_emoji(self, emoji_url: str, guild: discord.Guild):
        """Fetch and upload a custom emoji to the guild."""
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    emoji = await guild.create_custom_emoji(name="custom_emoji", image=image_data)
                    return str(emoji)
        return None

    # --- Tournament Commands ---
    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name="createtournament")
    async def create_tournament(self, ctx: commands.Context, name: str):
        """Create a new tournament. Only admins can use this command."""
        if name in self.tournaments:
            await ctx.send(f"❌ A tournament with the name `{name}` already exists.")
            return

        self.tournaments[name] = {"creator": ctx.author.id, "crews": [], "started": False}
        await self.config.guild(ctx.guild).tournaments.set(self.tournaments)
        await self.send_tournament_message(ctx, name)

    async def send_tournament_message(self, ctx: commands.Context, name: str):
        """Send a message with buttons to join and start the tournament."""
        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {ctx.author.display_name}\nCrews: 0",
            color=0x00FF00,
        )
        view = TournamentView(name, self)
        await ctx.send(embed=embed, view=view)

    async def update_tournament_message(self, message: discord.Message, name: str):
        """Update the tournament message with the current number of crews."""
        tournament = self.tournaments[name]
        creator = message.guild.get_member(tournament["creator"])
        crews = [crew for crew in self.crews.values() if crew["name"] in tournament["crews"]]

        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {creator.display_name if creator else 'Unknown'}\nCrews: {len(crews)}",
            color=0x00FF00,
        )
        embed.add_field(name="Crews", value="\n".join([crew["name"] for crew in crews]), inline=False)
        await message.edit(embed=embed)

    @commands.guild_only()
    @commands.command(name="viewtournament")
    async def view_tournament(self, ctx: commands.Context, name: str):
        """View the details of a tournament."""
        if name not in self.tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return

        tournament = self.tournaments[name]
        creator = ctx.guild.get_member(tournament["creator"])
        crews = [crew for crew in self.crews.values() if crew["name"] in tournament["crews"]]

        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {creator.display_name if creator else 'Unknown'}\nCrews: {len(crews)}",
            color=0x00FF00,
        )
        embed.add_field(name="Crews", value="\n".join([crew["name"] for crew in crews]), inline=False)
        view = TournamentView(name, self)
        await ctx.send(embed=embed, view=view)

    @commands.admin_or_permissions(administrator=True)
    @commands.command(name="starttournament")
    async def start_tournament(self, ctx: commands.Context, name: str):
        """Start the tournament. Only the creator can use this command."""
        if name not in self.tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return

        tournament = self.tournaments[name]
        if tournament["creator"] != ctx.author.id:
            await ctx.send("❌ Only the creator of the tournament can start it.")
            return

        if len(tournament["crews"]) < 2:
            await ctx.send("❌ Tournament needs at least 2 crews to start.")
            return

        tournament["started"] = True
        await self.run_tournament(ctx.channel, name)

    async def run_tournament(self, channel: discord.TextChannel, name: str):
        """Run the tournament matches."""
        if channel.id in self.active_channels:
            await channel.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")
            return

        # Mark the channel as active
        self.active_channels.add(channel.id)

        tournament = self.tournaments[name]
        crews = [crew for crew in self.crews.values() if crew["name"] in tournament["crews"]]

        # Create initial bracket
        bracket = self.create_bracket(crews)
        tournament["bracket"] = bracket

        while len(crews) > 1:
            for match in bracket:
                crew1 = match[0]
                crew2 = match[1]
                await channel.send(f"⚔️ Match: **{crew1['name']}** vs **{crew2['name']}**")
                winner = await self.run_match(channel, crew1, crew2)
                await channel.send(f"🏆 Winner: **{winner['name']}**")
                crews.remove(crew1 if winner == crew2 else crew2)

        winner = crews[0]
        await channel.send(f"🎉 The winner of the tournament `{name}` is **{winner['name']}**!")
        del self.tournaments[name]

        # Mark the channel as inactive
        self.active_channels.remove(channel.id)

    def create_bracket(self, crews):
        """Create the initial tournament bracket."""
        random.shuffle(crews)
        bracket = []
        for i in range(0, len(crews), 2):
            match = crews[i:i + 2]
            if len(match) == 2:
                bracket.append(match)
        return bracket

    async def run_match(self, channel: discord.TextChannel, crew1, crew2):
        """Run a single match between two crews."""
        # Initialize crew data
        crew1_hp = 100
        crew2_hp = 100
        crew1_status = {"burn": 0, "stun": False}
        crew2_status = {"burn": 0, "stun": False}

        # Create the initial embed
        embed = discord.Embed(
            title="🏴‍☠️ Crew Battle ⚔️",
            description=f"Battle begins between **{crew1['name']}** and **{crew2['name']}**!",
            color=0x00FF00,
        )
        embed.add_field(
            name="Health Bars",
            value=(
                f"**{crew1['name']}:** {self.generate_health_bar(crew1_hp)} {crew1_hp}/100\n"
                f"**{crew2['name']}:** {self.generate_health_bar(crew2_hp)} {crew2_hp}/100"
            ),
            inline=False,
        )
        embed.set_footer(text="Actions are automatic!")
        message = await channel.send(embed=embed)

        # Crew data structure
        crews = [
            {"name": crew1["name"], "hp": crew1_hp, "status": crew1_status},
            {"name": crew2["name"], "hp": crew2_hp, "status": crew2_status},
        ]
        turn_index = 0

        # Battle loop
        while crews[0]["hp"] > 0 and crews[1]["hp"] > 0:
            attacker = crews[turn_index]
            defender = crews[1 - turn_index]

            # Apply burn damage
            burn_damage = await self.apply_burn_damage(defender)
            if burn_damage > 0:
                embed.description = f"🔥 **{defender['name']}** takes {burn_damage} burn damage from fire stacks!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Skip turn if stunned
            if defender["status"]["stun"]:
                defender["status"]["stun"] = False  # Stun only lasts one turn
                embed.description = f"⚡ **{defender['name']}** is stunned and cannot act!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)
                turn_index = 1 - turn_index
                continue

            # Select move
            move = random.choice(MOVES)
            damage = self.calculate_damage(move["type"])
            await self.apply_effects(move, attacker, defender)

            # Apply damage
            defender["hp"] = max(0, defender["hp"] - damage)
            embed.description = (
                f"**{attacker['name']}** used **{move['name']}**: {move['description']} "
                f"and dealt **{damage}** damage to **{defender['name']}**!"
            )
            embed.set_field_at(
                0,
                name="Health Bars",
                value=(
                    f"**{crews[0]['name']}:** {self.generate_health_bar(crews[0]['hp'])} {crews[0]['hp']}/100\n"
                    f"**{crews[1]['name']}:** {self.generate_health_bar(crews[1]['hp'])} {crews[1]['hp']}/100"
                ),
                inline=False,
            )
            await message.edit(embed=embed)
            await asyncio.sleep(2)
            turn_index = 1 - turn_index

        # Determine winner
        winner = crews[0] if crews[0]["hp"] > 0 else crews[1]
        return winner

    async def apply_burn_damage(self, crew):
        """Apply burn damage to a crew if they have burn stacks."""
        if crew["status"]["burn"] > 0:
            burn_damage = 5 * crew["status"]["burn"]
            crew["hp"] = max(0, crew["hp"] - burn_damage)
            crew["status"]["burn"] -= 1
            return burn_damage
        return 0

    def calculate_damage(self, move_type: str, crit_chance: float = 0.2) -> int:
        """Calculate balanced damage for each move type."""
        base_damage = 0

        if move_type == "regular":
            base_damage = random.randint(5, 10)
        elif move_type == "strong":
            base_damage = random.randint(10, 20)
        elif move_type == "critical":
            base_damage = random.randint(15, 25)

            # Apply critical hit chance
            if random.random() < crit_chance:
                base_damage *= 2

        return base_damage

    async def apply_effects(self, move: dict, attacker: dict, defender: dict):
        """Apply special effects like burn, heal, stun, or crit."""
        effect = move.get("effect")
        if effect == "burn":
            if random.random() < move.get("burn_chance", 0):
                defender["status"]["burn"] += 1
                defender["status"]["burn"] = min(defender["status"]["burn"], 3)  # Cap burn stacks at 3
        elif effect == "stun":
            defender["status"]["stun"] = True
