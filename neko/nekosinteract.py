import discord
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

log = logging.getLogger("red.ultcogs.nekosinteract")

class NekoInteractions(commands.Cog):
    """
    Anime-style interaction commands using the nekos.best API
    
    Slap, poke, hug, and more with beautiful anime GIFs!
    Tracks interaction statistics and displays them in style.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        
        # Configuration setup with hierarchical scopes
        self.config = Config.get_conf(
            self, 
            identifier=847362951,  # Unique identifier for UltPanda
            force_registration=True
        )
        
        # Default settings
        self.config.register_global(
            api_calls_made=0,
            total_interactions=0
        )
        
        self.config.register_guild(
            enabled=True,
            embed_color=0xFF69B4,  # Hot pink default
            show_stats=True,
            cooldown_enabled=True,
            cooldown_seconds=3
        )
        
        # Track interactions per user per guild
        self.config.register_member(
            interactions_given={},  # {action: count}
            interactions_received={},  # {action: count}
            total_given=0,
            total_received=0,
            favorite_action=None
        )
        
        # Available interactions from nekos.best API
        self.interactions = {
            "hug": {"emoji": "🤗", "action_text": "hugged", "past_tense": "hugged"},
            "kiss": {"emoji": "😘", "action_text": "kissed", "past_tense": "kissed"},
            "slap": {"emoji": "👋", "action_text": "slapped", "past_tense": "slapped"},
            "poke": {"emoji": "👉", "action_text": "poked", "past_tense": "poked"},
            "pat": {"emoji": "✋", "action_text": "patted", "past_tense": "patted"},
            "cuddle": {"emoji": "🫂", "action_text": "cuddled with", "past_tense": "cuddled"},
            "feed": {"emoji": "🍰", "action_text": "fed", "past_tense": "fed"},
            "tickle": {"emoji": "🤭", "action_text": "tickled", "past_tense": "tickled"},
            "punch": {"emoji": "👊", "action_text": "punched", "past_tense": "punched"},
            "bite": {"emoji": "🦷", "action_text": "bit", "past_tense": "bitten"},
            "blush": {"emoji": "😊", "action_text": "made blush", "past_tense": "blushed at"},
            "smile": {"emoji": "😄", "action_text": "smiled at", "past_tense": "smiled at"},
            "wave": {"emoji": "👋", "action_text": "waved at", "past_tense": "waved at"},
            "highfive": {"emoji": "🙏", "action_text": "high-fived", "past_tense": "high-fived"},
            "handhold": {"emoji": "🤝", "action_text": "held hands with", "past_tense": "held hands"},
            "nom": {"emoji": "😋", "action_text": "nom'd", "past_tense": "nom'd"},
            "stare": {"emoji": "👀", "action_text": "stared at", "past_tense": "stared at"},
            "wink": {"emoji": "😉", "action_text": "winked at", "past_tense": "winked at"}
        }
        
        # Command cooldowns per guild
        self.cooldowns = {}
        
    def cog_unload(self):
        """Cleanup on cog unload"""
        asyncio.create_task(self.session.close())
        
    async def get_nekos_image(self, action: str) -> Optional[str]:
        """Fetch random image from nekos.best API"""
        try:
            url = f"https://nekos.best/api/v2/{action}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Increment API call counter
                    current_calls = await self.config.api_calls_made()
                    await self.config.api_calls_made.set(current_calls + 1)
                    return data.get("results", [{}])[0].get("url")
                else:
                    log.warning(f"API returned status {response.status} for action {action}")
        except Exception as e:
            log.error(f"Error fetching image for {action}: {e}")
        return None
        
    async def check_cooldown(self, user_id: int, guild_id: int) -> bool:
        """Check if user is on cooldown"""
        guild_cooldowns = self.cooldowns.get(guild_id, {})
        user_cooldown = guild_cooldowns.get(user_id, 0)
        
        cooldown_enabled = await self.config.guild_from_id(guild_id).cooldown_enabled()
        if not cooldown_enabled:
            return True
            
        cooldown_seconds = await self.config.guild_from_id(guild_id).cooldown_seconds()
        current_time = datetime.now().timestamp()
        
        if current_time - user_cooldown < cooldown_seconds:
            return False
            
        # Update cooldown
        if guild_id not in self.cooldowns:
            self.cooldowns[guild_id] = {}
        self.cooldowns[guild_id][user_id] = current_time
        return True
        
    async def update_interaction_stats(self, guild: discord.Guild, giver: discord.Member, 
                                     receiver: discord.Member, action: str):
        """Update interaction statistics for both users"""
        # Update giver stats
        async with self.config.member(giver).interactions_given() as given:
            given[action] = given.get(action, 0) + 1
            
        giver_total = await self.config.member(giver).total_given()
        await self.config.member(giver).total_given.set(giver_total + 1)
        
        # Update receiver stats
        async with self.config.member(receiver).interactions_received() as received:
            received[action] = received.get(action, 0) + 1
            
        receiver_total = await self.config.member(receiver).total_received()
        await self.config.member(receiver).total_received.set(receiver_total + 1)
        
        # Update global stats
        total_interactions = await self.config.total_interactions()
        await self.config.total_interactions.set(total_interactions + 1)
        
        # Update favorite action for giver
        given_stats = await self.config.member(giver).interactions_given()
        if given_stats:
            favorite = max(given_stats, key=given_stats.get)
            await self.config.member(giver).favorite_action.set(favorite)
            
    async def create_interaction_embed(self, giver: discord.Member, receiver: discord.Member, 
                                     action: str, image_url: str, count: int) -> discord.Embed:
        """Create beautiful embed for interactions"""
        action_data = self.interactions[action]
        guild_color = await self.config.guild(giver.guild).embed_color()
        
        embed = discord.Embed(
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Create engaging description
        if receiver.id == giver.id:
            description = f"{action_data['emoji']} **{giver.display_name}** {action_data['action_text']} themselves!"
        else:
            times_text = "time" if count == 1 else "times"
            description = (f"{action_data['emoji']} **{giver.display_name}** "
                         f"{action_data['action_text']} **{receiver.display_name}** "
                         f"({count} {times_text})!")
            
        embed.description = description
        
        if image_url:
            embed.set_image(url=image_url)
            
        # Add footer with fun stats
        embed.set_footer(
            text=f"💫 Powered by nekos.best | {action.title()} #{count}",
            icon_url="https://nekos.best/favicon.png"
        )
        
        return embed
        
    async def generate_interaction_command(self, action: str):
        """Dynamically generate interaction commands"""
        action_data = self.interactions[action]
        
        @commands.command(name=action)
        @commands.guild_only()
        async def interaction_cmd(self, ctx, target: Optional[discord.Member] = None):
            f"""{action_data['emoji']} {action_data['action_text'].title()} someone with a cute anime GIF!"""
            
            # Check if interactions are enabled
            if not await self.config.guild(ctx.guild).enabled():
                await ctx.send("❌ Neko interactions are disabled in this server!")
                return
                
            # Check cooldown
            if not await self.check_cooldown(ctx.author.id, ctx.guild.id):
                cooldown_seconds = await self.config.guild(ctx.guild).cooldown_seconds()
                await ctx.send(f"⏰ Please wait {cooldown_seconds} seconds between interactions!")
                return
                
            # Default to self-interaction if no target
            if target is None:
                target = ctx.author
                
            # Fetch image from API
            async with ctx.typing():
                image_url = await self.get_nekos_image(action)
                
            if not image_url:
                await ctx.send(f"❌ Failed to fetch {action} image. Please try again!")
                return
                
            # Get current count for this specific interaction
            if target.id == ctx.author.id:
                # Self interaction
                given_stats = await self.config.member(ctx.author).interactions_given()
                count = given_stats.get(action, 0) + 1
            else:
                # Get how many times giver has done this action to receiver
                given_stats = await self.config.member(ctx.author).interactions_given()
                count = given_stats.get(f"{action}_{target.id}", 0) + 1
                
                # Update specific target tracking
                async with self.config.member(ctx.author).interactions_given() as given:
                    given[f"{action}_{target.id}"] = count
                    
            # Update general stats
            await self.update_interaction_stats(ctx.guild, ctx.author, target, action)
            
            # Create and send embed
            embed = await self.create_interaction_embed(ctx.author, target, action, image_url, count)
            await ctx.send(embed=embed)
            
        return interaction_cmd
        
    def __init_subclass__(cls):
        # Dynamically add all interaction commands
        for action in cls.interactions:
            cmd = cls.generate_interaction_command(cls, action)
            setattr(cls, f"{action}_command", cmd)
            
    # Generate all interaction commands
    def __new__(cls, bot):
        instance = super().__new__(cls)
        
        # Add all interaction commands dynamically
        for action in instance.interactions:
            cmd_func = instance.generate_interaction_command(action)
            # Bind the method to the instance
            bound_method = cmd_func.__get__(instance, cls)
            setattr(instance, f"{action}_cmd", bound_method)
            
        return instance
        
    # Manual command definitions (since dynamic generation is complex in Red)
    @commands.command(aliases=["cuddles"])
    @commands.guild_only()
    async def hug(self, ctx, target: Optional[discord.Member] = None):
        """🤗 Give someone a warm hug with a cute anime GIF!"""
        await self._execute_interaction(ctx, "hug", target)
        
    @commands.command()
    @commands.guild_only() 
    async def kiss(self, ctx, target: Optional[discord.Member] = None):
        """😘 Give someone a sweet kiss!"""
        await self._execute_interaction(ctx, "kiss", target)
        
    @commands.command()
    @commands.guild_only()
    async def slap(self, ctx, target: Optional[discord.Member] = None):
        """👋 Slap someone (playfully!)"""
        await self._execute_interaction(ctx, "slap", target)
        
    @commands.command()
    @commands.guild_only()
    async def poke(self, ctx, target: Optional[discord.Member] = None):
        """👉 Poke someone to get their attention!"""
        await self._execute_interaction(ctx, "poke", target)
        
    @commands.command()
    @commands.guild_only()
    async def pat(self, ctx, target: Optional[discord.Member] = None):
        """✋ Give someone headpats!"""
        await self._execute_interaction(ctx, "pat", target)
        
    @commands.command()
    @commands.guild_only()
    async def cuddle(self, ctx, target: Optional[discord.Member] = None):
        """🫂 Cuddle with someone!"""
        await self._execute_interaction(ctx, "cuddle", target)
        
    @commands.command()
    @commands.guild_only()
    async def feed(self, ctx, target: Optional[discord.Member] = None):
        """🍰 Feed someone something delicious!"""
        await self._execute_interaction(ctx, "feed", target)
        
    @commands.command()
    @commands.guild_only()
    async def tickle(self, ctx, target: Optional[discord.Member] = None):
        """🤭 Tickle someone!"""
        await self._execute_interaction(ctx, "tickle", target)
        
    @commands.command()
    @commands.guild_only()
    async def punch(self, ctx, target: Optional[discord.Member] = None):
        """👊 Punch someone (anime style!)"""
        await self._execute_interaction(ctx, "punch", target)
        
    @commands.command()
    @commands.guild_only()
    async def bite(self, ctx, target: Optional[discord.Member] = None):
        """🦷 Playfully bite someone!"""
        await self._execute_interaction(ctx, "bite", target)
        
    async def _execute_interaction(self, ctx, action: str, target: Optional[discord.Member]):
        """Core interaction execution logic"""
        # Check if interactions are enabled
        if not await self.config.guild(ctx.guild).enabled():
            await ctx.send("❌ Neko interactions are disabled in this server!")
            return
            
        # Check cooldown
        if not await self.check_cooldown(ctx.author.id, ctx.guild.id):
            cooldown_seconds = await self.config.guild(ctx.guild).cooldown_seconds()
            await ctx.send(f"⏰ Please wait {cooldown_seconds} seconds between interactions!")
            return
            
        # Default to self-interaction if no target
        if target is None:
            target = ctx.author
            
        # Fetch image from API
        async with ctx.typing():
            image_url = await self.get_nekos_image(action)
            
        if not image_url:
            await ctx.send(f"❌ Failed to fetch {action} image. Please try again!")
            return
            
        # Get current count for this specific interaction pair
        given_stats = await self.config.member(ctx.author).interactions_given()
        interaction_key = f"{action}_{target.id}" if target.id != ctx.author.id else action
        count = given_stats.get(interaction_key, 0) + 1
        
        # Update stats
        await self.update_interaction_stats(ctx.guild, ctx.author, target, action)
        
        # Update specific interaction count
        async with self.config.member(ctx.author).interactions_given() as given:
            given[interaction_key] = count
            
        # Create and send embed
        embed = await self.create_interaction_embed(ctx.author, target, action, image_url, count)
        await ctx.send(embed=embed)
        
    @commands.group(name="nekostats", aliases=["nstats"])
    @commands.guild_only()
    async def neko_stats(self, ctx):
        """View interaction statistics"""
        if ctx.invoked_subcommand is None:
            await self.show_user_stats(ctx, ctx.author)
            
    @neko_stats.command(name="user", aliases=["u"])
    async def stats_user(self, ctx, user: Optional[discord.Member] = None):
        """View interaction stats for a specific user"""
        if user is None:
            user = ctx.author
        await self.show_user_stats(ctx, user)
        
    async def show_user_stats(self, ctx, user: discord.Member):
        """Display comprehensive user statistics"""
        given_stats = await self.config.member(user).interactions_given()
        received_stats = await self.config.member(user).interactions_received()
        total_given = await self.config.member(user).total_given()
        total_received = await self.config.member(user).total_received()
        favorite_action = await self.config.member(user).favorite_action()
        
        guild_color = await self.config.guild(ctx.guild).embed_color()
        embed = discord.Embed(
            title=f"🌸 {user.display_name}'s Interaction Stats",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Overview stats
        embed.add_field(
            name="📊 Overview",
            value=f"**Given:** {total_given:,}\n**Received:** {total_received:,}\n**Total:** {total_given + total_received:,}",
            inline=True
        )
        
        # Favorite action
        if favorite_action and favorite_action in self.interactions:
            emoji = self.interactions[favorite_action]["emoji"]
            embed.add_field(
                name="⭐ Favorite Action",
                value=f"{emoji} {favorite_action.title()}",
                inline=True
            )
        else:
            embed.add_field(name="⭐ Favorite Action", value="None yet!", inline=True)
            
        # Top given interactions
        if given_stats:
            # Filter out specific target interactions for cleaner display
            general_given = {k: v for k, v in given_stats.items() if "_" not in k}
            if general_given:
                top_given = sorted(general_given.items(), key=lambda x: x[1], reverse=True)[:5]
                given_text = "\n".join([
                    f"{self.interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count}"
                    for action, count in top_given
                ])
                embed.add_field(name="🎯 Top Given", value=given_text, inline=True)
                
        # Top received interactions  
        if received_stats:
            top_received = sorted(received_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            received_text = "\n".join([
                f"{self.interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count}"
                for action, count in top_received
            ])
            embed.add_field(name="💝 Top Received", value=received_text, inline=True)
            
        embed.set_footer(text="💫 UltPanda's Neko Interactions", icon_url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)
        
    @neko_stats.command(name="server", aliases=["guild", "s"])
    @commands.guild_only()
    async def stats_server(self, ctx):
        """View server-wide interaction statistics"""
        guild_color = await self.config.guild(ctx.guild).embed_color()
        embed = discord.Embed(
            title=f"🏰 {ctx.guild.name} - Server Stats",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        # Calculate server totals
        total_server_interactions = 0
        all_given_stats = {}
        
        for member in ctx.guild.members:
            if member.bot:
                continue
                
            member_given = await self.config.member(member).interactions_given()
            member_total = await self.config.member(member).total_given()
            total_server_interactions += member_total
            
            # Aggregate action counts (excluding specific targets)
            for action, count in member_given.items():
                if "_" not in action:  # Skip specific target interactions
                    all_given_stats[action] = all_given_stats.get(action, 0) + count
                    
        embed.add_field(
            name="📈 Server Overview",
            value=f"**Total Interactions:** {total_server_interactions:,}\n**Active Members:** {len([m for m in ctx.guild.members if not m.bot])}\n**Available Actions:** {len(self.interactions)}",
            inline=False
        )
        
        # Top server actions
        if all_given_stats:
            top_actions = sorted(all_given_stats.items(), key=lambda x: x[1], reverse=True)[:8]
            actions_text = "\n".join([
                f"{self.interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count:,}"
                for action, count in top_actions
            ])
            embed.add_field(name="🎯 Most Popular Actions", value=actions_text, inline=True)
            
        global_api_calls = await self.config.api_calls_made()
        global_total = await self.config.total_interactions()
        
        embed.add_field(
            name="🌐 Global Stats",
            value=f"**API Calls:** {global_api_calls:,}\n**Global Total:** {global_total:,}",
            inline=True
        )
        
        embed.set_footer(text="💫 Powered by nekos.best API", icon_url="https://nekos.best/favicon.png")
        await ctx.send(embed=embed)
        
    @commands.group(name="nekoset", aliases=["nset"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def neko_settings(self, ctx):
        """Configure neko interaction settings"""
        if ctx.invoked_subcommand is None:
            await self.show_settings(ctx)
            
    async def show_settings(self, ctx):
        """Display current settings"""
        enabled = await self.config.guild(ctx.guild).enabled()
        embed_color = await self.config.guild(ctx.guild).embed_color()
        show_stats = await self.config.guild(ctx.guild).show_stats()
        cooldown_enabled = await self.config.guild(ctx.guild).cooldown_enabled()
        cooldown_seconds = await self.config.guild(ctx.guild).cooldown_seconds()
        
        embed = discord.Embed(
            title="⚙️ Neko Interactions Settings",
            color=embed_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        settings_text = f"""
        **Enabled:** {"✅ Yes" if enabled else "❌ No"}
        **Embed Color:** {hex(embed_color)}
        **Show Stats:** {"✅ Yes" if show_stats else "❌ No"}
        **Cooldown Enabled:** {"✅ Yes" if cooldown_enabled else "❌ No"}
        **Cooldown Duration:** {cooldown_seconds} seconds
        """
        
        embed.description = settings_text
        embed.set_footer(text="Use the subcommands to modify these settings")
        await ctx.send(embed=embed)
        
    @neko_settings.command(name="toggle")
    async def settings_toggle(self, ctx):
        """Toggle neko interactions on/off"""
        current = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not current)
        
        status = "enabled" if not current else "disabled"
        emoji = "✅" if not current else "❌"
        await ctx.send(f"{emoji} Neko interactions {status} for this server!")
        
    @neko_settings.command(name="color")
    async def settings_color(self, ctx, color: discord.Color):
        """Set the embed color for interactions"""
        await self.config.guild(ctx.guild).embed_color.set(color.value)
        
        embed = discord.Embed(
            title="🎨 Color Updated!",
            description=f"Embed color set to {color}",
            color=color
        )
        await ctx.send(embed=embed)
        
    @neko_settings.command(name="cooldown")
    async def settings_cooldown(self, ctx, seconds: int):
        """Set cooldown duration (0 to disable)"""
        if seconds < 0:
            await ctx.send("❌ Cooldown cannot be negative!")
            return
            
        if seconds == 0:
            await self.config.guild(ctx.guild).cooldown_enabled.set(False)
            await ctx.send("⏰ Cooldown disabled!")
        else:
            await self.config.guild(ctx.guild).cooldown_enabled.set(True)
            await self.config.guild(ctx.guild).cooldown_seconds.set(seconds)
            await ctx.send(f"⏰ Cooldown set to {seconds} seconds!")
            
    @commands.command(name="nekohelp", aliases=["nhelp"])
    async def neko_help(self, ctx):
        """Show all available neko interaction commands"""
        guild_color = await self.config.guild(ctx.guild).embed_color()
        
        embed = discord.Embed(
            title="🌸 Neko Interactions - Command List",
            description="Cute anime-style interactions powered by nekos.best!",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Group commands for better display
        interaction_list = []
        for action, data in self.interactions.items():
            interaction_list.append(f"{data['emoji']} `{ctx.prefix}{action}` - {data['action_text'].title()} someone")
            
        # Split into chunks for multiple fields
        chunk_size = 8
        chunks = [interaction_list[i:i + chunk_size] for i in range(0, len(interaction_list), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            field_name = f"💫 Interactions {i+1}" if len(chunks) > 1 else "💫 Available Interactions"
            embed.add_field(
                name=field_name,
                value="\n".join(chunk),
                inline=True
            )
            
        embed.add_field(
            name="📊 Other Commands",
            value=f"`{ctx.prefix}nekostats` - View your stats\n`{ctx.prefix}nekoset` - Server settings (Admin)",
            inline=False
        )
        
        embed.set_footer(
            text="💫 Created by UltPanda | Use [p]help <command> for more info",
            icon_url=ctx.bot.user.display_avatar.url
        )
        
        await ctx.send(embed=embed)
