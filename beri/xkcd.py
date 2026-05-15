"""
XKCD comic mixin for the Beri economy cog.
Fetches a random (or specific) comic from xkcd.com and posts it as an embed.
"""

import random
import aiohttp
import discord
from redbot.core import commands


XKCD_API = "https://xkcd.com/{num}/info.0.json"
XKCD_LATEST = "https://xkcd.com/info.0.json"


class XKCD(commands.Cog):
    """XKCD comic mixin. No external dependencies beyond aiohttp (bundled with Red)."""

    async def _xkcd_fetch(self, url: str) -> dict | None:
        """Fetch JSON from a URL. Returns None on any error."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    async def _xkcd_latest_num(self) -> int | None:
        """Return the number of the most recent XKCD comic."""
        data = await self._xkcd_fetch(XKCD_LATEST)
        return data["num"] if data else None

    async def _xkcd_embed(self, data: dict) -> discord.Embed:
        """Build a Discord embed from XKCD API JSON."""
        num = data["num"]
        embed = discord.Embed(
            title=f"#{num}: {data['title']}",
            url=f"https://xkcd.com/{num}/",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=data["img"])
        if data.get("alt"):
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
          `[p]xkcd`      — random comic
          `[p]xkcd 327`  — specific comic by number
        """
        async with ctx.typing():
            latest = await self._xkcd_latest_num()
            if latest is None:
                return await ctx.send("❌ Couldn't reach xkcd.com right now. Try again later.")

            if num == 0:
                num = random.randint(1, latest)
            elif num < 1 or num > latest:
                return await ctx.send(f"❌ Comic number must be between **1** and **{latest}**.")

            # #404 intentionally doesn't exist on xkcd (it's a joke)
            if num == 404:
                embed = discord.Embed(
                    title="#404: Not Found",
                    url="https://xkcd.com/404/",
                    description="This comic intentionally does not exist. Classic Randall.",
                    color=discord.Color.red(),
                )
                embed.set_footer(text="xkcd.com")
                return await ctx.send(embed=embed)

            data = await self._xkcd_fetch(XKCD_API.format(num=num))
            if data is None:
                return await ctx.send(f"❌ Couldn't fetch comic #{num}.")

        await ctx.send(embed=await self._xkcd_embed(data))

    @commands.command(name="xkcdlatest", aliases=["xkcdnew"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def xkcd_latest(self, ctx: commands.Context):
        """Post the most recent XKCD comic."""
        async with ctx.typing():
            data = await self._xkcd_fetch(XKCD_LATEST)
            if data is None:
                return await ctx.send("❌ Couldn't reach xkcd.com right now.")

        await ctx.send(embed=await self._xkcd_embed(data))

    @xkcd.error
    @xkcd_latest.error
    async def _xkcd_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Cooldown — try again in **{error.retry_after:.1f}s**.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Please give a valid comic number, e.g. `[p]xkcd 327`.")
        else:
            raise error
