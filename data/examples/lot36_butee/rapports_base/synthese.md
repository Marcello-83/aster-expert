# Synthèse des résultats — QUAI-CW-TEST-01

## Ce que ce document est, et n'est pas

- Des **résultats de cas élémentaires** (G, EAU_P, EAU_A, Q1, Q3, A), lus dans le MED de résultats de Code_Aster. Aucune combinaison n'est faite, aucun verdict de dimensionnement n'est porté : la fiche ne décide aucune combinaison.
- Niveau de validation du calcul : C (exécuté jusqu'à `FIN`) avec contrôles D (voir plus bas) ; jamais E.
- Les grandeurs sont **linéaires** (modèle élastique, ressorts sans plafond) : un dépassement de la butée est un constat sur les limites du modèle, non une rupture calculée.

## Provenance

- **MED de résultats** : `data/processed/runs/20260925T090253-1f383214/proc.0/fort.80` (SHA-256 `c3f19a81aa749aaa7ca2a3edb67c35f3721a4162c7986cf76aeddfc8b88656d6`), relu par `medcoupling` dans le conteneur : chaque grandeur de cette synthèse vient de ses champs.
- Contre-vérification : listing `data/processed/runs/20260925T090253-1f383214/proc.0/fort.6` (SHA-256 `242b6d72cfb08dcf94789d3e0da94bb329cbc8382a8cbfb8b4a682a88fb6c2c7`) ; écart relatif maximal entre le MED et les tables imprimées, 72 tables : 4.88e-13.
- `.comm` : SHA-256 `5a2b9be4196638d9c6da0c21cd121b0a912e4f229744732f56ecde0774f37489`
- Données : `data/examples/combiwall_model_data.yaml`

## Repères, champs et unités

| Grandeur | Champ | Composantes | Repère | Unité | Source du repère |
|---|---|---|---|---|---|
| Déplacement horizontal (tête, profils) | DEPL | DY | global : X le long du quai de SYM_G vers SYM_D, Y vers la terre, Z ascendant (décision du point 9) ; DY < 0 : vers le bassin | mm | fiche, point 9 |
| Effort axial d'un tirant | EFGE_ELNO | N | local de la barre (axe du tirant) ; N > 0 en traction | kN | U2.01.05 (efforts de poutre en repère « utilisateur ») |
| Efforts généralisés d'un tube (DKT) | EFGE_ELNO (par élément et par nœud, sans moyenne) | NXX, NYY, MXX, MYY | local « utilisateur » de la facette : x_l = projection de VECTEUR = (0, 0, 1) sur le plan de la facette, donc **verticale** ; z_l = normale ; y_l = z_l ^ x_l (tangente horizontale). NXX et MXX : effort normal et moment de flexion **verticaux** ; NYY et MYY : circonférentiels | kN/m ; kN·m/m (par mètre de largeur) | U4.42.01, mot clé COQUE, opérande ANGL_REP / VECTEUR ; U2.01.05 |
| Efforts généralisés d'une palplanche (ELAS_COQUE) | EFGE_NOEU uniquement (décision 2) | NXX, NYY, NXY, MXX, MYY, MXY, QX, QY | local « utilisateur » : x_l = projection de VECTEUR = L (voir ci-dessous) sur le plan de la palplanche (plan Y = 0) ; moyenne arithmétique aux nœuds des valeurs par élément, restreinte aux mailles PALPS | kN/m ; kN·m/m | U4.42.01 COQUE ; U2.01.05 ; fiche, point 1 (décision 2) |
| Efforts d'une poutre de couronnement (POU_D_E) | EFGE_ELNO (par élément et par nœud, sans moyenne) | N, VY, VZ, MT, MFY, MFZ | local de la poutre : x_l le long de l'élément (du premier au second nœud), y_l parallèle à Y global et z_l = x_l ^ y_l = Z global (repère par défaut, ANGL_VRIL = 0). MFY : moment de flexion dans le plan vertical (autour de y_l) ; MFZ : dans le plan horizontal | kN ; kN·m | U4.42.01, mot clé ORIENTATION (remarques) ; U2.01.05 |
| Réactions d'appui | REAC_NODA (RESULTANTE) | DX, DY, DZ | global ; seules les composantes bloquées comptent (ANCRAGES : DX, DY, DZ ; PIED_TUBES : DZ ; SYM_G, SYM_D : DX) | kN | lots 23 et 34 (constat de la fiche, points 1 et 8) |
| Force des ressorts sur l'écran | DEPL/DY des nœuds à ressort × raideur | −k·DY | global, direction Y (positive vers la terre) | kN | fiche, point 4 ; K_T_D_N = (0, k, 0) |

Axe L des palplanches (`VECTEUR`, repère global) : (0.0, 0.0, 1.0) (vertical). Tubes : `VECTEUR = (0, 0, 1)`.
Orientation des éléments de poutre : chaque élément est listé du X le plus bas au plus haut, donc x_l = +X, y_l = +Y, z_l = +Z (déduit de l'ordre des lignes de la table, non de la documentation).

Tubes : axes à X = -10.4, -7.8, -5.2, -2.6, 0, 2.6, 5.2, 7.8, 10.4 m, rayon 0.71 m ; « porteur » d'un point = tube (cercle de rayon R) ou palplanche (plan Y = 0) le portant.

## Résultats par cas élémentaire

### Cas élémentaire G

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -15.6652 mm, z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001. Étendue sur les 322 nœuds des anneaux de tête : de -15.6652 à -15.5681 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 324.584 | 324.584 | 324.584 |
| 2 | -7.800 | 393.981 | 393.981 | 393.981 |
| 3 | -5.200 | 395.083 | 395.083 | 395.083 |
| 4 | -2.600 | 395.968 | 395.968 | 395.968 |
| 5 | 0.000 | 396.297 | 396.297 | 396.297 |
| 6 | 2.600 | 395.968 | 395.968 | 395.968 |
| 7 | 5.200 | 395.083 | 395.083 | 395.083 |
| 8 | 7.800 | 393.981 | 393.981 | 393.981 |
| 9 | 10.400 | 324.584 | 324.584 | 324.584 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1871.711 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -1077.240 | z = -4.500 m, x = -7.800 m, y = 0.710 m ; TUBE_02 ; maille 3422 ; nœud 5735 |
| NYY | 6797.398 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -1332.756 | z = 2.250 m, x = 10.289 m, y = 0.701 m ; TUBE_09 ; maille 34614 ; nœud 35298 |
| MXX | 81.451 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -112.951 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 |
| MYY | 83.737 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -33.885 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 265.120 | z = -13.000 m, x = -0.946 m, y = 0.000 m ; PALP_04_05 ; nœud 38643 | -185.918 | z = -5.250 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37839 |
| NYY | 0.106 | z = 2.600 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37392 | -1.441 | z = -13.250 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 19871 |
| NXY | 269.535 | z = -11.250 m, x = 1.890 m, y = 0.000 m ; TUBE_06 ; nœud 24238 | -269.535 | z = -11.250 m, x = -1.890 m, y = 0.000 m ; TUBE_04 ; nœud 13489 |
| MXX | 210.050 | z = -12.750 m, x = 1.418 m, y = 0.000 m ; PALP_05_06 ; nœud 38933 | -130.295 | z = -7.750 m, x = 1.418 m, y = 0.000 m ; PALP_05_06 ; nœud 39077 |
| MYY | 3.183 | z = -5.750 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 3441 | -2.535 | z = -13.750 m, x = -4.490 m, y = 0.000 m ; TUBE_03 ; nœud 9013 |
| MXY | 0.173 | z = -10.750 m, x = -1.654 m, y = 0.000 m ; PALP_04_05 ; nœud 38651 | -0.173 | z = -10.750 m, x = 1.654 m, y = 0.000 m ; PALP_05_06 ; nœud 39116 |
| QX | 482.817 | z = 2.600 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -144.611 | z = -12.000 m, x = 1.654 m, y = 0.000 m ; PALP_05_06 ; nœud 37471 |
| QY | 15.492 | z = -13.500 m, x = -1.890 m, y = 0.000 m ; TUBE_04 ; nœud 13372 | -15.492 | z = -13.500 m, x = 1.890 m, y = 0.000 m ; TUBE_06 ; nœud 24230 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.040 | z = 3.300 m, x = 1.300 m, y = 0.340 m ; maille 79667 ; nœud 37594 | -0.090 | z = 3.300 m, x = -10.075 m, y = 0.340 m ; maille 79632 ; nœud 37563 |
| VY | 103.777 | z = 3.300 m, x = 8.125 m, y = 0.340 m ; maille 79688 ; nœud 37612 | -103.777 | z = 3.300 m, x = -8.125 m, y = 0.340 m ; maille 79638 ; nœud 37569 |
| VZ | 31.982 | z = 3.300 m, x = -10.075 m, y = 0.340 m ; maille 79632 ; nœud 37563 | -31.982 | z = 3.300 m, x = 9.425 m, y = 0.340 m ; maille 79692 ; nœud 37616 |
| MT | 58.520 | z = 3.300 m, x = 9.100 m, y = 0.340 m ; maille 79691 ; nœud 37615 | -58.520 | z = 3.300 m, x = -8.775 m, y = 0.340 m ; maille 79636 ; nœud 37567 |
| MFY | 25.343 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79654 ; nœud 2258 | -93.027 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |
| MFZ | 205.412 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -399.538 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **3209.624** | **-1128.152** |
| PIED_TUBES | -0.000 | 0.000 | **4299.916** |
| SYM_G | **48.938** | 315.705 | -150.778 |
| SYM_D | **-48.938** | 315.705 | -150.778 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 3209.624 kN contre 3209.624 kN de réaction d'ancrage selon Y (écart relatif 1.5e-16) ; Σ N × sin θ = -1167.972 kN contre -1128.152 kN selon Z (écart relatif -3.5e-02, sous pesanteur l'ancrage porte en plus une part du poids propre du tirant : l'écart vertical n'est pas un défaut de lecture).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 15247.190 ; marne compacte 3987.138 ; total 19234.328.

### Cas élémentaire EAU_P

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -7.9221 mm, z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134. Étendue sur les 322 nœuds des anneaux de tête : de -7.9221 à -7.8720 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 167.125 | 167.125 | 167.125 |
| 2 | -7.800 | 202.855 | 202.855 | 202.855 |
| 3 | -5.200 | 203.419 | 203.419 | 203.419 |
| 4 | -2.600 | 203.871 | 203.871 | 203.871 |
| 5 | 0.000 | 204.040 | 204.040 | 204.040 |
| 6 | 2.600 | 203.871 | 203.871 | 203.871 |
| 7 | 5.200 | 203.419 | 203.419 | 203.419 |
| 8 | 7.800 | 202.855 | 202.855 | 202.855 |
| 9 | 10.400 | 167.125 | 167.125 | 167.125 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 976.112 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2299 ; nœud 146 | -502.772 | z = -3.750 m, x = -7.800 m, y = 0.710 m ; TUBE_02 ; maille 3424 ; nœud 5738 |
| NYY | 3498.159 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2299 ; nœud 146 | -685.423 | z = 2.250 m, x = -10.289 m, y = 0.701 m ; TUBE_01 ; maille 2299 ; nœud 4452 |
| MXX | 41.926 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 146 | -58.124 | z = 2.600 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 147 |
| MYY | 43.113 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 146 | -17.437 | z = 2.600 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 147 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 126.022 | z = -13.000 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 38886 | -53.474 | z = -4.750 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37841 |
| NYY | 0.028 | z = 2.600 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37392 | -0.533 | z = -13.000 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17730 |
| NXY | 98.414 | z = -11.250 m, x = 1.890 m, y = 0.000 m ; TUBE_06 ; nœud 24238 | -98.414 | z = -11.250 m, x = -1.890 m, y = 0.000 m ; TUBE_04 ; nœud 13489 |
| MXX | 85.589 | z = -12.750 m, x = 1.418 m, y = 0.000 m ; PALP_05_06 ; nœud 38933 | -47.908 | z = -6.750 m, x = 1.418 m, y = 0.000 m ; PALP_05_06 ; nœud 39081 |
| MYY | 1.588 | z = -3.750 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 3449 | -1.035 | z = -13.500 m, x = 4.490 m, y = 0.000 m ; TUBE_07 ; nœud 28590 |
| MXY | 0.069 | z = -10.250 m, x = -1.654 m, y = 0.000 m ; PALP_04_05 ; nœud 38653 | -0.069 | z = -10.250 m, x = 1.654 m, y = 0.000 m ; PALP_05_06 ; nœud 39118 |
| QX | 244.690 | z = 2.600 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -63.590 | z = 2.600 m, x = -9.454 m, y = 0.000 m ; PALP_01_02 ; nœud 37394 |
| QY | 6.827 | z = -3.750 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 36258 | -6.827 | z = -3.750 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 3449 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.020 | z = 3.300 m, x = 0.325 m, y = 0.340 m ; maille 79664 ; nœud 37591 | -0.045 | z = 3.300 m, x = -10.075 m, y = 0.340 m ; maille 79632 ; nœud 37563 |
| VY | 53.433 | z = 3.300 m, x = 7.800 m, y = 0.340 m ; maille 79687 ; nœud 2262 | -53.433 | z = 3.300 m, x = -8.450 m, y = 0.340 m ; maille 79637 ; nœud 37568 |
| VZ | 15.661 | z = 3.300 m, x = -8.775 m, y = 0.340 m ; maille 79636 ; nœud 37567 | -15.661 | z = 3.300 m, x = 9.425 m, y = 0.340 m ; maille 79692 ; nœud 37616 |
| MT | 30.522 | z = 3.300 m, x = 7.800 m, y = 0.340 m ; maille 79687 ; nœud 2262 | -30.522 | z = 3.300 m, x = -9.750 m, y = 0.340 m ; maille 79633 ; nœud 37564 |
| MFY | 12.363 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79654 ; nœud 2258 | -45.506 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |
| MFZ | 105.769 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 | -205.719 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **1652.563** | **-601.363** |
| PIED_TUBES | -0.000 | 0.000 | **601.363** |
| SYM_G | **-145.590** | 158.775 | -139.473 |
| SYM_D | **145.590** | 158.775 | -139.473 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 1652.563 kN contre 1652.563 kN de réaction d'ancrage selon Y (écart relatif 0.0e+00) ; Σ N × sin θ = -601.363 kN contre -601.363 kN selon Z (écart relatif 1.9e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 4946.552 ; marne compacte 770.085 ; total 5716.637.

### Cas élémentaire EAU_A

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -18.5828 mm, z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134. Étendue sur les 322 nœuds des anneaux de tête : de -18.5828 à -18.4653 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 392.221 | 392.221 | 392.221 |
| 2 | -7.800 | 476.075 | 476.075 | 476.075 |
| 3 | -5.200 | 477.398 | 477.398 | 477.398 |
| 4 | -2.600 | 478.460 | 478.460 | 478.460 |
| 5 | 0.000 | 478.856 | 478.856 | 478.856 |
| 6 | 2.600 | 478.460 | 478.460 | 478.460 |
| 7 | 5.200 | 477.398 | 477.398 | 477.398 |
| 8 | 7.800 | 476.075 | 476.075 | 476.075 |
| 9 | 10.400 | 392.221 | 392.221 | 392.221 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 2296.070 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2299 ; nœud 146 | -1163.560 | z = 2.600 m, x = -10.289 m, y = 0.701 m ; TUBE_01 ; maille 2185 ; nœud 140 |
| NYY | 8207.294 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2299 ; nœud 146 | -1614.601 | z = 2.250 m, x = -10.289 m, y = 0.701 m ; TUBE_01 ; maille 2299 ; nœud 4452 |
| MXX | 98.392 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 146 | -136.396 | z = 2.600 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 147 |
| MYY | 101.179 | z = 2.500 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 146 | -40.919 | z = 2.600 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 147 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 292.687 | z = -13.000 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 38886 | -124.683 | z = -4.750 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37841 |
| NYY | 0.065 | z = 2.600 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37392 | -1.240 | z = -13.000 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17730 |
| NXY | 228.890 | z = -11.250 m, x = 1.890 m, y = 0.000 m ; TUBE_06 ; nœud 24238 | -228.890 | z = -11.250 m, x = -1.890 m, y = 0.000 m ; TUBE_04 ; nœud 13489 |
| MXX | 199.154 | z = -12.750 m, x = 1.418 m, y = 0.000 m ; PALP_05_06 ; nœud 38933 | -112.061 | z = -6.750 m, x = -1.418 m, y = 0.000 m ; PALP_04_05 ; nœud 38718 |
| MYY | 3.663 | z = -4.000 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 36257 | -2.406 | z = -13.500 m, x = 4.490 m, y = 0.000 m ; TUBE_07 ; nœud 28590 |
| MXY | 0.160 | z = -10.250 m, x = -1.654 m, y = 0.000 m ; PALP_04_05 ; nœud 38653 | -0.160 | z = -10.250 m, x = 1.654 m, y = 0.000 m ; PALP_05_06 ; nœud 39118 |
| QX | 574.729 | z = 2.600 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -149.320 | z = 2.600 m, x = 9.454 m, y = 0.000 m ; PALP_08_09 ; nœud 37559 |
| QY | 15.760 | z = -4.000 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 36257 | -15.760 | z = -4.000 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 3448 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.046 | z = 3.300 m, x = 0.975 m, y = 0.340 m ; maille 79666 ; nœud 37593 | -0.105 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |
| VY | 125.400 | z = 3.300 m, x = 7.800 m, y = 0.340 m ; maille 79687 ; nœud 2262 | -125.400 | z = 3.300 m, x = -8.125 m, y = 0.340 m ; maille 79638 ; nœud 37569 |
| VZ | 36.754 | z = 3.300 m, x = -8.450 m, y = 0.340 m ; maille 79637 ; nœud 37568 | -36.754 | z = 3.300 m, x = 9.425 m, y = 0.340 m ; maille 79692 ; nœud 37616 |
| MT | 71.631 | z = 3.300 m, x = 8.775 m, y = 0.340 m ; maille 79690 ; nœud 37614 | -71.631 | z = 3.300 m, x = -9.750 m, y = 0.340 m ; maille 79633 ; nœud 37564 |
| MFY | 29.015 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79654 ; nœud 2258 | -106.796 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |
| MFZ | 248.227 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -482.797 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **3878.357** | **-1411.322** |
| PIED_TUBES | 0.000 | 0.000 | **1411.322** |
| SYM_G | **-346.439** | 373.688 | -327.322 |
| SYM_D | **346.439** | 373.688 | -327.322 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 3878.357 kN contre 3878.357 kN de réaction d'ancrage selon Y (écart relatif -2.4e-16) ; Σ N × sin θ = -1411.322 kN contre -1411.322 kN selon Z (écart relatif 3.3e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 11513.331 ; marne compacte 1803.112 ; total 13316.443.

### Cas élémentaire Q1

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -9.3084 mm, z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001. Étendue sur les 322 nœuds des anneaux de tête : de -9.3084 à -9.2489 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 198.367 | 198.367 | 198.367 |
| 2 | -7.800 | 240.777 | 240.777 | 240.777 |
| 3 | -5.200 | 241.446 | 241.446 | 241.446 |
| 4 | -2.600 | 241.983 | 241.983 | 241.983 |
| 5 | 0.000 | 242.183 | 242.183 | 242.183 |
| 6 | 2.600 | 241.983 | 241.983 | 241.983 |
| 7 | 5.200 | 241.446 | 241.446 | 241.446 |
| 8 | 7.800 | 240.777 | 240.777 | 240.777 |
| 9 | 10.400 | 198.367 | 198.367 | 198.367 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1185.438 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34614 ; nœud 2119 | -570.042 | z = 2.600 m, x = 10.289 m, y = 0.701 m ; TUBE_09 ; maille 34615 ; nœud 2120 |
| NYY | 4146.276 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34614 ; nœud 2119 | -824.805 | z = 2.250 m, x = 10.289 m, y = 0.701 m ; TUBE_09 ; maille 34614 ; nœud 35298 |
| MXX | 49.747 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -68.971 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 |
| MYY | 51.168 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -20.691 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 110.645 | z = -13.000 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 38886 | -52.793 | z = -4.750 m, x = 8.982 m, y = 0.000 m ; PALP_08_09 ; nœud 39974 |
| NYY | 0.030 | z = 2.600 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37392 | -0.486 | z = -13.000 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17730 |
| NXY | 90.014 | z = -11.250 m, x = 1.890 m, y = 0.000 m ; TUBE_06 ; nœud 24238 | -90.014 | z = -11.250 m, x = -1.890 m, y = 0.000 m ; TUBE_04 ; nœud 13489 |
| MXX | 74.447 | z = -12.750 m, x = 1.418 m, y = 0.000 m ; PALP_05_06 ; nœud 38933 | -35.653 | z = -7.750 m, x = -1.418 m, y = 0.000 m ; PALP_04_05 ; nœud 38714 |
| MYY | 1.904 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -0.902 | z = -13.500 m, x = -4.490 m, y = 0.000 m ; TUBE_03 ; nœud 9012 |
| MXY | 0.075 | z = 2.600 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 2184 | -0.075 | z = 2.600 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 77 |
| QX | 217.767 | z = 2.600 m, x = -9.690 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -56.636 | z = 2.600 m, x = -9.454 m, y = 0.000 m ; PALP_01_02 ; nœud 37394 |
| QY | 8.712 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -8.712 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.024 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79655 ; nœud 2258 | -0.053 | z = 3.300 m, x = -10.075 m, y = 0.340 m ; maille 79632 ; nœud 37563 |
| VY | 63.421 | z = 3.300 m, x = 7.800 m, y = 0.340 m ; maille 79687 ; nœud 2262 | -63.421 | z = 3.300 m, x = -8.125 m, y = 0.340 m ; maille 79638 ; nœud 37569 |
| VZ | 18.589 | z = 3.300 m, x = -9.750 m, y = 0.340 m ; maille 79633 ; nœud 37564 | -18.589 | z = 3.300 m, x = 8.450 m, y = 0.340 m ; maille 79689 ; nœud 37613 |
| MT | 36.228 | z = 3.300 m, x = 8.125 m, y = 0.340 m ; maille 79688 ; nœud 37612 | -36.228 | z = 3.300 m, x = -8.450 m, y = 0.340 m ; maille 79637 ; nœud 37568 |
| MFY | 14.674 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79654 ; nœud 2258 | -54.013 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |
| MFZ | 125.542 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -244.176 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **1961.492** | **-713.781** |
| PIED_TUBES | 0.000 | 0.000 | **713.781** |
| SYM_G | **-245.358** | 210.896 | -165.674 |
| SYM_D | **245.358** | 210.896 | -165.674 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 1961.492 kN contre 1961.492 kN de réaction d'ancrage selon Y (écart relatif -1.2e-16) ; Σ N × sin θ = -713.781 kN contre -713.781 kN selon Z (écart relatif 0.0e+00, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 4660.732 ; marne compacte 726.639 ; total 5387.372.

### Cas élémentaire Q3

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -4.3020 mm, z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001. Étendue sur les 322 nœuds des anneaux de tête : de -4.3020 à -4.0091 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 88.775 | 88.775 | 88.775 |
| 2 | -7.800 | 108.945 | 108.945 | 108.945 |
| 3 | -5.200 | 112.403 | 112.403 | 112.403 |
| 4 | -2.600 | 116.411 | 116.411 | 116.411 |
| 5 | 0.000 | 118.214 | 118.214 | 118.214 |
| 6 | 2.600 | 116.411 | 116.411 | 116.411 |
| 7 | 5.200 | 112.403 | 112.403 | 112.403 |
| 8 | 7.800 | 108.945 | 108.945 | 108.945 |
| 9 | 10.400 | 88.775 | 88.775 | 88.775 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 638.689 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34614 ; nœud 2119 | -152.912 | z = 2.600 m, x = 10.289 m, y = 0.701 m ; TUBE_09 ; maille 34730 ; nœud 2120 |
| NYY | 1865.083 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34614 ; nœud 2119 | -368.931 | z = 2.250 m, x = 10.289 m, y = 0.701 m ; TUBE_09 ; maille 34614 ; nœud 35298 |
| MXX | 22.236 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -30.800 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 |
| MYY | 22.889 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -9.240 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 31.879 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -12.450 | z = 2.600 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 2184 |
| NYY | 0.033 | z = -18.000 m, x = 8.982 m, y = 0.000 m ; PALP_08_09 ; nœud 37540 | -0.049 | z = -18.000 m, x = 1.182 m, y = 0.000 m ; PALP_05_06 ; nœud 37468 |
| NXY | 16.531 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -16.531 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 |
| MXX | 7.366 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -1.945 | z = 2.600 m, x = -0.946 m, y = 0.000 m ; PALP_04_05 ; nœud 37463 |
| MYY | 0.034 | z = 2.600 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 37490 | -0.121 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| MXY | 0.008 | z = 2.500 m, x = -0.946 m, y = 0.000 m ; PALP_04_05 ; nœud 37459 | -0.008 | z = 2.500 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 37486 |
| QX | 9.570 | z = 2.600 m, x = 3.310 m, y = 0.000 m ; TUBE_06 ; nœud 1281 | -2.777 | z = 2.600 m, x = 3.546 m, y = 0.000 m ; PALP_06_07 ; nœud 37514 |
| QY | 0.667 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -0.667 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.404 | z = 3.300 m, x = 0.650 m, y = 0.340 m ; maille 79665 ; nœud 37592 | -0.212 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |
| VY | 381.284 | z = 3.300 m, x = 0.325 m, y = 0.340 m ; maille 79664 ; nœud 37591 | -381.284 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79655 ; nœud 2258 |
| VZ | 180.509 | z = 3.300 m, x = -0.975 m, y = 0.340 m ; maille 79660 ; nœud 37588 | -180.509 | z = 3.300 m, x = 0.975 m, y = 0.340 m ; maille 79666 ; nœud 37593 |
| MT | 263.946 | z = 3.300 m, x = -2.275 m, y = 0.340 m ; maille 79656 ; nœud 37584 | -263.946 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 |
| MFY | 542.010 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -178.905 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |
| MFZ | 1515.327 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -864.289 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **912.726** | **-332.138** |
| PIED_TUBES | 0.000 | -0.000 | **-167.862** |
| SYM_G | **-232.225** | 136.925 | -75.691 |
| SYM_D | **232.225** | 136.925 | -75.691 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 912.726 kN contre 912.726 kN de réaction d'ancrage selon Y (écart relatif -1.3e-16) ; Σ N × sin θ = -332.138 kN contre -332.138 kN selon Z (écart relatif 3.5e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 2.758 ; marne compacte -49.485 ; total -46.726.

### Cas élémentaire A

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue 3.4187 mm, z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001. Étendue sur les 322 nœuds des anneaux de tête : de 3.0202 à 3.4187 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | -65.795 | -65.795 | -65.795 |
| 2 | -7.800 | -80.860 | -80.860 | -80.860 |
| 3 | -5.200 | -83.766 | -83.766 | -83.766 |
| 4 | -2.600 | -87.366 | -87.366 | -87.366 |
| 5 | 0.000 | -90.071 | -90.071 | -90.071 |
| 6 | 2.600 | -87.366 | -87.366 | -87.366 |
| 7 | 5.200 | -83.766 | -83.766 | -83.766 |
| 8 | 7.800 | -80.860 | -80.860 | -80.860 |
| 9 | 10.400 | -65.795 | -65.795 | -65.795 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 2065.203 | z = 2.600 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; maille 19665 ; nœud 1204 | -1205.977 | z = 2.600 m, x = -0.675 m, y = -0.219 m ; TUBE_05 ; maille 18630 ; nœud 1148 |
| NYY | 619.561 | z = 2.600 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; maille 19665 ; nœud 1204 | -1373.954 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34614 ; nœud 2119 |
| MXX | 22.951 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 | -16.518 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 |
| MYY | 6.885 | z = 2.600 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2121 | -16.976 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 179.713 | z = 0.250 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 39007 | -606.825 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| NYY | 0.188 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -0.366 | z = -0.500 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17806 |
| NXY | 233.760 | z = 1.500 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 19928 | -233.760 | z = 1.500 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17856 |
| MXX | 44.655 | z = 2.500 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 999 | -36.501 | z = 1.250 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17857 |
| MYY | 0.354 | z = 1.000 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 995 | -0.423 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| MXY | 0.057 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -0.057 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| QX | 111.334 | z = 2.000 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 997 | -296.857 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| QY | 2.451 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -2.451 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.438 | z = 3.300 m, x = 1.625 m, y = 0.340 m ; maille 79668 ; nœud 37595 | -0.189 | z = 3.300 m, x = 7.150 m, y = 0.340 m ; maille 79685 ; nœud 37610 |
| VY | 340.944 | z = 3.300 m, x = -0.975 m, y = 0.340 m ; maille 79660 ; nœud 37588 | -340.944 | z = 3.300 m, x = 0.650 m, y = 0.340 m ; maille 79665 ; nœud 37592 |
| VZ | 7.055 | z = 3.300 m, x = -1.950 m, y = 0.340 m ; maille 79657 ; nœud 37585 | -7.055 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 79670 ; nœud 37597 |
| MT | 519.047 | z = 3.300 m, x = -2.275 m, y = 0.340 m ; maille 79656 ; nœud 37584 | -519.047 | z = 3.300 m, x = 1.950 m, y = 0.340 m ; maille 79669 ; nœud 37596 |
| MFY | 20.426 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -12.014 | z = 3.300 m, x = 7.800 m, y = 0.340 m ; maille 79686 ; nœud 2262 |
| MFZ | 747.348 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 | -1341.752 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **-0.000** | **-681.898** | **248.141** |
| PIED_TUBES | -0.000 | 0.000 | **-248.141** |
| SYM_G | **172.183** | -107.963 | 52.800 |
| SYM_D | **-172.183** | -107.963 | 52.800 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = -681.898 kN contre -681.898 kN de réaction d'ancrage selon Y (écart relatif 1.7e-16) ; Σ N × sin θ = 248.141 kN contre 248.141 kN selon Z (écart relatif -1.2e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse -209.595 ; marne compacte 91.493 ; total -118.102.

## Contrôles de validité de la décision 5 (cas élémentaires)

Ces contrôles portent sur des cas **élémentaires** : ils ne constituent pas une vérification de l'ouvrage (aucune combinaison n'est décidée dans la fiche) et ne portent aucun verdict de dimensionnement. Un dépassement est un constat sur les limites du modèle linéaire des ressorts.

### Signe : le ressort est en compression lorsque l'écran va vers le bassin (DY < 0)

| Cas | Nœuds | En compression | En traction | Cotes des nœuds en traction (m) | Réaction de traction maximale (kN) | Lieu |
|---|---:|---:|---:|---|---:|---|
| G | 10433 | 8828 | 1605 | -26.000 à -15.000 | 0.894 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| EAU_P | 10433 | 8652 | 1781 | -26.000 à -15.000 | 0.355 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| EAU_A | 10433 | 8652 | 1781 | -26.000 à -15.000 | 0.826 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| Q1 | 10433 | 8668 | 1765 | -26.000 à -15.000 | 0.319 | z = -18.250 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; nœud 20942 |
| Q3 | 10433 | 2605 | 7828 | -26.000 à -13.500 | 0.056 | z = -17.500 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 11134 |
| A | 10433 | 6771 | 3662 | -26.000 à -12.000 | 0.738 | z = -12.250 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 38889 |

### Butée : pression de réaction k·abs(DY) / A comparée à σ'p(z)

La force de butée d'un nœud est Σ (aire tributaire de chaque bande × σ'p de la couche de la bande à la cote du nœud), σ'p interpolée linéairement (`donnees_butee_combiwall_v1.md`) ; la pression initiale au repos n'est pas ajoutée (non modélisée, décision 5, item 3). Taux = force de réaction / force de butée.

| Cas | Nœuds comprimés | Taux maximal | Cote (m) | Porteur | Pression k·abs(DY)/A (kPa) | σ'p (kPa) | Nœuds au-delà de 100 % | Porteurs concernés |
|---|---:|---:|---:|---|---:|---:|---:|---|
| G | 8828 | 951.35 % | -12.000 | TUBE_04 | 448.09 | 47.10 | 2413 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| EAU_P | 8652 | 369.20 % | -12.000 | TUBE_06 | 173.89 | 47.10 | 1122 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| EAU_A | 8652 | 858.48 % | -12.000 | TUBE_06 | 404.35 | 47.10 | 2029 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| Q1 | 8668 | 335.55 % | -12.000 | TUBE_04 | 158.04 | 47.10 | 978 | PALP_01_02, PALP_02_03, PALP_03_04, PALP_04_05, PALP_05_06, PALP_06_07, PALP_07_08, PALP_08_09, TUBE_01, TUBE_02, TUBE_03, TUBE_04, TUBE_05, TUBE_06, TUBE_07, TUBE_08, TUBE_09 |
| Q3 | 2605 | 9.22 % | -12.000 | TUBE_07 | 4.34 | 47.10 | 0 | - |
| A | 6771 | 1.41 % | -19.750 | TUBE_05 | 5.49 | 387.98 | 0 | - |

## Profils du déplacement horizontal DY le long des tubes

`DEPL`, `DY`, repère global, en mm (< 0 vers le bassin). Chaque valeur est la **moyenne de DY sur l'anneau de nœuds** du tube à la cote donnée ; l'étendue (minimum à maximum sur l'anneau) figure entre parenthèses.

### TUBE_05

| Cote (m) | G | EAU_P | EAU_A | Q1 | Q3 | A |
|---:|---:|---:|---:|---:|---:|---:|
| 2.600 | -15.6652 (-15.6652 ; -15.6652) | -7.9221 (-7.9221 ; -7.9221) | -18.5828 (-18.5828 ; -18.5828) | -9.3084 (-9.3084 ; -9.3084) | -4.3020 (-4.3020 ; -4.3020) | 3.4187 (3.4187 ; 3.4187) |
| 2.500 | -15.8223 (-16.2327 ; -12.7263) | -7.9837 (-8.1964 ; -6.3908) | -18.7220 (-19.2215 ; -14.9843) | -9.3225 (-9.5756 ; -7.4327) | -4.2204 (-4.3477 ; -3.3031) | 3.4332 (2.6952 ; 3.6755) |
| 2.250 | -16.5149 (-16.8806 ; -15.7642) | -8.2919 (-8.4826 ; -7.9059) | -19.4315 (-19.8792 ; -18.5273) | -9.5379 (-9.7636 ; -9.0787) | -4.0991 (-4.2105 ; -3.8853) | 3.5340 (3.2553 ; 4.3847) |
| 2.000 | -17.1127 (-17.3346 ; -16.6039) | -8.5517 (-8.6685 ; -8.2879) | -20.0271 (-20.3008 ; -19.4120) | -9.6955 (-9.8352 ; -9.3804) | -3.9525 (-4.0109 ; -3.8128) | 3.6290 (3.1478 ; 5.2124) |
| 1.750 | -17.7095 (-17.8794 ; -17.3111) | -8.8120 (-8.9014 ; -8.6020) | -20.6232 (-20.8318 ; -20.1373) | -9.8544 (-9.9643 ; -9.6033) | -3.8119 (-3.8471 ; -3.7066) | 3.7211 (2.9896 ; 6.0649) |
| 1.500 | -18.2995 (-18.4341 ; -17.9983) | -9.0694 (-9.1410 ; -8.9052) | -21.2125 (-21.3780 ; -20.8377) | -10.0110 (-10.0987 ; -9.8160) | -3.6752 (-3.6970 ; -3.5982) | 3.7766 (2.8858 ; 6.7007) |
| 1.250 | -18.8769 (-18.9842 ; -18.6262) | -9.3207 (-9.3789 ; -9.1772) | -21.7878 (-21.9205 ; -21.4656) | -10.1620 (-10.2319 ; -9.9949) | -3.5413 (-3.5563 ; -3.4771) | 3.8172 (2.8580 ; 7.1839) |
| 1.000 | -19.4421 (-19.5317 ; -19.2350) | -9.5662 (-9.6164 ; -9.4389) | -22.3495 (-22.4613 ; -22.0696) | -10.3079 (-10.3655 ; -10.1646) | -3.4107 (-3.4243 ; -3.3561) | 3.8177 (2.9086 ; 7.3633) |
| 0.750 | -19.9928 (-20.0724 ; -19.8202) | -9.8044 (-9.8522 ; -9.6882) | -22.8945 (-22.9953 ; -22.6443) | -10.4477 (-10.4974 ; -10.3227) | -3.2833 (-3.2991 ; -3.2347) | 3.8045 (2.9874 ; 7.3561) |
| 0.500 | -20.5277 (-20.6026 ; -20.3855) | -10.0345 (-10.0813 ; -9.9272) | -23.4212 (-23.5176 ; -23.1945) | -10.5806 (-10.6257 ; -10.4713) | -3.1590 (-3.1774 ; -3.1146) | 3.8042 (2.9561 ; 7.3030) |
| 0.250 | -21.0452 (-21.1191 ; -20.9310) | -10.2554 (-10.3022 ; -10.1557) | -23.9274 (-24.0240 ; -23.7206) | -10.7062 (-10.7487 ; -10.6108) | -3.0377 (-3.0588 ; -2.9966) | 3.7962 (2.9115 ; 7.1403) |
| 0.000 | -21.5438 (-21.6194 ; -21.4417) | -10.4666 (-10.5139 ; -10.3743) | -24.4114 (-24.5111 ; -24.2231) | -10.8238 (-10.8651 ; -10.7415) | -2.9194 (-2.9433 ; -2.8809) | 3.7840 (2.8503 ; 6.9254) |
| -0.250 | -22.0221 (-22.1017 ; -21.8990) | -10.6672 (-10.7160 ; -10.5795) | -24.8714 (-24.9765 ; -24.6947) | -10.9328 (-10.9740 ; -10.8633) | -2.8041 (-2.8308 ; -2.7678) | 3.7675 (2.7557 ; 6.6860) |
| -0.500 | -22.4789 (-22.5642 ; -22.3323) | -10.8565 (-10.9084 ; -10.7578) | -25.3056 (-25.4180 ; -25.1012) | -11.0328 (-11.0747 ; -10.9675) | -2.6918 (-2.7211 ; -2.6574) | 3.7466 (2.6387 ; 6.4397) |
| -0.750 | -22.9129 (-23.0057 ; -22.7402) | -11.0340 (-11.0894 ; -10.9239) | -25.7125 (-25.8335 ; -25.4790) | -11.1233 (-11.1666 ; -11.0499) | -2.5824 (-2.6140 ; -2.5497) | 3.7217 (2.5286 ; 6.1973) |
| -1.000 | -23.3227 (-23.4304 ; -23.1210) | -11.1990 (-11.2583 ; -11.0770) | -26.0906 (-26.2217 ; -25.8263) | -11.2038 (-11.2494 ; -11.1214) | -2.4758 (-2.5094 ; -2.4446) | 3.6928 (2.4288 ; 5.9648) |
| -1.250 | -23.7074 (-23.8320 ; -23.4734) | -11.3509 (-11.4147 ; -11.2164) | -26.4387 (-26.5811 ; -26.1417) | -11.2740 (-11.3225 ; -11.1813) | -2.3720 (-2.4074 ; -2.3421) | 3.6600 (2.3411 ; 5.7453) |
| -1.500 | -24.0657 (-24.2094 ; -23.7959) | -11.4893 (-11.5580 ; -11.3414) | -26.7556 (-26.9105 ; -26.4238) | -11.3334 (-11.3856 ; -11.2291) | -2.2711 (-2.3077 ; -2.2423) | 3.6235 (2.2664 ; 5.5399) |
| -1.750 | -24.3967 (-24.5640 ; -24.0873) | -11.6136 (-11.6877 ; -11.4511) | -27.0401 (-27.2088 ; -26.6710) | -11.3818 (-11.4414 ; -11.2646) | -2.1729 (-2.2105 ; -2.1450) | 3.5835 (2.2045 ; 5.3484) |
| -2.000 | -24.6992 (-24.8972 ; -24.3461) | -11.7235 (-11.8036 ; -11.5451) | -27.2913 (-27.4755 ; -26.8820) | -11.4189 (-11.4866 ; -11.2871) | -2.0774 (-2.1156 ; -2.0503) | 3.5401 (2.1546 ; 5.1699) |
| -2.250 | -24.9726 (-25.2043 ; -24.5712) | -11.8185 (-11.9087 ; -11.6226) | -27.5082 (-27.7167 ; -27.0556) | -11.4444 (-11.5211 ; -11.2965) | -1.9845 (-2.0231 ; -1.9582) | 3.4934 (2.1156 ; 5.0029) |
| -2.500 | -25.2162 (-25.4899 ; -24.7614) | -11.8983 (-11.9999 ; -11.6831) | -27.6901 (-27.9251 ; -27.1904) | -11.4582 (-11.5460 ; -11.2923) | -1.8944 (-1.9329 ; -1.8687) | 3.4435 (2.0859 ; 4.8459) |
| -2.750 | -25.4290 (-25.7509 ; -24.9156) | -11.9626 (-12.0765 ; -11.7263) | -27.8363 (-28.1000 ; -27.2854) | -11.4600 (-11.5626 ; -11.2744) | -1.8068 (-1.8451 ; -1.7817) | 3.3907 (2.0640 ; 4.6972) |
| -3.000 | -25.6105 (-25.9893 ; -25.0328) | -12.0112 (-12.1389 ; -11.7516) | -27.9461 (-28.2411 ; -27.3395) | -11.4498 (-11.5686 ; -11.2423) | -1.7218 (-1.7597 ; -1.6972) | 3.3350 (2.0482 ; 4.5553) |
| -3.250 | -25.7600 (-26.2015 ; -25.1119) | -12.0439 (-12.1909 ; -11.7586) | -28.0191 (-28.3588 ; -27.3519) | -11.4273 (-11.5672 ; -11.1960) | -1.6393 (-1.6766 ; -1.6153) | 3.2766 (2.0369 ; 4.4188) |
| -3.500 | -25.8770 (-26.3864 ; -25.1521) | -12.0604 (-12.2284 ; -11.7472) | -28.0549 (-28.4430 ; -27.3218) | -11.3926 (-11.5572 ; -11.1352) | -1.5593 (-1.5959 ; -1.5358) | 3.2156 (2.0287 ; 4.2863) |
| -3.750 | -25.9610 (-26.5437 ; -25.1525) | -12.0608 (-12.2544 ; -11.7169) | -28.0533 (-28.4992 ; -27.2485) | -11.3455 (-11.5381 ; -11.0597) | -1.4817 (-1.5175 ; -1.4588) | 3.1522 (2.0223 ; 4.1569) |
| -4.000 | -26.0117 (-26.6732 ; -25.1124) | -12.0449 (-12.2683 ; -11.6677) | -28.0141 (-28.5279 ; -27.1314) | -11.2861 (-11.5087 ; -10.9694) | -1.4066 (-1.4414 ; -1.3842) | 3.0866 (2.0165 ; 4.0296) |
| -4.250 | -26.0287 (-26.7750 ; -25.0311) | -12.0127 (-12.2712 ; -11.5992) | -27.9372 (-28.5320 ; -26.9702) | -11.2144 (-11.4690 ; -10.8643) | -1.3339 (-1.3677 ; -1.3121) | 3.0188 (2.0104 ; 3.9037) |
| -4.500 | -26.0119 (-26.8490 ; -24.9081) | -11.9642 (-12.2605 ; -11.5116) | -27.8227 (-28.5053 ; -26.7646) | -11.1303 (-11.4190 ; -10.7443) | -1.2635 (-1.2962 ; -1.2423) | 2.9490 (2.0031 ; 3.7786) |
| -4.750 | -25.9612 (-26.8954 ; -24.7429) | -11.8995 (-12.2358 ; -11.4046) | -27.6707 (-28.4466 ; -26.5143) | -11.0340 (-11.3590 ; -10.6094) | -1.1954 (-1.2271 ; -1.1748) | 2.8774 (1.9940 ; 3.6539) |
| -5.000 | -25.8764 (-26.9142 ; -24.5350) | -11.8188 (-12.1975 ; -11.2782) | -27.4816 (-28.3562 ; -26.2193) | -10.9257 (-11.2891 ; -10.4594) | -1.1297 (-1.1601 ; -1.1097) | 2.8041 (1.9827 ; 3.5292) |
| -5.250 | -25.7577 (-26.9057 ; -24.2841) | -11.7222 (-12.1456 ; -11.1326) | -27.2557 (-28.2345 ; -25.8798) | -10.8054 (-11.2095 ; -10.2946) | -1.0661 (-1.0955 ; -1.0468) | 2.7293 (1.9688 ; 3.4045) |
| -5.500 | -25.6052 (-26.8702 ; -23.9900) | -11.6099 (-12.0804 ; -10.9678) | -26.9934 (-28.0821 ; -25.4958) | -10.6733 (-11.1203 ; -10.1149) | -1.0048 (-1.0330 ; -0.9861) | 2.6531 (1.9521 ; 3.2797) |
| -5.750 | -25.4192 (-26.8079 ; -23.6526) | -11.4821 (-12.0022 ; -10.7839) | -26.6954 (-27.8998 ; -25.0677) | -10.5297 (-11.0219 ; -9.9203) | -0.9456 (-0.9727 ; -0.9276) | 2.5757 (1.9324 ; 3.1546) |
| -6.000 | -25.1998 (-26.7192 ; -23.2718) | -11.3392 (-11.9113 ; -10.5813) | -26.3623 (-27.6881 ; -24.5960) | -10.3748 (-10.9143 ; -9.7110) | -0.8886 (-0.9145 ; -0.8712) | 2.4971 (1.9098 ; 3.0294) |
| -6.250 | -24.9477 (-26.6048 ; -22.8478) | -11.1815 (-11.8082 ; -10.3601) | -25.9950 (-27.4481 ; -24.0813) | -10.2088 (-10.7978 ; -9.4872) | -0.8337 (-0.8585 ; -0.8170) | 2.4176 (1.8842 ; 2.9042) |
| -6.500 | -24.6632 (-26.4651 ; -22.3809) | -11.0094 (-11.6932 ; -10.1206) | -25.5943 (-27.1806 ; -23.5243) | -10.0321 (-10.6727 ; -9.2489) | -0.7808 (-0.8046 ; -0.7648) | 2.3373 (1.8558 ; 2.7791) |
| -6.750 | -24.3471 (-26.3007 ; -21.8713) | -10.8233 (-11.5669 ; -9.8633) | -25.1612 (-26.8867 ; -22.9260) | -9.8451 (-10.5393 ; -8.9964) | -0.7300 (-0.7527 ; -0.7147) | 2.2563 (1.8247 ; 2.6542) |
| -7.000 | -24.0001 (-26.1125 ; -21.3197) | -10.6238 (-11.4296 ; -9.5887) | -24.6968 (-26.5676 ; -22.2874) | -9.6480 (-10.3979 ; -8.7300) | -0.6812 (-0.7028 ; -0.6665) | 2.1749 (1.7911 ; 2.5297) |
| -7.250 | -23.6229 (-25.9014 ; -20.7268) | -10.4112 (-11.2821 ; -9.2972) | -24.2024 (-26.2245 ; -21.6097) | -9.4413 (-10.2488 ; -8.4500) | -0.6343 (-0.6550 ; -0.6203) | 2.0930 (1.7551 ; 2.4058) |
| -7.500 | -23.2164 (-25.6682 ; -20.0936) | -10.1863 (-11.1247 ; -8.9896) | -23.6793 (-25.8588 ; -20.8945) | -9.2255 (-10.0923 ; -8.1569) | -0.5894 (-0.6091 ; -0.5760) | 2.0110 (1.7171 ; 2.2827) |
| -7.750 | -22.7819 (-25.4141 ; -19.4213) | -9.9496 (-10.9583 ; -8.6665) | -23.1288 (-25.4721 ; -20.1435) | -9.0009 (-9.9291 ; -7.8510) | -0.5464 (-0.5651 ; -0.5336) | 1.9288 (1.6771 ; 2.1605) |
| -8.000 | -22.3202 (-25.1405 ; -18.7113) | -9.7017 (-10.7835 ; -8.3288) | -22.5525 (-25.0659 ; -19.3583) | -8.7682 (-9.7595 ; -7.5332) | -0.5052 (-0.5230 ; -0.4930) | 1.8468 (1.6355 ; 2.0394) |
| -8.250 | -21.8328 (-24.8485 ; -17.9654) | -9.4434 (-10.6010 ; -7.9773) | -21.9520 (-24.6419 ; -18.5414) | -8.5278 (-9.5843 ; -7.2041) | -0.4659 (-0.4827 ; -0.4542) | 1.7649 (1.5924 ; 1.9195) |
| -8.500 | -21.3209 (-24.5399 ; -17.1858) | -9.1754 (-10.4117 ; -7.6132) | -21.3290 (-24.2020 ; -17.6949) | -8.2803 (-9.4041 ; -6.8647) | -0.4283 (-0.4443 ; -0.4172) | 1.6834 (1.5481 ; 1.8012) |
| -8.750 | -20.7860 (-24.2162 ; -16.3750) | -8.8984 (-10.2163 ; -7.2375) | -20.6852 (-23.7481 ; -16.8217) | -8.0262 (-9.2195 ; -6.5161) | -0.3925 (-0.4076 ; -0.3818) | 1.6024 (1.5028 ; 1.6844) |
| -9.000 | -20.2297 (-23.8795 ; -15.5357) | -8.6134 (-10.0157 ; -6.8516) | -20.0227 (-23.2820 ; -15.9247) | -7.7665 (-9.0321 ; -6.1594) | -0.3585 (-0.3727 ; -0.3481) | 1.5220 (1.4567 ; 1.5694) |
| -9.250 | -19.6537 (-23.5315 ; -14.6714) | -8.3211 (-9.8107 ; -6.4570) | -19.3433 (-22.8059 ; -15.0074) | -7.5014 (-8.8422 ; -5.7960) | -0.3261 (-0.3395 ; -0.3161) | 1.4424 (1.4100 ; 1.4587) |
| -9.500 | -19.0596 (-23.1739 ; -13.7857) | -8.0224 (-9.6024 ; -6.0551) | -18.6493 (-22.3219 ; -14.0734) | -7.2314 (-8.6497 ; -5.4274) | -0.2953 (-0.3079 ; -0.2856) | 1.3637 (1.3456 ; 1.3716) |
| -9.750 | -18.4494 (-22.8087 ; -12.8831) | -7.7184 (-9.3914 ; -5.6480) | -17.9427 (-21.8318 ; -13.1270) | -6.9575 (-8.4564 ; -5.0551) | -0.2662 (-0.2780 ; -0.2566) | 1.2861 (1.2371 ; 1.3155) |
| -10.000 | -17.8250 (-22.4379 ; -11.9683) | -7.4099 (-9.1786 ; -5.2374) | -17.2258 (-21.3376 ; -12.1728) | -6.6803 (-8.2627 ; -4.6812) | -0.2387 (-0.2496 ; -0.2291) | 1.2096 (1.1312 ; 1.2681) |
| -10.250 | -17.1887 (-22.0628 ; -11.0471) | -7.0980 (-8.9648 ; -4.8258) | -16.5011 (-20.8409 ; -11.2161) | -6.4008 (-8.0695 ; -4.3075) | -0.2127 (-0.2228 ; -0.2031) | 1.1346 (1.0280 ; 1.2208) |
| -10.500 | -16.5426 (-21.6848 ; -10.1258) | -6.7838 (-8.7504 ; -4.4157) | -15.7709 (-20.3430 ; -10.2628) | -6.1197 (-7.8771 ; -3.9365) | -0.1883 (-0.1975 ; -0.1784) | 1.0610 (0.9278 ; 1.1736) |
| -10.750 | -15.8890 (-21.3045 ; -9.2119) | -6.4683 (-8.5360 ; -4.0100) | -15.0378 (-19.8450 ; -9.3198) | -5.8379 (-7.6858 ; -3.5707) | -0.1653 (-0.1737 ; -0.1552) | 0.9890 (0.8310 ; 1.1268) |
| -11.000 | -15.2306 (-20.9221 ; -8.3141) | -6.1528 (-8.3216 ; -3.6122) | -14.3045 (-19.3470 ; -8.3953) | -5.5565 (-7.4956 ; -3.2131) | -0.1437 (-0.1514 ; -0.1332) | 0.9188 (0.7380 ; 1.0802) |
| -11.250 | -14.5697 (-20.5368 ; -7.4425) | -5.8382 (-8.1071 ; -3.2262) | -13.5734 (-18.8488 ; -7.4981) | -5.2762 (-7.3062 ; -2.8671) | -0.1236 (-0.1309 ; -0.1124) | 0.8505 (0.6491 ; 1.0341) |
| -11.500 | -13.9090 (-20.1473 ; -6.6074) | -5.5258 (-7.8921 ; -2.8561) | -12.8475 (-18.3495 ; -6.6380) | -4.9980 (-7.1172 ; -2.5365) | -0.1048 (-0.1121 ; -0.0929) | 0.7842 (0.5648 ; 0.9882) |
| -11.750 | -13.2525 (-19.7519 ; -5.8236) | -5.2172 (-7.6762 ; -2.5080) | -12.1305 (-17.8480 ; -5.8290) | -4.7235 (-6.9278 ; -2.2263) | -0.0874 (-0.0950 ; -0.0745) | 0.7202 (0.4862 ; 0.9426) |
| -12.000 | -12.5957 (-19.3487 ; -5.0694) | -4.9108 (-7.4586 ; -2.1728) | -11.4183 (-17.3427 ; -5.0499) | -4.4510 (-6.7374 ; -1.9284) | -0.0712 (-0.0791 ; -0.0573) | 0.6581 (0.4113 ; 0.8972) |
| -12.250 | -11.9541 (-18.9358 ; -4.3732) | -4.6128 (-7.2389 ; -1.8640) | -10.7261 (-16.8324 ; -4.3323) | -4.1862 (-6.5454 ; -1.6544) | -0.0564 (-0.0648 ; -0.0411) | 0.5988 (0.3435 ; 0.8521) |
| -12.500 | -11.3393 (-18.5113 ; -3.7450) | -4.3280 (-7.0164 ; -1.5872) | -10.0642 (-16.3158 ; -3.6888) | -3.9331 (-6.3510 ; -1.4087) | -0.0429 (-0.0521 ; -0.0260) | 0.5430 (0.2841 ; 0.8071) |
| -12.750 | -10.7457 (-18.0738 ; -3.1599) | -4.0541 (-6.7908 ; -1.3316) | -9.4278 (-15.7917 ; -3.0949) | -3.6898 (-6.1538 ; -1.1818) | -0.0307 (-0.0408 ; -0.0120) | 0.4902 (0.2308 ; 0.7622) |
| -13.000 | -10.1757 (-17.6217 ; -2.6241) | -3.7921 (-6.5616 ; -1.0996) | -8.8188 (-15.2593 ; -2.5558) | -3.4570 (-5.9532 ; -0.9756) | -0.0196 (-0.0308 ; 0.0011) | 0.4406 (0.1839 ; 0.7173) |
| -13.250 | -9.6300 (-17.1545 ; -2.1381) | -3.5421 (-6.3286 ; -0.8912) | -8.2379 (-14.7183 ; -2.0713) | -3.2350 (-5.7491 ; -0.7903) | -0.0096 (-0.0225 ; 0.0133) | 0.3940 (0.1430 ; 0.6726) |
| -13.500 | -9.1088 (-16.6722 ; -1.7015) | -3.3043 (-6.0921 ; -0.7057) | -7.6854 (-14.1688 ; -1.6401) | -3.0238 (-5.5415 ; -0.6251) | -0.0007 (-0.0153 ; 0.0245) | 0.3503 (0.1076 ; 0.6280) |
| -13.750 | -8.6124 (-16.1756 ; -1.3123) | -3.0788 (-5.8524 ; -0.5419) | -7.1614 (-13.6121 ; -1.2595) | -2.8234 (-5.3307 ; -0.4793) | 0.0072 (-0.0097 ; 0.0347) | 0.3096 (0.0773 ; 0.5836) |
| -14.000 | -8.1407 (-15.6664 ; -0.9678) | -2.8655 (-5.6102 ; -0.3986) | -6.6658 (-13.0495 ; -0.9263) | -2.6338 (-5.1174 ; -0.3514) | 0.0141 (-0.0053 ; 0.0440) | 0.2717 (0.0515 ; 0.5395) |
| -14.250 | -7.6933 (-15.1470 ; -0.6648) | -2.6643 (-5.3665 ; -0.2739) | -6.1983 (-12.4832 ; -0.6365) | -2.4548 (-4.9022 ; -0.2401) | 0.0202 (-0.0019 ; 0.0525) | 0.2366 (0.0298 ; 0.4957) |
| -14.500 | -7.2698 (-14.6199 ; -0.3999) | -2.4749 (-5.1221 ; -0.1664) | -5.7582 (-11.9155 ; -0.3866) | -2.2862 (-4.6861 ; -0.1439) | 0.0255 (0.0009 ; 0.0600) | 0.2041 (0.0118 ; 0.4525) |
| -14.750 | -6.8696 (-14.0881 ; -0.1701) | -2.2971 (-4.8782 ; -0.0744) | -5.3450 (-11.3490 ; -0.1728) | -2.1277 (-4.4700 ; -0.0615) | 0.0300 (0.0030 ; 0.0667) | 0.1740 (-0.0031 ; 0.4100) |
| -15.000 | -6.4919 (-13.5549 ; 0.0275) | -2.1305 (-4.6359 ; 0.0034) | -4.9579 (-10.7860 ; 0.0082) | -1.9789 (-4.2549 ; 0.0083) | 0.0338 (0.0046 ; 0.0725) | 0.1464 (-0.0150 ; 0.3682) |
| -15.250 | -6.1359 (-13.0233 ; 0.1954) | -1.9748 (-4.3962 ; 0.0684) | -4.5960 (-10.2292 ; 0.1592) | -1.8397 (-4.0418 ; 0.0667) | 0.0370 (0.0059 ; 0.0775) | 0.1211 (-0.0245 ; 0.3273) |
| -15.500 | -5.8006 (-12.4965 ; 0.3355) | -1.8295 (-4.1602 ; 0.1216) | -4.2583 (-9.6809 ; 0.2830) | -1.7095 (-3.8317 ; 0.1146) | 0.0395 (0.0068 ; 0.0817) | 0.0980 (-0.0317 ; 0.2874) |
| -15.750 | -5.4851 (-11.9777 ; 0.4495) | -1.6942 (-3.9287 ; 0.1641) | -3.9440 (-9.1431 ; 0.3817) | -1.5880 (-3.6253 ; 0.1529) | 0.0415 (0.0075 ; 0.0851) | 0.0768 (-0.0369 ; 0.2486) |
| -16.000 | -5.1885 (-11.4696 ; 0.5386) | -1.5684 (-3.7026 ; 0.1966) | -3.6518 (-8.6180 ; 0.4572) | -1.4748 (-3.4236 ; 0.1822) | 0.0431 (0.0080 ; 0.0879) | 0.0577 (-0.0403 ; 0.2110) |
| -16.250 | -4.9098 (-10.9750 ; 0.6037) | -1.4518 (-3.4827 ; 0.2197) | -3.3808 (-8.1071 ; 0.5111) | -1.3695 (-3.2271 ; 0.2031) | 0.0441 (0.0082 ; 0.0901) | 0.0403 (-0.0422 ; 0.1747) |
| -16.500 | -4.6480 (-10.4963 ; 0.6454) | -1.3438 (-3.2696 ; 0.2342) | -3.1299 (-7.6120 ; 0.5448) | -1.2716 (-3.0366 ; 0.2160) | 0.0448 (0.0082 ; 0.0918) | 0.0246 (-0.0426 ; 0.1398) |
| -16.750 | -4.4021 (-10.0355 ; 0.6644) | -1.2440 (-3.0640 ; 0.2406) | -2.8980 (-7.1344 ; 0.5597) | -1.1808 (-2.8527 ; 0.2216) | 0.0451 (0.0080 ; 0.0930) | 0.0105 (-0.0424 ; 0.1063) |
| -17.000 | -4.1712 (-9.5943 ; 0.6618) | -1.1520 (-2.8665 ; 0.2397) | -2.6841 (-6.6756 ; 0.5576) | -1.0967 (-2.6759 ; 0.2203) | 0.0451 (0.0076 ; 0.0938) | -0.0021 (-0.0425 ; 0.0745) |
| -17.250 | -3.9546 (-9.1740 ; 0.6390) | -1.0672 (-2.6778 ; 0.2323) | -2.4871 (-6.2373 ; 0.5404) | -1.0188 (-2.5068 ; 0.2131) | 0.0448 (0.0071 ; 0.0943) | -0.0134 (-0.0431 ; 0.0445) |
| -17.500 | -3.7513 (-8.7750 ; 0.5980) | -0.9894 (-2.4985 ; 0.2195) | -2.3061 (-5.8207 ; 0.5106) | -0.9469 (-2.3460 ; 0.2007) | 0.0442 (0.0065 ; 0.0942) | -0.0233 (-0.0440 ; 0.0164) |
| -17.750 | -3.5609 (-8.3981 ; 0.5418) | -0.9179 (-2.3289 ; 0.2024) | -2.1400 (-5.4266 ; 0.4708) | -0.8805 (-2.1936 ; 0.1843) | 0.0434 (0.0061 ; 0.0937) | -0.0322 (-0.0456 ; -0.0098) |
| -18.000 | -3.3800 (-8.0361 ; 0.4718) | -0.8521 (-2.1690 ; 0.1811) | -1.9873 (-5.0552 ; 0.4213) | -0.8189 (-2.0494 ; 0.1639) | 0.0425 (0.0057 ; 0.0927) | -0.0399 (-0.0480 ; -0.0288) |
| -18.250 | -3.2122 (-7.6937 ; 0.4024) | -0.7925 (-2.0189 ; 0.1598) | -1.8486 (-4.7064 ; 0.3717) | -0.7626 (-1.9135 ; 0.1437) | 0.0413 (0.0055 ; 0.0912) | -0.0466 (-0.0562 ; -0.0256) |
| -18.500 | -3.0592 (-7.3754 ; 0.3443) | -0.7382 (-1.8783 ; 0.1416) | -1.7223 (-4.3799 ; 0.3294) | -0.7112 (-1.7862 ; 0.1265) | 0.0401 (0.0053 ; 0.0893) | -0.0525 (-0.0767 ; -0.0227) |
| -18.750 | -2.9183 (-7.0730 ; 0.2960) | -0.6888 (-1.7470 ; 0.1258) | -1.6076 (-4.0748 ; 0.2926) | -0.6642 (-1.6667 ; 0.1116) | 0.0387 (0.0051 ; 0.0869) | -0.0575 (-0.0953 ; -0.0199) |
| -19.000 | -2.7891 (-6.7856 ; 0.2572) | -0.6441 (-1.6242 ; 0.1122) | -1.5038 (-3.7897 ; 0.2610) | -0.6214 (-1.5544 ; 0.0990) | 0.0373 (0.0049 ; 0.0843) | -0.0619 (-0.1124 ; -0.0171) |
| -19.250 | -2.6711 (-6.5113 ; 0.2261) | -0.6038 (-1.5094 ; 0.1002) | -1.4100 (-3.5229 ; 0.2331) | -0.5824 (-1.4488 ; 0.0880) | 0.0358 (0.0047 ; 0.0816) | -0.0656 (-0.1279 ; -0.0145) |
| -19.500 | -2.5638 (-6.2489 ; 0.2015) | -0.5674 (-1.4021 ; 0.0895) | -1.3256 (-3.2737 ; 0.2082) | -0.5472 (-1.3494 ; 0.0784) | 0.0343 (0.0043 ; 0.0789) | -0.0686 (-0.1419 ; -0.0120) |
| -19.750 | -2.4666 (-5.9985 ; 0.1820) | -0.5348 (-1.3022 ; 0.0799) | -1.2498 (-3.0416 ; 0.1858) | -0.5152 (-1.2562 ; 0.0698) | 0.0328 (0.0039 ; 0.0762) | -0.0712 (-0.1544 ; -0.0097) |
| -20.000 | -2.3788 (-5.7602 ; 0.1667) | -0.5057 (-1.2097 ; 0.0712) | -1.1820 (-2.8267 ; 0.1656) | -0.4865 (-1.1693 ; 0.0623) | 0.0313 (0.0033 ; 0.0736) | -0.0732 (-0.1655 ; -0.0075) |
| -20.250 | -2.2999 (-5.5347 ; 0.1547) | -0.4797 (-1.1246 ; 0.0634) | -1.1217 (-2.6291 ; 0.1476) | -0.4607 (-1.0887 ; 0.0556) | 0.0297 (0.0028 ; 0.0710) | -0.0748 (-0.1751 ; -0.0056) |
| -20.500 | -2.2293 (-5.3228 ; 0.1453) | -0.4567 (-1.0470 ; 0.0566) | -1.0682 (-2.4486 ; 0.1317) | -0.4375 (-1.0144 ; 0.0497) | 0.0282 (0.0022 ; 0.0684) | -0.0760 (-0.1833 ; -0.0039) |
| -20.750 | -2.1666 (-5.1248 ; 0.1378) | -0.4363 (-0.9766 ; 0.0506) | -1.0209 (-2.2851 ; 0.1178) | -0.4169 (-0.9465 ; 0.0447) | 0.0267 (0.0017 ; 0.0657) | -0.0769 (-0.1900 ; -0.0025) |
| -21.000 | -2.1110 (-4.9413 ; 0.1319) | -0.4185 (-0.9133 ; 0.0454) | -0.9793 (-2.1381 ; 0.1057) | -0.3985 (-0.8848 ; 0.0403) | 0.0252 (0.0012 ; 0.0631) | -0.0774 (-0.1955 ; -0.0012) |
| -21.250 | -2.0621 (-4.7723 ; 0.1272) | -0.4028 (-0.8569 ; 0.0408) | -0.9430 (-2.0070 ; 0.0952) | -0.3822 (-0.8292 ; 0.0365) | 0.0238 (0.0008 ; 0.0604) | -0.0777 (-0.1998 ; -0.0002) |
| -21.500 | -2.0194 (-4.6178 ; 0.1233) | -0.3892 (-0.8070 ; 0.0370) | -0.9113 (-1.8911 ; 0.0862) | -0.3679 (-0.7794 ; 0.0332) | 0.0224 (0.0004 ; 0.0577) | -0.0778 (-0.2030 ; 0.0006) |
| -21.750 | -1.9822 (-4.4774 ; 0.1201) | -0.3774 (-0.7632 ; 0.0337) | -0.8840 (-1.7893 ; 0.0786) | -0.3553 (-0.7352 ; 0.0305) | 0.0210 (0.0001 ; 0.0550) | -0.0777 (-0.2052 ; 0.0013) |
| -22.000 | -1.9502 (-4.3508 ; 0.1173) | -0.3673 (-0.7251 ; 0.0309) | -0.8605 (-1.7008 ; 0.0721) | -0.3443 (-0.6961 ; 0.0281) | 0.0197 (-0.0001 ; 0.0523) | -0.0774 (-0.2066 ; 0.0018) |
| -22.250 | -1.9229 (-4.2374 ; 0.1151) | -0.3587 (-0.6923 ; 0.0285) | -0.8404 (-1.6245 ; 0.0667) | -0.3347 (-0.6619 ; 0.0261) | 0.0185 (-0.0003 ; 0.0496) | -0.0770 (-0.2072 ; 0.0022) |
| -22.500 | -1.8997 (-4.1362 ; 0.1131) | -0.3514 (-0.6642 ; 0.0266) | -0.8234 (-1.5593 ; 0.0621) | -0.3264 (-0.6322 ; 0.0244) | 0.0173 (-0.0004 ; 0.0470) | -0.0764 (-0.2072 ; 0.0026) |
| -22.750 | -1.8803 (-4.0467 ; 0.1116) | -0.3452 (-0.6405 ; 0.0249) | -0.8091 (-1.5040 ; 0.0583) | -0.3193 (-0.6065 ; 0.0229) | 0.0162 (-0.0005 ; 0.0445) | -0.0758 (-0.2068 ; 0.0028) |
| -23.000 | -1.8642 (-3.9678 ; 0.1103) | -0.3401 (-0.6205 ; 0.0236) | -0.7972 (-1.4577 ; 0.0551) | -0.3132 (-0.5846 ; 0.0217) | 0.0152 (-0.0006 ; 0.0421) | -0.0752 (-0.2059 ; 0.0029) |
| -23.250 | -1.8510 (-3.8987 ; 0.1093) | -0.3359 (-0.6040 ; 0.0225) | -0.7873 (-1.4193 ; 0.0526) | -0.3080 (-0.5659 ; 0.0207) | 0.0142 (-0.0006 ; 0.0398) | -0.0745 (-0.2047 ; 0.0030) |
| -23.500 | -1.8403 (-3.8386 ; 0.1087) | -0.3324 (-0.5904 ; 0.0216) | -0.7793 (-1.3877 ; 0.0505) | -0.3036 (-0.5502 ; 0.0199) | 0.0134 (-0.0007 ; 0.0376) | -0.0738 (-0.2033 ; 0.0031) |
| -23.750 | -1.8319 (-3.7867 ; 0.1083) | -0.3296 (-0.5794 ; 0.0209) | -0.7727 (-1.3621 ; 0.0488) | -0.2999 (-0.5370 ; 0.0192) | 0.0126 (-0.0007 ; 0.0356) | -0.0731 (-0.2018 ; 0.0031) |
| -24.000 | -1.8253 (-3.7420 ; 0.1083) | -0.3273 (-0.5705 ; 0.0203) | -0.7675 (-1.3415 ; 0.0475) | -0.2969 (-0.5261 ; 0.0187) | 0.0118 (-0.0007 ; 0.0338) | -0.0725 (-0.2003 ; 0.0032) |
| -24.250 | -1.8203 (-3.7041 ; 0.1084) | -0.3256 (-0.5635 ; 0.0198) | -0.7634 (-1.3252 ; 0.0464) | -0.2944 (-0.5172 ; 0.0182) | 0.0112 (-0.0007 ; 0.0321) | -0.0718 (-0.1988 ; 0.0031) |
| -24.500 | -1.8165 (-3.6722 ; 0.1088) | -0.3242 (-0.5580 ; 0.0195) | -0.7602 (-1.3125 ; 0.0456) | -0.2924 (-0.5100 ; 0.0179) | 0.0106 (-0.0007 ; 0.0307) | -0.0713 (-0.1973 ; 0.0031) |
| -24.750 | -1.8138 (-3.6460 ; 0.1091) | -0.3231 (-0.5538 ; 0.0192) | -0.7578 (-1.3027 ; 0.0450) | -0.2908 (-0.5043 ; 0.0176) | 0.0101 (-0.0007 ; 0.0294) | -0.0708 (-0.1960 ; 0.0031) |
| -25.000 | -1.8120 (-3.6250 ; 0.1095) | -0.3224 (-0.5507 ; 0.0190) | -0.7560 (-1.2954 ; 0.0445) | -0.2895 (-0.4999 ; 0.0173) | 0.0098 (-0.0007 ; 0.0284) | -0.0704 (-0.1949 ; 0.0030) |
| -25.250 | -1.8107 (-3.6088 ; 0.1096) | -0.3218 (-0.5484 ; 0.0188) | -0.7547 (-1.2901 ; 0.0440) | -0.2886 (-0.4966 ; 0.0171) | 0.0094 (-0.0006 ; 0.0276) | -0.0700 (-0.1940 ; 0.0030) |
| -25.500 | -1.8100 (-3.5979 ; 0.1097) | -0.3214 (-0.5469 ; 0.0187) | -0.7538 (-1.2865 ; 0.0438) | -0.2879 (-0.4943 ; 0.0170) | 0.0092 (-0.0006 ; 0.0270) | -0.0698 (-0.1934 ; 0.0030) |
| -25.750 | -1.8096 (-3.5900 ; 0.1085) | -0.3212 (-0.5460 ; 0.0183) | -0.7533 (-1.2844 ; 0.0429) | -0.2876 (-0.4930 ; 0.0166) | 0.0091 (-0.0006 ; 0.0266) | -0.0697 (-0.1928 ; 0.0029) |
| -26.000 | -1.8096 (-3.5901 ; 0.1084) | -0.3212 (-0.5456 ; 0.0183) | -0.7532 (-1.2836 ; 0.0429) | -0.2874 (-0.4925 ; 0.0166) | 0.0091 (-0.0006 ; 0.0265) | -0.0696 (-0.1930 ; 0.0029) |

### TUBE_01

| Cote (m) | G | EAU_P | EAU_A | Q1 | Q3 | A |
|---:|---:|---:|---:|---:|---:|---:|
| 2.600 | -15.5681 (-15.5681 ; -15.5681) | -7.8720 (-7.8720 ; -7.8720) | -18.4653 (-18.4653 ; -18.4653) | -9.2489 (-9.2489 ; -9.2489) | -4.0091 (-4.0091 ; -4.0091) | 3.0202 (3.0202 ; 3.0202) |
| 2.500 | -15.5532 (-16.3461 ; -10.6040) | -7.8450 (-8.2546 ; -5.2977) | -18.3966 (-19.3581 ; -12.4190) | -9.1579 (-9.6447 ; -6.1353) | -3.8898 (-4.1095 ; -2.5401) | 2.9527 (1.9494 ; 3.1132) |
| 2.250 | -16.3819 (-17.0078 ; -15.1921) | -8.2232 (-8.5481 ; -7.6105) | -19.2703 (-20.0329 ; -17.8342) | -9.4563 (-9.8414 ; -8.7281) | -3.8222 (-3.9942 ; -3.5036) | 2.9589 (2.7184 ; 3.0839) |
| 2.000 | -16.9798 (-17.3458 ; -16.1825) | -8.4829 (-8.6742 ; -8.0702) | -19.8659 (-20.3143 ; -18.9010) | -9.6138 (-9.8420 ; -9.1220) | -3.6941 (-3.7876 ; -3.4852) | 2.9187 (2.7599 ; 2.9873) |
| 1.750 | -17.5760 (-17.8432 ; -16.9597) | -8.7427 (-8.8827 ; -8.4203) | -20.4611 (-20.7878 ; -19.7109) | -9.7721 (-9.9420 ; -9.3877) | -3.5707 (-3.6324 ; -3.4134) | 2.8784 (2.7577 ; 2.9249) |
| 1.500 | -18.1668 (-18.3686 ; -17.7074) | -9.0003 (-9.1071 ; -8.7546) | -21.0510 (-21.2985 ; -20.4844) | -9.9290 (-10.0585 ; -9.6373) | -3.4509 (-3.4933 ; -3.3372) | 2.8377 (2.7497 ; 2.8700) |
| 1.250 | -18.7425 (-18.8951 ; -18.3627) | -9.2506 (-9.3328 ; -9.0408) | -21.6239 (-21.8123 ; -21.1455) | -10.0789 (-10.1772 ; -9.8330) | -3.3325 (-3.3646 ; -3.2403) | 2.7952 (2.7234 ; 2.8206) |
| 1.000 | -19.3064 (-19.4334 ; -18.9933) | -9.4951 (-9.5674 ; -9.3137) | -22.1836 (-22.3425 ; -21.7757) | -10.2240 (-10.3053 ; -10.0160) | -3.2169 (-3.2418 ; -3.1419) | 2.7518 (2.6931 ; 2.7718) |
| 0.750 | -19.8556 (-19.9643 ; -19.5933) | -9.7323 (-9.7977 ; -9.5706) | -22.7264 (-22.8667 ; -22.3683) | -10.3628 (-10.4320 ; -10.1831) | -3.1037 (-3.1228 ; -3.0411) | 2.7074 (2.6582 ; 2.7237) |
| 0.500 | -20.3891 (-20.4841 ; -20.1701) | -9.9614 (-10.0223 ; -9.8155) | -23.2509 (-23.3788 ; -22.9324) | -10.4949 (-10.5548 ; -10.3388) | -2.9930 (-3.0081 ; -2.9404) | 2.6621 (2.6207 ; 2.6755) |
| 0.250 | -20.9052 (-20.9904 ; -20.7249) | -10.1814 (-10.2395 ; -10.0488) | -23.7551 (-23.8753 ; -23.4698) | -10.6197 (-10.6725 ; -10.4840) | -2.8848 (-2.8962 ; -2.8405) | 2.6160 (2.5810 ; 2.6267) |
| 0.000 | -21.4027 (-21.4834 ; -21.2583) | -10.3918 (-10.4482 ; -10.2715) | -24.2373 (-24.3532 ; -23.9818) | -10.7366 (-10.7864 ; -10.6194) | -2.7791 (-2.7897 ; -2.7420) | 2.5691 (2.5398 ; 2.5774) |
| -0.250 | -21.8801 (-21.9620 ; -21.7706) | -10.5917 (-10.6472 ; -10.4838) | -24.6957 (-24.8101 ; -24.4688) | -10.8451 (-10.8913 ; -10.7454) | -2.6758 (-2.6865 ; -2.6451) | 2.5214 (2.4971 ; 2.5279) |
| -0.500 | -22.3361 (-22.4217 ; -22.2133) | -10.7806 (-10.8359 ; -10.6855) | -25.1287 (-25.2446 ; -24.9304) | -10.9447 (-10.9870 ; -10.8619) | -2.5749 (-2.5859 ; -2.5500) | 2.4730 (2.4533 ; 2.4785) |
| -0.750 | -22.7695 (-22.8609 ; -22.6218) | -10.9578 (-11.0143 ; -10.8627) | -25.5346 (-25.6574 ; -25.3354) | -11.0349 (-11.0776 ; -10.9688) | -2.4764 (-2.4878 ; -2.4566) | 2.4240 (2.4084 ; 2.4285) |
| -1.000 | -23.1791 (-23.2783 ; -23.0033) | -11.1225 (-11.1825 ; -11.0162) | -25.9121 (-26.0436 ; -25.6835) | -11.1153 (-11.1593 ; -11.0492) | -2.3803 (-2.3919 ; -2.3649) | 2.3744 (2.3625 ; 2.3780) |
| -1.250 | -23.5636 (-23.6789 ; -23.3563) | -11.2744 (-11.3383 ; -11.1559) | -26.2599 (-26.4018 ; -25.9997) | -11.1854 (-11.2318 ; -11.1094) | -2.2865 (-2.2982 ; -2.2751) | 2.3242 (2.3157 ; 2.3269) |
| -1.500 | -23.9220 (-24.0568 ; -23.6794) | -11.4128 (-11.4813 ; -11.2811) | -26.5768 (-26.7305 ; -26.2823) | -11.2450 (-11.2946 ; -11.1576) | -2.1950 (-2.2065 ; -2.1870) | 2.2735 (2.2680 ; 2.2753) |
| -1.750 | -24.2532 (-24.4099 ; -23.9711) | -11.5374 (-11.6110 ; -11.3911) | -26.8616 (-27.0287 ; -26.5300) | -11.2937 (-11.3477 ; -11.1933) | -2.1058 (-2.1169 ; -2.1007) | 2.2224 (2.2197 ; 2.2235) |
| -2.000 | -24.5562 (-24.7428 ; -24.2302) | -11.6475 (-11.7270 ; -11.4852) | -27.1133 (-27.2953 ; -26.7414) | -11.3310 (-11.3935 ; -11.2160) | -2.0189 (-2.0293 ; -2.0150) | 2.1709 (2.1698 ; 2.1716) |
| -2.250 | -24.8302 (-25.0516 ; -24.4556) | -11.7429 (-11.8310 ; -11.5628) | -27.3311 (-27.5341 ; -26.9153) | -11.3570 (-11.4288 ; -11.2255) | -1.9342 (-1.9437 ; -1.9301) | 2.1190 (2.1165 ; 2.1212) |
| -2.500 | -25.0745 (-25.3372 ; -24.6460) | -11.8232 (-11.9228 ; -11.6235) | -27.5140 (-27.7443 ; -27.0504) | -11.3714 (-11.4535 ; -11.2215) | -1.8516 (-1.8602 ; -1.8474) | 2.0668 (2.0627 ; 2.0712) |
| -2.750 | -25.2883 (-25.5995 ; -24.8005) | -11.8882 (-12.0003 ; -11.6667) | -27.6615 (-27.9212 ; -27.1456) | -11.3739 (-11.4708 ; -11.2037) | -1.7713 (-1.7787 ; -1.7670) | 2.0143 (2.0084 ; 2.0210) |
| -3.000 | -25.4709 (-25.8399 ; -24.9180) | -11.9374 (-12.0633 ; -11.6922) | -27.7729 (-28.0646 ; -27.2001) | -11.3644 (-11.4778 ; -11.1719) | -1.6932 (-1.6992 ; -1.6889) | 1.9616 (1.9538 ; 1.9705) |
| -3.250 | -25.6216 (-26.0546 ; -24.9975) | -11.9709 (-12.1158 ; -11.6994) | -27.8476 (-28.1824 ; -27.2130) | -11.3429 (-11.4771 ; -11.1258) | -1.6171 (-1.6233 ; -1.6129) | 1.9087 (1.8988 ; 1.9198) |
| -3.500 | -25.7400 (-26.2420 ; -25.0382) | -11.9883 (-12.1544 ; -11.6882) | -27.8854 (-28.2694 ; -27.1835) | -11.3091 (-11.4679 ; -11.0652) | -1.5432 (-1.5507 ; -1.5390) | 1.8557 (1.8436 ; 1.8690) |
| -3.750 | -25.8255 (-26.4018 ; -25.0393) | -11.9896 (-12.1810 ; -11.6583) | -27.8860 (-28.3271 ; -27.1110) | -11.2631 (-11.4504 ; -10.9902) | -1.4714 (-1.4800 ; -1.4673) | 1.8026 (1.7882 ; 1.8181) |
| -4.000 | -25.8779 (-26.5339 ; -25.0000) | -11.9746 (-12.1959 ; -11.6095) | -27.8491 (-28.3581 ; -26.9949) | -11.2049 (-11.4226 ; -10.9004) | -1.4016 (-1.4114 ; -1.3977) | 1.7495 (1.7326 ; 1.7673) |
| -4.250 | -25.8967 (-26.6384 ; -24.9197) | -11.9435 (-12.2000 ; -11.5416) | -27.7746 (-28.3650 ; -26.8349) | -11.1344 (-11.3845 ; -10.7959) | -1.3338 (-1.3447 ; -1.3301) | 1.6963 (1.6769 ; 1.7166) |
| -4.500 | -25.8817 (-26.7153 ; -24.7979) | -11.8961 (-12.1908 ; -11.4545) | -27.6628 (-28.3417 ; -26.6307) | -11.0516 (-11.3363 ; -10.6766) | -1.2681 (-1.2801 ; -1.2645) | 1.6433 (1.6211 ; 1.6661) |
| -4.750 | -25.8329 (-26.7645 ; -24.6341) | -11.8327 (-12.1676 ; -11.3483) | -27.5136 (-28.2865 ; -26.3821) | -10.9568 (-11.2780 ; -10.5425) | -1.2043 (-1.2174 ; -1.1995) | 1.5903 (1.5653 ; 1.6157) |
| -5.000 | -25.7502 (-26.7863 ; -24.4277) | -11.7531 (-12.1308 ; -11.2227) | -27.3273 (-28.1997 ; -26.0891) | -10.8499 (-11.2100 ; -10.3936) | -1.1425 (-1.1566 ; -1.1361) | 1.5374 (1.5095 ; 1.5656) |
| -5.250 | -25.6336 (-26.7809 ; -24.1786) | -11.6578 (-12.0805 ; -11.0780) | -27.1043 (-28.0817 ; -25.7517) | -10.7311 (-11.1322 ; -10.2298) | -1.0826 (-1.0978 ; -1.0746) | 1.4848 (1.4538 ; 1.5158) |
| -5.500 | -25.4832 (-26.7484 ; -23.8865) | -11.5467 (-12.0169 ; -10.9142) | -26.8451 (-27.9332 ; -25.3701) | -10.6006 (-11.0450 ; -10.0513) | -1.0247 (-1.0409 ; -1.0150) | 1.4324 (1.3982 ; 1.4664) |
| -5.750 | -25.2993 (-26.6893 ; -23.5513) | -11.4203 (-11.9403 ; -10.7315) | -26.5501 (-27.7547 ; -24.9446) | -10.4585 (-10.9485 ; -9.8581) | -0.9686 (-0.9859 ; -0.9574) | 1.3803 (1.3428 ; 1.4173) |
| -6.000 | -25.0822 (-26.6040 ; -23.1728) | -11.2787 (-11.8512 ; -10.5300) | -26.2202 (-27.5470 ; -24.4758) | -10.3052 (-10.8429 ; -9.6502) | -0.9144 (-0.9328 ; -0.9016) | 1.3285 (1.2876 ; 1.3687) |
| -6.250 | -24.8322 (-26.4928 ; -22.7513) | -11.1223 (-11.7498 ; -10.3101) | -25.8560 (-27.3110 ; -23.9641) | -10.1409 (-10.7285 ; -9.4279) | -0.8620 (-0.8814 ; -0.8477) | 1.2770 (1.2326 ; 1.3206) |
| -6.500 | -24.5500 (-26.3565 ; -22.2870) | -10.9516 (-11.6366 ; -10.0720) | -25.4585 (-27.0476 ; -23.4103) | -9.9659 (-10.6055 ; -9.1912) | -0.8114 (-0.8319 ; -0.7956) | 1.2260 (1.1779 ; 1.2730) |
| -6.750 | -24.2360 (-26.1955 ; -21.7802) | -10.7669 (-11.5120 ; -9.8162) | -25.0286 (-26.7578 ; -22.8153) | -9.7805 (-10.4741 ; -8.9405) | -0.7625 (-0.7842 ; -0.7453) | 1.1754 (1.1235 ; 1.2260) |
| -7.000 | -23.8911 (-26.0108 ; -21.2315) | -10.5687 (-11.3765 ; -9.5431) | -24.5675 (-26.4428 ; -22.1803) | -9.5851 (-10.3348 ; -8.6759) | -0.7155 (-0.7382 ; -0.6968) | 1.1254 (1.0695 ; 1.1795) |
| -7.250 | -23.5160 (-25.8030 ; -20.6417) | -10.3575 (-11.2307 ; -9.2532) | -24.0763 (-26.1040 ; -21.5063) | -9.3800 (-10.1878 ; -8.3977) | -0.6701 (-0.6940 ; -0.6500) | 1.0759 (1.0159 ; 1.1338) |
| -7.500 | -23.1116 (-25.5733 ; -20.0116) | -10.1339 (-11.0752 ; -8.9472) | -23.5564 (-25.7425 ; -20.7950) | -9.1658 (-10.0335 ; -8.1065) | -0.6265 (-0.6514 ; -0.6050) | 1.0269 (0.9628 ; 1.0887) |
| -7.750 | -22.6790 (-25.3227 ; -19.3425) | -9.8985 (-10.9105 ; -8.6258) | -23.0091 (-25.3600 ; -20.0478) | -8.9429 (-9.8724 ; -7.8027) | -0.5845 (-0.6105 ; -0.5616) | 0.9786 (0.9102 ; 1.0443) |
| -8.000 | -22.2193 (-25.0524 ; -18.6359) | -9.6520 (-10.7375 ; -8.2898) | -22.4360 (-24.9580 ; -19.2668) | -8.7117 (-9.7049 ; -7.4869) | -0.5442 (-0.5712 ; -0.5200) | 0.9310 (0.8582 ; 1.0008) |
| -8.250 | -21.7338 (-24.7639 ; -17.8934) | -9.3951 (-10.5568 ; -7.9401) | -21.8387 (-24.5381 ; -18.4539) | -8.4728 (-9.5318 ; -7.1599) | -0.5056 (-0.5336 ; -0.4800) | 0.8842 (0.8068 ; 0.9580) |
| -8.500 | -21.2238 (-24.4587 ; -17.1173) | -9.1284 (-10.3692 ; -7.5777) | -21.2189 (-24.1023 ; -17.6117) | -8.2269 (-9.3537 ; -6.8227) | -0.4685 (-0.4975 ; -0.4416) | 0.8380 (0.7561 ; 0.9161) |
| -8.750 | -20.6908 (-24.1384 ; -16.3100) | -8.8529 (-10.1756 ; -7.2039) | -20.5784 (-23.6525 ; -16.7428) | -7.9743 (-9.1712 ; -6.4762) | -0.4330 (-0.4629 ; -0.4049) | 0.7927 (0.7062 ; 0.8751) |
| -9.000 | -20.1365 (-23.8050 ; -15.4743) | -8.5692 (-9.9767 ; -6.8199) | -19.9192 (-23.1905 ; -15.8502) | -7.7161 (-8.9858 ; -6.1217) | -0.3990 (-0.4298 ; -0.3698) | 0.7483 (0.6570 ; 0.8349) |
| -9.250 | -19.5624 (-23.4602 ; -14.6136) | -8.2783 (-9.7734 ; -6.4271) | -19.2432 (-22.7184 ; -14.9373) | -7.4526 (-8.7979 ; -5.7605) | -0.3666 (-0.3983 ; -0.3362) | 0.7048 (0.6088 ; 0.7958) |
| -9.500 | -18.9704 (-23.1058 ; -13.7315) | -7.9811 (-9.5667 ; -6.0271) | -18.5525 (-22.2382 ; -14.0077) | -7.1842 (-8.6074 ; -5.3941) | -0.3357 (-0.3681 ; -0.3042) | 0.6622 (0.5615 ; 0.7576) |
| -9.750 | -18.3624 (-22.7439 ; -12.8325) | -7.6786 (-9.3574 ; -5.6219) | -17.8495 (-21.7520 ; -13.0657) | -6.9119 (-8.4160 ; -5.0242) | -0.3062 (-0.3394 ; -0.2738) | 0.6206 (0.5153 ; 0.7204) |
| -10.000 | -17.7406 (-22.3761 ; -11.9214) | -7.3717 (-9.1462 ; -5.2132) | -17.1364 (-21.2616 ; -12.1159) | -6.6365 (-8.2243 ; -4.6524) | -0.2782 (-0.3120 ; -0.2449) | 0.5800 (0.4702 ; 0.6842) |
| -10.250 | -17.1070 (-22.0041 ; -11.0038) | -7.0615 (-8.9340 ; -4.8035) | -16.4156 (-20.7686 ; -11.1636) | -6.3588 (-8.0329 ; -4.2810) | -0.2517 (-0.2860 ; -0.2175) | 0.5405 (0.4264 ; 0.6491) |
| -10.500 | -16.4639 (-21.6290 ; -10.0861) | -6.7491 (-8.7212 ; -4.3952) | -15.6896 (-20.2744 ; -10.2147) | -6.0797 (-7.8423 ; -3.9122) | -0.2265 (-0.2613 ; -0.1917) | 0.5022 (0.3840 ; 0.6150) |
| -10.750 | -15.8139 (-21.2517 ; -9.1757) | -6.4355 (-8.5082 ; -3.9913) | -14.9610 (-19.7798 ; -9.2761) | -5.8001 (-7.6528 ; -3.5485) | -0.2027 (-0.2378 ; -0.1674) | 0.4650 (0.3430 ; 0.5819) |
| -11.000 | -15.1595 (-20.8720 ; -8.2815) | -6.1220 (-8.2953 ; -3.5953) | -14.2325 (-19.2853 ; -8.3557) | -5.5209 (-7.4644 ; -3.1931) | -0.1802 (-0.2154 ; -0.1446) | 0.4290 (0.3037 ; 0.5499) |
| -11.250 | -14.5032 (-20.4895 ; -7.4132) | -5.8097 (-8.0822 ; -3.2111) | -13.5068 (-18.7905 ; -7.4627) | -5.2431 (-7.2767 ; -2.8492) | -0.1591 (-0.1943 ; -0.1235) | 0.3942 (0.2663 ; 0.5188) |
| -11.500 | -13.8478 (-20.1027 ; -6.5814) | -5.4998 (-7.8687 ; -2.8427) | -12.7867 (-18.2945 ; -6.6066) | -4.9677 (-7.0893 ; -2.5206) | -0.1393 (-0.1742 ; -0.1039) | 0.3608 (0.2310 ; 0.4886) |
| -11.750 | -13.1974 (-19.7099 ; -5.8007) | -5.1940 (-7.6541 ; -2.4962) | -12.0762 (-17.7961 ; -5.8013) | -4.6961 (-6.9016 ; -2.2123) | -0.1207 (-0.1551 ; -0.0860) | 0.3287 (0.1981 ; 0.4593) |
| -12.000 | -12.5470 (-19.3093 ; -5.0495) | -4.8905 (-7.4378 ; -2.1626) | -11.3708 (-17.2940 ; -5.0259) | -4.4267 (-6.7128 ; -1.9163) | -0.1033 (-0.1370 ; -0.0694) | 0.2979 (0.1670 ; 0.4307) |
| -12.250 | -11.9123 (-18.8989 ; -4.3561) | -4.5955 (-7.2194 ; -1.8552) | -10.6855 (-16.7867 ; -4.3117) | -4.1650 (-6.5223 ; -1.6440) | -0.0872 (-0.1198 ; -0.0547) | 0.2686 (0.1387 ; 0.4029) |
| -12.500 | -11.3042 (-18.4769 ; -3.7304) | -4.3137 (-6.9982 ; -1.5796) | -10.0307 (-16.2731 ; -3.6712) | -3.9151 (-6.3294 ; -1.3998) | -0.0725 (-0.1035 ; -0.0421) | 0.2412 (0.1140 ; 0.3757) |
| -12.750 | -10.7170 (-18.0417 ; -3.1475) | -4.0427 (-6.7738 ; -1.3252) | -9.4008 (-15.7519 ; -3.0799) | -3.6747 (-6.1336 ; -1.1742) | -0.0589 (-0.0880 ; -0.0310) | 0.2154 (0.0917 ; 0.3492) |
| -13.000 | -10.1529 (-17.5920 ; -2.6136) | -3.7833 (-6.5458 ; -1.0943) | -8.7981 (-15.2224 ; -2.5432) | -3.4448 (-5.9345 ; -0.9693) | -0.0465 (-0.0733 ; -0.0215) | 0.1912 (0.0721 ; 0.3232) |
| -13.250 | -9.6125 (-17.1270 ; -2.1294) | -3.5358 (-6.3141 ; -0.8867) | -8.2230 (-14.6841 ; -2.0609) | -3.2254 (-5.7318 ; -0.7850) | -0.0352 (-0.0593 ; -0.0135) | 0.1686 (0.0550 ; 0.2977) |
| -13.500 | -9.0963 (-16.6468 ; -1.6943) | -3.3003 (-6.0787 ; -0.7020) | -7.6759 (-14.1373 ; -1.6315) | -3.0165 (-5.5256 ; -0.6208) | -0.0250 (-0.0460 ; -0.0068) | 0.1476 (0.0403 ; 0.2728) |
| -13.750 | -8.6043 (-16.1523 ; -1.3065) | -3.0769 (-5.8401 ; -0.5390) | -7.1568 (-13.5831 ; -1.2526) | -2.8184 (-5.3161 ; -0.4757) | -0.0157 (-0.0333 ; -0.0013) | 0.1280 (0.0276 ; 0.2484) |
| -14.000 | -8.1364 (-15.6452 ; -0.9632) | -2.8655 (-5.5990 ; -0.3962) | -6.6656 (-13.0231 ; -0.9207) | -2.6307 (-5.1040 ; -0.3486) | -0.0073 (-0.0213 ; 0.0031) | 0.1099 (0.0170 ; 0.2245) |
| -14.250 | -7.6924 (-15.1277 ; -0.6611) | -2.6659 (-5.3562 ; -0.2721) | -6.2019 (-12.4592 ; -0.6322) | -2.4534 (-4.8900 ; -0.2379) | 0.0001 (-0.0099 ; 0.0066) | 0.0932 (0.0081 ; 0.2011) |
| -14.500 | -7.2717 (-14.6025 ; -0.3971) | -2.4780 (-5.1128 ; -0.1650) | -5.7651 (-11.8938 ; -0.3833) | -2.2863 (-4.6751 ; -0.1423) | 0.0068 (0.0009 ; 0.0097) | 0.0778 (0.0008 ; 0.1784) |
| -14.750 | -6.8737 (-14.0725 ; -0.1681) | -2.3013 (-4.8699 ; -0.0734) | -5.3547 (-11.3294 ; -0.1704) | -2.1291 (-4.4601 ; -0.0603) | 0.0127 (0.0111 ; 0.0143) | 0.0637 (-0.0051 ; 0.1562) |
| -15.000 | -6.4978 (-13.5409 ; 0.0289) | -2.1357 (-4.6284 ; 0.0041) | -4.9698 (-10.7686 ; 0.0097) | -1.9814 (-4.2461 ; 0.0091) | 0.0179 (0.0125 ; 0.0208) | 0.0507 (-0.0097 ; 0.1347) |
| -15.250 | -6.1432 (-13.0109 ; 0.1962) | -1.9807 (-4.3896 ; 0.0688) | -4.6096 (-10.2137 ; 0.1601) | -1.8431 (-4.0340 ; 0.0671) | 0.0224 (0.0132 ; 0.0299) | 0.0389 (-0.0132 ; 0.1139) |
| -15.500 | -5.8091 (-12.4856 ; 0.3358) | -1.8359 (-4.1543 ; 0.1217) | -4.2733 (-9.6671 ; 0.2832) | -1.7136 (-3.8247 ; 0.1147) | 0.0264 (0.0134 ; 0.0384) | 0.0282 (-0.0158 ; 0.0938) |
| -15.750 | -5.4945 (-11.9681 ; 0.4493) | -1.7011 (-3.9236 ; 0.1640) | -3.9599 (-9.1311 ; 0.3814) | -1.5926 (-3.6193 ; 0.1527) | 0.0297 (0.0132 ; 0.0464) | 0.0184 (-0.0174 ; 0.0744) |
| -16.000 | -5.1986 (-11.4613 ; 0.5380) | -1.5756 (-3.6982 ; 0.1962) | -3.6684 (-8.6075 ; 0.4564) | -1.4798 (-3.4183 ; 0.1818) | 0.0326 (0.0127 ; 0.0539) | 0.0096 (-0.0183 ; 0.0559) |
| -16.250 | -4.9206 (-10.9678 ; 0.6028) | -1.4591 (-3.4789 ; 0.2192) | -3.3977 (-8.0981 ; 0.5099) | -1.3748 (-3.2226 ; 0.2025) | 0.0350 (0.0119 ; 0.0607) | 0.0017 (-0.0189 ; 0.0383) |
| -16.500 | -4.6595 (-10.4902 ; 0.6442) | -1.3512 (-3.2664 ; 0.2336) | -3.1470 (-7.6045 ; 0.5433) | -1.2772 (-3.0328 ; 0.2153) | 0.0369 (0.0110 ; 0.0669) | -0.0054 (-0.0197 ; 0.0216) |
| -16.750 | -4.4145 (-10.0305 ; 0.6631) | -1.2515 (-3.0614 ; 0.2399) | -2.9152 (-7.1281 ; 0.5581) | -1.1866 (-2.8495 ; 0.2208) | 0.0385 (0.0100 ; 0.0724) | -0.0117 (-0.0208 ; 0.0058) |
| -17.000 | -4.1847 (-9.5904 ; 0.6604) | -1.1594 (-2.8644 ; 0.2390) | -2.7012 (-6.6707 ; 0.5558) | -1.1026 (-2.6734 ; 0.2195) | 0.0397 (0.0090 ; 0.0773) | -0.0173 (-0.0225 ; -0.0089) |
| -17.250 | -3.9694 (-9.1711 ; 0.6376) | -1.0746 (-2.6763 ; 0.2316) | -2.5042 (-6.2336 ; 0.5387) | -1.0249 (-2.5050 ; 0.2122) | 0.0406 (0.0080 ; 0.0815) | -0.0222 (-0.0249 ; -0.0155) |
| -17.500 | -3.7676 (-8.7730 ; 0.5967) | -0.9967 (-2.4974 ; 0.2188) | -2.3231 (-5.8182 ; 0.5090) | -0.9531 (-2.3447 ; 0.1999) | 0.0412 (0.0071 ; 0.0851) | -0.0265 (-0.0351 ; -0.0142) |
| -17.750 | -3.5790 (-8.3969 ; 0.5405) | -0.9251 (-2.3283 ; 0.2017) | -2.1569 (-5.4251 ; 0.4692) | -0.8868 (-2.1929 ; 0.1834) | 0.0415 (0.0062 ; 0.0881) | -0.0302 (-0.0467 ; -0.0128) |
| -18.000 | -3.4002 (-8.0357 ; 0.4705) | -0.8594 (-2.1688 ; 0.1804) | -2.0042 (-5.0547 ; 0.4197) | -0.8254 (-2.0491 ; 0.1631) | 0.0416 (0.0053 ; 0.0906) | -0.0335 (-0.0573 ; -0.0113) |
| -18.250 | -3.2341 (-7.6939 ; 0.4011) | -0.7996 (-2.0190 ; 0.1592) | -1.8653 (-4.7067 ; 0.3701) | -0.7692 (-1.9136 ; 0.1429) | 0.0415 (0.0044 ; 0.0927) | -0.0362 (-0.0669 ; -0.0099) |
| -18.500 | -3.0824 (-7.3761 ; 0.3430) | -0.7451 (-1.8787 ; 0.1410) | -1.7385 (-4.3809 ; 0.3278) | -0.7178 (-1.7867 ; 0.1257) | 0.0412 (0.0035 ; 0.0943) | -0.0385 (-0.0757 ; -0.0085) |
| -18.750 | -2.9423 (-7.0741 ; 0.2947) | -0.6955 (-1.7476 ; 0.1252) | -1.6232 (-4.0763 ; 0.2910) | -0.6706 (-1.6675 ; 0.1108) | 0.0407 (0.0026 ; 0.0955) | -0.0404 (-0.0836 ; -0.0070) |
| -19.000 | -2.8135 (-6.7871 ; 0.2558) | -0.6504 (-1.6251 ; 0.1115) | -1.5184 (-3.7917 ; 0.2593) | -0.6276 (-1.5554 ; 0.0981) | 0.0401 (0.0017 ; 0.0963) | -0.0420 (-0.0906 ; -0.0057) |
| -19.250 | -2.6955 (-6.5131 ; 0.2248) | -0.6096 (-1.5105 ; 0.0996) | -1.4236 (-3.5254 ; 0.2315) | -0.5883 (-1.4500 ; 0.0872) | 0.0394 (0.0009 ; 0.0967) | -0.0432 (-0.0968 ; -0.0044) |
| -19.500 | -2.5878 (-6.2512 ; 0.2002) | -0.5727 (-1.4034 ; 0.0889) | -1.3380 (-3.2766 ; 0.2067) | -0.5527 (-1.3509 ; 0.0776) | 0.0386 (0.0002 ; 0.0965) | -0.0442 (-0.1021 ; -0.0033) |
| -19.750 | -2.4897 (-6.0011 ; 0.1808) | -0.5396 (-1.3037 ; 0.0792) | -1.2609 (-3.0450 ; 0.1843) | -0.5203 (-1.2580 ; 0.0691) | 0.0376 (-0.0003 ; 0.0959) | -0.0449 (-0.1066 ; -0.0023) |
| -20.000 | -2.4009 (-5.7632 ; 0.1656) | -0.5099 (-1.2114 ; 0.0706) | -1.1919 (-2.8307 ; 0.1643) | -0.4911 (-1.1713 ; 0.0616) | 0.0367 (-0.0007 ; 0.0947) | -0.0453 (-0.1102 ; -0.0015) |
| -20.250 | -2.3208 (-5.5382 ; 0.1537) | -0.4834 (-1.1266 ; 0.0629) | -1.1302 (-2.6335 ; 0.1465) | -0.4648 (-1.0909 ; 0.0550) | 0.0356 (-0.0010 ; 0.0932) | -0.0456 (-0.1130 ; -0.0008) |
| -20.500 | -2.2488 (-5.3266 ; 0.1444) | -0.4598 (-1.0491 ; 0.0562) | -1.0754 (-2.4536 ; 0.1307) | -0.4411 (-1.0169 ; 0.0492) | 0.0345 (-0.0012 ; 0.0912) | -0.0456 (-0.1150 ; -0.0002) |
| -20.750 | -2.1845 (-5.1291 ; 0.1372) | -0.4389 (-0.9789 ; 0.0502) | -1.0268 (-2.2906 ; 0.1170) | -0.4200 (-0.9493 ; 0.0443) | 0.0334 (-0.0013 ; 0.0890) | -0.0455 (-0.1164 ; 0.0002) |
| -21.000 | -2.1274 (-4.9459 ; 0.1314) | -0.4205 (-0.9159 ; 0.0451) | -0.9841 (-2.1440 ; 0.1050) | -0.4011 (-0.8878 ; 0.0399) | 0.0322 (-0.0014 ; 0.0865) | -0.0453 (-0.1172 ; 0.0006) |
| -21.250 | -2.0769 (-4.7772 ; 0.1267) | -0.4043 (-0.8596 ; 0.0406) | -0.9466 (-2.0133 ; 0.0947) | -0.3844 (-0.8324 ; 0.0362) | 0.0311 (-0.0014 ; 0.0839) | -0.0449 (-0.1174 ; 0.0009) |
| -21.500 | -2.0326 (-4.6230 ; 0.1230) | -0.3903 (-0.8098 ; 0.0368) | -0.9139 (-1.8977 ; 0.0859) | -0.3697 (-0.7828 ; 0.0330) | 0.0299 (-0.0014 ; 0.0811) | -0.0445 (-0.1172 ; 0.0011) |
| -21.750 | -1.9940 (-4.4829 ; 0.1198) | -0.3781 (-0.7662 ; 0.0336) | -0.8857 (-1.7963 ; 0.0783) | -0.3567 (-0.7387 ; 0.0303) | 0.0287 (-0.0014 ; 0.0782) | -0.0440 (-0.1166 ; 0.0013) |
| -22.000 | -1.9606 (-4.3566 ; 0.1172) | -0.3677 (-0.7282 ; 0.0308) | -0.8613 (-1.7080 ; 0.0719) | -0.3453 (-0.6998 ; 0.0280) | 0.0276 (-0.0013 ; 0.0753) | -0.0434 (-0.1157 ; 0.0014) |
| -22.250 | -1.9319 (-4.2432 ; 0.1150) | -0.3587 (-0.6955 ; 0.0285) | -0.8405 (-1.6319 ; 0.0666) | -0.3354 (-0.6657 ; 0.0260) | 0.0265 (-0.0013 ; 0.0724) | -0.0427 (-0.1145 ; 0.0015) |
| -22.500 | -1.9074 (-4.1423 ; 0.1131) | -0.3511 (-0.6675 ; 0.0266) | -0.8228 (-1.5669 ; 0.0620) | -0.3269 (-0.6361 ; 0.0244) | 0.0254 (-0.0012 ; 0.0696) | -0.0421 (-0.1131 ; 0.0016) |
| -22.750 | -1.8868 (-4.0528 ; 0.1116) | -0.3447 (-0.6438 ; 0.0249) | -0.8080 (-1.5118 ; 0.0583) | -0.3195 (-0.6105 ; 0.0229) | 0.0244 (-0.0012 ; 0.0668) | -0.0414 (-0.1116 ; 0.0016) |
| -23.000 | -1.8696 (-3.9740 ; 0.1103) | -0.3394 (-0.6239 ; 0.0236) | -0.7956 (-1.4656 ; 0.0552) | -0.3132 (-0.5885 ; 0.0218) | 0.0234 (-0.0011 ; 0.0641) | -0.0407 (-0.1100 ; 0.0016) |
| -23.250 | -1.8554 (-3.9050 ; 0.1094) | -0.3350 (-0.6074 ; 0.0225) | -0.7853 (-1.4272 ; 0.0526) | -0.3078 (-0.5699 ; 0.0208) | 0.0225 (-0.0010 ; 0.0616) | -0.0400 (-0.1083 ; 0.0016) |
| -23.500 | -1.8439 (-3.8450 ; 0.1088) | -0.3314 (-0.5938 ; 0.0216) | -0.7769 (-1.3957 ; 0.0506) | -0.3033 (-0.5542 ; 0.0200) | 0.0217 (-0.0010 ; 0.0592) | -0.0394 (-0.1066 ; 0.0016) |
| -23.750 | -1.8346 (-3.7930 ; 0.1085) | -0.3284 (-0.5828 ; 0.0209) | -0.7701 (-1.3701 ; 0.0489) | -0.2995 (-0.5410 ; 0.0193) | 0.0209 (-0.0009 ; 0.0570) | -0.0388 (-0.1050 ; 0.0016) |
| -24.000 | -1.8272 (-3.7484 ; 0.1084) | -0.3261 (-0.5739 ; 0.0203) | -0.7647 (-1.3495 ; 0.0476) | -0.2963 (-0.5302 ; 0.0187) | 0.0202 (-0.0009 ; 0.0550) | -0.0382 (-0.1035 ; 0.0015) |
| -24.250 | -1.8215 (-3.7105 ; 0.1086) | -0.3242 (-0.5669 ; 0.0199) | -0.7604 (-1.3332 ; 0.0466) | -0.2937 (-0.5213 ; 0.0183) | 0.0195 (-0.0008 ; 0.0531) | -0.0377 (-0.1021 ; 0.0015) |
| -24.500 | -1.8171 (-3.6786 ; 0.1089) | -0.3228 (-0.5615 ; 0.0196) | -0.7570 (-1.3205 ; 0.0458) | -0.2916 (-0.5141 ; 0.0179) | 0.0190 (-0.0008 ; 0.0515) | -0.0372 (-0.1008 ; 0.0015) |
| -24.750 | -1.8139 (-3.6524 ; 0.1093) | -0.3217 (-0.5573 ; 0.0193) | -0.7545 (-1.3107 ; 0.0452) | -0.2899 (-0.5083 ; 0.0177) | 0.0185 (-0.0007 ; 0.0502) | -0.0368 (-0.0996 ; 0.0014) |
| -25.000 | -1.8116 (-3.6314 ; 0.1096) | -0.3209 (-0.5541 ; 0.0191) | -0.7526 (-1.3034 ; 0.0447) | -0.2886 (-0.5039 ; 0.0174) | 0.0181 (-0.0007 ; 0.0490) | -0.0364 (-0.0987 ; 0.0014) |
| -25.250 | -1.8101 (-3.6152 ; 0.1097) | -0.3203 (-0.5518 ; 0.0189) | -0.7512 (-1.2981 ; 0.0442) | -0.2877 (-0.5006 ; 0.0172) | 0.0178 (-0.0006 ; 0.0481) | -0.0362 (-0.0979 ; 0.0014) |
| -25.500 | -1.8091 (-3.6043 ; 0.1099) | -0.3199 (-0.5503 ; 0.0188) | -0.7503 (-1.2945 ; 0.0439) | -0.2870 (-0.4984 ; 0.0171) | 0.0176 (-0.0006 ; 0.0475) | -0.0360 (-0.0974 ; 0.0013) |
| -25.750 | -1.8086 (-3.5964 ; 0.1086) | -0.3197 (-0.5494 ; 0.0184) | -0.7498 (-1.2924 ; 0.0431) | -0.2866 (-0.4970 ; 0.0167) | 0.0174 (-0.0006 ; 0.0471) | -0.0358 (-0.0970 ; 0.0013) |
| -26.000 | -1.8085 (-3.5964 ; 0.1085) | -0.3196 (-0.5490 ; 0.0184) | -0.7496 (-1.2916 ; 0.0431) | -0.2865 (-0.4965 ; 0.0167) | 0.0174 (-0.0006 ; 0.0470) | -0.0358 (-0.0970 ; 0.0013) |

## Vues (PNG, lues dans le MED de résultats)

Projections 2D produites par `aster_expert.report.figures` (matplotlib, sans interface : ParaVis hors interface est impossible ici, voir `docs/essais_lot36.md`). Repère : X le long du quai, Y vers la terre, Z ascendant. Aucune vue n'est un verdict : les limites de butée sont des constats sur le domaine du modèle linéaire.

### Cas G

**Déformée amplifiée ×10**

![Déformée amplifiée ×10 — cas G](vues/deformee_G.png)

**Cartographie de DY sur l'écran**

![Cartographie de DY sur l'écran — cas G](vues/dy_ecran_G.png)

**Efforts généralisés des tubes**

![Efforts généralisés des tubes — cas G](vues/efforts_tubes_G.png)

**Efforts généralisés des palplanches**

![Efforts généralisés des palplanches — cas G](vues/efforts_palplanches_G.png)

**Flèches : charges, ressorts, tirants**

![Flèches : charges, ressorts, tirants — cas G](vues/fleches_G.png)

**Diagrammes de la poutre de couronnement**

![Diagrammes de la poutre de couronnement — cas G](vues/poutre_G.png)

**Profils DY(z), M(z), N(z)**

![Profils DY(z), M(z), N(z) — cas G](vues/profils_G.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas G](vues/butee_G.png)

### Cas EAU_P

**Déformée amplifiée ×30**

![Déformée amplifiée ×30 — cas EAU_P](vues/deformee_EAU_P.png)

**Cartographie de DY sur l'écran**

![Cartographie de DY sur l'écran — cas EAU_P](vues/dy_ecran_EAU_P.png)

**Efforts généralisés des tubes**

![Efforts généralisés des tubes — cas EAU_P](vues/efforts_tubes_EAU_P.png)

**Efforts généralisés des palplanches**

![Efforts généralisés des palplanches — cas EAU_P](vues/efforts_palplanches_EAU_P.png)

**Flèches : charges, ressorts, tirants**

![Flèches : charges, ressorts, tirants — cas EAU_P](vues/fleches_EAU_P.png)

**Diagrammes de la poutre de couronnement**

![Diagrammes de la poutre de couronnement — cas EAU_P](vues/poutre_EAU_P.png)

**Profils DY(z), M(z), N(z)**

![Profils DY(z), M(z), N(z) — cas EAU_P](vues/profils_EAU_P.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas EAU_P](vues/butee_EAU_P.png)

### Cas EAU_A

**Déformée amplifiée ×10**

![Déformée amplifiée ×10 — cas EAU_A](vues/deformee_EAU_A.png)

**Cartographie de DY sur l'écran**

![Cartographie de DY sur l'écran — cas EAU_A](vues/dy_ecran_EAU_A.png)

**Efforts généralisés des tubes**

![Efforts généralisés des tubes — cas EAU_A](vues/efforts_tubes_EAU_A.png)

**Efforts généralisés des palplanches**

![Efforts généralisés des palplanches — cas EAU_A](vues/efforts_palplanches_EAU_A.png)

**Flèches : charges, ressorts, tirants**

![Flèches : charges, ressorts, tirants — cas EAU_A](vues/fleches_EAU_A.png)

**Diagrammes de la poutre de couronnement**

![Diagrammes de la poutre de couronnement — cas EAU_A](vues/poutre_EAU_A.png)

**Profils DY(z), M(z), N(z)**

![Profils DY(z), M(z), N(z) — cas EAU_A](vues/profils_EAU_A.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas EAU_A](vues/butee_EAU_A.png)

### Cas Q1

**Déformée amplifiée ×30**

![Déformée amplifiée ×30 — cas Q1](vues/deformee_Q1.png)

**Cartographie de DY sur l'écran**

![Cartographie de DY sur l'écran — cas Q1](vues/dy_ecran_Q1.png)

**Efforts généralisés des tubes**

![Efforts généralisés des tubes — cas Q1](vues/efforts_tubes_Q1.png)

**Efforts généralisés des palplanches**

![Efforts généralisés des palplanches — cas Q1](vues/efforts_palplanches_Q1.png)

**Flèches : charges, ressorts, tirants**

![Flèches : charges, ressorts, tirants — cas Q1](vues/fleches_Q1.png)

**Diagrammes de la poutre de couronnement**

![Diagrammes de la poutre de couronnement — cas Q1](vues/poutre_Q1.png)

**Profils DY(z), M(z), N(z)**

![Profils DY(z), M(z), N(z) — cas Q1](vues/profils_Q1.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas Q1](vues/butee_Q1.png)

### Cas Q3

**Déformée amplifiée ×100**

![Déformée amplifiée ×100 — cas Q3](vues/deformee_Q3.png)

**Cartographie de DY sur l'écran**

![Cartographie de DY sur l'écran — cas Q3](vues/dy_ecran_Q3.png)

**Efforts généralisés des tubes**

![Efforts généralisés des tubes — cas Q3](vues/efforts_tubes_Q3.png)

**Efforts généralisés des palplanches**

![Efforts généralisés des palplanches — cas Q3](vues/efforts_palplanches_Q3.png)

**Flèches : charges, ressorts, tirants**

![Flèches : charges, ressorts, tirants — cas Q3](vues/fleches_Q3.png)

**Diagrammes de la poutre de couronnement**

![Diagrammes de la poutre de couronnement — cas Q3](vues/poutre_Q3.png)

**Profils DY(z), M(z), N(z)**

![Profils DY(z), M(z), N(z) — cas Q3](vues/profils_Q3.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas Q3](vues/butee_Q3.png)

### Cas A

**Déformée amplifiée ×70**

![Déformée amplifiée ×70 — cas A](vues/deformee_A.png)

**Cartographie de DY sur l'écran**

![Cartographie de DY sur l'écran — cas A](vues/dy_ecran_A.png)

**Efforts généralisés des tubes**

![Efforts généralisés des tubes — cas A](vues/efforts_tubes_A.png)

**Efforts généralisés des palplanches**

![Efforts généralisés des palplanches — cas A](vues/efforts_palplanches_A.png)

**Flèches : charges, ressorts, tirants**

![Flèches : charges, ressorts, tirants — cas A](vues/fleches_A.png)

**Diagrammes de la poutre de couronnement**

![Diagrammes de la poutre de couronnement — cas A](vues/poutre_A.png)

**Profils DY(z), M(z), N(z)**

![Profils DY(z), M(z), N(z) — cas A](vues/profils_A.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas A](vues/butee_A.png)

## Contrôles de niveau D (équilibre et symétrie)

Seuil : 1e-06 (relatif). Bilan appliquée + réactions bloquées + ressorts = 0, par composante ; jamais un niveau E (aucune comparaison à une référence validée).

| Cas | X | Y | Z | Verdict |
|---|---:|---:|---:|---|
| EAU_A | -8.37e-13 | -8.01e-11 | -7.56e-13 | RÉUSSI |
| EAU_P | -1.53e-12 | -5.13e-11 | -3.66e-13 | RÉUSSI |
| G | 3.87e-13 | -5.00e-11 | -1.07e-12 | RÉUSSI |
| Q1 | 4.53e-12 | -8.76e-11 | -7.35e-13 | RÉUSSI |
| A | -1.90e-11 | 2.14e-10 | 0.00e+00 | informatif (aucun critère) |
| Q3 | 5.08e-12 | -2.28e-10 | 1.04e-12 | informatif (aucun critère) |

Symétrie des déplacements (paires de nœuds miroir), pire écart relatif :

| Cas | Paires vérifiées | Sans image miroir | Pire écart relatif |
|---|---:|---:|---:|
| A | 20057 | 0 | 5.65e-11 |
| EAU_A | 20057 | 0 | 2.39e-11 |
| EAU_P | 20057 | 0 | 2.88e-11 |
| G | 20057 | 0 | 2.73e-11 |
| Q1 | 20057 | 0 | 5.70e-11 |
| Q3 | 20057 | 0 | 5.44e-11 |

