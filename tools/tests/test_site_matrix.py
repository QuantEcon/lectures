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
        {"key": "intro", "runs_on": "ubuntu-latest", "image": "ghcr.io/quantecon/quantecon-build:latest",
         "timeout_minutes": 11 + 120, "cell_timeout": 601, "publishes": ["html", "pdf"],
         "extra_packages": [], "packages_hash": "none"},
        {"key": "dp", "runs_on": "ubuntu-latest", "image": "ghcr.io/quantecon/quantecon-build:latest",
         "timeout_minutes": 40 + 120, "cell_timeout": 2400, "publishes": ["html"],
         "extra_packages": ["jax"], "packages_hash": hashlib.sha256(b"jax").hexdigest()[:16]},
    ]
    assert "not built (not named): jax" in res.stderr


def test_a_site_with_no_leg_yet_is_refused_and_nothing_is_printed(tmp_path):
    root = scratch(tmp_path, {"dp": site_yml(), "jax": site_yml(runner="g4dn.2xlarge"),
                              "course": site_yml(type_="course")})

    res = run(root, "dp", "jax", "course", "nope")

    assert res.returncode == 1
    assert res.stdout == ""
    assert "sites/jax: runner 'g4dn.2xlarge' has no leg yet" in res.stderr
    assert "sites/course: type 'course' has no leg yet" in res.stderr
    assert "there is no site sites/nope/" in res.stderr


def test_the_packages_hash_follows_the_list_and_a_value_pip_could_read_as_an_option_is_refused(tmp_path):
    root = scratch(tmp_path, {"a": site_yml(extra_packages=["jax"]), "b": site_yml(extra_packages=["jax", "optax"]),
                              "c": site_yml(extra_packages=["--index-url=https://example.org/simple"]),
                              "d": site_yml(extra_packages="jax")})

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


def test_the_workflow_allowlist_resolves_against_the_real_sites():
    sites = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["env"]["SITES"].split()
    res = subprocess.run([sys.executable, str(TOOLS_DIR / "site-matrix"), *sites], capture_output=True, text=True)

    assert res.returncode == 0, res.stderr
    assert [item["key"] for item in json.loads(res.stdout)] == sites


def test_the_workflow_runs_on_the_same_paths_for_a_push_and_a_pull_request():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = data.get("on", data.get(True))  # YAML 1.1 reads a bare `on` as true
    push, pull = on["push"]["paths"], on["pull_request"]["paths"]

    assert push == pull
    for path in push:
        if path.startswith("tools/"):
            assert (REPO / path).is_file(), f"{path} is listed but does not exist"
