"""Replay the trial cases of the findings established by execution (lot 41,
étape 4.4), for each change of Code_Aster version.

For every finding of the base whose sources include execution sources, each
versioned trial case is run again in the container (`aster-expert run`
machinery, same restrictions) and each recorded value is looked for in the new
listing, with the criterion the versioned listings are already held to: the
number `value_obtained` printed, within 1e-9 relative. A case whose bytes no
longer match `case_sha256`, or that cannot be run as versioned (a mesh read
without an `.export` next to the case), is reported as such, never skipped in
silence. The run of a finding "holds" when every one of its values is found in
a run that ends normally.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aster_expert.agent.hypotheses import ExecutionSource
from aster_expert.constats.base import base_dir, load_base
from aster_expert.execution.compte_rendu import sha256_file
from aster_expert.execution.models import ExecutionReport

_NUMBER = re.compile(r"[-+]?\d\.\d+E[-+]\d+")


class ReplayError(RuntimeError):
    """The replay cannot start (no base, no container)."""


def value_printed(text: str, value: float) -> bool:
    """The criterion of the versioned listings (`value_obtained` printed)."""
    printed = [abs(float(t)) for t in _NUMBER.findall(text)]
    return any(abs(p - abs(value)) <= 1e-9 * abs(value) for p in printed)


class SourceCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    quantity: str
    value_obtained: float
    found: bool


class CaseReplay(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_path: str
    outcome: str
    """`rejoué`, `cas modifié`, `non rejouable` or `échec d'exécution`."""
    reason: str | None = None
    status: str | None = None
    work_dir: str | None = None
    duration_s: float | None = None
    checks: tuple[SourceCheck, ...] = ()


class ConstatReplay(BaseModel):
    model_config = ConfigDict(frozen=True)

    constat_id: str
    summary: str
    cases: tuple[CaseReplay, ...]

    @property
    def holds(self) -> bool:
        return all(
            c.outcome == "rejoué" and all(s.found for s in c.checks) for c in self.cases
        )

    @property
    def verdict(self) -> str:
        """`tient` (every case replayed, every value found), `à réexaminer` (a
        value no longer printed, a run that fails, a case whose bytes changed) or
        `non rejouable` (some case could not be run as versioned: nothing is
        concluded about it)."""
        if any(
            c.outcome in ("échec d'exécution", "cas modifié")
            or (c.outcome == "rejoué" and not all(s.found for s in c.checks))
            for c in self.cases
        ):
            return "à réexaminer"
        if any(c.outcome == "non rejouable" for c in self.cases):
            return "non rejouable"
        return "tient"


class ReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    aster_version: str
    image_digest: str
    replayed_at: datetime
    constats: tuple[ConstatReplay, ...]

    @property
    def all_hold(self) -> bool:
        return all(c.holds for c in self.constats)

    @property
    def to_review(self) -> list[str]:
        return [c.constat_id for c in self.constats if c.verdict == "à réexaminer"]

    @property
    def not_replayable(self) -> list[str]:
        return [c.constat_id for c in self.constats if c.verdict == "non rejouable"]

    def lines(self) -> list[str]:
        out = []
        for c in self.constats:
            out.append(f"{c.constat_id} : {c.verdict}")
            for case in c.cases:
                found = sum(s.found for s in case.checks)
                detail = (
                    f"{found}/{len(case.checks)} valeurs retrouvées"
                    if case.outcome == "rejoué"
                    else case.reason or ""
                )
                out.append(f"  {case.case_path} : {case.outcome} ({detail})")
        n_hold = sum(c.verdict == "tient" for c in self.constats)
        n_none = sum(c.verdict == "non rejouable" for c in self.constats)
        out.append(
            f"{n_hold}/{len(self.constats)} constat(s) établi(s) par exécution "
            f"tiennent sous Code_Aster {self.aster_version} ; {n_none} non "
            f"rejouable(s) en l'état ; à réexaminer : "
            f"{', '.join(self.to_review) if self.to_review else 'aucun'}."
        )
        return out


Runner = Callable[[Path], ExecutionReport]


def _default_runner(
    repo_root: Path, origin: str = "rejeu_constats"
) -> tuple[Runner, str, str]:
    import os  # noqa: PLC0415

    from aster_expert.execution.config import load_execution_config  # noqa: PLC0415
    from aster_expert.execution.docker_client import (  # noqa: PLC0415
        find_docker_binary,
    )
    from aster_expert.execution.errors import (  # noqa: PLC0415
        EnvironmentDetectionError,
        ExecutionRunError,
    )
    from aster_expert.execution.execute import execute_comm_file  # noqa: PLC0415
    from aster_expert.validation.errors import ValidationRunError  # noqa: PLC0415
    from aster_expert.validation.validate import (  # noqa: PLC0415
        resolve_digest_for_version,
    )

    try:
        config = load_execution_config(repo_root / "config" / "validation.yaml")
        digest, version = resolve_digest_for_version(
            repo_root / "data" / "processed" / "catalogue",
            None,
            repo_root / "config" / "versions.yaml",
        )
        docker_bin = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
    except (EnvironmentDetectionError, ValidationRunError, OSError, ValueError) as exc:
        raise ReplayError(str(exc)) from exc

    from aster_expert.execution.compte_rendu import run_origin  # noqa: PLC0415

    def run(comm: Path) -> ExecutionReport:
        try:
            # Lot 44 : une exécution de rejeu est une vérification (rex).
            with run_origin(origin):
                return execute_comm_file(
                    comm,
                    project_root=repo_root,
                    config=config,
                    docker_bin=docker_bin,
                    image_repository=os.environ.get(
                        "ASTER_IMAGE_REPOSITORY", "simvia/code_aster"
                    ),
                    image_digest=digest,
                    aster_version=version,
                )
        except ExecutionRunError as exc:
            raise ReplayError(str(exc)) from exc

    return run, version, digest


def _replay_case(
    repo_root: Path,
    case_path: str,
    case_sha256: str,
    sources: list[ExecutionSource],
    run: Runner,
) -> CaseReplay:
    path = repo_root / case_path
    if not path.is_file():
        return CaseReplay(
            case_path=case_path, outcome="non rejouable", reason="cas absent"
        )
    if sha256_file(path) != case_sha256:
        return CaseReplay(
            case_path=case_path,
            outcome="cas modifié",
            reason="les octets du cas ne sont plus ceux de la source",
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    if "LIRE_MAILLAGE" in text and not path.with_name(f"{path.stem}.export").is_file():
        return CaseReplay(
            case_path=case_path,
            outcome="non rejouable",
            reason=(
                "maillage lu sans .export à côté du cas (maillage non versionné "
                "avec lui)"
            ),
        )
    try:
        report = run(path)
    except ReplayError as exc:
        return CaseReplay(case_path=case_path, outcome="non rejouable", reason=str(exc))
    if report.status not in ("completed_ok", "completed_with_alarms") or not (
        report.mess_path
    ):
        return CaseReplay(
            case_path=case_path,
            outcome="échec d'exécution",
            reason=f"{report.status} ({report.diag})",
            status=report.status,
            work_dir=report.work_dir,
            duration_s=report.duration_s,
        )
    mess = Path(report.mess_path).read_text(encoding="utf-8", errors="replace")
    checks = tuple(
        SourceCheck(
            quantity=s.quantity,
            value_obtained=s.value_obtained,
            found=value_printed(mess, s.value_obtained),
        )
        for s in sources
    )
    return CaseReplay(
        case_path=case_path,
        outcome="rejoué",
        status=report.status,
        work_dir=report.work_dir,
        duration_s=report.duration_s,
        checks=checks,
    )


def replay_base(
    repo_root: Path,
    *,
    only: tuple[str, ...] = (),
    output_dir: Path | None = None,
    runner: tuple[Runner, str, str] | None = None,
) -> ReplayResult:
    """Replay every finding established by execution (or those of `only`);
    write `rejeu.json` and `rejeu.md` in `output_dir`."""
    try:
        base = load_base(base_dir(repo_root))
    except ValueError as exc:
        raise ReplayError(str(exc)) from exc
    unknown = [c for c in only if c not in base]
    if unknown:
        message = f"constats inconnus : {unknown}"
        raise ReplayError(message)
    run, version, digest = runner or _default_runner(repo_root)
    replays = []
    for constat in base.values():
        if only and constat.constat_id not in only:
            continue
        sources = [s for s in constat.entry.sources if isinstance(s, ExecutionSource)]
        if not sources:
            continue
        by_case: dict[tuple[str, str], list[ExecutionSource]] = {}
        for s in sources:
            by_case.setdefault((s.case_path, s.case_sha256), []).append(s)
        cases = tuple(
            _replay_case(repo_root, path, sha, case_sources, run)
            for (path, sha), case_sources in by_case.items()
        )
        replays.append(
            ConstatReplay(
                constat_id=constat.constat_id, summary=constat.summary, cases=cases
            )
        )
    result = ReplayResult(
        aster_version=version,
        image_digest=digest,
        replayed_at=datetime.now(UTC),
        constats=tuple(replays),
    )
    out = output_dir or (
        repo_root
        / "data"
        / "processed"
        / "rejeu_constats"
        / f"{result.replayed_at:%Y%m%dT%H%M%S}"
    )
    out.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = json.loads(result.model_dump_json())
    for item, replay in zip(payload["constats"], result.constats, strict=True):
        item["verdict"] = replay.verdict
    payload["a_reexaminer"] = result.to_review
    (out / "rejeu.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "rejeu.md").write_text(
        "# Rejeu des constats établis par exécution\n\n"
        f"Code_Aster {version} (`{digest}`), {result.replayed_at.isoformat()}.\n\n"
        "Critère : chaque valeur obtenue enregistrée dans une source d'exécution est "
        "de nouveau imprimée dans le listing du cas rejoué, à 1e-9 près en relatif.\n\n"
        + "\n".join(
            f"- {line}" if not line.startswith("  ") else f"  - {line.strip()}"
            for line in result.lines()
        )
        + "\n",
        encoding="utf-8",
    )
    return result


__all__ = [
    "CaseReplay",
    "ConstatReplay",
    "ReplayError",
    "ReplayResult",
    "SourceCheck",
    "replay_base",
    "value_printed",
]
