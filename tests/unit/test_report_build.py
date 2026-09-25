"""Synthèse d'un calcul (lot 35) : `build_synthesis`, `render_synthesis` et la commande
`aster-expert report`, sur un listing de synthèse écrit à partir des vrais paramètres du
quai réduit (aires tributaires des ressorts, axes des tubes) -- pas d'exécution."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from aster_expert.agent.model_data import load_model_data
from aster_expert.cli import app
from aster_expert.generation import comm
from aster_expert.meshing.combiwall import build_params, spring_node_areas
from aster_expert.report.build import CASES, build_synthesis
from aster_expert.report.render import (
    plot_profiles,
    render_controls,
    render_synthesis,
)
from aster_expert.report.tables import TableError

_ROOT = Path(__file__).resolve().parents[2]
_DATA = _ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"
_E = "{:.12E}"


def _table(header: list[str], rows: list[list[Any]], *, title: str = "") -> str:
    lines = [
        f"##{title}ASTER 17.04.00 CONCEPT 00000001 CALCULE LE 25/09/2026",
        " ".join(header),
    ]
    for row in rows:
        lines.append(
            " ".join(_E.format(c) if isinstance(c, float) else str(c) for c in row)
        )
    return "\n".join([*lines, ""]) + "\n"


def _write_mess(path: Path, cases: tuple[str, ...], *, dy_sign: float = -1.0) -> Path:
    params = build_params(load_model_data(_DATA))
    axes = params["tube"]["axes_x"]
    r = params["tube"]["rayon"]
    central = params["tube"]["central"]
    areas = spring_node_areas(params)["RESS_AV_ARGI"]
    spring_points = sorted(areas)[:5]
    parts: list[str] = []
    for case in cases:
        dy = dy_sign * 0.002
        header_pr = [
            "INTITULE",
            "NOEUD",
            "RESU",
            "NOM_CHAM",
            "NUME_ORDRE",
            "INST",
            "ABSC_CURV",
            "COOR_X",
            "COOR_Y",
            "COOR_Z",
            "DY",
        ]
        parts.append(
            _table(
                header_pr,
                [
                    [
                        comm.reaction_table_title("ANCRAGES", case)[:0]
                        + f"RESSORTS_{case}",
                        i,
                        "r",
                        "DEPL",
                        1,
                        0.0,
                        0.0,
                        x,
                        y,
                        z,
                        dy,
                    ]
                    for i, (x, y, z) in enumerate(spring_points, start=1)
                ],
            )
        )
        for tube in dict.fromkeys((central, 1)):
            parts.append(
                _table(
                    header_pr,
                    [
                        [
                            comm.profile_title(tube, case),
                            i,
                            "r",
                            "DEPL",
                            1,
                            0.0,
                            0.0,
                            axes[tube - 1] + r,
                            0.0,
                            z,
                            dy * (1 + z / 100),
                        ]
                        for i, z in enumerate((-26.0, -12.0, 2.6), start=1)
                    ],
                )
            )
        parts.append(
            _table(
                header_pr,
                [
                    [
                        comm.synthesis_title("tete", case),
                        1,
                        "r",
                        "DEPL",
                        1,
                        0.0,
                        0.0,
                        axes[central - 1],
                        r,
                        2.6,
                        dy,
                    ],
                    [
                        comm.synthesis_title("tete", case),
                        2,
                        "r",
                        "DEPL",
                        1,
                        0.0,
                        0.0,
                        axes[0],
                        r,
                        2.6,
                        dy / 2,
                    ],
                ],
            )
        )
        cols = [
            "RESULTAT",
            "NOM_CHAM",
            "INST",
            "NUME_ORDRE",
            "MAILLE",
            "NOEUD",
            "SOUS_POINT",
            "COOR_X",
            "COOR_Y",
            "COOR_Z",
        ]
        parts.append(
            _table(
                [*cols, "N"],
                [
                    [
                        "EFA",
                        "EFGE_ELNO",
                        0.0,
                        1,
                        100 + k,
                        200 + k,
                        1,
                        x,
                        r,
                        2.5,
                        1.0e5 * (k + 1),
                    ]
                    for k, x in enumerate(axes)
                ],
                title=comm.synthesis_title("tirants", case),
            )
        )
        parts.append(
            _table(
                [*cols, *comm.TUBE_EFFORT_COMPONENTS],
                [
                    [
                        "EFA",
                        "EFGE_ELNO",
                        0.0,
                        1,
                        1,
                        1,
                        1,
                        axes[central - 1],
                        r,
                        -5.0,
                        3e4,
                        1.0,
                        2e3,
                        5.0,
                    ],
                    [
                        "EFA",
                        "EFGE_ELNO",
                        0.0,
                        1,
                        2,
                        2,
                        1,
                        axes[0],
                        r,
                        2.5,
                        -4e4,
                        -2.0,
                        -1e3,
                        9.0,
                    ],
                ],
                title=comm.synthesis_title("tubes", case),
            )
        )
        parts.append(
            _table(
                [*cols[:4], "NOEUD", *cols[7:], *comm.PALP_EFFORT_COMPONENTS],
                [
                    [
                        "EFB",
                        "EFGE_NOEU",
                        0.0,
                        1,
                        7,
                        1.3,
                        0.0,
                        -3.0,
                        1e4,
                        0.5,
                        0.1,
                        2e3,
                        0.3,
                        0.05,
                        7e3,
                        0.2,
                    ],
                    [
                        "EFB",
                        "EFGE_NOEU",
                        0.0,
                        1,
                        8,
                        1.3,
                        0.0,
                        1.0,
                        -2e4,
                        -0.5,
                        -0.1,
                        -2e3,
                        -0.3,
                        -0.05,
                        -7e3,
                        -0.2,
                    ],
                ],
                title=comm.synthesis_title("palplanches", case),
            )
        )
        parts.append(
            _table(
                [*cols, *comm.BEAM_EFFORT_COMPONENTS],
                [
                    [
                        "EFA",
                        "EFGE_ELNO",
                        0.0,
                        1,
                        50,
                        300,
                        1,
                        axes[0],
                        0.34,
                        3.3,
                        0.0,
                        1e4,
                        2e3,
                        3e3,
                        5e3,
                        6e3,
                    ],
                    [
                        "EFA",
                        "EFGE_ELNO",
                        0.0,
                        1,
                        50,
                        301,
                        1,
                        axes[0] + 0.3,
                        0.34,
                        3.3,
                        0.0,
                        -1e4,
                        -2e3,
                        -3e3,
                        -5e3,
                        -6e3,
                    ],
                ],
                title=comm.synthesis_title("poutre", case),
            )
        )
        header_re = [
            "INTITULE",
            "RESU",
            "NOM_CHAM",
            "NUME_ORDRE",
            "INST",
            "DX",
            "DY",
            "DZ",
        ]
        for group in ("ANCRAGES", "PIED_TUBES", "SYM_G", "SYM_D"):
            parts.append(
                _table(
                    header_re,
                    [
                        [
                            comm.reaction_table_title(group, case),
                            "r",
                            "REAC_NODA",
                            1,
                            0.0,
                            1e3,
                            2e3,
                            3e3,
                        ]
                    ],
                )
            )
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


@pytest.fixture
def mess(tmp_path: Path) -> Path:
    return _write_mess(tmp_path / "fort.6", CASES)


def test_the_six_elementary_cases_are_summarised_from_the_tables(mess: Path) -> None:
    synthesis = build_synthesis(mess, _DATA)

    assert [c.case for c in synthesis.cases] == list(CASES)
    assert [p.label for p in synthesis.profiles] == ["TUBE_02", "TUBE_01"]
    case = synthesis.cases[0]
    assert case.head.max_abs.value == pytest.approx(-0.002)
    assert [round(t.n) for t in case.ties] == [100000, 200000, 300000]
    assert {p.component for p in case.tubes} == {"NXX", "NYY", "MXX", "MYY"}
    assert {p.component for p in case.palps} == set(comm.PALP_EFFORT_COMPONENTS)
    assert case.beam is not None
    assert {r.group for r in case.reactions} == {
        "ANCRAGES",
        "PIED_TUBES",
        "SYM_G",
        "SYM_D",
    }
    assert synthesis.provenance.med_read is False
    assert synthesis.beam_orientation_checked is True


def test_springs_moving_toward_the_basin_are_compressed_and_below_the_bearing_limit(
    mess: Path,
) -> None:
    springs = build_synthesis(mess, _DATA).cases[0].springs

    assert springs.sign.n_tension == 0
    assert springs.sign.n_compression == 5
    assert springs.bearing.n_over_100 == 0


def test_springs_moving_toward_the_land_are_reported_as_tension(tmp_path: Path) -> None:
    path = _write_mess(tmp_path / "fort.6", ("G",), dy_sign=+1.0)

    synthesis = build_synthesis(path, _DATA, cases=("G",))

    assert synthesis.cases[0].springs.sign.n_tension == 5
    assert synthesis.cases[0].springs.bearing.n_compressed == 0


def test_a_missing_table_stops_the_summary(mess: Path, tmp_path: Path) -> None:
    lines = mess.read_text(encoding="utf-8").split("\n")
    cut = tmp_path / "coupe.mess"
    cut.write_text("\n".join(lines[: len(lines) // 2]), encoding="utf-8")

    with pytest.raises(TableError):
        build_synthesis(cut, _DATA)


def test_the_document_states_units_fields_frames_and_gives_no_verdict(
    mess: Path,
) -> None:
    text = render_synthesis(build_synthesis(mess, _DATA), [])

    for token in (
        "DEPL",
        "EFGE_ELNO",
        "EFGE_NOEU uniquement (décision 2)",
        "REAC_NODA",
        "kN·m/m",
        "VECTEUR = (0, 0, 1)",
        "x_l",
        "U4.42.01",
        "repère local",
    ):
        assert token in text, token
    assert "### Cas élémentaire G" in text and "### Cas élémentaire A" in text
    assert "aucun verdict de dimensionnement" in text
    for banned in ("conforme", "non conforme", "vérifié", "OK"):
        assert banned not in text, banned
    assert "Aucune figure" in text
    assert "n'est pas relu" in text


def test_the_controls_document_carries_sign_and_bearing_tables(mess: Path) -> None:
    text = render_controls(build_synthesis(mess, _DATA))

    assert "Signe" in text and "Butée" in text
    assert "Nœuds au-delà de 100 %" in text
    assert "élémentaires" in text
    assert "Contrôles de niveau D" in text  # section présente même sans données


def test_no_figure_without_the_plotting_library(
    mess: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "aster_expert.report.render.matplotlib_available", lambda: False
    )

    assert plot_profiles(build_synthesis(mess, _DATA), tmp_path / "figs") == []


def test_one_figure_per_profile_when_the_plotting_library_is_present(
    mess: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved: list[str] = []

    class _Axes:
        def plot(self, *a: object, **k: object) -> None: ...
        def set_xlabel(self, *a: object) -> None: ...
        def set_ylabel(self, *a: object) -> None: ...
        def set_title(self, *a: object) -> None: ...
        def grid(self, *a: object) -> None: ...
        def legend(self) -> None: ...

    class _Figure:
        def savefig(self, path: Path, **k: object) -> None:
            saved.append(Path(path).name)

    stub = types.ModuleType("matplotlib")
    stub.use = lambda *_: None  # type: ignore[attr-defined]
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda **_: (_Figure(), _Axes())  # type: ignore[attr-defined]
    pyplot.close = lambda *_: None  # type: ignore[attr-defined]
    stub.pyplot = pyplot  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "matplotlib", stub)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", pyplot)
    monkeypatch.setattr("aster_expert.report.render.matplotlib_available", lambda: True)

    paths = plot_profiles(build_synthesis(mess, _DATA), tmp_path / "figs")

    assert saved == ["profil_dy_tube_02.png", "profil_dy_tube_01.png"]
    assert [p.name for p in paths] == saved


def test_the_report_command_writes_the_documents(mess: Path, tmp_path: Path) -> None:
    out = tmp_path / "sortie"

    result = CliRunner().invoke(
        app, ["report", str(mess), "--donnees", str(_DATA), "--sortie", str(out)]
    )

    assert result.exit_code == 0, result.output
    assert (out / "synthese.md").read_text(encoding="utf-8").startswith("# Synthèse")
    assert (out / "controles.md").is_file()
    data = json.loads((out / "synthese.json").read_text(encoding="utf-8"))
    assert data["provenance"]["med_read"] is False
    assert not list(out.glob("*.png"))


def test_the_report_command_refuses_a_missing_listing(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["report", str(tmp_path / "absent")])

    assert result.exit_code == 1
