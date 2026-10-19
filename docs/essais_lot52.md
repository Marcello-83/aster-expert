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

## 3. Exécution (après le commit du critère)

Point d'arrêt : `dc46aa5` (décisions, géométrie, critère). Toutes les exécutions Code_Aster et tous les
contrôles ont eu lieu après ce commit (`scripts/lot52.py` : `executer`, `controles`, `exports`, `med`,
`vues`, `depot` ; chaîne du tronc commun `resultats/lot52/logs/chaine_B52.sh`).

- **Arrêt de la VM** (19/10/2026, 04:25) : blocage du noyau (RCU, processeur saturé) pendant que trois
  processus de recombinaison tournaient en parallèle avec le post-traitement des livrables de B52.
  Perdus : ce post-traitement (exécution `20261019T082517-6fb933ef`, arrêtée à la commande 7, classée
  « écarté » dans `rex`) et les exports en cours. Reprise (`resultats/lot52/logs/reprise.sh`) **en
  série** : sous-étapes `livrables` executer, verifier, traiter sur le même `.comm`, puis exports avec
  deux processus au plus. Les exécutions de calcul des trois variantes et le harnais D, terminés avant
  l'arrêt, n'ont pas été relancés.
- **Vue 8** : les étiquettes des montants de PT1 étaient placées au-dessus du dessin, sous la légende ;
  elles ont été mises sous le dessin et décalées (le premier montant de PT1 est à 1 mm du dernier de T1),
  puis les vues ont été régénérées. Seule la présentation a changé.

## 4. Résultats des contrôles

| # | Résultat |
| --- | --- |
| 1 | `mesh check` 4 011/4 011 (géométrie B : B52 et B52P4 ; géométrie A : A52). |
| 2 | Niveau B `valide`, 1 616/1 616 commandes (trois `.comm`) ; exécutions `20261019T080553-0565f41d` (B52, 376 s), `20261019T080552-79e7f631` (A52, 377 s), `20261019T080547-57af43ef` (B52P4, 404 s) : `completed_ok`, 0 alarme. |
| 3 | Harnais D : 221/221 pour chaque variante ; écart relatif ≤ 7,4·10⁻¹¹ ; TP et TM (critère absolu) ≤ 3,9·10⁻⁷ N. |
| 4 | `geometrie_noeuds.csv`, trois variantes, 364 croisements : panne/montant 160 et panne/diagonale 120, jeu 0,0 mm (pose directe, liaison 0,085 m) ; montant/poutre 80, marge de 30,0 mm en haut et en bas dans le flanc (liaison 0,01 m), zone de soudure 180 mm ; panne/panne de rive du porte-à-faux 4, jeu 25,0 mm. **Aucun recouvrement, zone maximale 180 mm ≤ 200 mm.** |
| 5 | HU = 142 094,5 N (B), 141 385,7 N (A) : écart à la formule 0 ; HD ≤ 1,9·10⁻¹⁶ ; HU_IMP_M0 71 058 N, M1 à M4 88 317 N, M5 31 482 N (B) / 29 208 N (A), écart 0 ; réactions contre résultantes ≤ 3,8·10⁻¹². |
| 6 | Somme des modules contre le cas total : ≤ 1,5·10⁻¹¹ × max \|u\| (G2, Q, QD, HU_TUBES, HU_PANNES, HU_PLATELAGE, HD_TABLIER ; trois variantes). |
| 7 | AM1 ±X (274 kN) : ΣRX des palées ≤ 7,6·10⁻⁸ N (≤ 2,8·10⁻¹³ relatif) ; culée + force ≤ 1,8·10⁻¹³. |
| 8 | TP : DX de l'axe de C2 de P5 = 41,094 mm contre α·ΔT·38,85 = 41,103 mm, écart 0,023 % (≤ 1 %), YM et YP, trois variantes. |
| 9 | B52, 36 extrêmes tirés au sort (graine 52, dont N, MFY, MFZ des tronçons de montant) : écart ≤ 5,1·10⁻¹⁶ contre `recombiner.py` et contre l'énumération explicite. |
| 10 | 2 364 008 combinaisons en règles (107 534 360 dispositions) par formule, `recombiner.py` et énumération sans doublon ; aucune violation (B′, P57, P61). |
| 11 | `.npz` 8,95 Mo par variante ; lecteur indépendant contre `efforts_elementaires.csv` de B52 : 20/20 tirages conformes, \|Δ\| ≤ 2⁻²⁴ × \|v\|. |
| 12 | `.comm` de la chaîne identique (sha256 `bd8663c6…`, `cmp`) ; exécution `20261019T081415-9622053e` `completed_ok` (552 s) ; post-traitement niveau B 2 515/2 515, exécution `20261019T084157-a43ab358` `completed_ok` (283 s), tables E20.12 identiques (1 412 077 valeurs) ; DEPL et EFGE_ELNO unitaires du MED contre les tables E25.16, 221 cas : écart **0**. |
| 13 | MED de B52 relus : 3 295 nœuds, 780 QUAD4, 2 776 SEG2, 910 POI1, 1 190 groupes ; `charges.med` 234 champs (225 + 9 événements), `resultats.med` 18 champs ; écart de relecture nul ; combinaisons contre les tables : 0 ; résultantes des événements ≤ 4·10⁻¹⁵ ; **support commun `PONTON_B52_ELNO`** : 4 552 nœuds, 2 276 SEG2, 25 groupes, DEPL et efforts égaux nœud par nœud au DEPL d'origine et à l'ELNO de l'extrémité (écart de construction 0). |
| 14 | 12 PNG de B52 (vues 1 à 6, 7.1 à 7.4, 8, 9) : 1 920 × 1 080, 69 à 190 ko ; regardées à l'œil : vues 4, 6, 8 et 9 (vue 9 : pannes posées sur le montant et la diagonale, sans pénétration ; montant aboutant le flanc de la poutre). |

Tous les critères sont tenus. Niveau des résultats : **D** (harnais sur les trois exécutions du lot) ; aucun
niveau E.

## 5. Résultats

Temps de recombinaison par variante (deux processus) : lecture des tables 13 à 15 s ; exports 9 à 16 s ;
comparaison 588 à 666 s ; total 597 à 679 s ; énumération de contrôle (B52) 50 s. Le lot 51 quater
donnait 280 à 290 s avec quatre processus ; la comparaison compte ici 25 grandeurs de plus (familles) et
la part de chacune de ces causes dans l'allongement n'a pas été mesurée.

Ancrage requis par palée (kN, ELU fondamental / ELS caractéristique ; sensibilité HU_S5 entre
parenthèses) :

| Palée | B52 | A52 | B52P4 | B12 (lot 51 quater) |
|---|---|---|---|---|
| P1 | 23,2 / 0 (56,2 / 6,0) | 21,2 / 0 (54,3 / 3,6) | 23,3 / 0 (56,4 / 6,1) | 22,7 / 0 (55,8 / 5,2) |
| P2 | 11,1 / 0 (44,2 / 0) | 10,6 / 0 (43,7 / 0) | 11,2 / 0 (44,3 / 0) | 10,0 / 0 (43,1 / 0) |
| P3 | 5,7 / 0 (38,8 / 0) | 5,7 / 0 (38,8 / 0) | 5,8 / 0 (38,9 / 0) | 4,6 / 0 (37,7 / 0) |
| P4 | 0 / 0 (28,9 / 0) | 0 / 0 (30,9 / 0) | 0 / 0 (29,1 / 0) | 0 / 0 (27,8 / 0) |
| P5 | 0 / 0 (3,6 / 0) | 0 / 0 (1,2 / 0) | 0 / 0 (3,7 / 0) | 0 / 0 (3,0 / 0) |

Extrêmes par famille de B52 (kN, kN·m ; quatre états limites comparés) : poutres N −278,3 / +293,6,
My −71,8, Mz 17,6, V 49,2 ; pannes N −41,0 / +24,4, My 0,79, Mz −0,54, V 8,1 ; montants N −67,5 / +61,6,
My 5,7, Mz 11,5, V 56,0 ; diagonales N −76,5 / +76,2, My −4,9, Mz −2,3, V 11,2. **Les extrêmes des
montants sont tous dans les tronçons entre la poutre et le nœud de diagonale** (famille TRONCON égale à
la famille MONT sur les cinq grandeurs, trois variantes).

Comparaison B52 contre B12 du lot 51 quater (`comparaison_B52_B12_lot51quater.csv`) : flèches de l'ELS
fréquent plus grandes de 3,9 à 5,4 % (T1 à T5, PF), de l'ELS caractéristique de 1,5 à 4,8 % ; PP My
−71,8 contre −69,3 kN·m (+3,6 %) ; glissement des axes à l'ELU 110,3 contre 114,3 mm (−3,5 %) ; ancrage
par palée +0,4 à +1,1 kN ; culée ΣRX ELU inchangé (435,7 kN) ; piles, anneau, chevêtres, longrines : écarts de −2,3 à +4,6 % (torsion des chevêtres).
Deux extrêmes signés changent de signe avec un module voisin : culée RX d'un axe (−301,7 contre
+312,6 kN) et flèche caractéristique du porte-à-faux (−1,1 contre +1,0 mm).

## 6. Limites

- Niveau D au mieux ; aucun niveau E. Ni EC9, ni béton armé, ni appareil d'appui ; aucun ancrage
  modélisé.
- Liaisons montant/poutre (0,01 m) et panne/barre (0,085 m) rigides (LIAISON_SOLIDE) : la souplesse
  locale des parois soudées n'est pas représentée ; le moment des tronçons de montant en dépend.
- Panne de rive du porte-à-faux inchangée (plan des poutres, hypothèse du lot 51 ter) : hors de P64.
- Vue 6 : les largeurs en Y non cotées sur le schéma v4 sont lues à l'échelle du dessin (représentation).
- La comparaison avec B12 mélange trois changements (sections des pannes, sections et cote des montants,
  axe des appuis) : les écarts ne sont pas attribués séparément à chacun.
