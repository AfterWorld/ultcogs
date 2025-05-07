import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box, humanize_list
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union

# Constants
SCHEDULE1_CALCULATOR_URL = "https://schedule1-calculator.net"
RECIPES_ENDPOINT = "/api/recipes"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

class Schedule1Recipes(commands.Cog):
    """Enhanced tools for Schedule 1 game recipes and calculations"""
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=897123549, force_registration=True
        )
        
        # Default settings
        default_global = {
            "cache_lifetime": 3600,  # Cache for 1 hour
            "last_update_check": 0,
            "last_known_recipes": [],
        }
        
        default_user = {
            "favorites": [],
        }
        
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        
        self.recipes_cache = {}
        self.last_cache_update = 0
        self.cache_lifetime = 3600  # Cache for 1 hour
        self.session = None
        
        # Set up scheduled tasks
        self.recipe_refresh_task = None
        self.update_check_task = None
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.session = aiohttp.ClientSession()
        
        # Schedule the tasks for cache refreshing and game update checks
        self.recipe_refresh_task = self.bot.loop.create_task(self.scheduled_cache_refresh())
        self.update_check_task = self.bot.loop.create_task(self.scheduled_update_check())
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.session:
            await self.session.close()
        
        # Cancel the scheduled tasks
        if self.recipe_refresh_task:
            self.recipe_refresh_task.cancel()
        
        if self.update_check_task:
            self.update_check_task.cancel()
    
    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete user data when requested"""
        await self.config.user_from_id(user_id).clear()
    
    async def scheduled_cache_refresh(self):
        """Task to periodically refresh the recipe cache"""
        await self.bot.wait_until_ready()
        while True:
            try:
                # Refresh the cache
                await self.get_recipes(force_refresh=True)
                # Wait for the configured cache lifetime before refreshing again
                await asyncio.sleep(self.cache_lifetime)
            except asyncio.CancelledError:
                # Handle task cancellation
                break
            except Exception as e:
                # Log any errors but keep the task running
                print(f"Error refreshing recipe cache: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def scheduled_update_check(self):
        """Task to check for game updates"""
        await self.bot.wait_until_ready()
        while True:
            try:
                # Check for updates once a day
                await self.check_for_game_updates()
                await asyncio.sleep(86400)  # 24 hours
            except asyncio.CancelledError:
                # Handle task cancellation
                break
            except Exception as e:
                # Log any errors but keep the task running
                print(f"Error checking for game updates: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(3600)  # 1 hour
    
    async def check_for_game_updates(self):
        """Check if the game has been updated with new recipes"""
        # Get current recipes
        current_recipes = await self.get_recipes(force_refresh=True)
        
        # Get last known recipes
        last_known_recipes = await self.config.last_known_recipes()
        
        # Compare the number of recipes or specific recipe names
        current_recipe_names = sorted([r.get('name', '') for r in current_recipes])
        last_known_recipe_names = sorted([r.get('name', '') for r in last_known_recipes])
        
        if current_recipe_names != last_known_recipe_names:
            # Save the new recipes
            await self.config.last_known_recipes.set(current_recipes)
            await self.config.last_update_check.set(int(datetime.now().timestamp()))
            
            # Find new recipes
            new_recipes = [r for r in current_recipes if r.get('name', '') not in last_known_recipe_names]
            
            if new_recipes:
                # Notify designated channels about the update
                for guild in self.bot.guilds:
                    try:
                        # You could add a config option to specify which channel to notify
                        system_channel = guild.system_channel
                        if system_channel and system_channel.permissions_for(guild.me).send_messages:
                            embed = discord.Embed(
                                title="🆕 Schedule 1 Game Update Detected!",
                                description=f"Found {len(new_recipes)} new recipes in the game!",
                                color=0x00FF00
                            )
                            
                            # Show up to 5 new recipes
                            for i, recipe in enumerate(new_recipes[:5]):
                                embed.add_field(
                                    name=f"New Recipe: {recipe.get('name', 'Unknown')}",
                                    value=f"Base: {recipe.get('base', 'Unknown')}\nValue: ${recipe.get('value', 0):,.2f}",
                                    inline=False
                                )
                            
                            if len(new_recipes) > 5:
                                embed.set_footer(text=f"And {len(new_recipes) - 5} more new recipes! Use [p]s1 recipes to see all.")
                            else:
                                embed.set_footer(text="Use [p]s1 recipes to see details.")
                            
                            await system_channel.send(embed=embed)
                    except Exception:
                        # Skip if we can't send to this guild
                        continue
    
    async def get_recipes(self, force_refresh=False):
        """Get recipes from the website or cache"""
        current_time = asyncio.get_event_loop().time()
        
        # Return cached recipes if they're still valid
        if not force_refresh and self.recipes_cache and (current_time - self.last_cache_update < self.cache_lifetime):
            return self.recipes_cache
        
        # Try multiple times with exponential backoff
        max_retries = 3
        for retry in range(max_retries):
            try:
                recipes = await self.fetch_recipes_from_website()
                
                if recipes:
                    self.recipes_cache = recipes
                    self.last_cache_update = current_time
                    return recipes
            except Exception as e:
                # Wait with exponential backoff before retrying
                if retry < max_retries - 1:
                    await asyncio.sleep(2 ** retry)
        
        # If all retries failed, return the cached data if available, otherwise fallback
        return self.recipes_cache if self.recipes_cache else self.get_fallback_recipes()
    
    async def fetch_recipes_from_website(self):
        """Fetch recipes from the website through multiple methods"""
        try:
            # Try to fetch from the API endpoint first
            async with self.session.get(
                f"{SCHEDULE1_CALCULATOR_URL}{RECIPES_ENDPOINT}",
                headers={"User-Agent": USER_AGENT},
                timeout=10
            ) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        recipes = self.process_api_data(data)
                        if recipes:
                            return recipes
                    except:
                        # If it's not JSON, fall back to scraping
                        pass
            
            # Try scraping the main website
            async with self.session.get(
                SCHEDULE1_CALCULATOR_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    recipes = self.scrape_recipes(html)
                    if recipes:
                        return recipes
            
            # If all methods fail, return fallback recipes
            return self.get_fallback_recipes()
        except Exception:
            return self.get_fallback_recipes()
    
    def process_api_data(self, data):
        """Process API data if the endpoint returned JSON"""
        recipes = []
        
        # Handle different possible JSON structures
        if isinstance(data, list):
            for recipe in data:
                if isinstance(recipe, dict) and 'name' in recipe:
                    recipes.append(recipe)
        elif isinstance(data, dict) and 'recipes' in data:
            for recipe in data['recipes']:
                if isinstance(recipe, dict) and 'name' in recipe:
                    recipes.append(recipe)
        elif isinstance(data, dict) and 'data' in data:
            for recipe in data['data']:
                if isinstance(recipe, dict) and 'name' in recipe:
                    recipes.append(recipe)
        
        # Ensure all recipes have the standard fields
        for recipe in recipes:
            if 'ingredients' not in recipe:
                recipe['ingredients'] = []
            if 'effects' not in recipe:
                recipe['effects'] = []
            if 'value' not in recipe:
                recipe['value'] = 0
            if 'base' not in recipe:
                recipe['base'] = "Unknown"
        
        return recipes if recipes else []
    
    def scrape_recipes(self, html):
        """Scrape recipes from the website HTML using multiple selectors for resilience"""
        soup = BeautifulSoup(html, 'html.parser')
        recipes = []
        
        # Try multiple different selectors to find recipe containers
        selectors = [
            '.recipe-card', '.recipe-container', '.mix-info', 
            '.drug-recipe', '.recipe-item', '.recipe',
            '[data-recipe]', '[class*="recipe"]', '[class*="mix"]'
        ]
        
        for selector in selectors:
            recipe_containers = soup.select(selector)
            if recipe_containers:
                for container in recipe_containers:
                    recipe = self.extract_recipe_from_element(container)
                    if recipe and 'name' in recipe:
                        recipes.append(recipe)
        
        # If specific selectors didn't work, try a more generic approach
        if not recipes:
            # Look for elements that might contain recipe info based on text
            for elem in soup.find_all(['div', 'section', 'article']):
                text = elem.get_text().lower()
                if any(term in text for term in ['recipe', 'mix', 'drug', 'ingredient', 'effect']):
                    recipe = self.extract_recipe_from_element(elem)
                    if recipe and 'name' in recipe:
                        recipes.append(recipe)
        
        return recipes if recipes else []
    
    def extract_recipe_from_element(self, element):
        """Extract recipe data from a HTML element"""
        recipe = {}
        
        # Try to find recipe name with multiple selectors
        name_selectors = ['.recipe-name', '.mix-name', 'h3', 'h2', '.title', '[class*="name"]', 'strong', 'b']
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                recipe['name'] = name_elem.text.strip()
                break
        
        # If no name found, try to get the first text node
        if 'name' not in recipe:
            text_nodes = [t for t in element.find_all(text=True) if t.strip()]
            if text_nodes:
                recipe['name'] = text_nodes[0].strip()
        
        # Skip if no name found
        if 'name' not in recipe or not recipe['name']:
            return None
        
        # Try to find base product
        base_selectors = ['.base-product', '.drug-type', '.base', '[class*="base"]']
        for selector in base_selectors:
            base_elem = element.select_one(selector)
            if base_elem:
                recipe['base'] = base_elem.text.strip()
                break
        
        if 'base' not in recipe:
            recipe['base'] = "Unknown"
        
        # Try to find ingredients
        ingredient_selectors = ['.ingredient', '.ingredient-item', '.mix-ingredient', '.component', '[class*="ingredient"]']
        for selector in ingredient_selectors:
            ingredient_elems = element.select(selector)
            if ingredient_elems:
                recipe['ingredients'] = [elem.text.strip() for elem in ingredient_elems]
                break
        
        if 'ingredients' not in recipe:
            recipe['ingredients'] = []
        
        # Try to find effects
        effect_selectors = ['.effect', '.effect-item', '.mix-effect', '[class*="effect"]']
        for selector in effect_selectors:
            effect_elems = element.select(selector)
            if effect_elems:
                recipe['effects'] = [elem.text.strip() for elem in effect_elems]
                break
        
        if 'effects' not in recipe:
            recipe['effects'] = []
        
        # Try to find value
        value_selectors = ['.value', '.price', '.mix-value', '.cost', '[class*="price"]', '[class*="value"]']
        for selector in value_selectors:
            value_elem = element.select_one(selector)
            if value_elem:
                try:
                    value_text = value_elem.text.strip()
                    # Extract numeric value
                    value_match = re.search(r'(\d+(?:\.\d+)?)', value_text)
                    if value_match:
                        recipe['value'] = float(value_match.group(1))
                    else:
                        recipe['value'] = 0
                except:
                    recipe['value'] = 0
                break
        
        if 'value' not in recipe:
            recipe['value'] = 0
        
        return recipe
    
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
    
    def filter_recipes_by_effects(self, recipes, effects):
        """Filter recipes by effects"""
        if not effects:
            return recipes
        
        effects_lower = [e.lower() for e in effects]
        return [r for r in recipes if 
                'effects' in r and 
                any(any(e.lower().find(effect) != -1 for effect in effects_lower) for e in r['effects'])]
    
    def filter_recipes_by_ingredients(self, recipes, ingredients):
        """Filter recipes by ingredients"""
        if not ingredients:
            return recipes
        
        ingredients_lower = [i.lower() for i in ingredients]
        return [r for r in recipes if 
                'ingredients' in r and 
                any(any(i.lower().find(ing) != -1 for ing in ingredients_lower) for i in r['ingredients'])]
    
    def sort_recipes_by_value(self, recipes, descending=True):
        """Sort recipes by value"""
        return sorted(recipes, key=lambda r: r.get('value', 0), reverse=descending)
    
    def generate_random_recipe(self, recipes):
        """Generate a random recipe based on existing components"""
        if not recipes or len(recipes) < 2:
            return None
        
        # Get all available bases, ingredients and effects
        bases = list(set(r.get('base', '') for r in recipes if 'base' in r))
        all_ingredients = []
        for r in recipes:
            if 'ingredients' in r:
                all_ingredients.extend(r['ingredients'])
        all_ingredients = list(set(all_ingredients))
        
        if not bases or not all_ingredients:
            return None
        
        # Create a random recipe
        random_recipe = {
            "name": f"Random {random.choice(['Mix', 'Blend', 'Concoction', 'Formula', 'Brew'])} #{random.randint(1, 999)}",
            "base": random.choice(bases),
            "ingredients": random.sample(all_ingredients, min(random.randint(1, 5), len(all_ingredients))),
            "effects": [],
            "value": round(random.uniform(50, 300), 2)
        }
        
        # Add random effects based on ingredients
        possible_effects = ["Energizing", "Refreshing", "Spicy", "Bright-Eyed", "Calming", 
                            "Gingeritis", "Laxative", "Explosive", "Euphoric", "Addictive", 
                            "Sedating", "Tropic Thunder", "Munchies", "Focused"]
        
        effect_count = min(len(random_recipe['ingredients']), len(possible_effects))
        random_recipe['effects'] = random.sample(possible_effects, effect_count)
        
        return random_recipe
    
    def calculate_recipe_value(self, base, ingredients):
        """Calculate estimated value for a custom recipe"""
        # This is a placeholder calculation, would need to be adjusted
        # based on the actual game mechanics
        base_value = 50
        ingredient_value = len(ingredients) * 15
        
        # Add some randomness
        variance = random.uniform(0.8, 1.2)
        
        return round((base_value + ingredient_value) * variance, 2)
    
    def generate_recipe_emoji(self, recipe):
        """Generate an emoji representation of a recipe"""
        base_emoji = "🌿"
        ingredient_emojis = {
            "Flu Medicine": "💊",
            "Energy Drink": "🥤",
            "Chili": "🌶️",
            "Mouthwash": "🧴",
            "Banana": "🍌",
            "Iodine": "💧",
            "Horsemen": "🐎",
            "Vitamin": "💊",
            "Battery": "🔋",
            "Viagra": "💙",
        }
        
        emoji_str = base_emoji
        
        for ingredient in recipe.get('ingredients', []):
            if ingredient in ingredient_emojis:
                emoji_str += " + " + ingredient_emojis[ingredient]
            else:
                emoji_str += " + 🧪"
        
        emoji_str += f" = 💰 (${recipe.get('value', 0):,.2f})"
        
        return emoji_str
    
    @commands.group(name="s1", aliases=["schedule1"])
    async def s1(self, ctx):
        """Commands for Schedule 1 game recipes and calculations"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @s1.command(name="top", aliases=["topbud"])
    async def top(self, ctx, *, drug_type: str = None):
        """
        Get the top value recipe from Schedule 1 game
        
        Examples:
            [p]s1 top
            [p]s1 top Sour Diesel
            [p]s1 topbud Green
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes at the moment. Try again later.")
            
            # Filter by drug type if specified
            if drug_type:
                filtered_recipes = self.filter_recipes_by_type(recipes, drug_type)
                if not filtered_recipes:
                    return await ctx.send(f"I couldn't find any recipes for '{drug_type}'. Try another type or leave it blank for all recipes.")
                recipes = filtered_recipes
            
            # Sort by value and get the top one
            sorted_recipes = self.sort_recipes_by_value(recipes)
            top_recipe = sorted_recipes[0] if sorted_recipes else None
            
            if not top_recipe:
                return await ctx.send("I couldn't find any top recipes at the moment. Try again later.")
            
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
            
            # Add emoji representation
            emoji_str = self.generate_recipe_emoji(top_recipe)
            embed.add_field(
                name="Recipe Visualization",
                value=emoji_str,
                inline=False
            )
            
            # Add footer
            embed.set_footer(text="Data from Schedule1-Calculator.net | Use [p]s1 recipes for more")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="recipes", aliases=["list", "buds"])
    async def recipes(self, ctx, *, drug_type: str = None):
        """
        Get a paginated list of recipes from Schedule 1 game
        
        Examples:
            [p]s1 recipes
            [p]s1 recipes OG Kush
            [p]s1 list Green
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes at the moment. Try again later.")
            
            # Filter by drug type if specified
            if drug_type:
                filtered_recipes = self.filter_recipes_by_type(recipes, drug_type)
                if not filtered_recipes:
                    return await ctx.send(f"I couldn't find any recipes for '{drug_type}'. Try another type or leave it blank for all recipes.")
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
                            f"{self.generate_recipe_emoji(recipe)}"
                        ),
                        inline=False
                    )
                
                embed.set_footer(text="Data from Schedule1-Calculator.net | Use [p]s1 details <name> for more info")
                pages.append(embed)
            
            if not pages:
                return await ctx.send("No recipes found.")
            
            # Use Red's menu system for pagination
            await menu(ctx, pages, DEFAULT_CONTROLS)
    
    @s1.command(name="details", aliases=["recipe", "i"])
    async def recipe_details(self, ctx, *, recipe_name: str):
        """
        Show detailed information about a specific recipe
        
        Examples:
            [p]s1 details Miracle Mix
            [p]s1 recipe Ice Cream
            [p]s1 info Pure Profit
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes at the moment. Try again later.")
            
            # Find the recipe by name (case-insensitive partial match)
            name_lower = recipe_name.lower()
            matching_recipes = [r for r in recipes if name_lower in r.get('name', '').lower()]
            
            if not matching_recipes:
                return await ctx.send(f"I couldn't find any recipe matching '{recipe_name}'. Try a different name.")
            
            # Sort by name similarity to get best match
            matching_recipes.sort(key=lambda r: abs(len(r.get('name', '')) - len(recipe_name)))
            recipe = matching_recipes[0]
            
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
            
            # Add emoji visualization
            emoji_str = self.generate_recipe_emoji(recipe)
            embed.add_field(
                name="Recipe Visualization",
                value=emoji_str,
                inline=False
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
            
            # Add similar recipes
            similar_recipes = [r for r in recipes if r != recipe and (
                r.get('base', '') == recipe.get('base', '') or
                any(i in r.get('ingredients', []) for i in recipe.get('ingredients', []))
            )]
            
            if similar_recipes:
                similar_recipes = self.sort_recipes_by_value(similar_recipes)[:3]
                similar_text = ", ".join([f"{r.get('name', 'Unknown')} (${r.get('value', 0):,.2f})" for r in similar_recipes])
                embed.add_field(
                    name="Similar Recipes",
                    value=similar_text,
                    inline=False
                )
            
            embed.set_footer(text="Data from Schedule1-Calculator.net | Use [p]s1 favorite to save this recipe")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="random", aliases=["randomrecipe", "surprise"])
    async def random_recipe(self, ctx):
        """
        Generate a random recipe from available components
        
        Examples:
            [p]s1 random
            [p]s1 surprise
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes to base random generation on. Try again later.")
            
            random_recipe = self.generate_random_recipe(recipes)
            
            if not random_recipe:
                return await ctx.send("I couldn't generate a random recipe. Try again later.")
            
            embed = discord.Embed(
                title=f"🎲 Random Recipe: {random_recipe.get('name', 'Unknown Mix')}",
                description=f"A randomly generated recipe - results may vary in the game!",
                color=0x00FF00
            )
            
            # Add base product field
            if 'base' in random_recipe:
                embed.add_field(
                    name="Base Product",
                    value=random_recipe['base'],
                    inline=True
                )
            
            # Add estimated value field
            embed.add_field(
                name="Estimated Value",
                value=f"${random_recipe.get('value', 0):,.2f}",
                inline=True
            )
            
            # Add emoji visualization
            emoji_str = self.generate_recipe_emoji(random_recipe)
            embed.add_field(
                name="Recipe Visualization",
                value=emoji_str,
                inline=False
            )
            
            # Add ingredients field
            if 'ingredients' in random_recipe and random_recipe['ingredients']:
                ingredients_text = "\n".join([f"• {ing}" for ing in random_recipe['ingredients']])
                embed.add_field(
                    name="Ingredients",
                    value=ingredients_text,
                    inline=False
                )
            
            # Add effects field
            if 'effects' in random_recipe and random_recipe['effects']:
                effects_text = ", ".join(random_recipe['effects'])
                embed.add_field(
                    name="Predicted Effects",
                    value=effects_text,
                    inline=False
                )
            
            # Add mixing instructions
            if 'ingredients' in random_recipe and random_recipe['ingredients']:
                instructions = [
                    f"1. Start with {random_recipe.get('base', 'base product')}"
                ]
                
                for i, ingredient in enumerate(random_recipe.get('ingredients', []), 2):
                    instructions.append(f"{i}. Add {ingredient}")
                
                embed.add_field(
                    name="Mixing Instructions",
                    value="\n".join(instructions),
                    inline=False
                )
            
            embed.set_footer(text="Random recipe - actual results in game may vary! | Try [p]s1 builder to create your own")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="builder", aliases=["build", "create"])
    async def recipe_builder(self, ctx, base: str, *ingredients):
        """
        Build your own recipe and get an estimated value
        
        Examples:
            [p]s1 builder Sour Diesel Chili "Energy Drink" Vitamin
            [p]s1 build OG Kush Banana Iodine
            [p]s1 create "Green Crack" Mouthwash Banana
        """
        if not base:
            return await ctx.send("You need to specify a base product for your recipe.")
        
        if not ingredients:
            return await ctx.send("You need to specify at least one ingredient for your recipe.")
        
        async with ctx.typing():
            # Get all recipes to extract possible components
            recipes = await self.get_recipes()
            
            # Calculate an estimated value
            value = self.calculate_recipe_value(base, ingredients)
            
            # Generate a name based on components
            name_prefix = random.choice([
                "Custom", "Homemade", "DIY", "Artisanal", 
                "Hand-crafted", f"{ctx.author.name}'s", "Unique"
            ])
            
            name_suffix = random.choice([
                "Blend", "Mix", "Formula", "Concoction", "Brew", 
                "Special", "Creation", "Compound", "Recipe"
            ])
            
            base_short = base.split()[-1] if ' ' in base else base
            
            custom_recipe = {
                "name": f"{name_prefix} {base_short} {name_suffix}",
                "base": base,
                "ingredients": ingredients,
                "value": value,
                "effects": []
            }
            
            # Generate potential effects based on ingredients
            all_effects = set()
            
            # Find recipes with similar ingredients to predict effects
            for recipe in recipes:
                if recipe.get('base', '').lower() == base.lower():
                    all_effects.update(recipe.get('effects', []))
                
                for ingredient in ingredients:
                    if ingredient.lower() in [i.lower() for i in recipe.get('ingredients', [])]:
                        all_effects.update(recipe.get('effects', []))
            
            # If we found effects, randomly select some based on ingredient count
            if all_effects:
                effect_count = min(len(ingredients) + 1, len(all_effects))
                custom_recipe['effects'] = random.sample(list(all_effects), effect_count)
            else:
                # Fallback effects if none were found
                possible_effects = ["Energizing", "Refreshing", "Spicy", "Bright-Eyed", "Calming", 
                                    "Gingeritis", "Laxative", "Explosive", "Euphoric", "Addictive"]
                effect_count = min(len(ingredients), len(possible_effects))
                custom_recipe['effects'] = random.sample(possible_effects, effect_count)
            
            # Create an embed for the custom recipe
            embed = discord.Embed(
                title=f"🧪 Custom Recipe: {custom_recipe['name']}",
                description=f"Your custom recipe creation",
                color=0x00FF00
            )
            
            embed.add_field(
                name="Base Product",
                value=custom_recipe['base'],
                inline=True
            )
            
            embed.add_field(
                name="Estimated Value",
                value=f"${custom_recipe['value']:,.2f}",
                inline=True
            )
            
            # Add emoji visualization
            emoji_str = self.generate_recipe_emoji(custom_recipe)
            embed.add_field(
                name="Recipe Visualization",
                value=emoji_str,
                inline=False
            )
            
            ingredients_text = "\n".join([f"• {ing}" for ing in custom_recipe['ingredients']])
            embed.add_field(
                name="Ingredients",
                value=ingredients_text,
                inline=False
            )
            
            effects_text = ", ".join(custom_recipe['effects'])
            embed.add_field(
                name="Predicted Effects",
                value=effects_text,
                inline=False
            )
            
            instructions = [f"1. Start with {custom_recipe['base']}"]
            for i, ingredient in enumerate(custom_recipe['ingredients'], 2):
                instructions.append(f"{i}. Add {ingredient}")
            
            embed.add_field(
                name="Mixing Instructions",
                value="\n".join(instructions),
                inline=False
            )
            
            embed.set_footer(text="Custom recipe - actual results in game may vary!")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="compare", aliases=["vs"])
    async def compare_recipes(self, ctx, recipe1: str, recipe2: str):
        """
        Compare two recipes side by side
        
        Examples:
            [p]s1 compare "Miracle Mix" "Ice Cream Slime"
            [p]s1 vs "Pure Profit" "Wedding Cake"
        """
        if not recipe1 or not recipe2:
            return await ctx.send("You need to specify two recipe names to compare.")
        
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes to compare. Try again later.")
            
            # Find the recipes by name (case-insensitive partial match)
            recipe1_lower = recipe1.lower()
            recipe2_lower = recipe2.lower()
            
            matching_recipes1 = [r for r in recipes if recipe1_lower in r.get('name', '').lower()]
            matching_recipes2 = [r for r in recipes if recipe2_lower in r.get('name', '').lower()]
            
            if not matching_recipes1:
                return await ctx.send(f"I couldn't find any recipe matching '{recipe1}'. Try a different name.")
            
            if not matching_recipes2:
                return await ctx.send(f"I couldn't find any recipe matching '{recipe2}'. Try a different name.")
            
            # Get the best matches
            recipe1_obj = matching_recipes1[0]
            recipe2_obj = matching_recipes2[0]
            
            # Create a comparison embed
            embed = discord.Embed(
                title=f"🆚 Recipe Comparison",
                description=f"Comparing {recipe1_obj.get('name', 'Unknown')} vs {recipe2_obj.get('name', 'Unknown')}",
                color=0x00FF00
            )
            
            # Add base products
            embed.add_field(
                name="Base Product",
                value=f"**{recipe1_obj.get('name')}**: {recipe1_obj.get('base', 'Unknown')}\n"
                     f"**{recipe2_obj.get('name')}**: {recipe2_obj.get('base', 'Unknown')}",
                inline=False
            )
            
            # Add values and calculate difference
            value1 = recipe1_obj.get('value', 0)
            value2 = recipe2_obj.get('value', 0)
            diff = abs(value1 - value2)
            better = recipe1_obj.get('name') if value1 > value2 else recipe2_obj.get('name')
            
            embed.add_field(
                name="Value Comparison",
                value=f"**{recipe1_obj.get('name')}**: ${value1:,.2f}\n"
                     f"**{recipe2_obj.get('name')}**: ${value2:,.2f}\n"
                     f"**Difference**: ${diff:,.2f} ({better} is better)",
                inline=False
            )
            
            # Compare ingredients
            ing1 = recipe1_obj.get('ingredients', [])
            ing2 = recipe2_obj.get('ingredients', [])
            
            common_ings = set(ing1).intersection(set(ing2))
            unique_ing1 = set(ing1).difference(set(ing2))
            unique_ing2 = set(ing2).difference(set(ing1))
            
            ingredients_text = ""
            if common_ings:
                ingredients_text += f"**Common Ingredients**: {humanize_list(list(common_ings))}\n\n"
            
            ingredients_text += f"**{recipe1_obj.get('name')} Unique Ingredients**: "
            ingredients_text += humanize_list(list(unique_ing1)) if unique_ing1 else "None"
            ingredients_text += f"\n\n**{recipe2_obj.get('name')} Unique Ingredients**: "
            ingredients_text += humanize_list(list(unique_ing2)) if unique_ing2 else "None"
            
            embed.add_field(
                name="Ingredient Comparison",
                value=ingredients_text,
                inline=False
            )
            
            # Compare effects
            effects1 = set(recipe1_obj.get('effects', []))
            effects2 = set(recipe2_obj.get('effects', []))
            
            common_effects = effects1.intersection(effects2)
            unique_effects1 = effects1.difference(effects2)
            unique_effects2 = effects2.difference(effects1)
            
            effects_text = ""
            if common_effects:
                effects_text += f"**Common Effects**: {humanize_list(list(common_effects))}\n\n"
            
            effects_text += f"**{recipe1_obj.get('name')} Unique Effects**: "
            effects_text += humanize_list(list(unique_effects1)) if unique_effects1 else "None"
            effects_text += f"\n\n**{recipe2_obj.get('name')} Unique Effects**: "
            effects_text += humanize_list(list(unique_effects2)) if unique_effects2 else "None"
            
            embed.add_field(
                name="Effects Comparison",
                value=effects_text,
                inline=False
            )
            
            # Recommendation
            embed.add_field(
                name="Recommendation",
                value=f"Based on value, **{better}** is the better choice. "
                     f"It's worth ${diff:,.2f} more than the alternative.",
                inline=False
            )
            
            embed.set_footer(text="Data from Schedule1-Calculator.net | Use [p]s1 details <name> for more info")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="topingredients", aliases=["ingredients", "bestingredients"])
    async def top_ingredients(self, ctx, count: int = 5):
        """
        Show which ingredients appear in the most valuable recipes
        
        Examples:
            [p]s1 topingredients
            [p]s1 ingredients 10
            [p]s1 bestingredients 3
        """
        if count < 1:
            count = 5
        
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes to analyze. Try again later.")
            
            # Sort recipes by value
            sorted_recipes = self.sort_recipes_by_value(recipes)
            
            # Count ingredient occurrences in top recipes
            ingredient_values = {}
            ingredient_counts = {}
            
            # Only consider the top 50% of recipes by value
            top_recipes = sorted_recipes[:max(len(sorted_recipes) // 2, 5)]
            
            for recipe in top_recipes:
                for ingredient in recipe.get('ingredients', []):
                    if ingredient not in ingredient_values:
                        ingredient_values[ingredient] = []
                    
                    ingredient_values[ingredient].append(recipe.get('value', 0))
                    ingredient_counts[ingredient] = ingredient_counts.get(ingredient, 0) + 1
            
            # Calculate average value for recipes containing each ingredient
            ingredient_avg_values = {}
            for ingredient, values in ingredient_values.items():
                ingredient_avg_values[ingredient] = sum(values) / len(values)
            
            # Sort ingredients by average value
            sorted_ingredients = sorted(
                ingredient_avg_values.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Create embed
            embed = discord.Embed(
                title=f"🧪 Top {count} Valuable Ingredients",
                description=f"Ingredients that appear in the most profitable recipes",
                color=0x00FF00
            )
            
            for i, (ingredient, avg_value) in enumerate(sorted_ingredients[:count], 1):
                embed.add_field(
                    name=f"#{i}: {ingredient}",
                    value=f"Average Recipe Value: ${avg_value:,.2f}\n"
                         f"Found in {ingredient_counts[ingredient]} top recipes",
                    inline=False
                )
            
            embed.set_footer(text="Based on frequency in top-value recipes | Use [p]s1 builder to try these ingredients")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="effectsearch", aliases=["effect", "findeffect"])
    async def effect_search(self, ctx, *effects):
        """
        Find recipes that produce specific effects
        
        Examples:
            [p]s1 effectsearch Energizing Euphoric
            [p]s1 effect Calming
            [p]s1 findeffect Spicy
        """
        if not effects:
            return await ctx.send("You need to specify at least one effect to search for.")
        
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes to search. Try again later.")
            
            # Filter recipes by effects
            filtered_recipes = self.filter_recipes_by_effects(recipes, effects)
            
            if not filtered_recipes:
                return await ctx.send(f"I couldn't find any recipes with the effects: {humanize_list(list(effects))}.")
            
            # Sort by value
            sorted_recipes = self.sort_recipes_by_value(filtered_recipes)
            
            # Create embed
            embed = discord.Embed(
                title=f"🔍 Recipes with {humanize_list(list(effects))} Effects",
                description=f"Found {len(sorted_recipes)} recipes with these effects",
                color=0x00FF00
            )
            
            # Show top 5 recipes
            for i, recipe in enumerate(sorted_recipes[:5], 1):
                recipe_effects = recipe.get('effects', [])
                matching_effects = [e for e in recipe_effects if any(effect.lower() in e.lower() for effect in effects)]
                
                embed.add_field(
                    name=f"#{i}: {recipe.get('name', 'Unknown')}",
                    value=f"Base: {recipe.get('base', 'Unknown')}\n"
                         f"Value: ${recipe.get('value', 0):,.2f}\n"
                         f"Matching Effects: {humanize_list(matching_effects)}",
                    inline=False
                )
            
            if len(sorted_recipes) > 5:
                embed.set_footer(text=f"{len(sorted_recipes) - 5} more recipes found | Use [p]s1 recipes for all recipes")
            else:
                embed.set_footer(text="Data from Schedule1-Calculator.net")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="favorite", aliases=["fav", "save"])
    async def save_favorite(self, ctx, *, recipe_name: str):
        """
        Save a recipe to your favorites
        
        Examples:
            [p]s1 favorite Miracle Mix
            [p]s1 fav "Ice Cream Slime"
            [p]s1 save Pure Profit
        """
        async with ctx.typing():
            recipes = await self.get_recipes()
            
            if not recipes:
                return await ctx.send("I couldn't find any recipes to save. Try again later.")
            
            # Find the recipe by name (case-insensitive partial match)
            name_lower = recipe_name.lower()
            matching_recipes = [r for r in recipes if name_lower in r.get('name', '').lower()]
            
            if not matching_recipes:
                return await ctx.send(f"I couldn't find any recipe matching '{recipe_name}'. Try a different name.")
            
            # Get the best match
            recipe = matching_recipes[0]
            
            # Get user's current favorites
            async with self.config.user(ctx.author).favorites() as favorites:
                # Check if already favorited
                for fav in favorites:
                    if fav.get('name', '').lower() == recipe.get('name', '').lower():
                        return await ctx.send(f"You already have '{recipe.get('name', 'Unknown')}' in your favorites!")
                
                # Add to favorites
                favorites.append(recipe)
            
            await ctx.send(f"Added '{recipe.get('name', 'Unknown')}' to your favorites! Use `{ctx.prefix}s1 favorites` to view your saved recipes.")
    
    @s1.command(name="favorites", aliases=["favs", "saved"])
    async def view_favorites(self, ctx):
        """
        View your saved favorite recipes
        
        Examples:
            [p]s1 favorites
            [p]s1 favs
            [p]s1 saved
        """
        async with ctx.typing():
            # Get user's current favorites
            favorites = await self.config.user(ctx.author).favorites()
            
            if not favorites:
                return await ctx.send("You don't have any saved recipes. Use `{ctx.prefix}s1 favorite <name>` to save some!")
            
            # Sort by value
            sorted_favorites = sorted(favorites, key=lambda r: r.get('value', 0), reverse=True)
            
            # Create embed
            embed = discord.Embed(
                title=f"💖 {ctx.author.name}'s Favorite Recipes",
                description=f"You have {len(sorted_favorites)} saved recipes",
                color=0x00FF00
            )
            
            # Show all favorites, up to 10
            for i, recipe in enumerate(sorted_favorites[:10], 1):
                embed.add_field(
                    name=f"#{i}: {recipe.get('name', 'Unknown')}",
                    value=f"Base: {recipe.get('base', 'Unknown')}\n"
                         f"Value: ${recipe.get('value', 0):,.2f}\n"
                         f"{self.generate_recipe_emoji(recipe)}",
                    inline=False
                )
            
            if len(sorted_favorites) > 10:
                embed.set_footer(text=f"{len(sorted_favorites) - 10} more favorites not shown | Use [p]s1 details <name> for more info")
            else:
                embed.set_footer(text="Use [p]s1 details <name> for more info on any recipe")
            
            await ctx.send(embed=embed)
    
    @s1.command(name="unfavorite", aliases=["unfav", "removefav", "unsave"])
    async def remove_favorite(self, ctx, *, recipe_name: str):
        """
        Remove a recipe from your favorites
        
        Examples:
            [p]s1 unfavorite Miracle Mix
            [p]s1 unfav "Ice Cream Slime"
            [p]s1 removefav Pure Profit
        """
        async with ctx.typing():
            name_lower = recipe_name.lower()
            
            # Get user's current favorites
            async with self.config.user(ctx.author).favorites() as favorites:
                # Find the recipe to remove
                found = False
                for i, fav in enumerate(favorites):
                    if name_lower in fav.get('name', '').lower():
                        removed_name = fav.get('name', 'Unknown')
                        favorites.pop(i)
                        found = True
                        break
            
            if found:
                await ctx.send(f"Removed '{removed_name}' from your favorites!")
            else:
                await ctx.send(f"I couldn't find any recipe matching '{recipe_name}' in your favorites.")
    
    @s1.command(name="update", aliases=["refresh"])
    async def force_refresh(self, ctx):
        """
        Force refresh the recipe cache
        
        Examples:
            [p]s1 update
            [p]s1 refresh
        """
        async with ctx.typing():
            # Get the current recipe count
            old_recipes = await self.get_recipes()
            old_count = len(old_recipes)
            
            # Force refresh the cache
            recipes = await self.get_recipes(force_refresh=True)
            new_count = len(recipes)
            
            # Also check for game updates
            await self.check_for_game_updates()
            
            await ctx.send(f"Recipe cache refreshed! Found {new_count} recipes total (previously {old_count}).")
            
            # If there are new recipes, show a summary
            if new_count > old_count:
                # Sort by value and show the top new recipe
                sorted_recipes = self.sort_recipes_by_value(recipes)
                top_recipe = sorted_recipes[0]
                
                embed = discord.Embed(
                    title="🔄 Cache Refresh Summary",
                    description=f"Found {new_count - old_count} new recipes!",
                    color=0x00FF00
                )
                
                embed.add_field(
                    name="Current Top Recipe",
                    value=f"{top_recipe.get('name', 'Unknown')}\n"
                         f"Value: ${top_recipe.get('value', 0):,.2f}",
                    inline=False
                )
                
                embed.set_footer(text="Use [p]s1 recipes to see all available recipes")
                
                await ctx.send(embed=embed)
    
    @s1.command(name="about", aliases=["info", "help"])
    async def about_cog(self, ctx):
        """
        Show information about the Schedule 1 recipes cog
        
        Examples:
            [p]s1 about
            [p]s1 i
            [p]s1 help
        """
        embed = discord.Embed(
            title="📋 About Schedule 1 Recipes Cog",
            description="This cog provides information and tools for Schedule 1 game recipes.",
            color=0x00FF00
        )
        
        commands_text = (
            "**[p]s1 top** - Show the most profitable recipe\n"
            "**[p]s1 recipes** - List all available recipes\n"
            "**[p]s1 details** - Show details for a specific recipe\n"
            "**[p]s1 random** - Generate a random recipe\n"
            "**[p]s1 builder** - Create your own custom recipe\n"
            "**[p]s1 compare** - Compare two recipes side by side\n"
            "**[p]s1 topingredients** - Show most valuable ingredients\n"
            "**[p]s1 effectsearch** - Find recipes with specific effects\n"
            "**[p]s1 favorite** - Save a recipe to your favorites\n"
            "**[p]s1 favorites** - View your saved recipes\n"
            "**[p]s1 unfavorite** - Remove a recipe from favorites\n"
            "**[p]s1 update** - Force refresh the recipe cache"
        )
        
        embed.add_field(
            name="Available Commands",
            value=commands_text,
            inline=False
        )
        
        tips_text = (
            "• Search recipes by drug type using '[p]s1 recipes <type>'\n"
            "• Compare recipes to find the best value\n"
            "• Save your favorite recipes for quick reference\n"
            "• Create custom recipes to experiment before trying in-game\n"
            "• Check top ingredients to find the most profitable components\n"
            "• Search by effect to find recipes with specific properties"
        )
        
        embed.add_field(
            name="Tips",
            value=tips_text,
            inline=False
        )
        
        embed.set_footer(text="Data sourced from Schedule1-Calculator.net | Game mechanics may change over time")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Schedule1Recipes(bot))
