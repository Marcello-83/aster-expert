# Lot 34 -- tableaux de résultats (générés par scripts/report_lot34.py)

## Quai réduit, étape 1 : charge assemblée contre charge intégrée

**Référence indépendante du lot 33 (tri des paires), application unique, tables à 6 chiffres**

| Cas | Assemblée Y (N) | Intégrée, profil spécifié Y (N) | Écart rel. max | Verdict | Écart rel. max, règle nodale | Verdict |
|---|---:|---:|---:|---|---:|---|
| EAU_A | -4.298700000e+06 | -4.298700000e+06 | 1.08e-15 | ABSENT | — | — |
| EAU_P | -1.842300000e+06 | -1.842300000e+06 | 2.41e-14 | ABSENT | — | — |
| G | -5.604340000e+06 | -5.604228000e+06 | 2.00e-05 | PRESENT | — | — |
| Q1 | -1.836790000e+06 | -1.809136000e+06 | 1.53e-02 | PRESENT | — | — |

**Référence par couche, application unique de la fonction doublée, tables à 12 chiffres**

| Cas | Assemblée Y (N) | Intégrée, profil spécifié Y (N) | Écart rel. max | Verdict | Écart rel. max, règle nodale | Verdict |
|---|---:|---:|---:|---|---:|---|
| EAU_A | -4.298700000e+06 | -4.298700000e+06 | 1.08e-15 | ABSENT | 1.08e-15 | ABSENT |
| EAU_P | -1.842300000e+06 | -1.842300000e+06 | 2.41e-14 | ABSENT | 2.41e-14 | ABSENT |
| G | -5.604338252e+06 | -5.610988000e+06 | 1.19e-03 | PRESENT | 1.70e-14 | ABSENT |
| Q1 | -1.836788250e+06 | -1.837216000e+06 | 2.33e-04 | PRESENT | 2.41e-15 | ABSENT |

**Référence par couche, application par couche (correction), tables à 12 chiffres**

| Cas | Assemblée Y (N) | Intégrée, profil spécifié Y (N) | Écart rel. max | Verdict | Écart rel. max, règle nodale | Verdict |
|---|---:|---:|---:|---|---:|---|
| EAU_A | -4.298700000e+06 | -4.298700000e+06 | 1.08e-15 | ABSENT | 1.08e-15 | ABSENT |
| EAU_P | -1.842300000e+06 | -1.842300000e+06 | 2.41e-14 | ABSENT | 2.41e-14 | ABSENT |
| G | -5.610988000e+06 | -5.610988000e+06 | 2.07e-12 | ABSENT | 1.34e-14 | ABSENT |
| Q1 | -1.837216000e+06 | -1.837216000e+06 | 1.90e-15 | ABSENT | 1.90e-15 | ABSENT |

## Quai réduit, étape 2 : bilan d'équilibre (modèle corrigé)

**Quai réduit**

| Cas | Composante | Appliquée (N) | Réactions bloquées (N) | Ressorts (N) | Bilan (N) | Écart relatif |
|---|---|---:|---:|---:|---:|---:|
| EAU_A | X | -1.162021590e-10 | -3.999430887e-07 | 0.000000000e+00 | -4.001e-07 | -9.31e-14 |
| EAU_A | Y | -4.298700000e+06 | 9.791732637e+05 | 3.319526737e+06 | +4.425e-04 | 1.03e-10 |
| EAU_A | Z | 3.597881107e-12 | 5.000038072e-07 | 0.000000000e+00 | +5.000e-07 | 1.16e-13 |
| EAU_P | X | -3.492317546e-11 | 2.554763315e-11 | 0.000000000e+00 | -9.376e-12 | -5.09e-18 |
| EAU_P | Y | -1.842300000e+06 | 4.172245119e+05 | 1.425075488e+06 | +2.257e-05 | 1.23e-11 |
| EAU_P | Z | 1.112488866e-12 | -9.999785107e-07 | 0.000000000e+00 | -1.000e-06 | -5.43e-13 |
| G | X | 9.095515452e-10 | 4.960790448e-11 | 0.000000000e+00 | +9.592e-10 | 1.71e-16 |
| G | Y | -5.610988000e+06 | 8.101585619e+05 | 4.800829438e+06 | +2.430e-04 | 4.33e-11 |
| G | Z | -7.995777129e+05 | 7.995777129e+05 | 0.000000000e+00 | -9.249e-07 | -1.65e-13 |
| Q1 | X | -2.636824092e-09 | -6.999750067e-07 | 0.000000000e+00 | -7.026e-07 | -3.82e-13 |
| Q1 | Y | -1.837216000e+06 | 4.952201970e+05 | 1.341995803e+06 | +3.229e-05 | 1.76e-11 |
| Q1 | Z | 3.930946509e-12 | -9.000068530e-07 | 0.000000000e+00 | -9.000e-07 | -4.90e-13 |
| A (informatif) | X | 0.000000000e+00 | 2.999601098e-07 | 0.000000000e+00 | +3.000e-07 | 3.75e-13 |
| A (informatif) | Y | 8.000000000e+05 | -6.887623540e+05 | -1.112376460e+05 | -3.541e-05 | -4.43e-11 |
| A (informatif) | Z | 0.000000000e+00 | -3.999739420e-07 | 0.000000000e+00 | -4.000e-07 | -5.00e-13 |
| Q3 (informatif) | X | 0.000000000e+00 | 2.000579731e-07 | 0.000000000e+00 | +2.001e-07 | 2.31e-13 |
| Q3 (informatif) | Y | -8.660000000e+05 | 9.219009650e+05 | -5.590096517e+04 | -1.198e-04 | -1.38e-10 |
| Q3 (informatif) | Z | 5.000000000e+05 | -5.000000000e+05 | 0.000000000e+00 | +2.100e-06 | 2.42e-12 |

## Modèle complet, étape 4 : bilan d'équilibre

**Modèle complet**

| Cas | Composante | Appliquée (N) | Réactions bloquées (N) | Ressorts (N) | Bilan (N) | Écart relatif |
|---|---|---:|---:|---:|---:|---:|
| EAU_A | X | -1.162021590e-10 | -1.439985509e-05 | 0.000000000e+00 | -1.440e-05 | -8.37e-13 |
| EAU_A | Y | -1.719480000e+07 | 3.878357241e+06 | 1.331644276e+07 | -1.377e-03 | -8.01e-11 |
| EAU_A | Z | 2.511687236e-10 | -1.300009899e-05 | 0.000000000e+00 | -1.300e-05 | -7.56e-13 |
| EAU_P | X | 6.635687555e-10 | -1.129993987e-05 | 0.000000000e+00 | -1.130e-05 | -1.53e-12 |
| EAU_P | Y | -7.369200000e+06 | 1.652563206e+06 | 5.716636794e+06 | -3.779e-04 | -5.13e-11 |
| EAU_P | Z | 1.066962632e-10 | -2.700020559e-06 | 0.000000000e+00 | -2.700e-06 | -3.66e-13 |
| G | X | 5.100503131e-09 | 8.670116314e-06 | 0.000000000e+00 | +8.675e-06 | 3.87e-13 |
| G | Y | -2.244395200e+07 | 3.209623803e+06 | 1.923432820e+07 | -1.122e-03 | -5.00e-11 |
| G | Z | -3.171764209e+06 | 3.171764209e+06 | 0.000000000e+00 | -2.399e-05 | -1.07e-12 |
| Q1 | X | -2.009912237e-08 | 3.330006149e-05 | 0.000000000e+00 | +3.328e-05 | 4.53e-12 |
| Q1 | Y | -7.348864000e+06 | 1.961492321e+06 | 5.387371679e+06 | -6.436e-04 | -8.76e-11 |
| Q1 | Z | 1.082517300e-10 | -5.400041118e-06 | 0.000000000e+00 | -5.400e-06 | -7.35e-13 |
| A (informatif) | X | 0.000000000e+00 | -1.520002421e-05 | 0.000000000e+00 | -1.520e-05 | -1.90e-11 |
| A (informatif) | Y | 8.000000000e+05 | -6.818982118e+05 | -1.181017880e+05 | +1.713e-04 | 2.14e-10 |
| A (informatif) | Z | 0.000000000e+00 | 0.000000000e+00 | 0.000000000e+00 | +0.000e+00 | 0.00e+00 |
| Q3 (informatif) | X | 0.000000000e+00 | 4.400008452e-06 | 0.000000000e+00 | +4.400e-06 | 5.08e-12 |
| Q3 (informatif) | Y | -8.660000000e+05 | 9.127263561e+05 | -4.672635633e+04 | -1.972e-04 | -2.28e-10 |
| Q3 (informatif) | Z | 5.000000000e+05 | -5.000000000e+05 | 0.000000000e+00 | +8.999e-07 | 1.04e-12 |

### Table combinée du lot 33 (à ne pas lire)

| Cas | DY table combinée (N) | DY somme des 4 groupes (N) | DY ancrages seuls (N) |
|---|---:|---:|---:|
| EAU_A | 3.888582434e+06 | 4.625734174e+06 | 3.878357241e+06 |
| EAU_P | 1.656013964e+06 | 1.970113405e+06 | 1.652563206e+06 |
| G | 3.231000868e+06 | 3.841033151e+06 | 3.209623803e+06 |
| Q1 | 2.010466770e+06 | 2.383283762e+06 | 1.961492321e+06 |

### Symétrie (20 057 paires par cas, seuil 1e-6)

| Cas | Paires | Sans image | Pire écart relatif |
|---|---:|---:|---:|
| A | 20057 | 0 | 5.65e-11 |
| EAU_A | 20057 | 0 | 2.39e-11 |
| EAU_P | 20057 | 0 | 2.88e-11 |
| G | 20057 | 0 | 2.73e-11 |
| Q1 | 20057 | 0 | 5.70e-11 |
| Q3 | 20057 | 0 | 5.44e-11 |

### Pesanteur, cas G, direction verticale

| Terme | N |
|---|---:|
| Poids tubes + palplanches + tirants (maillage) | -1.386344209e+06 |
|   dont poids analytique | -1.386344209e+06 |
| Composante verticale de la pression sur l'écran | 3.879898937e-10 |
| Composante verticale de la poutre (poids propre + charge) | -1.785420000e+06 |
| Résultante verticale appliquée | -3.171764209e+06 |
| Réactions verticales bloquées (ancrages + pied des tubes) | 3.171764209e+06 |
| Bilan vertical | -2.399273217e-05 |
| Écart relatif | -1.07e-12 |
