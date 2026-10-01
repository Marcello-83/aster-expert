# Contrôles — QUAI-CW-TEST-01

## Contrôles de validité de la décision 5 (cas élémentaires)

Ces contrôles portent sur des cas **élémentaires** : ils ne constituent pas une vérification de l'ouvrage (aucune combinaison n'est décidée dans la fiche) et ne portent aucun verdict de dimensionnement. Un dépassement est un constat sur les limites du modèle linéaire des ressorts.

### Signe : le ressort est en compression lorsque l'écran va vers le bassin (DY < 0)

| Cas | Nœuds | En compression | En traction | Cotes des nœuds en traction (m) | Réaction de traction maximale (kN) | Lieu |
|---|---:|---:|---:|---|---:|---|
| G | 10433 | 8828 | 1605 | -26.000 à -15.000 | 0.899 | z = -18.250 m, x = 5.200 m, y = -0.710 m ; TUBE_07 ; nœud 29662 |
| EAU_P | 10433 | 8652 | 1781 | -26.000 à -15.000 | 0.358 | z = -18.250 m, x = -5.200 m, y = -0.710 m ; TUBE_03 ; nœud 12222 |
| EAU_A | 10433 | 8652 | 1781 | -26.000 à -15.000 | 0.832 | z = -18.250 m, x = 5.200 m, y = -0.710 m ; TUBE_07 ; nœud 29662 |
| Q1 | 10433 | 8668 | 1765 | -26.000 à -15.000 | 0.323 | z = -18.250 m, x = -5.200 m, y = -0.710 m ; TUBE_03 ; nœud 12222 |
| Q3 | 10433 | 2675 | 7758 | -26.000 à -13.500 | 0.058 | z = -17.750 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 11133 |
| A | 10433 | 6787 | 3646 | -26.000 à -12.000 | 0.759 | z = -12.250 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 38889 |

### Butée : pression de réaction k·abs(DY) / A comparée à σ'p(z)

La force de butée d'un nœud est Σ (aire tributaire de chaque bande × σ'p de la couche de la bande à la cote du nœud), σ'p interpolée linéairement (`donnees_butee_combiwall_v1.md`) ; la pression initiale au repos n'est pas ajoutée (non modélisée, décision 5, item 3). Taux = force de réaction / force de butée.

| Cas | Nœuds comprimés | Taux maximal | Cote (m) | Porteur | Pression k·abs(DY)/A (kPa) | σ'p (kPa) | Nœuds au-delà de 100 % | Porteurs concernés |
|---|---:|---:|---:|---|---:|---:|---:|---|
| G | 8828 | 956.47 % | -12.000 | TUBE_07 | 450.50 | 47.10 | 2413 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| EAU_P | 8652 | 371.85 % | -12.000 | TUBE_03 | 175.14 | 47.10 | 1122 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| EAU_A | 8652 | 864.70 % | -12.000 | TUBE_07 | 407.27 | 47.10 | 2029 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| Q1 | 8668 | 338.69 % | -12.000 | TUBE_07 | 159.52 | 47.10 | 1010 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| Q3 | 2675 | 10.66 % | -12.000 | TUBE_03 | 5.02 | 47.10 | 0 | - |
| A | 6787 | 1.47 % | -19.750 | TUBE_05 | 5.72 | 387.98 | 0 | - |

## Statique des efforts d'ensemble à la cote de dragage

Cote de la coupure : -11.75 m, première rangée au-dessus du dragage (-12 m) : la rangée du dragage porte les forces nodales des premiers ressorts, ce qui rend la coupure ambiguë (`aster_expert.report.section_statics`). Le corps inférieur (sous la coupure) est en équilibre sous la poussée, les ressorts, les réactions du pied et le poids ; la force que la partie haute exerce sur lui est l'opposée de leur somme. *Mesuré* : intégrale des efforts de coque (tubes et palplanches). *Attendu* : statique du corps inférieur. Écart = |mesuré − attendu| / max(|mesuré|, |attendu|). Grandeur **sensible à la discrétisation** (extrapolation des efforts par élément aux nœuds), non exacte : voir `docs/essais_lot37.md` pour le critère.

| Cas | Portée | T mesuré (kN) | T attendu (kN) | écart T | M mesuré (kN·m) | M attendu (kN·m) | écart M | N mesuré (kN) | N attendu (kN) | écart N |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G | ensemble | -5776.974 | -5828.658 | 0.89 % | 3850.039 | 3913.581 | 1.62 % | -3575.058 | -3679.923 | 2.85 % |
| G | cellule TUBE_05 | -722.122 | -728.582 | 0.89 % | 481.255 | 489.198 | 1.62 % | -446.882 | -459.990 | 2.85 % |
| EAU_P | ensemble | -2388.069 | -2410.513 | 0.93 % | 2488.822 | 2519.921 | 1.23 % | -556.010 | -598.787 | 7.14 % |
| EAU_P | cellule TUBE_05 | -298.509 | -301.314 | 0.93 % | 311.103 | 314.990 | 1.23 % | -69.501 | -74.848 | 7.14 % |
| EAU_A | ensemble | -5550.116 | -5602.251 | 0.93 % | 5787.618 | 5859.893 | 1.23 % | -1305.824 | -1405.278 | 7.08 % |
| EAU_A | cellule TUBE_05 | -693.764 | -700.281 | 0.93 % | 723.452 | 732.487 | 1.23 % | -163.228 | -175.660 | 7.08 % |
| Q1 | ensemble | -2062.113 | -2081.067 | 0.91 % | 2309.910 | 2337.695 | 1.19 % | -672.119 | -710.724 | 5.43 % |
| Q1 | cellule TUBE_05 | -257.764 | -260.133 | 0.91 % | 288.739 | 292.212 | 1.19 % | -84.015 | -88.841 | 5.43 % |
| Q3 | ensemble | 42.369 | 42.967 | 1.39 % | 618.420 | 621.665 | 0.52 % | 170.665 | 169.230 | 0.84 % |
| A | ensemble | 119.818 | 120.888 | 0.89 % | -741.925 | -747.188 | 0.70 % | 243.141 | 247.127 | 1.61 % |

## Contrôles de niveau D (équilibre et symétrie)

Seuil : 1e-06 (relatif). Bilan appliquée + réactions bloquées + ressorts = 0, par composante ; jamais un niveau E (aucune comparaison à une référence validée).

| Cas | X | Y | Z | Verdict |
|---|---:|---:|---:|---|
| EAU_A | 2.22e-13 | -1.92e-12 | 1.46e-17 | RÉUSSI |
| EAU_P | 3.80e-13 | -2.08e-12 | -1.36e-14 | RÉUSSI |
| G | 1.61e-13 | -8.63e-13 | -8.10e-14 | RÉUSSI |
| Q1 | 1.86e-13 | -2.76e-12 | -1.36e-14 | RÉUSSI |
| A | -6.25e-13 | 6.67e-12 | 1.25e-13 | informatif (aucun critère) |
| Q3 | 3.46e-13 | -5.48e-12 | -6.72e-17 | informatif (aucun critère) |

Symétrie des déplacements (paires de nœuds miroir), pire écart relatif :

| Cas | Paires vérifiées | Sans image miroir | Pire écart relatif |
|---|---:|---:|---:|
| A | 20057 | 0 | 5.21e-11 |
| EAU_A | 20057 | 0 | 3.27e-11 |
| EAU_P | 20057 | 0 | 4.12e-11 |
| G | 20057 | 0 | 3.85e-11 |
| Q1 | 20057 | 0 | 3.31e-11 |
| Q3 | 20057 | 0 | 4.85e-11 |

