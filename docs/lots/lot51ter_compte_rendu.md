# Lot 51 ter — Pontons aluminium : ponton intégral, cotes AVP corrigées, houle par surfaces, ancrage des palées

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-51ter`, depuis `main` après la
fusion de `lot-51bis`. Consigne (version 3) : `docs/lots/lot51ter_consigne.md`. Essais :
`docs/essais_lot51ter.md`, critère commité **avant** les exécutions (db1ffb2). Calcul linéaire
seulement ; aucune vérification EC9, béton armé ou appareil d'appui ; aucun ancrage modélisé ; aucun
autre projet modifié.

## Décisions P53 à P59

Enregistrées dans la fiche depuis `donnees/sources/enregistrement_P53_P59_lot51ter.md` (textes
extraits de la consigne par script, vérifiés à l'identique), fiche régénérée par
`scripts/fiche_lot50.py` (69 entrées, aucun bloqueur). **P47 et P50 sont ré-arbitrées** : annulées
par P53 et P55, l'ancienne décision reste dans `decision_history`. Choix de l'agent : A10 (noms des
groupes), A11 (lecture du DX des axes et de l'équilibre des palées).

- **P53** : dessus +1,40 ; poutres +1,30 ; pannes +1,375 (50 × 50) ou +1,37 (60 × 60) ; anneau
  0,40 × 0,40 de +0,69 à +1,09 (axe +0,89). **P54** : axe à +1,16, modélisation du lot 51 bis.
- **P55** : tubes drainés, aucune flottabilité. **P56** : quatre cas unitaires de 1 kPa
  (HU_TUBES, HU_PANNES, HU_PLATELAGE, HD_TABLIER), coefficients P5 partout (HU 14,49 / 12,99 /
  12,48 ; HD 12,03 ; HU_F 2,36 / 0,85 / 0,35), houle en phase. Classeur versé dans
  `donnees/sources/` : **deux copies différentes existent sur le partage** (ρg 10,25 et 10,05
  kN/m³) ; retenue celle de « Claude outputs » (16/10/2026, sha256 43d4a4ca…), la seule qui donne
  les valeurs de P56.
- **P57** : jamais de houle avec AC ou ACA. **P58** : ponton intégral. **P59** : ψ de l'amarrage.

Interprétations de l'outil, écrites avant les exécutions : à l'ELU accidentel, HU ou HD × 0,77
seulement comme action variable de tête (ψ2 = 0) ; HD n'entre pas à l'ELS fréquent (aucune valeur
fréquente donnée) ; panne de rive du porte-à-faux dans le plan des poutres, section des pannes
(hypothèse, à confirmer) ; **Lpf = porte-à-faux du diagnostic + 0,20 m : hypothèse de la consigne**.

## Géométrie générée (stations dans `variantes_lot51ter.yaml`)

Culée X = 0 ; C1 des palées en X = 6,25 / 14,02 / 21,79 / 29,56 / 37,33, C2 à + 1,52 ; bout du
porte-à-faux 39,90 (A, Lpf 1,05) ou 40,10 (B, Lpf 1,25). Plan moyen des semelles (m NGF) :

| Panne | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|
| A (piles 1,50 / 2,00 / 2,50 / 3,30 / 3,90) | −0,91 | −1,41 | −1,91 | −2,71 | −3,31 |
| B (piles 1,30 / 1,95 / 2,50 / 3,50 / 3,90) | −0,71 | −1,36 | −1,91 | −2,91 | −3,31 |

Dessus de semelle = +0,69 − H, fond = +0,49 − H. 3 215 nœuds, `mesh check` 3 526/3 526 pour les
quatre géométries ; sur C2 de P5, une seule oreille (PT5 continue avec PF).

## Effectifs

221 cas unitaires (G1, DEJ ; G2, Q, QD et les 4 cas de houle, chacun total + 6 modules ; 126
accostages ; 40 amarrages ; 4 températures). Événements : 168 AC, 168 ACA, 60 AM locaux, AM1 ±X,
AM2 YM/YP, 60 AMF. **2 351 600 combinaisons par variante en règles** (ELU f. 656 956, ELU acc.
836 856, ELS c 656 956, ELS f 199 662, ELS qp 1 170), soit 107 521 952 avec les 63 dispositions de
Q et de QD comptées. Méthode pour Q et QD : chaque module chargé ou non ; pour une grandeur et un
sens, l'événement prend la somme des contributions de même signe des modules (lignes d'influence,
exact en linéaire) ; les modules retenus sont écrits dans la combinaison (`Q[M0+M1]`). Au plus un
événement AC ou ACA par combinaison.

## Harnais et contrôles

Quatre variantes à **FIN** (`completed_ok`, 0 alarme), niveau B 1 616/1 616. **Harnais D : 221 cas
sur 221** pour chaque variante (résidu ≤ 2,8·10⁻¹⁰ ; DEJ ≤ 2,7·10⁻¹² ; TP, TM sous le critère
absolu, Σ|F| ≤ 6,5·10⁻⁷ N). HU_PLATELAGE et HD_TABLIER = largeur × longueur chargée à 3·10⁻¹⁶
(longueur chargée 40,091 m, soit 2,2·10⁻⁴ sous la nominale : 9 jeux de 1 mm) ; somme des modules
= total à 1,3·10⁻¹¹ ; AM1 : ΣRX culée = −274 kN, ΣRX palées ≤ 2·10⁻⁷ N ; TP : DX de P5 41,09 mm
contre α·ΔT·38,85 = 41,10 mm (0,023 %) ; appuis à axe ≤ 2,4·10⁻¹⁰ ; décomposition contre
`recombiner.py` et contre l'énumération explicite : 1,1·10⁻¹⁵ (36 extrêmes). **Niveau D** pour les
quatre variantes ; aucun niveau E.

## Comparaison (kN, kN·m, mm ; enveloppes B′ et ELU accidentel)

| Var. | PP My | PP \|N\| | L/f ELS f (T2) | L/f ELS c (T2) | L/f PF c | Axes Fz min / max | Gliss. X ELU / ELS c | Piles N min / max | Ancrage ELU / ELS c | Culée RX (un axe) / ΣRX ELU |
|---|---|---|---|---|---|---|---|---|---|---|
| A10 | −95,7 | 295,0 | 262 | 79 | 1 588 | −75,6 / 81,7 | 141,4 / 95,4 | −120,1 / 83,9 | 233,0 / 122,6 (P1) | 311,8 / 435,7 |
| A12 | −96,1 | 295,5 | 302 | 90 | 1 858 | −74,7 / 81,2 | 131,7 / 88,9 | −119,8 / 83,2 | 232,4 / 121,8 (P1) | 315,0 / 435,7 |
| B10 | −95,7 | 293,9 | 262 | 79 | 954 | −75,6 / 81,7 | 138,7 / 93,6 | −121,0 / 84,1 | 235,0 / 125,0 (P1) | 309,6 / 435,7 |
| B12 | −96,1 | 294,4 | 302 | 90 | 1 117 | −74,7 / 81,2 | 129,0 / 87,0 | −120,8 / 83,4 | 234,3 / 124,2 (P1) | 312,6 / 435,7 |

Flèches selon P51, variables seules : la travée T2 gouverne ; à l'ELS caractéristique, **la houle
HU soulève les travées de 64,7 à 79,6 mm (L/78 à L/90)**, au-delà du L/150 du superviseur ; à
l'ELS fréquent, L/262 à L/302 (vers le bas, Q).

- **A10** : référence panne A ; ancrage P1 233 kN à l'ELU.
- **A12** : tubes de 12 mm et pannes 60 : flèches −13 % (L/90 et L/302), glissement −7 %, ancrage
  quasi inchangé (−0,6 kN).
- **B10** : panne B (piles plus courtes en P1, P2, plus longues en P4, Lpf 1,25 m) : ancrage P1
  +2 kN, P5 +7 kN (porte-à-faux plus long, plus de houle), L/f du porte-à-faux 954.
- **B12** : B10 avec les sections renforcées : mêmes gains que A12.

## Ancrage par palée (effort requis = max(0 ; −ΣRz min), kN ; part de la houle ≥ 0,98)

| Palée | A10 ELU / ELS c | A12 | B10 | B12 |
|---|---|---|---|---|
| P1 | 233,0 / 122,6 | 232,4 / 121,8 | 235,0 / 125,0 | 234,3 / 124,2 |
| P2 | 221,8 / 112,5 | 221,1 / 111,7 | 222,3 / 113,0 | 221,6 / 112,3 |
| P3 | 216,9 / 106,6 | 216,2 / 105,8 | 216,9 / 106,6 | 216,2 / 105,8 |
| P4 | 209,0 / 97,1 | 208,3 / 96,4 | 207,0 / 94,8 | 206,3 / 94,0 |
| P5 | 131,9 / 45,2 | 131,4 / 44,6 | 139,0 / 49,7 | 138,4 / 49,1 |

Combinaison gouvernante partout : G × 0,9 + DEJ + HU × 1,5 + AM1 × 1,155 (ELU) et G + DEJ + HU +
AM1 × 0,77 (ELS c). Toutes les palées se soulèvent en bloc (182 ressorts tendus sur 182) ; P5, la
plus lourde (5,45 m³), demande le moins.

## Culée, chaîne longitudinale, DX des axes

- **Culée** (B10, ELU fondamental) : RX ±310 kN par axe (somme des deux axes 436 kN sous AM1 +
  AC + Q), RY YP ±79 kN, RZ +70 / −64 kN (soulèvement) ; ELU accidentel RX 211 kN, ELS c 209 kN,
  ELS qp 33 kN. **AM1 sur les 20 taquets donne la poussée longitudinale maximale sur la culée**
  (274 kN caractéristique). Détail : `culee.csv`.
- **Chaîne** (B10, ELU f.) : N dans les poutres principales de +294 / −280 kN à la culée, décroissant
  vers P5 (+37 à +87 kN à C2 et C1) : tout l'effort longitudinal passe par les poutres jusqu'à la
  culée. Détail : `chaine_x.csv`.
- **DX des axes** (B10) : sous TP 6,6 mm (P1 C1) à 41,1 mm (P5 C2), sous TM −4,0 à −25,0 mm ; ELS c
  de −67,5 à +90,3 mm en P5. **Les charges verticales déplacent aussi les axes en X** : les axes
  sont 0,14 m sous l'axe des poutres, et la rotation d'about des travées les écarte (HD seul : 41 mm
  en P5 ; contrôle à la main ≈ 10 mm par travée). Glissement à l'ELU jusqu'à 141 mm. Détail :
  `deplacements_axes.csv`.

## Corrections du tronc commun

1. **Harnais D version 3** (`controles/equilibre.py`, `harnais.py`, `projet/declaration.py`) :
   `controls.absolute_threshold_n` ; un cas autoéquilibré dont l'échelle déclarée ne dépasse pas ce
   seuil est jugé sur Σ|F| ≤ seuil (réactions bloquées et Σ|k·u|), écart relatif NaN ; CTL-005 et
   CTL-013 suivent. Tests : `tests/unit/test_controles_equilibre.py` (2 tests).
2. **Volume de l'anneau** : longrines coupées au nu des chevêtres, morceaux d'angle
   (`ANGLES_ANNEAU`) sans masse et sans DEJ ; volume de l'anneau 1,0304 m³ par palée. Test :
   `test_ring_corners_are_counted_once`, et DEJ au harnais à 2,7·10⁻¹².

## Livraison (`/media/sf_partage/echanges/lot51ter/pontons_alu_01/`, 1,2 Go)

Par variante : exports du lot 51 bis repérés par travée et par palée, `appuis_axes`,
`palee_equilibre`, `ancrage`, `culee`, `chaine_x`, `deplacements_axes` et `recombiner.py` ;
`comparaison_variantes.csv` et son détail ; `B10/charges.med` et `B10/charges_salome.py` ;
`empreintes.sha256` (76 fichiers, `sha256sum -c` : 0 écart). Noms neufs.

## `rex` et interventions

`aster-expert rex pontons_alu_01` : 38 exécutions attribuées, 1 échec (lot 51, DIAG-030), 0 depuis
le dernier retour ; développement 34 (taux 2,9 %), vérification 4 ; « Tous les échecs sont classés
: clôture possible » ; revue inscrite (`--enregistrer --lot 51ter`). Interventions de MM : 0.
Connaissances ayant évité une erreur : 0 attribuée (CA-034 et PAT-001 consultés avant d'écrire les
cinq RIGI_PARASOL mais non déclarés avant les exécutions ; PAT-005 et DIAG-030 reconduits).
