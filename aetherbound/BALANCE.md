# Class identity balance baseline

15,750 seeded solo simulations; fixed monster level, equally leveled player, no potions. Each player allocates one point/level to their class stat and one to vitality. The scripted strategy interrupts charged attacks and uses its damage skill when available. Starter gear is level 1 in every slot; all other gear matches the player level. Higher-tier cases are stress tests even at levels where those tiers cannot drop; Unique effects have separate regression tests.

These checks establish bounds, not final balance. They do not simulate human mistakes, party combat, or the full acquisition economy. Live Discord playtesting is still required.

| Class | Gear | Normal win rate | Boss win rate | Mean normal turns | Mean boss turns |
|---|---|---:|---:|---:|---:|
| vanguard | starter | 100.0% | 74.0% | 4.3 | 12.6 |
| vanguard | common | 100.0% | 100.0% | 4.1 | 10.9 |
| vanguard | uncommon | 100.0% | 100.0% | 3.8 | 9.4 |
| vanguard | rare | 100.0% | 100.0% | 3.4 | 8.2 |
| vanguard | epic | 100.0% | 100.0% | 3.1 | 7.4 |
| vanguard | legendary | 100.0% | 100.0% | 2.9 | 6.9 |
| vanguard | mythic | 100.0% | 100.0% | 2.9 | 6.9 |
| strider | starter | 100.0% | 99.0% | 4.2 | 10.8 |
| strider | common | 100.0% | 100.0% | 4.0 | 9.6 |
| strider | uncommon | 100.0% | 100.0% | 3.7 | 8.5 |
| strider | rare | 100.0% | 100.0% | 3.3 | 7.6 |
| strider | epic | 100.0% | 100.0% | 3.0 | 7.0 |
| strider | legendary | 100.0% | 100.0% | 2.9 | 6.4 |
| strider | mythic | 100.0% | 100.0% | 2.8 | 6.4 |
| arcanist | starter | 100.0% | 86.0% | 4.3 | 12.4 |
| arcanist | common | 100.0% | 100.0% | 4.1 | 10.8 |
| arcanist | uncommon | 100.0% | 100.0% | 3.9 | 9.4 |
| arcanist | rare | 100.0% | 100.0% | 3.5 | 8.1 |
| arcanist | epic | 100.0% | 100.0% | 3.2 | 7.4 |
| arcanist | legendary | 100.0% | 100.0% | 2.9 | 6.8 |
| arcanist | mythic | 100.0% | 100.0% | 2.9 | 6.8 |

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
| vanguard | raizen | starter | 50.0% | 12.7 |
| vanguard | raizen | common | 100.0% | 10.8 |
| vanguard | raizen | uncommon | 100.0% | 9.4 |
| vanguard | raizen | rare | 100.0% | 8.3 |
| vanguard | raizen | epic | 100.0% | 7.4 |
| vanguard | raizen | legendary | 100.0% | 6.9 |
| vanguard | raizen | mythic | 100.0% | 6.9 |
| strider | tsukara | starter | 98.0% | 10.8 |
| strider | tsukara | common | 100.0% | 9.6 |
| strider | tsukara | uncommon | 100.0% | 8.5 |
| strider | tsukara | rare | 100.0% | 7.6 |
| strider | tsukara | epic | 100.0% | 6.9 |
| strider | tsukara | legendary | 100.0% | 6.4 |
| strider | tsukara | mythic | 100.0% | 6.3 |
| strider | raizen | starter | 100.0% | 10.8 |
| strider | raizen | common | 100.0% | 9.6 |
| strider | raizen | uncommon | 100.0% | 8.5 |
| strider | raizen | rare | 100.0% | 7.6 |
| strider | raizen | epic | 100.0% | 7.0 |
| strider | raizen | legendary | 100.0% | 6.5 |
| strider | raizen | mythic | 100.0% | 6.4 |
| arcanist | tsukara | starter | 92.0% | 12.6 |
| arcanist | tsukara | common | 100.0% | 10.9 |
| arcanist | tsukara | uncommon | 100.0% | 9.4 |
| arcanist | tsukara | rare | 100.0% | 8.0 |
| arcanist | tsukara | epic | 100.0% | 7.3 |
| arcanist | tsukara | legendary | 100.0% | 6.8 |
| arcanist | tsukara | mythic | 100.0% | 6.8 |
| arcanist | raizen | starter | 80.0% | 12.3 |
| arcanist | raizen | common | 100.0% | 10.7 |
| arcanist | raizen | uncommon | 100.0% | 9.4 |
| arcanist | raizen | rare | 100.0% | 8.2 |
| arcanist | raizen | epic | 100.0% | 7.4 |
| arcanist | raizen | legendary | 100.0% | 6.8 |
| arcanist | raizen | mythic | 100.0% | 6.8 |

## Boss strategy comparison

50 seeds per case, no potions; 1,800 additional fights. Starter gear stays at level 1. Identity rotates defensive skills, banks Arcanist charges and avoids repeated Strider attacks. These policies are not optimal play.

| Class | Boss | Gear | Strategy | Win rate | Mean turns |
|---|---|---|---|---:|---:|
| vanguard | tsukara | starter | Attack only | 0.0% | 9.0 |
| vanguard | tsukara | starter | Interrupt | 98.0% | 12.5 |
| vanguard | tsukara | starter | Identity | 30.0% | 13.0 |
| vanguard | tsukara | common | Attack only | 0.0% | 12.0 |
| vanguard | tsukara | common | Interrupt | 100.0% | 10.9 |
| vanguard | tsukara | common | Identity | 100.0% | 12.3 |
| vanguard | raizen | starter | Attack only | 0.0% | 9.0 |
| vanguard | raizen | starter | Interrupt | 50.0% | 12.7 |
| vanguard | raizen | starter | Identity | 78.0% | 13.6 |
| vanguard | raizen | common | Attack only | 100.0% | 13.3 |
| vanguard | raizen | common | Interrupt | 100.0% | 10.8 |
| vanguard | raizen | common | Identity | 100.0% | 11.9 |
| strider | tsukara | starter | Attack only | 0.0% | 8.9 |
| strider | tsukara | starter | Interrupt | 98.0% | 10.8 |
| strider | tsukara | starter | Identity | 20.0% | 11.8 |
| strider | tsukara | common | Attack only | 0.0% | 12.0 |
| strider | tsukara | common | Interrupt | 100.0% | 9.6 |
| strider | tsukara | common | Identity | 100.0% | 10.9 |
| strider | raizen | starter | Attack only | 0.0% | 9.0 |
| strider | raizen | starter | Interrupt | 100.0% | 10.8 |
| strider | raizen | starter | Identity | 100.0% | 11.3 |
| strider | raizen | common | Attack only | 100.0% | 12.7 |
| strider | raizen | common | Interrupt | 100.0% | 9.6 |
| strider | raizen | common | Identity | 100.0% | 10.0 |
| arcanist | tsukara | starter | Attack only | 0.0% | 9.0 |
| arcanist | tsukara | starter | Interrupt | 92.0% | 12.6 |
| arcanist | tsukara | starter | Identity | 82.0% | 13.7 |
| arcanist | tsukara | common | Attack only | 0.0% | 12.0 |
| arcanist | tsukara | common | Interrupt | 100.0% | 10.9 |
| arcanist | tsukara | common | Identity | 100.0% | 12.9 |
| arcanist | raizen | starter | Attack only | 0.0% | 9.0 |
| arcanist | raizen | starter | Interrupt | 80.0% | 12.3 |
| arcanist | raizen | starter | Identity | 66.0% | 13.1 |
| arcanist | raizen | common | Attack only | 100.0% | 13.3 |
| arcanist | raizen | common | Interrupt | 100.0% | 10.7 |
| arcanist | raizen | common | Identity | 100.0% | 11.2 |

## Experience pacing

| Current level | EXP to next | Same-level normal wins (rounded up) |
|---|---:|---:|
| 1 | 123 | 4 |
| 5 | 455 | 8 |
| 10 | 1230 | 12 |
| 15 | 2405 | 17 |
| 19 | 3633 | 21 |
