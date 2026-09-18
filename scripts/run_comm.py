"""Run a `.export` or `.comm` file through `run_aster`, report its outcome as JSON.

Run inside the Code_Aster container by its own Python interpreter (see
docs/architecture.md, ADR-002). Encapsulates two `run_aster` entry points,
never reimplements them (docs/development-plan.md, lot 11, O1):

- `run_aster.run_aster_main.main` -- the exact function `bin/run_aster`
  itself calls (`if __name__ == "__main__": sys.exit(main())`): this script
  never re-derives a working directory, a `.export`, MPI splitting, or a
  time/memory limit by hand, it only builds the same argument vector a human
  would type on the command line.
- `run_aster.status.Status.load` -- read back the `--status-file` that
  `run_aster_main.main` itself writes when given one, exposing exactly the
  fields `docs/metadata.md` section 5 asks for (`diag`, `exitcode`,
  `is_completed`, `results_saved`, `times`) -- never a `.mess` text scrape.

Prints exactly one JSON object on stdout, always -- including when
`run_aster_main.main` itself raises before ever reaching a `Status` (a
malformed file, an environment import failure): this script's own contract
is to never let such a failure come out as a bare traceback on stdout, which
would break the host-side JSON parse.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        required=True,
        help="Absolute path, inside /work, of the .export or .comm.",
    )
    parser.add_argument("--wrkdir", required=True)
    parser.add_argument("--status-file", required=True)
    parser.add_argument("--time-limit", type=float, required=True)
    parser.add_argument("--memory-limit", type=float, required=True)
    args = parser.parse_args(argv)

    try:
        from run_aster.run_aster_main import main as run_aster_main
        from run_aster.status import Status
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        print(
            json.dumps(
                {
                    "ok": False,
                    "crash": f"cannot import run_aster: {type(exc).__name__}: {exc}",
                }
            )
        )
        return 1

    run_argv = [
        "--wrkdir",
        args.wrkdir,
        "--status-file",
        args.status_file,
        "--time_limit",
        str(args.time_limit),
        "--memory_limit",
        str(args.memory_limit),
        args.file,
    ]

    payload: dict[str, Any]
    try:
        exitcode = run_aster_main(run_argv)
    except SystemExit as exc:
        # argparse (inside run_aster_main itself) exits this way on a
        # malformed argument vector -- never expected here since this
        # script builds run_argv itself, but reported rather than let
        # propagate as a non-JSON exit.
        code = exc.code if isinstance(exc.code, int) else 1
        payload = {
            "ok": False,
            "crash": f"run_aster_main exited via SystemExit({exc.code!r})",
            "return_code": code,
        }
        print(json.dumps(payload))
        return 0
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        payload = {
            "ok": False,
            "crash": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(payload))
        return 0

    status = Status.load(args.status_file)
    payload = {
        "ok": True,
        "return_code": exitcode,
        "status_exitcode": status.exitcode,
        "diag": status.diag,
        "is_completed": status.is_completed(),
        "results_saved": status.results_saved(),
        "times": status.times,
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
