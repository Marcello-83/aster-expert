# Essais du lot 52 — PONTONS-ALU-01 : géométrie PRO (B12, treillis constructible, appui v4) et recalcul complet

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot52_consigne.md`. Code_Aster 17.4.0
(image `simvia/code_aster:17.4.0`, digest `sha256:d8d19ea9…`). La géométrie change : le maillage, le
`.comm` et les 221 cas unitaires sont recalculés pour les trois variantes (B52, A52, B52P4), puis
recombinés avec les règles du lot 51 quater (P60, P61). Calcul linéaire seulement. Aucune vérification
EC9, béton armé ou appareil d'appui ; aucun ancrage modélisé.

## Objet

Acter P62 à P66 (MM, 16/10/2026) : houle maintenue dans le critère de flèche (P62) ; poutres
200 × 200 × 12, pannes 50 × 50 × 5 (sensibilité × 4), montants et diagonales 120 × 120 × 6 (P63) ;
treillis horizontal sous les pannes, axe +1,29, liaisons rigides de 0,01 m (montant / poutre) et de
0,085 m (panne / montant ou diagonale), diagonales soudées sur les montants à e = 0,25 m de l'axe des
poutres (P64) ; axe des appuis à +1,175 (P65) ; défenses Delta, μ = 0,7 inchangé (P66). Produire le
modèle PRO, ses exports, la géométrie des nœuds, les vues et les MED de B52.

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | `mesh check` des maillages des géométries A et B (`maillage_ponton_52.py`) contre les invariants calculés depuis les seuls paramètres (`invariants_lot52`, avec le groupe MONTANTS_TRONCONS) | tous les invariants tenus | exacte | aucun écart |
| 2 | Niveau B des trois `.comm`, puis exécution jusqu'à `FIN` | `valide`, toutes les commandes confrontées ; `completed_ok` | exacte | — ; les alarmes sont rapportées |
| 3 | Harnais D du tronc commun (équilibre de chaque cas : réactions de la culée et forces des ressorts contre la résultante déclarée), 221 cas par variante | 221/221 | exacte (équilibre discret) | seuils de `projet.yaml` (10⁻⁶ relatif, 1 N absolu pour les cas thermiques) |
| 4 | `geometrie_noeuds.csv` (B52, A52, B52P4) : à chaque croisement panne/montant, panne/diagonale et montant/poutre, jeu = dessous de la barre du dessus − dessus de la barre du dessous (cotes de l'axe ± demi-cote du tube) ; zone de soudure projetée sur la poutre = largeur du montant + 2 × 30 mm | aucun recouvrement (jeu ≥ 0) ; zone ≤ 200 mm | exacte (cotes sur la grille de 1 mm) | jeu ≥ −10⁻⁶ mm ; zone ≤ 200 mm |
| 5 | Résultante de HU (P60, pannes de 50 : 4,92 × 0,40 + 1,91 × 0,20 + 0,90 × 1,327) et de HD (1,01 × 1,895) sur la longueur chargée, et de chaque HU_IMP_Mk (5,9 × 1,927 × longueur chargée du module) : Σ coefficient × résultante déclarée contre la formule, puis contre les réactions verticales de l'exécution (axes de la culée + ressorts des semelles) | égalité ; somme nulle | exacte | 10⁻⁶ en relatif |
| 6 | Somme des modules égale au cas total (G2, Q, QD et les quatre cas de houle, DEPL de tous les nœuds) | égalité | exacte (linéarité) | 10⁻⁹ × max \|u\| du cas total |
| 7 | Sous AM1 seul (±X) : ΣRX des palées (ressorts) ; ΣRX de la culée + force appliquée | ≈ 0 | exacte (culée seul point fixe en X) | 10⁻⁶ × force appliquée |
| 8 | Sous TP : DX de l'axe de C2 de P5 (porté par l'oreille 1) contre α·ΔT·38,85 (α = 23·10⁻⁶ /K, ΔT = +46 K) | égalité | sensible aux liaisons (point de l'axe sous la poutre) | 1 % en relatif |
| 9 | Enveloppes par décomposition contre (a) le `recombiner.py` livré et (b) l'énumération explicite (`brute_force`) : B52, 36 extrêmes tirés au sort (graine 52, lieux du lot 51 quater plus N, My, Mz des tronçons de montant) | égalité | exacte | 10⁻⁹ en relatif |
| 10 | Effectifs en règles (formule, `recombiner.py`, énumération sans doublon) ; exclusions B′, P57, P61 | égalité, 2 364 008 combinaisons par variante (règles du lot 51 quater inchangées) ; aucune violation | exacte | égalité stricte ; zéro |
| 11 | `efforts_elementaires.npz` (float32, toutes les barres) relu par le lecteur indépendant contre `efforts_elementaires.csv` de B52 (local, non déposé) : 20 tirages (graine 52) | égalité à l'arrondi float32 | exacte | \|Δ\| ≤ 2⁻²⁴ × \|v\| (+ 10⁻³⁰) |
| 12 | Rejeu B52 par la chaîne du tronc commun pour les MED unitaires : `.comm` de la chaîne identique à `resultats/lot52/B52/pontons_alu_01.comm` ; `completed_ok` ; tables E20.12 du post-traitement identiques ; DEPL et EFGE_ELNO unitaires du MED contre les tables E25.16 de l'exécution du lot | identique ; égalité | exacte | égalité d'octets ; 10⁻⁹ × max \|v\| |
| 13 | MED de B52 relus : `structure.med` (nœuds, mailles, groupes du maillage) ; `charges.med` (un champ par cas unitaire et par événement) ; `resultats.med` : sur le maillage d'origine, DEPL et EFGE_ELNO des combinaisons de la vue 7 contre les tables ; **sur le support commun** (maillage aux nœuds dédoublés par élément, `PONTON_B52_ELNO`), DEPL et efforts nodaux de chaque combinaison égaux, nœud par nœud, au DEPL du nœud d'origine et à l'effort ELNO de l'extrémité correspondante | égalité | exacte | 10⁻⁹ × max \|v\| |
| 14 | Chaque PNG de B52 (vues 1 à 9) : fichier non vide, 1 920 × 1 080 ; vues 4, 8 et 9 regardées à l'œil (vue 9 : pannes posées sur les montants, sans pénétration) | conforme | — | — |

Rapportés sans seuil : temps de recombinaison ; comparaison avec B12 du lot 51 quater sur les
grandeurs de `comparaison_variantes.csv`, chaque écart notable commenté en une phrase (la consigne
attend des flèches un peu plus grandes, une flexion des montants nouvelle, un ancrage quasi inchangé ;
un écart à ces attentes est rapporté tel quel, pas corrigé). Toute autre issue des critères 1 à 14 est
un échec, rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- **Géométrie P64** : axe des montants et des diagonales = dessus du tablier − cote des pannes − cote des
  montants / 2 = 1,40 − 0,05 − 0,06 = +1,29 ; extrémités des montants à Y = ±0,93 (axe des poutres),
  reliées verticalement au nœud de la poutre (LIAISON_SOLIDE, 0,01 m) ; nœud diagonale–montant à
  |Y| = 0,93 − e_diag = 0,68 ; pannes à +1,375 reliées aux montants et aux diagonales (LIAISON_SOLIDE,
  0,085 m). Les quatre pannes (Y = 0,56 ; 0,19 ; −0,18 ; −0,55) sont toutes entre ±0,68 et croisent
  chaque diagonale.
- **Panne de rive du porte-à-faux** : inchangée (plan des poutres, section des pannes, hypothèse du lot
  51 ter) ; les pannes du porte-à-faux y restent liées (0,075 m). Hors de P64, non modifiée.
- **Sections** : montants et diagonales `RECTANGLE` H = 0,12, EP = 0,006 (6082-T6 : mêmes E, ν, α, ρ
  que l'aluminium du projet) ; pannes 50 × 50 × 5 (B52, A52) ou × 4 (B52P4, même maillage que B52 :
  mêmes cotes extérieures).
- **Cas unitaires et règles** : ceux du lot 51 quater (221 cas, largeurs inchangées, HU_PANNES 0,05 m
  par panne ; P60 avec le coefficient des pannes de 50 : 1,91 ; P61 ; P62 : HU, HD et HU_IMP dans
  l'enveloppe de flèche de l'ELS caractéristique, comme au lot 51 quater).
- **Géométrie des nœuds** : cotes de dessus et de dessous = axe ± demi-cote extérieure du tube
  (montants 120, pannes 50, poutres 200). Croisement montant/poutre : le montant aboute le flanc de la
  poutre ; le jeu rapporté est vertical (marge du montant dans la hauteur du flanc : dessus de la poutre
  − dessus du montant et dessous du montant − dessous de la poutre), la zone de soudure projetée sur la
  poutre vaut 120 + 2 × 30 = 180 mm (bhaz = 30 mm, P63).
- **Famille « tronçon de montant »** : éléments du groupe MONTANTS_TRONCONS (|Y| ≥ 0,68) ; famille
  « montants » de la comparaison : tous les éléments des montants.
- **Support commun des MED** (défaut signalé au lot 51 quater) : MEDReader ne déforme qu'avec un champ
  aux nœuds, et un champ ELNO n'est pas un champ aux nœuds. Solution retenue : dans `resultats.med`, un
  second maillage `PONTON_B52_ELNO` où chaque SEG2 des barres a ses deux nœuds propres ; DEPL (copié du
  nœud d'origine) et efforts N, VY, VZ, MT, MFY, MFZ (valeur ELNO de l'extrémité) y sont deux champs aux
  nœuds du même maillage, ce qui permet de colorer la déformée par composante d'effort ; les champs du
  maillage d'origine sont conservés.
- **Vues** : côtés nommés « vue depuis la culée » (X = 0) et « vue depuis le porte-à-faux » (X max) ;
  vue 8 en plan (dessus, projection parallèle) de T1 et PT1 ; vue 9 : nœud poutre / montant / diagonale
  / panne en volume à leurs sections et à leurs cotes ; vue 6 : coupe transversale au droit de
  l'axe de C1 de P1, axe Ø 24 dessiné comme une barre selon Y, étrier en T (semelle 12 mm, oreilles
  15 mm), joues 15 mm, platine 20 mm sur calage 15 mm, tiges M20, cotes du schéma v4
  (`donnees/sources/schema_appui_articule_v4.pdf`) ; les largeurs en Y non cotées sur le schéma sont
  lues à l'échelle du dessin (représentation).
