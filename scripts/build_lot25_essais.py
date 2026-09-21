"""Build the trial cases of lot 25 (D7: ELAS_COQUE axes on a vertical shell).

Fully synthetic, native ASCII mesh format, deterministic (a test replays it byte
for byte). Reuses the mesh writer of lot 22. Files land in
`data/examples/lot25_essais/`.

Vertical cantilever plate in the XZ plane of the global frame (decision of point 9:
X along the quay, Y towards the land, Z vertical), X in [0, 1] m, Z in [0, H] m,
DKT quadrangles, ELAS_COQUE set of decision 2 v5 (SI). Clamped at Z = 0, line force
q along +Y (perpendicular to the plate) on the edge Z = H. Criterion and
references: `docs/essais_lot25.md`, written before the runs.

- D7a (`d7a`, `d7a16`): `VECTEUR = (0, 0, 1)`, L expected along Z (8 x 8, 16 x 16).
- D7b (`d7b`, `d7b16`): `VECTEUR = (1, 0, 0)`, L expected along X (counter-test).
- D7c (`d7c`): `ANGL_REP = (0, -90)`, same orientation as D7a expected.

The membrane and normal-rotation degrees of freedom carry no load: DRY (drilling,
without stiffness in DKT) is imposed to zero on all nodes.

Usage: python scripts/build_lot25_essais.py [--output-dir PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_lot22_essais as l22  # noqa: E402
import build_lot24_essais as l24  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "lot25_essais"

WIDTH = 1.0  # m, plate extent along X
HEIGHT = 1.0  # m, plate extent along Z
N = 8  # quadrangles per side
N_FINE = 16  # refined mesh (factor 2)
Q_LINE = 100.0  # N/m, line force along +Y on the edge Z = HEIGHT
EPAIS = l24.EPAIS
MATERIAL = l24.MATERIAL


def plate_mesh(title: str, n: int = N) -> l22.Mesh:
    """`n` x `n` QUAD4 grid in the XZ plane (Y = 0), normal along -Y."""
    flat = l22.Mesh(title)
    ids, quads = l22.grid(flat, x0=0.0, y0=0.0, lx=WIDTH, ly=HEIGHT, nx=n, ny=n)
    mesh = l22.Mesh(title)
    mesh.nodes = {nid: (x, 0.0, y) for nid, (x, y, _) in flat.nodes.items()}
    mesh.quads = dict(flat.quads)
    mesh.groups_ma["PLAQUE"] = [f"MA{q}" for q in quads]
    for i in range(n):
        mesh.segs[i + 1] = (ids[(i, n)], ids[(i + 1, n)])
    mesh.groups_ma["BORD_HAUT"] = [f"SG{m}" for m in sorted(mesh.segs)]
    mesh.groups_no["NBASE"] = [ids[(i, 0)] for i in range(n + 1)]
    mesh.groups_no["NHAUT"] = [ids[(i, n)] for i in range(n + 1)]
    mesh.groups_no["TOUS"] = sorted(mesh.nodes)
    return mesh


def _comm(name: str, comment: str, orientation: str, n: int) -> str:
    return f"""\
# Essai D7 (lot 25), variante {name} -- {comment}
# Console verticale DKT dans le plan XZ, {n} x {n} quadrangles, EPAIS = {EPAIS} m,
# ELAS_COQUE de la decision 2 v5 (SI), effort lineique {Q_LINE} N/m selon +Y en tete.

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(MODELE=MO, COQUE=_F(GROUP_MA="PLAQUE", EPAIS={l22._num(EPAIS)}, {orientation}))

MAT = DEFI_MATERIAU(ELAS_COQUE=_F({l22._coefs(MATERIAL)}))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA="PLAQUE", MATER=MAT))

CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        _F(GROUP_NO="TOUS", DRY=0.0),
        _F(GROUP_NO="NBASE", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRZ=0.0),
    ),
    FORCE_ARETE=_F(GROUP_MA="BORD_HAUT", FY={l22._num(Q_LINE)}),
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, CONTRAINTE="EFGE_NOEU")

T_DEPL = CREA_TABLE(
    RESU=_F(RESULTAT=RESU, NOM_CHAM="DEPL", NUME_ORDRE=1, NOM_CMP=("DX", "DY", "DZ"), TOUT="OUI")
)

IMPR_TABLE(TABLE=T_DEPL, UNITE=6, FORMAT_R="E20.12")

T_EFGE_NOEU = CREA_TABLE(
    RESU=_F(RESULTAT=RESU, NOM_CHAM="EFGE_NOEU", NUME_ORDRE=1, NOM_CMP=("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY"), TOUT="OUI")
)

IMPR_TABLE(TABLE=T_EFGE_NOEU, UNITE=6, FORMAT_R="E20.12")

FIN()
"""


def cases() -> dict[str, tuple[l22.Mesh, str]]:
    def case(name: str, comment: str, orientation: str, n: int):
        return (
            plate_mesh(f"Console verticale {name} (lot 25)", n),
            _comm(name, comment, orientation, n),
        )

    a = "VECTEUR=(0.0, 0.0, 1.0)"
    b = "VECTEUR=(1.0, 0.0, 0.0)"
    c = "ANGL_REP=(0.0, -90.0)"
    return {
        "essai_d7a/d7a": case("d7a", "VECTEUR selon Z, L attendu selon Z", a, N),
        "essai_d7a/d7a16": case("d7a16", "VECTEUR selon Z, maillage 16", a, N_FINE),
        "essai_d7b/d7b": case("d7b", "VECTEUR selon X, L attendu selon X", b, N),
        "essai_d7b/d7b16": case("d7b16", "VECTEUR selon X, maillage 16", b, N_FINE),
        "essai_d7c/d7c": case("d7c", "ANGL_REP (0, -90), meme axe que D7a", c, N),
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
