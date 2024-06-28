import contextlib
import discord 
from redbot.core.utils.views import SetApiView
from redbot.core.utils.chat_formatting import box
import sys
from redbot.core.bot import Red
from redbot.core import (
    __version__,
    version_info as red_version_info,
    commands,
    bank,
    errors,
    i18n,
    bank,
    modlog,
) 

class OnePieceServer(commands.Cog):
    """Tools providing info about our One Piece themed server <:strawhat:1243924879045034075>."""
    def __init__(self, bot):
        self.bot = bot

    async def cog_unload(self) -> None:
        global old_bounty
        self.bot.remove_command("info")
        if old_bounty:
            with contextlib.suppress(Exception):
                self.bot.remove_command("bounty")
                self.bot.add_command(old_bounty)

    @commands.command()
    async def info(self, ctx):
        """Shows information about our One Piece themed server <:strawhat:1243924879045034075>."""
        ping = round(self.bot.latency * 1000)
        python_url = "https://www.python.org/"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        dpy_version = "{}".format(discord.__version__)
        python_version = "{}.{}.{}".format(*sys.version_info[:3])
        red_version = "{}".format(__version__)
        title = "One Piece Community Discord <:strawhat:1243924879045034075>"
        embed = discord.Embed(title=title, description="Ahoy, pirates! Welcome to our One Piece themed Discord server. I'm Sunny, the bot sailing these digital seas. I'm always on deck and ready to help whenever a nakama needs me. Now, let me tell you about my friend [Red](https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop/redbot), the system that powers me.")
        embed.set_thumbnail(url="https://example.com/sunny_bot_avatar.png")
        embed.add_field(inline=False, name=' ', value='I (Sunny <:strawhat:1243924879045034075>) am an instance of Red-DiscordBot. If you want a bot like me (because I\'m as SUPER as Franky!), you can create your own by following the [Red installation docs](https://docs.discord.red/en/stable/install_guides/index.html).')
        embed.add_field(inline=False, name=' ', value='Use `!credits` and `!findcog` to view the other sources used in Sunny.')
        embed.add_field(inline=False, name=' ', value="You might be wondering how to get Sunny for your own server. Currently, Sunny is a private bot for this Grand Line, but if you want to set sail with a bot like Sunny, you'll need to contact our Shipwright (server admin). Or better yet, build your own Red instance and customize it to be as SUPER as you want!")
        embed.add_field(inline=False, name="", value=(f"**<:log_pose:1252942734738591776> Python Version: {python_version} \n<:den_den_mushi:1252942959855276143> discord.py: {dpy_version} \n<:sunny:1244503516039348234> Red version: {red_version} \n🏴‍☠️ Ping : {ping}ms\n**"))
        await ctx.send(embed=embed)

    @commands.command()
    async def credits(self, ctx):
        """Shows the credits for Sunny and the server."""
        cog = self.bot.get_cog("Downloader")
        repos = cog._repo_manager.repos
        s_repos = sorted(repos, key=lambda r: str.lower(r.name))
        embed = discord.Embed(title='The Honorable CreditBoard', description=" ")
        embed.add_field(inline=False, name='Red-DiscordBot', value="Sunny is powered by Red, created by [Twentysix26](https://github.com/Twentysix26) and [improved by many awesome people.](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors)")
        embed.add_field(inline=False, name='Emojis', value="Most of the emojis used in this bot are taken from NQN, so the credits go to their respective owners.")  
        embed.add_field(inline=False, name='Cogs and their creators (Thanks to those awesome people for their work! <:thanks:1254778925582778389>)', value='**[aaa3a-cogs](https://github.com/AAA3A-AAA3A/AAA3A-cogs): aaa3a\n[ad-cog](https://github.com/aikaterna/gobcog.git): aikaterna\n[adrian](https://github.com/designbyadrian/CogsByAdrian.git): thinkadrian \n[blizz-cogs](https://git.purplepanda.cc/blizz/blizz-cogs): blizzthewolf\n[crab-cogs](https://github.com/orchidalloy/crab-cogs): hollowstrawberry\n[flare-cogs](https://github.com/flaree/Flare-Cogs): flare (flare#0001)\n[fluffycogs](https://github.com/zephyrkul/FluffyCogs): Zephyrkul (Zephyrkul#1089)\n[jojocogs](https://github.com/Just-Jojo/JojoCogs): Jojo#7791\n[jumperplugins](https://github.com/Redjumpman/Jumper-Plugins): Redjumpman (Redjumpman#1337)\n[laggrons-dumb-cogs](https://github.com/retke/Laggrons-Dumb-Cogs): El Laggron\n[lui-cogs-v3](https://github.com/Injabie3/lui-cogs-v3): Injabie3#1660, sedruk, KaguneAstra#6000, TheDarkBot#1677, quachtridat・たつ#8232\n[maxcogs](https://github.com/ltzmax/maxcogs): MAX\n**')
        embed.add_field(inline=False, name=' ', value='**[affirmative-cogs](https://github.com/AffirmativeGuy/affirmative-cogs): affirmativeguy\n[npc-cogs](https://github.com/npc203/npc-cogs): epic guy#0715\n[pcxcogs](https://github.com/PhasecoreX/PCXCogs): PhasecoreX (PhasecoreX#0635)\n[seina-cogs](https://github.com/japandotorg/Seina-Cogs/): inthedark.org\n[sravan](https://github.com/sravan1946/sravan-cogs): sravan\n[toxic-cogs](https://github.com/NeuroAssassin/Toxic-Cogs): Neuro Assassin\n[Trusty-cogs](https://github.com/TrustyJAID/Trusty-cogs/): TrustyJAID\n[vrt-cogs](https://github.com/vertyco/vrt-cogs): Vertyco\n[yamicogs](https://github.com/yamikaitou/YamiCogs): YamiKaitou#8975\n**')
        await ctx.send(embed=embed)

    @commands.command()
    async def bounty(self, ctx):
        """Check the server's current activity level"""
        activity = round(self.bot.latency * 1000)
        await ctx.send(f"The current bounty (activity level) of our Grand Line is **{activity} million Berries**! Looks like we're becoming infamous!")

    @commands.command()
    async def berries(self, ctx, user: discord.Member = commands.Author):
        """Get info about your Berries balance"""
        bal = await bank.get_balance(user)
        currency = await bank.get_currency_name(ctx.guild)
        embed = discord.Embed(title="Your Berries Balance", description=(f"** {bal} {currency}**"))
        await ctx.send(embed=embed)

    @commands.command()
    async def wanted(self, ctx):
        """Very WANTED Pirates leaderboard"""
        guild = ctx.guild
        msg = await bank.get_leaderboard(positions=100, guild=guild)
        embed = discord.Embed(title="Top 100 Most Wanted Pirates", description=(f"{msg}"))
        await ctx.send(embed=embed)

async def setup(bot: Red) -> None:
    global old_bounty
    old_bounty = bot.get_command("bounty")
    if old_bounty:
        bot.remove_command(old_bounty.name)
    cog = OnePieceServer(bot)
    await bot.add_cog(cog)
