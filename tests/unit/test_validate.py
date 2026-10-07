"""Integration-style tests for validate_comm_file, without a real container.

`aster_expert.validation.checker_client.run_checks` is monkeypatched: it is
the one function in the whole pipeline that needs the Aster container
(docs/architecture.md, ADR-002) — everything upstream (parsing, M1, M2) and
downstream (M4, report assembly) is plain project Python, exercised here for
real.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import aster_expert.validation.validate as validate_module
from aster_expert.validation.errors import ValidationRunError
from aster_expert.validation.validate import (
    resolve_digest_for_version,
    validate_comm_file,
)

DIGEST = "sha256:testdigest"


def _schema(
    command: str,
    *,
    result_type: str | None = None,
    result_type_dynamic: bool = False,
    keywords: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "command": command,
        "aster_version": "17.4.0",
        "image_digest": DIGEST,
        "catalogue_source": "/opt/x/code_aster",
        "catalogue_hash": "sha256:cataloguehash",
        "kind": "operator",
        "result_type": result_type,
        "result_type_dynamic": result_type_dynamic,
        "docu": None,
        "keywords": keywords or [],
        "extracted_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    catalogue_dir = root / "data" / "processed" / "catalogue" / DIGEST
    catalogue_dir.mkdir(parents=True)

    (catalogue_dir / "LIRE_MAILLAGE.json").write_text(
        json.dumps(_schema("LIRE_MAILLAGE", result_type="maillage_sdaster")),
        encoding="utf-8",
    )
    (catalogue_dir / "AFFE_MODELE.json").write_text(
        json.dumps(
            _schema(
                "AFFE_MODELE",
                result_type="modele_sdaster",
                keywords=[
                    {
                        "path": ["MAILLAGE"],
                        "variant_id": "aaaa",
                        "kind": "simple",
                        "status": "required",
                        "value_type": "maillage_sdaster",
                        "allowed_values": None,
                        "default": None,
                        "min_values": 1,
                        "max_values": 1,
                        "condition": [],
                    },
                    {
                        "path": ["AFFE"],
                        "variant_id": "bbbb",
                        "kind": "factor",
                        "status": "required",
                        "min_occurrences": 1,
                        "max_occurrences": None,
                        "condition": [],
                        "children": [
                            {
                                "path": ["AFFE", "PHENOMENE"],
                                "variant_id": "cccc",
                                "kind": "simple",
                                "status": "required",
                                "value_type": "TXM",
                                "allowed_values": ["MECANIQUE", "THERMIQUE"],
                                "default": None,
                                "min_values": 1,
                                "max_values": 1,
                                "condition": [],
                            },
                            {
                                "path": ["AFFE", "MODELISATION"],
                                "variant_id": "dddd",
                                "kind": "simple",
                                "status": "required",
                                "value_type": "TXM",
                                "allowed_values": None,
                                "default": None,
                                "min_values": 1,
                                "max_values": 1,
                                "condition": [],
                            },
                        ],
                    },
                ],
            )
        ),
        encoding="utf-8",
    )

    versions_yaml = root / "config" / "versions.yaml"
    versions_yaml.parent.mkdir(parents=True)
    versions_yaml.write_text(
        "detected:\n  container:\n    image_digest: " + DIGEST + "\n", encoding="utf-8"
    )
    return root


def test_resolve_digest_default_uses_detected(project_root: Path) -> None:
    catalogue_root = project_root / "data" / "processed" / "catalogue"
    versions_path = project_root / "config" / "versions.yaml"

    digest, aster_version = resolve_digest_for_version(
        catalogue_root, None, versions_path
    )

    assert digest == DIGEST
    assert aster_version == "17.4.0"


def test_resolve_digest_explicit_version_not_extracted_fails_explicitly(
    project_root: Path,
) -> None:
    catalogue_root = project_root / "data" / "processed" / "catalogue"
    versions_path = project_root / "config" / "versions.yaml"

    with pytest.raises(ValidationRunError, match="18.0.0"):
        resolve_digest_for_version(catalogue_root, "18.0.0", versions_path)


def test_validate_comm_file_full_pipeline(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        'MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(PHENOMENE="BAD", MODELISATION="3D"))\n'
        "if 1:\n"
        "    X = AFFE_MODELE(MAILLAGE=MAIL, AFFE=une_variable_dynamique)\n",
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        # id 0 = LIRE_MAILLAGE (fully literal), id 1 = the AFFE_MODELE with a
        # bad PHENOMENE value, both "check"-mode. Statement 2 (X, under
        # `if 1:`) is excluded from checking (control_flow) but AFFE_MODELE
        # is static (result_type_dynamic=False in this fixture), so it still
        # arrives as a "type_probe" (lot 10c, point P1) -- never confronted
        # with checkCommandSyntax, so it gets no entry in this fake's return.
        assert {r["id"] for r in requests} == {0, 1, 2}
        probe = next(r for r in requests if r["id"] == 2)
        assert probe["mode"] == "type_probe"
        assert "keywords" not in probe
        return {
            0: {"id": 0, "ok": True},
            1: {
                "id": 1,
                "ok": False,
                "orig": "CheckerError",
                "message": (
                    "For keyword AFFE/PHENOMENE: Unexpected value: 'BAD', "
                    "must be in ('MECANIQUE', 'THERMIQUE')"
                ),
                "stack": "AFFE/PHENOMENE",
            },
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False
    assert len(report.errors) == 1
    finding = report.errors[0]
    assert finding.code == "INVALID_VALUE"
    assert finding.command == "AFFE_MODELE"
    assert finding.statement_index == 1
    assert finding.path == ["AFFE", "PHENOMENE"]
    assert finding.variant_id == "cccc"

    assert {c.statement_index for c in report.commands_checked} == {0, 1}
    assert len(report.commands_not_checked) == 1
    not_checked = report.commands_not_checked[0]
    assert not_checked.statement_index == 2
    assert any("control flow" in r for r in not_checked.reasons)


def test_validate_comm_file_unknown_command_imported_is_not_checked(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        "from code_aster.MacroCommands.defi_cont import DEFI_CONT\n"
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        "CONT = DEFI_CONT(MODELE=MAIL)\n",
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {"id": 0, "ok": True, "produced_type": "maillage_sdaster"},
            1: {
                "id": 1,
                "ok": False,
                "orig": "UnknownCommand",
                "message": "command not found in live catalogue: 'DEFI_CONT'",
                "stack": None,
            },
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False  # lot 48 bis : une commande non confrontée
    assert report.verdict == "partiel"
    assert report.errors == []
    not_checked = next(
        e for e in report.commands_not_checked if e.command == "DEFI_CONT"
    )
    assert any("MacroCommands" in r for r in not_checked.reasons)


def test_validate_comm_file_unknown_command_not_imported_is_an_error(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = STAT_NON_LINEX(FORMAT="MED")\n', encoding="utf-8")

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {
                "id": 0,
                "ok": False,
                "orig": "UnknownCommand",
                "message": "command not found in live catalogue: 'STAT_NON_LINEX'",
                "stack": None,
            }
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False
    assert len(report.errors) == 1
    assert report.errors[0].code == "UNKNOWN_COMMAND"
    assert report.commands_not_checked == []


def test_validate_comm_file_confirmed_absent_command_never_suggests_a_typo(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # docs/development-plan.md, lot 10c, point P4/R4: POST_GOUJ is
    # individually confirmed absent from the target catalogue (a real
    # defect of the two official cas tests still calling it), never a
    # typo -- the report must never suggest a close-match correction for
    # it, and must say so plainly rather than merely "not found".
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('T = POST_GOUJ(TABLE="tab1")\n', encoding="utf-8")

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {
                "id": 0,
                "ok": False,
                "orig": "UnknownCommand",
                "message": "command not found in live catalogue: 'POST_GOUJ'",
                "stack": None,
            }
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert len(report.errors) == 1
    finding = report.errors[0]
    assert finding.code == "UNKNOWN_COMMAND"
    assert finding.suggestion is None
    assert "absent from the target version's catalogue" in finding.message
    assert "not a typo" in finding.message


def test_validate_comm_file_non_standard_catalogue_object_is_not_checked(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('F = VARIABLE(NOM_PARA="X", VALE=1.0)\n', encoding="utf-8")

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {
                "id": 0,
                "ok": False,
                "orig": "NonStandardCatalogueObject",
                "message": (
                    "catalogue object for 'VARIABLE' is not a Command instance "
                    "(type: VariableSupport): not compatible with checkCommandSyntax"
                ),
                "stack": None,
            }
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False  # lot 48 bis : commande non confrontée
    assert report.verdict == "partiel"
    assert report.errors == []
    assert report.commands_not_checked[0].command == "VARIABLE"


def test_validate_comm_file_unresolved_concept_is_not_checked_with_enriched_reason(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        "if 1:\n"
        "    MAIL = MODI_MAILLAGE(reuse=MAIL, MAILLAGE=MAIL, INFO=1)\n"
        "MO = AFFE_MODELE(MAILLAGE=MAIL, "
        'AFFE=_F(PHENOMENE="MECANIQUE", MODELISATION="3D"))\n',
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        # statement 1 (MODI_MAILLAGE) is excluded by control_flow: never
        # confronted with checkCommandSyntax, but still arrives as a
        # "type_probe" (id 1, lot 10c point P1) since it reassigns MAIL.
        # This fake, standing in for the container, registers nothing for
        # it (no outcome entry -- a type_probe never produces one) exactly
        # as the real script would for a command this test does not declare
        # in project_root's fixture catalogue: MAIL's rebind never gets a
        # placeholder, so statement 2 (AFFE_MODELE) is sent but cannot
        # resolve MAIL.
        assert {r["id"] for r in requests} == {0, 1, 2}
        probe = next(r for r in requests if r["id"] == 1)
        assert probe["mode"] == "type_probe"
        assert "keywords" not in probe
        return {
            0: {"id": 0, "ok": True, "produced_type": "maillage_sdaster"},
            2: {
                "id": 2,
                "ok": False,
                "orig": "UnresolvedConcept",
                "message": "concept 'MAIL' has no resolved placeholder in this batch",
                "stack": None,
            },
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False  # lot 48 bis : commande non confrontée
    assert report.verdict == "partiel"
    assert report.errors == []
    entries_by_command = {e.command: e for e in report.commands_not_checked}
    assert "control flow" in entries_by_command["MODI_MAILLAGE"].reasons[0]
    affe = entries_by_command["AFFE_MODELE"]
    assert "statement 1" in affe.reasons[0]
    assert "control flow" in affe.reasons[0] or "MODI_MAILLAGE" in affe.reasons[0]


def test_validate_comm_file_syntax_error_fails_explicitly(
    project_root: Path, tmp_path: Path
) -> None:
    comm_path = tmp_path / "broken.comm"
    comm_path.write_text("DEBUT(CODE=\n", encoding="utf-8")

    with pytest.raises(ValidationRunError):
        validate_comm_file(
            comm_path,
            project_root=project_root,
            workroot=tmp_path,
            docker_bin=Path("/usr/bin/docker"),
        )


def test_validate_comm_file_consumer_of_an_errored_producer_is_checked_with_warning(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # docs/development-plan.md, lot 10c, point P1: a static producer that
    # itself ends up in `errors` (not merely excluded) still lets a
    # downstream consumer be checked -- but that consumer's CheckedEntry
    # carries a warning naming the exact statement in error, distinguishing
    # this from a plain "not verified" dependency.
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        'MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(PHENOMENE="BAD", MODELISATION="3D"))\n'
        "CH = AFFE_CHAR_MECA(MODELE=MO)\n",
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {"id": 0, "ok": True, "produced_type": "maillage_sdaster"},
            1: {
                "id": 1,
                "ok": False,
                "orig": "CheckerError",
                "message": (
                    "For keyword AFFE/PHENOMENE: Unexpected value: 'BAD', "
                    "must be in ('MECANIQUE', 'THERMIQUE')"
                ),
                "stack": "AFFE/PHENOMENE",
            },
            2: {"id": 2, "ok": True, "produced_type": None},
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert len(report.errors) == 1
    assert report.errors[0].statement_index == 1

    checked_by_index = {c.statement_index: c for c in report.commands_checked}
    producer = checked_by_index[1]
    assert producer.ok is False
    assert producer.warnings == []

    consumer = checked_by_index[2]
    assert consumer.ok is True
    assert len(consumer.warnings) == 1
    assert "'MO'" in consumer.warnings[0]
    assert "statement 1" in consumer.warnings[0]
    assert "in error" in consumer.warnings[0]


def test_validate_comm_file_execution_confirmed_override_for_extr_coupe(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # docs/development-plan.md, lot 10c, point P3: EXTR_COUPE's static
    # cham_gd_sdaster declaration disagrees with CREA_CHAMP's declared
    # resultat_sdaster expectation, but real execution of an official cas
    # test with this exact pattern (astest/zzzz169a.comm) reaches FIN — so
    # this project's own static check, not the file, is what is wrong here.
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        "resu_coupe = EXTR_COUPE(RESULTAT=MAIL)\n"
        "CH = CREA_CHAMP(\n"
        '    OPERATION="EXTR", TYPE_CHAM="NOEU_DEPL_R", RESULTAT=resu_coupe\n'
        ")\n",
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {"id": 0, "ok": True, "produced_type": "maillage_sdaster"},
            1: {"id": 1, "ok": True, "produced_type": "cham_gd_sdaster"},
            2: {
                "id": 2,
                "ok": False,
                "orig": "CheckerError",
                "message": (
                    "For keyword RESULTAT: Unexpected type: <class "
                    "'code_aster.Cata.Language.DataStructure."
                    "cham_gd_sdaster'>, expecting: [<class 'code_aster.Cata."
                    "Language.DataStructure.resultat_sdaster'>]"
                ),
                "stack": "RESULTAT",
            },
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is True
    assert report.errors == []
    consumer = next(c for c in report.commands_checked if c.statement_index == 2)
    assert consumer.ok is True
    assert len(consumer.warnings) == 1
    assert "EXTR_COUPE" in consumer.warnings[0]
    assert "zzzz169a.comm" in consumer.warnings[0]


def test_validate_comm_file_type_mismatch_not_overridden_for_other_producer(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The override is scoped to a concept actually produced by EXTR_COUPE
    # (verified host-side, never guessed from the message text alone): the
    # exact same message from a different producer stays a real error.
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        "resu_other = SOME_OTHER_COMMAND(RESULTAT=MAIL)\n"
        "CH = CREA_CHAMP(\n"
        '    OPERATION="EXTR", TYPE_CHAM="NOEU_DEPL_R", RESULTAT=resu_other\n'
        ")\n",
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {"id": 0, "ok": True, "produced_type": "maillage_sdaster"},
            1: {"id": 1, "ok": True, "produced_type": "cham_gd_sdaster"},
            2: {
                "id": 2,
                "ok": False,
                "orig": "CheckerError",
                "message": (
                    "For keyword RESULTAT: Unexpected type: <class "
                    "'code_aster.Cata.Language.DataStructure."
                    "cham_gd_sdaster'>, expecting: [<class 'code_aster.Cata."
                    "Language.DataStructure.resultat_sdaster'>]"
                ),
                "stack": "RESULTAT",
            },
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False
    assert len(report.errors) == 1
    assert report.errors[0].statement_index == 2
    assert report.errors[0].code == "INVALID_TYPE"


def test_validate_comm_file_verified_checker_limitation_is_not_checked_not_an_error(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # docs/development-plan.md, lot 10c, point P2: a verified systemic
    # checkCommandSyntax limitation (MACRO_ELAS_MULT's own sd_prod crashing
    # on a legitimate, catalogue-conformant CAS_CHARGE that omits the
    # optional-with-no-default NOM_CAS) is never presented as an error in
    # the user's file.
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        "DEF = MACRO_ELAS_MULT(\n"
        "    MODELE=MAIL,\n"
        '    CAS_CHARGE=_F(MODE_FOURIER=1, TYPE_MODE="SYME"),\n'
        ")\n",
        encoding="utf-8",
    )

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {
            0: {"id": 0, "ok": True, "produced_type": "maillage_sdaster"},
            1: {
                "id": 1,
                "ok": False,
                "orig": "CheckerError",
                "message": (
                    "Cannot type result of the command MACRO_ELAS_MULT\n"
                    "Exception raised: KeyError('NOM_CAS'))"
                ),
                "stack": None,
            },
        }

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.valid is False  # lot 48 bis : commande non confrontée
    assert report.verdict == "partiel"
    assert report.errors == []
    assert all(c.statement_index != 1 for c in report.commands_checked)
    not_checked = next(
        e for e in report.commands_not_checked if e.command == "MACRO_ELAS_MULT"
    )
    assert "checkCommandSyntax limitation" in not_checked.reasons[0]
    assert "NOM_CAS" in not_checked.reasons[0]


def test_validate_comm_file_tuple_of_concepts_is_resolved(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lot 48 bis (A16) : `CHAR_MECA_GLOBAL=(CL,)` est reconstruit en liste de
    marqueurs de concept, la commande et la suite sont confrontées."""
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(
        'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'
        'MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(PHENOMENE="MECANIQUE", '
        'MODELISATION="3D", TOUT="OUI"))\n'
        'CL = AFFE_CHAR_MECA(MODELE=MO, DDL_IMPO=_F(GROUP_NO="A", DX=0.0))\n'
        "R = MACRO_ELAS_MULT(MODELE=MO, CHAR_MECA_GLOBAL=(CL,), "
        'CAS_CHARGE=_F(NOM_CAS="C1", CHAR_MECA=CL))\n',
        encoding="utf-8",
    )
    seen: dict[int, dict[str, Any]] = {}

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        for r in requests:
            seen[r["id"]] = r
        return {r["id"]: {"id": r["id"], "ok": True} for r in requests}

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm_file(
        comm_path,
        project_root=project_root,
        workroot=tmp_path,
        docker_bin=Path("/usr/bin/docker"),
    )

    assert report.commands_not_checked == []
    macro = next(r for r in seen.values() if r["command"] == "MACRO_ELAS_MULT")
    assert macro["keywords"]["CHAR_MECA_GLOBAL"] == [{"__concept_ref__": "CL"}]
    assert report.verdict == "valide"
    assert report.valid is True
