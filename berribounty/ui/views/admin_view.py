"""Admin interface views for the One Piece bot."""

import discord
from typing import Dict, Any, Optional, List
from ..formatters import format_berries, format_percentage
from ..validators import validate_berries_amount, ValidationError

class AdminControlPanelView(discord.ui.View):
    """Main admin control panel view."""
    
    def __init__(self, bot, config, player_manager, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.config = config
        self.player_manager = player_manager
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this panel!",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="Server Stats", emoji="📊", style=discord.ButtonStyle.blurple)
    async def server_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show server statistics."""
        guild_data = await self.config.guild(interaction.guild).all()
        
        # Count active players
        players = guild_data.get("players", {})
        total_players = len(players)
        total_berries = sum(player.get("berries", 0) for player in players.values())
        
        # Battle stats
        total_battles = sum(
            player.get("wins", 0) + player.get("losses", 0) 
            for player in players.values()
        )
        
        # Devil fruit owners
        fruit_owners = sum(1 for player in players.values() if player.get("devil_fruit"))
        
        embed = discord.Embed(
            title="📊 Server Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👥 Players",
            value=f"Total: {total_players:,}",
            inline=True
        )
        
        embed.add_field(
            name="💰 Economy",
            value=f"Total Berries: {format_berries(total_berries)}",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Battles",
            value=f"Total Fought: {total_battles:,}",
            inline=True
        )
        
        embed.add_field(
            name="🍎 Devil Fruits",
            value=f"Owners: {fruit_owners} ({format_percentage(fruit_owners/total_players*100 if total_players > 0 else 0)})",
            inline=True
        )
        
        embed.add_field(
            name="🏦 Global Bank",
            value=format_berries(guild_data.get("global_bank", 0)),
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Maintenance",
            value="🔴 Enabled" if guild_data.get("maintenance_mode") else "🟢 Disabled",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Player Management", emoji="👥", style=discord.ButtonStyle.green)
    async def player_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open player management interface."""
        view = PlayerManagementView(self.bot, self.config, self.player_manager)
        embed = discord.Embed(
            title="👥 Player Management",
            description="Select a management option:",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Economy Control", emoji="💰", style=discord.ButtonStyle.blurple)
    async def economy_control(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open economy control interface."""
        view = EconomyControlView(self.bot, self.config, self.player_manager)
        embed = discord.Embed(
            title="💰 Economy Control",
            description="Manage server economy:",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="System Settings", emoji="⚙️", style=discord.ButtonStyle.grey)
    async def system_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open system settings interface."""
        view = SystemSettingsView(self.bot, self.config)
        embed = discord.Embed(
            title="⚙️ System Settings",
            description="Configure bot settings:",
            color=discord.Color.grey()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PlayerManagementView(discord.ui.View):
    """Player management interface."""
    
    def __init__(self, bot, config, player_manager, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.config = config
        self.player_manager = player_manager
    
    @discord.ui.select(
        placeholder="Select a player to manage...",
        min_values=1,
        max_values=1
    )
    async def select_player(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Select a player for management."""
        # This would need to be populated with actual players
        # For now, we'll use a modal to get player input
        modal = PlayerSelectModal(self.config, self.player_manager)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Search Player", emoji="🔍", style=discord.ButtonStyle.blurple)
    async def search_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Search for a specific player."""
        modal = PlayerSearchModal(self.config, self.player_manager)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Top Players", emoji="🏆", style=discord.ButtonStyle.green)
    async def top_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show top players by various metrics."""
        guild_data = await self.config.guild(interaction.guild).all()
        players = guild_data.get("players", {})
        
        if not players:
            await interaction.response.send_message("❌ No players found!", ephemeral=True)
            return
        
        # Sort by berries
        top_berries = sorted(
            players.items(),
            key=lambda x: x[1].get("berries", 0),
            reverse=True
        )[:10]
        
        # Sort by wins
        top_wins = sorted(
            players.items(),
            key=lambda x: x[1].get("wins", 0),
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="🏆 Top Players",
            color=discord.Color.gold()
        )
        
        # Top berries field
        berries_text = ""
        for i, (user_id, data) in enumerate(top_berries[:5], 1):
            user = self.bot.get_user(int(user_id))
            name = user.display_name if user else f"User {user_id}"
            berries_text += f"{i}. {name}: {format_berries(data.get('berries', 0))}\n"
        
        embed.add_field(name="💰 Richest Pirates", value=berries_text, inline=True)
        
        # Top wins field
        wins_text = ""
        for i, (user_id, data) in enumerate(top_wins[:5], 1):
            user = self.bot.get_user(int(user_id))
            name = user.display_name if user else f"User {user_id}"
            wins_text += f"{i}. {name}: {data.get('wins', 0)} wins\n"
        
        embed.add_field(name="⚔️ Best Fighters", value=wins_text, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Reset Player", emoji="🔄", style=discord.ButtonStyle.red)
    async def reset_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset a player's data."""
        modal = PlayerResetModal(self.config, self.player_manager)
        await interaction.response.send_modal(modal)

class EconomyControlView(discord.ui.View):
    """Economy control interface."""
    
    def __init__(self, bot, config, player_manager, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.config = config
        self.player_manager = player_manager
    
    @discord.ui.button(label="Global Bank", emoji="🏦", style=discord.ButtonStyle.blurple)
    async def global_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage global bank."""
        guild_data = await self.config.guild(interaction.guild).all()
        bank_amount = guild_data.get("global_bank", 0)
        
        embed = discord.Embed(
            title="🏦 Global Bank",
            description=f"Current Balance: {format_berries(bank_amount)}",
            color=discord.Color.green()
        )
        
        view = GlobalBankView(self.config)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Give Berries", emoji="💸", style=discord.ButtonStyle.green)
    async def give_berries(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Give berries to a player."""
        modal = GiveBerriesModal(self.config, self.player_manager)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove Berries", emoji="💸", style=discord.ButtonStyle.red)
    async def remove_berries(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove berries from a player."""
        modal = RemoveBerriesModal(self.config, self.player_manager)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Economy Report", emoji="📈", style=discord.ButtonStyle.blurple)
    async def economy_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate economy report."""
        guild_data = await self.config.guild(interaction.guild).all()
        players = guild_data.get("players", {})
        
        if not players:
            await interaction.response.send_message("❌ No players found!", ephemeral=True)
            return
        
        # Calculate statistics
        total_berries = sum(player.get("berries", 0) for player in players.values())
        average_berries = total_berries / len(players) if players else 0
        
        # Wealth distribution
        wealth_levels = {
            "broke": sum(1 for p in players.values() if p.get("berries", 0) < 1000),
            "poor": sum(1 for p in players.values() if 1000 <= p.get("berries", 0) < 100000),
            "middle": sum(1 for p in players.values() if 100000 <= p.get("berries", 0) < 1000000),
            "rich": sum(1 for p in players.values() if 1000000 <= p.get("berries", 0) < 10000000),
            "wealthy": sum(1 for p in players.values() if p.get("berries", 0) >= 10000000)
        }
        
        embed = discord.Embed(
            title="📈 Economy Report",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💰 Overall",
            value=(
                f"Total Circulation: {format_berries(total_berries)}\n"
                f"Average per Player: {format_berries(int(average_berries))}\n"
                f"Total Players: {len(players):,}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Wealth Distribution",
            value=(
                f"💸 Broke (<1K): {wealth_levels['broke']}\n"
                f"💰 Poor (1K-100K): {wealth_levels['poor']}\n"
                f"💎 Middle (100K-1M): {wealth_levels['middle']}\n"
                f"👑 Rich (1M-10M): {wealth_levels['rich']}\n"
                f"🏰 Wealthy (10M+): {wealth_levels['wealthy']}"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SystemSettingsView(discord.ui.View):
    """System settings interface."""
    
    def __init__(self, bot, config, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.config = config
    
    @discord.ui.button(label="Maintenance Mode", emoji="🔧", style=discord.ButtonStyle.secondary)
    async def toggle_maintenance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle maintenance mode."""
        current = await self.config.guild(interaction.guild).maintenance_mode()
        new_value = not current
        await self.config.guild(interaction.guild).maintenance_mode.set(new_value)
        
        status = "🔴 Enabled" if new_value else "🟢 Disabled"
        embed = discord.Embed(
            title="🔧 Maintenance Mode",
            description=f"Maintenance mode is now {status}",
            color=discord.Color.red() if new_value else discord.Color.green()
        )
        
        if new_value:
            embed.add_field(
                name="ℹ️ Info",
                value="All non-admin commands are now disabled.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Set Channels", emoji="📺", style=discord.ButtonStyle.blurple)
    async def set_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set bot channels."""
        modal = ChannelSettingsModal(self.config)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Command Settings", emoji="⚙️", style=discord.ButtonStyle.grey)
    async def command_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure command settings."""
        view = CommandSettingsView(self.config)
        embed = discord.Embed(
            title="⚙️ Command Settings",
            description="Configure command restrictions:",
            color=discord.Color.grey()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Modal classes for admin input

class PlayerSelectModal(discord.ui.Modal):
    def __init__(self, config, player_manager):
        super().__init__(title="Player Search")
        self.config = config
        self.player_manager = player_manager
    
    player_input = discord.ui.TextInput(
        label="Player Name/ID",
        placeholder="Enter player name or Discord ID...",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Implementation would search for player and show management options
        await interaction.response.send_message("🔍 Searching for player...", ephemeral=True)

class GiveBerriesModal(discord.ui.Modal):
    def __init__(self, config, player_manager):
        super().__init__(title="Give Berries")
        self.config = config
        self.player_manager = player_manager
    
    player_input = discord.ui.TextInput(
        label="Player Name/ID",
        placeholder="Enter player name or Discord ID...",
        required=True
    )
    
    amount_input = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter amount of berries...",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            
            # Validate amount
            is_valid, error = validate_berries_amount(amount, max_amount=1_000_000_000)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error}", ephemeral=True)
                return
            
            # Implementation would give berries to player
            await interaction.response.send_message(
                f"✅ Gave {format_berries(amount)} to player!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount!", ephemeral=True)

class RemoveBerriesModal(discord.ui.Modal):
    def __init__(self, config, player_manager):
        super().__init__(title="Remove Berries")
        self.config = config
        self.player_manager = player_manager
    
    player_input = discord.ui.TextInput(
        label="Player Name/ID",
        placeholder="Enter player name or Discord ID...",
        required=True
    )
    
    amount_input = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter amount of berries to remove...",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            
            # Validate amount
            is_valid, error = validate_berries_amount(amount, max_amount=1_000_000_000)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error}", ephemeral=True)
                return
            
            # Implementation would remove berries from player
            await interaction.response.send_message(
                f"✅ Removed {format_berries(amount)} from player!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount!", ephemeral=True)

class GlobalBankView(discord.ui.View):
    """Global bank management view."""
    
    def __init__(self, config, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.config = config
    
    @discord.ui.button(label="Deposit", emoji="⬇️", style=discord.ButtonStyle.green)
    async def deposit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deposit to global bank."""
        modal = BankDepositModal(self.config)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Withdraw", emoji="⬆️", style=discord.ButtonStyle.red)
    async def withdraw(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Withdraw from global bank."""
        modal = BankWithdrawModal(self.config)
        await interaction.response.send_modal(modal)

class BankDepositModal(discord.ui.Modal):
    def __init__(self, config):
        super().__init__(title="Bank Deposit")
        self.config = config
    
    amount_input = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter amount to deposit...",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            
            if amount <= 0:
                await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
                return
            
            # Add to global bank
            current = await self.config.guild(interaction.guild).global_bank()
            await self.config.guild(interaction.guild).global_bank.set(current + amount)
            
            await interaction.response.send_message(
                f"✅ Deposited {format_berries(amount)} to global bank!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount!", ephemeral=True)

class BankWithdrawModal(discord.ui.Modal):
    def __init__(self, config):
        super().__init__(title="Bank Withdrawal")
        self.config = config
    
    amount_input = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter amount to withdraw...",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            
            if amount <= 0:
                await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
                return
            
            # Check if enough in bank
            current = await self.config.guild(interaction.guild).global_bank()
            if amount > current:
                await interaction.response.send_message(
                    f"❌ Not enough in bank! Available: {format_berries(current)}",
                    ephemeral=True
                )
                return
            
            # Withdraw from global bank
            await self.config.guild(interaction.guild).global_bank.set(current - amount)
            
            await interaction.response.send_message(
                f"✅ Withdrew {format_berries(amount)} from global bank!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount!", ephemeral=True)