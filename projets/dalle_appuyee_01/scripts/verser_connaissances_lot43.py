"""Lot 43 : retour d'expérience de la dalle versé dans `connaissances/`.

1. Cas de la suite de convergence versionnés (`references/cas/`), avec un extrait
   de listing qui porte chaque valeur citée par une source d'exécution.
2. Constats : les six constats documentaires de la fiche (CA-046 à CA-051,
   externalisés : la fiche les référence) et un constat d'exécution (CA-052, ELS
   2D de CALC_FERRAILLAGE et SIGC_*_ELS).
3. Référence de validation REF-014 (niveau E : Navier, convergence ×2).
4. Précédents PRE-022 à PRE-031 (PRE-021 laissé libre, cité par MM) : les décisions de MM sur la dalle (jamais
   appliquées : proposées dans un projet futur).
5. Patrons PAT-010 (combinaisons à multiplicateurs constants) et PAT-011 (dalle
   DKT appuyée) ; contrôle CTL-012 (convergence contre une solution analytique).
6. Réutilisations des entrées du quai qui ont servi (PAT-008, PAT-009, CTL-005,
   CTL-006, CTL-008, CTL-010, PRE-016, PRE-018).

Aucune promotion : `aster-expert connaissances promouvoir` reste une commande
explicite. Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/verser_connaissances_lot43.py`
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arbitrer_fiche_lot43 import arbitrate
from build_fiche_lot43 import build_sheet

from aster_expert.agent.drafting import record_execution_finding
from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    DocumentarySource,
    ExecutionSource,
    PracticeHypothesisEntry,
)
from aster_expert.catalogue.query import catalogue_identifiers, resolve_active_digest
from aster_expert.connaissances.base import load_knowledge, write_entry
from aster_expert.connaissances.modeles import (
    CaughtError,
    CodeEvidence,
    Control,
    DecisionEvidence,
    DocumentEvidence,
    Evidence,
    ExecutionEvidence,
    Pattern,
    ReferenceCase,
    ReferenceQuantity,
    Reuse,
    TestEvidence,
    ValidationReference,
)
from aster_expert.connaissances.precedents import precedent_from_entry
from aster_expert.constats.base import base_dir, build_constat, write_constat
from aster_expert.constats.models import FindingOrigin

PROJECT_NAME = "dalle_appuyee_01"
PROJECT = ROOT / "projets" / PROJECT_NAME
FICHE = "projets/dalle_appuyee_01/fiche/hypotheses_dalle_arbitree.json"
CASES = PROJECT / "references" / "cas"
RESULTS = json.loads(
    (PROJECT / "references" / "niveau_e_lot43.json").read_text(encoding="utf-8")
)
NAVIER = json.loads(
    (PROJECT / "references" / "navier_lot43.json").read_text(encoding="utf-8")
)
TODAY = dt.date(2026, 10, 2)
LABELS = ("h0p500", "h0p250", "h0p125")
REPO_COMMIT = "4093f126b4829bec8fc07a97c67beba010c80fce"
IMAGE_DIGEST = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
DOC_COMMIT = "9c8c179f57ef7ca1d2891cac275ee4823a57967c"
LISTING_TABLES = (
    "DEPL_CENTRE_G",
    "DEPL_CENTRE_Q",
    "REACN_APPUI_Q",
    "##EFN_CENTRE_G",
    "##EFN_CENTRE_Q",
    "##EFN_C_RC02",
    "##FER02",
    "##SFER02",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# --- 1. cas versionnés -----------------------------------------------------------


def _listing_extract(mess: str, keep_cells: set[str]) -> str:
    """The tables named in `LISTING_TABLES`, the rows of the ferraillage tables
    restricted to `keep_cells` (cells around the centre), and the job diagnosis."""
    lines = mess.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        title = next(
            (
                t
                for t in LISTING_TABLES
                if t.startswith("##") and line.startswith(f"{t}ASTER")
            ),
            None,
        )
        intitule = next(
            (
                t
                for t in LISTING_TABLES
                if not t.startswith("##")
                and line.startswith("##")
                and t in " ".join(lines[i + 2 : i + 3])
            ),
            None,
        )
        if title or intitule:
            out += [line, lines[i + 1]]
            j = i + 2
            while j < len(lines) and lines[j].strip() and not lines[j].startswith("#"):
                cells = lines[j].split()
                if (
                    not title
                    or not title.endswith(("FER02", "SFER02"))
                    or cells[4] in keep_cells
                ):
                    out.append(lines[j])
                j += 1
            out.append("")
            i = j
            continue
        i += 1
    out += [ln for ln in lines if "DIAGNOSTIC JOB" in ln]
    return "\n".join(out) + "\n"


def version_cases() -> dict[str, dict[str, str]]:
    CASES.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict[str, str]] = {}
    for label, serie in zip(LABELS, RESULTS["series"], strict=True):
        src = PROJECT / "resultats" / "convergence" / label
        stem = f"dalle_{label}"
        for ext in ("comm", "mmed", "export"):
            target = CASES / f"{stem}.{ext}"
            if not target.is_file():
                shutil.copyfile(src / f"{stem}.{ext}", target)
        comm = CASES / f"{stem}.comm"
        if sha(comm) != serie["execution"]["comm_sha256"]:
            message = f"{comm} ne correspond plus à l'exécution enregistrée"
            raise SystemExit(message)
        mess = (
            ROOT / serie["execution"]["repertoire"] / "proc.0" / "fort.6"
        ).read_text(encoding="utf-8", errors="replace")
        keep = set(serie["ferraillage"]["ELU"]["mailles_voisines"])
        listing = CASES / f"{stem}_listing_extrait.txt"
        if not listing.is_file():
            listing.write_text(_listing_extract(mess, keep), encoding="utf-8")
        out[label] = {
            "comm": rel(comm),
            "sha": sha(comm),
            "listing": rel(listing),
            "run": Path(serie["execution"]["repertoire"]).name,
        }
    return out


# --- 2. constats -------------------------------------------------------------------

SUMMARIES = (
    "Pour une dalle plane, le catalogue 17.4 propose DKT et DKTG (Love-Kirchhoff), DST, Q4G et Q4GG (cisaillement transverse) et COQUE_3D, et U2.02.01 réserve DKT/DKQ aux plaques minces (h/L < 1/20).",
    "AFFE_CARA_ELEM/COQUE porte l'épaisseur EPAIS et le repère local ANGL_REP ou VECTEUR, avec A_CIS et COEF_RIGI_DRZ par défaut et GROUP_MA obligatoire.",
    "Sur une plaque, le poids propre s'applique par PESANTEUR avec RHO et une charge surfacique par FORCE_COQUE, en FZ global ou en PRES positive à l'opposé de la normale de la maille.",
    "La statique linéaire s'écrit MECA_STATIQUE (MODELE, CHAM_MATER, CARA_ELEM, EXCIT) avec un matériau DEFI_MATERIAU/ELAS (E, NU, RHO).",
    "Dans le cas test SSLS127, l'appui simple d'une dalle en plaque est DZ = 0 sur les bords, rotations libres, et les plans de symétrie bloquent DY et DRX ou DX et DRY.",
    "En 2D, CALC_FERRAILLAGE (EC2) offre les méthodes CAPRA-MAURY et SANDWICH, n'admet qu'une distance C_INF et C_SUP par face pour les deux directions, et ALPHA_CC y vaut 0,85 par défaut.",
)


def documentary_constats() -> list[tuple[str, CodeAsterHypothesisEntry, str]]:
    sheet = arbitrate(build_sheet())
    entries = [e for e in sheet.entries if isinstance(e, CodeAsterHypothesisEntry)]
    if len(entries) != len(SUMMARIES):
        message = f"{len(entries)} constats documentaires, {len(SUMMARIES)} résumés"
        raise SystemExit(message)
    return [
        (f"CA-{46 + i:03d}", e, s)
        for i, (e, s) in enumerate(zip(entries, SUMMARIES, strict=True))
    ]


R7_04_05_PIVOT = DocumentarySource(
    document_id="R7.04.05",
    aster_version="17.4.0",
    section_path=("Calcul_du_ferraillage_des_poutres_et_poteaux",),
    source_path="source/manuals/man_r/r7/r7.04.05/Calcul_du_ferraillage_des_poutres_et_poteaux.rst",
    source_commit=DOC_COMMIT,
    profile="theorie",
    excerpt="c’est le pivot relatif à l’acier tendu qui est retenu",
)


def els_constat_entry(cases: dict[str, dict[str, str]]) -> CodeAsterHypothesisEntry:
    serie = RESULTS["series"][-1]
    mess = (ROOT / serie["execution"]["repertoire"] / "proc.0" / "fort.6").read_text(
        encoding="utf-8", errors="replace"
    )
    from aster_expert.ferraillage.plaque import titled_table  # noqa: PLC0415

    cell = serie["ferraillage"]["ELU"]["mailles_voisines"][0]
    a = float(
        next(r for r in titled_table(mess, "FER02") if r["MAILLE"] == cell)["DNSYI"]
    )
    b = float(
        next(r for r in titled_table(mess, "SFER02") if r["MAILLE"] == cell)["DNSYI"]
    )
    node = titled_table(mess, "EFN_C_RC02")[0]
    from aster_expert.rebar.model import Concrete, Rectangle, Steel  # noqa: PLC0415
    from aster_expert.rebar.serviceability import design_els  # noqa: PLC0415

    module = design_els(
        Rectangle(width=1.0, depth=0.30, cover_pos=0.048, cover_neg=0.048),
        Concrete(fck=30.0, gamma_c=1.0),
        Steel(fyk=500.0, es=210000.0, gamma_s=1.0),
        0.0,
        float(node["MYY"]) / 1e6,
        sigma_c_lim=18.0,
        sigma_s_lim=400.0,
        alpha_e=15.0,
    ).as_neg
    case = cases["h0p125"]

    def source(value: float, quantity: str) -> ExecutionSource:
        return ExecutionSource(
            aster_version="17.4.0",
            image_digest=IMAGE_DIGEST,
            repo_commit=REPO_COMMIT,
            working_tree_modified=True,
            case_path=case["comm"],
            case_sha256=case["sha"],
            mess_path=case["listing"],
            quantity=quantity,
            value_obtained=value,
            reference="pivot acier de R7.04.05 refait par aster_expert.rebar.serviceability.design_els au nœud CENTRE (MYY de EFN_C_RC02, σs,lim = 400 MPa, αe = 15), indépendant de σc,lim (18 ou 1000 MPa)",
            reference_value=module,
            relative_deviation=(value - module) / module,
            validation_level="D",
        )

    return record_execution_finding(
        topic="CALC_FERRAILLAGE en 2D à l'ELS caractéristique : densités dépendantes de SIGC_*_ELS au pivot acier, écart au calcul de R7.04.05",
        option_retained=(
            "Dalle DKT de 0,30 m (C_INF = C_SUP = 0,048 m, SIGS_ELS = 400 MPa, ALPHA_E = 15), "
            f"combinaison ELS caractéristique : DNSYI de la maille {cell} voisine du centre vaut "
            f"{a:.12e} m²/m avec SIGC_INF_ELS = SIGC_SUP_ELS = 18 MPa et {b:.12e} m²/m avec "
            "1000 MPa (limite inatteignable) ; 4124 des 6144 densités de la dalle changent, "
            "y compris dans des mailles très peu sollicitées. Le pivot acier de R7.04.05 "
            "(cas 1D), où σc,lim se simplifie, refait par le module indépendant au nœud CENTRE, "
            f"donne {module:.12e} m²/m pour les deux valeurs : écarts de "
            f"{(a - module) / module:+.2%} et {(b - module) / module:+.2%}."
        ),
        justification=(
            "Exécution réelle du cas versionné references/cas/dalle_h0p125.comm (tables FER02 "
            "et SFER02, extrait de listing versionné) ; R7.04.05 § Dimensionnement à l'ELS "
            "caractéristique (pivot relatif à l'acier tendu)."
        ),
        notes=(
            "Lot 43, dalle_appuyee_01. Déduction, non établie : l'écart ne vient pas de la "
            "discrétisation (à l'ELU, la même comparaison maille/nœud ne s'écarte que de "
            "0,24 % sur ce maillage, critère F2 de docs/essais_lot43.md) ; même famille que "
            "les écarts ELS 1D inexpliqués de CA-044. Le mécanisme interne de l'ELS 2D n'est "
            "décrit ni par U4.81.42 ni par R7.04.05 (qui ne détaille que le cas 1D). Sans "
            "effet sur le ferraillage de la dalle : l'ELU et le minimum EN 1992 gouvernent. "
            "Conséquence pratique : SIGC_*_ELS n'est pas une simple limite inactive ; sa valeur "
            "change les densités ELS 2D, il faut la déclarer comme paramètre."
        ),
        sources=(
            source(
                a,
                f"DNSYI maille {cell}, ELS_CARA_Q_DOM, SIGC_*_ELS = 18 MPa (table FER02)",
            ),
            source(
                b,
                f"DNSYI maille {cell}, ELS_CARA_Q_DOM, SIGC_*_ELS = 1000 MPa (table SFER02)",
            ),
            R7_04_05_PIVOT,
        ),
        repo_root=ROOT,
        point_label="14",
    )


def write_constats(cases: dict[str, dict[str, str]]) -> list[str]:
    digest = resolve_active_digest(ROOT / "config" / "versions.yaml")
    commands, keywords = catalogue_identifiers(
        ROOT / "data" / "processed" / "catalogue", digest
    )
    directory = base_dir(ROOT)
    written = []
    items = documentary_constats()
    items.append(
        (
            "CA-052",
            els_constat_entry(cases),
            "Piège : en 2D à l'ELS caractéristique, les densités de CALC_FERRAILLAGE changent avec SIGC_*_ELS même là où la limite du béton n'est pas atteinte, et s'écartent de 3 à 4 % du pivot acier de R7.04.05.",
        )
    )
    for constat_id, entry, summary in items:
        constat = build_constat(
            entry,
            constat_id=constat_id,
            summary=summary,
            origin=FindingOrigin(
                project="DALLE-APPUYEE-01", fiche=FICHE, point_label=entry.point_label
            ),
            commands=commands,
            keywords=keywords,
        )
        write_constat(constat, directory)
        written.append(constat_id)
    return written


# --- 3. référence de validation ----------------------------------------------------


def reference(cases: dict[str, dict[str, str]]) -> ValidationReference:
    refcases = []
    for coarse, fine in (("h0p500", "h0p250"), ("h0p250", "h0p125")):
        s_c = RESULTS["series"][LABELS.index(coarse)]["cas"]
        s_f = RESULTS["series"][LABELS.index(fine)]["cas"]
        quantities = []
        for case in ("G", "Q"):
            nav = NAVIER["cas"][case]
            for q, key, label in (
                ("w", "w_m", "flèche au centre (m)"),
                ("mx", "mx_nm_par_m", "Mx au centre (N·m/m)"),
                ("my", "my_nm_par_m", "My au centre (N·m/m)"),
            ):
                quantities.append(
                    ReferenceQuantity(
                        name=f"{label}, cas {case}, maillage {coarse}",
                        value_obtained=s_c[case][q],
                        reference_value=nav[key],
                        criterion="raffinement",
                        refined_case_path=cases[fine]["comm"],
                        refined_value=s_f[case][q],
                        result="réussi"
                        if abs(s_f[case][q] - nav[key]) < abs(s_c[case][q] - nav[key])
                        else "échec",
                        note="w = -DZ, Mx = -MXX, My = -MYY (EFGE_NOEU au nœud CENTRE) ; Navier, references/navier_lot43.json",
                    )
                )
        refcases.append(
            ReferenceCase(
                case_path=cases[coarse]["comm"],
                case_sha256=cases[coarse]["sha"],
                quantities=tuple(quantities),
            )
        )
    sources: tuple[Evidence, ...] = tuple(
        ExecutionEvidence(
            case_path=cases[label]["comm"],
            case_sha256=cases[label]["sha"],
            outcome="réussite",
            level="E",
            note=f"maillage {label} de la suite de convergence",
        )
        for label in LABELS
    ) + (
        DocumentEvidence(
            path="docs/essais_lot43.md",
            note="critère écrit avant exécution (commit 4093f12), verdicts E0 à E2",
        ),
        TestEvidence(
            path="projets/dalle_appuyee_01/tests/test_navier.py",
            function="test_navier_deflection_matches_levy",
        ),
    )
    finest = RESULTS["series"][-1]["cas"]
    return ValidationReference(
        id="REF-014",
        title="Dalle rectangulaire DKT appuyée sur quatre côtés contre Navier (lot 43)",
        summary="Flèche et moments au centre d'une dalle DKT 6 × 4 m simplement appuyée sous charge uniforme, comparés à la série de Navier sur trois maillages de rapport 2 : erreur divisée par environ 4 à chaque raffinement.",
        origin_project=PROJECT_NAME,
        date=TODAY,
        validation_level="E",
        status="établi",
        sources=sources,
        commands=("AFFE_CARA_ELEM", "AFFE_CHAR_MECA", "AFFE_MODELE", "MECA_STATIQUE"),
        keywords=("DKT", "EFGE_NOEU", "FORCE_COQUE", "PESANTEUR"),
        problem="Dalle 6,00 × 4,00 × 0,30 m, E = 33 000 MPa, ν = 0,2, appui bilatéral DZ = 0 sur les quatre bords, cas G (7 500 Pa) et Q (10 000 Pa), QUAD4 12×8, 24×16, 48×32.",
        reference_solution=(
            "Série de Navier (Kirchhoff), ordre doublé jusqu'à 1e-10 (16 777 216 termes), "
            "contrôlée par la série de Lévy à 1e-14. Critère écrit avant exécution : erreur "
            "décroissante au raffinement ×2 (E1) et ≤ 1 % sur le maillage fin (E2) ; obtenu "
            f"sur 48×32 : w {finest['Q']['erreurs']['w']:.2e}, Mx {finest['Q']['erreurs']['mx']:.2e}, "
            f"My {finest['Q']['erreurs']['my']:.2e}."
        ),
        cases=tuple(refcases),
        result="réussi",
        replay_mode="listing",  # lot 48 bis
    )


# --- 4. précédents ---------------------------------------------------------------


def precedents() -> list[str]:
    sheet = arbitrate(build_sheet())
    practice = [e for e in sheet.entries if isinstance(e, PracticeHypothesisEntry)]
    written = []
    # PRE-021 reste libre : l'arbitrage de MM cite « PRE-021 (D21) », décision du quai
    # jamais versée (journal du lot 43, n° 19) ; la réutiliser créerait une confusion.
    for number, entry in enumerate(practice, start=22):
        pid = f"PRE-{number:03d}"
        prec = precedent_from_entry(
            entry,
            precedent_id=pid,
            title=f"Point {entry.point_label} : {entry.topic}"[:200],
            summary=f"Décision de MM au point {entry.point_label} de la fiche de la dalle (2026-10-02) : {entry.topic}."[
                :499
            ].rstrip(".")
            + ".",
            origin_project=PROJECT_NAME,
            fiche=FICHE,
            recorded_on=TODAY,
        )
        write_entry(ROOT, prec)
        written.append(pid)
    return written


# --- 5. patrons et contrôle --------------------------------------------------------


def patterns_and_control(cases: dict[str, dict[str, str]]) -> list[str]:
    h125 = cases["h0p125"]
    run = ExecutionEvidence(
        case_path=h125["comm"],
        case_sha256=h125["sha"],
        outcome="réussite",
        level="E",
        note="cas de référence de la dalle (48×32)",
    )
    pat10 = Pattern(
        id="PAT-010",
        title="Combinaisons d'actions par MECA_STATIQUE à multiplicateurs constants",
        summary="En élasticité linéaire, chaque combinaison s'obtient par un MECA_STATIQUE dont chaque charge élémentaire porte une FONC_MULT = DEFI_CONSTANTE(VALE=coefficient), ce qui donne directement les champs combinés sur lesquels CALC_FERRAILLAGE travaille.",
        origin_project=PROJECT_NAME,
        date=TODAY,
        validation_level="D",
        status="établi",
        sources=(
            run,
            TestEvidence(
                path="projets/dalle_appuyee_01/tests/test_projet_dalle.py",
                function="test_the_generated_comm_carries_every_decision",
            ),
        ),
        commands=("CALC_FERRAILLAGE", "DEFI_CONSTANTE", "MECA_STATIQUE"),
        keywords=("EXCIT", "FONC_MULT"),
        problem="Ferrailler une plaque sur des combinaisons EN 1990 alors que les combinaisons du tronc commun (lot 41) ne combinent que des tables d'efforts de poutre.",
        solution="Énumérer les combinaisons (aster_expert.combinaisons.enumeration) et écrire un MECA_STATIQUE par combinaison ; le résultat porte EFGE_ELNO et se ferraille en 2D. Vérifié au centre de la dalle : ELU = 1,35 G + 1,5 Q à 4e-13 près.",
        fragment="F_RC01_G = DEFI_CONSTANTE(VALE=1.35)\nF_RC01_Q = DEFI_CONSTANTE(VALE=1.5)\nRC01 = MECA_STATIQUE(\n    MODELE=MODELE, CHAM_MATER=CHMAT, CARA_ELEM=CARA,\n    EXCIT=(_F(CHARGE=CL), _F(CHARGE=CH_G, FONC_MULT=F_RC01_G), _F(CHARGE=CH_Q, FONC_MULT=F_RC01_Q)),\n)",
        fragment_language="comm",
        conditions="Élasticité linéaire, Code_Aster 17.4.0 ; les conditions aux limites (CL) sans multiplicateur.",
        controls=(),
        constats=(),
        implementation=(
            CodeEvidence(
                path="projets/dalle_appuyee_01/generation.py",
                symbol="combination_block",
            ),
        ),
    )
    pat11 = Pattern(
        id="PAT-011",
        title="Dalle en plaque DKT appuyée : appui bilatéral, blocage plan isostatique, normales orientées",
        summary="Une dalle DKT simplement appuyée se modélise entière, DZ = 0 sur les nœuds des bords, DX = DY = 0 en un coin et DY = 0 au coin voisin selon X, normales orientées +Z, et se lit en EFGE_NOEU au nœud central.",
        origin_project=PROJECT_NAME,
        date=TODAY,
        validation_level="E",
        status="établi",
        sources=(
            run,
            DocumentEvidence(
                path="docs/essais_lot43.md", note="niveau E (REF-014), contrôles D"
            ),
        ),
        commands=("AFFE_CARA_ELEM", "AFFE_CHAR_MECA", "AFFE_MODELE", "MODI_MAILLAGE"),
        keywords=("ANGL_REP", "DDL_IMPO", "DKT", "EFGE_NOEU", "ORIE_NORM_COQUE"),
        problem="Représenter l'appui simple de Navier (coins retenus) sans redondance de conditions (DIAG-001) ni mouvement de corps rigide dans le plan.",
        solution="DDL_IMPO DZ sur le groupe des bords, DX et DY en P_A, DY en P_B ; ORIE_NORM_COQUE VECT_NORM = (0, 0, 1) pour que la face « supérieure » de CALC_FERRAILLAGE soit le dessus (CA-045) ; ANGL_REP = (0, 0) pour x_l = X ; symétrie contrôlée, pas imposée.",
        fragment='CL = AFFE_CHAR_MECA(\n    MODELE=MODELE,\n    DDL_IMPO=(\n        _F(GROUP_NO="APPUIS", DZ=0.0),\n        _F(GROUP_NO="P_A", DX=0.0, DY=0.0),\n        _F(GROUP_NO="P_B", DY=0.0),\n    ),\n)',
        fragment_language="comm",
        conditions="Plaque plane dans le plan XY, DKT, petits déplacements ; appui bilatéral (les coins sont retenus : réaction de coin vers le bas).",
        controls=("CTL-005", "CTL-006", "CTL-012"),
        constats=("CA-028", "CA-045"),
        implementation=(
            CodeEvidence(
                path="projets/dalle_appuyee_01/generation.py", symbol="build_comm"
            ),
        ),
    )
    ctl12 = Control(
        id="CTL-012",
        title="Convergence au raffinement ×2 contre une solution analytique",
        summary="Sur une suite de maillages de rapport 2, l'erreur de chaque grandeur sensible à la discrétisation doit décroître strictement, et rester sous le seuil écrit avant l'exécution sur le maillage le plus fin.",
        origin_project=PROJECT_NAME,
        date=TODAY,
        validation_level="E",
        status="établi",
        sources=(
            run,
            DocumentEvidence(path="docs/essais_lot43.md", note="critères E1 et E2"),
        ),
        detects="Une erreur de modèle (conditions aux limites, signe, unités) qui ne disparaît pas au raffinement, ou un maillage trop grossier.",
        parameters="Tailles de la suite (données du projet), seuil sur le maillage fin (1 % au lot 43), référence calculée avant exécution.",
        implementation=CodeEvidence(
            path="projets/dalle_appuyee_01/scripts/niveau_e_lot43.py", symbol="evaluate"
        ),
        scope="projet",
        caught_error=CaughtError(
            mode="aucune consignée",
            description="Aucune erreur attrapée au lot 43 : les six grandeurs convergent.",
        ),
    )
    for entry in (pat10, pat11, ctl12):
        write_entry(ROOT, entry)
    return ["PAT-010", "PAT-011", "CTL-012"]


# --- 6. réutilisations --------------------------------------------------------------


def reuses(cases: dict[str, dict[str, str]]) -> list[str]:
    base = load_knowledge(ROOT)
    h125 = cases["h0p125"]
    run = ExecutionEvidence(
        case_path=h125["comm"],
        case_sha256=h125["sha"],
        outcome="réussite",
        level="D",
        note="contrôles D de la dalle (48×32)",
    )
    sheet = arbitrate(build_sheet())
    by_point = {
        e.point_label: e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
    }

    def decision(point: str) -> DecisionEvidence:
        e = by_point[point]
        assert e.decided_by is not None and e.decided_at is not None
        return DecisionEvidence(
            fiche=FICHE,
            point_label=point,
            decided_by=e.decided_by,
            decided_at=e.decided_at,
        )

    plan: dict[str, tuple[Evidence, str]] = {
        "PAT-008": (
            CodeEvidence(
                path="projets/dalle_appuyee_01/maillage/dalle_mesh.py",
                symbol="geometry_group",
            ),
            "Script Salomé de la dalle (partition unique, groupes sur la géométrie, segments imposés) : trois maillages vérifiés du premier coup (48/48 invariants).",
        ),
        "PAT-009": (
            CodeEvidence(
                path="projets/dalle_appuyee_01/generation.py", symbol="case_tables"
            ),
            "Efforts de la dalle lus par CREA_TABLE (EFGE_NOEU, EFGE_ELNO, FERR_ELEM), déplacements et réactions par POST_RELEVE_T : aucun arrêt.",
        ),
        "CTL-005": (
            run,
            "Équilibre G et Q de la dalle à 8,3e-12 (contrôle du tronc commun, composantes bloquées seules).",
        ),
        "CTL-006": (
            run,
            "Symétrie selon deux plans (X = 3, Y = 2) de la dalle entière : 808 paires par plan, 5,2e-13.",
        ),
        "CTL-008": (
            DocumentEvidence(
                path="projets/dalle_appuyee_01/maillage/invariants_h0p125.yaml",
                note="invariants analytiques",
            ),
            "mesh check sur les trois maillages de la dalle : 48/48 invariants chacun.",
        ),
        "CTL-010": (
            CodeEvidence(
                path="projets/dalle_appuyee_01/generation.py", symbol="_title"
            ),
            "Intitulés de la dalle contrôlés à 16 caractères et uniques par le générateur.",
        ),
        "PRE-016": (
            decision("13"),
            "Retenu par MM pour la dalle pour γG = 1,35 et γQ = 1,5 seulement (P5) ; le reste (actions du quai) ne s'applique pas.",
        ),
        "PRE-018": (
            decision("14"),
            "Retenu par MM pour la dalle (P6) : distance parement–axe = enrobage + diamètres, 36 et 48 mm.",
        ),
    }
    written = []
    for entry_id, (evidence, note) in plan.items():
        entry = base.entries[entry_id]
        if any(r.project == PROJECT_NAME for r in entry.reuses):
            continue
        updated = entry.model_copy(
            update={
                "reuses": (
                    *entry.reuses,
                    Reuse(
                        project=PROJECT_NAME, date=TODAY, evidence=evidence, note=note
                    ),
                )
            }
        )
        type(entry).model_validate(updated.model_dump())
        write_entry(ROOT, updated)
        written.append(entry_id)
    return written


def main() -> int:
    cases = version_cases()
    print("cas versionnés :", ", ".join(c["comm"] for c in cases.values()))
    print("constats :", write_constats(cases))
    write_entry(ROOT, reference(cases))
    print("référence : REF-014")
    print("précédents :", precedents())
    print("patrons et contrôle :", patterns_and_control(cases))
    print("réutilisations :", reuses(cases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
