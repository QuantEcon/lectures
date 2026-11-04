"""tools/pool-check: the pool's layout conventions (QuantEcon/project-monorepo#11)."""

import pytest

from conftest import lecture_text


def write(repo, rel, data):
    path = repo.pool(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    return path


def tags(res):
    return [line.strip()[1:].split("]", 1)[0] for line in res.stdout.splitlines() if line.startswith("  [")]


def test_a_promoted_pool_keeps_the_conventions(make_repo):
    # Upstream spellings (root-relative, lecture_specific/) are promote's to
    # rewrite; links to lectures and to other sites are not asset references.
    repo = make_repo(["intro", "intermediate"])
    shared = b"a figure both lectures use"
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/common/fig.png", shared)
    repo.mirror_file("intermediate", "_static/lecture_specific/mccall/fig.png", b"mccall's own figure")
    links = "See [Lake](lake.md), [a page elsewhere](https://example.org/_static/x.png) and [above](#top)."
    repo.lecture("intro", "lake", lecture_text("Lake", refs=["/_static/lecture_specific/common/fig.png"]))
    repo.lecture("intermediate", "mccall", lecture_text(
        "McCall", body=links,
        refs=["_static/lecture_specific/mccall/fig.png", "_static/lecture_specific/common/fig.png"],
    ))
    assert repo.promote("lake", "mccall").returncode == 0
    write(repo, "_static/quant-econ.bib", "")

    res = repo.pool_check()

    assert res.returncode == 0, res.stdout
    assert "pool-check — 2 lectures, 3 files under _static/" in res.stdout
    assert "clean:" in res.stdout


def test_the_pool_is_flat(make_repo):
    repo = make_repo(["intro"])
    write(repo, "kalman.md", lecture_text("Kalman"))
    write(repo, "drafts/kalman_v2.md", lecture_text("Kalman, again"))
    write(repo, "kalman.ipynb", "{}")

    res = repo.pool_check()

    assert res.returncode == 1
    assert "[top-level] lectures/drafts/ is neither a lecture (<slug>.md) nor _static/" in res.stdout
    assert "[top-level] lectures/kalman.ipynb is neither a lecture" in res.stdout
    assert tags(res) == ["top-level", "top-level"]


def test_a_lecture_name_may_not_start_with_an_underscore(make_repo):
    repo = make_repo(["intro"])
    write(repo, "_shared.md", lecture_text("Not a lecture's name"))

    res = repo.pool_check()

    assert res.returncode == 1
    assert "[underscore] lectures/_shared.md: a lecture's name may not start with `_`" in res.stdout
    assert tags(res) == ["underscore"]


def test_names_that_differ_only_in_case_are_refused(make_repo, tmp_path):
    (tmp_path / "Probe").write_text("")
    if (tmp_path / "probe").exists():
        pytest.skip("this file system cannot hold two names that differ only in case")
    repo = make_repo(["intro"])
    write(repo, "kalman.md", lecture_text("Kalman"))
    write(repo, "Kalman.md", lecture_text("Kalman"))

    res = repo.pool_check()

    assert res.returncode == 1
    assert "[case] lectures/Kalman.md and lectures/kalman.md differ only in case" in res.stdout
    assert tags(res) == ["case"]


def test_each_static_folder_belongs_to_a_lecture(make_repo):
    repo = make_repo(["intro"])
    write(repo, "kalman.md", lecture_text("Kalman", refs=["_static/kalman/fig.png"]))
    write(repo, "_static/kalman/fig.png", b"kalman's figure")
    write(repo, "_static/_shared/common.png", b"shared")
    write(repo, "_static/quant-econ.bib", "")
    write(repo, "_static/lecture_specific/kalman/fig.png", b"the upstream layout")
    write(repo, "_static/fig.png", b"a loose file")

    res = repo.pool_check()

    assert res.returncode == 1
    assert "[static-entry] lectures/_static/fig.png is a loose file" in res.stdout
    assert "[static-entry] lectures/_static/lecture_specific/ is no lecture's folder" in res.stdout
    assert tags(res) == ["static-entry", "static-entry"]


def test_an_asset_is_used_only_by_the_lecture_whose_folder_holds_it(make_repo):
    repo = make_repo(["intro"])
    write(repo, "kalman.md", lecture_text("Kalman", refs=["_static/kalman/fig.png"]))
    write(repo, "_static/kalman/fig.png", b"kalman's figure")
    write(repo, "_static/kalman/data.csv", "1,2\n")
    write(repo, "_static/_shared/common.png", b"shared")
    # A quoted path in code counts once it names a real file.
    code = (
        "```{code-cell} python\n"
        "data = open('_static/kalman/data.csv').read()\n"
        "other = '_static/kalman/no_such_file.csv'\n"
        "```"
    )
    write(repo, "lqcontrol.md", lecture_text("LQ", body=code, refs=["_static/kalman/fig.png", "_static/_shared/common.png"]))

    res = repo.pool_check()

    assert res.returncode == 1
    assert "[asset-owner] lectures/lqcontrol.md uses _static/kalman/data.csv, which belongs to lectures/kalman.md" in res.stdout
    assert "[asset-owner] lectures/lqcontrol.md uses _static/kalman/fig.png, which belongs to lectures/kalman.md" in res.stdout
    assert tags(res) == ["asset-owner", "asset-owner"]


def test_references_are_file_relative_and_stay_in_the_pool(make_repo):
    repo = make_repo(["intro"])
    body = "```{figure} /_static/kalman/fig.png\n```\n\n```{literalinclude} ../tools/promote\n```"
    write(repo, "kalman.md", lecture_text("Kalman", body=body))
    write(repo, "_static/kalman/fig.png", b"kalman's figure")

    res = repo.pool_check()

    assert res.returncode == 1
    assert ("[root-relative] lectures/kalman.md refers to /_static/kalman/fig.png: write it file-relative, "
            "as _static/kalman/fig.png") in res.stdout
    assert "[escapes] lectures/kalman.md refers to ../tools/promote, outside lectures/" in res.stdout
    assert tags(res) == ["root-relative", "escapes"]
