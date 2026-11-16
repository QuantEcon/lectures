"""sites/<key>/: tools/pool-check's site rules and tools/stage-site
(QuantEcon/project-monorepo#21)."""

import yaml

from conftest import lecture_text

URL = "https://intro.quantecon.org/"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    return path


def config(key="intro", url=URL, mapping=None, disabled=True, **top):
    """A site's _config.yml, as the series write it: branding, the address
    and the cross-reference settings."""
    sphinx = {
        "html_favicon": "_static/lectures-favicon.ico",
        "html_theme_options": {"dark_logo": "quantecon-logo-transparent.png"},
        "intersphinx_mapping": {key: [url, None]} if mapping is None else mapping,
    }
    if disabled:
        sphinx["intersphinx_disabled_reftypes"] = []
    data = {"title": key, "logo": "_static/qe-logo.png", "html": {"baseurl": url}, "sphinx": {"config": sphinx}}
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
        "publishes, url)",
        "[site-yml] sites/intro/site.yml: type 'course' is not one of series",
        "[site-yml] sites/intro/site.yml: runner 'macos-latest' is not one of ubuntu-latest, g4dn.2xlarge",
        "[site-yml] sites/intro/site.yml: cell_timeout '600' is not a whole number of seconds above 0",
        "[site-yml] sites/intro/site.yml: publishes ['pdf', 'epub'] is not a list of html, pdf, notebooks, each "
        "at most once, with html",
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


def test_stage_site_copies_a_site_in_refuses_a_second_and_cleans_up(make_repo):
    repo = pool_repo(make_repo, series=("intro", "dp"), consumers=("dp",))
    make_site(repo, key="intro")
    write(repo.root / "sites" / "intro" / "_static" / "lecture_specific" / "troubleshooting" / "launch.png", "png")
    make_site(repo, key="dp", cfg=config("dp", mapping={"intro": [URL, None]}))
    assert repo.pool_check().returncode == 0
    before = sorted(p.relative_to(repo.root).as_posix() for p in repo.pool("").rglob("*"))

    res = repo.stage_site("intro")

    assert res.returncode == 0, res.stdout + res.stderr
    assert "stage-site intro: 5 file(s) copied into lectures/, 0 already there" in res.stdout
    assert repo.pool("intro.md").read_text() == (repo.root / "sites/intro/intro.md").read_text()
    assert repo.pool("_static/lecture_specific/troubleshooting/launch.png").read_text() == "png"
    assert not repo.pool("_config.yml").exists() and not repo.pool("site.yml").exists()
    assert "1 file(s) copied" not in repo.stage_site("intro").stdout  # again: nothing new

    res = repo.stage_site("dp")  # another site's intro.md is still staged
    assert res.returncode == 1
    assert "[differs] lectures/intro.md is already there with other bytes" in res.stdout
    assert "refused, nothing copied" in res.stdout
    assert repo.pool("intro.md").read_text() == (repo.root / "sites/intro/intro.md").read_text()

    write(repo.pool("_static/qe-logo.png"), "edited after staging")
    res = repo.stage_site("--clean", "intro")
    assert res.returncode == 0
    assert "kept lectures/_static/qe-logo.png: its bytes are not sites/intro's" in res.stdout
    assert "4 file(s) removed" in res.stdout
    repo.pool("_static/qe-logo.png").unlink()
    after = sorted(p.relative_to(repo.root).as_posix() for p in repo.pool("").rglob("*"))
    assert after == before  # the empty lecture_specific/ folders went too
    assert repo.stage_site("dp").returncode == 0


def test_stage_site_refuses_an_unknown_site(make_repo):
    repo = pool_repo(make_repo)
    make_site(repo)

    res = repo.stage_site("jax")

    assert res.returncode == 1
    assert "there is no site sites/jax/ (sites: intro)" in res.stderr
