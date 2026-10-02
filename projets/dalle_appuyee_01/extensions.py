"""Extensions of the slab named by `projet.yaml` (lot 43): parameters of the mesh,
generator of the `.comm`, expected resultants of the load cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import DataRef
from dalle_appuyee_01.discretisation import SlabMesh
from dalle_appuyee_01.generation import build_comm, slab_values


def reference_mesh(ctx: ProjectContext) -> SlabMesh:
    """The finest mesh of the convergence series (point 10): the one of the
    project chain (`aster-expert projet dalle_appuyee_01`)."""
    items = ctx.data().items()
    sizes = items["maillage.tailles_convergence"].value
    if not isinstance(sizes, tuple):
        message = "maillage.tailles_convergence : une liste de tailles est attendue"
        raise ValueError(message)
    v = slab_values(ctx)
    return SlabMesh(length=v.length, width=v.width, size=min(float(s) for s in sizes))


def mesh_parameters(ctx: ProjectContext) -> bytes:
    return reference_mesh(ctx).parameters_bytes()


def generate(
    ctx: ProjectContext,
    *,
    fiche_path: Path,  # noqa: ARG001 -- la fiche est lue par le tronc commun (bloqueurs)
    data_path: Path,  # noqa: ARG001
    med_path: Path,
    aster_version: str,
) -> tuple[str, dict[str, Any]]:
    text, report = build_comm(ctx, mesh_label=med_path.name)
    report["aster_version"] = aster_version
    return text, report


def resultant(
    ctx: ProjectContext, case: str, **_inputs: Any
) -> dict[str, dict[str, float]]:
    """Applied load of a case (N, along -Z): computed from the data and compared
    with the value MM wrote (180,0 kN, 240,0 kN) -- both are reported."""
    v = slab_values(ctx)
    computed = {"G": -v.weight_resultant, "Q": -v.live_resultant}[case]
    key = {
        "G": "charges.resultante_poids_propre_attendue",
        "Q": "charges.resultante_exploitation_attendue",
    }[case]
    specified = -ctx.number(DataRef(data=key), unit="kN") * 1e3
    return {
        "as_evaluated": {"DX": 0.0, "DY": 0.0, "DZ": computed},
        "specified": {"DX": 0.0, "DY": 0.0, "DZ": specified},
    }
