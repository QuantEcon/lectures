"""sites/<key>/: tools/pool-check's site rules, tools/stage-site, and the
drift-check's ``site-stale`` (QuantEcon/project-monorepo#21)."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from conftest import lecture_text

URL = "https://intro.quantecon.org/"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    return path


def config(key="intro", url=URL, mapping=None, disabled=True, **top):
    """A valid site's _config.yml as the build reads it: the series' settings
    (branding, the address, the cross-reference settings) with the site
    additions already applied, so the pool's repository and execution cache,
    not the series' own."""
    sphinx = {
        "html_favicon": "_static/lectures-favicon.ico",
        "html_theme_options": {
            "dark_logo": "quantecon-logo-transparent.png",
            "repository_url": "https://github.com/QuantEcon/lectures",
            "path_to_docs": "lectures",
        },
        "intersphinx_mapping": {key: [url, None]} if mapping is None else mapping,
    }
    if disabled:
        sphinx["intersphinx_disabled_reftypes"] = []
    data = {
        "title": key,
        "logo": "_static/qe-logo.png",
        "only_build_toc_files": True,
        "execute": {"execute_notebooks": "cache", "cache": f"_build/jupyter_cache/{key}"},
        "html": {"baseurl": url},
        "sphinx": {"config": sphinx},
    }
    data.update(top)
    return yaml.safe_dump(data, sort_keys=False)


def site_yml(**fields):
    data = {"type": "series", "runner": "ubuntu-latest", "cell_timeout": 600, "publishes": ["html", "pdf"], "url": URL}
    data.update(fields)
    return yaml.safe_dump({k: v for k, v in data.items() if v is not None}, sort_keys=False)


def make_site(repo, key="intro", toc=("intro", "solow"), pages=("intro",), cfg=None, meta=None):
    site = repo.root / "sites" / key
    write(site / "_toc.yml", "format: jb-book\nroot: " + toc[0] + "\nchapters:\n" + "".join(f"- file: {n}\n" for n in toc[1:]))
    write(site / "_config.yml", cfg if cfg is not None else config(key))
    write(site / "site.yml", meta if meta is not None else site_yml())
    for page in pages:
        write(site / f"{page}.md", lecture_text(f"{key}: {page}"))
    for name in ("qe-logo.png", "lectures-favicon.ico", "quantecon-logo-transparent.png"):
        write(site / "_static" / name, f"{key}'s {name}")
    return site


def pool_repo(make_repo, series=("intro",), consumers=()):
    repo = make_repo(list(series), consumers=consumers)
    write(repo.pool("solow.md"), lecture_text("Solow"))
    write(repo.pool("_static/quant-econ.bib"), "")
    return repo


def problems(res):
    return [line.strip() for line in res.stdout.splitlines() if line.startswith("  [")]


def test_a_site_whose_folder_is_true_to_the_pool_is_clean(make_repo):
    repo = pool_repo(make_repo)
    make_site(repo)
    write(repo.root / "sites" / "README.md", "# Sites\n")

    res = repo.pool_check()

    assert res.returncode == 0, res.stdout
    assert "1 lectures, 1 files under _static/, 1 site(s)" in res.stdout


def test_every_toc_entry_is_a_pool_lecture_or_a_page_of_the_site(make_repo):
    repo = pool_repo(make_repo)
    make_site(repo, toc=("intro", "solow", "solow.md", "cobweb", "status"))

    res = repo.pool_check()

    assert res.returncode == 1
    assert problems(res) == [
        "[site-toc] sites/intro/_toc.yml lists cobweb, which is neither lectures/cobweb.md nor sites/intro/cobweb.md",
        "[site-toc] sites/intro/_toc.yml lists status, which is neither lectures/status.md nor sites/intro/status.md",
    ]


def test_a_glob_entry_is_reported_not_resolved(make_repo):
    repo = pool_repo(make_repo)
    site = make_site(repo)
    write(site / "_toc.yml", "format: jb-book\nroot: intro\nchapters:\n- glob: '*'\n")

    res = repo.pool_check()

    assert problems(res) == ["[site-toc] sites/intro/_toc.yml has `glob: *`, which this check cannot resolve: list each file"]


def test_staging_may_not_overwrite_a_pool_file(make_repo):
    repo = pool_repo(make_repo)
    write(repo.pool("_static/solow/fig.png"), "solow's figure")
    write(repo.pool("solow.md"), lecture_text("Solow") + "\n![fig](_static/solow/fig.png)\n")
    site = make_site(repo, pages=("intro", "solow"))
    write(site / "_static" / "solow" / "fig.png", "another figure")

    res = repo.pool_check()

    assert problems(res) == [
        "[site-page] sites/intro/solow.md has a pool lecture's name: staging it would overwrite lectures/solow.md",
        "[site-page] sites/intro/_static/solow/fig.png is also lectures/_static/solow/fig.png: staging would "
        "overwrite the pool's file",
    ]


def test_a_site_folder_holds_its_files_pages_and_static_only(make_repo):
    repo = pool_repo(make_repo)
    site = make_site(repo)
    (site / "site.yml").unlink()
    write(site / "notes.txt", "scratch")
    write(site / "drafts" / "intro.md", "draft")
    write(repo.root / "sites" / "stray.yml", "")

    res = repo.pool_check()

    assert problems(res) == [
        "[site-layout] sites/intro/drafts/ is none of a site's files: _config.yml, _toc.yml, site.yml, its pages "
        "(<name>.md) and _static/",
        "[site-layout] sites/intro/notes.txt is none of a site's files: _config.yml, _toc.yml, site.yml, its pages "
        "(<name>.md) and _static/",
        "[site-layout] sites/intro/ has no site.yml",
        "[site-layout] sites/stray.yml is not a site's folder: sites/ holds sites/<key>/ and README.md",
    ]


def test_site_yml_has_the_fields_the_build_reads_with_valid_values(make_repo):
    repo = pool_repo(make_repo)
    make_site(repo, meta=site_yml(
        type="course", runner="macos-latest", cell_timeout="600", publishes=["pdf", "epub"], url=None, runners=2,
    ))

    res = repo.pool_check()

    assert problems(res) == [
        "[site-yml] sites/intro/site.yml has no `url`",
        "[site-yml] sites/intro/site.yml: `runners` is not a field the build reads (type, runner, cell_timeout, "
        "publishes, url; optional: extra_packages, environment, local_links)",
        "[site-yml] sites/intro/site.yml: type 'course' is not one of series",
        "[site-yml] sites/intro/site.yml: runner 'macos-latest' is not one of ubuntu-latest, g4dn.2xlarge",
        "[site-yml] sites/intro/site.yml: cell_timeout '600' is not a whole number of seconds above 0",
        "[site-yml] sites/intro/site.yml: publishes ['pdf', 'epub'] is not a list of html, pdf, notebooks, each "
        "at most once, with html",
    ]


@pytest.mark.parametrize("value,ok", [
    (["jax"], True),
    (["jax[cuda13]", "optax>=0.2,<0.3"], True),
    ([], False),
    ("jax", False),
    (["jax", "jax"], False),
    (["-r requirements.txt"], False),
    (["--index-url=https://example.org/simple"], False),
    (["jax @ https://example.org/jax.whl"], False),
    ([3], False),
])
def test_site_yml_may_list_extra_packages_as_plain_pip_requirements(make_repo, value, ok):
    repo = pool_repo(make_repo)
    make_site(repo, meta=site_yml(extra_packages=value))

    res = repo.pool_check()

    if ok:
        assert res.returncode == 0, res.stdout + res.stderr
    else:
        assert problems(res) == [
            f"[site-yml] sites/intro/site.yml: extra_packages {value!r} is not a list of pip requirements (a name, "
            "optional [extras] and version specifiers, no spaces, none starting with -), each at most once",
        ]


@pytest.mark.parametrize("value,ok", [("series", True), ("base", True), (None, True), ("universal", False), (3, False)])
def test_site_yml_may_name_the_environment_it_builds_in(make_repo, value, ok):
    repo = pool_repo(make_repo)
    make_site(repo, meta=site_yml(environment=value))

    res = repo.pool_check()

    if ok:
        assert res.returncode == 0, res.stdout + res.stderr
    else:
        assert problems(res) == [
            f"[site-yml] sites/intro/site.yml: environment {value!r} is not one of series, base",
        ]


def test_site_yml_url_is_the_published_address_and_a_series_site_is_named_for_its_series(make_repo):
    repo = pool_repo(make_repo)
    make_site(repo, key="intro", meta=site_yml(url="https://example.org/"))
    make_site(repo, key="lectures", cfg=config("lectures"))

    res = repo.pool_check()

    assert problems(res) == [
        "[site-config] sites/intro/_config.yml maps `intro` to 'https://intro.quantecon.org/', not to its site.yml "
        "url 'https://example.org/'",
        "[site-yml] sites/intro/site.yml: url 'https://example.org/' is not html.baseurl in _config.yml "
        "('https://intro.quantecon.org/')",
        "[site-yml] sites/lectures/site.yml: a site of type series is named for its series, and `lectures` is not "
        "a series key in sync/manifest.yml (intro)",
    ]


def test_the_cross_reference_rules_hold_in_every_site(make_repo):
    # Every site maps itself and sets intersphinx_disabled_reftypes: []; no
    # site maps a consumer (dp), and a consumer is not asked to map itself.
    repo = pool_repo(make_repo, series=("intro", "dp"), consumers=("dp",))
    make_site(repo, key="intro", cfg=config("intro", mapping={"dp": ["https://dp.example/", None]}, disabled=False))
    make_site(repo, key="dp", cfg=config("dp", mapping={"intro": [URL, None]}))

    res = repo.pool_check()

    assert problems(res) == [
        "[site-config] sites/intro/_config.yml does not set `intersphinx_disabled_reftypes: []`: a link with no "
        "target in the site must resolve on the lecture's home site",
        "[site-config] sites/intro/_config.yml maps `dp` in intersphinx_mapping: dp only republishes other series' "
        "lectures, so a link must never resolve there",
        "[site-config] sites/intro/_config.yml does not map `intro` in intersphinx_mapping: a site maps itself, "
        "since a pool lecture may link to its home series' site by prefix ({doc}`intro:<name>`)",
    ]


def test_the_branding_a_config_names_is_in_the_site(make_repo):
    repo = pool_repo(make_repo)
    site = make_site(repo)
    (site / "_static" / "lectures-favicon.ico").unlink()
    (site / "_static" / "quantecon-logo-transparent.png").unlink()

    res = repo.pool_check()

    assert problems(res) == [
        "[site-config] sites/intro/_config.yml names _static/lectures-favicon.ico as `html_favicon`, and "
        "sites/intro/_static/lectures-favicon.ico does not exist",
        "[site-config] sites/intro/_config.yml names _static/quantecon-logo-transparent.png as `dark_logo`, and "
        "sites/intro/_static/quantecon-logo-transparent.png does not exist",
    ]


def test_the_additions_a_build_needs_are_there(make_repo):
    repo = pool_repo(make_repo)
    data = yaml.safe_load(config("intro"))
    data["only_build_toc_files"] = False
    data["execute"]["cache"] = "_build/jupyter_cache"
    theme = data["sphinx"]["config"]["html_theme_options"]
    theme["repository_url"] = "https://github.com/QuantEcon/lecture-python-intro"
    del theme["path_to_docs"]
    make_site(repo, cfg=yaml.safe_dump(data))

    res = repo.pool_check()

    assert problems(res) == [
        "[site-config] sites/intro/_config.yml does not set `only_build_toc_files: true`: without it Jupyter Book "
        "builds every lecture in the pool, not the site's contents",
        "[site-config] sites/intro/_config.yml: `execute.cache` is '_build/jupyter_cache', not "
        "_build/jupyter_cache/intro: each site keeps its own execution cache",
        "[site-config] sites/intro/_config.yml: `repository_url` is "
        "'https://github.com/QuantEcon/lecture-python-intro', not https://github.com/QuantEcon/lectures: the theme "
        "lists each page's changes from this repository's history, so its commit, history and GitHub links must "
        "name it (set it on a marked line after the series' own: the later key wins)",
        "[site-config] sites/intro/_config.yml: `path_to_docs` is None, not lectures: a page's full history link is "
        "the page's path in the repository, under the pool's folder",
    ]


@pytest.mark.parametrize("override_last, ok", [(True, True), (False, False)])
def test_the_repository_is_overridden_by_a_marked_line_after_the_series_own(make_repo, override_last, ok):
    # The series' repository_url stays verbatim, and a marked line repeats the
    # key: YAML's later key wins, as Jupyter Book 1 reads the file. Placed
    # before the series' line, the series' value wins, which is a finding.
    repo = pool_repo(make_repo)
    series = "      repository_url: https://github.com/QuantEcon/lecture-python-intro\n"
    ours = "      repository_url: https://github.com/QuantEcon/lectures  # site addition\n"
    text = config("intro").replace("      repository_url: https://github.com/QuantEcon/lectures\n",
                                   series + ours if override_last else ours + series)
    assert text.count("repository_url:") == 2
    make_site(repo, cfg=text)

    res = repo.pool_check()

    assert (res.returncode == 0) is ok, res.stdout + res.stderr
    assert any("`repository_url` is 'https://github.com/QuantEcon/lecture-python-intro'" in p
               for p in problems(res)) is not ok


@pytest.mark.parametrize("change, shown", [
    ({"sphinx": [1]}, "sphinx"),
    ({"sphinx": {"config": "x"}}, "sphinx.config"),
    ({"sphinx": {"config": {"intersphinx_mapping": ["a", "b"], "intersphinx_disabled_reftypes": []}}},
     "sphinx.config.intersphinx_mapping"),
    ({"html": "x"}, "html"),
    ({"execute": ["cache"]}, "execute"),
])
def test_a_config_of_the_wrong_shape_is_a_finding_not_a_crash(make_repo, change, shown):
    repo = pool_repo(make_repo)
    data = yaml.safe_load(config("intro"))
    data.update(change)
    make_site(repo, cfg=yaml.safe_dump(data))

    res = repo.pool_check()

    assert res.returncode == 1, res.stdout + res.stderr
    assert f"[site-config] sites/intro/_config.yml: `{shown}` is not a mapping" in problems(res)


def staged(repo):
    return sorted(p.relative_to(repo.root).as_posix() for p in repo.pool("").rglob("*"))


def test_stage_site_copies_a_site_in_refuses_a_second_and_cleans_up(make_repo):
    repo = pool_repo(make_repo, series=("intro", "dp"), consumers=("dp",))
    make_site(repo, key="intro")
    write(repo.root / "sites" / "intro" / "_static" / "lecture_specific" / "troubleshooting" / "launch.png", "png")
    make_site(repo, key="dp", cfg=config("dp", mapping={"intro": [URL, None]}))
    assert repo.pool_check().returncode == 0
    before = staged(repo)

    res = repo.stage_site("intro")

    assert res.returncode == 0, res.stdout + res.stderr
    assert "stage-site intro: 7 file(s) copied into lectures/ (recorded in _build/stage-site.json)" in res.stdout
    assert repo.pool("intro.md").read_text() == (repo.root / "sites/intro/intro.md").read_text()
    assert repo.pool("_static/lecture_specific/troubleshooting/launch.png").read_text() == "png"
    # The site's config and toc, where jb build lectures finds them by default;
    # site.yml is the workflow's, never copied.
    for name in ("_config.yml", "_toc.yml"):
        assert repo.pool(name).read_text() == (repo.root / "sites/intro" / name).read_text()
    assert not repo.pool("site.yml").exists()
    record = json.loads((repo.root / "_build" / "stage-site.json").read_text())
    assert record["site"] == "intro"
    assert [f["path"] for f in record["files"]] == [
        "lectures/_config.yml",
        "lectures/_toc.yml",
        "lectures/intro.md",
        "lectures/_static/lecture_specific/troubleshooting/launch.png",
        "lectures/_static/lectures-favicon.ico",
        "lectures/_static/qe-logo.png",
        "lectures/_static/quantecon-logo-transparent.png",
    ]
    assert record["dirs"] == ["lectures/_static/lecture_specific", "lectures/_static/lecture_specific/troubleshooting"]

    for again in ("intro", "dp"):  # one site at a time, and the same one only once
        res = repo.stage_site(again)
        assert res.returncode == 1
        assert "refused, nothing copied: sites/intro is staged (_build/stage-site.json)" in res.stdout
    assert repo.stage_site("--clean", "dp").returncode == 1

    write(repo.pool("_static/qe-logo.png"), "edited after staging")
    res = repo.stage_site("--clean", "intro")
    assert res.returncode == 0
    assert "kept lectures/_static/qe-logo.png: its bytes are not the ones staging copied" in res.stdout
    assert "6 file(s) removed" in res.stdout
    assert not (repo.root / "_build" / "stage-site.json").exists()
    repo.pool("_static/qe-logo.png").unlink()
    assert staged(repo) == before  # the lecture_specific/ folders it made went too
    assert repo.stage_site("dp").returncode == 0


INT_URL = "https://python.quantecon.org/"
LINKING = "\n".join([
    "See {doc}`intermediate:carried` and {doc}`the other lecture <intro:carried>`.",
    "Also [this lecture](https://python.quantecon.org/carried.html) and [the old address](https://python-intro.quantecon.org/carried.html).",
    "Left alone: {doc}`intermediate:elsewhere`, [a page it lacks](https://python.quantecon.org/elsewhere.html),",
    "[an anchor](https://python.quantecon.org/carried.html#a-section), an unmapped host [x](https://example.org/carried.html),",
    "the literal ``{doc}`intermediate:carried` `` and an unmapped prefix {doc}`programming:carried`.",
    "",
    "```{code-cell} ipython3",
    "url = '[here](https://python.quantecon.org/carried.html)'  # {doc}`intermediate:carried`",
    "```",
])


def links_repo(make_repo):
    """dp, a consumer that maps intro and intermediate, carries `carried` and
    `linking`; `linking` links to `carried` in every form the rewrite reads."""
    repo = pool_repo(make_repo, series=("intro", "intermediate", "programming", "dp"), consumers=("dp",))
    write(repo.pool("carried.md"), lecture_text("Carried"))
    write(repo.pool("elsewhere.md"), lecture_text("Elsewhere"))
    write(repo.pool("linking.md"), lecture_text("Linking", LINKING))
    make_site(repo, key="dp", toc=("intro", "carried", "linking"),
              cfg=config("dp", mapping={"intro": [URL, None], "intermediate": [INT_URL, None]}))
    make_site(repo, key="intro", toc=("intro", "elsewhere"))
    return repo


def test_stage_site_local_links_rewrites_a_consumers_links_to_lectures_it_carries_and_clean_puts_them_back(make_repo):
    repo = links_repo(make_repo)
    original = repo.pool("linking.md").read_bytes()

    res = repo.stage_site("--local-links", "dp")

    assert res.returncode == 0, res.stdout + res.stderr
    assert "stage-site dp: 4 link(s) in 1 lecture(s) rewritten to lectures within the site" in res.stdout
    text = repo.pool("linking.md").read_text()
    assert "See {doc}`carried` and {doc}`the other lecture <carried>`." in text
    assert "Also [this lecture](carried.md) and [the old address](carried.md)." in text
    # Not a lecture the site carries, an anchor, a host the site does not map,
    # an inline literal, a prefix the site does not map, and a code cell.
    for kept in ("{doc}`intermediate:elsewhere`", "(https://python.quantecon.org/elsewhere.html)",
                 "(https://python.quantecon.org/carried.html#a-section)", "(https://example.org/carried.html)",
                 "``{doc}`intermediate:carried` ``", "{doc}`programming:carried`",
                 "url = '[here](https://python.quantecon.org/carried.html)'  # {doc}`intermediate:carried`"):
        assert kept in text, kept
    record = json.loads((repo.root / "_build" / "stage-site.json").read_text())
    assert [r["path"] for r in record["rewritten"]] == ["lectures/linking.md"]
    assert (repo.root / "_build/stage-site-originals/linking.md").read_bytes() == original

    res = repo.stage_site("--clean", "dp")

    assert res.returncode == 0, res.stdout
    assert "1 lecture(s) put back" in res.stdout
    assert repo.pool("linking.md").read_bytes() == original
    assert not (repo.root / "_build" / "stage-site-originals").exists()
    assert repo.pool_check().returncode == 0


def test_stage_site_local_links_is_for_a_consumer_and_leaves_a_lecture_edited_after_staging(make_repo):
    repo = links_repo(make_repo)
    before = staged(repo)

    res = repo.stage_site("--local-links", "intro")
    assert res.returncode == 1
    assert ("stage-site intro: refused, nothing copied: --local-links is for a consumer site, and "
            "sync/manifest.yml does not mark intro `class: consumer`") in res.stdout
    assert staged(repo) == before

    assert repo.stage_site("--local-links", "dp").returncode == 0
    write(repo.pool("linking.md"), "edited after staging\n")
    res = repo.stage_site("--clean", "dp")
    assert res.returncode == 0
    assert ("kept lectures/linking.md: its bytes are not the ones staging wrote; its original is left at "
            "_build/stage-site-originals/linking.md") in res.stdout
    assert repo.pool("linking.md").read_text() == "edited after staging\n"
    # Staging the lecture again would replace that original, so it refuses.
    write(repo.pool("linking.md"), lecture_text("Linking", LINKING))
    res = repo.stage_site("--local-links", "dp")
    assert res.returncode == 1
    assert "  [exists] _build/stage-site-originals/linking.md" in res.stdout
    assert "refused, nothing copied: a lecture's original is left from an earlier --clean" in res.stdout
    assert not (repo.root / "_build" / "stage-site.json").exists()


def stage_site_module():
    loader = importlib.machinery.SourceFileLoader("stage_site_under_test", str(Path(__file__).parent.parent / "stage-site"))
    spec = importlib.util.spec_from_loader("stage_site_under_test", loader)
    tool = importlib.util.module_from_spec(spec)
    loader.exec_module(tool)
    return tool


HOSTS = ["https://python.quantecon.org/"]
LINK = "{doc}`intermediate:carried`"
ADDRESS = "[it](https://python.quantecon.org/carried.html)"


@pytest.mark.parametrize("text, expected, n", [
    # A % comment line, and the blocks whose body is code or literal text:
    # plain, with a language, and tilde fences.
    (f"% {LINK} {ADDRESS}", None, 0),
    (f"```\n{LINK} {ADDRESS}\n```", None, 0),
    (f"```python\n{LINK} {ADDRESS}\n```", None, 0),
    (f"~~~\n{LINK} {ADDRESS}\n~~~", None, 0),
    (f"~~~~{{code-block}} md\n{LINK}\n~~~~", None, 0),
    # A single-backtick literal is masked; a link after one on the line is read.
    (f"`{ADDRESS}` and {LINK}", f"`{ADDRESS}` and {{doc}}`carried`", 1),
    # A directive's body is prose, and a code cell inside it is not.
    (f"````{{note}}\nSee {LINK} and {ADDRESS}.\n\n```{{code-cell}} ipython3\n# {LINK} {ADDRESS}\n```\n````",
     f"````{{note}}\nSee {{doc}}`carried` and [it](carried.md).\n\n```{{code-cell}} ipython3\n# {LINK} {ADDRESS}\n```\n````",
     2),
    # A line opening with inline code is not a fence, and the rest is prose.
    (f"```x``` then {LINK}", f"```x``` then {{doc}}`carried`", 1),
    # An inline literal may run across a line break, as CommonMark reads one,
    # but not across a blank line or out of a heading.
    (f"Before `a literal that\n{ADDRESS} and {LINK}` crosses a line.", None, 0),
    (f"``two\n{ADDRESS}``", None, 0),
    (f"`x`\n{ADDRESS}", "`x`\n[it](carried.md)", 1),
    (f"`unclosed\n\n{ADDRESS}`", "`unclosed\n\n[it](carried.md)`", 1),
    (f"# A `heading\n{ADDRESS}`", "# A `heading\n[it](carried.md)`", 1),
    # Nor out of a list item into the next, or past a target line.
    (f"- a `stray\n- {ADDRESS} and `x`", "- a `stray\n- [it](carried.md) and `x`", 1),
    (f"1. a `stray\n   still the item `\n2. {ADDRESS}", f"1. a `stray\n   still the item `\n2. [it](carried.md)", 1),
    # An item's indented next lines continue it, literal and all.
    (f"- a `literal\n  {ADDRESS}` here", None, 0),
    (f"A `stray\n(here)=\n{ADDRESS} and `x`", "A `stray\n(here)=\n[it](carried.md) and `x`", 1),
    # A literal opens at a whole run: two backticks are not a single one's opener.
    (f"``x {ADDRESS} `", "``x [it](carried.md) `", 1),
])
def test_rewrite_links_reads_prose_alone(text, expected, n):
    tool = stage_site_module()

    assert tool.rewrite_links(text, {"carried"}, {"intermediate"}, HOSTS) == (text if expected is None else expected, n)


def test_stage_site_local_links_reads_a_nested_toc_and_the_sites_own_address_and_leaves_its_own_pages(make_repo):
    repo = pool_repo(make_repo, series=("intro", "intermediate", "dp"), consumers=("dp",))
    write(repo.pool("carried.md"), lecture_text("Carried"))
    write(repo.pool("deep.md"), lecture_text("Deep"))
    write(repo.pool("linking.md"), lecture_text("Linking", "\n".join([
        "[Its own address](https://dp.quantecon.org/carried.html), a section {doc}`intermediate:deep`,",
        "intro's root {doc}`intro:intro` and [by address](https://intro.quantecon.org/intro.html).",
    ])))
    make_site(repo, key="dp", toc=("intro", "carried"), meta=site_yml(url="https://dp.quantecon.org/"),
              cfg=config("dp", mapping={"intro": [URL, None], "intermediate": [INT_URL, None]}))
    write(repo.root / "sites/dp/_toc.yml", "\n".join([
        "format: jb-book", "root: intro", "parts:", "- caption: One", "  chapters:", "  - file: carried",
        "  - file: linking", "    sections:", "    - file: deep", "",
    ]))

    res = repo.stage_site("--local-links", "dp")

    assert res.returncode == 0, res.stdout + res.stderr
    assert "stage-site dp: 2 link(s) in 1 lecture(s) rewritten to lectures within the site" in res.stdout
    text = repo.pool("linking.md").read_text()
    assert "[Its own address](carried.md), a section {doc}`deep`," in text
    # intro is the site's own page, not a lecture it carries: the links to
    # intro's root still go to intro's site.
    assert "intro's root {doc}`intro:intro` and [by address](https://intro.quantecon.org/intro.html)." in text


def test_stage_site_clean_keeps_a_lecture_whose_original_is_gone_and_refuses_a_record_outside_its_folders(make_repo):
    repo = links_repo(make_repo)
    assert repo.stage_site("--local-links", "dp").returncode == 0
    rewritten = repo.pool("linking.md").read_bytes()
    (repo.root / "_build/stage-site-originals/linking.md").unlink()

    res = repo.stage_site("--clean", "dp")

    assert res.returncode == 0, res.stdout
    assert ("kept lectures/linking.md as it is: its original, _build/stage-site-originals/linking.md, is gone, "
            "so it cannot be put back") in res.stdout
    assert "its bytes are not" not in res.stdout
    assert repo.pool("linking.md").read_bytes() == rewritten
    assert not (repo.root / "_build" / "stage-site.json").exists()

    write(repo.pool("linking.md"), lecture_text("Linking", LINKING))
    assert repo.stage_site("--local-links", "dp").returncode == 0
    record_path = repo.root / "_build" / "stage-site.json"
    record = json.loads(record_path.read_text())
    record["rewritten"][0]["original"] = "lectures/solow.md"
    record_path.write_text(json.dumps(record))
    before = staged(repo)

    res = repo.stage_site("--clean", "dp")

    assert res.returncode == 2
    assert "names lectures/solow.md, which is not inside _build/stage-site-originals/" in res.stderr
    assert staged(repo) == before  # nothing removed or put back
    assert record_path.exists()


def test_stage_site_local_links_rewrites_only_a_file_directly_in_the_pool(make_repo):
    repo = links_repo(make_repo)
    outside = write(repo.root / "notes" / "outside.md", lecture_text("Outside", LINKING))
    nested = write(repo.pool("sub/page.md"), lecture_text("Nested", LINKING))
    (repo.pool("linked.md")).symlink_to(Path("..") / "notes" / "outside.md")
    # Two more names for linking.md: a link to it in the pool, and a case
    # variant, which a disk that ignores case (macOS's) finds.
    (repo.pool("alias.md")).symlink_to("linking.md")
    original = repo.pool("linking.md").read_bytes()
    write(repo.root / "sites/dp/_toc.yml", "\n".join([
        "format: jb-book", "root: intro", "chapters:", "- file: carried", "- file: linking",
        "- file: ../notes/outside", "- file: sub/page", "- file: linked", "- file: alias", "- file: LINKING", "",
    ]))
    before = {p: p.read_bytes() for p in (outside, nested)}

    res = repo.stage_site("--local-links", "dp")

    assert res.returncode == 0, res.stdout + res.stderr
    assert "stage-site dp: 4 link(s) in 1 lecture(s) rewritten to lectures within the site" in res.stdout
    assert {p: p.read_bytes() for p in (outside, nested)} == before
    record = json.loads((repo.root / "_build" / "stage-site.json").read_text())
    assert [r["path"] for r in record["rewritten"]] == ["lectures/linking.md"]
    res = repo.stage_site("--clean", "dp")
    assert res.returncode == 0
    assert "1 lecture(s) put back" in res.stdout
    assert repo.pool("linking.md").read_bytes() == original


def test_stage_site_clean_leaves_a_lecture_removed_since_staging_removed(make_repo):
    repo = links_repo(make_repo)
    assert repo.stage_site("--local-links", "dp").returncode == 0
    repo.pool("linking.md").unlink()

    res = repo.stage_site("--clean", "dp")

    assert res.returncode == 0, res.stdout
    assert ("kept lectures/linking.md as it is: it is no longer a plain file, so its original is left at "
            "_build/stage-site-originals/linking.md") in res.stdout
    assert not repo.pool("linking.md").exists()
    assert (repo.root / "_build/stage-site-originals/linking.md").is_file()
    assert not (repo.root / "_build" / "stage-site.json").exists()


def test_stage_site_clean_never_writes_through_a_link_left_in_a_lectures_place(make_repo):
    repo = links_repo(make_repo)
    assert repo.stage_site("--local-links", "dp").returncode == 0
    # A link that leads out of the pool is refused before anything is touched;
    # this one stays inside it, to a file holding the bytes staging wrote, so
    # only the link check stops the original being written through it.
    target = write(repo.pool("staged-copy.md"), repo.pool("linking.md").read_bytes())
    before = target.read_bytes()
    repo.pool("linking.md").unlink()
    repo.pool("linking.md").symlink_to("staged-copy.md")

    res = repo.stage_site("--clean", "dp")

    assert target.read_bytes() == before
    assert res.returncode == 0, res.stdout
    assert "kept lectures/linking.md as it is: it is no longer a plain file" in res.stdout
    assert (repo.root / "_build/stage-site-originals/linking.md").is_file()


def test_site_yml_local_links_is_true_or_false_and_only_a_consumers(make_repo):
    repo = pool_repo(make_repo, series=("intro", "dp"), consumers=("dp",))
    make_site(repo, key="intro", meta=site_yml(local_links=True))
    make_site(repo, key="dp", cfg=config("dp", mapping={"intro": [URL, None]}), meta=site_yml(local_links="yes"))

    res = repo.pool_check()

    assert problems(res) == [
        "[site-yml] sites/dp/site.yml: local_links 'yes' is not true or false",
        "[site-yml] sites/intro/site.yml: local_links is for a consumer series' site, whose copies link to their home "
        "series' sites, and `intro` is not `class: consumer` in sync/manifest.yml",
    ]


@pytest.mark.parametrize("name", ["_config.yml", "_toc.yml"])
def test_stage_site_refuses_a_config_or_toc_already_in_the_pool_which_pool_check_fails(make_repo, name):
    repo = pool_repo(make_repo)
    make_site(repo)
    write(repo.pool(name), "left from an earlier build\n")
    before = staged(repo)

    res = repo.pool_check()
    assert res.returncode == 1
    assert f"[top-level] lectures/{name} is neither a lecture (<slug>.md) nor _static/" in res.stdout

    res = repo.stage_site("intro")
    assert res.returncode == 1
    assert f"[exists] lectures/{name}" in res.stdout
    assert "refused, nothing copied: staging never overwrites" in res.stdout
    assert not (repo.root / "_build" / "stage-site.json").exists()
    assert staged(repo) == before
    assert repo.pool(name).read_text() == "left from an earlier build\n"


def test_stage_site_never_touches_a_file_it_did_not_copy(make_repo):
    # A pool file byte-identical to a site's file is not "already staged":
    # staging refuses it, and a clean can never remove it.
    repo = pool_repo(make_repo)
    site = make_site(repo)
    launch = "_static/lecture_specific/troubleshooting/launch.png"
    write(site / launch, "png")
    write(repo.pool(launch), "png")
    before = staged(repo)

    res = repo.stage_site("intro")

    assert res.returncode == 1
    assert f"[exists] lectures/{launch}" in res.stdout
    assert "refused, nothing copied: staging never overwrites" in res.stdout
    assert not (repo.root / "_build" / "stage-site.json").exists()
    assert repo.stage_site("--clean", "intro").returncode == 0
    assert staged(repo) == before
    assert repo.pool(launch).read_text() == "png"


@pytest.mark.parametrize("key", ["jax", ".", "..", "intro/", "intro/.."])
def test_stage_site_takes_only_a_site_folder(make_repo, key):
    repo = pool_repo(make_repo)
    make_site(repo)
    (repo.root / "sites" / "notes").mkdir()  # a folder, but not a site

    for k in (key, "notes"):
        res = repo.stage_site(k)
        assert res.returncode == 1
        assert f"there is no site sites/{k}/ (sites: intro)" in res.stderr
    assert not (repo.root / "_build").exists()


# --------------------------------------------------------------------------- #
# The drift-check's site-stale                                                #
# --------------------------------------------------------------------------- #
UPSTREAM_CONFIG = """title: intro
execute:
  execute_notebooks: "cache"
sphinx:
  config:
    html_theme_options:
      repository_url: https://github.com/QuantEcon/lecture-python-intro
      path_to_docs: lectures
    intersphinx_mapping:
      intermediate:
        - "https://python.quantecon.org/"
        - null
"""
SITE_CONFIG = """title: intro
# site addition: build only the toc's pages
only_build_toc_files: true  # site addition
execute:
  # site addition: this site's own cache
  cache: _build/jupyter_cache/intro  # site addition
  execute_notebooks: "cache"
sphinx:
  config:
    html_theme_options:
      repository_url: https://github.com/QuantEcon/lecture-python-intro
      # site addition: an override, the key again after the series' line
      repository_url: https://github.com/QuantEcon/lectures  # site addition
      path_to_docs: lectures
    intersphinx_disabled_reftypes: []  # site addition
    intersphinx_mapping:
      # site addition: this site maps itself
      intro:  # site addition
        - "https://intro.quantecon.org/"  # site addition
        - null  # site addition
      intermediate:
        - "https://python.quantecon.org/"
        - null
"""


def drift_repo(make_repo):
    """A promoted pool, and a site whose files are intro's, plus marked additions."""
    repo = make_repo(["intro"])
    repo.lecture("intro", "solow", lecture_text("Solow"))
    repo.lecture("intro", "intro", lecture_text("Intro"))
    repo.toc("intro", ["solow"])
    repo.mirror_file("intro", "_config.yml", UPSTREAM_CONFIG)
    repo.mirror_file("intro", "_static/qe-logo.png", b"\x89PNG logo")
    assert repo.promote("solow").returncode == 0
    site = repo.root / "sites" / "intro"
    mirror = repo.root / "mirror" / "intro" / "lectures"
    for rel in ("_toc.yml", "intro.md", "_static/qe-logo.png"):
        write(site / rel, (mirror / rel).read_bytes())
    write(site / "_config.yml", SITE_CONFIG)
    write(site / "site.yml", site_yml())
    return repo, site, mirror


def stale(res):
    return [line.strip() for line in res.stdout.splitlines() if line.strip().startswith("[site-stale]")]


def test_a_site_that_matches_its_series_but_for_marked_additions_is_clean(make_repo):
    repo, site, mirror = drift_repo(make_repo)
    toc = (site / "_toc.yml").read_text()
    write(site / "_toc.yml", toc + "  - file: extra  # site addition: a lecture the series lacks\n")

    res = repo.drift_check()

    assert res.returncode == 0, res.stdout + res.stderr
    assert stale(res) == []


def test_site_yml_is_the_sites_own_and_never_site_stale(make_repo):
    # The series has no site.yml, and the site's holds what only the build
    # reads, extra_packages among it.
    repo, site, mirror = drift_repo(make_repo)
    write(site / "site.yml", site_yml(extra_packages=["jax"]))

    res = repo.drift_check()

    assert res.returncode == 0, res.stdout + res.stderr
    assert stale(res) == []


def test_a_series_file_that_changed_upstream_is_site_stale(make_repo):
    repo, site, mirror = drift_repo(make_repo)
    write(mirror / "_config.yml", UPSTREAM_CONFIG.replace('"cache"', '"off"'))
    write(mirror / "intro.md", lecture_text("Intro, revised"))
    write(mirror / "_static/qe-logo.png", b"\x89PNG new logo")

    res = repo.drift_check()

    assert res.returncode == 1
    assert stale(res) == [
        "[site-stale] sites/intro/_config.yml no longer matches intro's lectures/_config.yml once the site's "
        "additions are removed",
        "[site-stale] sites/intro/_static/qe-logo.png no longer matches intro's lectures/_static/qe-logo.png",
        "[site-stale] sites/intro/intro.md no longer matches intro's lectures/intro.md",
    ]
    report = repo.drift_check("--print-issues").stdout
    assert "### drift(intro): sites/intro/_config.yml no longer matches the series" in report
    assert '-  execute_notebooks: "cache"\n+  execute_notebooks: "off"' in report
    assert "then put back the lines marked `# site addition`" in report


def test_a_toc_entry_added_upstream_is_site_stale(make_repo):
    repo, site, mirror = drift_repo(make_repo)
    repo.lecture("intro", "cobweb", lecture_text("Cobweb"))
    repo.toc("intro", ["solow", "cobweb"])

    res = repo.drift_check()

    assert stale(res) == [
        "[site-stale] sites/intro/_toc.yml no longer matches intro's lectures/_toc.yml once the site's additions "
        "are removed",
    ]
    report = repo.drift_check("--print-issues").stdout
    assert "+  - file: cobweb" in report


def test_a_file_the_series_removed_is_site_stale(make_repo):
    repo, site, mirror = drift_repo(make_repo)
    (mirror / "intro.md").unlink()

    res = repo.drift_check()

    assert stale(res) == ["[site-stale] sites/intro/intro.md: intro no longer has lectures/intro.md upstream"]


def test_a_folder_that_is_no_series_is_not_compared(make_repo):
    repo, site, mirror = drift_repo(make_repo)
    write(repo.root / "sites" / "reader" / "intro.md", "a course's own page")

    res = repo.drift_check()

    assert res.returncode == 0, res.stdout + res.stderr
