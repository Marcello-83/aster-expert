"""Data models for the `detected` section of config/versions.yaml, and for a
level-C execution report (docs/development-plan.md, lot 11; docs/metadata.md
section 5).

See docs/architecture.md, ADR-002, ADR-003, ADR-006.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# The "stable" and "testing" tags are mobile aliases on the registry side and
# have been observed to diverge from the locally cached image of the same
# name (docs/architecture.md, ADR-002). They are never a valid resolved tag.
FORBIDDEN_IMAGE_TAGS = frozenset({"stable", "testing"})


class ResolvedImage(BaseModel):
    """Identity of the container image actually used, resolved by digest."""

    model_config = ConfigDict(frozen=True)

    repository: str
    tag: str
    digest: str
    image_id: str
    cave_pin_source: str  # "directory" | "global" | "none"


class ContainerInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: str
    engine_version_raw: str
    image_repository: str
    image_tag: str
    image_digest: str
    image_id: str
    cave_pin_source: str


class RunAsterInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_in_container: str
    version_raw: str


class AsterPythonInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    interpreter_path_in_container: str
    pythonpath_extra: tuple[str, ...]


class CodeAsterPackageInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_in_container: str


class CatalogueInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_in_container: str
    fingerprint_sha256: str


class InvocationInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    mechanism: str
    mount_pattern: str


class DetectedEnvironment(BaseModel):
    """The full `detected` section written to config/versions.yaml."""

    model_config = ConfigDict(frozen=True)

    detected_at: datetime
    install_kind: str
    container: ContainerInfo
    run_aster: RunAsterInfo
    aster_python: AsterPythonInfo
    code_aster_package: CodeAsterPackageInfo
    catalogue: CatalogueInfo
    invocation: InvocationInfo


# One entry per string `run_aster.status.StateOptions.name()` can actually
# return (`external/codeaster-src/run_aster/status.py`, read directly, never
# guessed) -- plus two outcomes that are this project's own, never produced
# by run_aster itself: `interrupted_timeout` (docs/development-plan.md, lot
# 11, O2: the outer time budget enveloping the whole `docker run` call, not
# just Aster's own `--time_limit`, fired) and `crashed` (`run_aster_main.main`
# raised before ever constructing a `Status` -- e.g. a malformed file --
# so there is no diagnostic string to map at all). An execution level C
# report is never allowed to claim more than what `run_aster.status` itself
# established (docs/metadata.md section 5, "never reimplement it"): this is
# a *label*, not a recomputation -- `diag` always carries the raw string
# alongside it.
ExecutionStatus = Literal[
    "completed_ok",
    "completed_with_alarms",
    "completed_with_nook",
    "completed_no_test",
    "aborted",
    "failed_syntax",
    "failed",
    "failed_memory",
    "failed_no_convergence",
    "failed_cpu_limit",
    "failed_exception",
    "unknown",
    "interrupted_timeout",
    "crashed",
]

# `run_aster.status.StateOptions.name()` -> `ExecutionStatus` (docs/
# development-plan.md, lot 11). Built once, from a direct reading of that
# function's own body -- never from running it, since this project's Python
# never imports `run_aster` (docs/architecture.md, ADR-002): a diag string
# this table does not recognize is a real fact to fail loudly on (a newer
# run_aster added a state this project has not seen), never absorbed
# silently into an existing bucket.
DIAG_TO_STATUS: dict[str, ExecutionStatus] = {
    "OK": "completed_ok",
    "<A>_ALARM": "completed_with_alarms",
    "NOOK_TEST_RESU": "completed_with_nook",
    "NO_TEST_RESU": "completed_no_test",
    "<F>_ABNORMAL_ABORT": "aborted",
    "<F>_SYNTAX_ERROR": "failed_syntax",
    "<F>_ERROR": "failed",
    "<S>_MEMORY_ERROR": "failed_memory",
    "<S>_NO_CONVERGENCE": "failed_no_convergence",
    "<S>_CPU_LIMIT": "failed_cpu_limit",
    "<S>_ERROR": "failed_exception",
    "?": "unknown",
}


class ExecutionReport(BaseModel):
    """Level-C execution report (docs/metadata.md, section 5, amended lot 11).

    Deliberately narrower than the full schema section 5 originally sketched
    (`alarms`/`errors` as structured, per-alarm entries via
    `run_aster.error_messages`): O1 of this lot forbids writing a project
    output analyzer, and `run_aster.error_messages` is left to the
    dépouillement-fin lot. `diag` is the one and only detail level this
    report offers beyond `status` -- exactly what `run_aster.status` itself
    hands back, verbatim, never post-processed beyond the `DIAG_TO_STATUS`
    labelling above.
    """

    model_config = ConfigDict(frozen=True)

    comm_path: str
    aster_version: str
    image_digest: str
    status: ExecutionStatus
    diag: str | None
    return_code: int | None
    work_dir: str
    mess_path: str | None
    result_files: tuple[str, ...]
    duration_s: float | None
    extracted_by: Literal["run_aster.status"]
    executed_at: datetime
