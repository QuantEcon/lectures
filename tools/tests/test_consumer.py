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
