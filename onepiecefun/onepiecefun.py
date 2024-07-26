import random
import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

class OnePieceFun(commands.Cog):
    """Fun One Piece-themed commands for entertainment!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {
            "custom_devil_fruits": {},
            "custom_bounties": {}
        }
        self.config.register_guild(**default_guild)

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

    @commands.command()
    async def island(self, ctx):
        """Generate a random One Piece-style island name and description."""
        prefixes = ["Punk", "Whole", "Drum", "Fishman", "Sky", "Water", "Dressrosa", "Shells", "Jaya", "Enies", "Thriller"]
        suffixes = ["Island", "Kingdom", "Archipelago", "City", "Town", "Land", "Paradise", "Hell", "World", "Country"]
        
        features = ["giant trees", "talking animals", "extreme weather", "ancient ruins", "futuristic technology", 
                    "perpetual night", "eternal summer", "floating islands", "underwater caves", "living buildings"]
        
        dangers = ["man-eating plants", "volcanic eruptions", "whirlpools", "giant sea monsters", "unpredictable gravity", 
                   "memory-erasing mist", "time distortions", "reality-bending mirages", "cursed treasures", "shape-shifting natives"]
        
        island_name = f"{random.choice(prefixes)} {random.choice(suffixes)}"
        description = f"An island known for its {random.choice(features)}. Beware of the {random.choice(dangers)}!"
        
        await ctx.send(f"🏝️ **{island_name}** 🏝️\n{description}")

    @commands.command()
    async def crewrole(self, ctx, *, name: str):
        """Assign a random One Piece crew role to someone."""
        roles = [
            "Captain", "First Mate", "Navigator", "Sniper", "Chef", "Doctor", "Shipwright", "Musician",
            "Archaeologist", "Helmsman", "Lookout", "Strategist", "Cabin Boy/Girl", "Pet"
        ]
        
        role = random.choice(roles)
        quirks = [
            "who's always hungry",
            "with a secret past",
            "who's afraid of their own shadow",
            "who can't swim (even without a Devil Fruit)",
            "who tells the worst jokes",
            "who's obsessed with treasure",
            "who sleeps through every battle",
            "who's in love with the ship",
            "who thinks they're the captain (but they're not)",
            "who's actually a Marine spy (shh, don't tell anyone)"
        ]
        
        quirk = random.choice(quirks)
        
        await ctx.send(f"Ahoy! {name} would be the crew's {role}, {quirk}!")

    @commands.command()
    async def poneglyph(self, ctx):
        """Decode a 'mysterious' poneglyph message."""
        messages = [
            "The One Piece is real... but it was the friends we made along the way.",
            "Congratulations! You can read poneglyphs. The World Government wants to know your location.",
            "Here's the secret recipe for Sanji's best dish... just kidding, it's blank!",
            "Turn left at the giant whale, right at the sky island, and straight on 'til morning.",
            "This poneglyph intentionally left blank. Please try again in 800 years.",
            "The true power of the Gum-Gum fruit is... [The rest is too weathered to read]",
            "Warning: Reading this poneglyph may cause spontaneous dance parties.",
            "Raftel is just an anagram of... [The rest is covered in Buggy's graffiti]"
        ]
        
        decoded = random.choice(messages)
        await ctx.send(f"🗿 You've decoded the poneglyph! It reads:\n\n*{decoded}*")

    @commands.check(is_mod_or_admin)
    @commands.command()
    async def df_add(self, ctx, name: str, *, description: str):
        """Add a custom Devil Fruit to the server's list."""
        async with self.config.guild(ctx.guild).custom_devil_fruits() as df_list:
            df_list[name] = description
        await ctx.send(f"The {name} has been added to the Devil Fruit encyclopedia!")

    @commands.command()
    async def df_list(self, ctx):
        """List all custom Devil Fruits for this server."""
        df_list = await self.config.guild(ctx.guild).custom_devil_fruits()
        if not df_list:
            return await ctx.send("There are no custom Devil Fruits in this server's encyclopedia yet!")
        
        message = "🍎 **Custom Devil Fruits** 🍎\n\n"
        for name, desc in df_list.items():
            message += f"**{name}**: {desc}\n\n"
        
        pages = list(pagify(message, delims=["\n\n"], page_length=1000))
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @commands.check(is_mod_or_admin)
    @commands.command()
    async def bounty_add(self, ctx, name: str, amount: int, *, reason: str):
        """Add a custom bounty for someone in the server."""
        async with self.config.guild(ctx.guild).custom_bounties() as bounty_list:
            bounty_list[name] = {"amount": amount, "reason": reason}
        await ctx.send(f"A bounty of {amount:,} Berries has been placed on {name}'s head for {reason}!")

    @commands.command()
    async def bounty_list(self, ctx):
        """List all custom bounties for this server."""
        bounty_list = await self.config.guild(ctx.guild).custom_bounties()
        if not bounty_list:
            return await ctx.send("There are no custom bounties in this server yet!")
        
        message = "💰 **Custom Bounties** 💰\n\n"
        for name, info in bounty_list.items():
            message += f"**{name}**: {info['amount']:,} Berries\nReason: {info['reason']}\n\n"
        
        pages = list(pagify(message, delims=["\n\n"], page_length=1000))
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @commands.command()
    async def strawhat(self, ctx, *, name: str):
        """If the mentioned person joined the Straw Hat crew, what would their role and quirk be?"""
        roles = [
            "the second chef, specializing in desserts",
            "the apprentice shipwright, always carrying a hammer",
            "the assistant doctor, with a fear of blood",
            "the backup musician, who only knows one song",
            "the unofficial storyteller, with tales no one believes",
            "the ship's gardener, growing suspicious plants",
            "the crew's tailor, with a very 'unique' fashion sense",
            "the log keeper, who embellishes every entry",
            "the fishing expert, who's never caught a fish",
            "the treasure appraiser, who overvalues everything"
        ]
        
        quirks = [
            "but they sleep through every meal",
            "and they have a secret collection of Marine wanted posters",
            "though they get seasick easily",
            "but they think every island is Raftel",
            "and they're convinced they're the reincarnation of Gol D. Roger",
            "though they're terrified of Luffy's stretching",
            "but they keep trying to 'improve' Nami's climate baton",
            "and they have a peculiar habit of talking to Sea Kings",
            "though they believe they're the strongest after Luffy (they're not)",
            "but they're on a quest to find the 'One Piece' of perfect clothing"
        ]
        
        role = random.choice(roles)
        quirk = random.choice(quirks)
        
        await ctx.send(f"If {name} joined the Straw Hat crew, they'd be {role}, {quirk}!")

    @commands.command()
    async def move(self, ctx, *, name: str):
        """Generate a random One Piece-style move name."""
        prefixes = ["Gum-Gum", "Flame-Flame", "Rumble-Rumble", "Dragon-Dragon", "Chop-Chop", "Slip-Slip", "Smoke-Smoke", "Sand-Sand"]
        moves = ["Pistol", "Bazooka", "Gatling", "Rifle", "Storm", "Whip", "Hammer", "Cannon", "Tornado", "Blast", "Sword", "Spear"]
        adjectives = ["Flaming", "Thundering", "Colossal", "Rapid-Fire", "Spinning", "Gigantic", "Piercing", "Exploding"]
        
        move_name = f"{random.choice(prefixes)} {random.choice(adjectives)} {random.choice(moves)}"
        description = f"{name} unleashes their secret technique: {move_name}!"
        
        effects = [
            "It's super effective!",
            "The attack misses wildly and hits a nearby building instead.",
            "Somehow, it turns into a dance move mid-attack.",
            "Everyone is impressed, but also slightly confused.",
            "It works perfectly, but {name} forgets how they did it immediately after.",
            "The attack is so powerful, it launches {name} backwards!",
            "It's not very effective... but it looks really cool!",
            "The move is interrupted by the dinner bell. Priorities, right?"
        ]
        
        effect = random.choice(effects).format(name=name)
        
        await ctx.send(f"{description}\n{effect}")

async def setup(bot: Red):
    await bot.add_cog(OnePieceFun(bot))
