# Lot 50 ter — compte rendu (PONTONS-ALU-01 : export pour l'EC9, les vues et les plans)

Profil `vm`, branche `lot-50ter`. Lot d'export seulement : aucun maillage, aucune exécution
Code_Aster, aucune modification des résultats du lot 50 bis ni des autres projets. Source :
exécution de référence du lot 50 bis `20261012T144404-2cf50a46` (P24, P25, MP1200, k = 1), `.comm`
sha256 `5964ae42…b262`, MED des résultats des livrables sha256 `f7f89e4c…26d9c`.

## Fichiers déposés (`/media/sf_partage/echanges/lot50ter/pontons_alu_01/`)

Format commun : `;`, point décimal, UTF-8 sans BOM, SI (N, N·m, m, Pa), une ligne `#` en tête
(source et empreintes, unités, conventions). Lignes : données (total avec la ligne `#` et l'en-tête).

| Fichier | Lignes | sha256 |
|---|---|---|
| `noeuds.csv` | 416 (418) | `3c6342d664cec23d1f8806b46a68fc68e16b0523ee2179c7e854104c3d4eca01` |
| `elements.csv` | 378 (380) : 324 barres, 51 LIAISON_SOLIDE, 3 articulations | `52e2136ab3a80916653dea4eb9fcdf1fd94bac0069b0fa4f3760cc5f9d784089` |
| `membres.csv` | 117 (119) | `2944fe75d3ec56c5a77b652f4136ef0871946a71560a5cb3f2323a80c8559f18` |
| `efforts_elementaires.csv` | 9 984 (9 986) : 16 cas × 312 éléments × 2 extrémités | `47bb107d8ac7d9138c7858235d3cb54e80b0e30f636c4d5268cfed018123486c` |
| `deplacements_elementaires.csv` | 6 656 (6 658) : 16 cas × 416 nœuds | `e429ad584fe734afb9794aa80c131c594ea192835b31f323a7c93de828c3d4f8` |
| `reactions_elementaires.csv` | 48 (50) : 16 cas × (2 rotules + ressorts cumulés) | `b89263cc8d613e4e1acc6bebaca5a0596ee46eb21d19878bf41eb8f8234286a8` |
| `combinaisons.csv` | 5 004 (5 006) : B 3 402, B′ 1 602 | `0a43e148d526816889b6c3b069733c507f93afadbe34716bd159f8e0762545f3` |
| `charges.csv` | 41 (43) | `aaf126ab45609dddf557dcfa523020acdcbbe34e6af2f8e74d60fca86a72d800` |
| `sections.csv` | 49 (51) | `762d930597675ccb2fbe20fe4016209d99fff8a6f177c5b05a18157e7a55932c` |
| `recombiner.py` | script, bibliothèque standard seule | `9feda32b651700fc680037bd48d2b7f7b2fd23acb58990d9f407e4833be3f66c` |

`empreintes.sha256` les reprend (`sha256sum -c` : 10 OK). Les nombres sont écrits avec
17 chiffres significatifs ; les coordonnées et longueurs sont recalées sur la grille de 1 mm de
`config/arrondis.yaml` quand l'écart est du bruit binaire (< 10⁻⁶ m), les efforts jamais arrondis.

Cas : les 16 du lot 50 bis, noms Code_Aster (correspondance en tête des fichiers) : G1, G2, Q,
QD = Q½, HU/HD = houle de 1 kPa, AMM/AMP = AM∓, ACM/ACP = AC∓, AAM/AAP = ACA∓, TP/TM = T±, et
TAP/TAM = TA± (encore présents). Les facteurs de `combinaisons.csv` comprennent l'échelle de la
houle (5 kPa : facteur 7,5 en dominante ELU).

## Contrôle de recombinaison

Critère écrit avant l'export (`docs/essais_lot50ter.md` § 1) : 10⁻⁶ en relatif sur les valeurs non
arrondies du lot 50 bis. **Réussi** (`recombiner.py`, rejoué aussi depuis le partage par
`python -I -S`) :

- \|MFY\| max des poutres principales, ELU B : 53 217,469 N·m (53,2175 kN·m), écart 1,4·10⁻¹⁶ ;
  élément 79 (PP_YM, X = 3,75 m), B_ELU_G1.2_HD_TM_AMP_ACP_Q ;
- N min des pannes, ELU B : −85 649,607 N (−85,6 kN), écart 0 ; élément 334 (PANNE_4),
  B_ELU_G1.2_HD_TM_AMM_ACP_Q ;
- N min de SUP_1, ELU B : −58 007,693 N (−58,0 kN), écart 0 ; élément 349 (pied),
  B_ELU_G1.2_TP_HD_AMM_ACP_Q.

## Convention du repère local

AFFE_CARA_ELEM/ORIENTATION du `.comm`, règle de U4.42.01 (lue par `get_document_section`) :
x_l du nœud 1 au nœud 2 de la maille ; VECT_Z (0, 0, 1) → z_l = projection de +Z, y_l = z_l ∧ x_l ;
VECT_Y (1, 0, 0) → y_l = projection de +X, z_l = x_l ∧ y_l. Calculé élément par élément sur la
connectivité réelle du MED (`yl_*`, `zl_*` de `elements.csv`). Un exemple par famille :

| Famille | Élément (nœuds) | x_l | y_l | z_l | Lecture |
|---|---|---|---|---|---|
| Poutres principales (VECT_Z) | 61 (13 → 186) | +X | +Y | +Z | MFY = moment d'axe fort (My), VZ vertical |
| Montants (VECT_Z) | 119 (13 → 226) | +Y | −X | +Z | MFY flexion verticale |
| Diagonales (VECT_Z) | 179 (23 → 255) | (0,374 ; −0,928 ; 0) | (0,928 ; 0,374 ; 0) | +Z | MFY flexion verticale |
| Pannes (VECT_Z) | 229 (78 → 79) | +X | +Y | +Z | comme les poutres |
| Profilés supports (VECT_Y) | 349 (122 → 360) | +Z | +X | +Y | VY selon X, VZ selon Y |
| Chevêtre (VECT_Z) | 361 (128 → 129) | +Y | −X | +Z | HY = 0,25 selon X, HZ = 0,40 selon Z |
| Poteaux (VECT_Y) | 373 (139 → 371) | +Z | +X | +Y | comme les supports |

Efforts : EFGE_ELNO bruts de Code_Aster, N > 0 en traction, efforts intérieurs avec la même
convention aux deux extrémités (vérifié : continus d'un élément au suivant, sauts aux seuls
raccords). Numéros : nœud = numéro MED ; élément = numéro MED de la SEG2 (= « maille » des CSV du
lot 50 bis + 1).

Membres : chaque barre (PP_YM, MONT_1…, CHEVETRE, POT_1…) coupée à ses nœuds de raccord (nœud
commun à une autre barre, nœud d'une LIAISON_SOLIDE ou d'une articulation, appui) ; natures :
soudé, soudé avec excentricité par liaison rigide (pannes sur montants et diagonales, têtes des
supports), articulation (pied des supports sur le chevêtre, P18), liaison rigide (poteaux), appui
(rotules P25). Aucun nœud intermédiaire connecté par construction (colonne gardée, vide).

## Limites

- Les caractéristiques déduites des sections RECTANGLE et CERCLE (A, IY, IZ, JX, AY, AZ, RT) sont
  recalculées par les formules et tableaux de U4.42.01 : Code_Aster ne les imprime qu'avec
  INFO = 2, et aucune exécution n'était permise. MP1200 : valeurs affectées seulement (AY = AZ,
  hypothèse provisoire du lot 50).
- Poteaux : dans `elements.csv` et `membres.csv`, pas dans les efforts (hors liste de la consigne).
- Ressorts cumulés : résultante et moment par rapport à (6,25 ; 0 ; −0,755) ; les efforts nœud par
  nœud de la semelle ne sont pas exportés.
- Le critère est commité avec les résultats (même commit) : antériorité non démontrable par Git.

## Contrôles, `rex`, interventions

- `env-check` OK (profil vm), `mcp-check` OK (10 outils).
- Tests ciblés : `projets/pontons_alu_01/tests/test_pontons_export_lot50ter.py`, 9 réussis ; la
  batterie complète est rapportée dans le message du commit.
- Équilibre des 16 cas relu dans les fichiers exportés : résidu relatif maximal 2,1·10⁻¹¹.
- `aster-expert rex pontons_alu_01` : 11 exécutions, 0 échec, « Tous les échecs sont classés :
  clôture possible » ; revue inscrite (`--enregistrer --lot 50ter`).
- Interventions de MM : 0. Connaissances ayant évité une erreur : 0 (aucune commande écrite) ;
  documentation U4.42.01 consultée pour le repère local et les sections.
