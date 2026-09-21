# Aetherbound expansion order

This file distinguishes shipped foundations from planned features. It is not a
claim that the entire expansion is available.

## Foundation update — implemented

- Data-defined skills with unchanged combat baseline and original RNG timing.
- Victory loot equip / auto-equip controls, locking, confirmed bulk salvage,
  rarity-based yields and item binding metadata.
- Transactional economy events and guild-scoped admin audit.
- Kill switches for the two new interactive gear features.
- Armor-cap audit. Attribute respec already exists and remains free.

## Class identity and armor balance — implemented

Resolve / defensive Vanguard, Momentum / alternating Strider and charge-driven
Arcanist now have bounded resources, distinct costs/cooldowns and passives.
Resources persist in active battles and initialize safely for legacy saves.
Armor now gains logarithmically above 100. Extended boss-policy simulations and
resource/upgrade tests accompany the new baseline. Free attribute respec remains.
More classes remain a later expansion, after feedback on these three playstyles.

## Next: sets, then sockets

Put set bonuses in stats() so complete-loadout comparisons see them. Preserve the
binding policy already stored on items. Add intentional socket customization;
no gear rerolls. Extend simulations for set combinations and effect stacking.

## Shared-pool boss spawns

Keep personal act() encounters, but persist shared boss HP separately. Apply
validated damage, contribution and participation limits atomically; design rewards
against overkill, low-level farming and duplicate claims. Define death/expiry and
restart recovery before release. Add a dedicated boss-pool kill switch and seeded
multi-player simulations. Live party turn combat remains deferred.

## Endgame

Paragon XP/points first so level-20 XP has a purpose, with explicit progression
bounds. Then leaderboards and weekly dungeon modifiers. Decide season/reset rules
before persistent rankings. Prestige stays deferred until repeating content has
value. Keep economy changes audited and independently switchable.

## Escrowed trading

Implement two-player atomic transactions and escrow ownership before UI acceptance.
Only eligible unbound, unlocked, unequipped items may enter escrow. Handle both
inventories, capacity, confirmation, cancellation, expiry, restart and simultaneous
accept/cancel without duplication. Bound flags alone do not enable trading.
Add trade-specific audit events and a kill switch that blocks new trades while
preserving safe cancellation/refund of existing escrow.

## Artwork

Continue the approved human-created, credited sprite direction. Find suitable
licensed art for the remaining ten creatures, prioritizing Tsukara and Raizen.
Do not reuse unrelated sprites as if they depicted those bosses.

## Deferred

Gear rerolls, prestige, and live party combat are not part of the current release.
