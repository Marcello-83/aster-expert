"""Unit tests for `aster_expert.ingestion.xref` (lot 6, I4).

Synthetic fixtures only, including the one real defect shape found on the
17.4.0 corpus (`man_v/v6/v6.08.120/Probl_mes_de_r_f_rence.rst`): a
`:ref:`...`` role wrapped, apparently by accident, around a Python array
literal rather than a document id — a genuine corpus defect that this
module must report as unresolvable, never crash on or silently drop.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.xref import (
    build_reference_graph,
    build_reference_graph_result,
    extract_references,
    load_inventory_documents,
    write_xref_json,
)

FIXED_NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)


def test_extract_references_finds_ref_and_external_ref() -> None:
    text = (
        "Voir [:ref:`u4.84.01 <u4.84.01>`] et aussi "
        "[:external:ref:`U4.63.12 <U4.63.12>`]."
    )
    assert extract_references(text) == ["u4.84.01", "U4.63.12"]


def test_extract_references_ignores_numref_and_eq() -> None:
    # `:numref:`/`:eq:` target figure/equation labels, not documents (lot 6,
    # I3) — out of scope for this document-level graph.
    text = "Voir :numref:`fig-un <fig-un>` et :eq:`eq-un <eq-un>`."
    assert extract_references(text) == []


def test_extract_references_handles_real_corpus_defect_verbatim() -> None:
    # Verbatim shape of man_v/v6/v6.08.120/Probl_mes_de_r_f_rence.rst:67 —
    # a `:ref:` role wrapped around a Python array literal, not a document
    # id. Never crashes: the malformed target is extracted as-is.
    text = "lamort= NU.array([:ref:`0.0, 0.0, 0.0, <0.0, 0.0, 0.0,>`])"
    targets = extract_references(text)
    assert targets == ["0.0, 0.0, 0.0,"]


def test_build_reference_graph_classifies_resolvable_and_unresolvable(
    tmp_path: Path,
) -> None:
    doc_a = tmp_path / "u4.84.01"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text(
        "Voir :ref:`u4.52.02 <u4.52.02>` et :ref:`z9.99.99 <z9.99.99>`.\n",
        encoding="utf-8",
    )
    doc_b = tmp_path / "u4.52.02"
    doc_b.mkdir()
    (doc_b / "index.rst").write_text("Rien à voir ici.\n", encoding="utf-8")

    document_dirs = {"U4.84.01": doc_a, "U4.52.02": doc_b}
    known_ids = set(document_dirs)

    graph = build_reference_graph(document_dirs, known_ids)

    assert graph.total_references == 2
    assert graph.resolvable_references == 1
    assert graph.unresolvable_references == 1
    assert graph.edges[("U4.84.01", "U4.52.02")] == 1
    assert graph.unresolved[("U4.84.01", "z9.99.99")] == 1


def test_build_reference_graph_result_end_to_end(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    doc_a = repo_root / "source" / "manuals" / "man_u" / "u4" / "u4.84.01"
    doc_a.mkdir(parents=True)
    (doc_a / "index.rst").write_text(
        "Voir :ref:`u4.52.02 <u4.52.02>`.\n", encoding="utf-8"
    )
    doc_b = repo_root / "source" / "manuals" / "man_u" / "u4" / "u4.52.02"
    doc_b.mkdir(parents=True)
    (doc_b / "index.rst").write_text("Rien.\n", encoding="utf-8")

    inventory_path = tmp_path / "inventory.jsonl"
    with inventory_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "document_id": "U4.84.01",
                    "relative_path": "source/manuals/man_u/u4/u4.84.01",
                }
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {
                    "document_id": "U4.52.02",
                    "relative_path": "source/manuals/man_u/u4/u4.52.02",
                }
            )
            + "\n"
        )

    result = build_reference_graph_result(
        inventory_path=inventory_path,
        repo_root=repo_root,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    assert result.total_references == 1
    assert result.resolvable_references == 1
    assert result.edges == (
        result.edges[0].__class__(
            source_document_id="U4.84.01", target_document_id="U4.52.02", count=1
        ),
    )

    output_path = tmp_path / "xref.json"
    write_xref_json(result, output_path)
    reloaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert reloaded["total_references"] == 1


def test_load_inventory_documents(tmp_path: Path) -> None:
    inventory_path = tmp_path / "inventory.jsonl"
    inventory_path.write_text(
        json.dumps({"document_id": "V3.03.100", "relative_path": "a/b"}) + "\n",
        encoding="utf-8",
    )
    assert load_inventory_documents(inventory_path) == {"V3.03.100": "a/b"}
