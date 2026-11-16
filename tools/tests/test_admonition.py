"""A shared ``_admonition/`` include when one series edits its copy first.

The pool keeps one version for every lecture that uses it. A series whose
copy was the pool's version leads; the copies that have not followed are
recorded as stale, and reported as drift once they are a week behind."""

from datetime import datetime, timedelta, timezone

import yaml

from conftest import lecture_text

INCLUDE = "```{include} _admonition/gpu.md\n```"
ASSET = "_static/_shared/_admonition/gpu.md"
V1, V2, V3 = "GPU note, version 1\n", "GPU note, version 2\n", "GPU note, version 3\n"


def stamp(days_ago):
    then = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return then.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def set_synced(repo, series, when):
    path = repo.root / "sync" / "state.yml"
    state = yaml.safe_load(path.read_text(encoding="utf-8"))
    state[series]["synced_at"] = when
    path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")


def three_series(make_repo):
    """programming, intermediate and jax each hold the include, and each has
    a lecture of its own that uses it."""
    repo = make_repo(["programming", "intermediate", "jax"])
    for series in repo.order:
        repo.mirror_file(series, "_admonition/gpu.md", V1)
    repo.lecture("programming", "numba", lecture_text("Numba", INCLUDE))
    repo.lecture("intermediate", "mccall", lecture_text("McCall", INCLUDE))
    repo.lecture("jax", "jax_intro", lecture_text("JAX", INCLUDE))
    res = repo.promote("numba", "mccall", "jax_intro")
    assert res.returncode == 0, res.stderr
    record = repo.ledger()["assets"][ASSET]
    assert record["canonical"] == "programming"
    assert all("digest" not in s for s in record["sources"])
    return repo


def lead(repo, series, text, days_ago=0, n=2):
    repo.mirror_file(series, "_admonition/gpu.md", text)
    repo.move_pin(series, n)
    set_synced(repo, series, stamp(days_ago))


def sources(repo):
    return {s["series"]: s for s in repo.ledger()["assets"][ASSET]["sources"]}


def test_the_pool_takes_the_newer_version_and_the_lagging_copies_are_stale(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)

    # Before the refresh the drift-check asks for one, and raises no issue.
    dc = repo.drift_check()
    assert dc.returncode == 1
    assert "[asset-moved]" in dc.stdout and "the copy in intermediate changed upstream" in dc.stdout
    assert "DRIFT" not in dc.stdout

    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert f"[{ASSET}] STALE: programming, jax hold a version that is not the pool's; the pool takes intermediate's" in res.stdout
    # One file for every lecture that uses it, in the batch or not.
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V2
    record = repo.ledger()["assets"][ASSET]
    assert record["canonical"] == "intermediate"
    got = sources(repo)
    assert "digest" not in got["intermediate"]
    for series in ("programming", "jax"):
        assert got[series]["digest"] != record["digest"]
        assert got[series]["stale_since"]

    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    assert dc.stdout.count("[stale-copy]") == 2
    assert "is not at the pool's version" in dc.stdout


def test_a_copy_that_catches_up_is_current_again(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0
    since = sources(repo)["jax"]["stale_since"]

    lead(repo, "programming", V2)
    dc = repo.drift_check()
    assert "DRIFT" not in dc.stdout
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    record = repo.ledger()["assets"][ASSET]
    assert record["canonical"] == "programming"
    got = sources(repo)
    assert "digest" not in got["programming"] and "digest" not in got["intermediate"]
    # jax has not moved, so it has been behind since the same time.
    assert got["jax"]["stale_since"] == since

    lead(repo, "jax", V2)
    assert repo.promote("--refresh").returncode == 0
    assert all("digest" not in s for s in sources(repo).values())
    dc = repo.drift_check()
    assert dc.returncode == 0 and "stale-copy" not in dc.stdout, dc.stdout


def test_a_lagging_series_refreshed_for_another_reason_keeps_the_pools_version(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0

    # programming moves, but its include is still the earlier version.
    repo.lecture("programming", "numba", lecture_text("Numba", INCLUDE + "\n\nFixed upstream."))
    repo.move_pin("programming")
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert "Fixed upstream." in repo.pool("numba.md").read_text(encoding="utf-8")
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V2
    assert sources(repo)["programming"]["digest"]
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout


def test_a_copy_behind_for_more_than_a_week_becomes_drift(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2, days_ago=8)
    assert repo.promote("--refresh").returncode == 0

    dc = repo.drift_check("--print-issues")

    assert dc.returncode == 1
    assert dc.stdout.count("[stale-copy]") == 2
    assert "### drift(jax): lectures/_admonition/gpu.md is not at the pool's version" in dc.stdout
    assert "### drift(programming): lectures/_admonition/gpu.md is not at the pool's version" in dc.stdout
    assert "Make the same change in jax" in dc.stdout


def test_two_series_that_change_it_differently_are_refused(make_repo):
    repo = three_series(make_repo)
    before = repo.ledger_path.read_bytes()
    lead(repo, "intermediate", V2)
    lead(repo, "jax", V3)

    dc = repo.drift_check()
    assert dc.stdout.count("[asset-diverged]") == 2

    res = repo.promote("--refresh")
    assert res.returncode == 1
    assert "_admonition/gpu.md differs across series" in res.stderr
    assert "changed it differently" in res.stderr
    assert repo.ledger_path.read_bytes() == before
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V1


def test_a_stale_copy_may_only_catch_up(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0
    before = repo.ledger_path.read_bytes()

    # jax was behind and changes to a third version: a fork, not a lag.
    lead(repo, "jax", V3)
    dc = repo.drift_check()
    assert "[asset-diverged]" in dc.stdout and "the jax copy" in dc.stdout

    res = repo.promote("--refresh")
    assert res.returncode == 1
    assert "jax was behind the pool's version" in res.stderr
    assert repo.ledger_path.read_bytes() == before

    # Once the series that holds the pool's version follows, jax leads.
    lead(repo, "intermediate", V3, n=3)
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V3
    got = sources(repo)
    assert "digest" not in got["intermediate"] and "digest" not in got["jax"]
    assert got["programming"]["digest"]


def test_a_series_new_to_the_include_must_hold_the_pools_version(make_repo):
    repo = make_repo(["programming", "intermediate"])
    repo.mirror_file("programming", "_admonition/gpu.md", V1)
    repo.lecture("programming", "numba", lecture_text("Numba", INCLUDE))
    assert repo.promote("numba").returncode == 0

    repo.mirror_file("intermediate", "_admonition/gpu.md", V2)
    repo.lecture("intermediate", "mccall", lecture_text("McCall", INCLUDE))
    res = repo.promote("mccall")

    assert res.returncode == 1
    assert "intermediate was behind the pool's version, or never recorded" in res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V1


def test_a_refresh_with_no_lag_writes_no_per_source_digest(make_repo):
    repo = three_series(make_repo)
    for series in repo.order:
        repo.mirror_file(series, "_admonition/gpu.md", V2)
        repo.move_pin(series)

    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert "STALE" not in res.stdout
    assert all(set(s) == {"series", "path"} for s in sources(repo).values())
    assert repo.drift_check().returncode == 0


def test_a_leader_whose_own_lectures_did_not_move_is_still_taken(make_repo):
    # numba is one lecture in both series, canonical in programming. Only
    # intermediate's copy of the include changes, so no canonical pin of a
    # lecture that uses it moves.
    repo = make_repo(["programming", "intermediate"])
    for series in repo.order:
        repo.mirror_file(series, "_admonition/gpu.md", V1)
        repo.lecture(series, "numba", lecture_text("Numba", INCLUDE))
    assert repo.promote("numba").returncode == 0
    assert set(sources(repo)) == {"programming", "intermediate"}
    lead(repo, "intermediate", V2)

    assert "[asset-moved]" in repo.drift_check().stdout
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V2
    assert sources(repo)["programming"]["stale_since"]
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout


def test_a_series_none_of_whose_lectures_use_the_file_is_not_a_source(make_repo):
    # intermediate has a file of the same name, but no pool lecture that uses
    # it comes from intermediate: its copy is not the pool's business.
    repo = make_repo(["programming", "intermediate"])
    for series in repo.order:
        repo.mirror_file(series, "_admonition/gpu.md", V1)
    repo.lecture("programming", "numba", lecture_text("Numba", INCLUDE))
    repo.lecture("intermediate", "mccall", lecture_text("McCall"))
    assert repo.promote("numba", "mccall").returncode == 0
    assert set(sources(repo)) == {"programming"}

    lead(repo, "intermediate", V2)

    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V1


def test_a_series_left_out_of_a_run_keeps_its_stale_record(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0
    jax = sources(repo)["jax"]

    repo.lecture("programming", "numba", lecture_text("Numba", INCLUDE + "\n\nFixed upstream."))
    repo.move_pin("programming")
    res = repo.promote("--refresh", "--exclude", "jax")

    assert res.returncode == 0, res.stderr
    assert sources(repo)["jax"] == jax
    lead(repo, "jax", V2)
    assert repo.promote("--refresh").returncode == 0
    assert "digest" not in sources(repo)["jax"]


def test_when_the_holder_of_the_pools_version_drops_it_the_pool_follows_the_rest(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0

    # Left out of a run, the holder is not taken for gone.
    res = repo.promote("numba", "--exclude", "intermediate")
    assert res.returncode == 1
    assert "held only by intermediate, which this run leaves out" in res.stderr

    (repo.root / "mirror" / "intermediate" / "lectures" / "_admonition" / "gpu.md").unlink()
    repo.lecture("intermediate", "mccall", lecture_text("McCall"))
    repo.move_pin("intermediate", 3)
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V1
    assert set(sources(repo)) == {"programming", "jax"}
    assert all("digest" not in s for s in sources(repo).values())
    assert repo.drift_check().returncode == 0


def test_a_stale_copy_that_catches_up_as_the_pool_moves_again_is_not_drift(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0
    lead(repo, "jax", V2)
    lead(repo, "intermediate", V3, n=3)

    dc = repo.drift_check()
    assert "DRIFT" not in dc.stdout, dc.stdout
    assert "the jax copy is at the pool's version while intermediate moved" in dc.stdout

    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V3
    assert repo.drift_check().returncode == 0


def test_a_hand_edited_pool_include_is_never_overwritten(make_repo):
    repo = three_series(make_repo)
    repo.pool(ASSET).write_text("HAND EDIT\n", encoding="utf-8")

    res = repo.promote("jax_intro")
    assert res.returncode == 1
    assert "may not be overwritten" in res.stderr

    lead(repo, "intermediate", V2)
    res = repo.promote("--refresh")
    assert res.returncode == 1
    assert repo.pool(ASSET).read_text(encoding="utf-8") == "HAND EDIT\n"


def test_a_stale_since_that_cannot_be_read_is_drift(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)
    assert repo.promote("--refresh").returncode == 0
    text = repo.ledger_path.read_text(encoding="utf-8")
    since = sources(repo)["jax"]["stale_since"]
    repo.ledger_path.write_text(text.replace(f"stale_since: '{since}'", "stale_since: soon"), encoding="utf-8")

    dc = repo.drift_check()
    assert dc.returncode == 1 and "DRIFT" in dc.stdout


def test_a_series_left_out_while_the_version_changes_is_not_taken_for_a_holder(make_repo):
    repo = three_series(make_repo)
    lead(repo, "intermediate", V2)

    res = repo.promote("--refresh", "--exclude", "jax")
    assert res.returncode == 0, res.stderr
    record = repo.ledger()["assets"][ASSET]
    got = sources(repo)
    # jax's copy was not read: it is recorded at the version it was last seen at.
    assert got["jax"]["digest"] == got["programming"]["digest"] != record["digest"]
    assert got["jax"]["stale_since"]

    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    assert "asset-moved" not in dc.stdout

    # The next full refresh keeps the leader's version.
    repo.lecture("programming", "numba", lecture_text("Numba", INCLUDE + "\n\nFixed upstream."))
    repo.move_pin("programming")
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert repo.pool(ASSET).read_text(encoding="utf-8") == V2
    assert repo.ledger()["assets"][ASSET]["canonical"] == "intermediate"
    assert "digest" not in sources(repo)["intermediate"]
