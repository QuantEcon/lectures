"""tools/execution-report: execution_status.json from what a build leaves.

The fixture stands in for a Jupyter Book 1 build's output: Sphinx's
environment pickle with myst-nb's execution records in it (a SimpleNamespace
carrying the two attributes the tool reads, ``nb_metadata`` and
``all_docs``), the notebooks myst-nb writes to ``jupyter_execute/``, and the
traceback it writes to ``html/reports/``. No build is run.
"""

from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import TOOLS_DIR

TOOL = TOOLS_DIR / "execution-report"
SINCE = 1_763_340_000  # the build's start, seconds since the epoch


def notebook(kernel="python3"):
    return json.dumps({"cells": [], "metadata": {"kernelspec": {"name": kernel, "display_name": "Python 3"}},
                       "nbformat": 4, "nbformat_minor": 5})


def exec_data(succeeded=True, mtime=SINCE + 10, runtime=1.234, error=None):
    return {"mtime": mtime, "runtime": runtime, "method": "cache", "succeeded": succeeded,
            "error": error, "traceback": "Traceback ..." if error else None}


def make_build(root: Path, pages, all_docs=None, notebooks=(), reports=()):
    """A _build/ with the environment, notebooks and reports given."""
    build = root / "_build"
    (build / ".doctrees").mkdir(parents=True)
    read_at = {page: (SINCE + 60) * 1_000_000 for page in pages}
    read_at.update(all_docs or {})
    env = SimpleNamespace(nb_metadata={page: {"exec_data": data} for page, data in pages.items() if data},
                          all_docs=read_at)
    (build / ".doctrees" / "environment.pickle").write_bytes(pickle.dumps(env))
    for page in notebooks:
        path = build / "jupyter_execute" / f"{page}.ipynb"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(notebook("python3" if page != "julia_page" else "julia-1.10"), encoding="utf-8")
    for page in reports:
        path = build / "html" / "reports" / f"{page}.err.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Traceback ...\n", encoding="utf-8")
    return build


def run(root: Path, *args, env=None):
    # Under GitHub Actions the tests' own step has a GITHUB_OUTPUT: keep the
    # tool off it unless a test gives its own.
    if env is None:
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"}
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=root, capture_output=True, text=True, env=env)


def by_page(report):
    return {row["page"]: row for row in report["pages"]}


def test_every_kind_of_page_gets_its_row(tmp_path):
    pages = {
        "executed": exec_data(mtime=SINCE + 5, runtime=12.3456),
        "cached": exec_data(mtime=SINCE - 86_400, runtime=40.0),
        "broken": exec_data(succeeded=False, mtime=SINCE + 30, runtime=3.0, error="CellExecutionError"),
        "excluded": None,     # a notebook myst-nb wrote but did not execute
        "intro_text": None,   # not a notebook: no row
        "julia_page": exec_data(mtime=SINCE + 40),
    }
    make_build(tmp_path, pages, notebooks=["executed", "cached", "broken", "excluded", "julia_page"],
               reports=["broken"])
    summary = tmp_path / "summary.md"

    res = run(tmp_path, "--since", str(SINCE), "--site", "dp", "--summary", str(summary))

    assert res.returncode == 0, res.stderr
    report = json.loads((tmp_path / "_build" / "execution_status.json").read_text(encoding="utf-8"))
    rows = by_page(report)
    assert sorted(rows) == ["broken", "cached", "excluded", "executed", "julia_page"]
    assert rows["executed"] == {"page": "executed", "status": "ok", "duration": 12.35, "kernel": "python3",
                                "execution": "executed", "error": None, "report": None}
    assert rows["cached"]["execution"] == "cached" and rows["cached"]["duration"] == 40.0
    assert rows["broken"]["status"] == "failed"
    assert rows["broken"]["error"] == "CellExecutionError"
    assert rows["broken"]["execution"] == "executed"
    assert rows["broken"]["report"] == "_build/html/reports/broken.err.log"
    assert rows["excluded"] == {"page": "excluded", "status": "excluded", "duration": None, "kernel": "python3",
                                "execution": None, "error": None, "report": None}
    assert rows["julia_page"]["kernel"] == "julia-1.10"
    assert report["site"] == "dp"
    assert report["format"] == 1
    assert report["build_started"] == "2025-11-17T00:40:00Z"
    assert report["summary"] == {"pages": 5, "ok": 3, "failed": 1, "excluded": 1, "executed": 3, "cached": 1,
                                 "not_read": 0}
    assert "python" in report["versions"]
    assert "5 page(s): 3 ok, 1 failed, 1 excluded; 3 executed, 1 from the cache" in res.stdout
    text = summary.read_text(encoding="utf-8")
    assert "### Execution report: `dp`: 5 notebook page(s)" in text
    assert "| `broken` | failed (CellExecutionError) | executed | 3.00 | python3 |" in text


def test_a_page_matching_an_entry_made_earlier_in_the_same_build_is_cached(tmp_path):
    # dp's intro and zreferences have no code cells, so their notebooks hash
    # alike: intro is executed and cached, and zreferences, read later, takes
    # intro's fresh entry, whose time falls in intro's read, not in its own.
    us = 1_000_000
    pages = {"amss": exec_data(mtime=SINCE + 60),
             "intro": exec_data(mtime=SINCE + 530, runtime=0.5),
             "status": exec_data(mtime=SINCE + 690),
             "zreferences": exec_data(mtime=SINCE + 530, runtime=0.5)}
    read = {"amss": (SINCE + 61) * us, "intro": (SINCE + 531) * us, "status": (SINCE + 691) * us,
            "un_insure": (SINCE + 700) * us, "zreferences": (SINCE + 701) * us}
    make_build(tmp_path, pages, all_docs=read, notebooks=list(pages))

    res = run(tmp_path, "--since", str(SINCE))

    assert res.returncode == 0, res.stderr
    report = json.loads((tmp_path / "_build" / "execution_status.json").read_text(encoding="utf-8"))
    assert {row["page"]: row["execution"] for row in report["pages"]} == {
        "amss": "executed", "intro": "executed", "status": "executed", "zreferences": "cached"}


@pytest.mark.parametrize("scale", [1, 1_000_000], ids=["seconds", "microseconds"])
def test_read_times_in_seconds_or_microseconds_give_the_same_report(tmp_path, scale):
    # Sphinx 7.4 records each page's read in microseconds since the epoch,
    # older releases in seconds.
    pages = {"amss": exec_data(mtime=SINCE + 60), "intro": exec_data(mtime=SINCE + 530),
             "old": exec_data(mtime=SINCE - 3_600), "zreferences": exec_data(mtime=SINCE + 530)}
    read = {"amss": (SINCE + 61) * scale, "intro": (SINCE + 531) * scale, "old": (SINCE - 3_000) * scale,
            "zreferences": (SINCE + 701) * scale}
    make_build(tmp_path, pages, all_docs=read, notebooks=list(pages))

    res = run(tmp_path, "--since", str(SINCE))

    assert res.returncode == 0, res.stderr
    report = json.loads((tmp_path / "_build" / "execution_status.json").read_text(encoding="utf-8"))
    assert {row["page"]: row["execution"] for row in report["pages"]} == {
        "amss": "executed", "intro": "executed", "zreferences": "cached"}
    assert report["summary"]["not_read"] == 1


@pytest.mark.parametrize("read", [
    {"a": 12_345},                                     # neither unit
    {"a": 1.7e13},                                     # milliseconds, say
    {"a": "2026-11-17T00:00:00"},                      # not a number
    {"a": SINCE + 61, "b": (SINCE + 62) * 1_000_000},  # two units at once
], ids=["small", "milliseconds", "text", "mixed"])
def test_read_times_it_cannot_interpret_stop_the_report(tmp_path, read):
    # Read as the wrong unit, every page would count as cached, and main would
    # never save the cache: an error, not a quiet report.
    make_build(tmp_path, {page: exec_data() for page in read}, all_docs=read, notebooks=list(read))

    res = run(tmp_path, "--since", str(SINCE))

    assert res.returncode == 2
    assert "cannot tell an executed page from a cached one" in res.stderr
    assert not (tmp_path / "_build" / "execution_status.json").exists()
    # Without --since the times are not used, and the report is written.
    assert run(tmp_path).returncode == 0


def test_a_page_this_build_did_not_read_is_left_out_and_counted(tmp_path):
    # An incremental local build: `old` was read by an earlier build, and its
    # record is that build's.
    pages = {"new": exec_data(mtime=SINCE + 5), "old": exec_data(mtime=SINCE - 3_600)}
    make_build(tmp_path, pages, all_docs={"old": (SINCE - 3_000) * 1_000_000}, notebooks=["new", "old"])

    res = run(tmp_path, "--since", str(SINCE), "--summary", str(tmp_path / "summary.md"))

    assert res.returncode == 0, res.stderr
    report = json.loads((tmp_path / "_build" / "execution_status.json").read_text(encoding="utf-8"))
    assert [row["page"] for row in report["pages"]] == ["new"]
    assert report["summary"]["not_read"] == 1
    assert "1 not read by this build" in res.stdout
    assert "1 page(s) this build did not read" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_without_since_executed_or_cached_is_unknown(tmp_path):
    pages = {"a": exec_data(mtime=SINCE + 5), "b": exec_data(mtime=SINCE - 86_400)}
    make_build(tmp_path, pages, all_docs={"b": 1}, notebooks=["a", "b"])
    out = tmp_path / "elsewhere" / "status.json"

    res = run(tmp_path, "--out", str(out))

    assert res.returncode == 0, res.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert [row["execution"] for row in report["pages"]] == [None, None]
    assert report["build_started"] is None
    assert report["summary"]["not_read"] == 0  # without --since every page is reported


def test_step_outputs_carry_the_counts_the_cache_save_reads(tmp_path):
    pages = {"a": exec_data(mtime=SINCE - 10), "b": exec_data(mtime=SINCE - 20)}
    make_build(tmp_path, pages, notebooks=["a", "b"])
    output = tmp_path / "github_output"
    env = {**os.environ, "GITHUB_OUTPUT": str(output)}

    res = run(tmp_path, "--since", str(SINCE), env=env)

    assert res.returncode == 0, res.stderr
    assert output.read_text(encoding="utf-8").splitlines() == ["pages=2", "executed=0", "cached=2", "failed=0"]


def test_no_environment_is_an_error(tmp_path):
    res = run(tmp_path, "--since", str(SINCE))

    assert res.returncode == 2
    assert "environment.pickle does not exist" in res.stderr
    assert not (tmp_path / "_build" / "execution_status.json").exists()


def test_an_environment_it_cannot_import_names_the_python_to_use(tmp_path):
    # What `uv run --script` meets: a pickle naming a module this Python lacks.
    (tmp_path / "_build" / ".doctrees").mkdir(parents=True)
    (tmp_path / "_build" / ".doctrees" / "environment.pickle").write_bytes(b"cno_such_module_for_this_test\nEnv\n.")

    res = run(tmp_path)

    assert res.returncode == 2
    assert "No module named 'no_such_module_for_this_test'" in res.stderr
    assert "the Python that ran jb build" in res.stderr
