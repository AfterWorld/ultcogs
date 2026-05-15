"""
One Piece Devil Fruit data.
Each fruit has: name, type, rarity, ability, awakening_1 (lvl 15), awakening_2 (lvl 30).
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Rarity weights — must sum to 100
# ---------------------------------------------------------------------------
RARITY_WEIGHTS: Dict[str, float] = {
    "Paramecia":     50.0,
    "Zoan":          25.0,
    "Logia":         15.0,
    "Ancient Zoan":   7.0,
    "Mythical Zoan":  2.5,
    "Legendary":      0.5,
}

REROLL_COST_TABLE: List[int] = [
    10_000,   # 1st reroll
    25_000,   # 2nd
    50_000,   # 3rd
    100_000,  # 4th+ (cap)
]

FRUIT_ASSIGN_LEVEL     = 5
AWAKENING_STAGE1_LEVEL = 15
AWAKENING_STAGE2_LEVEL = 30

# ---------------------------------------------------------------------------
# Fruit definitions
# ---------------------------------------------------------------------------
DEVIL_FRUITS: Dict[str, List[dict]] = {

    # -----------------------------------------------------------------------
    "Paramecia": [
        {
            "name": "Gomu Gomu no Mi (Rubber-Rubber Fruit)",
            "ability": "Your body has the properties of rubber — you are immune to blunt force and can stretch any limb to devastating lengths.",
            "awakening_1": "Your rubber nature begins to overflow outwardly. You can coat nearby surfaces in rubber, redirecting kinetic force and creating elastic terrain.",
            "awakening_2": "The fruit's true nature awakens — the legendary Hito Hito no Mi, Model: Nika. Your body becomes the \"Sun God,\" granting limitless freedom and the ability to make your imagination reality. Gear 5.",
        },
        {
            "name": "Bara Bara no Mi (Chop-Chop Fruit)",
            "ability": "Your body can be split apart into independent pieces and reassembled instantly. You are immune to slashing attacks.",
            "awakening_1": "You can detach and independently control each body part at greater range and speed, overwhelming foes with coordinated strikes from all directions.",
            "awakening_2": "Your dismemberment extends to objects you touch — you can split and freely rearrange structures, weapons, and terrain in your vicinity.",
        },
        {
            "name": "Sube Sube no Mi (Slip-Slip Fruit)",
            "ability": "Your skin is perfectly smooth — all physical attacks slide off harmlessly, and you can make any surface frictionless.",
            "awakening_1": "You project a slipperiness aura, causing enemies nearby to lose footing. Projectiles and energy attacks glide away from you.",
            "awakening_2": "You extend frictionless fields across large areas, turning battlefields into chaotic slip zones while you move freely at extreme speed.",
        },
        {
            "name": "Bomu Bomu no Mi (Bomb-Bomb Fruit)",
            "ability": "Any part of your body — breath, sweat, hair — becomes explosive. You are immune to explosions.",
            "awakening_1": "Your explosive energy radiates passively. You can prime nearby objects with delayed detonations just by touching them.",
            "awakening_2": "You can generate a massive sustained explosion field, detonating the very air around you in rhythmic concussive waves.",
        },
        {
            "name": "Kiro Kiro no Mi (Kilo-Kilo Fruit)",
            "ability": "You can freely alter your body weight from 1 kg to 10,000 kg, using mass as a weapon or becoming nearly weightless.",
            "awakening_1": "You extend weight manipulation to nearby objects and people — selectively crushing foes or making allies light as a feather.",
            "awakening_2": "You can create gravitational pulses, slamming or launching entire groups at will, with your own weight changing instantaneously.",
        },
        {
            "name": "Doru Doru no Mi (Wax-Wax Fruit)",
            "ability": "You produce and harden candle wax strong enough to rival steel — useful for constructs, traps, and encasing enemies.",
            "awakening_1": "Your wax sets almost instantly on contact, trapping enemies mid-movement. You sculpt complex structures in seconds.",
            "awakening_2": "You can cover entire battlefields in hardened wax terrain, reshaping the environment into fortified architecture or prison cells at will.",
        },
        {
            "name": "Baku Baku no Mi (Munch-Munch Fruit)",
            "ability": "You can eat and digest anything — metal, wood, stone — and fuse eaten materials into your body to gain their properties.",
            "awakening_1": "You rapidly assimilate eaten materials, weaponizing them as armor plating, projectiles, or extending limbs of pure matter.",
            "awakening_2": "You can consume massive structures whole, rebuilding them as part of your body or launching them as artillery with your own strength.",
        },
        {
            "name": "Mane Mane no Mi (Clone-Clone Fruit)",
            "ability": "By touching someone's face, you can perfectly replicate their appearance, voice, and fighting style.",
            "awakening_1": "You can now copy multiple people simultaneously, maintaining their forms without physical contact once learned.",
            "awakening_2": "You can project life-like duplicates of copied individuals, creating illusory allies indistinguishable from the real thing.",
        },
        {
            "name": "Toge Toge no Mi (Spike-Spike Fruit)",
            "ability": "You can produce razor-sharp spikes from any part of your body on demand.",
            "awakening_1": "You launch spike volleys at high velocity and extend them in directional barriers that cover wide arcs.",
            "awakening_2": "You generate an omnidirectional spike field that radiates continuously outward, shredding anything in range.",
        },
        {
            "name": "Ori Ori no Mi (Cage-Cage Fruit)",
            "ability": "You generate iron shackles and restraints from your body, binding enemies in place.",
            "awakening_1": "Your bindings grow to encase entire areas — foes who enter your range are automatically seized.",
            "awakening_2": "You create a self-sustaining iron cage zone that contracts inward, inescapable without tremendous force.",
        },
        {
            "name": "Bane Bane no Mi (Spring-Spring Fruit)",
            "ability": "Your limbs transform into coiled springs, granting explosive jumping ability and spring-loaded strikes.",
            "awakening_1": "You convert inertia into stored spring energy — absorbing impacts and releasing them with multiplied force.",
            "awakening_2": "Your entire body becomes a high-tension spring system, moving at eye-blurring speed with every action driven by explosive release.",
        },
        {
            "name": "Noro Noro no Mi (Slow-Slow Fruit)",
            "ability": "You emit Noro Noro Beams that slow anything they hit to 1/30th of normal speed for 30 seconds.",
            "awakening_1": "Your slow field now radiates passively, gradually reducing the tempo of all movement in your vicinity.",
            "awakening_2": "You can slow time locally for a chosen target to near standstill while you move freely at full speed — a terrifying differential.",
        },
        {
            "name": "Doa Doa no Mi (Door-Door Fruit)",
            "ability": "You can create doors in any surface — walls, air, even people — granting passage or exposing vulnerabilities.",
            "awakening_1": "You create doors faster and at greater range, linking entry points across distances for rapid repositioning.",
            "awakening_2": "You open dimensional doors that transport you or attacks across vast distances instantaneously.",
        },
        {
            "name": "Awa Awa no Mi (Bubble-Bubble Fruit)",
            "ability": "You generate soap bubbles that wash away special abilities on contact, neutralizing Devil Fruit and Haki buffs.",
            "awakening_1": "Your bubbles persist and seek targets semi-autonomously, making it nearly impossible to avoid ability suppression.",
            "awakening_2": "You create a cleansing aura — enemies within range continuously have their powers stripped as fast as they activate them.",
        },
        {
            "name": "Beri Beri no Mi (Berry-Berry Fruit)",
            "ability": "Your body separates into dozens of small berry-like spheres, letting you dodge through attacks and reform instantly.",
            "awakening_1": "Your spheres move faster and strike independently as projectiles while your core remains protected.",
            "awakening_2": "You fragment to microscopic scale, becoming effectively intangible and reforming in any configuration explosively.",
        },
        {
            "name": "Sabi Sabi no Mi (Rust-Rust Fruit)",
            "ability": "You rust and corrode any metal you touch — weapons, armor, and machinery decay on contact.",
            "awakening_1": "Rust spreads from your touch without sustained contact, propagating through metal structures rapidly.",
            "awakening_2": "You emit a corrosive aura — all metal within range begins to rust and crumble whether you touch it or not.",
        },
        {
            "name": "Shari Shari no Mi (Wheel-Wheel Fruit)",
            "ability": "Your arms and legs transform into high-speed spinning wheels, granting momentum-based attacks and rapid travel.",
            "awakening_1": "You generate spinning fields around your body, deflecting attacks and shredding enemies who close in.",
            "awakening_2": "Your rotation accelerates to cyclone speeds, tearing apart terrain and launching spinning projectile discs.",
        },
        {
            "name": "Horo Horo no Mi (Hollow-Hollow Fruit)",
            "ability": "You create ghosts that pass through bodies and inflict despair — sapping victims of 10% of their will to fight.",
            "awakening_1": "Your ghosts multiply rapidly and track targets relentlessly — cumulative despair stacks with each passing.",
            "awakening_2": "You split your own soul outward, creating a massive Negative Hollow capable of breaking entire armies in a single pass.",
        },
        {
            "name": "Yomi Yomi no Mi (Revive-Revive Fruit)",
            "ability": "Your soul returns from the dead once — granting you a second life and the power to project your soul from your body.",
            "awakening_1": "You cool your soul to absolute zero, releasing a freezing aura that crystallizes everything around you.",
            "awakening_2": "You unleash your full soul in an invisible giant form, traversing walls and striking enemies who cannot perceive or defend against you.",
        },
        {
            "name": "Kage Kage no Mi (Shadow-Shadow Fruit)",
            "ability": "You manipulate shadows — stealing them, inserting them into corpses to create zombie soldiers, or wielding your own as a weapon.",
            "awakening_1": "Your shadow constructs grow larger and respond instantly to your will, acting as autonomous bodyguards.",
            "awakening_2": "You absorb hundreds of shadows into yourself, becoming a titan of darkness with compounded strength of all those within.",
        },
        {
            "name": "Nikyu Nikyu no Mi (Paw-Paw Fruit)",
            "ability": "Your palms repel anything at the speed of light — pain, attacks, people, air itself. You can also push out someone's memories or fatigue.",
            "awakening_1": "You create repulsion fields that passively deflect incoming attacks, requiring no deliberate motion.",
            "awakening_2": "You launch compressed air bubbles of repelled force as long-range instant-speed projectiles — Ursus Shock at will.",
        },
        {
            "name": "Mero Mero no Mi (Love-Love Fruit)",
            "ability": "Anyone who feels attraction toward you is turned to stone. You can project love energy as weapons.",
            "awakening_1": "Your petrification range expands and the threshold of attraction lowers — even mild admiration triggers the effect.",
            "awakening_2": "You radiate a passive love aura — any who look upon you risk petrification, making visual contact itself a weapon.",
        },
        {
            "name": "Doku Doku no Mi (Venom-Venom Fruit)",
            "ability": "You generate and control the most lethal poisons imaginable — contact, airborne, or as corrosive liquid venom.",
            "awakening_1": "Your venom becomes self-replenishing and coats your entire body as permanent armor that melts anything touching you.",
            "awakening_2": "You transform fully into a giant venom hydra, unleashing torrents of poison capable of dissolving entire warships.",
        },
        {
            "name": "Gura Gura no Mi (Quake-Quake Fruit)",
            "ability": "You create devastating shockwaves capable of splitting the sea, shattering landscapes, and generating tsunamis.",
            "awakening_1": "You sustain shockwave fields rather than single pulses — terrain warps continuously around you.",
            "awakening_2": "You crack the sky itself — your quakes propagate through the atmosphere, targeting any location within visual range.",
        },
        {
            "name": "Ope Ope no Mi (Op-Op Fruit)",
            "ability": "You create a Room — a spherical operating field in which you have absolute control over space, matter, and bodies within it.",
            "awakening_1": "Your Room expands dramatically and costs less focus to maintain. You operate on multiple targets simultaneously.",
            "awakening_2": "You can perform the Immortality Operation — granting another eternal life — and extend your Room to engulf entire islands. KROOM radiates freely.",
        },
        {
            "name": "Hobi Hobi no Mi (Hobby-Hobby Fruit)",
            "ability": "You turn people into toys and erase their existence from others' memories. Toys are bound to obey your contract.",
            "awakening_1": "Your transformation is instantaneous and your memory erasure becomes area-wide rather than individual.",
            "awakening_2": "You can transform abstract concepts and inanimate structures into bound servants and rewrite their purpose entirely.",
        },
        {
            "name": "Buki Buki no Mi (Arm-Arm Fruit)",
            "ability": "You transform any body part into any weapon — blades, guns, cannons, shields — interchangeable at will.",
            "awakening_1": "You weaponize at larger scale and with greater complexity — detachable missile limbs, rotating cannon arrays.",
            "awakening_2": "Your entire body becomes a walking warship, with simultaneous multi-directional weapons of overwhelming firepower.",
        },
        {
            "name": "Guru Guru no Mi (Spin-Spin Fruit)",
            "ability": "You spin any body part at incredible speed — generating propulsion, wind, and centrifugal strikes.",
            "awakening_1": "You generate a persistent spinning force field that deflects projectiles and churns the air into cutting vortices.",
            "awakening_2": "Your spin reaches supersonic speed, creating a localized tornado that you direct with precision.",
        },
        {
            "name": "Beta Beta no Mi (Stick-Stick Fruit)",
            "ability": "You secrete an incredibly sticky mucus from your body that traps anything it contacts.",
            "awakening_1": "You launch sticky projectiles at range and create adhesive fields that catch attacks and immobilize enemies.",
            "awakening_2": "Your mucus becomes near-unbreakable — even Haki-coated strikes struggle to pull free once caught.",
        },
        {
            "name": "Bari Bari no Mi (Barrier-Barrier Fruit)",
            "ability": "You generate indestructible barriers — walls, shields, or bubbles — capable of deflecting any attack.",
            "awakening_1": "Your barriers form faster, cover wider areas, and can be shaped into offensive rams or crushing cages.",
            "awakening_2": "You surround yourself in a perpetual omnidirectional barrier field, negating damage from all directions simultaneously.",
        },
        {
            "name": "Nui Nui no Mi (Stitch-Stitch Fruit)",
            "ability": "You stitch things together — people to the ground, wounds, joints, even air — using invisible seams.",
            "awakening_1": "Your stitches propagate across surfaces — a single touch stitches an enemy's entire body into place.",
            "awakening_2": "You stitch together reality itself — binding spatial regions together, preventing movement through an area entirely.",
        },
        {
            "name": "Giro Giro no Mi (Glare-Glare Fruit)",
            "ability": "You see through everything — walls, disguises, Haki — and can project illusions directly into others' minds.",
            "awakening_1": "You broadcast visions to multiple targets simultaneously, creating mass illusions indistinguishable from reality.",
            "awakening_2": "You read the subconscious — seeing intent before it forms, effectively granting perfect prediction of all actions.",
        },
        {
            "name": "Ito Ito no Mi (String-String Fruit)",
            "ability": "You generate razor-sharp strings strong enough to slice steel and bind anything, including controlling people like puppets.",
            "awakening_1": "You extend strings across vast distances and create Birdcage — a self-shrinking dome of indestructible string.",
            "awakening_2": "Your strings become microscopic and permeate the air — everything within range is puppeted without visible attachment.",
        },
        {
            "name": "Mochi Mochi no Mi (Mochi-Mochi Fruit)",
            "ability": "You generate and control mochi — sticky, pliable, and overwhelming in mass, reshaping your body and trapping foes.",
            "awakening_1": "Your mochi hardens to iron density on command, alternating between trapping and crushing with ease.",
            "awakening_2": "You produce mochi at massive scale — flooding areas, building titans of mochi, and launching high-speed projectile rounds.",
        },
    ],

    # -----------------------------------------------------------------------
    "Zoan": [
        {
            "name": "Ushi Ushi no Mi, Model: Giraffe (Ox-Ox Fruit, Giraffe)",
            "ability": "You transform into a giraffe or giraffe-human hybrid, granting enormous reach, leg-kick power, and a long neck for striking.",
            "awakening_1": "Your hybrid form becomes denser and faster — your neck delivers pile-driver strikes at unexpected angles.",
            "awakening_2": "Your awakening unlocks a battle-hardened muscular giraffe titan form with full Rokushiki mastery integrated.",
        },
        {
            "name": "Inu Inu no Mi, Model: Wolf (Dog-Dog Fruit, Wolf)",
            "ability": "You transform into a massive wolf or hybrid, with extraordinary speed, tracking senses, and pack-hunting instincts.",
            "awakening_1": "Your speed surpasses most swordsmen and your bite force is enough to crush stone pillars.",
            "awakening_2": "You call upon primal wolf instinct — your reflexes become subconscious, reacting before conscious thought.",
        },
        {
            "name": "Neko Neko no Mi, Model: Leopard (Cat-Cat Fruit, Leopard)",
            "ability": "You transform into a leopard or hybrid — the peak of Zoan combat ability, combining speed, agility, and raw power.",
            "awakening_1": "Your hybrid is nearly indistinguishable from a wild leopard in instinct, but with human-level tactical thought.",
            "awakening_2": "You achieve a fully mastered awakened Zoan state — your physical stats surpass nearly every non-Legendary fruit user.",
        },
        {
            "name": "Tori Tori no Mi, Model: Falcon (Bird-Bird Fruit, Falcon)",
            "ability": "You transform into a falcon — gaining precise flight, keen eyesight, and razor-sharp talon strikes.",
            "awakening_1": "Your falcon form reaches speeds rivaling cannon fire and your eyesight extends to near-supernatural range.",
            "awakening_2": "You dive-bomb with force that creates shockwaves upon impact, combining aerial mobility with catastrophic ground strikes.",
        },
        {
            "name": "Mogu Mogu no Mi (Mole-Mole Fruit)",
            "ability": "You transform into a mole or hybrid — able to burrow through stone and earth at high speed.",
            "awakening_1": "Your burrowing creates destabilizing tunnels beneath enemies' feet and lets you launch surprise attacks from below.",
            "awakening_2": "You tunnel through reinforced structures instantly and create underground networks for rapid repositioning mid-battle.",
        },
        {
            "name": "Kame Kame no Mi (Turtle-Turtle Fruit)",
            "ability": "You transform into a massive sea turtle with near-impenetrable shell defense and powerful crushing bites.",
            "awakening_1": "Your shell absorbs and redistributes kinetic force — strikes sent against you return at the attacker.",
            "awakening_2": "You retract fully and become a mobile fortress — channeling absorbed energy into a devastating release strike.",
        },
        {
            "name": "Batto Batto no Mi, Model: Vampire (Bat-Bat Fruit, Vampire)",
            "ability": "You transform into a vampire bat hybrid — flight, echolocation, and the ability to drain the energy of those you bite.",
            "awakening_1": "Your energy drain now passes through guards — Haki resistance only slows, not stops, the drain.",
            "awakening_2": "You command a swarm of bat extensions from your form, draining multiple targets simultaneously across the field.",
        },
    ],

    # -----------------------------------------------------------------------
    "Logia": [
        {
            "name": "Moku Moku no Mi (Smoke-Smoke Fruit)",
            "ability": "You transform into smoke — passing through attacks, obscuring vision, and suffocating foes in dense clouds.",
            "awakening_1": "Your smoke reaches near-poisonous density and you expand your cloud to cover an entire battlefield.",
            "awakening_2": "You create a permanent smoke dome — negating all visibility for enemies while you navigate it perfectly.",
        },
        {
            "name": "Suna Suna no Mi (Sand-Sand Fruit)",
            "ability": "You become desert sand — dehydrating anything you touch into dust, creating massive sandstorms, and sinking terrain.",
            "awakening_1": "Your sand absorbs moisture from the air itself, expanding your dehydration range beyond touch.",
            "awakening_2": "You summon a desert cataclysm — endless sand drawn from the earth itself, burying entire regions.",
        },
        {
            "name": "Mera Mera no Mi (Flame-Flame Fruit)",
            "ability": "You become fire — generating, controlling, and launching immense flames. You are immune to heat and burn.",
            "awakening_1": "Your fire burns hot enough to melt sea stone and you can sustain continent-wide fire pillars.",
            "awakening_2": "You achieve Flame Emperor level — your fire takes on solar properties, burning even in the absence of oxygen.",
        },
        {
            "name": "Goro Goro no Mi (Rumble-Rumble Fruit)",
            "ability": "You become lightning — moving at the speed of light, electrocuting foes, and calling down bolts from the sky.",
            "awakening_1": "You sustain electrical fields and can magnetize targets, drawing your lightning strikes unerringly.",
            "awakening_2": "You become an electromagnetic storm — generating EMP bursts, magnetizing terrain, and striking simultaneously across wide areas.",
        },
        {
            "name": "Hie Hie no Mi (Ice-Ice Fruit)",
            "ability": "You become ice — freezing anything you touch or exhale and reshaping terrain into glaciers.",
            "awakening_1": "Your freezing propagates through the ground — you can flash-freeze entire ocean surfaces and large enclosed spaces.",
            "awakening_2": "You lower ambient temperature to absolute zero in your vicinity — all liquids and gases around you crystallize instantly.",
        },
        {
            "name": "Yami Yami no Mi (Dark-Dark Fruit)",
            "ability": "You become darkness — nullifying other Devil Fruits on contact and creating black holes that crush and draw in everything.",
            "awakening_1": "Your darkness expands to engulf large areas, neutralizing multiple Devil Fruit users simultaneously.",
            "awakening_2": "You achieve a darkness singularity — a gravitational void that pulls in even Haki-coated attacks and compresses them.",
        },
        {
            "name": "Pika Pika no Mi (Glint-Glint Fruit)",
            "ability": "You become light — moving at absolute light speed, reflecting off surfaces, and launching blinding laser beams.",
            "awakening_1": "Your lasers now refract automatically, curving around obstacles and striking from impossible angles.",
            "awakening_2": "You unleash an Eight-Direction Flash — simultaneous laser strikes from all directions covering an island-wide radius.",
        },
        {
            "name": "Magu Magu no Mi (Magma-Magma Fruit)",
            "ability": "You become magma — the most destructive Logia, burning hotter than fire and capable of boiling entire seawater regions.",
            "awakening_1": "Your magma draws heat from the earth's core — unlimited fuel for sustained eruptions of continent-scale damage.",
            "awakening_2": "You become a supervolcano made flesh — triggering eruptions beneath enemy positions and launching magma meteors.",
        },
        {
            "name": "Numa Numa no Mi (Swamp-Swamp Fruit)",
            "ability": "You become a bottomless swamp — absorbing and storing anything that touches you, including cannonballs, and hurling them back.",
            "awakening_1": "Your swamp matter expands in range and you can launch stored objects with multiplied velocity.",
            "awakening_2": "You become an environmental hazard — turning ground into swamp terrain and pulling enemies under without warning.",
        },
        {
            "name": "Gasu Gasu no Mi (Gas-Gas Fruit)",
            "ability": "You become gas — forming explosive, poisonous, or suffocating atmospheres with total environmental control.",
            "awakening_1": "Your gas blends are more precise — you isolate specific gases to target weaknesses like oxygen deprivation or ignition.",
            "awakening_2": "You saturate an entire region's atmosphere — turning the sky itself into a weapon only you can safely breathe.",
        },
        {
            "name": "Yuki Yuki no Mi (Snow-Snow Fruit)",
            "ability": "You become snow — blizzard generation, shaping snow into weapons, and slowing all caught within your storms.",
            "awakening_1": "Your blizzards reach gale force, reducing visibility to zero and causing frostbite on contact with the air.",
            "awakening_2": "You generate a perpetual polar storm — lowering temperatures across an island and burying entire towns in minutes.",
        },
    ],

    # -----------------------------------------------------------------------
    "Ancient Zoan": [
        {
            "name": "Ryu Ryu no Mi, Model: Allosaurus (Dragon-Dragon Fruit, Allosaurus)",
            "ability": "You transform into a massive Allosaurus — one of the most powerful predators in history, with crushing bite force and relentless aggression.",
            "awakening_1": "Your Allosaurus form gains armored scaling and its charge becomes a seismic impact, cracking stone on contact.",
            "awakening_2": "You enter a berserker ancient state — your instincts take over and your combat capability exceeds all tactical analysis.",
        },
        {
            "name": "Ryu Ryu no Mi, Model: Spinosaurus (Dragon-Dragon Fruit, Spinosaurus)",
            "ability": "You transform into a Spinosaurus — enormous aquatic and land predator with sweeping claw attacks and tail devastation.",
            "awakening_1": "Your Spinosaurus form's sail radiates energy — your tail sweep generates massive shockwaves on impact.",
            "awakening_2": "You become an apex ancient beast with amphibious dominance — your size rivals small warships.",
        },
        {
            "name": "Ryu Ryu no Mi, Model: Pteranodon (Dragon-Dragon Fruit, Pteranodon)",
            "ability": "You transform into a Pteranodon — powerful aerial predator with sonic dive capabilities and razor-edged wing strikes.",
            "awakening_1": "Your dive speed reaches Mach levels, and your wingspan can level buildings on a full-speed pass.",
            "awakening_2": "You ride thermal currents at stratospheric height and dive with a sonic boom that flattens terrain below.",
        },
        {
            "name": "Ryu Ryu no Mi, Model: Brachiosaurus (Dragon-Dragon Fruit, Brachiosaurus)",
            "ability": "You transform into a Brachiosaurus — immovable, colossal, your sheer mass and long neck becoming devastating weapons.",
            "awakening_1": "Your neck lashes faster than it appears — a single full-speed strike levels fortified walls.",
            "awakening_2": "You become a living battering ram — no structure or defense can withstand your full-weight charge.",
        },
        {
            "name": "Zou Zou no Mi, Model: Mammoth (Elephant-Elephant Fruit, Mammoth)",
            "ability": "You transform into a colossal woolly mammoth — overwhelming brute force, impenetrable hide, and tusks that level landscapes.",
            "awakening_1": "Your mammoths freeze the ground with each step — your fur becomes thick enough to absorb explosive force.",
            "awakening_2": "You enter a primal stampede state — an unstoppable force that reshapes terrain with each passing.",
        },
        {
            "name": "Neko Neko no Mi, Model: Saber Tiger (Cat-Cat Fruit, Saber-Toothed Tiger)",
            "ability": "You transform into a saber-toothed tiger — explosive speed, prehistoric fang strength, and ambush mastery.",
            "awakening_1": "Your saber fangs can pierce anything short of the hardest sea stone. Your pounce covers fifty meters in an instant.",
            "awakening_2": "Your ancient predator instincts grant absolute battlefield awareness — no attack surprises you.",
        },
    ],

    # -----------------------------------------------------------------------
    "Mythical Zoan": [
        {
            "name": "Tori Tori no Mi, Model: Phoenix (Bird-Bird Fruit, Phoenix)",
            "ability": "You transform into a mythical phoenix — eternal blue flame regeneration heals any wound, and your fire burns the soul.",
            "awakening_1": "Your regeneration accelerates to near-instantaneous. Your blue flames now heal allies on contact while burning enemies.",
            "awakening_2": "You enter an undying state — your body cannot be destroyed while blue flames burn, and your resurrection aura revives fallen allies.",
        },
        {
            "name": "Inu Inu no Mi, Model: Kyubi no Kitsune (Dog-Dog Fruit, Nine-Tailed Fox)",
            "ability": "You transform into a nine-tailed fox — perfect shapeshifting into any person, and illusory fire that traps the mind.",
            "awakening_1": "Your illusions become multi-sensory — indistinguishable from reality even to Observation Haki users.",
            "awakening_2": "You project nine simultaneous tails as independent weapons while maintaining full human form and shapeshifting.",
        },
        {
            "name": "Hebi Hebi no Mi, Model: Yamata no Orochi (Snake-Snake Fruit, Eight-Headed Serpent)",
            "ability": "You transform into an eight-headed serpent — each head is independently conscious and nearly impossible to permanently kill.",
            "awakening_1": "Your heads regenerate within seconds of severing. Each head can act entirely independently in combat.",
            "awakening_2": "You grow to island scale — eight colossal heads striking simultaneously from all directions.",
        },
        {
            "name": "Uo Uo no Mi, Model: Seiryu (Fish-Fish Fruit, Azure Dragon)",
            "ability": "You transform into a colossal azure dragon — Flame Clouds, lightning breath, and size rivaling mountains.",
            "awakening_1": "Your Flame Clouds now lift entire islands. Your lightning breath carries the voltage of a thunderstorm.",
            "awakening_2": "You achieve Celestial Dragon ascension — a being of weather itself, calling storms, tidal waves, and divine lightning.",
        },
        {
            "name": "Hito Hito no Mi, Model: Daibutsu (Human-Human Fruit, Great Buddha)",
            "ability": "You transform into a massive golden Buddha — emitting golden shockwaves from every surface with overwhelming defensive bulk.",
            "awakening_1": "Your shockwaves propagate from the ground — rising pressure waves that knock down entire armies.",
            "awakening_2": "You achieve a temple-scale golden giant form — shockwaves radiate omnidirectionally with religious force.",
        },
        {
            "name": "Inu Inu no Mi, Model: Okuchi no Makami (Dog-Dog Fruit, Wolf Deity)",
            "ability": "You transform into the legendary guardian wolf deity — frost breath, divine speed, and a howl that paralyzes those who hear it.",
            "awakening_1": "Your frost reaches absolute zero instantly. Your howl carries Conqueror's Haki resonance, staggering even the strong-willed.",
            "awakening_2": "You manifest as a divine guardian — an aura of divine protection makes direct attacks wither before reaching you.",
        },
    ],

    # -----------------------------------------------------------------------
    "Legendary": [
        {
            "name": "Hito Hito no Mi, Model: Nika (Human-Human Fruit, Sun God Nika)",
            "ability": "The most ridiculous power in the world — your body becomes the freedom of rubber and the joy of the Sun God. Your imagination is your only limit.",
            "awakening_1": "Your Gear 5 ignites — white hair, white outfit, pure Nika energy. Your body warps reality playfully, yet with divine destructive power.",
            "awakening_2": "You are Nika fully manifest — the Drum of Liberation beats. The world's greatest power, the freest force in existence. None can cage you.",
        },
        {
            "name": "Gura Gura no Mi + Yami Yami no Mi (Dual Fruit — Blackbeard's Power)",
            "ability": "By defying the laws of nature, you wield both quake shockwaves and darkness simultaneously — nullifying other fruits while shattering the world.",
            "awakening_1": "Your darkness becomes a gravity singularity. Your quakes send shockwaves through the void, hitting targets beyond line of sight.",
            "awakening_2": "You collapse the two powers into one — a dark quake: a singularity that tears reality, impossible to defend against by conventional means.",
        },
        {
            "name": "Tama Tama no Mi (Egg-Egg Fruit — Mythical Evolution)",
            "ability": "You are an egg — impossible to permanently destroy. Each defeat hatches you into a stronger form with accumulated power.",
            "awakening_1": "Your hatching is now voluntary — you evolve mid-battle without needing to be defeated.",
            "awakening_2": "You become a perpetual evolution engine — battle-by-battle, you grow stronger with no upper ceiling.",
        },
        {
            "name": "Soku Soku no Mi (Speed-Speed Fruit — Legendary)",
            "ability": "A theoretical legendary fruit granting absolute speed — movement, thought, reaction, all at the speed of light simultaneously.",
            "awakening_1": "You perceive time at a crawl — to you, everything moves slowly. To others, you are simply invisible.",
            "awakening_2": "You break the causality barrier — your speed allows you to act before events occur, striking the future itself.",
        },
        {
            "name": "Conqueror's Embodiment — Will Made Manifest (Legendary Paramecia)",
            "ability": "Your Devil Fruit is born from your own Conqueror's Haki crystallized into a fruit — you manifest your will as physical force, shaping reality through sheer dominance.",
            "awakening_1": "Your will radiates as a visible aura — Conqueror's Haki coats your every attack without conscious effort.",
            "awakening_2": "Your will becomes indistinguishable from divine law — in your presence, weaker wills simply cease to resist.",
        },
    ],
}
