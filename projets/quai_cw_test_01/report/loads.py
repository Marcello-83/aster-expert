"""Charges appliquées par cas élémentaire, pour les vues (lot 36).

Calculées depuis les données du modèle par les mêmes fonctions que le générateur
(`quai_cw_test_01.generation.generate`, `quai_cw_test_01.generation.profiles`) : aucun
nombre n'est retapé ici. Ne sert qu'à représenter les charges (flèches) ; le calcul
lit les charges du `.comm`.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from aster_expert.agent.model_data import ModelData
from quai_cw_test_01.generation.generate import _sorted_points
from quai_cw_test_01.generation.profiles import integrate_profile
from quai_cw_test_01.generation.values import ModelValues


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BeamLoad(_Model):
    """Charge linéique de la décision 13 sur la hauteur de la poutre."""

    fy_per_m: float
    """N/m, selon Y (négatif : vers le bassin)."""
    mx_per_m: float
    """N.m/m, moment de transport à l'axe de la poutre."""
    fz_per_m: float | None = None
    """N/m, poids propre (cas G)."""


class AppliedLoads(_Model):
    pressure_pa: dict[str, list[tuple[float, float]]]
    """Pression normale à l'écran côté terre (points `(z, Pa)`), par cas : `G`, `Q1`,
    `EAU_P`, `EAU_A`."""
    beam: dict[str, BeamLoad]
    bollard_n: tuple[float, float, float]
    """`(FY, FZ, MX)` de l'amarrage (Q3), N et N.m."""
    defense_pa: float
    """Intensité de l'accostage (A), Pa, sur la surface développée de `DEFENSE`."""
    gravity: float
    beam_axis_z: float


def applied_loads(data: ModelData) -> AppliedLoads:
    mv = ModelValues(data)
    earth = "eau_terres.profil_poussee_terres_permanent"
    eau_p = [
        (z, p)
        for z, p, _, _ in sorted(
            mv.profile_si("eau_terres.profil_pression_eau_permanent")
        )
    ]
    eau_a = [
        (z, p)
        for z, p, _, _ in sorted(
            mv.profile_si("eau_terres.profil_pression_eau_accidentel")
        )
    ]
    pressure = {
        "G": _sorted_points(mv, earth, "G"),
        "Q1": _sorted_points(mv, earth, "Q1"),
        "EAU_P": eau_p,
        "EAU_A": eau_a,
    }
    z_low = mv.si("poutre_couronnement.cote_sous_face")
    z_high = mv.si("poutre_couronnement.cote_arase")
    axis = mv.si("poutre_couronnement.cote_centre_gravite")
    weight = (
        mv.si("poutre_couronnement.largeur")
        * mv.si("poutre_couronnement.hauteur")
        * mv.si("poutre_couronnement.masse_volumique")
        * mv.si("charges.acceleration_pesanteur")
    )
    beam: dict[str, BeamLoad] = {}
    for case, points in pressure.items():
        resultant, first_moment = integrate_profile(points, z_low, z_high)
        beam[case] = BeamLoad(
            fy_per_m=-resultant,
            mx_per_m=first_moment - axis * resultant,
            fz_per_m=-weight if case == "G" else None,
        )
    amarrage_fy = -mv.si("charges.amarrage_composante_horizontale")
    amarrage_fz = mv.si("charges.amarrage_effort") * math.sin(
        mv.si("charges.amarrage_inclinaison")
    )
    return AppliedLoads(
        pressure_pa=pressure,
        beam=beam,
        bollard_n=(
            amarrage_fy,
            amarrage_fz,
            mv.si("charges.amarrage_moment_transport"),
        ),
        defense_pa=0.0,
        gravity=mv.si("charges.acceleration_pesanteur"),
        beam_axis_z=axis,
    )


def defense_pressure(data: ModelData, defense_area: float) -> float:
    """Intensité de l'accostage rapportée à la surface développée de `DEFENSE`."""
    return ModelValues(data).si("charges.accostage_effort") / defense_area


__all__ = ["AppliedLoads", "BeamLoad", "applied_loads", "defense_pressure"]
