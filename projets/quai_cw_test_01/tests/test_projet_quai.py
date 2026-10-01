"""Le quai comme projet du tronc commun (lot 41).

- la déclaration `projet.yaml` nomme toutes les données que le générateur lit
  (`comm.required_data`, relevées dans le code du générateur) ;
- le tronc commun (contrôles D, combinaisons, ferraillage) redonne, à partir des
  exécutions archivées des lots 37 et 39, les sorties de référence figées à
  l'étape 1 (`references/`), octet pour octet ou aux chemins près énumérés par le
  critère. Ces derniers tests lisent `data/processed/runs/` (non versionné) : sans
  ces exécutions, ils sont sautés.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from aster_expert.combinaisons.efforts import combined_forces, write_combined_forces
from aster_expert.controles.equilibre import level_d_controls
from aster_expert.ferraillage.poutre import analyze_member, prepare_member
from aster_expert.projet.context import load_project

_ROOT = Path(__file__).resolve().parents[3]
_PROJECT = _ROOT / "projets" / "quai_cw_test_01"
_REFERENCES = _PROJECT / "references"
_RUN37 = _ROOT / "data" / "processed" / "runs" / "20260925T125131-c67e28a1"
_RUN39 = _ROOT / "data" / "processed" / "runs" / "20260928T100157-30609502"
_KEY = re.compile(
    r"\"((?:repere|geometrie|tube|palplanche|poutre_couronnement|tirants|sol|"
    r"eau_terres|charges|maillage)\.[A-Za-z0-9_]+)\""
)


def test_required_data_names_every_value_the_generator_reads() -> None:
    read: set[str] = set()
    for folder in ("generation", "meshing"):
        for path in (_PROJECT / folder).glob("*.py"):
            read |= set(_KEY.findall(path.read_text(encoding="utf-8")))
    ctx = load_project("quai_cw_test_01", _ROOT)

    assert set(ctx.declaration.comm.required_data) == read


def test_the_declared_mesh_script_is_the_verified_one() -> None:
    """L'empreinte du script Salomé conditionne le cache de maillage : déplacé,
    jamais modifié (le maillage vérifié du lot 27 reste le sien)."""
    import hashlib

    script = _PROJECT / "maillage" / "combiwall_mesh.py"
    assert hashlib.sha256(script.read_bytes()).hexdigest() == (
        "05213fec5f30e77b5e7a1ab0ef69ffa7cf56682370baaf68b944610c7518dfcb"
    )


@pytest.mark.skipif(not _RUN37.is_dir(), reason="exécution archivée du lot 37 absente")
def test_the_trunk_controls_reproduce_the_lot_37_equilibrium(tmp_path: Path) -> None:
    ctx = load_project("quai_cw_test_01", _ROOT)
    # Charge intégrée de référence (l'intégration relit le MED dans le conteneur) :
    # donnée à l'extension par son cache, comme si elle l'avait calculée.
    ctx.cache["integrale"] = json.loads(
        (_REFERENCES / "controles_d" / "integrale.json").read_text("utf-8")
    )

    level_d_controls(
        ctx,
        mess_path=_RUN37 / "proc.0" / "fort.6",
        comm_path=_RUN37 / "complet.comm",
        mesh_path=Path("inutilisé"),
        out_dir=tmp_path,
    )

    assert (tmp_path / "equilibre.json").read_bytes() == (
        _REFERENCES / "controles_d" / "equilibre.json"
    ).read_bytes()
    summary = json.loads((tmp_path / "controles_d.json").read_text("utf-8"))
    assert summary["verdict"] == "RÉUSSI"


@pytest.mark.skipif(not _RUN37.is_dir(), reason="exécution archivée du lot 37 absente")
def test_the_trunk_combinations_reproduce_lot_38(tmp_path: Path) -> None:
    ctx = load_project("quai_cw_test_01", _ROOT)
    result = combined_forces(ctx, _RUN37 / "proc.0" / "fort.6")
    write_combined_forces(
        ctx,
        result,
        tmp_path,
        comm_path=_ROOT / "data" / "examples" / "lot37_efforts" / "complet.comm",
        run_comm_path=_RUN37 / "complet.comm",
    )

    for name in (
        "combinaisons.csv",
        "extrema.csv",
        "controle_manuel.json",
        "poutre_couronnement.md",
    ):
        assert (tmp_path / name).read_bytes() == (
            _REFERENCES / "combinaisons" / name
        ).read_bytes(), name


@pytest.mark.skipif(
    not (_RUN37.is_dir() and _RUN39.is_dir()),
    reason="exécutions archivées des lots 37 et 39 absentes",
)
def test_the_trunk_rebar_reproduces_lot_39(tmp_path: Path) -> None:
    ctx = load_project("quai_cw_test_01", _ROOT)
    assert ctx.declaration.rebar is not None
    member = ctx.declaration.rebar.members[0]
    out = tmp_path / "ferraillage"
    comm = prepare_member(ctx, member, _RUN37 / "proc.0" / "fort.6", out)
    # L'exécution archivée du lot 39 a lu le même cas, à la ligne « Produit par »
    # près : son listing sert ici de résultat du `.comm` préparé.
    run = tmp_path / "run"
    (run / "proc.0").mkdir(parents=True)
    shutil.copyfile(comm, run / "poutre.comm")
    shutil.copyfile(_RUN39 / "proc.0" / "fort.6", run / "proc.0" / "fort.6")

    result = analyze_member(ctx, member, run, out)

    assert result.summary["controle_main"] == {
        "comparaisons": 63,
        "dans_le_critere": 63,
        "echecs": 2,
    }
    for name in (
        "ferraillage.csv",
        "enveloppes.csv",
        "synthese.csv",
        "synthese.md",
        "controle_main.json",
        "resume.json",
        "sections.csv",
        "efforts.csv",
        "rapports/mess_ferr_extrait.txt",
        "figures/as_x.png",
    ):
        assert (out / name).read_bytes() == (
            _REFERENCES / "ferraillage" / name
        ).read_bytes(), name
