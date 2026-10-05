"""Resolution of input paths against an allowed-roots policy (lot 46).

One function, `resolve_input_path`, is the single door every MCP tool and every
CLI command goes through when it is handed a path to read. It resolves symbolic
links and `..` first, then checks that the real location lies under one of the
roots of the policy, then the extension, then existence -- in that order, so a
refusal never reveals whether a file outside the roots exists.

Two policies exist (`config/chemins.yaml`, `config/validation.yaml`):

- read: repository areas, the test-case corpus and external roots declared by
  the user (read-only, no copy);
- execution: `execution.allowed_roots` (level C), unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

READ_CONFIG = Path("config") / "chemins.yaml"
READ_LOCAL_CONFIG = Path("config") / "chemins.local.yaml"


class PathRefusedError(Exception):
    """An input path is outside the policy. The message is meant for the user."""


@dataclass(frozen=True)
class PathPolicy:
    """Roots a path may lie under, and how to declare one more."""

    name: str
    roots: tuple[Path, ...]
    declare_hint: str


def _as_root(raw: str, project_root: Path) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def _read_roots(path: Path, key: str) -> list[str]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = data.get("lecture") or {}
    values = section.get(key) or []
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        message = f"{path} : lecture.{key} doit être une liste de chemins"
        raise PathRefusedError(message)
    return list(values)


def load_read_policy(project_root: Path) -> PathPolicy:
    """Read policy: `config/chemins.yaml` plus the optional local file."""
    config = project_root / READ_CONFIG
    if not config.is_file():
        message = f"politique de lecture introuvable : {config}"
        raise PathRefusedError(message)
    local = project_root / READ_LOCAL_CONFIG
    raw = [
        *_read_roots(config, "racines_depot"),
        *_read_roots(config, "racines_externes"),
        *_read_roots(local, "racines_depot"),
        *_read_roots(local, "racines_externes"),
    ]
    roots = tuple(dict.fromkeys(_as_root(r, project_root) for r in raw))
    hint = (
        "Pour l'autoriser en lecture seule, déclarer ce répertoire sous "
        f"`lecture.racines_externes` de {READ_LOCAL_CONFIG.as_posix()} "
        f"(non versionné, propre à la machine) ou de {READ_CONFIG.as_posix()} "
        "(versionné), par exemple :\n"
        "  lecture:\n    racines_externes:\n      - /chemin/du/répertoire"
    )
    return PathPolicy(name="lecture", roots=roots, declare_hint=hint)


def execution_policy(allowed_roots: Iterable[str], project_root: Path) -> PathPolicy:
    """Execution policy (level C): `execution.allowed_roots` of validation.yaml."""
    roots = tuple(_as_root(r, project_root) for r in allowed_roots)
    hint = (
        "Pour l'autoriser en exécution, ajouter ce répertoire à "
        "`execution.allowed_roots` de config/validation.yaml (décision de MM : "
        "l'exécution est plus stricte que la lecture)."
    )
    return PathPolicy(name="exécution", roots=roots, declare_hint=hint)


def resolve_input_path(
    path: str | Path,
    *,
    policy: PathPolicy,
    base: Path,
    suffixes: tuple[str, ...] | None = None,
    kind: str | None = "file",
) -> Path:
    """Return the real path, or raise `PathRefusedError` with an actionable message.

    `base` anchors a relative path (project root for MCP tools, working directory
    for the CLI). `suffixes` restricts the extension (case-sensitive). `kind` is
    `"file"`, `"dir"`, `"either"` (must exist) or `None` (existence not checked).
    """
    raw = Path(path).expanduser()
    anchored = raw if raw.is_absolute() else base / raw
    resolved = anchored.resolve()

    if not policy.roots:
        message = (
            f"{resolved} : aucune racine n'est déclarée pour la politique de "
            f"{policy.name}, rien n'est autorisé. {policy.declare_hint}"
        )
        raise PathRefusedError(message)

    if not any(resolved.is_relative_to(root) for root in policy.roots):
        shown = "\n".join(f"  - {root}" for root in policy.roots)
        via_link = (
            f" (chemin donné : {anchored}, qui mène par lien symbolique ou « .. » "
            f"à {resolved})"
            if anchored.absolute() != resolved
            else ""
        )
        missing = resolved if resolved.is_dir() else resolved.parent
        message = (
            f"{resolved} est hors des racines autorisées par la politique de "
            f"{policy.name}{via_link}. Racine manquante : {missing}.\n"
            f"Racines actuelles :\n{shown}\n{policy.declare_hint}"
        )
        raise PathRefusedError(message)

    if suffixes is not None and resolved.suffix not in suffixes:
        wanted = " ou ".join(suffixes)
        message = (
            f"{resolved} : extension {resolved.suffix or '(aucune)'!r} refusée, "
            f"{wanted} attendu."
        )
        raise PathRefusedError(message)

    found = {
        "file": resolved.is_file(),
        "dir": resolved.is_dir(),
        "either": resolved.exists(),
        None: True,
    }[kind]
    if not found:
        label = "Répertoire" if kind == "dir" else "Fichier"
        message = f"{label} introuvable : {resolved}"
        raise PathRefusedError(message)
    return resolved


__all__ = [
    "PathPolicy",
    "PathRefusedError",
    "execution_policy",
    "load_read_policy",
    "resolve_input_path",
]
