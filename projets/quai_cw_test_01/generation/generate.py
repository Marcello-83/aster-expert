"""`aster-expert generate <fiche> <données> <maillage vérifié>` (lot 28, Étape 3).

Orchestrates the whole `.comm` build: refuses to run unless the fiche is
ready, the mesh was verified for the exact parameters the data file gives
today, and the five Étape 2 facts are present, then assembles the
deterministic text via `quai_cw_test_01.generation.comm` and writes it out.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Collection
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from aster_expert.agent.hypotheses import CodeAsterHypothesisEntry, HypothesesSheet
from aster_expert.agent.model_data import load_model_data
from aster_expert.constats.base import load_resolved_sheet
from aster_expert.meshing.run import REPORT_NAME as RUN_REPORT_NAME
from aster_expert.meshing.run import MeshRunReport, find_verified_mesh, sha256_file
from quai_cw_test_01.generation import comm
from quai_cw_test_01.generation.errors import GenerationError
from quai_cw_test_01.generation.profiles import layer_profiles
from quai_cw_test_01.generation.springs import (
    SpringClass,
    build_spring_classes,
    check_spring_coverage,
    check_spring_sum,
)
from quai_cw_test_01.generation.terre import REPOS_TABLE_KPA
from quai_cw_test_01.generation.values import ModelValues
from quai_cw_test_01.meshing.combiwall import (
    band_projected_width,
    build_params,
    expected_masses,
    tube_head_ring_points,
)

POUTRE_EXEMPT_MOTIF = (
    "poutre de couronnement d'axe X, perpendiculaire aux plans de symétrie "
    "X = constante "
    "qui la terminent : elle n'est pas coupée par eux, section entière"
)
"""Lot 37 : motif de dispense de la poutre de couronnement dans le contrôle de
demi-section (`comm.check_symmetry_plane_sections`)."""

_REQUIRED_FACT_TOPICS = (
    "Liaison de corps solide entre un anneau de nœuds de coque et un nœud de poutre",
    "Pression répartie fonction de Z sur des coques DKT",
    "Orientation cohérente des normales de coque pour qu'une pression positive "
    "agisse côté terre",
    "Évaluation aux nœuds de FORCE_COQUE/PRES (fonction) : une marche de pression "
    "à une interface de couches déborde d'une demi-maille",
    "Conditions de symétrie par rapport à un plan X = constante pour des coques "
    "DKT et des poutres POU_D_E",
    "Élément de barre : section, matériau, et absence de degré de rotation au "
    "nœud commun avec la coque",
    "Application d'une force et d'un moment nodaux sur un nœud d'élément de poutre",
    "Charge linéique répartie et moment linéique sur un élément de poutre "
    "(FORCE_POUTRE)",
)


def _params_json_bytes(params: dict[str, Any]) -> bytes:
    """Byte-identical to the `_json` of
    `projets/quai_cw_test_01/scripts/build_lot27_maillage.py`: the serialisation
    of the parameters file `mesh run` hashed at run time."""
    return (json.dumps(params, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _check_facts_present(sheet: HypothesesSheet) -> list[str]:
    topics = {
        e.topic
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.status == "tranche"
    }
    return [t for t in _REQUIRED_FACT_TOPICS if t not in topics]


class GenerationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    comm_sha256: str
    fiche_sha256: str
    data_sha256: str
    med_sha256: str
    aster_version: str
    n_spring_classes: int
    spring_sums_mn_per_m: dict[str, float]
    load_case_resultants_n: dict[str, tuple[float, float, float]]


def _tube_beam_points(params: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    axes = params["tube"]["axes_x"]
    y, z = params["poutre"]["y"], params["poutre"]["z"]
    return {f"{i:02d}": (x, y, z) for i, x in enumerate(axes, start=1)}


def _normal_reference_point(params: dict[str, Any]) -> tuple[float, float, float]:
    """A point on the land-side generatrix (angle 90 degrees, Y = +radius) of
    the central tube, at its head level -- any node of `ECRAN_POUSSEE`, whose
    geometric normal there is exactly (0, 1, 0)."""
    tube = params["tube"]
    central_axis = tube["axes_x"][tube["central"] - 1]
    return (central_axis, tube["rayon"], tube["cotes"][-1])


def _sorted_points(
    mv: ModelValues, name: str, component: str
) -> list[tuple[float, float]]:
    """Ascending `(z, p)` pairs of one component, built layer by layer
    (`quai_cw_test_01.generation.profiles.layered_profile`) -- never a sort of
    `(z, p)` pairs, which swaps the two points of an interface whose upper
    layer is the less loaded (lot 34). For `profiles.integrate_profile`
    (décision 13, lot 33, étape 2)."""
    from quai_cw_test_01.generation.profiles import layered_profile  # noqa: PLC0415

    return layered_profile(mv.profile_si(name), component)


def _tributary_lengths(axes: list[float]) -> list[float]:
    """Tributary length of each beam node along X (half the span to each
    neighbour; the two end nodes get only their own half-span, summing to
    the beam's own total length) -- lot 33, étape 3, needed to turn décision
    13's linear force/moment (N/m) into nodal forces (`poutre_pressure_
    nodal_block`, never `FORCE_POUTRE` -- see that function's own
    docstring)."""
    n = len(axes)
    lengths = []
    for i in range(n):
        left = (axes[i] - axes[i - 1]) / 2 if i > 0 else 0.0
        right = (axes[i + 1] - axes[i]) / 2 if i < n - 1 else 0.0
        lengths.append(left + right)
    return lengths


def _poutre_pressure_charges(
    mv: ModelValues,
    eau_p_profile: list[tuple[float, float]],
    eau_a_profile: list[tuple[float, float]],
    *,
    g_accel: float,
    beam_group_names: list[str],
    axes: list[float],
) -> dict[str, str]:
    """Décision 13 (point 12, lot 33, étape 2) : la poussée (G, Q1) et la
    pression d'eau (EAU_P, EAU_A) sur la hauteur de la poutre de
    couronnement (+2,60 à +4,00), représentées par une charge linéique
    (force par mètre) et un moment linéique de transport à l'axe de la
    poutre (+3,30) -- `quai_cw_test_01.generation.profiles.integrate_profile`,
    jamais une résultante calculée à la main. Les mêmes profils que l'écran
    (Q3 et A n'en ont pas -- ce sont des efforts ponctuels, hors profil).

    Lot 33, étape 3 : la charge linéique est répartie en forces nodales
    tributaires-pondérées aux `n_tubes` nœuds `GEN_POUTRE_<n>`
    (`_tributary_lengths`, `poutre_pressure_nodal_block`) -- jamais
    `FORCE_POUTRE`, écarté par une exécution réelle (voir le docstring de
    `poutre_pressure_nodal_block`). Le cas G porte aussi le poids propre de
    la poutre (`largeur x hauteur x masse_volumique x g`, jamais sous
    `PESANTEUR` -- voir `quai_cw_test_01.generation.comm.pesanteur_block`),
    réparti de la même façon."""
    from quai_cw_test_01.generation.profiles import integrate_profile  # noqa: PLC0415

    z_low = mv.si("poutre_couronnement.cote_sous_face")
    z_high = mv.si("poutre_couronnement.cote_arase")
    axis = mv.si("poutre_couronnement.cote_centre_gravite")
    tributary = _tributary_lengths(axes)
    nodes = [f"{comm.BEAM_NODE_PREFIX}{n}" for n in beam_group_names]

    def charge(
        concept: str,
        points: list[tuple[float, float]],
        *,
        fz_per_length: float | None = None,
    ) -> str:
        resultant, first_moment = integrate_profile(points, z_low, z_high)
        fy_per_length = -resultant
        mx_per_length = first_moment - axis * resultant
        node_loads = {
            node: (
                fy_per_length * t,
                mx_per_length * t,
                fz_per_length * t if fz_per_length is not None else None,
            )
            for node, t in zip(nodes, tributary, strict=True)
        }
        return comm.poutre_pressure_nodal_block(concept, node_loads)

    g_points = _sorted_points(mv, "eau_terres.profil_poussee_terres_permanent", "G")
    q1_points = _sorted_points(mv, "eau_terres.profil_poussee_terres_permanent", "Q1")

    largeur = mv.si("poutre_couronnement.largeur")
    hauteur = mv.si("poutre_couronnement.hauteur")
    rho = mv.si("poutre_couronnement.masse_volumique")
    poids_lineique = largeur * hauteur * rho * g_accel

    return {
        "G": charge("CH_G_POUTRE", g_points, fz_per_length=-poids_lineique),
        "Q1": charge("CH_Q1_POUTRE", q1_points),
        "EAU_P": charge("CH_EAU_P_POUTRE", eau_p_profile),
        "EAU_A": charge("CH_EAU_A_POUTRE", eau_a_profile),
    }


class DiagnosticOmissions(BaseModel):
    """Lot 30, étape 3 : options de retrait d'un seul ingrédient à la fois,
    pour isoler le pivot nul (`<F> <FACTOR_11>`) de `LIAISON_SOLIDE`
    (docs/essais_lot28.md, docs/essais_lot30.md). **Outil de diagnostic
    uniquement** : chaque champ, à `True`, produit un `.comm` qui ne
    représente plus le modèle du quai et ne sert jamais à une production
    (CLAUDE.md, lot 30, « interdits »). Par défaut (tous `False`), le `.comm`
    produit est strictement celui de la production -- les tests de
    régression le vérifient octet pour octet."""

    model_config = ConfigDict(frozen=True)

    sans_ressorts: bool = False
    """Aucune classe de ressort : ni `CREA_POI1`, ni `DIS_T`, ni le contrôle
    d'équilibre des ressorts (`quai_cw_test_01.generation.comm.controls_block`
    omet `TAB_RESS_*` en leur absence)."""

    sans_tirants: bool = False
    """Aucun tirant : ni modélisation `BARRE`, ni matériau, ni blocage
    d'`ANCRAGES` (`CH_BLOC`), ni ce groupe dans le contrôle d'équilibre des
    réactions."""

    sans_palplanches: bool = False
    """Aucune palplanche : ni modélisation DKT ni matériau sur `PALPS` ; les
    charges de pression (point 5) portent alors sur `GEN_ECRAN_POUSSEE_TUBES`
    (`ECRAN_POUSSEE` moins `PALPS`, `quai_cw_test_01.generation.comm
    .ecran_poussee_tubes_group_block`) plutôt que sur `ECRAN_POUSSEE`, qui
    mêlerait une maille non affectée."""

    sans_poutre: bool = False
    """Aucune poutre de couronnement, donc aucune `LIAISON_SOLIDE` (`CH_
    SOLIDE` n'existe pas dans cette variante -- omis de `EXCIT` par
    `case_block`) ; BOLLARD exclu du contrôle de symétrie."""


class SolverDiagnostics(BaseModel):
    """Lot 33, étape 1 : isole l'effet de deux paramètres hérités des
    tentatives du lot 28, jamais démontrés nécessaires isolément
    (`docs/essais_lot28.md`, `docs/essais_lot33.md`) -- `SOLVEUR/RESI_RELA`
    (`quai_cw_test_01.generation.comm.SOLVER_RESI_RELA`, relaxé du défaut
    catalogue) et `COEF_RIGI_DRZ` (`comm.DRZ_STIFFNESS_COEF`, relevé du
    défaut catalogue). Testés un à la fois sur le quai réduit, tous deux se
    sont révélés inutiles à leur valeur de défaut catalogue ; la production
    ne passe donc plus aucun des deux mots-clés (`None` -> omis du `.comm`).
    **Outil de diagnostic uniquement** : une valeur non nulle ajoute le
    mot-clé correspondant, avec cette valeur, et produit un `.comm` qui ne
    représente plus la production. Par défaut (aucune valeur), le `.comm`
    produit est strictement celui de la production -- les tests de
    régression le vérifient octet pour octet."""

    model_config = ConfigDict(frozen=True)

    resi_rela: float | None = None
    coef_rigi_drz: float | None = None


class JunctionCandidate(BaseModel):
    """Lot 31, étape 2 : méthode de jonction tête de tube / poutre de
    couronnement, comparée sur le quai réduit. **Outil de diagnostic
    uniquement** : `method` autre que `liaison_solide` produit un `.comm` qui
    ne représente plus la décision de la fiche (point 3) et ne sert jamais à
    une production (CLAUDE.md, lot 31, « interdits »). Par défaut
    (`liaison_solide`), le `.comm` produit est strictement celui de la
    production -- les tests de régression le vérifient octet pour octet."""

    model_config = ConfigDict(frozen=True)

    method: comm.JunctionMethod = "liaison_solide"
    """`liaison_solide` (production, point 3, inchangée) ; `liaison_ddl_
    translations` (candidat C1 : translations de chaque nœud d'anneau liées à
    celles du nœud de poutre par LIAISON_DDL, bras de levier inclus,
    rotations de l'anneau libres) ; `noeud_unique` (candidat C4 : un seul
    nœud d'anneau -- le plus proche de la poutre -- rigidement lié au nœud de
    poutre)."""


class EquilibriumProbe(BaseModel):
    """Lot 34, étape 1 : sonde de la charge assemblée par Code_Aster.
    **Outil de diagnostic uniquement** : `blocage_total` à `True` produit un
    `.comm` où tous les degrés de liberté de tous les nœuds sont bloqués, sans
    `LIAISON_SOLIDE`, sans ressort lu ni symétrie ; `REAC_NODA` sommé sur tous
    les nœuds donne alors la charge assemblée (`comm.assembled_load_block`).
    Ne représente plus le modèle du quai. Par défaut (`False`), le `.comm`
    produit est strictement celui de la production -- les tests de régression
    le vérifient octet pour octet."""

    model_config = ConfigDict(frozen=True)

    blocage_total: bool = False

    pression_sur: Literal["ecran", "tubes", "palplanches", "aucune"] = "ecran"
    """Étape 1 (localisation d'un écart) : où porte la pression de poussée
    (`ecran` : `ECRAN_POUSSEE`, production ; `tubes` : `ECRAN_POUSSEE` moins
    `PALPS` ; `palplanches` : `PALPS` seul ; `aucune` : charge de poutre et
    poids seuls). Sans effet hors `blocage_total`."""

    extraction_nodale: bool = False
    """Ajoute la table `REAC_NODA` nœud par nœud (DY, DZ) à chaque cas, pour
    localiser un écart. Sans effet hors `blocage_total`."""

    forces_ressorts: bool = False
    """Modèle de production seulement (`blocage_total` faux) : ajoute la force
    des ressorts telle que Code_Aster la calcule (`FORC_NODA` restreint aux
    `POI1`, `comm.spring_force_block`) pour la comparer à k * DY."""


class InitialPressureDiagnostic(BaseModel):
    """Lot 36, étape 2, variante V1. **Outil de diagnostic uniquement** : à `True`,
    `pression_repos_bassin` ajoute au cas G une pression initiale au repos K0·σ'v
    côté bassin, dirigée vers la terre, sur les faces bassin de la fiche
    (`comm.initial_pressure_load_block`). Ne modifie pas la décision 5 et ne
    représente pas le modèle de calcul. Par défaut (`False`), le `.comm` produit est
    strictement celui de la production -- les tests de régression le vérifient octet
    pour octet."""

    model_config = ConfigDict(frozen=True)

    pression_repos_bassin: bool = False


def generate_comm(
    *,
    fiche_path: Path,
    data_path: Path,
    med_path: Path,
    project_root: Path,
    work_dir_root: str,
    aster_version: str,
    diagnostic: DiagnosticOmissions | None = None,
    junction: JunctionCandidate | None = None,
    solver: SolverDiagnostics | None = None,
    probe: EquilibriumProbe | None = None,
    initial_pressure: InitialPressureDiagnostic | None = None,
    waived_revisions: Collection[tuple[str, str]] = (),
) -> tuple[str, GenerationReport]:
    repos = (initial_pressure or InitialPressureDiagnostic()).pression_repos_bassin
    omit = diagnostic or DiagnosticOmissions()
    probe_cfg = probe or EquilibriumProbe()
    probing = probe_cfg.blocage_total
    pressure_on = probe_cfg.pression_sur if probing else "ecran"
    junc = junction or JunctionCandidate()
    slv = solver or SolverDiagnostics()
    if not fiche_path.is_file():
        message = f"fiche introuvable : {fiche_path}"
        raise GenerationError(message)
    if not data_path.is_file():
        message = f"fichier de données introuvable : {data_path}"
        raise GenerationError(message)
    if not med_path.is_file():
        message = f"maillage introuvable : {med_path}"
        raise GenerationError(message)

    sheet = load_resolved_sheet(fiche_path)
    data = load_model_data(data_path)
    blockers = sheet.generation_blockers(data, waived_revisions=waived_revisions)
    if blockers:
        message = (
            "génération refusée, la fiche ou les données ne sont pas prêtes :\n"
            + "\n".join(f"- {b}" for b in blockers)
        )
        raise GenerationError(message)

    missing_facts = _check_facts_present(sheet)
    if missing_facts:
        message = (
            "génération refusée, fait(s) de l'étape 2 manquant(s) :\n"
            + "\n".join(f"- {t}" for t in missing_facts)
        )
        raise GenerationError(message)

    params = build_params(data)
    current_params_sha = hashlib.sha256(_params_json_bytes(params)).hexdigest()

    run_report_path = med_path.parent / RUN_REPORT_NAME
    if not run_report_path.is_file():
        message = f"aucun rapport de mesh run à côté du maillage : {run_report_path}"
        raise GenerationError(message)
    run_report = MeshRunReport.model_validate_json(
        run_report_path.read_text(encoding="utf-8")
    )
    if run_report.params_sha256 != current_params_sha:
        message = (
            "génération refusée : le rapport de maillage ne porte pas sur les mêmes "
            f"empreintes de paramètres (maillage : {run_report.params_sha256}, "
            f"données actuelles : {current_params_sha})"
        )
        raise GenerationError(message)

    verified = find_verified_mesh(
        project_root / work_dir_root,
        script_sha256=run_report.script_sha256,
        params_sha256=run_report.params_sha256,
    )
    if verified is None or Path(verified.med_path).resolve() != med_path.resolve():
        message = (
            "génération refusée : ce maillage n'est pas confirmé vérifié par mesh "
            "check pour son empreinte script/paramètres (cache de maillage)"
        )
        raise GenerationError(message)

    mv = ModelValues(data)

    beam_points = _tube_beam_points(params)
    beam_group_names = list(beam_points)
    edge_tube_low, edge_tube_high = min(beam_group_names), max(beam_group_names)
    # Lot 37 : les tirants des tubes de bord sont dans les plans de symétrie
    # (décision 8,
    # point 7) : demi-section.
    tirant_groups = [f"TIRANT_{n}" for n in beam_group_names]
    edge_tirant_groups = sorted({f"TIRANT_{edge_tube_low}", f"TIRANT_{edge_tube_high}"})
    beam_group_full_names = {
        f"{comm.BEAM_NODE_PREFIX}{n}": p for n, p in beam_points.items()
    }
    normal_ref = _normal_reference_point(params)

    k_h = {
        "RESS_AV_ARGI": float(mv.raw("sol.k_h_argile_marneuse_raide")),
        "RESS_AV_MARNE": float(mv.raw("sol.k_h_marne_compacte")),
    }
    if omit.sans_ressorts:
        spring_classes: list[SpringClass] = []
    else:
        spring_classes = build_spring_classes(params, k_h)
        check_spring_coverage(spring_classes)
        for band_name in ("RESS_AV_ARGI", "RESS_AV_MARNE"):
            band = params["bandes"][band_name]
            check_spring_sum(
                spring_classes,
                band=band_name,
                k_h=k_h[band_name],
                projected_width_m=band_projected_width(params, band),
                projected_height_m=band["cote_haut"] - band["cote_bas"],
            )
    spring_group_names = [c.group_name for c in spring_classes]

    earth_points = mv.profile_si("eau_terres.profil_poussee_terres_permanent")
    g_layers = layer_profiles(earth_points, "G")
    q1_layers = layer_profiles(earth_points, "Q1")
    if [(x.name, x.z_low, x.z_high) for x in g_layers] != [
        (x.name, x.z_low, x.z_high) for x in q1_layers
    ]:
        message = "les composantes G et Q1 de la poussée n'ont pas les mêmes couches"
        raise GenerationError(message)
    eau_p_points = mv.profile_si("eau_terres.profil_pression_eau_permanent")
    eau_a_points = mv.profile_si("eau_terres.profil_pression_eau_accidentel")
    eau_p_profile = [(z, p) for z, p, _, _ in sorted(eau_p_points)]
    eau_a_profile = [(z, p) for z, p, _, _ in sorted(eau_a_points)]

    g_accel = mv.si("charges.acceleration_pesanteur")

    amarrage_fy = -mv.si("charges.amarrage_composante_horizontale")
    amarrage_effort = mv.si("charges.amarrage_effort")
    amarrage_incl = mv.si("charges.amarrage_inclinaison")
    amarrage_fz = amarrage_effort * math.sin(amarrage_incl)
    amarrage_mx = mv.si("charges.amarrage_moment_transport")

    accostage_effort = mv.si("charges.accostage_effort")
    defense_area = expected_masses(params)["DEFENSE"]["mass"]
    accostage_fy = accostage_effort / defense_area

    poussee_group_ma = (
        comm.ECRAN_POUSSEE_TUBES_GROUP
        if omit.sans_palplanches or pressure_on == "tubes"
        else "PALPS"
        if pressure_on == "palplanches"
        else "ECRAN_POUSSEE"
    )
    pressure_veri_norm = not omit.sans_palplanches and pressure_on == "ecran"

    poutre_pressure_charges = (
        {}
        if omit.sans_poutre
        else _poutre_pressure_charges(
            mv,
            eau_p_profile,
            eau_a_profile,
            g_accel=g_accel,
            beam_group_names=beam_group_names,
            axes=params["tube"]["axes_x"],
        )
    )

    # Lot 31, étape 2 : coordonnées analytiques de chaque nœud d'anneau de
    # tête, exigées par les candidats C1/C4 (comm.junction_ring_groups_block,
    # comm.junction_charge_block) -- jamais lues du MED, jamais nécessaires
    # sous LIAISON_SOLIDE (méthode de production, qui travaille sur
    # TETE_TUBE_<n> entier) ni quand la poutre elle-même n'existe pas.
    ring_points: dict[str, tuple[tuple[float, float, float], ...]] = (
        {}
        if omit.sans_poutre or junc.method == "liaison_solide"
        else {n: tube_head_ring_points(params, int(n)) for n in beam_group_names}
    )
    junction_charge = (
        ""
        if omit.sans_poutre or probing
        else comm.junction_charge_block(
            junc.method, beam_group_names, ring_points, beam_points
        )
    )

    def _controls(name: str, **kwargs: Any) -> str:
        if probing:
            return comm.assembled_load_block(name, nodal=probe_cfg.extraction_nodale)
        return comm.controls_block(
            name,
            spring_group_names,
            sans_tirants=omit.sans_tirants,
            spring_force_check=probe_cfg.forces_ressorts,
            **kwargs,
        )

    def _press(concept: str) -> list[str]:
        return [] if pressure_on == "aucune" else [concept]

    def _order(name: str) -> str:
        return "" if probing else comm.order_of_magnitude_block(name, beam_group_names)

    # Lot 35, étape 3 : les tubes dont on trace le profil de DY -- le tube central
    # (axe X = 0 : TUBE_05 du modèle complet) et le premier (TUBE_01, sur la face de
    # coupe SYM_G) ; un seul si le modèle n'en a qu'un.
    profile_tubes = tuple(dict.fromkeys((int(params["tube"]["central"]), 1)))
    head_groups = [f"TETE_TUBE_{n}" for n in beam_group_names]

    def _synthesis(name: str) -> str:
        if probing:
            return ""
        return comm.synthesis_block(
            name,
            profile_tubes=profile_tubes,
            head_groups=head_groups,
            sans_tirants=omit.sans_tirants,
            sans_palplanches=omit.sans_palplanches,
            sans_poutre=omit.sans_poutre,
            spring_group_names=spring_group_names,
        )

    text_parts = [
        comm.header(
            aster_version=aster_version,
            fiche_sha256=sha256_file(fiche_path),
            data_sha256=sha256_file(data_path),
            med_sha256=sha256_file(med_path),
        ),
        comm.mesh_prep_block(
            beam_points=beam_group_full_names,
            normal_ref_point=normal_ref,
            spring_classes=spring_classes,
            spring_bands={
                band: (b["cote_bas"], b["cote_haut"])
                for band, b in params["bandes"].items()
            },
            edge_tube_low=edge_tube_low,
            edge_tube_high=edge_tube_high,
            junction_method=junc.method,
            ring_points=ring_points,
        ),
        comm.six_dof_group_block() if probing else "",
        "" if probing else comm.profile_node_groups_block(profile_tubes),
        (
            comm.ecran_poussee_tubes_group_block()
            if omit.sans_palplanches or pressure_on == "tubes"
            else ""
        ),
        comm.pressure_layer_groups_block(g_layers, poussee_group_ma=poussee_group_ma),
        comm.initial_pressure_groups_block() if repos else "",
        "" if probing else comm.oriented_mesh_block(),
        comm.model_and_cara_block(
            mv,
            spring_classes,
            sans_tirants=omit.sans_tirants,
            sans_palplanches=omit.sans_palplanches,
            sans_poutre=omit.sans_poutre,
            coef_rigi_drz=slv.coef_rigi_drz,
            tirant_groups=tirant_groups,
            half_section_tirant_groups=edge_tirant_groups,
        ),
        comm.materials_block(
            mv,
            sans_tirants=omit.sans_tirants,
            sans_palplanches=omit.sans_palplanches,
            sans_poutre=omit.sans_poutre,
        ),
        junction_charge,
        (
            comm.full_block_charge_block()
            if probing
            else comm.symmetry_and_support_block(
                sans_tirants=omit.sans_tirants,
                split_ring_rotation=junc.method == "liaison_solide",
            )
        ),
        comm.layer_pressure_functions_block("G", g_layers),
        comm.layer_pressure_functions_block("Q1", q1_layers),
        comm.formule_block("F_EAU_P", eau_p_profile),
        comm.formule_block("F_EAU_A", eau_a_profile),
        comm.layered_pressure_load_block("CH_G_POUSSEE", "G", g_layers),
        (
            comm.initial_pressure_load_block("CH_G_REPOS", REPOS_TABLE_KPA)
            if repos
            else ""
        ),
        comm.pesanteur_block(
            "CH_G_POIDS",
            g_accel,
            sans_tirants=omit.sans_tirants,
            sans_palplanches=omit.sans_palplanches,
        ),
        comm.layered_pressure_load_block("CH_Q1", "Q1", q1_layers),
        comm.pressure_load_block(
            "CH_EAU_P",
            "F_EAU_P",
            group_ma=poussee_group_ma,
            veri_norm=pressure_veri_norm,
        ),
        comm.pressure_load_block(
            "CH_EAU_A",
            "F_EAU_A",
            group_ma=poussee_group_ma,
            veri_norm=pressure_veri_norm,
        ),
        (
            ""
            if omit.sans_poutre
            else comm.bollard_force_block(
                "CH_Q3", fy=amarrage_fy, fz=amarrage_fz, mx=amarrage_mx
            )
        ),
        comm.defense_force_block("CH_A", fy=accostage_fy),
        poutre_pressure_charges.get("G", ""),
        poutre_pressure_charges.get("EAU_P", ""),
        poutre_pressure_charges.get("EAU_A", ""),
        poutre_pressure_charges.get("Q1", ""),
        comm.case_block(
            "G",
            extra_charges=[
                *_press("CH_G_POUSSEE"),
                *(["CH_G_REPOS"] if repos else []),
                "CH_G_POIDS",
                *(["CH_G_POUTRE"] if "G" in poutre_pressure_charges else []),
            ],
            sans_poutre=omit.sans_poutre or probing,
            resi_rela=slv.resi_rela,
        ),
        _controls("G"),
        _synthesis("G"),
        _order("G"),
        comm.case_block(
            "EAU_P",
            extra_charges=[
                *_press("CH_EAU_P"),
                *(["CH_EAU_P_POUTRE"] if "EAU_P" in poutre_pressure_charges else []),
            ],
            sans_poutre=omit.sans_poutre or probing,
            resi_rela=slv.resi_rela,
        ),
        _controls("EAU_P"),
        _synthesis("EAU_P"),
        comm.case_block(
            "EAU_A",
            extra_charges=[
                *_press("CH_EAU_A"),
                *(["CH_EAU_A_POUTRE"] if "EAU_A" in poutre_pressure_charges else []),
            ],
            sans_poutre=omit.sans_poutre or probing,
            resi_rela=slv.resi_rela,
        ),
        _controls("EAU_A"),
        _synthesis("EAU_A"),
        comm.case_block(
            "Q1",
            extra_charges=[
                *_press("CH_Q1"),
                *(["CH_Q1_POUTRE"] if "Q1" in poutre_pressure_charges else []),
            ],
            sans_poutre=omit.sans_poutre or probing,
            resi_rela=slv.resi_rela,
        ),
        _controls("Q1"),
        _synthesis("Q1"),
        *(
            []
            if omit.sans_poutre
            else [
                comm.case_block(
                    "Q3",
                    extra_charges=["CH_Q3"],
                    sans_poutre=omit.sans_poutre or probing,
                    resi_rela=slv.resi_rela,
                ),
                _controls("Q3"),
                _synthesis("Q3"),
                _order("Q3"),
            ]
        ),
        comm.case_block(
            "A",
            extra_charges=["CH_A"],
            sans_poutre=omit.sans_poutre or probing,
            resi_rela=slv.resi_rela,
        ),
        _controls("A"),
        _synthesis("A"),
        (
            "\nFIN()\n"
            if probing
            else comm.footer(
                [
                    n
                    for n in ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")
                    if n != "Q3" or not omit.sans_poutre
                ],
                springs=bool(spring_group_names),
            )
        ),
    ]
    text = "".join(text_parts)
    tirant_section = mv.si("tirants.section_brute")
    tirants = [] if omit.sans_tirants else tirant_groups
    comm.check_symmetry_plane_sections(
        text,
        in_plane={
            g: ("BARRE", tirant_section) for g in tirants if g in edge_tirant_groups
        },
        off_plane={
            g: ("BARRE", tirant_section) for g in tirants if g not in edge_tirant_groups
        },
        exempt={} if omit.sans_poutre else {"POUTRE_COUR": POUTRE_EXEMPT_MOTIF},
        umbrella=dict.fromkeys(tirants, "TIRANTS"),
    )

    report = GenerationReport(
        comm_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        fiche_sha256=sha256_file(fiche_path),
        data_sha256=sha256_file(data_path),
        med_sha256=sha256_file(med_path),
        aster_version=aster_version,
        n_spring_classes=len(spring_classes),
        spring_sums_mn_per_m={
            band: sum(
                c.stiffness_mn_per_m * len(c.nodes)
                for c in spring_classes
                if c.band == band
            )
            for band in k_h
        },
        load_case_resultants_n={
            "Q3": (0.0, amarrage_fy, amarrage_fz),
            "A": (0.0, accostage_fy * defense_area, 0.0),
        },
    )
    return text, report


__all__ = [
    "DiagnosticOmissions",
    "EquilibriumProbe",
    "GenerationReport",
    "InitialPressureDiagnostic",
    "JunctionCandidate",
    "SolverDiagnostics",
    "POUTRE_EXEMPT_MOTIF",
    "generate_comm",
]
