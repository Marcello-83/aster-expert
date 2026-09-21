"""Copy the MED files and reports of the lot 26 trials into the repository.

Reads the JSON printed by `aster-expert mesh run` (one file per case) and the
text report of `aster-expert mesh check` (same case name), and writes, under
`data/examples/lot26_essais/`:

* `<geometry>/med/<name>.med`  : the MED file produced;
* `rapports/<case>_run.json`   : the run report (paths made project-relative);
* `rapports/<case>_check.txt`  : the check report.

Usage: python scripts/collect_lot26_essais.py <runs-dir>
where <runs-dir> holds `run_<case>.json` and `chk_<case>.txt`.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "examples" / "lot26_essais"
# case -> (geometry directory, name of the MED in the repository)
CASES = {
    "g1": ("plaque_raidisseur", "lot26_g1"),
    "g1alt": ("plaque_raidisseur", "altere_sans_partition"),
    "g2": ("tube_plaques", "lot26_g2"),
    "g2a": ("tube_plaques", "altere_36_facettes"),
    "g2b": ("tube_plaques", "altere_sans_cote_1"),
    "g3": ("poutre_barre", "lot26_g3"),
    "g3alt": ("poutre_barre", "altere_barre_non_reliee"),
}


def main(argv: list[str]) -> int:
    runs = Path(argv[1])
    (OUT / "rapports").mkdir(parents=True, exist_ok=True)
    for case, (directory, name) in CASES.items():
        report = json.loads((runs / f"run_{case}.json").read_text(encoding="utf-8"))
        med_dir = OUT / directory / "med"
        med_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(report["med_path"], med_dir / f"{name}.med")
        for key in ("work_dir", "med_path", "log_path"):
            report[key] = str(Path(report[key]).relative_to(ROOT))
        report["command"] = [c.replace(str(ROOT) + "/", "") for c in report["command"]]
        report["med_versioned_as"] = f"{directory}/med/{name}.med"
        (OUT / "rapports" / f"{case}_run.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        shutil.copy2(runs / f"chk_{case}.txt", OUT / "rapports" / f"{case}_check.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
