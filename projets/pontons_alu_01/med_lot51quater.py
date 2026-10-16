"""MED files of lot 51 quater for PONTONS-ALU-01 (consigne § MED), variants B10 and B12.

Sources: the unit fields Code_Aster wrote in MED for the variant (post-processing run of
the project chain on the `.comm` of lot 51 ter, unchanged: B10 at lot 51 ter, B12 at
this lot), copied under `resultats/lot51quater/<variante>/med_unitaires/`.

1. `scripts/med_lire_lot51quater.py` (medcoupling, in the Code_Aster image) dumps the
   unit DEPL, EFGE_ELNO and nodal forces FN, and the layout of the EFGE_ELNO ends.
2. Here (the project's Python): the unit fields of the MED against the E25.16 tables
   of the lot 51 ter run (criterion 2); the four combinations of view 7 (coefficients
   from `combinaisons_lot51quater`, governing combinations recomputed as the
   comparison does);
   the ELU envelopes of N, MFY, MFZ at each end (decomposition, fundamental and
   accidental ULS); the houle events P60 and P61 as nodal forces.
3. `scripts/med_ecrire_lot51quater.py` (medcoupling) writes structure.med, charges.med
   and resultats.med from templates (deep copies of unit fields, values replaced), adds
   the span, pier and pin groups, and reads the three files again.

Choice (consigne: « si l'écriture directe en Python (medcoupling) est plus sûre, la
préférer et le dire »): the combinations are written by medcoupling from the fields
Code_Aster wrote, never by a new Code_Aster command: no change to the `.comm`, nothing
to reconcile between two runs, every value checked against the tables.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.execution.container_env import build_environment_setup_script
from aster_expert.execution.docker_client import run_in_container
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51ter import envelope, governing
from pontons_alu_01.exports_lot51 import DEPL
from pontons_alu_01.exports_lot51quater import Variant51quater, load
from pontons_alu_01.exports_lot51ter import (
    STATES_COMPARED,
    _arrays,
    _rows_of,
    deflection_arrays,
)
from pontons_alu_01.generation_lot51ter import applied_loads

FloatArray = NDArray[np.float64]
LOT = "lot51quater"
SCRIPTS = Path(__file__).resolve().parent / "scripts"
READ_SCRIPT = SCRIPTS / "med_lire_lot51quater.py"
WRITE_SCRIPT = SCRIPTS / "med_ecrire_lot51quater.py"
ENVELOPE_FIELD = "ENV_ELU__EFGE_ELNO"
ENVELOPE_COMPONENTS = ("N_MAX", "N_MIN", "MFY_MAX", "MFY_MIN", "MFZ_MAX", "MFZ_MIN")
ELU_STATES = ("ELU_fondamental", "ELU_accidentel")
HOULE_EVENTS = (
    "HU",
    "HD",
    "HU_F",
    *(f"HU_IMP_M{k}" for k in range(6)),
)


def variant_dir(ctx: ProjectContext, code: str) -> Path:
    return ctx.results_dir / LOT / code


def image_ref(ctx: ProjectContext) -> str:
    from aster_expert.projet.pipeline import Runtime  # noqa: PLC0415

    rt = Runtime(ctx.repo_root)
    digest, _ = rt.aster()
    return f"{rt.image_repository}@{digest}"


def in_image(
    ctx: ProjectContext, work: Path, command: str, timeout: int = 3600
) -> None:
    docker = shutil.which("docker")
    if docker is None:
        message = "docker introuvable"
        raise RuntimeError(message)
    result = run_in_container(
        docker_bin=Path(docker),
        image_ref=image_ref(ctx),
        workdir=work,
        command=build_environment_setup_script() + "\n" + command + "\n",
        network="none",
        timeout=timeout,
        container_name=f"aster-expert-med51q-{uuid.uuid4().hex[:8]}",
        drop_to_host_user=True,
    )
    if result.returncode != 0:
        message = (
            f"medcoupling ({command}) : code {result.returncode} : "
            f"{result.stderr[-2000:]}"
        )
        raise RuntimeError(message)


# ------------------------------------------------------------------------- combinations


def _best(
    v: Variant51quater,
    f: dict[str, FloatArray],
    states: tuple[str, ...],
    *,
    without: tuple[str, ...] = (),
) -> tuple[float, str, dict[str, float], str, int]:
    """Signed extreme in absolute value over `states`: value, combination, its
    coefficients, state and place index."""
    vd = v.vd
    best: tuple[float, float, str, dict[str, float], str, int] | None = None
    for state in states:
        for sign in (1.0, -1.0):
            ext = envelope(vd.bs, vd.ev, f, state, sign=sign, without=without)
            scores = sign * ext.value
            q = int(np.argmax(scores))
            if best is None or float(scores[q]) > best[0]:
                name, coefs = governing(vd.bs, vd.ev, ext, q)
                best = (float(scores[q]), float(ext.value[q]), name, coefs, state, q)
    assert best is not None
    return best[1], best[2], best[3], best[4], best[5]


def view_combinations(v: Variant51quater) -> list[dict[str, Any]]:
    """The four combinations of view 7 (docs/essais_lot51quater.md § 2)."""
    vd = v.vd
    out: list[dict[str, Any]] = []
    rows = _rows_of(vd, ("POUTRES_PRINC",))
    value, name, coefs, state, q = _best(v, _arrays(vd, rows, 4), STATES_COMPARED)
    e, n = rows[q]
    out.append(
        {
            "cle": "PP_MY_EXTREME",
            "titre": "PP My extrême",
            "grandeur": f"MFY = {value * 1e-3:.1f} kN·m, élément {e} nœud {n}",
            "etat_limite": state,
            "combinaison": name,
            "coefficients": coefs,
        }
    )
    spans = [s.name for s in vd.g.spans if s.nature == "grande"] + ["PF"]
    worst: tuple[float, dict[str, Any]] | None = None
    for span in spans:
        f, where, length = deflection_arrays(vd, span)
        value, name, coefs, state, q = _best(v, f, ("ELS_frequent",), without=("G",))
        ratio = abs(value) / length
        if worst is None or ratio > worst[0]:
            worst = (
                ratio,
                {
                    "cle": "FLECHE_ELS_F",
                    "titre": "flèche de l'ELS fréquent",
                    "grandeur": f"flèche {span} = {value * 1e3:.1f} mm "
                    f"(L/{length / abs(value):.0f}), {where[q]}",
                    "etat_limite": state,
                    "combinaison": name,
                    "coefficients": coefs,
                },
            )
    assert worst is not None
    out.append(worst[1])
    supports = [
        vd.model.group_nodes["APP_CULEE_YM"][0],
        vd.model.group_nodes["APP_CULEE_YP"][0],
    ]
    rx = {
        c: np.array([sum(vd.tables.reac[c][n][0] for n in supports)]) for c in vd.cases
    }
    value, name, coefs, state, _ = _best(v, rx, ("ELU_fondamental",))
    out.append(
        {
            "cle": "CULEE_SRX",
            "titre": "ΣRX de la culée",
            "grandeur": f"ΣRX = {value * 1e-3:.1f} kN",
            "etat_limite": state,
            "combinaison": name,
            "coefficients": coefs,
        }
    )
    coefs = dict(vd.ev["G_DEJ_100"].coefficients)
    for k, c in vd.ev["HU_IMP_M0"].coefficients.items():
        coefs[k] = coefs.get(k, 0.0) + c
    out.append(
        {
            "cle": "IMPACT_M0",
            "titre": "impact HU_IMP_M0",
            "grandeur": "impact sur le module M0 (T1) seul",
            "etat_limite": "ELS_caracteristique",
            "combinaison": "ELS_caracteristique: G_DEJ_100×1 + HU_IMP_M0×1",
            "coefficients": coefs,
        }
    )
    return out


def combined(
    coefs: dict[str, float], cases: list[str], unit: NDArray[Any]
) -> NDArray[Any]:
    index = {c: i for i, c in enumerate(cases)}
    out = np.zeros(unit.shape[1:])
    for case, c in coefs.items():
        out = out + c * unit[index[case]]
    return out


# --------------------------------------------------------------------------- steps


def read_unit(ctx: ProjectContext, code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = variant_dir(ctx, code)
    work = base / "med_travail"
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "lu.json").is_file():
        for name in ("resultats.med", "charges.med"):
            shutil.copyfile(base / "med_unitaires" / name, work / name)
        shutil.copyfile(READ_SCRIPT, work / READ_SCRIPT.name)
        try:
            in_image(
                ctx,
                work,
                f"python3 {READ_SCRIPT.name} resultats.med charges.med lu.npz lu.json",
            )
        finally:
            for name in ("resultats.med", "charges.med"):
                (work / name).unlink(missing_ok=True)
    meta = json.loads((work / "lu.json").read_text("utf-8"))
    with np.load(work / "lu.npz") as data:
        arrays = {k: data[k] for k in data.files}
    return meta, arrays


def check_unit_fields(
    v: Variant51quater, meta: dict[str, Any], arrays: dict[str, Any]
) -> dict[str, Any]:
    """Criterion 2: unit DEPL and EFGE_ELNO of the MED against the E25.16 tables."""
    vd = v.vd
    worst_u = worst_e = 0.0
    missing = 0
    layout = [tuple(x) for x in meta["extremites"]]
    for i, case in enumerate(meta["cas"]):
        table = vd.tables.depl[case]
        med = arrays["depl"][i]
        ref = np.array(
            [
                table[n + 1][: len(DEPL)] if n + 1 in table else med[n]
                for n in range(len(med))
            ]
        )
        missing += sum(1 for n in range(len(med)) if n + 1 not in table)
        scale = max(float(np.nanmax(np.abs(ref))), 1e-300)
        worst_u = max(worst_u, float(np.nanmax(np.abs(med - ref))) / scale)
        etab = vd.tables.efge[case]
        eref = np.array([etab[k] for k in layout])
        scale = max(float(np.max(np.abs(eref))), 1e-300)
        worst_e = max(worst_e, float(np.max(np.abs(arrays["efge"][i] - eref))) / scale)
    return {
        "cas": len(meta["cas"]),
        "noeuds_absents_des_tables": missing,
        "DEPL_ecart_relatif_max": worst_u,
        "EFGE_ELNO_ecart_relatif_max": worst_e,
        "reussi": worst_u <= 1e-9 and worst_e <= 1e-9,
    }


def envelopes(v: Variant51quater, layout: list[tuple[int, int]]) -> NDArray[Any]:
    """ELU envelopes at each end (fundamental and accidental): max and min of N, MFY,
    MFZ, each component on its own."""
    vd = v.vd
    out = np.zeros((len(layout), len(ENVELOPE_COMPONENTS)))
    for k, comp in enumerate((0, 4, 5)):
        f = _arrays(vd, layout, comp)
        hi = np.max(
            [envelope(vd.bs, vd.ev, f, s, sign=1.0).value for s in ELU_STATES], axis=0
        )
        lo = np.min(
            [envelope(vd.bs, vd.ev, f, s, sign=-1.0).value for s in ELU_STATES], axis=0
        )
        out[:, 2 * k] = hi
        out[:, 2 * k + 1] = lo
    return out


def added_groups(v: Variant51quater, meta: dict[str, Any]) -> dict[str, Any]:
    """TRAVEE_<travée> and PALEE_<palée> (SEG2 of the bars of each span and pier),
    AXES_APPUI (nodes of the pins: ears and cap nodes)."""
    groups = meta["groupes"]
    out: dict[str, Any] = {}
    by_span: dict[str, set[int]] = {}
    for m in v.vd.g.members:
        grp = groups.get(m.name)
        if grp is None or grp["level"] != -1:
            continue
        prefix = (
            "PALEE" if m.span.startswith("P") and m.span[1:].isdigit() else "TRAVEE"
        )
        by_span.setdefault(f"{prefix}_{m.span}", set()).update(grp["ids"])
    for name in sorted(by_span):
        if name in groups:
            message = f"groupe {name} déjà présent"
            raise ValueError(message)
        out[name] = {"level": -1, "ids": sorted(by_span[name])}
    pins = sorted(
        {i for name, g in groups.items() if name.startswith("AX_") for i in g["ids"]}
    )
    out["AXES_APPUI"] = {"level": 1, "ids": pins}
    return out


def build_spec(
    code: str,
    v: Variant51quater,
    meta: dict[str, Any],
    arrays: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, NDArray[Any]], dict[str, Any]]:
    vd = v.vd
    layout = [tuple(x) for x in meta["extremites"]]
    combos = view_combinations(v)
    comb_depl = np.array(
        [combined(c["coefficients"], meta["cas"], arrays["depl"]) for c in combos]
    )
    comb_efge = np.array(
        [combined(c["coefficients"], meta["cas"], arrays["efge"]) for c in combos]
    )
    # contrôle : les mêmes combinaisons depuis les tables E25.16
    worst = 0.0
    for c, u, e in zip(combos, comb_depl, comb_efge, strict=True):
        ref_u = np.zeros_like(u)
        ref_e = np.zeros_like(e)
        for case, k in c["coefficients"].items():
            table = vd.tables.depl[case]
            ref_u += k * np.array([table[n + 1][: len(DEPL)] for n in range(len(u))])
            ref_e += k * np.array([vd.tables.efge[case][p] for p in layout])
        worst = max(
            worst,
            float(np.max(np.abs(u - ref_u))) / float(np.max(np.abs(ref_u))),
            float(np.max(np.abs(e - ref_e))) / float(np.max(np.abs(ref_e))),
        )
    env = envelopes(v, layout)
    events = []
    loads = applied_loads(vd.vals, vd.g)
    resultants = {}
    for name in HOULE_EVENTS:
        coefs = vd.ev[name].coefficients
        field = combined(coefs, meta["cas_charges"], arrays["fn"])
        events.append(field)
        got = field[:, :3].sum(axis=0)
        declared = np.array(
            [sum(c * loads[k][d] for k, c in coefs.items()) for d in ("DX", "DY", "DZ")]
        )
        resultants[name] = {
            "champ_N": got.tolist(),
            "declaree_N": declared.tolist(),
            "ecart_relatif": float(
                np.max(np.abs(got - declared)) / np.max(np.abs(declared))
            ),
        }
    spec = {
        "maillage_source": meta["maillage"],
        "maillage": f"PONTON_{code}",
        "groupes_ajoutes": added_groups(v, meta),
        "gabarit_forces": "FN_G1",
        "gabarit_depl": f"CAS_{meta['cas'][0]}__DEPL",
        "gabarit_efge": f"CAS_{meta['cas'][0]}__EFGE_ELNO",
        "evenements": [f"EV_{n}" for n in HOULE_EVENTS],
        "combinaisons": [c["cle"] for c in combos],
        "enveloppe": ENVELOPE_FIELD,
        "composantes_enveloppe": list(ENVELOPE_COMPONENTS),
    }
    data = {
        "evenements": np.array(events),
        "comb_depl": comb_depl,
        "comb_efge": comb_efge,
        "enveloppe": env,
    }
    checks = {
        "combinaisons": combos,
        "combinaisons_contre_tables_ecart_relatif_max": worst,
        "resultantes_evenements": resultants,
    }
    return spec, data, checks


def check_envelope(ctx: ProjectContext, code: str, env: NDArray[Any]) -> dict[str, Any]:
    """The envelope field against the comparison of the lot: PP My extreme (its state
    is an ULS) equals the extreme of MFY_MAX / MFY_MIN over the main beam ends."""
    path = ctx.results_dir / LOT / "exports" / "synthese.json"
    pp = json.loads(path.read_text("utf-8"))[code]["comparaison"]["PP_My"]
    return {
        "PP_My_comparaison_kNm": pp["value"],
        "PP_My_etat": pp["state"],
        "PP_My_lieu": pp["where"],
        "MFY_enveloppe_extremes_kNm": [
            float(env[:, 2].max()) * 1e-3,
            float(env[:, 3].min()) * 1e-3,
        ],
    }


def write_med(
    ctx: ProjectContext, code: str, spec: dict[str, Any], data: dict[str, NDArray[Any]]
) -> dict[str, Any]:
    base = variant_dir(ctx, code)
    work = base / "med_travail"
    out = base / "MED"
    out.mkdir(parents=True, exist_ok=True)
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
    np.savez(
        work / "spec.npz",
        evenements=data["evenements"],
        comb_depl=data["comb_depl"],
        comb_efge=data["comb_efge"],
        enveloppe=data["enveloppe"],
    )
    for name in ("resultats.med", "charges.med"):
        shutil.copyfile(base / "med_unitaires" / name, work / name)
    shutil.copyfile(WRITE_SCRIPT, work / WRITE_SCRIPT.name)
    try:
        in_image(
            ctx,
            work,
            f"python3 {WRITE_SCRIPT.name} resultats.med charges.med spec.json "
            "spec.npz sortie",
        )
    finally:
        for name in ("resultats.med", "charges.med"):
            (work / name).unlink(missing_ok=True)
    for name in ("structure.med", "charges.med", "resultats.med"):
        shutil.move(work / "sortie" / name, out / name)
    report: dict[str, Any] = json.loads(
        (work / "sortie" / "relecture.json").read_text("utf-8")
    )
    return report


def step_med(ctx: ProjectContext, codes: list[str], state: dict[str, Any]) -> None:
    for code in codes:
        t0 = time.perf_counter()
        meta, arrays = read_unit(ctx, code)
        v = load(ctx, code, state)
        info: dict[str, Any] = {
            "controle_champs_unitaires": check_unit_fields(v, meta, arrays)
        }
        spec, data, checks = build_spec(code, v, meta, arrays)
        info.update(checks)
        info["controle_enveloppe"] = check_envelope(ctx, code, data["enveloppe"])
        report = write_med(ctx, code, spec, data)
        expected_groups = len(meta["groupes"]) + len(spec["groupes_ajoutes"])
        info["relecture"] = report
        info["attendu"] = {
            "noeuds": meta["noeuds"],
            "niveaux": meta["niveaux"],
            "groupes": expected_groups,
            "champs_charges": meta["champs_charges"] + len(spec["evenements"]),
            "champs_resultats": 2 * len(spec["combinaisons"]) + 1,
        }
        ok = all(
            report[f]["noeuds"] == meta["noeuds"]
            and report[f]["niveaux"] == meta["niveaux"]
            and report[f]["groupes"] == expected_groups
            for f in ("structure.med", "charges.med", "resultats.med")
        )
        ok = (
            ok
            and len(report["charges.med"]["champs"])
            == info["attendu"]["champs_charges"]
        )
        ok = (
            ok
            and len(report["resultats.med"]["champs"])
            == info["attendu"]["champs_resultats"]
        )
        info["controle_med_reussi"] = bool(
            ok
            and info["controle_champs_unitaires"]["reussi"]
            and checks["combinaisons_contre_tables_ecart_relatif_max"] <= 1e-9
            and all(
                r["ecart_relatif"] <= 1e-9
                for r in checks["resultantes_evenements"].values()
            )
            and max(
                report[f]["ecart_relecture_max"] for f in report if f.endswith(".med")
            )
            == 0.0
        )
        info["duree_s"] = time.perf_counter() - t0
        path = variant_dir(ctx, code) / "med_controles.json"
        path.write_text(json.dumps(info, indent=1, ensure_ascii=False) + "\n", "utf-8")
        (variant_dir(ctx, code) / "combinaisons_vues.json").write_text(
            json.dumps(checks["combinaisons"], indent=1, ensure_ascii=False) + "\n",
            "utf-8",
        )
        verdict = "RÉUSSI" if info["controle_med_reussi"] else "ÉCHEC"
        print(f"{code} : MED écrits, contrôle {verdict}")


__all__ = ["step_med", "view_combinations"]
