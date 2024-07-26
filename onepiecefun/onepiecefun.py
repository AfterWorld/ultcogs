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
        """Get a random Devil Fruit fact or a made-up funny one."""
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
            "The Mochi-Mochi Fruit is a 'special Paramecia' type, blurring the lines between Paramecia and Logia.",
            "The Little-Little Fruit lets the user shrink anything they touch, including themselves.",
            "The Hobby-Hobby Fruit can turn people into toys, erasing memories of their existence.",
            "There's a non-canon Devil Fruit that gives the power to control ramen noodles. Yum!",
            "The Swim-Swim Fruit allows the user to swim through solid objects... but not water!",
            "Legend has it there's a Fruit-Fruit Fruit that turns the user into a walking fruit basket.",
            "The Flame-Flame Fruit doesn't just produce fire, it turns the user's body into flame.",
            "Some say there's a Sleep-Sleep Fruit that puts everyone to sleep... including the user!",
            "The Rumor-Rumor Fruit supposedly lets you spread rumors that become true. Or is that just a rumor?",
            "The Drill-Drill Fruit is perfect for dentists... and pirates who love to make holes in ships!",
            "The Kilo-Kilo Fruit allows the user to change their weight from 1 to 10,000 kilograms. Talk about a yo-yo diet!"
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
            f"Blimey, {target}! Ye be as useful in a fight as Usopp's rubber band of doom!",
            f"{target}, yer navigation skills make Luffy look like Nami!",
            f"Oi, {target}! Ye have the charisma of a Celestial Dragon at a commoner's party!",
            f"{target}, ye couldn't beat Spandam in an arm-wrestling match!",
            f"Arr, {target}! Yer about as intimidating as Chopper's cotton candy loving form!",
            f"Listen here, {target}, ye have the memory of Gaimon... stuck in a box for 20 years!"
        ]
        roast = random.choice(roasts)
        await ctx.send(roast)

    @commands.command()
    async def bounty(self, ctx, *, name: str):
        """Generate a random bounty for a given name with a funny reason."""
        bounty = random.randint(1000000, 5000000000)
        formatted_bounty = f"{bounty:,}"
        
        reasons = [
            "for eating too much at the Baratie without paying",
            "for mistaking a Marine base for a restaurant",
            "for trying to sell fake Devil Fruits to Kaido",
            "for asking Big Mom about her diet plan",
            "for using Zoro as a compass",
            "for stealing Doflamingo's sunglasses collection",
            "for trying to give Kaido swimming lessons",
            "for asking Buggy about his nose",
            "for trying to recruit Sea Kings into their crew",
            "for attempting to give Blackbeard a dental plan",
            "for trying to sell meat-scented cologne to Luffy",
            "for starting a 'Save the Sea Kings' campaign",
            "for opening a Monkey D. Luffy School of Strategy",
            "for trying to teach the Revolutionary Army to do the 'Binks' Sake' dance"
        ]
        
        reason = random.choice(reasons)
        
        await ctx.send(f"💰 **Bounty Alert!** 💰\n"
                       f"The World Government has placed a bounty of {formatted_bounty} Berries on {name}'s head "
                       f"{reason}!")

    @commands.command()
    async def shipname(self, ctx, name1: str, name2: str):
        """Generate a One Piece-style ship name for two characters."""
        ship_prefixes = ["Thousand", "Going", "Oro", "Red", "Big", "Polar", "Moby", "Sexy", "Drunken", "Merry", "Sunny", "Laughing", "Crying", "Flying", "Roaring"]
        ship_suffixes = ["Sunny", "Merry", "Jackson", "Force", "Top", "Tang", "Dick", "Foxy", "Roger", "Saber", "Dumpling", "Octopus", "Banana", "Cutlass"]
        
        ship_name = f"{random.choice(ship_prefixes)} {random.choice(ship_suffixes)}"
        await ctx.send(f"Ahoy! If {name1} and {name2} had a ship, it'd be called '{ship_name}'! May it sail the Grand Line with pride!")

    @commands.command()
    async def piratename(self, ctx, *, name: str):
        """Generate a One Piece-style pirate name."""
        epithets = ["Straw Hat", "Fire Fist", "Pirate Hunter", "Black Leg", "Cat Burglar", "Soul King", "Cyborg", "Devil Child", 
                    "Humming", "Red-Haired", "Hawk-Eye", "Surgeon of Death", "Dark King", "Fire Tank", "Big News", "Red Flag"]
        
        pirate_name = f"'{random.choice(epithets)}' {name}"
        await ctx.send(f"Yarr! If ye sailed the Grand Line, ye'd be known as {pirate_name}! Strike fear into the hearts of Marines everywhere!")

    @commands.command()
    async def devilfruit(self, ctx):
        """Generate a random, funny Devil Fruit power."""
        prefixes = ["Noodle", "Bubble", "Sneeze", "Hiccup", "Tickle", "Belch", "Giggle", "Blush", "Yawn", "Wink", "Blink", "Wiggle"]
        suffixes = ["Fruit", "Fruit", "Fruit", "Fruit", "Fruit", "Fruit", "Fruit", "Nut", "Berry", "Melon", "Pineapple", "Mango"]
        
        fruit_name = f"{random.choice(prefixes)}-{random.choice(prefixes)} {random.choice(suffixes)}"
        powers = [
            f"the power to {fruit_name.split('-')[0].lower()} uncontrollably when nervous",
            f"the ability to make others {fruit_name.split('-')[1].lower()} on command",
            f"the power to turn anything you touch into {fruit_name.split('-')[0].lower()}s",
            f"the ability to shoot {fruit_name.split('-')[1].lower()}s from your fingertips",
            f"the power to summon an army of {fruit_name.split('-')[0].lower()}ing sea creatures",
            f"the ability to create life-size {fruit_name.split('-')[1].lower()} sculptures with your mind"
        ]
        
        power = random.choice(powers)
        await ctx.send(f"Congratulations! Ye've eaten the {fruit_name}! Ye now have {power}. Use it wisely, ye scurvy dog!")

    @commands.command()
    async def reaction(self, ctx, *, situation: str):
        """Get a One Piece character's reaction to a situation."""
        characters = {
            "Luffy": ["laughs and asks if it's edible", "shouts 'I'm gonna be the Pirate King!'", "picks his nose thoughtfully"],
            "Zoro": ["gets lost trying to respond", "mumbles something about training", "takes a nap"],
            "Nami": ["demands payment for her opinion", "sighs and facepalms", "starts plotting how to profit from the situation"],
            "Usopp": ["tells an outrageous lie about a similar situation", "hides behind Luffy", "invents a new gadget to deal with it"],
            "Sanji": ["offers to cook something to help", "swoons if it involves a lady", "picks a fight with Zoro"],
            "Chopper": ["hides the wrong way", "offers medical advice", "gets sparkly-eyed with excitement"],
            "Robin": ["chuckles ominously", "shares a morbid historical fact", "calmly sips tea"],
            "Franky": ["strikes a pose and shouts 'SUPER!'", "offers to build a machine to solve the problem", "questions if it's 'SUPER' enough"],
            "Brook": ["makes a skull joke", "asks to see ladies' panties", "starts playing a song about the situation"]
        }
        
        character = random.choice(list(characters.keys()))
        reaction = random.choice(characters[character])
        
        await ctx.send(f"In response to '{situation}', {character} {reaction}.")

async def setup(bot: Red):
    await bot.add_cog(OnePieceFun(bot))
