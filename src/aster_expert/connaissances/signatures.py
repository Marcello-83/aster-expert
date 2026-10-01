"""Error signatures of a run and the diagnostics that match them (lot 42,
étape 3.3).

A run's messages come either from `run_aster.error_messages` (compte rendu of
lot 41, `ExecutionMessage`) or, for the runs archived before lot 41, from the
listing itself (`listing_messages`). `primary_signature` names the failure in one
line: the first `<F>`/`<S>`/`<E>`/`<EXCEPTION>` identifier other than
`CATAMESS_3` (« l'alarme X est aggravée en erreur », which only announces the
next message), else the abnormal stop or the Python error of the listing.

`match_diagnostics` returns every diagnostic whose signature matches: one of its
identifiers is among the run's identifiers and, when the signature has a
pattern, the pattern is found in the text of those messages (for an abnormal
stop or a Python error, in the listing).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from aster_expert.connaissances.base import KnowledgeBase
from aster_expert.connaissances.modeles import Diagnostic

_MESSAGE = re.compile(r"<(F|E|S|A|EXCEPTION)>\s*<([A-Z][A-Z0-9_]*)>")
_DIAG_JOB = re.compile(r"DIAGNOSTIC JOB\s*:\s*(\S+)")
_PY_ERROR = re.compile(r"^(\w+(?:Error|Exception)): (.*)$", re.MULTILINE)
_FRAME = re.compile(r"[║╔╗╚╝═]+")
ANNOUNCER = "CATAMESS_3"
OK_DIAGNOSTICS = ("OK", "<A>_ALARM")


class RunMessage(BaseModel):
    """One message of a run: kind (`<F>`…), identifier, cleaned text."""

    model_config = ConfigDict(frozen=True)

    kind: str
    identifier: str | None
    text: str


class DiagnosticMatch(BaseModel):
    """A diagnostic of the base matching a failed run."""

    model_config = ConfigDict(frozen=True)

    diagnostic_id: str
    title: str
    status: str
    signature: str
    correction: str
    file: str


def listing_messages(text: str, *, context: int = 600) -> list[RunMessage]:
    """Messages of a listing (`.mess`, `fort.6`), each with the text that follows
    its identifier (frames of the message boxes removed)."""
    out = []
    for m in _MESSAGE.finditer(text):
        tail = _FRAME.sub(" ", text[m.end() : m.end() + context])
        out.append(
            RunMessage(
                kind=f"<{m.group(1)}>",
                identifier=m.group(2),
                text=" ".join(tail.split()),
            )
        )
    return out


def job_diagnostic(text: str) -> str | None:
    """`DIAGNOSTIC JOB` of a listing (`OK`, `<F>_ERROR`, `<S>_ERROR`,
    `<F>_ABNORMAL_ABORT`…), the last one written."""
    found = _DIAG_JOB.findall(text)
    return found[-1] if found else None


def python_error(text: str) -> str | None:
    found = _PY_ERROR.findall(text)
    return f"{found[-1][0]}: {found[-1][1].strip()}" if found else None


def primary_signature(
    messages: Iterable[RunMessage], diag: str | None, listing: str = ""
) -> str:
    """The failure in one line (see the module docstring)."""
    for m in messages:
        if m.kind != "<A>" and m.identifier and m.identifier != ANNOUNCER:
            return f"{m.kind} <{m.identifier}>"
    error = python_error(listing)
    if diag and "ABNORMAL_ABORT" in diag:
        if "Segmentation fault" in listing:
            return "arrêt anormal (Segmentation fault)"
        if error:
            return f"arrêt anormal ({error})"
        return "arrêt anormal"
    if error:
        return f"erreur Python ({error})"
    return diag or "(signature inconnue)"


def _matches(
    diagnostic: Diagnostic,
    messages: list[RunMessage],
    diag: str | None,
    listing: str,
) -> bool:
    sig = diagnostic.signature
    pattern = re.compile(sig.pattern, re.IGNORECASE) if sig.pattern else None
    if sig.kind == "environnement":
        return False
    if sig.kind in ("arrêt anormal", "erreur Python"):
        if sig.kind == "arrêt anormal" and not (diag and "ABNORMAL_ABORT" in diag):
            return False
        return pattern is not None and bool(pattern.search(listing))
    selected = [
        m
        for m in messages
        if m.identifier is not None and m.identifier in sig.identifiers
    ]
    if not selected:
        return False
    if pattern is None:
        return True
    return any(pattern.search(m.text) for m in selected) or bool(
        pattern.search(listing)
    )


def match_diagnostics(
    base: KnowledgeBase,
    messages: Iterable[RunMessage],
    *,
    diag: str | None = None,
    listing: str = "",
) -> list[DiagnosticMatch]:
    msgs = list(messages)
    out = []
    for entry in base.entries.values():
        if isinstance(entry, Diagnostic) and _matches(entry, msgs, diag, listing):
            out.append(
                DiagnosticMatch(
                    diagnostic_id=entry.id,
                    title=entry.title,
                    status=entry.status,
                    signature=entry.signature.label(),
                    correction=entry.correction,
                    file=base.files[entry.id].as_posix(),
                )
            )
    return out


__all__ = [
    "ANNOUNCER",
    "OK_DIAGNOSTICS",
    "DiagnosticMatch",
    "RunMessage",
    "job_diagnostic",
    "listing_messages",
    "match_diagnostics",
    "primary_signature",
    "python_error",
]
