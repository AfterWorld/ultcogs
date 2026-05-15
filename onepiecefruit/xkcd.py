"""
XKCD comic cog for Red-DiscordBot.
Fetches a random (or specific) comic from xkcd.com and posts it as an embed.
"""

import random
import aiohttp
import discord
from redbot.core import commands


XKCD_API = "https://xkcd.com/{num}/info.0.json"
XKCD_LATEST = "https://xkcd.com/info.0.json"


class XKCD(commands.Cog):
    """Post XKCD comics in Discord."""

    def __init__(self, bot):
        self.bot = bot

    async def _fetch_json(self, url: str) -> dict | None:
        """Fetch JSON from a URL using aiohttp. Returns None on error."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    async def _get_latest_num(self) -> int | None:
        """Return the number of the most recent XKCD comic."""
        data = await self._fetch_json(XKCD_LATEST)
        return data["num"] if data else None

    async def _build_embed(self, data: dict) -> discord.Embed:
        """Turn XKCD JSON into a Discord embed."""
        num = data["num"]
        embed = discord.Embed(
            title=f"#{num}: {data['title']}",
            url=f"https://xkcd.com/{num}/",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=data["img"])
        if data.get("alt"):
            # Alt text can be long — truncate to embed field limit
            alt = data["alt"]
            if len(alt) > 1024:
                alt = alt[:1021] + "..."
            embed.add_field(name="Alt text", value=f"*{alt}*", inline=False)
        embed.set_footer(text="xkcd.com • A webcomic of romance, sarcasm, math, and language.")
        return embed

    # ══════════════════════════════════════════════════════════════════════
    # Commands
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="xkcd")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def xkcd(self, ctx: commands.Context, num: int = 0):
        """
        Post an XKCD comic.

        Usage:
          `[p]xkcd`        — random comic
          `[p]xkcd 327`    — specific comic by number
          `[p]xkcd latest` — most recent comic (use `[p]xkcd 0` or the alias)
        """
        async with ctx.typing():
            latest = await self._get_latest_num()
            if latest is None:
                return await ctx.send("❌ Couldn't reach xkcd.com right now. Try again later.")

            if num == 0:
                # 0 → random
                num = random.randint(1, latest)
            elif num < 1 or num > latest:
                return await ctx.send(f"❌ Comic number must be between **1** and **{latest}**.")

            # Comic #404 literally doesn't exist (intentional joke by xkcd)
            if num == 404:
                embed = discord.Embed(
                    title="#404: Not Found",
                    url="https://xkcd.com/404/",
                    description="This comic intentionally does not exist. Classic Randall.",
                    color=discord.Color.red(),
                )
                embed.set_footer(text="xkcd.com")
                return await ctx.send(embed=embed)

            data = await self._fetch_json(XKCD_API.format(num=num))
            if data is None:
                return await ctx.send(f"❌ Couldn't fetch comic #{num}.")

        embed = await self._build_embed(data)
        await ctx.send(embed=embed)

    @commands.command(name="xkcdlatest", aliases=["xkcdnew"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def xkcd_latest(self, ctx: commands.Context):
        """Post the most recent XKCD comic."""
        async with ctx.typing():
            data = await self._fetch_json(XKCD_LATEST)
            if data is None:
                return await ctx.send("❌ Couldn't reach xkcd.com right now.")

        embed = await self._build_embed(data)
        await ctx.send(embed=embed)

    @xkcd.error
    @xkcd_latest.error
    async def _xkcd_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Cooldown — try again in **{error.retry_after:.1f}s**.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Please give a valid comic number, e.g. `[p]xkcd 327`.")
        else:
            raise error


async def setup(bot):
    await bot.add_cog(XKCD(bot))
