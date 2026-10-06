"""Lot 47 ter, ENV-002: a long-lived process (the MCP server) keeps the schema of the
knowledge base it imported at start, while the base is read again at every call.

The failure of lot 47 bis is replayed in a child process on a copy of the sources and
of the base: the schema and one entry gain a field together, after the first search.
Without the refresh the whole base is refused (as in lot 47 bis); with it, the search
answers again (same hit as before the change). The repository itself is never modified.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from aster_expert.connaissances import fraicheur

ROOT = Path(__file__).resolve().parents[2]

CHILD = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path

    src, repo = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(src))
    from aster_expert.mcp import tools
    from aster_expert.connaissances import fraicheur

    log = repo / "journal.jsonl"
    out = {}

    def search():
        try:
            r = tools.search_connaissances(
                project_root=repo, layers=["controles"], limit=1, log_path=log
            )
            return {"ok": [h.id for h in r.results]}
        except Exception as exc:  # the failure of lot 47 bis
            return {"erreur": type(exc).__name__, "message": str(exc)[:400]}

    out["avant"] = search()
    # The session changes the schema and the base together (as in lot 47 bis).
    modeles = src / "aster_expert" / "connaissances" / "modeles.py"
    text = modeles.read_text("utf-8")
    anchor = (
        '    id_pattern: ClassVar[re.Pattern[str]] = '
        're.compile(r"^CTL-\\\\d{3}$")\\n'
    )
    assert text.count(anchor) == 1, "ancre du modèle Control introuvable"
    modeles.write_text(
        text.replace(anchor, anchor + "    essai_fraicheur: int = 0\\n"), "utf-8"
    )
    entry = repo / "connaissances" / "controles" / "CTL-001.yaml"
    entry.write_text(
        entry.read_text("utf-8") + "essai_fraicheur: 1\\n", "utf-8"
    )
    out["perime"] = fraicheur.is_stale()
    real = fraicheur.refresh_if_stale
    fraicheur.refresh_if_stale = lambda: False  # the server of lot 47 bis
    out["sans_rechargement"] = search()
    fraicheur.refresh_if_stale = real
    out["avec_rechargement"] = search()
    out["perime_apres"] = fraicheur.is_stale()
    print(json.dumps(out))
    """
)


def test_a_schema_changed_during_the_session_is_reloaded(tmp_path: Path) -> None:
    src = tmp_path / "src"
    shutil.copytree(
        ROOT / "src" / "aster_expert",
        src / "aster_expert",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    repo = tmp_path / "depot"
    shutil.copytree(ROOT / "connaissances", repo / "connaissances")
    script = tmp_path / "enfant.py"
    script.write_text(CHILD, "utf-8")
    done = subprocess.run(
        [sys.executable, "-I", str(script), str(src), str(repo)],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        cwd=tmp_path,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert "ok" in out["avant"]
    assert out["perime"] is True
    # Lot 47 bis: the old schema refuses the new field, the whole base fails.
    assert out["sans_rechargement"]["erreur"] == "KnowledgeBaseError"
    assert "Extra inputs are not permitted" in out["sans_rechargement"]["message"]
    # Lot 47 ter: reloaded, the search answers as before the change.
    assert out["avec_rechargement"] == out["avant"]
    assert out["perime_apres"] is False


def test_the_fingerprint_covers_the_read_path() -> None:
    assert "aster_expert.connaissances.modeles" in fraicheur.READ_PATH_MODULES
    assert "aster_expert.constats.models" in fraicheur.READ_PATH_MODULES
    assert fraicheur.code_fingerprint() == fraicheur.loaded_fingerprint()
    assert fraicheur.is_stale() is False
    assert fraicheur.refresh_if_stale() is False
