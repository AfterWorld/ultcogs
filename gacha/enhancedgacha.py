from redbot.core import commands, Config, bank
from redbot.core.utils.chat_formatting import humanize_timedelta
from redbot.core.bot import Red
import discord
from discord import app_commands
from discord.ext import tasks
import random
import asyncio
from datetime import datetime, timedelta
import aiohttp
from io import BytesIO

class EnhancedGacha(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3498299999912, force_registration=True)
        
        default_guild = {
            "characters": {},
            "maxscrollbeforecd": 10,
            "cooldown": 3600,
            "pity_threshold": 50,
            "spawn_rates": {"common": 70, "rare": 25, "epic": 5},
            "roll_cost": 100
        }
        default_member = {
            "haremname": None,
            "marriedto": [],
            "scrolled": 0,
            "cooldownspawn": None,
            "pity_counter": 0
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.reset.start()

    def cog_unload(self):
        self.reset.cancel()

    @tasks.loop(seconds=60)
    async def reset(self):
        all_members = await self.config.all_members()
        for guild_id, guild_data in all_members.items():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            for member_id, member_data in guild_data.items():
                if not member_data["cooldownspawn"]:
                    continue
                if member_data["cooldownspawn"] < datetime.utcnow().timestamp():
                    member = guild.get_member(member_id)
                    if not member:
                        continue
                    await self.config.member(member).scrolled.set(0)
                    await self.config.member(member).cooldownspawn.clear()
                    
    async def _valid_image_url(self, url: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        return False
                    if 'image' not in r.headers.get('Content-Type', ''):
                        return False
                    return True
        except aiohttp.ClientError:
            return False

    @commands.guild_only()
    @commands.hybrid_command(name="gachas")
    async def gachas(self, ctx: commands.Context, page: int = 1):
        """Lists all available characters."""
        characters = await self.config.guild(ctx.guild).characters()
        if not characters:
            return await ctx.send("There are no characters in the database.")

        sorted_chars = sorted(characters.items(), key=lambda x: x[0])
        pages = [sorted_chars[i:i+10] for i in range(0, len(sorted_chars), 10)]

        if page < 1 or page > len(pages):
            return await ctx.send(f"Invalid page number. Please choose between 1 and {len(pages)}.")

        embed = discord.Embed(title="Gacha Characters", color=discord.Color.blue())
        for name, data in pages[page-1]:
            rarity = data.get('rarity', 'Unknown')
            owner = ctx.guild.get_member(data['marriedto']) if data['marriedto'] else None
            embed.add_field(name=f"{name} ({rarity})", value=f"Owned by: {owner.mention if owner else 'None'}", inline=False)

        embed.set_footer(text=f"Page {page}/{len(pages)}")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Previous", style=discord.ButtonStyle.gray, custom_id="prev"))
        view.add_item(discord.ui.Button(label="Next", style=discord.ButtonStyle.gray, custom_id="next"))

        message = await ctx.send(embed=embed, view=view)

        def check(interaction):
            return interaction.message.id == message.id and interaction.user.id == ctx.author.id

        while True:
            try:
                interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                if interaction.data["custom_id"] == "prev":
                    page = max(1, page - 1)
                elif interaction.data["custom_id"] == "next":
                    page = min(len(pages), page + 1)

                embed.clear_fields()
                for name, data in pages[page-1]:
                    rarity = data.get('rarity', 'Unknown')
                    owner = ctx.guild.get_member(data['marriedto']) if data['marriedto'] else None
                    embed.add_field(name=f"{name} ({rarity})", value=f"Owned by: {owner.mention if owner else 'None'}", inline=False)
                embed.set_footer(text=f"Page {page}/{len(pages)}")

                await interaction.response.edit_message(embed=embed)
            except asyncio.TimeoutError:
                await message.edit(view=None)
                break

    @commands.guild_only()
    @commands.hybrid_command(name="roll")
    @app_commands.describe(option="Choose 'M' for male, 'F' for female, or a franchise option like 'opf', 'opm', 'op'")
    async def groll(self, ctx: commands.Context, option: str):
        """Roll for a character. Costs currency to use. Use 'opf' for One Piece female, 'opm' for One Piece male, 'op' for any One Piece character."""
        option = option.lower()
        if option not in ['m', 'f', 'opf', 'opm', 'op']:
            return await ctx.send("Invalid option. Please choose 'M', 'F', 'opf', 'opm', or 'op'.")

        roll_cost = await self.config.guild(ctx.guild).roll_cost()
        if not await bank.can_spend(ctx.author, roll_cost):
            return await ctx.send(f"You need {roll_cost} {await bank.get_currency_name(ctx.guild)} to roll.")

        await bank.withdraw_credits(ctx.author, roll_cost)

        characters = await self.config.guild(ctx.guild).characters()
        
        if option in ['opf', 'opm', 'op']:
            franchise = "One Piece"
            gender = 'F' if option == 'opf' else 'M' if option == 'opm' else random.choice(['M', 'F'])
            eligible_chars = [char for char in characters.items() if char[1]['gender'] == gender and char[1].get('franchise') == franchise]
        else:
            eligible_chars = [char for char in characters.items() if char[1]['gender'] == option.upper()]

        if not eligible_chars:
            await bank.deposit_credits(ctx.author, roll_cost)  # Refund if no eligible characters
            return await ctx.send(f"There are no characters available for the chosen option.")

        spawn_rates = await self.config.guild(ctx.guild).spawn_rates()
        rarity = random.choices(list(spawn_rates.keys()), weights=list(spawn_rates.values()))[0]

        pity_counter = await self.config.member(ctx.author).pity_counter()
        pity_threshold = await self.config.guild(ctx.guild).pity_threshold()

        if pity_counter >= pity_threshold:
            rarity = "epic"  # Guaranteed epic on pity
            await self.config.member(ctx.author).pity_counter.set(0)
        else:
            await self.config.member(ctx.author).pity_counter.set(pity_counter + 1)

        eligible_chars_rarity = [char for char in eligible_chars if char[1].get('rarity', 'common') == rarity]
        if not eligible_chars_rarity:
            eligible_chars_rarity = eligible_chars  # Fallback to all characters if none of the chosen rarity

        char_name, char_data = random.choice(eligible_chars_rarity)

        embed = discord.Embed(title=f"You rolled: {char_name}", color=discord.Color.gold())
        embed.add_field(name="Rarity", value=rarity.capitalize())
        embed.add_field(name="Gender", value=gender.upper())
        embed.set_image(url=char_data['url'])

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim"))

        message = await ctx.send(embed=embed, view=view)

        def check(interaction):
            return interaction.message.id == message.id and interaction.user.id == ctx.author.id

        try:
            interaction = await self.bot.wait_for("interaction", timeout=30.0, check=check)
            if interaction.data["custom_id"] == "claim":
                await self.claim_character(ctx, char_name, ctx.author)
                await interaction.response.send_message(f"You've successfully claimed {char_name}!")
        except asyncio.TimeoutError:
            await message.edit(view=None)
            await ctx.send("You didn't claim the character in time.")

    async def claim_character(self, ctx, char_name, user):
        async with self.config.guild(ctx.guild).characters() as characters:
            if char_name in characters and characters[char_name]['marriedto'] is None:
                characters[char_name]['marriedto'] = user.id
                async with self.config.member(user).marriedto() as marriedto:
                    marriedto.append(char_name)
                return True
        return False

    @commands.guild_only()
    @commands.command(aliases=["glb"])
    async def gleaderboard(self, ctx):
        """Get the leaderboard for card owners."""
        data = await self.config.all_members(ctx.guild)
        em = discord.Embed()

        if not data:
            return await ctx.send("None of the members own a card yet.")

        sort = sorted(data.items(), key=lambda x: len(x[1]["marriedto"]), reverse=True)
        msg = ""
        for x in sort:
            member = ctx.guild.get_member(x[0])
            if member:
                msg += f"\n{member.mention} - `{len(x[1]['marriedto'])}` cards"

        em.set_author(
            name=f"Cards leaderboard for {ctx.guild}", icon_url=ctx.guild.icon_url
        )
        em.description = msg
        await ctx.send(embed=em)

    @commands.command()
    @commands.guild_only()
    async def grename(self, ctx, *, name: str):
        """Rename your harem name."""
        await self.config.member(ctx.author).haremname.set(name)
        em = discord.Embed()
        em.description = (
            f"{ctx.author.mention} your harem name has been changed to {name}"
        )
        await ctx.send(embed=em)

    @commands.guild_only()
    @commands.command(name="glt")
    async def _list(self, ctx, member: discord.Member = None):
        """Get your harem."""
        member = ctx.author if not member else member
        em = discord.Embed()
        data = await self.config.member(member).marriedto()
        name = await self.config.member(member).haremname()
        if not data:
            return await ctx.send(f"{member} has no cards yet.")

        if member.bot:
            return await ctx.send("Bot can't get cards.")

        n = "\n"
        em.set_author(name=f"{name if name else member}", icon_url=member.avatar_url)
        em.description = f"{n.join([x for x in data])}"
        await ctx.send(embed=em)

    @commands.guild_only()
    @commands.command(name="gadd")
    @commands.has_permissions(manage_guild=True)
    async def gadd(self, ctx: commands.Context, name: str, gender: str, rarity: str, franchise: str, imgurl: str):
        """Add a new character to the database."""
        if gender.upper() not in ['M', 'F']:
            return await ctx.send("Invalid gender. Please use 'M' for male or 'F' for female.")

        if rarity.lower() not in ['common', 'rare', 'epic']:
            return await ctx.send("Invalid rarity. Please use 'common', 'rare', or 'epic'.")

        if not await self._valid_image_url(imgurl):
            return await ctx.send("Invalid image URL. Please provide a direct link to an image.")

        async with self.config.guild(ctx.guild).characters() as characters:
            if name in characters:
                return await ctx.send(f"{name} already exists in the database.")

            characters[name] = {
                "url": imgurl,
                "marriedto": None,
                "gender": gender.upper(),
                "rarity": rarity.lower(),
                "franchise": franchise
            }

        await ctx.send(f"{name} has been added to the database as a {rarity} {gender} character from {franchise}.")

    @commands.guild_only()
    @commands.hybrid_command(name="gprofile")
    async def gprofile(self, ctx: commands.Context, member: discord.Member = None):
        """View your or another member's gacha profile."""
        member = member or ctx.author
        data = await self.config.member(member).all()

        embed = discord.Embed(title=f"{member.display_name}'s Gacha Profile", color=member.color)
        embed.set_thumbnail(url=member.avatar.url)

        harem_name = data['haremname'] or "Not set"
        embed.add_field(name="Harem Name", value=harem_name, inline=False)

        characters = data['marriedto']
        char_count = len(characters)
        embed.add_field(name="Characters Owned", value=str(char_count), inline=True)

        pity_counter = data['pity_counter']
        pity_threshold = await self.config.guild(ctx.guild).pity_threshold()
        embed.add_field(name="Pity Counter", value=f"{pity_counter}/{pity_threshold}", inline=True)

        if char_count > 0:
            char_list = "\n".join(characters[:5])  # Show first 5 characters
            if char_count > 5:
                char_list += f"\n... and {char_count - 5} more"
            embed.add_field(name="Some Characters", value=char_list, inline=False)

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.hybrid_command(name="gconfig")
    @commands.has_permissions(manage_guild=True)
    async def gconfig(self, ctx: commands.Context):
        """Configure gacha settings."""
        embed = discord.Embed(title="Gacha Configuration", color=discord.Color.blue())
        guild_config = await self.config.guild(ctx.guild).all()

        embed.add_field(name="Max Scrolls Before Cooldown", value=guild_config['maxscrollbeforecd'], inline=True)
        embed.add_field(name="Cooldown (seconds)", value=guild_config['cooldown'], inline=True)
        embed.add_field(name="Pity Threshold", value=guild_config['pity_threshold'], inline=True)
        embed.add_field(name="Roll Cost", value=guild_config['roll_cost'], inline=True)

        spawn_rates = guild_config['spawn_rates']
        rates_str = "\n".join(f"{rarity}: {rate}%" for rarity, rate in spawn_rates.items())
        embed.add_field(name="Spawn Rates", value=rates_str, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Edit Max Scrolls", style=discord.ButtonStyle.gray, custom_id="edit_scrolls"))
        view.add_item(discord.ui.Button(label="Edit Cooldown", style=discord.ButtonStyle.gray, custom_id="edit_cooldown"))
        view.add_item(discord.ui.Button(label="Edit Pity", style=discord.ButtonStyle.gray, custom_id="edit_pity"))
        view.add_item(discord.ui.Button(label="Edit Roll Cost", style=discord.ButtonStyle.gray, custom_id="edit_cost"))
        view.add_item(discord.ui.Button(label="Edit Spawn Rates", style=discord.ButtonStyle.gray, custom_id="edit_rates"))

        message = await ctx.send(embed=embed, view=view)

        def check(interaction):
            return interaction.message.id == message.id and interaction.user.id == ctx.author.id

        while True:
            try:
                interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                await self.handle_config_interaction(interaction, ctx.guild)
            except asyncio.TimeoutError:
                await message.edit(view=None)
                break

    async def handle_config_interaction(self, interaction, guild):
        if interaction.data["custom_id"] == "edit_scrolls":
            await interaction.response.send_message("Enter the new max scrolls before cooldown:")
            msg = await self.bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            try:
                new_value = int(msg.content)
                await self.config.guild(guild).maxscrollbeforecd.set(new_value)
                await interaction.followup.send(f"Max scrolls before cooldown set to {new_value}")
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter a number.")

        elif interaction.data["custom_id"] == "edit_cooldown":
            await interaction.response.send_message("Enter the new cooldown in seconds:")
            msg = await self.bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            try:
                new_value = int(msg.content)
                await self.config.guild(guild).cooldown.set(new_value)
                await interaction.followup.send(f"Cooldown set to {new_value} seconds")
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter a number.")

        elif interaction.data["custom_id"] == "edit_pity":
            await interaction.response.send_message("Enter the new pity threshold:")
            msg = await self.bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            try:
                new_value = int(msg.content)
                await self.config.guild(guild).pity_threshold.set(new_value)
                await interaction.followup.send(f"Pity threshold set to {new_value}")
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter a number.")

        elif interaction.data["custom_id"] == "edit_cost":
            await interaction.response.send_message("Enter the new roll cost:")
            msg = await self.bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            try:
                new_value = int(msg.content)
                await self.config.guild(guild).roll_cost.set(new_value)
                await interaction.followup.send(f"Roll cost set to {new_value}")
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter a number.")

        elif interaction.data["custom_id"] == "edit_rates":
            await interaction.response.send_message("Enter the new spawn rates (format: common,rare,epic):")
            msg = await self.bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            try:
                rates = [int(x) for x in msg.content.split(',')]
                if len(rates) != 3 or sum(rates) != 100:
                    raise ValueError
                new_rates = {"common": rates[0], "rare": rates[1], "epic": rates[2]}
                await self.config.guild(guild).spawn_rates.set(new_rates)
                await interaction.followup.send(f"Spawn rates updated to: {new_rates}")
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter three comma-separated numbers that sum to 100.")

    @commands.guild_only()
    @commands.hybrid_command(name="gexchange")
    async def gexchange(self, ctx: commands.Context, member: discord.Member, your_card: str, their_card: str):
        """Propose a card exchange with another member."""
        if member == ctx.author:
            return await ctx.send("You can't exchange cards with yourself.")

        your_cards = await self.config.member(ctx.author).marriedto()
        their_cards = await self.config.member(member).marriedto()

        if your_card not in your_cards:
            return await ctx.send(f"You don't own the card '{your_card}'.")
        if their_card not in their_cards:
            return await ctx.send(f"{member.display_name} doesn't own the card '{their_card}'.")

        embed = discord.Embed(title="Card Exchange Proposal", color=discord.Color.blue())
        embed.add_field(name=f"{ctx.author.display_name} offers", value=your_card, inline=True)
        embed.add_field(name=f"{member.display_name} offers", value=their_card, inline=True)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept"))
        view.add_item(discord.ui.Button(label="Decline", style=discord.ButtonStyle.red, custom_id="decline"))

        message = await ctx.send(f"{member.mention}, {ctx.author.display_name} proposes a card exchange:", embed=embed, view=view)

        def check(interaction):
            return interaction.message.id == message.id and interaction.user.id == member.id

        try:
            interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
            if interaction.data["custom_id"] == "accept":
                await self.exchange_cards(ctx.author, member, your_card, their_card)
                await interaction.response.send_message("Exchange completed successfully!")
            else:
                await interaction.response.send_message("Exchange declined.")
        except asyncio.TimeoutError:
            await message.edit(view=None)
            await ctx.send("The exchange offer has expired.")

    async def exchange_cards(self, user1, user2, card1, card2):
        async with self.config.member(user1).marriedto() as user1_cards:
            user1_cards.remove(card1)
            user1_cards.append(card2)

        async with self.config.member(user2).marriedto() as user2_cards:
            user2_cards.remove(card2)
            user2_cards.append(card1)

        async with self.config.guild(user1.guild).characters() as characters:
            characters[card1]['marriedto'] = user2.id
            characters[card2]['marriedto'] = user1.id

    @commands.guild_only()
    @commands.hybrid_command(name="gevent")
    @commands.has_permissions(manage_guild=True)
    async def gevent(self, ctx: commands.Context, duration: int, bonus_rate: int):
        """Start a gacha event with increased epic drop rates."""
        if bonus_rate < 1 or bonus_rate > 100:
            return await ctx.send("Bonus rate must be between 1 and 100.")

        async with self.config.guild(ctx.guild).spawn_rates() as rates:
            original_rates = rates.copy()
            rates['epic'] = min(rates['epic'] + bonus_rate, 100)
            rates['rare'] = max(rates['rare'] - bonus_rate // 2, 0)
            rates['common'] = 100 - rates['epic'] - rates['rare']

        embed = discord.Embed(title="Gacha Event Started!", color=discord.Color.gold())
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
        embed.add_field(name="New Rates", value="\n".join(f"{k}: {v}%" for k, v in rates.items()), inline=False)

        await ctx.send(embed=embed)

        await asyncio.sleep(duration * 60)

        await self.config.guild(ctx.guild).spawn_rates.set(original_rates)
        await ctx.send("The gacha event has ended. Rates have returned to normal.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the necessary permissions to use this command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument: {str(error)}")
        else:
            await ctx.send(f"An error occurred: {str(error)}")

def setup(bot):
    bot.add_cog(EnhancedGacha(bot))
