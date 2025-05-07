# Impel Down levels and their descriptions
IMPEL_DOWN_LEVELS = {
    1: {
        "name": "Crimson Hell",
        "description": "A forest of red trees with blade-like leaves. Minor offenders are kept here.",
        "default_duration": 10,  # Default duration in minutes
        "restrictions": ["send_messages", "add_reactions"]
    },
    2: {
        "name": "Wild Beast Hell",
        "description": "Home to various wild beasts that guard prisoners. Slightly more dangerous offenders are kept here.",
        "default_duration": 30,  # Default duration in minutes
        "restrictions": ["send_messages", "add_reactions", "speak"]
    },
    3: {
        "name": "Starvation Hell",
        "description": "Prisoners are kept without food, waiting in despair. Serious offenders are imprisoned here.",
        "default_duration": 60,  # Default duration in minutes
        "restrictions": ["send_messages", "add_reactions", "speak", "view_channel"]
    },
    4: {
        "name": "Burning Hell",
        "description": "An extremely hot level where prisoners suffer from the intense heat. Major offenders are kept here.",
        "default_duration": 120,  # Default duration in minutes
        "restrictions": ["send_messages", "add_reactions", "speak", "view_channel"]
    },
    5: {
        "name": "Freezing Hell",
        "description": "An extremely cold level where prisoners are kept in freezing temperatures. Highly dangerous criminals are held here.",
        "default_duration": 240,  # Default duration in minutes
        "restrictions": ["send_messages", "add_reactions", "speak", "view_channel"]
    },
    6: {
        "name": "Eternal Hell",
        "description": "The final and most secure level of Impel Down. The most dangerous criminals in the world are kept here for life.",
        "default_duration": 720,  # Default duration in minutes
        "restrictions": ["send_messages", "add_reactions", "speak", "view_channel"]
    }
}

# Impel Down messages by level
IMPEL_DOWN_MESSAGES = {
    1: [
        "{user} has been sent to Impel Down Level 1: Crimson Hell by {mod} for {time} minutes!",
        "Warden {mod} has imprisoned {user} in Level 1 of Impel Down for {time} minutes!",
        "{user} has been sentenced to {time} minutes in Level 1: Crimson Hell by {mod}!"
    ],
    2: [
        "{user} has been thrown into Impel Down Level 2: Wild Beast Hell by {mod} for {time} minutes!",
        "Warden {mod} has imprisoned {user} in Level 2 of Impel Down for {time} minutes!",
        "{user} has been sentenced to {time} minutes in Level 2: Wild Beast Hell by {mod}!"
    ],
    3: [
        "{user} has been cast down to Impel Down Level 3: Starvation Hell by {mod} for {time} minutes!",
        "Warden {mod} has imprisoned {user} in Level 3 of Impel Down for {time} minutes!",
        "{user} has been sentenced to {time} minutes in Level 3: Starvation Hell by {mod}!"
    ],
    4: [
        "{user} has been thrown into Impel Down Level 4: Burning Hell by {mod} for {time} minutes!",
        "Warden {mod} has imprisoned {user} in Level 4 of Impel Down for {time} minutes!",
        "{user} has been sentenced to {time} minutes in Level 4: Burning Hell by {mod}!"
    ],
    5: [
        "{user} has been cast down to Impel Down Level 5: Freezing Hell by {mod} for {time} minutes!",
        "Warden {mod} has imprisoned {user} in Level 5 of Impel Down for {time} minutes!",
        "{user} has been sentenced to {time} minutes in Level 5: Freezing Hell by {mod}!"
    ],
    6: [
        "{user} has been thrown into Impel Down Level 6: Eternal Hell by {mod} for {time} minutes!",
        "Warden {mod} has imprisoned {user} in Level 6 of Impel Down for {time} minutes!",
        "{user} has been sentenced to {time} minutes in Level 6: Eternal Hell by {mod}!"
    ]
}

# Impel Down GIFs by level
IMPEL_DOWN_GIFS = {
    1: [
        "https://media.giphy.com/media/MCZ39lz83o5lC/giphy.gif",  # Prison scene
        "https://media.giphy.com/media/xUPGcC4A6ElTkMBjTG/giphy.gif",  # Impel Down
        "https://media.giphy.com/media/ZbISs2fONt46fKGjw5/giphy.gif"   # Prison
    ],
    2: [
        "https://media.giphy.com/media/26BRzozg4TCBXv6QU/giphy.gif",  # Monster
        "https://media.giphy.com/media/Wry3VKSx2T6vDhqfwV/giphy.gif",  # Prison
        "https://media.giphy.com/media/fSYCQpJKABoAc3jbHL/giphy.gif"   # Creatures
    ],
    3: [
        "https://media.giphy.com/media/l2Zbq7rNLpSCy3bR6/giphy.gif",  # Starvation
        "https://media.giphy.com/media/lRpQK581rklYfJMPAj/giphy.gif",  # Impel Down
        "https://media.giphy.com/media/QaCaZIZ9ekMpk7jOOV/giphy.gif"   # Prison
    ],
    4: [
        "
