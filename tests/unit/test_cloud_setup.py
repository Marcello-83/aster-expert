"""Tests de `scripts/cloud_setup.sh` (lot 41 ter), sans réseau ni Docker.

Le script recopie des constantes de la configuration (commits du corpus, digest
de l'image, version de Python) parce qu'il doit pouvoir tourner sans le dépôt,
collé dans la configuration de l'environnement Cloud : ces tests échouent dès
qu'une copie diverge, et quand le texte de `docs/cloud.md` n'est plus celui du
script.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "cloud_setup.sh"


def _constants() -> dict[str, str]:
    text = _SCRIPT.read_text(encoding="utf-8")
    return dict(re.findall(r'^([A-Z_]+)="([^"$]*)"$', text, flags=re.MULTILINE))


def test_corpus_constants_match_sources_yaml() -> None:
    config = yaml.safe_load((_REPO / "config" / "sources.yaml").read_text("utf-8"))
    sources = {s["name"]: s for s in config["sources"]}
    constants = _constants()
    for prefix, name in (("SRC", "codeaster-src"), ("DOC", "codeaster-doc")):
        assert constants[f"{prefix}_URL"] == sources[name]["url"]
        assert constants[f"{prefix}_REF"] == sources[name]["ref"]
        assert constants[f"{prefix}_COMMIT"] == sources[name]["commit"]
        assert sources[name]["local_path"] == f"external/{name}"


def test_image_constants_match_versions_yaml() -> None:
    versions = yaml.safe_load((_REPO / "config" / "versions.yaml").read_text("utf-8"))
    container = versions["detected"]["container"]
    constants = _constants()
    assert constants["IMAGE_REPOSITORY"] == container["image_repository"]
    assert constants["IMAGE_DIGEST"] == container["image_digest"]
    assert constants["IMAGE_TAG"] == container["image_tag"]
    assert constants["IMAGE_TAG"] not in ("stable", "testing")


def test_python_constant_matches_python_version_file() -> None:
    pin = (_REPO / ".python-version").read_text(encoding="utf-8").strip()
    assert _constants()["PYTHON_VERSION"] == pin


def test_script_is_valid_bash() -> None:
    subprocess.run(["bash", "-n", str(_SCRIPT)], check=True)


def _run(
    *args: str, env: dict[str, str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
        timeout=60,
    )


def test_session_mode_does_nothing_outside_the_cloud(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    env_file = tmp_path / "env"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "ASTER_CLOUD_CACHE": str(cache),
        "CLAUDE_ENV_FILE": str(env_file),
    }
    result = _run("--session", env=env, cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""
    assert not cache.exists()
    assert not env_file.exists()


def test_unknown_argument_is_refused(tmp_path: Path) -> None:
    env = {"PATH": os.environ["PATH"], "ASTER_CLOUD_CACHE": str(tmp_path / "c")}
    result = _run("--autre", env=env, cwd=tmp_path)
    assert result.returncode == 2
    assert "usage" in result.stderr


def test_cloud_md_carries_the_script_verbatim() -> None:
    doc = (_REPO / "docs" / "cloud.md").read_text(encoding="utf-8")
    script = _SCRIPT.read_text(encoding="utf-8")
    assert f"```bash\n{script}```\n" in doc


def test_session_start_hook_runs_the_script_in_session_mode() -> None:
    settings = json.loads((_REPO / ".claude" / "settings.json").read_text("utf-8"))
    hooks = settings["hooks"]["SessionStart"]
    commands = [h["command"] for entry in hooks for h in entry["hooks"]]
    assert commands == ['bash "$CLAUDE_PROJECT_DIR/scripts/cloud_setup.sh" --session']
    assert {entry["matcher"] for entry in hooks} == {"startup|resume"}


def test_cloud_products_are_ignored_by_git() -> None:
    if not (_REPO / ".git").exists():
        pytest.skip("pas de dépôt Git")
    text = _SCRIPT.read_text(encoding="utf-8")
    block = text[text.index("DONNEES=(") : text.index(")", text.index("DONNEES=("))]
    paths = [line.strip() for line in block.splitlines()[1:] if line.strip()]
    assert "data/processed/catalogue" in paths
    paths += ["external/codeaster-src", "external/codeaster-doc"]
    result = subprocess.run(
        ["git", "-C", str(_REPO), "check-ignore", "--no-index", *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    assert sorted(result.stdout.split()) == sorted(paths)
