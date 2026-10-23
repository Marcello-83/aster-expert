# Essais du lot 54 — PONTONS-ALU-01 : géométrie PRO définitive (treillis régulier, chevêtres 0,60), houle 5 kPa, recalcul complet

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot54_consigne.md` (copie de
`prompt_lot54_v3.md`). Code_Aster 17.4.0 (image `simvia/code_aster:17.4.0`, digest
`sha256:d8d19ea9…`). La géométrie change (P67, P68) : le maillage, le `.comm` et les 221 cas
unitaires sont recalculés pour B54 et A54, puis recombinés avec la houle de P69 et la règle P70.
B52 du lot 52 est recombiné avec les mêmes règles pour la comparaison. Calcul linéaire seulement.
Aucune vérification EC9, béton armé ou appareil d'appui ; aucun ancrage modélisé.

## Objet

Acter P67 à P76 (MM, 20 au 22/10/2026) : treillis horizontal régulier, montants à Xd + k × 1,25
(P67, P64 révisée) ; chevêtres 0,60 × 0,40 prolongés à Y = ±1,20 (P68, P43 et P48 révisées) ;
houle de projet de 5 kPa, HU_F majorant, aucun impact (P69, P56, P60 et P62 révisées, P61
annulée) ; accostage et amarrage local jamais au même poste (P70) ; P71 à P76 sans effet sur le
modèle. Produire le modèle final du PRO, ses exports, la géométrie des nœuds, les déplacements de
B54, la comparaison B52/B54 et les vues des notes.

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | `mesh check` des maillages des géométries A et B (`maillage_ponton_52.py`, paramètres X_MONTANTS, B_CHEVETRE, Y_CHEVETRE) contre les invariants calculés depuis les seuls paramètres (`invariants_lot54`) | tous les invariants tenus | exacte | aucun écart |
| 2 | Niveau B des deux `.comm`, puis exécution jusqu'à `FIN` | `valide`, toutes les commandes confrontées ; `completed_ok` | exacte | — ; les alarmes sont rapportées |
| 3 | Harnais D du tronc commun (équilibre de chaque cas : réactions de la culée et forces des ressorts contre la résultante déclarée), 221 cas par variante | 221/221 | exacte (équilibre discret) | seuils de `projet.yaml` (10⁻⁶ relatif, 1 N absolu pour les cas thermiques) |
| 4 | `geometrie_noeuds.csv` (B54, A54) : jeu à chaque croisement (dessous de la barre du dessus − dessus de la barre du dessous), zone de soudure projetée sur la poutre (largeur du montant + 2 × 30 mm) ; longueur de chaque diagonale des grandes travées, d'un bout à l'autre, lue sur les nœuds du maillage | aucun recouvrement ; zone ≤ 200 mm ; 25 diagonales de même longueur | exacte (cotes sur la grille de 1 mm) | jeu ≥ −10⁻⁶ mm ; zone ≤ 200 mm ; max − min ≤ 1 mm |
| 5 | Résultantes de HU (5,0 × (0,40 + 0,20 + 1,327)), HD (5,0 × 1,895) et HU_F (2,728 × 0,40 + 2,516 × 0,20 + 2,425 × 1,327), en kN/m, sur la longueur chargée : Σ coefficient × résultante déclarée des cas unitaires contre la formule, puis contre les réactions verticales de l'exécution (axes de la culée + ressorts des semelles) | égalité ; somme nulle | exacte | 10⁻⁶ en relatif |
| 6 | Poids propre d'un chevêtre : section (HY, HZ) et masse volumique du béton lues dans le `.comm`, longueur lue sur les nœuds du maillage, contre 0,60 × 0,40 × 2,40 × 25 = 14,4 kN | égalité | exacte | 1 % (consigne) |
| 7 | Somme des modules égale au cas total (G2, Q, QD et les quatre cas de houle, DEPL de tous les nœuds) | égalité | exacte (linéarité) | 10⁻⁹ × max \|u\| du cas total |
| 8 | Sous AM1 seul (±X) : ΣRX des palées (ressorts) ; ΣRX de la culée + force appliquée | ≈ 0 | exacte (culée seul point fixe en X) | 10⁻⁶ × force appliquée |
| 9 | Sous TP : DX de l'axe de C2 de P5 (porté par l'oreille 1) contre α·ΔT·38,85 (α = 23·10⁻⁶ /K, ΔT = +46 K) | égalité | sensible aux liaisons | 1 % en relatif |
| 10 | Centres des zones d'accostage de la géométrie contre ceux de P70 (Xd + 0,5 ; (Xd + Xf)/2 ; Xf − 0,5 ; milieu de PTk ; 38,85 + Lpf − 0,5) | égalité | exacte | 10⁻⁹ m |
| 11 | Enveloppes par décomposition (maximisation conjointe des emplacements AM et AC/ACA, P70) contre (a) le `recombiner.py` livré, combinaison par combinaison, paires d'`incompatibilites.csv` exclues, et (b) l'énumération explicite (`brute_force`, emplacements liés fusionnés) : B54, 36 extrêmes tirés au sort (graine 54), dont au moins 12 gouvernés dans une branche qui contient un emplacement d'amarrage et un emplacement d'accostage ; aucune combinaison gouvernante ne contient de paire interdite | égalité ; aucune paire interdite | exacte | 10⁻⁹ en relatif ; zéro |
| 12 | Effectifs en règles (formule, `recombiner.py`, énumération des choix permis sans doublon), paires interdites rencontrées dans l'énumération ; exclusions B′, P57, structure de P70 | égalité ; 0 paire interdite ; aucune violation | exacte | égalité stricte ; zéro |
| 13 | Effet de P70 : sur toutes les extrémités de barres (N, MFY, MFZ ; ELU fondamental, ELU accidentel, ELS caractéristique ; max et min), extrêmes changés par la règle dont la combinaison gouvernante sans la règle contient une paire interdite ; 3 tirés au sort (graine 54) : valeur sans la règle, paire interdite, valeur avec la règle, combinaison avec la règle | la valeur avec la règle n'est pas plus défavorable ; sa combinaison ne contient aucune paire interdite | exacte | — |
| 14 | `efforts_elementaires.npz` (float32) relu par le lecteur indépendant contre `efforts_elementaires.csv` de B54 : 20 tirages (graine 52 du lecteur) | égalité à l'arrondi float32 | exacte | \|Δ\| ≤ 2⁻²⁴ × \|v\| (+ 10⁻³⁰) |
| 15 | Déplacements de B54 (fichiers du lot 53) : liaisons (jeu Y relatif côté YP, Z relatif) nulles ; 12 extrêmes de combinaisons contre l'énumération explicite | nul ; égalité | exacte | 10⁻⁹ |
| 16 | Fiche : `projet verifier` ; P64, P43, P48, P56, P60 et P62 avec leur ancienne version dans `decision_history` ; P61 annulée (ré-arbitrée, ancienne décision dans l'historique) | conforme | — | — |
| 17 | Chaque PNG de B54 (vues 1 à 11) : fichier non vide, fond blanc, 200 dpi ; vues 4, 6, 7 et 11 regardées à l'œil | conforme | — | — |

Rapportés sans seuil : temps de recombinaison ; `comparaison_B52_B54.csv` (une phrase par écart de
plus de 5 % ; la consigne attend des pannes moins sollicitées, des montants et diagonales du même
ordre, un ancrage des palées un peu réduit : un écart à ces attentes est rapporté tel quel, pas
corrigé) ; ancrage par palée et réactions de culée ; synthèse des déplacements. Toute autre issue
des critères 1 à 17 est un échec, rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- **Un seul script de maillage** : `maillage_ponton_52.py` accepte depuis ce lot trois paramètres
  de variante de plus, X_MONTANTS (montants intérieurs d'une grande travée, P67 : 1,25 ; 2,50 ;
  3,75 ; 5,00), B_CHEVETRE (largeur des chevêtres selon X, P68 : 0,60 ; défaut 0,40, celle du
  lot 52) et Y_CHEVETRE (extrémités, P68 : ±1,20). Avec les valeurs par défaut, le maillage, les
  invariants et les `.comm` du lot 52 sont inchangés (tests du projet).
- **Anneau** : chevêtres 0,60 × 0,40 (HY selon X pour une barre selon Y), longrines 0,40 × 0,40
  coupées au nu des chevêtres (X = xc1 + 0,30 et xc2 − 0,30) ; les morceaux de longrine dans
  l'épaisseur d'un chevêtre (ANGLES_ANNEAU) restent sans poids ni déjaugeage (béton BETON0) :
  chaque m³ de l'anneau est compté une fois. Déjaugeage : 10 kN/m³ × 0,24 m² sur les chevêtres,
  × 0,16 m² sur les longrines courantes. Liaisons LG_ (longrine–chevêtre, 1 mm), TP_ (tête de
  pile) et appuis : inchangées ; les têtes de piles restent à Y = ±0,75, les appuis à ±0,93.
- **Treillis (P67)** : N conservé (une diagonale relie le nœud à +0,68 d'un montant à celui à
  −0,68 du suivant), cinq panneaux égaux de 1,25 m ; diagonales des grandes travées de longueur
  √(1,25² + 1,36²) = 1,847 m ; petites travées et porte-à-faux inchangés ; pannes coupées aux
  nouveaux croisements ; taquets à Xd + 1,6 et Xd + 4,6.
- **Houle (P69)** : événements HU, HD, HU_F sur les cas unitaires de P56 (groupe `houle_lot54` du
  fichier de données) ; aucun impact. Les règles de combinaison sont celles du lot 51 ter (P49,
  P56 pour la place de la houle dans les états limites, P57, P59, B′). P62 révisée : HU et HD dans
  l'enveloppe de flèche de l'ELS caractéristique. Pas de sensibilité HU_S5 : sous P69, la houle de
  projet est elle-même le forfait de 5 kPa ; `ancrage.csv` et `palee_equilibre.csv` sont ceux du
  lot 51 ter (P71 : pour mémoire).
- **P70** : paires interdites entre un événement AML ou AMF du taquet k, rive s, et un événement AC
  ou ACA d'une zone de la même rive dont le centre est à moins de 1,60 m du taquet ; 20 taquets
  (10 positions × 2 rives), deux zones interdites par taquet (début et milieu, ou milieu et fin),
  soit 1 920 paires d'événements. Dans une branche, deux emplacements qui portent une paire
  interdite sont maximisés conjointement (`combinaisons_lot51ter.Exclusion`, `joint_best` :
  options du premier emplacement groupées par ensemble d'options interdites du second, meilleure
  option permise prise parmi les k meilleures, k = plus grand ensemble interdit + 1) ; les autres
  emplacements restent indépendants. Sans exclusion, le moteur est inchangé (tests des lots
  51 ter à 52). Effectifs : 2 351 600 combinaisons en règles sans P70, 2 247 920 avec P70
  (103 680 exclues), décompte de l'outil avant exécution.
- **`recombiner.py`** (`scripts/recombiner_lot54.py`, bibliothèque standard) : lit
  `incompatibilites.csv` et saute toute combinaison qui réunit une paire interdite ; ses effectifs
  énumèrent ensemble les emplacements liés.
- **B52 recombiné** : les tables de l'exécution B52 du lot 52 n'existent plus sur la VM (clone neuf
  du dépôt le 23/10/2026, résultats non versionnés perdus) ; B52 est réexécuté à l'identique par
  `scripts/lot52.py executer --variantes B52` (même `.comm`, empreinte `bd8663c6…` attendue ; même
  maillage, empreinte `2cc66b5d…` attendue ; exécution de vérification). Si une empreinte diffère,
  c'est rapporté et la comparaison porte sur la réexécution.
- **Familles de la comparaison** : poutres (POUTRES_PRINC), pannes (PANNES_SEC), montants
  (MONTANTS), diagonales (DIAGONALES), chevêtres (CHEVETRES), longrines (LONGRINES), piles (PILES) ;
  N min, N max, My et Mz extrêmes en valeur absolue (signés), V max = √(VY² + VZ²) ; ELU
  fondamental, ELS caractéristique, ELS fréquent et ELU accidentel. Plus l'ancrage requis par palée.
- **MED** : la liste des exports de la consigne ne les mentionne pas ; ils ne sont pas produits
  dans ce lot (la chaîne du lot 52 reste disponible).
- **Vues des notes** : figures matplotlib (projection parallèle, fond blanc, 200 dpi, rognées),
  16 cm de large à l'impression, texte ≥ 11 pt et légendes ≥ 10 pt à cette taille ; une couleur par
  famille (poutres principales, pannes, montants, diagonales, chevêtres, longrines, piles, semelles,
  appuis), la même sur toutes les vues ; titres courts sans « lot », variante, code interne ni
  numéro de décision. Barres dessinées à leur section (tubes et rectangles en volume pour les zooms,
  traits épais pour les vues d'ensemble) ; déformées tirées des DEPL des nœuds.
