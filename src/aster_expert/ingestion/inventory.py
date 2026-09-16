"""`aster-expert sources inventory` : inventaire du corpus `codeaster-doc`.

Lot 6 (docs/development-plan.md). Un document est une seule chose, décidée
par la structure réelle du dépôt synchronisé, jamais devinée : un répertoire
qui porte son propre `index.rst`. Vérifié sur le corpus 17.4.0 (compte rendu
du lot 6) : aucun `index.rst` n'est imbriqué sous un autre répertoire qui en
porte déjà un, et les répertoires `other_pages` (un par famille) ne sont
jamais des documents — ce sont des pages de navigation générées par le
gabarit Sphinx du dépôt, sans identifiant documentaire.

Ce module ne lit chaque fichier `.rst` qu'une fois (son texte est réutilisé
pour la détection de contenu vide et de fichier orphelin au sein d'un même
document), et ne construit jamais le contenu de tous les documents en
mémoire simultanément : seul le contenu textuel des fichiers d'**un**
document est retenu le temps de son traitement, jamais celui du corpus
entier (contrainte mémoire, docs/development-plan.md lot 6).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from aster_expert.ingestion.models import (
    DocumentAnomaly,
    DocumentEntry,
    InventoryResult,
)

_OTHER_PAGES_DIRNAME = "other_pages"
_CHUNK_SIZE = 1 << 20  # 1 MiB : un seul fichier ouvert à la fois.

_LABEL_RE = re.compile(r"^\.\.\s+_([^:\n]+):\s*$", re.MULTILINE)
_TITLE_RE = re.compile(r"^\*\*(.+?)\*\*[ \t]*(.*)$", re.MULTILINE)
_TOCTREE_DIRECTIVE_RE = re.compile(r"^\.\.\s+toctree::\s*$")

# docs/corpus.md §3 : familles attendues avant l'inventaire réel. Amendé au
# lot 6 (I2) pour couvrir `man_s`, découvert lors de la synchronisation
# (docs/development-plan.md, observation de clôture du lot 3) et non
# anticipé par cette table.
_SINGLE_LETTER_COARSE_FAMILIES = frozenset({"R", "V", "D"})
_TWO_LETTER_COARSE_FAMILIES = frozenset({"SU", "SV"})


@dataclass(frozen=True)
class ParsedIndex:
    """Result of reading one document's `index.rst` (small file, read whole)."""

    raw_label: str | None
    title: str | None
    toctree_entries: tuple[str, ...]


def _extract_title(text: str, raw_label: str | None) -> str | None:
    """Find the title line, preferring the one that carries the document's
    own label as its bold marker (`**<raw_label>** <title>`).

    A handful of older documents (8/2047 on the 17.4.0 corpus, e.g.
    `U4.01.02`) carry earlier bold preamble lines before the real title
    (`**Manuel d'Utilisation**`, `**Fascicule ...**`, `**Document: ...**`):
    the first `**...**` line found is not reliably the title. When
    `raw_label` is known, anchoring the search to it resolves this
    unambiguously; the generic "first bold line with trailing text" match
    is only a fallback for the rarer case where no label was found at all
    (`missing_label`, already anomalous on its own).
    """
    if raw_label is not None:
        anchored_re = re.compile(
            r"^\*\*" + re.escape(raw_label) + r"\*\*[ \t]*(.*)$",
            re.MULTILINE | re.IGNORECASE,
        )
        anchored_match = anchored_re.search(text)
        if anchored_match:
            return anchored_match.group(1).strip() or None

    fallback_match = _TITLE_RE.search(text)
    if fallback_match:
        return fallback_match.group(2).strip() or None
    return None


def parse_index_rst(text: str) -> ParsedIndex:
    """Extract the label, title and toctree entries of one `index.rst`.

    Never executes or renders the file: plain text scanning, the same
    posture as `aster_expert.parsing.comm_parser` for `.comm` files (never
    guess what a missing or malformed piece would have said).
    """
    label_match = _LABEL_RE.search(text)
    raw_label = label_match.group(1) if label_match else None

    title = _extract_title(text, raw_label)

    lines = text.splitlines()
    entries: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if _TOCTREE_DIRECTIVE_RE.match(lines[i]):
            i += 1
            while i < n:
                line = lines[i]
                stripped = line.strip()
                if stripped == "":
                    i += 1
                    continue
                if not line[:1].isspace():
                    break
                if stripped.startswith(":") or stripped == "self":
                    i += 1
                    continue
                entries.append(stripped)
                i += 1
            continue
        i += 1

    return ParsedIndex(raw_label=raw_label, title=title, toctree_entries=tuple(entries))


def discover_document_dirs(manuals_root: Path) -> list[Path]:
    """Every directory that owns its own `index.rst`, `other_pages` excluded."""
    return sorted(
        p.parent
        for p in manuals_root.rglob("index.rst")
        if _OTHER_PAGES_DIRNAME not in p.parts
    )


def derive_family(document_id: str) -> str | None:
    """Coarse family matching docs/corpus.md §3's granularity, or None.

    `U` is split by digit (`U0`..`U7`) because docs/corpus.md §3 already
    distinguishes those individually (contexte, démarche, formats,
    sémantique des mots-clés). `R`, `V`, `D` are not split: docs/corpus.md
    §3 gives them one row regardless of the sub-numbering visible in the
    identifier (`R7`, `V3`, `D0`, ...). `SU`/`SV` (man_s, amendment lot 6,
    I2) mirror that same single-row treatment.
    """
    token = document_id.split(".", 1)[0]
    if not token:
        return None
    letters = "".join(ch for ch in token if ch.isalpha())
    digits = token[len(letters) :]
    if letters == "U":
        return token if digits else None
    if letters in _SINGLE_LETTER_COARSE_FAMILIES:
        return letters
    if letters in _TWO_LETTER_COARSE_FAMILIES:
        return letters
    return None


def _is_effectively_empty(text: str) -> bool:
    """True when a file carries no content beyond blank lines and directives.

    Deliberately narrow: only blank lines and lines whose *stripped* form
    starts with the reST comment/directive marker `..` are discarded before
    checking what remains. Found on real corpus data (lot 6, I3/I6):
    `man_r/r3/r3.08.10/1.rst` and `man_r/r7/r7.02.15/1.rst`, two toctree
    children that are 3 bytes of blank lines each. Never applied to strip
    prose inside a directive body (e.g. `.. math::`): those lines do not
    start with `..` themselves, so they are kept and count as content.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith(".."):
            continue
        return False
    return True


def _hash_and_size(files: list[Path], doc_dir: Path) -> tuple[str, int]:
    """Stream every file once, one at a time, into a single running hash."""
    hasher = hashlib.sha256()
    total_size = 0
    for file_path in files:
        rel = file_path.relative_to(doc_dir).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        with file_path.open("rb") as handle:
            while chunk := handle.read(_CHUNK_SIZE):
                hasher.update(chunk)
                total_size += len(chunk)
        hasher.update(b"\0")
    return f"sha256:{hasher.hexdigest()}", total_size


def build_inventory(
    manuals_root: Path,
    *,
    repo_root: Path,
    source_name: str,
    source_commit: str,
    now: datetime | None = None,
) -> InventoryResult:
    """Build the full document inventory of one synchronized doc corpus.

    `source_commit` is the single revision the whole working copy is
    checked out at (docs/corpus.md §5, `data/raw/manifest.json`), never a
    per-file `git log` lookup: the corpus is a single pinned clone, and a
    per-document blame would mean one `git log` invocation per document
    (~2000 on the 17.4.0 corpus), which the memory/performance constraint of
    this batch (docs/development-plan.md, lot 6) rules out for no
    documented benefit — every document is already tied to the same
    revision by construction.
    """
    resolved_now = now if now is not None else datetime.now(UTC)
    doc_dirs = discover_document_dirs(manuals_root)

    documents: list[DocumentEntry] = []
    anomalies: list[DocumentAnomaly] = []
    seen_ids: dict[str, str] = {}

    for doc_dir in doc_dirs:
        index_path = doc_dir / "index.rst"
        relative_path = doc_dir.relative_to(repo_root).as_posix()
        directory_name = doc_dir.name
        text = index_path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_index_rst(text)

        if parsed.raw_label is None:
            anomalies.append(
                DocumentAnomaly(
                    kind="missing_label",
                    document_id=None,
                    relative_path=relative_path,
                    detail="aucune directive '.. _id:' trouvée dans index.rst",
                )
            )
            raw_label = directory_name
            normalized_id = directory_name.upper()
        else:
            raw_label = parsed.raw_label
            normalized_id = raw_label.upper()
            if raw_label.lower() != directory_name.lower():
                anomalies.append(
                    DocumentAnomaly(
                        kind="label_directory_mismatch",
                        document_id=normalized_id,
                        relative_path=relative_path,
                        detail=(
                            f"label '{raw_label}' distinct du nom de "
                            f"répertoire '{directory_name}'"
                        ),
                    )
                )

        if parsed.title is None:
            anomalies.append(
                DocumentAnomaly(
                    kind="missing_title",
                    document_id=normalized_id,
                    relative_path=relative_path,
                    detail=(
                        "aucune ligne de titre "
                        f"'**{raw_label}** <titre>' trouvée dans index.rst"
                    ),
                )
            )

        subfamily = normalized_id.split(".", 1)[0]
        family = derive_family(normalized_id)
        if family is None:
            anomalies.append(
                DocumentAnomaly(
                    kind="unknown_family_prefix",
                    document_id=normalized_id,
                    relative_path=relative_path,
                    detail=(f"préfixe '{subfamily}' non reconnu par docs/corpus.md §3"),
                )
            )
            family = subfamily

        if normalized_id in seen_ids:
            anomalies.append(
                DocumentAnomaly(
                    kind="duplicate_document_id",
                    document_id=normalized_id,
                    relative_path=relative_path,
                    detail=(
                        f"identifiant '{normalized_id}' déjà utilisé par "
                        f"'{seen_ids[normalized_id]}'"
                    ),
                )
            )
        else:
            seen_ids[normalized_id] = relative_path

        available_names = {p.name for p in doc_dir.iterdir() if p.is_file()}
        for entry in parsed.toctree_entries:
            if f"{entry}.rst" not in available_names:
                anomalies.append(
                    DocumentAnomaly(
                        kind="unresolved_toctree_entry",
                        document_id=normalized_id,
                        relative_path=relative_path,
                        detail=(
                            f"entrée toctree '{entry}' ne correspond à aucun "
                            "fichier du répertoire"
                        ),
                    )
                )

        all_files = sorted(p for p in doc_dir.rglob("*") if p.is_file())
        fingerprint, size_bytes = _hash_and_size(all_files, doc_dir)
        files_rel = tuple(p.relative_to(doc_dir).as_posix() for p in all_files)

        document_effectively_empty = True
        rst_texts: dict[str, str] = {}
        for file_path in all_files:
            if file_path.suffix.lower() != ".rst":
                document_effectively_empty = False
                continue
            file_rel = file_path.relative_to(doc_dir).as_posix()
            file_text = file_path.read_text(encoding="utf-8", errors="replace")
            rst_texts[file_rel] = file_text
            if _is_effectively_empty(file_text):
                anomalies.append(
                    DocumentAnomaly(
                        kind="empty_component_file",
                        document_id=normalized_id,
                        relative_path=relative_path,
                        detail=(f"fichier '{file_rel}' sans contenu substantiel"),
                    )
                )
            else:
                document_effectively_empty = False

        if document_effectively_empty:
            anomalies.append(
                DocumentAnomaly(
                    kind="empty_document",
                    document_id=normalized_id,
                    relative_path=relative_path,
                    detail="aucun fichier composant ce document ne porte de contenu",
                )
            )

        toctree_files = {f"{entry}.rst" for entry in parsed.toctree_entries}
        referenced_files = toctree_files | {"index.rst"}
        combined_rst_text = "".join(rst_texts.values())
        for file_rel in files_rel:
            if file_rel in referenced_files:
                continue
            name = PurePosixPath(file_rel).name
            stem = PurePosixPath(file_rel).stem
            if name in combined_rst_text or stem in combined_rst_text:
                continue
            anomalies.append(
                DocumentAnomaly(
                    kind="orphan_file",
                    document_id=normalized_id,
                    relative_path=relative_path,
                    detail=(
                        f"fichier '{file_rel}' ni dans le toctree ni "
                        "mentionné par son nom dans un autre fichier .rst "
                        "du document"
                    ),
                )
            )

        documents.append(
            DocumentEntry(
                document_id=normalized_id,
                raw_label=raw_label,
                directory_name=directory_name,
                family=family,
                subfamily=subfamily,
                title=parsed.title,
                relative_path=relative_path,
                files=files_rel,
                size_bytes=size_bytes,
                fingerprint=fingerprint,
                source_name=source_name,
                source_commit=source_commit,
            )
        )

    return InventoryResult(
        generated_at=resolved_now,
        source_name=source_name,
        source_commit=source_commit,
        documents=tuple(documents),
        anomalies=tuple(anomalies),
    )


def default_inventory_path(project_root: Path) -> Path:
    return project_root / "data" / "raw" / "inventory.jsonl"


def write_inventory_jsonl(result: InventoryResult, path: Path) -> None:
    """One JSON object per line, one line per document — never per anomaly.

    Anomalies are not written to `inventory.jsonl` itself (docs/corpus.md §6
    keeps them a separate, explicit list): `result.anomalies` is the
    caller's responsibility to persist (CLI writes it alongside, lot 6).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for document in result.documents:
            handle.write(document.model_dump_json())
            handle.write("\n")
