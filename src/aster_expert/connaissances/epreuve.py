"""Proof of an entry of the base by a run that declares applying it (lot 46, step 5).

A declaration (`connaissances.declaration`) says which entries a run applies; it
proves nothing by itself. What proves, by type of entry:

- finding (`CA-nnn`): the replay of its test case under the current version
  (`aster-expert constats rejouer`), as before. Applying a workaround does not prove
  the behaviour: a declared finding is never proved here;
- pattern (`PAT-nnn`): applied in a **successful** run whose project level-D controls
  pass, on that run's own results (`controles_d.json`, whose `provenance` carries the
  fingerprints of the listing and of the `.comm` of the run);
- control (`CTL-nnn`): the control executed on a result of the project (it appears in
  `controles_d.json` of that run with its verdict) and passing. A control that failed
  on a real defect later corrected is proposed to the engineer, never proved by the
  machine (`corrected_defect`): the defect cannot be checked here;
- reference (`REF-nnn`): a successful replay of one of its versioned cases (the `.comm`
  of the run is that case, identical by fingerprint);
- precedent (`PRE-nnn`): never proved. It stays a precedent (CLAUDE.md, lot 42);
- diagnostic (`DIAG-nnn`): no proof rule by declaration.

No retroactive attribution: only a run that carries a declaration can prove anything.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from aster_expert.connaissances.base import KnowledgeBase, write_entry
from aster_expert.connaissances.declaration import AppliedEntry
from aster_expert.connaissances.modeles import (
    ExecutionEvidence,
    KnowledgeEntry,
    Reuse,
    ValidationReference,
)
from aster_expert.execution.compte_rendu import RunRecord, load_record, sha256_file

OK_STATUSES = ("completed_ok", "completed_with_alarms")
D_FILE = "controles_d.json"


class ProofVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_id: str
    layer: str
    proven: bool
    level: Literal["C", "D", "E"] | None
    reason: str


def _comm_sha(record: RunRecord) -> str | None:
    name = Path(record.report.comm_path).name
    return record.inputs_sha256.get(name)


def _d_file(repo_root: Path, project: str) -> Path:
    return repo_root / "projets" / project / "resultats" / "controles" / D_FILE


def _d_results(repo_root: Path, record: RunRecord) -> tuple[dict | None, str | None]:  # type: ignore[type-arg]
    """The project's level-D results when they belong to this run, else why not."""
    assert record.knowledge is not None
    path = _d_file(repo_root, record.knowledge.project)
    if not path.is_file():
        return None, f"aucun résultat de contrôle D ({path.relative_to(repo_root)})"
    data = json.loads(path.read_text(encoding="utf-8"))
    provenance = data.get("provenance") or {}
    mess = record.report.mess_path
    mess_sha = sha256_file(Path(mess)) if mess and Path(mess).is_file() else None
    if provenance.get("comm_sha256") != _comm_sha(record) or (
        mess_sha is None or provenance.get("mess_sha256") != mess_sha
    ):
        return None, (
            "les contrôles D du projet ne portent pas sur les résultats de cette "
            "exécution (empreintes du `.comm` ou du listing différentes)"
        )
    return data, None


def _reference_case_paths(ref: ValidationReference) -> list[str]:
    """Versioned cases of a reference: its own, refined ones and its sources' cases."""
    paths = [c.case_path for c in ref.cases]
    paths += [
        q.refined_case_path
        for c in ref.cases
        for q in c.quantities
        if q.refined_case_path
    ]
    paths += [
        src.case_path
        for src in ref.sources
        if isinstance(src, ExecutionEvidence) and src.case_path
    ]
    return list(dict.fromkeys(paths))


def _verdict(
    entry_id: str, layer: str, proven: bool, level: str | None, reason: str
) -> ProofVerdict:
    return ProofVerdict(
        entry_id=entry_id,
        layer=layer,
        proven=proven,
        level=level,  # type: ignore[arg-type]
        reason=reason,
    )


def evaluate_run(
    repo_root: Path, run_dir: Path, base: KnowledgeBase
) -> list[ProofVerdict]:
    """One verdict per declared entry; `[]` for a run without declaration."""
    record = load_record(run_dir)
    if record.knowledge is None:
        return []
    ok = record.report.status in OK_STATUSES
    d_results, d_problem = (
        _d_results(repo_root, record) if ok else (None, "exécution non réussie")
    )
    out = []
    for item in record.knowledge.applied:
        layer = base.layer_of(item.id)
        out.append(
            _evaluate_entry(
                repo_root, record, base, item, layer, ok, d_results, d_problem
            )
        )
    return out


def _evaluate_entry(
    repo_root: Path,
    record: RunRecord,
    base: KnowledgeBase,
    item: AppliedEntry,
    layer: str,
    ok: bool,
    d_results: dict | None,  # type: ignore[type-arg]
    d_problem: str | None,
) -> ProofVerdict:
    entry_id = item.id
    if layer == "constats_code_aster":
        return _verdict(
            entry_id,
            layer,
            False,
            None,
            "un constat s'éprouve par le rejeu de son cas d'essai sous la version "
            "courante (aster-expert constats rejouer) ; appliquer un contournement "
            "ne prouve pas le comportement",
        )
    if layer == "precedents":
        return _verdict(
            entry_id,
            layer,
            False,
            None,
            "un précédent n'est jamais promu par épreuve : il reste un précédent",
        )
    if layer == "diagnostics":
        return _verdict(
            entry_id, layer, False, None, "aucune règle d'épreuve par déclaration"
        )
    if not ok:
        return _verdict(
            entry_id,
            layer,
            False,
            None,
            f"exécution non réussie ({record.report.status})",
        )
    if layer == "references_validation":
        ref = base.entries[entry_id]
        assert isinstance(ref, ValidationReference)
        run_sha = _comm_sha(record)
        for case_path in _reference_case_paths(ref):
            path = repo_root / case_path
            if path.is_file() and run_sha is not None and sha256_file(path) == run_sha:
                return _verdict(
                    entry_id,
                    layer,
                    True,
                    "C",
                    f"rejeu réussi du cas versionné {case_path} (empreinte "
                    "identique) ; la comparaison des grandeurs reste celle de "
                    "`aster-expert connaissances rejouer-references`",
                )
        return _verdict(
            entry_id,
            layer,
            False,
            None,
            "le .comm de l'exécution n'est aucun des cas versionnés de la référence",
        )
    if layer == "patrons":
        if d_results is None:
            return _verdict(entry_id, layer, False, None, d_problem or "")
        if d_results.get("verdict") != "RÉUSSI":
            return _verdict(
                entry_id,
                layer,
                False,
                None,
                f"contrôles D du projet : {d_results.get('verdict')}",
            )
        return _verdict(
            entry_id,
            layer,
            True,
            "D",
            "appliqué dans une exécution réussie, contrôles D du projet réussis",
        )
    if layer == "controles":
        if d_results is None:
            return _verdict(entry_id, layer, False, None, d_problem or "")
        applied = (d_results.get("harness") or {}).get("controls") or {}
        outcome = applied.get(entry_id)
        if outcome is None:
            return _verdict(
                entry_id,
                layer,
                False,
                None,
                "le contrôle n'apparaît pas dans les résultats D de cette exécution "
                "(`harness.controls`)",
            )
        if outcome.get("verdict") == "RÉUSSI":
            return _verdict(
                entry_id,
                layer,
                True,
                "D",
                "contrôle exécuté sur le résultat du projet, RÉUSSI",
            )
        if item.corrected_defect:
            return _verdict(
                entry_id,
                layer,
                False,
                None,
                "échec sur un défaut déclaré réel et corrigé (« "
                f"{item.corrected_defect} ») : à proposer à MM, la machine ne vérifie "
                "pas le défaut",
            )
        return _verdict(
            entry_id,
            layer,
            False,
            None,
            f"contrôle en échec ({outcome.get('verdict')}) sans défaut corrigé déclaré",
        )
    return _verdict(entry_id, layer, False, None, "type d'entrée sans règle d'épreuve")


def record_proofs(
    repo_root: Path,
    run_dir: Path,
    verdicts: list[ProofVerdict],
    base: KnowledgeBase,
    *,
    today: dt.date | None = None,
) -> list[Path]:
    """Add a `Reuse` (never a promotion) to every entry proved by the run.

    Idempotent: a run already recorded on an entry is not recorded twice. The
    evidence names the versioned case when the `.comm` is one (replayable), else the
    archived run.
    """
    record = load_record(run_dir)
    assert record.knowledge is not None
    run_id = run_dir.name
    comm = Path(record.report.comm_path)
    try:
        relative = comm.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        relative = None
    versioned = relative is not None and "/resultats/" not in f"/{relative}"
    written = []
    for verdict in verdicts:
        if not verdict.proven or verdict.level is None:
            continue
        entry = base.entries[verdict.entry_id]
        marker = f"exécution {run_id}"
        if any(marker in r.note for r in entry.reuses):
            continue
        sha = _comm_sha(record)
        evidence = (
            ExecutionEvidence(
                case_path=relative,
                case_sha256=sha,
                outcome="réussite",
                level=verdict.level,
                note=f"{marker} : {verdict.reason}",
            )
            if versioned and relative is not None and sha is not None
            else ExecutionEvidence(
                run=run_id,
                outcome="réussite",
                level=verdict.level,
                note=f"{marker} : {verdict.reason}",
            )
        )
        reuse = Reuse(
            project=record.knowledge.project,
            date=today or dt.date.today(),
            evidence=evidence,
            note=f"{marker} (déclaration {record.knowledge.file}) : {verdict.reason}",
        )
        updated: KnowledgeEntry = entry.model_copy(
            update={"reuses": (*entry.reuses, reuse)}
        )
        written.append(write_entry(repo_root, updated))
    return written


__all__ = ["ProofVerdict", "evaluate_run", "record_proofs"]
