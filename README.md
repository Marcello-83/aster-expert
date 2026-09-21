# AsterExpert

Agent expert Code_Aster : recherche traçable dans le corpus officiel,
extraction des schémas exacts des commandes depuis le catalogue installé,
analyse et validation de fichiers `.comm`, exécution encadrée et dépouillement
des fichiers `.mess`.

Ce dépôt n'est pas un assistant généraliste. Il ne produit que des réponses
rattachées à une version de Code_Aster identifiée et à une source citable.

## Prérequis

- Machine virtuelle Ubuntu 24.04 avec une installation Code_Aster fonctionnelle.
- `run_aster` accessible dans le `PATH` de l'environnement Aster.
- Python 3.12 ou supérieur pour le projet (distinct du Python d'Aster).
- Git, et un accès réseau à `gitlab.com` pour la synchronisation du corpus.

## Installation

```bash
git clone <url-du-depot> aster-expert
cd aster-expert
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

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

# Interroger le corpus
aster-expert search "ressort non linéaire unilatéral" --version 18

# Texte intégral d'une section trouvée par 'search' (jamais tronqué)
aster-expert section --document U2.02.01 --section-path Conclusion_et_conseils_d_utilisation

# Schéma exact d'une commande
aster-expert catalogue show STAT_NON_LINE --keyword COMPORTEMENT

# Validation statique d'un fichier de commandes
aster-expert validate model.comm

# Exécution encadrée puis dépouillement
aster-expert run model.comm --timeout 1800
aster-expert mess analyze resultats/model.mess
```

Les commandes non encore implémentées sont listées dans
`docs/development-plan.md` avec leur lot d'appartenance.

## Serveur MCP (lot 8)

Un serveur MCP (`aster-expert-mcp`, module `aster_expert.mcp.server`) expose
sept outils, chacun un simple emballage d'une capacité déjà existante :

| Outil | Capacité encapsulée | Niveau de la réponse |
|-------|----------------------|-----------------------|
| `search_codeaster_docs` | `aster_expert.retrieval` (lot 7/7b/7c) | A |
| `get_document_section` | `aster_expert.indexing.bm25_index` (lot 8c) | A |
| `get_command_schema` | `aster_expert.catalogue` (lot 4/4b) | A |
| `analyze_comm` | `aster_expert.parsing.comm_parser` (lot 9) | A |
| `validate_comm` | `aster_expert.validation.validate` (lot 10/10b/10c) | B |
| `search_test_cases` | `aster_expert.parsing.comm_parser` sur `astest` (lot 22) | A |
| `read_test_case` | lecture bornée d'un fichier de commandes de `astest` (lot 22) | A |

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
pip install -e ".[mcp]"
```

Le serveur est déclaré au niveau du projet, dans `.mcp.json` (versionné) :

```bash
claude mcp add aster-expert -s project \
  -e 'ASTER_EXPERT_ROOT=${CLAUDE_PROJECT_DIR}' \
  -e 'ASTER_CONTAINER_WORKROOT=${CLAUDE_PROJECT_DIR}/data/processed/workroot' \
  -- '${CLAUDE_PROJECT_DIR}/.venv/bin/aster-expert-mcp'
```

`${CLAUDE_PROJECT_DIR}` est développé par Claude Code (documentation MCP :
`${VAR}` et `${VAR:-défaut}` dans `command`, `args` et `env`). Une entrée du même
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

## Structure

```
config/      paramètres de sources, versions, recherche et validation
data/        corpus brut, corpus transformé, index, jeux d'évaluation
external/    clones des dépôts Code_Aster (non versionnés)
docs/        architecture, corpus, métadonnées, plan de développement
src/         code du projet
scripts/     scripts autonomes, dont ceux exécutés par le Python d'Aster
tests/       tests unitaires, d'intégration et d'évaluation
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
