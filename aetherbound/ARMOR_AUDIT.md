# Armor cap audit

Fully equipped Vanguard; same-level gear in all 11 slots, one vitality point per level, no upgrades. 50 seeds per row. Higher tiers below their unlock level are stress tests. The final column counts builds where adding +1 upgrade to the chest produces no armor gain.

| Level | Rarity | Mean armor | Above soft threshold | Wasted chest upgrade |
|---|---|---:|---:|---:|
| 1 | common | 42.5 | 0% | 0% |
| 1 | uncommon | 53.5 | 0% | 0% |
| 1 | rare | 64.6 | 0% | 0% |
| 1 | epic | 75.6 | 0% | 0% |
| 1 | legendary | 86.5 | 0% | 0% |
| 1 | mythic | 96.5 | 0% | 0% |
| 3 | common | 64.5 | 0% | 0% |
| 3 | uncommon | 75.5 | 0% | 0% |
| 3 | rare | 86.6 | 0% | 0% |
| 3 | epic | 97.6 | 2% | 0% |
| 3 | legendary | 107.9 | 100% | 0% |
| 3 | mythic | 115.8 | 100% | 0% |
| 5 | common | 86.5 | 0% | 0% |
| 5 | uncommon | 98.6 | 18% | 0% |
| 5 | rare | 109.6 | 100% | 0% |
| 5 | epic | 118.7 | 100% | 0% |
| 5 | legendary | 126.3 | 100% | 0% |
| 5 | mythic | 131.9 | 100% | 0% |
| 6 | common | 97.5 | 0% | 0% |
| 6 | uncommon | 108.7 | 100% | 0% |
| 6 | rare | 118.0 | 100% | 0% |
| 6 | epic | 125.7 | 100% | 0% |
| 6 | legendary | 132.4 | 100% | 0% |
| 6 | mythic | 137.4 | 100% | 0% |
| 8 | common | 116.5 | 100% | 0% |
| 8 | uncommon | 124.5 | 100% | 0% |
| 8 | rare | 131.4 | 100% | 0% |
| 8 | epic | 137.4 | 100% | 0% |
| 8 | legendary | 142.8 | 100% | 0% |
| 8 | mythic | 146.8 | 100% | 0% |
| 10 | common | 130.2 | 100% | 0% |
| 10 | uncommon | 136.9 | 100% | 0% |
| 10 | rare | 142.8 | 100% | 0% |
| 10 | epic | 148.1 | 100% | 0% |
| 10 | legendary | 152.8 | 100% | 0% |
| 10 | mythic | 156.1 | 100% | 0% |
| 15 | common | 153.8 | 100% | 0% |
| 15 | uncommon | 158.3 | 100% | 0% |
| 15 | rare | 162.6 | 100% | 0% |
| 15 | epic | 166.4 | 100% | 0% |
| 15 | legendary | 170.0 | 100% | 0% |
| 15 | mythic | 172.4 | 100% | 0% |
| 20 | common | 169.7 | 100% | 0% |
| 20 | uncommon | 173.3 | 100% | 0% |
| 20 | rare | 176.7 | 100% | 0% |
| 20 | epic | 179.8 | 100% | 0% |
| 20 | legendary | 182.8 | 100% | 0% |
| 20 | mythic | 184.6 | 100% | 0% |

Effective armor equals raw armor up to 100, then 100 + 50 * ln(1 + (raw - 100) / 50). Damage reduction still uses 100 / (100 + effective armor). Every extra point of raw armor increases effective armor, though integer damage rounding can hide a small gain on an individual hit.
