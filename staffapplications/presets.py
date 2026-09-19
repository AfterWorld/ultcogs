"""Built-in recruitment copy and question templates."""

LEGACY_TEMPLATE = {
    "title": "Join Our Staff Team",
    "color": 5793266,
    "description": "Help support our community. Apply privately through DMs.",
    "requirements": "Be respectful, know the server rules, and answer honestly.",
    "positions": ["Moderator", "Helper"],
    "questions": [
        "What is your timezone?",
        "When are you available, and how many hours per week can you help?",
        "What relevant experience do you have?",
        "Why would you like to join our staff team?",
        "How would you handle an argument between two members?",
        "What would you do if a friend broke a server rule?",
    ],
}

ONE_PIECE_TEMPLATE = {
    "title": "⚓ Staff Applications • One Piece Community 👒",
    "color": 15844367,
    "description": "Want to become part of the staff team?\n\nWe are looking for active, respectful, and dedicated members who are willing to help the community grow and stay positive.\n\nTake your time answering the questions honestly and professionally.",
    "requirements": "• Be mature and respectful\n• Stay active in the server\n• Help other members\n• Follow all server rules\n• Be able to work in a team",
    "next_steps": "Once you submit your application, the management team will review it carefully. Accepted applicants may receive additional questions or an interview.",
    "footer": "Click Apply Now below to apply • Good luck, pirate!",
    "positions": ["Moderator"],
    "questions": [
        "Why do you want to become a moderator for this server?",
        "What experience do you have moderating Discord servers or other communities?",
        "How would you handle a conflict between two members in the server?",
        "What is your availability for moderation duties? (e.g., hours per day or time zones)",
        "How old are you?",
        "How would you improve the community experience as a moderator?",
        "Are you familiar with moderation tools (e.g., Discord bots like MEE6, Dyno, or Automod)? If so, which ones?",
        "Can you share an example of how you’ve resolved a challenging situation in a team or community setting?",
        "What qualities or skills do you think make a great moderator?",
        "How would you handle a situation where another staff member breaks the rules?",
    ],
}

# Fictional demonstration answers, matched by question rather than list position.
SAMPLE_ANSWERS = dict(
    zip(
        ONE_PIECE_TEMPLATE["questions"],
        [
            "I enjoy the One Piece community and want to help keep discussions welcoming, fair, and fun for everyone.",
            "I have helped moderate a small gaming community, welcomed new members, and handled reports with the rest of the team.",
            "I would calmly separate the disagreement from personal attacks, hear both sides, and apply the server rules consistently. I would involve a senior moderator if needed.",
            "I am usually available for about two hours on weekday evenings in Eastern Time, with more flexibility on weekends.",
            "22 (fictional example applicant).",
            "I would welcome newcomers, encourage spoiler-safe discussions, and help run community events and weekly One Piece discussions.",
            "I have used Discord AutoMod and Dyno for spam filters, moderation logs, warnings, and basic moderation commands.",
            "During a team event, two members disagreed about responsibilities. I listened to both, clarified the shared goal, and helped divide the tasks fairly.",
            "Patience, fairness, clear communication, teamwork, good judgment, and the ability to stay calm under pressure.",
            "I would document what happened and report it privately through the appropriate management process. Staff should be held to the same rules as everyone else.",
        ],
    )
)
