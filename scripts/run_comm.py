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
from pathlib import Path
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

    status_source = "run_aster.status.Status.load"
    if Path(args.status_file).is_file():
        status = Status.load(args.status_file)
    else:
        # Lot 47 quater: with mpi_nbcpu > 1, run_aster_main restarts itself under
        # mpiexec with its own `--status-file` (a temporary directory it deletes),
        # which overrides ours: no status file is left here. The status is then
        # computed by run_aster's own `get_status`, on the listing of each rank.
        status, status_source = _status_from_ranks(args.wrkdir, exitcode)
    payload = {
        "ok": True,
        "return_code": exitcode,
        "status_exitcode": status.exitcode,
        "diag": status.diag,
        "is_completed": status.is_completed(),
        "results_saved": status.results_saved(),
        "times": status.times,
        "status_source": status_source,
    }
    payload.update(_messages(args.wrkdir))
    print(json.dumps(payload))
    return 0


def _status_from_ranks(wrkdir, exitcode):
    """Status of an MPI run (lot 47 quater): `run_aster.status.get_status` on the
    `fort.6` of every rank (`proc.N`); the first rank whose diagnostic is not that of
    rank 0 is reported, so that a failure on any rank is never hidden."""
    from run_aster.status import Status, get_status

    listings = sorted(
        Path(wrkdir).glob("proc.*/fort.6"), key=lambda p: int(p.parent.name[5:])
    )
    if not listings:
        return Status(), "aucun listing de rang (proc.N/fort.6)"
    statuses = [(p, get_status(exitcode, str(p))) for p in listings]
    chosen_path, chosen = statuses[0]
    for path, status in statuses[1:]:
        if status.diag != chosen.diag:
            chosen_path, chosen = path, status
            break
    source = (
        f"run_aster.status.get_status sur {len(listings)} rang(s) MPI, "
        f"retenu {chosen_path.parent.name}/fort.6"
    )
    return chosen, source


# Lot 41 : messages <A>/<F>/<E>/<S> du listing, extraits par
# `run_aster.error_messages.search_msg` (jamais par un parseur du projet), sur tout
# le fichier (`maxlines` = nombre de lignes : sinon seules les 100 000 dernières
# lignes seraient lues). Les messages d'information (<I>, <INFO>) et le marqueur de
# fin sont écartés ; au-delà de MAX_MESSAGES, le nombre omis est rendu.
MAX_MESSAGES = 500
_KEPT = ("<A>", "<F>", "<E>", "<S>")


def _messages(wrkdir):
    from pathlib import Path

    root = Path(wrkdir)
    candidates = [root / "fort.6", *sorted(root.glob("proc.*/fort.6"))]
    mess = next((p for p in candidates if p.is_file()), None)
    if mess is None:
        return {"messages": [], "messages_truncated": 0, "messages_source": None}
    try:
        from run_aster.error_messages import search_msg

        text = mess.read_text(encoding="utf-8", errors="replace")
        found = search_msg(text, maxlines=len(text.splitlines()) + 1)
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        return {
            "messages": [],
            "messages_truncated": 0,
            "messages_source": None,
            "messages_error": f"{type(exc).__name__}: {exc}",
        }
    kept = []
    for entries in found.values():
        for line, cleaned in entries:
            first = cleaned.split(None, 1)[0] if cleaned.strip() else ""
            if first in _KEPT or "Traceback" in cleaned or "Error:" in first:
                kept.append({"line": line, "text": cleaned})
    return {
        "messages": kept[:MAX_MESSAGES],
        "messages_truncated": max(0, len(kept) - MAX_MESSAGES),
        "messages_source": "run_aster.error_messages",
    }


if __name__ == "__main__":
    sys.exit(main())
