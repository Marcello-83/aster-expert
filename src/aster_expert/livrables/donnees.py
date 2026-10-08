"""The arrays of the deliverables, as the container wrote them (lot 49).

`resultats/livrables/donnees/` holds, per declared field (`<key>.npz`), the raw arrays
of the MED fields -- elementary cases (`cas/<case>`), combinations (`comb/<i>/max`,
`.../min`, `.../max_pos`, `.../min_pos`) and envelopes (`env/...`) -- with the mapping
of their rows (`row_kind`: 0 node, 1 element-node, 2 Gauss point; `row_entity`,
`row_local`, `row_level`), plus the mesh (`maillage.npz`) and the loads
(`charges.npz`). Every query, view and table of the deliverables reads them here:
nothing is read from memory, nothing recomputed by Code_Aster.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.livrables.combinaisons import GenericCombination

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class FieldInfo:
    key: str
    field: str
    family: str
    components: tuple[str, ...]
    groups: tuple[str, ...]
    node_groups: tuple[str, ...]
    convention: str


@dataclass
class FieldArrays:
    info: FieldInfo
    kind: IntArray
    entity: IntArray
    local: IntArray
    level: IntArray
    arrays: dict[str, FloatArray] = field(default_factory=dict)

    def node_of_row(self, mesh: Mesh) -> IntArray:
        """Mesh node of each row (the node itself, or the node of the element)."""
        out = np.where(self.kind == 0, self.entity, -1)
        for level in np.unique(self.level[self.kind > 0]):
            rows = (self.kind > 0) & (self.level == level)
            conn = mesh.arrays[f"conn_{int(level)}"]
            out[rows] = conn[self.entity[rows], self.local[rows]]
        return out


@dataclass
class Mesh:
    arrays: dict[str, NDArray[Any]]

    @property
    def coords(self) -> FloatArray:
        """Coordinates with three components (a plane MED mesh stores two: Z = 0)."""
        coords = np.asarray(self.arrays["coords"], dtype=np.float64)
        if coords.shape[1] < 3:
            coords = np.hstack([coords, np.zeros((len(coords), 3 - coords.shape[1]))])
        return coords

    def node_group(self, name: str) -> IntArray:
        key = f"gno_{name}"
        if key in self.arrays:
            return self.arrays[key]
        cells = self.cell_group(name)
        if cells is None:
            message = f"groupe de nœuds {name} absent du maillage des livrables"
            raise KeyError(message)
        level, ids = cells
        conn = self.arrays[f"conn_{level}"][ids]
        return np.unique(conn[conn >= 0])

    def cell_group(self, name: str) -> tuple[int, IntArray] | None:
        for key, ids in self.arrays.items():
            if key.startswith("gma_") and key.split("_", 2)[2] == name:
                return int(key.split("_")[1]), ids
        return None

    def cell_groups_of(self, level: int, cell: int) -> list[str]:
        prefix = f"gma_{level}_"
        return [
            k[len(prefix) :]
            for k, ids in self.arrays.items()
            if k.startswith(prefix) and cell in set(ids.tolist())
        ]


class Deliverables:
    """Read access to `resultats/livrables/` of a project."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.data = root / "donnees"
        if not self.data.is_dir():
            message = f"livrables absents : {self.data} (projet <nom> livrables)"
            raise FileNotFoundError(message)

    @cached_property
    def plan(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(
            (self.root / "post" / "plan.json").read_text("utf-8")
        )
        return loaded

    @cached_property
    def spec(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(
            (self.root / "spec.json").read_text("utf-8")
        )
        return loaded

    @cached_property
    def container(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(
            (self.root / "conteneur.json").read_text("utf-8")
        )
        return loaded

    @cached_property
    def mesh(self) -> Mesh:
        with np.load(self.data / "maillage.npz") as npz:
            return Mesh({k: np.array(npz[k]) for k in npz.files})

    @cached_property
    def combinations(self) -> list[GenericCombination]:
        return [GenericCombination.model_validate(c) for c in self.spec["combinations"]]

    @cached_property
    def elementary(self) -> list[str]:
        return [c for c, i in self.spec["cases"].items() if i["elementary"]]

    def field_infos(self, declared: Any) -> list[FieldInfo]:
        """Declared fields (`DeliverablesSection.fields`) with their keys, in order."""
        first = self.plan["resultats"][0]["champs"]
        out = []
        for f, planned in zip(declared, first, strict=True):
            out.append(
                FieldInfo(
                    key=planned["cle"],
                    field=f.field,
                    family=f.family,
                    components=tuple(
                        self.container["champs"][planned["cle"]]["composantes"]
                    ),
                    groups=tuple(planned["groupes"]),
                    node_groups=tuple(planned["groupes_noeuds"]),
                    convention=f.convention,
                )
            )
        return out

    def field(self, info: FieldInfo) -> FieldArrays:
        with np.load(self.data / f"{info.key}.npz") as npz:
            arrays = {
                k: np.array(npz[k]) for k in npz.files if not k.startswith("row_")
            }
            return FieldArrays(
                info=info,
                kind=np.array(npz["row_kind"]),
                entity=np.array(npz["row_entity"]),
                local=np.array(npz["row_local"]),
                level=np.array(npz["row_level"]),
                arrays=arrays,
            )

    def loads(self) -> Iterator[tuple[str, FloatArray, IntArray, IntArray, list[str]]]:
        """(MED name, values, row kind, row entity, components) of each load field."""
        with np.load(self.data / "charges.npz") as npz:
            names = sorted(k[len("val/") :] for k in npz.files if k.startswith("val/"))
            info = self.container.get("charges", {})
            for name in names:
                yield (
                    name,
                    np.array(npz[f"val/{name}"]),
                    np.array(npz[f"row_kind/{name}"]),
                    np.array(npz[f"row_entity/{name}"]),
                    list(info.get(name, {}).get("composantes", [])),
                )


__all__ = ["Deliverables", "FieldArrays", "FieldInfo", "Mesh"]
