"""Numbers of the model ESTACADE-PIEUX-01 (lot 47), converted once to m, N, Pa, kg.

The data file keeps the units of its sources (annex B of the lot 47 instruction and
the decisions E1 to E16 of MM); every module of the project reads the model through
`model_values`, never the data file directly. Frame (agent's choice, point U1): X
along the deck from the abutment (X = 0), Y across from the deck axis, Z up with
Z = the NGF level, so the slab mid-plane is at Z = +1.30 and the pile tips at
Z = -13.00.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aster_expert.agent.model_data import DataValue, ProfilePoint
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import DataRef

LEVEL_PRECISION = 1.0e-9


class DataError(ValueError):
    """The data file does not give what the model needs."""


@dataclass(frozen=True)
class Section:
    """One pile segment of table B2, from `z_top` down to `z_bottom` (m)."""

    name: str
    z_top: float
    z_bottom: float
    area: float
    """m2"""
    inertia: float
    """m4"""

    def equivalent_tube(self) -> tuple[float, float]:
        """(R, EP) in m of the uniform tube with exactly this area and inertia:
        I / A = (R^2 + r^2) / 4 and A / pi = R^2 - r^2 (deduction, checked against
        the I/v column of B2 by `section_modulus`)."""
        s = 4.0 * self.inertia / self.area
        d = self.area / math.pi
        r_out = math.sqrt((s + d) / 2.0)
        r_in = math.sqrt((s - d) / 2.0)
        return r_out, r_out - r_in

    def section_modulus(self) -> float:
        """I / R of the equivalent tube (m3), to compare with I/v of B2."""
        return self.inertia / self.equivalent_tube()[0]


@dataclass(frozen=True)
class Pile:
    file: int
    """File index, 1 to 7."""
    side: str
    """`YM` (Y < 0) or `YP` (Y > 0)."""
    x: float
    y: float
    family: str
    """`RIVE` (files 1 and 7) or `EAU` (files 2 to 6), table B3."""

    @property
    def name(self) -> str:
        return f"F{self.file}_{self.side}"


@dataclass(frozen=True)
class SpringLevel:
    family: str
    z: float
    k: float
    """N/m, kx = ky."""

    @property
    def group(self) -> str:
        """Node group of the springs of this family at this level (24 characters
        at most): `KR_P100` (rive, +1.00), `KE_M1250` (eau, -12.50)."""
        sign = "P" if self.z >= 0 else "M"
        cm = round(abs(self.z) * 100)
        return f"K{self.family[0]}_{sign}{cm:03d}"


@dataclass(frozen=True)
class ModelValues:
    length: float
    width: float
    thickness: float
    z_mid: float
    x_files: tuple[float, ...]
    y_piles: float
    lane: tuple[float, float]
    guard_y: float
    cap_width: float
    cap_height: float
    sections: tuple[Section, ...]
    plug: tuple[float, float]
    """(top, bottom) levels of the plug (E14)."""
    z_tip: float
    springs: tuple[SpringLevel, ...]
    spring_step: float
    e_concrete: float
    nu_concrete: float
    gamma_concrete: float
    e_steel: float
    nu_steel: float
    gamma_steel: float
    alpha: float
    gravity: float
    g2_sidewalk: float
    g2_lane: float
    g2_guard: float
    ts_wheel: float
    ts_print: float
    ts_axle_spacing: float
    ts_wheel_spacing: float
    ts_y_centred: float
    udl: float
    tr: float
    lm2_wheel: float
    lm2_print_x: float
    lm2_print_y: float
    lm2_wheel_spacing: float
    fr_total: float
    delta_t: float
    moving_step: float

    @property
    def y_min(self) -> float:
        return -self.width / 2.0

    @property
    def y_max(self) -> float:
        return self.width / 2.0

    @property
    def z_top_slab(self) -> float:
        return self.z_mid + self.thickness / 2.0

    def piles(self) -> tuple[Pile, ...]:
        n = len(self.x_files)
        out = []
        for i, x in enumerate(self.x_files, start=1):
            family = "RIVE" if i in (1, n) else "EAU"
            for side, y in (("YM", -self.y_piles), ("YP", self.y_piles)):
                out.append(Pile(file=i, side=side, x=x, y=y, family=family))
        return tuple(out)

    def pile_levels(self) -> tuple[float, ...]:
        """Levels of the pile nodes, top (mid-plane) to tip: the spring nodes, the
        section breaks of B2 and the mid-plane, each once."""
        levels = {round(self.z_mid, 9), round(self.z_tip, 9)}
        levels.update(round(s.z_bottom, 9) for s in self.sections)
        levels.update(round(s.z, 9) for s in self.springs)
        return tuple(sorted(levels, reverse=True))

    def section_at(self, z_top: float, z_bottom: float) -> Section:
        """The B2 segment that holds the element between two pile levels (E3: the
        upper segment is prolonged up to the deck node)."""
        mid = (z_top + z_bottom) / 2.0
        for s in self.sections:
            if s.z_bottom - LEVEL_PRECISION <= mid <= s.z_top + LEVEL_PRECISION:
                return s
        message = f"aucun tronçon de B2 ne contient la cote {mid}"
        raise DataError(message)

    def spring_levels(self, family: str) -> tuple[SpringLevel, ...]:
        return tuple(s for s in self.springs if s.family == family)


def _value(ctx: ProjectContext, key: str, unit: str) -> float:
    return ctx.number(DataRef(data=key), unit=unit)


def _vector(items: dict[str, DataValue], key: str) -> tuple[float, ...]:
    value = items[key].value
    if not isinstance(value, tuple):
        message = f"{key} : une liste de valeurs est attendue"
        raise DataError(message)
    return tuple(float(v) for v in value)


def expand_profile(
    profile: tuple[ProfilePoint, ...], step: float, family: str
) -> tuple[SpringLevel, ...]:
    """Spring of every node of a B3 profile: points grouped by `layer` (one plateau
    each, given by its top and bottom levels, or a single level), every node at
    `step` between the two levels, bounds included. kN/m -> N/m."""
    plateaus: dict[str, list[ProfilePoint]] = {}
    for point in profile:
        if point.layer is None:
            message = f"profil {family} : point sans palier (layer) à z = {point.z}"
            raise DataError(message)
        plateaus.setdefault(point.layer, []).append(point)
    out: list[SpringLevel] = []
    seen: set[float] = set()
    for name, points in plateaus.items():
        ks = {p.p for p in points}
        if len(ks) != 1:
            message = f"profil {family}, palier {name} : raideurs différentes {ks}"
            raise DataError(message)
        k = next(iter(ks)) * 1e3
        top = max(p.z for p in points)
        bottom = min(p.z for p in points)
        count = round((top - bottom) / step)
        if abs(count * step - (top - bottom)) > LEVEL_PRECISION:
            message = f"profil {family}, palier {name} : bornes non multiples du pas"
            raise DataError(message)
        for i in range(count + 1):
            z = round(top - i * step, 9)
            if z in seen:
                message = f"profil {family} : nœud {z} dans deux paliers"
                raise DataError(message)
            seen.add(z)
            out.append(SpringLevel(family=family, z=z, k=k))
    levels = sorted(seen, reverse=True)
    for upper, lower in zip(levels, levels[1:], strict=False):
        if abs(upper - lower - step) > LEVEL_PRECISION:
            message = f"profil {family} : nœud manquant entre {lower} et {upper}"
            raise DataError(message)
    return tuple(sorted(out, key=lambda s: -s.z))


def model_values(ctx: ProjectContext) -> ModelValues:
    """Every number of the model, from the data file, in m, N, Pa."""
    cached = ctx.cache.get("estacade_values")
    if isinstance(cached, ModelValues):
        return cached
    items = ctx.data().items()
    z_mid = _value(ctx, "geometrie.cote_plan_moyen", "m NGF")
    bottoms = _vector(items, "pieu.cotes_troncons")
    areas = _vector(items, "pieu.aires_troncons")
    inertias = _vector(items, "pieu.inerties_troncons")
    if not len(bottoms) == len(areas) == len(inertias):
        message = (
            "pieu : cotes, aires et inerties des tronçons de longueurs différentes"
        )
        raise DataError(message)
    tops = (z_mid, *bottoms[:-1])
    sections = tuple(
        Section(
            name=f"T{i}",
            z_top=top,
            z_bottom=bottom,
            area=a * 1e-4,
            inertia=inertia * 1e-8,
        )
        for i, (top, bottom, a, inertia) in enumerate(
            zip(tops, bottoms, areas, inertias, strict=True), start=1
        )
    )
    step = _value(ctx, "ressorts.pas_noeuds", "m")
    springs: list[SpringLevel] = []
    for family, key in (("RIVE", "ressorts.files_rive"), ("EAU", "ressorts.files_eau")):
        profile = items[key].profile
        if profile is None:
            message = f"{key} : un profil est attendu"
            raise DataError(message)
        springs.extend(expand_profile(profile, step, family))
    n_files = int(_value(ctx, "geometrie.nombre_files", "-"))
    x0 = _value(ctx, "geometrie.abscisse_premiere_file", "m")
    dx = _value(ctx, "geometrie.entraxe_files", "m")
    values = ModelValues(
        length=_value(ctx, "geometrie.longueur_tablier", "m"),
        width=_value(ctx, "geometrie.largeur_tablier", "m"),
        thickness=_value(ctx, "geometrie.epaisseur_dalle", "m"),
        z_mid=z_mid,
        x_files=tuple(round(x0 + dx * i, 9) for i in range(n_files)),
        y_piles=_value(ctx, "geometrie.ordonnee_pieux", "m"),
        lane=(
            _value(ctx, "geometrie.voie_y_min", "m"),
            _value(ctx, "geometrie.voie_y_max", "m"),
        ),
        guard_y=_value(ctx, "geometrie.ordonnee_garde_corps", "m"),
        cap_width=_value(ctx, "chevetre.largeur", "m"),
        cap_height=_value(ctx, "chevetre.hauteur", "m"),
        sections=sections,
        plug=(
            _value(ctx, "pieu.bouchon_cote_haute", "m NGF"),
            _value(ctx, "pieu.bouchon_cote_basse", "m NGF"),
        ),
        z_tip=_value(ctx, "pieu.cote_pointe", "m NGF"),
        springs=tuple(springs),
        spring_step=step,
        e_concrete=_value(ctx, "materiaux.beton_module", "GPa") * 1e9,
        nu_concrete=_value(ctx, "materiaux.beton_poisson", "-"),
        gamma_concrete=_value(ctx, "materiaux.beton_poids_volumique", "kN/m3") * 1e3,
        e_steel=_value(ctx, "materiaux.acier_module", "GPa") * 1e9,
        nu_steel=_value(ctx, "materiaux.acier_poisson", "-"),
        gamma_steel=_value(ctx, "materiaux.acier_poids_volumique", "kN/m3") * 1e3,
        alpha=_value(ctx, "materiaux.dilatation_beton", "1/°C"),
        gravity=_value(ctx, "modele.acceleration_pesanteur", "m/s2"),
        g2_sidewalk=_value(ctx, "charges.g2_trottoirs", "kPa") * 1e3,
        g2_lane=_value(ctx, "charges.g2_voie", "kPa") * 1e3,
        g2_guard=_value(ctx, "charges.g2_garde_corps", "kN/m") * 1e3,
        ts_wheel=_value(ctx, "charges.ts_charge_roue", "kN") * 1e3,
        ts_print=_value(ctx, "charges.ts_empreinte", "m"),
        ts_axle_spacing=_value(ctx, "charges.ts_entraxe_essieux", "m"),
        ts_wheel_spacing=_value(ctx, "charges.ts_entraxe_roues", "m"),
        ts_y_centred=_value(ctx, "charges.ts_ordonnee_axe", "m"),
        udl=_value(ctx, "charges.udl", "kPa") * 1e3,
        tr=_value(ctx, "charges.tr", "kPa") * 1e3,
        lm2_wheel=_value(ctx, "charges.lm2_charge_roue", "kN") * 1e3,
        lm2_print_x=_value(ctx, "charges.lm2_empreinte_x", "m"),
        lm2_print_y=_value(ctx, "charges.lm2_empreinte_y", "m"),
        lm2_wheel_spacing=_value(ctx, "charges.lm2_entraxe_roues", "m"),
        fr_total=_value(ctx, "charges.fr_total", "kN") * 1e3,
        delta_t=_value(ctx, "charges.delta_t", "°C"),
        moving_step=_value(ctx, "charges.pas_charge_mobile", "m"),
    )
    ctx.cache["estacade_values"] = values
    return values


def describe(values: ModelValues) -> dict[str, Any]:
    """Summary of the derived numbers, for the reports."""
    return {
        "files_x_m": list(values.x_files),
        "pieux": [p.name for p in values.piles()],
        "cotes_noeuds_pieu_m": list(values.pile_levels()),
        "troncons": [
            {
                "nom": s.name,
                "haut": s.z_top,
                "bas": s.z_bottom,
                "A_m2": s.area,
                "I_m4": s.inertia,
                "tube_R_m": s.equivalent_tube()[0],
                "tube_EP_m": s.equivalent_tube()[1],
                "I_sur_R_m3": s.section_modulus(),
            }
            for s in values.sections
        ],
        "ressorts": [
            {"famille": s.family, "z": s.z, "k_N_m": s.k, "groupe": s.group}
            for s in values.springs
        ],
    }


__all__ = [
    "DataError",
    "ModelValues",
    "Pile",
    "Section",
    "SpringLevel",
    "describe",
    "expand_profile",
    "model_values",
]
