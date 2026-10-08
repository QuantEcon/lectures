"""drift-check judges a non-canonical copy by promotion's own rule: the same
lecture when byte-identical, or identical once asset references are
normalised to their pool paths (QuantEcon/lectures#15)."""

from conftest import lecture_text

FIG = "_static/lecture_specific/short_path/graph.png"


def short_path_repo(make_repo):
    """intro (canonical) spells the figure root-relative, intermediate
    file-relative; promote admits both as one lecture."""
    repo = make_repo(["intro", "intermediate"])
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, FIG, b"png")
    repo.lecture("intro", "short_path", lecture_text("Shortest Paths", refs=["/" + FIG]))
    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths", refs=[FIG]))
    res = repo.promote("short_path")
    assert res.returncode == 0, res.stderr
    entry = repo.entry("short_path")
    assert [s["series"] for s in entry["sources"]] == ["intro", "intermediate"]
    assert entry["sources"][0]["digest"] != entry["sources"][1]["digest"]
    assert repo.drift_check().returncode == 0
    return repo


def test_a_source_moving_in_lockstep_with_canonical_is_not_drift(make_repo):
    repo = short_path_repo(make_repo)

    # The same upstream edit lands in both series; the spelling still differs.
    repo.lecture("intro", "short_path", lecture_text("Shortest Paths", "edited", refs=["/" + FIG]))
    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths", "edited", refs=[FIG]))
    res = repo.drift_check()

    assert res.returncode == 1, res.stdout  # the refresh finding alone
    assert "[canonical-moved]" in res.stdout
    assert "[diverged]" not in res.stdout
    assert "[converged] lectures/short_path.md: the intermediate copy changed and now matches intro up to asset path spelling" in res.stdout


def test_a_source_changing_only_its_asset_spelling_is_not_drift(make_repo):
    repo = short_path_repo(make_repo)

    # intermediate adopts a third spelling of the same reference.
    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths", refs=["./" + FIG]))
    res = repo.drift_check()

    assert res.returncode == 0, res.stdout
    assert "[diverged]" not in res.stdout
    assert "up to asset path spelling" in res.stdout


def test_a_source_edited_on_its_own_is_still_drift(make_repo):
    repo = short_path_repo(make_repo)

    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths", "edited in intermediate", refs=[FIG]))
    res = repo.drift_check()

    assert res.returncode == 1
    assert "[diverged] lectures/short_path.md: the intermediate copy lectures/short_path.md no longer matches its canonical home in intro" in res.stdout


def test_a_divergent_copy_converging_up_to_spelling_is_reported_as_converged(make_repo):
    repo = make_repo(["intro", "intermediate"])
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, FIG, b"png")
    repo.lecture("intro", "short_path", lecture_text("Shortest Paths", refs=["/" + FIG]))
    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths (intermediate)", refs=[FIG]))
    repo.write_canonical_map({"short_path": "intro"})
    assert repo.promote("short_path").returncode == 0
    assert repo.entry("short_path")["interim"] is True
    assert repo.drift_check().returncode == 0

    # intermediate converges on intro's text, keeping its own spelling.
    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths", refs=[FIG]))
    res = repo.drift_check()

    assert res.returncode == 0, res.stdout
    assert "[converged] lectures/short_path.md: the divergent intermediate copy now matches intro up to asset path spelling — the interim entry can be re-promoted" in res.stdout
