"""La synthèse relue dans le MED de résultats (lot 36).

`load_med_data` lit le MED par `medcoupling` dans le conteneur
(`aster_expert.report.med_read`) et charge les tableaux (`numpy`). `med_tables`
reconstitue, à partir d'eux, **les mêmes lignes** que les tables imprimées dans le
`.mess` (mêmes noms, mêmes colonnes) : les grandeurs de la synthèse
(`quai_cw_test_01.report.quantities`) sont donc calculées par le même code, quelle que
soit la source. `cross_check` compare les deux sources ; les tables du `.mess` ne
sont plus qu'une contre-vérification.

Numérotation : le nœud `N<k>` de Code_Aster est l'indice MED `k - 1` ; la maille
`M<k>` est numérotée à la suite, niveau 0 (coques), puis -1 (segments), puis -2
(ponctuels), dans l'ordre du fichier.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.report.med_read import med_field_name, run_med_script, take_arrays
from aster_expert.report.tables import Record
from quai_cw_test_01.generation import comm

CASES_QUANTITIES = ("DEPL", "REAC_NODA", "FORC_NODA")
"""Champs aux nœuds de chaque cas (`comm.footer`)."""

#: groupe de nœuds d'appui de chaque table de réactions -> nom du groupe MED
SUPPORT_GROUPS = {
    "ANCRAGES": "ANCRAGES",
    "PIED_TUBES": "PIED_TUBES",
    "SYM_G": "SYM_G",
    "SYM_D": "SYM_D",
}


@dataclass(frozen=True)
class MedData:
    """Le contenu utile d'un MED de résultats (indices MED, à partir de 0)."""

    path: Path
    coords: np.ndarray
    conn: dict[int, np.ndarray]
    node_groups: dict[str, np.ndarray]
    cell_groups: dict[int, dict[str, np.ndarray]]
    arrays: dict[str, np.ndarray]
    components: dict[str, list[str]]
    cases: tuple[str, ...]

    def offset(self, level: int) -> int:
        """Numéro (0) du premier élément du niveau dans la numérotation `M<k>`."""
        out = 0
        for lv in (0, -1, -2):
            if lv == level:
                return out
            out += len(self.conn.get(lv, ()))
        message = f"niveau de maillage inconnu : {level}"
        raise ValueError(message)

    def node_field(self, case: str, quantity: str) -> np.ndarray:
        """Champ aux nœuds `(n_nœuds, n_composantes)` du cas (complet : les nœuds
        hors profil valent 0)."""
        name = med_field_name(case, quantity)
        values = self.arrays[name]
        nodes = self.arrays.get(f"{name}#nodes")
        if nodes is None:
            return values
        full = np.zeros((len(self.coords), values.shape[1]))
        full[nodes] = values
        return full

    def comp(self, name: str, component: str) -> int:
        return self.components[name].index(component)


def field_names(cases: Iterable[str], *, palplanches: bool = True) -> list[str]:
    names: list[str] = []
    for case in cases:
        names += [med_field_name(case, q) for q in CASES_QUANTITIES]
        names.append(med_field_name(f"{case}_ET", "EFGE_ELNO"))
        if palplanches:
            names.append(med_field_name(f"{case}_EP", "EFGE_NOEU"))
    return names


def load_med_data(med: Path, cases: Sequence[str], **kwargs: Any) -> MedData:
    """Lit `med` (conteneur, `medcoupling`) : maillage, groupes et champs des cas."""
    payload = run_med_script(med, ["extract", *field_names(cases)], **kwargs)
    arrays = take_arrays(payload)
    conn = {
        int(k.split("_", 1)[1]): arrays.pop(k)
        for k in [k for k in arrays if k.startswith("conn_")]
    }
    groups = payload["groups"]
    return MedData(
        path=med,
        coords=arrays.pop("coords"),
        conn=conn,
        node_groups={
            k: np.asarray(v, dtype=np.int64) for k, v in groups["node"].items()
        },
        cell_groups={
            int(lv): {k: np.asarray(v, dtype=np.int64) for k, v in by.items()}
            for lv, by in groups["cell"].items()
        },
        arrays=arrays,
        components={k: v["components"] for k, v in payload["fields"].items()},
        cases=tuple(cases),
    )


def _rows(
    data: MedData,
    nodes: np.ndarray,
    columns: dict[str, np.ndarray],
    *,
    extra: dict[str, list[str]] | None = None,
) -> list[Record]:
    """Une ligne par nœud de `nodes` : `NOEUD`, `COOR_X/Y/Z` et `columns`."""
    out: list[Record] = []
    for i, node in enumerate(nodes):
        row: Record = {"NOEUD": str(int(node) + 1)}
        for axis, name in enumerate(("COOR_X", "COOR_Y", "COOR_Z")):
            row[name] = float(data.coords[node, axis])
        for name, values in columns.items():
            row[name] = float(values[i])
        for name, texts in (extra or {}).items():
            row[name] = texts[i]
        out.append(row)
    return out


def _elno_rows(
    data: MedData,
    field: str,
    level: int,
    group: str,
    components: Sequence[str],
) -> list[Record]:
    """Une ligne par (maille du groupe, nœud local) d'un champ ELNO : `MAILLE`,
    `NOEUD`, `COOR_X/Y/Z` et les composantes demandées."""
    values = data.arrays[f"{field}@{level}"]
    cells = data.arrays[f"{field}@{level}#cells"]
    conn = data.conn[level]
    wanted = {int(c) for c in data.cell_groups[level][group]}
    columns = [data.comp(field, c) for c in components]
    offset = data.offset(level)
    out: list[Record] = []
    row_index = 0
    for cell in cells:
        nodes = [int(n) for n in conn[int(cell)] if n >= 0]
        if int(cell) in wanted:
            for local, node in enumerate(nodes):
                row: Record = {
                    "MAILLE": str(offset + int(cell) + 1),
                    "NOEUD": str(node + 1),
                    "SOUS_POINT": 1.0,
                }
                for axis, name in enumerate(("COOR_X", "COOR_Y", "COOR_Z")):
                    row[name] = float(data.coords[node, axis])
                for name, col in zip(components, columns, strict=True):
                    row[name] = float(values[row_index + local, col])
                out.append(row)
        row_index += len(nodes)
    return out


def med_tables(
    data: MedData,
    names: Iterable[str],
    *,
    profile_tubes: Sequence[int],
) -> dict[str, list[Record]]:
    """Les lignes de chaque table de `names` (mêmes noms que `build._table_names`)."""
    wanted = set(names)
    tables: dict[str, list[Record]] = {}
    head = np.unique(
        np.concatenate(
            [v for k, v in data.node_groups.items() if k.startswith("TETE_TUBE_")]
        )
    )
    springs = np.unique(data.conn[-2].ravel())
    palp_nodes = data.node_groups["GEN_TOUS_PALPS"]
    for case in data.cases:
        dy = data.node_field(case, "DEPL")[:, 1]
        reac = data.node_field(case, "REAC_NODA")
        title = f"RESSORTS_{case}"
        if title in wanted:
            tables[title] = _rows(data, springs, {"DY": dy[springs]})
        title = comm.synthesis_title("tete", case)
        if title in wanted:
            tables[title] = _rows(data, head, {"DY": dy[head]})
        for tube in profile_tubes:
            title = comm.profile_title(tube, case)
            if title in wanted:
                nodes = data.node_groups[f"{comm.PROFILE_NODE_GROUP_PREFIX}{tube:02d}"]
                tables[title] = _rows(data, nodes, {"DY": dy[nodes]})
        for group, med_group in SUPPORT_GROUPS.items():
            title = comm.reaction_table_title(group, case)
            if title in wanted:
                total = reac[data.node_groups[med_group]].sum(axis=0)
                tables[title] = [
                    {
                        "DX": float(total[0]),
                        "DY": float(total[1]),
                        "DZ": float(total[2]),
                    }
                ]
        field = med_field_name(f"{case}_ET", "EFGE_ELNO")
        for kind, level, group, components in (
            ("tubes", 0, "TUBES", comm.TUBE_EFFORT_COMPONENTS),
            ("poutre", -1, "POUTRE_COUR", comm.BEAM_EFFORT_COMPONENTS),
            ("tirants", -1, "TIRANTS", comm.TIE_EFFORT_COMPONENTS),
        ):
            title = comm.synthesis_title(kind, case)
            if title in wanted:
                tables[title] = _elno_rows(data, field, level, group, components)
        title = comm.synthesis_title("palplanches", case)
        if title in wanted:
            name = med_field_name(f"{case}_EP", "EFGE_NOEU")
            values = data.arrays[name]
            nodes = data.arrays.get(f"{name}#nodes", np.arange(len(values)))
            keep = np.isin(nodes, palp_nodes)
            columns = {
                c: values[keep, data.comp(name, c)] for c in comm.PALP_EFFORT_COMPONENTS
            }
            tables[title] = _rows(data, nodes[keep], columns)
    return tables


def cross_check(
    from_med: dict[str, list[Record]], from_mess: dict[str, list[Record]]
) -> dict[str, float]:
    """Écart relatif maximal par table entre le MED et le `.mess` : pour chaque
    colonne numérique commune, les valeurs triées des deux sources, écart absolu
    maximal rapporté à l'amplitude de la colonne (`max |v|`, colonne nulle : écart
    absolu). Un nombre de lignes différent est une erreur, pas un écart."""
    out: dict[str, float] = {}
    for name, rows in from_med.items():
        other = from_mess[name]
        if len(rows) != len(other):
            message = (
                f"{name} : {len(rows)} lignes dans le MED, {len(other)} dans le .mess"
            )
            raise ValueError(message)
        worst = 0.0
        for column in rows[0]:
            if column in ("NOEUD", "MAILLE", "SOUS_POINT") or column not in other[0]:
                continue
            a = np.sort([float(r[column]) for r in rows])
            b = np.sort([float(r[column]) for r in other])
            scale = float(max(np.abs(a).max(), np.abs(b).max()))
            gap = float(np.abs(a - b).max())
            worst = max(worst, gap / scale if scale > 0.0 else gap)
        if not math.isfinite(worst):
            message = f"{name} : écart non fini"
            raise ValueError(message)
        out[name] = worst
    return out
