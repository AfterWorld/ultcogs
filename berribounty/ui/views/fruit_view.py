# berribounty/ui/views/fruit_view.py
import discord
import random
import asyncio  # Add this import
from typing import Dict, Any, Optional, List
from berribounty.constants.fruits import DEVIL_FRUITS
from berribounty.managers.fruit_manager import FruitManager

class FruitSearchView(discord.ui.View):
    """Interactive view for searching devil fruits."""
    
    def __init__(self, player, fruit_manager: FruitManager, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.player = player
        self.fruit_manager = fruit_manager
        self.search_attempts = 0
        self.max_attempts = 3
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view."""
        return interaction.user == self.player.member
    
    @discord.ui.button(label="Search Island", emoji="🏝️", style=discord.ButtonStyle.green)
    async def search_island(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Search for a devil fruit on a mysterious island."""
        if self.search_attempts >= self.max_attempts:
            await interaction.response.send_message(
                "You've exhausted your search attempts for today!", 
                ephemeral=True
            )
            return
        
        self.search_attempts += 1
        
        # Calculate search success rate
        base_chance = 0.15  # 15% base chance
        berri_bonus = min(0.10, self.player.berries / 10_000_000)  # Up to 10% bonus
        total_chance = base_chance + berri_bonus
        
        # Search cost
        search_cost = 50_000 * self.search_attempts  # Increasing cost
        
        if self.player.berries < search_cost:
            await interaction.response.send_message(
                f"You need {search_cost:,} berries to search this island!", 
                ephemeral=True
            )
            return
        
        # Deduct search cost
        self.player.remove_berries(search_cost)
        
        embed = discord.Embed(title="🏝️ Searching Mysterious Island...", color=discord.Color.blue())
        embed.description = f"Search attempt {self.search_attempts}/{self.max_attempts}"
        embed.add_field(name="Cost", value=f"{search_cost:,} berries", inline=True)
        embed.add_field(name="Success Chance", value=f"{total_chance*100:.1f}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Simulate search delay
        await asyncio.sleep(3)
        
        if random.random() < total_chance:
            # Found a fruit!
            await self._handle_fruit_found(interaction)
        else:
            # No fruit found
            await self._handle_no_fruit(interaction)
    
    async def _handle_fruit_found(self, interaction: discord.Interaction):
        """Handle finding a devil fruit."""
        # Determine fruit rarity
        rare_chance = 0.1  # 10% chance for rare fruit
        is_rare = random.random() < rare_chance
        
        # Select fruit category
        if is_rare:
            available_fruits = self.fruit_manager.get_available_fruits("rare")
            category = "rare"
        else:
            available_fruits = self.fruit_manager.get_available_fruits("common")
            category = "common"
        
        if not available_fruits:
            # No fruits available in this category
            await self._handle_no_fruit(interaction)
            return
        
        # Select random fruit
        fruit_name = random.choice(available_fruits)
        fruit_data = DEVIL_FRUITS[category][fruit_name]
        
        # Create fruit selection embed
        embed = discord.Embed(
            title="🍎 Devil Fruit Found!",
            description=f"You discovered the **{fruit_name}**!",
            color=discord.Color.gold() if is_rare else discord.Color.green()
        )
        
        embed.add_field(name="Type", value=fruit_data["type"], inline=True)
        embed.add_field(name="Rarity", value=category.title(), inline=True)
        embed.add_field(name="Power", value=fruit_data["description"], inline=False)
        
        # Add special note for rare fruits
        if is_rare:
            embed.add_field(
                name="⚠️ Warning",
                value="This is a rare devil fruit! Only one person can possess it.",
                inline=False
            )
        
        # Create choice view
        choice_view = FruitChoiceView(self.player, fruit_name, self.fruit_manager)
        await interaction.edit_original_response(embed=embed, view=choice_view)
    
    async def _handle_no_fruit(self, interaction: discord.Interaction):
        """Handle not finding a fruit."""
        messages = [
            "🏝️ You searched the island thoroughly but found nothing...",
            "🌊 The waves washed away any traces of devil fruits...",
            "🐾 You found some strange animal tracks but no fruits...",
            "🗿 Ancient ruins suggest a fruit was here, but it's long gone...",
            "🌺 Beautiful flowers, but no devil fruits in sight..."
        ]
        
        message = random.choice(messages)
        
        embed = discord.Embed(
            title="No Fruit Found",
            description=message,
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="Attempts Remaining",
            value=f"{self.max_attempts - self.search_attempts}",
            inline=True
        )
        
        if self.search_attempts >= self.max_attempts:
            embed.add_field(
                name="Daily Limit Reached",
                value="Come back tomorrow for more searches!",
                inline=False
            )
            # Disable the button
            self.search_island.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Visit Market", emoji="🏪", style=discord.ButtonStyle.blurple)
    async def visit_market(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Visit the devil fruit market."""
        market_view = FruitMarketView(self.player, self.fruit_manager)
        embed = discord.Embed(
            title="🏪 Devil Fruit Market",
            description="Welcome to the Grand Line's premier devil fruit marketplace!",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed, view=market_view, ephemeral=True)
    
    @discord.ui.button(label="View Collection", emoji="📚", style=discord.ButtonStyle.grey)
    async def view_collection(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current devil fruit collection."""
        if not self.player.devil_fruit:
            embed = discord.Embed(
                title="📚 Your Collection",
                description="You haven't eaten any devil fruit yet!",
                color=discord.Color.red()
            )
        else:
            fruit_data = self.player.devil_fruit_data
            embed = discord.Embed(
                title="📚 Your Devil Fruit",
                description=f"**{self.player.devil_fruit}**",
                color=discord.Color.blue()
            )
            
            if fruit_data:
                embed.add_field(name="Type", value=fruit_data["type"], inline=True)
                embed.add_field(name="Power", value=fruit_data["description"], inline=False)
                
                if "moves" in fruit_data:
                    moves_text = "\n".join([f"• {move['name']}" for move in fruit_data["moves"][:5]])
                    embed.add_field(name="Special Moves", value=moves_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class FruitChoiceView(discord.ui.View):
    """View for choosing whether to eat a found devil fruit."""
    
    def __init__(self, player, fruit_name: str, fruit_manager: FruitManager):
        super().__init__(timeout=120.0)
        self.player = player
        self.fruit_name = fruit_name
        self.fruit_manager = fruit_manager
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view."""
        return interaction.user == self.player.member
    
    @discord.ui.button(label="Eat Fruit", emoji="🍽️", style=discord.ButtonStyle.green)
    async def eat_fruit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Eat the devil fruit."""
        # Check if player already has a fruit
        if self.player.devil_fruit:
            embed = discord.Embed(
                title="❌ Already Have Devil Fruit",
                description=f"You already have the {self.player.devil_fruit}!\nEating another would be fatal!",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        # Give fruit to player
        success = await self.fruit_manager.give_fruit(self.player, self.fruit_name)
        
        if success:
            embed = discord.Embed(
                title="🍎 Devil Fruit Consumed!",
                description=f"You have eaten the **{self.fruit_name}**!\nYou can no longer swim, but gained incredible powers!",
                color=discord.Color.gold()
            )
            
            # Add fruit abilities info
            fruit_data = self.player.devil_fruit_data
            if fruit_data and "moves" in fruit_data:
                moves_text = "\n".join([f"• {move['name']}" for move in fruit_data["moves"][:3]])
                embed.add_field(name="New Abilities", value=moves_text, inline=False)
        else:
            embed = discord.Embed(
                title="❌ Failed to Consume",
                description="Something went wrong while eating the fruit!",
                color=discord.Color.red()
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Sell Fruit", emoji="💰", style=discord.ButtonStyle.blurple)
    async def sell_fruit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sell the devil fruit for berries."""
        # Calculate fruit value
        fruit_data = None
        for category, fruits in DEVIL_FRUITS.items():
            if self.fruit_name in fruits:
                fruit_data = fruits[self.fruit_name]
                break
        
        if not fruit_data:
            await interaction.response.send_message("Error: Fruit data not found!", ephemeral=True)
            return
        
        # Base value based on rarity
        if any(self.fruit_name in fruits for fruits in [DEVIL_FRUITS["rare"]]):
            base_value = random.randint(5_000_000, 15_000_000)
        else:
            base_value = random.randint(1_000_000, 5_000_000)
        
        # Add berries to player
        self.player.add_berries(base_value)
        
        embed = discord.Embed(
            title="💰 Fruit Sold!",
            description=f"You sold the **{self.fruit_name}** for **{base_value:,}** berries!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="New Balance",
            value=f"{self.player.berries:,} berries",
            inline=True
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Keep for Later", emoji="📦", style=discord.ButtonStyle.grey)
    async def keep_fruit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Keep the fruit in inventory for later."""
        # For now, just convert to berries (simplified inventory system)
        embed = discord.Embed(
            title="📦 Fruit Stored",
            description=f"You decided to keep the **{self.fruit_name}** for later...\n*But it mysteriously disappeared!*",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="💡 Tip",
            value="Devil fruits are too rare to store safely. Next time, eat it or sell it!",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class FruitMarketView(discord.ui.View):
    """View for the devil fruit marketplace."""
    
    def __init__(self, player, fruit_manager: FruitManager):
        super().__init__(timeout=300.0)
        self.player = player
        self.fruit_manager = fruit_manager
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view."""
        return interaction.user == self.player.member
    
    @discord.ui.button(label="Browse Common Fruits", emoji="🍎", style=discord.ButtonStyle.green)
    async def browse_common(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Browse common devil fruits for sale."""
        available_fruits = self.fruit_manager.get_available_fruits("common")
        
        if not available_fruits:
            embed = discord.Embed(
                title="🍎 Common Fruits",
                description="No common devil fruits available for purchase right now!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show random selection of common fruits
        fruits_to_show = random.sample(available_fruits, min(5, len(available_fruits)))
        
        embed = discord.Embed(
            title="🍎 Common Devil Fruits",
            description="Available for purchase:",
            color=discord.Color.green()
        )
        
        for fruit_name in fruits_to_show:
            fruit_data = DEVIL_FRUITS["common"][fruit_name]
            price = random.randint(2_000_000, 8_000_000)
            embed.add_field(
                name=f"{fruit_name}",
                value=f"Type: {fruit_data['type']}\nPrice: {price:,} berries",
                inline=True
            )
        
        purchase_view = FruitPurchaseView(self.player, fruits_to_show, "common", self.fruit_manager)
        await interaction.response.send_message(embed=embed, view=purchase_view, ephemeral=True)
    
    @discord.ui.button(label="Browse Rare Fruits", emoji="💎", style=discord.ButtonStyle.red)
    async def browse_rare(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Browse rare devil fruits for sale."""
        available_fruits = self.fruit_manager.get_available_fruits("rare")
        
        if not available_fruits:
            embed = discord.Embed(
                title="💎 Rare Fruits",
                description="No rare devil fruits available for purchase right now!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show random selection of rare fruits
        fruits_to_show = random.sample(available_fruits, min(3, len(available_fruits)))
        
        embed = discord.Embed(
            title="💎 Rare Devil Fruits",
            description="Legendary powers for the worthy:",
            color=discord.Color.red()
        )
        
        for fruit_name in fruits_to_show:
            fruit_data = DEVIL_FRUITS["rare"][fruit_name]
            price = random.randint(50_000_000, 200_000_000)
            embed.add_field(
                name=f"{fruit_name}",
                value=f"Type: {fruit_data['type']}\nPrice: {price:,} berries",
                inline=True
            )
        
        purchase_view = FruitPurchaseView(self.player, fruits_to_show, "rare", self.fruit_manager)
        await interaction.response.send_message(embed=embed, view=purchase_view, ephemeral=True)

class FruitPurchaseView(discord.ui.View):
   """View for purchasing devil fruits."""
   
   def __init__(self, player, fruits: List[str], category: str, fruit_manager: FruitManager):
       super().__init__(timeout=180.0)
       self.player = player
       self.fruits = fruits
       self.category = category
       self.fruit_manager = fruit_manager
       
       # Create select menu with fruits
       options = []
       for fruit_name in fruits:
           fruit_data = DEVIL_FRUITS[category][fruit_name]
           if category == "rare":
               price = random.randint(50_000_000, 200_000_000)
           else:
               price = random.randint(2_000_000, 8_000_000)
           
           options.append(
               discord.SelectOption(
                   label=fruit_name,
                   description=f"{fruit_data['type']} - {price:,} berries",
                   emoji="💎" if category == "rare" else "🍎",
                   value=f"{fruit_name}|{price}"
               )
           )
       
       self.fruit_select.options = options
   
   async def interaction_check(self, interaction: discord.Interaction) -> bool:
       """Check if user can interact with this view."""
       return interaction.user == self.player.member
   
   @discord.ui.select(placeholder="Choose a fruit to purchase...")
   async def fruit_select(self, interaction: discord.Interaction, select: discord.ui.Select):
       """Handle fruit selection for purchase."""
       fruit_name, price_str = select.values[0].split("|")
       price = int(price_str)
       
       # Check if player already has a fruit
       if self.player.devil_fruit:
           embed = discord.Embed(
               title="❌ Already Have Devil Fruit",
               description=f"You already have the {self.player.devil_fruit}!",
               color=discord.Color.red()
           )
           await interaction.response.send_message(embed=embed, ephemeral=True)
           return
       
       # Check if player has enough berries
       if self.player.berries < price:
           embed = discord.Embed(
               title="❌ Insufficient Berries",
               description=f"You need {price:,} berries but only have {self.player.berries:,}!",
               color=discord.Color.red()
           )
           await interaction.response.send_message(embed=embed, ephemeral=True)
           return
       
       # Confirm purchase
       confirm_view = ConfirmPurchaseView(self.player, fruit_name, price, self.fruit_manager)
       
       fruit_data = DEVIL_FRUITS[self.category][fruit_name]
       embed = discord.Embed(
           title="🍎 Confirm Purchase",
           description=f"**{fruit_name}**\n*{fruit_data['description']}*",
           color=discord.Color.gold()
       )
       
       embed.add_field(name="Type", value=fruit_data["type"], inline=True)
       embed.add_field(name="Price", value=f"{price:,} berries", inline=True)
       embed.add_field(name="Your Berries", value=f"{self.player.berries:,}", inline=True)
       
       embed.add_field(
           name="⚠️ Warning",
           value="Devil fruits cannot be undone! You will lose the ability to swim forever!",
           inline=False
       )
       
       await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class ConfirmPurchaseView(discord.ui.View):
   """View for confirming devil fruit purchase."""
   
   def __init__(self, player, fruit_name: str, price: int, fruit_manager: FruitManager):
       super().__init__(timeout=60.0)
       self.player = player
       self.fruit_name = fruit_name
       self.price = price
       self.fruit_manager = fruit_manager
   
   async def interaction_check(self, interaction: discord.Interaction) -> bool:
       """Check if user can interact with this view."""
       return interaction.user == self.player.member
   
   @discord.ui.button(label="Confirm Purchase", emoji="✅", style=discord.ButtonStyle.green)
   async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
       """Confirm the fruit purchase."""
       # Double-check player has enough berries and no existing fruit
       if self.player.berries < self.price:
           await interaction.response.send_message("❌ Insufficient berries!", ephemeral=True)
           return
       
       if self.player.devil_fruit:
           await interaction.response.send_message("❌ You already have a devil fruit!", ephemeral=True)
           return
       
       # Process purchase
       self.player.remove_berries(self.price)
       success = await self.fruit_manager.give_fruit(self.player, self.fruit_name)
       
       if success:
           embed = discord.Embed(
               title="🎉 Purchase Successful!",
               description=f"You have acquired the **{self.fruit_name}**!",
               color=discord.Color.green()
           )
           
           embed.add_field(name="Berries Spent", value=f"{self.price:,}", inline=True)
           embed.add_field(name="Remaining Berries", value=f"{self.player.berries:,}", inline=True)
           
           # Add fruit abilities info
           fruit_data = self.player.devil_fruit_data
           if fruit_data and "moves" in fruit_data:
               moves_text = "\n".join([f"• {move['name']}" for move in fruit_data["moves"][:3]])
               embed.add_field(name="New Abilities", value=moves_text, inline=False)
       else:
           # Refund if something went wrong
           self.player.add_berries(self.price)
           embed = discord.Embed(
               title="❌ Purchase Failed",
               description="Something went wrong with your purchase. Berries have been refunded.",
               color=discord.Color.red()
           )
       
       await interaction.response.edit_message(embed=embed, view=None)
   
   @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.red)
   async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
       """Cancel the fruit purchase."""
       embed = discord.Embed(
           title="❌ Purchase Cancelled",
           description="You decided not to purchase the devil fruit.",
           color=discord.Color.orange()
       )
       
       await interaction.response.edit_message(embed=embed, view=None)
