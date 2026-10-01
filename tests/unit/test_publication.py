"""Tests de `aster_expert.publication` et du crochet `pre-commit` (lot 41 ter).

Les dépôts Git sont créés localement dans `tmp_path` ; les secrets d'essai sont
assemblés à l'exécution, pour que ce fichier n'en contienne aucun.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from aster_expert.publication import (
    PublicationRules,
    check_file,
    check_index,
    check_tree,
    load_rules,
    main,
)

_REPO = Path(__file__).resolve().parents[2]
_HOOK = _REPO / "scripts" / "git-hooks" / "pre-commit"
_GITHUB_TOKEN = "ghp" + "_" + "A1b2C3d4" * 5
_PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY-----\nabc\n"
_URL_WITH_PASSWORD = "https://moi" + ":" + "motdepasse@example.com/x"


def _rules(**changes: object) -> PublicationRules:
    rules = load_rules(_REPO)
    return rules.model_copy(update=changes)


def _check(path: str, data: bytes, rules: PublicationRules | None = None) -> list[str]:
    rules = rules or _rules()
    return [v.reason for v in check_file(path, len(data), lambda: data, rules)]


def test_repository_rules_set_the_50_mb_limit() -> None:
    assert load_rules(_REPO).max_file_bytes == 50 * 1024 * 1024


def test_a_file_over_the_limit_is_refused_without_being_read() -> None:
    rules = _rules(max_file_bytes=10)

    def never() -> bytes:
        raise AssertionError("un fichier trop gros n'est pas lu")

    found = check_file("data/resultat.med", 11, never, rules)
    assert [v.reason for v in found] == ["0.0 Mo, au-delà de 0 Mo"]


@pytest.mark.parametrize(
    ("path", "fragment"),
    [
        ("docs/calcul_3d_v5.comm", "fichier de MM"),
        ("data/PANG/coupe.txt", "PANG"),
        ("normes/NF_P_94-282.pdf", "NF P 94-282"),
        ("normes/extrait_afnor.txt", "AFNOR"),
        ("images/salome_meca.sif", "Singularity"),
        (".env", "environnement local"),
        ("cles/id_rsa", "clé privée"),
        ("cles/serveur.pem", "clé privée"),
        (".claude/settings.local.json", "réglages locaux"),
    ],
)
def test_forbidden_paths_are_refused(path: str, fragment: str) -> None:
    reasons = _check(path, b"x")
    assert reasons, path
    assert fragment in reasons[0]


@pytest.mark.parametrize(
    "path",
    [
        "docs/development-plan.md",
        "src/aster_expert/mcp/check.py",
        "data/examples/lot27_maillage/med/combiwall_mesh.med",
        ".env.example",
        "tests/unit/test_expanding.py",
    ],
)
def test_ordinary_paths_pass(path: str) -> None:
    assert _check(path, b"texte ordinaire\n") == []


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (f"token = {_GITHUB_TOKEN}\n", "jeton GitHub"),
        (_PRIVATE_KEY, "clé privée"),
        (f"url = {_URL_WITH_PASSWORD}\n", "identifiants dans une URL"),
    ],
)
def test_secrets_in_text_are_refused(content: str, reason: str) -> None:
    assert _check("notes.txt", content.encode()) == [reason]


def test_binary_contents_are_not_scanned() -> None:
    assert _check("data/x.bin", b"\0" + _GITHUB_TOKEN.encode()) == []


def test_naming_a_forbidden_file_in_a_text_is_allowed() -> None:
    # La règle porte sur les fichiers, pas sur leur mention : le plan de
    # développement cite les noms des fichiers de MM sans leur contenu.
    assert _check("docs/plan.md", b"Couverture de `calcul_3d_v3.comm` : 80 %\n") == []


def test_versioned_tree_holds_no_violation() -> None:
    if not (_REPO / ".git").exists():
        pytest.skip("pas de dépôt Git")
    assert check_tree(_REPO, load_rules(_REPO)) == []


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    root = tmp_path / "depot"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "essai@example.invalid")
    _git(root, "config", "user.name", "Essai")
    (root / "config").mkdir()
    shutil.copyfile(
        _REPO / "config" / "publication.yaml", root / "config" / "publication.yaml"
    )
    return root


def test_check_index_reads_the_staged_content(depot: Path) -> None:
    secret = depot / "notes.txt"
    secret.write_text(_GITHUB_TOKEN + "\n", encoding="utf-8")
    _git(depot, "add", "notes.txt", "config/publication.yaml")
    # Le contenu indexé fait foi, pas celui de l'arbre de travail.
    secret.write_text("propre\n", encoding="utf-8")
    found = check_index(depot, load_rules(depot))
    assert [(v.path, v.reason) for v in found] == [("notes.txt", "jeton GitHub")]


def test_main_exit_codes(depot: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(depot)
    assert main(["--autre"]) == 2
    _git(depot, "add", "config/publication.yaml")
    assert main(["--index"]) == 0
    (depot / "salome_meca.sif").write_bytes(b"x")
    _git(depot, "add", "salome_meca.sif")
    assert main(["--index"]) == 1
    _git(depot, "commit", "-q", "--no-verify", "-m", "essai")
    assert main(["--arbre"]) == 1


def test_pre_commit_hook_refuses_a_secret(depot: Path) -> None:
    assert _HOOK.stat().st_mode & stat.S_IXUSR
    hooks = depot / "scripts" / "git-hooks"
    hooks.mkdir(parents=True)
    shutil.copyfile(_HOOK, hooks / "pre-commit")
    (hooks / "pre-commit").chmod(0o755)
    # Le crochet appelle le Python du .venv du dépôt : celui du dépôt réel.
    (depot / ".venv").symlink_to(_REPO / ".venv")
    _git(depot, "config", "core.hooksPath", "scripts/git-hooks")
    (depot / "cle.txt").write_text(_PRIVATE_KEY, encoding="utf-8")
    _git(depot, "add", "cle.txt", "config/publication.yaml")
    env = {**os.environ, "PYTHONPATH": str(_REPO / "src")}
    refused = subprocess.run(
        ["git", "-C", str(depot), "commit", "-q", "-m", "essai"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert refused.returncode == 1
    assert "cle.txt : clé privée" in refused.stderr
    _git(depot, "rm", "-q", "--cached", "cle.txt")
    accepted = subprocess.run(
        ["git", "-C", str(depot), "commit", "-q", "-m", "essai"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stderr
