# AsterExpert

Agent expert Code_Aster : recherche traçable dans le corpus officiel,
extraction des schémas exacts des commandes depuis le catalogue installé,
analyse et validation de fichiers `.comm`, exécution encadrée et dépouillement
des fichiers `.mess`.

Ce dépôt n'est pas un assistant généraliste. Il ne produit que des réponses
rattachées à une version de Code_Aster identifiée et à une source citable.

## Prérequis

- Machine virtuelle Ubuntu (26.04 depuis le lot 41 bis) avec Docker, `cave` et
  l'image Code_Aster ; Singularity et l'image Salomé-Méca pour le maillage.
- `uv` dans l'espace utilisateur (installateur officiel,
  `curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh`). **Le
  projet ne dépend jamais du Python du système** : la version est fixée par
  `.python-version` (3.12) et installée par `uv` (lot 41 bis,
  `docs/environnement.md`).
- Git, et un accès réseau à `gitlab.com` pour la synchronisation du corpus.

## Installation

```bash
git clone <url-du-depot> aster-expert
cd aster-expert
uv python install            # Python de `.python-version`, géré par uv
uv sync --locked --all-extras  # .venv aux versions exactes de uv.lock (paquet éditable)
cp .env.example .env
.venv/bin/aster-expert env-check
```

`uv.lock` (versionné) fixe la version exacte de chaque dépendance ; `--locked`
refuse de l'actualiser silencieusement. Mettre à jour une dépendance est un
changement délibéré (`uv lock --upgrade-package <nom>`), commité avec sa
justification. `aster-expert env-check` vérifie l'environnement entier (Python du
`.venv`, dépendances contre `uv.lock`, Docker, `cave`, digest de l'image, Salomé,
dossier partagé, exécutable du serveur MCP) et sort en erreur au premier écart.

Renseigner ensuite `.env`, en particulier le chemin de l'environnement
Code_Aster.

## Première étape : identifier l'installation

Aucune commande de génération ou de validation ne fonctionne tant que la
version cible n'est pas résolue.

```bash
aster-expert env detect
```

Cette commande exécute un script d'introspection avec le Python d'Aster et
écrit le résultat dans `config/versions.yaml`, section `detected`. Elle relève :

- la version rapportée par `run_aster` ;
- le chemin du package `code_aster` ;
- le chemin du catalogue ;
- la révision de l'installation lorsqu'elle est disponible.

En cas d'échec, corriger `.env` avant de poursuivre. Ne jamais compléter
`config/versions.yaml` à la main avec une version supposée.

## Utilisation

```bash
# Synchroniser les dépôts officiels sous external/
aster-expert sources sync

# Extraire les schémas de commandes du catalogue installé
aster-expert catalogue extract

# Interroger le corpus (profil explicite : syntaxe, theorie ou methode)
aster-expert search "ressort non linéaire unilatéral" --profile methode

# Texte intégral d'une section trouvée par 'search' (jamais tronqué)
aster-expert section --document U2.02.01 --section-path Conclusion_et_conseils_d_utilisation

# Schéma exact d'une commande
aster-expert catalogue show STAT_NON_LINE --keyword COMPORTEMENT

# Validation statique d'un fichier de commandes (niveau B)
aster-expert validate model.comm

# Exécution encadrée (niveau C) : le compte rendu lisible (compte_rendu.json et
# compte_rendu.md : commande, empreintes, durée, statut, alarmes et erreurs <F>
# extraites par run_aster.error_messages, fichiers produits) est écrit dans le
# répertoire de l'exécution
aster-expert run model.comm --timeout 1800

# Constats Code_Aster de la base partagée, avant d'écrire une commande
aster-expert constats chercher --commande CREA_MAILLAGE
aster-expert constats chercher "pression évaluée aux noeuds"
# Rejouer les cas d'essai des constats établis par exécution (changement de version)
aster-expert constats rejouer

# Un projet (ouvrage) : vérifier sa déclaration, puis enchaîner les étapes
aster-expert projet quai_cw_test_01 verifier
aster-expert projet quai_cw_test_01 maillage      # mesh run (cache) + mesh check
aster-expert projet quai_cw_test_01 generer       # .comm par le générateur du projet
aster-expert projet quai_cw_test_01 valider       # niveau B
aster-expert projet quai_cw_test_01 executer      # niveau C
aster-expert projet quai_cw_test_01 controles     # niveau D : équilibre, pesanteur, symétrie
aster-expert projet quai_cw_test_01 synthese
aster-expert projet quai_cw_test_01 combinaisons
aster-expert projet quai_cw_test_01 ferraillage
aster-expert projet quai_cw_test_01 tout          # toutes les étapes, dans l'ordre

# Commandes unitaires équivalentes, sur un projet
aster-expert generate quai_cw_test_01 [--donnees D] [--maillage M]
aster-expert report <exécution> --projet quai_cw_test_01 [--sans-vues]
aster-expert mesh check --projet quai_cw_test_01
```

Il n'existe pas de commande de dépouillement d'un `.mess` séparée : l'analyse des
messages est faite par `aster-expert run` (compte rendu ci-dessus), les tables de
résultats par les étapes `controles`, `synthese`, `combinaisons` et `ferraillage`
d'un projet.

Les commandes non encore implémentées sont listées dans
`docs/development-plan.md` avec leur lot d'appartenance.

## Serveur MCP (lot 8)

Un serveur MCP (`aster-expert-mcp`, module `aster_expert.mcp.server`) expose
neuf outils, chacun un simple emballage d'une capacité déjà existante :

| Outil | Capacité encapsulée | Niveau de la réponse |
|-------|----------------------|-----------------------|
| `search_codeaster_docs` | `aster_expert.retrieval` (lot 7/7b/7c) | A |
| `get_document_section` | `aster_expert.indexing.bm25_index` (lot 8c) | A |
| `get_command_schema` | `aster_expert.catalogue` (lot 4/4b) | A |
| `analyze_comm` | `aster_expert.parsing.comm_parser` (lot 9) | A |
| `validate_comm` | `aster_expert.validation.validate` (lot 10/10b/10c) | B |
| `search_test_cases` | `aster_expert.parsing.comm_parser` sur `astest` (lot 22) | A |
| `read_test_case` | lecture bornée d'un fichier de commandes de `astest` (lot 22) | A |
| `search_constats` | `aster_expert.constats` : base partagée des constats Code_Aster (lot 41) | A (chaque constat porte son propre niveau, A à D) |
| `search_connaissances` | `aster_expert.connaissances` : les six couches de `connaissances/` (lot 42) | A (chaque entrée porte son statut et son niveau, A à E) |

`get_document_section` (lot 8c) renvoie le texte intégral, jamais tronqué,
d'un fragment ou d'une section — `search_codeaster_docs` ne renvoie qu'un
extrait de 280 caractères par résultat, insuffisant pour fonder une
affirmation sur le contenu réel d'une section (un tableau comparatif, une
liste de conditions). Désigner la section soit par `fragment_id` (recopié
d'un résultat de recherche), soit par `document_id` + `section_path` +
`granularity` ensemble.

Chaque réponse porte explicitement son niveau (`validation_level`) et ses
sources (identifiant de document, section, chemin, révision — déjà portées
par les modèles pydantic existants, jamais redéfinies pour ce serveur) : un
niveau `A` n'est jamais présenté comme une syntaxe vérifiée, une exécution
réussie, ni une validité physique. `search_codeaster_docs` exige que
l'appelant fournisse explicitement `profile` (`syntaxe`/`theorie`/`methode`)
: ce serveur ne devine jamais le profil à partir du texte de la requête
(ADR-007, `docs/architecture.md`) — la description de l'outil, visible par
l'appelant, explique comment le choisir.

Chaque appel est journalisé dans `data/processed/query_log.jsonl`
(horodatage, outil, requête, profil, filtres, documents retournés avec leurs
scores, durée) : `analyze_comm` et `validate_comm` n'y enregistrent jamais le
contenu du fichier fourni, seulement son nom et son empreinte SHA-256.

Prérequis avant de démarrer le serveur : un index construit
(`aster-expert index build`), un catalogue extrait
(`aster-expert catalogue extract`) — `search_codeaster_docs`/
`get_document_section`/`get_command_schema` échouent explicitement sinon. `validate_comm` a en plus
besoin de `ASTER_CONTAINER_WORKROOT` (un répertoire dédié, jamais `$HOME` ni
la racine du dépôt — voir `.env.example`, ADR-006) et de Docker.

Installer les dépendances du serveur (installation éditable : le serveur lance
toujours le code source du dépôt) :

```bash
uv sync --locked --all-extras
```

Le serveur est déclaré au niveau du projet, dans `.mcp.json` (versionné), sans
aucun chemin propre à une machine (lot 41 ter : le même fichier sert dans la VM et
dans le Cloud, `docs/cloud.md`) :

```json
"command": "uv",
"args": ["run", "--project", "${CLAUDE_PROJECT_DIR:-.}", "--locked",
         "--all-extras", "--quiet", "aster-expert-mcp"],
"env": {"ASTER_EXPERT_ROOT": "${CLAUDE_PROJECT_DIR:-.}",
        "ASTER_CONTAINER_WORKROOT": "${CLAUDE_PROJECT_DIR:-.}/data/processed/workroot"}
```

`${VAR}` et `${VAR:-défaut}` sont développés par Claude Code dans `command`, `args`
et `env` ; `CLAUDE_PROJECT_DIR` n'étant défini que dans l'environnement du serveur
lancé, c'est la valeur par défaut `.` qui s'applique, et Claude Code lance un
serveur de projet dans le répertoire du projet (documentation MCP).
`uv run --locked --all-extras` met le `.venv` en conformité avec `uv.lock` avant de
lancer le serveur. Une entrée du même
nom en portée `local` ou `user` primerait sur `.mcp.json` sans fusion : la
retirer (`claude mcp remove aster-expert -s local`). Le répertoire de travail
est créé au démarrage du serveur.

Une session Claude Code garde le processus serveur lancé à son démarrage : du
code ajouté ensuite n'y est pas visible. Vérifier avant tout lot, sur un serveur
neuf lancé comme `.mcp.json` le déclare :

```bash
aster-expert mcp-check
```

La commande compare les outils du serveur à ceux que déclare `server.py`, appelle
chacun sur une requête minimale (dont `validate_comm`, qui lance le conteneur) et
sort en erreur au premier écart.

## Organisation : un tronc commun, des projets, une base de constats (lot 41)

```
src/aster_expert/   tronc commun : ce qui vaut pour tout ouvrage
projets/<nom>/      un ouvrage = un projet (code, données, déclaration, références)
connaissances/      base partagée des constats Code_Aster, un fichier par constat
config/             paramètres de sources, versions, recherche et validation
data/               corpus brut, corpus transformé, index, jeux d'évaluation,
                    archives des essais des lots (data/examples/lotNN_*)
external/           clones des dépôts Code_Aster (non versionnés)
docs/               architecture, corpus, métadonnées, rapports d'essais des lots
scripts/            scripts autonomes (dont ceux exécutés par le Python d'Aster)
                    et essais génériques des lots
tests/              tests unitaires, d'intégration (dont `pytest -m lent`)
```

**Tronc commun** (`src/aster_expert/`) : catalogue et validation B ; recherche
documentaire et cas tests ; exécution et compte rendu ; schéma de fiche,
arbitrage et historique ; données structurées ; exécution Salomé et vérificateur
de maillage à invariants déclaratifs ; contrôles D paramétrés par la déclaration
(`controles`) ; lecture MED ; combinaisons à partir de la déclaration et des
données (`combinaisons`) ; ferraillage 1D par `CALC_FERRAILLAGE` et module EN 1992
(`ferraillage`, `rebar`) ; base de constats (`constats`) ; déclaration et
enchaînement des projets (`projet`). Aucune référence à un ouvrage : un test
l'interdit (`tests/unit/test_tronc_commun_sans_ouvrage.py`).

**Projet** (`projets/<nom>/`) : un paquet Python importé depuis `projets/`, avec
sa déclaration `projet.yaml` (schéma `aster_expert.projet.declaration`), sa fiche,
ses données et leurs sources, son script Salomé et ses invariants, son générateur
de `.comm` (ou un `.comm` écrit), ses extensions (charges intégrées, forces de
ressorts, prose de ses rapports), ses scripts et ses tests, ses résultats de
référence. La déclaration contient : le maillage et ses invariants, le `.comm` ou
son générateur et les données qu'il exige, les groupes d'appui et de ressorts de
l'équilibre, les cas de charge et leurs résultantes attendues, les plans de
symétrie, les combinaisons, les éléments à ferrailler. Le tronc commun ne lit que
cette déclaration et les résultats ; une déclaration incomplète ou incohérente est
refusée avec la liste des motifs (donnée manquante, groupe absent du maillage, cas
sans résultante attendue, données d'un autre ouvrage). Premier projet :
`projets/quai_cw_test_01/` (quai combi-wall QUAI-CW-TEST-01).

**Base de constats** (`connaissances/constats_code_aster/CA-nnn.json`) : un fait
établi sur Code_Aster par fichier (version, niveau A à D, sources dont les cas
d'essai versionnés, commandes et mots-clés concernés, résumé du piège en une
phrase). Une fiche de projet référence un constat (`{"nature": "constat",
"constat_id": ...}`) au lieu de le recopier. Recherche : `search_constats` (MCP),
`aster-expert constats chercher` ; rejeu à chaque changement de version :
`aster-expert constats rejouer`.

**Base de connaissances** (lot 42, `connaissances/LISEZMOI.md`) : six couches
(constats, diagnostics, patrons, contrôles, références de validation, précédents),
statuts `observé`/`établi`/`promu`. Recherche : `search_connaissances` (MCP),
`aster-expert connaissances chercher` ; contrôle : `aster-expert connaissances
verifier` ; promotion explicite : `aster-expert connaissances promouvoir <id>` ;
précédent proposé (jamais appliqué) : `aster-expert connaissances
proposer-precedent` ; rejeu des références : `aster-expert connaissances
rejouer-references`. Retour d'expérience de fin de lot : `aster-expert rex
<projet>` (échecs à classer, métriques, `connaissances/metriques/tableau_de_bord.md`).

<!-- etat:debut (généré depuis docs/etat.yaml par `aster-expert etat readme`) -->
## État du projet

Mis à jour au lot 51ter (2026-10-16), depuis `docs/etat.yaml` : ne pas éditer cette section à la main.

Lots : 66 faits sur 68 ; autres : 12 (partiel), 13 (non fait). Dernier lot : 51ter, Pontons aluminium : ponton intégral (culée, cinq palées, cinq grandes travées, porte-à-faux), cotes de l'AVP (P53, P47 annulée ; axe +1,16, P54), tubes drainés (P55, P50 annulée), houle par surfaces et par état limite (P56), houle et accostage non concomitants (P57), facteurs ψ de l'amarrage (P59) ; 221 cas unitaires, Q et QD par modules en lignes d'influence, 2 351 600 combinaisons par variante en règles ; quatre variantes (A10, A12, B10, B12) à FIN, harnais D 221/221 ; ancrage requis par palée, réactions de la culée, chaîne longitudinale, DX des axes ; harnais D version 3 (critère absolu des cas d'échelle nulle) et angles de l'anneau comptés une fois ; charges.med de B10.

Capacités :

- recherche : niveau A, opérationnelle. Moteur lexical BM25 seul ; ni index vectoriel ni reranking (lots conditionnels C1, C2 non lancés). Corpus, index et catalogue absents d'un runner neuf (ils se reconstruisent, scripts/cloud_setup.sh).
- catalogue : niveau A, opérationnelle. Un seul catalogue : Code_Aster 17.4.0, image par digest (config/versions.yaml).
- analyse : niveau A, opérationnelle. Les constructions dynamiques sont déclarées, jamais devinées.
- validation_b : niveau B, opérationnelle. Syntaxe confrontée au catalogue ; ne dit rien de l'exécution ni de la physique.
- execution_c : niveau C, opérationnelle. Racines d'exécution déclarées une à une (execution.allowed_roots). Salomé : VM seulement. Depuis le lot 47 quater, délai, mémoire, ncpus et mpi_nbcpu viennent de la ligne de commande, puis de l'.export (répercutés sur docker run), puis de la configuration (config/machine.local.yaml, config/validation.yaml) et de défauts calculés (aster_expert.execution.ressources) ; MPI exécutable (statut lu sur chaque rang, ENV-004) mais sans gain mesuré sur l'estacade ; refus sous 10 Go de disque libre (ENV-003). Lot 49 : fils = min(4, processeurs ÷ exécutions simultanées) sur 3 répétitions par point (gain 1,34 à 4 fils sur la production, perte au-delà) ; PARALLELISME_TEMPS='OUI' refusé avant exécution (DIAG-027).
- controles_d : niveau D, opérationnelle. Harnais par défaut depuis le lot 46 (CTL-005, CTL-006, CTL-012, CTL-013) ; version 2 de CTL-005 et CTL-013 (lot 47 bis) : échelle déclarée d'un cas autoéquilibré (self_equilibrated_scale). Paquets du quai et de la dalle réexportés avec le harnais au lot 49, sans exécution.
- reference_e : niveau E, partielle. Niveau E sur la seule dalle (solution de Navier) ; aucune référence pour le quai.
- ferraillage : niveau D, opérationnelle. Module EN 1992 indépendant calibré sur ssll13b/ssll13d ; FERR_MIN_FISS refusé pour les poutres ; tableau 7.2N transcrit, à vérifier par MM.
- notes : niveau D, opérationnelle. Contenu tiré de la fiche, des données et du paquet de résultats, jamais écrit à la main.
- maillage : niveau D, opérationnelle. Salomé n'existe que dans la VM ; indisponible dans le Cloud.
- base_de_connaissances : sans niveau de validation, opérationnelle. Depuis le lot 46 une exécution de projet déclare ses connaissances ; aucune exécution passée n'est attribuée ; manifestes d'archive à enregistrer dans la VM (rex --manifeste).
- securite_mcp : sans niveau de validation, opérationnelle. Politique de lecture appliquée aux outils MCP et aux commandes recevant un chemin ; les sorties (écriture) ne sont pas couvertes.
- integration_continue : sans niveau de validation, opérationnelle. ci.yml vert sur la branche du lot 46 (2 min 28 s) ; ci-lent.yml corrigé au lot 46 bis (profil ci), passage réel vert sur la branche claude/blissful-turing-ajkazc (constaté par MM, 2026-10-05).
- contre_calcul : niveau C, partielle. Comparaison à un calcul externe non validé (type calcul_externe_non_valide, jamais E ni promu) ; REF-015 observée depuis le lot 48 bis (grandeurs dérivées, non rejouables par l'outil) ; lecture C1 à C13 propre à l'estacade ; écarts des moments de pieux inexpliqués.
- livrables : niveau C, opérationnelle. MED et VTU produits par une exécution de post-traitement qui recopie le .comm de production et n'est acceptée que si ses tables égalent celles de la production (dalle 82 134, quai 9 931 632, estacade 135 668 valeurs) ; CTL-013 sur le MED des charges ; MED jamais versionnés (estacade 1,16 Go). Lecture directe du MED par un ParaView Windows non vérifiée (greffon MEDReader des binaires 5.12+, source secondaire) : VTU fournis. Les scripts ParaView supposent ParaView ≥ 5.10 (noms de tableaux entre guillemets). Le contrôle des charges ne détecte pas un déplacement qui conserve l'aire chargée (point d'application rapporté).
- synthese_ingenieur : niveau C, opérationnelle. Lecture des livrables du lot 49, sans calcul Code_Aster : torseurs concomitants par superposition des cas et des positions mobiles, chaque valeur relue par resultats lire (écart ≤ 1e-9) ; équilibre par état limite. Sections et critères déclarés par projet (engineering_summary). Lot 49 ter : section en T (tee_section, preuve par l'équilibre d'une coupe), bande ±b/2 des coques (exclusion_band), coupe interpolée à une cote, zones disjointes et signe déclaré, moment sur appui E27 avec modèles dérivés du tronc commun (derived_models, livrables --modele, harnais D) et variantes à seuil, convention ingénieur et formats du classeur, livraison avec empreintes (projet <nom> livraison). Modèle auxiliaire A1 de l'estacade hors du critère analytique de 2 % (−8,1 %, expliqué) ; A3 donne un moment d'encastrement nul (charges verticales seules). Quai : efforts de la poutre de couronnement nuls sous G, EAU_P et Q1 (réserve déclarée, à confirmer par MM).

Projets :

- `quai_cw_test_01` (Quai combi-wall QUAI-CW-TEST-01) : niveau D atteint, preuve `projets/quai_cw_test_01/resultats/paquet/paquet.json`.
- `dalle_appuyee_01` (Dalle appuyée C30/37 6 x 4 x 0,30 m) : niveau E atteint, preuve `projets/dalle_appuyee_01/resultats/paquet/paquet.json`.
- `estacade_pieux_01` (Estacade sur pieux ESTACADE-PIEUX-01 (contre-calcul d'un modèle non validé)) : niveau D atteint, preuve `projets/estacade_pieux_01/resultats/paquet/paquet.json`.
- `pontons_alu_01` (Ponton en aluminium PONTONS-ALU-01, palée type sur appuis à axe et trois travées (calcul PRO)) : niveau D atteint, preuve `projets/pontons_alu_01/resultats/paquet/paquet.json`.

Métriques :

- Tableau de bord des projets : `connaissances/metriques/tableau_de_bord.md`
- Métriques du quai : `connaissances/metriques/quai_cw_test_01.yaml`
- Métriques de la dalle : `connaissances/metriques/dalle_appuyee_01.yaml`
- Registre du retour d'expérience du quai : `connaissances/rex/quai_cw_test_01.yaml`
- Registre du retour d'expérience de la dalle : `connaissances/rex/dalle_appuyee_01.yaml`
- Métriques de l'estacade : `connaissances/metriques/estacade_pieux_01.yaml`
- Registre du retour d'expérience de l'estacade : `connaissances/rex/estacade_pieux_01.yaml`
- Métriques des pontons : `connaissances/metriques/pontons_alu_01.yaml`
- Registre du retour d'expérience des pontons : `connaissances/rex/pontons_alu_01.yaml`

<!-- etat:fin -->

## Tests

```bash
pytest               # série par défaut : aucun Docker, aucun Salomé
pytest -m lent       # tests réels : Code_Aster (cas du lot 22, arrêt <F> du lot 39)
                     # et Salomé (géométrie 1 du lot 26) puis mesh check ; ~2 min
pytest -m lent_aster   # Code_Aster seul (VM et Cloud)
pytest -m lent_salome  # Salomé seul (VM) ; ressource absente : test ignoré, motif affiché
```

## Niveaux de validation

Toute réponse produite par le système porte un niveau :

| Niveau | Signification |
|--------|---------------|
| A | Réponse documentaire, non exécutée |
| B | Syntaxe confrontée au catalogue |
| C | Fichier exécuté jusqu'à `FIN` |
| D | Résultats soumis à des contrôles physiques |
| E | Résultats comparés à une référence validée |

## Contribution

Les règles permanentes du dépôt sont dans `CLAUDE.md`. Elles s'appliquent aux
contributions humaines comme aux contributions assistées.

## Licences

La licence du code de ce dépôt reste à choisir : ajouter un fichier `LICENSE`
et décommenter le champ correspondant dans `pyproject.toml` avant toute
diffusion. Les dépôts Code_Aster clonés sous `external/` conservent leurs licences propres
(GPL v3 pour les sources, GFDL v1.3 pour la documentation) et ne sont pas
redistribués par ce projet.
