# Lot 32 — Débloquer le calcul du quai : conditions aux limites sans redondance

Version Code_Aster : 17.4.0 (image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).
Niveau de validation : **B** pour le `.comm` du quai réduit (étape 1) et pour
celui du quai complet (étape 3) ; **C** pour les deux, le modèle complet
atteignant `FIN` sans erreur pour la première fois depuis le lot 28 ; **D**
pour les contrôles d'équilibre, de symétrie et d'ordre de grandeur de
l'étape 3 (informatifs, sans clôture E : aucune comparaison à une référence
n'a été faite).

## Étape 0 : `mcp-check`

```
Outils déclarés dans le code (7) : analyze_comm, get_command_schema, get_document_section, read_test_case, search_codeaster_docs, search_test_cases, validate_comm
  OK search_codeaster_docs {"query": "STAT_NON_LINE", "k": 1} -> U4.53.01#But
  OK get_document_section {"fragment_id": "U4.53.01#But"} -> level A
  OK get_command_schema {"command": "STAT_NON_LINE"} -> level A
  OK analyze_comm {"comm_path": "..."} -> level A
  OK validate_comm {"comm_path": "..."} -> level B, valid=True
  OK search_test_cases {"command": "AFFE_MODELE", "limit": 1} -> adls102a.comm
  OK read_test_case {"path": "adls102a.comm"} -> level A
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.
```

## Étape 1 : règle de construction des conditions aux limites

### Généralisation de la correction du lot 31

Le lot 31 avait établi la cause du pivot nul (`LIAISON_SOLIDE`, cas 3DA,
dualisant une rotation quasi singulière sous DKT) et corrigé, côté
générateur, la seule redondance des **rotations** DRY/DRZ entre le plan de
symétrie brut (`SYM_G`/`SYM_D`) et l'anneau de tête de tube qui s'y trouve en
partie (`GEN_SYMG_ROT`/`GEN_SYMD_ROT`, `symmetry_and_support_block`) — sans
suffire (lots 29-31 : le pivot nul persistait).

L'énoncé de ce lot pointait une seconde redondance, sur la **translation** :
le nœud de poutre A (référence de `LIAISON_SOLIDE`) et les deux nœuds
d'anneau du plan de coupe B portent tous deux, sur ce plan, `DX = 0`
directement — alors que la relation rigide dérive déjà `DX_B` de `DX_A` (le
bras de levier B−A n'a pas de composante en X, les deux nœuds étant sur le
même plan, et les rotations DRY/DRZ de A qui entrent dans cette dérivation
sont elles-mêmes imposées à zéro) : imposer `DX_B = 0` une seconde fois est
la même équation, d'où le pivot nul, exactement comme pour DRY/DRZ au lot 31,
mais non corrigé alors.

### Implémentation

`aster_expert.generation.comm.symmetry_and_support_block` regroupe désormais
DX, DRY et DRZ dans une seule occurrence de `DDL_IMPO`, portée par
`GEN_SYMG_ROT`/`GEN_SYMD_ROT` (le plan de symétrie **moins** l'anneau de tête
qui s'y trouve) au lieu de `SYM_G`/`SYM_D` bruts — l'anneau ne porte plus
aucun blocage direct sur les trois degrés de liberté que `LIAISON_SOLIDE`
détermine déjà pour lui. Ceci ne s'applique que lorsque la jonction est
`LIAISON_SOLIDE` (`split_ring_rotation=True`, la méthode de production,
décision 4, inchangée) ; les candidats de diagnostic C1/C4 du lot 31, qui ne
dérivent pas le dof de l'anneau de la même façon, gardent le plan entier.

Contrôle du générateur, appelé avant écriture (dans
`symmetry_and_support_block` lui-même, jamais optionnel) :
`check_symmetry_ddl_impo_no_ring_redundancy` refuse la génération si une
ligne `DDL_IMPO` porte à la fois `GROUP_NO=("SYM_G",)` (ou `SYM_D`) et l'un
des degrés DX, DRY, DRZ — seuls les groupes `GEN_SYMG_ROT`/`GEN_SYMD_ROT` en
ont le droit. Testé (`tests/unit/test_generation_comm.py`) : le texte de
production passe le contrôle ; un texte reconstruit avec l'ancien défaut du
lot 31 (DX encore sur `SYM_G` brut) est rejeté ; les candidats non scindés
(`split_ring_rotation=False`) ne sont, à raison, pas concernés.

### Essai sur le quai réduit

`.comm` produit par `scripts/generate_lot32_regle_cl.py`
(`data/examples/lot32_cl/quai_reduit_regle_cl.comm`), validé niveau B
(80/80 commandes). Exécution réelle (`aster-expert run`, 42,1 s) :

```
[...]
 ╔════════════════════════════════════════════════════════════════════════════════════════════════╗
 ║ <F> <MED2_4>                                                                                   ║
 ║                                                                                                ║
 ║ Le champ 'RESU_EAUDEPL' est déjà présent                                                       ║
 ║ dans le fichier MED pour l'instant 0.                                                          ║
 ║   -> Conseil :                                                                                 ║
 ║      Vous pouvez soit imprimer le champ dans un autre fichier, soit                            ║
 ║      nommer le champ différemment.                                                             ║
 ║                                                                                                ║
 ║ Cette erreur est fatale. Le code s'arrête.                                                     ║
 ╚════════════════════════════════════════════════════════════════════════════════════════════════╝
```

**Plus aucun `<F> <FACTOR_11>`** : les six cas de charge (G, EAU_P, EAU_A,
Q1, Q3, A) atteignent tous `MECA_STATIQUE` + `CALC_CHAMP` + `POST_RELEVE_T`
sans erreur. Nouvel arrêt, déjà connu et sans rapport avec ce défaut : la
collision de nom de champ MED signalée au lot 31 (`RESU_EAU_P`/`RESU_EAU_A`
tronqués au même nom Jeveux de 8 caractères), à `IMPR_RESU`. Détail :
`data/examples/lot32_cl/executions.json`,
`data/examples/lot32_cl/rapports/mess_etape1_extrait.txt`.

**L'étape 1 réussit : passage direct à l'étape 3 (étape 2 non nécessaire).**

## Étape 3 : modèle complet

### 1. Correction de la collision de nom de champ MED

U7.05.21 (« Procédure IMPR_RESU au format 'MED' », opérande `RESU`, lu
intégralement via `get_document_section`) : sans indication explicite, « le
nom du champ stocké dans le fichier MED [est la] concaténation » de
`RESULTAT`/`NOM_CHAM`/`NUME_ORDRE` — où `RESULTAT` est le nom Jeveux interne
du concept, tronqué en silence à 8 caractères indépendamment du nom Python
choisi dans le `.comm` (`RESU_EAU_P` et `RESU_EAU_A` tronqués tous deux à
`RESU_EAU`, d'où la collision du lot 31). Le même document documente
l'opérande dédiée à cet usage : `NOM_RESU_MED`, « chaîne d'au plus 8
caractères », qui remplace cette troncature implicite par un nom court
explicite (« `U_HAUT__DEPL` » dans l'exemple du manuel).

`aster_expert.generation.comm.footer` porte désormais
`NOM_RESU_MED="<nom du cas>"` sur chaque occurrence de `RESU`
(`G`, `EAU_P`, `EAU_A`, `Q1`, `Q3`, `A` — tous ≤ 8 caractères, tous
distincts), avec un contrôle de longueur (`_nrm`, `MAX_NOM_RESU_MED_LEN = 8`)
qui refuse à la génération un nom qui dépasserait la limite documentée.
Testé (`tests/unit/test_generation_generate.py`,
`test_impr_resu_nom_resu_med_avoids_the_lot31_field_collision`).

### 2. Clôture de la révision du point 3

La cause établie à l'étape 1 (et déjà au lot 31) touchait la **construction
des conditions aux limites** autour de `LIAISON_SOLIDE`, jamais le choix de
méthode de jonction lui-même (décision 4, maillage coïncident). Celle-ci
**n'a pas changé** : la révision déclarée au lot 31
(`declare_under_revision`, motif = cause établie) est close par
`lift_revision`, motif = correction apportée et prouvée par exécution
(`data/examples/combiwall_inputs/lot32_enregistrement.json`,
`scripts/build_combiwall_reference.py::_lot32`). La fiche de référence
(`data/examples/hypotheses_combiwall_reference_arbitree.json`) n'a plus
aucune entrée en révision ; `is_ready_for_generation` est de nouveau `True`
pour ce point (les 22 valeurs « à fournir » du point 5, elles, restent
un sujet distinct et ouvert, non traité par ce lot).

### 3. Génération, validation B, exécution C

`aster-expert generate` (fiche versionnée, `combiwall_model_data.yaml`,
maillage vérifié du lot 28, 9 tubes, 40 114 nœuds) →
`data/examples/lot28_quai/quai_combiwall.comm`. `validate_comm` : niveau B,
**80/80 commandes valides**, aucune erreur, aucun avertissement.

Exécution réelle (`aster-expert run`, 147,9 s) : **`DIAGNOSTIC JOB : OK`**,
code de retour 0. C'est la première fois que le modèle complet atteint `FIN`
(le lot 28 avait atteint le niveau B seul ; tous les essais réels des lots
28 à 31 avaient échoué sur `<F> <FACTOR_11>`). Aucune ligne `<A>`, `<E>`,
`<F>` ou `<S>` dans tout le `.mess` (`grep` exhaustif, 0 occurrence) : **aucune
alarme**. Journal complet non versionné
(`data/processed/runs/20260924T082421-4ed9a9c6/`, `.gitignore`) ; extrait de
fin dans `data/examples/lot28_quai/rapports/mess_case_complet_extrait.txt`,
rapport dans `data/examples/lot28_quai/rapports/execution_report.json`.

### 4. Contrôles de niveau D

Critères, écrits avant lecture des résultats (données pour MM, jamais un
verdict — CLAUDE.md principe 6, comme au lot 28) : résultante horizontale
(DY) des efforts de ressort (`FORC_NODA`) et des réactions d'appui
(`REAC_NODA`, restreintes à `ANCRAGES`/`PIED_TUBES`/`SYM_G`/`SYM_D`, seuls
nœuds sans élément `ELAS_COQUE` — lot 23), symétrie des déplacements de
part et d'autre de X = 0, ordre de grandeur du déplacement horizontal en
tête d'écran sous G et Q3. Détail complet, tous cas :
`data/examples/lot28_quai/rapports/controles_niveau_d_lot32.json`.

| Cas    | Ressorts DY (N) | Réactions DY (N)\* |
|--------|----------------:|----------------------:|
| G      |      -5 159 880 |               3 099 650 |
| EAU_P  |      -1 317 130 |               1 655 840 |
| EAU_A  |      -3 071 420 |               3 870 350 |
| Q1     |      -1 355 000 |               1 611 190 |
| Q3     | -2 310 (DZ -119 235) | 1 019 700 (DZ -592 910) |
| A      |          20 567 |               -774 152 |

\* Somme ressorts + réactions non nulle par construction : ces deux groupes
ne couvrent pas tous les efforts internes (la charge appliquée elle-même
n'y figure pas, et lire une réaction sous `ELAS_COQUE` serait faux — lot 23).
Suivi comme au lot 28/23, jamais un critère de clôture.

Symétrie : `ANC_01`/`ANC_09` (ancrages, fixes) DX = DY = DZ = 0 exactement
sur les deux, tous cas — attendu par construction. `BOLLARD` (X = 0, sur
l'axe) : DX ≈ 0 à 1e-17 près, tous cas — confirme le maillage bien centré
sur le plan de symétrie. Anneaux de tête des tubes de bord (37 paires de
nœuds appariées entre `TETE_TUBE_02` et `TETE_TUBE_08`, tous cas) : écart
maximal 1,8e-5 sur DY et 3,0e-5 sur DZ (cas EAU_A/Q3, à comparer à des
amplitudes de 3e-3 à 2e-2), somme DX exactement nulle (antisymétrie
parfaite) — bon accord de symétrie sur les six cas.

Ordre de grandeur du déplacement horizontal (DY, m) en tête d'écran :

| Cas | max(DY) | min(DY) |
|-----|--------:|--------:|
| G   | -0,015032 | -0,015125 |
| Q3  | -0,004009 | -0,004301 |

### 5. Dépôt

`quai_combiwall_lot32.comm` et `resultats_quai_lot32.md` déposés dans
`/media/sf_partage/echanges/`.

## Coût

2 exécutions Code_Aster réelles (étape 1 : quai réduit, 42,1 s ; étape 3 :
modèle complet, 147,9 s) — **190,0 s cumulées**. Aucun essai exploratoire de
l'étape 2 (non nécessaire, l'étape 1 a réussi).

## Contrôles

```
$ aster-expert mcp-check
Outils déclarés dans le code (7) : analyze_comm, get_command_schema, get_document_section, read_test_case, search_codeaster_docs, search_test_cases, validate_comm
  OK search_codeaster_docs ... -> level A
  OK get_document_section ... -> level A
  OK get_command_schema ... -> level A
  OK analyze_comm ... -> level A
  OK validate_comm ... -> level B, valid=True
  OK search_test_cases ... -> adls102a.comm
  OK read_test_case ... -> level A
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.

$ ruff format --check
211 files already formatted

$ ruff check
All checks passed!

$ pytest tests/unit
803 passed in 53.04s

$ pytest
830 passed in 55.35s

$ mypy src
Success: no issues found in 77 source files

$ mypy
Success: no issues found in 138 source files
```

## Limites

- Le mécanisme précis de numérotation interne de Code_Aster (pourquoi
  *cette* redondance produit un pivot exactement nul plutôt qu'un
  conditionnement dégradé) reste hors de portée des sept outils MCP, comme
  aux lots 28/30/31 : la correction retenue traite la cause documentaire
  établie au lot 31 (relation dualisée sur un dof déjà dualisé), pas ce
  mécanisme numérique.
- Aucun contrôle de niveau E (comparaison à une référence validée) n'a été
  fait : les contrôles D sont des données pour MM, pas un verdict de
  validité physique.
- Aucune décision pratique n'a été prise ni complétée par ce lot : la
  clôture de la révision du point 3 confirme la décision 4 existante, elle
  ne la remplace pas.
