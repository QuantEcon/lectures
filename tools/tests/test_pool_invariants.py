"""Pool invariants the drift-check and promote guard (kept from the switch
tests when --switch moved out of this pull request)."""

from conftest import lecture_text


def test_a_direct_pool_edit_is_a_violation(make_repo):
    repo = make_repo(["intro", "intermediate"])
    repo.mirror_file("intermediate", "_static/lecture_specific/mccall/fig.png", b"figure v1")
    repo.lecture("intermediate", "mccall", lecture_text("McCall", refs=["_static/lecture_specific/mccall/fig.png"]))
    assert repo.promote("mccall").returncode == 0
    assert repo.drift_check().returncode == 0

    lecture = repo.pool("mccall.md")
    original = lecture.read_bytes()
    lecture.write_bytes(original + b"\nA fix made in the pool.\n")
    res = repo.drift_check()
    assert res.returncode == 2, res.stdout
    assert "[pool-edited] lectures/mccall.md" in res.stdout
    lecture.write_bytes(original)

    repo.pool("_static/mccall/fig.png").write_bytes(b"figure v2, redrawn in the pool")
    res = repo.drift_check()
    assert res.returncode == 2, res.stdout
    assert "[asset-edited] lectures/_static/mccall/fig.png" in res.stdout


def test_an_asset_two_lectures_use_is_shared(make_repo):
    repo = make_repo(["intro", "intermediate"])
    shared = b"a figure both series use"
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/common/fig.png", shared)
    repo.lecture("intro", "lake", lecture_text("Lake", refs=["_static/lecture_specific/common/fig.png"]))
    repo.lecture("intermediate", "mccall", lecture_text("McCall", refs=["_static/lecture_specific/common/fig.png"]))
    assert repo.promote("lake", "mccall").returncode == 0
    path = "_static/_shared/common/fig.png"
    assert list(repo.ledger()["assets"]) == [path]
    assert repo.pool(path).read_bytes() == shared
    assert path in repo.entry("lake")["assets"] and path in repo.entry("mccall")["assets"]
    assert repo.drift_check().returncode == 0
