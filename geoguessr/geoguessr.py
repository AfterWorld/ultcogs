"""
GeoGuessr-style Discord game cog for Red-Bot.
Requires: Google Street View Static API key + Google Maps Geocoding API key.
Set keys with: [p]geoset streetview_key <key> and [p]geoset maps_key <key>
"""

import asyncio
import math
import random
import time
from typing import Optional

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Approximate bounding boxes for "Street View friendly" regions
# (areas with high Street View coverage)
REGIONS = {
    "world": {"lat": (-60, 70), "lon": (-180, 180)},
    "europe": {"lat": (36, 70), "lon": (-10, 40)},
    "north_america": {"lat": (25, 70), "lon": (-168, -52)},
    "south_america": {"lat": (-55, 13), "lon": (-82, -34)},
    "asia": {"lat": (1, 55), "lon": (26, 145)},
    "oceania": {"lat": (-47, -10), "lon": (113, 178)},
}

# Countries with very high Street View coverage — used for random sampling
# to avoid getting empty ocean tiles constantly
SV_FRIENDLY_COORDS = [
    # USA scatter
    (40.7128, -74.0060), (34.0522, -118.2437), (41.8781, -87.6298),
    (29.7604, -95.3698), (33.4484, -112.0740), (39.9526, -75.1652),
    (29.4241, -98.4936), (32.7157, -117.1611), (32.7767, -96.7970),
    (30.3322, -81.6557), (47.6062, -122.3321), (25.7617, -80.1918),
    (44.9778, -93.2650), (36.1699, -115.1398), (38.9072, -77.0369),
    # Europe
    (51.5074, -0.1278), (48.8566, 2.3522), (52.5200, 13.4050),
    (41.9028, 12.4964), (40.4168, -3.7038), (52.3676, 4.9041),
    (50.0755, 14.4378), (47.4979, 19.0402), (59.9139, 10.7522),
    (55.6761, 12.5683), (60.1699, 24.9384), (53.3498, -6.2603),
    (45.4642, 9.1900), (37.9838, 23.7275), (38.7223, -9.1393),
    # South America
    (-23.5505, -46.6333), (-34.6037, -58.3816), (-33.4489, -70.6693),
    (-12.0464, -77.0428), (4.7110, -74.0721), (-0.1807, -78.4678),
    # Asia
    (35.6762, 139.6503), (37.5665, 126.9780), (25.0330, 121.5654),
    (1.3521, 103.8198), (13.7563, 100.5018), (14.5995, 120.9842),
    (22.3193, 114.1694), (-6.2088, 106.8456),
    # Oceania
    (-33.8688, 151.2093), (-37.8136, 144.9631), (-36.8485, 174.7633),
    # Canada
    (43.6532, -79.3832), (45.5017, -73.5673), (49.2827, -123.1207),
    # Africa (limited but some coverage)
    (-26.2041, 28.0473), (-33.9249, 18.4241), (30.0444, 31.2357),
    (-1.2921, 36.8219),
]

GUESS_TIMEOUT = 90       # seconds players have to guess
MAX_SCORE = 5000          # perfect score per round
EARTH_RADIUS_KM = 6371


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Return distance in km between two lat/lon points."""
    r = EARTH_RADIUS_KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_to_score(km: float) -> int:
    """Convert km distance to a 0-5000 score (GeoGuessr-style curve)."""
    if km < 0.05:
        return MAX_SCORE
    # Exponential decay: full marks within ~25 km, roughly 0 at ~5000 km
    score = MAX_SCORE * math.exp(-km / 2000)
    return max(0, round(score))


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class GeoGuessr(commands.Cog):
    """A GeoGuessr-style game using Google Street View."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)

        default_guild = {
            "streetview_key": None,   # Google Street View Static API key
            "maps_key": None,         # Google Maps Geocoding API key
            "active_game": None,      # dict with current game state
        }
        default_member = {
            "total_score": 0,
            "games_played": 0,
            "best_round": 0,
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        # In-memory game state per guild: {guild_id: game_dict}
        self.active_games: dict = {}

    # ------------------------------------------------------------------
    # Setup commands
    # ------------------------------------------------------------------

    @commands.group(name="geoset")
    @commands.admin_or_permissions(manage_guild=True)
    async def geoset(self, ctx: commands.Context):
        """Configure the GeoGuessr cog (admin only)."""

    @geoset.command(name="streetview_key")
    async def set_sv_key(self, ctx: commands.Context, key: str):
        """Set the Google Street View Static API key."""
        await self.config.guild(ctx.guild).streetview_key.set(key)
        await ctx.message.delete()  # hide the key from chat
        await ctx.send("✅ Street View API key saved.", delete_after=5)

    @geoset.command(name="maps_key")
    async def set_maps_key(self, ctx: commands.Context, key: str):
        """Set the Google Maps Geocoding API key (for guesses)."""
        await self.config.guild(ctx.guild).maps_key.set(key)
        await ctx.message.delete()
        await ctx.send("✅ Maps Geocoding API key saved.", delete_after=5)

    # ------------------------------------------------------------------
    # Game commands
    # ------------------------------------------------------------------

    @commands.group(name="geo", invoke_without_command=True)
    async def geo(self, ctx: commands.Context):
        """GeoGuessr-style location guessing game."""
        await ctx.send_help()

    @geo.command(name="start")
    @commands.guild_only()
    async def geo_start(self, ctx: commands.Context, region: str = "world"):
        """Start a new GeoGuessr round.\n\nRegions: world, europe, north_america, south_america, asia, oceania"""
        guild_id = ctx.guild.id

        if guild_id in self.active_games:
            await ctx.send("⚠️ A game is already running! Use `[p]geo stop` to end it.")
            return

        sv_key = await self.config.guild(ctx.guild).streetview_key()
        maps_key = await self.config.guild(ctx.guild).maps_key()
        if not sv_key or not maps_key:
            await ctx.send(
                "❌ API keys not configured. An admin needs to run:\n"
                "`[p]geoset streetview_key <key>`\n"
                "`[p]geoset maps_key <key>`"
            )
            return

        region = region.lower()
        if region not in REGIONS:
            await ctx.send(f"❌ Unknown region `{region}`. Choose from: {', '.join(REGIONS)}")
            return

        await ctx.send(f"🌍 Finding a Street View location ({region})…")

        lat, lon, image_url, sv_status = await self._find_street_view(sv_key, region)
        if not image_url:
            if sv_status == "REQUEST_DENIED":
                await ctx.send(
                    "❌ **REQUEST_DENIED** — Google rejected the API key.\n"
                    "Check that **Street View Static API** is enabled in your Google Cloud project "
                    "and that billing is active."
                )
            elif sv_status == "OVER_DAILY_LIMIT":
                await ctx.send("❌ **OVER_DAILY_LIMIT** — Quota exceeded for today.")
            else:
                await ctx.send(f"❌ Couldn't find a Street View image. (status: `{sv_status}`) Try again!")
            return

        game = {
            "channel_id": ctx.channel.id,
            "lat": lat,
            "lon": lon,
            "image_url": image_url,
            "region": region,
            "start_time": time.time(),
            "guesses": {},        # {user_id: {"lat": x, "lon": y, "score": n, "km": d}}
            "ended": False,
        }
        self.active_games[guild_id] = game

        embed = discord.Embed(
            title="🌍 Where in the World?",
            description=(
                f"**Region:** {region.replace('_', ' ').title()}\n\n"
                f"Use `[p]geo guess <city, country>` to submit your answer!\n"
                f"You have **{GUESS_TIMEOUT} seconds**. Multiple players can guess!"
            ),
            color=discord.Color.green(),
        )
        embed.set_image(url=image_url)
        embed.set_footer(text=f"Timer started • {GUESS_TIMEOUT}s remaining")
        await ctx.send(embed=embed)

        # Auto-end after timeout
        self.bot.loop.create_task(self._game_timer(ctx, guild_id))

    @geo.command(name="guess")
    @commands.guild_only()
    async def geo_guess(self, ctx: commands.Context, *, location: str):
        """Guess the location, e.g. `[p]geo guess Paris, France`"""
        guild_id = ctx.guild.id
        game = self.active_games.get(guild_id)

        if not game:
            await ctx.send("No active game! Start one with `[p]geo start`.")
            return
        if game["ended"]:
            await ctx.send("This round has already ended.")
            return
        if ctx.author.id in game["guesses"]:
            await ctx.send("You've already guessed this round!")
            return

        maps_key = await self.config.guild(ctx.guild).maps_key()
        guess_lat, guess_lon = await self._geocode(maps_key, location)

        if guess_lat is None:
            await ctx.send(f"❌ Couldn't find `{location}` on the map. Try a more specific location.")
            return

        km = haversine(game["lat"], game["lon"], guess_lat, guess_lon)
        score = distance_to_score(km)

        game["guesses"][ctx.author.id] = {
            "name": str(ctx.author.display_name),
            "lat": guess_lat,
            "lon": guess_lon,
            "km": km,
            "score": score,
            "location_name": location,
        }

        # Update persistent stats
        member_conf = self.config.member(ctx.author)
        async with member_conf.all() as member_data:
            member_data["total_score"] += score
            member_data["games_played"] += 1
            if score > member_data["best_round"]:
                member_data["best_round"] = score

        # Give quick feedback
        if score >= 4500:
            reaction = "🎯 **Incredible!**"
        elif score >= 3500:
            reaction = "🔥 **Great guess!**"
        elif score >= 2000:
            reaction = "👍 **Not bad!**"
        elif score >= 500:
            reaction = "😬 **Getting there…**"
        else:
            reaction = "💀 **Way off!**"

        await ctx.send(
            f"{reaction} **{ctx.author.display_name}** guessed `{location}` — "
            f"**{km:.0f} km** away → **{score:,} pts**"
        )

    @geo.command(name="stop")
    @commands.guild_only()
    async def geo_stop(self, ctx: commands.Context):
        """End the current round early and reveal the answer."""
        guild_id = ctx.guild.id
        if guild_id not in self.active_games:
            await ctx.send("No active game to stop.")
            return
        await self._end_game(ctx.guild, ctx.channel)

    @geo.command(name="leaderboard", aliases=["lb", "scores"])
    @commands.guild_only()
    async def geo_leaderboard(self, ctx: commands.Context):
        """Show the all-time leaderboard for this server."""
        all_members = await self.config.all_members(ctx.guild)
        if not all_members:
            await ctx.send("No scores recorded yet!")
            return

        sorted_members = sorted(
            all_members.items(),
            key=lambda x: x[1].get("total_score", 0),
            reverse=True,
        )[:10]

        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        lines = []
        for i, (uid, data) in enumerate(sorted_members):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            lines.append(
                f"{medals[i]} **{name}** — {data['total_score']:,} pts "
                f"({data['games_played']} rounds, best: {data['best_round']:,})"
            )

        embed = discord.Embed(
            title="🌍 GeoGuessr Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

    @geo.command(name="stats")
    @commands.guild_only()
    async def geo_stats(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Show your stats (or another member's)."""
        target = member or ctx.author
        data = await self.config.member(target).all()

        embed = discord.Embed(
            title=f"📊 Stats for {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Total Score", value=f"{data['total_score']:,} pts")
        embed.add_field(name="Rounds Played", value=str(data["games_played"]))
        embed.add_field(name="Best Round", value=f"{data['best_round']:,} pts")
        avg = data["total_score"] // data["games_played"] if data["games_played"] else 0
        embed.add_field(name="Avg per Round", value=f"{avg:,} pts")
        await ctx.send(embed=embed)

    @geo.command(name="help")
    async def geo_help(self, ctx: commands.Context):
        """Show how to play."""
        embed = discord.Embed(
            title="🌍 How to Play GeoGuessr",
            color=discord.Color.green(),
            description=(
                "A Street View image is posted — guess where in the world it was taken!\n\n"
                "**Commands**\n"
                "`[p]geo start [region]` — Start a new round\n"
                "`[p]geo guess <location>` — Submit your guess\n"
                "`[p]geo stop` — End the round early\n"
                "`[p]geo leaderboard` — All-time scores\n"
                "`[p]geo stats [@user]` — Personal stats\n\n"
                "**Regions**\n"
                "`world` • `europe` • `north_america` • `south_america` • `asia` • `oceania`\n\n"
                "**Scoring**\n"
                "Up to **5,000 pts** per round based on distance.\n"
                "Perfect guess (within city) = 5,000 pts 🎯\n"
                "All players can guess — fastest correct guess wins bragging rights!\n\n"
                f"⏱️ **{GUESS_TIMEOUT} seconds** per round."
            ),
        )
        await ctx.send(embed=embed)

    @geo.command(name="debug")
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def geo_debug(self, ctx: commands.Context):
        """Test your API keys and show exactly what Google returns. (Admin only)"""
        sv_key = await self.config.guild(ctx.guild).streetview_key()
        maps_key = await self.config.guild(ctx.guild).maps_key()

        lines = []
        lines.append(f"**Street View key set:** {'✅' if sv_key else '❌ not set'}")
        lines.append(f"**Maps key set:** {'✅' if maps_key else '❌ not set'}")

        if sv_key:
            # Test Street View metadata on a known-good location (Times Square)
            meta_url = (
                f"https://maps.googleapis.com/maps/api/streetview/metadata"
                f"?location=40.7580,-73.9855&key={sv_key}"
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(meta_url) as resp:
                        data = await resp.json(content_type=None)
                status = data.get("status", "NO_STATUS")
                lines.append(f"**Street View metadata test:** `{status}`")
                if status == "REQUEST_DENIED":
                    lines.append("→ Key is invalid, API not enabled, or billing not active.")
                elif status == "OK":
                    lines.append("→ Street View key is working ✅")
            except Exception as e:
                lines.append(f"**Street View metadata test:** EXCEPTION — `{e}`")

        if maps_key:
            # Test Geocoding on "Paris, France"
            from urllib.parse import quote as url_quote
            geo_url = (
                f"https://maps.googleapis.com/maps/api/geocode/json"
                f"?address={url_quote('Paris, France')}&key={maps_key}"
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(geo_url) as resp:
                        data = await resp.json(content_type=None)
                status = data.get("status", "NO_STATUS")
                lines.append(f"**Geocoding test (Paris, France):** `{status}`")
                if status == "REQUEST_DENIED":
                    lines.append("→ Key is invalid, Geocoding API not enabled, or billing not active.")
                elif status == "OK":
                    loc = data["results"][0]["geometry"]["location"]
                    lines.append(f"→ Geocoding key is working ✅ (got {loc['lat']:.3f}, {loc['lng']:.3f})")
            except Exception as e:
                lines.append(f"**Geocoding test:** EXCEPTION — `{e}`")

        embed = discord.Embed(title="🔧 GeoGuessr Debug", description="\n".join(lines), color=discord.Color.blurple())
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_street_view(self, api_key: str, region: str):
        """
        Try random coordinates until we find one with Street View coverage.
        Returns (lat, lon, image_url, last_status) — last_status is the final
        Google API status string, useful for debugging failures.
        """
        bounds = REGIONS[region]
        last_status = "NO_ATTEMPTS"

        for attempt in range(20):
            if attempt < 14:
                base = random.choice(SV_FRIENDLY_COORDS)
                lat = base[0] + random.uniform(-2, 2)
                lon = base[1] + random.uniform(-2, 2)
                lat = max(bounds["lat"][0], min(bounds["lat"][1], lat))
                lon = max(bounds["lon"][0], min(bounds["lon"][1], lon))
            else:
                lat = random.uniform(*bounds["lat"])
                lon = random.uniform(*bounds["lon"])

            meta_url = (
                f"https://maps.googleapis.com/maps/api/streetview/metadata"
                f"?location={lat},{lon}&radius=5000&key={api_key}"
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(meta_url) as resp:
                        data = await resp.json(content_type=None)
            except Exception as e:
                last_status = f"EXCEPTION: {e}"
                continue

            last_status = data.get("status", "UNKNOWN")

            if last_status != "OK":
                # If it's a key/billing error there's no point retrying
                if last_status in ("REQUEST_DENIED", "INVALID_REQUEST", "OVER_DAILY_LIMIT"):
                    break
                continue

            snapped = data.get("location", {})
            lat = snapped.get("lat", lat)
            lon = snapped.get("lng", lon)

            image_url = (
                f"https://maps.googleapis.com/maps/api/streetview"
                f"?size=640x400&location={lat},{lon}"
                f"&fov={random.randint(80, 110)}"
                f"&heading={random.randint(0, 359)}"
                f"&pitch={random.randint(-10, 10)}"
                f"&key={api_key}"
            )
            return lat, lon, image_url, "OK"

        return None, None, None, last_status

    async def _geocode(self, api_key: str, location: str):
        """Convert a place name to lat/lon using the Geocoding API."""
        from urllib.parse import quote as url_quote
        url = (
            f"https://maps.googleapis.com/maps/api/geocode/json"
            f"?address={url_quote(location)}&key={api_key}"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json(content_type=None)
            if data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return loc["lat"], loc["lng"]
        except Exception:
            pass
        return None, None

    async def _game_timer(self, ctx: commands.Context, guild_id: int):
        """Wait for GUESS_TIMEOUT then end the game automatically."""
        await asyncio.sleep(GUESS_TIMEOUT)
        if guild_id in self.active_games and not self.active_games[guild_id]["ended"]:
            channel = self.bot.get_channel(self.active_games[guild_id]["channel_id"])
            await self._end_game(ctx.guild, channel)

    async def _end_game(self, guild: discord.Guild, channel: discord.TextChannel):
        """Reveal the answer and post the round results."""
        guild_id = guild.id
        game = self.active_games.pop(guild_id, None)
        if not game:
            return
        game["ended"] = True

        lat, lon = game["lat"], game["lon"]
        guesses = game["guesses"]

        # Build results embed
        embed = discord.Embed(
            title="⏱️ Time's Up! Here's the Answer",
            color=discord.Color.orange(),
        )

        # Google Maps static image showing the answer pin
        answer_map = (
            f"https://maps.googleapis.com/maps/api/staticmap"
            f"?center={lat},{lon}&zoom=5&size=640x300"
            f"&markers=color:red%7C{lat},{lon}"
            f"&key={await self.config.guild(guild).streetview_key()}"
        )
        embed.set_image(url=answer_map)
        embed.add_field(
            name="📍 Location",
            value=f"[{lat:.4f}, {lon:.4f}](https://www.google.com/maps?q={lat},{lon})",
            inline=False,
        )

        if guesses:
            sorted_guesses = sorted(guesses.values(), key=lambda x: x["score"], reverse=True)
            result_lines = []
            medals = ["🥇", "🥈", "🥉"] + ["▪️"] * 20
            for i, g in enumerate(sorted_guesses):
                result_lines.append(
                    f"{medals[i]} **{g['name']}** — `{g['location_name']}` "
                    f"| **{g['km']:.0f} km** away | **{g['score']:,} pts**"
                )
            embed.add_field(name="📊 Round Results", value="\n".join(result_lines), inline=False)
        else:
            embed.add_field(name="📊 Round Results", value="Nobody guessed! 😢", inline=False)

        embed.set_footer(text="Use [p]geo start to play again • [p]geo leaderboard for all-time scores")
        await channel.send(embed=embed)