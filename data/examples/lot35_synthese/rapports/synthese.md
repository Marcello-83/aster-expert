# Synthèse des résultats — QUAI-CW-TEST-01-LOT30-REDUIT

## Ce que ce document est, et n'est pas

- Des **résultats de cas élémentaires** (G, EAU_P, EAU_A, Q1, Q3, A), lus dans les tables imprimées par Code_Aster. Aucune combinaison n'est faite, aucun verdict de dimensionnement n'est porté : la fiche ne décide aucune combinaison.
- Niveau de validation du calcul : C (exécuté jusqu'à `FIN`) avec contrôles D (voir plus bas) ; jamais E.
- Les grandeurs sont **linéaires** (modèle élastique, ressorts sans plafond) : un dépassement de la butée est un constat sur les limites du modèle, non une rupture calculée.

## Provenance

- Listing : `data/processed/runs/20260925T072820-14e55343/proc.0/fort.6` (SHA-256 `7a9666a6476248fccd94ea8896882867651bd4bbf5ffe930548ee6ef6e54f2fa`)
- `.comm` : SHA-256 `b887afe83f5f2add9a41431f52fbd9cece8d9668a1aca7fa56b4f23b28974477`
- Données : `data/examples/lot30_quai_reduit/model_data_reduit.yaml`
- Le MED de résultats **n'est pas relu** : chaque grandeur vient d'une table imprimée du listing, traçable à une commande du `.comm`.

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

Tubes : axes à X = -2.6, 0, 2.6 m, rayon 0.71 m ; « porteur » d'un point = tube (cercle de rayon R) ou palplanche (plan Y = 0) le portant.

## Résultats par cas élémentaire

### Cas élémentaire G

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -13.0236 mm, z = 2.600 m, x = 0.701 m, y = 0.111 m ; TUBE_02 ; nœud 160. Étendue sur les 82 nœuds des anneaux de tête : de -13.0236 à -13.0198 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -2.600 | 268.400 | 268.400 | 268.400 |
| 2 | 0.000 | 325.332 | 325.332 | 325.332 |
| 3 | 2.600 | 268.400 | 268.400 | 268.400 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1524.502 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -1096.537 | z = -4.750 m, x = 0.000 m, y = 0.710 m ; TUBE_02 ; maille 13490 ; nœud 4042 |
| NYY | 5623.348 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -1100.628 | z = 2.250 m, x = -2.489 m, y = 0.701 m ; TUBE_01 ; maille 12368 ; nœud 2760 |
| MXX | 67.361 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -93.404 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |
| MYY | 69.246 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -28.021 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 257.316 | z = -13.000 m, x = -0.946 m, y = 0.000 m ; PALP_01_02 ; nœud 9669 | -183.505 | z = -5.250 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9801 |
| NYY | 0.103 | z = 2.600 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9540 | -1.423 | z = -13.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5099 |
| NXY | 266.896 | z = -11.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5106 | -266.896 | z = -11.250 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 3077 |
| MXX | 206.830 | z = -12.750 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9647 | -131.057 | z = -7.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 10052 |
| MYY | 3.184 | z = -5.750 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 8398 | -2.502 | z = -13.750 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 2961 |
| MXY | 0.172 | z = -10.750 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9677 | -0.172 | z = -10.750 m, x = 1.654 m, y = 0.000 m ; PALP_02_03 ; nœud 10142 |
| QX | 486.987 | z = 2.600 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 504 | -143.260 | z = -12.000 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9550 |
| QY | 15.287 | z = -13.500 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 2960 | -15.287 | z = -13.500 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5098 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| VY | 49.516 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 10066 ; nœud 9580 | -49.516 | z = 3.300 m, x = -1.950 m, y = 0.340 m ; maille 10053 ; nœud 9568 |
| VZ | 18.809 | z = 3.300 m, x = -1.625 m, y = 0.340 m ; maille 10054 ; nœud 9569 | -18.809 | z = 3.300 m, x = 0.325 m, y = 0.340 m ; maille 10060 ; nœud 9574 |
| MT | 30.617 | z = 3.300 m, x = 0.650 m, y = 0.340 m ; maille 10061 ; nœud 9575 | -30.617 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| MFY | 24.452 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10058 ; nœud 576 | -24.452 | z = 3.300 m, x = 2.600 m, y = 0.340 m ; maille 10066 ; nœud 577 |
| MFZ | 64.371 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -64.371 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **810.159** | **-281.541** |
| PIED_TUBES | -0.000 | -0.000 | **1081.119** |
| SYM_G | **195.967** | 226.029 | -96.065 |
| SYM_D | **-195.967** | 226.029 | -96.065 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 810.159 kN contre 810.159 kN de réaction d'ancrage selon Y (écart relatif -1.0e-13) ; Σ N × sin θ = -294.814 kN contre -281.541 kN selon Z (écart relatif -4.7e-02, sous pesanteur l'ancrage porte en plus une part du poids propre du tirant : l'écart vertical n'est pas un défaut de lecture).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 3791.032 ; marne compacte 1009.798 ; total 4800.829.

### Cas élémentaire EAU_P

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -6.5626 mm, z = 2.600 m, x = -0.322 m, y = 0.633 m ; TUBE_02 ; nœud 245. Étendue sur les 82 nœuds des anneaux de tête : de -6.5626 à -6.5607 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -2.600 | 138.224 | 138.224 | 138.224 |
| 2 | 0.000 | 167.543 | 167.543 | 167.543 |
| 3 | 2.600 | 138.224 | 138.224 | 138.224 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 797.193 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 439 | -511.670 | z = -3.750 m, x = 0.000 m, y = 0.710 m ; TUBE_02 ; maille 13493 ; nœud 4046 |
| NYY | 2894.030 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -566.027 | z = 2.250 m, x = -2.489 m, y = 0.701 m ; TUBE_01 ; maille 12368 ; nœud 2760 |
| MXX | 34.679 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -48.068 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |
| MYY | 35.659 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -14.420 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 122.160 | z = -13.000 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9912 | -52.069 | z = -4.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 10064 |
| NYY | 0.026 | z = 2.600 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9540 | -0.524 | z = -13.000 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 1721 |
| NXY | 97.037 | z = -11.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5106 | -97.037 | z = -11.250 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 3077 |
| MXX | 83.922 | z = -12.750 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9647 | -48.200 | z = -6.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 10056 |
| MYY | 1.587 | z = -3.750 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 8406 | -1.017 | z = -13.500 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 2960 |
| MXY | 0.069 | z = -10.250 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9679 | -0.069 | z = -10.250 m, x = 1.654 m, y = 0.000 m ; PALP_02_03 ; nœud 10144 |
| QX | 246.891 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -64.165 | z = 2.600 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9542 |
| QY | 6.825 | z = -3.750 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 8406 | -6.825 | z = -3.750 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 1757 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| VY | 25.499 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -25.499 | z = 3.300 m, x = -1.950 m, y = 0.340 m ; maille 10053 ; nœud 9568 |
| VZ | 9.132 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 10057 ; nœud 9572 | -9.132 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 10066 ; nœud 9580 |
| MT | 15.970 | z = 3.300 m, x = 0.650 m, y = 0.340 m ; maille 10061 ; nœud 9575 | -15.970 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 10057 ; nœud 9572 |
| MFY | 11.872 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10058 ; nœud 576 | -11.872 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| MFZ | 33.149 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -33.149 | z = 3.300 m, x = 2.600 m, y = 0.340 m ; maille 10066 ; nœud 577 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **417.225** | **-151.827** |
| PIED_TUBES | -0.000 | 0.000 | **151.827** |
| SYM_G | **-69.961** | 112.625 | -111.579 |
| SYM_D | **69.961** | 112.625 | -111.579 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 417.225 kN contre 417.225 kN de réaction d'ancrage selon Y (écart relatif 5.5e-14) ; Σ N × sin θ = -151.827 kN contre -151.827 kN selon Z (écart relatif -2.1e-13, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 1225.832 ; marne compacte 199.244 ; total 1425.075.

### Cas élémentaire EAU_A

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -15.3923 mm, z = 2.600 m, x = 0.701 m, y = 0.111 m ; TUBE_02 ; nœud 160. Étendue sur les 82 nœuds des anneaux de tête : de -15.3923 à -15.3877 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -2.600 | 324.393 | 324.393 | 324.393 |
| 2 | 0.000 | 393.203 | 393.203 | 393.203 |
| 3 | 2.600 | 324.393 | 324.393 | 324.393 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1874.206 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -1182.225 | z = -3.750 m, x = 0.000 m, y = 0.710 m ; TUBE_02 ; maille 13493 ; nœud 4046 |
| NYY | 6788.890 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -1334.394 | z = 2.250 m, x = -2.489 m, y = 0.701 m ; TUBE_01 ; maille 12368 ; nœud 2760 |
| MXX | 81.382 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 439 | -112.796 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |
| MYY | 83.685 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 439 | -33.839 | z = 2.600 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 441 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 283.624 | z = -13.000 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9912 | -121.387 | z = -4.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 10064 |
| NYY | 0.061 | z = 2.600 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 9565 | -1.218 | z = -13.000 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 1721 |
| NXY | 225.658 | z = -11.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5106 | -225.658 | z = -11.250 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 3077 |
| MXX | 195.241 | z = -12.750 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9647 | -112.747 | z = -6.750 m, x = -1.182 m, y = 0.000 m ; PALP_01_02 ; nœud 9795 |
| MYY | 3.661 | z = -4.000 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 8405 | -2.363 | z = -13.500 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 2960 |
| MXY | 0.159 | z = -10.250 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9679 | -0.159 | z = -10.250 m, x = 1.654 m, y = 0.000 m ; PALP_02_03 ; nœud 10144 |
| QX | 579.896 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -150.670 | z = 2.600 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9542 |
| QY | 15.756 | z = -4.000 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 8405 | -15.756 | z = -4.000 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 1756 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 | -0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 |
| VY | 59.843 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 10066 ; nœud 9580 | -59.843 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| VZ | 21.432 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 10057 ; nœud 9572 | -21.432 | z = 3.300 m, x = 1.950 m, y = 0.340 m ; maille 10065 ; nœud 9579 |
| MT | 37.480 | z = 3.300 m, x = 0.975 m, y = 0.340 m ; maille 10062 ; nœud 9576 | -37.480 | z = 3.300 m, x = -0.325 m, y = 0.340 m ; maille 10058 ; nœud 9573 |
| MFY | 27.862 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -27.862 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| MFZ | 77.796 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10058 ; nœud 576 | -77.796 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **979.173** | **-356.318** |
| PIED_TUBES | -0.000 | 0.000 | **356.318** |
| SYM_G | **-168.947** | 265.380 | -261.857 |
| SYM_D | **168.947** | 265.380 | -261.857 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 979.173 kN contre 979.173 kN de réaction d'ancrage selon Y (écart relatif -6.0e-14) ; Σ N × sin θ = -356.318 kN contre -356.318 kN selon Z (écart relatif -8.4e-14, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 2852.972 ; marne compacte 466.554 ; total 3319.527.

### Cas élémentaire Q1

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -7.6948 mm, z = 2.600 m, x = -0.502 m, y = 0.502 m ; TUBE_02 ; nœud 259. Étendue sur les 82 nœuds des anneaux de tête : de -7.6948 à -7.6924 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -2.600 | 164.063 | 164.063 | 164.063 |
| 2 | 0.000 | 198.864 | 198.864 | 198.864 |
| 3 | 2.600 | 164.063 | 164.063 | 164.063 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 968.566 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12368 ; nœud 146 | -480.224 | z = 2.600 m, x = -2.489 m, y = 0.701 m ; TUBE_01 ; maille 12254 ; nœud 140 |
| NYY | 3427.860 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12368 ; nœud 146 | -683.090 | z = 2.250 m, x = -2.489 m, y = 0.701 m ; TUBE_01 ; maille 12368 ; nœud 2760 |
| MXX | 41.145 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -57.035 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |
| MYY | 42.320 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 | -17.111 | z = 2.600 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 147 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 106.062 | z = -13.000 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9912 | -51.126 | z = -4.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 10064 |
| NYY | 0.028 | z = 2.600 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 9565 | -0.475 | z = -13.000 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 1721 |
| NXY | 88.380 | z = -11.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5106 | -88.380 | z = -11.250 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 3077 |
| MXX | 72.468 | z = -12.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 9936 | -36.112 | z = -7.750 m, x = 1.182 m, y = 0.000 m ; PALP_02_03 ; nœud 10052 |
| MYY | 1.908 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -0.880 | z = -13.500 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 2960 |
| MXY | 0.075 | z = 2.600 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 504 | -0.075 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 |
| QX | 220.380 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -57.320 | z = 2.600 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9542 |
| QY | 8.732 | z = 2.600 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 504 | -8.732 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| VY | 30.266 | z = 3.300 m, x = 0.325 m, y = 0.340 m ; maille 10060 ; nœud 9574 | -30.266 | z = 3.300 m, x = -1.950 m, y = 0.340 m ; maille 10053 ; nœud 9568 |
| VZ | 10.839 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 10057 ; nœud 9572 | -10.839 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 10066 ; nœud 9580 |
| MT | 18.956 | z = 3.300 m, x = 1.625 m, y = 0.340 m ; maille 10064 ; nœud 9578 | -18.956 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| MFY | 14.091 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -14.091 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| MFZ | 39.346 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10058 ; nœud 576 | -39.346 | z = 3.300 m, x = 2.600 m, y = 0.340 m ; maille 10066 ; nœud 577 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **495.220** | **-180.209** |
| PIED_TUBES | -0.000 | -0.000 | **180.209** |
| SYM_G | **-155.591** | 156.118 | -132.565 |
| SYM_D | **155.591** | 156.118 | -132.565 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 495.220 kN contre 495.220 kN de réaction d'ancrage selon Y (écart relatif -2.7e-13) ; Σ N × sin θ = -180.209 kN contre -180.209 kN selon Z (écart relatif 2.8e-13, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse 1152.357 ; marne compacte 189.639 ; total 1341.996.

### Cas élémentaire Q3

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue -13.6118 mm, z = 2.600 m, x = 2.489 m, y = 0.701 m ; TUBE_03 ; nœud 440. Étendue sur les 82 nœuds des anneaux de tête : de -13.6118 à -13.6085 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -2.600 | 305.446 | 305.446 | 305.446 |
| 2 | 0.000 | 370.152 | 370.152 | 370.152 |
| 3 | 2.600 | 305.446 | 305.446 | 305.446 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 2304.724 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12368 ; nœud 146 | -416.434 | z = 2.600 m, x = 2.489 m, y = 0.701 m ; TUBE_03 ; maille 17084 ; nœud 440 |
| NYY | 6425.166 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17083 ; nœud 439 | -1272.480 | z = 2.250 m, x = 2.489 m, y = 0.701 m ; TUBE_03 ; maille 17083 ; nœud 7446 |
| MXX | 76.467 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 439 | -105.856 | z = 2.600 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 441 |
| MYY | 78.741 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 439 | -31.757 | z = 2.600 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 441 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 27.897 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 294 | -5.351 | z = 2.600 m, x = -0.946 m, y = 0.000 m ; PALP_01_02 ; nœud 9539 |
| NYY | 0.043 | z = -18.000 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 499 | -0.014 | z = 2.600 m, x = -1.418 m, y = 0.000 m ; PALP_01_02 ; nœud 9541 |
| NXY | 17.297 | z = 1.000 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 74 | -17.297 | z = 1.000 m, x = 1.890 m, y = 0.000 m ; TUBE_03 ; nœud 501 |
| MXX | 26.238 | z = 2.600 m, x = -1.890 m, y = 0.000 m ; TUBE_01 ; nœud 77 | -6.906 | z = 2.600 m, x = -1.654 m, y = 0.000 m ; PALP_01_02 ; nœud 9542 |
| MYY | 0.114 | z = 2.600 m, x = -0.946 m, y = 0.000 m ; PALP_01_02 ; nœud 9539 | -0.422 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 161 |
| MXY | 0.026 | z = 2.500 m, x = -0.946 m, y = 0.000 m ; PALP_01_02 ; nœud 9535 | -0.026 | z = 2.500 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9562 |
| QX | 34.730 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 161 | -10.047 | z = 2.600 m, x = 0.946 m, y = 0.000 m ; PALP_02_03 ; nœud 9566 |
| QY | 2.316 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 161 | -2.316 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 294 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| VY | 273.153 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -273.153 | z = 3.300 m, x = -0.650 m, y = 0.340 m ; maille 10057 ; nœud 9572 |
| VZ | 144.229 | z = 3.300 m, x = -1.950 m, y = 0.340 m ; maille 10053 ; nœud 9568 | -144.229 | z = 3.300 m, x = 1.625 m, y = 0.340 m ; maille 10064 ; nœud 9578 |
| MT | 113.007 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 | -113.007 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 |
| MFY | 187.498 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10058 ; nœud 576 | -187.498 | z = 3.300 m, x = 2.600 m, y = 0.340 m ; maille 10066 ; nœud 577 |
| MFZ | 355.099 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10058 ; nœud 576 | -355.099 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **0.000** | **921.901** | **-335.477** |
| PIED_TUBES | 0.000 | -0.000 | **-164.523** |
| SYM_G | **-800.331** | 466.930 | -370.958 |
| SYM_D | **800.331** | 466.930 | -370.958 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = 921.901 kN contre 921.901 kN de réaction d'ancrage selon Y (écart relatif -1.6e-14) ; Σ N × sin θ = -335.477 kN contre -335.477 kN selon Z (écart relatif -1.5e-13, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse -21.519 ; marne compacte -34.382 ; total -55.901.

### Cas élémentaire A

**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : maximum en valeur absolue 10.5449 mm, z = 2.600 m, x = 0.701 m, y = 0.111 m ; TUBE_02 ; nœud 160. Étendue sur les 82 nœuds des anneaux de tête : de 10.5102 à 10.5449 mm.

**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de la barre, kN ; > 0 en traction) :

| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |
|---:|---:|---:|---:|---:|
| 1 | -2.600 | -227.901 | -227.901 | -227.901 |
| 2 | 0.000 | -277.147 | -277.147 | -277.147 |
| 3 | 2.600 | -227.901 | -227.901 | -227.901 |

**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local « utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 1909.534 | z = 2.600 m, x = 0.000 m, y = -0.710 m ; TUBE_02 ; maille 15819 ; nœud 364 | -1250.297 | z = 2.600 m, x = -0.633 m, y = -0.322 m ; TUBE_02 ; maille 15014 ; nœud 315 |
| NYY | 932.993 | z = 2.250 m, x = 2.489 m, y = 0.701 m ; TUBE_03 ; maille 17083 ; nœud 7446 | -4750.182 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12368 ; nœud 146 |
| MXX | 79.630 | z = 2.600 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 441 | -57.258 | z = 2.500 m, x = -2.600 m, y = 0.710 m ; TUBE_01 ; maille 12369 ; nœud 146 |
| MYY | 23.889 | z = 2.600 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 441 | -58.815 | z = 2.500 m, x = 2.600 m, y = 0.710 m ; TUBE_03 ; maille 17084 ; nœud 439 |

**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère local « utilisateur » ; kN/m et kN·m/m) :

| Composante | Maximum (kN/m ou kN·m/m) | Lieu du maximum | Minimum (kN/m ou kN·m/m) | Lieu du minimum |
|---|---:|---|---:|---|
| NXX | 199.713 | z = 0.250 m, x = -0.946 m, y = 0.000 m ; PALP_01_02 ; nœud 9874 | -574.736 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 294 |
| NYY | 0.213 | z = -12.500 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5102 | -0.377 | z = -0.500 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5149 |
| NXY | 248.692 | z = 1.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5155 | -248.692 | z = 1.250 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 3085 |
| MXX | 55.434 | z = 2.500 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 293 | -29.276 | z = 1.250 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 5155 |
| MYY | 0.350 | z = 0.750 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 3029 | -0.564 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 294 |
| MXY | 0.055 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 161 | -0.055 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 294 |
| QX | 109.490 | z = 2.000 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 292 | -254.877 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 161 |
| QY | 3.264 | z = 2.600 m, x = 0.710 m, y = 0.000 m ; TUBE_02 ; nœud 161 | -3.264 | z = 2.600 m, x = -0.710 m, y = 0.000 m ; TUBE_02 ; nœud 294 |

**Moments et efforts extrêmes dans la poutre de couronnement** (`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :

| Composante | Maximum (kN ou kN·m) | Lieu du maximum | Minimum (kN ou kN·m) | Lieu du minimum |
|---|---:|---|---:|---|
| N | 0.000 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 | -0.000 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 |
| VY | 237.312 | z = 3.300 m, x = -2.275 m, y = 0.340 m ; maille 10052 ; nœud 9567 | -237.312 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 |
| VZ | 10.217 | z = 3.300 m, x = 2.275 m, y = 0.340 m ; maille 10066 ; nœud 9580 | -10.217 | z = 3.300 m, x = -0.325 m, y = 0.340 m ; maille 10058 ; nœud 9573 |
| MT | 336.670 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 | -336.670 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 |
| MFY | 13.282 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 | -13.282 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 |
| MFZ | 308.505 | z = 3.300 m, x = -2.600 m, y = 0.340 m ; maille 10051 ; nœud 575 | -308.505 | z = 3.300 m, x = 0.000 m, y = 0.340 m ; maille 10059 ; nœud 576 |

**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes bloquées en gras) :

| Groupe | DX | DY | DZ |
|---|---:|---:|---:|
| ANCRAGES | **-0.000** | **-688.762** | **250.638** |
| PIED_TUBES | -0.000 | 0.000 | **-250.638** |
| SYM_G | **596.039** | -379.951 | 179.094 |
| SYM_D | **-596.039** | -379.951 | 179.094 |

Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = -688.762 kN contre -688.762 kN de réaction d'ancrage selon Y (écart relatif 3.0e-14) ; Σ N × sin θ = 250.638 kN contre 250.638 kN selon Z (écart relatif 8.2e-14, exacte hors pesanteur).

Somme des ressorts par couche (force exercée sur l'écran selon Y, −Σ k·DY, kN) : argile marneuse -191.431 ; marne compacte 80.194 ; total -111.238.

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

## Profils du déplacement horizontal DY le long des tubes

`DEPL`, `DY`, repère global, en mm (< 0 vers le bassin). Chaque valeur est la **moyenne de DY sur l'anneau de nœuds** du tube à la cote donnée ; l'étendue (minimum à maximum sur l'anneau) figure entre parenthèses.

### TUBE_02

| Cote (m) | G | EAU_P | EAU_A | Q1 | Q3 | A |
|---:|---:|---:|---:|---:|---:|---:|
| 2.600 | -13.0236 (-13.0236 ; -13.0236) | -6.5626 (-6.5626 ; -6.5626) | -15.3923 (-15.3923 ; -15.3923) | -7.6948 (-7.6948 ; -7.6948) | -13.6085 (-13.6085 ; -13.6085) | 10.5449 (10.5449 ; 10.5449) |
| 2.500 | -13.2165 (-13.5525 ; -10.6735) | -6.6426 (-6.8170 ; -5.3341) | -15.5746 (-15.9842 ; -12.5044) | -7.7307 (-7.9384 ; -6.1785) | -13.3451 (-13.7426 ; -10.4718) | 10.4959 (8.2943 ; 10.7738) |
| 2.250 | -13.9470 (-14.2477 ; -13.3279) | -6.9701 (-7.1274 ; -6.6518) | -16.3293 (-16.6986 ; -15.5841) | -7.9689 (-8.1551 ; -7.5901) | -12.9442 (-13.2925 ; -12.2739) | 10.5794 (9.9455 ; 11.4256) |
| 2.000 | -14.5988 (-14.7858 ; -14.1766) | -7.2575 (-7.3563 ; -7.0383) | -16.9896 (-17.2212 ; -16.4792) | -8.1593 (-8.2777 ; -7.8971) | -12.4649 (-12.6497 ; -12.0277) | 10.6123 (10.0648 ; 12.1957) |
| 1.750 | -15.2483 (-15.3955 ; -14.9156) | -7.5447 (-7.6224 ; -7.3685) | -17.6490 (-17.8301 ; -17.2425) | -8.3502 (-8.4462 ; -8.1393) | -12.0053 (-12.1210 ; -11.6772) | 10.6402 (9.9222 ; 12.9842) |
| 1.500 | -15.8905 (-16.0099 ; -15.6373) | -7.8287 (-7.8926 ; -7.6893) | -18.3009 (-18.4481 ; -17.9841) | -8.5385 (-8.6169 ; -8.3728) | -11.5589 (-11.6350 ; -11.3220) | 10.6284 (9.7517 ; 13.5517) |
| 1.250 | -16.5202 (-16.6183 ; -16.3090) | -8.1069 (-8.1603 ; -7.9837) | -18.9391 (-19.0605 ; -18.6646) | -8.7213 (-8.7854 ; -8.5782) | -11.1222 (-11.1770 ; -10.9285) | 10.5968 (9.6526 ; 13.9621) |
| 1.000 | -17.1377 (-17.2219 ; -16.9633) | -8.3791 (-8.4261 ; -8.2686) | -19.5634 (-19.6687 ; -19.3230) | -8.8989 (-8.9531 ; -8.7756) | -10.6971 (-10.7375 ; -10.5369) | 10.5214 (9.6273 ; 14.0644) |
| 0.750 | -17.7405 (-17.8172 ; -17.5959) | -8.6440 (-8.6884 ; -8.5421) | -20.1711 (-20.2684 ; -19.9545) | -9.0703 (-9.1183 ; -8.9623) | -10.2826 (-10.3176 ; -10.1454) | 10.4282 (9.6263 ; 13.9759) |
| 0.500 | -18.3274 (-18.4011 ; -18.2094) | -8.9007 (-8.9450 ; -8.8057) | -20.7602 (-20.8551 ; -20.5626) | -9.2348 (-9.2792 ; -9.1402) | -9.8787 (-9.9169 ; -9.7594) | 10.3443 (9.4975 ; 13.8377) |
| 0.250 | -18.8966 (-18.9706 ; -18.8036) | -9.1481 (-9.1932 ; -9.0592) | -21.3287 (-21.4251 ; -21.1473) | -9.3919 (-9.4343 ; -9.3094) | -9.4853 (-9.5272 ; -9.3805) | 10.2490 (9.3559 ; 13.5863) |
| 0.000 | -19.4469 (-19.5234 ; -19.3395) | -9.3858 (-9.4324 ; -9.3029) | -21.8748 (-21.9754 ; -21.7086) | -9.5409 (-9.5826 ; -9.4698) | -9.1022 (-9.1483 ; -9.0098) | 10.1460 (9.1913 ; 13.2791) |
| -0.250 | -19.9767 (-20.0576 ; -19.8478) | -9.6127 (-9.6622 ; -9.5222) | -22.3967 (-22.5034 ; -22.2134) | -9.6813 (-9.7232 ; -9.6197) | -8.7293 (-8.7798 ; -8.6479) | 10.0354 (8.9955 ; 12.9442) |
| -0.500 | -20.4848 (-20.5718 ; -20.3320) | -9.8284 (-9.8811 ; -9.7266) | -22.8927 (-23.0070 ; -22.6812) | -9.8124 (-9.8553 ; -9.7435) | -8.3664 (-8.4211 ; -8.2948) | 9.9173 (8.7894 ; 12.5990) |
| -0.750 | -20.9698 (-21.0670 ; -20.7905) | -10.0320 (-10.0884 ; -9.9187) | -23.3610 (-23.4843 ; -23.1200) | -9.9340 (-9.9785 ; -9.8569) | -8.0134 (-8.0720 ; -7.9505) | 9.7922 (8.5867 ; 12.2546) |
| -1.000 | -21.4304 (-21.5423 ; -21.2220) | -10.2231 (-10.2835 ; -10.0979) | -23.8003 (-23.9338 ; -23.5284) | -10.0454 (-10.0923 ; -9.9592) | -7.6701 (-7.7320 ; -7.6150) | 9.6601 (8.3907 ; 11.9170) |
| -1.250 | -21.8656 (-21.9941 ; -21.6250) | -10.4010 (-10.4658 ; -10.2633) | -24.2092 (-24.3542 ; -23.9047) | -10.1464 (-10.1962 ; -10.0499) | -7.3365 (-7.4008 ; -7.2881) | 9.5216 (8.2037 ; 11.5894) |
| -1.500 | -22.2742 (-22.4213 ; -21.9980) | -10.5651 (-10.6348 ; -10.4141) | -24.5867 (-24.7440 ; -24.2475) | -10.2365 (-10.2906 ; -10.1285) | -7.0123 (-7.0784 ; -6.9698) | 9.3768 (8.0266 ; 11.2729) |
| -1.750 | -22.6551 (-22.8263 ; -22.3396) | -10.7151 (-10.7901 ; -10.5497) | -24.9314 (-25.1023 ; -24.5555) | -10.3153 (-10.3765 ; -10.1946) | -6.6975 (-6.7645 ; -6.6599) | 9.2260 (7.8597 ; 10.9676) |
| -2.000 | -23.0073 (-23.2084 ; -22.6487) | -10.8505 (-10.9315 ; -10.6694) | -25.2424 (-25.4292 ; -24.8270) | -10.3826 (-10.4517 ; -10.2478) | -6.3919 (-6.4590 ; -6.3586) | 9.0696 (7.7023 ; 10.6726) |
| -2.250 | -23.3300 (-23.5639 ; -22.9238) | -10.9708 (-11.0619 ; -10.7727) | -25.5188 (-25.7292 ; -25.0609) | -10.4382 (-10.5159 ; -10.2877) | -6.0953 (-6.1619 ; -6.0657) | 8.9077 (7.5535 ; 10.3867) |
| -2.500 | -23.6225 (-23.8977 ; -23.1638) | -11.0757 (-11.1778 ; -10.8588) | -25.7596 (-25.9959 ; -25.2558) | -10.4818 (-10.5703 ; -10.3139) | -5.8076 (-5.8731 ; -5.7812) | 8.7408 (7.4120 ; 10.1085) |
| -2.750 | -23.8839 (-24.2060 ; -23.3676) | -11.1650 (-11.2791 ; -10.9274) | -25.9644 (-26.2286 ; -25.4106) | -10.5133 (-10.6160 ; -10.3262) | -5.5288 (-5.5926 ; -5.5051) | 8.5691 (7.2764 ; 9.8364) |
| -3.000 | -24.1135 (-24.4912 ; -23.5341) | -11.2384 (-11.3656 ; -10.9781) | -26.1323 (-26.4270 ; -25.5242) | -10.5324 (-10.6506 ; -10.3243) | -5.2585 (-5.3202 ; -5.2373) | 8.3928 (7.1454 ; 9.5692) |
| -3.250 | -24.3107 (-24.7499 ; -23.6622) | -11.2956 (-11.4418 ; -11.0103) | -26.2629 (-26.6006 ; -25.5958) | -10.5391 (-10.6776 ; -10.3078) | -4.9968 (-5.0561 ; -4.9778) | 8.2123 (7.0175 ; 9.3055) |
| -3.500 | -24.4750 (-24.9807 ; -23.7511) | -11.3365 (-11.5030 ; -11.0239) | -26.3558 (-26.7407 ; -25.6244) | -10.5333 (-10.6953 ; -10.2767) | -4.7435 (-4.8000 ; -4.7265) | 8.0279 (6.8915 ; 9.0442) |
| -3.750 | -24.6059 (-25.1835 ; -23.7998) | -11.3609 (-11.5521 ; -11.0185) | -26.4108 (-26.8511 ; -25.6095) | -10.5148 (-10.7040 ; -10.2308) | -4.4984 (-4.5519 ; -4.4833) | 7.8399 (6.7663 ; 8.7843) |
| -4.000 | -24.7030 (-25.3580 ; -23.8076) | -11.3689 (-11.5888 ; -10.9939) | -26.4276 (-26.9334 ; -25.5503) | -10.4838 (-10.7020 ; -10.1698) | -4.2615 (-4.3118 ; -4.2476) | 7.6485 (6.6409 ; 8.5252) |
| -4.250 | -24.7659 (-25.5042 ; -23.7738) | -11.3603 (-11.6144 ; -10.9500) | -26.4062 (-26.9906 ; -25.4465) | -10.4400 (-10.6894 ; -10.0937) | -4.0325 (-4.0796 ; -4.0191) | 7.4540 (6.5145 ; 8.2662) |
| -4.500 | -24.7945 (-25.6220 ; -23.6979) | -11.3352 (-11.6263 ; -10.8866) | -26.3465 (-27.0169 ; -25.2978) | -10.3837 (-10.6662 ; -10.0025) | -3.8114 (-3.8552 ; -3.7985) | 7.2568 (6.3865 ; 8.0069) |
| -4.750 | -24.7886 (-25.7116 ; -23.5793) | -11.2936 (-11.6239 ; -10.8036) | -26.2488 (-27.0104 ; -25.1039) | -10.3149 (-10.6327 ; -9.8960) | -3.5979 (-3.6385 ; -3.5855) | 7.0572 (6.2564 ; 7.7469) |
| -5.000 | -24.7482 (-25.7731 ; -23.4175) | -11.2357 (-11.6075 ; -10.7010) | -26.1132 (-26.9715 ; -24.8647) | -10.2336 (-10.5888 ; -9.7743) | -3.3921 (-3.4294 ; -3.3802) | 6.8553 (6.1238 ; 7.4862) |
| -5.250 | -24.6732 (-25.8066 ; -23.2123) | -11.1616 (-11.5772 ; -10.5789) | -25.9401 (-26.9006 ; -24.5803) | -10.1401 (-10.5349 ; -9.6374) | -3.1937 (-3.2278 ; -3.1823) | 6.6516 (5.9887 ; 7.2247) |
| -5.500 | -24.5638 (-25.8123 ; -22.9634) | -11.0715 (-11.5333 ; -10.4374) | -25.7300 (-26.7982 ; -24.2510) | -10.0344 (-10.4710 ; -9.4853) | -3.0027 (-3.0336 ; -2.9917) | 6.4463 (5.8509 ; 6.9625) |
| -5.750 | -24.4203 (-25.7907 ; -22.6706) | -10.9657 (-11.4761 ; -10.2765) | -25.4835 (-26.6650 ; -23.8769) | -9.9168 (-10.3974 ; -9.3180) | -2.8188 (-2.8467 ; -2.8082) | 6.2397 (5.7104 ; 6.6996) |
| -6.000 | -24.2429 (-25.7420 ; -22.3339) | -10.8444 (-11.4058 ; -10.0966) | -25.2011 (-26.5017 ; -23.4585) | -9.7875 (-10.3142 ; -9.1357) | -2.6420 (-2.6669 ; -2.6319) | 6.0321 (5.5674 ; 6.4363) |
| -6.250 | -24.0320 (-25.6668 ; -21.9534) | -10.7080 (-11.3229 ; -9.8978) | -24.8837 (-26.3092 ; -22.9964) | -9.6468 (-10.2218 ; -8.9385) | -2.4722 (-2.4941 ; -2.4624) | 5.8237 (5.4221 ; 6.1728) |
| -6.500 | -23.7881 (-25.5656 ; -21.5293) | -10.5568 (-11.2278 ; -9.6804) | -24.5321 (-26.0883 ; -22.4913) | -9.4949 (-10.1203 ; -8.7264) | -2.3091 (-2.3283 ; -2.2997) | 5.6150 (5.2746 ; 5.9093) |
| -6.750 | -23.5119 (-25.4391 ; -21.0620) | -10.3913 (-11.1209 ; -9.4450) | -24.1473 (-25.8401 ; -21.9442) | -9.3323 (-10.0100 ; -8.4999) | -2.1527 (-2.1693 ; -2.1437) | 5.4062 (5.1253 ; 5.6462) |
| -7.000 | -23.2041 (-25.2879 ; -20.5520) | -10.2120 (-11.0028 ; -9.1918) | -23.7305 (-25.5658 ; -21.3560) | -9.1592 (-9.8912 ; -8.2590) | -2.0029 (-2.0170 ; -1.9942) | 5.1975 (4.9745 ; 5.3837) |
| -7.250 | -22.8653 (-25.1130 ; -20.0001) | -10.0193 (-10.8739 ; -8.9215) | -23.2827 (-25.2666 ; -20.7280) | -8.9761 (-9.7643 ; -8.0041) | -1.8595 (-1.8712 ; -1.8512) | 4.9892 (4.8226 ; 5.1223) |
| -7.500 | -22.4967 (-24.9152 ; -19.4072) | -9.8139 (-10.7349 ; -8.6347) | -22.8052 (-24.9439 ; -20.0617) | -8.7834 (-9.6296 ; -7.7356) | -1.7223 (-1.7319 ; -1.7144) | 4.7818 (4.6697 ; 4.8622) |
| -7.750 | -22.0991 (-24.6958 ; -18.7745) | -9.5962 (-10.5863 ; -8.3321) | -22.2996 (-24.5991 ; -19.3586) | -8.5815 (-9.4876 ; -7.4541) | -1.5913 (-1.6001 ; -1.5837) | 4.5753 (4.5164 ; 4.6037) |
| -8.000 | -21.6737 (-24.4559 ; -18.1034) | -9.3670 (-10.4290 ; -8.0145) | -21.7671 (-24.2339 ; -18.6206) | -8.3710 (-9.3387 ; -7.1601) | -1.4664 (-1.4761 ; -1.4591) | 4.3702 (4.3473 ; 4.3810) |
| -8.250 | -21.2216 (-24.1970 ; -17.3957) | -9.1270 (-10.2635 ; -7.6827) | -21.2095 (-23.8499 ; -17.8499) | -8.1523 (-9.1837 ; -6.8544) | -1.3473 (-1.3578 ; -1.3403) | 4.1666 (4.0933 ; 4.2098) |
| -8.500 | -20.7443 (-23.9205 ; -16.6535) | -8.8769 (-10.0908 ; -7.3379) | -20.6284 (-23.4489 ; -17.0488) | -7.9260 (-9.0232 ; -6.5380) | -1.2340 (-1.2451 ; -1.2274) | 3.9650 (3.8419 ; 4.0571) |
| -8.750 | -20.2432 (-23.6281 ; -15.8792) | -8.6174 (-9.9115 ; -6.9811) | -20.0256 (-23.0328 ; -16.2199) | -7.6926 (-8.8577 ; -6.2118) | -1.1264 (-1.1379 ; -1.1200) | 3.7655 (3.5937 ; 3.9054) |
| -9.000 | -19.7198 (-23.3217 ; -15.0757) | -8.3493 (-9.7266 ; -6.6137) | -19.4030 (-22.6035 ; -15.3663) | -7.4531 (-8.6890 ; -5.8770) | -1.0243 (-1.0360 ; -1.0182) | 3.5686 (3.3490 ; 3.7549) |
| -9.250 | -19.1758 (-23.0032 ; -14.2463) | -8.0736 (-9.5369 ; -6.2371) | -18.7625 (-22.1632 ; -14.4913) | -7.2076 (-8.5171 ; -5.5350) | -0.9275 (-0.9392 ; -0.9218) | 3.3743 (3.1081 ; 3.6059) |
| -9.500 | -18.6129 (-22.6742 ; -13.3946) | -7.7910 (-9.3433 ; -5.8528) | -18.1062 (-21.7138 ; -13.5986) | -6.9567 (-8.3422 ; -5.1872) | -0.8360 (-0.8474 ; -0.8307) | 3.1831 (2.8716 ; 3.4588) |
| -9.750 | -18.0329 (-22.3368 ; -12.5250) | -7.5026 (-9.1466 ; -5.4627) | -17.4363 (-21.2573 ; -12.6922) | -6.7014 (-8.1658 ; -4.8353) | -0.7496 (-0.7605 ; -0.7447) | 2.9952 (2.6398 ; 3.3138) |
| -10.000 | -17.4378 (-21.9927 ; -11.6423) | -7.2093 (-8.9477 ; -5.0688) | -16.7550 (-20.7956 ; -11.7769) | -6.4422 (-7.9886 ; -4.4810) | -0.6682 (-0.6782 ; -0.6637) | 2.8110 (2.4132 ; 3.1711) |
| -10.250 | -16.8298 (-21.6435 ; -10.7521) | -6.9121 (-8.7472 ; -4.6732) | -16.0647 (-20.3303 ; -10.8579) | -6.1801 (-7.8112 ; -4.1264) | -0.5917 (-0.6004 ; -0.5867) | 2.6306 (2.1924 ; 3.0310) |
| -10.500 | -16.2111 (-21.2905 ; -9.8607) | -6.6120 (-8.5458 ; -4.2785) | -15.3677 (-19.8628 ; -9.9409) | -5.9158 (-7.6342 ; -3.7737) | -0.5199 (-0.5270 ; -0.5145) | 2.4543 (1.9781 ; 2.8936) |
| -10.750 | -15.5840 (-20.9343 ; -8.9755) | -6.3102 (-8.3438 ; -3.8877) | -14.6667 (-19.3939 ; -9.0328) | -5.6502 (-7.4577 ; -3.4255) | -0.4528 (-0.4579 ; -0.4471) | 2.2825 (1.7709 ; 2.7589) |
| -11.000 | -14.9509 (-20.5751 ; -8.1052) | -6.0078 (-8.1414 ; -3.5041) | -13.9642 (-18.9242 ; -8.1416) | -5.3843 (-7.2817 ; -3.0848) | -0.3900 (-0.3927 ; -0.3843) | 2.1154 (1.5716 ; 2.6270) |
| -11.250 | -14.3145 (-20.2122 ; -7.2596) | -5.7058 (-7.9385 ; -3.1316) | -13.2628 (-18.4532 ; -7.2761) | -5.1190 (-7.1061 ; -2.7549) | -0.3317 (-0.3356 ; -0.3263) | 1.9534 (1.3814 ; 2.4978) |
| -11.500 | -13.6772 (-19.8444 ; -6.4492) | -5.4055 (-7.7348 ; -2.7742) | -12.5652 (-17.9802 ; -6.4459) | -4.8553 (-6.9304 ; -2.4393) | -0.2775 (-0.2830 ; -0.2728) | 1.7965 (1.2014 ; 2.3711) |
| -11.750 | -13.0430 (-19.4699 ; -5.6881) | -5.1085 (-7.5296 ; -2.4379) | -11.8753 (-17.5040 ; -5.6645) | -4.5945 (-6.7538 ; -2.1431) | -0.2275 (-0.2347 ; -0.2198) | 1.6454 (1.0334 ; 2.2467) |
| -12.000 | -12.4074 (-19.0869 ; -4.9556) | -4.8131 (-7.3225 ; -2.1139) | -11.1891 (-17.0233 ; -4.9117) | -4.3350 (-6.5759 ; -1.8585) | -0.1812 (-0.1901 ; -0.1692) | 1.4991 (0.8737 ; 2.1245) |
| -12.250 | -11.7860 (-18.6935 ; -4.2789) | -4.5256 (-7.1129 ; -1.8152) | -10.5212 (-16.5367 ; -4.2178) | -4.0826 (-6.3958 ; -1.5965) | -0.1389 (-0.1497 ; -0.1218) | 1.3599 (0.7289 ; 2.0041) |
| -12.500 | -11.1899 (-18.2880 ; -3.6677) | -4.2505 (-6.9002 ; -1.5472) | -9.8822 (-16.0431 ; -3.5950) | -3.8411 (-6.2131 ; -1.3612) | -0.1006 (-0.1137 ; -0.0775) | 1.2290 (0.6017 ; 1.8855) |
| -12.750 | -10.6140 (-17.8688 ; -3.0978) | -3.9857 (-6.6841 ; -1.2995) | -9.2672 (-15.5413 ; -3.0195) | -3.6086 (-6.0271 ; -1.1436) | -0.0659 (-0.0823 ; -0.0363) | 1.1054 (0.4877 ; 1.7684) |
| -13.000 | -10.0604 (-17.4346 ; -2.5753) | -3.7321 (-6.4641 ; -1.0744) | -8.6781 (-15.0305 ; -2.4966) | -3.3859 (-5.8375 ; -0.9457) | -0.0347 (-0.0553 ; 0.0021) | 0.9892 (0.3870 ; 1.6527) |
| -13.250 | -9.5298 (-16.9846 ; -2.1010) | -3.4900 (-6.2401 ; -0.8720) | -8.1157 (-14.5105 ; -2.0262) | -3.1732 (-5.6440 ; -0.7675) | -0.0067 (-0.0332 ; 0.0378) | 0.8803 (0.2990 ; 1.5383) |
| -13.500 | -9.0228 (-16.5190 ; -1.6743) | -3.2595 (-6.0123 ; -0.6916) | -7.5804 (-13.9814 ; -1.6071) | -2.9707 (-5.4467 ; -0.6084) | 0.0181 (-0.0161 ; 0.0708) | 0.7785 (0.2229 ; 1.4253) |
| -13.750 | -8.5394 (-16.0387 ; -1.2936) | -3.0408 (-5.7810 ; -0.5323) | -7.0722 (-13.4444 ; -1.2368) | -2.7783 (-5.2459 ; -0.4678) | 0.0402 (-0.0026 ; 0.1012) | 0.6837 (0.1576 ; 1.3136) |
| -14.000 | -8.0796 (-15.5453 ; -0.9562) | -2.8337 (-5.5470 ; -0.3926) | -6.5912 (-12.9010 ; -0.9122) | -2.5960 (-5.0423 ; -0.3443) | 0.0595 (0.0080 ; 0.1291) | 0.5955 (0.1023 ; 1.2035) |
| -14.250 | -7.6432 (-15.0410 ; -0.6591) | -2.6382 (-5.3111 ; -0.2710) | -6.1370 (-12.3532 ; -0.6297) | -2.4238 (-4.8364 ; -0.2366) | 0.0763 (0.0163 ; 0.1546) | 0.5138 (0.0558 ; 1.0950) |
| -14.500 | -7.2298 (-14.5285 ; -0.3991) | -2.4540 (-5.0743 ; -0.1660) | -5.7091 (-11.8034 ; -0.3857) | -2.2613 (-4.6293 ; -0.1435) | 0.0908 (0.0224 ; 0.1777) | 0.4384 (0.0174 ; 0.9886) |
| -14.750 | -6.8387 (-14.0109 ; -0.1732) | -2.2809 (-4.8377 ; -0.0761) | -5.3070 (-11.2539 ; -0.1767) | -2.1084 (-4.4219 ; -0.0635) | 0.1032 (0.0268 ; 0.1986) | 0.3688 (-0.0140 ; 0.8843) |
| -15.000 | -6.4693 (-13.4911 ; 0.0213) | -2.1186 (-4.6024 ; 0.0001) | -4.9300 (-10.7075 ; 0.0005) | -1.9648 (-4.2152 ; 0.0044) | 0.1135 (0.0297 ; 0.2173) | 0.3050 (-0.0390 ; 0.7824) |
| -15.250 | -6.1207 (-12.9724 ; 0.1867) | -1.9668 (-4.3694 ; 0.0639) | -4.5772 (-10.1664 ; 0.1486) | -1.8302 (-4.0101 ; 0.0613) | 0.1221 (0.0314 ; 0.2338) | 0.2465 (-0.0584 ; 0.6832) |
| -15.500 | -5.7922 (-12.4579 ; 0.3251) | -1.8250 (-4.1398 ; 0.1162) | -4.2478 (-9.6331 ; 0.2703) | -1.7042 (-3.8075 ; 0.1082) | 0.1290 (0.0321 ; 0.2484) | 0.1931 (-0.0729 ; 0.5869) |
| -15.750 | -5.4828 (-11.9508 ; 0.4379) | -1.6928 (-3.9144 ; 0.1581) | -3.9407 (-9.1096 ; 0.3675) | -1.5864 (-3.6084 ; 0.1457) | 0.1343 (0.0319 ; 0.2610) | 0.1445 (-0.0829 ; 0.4937) |
| -16.000 | -5.1915 (-11.4538 ; 0.5263) | -1.5699 (-3.6941 ; 0.1902) | -3.6551 (-8.5979 ; 0.4422) | -1.4765 (-3.4135 ; 0.1746) | 0.1383 (0.0311 ; 0.2718) | 0.1005 (-0.0891 ; 0.4038) |
| -16.250 | -4.9175 (-10.9696 ; 0.5910) | -1.4557 (-3.4796 ; 0.2132) | -3.3899 (-8.0998 ; 0.4957) | -1.3741 (-3.2235 ; 0.1953) | 0.1410 (0.0297 ; 0.2808) | 0.0607 (-0.0919 ; 0.3176) |
| -16.500 | -4.6599 (-10.5006 ; 0.6327) | -1.3499 (-3.2716 ; 0.2277) | -3.1441 (-7.6168 ; 0.5295) | -1.2788 (-3.0390 ; 0.2083) | 0.1426 (0.0279 ; 0.2882) | 0.0248 (-0.0923 ; 0.2352) |
| -16.750 | -4.4177 (-10.0490 ; 0.6521) | -1.2520 (-3.0708 ; 0.2343) | -2.9167 (-7.1503 ; 0.5448) | -1.1903 (-2.8608 ; 0.2141) | 0.1432 (0.0257 ; 0.2940) | -0.0073 (-0.0934 ; 0.1570) |
| -17.000 | -4.1900 (-9.6164 ; 0.6502) | -1.1616 (-2.8778 ; 0.2337) | -2.7066 (-6.7020 ; 0.5434) | -1.1081 (-2.6892 ; 0.2132) | 0.1429 (0.0234 ; 0.2984) | -0.0359 (-0.0953 ; 0.0833) |
| -17.250 | -3.9760 (-9.2039 ; 0.6282) | -1.0783 (-2.6932 ; 0.2267) | -2.5130 (-6.2733 ; 0.5273) | -1.0319 (-2.5250 ; 0.2064) | 0.1418 (0.0210 ; 0.3012) | -0.0614 (-0.0988 ; 0.0142) |
| -17.500 | -3.7750 (-8.8120 ; 0.5880) | -1.0016 (-2.5176 ; 0.2144) | -2.3349 (-5.8654 ; 0.4985) | -0.9614 (-2.3686 ; 0.1946) | 0.1400 (0.0188 ; 0.3026) | -0.0838 (-0.1048 ; -0.0501) |
| -17.750 | -3.5866 (-8.4416 ; 0.5327) | -0.9311 (-2.3513 ; 0.1977) | -2.1711 (-5.4793 ; 0.4598) | -0.8962 (-2.2203 ; 0.1787) | 0.1376 (0.0168 ; 0.3025) | -0.1035 (-0.1139 ; -0.0669) |
| -18.000 | -3.4073 (-8.0854 ; 0.4636) | -0.8662 (-2.1945 ; 0.1769) | -2.0203 (-5.1150 ; 0.4113) | -0.8356 (-2.0796 ; 0.1589) | 0.1347 (0.0150 ; 0.3011) | -0.1208 (-0.1646 ; -0.0597) |
| -18.250 | -3.2408 (-7.7482 ; 0.3951) | -0.8072 (-2.0470 ; 0.1561) | -1.8832 (-4.7725 ; 0.3629) | -0.7801 (-1.9469 ; 0.1392) | 0.1313 (0.0134 ; 0.2984) | -0.1355 (-0.2150 ; -0.0525) |
| -18.500 | -3.0888 (-7.4344 ; 0.3378) | -0.7535 (-1.9088 ; 0.1383) | -1.7582 (-4.4516 ; 0.3215) | -0.7294 (-1.8225 ; 0.1225) | 0.1276 (0.0118 ; 0.2946) | -0.1483 (-0.2611 ; -0.0457) |
| -18.750 | -2.9486 (-7.1359 ; 0.2903) | -0.7045 (-1.7796 ; 0.1229) | -1.6445 (-4.1513 ; 0.2858) | -0.6828 (-1.7054 ; 0.1082) | 0.1236 (0.0103 ; 0.2898) | -0.1592 (-0.3031 ; -0.0390) |
| -19.000 | -2.8200 (-6.8519 ; 0.2522) | -0.6601 (-1.6586 ; 0.1097) | -1.5414 (-3.8703 ; 0.2550) | -0.6404 (-1.5952 ; 0.0960) | 0.1194 (0.0089 ; 0.2841) | -0.1684 (-0.3410 ; -0.0326) |
| -19.250 | -2.7025 (-6.5804 ; 0.2219) | -0.6200 (-1.5453 ; 0.0981) | -1.4480 (-3.6072 ; 0.2281) | -0.6017 (-1.4914 ; 0.0855) | 0.1150 (0.0074 ; 0.2776) | -0.1760 (-0.3751 ; -0.0265) |
| -19.500 | -2.5953 (-6.3206 ; 0.1980) | -0.5838 (-1.4393 ; 0.0878) | -1.3639 (-3.3610 ; 0.2041) | -0.5665 (-1.3936 ; 0.0763) | 0.1104 (0.0060 ; 0.2706) | -0.1822 (-0.4052 ; -0.0209) |
| -19.750 | -2.4981 (-6.0721 ; 0.1792) | -0.5512 (-1.3405 ; 0.0785) | -1.2882 (-3.1314 ; 0.1825) | -0.5347 (-1.3016 ; 0.0682) | 0.1058 (0.0046 ; 0.2631) | -0.1871 (-0.4314 ; -0.0159) |
| -20.000 | -2.4103 (-5.8354 ; 0.1645) | -0.5220 (-1.2488 ; 0.0701) | -1.2203 (-2.9184 ; 0.1631) | -0.5059 (-1.2157 ; 0.0610) | 0.1012 (0.0033 ; 0.2550) | -0.1908 (-0.4538 ; -0.0116) |
| -20.250 | -2.3312 (-5.6112 ; 0.1531) | -0.4959 (-1.1644 ; 0.0627) | -1.1598 (-2.7223 ; 0.1458) | -0.4799 (-1.1358 ; 0.0547) | 0.0965 (0.0021 ; 0.2465) | -0.1936 (-0.4725 ; -0.0078) |
| -20.500 | -2.2603 (-5.4000 ; 0.1442) | -0.4728 (-1.0871 ; 0.0561) | -1.1059 (-2.5428 ; 0.1305) | -0.4566 (-1.0620 ; 0.0491) | 0.0919 (0.0011 ; 0.2376) | -0.1954 (-0.4876 ; -0.0046) |
| -20.750 | -2.1972 (-5.2024 ; 0.1372) | -0.4522 (-1.0169 ; 0.0503) | -1.0582 (-2.3797 ; 0.1171) | -0.4357 (-0.9944 ; 0.0443) | 0.0873 (0.0002 ; 0.2284) | -0.1964 (-0.4995 ; -0.0019) |
| -21.000 | -2.1412 (-5.0189 ; 0.1317) | -0.4341 (-0.9537 ; 0.0453) | -1.0161 (-2.2328 ; 0.1054) | -0.4171 (-0.9327 ; 0.0401) | 0.0827 (-0.0006 ; 0.2189) | -0.1968 (-0.5083 ; 0.0003) |
| -21.250 | -2.0918 (-4.8497 ; 0.1273) | -0.4182 (-0.8971 ; 0.0409) | -0.9791 (-2.1014 ; 0.0954) | -0.4005 (-0.8770 ; 0.0366) | 0.0783 (-0.0012 ; 0.2092) | -0.1965 (-0.5145 ; 0.0021) |
| -21.500 | -2.0485 (-4.6946 ; 0.1236) | -0.4043 (-0.8470 ; 0.0372) | -0.9468 (-1.9849 ; 0.0867) | -0.3859 (-0.8269 ; 0.0335) | 0.0740 (-0.0016 ; 0.1994) | -0.1957 (-0.5182 ; 0.0036) |
| -21.750 | -2.0108 (-4.5536 ; 0.1206) | -0.3923 (-0.8028 ; 0.0340) | -0.9188 (-1.8822 ; 0.0793) | -0.3729 (-0.7821 ; 0.0308) | 0.0698 (-0.0020 ; 0.1897) | -0.1945 (-0.5198 ; 0.0047) |
| -22.000 | -1.9782 (-4.4260 ; 0.1180) | -0.3819 (-0.7642 ; 0.0313) | -0.8946 (-1.7926 ; 0.0730) | -0.3615 (-0.7425 ; 0.0285) | 0.0658 (-0.0022 ; 0.1801) | -0.1930 (-0.5197 ; 0.0056) |
| -22.250 | -1.9502 (-4.3114 ; 0.1159) | -0.3729 (-0.7308 ; 0.0290) | -0.8738 (-1.7149 ; 0.0677) | -0.3516 (-0.7077 ; 0.0266) | 0.0620 (-0.0023 ; 0.1706) | -0.1911 (-0.5180 ; 0.0062) |
| -22.500 | -1.9265 (-4.2091 ; 0.1140) | -0.3653 (-0.7021 ; 0.0270) | -0.8560 (-1.6482 ; 0.0632) | -0.3429 (-0.6772 ; 0.0249) | 0.0583 (-0.0024 ; 0.1614) | -0.1891 (-0.5151 ; 0.0067) |
| -22.750 | -1.9064 (-4.1183 ; 0.1125) | -0.3588 (-0.6777 ; 0.0254) | -0.8410 (-1.5914 ; 0.0595) | -0.3354 (-0.6507 ; 0.0235) | 0.0549 (-0.0024 ; 0.1526) | -0.1870 (-0.5112 ; 0.0070) |
| -23.000 | -1.8897 (-4.0381 ; 0.1113) | -0.3534 (-0.6571 ; 0.0241) | -0.8284 (-1.5435 ; 0.0564) | -0.3290 (-0.6279 ; 0.0224) | 0.0516 (-0.0024 ; 0.1441) | -0.1847 (-0.5067 ; 0.0072) |
| -23.250 | -1.8760 (-3.9677 ; 0.1104) | -0.3489 (-0.6398 ; 0.0230) | -0.8178 (-1.5034 ; 0.0538) | -0.3234 (-0.6084 ; 0.0214) | 0.0486 (-0.0024 ; 0.1361) | -0.1825 (-0.5016 ; 0.0073) |
| -23.500 | -1.8648 (-3.9062 ; 0.1097) | -0.3451 (-0.6256 ; 0.0221) | -0.8091 (-1.4702 ; 0.0517) | -0.3187 (-0.5919 ; 0.0205) | 0.0458 (-0.0023 ; 0.1287) | -0.1803 (-0.4963 ; 0.0074) |
| -23.750 | -1.8558 (-3.8530 ; 0.1094) | -0.3420 (-0.6139 ; 0.0214) | -0.8020 (-1.4431 ; 0.0501) | -0.3147 (-0.5780 ; 0.0198) | 0.0433 (-0.0022 ; 0.1218) | -0.1781 (-0.4910 ; 0.0074) |
| -24.000 | -1.8488 (-3.8072 ; 0.1093) | -0.3396 (-0.6044 ; 0.0208) | -0.7962 (-1.4210 ; 0.0487) | -0.3114 (-0.5663 ; 0.0193) | 0.0410 (-0.0021 ; 0.1155) | -0.1761 (-0.4857 ; 0.0073) |
| -24.250 | -1.8433 (-3.7681 ; 0.1094) | -0.3376 (-0.5968 ; 0.0204) | -0.7916 (-1.4034 ; 0.0477) | -0.3087 (-0.5568 ; 0.0188) | 0.0390 (-0.0020 ; 0.1099) | -0.1742 (-0.4807 ; 0.0072) |
| -24.500 | -1.8392 (-3.7353 ; 0.1097) | -0.3360 (-0.5908 ; 0.0200) | -0.7880 (-1.3894 ; 0.0468) | -0.3064 (-0.5489 ; 0.0185) | 0.0372 (-0.0019 ; 0.1050) | -0.1725 (-0.4761 ; 0.0071) |
| -24.750 | -1.8362 (-3.7082 ; 0.1101) | -0.3348 (-0.5862 ; 0.0197) | -0.7851 (-1.3786 ; 0.0462) | -0.3046 (-0.5427 ; 0.0182) | 0.0357 (-0.0018 ; 0.1008) | -0.1710 (-0.4721 ; 0.0070) |
| -25.000 | -1.8341 (-3.6864 ; 0.1105) | -0.3339 (-0.5827 ; 0.0195) | -0.7830 (-1.3704 ; 0.0457) | -0.3032 (-0.5378 ; 0.0179) | 0.0344 (-0.0018 ; 0.0973) | -0.1698 (-0.4686 ; 0.0069) |
| -25.250 | -1.8326 (-3.6697 ; 0.1105) | -0.3332 (-0.5801 ; 0.0193) | -0.7814 (-1.3644 ; 0.0452) | -0.3021 (-0.5342 ; 0.0177) | 0.0335 (-0.0017 ; 0.0946) | -0.1688 (-0.4658 ; 0.0068) |
| -25.500 | -1.8318 (-3.6584 ; 0.1107) | -0.3328 (-0.5784 ; 0.0192) | -0.7804 (-1.3604 ; 0.0449) | -0.3014 (-0.5317 ; 0.0176) | 0.0328 (-0.0016 ; 0.0927) | -0.1681 (-0.4639 ; 0.0067) |
| -25.750 | -1.8313 (-3.6502 ; 0.1094) | -0.3325 (-0.5773 ; 0.0188) | -0.7798 (-1.3579 ; 0.0440) | -0.3010 (-0.5301 ; 0.0172) | 0.0324 (-0.0016 ; 0.0914) | -0.1677 (-0.4623 ; 0.0066) |
| -26.000 | -1.8312 (-3.6502 ; 0.1093) | -0.3324 (-0.5770 ; 0.0188) | -0.7796 (-1.3571 ; 0.0440) | -0.3008 (-0.5297 ; 0.0172) | 0.0322 (-0.0016 ; 0.0912) | -0.1675 (-0.4627 ; 0.0065) |

### TUBE_01

| Cote (m) | G | EAU_P | EAU_A | Q1 | Q3 | A |
|---:|---:|---:|---:|---:|---:|---:|
| 2.600 | -13.0198 (-13.0198 ; -13.0198) | -6.5607 (-6.5607 ; -6.5607) | -15.3877 (-15.3877 ; -15.3877) | -7.6924 (-7.6924 ; -7.6924) | -13.6118 (-13.6118 ; -13.6118) | 10.5102 (10.5102 ; 10.5102) |
| 2.500 | -13.0705 (-13.7253 ; -8.9768) | -6.5674 (-6.9059 ; -4.4602) | -15.3981 (-16.1929 ; -10.4533) | -7.6415 (-8.0439 ; -5.1411) | -13.1888 (-13.9482 ; -8.5488) | 10.2993 (6.8207 ; 10.8524) |
| 2.250 | -13.9155 (-14.4336 ; -12.9292) | -6.9538 (-7.2233 ; -6.4458) | -16.2911 (-16.9236 ; -15.1008) | -7.9495 (-8.2688 ; -7.3457) | -12.9230 (-13.5175 ; -11.8316) | 10.3815 (9.5429 ; 10.8115) |
| 2.000 | -14.5687 (-14.8761 ; -13.9055) | -7.2418 (-7.4029 ; -6.8980) | -16.9530 (-17.3306 ; -16.1500) | -8.1406 (-8.3330 ; -7.7306) | -12.4499 (-12.7701 ; -11.7346) | 10.3015 (9.7460 ; 10.5380) |
| 1.750 | -15.2190 (-15.4471 ; -14.7041) | -7.5292 (-7.6491 ; -7.2590) | -17.6131 (-17.8927 ; -16.9855) | -8.3318 (-8.4778 ; -8.0093) | -11.9953 (-12.2012 ; -11.4559) | 10.2170 (9.7932 ; 10.3781) |
| 1.500 | -15.8629 (-16.0380 ; -15.4774) | -7.8140 (-7.9071 ; -7.6063) | -18.2669 (-18.4822 ; -17.7895) | -8.5210 (-8.6341 ; -8.2744) | -11.5546 (-11.6920 ; -11.1630) | 10.1285 (9.8170 ; 10.2391) |
| 1.250 | -16.4922 (-16.6274 ; -16.1728) | -8.0918 (-8.1650 ; -7.9130) | -18.9042 (-19.0716 ; -18.4987) | -8.7034 (-8.7910 ; -8.4943) | -11.1209 (-11.2228 ; -10.7999) | 10.0303 (9.7744 ; 10.1159) |
| 1.000 | -17.1094 (-17.2205 ; -16.8458) | -8.3635 (-8.4276 ; -8.2076) | -19.5278 (-19.6676 ; -19.1798) | -8.8808 (-8.9524 ; -8.7032) | -10.6986 (-10.7752 ; -10.4328) | 9.9261 (9.7149 ; 9.9915) |
| 0.750 | -17.7116 (-17.8081 ; -17.4911) | -8.6278 (-8.6870 ; -8.4877) | -20.1344 (-20.2600 ; -19.8268) | -9.0519 (-9.1136 ; -8.8977) | -10.2864 (-10.3457 ; -10.0587) | 9.8153 (9.6363 ; 9.8675) |
| 0.500 | -18.2977 (-18.3836 ; -18.1145) | -8.8839 (-8.9401 ; -8.7564) | -20.7222 (-20.8390 ; -20.4468) | -9.2160 (-9.2703 ; -9.0816) | -9.8846 (-9.9394 ; -9.6866) | 9.6985 (9.5450 ; 9.7400) |
| 0.250 | -18.8663 (-18.9465 ; -18.7164) | -9.1308 (-9.1854 ; -9.0139) | -21.2895 (-21.4015 ; -21.0409) | -9.3727 (-9.4213 ; -9.2556) | -9.4930 (-9.5524 ; -9.3191) | 9.5759 (9.4433 ; 9.6076) |
| 0.000 | -19.4158 (-19.4956 ; -19.2975) | -9.3679 (-9.4218 ; -9.2610) | -21.8343 (-21.9445 ; -21.6102) | -9.5213 (-9.5667 ; -9.4200) | -9.1116 (-9.1762 ; -8.9582) | 9.4477 (9.3329 ; 9.4807) |
| -0.250 | -19.9449 (-20.0270 ; -19.8377) | -9.5943 (-9.6482 ; -9.4977) | -22.3549 (-22.4659 ; -22.1546) | -9.6612 (-9.7042 ; -9.5750) | -8.7402 (-8.8104 ; -8.6048) | 9.3142 (9.2149 ; 9.3496) |
| -0.500 | -20.4523 (-20.5387 ; -20.3226) | -9.8095 (-9.8639 ; -9.7217) | -22.8497 (-22.9666 ; -22.6698) | -9.7921 (-9.8349 ; -9.7206) | -8.3787 (-8.4543 ; -8.2592) | 9.1756 (9.0900 ; 9.2132) |
| -0.750 | -20.9366 (-21.0294 ; -20.7819) | -10.0128 (-10.0701 ; -9.9142) | -23.3170 (-23.4414 ; -23.1094) | -9.9133 (-9.9568 ; -9.8515) | -8.0269 (-8.1075 ; -7.9215) | 9.0322 (8.9587 ; 9.0713) |
| -1.000 | -21.3967 (-21.4992 ; -21.2139) | -10.2035 (-10.2644 ; -10.0936) | -23.7553 (-23.8890 ; -23.5184) | -10.0245 (-10.0696 ; -9.9541) | -7.6848 (-7.7695 ; -7.5917) | 8.8842 (8.8214 ; 8.9240) |
| -1.250 | -21.8313 (-21.9506 ; -21.6171) | -10.3811 (-10.4460 ; -10.2591) | -24.1635 (-24.3078 ; -23.8951) | -10.1252 (-10.1728 ; -10.0450) | -7.3521 (-7.4399 ; -7.2697) | 8.7319 (8.6787 ; 8.7715) |
| -1.500 | -22.2394 (-22.3777 ; -21.9902) | -10.5451 (-10.6146 ; -10.4100) | -24.5403 (-24.6965 ; -24.2380) | -10.2150 (-10.2659 ; -10.1237) | -7.0288 (-7.1186 ; -6.9556) | 8.5754 (8.5309 ; 8.6138) |
| -1.750 | -22.6199 (-22.7796 ; -22.3316) | -10.6949 (-10.7696 ; -10.5455) | -24.8845 (-25.0540 ; -24.5457) | -10.2937 (-10.3495 ; -10.1897) | -6.7147 (-6.8054 ; -6.6494) | 8.4150 (8.3785 ; 8.4511) |
| -2.000 | -22.9717 (-23.1612 ; -22.6403) | -10.8301 (-10.9106 ; -10.6651) | -25.1950 (-25.3792 ; -24.8167) | -10.3609 (-10.4247 ; -10.2426) | -6.4097 (-6.5002 ; -6.3510) | 8.2509 (8.2220 ; 8.2837) |
| -2.250 | -23.2940 (-23.5174 ; -22.9148) | -10.9504 (-11.0393 ; -10.7680) | -25.4711 (-25.6762 ; -25.0499) | -10.4163 (-10.4891 ; -10.2821) | -6.1136 (-6.2031 ; -6.0607) | 8.0834 (8.0617 ; 8.1119) |
| -2.500 | -23.5862 (-23.8496 ; -23.1541) | -11.0553 (-11.1554 ; -10.8538) | -25.7117 (-25.9432 ; -25.2439) | -10.4598 (-10.5426 ; -10.3079) | -5.8264 (-5.9139 ; -5.7784) | 7.9127 (7.8972 ; 7.9359) |
| -2.750 | -23.8473 (-24.1580 ; -23.3571) | -11.1445 (-11.2569 ; -10.9220) | -25.9163 (-26.1764 ; -25.3978) | -10.4913 (-10.5880 ; -10.3197) | -5.5478 (-5.6328 ; -5.5041) | 7.7390 (7.7277 ; 7.7559) |
| -3.000 | -24.0767 (-24.4433 ; -23.5227) | -11.2179 (-11.3435 ; -10.9721) | -26.0842 (-26.3754 ; -25.5103) | -10.5104 (-10.6230 ; -10.3172) | -5.2779 (-5.3596 ; -5.2380) | 7.5626 (7.5544 ; 7.5723) |
| -3.250 | -24.2738 (-24.7029 ; -23.6499) | -11.2751 (-11.4189 ; -11.0039) | -26.2149 (-26.5469 ; -25.5808) | -10.5171 (-10.6494 ; -10.3002) | -5.0163 (-5.0944 ; -4.9798) | 7.3836 (7.3779 ; 7.3923) |
| -3.500 | -24.4379 (-24.9346 ; -23.7379) | -11.3161 (-11.4805 ; -11.0171) | -26.3079 (-26.6879 ; -25.6083) | -10.5113 (-10.6669 ; -10.2686) | -4.7631 (-4.8372 ; -4.7297) | 7.2024 (7.1950 ; 7.2197) |
| -3.750 | -24.5687 (-25.1382 ; -23.7857) | -11.3406 (-11.5292 ; -11.0112) | -26.3630 (-26.7972 ; -25.5923) | -10.4929 (-10.6760 ; -10.2221) | -4.5181 (-4.5880 ; -4.4876) | 7.0191 (7.0018 ; 7.0456) |
| -4.000 | -24.6657 (-25.3136 ; -23.7927) | -11.3487 (-11.5658 ; -10.9862) | -26.3800 (-26.8806 ; -25.5321) | -10.4619 (-10.6745 ; -10.1606) | -4.2811 (-4.3467 ; -4.2534) | 6.8339 (6.8060 ; 6.8704) |
| -4.250 | -24.7285 (-25.4606 ; -23.7582) | -11.3402 (-11.5917 ; -10.9419) | -26.3589 (-26.9372 ; -25.4274) | -10.4183 (-10.6624 ; -10.0841) | -4.0521 (-4.1132 ; -4.0270) | 6.6472 (6.6077 ; 6.6944) |
| -4.500 | -24.7571 (-25.5794 ; -23.6816) | -11.3152 (-11.6040 ; -10.8781) | -26.2995 (-26.9646 ; -25.2779) | -10.3621 (-10.6398 ; -9.9924) | -3.8309 (-3.8875 ; -3.8083) | 6.4590 (6.4073 ; 6.5177) |
| -4.750 | -24.7511 (-25.6699 ; -23.5624) | -11.2738 (-11.6021 ; -10.7948) | -26.2020 (-26.9593 ; -25.0832) | -10.2935 (-10.6068 ; -9.8856) | -3.6173 (-3.6695 ; -3.5973) | 6.2698 (6.2048 ; 6.3407) |
| -5.000 | -24.7106 (-25.7322 ; -23.4002) | -11.2160 (-11.5862 ; -10.6920) | -26.0668 (-26.9215 ; -24.8435) | -10.2124 (-10.5635 ; -9.7636) | -3.4113 (-3.4591 ; -3.3937) | 6.0795 (6.0005 ; 6.1635) |
| -5.250 | -24.6355 (-25.7667 ; -23.1946) | -11.1421 (-11.5564 ; -10.5697) | -25.8941 (-26.8517 ; -24.5587) | -10.1190 (-10.5102 ; -9.6265) | -3.2127 (-3.2562 ; -3.1975) | 5.8886 (5.7948 ; 5.9865) |
| -5.500 | -24.5261 (-25.7734 ; -22.9454) | -11.0521 (-11.5130 ; -10.4280) | -25.6843 (-26.7506 ; -24.2290) | -10.0135 (-10.4469 ; -9.4742) | -3.0214 (-3.0607 ; -3.0086) | 5.6972 (5.5877 ; 5.8097) |
| -5.750 | -24.3824 (-25.7528 ; -22.6524) | -10.9464 (-11.4563 ; -10.2671) | -25.4380 (-26.6186 ; -23.8546) | -9.8961 (-10.3739 ; -9.3068) | -2.8373 (-2.8725 ; -2.8261) | 5.5056 (5.3796 ; 5.6334) |
| -6.000 | -24.2048 (-25.7051 ; -22.3156) | -10.8252 (-11.3865 ; -10.0871) | -25.1560 (-26.4565 ; -23.4362) | -9.7670 (-10.2914 ; -9.1244) | -2.6602 (-2.6916 ; -2.6495) | 5.3139 (5.1706 ; 5.4578) |
| -6.250 | -23.9937 (-25.6310 ; -21.9351) | -10.6889 (-11.3042 ; -9.8883) | -24.8388 (-26.2652 ; -22.9741) | -9.6265 (-10.1996 ; -8.9272) | -2.4900 (-2.5177 ; -2.4798) | 5.1224 (4.9611 ; 5.2831) |
| -6.500 | -23.7497 (-25.5308 ; -21.5111) | -10.5378 (-11.2096 ; -9.6710) | -24.4875 (-26.0456 ; -22.4691) | -9.4748 (-10.0987 ; -8.7152) | -2.3266 (-2.3507 ; -2.3168) | 4.9313 (4.7513 ; 5.1095) |
| -6.750 | -23.4731 (-25.4053 ; -21.0440) | -10.3724 (-11.1033 ; -9.4356) | -24.1029 (-25.7987 ; -21.9222) | -9.3123 (-9.9891 ; -8.4888) | -2.1698 (-2.1906 ; -2.1605) | 4.7408 (4.5414 ; 4.9371) |
| -7.000 | -23.1649 (-25.2552 ; -20.5343) | -10.1932 (-10.9857 ; -9.1826) | -23.6862 (-25.5257 ; -21.3344) | -9.1394 (-9.8710 ; -8.2480) | -2.0196 (-2.0372 ; -2.0107) | 4.5513 (4.3317 ; 4.7662) |
| -7.250 | -22.8257 (-25.0813 ; -19.9827) | -10.0005 (-10.8574 ; -8.9125) | -23.2386 (-25.2278 ; -20.7068) | -8.9563 (-9.7447 ; -7.9934) | -1.8758 (-1.8903 ; -1.8672) | 4.3628 (4.1224 ; 4.5968) |
| -7.500 | -22.4566 (-24.8847 ; -19.3902) | -9.7951 (-10.7189 ; -8.6259) | -22.7613 (-24.9064 ; -20.0409) | -8.7637 (-9.6107 ; -7.7251) | -1.7382 (-1.7500 ; -1.7300) | 4.1756 (3.9139 ; 4.4293) |
| -7.750 | -22.0584 (-24.6663 ; -18.7580) | -9.5775 (-10.5709 ; -8.3235) | -22.2557 (-24.5629 ; -19.3384) | -8.5618 (-9.4693 ; -7.4439) | -1.6067 (-1.6159 ; -1.5989) | 3.9899 (3.7064 ; 4.2637) |
| -8.000 | -21.6323 (-24.4275 ; -18.0874) | -9.3484 (-10.4141 ; -8.0061) | -21.7233 (-24.1990 ; -18.6011) | -8.3512 (-9.3211 ; -7.1502) | -1.4813 (-1.4885 ; -1.4738) | 3.8060 (3.5002 ; 4.1002) |
| -8.250 | -21.1797 (-24.1696 ; -17.3803) | -9.1083 (-10.2492 ; -7.6747) | -21.1658 (-23.8162 ; -17.8311) | -8.1325 (-9.1667 ; -6.8449) | -1.3618 (-1.3703 ; -1.3546) | 3.6241 (3.2955 ; 3.9391) |
| -8.500 | -20.7017 (-23.8941 ; -16.6387) | -8.8582 (-10.0770 ; -7.3302) | -20.5847 (-23.4165 ; -17.0307) | -7.9061 (-9.0068 ; -6.5288) | -1.2480 (-1.2577 ; -1.2412) | 3.4444 (3.0928 ; 3.7804) |
| -8.750 | -20.1998 (-23.6027 ; -15.8651) | -8.5987 (-9.8982 ; -6.9737) | -19.9820 (-23.0016 ; -16.2026) | -7.6727 (-8.8420 ; -6.2030) | -1.1398 (-1.1505 ; -1.1333) | 3.2671 (2.8924 ; 3.6244) |
| -9.000 | -19.6758 (-23.2973 ; -15.0622) | -8.3307 (-9.7138 ; -6.6067) | -19.3595 (-22.5736 ; -15.3499) | -7.4331 (-8.6739 ; -5.8687) | -1.0372 (-1.0485 ; -1.0310) | 3.0924 (2.6945 ; 3.4713) |
| -9.250 | -19.1312 (-22.9798 ; -14.2335) | -8.0551 (-9.5246 ; -6.2304) | -18.7193 (-22.1345 ; -14.4757) | -7.1876 (-8.5026 ; -5.5271) | -0.9399 (-0.9517 ; -0.9341) | 2.9206 (2.4996 ; 3.3211) |
| -9.500 | -18.5678 (-22.6517 ; -13.3826) | -7.7727 (-9.3315 ; -5.8466) | -18.0633 (-21.6862 ; -13.5839) | -6.9368 (-8.3282 ; -5.1798) | -0.8479 (-0.8598 ; -0.8425) | 2.7519 (2.3080 ; 3.1741) |
| -9.750 | -17.9876 (-22.3152 ; -12.5138) | -7.4845 (-9.1353 ; -5.4569) | -17.3939 (-21.2309 ; -12.6785) | -6.6815 (-8.1525 ; -4.8283) | -0.7609 (-0.7727 ; -0.7555) | 2.5865 (2.1202 ; 3.0303) |
| -10.000 | -17.3925 (-21.9721 ; -11.6318) | -7.1915 (-8.9369 ; -5.0633) | -16.7133 (-20.7703 ; -11.7642) | -6.4226 (-7.9758 ; -4.4745) | -0.6790 (-0.6903 ; -0.6725) | 2.4247 (1.9366 ; 2.8899) |
| -10.250 | -16.7848 (-21.6238 ; -10.7424) | -6.8947 (-8.7369 ; -4.6682) | -16.0240 (-20.3060 ; -10.8461) | -6.1608 (-7.7990 ; -4.1204) | -0.6019 (-0.6124 ; -0.5946) | 2.2665 (1.7576 ; 2.7530) |
| -10.500 | -16.1668 (-21.2717 ; -9.8518) | -6.5952 (-8.5359 ; -4.2739) | -15.3283 (-19.8396 ; -9.9301) | -5.8970 (-7.6225 ; -3.7682) | -0.5296 (-0.5389 ; -0.5216) | 2.1124 (1.5839 ; 2.6196) |
| -10.750 | -15.5408 (-20.9163 ; -8.9674) | -6.2940 (-8.3344 ; -3.8835) | -14.6289 (-19.3718 ; -9.0230) | -5.6321 (-7.4465 ; -3.4205) | -0.4618 (-0.4695 ; -0.4533) | 1.9624 (1.4162 ; 2.4897) |
| -11.000 | -14.9095 (-20.5580 ; -8.0979) | -5.9925 (-8.1324 ; -3.5003) | -13.9284 (-18.9031 ; -8.1327) | -5.3671 (-7.2711 ; -3.0803) | -0.3985 (-0.4041 ; -0.3899) | 1.8169 (1.2550 ; 2.3632) |
| -11.250 | -14.2754 (-20.1959 ; -7.2531) | -5.6916 (-7.9300 ; -3.1282) | -13.2296 (-18.4331 ; -7.2681) | -5.1029 (-7.0959 ; -2.7508) | -0.3396 (-0.3428 ; -0.3311) | 1.6760 (1.1014 ; 2.2400) |
| -11.500 | -13.6411 (-19.8288 ; -6.4434) | -5.3927 (-7.7266 ; -2.7712) | -12.5352 (-17.9611 ; -6.4388) | -4.8405 (-6.9207 ; -2.4357) | -0.2849 (-0.2895 ; -0.2770) | 1.5399 (0.9562 ; 2.1199) |
| -11.750 | -13.0109 (-19.4551 ; -5.6830) | -5.0973 (-7.5218 ; -2.4353) | -11.8492 (-17.4858 ; -5.6583) | -4.5813 (-6.7446 ; -2.1400) | -0.2343 (-0.2404 ; -0.2278) | 1.4090 (0.8210 ; 2.0026) |
| -12.000 | -12.3798 (-19.0729 ; -4.9511) | -4.8037 (-7.3151 ; -2.1116) | -11.1672 (-17.0060 ; -4.9063) | -4.3237 (-6.5671 ; -1.8558) | -0.1875 (-0.1953 ; -0.1796) | 1.2826 (0.6927 ; 1.8880) |
| -12.250 | -11.7633 (-18.6802 ; -4.2751) | -4.5182 (-7.1059 ; -1.8133) | -10.5040 (-16.5203 ; -4.2132) | -4.0732 (-6.3875 ; -1.5942) | -0.1447 (-0.1544 ; -0.1320) | 1.1625 (0.5765 ; 1.7757) |
| -12.500 | -11.1721 (-18.2755 ; -3.6645) | -4.2451 (-6.8936 ; -1.5455) | -9.8697 (-16.0276 ; -3.5911) | -3.8337 (-6.2052 ; -1.3592) | -0.1059 (-0.1178 ; -0.0874) | 1.0496 (0.4743 ; 1.6656) |
| -12.750 | -10.6007 (-17.8570 ; -3.0951) | -3.9823 (-6.6779 ; -1.2981) | -9.2591 (-15.5267 ; -3.0162) | -3.6031 (-6.0197 ; -1.1420) | -0.0708 (-0.0853 ; -0.0459) | 0.9431 (0.3825 ; 1.5575) |
| -13.000 | -10.0513 (-17.4234 ; -2.5731) | -3.7305 (-6.4583 ; -1.0733) | -8.6742 (-15.0168 ; -2.4939) | -3.3821 (-5.8305 ; -0.9443) | -0.0392 (-0.0575 ; -0.0072) | 0.8431 (0.3013 ; 1.4512) |
| -13.250 | -9.5246 (-16.9742 ; -2.0991) | -3.4901 (-6.2346 ; -0.8710) | -8.1158 (-14.4976 ; -2.0240) | -3.1711 (-5.6375 ; -0.7663) | -0.0108 (-0.0345 ; 0.0288) | 0.7495 (0.2303 ; 1.3465) |
| -13.500 | -9.0210 (-16.5093 ; -1.6728) | -3.2612 (-6.0071 ; -0.6909) | -7.5840 (-13.9694 ; -1.6053) | -2.9701 (-5.4406 ; -0.6075) | 0.0144 (-0.0166 ; 0.0621) | 0.6619 (0.1688 ; 1.2435) |
| -13.750 | -8.5407 (-16.0296 ; -1.2925) | -3.0438 (-5.7762 ; -0.5317) | -7.0792 (-13.4332 ; -1.2355) | -2.7791 (-5.2403 ; -0.4671) | 0.0367 (-0.0029 ; 0.0928) | 0.5804 (0.1162 ; 1.1421) |
| -14.000 | -8.0835 (-15.5369 ; -0.9554) | -2.8380 (-5.5425 ; -0.3922) | -6.6010 (-12.8906 ; -0.9112) | -2.5980 (-5.0370 ; -0.3438) | 0.0564 (0.0079 ; 0.1211) | 0.5047 (0.0716 ; 1.0425) |
| -14.250 | -7.6493 (-15.0332 ; -0.6585) | -2.6435 (-5.3070 ; -0.2707) | -6.1492 (-12.3436 ; -0.6290) | -2.4268 (-4.8316 ; -0.2363) | 0.0735 (0.0164 ; 0.1469) | 0.4345 (0.0343 ; 0.9448) |
| -14.500 | -7.2376 (-14.5214 ; -0.3987) | -2.4602 (-5.0705 ; -0.1658) | -5.7234 (-11.7946 ; -0.3852) | -2.2652 (-4.6249 ; -0.1432) | 0.0883 (0.0227 ; 0.1704) | 0.3697 (0.0035 ; 0.8492) |
| -14.750 | -6.8478 (-14.0044 ; -0.1730) | -2.2878 (-4.8343 ; -0.0760) | -5.3229 (-11.2460 ; -0.1764) | -2.1130 (-4.4179 ; -0.0634) | 0.1009 (0.0272 ; 0.1916) | 0.3099 (-0.0214 ; 0.7557) |
| -15.000 | -6.4794 (-13.4853 ; 0.0213) | -2.1260 (-4.5993 ; 0.0002) | -4.9470 (-10.7002 ; 0.0006) | -1.9699 (-4.2115 ; 0.0045) | 0.1116 (0.0302 ; 0.2107) | 0.2550 (-0.0412 ; 0.6647) |
| -15.250 | -6.1315 (-12.9672 ; 0.1867) | -1.9745 (-4.3667 ; 0.0639) | -4.5951 (-10.1599 ; 0.1486) | -1.8357 (-4.0068 ; 0.0613) | 0.1204 (0.0320 ; 0.2276) | 0.2047 (-0.0562 ; 0.5763) |
| -15.500 | -5.8034 (-12.4533 ; 0.3250) | -1.8329 (-4.1373 ; 0.1161) | -4.2661 (-9.6273 ; 0.2701) | -1.7099 (-3.8046 ; 0.1081) | 0.1275 (0.0328 ; 0.2425) | 0.1587 (-0.0672 ; 0.4908) |
| -15.750 | -5.4942 (-11.9467 ; 0.4377) | -1.7008 (-3.9122 ; 0.1579) | -3.9593 (-9.1045 ; 0.3672) | -1.5923 (-3.6058 ; 0.1456) | 0.1331 (0.0327 ; 0.2555) | 0.1169 (-0.0745 ; 0.4082) |
| -16.000 | -5.2032 (-11.4502 ; 0.5260) | -1.5778 (-3.6922 ; 0.1900) | -3.6736 (-8.5935 ; 0.4418) | -1.4825 (-3.4112 ; 0.1744) | 0.1373 (0.0318 ; 0.2666) | 0.0789 (-0.0787 ; 0.3288) |
| -16.250 | -4.9295 (-10.9666 ; 0.5907) | -1.4636 (-3.4780 ; 0.2130) | -3.4082 (-8.0960 ; 0.4953) | -1.3801 (-3.2216 ; 0.1951) | 0.1403 (0.0305 ; 0.2760) | 0.0446 (-0.0801 ; 0.2529) |
| -16.500 | -4.6721 (-10.4981 ; 0.6324) | -1.3577 (-3.2703 ; 0.2275) | -3.1621 (-7.6136 ; 0.5290) | -1.2848 (-3.0374 ; 0.2081) | 0.1421 (0.0287 ; 0.2838) | 0.0137 (-0.0807 ; 0.1807) |
| -16.750 | -4.4304 (-10.0470 ; 0.6518) | -1.2596 (-3.0697 ; 0.2341) | -2.9343 (-7.1477 ; 0.5444) | -1.1963 (-2.8595 ; 0.2138) | 0.1429 (0.0265 ; 0.2900) | -0.0140 (-0.0818 ; 0.1124) |
| -17.000 | -4.2036 (-9.6148 ; 0.6498) | -1.1690 (-2.8769 ; 0.2335) | -2.7239 (-6.7000 ; 0.5430) | -1.1140 (-2.6882 ; 0.2130) | 0.1428 (0.0241 ; 0.2947) | -0.0388 (-0.0837 ; 0.0483) |
| -17.250 | -3.9907 (-9.2028 ; 0.6278) | -1.0855 (-2.6925 ; 0.2266) | -2.5299 (-6.2718 ; 0.5269) | -1.0379 (-2.5243 ; 0.2062) | 0.1419 (0.0217 ; 0.2979) | -0.0607 (-0.0871 ; -0.0116) |
| -17.500 | -3.7910 (-8.8113 ; 0.5877) | -1.0087 (-2.5171 ; 0.2142) | -2.3514 (-5.8644 ; 0.4981) | -0.9674 (-2.3681 ; 0.1944) | 0.1403 (0.0194 ; 0.2996) | -0.0801 (-0.0933 ; -0.0622) |
| -17.750 | -3.6042 (-8.4412 ; 0.5324) | -0.9381 (-2.3511 ; 0.1976) | -2.1873 (-5.4787 ; 0.4594) | -0.9022 (-2.2200 ; 0.1785) | 0.1381 (0.0174 ; 0.2999) | -0.0972 (-0.1186 ; -0.0563) |
| -18.000 | -3.4268 (-8.0854 ; 0.4633) | -0.8731 (-2.1944 ; 0.1767) | -2.0364 (-5.1149 ; 0.4110) | -0.8417 (-2.0795 ; 0.1588) | 0.1353 (0.0155 ; 0.2987) | -0.1121 (-0.1659 ; -0.0499) |
| -18.250 | -3.2618 (-7.7484 ; 0.3949) | -0.8140 (-2.0471 ; 0.1559) | -1.8989 (-4.7728 ; 0.3625) | -0.7862 (-1.9471 ; 0.1391) | 0.1320 (0.0138 ; 0.2963) | -0.1248 (-0.2094 ; -0.0436) |
| -18.500 | -3.1111 (-7.4349 ; 0.3375) | -0.7599 (-1.9091 ; 0.1382) | -1.7734 (-4.4522 ; 0.3213) | -0.7354 (-1.8228 ; 0.1224) | 0.1284 (0.0123 ; 0.2928) | -0.1359 (-0.2490 ; -0.0376) |
| -18.750 | -2.9717 (-7.1367 ; 0.2901) | -0.7107 (-1.7800 ; 0.1228) | -1.6589 (-4.1522 ; 0.2855) | -0.6887 (-1.7058 ; 0.1080) | 0.1246 (0.0107 ; 0.2882) | -0.1453 (-0.2851 ; -0.0316) |
| -19.000 | -2.8435 (-6.8529 ; 0.2520) | -0.6659 (-1.6591 ; 0.1096) | -1.5548 (-3.8716 ; 0.2548) | -0.6459 (-1.5958 ; 0.0959) | 0.1205 (0.0092 ; 0.2828) | -0.1532 (-0.3176 ; -0.0259) |
| -19.250 | -2.7258 (-6.5817 ; 0.2218) | -0.6253 (-1.5460 ; 0.0980) | -1.4603 (-3.6087 ; 0.2279) | -0.6069 (-1.4921 ; 0.0854) | 0.1161 (0.0077 ; 0.2766) | -0.1598 (-0.3466 ; -0.0205) |
| -19.500 | -2.6182 (-6.3220 ; 0.1979) | -0.5885 (-1.4401 ; 0.0877) | -1.3750 (-3.3627 ; 0.2039) | -0.5714 (-1.3945 ; 0.0762) | 0.1117 (0.0062 ; 0.2698) | -0.1651 (-0.3720 ; -0.0157) |
| -19.750 | -2.5203 (-6.0738 ; 0.1791) | -0.5554 (-1.3413 ; 0.0784) | -1.2980 (-3.1334 ; 0.1824) | -0.5390 (-1.3027 ; 0.0681) | 0.1072 (0.0048 ; 0.2625) | -0.1693 (-0.3939 ; -0.0115) |
| -20.000 | -2.4313 (-5.8373 ; 0.1644) | -0.5256 (-1.2498 ; 0.0701) | -1.2288 (-2.9207 ; 0.1630) | -0.5098 (-1.2168 ; 0.0609) | 0.1026 (0.0035 ; 0.2546) | -0.1724 (-0.4122 ; -0.0079) |
| -20.250 | -2.3510 (-5.6131 ; 0.1530) | -0.4990 (-1.1654 ; 0.0626) | -1.1669 (-2.7246 ; 0.1457) | -0.4833 (-1.1370 ; 0.0546) | 0.0979 (0.0022 ; 0.2463) | -0.1747 (-0.4273 ; -0.0049) |
| -20.500 | -2.2787 (-5.4021 ; 0.1442) | -0.4753 (-1.0882 ; 0.0560) | -1.1117 (-2.5453 ; 0.1305) | -0.4595 (-1.0633 ; 0.0491) | 0.0933 (0.0012 ; 0.2376) | -0.1761 (-0.4392 ; -0.0023) |
| -20.750 | -2.2141 (-5.2046 ; 0.1372) | -0.4542 (-1.0181 ; 0.0503) | -1.0628 (-2.3824 ; 0.1171) | -0.4382 (-0.9957 ; 0.0443) | 0.0887 (0.0002 ; 0.2286) | -0.1769 (-0.4483 ; -0.0002) |
| -21.000 | -2.1565 (-5.0213 ; 0.1317) | -0.4356 (-0.9549 ; 0.0452) | -1.0195 (-2.2357 ; 0.1054) | -0.4191 (-0.9342 ; 0.0401) | 0.0842 (-0.0005 ; 0.2192) | -0.1770 (-0.4547 ; 0.0015) |
| -21.250 | -2.1056 (-4.8521 ; 0.1273) | -0.4192 (-0.8984 ; 0.0409) | -0.9814 (-2.1044 ; 0.0953) | -0.4021 (-0.8784 ; 0.0365) | 0.0798 (-0.0011 ; 0.2097) | -0.1766 (-0.4589 ; 0.0028) |
| -21.500 | -2.0607 (-4.6971 ; 0.1236) | -0.4049 (-0.8483 ; 0.0372) | -0.9481 (-1.9879 ; 0.0867) | -0.3870 (-0.8284 ; 0.0335) | 0.0755 (-0.0016 ; 0.2001) | -0.1757 (-0.4610 ; 0.0039) |
| -21.750 | -2.0216 (-4.5561 ; 0.1206) | -0.3924 (-0.8041 ; 0.0340) | -0.9192 (-1.8853 ; 0.0793) | -0.3736 (-0.7837 ; 0.0308) | 0.0713 (-0.0020 ; 0.1905) | -0.1745 (-0.4613 ; 0.0047) |
| -22.000 | -1.9876 (-4.4286 ; 0.1181) | -0.3816 (-0.7656 ; 0.0313) | -0.8941 (-1.7957 ; 0.0730) | -0.3619 (-0.7441 ; 0.0285) | 0.0673 (-0.0022 ; 0.1810) | -0.1729 (-0.4601 ; 0.0053) |
| -22.250 | -1.9583 (-4.3140 ; 0.1159) | -0.3724 (-0.7322 ; 0.0290) | -0.8726 (-1.7181 ; 0.0677) | -0.3517 (-0.7093 ; 0.0266) | 0.0634 (-0.0024 ; 0.1716) | -0.1711 (-0.4577 ; 0.0058) |
| -22.500 | -1.9332 (-4.2117 ; 0.1141) | -0.3645 (-0.7035 ; 0.0271) | -0.8542 (-1.6514 ; 0.0632) | -0.3427 (-0.6788 ; 0.0250) | 0.0597 (-0.0024 ; 0.1625) | -0.1692 (-0.4542 ; 0.0061) |
| -22.750 | -1.9120 (-4.1209 ; 0.1125) | -0.3578 (-0.6791 ; 0.0255) | -0.8386 (-1.5946 ; 0.0595) | -0.3350 (-0.6524 ; 0.0236) | 0.0563 (-0.0025 ; 0.1537) | -0.1671 (-0.4501 ; 0.0063) |
| -23.000 | -1.8942 (-4.0407 ; 0.1113) | -0.3521 (-0.6584 ; 0.0241) | -0.8255 (-1.5467 ; 0.0564) | -0.3283 (-0.6296 ; 0.0224) | 0.0530 (-0.0025 ; 0.1453) | -0.1649 (-0.4453 ; 0.0064) |
| -23.250 | -1.8795 (-3.9703 ; 0.1104) | -0.3474 (-0.6412 ; 0.0230) | -0.8146 (-1.5066 ; 0.0539) | -0.3226 (-0.6101 ; 0.0214) | 0.0500 (-0.0024 ; 0.1374) | -0.1628 (-0.4403 ; 0.0065) |
| -23.500 | -1.8674 (-3.9089 ; 0.1098) | -0.3436 (-0.6270 ; 0.0221) | -0.8056 (-1.4735 ; 0.0518) | -0.3178 (-0.5935 ; 0.0206) | 0.0471 (-0.0023 ; 0.1300) | -0.1606 (-0.4350 ; 0.0064) |
| -23.750 | -1.8576 (-3.8556 ; 0.1094) | -0.3404 (-0.6153 ; 0.0214) | -0.7982 (-1.4463 ; 0.0501) | -0.3136 (-0.5796 ; 0.0199) | 0.0446 (-0.0022 ; 0.1231) | -0.1586 (-0.4298 ; 0.0064) |
| -24.000 | -1.8498 (-3.8098 ; 0.1093) | -0.3378 (-0.6058 ; 0.0208) | -0.7922 (-1.4243 ; 0.0488) | -0.3102 (-0.5680 ; 0.0193) | 0.0423 (-0.0021 ; 0.1169) | -0.1567 (-0.4248 ; 0.0063) |
| -24.250 | -1.8436 (-3.7708 ; 0.1095) | -0.3357 (-0.5982 ; 0.0204) | -0.7874 (-1.4066 ; 0.0477) | -0.3074 (-0.5584 ; 0.0189) | 0.0402 (-0.0020 ; 0.1113) | -0.1549 (-0.4200 ; 0.0062) |
| -24.500 | -1.8389 (-3.7379 ; 0.1098) | -0.3341 (-0.5922 ; 0.0200) | -0.7836 (-1.3926 ; 0.0469) | -0.3050 (-0.5506 ; 0.0185) | 0.0384 (-0.0020 ; 0.1064) | -0.1533 (-0.4157 ; 0.0061) |
| -24.750 | -1.8354 (-3.7108 ; 0.1102) | -0.3328 (-0.5876 ; 0.0198) | -0.7806 (-1.3818 ; 0.0462) | -0.3032 (-0.5443 ; 0.0182) | 0.0369 (-0.0019 ; 0.1022) | -0.1519 (-0.4118 ; 0.0060) |
| -25.000 | -1.8328 (-3.6890 ; 0.1105) | -0.3319 (-0.5840 ; 0.0195) | -0.7784 (-1.3736 ; 0.0457) | -0.3017 (-0.5394 ; 0.0179) | 0.0356 (-0.0018 ; 0.0988) | -0.1507 (-0.4086 ; 0.0059) |
| -25.250 | -1.8311 (-3.6723 ; 0.1105) | -0.3312 (-0.5814 ; 0.0193) | -0.7768 (-1.3676 ; 0.0452) | -0.3006 (-0.5358 ; 0.0177) | 0.0346 (-0.0017 ; 0.0961) | -0.1498 (-0.4060 ; 0.0058) |
| -25.500 | -1.8300 (-3.6610 ; 0.1107) | -0.3307 (-0.5797 ; 0.0192) | -0.7757 (-1.3635 ; 0.0449) | -0.2999 (-0.5333 ; 0.0176) | 0.0339 (-0.0017 ; 0.0941) | -0.1491 (-0.4042 ; 0.0057) |
| -25.750 | -1.8293 (-3.6528 ; 0.1094) | -0.3305 (-0.5787 ; 0.0188) | -0.7751 (-1.3611 ; 0.0441) | -0.2994 (-0.5317 ; 0.0172) | 0.0335 (-0.0016 ; 0.0929) | -0.1487 (-0.4027 ; 0.0056) |
| -26.000 | -1.8293 (-3.6528 ; 0.1093) | -0.3304 (-0.5783 ; 0.0188) | -0.7749 (-1.3603 ; 0.0441) | -0.2993 (-0.5313 ; 0.0172) | 0.0334 (-0.0016 ; 0.0927) | -0.1486 (-0.4030 ; 0.0055) |

## Figures

Aucune figure : la bibliothèque de tracé (`matplotlib`) n'est pas disponible dans l'environnement du projet ; les profils sont donnés en tableaux ci-dessus.

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

