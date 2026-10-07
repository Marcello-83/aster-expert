# Sessions Claude Code dans le Cloud (lot 41 ter)

Depuis le lot 41 ter, le dépôt est hébergé sur un dépôt GitHub **privé**
(`docs/publication_github.md`). Une session Claude Code peut donc tourner, en plus
de la VM, dans le Cloud (claude.ai/code, application mobile, `claude --cloud`). Ce
document dit ce qu'on y fait, comment l'environnement Cloud est configuré, et
contient le texte exact du script d'installation et de la première tâche d'essai.

Sources : pages « Use Claude Code in the cloud », « Configure cloud environments »,
« MCP » et « Hooks » de la documentation Claude Code, relues le 2026-10-01. Ce qui
n'est pas écrit dans ces pages est signalé comme **non établi** (§ 8).

## 1. Ce qu'on fait où

| Travail | Cloud | VM |
|---|---|---|
| Développement, `ruff`, `mypy`, `pytest` (série par défaut) | oui | oui |
| Recherche documentaire, catalogue, outils MCP (`aster-expert`) | oui | oui |
| Fiche d'hypothèses, constats, génération et validation (niveau B) | oui | oui |
| Exécutions Code_Aster (niveau C), `pytest -m lent_aster` | oui (Docker, image tirée par digest) | oui |
| Maillage Salomé (`mesh run`), `pytest -m lent_salome` | **non** : image `salome_meca.sif` locale, plusieurs Go, sur aucun registre | oui |
| Dossier partagé `/media/sf_partage` (livrables lourds) | **non** | oui |
| MED de résultats volumineux, `résultats_MED_Paravis/`, ParaVis | **non** (ni versionnés ni copiés) | oui |
| `git push` | sur la branche de travail de la session seulement (proxy GitHub) ; jamais `main` | branche `lot-NN` |

Un lot qui exige Salomé ou le dossier partagé ne se lance que dans la VM. Les
exécutions Code_Aster d'un modèle complet (plusieurs minutes, MED de 140 Mo) sont
possibles dans le Cloud mais leurs MED n'en sortent pas : seuls les comptes rendus
et tableaux versionnables reviennent par la branche.

Machine Cloud (documentation) : Ubuntu 24.04 x86_64, 4 vCPU, 16 Go de RAM, 30 Go de
disque, Docker, `uv`, `gh` et `git` préinstallés. Le corpus (≈ 1,2 Go de copies de
travail), l'image Code_Aster (5,0 Go décompressés) et le `.venv` tiennent dans ces
30 Go.

## 2. Profil `vm`, `cloud` ou `ci`

`aster-expert env-check` annonce son profil en première ligne :

- `cloud` quand `CLAUDE_CODE_REMOTE=true` (variable posée par Claude Code dans une
  session Cloud, jamais en local), `ci` quand `GITHUB_ACTIONS=true` (runner GitHub,
  lot 46 bis), sinon `vm` ; `ASTER_EXPERT_PROFIL=vm|cloud|ci` force le profil
  (essais) ;
- en profil `ci`, mêmes absences attendues que dans le Cloud, plus celle du serveur
  MCP ; sans `cave`, `ASTER_IMAGE_REF` est **obligatoire** (la vérification `image`
  échoue sans elle). Le workflow `ci-lent` la construit depuis `config/versions.yaml`
  (digest lu, jamais recopié), après `docker pull` par digest, et `env-check` y est
  bloquant ;
- en profil `cloud`, l'absence de `cave`, de Salomé et du dossier partagé est
  **attendue** : la ligne commence par `--` au lieu de `OK` et le bilan les compte
  à part (« dont N absences attendues ») ; toute autre vérification (Python du
  `.venv`, `uv.lock`, Docker, image par digest, serveur MCP) est la même que dans la
  VM et échoue de la même façon.

Dans le Cloud, l'image n'est pas désignée par `cave` mais par
`ASTER_IMAGE_REF=<digest>`, que le crochet d'ouverture de session écrit pour la
session (§ 5).

## 3. Tests réels

Le marqueur `lent` du lot 41 est scindé :

- `pytest -m lent_aster` : Code_Aster réellement exécuté (cas du lot 22, arrêt
  `<F> <CALCULEL7_40>` du lot 39) ; exige Docker, l'image par digest et le catalogue
  extrait ;
- `pytest -m lent_salome` : géométrie 1 du lot 26 maillée par Salomé puis
  `mesh check` ; exige Singularity, l'image Salomé et Docker ;
- `pytest -m lent` lance encore les deux.

Une ressource absente fait **ignorer** le test avec son motif
(`aster_expert.environnement.ressources`, `tests/conftest.py`), par exemple :
`lent_salome ignoré : singularity absent du PATH (Salomé n'existe que dans la VM :
image locale, sur aucun registre)`.

## 4. Serveur MCP portable

`.mcp.json` ne contient plus aucun chemin de la VM :

```json
"command": "uv",
"args": ["run", "--project", "${CLAUDE_PROJECT_DIR:-.}", "--locked",
         "--all-extras", "--quiet", "aster-expert-mcp"]
```

Faits de la documentation « MCP » : `${VAR:-défaut}` est développé dans `command`,
`args` et `env` ; pour un `.mcp.json` de projet, `${CLAUDE_PROJECT_DIR}` exige une
valeur par défaut (la variable n'est posée que dans l'environnement du serveur
lancé, constat du lot 25) ; un serveur stdio déclaré dans le `.mcp.json` du projet
est lancé **dans le répertoire du projet**. La valeur par défaut `.` désigne donc
le dépôt, dans la VM comme dans le Cloud. `uv run --locked --all-extras` crée ou
met à jour le `.venv` exactement selon `uv.lock` avant de lancer le serveur (sans
réseau quand il est déjà conforme) : le serveur démarre même si le crochet de
session n'a pas encore tourné. `--all-extras` est indispensable : sans lui,
`uv run` retirerait les extras du `.venv`.

`ASTER_EXPERT_ROOT` et `ASTER_CONTAINER_WORKROOT` peuvent être relatifs : le
serveur les résout (`Path.resolve()`). `mcp-check` et `env-check` résolvent `uv`
dans le `PATH` et vérifient que `uv run … python` est bien le Python du `.venv` du
projet.

## 5. Configuration de l'environnement Cloud (à faire par MM)

Une fois, sur claude.ai/code, sélecteur d'environnement → **Add cloud
environment** :

1. **Name** : `aster-expert`.
2. **Network access** : **Custom**, case **Also include default list of common
   package managers** cochée, et dans **Allowed domains** :

   ```text
   releases.astral.sh
   ```

   Motif : `uv` télécharge Python 3.12 depuis `releases.astral.sh` (constaté :
   `uv python install 3.12.14 -v`, uv 0.12.21), domaine absent de la liste
   « Trusted ». Python du système exclu par la règle du lot 41 bis
   (`python-preference = "only-managed"`). Tout le reste est dans la liste par
   défaut : `pypi.org`/`files.pythonhosted.org` (`uv`, dépendances),
   `gitlab.com` (corpus), `registry-1.docker.io`, `auth.docker.io`,
   `production.cloudflare.docker.com` (image).
3. **Environment variables** : aucune n'est requise pour le calcul (le crochet de
   session écrit `ASTER_IMAGE_REF` et `ASTER_CONTAINER_WORKROOT`). Ne jamais y mettre
   de clé ou de jeton : toute personne qui utilise l'environnement les lit. Seule
   exception, la liste des termes confidentiels d'un projet réel, § 11.
4. **Setup script** : coller **tel quel** le texte de l'annexe (§ 10), qui est le
   contenu exact de `scripts/cloud_setup.sh`.

L'accès au dépôt privé passe par l'application GitHub Claude installée sur ce
**seul** dépôt (`docs/publication_github.md`, § 9).

## 6. Ce que fait le script, et sa durée

Le script s'exécute en root avant le lancement de Claude Code. Tout ce qui est long
est rangé **hors du dépôt**, dans `/opt/aster-expert` (variable
`ASTER_CLOUD_CACHE`) : chaque session repart d'un clone neuf, l'instantané du
disque (cache de l'environnement) garde le reste. Le dépôt n'en reçoit que des
liens symboliques, tous ignorés par Git (test).

Étapes, chacune journalisée avec sa durée dans `/opt/aster-expert/installation.log`
(`ETAPE <nom> OK|ECHEC <durée> s`) ; le script sort toujours en 0 (une erreur
empêcherait la session de démarrer), `env-check` dit ensuite ce qui manque :

1. `uv` 0.12.21 depuis PyPI si celui de l'image diffère ;
2. Python 3.12 géré par `uv` ;
3. image `simvia/code_aster@sha256:d8d19ea9…` tirée **par digest** puis étiquetée
   `17.4.0` en local, en parallèle des étapes 4 à 6 ;
4. corpus cloné depuis gitlab.com (`--filter=blob:none --branch 17.4.0
   --single-branch`, comme `sources sync`), commit figé contrôlé ;
5. si le dépôt est visible : `uv sync --locked --all-extras`, crochet Git, liens ;
   `sources sync` (adopte le clone, écrit le manifeste), `sources inventory`,
   `sources xref` ;
6. après l'image : `catalogue extract` (puis `config/versions.yaml` remis à sa
   version du dépôt si seul l'horodatage a changé, digest contrôlé), `sources
   command-map`, `fragments build`, `index build` (les deux granularités et
   l'index enrichi).

Durées **mesurées dans la VM** (2026-10-01), clone neuf, cache vide, cache `uv`
vide, Python et `uv` téléchargés, corpus recloné depuis gitlab.com ; seule l'image
Docker était déjà présente :

| Étape | Durée |
|---|---|
| `uv` (PyPI) | 2,2 s |
| Python 3.12.14 | 4,7 s |
| image (déjà présente : non mesurée à froid) | 0,7 s |
| clonage du corpus | 102,0 s |
| `uv sync` | 8,5 s |
| corpus (`sources sync`, inventaire, graphe) | 104,6 s |
| catalogue | 6,2 s |
| table, fragments, index | 13,5 s |
| **total** | **242 s** |

Produits identiques à ceux de la VM : les trois index BM25 à l'octet ; le
catalogue aux horodatages près et à l'ordre près de deux listes de valeurs
(`LIRE_RESU`, `TEST_RESU`, ensemble non ordonné du catalogue) ; graphe, table et
fragments aux horodatages près.

**Image non mesurée** : 1,6 Go compressés, 5,0 Go décompressés. Le tirage se fait
en parallèle du clonage et du corpus (≈ 215 s avant que le catalogue en ait
besoin). Si l'essai Cloud montre que l'installation dépasse cinq minutes (elle
n'est alors pas mise en cache), retirer l'image du script d'installation en
remplaçant, dans le texte collé, `etape image tirer_image &` par `true &`, et la
tirer à la demande dans la session :

```bash
bash scripts/cloud_setup.sh --image   # image par digest, puis catalogue et index
```

## 7. Ouverture de session

`.claude/settings.json` (versionné) déclare un crochet `SessionStart`
(`startup|resume`) : `bash "$CLAUDE_PROJECT_DIR/scripts/cloud_setup.sh" --session`.
Hors du Cloud il ne fait rien (`CLAUDE_CODE_REMOTE` ≠ `true`) et ne crée rien. Dans
le Cloud : démarre `dockerd` s'il ne répond pas (l'instantané ne garde aucun
processus), `uv sync`, crochet Git `pre-commit`, liens vers le cache ; corpus,
catalogue et index s'ils manquent (cas où le script d'installation n'aurait pas vu
le dépôt) ; puis écrit dans `$CLAUDE_ENV_FILE` `ASTER_IMAGE_REF`,
`ASTER_CONTAINER_WORKROOT` et, si besoin, le `PATH` de `uv`.

Essai de bout en bout **dans la VM**, en simulant le Cloud (clone neuf préparé par
le script, `CLAUDE_CODE_REMOTE=true`, `HOME` vide, `PATH` sans `cave` ni
`singularity`) : `env-check OK (profil cloud) : 8 vérifications, dont 2 absences
attendues` (`cave`, `salome` ; le dossier partagé, présent dans la VM, est vu OK),
`mcp-check OK : 8 outils`, `pytest -m lent_aster` : 2 réussis en 17 s,
`pytest -m lent_salome` : 1 ignoré avec son motif, arbre Git du clone inchangé.

## 8. Non établi (à confirmer par l'essai Cloud)

- Si le script d'installation voit déjà le clone du dépôt (la documentation ne le
  dit pas) : il le cherche (`CLAUDE_PROJECT_DIR`, répertoire courant, `/home`,
  `/root`, `/workspace`…) ; à défaut, l'ouverture de session fait index et
  catalogue (≈ 2 min de plus à chaque session).
- Sous quel utilisateur tourne la session (le script tourne en root) : le Python
  géré par `uv` est installé dans le `HOME` de root.
- Si `dockerd` tourne déjà pendant l'installation et à l'ouverture de session.
- La durée du tirage de l'image et donc de l'installation complète.
- `releases.astral.sh` effectivement joignable avec l'accès **Custom**.

## 9. Première tâche d'essai Cloud (à lancer par MM)

Sur claude.ai/code, environnement `aster-expert`, dépôt `aster-expert`, branche
`lot-41ter`, coller :

```text
Lot 41 ter — premier essai Cloud. Tout en français. Ne modifie aucun fichier, ne
commite rien, ne pousse rien : tu rapportes seulement.

1. Annonce ton profil (vm ou cloud), puis lance `.venv/bin/aster-expert env-check`
   et recopie sa sortie complète.
2. Lance `.venv/bin/pytest tests/unit -q -p no:cacheprovider` et recopie la
   dernière ligne (réussis, ignorés, en échec) ainsi que le détail de tout échec.
3. Lance `.venv/bin/pytest -m lent_aster -v -rs -p no:cacheprovider` et recopie la
   sortie. Dis explicitement si Code_Aster a réellement tourné (tests réussis, pas
   ignorés) et en combien de temps.
4. Lance `.venv/bin/aster-expert mcp-check` et recopie sa sortie. Dis aussi si les
   outils du serveur MCP `aster-expert` sont visibles dans ta session.
5. Recopie les lignes `ETAPE` et `===` de `/opt/aster-expert/installation.log`, et
   dis si l'installation a tourné pour cette session ou si l'instantané en cache a
   été réutilisé ; donne la durée totale d'installation.
6. Recopie la sortie de : `id`, `pwd`, `uname -a`, `nproc`, `free -g`, `df -h /`,
   `docker version --format '{{.Server.Version}}'`, `uv --version`,
   `git status --short`, `git branch --show-current`.

Si une commande échoue, recopie l'erreur telle quelle et passe à la suivante.
Termine par un compte rendu en français : ce qui fonctionne, ce qui ne fonctionne
pas, sans rien corriger.
```

## 9 bis. Deuxième tâche d'essai Cloud : base de connaissances (lot 42, à lancer par MM)

Le premier essai n'avait pas appelé d'outil MCP depuis la session elle-même : celui-ci
appelle **directement** `search_connaissances`, et vérifie que `aster-expert rex` se
comporte correctement sans les archives d'exécution, qui n'existent que dans la VM.

Sur claude.ai/code, environnement `aster-expert`, dépôt `aster-expert`, branche
`lot-42`, coller :

```text
Lot 42 — essai Cloud de la base de connaissances. Tout en français. Ne modifie
aucun fichier, ne commite rien, ne pousse rien : tu rapportes seulement.

1. Annonce ton profil, lu sur la première ligne de `.venv/bin/aster-expert
   env-check` (recopie la sortie complète).
2. Dis si l'outil MCP `search_connaissances` du serveur `aster-expert` est visible
   dans ta session. S'il l'est, appelle-le TOI-MÊME, directement (pas par un
   script ni par la ligne de commande), trois fois, et recopie pour chaque appel
   les champs `id`, `layer`, `status`, `entry_validation_level` et `summary` des
   résultats, ainsi que `total_by_layer` :
   a. `keyword="FACTOR_11"`, `layers=["diagnostics"]` ;
   b. `text="surface développée"` ;
   c. `layers=["precedents"]`, `limit=3`.
   S'il n'est pas visible, dis-le et passe à l'étape 3 sans le remplacer par autre
   chose.
3. Lance `.venv/bin/aster-expert rex quai_cw_test_01` et recopie sa sortie et son
   code de sortie (`echo $?`). Attendu en profil cloud : la commande dit que les
   archives d'exécution sont absentes et sort en 0, sans échouer. Puis lance
   `git status --short` et dis si un fichier a été modifié.
4. Lance `.venv/bin/aster-expert connaissances verifier` et recopie sa sortie
   (les exécutions archivées y sont déclarées non vérifiables, pas en écart).
5. Lance `.venv/bin/pytest tests/unit/test_connaissances.py
   projets/quai_cw_test_01/tests/test_capitalisation_lot42.py -q -rs -p
   no:cacheprovider` et recopie la sortie (un test est ignoré faute d'archives, avec
   son motif).

Si une commande échoue, recopie l'erreur telle quelle et passe à la suivante.
Termine par un compte rendu en français : ce qui fonctionne, ce qui ne fonctionne
pas, sans rien corriger.
```

## 10. Annexe : script d'installation (texte à coller)

Contenu exact de `scripts/cloud_setup.sh` (un test vérifie que ce bloc lui est
identique) :

```bash
#!/bin/bash
# Les fonctions appelées au travers de `etape` sont invisibles pour shellcheck.
# shellcheck disable=SC2329
# AsterExpert -- préparation d'une session Claude Code dans le Cloud (lot 41 ter).
#
# Ce fichier est à la fois :
#   1. le « script d'installation » de l'environnement Cloud (texte copié tel quel
#      dans la configuration de l'environnement, voir docs/cloud.md) : sans
#      argument ; s'exécute en root avant le lancement de Claude Code ; son
#      résultat est mis en cache (instantané du disque) s'il dure moins de cinq
#      minutes environ ;
#   2. le crochet d'ouverture de session (`--session`, déclaré dans
#      .claude/settings.json) : ne fait rien hors du Cloud (CLAUDE_CODE_REMOTE
#      différent de « true ») ; relie au dépôt ce que l'installation a préparé ;
#   3. l'étape à la demande (`--image`) : tire l'image Code_Aster par son digest
#      puis extrait le catalogue, si l'installation ne l'a pas fait.
#
# Tout ce qui est long (Python, image Docker, corpus, index, catalogue) est rangé
# HORS du dépôt, dans $ASTER_CLOUD_CACHE (par défaut /opt/aster-expert) : une
# session repart d'un clone neuf du dépôt, l'instantané garde le reste du disque.
# Le dépôt n'en reçoit que des liens symboliques, tous ignorés par Git.
#
# Les constantes ci-dessous recopient config/sources.yaml, config/versions.yaml et
# .python-version : tests/unit/test_cloud_setup.py échoue si elles divergent.
# Le script ne s'arrête jamais en erreur (une installation en échec empêcherait la
# session de démarrer) : chaque étape écrit OK ou ECHEC et sa durée dans
# $ASTER_CLOUD_CACHE/installation.log, et `aster-expert env-check` signale ensuite
# ce qui manque.

set -u -o pipefail

UV_VERSION="0.12.21"
PYTHON_VERSION="3.12"
SRC_URL="https://gitlab.com/codeaster/src.git"
SRC_REF="17.4.0"
SRC_COMMIT="50ebc13c70ee9df62faf93ddcb746a3757b3042a"
DOC_URL="https://gitlab.com/codeaster/doc/docaster.git"
DOC_REF="17.4.0"
DOC_COMMIT="9c8c179f57ef7ca1d2891cac275ee4823a57967c"
IMAGE_REPOSITORY="simvia/code_aster"
IMAGE_TAG="17.4.0"
IMAGE_DIGEST="sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"

CACHE="${ASTER_CLOUD_CACHE:-/opt/aster-expert}"
JOURNAL="$CACHE/installation.log"

# Produits du corpus et du catalogue, rangés dans le cache et reliés au dépôt.
DONNEES=(
    data/raw/manifest.json
    data/raw/inventory.jsonl
    data/processed/xref_graph.json
    data/processed/command_document_map.json
    data/processed/fragments_by_file.jsonl
    data/processed/fragments_by_subsection.jsonl
    data/processed/catalogue
    data/indexes/bm25_by_file
    data/indexes/bm25_by_file_e1
    data/indexes/bm25_by_subsection
)

journal() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$JOURNAL" >&2
}

# etape <nom> <commande...> : exécute, chronomètre, journalise ; jamais fatal.
etape() {
    local nom="$1"
    shift
    local debut fin code
    debut=$(date +%s.%N)
    "$@" >>"$JOURNAL" 2>&1
    code=$?
    fin=$(date +%s.%N)
    local duree
    duree=$(awk -v a="$debut" -v b="$fin" 'BEGIN { printf "%.1f", b - a }')
    if [ "$code" -eq 0 ]; then
        journal "ETAPE $nom OK ${duree} s"
    else
        journal "ETAPE $nom ECHEC (code $code) ${duree} s"
    fi
    return "$code"
}

trouver_depot() {
    local candidat
    for candidat in "${ASTER_EXPERT_ROOT:-}" "${CLAUDE_PROJECT_DIR:-}" \
        "$(git rev-parse --show-toplevel 2>/dev/null)" \
        "$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"; do
        if [ -n "$candidat" ] && grep -qs '^name = "aster-expert"' "$candidat/pyproject.toml"; then
            (cd "$candidat" && pwd)
            return 0
        fi
    done
    local trouve
    while IFS= read -r trouve; do
        if grep -qs '^name = "aster-expert"' "$trouve"; then
            dirname "$trouve"
            return 0
        fi
    done < <(find /home /root /workspace /code /src -maxdepth 4 \
        -name pyproject.toml 2>/dev/null)
    return 1
}

installer_uv() {
    if command -v uv >/dev/null && [ "$(uv --version | cut -d' ' -f2)" = "$UV_VERSION" ]; then
        return 0
    fi
    # PyPI est dans la liste « Trusted » ; astral.sh n'y est pas.
    python3 -m venv "$CACHE/outils/uv" &&
        "$CACHE/outils/uv/bin/pip" install --quiet "uv==$UV_VERSION" || return 1
    if [ -w /usr/local/bin ]; then
        ln -sfn "$CACHE/outils/uv/bin/uv" /usr/local/bin/uv
    fi
    export PATH="$CACHE/outils/uv/bin:$PATH"
    [ "$(uv --version | cut -d' ' -f2)" = "$UV_VERSION" ]
}

installer_python() {
    # Python géré par uv, jamais celui du système (CLAUDE.md, lot 41 bis) ;
    # téléchargé depuis releases.astral.sh : domaine à autoriser (docs/cloud.md).
    uv python install "$PYTHON_VERSION"
}

demarrer_docker() {
    docker info >/dev/null 2>&1 && return 0
    [ "$(id -u)" -eq 0 ] || return 1
    command -v dockerd >/dev/null || return 1
    nohup dockerd >/var/log/dockerd.log 2>&1 &
    local _
    for _ in $(seq 1 60); do
        docker info >/dev/null 2>&1 && return 0
        sleep 1
    done
    return 1
}

tirer_image() {
    demarrer_docker || return 1
    local reference="$IMAGE_REPOSITORY@$IMAGE_DIGEST"
    docker image inspect "$reference" >/dev/null 2>&1 || docker pull "$reference" || return 1
    # Étiquette locale du même digest (comme `cave` dans la VM) ; jamais `stable`.
    docker tag "$reference" "$IMAGE_REPOSITORY:$IMAGE_TAG"
}

cloner() {
    # cloner <url> <ref> <commit> <destination> : même clone que `sources sync`
    # (partiel, une seule référence), puis contrôle du commit figé.
    local url="$1" ref="$2" commit="$3" destination="$4"
    if [ ! -d "$destination/.git" ]; then
        rm -rf "$destination"
        git clone --quiet --filter=blob:none --branch "$ref" --single-branch \
            "$url" "$destination" || return 1
    fi
    local obtenu
    obtenu=$(git -C "$destination" rev-parse 'HEAD^{commit}') || return 1
    if [ "$obtenu" != "$commit" ]; then
        echo "commit $obtenu au lieu de $commit (référence $ref de $url)"
        return 1
    fi
}

cloner_corpus() {
    mkdir -p "$CACHE/external"
    cloner "$SRC_URL" "$SRC_REF" "$SRC_COMMIT" "$CACHE/external/codeaster-src" || return 1
    cloner "$DOC_URL" "$DOC_REF" "$DOC_COMMIT" "$CACHE/external/codeaster-doc"
}

# relier <chemin relatif> : le chemin du dépôt devient un lien vers le cache.
relier() {
    local relatif="$1"
    [ -e "$CACHE/donnees/$relatif" ] || return 0
    if [ -L "$DEPOT/$relatif" ] || [ ! -e "$DEPOT/$relatif" ]; then
        mkdir -p "$(dirname "$DEPOT/$relatif")"
        ln -sfn "$CACHE/donnees/$relatif" "$DEPOT/$relatif"
    fi
}

# ranger <chemin relatif> : un produit écrit dans le dépôt passe dans le cache.
ranger() {
    local relatif="$1"
    if [ -e "$DEPOT/$relatif" ] && [ ! -L "$DEPOT/$relatif" ]; then
        rm -rf "$CACHE/donnees/$relatif"
        mkdir -p "$(dirname "$CACHE/donnees/$relatif")"
        mv "$DEPOT/$relatif" "$CACHE/donnees/$relatif"
    fi
    relier "$relatif"
}

relier_tout() {
    local nom relatif
    for nom in codeaster-src codeaster-doc; do
        if [ -d "$CACHE/external/$nom" ] && [ ! -e "$DEPOT/external/$nom" ]; then
            ln -sfn "$CACHE/external/$nom" "$DEPOT/external/$nom"
        fi
    done
    for relatif in "${DONNEES[@]}"; do
        relier "$relatif"
    done
    mkdir -p "$DEPOT/data/processed/workroot"
}

aster() {
    (cd "$DEPOT" && ASTER_IMAGE_REF="$IMAGE_DIGEST" \
        ASTER_CONTAINER_WORKROOT="$DEPOT/data/processed/workroot" \
        .venv/bin/aster-expert "$@")
}

construire_corpus() {
    aster sources sync &&
        aster sources inventory &&
        aster sources xref
}

# La table commande -> document, les fragments et l'index enrichi lisent le
# catalogue : ils viennent après son extraction, donc après l'image.
construire_index() {
    aster sources command-map &&
        aster fragments build --granularity both &&
        aster index build --granularity both &&
        aster index build --granularity by_file --enrich-text
}

extraire_catalogue() {
    aster catalogue extract || return 1
    # `catalogue extract` réécrit la section `detected` de config/versions.yaml
    # (date, version de Docker, origine du pin) : on garde la version du dépôt
    # dès lors que le digest est le même, pour ne laisser aucun fichier modifié.
    if ! git -C "$DEPOT" diff --quiet -- config/versions.yaml; then
        if grep -q "image_digest: $IMAGE_DIGEST" "$DEPOT/config/versions.yaml"; then
            git -C "$DEPOT" checkout -- config/versions.yaml
        else
            echo "config/versions.yaml : digest d'image différent, fichier laissé modifié"
            return 1
        fi
    fi
}

ranger_tout() {
    local relatif
    for relatif in "${DONNEES[@]}"; do
        ranger "$relatif"
    done
}

# Première moitié : .venv, crochet Git, liens, corpus (sans catalogue).
preparer_depot() {
    etape uv_sync bash -c "cd '$DEPOT' && uv sync --locked --all-extras --quiet" || return 1
    git -C "$DEPOT" config core.hooksPath scripts/git-hooks
    relier_tout
    if [ ! -e "$CACHE/donnees/data/processed/xref_graph.json" ]; then
        etape corpus construire_corpus
        ranger_tout
    fi
}

# Seconde moitié, image présente : catalogue, puis table, fragments et index.
preparer_catalogue_et_index() {
    if [ ! -d "$CACHE/donnees/data/processed/catalogue/$IMAGE_DIGEST" ]; then
        etape catalogue extraire_catalogue || return 1
        ranger data/processed/catalogue
    fi
    if [ ! -e "$CACHE/donnees/data/indexes/bm25_by_subsection" ]; then
        etape index construire_index || return 1
        ranger_tout
    fi
}

ecrire_variables_session() {
    [ -n "${CLAUDE_ENV_FILE:-}" ] || return 0
    {
        echo "export ASTER_IMAGE_REF=$IMAGE_DIGEST"
        echo "export ASTER_CONTAINER_WORKROOT=$DEPOT/data/processed/workroot"
        if [ -x "$CACHE/outils/uv/bin/uv" ]; then
            echo "export PATH=\"$CACHE/outils/uv/bin:\$PATH\""
        fi
    } >>"$CLAUDE_ENV_FILE"
}

mode_installation() {
    mkdir -p "$CACHE"
    local debut
    debut=$(date +%s)
    journal "=== installation (cache $CACHE)"
    etape uv installer_uv
    etape python installer_python
    etape image tirer_image &
    local image=$!
    etape corpus_clone cloner_corpus
    if DEPOT=$(trouver_depot); then
        journal "dépôt trouvé : $DEPOT"
        preparer_depot
        wait "$image"
        preparer_catalogue_et_index
    else
        journal "dépôt non trouvé : index et catalogue faits à l'ouverture de session"
        wait "$image"
    fi
    journal "=== installation terminée en $(($(date +%s) - debut)) s"
}

mode_session() {
    [ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || return 0
    mkdir -p "$CACHE"
    DEPOT=$(trouver_depot) || {
        journal "session : dépôt introuvable"
        return 0
    }
    journal "=== session ($DEPOT)"
    [ -x "$CACHE/outils/uv/bin/uv" ] && export PATH="$CACHE/outils/uv/bin:$PATH"
    etape docker demarrer_docker
    [ -d "$CACHE/external/codeaster-doc" ] || etape corpus_clone cloner_corpus
    preparer_depot
    if docker image inspect "$IMAGE_REPOSITORY@$IMAGE_DIGEST" >/dev/null 2>&1; then
        preparer_catalogue_et_index
    else
        journal "image Code_Aster absente : catalogue et index attendent" \
            "\`bash scripts/cloud_setup.sh --image\`"
    fi
    ecrire_variables_session
    journal "=== session prête"
}

mode_image() {
    mkdir -p "$CACHE"
    DEPOT=$(trouver_depot) || {
        journal "dépôt introuvable"
        return 1
    }
    etape image tirer_image || return 1
    preparer_catalogue_et_index
}

# Installation et session sortent toujours en 0 (une erreur bloquerait la
# session) ; l'étape à la demande rend son vrai code.
case "${1:-}" in
"") mode_installation ;;
--session) mode_session ;;
--image)
    mode_image
    exit $?
    ;;
*)
    echo "usage : cloud_setup.sh [--session | --image]" >&2
    exit 2
    ;;
esac
exit 0
```

## 11. Termes confidentiels et vérification avant envoi (lot 48 bis)

### 11.1 La liste des termes

Un projet construit sur des données réelles (site, client, entreprise, références de
dossier) déclare `confidential_data: true` dans son `projet.yaml` (aujourd'hui :
`estacade_pieux_01`). Pour un tel projet, le contrôle de publication
(`python -m aster_expert.publication`) **échoue** quand il ne connaît aucun terme
interdit : `--arbre` (intégration continue, `pytest` ne le fait pas) toujours,
`--index` (crochet `pre-commit`) quand un fichier d'un tel projet est indexé. Avant le
lot 48 bis, l'absence du fichier local `config/termes_interdits.local.txt`, qui
n'existe que dans la VM, faisait passer le contrôle sans rien chercher (audit,
`docs/audit/audit_lot48.md`, § 5).

La liste vient de la variable d'environnement `ASTER_EXPERT_TERMES_INTERDITS` : un
terme par ligne (ou séparés par `;`), les lignes vides et les lignes commençant par `#`
sont ignorées, la comparaison se fait sans casse ni accents. Elle s'ajoute aux termes du
fichier local de la VM. Elle n'est **jamais** versionnée, ni écrite dans un journal ou
un message de commit (le contrôle ne cite que le rang du terme trouvé).

### 11.2 Ce que MM crée (sans écrire les termes ici)

1. **Intégration continue (GitHub Actions)** : dépôt GitHub → Settings → Secrets and
   variables → Actions → *New repository secret* ; nom `ASTER_EXPERT_TERMES_INTERDITS` ;
   valeur : les termes, un par ligne. Le workflow `ci.yml` le passe à l'étape « Contrôle
   de publication ». Sans le secret, cette étape échoue, donc la branche n'est pas
   fusionnable.
2. **Session Cloud** : environnement `aster-expert` → *Environment variables* → ajouter
   `ASTER_EXPERT_TERMES_INTERDITS=<termes séparés par ;>`. Limite constatée dans la
   documentation de l'environnement : une variable d'environnement est lisible par
   toute personne qui peut utiliser l'environnement (§ 5, point 3). La liste ne
   contient que des noms, pas des identifiants de connexion : l'exposition est
   acceptable tant que l'environnement n'est utilisé que par MM ; s'il est partagé,
   ne pas poser la variable et lancer le contrôle de publication dans la VM ou en
   intégration continue seulement.
3. **VM** : inchangé (`config/termes_interdits.local.txt`, ignoré par Git).

Vérification : `ASTER_EXPERT_TERMES_INTERDITS` absente, `python -m
aster_expert.publication --arbre` répond « projet à données confidentielles sans liste
de termes interdits » et le code 1 ; présente, il répond 0 si aucun terme n'apparaît
dans les fichiers versionnés.

### 11.3 Intégration continue : déclencheurs et coût

- `ci.yml` : pull request, envoi sur `main`, `lot-*` et `claude/**`.
- `ci-lent.yml` : à la demande, et automatiquement quand un envoi touche
  `src/aster_expert/execution/`, `validation/`, `connaissances/` ou le répertoire
  `connaissances/` (données de la base). Il lance `pytest -m lent_aster` puis le rejeu des références
  (`aster-expert connaissances rejouer-references`, code non nul si une référence est à
  réexaminer ou non rejouable). Durées et minutes facturées : `docs/essais_lot48bis.md`, § 2.

### 11.4 Vérification locale avant envoi

`scripts/git-hooks/pre-push` lance `ruff format --check`, `ruff check` puis `pytest`
(hors tests lents) et refuse l'envoi au premier échec. Il est activé avec les autres
crochets (`git config core.hooksPath scripts/git-hooks`, fait par
`scripts/cloud_setup.sh`). Ne jamais le contourner (`--no-verify`).
