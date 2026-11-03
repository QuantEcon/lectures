"""tools/bib-merge: one pool bibliography from the series' own files."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import re

import pytest
import yaml

SERIES = ["intro", "intermediate"]


def entry(key, fields, etype="article"):
    body = ",\n".join(f"  {name} = {value}" for name, value in fields)
    return f"@{etype}{{{key},\n{body}\n}}\n"


SMITH = [("author", "{Smith, Jane}"), ("title", "{A Title}"), ("journal", "{Econometrica}"), ("year", "{2000}")]
SMITH_DOI = SMITH + [("doi", "{10.1/abc}")]


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


def stubs(repo):
    """{key: stub} from --propose, read as the YAML it is."""
    out = repo.bib_merge("--propose").stdout
    return yaml.safe_load("rulings:\n" + out)["rulings"] or {}


def rule(repo, key, **fields):
    """A ruling for ``key``, sealed against the current copies."""
    return {**fields, "because": fields.get("because", "test"), "seal": stubs(repo)[key]["seal"]}


def outputs(tmp_path, repo, *args):
    """(result, {name: value}) with $GITHUB_OUTPUT captured."""
    path = tmp_path / "github_output"
    path.write_text("", encoding="utf-8")
    res = repo.bib_merge(*args, env={"GITHUB_OUTPUT": str(path)})
    values = dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return res, values


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


@pytest.mark.parametrize(
    "pages, expected",
    [
        ("S1-S20", "S1--S20"),
        ("1491 \u2212 1518", "1491--1518"),
        ("1-5,7-9", "1--5, 7--9"),
        ("1--68", "1--68"),
        ("1-1--1-20", "1-1--1-20"),
        ("A-1 to A-20", "A-1 to A-20"),
        ("123", "123"),
    ],
)
def test_a_page_range_is_rewritten_only_when_it_is_plainly_one(make_repo, pages, expected):
    repo = repo_with(make_repo, entry("P2000", SMITH + [("pages", f"{{{pages}}}")]), "")
    assert repo.bib_merge("--write").returncode == 0
    assert f"pages   = {{{expected}}}" in merged(repo)


@pytest.mark.parametrize("doi", ["doi:10.1/x", "https://www.doi.org/10.1/x", "dx.doi.org/10.1/x", "http://dx.doi.org/10.1/x"])
def test_a_doi_is_reduced_to_the_bare_doi(make_repo, doi):
    repo = repo_with(make_repo, entry("D2000", SMITH + [("doi", f"{{{doi}}}")]), "")
    assert repo.bib_merge("--write").returncode == 0
    assert "doi     = {10.1/x}" in merged(repo)


def test_the_output_does_not_depend_on_locale_or_hash_seed(make_repo):
    keys = ["beta", "Alpha", "gamma2", "Gamma1", "delta:2020/x+y"]
    text = "".join(entry(k, SMITH[:1] + [("title", "{Szőke and Borovička}")] + SMITH[2:]) for k in keys)
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
    ruling = rule(repo, "Smith2000", take="intermediate", set={"publisher": "Elsevier"}, drop=["number"], type="book")
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
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH_DOI))
    repo.bib_rulings(SERIES, {"Smith2000": rule(repo, "Smith2000", take="intermediate")})
    assert repo.bib_merge("--write").returncode == 0

    # Re-indented and re-ordered upstream: the bytes moved, the entries did not.
    repo.bib("intro", "@article{Smith2000,\n    year={2000},\n  author =   {Smith,   Jane},\n title={A Title}, journal={Econometrica}}\n")
    res = repo.bib_merge()
    assert res.returncode == 0, res.stdout

    # A copy that catches up with the ruled result holds too (a refresh).
    repo.bib("intro", entry("Smith2000", SMITH_DOI))
    res = repo.bib_merge()
    assert res.returncode == 1 and "[refresh]" in res.stdout and "[refused]" not in res.stdout
    assert repo.bib_merge("--write").returncode == 0

    # A real edit reopens the ruling.
    repo.bib("intro", entry("Smith2000", SMITH[:3] + [("year", "{2001}")]))
    res = repo.bib_merge()
    assert res.returncode == 2
    assert "[refused] Smith2000: reopened: the copy in intro changed since the ruling" in res.stdout


def test_an_edit_to_the_copy_a_ruling_takes_reopens_it(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH_DOI))
    repo.bib_rulings(SERIES, {"Smith2000": rule(repo, "Smith2000", take="intermediate")})
    assert repo.bib_merge("--write").returncode == 0
    before = body(repo)
    repo.bib("intermediate", entry("Smith2000", SMITH[:3] + [("year", "{1999}"), ("doi", "{10.1/abc}")]))
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "reopened: the copy it takes, intermediate's, changed since the ruling" in res.stdout
    assert body(repo) == before


def test_a_series_that_starts_holding_a_ruled_key_reopens_it(make_repo):
    repo = make_repo(["intro", "intermediate", "jax"])
    repo.bib("intro", entry("Smith2000", SMITH))
    repo.bib("intermediate", entry("Smith2000", SMITH_DOI))
    repo.bib("jax", "")
    repo.bib_rulings(["intro", "intermediate", "jax"])
    repo.bib_rulings(["intro", "intermediate", "jax"], {"Smith2000": rule(repo, "Smith2000", take="intermediate")})
    assert repo.bib_merge("--write").returncode == 0
    repo.bib("jax", entry("Smith2000", SMITH[:3] + [("year", "{2002}")]))
    res = repo.bib_merge()
    assert res.returncode == 2 and "jax now holds it, with a copy that differs from the result" in res.stdout
    repo.bib("jax", entry("Smith2000", SMITH_DOI))
    assert repo.bib_merge().returncode == 1


def test_a_ruling_whose_copy_is_gone_is_refused(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH_DOI))
    repo.bib_rulings(SERIES, {"Smith2000": rule(repo, "Smith2000", take="intermediate")})
    repo.bib("intermediate", "")
    res = repo.bib_merge()
    assert res.returncode == 2
    assert "its ruling takes `intermediate`, which no longer holds it" in res.stdout


def test_propose_seals_every_held_copy_and_keeps_a_reopened_rulings_fixes(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH_DOI))
    stub = stubs(repo)["Smith2000"]
    assert stub["take"] == "intermediate" and "one copy has more fields" in stub["because"]
    assert set(stub["seal"]) == {"intro", "intermediate"} and all(isinstance(d, str) for d in stub["seal"].values())

    repo.bib_rulings(SERIES, {"Smith2000": rule(repo, "Smith2000", take="intermediate", set={"note": "kept"}, because="the owner")})
    assert repo.bib_merge("--write").returncode == 0
    repo.bib("intermediate", entry("Smith2000", SMITH_DOI + [("volume", "{9}")]))
    stub = stubs(repo)["Smith2000"]
    assert stub["take"] == "intermediate" and stub["set"] == {"note": "kept"}
    assert stub["because"].startswith("TODO (re-sealed; it was: the owner)")

    # A stub must be edited before it counts: `because: TODO` is refused.
    repo.bib_rulings(SERIES, {"Smith2000": stub})
    res = repo.bib_merge()
    assert res.returncode == 2 and "`because` must say why" in res.stderr


# --------------------------------------------------------------------------- #
# What it refuses, and what it must read                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text, message",
    [
        (entry("Smith2000", SMITH) + entry("Smith2000", SMITH), "Duplicate"),
        ("@article{Smith2000,\n  title = {A},\n  title = {B}\n}\n", "Duplicate"),
        ("@article{Smith2000,\n  title = {A},\n  Title = {B}\n}\n", "field `title` appears twice"),
        ("@string{jpe = {Journal of Political Economy}}\n" + entry("Smith2000", SMITH), "@string"),
        (entry("Smith2000", SMITH[:2] + [("journal", "jpe")]), "field `journal` is the bare macro 'jpe'"),
        (entry("Smith2000", SMITH[:2] + [("journal", '{Journal of} # " Things"')]), "field `journal` is a concatenation"),
        (entry("Smith2000", SMITH[:1] + [("title", '"a } { b"')] + SMITH[2:]), "cannot be read"),
        ("@article{Smith2000,\n  title = {T},\n  % year = {1999},\n  journal = {J}\n}\n", "is not a field name"),
        ("@article{Smith2000,\n  title = {unbalanced\n}\n", "cannot be read exactly"),
        (entry("Smith2000", SMITH) + "@comment{@book{Hidden2020, title = {H}, publisher = {P}, year = {2020}}}\n", "find different keys"),
        (entry("Smith2000", SMITH) + entry("SMITH2000", SMITH), "find different keys"),
    ],
)
def test_input_it_cannot_read_exactly_is_refused_and_nothing_is_written(make_repo, text, message):
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    ours = [line for line in res.stderr.splitlines() if line.startswith("bib-merge: intro")]
    assert ours and message in ours[0], res.stderr
    assert not repo.pool("_static/quant-econ.bib").exists()


def test_a_file_that_is_not_utf8_is_refused(make_repo):
    repo = repo_with(make_repo, "", "")
    repo.mirror_file("intro", "_static/quant-econ.bib", "@article{K, title = {Caf\xe9}, journal = {J}}\n".encode("latin-1"))
    res = repo.bib_merge("--write")
    assert res.returncode == 2 and "is not UTF-8" in res.stderr


def test_unusual_but_valid_input_survives(make_repo):
    text = (
        "@online{site2020,\n  title = {A Site},\n  url = {https://example.org/a%20b},\n  year = {2020}\n}\n"
        "@misc{bare,\n}\n"
        '@article{quote2001,\n  title = "The {"}Quote{"} Paper",\n  journal = {J},\n  year = {2001}\n}\n'
        "@article{odd:key/2002+x,\n  title = {Braces \\{inside\\} and # @ =},\n  journal = {J},\n  year = {2002}\n}\n"
    )
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout + res.stderr
    out = merged(repo)
    assert "@online{site2020," in out and "@misc{bare," in out
    assert 'title   = {The {"}Quote{"} Paper}' in out
    assert "@article{odd:key/2002+x," in out


def test_an_entry_that_would_not_read_back_is_refused_alone(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH) + entry("Jones2001", SMITH), entry("Smith2000", SMITH_DOI))
    repo.bib_rulings(SERIES, {"Smith2000": rule(repo, "Smith2000", take="intermediate", set={"title": "Broken {"})})
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "[refused] Smith2000: its merged entry would not read back as written" in res.stdout
    out = merged(repo)
    assert "@article{Jones2001," in out and "Smith2000" not in out


def test_a_month_pybtex_does_not_know_is_read_and_dropped(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH + [("month", "sept")]), "")
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "month" not in body(repo) and "[info:pybtex] intro:" in res.stdout


@pytest.mark.parametrize(
    "field, raw, expected",
    [("pages", "{1-3,}", "1--3,"), ("doi", "{https://doi.org/doi:10.1/x}", "10.1/x"), ("doi", "{doi: https://doi.org/10.1/x}", "10.1/x")],
)
def test_the_normalising_is_idempotent(make_repo, field, raw, expected):
    repo = repo_with(make_repo, entry("Smith2000", SMITH + [(field, raw)]), "")
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout
    assert f"= {{{expected}}}" in merged(repo)
    assert repo.bib_merge().returncode == 0


def test_keys_equal_but_for_case_keep_the_committed_one_and_refresh_the_rest(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH) + entry("Jones2001", SMITH), "")
    assert repo.bib_merge("--write").returncode == 0
    repo.bib("intermediate", entry("smith2000", SMITH))
    repo.bib("intro", entry("Smith2000", SMITH) + entry("Jones2001", SMITH_DOI))
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "[refused] smith2000: equal to `Smith2000` when case is ignored" in res.stdout
    out = merged(repo)
    assert "@article{Smith2000," in out and "@article{smith2000," not in out
    assert "doi     = {10.1/abc}" in out  # Jones2001's update was not held back


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
    assert res.returncode == 2 and "[violation]" in res.stdout and "a hand edit" in res.stdout

    # The same hand edit is still a violation when a series has also moved.
    repo.bib("intermediate", entry("Jones2001", SMITH))
    res = repo.bib_merge()
    assert res.returncode == 2 and "a hand edit" in res.stdout
    path.write_text(clean, encoding="utf-8")
    res = repo.bib_merge()
    assert res.returncode == 1 and "[refresh]" in res.stdout
    assert repo.bib_merge("--write").returncode == 0

    # A byte change upstream that the normalising removes moves nothing.
    repo.bib("intermediate", entry("Jones2001", SMITH + [("abstract", "{Never shown.}")]))
    assert repo.bib_merge().returncode == 0

    # A ruling changed in the repository must be regenerated in the same change,
    # even when a series has moved too.
    repo.bib("intermediate", entry("Smith2000", SMITH_DOI))
    ruling = rule(repo, "Smith2000", take="intermediate")
    repo.bib_rulings(SERIES, {"Smith2000": ruling})
    assert repo.bib_merge("--write").returncode == 0
    repo.bib_rulings(SERIES, {"Smith2000": {**ruling, "set": {"note": "added"}}})
    repo.bib("intro", entry("Smith2000", SMITH) + entry("New2003", SMITH))
    res = repo.bib_merge()
    assert res.returncode == 2 and "sync/bib.yml changed and the file was not regenerated" in res.stdout


def test_a_hand_edit_to_a_carried_entry_is_a_violation(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH))
    assert repo.bib_merge("--write").returncode == 0
    repo.bib("intermediate", entry("Smith2000", SMITH_DOI))
    assert repo.bib_merge("--write").returncode == 2  # refused, carried
    path = repo.pool("_static/quant-econ.bib")
    path.write_text(path.read_text(encoding="utf-8").replace("{A Title}", "{Edited}"), encoding="utf-8")
    res = repo.bib_merge()
    assert res.returncode == 2 and "a hand edit" in res.stdout


@pytest.mark.parametrize("damage", ["hand edit", "unreadable", "not utf-8"])
def test_write_carries_nothing_from_a_committed_file_it_cannot_trust(make_repo, damage):
    repo = repo_with(make_repo, entry("Smith2000", SMITH) + entry("Jones2001", SMITH), entry("Smith2000", SMITH))
    assert repo.bib_merge("--write").returncode == 0
    repo.bib("intermediate", entry("Smith2000", SMITH_DOI))  # Smith2000 is now refused
    path = repo.pool("_static/quant-econ.bib")
    text = path.read_text(encoding="utf-8")
    if damage == "hand edit":
        path.write_text(text.replace("@article{Jones2001,", "@article{Jones2001,\n  note = {edited},"), encoding="utf-8")
    elif damage == "unreadable":
        path.write_text(text.replace("@article{Smith2000,", "<<<<<<< HEAD\n@article{Smith2000,"), encoding="utf-8")
    else:
        path.write_bytes(text.encode("utf-8") + "% caf\xe9\n".encode("latin-1"))
    before = path.read_bytes()
    res = repo.bib_merge("--write")
    assert res.returncode == 2
    assert "[write-refused]" in res.stdout and "cannot be trusted" in res.stdout, res.stdout
    assert path.read_bytes() == before
    check = repo.bib_merge()
    assert check.returncode == 2 and "[violation]" in check.stdout and "is missing" not in check.stdout


def test_an_unforeseen_error_fails_and_reports_an_error_state(tmp_path, make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "")
    bib = repo.root / "mirror" / "intermediate" / "lectures" / "_static" / "quant-econ.bib"
    bib.unlink()
    bib.mkdir()  # a directory where the file should be
    res, out = outputs(tmp_path, repo)
    assert res.returncode == 2 and "internal error" in res.stderr
    assert out == {"bib_state": "error", "bib_failed": "true", "bib_refresh": "false"}


def test_a_malformed_header_is_a_violation_not_a_crash(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "")
    assert repo.bib_merge("--write").returncode == 0
    path = repo.pool("_static/quant-econ.bib")
    path.write_text(re.sub(r"(?m)^% inputs: .*$", "% inputs: garbage", path.read_text(encoding="utf-8")), encoding="utf-8")
    res = repo.bib_merge()
    assert res.returncode == 2 and "[violation]" in res.stdout and "Traceback" not in res.stderr


def test_the_outputs_the_workflow_reads(tmp_path, make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "")
    res, out = outputs(tmp_path, repo)
    assert res.returncode == 2 and out == {"bib_state": "missing", "bib_failed": "true", "bib_refresh": "false"}
    repo.bib_merge("--write")
    res, out = outputs(tmp_path, repo)
    assert res.returncode == 0 and out == {"bib_state": "clean", "bib_failed": "false", "bib_refresh": "false"}
    repo.bib("intermediate", entry("Jones2001", SMITH))
    res, out = outputs(tmp_path, repo)
    assert res.returncode == 1 and out == {"bib_state": "refresh", "bib_failed": "false", "bib_refresh": "true"}
    repo.bib("intermediate", entry("Smith2000", SMITH_DOI))
    res, out = outputs(tmp_path, repo)
    assert res.returncode == 2 and out == {"bib_state": "refresh", "bib_failed": "true", "bib_refresh": "true"}


@pytest.mark.parametrize(
    "rulings_text, message",
    [
        ("series: [intro, intermediate\nrulings: {}\n", "sync/bib.yml cannot be read"),
        ("- intro\n- intermediate\n", "must be a mapping"),
        ("series: [intro, intermediate]\nrulings:\n  Smith2000: {take: intro, because: x, seal: {intro: '0000000000000000'}, drop: [1]}\n", "`drop` must be a list of field names"),
        ("series: [intro, intermediate]\nrulings:\n  Smith2000: {take: intro, because: x, seal: {intro: '0000000000000000'}, set: {1999: x}}\n", "`set` must map field names"),
        ("series: [intro, intermediate]\nrulings:\n  1999: {take: intro, because: x, seal: {intro: '0000000000000000'}}\n", "the key must be a string"),
        ("series: [intro, intermediate]\nrulings:\n  Smith2000: {take: intro, because: x, seal: {intro: 1234567890123456}}\n", "16-hex digest"),
    ],
)
def test_a_malformed_rulings_file_fails_and_says_why(tmp_path, make_repo, rulings_text, message):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "")
    (repo.root / "sync" / "bib.yml").write_text(rulings_text, encoding="utf-8")
    res, out = outputs(tmp_path, repo)
    assert res.returncode == 2 and message in res.stderr, res.stderr
    assert out["bib_state"] == "error" and out["bib_failed"] == "true"


@pytest.mark.parametrize(
    "ruling, message",
    [
        ({"take": "advanced", "because": "x", "seal": {"intro": "0" * 16}}, "takes `advanced`, which is not in `series`"),
        ({"take": "intro", "because": "x", "seal": {"intro": "0" * 16}, "colour": "red"}, "unknown fields: colour"),
        ({"take": "intro", "seal": {"intro": "0" * 16}}, "needs `because`"),
        ({"take": "intro", "because": "x", "seal": {"intro": "xyz"}}, "16-hex digest"),
        ({"take": "intro", "because": "x", "seal": {"intro": "0" * 16}, "set": {"note": " "}}, "use `drop` to remove a field"),
    ],
)
def test_a_malformed_ruling_stops_the_run(make_repo, ruling, message):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), "", {"Smith2000": ruling})
    res = repo.bib_merge()
    assert res.returncode == 2
    assert message in res.stderr, res.stderr


# --------------------------------------------------------------------------- #
# Checks and reports                                                           #
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
        # pybtex reads this with a warning; the key, not the file, fails.
        (entry("Commas", [("author", "{Hu, Y., Guo, Y.}"), ("title", "{T}"), ("journal", "{J}"), ("year", "{1}")]), "separates names with commas"),
        (entry("Stray", [("author", "{Kydland, Finn E., and Edward C. Prescott}"), ("title", "{T}"), ("journal", "{J}"), ("year", "{1}")]), "an empty name or a stray comma"),
        (entry("Doi", SMITH + [("doi", "{https://example.org/paper}")]), "is not a bare DOI starting `10.`"),
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
    assert "[refused] Smith2000: equal to `SMITH2000` when case is ignored" in res.stdout, res.stdout
    assert "[refused] SMITH2000: equal to `Smith2000` when case is ignored" in res.stdout
    assert "Traceback" not in res.stderr


def test_what_is_reported_but_not_failed(make_repo):
    text = (
        entry("Szoke2022", [("author", "{Sz{\\H{o}}ke, B{\\'a}lint and {{Ernst \\& Young}}}"), ("title", "{\\emph{Robust} Estimation}"), ("journal", "{JET}"), ("year", "{2022}")])
        + entry("CS1988", [("author", "{John Y. Campbell, Robert J. Shiller}"), ("title", "{T}"), ("journal", "{J}"), ("year", "{1988}")])
        + entry("DL1991", [("author", "{De Long, J. Bradford}"), ("title", "{T}"), ("journal", "{J}"), ("year", "{1991}")])
    )
    repo = repo_with(make_repo, text, "")
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout
    assert "[info:latex-escape] Szoke2022" in res.stdout
    assert "[info:style-name] CS1988" in res.stdout and "DL1991" not in res.stdout.split("[info:unused]")[0]


def test_a_series_with_a_bibliography_outside_the_list_is_reported(make_repo):
    repo = make_repo(["intro", "intermediate", "jax"])
    repo.bib("intro", entry("Smith2000", SMITH))
    repo.bib("intermediate", "")
    repo.bib("jax", entry("Jax2020", SMITH))
    repo.bib_rulings(SERIES)
    res = repo.bib_merge("--write")
    assert res.returncode == 0
    assert "[info:series-unlisted] jax has a quant-econ.bib" in res.stdout


def test_a_consumer_series_is_never_a_source(make_repo):
    repo = make_repo(["intro", "intermediate", "dp"], consumers=["dp"])
    repo.bib("intro", entry("Smith2000", SMITH))
    repo.bib("intermediate", "")
    repo.bib("dp", entry("Smith2000", SMITH_DOI))  # a consumer's older copy
    repo.bib_rulings(["intro", "intermediate", "dp"])
    res = repo.bib_merge("--write")
    assert res.returncode == 2 and "sync/bib.yml: `series` lists consumer series (class: consumer in sync/manifest.yml): dp;" in res.stderr, res.stderr

    # Left out of the list, its bibliography is ignored, and not reported as unlisted.
    repo.bib_rulings(SERIES)
    res = repo.bib_merge("--write")
    assert res.returncode == 0, res.stdout
    assert "series-unlisted" not in res.stdout
    assert "doi" not in body(repo)


def test_the_report_goes_to_stdout_and_the_check_to_stderr(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH), entry("Smith2000", SMITH_DOI))
    res = repo.bib_merge("--report")
    assert res.stdout.startswith("## Bibliography conflicts (1)")
    assert "### `Smith2000`: refused:" in res.stdout and "| doi | — | `10.1/abc` | · |" in res.stdout
    assert "[refused] Smith2000" in res.stderr and "[refused]" not in res.stdout


def test_the_equivalence_check_names_an_entry_pybtex_reads_differently(make_repo):
    repo = repo_with(make_repo, entry("Smith2000", SMITH) + entry("Jones2001", SMITH), "")
    loader = importlib.machinery.SourceFileLoader("bib_merge_under_test", str(repo.root / "tools" / "bib-merge"))
    spec = importlib.util.spec_from_loader("bib_merge_under_test", loader)
    tool = importlib.util.module_from_spec(spec)
    loader.exec_module(tool)
    series, rulings, rulings_digest = tool.load_rulings()
    copies, inputs, sources, _ = tool.collect_copies(series)
    merge = tool.Merge(series, rulings, copies, {})
    text = tool.render(merge.entries, inputs, rulings_digest)
    assert tool.equivalence_findings(text, merge, sources) == []
    tampered = text.replace("{Smith, Jane}", "{Smith, J.}", 1)
    assert tool.equivalence_findings(tampered, merge, sources) == [
        "Jones2001: pybtex reads the merged entry differently from intro's copy in author"
    ]
