"""Lot 35, étape 1 : archive les preuves d'exécution des constats `code_aster`
établis au lot 34 (et au lot 33 pour l'arrêt de post-traitement de la poutre), pour
que la fiche les cite avec une source d'exécution vérifiable
(`aster_expert.agent.hypotheses.ExecutionSource`).

Pour chaque essai, deux fichiers sont écrits dans `data/examples/lot35_constats/` :

- le `.comm` **exactement tel qu'exécuté** (copie octet pour octet du répertoire
  d'exécution, empreinte contrôlée contre `executions.json` du lot 34) ;
- un **extrait du listing** (`.mess.txt`) : les lignes de tables imprimées, recopiées
  textuellement du `.mess` réel, précédées d'un en-tête de provenance (lignes `#`).
  Aucune valeur n'est retapée : une valeur d'une source d'exécution doit figurer dans
  cet extrait (test `test_every_value_obtained_is_printed_in_its_versioned_listing`).

Les répertoires d'exécution vivent sous `data/processed/runs/` (non versionnés) : ce
script ne s'exécute qu'avec eux, et il est idempotent.

Usage : python scripts/build_lot35_constats.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "processed" / "runs"
OUT = ROOT / "data" / "examples" / "lot35_constats"
LOT34_EXECUTIONS = (
    ROOT / "data" / "examples" / "lot34_equilibre" / "rapports" / "executions.json"
)


def _lines(run: str) -> list[str]:
    return (
        (RUNS / run / "proc.0" / "fort.6")
        .read_text(encoding="utf-8", errors="replace")
        .splitlines()
    )


def _header_of(lines: list[str], first_row: int) -> str:
    """La ligne d'en-tête de la table dont la première ligne est `first_row`
    (indice 0)."""
    return lines[first_row - 1]


def _row(lines: list[str], pattern: str, *, after: int = 0) -> tuple[int, str]:
    """(indice 0, ligne) de la première ligne à partir de `after` qui commence par
    `pattern`."""
    rx = re.compile(pattern)
    for i in range(after, len(lines)):
        if rx.match(lines[i]):
            return i, lines[i]
    message = f"ligne introuvable : {pattern}"
    raise SystemExit(message)


def _extract(run: str, patterns: list[str]) -> list[str]:
    """Pour chaque motif : l'en-tête de sa table puis la ligne, telles quelles."""
    lines = _lines(run)
    out: list[str] = []
    for pattern in patterns:
        index, row = _row(lines, pattern)
        out.append(_header_of(lines, index))
        out.append(row)
    return out


def _copy_comm(run: str, name: str, expected_sha_prefix: str, dest: Path) -> None:
    source = RUNS / run / name
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if not digest.startswith(expected_sha_prefix):
        message = f"{source} : empreinte {digest} != {expected_sha_prefix}..."
        raise SystemExit(message)
    dest.write_bytes(source.read_bytes())


def _write_listing(dest: Path, run: str, comm: str, what: str, rows: list[str]) -> None:
    head = [
        f"# Extrait verbatim du listing (.mess) de l'exécution réelle {run}",
        f"# du cas {comm} (code_aster 17.4.0, image du manifeste).",
        f"# Contenu : {what}",
        "# Lignes recopiées telles quelles ; rien n'est retapé ni recalculé.",
        "#",
    ]
    dest.write_text("\n".join([*head, *rows]) + "\n", encoding="utf-8")


def _executions() -> dict[str, dict[str, str]]:
    data = json.loads(LOT34_EXECUTIONS.read_text(encoding="utf-8"))
    return {r["run"]: r for r in data["runs"]}


def main() -> int:
    if not RUNS.is_dir():
        print("data/processed/runs absent : rien à archiver", file=sys.stderr)
        return 1
    known = _executions()
    OUT.mkdir(parents=True, exist_ok=True)

    def sha_of(run: str) -> str:
        return known[run]["comm_sha256"][:16]

    # F1 -- évaluation aux nœuds de FORCE_COQUE/PRES (point 5)
    for tag, run, note in (
        ("f1_avant", "20260924T152937-a4da70cf", "fonction à interface doublée"),
        ("f1_apres", "20260924T155826-b6368ff9", "charge appliquée par couche"),
    ):
        _copy_comm(
            run, "sonde_blocage_total.comm", sha_of(run), OUT / f"{tag}.sonde.comm"
        )
        _write_listing(
            OUT / f"{tag}.mess.txt",
            run,
            "sonde_blocage_total.comm",
            f"REAC_NODA résultante, tous nœuds, cas G (sonde de blocage total, {note})",
            _extract(run, [r"^CHARGE_G  "]),
        )

    # F2 -- CREA_POI1 : une maille ponctuelle par nœud (point 4)
    for tag, run, note in (
        ("f2_avant", "20260924T153701-fcac67f2", "classes de bande seules"),
        ("f2_apres", "20260924T154200-f7ec9180", "classes communes de raideur sommée"),
    ):
        _copy_comm(
            run,
            "quai_reduit_forces_ressorts.comm",
            sha_of(run),
            OUT / f"{tag}.ressorts.comm",
        )
        _write_listing(
            OUT / f"{tag}.mess.txt",
            run,
            "quai_reduit_forces_ressorts.comm",
            "DEPL/DY puis FORC_NODA/DY (POI1) du nœud 65, à z = -18 (limite "
            f"argile/marne), cas G ({note})",
            _extract(run, [r"^RESSORTS_G  +65 ", r"^FRESS_G  +65 "]),
        )

    # F3 -- poutre chargée en forces nodales (point 12)
    run = "20260924T151447-7d8347d4"
    _copy_comm(
        run, "sonde_pression_aucune.comm", sha_of(run), OUT / "f3_nodal.sonde.comm"
    )
    _write_listing(
        OUT / "f3_nodal.mess.txt",
        run,
        "sonde_pression_aucune.comm",
        "REAC_NODA résultante, tous nœuds, cas G (poutre et poids seuls, forces "
        "nodales de la décision 13)",
        _extract(run, [r"^CHARGE_G  "]),
    )
    fail_run = "20260924T122731-0b829e46"
    fail = _lines(fail_run)
    start, _ = _row(fail, r".*<F> <CALCULEL2_92>")
    block = fail[max(0, start - 3) : start + 14]
    (OUT / "f3_echec_calculel2_92.mess.txt").write_text(
        "\n".join(
            [
                f"# Extrait verbatim du listing de l'exécution réelle {fail_run}, cas",
                "# data/examples/lot33_equilibre/quai_reduit/diag_no_fz.comm",
                "# (arrêt fatal au post-traitement ; niveau B : ce n'est pas une",
                "# source d'exécution, il est cité par les notes du constat).",
                "#",
                *block,
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # F4 -- REAC_NODA aux nœuds liés par LIAISON_SOLIDE (point 3)
    run = "20260924T153254-726c58d9"
    _copy_comm(
        run,
        "quai_reduit_controles.comm",
        sha_of(run),
        OUT / "f4_reactions.controles.comm",
    )
    _write_listing(
        OUT / "f4_reactions.mess.txt",
        run,
        "quai_reduit_controles.comm",
        "REAC_NODA résultante par groupe (ANCRAGES, PIED_TUBES, SYM_G, SYM_D) puis sur "
        "tous les nœuds, cas EAU_A",
        _extract(
            run,
            [
                r"^REAC_ANCR_EAU_A ",
                r"^REAC_PIED_EAU_A ",
                r"^REAC_SYMG_EAU_A ",
                r"^REAC_SYMD_EAU_A ",
                r"^REAC_TOUS_EAU_A ",
            ],
        ),
    )
    print(f"preuves écrites dans {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
