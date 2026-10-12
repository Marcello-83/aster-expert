"""Image du modèle filaire de PONTONS-ALU-01 (lot 50), tirée des points de construction
(pontons_alu_01.geometrie) : vue isométrique et vue en plan, liaisons rigides en rouge.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/image_maillage.py <sortie.png>
"""

import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from pontons_alu_01.geometrie import geometry  # noqa: E402

COLORS = {
    "POUTRES_PRINC": "#1f4e79",
    "MONTANTS": "#2e75b6",
    "DIAGONALES": "#5b9bd5",
    "PANNES_SEC": "#70ad47",
    "SUPPORTS": "#7f6000",
    "CHEVETRE": "#7f7f7f",
    "POTEAUX": "#404040",
}


def main() -> None:
    target = Path(sys.argv[1])
    g = geometry()
    fig = plt.figure(figsize=(14, 6))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    ax2 = fig.add_subplot(1, 2, 2)
    for m in g.members:
        xs, ys, zs = zip(*m.points, strict=True)
        ax.plot(xs, ys, zs, color=COLORS[m.family], lw=1.5)
        ax.scatter(xs, ys, zs, color=COLORS[m.family], s=4)
        ax2.plot(xs, ys, color=COLORS[m.family], lw=1.2)
    for a, b in g.links:
        ax.plot(*zip(a, b, strict=True), color="red", lw=1.0)
    for a, b in g.hinges:
        ax.plot(*zip(a, b, strict=True), color="orange", lw=1.0, ls="--")
    fx, fy, fz = g.footing_x, g.footing_y, g.footing_z
    for x in fx:
        ax.plot([x, x], [fy[0], fy[-1]], [fz, fz], color="#bfbfbf", lw=0.8)
    for y in fy:
        ax.plot([fx[0], fx[-1]], [y, y], [fz, fz], color="#bfbfbf", lw=0.8)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m NGF)")
    ax.set_box_aspect((7.0, 3.0, 2.3))
    ax.set_title(
        "Travée PONTONS-ALU-01 : barres, liaisons rigides (rouge), rotules (orange)"
    )
    ax2.set_aspect("equal")
    ax2.set_xlabel("X (m)")
    ax2.set_ylabel("Y (m)")
    ax2.set_title("Vue en plan : poutres, montants, diagonales, pannes (vert)")
    fig.tight_layout()
    fig.savefig(target, dpi=130)
    print(target)


if __name__ == "__main__":
    main()
