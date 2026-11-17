# `sites/` — one folder per published site

Each folder here is one published site, built on Jupyter Book 1 from the pool (`lectures/`) by selecting and ordering its lectures. Today there is one site per series, under the series' key from [`sync/manifest.yml`](../sync/manifest.yml): `intro`, `programming`, `intermediate`, `advanced`, `dp` and `jax`. A future course or reader is also a site, a new folder with a new `type` in its `site.yml`, not a new layout.

Nothing here is generated from a shared base. Each site's `_config.yml` and `_toc.yml` are the series' own files, copied verbatim from the series at the pin in [`sync/state.yml`](../sync/state.yml), with only the additions the build from the pool needs (QuantEcon/project-monorepo#21). An addition is always a whole line, and every added line holds the marker `# site addition`: a comment line that says why, then each line of YAML it adds with `  # site addition` after it. Removing every line that holds the marker gives back the series' file exactly, which is how the drift-check compares them.

## What a site's folder holds

| Path | What it is |
| --- | --- |
| `_config.yml` | The series' `_config.yml`, verbatim, plus the additions below |
| `_toc.yml` | The series' `_toc.yml`, verbatim (dp: one addition, below) |
| `site.yml` | The fields the build workflow reads (below) |
| `<name>.md` | The site's own pages, verbatim from the series: `intro`, `status`, and whichever of `troubleshooting`, `zreferences`, `about` and jax's `about_jax` the series has. They are not pool lectures (`tools/promote`'s `SITE_PAGES`) |
| `_static/` | The site's own files, verbatim from the series: the branding its `_config.yml` names (`logo`, `html_favicon`, `dark_logo`), and the files its pages use (`troubleshooting.md`'s `_static/lecture_specific/troubleshooting/launch.png`). Branding never enters the pool |

| Site | Pages | `_static/` |
| --- | --- | --- |
| `intro` | intro, about, status, troubleshooting, zreferences | qe-logo.png, lectures-favicon.ico, quantecon-logo-transparent.png, launch.png |
| `programming` | intro, status, troubleshooting | qe-logo.png, lectures-favicon.ico, quantecon-logo-transparent.png, launch.png |
| `intermediate` | intro, status, troubleshooting, zreferences | qe-logo-large.png, lectures-favicon.ico, launch.png |
| `advanced` | intro, status, troubleshooting, zreferences | qe-logo-large.png, lectures-favicon.ico, launch.png |
| `dp` | intro, status, zreferences | qe-logo-large.png, lectures-favicon.ico |
| `jax` | intro, about_jax, status, troubleshooting, zreferences | qe-logo-large.png, lectures-favicon.ico, quantecon-logo-transparent.png, launch.png |

The bibliography every `zreferences.md` and `_config.yml` names, `_static/quant-econ.bib`, is the pool's merged file ([`tools/bib-merge`](../tools/bib-merge)), not a site's.

## `site.yml`

| Field | What it holds | Values |
| --- | --- | --- |
| `type` | The kind of site | `series` for all six today |
| `runner` | The runner class the build runs on | `ubuntu-latest`, or the RunsOn GPU class `g4dn.2xlarge` |
| `cell_timeout` | Seconds, the limit on one cell's execution | A whole number above 0 |
| `publishes` | What the site publishes | A list of `html`, `pdf`, `notebooks`, with `html` |
| `url` | The published address | `html.baseurl` in the site's `_config.yml` |

Today's values, read from each series at its pin on 2026-11-17 (each `site.yml` names its source in comments):

| Site | `runner` | `cell_timeout` | `publishes` | `url` |
| --- | --- | --- | --- | --- |
| `intro` | ubuntu-latest | 600 | html, pdf, notebooks | https://intro.quantecon.org/ |
| `programming` | g4dn.2xlarge | 600 | html, pdf, notebooks | https://python-programming.quantecon.org/ |
| `intermediate` | g4dn.2xlarge | 2400 | html, pdf, notebooks | https://python.quantecon.org/ |
| `advanced` | ubuntu-latest | 7200 | html, pdf, notebooks | https://python-advanced.quantecon.org/ |
| `dp` | ubuntu-latest | 2400 | html | https://quantecon.github.io/lecture-dp/ |
| `jax` | g4dn.2xlarge | 2400 | html, pdf, notebooks | https://jax.quantecon.org/ |

- **`runner`** is what each series' `publish.yml` and `ci.yml` run on.
- **`cell_timeout`** is `execute: timeout` in the series' `_config.yml`, Jupyter Book's limit on one cell's execution. No series workflow sets a job time limit (`timeout-minutes`).
- **`publishes`** follows each series' `publish.yml`: five run three builds (`pdflatex` for the PDF, the `jupyter` builder for the notebooks, and HTML); dp's builds HTML alone.
- **`url`** is `html.baseurl`. dp's planned address, https://dynamic-programming.quantecon.org, changes it when dp moves.

## The deviations from verbatim

Every one of them, per site. A diff of a site's `_config.yml` or `_toc.yml` against the series' own file shows these and nothing else, and every line of them holds the `# site addition` marker.

| Addition | Why | Sites |
| --- | --- | --- |
| `execute: cache: _build/jupyter_cache/<key>` | The site's own execution cache, one per site as the build workflow keys it (QuantEcon/project-monorepo#77). The path is read from the directory `jb` is run from, the repository's root | all six |
| `intersphinx_disabled_reftypes: []` | A link with no target in the site resolves on the lecture's home site (QuantEcon/project-monorepo#22) | intro, programming, advanced, dp, jax (intermediate's own file already sets it) |
| `intersphinx_mapping` gains the site's own key and address | A site maps itself: a pool lecture whose home is another series writes its links into its home with the prefix (``{doc}`intermediate:linear_models` ``), and the build fails on a prefix the site does not define (the second-product spike, QuantEcon/project-monorepo#58) | programming, intermediate, advanced, jax (intro's own file already maps `intro`); not dp, below |
| `only_build_toc_files: true` | Build only the pages `_toc.yml` lists: the pool holds every series' lectures, and without it Jupyter Book builds every page in its source folder | programming, advanced (the others' own files set it) |
| `_toc.yml`: `- file: mccall_risk` after `- file: mccall_fitted_vfi` | Built from the pool, dp's Job Search lectures take intermediate's current text, numbered I to IX, and `mccall_risk` is the one lecture-dp does not list. Adding it in lecture-dp would show "Job Search V" twice on the live site, whose copies are still numbered V to VIII (QuantEcon/project-monorepo#21, 2026-10-08). The shadow comparison lists the extra page and the four renumbered titles as expected differences | dp |

Two things that are not additions:

- **No site maps `dp`,** and none of the six series' files does today, so nothing was removed. dp maps no site for itself either: its key is `dp`, and it holds no lecture of its own for a prefixed link to name.
- **jax's `_config.yml` sets `only_build_toc_files` twice** (`false`, then `true`). The later one wins, as in the series' own build; it is kept verbatim.

## Staging and building a site locally

Sphinx reads only inside its source folder, and every site's root page is called `intro.md`, so a site's own pages are copied into `lectures/` just before the build and removed after. [`tools/stage-site`](../tools/stage-site) does the copy: every `sites/<key>/<name>.md` to `lectures/<name>.md`, and every file under `sites/<key>/_static/` to the same path under `lectures/_static/`. It never overwrites: a destination that already exists, whatever its bytes, stops the run before anything is copied. It writes what it copies, and the folders it makes, to a record outside the pool, `_build/stage-site.json` (`_build/` is ignored by git), and `--clean` removes only what that record lists, each file only while its bytes are still the ones it copied, so it can never remove a pool file. One site is staged at a time: staging refuses while a record exists.

From the repository's root, with Jupyter Book 1 and the series' packages installed (each series' `environment.yml`):

```bash
uv run --script tools/stage-site dp
jb build lectures --toc "$PWD/sites/dp/_toc.yml" --config "$PWD/sites/dp/_config.yml" --path-output _build/sites/dp -n -W --keep-going
uv run --script tools/stage-site --clean dp
```

Give `--toc` as an absolute path: Jupyter Book 1 reads a relative one from inside `lectures/`. Clean before committing, or before running `tools/pool-check` and `tools/assets-report --check-index`, which read a staged page or file as the pool's. A lecture executes in `lectures/`, so a file it writes is left there too: dp's `short_path` writes `lectures/graph.txt`, which `--clean` does not remove (it did not stage it), and `git status` shows.

**`-n -W` is stricter than two series build today.** intro's and advanced's own publish builds run their HTML without `-n` or `-W`, and their PDF with `-n` only; programming, intermediate and jax build with `-n -W`, and dp through `QuantEcon/actions`' `build-lectures`. So a strict build of the intro or advanced site may fail on warnings those series tolerate today. How strict each site's build is, is QuantEcon/project-monorepo#25's to settle per site; `site.yml` does not carry it.

To see what the build executed, run [`tools/execution-report`](../tools/execution-report) with the Python that ran `jb build`, giving it the build's start so it can tell an executed page from one taken from the cache (below):

```bash
since=$(date +%s)
jb build lectures …   # as above
python tools/execution-report --build-dir _build/sites/dp/_build --since "$since" --site dp
```

## Building a site in CI

[`site-build.yml`](../.github/workflows/site-build.yml) builds the sites named in its `SITES` list, today `dp` alone: on every push to `main` and every pull request that touches the pool, the sites, the tools a build runs or what `tools/sync` reads; on demand; and on Mondays and Thursdays. Nothing is published. The other five sites are built when each is brought through (QuantEcon/project-monorepo#77).

Each site is one leg of a matrix (`fail-fast: false`, so one site's failure stops no other). [`tools/site-matrix`](../tools/site-matrix) reads the leg's settings from `site.yml`:

| `site.yml` | What the leg takes from it |
| --- | --- |
| `runner` | `runs-on`, and the container: `ubuntu-latest` builds in `ghcr.io/quantecon/quantecon-build:latest`, as dp's own workflows do. A site on the GPU class is refused until its leg, which needs a different shape (no container, the series' environment through conda, JAX for CUDA), is written |
| `cell_timeout` | The job's time limit, `timeout-minutes`: `cell_timeout` in whole minutes, the longest one cell may run, plus 120 minutes for the rest of a build from an empty cache. `site.yml` holds no job limit of its own, since no series sets one; dp's own weekly build from an empty cache took 22 to 41 minutes in October and November 2026. The per-cell limit itself stays where Jupyter Book reads it, `execute: timeout` in `_config.yml` |
| `type` | Only `series` has a leg so far: its execution cache is keyed on the series' `environment.yml` |
| `publishes` | Not yet: every leg builds HTML alone, which is all dp publishes |

A leg checks the repository out with its full history, reconstructs `mirror/<key>/` at the series' pin (`tools/sync <key>`, a few seconds, for the one file the cache key hashes, `environment.yml`), restores the site's execution cache, stages the site, and builds it with `QuantEcon/actions`' `build-lectures`: `builder: html`, `source-dir: lectures`, and `extra-args` with the absolute `--toc` and `--config` and `-W --keep-going` (`build-lectures` adds `-n`). So a warning, a cell that raises, a reference that does not resolve, or a label that two of the site's lectures both define fails the build, and `--keep-going` lists every failure, not only the first. It then writes the execution report, keeps the HTML (`html-<key>`, after a green build, for 7 days) and the report (`execution-status-<key>`) as artefacts, saves the cache and unstages the site. A failed build also uploads `build-lectures`' failure reports (`execution-reports-<key>`).

**The execution cache** is `actions/cache`, one per site, at the path the site's `_config.yml` names, `_build/jupyter_cache/<key>` (rule 7). A cache is never overwritten, so each one is saved under a new key, `jb1-<key>-<env hash>-<run>`, where the hash is of `mirror/<key>/environment.yml`, and a restore takes the newest one under `jb1-<key>-<env hash>-`. There is no fallback to another environment's cache: a changed `environment.yml` starts from an empty cache, rather than reuse outputs that other packages produced. A pull request only restores. A run on `main` saves after a green build that executed at least one page; one that took every page from the cache has nothing new to save. The twice-weekly run keeps each cache in use: GitHub drops a cache that is not read for 7 days. Like dp's own cache, it is keyed on `environment.yml` and not on the container image, so a new `:latest` image does not empty it.

**The execution report**, `execution_status.json`, is one row per page the build executed or took from the cache. [`tools/execution-report`](../tools/execution-report) reads it from Sphinx's environment (`_build/.doctrees/environment.pickle`), where myst-nb records each notebook page's execution, the record its own `{nb-exec-table}` (dp's `status` page) draws on. It does not read the jupyter-cache database, which holds only the pages that executed cleanly, from every build the cache has seen.

| Field | What it holds |
| --- | --- |
| `page` | The page, as Sphinx names it (`mccall_model`) |
| `status` | `ok`, `failed` (with `error`, the exception's class, and `report`, the traceback myst-nb wrote to `_build/html/reports/`), or `excluded`: a notebook page the build did not execute |
| `duration` | Seconds its execution took; for a page from the cache, the time recorded when the cache executed it |
| `kernel` | The kernel it names |
| `execution` | `executed` by this build, or `cached`: its outputs were taken from the execution cache |

The report also records the site, the build's start, the versions of the packages that decide what a page's execution produces, and the counts. The counts and the full table go to the run's summary.

## The rules

[`tools/pool-check`](../tools/pool-check) keeps them on every pull request that touches `lectures/` or `sites/` ([`pool-check.yml`](../.github/workflows/pool-check.yml)), except the third, which needs the mirror and is the drift-check's.

1. **Every site maps itself in `intersphinx_mapping`,** to the address in its `site.yml`. A consumer series (`class: consumer` in `sync/manifest.yml`, today `dp`) is the exception, by rule 2.
2. **No site maps `dp`.** dp only republishes other series' lectures; a link that leaves a site must land on the lecture's home, never on a copy.
3. **Lecture names are unique across the published sites.** A link that leaves a site resolves by name, so two sites publishing different lectures under one name would send readers to the wrong one. [`tools/drift-check`](../tools/drift-check) keeps it (`name-shared`).
4. **A link with no target in the site resolves to the lecture's home site,** through `intersphinx_disabled_reftypes: []`, by rules 1 to 3.
5. **Every `_toc.yml` entry is a pool lecture or a page of the site,** a site page never has a pool lecture's name, and no file under a site's `_static/` is also a pool file: staging would overwrite it.
6. **`site.yml` has every field above, each with a valid value,** and the branding a `_config.yml` names is in the site's `_static/`.
7. **The additions a build needs stay:** every site sets `only_build_toc_files: true` and its own cache, `execute.cache: _build/jupyter_cache/<key>`, and `_config.yml` is well formed where these rules read it.

## Keeping the copies true to the series

A site's files are copies of its series' files, so they follow the series until its cutover. After every sync the drift-check ([`tools/drift-check`](../tools/drift-check)) compares every file in each series' site folder but `site.yml` with the series' `lectures/<path>` at the pin: the pages and the `_static/` files byte for byte, and `_config.yml` and `_toc.yml` with every `# site addition` line removed. Each file that differs, or that the series no longer has, is `site-stale`, a `drift` finding: the nightly run opens an issue for it, with the diff, and closes the issue once the copy matches again. To settle one, copy the series' file at the pin over the site's and put back the lines marked `# site addition`. A change the site must not take is a decision to record here, as a marked addition, not a copy to leave stale.
