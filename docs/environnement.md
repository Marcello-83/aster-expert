# Environnement d'exécution d'AsterExpert

Document ouvert au lot 41 bis, après le passage de la VM d'Ubuntu 24.04 à Ubuntu
26.04. Il sert de référence pour l'environnement et garde la trace de la première
panne réelle survenue hors du code (§ 4, forme réutilisable par le lot 42).

## 1. Diagnostic du lot 41 bis (étape 0, avant toute correction)

Relevé le 2026-10-01, **avant toute modification**. Commandes exactes entre
apostrophes inverses ; les sorties citées sont réelles.

### 1.1 Système

- `/etc/os-release` : `Ubuntu 26.04.1 LTS (Resolute Raccoon)`, noyau
  `7.0.0-34-generic`.
- Mise à niveau : `/var/log/dist-upgrade/history.log`, transaction du
  2026-09-30 03:24:25 → 03:47:58 (heure de la VM). Elle a **retiré** `python3.12`,
  `python3.12-venv`, `python3.12-dev`, `python3.12-minimal`, `libpython3.12*`
  (version `3.12.3-1ubuntu0.17`), et mis à niveau `python3` (3.12.3 → 3.14),
  `docker.io` (`29.1.3-0ubuntu3~24.04.2` → `29.1.3-0ubuntu4.1`) et `containerd`.
- Pythons présents : `/usr/bin/python3 -> python3.14`, `/usr/bin/python3.14`
  (3.14.4). **Aucun `python3.12`** (`which -a python3.12` : rien).

### 1.2 Outils Python

- `uv` : absent. `pipx` : absent. `pip` : `/usr/bin/pip` = `pip 25.1.1 from
  /usr/lib/python3/dist-packages/pip (python 3.14)` (paquet système, non utilisé
  par le projet).
- `.venv` (`.venv/pyvenv.cfg`) : créé par `/usr/bin/python3 -m venv` avec
  `executable = /usr/bin/python3.12`, `version = 3.12.3`. Ses liens
  `.venv/bin/python3 -> /usr/bin/python3` suivent désormais 3.14 :
  `.venv/bin/python -V` donne `Python 3.14.4`, alors que les paquets sont dans
  `.venv/lib/python3.12/site-packages` (341 Mo). Résultat :
  - `.venv/bin/pytest --version` → `ModuleNotFoundError: No module named '_pytest'` ;
  - `.venv/bin/aster-expert --help` → `ModuleNotFoundError: No module named 'aster_expert'` ;
  - `.venv/bin/aster-expert-mcp` (commande de `.mcp.json`) → même erreur.

### 1.3 Code_Aster

- Docker : `Docker version 29.1.3, build 29.1.3-0ubuntu4.1` (paquet Ubuntu
  `docker.io` ; l'ancien `docker-ce` de Docker Inc. est en état `rc`, retiré avant
  la mise à niveau). Service `systemctl is-active docker` : `active`. Utilisateur
  `ubuntu` dans le groupe `docker` (982) : `docker run --rm hello-world` réussit sans
  `sudo`.
- `cave` : `/usr/bin/cave`, `cave 0.1.4` (paquet `cave 0.1.4-1`) ; `cave list` :
  `16.8.0  17.4.0` ; épinglage global `~/.cave` = `17.4.0`.
- Image : `simvia/code_aster:17.4.0`, digest
  `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`, identique
  à `config/versions.yaml` (`image_digest`) ; Id `6a66bdaf0942`.
- Sonde dans l'image (prélude `aster_expert.execution.container_env`, réseau coupé,
  utilisateur 1000:1000) : `3.11.14 code_aster et medcoupling importables`.

### 1.4 Salomé

- `singularity-ce version 4.3.7-noble` (`/usr/bin/singularity`, paquet tiers compilé
  pour 24.04, conservé tel quel). `apptainer` : absent (non utilisé).
- `~/Desktop/salome_meca.sif` : présent (5 626 949 632 octets). Version lue :
  `Version        : V2024.1.0_scibian_univ` (= `mesh.salome.expected_version`).
- Lancement sans interface, options de `config/validation.yaml`
  (`--containall --cleanenv --no-home --net --network none`), script jetable
  maillant un cube 2 × 2 × 2 : code retour 0, `compute=True nodes=27 hexa=8`, 5,4 s.

### 1.5 Partage

- `partage on /media/sf_partage type vboxsf (rw,nodev,relatime)` ; utilisateur dans
  `vboxsf` ; création puis suppression d'un fichier d'essai : réussie.

### 1.6 Claude Code

- `claude --version` : `2.1.286 (Claude Code)`.
- `.mcp.json` : serveur `aster-expert`, `stdio`, commande
  `${CLAUDE_PROJECT_DIR:-/home/ubuntu/projets/aster-expert}/.venv/bin/aster-expert-mcp`.
  L'exécutable existe mais échoue à l'import (§ 1.2) ; la session de ce lot l'affiche
  `failed to connect (CONNECTION_CLOSED)`.

### 1.7 Synthèse

| Élément | État | Changement depuis Ubuntu 24 |
|---|---|---|
| OS | Ubuntu 26.04.1, noyau 7.0 | oui (24.04 → 26.04) |
| Python système | 3.14.4 seul | oui : 3.12 retiré, `python3` → 3.14 |
| `.venv` du projet | **cassé** (interpréteur 3.14, paquets 3.12) | oui (conséquence directe) |
| `uv` / `pipx` | absents | non |
| `pip` système | 25.1.1 sous 3.14 | oui (interpréteur) ; non utilisé |
| Docker | fonctionne (29.1.3, `docker.io`) | mise à niveau de paquet, même version amont |
| Droits Docker | groupe `docker`, sans `sudo` | non |
| `cave` | fonctionne (0.1.4, pin 17.4.0) | non |
| Image Code_Aster | présente, digest conforme | non |
| `code_aster` / `medcoupling` dans l'image | importables (Python 3.11.14 de l'image) | non |
| Singularity | fonctionne (4.3.7-noble) | non (paquet 24.04 conservé) |
| Image Salomé | se lance, maille sans interface | non |
| Partage `/media/sf_partage` | monté, écriture possible | non |
| Claude Code | 2.1.286 | version antérieure non consignée |
| Serveur MCP | **ne démarre pas** | oui (conséquence du `.venv`) |

Seul le Python du projet est cassé. Docker, `cave`, Singularity et le partage ne
demandent aucune intervention `sudo`.

## 2. Python géré par le projet (lot 41 bis)

### 2.1 `uv`

Méthode relevée dans la documentation officielle
(<https://docs.astral.sh/uv/getting-started/installation/>, 2026-10-01) :
installateur autonome `curl -LsSf https://astral.sh/uv/install.sh | sh`, binaire
dans `~/.local/bin`, `UV_NO_MODIFY_PATH=1` pour ne pas toucher aux profils du
shell (`~/.local/bin` est déjà dans le `PATH`). Script téléchargé puis lancé :
`uv 0.12.21 (x86_64-unknown-linux-gnu)`, installé dans `/home/ubuntu/.local/bin`
(`uv`, `uvx`). Ni `sudo` ni paquet système.

### 2.2 Version fixée

- `.python-version` : `3.12` (versionné).
- `pyproject.toml` : `requires-python = ">=3.12"` (borne basse, inchangée ; une
  borne haute interdirait l'évaluation séparée de 3.14) ; nouvelle section
  `[tool.uv] python-preference = "only-managed"` : `uv` n'emploie jamais un Python
  du système.
- `uv python install 3.12` : `cpython-3.12.14-linux-x86_64-gnu`, dans
  `~/.local/share/uv/python/` ; le `.venv` pointe sur le répertoire de la branche
  mineure (`cpython-3.12-linux-x86_64-gnu`), qu'une mise à jour de correctif de
  `uv` déplace sans casser le `.venv`.

### 2.3 `.venv` reconstruit et verrouillage

- L'ancien `.venv` (Python 3.12.3 du système, 341 Mo) a été écarté (déplacé hors du
  dépôt), puis `uv sync --locked --extra dev --extra mcp --extra index --extra figures`
  (équivalent à `-e ".[dev,mcp,index,figures]"` : le paquet est installé en mode
  éditable). `.venv/pyvenv.cfg` : `home = ~/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin`,
  `uv = 0.12.21` ; `.venv/bin/python` → `Python 3.12.14`.
- `uv.lock` (versionné) : produit par `uv lock` en imposant à chaque paquet la
  version relevée dans l'ancien `.venv` (`-P nom==version`, 62 paquets, ceux des
  vérifications du lot 41). Comparaison verrou / ancien `.venv` : **aucune version
  différente** ; absent du verrou : `pip` (24.0, outil d'amorçage de `python -m venv`,
  non requis) ; en plus dans le verrou : `colorama`, `pywin32`, `httpx2-jsfetch`
  (marqueurs Windows/Emscripten, non installés sous Linux).
- Reconstruction : `uv sync --locked --all-extras` donne le même environnement ;
  `--locked` échoue si `uv.lock` ne correspond plus à `pyproject.toml`.

### 2.4 Évaluation de Python 3.14 (non adoptée)

Environnement séparé et temporaire, hors du dépôt : `uv python install 3.14`
(`cpython-3.14.7`, géré par `uv`), `uv venv --python 3.14`, installation des
**mêmes versions** (`uv export --frozen` de `uv.lock`) et du projet en éditable,
puis `pytest tests/unit` : **789 passed in 23.78s**, aucun échec, aucun
avertissement. Toutes les roues du verrou existent pour 3.14 (aucune compilation).
L'environnement et l'interpréteur 3.14 ont ensuite été supprimés
(`uv python uninstall 3.14`). Non évalués sous 3.14 : `pytest` complet (tests des
projets), `mypy`, `pytest -m lent`, le serveur MCP. Le passage reste un lot à part.

## 3. `aster-expert env-check` (lot 41 bis)

Module `aster_expert.environnement.verification`, commande `aster-expert env-check`,
tests `tests/unit/test_env_check.py` (31 tests, sans Docker ni Singularity). Huit
vérifications, dans l'ordre, arrêt au premier écart (code 1, sans trace Python,
avec la liste des vérifications non évaluées) :

| Vérification | Ce qui est contrôlé |
| --- | --- |
| `python` | version de l'interpréteur = `.python-version` ; interpréteur = `.venv` du projet ; `.venv` non bâti sur un Python sous `/usr` |
| `dependances` | paquet installé ; dépendances directes (tous extras) présentes ; **chaque** distribution du `.venv` à la version de `uv.lock`, aucune hors verrou ; modules de chaque dépendance directe importés |
| `docker` | binaire présent ; le démon répond à l'utilisateur sans `sudo` |
| `cave` | binaire présent, `cave --version`, version épinglée |
| `image` | image résolue comme pour `aster-expert run` (épinglage `cave` ou `ASTER_IMAGE_REF`) ; digest = `config/versions.yaml` |
| `salome` | `mesh.salome.runtime` présent ; image présente ; version lue dans l'image = `expected_version` |
| `partage` | `environnement.partage` (`config/validation.yaml`) monté, écriture d'un fichier temporaire |
| `mcp` | commande de `.mcp.json` (développée comme `mcp-check`) exécutable ; son interpréteur est celui du `.venv` et importe `aster_expert.mcp.server` |

Limite : si le `.venv` est cassé au point que `aster-expert` ne démarre pas (cas
exact du 2026-09-30 : `ModuleNotFoundError: No module named 'aster_expert'`),
`env-check` ne peut pas s'exécuter ; le symptôme est alors l'échec de la commande
elle-même, et la correction est `uv sync --locked --all-extras`.

## 4. Trace de panne : changement de Python du système (pour le lot 42)

Première panne réelle survenue **hors du code** : aucun fichier du dépôt n'avait
changé. Fiche rédigée pour être reprise telle quelle comme diagnostic.

| Rubrique | Contenu |
| --- | --- |
| Identifiant | ENV-001 — `.venv` cassé par la mise à niveau d'Ubuntu (24.04 → 26.04) |
| Date | mise à niveau du 2026-09-30 (03:24-03:51, heure de la VM) ; constat le 2026-10-01 (lot 41 bis) |
| Symptôme | `.venv/bin/pytest` → `ModuleNotFoundError: No module named '_pytest'` ; `.venv/bin/aster-expert` et `.venv/bin/aster-expert-mcp` → `ModuleNotFoundError: No module named 'aster_expert'` ; serveur MCP `failed to connect (CONNECTION_CLOSED)` dans Claude Code ; `.venv/bin/python -V` → `Python 3.14.4` alors que les paquets sont sous `.venv/lib/python3.12/` |
| Cause | le `.venv` avait été créé par `python3 -m venv` avec le Python **du système** : ses liens `.venv/bin/python3 -> /usr/bin/python3` suivaient le paquet `python3`. La mise à niveau a retiré `python3.12` et fait pointer `/usr/bin/python3` sur 3.14 : le même `.venv` a changé d'interpréteur sans être touché, et un interpréteur 3.14 ne lit pas `lib/python3.12/site-packages`. |
| Détection | `aster-expert env-check`, vérification `python` (version contre `.python-version`, interpréteur du `.venv`, `.venv` non bâti sous `/usr`) et `mcp` (l'interpréteur de la commande de `.mcp.json` importe le serveur). Si le `.venv` est cassé au point qu'`aster-expert` ne démarre plus, l'échec de la commande elle-même est le symptôme (§ 3, limite). |
| Correction | `uv` installé dans l'espace utilisateur ; `uv python install 3.12` ; ancien `.venv` écarté ; `uv sync --locked --all-extras` ; contrôle par `env-check` puis `mcp-check`. Aucun `sudo`. Docker, `cave`, l'image Code_Aster, Singularity, l'image Salomé et le partage n'ont demandé aucune intervention (§ 1.7). |
| Prévention | Python géré par le projet (`.python-version`, `uv`, `python-preference = "only-managed"`) : une mise à jour de l'OS ne change plus l'interpréteur du `.venv` ; dépendances verrouillées (`uv.lock`, `--locked`) : une reconstruction redonne les mêmes versions ; `env-check` en tête de chaque lot (`CLAUDE.md`). |
| Reste exposé | Docker (`docker.io`) et `singularity-ce` (paquet tiers `-noble` conservé sous 26.04) restent des paquets système : une mise à niveau peut les changer ; `env-check` le détecte (démon, version lue dans l'image Salomé), la correction relève de MM. |
