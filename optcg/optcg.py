import discord
import asyncio
import random
import aiohttp
import logging
import io
from datetime import datetime
from typing import Dict, List, Optional, Union
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.predicates import MessagePredicate

from .utils import create_silhouette, get_card_stats
from .battle import BattleSystem

log = logging.getLogger("red.optcg")

class OPTCG(commands.Cog):
    """One Piece Trading Card Game Cog - Collect cards and battle!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=20240508, force_registration=True)
        
        # Default settings
        default_global = {
            "spawn_chance": 0.15,  # Chance of spawning a card after each message (15%)
            "spawn_cooldown": 60,  # Cooldown in seconds between card spawns
            "last_spawn_time": 0,  # Timestamp of the last spawn
            "api_url": "https://apitcg.com/api/one-piece/cards"
        }
        
        default_guild = {
            "enabled": True,
            "spawn_channel": None,
            "active_card": None  # Currently active card that can be claimed
        }
        
        default_user = {
            "cards": [],           # List of card IDs
            "card_details": {},    # Dict mapping card IDs to details
            "claimed_starter": False
        }
        
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        
        self.spawn_lock = asyncio.Lock()
        self.session = aiohttp.ClientSession()
        
        # Initialize battle system
        self.battle_system = BattleSystem(bot, self.config)
    
    async def cog_load(self):
        # Initialize battle system
        await self.battle_system.initialize()
    
    def cog_unload(self):
        asyncio.create_task(self.session.close())
    
    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's data when they leave the guild."""
        await self.config.user_from_id(user_id).clear()
    
    async def fetch_random_card(self) -> Optional[Dict]:
        """Fetch a random card from the API."""
        try:
            # Try multiple pages to increase chances of success
            for _ in range(3):  # Try up to 3 different random pages
                page = random.randint(1, 20)
                async with self.session.get(
                    await self.config.api_url(),
                    params={"limit": 10, "page": page}
                ) as resp:
                    if resp.status != 200:
                        log.error(f"API request failed with status {resp.status}")
                        continue
                    
                    data = await resp.json()
                    cards = data.get("data", [])
                    if cards:
                        return random.choice(cards)
            
            # Fallback: try with a simpler request for any card
            async with self.session.get(
                await self.config.api_url(),
                params={"limit": 1}
            ) as resp:
                if resp.status != 200:
                    log.error(f"API request failed with status {resp.status}")
                    return None
                
                data = await resp.json()
                cards = data.get("data", [])
                if cards:
                    return cards[0]
                return None
        
        except Exception as e:
            log.error(f"Error fetching card from API: {e}")
            return None
    
    async def fetch_card_by_name(self, name: str) -> List[Dict]:
        """Fetch cards with the given name from the API."""
        try:
            async with self.session.get(
                await self.config.api_url(),
                params={"name": name}
            ) as resp:
                if resp.status != 200:
                    log.error(f"API request failed with status {resp.status}")
                    return []
                
                data = await resp.json()
                return data.get("data", [])
        
        except Exception as e:
            log.error(f"Error fetching card by name from API: {e}")
            return []
    
    async def spawn_card(self, guild: discord.Guild) -> Optional[discord.Message]:
        """Spawn a card in the guild's designated channel."""
        try:
            if await self.config.guild(guild).enabled() is False:
                log.debug(f"OPTCG is disabled in guild {guild.id}")
                return None
            
            spawn_channel_id = await self.config.guild(guild).spawn_channel()
            if not spawn_channel_id:
                log.debug(f"No spawn channel configured for guild {guild.id}")
                return None
            
            spawn_channel = guild.get_channel(spawn_channel_id)
            if not spawn_channel:
                log.debug(f"Could not find channel {spawn_channel_id} in guild {guild.id}")
                return None
            
            # Check permissions
            bot_member = guild.me
            permissions = spawn_channel.permissions_for(bot_member)
            
            if not permissions.send_messages:
                log.debug(f"Bot doesn't have permission to send messages in channel {spawn_channel_id}")
                return None
            
            if not permissions.embed_links:
                log.debug(f"Bot doesn't have permission to embed links in channel {spawn_channel_id}")
                return None
            
            if not permissions.attach_files:
                log.debug(f"Bot doesn't have permission to attach files in channel {spawn_channel_id}")
                # We'll continue but won't use file attachments
            
            log.debug(f"Fetching random card for guild {guild.id}")
            card = await self.fetch_random_card()
            if not card:
                log.error(f"Failed to fetch a random card for guild {guild.id}")
                return None
            
            log.debug(f"Storing active card for guild {guild.id}")
            await self.config.guild(guild).active_card.set(card)
            
            # Create embed
            embed = discord.Embed(
                title="A Wild One Piece Card Appears!",
                description="Use the button below or type `.optcg claim` to claim this card!",
                color=discord.Color.dark_gold()
            )
            
            use_file = False
            file = None
            
            # Create a silhouette of the card image if we have permissions
            if permissions.attach_files:
                try:
                    silhouette_image = await create_silhouette(self.session, card["images"]["large"])
                    if silhouette_image:
                        # If we successfully created a silhouette
                        file = discord.File(silhouette_image, filename="silhouette.png")
                        embed.set_image(url="attachment://silhouette.png")
                        use_file = True
                    else:
                        # Fall back to regular image if silhouette creation fails
                        embed.set_image(url=card["images"]["large"])
                except Exception as e:
                    log.error(f"Error creating silhouette: {e}")
                    embed.set_image(url=card["images"]["large"])
            else:
                embed.set_image(url=card["images"]["large"])
            
            # Check if we can use message components (buttons)
            if hasattr(discord, "ui") and hasattr(discord.ui, "Button"):
                # Create a button for claiming
                claim_button = discord.ui.Button(label="Claim Card", style=discord.ButtonStyle.primary)
                
                async def claim_callback(interaction: discord.Interaction):
                    await self.claim_card(interaction.user, guild, interaction.message)
                    
                claim_button.callback = claim_callback
                
                view = discord.ui.View()
                view.add_item(claim_button)
            else:
                view = None
                embed.description += "\n\nNote: Use `.optcg claim` to claim this card!"
            
            try:
                log.debug(f"Sending card spawn message to channel {spawn_channel_id}")
                if use_file:
                    message = await spawn_channel.send(embed=embed, file=file, view=view)
                else:
                    message = await spawn_channel.send(embed=embed, view=view)
                return message
            except Exception as e:
                log.error(f"Error spawning card: {e}")
                return None
                
        except Exception as e:
            log.error(f"Unexpected error in spawn_card: {e}")
            return None
    
    async def claim_card(self, user: discord.User, guild: discord.Guild, message: Optional[discord.Message] = None):
        """Claim the active card in the guild."""
        active_card = await self.config.guild(guild).active_card()
        if not active_card:
            if message:
                await message.edit(content="There's no card to claim right now!", view=None)
            return
        
        async with self.config.user(user).all() as user_data:
            cards = user_data["cards"]
            card_details = user_data["card_details"]
            
            # Add card to user's collection
            cards.append(active_card["id"])
            card_details[active_card["id"]] = active_card
        
        # Clear active card
        await self.config.guild(guild).active_card.set(None)
        
        # Create a new embed showing the card was claimed
        embed = discord.Embed(
            title=f"Card Claimed by {user.display_name}!",
            description=f"**{active_card['name']}** has been added to your collection.",
            color=discord.Color.green()
        )
        embed.set_image(url=active_card["images"]["large"])
        embed.add_field(name="Rarity", value=active_card["rarity"])
        embed.add_field(name="Type", value=active_card["type"])
        embed.add_field(name="Color", value=active_card["color"])
        embed.add_field(name="Power", value=str(active_card["power"]))
        
        if message:
            await message.edit(embed=embed, view=None)
    
    @commands.group(name="optcg")
    async def optcg(self, ctx: commands.Context):
        """Commands for the One Piece TCG Game."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            
    #
    # Battle related commands
    #
            
    @optcg.command(name="deck")
    async def set_battle_deck(self, ctx: commands.Context, *card_ids: str):
        """Set your battle deck with up to 5 cards from your collection.
        
        Example:
        `.optcg deck OP01-001 OP01-002 OP01-003`
        """
        if not card_ids:
            await ctx.send("Please specify at least one card ID to add to your battle deck.")
            return
            
        if len(card_ids) > 5:
            await ctx.send("You can only have up to 5 cards in your battle deck.")
            return
            
        success = await self.battle_system.set_battle_deck(ctx.author, list(card_ids))
            
        if success:
            await ctx.send(f"Battle deck updated with {len(card_ids)} cards!")
        else:
            await ctx.send("Failed to update battle deck. Make sure all card IDs are from your collection.")
            
    @optcg.command(name="battle")
    async def battle_command(self, ctx: commands.Context, opponent: discord.Member):
        """Challenge another user to a battle with your deck."""
        if opponent.bot:
            await ctx.send("You can't battle against bots!")
            return
            
        if opponent == ctx.author:
            await ctx.send("You can't battle against yourself!")
            return
            
        # Start the battle
        await self.battle_system.create_battle(ctx, ctx.author, opponent)
            
    @optcg.command(name="stats")
    async def battle_stats(self, ctx: commands.Context, user: discord.Member = None):
        """View your battle statistics or another user's."""
        target = user or ctx.author
        wins, losses = await self.battle_system.get_user_battle_stats(target)
        total = wins + losses
            
        # Calculate win rate
        win_rate = (wins / total) * 100 if total > 0 else 0
            
        embed = discord.Embed(
            title=f"{target.display_name}'s Battle Statistics",
            color=discord.Color.blue()
        )
            
        embed.add_field(name="Wins", value=str(wins), inline=True)
        embed.add_field(name="Losses", value=str(losses), inline=True)
        embed.add_field(name="Total Battles", value=str(total), inline=True)
        embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
            
        await ctx.send(embed=embed)
        
    @optcg.command(name="viewdeck")
    async def view_deck(self, ctx: commands.Context, user: discord.Member = None):
        """View your battle deck or another user's."""
        target = user or ctx.author
        user_data = await self.config.user(target).all()
        
        if not user_data.get("battle_deck"):
            if target == ctx.author:
                await ctx.send("You don't have a battle deck set up! Use `.optcg deck` to set one up.")
            else:
                await ctx.send(f"{target.display_name} doesn't have a battle deck set up!")
            return
        
        embed = discord.Embed(
            title=f"{target.display_name}'s Battle Deck",
            description=f"{len(user_data['battle_deck'])} cards",
            color=discord.Color.blue()
        )
        
        for card_id in user_data["battle_deck"]:
            if card_id in user_data["card_details"]:
                card = user_data["card_details"][card_id]
                stats = user_data.get("battle_stats", {}).get(card_id, (0, 0, 0))
                
                embed.add_field(
                    name=f"{card['name']} ({card['rarity']})",
                    value=f"ID: {card['id']}\nType: {card['type']}\nPower: {card['power']}\n"
                         f"Battle Stats: {stats[0]} ATK | {stats[1]} DEF | {stats[2]} HP",
                    inline=True
                )
        
        await ctx.send(embed=embed)
    
    @optcg.group(name="admin")
    @commands.admin_or_permissions(administrator=True)
    async def optcg_admin(self, ctx: commands.Context):
        """Admin commands for OPTCG configuration."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @optcg_admin.command(name="spawnrate")
    async def set_spawn_rate(self, ctx: commands.Context, rate: float):
        """Set the chance for a card to spawn (0.0 - 1.0).
        
        Example:
        `.optcg admin spawnrate 0.15` - Sets a 15% chance to spawn a card
        """
        if rate < 0 or rate > 1:
            await ctx.send("Spawn rate must be between 0.0 (0%) and 1.0 (100%).")
            return
        
        await self.config.spawn_chance.set(rate)
        await ctx.send(f"Card spawn rate set to {rate * 100:.1f}%")
    
    @optcg_admin.command(name="cooldown")
    async def set_cooldown(self, ctx: commands.Context, seconds: int):
        """Set the cooldown between card spawns in seconds.
        
        Example:
        `.optcg admin cooldown 60` - Sets a 60 second cooldown between spawns
        """
        if seconds < 0:
            await ctx.send("Cooldown must be a positive number of seconds.")
            return
        
        await self.config.spawn_cooldown.set(seconds)
        await ctx.send(f"Card spawn cooldown set to {seconds} seconds")
        
    @optcg_admin.command(name="reset")
    async def reset_user(self, ctx: commands.Context, user: discord.Member):
        """Reset a user's OPTCG data (admin only).
        
        This will delete all cards and reset stats. Use with caution!
        """
        await ctx.send(f"Are you sure you want to reset **{user.display_name}**'s OPTCG data? This will delete all their cards and cannot be undone. Type 'yes' to confirm.")
        
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Reset canceled due to timeout.")
            return
            
        if pred.result:
            await self.config.user(user).clear()
            await ctx.send(f"**{user.display_name}**'s OPTCG data has been reset!")
        else:
            await ctx.send("Reset canceled.")
            
    @optcg_admin.command(name="debug")
    async def debug_info(self, ctx: commands.Context):
        """Display debugging information for OPTCG setup."""
        guild = ctx.guild
        embed = discord.Embed(
            title="OPTCG Debug Information",
            description="Here's the current setup information to help diagnose issues.",
            color=discord.Color.blue()
        )
        
        # Guild Settings
        enabled = await self.config.guild(guild).enabled()
        spawn_channel_id = await self.config.guild(guild).spawn_channel()
        spawn_channel = guild.get_channel(spawn_channel_id) if spawn_channel_id else None
        
        embed.add_field(
            name="Guild Settings",
            value=f"Enabled: {enabled}\n"
                  f"Spawn Channel: {spawn_channel.mention if spawn_channel else 'Not Set'}\n"
                  f"Spawn Channel ID: {spawn_channel_id}",
            inline=False
        )
        
        # Global Settings
        spawn_chance = await self.config.spawn_chance()
        spawn_cooldown = await self.config.spawn_cooldown()
        last_spawn_time = await self.config.last_spawn_time()
        current_time = int(datetime.now().timestamp())
        time_since_last = current_time - last_spawn_time if last_spawn_time else 0
        
        embed.add_field(
            name="Global Settings",
            value=f"Spawn Chance: {spawn_chance * 100}%\n"
                  f"Spawn Cooldown: {spawn_cooldown} seconds\n"
                  f"Time Since Last Spawn: {time_since_last} seconds",
            inline=False
        )
        
        # Bot Permissions
        if spawn_channel:
            perms = spawn_channel.permissions_for(guild.me)
            
            perm_list = [
                f"Send Messages: {perms.send_messages}",
                f"Embed Links: {perms.embed_links}",
                f"Attach Files: {perms.attach_files}",
                f"Use External Emojis: {perms.use_external_emojis}",
                f"Add Reactions: {perms.add_reactions}",
                f"Read Message History: {perms.read_message_history}"
            ]
            
            embed.add_field(
                name="Bot Permissions in Spawn Channel",
                value="\n".join(perm_list),
                inline=False
            )
        
        # API Connection Test
        try:
            async with self.session.get(await self.config.api_url()) as resp:
                api_status = f"Status Code: {resp.status}"
                if resp.status == 200:
                    data = await resp.json()
                    api_status += f"\nCards Available: {data.get('total', 'Unknown')}"
        except Exception as e:
            api_status = f"Error: {str(e)}"
        
        embed.add_field(
            name="API Connection",
            value=api_status,
            inline=False
        )
        
        # Card Silhouette Testing
        try:
            test_url = "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-001.png"
            silhouette_result = "Not Tested"
            
            async with self.session.get(test_url) as resp:
                if resp.status == 200:
                    silhouette_result = "Image Fetch: Success\n"
                    try:
                        silhouette = await create_silhouette(self.session, test_url)
                        if silhouette:
                            silhouette_result += "Silhouette Creation: Success"
                        else:
                            silhouette_result += "Silhouette Creation: Failed"
                    except Exception as e:
                        silhouette_result += f"Silhouette Creation: Error ({str(e)})"
                else:
                    silhouette_result = f"Image Fetch: Failed (Status {resp.status})"
        except Exception as e:
            silhouette_result = f"Error: {str(e)}"
        
        embed.add_field(
            name="Silhouette Testing",
            value=silhouette_result,
            inline=False
        )
        
        # Cog Version Info
        embed.add_field(
            name="Cog Information",
            value="Version: 1.0.1\n"  # Bumped to version 1.0.1 with these fixes
                  "Last Updated: May 8, 2024",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @optcg_admin.command(name="apiurl")
    async def set_api_url(self, ctx: commands.Context, new_url: str = None):
        """View or set the API URL for fetching card data.
        
        If no URL is provided, shows the current API URL.
        
        Example:
        `.optcg admin apiurl https://apitcg.com/api/one-piece/cards`
        """
        if new_url is None:
            current_url = await self.config.api_url()
            await ctx.send(f"Current API URL: `{current_url}`")
            return
        
        # Test the new URL
        try:
            async with self.session.get(new_url) as resp:
                if resp.status != 200:
                    await ctx.send(f"Warning: Received status code {resp.status} when testing the new URL. Are you sure this is correct?")
                    await ctx.send("Do you want to set this URL anyway? (yes/no)")
                    
                    try:
                        pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                        await ctx.bot.wait_for("message", check=pred, timeout=30)
                        if not pred.result:
                            await ctx.send("API URL update canceled.")
                            return
                    except asyncio.TimeoutError:
                        await ctx.send("API URL update canceled due to timeout.")
                        return
                else:
                    # Test parsing the response as JSON
                    try:
                        data = await resp.json()
                        if "data" not in data:
                            await ctx.send("Warning: Response does not contain a 'data' field. This may not be a valid API endpoint for One Piece TCG cards.")
                            await ctx.send("Do you want to set this URL anyway? (yes/no)")
                            
                            try:
                                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                                await ctx.bot.wait_for("message", check=pred, timeout=30)
                                if not pred.result:
                                    await ctx.send("API URL update canceled.")
                                    return
                            except asyncio.TimeoutError:
                                await ctx.send("API URL update canceled due to timeout.")
                                return
                    except Exception as e:
                        await ctx.send(f"Warning: Could not parse response as JSON: {str(e)}")
                        await ctx.send("Do you want to set this URL anyway? (yes/no)")
                        
                        try:
                            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                            await ctx.bot.wait_for("message", check=pred, timeout=30)
                            if not pred.result:
                                await ctx.send("API URL update canceled.")
                                return
                        except asyncio.TimeoutError:
                            await ctx.send("API URL update canceled due to timeout.")
                            return
        except Exception as e:
            await ctx.send(f"Error testing URL: {str(e)}")
            await ctx.send("Do you want to set this URL anyway? (yes/no)")
            
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=pred, timeout=30)
                if not pred.result:
                    await ctx.send("API URL update canceled.")
                    return
            except asyncio.TimeoutError:
                await ctx.send("API URL update canceled due to timeout.")
                return
        
        # Update the API URL
        await self.config.api_url.set(new_url)
        await ctx.send(f"API URL has been updated to: `{new_url}`")
    
    @optcg.command(name="enable")
    @commands.admin_or_permissions(manage_guild=True)
    async def enable_optcg(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Enable card spawning in the specified channel."""
        if channel is None:
            channel = ctx.channel
        
        # Check permissions in the target channel
        permissions = channel.permissions_for(ctx.guild.me)
        missing_perms = []
        
        if not permissions.send_messages:
            missing_perms.append("Send Messages")
        if not permissions.embed_links:
            missing_perms.append("Embed Links")
        
        if missing_perms:
            await ctx.send(
                f"⚠️ Warning: I don't have the following required permissions in {channel.mention}: "
                f"{', '.join(missing_perms)}. Please grant these permissions for the game to work properly."
            )
            await ctx.send("Do you want to continue enabling OPTCG in this channel anyway? (yes/no)")
            
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=pred, timeout=30)
                if not pred.result:
                    await ctx.send("OPTCG setup canceled.")
                    return
            except asyncio.TimeoutError:
                await ctx.send("OPTCG setup canceled due to timeout.")
                return
        
        await self.config.guild(ctx.guild).enabled.set(True)
        await self.config.guild(ctx.guild).spawn_channel.set(channel.id)
        
        # Test API connection
        api_ok = False
        try:
            async with self.session.get(await self.config.api_url()) as resp:
                if resp.status == 200:
                    api_ok = True
        except Exception:
            api_ok = False
        
        embed = discord.Embed(
            title="OPTCG Enabled!",
            description=f"One Piece TCG card game has been enabled in {channel.mention}!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Next Steps",
            value="1. Players can get starter packs with `.optcg starter`\n"
                  "2. Cards will randomly spawn in this channel\n"
                  "3. Use `.optcg spawn` to force a card spawn (admin only)",
            inline=False
        )
        
        if not api_ok:
            embed.add_field(
                name="⚠️ Warning",
                value="Could not connect to the API. Cards may not spawn correctly. "
                      "Check `.optcg admin debug` for more information.",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @optcg.command(name="disable")
    @commands.admin_or_permissions(manage_guild=True)
    async def disable_optcg(self, ctx: commands.Context):
        """Disable card spawning in this guild."""
        await self.config.guild(ctx.guild).enabled.set(False)
        
        await ctx.send("OPTCG card spawning disabled for this server!")
    
    @optcg.command(name="claim")
    async def claim_command(self, ctx: commands.Context):
        """Claim the active card in the channel."""
        await ctx.message.delete()
        await self.claim_card(ctx.author, ctx.guild)
    
    @optcg.command(name="starter")
    async def claim_starter(self, ctx: commands.Context):
        """Claim a starter pack of 5 random One Piece cards."""
        user_data = await self.config.user(ctx.author).all()
        
        if user_data["claimed_starter"]:
            await ctx.send("You've already claimed your starter pack!")
            return
        
        # Fetch 5 random cards
        cards = []
        for _ in range(5):
            card = await self.fetch_random_card()
            if card:
                cards.append(card)
        
        if not cards:
            await ctx.send("Sorry, I couldn't fetch any cards right now. Try again later.")
            return
        
        # Add cards to user's collection
        async with self.config.user(ctx.author).all() as user_data:
            for card in cards:
                user_data["cards"].append(card["id"])
                user_data["card_details"][card["id"]] = card
            
            user_data["claimed_starter"] = True
        
        # Create embed to show the cards
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Starter Pack",
            description="You've received 5 random One Piece cards!",
            color=discord.Color.blue()
        )
        
        for i, card in enumerate(cards, 1):
            embed.add_field(
                name=f"{i}. {card['name']} ({card['rarity']})",
                value=f"Type: {card['type']}\nColor: {card['color']}\nPower: {card['power']}",
                inline=False
            )
        
        # Show the first card's image
        embed.set_image(url=cards[0]["images"]["large"])
        
        await ctx.send(embed=embed)
    
    @optcg.command(name="collection", aliases=["cards"])
    async def view_collection(self, ctx: commands.Context, user: discord.User = None):
        """View your card collection or another user's collection."""
        target = user or ctx.author
        user_data = await self.config.user(target).all()
        
        if not user_data["cards"]:
            if target == ctx.author:
                await ctx.send("You don't have any cards yet! Use `.optcg starter` to get your first cards.")
            else:
                await ctx.send(f"{target.display_name} doesn't have any cards yet!")
            return
        
        # Create pages of cards
        pages = []
        card_details = user_data["card_details"]
        chunks = [user_data["cards"][i:i+10] for i in range(0, len(user_data["cards"]), 10)]
        
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"{target.display_name}'s Collection",
                description=f"Page {i+1}/{len(chunks)} - {len(user_data['cards'])} cards total",
                color=discord.Color.blue()
            )
            
            for card_id in chunk:
                if card_id in card_details:
                    card = card_details[card_id]
                    embed.add_field(
                        name=f"{card['name']} ({card['rarity']})",
                        value=f"ID: {card['id']}\nType: {card['type']}\nColor: {card['color']}\nPower: {card['power']}",
                        inline=True
                    )
            
            pages.append(embed)
        
        await menu(ctx, pages, DEFAULT_CONTROLS)
    
    @optcg.command(name="card")
    async def view_card(self, ctx: commands.Context, card_id: str):
        """View details of a specific card from your collection."""
        user_data = await self.config.user(ctx.author).all()
        card_details = user_data["card_details"]
        
        if card_id not in card_details:
            await ctx.send(f"You don't have a card with ID `{card_id}` in your collection.")
            return
        
        card = card_details[card_id]
        
        embed = discord.Embed(
            title=f"{card['name']} ({card['rarity']})",
            description=f"ID: {card['id']}",
            color=discord.Color.blue()
        )
        
        embed.set_image(url=card["images"]["large"])
        
        embed.add_field(name="Type", value=card["type"], inline=True)
        embed.add_field(name="Color", value=card["color"], inline=True)
        embed.add_field(name="Power", value=str(card["power"]), inline=True)
        embed.add_field(name="Cost", value=str(card["cost"]), inline=True)
        embed.add_field(name="Counter", value=card["counter"], inline=True)
        embed.add_field(name="Family", value=card["family"], inline=True)
        
        if card["ability"]:
            # Remove HTML tags
            ability = card["ability"].replace("<br>", "\n")
            embed.add_field(name="Ability", value=ability, inline=False)
        
        if card["trigger"]:
            embed.add_field(name="Trigger", value=card["trigger"], inline=False)
        
        await ctx.send(embed=embed)
    
    @optcg.command(name="search")
    async def search_cards(self, ctx: commands.Context, *, name: str):
        """Search for One Piece cards by name."""
        cards = await self.fetch_card_by_name(name)
        
        if not cards:
            await ctx.send(f"No cards found matching '{name}'.")
            return
        
        # Create pages
        pages = []
        chunks = [cards[i:i+5] for i in range(0, len(cards), 5)]
        
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"Search Results for '{name}'",
                description=f"Page {i+1}/{len(chunks)} - {len(cards)} cards total",
                color=discord.Color.blue()
            )
            
            for card in chunk:
                embed.add_field(
                    name=f"{card['name']} ({card['rarity']})",
                    value=f"ID: {card['id']}\nType: {card['type']}\nColor: {card['color']}\nPower: {card['power']}",
                    inline=True
                )
            
            # Show the first card's image
            if i == 0:
                embed.set_image(url=cards[0]["images"]["large"])
            
            pages.append(embed)
        
        await menu(ctx, pages, DEFAULT_CONTROLS)
        
    @optcg_admin.command(name="testmode")
    async def toggle_test_mode(self, ctx: commands.Context):
        """Toggle test mode for OPTCG.
        
        In test mode, cards will be generated from a predefined set of sample data
        instead of fetching from the API. Use this when the API is unavailable.
        """
        current_mode = await self.config.get_raw("test_mode", default=False)
        await self.config.test_mode.set(not current_mode)
        
        if not current_mode:
            await ctx.send("Test mode enabled. Cards will now be generated from sample data.")
        else:
            await ctx.send("Test mode disabled. Cards will be fetched from the API.")

    SAMPLE_CARDS = [
        {
            "id": "OP01-001",
            "name": "Monkey D. Luffy",
            "rarity": "L",
            "type": "LEADER",
            "power": 5000,
            "images": {
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-001.png"
            }
        },
        {
            "id": "OP01-002",
            "name": "Roronoa Zoro",
            "rarity": "SR",
            "type": "CHARACTER",
            "power": 6000,
            "images": {
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-002.png"
            }
        }
    ]

    async def fetch_random_card(self) -> Optional[Dict]:
        """Fetch a random card from the API or use test data."""
        # Check if test mode is enabled
        test_mode = await self.config.get_raw("test_mode", default=False)
        
        if test_mode:
            # Use sample card data
            return random.choice(self.SAMPLE_CARDS)
        
        # Normal API fetch logic
        try:
            # Try multiple pages to increase chances of success
            for _ in range(3):  # Try up to 3 different random pages
                page = random.randint(1, 20)
                async with self.session.get(
                    await self.config.api_url(),
                    params={"limit": 10, "page": page}
                ) as resp:
                    if resp.status != 200:
                        log.error(f"API request failed with status {resp.status}")
                        continue
                    
                    try:
                        data = await resp.json()
                        cards = data.get("data", [])
                        if cards:
                            return random.choice(cards)
                    except Exception as e:
                        log.error(f"Failed to parse API response: {e}")
                        continue
            
            # If we get here, the API attempts failed
            log.warning("API fetch attempts failed, using sample card data as fallback")
            return random.choice(self.SAMPLE_CARDS)
        
        except Exception as e:
            log.error(f"Error fetching card from API: {e}")
            # Fallback to sample data on error
            log.warning("Using sample card data as fallback due to API error")
            return random.choice(self.SAMPLE_CARDS)

    # Sample card data for test mode
    SAMPLE_CARDS = [
        {
            "id": "OP01-001",
            "code": "OP01-001",
            "rarity": "L",
            "type": "LEADER",
            "name": "Monkey D. Luffy",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-001.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-001.png"
            },
            "cost": 5,
            "attribute": {
                "name": "Strike",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type01.png"
            },
            "power": 5000,
            "counter": "0",
            "color": "Red",
            "family": "Supernovas/Straw Hat Crew",
            "ability": "[Your Turn] If you have 5 or less Life cards, this Leader gains +1000 power.",
            "trigger": "",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-002",
            "code": "OP01-002",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Roronoa Zoro",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-002.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-002.png"
            },
            "cost": 4,
            "attribute": {
                "name": "Slash",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type02.png"
            },
            "power": 6000,
            "counter": "1000",
            "color": "Red",
            "family": "Supernovas/Straw Hat Crew",
            "ability": "[DON!! x1] [When Attacking] You may rest 2 of your DON!! cards: This Character gains +2000 power during this attack.",
            "trigger": "+1000",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-003",
            "code": "OP01-003",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Nami",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-003.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-003.png"
            },
            "cost": 3,
            "attribute": {
                "name": "Special",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type03.png"
            },
            "power": 5000,
            "counter": "1000",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[DON!! x1] [Activate: Main] [Once Per Turn] You may rest one of your DON!! cards: Draw 1 card.",
            "trigger": "",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-004",
            "code": "OP01-004",
            "rarity": "R",
            "type": "CHARACTER",
            "name": "Usopp",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-004.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-004.png"
            },
            "cost": 2,
            "attribute": {
                "name": "Ranged",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type04.png"
            },
            "power": 3000,
            "counter": "0",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[On Play] Look at the top 5 cards of your deck, reveal up to 1 Character card with a cost of 4 or less from among them and add it to your hand. Place the remaining cards at the bottom of the deck in any order.",
            "trigger": "",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-005",
            "code": "OP01-005",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Sanji",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-005.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-005.png"
            },
            "cost": 4,
            "attribute": {
                "name": "Strike",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type01.png"
            },
            "power": 6000,
            "counter": "0",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[On Play] If you have a Character with \"Nami\" in its name in play, give up to 1 of your opponent's Characters -4000 power during this turn.",
            "trigger": "",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-006",
            "code": "OP01-006",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Tony Tony Chopper",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-006.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-006.png"
            },
            "cost": 2,
            "attribute": {
                "name": "Special",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type03.png"
            },
            "power": 2000,
            "counter": "1000",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[Activate: Main] [Once Per Turn] <Don!! -1> (You may return the specified number of DON!! cards from your field to your DON!! deck.): Draw 2 cards, then place 1 card from your hand at the bottom of your deck.",
            "trigger": "+1000",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-007",
            "code": "OP01-007",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Nico Robin",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-007.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-007.png"
            },
            "cost": 3,
            "attribute": {
                "name": "Special",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type03.png"
            },
            "power": 5000,
            "counter": "0",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[On Play] Play up to 1 Character card with a cost of 4 or less from your hand.",
            "trigger": "",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-008",
            "code": "OP01-008",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Franky",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-008.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-008.png"
            },
            "cost": 5,
            "attribute": {
                "name": "Special",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type03.png"
            },
            "power": 7000,
            "counter": "0",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[Your Turn] If you have 8 or more cards in your hand, this Character gains +2000 power.",
            "trigger": "+2000",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-009",
            "code": "OP01-009",
            "rarity": "SR",
            "type": "CHARACTER",
            "name": "Brook",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-009.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-009.png"
            },
            "cost": 5,
            "attribute": {
                "name": "Slash",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type02.png"
            },
            "power": 7000,
            "counter": "0",
            "color": "Red",
            "family": "Straw Hat Crew",
            "ability": "[Blocker] (After your opponent declares an attack, you may rest this card to make it the new target of the attack.)",
            "trigger": "+1000",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        },
        {
            "id": "OP01-010",
            "code": "OP01-010",
            "rarity": "R",
            "type": "CHARACTER",
            "name": "Jinbe",
            "images": {
                "small": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-010.png",
                "large": "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-010.png"
            },
            "cost": 5,
            "attribute": {
                "name": "Strike",
                "image": "https://en.onepiece-cardgame.com/images/cardlist/attribute/ico_type01.png"
            },
            "power": 7000,
            "counter": "1000",
            "color": "Red",
            "family": "Straw Hat Crew/Fish-Man",
            "ability": "[DON!! x1] [When Attacking] You may rest one of your DON!! cards: If your Leader has a [DON!! x1] Trigger Icon, this Character gains +2000 power during this attack.",
            "trigger": "",
            "set": {
                "name": "Romance Dawn [OP01]"
            },
            "notes": []
        }
    ]

    async def fetch_card_by_name(self, name: str) -> List[Dict]:
        """Fetch cards with the given name from the API or test data."""
        # Check if test mode is enabled
        test_mode = await self.config.get_raw("test_mode", default=False)
        
        if test_mode:
            # Filter sample cards by name
            name_lower = name.lower()
            matching_cards = [
                card for card in self.SAMPLE_CARDS 
                if name_lower in card["name"].lower()
            ]
            return matching_cards
        
        # Normal API fetch logic
        try:
            async with self.session.get(
                await self.config.api_url(),
                params={"name": name}
            ) as resp:
                if resp.status != 200:
                    log.error(f"API request failed with status {resp.status}")
                    # Fall back to test data
                    name_lower = name.lower()
                    matching_cards = [
                        card for card in self.SAMPLE_CARDS 
                        if name_lower in card["name"].lower()
                    ]
                    return matching_cards
                
                try:
                    data = await resp.json()
                    return data.get("data", [])
                except Exception as e:
                    log.error(f"Failed to parse API response: {e}")
                    # Fall back to test data
                    name_lower = name.lower()
                    matching_cards = [
                        card for card in self.SAMPLE_CARDS 
                        if name_lower in card["name"].lower()
                    ]
                    return matching_cards
        
        except Exception as e:
            log.error(f"Error fetching card by name from API: {e}")
            # Fall back to test data
            name_lower = name.lower()
            matching_cards = [
                card for card in self.SAMPLE_CARDS 
                if name_lower in card["name"].lower()
            ]
            return matching_cards
    
    @optcg.command(name="spawn")
    @commands.admin_or_permissions(manage_guild=True)
    async def force_spawn(self, ctx: commands.Context):
        """Force spawn a card in the designated channel."""
        # Check if the cog is enabled for this guild
        if not await self.config.guild(ctx.guild).enabled():
            await ctx.send("OPTCG is not enabled in this server. Use `.optcg enable` first.")
            return
        
        # Check if a spawn channel is set
        spawn_channel_id = await self.config.guild(ctx.guild).spawn_channel()
        if not spawn_channel_id:
            await ctx.send("No spawn channel has been set. Use `.optcg enable #channel` to set one.")
            return
        
        # Check if the channel exists
        spawn_channel = ctx.guild.get_channel(spawn_channel_id)
        if not spawn_channel:
            await ctx.send(f"The configured spawn channel (ID: {spawn_channel_id}) doesn't exist anymore. Please set a new one with `.optcg enable #channel`.")
            return
        
        # Check permissions in the channel
        permissions = spawn_channel.permissions_for(ctx.guild.me)
        
        if not permissions.send_messages:
            await ctx.send(f"I don't have permission to send messages in {spawn_channel.mention}.")
            return
        
        if not permissions.embed_links:
            await ctx.send(f"I don't have permission to embed links in {spawn_channel.mention}.")
            return
        
        # Attempt to spawn a card
        message = await self.spawn_card(ctx.guild)
        
        if message:
            await ctx.send(f"A card has been spawned in {spawn_channel.mention}!")
        else:
            # Test API connection to diagnose issues
            try:
                async with self.session.get(await self.config.api_url()) as resp:
                    if resp.status != 200:
                        await ctx.send(f"Failed to connect to the API. Status code: {resp.status}. Please try again later.")
                    else:
                        await ctx.send("Failed to spawn a card, but the API seems to be working. There might be an issue with card generation or message sending. Check the logs for more details.")
            except Exception as e:
                await ctx.send(f"Failed to connect to the API: {str(e)}. Please check your internet connection or try again later.")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages to possibly spawn a card."""
        # Skip if the message is from a bot or not in a guild
        if message.author.bot or not message.guild:
            return
        
        # Skip if the cog is disabled for this guild
        if not await self.config.guild(message.guild).enabled():
            return
        
        # Check if we're on cooldown
        async with self.spawn_lock:
            last_spawn_time = await self.config.last_spawn_time()
            current_time = int(message.created_at.timestamp())
            
            if current_time - last_spawn_time < await self.config.spawn_cooldown():
                return
            
            # Roll for spawn chance
            spawn_chance = await self.config.spawn_chance()
            if random.random() < spawn_chance:
                await self.config.last_spawn_time.set(current_time)
                await self.spawn_card(message.guild)
