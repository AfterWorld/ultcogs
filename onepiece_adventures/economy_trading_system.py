import discord 
from redbot.core import commands, Config 
import random

class EconomyTradingSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def create_market_listing(self, ctx, item: str, price: int, quantity: int):
        user_data = await self.config.member(ctx.author).all()
        if item not in user_data["inventory"] or user_data["inventory"][item] < quantity:
            await ctx.send("You don't have enough of that item to sell.")
            return

        market_listings = await self.config.guild(ctx.guild).market_listings()
        listing_id = random.randint(1000, 9999)
        market_listings[listing_id] = {
            "seller": ctx.author.id,
            "item": item,
            "price": price,
            "quantity": quantity
        }
        await self.config.guild(ctx.guild).market_listings.set(market_listings)

        user_data["inventory"][item] -= quantity
        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"Listing created! ID: {listing_id}")

    async def buy_market_listing(self, ctx, listing_id: int):
        market_listings = await self.config.guild(ctx.guild).market_listings()
        if listing_id not in market_listings:
            await ctx.send("Invalid listing ID.")
            return

        listing = market_listings[listing_id]
        buyer_data = await self.config.member(ctx.author).all()
        if buyer_data["berries"] < listing["price"] * listing["quantity"]:
            await ctx.send("You don't have enough berries to buy this listing.")
            return

        seller = self.bot.get_user(listing["seller"])
        if seller:
            seller_data = await self.config.member(seller).all()
            seller_data["berries"] += listing["price"] * listing["quantity"]
            await self.config.member(seller).set(seller_data)

        buyer_data["berries"] -= listing["price"] * listing["quantity"]
        if listing["item"] not in buyer_data["inventory"]:
            buyer_data["inventory"][listing["item"]] = 0
        buyer_data["inventory"][listing["item"]] += listing["quantity"]
        await self.config.member(ctx.author).set(buyer_data)

        del market_listings[listing_id]
        await self.config.guild(ctx.guild).market_listings.set(market_listings)

        await ctx.send(f"You have successfully purchased {listing['quantity']} {listing['item']} for {listing['price'] * listing['quantity']} berries!")

    async def view_market_listings(self, ctx):
        market_listings = await self.config.guild(ctx.guild).market_listings()
        if not market_listings:
            await ctx.send("There are no active market listings.")
            return

        embed = discord.Embed(title="Market Listings", color=discord.Color.green())
        for listing_id, listing in market_listings.items():
            seller = self.bot.get_user(listing["seller"])
            embed.add_field(
                name=f"ID: {listing_id}",
                value=f"Seller: {seller.name}\nItem: {listing['item']}\nPrice: {listing['price']} berries\nQuantity: {listing['quantity']}",
                inline=False
            )

        await ctx.send(embed=embed)
