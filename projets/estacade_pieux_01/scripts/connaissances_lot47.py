"""Lot 47 -- what the jetty adds to `connaissances/` (after the runs).

1. The production case is versioned (`references/cas/estacade_pieux_01.*`: `.comm`,
   mesh, `.export`, companion file), so that the reference below is replayable.
2. REF-015, first entry of kind « calcul externe non validé » (lot 47): the
   comparison C1 to C13 with the published values of the source model. It can serve
   no promotion and is never a level E.
3. Precedents PRE-033 to PRE-038: decisions of MM that another project may meet
   (E2, E4, E12, E13, E15, E16); never applied, only proposed.
4. PAT-012 (moving loads by batches of MACRO_ELAS_MULT, prints aligned with the mesh,
   envelopes computed on the host) and CTL-014 (local maxima of a slab at a point
   support: convergence to check), both « observé ».
5. Reuses: DIAG-003 (FACTOR_57 met again, corrected by MUMPS iterative refinement,
   RESI_RELA unchanged) and DIAG-010 (JEVEUX_10 reproduced, corrected by its own
   correction), each with the run that holds after the correction.

Idempotent. Usage: `.venv/bin/python projets/estacade_pieux_01/scripts/connaissances_lot47.py`
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.connaissances.base import load_knowledge, write_entry
from aster_expert.connaissances.modeles import (
    CaughtError,
    CodeEvidence,
    Control,
    DocumentEvidence,
    ExecutionEvidence,
    Pattern,
    ReferenceCase,
    ReferenceQuantity,
    Reuse,
    ValidationReference,
)
from aster_expert.connaissances.precedents import precedent_from_entry

PROJECT = "estacade_pieux_01"
PDIR = ROOT / "projets" / PROJECT
CAS = PDIR / "references" / "cas"
FICHE = f"projets/{PROJECT}/fiche/hypotheses_estacade_pieux_01.json"
TODAY = dt.date(2026, 10, 5)
PRODUCTION_RUN = "20261005T101455-e0d5c870"
FAILED_JEVEUX_RUN = "20261005T101311-0097f394"
FAILED_FACTOR_RUN = "20261005T100413-8334652d"
CONVERGENCE_RUNS = (
    "20261005T100812-bdc02930",
    "20261005T100829-3782599a",
    "20261005T100910-b21d2121",
)
PRECEDENT_POINTS = ("E2", "E4", "E12", "E13", "E15", "E16")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version_case() -> Path:
    """Copies the production `.comm` (as executed), its mesh and companion file."""
    run = ROOT / "data" / "processed" / "runs" / PRODUCTION_RUN
    comm = next(run.glob("*.comm"))
    target = CAS / "estacade_pieux_01.comm"
    shutil.copyfile(comm, target)
    shutil.copyfile(next(run.glob("*.mmed")), CAS / "estacade_pieux_01.mmed")
    shutil.copyfile(
        next(run.glob("*.connaissances.yaml")),
        CAS / "estacade_pieux_01.connaissances.yaml",
    )
    (CAS / "estacade_pieux_01.export").write_text(
        "P time_limit 7200\nP memory_limit 10240\nP ncpus 1\nP mpi_nbcpu 1\nP mpi_nbnoeud 1\n"
        "F comm estacade_pieux_01.comm D 1\nF mmed estacade_pieux_01.mmed D 20\n",
        encoding="utf-8",
    )
    return target


def reference(case: Path) -> ValidationReference:
    rows = json.loads(
        (PDIR / "references" / "comparaison_lot47.json").read_text("utf-8")
    )["lignes"]
    quantities = []
    for r in rows:
        if r["tolerance"] is None and r["point"] != "C1":
            continue  # lectures d'information, sans verdict
        tolerance = 0.5 if r["point"] == "C1" else r["tolerance"]
        within = abs(r["ecart_relatif"]) <= tolerance
        quantities.append(
            ReferenceQuantity(
                name=f"{r['point']} {r['colonne']}",
                value_obtained=r["code_aster"],
                reference_value=r["source"],
                criterion="contre_calcul",
                tolerance=tolerance,
                result="réussi" if within else "échec",
                note=(
                    "valeur source arrondie au demi-centimètre : compatible si "
                    "0,25 ≤ u < 0,75 cm (équivaut à ±50 %)"
                    if r["point"] == "C1"
                    else f"verdict du rapport : {r['verdict']}"
                ),
            )
        )
    digest = sha(case)
    return ValidationReference(
        id="REF-015",
        title="Estacade sur pieux : contre-calcul d'un modèle d'avant-projet non validé (lot 47)",
        summary=(
            "Comparaison aux valeurs publiées d'un modèle externe non validé (C1 à C13) : "
            "accord sur les moments de travée de la dalle, l'effort normal en tête de pieu "
            "et l'effort tranchant du bouchon ; écarts aux appuis ponctuels (têtes de pieux), "
            "sur les chevêtres et les moments des pieux. Jamais un niveau E."
        ),
        origin_project=PROJECT,
        date=TODAY,
        validation_level="C",
        status="établi",
        sources=(
            ExecutionEvidence(
                run=PRODUCTION_RUN,
                case_path=rel(case),
                case_sha256=digest,
                outcome="réussite",
                level="C",
                note=(
                    "exécution de production (1 753 s, OK) ; contrôles D : équilibre et "
                    "symétrie tenus sur les cas chargés, ÉCHEC formel de TEP et TEM (écart "
                    "relatif indéfini pour une charge nulle)"
                ),
            ),
            DocumentEvidence(
                path="docs/essais_lot47.md",
                section="2.5",
                note="critères écrits avant l'exécution (commit fa97116), tableau § 3",
            ),
        ),
        commands=(
            "MACRO_ELAS_MULT",
            "AFFE_CARA_ELEM",
            "AFFE_CHAR_MECA",
            "CALC_CHAMP",
        ),
        keywords=(
            "DKT",
            "POU_D_T",
            "DIS_T",
            "EFGE_NOEU",
            "EFGE_ELNO",
            "FORCE_COQUE",
        ),
        problem=(
            "Dalle DKT 31,20 × 6,00 × 0,40 m sur 7 chevêtres POU_D_T au plan moyen, 14 "
            "pieux POU_D_T à ressorts horizontaux, DZ = 0 en pointe ; 247 cas, "
            "combinaisons 100 à 115 du modèle source (E1 à E16)."
        ),
        reference_solution=(
            "Valeurs publiées d'un modèle d'avant-projet d'un autre logiciel, non "
            "validé : un écart ne désigne pas d'avance le calcul fautif."
        ),
        cases=(
            ReferenceCase(
                case_path=rel(case), case_sha256=digest, quantities=tuple(quantities)
            ),
        ),
        result="échec" if any(q.result == "échec" for q in quantities) else "réussi",
        reference_kind="calcul_externe_non_valide",
    )


def precedents() -> list[str]:
    sheet = HypothesesSheet.model_validate_json((ROOT / FICHE).read_text("utf-8"))
    by_point = {
        e.point_label: e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
    }
    written = []
    for number, point in enumerate(PRECEDENT_POINTS, start=33):
        entry = by_point[point]
        pid = f"PRE-{number:03d}"
        prec = precedent_from_entry(
            entry,
            precedent_id=pid,
            title=f"Point {point} : {entry.topic}",
            summary=f"Décision de MM au point {point} de la fiche de l'estacade (2026-10-05) : {entry.topic}.",
            origin_project=PROJECT,
            fiche=FICHE,
            recorded_on=TODAY,
        )
        write_entry(ROOT, prec)
        written.append(pid)
    return written


def pattern_and_control(case: Path) -> list[str]:
    run = ExecutionEvidence(
        run=PRODUCTION_RUN,
        case_path=rel(case),
        case_sha256=sha(case),
        outcome="réussite",
        level="C",
        note="242 positions mobiles, Σ DZ des pointes = charge des roues à 2,8e-10",
    )
    pat = Pattern(
        id="PAT-012",
        title="Charges mobiles : positions en lots de MACRO_ELAS_MULT, empreintes alignées, enveloppes hors Code_Aster",
        summary=(
            "Les positions d'une charge mobile s'écrivent par un générateur : une charge "
            "FORCE_COQUE par position sur des empreintes réunions de mailles entières "
            "(bandes CREA_GROUP_MA/BANDE intersectées), résolues en lots de "
            "MACRO_ELAS_MULT (OPTION='SANS', une factorisation par lot, DETRUIRE après "
            "IMPR_RESU), puis enveloppées et combinées sur le poste à partir du MED."
        ),
        origin_project=PROJECT,
        date=TODAY,
        validation_level="C",
        status="observé",
        sources=(
            run,
            DocumentEvidence(path="docs/essais_lot47.md", section="2.2", note=None),
        ),
        commands=(
            "MACRO_ELAS_MULT",
            "DEFI_GROUP",
            "AFFE_CHAR_MECA",
            "IMPR_RESU",
            "DETRUIRE",
        ),
        keywords=(
            "CAS_CHARGE",
            "NOM_CAS",
            "BANDE",
            "CRIT_NOEUD",
            "INTERSEC",
            "FORCE_COQUE",
            "OPTION",
        ),
        problem="Évaluer des enveloppes et des combinaisons sur des centaines de positions d'une charge roulante sans écrire un cas à la main par position ni saturer la mémoire.",
        solution=(
            "Taille de maille qui divise tous les bords d'empreinte aux pas de "
            "déplacement ; groupes d'essieu par INTERSEC d'une bande X et d'une bande Y "
            "(CRIT_NOEUD='TOUS') ; lots de 25 cas par MACRO_ELAS_MULT avec OPTION='SANS', "
            "champs restreints (EFGE_NOEU de la dalle, EFGE_ELNO des poutres) écrits au "
            "MED puis le résultat détruit ; tous les pas lus par medcoupling "
            "(extract_steps), enveloppes et combinaisons calculées sur le poste."
        ),
        fragment=(
            "MB01 = MACRO_ELAS_MULT(MODELE=MODELE, CHAM_MATER=CHMAT, CARA_ELEM=CARA,\n"
            "    CHAR_MECA_GLOBAL=CL,\n"
            "    CAS_CHARGE=(\n"
            '        _F(NOM_CAS="TSA_M29", CHAR_MECA=CH_TSA_M29, OPTION="SANS"),\n'
            '        _F(NOM_CAS="TSA_M28", CHAR_MECA=CH_TSA_M28, OPTION="SANS"),\n'
            "    ),\n"
            '    SOLVEUR=_F(METHODE="MUMPS", POSTTRAITEMENTS="FORCE"))'
        ),
        fragment_language="comm",
        conditions="Élasticité linéaire ; empreintes rectangulaires alignées sur une grille régulière ; CHAR_MECA en référence simple (validateur de niveau B).",
        controls=("CTL-005", "CTL-013"),
        constats=("CA-029", "CA-055"),
        implementation=(
            CodeEvidence(
                path=f"projets/{PROJECT}/generation.py", symbol="solve_block", note=None
            ),
            CodeEvidence(
                path=f"projets/{PROJECT}/charges_mobiles.py",
                symbol="all_cases",
                note=None,
            ),
            CodeEvidence(
                path=f"projets/{PROJECT}/comparaison.py", symbol="Combiner", note=None
            ),
        ),
    )
    write_entry(ROOT, pat)
    ctl = Control(
        id="CTL-014",
        title="Maxima locaux d'une dalle à un appui ponctuel : convergence à contrôler avant toute comparaison",
        summary=(
            "Un maximum de dalle lu à une tête de pieu reliée en un seul nœud (effort "
            "tranchant, moment, effort normal) peut croître sans limite au raffinement : "
            "le contrôler sur une suite ×2 et lire aussi la grandeur hors du voisinage "
            "de l'appui avant de la comparer."
        ),
        origin_project=PROJECT,
        date=TODAY,
        validation_level="C",
        status="observé",
        sources=tuple(
            ExecutionEvidence(
                run=r,
                outcome="réussite",
                level="C",
                note=f"suite de convergence, maillage {h}",
            )
            for r, h in zip(
                CONVERGENCE_RUNS, ("0,10 m", "0,05 m", "0,025 m"), strict=True
            )
        ),
        commands=("CALC_CHAMP",),
        keywords=(
            "EFGE_NOEU",
            "DKT",
            "QX",
            "MXX",
        ),
        detects=(
            "Une singularité d'appui ponctuel prise pour un effort de dimensionnement : "
            "|QX| doublé à chaque division de la maille par 2 aux têtes de pieux "
            "(179 → 368 → 766 kN/m), moment sur appui +11,7 % entre 0,05 et 0,025 m."
        ),
        parameters="Suite de maillages de rapport 2 ; rayon d'exclusion autour des appuis ponctuels (0,60 m au lot 47) pour la lecture complémentaire.",
        implementation=CodeEvidence(
            path=f"projets/{PROJECT}/lecture.py", symbol="read_convergence", note=None
        ),
        scope="projet",
        caught_error=CaughtError(
            mode="a posteriori",
            description="C9, C12 « rive » et la colonne V de C13 lisent des maxima atteints aux têtes de pieux (lot 47, § 3.4).",
            evidence=DocumentEvidence(
                path="docs/essais_lot47.md", section="3.1", note=None
            ),
        ),
    )
    write_entry(ROOT, ctl)
    return ["PAT-012", "CTL-014"]


def reuses(case: Path) -> list[str]:
    base = load_knowledge(ROOT)
    holds = ExecutionEvidence(
        run=PRODUCTION_RUN,
        case_path=rel(case),
        case_sha256=sha(case),
        outcome="réussite",
        level="C",
        note="exécution de production après correction",
    )
    plan = {
        "DIAG-003": (
            "FACTOR_57 au maillage fin de la suite de convergence (1,8 million de ddl, "
            f"erreur 2,08e-6, exécution {FAILED_FACTOR_RUN}) ; aucune redondance ni "
            "mécanisme ; corrigé par POSTTRAITEMENTS='FORCE' (raffinement itératif), "
            "RESI_RELA inchangé ; toutes les exécutions suivantes réussies."
        ),
        "DIAG-010": (
            f"JEVEUX_10 (&&SSCGNO.LITMP2) reproduit (exécution {FAILED_JEVEUX_RUN}) par un "
            "CREA_GROUP_NO à quatre GROUP_MA ; corrigé par la correction du diagnostic "
            "(un groupe par GROUP_MA puis UNION) ; exécution suivante réussie."
        ),
    }
    written = []
    for entry_id, note in plan.items():
        entry = base.entries[entry_id]
        if any(r.project == PROJECT for r in entry.reuses):
            continue
        updated = entry.model_copy(
            update={
                "reuses": (
                    *entry.reuses,
                    Reuse(project=PROJECT, date=TODAY, evidence=holds, note=note),
                )
            }
        )
        type(entry).model_validate(updated.model_dump())
        write_entry(ROOT, updated)
        written.append(entry_id)
    return written


def main() -> None:
    case = version_case()
    write_entry(ROOT, reference(case))
    print(
        "REF-015 ;",
        ", ".join(precedents()),
        ";",
        ", ".join(pattern_and_control(case)),
        ";",
        ", ".join(reuses(case)),
    )


if __name__ == "__main__":
    main()
