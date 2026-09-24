"""Deterministic `.comm` text of the quay model (lot 28, Étape 3).

One function per block of the fiche; `aster_expert.generation.generate` calls
them in a fixed order and joins the result. No number is written here that
is not read from `ModelValues` (SI conversion documented at the point of
use) or computed by `aster_expert.meshing.combiwall`/`aster_expert.generation
.springs` from the model's own data -- never typed by hand.

Ordering constraint: the mesh (groups, the spring `POI1` cells created by
`CREA_POI1`, the shell normals) is entirely built and fixed *before* the
single `AFFE_MODELE`/`AFFE_CARA_ELEM` pair that assigns every element type at
once -- `AFFE_MODELE` cannot see a `POI1` cell `CREA_MAILLAGE` has not created
yet, and `AFFE_CARA_ELEM` is one call per model, never assembled piecemeal
from an earlier one's own keywords.
"""

from __future__ import annotations

from typing import Literal

from aster_expert.generation.errors import GenerationError
from aster_expert.generation.springs import SpringClass
from aster_expert.generation.values import ModelValues
from aster_expert.meshing.combiwall import Point3D

JunctionMethod = Literal["liaison_solide", "liaison_ddl_translations", "noeud_unique"]
"""Lot 31, étape 2 : méthode de jonction tête de tube / poutre de
couronnement. `liaison_solide` est la méthode de production (point 3,
inchangée) ; les deux autres sont des candidats de diagnostic, comparés sur
le quai réduit, jamais actifs par défaut (`generate.JunctionCandidate`)."""

ALL_NODES_GROUP = "GEN_TOUS_NOEUDS"
"""Lot 33, étape 4 : groupe de tous les nœuds structurels du maillage
(`DEFI_GROUP/CREA_GROUP_NO/GROUP_MA=("TUBES", "PALPS", "TIRANTS",
"POUTRE_COUR")`, U4.22.01 -- les quatre mailles affectées par `AFFE_MODELE`,
qui couvrent déjà tout nœud portant un DDL, ressorts compris, puisqu'un
ressort partage son nœud avec la coque), pour le contrôle de symétrie des
déplacements sur chaque nœud (`controls_block`'s own `TAB_SYM_<nom>`).
`POST_RELEVE_T/EXTRACTION` refuse `TOUT="OUI"` seul ("At least one argument
of ('GROUP_NO', 'NOEUD') must be defined", `checkCommandSyntax`, une règle
non visible du seul catalogue) ; `CREA_GROUP_NO/TOUT_GROUP_MA="OUI"` refuse
à son tour `NOM` (il nomme un groupe de nœuds par groupe de mailles
existant, jamais un seul groupe unifié, constaté par `checkCommandSyntax`)
-- d'où l'union explicite des quatre groupes de mailles plutôt que l'un ou
l'autre raccourci."""

REF_NORM_GROUP = "GEN_REF_NORM"
BEAM_NODE_PREFIX = "GEN_POUTRE_"
SYMG_ROT_GROUP = "GEN_SYMG_ROT"
SYMG_RING_GROUP = "GEN_SYMG_RING"
SYMD_ROT_GROUP = "GEN_SYMD_ROT"
SYMD_RING_GROUP = "GEN_SYMD_RING"
ENV_SPHERE_RADIUS = 1.0e-6
"""Metres: well under the mesh's own smallest node-to-node distance (a few
cm, `mesh check`'s `no_coincident_nodes`), so `ENV_SPHERE` selects exactly
one node, never zero or several."""
DRZ_STIFFNESS_COEF = 1.0e-3
"""Historical value of `AFFE_CARA_ELEM/COQUE/COEF_RIGI_DRZ` (point 3, lots
28-32): a DKT shell's own drilling (normal) rotation carries essentially no
physical stiffness, and `LIAISON_SOLIDE` tying a tube's head ring to its
beam node pivoted to a null factor on exactly that degree of freedom (`<F>
<FACTOR_11>`, an actual execution, never visible at level A/B) when left at
the catalogue's own default of 1e-5. That pivot's real cause, established at
lot 31 (R3.03.02/R3.07.03/R3.03.01: `LIAISON_SOLIDE` dualising a rotation a
DKT shell gives almost no stiffness) and fixed at lot 32 by removing the
boundary-condition redundancy that made it exact rather than merely
ill-conditioned, no longer needs this raise: **lot 33, étape 1** found the
model solves at the plain catalogue default on the reduced quay (isolated
test, `docs/essais_lot33.md`), so production no longer passes this value
(`model_and_cara_block`'s own `coef_rigi_drz` defaults to `None`, omitting
the keyword). Kept only so
`aster_expert.generation.generate.SolverDiagnostics` can still reproduce the
lots 28-32 behaviour on request."""

DRZ_STIFFNESS_COEF_CATALOGUE_DEFAULT = 1.0e-5
"""`AFFE_CARA_ELEM/COQUE/COEF_RIGI_DRZ`'s own catalogue default (level A,
`get_command_schema("AFFE_CARA_ELEM", keyword="COQUE.COEF_RIGI_DRZ")`,
confirmed lot 33, étape 1) -- the value `DRZ_STIFFNESS_COEF` was raised from,
and the value production now gets implicitly by omitting the keyword
entirely. Kept only for `aster_expert.generation.generate.SolverDiagnostics`
to pass explicitly when reproducing that omission is useful (e.g. a
regression test comparing byte-for-byte to the implicit form)."""


def _fmt(x: float) -> str:
    """A float, written so Python reparses it to the identical bit pattern
    (determinism: the same input always yields the same bytes)."""
    return repr(float(x))


def _pt(p: tuple[float, float, float]) -> str:
    return f"({_fmt(p[0])}, {_fmt(p[1])}, {_fmt(p[2])})"


def _tup(names: list[str]) -> str:
    return "(" + ", ".join(f'"{n}"' for n in names) + ",)"


MAX_GROUP_NAME_LEN = 24
"""Code_Aster truncates a node/mesh group `NOM` beyond this length silently
(no warning at creation, only a fatal `<F> <SOUSTRUC_37>` "existe déjà" the
first time two truncated names collide) -- not visible from the catalogue,
where `NOM` is a plain `TXM` with no declared length (`get_command_schema`,
`DEFI_GROUP.CREA_GROUP_NO.NOM`); found only by an actual execution (level C)
that hit exactly this with `GEN_BNDPART_RESS_AV_ARGI_BAS`/`_HAUT` (28/29
characters, both truncating to the identical `GEN_BNDPART_RESS_AV_ARGI`)."""


def _gn(name: str) -> str:
    """Every group name this module *creates* (never a reference to a name
    the mesh already carries) passes through here: refuses at generation
    time, rather than by a Code_Aster crash, the moment a name would be
    silently truncated."""
    if len(name) > MAX_GROUP_NAME_LEN:
        message = (
            f"nom de groupe trop long ({len(name)} > {MAX_GROUP_NAME_LEN} "
            f"caractères, tronqué en silence par Code_Aster) : {name}"
        )
        raise GenerationError(message)
    return name


def _env_sphere(name: str, point: tuple[float, float, float]) -> str:
    return (
        f'_F(NOM="{_gn(name)}", OPTION="ENV_SPHERE", POINT={_pt(point)}, '
        f"RAYON={_fmt(ENV_SPHERE_RADIUS)}, PRECISION={_fmt(ENV_SPHERE_RADIUS)}),"
    )


def header(
    *, aster_version: str, fiche_sha256: str, data_sha256: str, med_sha256: str
) -> str:
    return f"""\
# Généré par aster-expert generate (lot 28) -- NE PAS ÉDITER À LA MAIN.
# Toute modification doit passer par la fiche, le fichier de données ou le
# maillage vérifié, puis une nouvelle génération.
#
# Code_Aster ciblé : {aster_version}
# Fiche             : sha256:{fiche_sha256}
# Données           : sha256:{data_sha256}
# Maillage vérifié  : sha256:{med_sha256}

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"), DEBUG=_F(SDVERI="OUI"))

# Point 9 (repère global) : X le long du quai de SYM_G vers SYM_D, Y vers la
# terre, Z ascendant, unités m, N, Pa, kg -- imposé par le maillage, non
# recréé ici.
MAIL = LIRE_MAILLAGE(FORMAT="MED", UNITE=20, INFO=2)
"""


def spring_group_plan(
    spring_classes: list[SpringClass], bands: dict[str, tuple[float, float]]
) -> tuple[list[str], list[str]]:
    """Two DEFI_GROUP occurrence lists (CREA_GROUP_NO bodies, GROUP_NO=... for
    a following DEFI_GROUP with UNION) building every spring class's node
    group WITHOUT one `ENV_SPHERE` per node (~10 600 of them, an 11 000-line
    `.comm` that broke even static analysis): a class's nodes are almost
    always a handful of (X, Y) *columns*, each spanning many Z levels --
    `ENV_CYLINDRE` (cas test officiel zzzz106a.comm, trouvé via V1.01.106,
    combinaison absente de search_test_cases pour cette recherche mais lue
    directement) selects a whole column in one occurrence, `PLAN` (même cas
    test) the band's own top/bottom row in one occurrence each, and
    `INTERSEC`/`UNION`/`DIFFE` (37 cas tests officiels) combine them.

    A class whose nodes mix the band's boundary row (Z = cote_bas or
    cote_haut) with an interior row (never observed to affect more than a
    couple of classes here) cannot be split by the interior/boundary
    reference groups this way -- it falls back to one `ENV_SPHERE` per node,
    exactly as before, only for that class.

    Node-group names are capped at 24 characters: Code_Aster truncates a
    longer `NOM` silently (no warning at creation) and only reports it later
    as `<F> <SOUSTRUC_37>` "le groupe ... existe déjà" the first time two
    truncated names collide -- a real `.comm`'s execution hit exactly this
    with the full band name spelled out in every intermediate group (`GEN_
    BNDPART_RESS_AV_ARGI_BAS`/`_HAUT`, 28/29 characters, both truncating to
    the same 24-character `GEN_BNDPART_RESS_AV_ARGI`); the catalogue schema
    itself declares `NOM` as a plain `TXM` with no length, so this limit is
    not visible at level A/B, only from an actual run (level C). Every name
    here therefore uses the band's short suffix (`band.removeprefix(
    "RESS_AV_")`, already how a spring class's own group name is built) in
    place of the full band name.

    Returns (prep_occurrences, class_union_occurrences): `prep_occurrences` go
    into the first `DEFI_GROUP` (bands' ALL/PLAN/INTERIOR/BOUNDARY references,
    every column's cylinder, every column x row-type intersection, and any
    per-node fallback); `class_union_occurrences` go into a second
    `DEFI_GROUP`, one `UNION` (or a straight rename via `GROUP_NO`) per
    spring class, run after the first so every piece it unions already
    exists.
    """
    prep: list[str] = []
    unions: list[str] = []
    for band, (cote_bas, cote_haut) in bands.items():
        short = band.removeprefix("RESS_AV_")
        all_name = _gn(f"GEN_ALL_{short}")
        prep.append(f'_F(NOM="{all_name}", GROUP_MA=("{band}",)),')
        interior_name = _gn(f"GEN_INT_{short}")
        boundary_name = _gn(f"GEN_BND_{short}")
        bnd_part_bas = _gn(f"GEN_BNDPART_{short}_BAS")
        bnd_part_haut = _gn(f"GEN_BNDPART_{short}_HAUT")
        for suffix, z, bnd_part in (
            ("BAS", cote_bas, bnd_part_bas),
            ("HAUT", cote_haut, bnd_part_haut),
        ):
            plan_name = _gn(f"GEN_PLAN_{short}_{suffix}")
            prep.append(
                f'_F(NOM="{plan_name}", OPTION="PLAN", POINT=(0.0, 0.0, {_fmt(z)}), '
                f"VECT_NORMALE=(0.0, 0.0, 1.0), PRECISION={_fmt(ENV_SPHERE_RADIUS)}),"
            )
            prep.append(
                f'_F(NOM="{bnd_part}", INTERSEC=("{all_name}", "{plan_name}")),'
            )
        prep.append(
            f'_F(NOM="{boundary_name}", UNION=("{bnd_part_bas}", "{bnd_part_haut}")),'
        )
        prep.append(
            f'_F(NOM="{interior_name}", DIFFE=("{all_name}", "{boundary_name}")),'
        )

        for ci, c in enumerate((c for c in spring_classes if c.band == band), start=1):
            zs = {round(p[2], 6) for p in c.nodes}
            boundary_zs = {round(cote_bas, 6), round(cote_haut, 6)}
            if zs <= boundary_zs:
                reference = boundary_name
            elif zs.isdisjoint(boundary_zs):
                reference = interior_name
            else:
                # Mixed class: fall back to one ENV_SPHERE per node. Each
                # occurrence needs its OWN name -- a second `_F(NOM=...)`
                # sharing a name an earlier occurrence already created is the
                # exact same fatal "existe déjà" this function's docstring
                # warns about, never a way to accumulate nodes into one
                # group -- so every node gets a distinct temporary name, and
                # they are UNIONed under `c.group_name` afterwards, exactly
                # like the multi-column case below.
                mixed_names = [
                    _gn(f"GEN_MIX_{short}_{ci:02d}_{ni:03d}")
                    for ni in range(1, len(c.nodes) + 1)
                ]
                for name, p in zip(mixed_names, c.nodes, strict=True):
                    prep.append(_env_sphere(name, p))
                quoted = ", ".join(f'"{n}"' for n in mixed_names)
                unions.append(f'_F(NOM="{_gn(c.group_name)}", UNION=({quoted},)),')
                continue

            columns = sorted({(round(p[0], 6), round(p[1], 6)) for p in c.nodes})
            part_names = []
            for cj, (x, y) in enumerate(columns, start=1):
                col_name = _gn(f"GEN_COL_{short}_{ci:02d}_{cj:03d}")
                part_name = _gn(f"GEN_PART_{short}_{ci:02d}_{cj:03d}")
                radius = _fmt(ENV_SPHERE_RADIUS)
                prep.append(
                    f'_F(NOM="{col_name}", OPTION="ENV_CYLINDRE", '
                    f"POINT=({_fmt(x)}, {_fmt(y)}, 0.0), VECT_NORMALE=(0.0, 0.0, 1.0), "
                    f"RAYON={radius}, PRECISION={radius}),"
                )
                prep.append(
                    f'_F(NOM="{part_name}", INTERSEC=("{col_name}", "{reference}")),'
                )
                part_names.append(part_name)
            if len(part_names) == 1:
                unions.append(
                    f'_F(NOM="{_gn(c.group_name)}", GROUP_NO=("{part_names[0]}",)),'
                )
            else:
                quoted = ", ".join(f'"{n}"' for n in part_names)
                unions.append(f'_F(NOM="{_gn(c.group_name)}", UNION=({quoted},)),')
    return prep, unions


def _sym_split(sym_group: str, ring_group: str, rot_name: str, ring_name: str) -> str:
    """Splits a symmetry-plane node group into its `LIAISON_SOLIDE`-tied ring
    nodes and the rest -- see `symmetry_and_support_block`'s docstring for
    why the two need different `DDL_IMPO`."""
    return (
        f'_F(NOM="{_gn(ring_name)}", INTERSEC=("{sym_group}", "{ring_group}")),\n'
        f'        _F(NOM="{_gn(rot_name)}", DIFFE=("{sym_group}", "{ring_group}")),'
    )


def mesh_prep_block(
    *,
    beam_points: dict[str, tuple[float, float, float]],
    normal_ref_point: tuple[float, float, float],
    spring_classes: list[SpringClass],
    spring_bands: dict[str, tuple[float, float]],
    edge_tube_low: str,
    edge_tube_high: str,
    junction_method: JunctionMethod = "liaison_solide",
    ring_points: dict[str, tuple[Point3D, ...]] | None = None,
) -> str:
    """Every group the generator itself creates (reserved `GEN_` prefix,
    CLAUDE.md -- never part of the mesh's own naming convention), the spring
    `POI1` cells (`CREA_POI1`, one occurrence per stiffness class, lot 22
    essai C), the shell-normal orientation (point 5), and the symmetry-plane
    split of point 7 (see `symmetry_and_support_block`), all before any model
    is defined on this mesh. `edge_tube_low`/`edge_tube_high` are the tube
    numbers (as `beam_points`' own keys) whose head ring sits on `SYM_G`/
    `SYM_D` respectively (point 9: X runs from `SYM_G` to `SYM_D`, so these
    are always the lowest and highest tube numbers).

    Lot 31, étape 2 : `junction_method`/`ring_points` add the per-ring-node
    selectors candidates C1/C4 need (`junction_ring_groups_block`); the
    default (`liaison_solide`) adds nothing, reproducing the production text
    exactly."""
    junction_groups = junction_ring_groups_block(junction_method, ring_points or {})
    beam_groups = "\n        ".join(_env_sphere(n, p) for n, p in beam_points.items())
    prep, unions = spring_group_plan(spring_classes, spring_bands)
    sym_splits = (
        _sym_split(
            "SYM_G",
            f"TETE_TUBE_{edge_tube_low}",
            SYMG_ROT_GROUP,
            SYMG_RING_GROUP,
        )
        + "\n        "
        + _sym_split(
            "SYM_D",
            f"TETE_TUBE_{edge_tube_high}",
            SYMD_ROT_GROUP,
            SYMD_RING_GROUP,
        )
    )
    prep_body = "\n        ".join(
        [*prep, sym_splits, *([junction_groups] if junction_groups else [])]
    )
    union_body = "\n        ".join(unions)
    poi1 = "\n        ".join(
        f'_F(NOM_GROUP_MA="{_gn(c.group_name)}", GROUP_NO=("{c.group_name}",)),'
        for c in spring_classes
    )
    # Lot 30, étape 3 (diagnostic « sans les ressorts ») : `CREA_GROUP_NO`
    # (réunion des classes) et `CREA_POI1` ont chacun un minimum d'une
    # occurrence -- avec `spring_classes` vide, les deux commandes sont
    # omises plutôt que d'écrire une occurrence factice ; MAIL reste alors
    # celui du premier DEFI_GROUP.
    union_block = (
        f"""
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=(
        {union_body}
    ),
)
"""
        if unions
        else ""
    )
    creation_poi1 = (
        f"""
# Point 4 : une maille POI1 par nœud de ressort, regroupée par classe de
# raideur (une occurrence de CREA_POI1 par classe, jamais par nœud).
MAIL = CREA_MAILLAGE(
    MAILLAGE=MAIL,
    CREA_POI1=(
        {poi1}
    ),
)
"""
        if spring_classes
        else ""
    )
    return f"""
# Groupes créés par le générateur (préfixe réservé GEN_, hors convention de
# maillage) : un nœud de poutre par tube (point 3), le nœud de référence de
# ORIE_NORM_COQUE (point 5). Point 4 : chaque classe de raideur est bâtie par
# colonne (X, Y) -- ENV_CYLINDRE, une occurrence par colonne, jamais par
# nœud -- croisée avec la ligne haute ou basse de sa bande (PLAN) ou son
# complément (INTERIEUR = TOUT - HAUT - BAS), puis réunie (UNION) : voir
# spring_group_plan pour la justification et les sources.
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=(
        {beam_groups}
        {_env_sphere(REF_NORM_GROUP, normal_ref_point)}
        {prep_body}
    ),
)

{union_block}
{creation_poi1}
# Lot 33, étape 4 : GEN_TOUS_NOEUDS, en deux passes -- un groupe par nom de
# maille (comme les classes de ressort, spring_group_plan) puis leur UNION,
# jamais un seul CREA_GROUP_NO(GROUP_MA=(quatre noms,)) : cette dernière
# forme fait échouer une commande plus loin (<F> <JEVEUX_10>, "Le nom
# demandé existe déjà dans la base &&SSCGNO.LITMP2" -- une collision de nom
# interne à Code_Aster, jamais visible du catalogue ; une exécution réelle,
# non expliquée par les sept outils MCP, comme la numérotation interne de
# LIAISON_SOLIDE aux lots 28/30/31).
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=(
        _F(NOM="GEN_TOUS_TUBES", GROUP_MA=("TUBES",)),
        _F(NOM="GEN_TOUS_PALPS", GROUP_MA=("PALPS",)),
        _F(NOM="GEN_TOUS_TIRANTS", GROUP_MA=("TIRANTS",)),
        _F(NOM="GEN_TOUS_POUTRE", GROUP_MA=("POUTRE_COUR",)),
    ),
)
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=_F(
        NOM="{ALL_NODES_GROUP}",
        UNION=(
            "GEN_TOUS_TUBES",
            "GEN_TOUS_PALPS",
            "GEN_TOUS_TIRANTS",
            "GEN_TOUS_POUTRE",
        ),
    ),
)

# Point 5 : normales de coque cohérentes sur ECRAN_POUSSEE, orientées côté
# terre (MODI_MAILLAGE/ORIE_NORM_COQUE, U4.23.04 ; cas test sdls118a.comm) --
# une pression FORCE_COQUE/PRES positive (U4.44.01 : positive "suivant le
# sens contraire de la normale") pousse alors vers le bassin.
MAIL = MODI_MAILLAGE(
    reuse=MAIL,
    MAILLAGE=MAIL,
    ORIE_NORM_COQUE=_F(
        GROUP_MA=("ECRAN_POUSSEE",),
        VECT_NORM=(0.0, 1.0, 0.0),
        GROUP_NO="{REF_NORM_GROUP}",
    ),
)
"""


def _palp_coque_keyword(
    sans_palplanches: bool,
    epais_palp: float,
    vecteur_l: tuple[float, ...],
    *,
    coef_rigi_drz: float | None,
) -> str:
    if sans_palplanches:
        return ""
    vecteur = f"({_fmt(vecteur_l[0])}, {_fmt(vecteur_l[1])}, {_fmt(vecteur_l[2])})"
    drz = (
        f"\n            COEF_RIGI_DRZ={_fmt(coef_rigi_drz)},"
        if coef_rigi_drz is not None
        else ""
    )
    return (
        '_F(\n            GROUP_MA=("PALPS",),\n            '
        f"EPAIS={_fmt(epais_palp)},\n            "
        f"VECTEUR={vecteur},{drz}\n        ),"
    )


def _barre_keyword(sans_tirants: bool, section_tirant: float) -> str:
    if sans_tirants:
        return ""
    return (
        f'BARRE=_F(\n        GROUP_MA=("TIRANTS",), SECTION="GENERALE", CARA="A", '
        f"VALE={_fmt(section_tirant)}\n    ),"
    )


def model_and_cara_block(
    mv: ModelValues,
    spring_classes: list[SpringClass],
    *,
    sans_tirants: bool = False,
    sans_palplanches: bool = False,
    sans_poutre: bool = False,
    coef_rigi_drz: float | None = None,
) -> str:
    """One `AFFE_MODELE` and one `AFFE_CARA_ELEM`, every element type at once
    (points 1, 2, 3, 4): DKT on the shells, BARRE on the tie rods (no
    rotation dof, point 2), POU_D_E on the crown beam, DIS_T on every spring
    group (point 4).

    Lot 30, étape 3 (diagnostic « sans les tirants ») : `sans_tirants`
    omits the `BARRE` model and characteristics entirely -- `TIRANTS` has a
    minimum of one occurrence too, so it is dropped rather than left empty.
    `sans_palplanches` (retrait 3) similarly omits `PALPS` from the DKT
    `AFFE` and its own `COQUE` occurrence -- `TUBES` alone still satisfies
    `AFFE`'s own minimum. `sans_poutre` (retrait 4) omits `POUTRE_COUR`'s
    `POU_D_E` model and its `POUTRE` characteristics -- `CH_SOLIDE` does not
    exist either in this variant (`liaison_solide_block`, `case_block`).

    Lot 33, étape 1 (diagnostic « paramètres hérités ») : `coef_rigi_drz`
    lets `aster_expert.generation.generate.SolverDiagnostics` add an explicit
    `COEF_RIGI_DRZ` on both DKT groups at once (`TUBES`/`PALPS`) -- isolated
    testing on the reduced quay (`docs/essais_lot33.md`) found the model
    solves at the bare catalogue default (`DRZ_STIFFNESS_COEF_CATALOGUE_
    DEFAULT`), so production now leaves `coef_rigi_drz` at its default
    (`None`), omitting the keyword entirely rather than writing that default
    value out."""
    epais_tube = mv.si("tube.epaisseur_coque_retenue")
    epais_palp = mv.si("palplanche.epaisseur_coque_EPAIS")
    vecteur_l = mv.si_vector("palplanche.vecteur_axe_L")
    section_tirant = mv.si("tirants.section_brute")
    largeur_poutre = mv.si("poutre_couronnement.largeur")
    hauteur_poutre = mv.si("poutre_couronnement.hauteur")
    spring_names = [c.group_name for c in spring_classes]
    # K_T_D_N gives (kx, ky, kz) in the GLOBAL frame by default (REPERE not
    # given -- U4.42.01, confirmed by the fiche's own point 4 finding): the
    # ressort is horizontal, resisting the poussee's own Y direction, so the
    # stiffness sits in the SECOND component, never the first (X, along the
    # quay, which the ressort has no reason to resist).
    # Lot 31, étape 3 : un DIS_T sous PESANTEUR sans masse propre affectée
    # arrête l'exécution (`<F> <DISCRETS_26>`, "Vous utilisez la matrice de
    # MASSE ... alors que vous n'avez pas affecté les caractéristiques de
    # masses. Par défaut la masse est nulle.", U4.42.01 mot-clé DISCRET,
    # CARA="M_T_D_N" : 1 terme, la masse). Un ressort est un appui, pas de la
    # matière : la masse affectée est explicitement nulle, jamais omise.
    discret = "\n        ".join(
        f'_F(GROUP_MA=("{c.group_name}",), CARA="K_T_D_N", '
        f"VALE=(0.0, {_fmt(c.stiffness_n_per_m)}, 0.0)),\n        "
        f'_F(GROUP_MA=("{c.group_name}",), CARA="M_T_D_N", VALE=(0.0,)),'
        for c in spring_classes
    )
    # Lot 30, étape 3 (diagnostic « sans les ressorts ») : `AFFE`/`DISCRET`
    # ont chacun un minimum d'une occurrence -- avec `spring_classes` vide,
    # l'affectation DIS_T et le mot-clé DISCRET sont omis plutôt que d'écrire
    # une occurrence factice.
    dis_t_affe = (
        f'\n        _F(GROUP_MA={_tup(spring_names)}, PHENOMENE="MECANIQUE", '
        'MODELISATION="DIS_T"),'
        if spring_classes
        else ""
    )
    discret_keyword = (
        f"""
    DISCRET=(
        {discret}
    ),"""
        if spring_classes
        else ""
    )
    tirant_affe = (
        ""
        if sans_tirants
        else (
            '\n        _F(GROUP_MA=("TIRANTS",), PHENOMENE="MECANIQUE", '
            'MODELISATION="BARRE"),'
        )
    )
    dkt_group_ma = '("TUBES",)' if sans_palplanches else '("TUBES", "PALPS")'
    poutre_affe = (
        ""
        if sans_poutre
        else (
            '\n        _F(GROUP_MA=("POUTRE_COUR",), PHENOMENE="MECANIQUE", '
            'MODELISATION="POU_D_E"),'
        )
    )
    dkt_affe = (
        f'_F(GROUP_MA={dkt_group_ma}, PHENOMENE="MECANIQUE", MODELISATION="DKT"),'
        f"{tirant_affe}{poutre_affe}{dis_t_affe}"
    )
    palp_coque = _palp_coque_keyword(
        sans_palplanches, epais_palp, vecteur_l, coef_rigi_drz=coef_rigi_drz
    )
    tube_drz = (
        f"\n            COEF_RIGI_DRZ={_fmt(coef_rigi_drz)},"
        if coef_rigi_drz is not None
        else ""
    )
    return f"""
MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        {dkt_affe}
    ),
)

# Point 1 : épaisseurs de coque (tube : décision point 10 ; palplanche :
# EPAIS = t x s/b, décision point 1). VECTEUR fixe l'axe L (vertical) de la
# palplanche, plaque du plan Y = 0 (XZ) -- établi par l'essai D7 (lot 25,
# point 1) : VECTEUR = (0, 0, 1) place L selon Z.
# Point 2 : section brute du tirant (aire donnée, SECTION="GENERALE").
# Point 3 : section rectangulaire de la poutre de couronnement (HY = largeur
# horizontale perpendiculaire à l'axe X de la poutre, HZ = hauteur verticale
# -- convention du repère local par défaut d'une poutre d'axe X).
# Point 4 : raideur K_T_D_N (0, ky, 0) par classe, repère global par défaut --
# ressorts horizontaux seuls, dirigés selon Y (décision 5), convertis de
# MN/m en N/m (x1e6). M_T_D_N = 0 par classe (lot 31, étape 3) : un ressort
# est un appui, pas de la matière -- masse explicitement nulle sous
# PESANTEUR, jamais omise (U4.42.01 DISCRET, <F> <DISCRETS_26> sinon).
# Point 3 : COEF_RIGI_DRZ omis (lot 33, étape 1 : inutile au défaut
# catalogue sur le quai réduit, testé isolément -- voir DRZ_STIFFNESS_COEF).
CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=(
        _F(
            GROUP_MA=("TUBES",),
            EPAIS={_fmt(epais_tube)},{tube_drz}
        ),
        {palp_coque}
    ),
    {_barre_keyword(sans_tirants, section_tirant)}
    {_poutre_keyword(sans_poutre, largeur_poutre, hauteur_poutre)}{discret_keyword}
)
"""


def _poutre_keyword(sans_poutre: bool, largeur: float, hauteur: float) -> str:
    if sans_poutre:
        return ""
    return (
        'POUTRE=_F(\n        GROUP_MA=("POUTRE_COUR",),\n        '
        'SECTION="RECTANGLE",\n        CARA=("HY", "HZ"),\n        '
        f"VALE=({_fmt(largeur)}, {_fmt(hauteur)}),\n    ),"
    )


def materials_block(
    mv: ModelValues,
    *,
    sans_tirants: bool = False,
    sans_palplanches: bool = False,
    sans_poutre: bool = False,
) -> str:
    """Lot 30, étape 3 (diagnostic « sans les tirants ») : `sans_tirants`
    omits `MAT_TIRANT` and its `AFFE_MATERIAU` occurrence entirely.
    `sans_palplanches` (retrait 3) omits `PALPS`' own `AFFE_MATERIAU`
    occurrence (`MAT_PALP` stays defined, simply unused -- an unused
    material concept is not an error). `sans_poutre` (retrait 4) similarly
    omits `POUTRE_COUR`'s own `AFFE_MATERIAU` occurrence (`MAT_BETON` stays
    defined, unused)."""
    tube_e = mv.si("tube.module_young")
    tube_nu = mv.si("tube.coefficient_poisson")
    tube_rho = mv.si("tube.masse_volumique")
    beton_e = mv.si("poutre_couronnement.module_young")
    beton_nu = mv.si("poutre_couronnement.coefficient_poisson")
    beton_rho = mv.si("poutre_couronnement.masse_volumique")
    tirant_e = mv.si("tirants.module_young")
    tirant_rho = mv.si("tirants.masse_volumique")
    # NU du tirant : absent des données (aucun coefficient de Poisson n'est
    # fourni pour l'acier du tirant, cas de test §4). Le catalogue exige E et
    # NU définis ensemble (DEFI_MATERIAU/ELAS, contrainte croisée trouvée par
    # validate_comm : "('E', 'NU') must be all defined or all undefined"),
    # bien qu'un élément BARRE, purement axial, n'utilise pas NU. Valeur de
    # l'acier du tube (S355, même famille de matériau) reprise ici à défaut
    # -- À CONFIRMER PAR MM, ou à fournir explicitement pour l'acier 500/700
    # du tirant.
    tirant_nu = tube_nu

    memb_l = mv.si("palplanche.MEMB_L")
    memb_t = mv.si("palplanche.MEMB_T")
    memb_g = mv.si("palplanche.MEMB_G_LT")
    memb_lt = mv.si("palplanche.MEMB_LT")
    flex_l = mv.si("palplanche.FLEX_L")
    flex_t = mv.si("palplanche.FLEX_T")
    flex_g = mv.si("palplanche.FLEX_G_LT")
    flex_lt = mv.si("palplanche.FLEX_LT")
    cisa_l = mv.si("palplanche.CISA_L")
    cisa_t = mv.si("palplanche.CISA_T")
    palp_rho = mv.si("palplanche.masse_volumique")

    return f"""
# Point 1 : matériau du tube (ELAS) et de la palplanche (décision 2 --
# ELAS_COQUE, rigidités homogénéisées converties de MN/m et MN.m2/m en N/m
# et N.m2/m : facteur 1e6). Point 2 : matériaux poutre (béton C35/45) et
# tirant (E, NU, RHO -- DEFI_MATERIAU/ELAS exige E et NU définis ensemble ou
# non définis du tout, même si une modélisation BARRE, purement axiale,
# n'utilise pas NU ; NU du tirant repris du tube faute de donnée propre, voir
# le commentaire sur MAT_TIRANT). Les ressorts (DIS_T) ne portent pas de
# matériau.
MAT_TUBE = DEFI_MATERIAU(
    ELAS=_F(E={_fmt(tube_e)}, NU={_fmt(tube_nu)}, RHO={_fmt(tube_rho)})
)

MAT_PALP = DEFI_MATERIAU(
    ELAS_COQUE=_F(
        MEMB_L={_fmt(memb_l)},
        MEMB_T={_fmt(memb_t)},
        MEMB_G_LT={_fmt(memb_g)},
        MEMB_LT={_fmt(memb_lt)},
        FLEX_L={_fmt(flex_l)},
        FLEX_T={_fmt(flex_t)},
        FLEX_G_LT={_fmt(flex_g)},
        FLEX_LT={_fmt(flex_lt)},
        CISA_L={_fmt(cisa_l)},
        CISA_T={_fmt(cisa_t)},
        RHO={_fmt(palp_rho)},
    )
)

MAT_BETON = DEFI_MATERIAU(
    ELAS=_F(E={_fmt(beton_e)}, NU={_fmt(beton_nu)}, RHO={_fmt(beton_rho)})
)

{_mat_tirant_def(sans_tirants, tirant_e, tirant_nu, tirant_rho)}
CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(
        {_chmat_affe(sans_tirants, sans_palplanches, sans_poutre)}
    ),
)
"""


def _chmat_affe(sans_tirants: bool, sans_palplanches: bool, sans_poutre: bool) -> str:
    return (
        '_F(GROUP_MA=("TUBES",), MATER=MAT_TUBE),'
        f"{_mat_palp_affe(sans_palplanches)}"
        f"{_mat_beton_affe(sans_poutre)}"
        f"{_mat_tirant_affe(sans_tirants)}"
    )


def _mat_palp_affe(sans_palplanches: bool) -> str:
    if sans_palplanches:
        return ""
    return '\n        _F(GROUP_MA=("PALPS",), MATER=MAT_PALP),'


def _mat_beton_affe(sans_poutre: bool) -> str:
    if sans_poutre:
        return ""
    return '\n        _F(GROUP_MA=("POUTRE_COUR",), MATER=MAT_BETON),'


def _mat_tirant_def(sans_tirants: bool, e: float, nu: float, rho: float) -> str:
    if sans_tirants:
        return ""
    return f"""MAT_TIRANT = DEFI_MATERIAU(
    ELAS=_F(E={_fmt(e)}, NU={_fmt(nu)}, RHO={_fmt(rho)})
)
"""


def _mat_tirant_affe(sans_tirants: bool) -> str:
    if sans_tirants:
        return ""
    return '\n        _F(GROUP_MA=("TIRANTS",), MATER=MAT_TIRANT),'


def liaison_solide_block(
    beam_group_names: list[str], *, sans_poutre: bool = False
) -> str:
    """Point 3 : one rigid-body junction per tube, ring of head nodes + beam
    node (`LIAISON_SOLIDE`, U4.44.01; cas test sdlx03b.comm).

    Lot 30, étape 3 (diagnostic « sans la poutre, donc sans liaison de corps
    solide ») : `sans_poutre` returns an empty string -- `CH_SOLIDE` does not
    exist in this variant, `case_block` omits it from `EXCIT` accordingly."""
    if sans_poutre:
        return ""
    occurrences = "\n        ".join(
        f'_F(GROUP_NO=("TETE_TUBE_{n}", "{BEAM_NODE_PREFIX}{n}")),'
        for n in beam_group_names
    )
    return f"""
# Point 3 : liaison de corps solide entre l'anneau de tête de chaque tube et
# le nœud de poutre à son droit (encastrement dans la poutre, cas de test
# §3, U4.44.01 mot-clé LIAISON_SOLIDE).
CH_SOLIDE = AFFE_CHAR_MECA(
    MODELE=MO,
    LIAISON_SOLIDE=(
        {occurrences}
    ),
)
"""


def _ring_node_group(prefix: str, tube: str, index: int) -> str:
    return _gn(f"{prefix}{tube}_{index:02d}")


def junction_ring_groups_block(
    method: JunctionMethod,
    ring_points: dict[str, tuple[Point3D, ...]],
) -> str:
    """Lot 31, étape 2 : sélecteurs de nœuds (`CREA_GROUP_NO`/`ENV_SPHERE`)
    que les candidats C1 (`liaison_ddl_translations`) et C4 (`noeud_unique`)
    doivent ajouter pour adresser un nœud d'anneau à la fois -- `liaison_solide`
    (méthode de production, point 3) n'en a besoin d'aucun, la commande
    travaillant directement sur le groupe `TETE_TUBE_<n>` entier."""
    if method == "liaison_solide":
        return ""
    if method == "noeud_unique":
        return "\n        ".join(
            _env_sphere(f"GEN_J4_{tube}", max(points, key=lambda p: p[1]))
            for tube, points in ring_points.items()
        )
    return "\n        ".join(
        _env_sphere(_ring_node_group("GEN_J1_", tube, i), p)
        for tube, points in ring_points.items()
        for i, p in enumerate(points)
    )


def junction_charge_block(
    method: JunctionMethod,
    beam_group_names: list[str],
    ring_points: dict[str, tuple[Point3D, ...]],
    beam_points: dict[str, Point3D],
) -> str:
    """Lot 31, étape 2 : le chargement `CH_SOLIDE` de jonction tête de tube /
    poutre de couronnement, sous la méthode retenue. Candidats de diagnostic
    comparés sur le quai réduit, jamais actifs par défaut -- `liaison_solide`
    reproduit exactement `liaison_solide_block` (méthode de production)."""
    if method == "liaison_solide":
        return liaison_solide_block(beam_group_names, sans_poutre=False)
    if method == "noeud_unique":
        occurrences = "\n        ".join(
            f'_F(GROUP_NO=("GEN_J4_{tube}", "{BEAM_NODE_PREFIX}{tube}")),'
            for tube in beam_group_names
        )
        return f"""
# Lot 31, étape 2, candidat C4 : un seul nœud d'anneau (le plus proche de la
# poutre -- celui de plus grand Y, génératrice terre) rigidement lié au nœud
# de poutre ; le reste de l'anneau n'est plus tenu par cette liaison
# (réponse à la remarque de MM sur un maillage coïncident, sans modifier le
# maillage : le nœud d'anneau existant le plus proche joue ce rôle).
CH_SOLIDE = AFFE_CHAR_MECA(
    MODELE=MO,
    LIAISON_SOLIDE=(
        {occurrences}
    ),
)
"""
    blocks: list[str] = []
    for tube in beam_group_names:
        xa, ya, za = beam_points[tube]
        beam = f"{BEAM_NODE_PREFIX}{tube}"
        for i, (xm, ym, zm) in enumerate(ring_points[tube]):
            dx, dy, dz = xm - xa, ym - ya, zm - za
            node = _ring_node_group("GEN_J1_", tube, i)
            blocks.append(
                f'_F(GROUP_NO=("{node}", "{beam}", "{beam}", "{beam}"), '
                f'DDL=("DX", "DX", "DRY", "DRZ"), '
                f"COEF_MULT=(1.0, -1.0, {_fmt(-dz)}, {_fmt(dy)}), COEF_IMPO=0.0),"
            )
            blocks.append(
                f'_F(GROUP_NO=("{node}", "{beam}", "{beam}", "{beam}"), '
                f'DDL=("DY", "DY", "DRZ", "DRX"), '
                f"COEF_MULT=(1.0, -1.0, {_fmt(-dx)}, {_fmt(dz)}), COEF_IMPO=0.0),"
            )
            blocks.append(
                f'_F(GROUP_NO=("{node}", "{beam}", "{beam}", "{beam}"), '
                f'DDL=("DZ", "DZ", "DRX", "DRY"), '
                f"COEF_MULT=(1.0, -1.0, {_fmt(-dy)}, {_fmt(dx)}), COEF_IMPO=0.0),"
            )
    body = "\n        ".join(blocks)
    return f"""
# Lot 31, étape 2, candidat C1 : translations de chaque nœud d'anneau liées à
# celles du nœud de poutre, bras de levier inclus (R3.03.02, cas 3DA, relations
# de translation seulement -- les relations de rotation DRX(M)=DRX(A), etc.,
# sont omises : la rotation de chaque nœud d'anneau reste libre). LIAISON_DDL
# (U4.44.01), jamais LIAISON_SOLIDE : un multiplicateur de Lagrange par
# relation (même dualisation que LIAISON_SOLIDE), mais la rotation DRZ de
# l'anneau (quasi singulière, voir DRZ_STIFFNESS_COEF) n'est jamais dualisée.
CH_SOLIDE = AFFE_CHAR_MECA(
    MODELE=MO,
    LIAISON_DDL=(
        {body}
    ),
)
"""


def check_symmetry_ddl_impo_no_ring_redundancy(
    text: str, *, split_ring_rotation: bool
) -> None:
    """Lot 32, étape 1 : contrôle du générateur, appelé avant écriture.

    Règle générale (lot 32) : dans un ensemble de nœuds liés par une relation
    cinématique (ici, `LIAISON_SOLIDE` entre un anneau de tête de tube et son
    nœud de poutre), un degré de liberté que la relation détermine ne doit
    être imposé directement que sur un seul nœud de l'ensemble -- le nœud de
    poutre -- jamais sur les autres. Le nœud de poutre d'un tube de bord et
    les deux nœuds d'anneau qui touchent le plan de coupe (voir le
    commentaire de `symmetry_and_support_block`) forment un tel ensemble ; la
    relation détermine leurs six degrés de liberté, translations et
    rotations -- pas seulement DRY/DRZ, comme la correction du lot 31 le
    supposait à tort (insuffisante, lots 29 à 31).

    Contrôle textuel, volontairement étroit : quand `split_ring_rotation` est
    vrai (jonction LIAISON_SOLIDE), aucune ligne `DDL_IMPO` ne doit porter à
    la fois `GROUP_NO=("SYM_G",)` ou `GROUP_NO=("SYM_D",)` (le plan brut,
    anneau compris) et l'un des degrés DX, DRY, DRZ -- seuls les groupes
    `GEN_SYMG_ROT`/`GEN_SYMD_ROT` (anneau exclu par construction, voir
    `mesh_prep_block`/`_sym_split`) en ont le droit."""
    if not split_ring_rotation:
        return
    blocked = ("DX=0.0", "DRY=0.0", "DRZ=0.0")
    for raw_group in ('GROUP_NO=("SYM_G",)', 'GROUP_NO=("SYM_D",)'):
        for line in text.splitlines():
            if raw_group in line and any(dof in line for dof in blocked):
                message = (
                    "contrôle lot 32 (redondance CL / LIAISON_SOLIDE) : "
                    f"{raw_group} porte directement un degré de liberté que "
                    "LIAISON_SOLIDE détermine déjà pour les nœuds d'anneau du "
                    f"plan de coupe -- ligne : {line.strip()!r}"
                )
                raise GenerationError(message)


def symmetry_and_support_block(
    *, sans_tirants: bool = False, split_ring_rotation: bool = True
) -> str:
    """Point 7 (symmetry, X = constant planes), point 11 (`PIED_TUBES`,
    decision 12: vertical displacement blocked only), and point 2 (tie-rod
    anchor: "extrémité arrière bloquée", `tirants.longueur_modelisee`'s own
    comment in the data file -- the far end of the modelled rod length is
    fixed, not left free).

    An edge tube's head ring (`TETE_TUBE_01`/`TETE_TUBE_09`) sits partly on
    its own symmetry plane (two of its own nodes, at the vertical diameter,
    have X exactly equal to the plane): `LIAISON_SOLIDE` (point 3) already
    derives every ring node's full rigid-body motion (translations AND
    rotations) from the SAME beam node's own six dof, which the symmetry
    condition pins directly (DX = DRY = DRZ = 0) -- imposing any of the three
    a second time, directly on those two ring nodes, is then the identical
    equation again, not a new one (lot 32: not only DRY/DRZ, as lot 31 had
    assumed -- DX is derived exactly the same way, since both the beam node
    and the ring nodes sit on the plane, so the lever-arm's own X component
    is zero and the rigid-body relation reduces DX_ring to DX_beam). An
    actual execution hit exactly this (`<F> <FACTOR_11>`, a null pivot on the
    Lagrange multiplier of the resulting linearly dependent relation), never
    visible at level A/B. All three (DX, DRY, DRZ) are therefore withheld on
    the ring's own share of the plane (`GEN_SYMG_RING`/`GEN_SYMD_RING`,
    `mesh_prep_block`) and imposed only on the rest of the plane (beam node
    included -- `GEN_SYMG_ROT`/`GEN_SYMD_ROT`), checked by
    `check_symmetry_ddl_impo_no_ring_redundancy` before this function
    returns.

    Lot 31, étape 2 : `split_ring_rotation=False` (junction candidates C1/C4,
    `generate.JunctionCandidate`) imposes DX/DRY/DRZ on the *entire* symmetry
    plane, ring included -- neither candidate ties a ring node's own dof to
    the beam node's the same rigid way `LIAISON_SOLIDE` does, so the split
    that avoids the redundant pivot above is neither needed nor correct there
    (untouched by lot 32, whose rule concerns `LIAISON_SOLIDE` only)."""
    if split_ring_rotation:
        sym_g = f'_F(GROUP_NO=("{SYMG_ROT_GROUP}",), DX=0.0, DRY=0.0, DRZ=0.0),'
        sym_d = f'_F(GROUP_NO=("{SYMD_ROT_GROUP}",), DX=0.0, DRY=0.0, DRZ=0.0),'
    else:
        sym_g = '_F(GROUP_NO=("SYM_G",), DX=0.0, DRY=0.0, DRZ=0.0),'
        sym_d = '_F(GROUP_NO=("SYM_D",), DX=0.0, DRY=0.0, DRZ=0.0),'
    text = f"""
# Point 7 : symétrie par rapport aux plans X = constante (SYM_G, SYM_D) --
# translation normale au plan (DX) et rotations autour des deux axes du plan
# (DRY, DRZ) sur sa part hors anneau de tête seulement quand la jonction est
# LIAISON_SOLIDE (voir le commentaire de symmetry_and_support_block : la part
# de l'anneau tient alors ses six degrés de liberté de LIAISON_SOLIDE, les
# imposer une seconde fois y a produit un pivot nul -- lot 32, généralisé aux
# translations après le lot 31 qui n'excluait que les rotations), sur le plan
# entier sinon (candidats C1/C4, lot 31) ; DY, DZ, DRX libres (U4.44.01,
# tableau 5-2 : degrés de liberté dans le repère global ; cas test
# ssls100b.comm, bords de symétrie).
# Point 11 (décision 12) : appui vertical seul au pied des tubes.
# Point 2 : extrémité arrière du tirant bloquée (ANCRAGES) -- donnée du
# modèle (tirants.longueur_modelisee : "extrémité arrière bloquée"),
# BARRE n'ayant pas de degré de rotation à bloquer.{_ancrages_comment(sans_tirants)}
CH_BLOC = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        {sym_g}
        {sym_d}
        _F(GROUP_NO=("PIED_TUBES",), DZ=0.0),
        {_ancrages_ddl_impo(sans_tirants)}
    ),
)
"""
    check_symmetry_ddl_impo_no_ring_redundancy(
        text, split_ring_rotation=split_ring_rotation
    )
    return text


def _ancrages_comment(sans_tirants: bool) -> str:
    if not sans_tirants:
        return ""
    return (
        "\n# Lot 30, étape 3 (diagnostic « sans les tirants ») : ANCRAGES "
        "n'est plus bloqué, les tirants n'étant plus dans le modèle."
    )


def _ancrages_ddl_impo(sans_tirants: bool) -> str:
    if sans_tirants:
        return ""
    return '_F(GROUP_NO=("ANCRAGES",), DX=0.0, DY=0.0, DZ=0.0),'


def formule_block(name: str, points: list[tuple[float, float]]) -> str:
    """A `DEFI_FONCTION(NOM_PARA='Z', ...)` of pressure (Pa) against level
    (m), for `FORCE_COQUE`/`PRES` (point 5). `PROL_DROITE`/`PROL_GAUCHE` =
    "CONSTANT": the model is not asked to load anything above/below the
    profile's own range."""
    abscisse = ", ".join(_fmt(z) for z, _ in points)
    ordonnee = ", ".join(_fmt(p) for _, p in points)
    return f"""
{name} = DEFI_FONCTION(
    NOM_PARA="Z",
    ABSCISSE=({abscisse}),
    ORDONNEE=({ordonnee}),
    INTERPOL="LIN",
    PROL_DROITE="CONSTANT",
    PROL_GAUCHE="CONSTANT",
)
"""


ECRAN_POUSSEE_TUBES_GROUP = "GEN_ECRAN_POUSSEE_TUBES"
"""Lot 30, étape 3 (diagnostic « sans les palplanches ») : `ECRAN_POUSSEE`
mêle tubes et palplanches -- sans modèle sur `PALPS`, `FORCE_COQUE` n'y est
plus applicable (une coque non affectée). Ce groupe (`DIFFE`, créé seulement
dans ce diagnostic) porte les mêmes tubes, sans les panneaux de palplanche."""


def ecran_poussee_tubes_group_block() -> str:
    """Lot 30, étape 3 (diagnostic « sans les palplanches »): `GEN_
    ECRAN_POUSSEE_TUBES = ECRAN_POUSSEE \\ PALPS`, une maille de coque
    (`CREA_GROUP_MA`/`DIFFE`), pour porter `FORCE_COQUE` (point 5) sans
    toucher un panneau de palplanche que le modèle n'affecte plus."""
    return f"""
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_MA=_F(
        NOM="{ECRAN_POUSSEE_TUBES_GROUP}", DIFFE=("ECRAN_POUSSEE", "PALPS")
    ),
)
"""


def pressure_load_block(
    concept: str,
    formule_name: str,
    *,
    group_ma: str = "ECRAN_POUSSEE",
    veri_norm: bool = True,
) -> str:
    """`veri_norm=False` (lot 30, étape 3, diagnostic « sans les palplanches »
    only): `GEN_ECRAN_POUSSEE_TUBES` is the tubes' facets alone, no longer
    connected to each other once the palplanche panels that bridged them are
    gone -- `FORCE_COQUE`'s own automatic normal-orientation check
    (`VERI_NORM`, catalogue default `'OUI'`) refuses a disconnected boundary
    group (`<F> <MESH3_99>`, an actual execution): the check itself is
    disabled, exactly as its own message suggests, never a normal
    orientation this diagnostic needs to get right."""
    veri = "" if veri_norm else ' VERI_NORM="NON",'
    return f"""
{concept} = AFFE_CHAR_MECA_F(
    MODELE=MO,{veri} FORCE_COQUE=_F(GROUP_MA=("{group_ma}",), PRES={formule_name})
)
"""


def pesanteur_block(
    concept: str,
    g: float,
    *,
    sans_tirants: bool = False,
    sans_palplanches: bool = False,
) -> str:
    """Point 8 : pesanteur (cas G), tube/tirant/palplanche (RHO -- lot 22 :
    exigé sur tout élément ELAS_COQUE du modèle sous PESANTEUR).

    Lot 33, étape 3 : `POUTRE_COUR` n'est jamais dans `GROUP_MA` -- son propre
    poids est porté par une force nodale, au même titre que la charge de la
    décision 13 (`poutre_pressure_nodal_block`'s own `fz`, par nœud), jamais
    par `PESANTEUR`. `sans_tirants`/`sans_palplanches` (lot 30, étape 3)
    dropent `TIRANTS`/`PALPS` de `GROUP_MA` exactement comme `model_and_
    cara_block`'s own `AFFE_MODELE` drop leur propre affectation -- un
    `GROUP_MA` désignant un groupe qu'`AFFE_MODELE` n'a jamais affecté est
    refusé à l'exécution."""
    groups = [
        "TUBES",
        *(() if sans_palplanches else ("PALPS",)),
        *(() if sans_tirants else ("TIRANTS",)),
    ]
    group_ma = _tup(groups)
    return f"""
{concept} = AFFE_CHAR_MECA(
    MODELE=MO,
    PESANTEUR=_F(GRAVITE={_fmt(g)}, DIRECTION=(0.0, 0.0, -1.0), GROUP_MA={group_ma}),
)
"""


def bollard_force_block(concept: str, *, fy: float, fz: float, mx: float) -> str:
    return f"""
# Point 8 (cas Q3) : force et moment de transport sur BOLLARD (U4.44.01,
# FORCE_NODALE, repère global). FY : composante horizontale (donnée, non
# recalculée), vers le bassin (-Y). FZ : composante verticale, déduite de
# l'intensité et de l'inclinaison (amarrage_effort x sin(inclinaison)),
# calcul commenté ici, non typé en dur. MX : moment de transport (donné, non
# recalculé), d'axe parallèle au quai.
{concept} = AFFE_CHAR_MECA(
    MODELE=MO,
    FORCE_NODALE=_F(GROUP_NO=("BOLLARD",), FY={_fmt(fy)}, FZ={_fmt(fz)}, MX={_fmt(mx)}),
)
"""


def defense_force_block(concept: str, *, fy: float) -> str:
    """FY is a plain constant (no Z or position dependency): `AFFE_CHAR_MECA`
    (not the `_F` function variant -- confirmed by `validate_comm`,
    `AFFE_CHAR_MECA_F`'s `FORCE_COQUE` components accept only
    `fonction_sdaster`/`nappe_sdaster`/`formule`, never a bare float)."""
    return f"""
# Point 8 (cas A) : effort d'accostage sur DEFENSE, direction globale +Y
# (perpendiculaire au quai, vers la terre -- décision point 8), intensité
# rapportée à la surface développée des mailles de DEFENSE (essai lot 21,
# point 8 : la référence de FORCE_COQUE est la surface développée, non la
# surface projetée), FX = FZ = 0.
{concept} = AFFE_CHAR_MECA(
    MODELE=MO, FORCE_COQUE=_F(GROUP_MA=("DEFENSE",), FY={_fmt(fy)})
)
"""


def poutre_pressure_nodal_block(
    concept: str, node_loads: dict[str, tuple[float, float, float | None]]
) -> str:
    """Point 12 (décision 13, lot 33) : poussée et pression d'eau sur la
    hauteur de la poutre de couronnement (+2,60 à +4,00), représentées par
    des forces nodales (`FORCE_NODALE`, U4.44.01) aux nœuds `GEN_POUTRE_<n>`
    (un par tube), pondérées par la longueur tributaire de chaque nœud
    (`aster_expert.generation.generate._tributary_lengths`) -- jamais
    `FORCE_POUTRE`.

    **`FORCE_POUTRE` a été essayé en premier et écarté par une exécution
    réelle**, pas par la documentation : le cas test officiel `ssll119a.comm`
    combine bien `FORCE_POUTRE` avec plusieurs composantes (`FX`/`MX`) et un
    `LIAISON_SOLIDE` isolé (`data/examples/lot33_equilibre/isolation/`)
    fonctionne aussi -- mais la poutre de couronnement réelle, continue et
    liée par PLUSIEURS occurrences de `LIAISON_SOLIDE` (une par tube, point
    3), bloque tout `CALC_CHAMP` ultérieur sur son propre résultat dès que
    `FORCE_POUTRE` s'y ajoute (`<F> <CALCULEL2_92>`, "votre chargement
    contient plus d'une charge répartie... pas possible pour les modèles de
    poutre"), quel que soit le nombre de composantes non nulles ou la
    présence d'un second chargement réparti (`PESANTEUR`) --
    `data/examples/lot33_equilibre/quai_reduit/`. Mécanisme précis non
    identifié (comme la numérotation interne de `LIAISON_SOLIDE`, lots
    28/30/31 : hors de portée des sept outils MCP).

    La résultante et le moment totaux restent exacts (somme des poids
    tributaires = longueur totale de la poutre) : seule la répartition
    locale est approchée (concentrée aux `n_tubes` nœuds plutôt que
    continue), sans effet sur l'équilibre global -- la seule chose que
    l'étape 3 vérifie."""
    occurrences = []
    for node, (fy, mx, fz) in node_loads.items():
        fz_kw = f", FZ={_fmt(fz)}" if fz is not None else ""
        occurrences.append(
            f'_F(GROUP_NO=("{node}",), FY={_fmt(fy)}, MX={_fmt(mx)}{fz_kw}),'
        )
    body = "\n        ".join(occurrences)
    return f"""
# Point 12 (décision 13) : force et moment linéiques de la décision 13,
# répartis en forces nodales tributaires-pondérées aux nœuds de poutre
# (voir poutre_pressure_nodal_block -- jamais FORCE_POUTRE, une exécution
# réelle l'écarte pour la poutre continue à plusieurs LIAISON_SOLIDE).
{concept} = AFFE_CHAR_MECA(
    MODELE=MO,
    FORCE_NODALE=(
        {body}
    ),
)
"""


SOLVER_RESI_RELA = 1.0e-4
"""Historical value of `SOLVEUR/RESI_RELA` (MUMPS, catalogue default 1e-6;
lots 28-32): relaxed after an actual execution (`<F> <FACTOR_57>`, "la
solution du système linéaire est trop imprécise", erreur calculée 2.7e-5)
hit the default's tolerance once `LIAISON_SOLIDE` (point 3) coexisted with
`COEF_RIGI_DRZ`'s own, then deliberately tiny (point 3), drilling stiffness.
**Lot 33, étape 1** found the model solves at the plain catalogue default on
the reduced quay (isolated test, `docs/essais_lot33.md`) once `COEF_RIGI_DRZ`
itself no longer needs raising either (see `DRZ_STIFFNESS_COEF`'s own
docstring): production no longer passes this value (`case_block`'s own
`resi_rela` defaults to `None`, omitting the keyword). Kept only so
`aster_expert.generation.generate.SolverDiagnostics` can still reproduce the
lots 28-32 behaviour on request."""

SOLVER_RESI_RELA_CATALOGUE_DEFAULT = 1.0e-6
"""`SOLVEUR/RESI_RELA`'s own catalogue default under `METHODE="MUMPS"` (level
A, `get_command_schema("MECA_STATIQUE", keyword="SOLVEUR.RESI_RELA")`,
confirmed lot 33, étape 1) -- the value `SOLVER_RESI_RELA` was relaxed from,
and the value production now gets implicitly by omitting the keyword
entirely. Kept only for `aster_expert.generation.generate.SolverDiagnostics`
to pass explicitly when reproducing that omission is useful (e.g. a
regression test comparing byte-for-byte to the implicit form)."""


def case_block(
    name: str,
    *,
    extra_charges: list[str],
    sans_poutre: bool = False,
    resi_rela: float | None = None,
) -> str:
    """One elementary load case (Étape 3, point 4 of the table): its own
    `MECA_STATIQUE` and `REAC_NODA` (support reactions) for the equilibrium
    controls -- never combined with another case (no `COEF_MULT`, no
    superposition). The spring forces are read from `DEPL` in `controls_
    block` (lot 33, étape 3), not computed here.

    Neither `CONTRAINTE=("EFGE_ELNO",)` nor even a bare `FORCE_POUTRE` on
    `POUTRE_COUR` survive `CALC_CHAMP` once décision 13 is present: an
    actual execution (`<F> <CALCULEL2_92>`, "votre chargement contient plus
    d'une charge répartie... pas possible pour les modèles de poutre") --
    see `poutre_pressure_nodal_block`'s own docstring for the isolation that
    narrowed this to the continuous beam tied by several `LIAISON_SOLIDE`
    occurrences (point 3), never fixed by restricting `CALC_CHAMP`'s own
    `GROUP_MA`. Décision 13's load is therefore applied as nodal forces
    (`poutre_pressure_nodal_block`), never `FORCE_POUTRE`, in production.

    Lot 30, étape 3 (diagnostic « sans la poutre, donc sans liaison de corps
    solide ») : `sans_poutre` omits `CH_SOLIDE` from `EXCIT` -- the concept
    itself does not exist in this variant
    (`aster_expert.generation.comm.liaison_solide_block` returns an empty
    string).

    Lot 33, étape 1 (diagnostic « paramètres hérités ») : `resi_rela` lets
    `aster_expert.generation.generate.SolverDiagnostics` add an explicit
    `SOLVEUR/RESI_RELA` -- isolated testing on the reduced quay
    (`docs/essais_lot33.md`) found the model solves at the bare catalogue
    default (`SOLVER_RESI_RELA_CATALOGUE_DEFAULT`), so production now leaves
    `resi_rela` at its default (`None`), omitting the keyword entirely
    rather than writing that default value out."""
    charges = "\n        ".join(f"_F(CHARGE={c})," for c in extra_charges)
    ch_solide = "" if sans_poutre else "\n        _F(CHARGE=CH_SOLIDE),"
    solveur = (
        f'SOLVEUR=_F(METHODE="MUMPS", RESI_RELA={_fmt(resi_rela)}),'
        if resi_rela is not None
        else 'SOLVEUR=_F(METHODE="MUMPS"),'
    )
    return f"""
RESU_{name} = MECA_STATIQUE(
    MODELE=MO,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    EXCIT=({ch_solide}
        _F(CHARGE=CH_BLOC),
        {charges}
    ),
    {solveur}
)
RESU_{name} = CALC_CHAMP(reuse=RESU_{name}, RESULTAT=RESU_{name}, FORCE=("REAC_NODA",))
"""


_SUPPORT_GROUPS = ("ANCRAGES", "PIED_TUBES", "SYM_G", "SYM_D")
"""Point 8 (established at lot 20) / lot 23's own equilibrium-control rule:
nodes that carry no `ELAS_COQUE` element, the only ones `REAC_NODA` is valid
on. None of these four groups touches a palplanche quad (the palplanche
lies strictly between two tubes, never on a symmetry face, an anchor or a
tube foot): every node here belongs only to `ELAS` shells (the tube), a
`BARRE` (the anchor) or nothing at all."""


def controls_block(
    name: str,
    spring_group_names: list[str],
    *,
    reaction_components: tuple[str, ...] = ("DY",),
    sans_tirants: bool = False,
) -> str:
    """Étape 4's D-level controls, per elementary case: the displacement of
    every spring node (`DEPL`/`DY`, lot 33 étape 3 -- never `FORC_NODA`'s
    node-summed field, contaminated by whatever shell shares that node;
    never `EFGE_ELNO` either, which fails outright once a beam model in the
    same result carries more than one distributed load, see `controls_block`'s
    own `ressorts_block` for the actual execution) and the resultant in the
    support reactions (`REAC_NODA`, `_SUPPORT_GROUPS` only -- lot 23), for
    the equilibrium check; every node's displacement (`DEPL`) for the
    symmetry check. `POST_RELEVE_T`/`RESULTANTE`: 158 cas tests officiels
    (ex. forma40a.comm). A spring's own force is `k * DY` (point 4: a
    `K_T_D_N` carries stiffness on its second component alone, verified on a
    one-spring analytic case, `data/examples/lot33_equilibre/ressort_seul
    .comm`) -- `aster_expert`'s own analysis script multiplies and sums
    `TAB_RESS_<nom>` itself, once printed, matching each row's own `COOR_X`/
    `COOR_Y`/`COOR_Z` to the generator's own spring classes (never `k`
    recomputed by hand, never a node name parsed).

    Lot 33, étape 4 : the symmetry table used to be two hand-picked node
    pairs (`edge_tube_low`/`edge_tube_high`/`inner_tube_low`/`inner_tube_
    high`, dropped from this signature) -- `TAB_SYM_<nom>` now carries
    `GROUP_NO=(ALL_NODES_GROUP,)` (every node of the mesh, `mesh_prep_
    block`'s own `TOUT_GROUP_MA="OUI"` group -- `POST_RELEVE_T/EXTRACTION`
    refuses `TOUT="OUI"` alone), and `aster_expert`'s own analysis script
    pairs each node to its mirror by `COOR_X`/`COOR_Y`/`COOR_Z`, never a
    node name or a hand-picked group."""
    springs = ", ".join(f'"{n}"' for n in spring_group_names)
    components = ", ".join(f'"{c}"' for c in reaction_components)
    # Lot 30, étape 3 (diagnostic « sans les ressorts ») : `GROUP_MA` a un
    # minimum d'une occurrence -- sans classe de ressort, ce contrôle n'a
    # rien à extraire et est omis plutôt que d'écrire un GROUP_MA vide.
    # Lot 33, étape 3 : `EFGE_ELNO` (essayé d'abord) échoue dès que
    # `FORCE_POUTRE` porte la décision 13 sur la poutre de couronnement,
    # continue et liée par plusieurs occurrences de `LIAISON_SOLIDE` (point
    # 3) : `<F> <CALCULEL2_92>` -- voir `poutre_pressure_nodal_block`'s own
    # docstring pour l'isolation qui écarte `FORCE_POUTRE` de la production
    # (la décision 13 y est portée par des forces nodales, jamais par une
    # charge répartie -- ce contrôle n'a donc plus lieu de rencontrer ce
    # défaut, mais `EFGE_ELNO` reste écarté au profit de `DEPL`/`DY` par
    # sécurité et parce que ce dernier est de toute façon nécessaire).
    # `DEPL`/`DY` (jamais restreint de cette façon, un champ nodal ordinaire)
    # donne le même résultat par construction : un ressort K_T_D_N ne porte
    # de raideur que sur sa deuxième composante (point 4), donc son effort
    # vaut exactement k * DY (vérifié sur un cas isolé à réponse analytique
    # connue, `data/examples/lot33_equilibre/ressort_seul.comm`). `COOR_X`/
    # `COOR_Y`/`COOR_Z` (ajoutés automatiquement par `POST_RELEVE_T` à une
    # extraction nodale) identifient, sans ambiguïté et sans explosion par
    # classe, le nœud -- donc sa classe et sa raideur -- pour le script
    # d'analyse qui somme cette table (k n'est jamais recalculé dans le
    # `.comm`, seulement dans ce script, à partir des mêmes classes que le
    # générateur).
    ressorts_block = (
        f"""
TAB_RESS_{name} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="RESSORTS_{name}",
        RESULTAT=RESU_{name},
        NOM_CHAM="DEPL",
        TOUT_ORDRE="OUI",
        GROUP_NO=({springs}),
        NOM_CMP=("DY",),
    )
)
IMPR_TABLE(TABLE=TAB_RESS_{name}, UNITE=6)
"""
        if spring_group_names
        else ""
    )
    # Lot 30, étape 3 (diagnostic « sans les tirants ») : ANCRAGES n'a plus
    # aucun élément ni condition limite directe -- ses nœuds sont hors du
    # modèle (aucun DDL), REAC_NODA y échouerait ; exclu du contrôle.
    support_groups = (
        tuple(g for g in _SUPPORT_GROUPS if g != "ANCRAGES")
        if sans_tirants
        else _SUPPORT_GROUPS
    )
    return f"""{ressorts_block}
TAB_REAC_{name} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="REACTIONS_{name}",
        RESULTAT=RESU_{name},
        NOM_CHAM="REAC_NODA",
        TOUT_ORDRE="OUI",
        GROUP_NO={_tup(list(support_groups))},
        RESULTANTE=({components}),
    )
)
IMPR_TABLE(TABLE=TAB_REAC_{name}, UNITE=6)

# Point 7 : symétrie -- lot 33, étape 4 : TOUT le maillage, jamais deux
# paires choisies à la main (docs/essais_lot33.md) : le script d'analyse
# associe chaque nœud à son image miroir (x -> -x, mêmes y, z) par les
# coordonnées imprimées (COOR_X/Y/Z) et compare DY/DZ (égaux) et DX
# (opposé), sur chaque paire.
TAB_SYM_{name} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="SYMETRIE_{name}",
        RESULTAT=RESU_{name},
        NOM_CHAM="DEPL",
        TOUT_ORDRE="OUI",
        GROUP_NO=("{ALL_NODES_GROUP}",),
        NOM_CMP=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=TAB_SYM_{name}, UNITE=6)
"""


def order_of_magnitude_block(name: str, tube_names: list[str]) -> str:
    """Point 4's own "ordre de grandeur" (no pass/fail criterion, CLAUDE.md
    principle 6: a datum for MM, not a verdict): maximum horizontal head
    displacement of the screen."""
    groups = ", ".join(f'"TETE_TUBE_{n}"' for n in tube_names)
    return f"""
TAB_ORDRE_{name} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTREMA",
        INTITULE="ORDRE_GRANDEUR_{name}",
        RESULTAT=RESU_{name},
        NOM_CHAM="DEPL",
        TOUT_ORDRE="OUI",
        GROUP_NO=({groups}),
        NOM_CMP="DY",
    )
)
IMPR_TABLE(TABLE=TAB_ORDRE_{name}, UNITE=6)
"""


MAX_NOM_RESU_MED_LEN = 8
"""`IMPR_RESU/RESU/NOM_RESU_MED` (U7.05.21, opérande NOM_RESU_MED) : "chaine
d'au plus 8 caractères". Sans lui, le nom de champ MED par défaut concatène
RESULTAT/NOM_CHAM/NUME_ORDRE -- où RESULTAT est le nom Jeveux du concept,
lui-même tronqué en silence à 8 caractères indépendamment du nom Python
choisi ici (`RESU_EAU_P`/`RESU_EAU_A`, tous deux tronqués à `RESU_EAU`) :
exactement le défaut découvert au lot 31 (`<F> <MED2_4>`, "Le champ
'RESU_EAUDEPL' est déjà présent"), corrigé au lot 32 en fixant explicitement
un nom court par cas, jamais laissé à cette troncature implicite."""


def _nrm(name: str) -> str:
    if len(name) > MAX_NOM_RESU_MED_LEN:
        message = (
            f"NOM_RESU_MED trop long ({len(name)} > {MAX_NOM_RESU_MED_LEN} "
            f"caractères, U7.05.21) : {name}"
        )
        raise GenerationError(message)
    return name


def footer(result_names: list[str]) -> str:
    """Lot 31, étape 3 (défaut latent découvert en vérifiant la correction de
    masse) : `CARA_ELEM=CARA` sur chaque occurrence de `RESU` -- sans lui,
    l'écriture MED de `SIEF_ELGA` (sous-points d'un élément COQUE) échoue en
    fin d'exécution (`<F> <MED2_14>`, "On a besoin du CARA_ELEM pour imprimer
    des champs à sous-points pour les éléments de structure de type COQUE...
    Préciser le mot-clé CARA_ELEM sous le mot clé facteur RESU", IMPR_RESU/
    RESU/CARA_ELEM, condition FORMAT='MED') : jamais atteint avant ce lot, le
    pivot nul de LIAISON_SOLIDE arrêtant systématiquement l'exécution avant
    IMPR_RESU.

    Lot 32, étape 3 : `NOM_RESU_MED=<nom du cas>` (voir `MAX_NOM_RESU_MED_LEN`)
    sur chaque occurrence -- corrige la collision de champ MED entre
    `RESU_EAU_P` et `RESU_EAU_A` signalée au lot 31, jamais atteinte avant
    lui (le pivot nul de LIAISON_SOLIDE arrêtait toujours l'exécution avant
    IMPR_RESU)."""
    resu = "\n        ".join(
        f'_F(RESULTAT=RESU_{n}, CARA_ELEM=CARA, NOM_RESU_MED="{_nrm(n)}"),'
        for n in result_names
    )
    return f"""
IMPR_RESU(
    FORMAT="MED",
    UNITE=80,
    RESU=(
        {resu}
    ),
)

FIN()
"""


__all__ = [
    "BEAM_NODE_PREFIX",
    "REF_NORM_GROUP",
    "JunctionMethod",
    "bollard_force_block",
    "case_block",
    "check_symmetry_ddl_impo_no_ring_redundancy",
    "defense_force_block",
    "footer",
    "formule_block",
    "header",
    "junction_charge_block",
    "junction_ring_groups_block",
    "liaison_solide_block",
    "materials_block",
    "mesh_prep_block",
    "model_and_cara_block",
    "pesanteur_block",
    "poutre_pressure_nodal_block",
    "pressure_load_block",
    "symmetry_and_support_block",
]
