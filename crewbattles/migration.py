"""
migration.py
Data migration utility for upgrading legacy crew data to enhanced format
Updated for package structure with relative imports
"""

import json
import datetime
import asyncio
from typing import Dict, List, Any, Tuple
from pathlib import Path
import shutil

from .utils import EmbedBuilder
from .utils import NicknameManager


class CrewDataMigrator:
    """Handles migration from legacy crew data to enhanced format"""
    
    def __init__(self, cog, enhanced_logger, data_manager):
        self.cog = cog
        self.logger = enhanced_logger
        self.data_manager = data_manager
        self.migration_results = {}
    
    async def migrate_guild_data(self, guild, force_migration=False) -> Dict[str, Any]:
        """
        Migrate crew data for a specific guild from legacy to enhanced format
        
        Args:
            guild: Discord guild object
            force_migration: Whether to force migration even if data seems current
            
        Returns:
            Dict containing migration results and statistics
        """
        guild_id = str(guild.id)
        
        try:
            self.logger.info(f"Starting data migration for guild {guild.name} ({guild_id})")
            
            # Load existing data
            legacy_data = await self._load_legacy_data(guild)
            
            if not legacy_data:
                return {
                    "success": True,
                    "message": "No legacy data found to migrate",
                    "crews_migrated": 0,
                    "new_fields_added": 0
                }
            
            # Check if migration is needed
            if not force_migration and await self._is_data_current(legacy_data):
                return {
                    "success": True,
                    "message": "Data is already in enhanced format",
                    "crews_migrated": 0,
                    "new_fields_added": 0
                }
            
            # Create backup before migration
            backup_success = await self.data_manager.create_backup(guild)
            if not backup_success:
                self.logger.warning(f"Failed to create backup before migration for {guild.name}")
            
            # Perform migration
            migrated_data, migration_stats = await self._migrate_crew_data(guild, legacy_data)
            
            # Validate migrated data
            validation_success = await self._validate_migrated_data(guild, migrated_data)
            
            if not validation_success:
                raise Exception("Migrated data failed validation")
            
            # Update in-memory data
            self.cog.crews[guild_id] = migrated_data
            
            # Save migrated data
            save_success = await self.data_manager.save_crew_data(guild, migrated_data)
            
            if not save_success:
                raise Exception("Failed to save migrated data")
            
            # Log successful migration
            self.logger.log_crew_action(
                "data_migration_completed", guild.id,
                crews_migrated=migration_stats["crews_processed"],
                new_fields_added=migration_stats["fields_added"],
                backup_created=backup_success
            )
            
            return {
                "success": True,
                "message": "Data migration completed successfully",
                "crews_migrated": migration_stats["crews_processed"],
                "new_fields_added": migration_stats["fields_added"],
                "backup_created": backup_success,
                "validation_passed": validation_success
            }
            
        except Exception as e:
            self.logger.error(f"Migration failed for guild {guild.name}: {e}")
            return {
                "success": False,
                "message": f"Migration failed: {str(e)}",
                "crews_migrated": 0,
                "new_fields_added": 0,
                "error": str(e)
            }
    
    async def _load_legacy_data(self, guild) -> Dict[str, Any]:
        """Load legacy crew data from file"""
        try:
            file_path = self.data_manager.crews_dir / f"{guild.id}.json"
            
            if not file_path.exists():
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both legacy format (direct crew dict) and enhanced format (with metadata)
            if "crews" in data:
                return data["crews"]  # Enhanced format
            else:
                return data  # Legacy format
                
        except Exception as e:
            self.logger.error(f"Error loading legacy data for {guild.name}: {e}")
            return {}
    
    async def _is_data_current(self, data: Dict[str, Any]) -> bool:
        """Check if data is already in enhanced format"""
        if not data:
            return True
        
        # Check for enhanced format indicators
        sample_crew = next(iter(data.values()), {})
        
        enhanced_indicators = [
            "tag" in sample_crew,  # Crew tags
            "created_at" in sample_crew,  # Creation timestamp
            "stats" in sample_crew and isinstance(sample_crew.get("stats"), dict),  # Enhanced stats
        ]
        
        # If most enhanced features are present, consider it current
        return sum(enhanced_indicators) >= 2
    
    async def _migrate_crew_data(self, guild, legacy_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Migrate crew data to enhanced format"""
        migrated_crews = {}
        stats = {
            "crews_processed": 0,
            "fields_added": 0,
            "errors": 0
        }
        
        for crew_name, crew_data in legacy_data.items():
            try:
                migrated_crew = await self._migrate_single_crew(guild, crew_name, crew_data)
                migrated_crews[crew_name] = migrated_crew
                stats["crews_processed"] += 1
                
                # Count new fields added
                original_fields = set(crew_data.keys())
                new_fields = set(migrated_crew.keys()) - original_fields
                stats["fields_added"] += len(new_fields)
                
            except Exception as e:
                self.logger.error(f"Error migrating crew {crew_name}: {e}")
                stats["errors"] += 1
                # Keep original data if migration fails
                migrated_crews[crew_name] = crew_data
        
        return migrated_crews, stats
    
    async def _migrate_single_crew(self, guild, crew_name: str, crew_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single crew's data to enhanced format"""
        migrated = crew_data.copy()
        
        # Generate crew tag if missing
        if "tag" not in migrated:
            migrated["tag"] = NicknameManager.generate_crew_tag(crew_name)
        
        # Add creation timestamp if missing
        if "created_at" not in migrated:
            migrated["created_at"] = datetime.datetime.now().isoformat()
        
        # Ensure enhanced stats format
        if "stats" not in migrated:
            migrated["stats"] = {
                "wins": 0,
                "losses": 0,
                "tournaments_won": 0,
                "tournaments_participated": 0
            }
        else:
            # Ensure all required stat fields exist
            required_stats = ["wins", "losses", "tournaments_won", "tournaments_participated"]
            for stat in required_stats:
                if stat not in migrated["stats"]:
                    migrated["stats"][stat] = 0
        
        # Ensure members list exists and is valid
        if "members" not in migrated:
            migrated["members"] = []
        elif not isinstance(migrated["members"], list):
            migrated["members"] = []
        
        # Validate and fix member IDs
        valid_members = []
        for member_id in migrated["members"]:
            if isinstance(member_id, int):
                valid_members.append(member_id)
            elif isinstance(member_id, str) and member_id.isdigit():
                valid_members.append(int(member_id))
        migrated["members"] = valid_members
        
        # Ensure role IDs are integers
        for role_field in ["captain_role", "vice_captain_role", "crew_role"]:
            if role_field in migrated:
                role_id = migrated[role_field]
                if isinstance(role_id, str) and role_id.isdigit():
                    migrated[role_field] = int(role_id)
        
        # Add default emoji if missing
        if "emoji" not in migrated:
            migrated["emoji"] = "🏴‍☠️"
        
        # Ensure name field exists
        if "name" not in migrated:
            migrated["name"] = crew_name
        
        # Add description field if missing
        if "description" not in migrated:
            migrated["description"] = f"A mighty crew ready for battle!"
        
        return migrated
    
    async def _validate_migrated_data(self, guild, migrated_data: Dict[str, Any]) -> bool:
        """Validate that migrated data meets enhanced format requirements"""
        try:
            for crew_name, crew_data in migrated_data.items():
                # Check required fields
                required_fields = ["name", "emoji", "members", "captain_role", "vice_captain_role", "crew_role", "stats"]
                for field in required_fields:
                    if field not in crew_data:
                        self.logger.warning(f"Missing required field {field} in crew {crew_name}")
                        return False
                
                # Validate stats structure
                stats = crew_data.get("stats", {})
                required_stats = ["wins", "losses", "tournaments_won", "tournaments_participated"]
                for stat in required_stats:
                    if stat not in stats or not isinstance(stats[stat], int):
                        self.logger.warning(f"Invalid stat {stat} in crew {crew_name}")
                        return False
                
                # Validate members list
                members = crew_data.get("members", [])
                if not isinstance(members, list):
                    self.logger.warning(f"Invalid members list in crew {crew_name}")
                    return False
                
                # Validate role IDs
                for role_field in ["captain_role", "vice_captain_role", "crew_role"]:
                    role_id = crew_data.get(role_field)
                    if not isinstance(role_id, int):
                        self.logger.warning(f"Invalid {role_field} in crew {crew_name}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False


def add_migration_commands(cog_class):
    """Add migration commands to the cog"""
    
    @cog_class.commands.group(name="crewmigrate")
    @cog_class.commands.admin_or_permissions(administrator=True)
    async def migration_commands(self, ctx):
        """Data migration commands for crew system"""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create_info_embed(
                "🔄 Data Migration Commands",
                "Commands for migrating crew data to enhanced format"
            )
            embed.add_field(
                name="Available Commands",
                value=(
                    "`crewmigrate check` - Check if migration is needed\n"
                    "`crewmigrate run` - Migrate data to enhanced format\n"
                    "`crewmigrate force` - Force migration even if data seems current"
                ),
                inline=False
            )
            await ctx.send(embed=embed)
    
    @migration_commands.command(name="check")
    async def check_migration_status(self, ctx):
        """Check if data migration is needed"""
        try:
            migrator = CrewDataMigrator(self, self.enhanced_logger, self.data_manager)
            
            # Load current data
            legacy_data = await migrator._load_legacy_data(ctx.guild)
            
            if not legacy_data:
                embed = EmbedBuilder.create_info_embed(
                    "No Data Found",
                    "No crew data found for this server."
                )
            else:
                is_current = await migrator._is_data_current(legacy_data)
                
                if is_current:
                    embed = EmbedBuilder.create_success_embed(
                        "✅ Data is Current",
                        "Your crew data is already in enhanced format."
                    )
                    embed.add_field(
                        name="📊 Current Data",
                        value=f"**Crews Found:** {len(legacy_data)}",
                        inline=False
                    )
                else:
                    embed = EmbedBuilder.create_warning_embed(
                        "⚠️ Migration Needed",
                        "Your crew data needs to be migrated to the enhanced format."
                    )
                    embed.add_field(
                        name="📊 Legacy Data Found",
                        value=f"**Crews to Migrate:** {len(legacy_data)}",
                        inline=False
                    )
                    embed.add_field(
                        name="🚀 Next Steps",
                        value="Run `crewmigrate run` to upgrade your data to the enhanced format.",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.error(f"Migration check error: {e}")
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Check Failed",
                "An error occurred while checking migration status."
            ))
    
    @migration_commands.command(name="run")
    async def migrate_data(self, ctx):
        """Migrate legacy crew data to enhanced format"""
        try:
            # Create migrator instance
            migrator = CrewDataMigrator(self, self.enhanced_logger, self.data_manager)
            
            # Show migration start message
            embed = EmbedBuilder.create_info_embed(
                "🔄 Starting Data Migration",
                "Migrating crew data to enhanced format...\n"
                "This may take a moment."
            )
            
            start_msg = await ctx.send(embed=embed)
            
            # Perform migration
            results = await migrator.migrate_guild_data(ctx.guild, force_migration=False)
            
            # Create results embed
            if results["success"]:
                embed = EmbedBuilder.create_success_embed(
                    "✅ Migration Complete",
                    results["message"]
                )
                embed.add_field(
                    name="📊 Migration Statistics",
                    value=(
                        f"**Crews Migrated:** {results['crews_migrated']}\n"
                        f"**New Fields Added:** {results['new_fields_added']}\n"
                        f"**Backup Created:** {'✅' if results.get('backup_created') else '❌'}\n"
                        f"**Validation:** {'✅ Passed' if results.get('validation_passed') else '❌ Failed'}"
                    ),
                    inline=False
                )
            else:
                embed = EmbedBuilder.create_error_embed(
                    "❌ Migration Failed",
                    results["message"]
                )
                if "error" in results:
                    embed.add_field(
                        name="Error Details",
                        value=f"```{results['error']}```",
                        inline=False
                    )
            
            await start_msg.edit(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.error(f"Migration command error: {e}")
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Migration Error",
                "An error occurred during migration. Check logs for details."
            ))
    
    @migration_commands.command(name="force")
    async def force_migrate_data(self, ctx):
        """Force migration even if data appears current"""
        try:
            # Confirmation check
            embed = EmbedBuilder.create_warning_embed(
                "⚠️ Force Migration",
                "This will force migration even if your data appears to be current.\n"
                "A backup will be created automatically.\n\n"
                "Type `CONFIRM FORCE` to proceed:"
            )
            
            await ctx.send(embed=embed)
            
            def check(m):
                return (m.author == ctx.author and 
                       m.channel == ctx.channel and 
                       m.content == "CONFIRM FORCE")
            
            try:
                await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send(embed=EmbedBuilder.create_info_embed(
                    "Force Migration Cancelled",
                    "Operation timed out."
                ))
                return
            
            # Create migrator instance
            migrator = CrewDataMigrator(self, self.enhanced_logger, self.data_manager)
            
            # Show migration start message
            embed = EmbedBuilder.create_info_embed(
                "🔄 Force Migration Started",
                "Force migrating crew data to enhanced format...\n"
                "This may take a moment."
            )
            
            start_msg = await ctx.send(embed=embed)
            
            # Perform force migration
            results = await migrator.migrate_guild_data(ctx.guild, force_migration=True)
            
            # Create results embed
            if results["success"]:
                embed = EmbedBuilder.create_success_embed(
                    "✅ Force Migration Complete",
                    results["message"]
                )
                embed.add_field(
                    name="📊 Migration Statistics",
                    value=(
                        f"**Crews Processed:** {results['crews_migrated']}\n"
                        f"**New Fields Added:** {results['new_fields_added']}\n"
                        f"**Backup Created:** {'✅' if results.get('backup_created') else '❌'}\n"
                        f"**Validation:** {'✅ Passed' if results.get('validation_passed') else '❌ Failed'}"
                    ),
                    inline=False
                )
            else:
                embed = EmbedBuilder.create_error_embed(
                    "❌ Force Migration Failed",
                    results["message"]
                )
                if "error" in results:
                    embed.add_field(
                        name="Error Details",
                        value=f"```{results['error']}```",
                        inline=False
                    )
            
            await start_msg.edit(embed=embed)
            
        except Exception as e:
            self.enhanced_logger.error(f"Force migration command error: {e}")
            await ctx.send(embed=EmbedBuilder.create_error_embed(
                "Force Migration Error",
                "An error occurred during force migration. Check logs for details."
            ))
    
    # Add commands to cog
    cog_class.migration_commands = migration_commands
    cog_class.check_migration_status = check_migration_status
    cog_class.migrate_data = migrate_data
    cog_class.force_migrate_data = force_migrate_data
    
    return cog_class


# Integration function for main cog
def setup_migration(cog_class):
    """Setup migration functionality in the main cog"""
    return add_migration_commands(cog_class)