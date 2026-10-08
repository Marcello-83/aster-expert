"""VTK XML unstructured grids (`.vtu`) of the deliverables, written and read back
(lot 49).

A standard ParaView (Windows included) reads `.vtu` without any plugin; the MED reader
is a plugin of the ParaView binaries only from 5.12 on (secondary source: ParaView
forum and Kitware superbuild, see `docs/essais_lot49.md`). Each deliverable MED is
therefore converted too, and the conversion is checked: every array read back from
the `.vtu` equals the source array, value for value (`check_identical`).

Format: VTK XML 0.1, `UnstructuredGrid`, binary data inline, base64, a header of one
`UInt64` (the byte count of the block), no compression, little endian. Arrays are
`Float64` (values) or `Int64` (indices); points are `Float64`. Every component is a
scalar array of its own, named `<prefix>_<COMPONENT>` (the convention of the ParaView
script of MM: `FN_<case>_DX`), so that a `Calculator` can rebuild any vector.
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

VTK_TYPES: dict[int, int] = {
    # MED geometric type (medcoupling NORM_*) -> VTK cell type.
    0: 1,  # NORM_POI1 -> VTK_VERTEX
    1: 3,  # NORM_SEG2 -> VTK_LINE
    3: 5,  # NORM_TRI3 -> VTK_TRIANGLE
    4: 9,  # NORM_QUAD4 -> VTK_QUAD
    14: 10,  # NORM_TETRA4 -> VTK_TETRA
    18: 12,  # NORM_HEXA8 -> VTK_HEXAHEDRON
    16: 13,  # NORM_PENTA6 -> VTK_WEDGE
}
_DTYPES: dict[str, np.dtype[Any]] = {
    "Float64": np.dtype("<f8"),
    "Int64": np.dtype("<i8"),
    "UInt8": np.dtype("u1"),
}


@dataclass
class Grid:
    points: NDArray[np.float64]
    connectivity: NDArray[np.int64]
    offsets: NDArray[np.int64]
    types: NDArray[np.uint8]
    point_data: dict[str, NDArray[np.float64]] = field(default_factory=dict)
    cell_data: dict[str, NDArray[np.float64]] = field(default_factory=dict)


def grid_from_mesh(
    mesh: Mapping[str, NDArray[np.int64]],
) -> tuple[Grid, list[tuple[int, int]]]:
    """The grid of every level of a MED mesh (`maillage.npz` of the container), and the
    (level, cell) of each VTK cell, in order."""
    conn: list[int] = []
    offsets: list[int] = []
    types: list[int] = []
    order: list[tuple[int, int]] = []
    levels = sorted(
        (int(k.split("_")[1]) for k in mesh if k.startswith("conn_")), reverse=True
    )
    for level in levels:
        cells = mesh[f"conn_{level}"]
        med_types = mesh[f"type_{level}"]
        for index, (row, med_type) in enumerate(zip(cells, med_types, strict=True)):
            vtk = VTK_TYPES.get(int(med_type))
            if vtk is None:
                message = f"type de maille MED {int(med_type)} non converti en VTK"
                raise ValueError(message)
            nodes = [int(n) for n in row if n >= 0]
            conn.extend(nodes)
            offsets.append(len(conn))
            types.append(vtk)
            order.append((level, index))
    points = np.asarray(mesh["coords"], dtype=np.float64)
    if points.shape[1] < 3:  # plane MED mesh: Z = 0
        points = np.hstack([points, np.zeros((len(points), 3 - points.shape[1]))])
    grid = Grid(
        points=points,
        connectivity=np.asarray(conn, dtype=np.int64),
        offsets=np.asarray(offsets, dtype=np.int64),
        types=np.asarray(types, dtype=np.uint8),
    )
    return grid, order


def _encode(array: NDArray[Any], dtype: np.dtype[Any]) -> str:
    data = np.ascontiguousarray(array, dtype=dtype).tobytes()
    header = np.array([len(data)], dtype="<u8").tobytes()
    return base64.b64encode(header + data).decode("ascii")


def _data_array(
    parent: ET.Element, name: str, array: NDArray[np.generic], type_name: str
) -> None:
    components = 1 if array.ndim == 1 else int(array.shape[1])
    element = ET.SubElement(
        parent,
        "DataArray",
        type=type_name,
        Name=name,
        NumberOfComponents=str(components),
        format="binary",
    )
    element.text = _encode(array, _DTYPES[type_name])


def _type_of(array: NDArray[np.generic]) -> str:
    return "Int64" if np.issubdtype(array.dtype, np.integer) else "Float64"


def write_vtu(path: Path, grid: Grid) -> None:
    root = ET.Element(
        "VTKFile",
        type="UnstructuredGrid",
        version="0.1",
        byte_order="LittleEndian",
        header_type="UInt64",
    )
    piece = ET.SubElement(
        ET.SubElement(root, "UnstructuredGrid"),
        "Piece",
        NumberOfPoints=str(len(grid.points)),
        NumberOfCells=str(len(grid.types)),
    )
    points = ET.SubElement(piece, "Points")
    _data_array(points, "Points", grid.points, "Float64")
    cells = ET.SubElement(piece, "Cells")
    _data_array(cells, "connectivity", grid.connectivity, "Int64")
    _data_array(cells, "offsets", grid.offsets, "Int64")
    _data_array(cells, "types", grid.types, "UInt8")
    pdata = ET.SubElement(piece, "PointData")
    for name, array in grid.point_data.items():
        _data_array(pdata, name, array, _type_of(array))
    cdata = ET.SubElement(piece, "CellData")
    for name, array in grid.cell_data.items():
        _data_array(cdata, name, array, _type_of(array))
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _decode(element: ET.Element) -> NDArray[Any]:
    raw = base64.b64decode(element.text or "")
    size = int(np.frombuffer(raw[:8], dtype="<u8")[0])
    dtype = _DTYPES[element.attrib["type"]]
    array = np.frombuffer(raw[8 : 8 + size], dtype=dtype).copy()
    components = int(element.attrib.get("NumberOfComponents", "1"))
    out: NDArray[Any] = array.reshape(-1, components) if components > 1 else array
    return out


def read_vtu(path: Path) -> Grid:
    piece = ET.parse(path).getroot().find("UnstructuredGrid/Piece")
    assert piece is not None
    points = piece.find("Points/DataArray")
    cells = {e.attrib["Name"]: e for e in piece.findall("Cells/DataArray")}
    assert points is not None
    grid = Grid(
        points=_decode(points).astype(np.float64),
        connectivity=_decode(cells["connectivity"]).astype(np.int64),
        offsets=_decode(cells["offsets"]).astype(np.int64),
        types=_decode(cells["types"]).astype(np.uint8),
    )
    for element in piece.findall("PointData/DataArray"):
        grid.point_data[element.attrib["Name"]] = _decode(element)
    for element in piece.findall("CellData/DataArray"):
        grid.cell_data[element.attrib["Name"]] = _decode(element)
    return grid


def check_identical(written: Grid, path: Path) -> dict[str, object]:
    """Read `path` back and compare every array with `written`, bit for bit (NaN equal
    to NaN). Returns the count of arrays and values compared and the differing names."""
    read = read_vtu(path)
    differing: list[str] = []
    values = 0
    pairs: list[tuple[str, NDArray[Any], NDArray[Any]]] = [
        ("Points", written.points, read.points),
        ("connectivity", written.connectivity, read.connectivity),
        ("offsets", written.offsets, read.offsets),
        ("types", written.types, read.types),
    ]
    for name, source, target in pairs:
        if not np.array_equal(source, target):
            differing.append(name)
    for kind, src, dst in (
        ("point", written.point_data, read.point_data),
        ("cell", written.cell_data, read.cell_data),
    ):
        for name, array in src.items():
            other = dst.get(name)
            values += array.size
            if other is None or not np.array_equal(array, other, equal_nan=True):
                differing.append(f"{kind}:{name}")
    return {
        "tableaux": len(written.point_data) + len(written.cell_data),
        "valeurs": values,
        "differents": differing,
        "identiques": not differing,
    }


__all__ = [
    "VTK_TYPES",
    "Grid",
    "check_identical",
    "grid_from_mesh",
    "read_vtu",
    "write_vtu",
]
