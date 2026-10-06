"""``promote --switch``: a series' lectures become canonical in the pool."""

import shutil
from datetime import datetime, timezone

from conftest import lecture_text


def promoted_repo(make_repo):
    """intermediate holds ``mccall`` (with a figure), intro holds ``lake``."""
    repo = make_repo(["intro", "intermediate", "dp"], consumers=["dp"])
    repo.mirror_file("intermediate", "_static/lecture_specific/mccall/fig.png", b"figure v1")
    repo.lecture("intermediate", "mccall", lecture_text("McCall", refs=["_static/lecture_specific/mccall/fig.png"]))
    repo.lecture("intro", "lake", lecture_text("Lake"))
    res = repo.promote("mccall", "lake")
    assert res.returncode == 0, res.stderr
    return repo


def test_switch_flips_the_series_entries_and_is_idempotent(make_repo):
    repo = promoted_repo(make_repo)

    res = repo.promote("--switch", "intermediate")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("mccall")
    assert entry["canonical"] == "pool"
    assert list(entry)[:2] == ["canonical", "switched_at"]
    assert entry["switched_at"] == {
        "series": "intermediate",
        "pin": repo.pin("intermediate"),
        "date": datetime.now(timezone.utc).date().isoformat(),
    }
    assert repo.entry("lake")["canonical"] == "intro"  # another series: untouched
    asset = repo.ledger()["assets"]["_static/mccall/fig.png"]
    assert asset["canonical"] == "pool" and asset["switched_at"]["series"] == "intermediate"
    assert "1 switched, 0 already switched, 1 assets switched" in res.stdout

    first = repo.ledger_path.read_bytes()
    res = repo.promote("--switch", "intermediate")
    assert res.returncode == 0, res.stderr
    assert "0 switched, 1 already switched, 0 assets switched" in res.stdout
    assert repo.ledger_path.read_bytes() == first


def test_switch_dry_run_writes_nothing(make_repo):
    repo = promoted_repo(make_repo)
    before = repo.ledger_path.read_bytes()

    res = repo.promote("--switch", "intermediate", "--dry-run")

    assert res.returncode == 0, res.stderr
    assert "[mccall] would switch" in res.stdout
    assert repo.ledger_path.read_bytes() == before


def test_drift_check_stops_guarding_a_switched_series(make_repo):
    repo = promoted_repo(make_repo)
    pool_copy = repo.pool("mccall.md")
    original = pool_copy.read_bytes()

    # Before the switch a pool edit is a violation.
    pool_copy.write_bytes(original + b"\nA fix made in the pool.\n")
    assert repo.drift_check().returncode == 2
    pool_copy.write_bytes(original)

    assert repo.promote("--switch", "intermediate").returncode == 0

    # After it the pool copy (and its asset) may be edited, and the series'
    # copies moving upstream are no longer compared.
    pool_copy.write_bytes(original + b"\nA fix made in the pool.\n")
    repo.pool("_static/mccall/fig.png").write_bytes(b"figure v2, redrawn in the pool")
    repo.lecture("intermediate", "mccall", lecture_text("McCall, edited upstream"))
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout
    assert "clean:" in res.stdout

    # The switched series' mirror is not even read any more.
    shutil.rmtree(repo.root / "mirror" / "intermediate")
    assert repo.drift_check().returncode == 0


def test_switch_refuses_an_unknown_or_consumer_series(make_repo):
    repo = promoted_repo(make_repo)
    before = repo.ledger_path.read_bytes()

    res = repo.promote("--switch", "nonesuch")
    assert res.returncode == 2
    assert "unknown series 'nonesuch'" in res.stderr

    res = repo.promote("--switch", "dp")
    assert res.returncode == 2
    assert "is a consumer" in res.stderr
    assert repo.ledger_path.read_bytes() == before


def test_switch_refuses_while_a_refresh_is_pending(make_repo):
    repo = promoted_repo(make_repo)
    before = repo.ledger_path.read_bytes()
    repo.move_pin("intermediate")

    res = repo.promote("--switch", "intermediate")

    assert res.returncode == 1
    assert "[mccall] FAILED" in res.stderr and "--refresh` first" in res.stderr
    assert repo.ledger_path.read_bytes() == before

    assert repo.promote("--refresh").returncode == 0
    assert repo.promote("--switch", "intermediate").returncode == 0
    assert repo.entry("mccall")["switched_at"]["pin"] == repo.pin("intermediate")


def test_a_switched_lecture_is_never_overwritten_from_the_mirror(make_repo):
    repo = promoted_repo(make_repo)
    assert repo.promote("--switch", "intermediate").returncode == 0
    edited = repo.pool("mccall.md").read_bytes() + b"\nA fix made in the pool.\n"
    repo.pool("mccall.md").write_bytes(edited)

    res = repo.promote("mccall")
    assert res.returncode == 1
    assert "is canonical in the pool (switched from intermediate" in res.stderr

    repo.move_pin("intermediate")
    res = repo.promote("--refresh")
    assert res.returncode == 0
    assert "nothing to refresh" in res.stdout
    assert repo.pool("mccall.md").read_bytes() == edited


def test_an_asset_shared_with_a_guarded_lecture_stays_guarded(make_repo):
    repo = make_repo(["intro", "intermediate"])
    shared = b"a figure both series use"
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/common/fig.png", shared)
    repo.lecture("intro", "lake", lecture_text("Lake", refs=["_static/lecture_specific/common/fig.png"]))
    repo.lecture("intermediate", "mccall", lecture_text("McCall", refs=["_static/lecture_specific/common/fig.png"]))
    assert repo.promote("lake", "mccall").returncode == 0
    path = "_static/_shared/common/fig.png"
    assert repo.ledger()["assets"][path]["canonical"] == "intro"

    assert repo.promote("--switch", "intermediate").returncode == 0
    assert repo.ledger()["assets"][path]["canonical"] == "intro"  # lake still uses it

    res = repo.promote("--switch", "intro")
    assert res.returncode == 0
    assert "1 assets switched" in res.stdout
    assert repo.ledger()["assets"][path]["canonical"] == "pool"
