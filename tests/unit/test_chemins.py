"""Politique de lecture des chemins d'entrée (lot 46, étape 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.chemins import (
    PathRefusedError,
    execution_policy,
    load_read_policy,
    resolve_input_path,
)
from aster_expert.mcp import tools
from aster_expert.mcp.errors import McpToolError

COMM = "DEBUT()\nFIN()\n"


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    """Dépôt factice : config/chemins.yaml, projets/ lisible, hors/ non déclaré."""
    root = tmp_path / "depot"
    (root / "config").mkdir(parents=True)
    (root / "projets" / "p").mkdir(parents=True)
    (root / "config" / "chemins.yaml").write_text(
        "schema_version: 1\nlecture:\n  racines_depot: [projets]\n"
        "  racines_externes: []\n",
        encoding="utf-8",
    )
    (root / "projets" / "p" / "a.comm").write_text(COMM, encoding="utf-8")
    (tmp_path / "hors").mkdir()
    (tmp_path / "hors" / "x.comm").write_text(COMM, encoding="utf-8")
    return root


def _resoudre(depot: Path, chemin: str | Path, **kw: object) -> Path:
    return resolve_input_path(
        chemin,
        policy=load_read_policy(depot),
        base=depot,
        suffixes=(".comm",),
        **kw,  # type: ignore[arg-type]
    )


def test_chemin_dans_une_racine_accepte(depot: Path) -> None:
    assert (
        _resoudre(depot, "projets/p/a.comm")
        == (depot / "projets" / "p" / "a.comm").resolve()
    )


def test_remontee_par_points_points_refusee(depot: Path) -> None:
    with pytest.raises(PathRefusedError, match="hors des racines"):
        _resoudre(depot, "../../x.comm")
    # même cas avec un fichier existant, atteint par « .. » depuis une racine
    with pytest.raises(PathRefusedError, match="hors des racines"):
        _resoudre(depot, "projets/p/../../../hors/x.comm")


def test_chemin_absolu_hors_racine_refuse_et_dit_comment_declarer(
    depot: Path,
) -> None:
    cible = depot.parent / "hors" / "x.comm"
    with pytest.raises(PathRefusedError) as info:
        _resoudre(depot, cible)
    texte = str(info.value)
    assert f"Racine manquante : {cible.parent}" in texte
    assert "racines_externes" in texte
    assert "chemins.local.yaml" in texte


def test_refus_hors_racine_ne_revele_pas_l_existence(depot: Path) -> None:
    with pytest.raises(PathRefusedError, match="hors des racines") as info:
        _resoudre(depot, depot.parent / "hors" / "inexistant.comm")
    assert "introuvable" not in str(info.value)


def test_lien_symbolique_pointant_hors_racine_refuse(depot: Path) -> None:
    lien = depot / "projets" / "p" / "lien.comm"
    lien.symlink_to(depot.parent / "hors" / "x.comm")
    with pytest.raises(PathRefusedError, match="lien symbolique"):
        _resoudre(depot, lien)


def test_lien_symbolique_vers_un_fichier_de_la_racine_accepte(depot: Path) -> None:
    lien = depot / "projets" / "lien_interne.comm"
    lien.symlink_to(depot / "projets" / "p" / "a.comm")
    assert _resoudre(depot, lien) == (depot / "projets" / "p" / "a.comm").resolve()


def test_racine_externe_declaree_acceptee(depot: Path) -> None:
    externe = depot.parent / "hors"
    (depot / "config" / "chemins.local.yaml").write_text(
        f"lecture:\n  racines_externes:\n    - {externe}\n", encoding="utf-8"
    )
    assert _resoudre(depot, externe / "x.comm") == (externe / "x.comm").resolve()


def test_racine_externe_declaree_dans_le_fichier_versionne(depot: Path) -> None:
    externe = depot.parent / "hors"
    (depot / "config" / "chemins.yaml").write_text(
        f"lecture:\n  racines_depot: [projets]\n  racines_externes: ['{externe}']\n",
        encoding="utf-8",
    )
    assert _resoudre(depot, externe / "x.comm").name == "x.comm"


def test_extension_autre_que_comm_refusee(depot: Path) -> None:
    autre = depot / "projets" / "p" / "a.txt"
    autre.write_text(COMM, encoding="utf-8")
    with pytest.raises(PathRefusedError, match="extension"):
        _resoudre(depot, autre)


def test_fichier_absent_dans_la_racine_signale_introuvable(depot: Path) -> None:
    with pytest.raises(PathRefusedError, match="introuvable"):
        _resoudre(depot, "projets/p/absent.comm")


def test_politique_execution_sans_racine_refuse_tout(depot: Path) -> None:
    politique = execution_policy((), depot)
    with pytest.raises(PathRefusedError, match="aucune racine"):
        resolve_input_path(
            depot / "projets" / "p" / "a.comm", policy=politique, base=depot
        )


def test_politique_execution_plus_stricte_que_lecture(depot: Path) -> None:
    politique = execution_policy(("projets/p",), depot)
    ok = resolve_input_path(
        depot / "projets" / "p" / "a.comm",
        policy=politique,
        base=depot,
        suffixes=(".comm",),
    )
    assert ok.name == "a.comm"
    (depot / "projets" / "autre.comm").write_text(COMM, encoding="utf-8")
    with pytest.raises(PathRefusedError, match="allowed_roots"):
        resolve_input_path(
            depot / "projets" / "autre.comm", policy=politique, base=depot
        )


# --- outils MCP -----------------------------------------------------------------


def test_analyze_comm_mcp_refuse_hors_racine(depot: Path) -> None:
    with pytest.raises(McpToolError, match="hors des racines"):
        tools.analyze_comm(
            project_root=depot,
            comm_path=str(depot.parent / "hors" / "x.comm"),
            log_path=depot / "log.jsonl",
        )


def test_analyze_comm_mcp_accepte_racine_externe_declaree(depot: Path) -> None:
    externe = depot.parent / "hors"
    (depot / "config" / "chemins.local.yaml").write_text(
        f"lecture:\n  racines_externes:\n    - {externe}\n", encoding="utf-8"
    )
    resultat = tools.analyze_comm(
        project_root=depot,
        comm_path=str(externe / "x.comm"),
        log_path=depot / "log.jsonl",
    )
    assert resultat.analysis is not None and resultat.analysis.statements


def test_validate_comm_mcp_refuse_avant_tout_autre_prerequis(depot: Path) -> None:
    with pytest.raises(McpToolError, match="hors des racines"):
        tools.validate_comm(
            project_root=depot,
            comm_path=str(depot.parent / "hors" / "x.comm"),
            workroot=None,
            log_path=depot / "log.jsonl",
        )


def test_validate_comm_mcp_refuse_extension(depot: Path) -> None:
    autre = depot / "projets" / "p" / "a.txt"
    autre.write_text(COMM, encoding="utf-8")
    with pytest.raises(McpToolError, match="extension"):
        tools.validate_comm(
            project_root=depot,
            comm_path=str(autre),
            workroot=None,
            log_path=depot / "log.jsonl",
        )


def test_depot_reel_declare_les_racines_attendues() -> None:
    racine = Path(__file__).resolve().parents[2]
    noms = {r.relative_to(racine).as_posix() for r in load_read_policy(racine).roots}
    assert {"projets", "data", "external"} <= noms


# --- commandes `aster-expert` ----------------------------------------------------


def test_commande_comm_parse_applique_la_politique(
    depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from aster_expert import cli

    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(depot))
    monkeypatch.chdir(depot)
    runner = CliRunner()
    refus = runner.invoke(cli.app, ["comm", "parse", str(depot.parent / "hors/x.comm")])
    assert refus.exit_code == 1
    assert "Racine manquante" in refus.output
    accepte = runner.invoke(cli.app, ["comm", "parse", "projets/p/a.comm"])
    assert accepte.exit_code == 0, accepte.output
