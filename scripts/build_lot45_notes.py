"""Lot 45 : les quatre notes Word (hypothèses et résultats des deux projets).

Pour chaque projet déclaré dans `PROJECTS` : écrit `note_hypotheses.docx` et
`note_resultats.docx` dans `projets/<projet>/livrables/notes/`, lance le contrôle
automatique de chacune (`aster_expert.notes.controle`) et écrit le compte rendu du
contrôle, `controle_notes.json`, à côté. Aucune exécution Code_Aster : tout vient de la
fiche, des données et du paquet de résultats versionné.

Le nombre de pages n'est connu que d'un moteur de mise en page : il est relevé par
LibreOffice (`soffice`, `pdfinfo`) s'ils sont présents, sinon consigné `null`.

Usage : `.venv/bin/python scripts/build_lot45_notes.py [projet ...]`
Code de sortie 1 si un contrôle échoue.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.notes.controle import (
    NoteCheck,
    check_hypotheses_note,
    check_results_note,
)
from aster_expert.notes.hypotheses import NOTE_NAME as HYPOTHESES_NAME
from aster_expert.notes.hypotheses import build_hypotheses_note
from aster_expert.notes.resultats import NOTE_NAME as RESULTS_NAME
from aster_expert.notes.resultats import build_results_note
from aster_expert.projet.context import load_project

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ("quai_cw_test_01", "dalle_appuyee_01")


def page_count(path: Path) -> int | None:
    """Pages of a `.docx`, laid out by LibreOffice; `None` without it."""
    soffice = shutil.which("soffice")
    pdfinfo = shutil.which("pdfinfo")
    if soffice is None or pdfinfo is None:
        return None
    with tempfile.TemporaryDirectory() as work:
        done = subprocess.run(  # noqa: S603
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", work, str(path)],
            capture_output=True,
            text=True,
            check=False,
            env={"HOME": work, "PATH": "/usr/bin:/bin"},
        )
        pdf = Path(work) / (path.stem + ".pdf")
        if done.returncode != 0 or not pdf.is_file():
            return None
        info = subprocess.run(  # noqa: S603
            [pdfinfo, str(pdf)], capture_output=True, text=True, check=False
        ).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return None


def report(check: NoteCheck, path: Path) -> dict[str, object]:
    return {
        "note": path.name,
        "taille_octets": path.stat().st_size,
        "pages": page_count(path),
        "controle": "OK" if check.ok else "ÉCHEC",
        "compteurs": check.counts,
        "problemes": check.problems,
    }


def main(argv: list[str]) -> int:
    names = tuple(argv) or PROJECTS
    failed = False
    for name in names:
        ctx = load_project(name, ROOT)
        folder = ctx.project_dir / "livrables" / "notes"
        folder.mkdir(parents=True, exist_ok=True)
        hypotheses = build_hypotheses_note(ctx, folder / HYPOTHESES_NAME)
        results = build_results_note(ctx, folder / RESULTS_NAME)
        checks = {
            "hypotheses": (check_hypotheses_note(ctx, hypotheses), hypotheses),
            "resultats": (check_results_note(ctx, results), results),
        }
        document = {
            "projet": name,
            "genere_le": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **{kind: report(check, path) for kind, (check, path) in checks.items()},
        }
        (folder / "controle_notes.json").write_text(
            json.dumps(document, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        for kind, (check, path) in checks.items():
            status = "OK" if check.ok else "ÉCHEC"
            print(f"{name} {kind} : {path.relative_to(ROOT)} — contrôle {status}")
            for problem in check.problems:
                print(f"    {problem}")
            failed = failed or not check.ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
