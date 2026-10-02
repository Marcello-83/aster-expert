"""Métriques du lot 44 : développement et vérification, seuil des candidats patrons."""

from __future__ import annotations

import ast
import datetime as dt
from pathlib import Path

from aster_expert.connaissances.base import load_knowledge
from aster_expert.connaissances.modeles import CodeEvidence, Pattern
from aster_expert.connaissances.rex import (
    _UPPER,
    PATTERN_SIMILARITY_THRESHOLD,
    RunSummary,
    classify_runs,
)
from aster_expert.execution.compte_rendu import RUN_ORIGIN_ENV, run_origin

ROOT = Path(__file__).resolve().parents[2]


def _run(
    name: str, sha: str | None, failed: bool, origin: str | None = None
) -> RunSummary:
    return RunSummary(
        run=name,
        started=dt.datetime(2026, 10, 2),
        comm="c.comm",
        failed=failed,
        job=None,
        signature="<F> <X>" if failed else None,
        duration_s=None,
        duration_kind="inconnue",
        comm_sha256=sha,
        origin=origin,
    )


def test_a_replay_of_a_succeeded_comm_is_a_verification() -> None:
    runs = classify_runs(
        [
            _run("1", "a", failed=True),  # développement : échec
            _run("2", "a", failed=False),  # même .comm, réussite : encore développement
            _run("3", "a", failed=False),  # rejeu d'un .comm réussi : vérification
            _run("4", "b", failed=False, origin="rejeu_constats"),
            _run("5", None, failed=False),
        ]
    )
    assert [r.kind for r in runs] == [
        "développement",
        "développement",
        "vérification",
        "vérification",
        "développement",
    ]
    assert "même empreinte" in (runs[2].verification_reason or "")
    assert "rejeu_constats" in (runs[3].verification_reason or "")


def test_run_origin_marks_and_restores_the_environment(monkeypatch: object) -> None:
    import os  # noqa: PLC0415

    os.environ.pop(RUN_ORIGIN_ENV, None)
    with run_origin("test_lent"):
        assert os.environ[RUN_ORIGIN_ENV] == "test_lent"
    assert RUN_ORIGIN_ENV not in os.environ


def test_the_pattern_threshold_is_the_one_the_data_support() -> None:
    """Lot 44 : à partir du seuil, le patron le plus proche d'une implémentation
    citée par la base est le sien ; juste en dessous, ce n'est plus vrai."""
    base = load_knowledge(ROOT)
    vocabulary = {t for e in base.all_entries() for t in (*e.commands, *e.keywords)}
    patterns = [e for e in base.entries.values() if isinstance(e, Pattern)]

    def tokens(path: str, symbol: str) -> set[str]:
        text = (ROOT / path).read_text(encoding="utf-8")
        lines = text.splitlines()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef | ast.ClassDef) and node.name == symbol:
                body = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                return set(_UPPER.findall(body)) & vocabulary
        return set()

    def similarity(t: set[str], p: Pattern) -> float:
        union = t | set(p.commands) | set(p.keywords)
        return (
            len(t & (set(p.commands) | set(p.keywords))) / len(union) if union else 0.0
        )

    above, below_wrong = [], []
    for p in patterns:
        for ev in p.implementation:
            if not isinstance(ev, CodeEvidence) or not ev.path.endswith(".py"):
                continue
            t = tokens(ev.path, ev.symbol)
            own = similarity(t, p)
            best = max(patterns, key=lambda q: similarity(t, q))
            if own >= PATTERN_SIMILARITY_THRESHOLD:
                above.append(best.id == p.id)
            elif not t or best.id != p.id:
                below_wrong.append(p.id)
    assert above and all(above)
    assert below_wrong  # sous le seuil, l'attribution n'est pas fiable
