"""Reproducibility of the combi-wall reference fiche (lot 20, step 6; lot 21).

`scripts/build_combiwall_reference.py` rebuilds
`data/examples/hypotheses_combiwall_reference_arbitree.json` from the
versioned inputs; this test replays it in a temporary directory and compares
the result byte for byte with the versioned JSON. The fiche carries no
machine timestamp (`created_at` comes from the unarbitrated base), so nothing
is neutralized.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "build_combiwall_reference.py"
_VERSIONED = (
    _ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
)
_INPUTS = _ROOT / "data" / "examples" / "combiwall_inputs"
_DOC_ROOT = _ROOT / "external" / "codeaster-doc"


def test_replaying_the_build_script_reproduces_the_versioned_json(
    tmp_path: Path,
) -> None:
    output = tmp_path / "rebuilt.json"

    subprocess.run(
        [sys.executable, str(_SCRIPT), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.read_text(encoding="utf-8") == _VERSIONED.read_text(encoding="utf-8")


def test_arbitration_inputs_carry_no_unresolved_confirmation_marker() -> None:
    # v4 quotes the marker once, in its status sentence (how to read a marked
    # passage); no passage of any file carries it any more (lot 23).
    status_sentence = "Les passages marqués **[À CONFIRMER MM]** doivent"
    for path in _INPUTS.glob("*.md"):
        text = path.read_text(encoding="utf-8").replace(status_sentence, "")
        assert "À CONFIRMER" not in text, path.name


def test_every_excerpt_is_verbatim_in_the_documentation_clone() -> None:
    """Skipped when `external/` is absent (never committed, CLAUDE.md)."""
    if not _DOC_ROOT.is_dir():
        pytest.skip("external/codeaster-doc absent")
    for name in ("lot20_extraits.json", "lot21_extraits.json", "lot23_extraits.json"):
        extracts = json.loads((_INPUTS / name).read_text("utf-8"))
        assert extracts
        for x in extracts:
            lines = (_DOC_ROOT / x["source_path"]).read_text("utf-8").split("\n")
            assert x["text"] == "\n".join(lines[x["line_start"] - 1 : x["line_end"]]), (
                name,
                x["id"],
            )
