"""Unit tests for `aster_expert.ingestion.xref` (lot 6, I4 ; lot 6b, X1).

Synthetic fixtures only, including:

- the one real defect shape found on the 17.4.0 corpus
  (`man_v/v6/v6.08.120/Probl_mes_de_r_f_rence.rst`): a `:ref:`...`` role
  wrapped, apparently by accident, around a Python array literal rather
  than a document id — a genuine corpus defect this module must report as
  unresolved, never crash on or silently drop;
- the `:external:ref:` (intersphinx) categorization, always external by
  construction, never checked against the local domain (lot 6b, X1);
- the `autosectionlabel` mechanism, reproduced exactly as
  `sphinx.ext.autosectionlabel.register_sections_as_label` implements it
  (depth-0 sections only, raw title source, no document prefix) — real
  corpus measurement (lot 6b compte rendu): it resolves zero references
  on the 17.4.0 corpus, but the mechanism itself is exercised and tested
  here, never assumed away.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.xref import (
    build_autosectionlabel_index,
    build_reference_graph,
    build_reference_graph_result,
    extract_references,
    extract_top_section_labels,
    load_inventory_documents,
    normalize_label_name,
    write_xref_json,
)

FIXED_NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)


def test_extract_references_distinguishes_ref_and_external_ref() -> None:
    text = (
        "Voir [:ref:`u4.84.01 <u4.84.01>`] et aussi "
        "[:external:ref:`U4.63.12 <U4.63.12>`]."
    )
    occurrences = extract_references(text)
    assert [(o.role, o.raw_target) for o in occurrences] == [
        ("ref", "u4.84.01"),
        ("external:ref", "U4.63.12"),
    ]


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
    occurrences = extract_references(text)
    assert [o.raw_target for o in occurrences] == ["0.0, 0.0, 0.0,"]


def test_normalize_label_name_lowercases_and_collapses_whitespace() -> None:
    # Mirrors docutils.nodes.fully_normalize_name exactly.
    assert normalize_label_name("  Opérateur   COMB_SISM_MODAL ") == (
        "opérateur comb_sism_modal"
    )


def test_extract_top_section_labels_uses_raw_source_not_rendered_text() -> None:
    # Real shape (index.rst): the title's *raw* markup, "**id**" included,
    # becomes the label — never the resolved/rendered text.
    text = "\n.. _u4.84.01:\n\n**u4.84.01** Opérateur X\n========================\n"
    labels = extract_top_section_labels(text)
    assert labels == ["**u4.84.01** opérateur x"]


def test_extract_top_section_labels_plain_child_file_title() -> None:
    # Real shape (a child file like But.rst): a plain title, no bold "id"
    # marker — still depth 0 within its own file.
    text = "But\n===\n\nCalculer la réponse.\n"
    assert extract_top_section_labels(text) == ["but"]


def test_extract_top_section_labels_skips_deeper_subsections() -> None:
    # autosectionlabel_maxdepth = 1 on this corpus: only the depth-0
    # section is kept, a nested subsection is never registered.
    text = "Titre principal\n================\n\nSous-titre\n----------\n\nDu texte.\n"
    assert extract_top_section_labels(text) == ["titre principal"]


def test_build_autosectionlabel_index_covers_every_rst_file(tmp_path: Path) -> None:
    doc_dir = tmp_path / "u4.84.01"
    doc_dir.mkdir()
    (doc_dir / "index.rst").write_text(
        "**u4.84.01** Opérateur X\n========================\n", encoding="utf-8"
    )
    (doc_dir / "But.rst").write_text("But\n===\n\nTexte.\n", encoding="utf-8")

    index = build_autosectionlabel_index({"U4.84.01": doc_dir})

    assert index["**u4.84.01** opérateur x"] == [("U4.84.01", "index.rst")]
    assert index["but"] == [("U4.84.01", "But.rst")]


def test_build_reference_graph_resolves_via_explicit_label(tmp_path: Path) -> None:
    doc_a = tmp_path / "u4.84.01"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text(
        "Voir :ref:`u4.52.02 <u4.52.02>`.\n", encoding="utf-8"
    )
    doc_b = tmp_path / "u4.52.02"
    doc_b.mkdir()
    (doc_b / "index.rst").write_text("Rien.\n", encoding="utf-8")

    document_dirs = {"U4.84.01": doc_a, "U4.52.02": doc_b}
    graph = build_reference_graph(document_dirs, set(document_dirs), {})

    assert graph.total_references == 1
    assert graph.internal_resolved_references == 1
    assert graph.edges[("U4.84.01", "U4.52.02", "explicit_label")] == 1


def test_build_reference_graph_resolves_via_autosectionlabel(tmp_path: Path) -> None:
    # A target that is not a known document id, but matches exactly one
    # document's registered top-level title.
    doc_a = tmp_path / "u4.84.01"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text(
        "Voir la :ref:`Solution analytique <Solution analytique>`.\n",
        encoding="utf-8",
    )
    doc_b = tmp_path / "v1.01.001"
    doc_b.mkdir()
    (doc_b / "Solution.rst").write_text(
        "Solution analytique\n====================\n", encoding="utf-8"
    )

    document_dirs = {"U4.84.01": doc_a, "V1.01.001": doc_b}
    autosectionlabel_index = build_autosectionlabel_index(document_dirs)
    graph = build_reference_graph(
        document_dirs, set(document_dirs), autosectionlabel_index
    )

    assert graph.internal_resolved_references == 1
    assert graph.edges[("U4.84.01", "V1.01.001", "autosectionlabel")] == 1


def test_build_reference_graph_flags_ambiguous_autosectionlabel(
    tmp_path: Path,
) -> None:
    # Two distinct documents register the exact same top-level title:
    # Sphinx would pick whichever was processed last (a build-order
    # dependency we cannot replicate) — reported as ambiguous, never
    # guessed.
    doc_a = tmp_path / "u4.84.01"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text("Voir :ref:`Résumé <Résumé>`.\n", encoding="utf-8")
    doc_b = tmp_path / "v1.01.001"
    doc_b.mkdir()
    (doc_b / "index.rst").write_text("Résumé\n======\n", encoding="utf-8")
    doc_c = tmp_path / "v1.01.002"
    doc_c.mkdir()
    (doc_c / "index.rst").write_text("Résumé\n======\n", encoding="utf-8")

    document_dirs = {"U4.84.01": doc_a, "V1.01.001": doc_b, "V1.01.002": doc_c}
    autosectionlabel_index = build_autosectionlabel_index(document_dirs)
    graph = build_reference_graph(
        document_dirs, set(document_dirs), autosectionlabel_index
    )

    assert graph.internal_resolved_references == 0
    assert graph.ambiguous_references == 1
    ((_src, _target, candidates), count) = next(iter(graph.ambiguous.items()))
    assert set(candidates) == {"V1.01.001", "V1.01.002"}
    assert count == 1


def test_build_reference_graph_categorizes_external_ref_unconditionally(
    tmp_path: Path,
) -> None:
    # :external:ref: is always dispatched to intersphinx, even when its
    # target also happens to be a valid local document id (real corpus
    # shape: U4.63.12 exists locally yet is referenced via
    # :external:ref: in man_u/u4/u4.84.01/Op_randes.rst).
    doc_a = tmp_path / "u4.84.01"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text(
        "Voir :external:ref:`U4.63.12 <U4.63.12>`.\n", encoding="utf-8"
    )
    doc_b = tmp_path / "u4.63.12"
    doc_b.mkdir()
    (doc_b / "index.rst").write_text("Rien.\n", encoding="utf-8")

    document_dirs = {"U4.84.01": doc_a, "U4.63.12": doc_b}
    graph = build_reference_graph(document_dirs, set(document_dirs), {})

    assert graph.internal_resolved_references == 0
    assert graph.external_references == 1
    assert graph.external[("U4.84.01", "U4.63.12")] == 1


def test_build_reference_graph_truly_unresolved(tmp_path: Path) -> None:
    doc_a = tmp_path / "u4.84.01"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text("Voir :ref:`bib1 <bib1>`.\n", encoding="utf-8")

    document_dirs = {"U4.84.01": doc_a}
    graph = build_reference_graph(document_dirs, set(document_dirs), {})

    assert graph.unresolved_references == 1
    assert graph.unresolved[("U4.84.01", "bib1")] == 1


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
    assert result.internal_resolved_references == 1
    assert result.edges == (
        result.edges[0].__class__(
            source_document_id="U4.84.01",
            target_document_id="U4.52.02",
            via="explicit_label",
            count=1,
        ),
    )
    assert result.autosectionlabel_prefix_document is False
    assert result.autosectionlabel_maxdepth == 1

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
