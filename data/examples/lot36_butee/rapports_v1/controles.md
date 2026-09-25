# Contrôles — QUAI-CW-TEST-01

## Contrôles de validité de la décision 5 (cas élémentaires)

Ces contrôles portent sur des cas **élémentaires** : ils ne constituent pas une vérification de l'ouvrage (aucune combinaison n'est décidée dans la fiche) et ne portent aucun verdict de dimensionnement. Un dépassement est un constat sur les limites du modèle linéaire des ressorts.

### Signe : le ressort est en compression lorsque l'écran va vers le bassin (DY < 0)

| Cas | Nœuds | En compression | En traction | Cotes des nœuds en traction (m) | Réaction de traction maximale (kN) | Lieu |
|---|---:|---:|---:|---|---:|---|
| G | 10433 | 5867 | 4566 | -26.000 à -15.250 | 0.846 | z = -25.750 m, x = -5.833 m, y = -0.322 m ; TUBE_03 ; nœud 11429 |
| EAU_P | 10433 | 8652 | 1781 | -26.000 à -15.000 | 0.355 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| EAU_A | 10433 | 8652 | 1781 | -26.000 à -15.000 | 0.826 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| Q1 | 10433 | 8668 | 1765 | -26.000 à -15.000 | 0.319 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| Q3 | 10433 | 2605 | 7828 | -26.000 à -13.500 | 0.056 | z = -17.500 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 11134 |
| A | 10433 | 6771 | 3662 | -26.000 à -12.000 | 0.738 | z = -12.250 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 38889 |

### Butée : pression de réaction k·abs(DY) / A comparée à σ'p(z)

La force de butée d'un nœud est Σ (aire tributaire de chaque bande × σ'p de la couche de la bande à la cote du nœud), σ'p interpolée linéairement (`donnees_butee_combiwall_v1.md`) ; la pression initiale au repos n'est pas ajoutée (non modélisée, décision 5, item 3). Taux = force de réaction / force de butée.

| Cas | Nœuds comprimés | Taux maximal | Cote (m) | Porteur | Pression k·abs(DY)/A (kPa) | σ'p (kPa) | Nœuds au-delà de 100 % | Porteurs concernés |
|---|---:|---:|---:|---|---:|---:|---:|---|
| G | 5867 | 912.79 % | -12.000 | TUBE_04 | 429.92 | 47.10 | 2141 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| EAU_P | 8652 | 369.20 % | -12.000 | TUBE_06 | 173.89 | 47.10 | 1122 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| EAU_A | 8652 | 858.48 % | -12.000 | TUBE_06 | 404.35 | 47.10 | 2029 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| Q1 | 8668 | 335.55 % | -12.000 | TUBE_04 | 158.04 | 47.10 | 978 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| Q3 | 2605 | 9.22 % | -12.000 | TUBE_07 | 4.34 | 47.10 | 0 | - |
| A | 6771 | 1.41 % | -19.750 | TUBE_05 | 5.49 | 387.98 | 0 | - |

## Contrôles de niveau D

Non fournis à cette synthèse (option `--controles-d`).

