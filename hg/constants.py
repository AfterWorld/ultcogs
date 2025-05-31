# constants.py
"""Constants and configuration for the Hunger Games cog"""

# Game Configuration
DEFAULT_GUILD_CONFIG = {
    "games": {},
    "base_reward": 500,
    "sponsor_chance": 15,
    "event_interval": 30,
    "recruitment_time": 60,
    "enable_gifs": False,  # Added for GIF integration
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

DEATH_EVENTS = [
    "💀 | **{killer}** fed ~~**{player}**~~ to their pet Sea King!",
    "💀 | ~~**{player}**~~ got electrocuted trying to steal a Devil Fruit from the World Government vault.",
    "💀 | **{killer}** slipped a blade between ~~**{player}**~~'s ribs in the bustling port town!",
    "💀 | ~~**{player}**~~ drank seawater while having Devil Fruit powers and drowned helplessly.",
    "💀 | **{killer}** went into a rage and cleaved ~~**{player}**~~ in half with their legendary cutlass!",
    "💀 | ~~**{player}**~~ collapsed from exhaustion in the middle of a Marine raid.",
    "💀 | **{killer}** materialized behind ~~**{player}**~~ using Soru and slit their throat!",
    "💀 | ~~**{player}**~~ triggered a trap while exploring ancient Shandian ruins.",
    "💀 | **{killer}** devoured ~~**{player}**~~ alive using their Carnivorous Zoan powers!",
    "💀 | ~~**{player}**~~ touched a cursed treasure and was instantly turned to gold.",
    "💀 | **{killer}** crucified ~~**{player}**~~ on the town's execution platform for all to see!",
    "💀 | ~~**{player}**~~ was torn apart by Pacifista during a Buster Call.",
    "💀 | **{killer}** bludgeoned ~~**{player}**~~ to death with their kanabo!",
    "💀 | ~~**{player}**~~ got lost in the Calm Belt and became Sea King bait.",
    "💀 | **{killer}** slowly flayed ~~**{player}**~~ alive in their torture chamber on Thriller Bark!",
    "💀 | ~~**{player}**~~ fell into the ocean depths and was crushed by water pressure.",
    "💀 | **{killer}** keelhauled ~~**{player}**~~ beneath their ghostly pirate ship!",
    "💀 | ~~**{player}**~~ walked into Vegapunk's experimental laser grid.",
    "💀 | **{killer}** sacrificed ~~**{player}**~~ to summon an ancient Sea King!",
    "💀 | ~~**{player}**~~ was possessed by a vengeful spirit on Thriller Bark and self-destructed.",
    "💀 | **{killer}** impaled ~~**{player}**~~ with their trident in the Corrida Colosseum!",
    "💀 | ~~**{player}**~~ got crushed by falling debris during Whitebeard's earthquake.",
    "💀 | **{killer}** drained ~~**{player}**~~ completely dry using their Vampire Bat Zoan form!",
    "💀 | ~~**{player}**~~ ran straight into the Red Line at full speed.",
    "💀 | **{killer}** cursed ~~**{player}**~~ using their Voodoo-Voodoo Fruit powers!",
    "💀 | ~~**{player}**~~ was digested alive by a carnivorous plant on the Boin Archipelago.",
    "💀 | **{killer}** buried ~~**{player}**~~ alive under tons of rubble using their Earth-Earth Fruit!",
    "💀 | ~~**{player}**~~ fell off the edge of a Sky Island.",
    "💀 | **{killer}** burned ~~**{player}**~~ at the stake using their Flame-Flame Fruit!",
    "💀 | ~~**{player}**~~ activated a self-destruct Dial by accident.",
    "💀 | **{killer}** performed ritual seppuku on ~~**{player}**~~ with ceremonial precision!",
    "💀 | ~~**{player}**~~ was torn limb from limb by Kung-Fu Dugongs in the desert.",
    "💀 | **{killer}** harvested ~~**{player}**~~'s soul using their Soul-Soul Fruit powers!",
    "💀 | ~~**{player}**~~ drank obviously poisoned sake at the pirate feast.",
    "💀 | **{killer}** smashed ~~**{player}**~~ against the ship's mast repeatedly!",
    "💀 | ~~**{player}**~~ was consumed by shadow creatures in the Florian Triangle.",
    "💀 | **{killer}** tortured ~~**{player}**~~ to death with red-hot branding irons!",
    "💀 | ~~**{player}**~~ stepped on a pressure plate that triggered ancient Poneglyph defenses.",
    "💀 | **{killer}** had ~~**{player}**~~ thrown into the magma chamber of Punk Hazard!",
    "💀 | ~~**{player}**~~ was strangled by killer vines while napping in the jungle of Little Garden.",
    "💀 | **{killer}** carved ~~**{player}**~~ up like a piece of meat using their Dice-Dice Fruit!",
    "💀 | ~~**{player}**~~ got absorbed by Blackbeard's darkness powers.",
    "💀 | **{killer}** sacrificed ~~**{player}**~~ to their dark god on an obsidian altar!",
    "💀 | ~~**{player}**~~ sailed their ship straight into a massive whirlpool.",
    "💀 | **{killer}** garroted ~~**{player}**~~ with razor wire!",
    "💀 | ~~**{player}**~~ tried to pet a cyber-enhanced Tiger from Vegapunk's lab.",
    "💀 | **{killer}** ran ~~**{player}**~~ down with their ship at full sail!",
    "💀 | ~~**{player}**~~ ate poisonous mushrooms on the Boin Archipelago.",
    "💀 | **{killer}** locked ~~**{player}**~~ in Impel Down's Level 6 to rot forever!",
    "💀 | ~~**{player}**~~ got caught in the crossfire of a Yonko battle.",
    "💀 | **{killer}** gunned down ~~**{player}**~~ with their flintlock in broad daylight!",
    "💀 | ~~**{player}**~~ was betrayed by their own crew member.",
    "💀 | **{killer}** went berserk and tore ~~**{player}**~~ apart with their bare hands!",
    "💀 | ~~**{player}**~~ never woke up from Big Mom's dream-induced coma.",
    "💀 | **{killer}** dissolved ~~**{player}**~~ in a vat of acid using their Acid-Acid Fruit!",
    "💀 | ~~**{player}**~~ got lost in a temporal loop created by a Devil Fruit and aged to death instantly.",
    "💀 | **{killer}** decapitated ~~**{player}**~~ with a single sword draw!",
    "💀 | ~~**{player}**~~ challenged a Cipher Pol agent to combat and had their mind broken.",
    "💀 | **{killer}** vaporized ~~**{player}**~~ with a concentrated laser beam!",
    "💀 | ~~**{player}**~~ was driven insane by whispers from the Void Century.",
    "💀 | **{killer}** whipped ~~**{player}**~~ to death in the fighting pits of Dressrosa!",
    "💀 | ~~**{player}**~~ accidentally triggered explosive powder while raiding a Marine base.",
    "💀 | **{killer}** collected ~~**{player}**~~'s skull for their trophy wall!",
    "💀 | ~~**{player}**~~ was crushed by their own treasure hoard when their ship sank.",
    "💀 | **{killer}** possessed ~~**{player}**~~ using their Spirit-Spirit Fruit and made them jump overboard!",
    "💀 | ~~**{player}**~~ died of exhaustion while mining Sea Prism Stone.",
    "💀 | **{killer}** had ~~**{player}**~~ drawn and quartered in the town square!",
    "💀 | ~~**{player}**~~ was driven to madness by isolation on a deserted island.",
    "💀 | **{killer}** performed experimental surgery on ~~**{player}**~~ without anesthesia!",
    "💀 | ~~**{player}**~~ stood their ground against a horde of Marines and was overwhelmed.",
    "💀 | **{killer}** threw ~~**{player}**~~ to the wild beasts of Rusukaina!",
    "💀 | ~~**{player}**~~ touched an ancient weapon and was erased from existence.",
    "💀 | **{killer}** scalped ~~**{player}**~~ with a rusty cutlass!",
    "💀 | ~~**{player}**~~ drank liquid mercury thinking it was rum.",
    "💀 | **{killer}** beat ~~**{player}**~~ to death with a lead pipe for unpaid debts!",
    "💀 | ~~**{player}**~~ was flash-frozen by Aokiji's ice powers.",
    "💀 | **{killer}** impaled ~~**{player}**~~ on spikes as a warning to other pirates!",
    "💀 | ~~**{player}**~~ was devoured by dream parasites in the psychic realm of Totland.",
    "💀 | **{killer}** systematically eliminated ~~**{player}**~~ with extreme prejudice!",
    "💀 | ~~**{player}**~~ tried to surf on Akainu's magma flows.",
    "💀 | **{killer}** had ~~**{player}**~~ cement-shoed and thrown into the ocean!",
    "💀 | ~~**{player}**~~ was poisoned by contaminated food from a SMILE factory.",
    "💀 | **{killer}** cursed ~~**{player}**~~ to be eaten alive by spirit wolves!",
    "💀 | ~~**{player}**~~ volunteered for Vegapunk's experiments and mutated into oblivion.",
    "💀 | **{killer}** went into a blood rage and pulverized ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ fell asleep on a Sea Train track and was run over.",
    "💀 | **{killer}** haunted ~~**{player}**~~ using their Ghost-Ghost Fruit until they died of terror!",
    "💀 | ~~**{player}**~~ was betrayed by their navigator and sailed into a hurricane.",
    "💀 | **{killer}** threw ~~**{player}**~~ into the fighting pit with hungry beasts!",
    "💀 | ~~**{player}**~~ got stuck in a Devil Fruit paradox and ceased to exist.",
    "💀 | **{killer}** slowly peeled the skin off ~~**{player}**~~ using their Peel-Peel Fruit!",
    "💀 | ~~**{player}**~~ was disintegrated by ancient Poneglyph defense systems.",
    "💀 | **{killer}** made ~~**{player}**~~ walk the plank into shark-infested waters!",
    "💀 | ~~**{player}**~~ triggered an avalanche while climbing the Red Line.",
    "💀 | **{killer}** slowly tortured ~~**{player}**~~ to death for entertainment!",
    "💀 | ~~**{player}**~~ tried to reason with the World Government and was executed.",
    "💀 | **{killer}** crucified ~~**{player}**~~ upside down as an example to other pirates!",
    "💀 | ~~**{player}**~~ was consumed from the inside by parasitic Sea King larvae.",
    "💀 | **{killer}** tracked ~~**{player}**~~ through the Grand Line and finished them with a harpoon!",
    "💀 | ~~**{player}**~~ was betrayed by their own twin brother and stabbed in the back.",
    "💀 | **{killer}** beheaded ~~**{player}**~~ with their legendary blade!",
    "💀 | ~~**{player}**~~ wandered into a Devil's Triangle and was torn apart by supernatural forces.",
    "💀 | **{killer}** had ~~**{player}**~~ executed by Marine firing squad!",
    "💀 | ~~**{player}**~~ pressed the self-destruct button on a Marine warship.",
    "💀 | **{killer}** stalked ~~**{player}**~~ through the jungle and eviscerated them!",
    "💀 | ~~**{player}**~~ was trapped forever in a Mirror World dimension.",
    "💀 | **{killer}** obliterated ~~**{player}**~~ with their awakened Devil Fruit blast!",
    "💀 | ~~**{player}**~~ tried to make friends with the World Nobles.",
    "💀 | **{killer}** fed ~~**{player}**~~ to their mutant Sea King pet!",
    "💀 | ~~**{player}**~~ tripped and fell into the ocean with Devil Fruit powers.",
    "💀 | **{killer}** slowly lowered ~~**{player}**~~ into a vat of molten steel!",
    "💀 | **{killer}** stretched ~~**{player}**~~ until they snapped like rubber!",
    "💀 | ~~**{player}**~~ was devoured by a massive Sea King while trying to steal its treasure.",
    "💀 | **{killer}** executed ~~**{player}**~~ with a devastating magma punch!",
    "💀 | ~~**{player}**~~ fell into the ocean and drowned because of their Devil Fruit weakness.",
    "💀 | **{killer}** sliced ~~**{player}**~~ clean in half with their legendary blade!",
    "💀 | ~~**{player}**~~ got lost in the Florian Triangle and was consumed by the mist.",
    "💀 | **{killer}** turned ~~**{player}**~~ to ash with their fire powers!",
    "💀 | ~~**{player}**~~ tried to swim across the Calm Belt and became Sea King bait.",
    "💀 | **{killer}** froze ~~**{player}**~~ solid and shattered them into pieces!",
    "💀 | ~~**{player}**~~ was overwhelmed by a horde of Pacifista during the war.",
    "💀 | **{killer}** crushed ~~**{player}**~~ with Conqueror's Haki alone!",
    "💀 | ~~**{player}**~~ got caught in Enies Lobby's judicial waterfall.",
    "💀 | **{killer}** mauled ~~**{player}**~~ in their full Zoan beast form!",
    "💀 | ~~**{player}**~~ wandered into Impel Down and was tortured to death by the guards.",
    "💀 | **{killer}** impaled ~~**{player}**~~ with their dragon claw technique!",
    "💀 | ~~**{player}**~~ ate a poisonous Devil Fruit thinking it was regular food.",
    "💀 | **{killer}** made ~~**{player}**~~ walk the plank into a whirlpool!",
    "💀 | ~~**{player}**~~ was vaporized by one of Vegapunk's experimental weapons.",
    "💀 | **{killer}** used Fishman Karate to pierce straight through ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ got trampled by a herd of Kung-Fu Dugongs.",
    "💀 | **{killer}** turned ~~**{player}**~~ into a toy and erased their existence!",
    "💀 | ~~**{player}**~~ was trapped forever in a Mirror World dimension.",
    "💀 | **{killer}** obliterated ~~**{player}**~~ with their awakened Devil Fruit!",
    "💀 | ~~**{player}**~~ was assassinated by CP9 agents in their sleep.",
    "💀 | **{killer}** petrified ~~**{player}**~~ with their beauty and kicked them to pieces!",
    "💀 | ~~**{player}**~~ got caught in Whitebeard's earthquake and was buried under debris.",
    "💀 | **{killer}** stepped on ~~**{player}**~~ like they were an ant!",
    "💀 | ~~**{player}**~~ drank seawater in desperation and died of dehydration.",
    "💀 | **{killer}** blasted ~~**{player}**~~ to smithereens with their laser beam!",
    "💀 | ~~**{player}**~~ was crushed by their own treasure hoard in a collapsing cave.",
    "💀 | **{killer}** struck ~~**{player}**~~ down with divine lightning from Enel!",
    "💀 | ~~**{player}**~~ fell from a Sky Island and became a crater.",
    "💀 | **{killer}** electrocuted ~~**{player}**~~ with Electro during their Sulong form!",
    "💀 | ~~**{player}**~~ was dissolved by the acidic stomach of a massive sea beast.",
    "💀 | **{killer}** used Rokushiki to literally punch through ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ challenged Kaido to single combat and was obliterated.",
    "💀 | **{killer}** swapped ~~**{player}**~~'s heart with a rock using the Ope-Ope Fruit!",
    "💀 | ~~**{player}**~~ got caught in Big Mom's soul-stealing rampage.",
    "💀 | **{killer}** crushed ~~**{player}**~~ in their massive dinosaur jaws!",
    "💀 | ~~**{player}**~~ tried to steal from a Celestial Dragon and was executed on the spot.",
    "💀 | **{killer}** coated their fist with Haki and punched straight through ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ ate a SMILE fruit and laughed themselves to death.",
    "💀 | **{killer}** burned ~~**{player}**~~ to cinders with their fire fist!",
    "💀 | ~~**{player}**~~ was betrayed and sold to slave traders on Sabaody.",
    "💀 | **{killer}** puppeteered ~~**{player}**~~ into killing themselves using their String-String Fruit!",
    "💀 | ~~**{player}**~~ was fed explosive food by a vengeful cook.",
    "💀 | **{killer}** split ~~**{player}**~~ in two with a single sword draw!",
    "💀 | ~~**{player}**~~ sailed into the New World unprepared and was instantly vaporized.",
    "💀 | **{killer}** struck ~~**{player}**~~ with a 200 million volt lightning bolt!",
    "💀 | ~~**{player}**~~ got sucked into a Knock Up Stream without proper preparation.",
    "💀 | **{killer}** stretched their arm across the island to punch ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ was cursed by Aztec gold and crumbled to dust.",
    "💀 | **{killer}** impaled ~~**{player}**~~ with razor-sharp bone spears!",
    "💀 | ~~**{player}**~~ was poisoned by a seemingly friendly barkeeper.",
    "💀 | **{killer}** drained all moisture from ~~**{player}**~~ using their Sand-Sand Fruit!",
    "💀 | ~~**{player}**~~ got caught in crossfire between two Yonko crews.",
    "💀 | **{killer}** froze the entire ocean with ~~**{player}**~~ trapped inside!",
    "💀 | ~~**{player}**~~ was overtaken by a deadly Buster Call bombardment.",
    "💀 | **{killer}** struck ~~**{player}**~~ with 200 million volt divine judgment!",
    "💀 | ~~**{player}**~~ was caught in the middle of a Conqueror's Haki clash.",
    "💀 | **{killer}** snuck up on ~~**{player}**~~ and slit their throat with a hidden blade!",
    "💀 | ~~**{player}**~~ tried to befriend a wild tiger on Rusukaina Island.",
    "💀 | **{killer}** encased ~~**{player}**~~ in hardened wax and let them suffocate!",
    "💀 | ~~**{player}**~~ opened an ancient weapon's vault and released destructive forces.",
    "💀 | **{killer}** dive-bombed ~~**{player}**~~ with blazing phoenix talons!",
    "💀 | ~~**{player}**~~ was trapped in an eternal nightmare by a Sleep-Sleep fruit user.",
    "💀 | **{killer}** moved at light speed and bisected ~~**{player}**~~!",
    "💀 | ~~**{player}**~~ tried to navigate the Grand Line without a Log Pose and sailed into a hurricane.",
    "💀 | **{killer}** stole ~~**{player}**~~'s shadow and they crumbled in daylight!",
    "💀 | ~~**{player}**~~ was overwhelmed by the sheer presence of a Yonko's Conqueror's Haki.",
    "💀 | **{killer}** shattered the very air and ~~**{player}**~~ along with it using their Tremor-Tremor Fruit!",
    "💀 | ~~**{player}**~~ challenged Mihawk to a sword duel with a butter knife.",
    "💀 | **{killer}** trapped ~~**{player}**~~ in an inescapable barrier until they suffocated!",
    "💀 | ~~**{player}**~~ got their soul sucked out by Big Mom's homies.",
    "💀 | **{killer}** opened a door in ~~**{player}**~~'s chest and reached through using their Door-Door Fruit!",
    "💀 | ~~**{player}**~~ got lost in the Florian Triangle and was never seen again.",
    "💀 | **{killer}** turned ~~**{player}**~~ into a puddle of magma!",
    "💀 | ~~**{player}**~~ ate poisonous pufferfish sashimi prepared by an amateur chef.",
    "💀 | **{killer}** obliterated ~~**{player}**~~ and their entire island with an ancient weapon!"
]

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

# GIF Integration Constants
ENABLE_GIFS = False  # Set to True once GIFs are added
GIF_BASE_PATH = "gifs"
GIF_CACHE_TIMEOUT = 300  # 5 minutes
SUPPORTED_GIF_FORMATS = ['.gif', '.webp', '.mp4', '.mov']

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

# Future GIF Integration Structure
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
