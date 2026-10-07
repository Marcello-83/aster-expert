"""Manifest of the execution archive `data/processed/runs/` (lot 46, step 4).

The archive is not versioned: it lives in the VM only. A Cloud session creates a
`runs/` directory by running a case, and that partial archive was taken for the
whole one (lot 45: `rex` overwrote the versioned metrics; three tests read a partial
`runs/`). Each project registry (`connaissances/rex/<projet>.yaml`, versioned) now
carries a manifest: the number of runs attributed to the project and the digest of
their sorted identifiers. An archive is *conformant* when the oldest `runs` runs it
holds for the project have that digest -- runs added since are newer, so they come
after the recorded ones. Absent, partial or foreign archives all fail the same
test, with the reason stated.

Written by `aster-expert rex <projet> --manifeste` (VM, complete archive), mirrored
in `data/processed/runs/manifeste.json` so that the archive describes itself.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

RUNS_RELATIVE = Path("data") / "processed" / "runs"
REX_RELATIVE = Path("connaissances") / "rex"
MIRROR_NAME = "manifeste.json"
_RUN_TIME = re.compile(r"^(\d{8}T\d{6})-")


class ArchiveManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    runs: int
    sha256: str
    recorded: dt.date


def digest(run_ids: list[str]) -> str:
    """Digest of the sorted run identifiers."""
    text = "\n".join(sorted(run_ids)) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_started(run_id: str) -> dt.datetime | None:
    match = _RUN_TIME.match(run_id)
    if match is None:
        return None
    return dt.datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")


def _relative_to_root(path_text: str, repo_root: Path) -> str | None:
    path = Path(path_text)
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        pass
    parts = path.parts
    for marker in ("projets", "data"):
        if marker in parts:
            return Path(*parts[parts.index(marker) :]).as_posix()
    return None


def attributed_runs(
    repo_root: Path, case_roots: tuple[str, ...], legacy_before: dt.datetime | None
) -> list[str]:
    """Identifiers of the archived runs attributed to a project, oldest first.

    A run with a `compte_rendu.json` belongs to the project whose case roots hold its
    `.comm`; an older run (no record) belongs to it when it predates `legacy_before`.
    """
    runs_dir = repo_root / RUNS_RELATIVE
    if not runs_dir.is_dir():
        return []
    roots = tuple(r.rstrip("/") + "/" for r in case_roots)
    found = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        started = run_started(run_dir.name)
        if started is None:
            continue
        record = run_dir / "compte_rendu.json"
        data = _record_data(record)
        if data is not None:
            comm = _relative_to_root(str(data["report"]["comm_path"]), repo_root)
            if comm is None or not comm.startswith(roots):
                continue
        elif legacy_before is None or started >= legacy_before.replace(tzinfo=None):
            # Lot 47 ter (ENV-003): a report left empty by a full disk; lot 47 quater
            # (DIAG-026): no report at all, the run having been stopped while hung. The
            # run is attributed by the SHA-256 of its .comm, found under the case roots.
            if not _comm_under_roots(run_dir, repo_root, case_roots):
                continue
        found.append(run_dir.name)
    return found


def _record_data(record: Path) -> dict[str, Any] | None:
    """The run report, or None when absent, empty or not JSON."""
    if not record.is_file():
        return None
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _comm_under_roots(
    run_dir: Path, repo_root: Path, case_roots: tuple[str, ...]
) -> bool:
    """True when a .comm of the run has the SHA-256 of a .comm under a case root."""
    wanted = {_sha256(p) for p in run_dir.glob("*.comm")}
    if not wanted:
        return False
    for root in case_roots:
        base = repo_root / root
        if base.is_dir() and any(_sha256(p) in wanted for p in base.rglob("*.comm")):
            return True
    return False


def build_manifest(
    run_ids: list[str], *, today: dt.date | None = None
) -> ArchiveManifest:
    return ArchiveManifest(
        runs=len(run_ids), sha256=digest(run_ids), recorded=today or dt.date.today()
    )


def conformity_problem(
    run_ids: list[str], manifest: ArchiveManifest | None
) -> str | None:
    """Why `run_ids` (a project's archived runs) do not match the manifest, or None."""
    if manifest is None:
        return (
            "aucun manifeste versionné dans le registre du projet (archive non "
            "vérifiable ; dans la VM : `aster-expert rex <projet> --manifeste`)"
        )
    if len(run_ids) < manifest.runs:
        return (
            f"archive partielle : {len(run_ids)} exécution(s) du projet pour "
            f"{manifest.runs} au manifeste"
        )
    if digest(run_ids[: manifest.runs]) != manifest.sha256:
        return (
            f"archive non conforme au manifeste : l'empreinte des {manifest.runs} "
            "plus anciennes exécutions diffère"
        )
    return None


def _registries(repo_root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((repo_root / REX_RELATIVE).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "project" in data:
            out.append(data)
    return out


def _legacy_before(data: dict[str, Any]) -> dt.datetime | None:
    legacy = data.get("legacy_runs")
    if not legacy:
        return None
    before = legacy["before"]
    return (
        before
        if isinstance(before, dt.datetime)
        else dt.datetime.fromisoformat(str(before))
    )


def project_problem(repo_root: Path, data: dict[str, Any]) -> str | None:
    """Conformity of the archive for one registry (as loaded from YAML)."""
    if not (repo_root / RUNS_RELATIVE).is_dir():
        return (
            "archives d'exécution absentes (data/processed/runs/ : Cloud ou clone neuf)"
        )
    ids = attributed_runs(
        repo_root, tuple(data.get("case_roots") or ()), _legacy_before(data)
    )
    manifest = (
        ArchiveManifest.model_validate(data["archive"]) if data.get("archive") else None
    )
    return conformity_problem(ids, manifest)


def archive_problem(repo_root: Path) -> str | None:
    """None when the archive is complete for every registered project, else why not."""
    reasons = []
    for data in _registries(repo_root):
        problem = project_problem(repo_root, data)
        if problem is not None:
            reasons.append(f"{data['project']} : {problem}")
    return "; ".join(reasons) if reasons else None


def write_mirror(repo_root: Path) -> Path:
    """`runs/manifeste.json`: the manifests of the registries, next to the runs."""
    runs_dir = repo_root / RUNS_RELATIVE
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        data["project"]: ArchiveManifest.model_validate(data["archive"]).model_dump(
            mode="json"
        )
        for data in _registries(repo_root)
        if data.get("archive")
    }
    path = runs_dir / MIRROR_NAME
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


__all__ = [
    "MIRROR_NAME",
    "RUNS_RELATIVE",
    "ArchiveManifest",
    "archive_problem",
    "attributed_runs",
    "build_manifest",
    "conformity_problem",
    "digest",
    "project_problem",
    "run_started",
    "write_mirror",
]
