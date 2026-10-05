"""Termes confidentiels d'un projet réel (lot 47, annexe A de la consigne).

La liste vient de MM et vit dans `config/termes_interdits.local.txt`, non
versionné : ce fichier de test n'en contient aucun terme. Les essais de mécanique
emploient des termes inventés ; les deux essais sur le dépôt réel s'ignorent,
avec leur motif, si le fichier local est absent (clone neuf, Cloud, CI).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from aster_expert.publication import (
    TERMS_FILE,
    PublicationRules,
    check_commit_messages,
    check_file,
    check_message,
    check_tree,
    fold,
    load_forbidden_terms,
    load_rules,
    with_forbidden_terms,
)

_REPO = Path(__file__).resolve().parents[2]
_HOOKS = _REPO / "scripts" / "git-hooks"
_ABSENT = (
    f"{TERMS_FILE} absent : la liste des termes confidentiels est fournie par MM "
    "et n'existe que sur sa machine"
)


def _rules_with(*terms: str) -> PublicationRules:
    return load_rules(_REPO).model_copy(
        update={"forbidden_terms": tuple(fold(t) for t in terms)}
    )


def test_fold_ignores_case_and_accents() -> None:
    assert fold("Éléphant ÉTÉ") == "elephant ete"
    assert fold("Ville-Ébène") == fold("VILLE-EBENE")


def test_term_found_in_content_path_and_message_without_printing_it() -> None:
    rules = _rules_with("Saint-Exemple", "XZ-0042")
    data = "Quai de saint-EXEMPLE, réf. xz-0042\n".encode()
    found = check_file("notes.md", len(data), lambda: data, rules)
    assert [v.reason for v in found] == [
        "terme confidentiel n° 1 dans le contenu",
        "terme confidentiel n° 2 dans le contenu",
    ]
    for violation in found:
        assert "exemple" not in violation.reason.casefold()
    in_path = check_file("docs/Saint_Exemple/x.txt", 1, lambda: b"x", rules)
    assert in_path == []  # "_" n'est pas "-" : la comparaison est littérale
    in_path = check_file("docs/saint-exemple.txt", 1, lambda: b"x", rules)
    assert [v.reason for v in in_path] == ["terme confidentiel n° 1 dans le chemin"]
    assert [v.reason for v in check_message("Lot : Saint-Éxemple", rules)] == [
        "terme confidentiel n° 1 dans le message"
    ]


def test_local_file_reading(tmp_path: Path) -> None:
    assert load_forbidden_terms(tmp_path) is None
    (tmp_path / "config").mkdir()
    (tmp_path / TERMS_FILE).write_text(
        "# commentaire\n\n  Éxemple  \nAB_12\n", encoding="utf-8"
    )
    assert load_forbidden_terms(tmp_path) == ("exemple", "ab_12")


def test_local_file_is_ignored_and_refused_by_git() -> None:
    if not (_REPO / ".git").exists():
        pytest.skip("pas de dépôt Git")
    ignored = subprocess.run(
        ["git", "-C", str(_REPO), "check-ignore", "-q", str(TERMS_FILE)], check=False
    )
    assert ignored.returncode == 0
    data = b"x"
    found = check_file(str(TERMS_FILE), 1, lambda: data, load_rules(_REPO))
    assert found and "jamais versée" in found[0].reason


def _real_rules() -> PublicationRules:
    if load_forbidden_terms(_REPO) is None:
        pytest.skip(_ABSENT)
    if not (_REPO / ".git").exists():
        pytest.skip("pas de dépôt Git")
    return with_forbidden_terms(load_rules(_REPO), _REPO)


def test_versioned_tree_holds_no_confidential_term() -> None:
    rules = _real_rules()
    found = [v for v in check_tree(_REPO, rules) if "confidentiel" in v.reason]
    assert found == []


def test_commit_messages_hold_no_confidential_term() -> None:
    assert check_commit_messages(_REPO, _real_rules()) == []


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(_REPO / "src")},
        check=False,
    )


def test_hooks_refuse_a_confidential_term(tmp_path: Path) -> None:
    root = tmp_path / "depot"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "essai@example.invalid")
    _git(root, "config", "user.name", "Essai")
    (root / "config").mkdir()
    shutil.copyfile(
        _REPO / "config" / "publication.yaml", root / "config" / "publication.yaml"
    )
    (root / TERMS_FILE).write_text("Saint-Exemple\n", encoding="utf-8")
    (root / ".gitignore").write_text(f"/{TERMS_FILE.as_posix()}\n", encoding="utf-8")
    hooks = root / "scripts" / "git-hooks"
    hooks.mkdir(parents=True)
    for name in ("pre-commit", "commit-msg"):
        shutil.copyfile(_HOOKS / name, hooks / name)
        (hooks / name).chmod(0o755)
    (root / ".venv").symlink_to(_REPO / ".venv")
    _git(root, "config", "core.hooksPath", "scripts/git-hooks")
    (root / "note.md").write_text("Quai de SAINT-EXEMPLE\n", encoding="utf-8")
    _git(root, "add", ".gitignore", "config/publication.yaml", "note.md")
    refused = _git(root, "commit", "-q", "-m", "essai")
    assert refused.returncode == 1
    assert "note.md : terme confidentiel n° 1 dans le contenu" in refused.stderr
    (root / "note.md").write_text("Quai\n", encoding="utf-8")
    _git(root, "add", "note.md")
    refused = _git(root, "commit", "-q", "-m", "Lot : saint-éxemple")
    assert refused.returncode == 1
    assert "dans le message" in refused.stderr
    accepted = _git(root, "commit", "-q", "-m", "essai")
    assert accepted.returncode == 0, accepted.stderr
