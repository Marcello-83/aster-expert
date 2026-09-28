# Audit de l'outil AsterExpert — lot 40 (lecture seule)

Date : 2026-09-28. Dépôt audité : `main` au commit `8382425` (lot 39), arbre propre.
Auditeur : session neuve, sans participation au développement. Aucune ligne de code,
de test, de fiche ni de données du dépôt n'a été modifiée ; seuls ce rapport et
`docs/audit/annexes_lot40/` sont écrits.

Chaque affirmation ci-dessous renvoie à un fichier, un journal ou une commande relancée
pendant l'audit. `CLAUDE.md` et les comptes rendus des lots n'ont servi qu'à savoir
**où** chercher, jamais comme preuve. Méthode et commandes : § 8.

---

## 1. Synthèse pour MM (une page)

**Ce que l'outil sait faire aujourd'hui.** Pour **un** ouvrage, le quai combi-wall
QUAI-CW-TEST-01, la chaîne existe de bout en bout jusqu'aux efforts et à un premier
ferraillage de la poutre de couronnement : fiche d'hypothèses arbitrée et historisée,
maillage Salomé contrôlé par un vérificateur indépendant, fichier de commandes généré
automatiquement puis contrôlé contre le catalogue (niveau B), calcul exécuté jusqu'au bout
(niveau C), contrôles d'équilibre et de symétrie (niveau D), synthèse et vues 2D. Les
fondations générales sont solides et réutilisables : recherche documentaire mesurée,
accès au catalogue et aux cas tests, validation de niveau B, exécution encadrée en
conteneur. Les 1 078 tests automatiques passent ; l'analyse statique ne relève rien.

**Ce qu'il ne sait pas faire.** Il ne sait pas traiter un **second ouvrage**. L'essai
réel sur une dalle de 6 × 4 m (§ 5.3) s'arrête **à la première étape**, la recherche
documentaire. Il n'existe aucune commande qui passe d'une description à une fiche.
Il n'existe aucun script de maillage de dalle. Le générateur, la synthèse, les
combinaisons et les contrôles sont écrits pour le quai : noms de groupes, nombre de
tubes, couches de sol, coefficients de combinaison. Fournir des données de dalle au
générateur ne produit pas un refus lisible : le programme s'arrête sur une erreur
interne qui réclame le « rayon du tube ».

**Niveau réellement atteint.** Sur le quai : niveau **C avec contrôles D**, jamais E.
Aucune comparaison à une référence extérieure n'a été faite ; la ligne de comparaison
prévue pour votre logiciel de flexion composée est vide. Le modèle de ressorts
linéaires sort nettement de son domaine sous G : 2 413 nœuds dépassent la butée, avec un
taux maximal de 951 % (lot 36). Ce constat est rapporté sans être résolu.

**Étapes encore manuelles.** Sur 13 étapes entre une description et une note, 6 sont
des commandes de l'outil. 6 passent par du code Python écrit par une session pour le
lot : fiche, enregistrement des arbitrages, script Salomé, contrôles D, combinaisons,
ferraillage. La note de calcul **n'existe pas**. 53 des 64 scripts du dépôt portent un
numéro de lot.

**Fiabilité de l'exécution.** Sur les 190 calculs archivés, 38 % ont échoué. C'est
normal en phase de mise au point (diagnostic du pivot nul, essais de limites), mais cela
signifie qu'un calcul d'ouvrage demande encore une supervision d'expert.

**Recommandation principale.** Avant un second ouvrage, il faut séparer ce qui relève
du quai de ce qui relève du « moteur ». La structure fiche → données → maillage →
générateur est la bonne. En revanche, les maillons maillage, générateur et synthèse
doivent devenir des **familles d'ouvrages** interchangeables derrière une interface
commune, au lieu d'un code unique écrit pour le quai. Le radier est un bon deuxième cas
parce qu'il est simple. Il faut aussi que ses références soient indépendantes :
solution analytique de plaque et cas tests officiels. § 7 détaille dix recommandations.

---

## 2. Étape 0 — contrôle MCP

| Contrôle | Résultat |
|---|---|
| `aster-expert mcp-check` (serveur neuf, lancé comme `.mcp.json`) | **OK** : 7 outils déclarés = 7 outils du code, chacun appelé sur une requête minimale ; `validate_comm` → niveau B, `valid=True`. Dernière ligne de la sortie : « mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code. » |
| Outils visibles dans la session | les 7 (`analyze_comm`, `get_command_schema`, `get_document_section`, `read_test_case`, `search_codeaster_docs`, `search_test_cases`, `validate_comm`) |
| Appels directs depuis la session | les premiers appels ont été bloqués par une panne du contrôle d'autorisation de l'environnement (sans verdict, puis sortie du mode automatique), sans rapport avec l'outil. Après rétablissement : `search_test_cases(CALC_FERRAILLAGE)` → 13 cas sur 4 480 fichiers, 0 illisible ; `get_command_schema(AFFE_CARA_ELEM, keyword="COQUE.EPAIS")` → **64 597 caractères**, au-delà de la limite du client (voir écart E16) |

---

## 3. Étape 1 — inventaire factuel

### 3.1 Commandes CLI (25) et outils MCP (7)

Dernière utilisation réelle, d'après les archives. `aster-expert run` ne conserve **aucun
compte rendu JSON** de ses exécutions : seul reste le fichier `__status__` (objet
`run_aster.status` sérialisé), décodé pour cet audit (annexe `executions_archivees.json`,
méthode § 8). Pour les autres commandes, aucune ne journalise son usage : la « dernière
utilisation » est déduite des sorties datées quand il y en a.

| Commande | Rôle | Tests | Dernière utilisation attestée |
|---|---|---|---|
| `env detect` | détecte l'image et la version, écrit `config/versions.yaml` | `test_detect*.py` | non journalisée |
| `sources sync / inventory / probe / xref / command-map` | clonage versionné et inventaire du corpus | `test_sources_sync`, `test_inventory`, `test_rst_probe`, `test_xref`, `test_command_map` | non journalisée (manifeste) |
| `catalogue extract / show` | introspection du catalogue dans le conteneur | `test_catalogue_*` | non journalisée |
| `comm parse` | analyse structurelle d'un `.comm` | `test_comm_parser` | non journalisée |
| `eval summary / score / bench / decompose / profile-bench` | banc de la recherche | `test_bench`, `test_evaluation` | **relancée par cet audit** (§ 5) |
| `fragments build`, `index build` | découpage et index BM25 | `test_doc_fragments`, `test_bm25_index` | non journalisée |
| `search`, `section` | recherche et lecture intégrale | `test_cli`, `test_bm25_index` | relancée par cet audit (essai dalle) |
| `validate` | niveau B par `checkCommandSyntax` | `test_validate` (conteneur **simulé**) | via MCP : 2026-09-28T10:09Z |
| `mcp-check` | contrôle du serveur | `test_mcp_check` | cet audit |
| `run` | exécution encadrée (niveau C) | `test_execution_run` (conteneur **simulé**) | 190 exécutions, 2026-09-21 → 2026-09-28 |
| `mesh run` | script Salomé sans interface | `test_meshing_run` (simulé) | 13 comptes rendus, dernier au lot 37 |
| `mesh check` | vérificateur MED indépendant | `test_meshing_invariants` | 79 relevés dans `data/processed/mesh_checks/` |
| `generate` | `.comm` **du quai** | `test_generation_*` | lot 37-39 (sorties versionnées) |
| `report` | synthèse **d'un calcul du quai** | `test_report_*` | lot 37 (`data/processed/lot37_rapports`) |

README : la commande `aster-expert mess analyze` qu'il annonce **n'existe pas** (écart E17).

Outils MCP (`data/processed/query_log.jsonl`, 896 lignes lisibles, 1 illisible). Appels hors
`mcp-check`, c'est-à-dire l'usage réel :

| Outil | Appels réels | Appels `mcp-check` | Premier → dernier usage réel |
|---|---|---|---|
| `search_codeaster_docs` | 154 | 36 | 2026-09-18 → 2026-09-28 |
| `get_document_section` | 169 | 37 | 2026-09-18 → 2026-09-28 |
| `get_command_schema` | 90 | 37 | 2026-09-18 → 2026-09-28 |
| `validate_comm` | 100 | 36 | 2026-09-18 → 2026-09-28 |
| `read_test_case` | 73 | 32 | 2026-09-21 → 2026-09-28 |
| `search_test_cases` | 52 | 35 | 2026-09-21 → 2026-09-28 |
| `analyze_comm` | **8** | 37 | 2026-09-18 → **2026-09-22** |

`analyze_comm` n'est pratiquement plus utilisé depuis le lot 28 : la connexion avait été
perdue sur un `.comm` de ~10 600 occurrences (compte rendu du lot 28, non vérifié par
exécution ici).

### 3.2 Modules `src/aster_expert/`

Tests : **1 078 réussis, 0 échec, 0 ignoré, 4 min 17 s** (`pytest --cov`, annexe
`tests_lot40.txt`). `ruff check` : aucune erreur ; `ruff format --check` : 323 fichiers
conformes ; `mypy --strict` : aucune erreur sur 184 fichiers (**`src` et `tests` seulement,
les scripts ne sont pas typés**).

| Module | Fichiers | Lignes | Couverture | Dépendances notables | Propre au quai ? |
|---|---|---|---|---|---|
| `agent` (fiche, arbitrage, données, rédaction) | 5 | 1 995 | 97,7 % | pydantic | générique |
| `catalogue` | 5 | 428 | 95,9 % | conteneur | générique |
| `execution` | 8 | 1 114 | 95,1 % | Docker (simulé en test) | générique |
| `generation` | 8 | 3 756 | 93,0 % | `meshing.combiwall` | **oui, entièrement** |
| `indexing` | 5 | 763 | 97,8 % | bm25s | générique |
| `ingestion` | 9 | 2 347 | 94,8 % | git, docutils | générique |
| `mcp` | 9 | 1 870 | 86,1 % | mcp 2.x | générique |
| `meshing` | 9 | 2 835 | 91,9 % | conteneur medcoupling | `combiwall.py` (1 135 l.), `normals.py`, `equilibrium.py` : quai ; `run`, `check`, `invariants` : génériques |
| `parsing` | 6 | 1 461 | 93,3 % | ast | générique |
| `rebar` | 7 | 1 527 | 96,0 % | — | générique (section rectangulaire 1D) |
| `report` | 12 | 3 836 | **72,5 %** | medcoupling, matplotlib | **oui**, sauf `tables.py` et `med_read.py` |
| `retrieval` | 7 | 1 336 | 98,5 % | — | générique |
| `validation` | 7 | 1 395 | 83,8 % | conteneur | générique |
| `cli.py` | 1 | 1 939 | **32,0 %** | typer | mixte |
| **Total** | | **26 612** | **84 %** | | |

Fichiers les moins couverts : `validation/checker_client.py` 31,8 % ; `cli.py` 32,0 % ;
`report/med_read.py` 42,4 % ; `report/figures.py` 44,3 % ; `report/section_statics.py` 62,7 % ;
`report/loads.py` 63,0 % ; `mcp/check.py` 64,6 % ; `generation/values.py` 66,1 %.

Hors `src/` : **64 scripts, 15 426 lignes**, dont **53 portent un numéro de lot** ; tests :
85 fichiers, 21 113 lignes.

### 3.3 Constats `code_aster` de la fiche

Source : `data/examples/hypotheses_combiwall_reference_arbitree.json`, 63 entrées,
toutes tranchées : **45 constats `code_aster`** et **18 entrées de pratique** (décisions MM).

| Nature de la meilleure source d'un constat | Constats | Commentaire |
|---|---|---|
| au moins une source d'exécution | **18** | 84 sources d'exécution au total : **62 de niveau D, 22 de niveau C**, aucune E (le schéma l'interdit) |
| catalogue introspecté, sans exécution | 20 | fait de syntaxe, pas de comportement |
| documentaire seul (manuels) | 7 | niveau A |

Sources au total : 117 documentaires, 72 catalogue, 84 d'exécution. Les constats sont
rangés par point : 1 (tube, 10 constats), 3, 4, 5, 7, 8, 12 et 14. Le point 14, sur le
ferraillage, en compte 7, dont l'état des lieux de 36 sources.

### 3.4 Exécutions archivées

`data/processed/runs/` : **190 exécutions** (du 2026-09-21 au 2026-09-28 ; les exécutions
antérieures au lot 22 ne sont pas archivées ici). États décodés de `run_aster.status` :

| État | Nombre |
|---|---|
| `Ok` | 117 |
| `Fatal` | 52 |
| `Except` | 16 |
| `Abort` | 5 |
| **Taux d'échec** | **73 / 190 = 38,4 %** |

| Jour | Exécutions | Échecs | Temps écoulé Aster (s) |
|---|---|---|---|
| 2026-09-21 | 75 | 17 | 140 |
| 2026-09-23 | 47 | 31 | 123 |
| 2026-09-24 | 41 | 19 | 1 924 |
| 2026-09-25 | 17 | 3 | 3 343 |
| 2026-09-28 | 10 | 3 | 16 |
| **Total** | **190** | **73** | **5 545 s (1,54 h)** |

Temps mesuré par `run_aster` : le 4ᵉ temps de `Status._times`, sans le démarrage du
conteneur. Plus longues exécutions : `complet_v1.comm`, 779 s, et `complet_base.comm`,
581 s (lot 36) ; `quai_combiwall.comm`, 410 s. Salomé : 13 maillages pour 3 070 s cumulées,
dont deux maillages complets du quai de 1 072 s et 1 229 s. Seuls 9 lots ont consigné leurs
exécutions dans un `executions.json` rédigé à la main.

---

## 4. Étape 2 — évaluation par capacité

| Capacité | État | Niveau démontré | Preuve | Limites |
|---|---|---|---|---|
| Validation statique B | **opérationnelle** | B | `mcp-check` (valid=True) ; 100 appels réels ; `.comm` du quai 80/80 (lots 28-37) | tests unitaires sur conteneur simulé ; seule la syntaxe est vue, pas la cohérence des groupes avec le maillage |
| Recherche documentaire | **opérationnelle, moyenne hors syntaxe** | A | banc relancé : **hit@10 réaliste 82,5 %** (52/63), **explicite 86,4 %** (51/59), identique au lot 7c ; `syntaxe` 91,1 %, **`theorie` 66,7 %, `methode` 55,6 %** ; sans profil : 61,9 % (`by_file`), 60,3 % (`by_subsection`) | banc de 65 questions écrit par le développement (2026-09-17), jamais enrichi depuis ; profil à choisir par l'appelant ; l'essai dalle en description brute ramène en tête U3.12.01 et U2.06.10 (dynamique) |
| Accès aux cas tests | **opérationnelle** | A | 4 480 fichiers analysés, 0 illisible ; 125 appels réels | lecture seule, sans lien vers les résultats de référence des documents V |
| Exécution | **opérationnelle** | C | 117 exécutions `Ok` ; modèle complet en 410 à 779 s | aucun compte rendu JSON persistant ; aucun test automatique n'exécute réellement Code_Aster |
| Analyse du `.mess` | **partielle** | — | `ExecutionReport` ne rend que `status`/`diag` ; `run_aster.error_messages` n'est **pas encapsulé** (`execution/models.py:146-156` renvoie à un « lot de dépouillement fin » jamais fait) ; `report/tables.py` lit les tables du quai | pas d'extraction des alarmes ni des erreurs `<F>` par l'outil : leur lecture dans les lots 28-37 a été faite à la main par les sessions |
| Fiche : schéma, arbitrage, historique, blocages | **opérationnelle** | — (structure) | `agent/hypotheses.py`, `arbitration.py` ; `decision_history`, `revision_history`, `generation_blockers` ; couverture 97,7 % | la fiche arbitrée est produite par `scripts/build_combiwall_reference.py` (1 364 lignes, propre au quai) ; `generation_blockers` ne vérifie pas que les données conviennent au générateur (essai dalle) |
| **Rédaction assistée de la fiche depuis une description** | **partielle, non outillée** | A | procédure écrite (skill `hypotheses-drafting`, 100 lignes) + barrière d'écriture `agent/drafting.py` ; trame `data/config/hypotheses_trame_defaut.json` | **aucune commande** : il faut qu'une session écrive des appels Python ; appliquée une seule fois, sur le quai (lot 14b, 2026-09-18) ; jamais réessayée sur un autre ouvrage |
| Maillage Salomé et vérificateur | **opérationnel pour le quai ; moteur générique** | vérificateur : 588/588 puis 599/599 invariants | `meshing/run.py`, `check.py`, `invariants.py` génériques ; `scripts/salome/combiwall_mesh.py` + `meshing/combiwall.py` propres au quai | un nouvel ouvrage = nouveau script Salomé + nouveau calcul analytique des comptages ; aucun gabarit |
| Générateur de `.comm` | **opérationnel pour le quai seulement** | B (80/80), C sur le modèle complet | `generation/` 3 756 lignes | **entièrement propre au quai** (§ 6.1) ; données étrangères → erreur interne non interceptée (§ 6.3) |
| Contrôles D | **partielle** | D (équilibre ≤ 2,8e-12, symétrie ≤ 5,2e-11, lot 37) | tables de contrôle écrites par `comm.controls_block` ; lectures par `scripts/analyze_lot34_equilibre.py`, `analyze_lot3x_*` | contrôles portés par des **scripts de lot**, non par l'outil ; propres au quai ; D sur un modèle de ressorts linéaires hors domaine sous G (lot 36) |
| Post-traitement et figures | **partielle** | lecture MED contre-vérifiée au `.mess` (4,9e-13, lot 36) | `report/` ; 48 PNG (lot 36) | propre au quai ; vues 2D `matplotlib` seulement ; ParaVis hors interface impossible (écart E3) |
| Combinaisons | **partielle** | — (arithmétique) | `report/combinations.py` : 18 combinaisons de D17 | cas `G, EAU_P, EAU_A, Q1, Q3, A` et coefficients γ/ψ **codés en dur** (l. 23-28), en double avec `combiwall_model_data.yaml` l. 328-332 ; aucune commande CLI |
| Ferraillage 1D | **partielle** | ELU : accord module/Code_Aster ≤ 6,5e-13 sur 61/63 sections ; référence `ssll13d` | `rebar/` ; `tests/unit/test_rebar_ultimate.py`, `test_rebar_serviceability.py` | ELS : écarts non expliqués (E1, E2) ; tableau 7.2N transcrit par la session, à vérifier ; appelé seulement par des scripts de lot |
| Ferraillage 2D | **absente en pratique** | essai sur **un élément** (lot 39, étape 6) | `docs/essais_lot39.md` § étape 6 | un échec sur un cas dégénéré (`nxx_t_mxx`) ; Capra-Maury non recalculé ; comparaison Wood-Armer sans seuil (−3,3 %, ±8,8 %) ; aucun module 2D |
| Notes de calcul | **absente** | — | aucune occurrence de « note de calcul » dans `src/` ni dans `scripts/`, hors une mention de schéma | — |
| Non-linéaire | **absente** | — | aucun `STAT_NON_LINE` dans `generation/` ; décision 5 (ressorts linéaires) hors domaine (lot 36) | — |
| Thermique | **absente** | — | aucune trace dans `generation/` | — |
| Dynamique | **absente** | — | idem | — |
| Phasage | **absente** | — | point 6 de la fiche (phasage) tranché par MM comme non modélisé ; aucun code | — |

---

## 5. Étape 3 — généricité (question centrale)

### 5.1 Éléments propres au combi-wall dans `src/`

Recherche des noms de groupes, cotes, nombres et formules du quai. Fichier et ligne, au
commit `8382425` :

| Fichier : lignes | Élément codé en dur |
|---|---|
| `generation/__init__.py:1` | « Deterministic `.comm` generator for the combi-wall quay model » : le module entier |
| `generation/generate.py:49-58` | `_REQUIRED_FACT_TOPICS` : intitulés exacts de constats du quai (LIAISON_SOLIDE anneau/poutre, pression côté terre, POU_D_E…) exigés par la génération |
| `generation/generate.py:94-160, 470, 523, 713, 731` | points de poutre par tube, `ECRAN_POUSSEE`, `TUBE_05`/`TUBE_01`, cas `G…A`, dispense `POUTRE_COUR` |
| `generation/comm.py:53-56` | groupes `GEN_SYMG_ROT`, `GEN_SYMG_RING`, `GEN_SYMD_ROT`, `GEN_SYMD_RING` |
| `generation/comm.py:259, 317, 324, 429, 454` | `ENV_CYLINDRE`, `SYM_G`, `SYM_D`, `POUTRE_COUR`, `ECRAN_POUSSEE` |
| `generation/comm.py:710, 769, 880, 2006, 2037` | `POUTRE_COUR` (modèle, matériau, synthèse) |
| `generation/comm.py:1099-1121` | `DDL_IMPO` sur `SYM_G`, `SYM_D`, `PIED_TUBES` |
| `generation/comm.py:1183, 1305-1306` | `PALPS`, `RESS_AV_ARGI`, `RESS_AV_MARNE` |
| `generation/comm.py:1424, 1429` | charges de bollard et de défense |
| `generation/comm.py:1579, 1602-1604` | `_SUPPORT_GROUPS = ("ANCRAGES", "PIED_TUBES", "SYM_G", "SYM_D")` |
| `generation/terre.py:38-42` | **couches de sol (γ, γ', φ, c) en dur**, absentes du fichier de données |
| `generation/terre.py:46-52` | cotes du terre-plein (4,0), de la nappe (2,0), du pied (−26,0), du dragage (−12,0) |
| `generation/terre.py:141-144` | tableau K0·σ'v de la variante V1 (données fictives) |
| `meshing/combiwall.py` (1 135 lignes) | comptages analytiques du quai ; l. 86-106 : tubes, entraxes, palplanches ; l. 103 : message « pas à huit entraxes » |
| `report/build.py:41, 49-51, 182, 197-215` | cas, groupes d'appui, cas uniformes, demi-tubes de bord |
| `report/combinations.py:23-28` | cas et coefficients de D17 (en double avec les données) |
| `report/med_source.py:36-38, 185, 218` | `PIED_TUBES`, `SYM_*`, `TETE_TUBE_`, `POUTRE_COUR` |
| `report/figures.py:251, 538, 658, 738, 759` | plan « Z = −12,00 m CM », `POUTRE_COUR`, `TUBE_05` |
| `report/section_statics.py:185, 217` | `ECRAN_POUSSEE`, `PIED_TUBES` |
| `report/quantities.py:38` | `TUBE_05`, `PALP_01_02`, `TIRANT_03` |
| `cli.py` (`generate`, `report`) | aide : « le .comm du quai », « calcul du quai » ; `--donnees` par défaut `combiwall_model_data.yaml` |

Dans `scripts/`, sont propres au quai `salome/combiwall_mesh.py` (518 l.),
`build_combiwall_reference.py` (1 364 l.) et les 53 scripts numérotés par lot. Seuls 8 scripts
sont génériques : environnement, catalogue, syntaxe, exécution, lecture MED, essai
`FORCE_COQUE`.

**Bilan chiffré.** Sur 26 612 lignes de `src/`, environ **8 700** sont propres au quai :
`generation` 3 756, `meshing/combiwall|normals|equilibrium` ~1 600, `report` hors `tables`
et `med_read` ~3 300. Cela fait environ **un tiers** du code, et surtout **tout l'aval de
la chaîne**.

Côté générique, les éléments suivants sont réutilisables : les schémas de fiche et de
données, les barrières d'écriture, le moteur de maillage et de vérification, la validation,
l'exécution, la recherche et le module de ferraillage 1D. Aucun mécanisme ne permet de
réutiliser un **constat `code_aster`** d'une fiche dans une autre : `PriorDecision` ne
couvre que les décisions de pratique. Les 45 constats, dont 18 éprouvés par exécution,
sont donc enfermés dans la fiche du quai.

### 5.2 Essai de pensée — radier DKT sur appuis élastiques, ferraillage 2D

Estimations grossières en lots de la taille des lots 26 à 39, soit une session chacun.

| Étape | Sort | Ce qu'il faut écrire | Estimation |
|---|---|---|---|
| Description → fiche projet | se paramètre | appliquer la procédure `hypotheses-drafting` à un radier ; écrire l'équivalent de `build_combiwall_reference.py` pour le radier, ou mieux un constructeur générique | 1 lot |
| Arbitrage MM, historique, blocages | tel quel | — | 0 |
| Données chiffrées | tel quel (schéma) | un YAML du radier | < 0,5 lot |
| Maillage | moteur tel quel ; contenu réécrit | script Salomé du radier ; module de comptages analytiques ; invariants | 1 lot |
| Générateur `.comm` | **réécrit** | modèle DKT, `ELAS`/`ELAS_COQUE`, ressorts (`CREA_POI1`/`DISCRET`, faits réutilisables par recopie), charges, conditions d'appui, impressions ; seuls les utilitaires (`_fmt`, `_gn`, `formule_block`, `footer`) se reprennent | 1,5 à 2 lots |
| Validation B, exécution C | tel quel | — | 0 |
| Contrôles D | **réécrits** | équilibre et symétrie du radier dans l'outil (et non dans des scripts de lot) ; comparaison à une solution de plaque (Navier) = premier niveau **E** possible | 1 lot |
| Post-traitement, vues | **réécrits à ~70 %** | `tables.py`, `med_read.py` réutilisables ; synthèse, vues et grandeurs propres au radier | 1 lot |
| Combinaisons | se paramètre | sortir cas et coefficients du code | 0,3 lot |
| Ferraillage 2D | **à construire** | module 2D (Capra-Maury ou Wood-Armer) calibré sur cas tests officiels ; essais de `CALC_FERRAILLAGE` 2D au-delà d'un élément ; lever l'échec du cas dégénéré | 1,5 à 2 lots |
| Note | **à construire** | — | 1 lot |
| **Total** | | | **~9 à 11 lots**, dont l'essentiel est de la réécriture |

Si la refactorisation de la recommandation R1 est faite d'abord, le travail ne sera pas
perdu pour le troisième ouvrage. Sinon, chaque ouvrage coûtera à nouveau ~10 lots.

### 5.3 Essai réel minimal — dalle 6 × 4 m, 0,30 m, appuyée sur quatre côtés, 10 kPa

Description utilisée : « Dalle rectangulaire en béton armé de 6 m par 4 m et 0,30 m
d'épaisseur. Elle est simplement appuyée sur ses quatre côtés. Elle porte une charge
uniforme de 10 kPa. » Sorties réelles : `annexes_lot40/essai_dalle/`.

| # | Étape | Commande | Résultat | Où et pourquoi elle s'arrête |
|---|---|---|---|---|
| 1 | Recherche documentaire | `aster-expert search "<description>" --profile methode --k 5` | code 0 ; en tête : U3.12.01 (liste des cas tests), R3.07.09 (Q4GG), R7.01.31 (GLRC), U2.06.10 (**dynamique**) | fonctionne (niveau A) ; pertinence médiocre sur la description brute. Reformulée (« modélisation d'une dalle en coque DKT… »), U2.02.01 arrive en tête |
| 2 | Fiche d'hypothèses | aucune | — | **arrêt** : aucune commande ne produit une fiche. La procédure exige qu'une session écrive des appels Python à `agent.drafting` (code). La trame par défaut n'est pas une fiche : passée à `generate`, elle est refusée par le schéma (`structure_description`, `created_at` manquants) |
| 3 | Données | YAML de 4 valeurs (`dalle_donnees.yaml`, données seulement) | accepté par le schéma | le schéma est générique |
| 4 | Maillage | `aster-expert mesh run <script>` | — | **arrêt** : il n'existe que les scripts du quai et du lot 26 ; il faut écrire un script Salomé (code) |
| 5 | Génération | `aster-expert generate <fiche quai> dalle_donnees.yaml <med>` | **code 1, trace Python non interceptée** : `CombiwallMeshError: valeur absente ou à fournir : tube.rayon` (`meshing/combiwall.py:67`) | la fiche d'un projet QUAI est acceptée avec les données d'un projet DALLE sans contrôle ; `generation_blockers` ne signale rien ; l'échec survient dans le calcul des paramètres du quai |
| 6 | Validation, exécution | `validate`, `run` | — | génériques, mais rien à leur donner sans écrire un `.comm` |
| 7 | Synthèse | `aster-expert report <exécution ssls502a> --donnees dalle_donnees.yaml` | code 1 : « report ÉCHEC : valeur absente ou à fournir : tube.rayon » | la synthèse ne sait lire qu'un calcul du quai |

**Conclusion de l'essai.** Sans écrire de code, la chaîne s'arrête **après l'étape 1**.
Aucune étape en aval de la recherche n'accepte un autre ouvrage que le quai.

---

## 6. Étape 4 — qualité et risques

### 6.1 Références indépendantes ou autocohérence

| Domaine | Référence indépendante | Autocohérence seulement |
|---|---|---|
| Ferraillage ELU 1D | **cas test officiel `ssll13d`** (`test_rebar_ultimate.py`) ; accord Code_Aster/module ≤ 6,5e-13 (lot 39) | — |
| Ferraillage ELS 1D | `ssll13b` (accord sur le cas fortement tendu) | le cas partiellement comprimé n'est testé qu'en « ordre de grandeur » (`test_design_els_pure_moment_is_of_the_right_order_but_not_exact`) |
| Minima et effort tranchant EC2 | formules refaites « à la main » **dans le test** (`test_rebar_minimum_shear.py`), par la même session | tableau 7.2N transcrit par la session, jamais confronté à la norme |
| Validation B | `checkCommandSyntax` de Code_Aster (autorité externe) | tests unitaires sur conteneur **simulé** |
| Maillage | vérificateur MED indépendant de Salomé | valeurs attendues calculées par `meshing/combiwall.py`, écrit par les mêmes sessions que le script Salomé (même lecture des données) |
| Génération | exécution réelle + équilibre global (loi physique) | tests `test_generation_*` = comparaison au `.comm` déjà produit (non-régression) |
| Fiche arbitrée | textes d'arbitrage de MM recopiés à l'identique | test de rejeu octet pour octet du script (non-régression) |
| Recherche | — | banc de 65 questions annoté par le développement lui-même |
| Quai complet | **aucune** (pas de niveau E) ; `ligne_comparaison_mm.csv` : colonnes MM vides | équilibre, symétrie, statique d'une coupe (0,9 à 1,6 %) |

**Aucun test automatique n'exécute réellement Code_Aster ni Salomé.** Docker est simulé
dans `test_validate`, `test_execution_run` et `test_meshing_run`. Les preuves d'exécution
existent, mais dans les archives et les rapports, pas dans la suite de tests. Une
régression de l'image `simvia/code_aster` ne serait vue que par `mcp-check`, qui ne
couvre que `validate_comm`.

### 6.2 Écarts ouverts et impact

| # | Écart | Source | Impact |
|---|---|---|---|
| E1 | ELS caractéristique de `CALC_FERRAILLAGE` 1D : −16 % à +0,25 % par rapport au pivot acier refait à la main, cause non établie | `essais_lot39.md` l. 330-333 | aucune aire ELS 1D ne peut être prise sans contre-calcul ; bloque une note ELS |
| E2 | `ssll13b` : le module s'écarte de 2,7 % (CHEFF4) et d'~10 % sur le cas partiellement comprimé ; ELS QP non calibré | `test_rebar_serviceability.py` l. 49-63 ; `essais_lot38.md` Limites | ni Code_Aster ni le module ne sont une référence ELS ; le test tolère l'écart |
| E3 | ParaVis : pas de rendu hors interface (ni Xvfb ni EGL) ; *Extract Group* non essayé | `essais_lot36.md` Limites ; `pyproject.toml` l. 50-53 | vues 2D seulement ; toute vue 3D reste manuelle pour MM |
| E4 | Ressorts linéaires hors domaine sous G : 2 413 nœuds au-delà de la butée, jusqu'à 951 % ; 27 % des ressorts comprimés au-delà de la butée (lot 35) | `essais_lot36.md` ; `essais_lot35.md` l. 246 (2 413 / 8 828 = 27 %) | **la validité physique des résultats sous G n'est pas acquise** ; pas de non-linéaire |
| E5 | Ferraillage 2D : un élément, échec sur un cas dégénéré, Capra-Maury non recalculé | `essais_lot39.md` étape 6 | pas de ferraillage de plaque utilisable |
| E6 | Tableau 7.2N transcrit par la session ; γc = 1,2 et γs = 1,0 accidentels non décidés par MM | `essais_lot39.md` Limites | minimum de fissuration (gouvernant sur toute la poutre) non assuré |
| E7 | `POST_RELEVE_T/RESULTANTE` multi-groupes ≠ somme des groupes, cause non établie | `essais_lot34.md` l. 160, 255 | contourné (table retirée) ; piège pour tout autre modèle |
| E8 | `FERR_MIN='EC2'` juste en MPa seulement ; `FERR_MIN_FISS` refusé en 1D | `essais_lot39.md` | contourné ; à rappeler dans tout futur générateur |
| E9 | Pas de niveau E sur le quai ; ligne de comparaison MM vide | `data/examples/lot38_essais/ligne_comparaison_mm.csv` | aucune validation externe du modèle complet |
| E10 | Raffinement vertical seul ; statique de coupe à −11,75 et non à −12,00 | `essais_lot37.md` l. 141-159 | convergence en maille non démontrée en plan |
| E11 | Sonde de charge assemblée non relancée sur le modèle complet au lot 37 | idem | contrôle de charge fondé sur une intégrale indépendante seulement |
| E12 | Symétrie sourcée pour `POU_D_E`, appliquée à `POU_D_T` sans constat | idem | lacune documentaire, pas numérique (l'exécution passe) |
| E13 | Moments de poutre lus pour `x_l = +X` « déduit de l'ordre des lignes » | `essais_lot35.md` l. 193, 270 | signe des moments de poutre à confirmer |
| E14 | Aucun compte rendu JSON d'exécution persistant ; traçabilité par `executions.json` manuels (9 lots) | § 3.4 | audit des exécutions possible seulement par décodage du pickle |
| E15 | `run_aster.error_messages` non encapsulé ; pas d'extraction des alarmes | `execution/models.py:146-156` | lecture des `<A>`/`<F>` à la main à chaque lot |
| E16 | `get_command_schema` avec `keyword` renvoie aussi la commande entière (64 597 caractères) | appel de cet audit | dépasse la limite du client ; oblige à relire un fichier intermédiaire |
| E17 | README : `aster-expert mess analyze` n'existe pas ; exemple `--version 18` alors que l'installation est 17.4.0 | `README.md` l. 62, 75 | documentation trompeuse pour un nouvel utilisateur |
| E18 | `CLAUDE.md` ne résume pas les lots 33 et 38 dans sa liste de lots | `CLAUDE.md` | reprise de contexte incomplète |
| E19 | `generate` : données d'un autre projet acceptées, échec par trace Python non interceptée | § 5.3, étape 5 | un utilisateur non développeur ne comprend pas le refus |
| E20 | Journal MCP : 1 ligne illisible sur 897 | `query_log.jsonl` | mineur |

### 6.3 Dette technique

- **Dérogations** : 117 `noqa`, dont 23 dans `src/` (11 `E402`, 5 `PLC0415`, 7 `S603`/`BLE001`
  motivées) et 94 dans 28 scripts (42 `E402`, 32 `PLC0415`, 7 `BLE001`…). 22 `type: ignore`
  dans `src/`, dont 10 dans `cli.py` et 9 dans `rebar/model.py`. 18 exceptions de fichiers
  dans `pyproject.toml` (`E501`/`UP` pour les gabarits des scripts de lot).
- **Scripts hors `src/`** : 64 fichiers et 15 426 lignes, **non vérifiés par `mypy`**
  (`files = ["src", "tests"]`). 53 sont des scripts de lot, et plusieurs portent des
  fonctions de l'outil : contrôles D (`analyze_lot34_equilibre.py`), export et ferraillage
  de la poutre (`build_lot38_export.py`, `build_lot39_poutre.py`).
- **Doublons** :
  - cas élémentaires dans `report/build.py:41`, `report/combinations.py:23` et `generation/generate.py:713` ;
  - correspondance des groupes d'appui dans `generation/comm.py:1602`, `report/build.py:49` et `report/med_source.py:36` ;
  - coefficients γ/ψ dans `report/combinations.py:25-28` et dans `combiwall_model_data.yaml` l. 328-332 ;
  - sérialisation des paramètres « octet pour octet identique » à `scripts/build_lot27_maillage.py` (`generate.py:66-69`) ;
  - données de sol : dans `terre.py` seulement, hors du fichier de données sourcé.
- **Couverture faible là où l'utilisateur agit** : `cli.py` 32 %, `report/figures.py` 44 %,
  `report/med_read.py` 42 %.

### 6.4 Ergonomie pour MM : de la description à la note

| # | Étape | Outil | Supervision |
|---|---|---|---|
| 1 | Rédiger la description / le cas de test | MM | — |
| 2 | Projet de fiche | session + skill + appels Python | **forte** (expert Code_Aster) |
| 3 | Arbitrer | MM (texte d'arbitrage) | MM |
| 4 | Enregistrer l'arbitrage | script propre au projet (`build_combiwall_reference.py`) | session |
| 5 | Données chiffrées | YAML + `check_consistency` | MM complète les « à fournir » |
| 6 | Script Salomé + comptages attendus | code écrit par une session | **forte** |
| 7 | `mesh run` puis `mesh check` | **CLI** | faible |
| 8 | `generate` | **CLI** | faible (quai seulement) |
| 9 | `validate` | **CLI** | faible |
| 10 | `run` | **CLI** | moyenne (38 % d'échecs archivés) |
| 11 | Contrôles D | scripts de lot | **forte** |
| 12 | `report` | **CLI** | faible (quai seulement) |
| 13 | Combinaisons, ferraillage | scripts de lot | **forte** |
| 14 | Note de calcul | **absente** | — |

Sur les 13 étapes outillables, 6 sont des commandes et 6 demandent du code écrit par une
session. La note n'existe pas. MM ne peut pas conduire seul la chaîne, même sur le quai.

### 6.5 Coût du développement

| Mesure | Valeur | Source |
|---|---|---|
| Durée | 2026-09-15 → 2026-09-28 (14 jours calendaires, 10 jours avec commit) | `git log` |
| Lots | 47 étiquettes (lots 1 à 39 sans 12 ni 13, plus 10 sous-lots) ; 60 commits | `git log` |
| Volume | +641 776 / −3 072 lignes, en majorité des données (`data/examples` : 116 Mo) | `git log --shortstat` |
| Exécutions Code_Aster archivées | 190, 5 545 s (1,54 h) de calcul, 38 % d'échecs | § 3.4 |
| Maillages Salomé | 13, 3 070 s | `data/processed/mesh_runs/*/mesh_run_report.json` |
| Stockage des exécutions | 17 Go (`data/processed/runs`) | `du` |
| Code | 26 612 lignes `src/`, 15 426 `scripts/`, 21 113 tests | `wc` |

Rapport entre ces chiffres : une vingtaine de lots (19 à 39) ont été consacrés au seul
quai, dont six (28 à 34) au diagnostic d'un pivot nul, puis de l'équilibre.

---

## 7. Étape 5 — recommandations (dix au plus)

Classées par valeur pour l'objectif, puis par effort : F = faible, M = moyen, É = élevé.

| # | Recommandation | Valeur | Effort | Preuve |
|---|---|---|---|---|
| **R1** | **Avant tout second ouvrage**, définir une interface « famille d'ouvrage » (paramètres depuis données, comptages attendus, script Salomé, blocs `.comm`, groupes d'appui, cas, grandeurs de synthèse) et y déplacer le quai comme **première implémentation**, sans en changer la sortie : `.comm` octet pour octet identique, test existant | très haute | É (2 lots) | § 5.1 : ~8 700 lignes propres au quai ; § 5.3 : arrêt à l'étape 1 |
| **R2** | Traiter le **radier / la dalle** comme deuxième famille, choisie pour ses **références indépendantes** : solution de Navier, cas tests officiels de plaque DKT. Premier niveau **E** de l'outil | très haute | É (~9-11 lots, moins après R1) | § 5.2 ; E9 |
| **R3** | Sortir du code toutes les **données de projet** : couches de sol de `terre.py:38-52`, cas et γ/ψ de `combinations.py:23-28`, cotes des vues. Les lire du fichier de données sourcé ; un test interdit les nombres d'ouvrage dans `src/` | haute | F-M | § 5.1, § 6.3 |
| **R4** | Donner à `generate` et `report` un **contrôle d'adéquation** : même projet dans la fiche et les données, clés exigées par la famille présentes, refus lisible sans trace Python | haute | F | E19, § 5.3 |
| **R5** | Créer une **base de constats `code_aster`** hors des fiches de projet, citée par référence : les 18 constats éprouvés par exécution doivent servir au radier | haute | M | § 3.3, § 5.1 (`PriorDecision` ne couvre que la pratique) |
| **R6** | Faire entrer dans `src/` et dans la CLI ce qui vit dans des scripts de lot : contrôles D, combinaisons, ferraillage, enregistrement d'arbitrage. Soumettre ce code à `mypy` | haute | M | § 6.3, § 6.4 (6 étapes « code de session ») |
| **R7** | Persister un **compte rendu JSON** par `run` (état, durée, version, empreintes) et encapsuler `run_aster.error_messages` (alarmes, `<F>`) | moyenne | F | E14, E15 |
| **R8** | Ajouter une **petite suite d'intégration réelle** (marqueur `requires_aster`, déjà déclaré et jamais utilisé) : un cas test officiel exécuté, un `validate` réel, un `mesh check` réel, lancée avant chaque lot | moyenne | F | § 6.1 : aucun test n'exécute Code_Aster |
| **R9** | Clore les écarts de ferraillage **avant toute note** : faire vérifier le tableau 7.2N et les γ accidentels par MM, remplir la ligne de comparaison MM, établir ou borner l'écart ELS (E1, E2), construire le 2D sur les cas tests officiels | moyenne | M-É | E1, E2, E5, E6, E9 |
| **R10** | Enrichir le **banc de recherche** avec les questions nées des lots 20-39 (ferraillage, pression aux nœuds, `LIAISON_SOLIDE`…) et des questions « description d'ouvrage » ; le faire annoter par MM ; viser `methode` et `theorie` (55,6 % et 66,7 %) | moyenne | M | § 4, banc relancé |

**Réponse aux deux questions posées.**

- *Que faire avant un second ouvrage ?* R1, R3 et R4 d'abord : sans elles, le second
  ouvrage recopierait le quai. R5 permet de ne pas rechercher de nouveau des faits déjà
  établis. R8 vérifie que rien ne régresse pendant la refactorisation.
- *L'architecture supporte-t-elle plusieurs familles ?* **La suite des étapes, oui ;
  l'implémentation, non.** La fiche, les données, les barrières, le moteur de maillage,
  la validation et l'exécution sont génériques. Le calcul des paramètres, les comptages,
  le générateur, la synthèse et les contrôles forment un bloc unique écrit pour le quai.
  Il faut les restructurer en greffons par famille derrière une interface commune (R1).
  L'ordre des étapes n'a pas à être refait.

---

## 8. Méthode et reproductibilité

Commandes lancées pendant l'audit, depuis la racine du dépôt :

```
.venv/bin/aster-expert mcp-check                                   # OK, 7 outils
.venv/bin/pytest -q --cov=aster_expert --cov-report=json:...        # 1078 passed, 4 min 17 s
.venv/bin/ruff check . ; .venv/bin/ruff format --check . ; .venv/bin/mypy
.venv/bin/aster-expert eval summary
.venv/bin/aster-expert eval bench --granularity by_file|by_subsection --output ...
.venv/bin/aster-expert eval profile-bench --output ...
.venv/bin/aster-expert search "<description dalle>" --profile methode --k 5   (+ 3 reformulations)
.venv/bin/aster-expert generate <fiche quai> dalle_donnees.yaml dalle_vide.med
.venv/bin/aster-expert generate data/config/hypotheses_trame_defaut.json dalle_donnees.yaml dalle_vide.med
.venv/bin/aster-expert report data/processed/runs/20260921T093141-fdefd4f7 --donnees dalle_donnees.yaml --sans-vues
```

Les états d'exécution sont décodés par un désérialiseur à classes factices, sans importer
`run_aster` (`annexes_lot40/decodage_status.py.txt`, conservé en `.txt` : c'est un outil
d'audit, pas du code du dépôt). La correspondance des indicateurs est celle de
`external/codeaster-src/run_aster/status.py`, `StateOptions` : `Ok` = 1024, `Fatal` = 256,
`Except` = 64, `Abort` = 512.

Annexes (`docs/audit/annexes_lot40/`) :

- `executions_archivees.json` : 190 exécutions, état, temps ;
- `banc_recherche_lot40.json` : hit@k relancés ;
- `tests_lot40.txt` : résultat de `pytest` et couverture par fichier ;
- `essai_dalle/` : aides des commandes, recherches, `generate`, `report`, données de la dalle ;
- `decodage_status.py.txt`.

Non fait, par choix de périmètre : aucune exécution Code_Aster ni Salomé nouvelle. Une
dalle aurait exigé d'écrire un `.comm` ou un script Salomé, ce que le lot interdit.
