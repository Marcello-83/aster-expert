# Lot 51 quater — Pontons aluminium : houle « tablier noyé », impact quasi statique, vues 3D, MED complets

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-51quater`, depuis `main` après
la fusion de `lot-51ter`. Consigne : `docs/lots/lot51quater_consigne.md`. Essais :
`docs/essais_lot51quater.md`, critère commité au point d'arrêt `030333d` avant les recombinaisons.
**Aucune réexécution pour les résultats** : les 221 cas unitaires du lot 51 ter sont recombinés.
Niveau des résultats : **D** (celui du lot 51 ter). Ni EC9, ni béton armé, ni appareil d'appui ;
aucun ancrage modélisé ; aucun autre projet modifié.

## Décisions P60 et P61

Enregistrées depuis `donnees/sources/enregistrement_P60_P61_lot51quater.md` (textes extraits de la
consigne, vérifiés à l'identique) ; **P56 ré-arbitrée** (seuls ses coefficients changent, l'ancienne
décision reste dans `decision_history`) ; fiche régénérée : 71 entrées, aucun bloqueur. Valeurs dans
le groupe `houle_lot51quater` du fichier de données.

- **P60, tablier noyé** : HU = HU_TUBES × 4,92 + HU_PANNES × 1,91 (pannes 50) ou 2,11 (pannes 60) +
  HU_PLATELAGE × 0,90 ; HD = HD_TABLIER × 1,01 ; HU_F inchangé. Vérifié : 2 × 10,05 × (1,445 − z).
- **P61, impact** : six événements exclusifs HU_IMP_M0 à M5 = 5,9 × (HU_TUBES_Mk + HU_PANNES_Mk +
  HU_PLATELAGE_Mk), alternatifs à HU dans l'emplacement de la houle, à l'ELU fondamental et à l'ELS
  caractéristique seulement, jamais avec Q, AC ou ACA. 5,9 kPa correspond à w = 2π × 2,03 / 11,5 =
  1,109 m/s (5,94) ; avec w arrondi à 1,1 m/s on obtient 5,84 kPa.
- **HU_S5** (sensibilité, sans décision) : HU remplacé par 5 kPa sur les trois cas de sous-face, sans
  impact ; seulement dans `ancrage.csv`, `palee_equilibre.csv` et les colonnes `_S5` de la comparaison.
- Effectifs : **2 364 008 combinaisons en règles par variante** (107 534 360 dispositions).

## Identité avec le lot 51 ter

- Coefficients P56 passés par les règles du lot : les 61 grandeurs de `comparaison_variantes.csv` du
  lot 51 ter retrouvées **exactement** (valeur, combinaison, lieu), quatre variantes.
- Combinaisons sans houle : enveloppes identiques (8 070 valeurs par variante, écart nul).
- Énumération complète sur B10, 36 extrêmes tirés au sort : écart ≤ 3,2·10⁻¹⁵ (9 gouvernés par un
  impact). Résultantes : HU à 0, HU_IMP_Mk ≤ 1,6·10⁻¹⁶ de la formule ; réactions ≤ 3,3·10⁻¹².

## Comparaison (kN, kN·m, mm ; entre parenthèses, le lot 51 ter)

| Var. | PP My | L/f ELS c (T2) | L/f ELS f (T2) | L/f PF c | Axes Fz min | Gliss. X ELU | Piles N max | Ancrage ELU / ELS c | Culée ΣRX ELU |
|---|---|---|---|---|---|---|---|---|---|
| A10 | −68,3 (−95,7) | 142 (79) | 262 (262) | 3 330 (1 588) | −40,6 (−75,6) | 119,1 (141,4) | 71,1 (83,9) | 21,5 / 0 (233,0 / 122,6) | 435,7 (435,7) |
| A12 | −69,3 (−96,1) | 164 (90) | 302 (302) | 3 884 (1 858) | −40,1 (−74,7) | 113,3 (131,7) | 69,9 (83,2) | 20,8 / 0 (232,4 / 121,8) | 435,7 (435,7) |
| B10 | −68,3 (−95,7) | 142 (79) | 262 (262) | 2 051 (954) | −43,8 (−75,6) | 120,1 (138,7) | 74,3 (84,1) | 23,4 / 0 (235,0 / 125,0) | 435,7 (435,7) |
| B12 | −69,3 (−96,1) | 164 (90) | 302 (302) | 2 402 (1 117) | −43,1 (−74,7) | 114,3 (129,0) | 73,1 (83,4) | 22,7 / 0 (234,3 / 124,2) | 435,7 (435,7) |

- **A10** : la houle ne gouverne plus PP My (Q + AC) ; flèche caractéristique L/142 (impact sur T2),
  au-dessus du L/150 du superviseur ; ancrage ELU 21,5 kN en P1, rien à l'ELS c.
- **A12** : sections renforcées : L/164 à l'ELS c, sous le critère L/150 ; ancrage 20,8 kN.
- **B10** : comme A10 ; ancrage P1 23,4 kN (piles plus courtes) ; porte-à-faux L/2 051.
- **B12** : comme A12 ; ancrage P1 22,7 kN.

## Ancrage par palée (kN, ELU fondamental / ELS caractéristique ; HU_S5 entre parenthèses)

| Palée | A10 | A12 | B10 | B12 |
|---|---|---|---|---|
| P1 | 21,5 / 0 (54,5 / 3,6) | 20,8 / 0 (53,9 / 2,8) | 23,4 / 0 (56,5 / 6,0) | 22,7 / 0 (55,8 / 5,2) |
| P2 | 10,2 / 0 (43,3 / 0) | 9,5 / 0 (42,6 / 0) | 10,7 / 0 (43,7 / 0) | 10,0 / 0 (43,1 / 0) |
| P3 | 5,3 / 0 (38,3 / 0) | 4,6 / 0 (37,7 / 0) | 5,3 / 0 (38,3 / 0) | 4,6 / 0 (37,7 / 0) |
| P4 | 0 / 0 (30,5 / 0) | 0 / 0 (29,8 / 0) | 0 / 0 (28,5 / 0) | 0 / 0 (27,8 / 0) |
| P5 | 0 / 0 (1,1 / 0) | 0 / 0 (0,6 / 0) | 0 / 0 (3,5 / 0) | 0 / 0 (3,0 / 0) |

Avec P60/P61, seules P1 à P3 se soulèvent, et seulement à l'ELU (G × 0,9 + DEJ + impact × 1,5 +
amarrage × 1,155). Le forfait AVP de 5 kPa (HU_S5) demande 28 à 57 kN en P1 à P4 à l'ELU.

## Événement de houle gouvernant

| Grandeur | A10, A12, B10, B12 |
|---|---|
| PP My | aucun (Q + AM1 + AC) |
| Flèche ELS c (T2, plus petit L/f) | HU_IMP_M1 |
| Ancrage ELU et ELS c (P1, palée la plus défavorable) | HU_IMP_M1 ; P2 : HU_IMP_M2 ; P3 : HU_IMP_M3 |

HU (immersion) ne gouverne plus aucune de ces grandeurs : l'impact local le remplace.

## Temps de recombinaison

Par variante, les quatre en parallèle : lecture des tables 19 s, exports 9 à 19 s, comparaison 270 à
275 s, **total 280 à 290 s**. Contrôles d'identité 226 à 232 s ; énumération B10 53 s.

## `.npz`

`efforts_elementaires.npz` (float32, 221 cas × 4 552 extrémités × 6 composantes, toutes les barres) :
**8,7 Mo** par variante (CSV : 188 Mo, déposé pour B10 seulement). Lecture indépendante
(`scripts/lire_npz_lot51quater.py`) : 20/20 tirages contre le CSV.

## PNG et MED

- `vues/` (20 PNG, 1 920 × 1 080) : pour B10 et B12, `vue1_ponton_iso_cote_mer`,
  `vue2_ponton_iso_cote_port`, `vue3_culee_T1`, `vue4_palee_P1`, `vue5_P5_PT5_porte_a_faux`,
  `vue6_coupe_transversale_P1`, `vue7_1` à `vue7_4` (déformées PP My, flèche ELS f, ΣRX culée, impact
  HU_IMP_M0). Regardées à l'œil : B10 vues 1, 4, 6 et 7.4 ; B12 vue 5. Côté mer : vue depuis
  l'extrémité du porte-à-faux ; côté port : depuis la culée (le modèle ne les définit pas : hypothèse).
- `B10/MED/`, `B12/MED/` : `structure.med` (1 029 groupes dont TRAVEE_*, PALEE_*, AXES_APPUI),
  `charges.med` (225 champs unitaires de Code_Aster + EV_HU, EV_HD, EV_HU_F, EV_HU_IMP_M0 à M5),
  `resultats.med` (DEPL et EFGE_ELNO des 4 combinaisons, ENV_ELU__EFGE_ELNO : N, MFY, MFZ max et min,
  ELU fondamental et accidentel). **Écrits en Python (medcoupling)** à partir des champs unitaires que
  Code_Aster a écrits en MED (rejeu du `.comm` du lot 51 ter, inchangé, sha256 vérifié, pour B12) :
  plus sûr qu'une commande de combinaison ajoutée, puisque le `.comm` reste intact et que chaque valeur
  est confrontée aux tables (écart 0). Format MED 3.3 : le MEDReader de Salomé-Méca 2024.1 refuse le
  4.2 que medcoupling écrit par défaut.
- `scripts/` : `vues_3d_pontons.py` (pvbatch, paramétré par la variante), `afficher_pontons_salome.py`
  (ParaVis : coloration par famille sur la déformée, ou par composante d'effort sur la structure non
  déformée ; flèches de charges à l'échelle de chaque cas), `lire_npz_lot51quater.py`.
- Dépôt `/media/sf_partage/echanges/lot51quater/pontons_alu_01/` : 104 fichiers, 748 Mo, `sha256sum
  -c` sans écart.

## Points ouverts

- HU_PANNES des variantes 12 : largeur 0,05 m conservée (cas unitaire du lot 51 ter) alors que les
  pannes ont 0,06 m de sous-face : le coefficient 2,11 porte sur 0,20 m au lieu de 0,24 m.
- p_imp : 5,9 kPa décidé (w = 1,109 m/s) ; 5,84 kPa avec w = 1,1 m/s.
- Côtés mer et port des vues 1 et 2 à confirmer.

## `rex` et interventions

`aster-expert rex pontons_alu_01` : 40 exécutions attribuées, 1 échec (lot 51, DIAG-030), 0 depuis
le dernier retour ; développement 35 (taux 2,9 %), vérification 5 ; « Tous les échecs sont classés :
clôture possible » ; revue inscrite (`--enregistrer --lot 51quater`). Interventions de MM : 0.
Connaissances ayant évité une erreur : 0 attribuée.
