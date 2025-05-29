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

# Death Events - Mixed Themes with Discord Markdown
DEATH_EVENTS = [
    "💀 | **{killer}** the Ruthless pushed ~~**{player}**~~ the Unlucky off the crow's nest into shark-infested waters!",
    "💀 | ~~**{player}**~~ the Foolhardy tried to tame themselves a wild kraken.",
    "💀 | **{killer}** the Merciless caught ~~**{player}**~~ the Greedy tryin' to plunder their grub. They didn't take that lightly.",
    "💀 | **{killer}** choked ~~**{player}**~~ the Sleepy while they were restin'. How treacherous!",
    "💀 | ~~**{player}**~~ the Careless stepped on a landmine in the abandoned wasteland.",
    "💀 | **{killer}** the Sharpshooter sniped ~~**{player}**~~ the Wanderer from across the battlefield!",
    "💀 | ~~**{player}**~~ the Brave was overwhelmed by a pack of cyber-wolves in the neon district.",
    "💀 | **{killer}** the Backstabber ambushed ~~**{player}**~~ the Trusting with a rusty blade in the alleyway!",
    "💀 | ~~**{player}**~~ the Curious got vaporized by alien technology they shouldn't have touched.",
    "💀 | **{killer}** the Vengeful threw ~~**{player}**~~ the Weak into the gladiator pit with the lions!",
    "💀 | ~~**{player}**~~ the Reckless froze to death in the nuclear winter storms.",
    "💀 | **{killer}** the Hunter tracked down ~~**{player}**~~ the Prey and finished them with a crossbow bolt!",
    "💀 | ~~**{player}**~~ the Lost fell into a lava pit while exploring the volcanic caves.",
    "💀 | **{killer}** the Poisoner slipped deadly toxins into ~~**{player}**~~ the Trusting's water supply!",
    "💀 | ~~**{player}**~~ the Unlucky was struck by lightning during the electromagnetic storm.",
    "💀 | **{killer}** the Savage mauled ~~**{player}**~~ the Defenseless with their bare hands in a frenzy!",
    "💀 | ~~**{player}**~~ the Clumsy drowned in the flooded subway tunnels.",
    "💀 | **{killer}** the Sniper picked off ~~**{player}**~~ the Exposed from their hidden perch!",
    "💀 | ~~**{player}**~~ the Hungry ate poisonous berries thinking they were safe to consume.",
    "💀 | **{killer}** the Ruthless strangled ~~**{player}**~~ the Victim in their sleep with a garrote wire!",
    "💀 | ~~**{player}**~~ the Explorer was devoured by mutant spiders in the abandoned laboratory.",
    "💀 | **{killer}** the Demolisher crushed ~~**{player}**~~ the Unfortunate under falling debris!",
    "💀 | ~~**{player}**~~ the Traveler was consumed by acid rain in the toxic wasteland.",
    "💀 | **{killer}** the Executioner beheaded ~~**{player}**~~ the Condemned with a ceremonial sword!"
]

# Survival Events - Mixed Themes with Discord Markdown  
SURVIVAL_EVENTS = [
    "🌿 | **{player}** the Resourceful found a hidden cache of supplies in an abandoned bunker!",
    "💊 | **{player}** the Lucky discovered medical supplies and __*healed their wounds*__!",
    "🍖 | **{player}** the Hunter successfully trapped a wild boar for a hearty meal!",
    "💧 | **{player}** the Survivor located a clean water source in the desert oasis!",
    "🏠 | **{player}** the Smart discovered a safe shelter in the ruined castle!",
    "🔥 | **{player}** the Prepared started a fire to keep warm during the cold night!",
    "🍄 | **{player}** the Wise found edible mushrooms (and they weren't poisonous)!",
    "🎒 | **{player}** the Scavenger salvaged useful gear from a fallen tribute's backpack!",
    "🗡️ | **{player}** the Crafty forged a makeshift weapon from scrap metal!",
    "🌙 | **{player}** the Stealthy successfully hid from other tributes in the shadows!",
    "⚡ | **{player}** the Alert avoided a deadly trap by pure instinct!",
    "🦋 | **{player}** the Peaceful made friends with some harmless butterflies!",
    "🌳 | **{player}** the Agile climbed a massive tree to scout the surrounding area!",
    "🏃 | **{player}** the Fast outran a pack of radioactive wolves!",
    "🍯 | **{player}** the Forager found honey and __*gained energy*__ for the trials ahead!",
    "🛡️ | **{player}** the Engineer crafted armor from salvaged vehicle parts!",
    "🎯 | **{player}** the Marksman practiced their aim with makeshift targets!",
    "🌺 | **{player}** the Herbalist discovered healing herbs in the jungle!",
    "💤 | **{player}** the Tired got a good night's sleep in their hidden cave!",
    "🦎 | **{player}** the Survivor caught and cooked a lizard over their campfire!",
    "🔧 | **{player}** the Mechanic __*repaired their equipment*__ using spare parts!",
    "🎵 | **{player}** the Musician played a tune that __*boosted their morale*__!",
    "💎 | **{player}** the Explorer discovered valuable gems in the crystal caves!",
    "🗺️ | **{player}** the Navigator found an ancient map showing secret passages!",
    "🧪 | **{player}** the Chemist brewed a __*stamina potion*__ from local plants!"
]

# Alliance Events - Mixed Themes with Discord Markdown
ALLIANCE_EVENTS = [
    "🤝 | **{player1}** the Diplomatic and **{player2}** the Trustworthy __*formed an alliance*__ by the campfire!",
    "💔 | **{player1}** the Treacherous __*betrayed their ally*__ ~~**{player2}**~~ the Naive for their supplies!",
    "🛡️ | **{player1}** the Loyal protected **{player2}** the Vulnerable from a sneak attack!",
    "🔥 | **{player1}** the Kind and **{player2}** the Grateful __*shared a campfire*__ during the cold night!",
    "🍖 | **{player1}** the Generous shared their last meal with **{player2}** the Starving!",
    "⚔️ | **{player1}** the Fierce and **{player2}** the Brave __*teamed up*__ to raid the supply depot!",
    "🗣️ | **{player1}** the Strategist and **{player2}** the Follower __*planned their next move*__ together!",
    "💰 | **{player1}** the Collector and **{player2}** the Partner __*agreed to split*__ any treasure they find!",
    "🏥 | **{player1}** the Medic tended to **{player2}** the Injured's wounds with __*makeshift bandages*__!",
    "🎯 | **{player1}** the Mentor taught **{player2}** the Student how to __*use their weapon*__ properly!"
]

# Sponsor Events - Mixed Themes with Discord Markdown
SPONSOR_EVENTS = [
    "🎁 | **SPONSOR GIFT!** **{player}** the Favored __*received a care package*__ dropped from the sky!",
    "💊 | **SPONSOR GIFT!** **{player}** the Lucky was given __*life-saving medicine*__ by mysterious benefactor!",
    "🗡️ | **SPONSOR GIFT!** **{player}** the Warrior __*received a weapon upgrade*__ from their sponsor!",
    "🍖 | **SPONSOR GIFT!** **{player}** the Hungry was sent a __*feast fit for a king*__!",
    "🛡️ | **SPONSOR GIFT!** **{player}** the Survivor __*received protective gear*__ just in time!",
    "🔋 | **SPONSOR GIFT!** **{player}** the Tech-Savvy got __*high-tech equipment*__ from their sponsor!",
    "🧪 | **SPONSOR GIFT!** **{player}** the Alchemist received __*experimental enhancement serum*__!",
    "🎒 | **SPONSOR GIFT!** **{player}** the Prepared was given a __*fully stocked survival kit*__!",
    "💰 | **SPONSOR GIFT!** **{player}** the Wealthy received __*valuable currency*__ from their patron!",
    "🗺️ | **SPONSOR GIFT!** **{player}** the Navigator was sent __*detailed maps*__ of the arena!"
]

# Revival Messages - Enhanced with Discord Markdown
REVIVAL_MESSAGES = [
    "✨ | **MIRACLE!** ~~**{player}**~~ the Fallen was __*revived by a generous sponsor*__!",
    "💫 | **UNPRECEDENTED!** The Capitol has __*brought*__ ~~**{player}**~~ the Deceased __*back to life*__!",
    "🌟 | **AMAZING!** ~~**{player}**~~ the Lost __*defied death*__ with sponsor intervention!",
    "⚡ | **SHOCKING!** ~~**{player}**~~ the Gone has been __*resurrected by mysterious forces*__!",
    "🎭 | **DRAMATIC TWIST!** ~~**{player}**~~ the Dead __*returns from beyond*__ the veil!",
    "🔮 | **MYSTICAL!** Ancient magic has __*restored*__ ~~**{player}**~~ the Departed __*to the living*__!",
    "🧬 | **SCIENTIFIC BREAKTHROUGH!** Advanced technology __*regenerated*__ ~~**{player}**~~ the Eliminated!",
    "👻 | **SUPERNATURAL!** ~~**{player}**~~ the Spirit __*materialized back*__ into physical form!"
]

# District Names - Varied and Creative Themes
DISTRICTS = {
    1: "The Neon Metropolis",
    2: "The Frozen Wasteland", 
    3: "The Floating Islands",
    4: "The Underground Caverns",
    5: "The Cyber District",
    6: "The Savage Jungle",
    7: "The Desert Oasis",
    8: "The Sky Fortress",
    9: "The Sunken City",
    10: "The Volcanic Peaks",
    11: "The Crystal Mines",
    12: "The Shadow Realm"
}

# Player Titles/Epithets for Flavor
PLAYER_TITLES = [
    "the Ambitious", "the Ruthless", "the Cunning", "the Brave", "the Wise",
    "the Fierce", "the Clever", "the Strong", "the Swift", "the Silent",
    "the Bold", "the Crafty", "the Noble", "the Wild", "the Mystic",
    "the Deadly", "the Lucky", "the Cursed", "the Ancient", "the Young",
    "the Scarred", "the Pure", "the Dark", "the Bright", "the Forgotten",
    "the Legendary", "the Humble", "the Proud", "the Broken", "the Whole",
    "the Lost", "the Found", "the First", "the Last", "the Chosen",
    "the Banished", "the Returned", "the Seeker", "the Guardian", "the Destroyer",
    "the Creator", "the Wanderer", "the Settler", "the Rebel", "the Loyal",
    "the Mad", "the Sane", "the Dreamer", "the Realist", "the Optimist"
]

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
