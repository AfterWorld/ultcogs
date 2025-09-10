import discord
from datetime import datetime
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
from .constants import EMBED_COLOR_PENDING, EMBED_COLOR_APPROVED, EMBED_COLOR_DENIED


def get_vote_field(upvotes: int, downvotes: int) -> str:
    return f"👍 {upvotes} | 👎 {downvotes}"


def get_embed_color(status: str) -> discord.Color:
    if status == "approved":
        return EMBED_COLOR_APPROVED
    elif status == "denied":
        return EMBED_COLOR_DENIED
    return EMBED_COLOR_PENDING


def can_moderate_suggestions(member: discord.Member) -> bool:
    """
    Determine if a user can moderate suggestions.
    You can customize this to enforce role requirements.
    """
    if member.guild_permissions.administrator:
        return True
    allowed_roles = {"Admin", "Moderator", "Suggestions"}  # customize as needed
    return any(r.name in allowed_roles for r in member.roles)


def create_status_embed(
    suggestion_id: int,
    suggestion: str,
    status: str,
    moderator: discord.Member = None,
    reason: str = None,
    author: discord.Member = None,
) -> discord.Embed:
    color = get_embed_color(status)
    embed = discord.Embed(
        title=f"Suggestion #{suggestion_id}",
        description=suggestion,
        color=color,
        timestamp=datetime.now(),
    )

    if author:
        embed.set_author(name=str(author), icon_url=author.display_avatar.url)

    embed.add_field(name="Status", value=status.capitalize(), inline=True)

    if moderator:
        embed.add_field(name="Reviewed By", value=moderator.mention, inline=True)

    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)

    return embed


def format_blacklist_entry(user: discord.User, data: dict, ctx: commands.Context) -> str:
    moderator = ctx.guild.get_member(data.get("by")) if ctx.guild else None
    moderator_str = moderator.display_name if moderator else f"<@{data.get('by')}>"
    timestamp = datetime.fromtimestamp(data.get("timestamp", 0))
    reason = data.get("reason", "No reason provided")
    return f"**{user.mention}** - {reason}\n*Blacklisted by {moderator_str} on {timestamp.strftime('%Y-%m-%d')}*"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"
