"""
One Piece Discord Bot Cog for Red Discord Bot
"""

from .onepiece import OnePiece

def setup(bot):
    bot.add_cog(OnePiece(bot))
