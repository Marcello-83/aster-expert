# Lot 37 — Corrections issues de la relecture des résultats du lot 36

Rapport d'essai (modèle : `docs/modele_rapport_essai.md`). La section « Critère de
réussite » est écrite **avant** toute exécution du lot et n'est pas modifiée après elle ;
les sections suivantes sont ajoutées après les exécutions.

## Objet

1. Corriger la section des tirants de bord (décision 8, point 7, v4 : les tirants 1 et 9,
   situés dans les plans de symétrie, ont une **demi-section**) et ajouter au générateur un
   contrôle générique de ce type d'omission.
2. Enregistrer à l'identique les décisions D14, D15 et D16 de MM (étape 2 du lot) ; établir
   l'identifiant de la poutre de Timoshenko par la documentation et le catalogue ;
   l'appliquer au générateur (la décision 14 change la formulation de la poutre de
   couronnement).
3. Ajouter à `aster-expert report` les **efforts d'ensemble des tubes vus comme des
   poutres** : `N(z)`, `M(z)`, `T(z)` de chaque tube, et un contrôle de statique à la cote
   de dragage.
4. Une exécution du modèle complet (Code_Aster 17.4.0, image `sha256:d8d19ea9…`), avec les
   contrôles de niveau D du lot 35 et la synthèse enrichie ; comparaison avant/après des
   efforts des tirants et de la poutre sous G et Q3.

Niveau de validation visé : **C avec contrôles D** sur le modèle complet. Jamais E (aucune
référence validée).

## Ce que les prototypes ont déjà montré (déclaré avant le critère)

Le contrôle de statique (étape 3) a été mis au point sur le MED de résultats du lot 36
(`résultats_MED_Paravis/quai_combiwall_resultats_base.med`, modèle du lot 36, non celui du
lot 37) : c'est de là que viennent le choix de la cote de coupure (première rangée au-dessus
du dragage, sans nœud à ressort), la prise de la moyenne des estimations par le haut et par
le bas, et l'ordre de grandeur des seuils ci-dessous (écarts de ~1 % sur T et M). Les
seuils n'ont pas été serrés pour « passer » : 5 % laisse une marge de cinq sur ce qui a été
vu. Les résultats du modèle du lot 37 ne sont pas connus au moment où ce critère est écrit.

## Critère de réussite (écrit avant l'exécution)

| Id | Grandeur | Attendu et origine | Nature | Seuil de réussite |
| --- | --- | --- | --- | --- |
| C1 | Section de barre de `TIRANT_01` et `TIRANT_09` dans le `.comm` généré du modèle complet ; des sept autres | A/2 = 0,00221 m² ; A = 0,00442 m² (décision 8 ; `tirants.section_brute`) | exacte | égalité à 1e-12 en relatif (lecture du `.comm` par `ast`) |
| C2 | Le contrôle générique refuse le `.comm` du lot 36 | contrôle `check_symmetry_plane_sections` | exacte | refus (test) |
| C3 | Niveau B du `.comm` du modèle complet (`validate_comm`) | catalogue 17.4.0 | exacte | `valid = true`, aucune commande non vérifiée |
| C4 | `MODELISATION` de la poutre de couronnement | `POU_D_T` (U3.11.01, catalogue d'`AFFE_MODELE`) | exacte | présent dans le `.comm`, `POU_D_E` absent |
| C5 | Exécution du modèle complet | Code_Aster 17.4.0 | exacte | `DIAGNOSTIC JOB : OK`, 0 `<F>`, `<E>`, `<S>`, `<A>` |
| C6 | Effort des tirants sous G, EAU_P, EAU_A, Q1 (charges uniformes le long du quai) : (a) `N(TIRANT_01) / N(TIRANT_05)` ; (b) dispersion des `N` des tirants 2 à 8 | (a) 0,5 ; (b) nulle : maillage et charge symétriques par rapport aux plans de coupe, la solution est périodique (tirants intérieurs égaux, tirant de bord = moitié) | exacte | (a) et (b) à 1e-6 en relatif, pour chacun des quatre cas |
| C7 | Contrôles de niveau D du lot 35 : équilibre X, Y, Z de G, EAU_P, EAU_A, Q1 (`scripts/analyze_lot34_equilibre.py`) ; symétrie des déplacements | charge appliquée intégrée indépendamment (poids des tirants de bord à demi-section) + réactions bloquées + ressorts = 0 | exacte | 1e-6 en relatif sur chaque composante et chaque cas (seuil du script) |
| C8 | Statique des efforts d'ensemble à `z = −11,75 m` (première rangée au-dessus du dragage) : `T_y` et `M_x` mesurés (intégrales des efforts de coque, tubes et palplanches) contre le corps inférieur (poussée, ressorts, pied, poids) — **ensemble** de l'ouvrage, les six cas | statique du corps inférieur (`aster_expert.report.section_statics`) | sensible à la discrétisation | écart relatif ≤ 5 % pour `T_y` et `M_x`, chaque cas |
| C9 | Idem C8 sur la **cellule** de `TUBE_05` (tube + demi-palplanches), cas uniformes G, EAU_P, EAU_A, Q1 | statique du corps inférieur de la cellule (symétrie de mi-palplanche à mi-palplanche) | sensible à la discrétisation | écart relatif ≤ 5 % pour `T_y` et `M_x`, chaque cas |
| C10 | Décroissance de l'écart de C8 et C9 avec le raffinement ×2 sur le quai réduit (`taille_verticale_visee` 0,25 m → 0,125 m, trois entraxes réduits, mêmes charges) | l'erreur d'intégration des efforts par élément aux nœuds décroît avec h | sensible à la discrétisation | pour chaque (cas, portée, grandeur T ou M) dont l'écart grossier est ≥ 1e-3 : écart fin < écart grossier |
| C11 | Intégration des efforts de coque sur la circonférence, tube synthétique à 40 facettes | `N = NXX × périmètre du polygone` ; `M` du polygone en forme fermée ; écoulement de cisaillement d'un tube mince : `T = V` | exacte (N, M) / facettisation (T, `QX`) | N, M : 1e-12 ; T, `QX` : 1 % (erreur de facettisation O(1/n²) à 40 facettes) |
| C12 | Décisions D14, D15, D16 dans la fiche | texte de l'énoncé de MM | exacte | égalité du texte (test) ; historique des décisions précédentes conservé ; fiche sans bloqueur |

Informatif, sans critère ni verdict (CLAUDE.md, principe 6) : le tableau avant/après des
efforts des tirants et de la poutre sous G et Q3 (avant = lot 36, base) ; les profils
`N`, `M`, `T` de `TUBE_05` et `TUBE_01` ; la part `QX` de `T` ; `N` de la statique (il n'entre
pas dans C8/C9 : c'est une différence de grandes valeurs, sensible aux efforts membranaires
des palplanches).

Règle : toute autre issue est un échec, rapporté tel quel.

## Modèle et exécution

- Générateur de production (`aster_expert.generation.generate`, aucune option de diagnostic) :
  `scripts/generate_lot37.py`. Fiche : `hypotheses_combiwall_reference_arbitree.json` avec
  les décisions 14, 15, 16 (`scripts/build_combiwall_reference.py`, `lot37_*` de
  `data/examples/combiwall_inputs/`). Image `sha256:d8d19ea9…`, Code_Aster 17.4.0.
- `.comm` (`data/examples/lot37_efforts/`) : modèle complet `complet.comm` (SHA-256
  `093bb1ac…`, 3 720 lignes, niveau B par `validate_comm` : `valid = true`, **265 commandes
  confrontées sur 265**, aucune non vérifiée) ; quai réduit `reduit.comm` (`231e10bb…`) et
  `reduit_fin.comm` (`e04faa42…`, maillage `taille_verticale_visee` 0,125 m, 20 208 nœuds contre
  10 204, `mesh check` : tous les invariants tenus). Différence entre `complet.comm` et le
  `.comm` du lot 36 : l'en-tête (empreinte de la fiche), `POU_D_T` et les deux occurrences de
  `BARRE` — rien d'autre (`diff`).
- Exécutions Code_Aster : quai réduit 175,4 s (`20260925T124252-5122d9f4`), quai réduit fin
  336,4 s (`20260925T124551-83f1dfda`), **modèle complet 430,3 s** (`20260925T125131-c67e28a1`) :
  trois `DIAGNOSTIC JOB : OK`, 0 ligne `<F>`, `<E>`, `<S>`, `<A>`. Cumul 942,1 s ; une seule
  exécution du modèle complet. Un maillage Salomé (183,6 s) — le premier lancement, en double
  par erreur de ma part (deux processus concurrents), a produit un second maillage identique
  non utilisé.
- Autres commandes : `aster-expert report` (modèle complet avec vues : 3 min 30 ;
  contrôles D `analyze_lot34_charge_assemblee.py` puis `analyze_lot34_equilibre.py`).
  `config/validation.yaml` : racine `data/examples/lot37_efforts` ajoutée aux
  `allowed_roots` (comme à chaque lot).

## Résultats

| Id | Résultat obtenu | Verdict |
| --- | --- | --- |
| C1 | `TIRANT_01`, `TIRANT_09` : 0,00221 ; `TIRANT_02` à `08` : 0,00442 ; écart 0 | réussi |
| C2 | le contrôle refuse le `.comm` du lot 36 (`test_check_fails_on_the_lot36_comm`) | réussi |
| C3 | niveau B 265/265, `valid = true` | réussi |
| C4 | `POU_D_T` présent, `POU_D_E` absent | réussi |
| C5 | trois exécutions `DIAGNOSTIC JOB : OK`, 0/0/0/0 | réussi |
| C6 | `N1/N5` = 0,500000000000041 (G), 0,49999999999996 (EAU_P), 0,49999999999942 (EAU_A), 0,49999999999975 (Q1) ; dispersion des tirants 2 à 8 : 6,9e-13, 9,8e-13, 1,7e-12, 5,5e-13 | réussi (seuil 1e-6) |
| C7 | équilibre X, Y, Z de G, EAU_P, EAU_A, Q1 : au plus 2,8e-12 (DZ de G : 8,1e-14, le poids des tirants de bord à demi-section est bien pris en compte) ; symétrie, 20 057 paires, six cas : au plus 5,2e-11 | réussi (seuil 1e-6) |
| C8 | ensemble, six cas, à −11,75 m : T de 0,89 à 1,39 %, M de 0,52 à 1,62 % | réussi (seuil 5 %) |
| C9 | cellule de `TUBE_05`, G, EAU_P, EAU_A, Q1 : T de 0,89 à 0,93 %, M de 1,19 à 1,62 % | réussi (seuil 5 %) |
| C10 | quai réduit, 0,25 → 0,125 m : T 0,89-1,39 % → 0,19-0,38 % (facteur 3,7 à 4,7) ; M 0,52-1,62 % → 0,18-0,83 % (facteur 1,9 à 2,9) ; les 20 lignes (cas, portée, T/M) décroissent | réussi |
| C11 | tests unitaires (`test_report_sections.py`) : N, M exacts à 1e-12, T et `QX` à 1 % (0,4 % à 40 facettes) | réussi |
| C12 | `test_lot37_decisions.py` : textes identiques, historique conservé, 0 bloqueur de génération | réussi |

Détail : `data/examples/lot37_efforts/rapports/criteres_lot37.json`,
`equilibre_complet.json`, `tableau_avant_apres.md`, `complet/` (synthèse, contrôles, JSON,
54 vues dont `efforts_tube_<cas>.png`).

## Verdict

Les douze critères sont tenus ; aucun n'a été relâché ni modifié après l'exécution.
Niveau atteint : **C avec contrôles D** sur le modèle complet, jamais E.

## Lecture

**Faits.**
- Le tirant de bord porte désormais la moitié de l'effort d'un tirant courant (G : 212,6 kN
  contre 425,1 kN ; avant, 324,6 kN contre 396 kN), et les tirants 2 à 8 sont égaux entre eux
  sous charge uniforme : avant, ils variaient de 394,0 à 396,3 kN, effet de bord du défaut.
- Sous G (charge uniforme), les efforts de la poutre de couronnement sont **nuls** : avant,
  VY valait ±103,8 kN et MFZ jusqu'à −399,5 kN·m. Ce n'était donc pas un effet de la charge
  mais du défaut de bord. Sous Q3 les efforts de poutre changent de 1 à 14 % (MFZ min
  −864,3 → −752,2 kN·m) ; les tirants courants changent de +7 % (G, 396 → 425 kN).
- `T` ne se réduit pas à la part `NXY` : près de la tête, la part `QX` (cisaillement
  transversal, normal à la coque) domine (TUBE_05, G, cote 2,60 m : `NXY` +31,5 kN, `QX`
  −122,4 kN, total −90,9 kN). La définition de l'énoncé (`∫ NXY · composante horizontale`)
  aurait donné un signe opposé à cette cote. À l'endroit du contrôle (−11,75 m) `QX` est
  négligeable (−0,02 kN).
- `M(z)` de `TUBE_05` sous G passe par un extremum (−1 688 kN·m) à −4,75 m, cote où `T` change de
  signe ; `T` maximal −580,8 kN à −11,75 m. `TUBE_01` (demi-tube) : la moitié.
- La statique du corps inférieur (poussée, ressorts, pied, poids) égale les efforts d'ensemble
  intégrés à 0,9 % (T) et 1,2 à 1,6 % (M), erreur divisée par 2 à 4 par le raffinement.

**Déductions.**
- Le raffinement porte sur la taille verticale seulement (les 40 facettes de tube et les cinq
  segments de palplanche par panneau restent) : la décroissance mesurée est celle de l'erreur
  verticale ; la contribution de la facettisation à l'écart résiduel n'est pas isolée.
- Les changements de la poutre et des tirants viennent de **deux** modifications simultanées
  (demi-section, `POU_D_T`) : le tableau ne les sépare pas.

**Recommandations (pas de décision).** Lire l'effort tranchant d'un tube avec ses deux parts ;
ne pas utiliser `T` près de la tête (zone d'encastrement, hors domaine de la décision 14).

## Écarts au périmètre demandé et limites

- **La cote du contrôle n'est pas −12,00 m mais −11,75 m** (première rangée au-dessus du
  dragage) : la rangée du dragage porte les forces nodales des premiers ressorts, la coupure y
  est ambiguë (écarts de ~20 % entre estimations par le haut et par le bas, vus sur le MED du
  lot 36). Les profils donnent aussi −12,00 m.
- La cellule de `TUBE_05` (statique sur la portée d'un tube) n'existe que pour les charges
  uniformes ; Q3 et A ne sont contrôlés que sur l'ensemble.
- L'effort normal de la statique n'entre dans aucun critère : écart de 1 à 7 % (différence de
  grandes valeurs).
- `M` ne contient que `∫ NXX·y ds` ; le moment de flexion de paroi est donné à part par la
  statique (négligeable).
- Sonde de charge assemblée non relancée sur le modèle complet : la charge appliquée est
  l'intégrale indépendante (poids des tirants de bord recalculé à demi-section dans
  `analyze_lot34_charge_assemblee.py`).
- Les conditions de symétrie ont été sourcées pour `POU_D_E` ; `POU_D_T` a les mêmes six degrés
  de liberté (U3.11.01), et l'exécution passe, mais aucun constat ne le dit.
- La fiche ne dit plus, dans la décision 4 révisée, ni « maillage coïncident » ni
  `LIAISON_SOLIDE` (texte de MM enregistré à l'identique) : ils restent dans l'historique.
