"""Lot 39 : extraits versionnés des listings et journal des exécutions réelles.

Pour chaque exécution de `aster-expert run` du lot (répertoire de travail sous
`data/processed/runs/`, non versionné), écrit dans `<essai>/../rapports/` :

- `mess_<nom>_extrait.txt` : la table imprimée (`##FERR_*`), les messages
  `<A>`/`<E>`/`<F>` éventuels et la ligne `DIAGNOSTIC JOB` ;
- `executions.json` : version, digest d'image, `.comm` exécuté (chemin versionné et
  sha256, contrôlé identique au versionné), diagnostic, durée, heure.

Les durées sont celles qu'a affichées `aster-expert run` à la fin de chaque
exécution (ligne « Durée »), recopiées ci-dessous.

Usage : python projets/quai_cw_test_01/scripts/collect_lot39_essais.py
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "data" / "processed" / "runs"
IMAGE = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
ESSAIS = ROOT / "data" / "examples" / "lot39_essais"
POUTRE = ROOT / "data" / "examples" / "lot39_poutre"

# (nom, .comm versionné, répertoire d'exécution, durée affichée en s)
EXECUTIONS = (
    ("d19", ESSAIS / "d19" / "d19.comm", "20260928T095358-e9475e88", 13.7),
    ("limites", ESSAIS / "limites" / "limites.comm", "20260928T095412-2b7d81be", 10.0),
    ("fermin", ESSAIS / "fermin" / "fermin.comm", "20260928T095423-69cfd1c4", 9.6),
    ("fiss", ESSAIS / "fiss" / "fiss.comm", "20260928T095433-ba976fa9", 8.0),
    (
        "fermin_mpa",
        ESSAIS / "fermin_mpa" / "fermin_mpa.comm",
        "20260928T095741-ba84496c",
        10.1,
    ),
    ("poutre", POUTRE / "poutre.comm", "20260928T100157-30609502", 11.5),
    ("plaque", ESSAIS / "plaque" / "plaque.comm", "20260928T100918-aa126904", 8.4),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(lines: list[str]) -> str:
    kept: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("##FERR_"):
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("# "):
                kept.append(lines[i])
                i += 1
            kept.append("")
            continue
        if re.search(r"<[AEF]> <", line):
            block = [line]
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("╚"):
                block.append(lines[j])
                j += 1
            if j < len(lines):
                block.append(lines[j])
            kept.extend(block)
            kept.append("")
            i = j + 1
            continue
        if "DIAGNOSTIC JOB" in line:
            kept.append(line)
        i += 1
    return "\n".join(kept) + "\n"


def main() -> int:
    journals: dict[Path, dict[str, object]] = {}
    for name, comm, run_name, duration in EXECUTIONS:
        run = RUNS / run_name
        executed = run / comm.name
        assert _sha(executed) == _sha(comm), f"{name} : .comm exécuté différent"
        lines = (run / "proc.0" / "fort.6").read_text(encoding="utf-8").splitlines()
        diagnostic = [ln for ln in lines if "DIAGNOSTIC JOB" in ln][-1].split(":")[-1]
        folder = (
            comm.parents[1] / "rapports"
            if comm.parent != POUTRE
            else POUTRE / "rapports"
        )
        folder.mkdir(parents=True, exist_ok=True)
        if comm.parent != POUTRE:
            (folder / f"mess_{name}_extrait.txt").write_text(extract(lines), "utf-8")
        stamp = datetime.strptime(run_name[:15], "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
        journals.setdefault(folder, {})[name] = {
            "aster_version": "17.4.0",
            "image_digest": IMAGE,
            "comm_path": comm.relative_to(ROOT).as_posix(),
            "comm_sha256": _sha(comm),
            "diagnostic": diagnostic.strip(),
            "duration_s": duration,
            "executed_at": stamp.isoformat().replace("+00:00", "Z"),
            "work_dir": run.relative_to(ROOT).as_posix(),
        }
    for folder, journal in journals.items():
        (folder / "executions.json").write_text(
            json.dumps(journal, ensure_ascii=False, indent=1) + "\n", "utf-8"
        )
        print(f"écrit {(folder / 'executions.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
