"""Readable report of one execution, written next to it (lot 41, étape 5.1).

Until lot 40, `aster-expert run` left only the pickled `run_aster.status` of an
execution: the audit had to decode it. Every execution now writes, in its work
directory, `compte_rendu.json` and `compte_rendu.md`: the command, the
fingerprints of the files given to Code_Aster, the duration, the status and
diagnostic of `run_aster.status`, the alarms and `<F>` errors with their
identifier and message (`run_aster.error_messages`), and the files produced.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

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


def build_record(
    report: ExecutionReport, *, command: str, image: str, inputs_sha256: dict[str, str]
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
    return RunRecord(
        report=report,
        command=command,
        image=image,
        inputs_sha256=inputs_sha256,
        outputs=outputs,
        alarms_by_identifier=dict(sorted(alarms.items())),
        errors=errors,
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
        f"| Statut | {r.status} |",
        f"| Diagnostic (`run_aster.status`) | {r.diag or '—'} |",
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
    "load_record",
    "parse_message",
    "parse_messages",
    "render_markdown",
    "sha256_file",
    "write_record",
]
