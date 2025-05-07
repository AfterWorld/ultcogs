# List of warning messages that will be randomly selected
WARN_MESSAGES = [
    "The World Government has increased {user}'s bounty! They're now at Warning Level {level}!",
    "Marine HQ has issued a new bounty for {user}! Now at Warning Level {level}!",
    "{mod} has reported pirate activity from {user}! Bounty increased to Level {level}!",
    "A Marine report filed by {mod} has increased {user}'s bounty to Level {level}!",
    "ATTENTION PIRATES: {user}'s bounty has increased to Level {level} by order of {mod}!",
    "{user} has been spotted by Marine {mod}! Bounty now at Level {level}!",
    "The Marines have updated their wanted posters! {user} now has a Level {level} bounty!",
    "{mod} has alerted Marine HQ about {user}! Their bounty is now Level {level}!",
    "WANTED DEAD OR ALIVE: {user} with a Level {level} bounty reported by {mod}!",
    "{user}'s name has been recorded in the Marine records at Level {level} by {mod}!"
]

# List of warning GIFs that will be randomly selected
WARN_GIFS = [
    "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",  # Wanted poster
    "https://media.giphy.com/media/l2ZE9kYZ6UcoMzKdq/giphy.gif",  # Marine
    "https://media.giphy.com/media/xUOxfijCUYEGRZJkiI/giphy.gif",  # Marine HQ
    "https://media.giphy.com/media/fH985LNdqFZXOFHygK/giphy.gif",  # Bounty increase
    "https://media.giphy.com/media/H7SaUQ5vEbocJqYZKO/giphy.gif",  # Marine warning
    "https://media.giphy.com/media/jofMbkWWJ6AwBhYqr1/giphy.gif",  # Wanted
    "https://media.giphy.com/media/2wYiftbF7h9RBD0CKw/giphy.gif",  # Marine alert
    "https://media.giphy.com/media/l0MYsNv0lRNqDZsnm/giphy.gif",  # Marine ship
    "https://media.giphy.com/media/3wZeXMqJ2XtlBtJR5C/giphy.gif",  # Warning
    "https://media.giphy.com/media/3HAYjf986boJO698zIY/giphy.gif"   # Marine alert
]

# Alternative command names for warn
WARN_ALIASES = [
    "bountyraise",
    "marinealert",
    "wantedposter",
    "increasebounty",
    "reportpirate"
]

# Bounty levels based on warning count
BOUNTY_LEVELS = {
    0: "0 Berries",
    1: "10,000,000 Berries",
    2: "50,000,000 Berries",
    3: "100,000,000 Berries",
    4: "300,000,000 Berries",
    5: "500,000,000 Berries",
    6: "1,000,000,000+ Berries"
}

# Bounty descriptions based on warning count
BOUNTY_DESCRIPTIONS = {
    0: "Harmless Civilian",
    1: "East Blue Troublemaker",
    2: "Paradise Rookie",
    3: "Supernova Threat",
    4: "Warlord Level Danger",
    5: "Yonko Commander Class",
    6: "Yonko Level Threat"
}
