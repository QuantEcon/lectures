"""Retiring a lecture that was renamed or removed upstream.

``--toc SERIES`` retires the entries canonical in SERIES whose lecture left
its toc, whose canonical copy is gone and whose name no series holds;
``--retire SLUG`` retires by name; ``--refresh`` never retires."""

from conftest import lecture_text


def promoted(make_repo, slugs=("mccall", "lqcontrol"), series=("intermediate", "advanced")):
    repo = make_repo(list(series))
    for slug in slugs:
        repo.lecture("intermediate", slug, lecture_text(slug))
    repo.toc("intermediate", slugs)
    res = repo.promote("--toc", "intermediate")
    assert res.returncode == 0, res.stderr
    return repo


def drop(repo, series, slug):
    (repo.root / "mirror" / series / "lectures" / f"{slug}.md").unlink()


def test_a_removed_lecture_is_retired_by_the_toc_run(make_repo):
    repo = promoted(make_repo)
    drop(repo, "intermediate", "lqcontrol")
    repo.toc("intermediate", ["mccall"])
    repo.move_pin("intermediate")

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 0, res.stderr
    assert "[lqcontrol] retired: lectures/lqcontrol.md and its ledger entry removed" in res.stdout
    assert ", 1 retired" in res.stdout and "RETIRED: lqcontrol" in res.stdout
    assert "lectures/lqcontrol.md" not in repo.ledger()
    assert not repo.pool("lqcontrol.md").exists()
    assert repo.pool("mccall.md").is_file()
    assert repo.drift_check("--accept-toc", "intermediate").returncode == 0
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout


def test_a_renamed_lecture_is_retired_and_promoted_under_its_new_name(make_repo):
    repo = promoted(make_repo)
    drop(repo, "intermediate", "lqcontrol")
    repo.lecture("intermediate", "lq_control", lecture_text("lqcontrol"))
    repo.toc("intermediate", ["mccall", "lq_control"])
    repo.move_pin("intermediate")

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 0, res.stderr
    ledger = repo.ledger()
    assert "lectures/lqcontrol.md" not in ledger and "lectures/lq_control.md" in ledger
    assert not repo.pool("lqcontrol.md").exists() and repo.pool("lq_control.md").is_file()


def test_a_renamed_lecture_takes_its_own_assets_with_it(make_repo):
    # The `coase` case: the lecture's figures live in a folder named for it.
    repo = make_repo(["intro"])
    repo.mirror_file("intro", "_static/lecture_specific/coase/fig.png", b"png-bytes")
    repo.mirror_file("intro", "_static/lecture_specific/shared/both.png", b"both-bytes")
    refs = ["_static/lecture_specific/coase/fig.png", "_static/lecture_specific/shared/both.png"]
    repo.lecture("intro", "coase", lecture_text("Coase", refs=refs))
    repo.lecture("intro", "markets", lecture_text("Markets", refs=refs[1:]))
    repo.toc("intro", ["coase", "markets"])
    assert repo.promote("--toc", "intro").returncode == 0
    assert repo.pool("_static/coase/fig.png").is_file()

    drop(repo, "intro", "coase")
    (repo.root / "mirror" / "intro" / "lectures" / refs[0]).unlink()
    repo.mirror_file("intro", "_static/lecture_specific/theory_of_the_firm/fig.png", b"png-bytes")
    repo.lecture("intro", "theory_of_the_firm", lecture_text(
        "Coase", refs=["_static/lecture_specific/theory_of_the_firm/fig.png", refs[1]]))
    repo.toc("intro", ["theory_of_the_firm", "markets"])
    repo.move_pin("intro")

    res = repo.promote("--toc", "intro")

    assert res.returncode == 0, res.stderr
    assert "[ledger] pruned stale asset: _static/coase/fig.png" in res.stdout
    assert not repo.pool("_static/coase").exists()
    assert repo.pool("_static/theory_of_the_firm/fig.png").is_file()
    # The asset the retired lecture shared stays, for the lecture still using it.
    assert repo.pool("_static/_shared/shared/both.png").is_file()
    ledger = repo.ledger()
    assert "lectures/coase.md" not in ledger
    assert "_static/coase/fig.png" not in ledger["assets"]
    assert repo.drift_check("--accept-toc", "intro").returncode == 0
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    assert repo.pool_check().returncode == 0


def test_a_lecture_another_series_still_holds_is_not_retired_on_its_own(make_repo):
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    for series in ("intermediate", "dp"):
        repo.lecture(series, "lqcontrol", lecture_text("LQ"))
    repo.lecture("intermediate", "mccall", lecture_text("McCall"))
    repo.toc("intermediate", ["mccall", "lqcontrol"])
    assert repo.promote("--toc", "intermediate").returncode == 0
    drop(repo, "intermediate", "lqcontrol")
    repo.toc("intermediate", ["mccall"])
    repo.move_pin("intermediate")

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 0, res.stderr
    assert "[lqcontrol] WARN: left intermediate's toc and its canonical copy is gone, but dp still holds lqcontrol.md" in res.stdout
    assert "tools/promote --retire lqcontrol" in res.stdout
    assert "lectures/lqcontrol.md" in repo.ledger()
    assert repo.pool("lqcontrol.md").is_file()

    # By name it goes, with a warning that dp still holds it.
    res = repo.promote("--retire", "lqcontrol")
    assert res.returncode == 0, res.stderr
    assert "[lqcontrol] WARN: dp still holds lqcontrol.md" in res.stdout
    assert "summary [retire]" in res.stdout
    assert "lectures/lqcontrol.md" not in repo.ledger()
    assert not repo.pool("lqcontrol.md").exists()


def test_a_lecture_out_of_the_toc_whose_copy_remains_is_not_retired_on_its_own(make_repo):
    repo = promoted(make_repo)
    repo.toc("intermediate", ["mccall"])
    repo.move_pin("intermediate")

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 0, res.stderr
    assert "retired" not in res.stdout
    assert "lectures/lqcontrol.md" in repo.ledger()

    assert repo.promote("--retire", "lqcontrol").returncode == 0
    assert "lectures/lqcontrol.md" not in repo.ledger()


def test_more_than_the_cap_retires_none_and_fails(make_repo):
    slugs = [f"lec{i}" for i in range(7)]
    repo = promoted(make_repo, slugs=slugs)
    before = repo.ledger_path.read_bytes()
    for slug in slugs[1:]:
        drop(repo, "intermediate", slug)
    repo.toc("intermediate", slugs[:1])
    repo.move_pin("intermediate")

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 1
    assert "6 lectures canonical in intermediate have left its toc" in res.stderr
    assert "More than 5 are never retired by a --toc run" in res.stderr
    assert "tools/promote --retire lec1 lec2 lec3 lec4 lec5 lec6" in res.stderr
    assert repo.ledger_path.read_bytes() == before
    assert all(repo.pool(f"{slug}.md").is_file() for slug in slugs)

    # By name, the same six go.
    res = repo.promote("--retire", *slugs[1:])
    assert res.returncode == 0, res.stderr
    assert sorted(k for k in repo.ledger() if k != "assets") == ["lectures/lec0.md"]


def test_retire_refuses_a_lecture_still_in_its_toc_and_retires_none(make_repo):
    repo = promoted(make_repo)
    drop(repo, "intermediate", "lqcontrol")
    repo.toc("intermediate", ["mccall"])
    before = repo.ledger_path.read_bytes()

    res = repo.promote("--retire", "lqcontrol", "mccall")

    assert res.returncode == 1
    assert "[mccall] FAILED: not retired: intermediate's _toc.yml still lists it" in res.stderr
    assert "nothing was retired" in res.stderr
    assert repo.ledger_path.read_bytes() == before
    assert repo.pool("lqcontrol.md").is_file()

    res = repo.promote("--retire", "nosuch")
    assert res.returncode == 1
    assert "lectures/nosuch.md is not in the ledger" in res.stderr


def test_retirement_never_acts_on_a_series_out_of_the_manifest(make_repo):
    # A series the pool has taken over leaves the manifest: its lectures are
    # the pool's own, and nothing retires them.
    repo = make_repo(["intro", "extra"])
    repo.lecture("extra", "only_extra", lecture_text("Only in extra"))
    repo.lecture("intro", "kept", lecture_text("Kept"))
    repo.toc("intro", ["kept"])
    assert repo.promote("only_extra", "kept").returncode == 0
    repo.order = ["intro"]
    repo.write_manifest()
    repo.write_state({"intro": repo.pin("intro")})

    res = repo.promote("--retire", "only_extra")
    assert res.returncode == 1
    assert "its canonical series 'extra' is not in sync/manifest.yml" in res.stderr
    assert "retirement never acts on it" in res.stderr

    res = repo.promote("--toc", "intro")
    assert res.returncode == 0, res.stderr
    assert "lectures/only_extra.md" in repo.ledger()
    assert repo.pool("only_extra.md").is_file()


def test_a_dry_run_retires_nothing(make_repo):
    repo = promoted(make_repo)
    drop(repo, "intermediate", "lqcontrol")
    repo.toc("intermediate", ["mccall"])
    before = repo.ledger_path.read_bytes()

    res = repo.promote("--toc", "intermediate", "--dry-run")

    assert res.returncode == 0, res.stderr
    assert "[lqcontrol] would retire: lectures/lqcontrol.md and its ledger entry" in res.stdout
    assert repo.ledger_path.read_bytes() == before
    assert repo.pool("lqcontrol.md").is_file()


def test_retire_needs_slugs_and_no_other_mode(make_repo):
    repo = promoted(make_repo)
    assert repo.promote("--retire").returncode == 2
    assert repo.promote("--retire", "--refresh").returncode == 2
    assert repo.promote("--retire", "mccall", "--toc", "intermediate").returncode == 2


def test_an_empty_toc_retires_nothing(make_repo):
    repo = promoted(make_repo)
    drop(repo, "intermediate", "lqcontrol")
    repo.mirror_file("intermediate", "_toc.yml", "")
    before = repo.ledger_path.read_bytes()

    res = repo.promote("--toc", "intermediate")
    assert "retired" not in res.stdout
    assert repo.ledger_path.read_bytes() == before

    # By name, a lecture whose copy remains is refused: the toc shows nothing.
    res = repo.promote("--retire", "mccall")
    assert res.returncode == 1
    assert "its canonical copy still exists in intermediate" in res.stderr


def test_retiring_warns_of_lectures_that_link_to_it(make_repo):
    repo = make_repo(["intermediate"])
    repo.lecture("intermediate", "lqcontrol", lecture_text("LQ"))
    repo.lecture("intermediate", "mccall", lecture_text("McCall", "See {doc}`lqcontrol` and {doc}`LQ <lqcontrol>`."))
    repo.toc("intermediate", ["mccall", "lqcontrol"])
    assert repo.promote("--toc", "intermediate").returncode == 0
    drop(repo, "intermediate", "lqcontrol")
    repo.toc("intermediate", ["mccall"])

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 0, res.stderr
    assert "[lqcontrol] WARN: 1 pool lecture(s) link to lqcontrol with {doc} and will not resolve it: mccall" in res.stdout


def test_a_lecture_moved_into_a_subfolder_is_retired_and_promoted_there(make_repo):
    repo = promoted(make_repo)
    drop(repo, "intermediate", "lqcontrol")
    repo.lecture("intermediate", "sub/lqcontrol", lecture_text("lqcontrol"))
    repo.toc("intermediate", ["mccall", "sub/lqcontrol"])
    repo.move_pin("intermediate")

    res = repo.promote("--toc", "intermediate")
    assert res.returncode == 0, res.stderr
    ledger = repo.ledger()
    assert "lectures/lqcontrol.md" not in ledger and "lectures/sub/lqcontrol.md" in ledger
    assert not repo.pool("lqcontrol.md").exists() and repo.pool("sub/lqcontrol.md").is_file()

    # A second run retires nothing and does not stop, and the refresh does
    # not take the moved lecture for one whose copy is gone.
    res = repo.promote("--toc", "intermediate")
    assert res.returncode == 0, res.stderr
    assert "retired" not in res.stdout
    repo.move_pin("intermediate", 3)
    res = repo.promote("--refresh")
    assert "canonical copy is gone" not in res.stdout + res.stderr

    # Moved back out, the subfolder entry is the one retired, and its folder goes.
    drop(repo, "intermediate", "sub/lqcontrol")
    repo.lecture("intermediate", "lqcontrol", lecture_text("lqcontrol"))
    repo.toc("intermediate", ["mccall", "lqcontrol"])
    res = repo.promote("--toc", "intermediate")
    assert res.returncode == 0, res.stderr
    assert "lectures/sub/lqcontrol.md" not in repo.ledger()
    assert not repo.pool("sub").exists() and repo.pool("lqcontrol.md").is_file()


def test_retire_refuses_a_lecture_another_source_series_still_publishes(make_repo):
    repo = make_repo(["intermediate", "advanced"])
    for series in repo.order:
        repo.lecture(series, "lqcontrol", lecture_text("LQ"))
    repo.toc("intermediate", ["lqcontrol"])
    repo.toc("advanced", ["lqcontrol"])
    assert repo.promote("--toc", "intermediate").returncode == 0
    drop(repo, "intermediate", "lqcontrol")
    repo.toc("intermediate", ["other"])
    repo.lecture("intermediate", "other", lecture_text("Other"))

    res = repo.promote("--retire", "lqcontrol")
    assert res.returncode == 1
    assert "advanced still holds it and lists it in its _toc.yml" in res.stderr
    assert "`tools/promote lqcontrol` re-homes it there" in res.stderr

    assert repo.promote("lqcontrol").returncode == 0
    assert repo.entry("lqcontrol")["canonical"] == "advanced"
