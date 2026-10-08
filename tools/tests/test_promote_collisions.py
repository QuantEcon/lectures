"""Same-name collisions, the canonical map, jax by default, byte stability."""

import hashlib

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
    # The message groups the copies: which agree with the anchor, which do not.
    assert "same: intro:" in line and "different: intermediate:" in line and ", jax:" in line


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


def test_canonical_map_picks_a_copy_and_priority_picks_among_identical_holders(make_repo):
    repo = make_repo(["intro", "intermediate", "jax"])
    repo.lecture("intro", "mle", lecture_text("MLE (intro)"))
    shared = lecture_text("MLE (intermediate and jax)")
    repo.lecture("intermediate", "mle", shared)
    repo.lecture("jax", "mle", shared)
    repo.write_canonical_map({"mle": "jax"})

    res = repo.promote("mle")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("mle")
    assert entry["canonical"] == "intermediate"
    assert [s["series"] for s in entry["sources"]] == ["intermediate", "jax"]
    assert [s["series"] for s in entry["divergent"]] == ["intro"]


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
    # The map picks a copy, not a priority: identical copies still go to the
    # highest-priority series, so removing the entry changes nothing.
    entry = repo.entry("shared")
    assert entry["canonical"] == "intro"
    assert [s["series"] for s in entry["sources"]] == ["intro", "intermediate"]
    assert "interim" not in entry


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


def stale_pair(make_repo):
    """advanced and dp-test hold ``amss`` identically; advanced then edits it
    upstream and dp-test does not move — dp-test's copy is stale."""
    repo = make_repo(["advanced", "dp-test"])
    repo.lecture("advanced", "amss", lecture_text("AMSS"))
    repo.lecture("dp-test", "amss", lecture_text("AMSS"))
    assert repo.promote("amss").returncode == 0
    recorded = {s["series"]: s["digest"] for s in repo.entry("amss")["sources"]}
    repo.lecture("advanced", "amss", lecture_text("AMSS", "A typo fixed upstream."))
    repo.move_pin("advanced")
    return repo, recorded


def test_a_stale_copy_stays_a_source_and_the_refresh_goes_through(make_repo):
    repo, recorded = stale_pair(make_repo)

    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert "stale: dp-test at an earlier promoted version" in res.stdout
    entry = repo.entry("amss")
    assert entry["canonical"] == "advanced"
    assert "divergent" not in entry and "interim" not in entry
    digests = {s["series"]: s["digest"] for s in entry["sources"]}
    assert digests["dp-test"] == recorded["dp-test"]
    assert digests["advanced"] != recorded["advanced"]
    assert "A typo fixed upstream." in repo.pool("amss.md").read_text(encoding="utf-8")
    # The drift-check agrees: a stale copy is not drift.
    assert repo.drift_check().returncode == 0


def test_a_copy_edited_since_promotion_still_fails_the_refresh(make_repo):
    repo, _ = stale_pair(make_repo)
    repo.lecture("dp-test", "amss", lecture_text("AMSS", "Edited on its own."))
    before = repo.ledger_path.read_bytes()

    res = repo.promote("--refresh")

    assert res.returncode == 1
    assert "[amss] FAILED: amss.md differs across series" in res.stderr
    assert "different: dp-test:" in res.stderr
    assert repo.ledger_path.read_bytes() == before


def test_a_copy_that_caught_up_then_fell_behind_again_is_still_stale(make_repo):
    repo, _ = stale_pair(make_repo)
    assert repo.promote("--refresh").returncode == 0
    caught_up = lecture_text("AMSS", "A typo fixed upstream.")
    repo.lecture("dp-test", "amss", caught_up)
    repo.move_pin("dp-test")
    repo.lecture("advanced", "amss", lecture_text("AMSS", "A second fix upstream."))
    repo.move_pin("advanced", 3)

    dc = repo.drift_check()

    assert "[stale-copy]" in dc.stdout and "[diverged]" not in dc.stdout, dc.stdout
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    digests = {s["series"]: s["digest"] for s in repo.entry("amss")["sources"]}
    assert digests["dp-test"] == hashlib.sha256(caught_up.encode("utf-8")).hexdigest()


def test_a_second_canonical_move_keeps_an_unmoved_copy_stale(make_repo):
    # After the first refresh only the copy's OWN recorded digest still
    # matches it, so this pins that half of the rule.
    repo, recorded = stale_pair(make_repo)
    assert repo.promote("--refresh").returncode == 0
    repo.lecture("advanced", "amss", lecture_text("AMSS", "A second fix upstream."))
    repo.move_pin("advanced", 3)

    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    digests = {s["series"]: s["digest"] for s in repo.entry("amss")["sources"]}
    assert digests["dp-test"] == recorded["dp-test"]
    assert "A second fix upstream." in repo.pool("amss.md").read_text(encoding="utf-8")


def test_a_copy_never_recorded_as_a_source_is_not_stale(make_repo):
    # A series that holds an old version but was never recorded is a
    # collision, even when its copy equals the canonical's recorded version.
    repo = make_repo(["advanced", "dp-test"])
    repo.lecture("advanced", "amss", lecture_text("AMSS"))
    assert repo.promote("amss").returncode == 0
    repo.lecture("dp-test", "amss", lecture_text("AMSS"))
    repo.lecture("advanced", "amss", lecture_text("AMSS", "A fix upstream."))
    repo.move_pin("advanced")

    res = repo.promote("--refresh")

    assert res.returncode == 1
    assert "[amss] FAILED: amss.md differs across series" in res.stderr


def test_toc_of_a_lagging_series_takes_the_canonical_copy(make_repo):
    repo = make_repo(["advanced", "dp-test"])
    repo.lecture("advanced", "amss", lecture_text("AMSS"))
    repo.lecture("dp-test", "amss", lecture_text("AMSS"))
    repo.toc("dp-test", ["amss"])
    assert repo.promote("--toc", "dp-test").returncode == 0
    assert repo.entry("amss")["canonical"] == "advanced"
    repo.lecture("advanced", "amss", lecture_text("AMSS", "A fix upstream."))
    repo.move_pin("advanced")

    # Before any refresh, and again after one, --toc of the lagging series
    # takes the canonical copy and keeps its own copy as a stale source.
    for _ in range(2):
        res = repo.promote("--toc", "dp-test")
        assert res.returncode == 0, res.stderr
        assert "A fix upstream." in repo.pool("amss.md").read_text(encoding="utf-8")
        entry = repo.entry("amss")
        assert entry["canonical"] == "advanced"
        assert [s["series"] for s in entry["sources"]] == ["advanced", "dp-test"]
        assert "divergent" not in entry and "interim" not in entry
        assert repo.promote("--refresh").returncode == 0


def test_a_map_entry_naming_a_stale_copy_is_refused(make_repo):
    # The map names the lower-priority holder of two identical copies (it
    # settles nothing); when the canonical copy moves on, following the map
    # would keep the lagging text, so the entry is refused and named.
    repo = make_repo(["advanced", "dp-test"])
    repo.lecture("advanced", "amss", lecture_text("AMSS"))
    repo.lecture("dp-test", "amss", lecture_text("AMSS"))
    repo.write_canonical_map({"amss": "dp-test"})
    res = repo.promote("amss")
    assert res.returncode == 0, res.stderr
    assert "settles nothing" in res.stdout
    assert repo.entry("amss")["canonical"] == "advanced"
    before = repo.ledger_path.read_bytes()
    repo.lecture("advanced", "amss", lecture_text("AMSS", "A fix upstream."))
    repo.move_pin("advanced")

    res = repo.promote("--refresh")

    assert res.returncode == 1
    failed = [line for line in res.stderr.splitlines() if line.startswith("[amss] FAILED")]
    assert len(failed) == 1, res.stderr
    assert "names 'dp-test'" in failed[0] and "earlier promoted version" in failed[0]
    assert "remove it" in failed[0]
    assert repo.ledger_path.read_bytes() == before


def test_a_map_entry_over_spelling_only_copies_is_not_refused(make_repo):
    # Copies equal after asset-path normalisation, nothing moved: a map line
    # naming either holder settles nothing, and a refresh goes through.
    repo = make_repo(["intro", "intermediate"])
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/short_path/graph.png", b"png")
    repo.lecture("intro", "short_path", lecture_text("Short paths", refs=["/_static/lecture_specific/short_path/graph.png"]))
    repo.lecture("intermediate", "short_path", lecture_text("Short paths", refs=["_static/lecture_specific/short_path/graph.png"]))
    repo.write_canonical_map({"short_path": "intermediate"})
    assert repo.promote("short_path").returncode == 0
    repo.move_pin("intro")

    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert "settles nothing" in res.stdout
