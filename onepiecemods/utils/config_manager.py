# onepiecemods/utils/config_manager.py
import discord
from discord.ext import commands
from typing import Dict, Any, Optional, Union, List, Tuple
import json
import logging
from datetime import datetime

logger = logging.getLogger("red.onepiecemods.config")

class ConfigManager:
    """Advanced configuration management for One Piece Mods"""
    
    # Define configuration schema with validation
    CONFIG_SCHEMA = {
        "mute_role": {
            "type": int,
            "default": None,
            "description": "Role ID for Sea Prism Stone (mute) role",
            "validator": "validate_role_id"
        },
        "log_channel": {
            "type": int,
            "default": None,
            "description": "Channel ID for Marine HQ (moderation logs)",
            "validator": "validate_channel_id"
        },
        "warning_cooldown": {
            "type": int,
            "default": 30,
            "min": 5,
            "max": 3600,
            "description": "Cooldown between warnings in seconds"
        },
        "auto_escalation": {
            "type": bool,
            "default": True,
            "description": "Enable automatic escalation to Impel Down"
        },
        "max_warning_level": {
            "type": int,
            "default": 6,
            "min": 1,
            "max": 10,
            "description": "Maximum warning level before capping"
        },
        "escalation_levels": {
            "type": dict,
            "default": {
                3: {"level": 1, "duration": 30},
                5: {"level": 3, "duration": 60},
                7: {"level": 5, "duration": 120}
            },
            "description": "Warning levels that trigger escalation",
            "validator": "validate_escalation_levels"
        },
        "audit_log_format": {
            "type": str,
            "default": "One Piece Mods: {moderator} ({moderator_id}) | {reason}",
            "description": "Format template for audit log entries"
        },
        "backup_enabled": {
            "type": bool,
            "default": True,
            "description": "Enable automatic backup system"
        },
        "backup_interval": {
            "type": int,
            "default": 24,
            "min": 1,
            "max": 168,
            "description": "Hours between automatic backups"
        },
        "webhook_url": {
            "type": str,
            "default": None,
            "description": "Discord webhook URL for advanced logging",
            "validator": "validate_webhook_url"
        },
        "dm_on_punishment": {
            "type": bool,
            "default": False,
            "description": "Send DM to users when punished"
        },
        "punishment_appeal_channel": {
            "type": int,
            "default": None,
            "description": "Channel for punishment appeals",
            "validator": "validate_channel_id"
        },
        "automod_integration": {
            "type": bool,
            "default": False,
            "description": "Integrate with Discord's AutoMod"
        }
    }
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
    
    async def validate_role_id(self, guild: discord.Guild, role_id: int) -> Tuple[bool, str]:
        """Validate that a role ID exists in the guild"""
        if role_id is None:
            return True, ""
        
        role = guild.get_role(role_id)
        if not role:
            return False, f"Role with ID {role_id} not found in this server"
        
        return True, ""
    
    async def validate_channel_id(self, guild: discord.Guild, channel_id: int) -> Tuple[bool, str]:
        """Validate that a channel ID exists in the guild"""
        if channel_id is None:
            return True, ""
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return False, f"Channel with ID {channel_id} not found in this server"
        
        if not isinstance(channel, discord.TextChannel):
            return False, f"Channel must be a text channel"
        
        return True, ""
    
    async def validate_webhook_url(self, guild: discord.Guild, webhook_url: str) -> Tuple[bool, str]:
        """Validate webhook URL format"""
        if webhook_url is None:
            return True, ""
        
        # Accept Discord webhook URLs from all Discord domains
        valid_prefixes = [
            "https://discord.com/api/webhooks/",
            "https://canary.discord.com/api/webhooks/",
            "https://ptb.discord.com/api/webhooks/"
        ]
        
        if not any(webhook_url.startswith(prefix) for prefix in valid_prefixes):
            return False, "Invalid webhook URL format. Must be a Discord webhook URL."
        
        try:
            # Test webhook by sending a test message
            # Use bot's session if available, otherwise use the default
            session = getattr(self.bot, 'session', None)
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send("✅ Webhook test successful", username="One Piece Mods")
            return True, ""
        except Exception as e:
            return False, f"Webhook test failed: {str(e)}"
    
    async def validate_escalation_levels(self, guild: discord.Guild, escalation_data: dict) -> Tuple[bool, str]:
        """Validate escalation levels configuration"""
        if not isinstance(escalation_data, dict):
            return False, "Escalation levels must be a dictionary"
        
        for level_str, data in escalation_data.items():
            try:
                level = int(level_str)
                if level < 1 or level > 20:
                    return False, f"Warning level {level} out of range (1-20)"
                
                if not isinstance(data, dict):
                    return False, f"Escalation data for level {level} must be a dictionary"
                
                if "level" not in data or "duration" not in data:
                    return False, f"Escalation level {level} missing 'level' or 'duration'"
                
                impel_level = data["level"]
                duration = data["duration"]
                
                if not isinstance(impel_level, int) or impel_level < 1 or impel_level > 6:
                    return False, f"Impel Down level must be 1-6, got {impel_level}"
                
                if not isinstance(duration, int) or duration < 1:
                    return False, f"Duration must be positive integer, got {duration}"
                    
            except (ValueError, TypeError) as e:
                return False, f"Invalid escalation configuration: {str(e)}"
        
        return True, ""
    
    async def get_setting(self, guild: discord.Guild, setting: str) -> Any:
        """Get a configuration setting with validation"""
        if setting not in self.CONFIG_SCHEMA:
            raise ValueError(f"Unknown setting: {setting}")
        
        schema = self.CONFIG_SCHEMA[setting]
        
        try:
            if setting in ["escalation_levels"]:
                # Handle complex nested settings
                value = await getattr(self.config.guild(guild), setting)()
                return value
            else:
                value = await getattr(self.config.guild(guild), setting)()
                return value
        except Exception as e:
            logger.warning(f"Error getting setting {setting}: {e}, using default")
            return schema["default"]
    
    async def set_setting(self, guild: discord.Guild, setting: str, value: Any) -> Tuple[bool, str]:
        """Set a configuration setting with validation"""
        if setting not in self.CONFIG_SCHEMA:
            return False, f"Unknown setting: {setting}"
        
        schema = self.CONFIG_SCHEMA[setting]
        
        # Type validation
        expected_type = schema["type"]
        if expected_type == int and not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                return False, f"Setting {setting} must be an integer"
        
        elif expected_type == bool:
            if isinstance(value, str):
                value = value.lower() in ["true", "yes", "1", "enable", "on"]
            elif not isinstance(value, bool):
                return False, f"Setting {setting} must be a boolean"
        
        elif expected_type == str and not isinstance(value, str):
            return False, f"Setting {setting} must be a string"
        
        elif expected_type == dict and not isinstance(value, dict):
            return False, f"Setting {setting} must be a dictionary"
        
        # Range validation for integers
        if expected_type == int:
            if "min" in schema and value < schema["min"]:
                return False, f"Setting {setting} must be at least {schema['min']}"
            if "max" in schema and value > schema["max"]:
                return False, f"Setting {setting} must be at most {schema['max']}"
        
        # Custom validation
        if "validator" in schema:
            validator_name = schema["validator"]
            validator = getattr(self, validator_name)
            is_valid, error_msg = await validator(guild, value)
            if not is_valid:
                return False, error_msg
        
        # Set the value
        try:
            await getattr(self.config.guild(guild), setting).set(value)
            logger.info(f"Setting {setting} updated for guild {guild.id}")
            return True, ""
        except Exception as e:
            logger.error(f"Error setting {setting}: {e}")
            return False, f"Failed to save setting: {str(e)}"
    
    async def reset_setting(self, guild: discord.Guild, setting: str) -> Tuple[bool, str]:
        """Reset a setting to its default value"""
        if setting not in self.CONFIG_SCHEMA:
            return False, f"Unknown setting: {setting}"
        
        default_value = self.CONFIG_SCHEMA[setting]["default"]
        return await self.set_setting(guild, setting, default_value)
    
    async def get_all_settings(self, guild: discord.Guild) -> Dict[str, Any]:
        """Get all configuration settings for a guild"""
        settings = {}
        for setting in self.CONFIG_SCHEMA:
            try:
                settings[setting] = await self.get_setting(guild, setting)
            except Exception as e:
                logger.error(f"Error getting setting {setting}: {e}")
                settings[setting] = self.CONFIG_SCHEMA[setting]["default"]
        
        return settings
    
    async def validate_all_settings(self, guild: discord.Guild) -> List[Tuple[str, str]]:
        """Validate all current settings and return any errors"""
        errors = []
        settings = await self.get_all_settings(guild)
        
        for setting, value in settings.items():
            schema = self.CONFIG_SCHEMA[setting]
            
            if "validator" in schema:
                validator_name = schema["validator"]
                validator = getattr(self, validator_name)
                is_valid, error_msg = await validator(guild, value)
                if not is_valid:
                    errors.append((setting, error_msg))
        
        return errors
    
    async def export_config(self, guild: discord.Guild) -> str:
        """Export guild configuration as JSON"""
        settings = await self.get_all_settings(guild)
        
        export_data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "export_timestamp": datetime.now().isoformat(),
            "settings": settings,
            "schema_version": "2.0"
        }
        
        return json.dumps(export_data, indent=2)
    
    async def import_config(self, guild: discord.Guild, config_json: str) -> Tuple[bool, List[str]]:
        """Import guild configuration from JSON"""
        messages = []
        
        try:
            data = json.loads(config_json)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {str(e)}"]
        
        if "settings" not in data:
            return False, ["No settings found in configuration"]
        
        imported_settings = data["settings"]
        
        # Import each setting
        for setting, value in imported_settings.items():
            if setting in self.CONFIG_SCHEMA:
                success, error = await self.set_setting(guild, setting, value)
                if success:
                    messages.append(f"✅ Imported {setting}")
                else:
                    messages.append(f"❌ Failed to import {setting}: {error}")
            else:
                messages.append(f"⚠️ Unknown setting {setting} skipped")
        
        return True, messages
    
    def get_setting_info(self, setting: str) -> Dict[str, Any]:
        """Get information about a configuration setting"""
        if setting not in self.CONFIG_SCHEMA:
            return {}
        
        schema = self.CONFIG_SCHEMA[setting].copy()
        
        # Add readable type name
        type_names = {
            int: "Integer",
            str: "Text",
            bool: "True/False",
            dict: "Dictionary"
        }
        schema["type_name"] = type_names.get(schema["type"], str(schema["type"]))
        
        return schema
    
    def get_all_setting_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all configuration settings"""
        return {setting: self.get_setting_info(setting) for setting in self.CONFIG_SCHEMA}
    
    async def create_config_embed(self, guild: discord.Guild, detailed: bool = False) -> discord.Embed:
        """Create an embed showing current configuration"""
        settings = await self.get_all_settings(guild)
        
        embed = discord.Embed(
            title="⚙️ One Piece Mods Configuration",
            description=f"Settings for {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Group settings by category
        categories = {
            "🛡️ Moderation": ["mute_role", "log_channel", "warning_cooldown", "auto_escalation", "max_warning_level"],
            "⚡ Escalation": ["escalation_levels"],
            "💾 Backup & Logging": ["backup_enabled", "backup_interval", "webhook_url", "audit_log_format"],
            "🔧 Advanced": ["dm_on_punishment", "punishment_appeal_channel", "automod_integration"]
        }
        
        for category, setting_list in categories.items():
            if not detailed and category == "🔧 Advanced":
                continue
            
            field_value = ""
            for setting in setting_list:
                if setting in settings:
                    value = settings[setting]
                    
                    # Format value for display
                    if setting == "mute_role" and value:
                        role = guild.get_role(value)
                        display_value = role.mention if role else f"Deleted Role ({value})"
                    elif setting == "log_channel" and value:
                        channel = guild.get_channel(value)
                        display_value = channel.mention if channel else f"Deleted Channel ({value})"
                    elif setting == "punishment_appeal_channel" and value:
                        channel = guild.get_channel(value)
                        display_value = channel.mention if channel else f"Deleted Channel ({value})"
                    elif setting == "webhook_url" and value:
                        display_value = "✅ Configured"
                    elif setting == "escalation_levels":
                        if detailed:
                            escalation_summary = []
                            for level, data in value.items():
                                escalation_summary.append(f"Level {level} → Impel Down {data['level']} ({data['duration']}m)")
                            display_value = "\n".join(escalation_summary) if escalation_summary else "None"
                        else:
                            display_value = f"{len(value)} escalation rules"
                    elif isinstance(value, bool):
                        display_value = "✅ Enabled" if value else "❌ Disabled"
                    elif value is None:
                        display_value = "Not set"
                    else:
                        display_value = str(value)
                    
                    setting_name = setting.replace("_", " ").title()
                    field_value += f"**{setting_name}:** {display_value}\n"
            
            if field_value:
                embed.add_field(name=category, value=field_value, inline=False)
        
        # Add validation status
        errors = await self.validate_all_settings(guild)
        if errors:
            error_summary = f"⚠️ {len(errors)} configuration issues found"
            embed.add_field(name="Validation Status", value=error_summary, inline=False)
        else:
            embed.add_field(name="Validation Status", value="✅ All settings valid", inline=False)
        
        embed.set_footer(text=f"Guild ID: {guild.id}")
        
        return embed
    
    async def migrate_config(self, guild: discord.Guild, from_version: str, to_version: str) -> List[str]:
        """Migrate configuration between versions"""
        messages = []
        
        if from_version == "1.0" and to_version == "2.0":
            # Example migration: add new default values
            new_settings = {
                "backup_interval": 24,
                "dm_on_punishment": False,
                "automod_integration": False
            }
            
            for setting, default_value in new_settings.items():
                try:
                    current_value = await self.get_setting(guild, setting)
                    if current_value == self.CONFIG_SCHEMA[setting]["default"]:
                        await self.set_setting(guild, setting, default_value)
                        messages.append(f"✅ Added new setting: {setting}")
                except Exception as e:
                    messages.append(f"❌ Failed to migrate {setting}: {str(e)}")
        
        return messages