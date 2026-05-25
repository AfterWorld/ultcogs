# GeoGuessr Red-Bot Cog

A multiplayer GeoGuessr-style game for Discord using Google Street View.

---

## Features
- 🌍 Random Street View images from 6 world regions
- ⏱️ 90-second countdown timer per round
- 👥 Multiplayer — everyone in the channel can guess
- 📏 Distance-based scoring up to **5,000 pts** per round
- 🏆 All-time server leaderboard + personal stats

---

## Installation

### 1. Add the cog to Red
```
[p]load downloader
[p]repo add geoguessr https://github.com/AfterWorld/geoguessr   # or load locally
[p]cog install geoguessr geoguessr
[p]load geoguessr
```

Or load locally by placing the `geoguessr/` folder in your Red cogs directory:
```
[p]addpath /path/to/parent/folder
[p]load geoguessr
```

### 2. Get Google API Keys

Go to https://console.cloud.google.com and create a project, then enable:
- **Street View Static API** — for fetching the location images
- **Geocoding API** — for converting player guesses (e.g. "Paris, France") to coordinates

Both APIs have a free tier (~$200/month credit from Google).

### 3. Set your keys (admin only)
```
[p]geoset streetview_key YOUR_KEY_HERE
[p]geoset maps_key YOUR_KEY_HERE
```
The bot will delete your message immediately to keep keys out of chat.

---

## Commands

| Command | Description |
|---|---|
| `[p]geo start [region]` | Start a new round |
| `[p]geo guess <location>` | Submit your guess, e.g. `[p]geo guess Tokyo, Japan` |
| `[p]geo stop` | End the round early and reveal the answer |
| `[p]geo leaderboard` | Top 10 all-time scores for the server |
| `[p]geo stats [@user]` | View your (or another user's) stats |
| `[p]geo help` | In-Discord help embed |
| `[p]geoset streetview_key` | (Admin) Set Street View API key |
| `[p]geoset maps_key` | (Admin) Set Geocoding API key |

### Regions
`world` • `europe` • `north_america` • `south_america` • `asia` • `oceania`

---

## Scoring

Scores follow an exponential decay curve similar to GeoGuessr:

| Distance | Score |
|---|---|
| < 1 km | ~5,000 |
| 25 km | ~4,940 |
| 100 km | ~4,759 |
| 500 km | ~3,894 |
| 1,000 km | ~3,033 |
| 2,000 km | ~1,839 |
| 5,000 km | ~83 |

---

## Notes

- The cog filters for Street View coverage using the metadata API (free) before fetching the actual image.
- API keys are stored per-guild in Red's encrypted Config system.
- `aiohttp` is a standard Red dependency and should already be available.