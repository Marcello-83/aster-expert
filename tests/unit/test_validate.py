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
        # bad PHENOMENE value; the third statement is under `if 1:` and must
        # never reach here at all (control_flow excludes it before M2/M3).
        assert {r["id"] for r in requests} == {0, 1}
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
