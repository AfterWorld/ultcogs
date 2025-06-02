# constants.py - Updated with One Piece theming and bug fixes
"""Constants and configuration for the Hunger Games cog"""

# Game Configuration
DEFAULT_GUILD_CONFIG = {
    "games": {},
    "base_reward": 500,
    "sponsor_chance": 15,
    "event_interval": 30,
    "recruitment_time": 60,
    "enable_gifs": False,
    "enable_custom_images": True,
    "poll_threshold": None,  # Minimum players needed to start via poll
    "poll_ping_role": None,  # Role to ping when polls start
    "blacklisted_roles": [],  # Roles that can't participate
}

DEFAULT_MEMBER_CONFIG = {
    "wins": 0,
    "deaths": 0,
    "kills": 0,
    "revives": 0,
    "games_played": 0,  # Added missing field
    "temp_banned_until": None,  # Temporary ban timestamp
}

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

# Poll specific constants
POLL_EMOJIS = {
    "join": "✅",
    "leave": "❌",
    "start": "🎮"
}

# One Piece Style Death Events - Player vs Player
PLAYER_DEATH_EVENTS = [
    "💀 | **{killer}** fed ~~**{player}**~~ to their pet Sea King!",
    "💀 | **{killer}** slipped a blade between ~~**{player}**~~'s ribs in the bustling port town!",
    "💀 | **{killer}** went into a rage and cleaved ~~**{player}**~~ in half with their legendary cutlass!",
    "💀 | **{killer}** materialized behind ~~**{player}**~~ using Soru and slit their throat!",
    "💀 | **{killer}** devoured ~~**{player}**~~ alive using their Carnivorous Zoan powers!",
    "💀 | **{killer}** crucified ~~**{player}**~~ on the town's execution platform for all to see!",
    "💀 | **{killer}** bludgeoned ~~**{player}**~~ to death with their kanabo!",
    "💀 | **{killer}** slowly flayed ~~**{player}**~~ alive in their torture chamber on Thriller Bark!",
    "💀 | **{killer}** keelhauled ~~**{player}**~~ beneath their ghostly pirate ship!",
    "💀 | **{killer}** sacrificed ~~**{player}**~~ to summon an ancient Sea King!",
    "💀 | **{killer}** impaled ~~**{player}**~~ with their trident in the Corrida Colosseum!",
    "💀 | **{killer}** drained ~~**{player}**~~ completely dry using their Vampire Bat Zoan form!",
    "💀 | **{killer}** cursed ~~**{player}**~~ using their Voodoo-Voodoo Fruit powers!",
    "💀 | **{killer}** buried ~~**{player}**~~ alive under tons of rubble using their Earth-Earth Fruit!",
    "💀 | **{killer}** burned ~~**{player}**~~ at the stake using their Flame-Flame Fruit!",
    "💀 | **{killer}** performed ritual seppuku on ~~**{player}**~~ with ceremonial precision!",
    "💀 | **{killer}** harvested ~~**{player}**~~'s soul using their Soul-Soul Fruit powers!",
    "💀 | **{killer}** smashed ~~**{player}**~~ against the ship's mast repeatedly!",
    "💀 | **{killer}** tortured ~~**{player}**~~ to death with red-hot branding irons!",
    "💀 | **{killer}** had ~~**{player}**~~ thrown into the magma chamber of Punk Hazard!",
    "💀 | **{killer}** carved ~~**{player}**~~ up like a piece of meat using their Dice-Dice Fruit!",
    "💀 | **{killer}** sacrificed ~~**{player}**~~ to their dark god on an obsidian altar!",
    "💀 | **{killer}** garroted ~~**{player}**~~ with razor wire!",
    "💀 | **{killer}** ran ~~**{player}**~~ down with their ship at full sail!",
    "💀 | **{killer}** locked ~~**{player}**~~ in Impel Down's Level 6 to rot forever!",
    "💀 | **{killer}** gunned down ~~**{player}**~~ with their flintlock in broad daylight!",
    "💀 | **{killer}** went berserk and tore ~~**{player}**~~ apart with their bare hands!",
    "💀 | **{killer}** dissolved ~~**{player}**~~ in a vat of acid using their Acid-Acid Fruit!",
    "💀 | **{killer}** decapitated ~~**{player}**~~ with a single sword draw!",
    "💀 | **{killer}** vaporized ~~**{player}**~~ with a concentrated laser beam!",
    "💀 | **{killer}** whipped ~~**{player}**~~ to death in the fighting pits of Dressrosa!",
    "💀 | **{killer}** collected ~~**{player}**~~'s skull for their trophy wall!",
    "💀 | **{killer}** possessed ~~**{player}**~~ using their Spirit-Spirit Fruit and made them jump overboard!",
    "💀 | **{killer}** had ~~**{player}**~~ drawn and quartered in the town square!",
    "💀 | **{killer}** performed experimental surgery on ~~**{player}**~~ without anesthesia!",
    "💀 | **{killer}** threw ~~**{player}**~~ to the wild beasts of Rusukaina!",
    "💀 | **{killer}** scalped ~~**{player}**~~ with a rusty cutlass!",
    "💀 | **{killer}** beat ~~**{player}**~~ to death with a lead pipe for unpaid debts!",
    "💀 | **{killer}** impaled ~~**{player}**~~ on spikes as a warning to other pirates!",
    "💀 | **{killer}** systematically eliminated ~~**{player}**~~ with extreme prejudice!",
    "💀 | **{killer}** had ~~**{player}**~~ cement-shoed and thrown into the ocean!",
    "💀 | **{killer}** cursed ~~**{player}**~~ to be eaten alive by spirit wolves!",
    "💀 | **{killer}** went into a blood rage and pulverized ~~**{player}**~~!",
    "💀 | **{killer}** haunted ~~**{player}**~~ using their Ghost-Ghost Fruit until they died of terror!",
    "💀 | **{killer}** threw ~~**{player}**~~ into the fighting pit with hungry beasts!",
    "💀 | **{killer}** slowly peeled the skin off ~~**{player}**~~ using their Peel-Peel Fruit!",
    "💀 | **{killer}** made ~~**{player}**~~ walk the plank into shark-infested waters!",
    "💀 | **{killer}** slowly tortured ~~**{player}**~~ to death for entertainment!",
    "💀 | **{killer}** crucified ~~**{player}**~~ upside down as an example to other pirates!",
    "💀 | **{killer}** tracked ~~**{player}**~~ through the Grand Line and finished them with a harpoon!",
    "💀 | **{killer}** beheaded ~~**{player}**~~ with their legendary blade!",
    "💀 | **{killer}** had ~~**{player}**~~ executed by Marine firing squad!",
    "💀 | **{killer}** stalked ~~**{player}**~~ through the jungle and eviscerated them!",
    "💀 | **{killer}** obliterated ~~**{player}**~~ with their awakened Devil Fruit blast!",
    "💀 | **{killer}** fed ~~**{player}**~~ to their mutant Sea King pet!",
    "💀 | **{killer}** slowly lowered ~~**{player}**~~ into a vat of molten steel!"
]

# Environmental Death Events - No killer needed
ENVIRONMENTAL_DEATH_EVENTS = [
    "💀 | ~~**{player}**~~ got electrocuted trying to steal a Devil Fruit from the World Government vault.",
    "💀 | ~~**{player}**~~ drank seawater while having Devil Fruit powers and drowned helplessly.",
    "💀 | ~~**{player}**~~ collapsed from exhaustion in the middle of a Marine raid.",
    "💀 | ~~**{player}**~~ triggered a trap while exploring ancient Shandian ruins.",
    "💀 | ~~**{player}**~~ touched a cursed treasure and was instantly turned to gold.",
    "💀 | ~~**{player}**~~ was torn apart by Pacifista during a Buster Call.",
    "💀 | ~~**{player}**~~ got lost in the Calm Belt and became Sea King bait.",
    "💀 | ~~**{player}**~~ fell into the ocean depths and was crushed by water pressure.",
    "💀 | ~~**{player}**~~ walked into Vegapunk's experimental laser grid.",
    "💀 | ~~**{player}**~~ was possessed by a vengeful spirit on Thriller Bark and self-destructed.",
    "💀 | ~~**{player}**~~ got crushed by falling debris during Whitebeard's earthquake.",
    "💀 | ~~**{player}**~~ ran straight into the Red Line at full speed.",
    "💀 | ~~**{player}**~~ was digested alive by a carnivorous plant on the Boin Archipelago.",
    "💀 | ~~**{player}**~~ fell off the edge of a Sky Island.",
    "💀 | ~~**{player}**~~ activated a self-destruct Dial by accident.",
    "💀 | ~~**{player}**~~ was torn limb from limb by Kung-Fu Dugongs in the desert.",
    "💀 | ~~**{player}**~~ drank obviously poisoned sake at the pirate feast.",
    "💀 | ~~**{player}**~~ was consumed by shadow creatures in the Florian Triangle.",
    "💀 | ~~**{player}**~~ stepped on a pressure plate that triggered ancient Poneglyph defenses.",
    "💀 | ~~**{player}**~~ was strangled by killer vines while napping in the jungle of Little Garden.",
    "💀 | ~~**{player}**~~ got absorbed by Blackbeard's darkness powers.",
    "💀 | ~~**{player}**~~ sailed their ship straight into a massive whirlpool.",
    "💀 | ~~**{player}**~~ tried to pet a cyber-enhanced Tiger from Vegapunk's lab.",
    "💀 | ~~**{player}**~~ ate poisonous mushrooms on the Boin Archipelago.",
    "💀 | ~~**{player}**~~ got caught in the crossfire of a Yonko battle.",
    "💀 | ~~**{player}**~~ was betrayed by their own crew member.",
    "💀 | ~~**{player}**~~ never woke up from Big Mom's dream-induced coma.",
    "💀 | ~~**{player}**~~ got lost in a temporal loop created by a Devil Fruit and aged to death instantly.",
    "💀 | ~~**{player}**~~ challenged a Cipher Pol agent to combat and had their mind broken.",
    "💀 | ~~**{player}**~~ was driven insane by whispers from the Void Century.",
    "💀 | ~~**{player}**~~ accidentally triggered explosive powder while raiding a Marine base.",
    "💀 | ~~**{player}**~~ was crushed by their own treasure hoard when their ship sank.",
    "💀 | ~~**{player}**~~ died of exhaustion while mining Sea Prism Stone.",
    "💀 | ~~**{player}**~~ was driven to madness by isolation on a deserted island.",
    "💀 | ~~**{player}**~~ stood their ground against a horde of Marines and was overwhelmed.",
    "💀 | ~~**{player}**~~ touched an ancient weapon and was erased from existence.",
    "💀 | ~~**{player}**~~ drank liquid mercury thinking it was rum.",
    "💀 | ~~**{player}**~~ was flash-frozen by Aokiji's ice powers.",
    "💀 | ~~**{player}**~~ was devoured by dream parasites in the psychic realm of Totland.",
    "💀 | ~~**{player}**~~ tried to surf on Akainu's magma flows.",
    "💀 | ~~**{player}**~~ was poisoned by contaminated food from a SMILE factory.",
    "💀 | ~~**{player}**~~ volunteered for Vegapunk's experiments and mutated into oblivion.",
    "💀 | ~~**{player}**~~ fell asleep on a Sea Train track and was run over.",
    "💀 | ~~**{player}**~~ was betrayed by their navigator and sailed into a hurricane.",
    "💀 | ~~**{player}**~~ got stuck in a Devil Fruit paradox and ceased to exist.",
    "💀 | ~~**{player}**~~ was disintegrated by ancient Poneglyph defense systems.",
    "💀 | ~~**{player}**~~ triggered an avalanche while climbing the Red Line.",
    "💀 | ~~**{player}**~~ tried to reason with the World Government and was executed.",
    "💀 | ~~**{player}**~~ was consumed from the inside by parasitic Sea King larvae.",
    "💀 | ~~**{player}**~~ was betrayed by their own twin brother and stabbed in the back.",
    "💀 | ~~**{player}**~~ wandered into a Devil's Triangle and was torn apart by supernatural forces.",
    "💀 | ~~**{player}**~~ pressed the self-destruct button on a Marine warship.",
    "💀 | ~~**{player}**~~ was trapped forever in a Mirror World dimension.",
    "💀 | ~~**{player}**~~ tried to make friends with the World Nobles.",
    "💀 | ~~**{player}**~~ tripped and fell into the ocean with Devil Fruit powers.",
    "💀 | ~~**{player}**~~ was devoured by a massive Sea King while trying to steal its treasure.",
    "💀 | ~~**{player}**~~ fell into the ocean and drowned because of their Devil Fruit weakness.",
    "💀 | ~~**{player}**~~ got lost in the Florian Triangle and was consumed by the mist.",
    "💀 | ~~**{player}**~~ tried to swim across the Calm Belt and became Sea King bait.",
    "💀 | ~~**{player}**~~ was overwhelmed by a horde of Pacifista during the war.",
    "💀 | ~~**{player}**~~ got caught in Enies Lobby's judicial waterfall.",
    "💀 | ~~**{player}**~~ wandered into Impel Down and was tortured to death by the guards.",
    "💀 | ~~**{player}**~~ ate a poisonous Devil Fruit thinking it was regular food.",
    "💀 | ~~**{player}**~~ was vaporized by one of Vegapunk's experimental weapons.",
    "💀 | ~~**{player}**~~ got trampled by a herd of Kung-Fu Dugongs.",
    "💀 | ~~**{player}**~~ was trapped forever in a Mirror World dimension.",
    "💀 | ~~**{player}**~~ was assassinated by CP9 agents in their sleep.",
    "💀 | ~~**{player}**~~ got caught in Whitebeard's earthquake and was buried under debris.",
    "💀 | ~~**{player}**~~ drank seawater in desperation and died of dehydration.",
    "💀 | ~~**{player}**~~ was crushed by their own treasure hoard in a collapsing cave.",
    "💀 | ~~**{player}**~~ fell from a Sky Island and became a crater.",
    "💀 | ~~**{player}**~~ was dissolved by the acidic stomach of a massive sea beast.",
    "💀 | ~~**{player}**~~ challenged Kaido to single combat and was obliterated.",
    "💀 | ~~**{player}**~~ got caught in Big Mom's soul-stealing rampage.",
    "💀 | ~~**{player}**~~ tried to steal from a Celestial Dragon and was executed on the spot.",
    "💀 | ~~**{player}**~~ ate a SMILE fruit and laughed themselves to death.",
    "💀 | ~~**{player}**~~ was betrayed and sold to slave traders on Sabaody.",
    "💀 | ~~**{player}**~~ was fed explosive food by a vengeful cook.",
    "💀 | ~~**{player}**~~ sailed into the New World unprepared and was instantly vaporized.",
    "💀 | ~~**{player}**~~ got sucked into a Knock Up Stream without proper preparation.",
    "💀 | ~~**{player}**~~ was cursed by Aztec gold and crumbled to dust.",
    "💀 | ~~**{player}**~~ was poisoned by a seemingly friendly barkeeper.",
    "💀 | ~~**{player}**~~ got caught in crossfire between two Yonko crews.",
    "💀 | ~~**{player}**~~ was overtaken by a deadly Buster Call bombardment.",
    "💀 | ~~**{player}**~~ was caught in the middle of a Conqueror's Haki clash.",
    "💀 | ~~**{player}**~~ tried to befriend a wild tiger on Rusukaina Island.",
    "💀 | ~~**{player}**~~ opened an ancient weapon's vault and released destructive forces.",
    "💀 | ~~**{player}**~~ was trapped in an eternal nightmare by a Sleep-Sleep fruit user.",
    "💀 | ~~**{player}**~~ tried to navigate the Grand Line without a Log Pose and sailed into a hurricane.",
    "💀 | ~~**{player}**~~ was overwhelmed by the sheer presence of a Yonko's Conqueror's Haki.",
    "💀 | ~~**{player}**~~ challenged Mihawk to a sword duel with a butter knife.",
    "💀 | ~~**{player}**~~ got their soul sucked out by Big Mom's homies.",
    "💀 | ~~**{player}**~~ got lost in the Florian Triangle and was never seen again.",
    "💀 | ~~**{player}**~~ ate poisonous pufferfish sashimi prepared by an amateur chef."
]

# Combine all death events for backwards compatibility
DEATH_EVENTS = PLAYER_DEATH_EVENTS + ENVIRONMENTAL_DEATH_EVENTS

# One Piece Style Survival Events
SURVIVAL_EVENTS = [
    "🏴‍☠️ | **{player}** found a hidden treasure cache buried on a deserted island!",
    "🍖 | **{player}** discovered meat and __*healed their wounds*__ after a hearty meal!",
    "🐟 | **{player}** successfully caught a massive fish for a feast!",
    "💧 | **{player}** located a freshwater spring on the tropical island!",
    "🏠 | **{player}** discovered a safe cave shelter in the cliffs!",
    "🔥 | **{player}** started a campfire to cook their catch and stay warm!",
    "🍌 | **{player}** found edible tropical fruits hanging from palm trees!",
    "🎒 | **{player}** salvaged useful supplies from a washed-up shipwreck!",
    "⚔️ | **{player}** forged a makeshift weapon from ship debris!",
    "🌙 | **{player}** successfully hid from Marine patrols in the jungle!",
    "⚡ | **{player}** avoided a deadly Sea King by pure instinct!",
    "🦜 | **{player}** made friends with a helpful News Coo!",
    "🌴 | **{player}** climbed a massive palm tree to scout for other islands!",
    "🏃 | **{player}** outran a pack of wild boars on Little Garden!",
    "🍯 | **{player}** found wild honey and __*gained energy*__ for the journey ahead!",
    "🛡️ | **{player}** crafted armor from Sea King scales!",
    "🎯 | **{player}** practiced their aim by throwing coconuts at trees!",
    "🌺 | **{player}** discovered healing herbs native to the Grand Line!",
    "💤 | **{player}** got a good night's sleep in their hammock between palm trees!",
    "🦎 | **{player}** caught and cooked a lizard over their campfire!",
    "🔧 | **{player}** __*repaired their ship*__ using driftwood and rope!",
    "🎵 | **{player}** played a sea shanty that __*boosted their morale*__!",
    "💎 | **{player}** discovered valuable gems washed ashore from sunken ships!",
    "🗺️ | **{player}** found an old treasure map buried in the sand!",
    "🧪 | **{player}** brewed a __*stamina potion*__ from tropical plants!"
]

# One Piece Style Crate Events - Treasure Chests and Shipwrecks
CRATE_EVENTS = [
    "🏴‍☠️ | **{player}** discovered a __*buried treasure chest*__ on the beach!",
    "🏴‍☠️ | **{player}** found __*legendary pirate weapons*__ in an ancient shipwreck!",
    "🏴‍☠️ | **{player}** uncovered __*medical supplies*__ in a Marine supply crate!",
    "🏴‍☠️ | **{player}** located a __*food cache*__ hidden by previous castaways!",
    "🏴‍☠️ | **{player}** cracked open a __*mystery chest*__ containing Devil Fruit!",
    "🏴‍☠️ | **{player}** stumbled upon a __*treasure hoard*__ meant for another pirate crew!",
    "🏴‍☠️ | **{player}** found a __*survival kit*__ stashed in a cave by shipwrecked sailors!",
    "🏴‍☠️ | **{player}** discovered __*explosive barrels*__ in a hidden weapons cache!",
    "🏴‍☠️ | **{player}** spotted a __*camouflaged chest*__ containing navigation tools!",
    "🏴‍☠️ | **{player}** broke into a __*locked treasure vault*__ filled with rare artifacts!",
    "🏴‍☠️ | **{player}** found a __*telescope and compass set*__ in a captain's quarters!",
    "🏴‍☠️ | **{player}** excavated a __*buried armory*__ from the age of pirates!",
    "🏴‍☠️ | **{player}** located a __*first aid chest*__ hidden by a ship's doctor!",
    "🏴‍☠️ | **{player}** discovered a __*trap-making kit*__ in abandoned ruins!",
    "🏴‍☠️ | **{player}** raided a __*merchant's treasure*__ washed ashore from a storm!",
    "🏴‍☠️ | **{player}** found __*communication equipment*__ in a Marine outpost!",
    "🏴‍☠️ | **{player}** uncovered a __*defensive gear set*__ in sunken Navy ship!",
    "🏴‍☠️ | **{player}** broke open a __*Dial collection*__ from Skypiea!",
    "🏴‍☠️ | **{player}** located a __*shipwright's tool chest*__ on the shoreline!",
    "🏴‍☠️ | **{player}** found a __*multi-tool cache*__ in underwater caverns!",
    "🏴‍☠️ | **{player}** discovered a __*smoke bomb stash*__ near ancient ruins!",
    "🏴‍☠️ | **{player}** spotted a __*climbing gear chest*__ in mountain caves!",
    "🏴‍☠️ | **{player}** raided a __*noble's treasure*__ intended for World Nobles!",
    "🏴‍☠️ | **{player}** found a __*fishing equipment set*__ in a coastal village!",
    "🏴‍☠️ | **{player}** uncovered a __*rum and rations cache*__ hidden by pirates!"
]

# One Piece Style Alliance Events - Crew Formation and Pirate Alliances
ALLIANCE_EVENTS = [
    "🤝 | **{player1}** and **{player2}** __*formed a pirate alliance*__ over shared sake!",
    "💔 | **{player1}** __*betrayed their crewmate*__ ~~**{player2}**~~ for their treasure!",
    "🛡️ | **{player1}** protected **{player2}** from a Marine sneak attack!",
    "🔥 | **{player1}** and **{player2}** __*shared a campfire*__ on the beach!",
    "🍖 | **{player1}** shared their last meal with starving **{player2}**!",
    "⚔️ | **{player1}** and **{player2}** __*teamed up*__ to raid a Marine base!",
    "🗣️ | **{player1}** and **{player2}** __*planned their next voyage*__ together!",
    "💰 | **{player1}** and **{player2}** __*agreed to split*__ any treasure they find!",
    "🏥 | **{player1}** tended to **{player2}**'s wounds with __*makeshift bandages*__!",
    "🎯 | **{player1}** taught **{player2}** how to __*use their cutlass*__ properly!"
]

# One Piece Style Sponsor Events - Benefactor Pirates and Mysterious Aid
SPONSOR_EVENTS = [
    "🎁 | **MYSTERIOUS BENEFACTOR!** **{player}** __*received a care package*__ from an unknown pirate!",
    "💊 | **SHIP DOCTOR'S GIFT!** **{player}** was given __*life-saving medicine*__ by a kind doctor!",
    "⚔️ | **WEAPON MASTER'S GIFT!** **{player}** __*received a legendary blade*__ from a master swordsmith!",
    "🍖 | **COOK'S GIFT!** **{player}** was sent a __*feast fit for a pirate king*__!",
    "🛡️ | **ARMOR SMITH'S GIFT!** **{player}** __*received protective gear*__ just in time!",
    "🔋 | **SCIENTIST'S GIFT!** **{player}** got __*advanced technology*__ from a brilliant inventor!",
    "🧪 | **ALCHEMIST'S GIFT!** **{player}** received __*experimental enhancement serum*__!",
    "🎒 | **NAVIGATOR'S GIFT!** **{player}** was given a __*fully stocked survival kit*__!",
    "💰 | **MERCHANT'S GIFT!** **{player}** received __*valuable berries*__ from a wealthy trader!",
    "🗺️ | **CARTOGRAPHER'S GIFT!** **{player}** was sent __*detailed sea charts*__ of the area!"
]

# One Piece Style Revival Messages - Devil Fruit Miracles and Sea Magic
REVIVAL_MESSAGES = [
    "✨ | **MIRACLE OF THE SEA!** ~~**{player}**~~ the Fallen was __*revived by a mysterious Devil Fruit power*__!",
    "💫 | **UNPRECEDENTED!** The power of friendship has __*brought*__ ~~**{player}**~~ the Deceased __*back to life*__!",
    "🌟 | **AMAZING!** ~~**{player}**~~ the Lost __*defied death*__ with the help of a legendary Sea King!",
    "⚡ | **SHOCKING!** ~~**{player}**~~ the Gone has been __*resurrected by ancient island magic*__!",
    "🎭 | **DRAMATIC TWIST!** ~~**{player}**~~ the Dead __*returns from Davy Jones' Locker*__!",
    "🔮 | **MYSTICAL!** Ancient sea magic has __*restored*__ ~~**{player}**~~ the Departed __*to the living*__!",
    "🧬 | **SCIENTIFIC BREAKTHROUGH!** Vegapunk's technology __*regenerated*__ ~~**{player}**~~ the Eliminated!",
    "👻 | **SUPERNATURAL!** ~~**{player}**~~ the Spirit __*materialized back*__ from the afterlife using Brook's Yomi-Yomi powers!"
]

# One Piece Themed Districts - Grand Line Islands and Locations
DISTRICTS = {
    1: "East Blue - Dawn Island",          # Luffy's home
    2: "East Blue - Syrup Village",        # Usopp's home
    3: "East Blue - Baratie",              # Sanji's restaurant
    4: "East Blue - Cocoyasi Village",     # Nami's home
    5: "Grand Line - Whisky Peak",        # First island
    6: "Grand Line - Little Garden",      # Giants' island
    7: "Grand Line - Drum Island",        # Chopper's home
    8: "Grand Line - Alabasta",           # Desert kingdom
    9: "Grand Line - Skypiea",            # Sky island
    10: "Grand Line - Water 7",           # Shipbuilding city
    11: "Grand Line - Thriller Bark",     # Ghost ship
    12: "New World - Dressrosa"           # Colosseum kingdom
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
    "the Mad", "the Sane", "the Dreamer", "the Realist", "the Optimist",
    "the Cold Hearted", "the Flame Bearer", "the Shadow Walker", "the Storm Bringer"
]

# Game Phases
GAME_PHASES = [
    "🌅 **DAWN** - The Grand Line awakens to a new battle...",
    "☀️ **MORNING** - The pirate hunt continues across the seas...",
    "🌞 **MIDDAY** - The sun beats down mercilessly on the battlefield...",
    "🌇 **AFTERNOON** - Storm clouds gather on the horizon...",
    "🌆 **EVENING** - The sea grows restless as darkness approaches...",
    "🌙 **NIGHT** - Only the strongest pirates survive the Grand Line's darkness...",
    "⭐ **MIDNIGHT** - The ocean holds its breath under starlight...",
    "🌌 **LATE NIGHT** - Devil Fruit powers lurk in every shadow..."
]

# Final showdown messages
FINALE_MESSAGES = [
    "⚔️ **FINAL CLASH!** Only {count} pirates remain on the Grand Line!",
    "🔥 **THE PIRATE KING'S THRONE AWAITS!** {count} survivors left!",
    "💀 **FINAL BATTLE INCOMING!** {count} pirates fight for the ultimate treasure!",
    "👑 **CROWNING THE PIRATE KING!** {count} contenders for the throne!",
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

# Victory Customization
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
        "🌪 **SPECTACULAR UPSET!**",
        "💫 **MIRACLE VICTORY!**"
    ],
    "final_duel": [  # 2 player games
        "⚔️ **FINAL DUEL VICTOR!**",
        "🥊 **ONE-ON-ONE CHAMPION!**",
        "🎯 **ULTIMATE SHOWDOWN WINNER!**",
        "💀 **LAST TRIBUTE STANDING!**"
    ]
}

# Midgame Atmospheric Events
MIDGAME_ATMOSPHERIC_EVENTS = [
    "🌙 | An eerie calm falls over the Grand Line as night approaches...",
    "🦅 | News Coos circle overhead, broadcasting the chaos to the world...",
    "🔊 | Wanted posters of fallen pirates float across the battlefield...",
    "⭐ | The stars above seem to judge the remaining warriors...",
    "🌿 | Strange sounds echo from the depths of the ocean...",
    "💨 | A sea breeze carries the scent of salt... and blood...",
    "🌫️ | Mysterious fog rolls across the waves, hiding unknown dangers...",
    "🎵 | The wind carries the final songs of defeated pirates..."
]

# Cannon Malfunction Events
CANNON_DEATH_EVENTS = [
    "💣💥 | A Marine battleship's cannon misfires and the blast catches ~~**{player}**~~ in the explosion!",
    "💣⚡ | ~~**{player}**~~ was struck by debris from an exploding cannon!",
    "💣🔥 | ~~**{player}**~~ couldn't escape the cannonball's devastating blast!",
    "💣💀 | ~~**{player}**~~ was caught in the shockwave of a ship's exploding armory!"
]

CANNON_SCARE_EVENTS = [
    "💣💨 | A Marine ship fires in the distance, the blast barely missing the pirates!",
    "💣⚠️ | A cannon misfires, sending cannonballs flying but harming no one!",
    "💣😰 | The sound of naval artillery echoes across the sea, making everyone take cover!",
    "💣🌪️ | A cannon blast creates massive waves, but all pirates brace their ships in time!"
]

# Toxic Fog Events (Devil Fruit Gas Powers)
TOXIC_FOG_SINGLE_DEATH = [
    "☠️💨 | Poison gas from a Devil Fruit user engulfs the area! ~~**{player}**~~ couldn't escape in time!",
    "☠️🌫️ | ~~**{player}**~~ was overwhelmed by the deadly purple miasma!",
    "☠️💜 | ~~**{player}**~~ succumbed to the toxic Devil Fruit power!",
    "☠️🏃 | ~~**{player}**~~ couldn't outrun the spreading poisonous cloud!"
]

TOXIC_FOG_MULTI_DEATH = "☠️💨 | Deadly gas from a Devil Fruit ability sweeps the battlefield, claiming {players}!"
TOXIC_FOG_SURVIVAL = "💨😅 | Poisonous gas rolls across the sea, but all pirates find shelter on their ships in time!"

# Tracker Jacker Events
TRACKER_JACKER_DEATHS = [
    "🐙💀 | ~~**{player}**~~ was dragged to the depths by a massive Sea King!",
    "🐙😵 | ~~**{player}**~~ was crushed by enormous tentacles!",
    "🐙🌪️ | ~~**{player}**~~ couldn't escape the Sea King's whirlpool attack!",
    "🐙⚡ | ~~**{player}**~~ was overwhelmed by the ocean beast's fury!"
]

TRACKER_JACKER_HALLUCINATION = "🌀 | **{player}** sees mirages from dehydration and sea madness!"
TRACKER_JACKER_AVOIDANCE = "🐙⚠️ | Massive Sea Kings circle below but seem to ignore the final pirates..."

# Arena Trap Types and Events
ARENA_TRAP_TYPES = [
    ("sea stone mine", "💎", "triggered a hidden seastone explosive"),
    ("net trap", "🕸️", "was caught in a Marine capture net"),
    ("spike trap", "⬆️", "was impaled by hidden Marine spikes"),
    ("cage trap", "⛓️", "was trapped in a seastone cage and couldn't break free"),
    ("gas trap", "☠️", "triggered a Marine poison gas trap"),
    ("blade trap", "⚔️", "was sliced by hidden Marine blade mechanisms"),
    ("electric trap", "⚡", "was shocked by a Marine Den Den Mushi trap")
]

ARENA_TRAP_DEATH = "{emoji}💀 | ~~**{player}**~~ {description}!"
ARENA_TRAP_ESCAPE = "{emoji}😅 | **{player}** narrowly avoids a Marine {trap_name}!"

# Muttation Types and Events
MUTTATION_TYPES = [
    ("Sea Kings", "🐙", "devoured by"),
    ("Giant Bees", "🐝", "stung to death by"),
    ("Kung Fu Dugongs", "🦭", "beaten down by"),
    ("Sky Sharks", "🦈", "torn apart by"),
    ("Poison Spiders", "🕷️", "poisoned by"),
    ("Sea Serpents", "🐍", "constricted by"),
    ("Fighting Fish", "🐠", "eaten alive by")
]

MUTTATION_DEATH = "{emoji}💀 | ~~**{player}**~~ was {death_verb} {creature_name}!"
MUTTATION_ESCAPE = "{emoji}⚠️ | {creature_name} prowl the waters, but the pirates manage to avoid them!"

# Environmental Hazard Types
ENVIRONMENTAL_HAZARDS = [
    ("sudden storm", "🌊", "swept overboard during"),
    ("reverse mountain current", "🌊", "crushed against rocks by"),
    ("lightning storm", "⚡", "struck by lightning during"),
    ("hailstorm", "❄️", "battered to death by"),
    ("fire rain", "🔥", "burned alive by"),
    ("tornado", "🌪️", "swept away by"),
    ("underwater volcano", "🌋", "boiled alive by")
]

ENVIRONMENTAL_SINGLE_DEATH = "{emoji}💀 | ~~**{player}**~~ was {death_description} the {hazard_name}!"
ENVIRONMENTAL_MULTI_DEATH = "{emoji}💀 | ~~**{player}**~~ was {death_description} the {hazard_name}!"
ENVIRONMENTAL_SURVIVAL = "{emoji}⚠️ | A {hazard_name} rocks the Grand Line, but all pirates weather it safely!"
ENVIRONMENTAL_PARTIAL_SURVIVAL = "{emoji}😅 | **{survivors}** managed to navigate through the chaos!"

# Gamemaker Test Events
GAMEMAKER_COURAGE_DEATH = "🏛️💀 | The World Government tests **{player}**'s resolve - ~~**they broke under pressure**~~!"
GAMEMAKER_COURAGE_SURVIVAL = "🏛️⚡ | **{player}** faces the World Government's trial and emerges stronger!"
GAMEMAKER_TEST_ANNOUNCEMENT = "🏛️⚠️ | The World Government announces a bounty increase for the remaining pirates..."
GAMEMAKER_LOYALTY_TEST = "🏛️⚡ | Marine spies test the pirates' alliances with false information..."

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

# Utility functions
def get_random_player_title():
    """Get a random player title/epithet"""
    import random
    return random.choice(PLAYER_TITLES)

def get_random_district():
    """Get a random district number (1-12)"""
    import random
    return random.randint(1, 12)

def get_event_weights():
    """Get default event weights for events"""
    return {
        "death": 30,
        "survival": 25,
        "sponsor": 15,
        "alliance": 15,
        "crate": 15
    }
