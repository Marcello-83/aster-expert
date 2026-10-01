# Poutre de couronnement -- combinaisons de D17 (lot 38)

Source : `data/processed/runs/20260925T125131-c67e28a1/proc.0/fort.6` -- --- DIAGNOSTIC JOB : OK. `.comm` exécuté identique (sha256) à `data/examples/lot37_efforts/complet.comm`, inchangé par le lot 38 : aucune nouvelle exécution.

## Repère et conventions de signe

Repère global (décision du point 9) : X le long du quai (SYM_G -> SYM_D), Y vers la terre, Z ascendant, origine dans l'axe de TUBE_05 à la cote 0,00 CM. `N, VY, VZ, MT, MFY, MFZ` sont les composantes de `EFGE_ELNO` dans le repère « utilisateur » de la poutre (`POU_D_T`, axe porteur x_l = +X, U2.01.05 « Cas des poutres ») : N effort normal (traction positive), VY/VZ efforts tranchants, MT moment de torsion, MFY/MFZ moments de flexion. `EFGE_ELNO` n'étant pas moyenné par Code_Aster, les deux valeurs d'un nœud intérieur (une par élément adjacent) sont moyennées ici pour la lisibilité -- une simplification, jamais un contrôle d'équilibre.

## Géométrie de section et données D18

Section rectangulaire : HY = 2,50 m (largeur), HZ = 1,40 m (hauteur), axe à Y = 0,34 m, Z = 3,30 m. Béton C35/45, acier B500B, classe d'exposition XS3, durée d'utilisation 100 ans, enrobage nominal 65 mm, wk = 0,2 mm sous combinaison quasi permanente (décision D18, point 14).

## Combinaisons (18, décision D17, point 13)

| Nom | Famille | Coefficients |
| --- | --- | --- |
| `ELU_FOND_Q1_DOM_Q3_ACC_G_defav` | ELU fondamentale | G=1.35, EAU_P=1.35, Q1=1.5, Q3=1.05 |
| `ELU_FOND_Q1_DOM_G_defav` | ELU fondamentale | G=1.35, EAU_P=1.35, Q1=1.5 |
| `ELU_FOND_Q1_DOM_Q3_ACC_G_favo` | ELU fondamentale | G=1, EAU_P=1, Q1=1.5, Q3=1.05 |
| `ELU_FOND_Q1_DOM_G_favo` | ELU fondamentale | G=1, EAU_P=1, Q1=1.5 |
| `ELU_FOND_Q3_DOM_Q1_ACC_G_defav` | ELU fondamentale | G=1.35, EAU_P=1.35, Q3=1.5, Q1=1.05 |
| `ELU_FOND_Q3_DOM_G_defav` | ELU fondamentale | G=1.35, EAU_P=1.35, Q3=1.5 |
| `ELU_FOND_Q3_DOM_Q1_ACC_G_favo` | ELU fondamentale | G=1, EAU_P=1, Q3=1.5, Q1=1.05 |
| `ELU_FOND_Q3_DOM_G_favo` | ELU fondamentale | G=1, EAU_P=1, Q3=1.5 |
| `ELU_ACCIDENTELLE` | ELU accidentelle | G=1, EAU_A=1, A=1, Q1=0.5 |
| `ELS_CARA_Q1_DOM_Q3_ACC` | ELS caractéristique | G=1, EAU_P=1, Q1=1, Q3=0.7 |
| `ELS_CARA_Q1_DOM` | ELS caractéristique | G=1, EAU_P=1, Q1=1 |
| `ELS_CARA_Q3_DOM_Q1_ACC` | ELS caractéristique | G=1, EAU_P=1, Q3=1, Q1=0.7 |
| `ELS_CARA_Q3_DOM` | ELS caractéristique | G=1, EAU_P=1, Q3=1 |
| `ELS_FREQ_Q1_DOM_Q3_ACC` | ELS fréquente | G=1, EAU_P=1, Q1=0.5, Q3=0.7 |
| `ELS_FREQ_Q1_DOM` | ELS fréquente | G=1, EAU_P=1, Q1=0.5 |
| `ELS_FREQ_Q3_DOM_Q1_ACC` | ELS fréquente | G=1, EAU_P=1, Q3=0.5, Q1=0.7 |
| `ELS_FREQ_Q3_DOM` | ELS fréquente | G=1, EAU_P=1, Q3=0.5 |
| `ELS_QUASI_PERMANENTE` | ELS quasi permanente | G=1, EAU_P=1, Q1=0.3, Q3=0 |

## Contrôle manuel

Combinaison `ELU_FOND_Q3_DOM_G_defav` (ELU fondamentale, Q3 dominante, sans Q1, γG défavorable), nœud 2259 (bollard, X ≈ 0) : 1,35·(G+EAU_P) + 1,5·Q3, recalculé à la main à partir des tables élémentaires du `.mess`, contre `combine()` -- écart absolu maximal 8.470e-22 (unités N, N.m).

| Composante | À la main | `combine()` | Écart |
| --- | --- | --- | --- |
| N | 6.079173e+02 | 6.079173e+02 | 0.000e+00 |
| VY | 5.265271e-06 | 5.265271e-06 | 0.000e+00 |
| VZ | 1.696696e-06 | 1.696696e-06 | 0.000e+00 |
| MT | 5.516096e-06 | 5.516096e-06 | 8.470e-22 |
| MFY | 7.849687e+05 | 7.849687e+05 | 0.000e+00 |
| MFZ | 2.183517e+06 | 2.183517e+06 | 0.000e+00 |

## Extrema

Voir `extrema.csv` : pour chaque combinaison, le nœud où chaque composante est maximale en valeur absolue, avec les composantes concomitantes.

