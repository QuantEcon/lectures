"""tools/affected-sites: which sites a change reaches (QuantEcon/project-monorepo#77)."""

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
KEYS = ["dp", "intro", "intermediate"]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def toc(root, *chapters):
    return "format: jb-book\nroot: " + root + "\nchapters:\n" + "".join(f"- file: {c}\n" for c in chapters)


@pytest.fixture
def repo(make_repo):
    """Three sites: dp lists `shared` and `dp_only`; intro lists `shared` and
    `intro_only`; intermediate lists `int_only` in a part. The ledger records
    one `_shared` asset used by `dp_only` and `int_only`."""
    r = make_repo(["intro", "intermediate", "dp"])
    write(r.root / "sites/dp/_toc.yml", toc("intro", "shared", "dp_only"))
    write(r.root / "sites/intro/_toc.yml", toc("intro", "shared", "intro_only"))
    write(r.root / "sites/intermediate/_toc.yml",
          "format: jb-book\nroot: intro\nparts:\n- caption: One\n  chapters:\n  - file: int_only\n")
    write(r.root / "sync/ledger.yml", yaml.safe_dump({
        "lectures/dp_only.md": {"canonical": "dp", "assets": ["_static/_shared/two/fig.png"]},
        "lectures/int_only.md": {"canonical": "intermediate", "assets": ["_static/_shared/two/fig.png"]},
        "lectures/shared.md": {"canonical": "intro"},
    }))
    return r


def sites(repo, *paths, base=None):
    args = (["--base", base] if base else []) + KEYS
    res = repo.run("affected-sites", *args, input="".join(p + "\n" for p in paths))
    assert res.returncode == 0, res.stderr
    return res.stdout.split()


@pytest.mark.parametrize("paths, expected", [
    # A lecture: every site that lists it, in the order given.
    (["lectures/shared.md"], ["dp", "intro"]),
    (["lectures/int_only.md"], ["intermediate"]),
    (["lectures/listed_nowhere.md"], []),
    # A lecture's own assets, as its page.
    (["lectures/_static/intro_only/fig.png"], ["intro"]),
    # A shared asset: the sites of the lectures the ledger says use it, or
    # every site when it records none.
    (["lectures/_static/_shared/two/fig.png"], ["dp", "intermediate"]),
    (["lectures/_static/_shared/unrecorded.png"], KEYS),
    # The bibliography, and any other pool file: every site.
    (["lectures/_static/quant-econ.bib"], KEYS),
    (["lectures/odd-file.txt"], KEYS),
    # A site's own files: that site; sites/README.md, or a site not given: none.
    (["sites/intro/_config.yml"], ["intro"]),
    (["sites/README.md"], []),
    (["sites/jax/_toc.yml"], []),
    # Every other input of the build: every site.
    (["tools/stage-site"], KEYS),
    (["_base/environment-update.yml"], KEYS),
    ([".github/workflows/site-build.yml"], KEYS),
    (["sync/state.yml"], KEYS),
    # Anything else: none.
    (["README.md", "tools/tests/test_sites.py", ".github/workflows/tests.yml", "sync/ledger.yml"], []),
    ([], []),
    # Several paths: the union, in the order given.
    (["lectures/int_only.md", "sites/dp/intro.md"], ["dp", "intermediate"]),
])
def test_affected_sites_places_each_path(repo, paths, expected):
    assert sites(repo, *paths) == expected


def test_a_lecture_dropped_from_a_contents_list_still_builds_the_site_that_listed_it(repo):
    git = lambda *a: subprocess.run(["git", "-C", str(repo.root), *a], capture_output=True, text=True, check=True)
    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@example.org", "add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-qm", "base")
    base = git("rev-parse", "HEAD").stdout.strip()
    # The change deletes intro_only and takes it out of intro's contents.
    write(repo.root / "sites/intro/_toc.yml", toc("intro", "shared"))

    assert sites(repo, "lectures/intro_only.md") == []
    assert sites(repo, "lectures/intro_only.md", base=base) == ["intro"]


def test_affected_sites_refuses_a_key_with_no_site(repo):
    res = repo.run("affected-sites", "dp", "nosuch", input="lectures/shared.md\n")

    assert res.returncode == 2
    assert "no sites/<key>/_toc.yml for nosuch" in res.stderr


def test_build_inputs_are_the_workflows_path_filter_outside_the_pool_and_the_sites():
    loader = importlib.machinery.SourceFileLoader("affected_sites", str(ROOT / "tools" / "affected-sites"))
    spec = importlib.util.spec_from_loader("affected_sites", loader)
    tool = importlib.util.module_from_spec(spec)
    loader.exec_module(tool)
    workflow = yaml.safe_load((ROOT / ".github/workflows/site-build.yml").read_text(encoding="utf-8"))
    on = workflow.get("on", workflow.get(True))
    for event in ("push", "pull_request"):
        paths = [p for p in on[event]["paths"] if not p.startswith(("lectures/", "sites/"))]
        assert sorted(paths) == sorted(tool.BUILD_INPUTS), event
