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
| `[p]brandom [attribute]` | `[p]brandom aquos` |

The card spreadsheet PDF has 41 pages, but many effect cells are cut off at the page edge. Those entries have `effect: null`, `status: incomplete`, and an `excerpt` from visible text. Do not treat that excerpt as authoritative full text. Evo changed entries without full replacement wording have `status: evo wording pending`; their old effect is suppressed. Full replacement effects in the Evo notes supersede the spreadsheet. Rush Down is marked removed. The Post-New Vestroia Rules PDF supplies structured deck constraints and Preyas’s attribute trait. Deck validation itself is deferred. The G-Power charts in that PDF are images, so individual base values remain unknown pending visual transcription.

`cards.json` includes source document and page per record, structured `requires`, `attributes`, and `bakugan` arrays. `bakugan.json` indexes the available tagged names with unknown base G-Power. These are reference records, not a complete gameplay model. The PDF itself contains overlapping columns and some clipped names/tags; review an entry against the source before relying on it for deck legality. Add corrections directly to the JSON and keep source metadata. The next import can append versioned patch changes without changing commands.

Read-only; no user Config. Pagination buttons belong to the searching user and expire after three minutes. RepositoryHelp discovers the commands from the loaded cog automatically.

Card images live in a separate optional `data/images.json` index sourced from the Bakugan Brawl Online deck-builder public asset manifest. 263 records matched by normalized name and card type; embeds link to the public image host and credit the site. No images are copied into the repository. Unmatched or custom cards remain text only. Image links may change if the source removes or renames assets.

`brandom` samples one Guardian, two Generic Bakugan, six unrestricted single-attribute Normal Abilities, and three Gates (one matching Attribute or Reactor Gate, two Commands) using the dated public website catalog snapshot. The Discord embed shows the image directly. Random generation does not run the website's deck validator.
Each roll also attaches a website-compatible `.deck.json` file with the exact IDs in the image. Download it and use the deck builder's Import control to edit or validate the deck. The text fallback includes the same JSON file if image rendering fails.

`brandom` attaches a generated deck image with public game artwork when available. Missing art gets a labeled placeholder; if image rendering fails, the command sends its text list. Pillow is installed through `info.json`. `data/bakugan_art.json` maps Bakugan names to the site's public artwork URLs; the existing card image index remains separate.

## Community commands

- `[p]brules [topic]` shows multi-section explanations from the supplied rules PDF, with source pages and a full-rules link. For example, `[p]brules ability cards` covers activation, Signature, Fusion, Normal, and Trap cards. A server admin can use `[p]brulesauto true` in a channel to answer rule questions there with the source link (five-minute channel cooldown); `[p]brulesauto false` disables it.
- `[p]blinkprofile https://bakuganbrawl.online/u/<id>` links your public site profile. If the bot host cannot reach the site's API, a well-formed URL is still saved with an explicit unverified message; `[p]bstats` needs API access to show current stats. `[p]bleaderboard` reads the public wins ranking, and `[p]bunlinkprofile` removes the stored link. No website credentials are requested or stored. Linking a public URL does not prove account ownership.
- Attach a website `.deck.json` export to `[p]bdeckshare <title>` to resolve the exact website card IDs against `data/site_catalog.json` (public catalog snapshot dated 2026-09-29) and generate an inline image with the corresponding website artwork and card names. Export the JSON using the site's deck builder Export option. The site may add cards later; an unknown ID produces a clear update-needed error instead of a guessed match. An image downloaded with Share deck image can still be attached directly; image-only uploads cannot be turned back into structured card data. The bot saves a message link in the server's public `[p]bdecks [page]` list (up to 100 recent entries). The author or a moderator can use `[p]bdeckremove <id>` to remove the listing; the original Discord message remains until separately deleted.

Bakugan Brawl Online currently shows no community decks in its public gallery, so the bot's shared deck list is server-local and user submitted. It does not publish decks to the website. The site describes itself as a tabletop simulator, so the bot reports the site's public statistics rather than inferring game outcomes.
