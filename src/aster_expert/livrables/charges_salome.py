"""`charges.med` and `charges_salome.py`: the loads of a project, to look at in
Salomé-Méca (lot 50 quinquies).

Two deliverables, nothing else (MM, lot 50 quinquies):

- `charges.med` is **the file Code_Aster wrote**, copied byte for byte from
  `resultats/livrables/med/charges.med` (sub-step `traiter`, `IMPR_RESU(FORMAT='MED')`
  of the post-processing run, `postcomm.py`): one field per case, `FN_<case>` (nodal
  forces equivalent to the loads of the case, `CALC_VECT_ELEM(OPTION='CHAR_MECA')` then
  `ASSE_VECTEUR`), `FV_<case>` (nodal forces equivalent to the command variables of a
  thermal case, `CALC_VECT_ELEM(OPTION='FORC_VARC')`, self-balanced) and
  `VARC_<case>_TEMP_1` (the temperature field itself, `IMPR_RESU/RESU/CHAM_GD`). Two
  prefixes because the two kinds of forces come from two options of `CALC_VECT_ELEM`
  (U4.61.02) and a thermal case has no load of its own;
- `charges_salome.py`, short, readable and editable by hand, that MM runs in the ParaVis
  module of Salomé-Méca: arrows at the nodes, one pipeline object `Cas <name>` per case.

The earlier reconditioning of lot 50 quater (16 steps, `CHARGE_REPARTIE`,
`ECART_TEMPERATURE`, static reading of the `.comm`, `.vtu`) is still in
`charges_verif.py`, as the sub-step `charges_avance`, off by default.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.arrondis import format_value, load_table
from aster_expert.livrables.chaine import deliverables_dir, load_deliverables_state
from aster_expert.livrables.charges_salome_modele import SCRIPT_TEMPLATE
from aster_expert.livrables.donnees import Deliverables
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

OUT_NAME = "charges_salome"
MED_NAME = "charges.med"
SCRIPT_NAME = "charges_salome.py"
MECHANICAL = "mécanique"
THERMAL = "thermique"
FORCE_COMPONENTS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")

README = """\
1. Dans {script}, renseigner FICHIER_MED : chemin absolu de {med} dans la VM ({projet}, {version}).
2. Salomé-Méca, module ParaVis : {menu}.
3. {premier} s'affiche ; chaque cas est un objet « Cas <nom> » du navigateur de pipeline.
4. Autre cas : {cas} ; console Python : afficher_cas("<cas>"), ou l'oeil de « Cas <nom> ».
5. Paramètres en tête du script : CAS_AFFICHE, FACTEUR_ECHELLE (m par kN), SOUS_ECHANTILLONNAGE.
"""  # noqa: E501


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --- the cases ----------------------------------------------------------------------


def _total_forces(d: Deliverables, forces: list[str], n_nodes: int) -> Any:
    total = np.zeros((n_nodes, 6))
    wanted = set(forces)
    for name, values, kind, entity, components in d.loads():
        if name not in wanted:
            continue
        if components and tuple(components) != FORCE_COMPONENTS:
            message = f"charges : composantes de {name} inattendues : {components}"
            raise ProjectError(message)
        rows = values.reshape(len(kind), -1)
        total[entity[kind == 0]] += rows[kind == 0]
    return total


def _range_of(d: Deliverables, name: str) -> tuple[float, float] | None:
    for field_name, values, _kind, _entity, _components in d.loads():
        if field_name == name:
            return float(values.min()), float(values.max())
    return None


def read_cases(ctx: ProjectContext, d: Deliverables) -> list[dict[str, Any]]:
    """The cases of the MED of loads, in the order of the post-processing plan; each
    carries its nature, its MED fields and the title (case and resultant in kN)."""
    table = load_table(ctx.repo_root)
    n_nodes = len(d.mesh.coords)
    by_case: dict[str, dict[str, Any]] = {}
    for item in d.plan["charges"]:
        entry = by_case.setdefault(
            item["cas"], {"nom": item["cas"], "forces": None, "temperature": None}
        )
        if item["nature"] in ("forces", "forces_varc"):
            entry["forces"] = item["nom_med"]
            entry["nature"] = MECHANICAL if item["nature"] == "forces" else THERMAL
        elif item["nature"] == "temperature":
            entry["temperature"] = item["nom_med"]
    cases = []
    for entry in by_case.values():
        if entry["forces"] is None:
            message = f"charges : aucun champ de forces nodales pour {entry['nom']}"
            raise ProjectError(message)
        sums = _total_forces(d, [entry["forces"]], n_nodes).sum(axis=0)
        resultant = " ; ".join(
            f"Σ{c} = "
            f"{format_value(float(v) * 1.0e-3, 'kN', table, decimal_comma=True)} kN"
            for c, v in zip(("FX", "FY", "FZ"), sums[:3], strict=True)
        )
        title = f"{entry['nom']} - charge {entry['nature']} - {resultant}"
        if entry["temperature"]:
            span = _range_of(d, entry["temperature"])
            if span is not None:
                low, high = (
                    format_value(v, "°C", table, decimal_comma=True) for v in span
                )
                title += f" - TEMP = {low}" + (f" à {high}" if low != high else "")
        cases.append(
            {**entry, "titre": title, "resultante_n": [float(v) for v in sums[:3]]}
        )
    return cases


# --- the script ---------------------------------------------------------------------


def write_script(cases: list[dict[str, Any]], med_path: Path, out: Path) -> Path:
    """`charges_salome.py`: the template, `FICHIER_MED` and the table of cases."""
    keys = ("nom", "nature", "forces", "temperature", "titre")
    table = (
        "[\n"
        + "".join(
            "    {" + ", ".join(f"{k!r}: {c[k]!r}" for k in keys) + "},\n"
            for c in cases
        )
        + "]"
    )
    text = (
        SCRIPT_TEMPLATE.replace("@@FICHIER_MED@@", repr(str(med_path)))
        .replace("@@PREMIER_CAS@@", cases[0]["nom"])
        .replace("@@CAS@@", table)
    )
    path = out / SCRIPT_NAME
    path.write_text(text, encoding="utf-8")
    compile(text, str(path), "exec")
    return path


_MED_LINE = re.compile(r"^FICHIER_MED = .*$", re.MULTILINE)


def set_med_path(script: Path, med_path: Path) -> None:
    """Only the line `FICHIER_MED = ...` changes, the rest is untouched."""
    text = script.read_text(encoding="utf-8")
    new, count = _MED_LINE.subn(f"FICHIER_MED = {str(med_path)!r}", text)
    if count != 1:
        message = f"{script.name} : la ligne FICHIER_MED est introuvable ou répétée"
        raise ProjectError(message)
    script.write_text(new, encoding="utf-8")


# --- running the script in the Salomé-Méca image -------------------------------------


def run_in_salome(
    ctx: ProjectContext,
    script: Path,
    png_dir: Path,
    *,
    mode: str = "direct",
    cwd_name: str = "autre_dossier",
) -> list[str]:
    """Run `script --png` with `pvbatch` in the Salomé-Méca image (no screen,
    `xvfb-run`). `mode="exec"`: through `exec(open(script).read())` from another working
    directory, without `__file__` (how MM runs it in the ParaVis console). The directory
    of the script and of the MED are mounted at the same path as on the host."""
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415

    salome = load_mesh_config(ctx.repo_root / "config" / "validation.yaml").salome
    image = Path(str(salome.image_path)).expanduser()
    runtime = shutil.which("singularity")
    if runtime is None or not image.is_file():
        message = "rendu PNG : Singularity ou l'image Salomé-Méca absent (VM seulement)"
        raise ProjectError(message)
    png_dir.mkdir(parents=True, exist_ok=True)
    work = png_dir.parent / f"_{cwd_name}"
    work.mkdir(exist_ok=True)
    target = script.name
    if mode == "exec":
        driver = work / "lancement.py"
        driver.write_text(
            f"exec(open({str(script)!r}, encoding='utf-8').read())\n", encoding="utf-8"
        )
        target = str(driver)
    elif mode != "direct":
        message = f"mode inconnu : {mode}"
        raise ProjectError(message)
    here = script.parent if mode == "direct" else work
    command = (
        f"source {salome.install_root}/salome_prerequisites.sh >/dev/null 2>&1; "
        "unset DISPLAY; export HWLOC_COMPONENTS=-gl; "
        f"cd {here} && xvfb-run -a -s '-screen 0 1600x1200x24' pvbatch --no-mpi "
        f"{target} --png /png"
    )
    binds = {script.parent, Path(os.path.realpath(script.parent))}
    argv = [runtime, "exec", "--containall", "--cleanenv", "--no-home"]
    for folder in sorted(binds | {work}):
        argv += ["--bind", f"{folder}:{folder}"]
    argv += ["--bind", f"{png_dir}:/png", str(image), "bash", "-c", command]
    result = subprocess.run(  # noqa: S603 -- fixed argv
        argv, capture_output=True, text=True, timeout=3600, check=False
    )
    (png_dir / f"{script.stem}_{mode}.log").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    shutil.rmtree(work, ignore_errors=True)
    if result.returncode != 0:
        message = (
            f"{script.name} ({mode}) : code {result.returncode} : "
            f"{(result.stderr or result.stdout)[-800:]}"
        )
        raise ProjectError(message)
    return [
        line[6:] for line in result.stdout.splitlines() if line.startswith("[PNG] ")
    ]


# --- the sub-step -------------------------------------------------------------------


def step_charges_med(ctx: ProjectContext, rt: object = None) -> list[str]:  # noqa: ARG001
    """Sub-step `charges`: `charges.med` as Code_Aster wrote it and `charges_salome.py`,
    in `resultats/livrables/charges_salome/`; the 16 pictures (one isometric view per
    case) are drawn by the script itself, which is then run a second time through
    `exec()` from another directory (the way it is run in ParaVis)."""
    state = load_deliverables_state(ctx)
    root = deliverables_dir(ctx)
    source = root / "med" / MED_NAME
    if not state.outputs or not source.is_file():
        message = "charges : étape traiter d'abord (MED des charges absent)"
        raise ProjectError(message)
    d = Deliverables(root)
    cases = read_cases(ctx, d)
    out = root / OUT_NAME
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    med = out / MED_NAME
    shutil.copyfile(source, med)
    if sha256_of(med) != sha256_of(source):
        message = "charges : copie du MED différente de l'original"
        raise ProjectError(message)
    script = write_script(cases, med, out)
    lines = [
        f"charges.med copié tel quel ({med.stat().st_size} octets, sha256 "
        f"{sha256_of(med)[:12]}…) ; {len(cases)} cas : "
        + ", ".join(f"{c['nom']} ({c['nature']})" for c in cases),
        f"script {script.name} (FICHIER_MED = {med})",
    ]
    if not os.environ.get("ASTER_EXPERT_LIVRABLES_SANS_PNG"):
        made = run_in_salome(ctx, script, out / "png")
        lines.append(f"{len(made)} image(s) PNG rendues par le script (pvbatch)")
        again = run_in_salome(ctx, script, out / "png_exec", mode="exec")
        lines.append(
            f"{len(again)} image(s) rendues par exec() depuis un autre dossier"
        )
    (out / "cas.json").write_text(
        json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return lines


def deposit(
    ctx: ProjectContext,
    destination: Path,
    *,
    menu: str,
    version: str,
) -> list[str]:
    """Copy `charges.med`, `charges_salome.py` (its `FICHIER_MED` set to the copy),
    `png/`, with `LISEZMOI.txt` (five lines at most) and `empreintes.sha256`."""
    source = deliverables_dir(ctx) / OUT_NAME
    cases_path = source / "cas.json"
    if not cases_path.is_file():
        message = "charges : livrables absents (sous-étape charges d'abord)"
        raise ProjectError(message)
    cases = json.loads(cases_path.read_text("utf-8"))
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    shutil.copyfile(source / MED_NAME, destination / MED_NAME)
    copied.append(destination / MED_NAME)
    shutil.copyfile(source / SCRIPT_NAME, destination / SCRIPT_NAME)
    set_med_path(destination / SCRIPT_NAME, destination / MED_NAME)
    copied.append(destination / SCRIPT_NAME)
    (destination / "png").mkdir(exist_ok=True)
    for path in sorted((source / "png").glob("*.png")):
        shutil.copyfile(path, destination / "png" / path.name)
        copied.append(destination / "png" / path.name)
    readme = destination / "LISEZMOI.txt"
    names = [c["nom"] for c in cases]
    readme.write_text(
        README.format(
            projet=ctx.declaration.name,
            version=version,
            script=SCRIPT_NAME,
            med=MED_NAME,
            menu=menu,
            premier=names[0],
            cas=", ".join(names),
        ),
        encoding="utf-8",
    )
    copied.append(readme)
    fingerprints = destination / "empreintes.sha256"
    fingerprints.write_text(
        "".join(
            f"{sha256_of(p)}  {p.relative_to(destination).as_posix()}\n"
            for p in sorted(copied)
        ),
        encoding="utf-8",
    )
    return [str(p.relative_to(destination)) for p in sorted(copied)]


__all__ = [
    "OUT_NAME",
    "SCRIPT_NAME",
    "deposit",
    "read_cases",
    "run_in_salome",
    "set_med_path",
    "step_charges_med",
    "write_script",
]
