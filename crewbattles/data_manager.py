"""
crewbattles/data_manager.py
Enhanced data management with validation, backup, and atomic operations
"""

import json
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import discord

from .constants import CrewSettings, REQUIRED_CREW_FIELDS
from .models import CrewData, CrewStats
from .logger import EnhancedCrewLogger
from .exceptions import DataCorruptionError, BackupError, CrewValidationError


class DataManager:
    """Enhanced data management with validation, backup, and atomic operations"""
    
    def __init__(self, data_path: Path, logger: EnhancedCrewLogger):
        self.data_path = data_path
        self.crews_dir = data_path / "Crews"
        self.backup_dir = data_path / "Backups"
        self.temp_dir = data_path / "Temp"
        self.logger = logger
        
        # Ensure directories exist
        self.crews_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
    
    async def save_crew_data(self, guild: discord.Guild, crews: Dict[str, Dict[str, Any]]) -> bool:
        """
        Save crew data with backup, validation, and atomic operations
        Returns True if successful, False otherwise
        """
        start_time = datetime.datetime.now()
        
        try:
            # Create backup first
            backup_success = await self.create_backup(guild)
            if not backup_success:
                self.logger.warning(f"Backup failed for guild {guild.id}, proceeding with save anyway")
            
            # Validate all crew data before saving
            validation_errors = []
            for crew_name, crew_data in crews.items():
                is_valid, errors = self.validate_crew_data(crew_data)
                if not is_valid:
                    validation_errors.extend([f"{crew_name}: {error}" for error in errors])
            
            if validation_errors:
                self.logger.error(f"Validation failed for guild {guild.id}: {validation_errors}")
                raise CrewValidationError("Multiple crews", validation_errors)
            
            # Prepare data structure
            data = {
                "crews": crews,
                "metadata": {
                    "version": "enhanced_v1.1",
                    "last_modified": datetime.datetime.now().isoformat(),
                    "guild_id": guild.id,
                    "guild_name": guild.name,
                    "crew_count": len(crews),
                    "backup_created": backup_success
                }
            }
            
            # Atomic save operation
            success = await self._atomic_save(guild.id, data)
            
            if success:
                duration = (datetime.datetime.now() - start_time).total_seconds()
                file_path = self.crews_dir / f"{guild.id}.json"
                file_size = file_path.stat().st_size if file_path.exists() else 0
                
                self.logger.log_data_operation(
                    "save_crew_data", guild.id, True,
                    crew_count=len(crews),
                    file_size=file_size,
                    duration=duration
                )
            
            return success
            
        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.logger.log_error_with_context(
                e, "save_crew_data", guild.id,
                duration=duration,
                crew_count=len(crews)
            )
            return False
    
    async def load_crew_data(self, guild: discord.Guild) -> Dict[str, Dict[str, Any]]:
        """
        Load and validate crew data with automatic migration
        Returns crew data dictionary or empty dict if loading fails
        """
        start_time = datetime.datetime.now()
        
        try:
            file_path = self.crews_dir / f"{guild.id}.json"
            
            if not file_path.exists():
                self.logger.info(f"No data file found for guild {guild.name} ({guild.id})")
                return {}
            
            # Load data
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract metadata and crews
            metadata = data.get("metadata", {})
            version = metadata.get("version", "legacy")
            crew_data = data.get("crews", {})
            
            # Validate and migrate data
            crews = {}
            migration_count = 0
            
            for name, crew_dict in crew_data.items():
                try:
                    # Validate basic structure
                    is_valid, errors = self.validate_crew_data(crew_dict)
                    if not is_valid:
                        self.logger.warning(f"Validation errors for crew {name}: {errors}")
                        # Continue loading but with warnings
                    
                    # Migrate data if needed
                    migrated_crew = self._migrate_crew_data(crew_dict, version)
                    if migrated_crew != crew_dict:
                        migration_count += 1
                    
                    crews[name] = migrated_crew
                    
                except Exception as e:
                    self.logger.log_error_with_context(
                        e, f"load_crew_data for crew {name}", guild.id
                    )
                    continue
            
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            self.logger.log_data_operation(
                "load_crew_data", guild.id, True,
                crew_count=len(crews),
                data_version=version,
                migrations=migration_count,
                duration=duration
            )
            
            # Save migrated data if changes were made
            if migration_count > 0:
                self.logger.info(f"Migrated {migration_count} crews for guild {guild.id}")
                await self.save_crew_data(guild, crews)
            
            return crews
            
        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.logger.log_error_with_context(
                e, "load_crew_data", guild.id,
                duration=duration
            )
            return {}
    
    async def create_backup(self, guild: discord.Guild) -> bool:
        """
        Create a timestamped backup of current crew data
        Returns True if successful, False otherwise
        """
        try:
            source_file = self.crews_dir / f"{guild.id}.json"
            if not source_file.exists():
                return True  # No data to backup
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{guild.id}_{timestamp}.json"
            
            # Copy file with metadata
            shutil.copy2(source_file, backup_file)
            
            # Add backup metadata
            backup_metadata = {
                "original_file": str(source_file),
                "backup_created": datetime.datetime.now().isoformat(),
                "guild_id": guild.id,
                "guild_name": guild.name,
                "file_size": source_file.stat().st_size
            }
            
            metadata_file = backup_file.with_suffix('.meta.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(backup_metadata, f, indent=2)
            
            # Clean up old backups
            await self._cleanup_old_backups(guild.id)
            
            self.logger.log_data_operation(
                "create_backup", guild.id, True,
                backup_file=backup_file.name,
                file_size=source_file.stat().st_size
            )
            
            return True
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, "create_backup", guild.id
            )
            raise BackupError("create", str(e))
    
    async def restore_backup(self, guild: discord.Guild, backup_timestamp: str) -> bool:
        """
        Restore crew data from a specific backup
        Returns True if successful, False otherwise
        """
        try:
            backup_file = self.backup_dir / f"{guild.id}_{backup_timestamp}.json"
            
            if not backup_file.exists():
                raise BackupError("restore", f"Backup file not found: {backup_file}")
            
            # Create backup of current data first
            current_backup = await self.create_backup(guild)
            if not current_backup:
                self.logger.warning("Failed to backup current data before restore")
            
            # Copy backup to main location
            target_file = self.crews_dir / f"{guild.id}.json"
            shutil.copy2(backup_file, target_file)
            
            self.logger.log_data_operation(
                "restore_backup", guild.id, True,
                backup_timestamp=backup_timestamp,
                backup_file=backup_file.name
            )
            
            return True
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, "restore_backup", guild.id,
                backup_timestamp=backup_timestamp
            )
            return False
    
    def list_backups(self, guild: discord.Guild) -> List[Dict[str, Any]]:
        """
        List all available backups for a guild
        Returns list of backup information dictionaries
        """
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob(f"{guild.id}_*.json"):
                if backup_file.name.endswith('.meta.json'):
                    continue
                
                # Extract timestamp from filename
                timestamp_part = backup_file.stem.split('_', 1)[1]
                
                # Get file info
                file_stat = backup_file.stat()
                backup_info = {
                    "timestamp": timestamp_part,
                    "file_name": backup_file.name,
                    "file_size": file_stat.st_size,
                    "created_at": datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "readable_date": datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Try to load metadata if available
                meta_file = backup_file.with_suffix('.meta.json')
                if meta_file.exists():
                    try:
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            backup_info.update(metadata)
                    except:
                        pass  # Continue without metadata
                
                backups.append(backup_info)
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, "list_backups", guild.id
            )
            return []
    
    def validate_crew_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate crew data structure and content
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in REQUIRED_CREW_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate specific field types and values
        if 'name' in data:
            if not isinstance(data['name'], str) or not data['name'].strip():
                errors.append("Name must be a non-empty string")
            elif len(data['name']) > 100:
                errors.append("Name must be 100 characters or less")
        
        if 'emoji' in data:
            if not isinstance(data['emoji'], str):
                errors.append("Emoji must be a string")
        
        if 'members' in data:
            if not isinstance(data['members'], list):
                errors.append("Members field must be a list")
            else:
                for i, member in enumerate(data['members']):
                    if not isinstance(member, int):
                        errors.append(f"Member at index {i} must be an integer (user ID)")
                    elif member <= 0:
                        errors.append(f"Member at index {i} has invalid user ID")
        
        # Validate role IDs
        role_fields = ['captain_role', 'vice_captain_role', 'crew_role']
        for field in role_fields:
            if field in data:
                if not isinstance(data[field], int) or data[field] <= 0:
                    errors.append(f"{field} must be a positive integer")
        
        # Validate stats
        if 'stats' in data:
            stats = data['stats']
            if not isinstance(stats, dict):
                errors.append("Stats field must be a dictionary")
            else:
                stat_fields = ['wins', 'losses', 'tournaments_won', 'tournaments_participated']
                for field in stat_fields:
                    if field in stats:
                        if not isinstance(stats[field], int) or stats[field] < 0:
                            errors.append(f"Stats.{field} must be a non-negative integer")
        
        # Validate timestamps
        if 'created_at' in data:
            try:
                datetime.datetime.fromisoformat(data['created_at'])
            except ValueError:
                errors.append("created_at must be a valid ISO format timestamp")
        
        return len(errors) == 0, errors
    
    async def _atomic_save(self, guild_id: int, data: Dict[str, Any]) -> bool:
        """
        Perform atomic save operation using temporary file
        Returns True if successful, False otherwise
        """
        try:
            target_file = self.crews_dir / f"{guild_id}.json"
            temp_file = self.temp_dir / f"{guild_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.tmp"
            
            # Write to temporary file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Verify the temporary file was written correctly
            with open(temp_file, 'r', encoding='utf-8') as f:
                verification_data = json.load(f)
                if verification_data != data:
                    raise DataCorruptionError("Data verification failed after write")
            
            # Atomic rename operation
            temp_file.rename(target_file)
            
            return True
            
        except Exception as e:
            # Clean up temporary file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise e
    
    def _migrate_crew_data(self, crew_dict: Dict[str, Any], version: str) -> Dict[str, Any]:
        """
        Migrate crew data from older versions to current format
        Returns migrated data dictionary
        """
        migrated = crew_dict.copy()
        
        # Migration from legacy to enhanced_v1
        if version == "legacy":
            # Generate tag if missing
            if 'tag' not in migrated and migrated.get('name'):
                words = migrated['name'].split()
                migrated['tag'] = "".join(word[0] for word in words if word).upper()[:4]
            
            # Ensure stats structure
            if 'stats' not in migrated:
                migrated['stats'] = {
                    "wins": 0,
                    "losses": 0,
                    "tournaments_won": 0,
                    "tournaments_participated": 0
                }
            
            # Add missing fields with defaults
            if 'created_at' not in migrated:
                migrated['created_at'] = datetime.datetime.now().isoformat()
            
            if 'description' not in migrated:
                migrated['description'] = ""
        
        # Migration from enhanced_v1 to enhanced_v1.1
        if version in ["legacy", "enhanced_v1"]:
            # Add enhanced member tracking if missing
            if 'enhanced_members' not in migrated:
                migrated['enhanced_members'] = []
                
                # Convert legacy members to enhanced format
                for member_id in migrated.get('members', []):
                    migrated['enhanced_members'].append({
                        "user_id": member_id,
                        "joined_at": migrated.get('created_at', datetime.datetime.now().isoformat()),
                        "role": "member",
                        "battles_participated": 0,
                        "last_active": migrated.get('created_at', datetime.datetime.now().isoformat())
                    })
            
            # Add color field if missing
            if 'color' not in migrated:
                migrated['color'] = None
        
        return migrated
    
    async def _cleanup_old_backups(self, guild_id: int):
        """Remove old backup files beyond retention period"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(
                days=CrewSettings.BACKUP_RETENTION_DAYS
            )
            
            removed_count = 0
            for backup_file in self.backup_dir.glob(f"{guild_id}_*.json"):
                if backup_file.name.endswith('.meta.json'):
                    continue
                
                file_time = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    # Remove both backup file and metadata
                    backup_file.unlink()
                    
                    meta_file = backup_file.with_suffix('.meta.json')
                    if meta_file.exists():
                        meta_file.unlink()
                    
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.log_data_operation(
                    "cleanup_old_backups", guild_id, True,
                    removed_count=removed_count
                )
                
        except Exception as e:
            self.logger.log_error_with_context(
                e, "cleanup_old_backups", guild_id
            )
    
    async def export_crew_data(self, guild: discord.Guild, format_type: str = "json") -> Optional[Path]:
        """
        Export crew data in specified format for external use
        Returns path to exported file or None if failed
        """
        try:
            crews = await self.load_crew_data(guild)
            if not crews:
                return None
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format_type.lower() == "json":
                export_file = self.temp_dir / f"crew_export_{guild.id}_{timestamp}.json"
                
                export_data = {
                    "guild_info": {
                        "id": guild.id,
                        "name": guild.name,
                        "exported_at": datetime.datetime.now().isoformat()
                    },
                    "crews": crews,
                    "export_metadata": {
                        "format": "json",
                        "version": "enhanced_v1.1",
                        "crew_count": len(crews),
                        "total_members": sum(len(crew.get('members', [])) for crew in crews.values())
                    }
                }
                
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            elif format_type.lower() == "csv":
                import csv
                export_file = self.temp_dir / f"crew_export_{guild.id}_{timestamp}.csv"
                
                with open(export_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'crew_name', 'emoji', 'tag', 'member_count', 
                        'wins', 'losses', 'win_rate', 'tournaments_won', 
                        'tournaments_participated', 'created_at'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for crew_name, crew_data in crews.items():
                        stats = CrewStats.from_dict(crew_data.get('stats', {}))
                        writer.writerow({
                            'crew_name': crew_name,
                            'emoji': crew_data.get('emoji', ''),
                            'tag': crew_data.get('tag', ''),
                            'member_count': len(crew_data.get('members', [])),
                            'wins': stats.wins,
                            'losses': stats.losses,
                            'win_rate': f"{stats.win_rate:.1f}%",
                            'tournaments_won': stats.tournaments_won,
                            'tournaments_participated': stats.tournaments_participated,
                            'created_at': crew_data.get('created_at', '')
                        })
            
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            self.logger.log_data_operation(
                "export_crew_data", guild.id, True,
                format=format_type,
                crew_count=len(crews),
                export_file=export_file.name
            )
            
            return export_file
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, "export_crew_data", guild.id,
                format_type=format_type
            )
            return None
    
    async def import_crew_data(
        self, 
        guild: discord.Guild, 
        import_file: Path, 
        merge_mode: bool = False
    ) -> Tuple[bool, str, int]:
        """
        Import crew data from file
        Returns (success, message, crews_imported)
        """
        try:
            if not import_file.exists():
                return False, "Import file not found", 0
            
            # Create backup before importing
            backup_success = await self.create_backup(guild)
            if not backup_success:
                return False, "Failed to create backup before import", 0
            
            # Load import data
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data structure
            if 'crews' not in import_data:
                return False, "Invalid import file format - missing 'crews' section", 0
            
            imported_crews = import_data['crews']
            
            # Validate each crew
            validation_errors = []
            for crew_name, crew_data in imported_crews.items():
                is_valid, errors = self.validate_crew_data(crew_data)
                if not is_valid:
                    validation_errors.extend([f"{crew_name}: {error}" for error in errors])
            
            if validation_errors:
                return False, f"Validation errors: {'; '.join(validation_errors[:5])}", 0
            
            # Load existing crews if merging
            if merge_mode:
                existing_crews = await self.load_crew_data(guild)
                # Merge imported crews with existing ones
                existing_crews.update(imported_crews)
                final_crews = existing_crews
            else:
                final_crews = imported_crews
            
            # Save the imported/merged data
            save_success = await self.save_crew_data(guild, final_crews)
            
            if save_success:
                self.logger.log_data_operation(
                    "import_crew_data", guild.id, True,
                    crews_imported=len(imported_crews),
                    merge_mode=merge_mode,
                    total_crews=len(final_crews)
                )
                
                return True, f"Successfully imported {len(imported_crews)} crews", len(imported_crews)
            else:
                return False, "Failed to save imported data", 0
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, "import_crew_data", guild.id,
                import_file=str(import_file),
                merge_mode=merge_mode
            )
            return False, f"Import failed: {str(e)}", 0
    
    def get_data_statistics(self, guild: discord.Guild) -> Dict[str, Any]:
        """Get comprehensive statistics about stored data"""
        try:
            file_path = self.crews_dir / f"{guild.id}.json"
            
            stats = {
                "guild_id": guild.id,
                "guild_name": guild.name,
                "data_file_exists": file_path.exists(),
                "file_size": 0,
                "last_modified": None,
                "backup_count": 0,
                "crew_count": 0,
                "total_members": 0,
                "data_version": "unknown"
            }
            
            if file_path.exists():
                file_stat = file_path.stat()
                stats["file_size"] = file_stat.st_size
                stats["last_modified"] = datetime.datetime.fromtimestamp(
                    file_stat.st_mtime
                ).isoformat()
                
                # Try to load basic data info
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    metadata = data.get("metadata", {})
                    crews = data.get("crews", {})
                    
                    stats["data_version"] = metadata.get("version", "legacy")
                    stats["crew_count"] = len(crews)
                    stats["total_members"] = sum(
                        len(crew.get("members", [])) for crew in crews.values()
                    )
                    
                except:
                    pass  # Continue with basic file stats
            
            # Count backups
            backup_files = list(self.backup_dir.glob(f"{guild.id}_*.json"))
            stats["backup_count"] = len([f for f in backup_files if not f.name.endswith('.meta.json')])
            
            return stats
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, "get_data_statistics", guild.id
            )
            return {"error": str(e)}