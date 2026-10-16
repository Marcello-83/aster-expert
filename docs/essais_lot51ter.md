# Essais du lot 51 ter — PONTONS-ALU-01 : ponton intégral, cotes AVP, houle par surfaces, ancrage des palées

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot51ter_consigne.md` (version 3). Code_Aster
17.4.0 (image `simvia/code_aster:17.4.0`, digest `sha256:d8d19ea9…`). Calcul linéaire seulement ;
niveau visé : **D** (harnais d'équilibre et contrôles de cohérence), jamais plus. Aucune
vérification EC9, béton armé ou appareil d'appui ; aucun ancrage modélisé : le soulèvement se
constate et se rapporte (consigne, « Interdits »).

## Objet

Calculer, pour chacune des quatre variantes de `variantes_lot51ter.yaml` (A10, A12, B10, B12), le
ponton intégral (culée en X = 0, cinq palées, cinq grandes travées, porte-à-faux d'extrémité) aux
cotes de l'AVP (P53, P54) : 221 cas élémentaires unitaires, enveloppes du jeu B′ révisé et de l'ELU
accidentel avec la houle par surfaces et par état limite (P56), la non-concomitance de la houle et de
l'accostage (P57) et les facteurs de l'amarrage (P59) ; ancrage requis palée par palée, réactions de
la culée, chaîne longitudinale, déplacements en X des axes.

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | Fin d'exécution de chaque variante | `FIN` atteint, statut `completed_ok` ou `completed_with_alarms` | niveau C | — ; une variante qui s'arrête est rapportée avec son message, jamais stabilisée artificiellement |
| 2 | Harnais D du tronc commun, version 3 (correction 1 du lot), chaque cas de chaque variante : charge appliquée + réactions de la culée (DX, DY, DZ) + forces des ressorts des cinq semelles. Charge appliquée de DEJ : 10 kN/m³ × volume de béton modélisé, angles de l'anneau comptés une fois (correction 2). Cas thermiques : échelle Σ\|k·u\| des ressorts ; si elle ne dépasse pas 1 N (échelle nulle), critère absolu | 0 | exacte (équilibre discret) | résidu ≤ 10⁻⁶ × charge appliquée ; cas thermique d'échelle > 1 N : résidu ≤ 10⁻⁶ × Σ\|k·u\| ; échelle ≤ 1 N : Σ\|F\| ≤ 1 N (réactions de la culée et Σ\|k·u\|) ; CTL-013 : charge évaluée = charge déclarée, même seuil |
| 3 | HU_PLATELAGE et HD_TABLIER, chaque module et le total : résultante déclarée = largeur (1,327 m ; 1,895 m) × longueur chargée × 1 kPa, la longueur chargée étant celle des poutres principales du modèle ; cette résultante est celle que le harnais (critère 2) confronte aux réactions | égalité | exacte | 10⁻⁶ en relatif ; l'écart à la longueur nominale (X = 0 à 38,85 + Lpf) est rapporté, non jugé (jeux de 1 mm aux éclissages) |
| 4 | Somme des modules contre le cas total, G2, Q, QD, HU_TUBES, HU_PANNES, HU_PLATELAGE, HD_TABLIER, sur les déplacements de tous les nœuds (variante B10) | égalité (linéarité) | exacte | écart ≤ 10⁻⁶ × max \|u\| du cas total |
| 5 | Équilibre global sous AM1 seul (B10, AM1_+X et AM1_-X, combinaison linéaire des 40 cas d'amarrage) : ΣRX culée + ΣRX palées = force appliquée selon X (20 × 13,7 kN), ΣRX palées = Σ des forces X des ressorts des cinq semelles | ΣRX palées = 0, ΣRX culée = −force appliquée | exacte (X libre aux axes) | \|ΣRX palées\| ≤ 10⁻⁶ × force appliquée ; \|ΣRX culée + force\| ≤ 10⁻⁶ × force appliquée |
| 6 | Sous TP seul (chaque variante) : réactions de la culée et forces des ressorts nulles (critère 2) ; DX de l'axe du chevêtre C2 de P5 (X = 38,85, translation du point de l'axe portée par l'oreille) contre α·ΔT·38,85 (α = 23·10⁻⁶ /°C, ΔT = +46 °C) | égalité | sensible au modèle (jeux de 1 mm) | 1 % |
| 7 | Appuis à axe (B10, tous les cas) : pour chaque appui, somme des REAC_NODA (translations) de ses oreilles et du nœud du chevêtre ; composante X de l'effort de l'axe sur le chevêtre ; composante Y pour les appuis YM | 0 | exacte | ≤ 10⁻⁶ × max \|F\| des appuis du cas ; cas dont max \|F\| ≤ 1 N : ≤ 1 N en absolu |
| 8 | Enveloppes par décomposition (`combinaisons_lot51ter.envelope`, Q et QD par lignes d'influence) contre (a) l'énumération combinaison par combinaison du `recombiner.py` livré (bibliothèque standard) et (b) l'énumération explicite de toutes les combinaisons avec les 63 dispositions de Q et de QD (`brute_force`), variante B10, ELU fondamental et ELU accidentel, max et min, au lieu qui gouverne : MFY des poutres principales, N des piles, Fz des appuis à axe, ΣRz du sol de chaque palée, RX de la culée | égalité | exacte | écart ≤ 10⁻⁹ en relatif |
| 9 | Effectif des combinaisons en règles : formule contre énumération des règles avec suppression des doublons, et contre le décompte de `recombiner.py` relu dans les CSV ; effectif avec les dispositions de Q et de QD comptées : formule contre `recombiner.py --compter` | égalité, 2 351 600 en règles par variante (107 521 952 dispositions comptées) | exacte | égalité stricte |
| 10 | Exclusions dans les règles (`check_exclusions`) : aucune branche ne permet Q avec la houle (B′), la houle avec un événement AC ou ACA (P57), deux événements d'accostage | aucune violation | exacte | zéro |

Toute autre issue est un échec, rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- **Cotes (P53, P54)**, grille de 1 mm : dessus +1,40 ; axe des poutres principales, montants et
  diagonales +1,30 ; pannes +1,375 (50 × 50) ou +1,37 (60 × 60) ; axe des appuis +1,16 ; anneau
  0,40 × 0,40 de +0,69 à +1,09, axe +0,89 ; têtes de piles +0,69 ; dessus de semelle +0,69 − H ;
  plan moyen de la semelle +0,59 − H.
- **Travées** : T1 de X = 0 à X1 ; PTk de Xk + 1 mm à Xk + 1,52 − 1 mm (PT5 : jusqu'à X5 + 1,52,
  sans jeu) ; T(k+1) de Xk + 1,52 à X(k+1) ; PF de X5 + 1,52 à X5 + 1,52 + Lpf. Les jeux de 1 mm
  (deux par palée P1 à P4, un en P5) séparent les oreilles reliées par l'axe (nœuds distincts) :
  longueur chargée du tablier = longueur nominale − 9 mm.
- **Appuis à axe (P44, P54)** : relations du lot 51 bis au point de l'axe (Z = +1,16) ; sur le
  chevêtre C2 de P5, une seule oreille (PT5 continue avec PF) : Z, et Y en YP, de l'axe porté par
  l'oreille égaux à ceux portés par le nœud du chevêtre ; X libre partout.
- **Porte-à-faux** : poutres principales et pannes prolongées sans éclissage après l'axe C2 de P5,
  sans diagonale ; **panne de rive** transversale en bout, dans le plan des poutres principales
  (+1,30), de même section que les pannes, les pannes y étant reliées par LIAISON_SOLIDE comme
  aux montants. Section et position de la panne de rive : hypothèse de l'outil (la consigne n'en
  donne pas), à confirmer par MM.
- **Culée** : rotules aux extrémités des poutres principales en X = 0 (YP : X, Y, Z bloqués ; YM :
  X, Z), seul point fixe longitudinal.
- **Angles de l'anneau (correction 2)** : chaque longrine est coupée au nu des chevêtres (Xk + 0,20
  et Xk + 1,32) ; les morceaux dans l'épaisseur d'un chevêtre (groupe `ANGLES_ANNEAU`) gardent la
  raideur du béton mais un matériau sans masse (RHO = 0) et ne reçoivent pas DEJ : volume de l'anneau
  par palée = 2 × 2,10 × 0,16 + 2 × 1,12 × 0,16 = 1,0304 m³.
- **Houle (P56)** : cas unitaires de 1 kPa, FORCE_POUTRE ; HU_TUBES 0,20 m sur chaque poutre
  principale ; HU_PANNES 0,05 m sur chaque panne (pas sur la panne de rive) ; HU_PLATELAGE et
  HD_TABLIER : largeurs tributaires de G2 (tablier de 2,00 m) × 1,327 / 2,00 et × 1,895 / 2,00.
  Coefficients P5 partout, houle en phase sur toute la longueur. ELU accidentel : HU ou HD × 0,77
  comme action variable de tête (ψ1 du lot 51 bis), jamais en accompagnement (ψ2 = 0) ; ELS
  fréquent : HU_F × 1,0 en tête ; aucun équivalent fréquent de HD n'étant donné, HD n'entre pas à
  l'ELS fréquent ; ELS quasi permanent : pas de houle.
- **Q et QD par modules** : un événement Q (et QD) dont chaque module est chargé ou non ; pour une
  grandeur et un sens, la contribution est la somme des contributions de même signe des modules
  (lignes d'influence, exact en linéaire) ; une disposition sans module équivaut à l'absence de Q.
- **Ancrage** : ΣRz du sol d'une palée = Σ des forces des ressorts de sa semelle (−k_n × aire ×
  u_z, > 0 vers le haut) ; effort d'ancrage requis = max(0 ; −ΣRz min) à l'ELU fondamental et à
  l'ELS caractéristique ; part de HU = contribution de l'événement HU (ou HD) à ΣRz dans la
  combinaison gouvernante, rapportée à la contribution de toutes les actions variables.
- **DX des axes** : translation en X du point de l'axe portée par l'oreille 1 (déplacement du
  tablier au droit de l'axe) ; glissement = la même moins celle portée par le nœud du chevêtre.
- **Flèches (P51)** : relatives à la corde des appuis de chaque grande travée, actions variables
  seules ; porte-à-faux : déplacement vertical du bout moins celui de l'axe C2 de P5 corrigé de la
  rotation de la corde de PT5, rapport L/flèche avec L = 2 Lpf.

## 3. Modèle et exécution (après le commit du critère, db1ffb2)

- Maillages : `maillage/maillage_ponton_51ter.py`, quatre géométries (pannes A et B, pannes 50 et
  60 mm) : 3 215 nœuds, 2 776 SEG2, 780 QUAD4 chacune ; `mesh check` **3 526/3 526** invariants
  tenus pour les quatre (MED du script formaté, relancé à l'étape `executer`).
- `.comm` : `generation_lot51ter.build_comm`, un par variante, régénérés à l'octet près par un test
  (`references/execution_lot51ter/<variante>/pontons_alu_01.comm`) ; niveau B **valide**, 1 616/1 616
  commandes confrontées pour chacune ; 102 relations d'axe ; 221 cas.
- Exécutions : `scripts/lot51ter.py executer` (quatre en parallèle, `ncpus` 1), image
  `simvia/code_aster:17.4.0` par digest : A10 `20261016T081729-ce4889e8` (342 s), A12
  `…081720-7aff9418` (347 s), B10 `…081729-5e5f4d2e` (342 s), B12 `…081721-d59891e7` (346 s).
- `charges.med` de B10 : chaîne du tronc commun (`PONTONS_VARIANTE=B10`, exécution
  `20261016T082302-9a66f1cd`, `completed_ok`, 0 alarme ; livrables : post-traitement niveau B
  2 515/2 515, exécution `20261016T083601-16f8d3dd`, tables E20.12 identiques à la production,
  1 412 077 valeurs ; 221 cas, 221 vues rendues par pvbatch puis par `exec()`).

## 4. Résultats

| # | Résultat |
| --- | --- |
| 1 | 4 variantes `completed_ok`, 0 alarme. |
| 2 | **221 cas sur 221** réussis pour chaque variante (harnais version 3) ; résidu relatif maximal 2,8·10⁻¹⁰ (A12, TAM) ; DEJ 1,4·10⁻¹² à 2,7·10⁻¹² ; TP et TM sous le critère absolu : Σ\|F\| = 1,5·10⁻⁷ à 6,5·10⁻⁷ N ; TAP et TAM gardent le critère relatif (échelle > 1 N) ; CTL-013 RÉUSSI. |
| 3 | B10 : résultante déclarée de HU_PLATELAGE et HD_TABLIER = largeur × longueur chargée × 1 kPa à 2,7·10⁻¹⁶ (total) et 1,8·10⁻¹⁶ (modules) ; longueur chargée 40,091 m contre 40,10 m nominal : écart 2,24·10⁻⁴ (9 jeux de 1 mm), rapporté. |
| 4 | B10 : écart relatif maximal entre le cas total et la somme de ses modules 1,3·10⁻¹¹ (HD_TABLIER). |
| 5 | Quatre variantes : ΣRX culée = −274 000 N à 5·10⁻⁵ N près ; \|ΣRX palées\| ≤ 2,0·10⁻⁷ N (rapport 7·10⁻¹³). |
| 6 | Quatre variantes : DX de l'axe C2 de P5 sous TP = 41,094 mm contre α·ΔT·38,85 = 41,103 mm, écart 0,023 % (longueur d'aluminium = 38,85 m moins les jeux de 1 mm). |
| 7 | B10 : somme des REAC_NODA d'un appui ≤ 2,4·10⁻¹⁰, Fx ≤ 3,4·10⁻¹², Fy en YM ≤ 3,7·10⁻¹¹ (relatif) ; 3 cas d'effort d'appui ≤ 1 N (TP, TM, DEJ) : ≤ 7,4·10⁻⁸ N en absolu. |
| 8 | B10 : 36 extrêmes (MFY des poutres, N des piles, Fz des axes, ΣRz de chaque palée, RX de la culée ; ELU fondamental et accidentel ; max et min) : écart maximal 1,1·10⁻¹⁵ contre `recombiner.py`, 9,1·10⁻¹⁶ contre l'énumération explicite des 63 dispositions. |
| 9 | 2 351 600 combinaisons en règles par variante (ELU fondamental 656 956, ELU accidentel 836 856, ELS caractéristique 656 956, ELS fréquent 199 662, ELS quasi permanent 1 170), énumérées : 2 351 600, toutes distinctes ; 107 521 952 avec les dispositions comptées ; `recombiner.py --compter`, relancé depuis le partage par `python3 -I -S` : mêmes effectifs. |
| 10 | Aucune violation de B′, P57 ni de l'exclusivité de l'accostage dans les règles. |

## 5. Verdict

| # | Verdict |
| --- | --- |
| 1 à 10 | RÉUSSI. |

Niveau atteint : **D** pour les quatre variantes (harnais d'équilibre, contrôles de cohérence 3 à
10). Aucun niveau E (aucune référence extérieure).

## 6. Limites

- Le sol est linéaire et admet la traction (P19) : sous la combinaison qui gouverne ΣRz min à
  l'ELU fondamental, les 182 ressorts de chaque semelle sont tendus ; la palée se soulève en bloc.
  Constaté, aucun ancrage modélisé.
- Houle en phase sur toute la longueur et pressions P5 partout : borne haute voulue (P56).
- Panne de rive du porte-à-faux : section et position supposées (hypothèse de l'outil, § 2).
- Résultantes (V, M, RH) : maximum sur 2 048 directions, à 1,2·10⁻⁶ près par défaut.
- Critères 4, 7, 8 et 9 sur B10 ; les autres variantes emploient le même code.
