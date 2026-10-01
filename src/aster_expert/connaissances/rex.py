"""Retour d'expérience of a project (lot 42, étape 4): `aster-expert rex <projet>`.

The registry `connaissances/rex/<projet>.yaml` declares, for one project:

- `case_roots`: where the project's cases live (a run is attributed to the
  project when the `.comm` of its compte rendu lies under one of them);
- `legacy_runs`: the runs archived before compte rendus existed (lot 41), which
  name no path: those before `before` are attributed to the project, with their
  durations read from a versioned annex when there is one;
- `baseline`, `lots`: declared figures (supervisor interventions, knowledge
  that avoided an error), each with its nature (`mesure`, `estimation`,
  `non renseigné`) -- never presented as measured when they are not;
- `classifications`: one line per failed run: attached to a diagnostic of the
  base (`rattaché`), opened as a new diagnostic (`nouveau`), or set aside
  (`écarté`) as a typing or environment slip, always with a one-sentence reason;
- `reviews`: the history of the recorded reviews.

`review_project` lists the failed runs with their signature, the diagnostics
that match each one, and refuses closure (`blocking`) while a failure is not
classified or is classified under another signature. It also proposes the
fiche's `code_aster` entries not yet in the base, flags functions of the project
close to a pattern (shared Code_Aster identifiers), and computes the metrics
written to `connaissances/metriques/` with the Markdown dashboard. Without the
run archives (Cloud profile), it says so and examines nothing, without failing.
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aster_expert.connaissances.base import RUNS_RELATIVE, KnowledgeBase, load_knowledge
from aster_expert.connaissances.modeles import (
    LAYERS,
    CodeEvidence,
    Control,
    Diagnostic,
    Evidence,
    Pattern,
)
from aster_expert.connaissances.signatures import (
    OK_DIAGNOSTICS,
    DiagnosticMatch,
    RunMessage,
    job_diagnostic,
    listing_messages,
    match_diagnostics,
    primary_signature,
)
from aster_expert.mcp.logging import QueryLogEntry, default_query_log_path
from aster_expert.retrieval.candidates import read_journal

REX_RELATIVE = Path("connaissances") / "rex"
METRICS_RELATIVE = Path("connaissances") / "metriques"
DASHBOARD_NAME = "tableau_de_bord.md"
CONSULTATION_TOOLS = ("search_connaissances", "search_constats")
_RUN_TIME = re.compile(r"^(\d{8}T\d{6})-")
_UPPER = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

Nature = Literal["mesure", "estimation", "non renseigné"]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LegacyRuns(_Model):
    before: dt.datetime
    durations: str | None = None
    """Versioned annex (JSON list: `execution`, `temps_run_aster_s`)."""
    reason: str


class DeclaredFigure(_Model):
    value: float | None
    nature: Nature
    note: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> DeclaredFigure:
        if (self.value is None) != (self.nature == "non renseigné"):
            message = (
                "une valeur déclarée a une nature ; « non renseigné » n'a pas de valeur"
            )
            raise ValueError(message)
        return self


class Baseline(_Model):
    source: str
    lots: int
    executions: int
    failures: int
    compute_hours: float
    supervisor_interventions: DeclaredFigure


class LotRecord(_Model):
    lot: str
    supervisor_interventions: DeclaredFigure
    avoided_errors: DeclaredFigure
    note: str | None = None


class Classification(_Model):
    run: str
    signature: str
    decision: Literal["rattaché", "nouveau", "écarté"]
    diagnostic: str | None = None
    reason: str

    @model_validator(mode="after")
    def _coherent(self) -> Classification:
        if (self.decision == "écarté") != (self.diagnostic is None):
            message = (
                f"{self.run} : un échec rattaché ou ouvert nomme son diagnostic ; un "
                "échec écarté n'en nomme pas"
            )
            raise ValueError(message)
        if not self.reason.strip():
            message = f"{self.run} : une phrase de motif est exigée"
            raise ValueError(message)
        return self


class Review(_Model):
    date: dt.date
    lot: str
    runs: int
    failures: int
    unclassified: int
    last_run: str | None


class RexRegistry(_Model):
    project: str
    case_roots: tuple[str, ...]
    legacy_runs: LegacyRuns | None = None
    baseline: Baseline | None = None
    lots: tuple[LotRecord, ...] = ()
    reviews: tuple[Review, ...] = ()
    classifications: tuple[Classification, ...] = ()

    @model_validator(mode="after")
    def _unique_runs(self) -> RexRegistry:
        runs = [c.run for c in self.classifications]
        if len(runs) != len(set(runs)):
            message = "une exécution est classée deux fois"
            raise ValueError(message)
        return self


def registry_path(repo_root: Path, project: str) -> Path:
    return repo_root / REX_RELATIVE / f"{project}.yaml"


def load_registry(repo_root: Path, project: str) -> RexRegistry:
    path = registry_path(repo_root, project)
    if not path.is_file():
        message = (
            f"registre de retour d'expérience absent : {path.relative_to(repo_root)} "
            "(déclarer au moins `project` et `case_roots`)"
        )
        raise FileNotFoundError(message)
    registry = RexRegistry.model_validate(yaml.safe_load(path.read_text("utf-8")))
    if registry.project != project:
        message = f"{path} : le registre porte le projet {registry.project}"
        raise ValueError(message)
    return registry


def write_registry(repo_root: Path, registry: RexRegistry) -> Path:
    path = registry_path(repo_root, registry.project)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = registry.model_dump(mode="json", exclude_none=False)
    path.write_text(
        "# Registre de retour d'expérience (aster-expert rex, lot 42). Les "
        "classements\n# d'échec et les chiffres déclarés sont écrits par la "
        "session ; `reviews` par\n# `aster-expert rex --enregistrer`.\n"
        + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=88),
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------
# Exécutions du projet
# --------------------------------------------------------------------------


class RunSummary(_Model):
    run: str
    started: dt.datetime
    comm: str
    failed: bool
    job: str | None
    signature: str | None
    duration_s: float | None
    duration_kind: Literal["mur", "aster", "inconnue"]
    """`mur`: wall time of `aster-expert run` (compte rendu, container start
    included); `aster`: elapsed time measured by `run_aster` (legacy annex)."""
    matches: tuple[DiagnosticMatch, ...] = ()


def run_started(run_id: str) -> dt.datetime | None:
    m = _RUN_TIME.match(run_id)
    if m is None:
        return None
    return dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")


def _listing(run_dir: Path, mess_path: str | None) -> str:
    candidates = [run_dir / "proc.0" / "fort.6"]
    if mess_path:
        candidates.insert(0, Path(mess_path))
        candidates.insert(1, run_dir / Path(mess_path).name)
    candidates += sorted(run_dir.glob("*.mess"))
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


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


def _legacy_durations(repo_root: Path, legacy: LegacyRuns | None) -> dict[str, float]:
    if legacy is None or legacy.durations is None:
        return {}
    path = repo_root / legacy.durations
    if not path.is_file():
        return {}
    out = {}
    for row in json.loads(path.read_text(encoding="utf-8")):
        times = row.get("temps_run_aster_s") or []
        if len(times) >= 4:
            out[str(row["execution"])] = float(times[3])
    return out


def project_runs(
    repo_root: Path, registry: RexRegistry, base: KnowledgeBase | None
) -> list[RunSummary]:
    """Runs attributed to the project, oldest first (see the module docstring)."""
    runs_dir = repo_root / RUNS_RELATIVE
    durations = _legacy_durations(repo_root, registry.legacy_runs)
    roots = tuple(r.rstrip("/") + "/" for r in registry.case_roots)
    out = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        started = run_started(run_dir.name)
        if started is None:
            continue
        record = run_dir / "compte_rendu.json"
        mess_path = None
        if record.is_file():
            data = json.loads(record.read_text(encoding="utf-8"))
            report = data["report"]
            comm = _relative_to_root(str(report["comm_path"]), repo_root)
            if comm is None or not comm.startswith(roots):
                continue
            failed = report["status"] not in ("completed_ok", "completed_with_alarms")
            job = report.get("diag")
            duration = report.get("duration_s")
            kind: Literal["mur", "aster", "inconnue"] = (
                "mur" if duration is not None else "inconnue"
            )
            mess_path = report.get("mess_path")
            errors = [
                RunMessage(
                    kind=e["kind"], identifier=e.get("identifier"), text=e["text"]
                )
                for e in data.get("errors", [])
            ]
        else:
            legacy = registry.legacy_runs
            if legacy is None or started >= legacy.before.replace(tzinfo=None):
                continue
            comms = sorted(p.name for p in run_dir.glob("*.comm"))
            comm = comms[0] if comms else "(aucun .comm)"
            errors = []
            job = None
            failed = False
            duration = durations.get(run_dir.name)
            kind = "aster" if duration is not None else "inconnue"
        listing = _listing(run_dir, mess_path)
        if not record.is_file():
            job = job_diagnostic(listing)
            failed = job is None or job not in OK_DIAGNOSTICS
        signature = None
        matches: tuple[DiagnosticMatch, ...] = ()
        if failed:
            messages = listing_messages(listing) if listing else errors
            signature = primary_signature(messages, job, listing)
            if base is not None:
                matches = tuple(
                    match_diagnostics(base, messages, diag=job, listing=listing)
                )
        out.append(
            RunSummary(
                run=run_dir.name,
                started=started,
                comm=comm,
                failed=failed,
                job=job,
                signature=signature,
                duration_s=duration,
                duration_kind=kind,
                matches=matches,
            )
        )
    return out


# --------------------------------------------------------------------------
# Propositions
# --------------------------------------------------------------------------


class ConstatProposal(_Model):
    point_label: str | None
    topic: str


class PatternCandidate(_Model):
    path: str
    function: str
    identifiers: tuple[str, ...]
    closest: str | None
    similarity: float
    kind: Literal["proche d'un patron", "nouveau patron possible"]


def _declaration(repo_root: Path, project: str) -> dict[str, Any]:
    path = repo_root / "projets" / project / "projet.yaml"
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def constat_proposals(repo_root: Path, project: str) -> list[ConstatProposal]:
    """`code_aster` entries of the project's fiche still copied in it, not cited
    from the base (lot 41): each is a finding to add to the base."""
    fiche = _declaration(repo_root, project).get("fiche")
    if not isinstance(fiche, str):
        return []
    path = repo_root / "projets" / project / fiche
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        ConstatProposal(point_label=e.get("point_label"), topic=str(e.get("topic")))
        for e in data.get("entries", [])
        if e.get("nature") == "code_aster"
    ]


def pattern_candidates(
    repo_root: Path, project: str, base: KnowledgeBase, *, limit: int = 15
) -> list[PatternCandidate]:
    """Functions of the project naming Code_Aster identifiers of the base, not
    yet cited as the code of a pattern or a control, ranked by their Jaccard
    similarity to the closest pattern."""
    vocabulary: set[str] = set()
    for entry in base.all_entries():
        vocabulary.update(entry.commands)
        vocabulary.update(entry.keywords)
    commands = {c for e in base.all_entries() for c in e.commands}
    cited: set[tuple[str, str]] = set()
    patterns = [e for e in base.entries.values() if isinstance(e, Pattern)]
    for entry in base.entries.values():
        sources: list[Evidence] = list(entry.sources)
        if isinstance(entry, Pattern):
            sources += list(entry.implementation)
        if isinstance(entry, Control):
            sources.append(entry.implementation)
        for s in sources:
            if isinstance(s, CodeEvidence):
                cited.add((s.path, s.symbol))
    project_dir = repo_root / "projets" / project
    out = []
    for path in sorted(project_dir.rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        if "/tests/" in rel or "/scripts/" in rel or "/resultats/" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        if "aster_expert.connaissances" in text:
            # Code that writes knowledge entries, not modelling code.
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        source = text.splitlines()
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or (rel, node.name) in cited:
                continue
            body = "\n".join(source[node.lineno - 1 : node.end_lineno])
            tokens = set(_UPPER.findall(body)) & vocabulary
            if len(tokens & commands) < 1 or len(tokens) < 3:
                continue
            best, score = None, 0.0
            for p in patterns:
                ptokens = set(p.commands) | set(p.keywords)
                union = tokens | ptokens
                sim = len(tokens & ptokens) / len(union) if union else 0.0
                if sim > score:
                    best, score = p.id, sim
            out.append(
                PatternCandidate(
                    path=rel,
                    function=node.name,
                    identifiers=tuple(sorted(tokens)),
                    closest=best,
                    similarity=round(score, 3),
                    kind="proche d'un patron"
                    if score >= 0.25
                    else "nouveau patron possible",
                )
            )
    out.sort(key=lambda c: (-c.similarity, -len(c.identifiers), c.path, c.function))
    return out[:limit]


# --------------------------------------------------------------------------
# Revue
# --------------------------------------------------------------------------


class FailureLine(_Model):
    run: str
    comm: str
    signature: str
    classification: Classification | None
    problem: str | None
    """Why the failure blocks: not classified, classified under another
    signature, or attached to a diagnostic absent from the base."""
    suggestions: tuple[str, ...]


class RexReport(_Model):
    project: str
    archives_present: bool
    runs: int = 0
    failures: tuple[FailureLine, ...] = ()
    since_last_review: int = 0
    last_review: dt.date | None = None
    unknown_classified_runs: tuple[str, ...] = ()
    constat_proposals: tuple[ConstatProposal, ...] = ()
    pattern_candidates: tuple[PatternCandidate, ...] = ()
    metrics: dict[str, Any] = Field(default_factory=dict)

    @property
    def blocking(self) -> list[FailureLine]:
        return [f for f in self.failures if f.problem is not None]


def review_project(repo_root: Path, project: str) -> RexReport:
    registry = load_registry(repo_root, project)
    base = load_knowledge(repo_root)
    proposals = tuple(constat_proposals(repo_root, project))
    candidates = tuple(pattern_candidates(repo_root, project, base))
    if not (repo_root / RUNS_RELATIVE).is_dir():
        return RexReport(
            project=project,
            archives_present=False,
            constat_proposals=proposals,
            pattern_candidates=candidates,
            metrics=compute_metrics(repo_root, registry, base, None),
        )
    runs = project_runs(repo_root, registry, base)
    by_run = {c.run: c for c in registry.classifications}
    last_review = registry.reviews[-1] if registry.reviews else None
    failures = []
    since = 0
    for r in runs:
        if not r.failed:
            continue
        assert r.signature is not None
        if last_review is not None and r.started.date() > last_review.date:
            since += 1
        c = by_run.get(r.run)
        problem = None
        if c is None:
            problem = "non classé"
        elif c.signature != r.signature:
            problem = f"classé sous la signature « {c.signature} »"
        elif c.diagnostic is not None and c.diagnostic not in base.entries:
            problem = f"diagnostic {c.diagnostic} absent de la base"
        elif c.diagnostic is not None and not isinstance(
            base.entries[c.diagnostic], Diagnostic
        ):
            problem = f"{c.diagnostic} n'est pas un diagnostic"
        failures.append(
            FailureLine(
                run=r.run,
                comm=r.comm,
                signature=r.signature,
                classification=c,
                problem=problem,
                suggestions=tuple(m.diagnostic_id for m in r.matches),
            )
        )
    seen = {r.run for r in runs}
    unknown = tuple(c.run for c in registry.classifications if c.run not in seen)
    return RexReport(
        project=project,
        archives_present=True,
        runs=len(runs),
        failures=tuple(failures),
        since_last_review=since if last_review else len(failures),
        last_review=last_review.date if last_review else None,
        unknown_classified_runs=unknown,
        constat_proposals=proposals,
        pattern_candidates=candidates,
        metrics=compute_metrics(repo_root, registry, base, runs),
    )


# --------------------------------------------------------------------------
# Métriques
# --------------------------------------------------------------------------


def _fiche_project_name(repo_root: Path, project: str) -> str | None:
    name = _declaration(repo_root, project).get("fiche_project_name")
    return name if isinstance(name, str) else None


def knowledge_counts(
    repo_root: Path, project: str, base: KnowledgeBase
) -> dict[str, dict[str, int]]:
    """Entries the project created, by layer and status (a finding's origin is
    the fiche's project name declared in `projet.yaml`)."""
    names = {project}
    alias = _fiche_project_name(repo_root, project)
    if alias:
        names.add(alias)
    out: dict[str, dict[str, int]] = {}
    for layer in LAYERS:
        row = {"observé": 0, "établi": 0, "promu": 0}
        for e in base.by_layer(layer):
            if e.origin_project in names:
                row[e.status] += 1
        out[layer] = row
    return out


def read_log_tolerant(path: Path) -> tuple[list[QueryLogEntry], int]:
    """Valid usage entries of the query journal (`mcp-check` calls excluded) and
    the number of unreadable lines (a line damaged by an abrupt stop of the
    machine is counted, never repaired)."""
    return read_journal(path)


def _consultations(repo_root: Path, since: dt.date | None) -> dict[str, int]:
    out = dict.fromkeys(CONSULTATION_TOOLS, 0)
    entries, _ = read_log_tolerant(default_query_log_path(repo_root))
    for entry in entries:
        if entry.tool not in out:
            continue
        if since is not None and entry.timestamp.date() <= since:
            continue
        out[entry.tool] += 1
    return out


def _figure(fig: DeclaredFigure | None) -> dict[str, Any]:
    if fig is None:
        return {"value": None, "nature": "non renseigné"}
    return {"value": fig.value, "nature": fig.nature, "note": fig.note}


def compute_metrics(
    repo_root: Path,
    registry: RexRegistry,
    base: KnowledgeBase,
    runs: list[RunSummary] | None,
) -> dict[str, Any]:
    counts = knowledge_counts(repo_root, registry.project, base)
    created = sum(sum(row.values()) for row in counts.values())
    promoted = sum(row["promu"] for row in counts.values())
    declared_interventions = [
        lot.supervisor_interventions.value
        for lot in registry.lots
        if lot.supervisor_interventions.value is not None
    ]
    declared_avoided = [
        lot.avoided_errors.value
        for lot in registry.lots
        if lot.avoided_errors.value is not None
    ]
    metrics: dict[str, Any] = {
        "project": registry.project,
        "baseline": registry.baseline.model_dump(mode="json")
        if registry.baseline
        else None,
        "knowledge": {
            "created": created,
            "promoted": promoted,
            "by_layer": counts,
        },
        "consultations": {
            "calls": _consultations(repo_root, None),
            "note": (
                "appels journalisés (query_log.jsonl, hors mcp-check) de tous les "
                "projets : le journal ne porte pas le projet"
            ),
            "avoided_errors": {
                "value": sum(declared_avoided) if declared_avoided else None,
                "nature": "mesure" if declared_avoided else "non renseigné",
                "note": "déclaré lot par lot dans le compte rendu (registre, `lots`)",
            },
        },
        "lots": [
            {
                "lot": lot.lot,
                "supervisor_interventions": _figure(lot.supervisor_interventions),
                "avoided_errors": _figure(lot.avoided_errors),
            }
            for lot in registry.lots
        ],
        "declared_interventions_since_baseline": sum(declared_interventions)
        if declared_interventions
        else None,
    }
    if runs is None:
        metrics["measured"] = None
        return metrics
    failed = [r for r in runs if r.failed]
    by_signature: dict[str, int] = {}
    classified = {c.run: c for c in registry.classifications}
    by_cause: dict[str, int] = {}
    for r in failed:
        assert r.signature is not None
        by_signature[r.signature] = by_signature.get(r.signature, 0) + 1
        c = classified.get(r.run)
        key = (
            "non classé"
            if c is None
            else (c.diagnostic if c.diagnostic is not None else "écarté")
        )
        by_cause[key] = by_cause.get(key, 0) + 1
    attached = [r for r in failed if (c := classified.get(r.run)) and c.diagnostic]
    agree = sum(
        [m.diagnostic_id for m in r.matches] == [classified[r.run].diagnostic]
        for r in attached
    )
    wall = sum(r.duration_s or 0.0 for r in runs if r.duration_kind == "mur")
    aster = sum(r.duration_s or 0.0 for r in runs if r.duration_kind == "aster")
    metrics["measured"] = {
        "runs": len(runs),
        "failures": len(failed),
        "failure_rate": round(len(failed) / len(runs), 4) if runs else None,
        "compute_s": {
            "aster_legacy": round(aster, 1),
            "wall_since_lot41": round(wall, 1),
            "unknown_runs": sum(r.duration_kind == "inconnue" for r in runs),
            "note": (
                "temps Aster mesuré par run_aster pour les exécutions antérieures au "
                "lot 41 (annexe versionnée de l'audit), temps mur d'aster-expert run "
                "(conteneur compris) ensuite : deux grandeurs distinctes, jamais "
                "additionnées"
            ),
        },
        "first_run": runs[0].run if runs else None,
        "last_run": runs[-1].run if runs else None,
        "failures_by_signature": dict(sorted(by_signature.items())),
        "failures_by_cause": dict(sorted(by_cause.items())),
        "automatic_diagnosis": {
            "attached_failures": len(attached),
            "single_match_equal_to_classification": agree,
            "note": (
                "échecs rattachés à un diagnostic pour lesquels la recherche "
                "automatique de la base (signature) propose ce diagnostic et lui seul"
            ),
        },
    }
    return metrics


def write_metrics(repo_root: Path, metrics: dict[str, Any]) -> Path:
    directory = repo_root / METRICS_RELATIVE
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{metrics['project']}.yaml"
    path.write_text(
        "# Métriques du projet (aster-expert rex, lot 42) : « fonction de perte » de "
        "l'outil.\n# Fichier produit : ne pas éditer à la main.\n"
        + yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False, width=88),
        encoding="utf-8",
    )
    return path


def _fmt(value: Any, nature: str | None = None) -> str:
    if value is None:
        return "non renseigné"
    text = f"{value:g}".replace(".", ",") if isinstance(value, float) else str(value)
    if nature == "estimation":
        text += " (estimation)"
    return text


def render_dashboard(repo_root: Path) -> str:
    """Markdown table comparing the projects (one row per metrics file)."""
    directory = repo_root / METRICS_RELATIVE
    rows = []
    for path in sorted(directory.glob("*.yaml")):
        m = yaml.safe_load(path.read_text(encoding="utf-8"))
        b = m.get("baseline") or {}
        meas = m.get("measured") or {}
        interventions = b.get("supervisor_interventions") or {}
        k = m.get("knowledge") or {}
        rate_b = (
            f"{100 * b['failures'] / b['executions']:.1f} %".replace(".", ",")
            if b.get("executions")
            else "—"
        )
        rate_m = (
            f"{100 * meas['failure_rate']:.1f} %".replace(".", ",")
            if meas.get("failure_rate") is not None
            else "—"
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{m['project']}`",
                    _fmt(b.get("lots")),
                    f"{_fmt(b.get('executions'))} / {_fmt(meas.get('runs'))}",
                    f"{rate_b} / {rate_m}",
                    _fmt(b.get("compute_hours")),
                    _fmt(interventions.get("value"), interventions.get("nature")),
                    _fmt(k.get("created")),
                    _fmt(k.get("promoted")),
                ]
            )
            + " |"
        )
    return (
        "# Tableau de bord des projets\n\n"
        "Produit par `aster-expert rex <projet>` (lot 42) à partir de "
        "`connaissances/metriques/*.yaml` : ne pas éditer à la main.\n\n"
        "Les métriques sont la « fonction de perte » de l'outil : d'un projet à "
        "l'autre, le taux d'échec, les interventions du superviseur et le nombre de "
        "lots par ouvrage doivent baisser. « Base » : chiffres déclarés (audit du "
        "lot 40) ; « mesuré » : recompté par `rex` sur les archives d'exécution "
        "(toutes les exécutions attribuées au projet, y compris après l'audit).\n\n"
        "| Projet | Lots (base) | Exécutions (base / mesuré) | Taux d'échec (base / "
        "mesuré) | Calcul (h, base) | Interventions du superviseur | Connaissances "
        "créées | Promues |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n"
    )


def write_dashboard(repo_root: Path) -> Path:
    path = repo_root / METRICS_RELATIVE / DASHBOARD_NAME
    path.write_text(render_dashboard(repo_root), encoding="utf-8")
    return path


def record_review(
    repo_root: Path, report: RexReport, *, lot: str, today: dt.date | None = None
) -> Path:
    registry = load_registry(repo_root, report.project)
    measured = report.metrics.get("measured") or {}
    review = Review(
        date=today or dt.date.today(),
        lot=lot,
        runs=report.runs,
        failures=len(report.failures),
        unclassified=len(report.blocking),
        last_run=measured.get("last_run"),
    )
    updated = registry.model_copy(update={"reviews": (*registry.reviews, review)})
    return write_registry(repo_root, RexRegistry.model_validate(updated.model_dump()))


def render_report(report: RexReport) -> list[str]:
    lines = [f"Retour d'expérience du projet {report.project}"]
    if not report.archives_present:
        lines.append(
            "Archives d'exécution absentes (data/processed/runs/ : profil cloud ou "
            "clone neuf) : aucun échec examiné, métriques mesurées non recalculées."
        )
    else:
        lines.append(
            f"Exécutions attribuées au projet : {report.runs} ; échecs : "
            f"{len(report.failures)} ; depuis le dernier retour d'expérience "
            f"({report.last_review or 'aucun'}) : {report.since_last_review}."
        )
        by_decision: dict[str, int] = {}
        for f in report.failures:
            key = f.classification.decision if f.classification else "non classé"
            by_decision[key] = by_decision.get(key, 0) + 1
        lines.append(
            "Classement : "
            + ", ".join(f"{k} {v}" for k, v in sorted(by_decision.items()))
            + "."
        )
        causes = (report.metrics.get("measured") or {}).get("failures_by_cause", {})
        auto = (report.metrics.get("measured") or {}).get("automatic_diagnosis", {})
        if auto:
            lines.append(
                "Diagnostic retrouvé automatiquement par la base (seul et égal au "
                f"classement) : {auto['single_match_equal_to_classification']}/"
                f"{auto['attached_failures']} échecs rattachés."
            )
        lines.append(
            "Répartition par cause : "
            + ", ".join(f"{k} {v}" for k, v in causes.items())
            + "."
        )
        for f in report.blocking:
            hint = (
                f" ; diagnostics possibles : {', '.join(f.suggestions)}"
                if (f.suggestions)
                else ""
            )
            lines.append(
                f"  BLOQUANT {f.run} {f.comm} {f.signature} : {f.problem}{hint}"
            )
        for run in report.unknown_classified_runs:
            lines.append(f"  (classement d'une exécution introuvable : {run})")
    lines.append(
        f"Constats de la fiche à verser dans la base : {len(report.constat_proposals)}."
    )
    for p in report.constat_proposals:
        lines.append(f"  point {p.point_label} : {p.topic}")
    lines.append(
        f"Candidats patrons dans le code du projet : {len(report.pattern_candidates)}."
    )
    for c in report.pattern_candidates:
        lines.append(
            f"  {c.path}:{c.function} — {c.kind}"
            + (f" ({c.closest}, similarité {c.similarity})" if c.closest else "")
        )
    k = report.metrics.get("knowledge", {})
    lines.append(
        f"Connaissances créées par le projet : {k.get('created')} ; promues : "
        f"{k.get('promoted')}."
    )
    calls = report.metrics.get("consultations", {}).get("calls", {})
    lines.append(
        "Consultations journalisées (tous projets) : "
        + ", ".join(f"{t} {n}" for t, n in calls.items())
        + "."
    )
    if report.archives_present:
        verdict = (
            f"{len(report.blocking)} échec(s) non classé(s) : clôture du lot bloquée."
            if report.blocking
            else "Tous les échecs sont classés : clôture possible."
        )
        lines.append(verdict)
    return lines


__all__ = [
    "METRICS_RELATIVE",
    "REX_RELATIVE",
    "Classification",
    "RexRegistry",
    "RexReport",
    "RunSummary",
    "compute_metrics",
    "constat_proposals",
    "load_registry",
    "pattern_candidates",
    "project_runs",
    "read_log_tolerant",
    "record_review",
    "render_dashboard",
    "render_report",
    "review_project",
    "write_dashboard",
    "write_metrics",
    "write_registry",
]
