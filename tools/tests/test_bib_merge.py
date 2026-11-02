"""tools/bib-merge: one pool bibliography from the series' own files."""

from __future__ import annotations

import re

import pytest

SERIES = ["intro", "intermediate"]


def entry(key, fields, etype="article"):
    body = ",\n".join(f"  {name} = {value}" for name, value in fields)
    return f"@{etype}{{{key},\n{body}\n}}\n"


SMITH = [("author", "{Smith, Jane}"), ("title", "{A Title}"), ("journal", "{Econometrica}"), ("year", "{2000}")]


def repo_with(make_repo, intro, intermediate, rulings=None):
    repo = make_repo(SERIES)
    repo.bib("intro", intro)
    repo.bib("intermediate", intermediate)
    repo.bib_rulings(SERIES, rulings)
    return repo


def merged(repo):
    return repo.pool("_static/quant-econ.bib").read_text(encoding="utf-8")


def body(repo):
    """The merged file without its header, which records the input digests."""
    return "".join(line for line in merged(repo).splitlines(keepends=True) if not line.startswith("%"))


def seals(repo):
    """{key: {series: digest}} from --propose."""
    out, key = {}, None
    for line in repo.bib_merge("--propose").stdout.splitlines():
        m = re.match(r"^  (\S+):$", line)
        if m:
            key = m.group(1)
            continue
        m = re.match(r"^      (\S+): ([0-9a-f]{16})$", line)
        if m and key:
            out.setdefault(key, {})[m.group(1)] = m.group(2)
    return out


# --------------------------------------------------------------------------- #
# Merging and normalising                                                      #
# --------------------------------------------------------------------------- #
def test_identical_copies_merge_once_and_the_check_is_clean(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH))
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout + res.stderr
    assert body(repo).count("@article{Smith2000,") == 1
    assert repo.bib_merge().returncode == 0


def test_normalising_applies_the_mechanical_rules_and_nothing_else(make_repo):
    raw = (
        "@Article{Lee1999,\n"
        "  Author = {Lee, Kim and {{World Bank}}},\n"
        "  title = {A {Markov}\n      Model of \\'{E}conomies},\n"
        "  journal = \"Journal of Things\",\n"
        "  year = 1999,\n"
        "  month = may,\n"
        "  pages = {1 - 68},\n"
        "  doi = {https://doi.org/10.1000/xyz},\n"
        "  abstract = {Never shown.},\n"
        "  issn = {1234},\n"
        "  note = {}\n"
        "}\n"
        "@book{Ray2001,\n  author = {Ray, Al},\n  title = {T},\n  publisher = {P},\n  pages = {225\u2013287},\n  year = {2001}\n}\n"
    )
    repo = repo_with(make_repo, raw, "")
    assert repo.bib_merge("--write").returncode == 0
    assert body(repo) == (
        "\n@article{Lee1999,\n"
        "  author  = {Lee, Kim and {{World Bank}}},\n"
        "  title   = {A {Markov} Model of \\'{E}conomies},\n"
        "  journal = {Journal of Things},\n"
        "  pages   = {1--68},\n"
        "  year    = {1999},\n"
        "  doi     = {10.1000/xyz}\n"
        "}\n"
        "\n@book{Ray2001,\n"
        "  author    = {Ray, Al},\n"
        "  title     = {T},\n"
        "  pages     = {225--287},\n"
        "  publisher = {P},\n"
        "  year      = {2001}\n"
        "}\n"
    )


def test_the_output_does_not_depend_on_locale_or_hash_seed(make_repo):
    keys = ["beta", "Alpha", "gamma2", "Gamma1", "delta:2020/x+y"]
    text = "".join(entry(k, SMITH) for k in keys)
    repo = repo_with(make_repo, text, "")
    assert repo.bib_merge("--write", env={"LC_ALL": "C", "PYTHONHASHSEED": "1"}).returncode == 0
    first = merged(repo)
    assert repo.bib_merge("--write", env={"LC_ALL": "en_US.UTF-8", "PYTHONHASHSEED": "987"}).returncode == 0
    assert merged(repo) == first
    order = re.findall(r"^@article\{([^,]+),", first, flags=re.M)
    assert order == ["Alpha", "beta", "delta:2020/x+y", "Gamma1", "gamma2"]


# --------------------------------------------------------------------------- #
# Conflicts and rulings                                                        #
# --------------------------------------------------------------------------- #
def test_a_conflict_without_a_ruling_is_refused_and_keeps_the_committed_entry(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH))
    assert repo.bib_merge("--write").returncode == 0
    before = body(repo)
    repo.bib("intermediate", entry("Smith2000", SMITH[:1] + [("title", "{Another Title}")] + SMITH[2:]))
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "[refused] Smith2000: held by intro, intermediate with differing copies" in res.stdout
    assert "(the committed entry is kept)" in res.stdout
    assert body(repo) == before


def test_a_ruling_takes_a_copy_and_sets_drops_and_retypes(make_repo):
    intro = entry("Smith2000", SMITH + [("volume", "{3}")])
    intermediate = entry("Smith2000", SMITH[:1] + [("title", "{A Better Title}")] + SMITH[2:] + [("number", "{2}")])
    repo = repo_with(make_repo, intro, intermediate)
    stub = seals(repo)["Smith2000"]
    ruling = {"take": "intermediate", "set": {"publisher": "Elsevier"}, "drop": ["number"], "type": "book", "because": "test", "seal": stub}
    repo.bib_rulings(SERIES, {"Smith2000": ruling})
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout
    assert body(repo) == (
        "\n@book{Smith2000,\n"
        "  author    = {Smith, Jane},\n"
        "  title     = {A Better Title},\n"
        "  journal   = {Econometrica},\n"
        "  publisher = {Elsevier},\n"
        "  year      = {2000}\n"
        "}\n"
    )


def test_a_seal_holds_through_cosmetic_edits_and_reopens_on_a_real_one(make_repo):
    intro = entry("Smith2000", SMITH)
    intermediate = entry("Smith2000", SMITH + [("doi", "{10.1/abc}")])
    repo = repo_with(make_repo, intro, intermediate)
    ruling = {"take": "intermediate", "because": "more fields", "seal": seals(repo)["Smith2000"]}
    repo.bib_rulings(SERIES, {"Smith2000": ruling})
    assert repo.bib_merge("--write").returncode == 0

    # Re-indented and re-ordered upstream: the series file moved, the copy did not.
    repo.bib("intro", "@article{Smith2000,\n    year={2000},\n  author =   {Smith,   Jane},\n title={A Title}, journal={Econometrica}}\n")
    res = repo.bib_merge()
    assert res.returncode == 1, res.stdout
    assert "[refresh]" in res.stdout and "[refused]" not in res.stdout
    assert repo.bib_merge("--write").returncode == 0

    # A copy that catches up with the ruled result holds too.
    repo.bib("intro", intermediate)
    assert repo.bib_merge("--write").returncode == 0

    # A real edit reopens the ruling.
    repo.bib("intro", entry("Smith2000", SMITH[:3] + [("year", "{2001}")]))
    res = repo.bib_merge()
    assert res.returncode == 2
    assert "[refused] Smith2000: reopened: the copy in intro changed since the ruling" in res.stdout


def test_a_ruling_whose_copy_is_gone_is_refused(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH + [("doi", "{10.1/abc}")]))
    ruling = {"take": "intermediate", "because": "test", "seal": seals(repo)["Smith2000"]}
    repo.bib_rulings(SERIES, {"Smith2000": ruling})
    repo.bib("intermediate", "")
    res = repo.bib_merge()
    assert res.returncode == 2
    assert "its ruling takes `intermediate`, which no longer holds it" in res.stdout


def test_propose_seals_every_held_copy(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH + [("doi", "{10.1/abc}")]))
    out = repo.bib_merge("--propose").stdout
    assert "  Smith2000:\n    take: intermediate    # its fields include every other copy's" in out
    assert set(seals(repo)["Smith2000"]) == {"intro", "intermediate"}


# --------------------------------------------------------------------------- #
# What it refuses, and what it must read                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text, message",
    [
        (entry("Smith2000", SMITH) + entry("Smith2000", SMITH), "Duplicate"),
        ("@article{Smith2000,\n  title = {A},\n  title = {B}\n}\n", "Duplicate"),
        ("@string{jpe = {Journal of Political Economy}}\n" + entry("Smith2000", SMITH), "@string"),
        (entry("Smith2000", SMITH[:2] + [("journal", "jpe")]), "field `journal` is the bare macro 'jpe'"),
        (entry("Smith2000", SMITH[:2] + [("journal", '{Journal of} # " Things"')]), "field `journal` is a concatenation"),
        ("@article{Smith2000,\n  title = {unbalanced\n}\n", "cannot be read exactly"),
    ],
)
def test_input_it_cannot_read_exactly_is_refused_and_nothing_is_written(make_repo, text, message):
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    ours = [line for line in res.stderr.splitlines() if line.startswith("bib-merge: intro")]
    assert ours and message in ours[0], res.stderr
    assert not repo.pool("_static/quant-econ.bib").exists()


def test_unusual_but_valid_input_survives(make_repo):
    text = (
        "@online{site2020,\n  title = {A Site},\n  url = {https://example.org/a%20b},\n  year = {2020}\n}\n"
        "@misc{bare,\n}\n"
        '@article{quote2001,\n  title = "The {"}Quote{"} Paper",\n  journal = {J},\n  year = {2001}\n}\n'
        "@article{odd:key/2002+x,\n  title = {Braces \\{inside\\} and % # @ =},\n  journal = {J},\n  year = {2002}\n}\n"
    )
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout + res.stderr
    out = merged(repo)
    assert "@online{site2020," in out and "@misc{bare," in out
    assert 'title   = {The {"}Quote{"} Paper}' in out
    assert "@article{odd:key/2002+x," in out


# --------------------------------------------------------------------------- #
# The committed file                                                           #
# --------------------------------------------------------------------------- #
def test_the_check_tells_a_refresh_from_a_violation(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "")
    res = repo.bib_merge()
    assert res.returncode == 2 and "is missing" in res.stdout
    assert repo.bib_merge("--write").returncode == 0
    assert repo.bib_merge().returncode == 0

    path = repo.pool("_static/quant-econ.bib")
    clean = path.read_text(encoding="utf-8")
    path.write_text(clean.replace("{A Title}", "{A Title Fixed in the Pool}"), encoding="utf-8")
    res = repo.bib_merge()
    assert res.returncode == 2 and "[violation]" in res.stdout
    path.write_text(clean, encoding="utf-8")

    repo.bib("intermediate", entry("Jones2001", SMITH))
    res = repo.bib_merge()
    assert res.returncode == 1 and "[refresh]" in res.stdout
    assert repo.bib_merge("--write").returncode == 0

    # A ruling changed in the repository must be regenerated in the same change.
    repo.bib("intermediate", entry("Smith2000", SMITH + [("doi", "{10.1/abc}")]))
    ruling = {"take": "intermediate", "because": "test", "seal": seals(repo)["Smith2000"]}
    repo.bib_rulings(SERIES, {"Smith2000": ruling})
    assert repo.bib_merge("--write").returncode == 0
    ruling["set"] = {"note": "added"}
    repo.bib_rulings(SERIES, {"Smith2000": ruling})
    res = repo.bib_merge()
    assert res.returncode == 2 and "[violation]" in res.stdout


# --------------------------------------------------------------------------- #
# Checks                                                                       #
# --------------------------------------------------------------------------- #
def test_every_key_a_pool_lecture_cites_must_resolve(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH) + entry("Unused1999", SMITH), "")
    repo.pool("lake.md").write_text("See {cite:t}`Smith2000` and {cite}`Smith2000, Gone2001`.\n", encoding="utf-8")
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "[closure] Gone2001: cited by lake.md but not in the merged file" in res.stdout
    assert "Unused1999" in res.stdout and "[info:unused]" in res.stdout

    repo.pool("lake.md").write_text("See {cite:t}`Smith2000`.\n", encoding="utf-8")
    assert repo.bib_merge().returncode == 0


@pytest.mark.parametrize(
    "text, message",
    [
        (entry("Ch1", [("author", "{A, B}"), ("title", "{T}"), ("booktitle", "{Book}"), ("year", "{1}")], "incollection"), "@incollection needs `publisher` (rule 2)"),
        (entry("Amp", [("author", "{Hu, Y. & Guo, Y.}"), ("title", "{T}"), ("journal", "{J}"), ("year", "{1}")]), "joins names with `&` or `;`"),
        (entry("Commas", [("author", "{Hu, Y., Guo, Y.}"), ("title", "{T}"), ("journal", "{J}"), ("year", "{1}")]), "separates names with commas"),
    ],
)
def test_style_rules_the_normalising_cannot_apply_fail_the_check(make_repo, text, message):
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert message in res.stdout, res.stdout


def test_keys_equal_when_case_is_ignored_fail_the_check(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("SMITH2000", SMITH))
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "Smith2000: equal to `SMITH2000` when case is ignored (rule 12)" in res.stdout, res.stdout
    assert "Traceback" not in res.stderr


def test_latex_escapes_and_organisations_are_reported_not_failed(make_repo):
    text = entry("Szoke2022", [("author", "{Sz{\\H{o}}ke, B{\\'a}lint and {{Ernst \\& Young}}}"), ("title", "{\\emph{Robust} Estimation}"), ("journal", "{JET}"), ("year", "{2022}")])
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout
    assert "[info:latex-escape] Szoke2022" in res.stdout


def test_a_series_with_a_bibliography_outside_the_list_is_reported(make_repo):
    repo = make_repo(["intro", "intermediate", "jax"])
    repo.bib("intro", entry("Smith2000", SMITH))
    repo.bib("intermediate", "")
    repo.bib("jax", entry("Jax2020", SMITH))
    repo.bib_rulings(SERIES)
    res = repo.bib_merge("--write")
    assert res.returncode == 0
    assert "[info:series-unlisted] jax has a quant-econ.bib" in res.stdout


@pytest.mark.parametrize(
    "ruling, message",
    [
        ({"take": "advanced", "because": "x", "seal": {"intro": "0" * 16}}, "takes `advanced`, which is not in `series`"),
        ({"take": "intro", "because": "x", "seal": {"intro": "0" * 16}, "colour": "red"}, "unknown fields: colour"),
        ({"take": "intro", "seal": {"intro": "0" * 16}}, "needs `because`"),
        ({"take": "intro", "because": "x", "seal": {"intro": "xyz"}}, "16-hex digest"),
    ],
)
def test_a_malformed_ruling_stops_the_run(make_repo, ruling, message):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "", {"Smith2000": ruling})
    res = repo.bib_merge()
    assert res.returncode == 2
    assert message in res.stderr, res.stderr
