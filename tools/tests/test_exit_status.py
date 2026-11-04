"""An error stops a check with exit 2, never with the status that means a
finding (drift-check) or a broken rule (pool-check)."""

from conftest import lecture_text


def test_pool_check_exits_two_on_an_error(make_repo):
    repo = make_repo(["intro"])
    lecture = repo.pool("kalman.md")
    lecture.write_bytes(b"\xff\xfe not UTF-8 text")
    res = repo.pool_check()
    assert res.returncode == 2, res.stdout
    assert "error: lectures/kalman.md is not UTF-8 text" in res.stderr

    promote = repo.root / "tools" / "promote"
    promote.write_text("raise SystemExit(1)\n", encoding="utf-8")
    res = repo.pool_check()
    assert res.returncode == 2, res.stdout
    assert "error: tools/promote could not be loaded: it exited with status 1" in res.stderr

    promote.write_text("def broken(:\n", encoding="utf-8")
    res = repo.pool_check()
    assert res.returncode == 2, res.stdout
    assert "pool-check: internal error: SyntaxError" in res.stderr


def test_drift_check_exits_two_on_an_internal_error(make_repo):
    # drift-check.yml takes 1 as findings to handle, so a crash that exited 1
    # would leave the check job green with no report.
    repo = make_repo(["intermediate", "programming"])
    repo.lecture("intermediate", "career", lecture_text("Career"))
    repo.toc("intermediate", ["career"])
    assert repo.promote("career").returncode == 0
    assert repo.drift_check().returncode == 0
    (repo.root / "tools" / "promote").write_text("def broken(:\n", encoding="utf-8")

    res = repo.drift_check()

    assert res.returncode == 2, res.stdout
    assert "drift-check: internal error: SyntaxError" in res.stderr
