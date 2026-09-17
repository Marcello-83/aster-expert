"""E2 (lot 7b) : priorité des sources de `config/retrieval.yaml`, câblée.

`config/retrieval.yaml` déclare `defaults.source_priority` depuis le lot 1 ;
ce module en est le premier consommateur. Deux variantes, mesurées
séparément (consigne E2), jamais fusionnées en un seul mécanisme implicite :

- **filtre dur** (`hard_filter_search`) : restreint les fragments candidats
  aux familles du profil actif ; si le nombre de fragments obtenus reste
  inférieur à `k`, complète avec le reste du corpus (non filtré), jamais
  l'inverse — une question dont la seule réponse existante vit hors de la
  liste de priorité ne se retrouve jamais sans aucun résultat.
- **repondération douce** (`soft_reweight_search`) : chaque fragment candidat
  voit son score BM25 brut multiplié par un facteur qui ne dépend que de sa
  famille — `1.0` pour toute famille listée dans le profil actif,
  `out_of_priority_factor` sinon. Personne n'est exclu ; seul le classement
  change.

**Le profil de requête n'est jamais détecté automatiquement dans ce lot**
(consigne E2) : `priority_families` est toujours reçu en paramètre explicite
par l'appelant, jamais déduit du texte de la requête.

**Limite assumée de la repondération douce.** `soft_reweight_search`
ré-ordonne un bassin de candidats déjà classés par score BM25 brut
(`pool_size` fragments, jamais le corpus entier reclassé) : un fragment
hors bassin ne peut jamais remonter, même si son score repondéré aurait
dépassé celui d'un candidat du bassin. `pool_size` est choisi large
(200 par défaut, le plancher déjà appliqué par `aster_expert.indexing.
bm25_index.search` lui-même) précisément pour que cette limite reste sans
effet pratique aux profondeurs mesurées par ce lot (k <= 20 documents,
`aster_expert.retrieval.bench._FRAGMENT_SEARCH_K` = 150 fragments) — une
approximation documentée, jamais présentée comme un reclassement exact du
corpus entier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import bm25s
import yaml

from aster_expert.indexing.bm25_index import search
from aster_expert.indexing.models import SearchHit

SourcePriorityMode = Literal["hard", "soft"]

# Pénalité appliquée au score brut d'un fragment dont la famille n'apparaît
# pas dans le profil actif (lot 7b, E2b). Choisie, pas ajustée par
# recherche d'optimum sur le banc (CLAUDE.md interdit de "se régler sur le
# banc", instruction E3) : 0.3 réduit fortement le score d'une famille hors
# priorité sans l'annuler -- un fragment V ou D très fortement pertinent
# lexicalement (score brut nettement supérieur à ses concurrents U4/U7)
# peut donc encore remonter, ce qu'un filtre dur ne permettrait jamais.
DEFAULT_OUT_OF_PRIORITY_FACTOR = 0.3

# Bassin de candidats sur lequel la repondération douce ré-ordonne (voir
# docstring du module) -- identique au plancher déjà appliqué en interne par
# `aster_expert.indexing.bm25_index.search` (`max(k, 200)`), jamais un choix
# indépendant qui pourrait laisser croire à une garantie plus forte.
DEFAULT_SOFT_POOL_SIZE = 200


def load_source_priority(config_path: Path) -> dict[str, tuple[str, ...]]:
    """`defaults.source_priority` de `config/retrieval.yaml`, tel quel.

    Ne relit jamais `config/retrieval.yaml` au-delà de cette seule clé ici :
    `aster_expert.retrieval.config.load_retrieval_config` reste la lecture
    complète et validée du fichier ; cette fonction existe pour les
    appelants (CLI, banc) qui n'ont besoin que de cette correspondance sans
    valider le reste du schéma.
    """
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw = (data.get("defaults") or {}).get("source_priority") or {}
    return {profile: tuple(families) for profile, families in raw.items()}


def hard_filter_search(
    retriever: bm25s.BM25,
    corpus: list[dict[str, object]],
    query: str,
    *,
    k: int,
    priority_families: tuple[str, ...],
    version: str | None = None,
) -> list[SearchHit]:
    """E2a : fragments des familles prioritaires d'abord, repli sur le reste.

    Un second appel à `search` (non filtré) ne se produit que si le premier
    passage n'a pas atteint `k` résultats -- jamais systématiquement, pour
    ne jamais faire deux fois le travail quand le premier passage suffit
    déjà.
    """
    primary = search(
        retriever, corpus, query, k=k, version=version, family_in=priority_families
    )
    if len(primary) >= k:
        return primary

    fallback = search(retriever, corpus, query, k=k, version=version)
    seen = {hit.fragment_id for hit in primary}
    combined = list(primary)
    for hit in fallback:
        if hit.fragment_id in seen:
            continue
        combined.append(hit)
        if len(combined) >= k:
            break
    return combined


def soft_reweight_search(
    retriever: bm25s.BM25,
    corpus: list[dict[str, object]],
    query: str,
    *,
    k: int,
    priority_families: tuple[str, ...],
    version: str | None = None,
    pool_size: int = DEFAULT_SOFT_POOL_SIZE,
    out_of_priority_factor: float = DEFAULT_OUT_OF_PRIORITY_FACTOR,
) -> list[SearchHit]:
    """E2b : repondération du score brut par famille, sur un bassin large.

    `pool_size` doit être >= `k` (sans quoi la repondération ne pourrait
    jamais faire remonter un candidat par ailleurs classé au-delà de `k`
    par le score brut) -- vérifié explicitement plutôt que silencieusement
    tronqué.
    """
    if pool_size < k:
        message = f"pool_size ({pool_size}) doit être >= k ({k})"
        raise ValueError(message)

    pool = search(retriever, corpus, query, k=pool_size, version=version)
    priority_set = set(priority_families)
    reweighted = sorted(
        pool,
        key=lambda hit: (
            hit.score * (1.0 if hit.family in priority_set else out_of_priority_factor)
        ),
        reverse=True,
    )
    return reweighted[:k]
