"""Delivery of the deliverables to an exchange folder, and its check (lot 49 ter).

A CSV file deposited at lot 49 bis was saved again by Excel: its layout no longer
matched the others, and nothing said so. `aster-expert projet <nom> livraison
<dossier>` copies the delivered files -- the workbook, the files of
`flexion_composee/`, the diagrams, and what the project adds under
`paquet/comparaison/` -- and writes `manifeste_livraison.json`: the SHA-256 and the
size of every file, the commit of the repository and the date. `--verifier` reads the
folder again and reports every file modified, missing or added since the delivery
(exit code 1).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aster_expert.livrables.chaine import deliverables_dir
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

MANIFEST = "manifeste_livraison.json"
SOURCES: tuple[tuple[str, str], ...] = (
    ("classeur_livrables.xlsx", "."),
    ("paquet/flexion_composee/*.csv", "flexion_composee"),
    ("paquet/diagrammes/*.png", "diagrammes"),
    ("paquet/comparaison/*", "comparaison"),
)
"""(pattern under `resultats/livrables/`, subfolder of the delivery)."""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _commit(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def deliver(ctx: ProjectContext, target: Path) -> dict[str, Any]:
    """Copy the delivered files to `target` and write the manifest."""
    source = deliverables_dir(ctx)
    files: dict[str, dict[str, Any]] = {}
    for pattern, sub in SOURCES:
        for path in sorted(source.glob(pattern)):
            if not path.is_file():
                continue
            relative = Path(sub) / path.name if sub != "." else Path(path.name)
            out = target / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)
            files[relative.as_posix()] = {
                "sha256": digest(out),
                "octets": out.stat().st_size,
                "source": path.relative_to(ctx.repo_root).as_posix()
                if path.is_relative_to(ctx.repo_root)
                else str(path),
            }
    if not files:
        message = f"livraison : aucun fichier livrable sous {source}"
        raise ProjectError(message)
    manifest = {
        "projet": ctx.declaration.name,
        "livre_le": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": _commit(ctx.repo_root),
        "regle": "empreinte SHA-256 de chaque fichier livré ; `aster-expert projet "
        f"{ctx.declaration.name} livraison <dossier> --verifier` signale tout fichier "
        "modifié, absent ou ajouté depuis la livraison",
        "fichiers": files,
    }
    (target / MANIFEST).write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def verify(target: Path) -> dict[str, Any]:
    """Every file of the manifest against the folder: modified, missing, added."""
    path = target / MANIFEST
    if not path.is_file():
        message = f"livraison : pas de {MANIFEST} dans {target}"
        raise ProjectError(message)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    modified, missing = [], []
    for name, info in manifest["fichiers"].items():
        file = target / name
        if not file.is_file():
            missing.append(name)
        elif digest(file) != info["sha256"]:
            modified.append(name)
    present = {
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
        if p.is_file() and p.name != MANIFEST
    }
    added = sorted(present - set(manifest["fichiers"]))
    return {
        "dossier": str(target),
        "fichiers": len(manifest["fichiers"]),
        "modifies": modified,
        "absents": missing,
        "ajoutes": added,
        "verdict": "INTACT" if not (modified or missing or added) else "MODIFIÉ",
    }


def run(ctx: ProjectContext, target: Path, *, check: bool) -> list[str]:
    if check:
        result = verify(target)
        lines = [
            f"Livraison {target} : {result['verdict']} ({result['fichiers']} fichiers "
            "au manifeste)"
        ]
        for key, label in (
            ("modifies", "modifié après la livraison"),
            ("absents", "absent"),
            ("ajoutes", "ajouté après la livraison"),
        ):
            lines += [f"  {name} : {label}" for name in result[key]]
        if result["verdict"] != "INTACT":
            raise ProjectError("\n".join(lines))
        return lines
    manifest = deliver(ctx, target)
    return [
        f"Livraison {target} : {len(manifest['fichiers'])} fichiers, manifeste "
        f"{MANIFEST} (SHA-256), commit {manifest['commit']}"
    ]


__all__ = ["MANIFEST", "SOURCES", "deliver", "digest", "run", "verify"]
