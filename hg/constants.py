# constants.py
"""Constants and configuration for the Hunger Games cog"""

# Game Configuration
DEFAULT_GUILD_CONFIG = {
    "games": {},
    "base_reward": 500,
    "sponsor_chance": 15,
    "event_interval": 30,
    "recruitment_time": 60,
}

DEFAULT_MEMBER_CONFIG = {
    "wins": 0,
    "deaths": 0,
    "kills": 0,
    "revives": 0
}

# Emojis
EMOJIS = {
    "bow": "🏹",
    "fire": "🔥",
    "skull": "💀",
    "sword": "⚔️",
    "explosion": "💥",
    "crown": "👑",
    "money": "💰",
    "heart": "❤️",
    "sponsor": "🎁",
    "trophy": "🏆"
}

# Death Events
DEATH_EVENTS = [
    "💀 {player} was hunted down by a pack of mutant wolves!",
    "⚡ {player} stepped on a landmine and was blown to pieces!",
    "🗡️ {player} was ambushed by {killer} with a rusty sword!",
    "🏹 {player} took an arrow to the heart from {killer}!",
    "🔥 {player} was burned alive in a forest fire!",
    "💧 {player} drowned while trying to cross a river!",
    "🐍 {player} was bitten by a venomous snake!",
    "🕷️ {player} was overwhelmed by tracker jackers!",
    "💣 {player} triggered an explosive trap!",
    "⚔️ {player} was defeated in combat by {killer}!",
    "🌪️ {player} was caught in a deadly tornado!",
    "❄️ {player} froze to death during the night!",
    "🦅 {player} was carried away by mutant birds!",
    "⚒️ {player} was crushed by falling rocks!",
    "🎯 {player} was shot by {killer} with a crossbow!",
    "🌋 {player} fell into a lava pit!",
    "⚡ {player} was struck by lightning!",
    "🦈 {player} was attacked by mutant fish!",
    "🔪 {player} was stabbed by {killer} in their sleep!",
    "💀 {player} ate poisonous berries!"
]

# Survival Events
SURVIVAL_EVENTS = [
    "🌿 {player} found a hidden cache of supplies!",
    "💊 {player} discovered medicine and healed their wounds!",
    "🍖 {player} successfully hunted a wild animal for food!",
    "💧 {player} found a clean water source!",
    "🏠 {player} discovered a safe shelter for the night!",
    "🔥 {player} started a fire to keep warm!",
    "🍄 {player} found edible berries (and they weren't poisonous)!",
    "🎒 {player} salvaged useful items from a fallen tribute!",
    "🗡️ {player} crafted a makeshift weapon!",
    "🌙 {player} successfully hid from other tributes!",
    "⚡ {player} avoided a deadly trap!",
    "🦋 {player} befriended some harmless butterflies!",
    "🌳 {player} climbed a tree to scout the area!",
    "🏃 {player} outran a pack of wild animals!",
    "🍯 {player} found honey and gained energy!",
    "🛡️ {player} crafted armor from animal hide!",
    "🎯 {player} practiced their aim with makeshift targets!",
    "🌺 {player} found healing herbs!",
    "💤 {player} got a good night's sleep!",
    "🦎 {player} caught and cooked a lizard!"
]

# Alliance Events
ALLIANCE_EVENTS = [
    "🤝 {player1} and {player2} formed an alliance!",
    "💔 {player1} betrayed their ally {player2}!",
    "🛡️ {player1} protected {player2} from an attack!",
    "🔥 {player1} and {player2} shared a campfire!",
    "🍖 {player1} shared food with {player2}!",
]

# Sponsor Events
SPONSOR_EVENTS = [
    "🎁 **SPONSOR GIFT!** {player} received a care package!",
    "💊 **SPONSOR GIFT!** {player} was given life-saving medicine!",
    "🗡️ **SPONSOR GIFT!** {player} received a weapon upgrade!",
    "🍖 **SPONSOR GIFT!** {player} was sent a feast!",
    "🛡️ **SPONSOR GIFT!** {player} received protective gear!",
]

# Revival Messages
REVIVAL_MESSAGES = [
    "✨ **MIRACLE!** {player} was revived by a generous sponsor!",
    "💫 **UNPRECEDENTED!** The Capitol has brought {player} back to life!",
    "🌟 **AMAZING!** {player} defied death with sponsor intervention!",
    "⚡ **SHOCKING!** {player} has been resurrected by mysterious forces!",
    "🎭 **DRAMATIC TWIST!** {player} returns from the dead!",
]

# District Names
DISTRICTS = {
    1: "Luxury",
    2: "Masonry", 
    3: "Technology",
    4: "Fishing",
    5: "Power",
    6: "Transportation",
    7: "Lumber",
    8: "Textiles",
    9: "Grain",
    10: "Livestock",
    11: "Agriculture",
    12: "Mining"
}

# Game Phases
GAME_PHASES = [
    "🌅 **DAWN** - The arena awakens...",
    "☀️ **MORNING** - The hunt continues...",
    "🌞 **MIDDAY** - The sun beats down mercilessly...",
    "🌇 **AFTERNOON** - Shadows grow longer...",
    "🌆 **EVENING** - Darkness approaches...",
    "🌙 **NIGHT** - Only the strongest survive the darkness...",
    "⭐ **MIDNIGHT** - The arena holds its breath...",
    "🌌 **LATE NIGHT** - Terror lurks in every shadow..."
]

# Final showdown messages
FINALE_MESSAGES = [
    "⚔️ **FINAL SHOWDOWN!** Only {count} tributes remain!",
    "🔥 **THE END APPROACHES!** {count} survivors left!",
    "💀 **BLOODBATH INCOMING!** {count} tributes fight for victory!",
    "👑 **CROWNING MOMENT!** {count} contenders for the crown!",
]

# Victory display constants
VICTORY_TITLE_ART = [
    """
```
╔═══════════════════════════╗
║     🏹 HUNGER GAMES 🏹     ║
║      BATTLE ROYALE        ║
╚═══════════════════════════╝
```""",
    """
```
┌─────────────────────────────┐
│    ⚔️  BATTLE ROYALE  ⚔️    │
│      HUNGER GAMES 2025      │
└─────────────────────────────┘
```""",
    """
```
╭─────────────────────────────╮
│   🔥 THE HUNGER GAMES 🔥    │
│     ULTIMATE SHOWDOWN       │
╰─────────────────────────────╯
```"""
]

# Placement medals and positions
PLACEMENT_MEDALS = {
    1: "👑",
    2: "🥈", 
    3: "🥉",
    4: "4️⃣",
    5: "5️⃣"
}

# Era themes for variety
GAME_ERAS = [
    "Futuristic",
    "Medieval", 
    "Post-Apocalyptic",
    "Steampunk",
    "Cyberpunk",
    "Wild West",
    "Ancient Rome",
    "Dystopian"
]
