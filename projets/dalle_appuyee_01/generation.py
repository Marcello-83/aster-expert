"""Generator of the `.comm` of the slab DALLE-APPUYEE-01 (lot 43).

Everything comes from the arbitrated fiche and the data file (decisions of MM,
`arbitrage_dalle_appuyee_01_v1` and its ELS complement); each block names the
point of the fiche and the knowledge entry it applies. Units of the model: m, N,
Pa, kg (point 9); the data file keeps the units of its sources and the conversion
is done here, once, in `slab_values`.

Blocks:

- mesh (MED, unit 20), normals oriented +Z (`ORIE_NORM_COQUE`, CA-028): the
  "upper" face of `CALC_FERRAILLAGE` is the side of the normal (CA-045), here the
  top of the slab;
- DKT (point 1), `ELAS` E, NU, RHO with RHO = gamma / g (point 4), `EPAIS`,
  `ANGL_REP = (0, 0)`: x_l = X (point 9);
- supports (point 6): DZ = 0 on `APPUIS`, DX = DY = 0 at `P_A`, DY = 0 at `P_B`,
  each degree of freedom blocked once (DIAG-001);
- elementary cases G (`PESANTEUR`) and Q (`FORCE_COQUE/FZ`), computed separately
  (point 4), with the tables of the level D controls (reactions by group, all
  nodes, symmetry) and of the level E comparison (centre);
- combinations of `aster_expert.combinaisons.enumeration` (point 13), one
  `MECA_STATIQUE` each with constant multipliers, and the 2D reinforcement of the
  common trunk (`aster_expert.ferraillage.plaque`, point 14), plus the sensitivity
  run of the `SIGC_*_ELS` limit asked by MM.

Tables: read by `CREA_TABLE` for the forces, `POST_RELEVE_T` for the displacements
and reactions (PAT-009), printed in `E20.12`, titles of 16 characters at most and
unique (CTL-010, checked here).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from aster_expert.combinaisons.enumeration import Combination, enumerate_combinations
from aster_expert.ferraillage.plaque import check_group_block, plate_rebar_block
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import DataRef

TABLE_FORMAT_R = "E20.12"
TITLE_MAX = 16
ALL_NODES = "GEN_NOEUDS"
CASES = ("G", "Q")
SENSITIVITY_SIGC_PA = 1.0e9
"""Non-binding `SIGC_*_ELS` of the sensitivity run (MM, ELS complement): 1000 MPa,
far above any concrete stress of the slab -- an input device, not a limit."""


class GenerationError(ValueError):
    """A refusal of the generator (shown as `le générateur du projet refuse`)."""


@dataclass(frozen=True)
class SlabValues:
    """Numbers of the model, converted to m, N, Pa, kg."""

    length: float
    width: float
    thickness: float
    young: float
    poisson: float
    gravity: float
    unit_weight: float
    live_load: float

    @property
    def rho(self) -> float:
        """RHO such that RHO x g is exactly the unit weight (point 4)."""
        return self.unit_weight / self.gravity

    @property
    def weight_resultant(self) -> float:
        return self.unit_weight * self.length * self.width * self.thickness

    @property
    def live_resultant(self) -> float:
        return self.live_load * self.length * self.width


def _d(ctx: ProjectContext, key: str, unit: str) -> float:
    return ctx.number(DataRef(data=key), unit=unit)


def slab_values(ctx: ProjectContext) -> SlabValues:
    return SlabValues(
        length=_d(ctx, "geometrie.longueur", "m"),
        width=_d(ctx, "geometrie.largeur", "m"),
        thickness=_d(ctx, "geometrie.epaisseur", "m"),
        young=_d(ctx, "beton.module_young", "MPa") * 1e6,
        poisson=_d(ctx, "beton.coefficient_poisson", "-"),
        gravity=_d(ctx, "charges.acceleration_pesanteur", "m/s2"),
        unit_weight=_d(ctx, "beton.poids_volumique", "kN/m3") * 1e3,
        live_load=_d(ctx, "charges.exploitation_uniforme", "kPa") * 1e3,
    )


def _r(x: float) -> str:
    return repr(float(x))


def _title(text: str, seen: set[str]) -> str:
    if len(text) > TITLE_MAX:
        message = f"intitulé de table trop long ({len(text)} > {TITLE_MAX}) : {text}"
        raise GenerationError(message)
    if text in seen:
        message = f"intitulé de table en double : {text}"
        raise GenerationError(message)
    seen.add(text)
    return text


def _reaction(name: str, label: str, group: str, seen: set[str]) -> str:
    title = _title(f"REAC_{label}_{name}", seen)
    return f"""
T_R{label[:2]}_{name} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="{title}",
        RESULTAT={name_of(name)},
        NOM_CHAM="REAC_NODA",
        TOUT_ORDRE="OUI",
        GROUP_NO=("{group}",),
        RESULTANTE=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=T_R{label[:2]}_{name}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
"""


def name_of(case: str) -> str:
    return f"RESU_{case}"


def case_tables(case: str, seen: set[str]) -> str:
    """Level D (reactions, symmetry) and level E (centre) tables of a case."""
    resu = name_of(case)
    reactions = "".join(
        _reaction(case, label, group, seen)
        for label, group in (
            ("APPUIS", "APPUIS"),
            ("PA", "P_A"),
            ("PB", "P_B"),
            ("TOUS", ALL_NODES),
        )
    )
    sym = _title(f"SYMETRIE_{case}", seen)
    depl = _title(f"DEPL_CENTRE_{case}", seen)
    rnodes = _title(f"REACN_APPUI_{case}", seen)
    efn_c = _title(f"EFN_CENTRE_{case}", seen)
    efe_c = _title(f"EFE_CENTRE_{case}", seen)
    efn_d = _title(f"EFN_DALLE_{case}", seen)
    return f"""
{resu} = CALC_CHAMP(
    reuse={resu},
    RESULTAT={resu},
    CONTRAINTE=("EFGE_ELNO", "EFGE_NOEU"),
    FORCE=("REAC_NODA",),
)
{reactions}
# Réactions nœud par nœud des appuis (réaction de coin, P4) et symétrie de tous les
# nœuds (contrôle D : la symétrie est vérifiée, pas imposée, P4).
T_RN_{case} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="{rnodes}",
        RESULTAT={resu},
        NOM_CHAM="REAC_NODA",
        TOUT_ORDRE="OUI",
        GROUP_NO=("APPUIS",),
        NOM_CMP=("DZ",),
    )
)
IMPR_TABLE(TABLE=T_RN_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
T_SY_{case} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="{sym}",
        RESULTAT={resu},
        NOM_CHAM="DEPL",
        TOUT_ORDRE="OUI",
        GROUP_NO=("{ALL_NODES}",),
        NOM_CMP=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=T_SY_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
# Niveau E (point 10) : flèche et moments au nœud CENTRE (EFGE_NOEU) ; EFGE_ELNO des
# mailles voisines pour l'écart de lissage seulement.
T_DC_{case} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="{depl}",
        RESULTAT={resu},
        NOM_CHAM="DEPL",
        TOUT_ORDRE="OUI",
        GROUP_NO=("CENTRE",),
        NOM_CMP=("DX", "DY", "DZ", "DRX", "DRY"),
    )
)
IMPR_TABLE(TABLE=T_DC_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
T_NC_{case} = CREA_TABLE(
    RESU=_F(
        RESULTAT={resu},
        NOM_CHAM="EFGE_NOEU",
        TOUT_ORDRE="OUI",
        NOM_CMP=("MXX", "MYY", "MXY", "QX", "QY"),
        GROUP_NO="CENTRE",
    )
)
IMPR_TABLE(TABLE=T_NC_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}", TITRE="{efn_c}")
T_EC_{case} = CREA_TABLE(
    RESU=_F(
        RESULTAT={resu},
        NOM_CHAM="EFGE_ELNO",
        TOUT_ORDRE="OUI",
        NOM_CMP=("MXX", "MYY", "MXY"),
        GROUP_MA="CENTRE_V",
    )
)
IMPR_TABLE(TABLE=T_EC_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}", TITRE="{efe_c}")
T_ND_{case} = CREA_TABLE(
    RESU=_F(
        RESULTAT={resu},
        NOM_CHAM="EFGE_NOEU",
        TOUT_ORDRE="OUI",
        NOM_CMP=("MXX", "MYY", "MXY"),
        GROUP_MA="DALLE",
    )
)
IMPR_TABLE(TABLE=T_ND_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}", TITRE="{efn_d}")
"""


def combination_name(index: int) -> str:
    return f"RC{index:02d}"


def combination_block(
    index: int, combination: Combination, seen: set[str], *, name: str | None = None
) -> str:
    """One `MECA_STATIQUE` with the coefficients as constant multipliers (linear
    elasticity: exactly the combination of the elementary cases)."""
    resu = name or combination_name(index)
    functions = "".join(
        f"F_{resu}_{case} = DEFI_CONSTANTE(VALE={_r(coeff)})\n"
        for case, coeff in combination.coefficients.items()
    )
    excit = "".join(
        f"        _F(CHARGE=CH_{case}, FONC_MULT=F_{resu}_{case}),\n"
        for case in combination.coefficients
    )
    title = _title(f"EFN_C_{resu}", seen)
    return f"""
# {combination.name} ({combination.family}) : {combination.coefficients}
{functions}{resu} = MECA_STATIQUE(
    MODELE=MODELE,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    EXCIT=(
        _F(CHARGE=CL),
{excit}    ),
)
{resu} = CALC_CHAMP(reuse={resu}, RESULTAT={resu}, CONTRAINTE=("EFGE_ELNO", "EFGE_NOEU"))
T_N_{resu} = CREA_TABLE(
    RESU=_F(
        RESULTAT={resu},
        NOM_CHAM="EFGE_NOEU",
        TOUT_ORDRE="OUI",
        NOM_CMP=("NXX", "NYY", "NXY", "MXX", "MYY", "MXY"),
        GROUP_NO="CENTRE",
    )
)
IMPR_TABLE(TABLE=T_N_{resu}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}", TITRE="{title}")
"""


def build_comm(ctx: ProjectContext, *, mesh_label: str) -> tuple[str, dict[str, Any]]:
    v = slab_values(ctx)
    seen: set[str] = set()
    rebar = ctx.declaration.rebar
    section = ctx.declaration.combinations
    if rebar is None or not rebar.plates or section is None:
        message = (
            "la déclaration doit porter les combinaisons et la plaque à ferrailler"
        )
        raise GenerationError(message)
    plate = rebar.plates[0]
    combos = enumerate_combinations(section, ctx.number)
    result_of = {c.name: combination_name(i) for i, c in enumerate(combos, start=1)}
    combo_blocks = "".join(
        combination_block(i, c, seen) for i, c in enumerate(combos, start=1)
    )
    characteristic = [c for c in combos if c.family == "ELS caractéristique"]
    sensitivity = "".join(
        combination_block(0, c, seen, name="RSENS") for c in characteristic[:1]
    )
    rebar_text = plate_rebar_block(ctx, plate, result_of=result_of, cara="CARA")
    sens_text = plate_rebar_block(
        ctx,
        plate,
        result_of={c.name: "RSENS" for c in characteristic[:1]},
        cara="CARA",
        sigc_els_override=SENSITIVITY_SIGC_PA,
        type_combs=frozenset({"ELS"}),
        prefix="S",
    )
    for line in (rebar_text + sens_text).splitlines():
        if 'TITRE="' in line:
            _title(line.split('TITRE="', 1)[1].split('"', 1)[0], seen)
    tables = "".join(case_tables(case, seen) for case in CASES)
    text = f"""# Dalle DALLE-APPUYEE-01 (lot 43) -- maillage {mesh_label}.
# Généré par dalle_appuyee_01.generation à partir de la fiche arbitrée
# (fiche/hypotheses_dalle_arbitree.json) et des données (donnees/dalle_model_data.yaml) :
# ne pas éditer. Unités : m, N, Pa, kg (point 9).

DEBUT(CODE="OUI")

MAIL = LIRE_MAILLAGE(FORMAT="MED", UNITE=20)

# Point 10 / CA-045 : normales +Z, la face « supérieure » de CALC_FERRAILLAGE est le
# dessus de la dalle (MODI_MAILLAGE/ORIE_NORM_COQUE, CA-028).
MAIL = MODI_MAILLAGE(
    reuse=MAIL,
    MAILLAGE=MAIL,
    ORIE_NORM_COQUE=_F(GROUP_MA=("DALLE",), VECT_NORM=(0.0, 0.0, 1.0), GROUP_NO="P_A"),
)
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=_F(GROUP_MA="DALLE", NOM="{ALL_NODES}"),
)
{check_group_block(plate, "MAIL")}
# Point 1 : DKT (Love-Kirchhoff).
MODELE = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(GROUP_MA="DALLE", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

# Point 5 : béton non fissuré E = {v.young:.6g} Pa, NU = {v.poisson} ; point 4 :
# RHO = poids volumique / g = {v.unit_weight:.6g} / {v.gravity} kg/m3 (ρ·g = 25 kN/m³).
BETON = DEFI_MATERIAU(ELAS=_F(E={_r(v.young)}, NU={_r(v.poisson)}, RHO={_r(v.rho)}))
CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA="DALLE", MATER=BETON))

# Épaisseur ; ANGL_REP = (0, 0) : x_l = X, MXX porte sur la direction X.
CARA = AFFE_CARA_ELEM(
    MODELE=MODELE,
    COQUE=_F(GROUP_MA="DALLE", EPAIS={_r(v.thickness)}, ANGL_REP=(0.0, 0.0)),
)

# Point 6 : appui bilatéral DZ = 0 sur APPUIS (rotations libres), blocage plan
# isostatique DX = DY = 0 en P_A, DY = 0 en P_B ; chaque ddl bloqué une seule fois
# (DIAG-001).
CL = AFFE_CHAR_MECA(
    MODELE=MODELE,
    DDL_IMPO=(
        _F(GROUP_NO="APPUIS", DZ=0.0),
        _F(GROUP_NO="P_A", DX=0.0, DY=0.0),
        _F(GROUP_NO="P_B", DY=0.0),
    ),
)

# Point 4 : G par PESANTEUR (résultante attendue {v.weight_resultant:.6g} N), Q par
# FORCE_COQUE/FZ en -Z (résultante attendue {v.live_resultant:.6g} N), calculés séparément.
CH_G = AFFE_CHAR_MECA(
    MODELE=MODELE,
    PESANTEUR=_F(GRAVITE={_r(v.gravity)}, DIRECTION=(0.0, 0.0, -1.0), GROUP_MA=("DALLE",)),
)
CH_Q = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="DALLE", FZ={_r(-v.live_load)}))

RESU_G = MECA_STATIQUE(
    MODELE=MODELE, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=(_F(CHARGE=CL), _F(CHARGE=CH_G))
)
RESU_Q = MECA_STATIQUE(
    MODELE=MODELE, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=(_F(CHARGE=CL), _F(CHARGE=CH_Q))
)
{tables}
# Point 13 : combinaisons (aster_expert.combinaisons.enumeration, γ et ψ des données).
{combo_blocks}
# Point 14 : ferraillage 2D (aster_expert.ferraillage.plaque).
{rebar_text}
# Sensibilité demandée par MM : SIGC_*_ELS non contraignant ({SENSITIVITY_SIGC_PA:.3g} Pa) sur
# la combinaison caractéristique ; densités identiques = limite de 0,6 fck inactive.
{sensitivity}{sens_text}
FIN()
"""
    report = {
        "comm_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "combinaisons": [c.name for c in combos],
        "tables": sorted(seen),
        "resultante_G_N": v.weight_resultant,
        "resultante_Q_N": v.live_resultant,
        "rho_kg_m3": v.rho,
    }
    return text, report


__all__ = [
    "ALL_NODES",
    "CASES",
    "GenerationError",
    "SENSITIVITY_SIGC_PA",
    "SlabValues",
    "build_comm",
    "combination_name",
    "name_of",
    "slab_values",
]
