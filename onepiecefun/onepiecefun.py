import random
import discord
from redbot.core import commands
from redbot.core.bot import Red

class OnePieceFun(commands.Cog):
    """Fun One Piece-themed commands for entertainment!"""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def df(self, ctx):
        """Get a random Devil Fruit fact."""
        df_facts = [
            "The Gum-Gum Fruit was the first Devil Fruit introduced in the series.",
            "Blackbeard is the only known person to have eaten two Devil Fruits.",
            "The Calm-Calm Fruit allows the user to create a sphere of silence.",
            "Marco's Phoenix fruit is a Mythical Zoan, one of the rarest types.",
            "Some Devil Fruits, like the Jacket-Jacket Fruit, have seemingly useless powers.",
            "The Ope-Ope Fruit is considered the ultimate Devil Fruit for medical operations.",
            "Chopper's Human-Human Fruit allowed an animal to gain human intelligence and form.",
            "Kaku and Kalifa were given Devil Fruits by Spandam, despite being skilled fighters already.",
            "Brook's Revive-Revive Fruit allowed him to return to life after death... but only once.",
            "The Mochi-Mochi Fruit is a 'special Paramecia' type, blurring the lines between Paramecia and Logia."
        ]
        fact = random.choice(df_facts)
        await ctx.send(f"🍎 **Devil Fruit Fact:** {fact}")

    @commands.command()
    async def love(self, ctx, name1: str, name2: str):
        """Calculate the One Piece love compatibility between two names."""
        love_percentage = random.randint(1, 100)
        
        if love_percentage < 20:
            message = f"Arr! {name1} and {name2} be as compatible as Luffy and skipping meals! ({love_percentage}%)"
        elif love_percentage < 40:
            message = f"Yohohoho! The love between {name1} and {name2} be as empty as me belly! ({love_percentage}%)"
        elif love_percentage < 60:
            message = f"Aye, {name1} and {name2} be gettin' along like Zoro and a compass! ({love_percentage}%)"
        elif love_percentage < 80:
            message = f"Shiver me timbers! {name1} and {name2} be as close as Sanji to his kitchen! ({love_percentage}%)"
        else:
            message = f"By the powers of the sea! {name1} and {name2} be as perfect as Luffy and meat! ({love_percentage}%)"

        await ctx.send(message)

    @commands.command()
    async def roast(self, ctx, *, target: str):
        """Deliver a One Piece-themed roast."""
        roasts = [
            f"{target}, ye be as useless as a rubber knife at a Logia convention!",
            f"Oi, {target}! Even Buggy the Clown be laughin' at yer skills!",
            f"Ye know, {target}, if brains were berries, ye couldn't feed Chopper in his smallest form!",
            f"Arr, {target}! Ye be as lost as Zoro in a straight hallway!",
            f"Listen here, {target}, ye have the charm of a Sea King with a toothache!",
            f"{target}, yer as slow as Luffy's brain during a math test!",
            f"Oi, {target}! Ye couldn't find the One Piece if it were hangin' 'round yer neck!",
            f"Ye know what, {target}? Ye be makin' Foxy the Silver Fox look like a genius!",
            f"Arr, {target}! Ye have the fighting skills of a Den Den Mushi!",
            f"Blimey, {target}! Ye be as useful in a fight as Usopp's rubber band of doom!"
        ]
        roast = random.choice(roasts)
        await ctx.send(roast)

    @commands.command()
    async def bounty(self, ctx, *, name: str):
        """Generate a random bounty for a given name."""
        bounty = random.randint(1000000, 5000000000)
        formatted_bounty = f"{bounty:,}"
        
        await ctx.send(f"💰 **Bounty Alert!** 💰\n"
                       f"The World Government has placed a bounty of {formatted_bounty} Berries on {name}'s head!")

    @commands.command()
    async def shipname(self, ctx, name1: str, name2: str):
        """Generate a One Piece-style ship name for two characters."""
        ship_prefixes = ["Thousand", "Going", "Oro", "Red", "Big", "Polar", "Moby", "Sexy"]
        ship_suffixes = ["Sunny", "Merry", "Jackson", "Force", "Top", "Tang", "Dick", "Foxy"]
        
        ship_name = f"{random.choice(ship_prefixes)} {random.choice(ship_suffixes)}"
        await ctx.send(f"Ahoy! If {name1} and {name2} had a ship, it'd be called '{ship_name}'! May it sail the Grand Line with pride!")

async def setup(bot: Red):
    await bot.add_cog(OnePieceFun(bot))
