"""Classeur des livrables (lot 49, restructuré au lot 49 bis) relu : feuilles du lot 49
conservées après celles de la synthèse ingénieur, valeurs identiques à leur source du
paquet, police Arial 10 noire, en-têtes sur fond gris, jamais bleu, en-têtes figés,
format d'affichage tiré de config/arrondis.yaml (la valeur exacte reste dans la
cellule). La synthèse ingénieur elle-même : tests/unit/test_synthese_ingenieur.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from aster_expert.arrondis import load_table
from aster_expert.livrables.classeur import FIRST_SHEETS, LAST_SHEETS, build_workbook

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _package(root: Path) -> None:
    vis = root / "visualisation"
    _write(
        vis / "manifeste.json",
        {
            "projet": "essai",
            "code_aster": {"version": "17.4.0", "image_digest": "sha256:x"},
            "execution_production": "runs/a",
            "comm_production_sha256": "a" * 64,
            "execution_post_traitement": "runs/b",
            "comm_post_traitement_sha256": "b" * 64,
            "maillage": {"chemin": "m.med", "sha256": "c" * 64},
            "fichiers": {"med/resultats.med": {"sha256": "d" * 64, "octets": 10}},
            "champs": [
                {
                    "cle": "EFGE_ELNO",
                    "champ": "EFGE_ELNO",
                    "famille": "efforts_poutres",
                    "groupes": ["POUTRE"],
                    "groupes_noeuds": [],
                    "convention": "repère local, N > 0 traction",
                    "composantes": [
                        {"nom": "N", "unite_si": "N", "unite_affichage": "kN"},
                        {"nom": "MFY", "unite_si": "N·m", "unite_affichage": "kN·m"},
                    ],
                }
            ],
        },
    )
    _write(
        vis / "synthese.json",
        [
            {
                "famille": "efforts_poutres",
                "champ": "EFGE_ELNO",
                "composante": "N",
                "extremum": "max",
                "valeur_si": 123456.789,
                "unite_si": "N",
                "lieu": {
                    "noeud_med": 4,
                    "maille_med": 2,
                    "coordonnees_m": [1.0, 2.0, 3.0],
                },
                "combinaison": "C1",
                "position_mobile": "P1",
            }
        ],
    )
    _write(
        vis / "controle_charges.json",
        {
            "cas": {
                "G": {
                    "verdict": "RÉUSSI",
                    "ecart_relatif": 0.0,
                    "attendu_tel_qu_evalue_n": {"DX": 0.0, "DY": 0.0, "DZ": -1000.0},
                }
            }
        },
    )
    _write(
        vis / "equilibre_livrables.json",
        {
            "cas": {
                "G": {
                    "charge_n": {"FX": 0.0, "FY": 0.0, "FZ": -1000.0},
                    "reactions_n": {"FX": 0.0, "FY": 0.0, "FZ": 999.5},
                    "ressorts_n": {"FX": 0.0, "FY": 0.0, "FZ": 0.5},
                    "bilan_n": {"FX": 0.0, "FY": 0.0, "FZ": 0.0},
                }
            },
            "appuis_non_livres": [],
        },
    )
    _write(vis / "points.json", [])
    _write(
        vis / "enveloppes_lineiques.json",
        [
            {
                "cle": "EFGE_ELNO",
                "maille_med": 2,
                "extremite": 1,
                "noeud_med": 4,
                "x_m": 1.0,
                "y_m": 2.0,
                "z_m": 3.0,
                "niveau": -1,
                "N_max": 5000.0,
                "N_min": -2500.25,
                "MFY_max": 1234.5,
                "MFY_min": -1.0,
            }
        ],
    )
    _write(
        root / "paquet.json",
        {
            "depot": {"commit": "e" * 40},
            "exporte_le": "2026-10-08T00:00:00Z",
            "niveau": {
                "atteint": "D",
                "par_niveau": [{"niveau": "D", "atteint": True, "motif": "contrôles"}],
            },
            "criteres": [
                {
                    "niveau": "D",
                    "document": "docs/essais.md",
                    "commit_introduction": "f" * 40,
                    "date": "2026-10-01T00:00:00",
                }
            ],
        },
    )
    _write(
        root / "controles" / "controles_d.json",
        {"equilibrium": {"G": {"worst_relative_gap": 1.0e-12, "verdict": "RÉUSSI"}}},
    )


def test_the_workbook_is_read_back_identical_and_styled(tmp_path: Path) -> None:
    _package(tmp_path)
    path = tmp_path / "classeur.xlsx"
    build_workbook(tmp_path, load_table(ROOT)).save(path)
    wb = load_workbook(path)
    # Sans synthèse ingénieur déclarée : ses feuilles le disent ; les tables longues du
    # lot 49 (synthèse par champ, efforts aux points, enveloppes) sont des annexes CSV.
    assert wb.sheetnames == [*FIRST_SHEETS, *LAST_SHEETS]
    assert "Sans objet" in str(wb["Synthèse ingénieur"]["A1"].value)

    equilibre = wb["Réactions et équilibre"]
    rows = list(equilibre.iter_rows(min_row=3, values_only=True))
    fz = next(r for r in rows if r[1] == "FZ")
    assert fz[2:6] == (-1.0, 0.9995, 0.0005, 0.0)
    assert fz[-1] == "RÉUSSI"

    for sheet in wb.worksheets:
        for line in sheet.iter_rows():
            for cell in line:
                if cell.value is None:
                    continue
                assert cell.font.name == "Arial", (sheet.title, cell.coordinate)
                assert cell.font.sz == 10
                assert cell.font.color is None or cell.font.color.rgb == "FF000000"
                fill = cell.fill.fgColor.rgb if cell.fill.fill_type else None
                assert fill in (None, "FFD9D9D9"), (sheet.title, cell.coordinate, fill)
    sheet = wb["Réactions et équilibre"]
    headers = [sheet.cell(row=2, column=c) for c in range(1, 11)]
    assert all(c.fill.fill_type == "solid" for c in headers)
    assert all(c.fill.fgColor.rgb == "FFD9D9D9" for c in headers)
    assert sheet.freeze_panes == "B3"
