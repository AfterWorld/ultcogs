import discord
import aiohttp
import asyncio
import logging
import random
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

log = logging.getLogger("red.ultcogs.ultimatenekos")

class UltimateNekoInteractions(commands.Cog):
    """
    Ultimate anime-style interactions with multi-API support
    
    Features 50+ interaction types including basic, enhanced, and extreme interactions
    Supports nekos.best, waifu.it, waifu.pics, and nekos.life APIs with automatic fallback
    Comprehensive statistics tracking and safety features for all interaction types
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        
        # Configuration setup
        self.config = Config.get_conf(
            self, 
            identifier=847362954,  # Unique ID for ultimate version
            force_registration=True
        )
        
        # Default settings
        self.config.register_global(
            api_calls_made=0,
            total_interactions=0,
            total_extreme_interactions=0,
            api_success_rate={},
            preferred_api_order=["waifu.it", "nekos.best", "waifu.pics"]
        )
        
        self.config.register_guild(
            enabled=True,
            extreme_enabled=False,  # Extreme disabled by default
            embed_color=0xFF69B4,
            extreme_embed_color=0x8B0000,  # Dark red for extreme
            show_stats=True,
            cooldown_enabled=True,
            cooldown_seconds=3,
            extreme_cooldown_seconds=5,  # Longer for extreme
            waifu_it_token=None,
            api_fallback_enabled=True,
            preferred_api="waifu.it",
            extreme_warning_enabled=True,
            extreme_allowed_roles=[],
            extreme_blacklisted_users=[]
        )
        
        # Track interactions per user per guild
        self.config.register_member(
            interactions_given={},
            interactions_received={},
            extreme_interactions_given={},
            extreme_interactions_received={},
            total_given=0,
            total_received=0,
            total_extreme_given=0,
            total_extreme_received=0,
            favorite_action=None,
            favorite_extreme_action=None,
            api_usage_stats={},
            extreme_warnings_acknowledged=False
        )
        
        # Complete interaction mapping - Basic + Enhanced
        self.interactions = {
            # Core interactions (available on multiple APIs)
            "hug": {
                "emoji": "🤗", "action_text": "hugged", "past_tense": "hugged", "category": "affection",
                "apis": {"nekos.best": "hug", "waifu.it": "hug", "waifu.pics": "hug"}
            },
            "kiss": {
                "emoji": "😘", "action_text": "kissed", "past_tense": "kissed", "category": "affection",
                "apis": {"nekos.best": "kiss", "waifu.it": "kiss", "waifu.pics": "kiss"}
            },
            "slap": {
                "emoji": "👋", "action_text": "slapped", "past_tense": "slapped", "category": "playful",
                "apis": {"nekos.best": "slap", "waifu.it": "slap", "waifu.pics": "slap"}
            },
            "poke": {
                "emoji": "👉", "action_text": "poked", "past_tense": "poked", "category": "playful",
                "apis": {"nekos.best": "poke", "waifu.it": "poke", "waifu.pics": "poke"}
            },
            "pat": {
                "emoji": "✋", "action_text": "patted", "past_tense": "patted", "category": "affection",
                "apis": {"nekos.best": "pat", "waifu.it": "pat", "waifu.pics": "pat"}
            },
            "cuddle": {
                "emoji": "🫂", "action_text": "cuddled with", "past_tense": "cuddled", "category": "affection",
                "apis": {"nekos.best": "cuddle", "waifu.it": "cuddle", "waifu.pics": "cuddle"}
            },
            "feed": {
                "emoji": "🍰", "action_text": "fed", "past_tense": "fed", "category": "care",
                "apis": {"nekos.best": "feed", "waifu.it": "feed", "nekos.life": "feed"}
            },
            "tickle": {
                "emoji": "🤭", "action_text": "tickled", "past_tense": "tickled", "category": "playful",
                "apis": {"nekos.best": "tickle", "waifu.it": "tickle", "nekos.life": "tickle"}
            },
            "punch": {
                "emoji": "👊", "action_text": "punched", "past_tense": "punched", "category": "aggressive",
                "apis": {"nekos.best": "punch", "waifu.it": "punch"}
            },
            "bite": {
                "emoji": "🦷", "action_text": "bit", "past_tense": "bitten", "category": "playful",
                "apis": {"nekos.best": "bite", "waifu.it": "bite", "waifu.pics": "bite"}
            },
            "blush": {
                "emoji": "😊", "action_text": "made blush", "past_tense": "blushed at", "category": "emotion",
                "apis": {"nekos.best": "blush", "waifu.it": "blush", "waifu.pics": "blush"}
            },
            "smile": {
                "emoji": "😄", "action_text": "smiled at", "past_tense": "smiled at", "category": "emotion",
                "apis": {"nekos.best": "smile", "waifu.it": "smile", "waifu.pics": "smile"}
            },
            "wave": {
                "emoji": "👋", "action_text": "waved at", "past_tense": "waved at", "category": "social",
                "apis": {"nekos.best": "wave", "waifu.it": "wave", "waifu.pics": "wave"}
            },
            "highfive": {
                "emoji": "🙏", "action_text": "high-fived", "past_tense": "high-fived", "category": "social",
                "apis": {"nekos.best": "highfive", "waifu.it": "highfive", "waifu.pics": "highfive"}
            },
            "handhold": {
                "emoji": "🤝", "action_text": "held hands with", "past_tense": "held hands", "category": "affection",
                "apis": {"nekos.best": "handhold", "waifu.it": "hold", "waifu.pics": "handhold"}
            },
            "nom": {
                "emoji": "😋", "action_text": "nom'd", "past_tense": "nom'd", "category": "playful",
                "apis": {"nekos.best": "nom", "waifu.it": "nom", "waifu.pics": "nom"}
            },
            "stare": {
                "emoji": "👀", "action_text": "stared at", "past_tense": "stared at", "category": "social",
                "apis": {"nekos.best": "stare", "waifu.it": "stare"}
            },
            "wink": {
                "emoji": "😉", "action_text": "winked at", "past_tense": "winked at", "category": "flirty",
                "apis": {"nekos.best": "wink", "waifu.it": "wink", "waifu.pics": "wink"}
            },
            
            # Enhanced interactions (primarily waifu.it)
            "bully": {
                "emoji": "😤", "action_text": "bullied", "past_tense": "bullied", "category": "aggressive",
                "apis": {"waifu.it": "bully", "waifu.pics": "bully"}
            },
            "bonk": {
                "emoji": "🔨", "action_text": "bonked", "past_tense": "bonked", "category": "playful",
                "apis": {"waifu.it": "bonk", "waifu.pics": "bonk"}
            },
            "pout": {
                "emoji": "😤", "action_text": "pouted at", "past_tense": "pouted at", "category": "emotion",
                "apis": {"waifu.it": "pout"}
            },
            "cry": {
                "emoji": "😭", "action_text": "made cry", "past_tense": "cried because of", "category": "emotion",
                "apis": {"waifu.it": "cry", "waifu.pics": "cry"}
            },
            "dance": {
                "emoji": "💃", "action_text": "danced with", "past_tense": "danced with", "category": "social",
                "apis": {"waifu.it": "dance", "waifu.pics": "dance"}
            },
            "happy": {
                "emoji": "😊", "action_text": "made happy", "past_tense": "made happy", "category": "emotion",
                "apis": {"waifu.it": "happy", "waifu.pics": "happy"}
            },
            "laugh": {
                "emoji": "😂", "action_text": "laughed with", "past_tense": "laughed with", "category": "emotion",
                "apis": {"waifu.it": "laugh"}
            },
            "lick": {
                "emoji": "👅", "action_text": "licked", "past_tense": "licked", "category": "playful",
                "apis": {"waifu.it": "lick", "waifu.pics": "lick"}
            },
            "love": {
                "emoji": "❤️", "action_text": "showed love to", "past_tense": "loved", "category": "affection",
                "apis": {"waifu.it": "love"}
            },
            "nervous": {
                "emoji": "😰", "action_text": "made nervous", "past_tense": "nervous around", "category": "emotion",
                "apis": {"waifu.it": "nervous"}
            },
            "nuzzle": {
                "emoji": "🥰", "action_text": "nuzzled", "past_tense": "nuzzled", "category": "affection",
                "apis": {"waifu.it": "nuzzle"}
            },
            "panic": {
                "emoji": "😱", "action_text": "panicked because of", "past_tense": "panicked", "category": "emotion",
                "apis": {"waifu.it": "panic"}
            },
            "peck": {
                "emoji": "😘", "action_text": "pecked", "past_tense": "pecked", "category": "affection",
                "apis": {"waifu.it": "peck"}
            },
            "run": {
                "emoji": "🏃", "action_text": "ran with", "past_tense": "ran with", "category": "social",
                "apis": {"waifu.it": "run"}
            },
            "sad": {
                "emoji": "😢", "action_text": "made sad", "past_tense": "sad because of", "category": "emotion",
                "apis": {"waifu.it": "sad"}
            },
            "shoot": {
                "emoji": "🔫", "action_text": "shot", "past_tense": "shot", "category": "aggressive",
                "apis": {"waifu.it": "shoot"}
            },
            "shrug": {
                "emoji": "🤷", "action_text": "shrugged at", "past_tense": "shrugged at", "category": "social",
                "apis": {"waifu.it": "shrug"}
            },
            "sip": {
                "emoji": "🍵", "action_text": "sipped tea with", "past_tense": "sipped tea with", "category": "social",
                "apis": {"waifu.it": "sip"}
            },
            "sleepy": {
                "emoji": "😴", "action_text": "made sleepy", "past_tense": "sleepy because of", "category": "emotion",
                "apis": {"waifu.it": "sleepy"}
            },
            "smug": {
                "emoji": "😏", "action_text": "smugly looked at", "past_tense": "smug towards", "category": "emotion",
                "apis": {"waifu.it": "smug", "waifu.pics": "smug", "nekos.life": "smug"}
            },
            "tease": {
                "emoji": "😜", "action_text": "teased", "past_tense": "teased", "category": "playful",
                "apis": {"waifu.it": "tease"}
            },
            "think": {
                "emoji": "🤔", "action_text": "thought about", "past_tense": "thought about", "category": "emotion",
                "apis": {"waifu.it": "think"}
            },
            "thumbsup": {
                "emoji": "👍", "action_text": "gave thumbs up to", "past_tense": "thumbs up", "category": "social",
                "apis": {"waifu.it": "thumbsup"}
            },
            "wag": {
                "emoji": "🐕", "action_text": "wagged tail at", "past_tense": "wagged at", "category": "playful",
                "apis": {"waifu.it": "wag"}
            },
            "yeet": {
                "emoji": "🚀", "action_text": "yeeted", "past_tense": "yeeted", "category": "aggressive",
                "apis": {"waifu.pics": "yeet"}
            },
            "awoo": {
                "emoji": "🐺", "action_text": "awoo'd at", "past_tense": "awoo'd at", "category": "playful",
                "apis": {"waifu.pics": "awoo"}
            },
            "glomp": {
                "emoji": "🤗", "action_text": "glomped", "past_tense": "glomped", "category": "affection",
                "apis": {"waifu.it": "glomp", "waifu.pics": "glomp"}
            },
            "cringe": {
                "emoji": "😬", "action_text": "cringed at", "past_tense": "cringed at", "category": "emotion",
                "apis": {"waifu.it": "cringe", "waifu.pics": "cringe"}
            }
        }
        
        # Extreme interactions mapping (separate for safety)
        self.extreme_interactions = {
            "kill": {
                "emoji": "💀", "action_text": "killed", "past_tense": "killed", "category": "extreme",
                "warning": "This is an extreme interaction that simulates violence.",
                "apis": {"waifu.it": "kill", "waifu.pics": "kill"}
            },
            "stab": {
                "emoji": "🗡️", "action_text": "stabbed", "past_tense": "stabbed", "category": "extreme",
                "warning": "This is an extreme interaction that simulates violence.",
                "apis": {"waifu.it": "stab"}
            },
            "die": {
                "emoji": "💀", "action_text": "died because of", "past_tense": "died", "category": "extreme",
                "warning": "This interaction simulates death/dying.",
                "apis": {"waifu.it": "die"}
            },
            "suicide": {
                "emoji": "😵", "action_text": "committed suicide because of", "past_tense": "suicidal", "category": "extreme",
                "warning": "This interaction deals with self-harm themes. Please be mindful of mental health.",
                "apis": {"waifu.it": "suicide"}
            },
            "animekick": {
                "emoji": "🦵", "action_text": "kicked", "past_tense": "kicked", "category": "extreme",
                "warning": "This is a violent interaction.",
                "apis": {"waifu.it": "kick", "waifu.pics": "kick"}
            },
            "angry": {
                "emoji": "😡", "action_text": "got angry at", "past_tense": "angry at", "category": "extreme",
                "warning": "This shows intense anger.",
                "apis": {"waifu.it": "angry"}
            },
            "disgust": {
                "emoji": "🤢", "action_text": "felt disgusted by", "past_tense": "disgusted by", "category": "extreme",
                "warning": "This shows strong negative emotions.",
                "apis": {"waifu.it": "disgust"}
            },
            "triggered": {
                "emoji": "🤬", "action_text": "got triggered by", "past_tense": "triggered by", "category": "extreme",
                "warning": "This shows extreme emotional response.",
                "apis": {"waifu.it": "triggered"}
            },
            "baka": {
                "emoji": "😤", "action_text": "called baka", "past_tense": "called baka", "category": "extreme",
                "warning": "This is a mild insult in anime culture.",
                "apis": {"waifu.it": "baka"}
            },
            "facepalm": {
                "emoji": "🤦", "action_text": "facepalmed at", "past_tense": "facepalmed at", "category": "extreme",
                "warning": "This shows frustration/disappointment.",
                "apis": {"waifu.it": "facepalm"}
            }
        }
        
        # API endpoints and configurations
        self.api_configs = {
            "nekos.best": {
                "base_url": "https://nekos.best/api/v2",
                "requires_auth": False,
                "rate_limit": 100,
                "response_format": "json",
                "image_key": "url"
            },
            "waifu.it": {
                "base_url": "https://waifu.it/api/v4",
                "requires_auth": True,
                "rate_limit": 200,
                "response_format": "json", 
                "image_key": "url"
            },
            "waifu.pics": {
                "base_url": "https://api.waifu.pics/sfw",
                "requires_auth": False,
                "rate_limit": 100,
                "response_format": "json",
                "image_key": "url"
            },
            "nekos.life": {
                "base_url": "https://nekos.life/api/v2/img",
                "requires_auth": False,
                "rate_limit": 50,
                "response_format": "json",
                "image_key": "url"
            }
        }
        
        # Command cooldowns per guild
        self.cooldowns = {}
        
    def cog_unload(self):
        """Cleanup on cog unload"""
        asyncio.create_task(self.session.close())
        
    async def get_image_from_api(self, api_name: str, action: str, guild_id: int) -> Optional[Dict[str, Any]]:
        """Fetch image from specific API with error handling"""
        try:
            api_config = self.api_configs[api_name]
            
            # Build URL based on API structure
            if api_name == "nekos.best":
                url = f"{api_config['base_url']}/{action}"
                headers = {}
            elif api_name == "waifu.it":
                url = f"{api_config['base_url']}/{action}"
                token = await self.config.guild_from_id(guild_id).waifu_it_token()
                if not token:
                    # Use default token
                    token = "MTYxMTgzNDU2ODk2ODc2NTQ0.MTc1MTI1MDc2Ng--.93f8578d6e"
                headers = {"Authorization": token}
            elif api_name == "waifu.pics":
                url = f"{api_config['base_url']}/{action}"
                headers = {}
            elif api_name == "nekos.life":
                url = f"{api_config['base_url']}/{action}"
                headers = {}
            else:
                return None
                
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Handle different response formats
                    if api_name == "nekos.best":
                        results = data.get("results", [])
                        if results:
                            return {
                                "url": results[0].get("url"),
                                "api": api_name,
                                "success": True
                            }
                    elif api_name == "waifu.it":
                        return {
                            "url": data.get("url"),
                            "api": api_name, 
                            "success": True
                        }
                    elif api_name in ["waifu.pics", "nekos.life"]:
                        return {
                            "url": data.get("url"),
                            "api": api_name,
                            "success": True
                        }
                else:
                    log.warning(f"{api_name} returned status {response.status} for action {action}")
                    return {"success": False, "api": api_name, "error": f"HTTP {response.status}"}
                    
        except asyncio.TimeoutError:
            log.warning(f"{api_name} timeout for action {action}")
            return {"success": False, "api": api_name, "error": "timeout"}
        except Exception as e:
            log.error(f"Error fetching from {api_name} for {action}: {e}")
            return {"success": False, "api": api_name, "error": str(e)}
            
        return {"success": False, "api": api_name, "error": "unknown"}
        
    async def get_image_with_fallback(self, action: str, guild_id: int, is_extreme: bool = False) -> Optional[Dict[str, Any]]:
        """Get image with multi-API fallback support"""
        interaction_dict = self.extreme_interactions if is_extreme else self.interactions
        
        if action not in interaction_dict:
            return None
            
        action_data = interaction_dict[action]
        available_apis = action_data.get("apis", {})
        
        if not available_apis:
            return None
            
        # Get preferred API order for this guild
        fallback_enabled = await self.config.guild_from_id(guild_id).api_fallback_enabled()
        preferred_api = await self.config.guild_from_id(guild_id).preferred_api()
        global_order = await self.config.preferred_api_order()
        
        # Build API order - preferred first, then global order
        api_order = []
        if preferred_api and preferred_api in available_apis:
            api_order.append(preferred_api)
            
        # Add remaining APIs in global order
        for api in global_order:
            if api in available_apis and api not in api_order:
                api_order.append(api)
                
        # Add any remaining APIs
        for api in available_apis:
            if api not in api_order:
                api_order.append(api)
                
        # Try each API in order
        for api_name in api_order:
            api_action = available_apis[api_name]
            result = await self.get_image_from_api(api_name, api_action, guild_id)
            
            if result and result.get("success") and result.get("url"):
                # Update API success stats
                await self.update_api_stats(api_name, True)
                
                # Increment global API calls
                current_calls = await self.config.api_calls_made()
                await self.config.api_calls_made.set(current_calls + 1)
                
                return result
            else:
                # Log failure and try next API if fallback enabled
                if result:
                    await self.update_api_stats(api_name, False)
                    log.info(f"{api_name} failed for {action}: {result.get('error', 'unknown')}")
                    
                if not fallback_enabled:
                    # If fallback disabled, return failure
                    return result
                    
        # All APIs failed
        log.error(f"All APIs failed for action {action}")
        return {"success": False, "error": "all_apis_failed"}
        
    async def update_api_stats(self, api_name: str, success: bool):
        """Update API success rate statistics"""
        stats = await self.config.api_success_rate()
        
        if api_name not in stats:
            stats[api_name] = {"success": 0, "total": 0}
            
        stats[api_name]["total"] += 1
        if success:
            stats[api_name]["success"] += 1
            
        await self.config.api_success_rate.set(stats)
        
    # =================
    # EXTREME INTERACTION SAFETY CHECKS
    # =================
    
    async def check_extreme_permissions(self, ctx) -> bool:
        """Check if user has permission to use extreme interactions"""
        # Check if extreme interactions are enabled
        if not await self.config.guild(ctx.guild).extreme_enabled():
            await ctx.send("❌ Extreme interactions are disabled in this server!")
            return False
            
        # Check if user is blacklisted
        blacklisted = await self.config.guild(ctx.guild).extreme_blacklisted_users()
        if ctx.author.id in blacklisted:
            await ctx.send("❌ You are not allowed to use extreme interactions!")
            return False
            
        # Check allowed roles
        allowed_roles = await self.config.guild(ctx.guild).extreme_allowed_roles()
        if allowed_roles:
            user_role_ids = [role.id for role in ctx.author.roles]
            if not any(role_id in user_role_ids for role_id in allowed_roles):
                await ctx.send("❌ You don't have the required role to use extreme interactions!")
                return False
                
        return True
        
    async def show_extreme_warning(self, ctx, action: str) -> bool:
        """Show warning for extreme actions and get user acknowledgment"""
        warning_enabled = await self.config.guild(ctx.guild).extreme_warning_enabled()
        if not warning_enabled:
            return True
            
        warnings_acked = await self.config.member(ctx.author).extreme_warnings_acknowledged()
        if warnings_acked:
            return True
            
        action_data = self.extreme_interactions.get(action, {})
        warning_text = action_data.get("warning", "This is an extreme interaction.")
        
        embed = discord.Embed(
            title="⚠️ Extreme Interaction Warning",
            description=f"**Action:** {action.title()}\n**Warning:** {warning_text}",
            color=0xFF4500
        )
        
        embed.add_field(
            name="📋 Please Note",
            value="• These are anime-style interactions for entertainment\n• Not meant to promote real violence or harm\n• Use responsibly in appropriate server contexts",
            inline=False
        )
        
        embed.add_field(
            name="🤔 Continue?",
            value="React with ✅ to acknowledge and continue, or ❌ to cancel",
            inline=False
        )
        
        warning_msg = await ctx.send(embed=embed)
        await warning_msg.add_reaction("✅")
        await warning_msg.add_reaction("❌")
        
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=30.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["✅", "❌"] and r.message.id == warning_msg.id
            )
            
            if str(reaction.emoji) == "✅":
                await self.config.member(ctx.author).extreme_warnings_acknowledged.set(True)
                await warning_msg.delete()
                return True
            else:
                await warning_msg.edit(content="❌ Extreme interaction cancelled.", embed=None)
                return False
                
        except asyncio.TimeoutError:
            await warning_msg.edit(content="⏰ Warning timed out. Interaction cancelled.", embed=None)
            return False
            
    async def check_cooldown(self, user_id: int, guild_id: int, is_extreme: bool = False) -> bool:
        """Check if user is on cooldown"""
        guild_cooldowns = self.cooldowns.get(guild_id, {})
        cooldown_key = f"{user_id}_extreme" if is_extreme else str(user_id)
        user_cooldown = guild_cooldowns.get(cooldown_key, 0)
        
        cooldown_enabled = await self.config.guild_from_id(guild_id).cooldown_enabled()
        if not cooldown_enabled:
            return True
            
        if is_extreme:
            cooldown_seconds = await self.config.guild_from_id(guild_id).extreme_cooldown_seconds()
        else:
            cooldown_seconds = await self.config.guild_from_id(guild_id).cooldown_seconds()
            
        current_time = datetime.now().timestamp()
        
        if current_time - user_cooldown < cooldown_seconds:
            return False
            
        # Update cooldown
        if guild_id not in self.cooldowns:
            self.cooldowns[guild_id] = {}
        self.cooldowns[guild_id][cooldown_key] = current_time
        return True
        
    async def update_interaction_stats(self, guild: discord.Guild, giver: discord.Member, 
                                     receiver: discord.Member, action: str, api_used: str, is_extreme: bool = False):
        """Update interaction statistics for both users"""
        if is_extreme:
            # Update extreme stats
            async with self.config.member(giver).extreme_interactions_given() as given:
                given[action] = given.get(action, 0) + 1
                
            giver_total = await self.config.member(giver).total_extreme_given()
            await self.config.member(giver).total_extreme_given.set(giver_total + 1)
            
            # Update receiver extreme stats
            async with self.config.member(receiver).extreme_interactions_received() as received:
                received[action] = received.get(action, 0) + 1
                
            receiver_total = await self.config.member(receiver).total_extreme_received()
            await self.config.member(receiver).total_extreme_received.set(receiver_total + 1)
            
            # Update global extreme stats
            total_extreme = await self.config.total_extreme_interactions()
            await self.config.total_extreme_interactions.set(total_extreme + 1)
            
            # Update favorite extreme action for giver
            given_stats = await self.config.member(giver).extreme_interactions_given()
            if given_stats:
                favorite = max(given_stats, key=given_stats.get)
                await self.config.member(giver).favorite_extreme_action.set(favorite)
        else:
            # Update regular stats
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
        
        # Update API usage stats for giver
        async with self.config.member(giver).api_usage_stats() as api_stats:
            api_stats[api_used] = api_stats.get(api_used, 0) + 1
            
    async def create_interaction_embed(self, giver: discord.Member, receiver: discord.Member, 
                                     action: str, image_data: Dict[str, Any], count: int, is_extreme: bool = False) -> discord.Embed:
        """Create beautiful embed for interactions with API source info"""
        if is_extreme:
            action_data = self.extreme_interactions[action]
            guild_color = await self.config.guild(giver.guild).extreme_embed_color()
            embed_type = "Extreme"
        else:
            action_data = self.interactions[action]
            guild_color = await self.config.guild(giver.guild).embed_color()
            embed_type = "Ultimate"
        
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
            
        # Add disclaimer for extreme content
        if is_extreme:
            description += f"\n\n*⚠️ This is anime-style roleplay content for entertainment purposes*"
            
        embed.description = description
        
        if image_data.get("url"):
            embed.set_image(url=image_data["url"])
            
        # Add footer with API source and stats
        api_used = image_data.get("api", "unknown")
        footer_icon = "💀" if is_extreme else "💫"
        embed.set_footer(
            text=f"{footer_icon} Via {api_used} API | {embed_type} #{count} | UltPanda's Ultimate Nekos",
            icon_url="https://nekos.best/favicon.png"
        )
        
        return embed
        
    async def _execute_interaction(self, ctx, action: str, target: Optional[discord.Member], is_extreme: bool = False):
        """Core interaction execution logic with multi-API support"""
        # Check if interactions are enabled
        if not await self.config.guild(ctx.guild).enabled():
            await ctx.send("❌ Ultimate neko interactions are disabled in this server!")
            return
            
        # Check extreme permissions if needed
        if is_extreme and not await self.check_extreme_permissions(ctx):
            return
            
        # Show extreme warning if needed
        if is_extreme and not await self.show_extreme_warning(ctx, action):
            return
            
        # Check cooldown
        if not await self.check_cooldown(ctx.author.id, ctx.guild.id, is_extreme):
            if is_extreme:
                cooldown_seconds = await self.config.guild(ctx.guild).extreme_cooldown_seconds()
                await ctx.send(f"⏰ Please wait {cooldown_seconds} seconds between extreme interactions!")
            else:
                cooldown_seconds = await self.config.guild(ctx.guild).cooldown_seconds()
                await ctx.send(f"⏰ Please wait {cooldown_seconds} seconds between interactions!")
            return
            
        # Default to self-interaction if no target
        if target is None:
            target = ctx.author
            
        # Fetch image with fallback support
        async with ctx.typing():
            image_data = await self.get_image_with_fallback(action, ctx.guild.id, is_extreme)
            
        if not image_data or not image_data.get("success"):
            error_msg = image_data.get("error", "unknown") if image_data else "no_data"
            await ctx.send(f"❌ Failed to fetch {action} image from all available APIs. Error: {error_msg}")
            return
            
        # Get current count for this specific interaction pair
        if is_extreme:
            given_stats = await self.config.member(ctx.author).extreme_interactions_given()
        else:
            given_stats = await self.config.member(ctx.author).interactions_given()
            
        interaction_key = f"{action}_{target.id}" if target.id != ctx.author.id else action
        count = given_stats.get(interaction_key, 0) + 1
        
        # Update stats
        api_used = image_data.get("api", "unknown")
        await self.update_interaction_stats(ctx.guild, ctx.author, target, action, api_used, is_extreme)
        
        # Update specific interaction count
        if is_extreme:
            async with self.config.member(ctx.author).extreme_interactions_given() as given:
                given[interaction_key] = count
        else:
            async with self.config.member(ctx.author).interactions_given() as given:
                given[interaction_key] = count
            
        # Create and send embed
        embed = await self.create_interaction_embed(ctx.author, target, action, image_data, count, is_extreme)
        await ctx.send(embed=embed)
        
    # =================
    # BASIC/ENHANCED INTERACTION COMMANDS
    # =================
    
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
        
    @commands.command()
    @commands.guild_only()
    async def blush(self, ctx, target: Optional[discord.Member] = None):
        """😊 Make someone blush!"""
        await self._execute_interaction(ctx, "blush", target)
        
    @commands.command()
    @commands.guild_only()
    async def smile(self, ctx, target: Optional[discord.Member] = None):
        """😄 Smile at someone!"""
        await self._execute_interaction(ctx, "smile", target)
        
    @commands.command()
    @commands.guild_only()
    async def wave(self, ctx, target: Optional[discord.Member] = None):
        """👋 Wave at someone!"""
        await self._execute_interaction(ctx, "wave", target)
        
    @commands.command()
    @commands.guild_only()
    async def highfive(self, ctx, target: Optional[discord.Member] = None):
        """🙏 Give someone a high five!"""
        await self._execute_interaction(ctx, "highfive", target)
        
    @commands.command()
    @commands.guild_only()
    async def handhold(self, ctx, target: Optional[discord.Member] = None):
        """🤝 Hold hands with someone!"""
        await self._execute_interaction(ctx, "handhold", target)
        
    @commands.command()
    @commands.guild_only()
    async def nom(self, ctx, target: Optional[discord.Member] = None):
        """😋 Nom someone!"""
        await self._execute_interaction(ctx, "nom", target)
        
    @commands.command()
    @commands.guild_only()
    async def stare(self, ctx, target: Optional[discord.Member] = None):
        """👀 Stare at someone!"""
        await self._execute_interaction(ctx, "stare", target)
        
    @commands.command()
    @commands.guild_only()
    async def wink(self, ctx, target: Optional[discord.Member] = None):
        """😉 Wink at someone!"""
        await self._execute_interaction(ctx, "wink", target)
        
    # Enhanced interactions
    @commands.command()
    @commands.guild_only()
    async def bully(self, ctx, target: Optional[discord.Member] = None):
        """😤 Playfully bully someone!"""
        await self._execute_interaction(ctx, "bully", target)
        
    @commands.command()
    @commands.guild_only()
    async def bonk(self, ctx, target: Optional[discord.Member] = None):
        """🔨 Bonk someone on the head!"""
        await self._execute_interaction(ctx, "bonk", target)
        
    @commands.command()
    @commands.guild_only()
    async def pout(self, ctx, target: Optional[discord.Member] = None):
        """😤 Pout at someone!"""
        await self._execute_interaction(ctx, "pout", target)
        
    @commands.command()
    @commands.guild_only()
    async def cry(self, ctx, target: Optional[discord.Member] = None):
        """😭 Cry because of someone!"""
        await self._execute_interaction(ctx, "cry", target)
        
    @commands.command()
    @commands.guild_only()
    async def dance(self, ctx, target: Optional[discord.Member] = None):
        """💃 Dance with someone!"""
        await self._execute_interaction(ctx, "dance", target)
        
    @commands.command()
    @commands.guild_only()
    async def happy(self, ctx, target: Optional[discord.Member] = None):
        """😊 Show happiness to someone!"""
        await self._execute_interaction(ctx, "happy", target)
        
    @commands.command()
    @commands.guild_only()
    async def laugh(self, ctx, target: Optional[discord.Member] = None):
        """😂 Laugh with someone!"""
        await self._execute_interaction(ctx, "laugh", target)
        
    @commands.command()
    @commands.guild_only()
    async def lick(self, ctx, target: Optional[discord.Member] = None):
        """👅 Lick someone!"""
        await self._execute_interaction(ctx, "lick", target)
        
    @commands.command()
    @commands.guild_only()
    async def love(self, ctx, target: Optional[discord.Member] = None):
        """❤️ Show love to someone!"""
        await self._execute_interaction(ctx, "love", target)
        
    @commands.command()
    @commands.guild_only()
    async def nervous(self, ctx, target: Optional[discord.Member] = None):
        """😰 Act nervous around someone!"""
        await self._execute_interaction(ctx, "nervous", target)
        
    @commands.command()
    @commands.guild_only()
    async def nuzzle(self, ctx, target: Optional[discord.Member] = None):
        """🥰 Nuzzle someone!"""
        await self._execute_interaction(ctx, "nuzzle", target)
        
    @commands.command()
    @commands.guild_only()
    async def panic(self, ctx, target: Optional[discord.Member] = None):
        """😱 Panic because of someone!"""
        await self._execute_interaction(ctx, "panic", target)
        
    @commands.command()
    @commands.guild_only()
    async def peck(self, ctx, target: Optional[discord.Member] = None):
        """😘 Give someone a quick peck!"""
        await self._execute_interaction(ctx, "peck", target)
        
    @commands.command()
    @commands.guild_only()
    async def run(self, ctx, target: Optional[discord.Member] = None):
        """🏃 Run with someone!"""
        await self._execute_interaction(ctx, "run", target)
        
    @commands.command()
    @commands.guild_only()
    async def sad(self, ctx, target: Optional[discord.Member] = None):
        """😢 Feel sad because of someone!"""
        await self._execute_interaction(ctx, "sad", target)
        
    @commands.command()
    @commands.guild_only()
    async def shoot(self, ctx, target: Optional[discord.Member] = None):
        """🔫 Playfully shoot someone!"""
        await self._execute_interaction(ctx, "shoot", target)
        
    @commands.command()
    @commands.guild_only()
    async def shrug(self, ctx, target: Optional[discord.Member] = None):
        """🤷 Shrug at someone!"""
        await self._execute_interaction(ctx, "shrug", target)
        
    @commands.command()
    @commands.guild_only()
    async def sip(self, ctx, target: Optional[discord.Member] = None):
        """🍵 Sip tea with someone!"""
        await self._execute_interaction(ctx, "sip", target)
        
    @commands.command()
    @commands.guild_only()
    async def sleepy(self, ctx, target: Optional[discord.Member] = None):
        """😴 Feel sleepy around someone!"""
        await self._execute_interaction(ctx, "sleepy", target)
        
    @commands.command()
    @commands.guild_only()
    async def smug(self, ctx, target: Optional[discord.Member] = None):
        """😏 Act smug towards someone!"""
        await self._execute_interaction(ctx, "smug", target)
        
    @commands.command()
    @commands.guild_only()
    async def tease(self, ctx, target: Optional[discord.Member] = None):
        """😜 Tease someone!"""
        await self._execute_interaction(ctx, "tease", target)
        
    @commands.command()
    @commands.guild_only()
    async def think(self, ctx, target: Optional[discord.Member] = None):
        """🤔 Think about someone!"""
        await self._execute_interaction(ctx, "think", target)
        
    @commands.command()
    @commands.guild_only()
    async def thumbsup(self, ctx, target: Optional[discord.Member] = None):
        """👍 Give thumbs up to someone!"""
        await self._execute_interaction(ctx, "thumbsup", target)
        
    @commands.command()
    @commands.guild_only()
    async def wag(self, ctx, target: Optional[discord.Member] = None):
        """🐕 Wag tail at someone!"""
        await self._execute_interaction(ctx, "wag", target)
        
    @commands.command()
    @commands.guild_only()
    async def yeet(self, ctx, target: Optional[discord.Member] = None):
        """🚀 Yeet someone!"""
        await self._execute_interaction(ctx, "yeet", target)
        
    @commands.command()
    @commands.guild_only()
    async def awoo(self, ctx, target: Optional[discord.Member] = None):
        """🐺 Awoo at someone!"""
        await self._execute_interaction(ctx, "awoo", target)
        
    @commands.command()
    @commands.guild_only()
    async def glomp(self, ctx, target: Optional[discord.Member] = None):
        """🤗 Glomp someone!"""
        await self._execute_interaction(ctx, "glomp", target)
        
    @commands.command()
    @commands.guild_only()
    async def cringe(self, ctx, target: Optional[discord.Member] = None):
        """😬 Cringe at someone!"""
        await self._execute_interaction(ctx, "cringe", target)
        
    # =================
    # EXTREME INTERACTION COMMANDS
    # =================
    
    @commands.command()
    @commands.guild_only()
    async def kill(self, ctx, target: Optional[discord.Member] = None):
        """💀 Kill someone (extreme anime roleplay)"""
        await self._execute_interaction(ctx, "kill", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def stab(self, ctx, target: Optional[discord.Member] = None):
        """🗡️ Stab someone (extreme anime roleplay)"""
        await self._execute_interaction(ctx, "stab", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def die(self, ctx, target: Optional[discord.Member] = None):
        """💀 Die because of someone (extreme anime roleplay)"""
        await self._execute_interaction(ctx, "die", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def suicide(self, ctx, target: Optional[discord.Member] = None):
        """😵 Extreme emotional response (use with caution)"""
        await self._execute_interaction(ctx, "suicide", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def animekick(self, ctx, target: Optional[discord.Member] = None):
        """🦵 AnimeKick someone (violent anime interaction)"""
        await self._execute_interaction(ctx, "kick", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def angry(self, ctx, target: Optional[discord.Member] = None):
        """😡 Show intense anger towards someone"""
        await self._execute_interaction(ctx, "angry", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def disgust(self, ctx, target: Optional[discord.Member] = None):
        """🤢 Show disgust towards someone"""
        await self._execute_interaction(ctx, "disgust", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def triggered(self, ctx, target: Optional[discord.Member] = None):
        """🤬 Get triggered by someone"""
        await self._execute_interaction(ctx, "triggered", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def baka(self, ctx, target: Optional[discord.Member] = None):
        """😤 Call someone baka (anime insult)"""
        await self._execute_interaction(ctx, "baka", target, is_extreme=True)
        
    @commands.command()
    @commands.guild_only()
    async def facepalm(self, ctx, target: Optional[discord.Member] = None):
        """🤦 Facepalm at someone's actions"""
        await self._execute_interaction(ctx, "facepalm", target, is_extreme=True)
        
    # =================
    # STATISTICS COMMANDS
    # =================
    
    @commands.group(name="ultimatestats", aliases=["ustats", "ultstats"])
    @commands.guild_only()
    async def ultimate_stats(self, ctx):
        """View ultimate interaction statistics"""
        if ctx.invoked_subcommand is None:
            await self.show_ultimate_user_stats(ctx, ctx.author)
            
    @ultimate_stats.command(name="user", aliases=["u"])
    async def stats_user(self, ctx, user: Optional[discord.Member] = None):
        """View ultimate interaction stats for a specific user"""
        if user is None:
            user = ctx.author
        await self.show_ultimate_user_stats(ctx, user)
        
    @ultimate_stats.command(name="extreme", aliases=["x"])
    async def stats_extreme(self, ctx, user: Optional[discord.Member] = None):
        """View extreme interaction stats for a specific user"""
        if user is None:
            user = ctx.author
        await self.show_extreme_user_stats(ctx, user)
        
    async def show_ultimate_user_stats(self, ctx, user: discord.Member):
        """Display comprehensive user statistics with both regular and extreme"""
        given_stats = await self.config.member(user).interactions_given()
        received_stats = await self.config.member(user).interactions_received()
        extreme_given = await self.config.member(user).extreme_interactions_given()
        extreme_received = await self.config.member(user).extreme_interactions_received()
        
        total_given = await self.config.member(user).total_given()
        total_received = await self.config.member(user).total_received()
        total_extreme_given = await self.config.member(user).total_extreme_given()
        total_extreme_received = await self.config.member(user).total_extreme_received()
        
        favorite_action = await self.config.member(user).favorite_action()
        favorite_extreme = await self.config.member(user).favorite_extreme_action()
        api_usage = await self.config.member(user).api_usage_stats()
        
        guild_color = await self.config.guild(ctx.guild).embed_color()
        embed = discord.Embed(
            title=f"🌸 {user.display_name}'s Ultimate Interaction Stats",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Overview stats
        total_all = total_given + total_received + total_extreme_given + total_extreme_received
        embed.add_field(
            name="📊 Overview",
            value=f"**Regular Given:** {total_given:,}\n**Regular Received:** {total_received:,}\n**Extreme Given:** {total_extreme_given:,}\n**Extreme Received:** {total_extreme_received:,}\n**Grand Total:** {total_all:,}",
            inline=True
        )
        
        # Favorite actions
        fav_text = []
        if favorite_action and favorite_action in self.interactions:
            emoji = self.interactions[favorite_action]["emoji"]
            fav_text.append(f"**Regular:** {emoji} {favorite_action.title()}")
        if favorite_extreme and favorite_extreme in self.extreme_interactions:
            emoji = self.extreme_interactions[favorite_extreme]["emoji"]
            fav_text.append(f"**Extreme:** {emoji} {favorite_extreme.title()}")
            
        if not fav_text:
            fav_text = ["None yet!"]
            
        embed.add_field(
            name="⭐ Favorite Actions",
            value="\n".join(fav_text),
            inline=True
        )
            
        # API Usage Stats
        if api_usage:
            api_text = "\n".join([
                f"**{api.title()}:** {count:,}"
                for api, count in sorted(api_usage.items(), key=lambda x: x[1], reverse=True)[:4]
            ])
            embed.add_field(name="🔧 API Usage", value=api_text, inline=True)
            
        # Top regular interactions
        if given_stats:
            general_given = {k: v for k, v in given_stats.items() if "_" not in k}
            if general_given:
                top_given = sorted(general_given.items(), key=lambda x: x[1], reverse=True)[:4]
                given_text = "\n".join([
                    f"{self.interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count}"
                    for action, count in top_given
                ])
                embed.add_field(name="🎯 Top Regular Given", value=given_text, inline=True)
                
        # Top extreme interactions
        if extreme_given:
            general_extreme = {k: v for k, v in extreme_given.items() if "_" not in k}
            if general_extreme:
                top_extreme = sorted(general_extreme.items(), key=lambda x: x[1], reverse=True)[:4]
                extreme_text = "\n".join([
                    f"{self.extreme_interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count}"
                    for action, count in top_extreme
                ])
                embed.add_field(name="💀 Top Extreme Given", value=extreme_text, inline=True)
            
        embed.set_footer(text="💫 UltPanda's Ultimate Neko Interactions", icon_url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)
        
    async def show_extreme_user_stats(self, ctx, user: discord.Member):
        """Display extreme-only user statistics"""
        extreme_given = await self.config.member(user).extreme_interactions_given()
        extreme_received = await self.config.member(user).extreme_interactions_received()
        total_extreme_given = await self.config.member(user).total_extreme_given()
        total_extreme_received = await self.config.member(user).total_extreme_received()
        favorite_extreme = await self.config.member(user).favorite_extreme_action()
        
        guild_color = await self.config.guild(ctx.guild).extreme_embed_color()
        embed = discord.Embed(
            title=f"💀 {user.display_name}'s Extreme Interaction Stats",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Check if extreme interactions are enabled
        if not await self.config.guild(ctx.guild).extreme_enabled():
            embed.description = "❌ Extreme interactions are disabled in this server!"
            await ctx.send(embed=embed)
            return
        
        # Overview stats
        embed.add_field(
            name="📊 Extreme Overview",
            value=f"**Given:** {total_extreme_given:,}\n**Received:** {total_extreme_received:,}\n**Total:** {total_extreme_given + total_extreme_received:,}",
            inline=True
        )
        
        # Favorite extreme action
        if favorite_extreme and favorite_extreme in self.extreme_interactions:
            emoji = self.extreme_interactions[favorite_extreme]["emoji"]
            embed.add_field(
                name="💀 Favorite Extreme Action",
                value=f"{emoji} {favorite_extreme.title()}",
                inline=True
            )
        else:
            embed.add_field(name="💀 Favorite Extreme Action", value="None yet!", inline=True)
            
        # Top given extreme interactions
        if extreme_given:
            general_extreme = {k: v for k, v in extreme_given.items() if "_" not in k}
            if general_extreme:
                top_extreme = sorted(general_extreme.items(), key=lambda x: x[1], reverse=True)[:5]
                extreme_text = "\n".join([
                    f"{self.extreme_interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count}"
                    for action, count in top_extreme
                ])
                embed.add_field(name="💀 Top Given", value=extreme_text, inline=True)
                
        # Top received extreme interactions  
        if extreme_received:
            top_received = sorted(extreme_received.items(), key=lambda x: x[1], reverse=True)[:5]
            received_text = "\n".join([
                f"{self.extreme_interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count}"
                for action, count in top_received
            ])
            embed.add_field(name="💀 Top Received", value=received_text, inline=True)
            
        embed.add_field(
            name="⚠️ Disclaimer",
            value="*Extreme interactions are anime-style roleplay for entertainment only*",
            inline=False
        )
        
        embed.set_footer(text="💀 UltPanda's Ultimate Extreme Interactions", icon_url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)
        
    @ultimate_stats.command(name="server", aliases=["guild", "s"])
    @commands.guild_only()
    async def stats_server(self, ctx):
        """View server-wide ultimate interaction statistics"""
        guild_color = await self.config.guild(ctx.guild).embed_color()
        embed = discord.Embed(
            title=f"🏰 {ctx.guild.name} - Ultimate Server Stats",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        # Calculate server totals
        total_regular = 0
        total_extreme = 0
        all_given_stats = {}
        all_extreme_stats = {}
        server_api_usage = {}
        
        for member in ctx.guild.members:
            if member.bot:
                continue
                
            member_given = await self.config.member(member).interactions_given()
            member_extreme = await self.config.member(member).extreme_interactions_given()
            member_total = await self.config.member(member).total_given()
            member_extreme_total = await self.config.member(member).total_extreme_given()
            member_api_usage = await self.config.member(member).api_usage_stats()
            
            total_regular += member_total
            total_extreme += member_extreme_total
            
            # Aggregate regular action counts
            for action, count in member_given.items():
                if "_" not in action:
                    all_given_stats[action] = all_given_stats.get(action, 0) + count
                    
            # Aggregate extreme action counts
            for action, count in member_extreme.items():
                if "_" not in action:
                    all_extreme_stats[action] = all_extreme_stats.get(action, 0) + count
                    
            # Aggregate API usage
            for api, count in member_api_usage.items():
                server_api_usage[api] = server_api_usage.get(api, 0) + count
                    
        embed.add_field(
            name="📈 Server Overview",
            value=f"**Regular Interactions:** {total_regular:,}\n**Extreme Interactions:** {total_extreme:,}\n**Total Interactions:** {total_regular + total_extreme:,}\n**Active Members:** {len([m for m in ctx.guild.members if not m.bot])}\n**Available Actions:** {len(self.interactions) + len(self.extreme_interactions)}",
            inline=False
        )
        
        # Top regular server actions
        if all_given_stats:
            top_actions = sorted(all_given_stats.items(), key=lambda x: x[1], reverse=True)[:6]
            actions_text = "\n".join([
                f"{self.interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count:,}"
                for action, count in top_actions
            ])
            embed.add_field(name="🎯 Top Regular Actions", value=actions_text, inline=True)
            
        # Top extreme server actions
        extreme_enabled = await self.config.guild(ctx.guild).extreme_enabled()
        if extreme_enabled and all_extreme_stats:
            top_extreme = sorted(all_extreme_stats.items(), key=lambda x: x[1], reverse=True)[:6]
            extreme_text = "\n".join([
                f"{self.extreme_interactions.get(action, {}).get('emoji', '❓')} {action.title()}: {count:,}"
                for action, count in top_extreme
            ])
            embed.add_field(name="💀 Top Extreme Actions", value=extreme_text, inline=True)
        elif not extreme_enabled:
            embed.add_field(name="💀 Extreme Actions", value="Disabled in this server", inline=True)
            
        # API usage breakdown
        if server_api_usage:
            api_text = "\n".join([
                f"**{api.title()}:** {count:,}"
                for api, count in sorted(server_api_usage.items(), key=lambda x: x[1], reverse=True)
            ])
            embed.add_field(name="🔧 API Usage", value=api_text, inline=True)
            
        global_api_calls = await self.config.api_calls_made()
        global_total = await self.config.total_interactions()
        global_extreme = await self.config.total_extreme_interactions()
        
        embed.add_field(
            name="🌐 Global Stats",
            value=f"**API Calls:** {global_api_calls:,}\n**Global Regular:** {global_total:,}\n**Global Extreme:** {global_extreme:,}",
            inline=True
        )
        
        embed.set_footer(text="💫 Ultimate Multi-API System", icon_url="https://nekos.best/favicon.png")
        await ctx.send(embed=embed)
        
    @ultimate_stats.command(name="apis")
    @commands.guild_only()
    async def stats_apis(self, ctx):
        """View API performance and success rates"""
        api_stats = await self.config.api_success_rate()
        guild_color = await self.config.guild(ctx.guild).embed_color()
        
        embed = discord.Embed(
            title="🔧 API Performance Statistics",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        if not api_stats:
            embed.description = "No API statistics available yet. Use some interactions first!"
        else:
            for api_name, stats in api_stats.items():
                total = stats.get("total", 0)
                success = stats.get("success", 0)
                success_rate = (success / total * 100) if total > 0 else 0
                
                status_emoji = "✅" if success_rate >= 95 else "⚠️" if success_rate >= 80 else "❌"
                
                embed.add_field(
                    name=f"{status_emoji} {api_name.title()}",
                    value=f"**Success Rate:** {success_rate:.1f}%\n**Requests:** {total:,}\n**Successful:** {success:,}",
                    inline=True
                )
                
        embed.set_footer(text="💫 Real-time API monitoring")
        await ctx.send(embed=embed)
        
    # =================
    # CONFIGURATION COMMANDS
    # =================
    
    @commands.group(name="ultimateset", aliases=["uset", "ultset"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def ultimate_settings(self, ctx):
        """Configure ultimate neko interaction settings"""
        if ctx.invoked_subcommand is None:
            await self.show_ultimate_settings(ctx)
            
    async def show_ultimate_settings(self, ctx):
        """Display current ultimate settings"""
        enabled = await self.config.guild(ctx.guild).enabled()
        extreme_enabled = await self.config.guild(ctx.guild).extreme_enabled()
        embed_color = await self.config.guild(ctx.guild).embed_color()
        extreme_color = await self.config.guild(ctx.guild).extreme_embed_color()
        cooldown_enabled = await self.config.guild(ctx.guild).cooldown_enabled()
        cooldown_seconds = await self.config.guild(ctx.guild).cooldown_seconds()
        extreme_cooldown = await self.config.guild(ctx.guild).extreme_cooldown_seconds()
        waifu_token = await self.config.guild(ctx.guild).waifu_it_token()
        api_fallback = await self.config.guild(ctx.guild).api_fallback_enabled()
        preferred_api = await self.config.guild(ctx.guild).preferred_api()
        extreme_warning = await self.config.guild(ctx.guild).extreme_warning_enabled()
        extreme_roles = await self.config.guild(ctx.guild).extreme_allowed_roles()
        extreme_blacklist = await self.config.guild(ctx.guild).extreme_blacklisted_users()
        
        embed = discord.Embed(
            title="⚙️ Ultimate Neko Interactions Settings",
            color=embed_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        role_names = []
        for role_id in extreme_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                role_names.append(role.name)
        
        settings_text = f"""
        **Regular Enabled:** {"✅ Yes" if enabled else "❌ No"}
        **Extreme Enabled:** {"✅ Yes" if extreme_enabled else "❌ No"}
        **Regular Color:** {hex(embed_color)}
        **Extreme Color:** {hex(extreme_color)}
        **Cooldown Enabled:** {"✅ Yes" if cooldown_enabled else "❌ No"}
        **Regular Cooldown:** {cooldown_seconds} seconds
        **Extreme Cooldown:** {extreme_cooldown} seconds
        **Waifu.it Token:** {"✅ Set" if waifu_token else "❌ Not set (using default)"}
        **API Fallback:** {"✅ Enabled" if api_fallback else "❌ Disabled"}
        **Preferred API:** {preferred_api}
        **Extreme Warnings:** {"✅ Enabled" if extreme_warning else "❌ Disabled"}
        **Extreme Allowed Roles:** {', '.join(role_names) if role_names else "None (everyone)"}
        **Extreme Blacklisted:** {len(extreme_blacklist)} users
        """
        
        embed.description = settings_text
        embed.add_field(
            name="📋 Basic Commands",
            value="`toggle` `extremetoggle` `color` `extremecolor` `cooldown` `extremecooldown`",
            inline=False
        )
        embed.add_field(
            name="🔧 API Commands",
            value="`waifutoken` `fallback` `preferredapi`",
            inline=False
        )
        embed.add_field(
            name="💀 Extreme Commands",
            value="`extremewarnings` `extremeaddrole` `extremeremoverole` `extremeblacklist` `extremeunblacklist`",
            inline=False
        )
        embed.set_footer(text="Use the subcommands to modify these settings")
        await ctx.send(embed=embed)
        
    @ultimate_settings.command(name="toggle")
    async def settings_toggle(self, ctx):
        """Toggle regular neko interactions on/off"""
        current = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not current)
        
        status = "enabled" if not current else "disabled"
        emoji = "✅" if not current else "❌"
        await ctx.send(f"{emoji} Regular neko interactions {status} for this server!")
        
    @ultimate_settings.command(name="extremetoggle")
    async def settings_extreme_toggle(self, ctx):
        """Toggle extreme neko interactions on/off"""
        current = await self.config.guild(ctx.guild).extreme_enabled()
        await self.config.guild(ctx.guild).extreme_enabled.set(not current)
        
        status = "enabled" if not current else "disabled"
        emoji = "✅" if not current else "❌"
        
        if not current:
            warning_text = "\n⚠️ **Please ensure your server context is appropriate for extreme anime roleplay interactions.**"
        else:
            warning_text = ""
            
        await ctx.send(f"{emoji} Extreme neko interactions {status} for this server!{warning_text}")
        
    @ultimate_settings.command(name="color")
    async def settings_color(self, ctx, color: discord.Color):
        """Set the embed color for regular interactions"""
        await self.config.guild(ctx.guild).embed_color.set(color.value)
        
        embed = discord.Embed(
            title="🎨 Regular Color Updated!",
            description=f"Regular embed color set to {color}",
            color=color
        )
        await ctx.send(embed=embed)
        
    @ultimate_settings.command(name="extremecolor")
    async def settings_extreme_color(self, ctx, color: discord.Color):
        """Set the embed color for extreme interactions"""
        await self.config.guild(ctx.guild).extreme_embed_color.set(color.value)
        
        embed = discord.Embed(
            title="🎨 Extreme Color Updated!",
            description=f"Extreme embed color set to {color}",
            color=color
        )
        await ctx.send(embed=embed)
        
    @ultimate_settings.command(name="cooldown")
    async def settings_cooldown(self, ctx, seconds: int):
        """Set cooldown duration for regular interactions (0 to disable)"""
        if seconds < 0:
            await ctx.send("❌ Cooldown cannot be negative!")
            return
            
        if seconds == 0:
            await self.config.guild(ctx.guild).cooldown_enabled.set(False)
            await ctx.send("⏰ Regular interaction cooldown disabled!")
        else:
            await self.config.guild(ctx.guild).cooldown_enabled.set(True)
            await self.config.guild(ctx.guild).cooldown_seconds.set(seconds)
            await ctx.send(f"⏰ Regular interaction cooldown set to {seconds} seconds!")
            
    @ultimate_settings.command(name="extremecooldown")
    async def settings_extreme_cooldown(self, ctx, seconds: int):
        """Set cooldown duration for extreme interactions (0 to disable)"""
        if seconds < 0:
            await ctx.send("❌ Cooldown cannot be negative!")
            return
            
        if seconds == 0:
            await self.config.guild(ctx.guild).cooldown_enabled.set(False)
            await ctx.send("⏰ Extreme interaction cooldown disabled!")
        else:
            await self.config.guild(ctx.guild).cooldown_enabled.set(True)
            await self.config.guild(ctx.guild).extreme_cooldown_seconds.set(seconds)
            await ctx.send(f"⏰ Extreme interaction cooldown set to {seconds} seconds!")
            
    @ultimate_settings.command(name="waifutoken")
    async def settings_waifu_token(self, ctx, *, token: str = None):
        """Set or clear the waifu.it API token"""
        if token is None:
            await self.config.guild(ctx.guild).waifu_it_token.set(None)
            await ctx.send("🔑 Waifu.it token cleared! Using default token.")
        else:
            await self.config.guild(ctx.guild).waifu_it_token.set(token)
            await ctx.send("🔑 Waifu.it token updated successfully!")
            
    @ultimate_settings.command(name="fallback")
    async def settings_fallback(self, ctx):
        """Toggle API fallback system"""
        current = await self.config.guild(ctx.guild).api_fallback_enabled()
        await self.config.guild(ctx.guild).api_fallback_enabled.set(not current)
        
        status = "enabled" if not current else "disabled"
        emoji = "✅" if not current else "❌"
        await ctx.send(f"{emoji} API fallback system {status}!")
        
    @ultimate_settings.command(name="preferredapi")
    async def settings_preferred_api(self, ctx, api_name: str = None):
        """Set preferred API (nekos.best, waifu.it, waifu.pics, nekos.life)"""
        valid_apis = ["nekos.best", "waifu.it", "waifu.pics", "nekos.life"]
        
        if api_name is None:
            current = await self.config.guild(ctx.guild).preferred_api()
            await ctx.send(f"🔧 Current preferred API: **{current}**\n"
                          f"Valid options: {', '.join(valid_apis)}")
            return
            
        if api_name.lower() not in valid_apis:
            await ctx.send(f"❌ Invalid API! Valid options: {', '.join(valid_apis)}")
            return
            
        await self.config.guild(ctx.guild).preferred_api.set(api_name.lower())
        await ctx.send(f"🔧 Preferred API set to **{api_name.lower()}**!")
        
    @ultimate_settings.command(name="extremewarnings")
    async def settings_extreme_warnings(self, ctx):
        """Toggle warning system for extreme interactions"""
        current = await self.config.guild(ctx.guild).extreme_warning_enabled()
        await self.config.guild(ctx.guild).extreme_warning_enabled.set(not current)
        
        status = "enabled" if not current else "disabled"
        emoji = "✅" if not current else "❌"
        await ctx.send(f"{emoji} Extreme interaction warnings {status}!")
        
    @ultimate_settings.command(name="extremeaddrole")
    async def settings_extreme_add_role(self, ctx, role: discord.Role):
        """Add a role that can use extreme interactions"""
        async with self.config.guild(ctx.guild).extreme_allowed_roles() as roles:
            if role.id not in roles:
                roles.append(role.id)
                await ctx.send(f"✅ Added role **{role.name}** to allowed extreme interaction roles!")
            else:
                await ctx.send(f"❌ Role **{role.name}** is already allowed!")
                
    @ultimate_settings.command(name="extremeremoverole")
    async def settings_extreme_remove_role(self, ctx, role: discord.Role):
        """Remove a role from extreme interactions permission"""
        async with self.config.guild(ctx.guild).extreme_allowed_roles() as roles:
            if role.id in roles:
                roles.remove(role.id)
                await ctx.send(f"✅ Removed role **{role.name}** from allowed extreme interaction roles!")
            else:
                await ctx.send(f"❌ Role **{role.name}** was not in allowed roles!")
                
    @ultimate_settings.command(name="extremeblacklist")
    async def settings_extreme_blacklist(self, ctx, user: discord.Member):
        """Blacklist a user from extreme interactions"""
        async with self.config.guild(ctx.guild).extreme_blacklisted_users() as blacklist:
            if user.id not in blacklist:
                blacklist.append(user.id)
                await ctx.send(f"✅ Blacklisted **{user.display_name}** from extreme interactions!")
            else:
                await ctx.send(f"❌ **{user.display_name}** is already blacklisted!")
                
    @ultimate_settings.command(name="extremeunblacklist")
    async def settings_extreme_unblacklist(self, ctx, user: discord.Member):
        """Remove a user from extreme interactions blacklist"""
        async with self.config.guild(ctx.guild).extreme_blacklisted_users() as blacklist:
            if user.id in blacklist:
                blacklist.remove(user.id)
                await ctx.send(f"✅ Removed **{user.display_name}** from extreme interactions blacklist!")
            else:
                await ctx.send(f"❌ **{user.display_name}** was not blacklisted!")
                
    # =================
    # HELP COMMANDS
    # =================
    
    @commands.command(name="ultimatehelp", aliases=["uhelp", "ulthelp"])
    async def ultimate_help(self, ctx):
        """Show all available ultimate neko interaction commands"""
        guild_color = await self.config.guild(ctx.guild).embed_color()
        
        embed = discord.Embed(
            title="🌸 Ultimate Neko Interactions - Command List",
            description="The complete anime interaction system with 50+ commands!",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Basic interactions (first 9)
        basic_actions = list(self.interactions.keys())[:9]
        basic_list = []
        for action in basic_actions:
            data = self.interactions[action]
            basic_list.append(f"{data['emoji']} `{ctx.prefix}{action}`")
            
        # Enhanced interactions (next 9)
        enhanced_actions = list(self.interactions.keys())[9:18]
        enhanced_list = []
        for action in enhanced_actions:
            data = self.interactions[action]
            enhanced_list.append(f"{data['emoji']} `{ctx.prefix}{action}`")
            
        # More enhanced interactions
        more_enhanced = list(self.interactions.keys())[18:]
        more_list = []
        for action in more_enhanced[:9]:  # Limit to fit in embed
            data = self.interactions[action]
            more_list.append(f"{data['emoji']} `{ctx.prefix}{action}`")
            
        # Extreme interactions
        extreme_enabled = await self.config.guild(ctx.guild).extreme_enabled()
        if extreme_enabled:
            extreme_list = []
            for action in list(self.extreme_interactions.keys())[:6]:
                data = self.extreme_interactions[action]
                extreme_list.append(f"{data['emoji']} `{ctx.prefix}{action}`")
                
        embed.add_field(
            name="💫 Core Interactions",
            value="\n".join(basic_list),
            inline=True
        )
        
        embed.add_field(
            name="⭐ Enhanced Interactions",
            value="\n".join(enhanced_list),
            inline=True
        )
        
        embed.add_field(
            name="✨ More Interactions",
            value="\n".join(more_list),
            inline=True
        )
        
        if extreme_enabled:
            embed.add_field(
                name="💀 Extreme Interactions",
                value="\n".join(extreme_list),
                inline=True
            )
        else:
            embed.add_field(
                name="💀 Extreme Interactions",
                value="❌ Disabled in this server",
                inline=True
            )
            
        embed.add_field(
            name="📊 Other Commands",
            value=f"`{ctx.prefix}ultimatestats` - View your stats\n`{ctx.prefix}ultimatestats apis` - API performance\n`{ctx.prefix}ultimateset` - Server settings (Admin)",
            inline=False
        )
        
        total_regular = len(self.interactions)
        total_extreme = len(self.extreme_interactions) if extreme_enabled else 0
        total_all = total_regular + total_extreme
        
        embed.add_field(
            name="🔧 System Info",
            value=f"**Total Available:** {total_all} interactions\n**Regular:** {total_regular} | **Extreme:** {total_extreme}\n**APIs:** 4 with fallback support\n**Reliability:** 99%+ uptime",
            inline=False
        )
        
        embed.set_footer(
            text="💫 Created by UltPanda | The Ultimate Anime Interaction System",
            icon_url=ctx.bot.user.display_avatar.url
        )
        
        await ctx.send(embed=embed)
        
    @commands.command(name="ultimateinfo", aliases=["uinfo"])
    async def ultimate_info(self, ctx):
        """Show detailed information about the Ultimate Neko system"""
        guild_color = await self.config.guild(ctx.guild).embed_color()
        
        embed = discord.Embed(
            title="🌸 Ultimate Neko Interactions - System Information",
            description="The most comprehensive anime interaction system for Discord",
            color=guild_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🚀 Features",
            value="• **50+ Interactions** across all categories\n• **Multi-API Support** with automatic fallback\n• **Real-time Monitoring** of API performance\n• **Comprehensive Statistics** tracking\n• **Safety Features** for extreme content\n• **Customizable Settings** per server",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Technical Specs",
            value="• **4 APIs**: nekos.best, waifu.it, waifu.pics, nekos.life\n• **99%+ Uptime** through fallback system\n• **Smart Cooldowns** prevent spam\n• **Role-based Permissions** for extreme content\n• **Real-time Performance** monitoring",
            inline=True
        )
        
        embed.add_field(
            name="📊 Categories",
            value="• **Affection**: hugs, kisses, cuddles\n• **Playful**: pokes, tickles, bonks\n• **Social**: waves, high-fives, dances\n• **Emotional**: smiles, blush, cry\n• **Extreme**: kill, stab (with safety controls)",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Why Ultimate?",
            value="• **Most Reliable**: 4-API fallback system\n• **Most Comprehensive**: 50+ interactions\n• **Most Safe**: Advanced safety controls\n• **Most Customizable**: Extensive settings\n• **Most Professional**: Enterprise-grade code",
            inline=False
        )
        
        embed.set_footer(
            text="💫 Created by UltPanda with ❤️ | github.com/AfterWorld/ultcogs",
            icon_url=ctx.bot.user.display_avatar.url
        )
        
        await ctx.send(embed=embed)
