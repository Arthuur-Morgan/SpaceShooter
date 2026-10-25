# Adaptive Director Offline Training Results

Synthetic AI-player simulation; this does not modify `save_data.json`.

## Dataset

- Seed: 17
- Playstyles: 4
- Runs per playstyle: 12
- Encounter decisions: 3,456

## AI-player summaries

| Playstyle | Encounters | Average kills/run | Average damage/run |
| --- | ---: | ---: | ---: |
| mobile_rockets | 864 | 98.3 | 156.5 |
| anchored_autocannon | 864 | 136.3 | 177.9 |
| mobile_zapper | 864 | 116.5 | 142.2 |
| precision_big_gun | 864 | 119.2 | 156.8 |

## Highest learned context/action values

| Context and encounter | Learned value | Samples |
| --- | ---: | ---: |
| anchored:auto_cannon:active:assault | 0.958 | 3 |
| anchored:auto_cannon:standard:assault | 0.870 | 257 |
| mobile:zapper:standard:assault | 0.833 | 143 |
| mobile:zapper:active:assault | 0.817 | 118 |
| anchored:big_space_gun:standard:assault | 0.755 | 102 |
| anchored:big_space_gun:active:assault | 0.735 | 154 |
| anchored:big_space_gun:standard:frigate_barrage | 0.656 | 47 |
| anchored:auto_cannon:standard:crossfire | 0.655 | 177 |
| anchored:auto_cannon:standard:hunter_pack | 0.638 | 134 |
| anchored:big_space_gun:standard:battle_line | 0.628 | 5 |
| anchored:big_space_gun:standard:crossfire | 0.608 | 84 |
| mobile:zapper:active:hunter_pack | 0.607 | 45 |

## Interpretation

Higher values identify encounter choices that produced kills and score with manageable damage for that synthetic player context. The exported JSON profile is intentionally separate so it can be inspected or imported later without overwriting live player learning.
