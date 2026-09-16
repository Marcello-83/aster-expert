"""Unit tests for `aster_expert.ingestion.inventory` (lot 6).

Two kinds of coverage:

- synthetic fixture trees (`tmp_path`), built here, that isolate one
  behaviour at a time: no network, no dependency on the real synchronized
  `external/codeaster-doc` checkout;
- one `requires_corpus`-marked sanity check against the real checkout,
  skipped when it is absent, that pins the exact anomaly counts found on the
  17.4.0 corpus at lot 6 (docs/development-plan.md) so a future regression
  in the parser is caught rather than silently re-measured differently.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.ingestion.inventory import (
    build_inventory,
    derive_family,
    discover_document_dirs,
    parse_index_rst,
    write_inventory_jsonl,
)
from aster_expert.ingestion.models import InventoryResult

FIXED_NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_index(label: str, title: str, entries: list[str]) -> str:
    entries_block = "\n".join(f"    {e}" for e in entries)
    return (
        f"\n.. _{label}:\n\n"
        f"**{label}** {title}\n"
        f"{'=' * (len(label) + len(title) + 4)}\n\n"
        ".. toctree::\n"
        "    :hidden:\n\n"
        "    self\n\n"
        ".. toctree::\n"
        "    :maxdepth: 2\n"
        "    :numbered:\n\n"
        f"{entries_block}\n"
    )


# --------------------------------------------------------------------------
# parse_index_rst
# --------------------------------------------------------------------------


def test_parse_index_rst_extracts_label_title_and_toctree_entries() -> None:
    text = _minimal_index("u4.84.01", "Opérateur COMB_SISM_MODAL", ["But", "Syntaxe"])
    parsed = parse_index_rst(text)
    assert parsed.raw_label == "u4.84.01"
    assert parsed.title == "Opérateur COMB_SISM_MODAL"
    assert parsed.toctree_entries == ("But", "Syntaxe")


def test_parse_index_rst_excludes_self_and_directive_options() -> None:
    text = _minimal_index("r7.01.03", "Loi BETON_DOUBLE_DP", ["Notations"])
    parsed = parse_index_rst(text)
    assert "self" not in parsed.toctree_entries
    assert parsed.toctree_entries == ("Notations",)


def test_parse_index_rst_second_toctree_block_after_dedent() -> None:
    # Mirrors the real shape (man_r/r3/r3.08.10/index.rst): a hidden `self`
    # toctree, then a real one, both scanned, only the real one kept.
    text = (
        "\n.. _r3.08.10:\n\n"
        "**r3.08.10** Élément CABLE_GAINE\n"
        "=================================\n\n"
        "Du texte de résumé ici.\n\n"
        ".. toctree::\n"
        "    :hidden:\n\n"
        "    self\n\n"
        ".. toctree::\n"
        "    :maxdepth: 2\n\n"
        "    Formulation_variationnelle\n"
        "    1\n"
    )
    parsed = parse_index_rst(text)
    assert parsed.toctree_entries == ("Formulation_variationnelle", "1")


def test_parse_index_rst_missing_label_returns_none() -> None:
    text = "\n**x** Titre sans label\n=======================\n"
    parsed = parse_index_rst(text)
    assert parsed.raw_label is None
    assert parsed.title == "Titre sans label"


def test_parse_index_rst_missing_title_returns_none() -> None:
    text = "\n.. _u4.01.00:\n\nPas de ligne en gras ici.\n"
    parsed = parse_index_rst(text)
    assert parsed.raw_label == "u4.01.00"
    assert parsed.title is None


def test_parse_index_rst_skips_legacy_bold_preamble_before_real_title() -> None:
    # Verbatim shape of man_u/u4/u4.01.02/index.rst: bold preamble lines
    # ("**Manuel d'Utilisation**", "**Fascicule ...**", "**Document: ...**")
    # precede the real "**<label>** <title>" line. The *first* bold line is
    # not the title on 8/2047 documents of the real corpus (lot 6) — the
    # title must be anchored to the document's own label, not to "whichever
    # bold line comes first".
    text = (
        "\n.. _U4.01.02:\n\n"
        "Organisme(s):    EDF-R&D/AMA\n\n"
        "**Manuel d'Utilisation**\n\n"
        "**Fascicule U4.0-: Utilisation des commandes**\n\n"
        "**Document: U4.01.02**\n\n\n"
        "**u4.01.02** Nouveautés et modifications dans les commandes\n"
        "===========================================================\n"
    )
    parsed = parse_index_rst(text)
    assert parsed.title == "Nouveautés et modifications dans les commandes"


def test_parse_index_rst_title_anchor_is_case_insensitive() -> None:
    # The bold marker on the title line echoes the label's own case, which
    # is not always the same case as the ".. _LABEL:" directive itself
    # (docs/corpus.md §6: casing is not uniform).
    text = "\n.. _U4.84.01:\n\n**u4.84.01** Opérateur X\n========================\n"
    parsed = parse_index_rst(text)
    assert parsed.title == "Opérateur X"


# --------------------------------------------------------------------------
# derive_family
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("document_id", "expected"),
    [
        ("U4.84.01", "U4"),
        ("U0.00.01", "U0"),
        ("U7.02.11", "U7"),
        ("R7.01.03", "R"),
        ("R5.03.02", "R"),
        ("V3.03.100", "V"),
        ("D0.01.01", "D"),
        ("SU1.04.01", "SU"),
        ("SV4.02.01", "SV"),
    ],
)
def test_derive_family_known_prefixes(document_id: str, expected: str) -> None:
    assert derive_family(document_id) == expected


def test_derive_family_unknown_prefix_returns_none() -> None:
    assert derive_family("Z9.01.01") is None


# --------------------------------------------------------------------------
# discover_document_dirs
# --------------------------------------------------------------------------


def test_discover_document_dirs_excludes_other_pages(tmp_path: Path) -> None:
    manuals = tmp_path / "manuals"
    doc = manuals / "man_u" / "u4" / "u4.01.00"
    _write(doc / "index.rst", _minimal_index("u4.01.00", "Notice", []))
    nav = manuals / "man_u" / "other_pages" / "home"
    _write(nav / "index.rst", "\n.. _home:\n\n**home** Accueil\n=================\n")

    found = discover_document_dirs(manuals)
    assert found == [doc]


def test_discover_document_dirs_no_nesting(tmp_path: Path) -> None:
    manuals = tmp_path / "manuals"
    outer = manuals / "man_v" / "v3" / "v3.03.100"
    _write(outer / "index.rst", _minimal_index("v3.03.100", "Cas SSLS100", []))
    # A document is never nested inside another document's own directory on
    # the real corpus (verified at lot 6): guard the assumption with a
    # negative fixture too, so a future regression that starts nesting
    # documents does not just double-count silently.
    found = discover_document_dirs(manuals)
    assert found == [outer]


# --------------------------------------------------------------------------
# build_inventory : happy path and one entry per anomaly kind
# --------------------------------------------------------------------------


def _build(manuals_root: Path, repo_root: Path) -> InventoryResult:
    return build_inventory(
        manuals_root,
        repo_root=repo_root,
        source_name="codeaster-doc",
        source_commit="9c8c179f57ef7ca1d2891cac275ee4823a57967c",
        now=FIXED_NOW,
    )


def test_build_inventory_happy_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_u" / "u4" / "u4.84.01"
    _write(doc / "index.rst", _minimal_index("u4.84.01", "Opérateur X", ["But"]))
    _write(doc / "But.rst", "Contenu du but.\n")

    result = _build(manuals, repo_root)

    assert result.anomalies == ()
    assert len(result.documents) == 1
    entry = result.documents[0]
    assert entry.document_id == "U4.84.01"
    assert entry.raw_label == "u4.84.01"
    assert entry.directory_name == "u4.84.01"
    assert entry.family == "U4"
    assert entry.subfamily == "U4"
    assert entry.title == "Opérateur X"
    assert entry.relative_path == "source/manuals/man_u/u4/u4.84.01"
    assert set(entry.files) == {"index.rst", "But.rst"}
    assert entry.source_commit == "9c8c179f57ef7ca1d2891cac275ee4823a57967c"
    assert entry.fingerprint.startswith("sha256:")
    assert entry.size_bytes > 0


def test_build_inventory_missing_label(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_d" / "d0" / "d0.01.01"
    _write(doc / "index.rst", "\n**x** Titre sans label\n=======================\n")

    result = _build(manuals, repo_root)

    assert [a.kind for a in result.anomalies] == ["missing_label"]
    assert result.documents[0].document_id == "D0.01.01"  # fallback: dirname
    assert result.documents[0].raw_label == "d0.01.01"


def test_build_inventory_label_directory_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_r" / "r3" / "r3.07.11"
    _write(doc / "index.rst", _minimal_index("R3.07.10", "Titre décalé", []))

    result = _build(manuals, repo_root)

    kinds = [a.kind for a in result.anomalies]
    assert "label_directory_mismatch" in kinds
    assert result.documents[0].document_id == "R3.07.10"
    assert result.documents[0].directory_name == "r3.07.11"


def test_build_inventory_duplicate_document_id(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    _write(
        manuals / "man_r" / "r3" / "r3.07.10" / "index.rst",
        _minimal_index("r3.07.10", "Premier", []),
    )
    _write(
        manuals / "man_r" / "r3" / "r3.07.11" / "index.rst",
        _minimal_index("R3.07.10", "Second, même id normalisé", []),
    )

    result = _build(manuals, repo_root)

    duplicate_anomalies = [
        a for a in result.anomalies if a.kind == "duplicate_document_id"
    ]
    assert len(duplicate_anomalies) == 1
    assert duplicate_anomalies[0].detail.endswith("r3.07.10'")


def test_build_inventory_unresolved_toctree_entry(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_v" / "v1" / "v1.01.238"
    _write(doc / "index.rst", _minimal_index("v1.01.238", "Cas orphelin", ["1", "2"]))

    result = _build(manuals, repo_root)

    unresolved = [a for a in result.anomalies if a.kind == "unresolved_toctree_entry"]
    assert {a.detail for a in unresolved} == {
        "entrée toctree '1' ne correspond à aucun fichier du répertoire",
        "entrée toctree '2' ne correspond à aucun fichier du répertoire",
    }
    # The document itself is still inventoried: a broken cross-reference is
    # reported, never silently dropped from the corpus.
    assert len(result.documents) == 1


def test_build_inventory_orphan_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_v" / "v1" / "v1.01.163"
    _write(
        doc / "index.rst", _minimal_index("v1.01.163", "Cas avec fichier oublié", [])
    )
    # Present on disk, but neither a toctree entry nor mentioned anywhere.
    _write(doc / "Modelisation_I.rst", "Une modélisation jamais reliée.\n")

    result = _build(manuals, repo_root)

    orphans = [a for a in result.anomalies if a.kind == "orphan_file"]
    assert len(orphans) == 1
    assert "Modelisation_I.rst" in orphans[0].detail


def test_build_inventory_nested_toctree_via_hub_page_is_not_orphan(
    tmp_path: Path,
) -> None:
    # Real corpus shape (R5.03.17, lot 6): the index.rst toctree only
    # references an intermediate "sommaire" page, whose own toctree lists
    # the real chapters by their extension-less stem. A chapter mentioned
    # only that way (never directly in index.rst) must not be flagged.
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_r" / "r5" / "r5.03.17"
    _write(
        doc / "index.rst",
        _minimal_index("r5.03.17", "Relations de comportement", ["sommaire"]),
    )
    _write(
        doc / "sommaire.rst",
        "Sommaire\n========\n\n"
        ".. toctree::\n    :maxdepth: 2\n\n    Comportement_ELAS\n",
    )
    _write(doc / "Comportement_ELAS.rst", "Le comportement élastique.\n")

    result = _build(manuals, repo_root)

    assert not any(a.kind == "orphan_file" for a in result.anomalies)


def test_build_inventory_empty_component_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_r" / "r3" / "r3.08.10"
    _write(
        doc / "index.rst", _minimal_index("r3.08.10", "Élément avec page vide", ["1"])
    )
    _write(doc / "1.rst", "\n\n\n")  # verbatim shape of the real defect

    result = _build(manuals, repo_root)

    empty_anomalies = [a for a in result.anomalies if a.kind == "empty_component_file"]
    assert len(empty_anomalies) == 1
    assert "1.rst" in empty_anomalies[0].detail
    # The document as a whole is not empty: index.rst itself carries a title.
    assert not any(a.kind == "empty_document" for a in result.anomalies)


def test_build_inventory_whole_document_empty(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_d" / "d0" / "d0.02.02"
    # No title line at all: nothing but the label directive survives the
    # ".."-prefixed-line filter, on every composing file.
    _write(doc / "index.rst", "\n.. _d0.02.02:\n\n.. comment seul\n")

    result = _build(manuals, repo_root)

    assert any(a.kind == "empty_document" for a in result.anomalies)


def test_build_inventory_unknown_family_prefix(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_z" / "z9" / "z9.01.01"
    _write(doc / "index.rst", _minimal_index("z9.01.01", "Famille inconnue", []))

    result = _build(manuals, repo_root)

    unknown = [a for a in result.anomalies if a.kind == "unknown_family_prefix"]
    assert len(unknown) == 1
    assert result.documents[0].family == "Z9"  # best-effort, flagged, not dropped


def test_build_inventory_missing_title(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    doc = manuals / "man_d" / "d0" / "d0.01.01"
    _write(doc / "index.rst", "\n.. _d0.01.01:\n\nAucune ligne de titre ici.\n")

    result = _build(manuals, repo_root)

    assert [a.kind for a in result.anomalies] == ["missing_title"]
    assert result.documents[0].title is None
    assert result.documents[0].document_id == "D0.01.01"  # still inventoried


# --------------------------------------------------------------------------
# idempotence and JSONL output
# --------------------------------------------------------------------------


def test_write_inventory_jsonl_is_idempotent(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"
    _write(
        manuals / "man_u" / "u4" / "u4.01.00" / "index.rst",
        _minimal_index("u4.01.00", "Notice", []),
    )
    _write(
        manuals / "man_v" / "v3" / "v3.03.100" / "index.rst",
        _minimal_index("V3.03.100", "Cas SSLS100", ["Mod_lisation_A"]),
    )
    _write(
        manuals / "man_v" / "v3" / "v3.03.100" / "Mod_lisation_A.rst",
        "Modélisation A.\n",
    )

    out1 = tmp_path / "inv1.jsonl"
    out2 = tmp_path / "inv2.jsonl"
    write_inventory_jsonl(_build(manuals, repo_root), out1)
    write_inventory_jsonl(_build(manuals, repo_root), out2)

    assert out1.read_bytes() == out2.read_bytes()
    lines = [json.loads(line) for line in out1.read_text(encoding="utf-8").splitlines()]
    assert {entry["document_id"] for entry in lines} == {"U4.01.00", "V3.03.100"}


# --------------------------------------------------------------------------
# sanity check against the real synchronized corpus, when present
# --------------------------------------------------------------------------

_REAL_REPO_ROOT = Path(__file__).resolve().parents[2] / "external" / "codeaster-doc"


@pytest.mark.requires_corpus
@pytest.mark.skipif(
    not (_REAL_REPO_ROOT / "source" / "manuals").is_dir(),
    reason="external/codeaster-doc n'est pas synchronisé",
)
def test_build_inventory_real_corpus_counts_pinned_at_lot_6() -> None:
    manuals_root = _REAL_REPO_ROOT / "source" / "manuals"
    result = build_inventory(
        manuals_root,
        repo_root=_REAL_REPO_ROOT,
        source_name="codeaster-doc",
        source_commit="9c8c179f57ef7ca1d2891cac275ee4823a57967c",
        now=FIXED_NOW,
    )

    assert len(result.documents) == 2047
    from collections import Counter

    family_counts = Counter(d.family for d in result.documents)
    assert family_counts == {
        "V": 1303,
        "U4": 257,
        "R": 231,
        "D": 114,
        "U2": 64,
        "U3": 36,
        "U7": 24,
        "U1": 7,
        "SV": 6,
        "SU": 4,
        "U0": 1,
    }

    anomaly_counts = Counter(a.kind for a in result.anomalies)
    assert anomaly_counts == {
        "unresolved_toctree_entry": 14,
        "orphan_file": 14,
        "label_directory_mismatch": 3,
        "empty_component_file": 3,
        "duplicate_document_id": 1,
    }
