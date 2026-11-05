"""Product pages: the per-series pages a `--toc` run leaves to the products
(tools/promote's PRODUCT_PAGES), never pool content."""

from conftest import lecture_text

PRODUCT_PAGES = ["intro", "about", "status", "troubleshooting", "zreferences"]


def test_a_toc_run_skips_every_product_page_and_the_toc_watch_agrees(make_repo):
    # intro's `about` describes the series itself: what it covers, its level, its credits.
    repo = make_repo(["intro"])
    for slug in PRODUCT_PAGES + ["solow"]:
        repo.lecture("intro", slug, lecture_text(slug.title()))
    repo.toc("intro", PRODUCT_PAGES[1:] + ["solow"])  # the toc's root is `intro`

    res = repo.promote("--toc", "intro")

    assert res.returncode == 0, res.stdout
    assert "1 promoted, 0 unchanged, 5 skipped, 0 failed" in res.stdout
    for slug in PRODUCT_PAGES:
        assert f"[{slug}] SKIP: product page" in res.stdout
        assert not repo.pool(f"{slug}.md").exists()
    assert [key for key in repo.ledger() if key != "assets"] == ["lectures/solow.md"]

    # The toc watch skips the same pages, so none of them is `toc-unpromoted`.
    assert repo.drift_check("--accept-toc", "intro").returncode == 0
    res = repo.drift_check()
    assert res.returncode == 0, res.stdout
    assert "toc-unpromoted" not in res.stdout
