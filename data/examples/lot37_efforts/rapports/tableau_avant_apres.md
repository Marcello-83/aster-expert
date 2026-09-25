# Avant / après — efforts des tirants et de la poutre (cas G et Q3)

Avant : lot 36, base (`data/examples/lot36_butee/rapports_base/synthese.json` : tirants en section entière, poutre en `POU_D_E`). Après : lot 37 (tirants de bord `TIRANT_01` et `TIRANT_09` en demi-section, poutre en `POU_D_T`). **Deux changements simultanés** : l'écart de chaque ligne ne se laisse pas attribuer à l'un ou à l'autre par ce seul tableau. Cas élémentaires, aucun verdict.

## Effort normal des tirants (kN)

| Tirant | G avant | G après | Q3 avant | Q3 après |
|---:|---:|---:|---:|---:|
| 1 | 324.6 | 212.6 | 88.8 | 57.9 |
| 2 | 394.0 | 425.1 | 108.9 | 117.1 |
| 3 | 395.1 | 425.1 | 112.4 | 120.5 |
| 4 | 396.0 | 425.1 | 116.4 | 124.7 |
| 5 | 396.3 | 425.1 | 118.2 | 127.1 |
| 6 | 396.0 | 425.1 | 116.4 | 124.7 |
| 7 | 395.1 | 425.1 | 112.4 | 120.5 |
| 8 | 394.0 | 425.1 | 108.9 | 117.1 |
| 9 | 324.6 | 212.6 | 88.8 | 57.9 |

## Efforts extrêmes de la poutre de couronnement

N, VY, VZ en kN ; MT, MFY, MFZ en kN·m.

| Effort | Cas | Min avant | Min après | Max avant | Max après |
|---|---|---:|---:|---:|---:|
| N | G | -0.1 | -0.0 | 0.0 | 0.0 |
| VY | G | -103.8 | -0.0 | 103.8 | 0.0 |
| VZ | G | -32.0 | -0.0 | 32.0 | 0.0 |
| MT | G | -58.5 | -0.0 | 58.5 | 0.0 |
| MFY | G | -93.0 | -0.0 | 25.3 | 0.0 |
| MFZ | G | -399.5 | -0.0 | 205.4 | 0.0 |
| N | Q3 | -0.2 | -0.2 | 0.4 | 0.4 |
| VY | Q3 | -381.3 | -376.8 | 381.3 | 376.8 |
| VZ | Q3 | -180.5 | -176.4 | 180.5 | 176.4 |
| MT | Q3 | -263.9 | -267.7 | 263.9 | 267.7 |
| MFY | Q3 | -178.9 | -150.0 | 542.0 | 523.3 |
| MFZ | Q3 | -864.3 | -752.2 | 1515.3 | 1455.7 |
