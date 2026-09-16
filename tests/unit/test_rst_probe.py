"""Unit tests for `aster_expert.ingestion.rst_probe` (lot 6, I3).

Synthetic reST snippets only, chosen to reproduce the exact shapes found on
the real `codeaster-doc` corpus (a Sphinx-only role, a Sphinx-only
directive, a bare-docutils `.. math::` block, an `.. include::` pointing at
the generated, never-committed `_cache/` directory) — never network, never
the real checkout.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.rst_probe import (
    build_probe_report,
    find_conf_py_extensions,
    load_inventory_index,
    probe_documents,
    probe_source,
    stratified_sample_by_family,
    write_probe_report_json,
)

FIXED_NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)


def test_probe_source_recognizes_math_block_natively() -> None:
    # `.. math::` and `:math:` ship with bare docutils (no Sphinx needed):
    # this is the concrete evidence behind the lot 6 arbitrage note "formules
    # conservées en LaTeX".
    text = "\n.. math::\n    \\sigma = E \\varepsilon\n"
    result = probe_source(text)
    assert result.unknown_directives == ()
    assert result.unresolved_includes == ()
    assert "sigma" in text  # the LaTeX macro itself, never rewritten


def test_probe_source_flags_unknown_sphinx_role_but_keeps_text() -> None:
    text = "Voir :ref:`u4.84.01 <u4.84.01>` pour plus de détails.\n"
    result = probe_source(text)
    assert result.unknown_roles == ("ref",)
    # The raw role markup survives verbatim inside the `problematic` node:
    # nothing is dropped, only left unresolved as a cross-reference.
    assert result.recoverable_chars >= len("u4.84.01")


def test_probe_source_flags_unknown_sphinx_directive_but_keeps_body() -> None:
    text = "\n.. toctree::\n    :maxdepth: 2\n\n    But\n    Syntaxe\n"
    result = probe_source(text)
    assert result.unknown_directives == ("toctree",)
    # The full directive body (including its entries) is echoed verbatim in
    # a literal_block nested under the system_message: recoverable, not
    # lost, even though it is nested under the diagnostic node.
    assert result.recoverable_chars > 0


def test_probe_source_reports_unresolved_include_target() -> None:
    text = "\n.. include:: ../../../../../_cache/math_styles.rst\n"
    result = probe_source(text)
    assert result.unresolved_includes == ("/_cache/math_styles.rst",)
    # Unlike an unknown directive/role, this is the one genuine content gap
    # (docs/development-plan.md, lot 6, I3): only the `.. include::` line
    # itself (the directive's own raw text, echoed in a literal_block) is
    # recoverable here — the *included* file's content, absent from the
    # pre-build checkout, cannot appear anywhere in the doctree, so what
    # comes back is strictly less than the directive line plus whatever
    # `_cache/math_styles.rst` would have contributed.
    assert result.recoverable_chars < result.raw_chars
    assert result.recoverable_chars == len(text.strip())


def test_probe_source_recovers_almost_all_plain_prose() -> None:
    text = "Un paragraphe de prose tout à fait ordinaire, sans markup.\n"
    result = probe_source(text)
    # docutils normalizes the paragraph's trailing newline away: the one
    # character of difference is that normalization, not lost content.
    assert result.recoverable_chars == len(text.rstrip("\n"))
    assert result.unknown_directives == ()
    assert result.unknown_roles == ()
    assert result.unresolved_includes == ()


def test_probe_documents_aggregates_across_files(tmp_path: Path) -> None:
    doc_a = tmp_path / "u4.01.00"
    doc_a.mkdir()
    (doc_a / "index.rst").write_text(
        "\n.. toctree::\n    :maxdepth: 2\n\n    But\n", encoding="utf-8"
    )
    (doc_a / "But.rst").write_text("Un texte normal.\n", encoding="utf-8")

    doc_b = tmp_path / "r7.01.03"
    doc_b.mkdir()
    (doc_b / "index.rst").write_text(
        "\n.. include:: ../../_cache/math_styles.rst\n", encoding="utf-8"
    )

    aggregate = probe_documents([doc_a, doc_b])

    assert aggregate.sampled_documents == 2
    assert aggregate.sampled_files == 3
    assert aggregate.unknown_directives["toctree"] == 1
    assert aggregate.unresolved_includes
    assert 0.0 < aggregate.recovery_ratio < 1.0


def test_stratified_sample_by_family_is_deterministic_and_evenly_spaced() -> None:
    documents_by_family = {
        "R": [f"R{n:02d}" for n in range(10)],
        "SU": ["SU1", "SU2"],
    }
    first = stratified_sample_by_family(documents_by_family, {"R": 4, "SU": 5})
    second = stratified_sample_by_family(documents_by_family, {"R": 4, "SU": 5})

    assert first == second  # deterministic, never a random draw
    assert len(first["R"]) == 4
    # SU only has 2 documents: asking for 5 returns all of them, not a
    # fabricated extra entry.
    assert first["SU"] == ["SU1", "SU2"]


def test_find_conf_py_extensions_reads_without_executing(tmp_path: Path) -> None:
    conf_py = tmp_path / "conf.py"
    conf_py.write_text(
        "import os\n"
        "raise RuntimeError('never actually run')\n"
        'extensions = ["sphinx.ext.autosectionlabel", "sphinx.ext.intersphinx"]\n',
        encoding="utf-8",
    )
    extensions = find_conf_py_extensions(conf_py)
    assert extensions == ("sphinx.ext.autosectionlabel", "sphinx.ext.intersphinx")


def _write_inventory(path: Path, entries: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


def test_load_inventory_index_groups_by_family(tmp_path: Path) -> None:
    inventory_path = tmp_path / "inventory.jsonl"
    _write_inventory(
        inventory_path,
        [
            {
                "document_id": "U4.01.00",
                "family": "U4",
                "relative_path": "source/manuals/man_u/u4/u4.01.00",
            },
            {
                "document_id": "SU1.02.01",
                "family": "SU",
                "relative_path": "source/manuals/man_s/su1/su1.02.01",
            },
        ],
    )
    by_family, relative_path_by_id = load_inventory_index(inventory_path)
    assert by_family == {"U4": ["U4.01.00"], "SU": ["SU1.02.01"]}
    assert relative_path_by_id["SU1.02.01"] == "source/manuals/man_s/su1/su1.02.01"


def test_build_probe_report_end_to_end(tmp_path: Path) -> None:
    repo_root = tmp_path / "codeaster-doc"
    manuals = repo_root / "source" / "manuals"

    doc_u4 = manuals / "man_u" / "u4" / "u4.01.00"
    doc_u4.mkdir(parents=True)
    (doc_u4 / "index.rst").write_text(
        "\n.. toctree::\n    :maxdepth: 2\n\n    But\n", encoding="utf-8"
    )
    (doc_u4 / "But.rst").write_text(
        "Un texte normal sur l'opérateur.\n", encoding="utf-8"
    )

    doc_su1 = manuals / "man_s" / "su1" / "su1.02.01"
    doc_su1.mkdir(parents=True)
    (doc_su1 / "index.rst").write_text(
        "Un texte normal sur Salome-Meca.\n", encoding="utf-8"
    )

    inventory_path = tmp_path / "inventory.jsonl"
    _write_inventory(
        inventory_path,
        [
            {
                "document_id": "U4.01.00",
                "family": "U4",
                "relative_path": "source/manuals/man_u/u4/u4.01.00",
            },
            {
                "document_id": "SU1.02.01",
                "family": "SU",
                "relative_path": "source/manuals/man_s/su1/su1.02.01",
            },
        ],
    )

    conf_py = repo_root / "source" / "conf.py"
    conf_py.write_text(
        'extensions = ["sphinx.ext.autosectionlabel"]\n', encoding="utf-8"
    )

    report = build_probe_report(
        inventory_path=inventory_path,
        repo_root=repo_root,
        conf_py_path=conf_py,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        per_family={"U4": 1, "man_s": 1},
        now=FIXED_NOW,
    )

    assert report.sampled_documents == 2
    assert report.sample_per_family == {"U4": ("U4.01.00",), "man_s": ("SU1.02.01",)}
    assert [d.name for d in report.unknown_directives] == ["toctree"]
    assert report.conf_py_extensions == ("sphinx.ext.autosectionlabel",)
    assert report.source_commit == "deadbeef"

    output_path = tmp_path / "report.json"
    write_probe_report_json(report, output_path)
    reloaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert reloaded["sampled_documents"] == 2
