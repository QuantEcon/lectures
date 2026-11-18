"""tools/pool-check: the one environment, _base/environment-update.yml,
lists every package a pool lecture installs (QuantEcon/project-monorepo#77)."""

import pytest

from conftest import lecture_text

ENVIRONMENT = """\
channels:
  - defaults
dependencies:
  - pip
  - plotly::plotly-orca==1.3.1
  - pip:
    - foo==1.1.0rc1
    - jax==0.11.0
    - plotly==6.7.0
    - prettytable==3.17.0
    - quantecon==0.13.1
    - quantecon-book-networks==1.6
"""
WHERE = "_base/environment-update.yml"


def cell(*lines, tags=None, fence="```"):
    head = [f"{fence}{{code-cell}} ipython3"] + ([f":tags: [{tags}]"] if tags else [])
    return "\n".join(head + list(lines) + [fence])


def write_lecture(repo, slug, *blocks):
    path = repo.pool(f"{slug}.md")
    path.write_text(lecture_text(slug, body="\n\n".join(blocks)), encoding="utf-8")
    return path


def write_environment(repo, text=ENVIRONMENT):
    path = repo.root / "_base" / "environment-update.yml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def problems(res):
    return [line.strip() for line in res.stdout.splitlines() if line.startswith("  [")]


def line_of(path, text):
    return path.read_text(encoding="utf-8").splitlines().index(text) + 1


def unlisted(path, text, name="interpolation"):
    return (
        f"[install-listed] lectures/{path.stem}.md:{line_of(path, text)} installs {name}, which {WHERE} does not "
        "list: pin it there, so every site builds with one version of it"
    )


def test_a_pool_whose_installs_are_all_pinned_is_clean(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo)
    write_lecture(repo, "kesten", cell("!pip install --upgrade quantecon jax"))
    write_lecture(repo, "networks", cell("!pip install quantecon_book_networks==1.6", tags="hide-output"))
    write_lecture(repo, "speed", cell('%pip install -q quantecon "jax==0.11.0" 2>&1 > /dev/null'))
    write_lecture(repo, "auction", cell('!pip install "prettytable<3.18"'))
    write_lecture(repo, "plots", cell("!conda install -y -c conda-forge plotly plotly-orca"))
    write_lecture(repo, "solow", "No install here.")

    res = repo.pool_check()

    assert res.returncode == 0, res.stdout
    assert (
        f"info: {WHERE} lists 7 package(s); the pool's lectures install 6 of them, in 5 lecture(s)" in res.stdout
    )
    assert "clean:" in res.stdout


def test_a_package_the_environment_does_not_list_is_reported_at_its_line(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo)
    path = write_lecture(repo, "odu", cell("import numpy as np", "!pip install quantecon interpolation"))

    res = repo.pool_check()

    assert res.returncode == 1
    assert problems(res) == [unlisted(path, "!pip install quantecon interpolation")]
    # The count is of the listed packages the lectures install.
    assert f"info: {WHERE} lists 7 package(s); the pool's lectures install 1 of them, in 1 lecture(s)" in res.stdout


@pytest.mark.parametrize("line", [
    "!pip install quantecon ; pip install interpolation",
    "!pip install quantecon&&pip install interpolation",
    "!echo start | tee log && python -m pip install interpolation > /dev/null 2>&1",
    "!{sys.executable} -m pip install interpolation",
    "!python3.13 -m pip -q install interpolation",
    "!uv pip install interpolation",
    "!!pip install interpolation",
    "%pip install --root-user-action ignore --index-url https://example.org/simple interpolation",
    "!mamba install -c conda-forge -y interpolation",
])
def test_every_way_a_shell_line_installs_is_read(make_repo, line):
    repo = make_repo(["intro"])
    write_environment(repo)
    path = write_lecture(repo, "odu", cell(line))

    res = repo.pool_check()

    assert res.returncode == 1
    assert problems(res) == [unlisted(path, line)]


def test_a_bash_cell_s_lines_are_shell_lines(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo)
    path = write_lecture(repo, "odu", cell("%%bash", "pip install interpolation"))

    res = repo.pool_check()

    assert problems(res) == [unlisted(path, "pip install interpolation")]


def test_names_compare_as_pep_503_has_them_across_the_pip_and_conda_lists(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo)
    write_lecture(repo, "a", cell("!pip install Quantecon-Book.Networks QuantEcon"))
    write_lecture(repo, "b", cell("!conda install plotly", "!pip install plotly_orca"))

    res = repo.pool_check()

    assert res.returncode == 0, res.stdout


def test_a_lecture_s_own_version_limit_must_allow_the_pinned_version(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo, ENVIRONMENT.replace("prettytable==3.17.0", "prettytable==3.19.0"))
    limited = '!pip install "prettytable<3.18"'
    path = write_lecture(repo, "auction", cell(limited), cell("!pip install jax==0.12.0"))

    res = repo.pool_check()

    assert res.returncode == 1
    assert problems(res) == [
        f"[install-listed] lectures/auction.md:{line_of(path, limited)} asks for prettytable<3.18, but {WHERE} "
        "pins prettytable 3.19.0",
        f"[install-listed] lectures/auction.md:{line_of(path, '!pip install jax==0.12.0')} asks for jax==0.12.0, "
        f"but {WHERE} pins jax 0.11.0",
    ]


def test_a_pinned_pre_release_satisfies_a_limit_as_pip_judges_an_installed_one(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo)
    write_lecture(repo, "a", cell('!pip install "foo>=1.0"'))

    res = repo.pool_check()

    assert res.returncode == 0, res.stdout


def test_only_the_code_cells_a_notebook_holds_are_read(make_repo):
    # Prose, a code block, a commented line and a code cell inside another
    # directive (backtick or colon fenced) are not notebook cells.
    repo = make_repo(["intro"])
    write_environment(repo)
    write_lecture(
        repo,
        "getting_started",
        "To install it yourself, run `!pip install interpolation`.",
        "```{code-block} ipython3\n!conda install -c conda-forge interpolation\n```",
        "````{note}\n" + cell("!pip install cvxpy") + "\n````",
        ":::{note}\n" + cell("!pip install highspy") + "\n:::",
        cell("# !pip install highspy", "!pip install quantecon  # and nothing else"),
    )

    res = repo.pool_check()

    assert res.returncode == 0, res.stdout


@pytest.mark.parametrize("before, cell_fence, inner", [
    # A line that opens with inline code is not a fence, so it hides nothing.
    ("```pip``` is the installer.", "```", None),
    # A shorter fence, or one of the other character, does not close a cell.
    ("", "````", "```"),
    ("", "~~~", "```"),
])
def test_a_cell_runs_to_its_own_closing_fence(make_repo, before, cell_fence, inner):
    repo = make_repo(["intro"])
    write_environment(repo)
    lines = (["print('a fence')", inner] if inner else []) + ["!pip install interpolation"]
    path = write_lecture(repo, "odu", before, cell(*lines, fence=cell_fence))

    res = repo.pool_check()

    assert problems(res) == [unlisted(path, "!pip install interpolation")]


def test_an_install_line_the_check_cannot_read_is_reported(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo)
    lines = (
        "!pip install -r requirements.txt",
        "!pip install https://example.org/pkg-1.0.tar.gz",
        "!pip install quantecon@https://example.org/quantecon-0.13.1.tar.gz",
        "!pip install --requirement=more.txt quantecon",
        "!pip install 'quantecon",
    )
    path = write_lecture(repo, "odd", cell(*lines))

    res = repo.pool_check()

    assert res.returncode == 1
    at = {text: f"[install-listed] lectures/odd.md:{line_of(path, text)}: `{text}` installs what this check cannot read"
          for text in lines}
    assert problems(res) == [
        f"{at[lines[0]]} (`-r`): name each package on the line",
        f"{at[lines[1]]} (`https://example.org/pkg-1.0.tar.gz`): name the package, not a file or an address",
        f"{at[lines[2]]} (`quantecon@https://example.org/quantecon-0.13.1.tar.gz`): name the package, not a file "
        "or an address",
        f"{at[lines[3]]} (`--requirement`): name each package on the line",
        f"{at[lines[4]]} (No closing quotation): write it as one plain line",
    ]


def test_every_entry_in_the_environment_is_pinned_to_one_version_once(make_repo):
    repo = make_repo(["intro"])
    loose = (
        ENVIRONMENT.replace("quantecon==0.13.1", "quantecon")
        .replace("plotly-orca==1.3.1", "plotly-orca=1.3.1")
        .replace("prettytable==3.17.0", "prettytable>=3.17")
        .replace("plotly==6.7.0", "plotly==6.*")
        .replace("jax==0.11.0", "jax==0.11.0; python_version < '3.14'")
        + "    - Quantecon_Book.Networks==1.6\n"
    )
    write_environment(repo, loose)
    write_lecture(repo, "kalman", cell("!pip install quantecon"))

    res = repo.pool_check()

    assert res.returncode == 1
    # An entry listed without a pin is reported once, not again at every
    # lecture that installs it.
    pip = f"is not a package pinned to one version (`name==version`)"
    assert problems(res) == [
        f"[environment] {WHERE}: conda entry `plotly::plotly-orca=1.3.1` is not a package pinned to one version "
        "(`name==version`; a single `=` is a prefix to conda)",
        f"[environment] {WHERE}: pip entry `jax==0.11.0; python_version < '3.14'` {pip}",
        f"[environment] {WHERE}: pip entry `plotly==6.*` {pip}",
        f"[environment] {WHERE}: pip entry `prettytable>=3.17` {pip}",
        f"[environment] {WHERE}: pip entry `quantecon` {pip}",
        f"[environment] {WHERE} lists quantecon-book-networks more than once (`Quantecon_Book.Networks==1.6`)",
    ]


def test_the_environment_is_a_conda_environment_file(make_repo):
    repo = make_repo(["intro"])
    write_environment(repo, "- quantecon==0.13.1\n")
    write_lecture(repo, "kalman", cell("!pip install quantecon"))

    res = repo.pool_check()

    assert res.returncode == 1
    assert problems(res)[0] == (
        f"[environment] {WHERE} is not a Conda environment file: it has no `dependencies` list"
    )


def test_lectures_that_install_need_the_environment_and_a_pool_that_installs_nothing_does_not(make_repo):
    repo = make_repo(["intro"])
    write_lecture(repo, "solow", "No install here.")

    assert repo.pool_check().returncode == 0

    write_lecture(repo, "kalman", cell("!pip install quantecon"))
    res = repo.pool_check()

    assert res.returncode == 1
    assert problems(res) == [
        f"[install-listed] 1 pool lecture(s) install packages, but there is no {WHERE} to pin them in",
    ]
