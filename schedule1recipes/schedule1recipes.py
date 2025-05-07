import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core import Config
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Optional

# Constants
SCHEDULE1_CALCULATOR_URL = "https://schedule1-calculator.net"
RECIPES_ENDPOINT = "/api/recipes"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

class Schedule1Recipes(commands.Cog):
    """Get top drug recipes from Schedule 1 game"""
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=897123549, force_registration=True
        )
        # Default settings
        default_global = {
            "cache_lifetime": 3600,  # Cache for 1 hour
        }
        self.config.register_global(**default_global)
        
        self.recipes_cache = {}
        self.last_cache_update = 0
        self.cache_lifetime = 3600  # Cache for 1 hour
        self.session = None
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.session:
            await self.session.close()
    
    async def red_delete_data_for_user(self, *, requester, user_id):
        """Nothing to delete"""
        pass
    
    async def get_recipes(self, force_refresh=False):
        """Get recipes from the website or cache"""
        current_time = asyncio.get_event_loop().time()
        
        # Return cached recipes if they're still valid
        if not force_refresh and self.recipes_cache and (current_time - self.last_cache_update < self.cache_lifetime):
            return self.recipes_cache
        
        recipes = await self.fetch_recipes_from_website()
        
        if recipes:
            self.recipes_cache = recipes
            self.last_cache_update = current_time
        
        return recipes
    
    async def fetch_recipes_from_website(self):
        """Fetch recipes from the website through scraping"""
        try:
            # Try to fetch from the API endpoint first (if it exists)
            async with self.session.get(
                f"{SCHEDULE1_CALCULATOR_URL}{RECIPES_ENDPOINT}",
                headers={"User-Agent": USER_AGENT}
            ) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        return self.process_api_data(data)
                    except:
                        # If it's not JSON, fall back to scraping
                        pass
            
            # Fall back to scraping the website
            async with self.session.get(
                SCHEDULE1_CALCULATOR_URL,
                headers={"User-Agent": USER_AGENT}
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    return self.scrape_recipes(html)
                else:
                    return self.get_fallback_recipes()
        except Exception:
            return self.get_fallback_recipes()
    
    def process_api_data(self, data):
        """Process API data if the endpoint returned JSON"""
        recipes = []
        
        # This is a placeholder since we don't know the exact API structure
        # Adjust according to the actual API response
        if isinstance(data, list):
            for recipe in data:
                if isinstance(recipe, dict) and 'name' in recipe and 'ingredients' in recipe:
                    recipes.append(recipe)
        elif isinstance(data, dict) and 'recipes' in data:
            for recipe in data['recipes']:
                if isinstance(recipe, dict) and 'name' in recipe and 'ingredients' in recipe:
                    recipes.append(recipe)
        
        return recipes if recipes else self.get_fallback_recipes()
    
    def scrape_recipes(self, html):
        """Scrape recipes from the website HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        recipes = []
        
        # Look for recipe tables or containers
        # This is a generic approach since we don't know the exact HTML structure
        recipe_containers = soup.select('.recipe-card, .recipe-container, .mix-info')
        
        if recipe_containers:
            for container in recipe_containers:
                recipe = {}
                
                # Try to find recipe name
                name_elem = container.select_one('.recipe-name, .mix-name, h3, h2')
                if name_elem:
                    recipe['name'] = name_elem.text.strip()
                else:
                    continue  # Skip if no name found
                
                # Try to find base product
                base_elem = container.select_one('.base-product, .drug-type')
                if base_elem:
                    recipe['base'] = base_elem.text.strip()
                
                # Try to find ingredients
                ingredient_elems = container.select('.ingredient, .ingredient-item, .mix-ingredient')
                if ingredient_elems:
                    recipe['ingredients'] = [elem.text.strip() for elem in ingredient_elems]
                
                # Try to find effects
                effect_elems = container.select('.effect, .effect-item, .mix-effect')
                if effect_elems:
                    recipe['effects'] = [elem.text.strip() for elem in effect_elems]
                
                # Try to find value
                value_elem = container.select_one('.value, .price, .mix-value')
                if value_elem:
                    try:
                        value_text = value_elem.text.strip()
                        # Extract numeric value
                        value = ''.join(c for c in value_text if c.isdigit() or c == '.')
                        recipe['value'] = float(value) if value else 0
                    except:
                        recipe['value'] = 0
                
                recipes.append(recipe)
        
        return recipes if recipes else self.get_fallback_recipes()
    
    def get_fallback_recipes(self):
        """Return hardcoded fallback recipes if website scraping fails"""
        return [
            {
                "name": "Miracle Mix",
                "base": "Sour Diesel",
                "ingredients": ["Flu Medicine", "Energy Drink", "Chili", "Flu Medicine", "Mouthwash", "Banana", "Iodine", "Horsemen"],
                "effects": ["Energizing", "Refreshing", "Spicy", "Bright-Eyed", "Calming", "Gingeritis", "Laxative", "Explosive"],
                "value": 200
            },
            {
                "name": "Ice Cream Slime",
                "base": "Green Crack",
                "ingredients": ["Mouthwash", "Banana", "Vitamin"],
                "effects": ["Focused", "Calming", "Gingeritis", "Refreshing"],
                "value": 120
            },
            {
                "name": "Pure Profit",
                "base": "OG Kush",
                "ingredients": ["Banana", "Chili"],
                "effects": ["Calming", "Gingeritis", "Spicy"],
                "value": 80
            },
            {
                "name": "Wedding Cake",
                "base": "Granddaddy Purple",
                "ingredients": ["Viagra", "Energy Drink"],
                "effects": ["Sedating", "Tropic Thunder", "Munchies"],
                "value": 150
            },
            {
                "name": "Cocaine Supreme",
                "base": "Pure Coke",
                "ingredients": ["Vitamin", "Battery", "Chili"],
                "effects": ["Energizing", "Euphoric", "Addictive", "Refreshing", "Bright-Eyed", "Spicy"],
                "value": 300
            }
        ]
    
    def filter_recipes_by_type(self, recipes, drug_type):
        """Filter recipes by drug type"""
        if not drug_type:
            return recipes
        
        drug_type = drug_type.lower()
        return [r for r in recipes if 
                ('base' in r and r['base'].lower().find(drug_type) != -1) or
                ('name' in r and r['name'].lower().find(drug_type) != -1)]
    
    def sort_recipes_by_value(self, recipes, descending=True):
        """Sort recipes by value"""
        return sorted(recipes, key=lambda r: r.get('value', 0), reverse=descending)
    
    @commands.command(name="topbud")
    async def top_bud(self, ctx, *, drug_type: str = None):
        """
        Get the top bud recipe from Schedule 1 game
        
        Examples:
            [p]topbud
            [p]topbud Sour Diesel
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                await ctx.send("I couldn't find any recipes at the moment. Try again later.")
                return
            
            # Filter by drug type if specified
            if drug_type:
                filtered_recipes = self.filter_recipes_by_type(recipes, drug_type)
                if not filtered_recipes:
                    await ctx.send(f"I couldn't find any recipes for '{drug_type}'. Try another type or leave it blank for all recipes.")
                    return
                recipes = filtered_recipes
            
            # Sort by value and get the top one
            sorted_recipes = self.sort_recipes_by_value(recipes)
            top_recipe = sorted_recipes[0] if sorted_recipes else None
            
            if not top_recipe:
                await ctx.send("I couldn't find any top recipes at the moment. Try again later.")
                return
            
            # Create an embed for the top recipe
            embed = discord.Embed(
                title=f"🌿 Top Bud: {top_recipe.get('name', 'Unknown Mix')}",
                description=f"The most profitable bud recipe currently available",
                color=0x00FF00
            )
            
            # Add base product field
            if 'base' in top_recipe:
                embed.add_field(
                    name="Base Product",
                    value=top_recipe['base'],
                    inline=True
                )
            
            # Add value field
            embed.add_field(
                name="Value",
                value=f"${top_recipe.get('value', 0):,.2f}",
                inline=True
            )
            
            # Add ingredients field
            if 'ingredients' in top_recipe and top_recipe['ingredients']:
                ingredients_text = "\n".join([f"• {ing}" for ing in top_recipe['ingredients']])
                embed.add_field(
                    name="Ingredients",
                    value=ingredients_text,
                    inline=False
                )
            
            # Add effects field
            if 'effects' in top_recipe and top_recipe['effects']:
                effects_text = ", ".join(top_recipe['effects'])
                embed.add_field(
                    name="Effects",
                    value=effects_text,
                    inline=False
                )
            
            # Add footer
            embed.set_footer(text="Data from Schedule1-Calculator.net")
            
            # Need to use Red's more traditional menu system
            await ctx.send(embed=embed)
    
    @commands.command(name="s1recipes", aliases=["recipes", "buds"])
    async def all_recipes(self, ctx, *, drug_type: str = None):
        """
        Get a list of recipes from Schedule 1 game
        
        Examples:
            [p]s1recipes
            [p]recipes OG Kush
            [p]buds Green
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                await ctx.send("I couldn't find any recipes at the moment. Try again later.")
                return
            
            # Filter by drug type if specified
            if drug_type:
                filtered_recipes = self.filter_recipes_by_type(recipes, drug_type)
                if not filtered_recipes:
                    await ctx.send(f"I couldn't find any recipes for '{drug_type}'. Try another type or leave it blank for all recipes.")
                    return
                recipes = filtered_recipes
            
            # Sort by value
            sorted_recipes = self.sort_recipes_by_value(recipes)
            
            # Paginate recipes (5 per page)
            page_size = 5
            pages = []
            
            for i in range(0, len(sorted_recipes), page_size):
                page_recipes = sorted_recipes[i:i+page_size]
                
                embed = discord.Embed(
                    title=f"🌿 Schedule 1 Recipes",
                    description=f"Page {i//page_size + 1}/{(len(sorted_recipes) + page_size - 1) // page_size}" + 
                                (f" - Type: {drug_type}" if drug_type else ""),
                    color=0x00FF00
                )
                
                for j, recipe in enumerate(page_recipes, i + 1):
                    embed.add_field(
                        name=f"#{j}: {recipe.get('name', 'Unknown Mix')}",
                        value=(
                            f"Base: {recipe.get('base', 'Unknown')}\n"
                            f"Value: ${recipe.get('value', 0):,.2f}\n"
                            f"Ingredients: {len(recipe.get('ingredients', []))}\n"
                        ),
                        inline=False
                    )
                
                embed.set_footer(text="Data from Schedule1-Calculator.net")
                pages.append(embed)
            
            if not pages:
                await ctx.send("No recipes found.")
                return
            
            # Use Red's menu system for pagination
            await menu(ctx, pages, DEFAULT_CONTROLS)
    
    @commands.command(name="recipedetails", aliases=["s1recipe", "recipedeets"])
    async def recipe_details(self, ctx, *, recipe_name: str):
        """
        Show detailed information about a specific recipe
        
        Examples:
            [p]recipedetails Miracle Mix
            [p]s1recipe Ice Cream Slime
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                await ctx.send("I couldn't find any recipes at the moment. Try again later.")
                return
            
            # Find the recipe by name (case-insensitive partial match)
            name_lower = recipe_name.lower()
            matching_recipes = [r for r in recipes if name_lower in r.get('name', '').lower()]
            
            if not matching_recipes:
                await ctx.send(f"I couldn't find any recipe matching '{recipe_name}'. Try a different name.")
                return
            
            # Get the best match (most similar name)
            recipe = min(matching_recipes, key=lambda r: abs(len(r.get('name', '')) - len(recipe_name)))
            
            # Create an embed for the recipe details
            embed = discord.Embed(
                title=f"🧪 Recipe Details: {recipe.get('name', 'Unknown Mix')}",
                description=f"Complete details for this recipe",
                color=0x00FF00
            )
            
            # Add base product field
            if 'base' in recipe:
                embed.add_field(
                    name="Base Product",
                    value=recipe['base'],
                    inline=True
                )
            
            # Add value field
            embed.add_field(
                name="Value",
                value=f"${recipe.get('value', 0):,.2f}",
                inline=True
            )
            
            # Add ingredients field
            if 'ingredients' in recipe and recipe['ingredients']:
                ingredients_text = "\n".join([f"• {ing}" for ing in recipe['ingredients']])
                embed.add_field(
                    name="Ingredients",
                    value=ingredients_text,
                    inline=False
                )
            
            # Add effects field
            if 'effects' in recipe and recipe['effects']:
                effects_text = ", ".join(recipe['effects'])
                embed.add_field(
                    name="Effects",
                    value=effects_text,
                    inline=False
                )
            
            # Add mixing instructions
            if 'ingredients' in recipe and recipe['ingredients']:
                instructions = [
                    f"1. Start with {recipe.get('base', 'base product')}"
                ]
                
                for i, ingredient in enumerate(recipe.get('ingredients', []), 2):
                    instructions.append(f"{i}. Add {ingredient}")
                
                embed.add_field(
                    name="Mixing Instructions",
                    value="\n".join(instructions),
                    inline=False
                )
            
            embed.set_footer(text="Data from Schedule1-Calculator.net")
            
            await ctx.send(embed=embed)

async def setup(bot):
    cog = Schedule1Recipes(bot)
    await bot.add_cog(cog)
