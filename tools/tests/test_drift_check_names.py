"""The drift-check's names check: lecture names unique across the published
sites (QuantEcon/project-monorepo#11)."""

from conftest import lecture_text


def test_two_sites_publishing_different_lectures_under_one_name_is_drift(make_repo):
    repo = make_repo(["intermediate", "dp", "jax"], consumers=["dp"])
    repo.lecture("intermediate", "career", lecture_text("Career"))
    assert repo.promote("career").returncode == 0  # the check needs a ledger
    repo.lecture("intermediate", "ifp", lecture_text("Income Fluctuations"))
    repo.lecture("jax", "ifp", lecture_text("Income Fluctuations, in JAX", "A different lecture."))
    repo.lecture("dp", "ifp", lecture_text("Income Fluctuations (dp's older copy)"))
    repo.toc("intermediate", ["career", "ifp"])
    repo.toc("jax", ["ifp"])
    repo.toc("dp", ["ifp"])  # a consumer only republishes: never a second name

    res = repo.drift_check("--print-issues")

    assert res.returncode == 1, res.stdout
    assert ("[name-shared] lectures/ifp.md: jax and intermediate both publish a lecture named ifp, "
            "and they are different lectures") in res.stdout
    assert res.stdout.count("[name-shared]") == 1
    assert "### drift(jax): lectures/ifp.md is a different lecture from intermediate's" in res.stdout

    # The remedy is upstream: jax renames its copy (with a redirect there).
    jax = repo.root / "mirror" / "jax" / "lectures"
    (jax / "ifp.md").rename(jax / "ifp_jax.md")
    repo.toc("jax", ["ifp_jax"])
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout


def test_one_lecture_two_sites_publish_under_its_name_is_clean(make_repo):
    # The two copies differ only in how they spell an asset path.
    repo = make_repo(["programming", "intermediate"])
    repo.lecture("programming", "career", lecture_text("Career"))
    assert repo.promote("career").returncode == 0
    for series, ref in (
        ("programming", "/_static/lecture_specific/pandas_panel/fig.png"),
        ("intermediate", "_static/lecture_specific/pandas_panel/fig.png"),
    ):
        repo.mirror_file(series, "_static/lecture_specific/pandas_panel/fig.png", b"one figure")
        repo.lecture(series, "pandas_panel", lecture_text("Pandas for Panel Data", refs=[ref]))
        repo.toc(series, ["pandas_panel"])

    res = repo.drift_check()

    assert res.returncode == 0, res.stdout
    assert "clean:" in res.stdout


def test_a_pooled_name_another_site_starts_publishing_differently_is_drift(make_repo):
    repo = make_repo(["programming", "intermediate"])
    repo.lecture("intermediate", "lqcontrol", lecture_text("LQ Control"))
    repo.toc("intermediate", ["lqcontrol"])
    assert repo.promote("--toc", "intermediate").returncode == 0
    assert repo.drift_check().returncode == 0

    # promote never saw programming's copy: the ledger does not record it.
    repo.lecture("programming", "lqcontrol", lecture_text("LQ Control, an introduction"))
    repo.toc("programming", ["lqcontrol"])
    res = repo.drift_check()

    assert res.returncode == 1, res.stdout
    assert "[name-shared] lectures/lqcontrol.md: programming and intermediate both publish" in res.stdout


def test_only_the_sites_that_list_a_name_are_compared(make_repo):
    # intermediate, canonical for lqcontrol, stops listing it; advanced, a
    # recorded source, still does, and programming starts to with another text.
    repo = make_repo(["programming", "intermediate", "advanced"])
    text = lecture_text("LQ Control")
    repo.lecture("intermediate", "lqcontrol", text)
    repo.lecture("advanced", "lqcontrol", text)
    assert repo.promote("lqcontrol").returncode == 0
    assert repo.entry("lqcontrol")["canonical"] == "intermediate"
    repo.toc("intermediate", ["kalman"])
    repo.toc("advanced", ["lqcontrol"])
    repo.lecture("programming", "lqcontrol", lecture_text("LQ Control, an introduction"))
    repo.toc("programming", ["lqcontrol"])

    res = repo.drift_check()

    assert res.returncode == 1, res.stdout
    assert "[name-shared] lectures/lqcontrol.md: programming and advanced both publish" in res.stdout
    assert res.stdout.count("[name-shared]") == 1


def test_sites_that_agree_are_clean_though_the_pooled_copy_is_unlisted(make_repo):
    # The pool's copy came from intermediate, which stopped listing the name,
    # and the two sites that list it publish one text: no clash between sites.
    # promote refuses those copies when their series is promoted.
    repo = make_repo(["programming", "intermediate", "advanced"])
    repo.lecture("intermediate", "lqcontrol", lecture_text("LQ Control"))
    assert repo.promote("lqcontrol").returncode == 0
    repo.toc("intermediate", ["kalman"])
    rewritten = lecture_text("LQ Control", "Rewritten.")
    for series in ("programming", "advanced"):
        repo.lecture(series, "lqcontrol", rewritten)
        repo.toc(series, ["lqcontrol"])

    res = repo.drift_check()
    assert res.returncode == 0, res.stdout

    res = repo.promote("--toc", "programming")
    assert res.returncode == 1
    assert "[lqcontrol] FAILED" in res.stderr
