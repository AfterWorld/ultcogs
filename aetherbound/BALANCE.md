# Phase 1 balance baseline

15,750 seeded solo simulations; fixed monster level, equally leveled player, no potions. Each player allocates one point/level to their class stat and one to vitality. The scripted strategy interrupts charged attacks and uses its damage skill when available. Starter gear is level 1 in every slot; all other gear matches the player level. Higher-tier cases are stress tests even at levels where those tiers cannot drop; Unique effects have separate regression tests.

These checks establish bounds, not final balance. They do not simulate human mistakes, party combat, or the full acquisition economy. Live Discord playtesting is still required.

| Class | Gear | Normal win rate | Boss win rate | Mean normal turns | Mean boss turns |
|---|---|---:|---:|---:|---:|
| vanguard | starter | 100.0% | 91.0% | 4.3 | 12.5 |
| vanguard | common | 100.0% | 100.0% | 4.1 | 10.7 |
| vanguard | uncommon | 100.0% | 100.0% | 3.8 | 9.4 |
| vanguard | rare | 100.0% | 100.0% | 3.4 | 8.2 |
| vanguard | epic | 100.0% | 100.0% | 3.1 | 7.4 |
| vanguard | legendary | 100.0% | 100.0% | 2.9 | 6.9 |
| vanguard | mythic | 100.0% | 100.0% | 2.9 | 6.9 |
| strider | starter | 100.0% | 87.0% | 4.4 | 12.2 |
| strider | common | 100.0% | 100.0% | 4.1 | 10.6 |
| strider | uncommon | 100.0% | 100.0% | 3.9 | 9.3 |
| strider | rare | 100.0% | 100.0% | 3.4 | 8.3 |
| strider | epic | 100.0% | 100.0% | 3.2 | 7.5 |
| strider | legendary | 100.0% | 100.0% | 2.9 | 7.0 |
| strider | mythic | 100.0% | 100.0% | 2.9 | 6.9 |
| arcanist | starter | 100.0% | 99.0% | 4.3 | 12.7 |
| arcanist | common | 100.0% | 100.0% | 4.1 | 10.8 |
| arcanist | uncommon | 100.0% | 100.0% | 3.9 | 9.6 |
| arcanist | rare | 100.0% | 100.0% | 3.5 | 8.4 |
| arcanist | epic | 100.0% | 100.0% | 3.2 | 7.6 |
| arcanist | legendary | 100.0% | 100.0% | 2.9 | 7.0 |
| arcanist | mythic | 100.0% | 100.0% | 2.9 | 7.0 |

## Individual boss outcomes

| Class | Boss | Gear | Win rate | Mean turns |
|---|---|---|---:|---:|
| vanguard | tsukara | starter | 98.0% | 12.5 |
| vanguard | tsukara | common | 100.0% | 10.9 |
| vanguard | tsukara | uncommon | 100.0% | 9.4 |
| vanguard | tsukara | rare | 100.0% | 8.1 |
| vanguard | tsukara | epic | 100.0% | 7.3 |
| vanguard | tsukara | legendary | 100.0% | 6.9 |
| vanguard | tsukara | mythic | 100.0% | 6.8 |
| vanguard | raizen | starter | 84.0% | 12.5 |
| vanguard | raizen | common | 100.0% | 10.5 |
| vanguard | raizen | uncommon | 100.0% | 9.4 |
| vanguard | raizen | rare | 100.0% | 8.3 |
| vanguard | raizen | epic | 100.0% | 7.4 |
| vanguard | raizen | legendary | 100.0% | 6.9 |
| vanguard | raizen | mythic | 100.0% | 6.9 |
| strider | tsukara | starter | 100.0% | 12.2 |
| strider | tsukara | common | 100.0% | 10.7 |
| strider | tsukara | uncommon | 100.0% | 9.3 |
| strider | tsukara | rare | 100.0% | 8.3 |
| strider | tsukara | epic | 100.0% | 7.5 |
| strider | tsukara | legendary | 100.0% | 7.0 |
| strider | tsukara | mythic | 100.0% | 6.9 |
| strider | raizen | starter | 74.0% | 12.3 |
| strider | raizen | common | 100.0% | 10.4 |
| strider | raizen | uncommon | 100.0% | 9.2 |
| strider | raizen | rare | 100.0% | 8.3 |
| strider | raizen | epic | 100.0% | 7.6 |
| strider | raizen | legendary | 100.0% | 7.0 |
| strider | raizen | mythic | 100.0% | 7.0 |
| arcanist | tsukara | starter | 100.0% | 12.8 |
| arcanist | tsukara | common | 100.0% | 11.2 |
| arcanist | tsukara | uncommon | 100.0% | 9.5 |
| arcanist | tsukara | rare | 100.0% | 8.4 |
| arcanist | tsukara | epic | 100.0% | 7.6 |
| arcanist | tsukara | legendary | 100.0% | 7.0 |
| arcanist | tsukara | mythic | 100.0% | 6.9 |
| arcanist | raizen | starter | 98.0% | 12.6 |
| arcanist | raizen | common | 100.0% | 10.5 |
| arcanist | raizen | uncommon | 100.0% | 9.6 |
| arcanist | raizen | rare | 100.0% | 8.5 |
| arcanist | raizen | epic | 100.0% | 7.6 |
| arcanist | raizen | legendary | 100.0% | 7.0 |
| arcanist | raizen | mythic | 100.0% | 7.0 |

## Experience pacing

| Current level | EXP to next | Same-level normal wins (rounded up) |
|---|---:|---:|
| 1 | 123 | 4 |
| 5 | 455 | 8 |
| 10 | 1230 | 12 |
| 15 | 2405 | 17 |
| 19 | 3633 | 21 |
