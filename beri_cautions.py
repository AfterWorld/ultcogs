# -*- coding: utf-8 -*-
import discord
from redbot.core import commands, Config, checks
import time

class BeriCautions(commands.Cog):
    """Cautions system with Beri punishments and auto-mutes."""
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=987654321, force_registration=True)
        default_guild = {
            "cautions": {},
            "mute_role": None,
            "log_channel": None,
            "expiry_days": 30,
            "thresholds": {},
            "beri_fines": {
                "enabled": True,
                "per_point": 1000,
                "min": 0,
                "max": 250000,
                "thresholds": {},
            },
        }
        self.config.register_guild(**default_guild)

    async def _send(self, ctx, *, content=None, embed=None):
        return await ctx.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def caution(self, ctx, member: discord.Member, points: int, *, reason: str = "No reason"):
        g = await self.config.guild(ctx.guild).all()
        cautions = g["cautions"]
        uid = str(member.id)
        user_data = cautions.get(uid, {"points": 0, "history": []})
        user_data["points"] += points
        user_data["history"].append({"time": int(time.time()), "points": points, "reason": reason})
        cautions[uid] = user_data
        await self.config.guild(ctx.guild).cautions.set(cautions)

        fine_applied = ""
        if g["beri_fines"]["enabled"]:
            core = self.bot.get_cog("BeriCore")
            if core:
                per_point = g["beri_fines"]["per_point"]
                min_fine = g["beri_fines"]["min"]
                max_fine = g["beri_fines"]["max"]
                fine = max(min_fine, min(max_fine, per_point * points))
                await core.add_beri(member, -fine, reason=f"punish:caution:{reason}", actor=ctx.author, bypass_cap=True)
                fine_applied = f"\n💸 Fined **{fine}** Beri."

        await self._send(ctx, embed=discord.Embed(
            title="Caution Issued",
            description=f"{member.mention} cautioned for **{points}** points.\nReason: {reason}{fine_applied}",
            color=discord.Color.orange()
        ))

    @commands.group(name="cautionset", invoke_without_command=True)
    @checks.admin()
    async def cautionset(self, ctx):
        await self._send(ctx, embed=discord.Embed(title="Caution Settings", description="Subcommands: berifine, mute, log, expiry, thresholds", color=discord.Color.blurple()))

    @cautionset.group(name="berifine")
    async def cautionset_berifine(self, ctx):
        await self._send(ctx, embed=discord.Embed(title="Beri Fine Settings", description="Subcommands: toggle, perpoint, range, threshold", color=discord.Color.blurple()))

    @cautionset_berifine.command(name="toggle")
    async def berifine_toggle(self, ctx, value: bool):
        g = await self.config.guild(ctx.guild).all()
        g["beri_fines"]["enabled"] = value
        await self.config.guild(ctx.guild).set(g)
        await self._send(ctx, embed=discord.Embed(description=f"Beri fines enabled: {value}", color=discord.Color.green()))

    @cautionset_berifine.command(name="perpoint")
    async def berifine_perpoint(self, ctx, amount: int):
        g = await self.config.guild(ctx.guild).all()
        g["beri_fines"]["per_point"] = amount
        await self.config.guild(ctx.guild).set(g)
        await self._send(ctx, embed=discord.Embed(description=f"Per-point fine set to {amount} Beri.", color=discord.Color.green()))

    @cautionset_berifine.command(name="range")
    async def berifine_range(self, ctx, min_fine: int, max_fine: int):
        g = await self.config.guild(ctx.guild).all()
        g["beri_fines"]["min"] = min_fine
        g["beri_fines"]["max"] = max_fine
        await self.config.guild(ctx.guild).set(g)
        await self._send(ctx, embed=discord.Embed(description=f"Fine range set: {min_fine} - {max_fine} Beri.", color=discord.Color.green()))

    @cautionset_berifine.command(name="threshold")
    async def berifine_threshold(self, ctx, points: int, amount: int):
        g = await self.config.guild(ctx.guild).all()
        g["beri_fines"]["thresholds"][str(points)] = amount
        await self.config.guild(ctx.guild).set(g)
        await self._send(ctx, embed=discord.Embed(description=f"Threshold fine: {points} points = {amount} Beri", color=discord.Color.green()))


async def setup(bot):
    await bot.add_cog(BeriCautions(bot))
