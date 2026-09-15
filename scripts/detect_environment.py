"""Probe run inside the Code_Aster container by its own Python interpreter.

Standard library only (see scripts/README.md). Reports, as JSON on stdout:
run_aster's version, the code_aster package location, the Cata (catalogue)
package location and a content fingerprint of that package. Never guesses:
any failure to import or locate something exits non-zero with a message on
stderr and no JSON on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def compute_fingerprint(root: Path) -> str:
    """Return a content-based sha256 fingerprint of a package directory.

    Deterministic across re-runs of the same content: based on the sorted
    relative paths and file contents, never on mtimes.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*.py") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run_aster_version_raw(run_aster_path: Path) -> str:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [str(run_aster_path), "--version"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        message = f"'{run_aster_path} --version' failed: {result.stderr.strip()}"
        raise RuntimeError(message)
    return result.stdout.strip()


def build_report(
    *,
    run_aster_path: Path,
    pythonpath_extra: list[str],
    run_aster_version: str,
    python_executable: str,
    code_aster_package_path: Path,
    catalogue_path: Path,
    catalogue_fingerprint: str,
) -> dict[str, object]:
    return {
        "run_aster": {
            "path_in_container": str(run_aster_path),
            "version_raw": run_aster_version,
        },
        "aster_python": {
            "interpreter_path_in_container": python_executable,
            "pythonpath_extra": pythonpath_extra,
        },
        "code_aster_package": {
            "path_in_container": str(code_aster_package_path),
        },
        "catalogue": {
            "path_in_container": str(catalogue_path),
            "fingerprint_sha256": catalogue_fingerprint,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-aster-path", required=True, type=Path)
    parser.add_argument("--pythonpath-extra", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        version_raw = run_aster_version_raw(args.run_aster_path)

        # Imported here, not at module scope: this module is also imported by
        # the project's unit tests, run by the project's own Python, which
        # never has `code_aster` on its path (docs/architecture.md, ADR-002).
        import code_aster.Cata  # noqa: PLC0415
        import code_aster.Cata.Commands  # noqa: F401, PLC0415

        code_aster_package_path = Path(code_aster.Cata.__file__).parent.parent
        catalogue_path = Path(code_aster.Cata.__file__).parent
        fingerprint = compute_fingerprint(catalogue_path)

        report = build_report(
            run_aster_path=args.run_aster_path,
            pythonpath_extra=[p for p in args.pythonpath_extra if p],
            run_aster_version=version_raw,
            python_executable=sys.executable,
            code_aster_package_path=code_aster_package_path,
            catalogue_path=catalogue_path,
            catalogue_fingerprint=fingerprint,
        )
    except Exception as exc:  # noqa: BLE001 - reported on stderr, never swallowed
        print(f"detect_environment: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
