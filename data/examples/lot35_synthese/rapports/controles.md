# Contrôles — QUAI-CW-TEST-01-LOT30-REDUIT

## Contrôles de validité de la décision 5 (cas élémentaires)

Ces contrôles portent sur des cas **élémentaires** : ils ne constituent pas une vérification de l'ouvrage (aucune combinaison n'est décidée dans la fiche) et ne portent aucun verdict de dimensionnement. Un dépassement est un constat sur les limites du modèle linéaire des ressorts.

### Signe : le ressort est en compression lorsque l'écran va vers le bassin (DY < 0)

| Cas | Nœuds | En compression | En traction | Cotes des nœuds en traction (m) | Réaction de traction maximale (kN) | Lieu |
|---|---:|---:|---:|---|---:|---|
| G | 2651 | 2216 | 435 | -26.000 à -15.000 | 0.878 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_02 ; nœud 6170 |
| EAU_P | 2651 | 2176 | 475 | -26.000 à -15.000 | 0.347 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_02 ; nœud 6170 |
| EAU_A | 2651 | 2176 | 475 | -26.000 à -15.000 | 0.806 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_02 ; nœud 6170 |
| Q1 | 2651 | 2184 | 467 | -26.000 à -15.000 | 0.309 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_02 ; nœud 6170 |
| Q3 | 2651 | 577 | 2074 | -26.000 à -13.500 | 0.150 | z = -16.750 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5085 |
| A | 2651 | 1689 | 962 | -26.000 à -12.000 | 1.701 | z = -12.250 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9915 |

### Butée : pression de réaction k·abs(DY) / A comparée à σ'p(z)

La force de butée d'un nœud est Σ (aire tributaire de chaque bande × σ'p de la couche de la bande à la cote du nœud), σ'p interpolée linéairement (`donnees_butee_combiwall_v1.md`) ; la pression initiale au repos n'est pas ajoutée (non modélisée, décision 5, item 3). Taux = force de réaction / force de butée.

| Cas | Nœuds comprimés | Taux maximal | Cote (m) | Porteur | Pression k·abs(DY)/A (kPa) | σ'p (kPa) | Nœuds au-delà de 100 % | Porteurs concernés |
|---|---:|---:|---:|---|---:|---:|---:|---|
| G | 2216 | 937.28 % | -12.000 | TUBE_02 | 441.46 | 47.10 | 603 | PALP_01_02, PALP_02_03, TUBE_01, TUBE_02, TUBE_03 |
| EAU_P | 2176 | 361.90 % | -12.000 | TUBE_02 | 170.45 | 47.10 | 274 | PALP_01_02, PALP_02_03, TUBE_01, TUBE_02, TUBE_03 |
| EAU_A | 2176 | 841.34 % | -12.000 | TUBE_02 | 396.27 | 47.10 | 511 | PALP_01_02, PALP_02_03, TUBE_01, TUBE_02, TUBE_03 |
| Q1 | 2184 | 326.88 % | -12.000 | TUBE_02 | 153.96 | 47.10 | 246 | PALP_01_02, PALP_02_03, TUBE_01, TUBE_02, TUBE_03 |
| Q3 | 577 | 14.51 % | -12.000 | TUBE_01 | 6.83 | 47.10 | 0 | - |
| A | 1689 | 3.68 % | -19.500 | TUBE_02 | 13.96 | 379.35 | 0 | - |

## Contrôles de niveau D (équilibre et symétrie)

Seuil : 1e-06 (relatif). Bilan appliquée + réactions bloquées + ressorts = 0, par composante ; jamais un niveau E (aucune comparaison à une référence validée).

| Cas | X | Y | Z | Verdict |
|---|---:|---:|---:|---|
| EAU_A | -9.31e-14 | 1.03e-10 | 1.16e-13 | RÉUSSI |
| EAU_P | -5.09e-18 | 1.23e-11 | -5.43e-13 | RÉUSSI |
| G | 1.71e-16 | 4.33e-11 | -1.65e-13 | RÉUSSI |
| Q1 | -3.82e-13 | 1.76e-11 | -4.90e-13 | RÉUSSI |
| A | 3.75e-13 | -4.43e-11 | -5.00e-13 | informatif (aucun critère) |
| Q3 | 2.31e-13 | -1.38e-10 | 2.42e-12 | informatif (aucun critère) |

Symétrie des déplacements (paires de nœuds miroir), pire écart relatif :

| Cas | Paires vérifiées | Sans image miroir | Pire écart relatif |
|---|---:|---:|---:|
| A | 5102 | 0 | 1.35e-11 |
| EAU_A | 5102 | 0 | 1.09e-11 |
| EAU_P | 5102 | 0 | 2.03e-11 |
| G | 5102 | 0 | 1.18e-11 |
| Q1 | 5102 | 0 | 1.29e-11 |
| Q3 | 5102 | 0 | 1.20e-11 |

