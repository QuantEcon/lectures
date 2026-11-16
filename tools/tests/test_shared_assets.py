"""A pool asset that lectures share (QuantEcon/lectures#23).

The pool keeps one file. Lectures that share it stay on one pool path, an
asset's record follows the series its lectures come from, a copy that
differs is recorded and reported, and two lectures that bring different
bytes to one path are both refused."""

from conftest import lecture_text

CRRA = "_static/lecture_specific/amss2/crra_utility.py"
SHARED_CRRA = "_static/_shared/amss2/crra_utility.py"


def loads(title, path, body=""):
    """A lecture whose code cell :load:s a file."""
    return lecture_text(title, body + "\n\n```{code-cell} python3\n:load: " + path + "\n```")


def assets(repo):
    return repo.ledger()["assets"]


def sources(repo, dest):
    return {s["series"]: s for s in assets(repo)[dest]["sources"]}


# --------------------------------------------------------------------------- #
# Gap 1: a shared file never splits across two pool paths                      #
# --------------------------------------------------------------------------- #
def test_a_partial_refresh_keeps_a_shared_file_on_one_path(make_repo):
    repo = make_repo(["advanced", "extra"])
    for s in ("advanced", "extra"):
        repo.mirror_file(s, CRRA, "v1\n")
        repo.lecture(s, "amss2", loads("AMSS2", CRRA))
        repo.lecture(s, "amss3", loads("AMSS3", CRRA))
    assert repo.promote("amss2", "amss3").returncode == 0
    assert repo.entry("amss2")["assets"] == repo.entry("amss3")["assets"] == [SHARED_CRRA]

    repo.mirror_file("advanced", CRRA, "v2\n")
    repo.lecture("advanced", "amss2", loads("AMSS2", CRRA, "advanced edit"))
    repo.lecture("advanced", "amss3", loads("AMSS3", CRRA, "advanced edit"))
    repo.move_pin("advanced")
    repo.lecture("extra", "amss3", loads("AMSS3", CRRA, "another edit"))  # amss3 will be refused
    repo.move_pin("extra")

    res = repo.promote("--refresh")

    # amss2 refreshes, amss3 is refused, and the file stays where both use it.
    assert res.returncode == 1
    assert "[amss3] FAILED: amss3.md differs across series" in res.stderr
    assert repo.entry("amss2")["assets"] == repo.entry("amss3")["assets"] == [SHARED_CRRA]
    assert repo.pool(SHARED_CRRA).read_text(encoding="utf-8") == "v2\n"
    assert not repo.pool("_static/amss2/crra_utility.py").exists()

    # Settled as its FAILED line says, amss3 refreshes the next night.
    repo.write_canonical_map({"amss3": "advanced"})
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert "advanced edit" in repo.pool("amss3.md").read_text(encoding="utf-8")
    assert repo.entry("amss3")["assets"] == [SHARED_CRRA]


def test_a_file_shared_across_series_follows_the_series_that_changes_it(make_repo):
    # The duopoly_mpe.py shape: two lectures, canonical in different series.
    DUO = "_static/lecture_specific/markov_perf/duopoly_mpe.py"
    DEST = "_static/_shared/markov_perf/duopoly_mpe.py"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, DUO, "v1\n")
    repo.lecture("intermediate", "markov_perf", loads("MPE", DUO))
    repo.lecture("advanced", "rob_markov_perf", loads("Robust MPE", DUO))
    assert repo.promote("markov_perf", "rob_markov_perf").returncode == 0
    assert assets(repo)[DEST]["canonical"] == "intermediate"

    repo.mirror_file("intermediate", DUO, "v2\n")
    repo.move_pin("intermediate")
    assert "[asset-moved]" in repo.drift_check().stdout
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert repo.pool(DEST).read_text(encoding="utf-8") == "v2\n"
    assert not repo.pool("_static/markov_perf/duopoly_mpe.py").exists()
    assert repo.entry("markov_perf")["assets"] == repo.entry("rob_markov_perf")["assets"] == [DEST]
    got = sources(repo, DEST)
    assert "digest" not in got["intermediate"] and got["advanced"]["stale_since"]
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    assert "the advanced copy" in dc.stdout and "is not at the pool's version" in dc.stdout
    assert "nothing to refresh" in repo.promote("--refresh").stdout

    # advanced follows: its copy is current again.
    repo.mirror_file("advanced", DUO, "v2\n")
    repo.move_pin("advanced")
    assert repo.promote("--refresh").returncode == 0
    assert all("digest" not in s for s in sources(repo, DEST).values())
    assert repo.drift_check().returncode == 0


def test_the_lagging_series_leading_instead_is_taken_the_same_way(make_repo):
    DUO = "_static/lecture_specific/markov_perf/duopoly_mpe.py"
    DEST = "_static/_shared/markov_perf/duopoly_mpe.py"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, DUO, "v1\n")
    repo.lecture("intermediate", "markov_perf", loads("MPE", DUO))
    repo.lecture("advanced", "rob_markov_perf", loads("Robust MPE", DUO))
    assert repo.promote("markov_perf", "rob_markov_perf").returncode == 0

    repo.mirror_file("advanced", DUO, "v2\n")
    repo.move_pin("advanced")
    dc = repo.drift_check()
    assert "[asset-moved]" in dc.stdout and "DRIFT" not in dc.stdout
    assert repo.promote("--refresh").returncode == 0

    assert repo.pool(DEST).read_text(encoding="utf-8") == "v2\n"
    assert assets(repo)[DEST]["canonical"] == "advanced"
    assert sources(repo, DEST)["intermediate"]["stale_since"]
    assert repo.drift_check().returncode == 0


# --------------------------------------------------------------------------- #
# Lectures that share a file move together                                     #
# --------------------------------------------------------------------------- #
def test_a_second_user_pulls_the_first_into_the_batch(make_repo):
    # The arellano shape: a lecture's own figure gains a second user.
    FIG = "_static/lecture_specific/arellano/fig.png"
    repo = make_repo(["advanced", "jax"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("advanced", "arellano", lecture_text("Arellano", refs=[FIG]))
    assert repo.promote("arellano").returncode == 0
    assert repo.entry("arellano")["assets"] == ["_static/arellano/fig.png"]

    repo.lecture("jax", "arellano_jax", lecture_text("Arellano with JAX", refs=[FIG]))
    res = repo.promote("arellano_jax")

    assert res.returncode == 0, res.stderr
    shared = "_static/_shared/arellano/fig.png"
    assert repo.entry("arellano")["assets"] == repo.entry("arellano_jax")["assets"] == [shared]
    assert shared in repo.pool("arellano.md").read_text(encoding="utf-8")
    assert repo.pool(shared).is_file() and not repo.pool("_static/arellano").exists()
    assert set(sources(repo, shared)) == {"advanced", "jax"}
    assert repo.drift_check().returncode == 0
    assert repo.pool_check().returncode == 0


def test_a_user_that_cannot_be_pulled_in_holds_the_mover_back(make_repo):
    FIG = "_static/lecture_specific/arellano/fig.png"
    repo = make_repo(["advanced", "jax"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("advanced", "arellano", lecture_text("Arellano", refs=[FIG]))
    assert repo.promote("arellano").returncode == 0
    before = repo.ledger_path.read_bytes()
    (repo.root / "mirror" / "advanced" / "lectures" / "arellano.md").unlink()
    repo.lecture("jax", "arellano_jax", lecture_text("Arellano with JAX", refs=[FIG]))

    res = repo.promote("arellano_jax")

    assert res.returncode == 1
    assert "[arellano_jax] FAILED" in res.stderr
    assert "moves with its other consumer(s) (arellano), and arellano could not be re-promoted" in res.stderr
    assert repo.ledger_path.read_bytes() == before
    assert not repo.pool("arellano_jax.md").exists()


def test_a_lecture_that_stops_using_a_shared_file_takes_its_other_user_along(make_repo):
    FIG = "_static/fig.png"
    repo = make_repo(["intro", "intermediate"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("intro", "aaa", lecture_text("A", refs=[FIG]))
    repo.lecture("intermediate", "bbb", lecture_text("B", refs=[FIG]))
    assert repo.promote("aaa", "bbb").returncode == 0
    assert repo.entry("bbb")["assets"] == ["_static/_shared/fig.png"]

    repo.lecture("intro", "aaa", lecture_text("A"))
    repo.move_pin("intro")
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert "[bbb] PULLED IN: it shares _static/_shared/fig.png with aaa" in res.stdout
    assert "PULLED IN: bbb" in res.stdout
    assert repo.entry("bbb")["assets"] == ["_static/bbb/fig.png"]
    record = assets(repo)["_static/bbb/fig.png"]
    assert record["canonical"] == "intermediate" and [s["series"] for s in record["sources"]] == ["intermediate"]
    assert not repo.pool("_static/_shared").exists()
    # intro's file is no longer the pool's business.
    repo.mirror_file("intro", FIG, b"changed")
    repo.move_pin("intro", 3)
    assert repo.drift_check().returncode == 0
    assert repo.pool_check().returncode == 0


def test_two_files_that_become_one_are_merged_with_both_users(make_repo):
    FIG = "_static/fig.png"
    repo = make_repo(["intro", "intermediate"])
    repo.mirror_file("intro", FIG, b"intro's")
    repo.mirror_file("intermediate", FIG, b"intermediate's")
    repo.lecture("intro", "aaa", lecture_text("A", refs=[FIG]))
    repo.lecture("intermediate", "bbb", lecture_text("B", refs=[FIG]))
    assert repo.promote("aaa").returncode == 0
    assert repo.promote("bbb").returncode == 0
    assert repo.entry("aaa")["assets"] == ["_static/aaa/fig.png"]
    assert repo.entry("bbb")["assets"] == ["_static/bbb/fig.png"]

    repo.mirror_file("intermediate", FIG, b"intro's")
    repo.move_pin("intermediate")
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert repo.entry("aaa")["assets"] == repo.entry("bbb")["assets"] == ["_static/_shared/fig.png"]
    assert not repo.pool("_static/aaa").exists() and not repo.pool("_static/bbb").exists()
    assert repo.drift_check().returncode == 0 and repo.pool_check().returncode == 0


def test_a_hand_edited_file_is_not_lost_when_its_asset_moves(make_repo):
    FIG = "_static/lecture_specific/arellano/fig.png"
    repo = make_repo(["advanced", "jax"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("advanced", "arellano", lecture_text("Arellano", refs=[FIG]))
    assert repo.promote("arellano").returncode == 0
    repo.pool("_static/arellano/fig.png").write_bytes(b"edited in the pool")
    repo.lecture("jax", "arellano_jax", lecture_text("Arellano with JAX", refs=[FIG]))

    res = repo.promote("arellano_jax")

    assert res.returncode == 1
    assert "the pool file at _static/arellano/fig.png differs from its recorded digest" in res.stderr
    assert repo.pool("_static/arellano/fig.png").read_bytes() == b"edited in the pool"
    assert not repo.pool("arellano_jax.md").exists()


def test_a_pulled_lecture_is_not_written_when_the_lecture_that_needed_it_fails(make_repo):
    FIG = "_static/lecture_specific/arellano/fig.png"
    repo = make_repo(["advanced", "jax"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("advanced", "arellano", lecture_text("Arellano", refs=[FIG]))
    assert repo.promote("arellano").returncode == 0
    repo.lecture("advanced", "arellano", lecture_text("Arellano", "Edited upstream.", refs=[FIG]))
    repo.move_pin("advanced")
    repo.lecture("jax", "arellano_jax", lecture_text("Arellano with JAX", refs=[FIG]))
    repo.pool("arellano_jax.md").write_text("an unrecorded pool file\n", encoding="utf-8")
    before = repo.ledger_path.read_bytes()

    res = repo.promote("arellano_jax")

    assert res.returncode == 1
    assert "[arellano_jax] FAILED" in res.stderr and "PULLED IN" not in res.stdout
    assert repo.ledger_path.read_bytes() == before
    assert "Edited upstream." not in repo.pool("arellano.md").read_text(encoding="utf-8")


def test_a_new_lecture_whose_other_series_copy_differs_holds_nobody_back(make_repo):
    G = "_static/g.png"
    repo = make_repo(["intro", "intermediate", "extra"])
    repo.mirror_file("intermediate", G, b"g")
    repo.lecture("intermediate", "bbb", lecture_text("B", refs=[G]))
    repo.lecture("intermediate", "ddd", lecture_text("D", refs=[G]))
    assert repo.promote("bbb", "ddd").returncode == 0
    # eee is one lecture in intro and extra; extra's g.png is another file.
    repo.mirror_file("intro", G, b"g")
    repo.mirror_file("extra", G, b"another g")
    for s in ("intro", "extra"):
        repo.lecture(s, "eee", lecture_text("E", refs=[G]))

    res = repo.promote("bbb", "eee")

    assert res.returncode == 0, res.stderr
    got = sources(repo, "_static/_shared/g.png")
    assert set(got) == {"intro", "intermediate", "extra"}
    assert got["extra"]["differs"] is True and "digest" not in got["intro"]


# --------------------------------------------------------------------------- #
# Gap 2: an asset's record follows the lectures that use it                    #
# --------------------------------------------------------------------------- #
def test_an_assets_sources_are_the_series_its_lectures_come_from(make_repo):
    FIG = "_static/lecture_specific/lq/fig.png"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig v1")
    # advanced holds a file of that name, and no lecture that uses it.
    repo.lecture("advanced", "lq", lecture_text("LQ", refs=[FIG]))
    assert repo.promote("lq").returncode == 0

    record = assets(repo)["_static/lq/fig.png"]
    assert record["canonical"] == "advanced"
    assert [s["series"] for s in record["sources"]] == ["advanced"]

    repo.mirror_file("intermediate", FIG, b"fig v2")
    repo.move_pin("intermediate")
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    assert "nothing to refresh" in repo.promote("--refresh").stdout


def test_a_record_from_before_sources_followed_users_is_not_watched(make_repo):
    FIG = "_static/lecture_specific/lq/fig.png"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig v1")
    repo.lecture("advanced", "lq", lecture_text("LQ", refs=[FIG]))
    assert repo.promote("lq").returncode == 0
    # As an older promote wrote it: every series with those bytes is a source.
    text = repo.ledger_path.read_text(encoding="utf-8")
    old = "    sources:\n    - series: advanced\n      path: " + FIG + "\n"
    assert old in text
    repo.ledger_path.write_text(
        text.replace(old, "    sources:\n    - series: intermediate\n      path: " + FIG + "\n" + old[len("    sources:\n"):]),
        encoding="utf-8",
    )
    assert set(sources(repo, "_static/lq/fig.png")) == {"intermediate", "advanced"}

    repo.mirror_file("intermediate", FIG, b"fig v2")
    repo.move_pin("intermediate")

    assert repo.drift_check().returncode == 0
    assert "nothing to refresh" in repo.promote("--refresh").stdout


# --------------------------------------------------------------------------- #
# Gap 3: a destination collision refuses every lecture involved                #
# --------------------------------------------------------------------------- #
def test_a_destination_collision_is_not_settled_by_run_order(make_repo):
    FAM, DEST = "_static/lecture_specific/fam/x.png", "_static/_shared/fam/x.png"
    for order in (("aaa", "bbb"), ("bbb", "aaa")):
        repo = make_repo(["intro", "intermediate"])
        repo.mirror_file("intro", FAM, b"intro bytes")
        repo.lecture("intro", "aaa", lecture_text("Intro lecture", refs=[FAM]))
        repo.mirror_file("intermediate", FAM, b"intermediate bytes")
        repo.lecture("intermediate", "bbb", lecture_text("Intermediate lecture", refs=[FAM]))

        res = repo.promote(*order)

        assert res.returncode == 1
        for slug in ("aaa", "bbb"):
            line = next(x for x in res.stderr.splitlines() if x.startswith(f"[{slug}] FAILED"))
            assert f"asset destination collision at {DEST}" in line
            assert "intro:" in line and "intermediate:" in line and "(used by aaa)" in line and "(used by bbb)" in line
        assert not repo.ledger_path.exists() and not repo.pool(DEST).exists()


# --------------------------------------------------------------------------- #
# Gap 4: a copy that differs is recorded, never dropped                        #
# --------------------------------------------------------------------------- #
def test_an_edited_copy_stays_recorded_through_a_refresh(make_repo):
    FIG, DEST = "_static/lecture_specific/career/fig.png", "_static/career/fig.png"
    repo = make_repo(["intermediate", "extra"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig v1")
        repo.lecture(s, "career", lecture_text("Career", refs=[FIG]))
    repo.lecture("intermediate", "other", lecture_text("Other"))
    assert repo.promote("career", "other").returncode == 0
    assert set(sources(repo, DEST)) == {"intermediate", "extra"}

    # extra, which held the pool's version, changes the figure: it leads.
    repo.mirror_file("extra", FIG, b"fig edited in extra")
    repo.move_pin("extra")
    assert "[asset-moved]" in repo.drift_check().stdout
    repo.lecture("intermediate", "other", lecture_text("Other", "an unrelated fix"))
    repo.move_pin("intermediate")
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert repo.pool(DEST).read_bytes() == b"fig edited in extra"
    got = sources(repo, DEST)
    assert set(got) == {"intermediate", "extra"}  # neither is dropped
    assert got["intermediate"]["stale_since"] and "digest" not in got["extra"]
    assert "the intermediate copy" in repo.drift_check().stdout


def test_a_copy_that_differs_at_the_first_promotion_is_a_different_file(make_repo):
    FIG, DEST = "_static/figs/a.png", "_static/career/figs/a.png"
    repo = make_repo(["intermediate", "extra"])
    repo.mirror_file("intermediate", FIG, b"one")
    repo.mirror_file("extra", FIG, b"two")
    for s in repo.order:
        repo.lecture(s, "career", lecture_text("Career", refs=[FIG]))

    assert repo.promote("career").returncode == 0

    got = sources(repo, DEST)
    assert "digest" not in got["intermediate"]
    assert got["extra"]["digest"] and got["extra"]["differs"] is True and "stale_since" not in got["extra"]
    dc = repo.drift_check()
    assert dc.returncode == 0, dc.stdout
    assert "[differing-copy]" in dc.stdout and "the extra copy lectures/" + FIG + " is a different file from the pool's" in dc.stdout

    # A lecture only extra holds, using that name, gets extra's own file.
    repo.lecture("extra", "other", lecture_text("Other", refs=[FIG]))
    assert repo.promote("other").returncode == 0
    assert repo.entry("other")["assets"] == ["_static/other/figs/a.png"]
    assert repo.pool("_static/other/figs/a.png").read_bytes() == b"two"
    assert repo.pool(DEST).read_bytes() == b"one"
    # Promoted again, nothing moves.
    before = repo.ledger_path.read_bytes()
    assert repo.promote("other", "career").returncode == 0
    assert repo.ledger_path.read_bytes() == before


def test_a_differing_copy_is_judged_the_same_whenever_it_appears(make_repo):
    FIG, DEST = "_static/figs/a.png", "_static/career/figs/a.png"
    repo = make_repo(["intermediate", "extra"])
    repo.mirror_file("intermediate", FIG, b"one")
    repo.lecture("intermediate", "career", lecture_text("Career", refs=[FIG]))
    assert repo.promote("career").returncode == 0

    # extra gains the same lecture later, with another file under the name.
    repo.mirror_file("extra", FIG, b"two")
    repo.lecture("extra", "career", lecture_text("Career", refs=[FIG]))
    repo.move_pin("extra")
    res = repo.promote("career")

    assert res.returncode == 0, res.stderr
    assert sources(repo, DEST)["extra"]["differs"] is True
    assert repo.pool(DEST).read_bytes() == b"one"

    # When extra's file becomes the pool's, the refresh records it plain.
    repo.mirror_file("extra", FIG, b"one")
    repo.move_pin("extra", 3)
    assert "[asset-caught-up]" in repo.drift_check().stdout
    assert repo.promote("--refresh").returncode == 0
    assert all("digest" not in s for s in sources(repo, DEST).values())
    assert repo.drift_check().returncode == 0


def test_a_copy_that_catches_up_is_recorded_and_may_lead_next(make_repo):
    DUO = "_static/lecture_specific/markov_perf/duopoly_mpe.py"
    DEST = "_static/_shared/markov_perf/duopoly_mpe.py"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, DUO, "v1\n")
    repo.lecture("intermediate", "markov_perf", loads("MPE", DUO))
    repo.lecture("advanced", "rob_markov_perf", loads("Robust MPE", DUO))
    assert repo.promote("markov_perf", "rob_markov_perf").returncode == 0
    repo.mirror_file("intermediate", DUO, "v2\n")
    repo.move_pin("intermediate")
    assert repo.promote("--refresh").returncode == 0
    assert sources(repo, DEST)["advanced"]["stale_since"]

    # advanced makes the same edit: only the file changes, no lecture.
    repo.mirror_file("advanced", DUO, "v2\n")
    repo.move_pin("advanced")
    dc = repo.drift_check()
    assert dc.returncode == 1 and "[asset-caught-up]" in dc.stdout and "DRIFT" not in dc.stdout
    assert repo.promote("--refresh").returncode == 0
    assert all("digest" not in s for s in sources(repo, DEST).values())
    assert repo.drift_check().returncode == 0

    # Having held the pool's version, advanced may lead.
    repo.mirror_file("advanced", DUO, "v3\n")
    repo.move_pin("advanced", 3)
    assert "[asset-moved]" in repo.drift_check().stdout
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert repo.pool(DEST).read_text(encoding="utf-8") == "v3\n"
    assert assets(repo)[DEST]["canonical"] == "advanced"


def test_a_series_whose_lecture_copy_has_diverged_does_not_lead_with_its_file(make_repo):
    # pandas_panel is one lecture in two series. The non-canonical series
    # edits its lecture AND its figure: the lecture is drift, for a person to
    # settle, and its figure is not followed meanwhile.
    FIG, DEST = "_static/lecture_specific/pandas_panel/venn.png", "_static/pandas_panel/venn.png"
    repo = make_repo(["programming", "intermediate"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"venn")
        repo.lecture(s, "pandas_panel", lecture_text("Panel", refs=[FIG]))
    assert repo.promote("pandas_panel").returncode == 0
    before = repo.ledger_path.read_bytes()

    repo.lecture("intermediate", "pandas_panel", lecture_text("Panel", "An edit of its own.", refs=[FIG]))
    repo.mirror_file("intermediate", FIG, b"venn, edited")
    repo.move_pin("intermediate")

    for night in (1, 2):
        dc = repo.drift_check()
        assert "[diverged]" in dc.stdout
        assert "REFRESH" not in dc.stdout, dc.stdout
        assert "nothing to refresh" in repo.promote("--refresh").stdout
    assert repo.ledger_path.read_bytes() == before
    assert repo.pool(DEST).read_bytes() == b"venn"


def test_a_record_whose_canonical_series_is_no_longer_a_user_is_rewritten(make_repo):
    FIG, DEST = "_static/lecture_specific/lq/fig.png", "_static/lq/fig.png"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig v1")
    repo.lecture("advanced", "lq", lecture_text("LQ", refs=[FIG]))
    assert repo.promote("lq").returncode == 0
    # As an older promote could leave it: canonical in a series with no user.
    text = repo.ledger_path.read_text(encoding="utf-8")
    old = "    canonical: advanced\n    digest"
    assert text.count(old) == 1
    text = text.replace(old, "    canonical: intermediate\n    digest")
    src = "    sources:\n    - series: advanced\n      path: " + FIG + "\n"
    assert text.count(src) == 1
    repo.ledger_path.write_text(
        text.replace(src, "    sources:\n    - series: intermediate\n      path: " + FIG + "\n" + src[len("    sources:\n"):]),
        encoding="utf-8",
    )

    dc = repo.drift_check()
    assert dc.returncode == 1 and "[asset-record]" in dc.stdout
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    record = assets(repo)[DEST]
    assert record["canonical"] == "advanced" and [s["series"] for s in record["sources"]] == ["advanced"]
    assert repo.drift_check().returncode == 0
    assert "nothing to refresh" in repo.promote("--refresh").stdout


def test_re_promoting_a_lecture_restores_its_own_hand_edited_file(make_repo):
    FIG, DEST = "_static/lecture_specific/lq/fig.png", "_static/lq/fig.png"
    repo = make_repo(["advanced"])
    repo.mirror_file("advanced", FIG, b"fig")
    repo.lecture("advanced", "lq", lecture_text("LQ", refs=[FIG]))
    assert repo.promote("lq").returncode == 0
    repo.pool(DEST).write_bytes(b"edited in the pool")
    assert "[asset-edited]" in repo.drift_check().stdout

    assert repo.promote("lq").returncode == 0

    assert repo.pool(DEST).read_bytes() == b"fig"
    assert repo.drift_check().returncode == 0


# --------------------------------------------------------------------------- #
# Left as it is: two spellings of one file                                     #
# --------------------------------------------------------------------------- #
def test_two_spellings_of_one_file_are_one_asset(make_repo):
    # long_run_growth writes one figure two ways; both rewrite to one pool path.
    FIG = "_static/lecture_specific/long_run_growth/tooze.png"
    repo = make_repo(["intro"])
    repo.mirror_file("intro", FIG, b"fig")
    repo.lecture("intro", "long_run_growth", lecture_text("Growth", refs=[FIG, "/" + FIG]))

    res = repo.promote("long_run_growth")

    assert res.returncode == 0, res.stderr
    entry = repo.entry("long_run_growth")
    assert entry["assets"] == ["_static/long_run_growth/tooze.png"]
    assert sorted(r["from"] for r in entry["rewrites"]) == ["/" + FIG, FIG]
    assert {r["to"] for r in entry["rewrites"]} == {"_static/long_run_growth/tooze.png"}
    assert repo.drift_check().returncode == 0
    assert repo.pool_check().returncode == 0


# --------------------------------------------------------------------------- #
# The record keeps its history when the asset moves, is renamed or is left out #
# --------------------------------------------------------------------------- #
def test_a_stale_record_survives_the_assets_move(make_repo):
    FIG = "_static/lecture_specific/lq/fig.png"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"v1")
        repo.lecture(s, "lq", lecture_text("LQ", refs=[FIG]))
    assert repo.promote("lq").returncode == 0
    repo.mirror_file("intermediate", FIG, b"v2")
    repo.move_pin("intermediate")
    assert repo.promote("--refresh").returncode == 0
    since = sources(repo, "_static/lq/fig.png")["advanced"]["stale_since"]

    # A second lecture starts to use the figure: it moves to _shared/.
    repo.lecture("intermediate", "lq2", lecture_text("LQ 2", refs=[FIG]))
    res = repo.promote("lq2")

    assert res.returncode == 0, res.stderr
    got = sources(repo, "_static/_shared/lq/fig.png")
    assert got["advanced"]["stale_since"] == since and "differs" not in got["advanced"]
    assert "STALE: advanced" in res.stdout

    # advanced forks: drift, as before the move.
    repo.mirror_file("advanced", FIG, b"a fork")
    repo.move_pin("advanced")
    assert "[asset-diverged]" in repo.drift_check().stdout


def test_a_hand_edited_shared_file_is_never_restored_silently(make_repo):
    FIG = "_static/fig.png"
    repo = make_repo(["intro", "intermediate"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("intro", "aaa", lecture_text("A", refs=[FIG]))
    repo.lecture("intermediate", "bbb", lecture_text("B", refs=[FIG]))
    assert repo.promote("aaa", "bbb").returncode == 0
    repo.pool("_static/_shared/fig.png").write_bytes(b"edited in the pool")

    res = repo.promote("aaa", "bbb")  # every user in the batch, no version change

    assert res.returncode == 1
    assert "differs from its recorded digest" in res.stderr
    assert repo.pool("_static/_shared/fig.png").read_bytes() == b"edited in the pool"


def test_a_series_left_out_that_only_holds_a_copy_keeps_its_record(make_repo):
    FIG, DEST = "_static/lecture_specific/numba/fig.png", "_static/numba/fig.png"
    repo = make_repo(["programming", "intermediate"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"v1")
        repo.lecture(s, "numba", lecture_text("Numba", refs=[FIG]))
    assert repo.promote("numba").returncode == 0
    repo.mirror_file("programming", FIG, b"v2")
    repo.move_pin("programming")

    res = repo.promote("--refresh", "--exclude", "intermediate")

    assert res.returncode == 0, res.stderr
    got = sources(repo, DEST)
    assert got["intermediate"]["stale_since"] and "differs" not in got["intermediate"]


def test_a_file_renamed_upstream_is_still_the_one_shared_file(make_repo):
    OLD = "_static/lecture_specific/markov_perf/sub/duopoly_mpe.py"
    NEW = "_static/markov_perf/sub/duopoly_mpe.py"
    DEST = "_static/_shared/markov_perf/sub/duopoly_mpe.py"
    repo = make_repo(["intermediate", "advanced"])
    for s in repo.order:
        repo.mirror_file(s, OLD, "v1\n")
    repo.lecture("intermediate", "markov_perf", loads("MPE", OLD))
    repo.lecture("advanced", "rob_markov_perf", loads("Robust MPE", OLD))
    assert repo.promote("markov_perf", "rob_markov_perf").returncode == 0

    (repo.root / "mirror" / "intermediate" / "lectures" / OLD).unlink()
    repo.mirror_file("intermediate", NEW, "v1\n")
    repo.lecture("intermediate", "markov_perf", loads("MPE", NEW))
    repo.move_pin("intermediate")
    assert repo.promote("--refresh").returncode == 0

    assert repo.entry("markov_perf")["assets"] == repo.entry("rob_markov_perf")["assets"] == [DEST]
    assert sources(repo, DEST)["intermediate"]["path"] == NEW
    assert repo.drift_check().returncode == 0 and repo.pool_check().returncode == 0

    # Its next version reaches both lectures.
    repo.mirror_file("intermediate", NEW, "v2\n")
    repo.move_pin("intermediate", 3)
    assert "[asset-moved]" in repo.drift_check().stdout
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert repo.entry("markov_perf")["assets"] == repo.entry("rob_markov_perf")["assets"] == [DEST]
    assert repo.pool(DEST).read_text(encoding="utf-8") == "v2\n"
    assert sources(repo, DEST)["advanced"]["stale_since"]
    assert repo.drift_check().returncode == 0 and repo.pool_check().returncode == 0


def test_an_optional_pull_in_that_cannot_be_re_promoted_does_not_fail_the_run(make_repo):
    FIG = "_static/fig.png"
    repo = make_repo(["intro", "intermediate", "extra"])
    for s in repo.order:
        repo.mirror_file(s, FIG, b"fig")
    repo.lecture("intro", "aaa", lecture_text("A", refs=[FIG]))
    for s in ("intermediate", "extra"):
        repo.lecture(s, "bbb", lecture_text("B", refs=[FIG]))
    assert repo.promote("aaa", "bbb").returncode == 0

    # aaa stops using the figure; bbb cannot be re-promoted (extra edited its copy).
    repo.lecture("intro", "aaa", lecture_text("A"))
    repo.move_pin("intro")
    repo.lecture("extra", "bbb", lecture_text("B", "extra's own edit", refs=[FIG]))
    repo.move_pin("extra")
    res = repo.promote("--refresh")

    assert res.returncode == 0, res.stderr
    assert "[bbb] WARN: not re-promoted with the lecture that stopped using a file they shared" in res.stdout
    assert "FAILED" not in res.stderr
    assert repo.entry("aaa")["assets"] == []
    assert repo.entry("bbb")["assets"] == ["_static/_shared/fig.png"] and repo.pool("_static/_shared/fig.png").is_file()
    assert repo.pool_check().returncode == 0
