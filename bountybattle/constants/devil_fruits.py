# constants/devil_fruits.py

# Devil Fruit definitions
DEVIL_FRUITS = {
    "Common": {
        # Paramecia Fruits
        "Gomu Gomu no Mi": {"type": "Paramecia", "effect": "rubber", "bonus": "Immune to blunt attacks"},
        "Bomu Bomu no Mi": {"type": "Paramecia", "effect": "explosion", "bonus": "Explosive attacks deal 30% extra damage"},
        "Kilo Kilo no Mi": {"type": "Paramecia", "effect": "weight", "bonus": "Increase or decrease weight to avoid attacks"},
        "Toge Toge no Mi": {"type": "Paramecia", "effect": "spikes", "bonus": "Counter melee attacks with spike damage"},
        "Bane Bane no Mi": {"type": "Paramecia", "effect": "springs", "bonus": "Jump twice as far and attack with spring force"},
        "Hana Hana no Mi": {"type": "Paramecia", "effect": "multiple limbs", "bonus": "Can attack or defend from any direction"},
        "Doru Doru no Mi": {"type": "Paramecia", "effect": "wax", "bonus": "Create shields and weapons from hard wax"},
        "Supa Supa no Mi": {"type": "Paramecia", "effect": "blades", "bonus": "Body turns into blades, increasing melee damage"},
        "Baku Baku no Mi": {"type": "Paramecia", "effect": "eat anything", "bonus": "Can consume and copy enemy weapons"},
        "Mane Mane no Mi": {"type": "Paramecia", "effect": "copy", "bonus": "Can mimic an enemy's attack once per battle"},
        "Goe Goe no Mi": {"type": "Paramecia", "effect": "sound waves", "bonus": "Launch powerful sound-based attacks"},
        "Ori Ori no Mi": {"type": "Paramecia", "effect": "binding", "bonus": "Can trap enemies in iron restraints"},
        "Shari Shari no Mi": {"type": "Paramecia", "effect": "wheels", "bonus": "Can turn limbs into spinning wheels for attacks"},
        "Awa Awa no Mi": {"type": "Paramecia", "effect": "bubbles", "bonus": "Reduces enemy defense with cleansing bubbles"},
        "Noro Noro no Mi": {"type": "Paramecia", "effect": "slow beam", "bonus": "Temporarily slows down enemies"},
        "Giro Giro no Mi": {"type": "Paramecia", "effect": "x-ray", "bonus": "Can read enemy attacks before they strike"},
        "Tama Tama no Mi": {"type": "Paramecia", "effect": "egg", "bonus": "Can harden body like a shell once per battle"},
        "Ato Ato no Mi": {"type": "Paramecia", "effect": "art", "bonus": "Can slow down an opponent by turning them into a painting"},
        "Nemu Nemu no Mi": {"type": "Paramecia", "effect": "sleep", "bonus": "Chance to put an opponent to sleep for 1 turn"},
        "Hiso Hiso no Mi": {"type": "Paramecia", "effect": "whisper", "bonus": "Can communicate with animals"},
        "Samu Samu no Mi": {"type": "Paramecia", "effect": "cold body", "bonus": "Slight resistance to ice attacks"},
        "Ashi Ashi no Mi": {"type": "Paramecia", "effect": "feet", "bonus": "Movement speed increased by 15%"},
        "Beta Beta no Mi": {"type": "Paramecia", "effect": "sticky", "bonus": "Can slow down enemy movement"},
        "Jiki Jiki no Mi": {"type": "Paramecia", "effect": "magnetism", "bonus": "Can attract and repel small metal objects"},
        "Mitsu Mitsu no Mi": {"type": "Paramecia", "effect": "honey", "bonus": "Can trap opponents in sticky honey"},
        "Taru Taru no Mi": {"type": "Paramecia", "effect": "liquid body", "bonus": "Takes reduced damage from physical attacks"},

        # Regular Zoans
        "Neko Neko no Mi: Model Leopard": {"type": "Zoan", "effect": "leopard", "bonus": "20% increased speed and agility"},
        "Tori Tori no Mi: Model Falcon": {"type": "Zoan", "effect": "falcon", "bonus": "Enhanced aerial mobility"},
        "Mushi Mushi no Mi: Model Hornet": {"type": "Zoan", "effect": "hornet", "bonus": "Can fly and sting enemies"},
        "Zou Zou no Mi": {"type": "Zoan", "effect": "elephant", "bonus": "Increased strength and durability"},
        "Uma Uma no Mi": {"type": "Zoan", "effect": "horse", "bonus": "Enhanced speed on land"},
        "Kame Kame no Mi": {"type": "Zoan", "effect": "turtle", "bonus": "Enhanced defense and swimming ability"},

        # SMILE Fruits
        "Alpaca SMILE": {"type": "Zoan", "effect": "alpaca features", "bonus": "Gains alpaca traits"},
        "Armadillo SMILE": {"type": "Zoan", "effect": "armadillo features", "bonus": "Can roll into a ball for defense"},
        "Bat SMILE": {"type": "Zoan", "effect": "bat features", "bonus": "Limited flight capability"},
        "Elephant SMILE": {"type": "Zoan", "effect": "elephant features", "bonus": "Trunk-based attacks"},
        "Chicken SMILE": {"type": "Zoan", "effect": "chicken features", "bonus": "Can glide short distances"},
        "Flying Squirrel SMILE": {"type": "Zoan", "effect": "flying squirrel features", "bonus": "Gliding ability"}
    },
    "Rare": {
        # Logia Fruits
        "Yami Yami no Mi": {"type": "Logia", "effect": "darkness", "bonus": "Can absorb 15% of the opponent's attack damage as HP"},
        "Hie Hie no Mi": {"type": "Logia", "effect": "ice", "bonus": "Can freeze an opponent, skipping their next turn"},
        "Mera Mera no Mi": {"type": "Logia", "effect": "fire", "bonus": "Fire attacks do double damage"},
        "Suna Suna no Mi": {"type": "Logia", "effect": "sand", "bonus": "10% chance to drain enemy's HP"},
        "Gasu Gasu no Mi": {"type": "Logia", "effect": "gas", "bonus": "Can poison enemies with toxic gas"},
        "Pika Pika no Mi": {"type": "Logia", "effect": "light", "bonus": "Moves first in every battle"},
        "Magu Magu no Mi": {"type": "Logia", "effect": "magma", "bonus": "Deals additional burn damage over time"},
        "Mori Mori no Mi": {"type": "Logia", "effect": "forest", "bonus": "Can summon roots to immobilize opponents"},
        "Kaze Kaze no Mi": {"type": "Logia", "effect": "wind", "bonus": "Has a 20% chance to dodge any attack"},
        "Goro Goro no Mi": {"type": "Logia", "effect": "lightning", "bonus": "Lightning attacks have chance to paralyze"},
        "Moku Moku no Mi": {"type": "Logia", "effect": "smoke", "bonus": "Can become intangible at will"},
        "Yuki Yuki no Mi": {"type": "Logia", "effect": "snow", "bonus": "Can freeze and control battlefield"},
        "Numa Numa no Mi": {"type": "Logia", "effect": "swamp", "bonus": "Can create quicksand traps"},

        # Mythical Zoans
        "Tori Tori no Mi: Model Phoenix": {"type": "Mythical Zoan", "effect": "phoenix", "bonus": "Heals 10% HP every 3 turns"},
        "Tori Tori no Mi: Model Thunderbird": {"type": "Mythical Zoan", "effect": "thunderbird", "bonus": "Lightning attacks deal extra damage"},
        "Uo Uo no Mi: Model Seiryu": {"type": "Mythical Zoan", "effect": "azure dragon", "bonus": "30% stronger attacks in battles"},
        "Hito Hito no Mi: Model Nika": {"type": "Mythical Zoan", "effect": "nika", "bonus": "Randomly boosts attack, speed, or defense"},
        "Hito Hito no Mi: Model Daibutsu": {"type": "Mythical Zoan", "effect": "giant buddha", "bonus": "Boosts defense and attack power"},
        "Hito Hito no Mi: Model Onyudo": {"type": "Mythical Zoan", "effect": "monk", "bonus": "Can grow to massive sizes"},
        "Inu Inu no Mi: Model Cerberus": {"type": "Mythical Zoan", "effect": "cerberus", "bonus": "Can attack twice per turn"},
        "Inu Inu no Mi: Model Okuchi no Makami": {"type": "Mythical Zoan", "effect": "wolf deity", "bonus": "Healing abilities are doubled"},
        "Hebi Hebi no Mi: Model Yamata no Orochi": {"type": "Mythical Zoan", "effect": "orochi", "bonus": "Gain 2 extra attacks every 3 turns"},
        "Uma Uma no Mi: Model Pegasus": {"type": "Mythical Zoan", "effect": "pegasus", "bonus": "Flight and enhanced speed"},

        # Ancient Zoans
        "Ryu Ryu no Mi: Model Spinosaurus": {"type": "Ancient Zoan", "effect": "spinosaurus", "bonus": "Increase HP by 20%"},
        "Ryu Ryu no Mi: Model Pteranodon": {"type": "Ancient Zoan", "effect": "pteranodon", "bonus": "Gain a 15% chance to evade attacks"},
        "Ryu Ryu no Mi: Model Allosaurus": {"type": "Ancient Zoan", "effect": "allosaurus", "bonus": "Increase attack damage by 25%"},
        "Ryu Ryu no Mi: Model Brachiosaurus": {"type": "Ancient Zoan", "effect": "brachiosaurus", "bonus": "Massive strength increase"},
        "Ryu Ryu no Mi: Model Pachycephalosaurus": {"type": "Ancient Zoan", "effect": "pachycephalosaurus", "bonus": "Powerful headbutt attacks"},
        "Ryu Ryu no Mi: Model Triceratops": {"type": "Ancient Zoan", "effect": "triceratops", "bonus": "Enhanced charging attacks"},
        "Kumo Kumo no Mi: Model Rosamygale Grauvogeli": {"type": "Ancient Zoan", "effect": "ancient spider", "bonus": "Web attacks slow enemies"},
        
        # Special & Powerful Paramecia
        "Mochi Mochi no Mi": {"type": "Special Paramecia", "effect": "mochi", "bonus": "Can dodge one attack every 4 turns"},
        "Gura Gura no Mi": {"type": "Paramecia", "effect": "quake", "bonus": "Earthquake attack deals massive AoE damage"},
        "Zushi Zushi no Mi": {"type": "Paramecia", "effect": "gravity", "bonus": "20% chance to stun an enemy every turn"},
        "Toki Toki no Mi": {"type": "Paramecia", "effect": "time", "bonus": "Can speed up cooldowns for abilities"},
        "Ope Ope no Mi": {"type": "Paramecia", "effect": "surgical", "bonus": "Complete control within operation room"},
        "Gold Gold no Mi": {"type": "Paramecia", "effect": "gold", "bonus": "Can create and control gold"},
        "More More no Mi": {"type": "Paramecia", "effect": "multiplication", "bonus": "Can multiply objects and attacks"},
        "Luck Luck no Mi": {"type": "Paramecia", "effect": "fortune", "bonus": "Increases chance of critical hits"},
        "Through Through no Mi": {"type": "Paramecia", "effect": "phasing", "bonus": "Can pass through solid objects"},
        "Return Return no Mi": {"type": "Paramecia", "effect": "reversal", "bonus": "Can return attacks to sender"},
        "Soru Soru no Mi": {"type": "Paramecia", "effect": "soul manipulation", "bonus": "Can steal and manipulate life force"},
        "Bari Bari no Mi": {"type": "Paramecia", "effect": "barrier", "bonus": "Block 40% of incoming melee damage"},
        "Doku Doku no Mi": {"type": "Paramecia", "effect": "poison", "bonus": "Deals poison damage over time"},
        "Hobi Hobi no Mi": {"type": "Paramecia", "effect": "toy conversion", "bonus": "Can erase people from memories"},
        "Kira Kira no Mi": {"type": "Paramecia", "effect": "diamond", "bonus": "Defense increases by 30%"},
        "Ito Ito no Mi": {"type": "Paramecia", "effect": "string control", "bonus": "Can control people and create clones"}
    }
}
