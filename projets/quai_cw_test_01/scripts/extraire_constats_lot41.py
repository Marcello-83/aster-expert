"""Lot 41, étape 4.1 : extrait les 45 constats `code_aster` de la fiche du quai vers
la base partagée `connaissances/constats_code_aster/`, un fichier par constat.

Entrées : la fiche complète telle que la produit
`scripts/build_combiwall_reference.py` avant l'externalisation (appel de `build()`
sans `externalize`), les résumés `lot41_resumes_constats.yaml` (un par constat,
dans l'ordre de la fiche, contrôlés par le début du sujet), le catalogue extrait de
la version cible (commandes et mots-clés cités par chaque constat).

Identifiants : `CA-001` à `CA-045`, dans l'ordre de la fiche. Le script est
idempotent : relancé, il réécrit les mêmes fichiers octet pour octet.

Usage : python projets/quai_cw_test_01/scripts/extraire_constats_lot41.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml

from aster_expert.agent.hypotheses import CodeAsterHypothesisEntry, HypothesesSheet
from aster_expert.catalogue.query import (
    catalogue_identifiers,
    resolve_active_digest,
)
from aster_expert.constats.base import base_dir, build_constat, write_constat
from aster_expert.constats.models import Constat, FindingOrigin

PROJECT = ROOT / "projets" / "quai_cw_test_01"
FICHE = PROJECT / "fiche" / "hypotheses_combiwall_reference_arbitree.json"
SUMMARIES = Path(__file__).resolve().parent / "lot41_resumes_constats.yaml"


def full_sheet() -> HypothesesSheet:
    """The fiche with its `code_aster` entries written out (never read from the
    versioned file, which cites the base once externalized)."""
    import build_combiwall_reference  # noqa: PLC0415

    return build_combiwall_reference.build(externalize=False)


def constats(sheet: HypothesesSheet) -> list[Constat]:
    summaries = yaml.safe_load(SUMMARIES.read_text(encoding="utf-8"))
    entries = [e for e in sheet.entries if isinstance(e, CodeAsterHypothesisEntry)]
    if len(entries) != len(summaries):
        message = f"{len(entries)} constats dans la fiche, {len(summaries)} résumés"
        raise SystemExit(message)
    digest = resolve_active_digest(ROOT / "config" / "versions.yaml")
    commands, keywords = catalogue_identifiers(
        ROOT / "data" / "processed" / "catalogue", digest
    )
    out = []
    for number, (entry, item) in enumerate(zip(entries, summaries, strict=True), 1):
        if not entry.topic.startswith(item["topic"]):
            message = (
                f"résumé {number} : sujet « {item['topic']} » attendu, "
                f"« {entry.topic[:60]} » trouvé"
            )
            raise SystemExit(message)
        out.append(
            build_constat(
                entry,
                constat_id=f"CA-{number:03d}",
                summary=item["summary"],
                origin=FindingOrigin(
                    project=sheet.project_name,
                    fiche=FICHE.relative_to(ROOT).as_posix(),
                    point_label=entry.point_label,
                ),
                commands=commands,
                keywords=keywords,
            )
        )
    return out


def main() -> int:
    directory = base_dir(ROOT)
    found = constats(full_sheet())
    for constat in found:
        write_constat(constat, directory)
    print(f"{len(found)} constats écrits dans {directory.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
