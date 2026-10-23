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

## 3. Exécution (après le commit du critère)

Point d'arrêt : `425101f` (décisions, géométrie, moteur P70, critère). Toutes les exécutions
Code_Aster et tous les contrôles ont eu lieu après ce commit (`scripts/lot54.py` : `executer`,
`controles`, `exports`, `vues`, `depot`).

- **Clone neuf** : le dépôt de la VM a été recloné le 23/10/2026 à 03:32 ; `external/`, les
  index, le catalogue extrait, `.env` et tous les résultats non versionnés des lots précédents
  avaient disparu. Remise en état par les commandes du dépôt (`docs/cloud.md` § 6) : `sources
  sync`, `inventory`, `xref`, `catalogue extract` (avec `ASTER_CONTAINER_WORKROOT =
  data/processed/workroot`, `config/versions.yaml` remis à sa version versionnée, même digest),
  `command-map`, `fragments build`, `index build`. `mcp-check` : 9 outils sur 10 ; `query_results`
  échoue faute de livrables locaux d'un projet (les reconstruire supposerait de relancer la chaîne
  d'un autre projet, hors consigne). Crochet Git et identité Git configurés dans le clone.
- **Exécutions** : B54 `20261023T081230-ebb19a19` (282 s) et A54 `20261023T081229-c87839be`
  (283 s) ; B52 réexécuté à l'identique par `scripts/lot52.py executer --variantes B52`
  (`20261023T081258-b7cc6e93`, 257 s ; exécution de vérification).
- **B52 réexécuté** : `.comm` identique (sha256 `bd8663c6…`) ; le MED régénéré a une autre
  empreinte (`fc7735bf…` au lieu de `2cc66b5d…`) mais le même contenu : contre les fichiers du
  lot 52 déposés sur le partage (`scripts/verifier_reexecution_B52_lot54.py`), 3 295 nœuds à
  4,3·10⁻¹³ m près et mêmes groupes, 2 276 éléments identiques, 6 035 952 efforts unitaires
  égaux en float32, 4 641 réactions unitaires à écart nul.
- **Corrections en cours de lot** (code d'exports seul, aucune exécution rejouée) : cache de
  lecture des MED dans un dossier du lot 51 absent du clone (créé) ; contrôles des diagonales
  et du poids des chevêtres filtrés sur le groupe de la barre et non sur le nom du membre.
- **Vues** : plusieurs passes de mise en page (zoom des axes 3D, valeurs aux palées en tableau
  sous le dessin, cotes de la coupe et du plan) ; canevas fixé à 16 cm (1 260 px à 200 dpi) pour
  que le texte imprimé reste à sa taille en points. Seule la présentation a changé.

## 4. Résultats des contrôles

| # | Résultat |
| --- | --- |
| 1 | `mesh check` 4 011/4 011 (géométries B et A). |
| 2 | Niveau B `valide`, 1 616/1 616 commandes (B54, A54, et B52 réexécuté) ; trois exécutions `completed_ok`, 0 alarme. |
| 3 | Harnais D : 221/221 pour B54 et A54 ; écart relatif ≤ 1,4·10⁻¹⁰ (B54), 1,5·10⁻¹⁰ (A54) ; TP, TM (critère absolu) ≤ 5,5·10⁻⁷ N. |
| 4 | `geometrie_noeuds.csv`, B54 et A54, 364 croisements : panne/montant 160 et panne/diagonale 120, jeu 0,0 mm ; montant/poutre 80, marge 30,0 mm, zone de soudure 180 mm ; panne/panne de rive 4, jeu 25,0 mm. **Aucun recouvrement, zone ≤ 200 mm.** 25 diagonales des grandes travées : 1,847187 m, écart max − min 2,4·10⁻¹⁵ m (nœuds du maillage). |
| 5 | HU, HD, HU_F : écart à la formule ≤ 1,5·10⁻¹⁶, réactions contre résultantes ≤ 1,4·10⁻¹² (B54 et A54). |
| 6 | Chevêtre (HY 0,6, HZ 0,4, RHO du `.comm`, longueur 2,40 m sur les nœuds) : 14,4 kN pour les 10 chevêtres, écart 0. |
| 7 | Somme des modules contre le cas total : ≤ 1,3·10⁻¹¹ × max \|u\|. |
| 8 | AM1 ±X : ΣRX des palées ≤ 3,5·10⁻¹³, culée + force ≤ 3,0·10⁻¹³ (relatif). |
| 9 | TP : DX de l'axe de C2 de P5 = 41,094 mm contre 41,103 mm, écart 0,023 % (YM, YP, deux variantes). |
| 10 | Centres des 21 zones d'accostage : écart ≤ 7,1·10⁻¹⁵ m aux formules de P70. |
| 11 | 36 extrêmes (graine 54), dont **27** gouvernés dans une branche AM + AC : écart ≤ 5,8·10⁻¹⁶ contre `recombiner.py`, ≤ 3,9·10⁻¹⁶ contre l'énumération explicite ; aucune paire interdite dans les combinaisons gouvernantes. |
| 12 | 2 247 920 combinaisons (102 775 712 dispositions) par formule, `recombiner.py` et énumération sans doublon ; 0 paire interdite énumérée ; 1 920 paires dans `incompatibilites.csv`, égales à celles de l'outil ; 14 branches portent P70 ; 103 680 combinaisons exclues (2 351 600 sans P70) ; aucune violation de B′ ni de P57. |
| 13 | 82 296 extrêmes examinés, 1 539 changés par P70 avec une paire interdite dans la combinaison sans la règle. Trois tirés au sort : panne PANNE_T1_4 MFY ELU f. max 259,7 → 258,2 N·m (AML_TQ1_YM_PERP avec AC_T1M_YM_+Z ; avec la règle : AML_TQ3_YP_PERP) ; panne PANNE_T3_1 MFZ ELU f. max 49,0 → 48,5 N·m (AML_TQ6_YP_PERP avec AC_T3M_YP_-Z ; avec la règle : AC_T3M_YM_-Z) ; diagonale DIAG_T4_3 MFZ ELU acc. max 941,8 → 873,2 N·m, −7,3 % (ACA_T4M_YP_-Z avec AML_TQ8_YP_PERP ; avec la règle : AMF_TQ8_YP_PERP + AC_T4F_YM_-X). Aucune paire interdite avec la règle, aucune valeur plus défavorable. |
| 14 | `.npz` relu par le lecteur indépendant : 20/20 tirages conformes. |
| 15 | Déplacements de B54 : liaisons ≤ 3,8·10⁻¹⁶ (relatif) ; 12 extrêmes contre l'énumération : ≤ 1,9·10⁻¹⁵. |
| 16 | `projet verifier` : déclaration cohérente, 86 entrées, aucun bloqueur ; P43, P48, P56, P60, P61, P62, P64 avec leur ancienne décision dans `decision_history` ; P61 annulée (« P61 est annulée » dans l'option retenue). |
| 17 | 13 PNG (vues 1 à 10, 11 A, B, C) : non vides, fond blanc, 200 dpi, largeur ≤ 1 260 px (16 cm). Vues 4, 6, 7 et 11 regardées à l'œil, ainsi que 1, 3, 5, 8, 9 et 10. |

Tous les critères sont tenus. Niveau des résultats : **D** (harnais sur les exécutions du lot) ;
aucun niveau E.

## 5. Résultats

Temps de recombinaison (deux processus) : B54 1 117 s, A54 1 099 s (dont comparaison et
familles 1 090 à 1 102 s), B52 948 s (familles et ancrage seuls) ; énumération de contrôle 41 s ;
effet de P70 3 s ; déplacements 2 s.

Ancrage requis par palée (kN, ELU fondamental / ELS caractéristique ; aucun ancrage modélisé,
P71 : pour mémoire) :

| Palée | B54 | A54 | B52 sous P69/P70 |
|---|---|---|---|
| P1 | 51,1 / 0 | 49,1 / 0 | 56,2 / 6,0 |
| P2 | 39,0 / 0 | 38,5 / 0 | 44,2 / 0 |
| P3 | 33,6 / 0 | 33,6 / 0 | 38,8 / 0 |
| P4 | 23,7 / 0 | 25,7 / 0 | 28,9 / 0 |
| P5 | 0 / 0 | 0 / 0 | 3,6 / 0 |

Gouvernant : G_DEJ_090 + 1,5 HU + accompagnements T et AM. B52 sous P69 retrouve les valeurs
HU_S5 du lot 52 (même forfait de 5 kPa). La baisse de 5,2 kN à chaque palée égale le poids
déjaugé supplémentaire de l'anneau à l'ELU : chevêtres +0,48 m³, longrines −0,064 m³, soit
0,9 × 25 × 0,416 − 10 × 0,416 = 5,2 kN (calcul à la main, égal à l'écart des enveloppes).

Culée (B54, ELU fondamental) : ΣRX 435,7 kN (inchangé, fixé par AM1) ; RX d'un axe −300,8 kN ;
RY ±75,6 kN (axe YP) ; RZ de −22,7 à +52,9 kN.

Flèches de B54 (variables seules, relatives à la corde) : ELS fréquent L/288 à L/326, ELS
caractéristique L/172 (T2, −36,3 mm) à L/231 ; soulèvement de T2 sous la houle (ELS
caractéristique) +34,9 mm (L/179).

Comparaison B52 / B54 (`comparaison_B52_B54.csv`, écarts de plus de 5 %) :

- pannes : |Mz| −22 % (0,54 → 0,42 kN·m) et V −24 % (8,1 → 6,1 kN) ; |N| et My à ±3 % ;
- montants : |My| −14 % (5,7 → 4,9 kN·m) ; N, Mz, V à ±3 % ;
- diagonales : |My| −14 % (4,9 → 4,3 kN·m), V +18 % (11,2 → 13,2 kN, DIAG_T1_1 près de la culée) ;
- longrines : N ±0,6 kN, écarts de 8 et 15 % sur des valeurs sans portée ;
- ancrage : −9 à −18 % à l'ELU (−5,2 kN par palée), nul à l'ELS caractéristique pour P1 (6,0 → 0)
  et à l'ELU pour P5 (3,6 → 0).

Déplacements de B54 (`deplacements_synthese.csv`) : à 0,2 mm près ceux de B52 du lot 53 ;
DY max 78,9 mm au bout du porte-à-faux (ELU accidentel), 55,9 mm (ELS caractéristique) ; DX de
l'axe de P5 hors thermique 31,9 mm (ELS caractéristique).

## 6. Limites

- Niveau D au mieux ; aucun niveau E. Ni EC9, ni béton armé, ni appareil d'appui ; aucun ancrage
  modélisé.
- MED non produits (non demandés par la liste des exports) ; la chaîne du lot 52 reste disponible.
- Liaisons rigides : souplesse des parois soudées non représentée (moments des tronçons de montant
  et des diagonales près des nœuds).
- La hausse de V des diagonales (+18 %) n'est pas isolée par un calcul ; explication probable
  (déduction) : diagonales plus raides et plus courtes du treillis régulier.
- `rex` refuse l'archive locale (clone neuf, 3 exécutions sur 49 au manifeste) : les métriques
  mesurées ne sont pas recalculées ; les trois exécutions du lot ont réussi.
- `mcp-check` partiel (9/10) faute de livrables locaux d'un projet.
- Vues : 3D en projection parallèle par matplotlib ; le tri de profondeur des faces peut laisser
  de petits défauts de recouvrement dans les vues en volume ; platelage dessiné sur la coupe
  (épaisseur de dessin, non modélisé).
