# Compatibility audit: Red 3.5.24

Originally audited on branch `compat-audit`, from `main` at `ded33d5`. Status last updated at `e082bf8`, when the audit's checks were rerun. Line numbers are from the original audit and may have moved.

**Target:** Red-DiscordBot 3.5.24, which pins discord.py 2.7.1 and aiohttp 3.9.5 and requires Python below 3.12. All checks ran on Python 3.11.15.

## Status

**Fixed:**
- Every crash found in cogs that can load
- All metadata findings
- `utcnow()` times in `beri_cautions` and `buckshot`
- `polls` requirements and outdated text

**Still open:**
- **`onepiecemods` can't load** because of its syntax errors, and has never had a full audit.
- **`BB` blocks the event loop** with synchronous `requests` calls.
- **`crewbattles` and `staffapplications`** do blocking file or database work on the event loop.
- **The remaining deprecated calls and leftover code** listed below.

Nothing here has been tested on a live bot.

## How this was checked

| Check | Coverage |
|---|---|
| Parse every tracked `.py` file with Python 3.11 | All 164 files |
| Import each cog and run its `setup()` with a stub bot | All 28 cogs, with declared requirements installed |
| Resolve `discord.*`, `commands.*`, `checks.*` and imports against the installed packages | All files that parse |
| Compare `ctx.*`, `interaction.*` and `bot.*` members, and `send`/`edit`/UI keywords, with the real classes | All files that parse |
| Search for removed APIs, blocking calls, unawaited calls and naive/aware datetime mixes | All files that parse |
| Read every `info.json` with Downloader's own `Installable` class | All 28 cogs |
| Existing test suites | `aetherbound` 164, `staffapplications` 95, `mrwhite` 127 all pass; `guesscandy` and `onepieceguess` reported OK in the original audit |

**Not covered:**
- Nothing ran on a live bot. `cog_load` and command bodies ran only in the test suites and in targeted checks of the fixes.
- The scan can't identify the type of most variables, so a wrong attribute on something like `user` or `channel` can be missed.
- The blocking search only looks for direct calls, so file I/O inside synchronous helpers can be missed.
- `onepiecemods/onepiecemods.py` can't be parsed, so it got only a text search.

## Will crash

### Open: `onepiecemods` can't load

`onepiecemods/onepiecemods.py:516` raises `IndentationError` on import, so `[p]load onepiecemods` fails. This isn't a single bad line. Blocks starting with `serious = await self.config.guild(ctx.guild).serious_mode()` were pasted at the wrong indent throughout the file. Parse errors continue at least as far as line 1537. Fixing them means restoring each block's intended logic, and the file needs a full audit afterwards.

### Fixed

| Cog | Location | Problem | Commit |
|---|---|---|---|
| `BB` | `BB/deathbattle.py:10-11` | Undeclared `requests` and `Pillow` stopped it loading on a normal install. Now declared in a new `info.json` | `3467991` |
| `BB` | `BB/deathbattle.py:773`, `:896` | `discord.Color.gray()` doesn't exist | `3323a24` |
| `report` | `report/advancedreport.py:367` | A non-persistent view made `cog_load` skip registering "Report Message" | `3a24106` |
| `report` | `report/advancedreport.py:46` | `discord.timedelta` doesn't exist, so the Mute button always failed | `3a24106` |
| `enchantedlogs` | `enchantedlogs/enhancedmodlog.py:212`, `:216` | Treated Red's `int` `Case.until` as a `datetime` | `cb48c9c` |
| `enchantedlogs` | `enchantedlogs/enhancedmodlog.py:58`, `:177` | `self.bot.logger` doesn't exist | `bebeb0f` |
| `gacha` | `gacha/enhancedgacha.py:226` | `member.avatar.url` failed for default avatars | `9d3037f` |
| `doublepost` | `doublepost/consecutivefilter.py:435` | `self.bot.is_command` doesn't exist, which logged a traceback for ordinary messages | `8beca0e` |

`BB` still needs its requirements installed, which Downloader now does. Without `requests`, a manual copy of the cog still fails to load.

## Deprecated

### `datetime.utcnow()`

Deprecated from Python 3.12. Where the value goes through `.timestamp()`, is shown to users, or is passed to Discord, times are off by the host's UTC offset unless the host runs in UTC.

| Cog | Locations | Status |
|---|---|---|
| `beri_cautions` | `beri_cautions.py` (18 calls) | **Fixed in `e93d2e6`.** Also corrected the length of automatic timeouts on non-UTC hosts |
| `buckshot` | `buckshot.py` (7 calls) | **Fixed in `e93d2e6`** |
| `enchantedlogs` | `enhancedmodlog.py:212` | **Fixed in `cb48c9c`** |
| `afk` | `CustomAFK.py:50, 67, 91` | Open. Elapsed times are consistent, apart from daylight-saving changes |
| `Suggestion` | `utils.py:11, 23` | Open. Consistent; stored as naive ISO strings |
| `gacha` | `enhancedgacha.py:51` | Open. No effect in practice: nothing sets `cooldownspawn`, so this line never runs |

**Existing data:** on a non-UTC host, warning expiries and holds stored in `beri_cautions` before `e93d2e6` keep their shifted times until they end. They aren't migrated.

### Blocking the event loop: open

| Cog | Locations | Problem |
|---|---|---|
| `BB` | `deathbattle.py:103`, called from `:169` | Synchronous `requests.get` for each avatar (2-second timeout), plus image work; can freeze the bot for several seconds per battle |
| `crewbattles` | `data_manager.py:113, 197, 371, 375, 507, 514, 577`; `migration.py:121`; `tournament.py:137, 170` | `open()` with `json.load`/`json.dump` inside async functions; gets worse as data grows |
| `staffapplications` | `store.py:53`, used directly from the cog | Synchronous SQLite on the event loop. Low impact for small data and documented as a design choice. `aetherbound` and `voyage` already avoid this with `asyncio.to_thread` and `aiosqlite` |

### `bot.loop`: open

These work on 3.5.24, because Red loads cogs after login, when the loop is set. `asyncio.create_task` is the modern form, and these tasks aren't always kept or cancelled on unload.

- `beri_cautions/beri_cautions.py:76-77`
- `crewbattles/crew.py:65`, `crewbattles/tournament.py:68`
- `enchantedlogs/enhancedmodlog.py:48`, `:168`
- `onepiecemods/__init__.py:14`, `onepiecemods/onepiecemods.py:1269`

### `asyncio.get_event_loop()`: open

These work, because each call runs inside a running loop. `get_running_loop()` is the modern form.

- `beri/casino.py:432, 434, 436`
- `beri_cautions/beri_cautions.py:426, 440`
- `optcg/utils.py:30`
- `qimposters/onepiece_imposters.py:814, 817`

## Cosmetic

### Metadata

Red's Downloader doesn't reject bad or missing `info.json` files. It logs any JSON error and uses defaults, so these cogs still installed, but silently lost their requirements, version limits, install message and data statement.

| Cog | Problem | Status |
|---|---|---|
| `BB`, `beri` | No `info.json` | **Fixed in `3467991`** |
| `buckshot` | A comment line made `info.json` invalid JSON | **Fixed in `3467991`** |
| `doublepost` | `Info.json` wasn't found on Linux | **Fixed in `3467991`** |
| `Suggestion`, `enchantedlogs`, `optcg`, `BB`, `beri` | No end-user data statement | **Fixed in `3467991`** |
| `afk` | Statement only in `__init__.py` | **Fixed in `3467991`**, but see below |
| `afk`, `crewbattles` and all others below 3.5.24 | `min_bot_version` missing or low | **Fixed in `3467991`:** every cog is now 3.5.24 |
| `polls`, `onepiecemods` | Listed `discord.py` in `requirements`. Cogs must not list discord.py or Red, because Red provides them | **Fixed in `7744ec5`** |
| `polls` | Outdated Components V2, version, voting and `quickpoll` text | **Fixed in `0cb9397` and `e082bf8`** |
| `mrwhite` | `min_python_version` is `3.11.15`, which blocks installs on earlier 3.11 releases | Open |

**Inaccurate data statements, found while fixing the above and still open:**
- `afk/__init__.py:3` describes adventure data, bounties and crews, which the cog doesn't store. Its `info.json` is now accurate, so the two disagree.
- `crewbattles/info.json` says the cog stores no end-user data, but its `data_manager.py` and `tournament.py` read and write data files. Those files' contents weren't reviewed.

There's also no repository-level `info.json`. Downloader tolerates this too, so it only loses the repo's own description and install message.

### Leftover code: open

- `gacha/enhancedgacha.py:426-427`: a second, synchronous `setup` with an unawaited `add_cog`. Nothing calls it, because `gacha/__init__.py` has its own.
- `polls/v2poll.py:146`: `create_sprite_select_menu` builds a raw component dictionary and is never called.
- `crewbattles/setup.py`: its only caller is commented out at `crewbattles/crew.py:968-969`.
- `crewbattles/setup.py:8`, `crewbattles/ui.py:9`, `report/advancedreport.py:2`, `onepiecemods/utils/config_manager.py:3`, `onepiecemods/utils/hierarchy.py:3`: import `commands` from `discord.ext`. No registered command uses it in the cogs that load; `onepiecemods` couldn't be checked.
- `beri_cautions.py` at the repo root: not a package, so Downloader ignores it. It's a separate copy and still has the 18 `utcnow()` calls fixed in the package.

### Repo tooling: open

- `guesscandy/requirements-dev.txt:1` pins discord.py 2.6.3, while Red 3.5.24 pins 2.7.1.
- `.github/workflows/repohelp.yml` targets the deleted `repohelp/` directory.

## All cogs

Current state. Every cog has an `__init__.py`, an `info.json` that Downloader can read, `min_bot_version` 3.5.24 and an end-user data statement. "Loads" means the import and stub `setup()` both passed with the cog's declared requirements installed.

| Cog | `requirements` | Loads | Worst open finding |
|---|---|---|---|
| `aetherbound` | none | Yes | None |
| `afk` | none | Yes | Deprecated |
| `BB` | `requests`, `Pillow` | Yes | Deprecated |
| `beri` | none | Yes | Deprecated |
| `beri_cautions` | none | Yes | Deprecated |
| `bericore` | none | Yes | None |
| `buckshot` | none | Yes | None |
| `crewbattles` | none | Yes | Deprecated |
| `doublepost` | none | Yes | None |
| `enchantedlogs` | none | Yes | Deprecated |
| `gacha` | none | Yes | Deprecated |
| `grill` | none | Yes | None |
| `guesscandy` | `tzdata` | Yes | Cosmetic |
| `mine` | none | Yes | None |
| `mrwhite` | `Pillow>=10.1.0` | Yes | Cosmetic |
| `neko` | `aiohttp>=3.8.0` | Yes | None |
| `onepiecefruit` | `pydantic>=2.0` | Yes | None |
| `onepieceguess` | `aiohttp`, `Pillow>=10.0` | Yes | None |
| `onepiecemods` | none | **No** | **Will crash** |
| `opcsupporters` | none | Yes | None |
| `ope` | `PyYAML>=6.0` | Yes | None |
| `optcg` | `Pillow`, `aiohttp` | Yes | Deprecated |
| `polls` | none | Yes | Cosmetic |
| `qimposters` | none | Yes | Deprecated |
| `report` | none | Yes | Cosmetic |
| `staffapplications` | none | Yes | Deprecated |
| `Suggestion` | none | Yes | Deprecated |
| `voyage` | `aiosqlite` | Yes | None |

`Character Sprite/` holds only images and isn't a cog. `aetherbound` and `staffapplications` use discord.py's newer `LayoutView` components, which 3.5.24 supports.
