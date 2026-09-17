"""Sonde d'analyse .rst par docutils (lot 6, I3).

Valide — ou infirme — l'arbitrage retenu au lot 6 : analyser le corpus
`codeaster-doc` depuis ses sources `.rst` versionnées, jamais depuis un
rendu Sphinx construit (docs/corpus.md §2 ; docs/development-plan.md,
lot 6). `docutils` seul (sans Sphinx, sans `conf.py` exécuté, sans
extension) ne connaît ni les directives ni les rôles propres à Sphinx
(`toctree`, `ref`, `external:ref`, ...) : il les signale comme inconnus au
lieu de les résoudre, mais — fait vérifié ici, pas supposé — ne perd
jamais le texte brut qui les compose. Ce module mesure précisément ce que
`docutils` récupère et ce qu'il ne récupère pas, jamais l'un supposé à
partir de l'autre.

Un élément non reconnu (directive ou rôle) ne provoque jamais un échec
silencieux : `probe_source` le recense toujours, avec son nom exact, plutôt
que de l'ignorer (CLAUDE.md, « Ne jamais neutraliser une alarme sans en
expliquer la cause »).
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from docutils import nodes
from docutils.core import publish_doctree
from docutils.utils import SystemMessage

from aster_expert.ingestion.models import ProbeFrequency, RstProbeReport

_UNKNOWN_DIRECTIVE_RE = re.compile(r'Unknown directive type "([^"]+)"')
_UNKNOWN_ROLE_RE = re.compile(r'Unknown interpreted text role "([^"]+)"')
_INCLUDE_PATH_RE = re.compile(
    r'include" directive path:\s*\n\s*InputError.*?\'([^\']+)\''
)

_SETTINGS_OVERRIDES = {
    "report_level": 5,  # ne jamais imprimer sur la sortie standard/erreur
    "halt_level": 5,  # ne jamais interrompre l'analyse (docutils.utils.Reporter)
    "file_insertion_enabled": True,  # nécessaire pour tenter réellement `include`
    # `source/conf.py` du corpus déclare `language = "fr"` : sans ce réglage,
    # docutils reste sur sa table de noms anglaise et signale à tort comme
    # « directive inconnue » un nom français d'une directive pourtant
    # native de docutils (constaté au lot 6, I3 : `.. avertissement::` est
    # l'alias français, fourni par `docutils.parsers.rst.languages.fr`, de
    # la directive native `warning` — jamais une extension Sphinx).
    "language_code": "fr",
}


@dataclass(frozen=True)
class ProbeResult:
    """Result of probing exactly one `.rst` file's raw text with docutils."""

    raw_chars: int
    recoverable_chars: int
    unknown_directives: tuple[str, ...]
    unknown_roles: tuple[str, ...]
    unresolved_includes: tuple[str, ...]


def _is_synthetic_diagnostic_paragraph(node: nodes.Text) -> bool:
    """True for text that IS one of docutils' own generated messages.

    Never true for a `literal_block`/`problematic` node nested under the
    same `system_message`: that node echoes the *original* source text
    verbatim (verified empirically, lot 6 compte rendu) — it is exactly
    what would be lost if excluded here.
    """
    parent = node.parent
    return isinstance(parent, nodes.paragraph) and isinstance(
        parent.parent, nodes.system_message
    )


def probe_source(text: str, *, source_path: str = "<string>") -> ProbeResult:
    """Parse one `.rst` source with bare docutils and measure what survives.

    Never raises on malformed or Sphinx-only markup: `report_level` and
    `halt_level` are both set to suppress printing and to never halt, so an
    unknown directive/role becomes a `system_message` node in the doctree,
    inspected here, rather than an exception. A genuinely unparsable source
    (not valid reST at all) still raises `docutils.utils.SystemMessage`,
    propagated rather than swallowed.
    """
    doctree = publish_doctree(
        text,
        source_path=source_path,
        settings_overrides=_SETTINGS_OVERRIDES,
    )

    recoverable_chars = 0
    for text_node in doctree.findall(nodes.Text):
        if not _is_synthetic_diagnostic_paragraph(text_node):
            recoverable_chars += len(text_node.astext())

    unknown_directives: list[str] = []
    unknown_roles: list[str] = []
    unresolved_includes: list[str] = []
    for message in doctree.findall(nodes.system_message):
        message_text = message.astext()
        for match in _UNKNOWN_DIRECTIVE_RE.finditer(message_text):
            unknown_directives.append(match.group(1))
        for match in _UNKNOWN_ROLE_RE.finditer(message_text):
            unknown_roles.append(match.group(1))
        include_match = _INCLUDE_PATH_RE.search(message_text)
        if include_match:
            unresolved_includes.append(include_match.group(1))

    return ProbeResult(
        raw_chars=len(text),
        recoverable_chars=recoverable_chars,
        unknown_directives=tuple(unknown_directives),
        unknown_roles=tuple(unknown_roles),
        unresolved_includes=tuple(unresolved_includes),
    )


def probe_file(path: Path) -> ProbeResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return probe_source(text, source_path=str(path))
    except SystemMessage as exc:
        # A source docutils itself refuses to parse at all (not just an
        # unknown directive/role, which never raises): reported as total
        # loss for this file, never guessed at partially.
        return ProbeResult(
            raw_chars=len(text),
            recoverable_chars=0,
            unknown_directives=(),
            unknown_roles=(),
            unresolved_includes=(f"PARSE_ERROR: {exc}",),
        )


@dataclass(frozen=True)
class AggregateProbeResult:
    """Sum of `probe_file` over every file composing a sample of documents."""

    sampled_documents: int
    sampled_files: int
    raw_chars: int
    recoverable_chars: int
    unknown_directives: Counter[str] = field(default_factory=Counter)
    unknown_roles: Counter[str] = field(default_factory=Counter)
    unresolved_includes: Counter[str] = field(default_factory=Counter)
    parse_errors: tuple[str, ...] = ()

    @property
    def recovery_ratio(self) -> float:
        return self.recoverable_chars / self.raw_chars if self.raw_chars else 1.0


def probe_documents(
    document_dirs: list[Path],
) -> AggregateProbeResult:
    """Probe every `.rst` file composing each of the given document dirs."""
    unknown_directives: Counter[str] = Counter()
    unknown_roles: Counter[str] = Counter()
    unresolved_includes: Counter[str] = Counter()
    parse_errors: list[str] = []
    raw_chars = 0
    recoverable_chars = 0
    file_count = 0

    for doc_dir in document_dirs:
        for rst_path in sorted(doc_dir.rglob("*.rst")):
            file_count += 1
            result = probe_file(rst_path)
            raw_chars += result.raw_chars
            recoverable_chars += result.recoverable_chars
            unknown_directives.update(result.unknown_directives)
            unknown_roles.update(result.unknown_roles)
            for target in result.unresolved_includes:
                if target.startswith("PARSE_ERROR"):
                    parse_errors.append(f"{rst_path}: {target}")
                else:
                    unresolved_includes[target] += 1

    return AggregateProbeResult(
        sampled_documents=len(document_dirs),
        sampled_files=file_count,
        raw_chars=raw_chars,
        recoverable_chars=recoverable_chars,
        unknown_directives=unknown_directives,
        unknown_roles=unknown_roles,
        unresolved_includes=unresolved_includes,
        parse_errors=tuple(parse_errors),
    )


def stratified_sample_by_family(
    documents_by_family: dict[str, list[str]],
    per_family: dict[str, int],
) -> dict[str, list[str]]:
    """Evenly spaced, deterministic sample of relative paths per family.

    Evenly spaced over the family's documents sorted by id (not the first
    N, which would cluster in one sub-theme, e.g. always `r3.*` for family
    `R`) — deterministic so re-running the probe on the same inventory
    reproduces the same sample, never a random draw.
    """
    sampled: dict[str, list[str]] = {}
    for family, count in per_family.items():
        pool = sorted(documents_by_family.get(family, []))
        if not pool:
            sampled[family] = []
            continue
        n = min(count, len(pool))
        if n == len(pool):
            sampled[family] = pool
            continue
        step = len(pool) / n
        sampled[family] = [pool[int(i * step)] for i in range(n)]
    return sampled


def find_conf_py_extensions(conf_py_path: Path) -> tuple[str, ...]:
    """Read the `extensions = [...]` assignment of a Sphinx `conf.py`.

    Never executes `conf.py` (it is arbitrary Python, and the whole point
    of the lot 6 arbitrage is to never need a working Sphinx build):
    parsed with `ast`, the same posture as
    `aster_expert.parsing.comm_parser` for `.comm` files, and only the
    single `extensions = [...]` top-level assignment is read.
    """
    tree = ast.parse(conf_py_path.read_text(encoding="utf-8"))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if isinstance(target, ast.Name) and target.id == "extensions":
            value = ast.literal_eval(statement.value)
            return tuple(value)
    return ()


def load_inventory_index(
    inventory_path: Path,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Read `data/raw/inventory.jsonl`, grouping document ids by family.

    Never re-derives family/family membership from the id itself here: the
    inventory (`aster_expert.ingestion.inventory.build_inventory`) is the
    one place that decides `family`, so a re-derivation here could silently
    drift from it.
    """
    by_family: dict[str, list[str]] = {}
    relative_path_by_id: dict[str, str] = {}
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        by_family.setdefault(entry["family"], []).append(entry["document_id"])
        relative_path_by_id[entry["document_id"]] = entry["relative_path"]
    return by_family, relative_path_by_id


def build_probe_report(
    *,
    inventory_path: Path,
    repo_root: Path,
    conf_py_path: Path,
    source_name: str,
    source_commit: str,
    per_family: dict[str, int],
    now: datetime | None = None,
) -> RstProbeReport:
    """Build the full I3 probe report from an existing inventory.

    `per_family` keys are inventory family codes (docs/corpus.md §3),
    except the synthetic key `"man_s"`, which pools the `SU` and `SV`
    families together — the task names the family by its source directory
    (`man_s`), which the inventory itself never uses as a `family` value
    (it distinguishes `SU`/`SV`, docs/corpus.md §3 amendment lot 6, I2).
    """
    resolved_now = now if now is not None else datetime.now(UTC)
    documents_by_family, relative_path_by_id = load_inventory_index(inventory_path)
    if "man_s" in per_family:
        documents_by_family["man_s"] = documents_by_family.get(
            "SU", []
        ) + documents_by_family.get("SV", [])

    sample = stratified_sample_by_family(documents_by_family, per_family)
    doc_dirs = [
        repo_root / relative_path_by_id[doc_id]
        for ids in sample.values()
        for doc_id in ids
    ]

    aggregate = probe_documents(doc_dirs)
    conf_py_extensions = find_conf_py_extensions(conf_py_path)

    return RstProbeReport(
        generated_at=resolved_now,
        source_name=source_name,
        source_commit=source_commit,
        sample_per_family={k: tuple(v) for k, v in sample.items()},
        sampled_documents=aggregate.sampled_documents,
        sampled_files=aggregate.sampled_files,
        raw_chars=aggregate.raw_chars,
        recoverable_chars=aggregate.recoverable_chars,
        recovery_ratio=aggregate.recovery_ratio,
        parse_errors=aggregate.parse_errors,
        unknown_directives=tuple(
            ProbeFrequency(name=name, count=count)
            for name, count in aggregate.unknown_directives.most_common()
        ),
        unknown_roles=tuple(
            ProbeFrequency(name=name, count=count)
            for name, count in aggregate.unknown_roles.most_common()
        ),
        unresolved_includes=tuple(
            ProbeFrequency(name=name, count=count)
            for name, count in aggregate.unresolved_includes.most_common()
        ),
        conf_py_extensions=conf_py_extensions,
    )


def default_probe_report_path(project_root: Path) -> Path:
    return project_root / "data" / "processed" / "rst_probe_report.json"


def write_probe_report_json(report: RstProbeReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
