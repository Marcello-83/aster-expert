"""Build the trial cases of lot 24 (D6: generalised forces of a full ELAS_COQUE plate).

Fully synthetic, native ASCII mesh format, deterministic (a test replays it
byte for byte). Reuses the mesh writer of lot 22 and the tables of lot 23.
Files land in `data/examples/lot24_essais/`.

Square DKT plate (a x a, quadrangles) with the ELAS_COQUE set of decision 2 v5
(rigidities per metre of width, in SI units: MN -> 1e6 N), EPAIS = 13.85 mm and
RHO = 7850 kg/m3. L is the mesh Y axis and T the mesh X axis (`ANGL_REP =
(90, 0)`, the orientation lot 22 established as "T along the mesh X axis").

- D6a (`d6a`): membrane traction along T. Edge x = 0 held in X, edge x = a loaded
  by a line force q (N/m) along X. Reference: elongation q a / MEMB_T, NYY = q
  (local T normal force).
- D6b (`d6b`): cylindrical bending along T. Edges x = 0 and x = a simply supported
  (DZ = 0), uniform pressure p. Reference: w = 5 p a^4 / (384 FLEX_T),
  MYY = p a^2 / 8 at mid-span, |QY| = p a / 2 at the supports.
- D6b16 (`d6b16`): D6b on a 16 x 16 mesh (discretisation control).
- D6c (`d6c`): pure membrane shear. Self-equilibrated shear line forces tau on
  the four edges, minimal supports (node (0,0) fixed, node (a,0) held in Y).
  Reference: displacement u_x = gamma y with gamma = tau / MEMB_G_LT, |NXY| = tau.

In every case DZ, DRX, DRY and DRZ are imposed to zero on all nodes except D6b
(DZ free, DRZ imposed): the membrane cases isolate the membrane response.

Usage: python scripts/build_lot24_essais.py [--output-dir PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_lot22_essais as l22  # noqa: E402
import build_lot23_essais as l23  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "lot24_essais"

SIDE = 1.0  # m, side of the square plate
N = 8  # quadrangles per side
N_FINE = 16  # refined mesh of D6b (discretisation control)
EPAIS = 0.01385  # m, t * s / b = 9.5 mm * 1.458
# Decision 2 v5, SI (1 MN = 1e6 N): membrane MN/m, bending MN.m^2/m.
MATERIAL = {
    "MEMB_L": 2908.0e6,
    "MEMB_LT": 0.0,
    "MEMB_T": 0.081e6,
    "MEMB_G_LT": 526.0e6,
    "FLEX_L": 89.0e6,
    "FLEX_LT": 0.0,
    "FLEX_T": 0.0113e6,
    "FLEX_G_LT": 0.0084e6,
    "CISA_L": 526.0e6,
    "CISA_T": 526.0e6,
    "RHO": 7850.0,
}
ORIENTATION = "ANGL_REP=(90.0, 0.0)"

Q_TRACTION = 100.0  # N/m
P_PRESSURE = 100.0  # Pa
TAU_SHEAR = 1.0e5  # N/m


def plate_mesh(title: str, n: int = N) -> l22.Mesh:
    mesh = l22.Mesh(title)
    ids, quads = l22.grid(mesh, x0=0.0, y0=0.0, lx=SIDE, ly=SIDE, nx=n, ny=n)
    mesh.groups_ma["PLAQUE"] = [f"MA{q}" for q in quads]
    edges = {
        "BORD_X0": [(ids[(0, j)], ids[(0, j + 1)]) for j in range(n)],
        "BORD_XA": [(ids[(n, j)], ids[(N, j + 1)]) for j in range(n)],
        "BORD_Y0": [(ids[(i, 0)], ids[(i + 1, 0)]) for i in range(n)],
        "BORD_YA": [(ids[(i, n)], ids[(i + 1, N)]) for i in range(n)],
    }
    next_id = 1
    for name, segments in edges.items():
        members = []
        for pair in segments:
            mesh.segs[next_id] = pair
            members.append(f"SG{next_id}")
            next_id += 1
        mesh.groups_ma[name] = members
    mesh.groups_no["NX0"] = [ids[(0, j)] for j in range(n + 1)]
    mesh.groups_no["NXA"] = [ids[(n, j)] for j in range(n + 1)]
    mesh.groups_no["MILIEU"] = [ids[(n // 2, j)] for j in range(n + 1)]
    mesh.groups_no["COIN0"] = [ids[(0, 0)]]
    mesh.groups_no["COINA"] = [ids[(n, 0)]]
    mesh.groups_no["TOUS"] = sorted(mesh.nodes)
    return mesh


def _tables() -> str:
    out = [
        'T_DEPL = CREA_TABLE(\n    RESU=_F(RESULTAT=RESU, NOM_CHAM="DEPL", NUME_ORDRE=1, NOM_CMP=("DX", "DY", "DZ"), TOUT="OUI")\n)\n'
    ]
    out.append('IMPR_TABLE(TABLE=T_DEPL, UNITE=6, FORMAT_R="E20.12")\n')
    for field in ("EFGE_ELNO", "EFGE_NOEU"):
        out.append(
            f"""\
T_{field} = CREA_TABLE(
    RESU=_F(RESULTAT=RESU, NOM_CHAM="{field}", NUME_ORDRE=1, NOM_CMP=("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY"), TOUT="OUI")
)

IMPR_TABLE(TABLE=T_{field}, UNITE=6, FORMAT_R="E20.12")
"""
        )
    for group in ("NX0", "NXA", "TOUS"):
        out.append(
            l23._resultant(f"REAC_NODA_{group}", "REAC_NODA", group, f"T_R_{group}")
        )
    return "\n".join(out)


def _comm(name: str, comment: str, *, ddl_impo: str, load: str, n: int = N) -> str:
    return f"""\
# Essai D6 (lot 24), variante {name} -- {comment}
# Plaque carree DKT {SIDE} m x {SIDE} m, {n} x {n} quadrangles, EPAIS = {EPAIS} m,
# ELAS_COQUE de la decision 2 v5 (SI). L = axe Y du maillage, T = axe X.

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(MODELE=MO, COQUE=_F(GROUP_MA="PLAQUE", EPAIS={l22._num(EPAIS)}, {ORIENTATION}))

MAT = DEFI_MATERIAU(ELAS_COQUE=_F({l22._coefs(MATERIAL)}))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA="PLAQUE", MATER=MAT))

CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
{ddl_impo}
    ),
    {load}
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

RESU = CALC_CHAMP(
    reuse=RESU,
    RESULTAT=RESU,
    CONTRAINTE=("EFGE_ELNO", "EFGE_NOEU"),
    FORCE="REAC_NODA",
)

{_tables()}
FIN()
"""


_MEMBRANE_ONLY = '        _F(GROUP_NO="TOUS", DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),'


def d6a_comm() -> str:
    ddl = "\n".join(
        [
            _MEMBRANE_ONLY,
            '        _F(GROUP_NO="NX0", DX=0.0),',
            '        _F(GROUP_NO="COIN0", DY=0.0),',
        ]
    )
    return _comm(
        "d6a",
        f"traction de membrane selon T, q = {Q_TRACTION} N/m",
        ddl_impo=ddl,
        load=f'FORCE_ARETE=_F(GROUP_MA="BORD_XA", FX={l22._num(Q_TRACTION)}),',
    )


def d6b_comm(name: str = "d6b", n: int = N) -> str:
    ddl = "\n".join(
        [
            '        _F(GROUP_NO="TOUS", DRZ=0.0),',
            '        _F(GROUP_NO=("NX0", "NXA"), DZ=0.0),',
            '        _F(GROUP_NO="COIN0", DX=0.0, DY=0.0),',
            '        _F(GROUP_NO="COINA", DY=0.0),',
        ]
    )
    return _comm(
        name,
        f"flexion cylindrique selon T, appuis sur x = 0 et x = a, p = {P_PRESSURE} Pa, {n} x {n}",
        ddl_impo=ddl,
        n=n,
        load=f'PRES_REP=_F(GROUP_MA="PLAQUE", PRES={l22._num(P_PRESSURE)}),',
    )


def d6c_comm() -> str:
    ddl = "\n".join(
        [
            _MEMBRANE_ONLY,
            '        _F(GROUP_NO="COIN0", DX=0.0, DY=0.0),',
            '        _F(GROUP_NO="COINA", DY=0.0),',
        ]
    )
    tau = l22._num(TAU_SHEAR)
    minus = l22._num(-TAU_SHEAR)
    load = (
        "FORCE_ARETE=(\n"
        f'        _F(GROUP_MA="BORD_YA", FX={tau}),\n'
        f'        _F(GROUP_MA="BORD_Y0", FX={minus}),\n'
        f'        _F(GROUP_MA="BORD_XA", FY={tau}),\n'
        f'        _F(GROUP_MA="BORD_X0", FY={minus}),\n'
        "    ),"
    )
    return _comm(
        "d6c",
        f"cisaillement de membrane pur, tau = {TAU_SHEAR:g} N/m sur les quatre bords",
        ddl_impo=ddl,
        load=load,
    )


def cases() -> dict[str, tuple[l22.Mesh, str]]:
    return {
        "essai_d6a/d6a": (plate_mesh("Plaque D6a (lot 24)"), d6a_comm()),
        "essai_d6b/d6b": (plate_mesh("Plaque D6b (lot 24)"), d6b_comm()),
        "essai_d6b/d6b16": (
            plate_mesh("Plaque D6b, maillage raffine (lot 24)", N_FINE),
            d6b_comm("d6b16", N_FINE),
        ),
        "essai_d6c/d6c": (plate_mesh("Plaque D6c (lot 24)"), d6c_comm()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    for rel, (mesh, comm) in cases().items():
        stem = Path(rel)
        target = args.output_dir / stem
        target.parent.mkdir(parents=True, exist_ok=True)
        target.with_suffix(".mail").write_text(l22.write_mesh(mesh), encoding="utf-8")
        target.with_suffix(".comm").write_text(comm, encoding="utf-8")
        target.with_suffix(".export").write_text(
            l22.export_text(stem.name), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
