"""Loading and checking the knowledge base (lot 42, étapes 1 et 2).

`connaissances/<couche>/<ID>.yaml`, one entry per file, for the five YAML
layers; the findings of lot 41 (`connaissances/constats_code_aster/CA-nnn.json`)
are read through `aster_expert.constats.base` and seen here as `ConstatView`.

Checks made on loading (a failing check refuses the whole base, with every
problem listed):

- the file name is the identifier, an identifier is used once;
- every cited finding, control or pattern exists;
- the level an entry claims does not exceed the level its sources reach (with
  the level of each cited finding);
- the status of a finding is derived: `établi` when it was established by
  execution of a versioned trial case (level C or D), `observé` otherwise,
  `promu` only through the promotion journal (`connaissances/promotions.yaml`).

`verify_against_repository` confronts the proofs with the repository: a cited
case exists and has its fingerprint, a cited test defines its function, cited
code defines its symbol, a cited document exists, an archived run exists when
the archives are present (VM profile; absent in the Cloud, said as such).
"""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aster_expert.connaissances.modeles import (
    ENTRY_TYPES,
    LAYERS,
    YAML_LAYERS,
    CodeEvidence,
    ConstatEvidence,
    Control,
    DecisionEvidence,
    DocumentEvidence,
    Evidence,
    ExecutionEvidence,
    KnowledgeEntry,
    LayerName,
    Level,
    Pattern,
    Reuse,
    Status,
    TestEvidence,
    ValidationReference,
)
from aster_expert.constats.base import BASE_RELATIVE, ConstatBaseError, load_base
from aster_expert.constats.models import Constat

KNOWLEDGE_RELATIVE = Path("connaissances")
PROMOTIONS_FILE = "promotions.yaml"
RUNS_RELATIVE = Path("data") / "processed" / "runs"


class KnowledgeBaseError(ValueError):
    """The base is unreadable or incoherent; the message lists every problem."""


EPREUVES_FILE = "epreuves_constats.yaml"


class ConstatProof(BaseModel):
    """A finding proved in a project other than its origin (lot 44): the
    finding's JSON schema (lot 41) has no `reuses`, so its épreuves live in
    `connaissances/epreuves_constats.yaml`, one per (finding, project)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    constat_id: str
    reuse: Reuse

    @model_validator(mode="after")
    def _is_a_proof(self) -> ConstatProof:
        if not self.reuse.proven:
            message = (
                f"{self.constat_id} : une épreuve est une exécution réussie ou un test "
                "versionné, jamais une citation (lot 44)"
            )
            raise ValueError(message)
        return self


ANOMALIES_FILE = "anomalies_ouvertes.yaml"


class AnomalySignature(BaseModel):
    """How one manifestation of an open anomaly shows (lot 44): the entry of the
    base that records it, the situation and the deviation observed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entry: str
    """Identifier in the base (`CA-nnn`, `REF-nnn`...)."""
    command: str
    situation: str
    deviation: str
    """The observed deviation, as recorded by the entry (text, with its sign)."""


class OpenAnomaly(BaseModel):
    """Several entries that may share one unexplained cause, linked as a single
    open anomaly (lot 44: CA-052 and REF-012). Nothing is concluded: `hypothesis`
    says why they are linked, `investigation` what was (not) done."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    status: Literal["ouverte", "close"]
    opened: dt.date
    lot: str
    signatures: tuple[AnomalySignature, ...] = Field(min_length=2)
    related: tuple[str, ...] = ()
    """Other entries of the same family, not signatures of the anomaly."""
    hypothesis: str
    investigation: str

    @model_validator(mode="after")
    def _coherent(self) -> OpenAnomaly:
        if not re.match(r"^ANO-\d{3}$", self.id):
            message = f"identifiant d'anomalie {self.id!r} : forme ANO-nnn"
            raise ValueError(message)
        return self


def load_anomalies(repo_root: Path) -> list[OpenAnomaly]:
    """The open anomalies of `connaissances/anomalies_ouvertes.yaml` (lot 44)."""
    path = knowledge_dir(repo_root) / ANOMALIES_FILE
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [OpenAnomaly.model_validate(a) for a in raw.get("anomalies") or []]


class ConstatView(BaseModel):
    """A finding of lot 41 seen as a knowledge entry."""

    model_config = ConfigDict(frozen=True)

    constat: Constat
    status: Status
    projects: tuple[str, ...]
    """Origin and projects that *proved* the finding (lot 44: an épreuve of
    `connaissances/epreuves_constats.yaml`, successful execution or passing test).
    Until lot 43 the projects whose fiche merely cites it counted too."""
    cited_by: tuple[str, ...] = ()
    """Projects whose fiche cites the finding without having proved it:
    reported, never counted for promotion."""
    proofs: tuple[ConstatProof, ...] = ()

    @property
    def id(self) -> str:
        return self.constat.constat_id

    @property
    def title(self) -> str:
        return self.constat.entry.topic

    @property
    def summary(self) -> str:
        return self.constat.summary

    @property
    def validation_level(self) -> Level:
        return self.constat.validation_level

    @property
    def origin_project(self) -> str:
        return self.constat.origin.project

    @property
    def commands(self) -> tuple[str, ...]:
        return self.constat.commands

    @property
    def keywords(self) -> tuple[str, ...]:
        return self.constat.keywords

    def searchable_text(self) -> str:
        return self.constat.searchable_text()


AnyEntry = KnowledgeEntry | ConstatView


class PromotionEvent(BaseModel):
    """One promotion of the journal `connaissances/promotions.yaml`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    date: str
    by: str
    reason: str
    projects: tuple[str, ...]


class KnowledgeBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: Path
    """Repository root."""
    entries: dict[str, KnowledgeEntry]
    constats: dict[str, ConstatView]
    files: dict[str, Path]
    """Path of each entry's file, relative to the repository root."""
    anomalies: tuple[OpenAnomaly, ...] = ()
    """Open anomalies linking several entries (lot 44)."""

    def anomalies_of(self, entry_id: str) -> tuple[OpenAnomaly, ...]:
        return tuple(
            a
            for a in self.anomalies
            if entry_id in {s.entry for s in a.signatures} or entry_id in a.related
        )

    def get(self, entry_id: str) -> AnyEntry | None:
        return self.entries.get(entry_id) or self.constats.get(entry_id)

    def layer_of(self, entry_id: str) -> LayerName:
        if entry_id in self.constats:
            return "constats_code_aster"
        return self.entries[entry_id].layer

    def all_entries(self) -> list[AnyEntry]:
        return [*self.constats.values(), *self.entries.values()]

    def by_layer(self, layer: LayerName) -> list[AnyEntry]:
        if layer == "constats_code_aster":
            return list(self.constats.values())
        return [e for e in self.entries.values() if e.layer == layer]

    def counts(self) -> dict[str, dict[str, int]]:
        """Number of entries by layer and status."""
        out: dict[str, dict[str, int]] = {}
        for layer in LAYERS:
            row = {"observé": 0, "établi": 0, "promu": 0}
            for e in self.by_layer(layer):
                row[e.status] += 1
            out[layer] = row
        return out


def knowledge_dir(repo_root: Path) -> Path:
    return repo_root / KNOWLEDGE_RELATIVE


def layer_dir(repo_root: Path, layer: LayerName) -> Path:
    return knowledge_dir(repo_root) / layer


def entry_path(repo_root: Path, entry: KnowledgeEntry) -> Path:
    return layer_dir(repo_root, entry.layer) / f"{entry.id}.yaml"


def dump_entry(entry: KnowledgeEntry) -> str:
    """Deterministic YAML text of an entry (keys in schema order, UTF-8)."""
    data = entry.model_dump(mode="json", exclude_defaults=False)
    return yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, width=88, default_flow_style=False
    )


def write_entry(repo_root: Path, entry: KnowledgeEntry) -> Path:
    path = entry_path(repo_root, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_entry(entry), encoding="utf-8")
    return path


def read_entry(path: Path, layer: LayerName) -> KnowledgeEntry:
    model = ENTRY_TYPES[layer]
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        message = f"{path} : YAML illisible : {exc}"
        raise KnowledgeBaseError(message) from exc
    if not isinstance(raw, dict):
        message = f"{path} : une entrée est un dictionnaire YAML"
        raise KnowledgeBaseError(message)
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '(entrée)'} : {err['msg']}"
            for err in exc.errors()
        )
        message = f"{path} : {details}"
        raise KnowledgeBaseError(message) from exc


def load_promotions(repo_root: Path) -> list[PromotionEvent]:
    path = knowledge_dir(repo_root) / PROMOTIONS_FILE
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    events = raw.get("promotions") or []
    return [PromotionEvent.model_validate(e) for e in events]


def project_aliases(repo_root: Path) -> dict[str, str]:
    """`fiche_project_name` (or, without it, `structure`) of each declared
    project -> its name: the origin of a finding is written with the fiche's
    project name (lot 41)."""
    out: dict[str, str] = {}
    for declaration in sorted((repo_root / "projets").glob("*/projet.yaml")):
        try:
            raw = yaml.safe_load(declaration.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        name = raw.get("name") or declaration.parent.name
        # Same rule as the coherence check (`aster_expert.projet.check`): the
        # fiche carries `fiche_project_name`, or `structure` when it is absent
        # (lot 43: the slab's findings were attributed to no project).
        alias = raw.get("fiche_project_name") or raw.get("structure")
        if isinstance(alias, str):
            out[alias] = str(name)
    return out


def load_constat_proofs(repo_root: Path) -> list[ConstatProof]:
    """The épreuves of `connaissances/epreuves_constats.yaml` (lot 44)."""
    path = knowledge_dir(repo_root) / EPREUVES_FILE
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [ConstatProof.model_validate(e) for e in raw.get("epreuves") or []]


def citing_projects(repo_root: Path) -> dict[str, set[str]]:
    """For each finding, the projects whose fiche cites it by reference
    (`projets/<nom>/projet.yaml`, key `fiche`)."""
    out: dict[str, set[str]] = {}
    projects = repo_root / "projets"
    if not projects.is_dir():
        return out
    for declaration in sorted(projects.glob("*/projet.yaml")):
        try:
            raw = yaml.safe_load(declaration.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        fiche = raw.get("fiche")
        name = raw.get("name") or declaration.parent.name
        if not isinstance(fiche, str):
            continue
        path = declaration.parent / fiche
        if not path.is_file():
            continue
        text = path.read_text("utf-8")
        for match in re.finditer(r'"constat_id"\s*:\s*"(CA-\d{3})"', text):
            out.setdefault(match.group(1), set()).add(str(name))
    return out


def _constat_status(constat: Constat, promoted: set[str]) -> Status:
    if constat.constat_id in promoted:
        return "promu"
    if constat.validation_level in ("C", "D") and constat.trial_cases:
        return "établi"
    return "observé"


def load_knowledge(repo_root: Path) -> KnowledgeBase:
    """Every entry of the six layers, cross-checked. Raises `KnowledgeBaseError`
    listing every problem."""
    problems: list[str] = []
    entries: dict[str, KnowledgeEntry] = {}
    files: dict[str, Path] = {}
    for layer in YAML_LAYERS:
        directory = layer_dir(repo_root, layer)
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            try:
                entry = read_entry(path, layer)
            except KnowledgeBaseError as exc:
                problems.append(str(exc))
                continue
            if path.stem != entry.id:
                problems.append(f"{path} : le fichier porte l'identifiant {entry.id}")
                continue
            if entry.id in entries:
                problems.append(f"{entry.id} : identifiant utilisé deux fois")
                continue
            entries[entry.id] = entry
            files[entry.id] = path.relative_to(repo_root)
    try:
        raw_constats = load_base(repo_root / BASE_RELATIVE)
    except ConstatBaseError as exc:
        problems.append(str(exc))
        raw_constats = {}
    promotions = load_promotions(repo_root)
    promoted = {p.id for p in promotions}
    citing = citing_projects(repo_root)
    aliases = project_aliases(repo_root)
    try:
        epreuves = load_constat_proofs(repo_root)
    except (ValidationError, yaml.YAMLError) as exc:
        problems.append(f"{EPREUVES_FILE} : {exc}")
        epreuves = []
    constats: dict[str, ConstatView] = {}
    for cid, constat in raw_constats.items():
        origin = aliases.get(constat.origin.project, constat.origin.project)
        proofs = tuple(e for e in epreuves if e.constat_id == cid)
        projects = tuple(sorted({origin, *(e.reuse.project for e in proofs)}))
        constats[cid] = ConstatView(
            constat=constat,
            status=_constat_status(constat, promoted),
            projects=projects,
            cited_by=tuple(sorted(citing.get(cid, set()) - set(projects))),
            proofs=proofs,
        )
        files[cid] = BASE_RELATIVE / f"{cid}.json"
    for e in epreuves:
        if e.constat_id not in raw_constats:
            problems.append(f"{EPREUVES_FILE} : {e.constat_id} absent de la base")
    try:
        anomalies = load_anomalies(repo_root)
    except (ValidationError, yaml.YAMLError) as exc:
        problems.append(f"{ANOMALIES_FILE} : {exc}")
        anomalies = []
    known = set(entries) | set(constats)
    for a in anomalies:
        for ref in (*(sig.entry for sig in a.signatures), *a.related):
            if ref not in known:
                problems.append(
                    f"{ANOMALIES_FILE} : {a.id} cite {ref}, absent de la base"
                )
    for p in promotions:
        if p.id not in entries and p.id not in constats:
            problems.append(f"promotions.yaml : {p.id} absent de la base")
    constat_levels: dict[str, Level] = {
        cid: c.validation_level for cid, c in constats.items()
    }
    for entry in entries.values():
        problems += _cross_check(entry, entries, constats, constat_levels)
    if problems:
        raise KnowledgeBaseError(
            "base de connaissances incohérente :\n- " + "\n- ".join(problems)
        )
    return KnowledgeBase(
        root=repo_root,
        entries=entries,
        constats=constats,
        files=files,
        anomalies=tuple(anomalies),
    )


def _all_sources(entry: KnowledgeEntry) -> list[Evidence]:
    sources: list[Evidence] = [*entry.sources, *(r.evidence for r in entry.reuses)]
    if isinstance(entry, Pattern):
        sources += list(entry.implementation)
    if isinstance(entry, Control):
        sources.append(entry.implementation)
        if entry.caught_error.evidence is not None:
            sources.append(entry.caught_error.evidence)
    return sources


def _cross_check(
    entry: KnowledgeEntry,
    entries: dict[str, KnowledgeEntry],
    constats: dict[str, ConstatView],
    constat_levels: dict[str, Level],
) -> list[str]:
    problems = []
    for source in _all_sources(entry):
        if isinstance(source, ConstatEvidence) and source.constat_id not in constats:
            problems.append(
                f"{entry.id} : constat {source.constat_id} absent de la base"
            )
    if isinstance(entry, Pattern):
        for cid in entry.constats:
            if cid not in constats:
                problems.append(f"{entry.id} : constat {cid} absent de la base")
        for ctl in entry.controls:
            if ctl not in entries:
                problems.append(f"{entry.id} : contrôle {ctl} absent de la base")
    reached = entry.evidence_level(constat_levels)
    if "ABCDE".index(entry.validation_level) > "ABCDE".index(reached):
        problems.append(
            f"{entry.id} : niveau {entry.validation_level} déclaré, {reached} "
            "atteint par les sources"
        )
    return problems


# --------------------------------------------------------------------------
# Confrontation des preuves au dépôt
# --------------------------------------------------------------------------


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _defines(path: Path, name: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name == name
        ):
            return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return True
    return False


class RepositoryCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    problems: tuple[str, ...]
    unverifiable: tuple[str, ...]
    """Archived runs not checked because the archives are absent (Cloud)."""
    checked: int


def verify_against_repository(base: KnowledgeBase) -> RepositoryCheck:
    root = base.root
    runs = root / RUNS_RELATIVE
    runs_present = runs.is_dir()
    problems: list[str] = []
    unverifiable: list[str] = []
    checked = 0
    for entry in base.entries.values():
        sources = _all_sources(entry)
        if isinstance(entry, ValidationReference):
            for case in entry.cases:
                for q in case.quantities:
                    if (
                        q.refined_case_path
                        and not (root / q.refined_case_path).is_file()
                    ):
                        problems.append(
                            f"{entry.id} : cas raffiné absent {q.refined_case_path}"
                        )
        for source in sources:
            checked += 1
            problems += _check_source(
                entry.id, source, root, runs, runs_present, unverifiable
            )
    for view in base.constats.values():
        for proof in view.proofs:
            checked += 1
            problems += _check_source(
                view.id, proof.reuse.evidence, root, runs, runs_present, unverifiable
            )
    return RepositoryCheck(
        problems=tuple(problems), unverifiable=tuple(unverifiable), checked=checked
    )


def _check_source(
    entry_id: str,
    source: Evidence,
    root: Path,
    runs: Path,
    runs_present: bool,
    unverifiable: list[str],
) -> list[str]:
    problems = []
    if isinstance(source, ExecutionEvidence):
        if source.case_path is not None:
            path = root / source.case_path
            if not path.is_file():
                problems.append(f"{entry_id} : cas absent {source.case_path}")
            elif sha256_path(path) != source.case_sha256:
                problems.append(f"{entry_id} : empreinte modifiée {source.case_path}")
        if source.run is not None:
            if not runs_present:
                unverifiable.append(f"{entry_id} : {source.run}")
            elif not (runs / source.run).is_dir():
                problems.append(f"{entry_id} : exécution archivée absente {source.run}")
    elif isinstance(source, TestEvidence | CodeEvidence):
        path = root / source.path
        name = source.function if isinstance(source, TestEvidence) else source.symbol
        if not path.is_file():
            problems.append(f"{entry_id} : fichier absent {source.path}")
        elif path.suffix == ".py" and not _defines(path, name):
            problems.append(f"{entry_id} : {name} non défini dans {source.path}")
        elif path.suffix != ".py" and name not in path.read_text(
            "utf-8", errors="replace"
        ):
            problems.append(f"{entry_id} : {name} absent de {source.path}")
    elif isinstance(source, DocumentEvidence | DecisionEvidence):
        rel = source.path if isinstance(source, DocumentEvidence) else source.fiche
        if not (root / rel).is_file():
            problems.append(f"{entry_id} : document absent {rel}")
    return problems


def entry_as_dict(entry: AnyEntry, base: KnowledgeBase) -> dict[str, Any]:
    """Short form used by the search results and the reports."""
    return {
        "id": entry.id,
        "layer": base.layer_of(entry.id),
        "title": entry.title,
        "summary": entry.summary,
        "status": entry.status,
        "validation_level": entry.validation_level,
        "origin_project": entry.origin_project,
        "commands": list(entry.commands),
        "keywords": list(entry.keywords),
        "file": base.files[entry.id].as_posix(),
        "open_anomalies": [a.id for a in base.anomalies_of(entry.id)],
    }


__all__ = [
    "ANOMALIES_FILE",
    "EPREUVES_FILE",
    "KNOWLEDGE_RELATIVE",
    "PROMOTIONS_FILE",
    "RUNS_RELATIVE",
    "AnyEntry",
    "AnomalySignature",
    "ConstatProof",
    "ConstatView",
    "KnowledgeBase",
    "KnowledgeBaseError",
    "PromotionEvent",
    "RepositoryCheck",
    "citing_projects",
    "OpenAnomaly",
    "load_anomalies",
    "load_constat_proofs",
    "project_aliases",
    "dump_entry",
    "entry_as_dict",
    "entry_path",
    "knowledge_dir",
    "layer_dir",
    "load_knowledge",
    "load_promotions",
    "read_entry",
    "sha256_path",
    "verify_against_repository",
    "write_entry",
]
