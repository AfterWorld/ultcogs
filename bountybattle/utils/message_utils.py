class MessageUtils:
    """Utilities for message formatting and display."""
    
    def get_status_icons(self, player_data: dict) -> str:
        """Get status effect icons for display."""
        STATUS_EMOJI = {
            "burn": "🔥",
            "stun": "⚡",
            "frozen": "❄️",
            "protected": "🛡️",
            "transformed": "✨",
            "poison": "☠️",
            "bind": "🔒",
            "root": "🌿",
            "slow": "🐌",
            "dodge": "👻",
            "attack_boost": "⚔️",
            "defense_boost": "🛡️",
            "speed_boost": "💨",
            "elemental_boost": "✨",
            "thunder_charge": "⚡",
            "shell_defense": "🐢"
        }
        
        status_icons = []
        if "status" not in player_data:
            return "✨ None"
            
        for status, active in player_data["status"].items():
            if active and status in STATUS_EMOJI:
                if isinstance(active, bool) and active:
                    status_icons.append(STATUS_EMOJI[status])
                elif isinstance(active, (int, float)) and active > 0:
                    status_icons.append(f"{STATUS_EMOJI[status]}x{active}")
                    
        return " ".join(status_icons) if status_icons else "✨ None"
    
    def generate_health_bar(self, current_hp: int, max_hp: int = 250, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"
        
    def format_cooldown_time(self, seconds: int) -> str:
        """Format cooldown time into a readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}m {seconds}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"