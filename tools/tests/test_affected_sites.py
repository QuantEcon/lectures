"""tools/affected-sites: which sites a change reaches (QuantEcon/project-monorepo#77)."""

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
KEYS = ["dp", "intro", "intermediate"]
EMAIL = ["-c", "user.name=t", "-c", "user.email=t@example.org"]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def toc(root, *chapters):
    return "format: jb-book\nroot: " + root + "\nchapters:\n" + "".join(f"- file: {c}\n" for c in chapters)


@pytest.fixture
def repo(make_repo):
    """Three sites: dp lists `shared` and `dp_only`; intro lists `shared` and
    `intro_only`; intermediate lists `int_only` in a part, with `int_nested`
    a section under it. The ledger records one `_shared` asset used by
    `dp_only` and `int_only`. dp builds in the series environment (its
    site.yml leaves it to the default), the others in base."""
    r = make_repo(["intro", "intermediate", "dp"])
    write(r.root / "sites/dp/_toc.yml", toc("intro", "shared", "dp_only"))
    write(r.root / "sites/intro/_toc.yml", toc("intro", "shared", "intro_only"))
    write(r.root / "sites/intermediate/_toc.yml",
          "format: jb-book\nroot: intro\nparts:\n- caption: One\n  chapters:\n  - file: int_only\n"
          "    sections:\n    - file: int_nested\n")
    write(r.root / "sites/dp/site.yml", "runner: ubuntu-latest\n")
    write(r.root / "sites/intro/site.yml", "runner: ubuntu-latest\nenvironment: base\n")
    write(r.root / "sites/intermediate/site.yml", "runner: gpu\nenvironment: base\n")
    for slug in ("intro", "shared", "dp_only", "intro_only", "int_only", "int_nested"):
        write(r.root / f"lectures/{slug}.md", f"# {slug}\n")
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


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo.root), *args], capture_output=True, text=True, check=True)


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, *EMAIL, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def changed_sites(repo, base):
    """The sites the workflow's own command reaches: git's NUL-separated
    diff of the base and the working tree, with no rename detection."""
    head = commit(repo, "head")
    diff = subprocess.run(["git", "-C", str(repo.root), "diff", "--no-renames", "--name-only", "-z", base, head],
                          capture_output=True, check=True).stdout.decode("utf-8")
    res = repo.run("affected-sites", "-z", "--base", base, *KEYS, input=diff)
    assert res.returncode == 0, res.stderr
    return res.stdout.split()


@pytest.fixture
def history(repo):
    git(repo, "init", "-q")
    return repo, commit(repo, "base")


@pytest.mark.parametrize("paths, expected", [
    # A lecture: every site that lists it, in the order given.
    (["lectures/shared.md"], ["dp", "intro"]),
    (["lectures/int_only.md"], ["intermediate"]),
    (["lectures/listed_nowhere.md"], []),
    # A section nested under a chapter, inside a part.
    (["lectures/int_nested.md"], ["intermediate"]),
    # A lecture's own assets, as its page; a _static folder that is no
    # lecture's: every site.
    (["lectures/_static/intro_only/fig.png"], ["intro"]),
    (["lectures/_static/lecture_specific/troubleshooting/launch.png"], KEYS),
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
    (["sync/manifest.yml"], KEYS),
    # tools/sync and the pins it reads: the sites in the series environment.
    (["sync/state.yml"], ["dp"]),
    (["tools/sync"], ["dp"]),
    # Anything else: none.
    (["README.md", "tools/tests/test_sites.py", ".github/workflows/tests.yml", "sync/ledger.yml"], []),
    ([], []),
    # Several paths: the union, in the order given.
    (["lectures/int_only.md", "sites/dp/intro.md"], ["dp", "intermediate"]),
])
def test_affected_sites_places_each_path(repo, paths, expected):
    assert sites(repo, *paths) == expected


def test_a_lecture_dropped_from_a_contents_list_still_builds_the_site_that_listed_it(history):
    repo, base = history
    # The change deletes intro_only and takes it out of intro's contents.
    (repo.root / "lectures/intro_only.md").unlink()
    write(repo.root / "sites/intro/_toc.yml", toc("intro", "shared"))

    assert sites(repo, "lectures/intro_only.md") == []
    assert sites(repo, "lectures/intro_only.md", base=base) == ["intro"]


def test_a_shared_asset_dropped_from_the_ledger_still_builds_the_sites_of_its_old_users(history):
    repo, base = history
    # The change stops dp_only using the asset, and the ledger with it.
    write(repo.root / "sync/ledger.yml", yaml.safe_dump({
        "lectures/dp_only.md": {"canonical": "dp"},
        "lectures/int_only.md": {"canonical": "intermediate", "assets": ["_static/_shared/two/fig.png"]},
    }))

    assert sites(repo, "lectures/_static/_shared/two/fig.png") == ["intermediate"]
    assert sites(repo, "lectures/_static/_shared/two/fig.png", base=base) == ["dp", "intermediate"]


def test_a_pin_refresh_still_builds_a_site_the_change_moves_out_of_the_series_environment(history):
    repo, base = history
    write(repo.root / "sites/dp/site.yml", "runner: ubuntu-latest\nenvironment: base\n")

    assert sites(repo, "sync/state.yml") == []
    assert sites(repo, "sync/state.yml", base=base) == ["dp"]


def test_a_site_with_no_site_yml_counts_as_series(repo):
    (repo.root / "sites/intro/site.yml").unlink()

    assert sites(repo, "sync/state.yml") == ["dp", "intro"]


def test_a_renamed_lecture_builds_the_sites_that_list_its_old_name(history):
    repo, base = history
    # A rename with no contents-list change: git, detecting the rename,
    # would print only the new name, which no site lists.
    git(repo, "mv", "lectures/intro_only.md", "lectures/intro_only_v2.md")

    assert changed_sites(repo, base) == ["intro"]


def test_an_asset_moved_out_of_its_lectures_folder_builds_that_lectures_sites(history):
    repo, base = history
    write(repo.root / "lectures/_static/int_only/fig.png", "png")
    base = commit(repo, "the asset")
    (repo.root / "lectures/_static/dp_only").mkdir()
    git(repo, "mv", "lectures/_static/int_only/fig.png", "lectures/_static/dp_only/fig.png")

    assert changed_sites(repo, base) == ["dp", "intermediate"]


def test_a_name_git_would_quote_reaches_its_site(history):
    repo, base = history
    write(repo.root / "lectures/_static/intro_only/caf\u00e9.png", "png")

    assert changed_sites(repo, base) == ["intro"]


def test_affected_sites_refuses_a_base_that_is_no_commit(history):
    repo, _ = history
    res = repo.run("affected-sites", "--base", "0123456789abcdef0123456789abcdef01234567", *KEYS, input="lectures/shared.md\n")

    assert res.returncode == 2
    assert "is no commit in this repository" in res.stderr


def test_affected_sites_refuses_a_contents_list_it_cannot_parse(repo):
    write(repo.root / "sites/intro/_toc.yml", "root: [unclosed\n")
    res = repo.run("affected-sites", *KEYS, input="lectures/shared.md\n")

    assert res.returncode == 2
    assert "cannot be parsed" in res.stderr
    assert "Traceback" not in res.stderr


def test_affected_sites_refuses_a_key_with_no_site(repo):
    res = repo.run("affected-sites", "dp", "nosuch", input="lectures/shared.md\n")

    assert res.returncode == 2
    assert "no sites/<key>/_toc.yml for nosuch" in res.stderr


def workflow():
    return yaml.safe_load((ROOT / ".github/workflows/site-build.yml").read_text(encoding="utf-8"))


def choose_step():
    steps = workflow()["jobs"]["sites"]["steps"]
    return next(s for s in steps if s.get("name") == "Choose the sites the change reaches")


def test_build_inputs_are_the_workflows_path_filter_outside_the_pool_and_the_sites():
    loader = importlib.machinery.SourceFileLoader("affected_sites", str(ROOT / "tools" / "affected-sites"))
    spec = importlib.util.spec_from_loader("affected_sites", loader)
    tool = importlib.util.module_from_spec(spec)
    loader.exec_module(tool)
    on = workflow().get("on", workflow().get(True))
    for event in ("push", "pull_request"):
        paths = [p for p in on[event]["paths"] if not p.startswith(("lectures/", "sites/"))]
        assert sorted(paths) == sorted(tool.BUILD_INPUTS + tool.SERIES_INPUTS), event


def test_the_workflow_lists_renamed_paths_by_both_names_and_separates_them_with_nul():
    run = choose_step()["run"]

    assert 'git diff --no-renames --name-only -z "$base" HEAD' in run
    assert "tools/affected-sites -z --base" in run


def test_the_workflow_builds_every_site_for_a_change_to_the_rule_itself():
    run = choose_step()["run"]

    assert "grep -qzxF -e tools/affected-sites -e .github/workflows/site-build.yml" in run


def test_a_push_is_compared_with_the_last_build_on_main_that_succeeded():
    steps = workflow()["jobs"]["sites"]["steps"]
    last = next(s for s in steps if s.get("id") == "last")

    assert last["if"] == "${{ github.event_name == 'push' }}"
    assert "branch=main&status=success" in last["run"]
    assert 'select(.event == "push" or .event == "schedule" or .event == "workflow_dispatch")' in last["run"]
    assert steps.index(last) < steps.index(choose_step())
    assert choose_step()["env"]["LAST_GOOD"] == "${{ steps.last.outputs.sha }}"
    assert "github.event.before" not in str(choose_step())
    assert workflow()["jobs"]["sites"]["permissions"] == {"contents": "read", "actions": "read"}


def test_only_the_query_step_holds_the_token():
    for step in workflow()["jobs"]["sites"]["steps"]:
        if "GH_TOKEN" in (step.get("env") or {}):
            assert step.get("id") == "last", step.get("name")


def test_a_call_from_publish_builds_the_sites_it_names_and_grants_what_the_called_jobs_ask():
    step = choose_step()
    assert step["env"]["CALLED_SITES"] == "${{ inputs.sites }}"
    assert "keys=$CALLED_SITES" in step["run"]
    # A called workflow's jobs get no more than the calling job grants, and
    # GitHub refuses the call if one asks for more.
    publish = yaml.safe_load((ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8"))
    granted = publish["jobs"]["build"]["permissions"]
    for name, job in workflow()["jobs"].items():
        for scope, level in (job.get("permissions") or {}).items():
            assert granted.get(scope) in (level, "write"), (name, scope)
