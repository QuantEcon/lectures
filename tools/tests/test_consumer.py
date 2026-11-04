"""The consumer series class: never canonical, superseded, unwatched."""

from conftest import lecture_text


def test_consumer_copy_is_superseded_and_never_canonical(make_repo):
    # dp comes FIRST in manifest order: priority alone would make it canonical.
    repo = make_repo(["dp", "intermediate"], consumers=["dp"])
    repo.lecture("dp", "career", lecture_text("Career (an older copy)"))
    current = lecture_text("Career")
    repo.lecture("intermediate", "career", current)

    res = repo.promote("career")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("career")
    assert entry["canonical"] == "intermediate"
    assert [s["series"] for s in entry["sources"]] == ["intermediate"]
    assert [s["series"] for s in entry["superseded"]] == ["dp"]
    assert "divergent" not in entry and "interim" not in entry
    assert set(entry["promoted_at"]) == {"dp", "intermediate"}
    assert repo.pool("career.md").read_text(encoding="utf-8") == current


def test_identical_consumer_copy_is_superseded_not_a_source(make_repo):
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    text = lecture_text("Job Search")
    repo.lecture("intermediate", "mccall_model", text)
    repo.lecture("dp", "mccall_model", text)

    assert repo.promote("mccall_model").returncode == 0
    entry = repo.entry("mccall_model")
    assert [s["series"] for s in entry["sources"]] == ["intermediate"]
    assert [s["series"] for s in entry["superseded"]] == ["dp"]


def test_a_lecture_held_only_by_a_consumer_is_refused(make_repo):
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    repo.lecture("dp", "dp_only", lecture_text("Only in dp"))

    res = repo.promote("dp_only")

    assert res.returncode == 1
    assert "held only by consumer series (dp)" in res.stderr
    assert not repo.pool("dp_only.md").exists()


def test_a_pool_lecture_its_home_series_dropped_is_refused_as_removed(make_repo):
    # dp still republishes its copy. The refusal names the removal, as the
    # drift-check does, not the consumer that kept a copy.
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    repo.lecture("intermediate", "lqcontrol", lecture_text("LQ Control"))
    repo.lecture("dp", "lqcontrol", lecture_text("LQ Control (dp's older copy)"))
    assert repo.promote("lqcontrol").returncode == 0
    (repo.root / "mirror" / "intermediate" / "lectures" / "lqcontrol.md").unlink()
    repo.move_pin("intermediate")

    res = repo.promote("--refresh")

    assert res.returncode == 1
    failed = [line for line in res.stderr.splitlines() if line.startswith("[lqcontrol] FAILED")]
    assert len(failed) == 1, res.stderr
    assert "(removed or renamed upstream?); only consumer series (dp) still do" in failed[0]
    assert "canonical-removed" in failed[0]
    assert "held only by consumer" not in failed[0]
    assert "[canonical-removed]" in repo.drift_check().stdout


def test_a_refusal_names_a_holder_the_run_excludes(make_repo):
    # dp's toc lists a lecture whose only home, jax, this run leaves out.
    repo = make_repo(["intermediate", "dp", "jax"], consumers=["dp"])
    text = lecture_text("Neural Nets")
    repo.lecture("jax", "jax_nn", text)
    repo.lecture("dp", "jax_nn", text)
    repo.toc("dp", ["jax_nn"])

    res = repo.promote("--toc", "dp", "--exclude", "jax")

    assert res.returncode == 1
    assert "held only by consumer series (dp)" in res.stderr
    assert "; jax, excluded from this run, holds a copy" in res.stderr
    assert not repo.pool("jax_nn.md").exists()


def test_a_consumer_toc_promotes_each_lecture_from_its_canonical_home(make_repo):
    repo = make_repo(["intermediate", "advanced", "dp"], consumers=["dp"])
    repo.lecture("intermediate", "jv", lecture_text("Job Search VI"))
    repo.lecture("advanced", "amss", lecture_text("AMSS"))
    repo.lecture("dp", "jv", lecture_text("Job Search V (older)"))
    repo.lecture("dp", "amss", lecture_text("AMSS"))
    repo.toc("dp", ["jv", "amss"])

    res = repo.promote("--toc", "dp")

    assert res.returncode == 0, res.stderr
    assert repo.entry("jv")["canonical"] == "intermediate"
    assert repo.entry("amss")["canonical"] == "advanced"
    for slug in ("jv", "amss"):
        assert [s["series"] for s in repo.entry(slug)["superseded"]] == ["dp"]


def test_a_refresh_that_considers_the_consumer_keeps_its_superseded_rows(make_repo):
    # CI's refresh leaves out PROMOTE_EXCLUDE, which never lists a consumer: a
    # refresh that excluded dp would strip these rows and dp's pin (#19).
    repo = make_repo(["intermediate", "dp", "jax"], consumers=["dp"])
    repo.lecture("intermediate", "career", lecture_text("Career"))
    repo.lecture("dp", "career", lecture_text("Career (dp's older copy)"))
    repo.toc("dp", ["career"])
    assert repo.promote("--toc", "dp", "--exclude", "jax").returncode == 0
    repo.lecture("intermediate", "career", lecture_text("Career", "Edited upstream."))
    repo.move_pin("intermediate")
    repo.move_pin("dp")

    res = repo.promote("--refresh", "--exclude", "jax")

    assert res.returncode == 0, res.stderr
    assert "Edited upstream." in repo.pool("career.md").read_text(encoding="utf-8")
    entry = repo.entry("career")
    assert [s["series"] for s in entry["superseded"]] == ["dp"]
    assert entry["promoted_at"]["dp"] == repo.pin("dp")


def test_drift_check_does_not_watch_a_consumers_copies(make_repo):
    repo = make_repo(["intermediate", "advanced", "dp"], consumers=["dp"])
    text = lecture_text("Optimal Taxation")
    repo.lecture("intermediate", "opt_tax", text)
    repo.lecture("advanced", "opt_tax", text)  # an identical, watched source
    repo.lecture("dp", "opt_tax", lecture_text("Optimal Taxation (older)"))
    assert repo.promote("opt_tax").returncode == 0
    assert repo.drift_check().returncode == 0

    # The consumer's stale copy moves again: nothing to report.
    repo.lecture("dp", "opt_tax", lecture_text("Optimal Taxation (older still)"))
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout
    assert "clean:" in res.stdout

    # Control: a canonical-eligible source moving IS drift.
    repo.lecture("advanced", "opt_tax", lecture_text("Optimal Taxation, edited in advanced"))
    res = repo.drift_check()
    assert res.returncode == 1
    assert "the advanced copy lectures/opt_tax.md no longer matches" in res.stdout


def test_drift_check_watches_a_consumers_accepted_toc(make_repo):
    # The pool's dp selection is promoted from dp's toc, so the toc is watched
    # although dp's copies are not.
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    repo.lecture("intermediate", "career", lecture_text("Career"))
    repo.toc("dp", ["career"])
    assert repo.promote("--toc", "dp").returncode == 0
    assert repo.drift_check("--accept-toc", "dp").returncode == 0
    assert repo.drift_check().returncode == 0

    repo.lecture("intermediate", "mccall_model", lecture_text("Job Search"))
    repo.toc("dp", ["career", "mccall_model"])
    res = repo.drift_check("--print-issues")
    assert res.returncode == 1
    assert "[toc-changed] dp: lectures/_toc.yml changed since it was accepted" in res.stdout
    assert "re-run `tools/promote --toc dp`" in res.stdout

    # The remedy clears it: promote from the new toc, then re-accept.
    assert repo.promote("--toc", "dp").returncode == 0
    assert repo.pool("mccall_model.md").exists()
    assert repo.drift_check("--accept-toc", "dp").returncode == 0
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout


def test_an_accepted_toc_listing_a_lecture_the_pool_lacks_is_drift(make_repo):
    # Accepting a toc clears toc-changed whether or not the pool followed it.
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    repo.lecture("intermediate", "career", lecture_text("Career"))
    repo.lecture("intermediate", "mccall_model", lecture_text("Job Search"))
    repo.toc("dp", ["career"])
    assert repo.promote("--toc", "dp").returncode == 0
    assert repo.drift_check("--accept-toc", "dp").returncode == 0

    repo.toc("dp", ["career", "mccall_model"])
    assert repo.drift_check("--accept-toc", "dp").returncode == 0  # re-accepted, never promoted
    res = repo.drift_check("--print-issues")

    assert res.returncode == 1, res.stdout
    assert ("[toc-unpromoted] dp: the accepted lectures/_toc.yml lists 1 lecture(s) the pool does not hold: "
            "mccall_model") in res.stdout
    assert "### drift(dp): _toc.yml lists lectures the pool does not hold" in res.stdout
    assert "[toc-changed]" not in res.stdout

    assert repo.promote("--toc", "dp").returncode == 0
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout


def test_drift_check_honours_a_class_declared_after_promotion(make_repo):
    # A ledger written while dp was an ordinary series lists dp as a source;
    # declaring dp a consumer afterwards stops its copy being watched.
    repo = make_repo(["intermediate", "dp"])
    text = lecture_text("Career")
    repo.lecture("intermediate", "career", text)
    repo.lecture("dp", "career", text)
    assert repo.promote("career").returncode == 0
    assert [s["series"] for s in repo.entry("career")["sources"]] == ["intermediate", "dp"]

    repo.lecture("dp", "career", lecture_text("Career (dp edit)"))
    assert repo.drift_check().returncode == 1  # an ordinary series: drift

    repo.write_manifest(consumers=["dp"])
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout
    assert "clean:" in res.stdout
