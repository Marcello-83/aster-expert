"""`mesh run` and `mesh check` orchestration, with injected runners (lot 26).

No Singularity, no Docker, no Salome: the runner is a fake that writes what a
Salome script would write (or does not).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aster_expert.meshing.check import check_med
from aster_expert.meshing.config import MeshConfig, load_mesh_config
from aster_expert.meshing.errors import MeshCheckError, MeshConfigError, MeshRunError
from aster_expert.meshing.run import (
    Runner,
    build_shell_command,
    find_verified_mesh,
    record_verified_mesh,
    run_salome_script,
    sha256_file,
)

_ROOT = Path(__file__).resolve().parents[2]
_README = "Version        : V2024.1.0_scibian_univ\n"


@pytest.fixture
def config() -> MeshConfig:
    return load_mesh_config(_ROOT / "config" / "validation.yaml")


@pytest.fixture
def image(tmp_path: Path, config: MeshConfig) -> MeshConfig:
    fake = tmp_path / "salome.sif"
    fake.write_bytes(b"image")
    return config.model_copy(
        update={
            "salome": config.salome.model_copy(
                update={"image_path": str(fake), "runtime": "true"}
            )
        }
    )


def _result(
    code: int = 0, out: str = "", err: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, out, err)


def _fake_salome(
    *,
    write_med: bool = True,
    meta_sha: str | None = "auto",
    code: int = 0,
    out: str = "",
) -> Runner:
    def runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        if "cat" in argv:
            return _result(out=_README)
        work = Path(argv[argv.index("--bind") + 1].split(":")[0])
        if write_med:
            (work / "s.med").write_bytes(b"MED")
        if meta_sha is not None:
            params = work / "params.json"
            sha = (
                hashlib.sha256(params.read_bytes()).hexdigest()
                if meta_sha == "auto"
                else meta_sha
            )
            (work / "s.meta.json").write_text(json.dumps({"params_sha256": sha}))
        return _result(code, out)

    return runner


@pytest.fixture
def script_and_params(tmp_path: Path) -> tuple[Path, Path]:
    script = tmp_path / "s.py"
    script.write_text("print(1)\n", encoding="utf-8")
    params = tmp_path / "params.json"
    params.write_text('{"a": 1}', encoding="utf-8")
    return script, params


def test_the_versioned_config_declares_salome_without_code_defaults(
    config: MeshConfig,
) -> None:
    assert config.salome.image_path.endswith("salome_meca.sif")
    assert config.salome.expected_version == "V2024.1.0_scibian_univ"
    assert "--net" in config.salome.container_options
    assert "{script}" in config.salome.command


def test_a_missing_mesh_section_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "v.yaml"
    path.write_text("execution: {}\n", encoding="utf-8")
    with pytest.raises(MeshConfigError):
        load_mesh_config(path)


def test_shell_command_sources_the_environment_then_launches(
    config: MeshConfig,
) -> None:
    shell = build_shell_command(config, "s.py", ["p.json", "s.med"])
    assert shell.index("salome_prerequisites.sh") < shell.index("salome_modules.sh")
    assert shell.endswith("salome -t --shutdown-servers=1 /work/s.py args:p.json,s.med")


def test_a_successful_run_reports_every_fingerprint(
    tmp_path: Path, image: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    script, params = script_and_params
    report = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    assert report.script_sha256 == hashlib.sha256(script.read_bytes()).hexdigest()
    assert report.params_sha256 == report.params_sha256_recorded_by_script
    assert report.med_sha256 == hashlib.sha256(b"MED").hexdigest()
    assert report.image_sha256 == hashlib.sha256(b"image").hexdigest()
    assert report.image_sha256_source == "computed"
    assert report.salome_version == "V2024.1.0_scibian_univ"
    assert Path(report.log_path).is_file()
    assert (Path(report.work_dir) / "mesh_run_report.json").is_file()
    # second run: the digest comes from the cache
    again = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    assert again.image_sha256_source == "cache"
    assert again.work_dir != report.work_dir


@pytest.mark.parametrize(
    ("runner_kwargs", "message"),
    [
        ({"code": 3}, "exited with code 3"),
        ({"write_med": False}, "no MED file"),
        ({"out": "Traceback (most recent call last):\n"}, "Python exception"),
        ({"meta_sha": None}, "did not record the fingerprint"),
        ({"meta_sha": "0" * 64}, "did not record the fingerprint"),
    ],
)
def test_a_bad_run_fails(
    tmp_path: Path,
    image: MeshConfig,
    script_and_params: tuple[Path, Path],
    runner_kwargs: dict[str, object],
    message: str,
) -> None:
    script, params = script_and_params
    with pytest.raises(MeshRunError, match=message):
        run_salome_script(
            script,
            project_root=tmp_path,
            config=image,
            params=params,
            runner=_fake_salome(**runner_kwargs),  # type: ignore[arg-type]
        )


def test_an_unexpected_salome_version_stops_the_run(
    tmp_path: Path, image: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    script, params = script_and_params

    def runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return _result(out="Version : V1.0\n")

    with pytest.raises(MeshRunError, match="differs from the expected"):
        run_salome_script(
            script, project_root=tmp_path, config=image, params=params, runner=runner
        )


def test_a_missing_image_is_refused(
    tmp_path: Path, config: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    script, _ = script_and_params
    missing = config.model_copy(
        update={
            "salome": config.salome.model_copy(
                update={"image_path": str(tmp_path / "no.sif")}
            )
        }
    )
    with pytest.raises(MeshRunError, match="image not found"):
        run_salome_script(script, project_root=tmp_path, config=missing)


def test_check_med_reads_through_the_container_and_evaluates(
    tmp_path: Path, config: MeshConfig
) -> None:
    med = tmp_path / "m.med"
    med.write_bytes(b"MED")
    invariants = tmp_path / "inv.yaml"
    invariants.write_text(
        "schema_version: 1\ncounts:\n  nodes: 2\n  cells: {SEG2: 1}\n", encoding="utf-8"
    )
    dump = {
        "mesh_name": "m",
        "space_dimension": 3,
        "coords": [[0, 0, 0], [1, 0, 0]],
        "levels": {"0": {"types": ["NORM_SEG2"], "connectivity": [[0, 1]]}},
        "groups": [],
    }
    seen: dict[str, object] = {}

    def runner(**kwargs: object) -> subprocess.CompletedProcess[str]:
        work = Path(str(kwargs["workdir"]))
        seen.update(kwargs)
        (work / "dump.json").write_text(json.dumps(dump))
        return _result()

    report = check_med(
        med,
        invariants,
        project_root=tmp_path,
        config=config,
        docker_bin=Path("docker"),
        image_ref="img@sha256:x",
        runner=runner,
    )
    assert report.ok and len(report.results) == 2
    assert seen["network"] == "none"
    assert "dump_med.py" in str(seen["command"])
    assert Path(report.report_path).read_text("utf-8").endswith("tenus.\n")

    invariants.write_text("schema_version: 1\ncounts:\n  nodes: 3\n", encoding="utf-8")
    failing = check_med(
        med,
        invariants,
        project_root=tmp_path,
        config=config,
        docker_bin=Path("docker"),
        image_ref="img@sha256:x",
        runner=runner,
    )
    assert not failing.ok


def test_a_verified_med_is_reused_without_relaunching_salome(
    tmp_path: Path, image: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    """Lot 28, "cache de maillage": once a MED is recorded verified, a later
    `run_salome_script` with the identical fingerprint returns it unchanged
    (`from_cache=True`) and never calls the runner at all."""
    script, params = script_and_params
    report = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    assert not report.from_cache
    record_verified_mesh(tmp_path / image.work_dir_root, report)

    def forbidden(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise AssertionError("Salome must not be invoked on a cache hit")

    cached = run_salome_script(
        script, project_root=tmp_path, config=image, params=params, runner=forbidden
    )
    assert cached.from_cache
    assert cached.model_copy(update={"from_cache": False}) == report


def test_a_changed_script_misses_the_cache(
    tmp_path: Path, image: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    script, params = script_and_params
    report = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    record_verified_mesh(tmp_path / image.work_dir_root, report)

    script.write_text("print(2)\n", encoding="utf-8")
    again = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    assert not again.from_cache
    assert again.work_dir != report.work_dir


def test_a_missing_med_is_a_cache_miss_not_a_stale_hit(
    tmp_path: Path, image: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    script, params = script_and_params
    report = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    record_verified_mesh(tmp_path / image.work_dir_root, report)
    Path(report.med_path).unlink()

    found = find_verified_mesh(
        tmp_path / image.work_dir_root,
        script_sha256=report.script_sha256,
        params_sha256=report.params_sha256,
    )
    assert found is None


def test_check_med_records_a_verified_med_in_the_run_cache(
    tmp_path: Path, image: MeshConfig, script_and_params: tuple[Path, Path]
) -> None:
    """`mesh check` finding a `mesh run`-produced MED `ok` feeds the same cache a
    later `mesh run` call consults (integration of the two lot 28 halves)."""
    script, params = script_and_params
    run_report = run_salome_script(
        script,
        project_root=tmp_path,
        config=image,
        params=params,
        runner=_fake_salome(),
    )
    med = Path(run_report.med_path)
    invariants = tmp_path / "inv.yaml"
    invariants.write_text("schema_version: 1\n", encoding="utf-8")

    def dump_runner(**kwargs: object) -> subprocess.CompletedProcess[str]:
        work = Path(str(kwargs["workdir"]))
        (work / "dump.json").write_text(
            json.dumps(
                {
                    "mesh_name": "m",
                    "space_dimension": 3,
                    "coords": [],
                    "levels": {},
                    "groups": [],
                }
            )
        )
        return _result()

    check_report = check_med(
        med,
        invariants,
        project_root=tmp_path,
        config=image,
        docker_bin=Path("docker"),
        image_ref="img@sha256:x",
        runner=dump_runner,
    )
    assert check_report.ok
    found = find_verified_mesh(
        tmp_path / image.work_dir_root,
        script_sha256=run_report.script_sha256,
        params_sha256=run_report.params_sha256,
    )
    assert found is not None
    assert found.med_sha256 == sha256_file(med) == run_report.med_sha256


def test_check_med_fails_when_the_reader_fails(
    tmp_path: Path, config: MeshConfig
) -> None:
    med = tmp_path / "m.med"
    shutil.copy(_ROOT / "config" / "validation.yaml", med)
    invariants = tmp_path / "inv.yaml"
    invariants.write_text("schema_version: 1\n", encoding="utf-8")

    def runner(**kwargs: object) -> subprocess.CompletedProcess[str]:
        return _result(1, err="boom")

    with pytest.raises(MeshCheckError, match="could not read"):
        check_med(
            med,
            invariants,
            project_root=tmp_path,
            config=config,
            docker_bin=Path("docker"),
            image_ref="i",
            runner=runner,
        )
