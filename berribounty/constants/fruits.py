"""Devil fruit definitions for the One Piece bot."""

DEVIL_FRUITS = {
    "common": {
        "Smoke-Smoke Fruit": {
            "type": "Logia",
            "description": "Allows the user to create, control, and transform into smoke",
            "abilities": [
                "Smoke transformation",
                "Smoke manipulation",
                "Flight via smoke"
            ],
            "moves": [
                {
                    "name": "Smoke Screen",
                    "description": "Create a cloud of smoke to confuse enemies",
                    "damage": 20,
                    "mp_cost": 15,
                    "cooldown": 2,
                    "effects": [{"type": "blind", "duration": 2}]
                },
                {
                    "name": "Smoke Burst",
                    "description": "Explosive burst of smoke",
                    "damage": 35,
                    "mp_cost": 25,
                    "cooldown": 3
                }
            ],
            "weaknesses": ["Water", "Sea stone", "Strong winds"]
        },
        "Rubber-Rubber Fruit": {
            "type": "Paramecia",
            "description": "Grants the user's body the properties of rubber",
            "abilities": [
                "Immunity to blunt attacks",
                "Stretching limbs",
                "Electricity resistance"
            ],
            "moves": [
                {
                    "name": "Gum-Gum Pistol",
                    "description": "Stretch arm to punch distant enemies",
                    "damage": 30,
                    "mp_cost": 10,
                    "cooldown": 1
                },
                {
                    "name": "Gum-Gum Bazooka",
                    "description": "Double-handed stretching attack",
                    "damage": 50,
                    "mp_cost": 20,
                    "cooldown": 3
                }
            ],
            "weaknesses": ["Cutting attacks", "Sea stone", "Sharp objects"]
        },
        "Chop-Chop Fruit": {
            "type": "Paramecia",
            "description": "Allows the user to split their body into parts",
            "abilities": [
                "Body separation",
                "Immunity to cutting attacks",
                "Flying body parts"
            ],
            "moves": [
                {
                    "name": "Chop-Chop Cannon",
                    "description": "Launch separated hand as projectile",
                    "damage": 25,
                    "mp_cost": 15,
                    "cooldown": 2
                },
                {
                    "name": "Chop-Chop Festival",
                    "description": "Separate into many pieces for chaos",
                    "damage": 40,
                    "mp_cost": 30,
                    "cooldown": 4,
                    "effects": [{"type": "confuse", "duration": 3}]
                }
            ],
            "weaknesses": ["Feet (cannot be separated)", "Sea stone"]
        },
        "Slip-Slip Fruit": {
            "type": "Paramecia",
            "description": "Makes the user's skin smooth, causing attacks to slip off",
            "abilities": [
                "Smooth skin",
                "Attack deflection",
                "Enhanced beauty"
            ],
            "moves": [
                {
                    "name": "Smooth Reflection",
                    "description": "Deflect attacks back at enemy",
                    "damage": 0,
                    "mp_cost": 20,
                    "cooldown": 4,
                    "effects": [{"type": "reflect", "duration": 1}]
                }
            ],
            "weaknesses": ["Sea stone", "Non-physical attacks"]
        }
    },
    "rare": {
        "Fire-Fire Fruit": {
            "type": "Logia",
            "description": "Allows the user to create, control, and transform into fire",
            "abilities": [
                "Fire transformation",
                "Fire manipulation",
                "Heat generation",
                "Fire immunity"
            ],
            "moves": [
                {
                    "name": "Fire Fist",
                    "description": "Launch a fist-shaped fire projectile",
                    "damage": 60,
                    "mp_cost": 25,
                    "cooldown": 2
               },
               {
                   "name": "Flame Spear",
                   "description": "Create spears of fire to attack",
                   "damage": 45,
                   "mp_cost": 20,
                   "cooldown": 2
               },
               {
                   "name": "Great Flame Commandment",
                   "description": "Massive fire attack",
                   "damage": 100,
                   "mp_cost": 50,
                   "cooldown": 6,
                   "effects": [{"type": "burn", "duration": 3, "damage": 10}]
               }
           ],
           "weaknesses": ["Magma", "Sea stone", "Water (to some extent)"]
       },
       "Ice-Ice Fruit": {
           "type": "Logia",
           "description": "Allows the user to create, control, and transform into ice",
           "abilities": [
               "Ice transformation",
               "Ice manipulation",
               "Freezing attacks",
               "Cold immunity"
           ],
           "moves": [
               {
                   "name": "Ice Saber",
                   "description": "Create a sword of ice",
                   "damage": 50,
                   "mp_cost": 20,
                   "cooldown": 2
               },
               {
                   "name": "Ice Age",
                   "description": "Freeze a large area",
                   "damage": 70,
                   "mp_cost": 40,
                   "cooldown": 5,
                   "effects": [{"type": "freeze", "duration": 2}]
               },
               {
                   "name": "Absolute Zero",
                   "description": "Ultimate freezing attack",
                   "damage": 120,
                   "mp_cost": 60,
                   "cooldown": 8,
                   "effects": [{"type": "freeze", "duration": 4}]
               }
           ],
           "weaknesses": ["Fire", "Heat", "Sea stone"]
       },
       "Dark-Dark Fruit": {
           "type": "Logia",
           "description": "Grants the power of darkness with unique properties",
           "abilities": [
               "Darkness manipulation",
               "Gravitational pull",
               "Ability absorption",
               "Cannot transform into darkness"
           ],
           "moves": [
               {
                   "name": "Dark Water",
                   "description": "Pull enemies with darkness",
                   "damage": 40,
                   "mp_cost": 25,
                   "cooldown": 3,
                   "effects": [{"type": "pull", "duration": 1}]
               },
               {
                   "name": "Black Hole",
                   "description": "Create a gravitational void",
                   "damage": 80,
                   "mp_cost": 45,
                   "cooldown": 6,
                   "effects": [{"type": "absorb", "duration": 2}]
               },
               {
                   "name": "Liberation",
                   "description": "Release absorbed attacks",
                   "damage": 100,
                   "mp_cost": 50,
                   "cooldown": 7
               }
           ],
           "weaknesses": ["Light attacks", "Takes double damage", "Sea stone"]
       },
       "Light-Light Fruit": {
           "type": "Logia",
           "description": "Allows the user to create, control, and transform into light",
           "abilities": [
               "Light transformation",
               "Light-speed movement",
               "Laser attacks",
               "Light manipulation"
           ],
           "moves": [
               {
                   "name": "Light Speed Kick",
                   "description": "Kick at the speed of light",
                   "damage": 55,
                   "mp_cost": 25,
                   "cooldown": 2
               },
               {
                   "name": "Laser Beam",
                   "description": "Fire concentrated light beam",
                   "damage": 65,
                   "mp_cost": 30,
                   "cooldown": 3
               },
               {
                   "name": "Eight-Span Mirror",
                   "description": "Reflect and multiply light attacks",
                   "damage": 90,
                   "mp_cost": 50,
                   "cooldown": 6
               }
           ],
           "weaknesses": ["Darkness", "Mirrors", "Sea stone"]
       },
       "Tremor-Tremor Fruit": {
           "type": "Paramecia",
           "description": "Allows the user to create earthquakes and tremors",
           "abilities": [
               "Earthquake generation",
               "Shockwave attacks",
               "Environmental destruction",
               "Tsunami creation"
           ],
           "moves": [
               {
                   "name": "Tremor Punch",
                   "description": "Punch that creates shockwaves",
                   "damage": 70,
                   "mp_cost": 30,
                   "cooldown": 3
               },
               {
                   "name": "Seaquake",
                   "description": "Create tremors in the ground",
                   "damage": 85,
                   "mp_cost": 40,
                   "cooldown": 5,
                   "effects": [{"type": "stun", "duration": 2}]
               },
               {
                   "name": "World's Strongest Man",
                   "description": "Ultimate earthquake attack",
                   "damage": 150,
                   "mp_cost": 80,
                   "cooldown": 10,
                   "effects": [{"type": "devastation", "duration": 1}]
               }
           ],
           "weaknesses": ["Sea stone", "Physical strain on user"]
       },
       "Phoenix-Phoenix Fruit": {
           "type": "Mythical Zoan",
           "description": "Allows transformation into a phoenix with regenerative flames",
           "abilities": [
               "Phoenix transformation",
               "Regenerative flames",
               "Flight",
               "Resurrection"
           ],
           "moves": [
               {
                   "name": "Phoenix Brand",
                   "description": "Attack with healing flames",
                   "damage": 50,
                   "mp_cost": 25,
                   "cooldown": 3,
                   "effects": [{"type": "heal", "amount": 20}]
               },
               {
                   "name": "Blue Flames",
                   "description": "Unleash regenerative fire",
                   "damage": 40,
                   "mp_cost": 30,
                   "cooldown": 4,
                   "effects": [{"type": "regen", "duration": 3, "amount": 15}]
               },
               {
                   "name": "Phoenix Rising",
                   "description": "Full phoenix transformation",
                   "damage": 80,
                   "mp_cost": 60,
                   "cooldown": 8,
                   "effects": [{"type": "revive", "duration": 1}]
               }
           ],
           "weaknesses": ["Sea stone", "Water", "Extreme cold"]
       }
   }
}