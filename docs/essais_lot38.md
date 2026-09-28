# Essais lot 38 — `CALC_FERRAILLAGE` sur la section réelle de la poutre de couronnement

## Objet

Comparer l'aire d'armature que `CALC_FERRAILLAGE` (Code_Aster 17.4.0) calcule sur
la section de la poutre de couronnement (2,50 m x 1,40 m, C35/45, B500B, enrobage
nominal 65 mm, décision D18) à un calcul EN 1992-1-1 indépendant, fait par l'outil
en Python (`aster_expert.rebar`, jamais `code_aster`). Niveau C/D. **L'écart est
rapporté, il n'est pas jugé bon ou mauvais par cette session** (consigne du lot
38, étape 4).

## Critère de réussite (écrit avant l'exécution)

| Cas | N (MN, traction+) | M (MN.m) | Grandeur | Nature |
| --- | --- | --- | --- | --- |
| flexion simple | 0 | 2,183517 | ATOT (ELU) | comparaison à l'aire EN 1992 du module `aster_expert.rebar.ultimate` |
| composée compression | −5,0 | 2,183517 | ATOT (ELU) | idem |
| composée traction | +5,0 | 2,183517 | ATOT (ELU) | idem |
| ELS quasi permanente | −1,0 | 0,5 | ATOT (ELS_QP, wk = 0,2 mm) | comparaison à `aster_expert.rebar.serviceability.design_els_qp` |

M et N sont choisis pour illustrer les régimes de la commande sur la section du
projet (ordre de grandeur des efforts réels de la poutre sous les combinaisons
de D17, `data/examples/lot38_combinaisons/extrema.csv` ; N composée choisi
arbitrairement pour exercer une flexion composée, pas une valeur réelle de la
poutre). Aucun seuil n'est fixé a priori pour l'écart : il est rapporté chiffré
(CLAUDE.md, l'écart n'a pas de seuil de réussite prescrit par ce lot, contrairement
au critère habituel des essais physiques -- la grandeur comparée est un résultat
d'algorithme de dimensionnement, pas une grandeur qu'une théorie d'élément
reproduit exactement).

## Modèle et exécution

`data/examples/lot38_essais/essais.comm` (`scripts/build_lot38_essais.py`),
poutre `POU_D_E` à un élément, efforts imposés (`CREA_CHAMP/CART_SIEF_R` ->
`CREA_RESU`, schéma des cas tests officiels `ssll13*`/`ssll18*`). Validé niveau B
(`validate_comm`, 12/13 commandes confrontées ; `CREA_TABLE`/`IMPR_TABLE` non
résolues par le validateur statique, comportement connu, sans rapport avec ce
lot). Exécuté le 28/09/2026, `aster-expert run`, `DIAGNOSTIC JOB : OK`,
15,8 s, version 17.4.0, digest
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

Paramètres `CALC_FERRAILLAGE` (EC2) : `GAMMA_S=1,15`, `GAMMA_C=1,5`,
`ALPHA_CC=1,0`, `TYPE_DIAGRAMME='B2'`, `EYS=210000 MPa` (valeur usuelle de la
documentation, non une donnée du projet). ELS_QP : `ALPHA_E=15` (valeur usuelle
documentée), `SIGC_*_ELS=0,6·fck=21 MPa`, `SIGS_ELS=0,8·fyk=400 MPa`,
`SIGC_ELS_QP=0,45·fck=15,75 MPa`, `KT=0,4` (longue durée, choix motivé par la
nature permanente/quasi permanente du chargement), `WMAX_*=0,2 mm` (D18),
`PHI_*=25 mm` (valeur usuelle documentée, non une donnée du projet).

## Résultats

Premier calcul du module avec le diagramme béton parabole-rectangle (option par
défaut initiale) : écart de +0,31 % en flexion simple par rapport à
Code_Aster, alors que la flexion composée avec traction correspondait déjà à
moins de 1e-6. L'écart a conduit à comparer les deux diagrammes béton que
`R7.04.05` documente pour l'ELU (parabole-rectangle et bloc rectangulaire
simplifié) sur les cas officiels `ssll13d.comm` : le bloc simplifié reproduit
Code_Aster à 1e-6 m² près sur tous les cas aux pivots A et B essayés, le
parabole-rectangle non (écarts de 0,1 à 0,6 %) -- `CALC_FERRAILLAGE` utilise
donc en réalité le bloc rectangulaire simplifié pour son calcul ELU, une
information d'exécution que `R7.04.05` ne présente que comme une option
(`aster_expert.rebar.ultimate`, tête de fichier ; `tests/unit/
test_rebar_ultimate.py`). Le bloc rectangulaire est devenu le réglage par
défaut du module ; les résultats ci-dessous sont ceux obtenus avec ce réglage.

| Cas | ATOT Code_Aster (m²) | ATOT module (m²) | Écart relatif |
| --- | --- | --- | --- |
| flexion simple | 2,074218e-03 | 2,074218e-03 | < 1e-9 |
| composée compression | 0 | **infeasible** (voir Lecture) | sans objet |
| composée traction | 1,150000e-02 | 1,150000e-02 (7,869025e-03 + 3,630975e-03) | < 1e-9 |
| ELS quasi permanente | 0 | **infeasible** (voir Lecture) | sans objet |

Détail des faces (m²), AYS = face « supérieure » suivant Y (positive), AYI = face
« inférieure » (négative), convention du champ `FERR_ELEM` :

| Cas | AYS (Code_Aster) | AYI (Code_Aster) | as_pos (module) | as_neg (module) |
| --- | --- | --- | --- | --- |
| flexion simple | 2,074218e-03 | 0 | 2,074218e-03 | 0 |
| composée traction | 7,869025e-03 | 3,630975e-03 | 7,869025e-03 | 3,630975e-03 |

## Verdict (au regard du seul écart, sans jugement de bon/mauvais)

- Flexion simple : accord à 1e-9 (pivot A dans les deux cas) avec le diagramme
  rectangulaire simplifié.
- Flexion composée avec traction : accord à 1e-9.
- Flexion composée avec compression et ELS quasi permanente : **le module ne
  trouve aucune solution admissible** dans les familles de plans de déformation
  qu'il couvre, alors que Code_Aster trouve un ferraillage nul (section
  entièrement comprimée à l'échelle des efforts imposés, dans les deux cas :
  résultante de compression du béton seul très supérieure à N pour tout x du
  domaine entièrement comprimé sondé -- constaté par sonde directe,
  `Fc` de 66 à 82 MN pour un `N` de 5 MN demandé). La cause précise (résolution
  de balayage insuffisante, ou solution hors des trois familles couvertes par
  `aster_expert.rebar.ultimate`) n'est pas établie par cette session.

## Lecture

- Fait : avec le diagramme béton rectangulaire simplifié, les deux cas où le
  module aboutit (flexion simple, flexion composée avec traction) accordent
  avec Code_Aster à 1e-9 près.
- Fait : avec le diagramme parabole-rectangle (implémenté aussi, non retenu par
  défaut), le même essai de flexion simple s'écartait de 0,31 % -- c'est cet
  écart qui a mené à la comparaison des deux diagrammes et à la conclusion
  ci-dessus sur le comportement réel de `CALC_FERRAILLAGE`.
- Fait : sur les deux cas de compression dominante, le module ne trouve pas de
  solution alors que Code_Aster en trouve une (armature nulle).
- Déduction : le module analytique de ce lot (`aster_expert.rebar`), écrit
  indépendamment à partir de `R7.04.05`, ne couvre pas correctement tous les cas
  où le béton seul suffit sous compression dominante -- limite documentée, pas
  corrigée dans ce lot (budget de la session).
- Recommandation : ne pas utiliser `aster_expert.rebar` comme substitut à
  `CALC_FERRAILLAGE` pour un cas fortement comprimé sans vérification
  complémentaire ; pour un cas au pivot A ou B avec le diagramme rectangulaire,
  l'accord observé est net.

## Limites

- Un seul type d'élément essayé (poutre, `TYPE_STRUCTURE='1D'`) : aucun essai sur
  plaque/coque (`TYPE_STRUCTURE='2D'`) dans ce lot, faute de temps -- l'état des
  lieux documentaire (`docs/etat_des_lieux_lot38_ferraillage.md`) couvre les deux
  types, mais seuls des cas tests officiels (déjà exécutés par EDF, non par cette
  session) illustrent le 2D.
- ELS caractéristique non essayé sur la section du projet (seul ELU et ELS_QP le
  sont) ; le module `design_els` a été calibré séparément sur les cas tests
  officiels `ssll13b.comm` (`tests/unit/test_rebar_serviceability.py`) : accord
  exact sur le cas fortement tendu (extension du domaine du pivot acier aux
  sections entièrement tendues), écart de l'ordre de 10 % non expliqué sur un cas
  partiellement comprimé modéré (`test_design_els_pure_moment_is_of_the_right_
  order_but_not_exact`) -- non revu à la lumière du changement de diagramme béton
  ci-dessus (`design_els` reste sur son diagramme élastique linéaire propre à
  l'ELS, sans équivalent parabole/rectangle ; le défaut est donc distinct).
- Aucune ligne de comparaison au logiciel de flexion composée de MM n'a été
  remplie (à faire par MM : voir `data/examples/lot38_essais/ligne_comparaison_mm.csv`).
- `VERI_FERRAILLAGE` n'est pas essayé (n'accepte pas `TYPE_STRUCTURE='1D'`,
  établi au §3 de l'état des lieux, catalogue).
