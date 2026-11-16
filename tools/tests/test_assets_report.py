"""tools/assets-report: the audit of static assets and the shared-asset index (QuantEcon/project-monorepo#9)."""

import json

from conftest import lecture_text

INDEX = "_static/_shared/README.md"


def report(repo, *args):
    """Run the report and return ``(result, markdown, data)``."""
    res = repo.assets_report("--out", "report.md", "--json", "report.json", *args)
    assert res.returncode == 0, res.stdout + res.stderr
    md = (repo.root / "report.md").read_text(encoding="utf-8")
    return res, md, json.loads((repo.root / "report.json").read_text(encoding="utf-8"))


def series_entry(data, series):
    (entry,) = [s for s in data["series"] if s["series"] == series]
    return entry


def write_pool(repo, rel, data):
    path = repo.pool(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    return path


def shared_pool(repo):
    """Promote two lectures that share a figure, each with one of its own."""
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/common/fig.png", b"a figure both use")
    repo.mirror_file("intermediate", "_static/lecture_specific/mccall/own.png", b"mccall's own")
    repo.lecture("intro", "lake", lecture_text("Lake", refs=["/_static/lecture_specific/common/fig.png"]))
    repo.lecture("intermediate", "mccall", lecture_text(
        "McCall", refs=["_static/lecture_specific/mccall/own.png", "_static/lecture_specific/common/fig.png"],
    ))
    assert repo.promote("lake", "mccall").returncode == 0


# --------------------------------------------------------------------------- #
# The series                                                                   #
# --------------------------------------------------------------------------- #
def test_each_file_is_sorted_by_what_uses_it(make_repo):
    repo = make_repo(["intro"])
    repo.mirror_file("intro", "_static/lecture_specific/lake/fig.png", b"png")
    repo.mirror_file("intro", "_static/lecture_specific/lake/fig", b"digraph {}")  # its Graphviz source
    repo.mirror_file("intro", "_static/lecture_specific/lake/fig.tex", b"\\tikz")
    repo.mirror_file("intro", "_static/lecture_specific/lake/old.png", b"nobody's")
    repo.mirror_file("intro", "_static/lecture_specific/lake/data.csv", b"a,b")
    repo.mirror_file("intro", "_static/includes/note.md", "![x](../lecture_specific/lake/inc.png)\n")
    repo.mirror_file("intro", "_static/lecture_specific/lake/inc.png", b"used by the include")
    repo.mirror_file("intro", "_static/qe-logo.png", b"branding")
    repo.mirror_file("intro", "_static/custom.css", b"css")
    repo.mirror_file("intro", "_config.yml", "html:\n  extra_css: _static/custom.css\n")
    repo.lecture("intro", "lake", lecture_text(
        "Lake",
        body="```{include} _static/includes/note.md\n```\n\n"
        "Get [the data](https://github.com/test/intro/blob/main/lectures/_static/lecture_specific/lake/data.csv).",
        refs=["/_static/lecture_specific/lake/fig.png"],
    ))

    _, md, data = report(repo)

    intro = series_entry(data, "intro")
    assert intro["files"] == 9
    # fig.png, the include and the image the include uses
    assert intro["used_by_lecture"] == 3
    assert intro["linked_by_address"] == ["_static/lecture_specific/lake/data.csv"]
    assert intro["used_by_config"] == ["_static/custom.css", "_static/qe-logo.png"]
    orphaned = {o["path"]: o["figure_source"] for o in intro["orphaned"]}
    assert orphaned == {
        "_static/lecture_specific/lake/fig": True,
        "_static/lecture_specific/lake/fig.tex": True,
        "_static/lecture_specific/lake/old.png": False,
    }
    assert "| intro | 9 |" in md
    assert "- `_static/lecture_specific/lake/fig`, 10 B (figure source)" in md


def test_a_lecture_and_the_configuration_are_not_files_beside_it(make_repo):
    repo = make_repo(["intro"])
    repo.lecture("intro", "lake", lecture_text("Lake"))
    repo.mirror_file("intro", "_config.yml", "title: x\n")
    repo.toc("intro", ["lake"])
    repo.mirror_file("intro", "plot.png", b"a loose figure at the top")

    _, _, data = report(repo)

    intro = series_entry(data, "intro")
    assert intro["files"] == 1
    assert [o["path"] for o in intro["orphaned"]] == ["plot.png"]


def test_collisions_are_paths_with_different_bytes(make_repo):
    repo = make_repo(["intro", "intermediate", "advanced"])
    repo.mirror_file("intro", "_static/lecture_specific/a/fig.png", b"one")
    repo.mirror_file("intermediate", "_static/lecture_specific/a/fig.png", b"two")
    repo.mirror_file("advanced", "_static/lecture_specific/a/fig.png", b"two")
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/b/same.png", b"same bytes")

    _, md, data = report(repo)

    assert data["collisions"] == [
        {"path": "_static/lecture_specific/a/fig.png", "groups": [["intro"], ["intermediate", "advanced"]]},
    ]
    assert "- `_static/lecture_specific/a/fig.png`: intro; intermediate, advanced" in md


def test_the_largest_files_name_every_series_that_holds_them(make_repo):
    repo = make_repo(["intro", "intermediate"])
    for series in ("intro", "intermediate"):
        repo.mirror_file(series, "_static/lecture_specific/big/data.csv", b"x" * 5000)
    repo.mirror_file("intro", "_static/lecture_specific/small/a.png", b"x")

    _, md, _ = report(repo)

    largest = md.split("largest files", 1)[1]
    assert largest.index("big/data.csv` | intro, intermediate | 4.9 KB") < largest.index("small/a.png")


def test_the_report_needs_the_mirror(make_repo):
    repo = make_repo(["intro"])
    (repo.root / "mirror" / "intro" / "lectures").rmdir()

    res = repo.assets_report()

    assert res.returncode == 2
    assert "mirror/intro/lectures/ does not exist: run tools/sync first, or pass --reconstruct" in res.stderr


# --------------------------------------------------------------------------- #
# Files on GitHub, by address                                                  #
# --------------------------------------------------------------------------- #
def test_addresses_of_files_on_github_are_listed_by_repository(make_repo):
    repo = make_repo(["intro"])
    body = "\n".join([
        "Data from [the repository](https://github.com/QuantEcon/data-lectures).",
        "```{code-cell} ipython3",
        "a = pd.read_csv('https://github.com/QuantEcon/data-lectures/raw/main/lectures/a.csv')",
        "b = pd.read_csv('https://raw.githubusercontent.com/QuantEcon/data-lectures/main/lectures/b.csv')",
        "url = ('https://github.com/QuantEcon/data-lectures/raw/main/'",
        "       'lectures/c.csv')",
        "c = 'https://github.com/QuantEcon/QuantEcon.py/blob/0123abcd/quantecon/lss.py'",
        "```",
    ])
    write_pool(repo, "lake.md", lecture_text("Lake", body=body))

    _, md, data = report(repo)

    links = {(l["repo"], l["form"], l["ref"], l["path"]) for l in data["github_files"]}
    assert links == {
        ("QuantEcon/data-lectures", "github.com/raw", "main", "lectures/a.csv"),
        ("QuantEcon/data-lectures", "raw.githubusercontent.com", "main", "lectures/b.csv"),
        ("QuantEcon/data-lectures", "github.com/raw", "main", ""),
        ("QuantEcon/QuantEcon.py", "github.com/blob", "0123abcd", "quantecon/lss.py"),
    }
    (pinned,) = [l for l in data["github_files"] if l["repo"] == "QuantEcon/QuantEcon.py"]
    assert pinned["pinned"] is True
    assert "| QuantEcon/data-lectures | 3 | 1 | main 3 |" in md
    assert "an address completed in code (main)" in md


# --------------------------------------------------------------------------- #
# The pool and the index                                                       #
# --------------------------------------------------------------------------- #
def test_the_index_lists_each_shared_file_its_users_and_their_series(make_repo):
    repo = make_repo(["intro", "intermediate", "dp"], consumers=("dp",))
    # dp republishes mccall: the ledger records its copy as superseded.
    repo.lecture("dp", "mccall", lecture_text(
        "McCall", refs=["_static/lecture_specific/mccall/own.png", "_static/lecture_specific/common/fig.png"],
    ))
    repo.mirror_file("dp", "_static/lecture_specific/mccall/own.png", b"mccall's own")
    repo.mirror_file("dp", "_static/lecture_specific/common/fig.png", b"a figure both use")
    shared_pool(repo)
    assert {s["series"] for s in repo.entry("mccall")["superseded"]} == {"dp"}

    res = repo.assets_report("--write-index")

    assert res.returncode == 0, res.stdout + res.stderr
    index = repo.pool(INDEX).read_text(encoding="utf-8")
    assert "Generated by tools/assets-report --write-index" in index
    assert "| `common/fig.png` | `lake`, `mccall` | intro, intermediate, dp |" in index
    assert "mccall/own.png" not in index  # a lecture's own folder needs no index
    assert repo.assets_report("--check-index").returncode == 0
    # The index sits in _shared/ without breaking the pool's layout.
    write_pool(repo, "_static/quant-econ.bib", "")
    assert repo.pool_check().returncode == 0


def test_a_stale_or_missing_index_fails_the_check(make_repo):
    repo = make_repo(["intro", "intermediate"])
    shared_pool(repo)

    res = repo.assets_report("--check-index")
    assert res.returncode == 1
    assert f"lectures/{INDEX} is missing: run tools/assets-report --write-index and commit it" in res.stdout

    assert repo.assets_report("--write-index").returncode == 0
    index = repo.pool(INDEX)
    index.write_text(index.read_text(encoding="utf-8").replace("`lake`, ", ""), encoding="utf-8")

    res = repo.assets_report("--check-index")
    assert res.returncode == 1
    assert f"lectures/{INDEX} is stale" in res.stdout


def test_a_file_no_pool_lecture_uses_is_an_orphan(make_repo):
    repo = make_repo(["intro", "intermediate"])
    shared_pool(repo)
    write_pool(repo, "_static/mccall/left_behind.png", b"no reference")
    write_pool(repo, "_static/quant-econ.bib", "")  # the merged bibliography is not an asset
    assert repo.assets_report("--write-index").returncode == 0

    res = repo.assets_report("--check-index")

    assert res.returncode == 1
    assert "lectures/_static/mccall/left_behind.png is used by no pool lecture" in res.stdout
    assert "1 problem(s)." in res.stdout
    _, md, data = report(repo)
    assert data["pool"]["orphaned"] == ["_static/mccall/left_behind.png"]
    assert "**1 orphaned**" in md


def test_a_shared_file_one_lecture_uses_is_listed_not_failed(make_repo):
    repo = make_repo(["intro"])
    # A family folder: promote places it in _shared/ whatever its count.
    repo.mirror_file("intro", "_static/lecture_specific/family/fig.png", b"family")
    repo.lecture("intro", "lake", lecture_text("Lake", refs=["_static/lecture_specific/family/fig.png"]))
    assert repo.promote("lake").returncode == 0
    assert repo.pool("_static/_shared/family/fig.png").is_file()
    assert repo.assets_report("--write-index").returncode == 0

    assert repo.assets_report("--check-index").returncode == 0
    _, md, _ = report(repo)
    assert "1 files in `_shared/` are used by one lecture alone" in md
    assert "- `_static/_shared/family/fig.png`: `lake`" in md


def test_the_index_options_take_no_other(make_repo):
    repo = make_repo(["intro"])

    res = repo.assets_report("--check-index", "--out", "x.md")

    assert res.returncode == 2
    assert "--write-index and --check-index take no other option" in res.stderr
