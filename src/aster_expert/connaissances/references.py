"""Replay of the validation references (lot 42, étape 5.5): one command,
`aster-expert connaissances rejouer-references`.

Each versioned case of each reference is run again in the container (machinery
of `aster-expert run`, as the replay of findings of lot 41), and each recorded
value is looked for in the new listing with the criterion of the versioned
listings (number printed, within 1e-9 relative). The reference criterion itself
(`exact` within its tolerance, or error decreasing with refinement) is the one
recorded in the entry, written before the run of origin and never changed: the
replay only checks that the values are still those.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aster_expert.connaissances.base import load_knowledge, sha256_path
from aster_expert.connaissances.modeles import (
    ExecutionEvidence,
    ReferenceCase,
    ReferenceQuantity,
    ValidationReference,
)
from aster_expert.constats.rejeu import ReplayError, Runner, _default_runner
from aster_expert.constats.rejeu import value_printed as _printed


class QuantityReplay(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value_obtained: float
    found: bool


class CaseOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_path: str
    outcome: str
    """`rejoué`, `cas modifié`, `non rejouable` or `échec d'exécution`."""
    reason: str | None = None
    work_dir: str | None = None
    duration_s: float | None = None
    quantities: tuple[QuantityReplay, ...] = ()

    @property
    def holds(self) -> bool:
        return self.outcome == "rejoué" and all(q.found for q in self.quantities)


class ReferenceReplay(BaseModel):
    model_config = ConfigDict(frozen=True)

    reference_id: str
    recorded_result: str
    cases: tuple[CaseOutcome, ...]

    @property
    def verdict(self) -> str:
        if all(c.holds for c in self.cases):
            return "tient"
        if any(c.outcome == "non rejouable" for c in self.cases) and not any(
            c.outcome in ("échec d'exécution", "cas modifié")
            or (c.outcome == "rejoué" and not c.holds)
            for c in self.cases
        ):
            return "non rejouable"
        return "à réexaminer"


class ReferencesReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    aster_version: str
    image_digest: str
    replayed_at: datetime
    references: tuple[ReferenceReplay, ...]

    def lines(self) -> list[str]:
        out = []
        for r in self.references:
            out.append(f"{r.reference_id} ({r.recorded_result}) : {r.verdict}")
            for c in r.cases:
                found = sum(q.found for q in c.quantities)
                detail = (
                    f"{found}/{len(c.quantities)} valeurs retrouvées"
                    if c.outcome == "rejoué"
                    else c.reason or ""
                )
                out.append(f"  {c.case_path} : {c.outcome} ({detail})")
        n = sum(r.verdict == "tient" for r in self.references)
        out.append(
            f"{n}/{len(self.references)} référence(s) de validation tiennent sous "
            f"Code_Aster {self.aster_version}."
        )
        return out


def _replay_case(repo_root: Path, case: ReferenceCase, run: Runner) -> CaseOutcome:
    path = repo_root / case.case_path
    if not path.is_file():
        return CaseOutcome(
            case_path=case.case_path, outcome="non rejouable", reason="cas absent"
        )
    if sha256_path(path) != case.case_sha256:
        return CaseOutcome(
            case_path=case.case_path,
            outcome="cas modifié",
            reason="les octets du cas ne sont plus ceux de la référence",
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    if "LIRE_MAILLAGE" in text and not path.with_name(f"{path.stem}.export").is_file():
        return CaseOutcome(
            case_path=case.case_path,
            outcome="non rejouable",
            reason="maillage lu sans .export à côté du cas",
        )
    try:
        report = run(path)
    except ReplayError as exc:
        return CaseOutcome(
            case_path=case.case_path, outcome="non rejouable", reason=str(exc)
        )
    if report.status not in ("completed_ok", "completed_with_alarms") or not (
        report.mess_path
    ):
        return CaseOutcome(
            case_path=case.case_path,
            outcome="échec d'exécution",
            reason=f"{report.status} ({report.diag})",
            work_dir=report.work_dir,
            duration_s=report.duration_s,
        )
    mess = Path(report.mess_path).read_text(encoding="utf-8", errors="replace")
    return CaseOutcome(
        case_path=case.case_path,
        outcome="rejoué",
        work_dir=report.work_dir,
        duration_s=report.duration_s,
        quantities=tuple(
            QuantityReplay(
                name=q.name,
                value_obtained=q.value_obtained,
                found=_printed(mess, q.value_obtained),
            )
            for q in case.quantities
        ),
    )


def _with_refined_cases(ref: ValidationReference) -> list[ReferenceCase]:
    """The cases of the reference, plus one pseudo-case per refined mesh (×2)
    holding the refined values, with the fingerprint its execution source
    records."""
    shas = {
        s.case_path: s.case_sha256
        for s in ref.sources
        if isinstance(s, ExecutionEvidence) and s.case_path and s.case_sha256
    }
    refined: dict[str, list[ReferenceQuantity]] = {}
    for case in ref.cases:
        for q in case.quantities:
            if q.refined_case_path is not None and q.refined_value is not None:
                refined.setdefault(q.refined_case_path, []).append(
                    q.model_copy(
                        update={
                            "name": f"{q.name} (raffiné)",
                            "value_obtained": q.refined_value,
                        }
                    )
                )
    extra = [
        ReferenceCase.model_construct(
            case_path=path, case_sha256=shas.get(path, ""), quantities=tuple(qs)
        )
        for path, qs in refined.items()
    ]
    return [*ref.cases, *extra]


def replay_references(
    repo_root: Path,
    *,
    only: tuple[str, ...] = (),
    output_dir: Path | None = None,
    runner: tuple[Runner, str, str] | None = None,
) -> ReferencesReplayResult:
    base = load_knowledge(repo_root)
    refs = [e for e in base.entries.values() if isinstance(e, ValidationReference)]
    unknown = [i for i in only if i not in {r.id for r in refs}]
    if unknown:
        message = f"références inconnues : {unknown}"
        raise ReplayError(message)
    run, version, digest = runner or _default_runner(repo_root, "rejeu_references")
    replays = [
        ReferenceReplay(
            reference_id=ref.id,
            recorded_result=ref.result,
            cases=tuple(
                _replay_case(repo_root, c, run) for c in _with_refined_cases(ref)
            ),
        )
        for ref in refs
        if not only or ref.id in only
    ]
    result = ReferencesReplayResult(
        aster_version=version,
        image_digest=digest,
        replayed_at=datetime.now(UTC),
        references=tuple(replays),
    )
    out = output_dir or (
        repo_root
        / "data"
        / "processed"
        / "rejeu_references"
        / f"{result.replayed_at:%Y%m%dT%H%M%S}"
    )
    out.mkdir(parents=True, exist_ok=True)
    payload = json.loads(result.model_dump_json())
    for item, replay in zip(payload["references"], result.references, strict=True):
        item["verdict"] = replay.verdict
    (out / "rejeu.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "rejeu.md").write_text(
        "# Rejeu des références de validation\n\n"
        f"Code_Aster {version} (`{digest}`), {result.replayed_at.isoformat()}.\n\n"
        + "\n".join(f"- {line.strip()}" for line in result.lines())
        + "\n",
        encoding="utf-8",
    )
    return result


__all__ = [
    "CaseOutcome",
    "QuantityReplay",
    "ReferenceReplay",
    "ReferencesReplayResult",
    "replay_references",
]
