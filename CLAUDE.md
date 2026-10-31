# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A collection of independent cogs (plugins) for [Red-DiscordBot](https://docs.discord.red/). Each top-level directory with an `__init__.py` is one cog, loaded with `[p]load <dirname>` and installed through Red's Downloader. There is no build step and no root-level project config, so tooling is per-cog.

Target stack, where a cog pins one: Python 3.11, Red-DiscordBot 3.5.24, discord.py 2.7.1 (`guesscandy` pins discord.py 2.6.3 instead). Pins are per cog, so use a separate venv when they differ.

## Commands

Run everything from the repository root. Only the cogs below have tests or lint config. CI (`.github/workflows/<cog>.yml`) runs only when that cog's files change.

Install dev requirements in an isolated venv, never in a running bot's environment: `python -m pip install -r <cog>/requirements-dev.txt`.

**aetherbound, staffapplications** (ruff + pytest), **mrwhite** (pytest only):

```bash
python -m ruff check --config <cog>/ruff.toml <cog>
python -m ruff format --check --config <cog>/ruff.toml <cog>

# PowerShell: $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -c <cog>/pytest.ini --confcutdir=<cog>/tests <cog>/tests -q

# Single test: same command, with a node id in place of the final path
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -c aetherbound/pytest.ini --confcutdir=aetherbound/tests "aetherbound/tests/test_engine.py::test_roster" -q
```

Keep the plugin autoload flag and `--confcutdir`: they stop pytest from importing unrelated cogs' packages in this repo.

**guesscandy**: `python guesscandy/test_game.py` (requires `guesscandy/requirements-dev.txt`; also checks the bundled photos).

**onepieceguess** (stdlib only):

```bash
python -m py_compile onepieceguess/*.py
python -m unittest onepieceguess.test_game
python -m json.tool onepieceguess/info.json > /dev/null
```

### Aetherbound balance baselines

CI fails if these committed reports differ from a fresh run, so regenerate them after changing anything that affects balance (combat, content, loot):

```bash
python -m aetherbound.balance > aetherbound/BALANCE.md
python -m aetherbound.balance --armor > aetherbound/ARMOR_AUDIT.md
python -m aetherbound.balance --customization > aetherbound/CUSTOMIZATION_BALANCE.md
python -m aetherbound.boss_balance > aetherbound/BOSS_BALANCE.md
```

CI compares them with `diff -u` on Linux, so line endings or encoding changed by Windows shell redirection can cause a failure.

## Architecture

### Cog conventions

- `__init__.py` normally defines `setup(bot)`, which adds the cog.
- `info.json` holds Downloader metadata: `requirements`, `min_bot_version`, `end_user_data_statement` and so on. Update it when runtime dependencies or stored user data change. Never list discord.py or Red in `requirements`, because Red provides them.
- Use relative imports within a cog. Cogs are installed independently, so never import from another cog's directory.
- Integrations between cogs are runtime lookups with `bot.get_cog("Name")`, and the other cog may not be loaded. `BeriCore` (`bericore/`) is the shared currency provider used by `beri`, `beri_cautions`, `onepiecefruit`, `onepieceguess`, `voyage` and `Suggestion`.

### Layering in the tested cogs

The newer cogs separate rules from Discord, and new work in them should keep that split:

- **Rules without Discord imports**: `engine.py` in `aetherbound`, `mrwhite`, `guesscandy` and `onepieceguess`, plus `aetherbound`'s `content.py` and `loot.py`. This is what makes the rules testable and, in Aetherbound, simulatable.
- **Persistence**: `store.py` in `aetherbound` and `staffapplications` is a SQLite store that assumes one bot process owns the database. Aetherbound's engine mutations must run inside a `Store` transaction so state and rewards commit atomically.
- **Discord layer**: the main cog module for commands, `views.py` for controls and, in Aetherbound, `presentation.py` for embeds. Aetherbound's persistent views use battle IDs and turn versions to reject stale or double clicks.
- `mrwhite/session.py` serializes player inputs and manages messages and deadlines for a game in progress. Game state stays in `engine.py`.

Older cogs (for example `onepiecefruit`, `voyage`, `crewbattles`) are less uniform, and some are single large modules. `beri` composes its cog class from mixins, one per feature file, and routes balance changes through `_modify_balance()`.

### Aetherbound documents

`aetherbound/ROADMAP.md` separates shipped features from planned ones, so check it before assuming a feature exists. `aetherbound/README.md` is the source of truth for setup and required permissions.

### Command style

Most cogs use prefix commands. `app_commands` or hybrid commands appear in only a few (`gacha`, `voyage`, `report`, `opcsupporters`, `onepieceguess`, `polls`). Aetherbound deliberately registers no slash commands.

## Slash command conversion

These are Red-DiscordBot 3.5 cogs. Convert prefix commands to `commands.hybrid_command` / `commands.hybrid_group`, using `polls/v2poll.py` as the reference example. `voyage/voyage.py` only partly follows these rules: it uses hybrid commands, but has several top-level commands and no `@app_commands.describe`.

- Discord allows only 100 top-level slash commands per bot, so each cog exposes at most one top-level hybrid group, with its commands as subcommands.
- Every slash parameter gets a short description using `@app_commands.describe`.
- Owner-only and admin setup commands may stay prefix-only.
- Do not change command behavior, Config keys, or data formats. Fixing a crash, a deprecated API or wrong displayed times is an allowed exception to the command behavior rule.
- When a cog is converted, set `min_bot_version` in its `info.json` to 3.5.24.
- When a cog is converted, also fix its deprecated APIs (e.g. `datetime.utcnow()`).
- Flag any command that doesn't translate cleanly (variable arguments, free-text parsing, attachments) instead of guessing.
- Work on one cog at a time and stop for review after each.

## Repository quirks

- There is no repository-level `info.json`, which Red's Downloader normally expects at the repo root.
- `BB/` and `beri/` have no `info.json`, and `doublepost/` uses `Info.json` (capitalized), which matters on case-sensitive filesystems.
- `.github/workflows/repohelp.yml` is left over: the `repohelp/` directory has been deleted.
- There is no root `.gitignore`, and some `__pycache__` files are tracked, so check `git status` before staging with broad paths.
- `beri_cautions.py` at the root is a separate copy that differs from `beri_cautions/beri_cautions.py`. The package is the installable cog.
