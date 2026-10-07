"""Time profile of a run, by command, from the timer table of its listing
(lot 47 quater).

**Documented gap.** `run_aster.status.get_status` reads only the `TOTAL_JOB` line of the
table that `code_aster.Utilities.as_timer.Timer` prints at the end of a run (format
`aster`: ` * %(name)-24s : %(cpu_dt)10.2f : %(sys_dt)10.2f : %(cpu_sys)10.2f :
%(tot_dt)10.2f *`, 17.4.0). No module of `run_aster` reads the lines by command; this
module reads them, and nothing else of the listing.

The table holds one line per command, in the order of execution, up to `MaxSize` (500)
timers; beyond, one line `after 500 timers` sums the rest. Lines whose name starts with
`. ` (`. check syntax`, `. fortran`, `. cleanup`) break `TOTAL_JOB` down by nature, not
by command: they are kept apart and never added to the commands.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_LINE = re.compile(
    r"^ \* (?P<name>.{24}) :\s*(?P<user>[0-9.]+) :\s*(?P<sys>[0-9.]+) :"
    r"\s*(?P<usersys>[0-9.]+) :\s*(?P<elapsed>[0-9.]+) \*$"
)
_HEADER = (
    " * COMMAND                  :       USER :     SYSTEM :   USER+SYS :    ELAPSED *"
)
TOTAL = "TOTAL_JOB"
OVERFLOW_PREFIX = "after "


@dataclass(frozen=True)
class Timing:
    user_sys: float
    elapsed: float


@dataclass
class Profile:
    """Elapsed and CPU time, summed by command name."""

    by_command: dict[str, Timing] = field(default_factory=dict)
    occurrences: dict[str, int] = field(default_factory=dict)
    breakdown: dict[str, Timing] = field(default_factory=dict)
    overflow: Timing | None = None
    total: Timing | None = None

    def grouped(self, groups: dict[str, tuple[str, ...]]) -> dict[str, float]:
        """Elapsed time by group of commands; what no group names goes to « reste »."""
        result: dict[str, float] = dict.fromkeys(groups, 0.0)
        result["reste"] = 0.0
        for command, timing in self.by_command.items():
            target = next((g for g, cmds in groups.items() if command in cmds), "reste")
            result[target] += timing.elapsed
        if self.overflow is not None:
            result["reste"] += self.overflow.elapsed
        return result


def read_profile(mess: Path) -> Profile:
    """Read the last timer table of `mess` (`fort.6` or `.mess`)."""
    lines = mess.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        start = max(i for i, line in enumerate(lines) if line.rstrip() == _HEADER)
    except ValueError as exc:
        message = f"{mess} : aucun tableau des temps par commande"
        raise ValueError(message) from exc
    sums: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    profile = Profile()
    for line in lines[start + 1 :]:
        match = _LINE.match(line.rstrip())
        if match is None:
            if line.startswith(" ****") or not line.strip():
                continue
            break
        name = match["name"].strip()
        timing = Timing(float(match["usersys"]), float(match["elapsed"]))
        if name == TOTAL:
            profile.total = timing
            break
        if name.startswith(". "):
            profile.breakdown[name[2:]] = timing
        elif name.startswith(OVERFLOW_PREFIX):
            profile.overflow = timing
        else:
            sums[name][0] += timing.user_sys
            sums[name][1] += timing.elapsed
            profile.occurrences[name] = profile.occurrences.get(name, 0) + 1
    profile.by_command = {k: Timing(v[0], v[1]) for k, v in sums.items()}
    if profile.total is None:
        message = f"{mess} : ligne {TOTAL} absente du tableau des temps"
        raise ValueError(message)
    return profile


__all__ = ["Profile", "Timing", "read_profile"]
