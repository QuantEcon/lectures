"""tools/site-matrix: the build workflow's matrix, read from each site.yml,
and the workflow's own settings that the matrix relies on."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from conftest import TOOLS_DIR

REPO = TOOLS_DIR.parent
WORKFLOW = REPO / ".github" / "workflows" / "site-build.yml"


def site_yml(runner="ubuntu-latest", cell_timeout=2400, type_="series", publishes=("html",), **more):
    return yaml.safe_dump({"type": type_, "runner": runner, "cell_timeout": cell_timeout,
                           "publishes": list(publishes), "url": "https://example.org/", **more})


def scratch(root: Path, sites):
    (root / "tools").mkdir()
    shutil.copy(TOOLS_DIR / "site-matrix", root / "tools" / "site-matrix")
    for key, text in sites.items():
        (root / "sites" / key).mkdir(parents=True)
        (root / "sites" / key / "site.yml").write_text(text, encoding="utf-8")
    return root


def run(root: Path, *keys):
    return subprocess.run([sys.executable, str(root / "tools" / "site-matrix"), *keys],
                          capture_output=True, text=True)


def test_a_cpu_series_site_gets_its_runner_container_and_time_limit(tmp_path):
    root = scratch(tmp_path, {"dp": site_yml(extra_packages=["jax"]),
                              "intro": site_yml(cell_timeout=601, publishes=["html", "pdf"]),
                              "jax": site_yml(runner="g4dn.2xlarge")})

    res = run(root, "intro", "dp", "intro")

    assert res.returncode == 0, res.stderr
    assert "\n" not in res.stdout.strip()  # one line, for $GITHUB_OUTPUT
    assert json.loads(res.stdout) == [
        {"key": "intro", "runs_on": "ubuntu-latest", "leg": "container", "machine": "", "environment": "series",
         "image": "ghcr.io/quantecon/quantecon-build:latest", "env_file": "mirror/intro/environment.yml",
         "cache_tag": "", "timeout_minutes": 11 + 150, "cell_timeout": 601, "publishes": ["html", "pdf"],
         "extra_packages": [], "packages_hash": "none"},
        {"key": "dp", "runs_on": "ubuntu-latest", "leg": "container", "machine": "", "environment": "series",
         "image": "ghcr.io/quantecon/quantecon-build:latest", "env_file": "mirror/dp/environment.yml",
         "cache_tag": "", "timeout_minutes": 40 + 150, "cell_timeout": 2400, "publishes": ["html"],
         "extra_packages": ["jax"], "packages_hash": hashlib.sha256(b"jax").hexdigest()[:16]},
    ]
    assert "not built (not named): jax" in res.stderr


def test_a_site_in_the_base_environment_builds_in_the_full_image_keyed_on_the_list(tmp_path):
    root = scratch(tmp_path, {"intro": site_yml(cell_timeout=600, environment="base"),
                              "dp": site_yml(environment="series"),
                              "odd": site_yml(environment="universal")})

    res = run(root, "intro", "dp")

    assert res.returncode == 0, res.stderr
    intro, dp = json.loads(res.stdout)
    assert {k: intro[k] for k in ("environment", "image", "env_file", "cache_tag")} == {
        "environment": "base", "image": "ghcr.io/quantecon/quantecon:latest",
        "env_file": "_base/environment-update.yml", "cache_tag": "base-"}
    assert {k: dp[k] for k in ("environment", "image", "env_file", "cache_tag")} == {
        "environment": "series", "image": "ghcr.io/quantecon/quantecon-build:latest",
        "env_file": "mirror/dp/environment.yml", "cache_tag": ""}

    res = run(root, "odd")
    assert res.returncode == 1
    assert res.stdout == ""
    assert "sites/odd: environment 'universal' is not one of series, base" in res.stderr


def test_a_gpu_site_builds_on_its_runs_on_machine_in_the_base_environment_alone(tmp_path):
    root = scratch(tmp_path, {"programming": site_yml(runner="g4dn.2xlarge", cell_timeout=600, environment="base"),
                              "jax": site_yml(runner="g4dn.2xlarge"),
                              "intro": site_yml(environment="base")})

    res = run(root, "--run-id", "123", "programming", "intro")

    assert res.returncode == 0, res.stderr
    programming, intro = json.loads(res.stdout)
    machine = programming["machine"]
    assert machine.startswith("family=g4dn.2xlarge/ami=ami-")
    assert {k: programming[k] for k in ("runs_on", "leg", "environment", "image", "env_file", "cache_tag",
                                        "timeout_minutes")} == {
        "runs_on": f"runs-on=123/{machine}", "leg": "gpu", "environment": "base", "image": "",
        "env_file": "_base/environment-update.yml", "cache_tag": "base-", "timeout_minutes": 10 + 150}
    # A container site in the same run is unchanged.
    assert {k: intro[k] for k in ("runs_on", "leg", "machine", "image")} == {
        "runs_on": "ubuntu-latest", "leg": "container", "machine": "", "image": "ghcr.io/quantecon/quantecon:latest"}

    # A GPU site in the series environment, or with no run for RunsOn's label, is refused.
    res = run(root, "--run-id", "123", "jax")
    assert res.returncode == 1
    assert res.stdout == ""
    assert ("sites/jax: a site on g4dn.2xlarge builds in the base environment alone (environment: base), "
            "not 'series'") in res.stderr
    res = run(root, "programming")
    assert res.returncode == 1
    assert "sites/programming: a site on g4dn.2xlarge needs --run-id" in res.stderr
    res = run(root, "--run-id", "12a", "programming")
    assert res.returncode == 2
    assert "--run-id '12a' is not a run ID" in res.stderr


def test_a_list_or_mapping_where_a_name_belongs_is_refused_like_an_unknown_name(tmp_path):
    root = scratch(tmp_path, {"envlist": site_yml(environment=["base"]),
                              "envmap": site_yml(environment={"name": "base"}),
                              "runlist": site_yml(runner=["ubuntu-latest"]),
                              "runmap": site_yml(runner={"label": "ubuntu-latest"}),
                              "dp": site_yml()})

    res = run(root, "envlist", "envmap", "runlist", "runmap", "dp")

    # Every refusal is collected and reported, with no traceback.
    assert res.returncode == 1
    assert res.stdout == ""
    assert "Traceback" not in res.stderr
    assert "sites/envlist: environment ['base'] is not one of series, base" in res.stderr
    assert "sites/envmap: environment {'name': 'base'} is not one of series, base" in res.stderr
    assert "sites/runlist: runner ['ubuntu-latest'] has no leg yet" in res.stderr
    assert "sites/runmap: runner {'label': 'ubuntu-latest'} has no leg yet" in res.stderr


def test_a_site_with_no_leg_yet_is_refused_and_nothing_is_printed(tmp_path):
    root = scratch(tmp_path, {"dp": site_yml(), "mac": site_yml(runner="macos-latest"),
                              "course": site_yml(type_="course")})

    res = run(root, "dp", "mac", "course", "nope")

    assert res.returncode == 1
    assert res.stdout == ""
    assert "sites/mac: runner 'macos-latest' has no leg yet (only ubuntu-latest, g4dn.2xlarge)" in res.stderr
    assert "sites/course: type 'course' has no leg yet" in res.stderr
    assert "there is no site sites/nope/" in res.stderr


def test_the_packages_hash_follows_the_list_and_a_value_pip_could_read_as_an_option_is_refused(tmp_path):
    root = scratch(tmp_path, {"a": site_yml(extra_packages=["jax"]), "b": site_yml(extra_packages=["jax", "optax"]),
                              "c": site_yml(extra_packages=["--index-url=https://example.org/simple"]),
                              "d": site_yml(extra_packages="jax"),
                              "e": site_yml(extra_packages=[]), "f": site_yml(extra_packages=["jax", "jax"])})

    res = run(root, "a", "b")
    assert res.returncode == 0, res.stderr
    first, second = json.loads(res.stdout)
    assert first["packages_hash"] != second["packages_hash"]
    assert second["packages_hash"] == hashlib.sha256(b"jax\noptax").hexdigest()[:16]

    res = run(root, "c", "d")
    assert res.returncode == 1
    assert res.stdout == ""
    assert "sites/c: extra_packages ['--index-url=https://example.org/simple'] is not a list of pip requirements" \
        in res.stderr
    assert "sites/d: extra_packages 'jax' is not a list of pip requirements" in res.stderr

    # As pool-check rules: present means a non-empty list, each requirement once.
    res = run(root, "e", "f")
    assert res.returncode == 1
    assert "sites/e: extra_packages [] is not a list of pip requirements" in res.stderr
    assert "sites/f: extra_packages ['jax', 'jax'] is not a list of pip requirements" in res.stderr


def test_the_workflow_allowlist_resolves_against_the_real_sites():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    sites = data["env"]["SITES"].split()
    res = subprocess.run([sys.executable, str(TOOLS_DIR / "site-matrix"), "--run-id", "1", *sites],
                         capture_output=True, text=True)

    assert res.returncode == 0, res.stderr
    assert [item["key"] for item in json.loads(res.stdout)] == sites
    # The workflow gives the run's ID, which a GPU site's RunsOn label needs.
    step = next(s for s in data["jobs"]["sites"]["steps"] if s.get("id") == "matrix")
    assert '--run-id "$GITHUB_RUN_ID"' in step["run"]


def test_the_workflow_runs_on_the_same_paths_for_a_push_and_a_pull_request():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = data.get("on", data.get(True))  # YAML 1.1 reads a bare `on` as true
    push, pull = on["push"]["paths"], on["pull_request"]["paths"]

    assert push == pull
    for path in push:
        if path.startswith("tools/"):
            assert (REPO / path).is_file(), f"{path} is listed but does not exist"
