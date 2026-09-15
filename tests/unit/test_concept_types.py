"""Unit tests for the M1 concept -> Aster type table (lot 10)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.validation.concept_types import (
    build_concept_type_table,
    resolve_concept_type,
)

DIGEST = "sha256:test"


def _write_schema(
    catalogue_root: Path,
    command: str,
    *,
    result_type: str | None,
    result_type_dynamic: bool,
) -> None:
    digest_dir = catalogue_root / DIGEST
    digest_dir.mkdir(parents=True, exist_ok=True)
    schema: dict[str, Any] = {
        "command": command,
        "aster_version": "17.4.0",
        "image_digest": DIGEST,
        "catalogue_source": "/opt/x/code_aster",
        "catalogue_hash": "sha256:def",
        "kind": "operator",
        "result_type": result_type,
        "result_type_dynamic": result_type_dynamic,
        "docu": None,
        "keywords": [],
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    (digest_dir / f"{command}.json").write_text(json.dumps(schema), encoding="utf-8")


# LIRE_MAILLAGE genuinely has result_type_dynamic=true on the 17.4.0
# catalogue (verified in the lot 10 batch report): a plain literal-only
# LIRE_MAILLAGE call still yields a concept of unknown type by this project's
# own conservative rule, not a guessed "maillage_sdaster".
SOURCE = """\
MAIL = LIRE_MAILLAGE(FORMAT="MED")
MO = AFFE_MODELE(
    MAILLAGE=MAIL, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="3D")
)
MAIL = MODI_MAILLAGE(reuse=MAIL, MAILLAGE=MAIL, ORIE_PEAU=_F(GROUP_MA_PEAU="haut"))
"""


@pytest.fixture
def catalogue_root(tmp_path: Path) -> Path:
    root = tmp_path / "catalogue"
    _write_schema(root, "LIRE_MAILLAGE", result_type=None, result_type_dynamic=True)
    _write_schema(
        root, "AFFE_MODELE", result_type="modele_sdaster", result_type_dynamic=False
    )
    _write_schema(
        root, "MODI_MAILLAGE", result_type="maillage_sdaster", result_type_dynamic=False
    )
    return root


def test_dynamic_result_type_is_unknown(catalogue_root: Path) -> None:
    analysis = parse_comm_source(SOURCE, file_path="t.comm")
    table, warnings = build_concept_type_table(
        analysis, catalogue_root=catalogue_root, digest=DIGEST
    )

    # MAIL is produced by both LIRE_MAILLAGE (dynamic result type) and
    # MODI_MAILLAGE (reuse, maillage_sdaster): the known type from the
    # reentrant call wins over the unresolved contribution.
    assert table["MAIL"].aster_type == "maillage_sdaster"
    assert table["MO"].aster_type == "modele_sdaster"
    assert warnings == []


def test_concept_never_produced_is_unknown(catalogue_root: Path) -> None:
    analysis = parse_comm_source(SOURCE, file_path="t.comm")
    table, _ = build_concept_type_table(
        analysis, catalogue_root=catalogue_root, digest=DIGEST
    )

    info = resolve_concept_type(table, "NEVER_ASSIGNED")
    assert info.aster_type is None
    assert "no statement in this file assigns" in info.reason


def test_unknown_command_contributes_no_type(tmp_path: Path) -> None:
    root = tmp_path / "catalogue"
    _write_schema(
        root, "AFFE_MODELE", result_type="modele_sdaster", result_type_dynamic=False
    )
    source = "X = INEXISTANT_CMD(A=1)\n"
    analysis = parse_comm_source(source, file_path="t.comm")

    table, _ = build_concept_type_table(analysis, catalogue_root=root, digest=DIGEST)

    assert table["X"].aster_type is None
    assert "not found in the catalogue" in table["X"].reason


def test_conflicting_types_across_producers_is_unknown_and_warned(
    tmp_path: Path,
) -> None:
    root = tmp_path / "catalogue"
    _write_schema(
        root, "AFFE_MODELE", result_type="modele_sdaster", result_type_dynamic=False
    )
    _write_schema(root, "LIRE_MAILLAGE", result_type=None, result_type_dynamic=True)
    _write_schema(
        root, "DEFI_GROUP", result_type="maillage_sdaster", result_type_dynamic=False
    )
    source = (
        'X = AFFE_MODELE(MAILLAGE="m", AFFE=_F(TOUT="OUI"))\n'
        "X = DEFI_GROUP(reuse=X, MAILLAGE=X)\n"
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    table, warnings = build_concept_type_table(
        analysis, catalogue_root=root, digest=DIGEST
    )

    assert table["X"].aster_type is None
    assert "conflicting types" in table["X"].reason
    assert len(warnings) == 1
