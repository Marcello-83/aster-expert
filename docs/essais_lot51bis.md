# Essais du lot 51 bis — PONTONS-ALU-01 : appuis articulés à axe, tablier rehaussé, palées types, équilibre des palées

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot51bis_consigne.md`. Code_Aster 17.4.0
(image `simvia/code_aster:17.4.0`, digest `sha256:d8d19ea9…`). Calcul linéaire seulement ; niveau
visé : **D** (harnais d'équilibre et contrôles de cohérence), jamais plus. Aucune vérification
EC9, béton armé ou appareil d'appui ; aucun ancrage de semelle ni stabilisation artificielle
(consigne, « Interdits »).

## Objet

Établir, pour chacune des cinq variantes de `variantes_lot51bis.yaml` (H40C, H40P, H80C, H80P,
H80C-S3), un calcul linéaire des 69 cas élémentaires (les 68 du lot 51 et DEJ, déjaugeage du
béton, P49), puis les enveloppes du jeu B′ révisé et de l'ELU accidentel avec la règle de DEJ
(P49), l'équilibre de la palée (ΣRz du sol sous la semelle, lest manquant) et les efforts des
appuis à axe (P44).

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | Fin d'exécution de chaque variante | `FIN` atteint, statut `completed_ok` ou `completed_with_alarms` | niveau C | — ; une variante qui s'arrête est rapportée avec son message, jamais stabilisée artificiellement |
| 2 | Équilibre de chaque cas, chaque variante (harnais D du tronc commun) : charge appliquée + réactions des rotules du quai (DX, DY, DZ) + réactions des oreilles en X = 14,02 (DZ ; DY en YP) + forces des ressorts de sol. Pour **DEJ**, la charge appliquée déclarée vaut 10 kN/m³ × volume de béton de la palée tel que modélisé (`generation_lot51bis.concrete_volumes`), vers le haut | 0 | exacte (équilibre discret) | résidu ≤ 10⁻⁶ × charge appliquée ; cas thermiques autoéquilibrés : résidu ≤ 10⁻⁶ × Σ\|k·u\| des ressorts de sol |
| 3 | Somme des cas par travée : `G2_T1 + G2_PT + G2_T2` contre `G2`, de même Q, HU, HD, sur les déplacements de tous les nœuds (variante H80C) | égalité (linéarité) | exacte | écart ≤ 10⁻⁶ × max \|u\| du cas total |
| 4 | Appuis à axe (H80C, tous les cas) : pour chaque appui, somme des REAC_NODA (translations) de ses oreilles et du nœud du chevêtre ; composante X de l'effort de l'axe sur le chevêtre ; composante Y pour les appuis YM | 0 (relations sans second membre, X libre, Y libre en YM) | exacte | ≤ 10⁻⁶ × max \|F\| des appuis du cas |
| 5 | Enveloppes par décomposition (`combinaisons_lot51bis`) contre l'énumération combinaison par combinaison du `recombiner.py` livré (bibliothèque standard), variante H80C, ELU fondamental et ELU accidentel, max et min : MFY des poutres principales, N des piles, Fz des appuis à axe, ΣRz du sol sous la semelle | égalité | exacte | écart ≤ 10⁻⁹ en relatif |
| 6 | Effectif des combinaisons : formule de dénombrement contre énumération avec suppression des doublons (jeux de coefficients identiques gardés une fois) | égalité, 430 914 par variante | exacte | égalité stricte |

Toute autre issue est un échec, rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- **Axe (P44)** : l'axe n'est pas un nœud du maillage. Pour un point P de l'axe et un nœud N,
  la translation de P portée par N vaut u_N + θ_N ∧ (P − N). Relations (LIAISON_DDL, second
  membre nul) : translations de P égales pour les deux oreilles (extrémités des poutres
  principales des deux travées), DRX égales (éclissage articulé : rotations autour de y_l = Y
  et z_l = Z libres) ; Z de P égal pour l'oreille 1 et le nœud du chevêtre sous l'appui
  (Y = ±0,93, sur l'axe de l'anneau) ; Y égal en YP seulement ; X libre. En X = 14,02 : Z de P
  nul, Y nul en YP (support fixe de la palée suivante, P44). P est à X du chevêtre (oreille de
  la petite travée à 1 mm, comme au lot 51), Y = ±0,93, Z = +1,588.
- **Effort de l'axe sur le chevêtre** : REAC_NODA du nœud AX_…_K (seules les relations de
  l'axe y agissent), repère global, Fz compté positif vers le bas (compression) ; en X = 14,02,
  opposé de REAC_NODA de l'oreille. Rotation relative autour de Y : DRY de l'oreille − DRY du
  nœud du chevêtre (DRY de l'oreille en X = 14,02).
- **Cotes (P47)** : plan moyen +1,358 du lot 51 (1,3575 recalé sur la grille de 1 mm) + 0,50 =
  +1,858 ; sous-face des poutres +1,758 ; axe +1,588 ; dessus des chevêtres +1,488 ; axe de
  l'anneau +1,288 (h = 0,40) ou +1,088 (h = 0,80) ; têtes de piles = sous-face de l'anneau ;
  dessus de la semelle = tête − hauteur libre ; plan moyen de la semelle 0,10 m plus bas.
- **Têtes de piles encastrées (P46)** : LIAISON_SOLIDE entre la tête de pile (sous-face de
  l'anneau) et le nœud de l'anneau (axe), à h/2 au-dessus : la pile ne fléchit pas dans
  l'épaisseur de l'anneau.
- **Volumes de béton** : ceux du modèle (longueur des barres × section, semelle 2,60 × 2,60 ×
  0,20) ; les longrines vont d'axe de chevêtre à axe de chevêtre (moins 1 mm), comme au lot 51,
  si bien que les angles de l'anneau sont comptés deux fois (2 × 0,398 m × 0,40 × h : 0,127 m³
  pour h = 0,40, 0,255 m³ pour h = 0,80). G1 et DEJ portent sur ce même volume ; l'écart sur le
  poids déjaugé (15 kN/m³ × ce volume) est rapporté avec le lest manquant.
- **DEJ (P49)** : FORCE_POUTRE FZ = 10 kN/m³ × section sur les chevêtres, longrines et piles,
  FORCE_COQUE FZ = 10 kN/m³ × 0,20 m sur la semelle (repère global, PAT-005). Combinaisons : G ×
  1,2 sans DEJ, G × 0,9 avec DEJ × 1,0 ; ELS et ELU accidentel : G × 1,0 avec et sans DEJ.
- **Équilibre de la palée** : ΣRz = Σ des forces du sol sur la semelle (−k_n × aire tributaire ×
  u_z, > 0 vers le haut), linéaire en les cas : minimum par état limite par décomposition ;
  ressorts en traction dans la combinaison qui gouverne : force du sol < 0. Le sol linéaire
  admet la traction (P19) : aucun ressort n'est désactivé. Lest manquant = max(0 ; −ΣRz min
  ELU) / 0,9, ΣRz min ELU étant le plus petit de l'ELU fondamental et de l'ELU accidentel.
- **Flèches (P51)** : ELS caractéristique sans la composante tangentielle d'accostage (ACX et
  ACZ annulés pour cette seule grandeur) ; ELS fréquent avec (ψ1 = 0,5). Travée 1, relative à
  la corde des appuis, actions variables seules (G et DEJ exclus).
- **Variante H80C-S3** : même maillage que H80C, seule la section des poutres principales
  change.

## 3. Modèle et exécution

À remplir après les exécutions, sans modifier les § 1 et 2.
