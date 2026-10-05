# Annexe B de la consigne du lot 47 — données du modèle source

Recopiée à l'identique de la consigne de MM (lot 47). Seules les valeurs
numériques du modèle source sont versées : aucun document source, aucune figure,
aucun extrait de texte (décision de confidentialité de MM). Chaque valeur des
données du projet cite sa source sous la forme « référence externe, tableau ou
figure n° » : ici, le tableau B1 à B6 de cette annexe, qui transcrit le modèle
source.

## Annexe B — Données (à verser dans le projet)

### B1. Géométrie

- Tablier : dalle d'épaisseur 0,40 m, largeur 6,00 m, longueur 31,20 m, plan
  moyen à +1,30 m NGF. Les pentes sont négligées : la face supérieure est à
  +1,50 m.
- Files de pieux 1 à 7 : X = 0,60 + 5,00·(i − 1) m, depuis l'about.
- Deux pieux par file, en Y = ±2,00 m depuis l'axe du tablier.
- Chevêtres : 7, un par file, transversaux, longueur 6,00 m, section
  1,20 × 0,90 m.
- Pieux : tube Ø660 × 19 mm, S355, pointe à −13,00 m NGF. Ils sont reliés au
  chevêtre au nœud du plan moyen.
- Profil en travers :
  - voie centrale de 3,00 m (Y de −1,50 à +1,50) ;
  - deux trottoirs de 1,50 m ;
  - garde-corps en rive (Y = ±3,00).

### B2. Sections des pieux (corrodées, 50 ans)

| Niveaux (m NGF) | A (cm²) | I (cm⁴) | I/v (cm³) |
|---|---|---|---|
| nœud du tablier à +0,70 | 305,30 | 155 063 | 4 752,9 |
| +0,70 à 0,0 | 305,30 | 155 063 | 4 752,9 |
| 0,0 à −0,80 | 346,43 | 177 083 | 5 394,8 |
| −0,80 à −2,25 | 312,13 | 160 406 | 4 886,7 |
| −2,25 à −13,00 | 358,45 | 184 242 | 5 593,3 |

### B3. Ressorts horizontaux nodaux (kx = ky, kN/m, un nœud tous les 0,50 m)

**Files 1 et 7** (crête de talus) :

| Cote (m NGF) | k (kN/m) |
|---|---|
| +1,00 | 3 500 |
| +0,50 | 8 300 |
| 0,00 | 9 700 |
| −0,50 | 11 000 |
| −1,00 | 12 300 |
| −1,50 | 13 600 |
| −2,00 et −2,50 | 14 000 |
| −3,00 à −6,00 | 3 400 |
| −6,50 à −12,50 | 21 200 |
| −13,00 | 10 600 |

**Files 2 à 6** (dans l'eau) :

| Cote (m NGF) | k (kN/m) |
|---|---|
| −2,00 | 900 |
| −2,50 | 2 400 |
| −3,00 | 3 000 |
| −3,50 à −6,00 | 3 400 |
| −6,50 à −12,50 | 21 200 |
| −13,00 | 10 600 |

### B4. Charges (cas élémentaires)

| Cas | Définition |
|---|---|
| PP | Poids propre automatique, avec les poids volumiques de E7 |
| G2 | Trottoirs 8,08 kPa ; voie 2,28 kPa ; garde-corps 0,50 kN/m sur chaque rive |
| TS | 4 roues de 135 kN, empreinte 0,40 × 0,40 m. Essieux à 1,20 m d'entraxe, roues à 2,00 m d'entraxe transversal. Position « axé » : roues à Y = ±1,00. Position « bord de voie » : roue la plus excentrée tangente au bord de la voie, à déduire. |
| UDL | 6,30 kPa sur la voie, sur toute la longueur |
| TR | 5,0 kPa sur les deux trottoirs, sur toute la longueur |
| LM1 | TS + UDL + TR, enveloppe sur les positions de TS |
| LM2 | 2 roues de 160 kN, empreinte 0,35 × 0,60 m (0,35 m selon X), à 2,00 m d'entraxe ; enveloppe sur les positions |
| LM3 | Non modélisé : les dimensions des patins manquent. C13 se limite donc à LM1 et LM2 pour la grue. |
| FR | 381 kN selon X, réparti sur la surface de la voie |
| TE+ / TE− | ΔT = ±27,5 °C sur la dalle et les chevêtres |

### B5. Combinaisons du modèle source

| N° | ELS f | ELS c | ELU+ (G = 1,35) / ELU− (G = 1,00) |
|---|---|---|---|
| 100 | G + 0,5 TR | G + TR | γG G + 1,5 TR |
| 101 | G + 0,5 FR | G + FR | γG G + 1,5 FR |
| 102 / 109 | G + 0,5 LM1 | G + LM1 | γG G + 1,5 LM1 |
| 103 / 110 | G + 0,5 LM1 + 0,3 FR | G + LM1 + 0,7 FR | γG G + 1,5 LM1 + 1,05 FR |
| 104 / 111 | idem 103 + 0,5 TE+ | idem 103 + 0,6 TE+ | idem 103 + 0,9 TE+ |
| 105 / 112 | idem 103 + 0,5 TE− | idem 103 + 0,6 TE− | idem 103 + 0,9 TE− |
| 106 / 113 | G + 0,3 LM1 + 0,5 FR | G + 0,7 LM1 + FR | γG G + 1,05 LM1 + 1,5 FR |
| 107 / 114 | idem 106 + 0,5 TE+ | idem 106 + 0,6 TE+ | idem 106 + 0,9 TE+ |
| 108 / 115 | idem 106 + 0,5 TE− | idem 106 + 0,6 TE− | idem 106 + 0,9 TE− |

G = PP + G2. Les combinaisons 102 à 108 ont le TS « axé », les combinaisons
109 à 115 le TS en « bord de voie ».

### B6. Points de comparaison (valeurs du modèle source)

| N° | Grandeur | ELS f | ELS c | ELU | Comb. |
|---|---|---|---|---|---|
| C1 | Déplacement maximal | — | 0,5 cm | — | 107 |
| C2 | N max en tête de pieu (kN) | 514 | 727 | 1 048 | 112 |
| C3 | M dans le bouchon (kN·m), max / min | 155 / −209 | 186 / −312 | 260 / −449 | 111 |
| C4 | V dans le bouchon, ELU (kN) | — | — | 253 | 114 |
| C5 | M dans le pieu, ELU (kN·m), max / min | — | — | 273 / −463 | 111 |
| C6 | M en travée du chevêtre (kN·m) | 180 | 276 | 408 | 105 / 112 |
| C7 | M sur appui du chevêtre, ELU (kN·m) | — | — | −177 | — |
| C8 | V dans le chevêtre, ELU (kN), max / min | — | — | 620 / −653 | 105 / 112 |
| C9 | Mxx de la dalle en chapeau (kN·m/m) | 79 | 118 | 174 | 111 |
| C10 | Mxx de la dalle en travée (kN·m/m) | 82 | 134 | 198 | 112 |
| C11 | Nxx de la dalle (kN/m) : FR seul / TE− seul | 18,9 / 64,1 | | | cas élém. |
| C12 | Qxx de la dalle, ELU (kN/m) : courant / rive | — | — | 320 / 568 | 111 / 100 |
| C13 | Enveloppes non pondérées de la dalle : Mxx inf. / Mxx sup. / V | LM1 : 85 / −47 / 154 ; LM2 : 64 / −30 / 138 | | | élém. |

Valeurs dont la source est incohérente, à commenter sans les arbitrer :

- C2 : la même source donne aussi 554, 767 et 1 102 kN ;
- C1 : valeur arrondie au demi-centimètre.
