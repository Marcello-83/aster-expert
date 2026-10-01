# Synthèse des résultats — QUAI-CW-TEST-01

## Ce que ce document est, et n'est pas

- Des **résultats de cas élémentaires** (G, EAU_P, EAU_A, Q1, Q3, A), lus dans le MED de résultats de Code_Aster. Aucune combinaison n'est faite, aucun verdict de dimensionnement n'est porté : la fiche ne décide aucune combinaison.
- Niveau de validation du calcul : C (exécuté jusqu'à `FIN`) avec contrôles D (voir plus bas) ; jamais E.
- Les grandeurs sont **linéaires** (modèle élastique, ressorts sans plafond) : un dépassement de la butée est un constat sur les limites du modèle, non une rupture calculée.

## Provenance

- **MED de résultats** : `data/processed/runs/20260925T125131-c67e28a1/proc.0/fort.80` (SHA-256 `f96877c38399ae23559083497f769249c96a4564ec1ca756556d3defc62a334e`), relu par `medcoupling` dans le conteneur : chaque grandeur de cette synthèse vient de ses champs.
- Contre-vérification : listing `data/processed/runs/20260925T125131-c67e28a1/proc.0/fort.6` (SHA-256 `b5477f72733efa16142a8827da4909e415996f4b843f3fef25cf6cba0f4eb731`) ; écart relatif maximal entre le MED et les tables imprimées, 72 tables : 4.81e-13.
- `.comm` : SHA-256 `093bb1ac1f186c9f8a64944c7854cb5355827088e69550f6832a6c5f0cd7a93d`
- Données : `data/examples/combiwall_model_data.yaml`

## Repères, champs et unités

| Grandeur | Champ | Composantes | Repère | Unité | Source du repère |
|---|---|---|---|---|---|
| Déplacement horizontal (tête, profils) | DEPL | DY | global : X le long du quai de SYM_G vers SYM_D, Y vers la terre, Z ascendant (décision du point 9) ; DY < 0 : vers le bassin | mm | fiche, point 9 |
| Effort axial d'un tirant | EFGE_ELNO | N | local de la barre (axe du tirant) ; N > 0 en traction | kN | U2.01.05 (efforts de poutre en repère « utilisateur ») |
| Efforts généralisés d'un tube (DKT) | EFGE_ELNO (par élément et par nœud, sans moyenne) | NXX, NYY, MXX, MYY | local « utilisateur » de la facette : x_l = projection de VECTEUR = (0, 0, 1) sur le plan de la facette, donc **verticale** ; z_l = normale ; y_l = z_l ^ x_l (tangente horizontale). NXX et MXX : effort normal et moment de flexion **verticaux** ; NYY et MYY : circonférentiels | kN/m ; kN·m/m (par mètre de largeur) | U4.42.01, mot clé COQUE, opérande ANGL_REP / VECTEUR ; U2.01.05 |
| Efforts généralisés d'une palplanche (ELAS_COQUE) | EFGE_NOEU uniquement (décision 2) | NXX, NYY, NXY, MXX, MYY, MXY, QX, QY | local « utilisateur » : x_l = projection de VECTEUR = L (voir ci-dessous) sur le plan de la palplanche (plan Y = 0) ; moyenne arithmétique aux nœuds des valeurs par élément, restreinte aux mailles PALPS | kN/m ; kN·m/m | U4.42.01 COQUE ; U2.01.05 ; fiche, point 1 (décision 2) |
| Efforts d'une poutre de couronnement (POU_D_T) | EFGE_ELNO (par élément et par nœud, sans moyenne) | N, VY, VZ, MT, MFY, MFZ | local de la poutre : x_l le long de l'élément (du premier au second nœud), y_l parallèle à Y global et z_l = x_l ^ y_l = Z global (repère par défaut, ANGL_VRIL = 0). MFY : moment de flexion dans le plan vertical (autour de y_l) ; MFZ : dans le plan horizontal | kN ; kN·m | U4.42.01, mot clé ORIENTATION (remarques) ; U2.01.05 |
| Réactions d'appui | REAC_NODA (RESULTANTE) | DX, DY, DZ | global ; seules les composantes bloquées comptent (ANCRAGES : DX, DY, DZ ; PIED_TUBES : DZ ; SYM_G, SYM_D : DX) | kN | lots 23 et 34 (constat de la fiche, points 1 et 8) |
| Force des ressorts sur l'écran | DEPL/DY des nœuds à ressort × raideur | −k·DY | global, direction Y (positive vers la terre) | kN | fiche, point 4 ; K_T_D_N = (0, k, 0) |

Axe L des palplanches (`VECTEUR`, repère global) : (0.0, 0.0, 1.0) (vertical). Tubes : `VECTEUR = (0, 0, 1)`.
Orientation des éléments de poutre : chaque élément est listé du X le plus bas au plus haut, donc x_l = +X, y_l = +Y, z_l = +Z (déduit de l'ordre des lignes de la table, non de la documentation).

Tubes : axes à X = -10.4, -7.8, -5.2, -2.6, 0, 2.6, 5.2, 7.8, 10.4 m, rayon 0.71 m ; « porteur » d'un point = tube (cercle de rayon R) ou palplanche (plan Y = 0) le portant.

## Résultats par cas élémentaire

### Cas élémentaire G

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -16.7481 mm, z = 2.600 m, x = -5.901 m, y = 0.111 m ; TUBE_03 ; nœud 567. Étendue sur les 322 nœuds des anneaux de tête : de -16.7481 à -16.7481 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 212.572 | 212.572 | 212.572 |
| 2 | -7.800 | 425.144 | 425.144 | 425.144 |
| 3 | -5.200 | 425.144 | 425.144 | 425.144 |
| 4 | -2.600 | 425.144 | 425.144 | 425.144 |
| 5 | 0.000 | 425.144 | 425.144 | 425.144 |
| 6 | 2.600 | 425.144 | 425.144 | 425.144 |
| 7 | 5.200 | 425.144 | 425.144 | 425.144 |
| 8 | 7.800 | 425.144 | 425.144 | 425.144 |
| 9 | 10.400 | 212.572 | 212.572 | 212.572 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1157.703 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8050 ; nœud 503 | -1068.033 | z = -4.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8022 ; nœud 10095 |
| NYY | 4449.235 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8050 ; nœud 503 | -872.505 | z = 2.250 m, x = -5.089 m, y = 0.701 m ; TUBE_03 ; maille 8049 ; nœud 10011 |
| MXX | 53.360 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8165 ; nœud 503 | -73.983 | z = 2.600 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 147 |
| MYY | 54.847 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8050 ; nœud 503 | -22.195 | z = 2.600 m, x = -10.400 m, y = 0.710 m ; TUBE_01 ; maille 2300 ; nœud 147 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 265.573 | z = -13.000 m, x = 6.146 m, y = 0.000 m ; PALP_07_08 ; nœud 39510 | -183.905 | z = -5.250 m, x = -3.782 m, y = 0.000 m ; PALP_03_04 ; nœud 38463 |
| NYY | 0.101 | z = 2.600 m, x = -8.982 m, y = 0.000 m ; PALP_01_02 ; nœud 37392 | -1.444 | z = -13.250 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15511 |
| NXY | 270.396 | z = -11.250 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15518 | -270.396 | z = -11.250 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17849 |
| MXX | 211.250 | z = -12.750 m, x = 4.018 m, y = 0.000 m ; PALP_06_07 ; nœud 39245 | -129.912 | z = -7.750 m, x = 6.618 m, y = 0.000 m ; PALP_07_08 ; nœud 39701 |
| MYY | 3.180 | z = -5.750 m, x = 7.090 m, y = 0.000 m ; TUBE_08 ; nœud 32980 | -2.544 | z = -13.750 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17733 |
| MXY | 0.173 | z = -10.750 m, x = 3.546 m, y = 0.000 m ; PALP_06_07 ; nœud 39275 | -0.173 | z = -10.750 m, x = 6.854 m, y = 0.000 m ; PALP_07_08 ; nœud 39740 |
| QX | 478.762 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -145.074 | z = -12.000 m, x = 6.146 m, y = 0.000 m ; PALP_07_08 ; nœud 37522 |
| QY | 15.555 | z = -13.500 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17732 | -15.555 | z = -13.500 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 11150 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 9.100 m, y = 0.340 m ; maille 79691 ; nœud 37615 | -0.000 | z = 3.300 m, x = -9.750 m, y = 0.340 m ; maille 79633 ; nœud 37564 |
| VY | 0.000 | z = 3.300 m, x = 7.475 m, y = 0.340 m ; maille 79686 ; nœud 37611 | -0.000 | z = 3.300 m, x = -5.850 m, y = 0.340 m ; maille 79645 ; nœud 37575 |
| VZ | 0.000 | z = 3.300 m, x = 1.950 m, y = 0.340 m ; maille 79669 ; nœud 37596 | -0.000 | z = 3.300 m, x = -10.075 m, y = 0.340 m ; maille 79632 ; nœud 37563 |
| MT | 0.000 | z = 3.300 m, x = 6.500 m, y = 0.340 m ; maille 79683 ; nœud 37608 | -0.000 | z = 3.300 m, x = -7.150 m, y = 0.340 m ; maille 79641 ; nœud 37571 |
| MFY | 0.000 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 | -0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 |
| MFZ | 0.000 | z = 3.300 m, x = -5.200 m, y = 0.340 m ; maille 79646 ; nœud 2257 | -0.000 | z = 3.300 m, x = 10.075 m, y = 0.340 m ; maille 79694 ; nœud 37618 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **3196.115** | **-1127.661** |
| PIED_TUBES | 0.000 | 0.000 | **4290.576** |
| SYM_G | **342.563** | 141.334 | -38.888 |
| SYM_D | **-342.563** | 141.334 | -38.888 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 3196.115 kN contre 3196.115 kN de réaction d'ancrage selon Y (écart relatif 0.0e+00) ; Σ N × sin θ = -1163.056 kN contre -1127.661 kN selon Z (écart relatif -3.1e-02, sous pesanteur l'ancrage porte en plus une part du poids propre du tirant : l'écart vertical n'est pas un défaut de lecture).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 15283.271 ; marne compacte 3964.566 ; total 19247.837.

### Cas élémentaire EAU_P

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -8.4793 mm, z = 2.600 m, x = -4.499 m, y = 0.111 m ; TUBE_03 ; nœud 440. Étendue sur les 322 nœuds des anneaux de tête : de -8.4793 à -8.4793 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 109.441 | 109.441 | 109.441 |
| 2 | -7.800 | 218.881 | 218.881 | 218.881 |
| 3 | -5.200 | 218.881 | 218.881 | 218.881 |
| 4 | -2.600 | 218.881 | 218.881 | 218.881 |
| 5 | 0.000 | 218.881 | 218.881 | 218.881 |
| 6 | 2.600 | 218.881 | 218.881 | 218.881 |
| 7 | 5.200 | 218.881 | 218.881 | 218.881 |
| 8 | 7.800 | 218.881 | 218.881 | 218.881 |
| 9 | 10.400 | 109.441 | 109.441 | 109.441 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 621.904 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8050 ; nœud 503 | -498.496 | z = -4.000 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8024 ; nœud 10097 |
| NYY | 2292.505 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8050 ; nœud 503 | -447.267 | z = 2.250 m, x = -5.089 m, y = 0.701 m ; TUBE_03 ; maille 8049 ; nœud 10011 |
| MXX | 27.460 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8165 ; nœud 503 | -38.053 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_04 ; maille 12765 ; nœud 784 |
| MYY | 28.235 | z = 2.500 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8050 ; nœud 503 | -11.416 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_04 ; maille 12765 ; nœud 784 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 126.259 | z = -13.000 m, x = -4.254 m, y = 0.000 m ; PALP_03_04 ; nœud 38262 | -52.541 | z = -4.750 m, x = -3.782 m, y = 0.000 m ; PALP_03_04 ; nœud 38465 |
| NYY | 0.026 | z = 2.600 m, x = -1.182 m, y = 0.000 m ; PALP_04_05 ; nœud 37464 | -0.535 | z = -13.000 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15512 |
| NXY | 98.864 | z = -11.250 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 19878 | -98.864 | z = -11.250 m, x = 3.310 m, y = 0.000 m ; TUBE_06 ; nœud 22209 |
| MXX | 86.209 | z = -12.750 m, x = -6.382 m, y = 0.000 m ; PALP_02_03 ; nœud 37997 | -47.744 | z = -6.750 m, x = -6.382 m, y = 0.000 m ; PALP_02_03 ; nœud 38145 |
| MYY | 1.587 | z = -3.750 m, x = 3.310 m, y = 0.000 m ; TUBE_06 ; nœud 22179 | -1.041 | z = -13.500 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 11150 |
| MXY | 0.069 | z = -10.250 m, x = 3.546 m, y = 0.000 m ; PALP_06_07 ; nœud 39277 | -0.069 | z = -10.250 m, x = 4.254 m, y = 0.000 m ; PALP_06_07 ; nœud 39430 |
| QX | 242.573 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -63.039 | z = 2.600 m, x = 9.454 m, y = 0.000 m ; PALP_08_09 ; nœud 37559 |
| QY | 6.826 | z = -3.750 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 36258 | -6.826 | z = -3.750 m, x = 3.310 m, y = 0.000 m ; TUBE_06 ; nœud 22179 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 9.100 m, y = 0.340 m ; maille 79691 ; nœud 37615 | -0.000 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |
| VY | 0.000 | z = 3.300 m, x = 7.475 m, y = 0.340 m ; maille 79686 ; nœud 37611 | -0.000 | z = 3.300 m, x = -7.150 m, y = 0.340 m ; maille 79641 ; nœud 37571 |
| VZ | 0.000 | z = 3.300 m, x = 0.650 m, y = 0.340 m ; maille 79665 ; nœud 37592 | -0.000 | z = 3.300 m, x = -2.275 m, y = 0.340 m ; maille 79656 ; nœud 37584 |
| MT | 0.000 | z = 3.300 m, x = 7.475 m, y = 0.340 m ; maille 79686 ; nœud 37611 | -0.000 | z = 3.300 m, x = -7.475 m, y = 0.340 m ; maille 79640 ; nœud 37570 |
| MFY | 0.000 | z = 3.300 m, x = 5.200 m, y = 0.340 m ; maille 79678 ; nœud 2261 | -0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 |
| MFZ | 0.000 | z = 3.300 m, x = -5.200 m, y = 0.340 m ; maille 79646 ; nœud 2257 | -0.000 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **1645.487** | **-598.787** |
| PIED_TUBES | -0.000 | 0.000 | **598.787** |
| SYM_G | **5.410** | 68.990 | -81.008 |
| SYM_D | **-5.410** | 68.990 | -81.008 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 1645.487 kN contre 1645.487 kN de réaction d'ancrage selon Y (écart relatif -1.4e-16) ; Σ N × sin θ = -598.787 kN contre -598.787 kN selon Z (écart relatif 1.9e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 4965.278 ; marne compacte 758.435 ; total 5723.713.

### Cas élémentaire EAU_A

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -19.8904 mm, z = 2.600 m, x = 5.910 m, y = 0.000 m ; TUBE_07 ; nœud 1561. Étendue sur les 322 nœuds des anneaux de tête : de -19.8904 à -19.8904 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 256.843 | 256.843 | 256.843 |
| 2 | -7.800 | 513.686 | 513.686 | 513.686 |
| 3 | -5.200 | 513.686 | 513.686 | 513.686 |
| 4 | -2.600 | 513.686 | 513.686 | 513.686 |
| 5 | 0.000 | 513.686 | 513.686 | 513.686 |
| 6 | 2.600 | 513.686 | 513.686 | 513.686 |
| 7 | 5.200 | 513.686 | 513.686 | 513.686 |
| 8 | 7.800 | 513.686 | 513.686 | 513.686 |
| 9 | 10.400 | 256.843 | 256.843 | 256.843 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1462.825 | z = 2.500 m, x = 5.200 m, y = 0.710 m ; TUBE_07 ; maille 26565 ; nœud 1623 | -1151.285 | z = -3.750 m, x = -5.200 m, y = 0.710 m ; TUBE_03 ; maille 8024 ; nœud 10098 |
| NYY | 5377.188 | z = 2.500 m, x = 5.200 m, y = 0.710 m ; TUBE_07 ; maille 26565 ; nœud 1623 | -1055.681 | z = 2.250 m, x = 5.089 m, y = 0.701 m ; TUBE_07 ; maille 26564 ; nœud 27669 |
| MXX | 64.441 | z = 2.500 m, x = 7.800 m, y = 0.710 m ; TUBE_08 ; maille 31165 ; nœud 1903 | -89.292 | z = 2.600 m, x = 7.800 m, y = 0.710 m ; TUBE_08 ; maille 31165 ; nœud 1904 |
| MYY | 66.261 | z = 2.500 m, x = 10.400 m, y = 0.710 m ; TUBE_09 ; maille 34615 ; nœud 2119 | -26.788 | z = 2.600 m, x = 7.800 m, y = 0.710 m ; TUBE_08 ; maille 31165 ; nœud 1904 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 293.244 | z = -13.000 m, x = 6.146 m, y = 0.000 m ; PALP_07_08 ; nœud 39510 | -122.494 | z = -4.750 m, x = -4.018 m, y = 0.000 m ; PALP_03_04 ; nœud 38414 |
| NYY | 0.060 | z = 2.600 m, x = -1.182 m, y = 0.000 m ; PALP_04_05 ; nœud 37464 | -1.244 | z = -13.000 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15512 |
| NXY | 229.947 | z = -11.250 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15518 | -229.947 | z = -11.250 m, x = 3.310 m, y = 0.000 m ; TUBE_06 ; nœud 22209 |
| MXX | 200.609 | z = -12.750 m, x = -6.382 m, y = 0.000 m ; PALP_02_03 ; nœud 37997 | -111.676 | z = -6.750 m, x = -6.382 m, y = 0.000 m ; PALP_02_03 ; nœud 38145 |
| MYY | 3.660 | z = -4.000 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 11187 | -2.419 | z = -13.500 m, x = 5.910 m, y = 0.000 m ; TUBE_07 ; nœud 26452 |
| MXY | 0.161 | z = -10.250 m, x = -6.854 m, y = 0.000 m ; PALP_02_03 ; nœud 38029 | -0.161 | z = -10.250 m, x = -6.146 m, y = 0.000 m ; PALP_02_03 ; nœud 38182 |
| QX | 569.760 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -148.028 | z = 2.600 m, x = -6.146 m, y = 0.000 m ; PALP_02_03 ; nœud 37415 |
| QY | 15.757 | z = -4.000 m, x = 1.890 m, y = 0.000 m ; TUBE_06 ; nœud 24267 | -15.757 | z = -4.000 m, x = 3.310 m, y = 0.000 m ; TUBE_06 ; nœud 22180 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 0.975 m, y = 0.340 m ; maille 79666 ; nœud 37593 | -0.000 | z = 3.300 m, x = -9.750 m, y = 0.340 m ; maille 79633 ; nœud 37564 |
| VY | 0.000 | z = 3.300 m, x = 7.475 m, y = 0.340 m ; maille 79686 ; nœud 37611 | -0.000 | z = 3.300 m, x = -7.150 m, y = 0.340 m ; maille 79641 ; nœud 37571 |
| VZ | 0.000 | z = 3.300 m, x = 1.950 m, y = 0.340 m ; maille 79669 ; nœud 37596 | -0.000 | z = 3.300 m, x = -1.300 m, y = 0.340 m ; maille 79659 ; nœud 37587 |
| MT | 0.000 | z = 3.300 m, x = 5.200 m, y = 0.340 m ; maille 79679 ; nœud 2261 | -0.000 | z = 3.300 m, x = -7.475 m, y = 0.340 m ; maille 79640 ; nœud 37570 |
| MFY | 0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79654 ; nœud 2258 | -0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 |
| MFZ | 0.000 | z = 3.300 m, x = 5.200 m, y = 0.340 m ; maille 79679 ; nœud 2261 | -0.000 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **3861.749** | **-1405.278** |
| PIED_TUBES | -0.000 | 0.000 | **1405.278** |
| SYM_G | **7.940** | 162.974 | -190.112 |
| SYM_D | **-7.940** | 162.974 | -190.112 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 3861.749 kN contre 3861.749 kN de réaction d'ancrage selon Y (écart relatif -1.2e-16) ; Σ N × sin θ = -1405.278 kN contre -1405.278 kN selon Z (écart relatif 0.0e+00, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 11557.279 ; marne compacte 1775.772 ; total 13333.051.

### Cas élémentaire Q1

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -9.9697 mm, z = 2.600 m, x = 5.901 m, y = 0.111 m ; TUBE_07 ; nœud 1560. Étendue sur les 322 nœuds des anneaux de tête : de -9.9697 à -9.9697 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 129.899 | 129.899 | 129.899 |
| 2 | -7.800 | 259.799 | 259.799 | 259.799 |
| 3 | -5.200 | 259.799 | 259.799 | 259.799 |
| 4 | -2.600 | 259.799 | 259.799 | 259.799 |
| 5 | 0.000 | 259.799 | 259.799 | 259.799 |
| 6 | 2.600 | 259.799 | 259.799 | 259.799 |
| 7 | 5.200 | 259.799 | 259.799 | 259.799 |
| 8 | 7.800 | 259.799 | 259.799 | 259.799 |
| 9 | 10.400 | 129.899 | 129.899 | 129.899 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 755.960 | z = 2.500 m, x = 5.200 m, y = 0.710 m ; TUBE_07 ; maille 26564 ; nœud 1623 | -434.959 | z = -13.250 m, x = -5.200 m, y = -0.710 m ; TUBE_03 ; maille 10401 ; nœud 12241 |
| NYY | 2712.522 | z = 2.500 m, x = 5.200 m, y = 0.710 m ; TUBE_07 ; maille 26564 ; nœud 1623 | -542.130 | z = 2.250 m, x = 5.089 m, y = 0.701 m ; TUBE_07 ; maille 26564 ; nœud 27669 |
| MXX | 32.576 | z = 2.500 m, x = 5.200 m, y = 0.710 m ; TUBE_07 ; maille 26450 ; nœud 1623 | -45.148 | z = 2.600 m, x = 7.800 m, y = 0.710 m ; TUBE_08 ; maille 31165 ; nœud 1904 |
| MYY | 33.508 | z = 2.500 m, x = 5.200 m, y = 0.710 m ; TUBE_07 ; maille 26450 ; nœud 1623 | -13.544 | z = 2.600 m, x = 2.600 m, y = 0.710 m ; TUBE_06 ; maille 21850 ; nœud 1344 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 110.927 | z = -13.000 m, x = -6.146 m, y = 0.000 m ; PALP_02_03 ; nœud 38019 | -51.686 | z = -4.750 m, x = -4.018 m, y = 0.000 m ; PALP_03_04 ; nœud 38414 |
| NYY | 0.027 | z = 2.600 m, x = -3.782 m, y = 0.000 m ; PALP_03_04 ; nœud 37440 | -0.488 | z = -13.000 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15512 |
| NXY | 90.549 | z = -11.250 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 15518 | -90.549 | z = -11.250 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17849 |
| MXX | 75.182 | z = -12.750 m, x = 4.018 m, y = 0.000 m ; PALP_06_07 ; nœud 39245 | -35.420 | z = -7.750 m, x = -6.382 m, y = 0.000 m ; PALP_02_03 ; nœud 38141 |
| MYY | 1.900 | z = 2.600 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 574 | -0.908 | z = -13.500 m, x = -4.490 m, y = 0.000 m ; TUBE_03 ; nœud 9012 |
| MXY | 0.075 | z = 2.600 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 574 | -0.075 | z = 2.600 m, x = 5.910 m, y = 0.000 m ; TUBE_07 ; nœud 1561 |
| QX | 215.254 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_04 ; nœud 721 | -55.983 | z = 2.600 m, x = -0.946 m, y = 0.000 m ; PALP_04_05 ; nœud 37463 |
| QY | 8.690 | z = 2.600 m, x = -5.910 m, y = 0.000 m ; TUBE_03 ; nœud 574 | -8.690 | z = 2.600 m, x = -7.090 m, y = 0.000 m ; TUBE_02 ; nœud 161 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 8.450 m, y = 0.340 m ; maille 79689 ; nœud 37613 | -0.000 | z = 3.300 m, x = -5.200 m, y = 0.340 m ; maille 79647 ; nœud 2257 |
| VY | 0.000 | z = 3.300 m, x = 7.475 m, y = 0.340 m ; maille 79686 ; nœud 37611 | -0.000 | z = 3.300 m, x = -5.850 m, y = 0.340 m ; maille 79645 ; nœud 37575 |
| VZ | 0.000 | z = 3.300 m, x = 0.325 m, y = 0.340 m ; maille 79664 ; nœud 37591 | -0.000 | z = 3.300 m, x = -0.325 m, y = 0.340 m ; maille 79662 ; nœud 37590 |
| MT | 0.000 | z = 3.300 m, x = 6.175 m, y = 0.340 m ; maille 79682 ; nœud 37607 | -0.000 | z = 3.300 m, x = -6.825 m, y = 0.340 m ; maille 79642 ; nœud 37572 |
| MFY | 0.000 | z = 3.300 m, x = -5.200 m, y = 0.340 m ; maille 79647 ; nœud 2257 | -0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 |
| MFZ | 0.000 | z = 3.300 m, x = 5.200 m, y = 0.340 m ; maille 79679 ; nœud 2261 | -0.000 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **1953.093** | **-710.724** |
| PIED_TUBES | 0.000 | 0.000 | **710.724** |
| SYM_G | **-66.130** | 104.326 | -96.279 |
| SYM_D | **66.130** | 104.326 | -96.279 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 1953.093 kN contre 1953.093 kN de réaction d'ancrage selon Y (écart relatif -1.2e-16) ; Σ N × sin θ = -710.724 kN contre -710.724 kN selon Z (écart relatif 1.6e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 4682.959 ; marne compacte 712.812 ; total 5395.771.

### Cas élémentaire Q3

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -4.6323 mm, z = 2.600 m, x = -0.701 m, y = 0.111 m ; TUBE_05 ; nœud 1127. Étendue sur les 322 nœuds des anneaux de tête : de -4.6323 à -4.3141 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | 57.899 | 57.899 | 57.899 |
| 2 | -7.800 | 117.063 | 117.063 | 117.063 |
| 3 | -5.200 | 120.460 | 120.460 | 120.460 |
| 4 | -2.600 | 124.670 | 124.670 | 124.670 |
| 5 | 0.000 | 127.094 | 127.094 | 127.094 |
| 6 | 2.600 | 124.670 | 124.670 | 124.670 |
| 7 | 5.200 | 120.460 | 120.460 | 120.460 |
| 8 | 7.800 | 117.063 | 117.063 | 117.063 |
| 9 | 10.400 | 57.899 | 57.899 | 57.899 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 528.088 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17249 ; nœud 1063 | -98.036 | z = 2.600 m, x = -10.400 m, y = -0.710 m ; TUBE_01 ; maille 115 ; nœud 14 |
| NYY | 1340.330 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17249 ; nœud 1063 | -266.177 | z = 2.250 m, x = 0.111 m, y = 0.701 m ; TUBE_05 ; maille 17249 ; nœud 18731 |
| MXX | 15.891 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1063 | -21.972 | z = 2.600 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1064 |
| MYY | 16.376 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1063 | -6.592 | z = 2.600 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17250 ; nœud 1064 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 33.459 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -11.481 | z = 2.600 m, x = 9.690 m, y = 0.000 m ; TUBE_09 ; nœud 2184 |
| NYY | 0.038 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -0.051 | z = -18.000 m, x = -1.182 m, y = 0.000 m ; PALP_04_05 ; nœud 37445 |
| NXY | 18.786 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 | -18.786 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 |
| MXX | 7.282 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -1.922 | z = 2.600 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 37490 |
| MYY | 0.033 | z = 2.600 m, x = -0.946 m, y = 0.000 m ; PALP_04_05 ; nœud 37463 | -0.123 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 |
| MXY | 0.008 | z = 2.500 m, x = -0.946 m, y = 0.000 m ; PALP_04_05 ; nœud 37459 | -0.008 | z = 2.500 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 37486 |
| QX | 8.941 | z = 2.600 m, x = -3.310 m, y = 0.000 m ; TUBE_04 ; nœud 854 | -2.612 | z = 2.600 m, x = 3.546 m, y = 0.000 m ; PALP_06_07 ; nœud 37514 |
| QY | 0.675 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -0.675 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.405 | z = 3.300 m, x = 1.625 m, y = 0.340 m ; maille 79668 ; nœud 37595 | -0.183 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |
| VY | 376.849 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 | -376.849 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79655 ; nœud 2258 |
| VZ | 176.412 | z = 3.300 m, x = -0.325 m, y = 0.340 m ; maille 79662 ; nœud 37590 | -176.412 | z = 3.300 m, x = 0.650 m, y = 0.340 m ; maille 79665 ; nœud 37592 |
| MT | 267.738 | z = 3.300 m, x = -1.625 m, y = 0.340 m ; maille 79658 ; nœud 37586 | -267.738 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 79670 ; nœud 37597 |
| MFY | 523.312 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -150.007 | z = 3.300 m, x = -7.800 m, y = 0.340 m ; maille 79639 ; nœud 2256 |
| MFZ | 1455.678 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -752.247 | z = 3.300 m, x = 10.400 m, y = 0.340 m ; maille 79694 ; nœud 2263 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **908.967** | **-330.770** |
| PIED_TUBES | -0.000 | -0.000 | **-169.230** |
| SYM_G | **-151.399** | 88.822 | -44.256 |
| SYM_D | **151.399** | 88.822 | -44.256 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 908.967 kN contre 908.967 kN de réaction d'ancrage selon Y (écart relatif -1.3e-16) ; Σ N × sin θ = -330.770 kN contre -330.770 kN selon Z (écart relatif 0.0e+00, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 12.705 ; marne compacte -55.673 ; total -42.967.

### Cas élémentaire A

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue 3.6688 mm, z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001. Étendue sur les 322 nœuds des anneaux de tête : de 3.2437 à 3.6688 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -10.400 | -42.882 | -42.882 | -42.882 |
| 2 | -7.800 | -86.832 | -86.832 | -86.832 |
| 3 | -5.200 | -89.734 | -89.734 | -89.734 |
| 4 | -2.600 | -93.531 | -93.531 | -93.531 |
| 5 | 0.000 | -96.721 | -96.721 | -96.721 |
| 6 | 2.600 | -93.531 | -93.531 | -93.531 |
| 7 | 5.200 | -89.734 | -89.734 | -89.734 |
| 8 | 7.800 | -86.832 | -86.832 | -86.832 |
| 9 | 10.400 | -42.882 | -42.882 | -42.882 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 2065.321 | z = 2.600 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; maille 19665 ; nœud 1204 | -1205.253 | z = 2.600 m, x = 0.675 m, y = -0.219 m ; TUBE_05 ; maille 20585 ; nœud 1260 |
| NYY | 619.596 | z = 2.600 m, x = 0.000 m, y = -0.710 m ; TUBE_05 ; maille 19665 ; nœud 1204 | -1008.568 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1063 |
| MXX | 16.874 | z = 2.600 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1064 | -12.160 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1063 |
| MYY | 5.062 | z = 2.600 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1064 | -12.480 | z = 2.500 m, x = 0.000 m, y = 0.710 m ; TUBE_05 ; maille 17365 ; nœud 1063 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 180.246 | z = 0.250 m, x = 0.946 m, y = 0.000 m ; PALP_05_06 ; nœud 39007 | -606.030 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| NYY | 0.190 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -0.366 | z = -0.500 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 19921 |
| NXY | 234.282 | z = 1.250 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 19927 | -234.282 | z = 1.250 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17857 |
| MXX | 44.682 | z = 2.500 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 999 | -36.455 | z = 1.250 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 17857 |
| MYY | 0.355 | z = 1.000 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1131 | -0.422 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 |
| MXY | 0.057 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -0.057 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| QX | 111.247 | z = 2.000 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 997 | -296.373 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |
| QY | 2.446 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1001 | -2.446 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_05 ; nœud 1134 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.445 | z = 3.300 m, x = 1.625 m, y = 0.340 m ; maille 79668 ; nœud 37595 | -0.186 | z = 3.300 m, x = 7.475 m, y = 0.340 m ; maille 79686 ; nœud 37611 |
| VY | 337.609 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 79661 ; nœud 37589 | -337.609 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 79670 ; nœud 37597 |
| VZ | 6.960 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 79661 ; nœud 37589 | -6.960 | z = 3.300 m, x = 0.325 m, y = 0.340 m ; maille 79664 ; nœud 37591 |
| MT | 517.115 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 79655 ; nœud 2258 | -517.115 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 |
| MFY | 24.823 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79662 ; nœud 2259 | -17.012 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 |
| MFZ | 663.971 | z = 3.300 m, x = -10.400 m, y = 0.340 m ; maille 79631 ; nœud 2255 | -1297.173 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 79663 ; nœud 2259 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **-0.000** | **-679.112** | **247.127** |
| PIED_TUBES | -0.000 | 0.000 | **-247.127** |
| SYM_G | **112.203** | -72.257 | 29.681 |
| SYM_D | **-112.203** | -72.257 | 29.681 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = -679.112 kN contre -679.112 kN de réaction d'ancrage selon Y (écart relatif 0.0e+00) ; Σ N × sin θ = 247.127 kN contre 247.127 kN selon Z (écart relatif -1.2e-16, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse -216.967 ; marne compacte 96.079 ; total -120.888.

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

## Profils du déplacement horizontal DY le long des tubes

`DEPL`, `DY`, repère global, en mm (< 0 vers le bassin). Chaque valeur est la **moyenne de DY sur l'anneau de nœuds** du tube à la cote donnée ; l'étendue (minimum à maximum sur l'anneau) figure entre parenthèses.

### TUBE_05

| Cote (m) | G | EAU_P | EAU_A | Q1 | Q3 | A |
|---:|---:|---:|---:|---:|---:|---:|
| 2.600 | -16.7481 (-16.7481 ; -16.7481) | -8.4793 (-8.4793 ; -8.4793) | -19.8904 (-19.8904 ; -19.8904) | -9.9697 (-9.9697 ; -9.9697) | -4.6323 (-4.6323 ; -4.6323) | 3.6688 (3.6688 ; 3.6688) |
| 2.500 | -16.8897 (-17.3303 ; -13.5688) | -8.5329 (-8.7611 ; -6.8244) | -20.0109 (-20.5469 ; -16.0018) | -9.9744 (-10.2460 ; -7.9473) | -4.5462 (-4.6829 ; -3.5597) | 3.6800 (2.8902 ; 3.9237) |
| 2.250 | -17.5645 (-17.9566 ; -16.7603) | -8.8320 (-9.0363 ; -8.4184) | -20.6990 (-21.1786 ; -19.7303) | -10.1789 (-10.4208 ; -9.6871) | -4.4201 (-4.5397 ; -4.1899) | 3.7772 (3.4862 ; 4.6280) |
| 2.000 | -18.1380 (-18.3743 ; -17.5941) | -9.0794 (-9.2035 ; -8.7975) | -21.2654 (-21.5564 ; -20.6079) | -10.3218 (-10.4702 ; -9.9852) | -4.2667 (-4.3294 ; -4.1162) | 3.8672 (3.3862 ; 5.4508) |
| 1.750 | -18.7112 (-18.8907 ; -18.2863) | -9.3275 (-9.4219 ; -9.1039) | -21.8332 (-22.0533 ; -21.3152) | -10.4664 (-10.5821 ; -10.1991) | -4.1194 (-4.1574 ; -4.0058) | 3.9544 (3.2232 ; 6.2983) |
| 1.500 | -19.2779 (-19.4191 ; -18.9575) | -9.5730 (-9.6480 ; -9.3989) | -22.3945 (-22.5680 ; -21.9964) | -10.6088 (-10.7005 ; -10.4020) | -3.9760 (-3.9997 ; -3.8930) | 4.0049 (3.1145 ; 6.9292) |
| 1.250 | -19.8320 (-19.9438 ; -19.5658) | -9.8124 (-9.8729 ; -9.6609) | -22.9418 (-23.0798 ; -22.6008) | -10.7456 (-10.8182 ; -10.5690) | -3.8355 (-3.8520 ; -3.7663) | 4.0406 (3.0819 ; 7.4074) |
| 1.000 | -20.3742 (-20.4667 ; -20.1545) | -10.0461 (-10.0983 ; -9.9123) | -23.4757 (-23.5910 ; -23.1806) | -10.8775 (-10.9369 ; -10.7265) | -3.6984 (-3.7123 ; -3.6395) | 4.0362 (3.1276 ; 7.5819) |
| 0.750 | -20.9020 (-20.9835 ; -20.7190) | -10.2725 (-10.3219 ; -10.1510) | -23.9931 (-24.0970 ; -23.7303) | -11.0033 (-11.0543 ; -10.8719) | -3.5643 (-3.5806 ; -3.5120) | 4.0181 (3.2015 ; 7.5697) |
| 0.500 | -21.4141 (-21.4903 ; -21.2633) | -10.4909 (-10.5390 ; -10.3792) | -24.4924 (-24.5913 ; -24.2553) | -11.1224 (-11.1683 ; -11.0078) | -3.4334 (-3.4524 ; -3.3857) | 4.0130 (3.1652 ; 7.5117) |
| 0.250 | -21.9090 (-21.9839 ; -21.7877) | -10.7003 (-10.7480 ; -10.5969) | -24.9714 (-25.0691 ; -24.7561) | -11.2342 (-11.2773 ; -11.1345) | -3.3056 (-3.3274 ; -3.2614) | 4.0001 (3.1152 ; 7.3441) |
| 0.000 | -22.3852 (-22.4615 ; -22.2836) | -10.8999 (-10.9480 ; -10.8047) | -25.4284 (-25.5290 ; -25.2332) | -11.3382 (-11.3798 ; -11.2524) | -3.1808 (-3.2055 ; -3.1395) | 3.9830 (3.0487 ; 7.1243) |
| -0.250 | -22.8413 (-22.9213 ; -22.7187) | -11.0891 (-11.1381 ; -11.0017) | -25.8616 (-25.9673 ; -25.6855) | -11.4336 (-11.4751 ; -11.3613) | -3.0590 (-3.0866 ; -3.0202) | 3.9616 (2.9487 ; 6.8801) |
| -0.500 | -23.2760 (-23.3616 ; -23.1299) | -11.2672 (-11.3192 ; -11.1686) | -26.2693 (-26.3820 ; -26.0655) | -11.5202 (-11.5622 ; -11.4551) | -2.9402 (-2.9705 ; -2.9035) | 3.9359 (2.8271 ; 6.6289) |
| -0.750 | -23.6881 (-23.7810 ; -23.5158) | -11.4334 (-11.4889 ; -11.3235) | -26.6498 (-26.7711 ; -26.4167) | -11.5973 (-11.6408 ; -11.5242) | -2.8243 (-2.8571 ; -2.7895) | 3.9062 (2.7124 ; 6.3816) |
| -1.000 | -24.0763 (-24.1838 ; -23.8749) | -11.5873 (-11.6467 ; -11.4654) | -27.0018 (-27.1331 ; -26.7378) | -11.6646 (-11.7103 ; -11.5824) | -2.7113 (-2.7462 ; -2.6781) | 3.8725 (2.6080 ; 6.1443) |
| -1.250 | -24.4395 (-24.5641 ; -24.2056) | -11.7282 (-11.7920 ; -11.5937) | -27.3240 (-27.4666 ; -27.0272) | -11.7217 (-11.7703 ; -11.6291) | -2.6012 (-2.6379 ; -2.5694) | 3.8349 (2.5158 ; 5.9200) |
| -1.500 | -24.7765 (-24.9204 ; -24.5067) | -11.8556 (-11.9244 ; -11.7076) | -27.6153 (-27.7704 ; -27.2833) | -11.7682 (-11.8205 ; -11.6639) | -2.4939 (-2.5319 ; -2.4633) | 3.7937 (2.4365 ; 5.7098) |
| -1.750 | -25.0864 (-25.2543 ; -24.7767) | -11.9691 (-12.0433 ; -11.8065) | -27.8744 (-28.0433 ; -27.5048) | -11.8038 (-11.8635 ; -11.6863) | -2.3894 (-2.4284 ; -2.3599) | 3.7490 (2.3701 ; 5.5136) |
| -2.000 | -25.3681 (-25.5670 ; -25.0144) | -12.0683 (-12.1485 ; -11.8895) | -28.1004 (-28.2853 ; -27.6904) | -11.8281 (-11.8961 ; -11.6960) | -2.2877 (-2.3273 ; -2.2591) | 3.7009 (2.3157 ; 5.3303) |
| -2.250 | -25.6209 (-25.8538 ; -25.2185) | -12.1526 (-12.2433 ; -11.9562) | -28.2924 (-28.5019 ; -27.8386) | -11.8410 (-11.9182 ; -11.6925) | -2.1886 (-2.2286 ; -2.1608) | 3.6495 (2.2721 ; 5.1585) |
| -2.500 | -25.8440 (-26.1198 ; -25.3879) | -12.2220 (-12.3241 ; -12.0061) | -28.4497 (-28.6860 ; -27.9483) | -11.8423 (-11.9311 ; -11.6757) | -2.0923 (-2.1323 ; -2.0652) | 3.5950 (2.2380 ; 4.9968) |
| -2.750 | -26.0367 (-26.3614 ; -25.5215) | -12.2759 (-12.3905 ; -12.0386) | -28.5715 (-28.8369 ; -28.0185) | -11.8318 (-11.9357 ; -11.6451) | -1.9986 (-2.0383 ; -1.9722) | 3.5376 (2.2116 ; 4.8434) |
| -3.000 | -26.1982 (-26.5805 ; -25.6183) | -12.3142 (-12.4431 ; -12.0534) | -28.6572 (-28.9549 ; -28.0480) | -11.8094 (-11.9301 ; -11.6006) | -1.9075 (-1.9468 ; -1.8818) | 3.4774 (2.1914 ; 4.6968) |
| -3.250 | -26.3280 (-26.7736 ; -25.6772) | -12.3367 (-12.4852 ; -12.0501) | -28.7064 (-29.0494 ; -28.0360) | -11.7749 (-11.9169 ; -11.5420) | -1.8191 (-1.8576 ; -1.7939) | 3.4144 (2.1757 ; 4.5557) |
| -3.500 | -26.4255 (-26.9395 ; -25.6974) | -12.3433 (-12.5128 ; -12.0283) | -28.7187 (-29.1105 ; -27.9817) | -11.7283 (-11.8957 ; -11.4689) | -1.7331 (-1.7709 ; -1.7086) | 3.3490 (2.1632 ; 4.4186) |
| -3.750 | -26.4903 (-27.0780 ; -25.6780) | -12.3337 (-12.5296 ; -11.9879) | -28.6939 (-29.1450 ; -27.8845) | -11.6695 (-11.8652 ; -11.3814) | -1.6497 (-1.6865 ; -1.6258) | 3.2812 (2.1525 ; 4.2847) |
| -4.000 | -26.5220 (-27.1891 ; -25.6184) | -12.3081 (-12.5343 ; -11.9286) | -28.6318 (-29.1521 ; -27.7438) | -11.5985 (-11.8245 ; -11.2792) | -1.5688 (-1.6045 ; -1.5455) | 3.2111 (2.1425 ; 4.1528) |
| -4.250 | -26.5204 (-27.2728 ; -25.5178) | -12.2662 (-12.5279 ; -11.8503) | -28.5323 (-29.1345 ; -27.5593) | -11.5153 (-11.7737 ; -11.1623) | -1.4903 (-1.5249 ; -1.4677) | 3.1390 (2.1321 ; 4.0224) |
| -4.500 | -26.4851 (-27.3289 ; -25.3757) | -12.2083 (-12.5080 ; -11.7528) | -28.3956 (-29.0863 ; -27.3306) | -11.4200 (-11.7128 ; -11.0306) | -1.4142 (-1.4477 ; -1.3923) | 3.0649 (2.1207 ; 3.8929) |
| -4.750 | -26.4162 (-27.3577 ; -25.1916) | -12.1343 (-12.4743 ; -11.6361) | -28.2217 (-29.0063 ; -27.0576) | -11.3127 (-11.6421 ; -10.8841) | -1.3405 (-1.3727 ; -1.3194) | 2.9891 (2.1075 ; 3.7637) |
| -5.000 | -26.3136 (-27.3593 ; -24.9651) | -12.0444 (-12.4271 ; -11.5002) | -28.0109 (-28.8950 ; -26.7402) | -11.1934 (-11.5616 ; -10.7229) | -1.2692 (-1.3001 ; -1.2488) | 2.9116 (2.0922 ; 3.6347) |
| -5.250 | -26.1773 (-27.3338 ; -24.6959) | -11.9387 (-12.3664 ; -11.3451) | -27.7637 (-28.7528 ; -26.3785) | -11.0623 (-11.4716 ; -10.5468) | -1.2002 (-1.2298 ; -1.1806) | 2.8327 (2.0743 ; 3.5057) |
| -5.500 | -26.0074 (-27.2815 ; -24.3838) | -11.8174 (-12.2926 ; -11.1710) | -27.4805 (-28.5803 ; -25.9727) | -10.9197 (-11.3723 ; -10.3560) | -1.1334 (-1.1617 ; -1.1147) | 2.7524 (2.0537 ; 3.3765) |
| -5.750 | -25.8043 (-27.2029 ; -24.0286) | -11.6809 (-12.2060 ; -10.9780) | -27.1619 (-28.3782 ; -25.5231) | -10.7657 (-11.2638 ; -10.1506) | -1.0690 (-1.0959 ; -1.0511) | 2.6709 (2.0301 ; 3.2473) |
| -6.000 | -25.5683 (-27.0982 ; -23.6303) | -11.5294 (-12.1069 ; -10.7663) | -26.8086 (-28.1471 ; -25.0302) | -10.6005 (-11.1464 ; -9.9306) | -1.0067 (-1.0323 ; -0.9897) | 2.5884 (2.0037 ; 3.1179) |
| -6.250 | -25.2997 (-26.9680 ; -23.1891) | -11.3632 (-11.9957 ; -10.5362) | -26.4214 (-27.8881 ; -24.4947) | -10.4245 (-11.0203 ; -9.6962) | -0.9466 (-0.9709 ; -0.9305) | 2.5050 (1.9744 ; 2.9886) |
| -6.500 | -24.9991 (-26.8129 ; -22.7051) | -11.1828 (-11.8728 ; -10.2880) | -26.0012 (-27.6020 ; -23.9172) | -10.2379 (-10.8859 ; -9.4476) | -0.8887 (-0.9117 ; -0.8734) | 2.4208 (1.9424 ; 2.8594) |
| -6.750 | -24.6672 (-26.6336 ; -22.1789) | -10.9886 (-11.7387 ; -10.0221) | -25.5490 (-27.2899 ; -23.2987) | -10.0412 (-10.7433 ; -9.1849) | -0.8329 (-0.8545 ; -0.8185) | 2.3361 (1.9077 ; 2.7305) |
| -7.000 | -24.3047 (-26.4307 ; -21.6109) | -10.7810 (-11.5939 ; -9.7390) | -25.0659 (-26.9530 ; -22.6402) | -9.8347 (-10.5928 ; -8.9085) | -0.7792 (-0.7995 ; -0.7657) | 2.2509 (1.8706 ; 2.6021) |
| -7.250 | -23.9123 (-26.2051 ; -21.0020) | -10.5607 (-11.4389 ; -9.4393) | -24.5532 (-26.5926 ; -21.9432) | -9.6187 (-10.4349 ; -8.6187) | -0.7275 (-0.7466 ; -0.7150) | 2.1654 (1.8312 ; 2.4743) |
| -7.500 | -23.4910 (-25.9580 ; -20.3530) | -10.3281 (-11.2744 ; -9.1236) | -24.0121 (-26.2100 ; -21.2089) | -9.3938 (-10.2699 ; -8.3158) | -0.6779 (-0.6957 ; -0.6663) | 2.0797 (1.7898 ; 2.3473) |
| -7.750 | -23.0419 (-25.6902 ; -19.6652) | -10.0839 (-11.1009 ; -8.7925) | -23.4440 (-25.8067 ; -20.4391) | -9.1604 (-10.0983 ; -8.0006) | -0.6303 (-0.6468 ; -0.6195) | 1.9941 (1.7465 ; 2.2214) |
| -8.000 | -22.5662 (-25.4033 ; -18.9401) | -9.8287 (-10.9192 ; -8.4470) | -22.8506 (-25.3844 ; -19.6356) | -8.9190 (-9.9206 ; -7.6734) | -0.5846 (-0.5999 ; -0.5747) | 1.9086 (1.7017 ; 2.0966) |
| -8.250 | -22.0649 (-25.0984 ; -18.1794) | -9.5633 (-10.7301 ; -8.0879) | -22.2333 (-24.9448 ; -18.8007) | -8.6701 (-9.7375 ; -7.3353) | -0.5408 (-0.5549 ; -0.5318) | 1.8234 (1.6555 ; 1.9731) |
| -8.500 | -21.5396 (-24.7772 ; -17.3853) | -9.2883 (-10.5342 ; -7.7162) | -21.5940 (-24.4896 ; -17.9368) | -8.4143 (-9.5495 ; -6.9871) | -0.4990 (-0.5118 ; -0.4907) | 1.7385 (1.6081 ; 1.8512) |
| -8.750 | -20.9915 (-24.4413 ; -16.5604) | -9.0046 (-10.3325 ; -7.3333) | -20.9344 (-24.0209 ; -17.0464) | -8.1523 (-9.3575 ; -6.6298) | -0.4590 (-0.4706 ; -0.4515) | 1.6543 (1.5599 ; 1.7310) |
| -9.000 | -20.4225 (-24.0927 ; -15.7073) | -8.7130 (-10.1258 ; -6.9403) | -20.2564 (-23.5405 ; -16.1328) | -7.8847 (-9.1629 ; -6.2647) | -0.4208 (-0.4312 ; -0.4140) | 1.5708 (1.5109 ; 1.6126) |
| -9.250 | -19.8341 (-23.7332 ; -14.8296) | -8.4143 (-9.9150 ; -6.5387) | -19.5621 (-23.0505 ; -15.1992) | -7.6120 (-8.9659 ; -5.8930) | -0.3845 (-0.3937 ; -0.3783) | 1.4882 (1.4614 ; 1.5017) |
| -9.500 | -19.2280 (-23.3645 ; -13.9309) | -8.1094 (-9.7009 ; -6.1302) | -18.8535 (-22.5530 ; -14.2495) | -7.3347 (-8.7666 ; -5.5164) | -0.3499 (-0.3578 ; -0.3443) | 1.4065 (1.3822 ; 1.4140) |
| -9.750 | -18.6061 (-22.9886 ; -13.0156) | -7.7994 (-9.4843 ; -5.7165) | -18.1328 (-22.0499 ; -13.2878) | -7.0536 (-8.5667 ; -5.1365) | -0.3170 (-0.3238 ; -0.3119) | 1.3260 (1.2706 ; 1.3616) |
| -10.000 | -17.9705 (-22.6074 ; -12.0887) | -7.4851 (-9.2662 ; -5.2996) | -17.4023 (-21.5432 ; -12.3188) | -6.7696 (-8.3667 ; -4.7550) | -0.2858 (-0.2914 ; -0.2811) | 1.2468 (1.1616 ; 1.3116) |
| -10.250 | -17.3233 (-22.2223 ; -11.1557) | -7.1676 (-9.0472 ; -4.8819) | -16.6644 (-21.0343 ; -11.3478) | -6.4834 (-8.1673 ; -4.3742) | -0.2563 (-0.2607 ; -0.2518) | 1.1690 (1.0555 ; 1.2619) |
| -10.500 | -16.6667 (-21.8347 ; -10.2230) | -6.8480 (-8.8279 ; -4.4660) | -15.9215 (-20.5248 ; -10.3808) | -6.1959 (-7.9690 ; -3.9962) | -0.2285 (-0.2322 ; -0.2241) | 1.0928 (0.9525 ; 1.2123) |
| -10.750 | -16.0031 (-21.4451 ; -9.2983) | -6.5273 (-8.6087 ; -4.0547) | -15.1762 (-20.0155 ; -9.4247) | -5.9079 (-7.7720 ; -3.6237) | -0.2022 (-0.2057 ; -0.1979) | 1.0184 (0.8530 ; 1.1632) |
| -11.000 | -15.3349 (-21.0537 ; -8.3902) | -6.2067 (-8.3896 ; -3.6515) | -14.4311 (-19.5067 ; -8.4876) | -5.6205 (-7.5764 ; -3.2598) | -0.1775 (-0.1810 ; -0.1730) | 0.9457 (0.7574 ; 1.1144) |
| -11.250 | -14.6648 (-20.6598 ; -7.5088) | -5.8873 (-8.1707 ; -3.2605) | -13.6888 (-18.9981 ; -7.5786) | -5.3345 (-7.3817 ; -2.9078) | -0.1543 (-0.1582 ; -0.1495) | 0.8751 (0.6660 ; 1.0661) |
| -11.500 | -13.9952 (-20.2620 ; -6.6645) | -5.5703 (-7.9515 ; -2.8857) | -12.9521 (-18.4888 ; -6.7074) | -5.0509 (-7.1876 ; -2.5715) | -0.1327 (-0.1369 ; -0.1273) | 0.8066 (0.5794 ; 1.0182) |
| -11.750 | -13.3303 (-19.8586 ; -5.8722) | -5.2574 (-7.7314 ; -2.5332) | -12.2249 (-17.9775 ; -5.8880) | -4.7713 (-6.9933 ; -2.2562) | -0.1125 (-0.1172 ; -0.1064) | 0.7405 (0.4986 ; 0.9706) |
| -12.000 | -12.6653 (-19.4477 ; -5.1100) | -4.9468 (-7.5098 ; -2.1938) | -11.5029 (-17.4629 ; -5.0992) | -4.4938 (-6.7982 ; -1.9534) | -0.0937 (-0.0988 ; -0.0867) | 0.6763 (0.4217 ; 0.9233) |
| -12.250 | -12.0161 (-19.0273 ; -4.4066) | -4.6449 (-7.2862 ; -1.8813) | -10.8014 (-16.9435 ; -4.3729) | -4.2243 (-6.6016 ; -1.6749) | -0.0763 (-0.0820 ; -0.0681) | 0.6151 (0.3521 ; 0.8763) |
| -12.500 | -11.3942 (-18.5956 ; -3.7721) | -4.3565 (-7.0600 ; -1.6012) | -10.1310 (-16.4181 ; -3.7217) | -3.9669 (-6.4028 ; -1.4253) | -0.0605 (-0.0669 ; -0.0507) | 0.5575 (0.2911 ; 0.8295) |
| -12.750 | -10.7940 (-18.1510 ; -3.1813) | -4.0791 (-6.8308 ; -1.3427) | -9.4865 (-15.8855 ; -3.1209) | -3.7195 (-6.2012 ; -1.1949) | -0.0461 (-0.0532 ; -0.0344) | 0.5031 (0.2364 ; 0.7828) |
| -13.000 | -10.2178 (-17.6922 ; -2.6406) | -3.8139 (-6.5981 ; -1.1082) | -8.8700 (-15.3449 ; -2.5758) | -3.4829 (-5.9965 ; -0.9858) | -0.0330 (-0.0409 ; -0.0191) | 0.4518 (0.1883 ; 0.7363) |
| -13.250 | -9.6663 (-17.2184 ; -2.1504) | -3.5609 (-6.3617 ; -0.8976) | -8.2821 (-14.7959 ; -2.0862) | -3.2574 (-5.7883 ; -0.7978) | -0.0212 (-0.0302 ; -0.0049) | 0.4038 (0.1463 ; 0.6899) |
| -13.500 | -9.1399 (-16.7296 ; -1.7101) | -3.3204 (-6.1219 ; -0.7101) | -7.7232 (-14.2387 ; -1.6505) | -3.0429 (-5.5768 ; -0.6304) | -0.0106 (-0.0210 ; 0.0083) | 0.3588 (0.1099 ; 0.6437) |
| -13.750 | -8.6386 (-16.2268 ; -1.3178) | -3.0924 (-5.8789 ; -0.5448) | -7.1933 (-13.6743 ; -1.2662) | -2.8395 (-5.3622 ; -0.4826) | -0.0011 (-0.0135 ; 0.0205) | 0.3168 (0.0788 ; 0.5977) |
| -14.000 | -8.1624 (-15.7116 ; -0.9708) | -2.8768 (-5.6336 ; -0.4001) | -6.6922 (-13.1044 ; -0.9298) | -2.6472 (-5.1451 ; -0.3532) | 0.0074 (-0.0075 ; 0.0318) | 0.2778 (0.0523 ; 0.5520) |
| -14.250 | -7.7109 (-15.1862 ; -0.6656) | -2.6734 (-5.3868 ; -0.2743) | -6.2197 (-12.5310 ; -0.6375) | -2.4656 (-4.9264 ; -0.2406) | 0.0148 (-0.0030 ; 0.0421) | 0.2416 (0.0301 ; 0.5068) |
| -14.500 | -7.2836 (-14.6535 ; -0.3990) | -2.4821 (-5.1395 ; -0.1659) | -5.7750 (-11.9564 ; -0.3854) | -2.2947 (-4.7067 ; -0.1433) | 0.0213 (0.0003 ; 0.0514) | 0.2081 (0.0116 ; 0.4621) |
| -14.750 | -6.8800 (-14.1162 ; -0.1678) | -2.3025 (-4.8928 ; -0.0732) | -5.3577 (-11.3832 ; -0.1700) | -2.1341 (-4.4873 ; -0.0601) | 0.0269 (0.0030 ; 0.0598) | 0.1772 (-0.0036 ; 0.4181) |
| -15.000 | -6.4991 (-13.5777 ; 0.0309) | -2.1343 (-4.6477 ; 0.0051) | -4.9668 (-10.8139 ; 0.0122) | -1.9834 (-4.2690 ; 0.0103) | 0.0318 (0.0050 ; 0.0672) | 0.1488 (-0.0158 ; 0.3750) |
| -15.250 | -6.1403 (-13.0410 ; 0.1995) | -1.9771 (-4.4054 ; 0.0705) | -4.6015 (-10.2509 ; 0.1642) | -1.8425 (-4.0528 ; 0.0692) | 0.0358 (0.0066 ; 0.0738) | 0.1227 (-0.0255 ; 0.3328) |
| -15.500 | -5.8025 (-12.5094 ; 0.3402) | -1.8305 (-4.1669 ; 0.1240) | -4.2607 (-9.6967 ; 0.2886) | -1.7107 (-3.8397 ; 0.1175) | 0.0392 (0.0077 ; 0.0794) | 0.0989 (-0.0328 ; 0.2916) |
| -15.750 | -5.4848 (-11.9859 ; 0.4545) | -1.6940 (-3.9330 ; 0.1666) | -3.9436 (-9.1533 ; 0.3877) | -1.5878 (-3.6305 ; 0.1559) | 0.0420 (0.0086 ; 0.0843) | 0.0772 (-0.0381 ; 0.2517) |
| -16.000 | -5.1862 (-11.4735 ; 0.5437) | -1.5672 (-3.7047 ; 0.1992) | -3.6490 (-8.6227 ; 0.4634) | -1.4734 (-3.4260 ; 0.1853) | 0.0442 (0.0091 ; 0.0884) | 0.0575 (-0.0416 ; 0.2129) |
| -16.250 | -4.9057 (-10.9747 ; 0.6087) | -1.4497 (-3.4826 ; 0.2223) | -3.3758 (-8.1068 ; 0.5172) | -1.3670 (-3.2270 ; 0.2062) | 0.0458 (0.0094 ; 0.0918) | 0.0396 (-0.0434 ; 0.1755) |
| -16.500 | -4.6423 (-10.4920 ; 0.6502) | -1.3409 (-3.2675 ; 0.2367) | -3.1230 (-7.6070 ; 0.5507) | -1.2682 (-3.0341 ; 0.2190) | 0.0470 (0.0094 ; 0.0946) | 0.0235 (-0.0439 ; 0.1396) |
| -16.750 | -4.3950 (-10.0275 ; 0.6690) | -1.2404 (-3.0600 ; 0.2430) | -2.8894 (-7.1249 ; 0.5653) | -1.1765 (-2.8479 ; 0.2244) | 0.0477 (0.0092 ; 0.0969) | 0.0091 (-0.0437 ; 0.1052) |
| -17.000 | -4.1630 (-9.5830 ; 0.6661) | -1.1477 (-2.8607 ; 0.2419) | -2.6741 (-6.6620 ; 0.5628) | -1.0916 (-2.6690 ; 0.2230) | 0.0481 (0.0087 ; 0.0988) | -0.0039 (-0.0440 ; 0.0725) |
| -17.250 | -3.9453 (-9.1596 ; 0.6430) | -1.0625 (-2.6704 ; 0.2344) | -2.4759 (-6.2199 ; 0.5453) | -1.0132 (-2.4981 ; 0.2155) | 0.0481 (0.0081 ; 0.1001) | -0.0154 (-0.0446 ; 0.0417) |
| -17.500 | -3.7411 (-8.7578 ; 0.6017) | -0.9841 (-2.4897 ; 0.2214) | -2.2938 (-5.7999 ; 0.5150) | -0.9407 (-2.3355 ; 0.2029) | 0.0478 (0.0075 ; 0.1009) | -0.0256 (-0.0458 ; 0.0128) |
| -17.750 | -3.5500 (-8.3783 ; 0.5451) | -0.9122 (-2.3187 ; 0.2041) | -2.1268 (-5.4027 ; 0.4748) | -0.8738 (-2.1815 ; 0.1863) | 0.0472 (0.0070 ; 0.1011) | -0.0346 (-0.0477 ; -0.0140) |
| -18.000 | -3.3685 (-8.0140 ; 0.4747) | -0.8462 (-2.1576 ; 0.1826) | -1.9733 (-5.0286 ; 0.4247) | -0.8119 (-2.0359 ; 0.1657) | 0.0464 (0.0065 ; 0.1007) | -0.0426 (-0.0503 ; -0.0295) |
| -18.250 | -3.2002 (-7.6696 ; 0.4049) | -0.7863 (-2.0064 ; 0.1611) | -1.8341 (-4.6773 ; 0.3747) | -0.7553 (-1.8988 ; 0.1452) | 0.0454 (0.0062 ; 0.0998) | -0.0494 (-0.0617 ; -0.0263) |
| -18.500 | -3.0469 (-7.3494 ; 0.3464) | -0.7318 (-1.8649 ; 0.1427) | -1.7074 (-4.3485 ; 0.3320) | -0.7036 (-1.7703 ; 0.1278) | 0.0443 (0.0059 ; 0.0984) | -0.0554 (-0.0826 ; -0.0232) |
| -18.750 | -2.9056 (-7.0454 ; 0.2978) | -0.6823 (-1.7328 ; 0.1267) | -1.5924 (-4.0414 ; 0.2947) | -0.6565 (-1.6498 ; 0.1127) | 0.0430 (0.0056 ; 0.0965) | -0.0605 (-0.1017 ; -0.0203) |
| -19.000 | -2.7763 (-6.7566 ; 0.2585) | -0.6375 (-1.6093 ; 0.1129) | -1.4882 (-3.7546 ; 0.2626) | -0.6135 (-1.5367 ; 0.0998) | 0.0416 (0.0054 ; 0.0942) | -0.0649 (-0.1191 ; -0.0175) |
| -19.250 | -2.6582 (-6.4810 ; 0.2272) | -0.5971 (-1.4938 ; 0.1008) | -1.3943 (-3.4864 ; 0.2344) | -0.5745 (-1.4303 ; 0.0887) | 0.0402 (0.0050 ; 0.0918) | -0.0687 (-0.1350 ; -0.0148) |
| -19.500 | -2.5508 (-6.2178 ; 0.2022) | -0.5607 (-1.3860 ; 0.0899) | -1.3098 (-3.2359 ; 0.2091) | -0.5392 (-1.3303 ; 0.0788) | 0.0387 (0.0046 ; 0.0893) | -0.0718 (-0.1493 ; -0.0122) |
| -19.750 | -2.4535 (-5.9665 ; 0.1825) | -0.5281 (-1.2857 ; 0.0801) | -1.2340 (-3.0029 ; 0.1864) | -0.5073 (-1.2367 ; 0.0701) | 0.0372 (0.0041 ; 0.0868) | -0.0743 (-0.1621 ; -0.0098) |
| -20.000 | -2.3658 (-5.7277 ; 0.1669) | -0.4990 (-1.1930 ; 0.0713) | -1.1663 (-2.7874 ; 0.1659) | -0.4785 (-1.1494 ; 0.0624) | 0.0356 (0.0035 ; 0.0843) | -0.0763 (-0.1733 ; -0.0076) |
| -20.250 | -2.2870 (-5.5019 ; 0.1548) | -0.4731 (-1.1077 ; 0.0635) | -1.1061 (-2.5893 ; 0.1477) | -0.4528 (-1.0686 ; 0.0556) | 0.0340 (0.0029 ; 0.0817) | -0.0779 (-0.1830 ; -0.0056) |
| -20.500 | -2.2166 (-5.2898 ; 0.1452) | -0.4501 (-1.0300 ; 0.0566) | -1.0527 (-2.4087 ; 0.1317) | -0.4297 (-0.9942 ; 0.0497) | 0.0324 (0.0023 ; 0.0791) | -0.0791 (-0.1912 ; -0.0039) |
| -20.750 | -2.1540 (-5.0919 ; 0.1377) | -0.4298 (-0.9596 ; 0.0505) | -1.0056 (-2.2452 ; 0.1176) | -0.4092 (-0.9263 ; 0.0446) | 0.0308 (0.0017 ; 0.0765) | -0.0800 (-0.1980 ; -0.0024) |
| -21.000 | -2.0986 (-4.9085 ; 0.1317) | -0.4121 (-0.8964 ; 0.0452) | -0.9643 (-2.0984 ; 0.1054) | -0.3909 (-0.8647 ; 0.0401) | 0.0293 (0.0012 ; 0.0737) | -0.0805 (-0.2035 ; -0.0012) |
| -21.250 | -2.0499 (-4.7397 ; 0.1269) | -0.3965 (-0.8401 ; 0.0407) | -0.9282 (-1.9676 ; 0.0948) | -0.3748 (-0.8093 ; 0.0363) | 0.0278 (0.0007 ; 0.0709) | -0.0807 (-0.2078 ; -0.0001) |
| -21.500 | -2.0074 (-4.5856 ; 0.1229) | -0.3830 (-0.7904 ; 0.0368) | -0.8969 (-1.8521 ; 0.0858) | -0.3606 (-0.7597 ; 0.0330) | 0.0263 (0.0004 ; 0.0681) | -0.0807 (-0.2109 ; 0.0007) |
| -21.750 | -1.9705 (-4.4457 ; 0.1197) | -0.3714 (-0.7469 ; 0.0335) | -0.8698 (-1.7509 ; 0.0781) | -0.3481 (-0.7157 ; 0.0302) | 0.0248 (0.0001 ; 0.0652) | -0.0806 (-0.2130 ; 0.0014) |
| -22.000 | -1.9388 (-4.3197 ; 0.1169) | -0.3614 (-0.7090 ; 0.0307) | -0.8466 (-1.6630 ; 0.0716) | -0.3373 (-0.6770 ; 0.0278) | 0.0234 (-0.0002 ; 0.0623) | -0.0802 (-0.2143 ; 0.0019) |
| -22.250 | -1.9117 (-4.2068 ; 0.1146) | -0.3529 (-0.6765 ; 0.0283) | -0.8269 (-1.5874 ; 0.0661) | -0.3279 (-0.6432 ; 0.0258) | 0.0221 (-0.0004 ; 0.0594) | -0.0797 (-0.2148 ; 0.0023) |
| -22.500 | -1.8888 (-4.1063 ; 0.1127) | -0.3457 (-0.6487 ; 0.0263) | -0.8102 (-1.5229 ; 0.0616) | -0.3197 (-0.6138 ; 0.0241) | 0.0209 (-0.0005 ; 0.0566) | -0.0791 (-0.2147 ; 0.0027) |
| -22.750 | -1.8696 (-4.0173 ; 0.1111) | -0.3397 (-0.6253 ; 0.0247) | -0.7962 (-1.4684 ; 0.0578) | -0.3127 (-0.5886 ; 0.0227) | 0.0197 (-0.0006 ; 0.0539) | -0.0785 (-0.2141 ; 0.0029) |
| -23.000 | -1.8538 (-3.9391 ; 0.1099) | -0.3347 (-0.6057 ; 0.0234) | -0.7845 (-1.4229 ; 0.0546) | -0.3068 (-0.5670 ; 0.0215) | 0.0185 (-0.0007 ; 0.0512) | -0.0778 (-0.2131 ; 0.0031) |
| -23.250 | -1.8408 (-3.8707 ; 0.1089) | -0.3306 (-0.5895 ; 0.0223) | -0.7750 (-1.3852 ; 0.0520) | -0.3018 (-0.5487 ; 0.0205) | 0.0175 (-0.0008 ; 0.0487) | -0.0770 (-0.2118 ; 0.0032) |
| -23.500 | -1.8304 (-3.8112 ; 0.1083) | -0.3272 (-0.5762 ; 0.0214) | -0.7672 (-1.3544 ; 0.0500) | -0.2975 (-0.5333 ; 0.0196) | 0.0165 (-0.0008 ; 0.0464) | -0.0763 (-0.2102 ; 0.0032) |
| -23.750 | -1.8222 (-3.7598 ; 0.1079) | -0.3245 (-0.5655 ; 0.0206) | -0.7609 (-1.3294 ; 0.0483) | -0.2940 (-0.5205 ; 0.0190) | 0.0157 (-0.0008 ; 0.0442) | -0.0756 (-0.2086 ; 0.0032) |
| -24.000 | -1.8158 (-3.7157 ; 0.1079) | -0.3224 (-0.5569 ; 0.0201) | -0.7559 (-1.3095 ; 0.0470) | -0.2910 (-0.5100 ; 0.0184) | 0.0149 (-0.0008 ; 0.0421) | -0.0749 (-0.2069 ; 0.0033) |
| -24.250 | -1.8109 (-3.6782 ; 0.1080) | -0.3207 (-0.5502 ; 0.0196) | -0.7521 (-1.2938 ; 0.0460) | -0.2887 (-0.5013 ; 0.0180) | 0.0142 (-0.0008 ; 0.0403) | -0.0742 (-0.2053 ; 0.0032) |
| -24.500 | -1.8073 (-3.6468 ; 0.1084) | -0.3194 (-0.5449 ; 0.0193) | -0.7490 (-1.2816 ; 0.0452) | -0.2867 (-0.4944 ; 0.0176) | 0.0135 (-0.0008 ; 0.0387) | -0.0736 (-0.2038 ; 0.0032) |
| -24.750 | -1.8048 (-3.6209 ; 0.1088) | -0.3185 (-0.5409 ; 0.0190) | -0.7468 (-1.2723 ; 0.0446) | -0.2852 (-0.4889 ; 0.0173) | 0.0130 (-0.0008 ; 0.0373) | -0.0731 (-0.2024 ; 0.0032) |
| -25.000 | -1.8030 (-3.6003 ; 0.1091) | -0.3177 (-0.5379 ; 0.0188) | -0.7451 (-1.2654 ; 0.0441) | -0.2840 (-0.4847 ; 0.0171) | 0.0126 (-0.0008 ; 0.0362) | -0.0726 (-0.2012 ; 0.0031) |
| -25.250 | -1.8019 (-3.5844 ; 0.1092) | -0.3172 (-0.5358 ; 0.0186) | -0.7439 (-1.2604 ; 0.0436) | -0.2831 (-0.4816 ; 0.0169) | 0.0122 (-0.0008 ; 0.0353) | -0.0723 (-0.2002 ; 0.0031) |
| -25.500 | -1.8012 (-3.5737 ; 0.1094) | -0.3169 (-0.5343 ; 0.0185) | -0.7431 (-1.2571 ; 0.0433) | -0.2825 (-0.4794 ; 0.0168) | 0.0120 (-0.0007 ; 0.0347) | -0.0720 (-0.1995 ; 0.0031) |
| -25.750 | -1.8009 (-3.5659 ; 0.1082) | -0.3167 (-0.5335 ; 0.0182) | -0.7427 (-1.2551 ; 0.0425) | -0.2822 (-0.4782 ; 0.0164) | 0.0119 (-0.0007 ; 0.0342) | -0.0719 (-0.1989 ; 0.0030) |
| -26.000 | -1.8008 (-3.5659 ; 0.1081) | -0.3166 (-0.5331 ; 0.0182) | -0.7425 (-1.2543 ; 0.0425) | -0.2821 (-0.4777 ; 0.0164) | 0.0118 (-0.0007 ; 0.0342) | -0.0718 (-0.1991 ; 0.0030) |

### TUBE_01

| Cote (m) | G | EAU_P | EAU_A | Q1 | Q3 | A |
|---:|---:|---:|---:|---:|---:|---:|
| 2.600 | -16.7481 (-16.7481 ; -16.7481) | -8.4793 (-8.4793 ; -8.4793) | -19.8904 (-19.8904 ; -19.8904) | -9.9697 (-9.9697 ; -9.9697) | -4.3141 (-4.3141 ; -4.3141) | 3.2437 (3.2437 ; 3.2437) |
| 2.500 | -16.8127 (-17.3303 ; -13.5688) | -8.4933 (-8.7611 ; -6.8244) | -19.9180 (-20.5469 ; -16.0018) | -9.9274 (-10.2460 ; -7.9473) | -4.2168 (-4.3607 ; -3.3373) | 3.1926 (2.5382 ; 3.2968) |
| 2.250 | -17.5453 (-17.9566 ; -16.7603) | -8.8221 (-9.0363 ; -8.4184) | -20.6758 (-21.1786 ; -19.7303) | -10.1671 (-10.4208 ; -9.6871) | -4.1230 (-4.2357 ; -3.9162) | 3.1793 (3.0218 ; 3.2603) |
| 2.000 | -18.1250 (-18.3743 ; -17.5941) | -9.0725 (-9.2035 ; -8.7975) | -21.2495 (-21.5564 ; -20.6079) | -10.3136 (-10.4702 ; -9.9852) | -3.9901 (-4.0513 ; -3.8549) | 3.1356 (3.0314 ; 3.1802) |
| 1.750 | -18.7008 (-18.8907 ; -18.2863) | -9.3219 (-9.4219 ; -9.1039) | -21.8203 (-22.0533 ; -21.3152) | -10.4596 (-10.5821 ; -10.1991) | -3.8613 (-3.9016 ; -3.7599) | 3.0912 (3.0120 ; 3.1219) |
| 1.500 | -19.2698 (-19.4191 ; -18.9575) | -9.5684 (-9.6480 ; -9.3989) | -22.3841 (-22.5680 ; -21.9964) | -10.6033 (-10.7005 ; -10.4020) | -3.7357 (-3.7635 ; -3.6628) | 3.0463 (2.9885 ; 3.0678) |
| 1.250 | -19.8250 (-19.9438 ; -19.5658) | -9.8082 (-9.8729 ; -9.6609) | -22.9325 (-23.0798 ; -22.6008) | -10.7407 (-10.8182 ; -10.5690) | -3.6119 (-3.6329 ; -3.5532) | 2.9998 (2.9528 ; 3.0169) |
| 1.000 | -20.3680 (-20.4667 ; -20.1545) | -10.0420 (-10.0983 ; -9.9123) | -23.4671 (-23.5910 ; -23.1806) | -10.8731 (-10.9369 ; -10.7265) | -3.4908 (-3.5072 ; -3.4435) | 2.9523 (2.9141 ; 2.9659) |
| 0.750 | -20.8964 (-20.9835 ; -20.7190) | -10.2686 (-10.3219 ; -10.1510) | -23.9849 (-24.0970 ; -23.7303) | -10.9993 (-11.0543 ; -10.8719) | -3.3721 (-3.3848 ; -3.3331) | 2.9039 (2.8722 ; 2.9150) |
| 0.500 | -21.4090 (-21.4903 ; -21.2633) | -10.4870 (-10.5390 ; -10.3792) | -24.4843 (-24.5913 ; -24.2553) | -11.1187 (-11.1683 ; -11.0078) | -3.2559 (-3.2656 ; -3.2237) | 2.8545 (2.8282 ; 2.8638) |
| 0.250 | -21.9041 (-21.9839 ; -21.7877) | -10.6963 (-10.7480 ; -10.5969) | -24.9633 (-25.0691 ; -24.7561) | -11.2308 (-11.2773 ; -11.1345) | -3.1422 (-3.1494 ; -3.1158) | 2.8043 (2.7826 ; 2.8118) |
| 0.000 | -22.3806 (-22.4615 ; -22.2836) | -10.8958 (-10.9480 ; -10.8047) | -25.4202 (-25.5290 ; -25.2332) | -11.3349 (-11.3798 ; -11.2524) | -3.0310 (-3.0370 ; -3.0096) | 2.7533 (2.7356 ; 2.7593) |
| -0.250 | -22.8368 (-22.9213 ; -22.7187) | -11.0850 (-11.1381 ; -11.0017) | -25.8533 (-25.9673 ; -25.6855) | -11.4305 (-11.4751 ; -11.3613) | -2.9222 (-2.9280 ; -2.9053) | 2.7016 (2.6875 ; 2.7063) |
| -0.500 | -23.2717 (-23.3616 ; -23.1299) | -11.2630 (-11.3192 ; -11.1686) | -26.2608 (-26.3820 ; -26.0655) | -11.5172 (-11.5622 ; -11.4551) | -2.8157 (-2.8215 ; -2.8029) | 2.6491 (2.6384 ; 2.6528) |
| -0.750 | -23.6839 (-23.7810 ; -23.5158) | -11.4292 (-11.4889 ; -11.3235) | -26.6411 (-26.7711 ; -26.4167) | -11.5945 (-11.6408 ; -11.5242) | -2.7117 (-2.7174 ; -2.7026) | 2.5960 (2.5883 ; 2.5988) |
| -1.000 | -24.0721 (-24.1838 ; -23.8749) | -11.5831 (-11.6467 ; -11.4654) | -26.9930 (-27.1331 ; -26.7378) | -11.6619 (-11.7103 ; -11.5824) | -2.6100 (-2.6157 ; -2.6042) | 2.5423 (2.5374 ; 2.5445) |
| -1.250 | -24.4353 (-24.5641 ; -24.2056) | -11.7240 (-11.7920 ; -11.5937) | -27.3152 (-27.4666 ; -27.0272) | -11.7191 (-11.7703 ; -11.6291) | -2.5107 (-2.5161 ; -2.5077) | 2.4881 (2.4854 ; 2.4897) |
| -1.500 | -24.7723 (-24.9204 ; -24.5067) | -11.8515 (-11.9244 ; -11.7076) | -27.6063 (-27.7704 ; -27.2833) | -11.7657 (-11.8205 ; -11.6639) | -2.4136 (-2.4187 ; -2.4105) | 2.4333 (2.4298 ; 2.4346) |
| -1.750 | -25.0822 (-25.2543 ; -24.7767) | -11.9651 (-12.0433 ; -11.8065) | -27.8654 (-28.0433 ; -27.5048) | -11.8013 (-11.8635 ; -11.6863) | -2.3189 (-2.3235 ; -2.3154) | 2.3781 (2.3735 ; 2.3804) |
| -2.000 | -25.3639 (-25.5670 ; -25.0144) | -12.0643 (-12.1485 ; -11.8895) | -28.0914 (-28.2853 ; -27.6904) | -11.8257 (-11.8961 ; -11.6960) | -2.2264 (-2.2303 ; -2.2227) | 2.3225 (2.3166 ; 2.3269) |
| -2.250 | -25.6165 (-25.8538 ; -25.2185) | -12.1487 (-12.2433 ; -11.9562) | -28.2835 (-28.5019 ; -27.8386) | -11.8387 (-11.9182 ; -11.6925) | -2.1361 (-2.1417 ; -2.1322) | 2.2665 (2.2593 ; 2.2730) |
| -2.500 | -25.8396 (-26.1198 ; -25.3879) | -12.2181 (-12.3241 ; -12.0061) | -28.4407 (-28.6860 ; -27.9483) | -11.8400 (-11.9311 ; -11.6757) | -2.0481 (-2.0553 ; -2.0441) | 2.2103 (2.2015 ; 2.2188) |
| -2.750 | -26.0321 (-26.3614 ; -25.5215) | -12.2721 (-12.3905 ; -12.0386) | -28.5626 (-28.8369 ; -28.0185) | -11.8296 (-11.9357 ; -11.6451) | -1.9623 (-1.9708 ; -1.9582) | 2.1537 (2.1433 ; 2.1642) |
| -3.000 | -26.1935 (-26.5805 ; -25.6183) | -12.3105 (-12.4431 ; -12.0534) | -28.6483 (-28.9549 ; -28.0480) | -11.8072 (-11.9301 ; -11.6006) | -1.8786 (-1.8885 ; -1.8746) | 2.0970 (2.0847 ; 2.1095) |
| -3.250 | -26.3231 (-26.7736 ; -25.6772) | -12.3330 (-12.4852 ; -12.0501) | -28.6976 (-29.0494 ; -28.0360) | -11.7728 (-11.9169 ; -11.5420) | -1.7971 (-1.8082 ; -1.7931) | 2.0401 (2.0258 ; 2.0547) |
| -3.500 | -26.4204 (-26.9395 ; -25.6974) | -12.3396 (-12.5128 ; -12.0283) | -28.7100 (-29.1105 ; -27.9817) | -11.7261 (-11.8957 ; -11.4689) | -1.7177 (-1.7299 ; -1.7138) | 1.9831 (1.9667 ; 1.9998) |
| -3.750 | -26.4849 (-27.0780 ; -25.6780) | -12.3301 (-12.5296 ; -11.9879) | -28.6851 (-29.1450 ; -27.8845) | -11.6673 (-11.8652 ; -11.3814) | -1.6405 (-1.6538 ; -1.6364) | 1.9260 (1.9074 ; 1.9449) |
| -4.000 | -26.5164 (-27.1891 ; -25.6184) | -12.3044 (-12.5343 ; -11.9286) | -28.6230 (-29.1521 ; -27.7438) | -11.5963 (-11.8245 ; -11.2792) | -1.5653 (-1.5796 ; -1.5597) | 1.8689 (1.8480 ; 1.8901) |
| -4.250 | -26.5144 (-27.2728 ; -25.5178) | -12.2626 (-12.5279 ; -11.8503) | -28.5235 (-29.1345 ; -27.5593) | -11.5131 (-11.7737 ; -11.1623) | -1.4922 (-1.5076 ; -1.4852) | 1.8118 (1.7885 ; 1.8355) |
| -4.500 | -26.4788 (-27.3289 ; -25.3757) | -12.2046 (-12.5080 ; -11.7528) | -28.3867 (-29.0863 ; -27.3306) | -11.4177 (-11.7128 ; -11.0306) | -1.4211 (-1.4376 ; -1.4126) | 1.7549 (1.7289 ; 1.7810) |
| -4.750 | -26.4095 (-27.3577 ; -25.1916) | -12.1305 (-12.4743 ; -11.6361) | -28.2126 (-29.0063 ; -27.0576) | -11.3103 (-11.6421 ; -10.8841) | -1.3520 (-1.3696 ; -1.3420) | 1.6980 (1.6693 ; 1.7267) |
| -5.000 | -26.3064 (-27.3593 ; -24.9651) | -12.0405 (-12.4271 ; -11.5002) | -28.0017 (-28.8950 ; -26.7402) | -11.1910 (-11.5616 ; -10.7229) | -1.2850 (-1.3036 ; -1.2735) | 1.6413 (1.6097 ; 1.6728) |
| -5.250 | -26.1695 (-27.3338 ; -24.6959) | -11.9347 (-12.3664 ; -11.3451) | -27.7543 (-28.7528 ; -26.3785) | -11.0598 (-11.4716 ; -10.5468) | -1.2199 (-1.2396 ; -1.2068) | 1.5849 (1.5503 ; 1.6192) |
| -5.500 | -25.9991 (-27.2815 ; -24.3838) | -11.8133 (-12.2926 ; -11.1710) | -27.4708 (-28.5803 ; -25.9727) | -10.9170 (-11.3723 ; -10.3560) | -1.1567 (-1.1776 ; -1.1421) | 1.5287 (1.4909 ; 1.5660) |
| -5.750 | -25.7954 (-27.2029 ; -24.0286) | -11.6767 (-12.2060 ; -10.9780) | -27.1519 (-28.3782 ; -25.5231) | -10.7629 (-11.2638 ; -10.1506) | -1.0955 (-1.1175 ; -1.0794) | 1.4728 (1.4318 ; 1.5133) |
| -6.000 | -25.5586 (-27.0982 ; -23.6303) | -11.5249 (-12.1069 ; -10.7663) | -26.7981 (-28.1471 ; -25.0302) | -10.5975 (-11.1464 ; -9.9306) | -1.0362 (-1.0594 ; -1.0185) | 1.4173 (1.3728 ; 1.4610) |
| -6.250 | -25.2892 (-26.9680 ; -23.1891) | -11.3586 (-11.9957 ; -10.5362) | -26.4104 (-27.8881 ; -24.4947) | -10.4213 (-11.0203 ; -9.6962) | -0.9788 (-1.0031 ; -0.9595) | 1.3622 (1.3141 ; 1.4093) |
| -6.500 | -24.9877 (-26.8129 ; -22.7051) | -11.1779 (-11.8728 ; -10.2880) | -25.9897 (-27.6020 ; -23.9172) | -10.2345 (-10.8859 ; -9.4476) | -0.9233 (-0.9488 ; -0.9024) | 1.3076 (1.2558 ; 1.3581) |
| -6.750 | -24.6548 (-26.6336 ; -22.1789) | -10.9834 (-11.7387 ; -10.0221) | -25.5369 (-27.2899 ; -23.2987) | -10.0375 (-10.7433 ; -9.1849) | -0.8696 (-0.8963 ; -0.8472) | 1.2534 (1.1977 ; 1.3076) |
| -7.000 | -24.2911 (-26.4307 ; -21.6109) | -10.7756 (-11.5939 ; -9.7390) | -25.0531 (-26.9530 ; -22.6402) | -9.8307 (-10.5928 ; -8.9085) | -0.8177 (-0.8456 ; -0.7937) | 1.1999 (1.1401 ; 1.2578) |
| -7.250 | -23.8976 (-26.2051 ; -21.0020) | -10.5549 (-11.4389 ; -9.4393) | -24.5396 (-26.5926 ; -21.9432) | -9.6143 (-10.4349 ; -8.6187) | -0.7676 (-0.7968 ; -0.7420) | 1.1469 (1.0830 ; 1.2086) |
| -7.500 | -23.4751 (-25.9580 ; -20.3530) | -10.3219 (-11.2744 ; -9.1236) | -23.9977 (-26.2100 ; -21.2089) | -9.3890 (-10.2699 ; -8.3158) | -0.7193 (-0.7497 ; -0.6922) | 1.0946 (1.0263 ; 1.1603) |
| -7.750 | -23.0246 (-25.6902 ; -19.6652) | -10.0773 (-11.1009 ; -8.7925) | -23.4287 (-25.8067 ; -20.4391) | -9.1551 (-10.0983 ; -8.0006) | -0.6728 (-0.7044 ; -0.6440) | 1.0429 (0.9702 ; 1.1127) |
| -8.000 | -22.5474 (-25.4033 ; -18.9401) | -9.8218 (-10.9192 ; -8.4470) | -22.8344 (-25.3844 ; -19.6356) | -8.9131 (-9.9206 ; -7.6734) | -0.6280 (-0.6608 ; -0.5977) | 0.9920 (0.9148 ; 1.0660) |
| -8.250 | -22.0446 (-25.0984 ; -18.1794) | -9.5559 (-10.7301 ; -8.0879) | -22.2162 (-24.9448 ; -18.8007) | -8.6637 (-9.7375 ; -7.3353) | -0.5849 (-0.6189 ; -0.5530) | 0.9419 (0.8600 ; 1.0201) |
| -8.500 | -21.5177 (-24.7772 ; -17.3853) | -9.2805 (-10.5342 ; -7.7162) | -21.5759 (-24.4896 ; -17.9368) | -8.4074 (-9.5495 ; -6.9871) | -0.5435 (-0.5787 ; -0.5101) | 0.8926 (0.8060 ; 0.9752) |
| -8.750 | -20.9682 (-24.4413 ; -16.5604) | -8.9964 (-10.3325 ; -7.3333) | -20.9153 (-24.0209 ; -17.0464) | -8.1447 (-9.3575 ; -6.6298) | -0.5037 (-0.5401 ; -0.4688) | 0.8443 (0.7527 ; 0.9313) |
| -9.000 | -20.3976 (-24.0927 ; -15.7073) | -8.7044 (-10.1258 ; -6.9403) | -20.2364 (-23.5405 ; -16.1328) | -7.8765 (-9.1629 ; -6.2647) | -0.4656 (-0.5032 ; -0.4293) | 0.7968 (0.7004 ; 0.8883) |
| -9.250 | -19.8078 (-23.7332 ; -14.8296) | -8.4053 (-9.9150 ; -6.5387) | -19.5413 (-23.0505 ; -15.1992) | -7.6033 (-8.9659 ; -5.8930) | -0.4292 (-0.4678 ; -0.3914) | 0.7503 (0.6489 ; 0.8464) |
| -9.500 | -19.2003 (-23.3645 ; -13.9309) | -8.1002 (-9.7009 ; -6.1302) | -18.8319 (-22.5530 ; -14.2495) | -7.3255 (-8.7666 ; -5.5164) | -0.3943 (-0.4340 ; -0.3551) | 0.7048 (0.5986 ; 0.8055) |
| -9.750 | -18.5773 (-22.9886 ; -13.0156) | -7.7899 (-9.4843 ; -5.7165) | -18.1107 (-22.0499 ; -13.2878) | -7.0440 (-8.5667 ; -5.1365) | -0.3610 (-0.4017 ; -0.3205) | 0.6604 (0.5493 ; 0.7657) |
| -10.000 | -17.9408 (-22.6074 ; -12.0887) | -7.4755 (-9.2662 ; -5.2996) | -17.3798 (-21.5432 ; -12.3188) | -6.7596 (-8.3667 ; -4.7550) | -0.3293 (-0.3709 ; -0.2876) | 0.6171 (0.5013 ; 0.7270) |
| -10.250 | -17.2931 (-22.2223 ; -11.1557) | -7.1579 (-9.0472 ; -4.8819) | -16.6418 (-21.0343 ; -11.3478) | -6.4733 (-8.1673 ; -4.3742) | -0.2991 (-0.3415 ; -0.2563) | 0.5750 (0.4546 ; 0.6894) |
| -10.500 | -16.6363 (-21.8347 ; -10.2230) | -6.8384 (-8.8279 ; -4.4660) | -15.8992 (-20.5248 ; -10.3808) | -6.1857 (-7.9690 ; -3.9962) | -0.2704 (-0.3135 ; -0.2267) | 0.5341 (0.4094 ; 0.6530) |
| -10.750 | -15.9730 (-21.4451 ; -9.2983) | -6.5180 (-8.6087 ; -4.0547) | -15.1545 (-20.0155 ; -9.4247) | -5.8979 (-7.7720 ; -3.6237) | -0.2432 (-0.2869 ; -0.1987) | 0.4944 (0.3658 ; 0.6177) |
| -11.000 | -15.3057 (-21.0537 ; -8.3902) | -6.1978 (-8.3896 ; -3.6515) | -14.4104 (-19.5067 ; -8.4876) | -5.6108 (-7.5764 ; -3.2598) | -0.2174 (-0.2616 ; -0.1724) | 0.4560 (0.3239 ; 0.5834) |
| -11.250 | -14.6371 (-20.6598 ; -7.5088) | -5.8791 (-8.1707 ; -3.2605) | -13.6697 (-18.9981 ; -7.5786) | -5.3255 (-7.3817 ; -2.9078) | -0.1931 (-0.2375 ; -0.1478) | 0.4190 (0.2841 ; 0.5502) |
| -11.500 | -13.9699 (-20.2620 ; -6.6645) | -5.5631 (-7.9515 ; -2.8857) | -12.9352 (-18.4888 ; -6.7074) | -5.0428 (-7.1876 ; -2.5715) | -0.1703 (-0.2146 ; -0.1251) | 0.3833 (0.2464 ; 0.5179) |
| -11.750 | -13.3081 (-19.8586 ; -5.8722) | -5.2515 (-7.7314 ; -2.5332) | -12.2109 (-17.9775 ; -5.8880) | -4.7643 (-6.9933 ; -2.2562) | -0.1488 (-0.1928 ; -0.1042) | 0.3492 (0.2114 ; 0.4866) |
| -12.000 | -12.6469 (-19.4477 ; -5.1100) | -4.9423 (-7.5098 ; -2.1938) | -11.4923 (-17.4629 ; -5.0992) | -4.4881 (-6.7982 ; -1.9534) | -0.1287 (-0.1720 ; -0.0848) | 0.3163 (0.1782 ; 0.4561) |
| -12.250 | -12.0019 (-19.0273 ; -4.4066) | -4.6420 (-7.2862 ; -1.8813) | -10.7945 (-16.9435 ; -4.3729) | -4.2202 (-6.6016 ; -1.6749) | -0.1099 (-0.1523 ; -0.0676) | 0.2851 (0.1481 ; 0.4265) |
| -12.500 | -11.3842 (-18.5956 ; -3.7721) | -4.3552 (-7.0600 ; -1.6012) | -10.1281 (-16.4181 ; -3.7217) | -3.9643 (-6.4028 ; -1.4253) | -0.0927 (-0.1335 ; -0.0527) | 0.2559 (0.1217 ; 0.3975) |
| -12.750 | -10.7879 (-18.1510 ; -3.1813) | -4.0795 (-6.8308 ; -1.3427) | -9.4873 (-15.8855 ; -3.1209) | -3.7185 (-6.2012 ; -1.1949) | -0.0769 (-0.1156 ; -0.0397) | 0.2284 (0.0980 ; 0.3692) |
| -13.000 | -10.2154 (-17.6922 ; -2.6406) | -3.8157 (-6.5981 ; -1.1082) | -8.8743 (-15.3449 ; -2.5758) | -3.4833 (-5.9965 ; -0.9858) | -0.0623 (-0.0986 ; -0.0284) | 0.2027 (0.0771 ; 0.3415) |
| -13.250 | -9.6672 (-17.2184 ; -2.1504) | -3.5642 (-6.3617 ; -0.8976) | -8.2897 (-14.7959 ; -2.0862) | -3.2591 (-5.7883 ; -0.7978) | -0.0490 (-0.0823 ; -0.0189) | 0.1786 (0.0589 ; 0.3144) |
| -13.500 | -9.1437 (-16.7296 ; -1.7101) | -3.3250 (-6.1219 ; -0.7101) | -7.7338 (-14.2387 ; -1.6505) | -3.0458 (-5.5768 ; -0.6304) | -0.0369 (-0.0668 ; -0.0108) | 0.1563 (0.0432 ; 0.2879) |
| -13.750 | -8.6450 (-16.2268 ; -1.3178) | -3.0981 (-5.8789 ; -0.5448) | -7.2065 (-13.6743 ; -1.2662) | -2.8435 (-5.3622 ; -0.4826) | -0.0259 (-0.0520 ; -0.0042) | 0.1355 (0.0298 ; 0.2619) |
| -14.000 | -8.1709 (-15.7116 ; -0.9708) | -2.8835 (-5.6336 ; -0.4001) | -6.7077 (-13.1044 ; -0.9298) | -2.6520 (-5.1451 ; -0.3532) | -0.0160 (-0.0379 ; 0.0012) | 0.1162 (0.0184 ; 0.2365) |
| -14.250 | -7.7211 (-15.1862 ; -0.6656) | -2.6809 (-5.3868 ; -0.2743) | -6.2370 (-12.5310 ; -0.6375) | -2.4712 (-4.9264 ; -0.2406) | -0.0071 (-0.0245 ; 0.0055) | 0.0985 (0.0089 ; 0.2117) |
| -14.500 | -7.2952 (-14.6535 ; -0.3990) | -2.4902 (-5.1395 ; -0.1659) | -5.7939 (-11.9564 ; -0.3854) | -2.3009 (-4.7067 ; -0.1433) | 0.0009 (-0.0118 ; 0.0088) | 0.0821 (0.0011 ; 0.1876) |
| -14.750 | -6.8924 (-14.1162 ; -0.1678) | -2.3111 (-4.8928 ; -0.0732) | -5.3776 (-11.3832 ; -0.1700) | -2.1407 (-4.4873 ; -0.0601) | 0.0080 (0.0003 ; 0.0119) | 0.0671 (-0.0051 ; 0.1641) |
| -15.000 | -6.5122 (-13.5777 ; 0.0309) | -2.1432 (-4.6477 ; 0.0051) | -4.9875 (-10.8139 ; 0.0122) | -1.9904 (-4.2690 ; 0.0103) | 0.0143 (0.0117 ; 0.0165) | 0.0533 (-0.0101 ; 0.1413) |
| -15.250 | -6.1537 (-13.0410 ; 0.1995) | -1.9862 (-4.4054 ; 0.0705) | -4.6225 (-10.2509 ; 0.1642) | -1.8496 (-4.0528 ; 0.0692) | 0.0199 (0.0140 ; 0.0225) | 0.0408 (-0.0139 ; 0.1192) |
| -15.500 | -5.8159 (-12.5094 ; 0.3402) | -1.8396 (-4.1669 ; 0.1240) | -4.2819 (-9.6967 ; 0.2886) | -1.7179 (-3.8397 ; 0.1175) | 0.0247 (0.0145 ; 0.0327) | 0.0294 (-0.0166 ; 0.0980) |
| -15.750 | -5.4982 (-11.9859 ; 0.4545) | -1.7030 (-3.9330 ; 0.1666) | -3.9645 (-9.1533 ; 0.3877) | -1.5950 (-3.6305 ; 0.1559) | 0.0289 (0.0145 ; 0.0422) | 0.0190 (-0.0184 ; 0.0775) |
| -16.000 | -5.1995 (-11.4735 ; 0.5437) | -1.5761 (-3.7047 ; 0.1992) | -3.6695 (-8.6227 ; 0.4634) | -1.4804 (-3.4260 ; 0.1853) | 0.0325 (0.0141 ; 0.0511) | 0.0097 (-0.0193 ; 0.0580) |
| -16.250 | -4.9189 (-10.9747 ; 0.6087) | -1.4583 (-3.4826 ; 0.2223) | -3.3958 (-8.1068 ; 0.5172) | -1.3738 (-3.2270 ; 0.2062) | 0.0355 (0.0134 ; 0.0593) | 0.0013 (-0.0200 ; 0.0393) |
| -16.500 | -4.6555 (-10.4920 ; 0.6502) | -1.3492 (-3.2675 ; 0.2367) | -3.1423 (-7.6070 ; 0.5507) | -1.2748 (-3.0341 ; 0.2190) | 0.0381 (0.0125 ; 0.0668) | -0.0062 (-0.0209 ; 0.0217) |
| -16.750 | -4.4085 (-10.0275 ; 0.6690) | -1.2484 (-3.0600 ; 0.2430) | -2.9080 (-7.1249 ; 0.5653) | -1.1829 (-2.8479 ; 0.2244) | 0.0401 (0.0115 ; 0.0735) | -0.0128 (-0.0222 ; 0.0051) |
| -17.000 | -4.1770 (-9.5830 ; 0.6661) | -1.1554 (-2.8607 ; 0.2419) | -2.6920 (-6.6620 ; 0.5628) | -1.0979 (-2.6690 ; 0.2230) | 0.0418 (0.0104 ; 0.0795) | -0.0188 (-0.0241 ; -0.0104) |
| -17.250 | -3.9602 (-9.1596 ; 0.6430) | -1.0699 (-2.6704 ; 0.2344) | -2.4931 (-6.2199 ; 0.5453) | -1.0193 (-2.4981 ; 0.2155) | 0.0431 (0.0094 ; 0.0847) | -0.0239 (-0.0268 ; -0.0165) |
| -17.500 | -3.7571 (-8.7578 ; 0.6017) | -0.9913 (-2.4897 ; 0.2214) | -2.3104 (-5.7999 ; 0.5150) | -0.9467 (-2.3355 ; 0.2029) | 0.0440 (0.0083 ; 0.0892) | -0.0285 (-0.0380 ; -0.0151) |
| -17.750 | -3.5674 (-8.3783 ; 0.5451) | -0.9191 (-2.3187 ; 0.2041) | -2.1428 (-5.4027 ; 0.4748) | -0.8797 (-2.1815 ; 0.1863) | 0.0446 (0.0073 ; 0.0931) | -0.0324 (-0.0502 ; -0.0137) |
| -18.000 | -3.3876 (-8.0140 ; 0.4747) | -0.8530 (-2.1576 ; 0.1826) | -1.9890 (-5.0286 ; 0.4247) | -0.8177 (-2.0359 ; 0.1657) | 0.0449 (0.0063 ; 0.0964) | -0.0358 (-0.0614 ; -0.0121) |
| -18.250 | -3.2208 (-7.6696 ; 0.4049) | -0.7928 (-2.0064 ; 0.1611) | -1.8492 (-4.6773 ; 0.3747) | -0.7611 (-1.8988 ; 0.1452) | 0.0450 (0.0053 ; 0.0991) | -0.0387 (-0.0715 ; -0.0106) |
| -18.500 | -3.0685 (-7.3494 ; 0.3464) | -0.7379 (-1.8649 ; 0.1427) | -1.7217 (-4.3485 ; 0.3320) | -0.7092 (-1.7703 ; 0.1278) | 0.0448 (0.0043 ; 0.1014) | -0.0411 (-0.0807 ; -0.0091) |
| -18.750 | -2.9279 (-7.0454 ; 0.2978) | -0.6880 (-1.7328 ; 0.1267) | -1.6057 (-4.0414 ; 0.2947) | -0.6618 (-1.6498 ; 0.1127) | 0.0445 (0.0033 ; 0.1031) | -0.0431 (-0.0890 ; -0.0076) |
| -19.000 | -2.7988 (-6.7566 ; 0.2585) | -0.6428 (-1.6093 ; 0.1129) | -1.5005 (-3.7546 ; 0.2626) | -0.6185 (-1.5367 ; 0.0998) | 0.0440 (0.0024 ; 0.1044) | -0.0447 (-0.0964 ; -0.0062) |
| -19.250 | -2.6805 (-6.4810 ; 0.2272) | -0.6018 (-1.4938 ; 0.1008) | -1.4053 (-3.4864 ; 0.2344) | -0.5791 (-1.4303 ; 0.0887) | 0.0433 (0.0015 ; 0.1051) | -0.0460 (-0.1028 ; -0.0049) |
| -19.500 | -2.5726 (-6.2178 ; 0.2022) | -0.5649 (-1.3860 ; 0.0899) | -1.3195 (-3.2359 ; 0.2091) | -0.5433 (-1.3303 ; 0.0788) | 0.0425 (0.0007 ; 0.1053) | -0.0470 (-0.1084 ; -0.0037) |
| -19.750 | -2.4744 (-5.9665 ; 0.1825) | -0.5317 (-1.2857 ; 0.0801) | -1.2423 (-3.0029 ; 0.1864) | -0.5109 (-1.2367 ; 0.0701) | 0.0416 (0.0001 ; 0.1049) | -0.0477 (-0.1130 ; -0.0026) |
| -20.000 | -2.3855 (-5.7277 ; 0.1669) | -0.5019 (-1.1930 ; 0.0713) | -1.1732 (-2.7874 ; 0.1659) | -0.4816 (-1.1494 ; 0.0624) | 0.0406 (-0.0004 ; 0.1040) | -0.0482 (-0.1168 ; -0.0017) |
| -20.250 | -2.3054 (-5.5019 ; 0.1548) | -0.4754 (-1.1077 ; 0.0635) | -1.1115 (-2.5893 ; 0.1477) | -0.4553 (-1.0686 ; 0.0556) | 0.0396 (-0.0007 ; 0.1026) | -0.0484 (-0.1197 ; -0.0010) |
| -20.500 | -2.2335 (-5.2898 ; 0.1452) | -0.4518 (-1.0300 ; 0.0566) | -1.0568 (-2.4087 ; 0.1317) | -0.4317 (-0.9942 ; 0.0497) | 0.0385 (-0.0010 ; 0.1008) | -0.0485 (-0.1219 ; -0.0004) |
| -20.750 | -2.1694 (-5.0919 ; 0.1377) | -0.4310 (-0.9596 ; 0.0505) | -1.0084 (-2.2452 ; 0.1176) | -0.4107 (-0.9263 ; 0.0446) | 0.0373 (-0.0012 ; 0.0987) | -0.0483 (-0.1233 ; 0.0001) |
| -21.000 | -2.1124 (-4.9085 ; 0.1317) | -0.4127 (-0.8964 ; 0.0452) | -0.9658 (-2.0984 ; 0.1054) | -0.3919 (-0.8647 ; 0.0401) | 0.0361 (-0.0013 ; 0.0962) | -0.0481 (-0.1242 ; 0.0005) |
| -21.250 | -2.0622 (-4.7397 ; 0.1269) | -0.3967 (-0.8401 ; 0.0407) | -0.9286 (-1.9676 ; 0.0948) | -0.3753 (-0.8093 ; 0.0363) | 0.0349 (-0.0014 ; 0.0936) | -0.0477 (-0.1244 ; 0.0009) |
| -21.500 | -2.0181 (-4.5856 ; 0.1229) | -0.3827 (-0.7904 ; 0.0368) | -0.8962 (-1.8521 ; 0.0858) | -0.3607 (-0.7597 ; 0.0330) | 0.0336 (-0.0014 ; 0.0908) | -0.0472 (-0.1242 ; 0.0011) |
| -21.750 | -1.9797 (-4.4457 ; 0.1197) | -0.3707 (-0.7469 ; 0.0335) | -0.8682 (-1.7509 ; 0.0781) | -0.3479 (-0.7157 ; 0.0302) | 0.0324 (-0.0014 ; 0.0878) | -0.0466 (-0.1235 ; 0.0013) |
| -22.000 | -1.9465 (-4.3197 ; 0.1169) | -0.3604 (-0.7090 ; 0.0307) | -0.8442 (-1.6630 ; 0.0716) | -0.3367 (-0.6770 ; 0.0278) | 0.0312 (-0.0014 ; 0.0849) | -0.0460 (-0.1225 ; 0.0015) |
| -22.250 | -1.9181 (-4.2068 ; 0.1146) | -0.3515 (-0.6765 ; 0.0283) | -0.8237 (-1.5874 ; 0.0661) | -0.3269 (-0.6432 ; 0.0258) | 0.0301 (-0.0014 ; 0.0819) | -0.0453 (-0.1213 ; 0.0016) |
| -22.500 | -1.8939 (-4.1063 ; 0.1127) | -0.3441 (-0.6487 ; 0.0263) | -0.8064 (-1.5229 ; 0.0616) | -0.3185 (-0.6138 ; 0.0241) | 0.0289 (-0.0013 ; 0.0789) | -0.0446 (-0.1198 ; 0.0016) |
| -22.750 | -1.8736 (-4.0173 ; 0.1111) | -0.3378 (-0.6253 ; 0.0247) | -0.7918 (-1.4684 ; 0.0578) | -0.3113 (-0.5886 ; 0.0227) | 0.0278 (-0.0013 ; 0.0760) | -0.0438 (-0.1182 ; 0.0017) |
| -23.000 | -1.8567 (-3.9391 ; 0.1099) | -0.3326 (-0.6057 ; 0.0234) | -0.7798 (-1.4229 ; 0.0546) | -0.3052 (-0.5670 ; 0.0215) | 0.0268 (-0.0012 ; 0.0731) | -0.0431 (-0.1164 ; 0.0017) |
| -23.250 | -1.8427 (-3.8707 ; 0.1089) | -0.3284 (-0.5895 ; 0.0223) | -0.7698 (-1.3852 ; 0.0520) | -0.3000 (-0.5487 ; 0.0205) | 0.0258 (-0.0012 ; 0.0704) | -0.0424 (-0.1147 ; 0.0017) |
| -23.500 | -1.8314 (-3.8112 ; 0.1083) | -0.3249 (-0.5762 ; 0.0214) | -0.7617 (-1.3544 ; 0.0500) | -0.2956 (-0.5333 ; 0.0196) | 0.0249 (-0.0011 ; 0.0679) | -0.0417 (-0.1129 ; 0.0017) |
| -23.750 | -1.8223 (-3.7598 ; 0.1079) | -0.3221 (-0.5655 ; 0.0206) | -0.7552 (-1.3294 ; 0.0483) | -0.2919 (-0.5205 ; 0.0190) | 0.0240 (-0.0010 ; 0.0655) | -0.0410 (-0.1112 ; 0.0016) |
| -24.000 | -1.8152 (-3.7157 ; 0.1079) | -0.3198 (-0.5569 ; 0.0201) | -0.7500 (-1.3095 ; 0.0470) | -0.2889 (-0.5100 ; 0.0184) | 0.0233 (-0.0010 ; 0.0634) | -0.0404 (-0.1095 ; 0.0016) |
| -24.250 | -1.8097 (-3.6782 ; 0.1080) | -0.3181 (-0.5502 ; 0.0196) | -0.7459 (-1.2938 ; 0.0460) | -0.2864 (-0.5013 ; 0.0180) | 0.0226 (-0.0009 ; 0.0614) | -0.0398 (-0.1080 ; 0.0016) |
| -24.500 | -1.8055 (-3.6468 ; 0.1084) | -0.3167 (-0.5449 ; 0.0193) | -0.7428 (-1.2816 ; 0.0452) | -0.2844 (-0.4944 ; 0.0176) | 0.0220 (-0.0009 ; 0.0597) | -0.0393 (-0.1066 ; 0.0016) |
| -24.750 | -1.8024 (-3.6209 ; 0.1088) | -0.3157 (-0.5409 ; 0.0190) | -0.7404 (-1.2723 ; 0.0446) | -0.2828 (-0.4889 ; 0.0173) | 0.0215 (-0.0008 ; 0.0582) | -0.0389 (-0.1054 ; 0.0015) |
| -25.000 | -1.8003 (-3.6003 ; 0.1091) | -0.3150 (-0.5379 ; 0.0188) | -0.7387 (-1.2654 ; 0.0441) | -0.2816 (-0.4847 ; 0.0171) | 0.0210 (-0.0008 ; 0.0570) | -0.0385 (-0.1044 ; 0.0015) |
| -25.250 | -1.7988 (-3.5844 ; 0.1092) | -0.3144 (-0.5358 ; 0.0186) | -0.7375 (-1.2604 ; 0.0436) | -0.2807 (-0.4816 ; 0.0169) | 0.0207 (-0.0008 ; 0.0561) | -0.0382 (-0.1036 ; 0.0015) |
| -25.500 | -1.7979 (-3.5737 ; 0.1094) | -0.3141 (-0.5343 ; 0.0185) | -0.7366 (-1.2571 ; 0.0433) | -0.2801 (-0.4794 ; 0.0168) | 0.0204 (-0.0007 ; 0.0554) | -0.0380 (-0.1031 ; 0.0014) |
| -25.750 | -1.7974 (-3.5659 ; 0.1082) | -0.3139 (-0.5335 ; 0.0182) | -0.7362 (-1.2551 ; 0.0425) | -0.2797 (-0.4782 ; 0.0164) | 0.0203 (-0.0007 ; 0.0549) | -0.0379 (-0.1026 ; 0.0014) |
| -26.000 | -1.7974 (-3.5659 ; 0.1081) | -0.3138 (-0.5331 ; 0.0182) | -0.7360 (-1.2543 ; 0.0425) | -0.2796 (-0.4777 ; 0.0164) | 0.0203 (-0.0007 ; 0.0549) | -0.0379 (-0.1027 ; 0.0014) |

## Efforts d'ensemble des tubes (le tube vu comme une poutre)

Intégrales, sur la circonférence, des efforts de coque `EFGE_ELNO` à chaque cote (`aster_expert.report.sections` ; convention de U2.01.05, lue le jour du lot 37) : `N = ∫ NXX ds` (traction positive), `M = ∫ NXX·y ds` (moment d'axe X du tube, `y` distance à l'axe ; > 0 : traction côté terre), `T = ∫ (NXY·y_l + QX·n)·Y ds` (effort tranchant selon Y, force exercée par la partie haute sur la partie basse ; la part de `NXY` et celle de `QX` sont données à part). Les efforts de flexion de paroi (`MXX`) ne sont pas dans `M`. Valeur d'une cote : moyenne des estimations par le haut et par le bas (les efforts par élément aux nœuds ne sont pas continus d'une rangée à l'autre). Le tube de bord (`TUBE_01`) est un **demi-tube** dans un plan de symétrie : ses efforts sont ceux du demi-tube. Cas élémentaires ; aucun verdict.

### TUBE_05

**G** — extrêmes : N (plus grande valeur absolue) = -726.782 kN à -13.25 m ; M = -1688.278 kN·m à -4.75 m ; T = -580.793 kN à -11.75 m (tête du tube : 2.6 m).

**EAU_P** — extrêmes : N (plus grande valeur absolue) = -201.291 kN à -13 m ; M = -805.600 kN·m à -4 m ; T = -247.513 kN à -11.75 m (tête du tube : 2.6 m).

**EAU_A** — extrêmes : N (plus grande valeur absolue) = -469.279 kN à -13 m ; M = -1861.961 kN·m à -4 m ; T = -574.953 kN à -11.75 m (tête du tube : 2.6 m).

**Q1** — extrêmes : N (plus grande valeur absolue) = -199.378 kN à -13 m ; M = -609.469 kN·m à -3.75 m ; T = -209.846 kN à -11.75 m (tête du tube : 2.6 m).

**Q3** — extrêmes : N (plus grande valeur absolue) = 196.959 kN à 2.5 m ; M = 243.245 kN·m à 2.5 m ; T = -107.835 kN à 2.6 m (tête du tube : 2.6 m).

**A** — extrêmes : N (plus grande valeur absolue) = -154.690 kN à 0.5 m ; M = -508.771 kN·m à 2.6 m ; T = -770.234 kN à 2.25 m (tête du tube : 2.6 m).

| Cote (m) | Cas | N (kN) | M (kN·m) | T (kN) | dont NXY | dont QX |
|---:|---|---:|---:|---:|---:|---:|
| 2.60 | G | -462.264 | -254.954 | -90.862 | 31.548 | -122.410 |
| 2.60 | EAU_P | -125.673 | -95.497 | -36.905 | 25.523 | -62.428 |
| 2.60 | EAU_A | -293.989 | -223.160 | -89.218 | 57.109 | -146.326 |
| 2.60 | Q1 | -147.165 | -75.786 | -78.676 | -5.438 | -73.237 |
| 2.60 | Q3 | 71.375 | 159.573 | -107.835 | -74.820 | -33.015 |
| 2.60 | A | 131.658 | -508.771 | -652.429 | -661.342 | 8.913 |
| 0.00 | G | -278.104 | -1000.146 | 276.718 | 276.710 | 0.008 |
| 0.00 | EAU_P | -43.837 | -508.717 | 146.905 | 146.900 | 0.004 |
| 0.00 | EAU_A | -103.101 | -1165.778 | 340.331 | 340.321 | 0.010 |
| 0.00 | Q1 | -56.402 | -406.368 | 110.646 | 110.642 | 0.003 |
| 0.00 | Q3 | 88.912 | 158.565 | 7.740 | 7.740 | 0.000 |
| 0.00 | A | -149.405 | 235.998 | 34.552 | 34.580 | -0.028 |
| -11.75 | G | -601.429 | 393.063 | -580.793 | -580.775 | -0.018 |
| -11.75 | EAU_P | -159.373 | 267.249 | -247.513 | -247.504 | -0.008 |
| -11.75 | EAU_A | -371.777 | 621.570 | -574.953 | -574.934 | -0.019 |
| -11.75 | Q1 | -160.693 | 253.120 | -209.846 | -209.839 | -0.007 |
| -11.75 | Q3 | 75.755 | 75.225 | 7.116 | 7.116 | 0.000 |
| -11.75 | A | 56.734 | -123.819 | 26.974 | 26.973 | 0.001 |
| -12.00 | G | -651.093 | 545.758 | -565.873 | -565.651 | -0.222 |
| -12.00 | EAU_P | -178.065 | 331.926 | -238.608 | -238.518 | -0.091 |
| -12.00 | EAU_A | -415.241 | 771.822 | -554.310 | -554.099 | -0.211 |
| -12.00 | Q1 | -177.719 | 308.211 | -202.929 | -202.848 | -0.082 |
| -12.00 | Q3 | 75.491 | 73.513 | 7.485 | 7.487 | -0.002 |
| -12.00 | A | 59.228 | -130.927 | 24.588 | 24.573 | 0.015 |
| -18.00 | G | -485.536 | 669.880 | 86.704 | 86.767 | -0.063 |
| -18.00 | EAU_P | -70.874 | 309.764 | 72.746 | 72.747 | -0.000 |
| -18.00 | EAU_A | -166.404 | 719.832 | 169.014 | 169.015 | -0.001 |
| -18.00 | Q1 | -85.064 | 272.366 | 59.938 | 59.942 | -0.004 |
| -18.00 | Q3 | 94.835 | 12.304 | 6.877 | 6.876 | 0.001 |
| -18.00 | A | 35.085 | -56.840 | -18.210 | -18.208 | -0.002 |
| -26.00 | G | -535.864 | 40.912 | -0.878 | -0.878 | 0.001 |
| -26.00 | EAU_P | -74.838 | 15.017 | -0.560 | -0.561 | 0.001 |
| -26.00 | EAU_A | -175.635 | 34.877 | -1.302 | -1.304 | 0.002 |
| -26.00 | Q1 | -88.831 | 19.659 | -1.104 | -1.106 | 0.002 |
| -26.00 | Q3 | 96.161 | -4.781 | 0.488 | 0.489 | -0.001 |
| -26.00 | A | 36.419 | 3.613 | -0.536 | -0.537 | 0.001 |

### TUBE_01 (demi-tube, plan de symétrie)

**G** — extrêmes : N (plus grande valeur absolue) = -363.391 kN à -13.25 m ; M = -844.139 kN·m à -4.75 m ; T = -290.397 kN à -11.75 m (tête du tube : 2.6 m).

**EAU_P** — extrêmes : N (plus grande valeur absolue) = -100.645 kN à -13 m ; M = -402.800 kN·m à -4 m ; T = -123.756 kN à -11.75 m (tête du tube : 2.6 m).

**EAU_A** — extrêmes : N (plus grande valeur absolue) = -234.640 kN à -13 m ; M = -930.981 kN·m à -4 m ; T = -287.477 kN à -11.75 m (tête du tube : 2.6 m).

**Q1** — extrêmes : N (plus grande valeur absolue) = -99.689 kN à -13 m ; M = -304.734 kN·m à -3.75 m ; T = -104.923 kN à -11.75 m (tête du tube : 2.6 m).

**Q3** — extrêmes : N (plus grande valeur absolue) = -37.788 kN à 2.25 m ; M = 100.919 kN·m à 2.5 m ; T = -50.219 kN à 2.6 m (tête du tube : 2.6 m).

**A** — extrêmes : N (plus grande valeur absolue) = 30.726 kN à 2.25 m ; M = 42.393 kN·m à 2.6 m ; T = 45.965 kN à 2.6 m (tête du tube : 2.6 m).

| Cote (m) | Cas | N (kN) | M (kN·m) | T (kN) | dont NXY | dont QX |
|---:|---|---:|---:|---:|---:|---:|
| 2.60 | G | -231.132 | -127.477 | -45.431 | 15.774 | -61.205 |
| 2.60 | EAU_P | -62.837 | -47.749 | -18.453 | 12.762 | -31.214 |
| 2.60 | EAU_A | -146.994 | -111.580 | -44.609 | 28.554 | -73.163 |
| 2.60 | Q1 | -73.582 | -37.893 | -39.338 | -2.719 | -36.619 |
| 2.60 | Q3 | -31.819 | 62.232 | -50.219 | -34.969 | -15.249 |
| 2.60 | A | 26.572 | 42.393 | 45.965 | 32.906 | 13.059 |
| 0.00 | G | -139.052 | -500.073 | 138.359 | 138.355 | 0.004 |
| 0.00 | EAU_P | -21.918 | -254.358 | 73.452 | 73.450 | 0.002 |
| 0.00 | EAU_A | -51.550 | -582.889 | 170.166 | 170.161 | 0.005 |
| 0.00 | Q1 | -28.201 | -203.184 | 55.323 | 55.321 | 0.002 |
| 0.00 | Q3 | -14.214 | 64.429 | 2.651 | 2.651 | 0.000 |
| 0.00 | A | 12.675 | 19.402 | 5.066 | 5.066 | 0.000 |
| -11.75 | G | -300.714 | 196.532 | -290.397 | -290.388 | -0.009 |
| -11.75 | EAU_P | -79.687 | 133.624 | -123.756 | -123.752 | -0.004 |
| -11.75 | EAU_A | -185.888 | 310.785 | -287.477 | -287.467 | -0.010 |
| -11.75 | Q1 | -80.347 | 126.560 | -104.923 | -104.919 | -0.004 |
| -11.75 | Q3 | -16.589 | 35.878 | 2.573 | 2.573 | -0.000 |
| -11.75 | A | 16.910 | -37.901 | 4.124 | 4.124 | 0.000 |
| -12.00 | G | -325.547 | 272.879 | -282.936 | -282.825 | -0.111 |
| -12.00 | EAU_P | -89.032 | 165.963 | -119.304 | -119.259 | -0.045 |
| -12.00 | EAU_A | -207.620 | 385.911 | -277.155 | -277.049 | -0.106 |
| -12.00 | Q1 | -88.859 | 154.105 | -101.465 | -101.424 | -0.041 |
| -12.00 | Q3 | -16.825 | 35.267 | 2.793 | 2.794 | -0.001 |
| -12.00 | A | 17.506 | -39.008 | 3.591 | 3.588 | 0.003 |
| -18.00 | G | -242.768 | 334.940 | 43.352 | 43.384 | -0.032 |
| -18.00 | EAU_P | -35.437 | 154.882 | 36.373 | 36.373 | -0.000 |
| -18.00 | EAU_A | -83.202 | 359.916 | 84.507 | 84.508 | -0.001 |
| -18.00 | Q1 | -42.532 | 136.183 | 29.969 | 29.971 | -0.002 |
| -18.00 | Q3 | -18.079 | 7.461 | 3.191 | 3.191 | 0.000 |
| -18.00 | A | 15.828 | -14.303 | -4.746 | -4.746 | -0.000 |
| -26.00 | G | -267.932 | 20.456 | -0.439 | -0.439 | 0.000 |
| -26.00 | EAU_P | -37.419 | 7.508 | -0.280 | -0.281 | 0.000 |
| -26.00 | EAU_A | -87.817 | 17.439 | -0.651 | -0.652 | 0.001 |
| -26.00 | Q1 | -44.415 | 9.829 | -0.552 | -0.553 | 0.001 |
| -26.00 | Q3 | -18.469 | -2.237 | 0.241 | 0.241 | -0.000 |
| -26.00 | A | 16.250 | 1.690 | -0.212 | -0.212 | 0.000 |

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

**Efforts d'ensemble N(z), M(z), T(z) des tubes**

![Efforts d'ensemble N(z), M(z), T(z) des tubes — cas G](vues/efforts_tube_G.png)

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

**Efforts d'ensemble N(z), M(z), T(z) des tubes**

![Efforts d'ensemble N(z), M(z), T(z) des tubes — cas EAU_P](vues/efforts_tube_EAU_P.png)

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

**Efforts d'ensemble N(z), M(z), T(z) des tubes**

![Efforts d'ensemble N(z), M(z), T(z) des tubes — cas EAU_A](vues/efforts_tube_EAU_A.png)

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

**Efforts d'ensemble N(z), M(z), T(z) des tubes**

![Efforts d'ensemble N(z), M(z), T(z) des tubes — cas Q1](vues/efforts_tube_Q1.png)

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

**Efforts d'ensemble N(z), M(z), T(z) des tubes**

![Efforts d'ensemble N(z), M(z), T(z) des tubes — cas Q3](vues/efforts_tube_Q3.png)

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

**Efforts d'ensemble N(z), M(z), T(z) des tubes**

![Efforts d'ensemble N(z), M(z), T(z) des tubes — cas A](vues/efforts_tube_A.png)

**Pression de réaction et butée limite**

![Pression de réaction et butée limite — cas A](vues/butee_A.png)

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

