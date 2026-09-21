"""Read-only access to the test-case command files (lot 22).

A local git repository is created in `tmp_path` (CLAUDE.md: no network in unit
tests) and a synchronisation manifest points at its commit. Covers the three
checks the lot names -- search on a known command, bounded reading, refusal of
a path outside the corpus -- plus the provenance guards and the journal.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aster_expert.mcp.errors import McpToolError
from aster_expert.mcp.logging import default_query_log_path
from aster_expert.mcp.testcases import clear_parse_cache
from aster_expert.mcp.tools import read_test_case, search_test_cases

_MAT_COQUE = """\
# ELAS_COQUE dans un commentaire ne compte pas
DEBUT()
MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
MAT = DEFI_MATERIAU(ELAS_COQUE=_F(MEMB_L=1.0, FLEX_L=2.0))
FIN()
"""
_MAT_ELAS = """\
DEBUT()
MAT = DEFI_MATERIAU(ELAS=_F(E=1.0, NU=0.3))
TXT = "DEFI_MATERIAU ELAS_COQUE dans une chaîne"
FIN()
"""
_BROKEN = "DEFI_MATERIAU(ELAS_COQUE=_F(\n"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _commit_corpus(project: Path, message: str) -> None:
    """Commit the corpus working copy and record the new commit in the manifest."""
    repo = project / "external" / "codeaster-src"
    _git(repo, "add", "-A")
    _git(
        repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message
    )
    manifest = project / "data" / "raw" / "manifest.json"
    data = json.loads(manifest.read_text())
    data["sources"][0]["commit"] = _git(repo, "rev-parse", "HEAD")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    clear_parse_cache()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    corpus = tmp_path / "external" / "codeaster-src"
    astest = corpus / "astest"
    astest.mkdir(parents=True)
    (astest / "coque01a.comm").write_text(_MAT_COQUE, encoding="utf-8")
    (astest / "elas01a.comm").write_text(_MAT_ELAS, encoding="utf-8")
    (astest / "coque01a.com1").write_text(_MAT_COQUE, encoding="utf-8")
    (astest / "coque01a.export").write_text("F comm coque01a.comm D 1\n", "utf-8")
    (astest / "coque01a.mail").write_text("FIN\n", encoding="utf-8")
    _git(corpus, "init", "-q")
    _git(corpus, "add", ".")
    _git(
        corpus,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "-m",
        "corpus",
    )
    commit = _git(corpus, "rev-parse", "HEAD")
    manifest = tmp_path / "data" / "raw" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "name": "codeaster-src",
                        "ref": "17.4.0",
                        "commit": commit,
                        "local_path": "external/codeaster-src",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    clear_parse_cache()
    return tmp_path


def test_search_on_a_known_command_matches_structure_not_text(project: Path) -> None:
    result = search_test_cases(project_root=project, command="DEFI_MATERIAU")

    assert result.validation_level == "A"
    assert [h.path for h in result.results] == [
        "coque01a.com1",
        "coque01a.comm",
        "elas01a.comm",
    ]
    assert result.files_scanned == 3  # only command files, not .export/.mail
    assert result.source.source_name == "codeaster-src"
    assert result.source.aster_version == "17.4.0"
    assert len(result.source.source_commit) == 40
    assert result.results[0].line_starts == [4]


def test_search_with_a_keyword_ignores_comments_and_strings(project: Path) -> None:
    result = search_test_cases(
        project_root=project, command="DEFI_MATERIAU", keyword="ELAS_COQUE"
    )

    assert [h.path for h in result.results] == ["coque01a.com1", "coque01a.comm"]
    assert all(h.keyword_paths == ["ELAS_COQUE"] for h in result.results)


def test_search_with_a_dotted_keyword_path_matches_the_tail(project: Path) -> None:
    hit = search_test_cases(
        project_root=project, command="DEFI_MATERIAU", keyword="ELAS_COQUE.FLEX_L"
    )
    miss = search_test_cases(
        project_root=project, command="DEFI_MATERIAU", keyword="ELAS.FLEX_L"
    )

    assert [h.path for h in hit.results] == ["coque01a.com1", "coque01a.comm"]
    assert miss.results == []


def test_search_limit_truncates_and_says_so(project: Path) -> None:
    result = search_test_cases(project_root=project, command="DEFI_MATERIAU", limit=1)

    assert result.total_matches == 3 and len(result.results) == 1
    assert result.truncated is True


def test_search_declares_an_unparsable_file(project: Path) -> None:
    (project / "external/codeaster-src/astest/casse01a.comm").write_text(
        _BROKEN, encoding="utf-8"
    )
    _commit_corpus(project, "casse")

    result = search_test_cases(project_root=project, command="DEFI_MATERIAU")

    assert result.files_unparsable == 1
    assert "casse01a.comm" not in [h.path for h in result.results]


def test_read_a_whole_file_under_the_threshold(project: Path) -> None:
    result = read_test_case(project_root=project, path="coque01a.comm")

    assert result.content == _MAT_COQUE.rstrip("\n")
    assert result.total_lines == 5
    assert (result.line_start, result.line_end) == (1, 5)
    assert result.guidance is None
    assert result.validation_level == "A"


def test_read_by_range(project: Path) -> None:
    result = read_test_case(
        project_root=project, path="coque01a.comm", line_start=4, line_end=4
    )

    assert (
        result.content == "MAT = DEFI_MATERIAU(ELAS_COQUE=_F(MEMB_L=1.0, FLEX_L=2.0))"
    )
    assert (result.line_start, result.line_end) == (4, 4)


def test_read_above_the_threshold_returns_no_content_and_guidance(
    project: Path,
) -> None:
    big = project / "external/codeaster-src/astest/gros01a.comm"
    big.write_text("\n".join(f"X{i} = {i}" for i in range(4000)) + "\n", "utf-8")
    _commit_corpus(project, "gros")

    whole = read_test_case(project_root=project, path="gros01a.comm")
    ranged = read_test_case(
        project_root=project, path="gros01a.comm", line_start=10, line_end=12
    )

    assert whole.content is None
    assert whole.content_length > 20_000 and whole.total_lines == 4000
    assert whole.guidance is not None and "1..4000" in whole.guidance
    assert ranged.content == "X9 = 9\nX10 = 10\nX11 = 11"


def test_read_range_out_of_bounds_or_half_given_is_refused(project: Path) -> None:
    with pytest.raises(McpToolError, match="hors des bornes"):
        read_test_case(
            project_root=project, path="coque01a.comm", line_start=1, line_end=99
        )
    with pytest.raises(McpToolError, match="ensemble"):
        read_test_case(project_root=project, path="coque01a.comm", line_start=1)


@pytest.mark.parametrize(
    "bad",
    [
        "../../../data/raw/manifest.json",
        "../codeaster-src/astest/coque01a.comm",
        "/etc/passwd",
        "coque01a.export",
        "coque01a.mail",
        "sous/coque01a.comm",
    ],
)
def test_read_refuses_a_path_outside_the_corpus_or_not_a_command_file(
    project: Path, bad: str
) -> None:
    with pytest.raises(McpToolError, match="Chemin refusé"):
        read_test_case(project_root=project, path=bad)


def test_read_refuses_a_symbolic_link_leaving_the_corpus(project: Path) -> None:
    secret = project / "secret.comm"
    secret.write_text("SECRET = 1\n", encoding="utf-8")
    (project / "external/codeaster-src/astest/lien.comm").symlink_to(secret)
    _commit_corpus(project, "lien")

    with pytest.raises(McpToolError, match="Chemin refusé"):
        read_test_case(project_root=project, path="lien.comm")


def test_read_unknown_file_fails_loudly(project: Path) -> None:
    with pytest.raises(McpToolError, match="introuvable"):
        read_test_case(project_root=project, path="absent01a.comm")


def test_a_corpus_moved_off_the_recorded_commit_is_refused(project: Path) -> None:
    repo = project / "external/codeaster-src"
    (repo / "astest/nouveau01a.comm").write_text("FIN()\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "n")

    with pytest.raises(McpToolError, match="corpus refusé"):
        search_test_cases(project_root=project, command="DEFI_MATERIAU")
    with pytest.raises(McpToolError, match="corpus refusé"):
        read_test_case(project_root=project, path="coque01a.comm")


def test_a_corpus_with_local_modifications_is_refused(project: Path) -> None:
    (project / "external/codeaster-src/astest/coque01a.comm").write_text(
        "DEBUT()\n", encoding="utf-8"
    )

    with pytest.raises(McpToolError, match="modifications locales"):
        read_test_case(project_root=project, path="coque01a.comm")


def test_a_missing_manifest_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(McpToolError, match="Manifeste"):
        search_test_cases(project_root=tmp_path, command="DEFI_MATERIAU")


def test_every_call_is_journalled_like_the_other_tools(project: Path) -> None:
    search_test_cases(
        project_root=project, command="DEFI_MATERIAU", keyword="ELAS_COQUE"
    )
    read_test_case(project_root=project, path="coque01a.comm", line_start=1, line_end=2)

    lines = [
        json.loads(line)
        for line in default_query_log_path(project).read_text("utf-8").splitlines()
    ]
    assert [line["tool"] for line in lines] == ["search_test_cases", "read_test_case"]
    assert lines[0]["query"] == "DEFI_MATERIAU.ELAS_COQUE"
    assert [r["identifier"] for r in lines[0]["returned"]] == [
        "coque01a.com1",
        "coque01a.comm",
    ]
    assert lines[0]["filters"]["source_commit"] == lines[1]["filters"]["source_commit"]
    assert lines[1]["query"] == "coque01a.comm"
    assert lines[1]["filters"]["line_start"] == "1"
    assert lines[1]["duration_s"] >= 0.0
    # only file names and identifiers, never file content
    assert "MEMB_L" not in default_query_log_path(project).read_text("utf-8")


def test_the_server_registers_the_two_tools() -> None:
    from aster_expert.mcp import server

    names = {t.name for t in server.app._tool_manager.list_tools()}  # noqa: SLF001

    assert {"search_test_cases", "read_test_case"} <= names
