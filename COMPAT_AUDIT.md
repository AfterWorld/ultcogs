# Compatibility audit: Red 3.5.24

Audited on branch `compat-audit`, created from `main` at `ded33d5`. No cog code was changed.

**Target:** Red-DiscordBot 3.5.24, which pins discord.py 2.7.1 and aiohttp 3.9.5 and requires Python below 3.12. All checks ran on Python 3.11.15.

## Summary

- **One cog can't load at all:** `onepiecemods` has syntax errors.
- **One cog fails to load on a normal install:** `BB` imports `requests` and `Pillow`, but has no `info.json` to install them.
- **Five cogs load but have code paths that fail:** `BB`, `report`, `enchantedlogs`, `gacha` and `doublepost`.
- **27 of 28 cogs parse, and every cog except `onepiecemods` and `BB` passed both the import and stub `setup()` checks.** `BB` passes them too once `requests` is installed.

## How this was checked

| Check | Coverage |
|---|---|
| Parse every tracked `.py` file with Python 3.11 | All 164 files |
| Import each cog and run its `setup()` with a stub bot | All 28 cogs, with declared requirements installed |
| Resolve `discord.*`, `commands.*`, `checks.*` and imports against the installed packages | All files that parse |
| Compare `ctx.*`, `interaction.*` and `bot.*` members, and `send`/`edit`/UI keywords, with the real classes | All files that parse |
| Search for removed APIs, blocking calls, unawaited calls and naive/aware datetime mixes | All files that parse |
| Existing test suites | `aetherbound` 164, `staffapplications` 95, `mrwhite` 127 all pass; `guesscandy` and `onepieceguess` report OK |

**Not covered:**
- Nothing ran on a live bot, and `cog_load` and command bodies did not run, apart from the test suites above.
- The scan can't identify the type of most variables, so a wrong attribute on something like `user` or `channel` can be missed.
- The blocking search only looks for direct calls, so file I/O inside synchronous helpers can be missed.
- `onepiecemods/onepiecemods.py` can't be parsed, so it got only a text search.

## Will crash

### `onepiecemods`: cog can't load

`onepiecemods/onepiecemods.py:516` raises `IndentationError` on import, so `[p]load onepiecemods` fails. This isn't a single bad line. Blocks starting with `serious = await self.config.guild(ctx.guild).serious_mode()` were pasted at the wrong indent throughout the file. Parse errors continue at least as far as line 1537. Fixing them means restoring each block's intended logic, and the file needs a full audit afterwards.

### `BB`: cog fails to load on a normal install

| Location | Problem | Result |
|---|---|---|
| `BB/deathbattle.py:10-11` | Imports `PIL` and `requests`; neither ships with Red, and with no `info.json` Downloader can't install them | `ModuleNotFoundError` on load |
| `BB/deathbattle.py:773`, `:896` | `discord.Color.gray()` doesn't exist in 2.7.1 | `AttributeError` when a fruit removal or purchase confirmation times out, so the timeout message is never shown |

### `report`: context menu and mute button don't work

| Location | Problem | Result |
|---|---|---|
| `report/advancedreport.py:367` | `add_view(ReportView(self, {}))` uses a view with a 300-second timeout and no custom IDs. Confirmed to raise `ValueError: View is not persistent` | Caught by `cog_load`'s `try`, which also skips `_register_context_menu()`, so **"Report Message" is never registered** |
| `report/advancedreport.py:46` | `discord.timedelta` doesn't exist | The **Mute button always fails**, shows staff the error, and never applies the timeout |

### `enchantedlogs`: temporary actions break the log

| Location | Problem | Result |
|---|---|---|
| `enchantedlogs/enhancedmodlog.py:212` | Red's `Case.until` is an `int`, but this subtracts a `datetime` from it | `TypeError`, with no enhanced log entry for any case that has an expiry |
| `enchantedlogs/enhancedmodlog.py:216` | Calls `.timestamp()` on that same `int` | Would raise `AttributeError` once line 212 is fixed |
| `enchantedlogs/enhancedmodlog.py:58`, `:177` | `self.bot.logger` doesn't exist on Red | `AttributeError` when ModLog isn't loaded (`:58`), or when sending a log message fails (`:177`) |

### `gacha`: profile fails for default avatars

`gacha/enhancedgacha.py:226` uses `member.avatar.url`. `avatar` is `None` for anyone without a custom avatar, so the profile command raises `AttributeError` for those members. `member.display_avatar.url` is always safe.

### `doublepost`: failure caught on ordinary messages

`doublepost/consecutivefilter.py:435` calls `self.bot.is_command`, which doesn't exist on Red. An `except` catches the error, so nothing visibly breaks, but each non-command message that reaches this check logs a warning with a traceback, which can flood the log.

## Deprecated

### `datetime.utcnow()`

Deprecated from Python 3.12, and the same mistake caused the `polls` end-time bug. Where the value goes through `.timestamp()` or is shown to users, times are off by the host's UTC offset unless the host runs in UTC.

| Cog | Locations | Effect on a non-UTC host |
|---|---|---|
| `beri_cautions` | `beri_cautions.py:94, 110, 127, 237, 310, 345, 676, 710, 940, 947, 984, 1100, 1132, 1220, 1242, 1533, 1583, 1878` | **Wrong times shown to users.** Warning expiry and hold times appear in `<t:...>` tags (`:694-695`, `:724`, `:972`, `:1601-1605`, `:1896-1899`). Internal comparisons stay consistent |
| `buckshot` | `buckshot.py:62, 63, 134, 185, 310, 396, 796` | **Wrong embed time at `:185`.** Durations are consistent |
| `afk` | `CustomAFK.py:50, 67, 91` | Elapsed times are consistent, apart from daylight-saving changes |
| `Suggestion` | `utils.py:11, 23` | Consistent; stored as naive ISO strings |
| `gacha` | `enhancedgacha.py:51` | None in practice: nothing sets `cooldownspawn`, so this line never runs |
| `enchantedlogs` | `enhancedmodlog.py:212` | See the crash above |

### Blocking the event loop

| Cog | Locations | Problem |
|---|---|---|
| `BB` | `deathbattle.py:103`, called from `:169` | Synchronous `requests.get` for each avatar (2-second timeout), plus image work; can freeze the bot for several seconds per battle |
| `crewbattles` | `data_manager.py:113, 197, 371, 375, 507, 514, 577`; `migration.py:121`; `tournament.py:137, 170` | `open()` with `json.load`/`json.dump` inside async functions; gets worse as data grows |
| `staffapplications` | `store.py:53`, used directly from the cog | Synchronous SQLite on the event loop. Low impact for small data and documented as a design choice. `aetherbound` and `voyage` already avoid this with `asyncio.to_thread` and `aiosqlite` |

### `bot.loop`

These work on 3.5.24, because Red loads cogs after login, when the loop is set. `asyncio.create_task` is the modern form, and these tasks aren't always kept or cancelled on unload.

- `beri_cautions/beri_cautions.py:76-77`
- `crewbattles/crew.py:65`, `crewbattles/tournament.py:68`
- `enchantedlogs/enhancedmodlog.py:48`, `:168`
- `onepiecemods/__init__.py:14`, `onepiecemods/onepiecemods.py:1269`

### `asyncio.get_event_loop()`

These work, because each call runs inside a running loop. `get_running_loop()` is the modern form.

- `beri/casino.py:432, 434, 436`
- `beri_cautions/beri_cautions.py:426, 440`
- `optcg/utils.py:30`
- `qimposters/onepiece_imposters.py:814, 817`

## Cosmetic

### Metadata

Red's Downloader doesn't reject bad or missing `info.json` files. It logs any JSON error and uses defaults, so these cogs still install, but they silently lose their requirements, version limits, install message and data statement.

| Cog | Problem |
|---|---|
| `BB`, `beri` | No `info.json`. For `BB` this causes the load failure above |
| `buckshot` | `info.json` starts with a `# info.json` comment line, which makes it invalid JSON, so all its metadata is ignored |
| `doublepost` | File is named `Info.json`, which isn't found on Linux, so the same applies there |
| `Suggestion`, `enchantedlogs`, `optcg` | No end-user data statement in `info.json` or `__init__.py` |
| `afk` | Statement only in `__init__.py`, not `info.json` |
| `afk`, `crewbattles` | No `min_bot_version` |
| `mrwhite` | `min_python_version` is `3.11.15`, which blocks installs on earlier 3.11 releases |
| `polls`, `onepiecemods` | Listed `discord.py` in `requirements`. Cogs must not list discord.py or Red, because Red provides them. **Fixed after this audit:** both are now `[]`; the table below still shows the audited values |

There's also no repository-level `info.json`. Downloader tolerates this too, so it only loses the repo's own description and install message.

### Leftover code

- `gacha/enhancedgacha.py:426-427`: a second, synchronous `setup` with an unawaited `add_cog`. Nothing calls it, because `gacha/__init__.py` has its own.
- `polls/v2poll.py:146`: `create_sprite_select_menu` builds a raw component dictionary and is never called.
- `crewbattles/setup.py`: its only caller is commented out at `crewbattles/crew.py:968-969`.
- `crewbattles/setup.py:8`, `crewbattles/ui.py:9`, `report/advancedreport.py:2`, `onepiecemods/utils/config_manager.py:3`, `onepiecemods/utils/hierarchy.py:3`: import `commands` from `discord.ext`. No registered command uses it in the cogs that load; `onepiecemods` couldn't be checked.
- `beri_cautions.py` at the repo root: not a package, so Downloader ignores it, and it repeats the `beri_cautions` findings above.

### Repo tooling

- `guesscandy/requirements-dev.txt:1` pins discord.py 2.6.3, while Red 3.5.24 pins 2.7.1.
- `.github/workflows/repohelp.yml` targets the deleted `repohelp/` directory.

## All cogs

"Loads" means the import and stub `setup()` both passed with the cog's declared requirements installed. `—` means not declared.

| Cog | `min_bot_version` | `requirements` | Data statement | Loads | Worst finding |
|---|---|---|---|---|---|
| `aetherbound` | 3.5.24 | none | `info.json` | Yes | None |
| `afk` | — | — | `__init__.py` | Yes | Deprecated |
| `BB` | no `info.json` | no `info.json` | **Missing** | **No** | **Will crash** |
| `beri` | no `info.json` | no `info.json` | **Missing** | Yes | Deprecated |
| `beri_cautions` | 3.5.0 | none | `info.json` | Yes | Deprecated |
| `bericore` | 3.5.0 | none | `info.json` | Yes | None |
| `buckshot` | 3.5.0, unread (invalid JSON) | none, unread | **Unreadable** | Yes | Deprecated |
| `crewbattles` | — | — | Both | Yes | Deprecated |
| `doublepost` | 3.5.0, unread on Linux | none | `info.json`, unread on Linux | Yes | **Will crash** (caught) |
| `enchantedlogs` | 3.5.0 | none | **Missing** | Yes | **Will crash** |
| `gacha` | 3.5.0 | — | `info.json` | Yes | **Will crash** |
| `grill` | 3.5.0 | none | `info.json` | Yes | None |
| `guesscandy` | 3.5.24 | `tzdata` | `info.json` | Yes | Cosmetic |
| `mine` | 3.5.0 | — | `info.json` | Yes | None |
| `mrwhite` | 3.5.24 | `Pillow>=10.1.0` | `info.json` | Yes | Cosmetic |
| `neko` | 3.5.0 | `aiohttp>=3.8.0` | Both | Yes | None |
| `onepiecefruit` | 3.5.0 | `pydantic>=2.0` | Both | Yes | None |
| `onepieceguess` | 3.5.24 | `aiohttp`, `Pillow>=10.0` | Both | Yes | None |
| `onepiecemods` | 3.5.0 | `discord.py>=2.3.0` | `info.json` | **No** | **Will crash** |
| `opcsupporters` | 3.5.0 | none | Both | Yes | None |
| `ope` | 3.5.0 | `PyYAML>=6.0` | Both | Yes | None |
| `optcg` | 3.5.0 | `Pillow`, `aiohttp` | **Missing** | Yes | Deprecated |
| `polls` | 3.5.0 | `discord.py>=2.0.0` | `info.json` | Yes | Cosmetic |
| `qimposters` | 3.5.0 | none | Both | Yes | Deprecated |
| `report` | 3.5.0 | none | `info.json` | Yes | **Will crash** |
| `staffapplications` | 3.5.24 | none | Both | Yes | Deprecated |
| `Suggestion` | 3.5.0 | none | **Missing** | Yes | Deprecated |
| `voyage` | 3.5.0 | `aiosqlite` | `info.json` | Yes | None |

Every cog directory has an `__init__.py`. `Character Sprite/` holds only images and isn't a cog. `aetherbound` and `staffapplications` use discord.py's newer `LayoutView` components, and both correctly require 3.5.24.
