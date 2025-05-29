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
EXTENDED_DEATH_EVENTS = [
    "💀 | **{killer}** the Bloodthirsty fed ~~**{player}**~~ the Helpless to their pet dragon!",
    "💀 | ~~**{player}**~~ the Overconfident got electrocuted trying to hack the mainframe.",
    "💀 | **{killer}** the Assassin slipped a blade between ~~**{player}**~~ the Unaware's ribs in the crowded marketplace!",
    "💀 | ~~**{player}**~~ the Thirsty drank contaminated water from the radioactive river.",
    "💀 | **{killer}** the Berserker went into a rage and cleaved ~~**{player}**~~ the Innocent in half with a battle axe!",
    "💀 | ~~**{player}**~~ the Sleepless collapsed from exhaustion in the middle of the zombie horde.",
    "💀 | **{killer}** the Phantom materialized behind ~~**{player}**~~ the Paranoid and slit their throat!",
    "💀 | ~~**{player}**~~ the Greedy triggered a booby trap while looting the ancient tomb.",
    "💀 | **{killer}** the Cannibal devoured ~~**{player}**~~ the Tender alive in the post-apocalyptic wasteland!",
    "💀 | ~~**{player}**~~ the Rash touched the cursed artifact and was instantly incinerated.",
    "💀 | **{killer}** the Warlord crucified ~~**{player}**~~ the Rebel on the city gates for all to see!",
    "💀 | ~~**{player}**~~ the Optimistic was torn apart by robotic sentries in the forbidden zone.",
    "💀 | **{killer}** the Madman bludgeoned ~~**{player}**~~ the Peaceful to death with a crowbar!",
    "💀 | ~~**{player}**~~ the Naive got lost in the interdimensional portal maze and starved.",
    "💀 | **{killer}** the Torturer slowly flayed ~~**{player}**~~ the Screaming alive in their dungeon!",
    "💀 | ~~**{player}**~~ the Adventurous fell into a pit of space-time anomalies.",
    "💀 | **{killer}** the Pirate keelhauled ~~**{player}**~~ the Mutinous beneath their ghostly ship!",
    "💀 | ~~**{player}**~~ the Careless walked into a field of plasma mines.",
    "💀 | **{killer}** the Necromancer sacrificed ~~**{player}**~~ the Pure to summon demons from the void!",
    "💀 | ~~**{player}**~~ the Curious was possessed by malevolent AI and self-destructed.",
    "💀 | **{killer}** the Gladiator impaled ~~**{player}**~~ the Cowering with a trident in the arena!",
    "💀 | ~~**{player}**~~ the Unlucky got crushed by a falling meteor in the asteroid field.",
    "💀 | **{killer}** the Vampire drained ~~**{player}**~~ the Anemic completely dry in the moonlit cemetery!",
    "💀 | ~~**{player}**~~ the Hasty ran straight into a force field barrier at full speed.",
    "💀 | **{killer}** the Witch cursed ~~**{player}**~~ the Skeptical to die of a thousand cuts!",
    "💀 | ~~**{player}**~~ the Hungry was digested alive by a carnivorous plant in the bio-dome.",
    "💀 | **{killer}** the Demolisher buried ~~**{player}**~~ the Cornered alive under tons of rubble!",
    "💀 | ~~**{player}**~~ the Dizzy fell off the edge of the floating sky city.",
    "💀 | **{killer}** the Zealot burned ~~**{player}**~~ the Heretic at the stake in righteous fury!",
    "💀 | ~~**{player}**~~ the Clumsy activated the self-destruct sequence by accident.",
    "💀 | **{killer}** the Samurai performed seppuku on ~~**{player}**~~ the Dishonored with ceremonial precision!",
    "💀 | ~~**{player}**~~ the Weak was torn limb from limb by mutant bears in the irradiated forest.",
    "💀 | **{killer}** the Reaper harvested ~~**{player}**~~ the Marked's soul with their spectral scythe!",
    "💀 | ~~**{player}**~~ the Gullible drank the obviously poisoned chalice at the feast.",
    "💀 | **{killer}** the Brute smashed ~~**{player}**~~ the Fragile against the concrete wall repeatedly!",
    "💀 | ~~**{player}**~~ the Lost was consumed by shadow creatures in the void between dimensions.",
    "💀 | **{killer}** the Inquisitor tortured ~~**{player}**~~ the Confessor to death with red-hot irons!",
    "💀 | ~~**{player}**~~ the Impatient stepped on a pressure plate that triggered laser turrets.",
    "💀 | **{killer}** the Overlord had ~~**{player}**~~ the Defiant thrown into the lava forge!",
    "💀 | ~~**{player}**~~ the Sleepy was strangled by killer vines while napping in the jungle.",
    "💀 | **{killer}** the Butcher carved ~~**{player}**~~ the Tender up like a piece of meat!",
    "💀 | ~~**{player}**~~ the Curious got absorbed by the experimental black hole device.",
    "💀 | **{killer}** the Cultist sacrificed ~~**{player}**~~ the Virgin to their dark god on the obsidian altar!",
    "💀 | ~~**{player}**~~ the Reckless drove their hover-bike straight into the plasma storm.",
    "💀 | **{killer}** the Executioner garroted ~~**{player}**~~ the Condemned with razor wire!",
    "💀 | ~~**{player}**~~ the Foolish tried to pet a cyber-enhanced sabertooth tiger.",
    "💀 | **{killer}** the Marauder ran ~~**{player}**~~ the Fleeing down with their war chariot!",
    "💀 | ~~**{player}**~~ the Hungry ate glowing mushrooms in the alien cavern system.",
    "💀 | **{killer}** the Warden locked ~~**{player}**~~ the Prisoner in the oubliette to rot forever!",
    "💀 | ~~**{player}**~~ the Unlucky got caught in the crossfire of a mech battle.",
    "💀 | **{killer}** the Sicario gunned down ~~**{player}**~~ the Witness in broad daylight!",
    "💀 | ~~**{player}**~~ the Trusting was betrayed by their own android companion.",
    "💀 | **{killer}** the Berserker went berserk and tore ~~**{player}**~~ the Peaceful apart with their bare hands!",
    "💀 | ~~**{player}**~~ the Dreamer never woke up from the virtual reality nightmare.",
    "💀 | **{killer}** the Alchemist dissolved ~~**{player}**~~ the Curious in a vat of acid!",
    "💀 | ~~**{player}**~~ the Wanderer got lost in the temporal loop and aged to death instantly.",
    "💀 | **{killer}** the Gladiator decapitated ~~**{player}**~~ the Challenger with a single swing!",
    "💀 | ~~**{player}**~~ the Cocky challenged a quantum computer to chess and had their brain fried.",
    "💀 | **{killer}** the Bounty Hunter vaporized ~~**{player}**~~ the Fugitive with a plasma rifle!",
    "💀 | ~~**{player}**~~ the Paranoid was driven insane by whispers from the cosmic void.",
    "💀 | **{killer}** the Slaver whipped ~~**{player}**~~ the Rebellious to death in the fighting pits!",
    "💀 | ~~**{player}**~~ the Clumsy accidentally triggered a nuclear warhead while scavenging.",
    "💀 | **{killer}** the Headhunter collected ~~**{player}**~~ the Valuable's skull for their trophy wall!",
    "💀 | ~~**{player}**~~ the Greedy was crushed by their own hoarded treasure when the vault collapsed.",
    "💀 | **{killer}** the Demon possessed ~~**{player}**~~ the Innocent and made them self-immolate!",
    "💀 | ~~**{player}**~~ the Overworked died of exhaustion while mining asteroids in zero gravity.",
    "💀 | **{killer}** the Tyrant had ~~**{player}**~~ the Outspoken drawn and quartered in the town square!",
    "💀 | ~~**{player}**~~ the Lonely was driven to madness by isolation in the sensory deprivation chamber.",
    "💀 | **{killer}** the Surgeon performed experimental surgery on ~~**{player}**~~ the Unwilling without anesthesia!",
    "💀 | ~~**{player}**~~ the Brave stood their ground against a horde of cyber-zombies and was overwhelmed.",
    "💀 | **{killer}** the Warchief threw ~~**{player}**~~ the Coward to the dire wolves!",
    "💀 | ~~**{player}**~~ the Curious touched the time crystal and was erased from existence.",
    "💀 | **{killer}** the Raider scalped ~~**{player}**~~ the Settler with a rusty machete!",
    "💀 | ~~**{player}**~~ the Thirsty drank liquid mercury thinking it was water.",
    "💀 | **{killer}** the Enforcer beat ~~**{player}**~~ the Debtor to death with a lead pipe for unpaid debts!",
    "💀 | ~~**{player}**~~ the Explorer was flash-frozen in the cryogenic laboratory malfunction.",
    "💀 | **{killer}** the Warlord impaled ~~**{player}**~~ the Messenger on spikes as a warning to others!",
    "💀 | ~~**{player}**~~ the Sleepy was devoured by dream parasites in the psychic realm.",
    "💀 | **{killer}** the Terminator systematically eliminated ~~**{player}**~~ the Target with extreme prejudice!",
    "💀 | ~~**{player}**~~ the Rash tried to surf on molten lava flows.",
    "💀 | **{killer}** the Crimelord had ~~**{player}**~~ the Snitch cement-shoed and thrown into the harbor!",
    "💀 | ~~**{player}**~~ the Hungry was poisoned by radioactive food rations.",
    "💀 | **{killer}** the Shaman cursed ~~**{player}**~~ the Disbeliever to be eaten alive by spirit wolves!",
    "💀 | ~~**{player}**~~ the Eager volunteered for genetic experiments and mutated into oblivion.",
    "💀 | **{killer}** the Berserker went into blood rage and pulverized ~~**{player}**~~ the Peacemaker!",
    "💀 | ~~**{player}**~~ the Lazy fell asleep on the conveyor belt and was processed by factory machinery.",
    "💀 | **{killer}** the Spectre haunted ~~**{player}**~~ the Skeptical until they died of pure terror!",
    "💀 | ~~**{player}**~~ the Hopeful was betrayed by their AI companion and ejected into space.",
    "💀 | **{killer}** the Savage threw ~~**{player}**~~ the Civilized into the fighting pit with hungry raptors!",
    "💀 | ~~**{player}**~~ the Unlucky got stuck in a temporal paradox and ceased to exist.",
    "💀 | **{killer}** the Torturer slowly peeled the skin off ~~**{player}**~~ the Screaming!",
    "💀 | ~~**{player}**~~ the Curious was disintegrated by the alien defense system.",
    "💀 | **{killer}** the Admiral made ~~**{player}**~~ the Mutineer walk the plank into the void of space!",
    "💀 | ~~**{player}**~~ the Careless triggered an avalanche while skiing down the radioactive mountain.",
    "💀 | **{killer}** the Psychopath slowly tortured ~~**{player}**~~ the Innocent to death for entertainment!",
    "💀 | ~~**{player}**~~ the Foolish tried to reason with the genocidal AI overlord.",
    "💀 | **{killer}** the Conqueror crucified ~~**{player}**~~ the Resistant upside down as an example!",
    "💀 | ~~**{player}**~~ the Hungry was consumed from the inside by parasitic nanobots.",
    "💀 | **{killer}** the Huntsman tracked ~~**{player}**~~ the Prey through the nuclear wasteland and finished them with a harpoon!",
    "💀 | ~~**{player}**~~ the Trusting was betrayed by their own clone and stabbed in the back.",
    "💀 | **{killer}** the Slayer beheaded ~~**{player}**~~ the Cowardly with an energy sword!",
    "💀 | ~~**{player}**~~ the Lost wandered into the interdimensional rift and was torn apart.",
    "💀 | **{killer}** the Dictator had ~~**{player}**~~ the Protestor executed by firing squad!",
    "💀 | ~~**{player}**~~ the Impatient pressed the big red button labeled 'DO NOT PRESS'.",
    "💀 | **{killer}** the Predator stalked ~~**{player}**~~ the Helpless through the cyber jungle and eviscerated them!",
    "💀 | ~~**{player}**~~ the Dreamer was trapped forever in a virtual reality horror simulation.",
    "💀 | **{killer}** the Destroyer obliterated ~~**{player}**~~ the Fragile with a plasma cannon blast!",
    "💀 | ~~**{player}**~~ the Optimistic tried to make friends with the killer robots.",
    "💀 | **{killer}** the Overlord fed ~~**{player}**~~ the Expendable to their mutant pet shark!",
    "💀 | ~~**{player}**~~ the Clumsy tripped and fell into the antimatter containment unit.",
    "💀 | **{killer}** the Executioner slowly lowered ~~**{player}**~~ the Condemned into a vat of molten steel!",
    "💀 | **{killer}** the Devil Fruit User stretched ~~**{player}**~~ the Unlucky until they snapped like a rubber band!",
    "💀 | ~~**{player}**~~ the Greedy was devoured by a massive Sea King while trying to steal its treasure.",
    "💀 | **{killer}** the Marine Admiral executed ~~**{player}**~~ the Pirate with a devastating magma punch!",
    "💀 | ~~**{player}**~~ the Cursed fell into the ocean and drowned because of their Devil Fruit weakness.",
    "💀 | **{killer}** the Swordsman sliced ~~**{player}**~~ the Helpless clean in half with their legendary blade!",
    "💀 | ~~**{player}**~~ the Navigator got lost in the Florian Triangle and was consumed by the mist.",
    "💀 | **{killer}** the Logia User turned ~~**{player}**~~ the Unfortunate to ash with their fire powers!",
    "💀 | ~~**{player}**~~ the Foolish tried to swim across the Calm Belt and became Sea King bait.",
    "💀 | **{killer}** the Shichibukai froze ~~**{player}**~~ the Challenger solid and shattered them!",
    "💀 | ~~**{player}**~~ the Weak was overwhelmed by a horde of Pacifista during the war.",
    "💀 | **{killer}** the Yonko Commander crushed ~~**{player}**~~ the Rookie with Conqueror's Haki alone!",
    "💀 | ~~**{player}**~~ the Careless got caught in Enies Lobby's judicial waterfall.",
    "💀 | **{killer}** the Zoan User mauled ~~**{player}**~~ the Defenseless in their full beast form!",
    "💀 | ~~**{player}**~~ the Lost wandered into Impel Down and was tortured to death by the guards.",
    "💀 | **{killer}** the Revolutionary impaled ~~**{player}**~~ the Loyalist with their dragon claw technique!",
    "💀 | ~~**{player}**~~ the Hungry ate a poisonous Devil Fruit thinking it was regular food.",
    "💀 | **{killer}** the Pirate Captain made ~~**{player}**~~ the Mutineer walk the plank into a whirlpool!",
    "💀 | ~~**{player}**~~ the Curious was vaporized by one of Vegapunk's experimental weapons.",
    "💀 | **{killer}** the Fishman used Water Shot to pierce straight through ~~**{player}**~~ the Surprised!",
    "💀 | ~~**{player}**~~ the Unlucky got trampled by a herd of Kung-Fu Dugongs.",
    "💀 | **{killer}** the Paramecia User turned ~~**{player}**~~ the Victim into a toy and forgot they ever existed!",
    "💀 | ~~**{player}**~~ the Dreamer was trapped forever in a Mirror World dimension.",
    "💀 | **{killer}** the Supernova obliterated ~~**{player}**~~ the Bystander with their awakened Devil Fruit!",
    "💀 | ~~**{player}**~~ the Sleepy was assassinated by CP9 agents in their sleep.",
    "💀 | **{killer}** the Warlord petrified ~~**{player}**~~ the Smitten with their beauty and kicked them to pieces!",
    "💀 | ~~**{player}**~~ the Reckless got caught in Whitebeard's earthquake and was buried under debris.",
    "💀 | **{killer}** the Giant stepped on ~~**{player}**~~ the Tiny like they were an ant!",
    "💀 | ~~**{player}**~~ the Thirsty drank seawater in desperation and died of dehydration.",
    "💀 | **{killer}** the Cyborg blasted ~~**{player}**~~ the Organic to smithereens with their laser beam!",
    "💀 | ~~**{player}**~~ the Greedy was crushed by their own treasure hoard in a collapsing cave.",
    "💀 | **{killer}** the Sky Islander struck ~~**{player}**~~ the Trespasser down with divine lightning!",
    "💀 | ~~**{player}**~~ the Landlubber fell from a Sky Island and became a crater.",
    "💀 | **{killer}** the Mink electrocuted ~~**{player}**~~ the Invader with Electro during Sulong form!",
    "💀 | ~~**{player}**~~ the Curious was dissolved by the acidic stomach of a massive sea beast.",
    "💀 | **{killer}** the Assassin used Rokushiki to literally punch through ~~**{player}**~~ the Unsuspecting!",
    "💀 | ~~**{player}**~~ the Overconfident challenged Kaido to single combat and was obliterated.",
    "💀 | **{killer}** the Surgeon of Death swapped ~~**{player}**~~ the Panicked's heart with a rock!",
    "💀 | ~~**{player}**~~ the Unlucky got caught in Big Mom's soul-stealing rampage.",
    "💀 | **{killer}** the Ancient Zoan crushed ~~**{player}**~~ the Frightened in their massive dinosaur jaws!",
    "💀 | ~~**{player}**~~ the Foolish tried to steal from a Celestial Dragon and was executed on the spot.",
    "💀 | **{killer}** the Haki Master coated their fist and punched straight through ~~**{player}**~~ the Weak!",
    "💀 | ~~**{player}**~~ the Confused ate a SMILE fruit and laughed themselves to death.",
    "💀 | **{killer}** the Flame Emperor burned ~~**{player}**~~ the Combustible to cinders with their fire fist!",
    "💀 | ~~**{player}**~~ the Hopeful was betrayed and sold to slave traders on Sabaody.",
    "💀 | **{killer}** the String Master puppeteered ~~**{player}**~~ the Helpless into killing themselves!",
    "💀 | ~~**{player}**~~ the Hungry was fed explosive food by a vengeful cook.",
    "💀 | **{killer}** the Dark King split ~~**{player}**~~ the Arrogant in two with a single sword draw!",
    "💀 | ~~**{player}**~~ the Lost sailed into the New World unprepared and was instantly vaporized.",
    "💀 | **{killer}** the Weather Witch struck ~~**{player}**~~ the Unlucky with a concentrated lightning bolt!",
    "💀 | ~~**{player}**~~ the Careless got sucked into a Knock Up Stream without proper preparation.",
    "💀 | **{killer}** the Rubber Human stretched their arm across the island to punch ~~**{player}**~~ the Distant!",
    "💀 | ~~**{player}**~~ the Greedy was cursed by Aztec gold and crumbled to dust.",
    "💀 | **{killer}** the Bone User impaled ~~**{player}**~~ the Screaming with razor-sharp bone spears!",
    "💀 | ~~**{player}**~~ the Trusting was poisoned by a seemingly friendly barkeeper.",
    "💀 | **{killer}** the Sand Crocodile drained all moisture from ~~**{player}**~~ the Withered!",
    "💀 | ~~**{player}**~~ the Unlucky got caught in crossfire between two Yonko crews.",
    "💀 | **{killer}** the Ice Admiral froze the entire ocean with ~~**{player}**~~ the Swimming trapped inside!",
    "💀 | ~~**{player}**~~ the Slow was overtaken by a deadly Buster Call bombardment.",
    "💀 | **{killer}** the Thunder God struck ~~**{player}**~~ the Heretic with 200 million volt divine judgment!",
    "💀 | ~~**{player}**~~ the Peaceful was caught in the middle of a Conqueror's Haki clash.",
    "💀 | **{killer}** the Invisible Man snuck up on ~~**{player}**~~ the Oblivious and slit their throat!",
    "💀 | ~~**{player}**~~ the Optimistic tried to befriend a wild tiger on Rusukaina Island.",
    "💀 | **{killer}** the Wax Human encased ~~**{player}**~~ the Struggling in hardened wax and let them suffocate!",
    "💀 | ~~**{player}**~~ the Curious opened Pandora's Box and released ancient curses.",
    "💀 | **{killer}** the Phoenix dive-bombed ~~**{player}**~~ the Earthbound with blazing talons!",
    "💀 | ~~**{player}**~~ the Dreamer was trapped in an eternal nightmare by a Sleep-Sleep fruit user.",
    "💀 | **{killer}** the Light Human moved at light speed and bisected ~~**{player}**~~ the Slow!",
    "💀 | ~~**{player}**~~ the Landlocked tried to navigate the Grand Line without a Log Pose and sailed into a hurricane.",
    "💀 | **{killer}** the Shadow Master stole ~~**{player}**~~ the Sunlit's shadow and they crumbled in daylight!",
    "💀 | ~~**{player}**~~ the Weak was overwhelmed by the sheer presence of a Yonko's Conqueror's Haki.",
    "💀 | **{killer}** the Quake Human shattered the very air and ~~**{player}**~~ the Fragile along with it!",
    "💀 | ~~**{player}**~~ the Foolish challenged Mihawk to a sword duel with a butter knife.",
    "💀 | **{killer}** the Barrier User trapped ~~**{player}**~~ the Claustrophobic in an inescapable barrier until they suffocated!",
    "💀 | ~~**{player}**~~ the Unlucky got their soul sucked out by Big Mom's homies.",
    "💀 | **{killer}** the Door-Door fruit user opened a door in ~~**{player}**~~ the Solid's chest and reached through!",
    "💀 | ~~**{player}**~~ the Careless got lost in the Florian Triangle and was never seen again.",
    "💀 | **{killer}** the Magma Admiral turned ~~**{player}**~~ the Frozen into a puddle of lava!",
    "💀 | ~~**{player}**~~ the Hungry ate poisonous pufferfish sashimi prepared by an amateur chef.",
    "💀 | **{killer}** the Ancient Weapon obliterated ~~**{player}**~~ the Insignificant and their entire island!"
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
