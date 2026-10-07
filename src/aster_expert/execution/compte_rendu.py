"""Readable report of one execution, written next to it (lot 41, étape 5.1).

Until lot 40, `aster-expert run` left only the pickled `run_aster.status` of an
execution: the audit had to decode it. Every execution now writes, in its work
directory, `compte_rendu.json` and `compte_rendu.md`: the command, the
fingerprints of the files given to Code_Aster, the duration, the status and
diagnostic of `run_aster.status`, the alarms and `<F>` errors with their
identifier and message (`run_aster.error_messages`), and the files produced.

Lot 42 (étape 3.3) : when the run fails, the diagnostics of the knowledge base
whose signature matches its messages (`connaissances/diagnostics/`) are written
in the compte rendu and shown by `aster-expert run`, before any other
hypothesis is made. An unreadable base is reported, never fatal to the run.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aster_expert.connaissances.declaration import AppliedKnowledge
from aster_expert.connaissances.signatures import (
    DiagnosticMatch,
    RunMessage,
    listing_messages,
    match_diagnostics,
)
from aster_expert.execution.models import (
    ExecutionMessage,
    ExecutionReport,
    MessageKind,
)

REPORT_JSON = "compte_rendu.json"
REPORT_MD = "compte_rendu.md"

_IDENTIFIER = re.compile(r"^<([A-Z0-9_]+)>$")
_KINDS: dict[str, MessageKind] = {
    "<A>": "<A>",
    "<F>": "<F>",
    "<E>": "<E>",
    "<S>": "<S>",
}


def parse_message(line: int, text: str) -> ExecutionMessage:
    """Kind and identifier are the first two words of the cleaned text."""
    words = text.split()
    kind: MessageKind = _KINDS.get(words[0] if words else "", "erreur Python")
    identifier = None
    if kind != "erreur Python" and len(words) > 1:
        match = _IDENTIFIER.match(words[1])
        identifier = match.group(1) if match else None
    return ExecutionMessage(
        kind=kind, identifier=identifier, line=line, text=" ".join(words)
    )


def parse_messages(raw: list[dict[str, Any]]) -> tuple[ExecutionMessage, ...]:
    return tuple(parse_message(int(m["line"]), str(m["text"])) for m in raw)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RunRecord(BaseModel):
    """What `compte_rendu.json` holds."""

    model_config = ConfigDict(frozen=True)

    report: ExecutionReport
    command: str
    """The command run inside the container."""
    image: str
    inputs_sha256: dict[str, str]
    """Files given to Code_Aster (staged in the work directory), by name."""
    outputs: dict[str, int]
    """Files produced, by path relative to the work directory, with their size."""
    alarms_by_identifier: dict[str, int]
    errors: tuple[ExecutionMessage, ...]
    """`<F>`, `<E>`, `<S>` messages and Python errors, in the order of the listing."""
    diagnostics: tuple[DiagnosticMatch, ...] = ()
    """Diagnostics of the knowledge base matching a failed run (lot 42)."""
    diagnostics_error: str | None = None
    """Why the knowledge base could not be searched, if it could not."""
    origin: str | None = None
    """Lot 44: what launched the run when it is a verification command
    (`rejeu_constats`, `rejeu_references`, `test_lent`), read from
    `ASTER_EXPERT_RUN_ORIGIN`; `None` for an ordinary run. `rex` counts such runs
    as verification, never as development."""
    knowledge: AppliedKnowledge | None = None
    """Lot 46: the knowledge the run declares applying (companion file
    `<stem>.connaissances.yaml`, copied here). Mandatory for a project's run; `None`
    for an older run or one outside any project that declared nothing."""
    resources: str | None = None
    """Lot 47 quater: the limits of the run (threads, MPI processes, time, memory,
    `docker run` limits) and where each came from; `None` for an older run."""


RUN_ORIGIN_ENV = "ASTER_EXPERT_RUN_ORIGIN"
RUN_ORIGINS = ("rejeu_constats", "rejeu_references", "test_lent")


@contextmanager
def run_origin(origin: str) -> Iterator[None]:
    """Mark every run launched inside the block with `origin` (lot 44)."""
    if origin not in RUN_ORIGINS:
        known = ", ".join(RUN_ORIGINS)
        known = ", ".join(RUN_ORIGINS)
        message = f"origine d'exécution inconnue : {origin!r} ({known})"
        raise ValueError(message)
    previous = os.environ.get(RUN_ORIGIN_ENV)
    os.environ[RUN_ORIGIN_ENV] = origin
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(RUN_ORIGIN_ENV, None)
        else:
            os.environ[RUN_ORIGIN_ENV] = previous


FAILED_STATUSES_OK = ("completed_ok", "completed_with_alarms")


def find_diagnostics(
    report: ExecutionReport, knowledge_root: Path
) -> tuple[tuple[DiagnosticMatch, ...], str | None]:
    """Diagnostics matching a failed run: messages of the compte rendu, completed
    by those of the listing (an abnormal stop has none of the former)."""
    from aster_expert.connaissances.base import (  # noqa: PLC0415
        KnowledgeBaseError,
        load_knowledge,
    )

    try:
        base = load_knowledge(knowledge_root)
    except (KnowledgeBaseError, OSError) as exc:
        return (), f"base de connaissances illisible : {exc}"
    listing = ""
    if report.mess_path and Path(report.mess_path).is_file():
        listing = Path(report.mess_path).read_text(encoding="utf-8", errors="replace")
    messages = [
        RunMessage(kind=m.kind, identifier=m.identifier, text=m.text)
        for m in report.messages
    ] + listing_messages(listing)
    return tuple(
        match_diagnostics(base, messages, diag=report.diag, listing=listing)
    ), None


def build_record(
    report: ExecutionReport,
    *,
    command: str,
    image: str,
    inputs_sha256: dict[str, str],
    knowledge_root: Path | None = None,
    knowledge: AppliedKnowledge | None = None,
    resources: str | None = None,
) -> RunRecord:
    work_dir = Path(report.work_dir)
    outputs = {
        name: (work_dir / name).stat().st_size
        for name in report.result_files
        if (work_dir / name).is_file()
    }
    alarms = Counter(
        m.identifier or "(sans identifiant)" for m in report.messages if m.kind == "<A>"
    )
    errors = tuple(m for m in report.messages if m.kind != "<A>")
    diagnostics: tuple[DiagnosticMatch, ...] = ()
    diagnostics_error = None
    if knowledge_root is not None and report.status not in FAILED_STATUSES_OK:
        diagnostics, diagnostics_error = find_diagnostics(report, knowledge_root)
    return RunRecord(
        report=report,
        command=command,
        image=image,
        inputs_sha256=inputs_sha256,
        outputs=outputs,
        alarms_by_identifier=dict(sorted(alarms.items())),
        errors=errors,
        diagnostics=diagnostics,
        diagnostics_error=diagnostics_error,
        origin=os.environ.get(RUN_ORIGIN_ENV) or None,
        knowledge=knowledge,
        resources=resources,
    )


def render_markdown(record: RunRecord) -> str:
    r = record.report
    lines = [
        f"# Compte rendu d'exécution — {Path(r.comm_path).name}",
        "",
        "Exécution Code_Aster encadrée (`aster-expert run`). Niveau atteint au mieux : "
        "C (exécution jusqu'à `FIN`) si le statut est `completed_ok` ou "
        "`completed_with_alarms` ; aucun contrôle physique n'est fait ici.",
        "",
        "| Élément | Valeur |",
        "| --- | --- |",
        f"| Fichier de commandes | `{r.comm_path}` |",
        f"| Code_Aster | {r.aster_version} |",
        f"| Image | `{record.image}` |",
        f"| Commande | `{record.command}` |",
        f"| Ressources | {record.resources or '—'} |",
        f"| Statut | {r.status} |",
        f"| Diagnostic (`run_aster.status`) | {r.diag or '—'} |",
        f"| Lecture du statut | {r.status_source or '—'} |",
        f"| Code de retour | {r.return_code if r.return_code is not None else '—'} |",
        "| Durée | "
        + (f"{r.duration_s:.1f} s" if r.duration_s is not None else "—")
        + " |",
        f"| Date | {r.executed_at.isoformat()} |",
        f"| Répertoire | `{r.work_dir}` |",
        f"| Listing | `{r.mess_path or '—'}` |",
        "",
        "## Fichiers donnés à Code_Aster",
        "",
        "| Fichier | SHA-256 |",
        "| --- | --- |",
    ]
    lines += [f"| `{n}` | `{s}` |" for n, s in record.inputs_sha256.items()]
    lines += ["", "## Messages (`run_aster.error_messages`)", ""]
    if r.messages_source is None:
        lines.append(
            "Messages non extraits"
            + (f" : {r.messages_error}" if r.messages_error else " (pas de listing).")
        )
    else:
        n_alarms = sum(record.alarms_by_identifier.values())
        lines.append(
            f"{n_alarms} alarme(s), {len(record.errors)} erreur(s)"
            + (
                f" ; {r.messages_truncated} message(s) au-delà du plafond non repris"
                if r.messages_truncated
                else ""
            )
            + "."
        )
        if record.alarms_by_identifier:
            lines += ["", "| Alarme | Occurrences |", "| --- | --- |"]
            lines += [
                f"| `{k}` | {v} |" for k, v in record.alarms_by_identifier.items()
            ]
        if record.errors:
            lines += [
                "",
                "| Genre | Identifiant | Ligne | Message |",
                "| --- | --- | --- | --- |",
            ]
            for m in record.errors:
                text = m.text.replace("|", "\\|")
                lines.append(
                    f"| {m.kind} | {m.identifier or '—'} | {m.line} | {text[:400]} |"
                )
    if r.status not in FAILED_STATUSES_OK:
        lines += ["", "## Diagnostics de la base de connaissances", ""]
        if record.diagnostics_error:
            lines.append(record.diagnostics_error)
        elif not record.diagnostics:
            lines.append(
                "Aucun diagnostic de `connaissances/diagnostics/` ne correspond : "
                "échec à classer au retour d'expérience (`aster-expert rex`)."
            )
        else:
            lines += [
                "Lire ces diagnostics avant toute autre hypothèse.",
                "",
                "| Diagnostic | Statut | Signature | Correction |",
                "| --- | --- | --- | --- |",
            ]
            for d in record.diagnostics:
                correction = d.correction.replace("|", "\\|")
                lines.append(
                    f"| `{d.diagnostic_id}` {d.title} | {d.status} | {d.signature} | "
                    f"{correction[:300]} |"
                )
    lines += ["", "## Connaissances appliquées (déclaration, lot 46)", ""]
    if record.knowledge is None:
        lines.append(
            "Aucune déclaration (exécution hors projet ou antérieure au lot 46)."
        )
    else:
        know = record.knowledge
        lines.append(f"Déclaration `{know.file}` (SHA-256 `{know.sha256[:16]}…`).")
        if know.applied:
            lines += ["", "| Entrée | Ce qui en est appliqué |", "| --- | --- |"]
            lines += [
                f"| `{e.id}` | {e.how.replace('|', chr(92) + '|')} |"
                for e in know.applied
            ]
        else:
            lines.append(f"Aucune entrée appliquée : {know.none_reason}")
    lines += [
        "",
        "## Fichiers produits",
        "",
        "| Fichier | Taille (octets) |",
        "| --- | --- |",
    ]
    lines += [f"| `{n}` | {s} |" for n, s in record.outputs.items()]
    return "\n".join(lines) + "\n"


def write_record(record: RunRecord) -> tuple[Path, Path]:
    work_dir = Path(record.report.work_dir)
    json_path = work_dir / REPORT_JSON
    md_path = work_dir / REPORT_MD
    json_path.write_text(
        json.dumps(json.loads(record.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(record), encoding="utf-8")
    return json_path, md_path


def load_record(work_dir: Path) -> RunRecord:
    return RunRecord.model_validate_json(
        (work_dir / REPORT_JSON).read_text(encoding="utf-8")
    )


__all__ = [
    "REPORT_JSON",
    "REPORT_MD",
    "RunRecord",
    "build_record",
    "find_diagnostics",
    "load_record",
    "parse_message",
    "parse_messages",
    "render_markdown",
    "sha256_file",
    "write_record",
]
