"""
INTEGRATION GUIDE — chargen into OnePieceFruit core.py
═══════════════════════════════════════════════════════════════════════════════

This file documents the EXACT minimal changes needed to wire chargen into your
existing core.py. Do not copy this file into your cog — apply the patches below.

─────────────────────────────────────────────────────────────────────────────
STEP 1: Add the import at the top of core.py
─────────────────────────────────────────────────────────────────────────────

    from .chargen.mixin import CharGenMixin

─────────────────────────────────────────────────────────────────────────────
STEP 2: Add CharGenMixin to the class definition
─────────────────────────────────────────────────────────────────────────────

    # BEFORE:
    class OnePieceFruit(commands.Cog):

    # AFTER:
    class OnePieceFruit(CharGenMixin, commands.Cog):

    MRO note: CharGenMixin must come BEFORE commands.Cog in the inheritance
    list so its commands are picked up by Red's cog loader correctly.

─────────────────────────────────────────────────────────────────────────────
STEP 3: Register the Config default in __init__
─────────────────────────────────────────────────────────────────────────────

    Add this line alongside your other self.config.register_* calls:

        self.config.register_member(character=None)

    If you're already calling register_member() with other keys, simply add
    character=None as another keyword argument:

        self.config.register_member(
            rep=0,
            streak=0,
            # ... your existing keys ...
            character=None,   # ← add this
        )

─────────────────────────────────────────────────────────────────────────────
STEP 4: File layout after integration
─────────────────────────────────────────────────────────────────────────────

    OnePieceFruit/
    ├── __init__.py
    ├── core.py              ← modified (steps 1-3 above)
    ├── models.py            ← your existing fruit/rep models (unchanged)
    ├── fruits.py            ← unchanged
    ├── piraterep.py         ← unchanged
    ├── info.json            ← unchanged
    └── chargen/
        ├── __init__.py      ← new
        ├── pools.py         ← new (all weighted RNG pools)
        ├── models.py        ← new (OnePieceCharacter dataclass)
        ├── engine.py        ← new (WheelEngine RNG logic)
        ├── animator.py      ← new (phased Discord embed animation)
        └── mixin.py         ← new (commands: rollchar, mychar, charinfo, chardelete)

─────────────────────────────────────────────────────────────────────────────
STEP 5: Reload the cog
─────────────────────────────────────────────────────────────────────────────

    [p]reload OnePieceFruit

─────────────────────────────────────────────────────────────────────────────
Config schema that gets written to Red's config storage
─────────────────────────────────────────────────────────────────────────────

    Per-guild, per-member entry under the "character" key:

    {
        "user_id":          123456789,
        "guild_id":         987654321,
        "display_name":     "Adam",
        "epithet":          "the Ironclad",
        "race":             "Human",
        "is_d_clan":        false,
        "affiliation":      "Pirate",
        "has_devil_fruit":  true,
        "devil_fruit_type": "Logia",
        "devil_fruit_name": "Mera Mera no Mi",
        "haki":             "Armament & Observation",
        "fighting_style":   "Devil Fruit Mastery",
        "strength":         "A-Tier",
        "speed":            "B-Tier",
        "battle_iq":        "S-Tier",
        "marine_rank":      null,
        "bounty":           1240000000,
        "rolled_at":        1716739200
    }

═══════════════════════════════════════════════════════════════════════════════
"""
