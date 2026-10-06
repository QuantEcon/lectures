"""Same-name collisions, the canonical map, jax by default, byte stability."""

from conftest import lecture_text


def test_identical_copies_keep_the_highest_priority_series_canonical(make_repo):
    repo = make_repo(["intro", "intermediate"])
    text = lecture_text("Shared")
    repo.lecture("intro", "shared", text)
    repo.lecture("intermediate", "shared", text)

    res = repo.promote("shared")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("shared")
    assert entry["canonical"] == "intro"
    assert [s["series"] for s in entry["sources"]] == ["intro", "intermediate"]
    assert "divergent" not in entry and "interim" not in entry
    assert repo.pool("shared.md").read_text(encoding="utf-8") == text


def test_differing_copy_is_an_error_naming_the_lecture_and_both_series(make_repo):
    repo = make_repo(["intro", "intermediate"])
    repo.lecture("intro", "lake_model", lecture_text("A Lake Model of Employment"))
    repo.lecture("intermediate", "lake_model", lecture_text("A Lake Model of Unemployment"))

    res = repo.promote("lake_model")

    assert res.returncode == 1
    failed = [line for line in res.stderr.splitlines() if line.startswith("[lake_model] FAILED")]
    assert len(failed) == 1, res.stderr
    assert "lake_model.md differs across series" in failed[0]
    assert "intro:" in failed[0] and "intermediate:" in failed[0]
    assert "sync/canonical.yml" in failed[0]
    # Nothing was overwritten or recorded.
    assert not repo.pool("lake_model.md").exists()
    assert not repo.ledger_path.exists()


def test_run_order_never_decides_a_collision(make_repo):
    # Asking for the lower-priority series' toc used to make its copy win
    # (recorded as interim); it is now the same error.
    repo = make_repo(["intro", "intermediate"])
    repo.lecture("intro", "lln_clt", lecture_text("LLN and CLT (intro)"))
    repo.lecture("intermediate", "lln_clt", lecture_text("LLN and CLT (intermediate)"))
    repo.toc("intermediate", ["lln_clt"])

    res = repo.promote("--toc", "intermediate")

    assert res.returncode == 1
    assert "[lln_clt] FAILED: lln_clt.md differs across series" in res.stderr
    assert not repo.ledger_path.exists()


def test_three_way_collision_names_every_series(make_repo):
    repo = make_repo(["intro", "intermediate", "jax"])
    for series in ("intro", "intermediate", "jax"):
        repo.lecture(series, "mle", lecture_text(f"Maximum Likelihood ({series})"))

    res = repo.promote("mle")

    assert res.returncode == 1
    line = next(l for l in res.stderr.splitlines() if l.startswith("[mle] FAILED"))
    for series in ("intro:", "intermediate:", "jax:"):
        assert series in line


def test_canonical_map_resolves_a_collision(make_repo):
    repo = make_repo(["intro", "intermediate"])
    repo.lecture("intro", "lake_model", lecture_text("Lake (intro)"))
    winner = lecture_text("Lake (intermediate)")
    repo.lecture("intermediate", "lake_model", winner)
    repo.write_canonical_map({"lake_model": "intermediate"})

    res = repo.promote("lake_model")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("lake_model")
    assert entry["canonical"] == "intermediate"
    assert entry["interim"] is True
    assert [s["series"] for s in entry["sources"]] == ["intermediate"]
    assert [s["series"] for s in entry["divergent"]] == ["intro"]
    assert set(entry["promoted_at"]) == {"intro", "intermediate"}
    assert repo.pool("lake_model.md").read_text(encoding="utf-8") == winner


def test_canonical_map_rejects_unknown_and_consumer_series(make_repo):
    repo = make_repo(["intermediate", "dp"], consumers=["dp"])
    repo.lecture("intermediate", "career", lecture_text("Career"))

    repo.write_canonical_map({"career": "dp"})
    res = repo.promote("career")
    assert res.returncode != 0
    assert "consumer series and is never canonical" in res.stderr

    repo.write_canonical_map({"career": "nonesuch"})
    res = repo.promote("career")
    assert res.returncode != 0
    assert "unknown series 'nonesuch'" in res.stderr


def test_canonical_map_entry_that_settles_nothing_warns(make_repo):
    repo = make_repo(["intro", "intermediate"])
    text = lecture_text("Shared")
    repo.lecture("intro", "shared", text)
    repo.lecture("intermediate", "shared", text)
    repo.write_canonical_map({"shared": "intermediate"})

    res = repo.promote("shared")

    assert res.returncode == 0, res.stderr
    assert "settles nothing" in res.stdout
    assert repo.entry("shared")["canonical"] == "intermediate"


def test_jax_is_considered_by_default(make_repo):
    repo = make_repo(["intro", "jax"])
    text = lecture_text("Same everywhere")
    repo.lecture("intro", "same", text)
    repo.lecture("jax", "same", text)
    repo.lecture("intro", "schelling", lecture_text("Schelling (intro)"))
    repo.lecture("jax", "schelling", lecture_text("Schelling (jax)"))

    res = repo.promote("same")
    assert res.returncode == 0, res.stderr
    assert [s["series"] for s in repo.entry("same")["sources"]] == ["intro", "jax"]

    res = repo.promote("schelling")
    assert res.returncode == 1
    assert "schelling.md differs across series" in res.stderr and "jax:" in res.stderr

    # --exclude remains the per-run way to leave a series out.
    res = repo.promote("schelling", "--exclude", "jax")
    assert res.returncode == 0, res.stderr
    assert [s["series"] for s in repo.entry("schelling")["sources"]] == ["intro"]


def test_copies_differing_only_in_asset_path_spelling_are_one_lecture(make_repo):
    repo = make_repo(["intro", "intermediate"])
    figure = b"\x89PNG fake figure bytes"
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/short_path/graph.png", figure)
    # Root-relative in one series, file-relative in the other: both normalise
    # to the same pool path, so they are the same lecture.
    repo.lecture("intro", "short_path", lecture_text("Shortest Paths", refs=["/_static/lecture_specific/short_path/graph.png"]))
    repo.lecture("intermediate", "short_path", lecture_text("Shortest Paths", refs=["_static/lecture_specific/short_path/graph.png"]))

    res = repo.promote("short_path")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("short_path")
    assert entry["canonical"] == "intro"
    assert [s["series"] for s in entry["sources"]] == ["intro", "intermediate"]
    assert entry["sources"][0]["digest"] != entry["sources"][1]["digest"]
    assert "divergent" not in entry
    assert entry["assets"] == ["_static/short_path/graph.png"]
    assert repo.pool("_static/short_path/graph.png").read_bytes() == figure


def test_ledger_write_is_byte_stable(make_repo):
    repo = make_repo(["intro", "intermediate", "dp"], consumers=["dp"])
    figure = b"figure bytes"
    repo.mirror_file("intermediate", "_static/lecture_specific/mccall/fig.png", figure)
    repo.lecture("intermediate", "mccall", lecture_text("McCall", refs=["_static/lecture_specific/mccall/fig.png"]))
    repo.lecture("dp", "mccall", lecture_text("McCall, an older copy"))
    repo.lecture("intro", "lake_model", lecture_text("Lake (intro)"))
    repo.lecture("intermediate", "lake_model", lecture_text("Lake (intermediate)"))
    repo.write_canonical_map({"lake_model": "intermediate"})

    assert repo.promote("mccall", "lake_model").returncode == 0
    first = repo.ledger_path.read_bytes()

    res = repo.promote("mccall", "lake_model")
    assert res.returncode == 0, res.stderr
    assert "2 unchanged" in res.stdout
    assert repo.ledger_path.read_bytes() == first

    res = repo.promote("--refresh")
    assert res.returncode == 0
    assert "nothing to refresh" in res.stdout
    assert repo.ledger_path.read_bytes() == first
