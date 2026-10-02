# ruff: noqa: E501
# Texte des entrées de connaissance : phrases et fragments de .comm gardés sur une
# ligne pour rester lisibles et comparables aux rapports cités.
"""Capitalisation du quai dans la base de connaissances (lot 42, étape 5).

Ce module construit, à partir des fichiers versionnés du projet, les entrées que
le quai verse dans `connaissances/` : diagnostics (classement des 73 exécutions
échouées relevées par l'audit du lot 40, plus ENV-001), patrons, contrôles,
références de validation et précédents. Le texte des entrées est rédigé ici par la
session à partir des rapports d'essais des lots 21 à 41 (chacun cité en source) ;
les empreintes des cas, les décisions de la fiche et les valeurs des références
sont lues dans le dépôt, jamais recopiées à la main. Le script
`scripts/amorcer_connaissances_lot42.py` écrit les fichiers ; un test rejoue la
construction et la compare octet pour octet aux fichiers versionnés.

Statuts : `établi` au mieux (preuve rejouable : cas versionné ou test) ; aucune
entrée n'est `promu`, un seul projet existant.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.connaissances.base import sha256_path
from aster_expert.connaissances.modeles import (
    CaughtError,
    CodeEvidence,
    ConstatEvidence,
    Control,
    Diagnostic,
    DocumentEvidence,
    Evidence,
    ExecutionEvidence,
    KnowledgeEntry,
    Pattern,
    ReferenceCase,
    ReferenceQuantity,
    Signature,
    TestEvidence,
    ValidationReference,
)
from aster_expert.connaissances.precedents import precedent_from_entry
from aster_expert.connaissances.rex import Classification

PROJECT = "quai_cw_test_01"
RECORDED_ON = dt.date(2026, 10, 1)
FICHE = "projets/quai_cw_test_01/fiche/hypotheses_combiwall_reference_arbitree.json"
GEN = "projets/quai_cw_test_01/generation"
TESTS = "projets/quai_cw_test_01/tests"
COMM_REF = "projets/quai_cw_test_01/references/comm/complet.comm"


class _Repo:
    """Fingerprints read from the repository."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def case(
        self,
        path: str,
        outcome: str,
        note: str,
        level: str | None = None,
    ) -> ExecutionEvidence:
        return ExecutionEvidence.model_validate(
            {
                "case_path": path,
                "case_sha256": sha256_path(self.root / path),
                "outcome": outcome,
                "level": level,
                "note": note,
            }
        )


def _run(
    run: str, outcome: str, note: str, level: str | None = None
) -> ExecutionEvidence:
    return ExecutionEvidence.model_validate(
        {"run": run, "outcome": outcome, "level": level, "note": note}
    )


def _doc(
    path: str, section: str | None = None, note: str | None = None
) -> DocumentEvidence:
    return DocumentEvidence(path=path, section=section, note=note)


def _test(path: str, function: str, note: str | None = None) -> TestEvidence:
    return TestEvidence(path=path, function=function, note=note)


def _code(path: str, symbol: str, note: str | None = None) -> CodeEvidence:
    return CodeEvidence(path=path, symbol=symbol, note=note)


def _ca(constat_id: str) -> ConstatEvidence:
    return ConstatEvidence(constat_id=constat_id)


def _common(
    entry_id: str,
    title: str,
    summary: str,
    level: str,
    status: str,
    sources: list[Evidence],
    commands: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "title": title,
        "summary": summary,
        "origin_project": PROJECT,
        "date": RECORDED_ON,
        "validation_level": level,
        "status": status,
        "sources": tuple(sources),
        "commands": commands,
        "keywords": keywords,
    }


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def diagnostics(repo: _Repo) -> list[Diagnostic]:
    out: list[Diagnostic] = []

    def add(
        entry_id: str,
        title: str,
        summary: str,
        level: str,
        status: str,
        sources: list[Evidence],
        *,
        category: str,
        signature: Signature,
        cause: str,
        established: bool,
        correction: str,
        prevention: str | None = None,
        commands: tuple[str, ...] = (),
        keywords: tuple[str, ...] = (),
    ) -> None:
        out.append(
            Diagnostic.model_validate(
                {
                    **_common(
                        entry_id,
                        title,
                        summary,
                        level,
                        status,
                        sources,
                        commands,
                        keywords,
                    ),
                    "category": category,
                    "signature": signature,
                    "cause": cause,
                    "cause_established": established,
                    "correction": correction,
                    "prevention": prevention,
                }
            )
        )

    add(
        "DIAG-001",
        "Pivot nul à la factorisation : relation cinématique et blocage sur le même ddl",
        "Un pivot nul FACTOR_11 apparaît quand un degré de liberté déjà déterminé par une "
        "relation dualisée (LIAISON_SOLIDE) est bloqué une seconde fois par DDL_IMPO, "
        "comme au plan de symétrie du quai.",
        "C",
        "établi",
        [
            _run(
                "20260923T093604-686ef117",
                "échec",
                "lot 28, modèle complet : premier FACTOR_11",
            ),
            _run(
                "20260923T140055-163894f7",
                "échec",
                "lot 30, quai réduit : même pivot (nœuds 575/13)",
            ),
            _run(
                "20260924T073315-ef945d2f",
                "échec",
                "lot 31, candidat LIAISON_SOLIDE : même pivot",
            ),
            _run(
                "20260924T082421-4ed9a9c6",
                "réussite",
                "lot 32, modèle complet après la règle de CL : DIAGNOSTIC JOB OK",
                "C",
            ),
            _doc(
                "docs/essais_lot31.md",
                note="cause documentaire (R3.03.01, R3.03.02, R3.07.03)",
            ),
            _doc(
                "docs/essais_lot32.md",
                note="correction généralisée à DX, preuve par exécution",
            ),
            _ca("CA-032"),
            _test(
                f"{TESTS}/test_generation_comm.py",
                "test_symmetry_block_excludes_the_ring_from_every_determined_dof",
            ),
            _test(
                f"{TESTS}/test_generation_comm.py",
                "test_control_rejects_a_direct_dx_block_on_the_raw_plane",
            ),
        ],
        category="modélisation",
        signature=Signature(kind="<F>", identifiers=("FACTOR_11",)),
        cause=(
            "La matrice est singulière parce qu'un même degré de liberté est contraint "
            "deux fois : LIAISON_SOLIDE (anneau DKT + nœud de poutre, cas 3DA de R3.03.02) "
            "dualise les ddl de l'anneau, dont DRZ qui n'a qu'une raideur fictive "
            "(COEF_RIGI_DRZ, R3.07.03) ; DDL_IMPO de symétrie bloquait en plus DX, DRY, "
            "DRZ des mêmes nœuds d'anneau au plan de coupe (R3.03.01 : structure retenue "
            "par son dernier ddl physique). Ni les ressorts, ni les tirants, ni les "
            "palplanches, ni la raideur (1e2 à 1e10) n'en sont la cause (lots 29 et 30). "
            "FACTOR_11 a d'autres causes possibles (mécanisme libre) : ce diagnostic vaut "
            "pour une relation cinématique combinée à des blocages."
        ),
        established=True,
        correction=(
            "Ne bloquer par DDL_IMPO que les ddl que la relation ne détermine pas : au plan "
            "de symétrie, DX/DRY/DRZ sur le groupe du plan privé des nœuds de l'anneau "
            "(DEFI_GROUP/DIFFE), l'anneau tenant ses ddl de LIAISON_SOLIDE "
            "(symmetry_and_support_block, contrôle check_symmetry_ddl_impo_no_ring_redundancy)."
        ),
        prevention="Contrôle CTL-002 avant écriture du .comm.",
        commands=("AFFE_CHAR_MECA",),
        keywords=("DDL_IMPO", "DKT", "DRZ", "FACTOR_11", "LIAISON_SOLIDE"),
    )
    add(
        "DIAG-002",
        "Nom de groupe tronqué en silence puis doublon",
        "Un nom de groupe de plus de 24 caractères est tronqué sans message par "
        "Code_Aster et n'est signalé qu'au premier doublon résultant (SOUSTRUC_37).",
        "B",
        "établi",
        [
            _run(
                "20260923T092118-f4ab1161",
                "échec",
                "lot 28 : GEN_BNDPART_RESS_AV_ARGI existe déjà",
            ),
            _run("20260923T093142-691355f1", "échec", "lot 28 : même doublon"),
            _doc("docs/essais_lot28.md"),
            _code(f"{GEN}/comm.py", "_gn"),
            _test(
                f"{TESTS}/test_generation_lot36.py",
                "test_v1_group_names_respect_the_group_name_limit",
            ),
        ],
        category="préparation",
        signature=Signature(
            kind="<F>", identifiers=("SOUSTRUC_37",), pattern="existe déjà"
        ),
        cause=(
            "Code_Aster tronque à 24 caractères le nom d'un groupe créé (DEFI_GROUP, "
            "CREA_POI1) ; deux noms qui ne diffèrent qu'au-delà deviennent identiques. Le "
            "catalogue ne le dit pas (NOM est un TXM sans longueur)."
        ),
        established=True,
        correction="Limiter à 24 caractères tout nom de groupe créé, refusé à la génération (_gn).",
        commands=("DEFI_GROUP", "CREA_MAILLAGE"),
        keywords=("CREA_POI1", "SOUSTRUC_37"),
    )
    add(
        "DIAG-003",
        "Solution MUMPS trop imprécise",
        "MUMPS arrête le calcul (FACTOR_57) quand l'erreur de la solution dépasse "
        "RESI_RELA ; sur le reproducteur du lot 28 le relâchement à 1e-4 l'a levé, sans "
        "cause établie.",
        "A",
        "observé",
        [
            _run(
                "20260923T121558-6f3c1e73",
                "échec",
                "lot 28, reproduction isolée : erreur calculée 2,74e-5",
            ),
            _doc("docs/essais_lot28.md", note="relâchement de RESI_RELA à 1e-4"),
            _doc(
                "docs/essais_lot33.md",
                note="RESI_RELA par défaut sans échec sur le quai réduit : paramètre retiré",
            ),
        ],
        category="modélisation",
        signature=Signature(kind="<F>", identifiers=("FACTOR_57",)),
        cause=(
            "Conditionnement de la matrice du reproducteur (tube isolé avec LIAISON_SOLIDE) : "
            "non établi. Sur le quai réduit, le défaut de 1e-6 n'échoue pas (lot 33)."
        ),
        established=False,
        correction=(
            "Chercher d'abord une redondance ou un mécanisme (DIAG-001) ; ne relâcher "
            "SOLVEUR/RESI_RELA qu'en le justifiant et en contrôlant l'équilibre (niveau D)."
        ),
        commands=("MECA_STATIQUE",),
        keywords=("FACTOR_57", "MUMPS", "RESI_RELA", "SOLVEUR"),
    )
    add(
        "DIAG-004",
        "Ressort DIS_T sans masse sous PESANTEUR",
        "Sous PESANTEUR, un élément DIS_T qui ne porte que K_T_D_N arrête le calcul "
        "(DISCRETS_26/30/31) : une masse M_T_D_N, même nulle, doit être affectée.",
        "B",
        "établi",
        [
            _run("20260923T130902-3cb174f7", "échec", "lot 29, reproducteur"),
            _run("20260923T173024-00363e2e", "échec", "lot 30, retrait de la poutre"),
            _doc("docs/essais_lot31.md", note="correction vérifiée par exécution"),
            _test(
                f"{TESTS}/test_generation_generate.py",
                "test_springs_carry_an_explicit_zero_mass",
            ),
        ],
        category="modélisation",
        signature=Signature(
            kind="<F>", identifiers=("DISCRETS_26", "DISCRETS_30", "DISCRETS_31")
        ),
        cause=(
            "PESANTEUR passe par la matrice de masse ; un discret sans caractéristique de "
            "masse produit l'alarme, aggravée en erreur par DEBUT(ERREUR=_F(ALARME="
            '"EXCEPTION")) (CATAMESS_3).'
        ),
        established=True,
        correction='AFFE_CARA_ELEM/DISCRET, CARA="M_T_D_N", VALE=(0.0,) par classe de ressort.',
        commands=("AFFE_CARA_ELEM", "AFFE_CHAR_MECA"),
        keywords=("DISCRET", "DIS_T", "K_T_D_N", "M_T_D_N", "PESANTEUR"),
    )
    add(
        "DIAG-005",
        "IMPR_RESU d'un champ à sous-points sans CARA_ELEM",
        "IMPR_RESU au format MED d'un champ à sous-points d'élément de structure "
        "(SIEF_ELGA de coque) exige CARA_ELEM, sinon MED2_14.",
        "B",
        "établi",
        [
            _run("20260923T130503-d423a6b9", "échec", "lot 29, reproducteur"),
            _run("20260924T073906-857c7055", "échec", "lot 31, quai réduit"),
            _doc("docs/essais_lot31.md"),
            _test(
                f"{TESTS}/test_generation_generate.py",
                "test_impr_resu_carries_cara_elem_for_every_result",
            ),
        ],
        category="modélisation",
        signature=Signature(kind="<F>", identifiers=("MED2_14",)),
        cause="Le nombre de sous-points du champ n'est connu que par les caractéristiques élémentaires.",
        established=True,
        correction="CARA_ELEM=<concept AFFE_CARA_ELEM> sur chaque occurrence RESU d'IMPR_RESU.",
        commands=("IMPR_RESU",),
        keywords=("CARA_ELEM", "MED2_14", "SIEF_ELGA"),
    )
    add(
        "DIAG-006",
        "Collision de nom de champ MED entre deux résultats",
        "Deux concepts résultats dont les huit premiers caractères coïncident écrivent le "
        "même nom de champ MED (MED2_4) : NOM_RESU_MED doit être donné.",
        "B",
        "établi",
        [
            _run(
                "20260924T074135-83e8c50b",
                "échec",
                "lot 31 : RESU_EAUDEPL présent deux fois",
            ),
            _run("20260924T081527-4aa4bf7d", "échec", "lot 32, quai réduit"),
            _doc("docs/essais_lot32.md", note="U7.05.21"),
            _test(
                f"{TESTS}/test_generation_generate.py",
                "test_impr_resu_nom_resu_med_avoids_the_lot31_field_collision",
            ),
        ],
        category="préparation",
        signature=Signature(kind="<F>", identifiers=("MED2_4",)),
        cause="Le nom de champ MED part du nom Jeveux du concept, tronqué à 8 caractères (RESU_EAU_P et RESU_EAU_A).",
        established=True,
        correction='NOM_RESU_MED="<nom du cas>" (8 caractères au plus) par occurrence RESU.',
        commands=("IMPR_RESU",),
        keywords=("MED2_4", "NOM_RESU_MED"),
    )
    add(
        "DIAG-007",
        "Vérification d'orientation sur un groupe de bord non connexe",
        "FORCE_COQUE avec VERI_NORM par défaut refuse un groupe de mailles non connexe "
        "(MESH3_99) ; VERI_NORM=\"NON\" n'est admissible qu'après une vérification "
        "explicite des normales.",
        "B",
        "établi",
        [
            _run(
                "20260923T172128-71b3a102", "échec", "lot 30, retrait des palplanches"
            ),
            _run("20260924T155517-5d41bb8c", "échec", "lot 34, charge par couche"),
            _doc("docs/essais_lot34.md"),
            _test(
                f"{TESTS}/test_generation_generate.py",
                "test_lot35_the_layer_loads_still_disable_veri_norm_explicitly",
            ),
            _test(
                f"{TESTS}/test_meshing_normals.py",
                "test_altered_mesh_with_a_flipped_cell_is_rejected",
            ),
        ],
        category="modélisation",
        signature=Signature(kind="<F>", identifiers=("MESH3_99",)),
        cause="La vérification automatique d'orientation exige un ensemble connexe de mailles de bord.",
        established=True,
        correction=(
            "Orienter par MODI_MAILLAGE/ORIE_NORM_COQUE, vérifier les normales sur le "
            'maillage relu (contrôle CTL-007), puis VERI_NORM="NON" sur la charge.'
        ),
        commands=("AFFE_CHAR_MECA_F", "MODI_MAILLAGE"),
        keywords=("FORCE_COQUE", "MESH3_99", "ORIE_NORM_COQUE", "VERI_NORM"),
    )
    add(
        "DIAG-008",
        "Force imposée sur une composante absente des nœuds",
        "AFFE_CHAR_MECA refuse (CHARGES2_46) une force sur des nœuds qui ne portent pas la "
        "composante, par exemple un groupe sorti du modèle.",
        "A",
        "observé",
        [
            _run(
                "20260923T172818-a733f4f9",
                "échec",
                "lot 30 : BOLLARD hors modèle sans la poutre",
            ),
            _doc("docs/essais_lot30.md"),
        ],
        category="préparation",
        signature=Signature(kind="<F>", identifiers=("CHARGES2_46",)),
        cause="Les nœuds chargés n'appartiennent à aucun élément du modèle qui porte la composante (ici FY).",
        established=True,
        correction="Retirer la charge du cas, ou rendre au modèle les éléments qui portent ces nœuds.",
        commands=("AFFE_CHAR_MECA",),
        keywords=("CHARGES2_46", "FORCE_NODALE"),
    )
    add(
        "DIAG-009",
        "Plusieurs charges réparties sur une poutre liée : post-traitement impossible",
        "Une charge FORCE_POUTRE sur une poutre continue liée par plusieurs LIAISON_SOLIDE "
        "arrête tout CALC_CHAMP ultérieur (CALCULEL2_92).",
        "D",
        "établi",
        [
            _run("20260924T121058-05b0b9dc", "échec", "lot 33, quai réduit"),
            _run("20260924T122731-0b829e46", "échec", "lot 33, diagnostic sans FZ"),
            _ca("CA-035"),
            _test(
                f"{TESTS}/test_generation_generate.py",
                "test_poutre_pressure_charges_use_nodal_forces_not_force_poutre",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="<F>", identifiers=("CALCULEL2_92",)),
        cause="Voir CA-035 : le chargement réparti de poutre n'est pas accepté par le post-traitement dans cette configuration.",
        established=True,
        correction="Charges de poutre en forces nodales tributaires (FORCE_NODALE), résultante et moment exacts.",
        commands=("AFFE_CHAR_MECA", "CALC_CHAMP"),
        keywords=("CALCULEL2_92", "FORCE_NODALE", "FORCE_POUTRE", "LIAISON_SOLIDE"),
    )
    add(
        "DIAG-010",
        "Collision de nom interne à DEFI_GROUP (JEVEUX_10)",
        "Un CREA_GROUP_NO portant plusieurs GROUP_MA dans une seule occurrence a fait "
        "échouer une commande ultérieure (JEVEUX_10, &&SSCGNO.LITMP2) ; un groupe par "
        "nom de maille puis leur UNION l'évite.",
        "A",
        "observé",
        [
            _run("20260924T130146-8aa8d8c0", "échec", "lot 33, quai réduit"),
            _run("20260924T130411-24ad2142", "échec", "lot 33, même erreur"),
            _code(
                f"{GEN}/comm.py",
                "profile_node_groups_block",
                note="une occurrence par groupe de mailles",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="<F>", identifiers=("JEVEUX_10",), pattern="SSCGNO"),
        cause="Collision d'un nom d'objet temporaire interne à Code_Aster : mécanisme non établi.",
        established=False,
        correction="CREA_GROUP_NO : une occurrence par groupe de mailles, puis UNION.",
        commands=("DEFI_GROUP",),
        keywords=("CREA_GROUP_NO", "JEVEUX_10", "UNION"),
    )
    add(
        "DIAG-011",
        "EFGE_NOEU sur des éléments de repères locaux incompatibles",
        "CALC_CHAMP/EFGE_NOEU s'arrête (UTILITAI_4) sur un groupe dont les repères locaux "
        "diffèrent trop d'une maille à l'autre (facettes de tube à 92°) ; les efforts se "
        "lisent alors en EFGE_ELNO par CREA_TABLE.",
        "B",
        "établi",
        [
            _run("20260925T071043-39e3665b", "échec", "lot 35, quai réduit"),
            _doc("docs/essais_lot35.md"),
            _test(
                f"{TESTS}/test_generation_comm.py",
                "test_displacements_by_post_releve_t_and_efforts_by_crea_table",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="<F>", identifiers=("UTILITAI_4",)),
        cause="La moyenne aux nœuds d'efforts exprimés dans des repères locaux différents n'est pas définie.",
        established=True,
        correction="EFGE_ELNO (sans moyenne) lu par CREA_TABLE ; EFGE_NOEU sur les seuls groupes plans (palplanches).",
        commands=("CALC_CHAMP", "CREA_TABLE"),
        keywords=("EFGE_ELNO", "EFGE_NOEU", "UTILITAI_4"),
    )
    add(
        "DIAG-012",
        "POST_RELEVE_T sur un champ d'éléments de structure",
        "POST_RELEVE_T s'arrête (POSTRELE_70 aggravée en erreur) sur un champ d'efforts de "
        "structure ; CREA_TABLE lit les valeurs stockées.",
        "B",
        "établi",
        [
            _run("20260925T071216-4bf41bd0", "échec", "lot 35, essai A"),
            _doc("docs/essais_lot35.md"),
            _test(
                f"{TESTS}/test_generation_comm.py",
                "test_displacements_by_post_releve_t_and_efforts_by_crea_table",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="<F>", identifiers=("POSTRELE_70",)),
        cause="Alarme POSTRELE_70 aggravée en erreur par DEBUT/ERREUR (CATAMESS_3) sur un champ de structure.",
        established=True,
        correction="Extraire les efforts par CREA_TABLE/RESU, POST_RELEVE_T gardé pour les déplacements.",
        commands=("CREA_TABLE", "POST_RELEVE_T"),
        keywords=("CATAMESS_3", "EFGE_NOEU", "POSTRELE_70"),
    )
    add(
        "DIAG-013",
        "Changement de repère local refusé par POST_RELEVE_T",
        'POST_RELEVE_T avec REPERE="LOCAL" sur EFGE_ELNO s\'arrête (POSTRELE_38, '
        "composante non traitée dans un changement de repère).",
        "B",
        "établi",
        [
            _run("20260925T071423-4fe99c43", "échec", "lot 35, quai réduit"),
            _doc("docs/essais_lot35.md"),
            _test(
                f"{TESTS}/test_generation_comm.py",
                "test_displacements_by_post_releve_t_and_efforts_by_crea_table",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="<F>", identifiers=("POSTRELE_38",)),
        cause="Les composantes d'efforts généralisés ne sont pas traitées par le changement de repère de POST_RELEVE_T.",
        established=True,
        correction="Lire les efforts dans leur repère d'élément (CREA_TABLE) et les projeter hors de Code_Aster.",
        commands=("POST_RELEVE_T",),
        keywords=("EFGE_ELNO", "POSTRELE_38", "REPERE"),
    )
    add(
        "DIAG-014",
        "FERR_MIN_FISS refusé pour les poutres",
        "CALC_FERRAILLAGE refuse le ferraillage minimal de fissuration (FERR_MIN_FISS) pour "
        "les éléments de poutre (CALCULEL7_40) : limite de la version 17.4.",
        "C",
        "établi",
        [
            _run("20260928T095433-ba976fa9", "échec", "lot 39, essai fiss"),
            repo.case(
                "data/examples/lot39_essais/fiss/fiss.comm",
                "échec",
                "cas versionné qui reproduit l'arrêt",
            ),
            _ca("CA-041"),
            _test(
                "tests/integration/test_reel_lent.py",
                "test_a_fatal_error_is_reported_with_its_identifier",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="<F>", identifiers=("CALCULEL7_40",)),
        cause="Fonction non disponible pour les éléments POUTRE en 17.4 (message explicite).",
        established=True,
        correction="Calculer la maîtrise de la fissuration hors de Code_Aster (module aster_expert.rebar) ou en 2D.",
        commands=("CALC_FERRAILLAGE",),
        keywords=("CALCULEL7_40", "FERR_MIN_FISS"),
    )
    add(
        "DIAG-015",
        "PESANTEUR sans RHO sur un élément ELAS_COQUE",
        "PESANTEUR exige RHO sur tous les éléments ELAS_COQUE du modèle, même si elle est "
        "restreinte à un autre groupe (MODELISA9_77 puis MODELISA6_4).",
        "D",
        "établi",
        [
            _run(
                "20260921T100522-f5d8b88c",
                "échec",
                "lot 22, essai b1 : échec attendu, c'est le fait établi",
            ),
            _run(
                "20260921T101704-c98db170",
                "échec",
                "lot 22, essai b4 (PESANTEUR restreinte)",
            ),
            repo.case(
                "data/examples/lot22_essais/essai_b/b1.comm",
                "échec",
                "cas versionné de l'échec",
            ),
            _ca("CA-024"),
        ],
        category="modélisation",
        signature=Signature(
            kind="<EXCEPTION>", identifiers=("MODELISA9_77",), pattern="RHO"
        ),
        cause="Le poids est calculé élément par élément sur tout le modèle (voir CA-024).",
        established=True,
        correction="Donner RHO à chaque matériau ELAS_COQUE (RHO = 0 annule le poids sans alarme : le vérifier).",
        commands=("AFFE_CHAR_MECA", "DEFI_MATERIAU"),
        keywords=("ELAS_COQUE", "MODELISA6_4", "MODELISA9_77", "PESANTEUR", "RHO"),
    )
    add(
        "DIAG-016",
        "Table de SIEF_ELGA sous DKT : COOR_ELGA indisponible",
        "CREA_TABLE sur SIEF_ELGA d'un modèle DKT s'arrête (CALCUL_37) car MEBODKT ne "
        "calcule pas COOR_ELGA ; IMPR_RESU au format RESULTAT imprime le champ.",
        "D",
        "établi",
        [
            _run("20260921T112543-42b74df1", "échec", "lot 23, essai d1"),
            repo.case(
                "data/examples/lot23_essais/essai_d1/d1.comm",
                "réussite",
                "cas corrigé (IMPR_RESU FORMAT RESULTAT)",
                "D",
            ),
        ],
        category="préparation",
        signature=Signature(
            kind="<EXCEPTION>", identifiers=("CALCUL_37",), pattern="COOR_ELGA"
        ),
        cause="CREA_TABLE d'un champ aux points de Gauss demande leurs coordonnées (option COOR_ELGA), absente de l'élément MEBODKT.",
        established=True,
        correction='IMPR_RESU(FORMAT="RESULTAT") du champ, ou lire EFGE_ELNO/EFGE_NOEU (CA-025).',
        commands=("CREA_TABLE", "IMPR_RESU"),
        keywords=("CALCUL_37", "COOR_ELGA", "DKT", "SIEF_ELGA"),
    )
    add(
        "DIAG-017",
        "Charge affectée à des mailles hors du modèle",
        "AFFE_CHAR_MECA refuse (MODELISA6_96) une charge (FORCE_ARETE) sur des mailles qui "
        "n'appartiennent pas au modèle.",
        "D",
        "établi",
        [
            _run(
                "20260921T112635-b6570a85",
                "échec",
                "lot 23, essai d5a : segments de bord hors AFFE_MODELE",
            ),
            repo.case(
                "data/examples/lot23_essais/essai_d5/d5a.comm",
                "réussite",
                "cas corrigé (modèle sur TOUT)",
                "D",
            ),
        ],
        category="préparation",
        signature=Signature(kind="<EXCEPTION>", identifiers=("MODELISA6_96",)),
        cause="Les mailles chargées (SEG2 de bord) n'avaient reçu aucune modélisation.",
        established=True,
        correction="Inclure dans AFFE_MODELE les mailles qui portent la charge.",
        commands=("AFFE_CHAR_MECA", "AFFE_MODELE"),
        keywords=("FORCE_ARETE", "MODELISA6_96"),
    )
    add(
        "DIAG-018",
        "Nom de maille en double dans un maillage ASTER",
        "LIRE_MAILLAGE refuse (MODELISA7_10) un maillage au format ASTER où deux mailles "
        "portent le même nom.",
        "D",
        "établi",
        [
            _run(
                "20260921T100453-a31e069c",
                "échec",
                "lot 22, essai a1 : MA1 pris par un QUAD4 et un SEG2",
            ),
            _doc("docs/essais_lot22.md"),
            repo.case(
                "data/examples/lot22_essais/essai_a/a1.comm",
                "réussite",
                "cas corrigé (segments SG1…)",
                "D",
            ),
        ],
        category="préparation",
        signature=Signature(kind="<EXCEPTION>", identifiers=("MODELISA7_10",)),
        cause="Les noms de mailles d'un maillage ASTER sont uniques tous types confondus.",
        established=True,
        correction="Préfixes distincts par type de maille.",
        commands=("LIRE_MAILLAGE",),
        keywords=("MODELISA7_10",),
    )
    add(
        "DIAG-019",
        "Liste de noms trop longue sur une ligne d'un maillage ASTER",
        "Un GROUP_MA écrit sur une seule ligne de 360 noms est mal lu par le format ASTER "
        "(alarmes MODELISA5_8, CALCULEL_58, puis CALCULEL_6).",
        "D",
        "établi",
        [
            _run("20260921T093450-a49d007b", "échec", "lot 21, demi-cylindre"),
            _doc("docs/essai_lot21_force_coque.md"),
            repo.case(
                "data/examples/fcoque_essai/demi_cylindre.comm",
                "réussite",
                "cas corrigé (8 noms par ligne)",
                "D",
            ),
        ],
        category="préparation",
        signature=Signature(kind="<EXCEPTION>", identifiers=("CALCULEL_6",)),
        cause="Le format ASTER lit des enregistrements de largeur fixe : une ligne trop longue est coupée.",
        established=True,
        correction="Répartir les listes de noms sur des lignes de 8 noms.",
        commands=("LIRE_MAILLAGE",),
        keywords=("CALCULEL_58", "CALCULEL_6", "MODELISA5_8"),
    )
    add(
        "DIAG-020",
        "Maille POI1 écrite au même nœud qu'une autre maille",
        "Une maille POI1 écrite directement dans un maillage natif au nœud d'un QUAD4 est "
        "refusée (MODELISA8_14, aggravée) ; CREA_POI1 la crée correctement.",
        "A",
        "observé",
        [
            _run("20260923T130739-57ea01cb", "échec", "lot 29, reproducteur"),
            _doc("docs/essais_lot29.md"),
        ],
        category="préparation",
        signature=Signature(kind="<F>", identifiers=("MODELISA8_14",)),
        cause="Alarme « maille incluse dans une autre » aggravée en erreur par DEBUT/ERREUR.",
        established=True,
        correction="Créer les POI1 par CREA_MAILLAGE/CREA_POI1 depuis un GROUP_NO.",
        commands=("CREA_MAILLAGE",),
        keywords=("CREA_POI1", "MODELISA8_14", "POI1"),
    )
    add(
        "DIAG-021",
        "Maillage sans maille",
        "LIRE_MAILLAGE d'un maillage ASTER sans aucune maille s'arrête sur « Il manque les "
        "mailles » (MODELISA5_3), présenté comme une erreur développeur.",
        "A",
        "observé",
        [
            _run(
                "20260924T095750-e41e8395",
                "échec",
                "lot 33, ressort seul : un nœud, aucune maille",
            ),
            _doc("docs/essais_lot33.md"),
        ],
        category="préparation",
        signature=Signature(kind="<F>", identifiers=("MODELISA5_3",)),
        cause="Le fichier ne déclarait qu'un nœud et un GROUP_NO, aucune maille.",
        established=True,
        correction="Déclarer au moins une maille (ici la POI1 du ressort) dans le maillage.",
        commands=("LIRE_MAILLAGE",),
        keywords=("MODELISA5_3", "POI1"),
    )
    add(
        "DIAG-022",
        "Arrêt anormal à la lecture du maillage",
        "Un arrêt anormal par Segmentation fault dès LIRE_MAILLAGE signale un fichier de "
        "maillage absent de l'unité (pas de .export du même nom que le .comm) ou lu dans "
        "un autre format que le sien.",
        "A",
        "observé",
        [
            _run(
                "20260923T141049-0f80be92",
                "échec",
                "lot 30 : .export d'un autre nom, fort.20 absent",
            ),
            _run("20260924T092624-be572f9f", "échec", "lot 33 : aucun .export copié"),
            _run(
                "20260928T083040-fc18b62a",
                "échec",
                'lot 39 : FORMAT="MED" sur un maillage ASTER',
            ),
            _run(
                "20260928T083113-a4a49af7",
                "échec",
                'lot 39 : même cas en FORMAT="ASTER", lecture passée',
            ),
            _doc("docs/essais_lot30.md"),
        ],
        category="préparation",
        signature=Signature(kind="arrêt anormal", pattern="Segmentation fault"),
        cause="LIRE_MAILLAGE lit une unité vide ou d'un autre format sans message d'erreur.",
        established=True,
        correction=(
            "Nommer le .export et le maillage comme le .comm (aster-expert run copie les "
            "fichiers <nom>.* voisins) et accorder FORMAT au fichier."
        ),
        commands=("LIRE_MAILLAGE",),
        keywords=("FORMAT", "UNITE"),
    )
    add(
        "DIAG-023",
        "Fichier déclaré dans l'.export absent",
        "run_aster s'arrête (FileNotFoundError dans copy_datafiles) quand un fichier déclaré "
        "dans l'.export n'est pas à côté du .comm.",
        "A",
        "observé",
        [
            _run(
                "20260921T170137-2b50e2fd",
                "échec",
                "lot 27 : lot27_maillage.mmed absent",
            )
        ],
        category="préparation",
        signature=Signature(kind="arrêt anormal", pattern="FileNotFoundError"),
        cause="L'.export nommait un maillage qui n'avait pas été copié dans le répertoire de travail.",
        established=True,
        correction="Placer chaque fichier de l'.export à côté du .comm, sous le même nom de base.",
    )
    add(
        "DIAG-024",
        "MECA_STATIQUE sans CHAM_MATER",
        "MECA_STATIQUE sur un modèle de discrets seuls s'arrête (KeyError 'CHAM_MATER') "
        "sans champ de matériau, bien que le catalogue le dise facultatif.",
        "C",
        "établi",
        [
            _run("20260924T095848-d6e6c49e", "échec", "lot 33, ressort seul"),
            repo.case(
                "data/examples/lot33_equilibre/ressort_seul.comm",
                "réussite",
                "cas corrigé (matériau sans usage sous DIS_T)",
                "C",
            ),
        ],
        category="limite de Code_Aster",
        signature=Signature(kind="arrêt anormal", pattern="KeyError: 'CHAM_MATER'"),
        cause="PhysicalProblem exige un champ de matériau à l'exécution ; le catalogue le déclare optionnel.",
        established=True,
        correction="Affecter un matériau quelconque (DEFI_MATERIAU/ELAS) aux mailles des discrets.",
        commands=("AFFE_MATERIAU", "MECA_STATIQUE"),
        keywords=("CHAM_MATER", "DIS_T"),
    )
    add(
        "ENV-001",
        ".venv cassé par la mise à niveau d'Ubuntu",
        "La mise à niveau d'Ubuntu 24.04 vers 26.04 a retiré python3.12 et fait changer "
        "d'interpréteur un .venv créé avec le Python du système, sans qu'aucun fichier du "
        "dépôt ne change.",
        "A",
        "observé",
        [
            _doc("docs/environnement.md", section="4. Trace de panne"),
            _code("src/aster_expert/environnement/verification.py", "check_python"),
        ],
        category="environnement",
        signature=Signature(
            kind="environnement",
            pattern="ModuleNotFoundError: No module named '(_pytest|aster_expert)'",
        ),
        cause=(
            "Les liens .venv/bin/python3 suivaient /usr/bin/python3, passé à 3.14 : un "
            "interpréteur 3.14 ne lit pas lib/python3.12/site-packages."
        ),
        established=True,
        correction=(
            "uv dans l'espace utilisateur, uv python install 3.12, uv sync --locked "
            "--all-extras, puis env-check et mcp-check ; aucun sudo."
        ),
        prevention=(
            "Python géré par le projet (.python-version, python-preference = "
            '"only-managed"), uv.lock, env-check en tête de chaque lot.'
        ),
    )
    return out


def failure_classifications() -> dict[str, tuple[str, str | None, str]]:
    """Primary signature -> (decision, diagnostic, reason), for the 73 failures."""
    att = "rattaché"
    return {
        "<F> <FACTOR_11>": (
            att,
            "DIAG-001",
            "pivot nul des lots 28 à 31, cause établie au lot 31, levé au lot 32",
        ),
        "<F> <SOUSTRUC_37>": (
            att,
            "DIAG-002",
            "nom de groupe tronqué à 24 caractères (lot 28)",
        ),
        "<F> <FACTOR_57>": (
            att,
            "DIAG-003",
            "reproducteur du lot 28, levé par RESI_RELA relâché, cause non établie",
        ),
        "<F> <DISCRETS_26>": (
            att,
            "DIAG-004",
            "ressorts DIS_T sans masse sous PESANTEUR (lots 29 et 30)",
        ),
        "<F> <MED2_14>": (att, "DIAG-005", "IMPR_RESU sans CARA_ELEM (lots 29 et 31)"),
        "<F> <MED2_4>": (
            att,
            "DIAG-006",
            "collision de nom de champ MED (lots 31 et 32)",
        ),
        "<F> <MESH3_99>": (
            att,
            "DIAG-007",
            "VERI_NORM sur un groupe non connexe (lots 30 et 34)",
        ),
        "<F> <CHARGES2_46>": (
            att,
            "DIAG-008",
            "force sur BOLLARD hors modèle (lot 30, retrait de la poutre)",
        ),
        "<F> <CALCULEL2_92>": (
            att,
            "DIAG-009",
            "FORCE_POUTRE sur poutre liée (lot 33, CA-035)",
        ),
        "<F> <JEVEUX_10>": (
            att,
            "DIAG-010",
            "CREA_GROUP_NO à plusieurs GROUP_MA (lot 33)",
        ),
        "<F> <UTILITAI_4>": (
            att,
            "DIAG-011",
            "EFGE_NOEU sur repères locaux incompatibles (lot 35)",
        ),
        "<F> <POSTRELE_70>": (
            att,
            "DIAG-012",
            "POST_RELEVE_T sur champ de structure (lot 35)",
        ),
        "<F> <POSTRELE_38>": (att, "DIAG-013", "REPERE LOCAL refusé (lot 35)"),
        "<F> <CALCULEL7_40>": (
            att,
            "DIAG-014",
            "limite FERR_MIN_FISS poutre, échec voulu de l'essai (lot 39)",
        ),
        "<EXCEPTION> <MODELISA9_77>": (
            att,
            "DIAG-015",
            "RHO exigé sous PESANTEUR, échec voulu de l'essai B (lot 22)",
        ),
        "<EXCEPTION> <CALCUL_37>": (
            att,
            "DIAG-016",
            "CREA_TABLE sur SIEF_ELGA DKT (lot 23)",
        ),
        "<EXCEPTION> <MODELISA6_96>": (
            att,
            "DIAG-017",
            "FORCE_ARETE sur mailles hors modèle (lot 23)",
        ),
        "<EXCEPTION> <MODELISA7_10>": (
            att,
            "DIAG-018",
            "noms de mailles en double (lot 22)",
        ),
        "<EXCEPTION> <CALCULEL_6>": (
            att,
            "DIAG-019",
            "liste de noms sur une ligne (lot 21)",
        ),
        "<F> <MODELISA8_14>": (
            att,
            "DIAG-020",
            "POI1 écrite au nœud d'un QUAD4 (lot 29)",
        ),
        "<F> <MODELISA5_3>": (att, "DIAG-021", "maillage sans maille (lot 33)"),
        "arrêt anormal (Segmentation fault)": (
            att,
            "DIAG-022",
            "maillage absent ou de mauvais format (lots 30, 33, 39)",
        ),
        "<F> <MODELISA7_75>": (
            "écarté",
            None,
            "faute de frappe : GROUP_NO TUBE_08 laissé dans le reproducteur réduit du lot 28 ; le message nomme le groupe",
        ),
        "<F> <MODELISA7_77>": (
            "écarté",
            None,
            "faute de frappe : nom de groupe absent du maillage (lot 29 : GROUP_NO pour GROUP_MA ; lot 39 : M1 pour PoutreAB) ; le message nomme le groupe",
        ),
    }


def classify(signature: str, run: str) -> Classification:
    table = failure_classifications()
    if signature.startswith("arrêt anormal (FileNotFoundError"):
        return Classification(
            run=run,
            signature=signature,
            decision="rattaché",
            diagnostic="DIAG-023",
            reason="fichier de l'.export absent (lot 27)",
        )
    if signature.startswith("arrêt anormal (KeyError: 'CHAM_MATER'"):
        return Classification(
            run=run,
            signature=signature,
            decision="rattaché",
            diagnostic="DIAG-024",
            reason="CHAM_MATER exigé à l'exécution (lot 33)",
        )
    decision, diagnostic, reason = table[signature]
    return Classification.model_validate(
        {
            "run": run,
            "signature": signature,
            "decision": decision,
            "diagnostic": diagnostic,
            "reason": reason,
        }
    )


# ---------------------------------------------------------------------------
# Patrons
# ---------------------------------------------------------------------------


def _pattern(
    entry_id: str,
    title: str,
    summary: str,
    level: str,
    sources: list[Evidence],
    *,
    problem: str,
    solution: str,
    fragment: str,
    language: str,
    conditions: str,
    controls: tuple[str, ...] = (),
    constats: tuple[str, ...] = (),
    implementation: tuple[CodeEvidence, ...] = (),
    commands: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
) -> Pattern:
    return Pattern.model_validate(
        {
            **_common(
                entry_id, title, summary, level, "établi", sources, commands, keywords
            ),
            "problem": problem,
            "solution": solution,
            "fragment": fragment,
            "fragment_language": language,
            "conditions": conditions,
            "controls": controls,
            "constats": constats,
            "implementation": implementation,
        }
    )


def patterns(repo: _Repo) -> list[Pattern]:
    return [
        _pattern(
            "PAT-001",
            "Ressorts de sol nodaux par classe de raideur",
            "Les raideurs de sol nodales s'écrivent par classe de raideur (une occurrence "
            "de CREA_POI1 et de DISCRET par classe, jamais par nœud), avec une classe "
            "commune de raideur sommée pour chaque nœud partagé par deux bandes.",
            "D",
            [
                repo.case(
                    "data/examples/lot22_essais/essai_c/c.comm",
                    "réussite",
                    "plaque sur ressorts nodaux : DZ et résultante exacts",
                    "D",
                ),
                repo.case(
                    "data/examples/lot35_constats/f2_apres.ressorts.comm",
                    "réussite",
                    "classe commune : force du nœud partagé exacte",
                    "D",
                ),
                _test(
                    f"{TESTS}/test_generation_springs.py",
                    "test_a_node_shared_by_two_bands_gets_one_common_class_of_summed_stiffness",
                ),
                _doc(
                    "docs/essais_lot34.md",
                    note="cause (3) : CREA_POI1 une maille par nœud",
                ),
            ],
            problem=(
                "Représenter un sol par des ressorts nodaux de raideur k_h × aire tributaire, "
                "variable par couche, sur des milliers de nœuds, sans perdre la raideur aux "
                "nœuds communs à deux couches."
            ),
            solution=(
                "Grouper les nœuds de même raideur (mêmes VALE) en classes ; une occurrence "
                "CREA_POI1 par classe, DIS_T sur les POI1, DISCRET K_T_D_N et M_T_D_N = 0 par "
                "classe ; un nœud partagé reçoit une classe commune de raideur sommée, écrite "
                "après les autres (CREA_POI1 ne crée qu'une maille par nœud)."
            ),
            fragment=(
                "MAIL = CREA_MAILLAGE(\n    MAILLAGE=MAIL,\n    CREA_POI1=(\n"
                '        _F(NOM_GROUP_MA="GEN_RESS_ARGI_01", GROUP_NO=("GEN_RESS_ARGI_01",)),\n'
                "    ),\n)\n"
                "CARA = AFFE_CARA_ELEM(\n    MODELE=MO,\n    DISCRET=(\n"
                '        _F(GROUP_MA=("GEN_RESS_ARGI_01",), CARA="K_T_D_N", VALE=(0.0, 76015.34812908873, 0.0)),\n'
                '        _F(GROUP_MA=("GEN_RESS_ARGI_01",), CARA="M_T_D_N", VALE=(0.0,)),\n'
                "    ),\n)"
            ),
            language="comm",
            conditions=(
                "Élasticité linéaire (ressorts bilatéraux) ; la tolérance de comparaison de "
                "deux raideurs sur maillage irrégulier n'est pas établie ; ressorts appuis, "
                "sans masse (DIAG-004)."
            ),
            controls=("CTL-003", "CTL-004"),
            constats=("CA-020", "CA-034"),
            implementation=(
                _code(f"{GEN}/springs.py", "build_spring_classes"),
                _code(f"{GEN}/springs.py", "_combined_classes"),
            ),
            commands=("AFFE_CARA_ELEM", "AFFE_MODELE", "CREA_MAILLAGE"),
            keywords=("CREA_POI1", "DISCRET", "DIS_T", "K_T_D_N", "M_T_D_N", "POI1"),
        ),
        _pattern(
            "PAT-002",
            "Liaison tête de pieu tubulaire-poutre sans redondance",
            "Une tête de tube en coque se lie à la poutre de couronnement par une "
            "occurrence de LIAISON_SOLIDE par tube (anneau DKT + nœud de poutre), les "
            "blocages de symétrie excluant les ddl que la liaison détermine déjà.",
            "C",
            [
                _run(
                    "20260924T082421-4ed9a9c6",
                    "réussite",
                    "lot 32, modèle complet : DIAGNOSTIC JOB OK",
                    "C",
                ),
                _test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_symmetry_block_excludes_the_ring_from_every_determined_dof",
                ),
                _doc("docs/essais_lot32.md"),
                _ca("CA-008"),
                _ca("CA-032"),
            ],
            problem="Relier une coque (tube facetté) à une poutre transversale en T, à plusieurs appuis, dans un modèle à plans de symétrie.",
            solution=(
                "LIAISON_SOLIDE par tube ; au plan de symétrie, DDL_IMPO DX/DRY/DRZ sur le "
                "groupe du plan privé des nœuds d'anneau (DEFI_GROUP/DIFFE) ; lire les "
                "réactions sur les seules composantes bloquées (CA-036)."
            ),
            fragment=(
                "CH_SOLIDE = AFFE_CHAR_MECA(\n    MODELE=MO,\n    LIAISON_SOLIDE=(\n"
                '        _F(GROUP_NO=("TETE_TUBE_01", "GEN_POUTRE_01")),\n    ),\n)\n'
                "CH_BLOC = AFFE_CHAR_MECA(\n    MODELE=MO,\n    DDL_IMPO=(\n"
                '        _F(GROUP_NO=("GEN_SYMG_ROT",), DX=0.0, DRY=0.0, DRZ=0.0),\n    ),\n)'
            ),
            language="comm",
            conditions=(
                "Coques DKT, poutre POU_D_E ou POU_D_T, statique linéaire ; la numérotation "
                "interne de Code_Aster n'est pas éclairée (lots 28 à 32) : un autre ouvrage "
                "reprend le contrôle CTL-002."
            ),
            controls=("CTL-002",),
            constats=("CA-008", "CA-030", "CA-032", "CA-036", "CA-038"),
            implementation=(
                _code(f"{GEN}/comm.py", "liaison_solide_block"),
                _code(f"{GEN}/comm.py", "symmetry_and_support_block"),
            ),
            commands=("AFFE_CHAR_MECA", "DEFI_GROUP"),
            keywords=("DDL_IMPO", "DIFFE", "DKT", "LIAISON_SOLIDE", "POU_D_T"),
        ),
        _pattern(
            "PAT-003",
            "Pression des terres et de l'eau par couche, normales orientées",
            "Une pression qui saute d'une couche à l'autre s'applique par une occurrence "
            "de FORCE_COQUE/PRES par groupe de couche (CREA_GROUP_MA/BANDE), linéaire sur la "
            "couche, après orientation des normales vérifiée sur le maillage relu.",
            "D",
            [
                repo.case(
                    "data/examples/lot35_constats/f1_apres.sonde.comm",
                    "réussite",
                    "résultante assemblée à 2,1e-12 de la spécifiée",
                    "D",
                ),
                _test(
                    f"{TESTS}/test_generation_generate.py",
                    "test_lot35_the_oriented_mesh_follows_the_layer_groups",
                ),
                _doc("docs/essais_lot34.md"),
            ],
            problem="Appliquer un profil de pression par couches, discontinu aux interfaces, sur des coques à normales hétérogènes.",
            solution=(
                "MODI_MAILLAGE/ORIE_NORM_COQUE vers le côté chargé ; groupes de couche par "
                'CREA_GROUP_MA/BANDE (CRIT_NOEUD="TOUS") intersectés avec la surface chargée ; '
                'une fonction DEFI_FONCTION par couche ; VERI_NORM="NON" seulement après '
                "contrôle explicite des normales (CTL-007)."
            ),
            fragment=(
                'CH_G_POUSSEE = AFFE_CHAR_MECA_F(\n    MODELE=MO, VERI_NORM="NON",\n'
                '    FORCE_COQUE=(\n        _F(GROUP_MA=("GEN_COUCHE_MARNE",), PRES=F_G_MARNE),\n'
                '        _F(GROUP_MA=("GEN_COUCHE_ARGILE",), PRES=F_G_ARGILE),\n    ),\n)'
            ),
            language="comm",
            conditions=(
                "Interfaces de couche alignées sur des rangées de nœuds (sinon une maille "
                "reste sans pression, signalée par l'équilibre seulement) ; DKT QUAD4 plans."
            ),
            controls=("CTL-005", "CTL-007"),
            constats=("CA-012", "CA-028", "CA-029"),
            implementation=(
                _code(f"{GEN}/comm.py", "layered_pressure_load_block"),
                _code(f"{GEN}/comm.py", "pressure_layer_groups_block"),
            ),
            commands=(
                "AFFE_CHAR_MECA_F",
                "DEFI_FONCTION",
                "DEFI_GROUP",
                "MODI_MAILLAGE",
            ),
            keywords=(
                "BANDE",
                "CREA_GROUP_MA",
                "CRIT_NOEUD",
                "FORCE_COQUE",
                "ORIE_NORM_COQUE",
                "PRES",
                "VERI_NORM",
            ),
        ),
        _pattern(
            "PAT-004",
            "Demi-section d'un élément linéaire dans un plan de symétrie",
            "Un élément linéaire situé dans un plan de symétrie porte la moitié de sa "
            "section (A/2), un élément perpendiculaire au plan en étant dispensé par un motif "
            "écrit.",
            "B",
            [
                _test(
                    f"{TESTS}/test_generation_lot37.py",
                    "test_generated_comm_gives_half_section_to_the_edge_tie_rods_only",
                ),
                _test(
                    f"{TESTS}/test_generation_lot37.py",
                    "test_check_fails_on_the_lot36_comm",
                ),
                _doc("docs/essais_lot37.md"),
            ],
            problem="Modéliser une tranche symétrique dont les plans de coupe passent par des tirants ou des poutres.",
            solution=(
                "AFFE_CARA_ELEM/BARRE : une occurrence pour les éléments courants (A), une pour "
                "ceux du plan (A/2) ; contrôle check_symmetry_plane_sections avant écriture."
            ),
            fragment=(
                'BARRE=(\n    _F(GROUP_MA=("TIRANT_02",), SECTION="GENERALE", CARA="A", VALE=0.00442),\n'
                '    _F(GROUP_MA=("TIRANT_01", "TIRANT_09",), SECTION="GENERALE", CARA="A", VALE=0.00221),\n),'
            ),
            language="comm",
            conditions="Symétrie géométrique et de chargement ; le poids de l'élément suit la section.",
            controls=("CTL-001",),
            constats=("CA-030", "CA-031"),
            implementation=(_code(f"{GEN}/comm.py", "_barre_keyword"),),
            commands=("AFFE_CARA_ELEM",),
            keywords=("BARRE", "SECTION"),
        ),
        _pattern(
            "PAT-005",
            "Charge d'empreinte sur une surface de coques développée",
            "Une charge répartie sur une empreinte de coques facettées s'écrit par "
            "FORCE_COQUE en repère global, son intensité se rapportant à la surface "
            "développée des facettes, non à la surface projetée.",
            "D",
            [
                repo.case(
                    "data/examples/fcoque_essai/demi_cylindre.comm",
                    "réussite",
                    "résultante 2,22982 pour 2,229823 m² développés",
                    "D",
                ),
                _ca("CA-021"),
                _doc("docs/essai_lot21_force_coque.md"),
            ],
            problem="Appliquer un effort d'accostage connu (N) sur une empreinte de tube facetté.",
            solution=(
                "Intensité = effort / surface développée des mailles du groupe ; "
                "AFFE_CHAR_MECA/FORCE_COQUE avec FX, FY, FZ (repère global), jamais PRES."
            ),
            fragment=(
                "CH_A = AFFE_CHAR_MECA(\n"
                '    MODELE=MO, FORCE_COQUE=_F(GROUP_MA=("DEFENSE",), FY=718056.0475032325)\n)'
            ),
            language="comm",
            conditions="Direction fixe ; surface développée calculée sur le maillage réel (non sur la géométrie nominale).",
            controls=("CTL-005",),
            constats=("CA-018", "CA-021"),
            implementation=(_code(f"{GEN}/comm.py", "defense_force_block"),),
            commands=("AFFE_CHAR_MECA",),
            keywords=("FORCE_COQUE",),
        ),
        _pattern(
            "PAT-006",
            "Poids et charges d'une poutre liée en forces nodales tributaires",
            "Le poids et les charges d'une poutre continue liée par plusieurs LIAISON_SOLIDE "
            "s'appliquent en FORCE_NODALE sur longueurs tributaires, résultante et moment "
            "exacts par construction.",
            "D",
            [
                repo.case(
                    "data/examples/lot35_constats/f3_nodal.sonde.comm",
                    "réussite",
                    "résultante assemblée égale à la somme écrite",
                    "D",
                ),
                _test(
                    f"{TESTS}/test_generation_generate.py",
                    "test_poutre_pressure_charges_use_nodal_forces_not_force_poutre",
                ),
                _test(
                    f"{TESTS}/test_generation_generate.py",
                    "test_tributary_lengths_sum_to_the_total_span",
                ),
            ],
            problem="Charger une poutre de couronnement sans FORCE_POUTRE ni PESANTEUR répartie (CALCULEL2_92).",
            solution="FORCE_NODALE par nœud de poutre : q × longueur tributaire, demi-longueur aux plans de symétrie.",
            fragment=(
                "CH_G_POUTRE = AFFE_CHAR_MECA(\n    MODELE=MO,\n    FORCE_NODALE=(\n"
                '        _F(GROUP_NO=("GEN_POUTRE_01",), FY=-7452.899999999999, MX=-1739.0100000000007, FZ=-111588.74999999999),\n'
                "    ),\n)"
            ),
            language="comm",
            conditions="Poutre POU_D_E/POU_D_T liée par plusieurs LIAISON_SOLIDE ; la répartition le long des éléments n'est pas représentée (efforts aux nœuds).",
            controls=("CTL-005",),
            constats=("CA-019", "CA-035"),
            implementation=(_code(f"{GEN}/comm.py", "poutre_pressure_nodal_block"),),
            commands=("AFFE_CHAR_MECA",),
            keywords=("FORCE_NODALE", "FORCE_POUTRE", "LIAISON_SOLIDE"),
        ),
        _pattern(
            "PAT-007",
            "Plaque orthotrope ELAS_COQUE et lecture des efforts généralisés",
            "Une plaque orthotrope homogénéisée s'écrit en ELAS_COQUE sur DKT, axe L fixé par "
            "VECTEUR, et ses résultats se lisent en EFGE_ELNO/EFGE_NOEU, jamais en REAC_NODA, "
            "FORC_NODA ou SIEF_ELGA.",
            "D",
            [
                repo.case(
                    "data/examples/lot23_essais/essai_d1/d1.comm",
                    "réussite",
                    "MXX, QX et flèche exacts",
                    "D",
                ),
                repo.case(
                    "data/examples/lot25_essais/essai_d7a/d7a.comm",
                    "réussite",
                    "plan XZ, VECTEUR = (0, 0, 1)",
                    "D",
                ),
                _ca("CA-023"),
                _ca("CA-025"),
            ],
            problem="Représenter une palplanche (rigidités par unité de largeur différentes selon L et T) en coque.",
            solution=(
                "DEFI_MATERIAU/ELAS_COQUE (groupe MEMB_* … CISA_* complet, RHO masse "
                "volumique), AFFE_CARA_ELEM/COQUE avec EPAIS et VECTEUR ; efforts par "
                "EFGE_NOEU ; équilibre par les ressorts ou des appuis sans ELAS_COQUE."
            ),
            fragment=(
                "MAT_PALP = DEFI_MATERIAU(\n    ELAS_COQUE=_F(\n        MEMB_L=2908000000.0, MEMB_T=81000.0, MEMB_G_LT=526000000.0, MEMB_LT=0.0,\n"
                "        FLEX_L=89000000.0, FLEX_T=11300.0, FLEX_G_LT=8400.0, FLEX_LT=0.0,\n"
                "        CISA_L=526000000.0, CISA_T=526000000.0, RHO=7850.0,\n    )\n)\n"
                'COQUE=_F(GROUP_MA=("PALPS",), EPAIS=0.01385, VECTEUR=(0.0, 0.0, 1.0)),'
            ),
            language="comm",
            conditions=(
                "DKT QUAD4 ; torsion (FLEX_G_LT, MXY), couplages, COQUE_3D et DST non "
                "testés ; RHO × EPAIS fait le poids (CA-024)."
            ),
            constats=("CA-022", "CA-023", "CA-024", "CA-025", "CA-026", "CA-027"),
            implementation=(_code(f"{GEN}/comm.py", "_palp_coque_keyword"),),
            commands=("AFFE_CARA_ELEM", "CALC_CHAMP", "DEFI_MATERIAU"),
            keywords=(
                "DKT",
                "EFGE_ELNO",
                "EFGE_NOEU",
                "ELAS_COQUE",
                "FLEX_L",
                "FLEX_T",
                "REAC_NODA",
                "VECTEUR",
            ),
        ),
        _pattern(
            "PAT-008",
            "Script Salomé en partition unique, groupes sur la géométrie",
            "Un maillage d'ouvrage se produit par un script Salomé qui assemble toute la "
            "géométrie en une seule partition, crée les groupes sur la géométrie et impose "
            "un nombre entier de segments par arête, puis se vérifie par mesh check.",
            "B",
            [
                _test(
                    "tests/integration/test_reel_lent.py",
                    "test_salome_meshes_a_minimal_geometry_and_mesh_check_holds",
                ),
                _doc("docs/essais_lot26.md"),
                _doc("docs/essais_lot27.md"),
            ],
            problem="Garantir le partage des nœuds aux interfaces coque/poutre/barre et des groupes reproductibles.",
            solution=(
                "MakePartition en arguments nommés (KeepNonlimitShapes=1, 8e argument) entre "
                "# ASSEMBLY begin/end ; CreateGroup/UnionIDs puis GroupOnGeom ; segment_count "
                "par arête ; empreinte des paramètres dans <sortie>.meta.json."
            ),
            fragment=(
                "PARTITION = geompy.MakePartition(\n    ListShapes=faces + edges,\n    ListTools=[],\n"
                '    ListKeepInside=[],\n    ListRemoveInside=[],\n    Limit=geompy.ShapeType["FACE"],\n'
                "    RemoveWebs=0,\n    ListMaterials=[],\n    KeepNonlimitShapes=1,\n)"
            ),
            language="salome",
            conditions="Salomé-Méca V2024.1.0 (conteneur Singularity) ; signatures GEOM/SMESH relevées par introspection, jamais de mémoire.",
            controls=("CTL-008",),
            implementation=(
                _code(
                    "projets/quai_cw_test_01/maillage/combiwall_mesh.py",
                    "segment_count",
                ),
            ),
            keywords=("SEG2", "QUAD4"),
        ),
        _pattern(
            "PAT-009",
            "Efforts lus par CREA_TABLE, déplacements par POST_RELEVE_T",
            "Les efforts d'éléments de structure se lisent par CREA_TABLE sur EFGE_ELNO (ou "
            "EFGE_NOEU sur des groupes plans), imprimés en E20.12 avec un intitulé de 16 "
            "caractères au plus ; POST_RELEVE_T reste réservé aux déplacements et réactions.",
            "B",
            [
                _test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_displacements_by_post_releve_t_and_efforts_by_crea_table",
                ),
                _test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_control_tables_print_twelve_significant_digits",
                ),
                _doc("docs/essais_lot35.md"),
            ],
            problem="Extraire des efforts de coques facettées et de poutres sans les arrêts POSTRELE_70, POSTRELE_38, UTILITAI_4.",
            solution='CREA_TABLE/RESU (valeurs stockées), IMPR_TABLE FORMAT_R="E20.12", TITRE posé sur IMPR_TABLE.',
            fragment=(
                'TAB_EFTUBE_G = CREA_TABLE(\n    RESU=_F(\n        RESULTAT=EFA_G,\n        NOM_CHAM="EFGE_ELNO",\n'
                '        TOUT_ORDRE="OUI",\n        GROUP_MA=("TUBES",), NOM_CMP=("NXX", "NYY", "MXX", "MYY",),\n    ),\n)\n'
                'IMPR_TABLE(TABLE=TAB_EFTUBE_G, UNITE=6, FORMAT_R="E20.12", TITRE="EFTUBE_G")'
            ),
            language="comm",
            conditions="Code_Aster 17.4.0 ; IMPR_TABLE tronque l'intitulé à 16 caractères.",
            controls=("CTL-010",),
            implementation=(_code(f"{GEN}/comm.py", "synthesis_block"),),
            commands=("CALC_CHAMP", "CREA_TABLE", "IMPR_TABLE", "POST_RELEVE_T"),
            keywords=("EFGE_ELNO", "EFGE_NOEU", "FORMAT_R", "TITRE"),
        ),
    ]


# ---------------------------------------------------------------------------
# Contrôles
# ---------------------------------------------------------------------------


def _control(
    entry_id: str,
    title: str,
    summary: str,
    sources: list[Evidence],
    *,
    detects: str,
    parameters: str,
    implementation: CodeEvidence,
    caught: CaughtError,
    keywords: tuple[str, ...] = (),
    commands: tuple[str, ...] = (),
) -> Control:
    scope = "tronc commun" if implementation.path.startswith("src/") else "projet"
    return Control.model_validate(
        {
            **_common(
                entry_id, title, summary, "B", "établi", sources, commands, keywords
            ),
            "detects": detects,
            "parameters": parameters,
            "implementation": implementation,
            "scope": scope,
            "caught_error": caught,
        }
    )


def controls() -> list[Control]:
    return [
        _control(
            "CTL-001",
            "Demi-section dans un plan de symétrie",
            "Tout groupe linéaire situé dans un plan de symétrie doit porter la moitié de sa "
            "section, sauf dispense motivée par écrit.",
            [
                _test(
                    f"{TESTS}/test_generation_lot37.py",
                    "test_check_refuses_full_section_on_an_edge_tie_rod_and_half_inside",
                )
            ],
            detects="Une section entière (ou une demi-section hors du plan) sur un élément BARRE/POUTRE d'un plan de symétrie.",
            parameters="Plans de symétrie (X = constante), groupes linéaires, dispenses avec motif.",
            implementation=_code(f"{GEN}/comm.py", "check_symmetry_plane_sections"),
            caught=CaughtError(
                mode="a posteriori",
                description="Tirants de bord du lot 36 en section entière, relevés par MM à la relecture ; le contrôle refuse ce .comm.",
                evidence=_test(
                    f"{TESTS}/test_generation_lot37.py",
                    "test_check_fails_on_the_lot36_comm",
                ),
            ),
            keywords=("BARRE",),
            commands=("AFFE_CARA_ELEM",),
        ),
        _control(
            "CTL-002",
            "Aucun blocage redondant avec LIAISON_SOLIDE",
            "Aucune ligne DDL_IMPO ne bloque DX, DRY ou DRZ sur le groupe brut d'un plan de "
            "symétrie qui contient des nœuds liés par LIAISON_SOLIDE.",
            [
                _test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_control_rejects_a_direct_rotation_block_on_the_raw_plane",
                )
            ],
            detects="La redondance condition aux limites / relation cinématique qui produit le pivot nul FACTOR_11 (DIAG-001).",
            parameters="Groupes bruts des plans de symétrie, composantes déterminées par la liaison.",
            implementation=_code(
                f"{GEN}/comm.py", "check_symmetry_ddl_impo_no_ring_redundancy"
            ),
            caught=CaughtError(
                mode="a posteriori",
                description="Pivot nul des lots 28 à 31 ; écrit au lot 32, il refuse le blocage DX direct du plan brut.",
                evidence=_test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_control_rejects_a_direct_dx_block_on_the_raw_plane",
                ),
            ),
            keywords=("DDL_IMPO", "FACTOR_11", "LIAISON_SOLIDE"),
            commands=("AFFE_CHAR_MECA",),
        ),
        _control(
            "CTL-003",
            "Couverture des ressorts nodaux",
            "Chaque nœud à ressort appartient à une seule classe, et chaque nœud partagé par "
            "deux bandes à une classe commune de raideur sommée.",
            [
                _test(
                    f"{TESTS}/test_generation_springs.py",
                    "test_coverage_refuses_a_common_class_of_the_wrong_stiffness",
                )
            ],
            detects="Un nœud dont la raideur serait écrasée par une seconde DISCRET (CREA_POI1 une maille par nœud).",
            parameters="Classes de raideur, bandes de couche.",
            implementation=_code(f"{GEN}/springs.py", "check_spring_coverage"),
            caught=CaughtError(
                mode="a posteriori",
                description="Raideur de l'argile perdue sur 43 nœuds du quai réduit et 169 du modèle complet (lot 34).",
                evidence=_test(
                    f"{TESTS}/test_generation_springs.py",
                    "test_coverage_refuses_a_shared_node_without_its_common_class",
                ),
            ),
            keywords=("CREA_POI1", "DISCRET"),
        ),
        _control(
            "CTL-004",
            "Somme des raideurs par bande",
            "La somme des raideurs écrites dans une bande égale k_h × largeur projetée × "
            "hauteur de bande, à 1e-9 près.",
            [
                _test(
                    f"{TESTS}/test_generation_springs.py",
                    "test_a_broken_invariant_is_refused",
                )
            ],
            detects="Une erreur d'aire tributaire ou de conversion d'unités des ressorts.",
            parameters="k_h par couche, largeur projetée (band_projected_width), hauteur de bande.",
            implementation=_code(f"{GEN}/springs.py", "check_spring_sum"),
            caught=CaughtError(
                mode="aucune consignée",
                description="Aucune erreur réelle consignée ; au lot 30 c'est le contrôle lui-même (largeurs en dur) qui a dû être généralisé.",
            ),
            keywords=("K_T_D_N",),
        ),
        _control(
            "CTL-005",
            "Équilibre par cas de charge",
            "Pour chaque cas, la somme des réactions des composantes réellement bloquées et "
            "des forces des ressorts équilibre la charge appliquée, au seuil déclaré.",
            [
                _test(
                    "tests/unit/test_controles_equilibre.py",
                    "test_an_unbalanced_case_fails",
                )
            ],
            detects="Une charge mal assemblée, une raideur perdue, une lecture de réaction fausse.",
            parameters="Groupes d'appui et composantes bloquées, groupes de ressorts, résultantes attendues (projet.yaml).",
            implementation=_code(
                "src/aster_expert/controles/equilibre.py", "level_d_controls"
            ),
            caught=CaughtError(
                mode="attrapée",
                description="Écart d'équilibre du lot 33, expliqué au lot 34 par quatre causes (tri des profils, évaluation aux nœuds, CREA_POI1, composantes libres).",
                evidence=_doc("docs/essais_lot34.md"),
            ),
            keywords=("REAC_NODA", "RESULTANTE"),
            commands=("POST_RELEVE_T",),
        ),
        _control(
            "CTL-006",
            "Symétrie des déplacements",
            "Les déplacements de paires de nœuds symétriques sont égaux (composantes paires) ou "
            "opposés (composantes impaires), au seuil déclaré.",
            [
                _test(
                    "tests/unit/test_controles_equilibre.py",
                    "test_symmetry_about_an_offset_plane",
                )
            ],
            detects="Une condition de symétrie ou un chargement dissymétrique par erreur.",
            parameters="Plan de symétrie, paires de nœuds, seuil.",
            implementation=_code(
                "src/aster_expert/controles/equilibre.py", "symmetry_check"
            ),
            caught=CaughtError(
                mode="attrapée",
                description="Écart de 6,07e-7 au lot 33 : l'impression E12.5 limitait le critère ; tables passées en E20.12 (lot 34).",
                evidence=_doc("docs/essais_lot34.md"),
            ),
        ),
        _control(
            "CTL-007",
            "Normales des couches chargées",
            "Après ORIE_NORM_COQUE, chaque maille d'une couche chargée a sa normale du côté "
            "attendu sur le maillage relu hors de Code_Aster.",
            [
                _test(
                    f"{TESTS}/test_meshing_normals.py",
                    "test_altered_mesh_with_a_flipped_cell_is_rejected",
                )
            ],
            detects="Une maille retournée, qui inverserait la pression (VERI_NORM désactivé).",
            parameters="Groupes de couche, côté chargé, maillage orienté (unité 81).",
            implementation=_code(
                "projets/quai_cw_test_01/meshing/normals.py", "check_layer_normals"
            ),
            caught=CaughtError(
                mode="aucune consignée",
                description="Aucune maille retournée trouvée sur le quai (lot 35).",
            ),
            keywords=("ORIE_NORM_COQUE", "VERI_NORM"),
        ),
        _control(
            "CTL-008",
            "Invariants de maillage (mesh check)",
            "Le MED produit est relu sans Salomé et confronté à des invariants calculés "
            "analytiquement avant l'exécution : comptages, groupes, nœuds imposés, partagés, "
            "orphelins et confondus.",
            [
                _test(
                    "tests/unit/test_meshing_invariants.py",
                    "test_missing_group_and_wrong_type_and_bbox_are_reported",
                )
            ],
            detects="Une géométrie ou un groupe perdu, des nœuds non partagés aux interfaces.",
            parameters="Fichier d'invariants généré à partir des paramètres.",
            implementation=_code("src/aster_expert/meshing/check.py", "check_med"),
            caught=CaughtError(
                mode="attrapée",
                description="Lot 26 : RemoveWebs passé en 6e position de MakePartition, arêtes isolées supprimées (15 nœuds au lieu de 19).",
                evidence=_doc("docs/essais_lot26.md"),
            ),
        ),
        _control(
            "CTL-009",
            "Longueur des noms de groupes créés",
            "Tout nom de groupe créé par le générateur a 24 caractères au plus.",
            [
                _test(
                    f"{TESTS}/test_generation_lot36.py",
                    "test_v1_group_names_respect_the_group_name_limit",
                )
            ],
            detects="Un nom tronqué en silence par Code_Aster (DIAG-002).",
            parameters="Limite de 24 caractères.",
            implementation=_code(f"{GEN}/comm.py", "_gn"),
            caught=CaughtError(
                mode="a posteriori",
                description="Doublon SOUSTRUC_37 du lot 28.",
                evidence=_doc("docs/essais_lot28.md"),
            ),
            keywords=("SOUSTRUC_37",),
        ),
        _control(
            "CTL-010",
            "Intitulés des tables imprimées",
            "Chaque intitulé de table de contrôle tient en 16 caractères et est unique.",
            [
                _test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_a_too_long_reaction_table_title_is_refused",
                )
            ],
            detects="Deux tables rendues indiscernables par la troncature d'IMPR_TABLE.",
            parameters="Longueur 16, unicité.",
            implementation=_code(f"{GEN}/comm.py", "reaction_table_title"),
            caught=CaughtError(
                mode="a posteriori",
                description="Lot 34 : intitulés tronqués à 16 caractères, tables indiscernables.",
                evidence=_test(
                    f"{TESTS}/test_generation_comm.py",
                    "test_every_reaction_table_title_fits_the_printed_column_and_is_unique",
                ),
            ),
            commands=("IMPR_TABLE",),
        ),
        _control(
            "CTL-011",
            "Génération refusée sur un maillage non vérifié",
            "Le générateur refuse un maillage qui ne correspond pas au dernier mesh check réussi.",
            [
                _test(
                    f"{TESTS}/test_generation_generate.py",
                    "test_refuses_when_the_mesh_was_never_confirmed_verified",
                )
            ],
            detects="Un .comm bâti sur un maillage modifié ou jamais contrôlé.",
            parameters="Empreintes du script, des paramètres et du MED.",
            implementation=_code(
                "src/aster_expert/meshing/run.py", "find_verified_mesh"
            ),
            caught=CaughtError(
                mode="aucune consignée",
                description="Aucune erreur réelle consignée : garde préventive (lot 28).",
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Références de validation
# ---------------------------------------------------------------------------

_CRITERION_NOTE = (
    "Critère du dépôt (CLAUDE.md, « Critère de réussite des essais », à partir du lot "
    "25) : grandeur exacte à 1e-6 relatif, grandeur sensible à la discrétisation "
    "dont l'erreur décroît au raffinement ×2. Les essais antérieurs au lot 25 "
    "n'avaient pas écrit de critère : celui-ci leur est appliqué tel quel, sans "
    "adaptation."
)


class _Sources:
    """Execution sources of the findings, by (finding, case)."""

    def __init__(self, root: Path) -> None:
        self.by_case: dict[str, list[dict[str, Any]]] = {}
        for path in sorted(
            (root / "connaissances" / "constats_code_aster").glob("CA-*.json")
        ):
            data = json.loads(path.read_text(encoding="utf-8"))
            for s in data["entry"]["sources"]:
                if "case_path" in s:
                    s = {**s, "constat_id": data["constat_id"]}
                    self.by_case.setdefault(s["case_path"], []).append(s)

    def source(self, case: str, quantity_start: str) -> dict[str, Any]:
        found = [
            s for s in self.by_case[case] if s["quantity"].startswith(quantity_start)
        ]
        if len(found) != 1:
            message = f"{case} : {len(found)} source(s) pour « {quantity_start} »"
            raise ValueError(message)
        return found[0]

    def exact(
        self, case: str, start: str, tol: float = 1e-6, note: str | None = None
    ) -> ReferenceQuantity:
        s = self.source(case, start)
        q = {
            "name": s["quantity"],
            "value_obtained": s["value_obtained"],
            "reference_value": s["reference_value"],
            "criterion": "exact",
            "tolerance": tol,
            "note": note or f"{s['constat_id']} ; référence : {s['reference']}",
        }
        dev = abs((s["value_obtained"] - s["reference_value"]) / s["reference_value"])
        q["result"] = "réussi" if dev <= tol else "échec"
        return ReferenceQuantity.model_validate(q)

    def refined(
        self, case: str, start: str, fine_case: str, fine_start: str
    ) -> ReferenceQuantity:
        s = self.source(case, start)
        f = self.source(fine_case, fine_start)
        dev = abs((s["value_obtained"] - s["reference_value"]) / s["reference_value"])
        fdev = abs((f["value_obtained"] - f["reference_value"]) / f["reference_value"])
        return ReferenceQuantity.model_validate(
            {
                "name": s["quantity"],
                "value_obtained": s["value_obtained"],
                "reference_value": s["reference_value"],
                "criterion": "raffinement",
                "refined_case_path": fine_case,
                "refined_value": f["value_obtained"],
                "result": "réussi" if fdev < dev else "échec",
                "note": f"{s['constat_id']} ; référence : {s['reference']}",
            }
        )

    def level(self, case: str) -> str:
        return str(max(s["validation_level"] for s in self.by_case[case]))


def references(repo: _Repo) -> list[ValidationReference]:
    src = _Sources(repo.root)
    lot22 = "data/examples/lot22_essais"
    lot23 = "data/examples/lot23_essais"
    lot24 = "data/examples/lot24_essais"
    lot25 = "data/examples/lot25_essais"
    lot39 = "data/examples/lot39_essais"

    def ref(
        entry_id: str,
        title: str,
        summary: str,
        problem: str,
        solution: str,
        cases: list[tuple[str, list[ReferenceQuantity]]],
        docs: list[str],
        keywords: tuple[str, ...],
        commands: tuple[str, ...],
    ) -> ValidationReference:
        ref_cases = [
            ReferenceCase(
                case_path=c, case_sha256=sha256_path(repo.root / c), quantities=tuple(q)
            )
            for c, q in cases
        ]
        refined = sorted(
            {q.refined_case_path for _, qs in cases for q in qs if q.refined_case_path}
        )
        sources: list[Evidence] = [
            repo.case(c, "réussite", "cas versionné de la référence", src.level(c))
            for c, _ in cases
        ]
        sources += [
            repo.case(c, "réussite", "cas raffiné ×2", src.level(c)) for c in refined
        ]
        sources += [_doc(d) for d in docs]
        level = max(src.level(c) for c, _ in cases)
        result = (
            "réussi"
            if all(q.result == "réussi" for _, qs in cases for q in qs)
            else "échec"
        )
        return ValidationReference.model_validate(
            {
                **_common(
                    entry_id,
                    title,
                    summary,
                    level,
                    "établi",
                    sources,
                    commands,
                    keywords,
                ),
                "problem": problem,
                "reference_solution": solution + " " + _CRITERION_NOTE,
                "cases": tuple(ref_cases),
                "result": result,
            }
        )

    a = f"{lot22}/essai_a"
    d6 = f"{lot24}"
    return [
        ref(
            "REF-001",
            "Console ELAS_COQUE : orientation de L et T (essai A, lot 22)",
            "Flèche en bout d'une console DKT ELAS_COQUE chargée en bout, axe L le long ou en travers de la console, comparée à P·L³/(3·FLEX·b).",
            "Console DKT encastrée, charge linéique en bout, trois orientations du repère utilisateur.",
            "Solution analytique de poutre : P·L³/(3·FLEX·b).",
            [
                (f"{a}/a1.comm", [src.exact(f"{a}/a1.comm", "flèche en bout")]),
                (f"{a}/a2.comm", [src.exact(f"{a}/a2.comm", "flèche en bout")]),
                (f"{a}/a3.comm", [src.exact(f"{a}/a3.comm", "flèche en bout")]),
            ],
            ["docs/essais_lot22.md"],
            ("ANGL_REP", "DKT", "ELAS_COQUE", "FLEX_L", "FLEX_T", "VECTEUR"),
            ("AFFE_CARA_ELEM", "DEFI_MATERIAU"),
        ),
        ref(
            "REF-002",
            "Poids propre ELAS et ELAS_COQUE (essai B, lot 22)",
            "Résultante verticale des réactions de deux plaques sous PESANTEUR, comparée à RHO × EPAIS × g × aire.",
            "Deux plaques (ELAS, ELAS_COQUE) sous PESANTEUR ; la console b3, sensible à la discrétisation et sans cas raffiné, n'est pas une référence.",
            "Équilibre : RHO × EPAIS × g × aire.",
            [
                (
                    f"{lot22}/essai_b/b2.comm",
                    [
                        src.exact(
                            f"{lot22}/essai_b/b2.comm",
                            "résultante verticale des réactions de la plaque 1",
                        ),
                        src.exact(
                            f"{lot22}/essai_b/b2.comm",
                            "résultante verticale des réactions de la plaque 2",
                        ),
                    ],
                )
            ],
            ["docs/essais_lot22.md"],
            ("ELAS_COQUE", "PESANTEUR", "RHO"),
            ("AFFE_CHAR_MECA", "DEFI_MATERIAU"),
        ),
        ref(
            "REF-003",
            "Plaque sur ressorts nodaux (essai C, lot 22)",
            "Déplacement et résultante des ressorts d'une plaque posée sur des ressorts DIS_T proportionnels à l'aire tributaire, comparés à p/ks et p × aire.",
            "Plaque DKT sur ressorts DISCRET K_T_D_N, pression uniforme.",
            "Déplacement uniforme p/ks, résultante p × aire.",
            [
                (
                    f"{lot22}/essai_c/c.comm",
                    [
                        src.exact(f"{lot22}/essai_c/c.comm", "déplacement DZ"),
                        src.exact(
                            f"{lot22}/essai_c/c.comm",
                            "résultante DZ des forces nodales",
                        ),
                    ],
                )
            ],
            ["docs/essais_lot22.md"],
            ("CREA_POI1", "DISCRET", "DIS_T", "K_T_D_N"),
            ("AFFE_CARA_ELEM", "CREA_MAILLAGE"),
        ),
        ref(
            "REF-004",
            "Efforts généralisés d'une console ELAS_COQUE (essais D1 à D3, lot 23)",
            "MXX, QX et flèche d'une console DKT ELAS_COQUE, indépendants de EPAIS et de CISA, comparés à la statique et à P·L³/(3·FLEX·b).",
            "Console DKT ELAS_COQUE, EPAIS et CISA variés.",
            "Statique de console et flèche de poutre.",
            [
                (
                    f"{lot23}/essai_d1/d1.comm",
                    [
                        src.exact(
                            f"{lot23}/essai_d1/d1.comm",
                            "MXX moyen des points EFGE_ELNO en x = 0",
                        ),
                        src.exact(
                            f"{lot23}/essai_d1/d1.comm",
                            "MXX moyen des points EFGE_ELNO en x = L/2",
                        ),
                        src.exact(f"{lot23}/essai_d1/d1.comm", "|QX| moyen"),
                        src.exact(
                            f"{lot23}/essai_d1/d1.comm",
                            "MXX moyen des points EFGE_NOEU",
                        ),
                        src.exact(f"{lot23}/essai_d1/d1.comm", "flèche en bout"),
                    ],
                ),
                (
                    f"{lot23}/essai_d2/d2a.comm",
                    [
                        src.exact(f"{lot23}/essai_d2/d2a.comm", "MXX"),
                        src.exact(f"{lot23}/essai_d2/d2a.comm", "flèche"),
                    ],
                ),
                (
                    f"{lot23}/essai_d2/d2b.comm",
                    [
                        src.exact(f"{lot23}/essai_d2/d2b.comm", "MXX"),
                        src.exact(f"{lot23}/essai_d2/d2b.comm", "flèche"),
                    ],
                ),
                (
                    f"{lot23}/essai_d3/d3.comm",
                    [
                        src.exact(f"{lot23}/essai_d3/d3.comm", "MXX"),
                        src.exact(f"{lot23}/essai_d3/d3.comm", "flèche"),
                    ],
                ),
            ],
            ["docs/essais_lot23.md"],
            ("CISA_L", "CISA_T", "EFGE_ELNO", "EFGE_NOEU", "ELAS_COQUE", "EPAIS"),
            ("CALC_CHAMP", "DEFI_MATERIAU"),
        ),
        ref(
            "REF-005",
            "Modèle mixte ELAS_COQUE / ELAS (essai D5, lot 23)",
            "Résultantes d'appui et flèche d'une console ELAS_COQUE prolongée par des appuis sans ELAS_COQUE, comparées à la charge et à la flèche de poutre.",
            "Console ELAS_COQUE avec appuis par ressorts DIS_TR ou par éléments ELAS.",
            "Équilibre P = 5 N et P·L³/(3·FLEX·b).",
            [
                (
                    f"{lot23}/essai_d5/d5a.comm",
                    [src.exact(f"{lot23}/essai_d5/d5a.comm", "résultante DZ")],
                ),
                (
                    f"{lot23}/essai_d5/d5b.comm",
                    [
                        src.exact(f"{lot23}/essai_d5/d5b.comm", "résultante DZ"),
                        src.exact(f"{lot23}/essai_d5/d5b.comm", "flèche en bout"),
                    ],
                ),
            ],
            ["docs/essais_lot23.md"],
            ("DIS_TR", "ELAS_COQUE", "FORC_NODA", "REAC_NODA"),
            ("CALC_CHAMP",),
        ),
        ref(
            "REF-006",
            "Plaque orthotrope : membrane et cisaillement (essais D6a, D6c, lot 24)",
            "Allongement, effort normal et glissement d'une plaque ELAS_COQUE en membrane et en cisaillement, comparés aux solutions exactes.",
            "Plaque carrée DKT, coefficients de la décision 2, traction selon T et cisaillement pur.",
            "q·a/MEMB_T, NYY = q, γ·a = τ·a/MEMB_G_LT, NXY = τ.",
            [
                (
                    f"{d6}/essai_d6a/d6a.comm",
                    [
                        src.exact(f"{d6}/essai_d6a/d6a.comm", "allongement DX"),
                        src.exact(f"{d6}/essai_d6a/d6a.comm", "effort normal NYY"),
                        src.exact(
                            f"{d6}/essai_d6a/d6a.comm", "résultante REAC_NODA en X"
                        ),
                    ],
                ),
                (
                    f"{d6}/essai_d6c/d6c.comm",
                    [
                        src.exact(f"{d6}/essai_d6c/d6c.comm", "déplacement DX"),
                        src.exact(
                            f"{d6}/essai_d6c/d6c.comm", "effort de cisaillement NXY"
                        ),
                    ],
                ),
            ],
            ["docs/essais_lot24.md"],
            ("EFGE_NOEU", "ELAS_COQUE", "MEMB_G_LT", "MEMB_T"),
            ("DEFI_MATERIAU",),
        ),
        ref(
            "REF-007",
            "Plaque orthotrope : flexion cylindrique (essai D6b, lot 24)",
            "Flèche, moment et effort tranchant d'une plaque ELAS_COQUE en flexion cylindrique selon T, flèche et tranchant d'appui jugés au raffinement ×2.",
            "Plaque carrée DKT 8 × 8 puis 16 × 16, pression uniforme, appuis simples ; REAC_NODA d'appui, faux sous ELAS_COQUE (CA-023), n'est pas une grandeur de référence.",
            "5·p·a⁴/(384·FLEX_T), p·a²/8, p·(a − 2x)/2.",
            [
                (
                    f"{d6}/essai_d6b/d6b.comm",
                    [
                        src.refined(
                            f"{d6}/essai_d6b/d6b.comm",
                            "flèche DZ",
                            f"{d6}/essai_d6b/d6b16.comm",
                            "flèche DZ",
                        ),
                        src.exact(f"{d6}/essai_d6b/d6b.comm", "moment MYY"),
                        src.exact(
                            f"{d6}/essai_d6b/d6b.comm",
                            "effort tranchant QY (valeur absolue) moyen des nœuds EFGE_NOEU en x",
                        ),
                        src.refined(
                            f"{d6}/essai_d6b/d6b.comm",
                            "effort tranchant QY (valeur absolue) moyen des nœuds EFGE_NOEU d'appui",
                            f"{d6}/essai_d6b/d6b16.comm",
                            "effort tranchant QY",
                        ),
                    ],
                ),
            ],
            ["docs/essais_lot24.md"],
            ("EFGE_NOEU", "ELAS_COQUE", "FLEX_T"),
            ("DEFI_MATERIAU",),
        ),
        ref(
            "REF-008",
            "Coque dans le plan XZ : orientation par VECTEUR et ANGL_REP (essai D7, lot 25)",
            "Flèche en tête et moment d'encastrement d'une console verticale ELAS_COQUE selon trois orientations ; la flèche, classée sensible à la discrétisation par le critère écrit du lot 25, échoue à ce critère.",
            "Console DKT dans le plan XZ, charge linéique en tête, VECTEUR = (0, 0, 1), (1, 0, 0) et ANGL_REP = (0, −90).",
            "q·H³/(3·FLEX), q·H ; le lot 25 avait classé la flèche « sensible à la discrétisation » avant l'exécution, alors qu'elle est reproduite à la précision du solveur : échec rapporté tel quel (critère 2 du lot 25).",
            [
                (
                    f"{lot25}/essai_d7a/d7a.comm",
                    [
                        src.refined(
                            f"{lot25}/essai_d7a/d7a.comm",
                            "flèche en tête",
                            f"{lot25}/essai_d7a/d7a16.comm",
                            "flèche en tête",
                        ),
                        src.exact(f"{lot25}/essai_d7a/d7a.comm", "moment fléchissant"),
                    ],
                ),
                (
                    f"{lot25}/essai_d7b/d7b.comm",
                    [
                        src.refined(
                            f"{lot25}/essai_d7b/d7b.comm",
                            "flèche en tête",
                            f"{lot25}/essai_d7b/d7b16.comm",
                            "flèche en tête",
                        ),
                        src.exact(f"{lot25}/essai_d7b/d7b.comm", "moment fléchissant"),
                    ],
                ),
                (
                    f"{lot25}/essai_d7c/d7c.comm",
                    [src.exact(f"{lot25}/essai_d7c/d7c.comm", "flèche en tête")],
                ),
            ],
            ["docs/essais_lot25.md"],
            ("ANGL_REP", "EFGE_NOEU", "ELAS_COQUE", "VECTEUR"),
            ("AFFE_CARA_ELEM",),
        ),
        ref(
            "REF-009",
            "FORCE_COQUE sur un demi-cylindre facetté (lot 21)",
            "Résultante des réactions d'un demi-cylindre facetté sous FORCE_COQUE d'intensité unité, comparée à la surface développée ; écart 1,4e-6, au-delà du critère 1e-6, borné par l'impression E12.5 à six chiffres.",
            "Demi-cylindre de 36 × 10 facettes, FORCE_COQUE FX = 1.",
            "Surface développée exacte des facettes.",
            [
                (
                    "data/examples/fcoque_essai/demi_cylindre.comm",
                    [
                        src.exact(
                            "data/examples/fcoque_essai/demi_cylindre.comm",
                            "résultante DX",
                        )
                    ],
                )
            ],
            ["docs/essai_lot21_force_coque.md"],
            ("FORCE_COQUE", "REAC_NODA"),
            ("AFFE_CHAR_MECA",),
        ),
        ref(
            "REF-010",
            "Ferraillage ELU 1D de CALC_FERRAILLAGE contre le module rebar (lot 39)",
            "Aires d'acier ELU de CALC_FERRAILLAGE en flexion simple, composée, déviée et en cisaillement-torsion, comparées au calcul indépendant aster_expert.rebar.",
            "Section rectangulaire de poutre, efforts imposés un à un.",
            "Module aster_expert.rebar (EN 1992-1-1, procédure de Bresler de R7.04.05, θ = 21,8°).",
            [
                (
                    f"{lot39}/d19/d19.comm",
                    [
                        src.exact(f"{lot39}/d19/d19.comm", "AYS (m²), flexion simple"),
                        src.exact(
                            f"{lot39}/d19/d19.comm", "AYI (m²), flexion composée"
                        ),
                    ],
                ),
                (
                    f"{lot39}/limites/limites.comm",
                    [
                        src.exact(
                            f"{lot39}/limites/limites.comm", "AYI (m²), MFZ = -1"
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm", "AZS (m²), MFY = +1"
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm",
                            "AYS (m²), MFY = MFZ = 1 MN·m, ELU",
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm", "AZS (m²), MFY = MFZ = 3"
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm",
                            "AST (m²/m), VY = 4 MN seul",
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm",
                            "AST (m²/m), VZ = 4 MN seul",
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm", "AST (m²/m), MT = 4"
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm",
                            "AST (m²/m), VY = 4 MN et MT",
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm", "AST (m²/m), VY = VZ"
                        ),
                    ],
                ),
            ],
            ["docs/essais_lot39.md"],
            ("AST", "AYI", "AYS", "AZS"),
            ("CALC_FERRAILLAGE",),
        ),
        ref(
            "REF-011",
            "Ferraillage ELU 2D d'une plaque DKT (lot 39)",
            "Densités d'acier ELU de CALC_FERRAILLAGE sur une plaque DKT sous MXX seul et NXX seul, comparées au module rebar et à N/(2 fyd).",
            "Plaque DKT, efforts imposés ; le cas MXY, comparé à Wood-Armer (autre méthode), n'est pas une référence.",
            "aster_expert.rebar (bande de 1 m), N/(2 fyd) par nappe.",
            [
                (
                    f"{lot39}/plaque/plaque.comm",
                    [
                        src.exact(f"{lot39}/plaque/plaque.comm", "DNSXS (m²/m), MXX"),
                        src.exact(f"{lot39}/plaque/plaque.comm", "DNSXI (m²/m), NXX"),
                    ],
                )
            ],
            ["docs/essais_lot39.md"],
            ("DNSXI", "DNSXS"),
            ("CALC_FERRAILLAGE",),
        ),
        ref(
            "REF-012",
            "Ferraillage ELS caractéristique 1D (lot 39)",
            "Aires ELS caractéristiques 1D de CALC_FERRAILLAGE comparées au pivot acier de R7.04.05 refait par aster_expert.rebar : écarts de −4,4 % et +0,25 %, cause non établie.",
            "Section rectangulaire, MFZ puis MFY seuls, ELS caractéristique.",
            "Pivot acier de R7.04.05 (aster_expert.rebar.service).",
            [
                (
                    f"{lot39}/limites/limites.comm",
                    [
                        src.exact(
                            f"{lot39}/limites/limites.comm",
                            "AYS (m²), MFZ = 2 MN·m, ELS",
                        ),
                        src.exact(
                            f"{lot39}/limites/limites.comm",
                            "AZS (m²), MFY = 1 MN·m, ELS",
                        ),
                    ],
                )
            ],
            ["docs/essais_lot39.md"],
            ("AYS", "AZS"),
            ("CALC_FERRAILLAGE",),
        ),
        ref(
            "REF-013",
            "Ferraillage minimal EC2 en MPa (lot 39)",
            "Aires minimales FERR_MIN='EC2' en UNITE_CONTRAINTE='MPa', comparées aux formules 9.1N et 9.5N de l'EN 1992-1-1.",
            "Section rectangulaire, avec et sans effort, unités MPa et mm.",
            "EN 1992-1-1, 9.2.1.1 (9.1N) et 9.2.2(5) (9.5N), citées par article.",
            [
                (
                    f"{lot39}/fermin_mpa/fermin_mpa.comm",
                    [
                        src.exact(f"{lot39}/fermin_mpa/fermin_mpa.comm", "AYS (mm²)"),
                        src.exact(f"{lot39}/fermin_mpa/fermin_mpa.comm", "AZI (mm²)"),
                        src.exact(
                            f"{lot39}/fermin_mpa/fermin_mpa.comm", "AST (mm²/mm)"
                        ),
                    ],
                )
            ],
            ["docs/essais_lot39.md"],
            ("FERR_MIN", "UNITE_CONTRAINTE"),
            ("CALC_FERRAILLAGE",),
        ),
    ]


# ---------------------------------------------------------------------------
# Précédents
# ---------------------------------------------------------------------------


def precedents(root: Path) -> list[KnowledgeEntry]:
    sheet = HypothesesSheet.model_validate_json(
        (root / FICHE).read_text(encoding="utf-8")
    )
    out: list[KnowledgeEntry] = []
    n = 0
    for entry in sheet.entries:
        if not isinstance(entry, PracticeHypothesisEntry) or entry.status != "tranche":
            continue
        n += 1
        assert entry.decided_at is not None
        topic = entry.topic.strip().rstrip(".")
        summary = (
            f"Décision de MM au point {entry.point_label} de la fiche du quai "
            f"({entry.decided_at.date().isoformat()}) : {topic}."
        )
        note = _PRECEDENT_NOTES.get(entry.topic)
        out.append(
            precedent_from_entry(
                entry,
                precedent_id=f"PRE-{n:03d}",
                title=f"Point {entry.point_label} : {topic}",
                summary=f"{summary[:-1]} ; {note}." if note else summary,
                origin_project=PROJECT,
                fiche=FICHE,
                # Lot 44 : une décision prise après l'amorçage (D20, D21) est datée
                # du jour de son versement, non de celui de l'amorçage.
                recorded_on=max(RECORDED_ON, entry.decided_at.date()),
            )
        )
    return out


_PRECEDENT_NOTES = {
    "Maîtrise de la fissuration de la poutre de couronnement (section minimale, "
    "contrainte de l'acier)": (
        "D21 ; correspondance : l'arbitrage de la dalle "
        "(arbitrage_dalle_appuyee_01_v1, P6) la citait par erreur « PRE-021 », "
        "identifiant qui n'a jamais existé"
    ),
}
"""Lot 44: notes appended to a precedent's summary, by topic of the decision."""


def build_entries(root: Path) -> list[KnowledgeEntry]:
    repo = _Repo(root)
    return [
        *diagnostics(repo),
        *patterns(repo),
        *controls(),
        *references(repo),
        *precedents(root),
    ]


__all__ = [
    "PROJECT",
    "build_entries",
    "classify",
    "controls",
    "diagnostics",
    "failure_classifications",
    "patterns",
    "precedents",
    "references",
]
