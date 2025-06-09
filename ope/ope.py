import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import discord
import yaml
from discord.ext import tasks
from redbot.core import commands, Config, checks, data_manager
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify


class OPE(commands.Cog):
    """One Piece Engagement - Enhanced with automatic themed daily rotation!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1111222233334444)
        
        # Paths for data files
        self.cog_data_path = Path(data_manager.cog_data_path(self))
        self.challenges_path = self.cog_data_path / "challenges"
        self.themes_path = self.cog_data_path / "themes"  # New themed content
        self.trivia_path = self.cog_data_path / "trivia"
        self.constants_path = self.cog_data_path / "constants.yaml"
        
        # Create directories
        self.challenges_path.mkdir(parents=True, exist_ok=True)
        self.themes_path.mkdir(parents=True, exist_ok=True)
        self.trivia_path.mkdir(parents=True, exist_ok=True)
        
        # Enhanced guild settings with theme support
        default_guild = {
            "challenge_channel": None,
            "trivia_channel": None,
            "daily_challenges": True,
            "themed_days": True,  # New: Enable themed daily rotation
            "auto_trivia": False,
            "challenge_time": "12:00",
            "trivia_interval": 3600,
            "current_daily": None,
            "current_weekly": None,
            "current_theme": None,  # Track current day's theme
            "weekly_day": 1,
            "participants": {},
            "trivia_leaderboard": {},
            "challenge_rewards": True,
            "points_per_daily": 10,
            "points_per_weekly": 50,
            "weekly_tournament": False,
            "tournament_day": 6,
            "theme_override": None,  # Admin can override theme for special events
            "trivia_boost_days": [1, 4],  # Tuesday=1, Friday=4 get extra trivia
        }
        
        # Default user settings
        default_user = {
            "total_points": 0,
            "daily_streak": 0,
            "trivia_correct": 0,
            "trivia_attempted": 0,
            "favorite_category": None,
            "achievements": [],
            "theme_participation": {}  # Track participation by theme
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        
        # Cache for loaded data
        self.constants = {}
        self.daily_challenges = {}
        self.weekly_challenges = {}
        self.themed_challenges = {}  # New: themed content cache
        self.trivia_data = {}
        
        # Weekly theme schedule
        self.weekly_themes = {
            0: "theory_monday",      # Monday
            1: "trivia_tuesday",     # Tuesday  
            2: "whatif_wednesday",   # Wednesday
            3: "throwback_thursday", # Thursday
            4: "fight_friday",       # Friday
            5: "creative_saturday",  # Saturday
            6: "summary_sunday"      # Sunday
        }
        
        # Load all data files
        self.load_all_data()
        
        # Start background tasks
        self.daily_challenge_task.start()
        self.auto_trivia_task.start()

    def cog_unload(self):
        self.daily_challenge_task.cancel()
        self.auto_trivia_task.cancel()

    def load_all_data(self):
        """Load all data files into memory"""
        self.load_constants()
        self.load_challenges()
        self.load_themed_challenges()  # New: load themed content
        self.load_trivia_data()

    def load_constants(self):
        """Load constants from file or create default"""
        if not self.constants_path.exists():
            self.create_default_constants()
        
        try:
            with open(self.constants_path, 'r', encoding='utf-8') as f:
                self.constants = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading constants: {e}")
            self.create_default_constants()

    def create_default_constants(self):
        """Create default constants file"""
        default_constants = {
            "characters": {
                "straw_hats": ["luffy", "zoro", "nami", "usopp", "sanji", "chopper", "robin", "franky", "brook", "jinbe"],
                "emperors": ["shanks", "kaido", "big mom", "blackbeard"],
                "admirals": ["akainu", "kizaru", "aokiji", "fujitora", "ryokugyu"],
                "warlords": ["mihawk", "crocodile", "doflamingo", "hancock", "jinbe", "law", "weevil"]
            },
            "locations": {
                "islands": ["alabasta", "skypiea", "water 7", "thriller bark", "sabaody", "amazon lily", "impel down", "marineford", "fishman island", "punk hazard", "dressrosa", "zou", "whole cake island", "wano"],
                "seas": ["east blue", "west blue", "north blue", "south blue", "grand line", "new world"],
                "special_places": ["reverse mountain", "calm belt", "red line", "marie geoise", "enies lobby"]
            },
            "devil_fruits": {
                "paramecia": ["gomu gomu", "bara bara", "sube sube", "bomu bomu", "kiro kiro"],
                "zoan": ["hito hito", "tori tori", "inu inu", "neko neko", "ushi ushi"],
                "logia": ["moku moku", "mera mera", "suna suna", "goro goro", "hie hie"]
            },
            "emojis": {
                "luffy": "🍖",
                "zoro": "⚔️",
                "nami": "🍊",
                "usopp": "🎯",
                "sanji": "🚬",
                "chopper": "🦌",
                "robin": "📚",
                "franky": "🤖",
                "brook": "💀",
                "jinbe": "🐠",
                "ace": "🔥",
                "law": "⚕️",
                "kidd": "🧲",
                "shanks": "🦾",
                "whitebeard": "⚡",
                "kaido": "🐉"
            },
            "difficulty_colors": {
                "easy": 0x00ff00,
                "medium": 0xff8000,
                "hard": 0xff0000,
                "expert": 0x8b00ff
            },
            "point_values": {
                "easy_trivia": 10,
                "medium_trivia": 20,
                "hard_trivia": 30,
                "expert_trivia": 50,
                "daily_challenge": 15,
                "weekly_challenge": 75,
                "streak_bonus": 5
            }
        }
        
        with open(self.constants_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_constants, f, default_flow_style=False, allow_unicode=True)
        
        self.constants = default_constants

    def load_challenges(self):
        """Load challenge files"""
        # Create default challenge files if they don't exist
        self.create_default_challenges()
        
        # Load daily challenges
        daily_file = self.challenges_path / "daily_challenges.yaml"
        if daily_file.exists():
            with open(daily_file, 'r', encoding='utf-8') as f:
                self.daily_challenges = yaml.safe_load(f)
        
        # Load weekly challenges
        weekly_file = self.challenges_path / "weekly_challenges.yaml"
        if weekly_file.exists():
            with open(weekly_file, 'r', encoding='utf-8') as f:
                self.weekly_challenges = yaml.safe_load(f)

    def create_default_challenges(self):
        """Create default challenge files"""
        daily_challenges = {
            "discussion": [
                {
                    "prompt": "What's your favorite Devil Fruit power and why?",
                    "category": "powers",
                    "difficulty": "easy"
                },
                {
                    "prompt": "If you could join any pirate crew, which would it be?",
                    "category": "crews",
                    "difficulty": "easy"
                },
                {
                    "prompt": "What do you think is the most emotional One Piece moment?",
                    "category": "emotions",
                    "difficulty": "medium"
                }
            ],
            "creative": [
                {
                    "prompt": "Draw or describe your own pirate flag design!",
                    "category": "art",
                    "difficulty": "medium"
                },
                {
                    "prompt": "Create a new Devil Fruit and describe its powers!",
                    "category": "powers",
                    "difficulty": "medium"
                },
                {
                    "prompt": "Design a new island for the Straw Hats to visit!",
                    "category": "worldbuilding",
                    "difficulty": "hard"
                }
            ],
            "trivia": [
                {
                    "prompt": "Name 3 members of the Worst Generation",
                    "answers": ["luffy", "zoro", "law", "kidd", "killer", "hawkins", "drake", "apoo", "bonney", "bege", "urouge"],
                    "min_correct": 3,
                    "difficulty": "medium"
                },
                {
                    "prompt": "List 5 Straw Hat Pirates in order of joining",
                    "answers": ["luffy", "zoro", "nami", "usopp", "sanji", "chopper", "robin", "franky", "brook", "jinbe"],
                    "min_correct": 5,
                    "difficulty": "easy"
                }
            ],
            "scenario": [
                {
                    "prompt": "You're stuck on a deserted island with one Straw Hat member. Who do you choose and why?",
                    "category": "survival",
                    "difficulty": "easy"
                },
                {
                    "prompt": "You have to defend your hometown from pirates. Which 3 One Piece characters do you recruit?",
                    "category": "strategy",
                    "difficulty": "medium"
                }
            ]
        }
        
        weekly_challenges = {
            "contests": [
                {
                    "title": "Best One Piece Fan Art Contest",
                    "description": "Create original One Piece artwork",
                    "theme": "Adventure",
                    "duration": 7,
                    "category": "art"
                },
                {
                    "title": "Ultimate Fight Tournament",
                    "description": "Vote for the best One Piece battles",
                    "theme": "Epic Battles",
                    "duration": 7,
                    "category": "tournament"
                }
            ],
            "analysis": [
                {
                    "title": "Character Deep Dive Week",
                    "description": "Analyze character development and growth",
                    "theme": "Character Analysis",
                    "duration": 7,
                    "category": "analysis"
                }
            ],
            "theory": [
                {
                    "title": "Theory Crafting Week",
                    "description": "Share your wildest One Piece theories",
                    "theme": "Predictions",
                    "duration": 7,
                    "category": "theory"
                }
            ]
        }
        
        # Save files
        with open(self.challenges_path / "daily_challenges.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(daily_challenges, f, default_flow_style=False, allow_unicode=True)
        
        with open(self.challenges_path / "weekly_challenges.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(weekly_challenges, f, default_flow_style=False, allow_unicode=True)

    def load_trivia_data(self):
        """Load trivia data files"""
        # Create default trivia if it doesn't exist
        self.create_default_trivia()
        
        # Load all trivia files
        for trivia_file in self.trivia_path.glob("*.yaml"):
            difficulty = trivia_file.stem
            with open(trivia_file, 'r', encoding='utf-8') as f:
                self.trivia_data[difficulty] = yaml.safe_load(f)

    def create_default_trivia(self):
        """Create default trivia files"""
        easy_trivia = {
            "general": [
                {
                    "question": "What is Luffy's dream?",
                    "answers": ["to become pirate king", "pirate king", "become the pirate king"],
                    "category": "dreams"
                },
                {
                    "question": "Who is the navigator of the Straw Hat Pirates?",
                    "answers": ["nami"],
                    "category": "crew"
                },
                {
                    "question": "What Devil Fruit did Luffy eat?",
                    "answers": ["gomu gomu no mi", "rubber fruit", "gum gum fruit"],
                    "category": "powers"
                }
            ],
            "characters": [
                {
                    "question": "What color is Zoro's hair?",
                    "answers": ["green"],
                    "category": "appearance"
                },
                {
                    "question": "What does Sanji love to cook?",
                    "answers": ["food", "anything", "everything"],
                    "category": "personality"
                }
            ]
        }
        
        medium_trivia = {
            "general": [
                {
                    "question": "What is the name of Law's submarine?",
                    "answers": ["polar tang"],
                    "category": "ships"
                },
                {
                    "question": "Which island is known as the 'Island of Women'?",
                    "answers": ["amazon lily"],
                    "category": "locations"
                }
            ],
            "powers": [
                {
                    "question": "What type of Devil Fruit did Ace eat?",
                    "answers": ["logia", "fire logia", "mera mera no mi"],
                    "category": "devil_fruits"
                }
            ]
        }
        
        hard_trivia = {
            "general": [
                {
                    "question": "What was the first island the Straw Hats visited in the New World?",
                    "answers": ["fishman island", "fish-man island"],
                    "category": "locations"
                },
                {
                    "question": "Who was the first person to call Luffy 'Straw Hat'?",
                    "answers": ["mihawk", "dracule mihawk"],
                    "category": "nicknames"
                }
            ]
        }
        
        # Save trivia files
        with open(self.trivia_path / "easy.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(easy_trivia, f, default_flow_style=False, allow_unicode=True)
        
        with open(self.trivia_path / "medium.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(medium_trivia, f, default_flow_style=False, allow_unicode=True)
        
        with open(self.trivia_path / "hard.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(hard_trivia, f, default_flow_style=False, allow_unicode=True)

    def load_themed_challenges(self):
        """Load themed challenge files for each day"""
        self.create_default_themed_challenges()
        
        for day_num, theme_name in self.weekly_themes.items():
            theme_file = self.themes_path / f"{theme_name}.yaml"
            if theme_file.exists():
                with open(theme_file, 'r', encoding='utf-8') as f:
                    self.themed_challenges[theme_name] = yaml.safe_load(f)

    def create_default_themed_challenges(self):
        """Create ALL themed challenge files for each day - COMPLETE VERSION"""
        
        # Monday - Theory Monday
        theory_monday = {
            "theme_info": {
                "name": "Theory Monday",
                "emoji": "🧭",
                "description": "Dive deep into One Piece mysteries and theories",
                "focus": "predictions, theories, mysteries, lore"
            },
            "discussion": [
                {"prompt": "What do you think the One Piece treasure actually is?", "category": "mysteries", "difficulty": "medium"},
                {"prompt": "What's your theory about the Will of D?", "category": "ancient_history", "difficulty": "hard"},
                {"prompt": "How do you think the final war will unfold?", "category": "predictions", "difficulty": "expert"},
                {"prompt": "What's the connection between Joy Boy and Luffy?", "category": "mysteries", "difficulty": "hard"},
                {"prompt": "What happened during the Void Century?", "category": "ancient_history", "difficulty": "expert"},
                {"prompt": "Is Im-sama the final villain or something bigger?", "category": "predictions", "difficulty": "hard"},
                {"prompt": "What's the true power of the Ancient Weapons?", "category": "mysteries", "difficulty": "hard"},
                {"prompt": "How will the World Government fall?", "category": "predictions", "difficulty": "medium"},
                {"prompt": "What's Blackbeard's ultimate plan?", "category": "villains", "difficulty": "medium"},
                {"prompt": "Is Laugh Tale on the moon or underwater?", "category": "mysteries", "difficulty": "medium"}
            ],
            "trivia_focus": ["mysteries", "ancient_history", "void_century", "poneglyphs"]
        }
        
        # Tuesday - Trivia Tuesday  
        trivia_tuesday = {
            "theme_info": {
                "name": "Trivia Tuesday",
                "emoji": "🎯", 
                "description": "Test your One Piece knowledge with intensive trivia",
                "focus": "knowledge testing, competitions, brain challenges"
            },
            "knowledge": [
                {"prompt": "Name all 11 members of the Worst Generation", "answers": ["luffy", "zoro", "law", "kidd", "killer", "hawkins", "drake", "apoo", "bonney", "bege", "urouge"], "min_correct": 8, "category": "characters", "difficulty": "medium"},
                {"prompt": "List the first 5 Straw Hat Pirates in joining order", "answers": ["luffy", "zoro", "nami", "usopp", "sanji"], "min_correct": 5, "category": "crew", "difficulty": "easy"},
                {"prompt": "Name 5 Whitebeard Pirates division commanders", "answers": ["marco", "ace", "vista", "thatch", "jozu", "blamenco", "rakuyo", "namule", "blenheim", "curiel"], "min_correct": 5, "category": "crews", "difficulty": "hard"},
                {"prompt": "List all current Yonko in order of bounty", "answers": ["whitebeard", "kaido", "big mom", "shanks", "blackbeard"], "min_correct": 4, "category": "emperors", "difficulty": "medium"},
                {"prompt": "Name 3 Logia Devil Fruit users", "answers": ["ace", "smoker", "crocodile", "enel", "aokiji", "kizaru", "akainu", "blackbeard", "caesar"], "min_correct": 3, "category": "powers", "difficulty": "easy"},
                {"prompt": "List 5 Grand Line islands in story order", "answers": ["reverse mountain", "whisky peak", "little garden", "drum island", "alabasta", "jaya", "skypiea"], "min_correct": 5, "category": "locations", "difficulty": "hard"}
            ],
            "quiz": [
                {"prompt": "Quick Fire Round: Name as many One Piece islands as you can in 60 seconds!", "category": "speed_round", "difficulty": "medium"},
                {"prompt": "Bounty Challenge: Order these bounties from highest to lowest", "category": "bounties", "difficulty": "hard"},
                {"prompt": "Devil Fruit Speed Round: Name the user for each fruit!", "category": "powers", "difficulty": "medium"}
            ],
            "trivia_boost": True,
            "trivia_focus": ["general", "characters", "crews", "bounties"]
        }
        
        # Wednesday - What-If Wednesday
        whatif_wednesday = {
            "theme_info": {
                "name": "What-If Wednesday", 
                "emoji": "❓",
                "description": "Explore alternate timelines and scenarios",
                "focus": "alternate scenarios, creative thinking, what-if discussions"
            },
            "scenario": [
                {"prompt": "What if Ace never died? How would the story change?", "category": "alternate_timeline", "difficulty": "medium"},
                {"prompt": "What if Luffy ate a different Devil Fruit as a child?", "category": "alternate_powers", "difficulty": "easy"},
                {"prompt": "What if Sabo never lost his memory?", "category": "alternate_timeline", "difficulty": "medium"},
                {"prompt": "What if the Straw Hats met 10 years earlier?", "category": "alternate_timeline", "difficulty": "easy"},
                {"prompt": "What if Zoro joined the Marines instead of becoming a pirate?", "category": "alternate_paths", "difficulty": "medium"},
                {"prompt": "What if Robin never joined the Straw Hats?", "category": "alternate_crew", "difficulty": "hard"},
                {"prompt": "What if Whitebeard survived Marineford?", "category": "alternate_timeline", "difficulty": "hard"},
                {"prompt": "What if Crocodile successfully took over Alabasta?", "category": "villain_victory", "difficulty": "medium"},
                {"prompt": "What if Luffy failed to save Sanji from Big Mom?", "category": "mission_failure", "difficulty": "hard"},
                {"prompt": "What if the Going Merry never broke?", "category": "alternate_ships", "difficulty": "easy"},
                {"prompt": "What if Shanks never lost his arm?", "category": "alternate_timeline", "difficulty": "medium"},
                {"prompt": "What if Garp raised Luffy to be a Marine?", "category": "alternate_upbringing", "difficulty": "medium"},
                {"prompt": "What if Law never formed an alliance with Luffy?", "category": "alternate_alliances", "difficulty": "medium"},
                {"prompt": "What if Doflamingo successfully killed everyone in Dressrosa?", "category": "villain_victory", "difficulty": "hard"},
                {"prompt": "What if Jinbe joined the crew earlier?", "category": "alternate_crew", "difficulty": "easy"}
            ],
            "alternate": [
                {"prompt": "Create an alternate version of your favorite arc with a different outcome", "category": "story_rewrite", "difficulty": "hard"},
                {"prompt": "What if the Straw Hats were Marines? What would their ranks be?", "category": "role_reversal", "difficulty": "medium"},
                {"prompt": "Design an alternate path for Luffy to become Pirate King", "category": "alternate_journey", "difficulty": "hard"}
            ],
            "trivia_focus": ["story", "plot_points", "key_events"]
        }
        
        # Thursday - Throwback Thursday
        throwback_thursday = {
            "theme_info": {
                "name": "Throwback Thursday",
                "emoji": "⏪", 
                "description": "Celebrate classic One Piece moments and nostalgia",
                "focus": "classic moments, early arcs, nostalgic content, memories"
            },
            "memory": [
                {"prompt": "Share your favorite moment from the East Blue saga", "category": "early_arcs", "difficulty": "easy"},
                {"prompt": "What was the most emotional scene in Alabasta?", "category": "classic_moments", "difficulty": "easy"},
                {"prompt": "Best Going Merry moment that made you cry?", "category": "emotional_moments", "difficulty": "medium"},
                {"prompt": "Most shocking moment in Enies Lobby?", "category": "classic_moments", "difficulty": "medium"},
                {"prompt": "Your favorite Skypiea moment that everyone forgets?", "category": "underrated_moments", "difficulty": "medium"},
                {"prompt": "What made you fall in love with One Piece initially?", "category": "first_impressions", "difficulty": "easy"},
                {"prompt": "Best pre-timeskip fight scene?", "category": "classic_battles", "difficulty": "easy"},
                {"prompt": "Most nostalgic One Piece opening song?", "category": "music_nostalgia", "difficulty": "easy"},
                {"prompt": "Funniest early series moment?", "category": "comedy_classics", "difficulty": "easy"},
                {"prompt": "Which early villain do you miss most?", "category": "classic_villains", "difficulty": "medium"},
                {"prompt": "Best character introduction in the early series?", "category": "character_debuts", "difficulty": "medium"},
                {"prompt": "Most quotable line from pre-timeskip?", "category": "memorable_quotes", "difficulty": "medium"}
            ],
            "visual": [
                {"prompt": "Share a screenshot of your favorite classic One Piece moment!", "category": "screenshots", "difficulty": "easy"},
                {"prompt": "Post your favorite old-school One Piece art style panel", "category": "art_nostalgia", "difficulty": "easy"},
                {"prompt": "Show us your favorite Going Merry scene", "category": "ship_nostalgia", "difficulty": "easy"}
            ],
            "nostalgia": [
                {"prompt": "What classic One Piece moment hits different now that you're older?", "category": "perspective_change", "difficulty": "medium"},
                {"prompt": "Which early series prediction of yours came true?", "category": "old_predictions", "difficulty": "hard"},
                {"prompt": "What do you miss most about pre-timeskip One Piece?", "category": "series_evolution", "difficulty": "medium"}
            ],
            "trivia_focus": ["early_arcs", "classic_moments", "east_blue", "alabasta"]
        }
        
        # Friday - Fight Friday
        fight_friday = {
            "theme_info": {
                "name": "Fight Friday",
                "emoji": "⚔️",
                "description": "Battle discussions, power scaling, and combat analysis", 
                "focus": "battles, power scaling, combat, strength debates"
            },
            "debate": [
                {"prompt": "Who would win: Current Luffy vs Prime Whitebeard?", "category": "powerscaling", "difficulty": "medium"},
                {"prompt": "Rank the Admirals by overall strength", "category": "powerscaling", "difficulty": "medium"}, 
                {"prompt": "Best fighting technique in all of One Piece?", "category": "techniques", "difficulty": "easy"},
                {"prompt": "Create the ultimate tournament bracket with current fighters", "category": "tournaments", "difficulty": "hard"},
                {"prompt": "Mihawk vs Shanks - who really wins?", "category": "legendary_battles", "difficulty": "hard"},
                {"prompt": "Strongest Straw Hat in a 1v1 (excluding Luffy)?", "category": "crew_battles", "difficulty": "medium"},
                {"prompt": "Which Emperor has the most devastating attack?", "category": "ultimate_attacks", "difficulty": "medium"},
                {"prompt": "Best Devil Fruit for pure combat?", "category": "combat_fruits", "difficulty": "medium"},
                {"prompt": "Who has the most broken Haki abilities?", "category": "haki_debate", "difficulty": "hard"},
                {"prompt": "Create the perfect fighting crew from any series characters", "category": "dream_teams", "difficulty": "hard"}
            ],
            "ranking": [
                {"prompt": "Rank all Conqueror's Haki users by mastery level", "category": "haki", "difficulty": "hard"},
                {"prompt": "Top 10 strongest characters currently alive", "category": "power_rankings", "difficulty": "expert"},
                {"prompt": "Rank the Worst Generation by current power level", "category": "supernova_ranking", "difficulty": "medium"},
                {"prompt": "Best to worst: All Warlord combat abilities", "category": "warlord_ranking", "difficulty": "medium"}
            ],
            "analysis": [
                {"prompt": "Break down the perfect counter to Kaido's fighting style", "category": "combat_analysis", "difficulty": "expert"},
                {"prompt": "Most underrated fighter who deserves respect", "category": "underrated_fighters", "difficulty": "medium"},
                {"prompt": "Predict the fighting style of the final boss", "category": "final_boss", "difficulty": "expert"}
            ],
            "trivia_boost": True,
            "trivia_focus": ["combat", "techniques", "powers", "battles"]
        }
        
        # Saturday - Creative Saturday
        creative_saturday = {
            "theme_info": {
                "name": "Creative Saturday", 
                "emoji": "🎨",
                "description": "Art, writing, and creative expression showcase",
                "focus": "creativity, art, writing, original content"
            },
            "creative": [
                {"prompt": "Design a new Devil Fruit and describe its powers!", "category": "original_content", "difficulty": "medium"},
                {"prompt": "Create your own pirate crew with unique members", "category": "original_content", "difficulty": "medium"},
                {"prompt": "Draw or describe your interpretation of Laugh Tale", "category": "art", "difficulty": "hard"},
                {"prompt": "Write a short adventure featuring any One Piece character", "category": "writing", "difficulty": "medium"},
                {"prompt": "Design a new island with unique culture and challenges", "category": "worldbuilding", "difficulty": "hard"},
                {"prompt": "Create an original Marine Admiral with unique powers", "category": "character_creation", "difficulty": "medium"},
                {"prompt": "Invent a new fighting style combining existing techniques", "category": "technique_creation", "difficulty": "medium"},
                {"prompt": "Design the perfect ship for your dream crew", "category": "ship_design", "difficulty": "medium"},
                {"prompt": "Create a new race for the One Piece world", "category": "worldbuilding", "difficulty": "hard"},
                {"prompt": "Invent a Revolutionary Army member with a tragic backstory", "category": "character_creation", "difficulty": "hard"}
            ],
            "art": [
                {"prompt": "Share your One Piece fan art or describe a scene you'd love to draw!", "category": "art_showcase", "difficulty": "easy"},
                {"prompt": "Design a new Jolly Roger for your favorite character", "category": "flag_design", "difficulty": "easy"},
                {"prompt": "Create a movie poster for a One Piece film starring your favorite character", "category": "poster_design", "difficulty": "medium"},
                {"prompt": "Design costume variants for the Straw Hats", "category": "costume_design", "difficulty": "medium"}
            ],
            "writing": [
                {"prompt": "Write a diary entry from any One Piece character's perspective", "category": "character_writing", "difficulty": "medium"},
                {"prompt": "Create a news article about a major One Piece event", "category": "news_writing", "difficulty": "medium"},
                {"prompt": "Write a letter between two characters who haven't met yet", "category": "creative_writing", "difficulty": "hard"},
                {"prompt": "Compose a sea shanty that the Straw Hats would sing", "category": "song_writing", "difficulty": "hard"}
            ],
            "showcase": [
                {"prompt": "Share any One Piece related creation you've made!", "category": "community_showcase", "difficulty": "easy"},
                {"prompt": "Show off your One Piece collection or setup", "category": "collection_showcase", "difficulty": "easy"}
            ],
            "trivia_focus": ["characters", "world_building", "creative"]
        }
        
        # Sunday - Summary Sunday
        summary_sunday = {
            "theme_info": {
                "name": "Summary Sunday",
                "emoji": "🏆",
                "description": "Week recap, community highlights, and celebrations",
                "focus": "community highlights, week review, achievements"
            },
            "community": [
                {"prompt": "What was the best theory shared this week?", "category": "community_highlight", "difficulty": "easy"},
                {"prompt": "Most creative idea from this week's challenges?", "category": "community_highlight", "difficulty": "easy"}, 
                {"prompt": "Share your favorite community contribution from this week", "category": "appreciation", "difficulty": "easy"},
                {"prompt": "What One Piece topic should we explore more next week?", "category": "planning", "difficulty": "easy"},
                {"prompt": "Which daily theme did you enjoy most this week?", "category": "theme_feedback", "difficulty": "easy"},
                {"prompt": "Highlight someone who had great participation this week", "category": "member_spotlight", "difficulty": "easy"},
                {"prompt": "What was the most interesting debate from Fight Friday?", "category": "weekly_recap", "difficulty": "easy"},
                {"prompt": "Best creative work shared on Creative Saturday?", "category": "art_highlight", "difficulty": "easy"}
            ],
            "reflection": [
                {"prompt": "How did this week's One Piece discussions change your perspective?", "category": "reflection", "difficulty": "medium"},
                {"prompt": "What new One Piece knowledge did you learn this week?", "category": "learning", "difficulty": "easy"},
                {"prompt": "Which challenge made you think the hardest?", "category": "mental_challenge", "difficulty": "medium"},
                {"prompt": "How has your One Piece journey evolved lately?", "category": "personal_growth", "difficulty": "medium"}
            ],
            "planning": [
                {"prompt": "What special events should we plan for next month?", "category": "event_planning", "difficulty": "medium"},
                {"prompt": "Suggest improvements for any of our themed days", "category": "system_feedback", "difficulty": "medium"},
                {"prompt": "What One Piece milestone should we celebrate next?", "category": "celebration_planning", "difficulty": "easy"}
            ],
            "achievements": [
                {"prompt": "Celebrate your One Piece knowledge growth this week!", "category": "personal_achievement", "difficulty": "easy"},
                {"prompt": "Share a One Piece goal you're working towards", "category": "future_goals", "difficulty": "easy"},
                {"prompt": "What One Piece skill have you improved on recently?", "category": "skill_development", "difficulty": "medium"}
            ],
            "trivia_focus": ["mixed_review", "weekly_highlights"]
        }
        
        # Save all theme files
        themes = {
            "theory_monday": theory_monday,
            "trivia_tuesday": trivia_tuesday,
            "whatif_wednesday": whatif_wednesday,
            "throwback_thursday": throwback_thursday,
            "fight_friday": fight_friday,
            "creative_saturday": creative_saturday,
            "summary_sunday": summary_sunday
        }
        
        for theme_name, theme_data in themes.items():
            theme_file = self.themes_path / f"{theme_name}.yaml"
            with open(theme_file, 'w', encoding='utf-8') as f:
                yaml.dump(theme_data, f, default_flow_style=False, allow_unicode=True)

    def get_current_theme(self, override_theme: str = None) -> str:
        """Get current day's theme or override"""
        if override_theme:
            return override_theme
        
        current_day = datetime.now().weekday()  # 0=Monday, 6=Sunday
        return self.weekly_themes.get(current_day, "theory_monday")

    async def post_daily_challenge(self, guild: discord.Guild):
        """Enhanced daily challenge posting with theme awareness"""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["challenge_channel"]
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        # Get current theme
        override_theme = guild_config.get("theme_override")
        current_theme = self.get_current_theme(override_theme)
        theme_data = self.themed_challenges.get(current_theme, {})
        
        # Check if themed days are enabled
        if guild_config.get("themed_days", True) and theme_data:
            challenge = await self.select_themed_challenge(theme_data)
        else:
            # Fall back to regular challenges
            if not self.daily_challenges:
                return
            challenge_type = random.choice(list(self.daily_challenges.keys()))
            challenge = random.choice(self.daily_challenges[challenge_type])
            challenge["theme"] = "random"
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Create themed challenge embed
        theme_info = theme_data.get("theme_info", {})
        theme_emoji = theme_info.get("emoji", "🏴‍☠️")
        theme_name = theme_info.get("name", "Daily Challenge")
        
        embed = discord.Embed(
            title=f"{theme_emoji} {theme_name}!",
            description=challenge["prompt"],
            color=self.get_theme_color(current_theme),
            timestamp=datetime.now()
        )
        
        if theme_info.get("description"):
            embed.add_field(
                name="📋 Today's Theme",
                value=theme_info["description"],
                inline=False
            )
        
        embed.add_field(
            name="📝 How to Participate",
            value="React with ⚓ and share your response!",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Reward",
            value=f"{guild_config['points_per_daily']} Berries",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Deadline",
            value="Before tomorrow's challenge!",
            inline=True
        )
        
        embed.set_footer(text=f"Category: {challenge.get('category', 'General').title()} | Theme: {current_theme.replace('_', ' ').title()}")
        
        try:
            message = await channel.send(embed=embed)
            await message.add_reaction("⚓")
            
            # Update config with current theme
            await self.config.guild(guild).current_daily.set(today)
            await self.config.guild(guild).current_theme.set(current_theme)
            
        except discord.Forbidden:
            pass

    async def select_themed_challenge(self, theme_data: dict) -> dict:
        """Select appropriate challenge from themed data"""
        # Get all challenge categories for this theme
        challenge_categories = [key for key in theme_data.keys() 
                              if key not in ["theme_info", "trivia_focus", "trivia_boost"]]
        
        if not challenge_categories:
            return {"prompt": "What's your favorite One Piece moment?", "category": "general"}
        
        # Select random category and challenge
        category = random.choice(challenge_categories)
        challenges = theme_data[category]
        challenge = random.choice(challenges)
        challenge["theme_category"] = category
        
        return challenge

    def get_theme_color(self, theme_name: str) -> discord.Color:
        """Get color for each theme"""
        theme_colors = {
            "theory_monday": discord.Color.purple(),      # Purple for mystery
            "trivia_tuesday": discord.Color.blue(),       # Blue for knowledge
            "whatif_wednesday": discord.Color.orange(),   # Orange for creativity
            "throwback_thursday": discord.Color.green(),  # Green for nostalgia
            "fight_friday": discord.Color.red(),          # Red for battles
            "creative_saturday": discord.Color.gold(),    # Gold for creativity
            "summary_sunday": discord.Color.blurple()     # Discord blurple for community
        }
        return theme_colors.get(theme_name, discord.Color.red())

    @tasks.loop(minutes=5)
    async def daily_challenge_task(self):
        """Enhanced daily challenge task with theme awareness"""
        for guild_id in await self.config.all_guilds():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            guild_config = await self.config.guild(guild).all()
            if not guild_config["daily_challenges"]:
                continue
                
            # Check if it's time for daily challenge
            now = datetime.now()
            target_time = datetime.strptime(guild_config["challenge_time"], "%H:%M").time()
            
            if (now.time().hour == target_time.hour and 
                now.time().minute == target_time.minute and
                guild_config["current_daily"] != now.strftime("%Y-%m-%d")):
                
                await self.post_daily_challenge(guild)

    @tasks.loop(minutes=30)
    async def auto_trivia_task(self):
        """Enhanced auto trivia with theme awareness and boost days"""
        for guild_id in await self.config.all_guilds():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            guild_config = await self.config.guild(guild).all()
            if not guild_config["auto_trivia"]:
                continue
                
            # Check theme boost days (Tuesday=1, Friday=4)
            current_day = datetime.now().weekday()
            boost_days = guild_config.get("trivia_boost_days", [1, 4])
            
            # Adjust interval for boost days
            base_interval = guild_config["trivia_interval"]
            if current_day in boost_days:
                interval = base_interval // 2  # Double frequency on boost days
            else:
                interval = base_interval
            
            # Check if enough time has passed since last trivia
            now = datetime.now()
            last_trivia = await self.config.guild(guild).get_raw("last_auto_trivia", default=None)
            
            if last_trivia is None:
                await self.post_themed_auto_trivia(guild)
                await self.config.guild(guild).set_raw("last_auto_trivia", value=now.timestamp())
                continue
            
            last_trivia_time = datetime.fromtimestamp(last_trivia)
            time_diff = (now - last_trivia_time).total_seconds()
            
            if time_diff >= interval:
                await self.post_themed_auto_trivia(guild)
                await self.config.guild(guild).set_raw("last_auto_trivia", value=now.timestamp())

    async def post_themed_auto_trivia(self, guild: discord.Guild):
        """Post auto trivia with theme awareness"""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["trivia_channel"]
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        # Get current theme and focus
        current_theme = self.get_current_theme(guild_config.get("theme_override"))
        theme_data = self.themed_challenges.get(current_theme, {})
        trivia_focus = theme_data.get("trivia_focus", [])
        
        # Select difficulty and category
        difficulties = list(self.trivia_data.keys())
        if not difficulties:
            return
            
        difficulty = random.choice(difficulties)
        trivia_set = self.trivia_data[difficulty]
        
        # Try to use themed category if available
        if trivia_focus:
            available_categories = [cat for cat in trivia_focus if cat in trivia_set]
            if available_categories:
                category = random.choice(available_categories)
            else:
                category = random.choice(list(trivia_set.keys()))
        else:
            category = random.choice(list(trivia_set.keys()))
        
        question_data = random.choice(trivia_set[category])
        
        # Enhanced embed for themed trivia
        theme_info = theme_data.get("theme_info", {})
        theme_emoji = theme_info.get("emoji", "🧠")
        
        embed = discord.Embed(
            title=f"{theme_emoji} Themed Auto Trivia!",
            description=question_data["question"],
            color=self.get_theme_color(current_theme)
        )
        embed.add_field(name="⏰ Time Limit", value="45 seconds", inline=True)
        embed.add_field(name="🏆 Points", value=str(self.constants["point_values"][f"{difficulty}_trivia"]), inline=True)
        embed.add_field(name="🎯 Difficulty", value=difficulty.title(), inline=True)
        embed.add_field(name="📂 Category", value=question_data.get("category", "General").title(), inline=True)
        
        if theme_info.get("name"):
            embed.add_field(name="🎭 Today's Theme", value=theme_info["name"], inline=True)
        
        embed.set_footer(text="First to answer correctly wins! 🏴‍☠️")
        
        try:
            message = await channel.send("🚨 **THEMED TRIVIA ATTACK!** 🚨", embed=embed)
            
            def check(m):
                return (m.channel == channel and 
                       any(answer.lower() in m.content.lower() 
                           for answer in question_data["answers"]))
            
            try:
                response = await self.bot.wait_for('message', timeout=45.0, check=check)
                
                # Award points with theme bonus
                base_points = self.constants["point_values"][f"{difficulty}_trivia"]
                theme_bonus = 5 if current_theme in ["trivia_tuesday", "fight_friday"] else 0
                total_points = base_points + theme_bonus + 5  # +5 speed bonus
                
                await self.add_user_points(response.author, total_points)
                
                # Update user stats
                user_data = await self.config.user(response.author).all()
                await self.config.user(response.author).trivia_correct.set(user_data["trivia_correct"] + 1)
                await self.config.user(response.author).trivia_attempted.set(user_data["trivia_attempted"] + 1)
                
                # Winner embed
                win_embed = discord.Embed(
                    title="🎉 Themed Trivia Winner!",
                    description=f"{response.author.mention} got it right!",
                    color=discord.Color.green()
                )
                win_embed.add_field(name="✅ Answer", value=question_data["answers"][0].title(), inline=True)
                win_embed.add_field(name="🏆 Points Earned", value=str(total_points), inline=True)
                
                if theme_bonus > 0:
                    win_embed.add_field(name="🎭 Theme Bonus", value=f"+{theme_bonus} points", inline=True)
                
                await channel.send(embed=win_embed)
                
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ No One Got It!",
                    description=f"The answer was: **{question_data['answers'][0].title()}**",
                    color=discord.Color.orange()
                )
                timeout_embed.add_field(name="🤔 Better luck next time!", value="Stay sharp for the next themed trivia!", inline=False)
                await channel.send(embed=timeout_embed)
                
        except discord.Forbidden:
            pass

    async def post_weekly_challenge(self, guild: discord.Guild):
        """Post this week's challenge"""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["challenge_channel"]
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return
            
        # Select random weekly challenge
        if not self.weekly_challenges:
            return
            
        challenge_type = random.choice(list(self.weekly_challenges.keys()))
        challenge = random.choice(self.weekly_challenges[challenge_type])
        this_week = datetime.now().strftime("%Y-W%U")
        
        # Create challenge embed
        embed = discord.Embed(
            title="🌊 Weekly Grand Line Challenge!",
            description=challenge.get("description", challenge.get("title", "Weekly Challenge")),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📅 Duration",
            value=f"{challenge.get('duration', 7)} days",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Reward",
            value=f"{guild_config.get('points_per_weekly', 75)} Berries",
            inline=True
        )
        
        embed.add_field(
            name="🎭 Theme",
            value=challenge.get("theme", "Adventure"),
            inline=True
        )
        
        embed.add_field(
            name="📝 How to Participate",
            value="React with 🏴‍☠️ and submit your entry!",
            inline=False
        )
        
        embed.set_footer(text=f"Challenge Type: {challenge.get('category', 'Contest').title()}")
        
        try:
            message = await channel.send(embed=embed)
            await message.add_reaction("🏴‍☠️")
            
            # Update config
            await self.config.guild(guild).current_weekly.set(this_week)
            
        except discord.Forbidden:
            pass

    async def post_auto_trivia(self, guild: discord.Guild):
        """Post automatic trivia question"""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["trivia_channel"]
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return
            
        # Select random difficulty and category
        difficulties = list(self.trivia_data.keys())
        if not difficulties:
            return
            
        difficulty = random.choice(difficulties)
        trivia_set = self.trivia_data[difficulty]
        
        if not trivia_set:
            return
            
        category = random.choice(list(trivia_set.keys()))
        question_data = random.choice(trivia_set[category])
        
        # Create trivia embed
        embed = discord.Embed(
            title="🧠 Auto One Piece Trivia!",
            description=question_data["question"],
            color=discord.Color(self.constants["difficulty_colors"][difficulty])
        )
        embed.add_field(name="⏰ Time Limit", value="45 seconds", inline=True)
        embed.add_field(name="🏆 Points", value=str(self.constants["point_values"][f"{difficulty}_trivia"]), inline=True)
        embed.add_field(name="📂 Category", value=question_data.get("category", "General").title(), inline=True)
        embed.add_field(name="🎯 Difficulty", value=difficulty.title(), inline=True)
        embed.set_footer(text="First to answer correctly wins! 🏴‍☠️")
        
        try:
            message = await channel.send("🚨 **SUDDEN TRIVIA ATTACK!** 🚨", embed=embed)
            
            def check(m):
                return (m.channel == channel and 
                       any(answer.lower() in m.content.lower() 
                           for answer in question_data["answers"]))
            
            try:
                response = await self.bot.wait_for('message', timeout=45.0, check=check)
                
                # Award points
                points = self.constants["point_values"][f"{difficulty}_trivia"]
                await self.add_user_points(response.author, points)
                
                # Update user stats
                user_data = await self.config.user(response.author).all()
                await self.config.user(response.author).trivia_correct.set(user_data["trivia_correct"] + 1)
                await self.config.user(response.author).trivia_attempted.set(user_data["trivia_attempted"] + 1)
                
                # Winner embed
                win_embed = discord.Embed(
                    title="🎉 Lightning Round Winner!",
                    description=f"{response.author.mention} was fastest!",
                    color=discord.Color.green()
                )
                win_embed.add_field(name="✅ Answer", value=question_data["answers"][0].title(), inline=True)
                win_embed.add_field(name="🏆 Points Earned", value=str(points), inline=True)
                win_embed.add_field(name="⚡ Speed Bonus", value="+5 points", inline=True)
                
                # Speed bonus for auto trivia
                await self.add_user_points(response.author, 5)
                
                await channel.send(embed=win_embed)
                
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ No One Got It!",
                    description=f"The answer was: **{question_data['answers'][0].title()}**",
                    color=discord.Color.orange()
                )
                timeout_embed.add_field(name="🤔 Better luck next time!", value="Stay sharp for the next surprise trivia!", inline=False)
                await channel.send(embed=timeout_embed)
                
        except discord.Forbidden:
            pass

    @commands.group(name="onepiece", aliases=["op"])
    async def onepiece(self, ctx):
        """One Piece engagement system with automatic themed daily rotation!"""
        if ctx.invoked_subcommand is None:
            # Get current theme info
            current_theme = self.get_current_theme()
            theme_data = self.themed_challenges.get(current_theme, {})
            theme_info = theme_data.get("theme_info", {})
            
            embed = discord.Embed(
                title="🏴‍☠️ One Piece Engagement Hub",
                description="Welcome to the ultimate themed One Piece experience!",
                color=self.get_theme_color(current_theme)
            )
            
            if theme_info:
                embed.add_field(
                    name=f"{theme_info.get('emoji', '🎯')} Today's Theme: {theme_info.get('name', 'Daily Challenge')}",
                    value=theme_info.get("description", "Themed One Piece content"),
                    inline=False
                )
            
            embed.add_field(
                name="🎯 Daily Challenges",
                value="`[p]op challenge` - Today's themed challenge\n"
                      "`[p]op challenges` - Challenge management\n"
                      "`[p]op themes` - Theme information",
                inline=True
            )
            embed.add_field(
                name="🧠 Trivia Games",
                value="`[p]op trivia` - Start themed trivia\n"
                      "`[p]op quiz [difficulty]` - Quick quiz",
                inline=True
            )
            embed.add_field(
                name="📊 Stats & Info",
                value="`[p]op stats` - Your stats\n"
                      "`[p]op leaderboard` - Top players\n"
                      "`[p]op schedule` - Weekly schedule",
                inline=True
            )
            await ctx.send(embed=embed)

    @onepiece.command(name="themes")
    async def show_themes(self, ctx):
        """Show the weekly themed schedule"""
        embed = discord.Embed(
            title="🗓️ Weekly Themed Schedule",
            description="Each day has a special theme with curated content!",
            color=discord.Color.blurple()
        )
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day_num, day_name in enumerate(days):
            theme_name = self.weekly_themes[day_num]
            theme_data = self.themed_challenges.get(theme_name, {})
            theme_info = theme_data.get("theme_info", {})
            
            emoji = theme_info.get("emoji", "🎯")
            name = theme_info.get("name", theme_name.replace("_", " ").title())
            description = theme_info.get("description", "Themed content")
            focus = theme_info.get("focus", "One Piece discussions")
            
            embed.add_field(
                name=f"{emoji} **{day_name}** - {name}",
                value=f"{description}\n*Focus: {focus}*",
                inline=False
            )
        
        current_theme = self.get_current_theme()
        embed.set_footer(text=f"Today's theme: {current_theme.replace('_', ' ').title()}")
        
        await ctx.send(embed=embed)

    @onepiece.command(name="schedule")
    async def show_schedule(self, ctx):
        """Show the weekly schedule (alias for themes)"""
        await self.show_themes(ctx)

    @onepiece.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx, scope: str = "server"):
        """Show the One Piece trivia leaderboard"""
        if scope.lower() not in ["server", "global"]:
            scope = "server"
            
        if scope.lower() == "server":
            # Server leaderboard
            all_users = await self.config.all_users()
            server_members = [member.id for member in ctx.guild.members]
            
            # Filter to only server members
            server_data = {user_id: data for user_id, data in all_users.items() 
                          if user_id in server_members and data.get('total_points', 0) > 0}
        else:
            # Global leaderboard
            server_data = await self.config.all_users()
            server_data = {user_id: data for user_id, data in server_data.items() 
                          if data.get('total_points', 0) > 0}
        
        if not server_data:
            await ctx.send("No one has earned points yet! Start playing trivia! 🏴‍☠️")
            return
        
        # Sort by total points
        sorted_users = sorted(server_data.items(), key=lambda x: x[1]['total_points'], reverse=True)
        
        embed = discord.Embed(
            title=f"🏆 {scope.title()} One Piece Leaderboard",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        for i, (user_id, data) in enumerate(sorted_users[:10], 1):
            user = self.bot.get_user(user_id)
            if user is None:
                continue
                
            points = data['total_points']
            accuracy = 0
            if data.get('trivia_attempted', 0) > 0:
                accuracy = (data.get('trivia_correct', 0) / data['trivia_attempted']) * 100
            
            # Get rank title
            rank_title = self.get_rank_title(points)
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            leaderboard_text += f"{medal} **{user.display_name}**\n"
            leaderboard_text += f"   💰 {points:,} berries | 🎯 {accuracy:.1f}% | {rank_title}\n\n"
        
        embed.description = leaderboard_text
        
        # Add user's position if not in top 10
        user_position = None
        for i, (user_id, _) in enumerate(sorted_users, 1):
            if user_id == ctx.author.id:
                user_position = i
                break
        
        if user_position and user_position > 10:
            user_data = await self.config.user(ctx.author).all()
            user_accuracy = 0
            if user_data['trivia_attempted'] > 0:
                user_accuracy = (user_data['trivia_correct'] / user_data['trivia_attempted']) * 100
            
            embed.add_field(
                name="📍 Your Position",
                value=f"#{user_position} - {user_data['total_points']:,} berries ({user_accuracy:.1f}%)",
                inline=False
            )
        
        await ctx.send(embed=embed)

    def get_rank_title(self, points: int) -> str:
        """Get rank title based on points"""
        rank_thresholds = [
            (20000, "Pirate King Candidate"),
            (10000, "Yonko Level"),
            (5000, "Emperor Commander"),
            (2000, "Warlord Level"),
            (1000, "Supernova"),
            (500, "New World Pirate"),
            (300, "Grand Line Traveler"),
            (100, "East Blue Veteran"),
            (0, "Rookie Pirate")
        ]
        
        for threshold, title in rank_thresholds:
            if points >= threshold:
                return title
        return "Rookie Pirate"

    @onepiece.command(name="daily")
    async def today_challenge(self, ctx):
        """Show today's challenge if there is one"""
        guild_config = await self.config.guild(ctx.guild).all()
        channel_id = guild_config["challenge_channel"]
        
        if not channel_id:
            await ctx.send("❌ No challenge channel set! Ask an admin to set one up.")
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        current_daily = guild_config.get("current_daily")
        
        if current_daily != today:
            await ctx.send("🤔 No challenge posted today yet! Check back later or ask an admin to post one.")
            return
        
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            await ctx.send(f"📍 Today's challenge is in {channel.mention}!")
        else:
            await ctx.send("❌ Challenge channel not found!")

    @onepiece.command(name="profile", aliases=["rank"])
    async def user_profile(self, ctx, user: discord.Member = None):
        """Show detailed user profile and achievements"""
        if user is None:
            user = ctx.author
            
        user_data = await self.config.user(user).all()
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {user.display_name}'s Pirate Profile",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        # Basic stats
        points = user_data['total_points']
        rank_title = self.get_rank_title(points)
        
        embed.add_field(
            name="👑 Pirate Rank",
            value=rank_title,
            inline=True
        )
        
        embed.add_field(
            name="💰 Total Berries",
            value=f"{points:,}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 Daily Streak",
            value=f"{user_data['daily_streak']} days",
            inline=True
        )
        
        # Trivia stats
        if user_data['trivia_attempted'] > 0:
            accuracy = (user_data['trivia_correct'] / user_data['trivia_attempted']) * 100
        else:
            accuracy = 0
            
        embed.add_field(
            name="🧠 Trivia Stats",
            value=f"✅ {user_data['trivia_correct']} correct\n"
                  f"❓ {user_data['trivia_attempted']} attempted\n"
                  f"🎯 {accuracy:.1f}% accuracy",
            inline=True
        )
        
        # Achievements
        achievements = user_data.get('achievements', [])
        if achievements:
            embed.add_field(
                name="🏆 Recent Achievements",
                value="\n".join(achievements[-3:]),  # Show last 3
                inline=True
            )
        else:
            embed.add_field(
                name="🏆 Achievements",
                value="None yet - keep playing!",
                inline=True
            )
        
        # Progress to next rank
        current_points = points
        next_rank_points = None
        for threshold, title in [(100, "East Blue Veteran"), (300, "Grand Line Traveler"), 
                                (500, "New World Pirate"), (1000, "Supernova"), 
                                (2000, "Warlord Level"), (5000, "Emperor Commander"),
                                (10000, "Yonko Level"), (20000, "Pirate King Candidate")]:
            if current_points < threshold:
                next_rank_points = threshold
                next_rank_title = title
                break
        
        if next_rank_points:
            progress = current_points / next_rank_points
            progress_bar = "▓" * int(progress * 10) + "░" * (10 - int(progress * 10))
            embed.add_field(
                name="📈 Progress to Next Rank",
                value=f"{progress_bar}\n{current_points}/{next_rank_points} to {next_rank_title}",
                inline=False
            )
        
        embed.set_footer(text=f"Nakama since")
        
        await ctx.send(embed=embed)

    @onepiece.group(name="challenges")
    @checks.admin_or_permissions(manage_guild=True)
    async def challenges_admin(self, ctx):
        """Challenge administration commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @challenges_admin.command(name="channel")
    async def set_challenge_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the challenges channel"""
        if channel is None:
            channel = ctx.channel
            
        await self.config.guild(ctx.guild).challenge_channel.set(channel.id)
        await ctx.send(f"✅ Challenge channel set to {channel.mention}")

    @challenges_admin.command(name="reload")
    async def reload_data(self, ctx):
        """Reload all data files"""
        try:
            self.load_all_data()
            await ctx.send("✅ All data files reloaded successfully!")
        except Exception as e:
            await ctx.send(f"❌ Error reloading data: {str(e)}")

    @challenges_admin.command(name="time")
    async def set_challenge_time(self, ctx, time: str):
        """Set daily challenge time (24hr format: HH:MM)"""
        try:
            datetime.strptime(time, "%H:%M")
            await self.config.guild(ctx.guild).challenge_time.set(time)
            await ctx.send(f"✅ Daily challenge time set to {time}")
        except ValueError:
            await ctx.send("❌ Invalid time format. Use HH:MM (24hr format)")

    @challenges_admin.command(name="toggle")
    async def toggle_challenges(self, ctx, challenge_type: str):
        """Toggle daily or weekly challenges"""
        if challenge_type.lower() == "daily":
            current = await self.config.guild(ctx.guild).daily_challenges()
            await self.config.guild(ctx.guild).daily_challenges.set(not current)
            status = "enabled" if not current else "disabled"
            await ctx.send(f"✅ Daily challenges {status}")
        elif challenge_type.lower() == "weekly":
            current = await self.config.guild(ctx.guild).weekly_challenges()
            await self.config.guild(ctx.guild).weekly_challenges.set(not current)
            status = "enabled" if not current else "disabled"
            await ctx.send(f"✅ Weekly challenges {status}")
        else:
            await ctx.send("❌ Use 'daily' or 'weekly'")

    @challenges_admin.command(name="force")
    async def force_challenge(self, ctx, challenge_type: str):
        """Force post a challenge now"""
        if challenge_type.lower() == "daily":
            await self.post_daily_challenge(ctx.guild)
            await ctx.send("✅ Daily challenge posted!")
        elif challenge_type.lower() == "weekly":
            await self.post_weekly_challenge(ctx.guild)
            await ctx.send("✅ Weekly challenge posted!")
        else:
            await ctx.send("❌ Use 'daily' or 'weekly'")

    @challenges_admin.command(name="status")
    async def challenge_status(self, ctx):
        """Show current challenge settings"""
        config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Challenges Status",
            color=discord.Color.gold()
        )
        
        channel = ctx.guild.get_channel(config.get("challenge_channel"))
        embed.add_field(
            name="📍 Channel",
            value=channel.mention if channel else "Not set",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Daily Time",
            value=config.get("challenge_time", "12:00"),
            inline=True
        )
        
        # Use .get() with defaults to handle missing keys
        daily_status = "✅" if config.get("daily_challenges", True) else "❌"
        weekly_status = "✅" if config.get("weekly_challenges", False) else "❌"
        
        embed.add_field(
            name="📅 Status",
            value=f"Daily: {daily_status}\nWeekly: {weekly_status}",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Rewards",
            value=f"Daily: {config.get('points_per_daily', 10)} Berries\nWeekly: {config.get('points_per_weekly', 50)} Berries",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @onepiece.group(name="trivia_admin", aliases=["tadmin"])
    @checks.admin_or_permissions(manage_guild=True)
    async def trivia_admin(self, ctx):
        """Auto trivia administration commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @trivia_admin.command(name="channel")
    async def set_trivia_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the auto trivia channel"""
        if channel is None:
            channel = ctx.channel
            
        await self.config.guild(ctx.guild).trivia_channel.set(channel.id)
        await ctx.send(f"✅ Auto trivia channel set to {channel.mention}")

    @trivia_admin.command(name="toggle")
    async def toggle_auto_trivia(self, ctx):
        """Toggle auto trivia on/off"""
        current = await self.config.guild(ctx.guild).auto_trivia()
        await self.config.guild(ctx.guild).auto_trivia.set(not current)
        status = "enabled" if not current else "disabled"
        await ctx.send(f"✅ Auto trivia {status}")

    @trivia_admin.command(name="interval")
    async def set_trivia_interval(self, ctx, minutes: int):
        """Set auto trivia interval in minutes (minimum 30)"""
        if minutes < 30:
            await ctx.send("❌ Minimum interval is 30 minutes")
            return
            
        seconds = minutes * 60
        await self.config.guild(ctx.guild).trivia_interval.set(seconds)
        await ctx.send(f"✅ Auto trivia interval set to {minutes} minutes")

    @trivia_admin.command(name="force")
    async def force_auto_trivia(self, ctx):
        """Force post an auto trivia question now"""
        await self.post_auto_trivia(ctx.guild)
        await ctx.send("✅ Auto trivia posted!")

    @trivia_admin.command(name="status")
    async def trivia_status(self, ctx):
        """Show auto trivia settings"""
        config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="🧠 Auto Trivia Settings",
            color=discord.Color.blue()
        )
        
        trivia_channel = ctx.guild.get_channel(config["trivia_channel"])
        embed.add_field(
            name="📍 Channel",
            value=trivia_channel.mention if trivia_channel else "Not set",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Status",
            value="✅ Enabled" if config["auto_trivia"] else "❌ Disabled",
            inline=True
        )
        
        interval_minutes = config["trivia_interval"] // 60
        embed.add_field(
            name="⏰ Interval",
            value=f"{interval_minutes} minutes",
            inline=True
        )
        
        # Show last trivia time if available
        last_trivia = await self.config.guild(ctx.guild).get_raw("last_auto_trivia", default=None)
        if last_trivia:
            last_time = datetime.fromtimestamp(last_trivia)
            embed.add_field(
                name="📅 Last Trivia",
                value=f"<t:{int(last_trivia)}:R>",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @onepiece.command(name="trivia")
    async def trivia_game(self, ctx, difficulty: str = "easy", category: str = "general"):
        """Start a trivia game"""
        if difficulty not in self.trivia_data:
            difficulty = "easy"
            
        trivia_set = self.trivia_data[difficulty]
        if category not in trivia_set:
            category = random.choice(list(trivia_set.keys()))
            
        question_data = random.choice(trivia_set[category])
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {difficulty.title()} One Piece Trivia",
            description=question_data["question"],
            color=discord.Color(self.constants["difficulty_colors"][difficulty])
        )
        embed.add_field(name="⏰ Time Limit", value="30 seconds", inline=True)
        embed.add_field(name="🏆 Points", value=str(self.constants["point_values"][f"{difficulty}_trivia"]), inline=True)
        embed.add_field(name="📂 Category", value=question_data.get("category", "General").title(), inline=True)
        
        message = await ctx.send(embed=embed)
        
        def check(m):
            return (m.channel == ctx.channel and 
                   any(answer.lower() in m.content.lower() 
                       for answer in question_data["answers"]))
        
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            
            # Award points
            points = self.constants["point_values"][f"{difficulty}_trivia"]
            await self.add_user_points(response.author, points)
            
            # Update user stats
            user_data = await self.config.user(response.author).all()
            await self.config.user(response.author).trivia_correct.set(user_data["trivia_correct"] + 1)
            await self.config.user(response.author).trivia_attempted.set(user_data["trivia_attempted"] + 1)
            
            # Winner embed
            win_embed = discord.Embed(
                title="🎉 Correct!",
                description=f"{response.author.mention} got it right!",
                color=discord.Color.green()
            )
            win_embed.add_field(name="✅ Answer", value=question_data["answers"][0].title(), inline=True)
            win_embed.add_field(name="🏆 Points Earned", value=str(points), inline=True)
            
            await ctx.send(embed=win_embed)
            
        except asyncio.TimeoutError:
            # Update attempted count
            await self.update_user_trivia_attempts(ctx.author)
            
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The answer was: **{question_data['answers'][0].title()}**",
                color=discord.Color.orange()
            )
            await ctx.send(embed=timeout_embed)

    async def add_user_points(self, user: discord.User, points: int):
        """Add points to a user"""
        current_points = await self.config.user(user).total_points()
        await self.config.user(user).total_points.set(current_points + points)

    async def update_user_trivia_attempts(self, user: discord.User):
        """Update user's trivia attempt count"""
        attempts = await self.config.user(user).trivia_attempted()
        await self.config.user(user).trivia_attempted.set(attempts + 1)

    @onepiece.command(name="stats")
    async def user_stats(self, ctx, user: discord.Member = None):
        """Show user statistics"""
        if user is None:
            user = ctx.author
            
        user_data = await self.config.user(user).all()
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {user.display_name}'s Stats",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💰 Total Berries",
            value=f"{user_data['total_points']:,}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 Daily Streak",
            value=f"{user_data['daily_streak']} days",
            inline=True
        )
        
        # Calculate trivia accuracy
        if user_data['trivia_attempted'] > 0:
            accuracy = (user_data['trivia_correct'] / user_data['trivia_attempted']) * 100
        else:
            accuracy = 0
            
        embed.add_field(
            name="🧠 Trivia Accuracy",
            value=f"{accuracy:.1f}% ({user_data['trivia_correct']}/{user_data['trivia_attempted']})",
            inline=True
        )
        
        if user_data['achievements']:
            embed.add_field(
                name="🏆 Achievements",
                value="\n".join(user_data['achievements'][:5]),
                inline=False
            )
        
        await ctx.send(embed=embed)
