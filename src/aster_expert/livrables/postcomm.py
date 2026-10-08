"""The post-processing `.comm` of the deliverables (lot 49).

**Method.** The production `.comm` is kept byte for byte (the conservation rule of the
validation levels compares it, lot 45). The post-processing run executes a *copy* of
it in which blocks of outputs are inserted, never anything removed or changed:

- for every solve (`MECA_STATIQUE`, `MACRO_ELAS_MULT`), just before the `DETRUIRE` that
  frees its result (or before `FIN`), the fields the deliverables declare and the
  production did not compute (`CALC_CHAMP(reuse=...)`), then one `IMPR_RESU` to the
  working MED (every case of the result, `NOM_RESU_MED` = a token of the result,
  U7.05.21 « Opérande NOM_RESU_MED » : at most 8 characters, the MED field is the token
  completed to 8 characters by `_` followed by the Code_Aster field name);
- for every elementary case, the nodal forces equivalent to its loads:
  `CALC_VECT_ELEM(OPTION='CHAR_MECA', CHARGE=<loads of the case>, MODELE, CHAM_MATER,
  CARA_ELEM)` (U4.61.02 : `CHAM_MATER` « nécessaire en mécanique pour les chargements
  de pesanteur », `CARA_ELEM` for structural elements), assembled by `ASSE_VECTEUR` on
  a `NUME_DDL` of the model alone (U4.61.23, catalogue 17.4 : `VECT_ELEM`, `NUME_DDL`),
  written by `IMPR_RESU(CHAM_GD=..., NOM_CHAM_MED=...)` (U7.05.21 « Opérande
  NOM_CHAM_MED » : a string of 64 characters). Kinematic charges are left out (no
  second member of their own); a case whose material field carries command variables
  (temperature) gets the nodal forces of those variables (`OPTION='FORC_VARC'`) and its
  temperature fields themselves.

Why not read the archived results again (`POURSUITE`, `LIRE_RESU`)? The production
runs keep no base (`glob.*` is not archived), their MED does not hold the reactions,
the forces of the springs nor the loads, and the reactions of a `MACRO_ELAS_MULT`
result read back need the loads of each case (`EXCIT`), which a MED does not carry.
The copy recomputes the cases with the very same commands; the post-processing run is
accepted only if every table it prints (`IMPR_TABLE`, format `E20.12`) equals the
production one (`aster_expert.livrables.verification`).
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass, field

from aster_expert.livrables.inventaire import Inventory, Solve, SolveCase
from aster_expert.projet.declaration import DeliverableField, DeliverablesSection

TOKEN_PREFIX = "L49R"
"""`NOM_RESU_MED` of the n-th solve: `L49R` + 3 digits (7 characters, ≤ 8)."""
MED_NAME_MAX = 64


class PostCommError(ValueError):
    pass


def field_keys(fields: Iterable[DeliverableField]) -> list[str]:
    """Stable key of each declared field: its Code_Aster name, followed by `_2`, `_3`...
    for a field declared again on other groups."""
    seen: dict[str, int] = {}
    out = []
    for f in fields:
        k = seen.get(f.field, 0) + 1
        seen[f.field] = k
        out.append(f.field if k == 1 else f"{f.field}_{k}")
    return out


def case_field_name(case: str, key: str) -> str:
    """MED name of an elementary case's field in the deliverable MED."""
    name = f"CAS_{case}__{key}"
    if len(name) > MED_NAME_MAX:
        message = f"nom de champ MED de plus de {MED_NAME_MAX} caractères : {name}"
        raise PostCommError(message)
    return name


@dataclass(frozen=True)
class PlannedField:
    key: str
    field: str
    family: str
    groups: tuple[str, ...]
    node_groups: tuple[str, ...]
    components: tuple[str, ...]
    med_name: str


@dataclass(frozen=True)
class PlannedResult:
    result: str
    token: str
    command: str
    cases: tuple[tuple[str, int], ...]
    """(case name, `NUME_ORDRE`)."""
    fields: tuple[PlannedField, ...]


@dataclass(frozen=True)
class PlannedLoad:
    case: str
    kind: str
    """`forces` (CHAR_MECA), `forces_varc` (FORC_VARC) or `temperature`."""
    med_name: str
    charges: tuple[str, ...] = ()
    concept: str | None = None
    note: str | None = None


@dataclass
class PostPlan:
    work_unit: int
    loads_unit: int
    cases_unit: int
    results: list[PlannedResult] = field(default_factory=list)
    loads: list[PlannedLoad] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "unite_med_travail": self.work_unit,
            "unite_med_charges": self.loads_unit,
            "unite_med_cas": self.cases_unit,
            "resultats": [
                {
                    "resultat": r.result,
                    "jeton": r.token,
                    "commande": r.command,
                    "cas": [{"nom": n, "nume_ordre": o} for n, o in r.cases],
                    "champs": [
                        {
                            "cle": f.key,
                            "champ": f.field,
                            "famille": f.family,
                            "groupes": list(f.groups),
                            "groupes_noeuds": list(f.node_groups),
                            "composantes": list(f.components),
                            "nom_med": f.med_name,
                        }
                        for f in r.fields
                    ],
                }
                for r in self.results
            ],
            "charges": [
                {
                    "cas": load.case,
                    "nature": load.kind,
                    "nom_med": load.med_name,
                    "charges": list(load.charges),
                    "concept": load.concept,
                    "note": load.note,
                }
                for load in self.loads
            ],
            "notes": list(self.notes),
        }


def expand_groups(patterns: Iterable[str], known: Iterable[str]) -> tuple[str, ...]:
    """Groups of a deliverable: a name as is, or a pattern (`GEN_RESS_*`) expanded on
    the group names the `.comm` uses; a pattern that matches nothing is refused."""
    known = sorted(set(known))
    out: list[str] = []
    for pattern in patterns:
        if any(ch in pattern for ch in "*?["):
            found = [g for g in known if fnmatch.fnmatchcase(g, pattern)]
            if not found:
                message = f"livrables : le motif de groupes {pattern} ne désigne rien"
                raise PostCommError(message)
            out.extend(found)
        else:
            out.append(pattern)
    return tuple(dict.fromkeys(out))


def resolve_fields(
    deliverables: DeliverablesSection, known_groups: Iterable[str]
) -> tuple[DeliverableField, ...]:
    """The declared fields with their group patterns expanded."""
    known = list(known_groups)
    return tuple(
        f.model_copy(
            update={
                "groups": expand_groups(f.groups, known),
                "node_groups": expand_groups(f.node_groups, known),
            }
        )
        for f in deliverables.fields
    )


def field_tokens(token: str, fields: Iterable[DeliverableField]) -> list[str]:
    """`NOM_RESU_MED` of each declared field of a result: the result's token, followed
    by a letter for the second, third... occurrence of a same field (two occurrences
    of a field under one name would write the same MED field, DIAG-006)."""
    seen: dict[str, int] = {}
    out = []
    for f in fields:
        k = seen.get(f.field, 0)
        seen[f.field] = k + 1
        out.append(token if k == 0 else token + "ABCDEFGHIJ"[k])
    return out


def _free_units(used: set[int], count: int) -> list[int]:
    out: list[int] = []
    candidate = 91
    while len(out) < count:
        if candidate not in used:
            out.append(candidate)
        candidate += 1
    return out


def _tuple(values: Iterable[str]) -> str:
    items = [f'"{v}"' for v in values]
    return "(" + ", ".join(items) + ("," if len(items) == 1 else "") + ")"


def _missing_options(
    solve: Solve, fields: Iterable[DeliverableField], computed: set[str]
) -> list[str]:
    """One `CALC_CHAMP(reuse=...)` per option the production did not compute, on the
    union of the groups the deliverables declare for it (none: the whole model)."""
    groups: dict[str, set[str] | None] = {}
    for f in fields:
        option = f.field
        if option == "DEPL" or option in computed:
            continue
        if option == "SIEF_ELGA" and all(c.stores_sief for c in solve.cases):
            continue
        if option not in groups:
            groups[option] = set(f.groups) if f.groups else None
        elif groups[option] is not None:
            if f.groups:
                groups[option] |= set(f.groups)  # type: ignore[operator]
            else:
                groups[option] = None
    lines = []
    for option, where in groups.items():
        key = "FORCE" if option == "REAC_NODA" else "CONTRAINTE"
        restrict = f", GROUP_MA={_tuple(sorted(where))}" if where else ""
        lines.append(
            f"{solve.result} = CALC_CHAMP(reuse={solve.result}, "
            f'RESULTAT={solve.result}{restrict}, {key}=("{option}",))'
        )
    return lines


def _impr_occurrence(
    solve: Solve, f: DeliverableField, naming: str, order: int | None = None
) -> str:
    """One occurrence of `IMPR_RESU/RESU`; `naming` is `NOM_RESU_MED="..."` or
    `NOM_CHAM_MED="..."`, `order` selects one `NUME_ORDRE`."""
    parts = [f"RESULTAT={solve.result}"]
    if order is not None:
        parts.append(f"NUME_ORDRE={order}")
    parts += [naming, f'NOM_CHAM="{f.field}"']
    if f.components:
        parts.append(f"NOM_CMP={_tuple(f.components)}")
    if f.groups:
        parts.append(f"GROUP_MA={_tuple(f.groups)}")
    if f.node_groups:
        parts.append(f"GROUP_NO={_tuple(f.node_groups)}")
    # CARA_ELEM sert aux champs à sous-points (DIAG-005) ; donné pour SIEF_ELGA de
    # discrets, sans sous-points, il produit l'alarme MED2_13 (DIAG-028), fatale sous
    # DEBUT(ERREUR=_F(ALARME="EXCEPTION")).
    if solve.cara_elem and f.family != "ressorts":
        parts.append(f"CARA_ELEM={solve.cara_elem}")
    return "        _F(" + ", ".join(parts) + "),"


def load_med_name(prefix: str, case: str, suffix: str = "") -> str:
    name = f"{prefix}_{case}{suffix}"
    if len(name) > MED_NAME_MAX:
        message = f"nom de champ MED de plus de {MED_NAME_MAX} caractères : {name}"
        raise PostCommError(message)
    return name


def _load_block(
    inv: Inventory,
    solve: Solve,
    case: SolveCase,
    index: int,
    numbering: str,
    unit: int,
    plan: PostPlan,
) -> list[str]:
    lines: list[str] = []
    loads = inv.loads_of(case)
    mixed = [c for c in case.charges if inv.mixed(c)]
    if mixed:
        message = (
            f"cas {case.name} : charge(s) qui mêlent conditions cinématiques et "
            f"chargements, non séparables : {mixed}"
        )
        raise PostCommError(message)
    for c in case.charges:
        if c in inv.nonzero_imposed:
            plan.notes.append(
                f"cas {case.name} : déplacement imposé non nul ({c}, "
                f"{inv.nonzero_imposed[c]}) : non représenté par des forces"
            )
    # U4.61.02 and catalogue 17.4: with OPTION='CHAR_MECA', MODELE calls for
    # SOUS_STRUC (sub-structures); the model is known from the charges. FORC_VARC
    # requires MODELE and CHAM_MATER.
    materials = f"CHAM_MATER={solve.cham_mater}"
    if solve.cara_elem:
        materials += f", CARA_ELEM={solve.cara_elem}"
    common = f"MODELE={solve.modele}, {materials}"
    if loads:
        ve, fn = f"L49V{index:03d}", f"L49F{index:03d}"
        name = load_med_name("FN", case.name)
        lines += [
            f'{ve} = CALC_VECT_ELEM(OPTION="CHAR_MECA", '
            f"CHARGE={_tuple_concepts(loads)}, {materials})",
            f"{fn} = ASSE_VECTEUR(VECT_ELEM={ve}, NUME_DDL={numbering})",
            f'IMPR_RESU(FORMAT="MED", UNITE={unit}, '
            f'RESU=_F(CHAM_GD={fn}, NOM_CHAM_MED="{name}"))',
            f"DETRUIRE(NOM=({ve}, {fn}))",
        ]
        plan.loads.append(
            PlannedLoad(case=case.name, kind="forces", med_name=name, charges=loads)
        )
    varc = inv.varc.get(solve.cham_mater, ())
    if varc:
        ve, fn = f"L49W{index:03d}", f"L49G{index:03d}"
        name = load_med_name("FV", case.name)
        lines += [
            f'{ve} = CALC_VECT_ELEM(OPTION="FORC_VARC", {common})',
            f"{fn} = ASSE_VECTEUR(VECT_ELEM={ve}, NUME_DDL={numbering})",
            f'IMPR_RESU(FORMAT="MED", UNITE={unit}, '
            f'RESU=_F(CHAM_GD={fn}, NOM_CHAM_MED="{name}"))',
            f"DETRUIRE(NOM=({ve}, {fn}))",
        ]
        plan.loads.append(
            PlannedLoad(
                case=case.name,
                kind="forces_varc",
                med_name=name,
                note=(
                    "forces nodales équivalentes aux variables de commande "
                    f"({', '.join(sorted({v.nom_varc for v in varc}))}) du champ de "
                    f"matériau {solve.cham_mater} (FORC_VARC), autoéquilibrées"
                ),
            )
        )
        for k, source in enumerate(varc, 1):
            name = load_med_name("VARC", case.name, f"_{source.nom_varc}_{k}")
            if source.kind == "CHAM_GD":
                resu = f"CHAM_GD={source.concept}"
            else:
                resu = f'RESULTAT={source.concept}, NOM_CHAM="{source.nom_varc}"'
            lines.append(
                f'IMPR_RESU(FORMAT="MED", UNITE={unit}, '
                f'RESU=_F({resu}, NOM_CHAM_MED="{name}"))'
            )
            plan.loads.append(
                PlannedLoad(
                    case=case.name,
                    kind="temperature",
                    med_name=name,
                    concept=source.concept,
                    note=(
                        f"champ propre de la variable {source.nom_varc} "
                        f"({source.kind} {source.concept}, groupes "
                        f"{', '.join(source.groups) or 'tous'}) : une charge thermique "
                        "se représente par sa température, pas par une force"
                    ),
                )
            )
    if not loads and not varc:
        plan.notes.append(f"cas {case.name} : ni chargement ni variable de commande")
    return lines


def _tuple_concepts(names: Iterable[str]) -> str:
    items = list(names)
    return "(" + ", ".join(items) + ("," if len(items) == 1 else "") + ")"


def build_post_comm(
    production: str,
    inv: Inventory,
    deliverables: DeliverablesSection,
    *,
    mobile_cases: Iterable[str] = (),
    known_groups: Iterable[str] = (),
) -> tuple[str, PostPlan]:
    """The post-processing `.comm` (the production text with blocks inserted) and its
    plan (what each MED field holds)."""
    mobile = set(mobile_cases)
    fields = resolve_fields(deliverables, known_groups)
    work_unit, loads_unit, cases_unit = _free_units(inv.units, 3)
    plan = PostPlan(work_unit=work_unit, loads_unit=loads_unit, cases_unit=cases_unit)
    keys = field_keys(fields)
    inserts: dict[int, list[str]] = {}
    numberings: dict[str, str] = {}
    load_index = 0
    for number, solve in enumerate(inv.solves, 1):
        token = f"{TOKEN_PREFIX}{number:03d}"
        block = [
            "",
            f"# --- Lot 49, livrables : résultat {solve.result} "
            f"({len(solve.cases)} cas), ajouté au .comm de production ---",
        ]
        block += _missing_options(solve, fields, inv.computed.get(solve.result, set()))
        tokens = field_tokens(token, fields)
        occurrences = [
            _impr_occurrence(solve, f, f'NOM_RESU_MED="{tk}"')
            for f, tk in zip(fields, tokens, strict=True)
        ]
        block += [
            f'IMPR_RESU(FORMAT="MED", UNITE={work_unit}, RESU=(',
            *occurrences,
            "))",
        ]
        plan.results.append(
            PlannedResult(
                result=solve.result,
                token=token,
                command=solve.command,
                cases=tuple((c.name, c.order) for c in solve.cases),
                fields=tuple(
                    PlannedField(
                        key=key,
                        field=f.field,
                        family=f.family,
                        groups=f.groups,
                        node_groups=f.node_groups,
                        components=f.components,
                        med_name=tk.ljust(8, "_") + f.field,
                    )
                    for f, tk, key in zip(fields, tokens, keys, strict=True)
                ),
            )
        )
        elementary = [c for c in solve.cases if c.name not in mobile]
        if elementary:
            block.append(f'IMPR_RESU(FORMAT="MED", UNITE={cases_unit}, RESU=(')
            for case in elementary:
                for f, key in zip(fields, keys, strict=True):
                    name = case_field_name(case.name, key)
                    block.append(
                        _impr_occurrence(
                            solve, f, f'NOM_CHAM_MED="{name}"', order=case.order
                        )
                    )
            block.append("))")
        if solve.modele not in numberings:
            numberings[solve.modele] = f"L49N{len(numberings) + 1:03d}"
            block.append(
                f"{numberings[solve.modele]} = NUME_DDL(MODELE={solve.modele})"
            )
        for case in solve.cases:
            if case.name in mobile:
                continue
            load_index += 1
            block += _load_block(
                inv, solve, case, load_index, numberings[solve.modele], loads_unit, plan
            )
        block.append("")
        at = inv.destroyed_at.get(solve.result, inv.fin_line)
        if at < solve.line_start:
            message = f"{solve.result} détruit avant sa résolution (ligne {at})"
            raise PostCommError(message)
        inserts.setdefault(at, []).extend(block)
    lines = production.splitlines()
    out: list[str] = [
        "# Lot 49 -- .comm de post-traitement des livrables : copie du .comm de",
        "# production, inchangé, dans laquelle des blocs de sorties sont insérés",
        "# (aster_expert.livrables.postcomm). Ne pas éditer.",
    ]
    for number, line in enumerate(lines, 1):
        if number in inserts:
            out.extend(inserts[number])
        out.append(line)
    return "\n".join(out) + "\n", plan


__all__ = [
    "MED_NAME_MAX",
    "PlannedField",
    "PlannedLoad",
    "PlannedResult",
    "PostCommError",
    "PostPlan",
    "build_post_comm",
    "case_field_name",
    "field_keys",
    "expand_groups",
    "field_tokens",
    "resolve_fields",
    "load_med_name",
]
