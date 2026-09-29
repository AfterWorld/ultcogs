# BakuganDB

Red 3.5.24 / Python 3.11 reference cog. Load with `[p]load bakugandb`.

| Command | Example |
| --- | --- |
| `[p]bcard <name>` | `[p]bcard bluesquall` |
| `[p]bcards [terms]` | `[p]bcards normal aquos` |
| `[p]bsearch <text>` | `[p]bsearch revive` |
| `[p]bbakugan <name>` | `[p]bbakugan preyas` |
| `[p]bfusion <name>` | `[p]bfusion blue stealth` |
| `[p]bgates [terms]` | `[p]bgates command` |

The card spreadsheet PDF has 41 pages, but many effect cells are cut off at the page edge. Those entries have `effect: null`, `status: incomplete`, and an `excerpt` from visible text. Do not treat that excerpt as authoritative full text. Evo changed entries without full replacement wording have `status: evo wording pending`; their old effect is suppressed. Full replacement effects in the Evo notes supersede the spreadsheet. Rush Down is marked removed. The separately named Post-New Vestroia Rules file was not among the two supplied PDFs, so `rules.json` has no deck constraints and deck validation is deferred.

`cards.json` includes source document and page per record, structured `requires`, `attributes`, and `bakugan` arrays. `bakugan.json` indexes the available tagged names with unknown base G-Power. These are reference records, not a complete gameplay model. The PDF itself contains overlapping columns and some clipped names/tags; review an entry against the source before relying on it for deck legality. Add corrections directly to the JSON and keep source metadata. The next import can append versioned patch changes without changing commands.

Read-only; no user Config. Pagination buttons belong to the searching user and expire after three minutes. RepositoryHelp discovers the commands from the loaded cog automatically.
