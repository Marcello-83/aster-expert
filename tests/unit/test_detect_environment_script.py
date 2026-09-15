"""Unit tests for scripts/detect_environment.py's pure logic.

This script runs under the Aster Python inside the container in production
(docs/architecture.md, ADR-002) and is not part of the `aster_expert` package.
Its testable functions never import `code_aster`, so they can be exercised
here, under the project's own Python, without any installation.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
import types
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "detect_environment.py"


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "detect_environment_script", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


detect_environment_script = _load_script()


def test_compute_fingerprint_is_deterministic(tmp_path: Path) -> None:
    package = tmp_path / "Cata"
    package.mkdir()
    (package / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    (package / "Syntax.py").write_text("y = 2\n", encoding="utf-8")

    first = detect_environment_script.compute_fingerprint(package)
    second = detect_environment_script.compute_fingerprint(package)
    assert first == second
    assert len(first) == 64  # sha256 hex digest


def test_compute_fingerprint_changes_with_content(tmp_path: Path) -> None:
    package = tmp_path / "Cata"
    package.mkdir()
    (package / "__init__.py").write_text("x = 1\n", encoding="utf-8")

    before = detect_environment_script.compute_fingerprint(package)
    (package / "__init__.py").write_text("x = 2\n", encoding="utf-8")
    after = detect_environment_script.compute_fingerprint(package)

    assert before != after


def test_compute_fingerprint_ignores_mtime(tmp_path: Path) -> None:
    package = tmp_path / "Cata"
    package.mkdir()
    (package / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    first = detect_environment_script.compute_fingerprint(package)

    time.sleep(0.01)
    os.utime(package / "__init__.py", None)
    second = detect_environment_script.compute_fingerprint(package)

    assert first == second


def test_build_report_shape() -> None:
    report = detect_environment_script.build_report(
        run_aster_path=Path("/opt/x/bin/run_aster"),
        pythonpath_extra=["/opt/x/view/site-packages"],
        run_aster_version="code_aster 17.4.0 (spack-local)",
        python_executable="/opt/x/bin/python3",
        code_aster_package_path=Path("/opt/x/lib64/aster/code_aster"),
        catalogue_path=Path("/opt/x/lib64/aster/code_aster/Cata"),
        catalogue_fingerprint="abc123",
    )

    assert report == {
        "run_aster": {
            "path_in_container": "/opt/x/bin/run_aster",
            "version_raw": "code_aster 17.4.0 (spack-local)",
        },
        "aster_python": {
            "interpreter_path_in_container": "/opt/x/bin/python3",
            "pythonpath_extra": ["/opt/x/view/site-packages"],
        },
        "code_aster_package": {"path_in_container": "/opt/x/lib64/aster/code_aster"},
        "catalogue": {
            "path_in_container": "/opt/x/lib64/aster/code_aster/Cata",
            "fingerprint_sha256": "abc123",
        },
    }


def test_main_fails_loudly_when_run_aster_missing(tmp_path: Path) -> None:
    missing = tmp_path / "run_aster"
    exit_code = detect_environment_script.main(["--run-aster-path", str(missing)])
    assert exit_code == 1
