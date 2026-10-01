"""Butée limite de Rankine côté terre et pression initiale au repos (lot 36).

Diagnostic seulement (décision 5, domaine de validité, items 3 et 4) : aucune de
ces grandeurs n'entre dans le modèle de calcul. Les paramètres sont ceux du cas de
test (`cas_test_quai_combiwall_v2.md`, §5 stratigraphie et §6 niveaux d'eau) ; les
profils qui s'en déduisent sont vérifiés par les tests contre les profils déjà
versionnés (butée côté bassin du lot 35, poussée active G de l'annexe A.4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    name: str
    top: float
    bottom: float
    gamma: float
    """kN/m³ au-dessus de la nappe."""
    gamma_sub: float
    """kN/m³ déjaugé, sous la nappe."""
    phi_deg: float
    cohesion: float
    """kPa."""

    @property
    def kp(self) -> float:
        return math.tan(math.radians(45.0 + self.phi_deg / 2.0)) ** 2

    @property
    def ka(self) -> float:
        return math.tan(math.radians(45.0 - self.phi_deg / 2.0)) ** 2


LAYERS = (
    Layer("remblai", 4.0, -2.0, 19.0, 10.0, 32.0, 0.0),
    Layer("sable", -2.0, -9.0, 20.0, 10.5, 35.0, 0.0),
    Layer("argile marneuse", -9.0, -18.0, 20.0, 10.5, 25.0, 15.0),
    Layer("marne compacte", -18.0, -35.0, 21.0, 11.5, 30.0, 40.0),
)
"""Stratigraphie du cas de test, §5."""

TERRE_GROUND = 4.0
"""Cote du terre-plein (m CM)."""
NAPPE_TERRE = 2.0
"""Nappe côté terre, niveau normal (§6, situation permanente du cas G)."""
FOOT = -26.0
"""Pied des tubes (m CM)."""
DREDGE = -12.0
"""Cote de dragage côté bassin, sol immergé au-dessous."""

BAND_LAYER = {"RESS_AV_ARGI": "argile marneuse", "RESS_AV_MARNE": "marne compacte"}


def layer_at(z: float, *, below: bool = True) -> Layer:
    """Couche de la cote `z` ; à une interface, la couche située dessous
    (`below`) ou dessus."""
    for layer in LAYERS:
        lo, hi = layer.bottom, layer.top
        inside = lo < z < hi
        edge = (z == hi and below) or (z == lo and not below)
        if inside or edge:
            return layer
    message = f"cote {z:g} hors de la stratigraphie"
    raise ValueError(message)


def _sigma_v(z: float, top: float, water: float) -> float:
    """Contrainte verticale effective (kPa) à la cote z, depuis la cote `top`,
    nappe à la cote `water` (γ au-dessus, γ' au-dessous)."""
    total = 0.0
    for layer in LAYERS:
        hi = min(layer.top, top)
        lo = max(layer.bottom, z)
        if hi <= lo:
            continue
        dry = max(0.0, hi - max(lo, water))
        wet = max(0.0, min(hi, water) - lo)
        total += layer.gamma * dry + layer.gamma_sub * wet
    return total


def sigma_v_terre(z: float) -> float:
    """σ'v côté terre à la cote z (kPa), nappe à `NAPPE_TERRE`."""
    return _sigma_v(z, TERRE_GROUND, NAPPE_TERRE)


def sigma_v_bassin(z: float) -> float:
    """σ'v côté bassin (kPa) : sol immergé sous `DREDGE`, γ' de chaque couche,
    aucune surcharge."""
    total = 0.0
    for layer in LAYERS:
        hi = min(layer.top, DREDGE)
        lo = max(layer.bottom, z)
        if hi > lo:
            total += layer.gamma_sub * (hi - lo)
    return total


def passive_terre(z: float, *, below: bool = True) -> float:
    """Kp·σ'v + 2c'√Kp côté terre (kPa), Rankine sans frottement."""
    layer = layer_at(z, below=below)
    return layer.kp * sigma_v_terre(z) + 2.0 * layer.cohesion * math.sqrt(layer.kp)


def passive_bassin(z: float, *, below: bool = True) -> float:
    layer = layer_at(z, below=below)
    return layer.kp * sigma_v_bassin(z) + 2.0 * layer.cohesion * math.sqrt(layer.kp)


def active_terre(z: float, *, below: bool = True) -> float:
    """Ka·σ'v − 2c'√Ka côté terre (kPa), non écrêtée : recoupe la poussée G."""
    layer = layer_at(z, below=below)
    return layer.ka * sigma_v_terre(z) - 2.0 * layer.cohesion * math.sqrt(layer.ka)


def k0_pressure_bassin(z: float, *, below: bool = True) -> float:
    """K0·σ'v côté bassin (kPa), K0 = 1 − sin φ' (V1 du lot 36)."""
    layer = layer_at(z, below=below)
    return (1.0 - math.sin(math.radians(layer.phi_deg))) * sigma_v_bassin(z)


def butee_terre_pa() -> dict[str, list[tuple[float, float]]]:
    """Profil de butée limite côté terre par bande de ressorts, en pascals, du haut
    vers le bas (format de `report.build._butee_pa`)."""
    out: dict[str, list[tuple[float, float]]] = {}
    for band, name in BAND_LAYER.items():
        layer = next(x for x in LAYERS if x.name == name)
        top = min(layer.top, DREDGE)
        bottom = max(layer.bottom, FOOT)
        out[band] = [
            (top, passive_terre(top, below=True) * 1.0e3),
            (bottom, passive_terre(bottom, below=False) * 1.0e3),
        ]
    return out


REPOS_TABLE_KPA = {
    "RESS_AV_ARGI": ((-12.0, 0.0), (-18.0, 36.4)),
    "RESS_AV_MARNE": ((-18.0, 31.5), (-26.0, 77.5)),
}
"""Pression initiale au repos côté bassin K0·σ'v de la variante V1 (lot 36), par
bande, points (z, kPa) du tableau de l'énoncé du lot : données fictives de
diagnostic. Le calcul `k0_pressure_bassin` les retrouve à 0,05 kPa près (le tableau
est arrondi à 0,1 kPa) ; ce sont les valeurs du tableau, non recalculées, que la
variante écrit."""
