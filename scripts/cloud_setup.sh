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
