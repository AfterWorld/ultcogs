import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import box

class OPWelcome:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def channel(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).welcome_channel.set(channel.id)
        await ctx.send(f"Welcome channel set to {channel.mention}")

    async def toggle(self, ctx):
        current = await self.config.guild(ctx.guild).welcome_enabled()
        await self.config.guild(ctx.guild).welcome_enabled.set(not current)
        state = "enabled" if not current else "disabled"
        await ctx.send(f"Welcome message {state}.")

    async def test(self, ctx):
        await self.on_member_join(ctx.author)
        
    async def on_member_join(self, member):
        guild = member.guild
        if not await self.config.guild(guild).welcome_enabled():
            return

        channel_id = await self.config.guild(guild).welcome_channel()
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        welcome_message = (
            f"Ahoy, {member.mention}! Welcome aboard the {guild.name} crew!\n\n"
            "You've just set sail on an incredible adventure in the world of One Piece!\n\n"
            f"{box('About One Piece', lang='css')}\n"
            "One Piece is an epic tale of pirates, adventure, and the search for the ultimate treasure - the One Piece. "
            "Join Monkey D. Luffy and his diverse crew as they navigate treacherous seas, face powerful enemies, "
            "and uncover the mysteries of the Grand Line.\n\n"
            f"{box('Server Information', lang='css')}\n"
            "🏴‍☠️ Crew Quarters (channels):\n"
            "• #rules-and-info - Essential laws of the sea\n"
            "• #general-chat - Main deck for casual conversations\n"
            "• #devil-fruit-discussion - Discuss powerful abilities\n"
            "• #bounty-board - Check your rank and rewards\n\n"
            f"{box('Adventure Awaits!', lang='css')}\n"
            "• Join battles with `.battle @opponent`\n"
            "• Start team battles with `.teambattle @teammate vs @opponent1 @opponent2`\n"
            "• Check your profile with `.profile`\n"
            "• Train your skills with `.train strength` (or defense/speed)\n"
            "• Explore islands with `.explore`\n"
            "• Join crews with `.join_crew <crew_name>`\n"
            "• Eat Devil Fruits with `.eat_devil_fruit <fruit_name>`\n\n"
            "Set sail, make friends, and carve your legend in the world of One Piece!"
        )

        await channel.send(welcome_message)
