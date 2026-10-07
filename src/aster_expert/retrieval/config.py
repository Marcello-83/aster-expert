"""Typed access to `config/retrieval.yaml` (lot 7b, E2 : « enfin câblée »).

`config/retrieval.yaml` has declared `defaults.source_priority` since lot 1
without anything reading it (lot 7b instruction). This module is the first
reader: a `pydantic` model of the file (CLAUDE.md, « Modèles de données
validés pour tout objet sérialisé »), not just the one field this lot
consumes, so a future lot enabling `engines.vector` or `fusion` does not
have to invent a second loader.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class LexicalEngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    backend: str | None
    k1: float
    b: float


class VectorEngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    backend: str | None
    model: str | None
    dimension: int | None


class EnginesConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    lexical: LexicalEngineConfig
    vector: VectorEngineConfig


class FusionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    method: str | None


class RerankingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    backend: str | None


class DefaultsConfig(BaseModel):
    """`source_priority` : query profile -> families in priority order.

    A profile named here is never auto-detected from a query in this lot
    (lot 7b instruction E2: "N'invente pas de détection automatique du
    profil de requête") — every caller passes one explicitly.
    """

    model_config = ConfigDict(frozen=True)

    top_k: int
    source_priority: dict[str, tuple[str, ...]]


class FiltersConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: tuple[str, ...]


class OutputConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    show_scores: bool
    show_source_path: bool
    show_commit: bool
    max_excerpt_chars: int


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    engines: EnginesConfig
    fusion: FusionConfig
    reranking: RerankingConfig
    defaults: DefaultsConfig
    filters: FiltersConfig
    output: OutputConfig


def load_retrieval_config(path: Path) -> RetrievalConfig:
    if not path.is_file():
        message = f"config/retrieval.yaml introuvable : {path}"
        raise FileNotFoundError(message)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return RetrievalConfig.model_validate(data)
