"""VTK XML unstructured grids (`.vtu`) of the deliverables, written and read back
(lot 49).

A standard ParaView (Windows included) reads `.vtu` without any plugin; the MED reader
is a plugin of the ParaView binaries only from 5.12 on (secondary source: ParaView
forum and Kitware superbuild, see `docs/essais_lot49.md`). Each deliverable MED is
therefore converted too, and the conversion is checked: every array read back from
the `.vtu` equals the source array, value for value (`check_identical`).

Format: VTK XML 0.1, `UnstructuredGrid`, data **appended raw** (`<AppendedData
encoding="raw">`, each block preceded by its byte count as a `UInt64`), little endian,
no compression -- a third smaller than inline base64. Arrays are `Float64` (values)
or `Int64` (indices); points are `Float64`. Every component is a scalar array of its
own, named `<prefix>_<COMPONENT>` (the convention of the ParaView script of MM:
`FN_<case>_DX`), so that a `Calculator` can rebuild any vector.
"""

from __future__ import annotations

import re
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
_MARKER = b'<AppendedData encoding="raw">'


@dataclass
class Grid:
    points: NDArray[np.float64]
    connectivity: NDArray[np.int64]
    offsets: NDArray[np.int64]
    types: NDArray[np.uint8]
    point_data: dict[str, NDArray[Any]] = field(default_factory=dict)
    cell_data: dict[str, NDArray[Any]] = field(default_factory=dict)


def grid_from_mesh(
    mesh: Mapping[str, NDArray[Any]],
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


def select_cells(grid: Grid, cells: NDArray[np.int64]) -> Grid:
    """The same points with only `cells` (VTK cell indices, in this order)."""
    starts = np.concatenate([[0], grid.offsets[:-1]])
    conn: list[NDArray[np.int64]] = []
    offsets: list[int] = []
    total = 0
    for cell in cells:
        nodes = grid.connectivity[starts[cell] : grid.offsets[cell]]
        conn.append(nodes)
        total += len(nodes)
        offsets.append(total)
    return Grid(
        points=grid.points,
        connectivity=(
            np.concatenate(conn) if conn else np.zeros(0, dtype=np.int64)
        ).astype(np.int64),
        offsets=np.asarray(offsets, dtype=np.int64),
        types=grid.types[cells].astype(np.uint8),
    )


def vertices(points: NDArray[np.float64], nodes: NDArray[np.int64]) -> Grid:
    """A grid of the points `nodes` only, one vertex cell each."""
    return Grid(
        points=points[nodes],
        connectivity=np.arange(len(nodes), dtype=np.int64),
        offsets=np.arange(1, len(nodes) + 1, dtype=np.int64),
        types=np.full(len(nodes), 1, dtype=np.uint8),
    )


def _type_of(array: NDArray[Any]) -> str:
    return "Int64" if np.issubdtype(array.dtype, np.integer) else "Float64"


class _Appender:
    def __init__(self) -> None:
        self.blocks: list[bytes] = []
        self.offset = 0

    def add(
        self, parent: ET.Element, name: str, array: NDArray[Any], type_name: str
    ) -> None:
        data = np.ascontiguousarray(array, dtype=_DTYPES[type_name]).tobytes()
        components = 1 if array.ndim == 1 else int(array.shape[1])
        ET.SubElement(
            parent,
            "DataArray",
            type=type_name,
            Name=name,
            NumberOfComponents=str(components),
            format="appended",
            offset=str(self.offset),
        )
        block = np.array([len(data)], dtype="<u8").tobytes() + data
        self.blocks.append(block)
        self.offset += len(block)


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
    appender = _Appender()
    appender.add(ET.SubElement(piece, "Points"), "Points", grid.points, "Float64")
    cells = ET.SubElement(piece, "Cells")
    appender.add(cells, "connectivity", grid.connectivity, "Int64")
    appender.add(cells, "offsets", grid.offsets, "Int64")
    appender.add(cells, "types", grid.types, "UInt8")
    pdata = ET.SubElement(piece, "PointData")
    for name, array in grid.point_data.items():
        appender.add(pdata, name, array, _type_of(array))
    cdata = ET.SubElement(piece, "CellData")
    for name, array in grid.cell_data.items():
        appender.add(cdata, name, array, _type_of(array))
    header = ET.tostring(root, encoding="unicode")
    assert header.endswith("</VTKFile>")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b'<?xml version="1.0"?>\n')
        handle.write(header[: -len("</VTKFile>")].encode("utf-8"))
        handle.write(b"\n  " + _MARKER + b"\n   _")
        for block in appender.blocks:
            handle.write(block)
        handle.write(b"\n  </AppendedData>\n</VTKFile>\n")


def read_vtu(path: Path) -> Grid:
    raw = path.read_bytes()
    start = raw.index(_MARKER)
    data_start = raw.index(b"_", start + len(_MARKER)) + 1
    header = raw[:start].decode("utf-8") + "</VTKFile>"
    header = re.sub(r"^<\?xml[^>]*\?>", "", header).strip()
    piece = ET.fromstring(header).find("UnstructuredGrid/Piece")
    assert piece is not None

    def decode(element: ET.Element) -> NDArray[Any]:
        offset = data_start + int(element.attrib["offset"])
        size = int(np.frombuffer(raw[offset : offset + 8], dtype="<u8")[0])
        array = np.frombuffer(
            raw[offset + 8 : offset + 8 + size], dtype=_DTYPES[element.attrib["type"]]
        ).copy()
        components = int(element.attrib.get("NumberOfComponents", "1"))
        out: NDArray[Any] = array.reshape(-1, components) if components > 1 else array
        return out

    points = piece.find("Points/DataArray")
    assert points is not None
    cells = {e.attrib["Name"]: e for e in piece.findall("Cells/DataArray")}
    grid = Grid(
        points=decode(points).astype(np.float64),
        connectivity=decode(cells["connectivity"]).astype(np.int64),
        offsets=decode(cells["offsets"]).astype(np.int64),
        types=decode(cells["types"]).astype(np.uint8),
    )
    for element in piece.findall("PointData/DataArray"):
        grid.point_data[element.attrib["Name"]] = decode(element)
    for element in piece.findall("CellData/DataArray"):
        grid.cell_data[element.attrib["Name"]] = decode(element)
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
    "select_cells",
    "vertices",
    "write_vtu",
]
