"""Structured numerical data of a model to generate (lot 25).

The generator of `.comm` files and meshes cannot rely on prose: every number it
needs is a `DataValue` in a YAML file validated here, carrying its value, its
unit, its source (a section of the test case, or the `point_label` of a fiche
decision or finding) and an optional comment. A value no source states is kept
absent -- `status="a_fournir"`, no value -- and blocks the generation
(`ModelData.missing_values`, merged by `HypothesesSheet.generation_blockers`).
Nothing is invented, converted or derived in the file: values keep the unit of
their source (MN, kN, cm, mm, degrees); the conversion to SI is the generator's.

`check_consistency` confronts every value whose source is a decision (or a
Code_Aster finding, or a test-case section) with the text of that source: the
number must appear there, in French notation (decimal comma, thousands
separator, sign, number written in words for small counts), within the rounding
of the digits displayed. It reports discrepancies, it never corrects them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    HypothesesSheet,
    PracticeHypothesisEntry,
)

Scalar = float | int | str


class ValueSource(BaseModel):
    """Where a value was copied from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["cas_test", "decision", "constat"]
    document: str | None = None
    """`cas_test`: versioned file name in the project's sources directory
    (`data_sources` of its declaration, lot 41)."""
    section: str | None = None
    """`cas_test`: section of that file, e.g. `§2`."""
    point_label: str | None = None
    """`decision` (decided `pratique` entries) and `constat` (`code_aster`)."""
    topic_prefix: str | None = None
    """`constat`: start of the entry's topic, to pick it among the point's."""

    @model_validator(mode="after")
    def _fields_match_kind(self) -> ValueSource:
        if self.kind == "cas_test":
            if not self.document or not self.section:
                message = "source cas_test : `document` et `section` sont requis"
                raise ValueError(message)
            if self.point_label or self.topic_prefix:
                message = "source cas_test : pas de `point_label` ni de `topic_prefix`"
                raise ValueError(message)
        else:
            if not self.point_label:
                message = f"source {self.kind} : `point_label` est requis"
                raise ValueError(message)
            if self.document or self.section:
                message = f"source {self.kind} : pas de `document` ni de `section`"
                raise ValueError(message)
            if self.kind == "decision" and self.topic_prefix:
                message = "source decision : pas de `topic_prefix`"
                raise ValueError(message)
            if self.kind == "constat" and not self.topic_prefix:
                message = "source constat : `topic_prefix` est requis"
                raise ValueError(message)
        return self

    def label(self) -> str:
        if self.kind == "cas_test":
            return f"{self.document} {self.section}"
        return f"{self.kind} du point {self.point_label}"


class ProfilePoint(BaseModel):
    """One point (Z, p) of a piecewise-linear profile (lot 27).

    A discontinuity at an interface is two points of the same `z`, one per layer.
    How a discontinuity reaches Code_Aster is the generator's, not settled here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    z: float
    """Level, in the unit `z_unit` of the value (m CM)."""
    p: float
    """Pressure, in the unit of the value."""
    layer: str | None = None
    """Layer of the point (`remblai`, `sable`, ...), when the profile has any."""
    component: str | None = None
    """Series of the source table (`G`, `Q1`), when it gives several."""


class DataValue(BaseModel):
    """One number (or short text, or profile) of the model, with unit and source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["fourni", "a_fournir"]
    value: Scalar | tuple[float, ...] | None = None
    profile: tuple[ProfilePoint, ...] | None = None
    """A profile as an array of points (Z, p): alternative to `value`."""
    unit: str
    source: ValueSource | None = None
    required_by: str | None = None
    """`a_fournir`: `point_label` of the fiche point that calls for the value."""
    comment: str | None = None

    @model_validator(mode="after")
    def _status_is_coherent(self) -> DataValue:
        if self.status == "fourni":
            if (self.value is None) == (self.profile is None) or self.source is None:
                message = (
                    "valeur `fourni` : `source` et un seul de `value` ou `profile` "
                    "sont requis"
                )
                raise ValueError(message)
            if self.required_by is not None:
                message = "valeur `fourni` : `required_by` n'a pas de sens"
                raise ValueError(message)
        else:
            if (
                self.value is not None
                or self.profile is not None
                or self.source is not None
            ):
                message = (
                    "valeur `a_fournir` : ni `value`, ni `profile`, ni `source` -- une "
                    "valeur absente de toutes les sources reste absente"
                )
                raise ValueError(message)
            if not self.required_by or not self.comment:
                message = (
                    "valeur `a_fournir` : `required_by` et `comment` (ce que les "
                    "sources disent et ne disent pas) sont requis"
                )
                raise ValueError(message)
        return self


class ModelData(BaseModel):
    """The structured data file of one model (lot 25)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project: str
    case_reference: str
    groups: dict[str, dict[str, DataValue]]

    def items(self) -> dict[str, DataValue]:
        """Every value under its dotted name `group.key`."""
        return {
            f"{group}.{key}": value
            for group, values in self.groups.items()
            for key, value in values.items()
        }

    def missing_values(self) -> tuple[str, ...]:
        """Generation blockers: the values still to provide."""
        return tuple(
            f"valeur à fournir (point {v.required_by}) : {name} [{v.unit}] -- "
            f"{v.comment}"
            for name, v in self.items().items()
            if v.status == "a_fournir"
        )


def load_model_data(path: Path) -> ModelData:
    """Read and validate a data file."""
    return ModelData.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# --- consistency with the sources ------------------------------------------------

_SPACES = "   "
_NUMBER = re.compile(
    rf"(?<![\w.,])([+\-−±]?)"
    rf"(\d{{1,3}}(?:[{_SPACES}]\d{{3}})+|\d+)"
    rf"(?:[,.](\d+))?"
)
_WORDS = {
    "nul": 0,
    "nuls": 0,
    "nulle": 0,
    "nulles": 0,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
}


class Discrepancy(BaseModel):
    """A value not found in its source."""

    model_config = ConfigDict(frozen=True)

    name: str
    value: Scalar | tuple[float, ...]
    source: str
    reason: str

    def __str__(self) -> str:
        return f"{self.name} = {self.value!r} ({self.source}) : {self.reason}"


def numbers_in(text: str) -> list[tuple[float, int]]:
    """Numbers of a French text with the number of decimals displayed.

    Handles the decimal comma, the thousands separator (space, no-break space,
    narrow no-break space), the signs `+`, `-`, `−` (U+2212) and `±` (read as
    positive), and the small integers written in words.
    """
    found: list[tuple[float, int]] = []
    for match in _NUMBER.finditer(text):
        sign, integer, decimals = match.groups()
        digits = re.sub(f"[{_SPACES}]", "", integer)
        value = float(f"{digits}.{decimals}" if decimals else digits)
        found.append((-value if sign in ("-", "−") else value, len(decimals or "")))
    for word in re.findall(r"[a-zé]+", text.lower()):
        if word in _WORDS:
            found.append((float(_WORDS[word]), 0))
    return found


def _appears(value: float, text: str) -> bool:
    # « un » / « une » only stand for the value 1, exactly: read as a number of
    # tolerance 0.5 they would accept every value between 0.5 and 1.5. The check is
    # weak for that value (the article is everywhere): it is not a proof.
    if value == 1 and re.search(r"\b[Uu]ne?\b", text):
        return True
    for number, decimals in numbers_in(text):
        tolerance = 0.5 * 10 ** (-decimals) + 1e-12 * abs(number)
        if abs(value - number) <= tolerance:
            return True
    return False


def _section(text: str, section: str) -> str | None:
    """Text of a section `§N` of a test-case file (`## N. …` or `## §N …`).

    `document` (lot 35) désigne le fichier entier : une donnée complémentaire
    sans sections numérotées (une note de données du projet)."""
    if section == "document":
        return text
    if re.fullmatch(r"[A-Z]\.?\d+", section):
        # sub-section `### A.1 …` of a complementary-data file, or `### B3. …` of
        # an annex copied verbatim (lot 47): up to the next heading
        match = re.search(
            rf"^### {re.escape(section)}\b.*?(?=^#{{1,3}} |\Z)", text, flags=re.M | re.S
        )
        return match[0] if match else None
    number = section.removeprefix("§")
    parts = re.split(r"^## ", text, flags=re.M)
    for part in parts[1:]:
        title = part.split("\n", 1)[0]
        if re.match(rf"(§{number}\b|{number}\.)", title):
            return part
    return None


def _source_text(
    source: ValueSource, sheet: HypothesesSheet, inputs_dir: Path
) -> tuple[str | None, str]:
    """(text to search, reason if none)."""
    if source.kind == "cas_test":
        assert source.document is not None
        assert source.section is not None
        path = inputs_dir / source.document
        if not path.is_file():
            return None, f"fichier {source.document} introuvable"
        section = _section(path.read_text(encoding="utf-8"), source.section)
        if section is None:
            return None, f"section {source.section} introuvable"
        return section, ""
    if source.kind == "decision":
        entries = [
            e
            for e in sheet.entries
            if isinstance(e, PracticeHypothesisEntry)
            and e.status == "tranche"
            and e.point_label == source.point_label
        ]
        if not entries:
            return None, f"aucune décision tranchée au point {source.point_label}"
        return "\n".join(e.option_retained or "" for e in entries), ""
    assert source.topic_prefix is not None
    findings = [
        e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.point_label == source.point_label
        and e.topic.startswith(source.topic_prefix)
    ]
    if len(findings) != 1:
        return None, (
            f"{len(findings)} constat(s) code_aster au point {source.point_label} "
            f"pour le sujet « {source.topic_prefix} »"
        )
    return findings[0].option_retained or "", ""


def check_consistency(
    data: ModelData, sheet: HypothesesSheet, inputs_dir: Path
) -> list[Discrepancy]:
    """Confront every provided value with the text of its source.

    Reported, never corrected. A numerical value must appear in the source text
    within the rounding of its displayed digits; a text value must appear
    verbatim; a vector must have each component present.
    """
    report: list[Discrepancy] = []
    for name, item in data.items().items():
        if item.status != "fourni" or item.source is None:
            continue
        text, problem = _source_text(item.source, sheet, inputs_dir)
        label = item.source.label()
        if text is None:
            report.append(
                Discrepancy(
                    name=name,
                    value=item.value if item.value is not None else (),
                    source=label,
                    reason=problem,
                )
            )
            continue
        values = item.value
        if item.profile is not None:
            absent = [
                f"{n:g}"
                for point in item.profile
                for n in (point.z, point.p)
                if not _appears(n, text)
            ]
            if absent:
                report.append(
                    Discrepancy(
                        name=name,
                        value=tuple(x for pt in item.profile for x in (pt.z, pt.p)),
                        source=label,
                        reason=f"absent du texte de la source : {', '.join(absent)}",
                    )
                )
            continue
        assert values is not None
        if isinstance(values, str):
            ok = values in text
            missing: list[str] = [] if ok else [values]
        else:
            components = values if isinstance(values, tuple) else (values,)
            missing = [
                f"{component:g}"
                for component in components
                if not _appears(component, text)
            ]
        if missing:
            report.append(
                Discrepancy(
                    name=name,
                    value=values,
                    source=label,
                    reason=f"absent du texte de la source : {', '.join(missing)}",
                )
            )
    return report


__all__: list[str] = [
    "DataValue",
    "Discrepancy",
    "ModelData",
    "ProfilePoint",
    "ValueSource",
    "check_consistency",
    "load_model_data",
    "numbers_in",
]
