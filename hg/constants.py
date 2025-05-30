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

VICTORY_PHRASES = [
    "🏆 **WINNER!**",
    "👑 **CHAMPION!**", 
    "🎯 **VICTOR!**",
    "⚔️ **SURVIVOR!**",
    "🔥 **DOMINATION!**",
    "💀 **LAST STANDING!**",
    "🌟 **LEGENDARY!**",
    "⚡ **ULTIMATE VICTOR!**",
    "🎭 **TRIUMPHANT!**",
    "💎 **SUPREME VICTOR!**",
    "🏹 **ARENA MASTER!**",
    "🎪 **SPECTACULAR VICTORY!**"
]

GIF_CATEGORIES = {
    "victory": {
        "general": [],  # General victory GIFs
        "high_kill": [],  # For winners with 3+ kills
        "underdog": [],  # For winners with 0 kills
        "final_duel": [],  # For 2-player games
        "bloodbath": []  # For very high kill games
    },
    "death": [],
    "sponsor": [],
    "revival": []
}

# Placeholder for future GIF functionality
ENABLE_GIFS = False  # Set to True when GIF system is implemented
GIF_FOLDER_PATH = "gifs/"  # Folder path for GIF files

# Player Emoji Mappings based on titles and performance
TITLE_EMOJIS = {
    # Temperature/Element based
    "cold": "❄️", "ice": "❄️", "frozen": "❄️", "winter": "❄️",
    "fire": "🔥", "flame": "🔥", "burning": "🔥", "hot": "🔥",
    "storm": "⛈️", "thunder": "⚡", "lightning": "⚡",
    
    # Color/Light based
    "shadow": "🌙", "dark": "🌑", "night": "🌙", "black": "⚫",
    "light": "☀️", "bright": "☀️", "golden": "🌟", "white": "⚪",
    "red": "🔴", "blood": "🩸", "crimson": "🔴",
    "blue": "🔵", "azure": "💙", "sapphire": "💎",
    "green": "🟢", "emerald": "💚", "jade": "💚",
    
    # Nature based
    "wild": "🐺", "savage": "🐺", "beast": "🐺", "wolf": "🐺",
    "eagle": "🦅", "hawk": "🦅", "falcon": "🦅",
    "lion": "🦁", "tiger": "🐅", "bear": "🐻",
    "snake": "🐍", "viper": "🐍", "serpent": "🐍",
    
    # Status/Personality based
    "noble": "👑", "royal": "👑", "king": "👑", "queen": "👑",
    "wise": "🧠", "sage": "🧠", "clever": "🧠", "smart": "🧠",
    "swift": "⚡", "quick": "⚡", "fast": "💨", "speedy": "💨",
    "strong": "💪", "mighty": "💪", "powerful": "💪",
    "silent": "🤫", "quiet": "🤫", "stealth": "👤",
    "lucky": "🍀", "fortunate": "🍀", "blessed": "✨",
    "cursed": "💀", "doomed": "💀", "damned": "💀",
    "broken": "💔", "shattered": "💔", "wounded": "🩹",
    
    # Combat based
    "deadly": "💀", "killer": "💀", "death": "💀", "reaper": "💀",
    "warrior": "⚔️", "fighter": "⚔️", "soldier": "⚔️",
    "hunter": "🏹", "archer": "🏹", "marksman": "🎯",
    "blade": "🗡️", "sword": "🗡️", "knife": "🔪",
    
    # Mystical/Fantasy based
    "mystic": "🔮", "magic": "🔮", "wizard": "🧙", "witch": "🧙‍♀️",
    "dragon": "🐉", "phoenix": "🔥", "angel": "😇", "demon": "😈",
    "ghost": "👻", "spirit": "👻", "soul": "👻",
    
    # Default fallbacks for kill counts
    "default_high_kill": "💀",  # 5+ kills
    "default_medium_kill": "⚔️",  # 3-4 kills  
    "default_low_kill": "🗡️",  # 1-2 kills
    "default_no_kill": "🏹"  # 0 kills
}

# Victory messages based on different scenarios
VICTORY_SCENARIOS = {
    "high_kill": [  # 5+ kills
        "🔥 **ABSOLUTE DOMINATION!**",
        "💀 **MERCILESS CHAMPION!**",
        "⚔️ **ARENA DESTROYER!**",
        "🩸 **BLOODTHIRSTY VICTOR!**"
    ],
    "medium_kill": [  # 3-4 kills
        "⚔️ **SKILLED WARRIOR!**",
        "🎯 **TACTICAL VICTOR!**",
        "🔥 **BATTLE MASTER!**",
        "🏹 **DEADLY CHAMPION!**"
    ],
    "low_kill": [  # 1-2 kills
        "🛡️ **STRATEGIC SURVIVOR!**",
        "🎭 **CUNNING CHAMPION!**",
        "🌟 **CLEVER VICTOR!**",
        "🦉 **WISE WINNER!**"
    ],
    "no_kill": [  # 0 kills (pure survival)
        "🕊️ **PEACEFUL CHAMPION!**",
        "🦋 **SURVIVAL MASTER!**",
        "🌿 **NATURE'S CHOSEN!**",
        "✨ **MIRACLE SURVIVOR!**"
    ],
    "underdog": [  # Small games or came from behind
        "⚡ **UNDERDOG TRIUMPH!**",
        "🌟 **AGAINST ALL ODDS!**",
        "🎪 **SPECTACULAR UPSET!**",
        "💫 **MIRACLE VICTORY!**"
    ],
    "final_duel": [  # 2 player games
        "⚔️ **FINAL DUEL VICTOR!**",
        "🥊 **ONE-ON-ONE CHAMPION!**",
        "🎯 **ULTIMATE SHOWDOWN WINNER!**",
        "💀 **LAST TRIBUTE STANDING!**"
    ]
}

# Death Events - Mixed Themes with Discord Markdown (Fixed titles)
DEATH_EVENTS = [
    "💀 | **{killer}** fed ~~**{player}**~~ to their pet dragon!",
    "💀 | ~~**{player}**~~ got electrocuted trying to hack the mainframe.",
    "💀 | **{killer}** slipped a blade between ~~**{player}**~~'s ribs in the crowded marketplace!",
    "💀 | ~~**{player}**~~ drank contaminated water from the radioactive river.",
    "💀 | **{killer}** went into a rage and cleaved ~~**{player}**~~ in half with a battle axe!",
    "💀 | ~~**{player}**~~ collapsed from exhaustion in the middle of the zombie horde.",
    "💀 | **{killer}** materialized behind ~~**{player}**~~ and slit their throat!",
    "💀 | ~~**{player}**~~ triggered a booby trap while looting the ancient tomb.",
    "💀 | **{killer}** devoured ~~**{player}**~~ alive in the post-apocalyptic wasteland!",
    "💀 | ~~**{player}**~~ touched the cursed artifact and was instantly incinerated.",
    "💀 | **{killer}** crucified ~~**{player}**~~ on the city gates for all to see!",
    "💀 | ~~**{player}**~~ was torn apart by robotic sentries in the forbidden zone.",
    "💀 | **{killer}** bludgeoned ~~**{player}**~~ to death with a crowbar!",
    "💀 | ~~**{player}**~~ got lost in the interdimensional portal maze and starved.",
    "💀 | **{killer}** slowly flayed ~~**{player}**~~ alive in their dungeon!",
    "💀 | ~~**{player}**~~ fell into a pit of space-time anomalies.",
    "💀 | **{killer}** keelhauled ~~**{player}**~~ beneath their ghostly ship!",
    "💀 | ~~**{player}**~~ walked into a field of plasma mines.",
    "💀 | **{killer}** sacrificed ~~**{player}**~~ to summon demons from the void!",
    "💀 | ~~**{player}**~~ was possessed by malevolent AI and self-destructed.",
    "💀 | **{killer}** impaled ~~**{player}**~~ with a trident in the arena!",
    "💀 | ~~**{player}**~~ got crushed by a falling meteor in the asteroid field.",
    "💀 | **{killer}** drained ~~**{player}**~~ completely dry in the moonlit cemetery!",
    "💀 | ~~**{player}**~~ ran straight into a force field barrier at full speed.",
    "💀 | **{killer}** cursed ~~**{player}**~~ to die of a thousand cuts!",
    "💀 | ~~**{player}**~~ was digested alive by a carnivorous plant in the bio-dome.",
    "💀 | **{killer}** buried ~~**{player}**~~ alive under tons of rubble!",
    "💀 | ~~**{player}**~~ fell off the edge of the floating sky city.",
    "💀 | **{killer}** burned ~~**{player}**~~ at the stake in righteous fury!",
    "💀 | ~~**{player}**~~ activated the self-destruct sequence by accident.",
    "💀 | **{killer}** performed seppuku on ~~**{player}**~~ with ceremonial precision!",
    "💀 | ~~**{player}**~~ was torn limb from limb by mutant bears in the irradiated forest.",
    "💀 | **{killer}** harvested ~~**{player}**~~'s soul with their spectral scythe!",
    "💀 | ~~**{player}**~~ drank the obviously poisoned chalice at the feast.",
    "💀 | **{killer}** smashed ~~**{player}**~~ against the concrete wall repeatedly!",
    "💀 | ~~**{player}**~~ was consumed by shadow creatures in the void between dimensions.",
    "💀 | **{killer}** tortured ~~**{player}**~~ to death with red-hot irons!",
    "💀 | ~~**{player}**~~ stepped on a pressure plate that triggered laser turrets.",
    "💀 | **{killer}** had ~~**{player}**~~ thrown into the lava forge!",
    "💀 | ~~**{player}**~~ was strangled by killer vines while napping in the jungle.",
    "💀 | **{killer}** carved ~~**{player}**~~ up like a piece of meat!",
    "💀 | ~~**{player}**~~ got absorbed by the experimental black hole device.",
    "💀 | **{killer}** sacrificed ~~**{player}**~~ to their dark god on the obsidian altar!",
    "💀 | ~~**{player}**~~ drove their hover-bike straight into the plasma storm.",
    "💀 | **{killer}** garroted ~~**{player}**~~ with razor wire!",
    "💀 | ~~**{player}**~~ tried to pet a cyber-enhanced sabertooth tiger.",
    "💀 | **{killer}** ran ~~**{player}**~~ down with their war chariot!",
    "💀 | ~~**{player}**~~ ate glowing mushrooms in the alien cavern system.",
    "💀 | **{killer}** locked ~~**{player}**~~ in the oubliette to rot forever!",
    "💀 | ~~**{player}**~~ got caught in the crossfire of a mech battle.",
    "💀 | **{killer}** gunned down ~~**{player}**~~ in broad daylight!",
    "💀 | ~~**{player}**~~ was betrayed by their own android companion.",
    "💀 | **{killer}** went berserk and tore ~~**{player}**~~ apart with their bare hands!",
    "💀 | ~~**{player}**~~ never woke up from the virtual reality nightmare.",
    "💀 | **{killer}** dissolved ~~**{player}**~~ in a vat of acid!",
    "💀 | ~~**{player}**~~ got lost in the temporal loop and aged to death instantly.",
    "💀 | **{killer}** decapitated ~~**{player}**~~ with a single swing!",
    "💀 | ~~**{player}**~~ challenged a quantum computer to chess and had their brain fried.",
    "💀 | **{killer}** vaporized ~~**{player}**~~ with a plasma rifle!",
    "💀 | ~~**{player}**~~ was driven insane by whispers from the cosmic void.",
    "💀 | **{killer}** whipped ~~**{player}**~~ to death in the fighting pits!",
    "💀 | ~~**{player}**~~ accidentally triggered a nuclear warhead while scavenging.",
    "💀 | **{killer}** collected ~~**{player}**~~'s skull for their trophy wall!",
    "💀 | ~~**{player}**~~ was crushed by their own hoarded treasure when the vault collapsed.",
    "💀 | **{killer}** possessed ~~**{player}**~~ and made them self-immolate!",
    "💀 | ~~**{player}**~~ died of exhaustion while mining asteroids in zero gravity.",
    "💀 | **{killer}** had ~~**{player}**~~ drawn and quartered in the town square!",
    "💀 | ~~**{player}**~~ was driven to madness by isolation in the sensory deprivation chamber.",
    "💀 | **{killer}** performed experimental surgery on ~~**{player}**~~ without anesthesia!",
    "💀 | ~~**{player}**~~ stood their ground against a horde of cyber-zombies and was overwhelmed.",
    "💀 | **{killer}** threw ~~**{player}**~~ to the dire wolves!",
    "💀 | ~~**{player}**~~ touched the time crystal and was erased from existence.",
    "💀 | **{killer}** scalped ~~**{player}**~~ with a rusty machete!",
    "💀 | ~~**{player}**~~ drank liquid mercury thinking it was water.",
    "💀 | **{killer}** beat ~~**{player}**~~ to death with a lead pipe for unpaid debts!",
    "💀 | ~~**{player}**~~ was flash-frozen in the cryogenic laboratory malfunction.",
    "💀 | **{killer}** impaled ~~**{player}**~~ on spikes as a warning to others!",
    "💀 | ~~**{player}**~~ was devoured by dream parasites in the psychic realm.",
    "💀 | **{killer}** systematically eliminated ~~**{player}**~~ with extreme prejudice!",
    "💀 | ~~**{player}**~~ tried to surf on molten lava flows.",
    "💀 | **{killer}** had ~~**{player}**~~ cement-shoed and thrown into the harbor!",
    "💀 | ~~**{player}**~~ was poisoned by radioactive food rations.",
    "💀 | **{killer}** cursed ~~**{player}**~~ to be eaten alive by spirit wolves!",
    "💀 | ~~**{player}**~~ volunteered for genetic experiments and mutated into oblivion.",
    "💀 | **{killer}** went into blood rage and pulverized ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ fell asleep on the conveyor belt and was processed by factory machinery.",
    "💀 | **{killer}** haunted ~~**{player}**~~ until they died of pure terror!",
    "💀 | ~~**{player}**~~ was betrayed by their AI companion and ejected into space.",
    "💀 | **{killer}** threw ~~**{player}**~~ into the fighting pit with hungry raptors!",
    "💀 | ~~**{player}**~~ got stuck in a temporal paradox and ceased to exist.",
    "💀 | **{killer}** slowly peeled the skin off ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ was disintegrated by the alien defense system.",
    "💀 | **{killer}** made ~~**{player}**~~ walk the plank into the void of space!",
    "💀 | ~~**{player}**~~ triggered an avalanche while skiing down the radioactive mountain.",
    "💀 | **{killer}** slowly tortured ~~**{player}**~~ to death for entertainment!",
    "💀 | ~~**{player}**~~ tried to reason with the genocidal AI overlord.",
    "💀 | **{killer}** crucified ~~**{player}**~~ upside down as an example!",
    "💀 | ~~**{player}**~~ was consumed from the inside by parasitic nanobots.",
    "💀 | **{killer}** tracked ~~**{player}**~~ through the nuclear wasteland and finished them with a harpoon!",
    "💀 | ~~**{player}**~~ was betrayed by their own clone and stabbed in the back.",
    "💀 | **{killer}** beheaded ~~**{player}**~~ with an energy sword!",
    "💀 | ~~**{player}**~~ wandered into the interdimensional rift and was torn apart.",
    "💀 | **{killer}** had ~~**{player}**~~ executed by firing squad!",
    "💀 | ~~**{player}**~~ pressed the big red button labeled 'DO NOT PRESS'.",
    "💀 | **{killer}** stalked ~~**{player}**~~ through the cyber jungle and eviscerated them!",
    "💀 | ~~**{player}**~~ was trapped forever in a virtual reality horror simulation.",
    "💀 | **{killer}** obliterated ~~**{player}**~~ with a plasma cannon blast!",
    "💀 | ~~**{player}**~~ tried to make friends with the killer robots.",
    "💀 | **{killer}** fed ~~**{player}**~~ to their mutant pet shark!",
    "💀 | ~~**{player}**~~ tripped and fell into the antimatter containment unit.",
    "💀 | **{killer}** slowly lowered ~~**{player}**~~ into a vat of molten steel!",
    "💀 | **{killer}** stretched ~~**{player}**~~ until they snapped like a rubber band!",
    "💀 | ~~**{player}**~~ was devoured by a massive Sea King while trying to steal its treasure.",
    "💀 | **{killer}** executed ~~**{player}**~~ with a devastating magma punch!",
    "💀 | ~~**{player}**~~ fell into the ocean and drowned because of their Devil Fruit weakness.",
    "💀 | **{killer}** sliced ~~**{player}**~~ clean in half with their legendary blade!",
    "💀 | ~~**{player}**~~ got lost in the Florian Triangle and was consumed by the mist.",
    "💀 | **{killer}** turned ~~**{player}**~~ to ash with their fire powers!",
    "💀 | ~~**{player}**~~ tried to swim across the Calm Belt and became Sea King bait.",
    "💀 | **{killer}** froze ~~**{player}**~~ solid and shattered them!",
    "💀 | ~~**{player}**~~ was overwhelmed by a horde of Pacifista during the war.",
    "💀 | **{killer}** crushed ~~**{player}**~~ with Conqueror's Haki alone!",
    "💀 | ~~**{player}**~~ got caught in Enies Lobby's judicial waterfall.",
    "💀 | **{killer}** mauled ~~**{player}**~~ in their full beast form!",
    "💀 | ~~**{player}**~~ wandered into Impel Down and was tortured to death by the guards.",
    "💀 | **{killer}** impaled ~~**{player}**~~ with their dragon claw technique!",
    "💀 | ~~**{player}**~~ ate a poisonous Devil Fruit thinking it was regular food.",
    "💀 | **{killer}** made ~~**{player}**~~ walk the plank into a whirlpool!",
    "💀 | ~~**{player}**~~ was vaporized by one of Vegapunk's experimental weapons.",
    "💀 | **{killer}** used Water Shot to pierce straight through ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ got trampled by a herd of Kung-Fu Dugongs.",
    "💀 | **{killer}** turned ~~**{player}**~~ into a toy and forgot they ever existed!",
    "💀 | ~~**{player}**~~ was trapped forever in a Mirror World dimension.",
    "💀 | **{killer}** obliterated ~~**{player}**~~ with their awakened Devil Fruit!",
    "💀 | ~~**{player}**~~ was assassinated by CP9 agents in their sleep.",
    "💀 | **{killer}** petrified ~~**{player}**~~ with their beauty and kicked them to pieces!",
    "💀 | ~~**{player}**~~ got caught in Whitebeard's earthquake and was buried under debris.",
    "💀 | **{killer}** stepped on ~~**{player}**~~ like they were an ant!",
    "💀 | ~~**{player}**~~ drank seawater in desperation and died of dehydration.",
    "💀 | **{killer}** blasted ~~**{player}**~~ to smithereens with their laser beam!",
    "💀 | ~~**{player}**~~ was crushed by their own treasure hoard in a collapsing cave.",
    "💀 | **{killer}** struck ~~**{player}**~~ down with divine lightning!",
    "💀 | ~~**{player}**~~ fell from a Sky Island and became a crater.",
    "💀 | **{killer}** electrocuted ~~**{player}**~~ with Electro during Sulong form!",
    "💀 | ~~**{player}**~~ was dissolved by the acidic stomach of a massive sea beast.",
    "💀 | **{killer}** used Rokushiki to literally punch through ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ challenged Kaido to single combat and was obliterated.",
    "💀 | **{killer}** swapped ~~**{player}**~~'s heart with a rock!",
    "💀 | ~~**{player}**~~ got caught in Big Mom's soul-stealing rampage.",
    "💀 | **{killer}** crushed ~~**{player}**~~ in their massive dinosaur jaws!",
    "💀 | ~~**{player}**~~ tried to steal from a Celestial Dragon and was executed on the spot.",
    "💀 | **{killer}** coated their fist and punched straight through ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ ate a SMILE fruit and laughed themselves to death.",
    "💀 | **{killer}** burned ~~**{player}**~~ to cinders with their fire fist!",
    "💀 | ~~**{player}**~~ was betrayed and sold to slave traders on Sabaody.",
    "💀 | **{killer}** puppeteered ~~**{player}**~~ into killing themselves!",
    "💀 | ~~**{player}**~~ was fed explosive food by a vengeful cook.",
    "💀 | **{killer}** split ~~**{player}**~~ in two with a single sword draw!",
    "💀 | ~~**{player}**~~ sailed into the New World unprepared and was instantly vaporized.",
    "💀 | **{killer}** struck ~~**{player}**~~ with a concentrated lightning bolt!",
    "💀 | ~~**{player}**~~ got sucked into a Knock Up Stream without proper preparation.",
    "💀 | **{killer}** stretched their arm across the island to punch ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ was cursed by Aztec gold and crumbled to dust.",
    "💀 | **{killer}** impaled ~~**{player}**~~ with razor-sharp bone spears!",
    "💀 | ~~**{player}**~~ was poisoned by a seemingly friendly barkeeper.",
    "💀 | **{killer}** drained all moisture from ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ got caught in crossfire between two Yonko crews.",
    "💀 | **{killer}** froze the entire ocean with ~~**{player}**~~ trapped inside!",
    "💀 | ~~**{player}**~~ was overtaken by a deadly Buster Call bombardment.",
    "💀 | **{killer}** struck ~~**{player}**~~ with 200 million volt divine judgment!",
    "💀 | ~~**{player}**~~ was caught in the middle of a Conqueror's Haki clash.",
    "💀 | **{killer}** snuck up on ~~**{player}**~~ and slit their throat!",
    "💀 | ~~**{player}**~~ tried to befriend a wild tiger on Rusukaina Island.",
    "💀 | **{killer}** encased ~~**{player}**~~ in hardened wax and let them suffocate!",
    "💀 | ~~**{player}**~~ opened Pandora's Box and released ancient curses.",
    "💀 | **{killer}** dive-bombed ~~**{player}**~~ with blazing talons!",
    "💀 | ~~**{player}**~~ was trapped in an eternal nightmare by a Sleep-Sleep fruit user.",
    "💀 | **{killer}** moved at light speed and bisected ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ tried to navigate the Grand Line without a Log Pose and sailed into a hurricane.",
    "💀 | **{killer}** stole ~~**{player}**~~'s shadow and they crumbled in daylight!",
    "💀 | ~~**{player}**~~ was overwhelmed by the sheer presence of a Yonko's Conqueror's Haki.",
    "💀 | **{killer}** shattered the very air and ~~**{player}**~~ along with it!",
    "💀 | ~~**{player}**~~ challenged Mihawk to a sword duel with a butter knife.",
    "💀 | **{killer}** trapped ~~**{player}**~~ in an inescapable barrier until they suffocated!",
    "💀 | ~~**{player}**~~ got their soul sucked out by Big Mom's homies.",
    "💀 | **{killer}** opened a door in ~~**{player}**~~'s chest and reached through!",
    "💀 | ~~**{player}**~~ got lost in the Florian Triangle and was never seen again.",
    "💀 | **{killer}** turned ~~**{player}**~~ into a puddle of lava!",
    "💀 | ~~**{player}**~~ ate poisonous pufferfish sashimi prepared by an amateur chef.",
    "💀 | **{killer}** obliterated ~~**{player}**~~ and their entire island!"
]

# Survival Events - Mixed Themes with Discord Markdown (Fixed titles)
SURVIVAL_EVENTS = [
    "🌿 | **{player}** found a hidden cache of supplies in an abandoned bunker!",
    "💊 | **{player}** discovered medical supplies and __*healed their wounds*__!",
    "🍖 | **{player}** successfully trapped a wild boar for a hearty meal!",
    "💧 | **{player}** located a clean water source in the desert oasis!",
    "🏠 | **{player}** discovered a safe shelter in the ruined castle!",
    "🔥 | **{player}** started a fire to keep warm during the cold night!",
    "🍄 | **{player}** found edible mushrooms (and they weren't poisonous)!",
    "🎒 | **{player}** salvaged useful gear from a fallen tribute's backpack!",
    "🗡️ | **{player}** forged a makeshift weapon from scrap metal!",
    "🌙 | **{player}** successfully hid from other tributes in the shadows!",
    "⚡ | **{player}** avoided a deadly trap by pure instinct!",
    "🦋 | **{player}** made friends with some harmless butterflies!",
    "🌳 | **{player}** climbed a massive tree to scout the surrounding area!",
    "🏃 | **{player}** outran a pack of radioactive wolves!",
    "🍯 | **{player}** found honey and __*gained energy*__ for the trials ahead!",
    "🛡️ | **{player}** crafted armor from salvaged vehicle parts!",
    "🎯 | **{player}** practiced their aim with makeshift targets!",
    "🌺 | **{player}** discovered healing herbs in the jungle!",
    "💤 | **{player}** got a good night's sleep in their hidden cave!",
    "🦎 | **{player}** caught and cooked a lizard over their campfire!",
    "🔧 | **{player}** __*repaired their equipment*__ using spare parts!",
    "🎵 | **{player}** played a tune that __*boosted their morale*__!",
    "💎 | **{player}** discovered valuable gems in the crystal caves!",
    "🗺️ | **{player}** found an ancient map showing secret passages!",
    "🧪 | **{player}** brewed a __*stamina potion*__ from local plants!"
]

# NEW: Crate Events - Equipment and Gear Discovery (Fixed titles)
CRATE_EVENTS = [
    "📦 | **{player}** discovered a __*weapon cache*__ hidden in the ruins of District 8!",
    "📦 | **{player}** found __*advanced combat gear*__ in an abandoned military crate!",
    "📦 | **{player}** uncovered __*medical supplies*__ in a Capitol emergency drop!",
    "📦 | **{player}** located a __*food cache*__ buried near the Cornucopia!",
    "📦 | **{player}** cracked open a __*mystery crate*__ containing high-tech equipment!",
    "📦 | **{player}** stumbled upon a __*supply drop*__ meant for another tribute!",
    "📦 | **{player}** found a __*survival kit*__ stashed in District 12's mines!",
    "📦 | **{player}** discovered __*explosive devices*__ in a hidden weapons depot!",
    "📦 | **{player}** spotted a __*camouflaged crate*__ containing stealth gear!",
    "📦 | **{player}** broke into a __*locked container*__ filled with rare items!",
    "📦 | **{player}** found a __*night vision kit*__ in District 3's tech ruins!",
    "📦 | **{player}** excavated a __*buried arsenal*__ from the old rebellion!",
    "📦 | **{player}** located a __*first aid crate*__ hidden by previous tributes!",
    "📦 | **{player}** discovered a __*trap-making kit*__ in the abandoned warehouses!",
    "📦 | **{player}** raided a __*sponsor cache*__ dropped for eliminated tributes!",
    "📦 | **{player}** found __*communication equipment*__ in District 1's luxury bunker!",
    "📦 | **{player}** uncovered a __*defensive gear set*__ in the training center ruins!",
    "📦 | **{player}** broke open a __*power source crate*__ from District 5!",
    "📦 | **{player}** located a __*precision tools kit*__ in the Victor's Village!",
    "📦 | **{player}** found a __*multi-tool cache*__ in the underground tunnels!",
    "📦 | **{player}** discovered a __*smoke grenade stash*__ near the force field!",
    "📦 | **{player}** spotted a __*climbing gear crate*__ in the mountain district!",
    "📦 | **{player}** raided a __*sponsor gift*__ intended for the final tributes!",
    "📦 | **{player}** found a __*hunting equipment set*__ in District 11's farmlands!",
    "📦 | **{player}** uncovered a __*energy drink cache*__ hidden by the Gamemakers!"
]

# Alliance Events - Mixed Themes with Discord Markdown (Fixed titles)
ALLIANCE_EVENTS = [
    "🤝 | **{player1}** and **{player2}** __*formed an alliance*__ by the campfire!",
    "💔 | **{player1}** __*betrayed their ally*__ ~~**{player2}**~~ for their supplies!",
    "🛡️ | **{player1}** protected **{player2}** from a sneak attack!",
    "🔥 | **{player1}** and **{player2}** __*shared a campfire*__ during the cold night!",
    "🍖 | **{player1}** shared their last meal with **{player2}**!",
    "⚔️ | **{player1}** and **{player2}** __*teamed up*__ to raid the supply depot!",
    "🗣️ | **{player1}** and **{player2}** __*planned their next move*__ together!",
    "💰 | **{player1}** and **{player2}** __*agreed to split*__ any treasure they find!",
    "🏥 | **{player1}** tended to **{player2}**'s wounds with __*makeshift bandages*__!",
    "🎯 | **{player1}** taught **{player2}** how to __*use their weapon*__ properly!"
]

# Sponsor Events - Mixed Themes with Discord Markdown (Fixed titles)
SPONSOR_EVENTS = [
    "🎁 | **SPONSOR GIFT!** **{player}** __*received a care package*__ dropped from the sky!",
    "💊 | **SPONSOR GIFT!** **{player}** was given __*life-saving medicine*__ by mysterious benefactor!",
    "🗡️ | **SPONSOR GIFT!** **{player}** __*received a weapon upgrade*__ from their sponsor!",
    "🍖 | **SPONSOR GIFT!** **{player}** was sent a __*feast fit for a king*__!",
    "🛡️ | **SPONSOR GIFT!** **{player}** __*received protective gear*__ just in time!",
    "🔋 | **SPONSOR GIFT!** **{player}** got __*high-tech equipment*__ from their sponsor!",
    "🧪 | **SPONSOR GIFT!** **{player}** received __*experimental enhancement serum*__!",
    "🎒 | **SPONSOR GIFT!** **{player}** was given a __*fully stocked survival kit*__!",
    "💰 | **SPONSOR GIFT!** **{player}** received __*valuable currency*__ from their patron!",
    "🗺️ | **SPONSOR GIFT!** **{player}** was sent __*detailed maps*__ of the arena!"
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

# Midgame Event Categories
MIDGAME_ATMOSPHERIC_EVENTS = [
    "🌙 | An eerie silence falls over the arena as night approaches...",
    "🦅 | Mockingjays begin singing a haunting melody throughout the arena...",
    "🔊 | The fallen tributes' faces appear in the sky, a grim reminder...",
    "⭐ | The arena's artificial stars flicker ominously overhead...",
    "🌿 | Strange sounds echo from the depths of the arena...",
    "💨 | A gentle breeze carries the scent of distant flowers... and death...",
    "🌫️ | Mist rolls through the arena, creating ghostly shapes...",
    "🎵 | The wind carries whispers of the fallen tributes..."
]

# Cannon Malfunction Events
CANNON_DEATH_EVENTS = [
    "📯💥 | A cannon misfires and the blast catches ~~**{player}**~~ in the explosion!",
    "📯⚡ | ~~**{player}**~~ was struck by debris from a malfunctioning cannon!",
    "📯🔥 | ~~**{player}**~~ couldn't escape the cannon's unexpected blast radius!",
    "📯💀 | ~~**{player}**~~ was caught in the shockwave of an exploding cannon!"
]

CANNON_SCARE_EVENTS = [
    "📯💨 | A cannon fires in the distance, the blast barely missing the tributes!",
    "📯⚠️ | A cannon misfires, sending debris flying but harming no one!",
    "📯😰 | The sound of a cannon echoes through the arena, making everyone jump!",
    "📯🌪️ | A cannon blast creates a shockwave, but all tributes take cover in time!"
]

# Toxic Fog Events
TOXIC_FOG_SINGLE_DEATH = [
    "☠️💨 | Toxic fog engulfs the arena! ~~**{player}**~~ couldn't escape in time!",
    "☠️🌫️ | ~~**{player}**~~ was overwhelmed by the deadly green fog!",
    "☠️💚 | ~~**{player}**~~ succumbed to the poisonous mist!",
    "☠️🏃 | ~~**{player}**~~ couldn't outrun the spreading toxic cloud!"
]

TOXIC_FOG_MULTI_DEATH = "☠️💨 | Deadly fog sweeps through the arena, claiming {players}!"
TOXIC_FOG_SURVIVAL = "💨😅 | Toxic fog rolls through the arena, but all tributes find shelter in time!"

# Tracker Jacker Events
TRACKER_JACKER_DEATHS = [
    "🐝💀 | ~~**{player}**~~ was swarmed by tracker jackers and stung to death!",
    "🐝😵 | ~~**{player}**~~ succumbed to tracker jacker venom!",
    "🐝🌪️ | ~~**{player}**~~ couldn't outrun the deadly tracker jacker nest!",
    "🐝⚡ | ~~**{player}**~~ was overwhelmed by the aggressive swarm!"
]

TRACKER_JACKER_HALLUCINATION = "🌀 | **{player}** hallucinates from tracker jacker venom!"
TRACKER_JACKER_AVOIDANCE = "🐝⚠️ | Tracker jackers swarm overhead but seem to ignore the final tributes..."

# Arena Trap Types and Events
ARENA_TRAP_TYPES = [
    ("landmine", "💥", "stepped on a hidden landmine"),
    ("pitfall", "🕳️", "fell into a concealed pit trap"),
    ("spikes", "⬆️", "was impaled by rising spike trap"),
    ("net", "🕸️", "was caught in a net trap and couldn't escape"),
    ("gas", "☠️", "triggered a poison gas trap"),
    ("blade", "⚔️", "was sliced by hidden blade traps"),
    ("electrical", "⚡", "was electrocuted by a hidden shock trap")
]

ARENA_TRAP_DEATH = "{emoji}💀 | ~~**{player}**~~ {description}!"
ARENA_TRAP_ESCAPE = "{emoji}😅 | **{player}** narrowly avoids a {trap_name} trap!"

# Muttation Types and Events
MUTTATION_TYPES = [
    ("wolf mutts", "🐺", "torn apart by"),
    ("tracker jackers", "🐝", "stung to death by"),
    ("lizard mutts", "🦎", "devoured by"),
    ("bird mutts", "🦅", "carried off by"),
    ("spider mutts", "🕷️", "poisoned by"),
    ("snake mutts", "🐍", "strangled by"),
    ("bear mutts", "🐻", "mauled by")
]

MUTTATION_DEATH = "{emoji}💀 | ~~**{player}**~~ was {death_verb} {mutt_name}!"
MUTTATION_ESCAPE = "{emoji}⚠️ | {mutt_name} prowl the arena, but the tributes manage to avoid them!"

# Environmental Hazard Types
ENVIRONMENTAL_HAZARDS = [
    ("earthquake", "🌍", "crushed by falling rocks during"),
    ("flash flood", "🌊", "swept away by"),
    ("lightning storm", "⚡", "struck by lightning during"),
    ("avalanche", "❄️", "buried alive in"),
    ("forest fire", "🔥", "consumed by"),
    ("tornado", "🌪️", "swept away by"),
    ("volcanic eruption", "🌋", "incinerated by")
]

ENVIRONMENTAL_SINGLE_DEATH = "{emoji}💀 | ~~**{player}**~~ was {death_description} the {hazard_name}!"
ENVIRONMENTAL_MULTI_DEATH = "{emoji}💀 | {players} were caught in the deadly {hazard_name}!"
ENVIRONMENTAL_SURVIVAL = "{emoji}⚠️ | A {hazard_name} rocks the arena, but all tributes find safety!"
ENVIRONMENTAL_PARTIAL_SURVIVAL = "{emoji}😅 | **{survivors}** managed to escape!"

# Gamemaker Test Events
GAMEMAKER_COURAGE_DEATH = "🎭💀 | The Gamemakers test **{player}**'s courage - ~~**they failed fatally**~~!"
GAMEMAKER_COURAGE_SURVIVAL = "🎭⚡ | **{player}** faces the Gamemakers' courage test and survives!"
GAMEMAKER_TEST_ANNOUNCEMENT = "🎭⚠️ | The Gamemakers announce a test is coming for the remaining tributes..."
GAMEMAKER_LOYALTY_TEST = "🎭⚡ | The Gamemakers test the tributes' loyalties with a mysterious announcement..."

# Event Type Categories for Midgame
MIDGAME_DEADLY_EVENT_TYPES = [
    "cannon_malfunction",
    "toxic_fog", 
    "tracker_jackers",
    "arena_trap",
    "muttation_attack",
    "environmental_hazard",
    "gamemaker_test"
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
