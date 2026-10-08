"""``promote --refresh``: an entry this run cannot refresh is never skipped
silently once its canonical copy has moved."""

from conftest import lecture_text


def jax_only_entry(make_repo):
    """A lecture only jax holds, promoted by a default run (jax considered)."""
    repo = make_repo(["intermediate", "jax"])
    repo.lecture("jax", "jax_nn", lecture_text("Neural nets"))
    assert repo.promote("jax_nn").returncode == 0
    assert repo.entry("jax_nn")["canonical"] == "jax"
    return repo


def test_an_excluded_canonical_series_is_skipped_while_its_pin_stands(make_repo):
    repo = jax_only_entry(make_repo)
    repo.move_pin("intermediate")

    res = repo.promote("--refresh", "--exclude", "jax")

    assert res.returncode == 0, res.stderr
    assert "[jax_nn] SKIP: canonical series 'jax' is excluded" in res.stdout


def test_an_excluded_canonical_series_whose_pin_moved_fails_the_refresh(make_repo):
    repo = jax_only_entry(make_repo)
    before = repo.ledger_path.read_bytes()
    repo.lecture("jax", "jax_nn", lecture_text("Neural nets", "Fixed upstream."))
    repo.move_pin("jax")

    res = repo.promote("--refresh", "--exclude", "jax")

    assert res.returncode == 1
    failed = [line for line in res.stderr.splitlines() if line.startswith("[jax_nn] FAILED")]
    assert len(failed) == 1, res.stderr
    assert "canonical series 'jax' is excluded, but its pin moved since promotion" in failed[0]
    assert "PROMOTE_EXCLUDE" in failed[0]
    assert repo.ledger_path.read_bytes() == before
    assert "Fixed upstream." not in repo.pool("jax_nn.md").read_text(encoding="utf-8")

    # With jax considered again, the same entry refreshes.
    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert "Fixed upstream." in repo.pool("jax_nn.md").read_text(encoding="utf-8")


def test_a_consumer_canonical_entry_whose_pin_moved_fails_the_refresh(make_repo):
    # A ledger written before dp was declared a consumer can name dp canonical.
    repo = make_repo(["intermediate", "dp"])
    repo.lecture("dp", "dp_only", lecture_text("Only in dp"))
    assert repo.promote("dp_only").returncode == 0
    repo.write_manifest(consumers=["dp"])

    res = repo.promote("--refresh")
    assert res.returncode == 0, res.stderr
    assert "[dp_only] SKIP: canonical series 'dp' is a consumer" in res.stdout

    repo.move_pin("dp")
    res = repo.promote("--refresh")
    assert res.returncode == 1
    assert "[dp_only] FAILED: canonical series 'dp' is a consumer, but its pin moved" in res.stderr


def test_a_canonical_series_that_left_the_manifest_is_named_as_such(make_repo):
    repo = make_repo(["intro", "extra"])
    repo.lecture("extra", "only_extra", lecture_text("Only in extra"))
    assert repo.promote("only_extra").returncode == 0
    # The series leaves the manifest; the next sync drops its pin.
    repo.order = ["intro"]
    repo.write_manifest()
    repo.write_state({"intro": repo.pin("intro")})

    res = repo.promote("--refresh")

    assert res.returncode == 1
    failed = [line for line in res.stderr.splitlines() if line.startswith("[only_extra] FAILED")]
    assert len(failed) == 1, res.stderr
    assert "canonical series 'extra' is not in sync/manifest.yml" in failed[0]
    assert "-> none)" in failed[0] and "excluded" not in failed[0]


def test_a_canonical_copy_gone_upstream_is_named_as_such(make_repo):
    repo = make_repo(["advanced", "dp-test"])
    for series in ("advanced", "dp-test"):
        repo.lecture(series, "amss", lecture_text("AMSS"))
    assert repo.promote("amss").returncode == 0
    (repo.root / "mirror" / "advanced" / "lectures" / "amss.md").unlink()
    repo.move_pin("advanced")

    res = repo.promote("--refresh")

    assert res.returncode == 1
    assert "[amss] FAILED: the canonical copy of amss.md is gone from advanced upstream" in res.stderr
    assert "canonical-removed" in res.stderr
