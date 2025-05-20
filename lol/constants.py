# lol/constants.py - Constants and configuration
from typing import Dict, List, Tuple

# Data Dragon version - can be updated as needed
DDRAGON_VERSION = "13.24.1"

# Mapping of regions to their routing values
REGION_MAPPING = {
    "na": "na1",
    "euw": "euw1", 
    "eune": "eun1",
    "kr": "kr",
    "br": "br1",
    "jp": "jp1",
    "ru": "ru",
    "oc": "oc1",
    "tr": "tr1",
    "lan": "la1",
    "las": "la2",
    "me": "me1",
    "sg": "sg2",
    "tw": "tw2",
    "vn": "vn2"
}

# Regional routing for match API
MATCH_ROUTING = {
    "na1": "americas",
    "br1": "americas", 
    "la1": "americas",
    "la2": "americas",
    "kr": "asia",
    "jp1": "asia",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "me1": "europe",
    "oc1": "sea",
    "sg2": "sea",
    "tw2": "sea",
    "vn2": "sea"
}

# Endpoint-specific rate limits (requests, seconds)
ENDPOINT_RATE_LIMITS: Dict[str, List[Tuple[int, int]]] = {
    # Champion rotation
    "champion-rotations": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    
    # Summoner endpoints
    "summoner": [(1600, 60)],  # 1600/1m
    
    # League endpoints
    "league-entries": [(100, 60)],  # 100/1m
    "league-challenger": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    "league-master": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    "league-grandmaster": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    
    # Account endpoints
    "account": [(1000, 60), (20000, 10), (1200000, 600)],  # 1000/1m, 20000/10s, 1200000/10m
    
    # Match endpoints
    "match": [(2000, 10)],  # 2000/10s
    
    # Champion mastery
    "champion-mastery": [(20000, 10), (1200000, 600)],  # 20000/10s, 1200000/10m
    
    # Status
    "status": [(20000, 10), (1200000, 600)],  # 20000/10s, 1200000/10m
    
    # Clash
    "clash-teams": [(200, 60)],  # 200/1m
    "clash-tournaments": [(10, 60)],  # 10/1m
    "clash-players": [(20000, 10), (1200000, 600)],  # 20000/10s, 1200000/10m
}

# Queue type mappings
QUEUE_TYPES = {
    420: "Ranked Solo/Duo",
    440: "Ranked Flex",
    450: "ARAM",
    400: "Normal Draft",
    430: "Normal Blind",
    900: "URF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
}

# Rank emojis
RANK_EMOJIS = {
    "IRON": "🥉",
    "BRONZE": "🟤", 
    "SILVER": "🩶",
    "GOLD": "🟡",
    "PLATINUM": "🐱‍👤",
    "EMERALD": "💚",
    "DIAMOND": "💎",
    "MASTER": "🔥",
    "GRANDMASTER": "⭐",
    "CHALLENGER": "🏆"
}

# Champion role emojis
CHAMPION_ROLE_EMOJIS = {
    "Assassin": "🗡️",
    "Fighter": "⚔️",
    "Mage": "🔮",
    "Marksman": "🏹",
    "Support": "🛡️",
    "Tank": "🛡️"
}

# Game mode emojis
GAME_MODE_EMOJIS = {
    "CLASSIC": "🏛️",
    "ARAM": "🌉",
    "URF": "🚀",
    "ODIN": "🔱",
    "TUTORIAL": "📚",
    "DOOMBOTSTEEMO": "🍄"
}

# Rank tier colors for embeds
RANK_COLORS = {
    "IRON": 0x8B4513,
    "BRONZE": 0xCD7F32,
    "SILVER": 0xC0C0C0,
    "GOLD": 0xFFD700,
    "PLATINUM": 0x00CED1,
    "EMERALD": 0x50C878,
    "DIAMOND": 0xB9F2FF,
    "MASTER": 0x9F2B68,
    "GRANDMASTER": 0xFF5722,
    "CHALLENGER": 0x9C27B0
}