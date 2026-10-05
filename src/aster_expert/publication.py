"""What must never enter the repository (lot 41 ter).

The repository is hosted on a private GitHub repository from lot 41 ter. The
rules of `config/publication.yaml` refuse a file larger than the size limit, a
path matching a forbidden pattern (files of MM, standards under licence, local
images, keys) and a text content matching a secret pattern. They are applied by
the Git hook `scripts/git-hooks/pre-commit` to the staged files, and by
`tests/unit/test_publication.py` to the whole versioned tree.

Lot 47: a project built from real data adds confidential terms (site,
client, firm, file references). They are listed by MM in the local, never
versioned file `config/termes_interdits.local.txt` (one term per line, `#`
comments) and searched without case nor accents in the paths, the text contents
and the commit messages. Without that file the term check is skipped and said so.

Usage: `python -m aster_expert.publication --index` (staged files, as the hook
does), `--arbre` (every versioned file) or `--message <file>` (a commit message,
as the `commit-msg` hook does). Exit code 1 on the first run with a violation,
every violation listed.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable
from functools import partial
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

RULES_FILE = Path("config") / "publication.yaml"
TERMS_FILE = Path("config") / "termes_interdits.local.txt"
_TEXT_PROBE = 8192


class PublicationError(Exception):
    """The rules cannot be read, or Git cannot list the files."""


class PatternRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern: str
    reason: str


class PublicationRules(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int
    max_file_bytes: int
    forbidden_paths: tuple[PatternRule, ...]
    forbidden_contents: tuple[PatternRule, ...]
    forbidden_terms: tuple[str, ...] = ()


class Violation(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    reason: str


def load_rules(project_root: Path) -> PublicationRules:
    path = project_root / RULES_FILE
    if not path.is_file():
        message = f"règles de publication introuvables : {path}"
        raise PublicationError(message)
    rules = PublicationRules.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    for rule in (*rules.forbidden_paths, *rules.forbidden_contents):
        try:
            re.compile(rule.pattern)
        except re.error as exc:
            message = f"{path} : motif invalide {rule.pattern!r} ({exc})"
            raise PublicationError(message) from exc
    return rules


def fold(text: str) -> str:
    """Lower-case text without accents, for a comparison ignoring both."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def load_forbidden_terms(project_root: Path) -> tuple[str, ...] | None:
    """Folded confidential terms of the local file, None if the file is absent."""
    path = project_root / TERMS_FILE
    if not path.is_file():
        return None
    terms: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        term = line.strip()
        if term and not term.startswith("#"):
            terms.append(fold(term))
    return tuple(terms)


def with_forbidden_terms(
    rules: PublicationRules, project_root: Path
) -> PublicationRules:
    """The rules completed by the local confidential terms, if the file exists."""
    terms = load_forbidden_terms(project_root)
    if not terms:
        return rules
    return rules.model_copy(update={"forbidden_terms": terms})


def _term_violations(
    path: str, text: str, terms: Iterable[str], where: str
) -> list[Violation]:
    folded = fold(text)
    # The term itself is never printed: the message would leak it.
    return [
        Violation(path=path, reason=f"terme confidentiel n° {rank} dans {where}")
        for rank, term in enumerate(terms, start=1)
        if term in folded
    ]


def check_message(text: str, rules: PublicationRules) -> list[Violation]:
    """Violations of a commit message (confidential terms only)."""
    return _term_violations(
        "message de commit", text, rules.forbidden_terms, "le message"
    )


def check_commit_messages(
    project_root: Path, rules: PublicationRules
) -> list[Violation]:
    """Confidential terms in the messages of every commit reachable from HEAD."""
    if not rules.forbidden_terms:
        return []
    log = _git(project_root, "log", "--format=%H%x00%B%x00").stdout.decode(
        "utf-8", errors="replace"
    )
    parts = log.split("\0")
    found: list[Violation] = []
    for sha, message in zip(parts[0::2], parts[1::2], strict=False):
        found.extend(
            _term_violations(
                f"commit {sha.strip()[:12]}",
                message,
                rules.forbidden_terms,
                "le message",
            )
        )
    return found


def _is_text(data: bytes) -> bool:
    return b"\0" not in data[:_TEXT_PROBE]


def check_file(
    path: str, size: int, read: Callable[[], bytes], rules: PublicationRules
) -> list[Violation]:
    """Violations of one file; `read` is only called for a file under the limit."""
    found: list[Violation] = []
    if size > rules.max_file_bytes:
        limit = rules.max_file_bytes / 1024 / 1024
        found.append(
            Violation(
                path=path,
                reason=f"{size / 1024 / 1024:.1f} Mo, au-delà de {limit:.0f} Mo",
            )
        )
    for rule in rules.forbidden_paths:
        if re.search(rule.pattern, path, flags=re.IGNORECASE):
            found.append(Violation(path=path, reason=rule.reason))
    if size <= rules.max_file_bytes:
        data = read()
        if _is_text(data):
            text = data.decode("utf-8", errors="replace")
            for rule in rules.forbidden_contents:
                if re.search(rule.pattern, text):
                    found.append(Violation(path=path, reason=rule.reason))
            found.extend(
                _term_violations(path, text, rules.forbidden_terms, "le contenu")
            )
    found.extend(_term_violations(path, path, rules.forbidden_terms, "le chemin"))
    return found


def _git(project_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(project_root), *args],  # noqa: S607 - git from PATH
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = f"git {' '.join(args)} : {result.stderr.decode(errors='replace')}"
        raise PublicationError(message.strip())
    return result


def _names(output: bytes) -> list[str]:
    return [name for name in output.decode("utf-8").split("\0") if name]


def check_index(project_root: Path, rules: PublicationRules) -> list[Violation]:
    """Violations among the staged files (added, copied, modified, renamed)."""
    staged = _names(
        _git(
            project_root, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"
        ).stdout
    )
    found: list[Violation] = []
    for name in staged:
        size = int(_git(project_root, "cat-file", "-s", f":{name}").stdout)
        found.extend(
            check_file(name, size, partial(_staged, project_root, name), rules)
        )
    return found


def _staged(project_root: Path, name: str) -> bytes:
    return _git(project_root, "cat-file", "blob", f":{name}").stdout


def check_tree(
    project_root: Path, rules: PublicationRules, names: Iterable[str] | None = None
) -> list[Violation]:
    """Violations among the versioned files of the working tree."""
    if names is None:
        names = _names(_git(project_root, "ls-files", "-z").stdout)
    found: list[Violation] = []
    for name in names:
        path = project_root / name
        if not path.is_file():  # deleted, not yet committed
            continue
        found.extend(check_file(name, path.stat().st_size, path.read_bytes, rules))
    return found


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    is_message = len(args) == 2 and args[0] == "--message"
    if args not in (["--index"], ["--arbre"]) and not is_message:
        print(
            "usage : python -m aster_expert.publication"
            " --index | --arbre | --message <fichier>"
        )
        return 2
    project_root = Path(
        _git(Path.cwd(), "rev-parse", "--show-toplevel").stdout.decode().strip()
    )
    rules = with_forbidden_terms(load_rules(project_root), project_root)
    if is_message:
        found = check_message(Path(args[1]).read_text(encoding="utf-8"), rules)
    elif args == ["--index"]:
        found = check_index(project_root, rules)
    else:
        found = check_tree(project_root, rules)
    if found:
        print(f"Publication refusée ({RULES_FILE}) :", file=sys.stderr)
        for violation in found:
            print(f"  {violation.path} : {violation.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__: list[str] = [
    "PublicationError",
    "PublicationRules",
    "Violation",
    "check_commit_messages",
    "check_file",
    "check_index",
    "check_message",
    "check_tree",
    "fold",
    "load_forbidden_terms",
    "load_rules",
    "main",
    "with_forbidden_terms",
]
