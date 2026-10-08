"""`aster-expert projet exporter-resultats <nom>`: a versionable results package
(lot 45).

The steps of a project leave their outputs in `projets/<nom>/resultats/`, which
is not versioned, next to archives of executions (`data/processed/runs/`) that
only the machine which ran them holds. The results notes are written where
neither exists (the Cloud): this module copies, into
`projets/<nom>/resultats/<output>/` (default `paquet/`), what a note may read:

- the files the declaration lists (`results_package.items`), by section --
  tables (CSV, JSON), existing figures (PNG), text reports (TXT) -- never a MED
  file, refused by suffix and by the HDF5 signature;
- the execution reports (`compte_rendu.json`) of the project's execution and of
  its reinforcement executions, the `mesh check` report and the level B report;
- `paquet.json`: fingerprints of the fiche, the data, the `.comm`, the mesh and
  the execution, the coherence checks between them, the regeneration of the
  `.comm` from the versioned fiche and data, the commits that introduced the
  criteria documents, and the validation level reached, stated level by level
  with the reason it stops where it stops.

Nothing is computed again: the package states what the steps produced. The
ceiling is 20 Mo per project (`PACKAGE_MAX_BYTES`); a larger package is refused
and nothing is written.

Conservation of a level (rule decided by MM, lot 45): a level stays acquired for a
`.comm` whose content, comments and header removed, is identical to the one that
obtained it (`normalize_comm`); otherwise the level must be replayed with the
original criteria, without rewriting them. No judgement is made on the influence of
a parameter: a changed value is a changed `.comm`. A criteria document committed
after the execution, or in a commit that also holds execution evidence, is flagged
(`anteriorite_demontrable`). `reevaluate_package` applies both to an existing
package from its own files, without the working archives (the Cloud has none).
"""

from __future__ import annotations

import difflib
import hashlib
import io
import json
import shutil
import subprocess
import tokenize
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import PackageItem, ResultsPackageSection
from aster_expert.projet.errors import ProjectError

MANIFEST_NAME = "paquet.json"
ALLOWED_SUFFIXES = {
    ".csv": "tableau",
    ".json": "tableau",
    ".png": "figure",
    ".txt": "texte",
}
MED_SUFFIXES = (".med", ".mmed", ".rmed")
_HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"
_MAX_DIFF_LINES = 40
CONSERVATION_RULE = (
    "Un niveau reste acquis pour un .comm dont le contenu, commentaires et en-tête "
    "retirés, est identique à celui qui l'a obtenu ; sinon le niveau doit être "
    "rejoué, avec les critères d'origine, sans les réécrire. Aucun jugement sur "
    "l'influence d'un paramètre."
)
# Paths whose presence in the commit that introduced a criteria document shows that
# results were committed with it (the order of writing is then not demonstrable).
_EVIDENCE_NAMES = (
    "mess",
    "compte_rendu",
    "executions",
    "listing",
    "resultats",
    "rapports",
)
_NOT_EVIDENCE_PREFIXES = ("docs/", "tests/", "src/", "scripts/", "config/")
_NOT_EVIDENCE_SUFFIXES = (".py", ".md", ".yaml", ".yml", ".toml")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(root.resolve()):
        return resolved.relative_to(root.resolve()).as_posix()
    return str(resolved)


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return done.stdout


def _is_med(path: Path) -> bool:
    if path.suffix.lower() in MED_SUFFIXES:
        return True
    with path.open("rb") as stream:
        return stream.read(len(_HDF5_SIGNATURE)) == _HDF5_SIGNATURE


def _strip_comments(text: str) -> list[str]:
    """Lines of `text` without their comments (tokenizer; a naive per-line scan
    that respects quotes if the text is not valid Python)."""
    lines = text.splitlines()
    cuts: dict[int, int] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                cuts[token.start[0] - 1] = token.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        cuts = {}
        for index, line in enumerate(lines):
            quote = ""
            for column, char in enumerate(line):
                if quote:
                    quote = "" if char == quote else quote
                elif char in "\"'":
                    quote = char
                elif char == "#":
                    cuts[index] = column
                    break
    return [line[: cuts[i]] if i in cuts else line for i, line in enumerate(lines)]


def normalize_comm(text: str) -> str:
    """The content of a `.comm` for the conservation rule: comments (header
    included, it is made of comments), trailing spaces and blank lines removed."""
    kept = (line.rstrip() for line in _strip_comments(text))
    return "\n".join(line for line in kept if line.strip())


def comm_content_sha256(text: str) -> str:
    return hashlib.sha256(normalize_comm(text).encode("utf-8")).hexdigest()


def lines_only_comments(difference: list[str]) -> bool | None:
    """Whether a recorded difference (`-`/`+` lines of `_comm_difference`) touches
    comments only: the removed and the added lines are equal once comments are
    removed. `None` when the difference was truncated (undecidable)."""
    if any(line.startswith("... (") for line in difference):
        return None
    removed = [line[1:] for line in difference if line.startswith("-")]
    added = [line[1:] for line in difference if line.startswith("+")]

    def content(lines: list[str]) -> list[str]:
        return [x.rstrip() for x in _strip_comments("\n".join(lines)) if x.strip()]

    return content(removed) == content(added)


def compare_comm(reference: str, other: str) -> dict[str, Any]:
    """The conservation rule on two `.comm` texts."""
    same_bytes = reference == other
    same_content = normalize_comm(reference) == normalize_comm(other)
    return {
        "identique_octets": same_bytes,
        "identique_hors_commentaires": same_content,
        "empreinte_hors_commentaires": comm_content_sha256(other),
        "difference": [] if same_bytes else _comm_difference(reference, other),
    }


@dataclass
class _Copy:
    source: Path
    destination: str
    section: str
    label: str | None


@dataclass
class PackageResult:
    """What the export wrote."""

    directory: Path
    manifest: dict[str, Any]
    lines: list[str] = field(default_factory=list)


def _require_file(value: str | None, what: str, step: str) -> Path:
    if value is None:
        message = f"{what} inconnu : lancer d'abord l'étape « {step} »"
        raise ProjectError(message)
    path = Path(value)
    if not path.is_file() and not path.is_dir():
        message = f"{what} introuvable : {path} (relancer l'étape « {step} »)"
        raise ProjectError(message)
    return path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        message = f"fichier JSON illisible : {path} : {exc}"
        raise ProjectError(message) from exc
    if not isinstance(data, dict):
        message = f"fichier JSON qui n'est pas un objet : {path}"
        raise ProjectError(message)
    return data


def _check(label: str, expected: object, obtained: object) -> dict[str, Any]:
    return {
        "controle": label,
        "attendu": expected,
        "obtenu": obtained,
        "ok": expected == obtained,
    }


def _matches(ctx: ProjectContext, item: PackageItem) -> list[Path]:
    pattern = item.source
    if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        message = f"paquet : source {pattern!r} hors du répertoire du projet"
        raise ProjectError(message)
    found = sorted(p for p in ctx.project_dir.glob(pattern) if p.is_file())
    if not found and item.required:
        message = (
            f"paquet : aucun fichier pour {pattern!r} (section {item.section}) ; "
            "lancer d'abord l'étape qui le produit, ou le déclarer `required: false`"
        )
        raise ProjectError(message)
    return found


def _plan_copies(
    ctx: ProjectContext,
    section: ResultsPackageSection,
    automatic: list[_Copy],
) -> list[_Copy]:
    copies = list(automatic)
    for item in section.items:
        for path in _matches(ctx, item):
            copies.append(
                _Copy(
                    source=path,
                    destination=f"{item.section}/{path.name}",
                    section=item.section,
                    label=item.label,
                )
            )
    seen: dict[str, Path] = {}
    for copy in copies:
        suffix = copy.source.suffix.lower()
        if _is_med(copy.source):
            message = f"paquet : fichier MED refusé ({copy.source}) : jamais de MED"
            raise ProjectError(message)
        if suffix not in ALLOWED_SUFFIXES:
            allowed = ", ".join(sorted(ALLOWED_SUFFIXES))
            message = (
                f"paquet : {copy.source.name} refusé, extensions admises : {allowed}"
            )
            raise ProjectError(message)
        other = seen.get(copy.destination)
        if other is not None and other.resolve() != copy.source.resolve():
            message = (
                f"paquet : deux fichiers pour {copy.destination} ({other} et "
                f"{copy.source}) : les déclarer dans deux sections"
            )
            raise ProjectError(message)
        seen[copy.destination] = copy.source
    unique: dict[str, _Copy] = {c.destination: c for c in copies}
    return [unique[k] for k in sorted(unique)]


def _commit_files(repo_root: Path, commit: str) -> list[str]:
    out = _git(repo_root, "show", "--name-only", "--format=", commit)
    return [line for line in (out or "").splitlines() if line.strip()]


def _execution_evidence(files: list[str], document: str) -> list[str]:
    """Files of a commit that look like execution results (listings, reports of
    execution, results tables), documentation, code and configuration aside."""
    found = []
    for name in files:
        lowered = name.lower()
        if (
            name == document
            or lowered.startswith(_NOT_EVIDENCE_PREFIXES)
            or lowered.endswith(_NOT_EVIDENCE_SUFFIXES)
        ):
            continue
        if any(word in lowered for word in _EVIDENCE_NAMES):
            found.append(name)
    return found


def _after(date: str | None, executed_at: str | None) -> bool | None:
    if date is None or executed_at is None:
        return None
    try:
        committed = datetime.fromisoformat(date)
        executed = datetime.fromisoformat(executed_at)
    except ValueError:
        return None
    if executed.tzinfo is None:
        executed = executed.replace(tzinfo=UTC)
    return committed > executed


def flag_criterion(
    entry: dict[str, Any], files: list[str], executed_at: str | None
) -> dict[str, Any]:
    """Whether the order « criteria written, then execution » can be shown from the
    commit history: the commit must precede the execution and must not hold
    execution results with the document."""
    evidence = _execution_evidence(files, entry["document"])
    after = _after(entry.get("date"), executed_at)
    reasons = []
    if entry.get("commit_introduction") is None:
        reasons.append("document non versionné ou historique Git absent")
    if after is True:
        reasons.append("commité après l'exécution")
    elif after is None and entry.get("commit_introduction") is not None:
        reasons.append("date d'exécution inconnue")
    if evidence:
        reasons.append(
            f"commité avec des résultats d'exécution ({len(evidence)} fichier(s) : "
            f"{', '.join(evidence[:3])}{', ...' if len(evidence) > 3 else ''})"
        )
    entry["posterieur_a_l_execution"] = after
    entry["resultats_dans_le_commit"] = evidence
    entry["anteriorite_demontrable"] = not reasons
    entry["anteriorite_motif"] = (
        "commit antérieur à l'exécution, sans résultat d'exécution dans le commit"
        if not reasons
        else " ; ".join(reasons) + " : antériorité non démontrable"
    )
    return entry


def _criteria(
    ctx: ProjectContext, section: ResultsPackageSection, executed_at: str | None
) -> list[Any]:
    out = []
    for criterion in section.criteria:
        document = ctx.repo_root / criterion.document
        if not document.is_file():
            message = f"paquet : document de critères introuvable : {document}"
            raise ProjectError(message)
        log = _git(
            ctx.repo_root,
            "log",
            "--diff-filter=A",
            "--format=%H%x09%aI%x09%s",
            "--",
            criterion.document,
        )
        first = (log or "").strip().splitlines()
        entry: dict[str, Any] = {
            "niveau": criterion.level,
            "document": criterion.document,
            "document_sha256": _sha(document),
        }
        files: list[str] = []
        if first:
            commit, date, subject = first[-1].split("\t", 2)
            entry.update(
                {"commit_introduction": commit, "date": date, "message": subject}
            )
            files = _commit_files(ctx.repo_root, commit)
        else:
            entry.update(
                {
                    "commit_introduction": None,
                    "date": None,
                    "message": "document non versionné ou historique Git absent",
                }
            )
        out.append(flag_criterion(entry, files, executed_at))
    return out


def _regenerate(ctx: ProjectContext, rt: Any, mesh: Path, executed: Path) -> Any:
    """Regenerate the `.comm` in memory from the versioned fiche and data, and
    compare it to the executed one (nothing is written): `difference` lists the
    lines of the executed `.comm` (`-`) that the regenerated one (`+`) changes."""
    d = ctx.declaration
    if d.comm.generator is None:
        return {"statut": "sans_objet", "motif": "`.comm` écrit à la main"}
    blockers = ctx.blockers_for("generer")
    if blockers:
        return {"statut": "refusee", "motif": list(blockers)}
    try:
        _, version = rt.aster()
        text, _ = ctx.extension(d.comm.generator)(
            ctx,
            fiche_path=ctx.fiche_path,
            data_path=ctx.data_path,
            med_path=mesh,
            aster_version=version,
        )
    except (ProjectError, ValueError) as exc:
        return {"statut": "refusee", "motif": str(exc)}
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    old_text = executed.read_text(encoding="utf-8")
    comparison = compare_comm(old_text, text)
    return {
        "statut": "identique" if comparison["identique_octets"] else "different",
        "sha256": sha,
        "identique_hors_commentaires": comparison["identique_hors_commentaires"],
        "empreinte_hors_commentaires": comparison["empreinte_hors_commentaires"],
        "difference": comparison["difference"],
    }


def _comm_difference(reference: str, executed: str) -> list[str]:
    """Lines removed (`-`, reference side) and added (`+`, packaged side)."""
    diff = difflib.unified_diff(
        reference.splitlines(),
        executed.splitlines(),
        fromfile="reference",
        tofile="paquet",
        n=0,
        lineterm="",
    )
    lines = [line for line in diff if not line.startswith(("---", "+++", "@@"))]
    if len(lines) > _MAX_DIFF_LINES:
        omitted = len(lines) - _MAX_DIFF_LINES
        return [*lines[:_MAX_DIFF_LINES], f"... ({omitted} lignes de plus)"]
    return lines


def _level_e(
    ctx: ProjectContext, section: ResultsPackageSection, run_comm: Path
) -> dict[str, Any] | None:
    spec = section.level_e
    if spec is None:
        return None
    results_path = ctx.path(spec.results)
    data = _read_json(results_path)
    verdicts = data.get("verdicts")
    if not isinstance(verdicts, dict) or not verdicts:
        message = f"niveau E : {results_path} sans `verdicts`"
        raise ProjectError(message)
    by_id = {
        key: value.get("verdict") if isinstance(value, dict) else None
        for key, value in verdicts.items()
    }
    missing = [i for i in spec.criteria_ids if i not in by_id]
    if missing:
        message = (
            f"niveau E : critères absents de {results_path} : {', '.join(missing)}"
        )
        raise ProjectError(message)
    entry: dict[str, Any] = {
        "resultats": spec.results,
        "resultats_sha256": _sha(results_path),
        "criteres_niveau_e": list(spec.criteria_ids),
        "verdicts": by_id,
        "tous_reussis": all(by_id[i] == "RÉUSSI" for i in spec.criteria_ids),
    }
    if spec.comm is not None:
        reference = ctx.path(spec.comm)
        if not reference.is_file():
            message = f"niveau E : .comm de référence introuvable : {reference}"
            raise ProjectError(message)
        comparison = compare_comm(
            reference.read_text(encoding="utf-8"),
            run_comm.read_text(encoding="utf-8"),
        )
        entry["comm_reference"] = spec.comm
        entry["comm_reference_sha256"] = _sha(reference)
        entry["comm_execute_sha256"] = _sha(run_comm)
        entry["comm_execute_hors_commentaires_sha256"] = comparison[
            "empreinte_hors_commentaires"
        ]
        entry["meme_comm_octets"] = comparison["identique_octets"]
        entry["meme_comm_que_l_execution"] = comparison["identique_hors_commentaires"]
        entry["difference_comm"] = comparison["difference"]
    else:
        entry["meme_comm_que_l_execution"] = None
    return entry


def _validation_counts(validation: dict[str, Any]) -> tuple[Any, Any, Any]:
    """(checked, total, errors) of a level B validation: the summary kept in the
    state (counts) or the full report copied in the package (lists)."""
    checked = validation.get("commands_checked")
    if isinstance(checked, list):
        not_checked = validation.get("commands_not_checked") or []
        return (
            len(checked),
            len(checked) + len(not_checked),
            len(validation.get("errors") or []),
        )
    return checked, validation.get("commands_total"), validation.get("errors")


def _levels(
    validation: dict[str, Any],
    report: dict[str, Any],
    comm_ok: bool,
    controls: dict[str, Any] | None,
    controls_attached: bool,
    level_e: dict[str, Any] | None,
    regeneration: dict[str, Any] | None,
    comm_rule: str | None = None,
) -> dict[str, Any]:
    """Each level, reached or not, with its reason; the level reached is the
    highest of an unbroken sequence from B. The conservation rule decides whether
    the levels hold for the `.comm` regenerated from the current fiche."""
    steps: list[dict[str, Any]] = []
    b_ok = validation.get("valid") is True and validation.get("validation_level") == "B"
    steps.append(
        {
            "niveau": "B",
            "atteint": b_ok,
            "motif": (
                "{}/{} commandes confrontées au catalogue, {} erreur(s)".format(
                    *_validation_counts(validation)
                )
                if validation
                else "aucune validation de niveau B consignée"
            ),
        }
    )
    status = report.get("status")
    c_ok = status in ("completed_ok", "completed_with_alarms") and comm_ok
    steps.append(
        {
            "niveau": "C",
            "atteint": c_ok,
            "motif": (
                f"exécution {status} ({report.get('diag')}) ; .comm du projet "
                + ("identique" if comm_ok else "DIFFÉRENT")
                + " de celui de l'exécution"
                + (f" ({comm_rule})" if comm_rule and comm_ok else "")
            ),
        }
    )
    if controls is None:
        steps.append(
            {"niveau": "D", "atteint": False, "motif": "aucun contrôle D consigné"}
        )
    else:
        verdict = controls.get("verdict")
        steps.append(
            {
                "niveau": "D",
                "atteint": verdict == "RÉUSSI" and controls_attached,
                "motif": (
                    f"contrôles D : {verdict} (seuil {controls.get('threshold')}) ; "
                    + (
                        "rattachés à l'exécution du paquet par leurs empreintes"
                        if controls_attached
                        else "NON rattachés à l'exécution du paquet (empreintes "
                        "absentes ou différentes : relancer l'étape « controles »)"
                    )
                ),
            }
        )
    if level_e is None:
        steps.append(
            {"niveau": "E", "atteint": False, "motif": "aucune référence déclarée"}
        )
    else:
        same = level_e.get("meme_comm_que_l_execution")
        e_ok = level_e["tous_reussis"] and same is True
        if not level_e["tous_reussis"]:
            reason = (
                "comparaison à la référence : au moins un critère de niveau E en échec"
            )
        elif same is True:
            reason = (
                "critères réussis sur un .comm identique à celui de l'exécution du "
                "paquet"
                + (
                    ""
                    if level_e.get("meme_comm_octets") is not False
                    else " hors commentaires et en-tête (règle de conservation)"
                )
            )
        elif same is False:
            n = len(level_e["difference_comm"])
            reason = (
                "niveau E obtenu sur le .comm d'empreinte "
                f"{level_e.get('comm_reference_sha256')}, à rejouer : le .comm de "
                f"l'exécution du paquet (empreinte {level_e.get('comm_execute_sha256')}"
                f") en diffère hors commentaires ({n} ligne(s) de différence, "
                "`difference_comm`) ; le niveau E ne se reporte pas"
            )
        else:
            reason = "critères réussis ; .comm de référence non déclaré"
        steps.append({"niveau": "E", "atteint": e_ok, "motif": reason})
    reached = None
    for step in steps:
        if not step["atteint"]:
            break
        reached = step["niveau"]
    out: dict[str, Any] = {"atteint": reached, "par_niveau": steps}
    out["regle_de_conservation"] = CONSERVATION_RULE
    if regeneration is not None and regeneration.get("statut") in (
        "identique",
        "different",
    ):
        if regeneration["statut"] == "identique":
            holds: bool | None = True
            why = "le .comm régénéré de la fiche et des données actuelles est identique"
        elif regeneration.get("identique_hors_commentaires") is True:
            holds = True
            why = (
                "le .comm régénéré ne diffère de l'exécuté que par des commentaires "
                "ou l'en-tête : les niveaux atteints sont conservés (règle de "
                "conservation)"
            )
        elif regeneration.get("identique_hors_commentaires") is False:
            holds = False
            why = (
                "le .comm régénéré diffère de l'exécuté hors commentaires : les "
                "niveaux ne se reportent pas, à rejouer avec les critères d'origine"
            )
        else:
            holds = None
            why = "différence tronquée : conservation non décidable"
        out["conservation"] = {"valable": holds, "motif": why}
    return out


def export_results(
    ctx: ProjectContext, rt: Any, *, regenerate: bool = True
) -> PackageResult:
    """Write the results package of the project (see the module docstring)."""
    from aster_expert.projet.pipeline import load_state  # noqa: PLC0415

    d = ctx.declaration
    section = d.results_package
    if section is None:
        message = (
            f"le projet {d.name} ne déclare pas de paquet de résultats "
            "(`results_package` dans projet.yaml)"
        )
        raise ProjectError(message)
    state = load_state(ctx)
    comm = _require_file(state.comm, ".comm", "generer")
    mesh = _require_file(state.mesh_med, "maillage vérifié", "maillage")
    run_dir = _require_file(state.execution_dir, "répertoire d'exécution", "executer")
    record_path = run_dir / "compte_rendu.json"
    if not record_path.is_file():
        message = f"compte rendu d'exécution absent : {record_path}"
        raise ProjectError(message)
    record = _read_json(record_path)
    report = record.get("report", {})
    inputs = record.get("inputs_sha256", {})
    mess = run_dir / "proc.0" / "fort.6"
    run_comm = run_dir / comm.name
    root = ctx.repo_root

    comm_sha = _sha(comm)
    mesh_sha = _sha(mesh)
    mess_sha = _sha(mess) if mess.is_file() else None
    mesh_copy = f"{comm.stem}.{d.comm.export.mesh_format}"
    checks: dict[str, dict[str, Any]] = {
        "comm_execute": _check(
            ".comm du projet = .comm de l'exécution", comm_sha, inputs.get(comm.name)
        ),
        "maillage_execute": _check(
            "maillage vérifié = maillage de l'exécution",
            mesh_sha,
            inputs.get(mesh_copy),
        ),
    }
    if not checks["comm_execute"]["ok"] and run_comm.is_file():
        # Lot 49 : règle de conservation d'un niveau (lot 45) appliquée au niveau C ; un
        # .comm identique hors commentaires et en-tête (l'en-tête porte l'empreinte de
        # la fiche) garde le niveau de son exécution, et le dit.
        same = normalize_comm(comm.read_text(encoding="utf-8")) == normalize_comm(
            run_comm.read_text(encoding="utf-8")
        )
        checks["comm_execute"]["ok"] = same
        checks["comm_execute"]["regle"] = (
            "identique hors commentaires et en-tête (règle de conservation, lot 45)"
            if same
            else "différent hors commentaires et en-tête"
        )

    controls_path = ctx.results_dir / "controles" / "controles_d.json"
    controls = _read_json(controls_path) if controls_path.is_file() else None
    if controls is not None:
        provenance = controls.get("provenance") or {}
        checks["controles_mess"] = _check(
            "contrôles D faits sur le .mess de l'exécution",
            mess_sha,
            provenance.get("mess_sha256"),
        )
        checks["controles_comm"] = _check(
            "contrôles D faits sur le .comm de l'exécution",
            _sha(run_comm) if run_comm.is_file() else None,
            provenance.get("comm_sha256"),
        )

    automatic = [
        _Copy(record_path, "execution/compte_rendu.json", "execution", None),
    ]
    rebar: dict[str, Any] = {}
    for group, directory in sorted(state.rebar_executions.items()):
        rebar_record = Path(directory) / "compte_rendu.json"
        if not rebar_record.is_file():
            message = f"compte rendu d'exécution absent : {rebar_record}"
            raise ProjectError(message)
        content = _read_json(rebar_record)
        automatic.append(
            _Copy(
                rebar_record,
                f"execution/compte_rendu_ferraillage_{group}.json",
                "execution",
                None,
            )
        )
        rebar[group] = {
            "repertoire": _rel(Path(directory), root),
            "compte_rendu_sha256": _sha(rebar_record),
            "entrees_sha256": content.get("inputs_sha256", {}),
            "statut": content.get("report", {}).get("status"),
            "diagnostic": content.get("report", {}).get("diag"),
        }
    if state.mesh_check_report is not None and Path(state.mesh_check_report).is_file():
        automatic.append(
            _Copy(
                Path(state.mesh_check_report),
                "maillage/rapport_mesh_check.txt",
                "maillage",
                None,
            )
        )
    validation_path = ctx.results_dir / "validation.json"
    if validation_path.is_file():
        automatic.append(
            _Copy(validation_path, "validation/validation.json", "validation", None)
        )
    copies = _plan_copies(ctx, section, automatic)

    total = sum(c.source.stat().st_size for c in copies)
    if total > section.max_bytes:
        message = (
            f"paquet de {total} octets, plafond {section.max_bytes} : retirer des "
            "fichiers de la déclaration (`results_package.items`)"
        )
        raise ProjectError(message)

    level_e = _level_e(ctx, section, run_comm) if run_comm.is_file() else None
    regeneration = (
        _regenerate(ctx, rt, mesh, comm) if regenerate else {"statut": "non_demandee"}
    )
    head = (_git(root, "rev-parse", "HEAD") or "").strip() or None
    dirty = _git(root, "status", "--porcelain")
    files = [
        {
            "chemin": c.destination,
            "section": c.section,
            "type": ALLOWED_SUFFIXES[c.source.suffix.lower()],
            "source": _rel(c.source, root),
            "libelle": c.label,
            "octets": c.source.stat().st_size,
            "sha256": _sha(c.source),
        }
        for c in copies
    ]
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "projet": d.name,
        "ouvrage": d.structure,
        "exporte_le": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "depot": {
            "commit": head,
            "arbre_modifie": None if dirty is None else bool(dirty.strip()),
        },
        "code_aster": {
            "version": report.get("aster_version"),
            "image_digest": report.get("image_digest"),
        },
        "empreintes": {
            "fiche": {
                "chemin": _rel(ctx.fiche_path, root),
                "sha256": _sha(ctx.fiche_path),
            },
            "donnees": {
                "chemin": _rel(ctx.data_path, root),
                "sha256": _sha(ctx.data_path),
            },
            "comm": {"chemin": _rel(comm, root), "sha256": comm_sha},
            "maillage": {"chemin": _rel(mesh, root), "sha256": mesh_sha},
            "execution": {
                "repertoire": _rel(run_dir, root),
                "compte_rendu_sha256": _sha(record_path),
                "mess_sha256": mess_sha,
                "entrees_sha256": inputs,
                "statut": report.get("status"),
                "diagnostic": report.get("diag"),
                "duree_s": report.get("duration_s"),
                "execute_le": report.get("executed_at"),
            },
            "executions_ferraillage": rebar,
        },
        "coherence": list(checks.values()),
        "regeneration_comm": regeneration,
        "criteres": _criteria(ctx, section, report.get("executed_at")),
        "niveau_e": level_e,
        "niveau": _levels(
            state.validation or {},
            report,
            checks["comm_execute"]["ok"],
            controls,
            checks.get("controles_mess", {}).get("ok", False)
            and checks.get("controles_comm", {}).get("ok", False),
            level_e,
            regeneration,
            comm_rule=checks["comm_execute"].get("regle"),
        ),
        "sections": sorted({c.section for c in copies}),
        "fichiers": files,
        "taille_octets": total,
        "plafond_octets": section.max_bytes,
    }

    target = ctx.results_dir / section.output
    if not target.resolve().is_relative_to(ctx.results_dir.resolve()):
        message = f"paquet : {target} hors du répertoire de résultats"
        raise ProjectError(message)
    staging = target.with_name(target.name + ".en_cours")
    if staging.exists():
        shutil.rmtree(staging)
    for c in copies:
        destination = staging / c.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(c.source, destination)
    (staging / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)

    lines = [
        f"Paquet de résultats : {target} ({len(files)} fichiers, {total} octets, "
        f"plafond {section.max_bytes})",
        f"Sections : {', '.join(manifest['sections'])}",
    ]
    for check in checks.values():
        lines.append(f"  {'OK' if check['ok'] else 'ÉCART'} {check['controle']}")
    lines.append(f"Régénération du .comm : {regeneration['statut']}")
    lines.extend(f"    {line}" for line in regeneration.get("difference", []))
    for step in manifest["niveau"]["par_niveau"]:
        mark = "atteint" if step["atteint"] else "non atteint"
        lines.append(f"  Niveau {step['niveau']} {mark} : {step['motif']}")
    lines.extend(_summary_lines(manifest))
    return PackageResult(directory=target, manifest=manifest, lines=lines)


def _summary_lines(manifest: dict[str, Any]) -> list[str]:
    lines = []
    conservation = manifest["niveau"].get("conservation")
    if conservation is not None:
        lines.append(f"Conservation des niveaux : {conservation['motif']}")
    for criterion in manifest["criteres"]:
        if not criterion.get("anteriorite_demontrable", True):
            lines.append(
                f"  CRITÈRE {criterion['niveau']} {criterion['document']} : "
                f"{criterion['anteriorite_motif']}"
            )
    lines.append(f"Niveau atteint : {manifest['niveau']['atteint'] or 'aucun'}")
    return lines


def _read_optional(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.is_file() else None


def _reconstruct_executed_comm(
    ctx: ProjectContext, manifest: dict[str, Any]
) -> str | None:
    """The executed `.comm`, regenerated from the versioned fiche and data, when its
    SHA-256 is the one the package recorded for the executed file (so it **is** that
    file, byte for byte); `None` otherwise (the working archive is not here)."""
    d = ctx.declaration
    if d.comm.generator is None:
        return None
    mesh_name = Path(manifest["empreintes"]["maillage"]["chemin"])
    try:
        text, _ = ctx.extension(d.comm.generator)(
            ctx,
            fiche_path=ctx.fiche_path,
            data_path=ctx.data_path,
            med_path=mesh_name,
            aster_version=manifest["code_aster"]["version"],
        )
    except (ProjectError, ValueError, OSError):
        return None
    recorded = manifest["empreintes"]["comm"]["sha256"]
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != recorded:
        return None
    return str(text)


def _refresh_level_e(
    ctx: ProjectContext,
    manifest: dict[str, Any],
    directory: Path,
    section: ResultsPackageSection,
) -> dict[str, Any] | None:
    """Level E declared today (results, criteria, reference `.comm`), judged against
    the executed `.comm` reconstructed from the package's fingerprint; the versioned
    reference files of the `niveau_e` section are copied into the package. `None`
    when the executed `.comm` cannot be established (the recorded level E stays)."""
    executed = _reconstruct_executed_comm(ctx, manifest)
    if executed is None:
        return None
    scratch = directory.with_name(directory.name + ".comm_reconstruit")
    scratch.mkdir(exist_ok=True)
    try:
        comm = scratch / "executed.comm"
        comm.write_text(executed, encoding="utf-8")
        entry = _level_e(ctx, section, comm)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    known = {f["chemin"]: f for f in manifest["fichiers"]}
    for item in section.items:
        if item.section != "niveau_e":
            continue
        for source in _matches(ctx, item):
            destination = f"niveau_e/{source.name}"
            target = directory / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            known[destination] = {
                "chemin": destination,
                "section": "niveau_e",
                "type": ALLOWED_SUFFIXES[source.suffix.lower()],
                "source": _rel(source, ctx.repo_root),
                "libelle": item.label,
                "octets": source.stat().st_size,
                "sha256": _sha(source),
            }
    manifest["fichiers"] = [known[k] for k in sorted(known)]
    manifest["taille_octets"] = sum(f["octets"] for f in manifest["fichiers"])
    manifest["sections"] = sorted({f["section"] for f in manifest["fichiers"]})
    return entry


def reevaluate_package(
    directory: Path, repo_root: Path, ctx: ProjectContext | None = None
) -> PackageResult:
    """Re-apply the conservation rule and the criteria flags to an existing package,
    from its own files and the Git history (no working archive, no execution):
    `paquet.json` is rewritten. With the project (`ctx`), the level E declared today
    is judged too (see `_refresh_level_e`); the files of the package are otherwise
    untouched."""
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        message = f"paquet absent : {manifest_path} (lancer d'abord l'export)"
        raise ProjectError(message)
    manifest = _read_json(manifest_path)
    report = _read_json(directory / "execution" / "compte_rendu.json").get("report", {})
    executed_at = manifest["empreintes"]["execution"].get("execute_le") or report.get(
        "executed_at"
    )
    by_label = {c["controle"]: c["ok"] for c in manifest["coherence"]}
    comm_ok = by_label.get(".comm du projet = .comm de l'exécution", False)
    controls = _read_optional(directory / "controles" / "controles_d.json")
    attached = by_label.get(
        "contrôles D faits sur le .mess de l'exécution", False
    ) and by_label.get("contrôles D faits sur le .comm de l'exécution", False)
    for criterion in manifest["criteres"]:
        files = (
            _commit_files(repo_root, criterion["commit_introduction"])
            if criterion.get("commit_introduction")
            else []
        )
        flag_criterion(criterion, files, executed_at)
    regeneration = manifest.get("regeneration_comm")
    if isinstance(regeneration, dict) and regeneration.get("statut") == "different":
        regeneration["identique_hors_commentaires"] = lines_only_comments(
            regeneration.get("difference", [])
        )
    level_e = manifest.get("niveau_e")
    package = ctx.declaration.results_package if ctx is not None else None
    if ctx is not None and package is not None and package.level_e is not None:
        refreshed = _refresh_level_e(ctx, manifest, directory, package)
        if refreshed is not None:
            level_e = manifest["niveau_e"] = refreshed
    if isinstance(level_e, dict) and level_e.get("comm_reference") is not None:
        if level_e.get("meme_comm_octets") is None:
            level_e["meme_comm_octets"] = not level_e.get("difference_comm")
        if level_e["meme_comm_octets"]:
            level_e["meme_comm_que_l_execution"] = True
        else:
            level_e["meme_comm_que_l_execution"] = lines_only_comments(
                level_e.get("difference_comm", [])
            )
        level_e.setdefault(
            "comm_execute_sha256", manifest["empreintes"]["comm"]["sha256"]
        )
    validation = _read_optional(directory / "validation" / "validation.json") or {}
    rule = next(
        (
            c.get("regle")
            for c in manifest.get("coherence", [])
            if c.get("controle") == ".comm du projet = .comm de l'exécution"
        ),
        None,
    )
    manifest["niveau"] = _levels(
        validation,
        report,
        comm_ok,
        controls,
        attached,
        level_e,
        regeneration,
        comm_rule=rule,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return PackageResult(
        directory=directory, manifest=manifest, lines=_summary_lines(manifest)
    )


__all__ = [
    "ALLOWED_SUFFIXES",
    "MANIFEST_NAME",
    "CONSERVATION_RULE",
    "PackageResult",
    "compare_comm",
    "export_results",
    "lines_only_comments",
    "normalize_comm",
    "reevaluate_package",
]
