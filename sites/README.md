# `sites/` — one folder per published site

Each folder here is one published site, built on Jupyter Book 1 from the pool (`lectures/`) by selecting and ordering its lectures. Today there is one site per series, under the series' key from [`sync/manifest.yml`](../sync/manifest.yml): `intro`, `programming`, `intermediate`, `advanced`, `dp` and `jax`. A future course or reader is also a site, a new folder with a new `type` in its `site.yml`, not a new layout.

Nothing here is generated from a shared base. Each site's `_config.yml` and `_toc.yml` are the series' own files, copied verbatim from the series at the pin in [`sync/state.yml`](../sync/state.yml), with only the additions the build from the pool needs (QuantEcon/project-monorepo#21). An addition is always a whole line, and every added line holds the marker `# site addition`: a comment line that says why, then each line of YAML it adds with `  # site addition` after it. Removing every line that holds the marker gives back the series' file exactly, which is how the drift-check compares them.

A setting the site must change, not add, is an addition too: the series' line stays as it is, and a marked line after it sets the same key again. YAML's later key wins as everything here reads these files (PyYAML, in Jupyter Book 1, `tools/pool-check`, the drift-check and `build-lectures`' check of the executed notebooks), and jax's own file already relies on it (below). Placed before the series' line, the series' value would win, so pool-check checks the value the build reads, not the line. `repository_url` is the one override today.

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
| `extra_packages` | Optional: what the build installs with pip before it builds the site | A list of pip requirements, each a name with optional `[extras]` and version specifiers, no spaces, none starting with `-`, each at most once |
| `environment` | Optional: what the build runs in | `series` (the default): the lean image, with nothing installed but `extra_packages`; or `base`: the full image with `_base/environment-update.yml` applied, or on a GPU site the same base created on its machine, with the list and `jax[cuda13]` |

Today's values, read from each series at its pin on 2026-11-17, and dp's `publishes` on 2026-11-26 (each `site.yml` names its source in comments):

| Site | `runner` | `cell_timeout` | `publishes` | `url` |
| --- | --- | --- | --- | --- |
| `intro` | ubuntu-latest | 600 | html, pdf, notebooks | https://intro.quantecon.org/ |
| `programming` | g4dn.2xlarge | 600 | html, pdf, notebooks | https://python-programming.quantecon.org/ |
| `intermediate` | g4dn.2xlarge | 2400 | html, pdf, notebooks | https://python.quantecon.org/ |
| `advanced` | ubuntu-latest | 7200 | html, pdf, notebooks | https://python-advanced.quantecon.org/ |
| `dp` | ubuntu-latest | 2400 | html, notebooks | https://quantecon.github.io/lecture-dp/ |
| `jax` | g4dn.2xlarge | 2400 | html, pdf, notebooks | https://jax.quantecon.org/ |

- **`runner`** is what each series' `publish.yml` and `ci.yml` run on.
- **`cell_timeout`** is `execute: timeout` in the series' `_config.yml`, Jupyter Book's limit on one cell's execution. No series workflow sets a job time limit (`timeout-minutes`).
- **`publishes`** follows each series' `publish.yml`: five run three builds (`pdflatex` for the PDF, the `jupyter` builder for the notebooks, and HTML); dp's runs two, the notebooks and HTML, with no PDF (since QuantEcon/lecture-dp#87).
- **`url`** is `html.baseurl`. dp's planned address, https://dynamic-programming.quantecon.org, changes it when dp moves.
- **`extra_packages`** is set by dp alone: `[jax]`. The image the build runs in has no jax, and `mccall_risk`, the lecture dp's site adds from intermediate, imports it after installing only `quantecon`. In a cold build it passes only because pages read before it install jax themselves; once those pages come from the cache, it would fail on its own. The owner decided on 2026-11-17 that dp keeps its own environment and the build installs jax first. On `ubuntu-latest`, `jax` is the CPU wheel; a GPU site's leg adds `jax[cuda13]` at the list's version, as the GPU series' own workflows install it.
- **`environment`** is `base` for every site but dp, the five brought into the one environment every site is to build with (QuantEcon/project-monorepo#77; the design note is `ideas/one-environment-for-every-site.md` in QuantEcon/project-monorepo): the full image, `ghcr.io/quantecon/quantecon:latest`, whose `anaconda=2026.07` is what every series' `environment.yml` names, with `_base/environment-update.yml` applied. A GPU site builds in it alone, on its machine (below). They moved in the owner's order of 2026-11-22: intro, advanced, then the GPU sites, programming, intermediate and jax. dp keeps the default, `series`, until its first shadow comparison, so that comparison measures the move of the build alone. Once the list covers a site's packages, its `extra_packages` retires.

## The deviations from verbatim

Every one of them, per site. A diff of a site's `_config.yml` or `_toc.yml` against the series' own file shows these and nothing else, and every line of them holds the `# site addition` marker.

| Addition | Why | Sites |
| --- | --- | --- |
| `execute: cache: _build/jupyter_cache/<key>` | The site's own execution cache, one per site as the build workflow keys it (QuantEcon/project-monorepo#77). The path is read from the directory `jb` is run from, the repository's root | all six |
| `intersphinx_disabled_reftypes: []` | A link with no target in the site resolves on the lecture's home site (QuantEcon/project-monorepo#22) | intro, programming, advanced, dp, jax (intermediate's own file already sets it) |
| `intersphinx_mapping` gains the site's own key and address | A site maps itself: a pool lecture whose home is another series writes its links into its home with the prefix (``{doc}`intermediate:linear_models` ``), and the build fails on a prefix the site does not define (the second-product spike, QuantEcon/project-monorepo#58) | programming, intermediate, advanced, jax (intro's own file already maps `intro`); not dp, below |
| `only_build_toc_files: true` | Build only the pages `_toc.yml` lists: the pool holds every series' lectures, and without it Jupyter Book builds every page in its source folder | programming, advanced (the others' own files set it) |
| `html_theme_options`: `repository_url: https://github.com/QuantEcon/lectures`, after the series' own (an override, above) | Each page's "Last changed" line and changelog are the pool's history, `git log` of `lectures/<page>.md` in this repository, so the links beside them must name it. With the series' address every commit link is a 404 and the full-history link shows the series' file, not the history listed (below) | all six |
| `_toc.yml`: `- file: mccall_risk` after `- file: mccall_fitted_vfi` | Built from the pool, dp's Job Search lectures take intermediate's current text, numbered I to IX, and `mccall_risk` is the one lecture-dp does not list. Adding it in lecture-dp would show "Job Search V" twice on the live site, whose copies are still numbered V to VIII (QuantEcon/project-monorepo#21, 2026-10-08). The shadow comparison lists the extra page and the four renumbered titles as expected differences | dp |

Two things that are not additions:

- **No site maps `dp`,** and none of the six series' files does today, so nothing was removed. dp maps no site for itself either: its key is `dp`, and it holds no lecture of its own for a prefixed link to name.
- **jax's `_config.yml` sets `only_build_toc_files` twice** (`false`, then `true`). The later one wins, as in the series' own build; it is kept verbatim.

## A page's "Last changed" line

quantecon-book-theme (0.22.2 in the build image) puts a "Last changed" date and a changelog of the page's last 10 commits on every lecture page, from `git log --follow` of the page's source in the checkout the site is built from, which is why the build checks out the full history. Built from the pool, that is this repository's history of `lectures/<page>.md`, so the theme's links take the `repository_url` override above:

| Link | What the theme builds it from | dp's `perm_income`, built locally on 2026-11-17 |
| --- | --- | --- |
| Each commit | `repository_url`, then `/commit/<hash>` | https://github.com/QuantEcon/lectures/commit/078f3b2 |
| Full history | `repository_url`, then `/commits/main/`, `path_to_docs` and the page's file (`main` is the theme's, not `repository_branch`) | https://github.com/QuantEcon/lectures/commits/main/lectures/perm_income.md |
| GitHub button | `repository_url` alone | https://github.com/QuantEcon/lectures |
| Colab | `nb_repository_url` and `nb_branch`, never `repository_url`, so unchanged | https://colab.research.google.com/github/QuantEcon/lecture-dp.notebooks/blob/main/perm_income.ipynb |

- **Readers see the pool's commits:** their subjects, authors and dates. These are the subjects of this repository's squash-merged pull requests, promotions and refreshes among them ("promote: take dp's lectures from their home series; …"), not the authors' history in the series. A site page (`intro`, `status`, …) has no line, since its staged copy is not tracked.
- **The theme's page-source link** drops `lectures/` when the repository and its source folder are both called `lectures` (QuantEcon/quantecon-book-theme#452): it finds the folder by searching the source folder's absolute path for the repository's name. Its `layout.html` keeps that link inside an HTML comment, so no reader sees it; it matters only if the theme turns it on.
- **No switch hides the line.** The theme shows it on every tracked page once `repository_url` is set. `changelog_max_entries: 0` would hide it, but the theme's `theme.conf` does not declare that option, so Sphinx warns that it is unsupported, which fails the strict build.

## Staging and building a site locally

Sphinx reads only inside its source folder, and every site's root page is called `intro.md`, so a site's own pages are copied into `lectures/` just before the build and removed after. [`tools/stage-site`](../tools/stage-site) does the copy: every `sites/<key>/<name>.md` to `lectures/<name>.md`, every file under `sites/<key>/_static/` to the same path under `lectures/_static/`, and the site's `_config.yml` and `_toc.yml` to `lectures/_config.yml` and `lectures/_toc.yml`, where `jb build lectures` finds them with no `--config` or `--toc`, and where `QuantEcon/actions`' `build-lectures` reads the configuration for its check of the executed notebooks. `site.yml` is not copied. The configuration's paths resolve as they would from the site's folder: Jupyter Book 1 reads the branding (`logo`, `html_favicon`) and the bibliography (`_static/quant-econ.bib`) against `lectures/` wherever the file sits, and the execution cache, `_build/jupyter_cache/<key>`, against the directory `jb` runs in. It never overwrites: a destination that already exists, whatever its bytes, stops the run before anything is copied. It writes what it copies, and the folders it makes, to a record outside the pool, `_build/stage-site.json` (`_build/` is ignored by git), and `--clean` removes only what that record lists, each file only while its bytes are still the ones it copied, so it can never remove a pool file. One site is staged at a time: staging refuses while a record exists.

From the repository's root, with Jupyter Book 1 and the series' packages installed (each series' `environment.yml`):

```bash
uv run --script tools/stage-site dp
jb build lectures --path-output _build/sites/dp -n -W --keep-going
uv run --script tools/stage-site --clean dp
```

Run `jb` from the repository's root, where the cache path is read from. Clean before committing, or before running `tools/pool-check` and `tools/assets-report --check-index`, which read a staged page or file as the pool's, and fail a staged `lectures/_config.yml` or `lectures/_toc.yml` (`top-level`). A lecture executes in `lectures/`, so a file it writes is left there too: dp's `short_path` writes `lectures/graph.txt`, which `--clean` does not remove (it did not stage it), and `git status` shows.

**`-n -W` is stricter than two series build today.** intro's and advanced's own publish builds run their HTML without `-n` or `-W`, and their PDF with `-n` only; programming, intermediate and jax build with `-n -W`, and dp through `QuantEcon/actions`' `build-lectures`. So a strict build of the intro or advanced site, its HTML or its PDF, may fail on warnings those series tolerate today. How strict each site's build is, is QuantEcon/project-monorepo#25's to settle per site; `site.yml` does not carry it.

To see what the build executed, run [`tools/execution-report`](../tools/execution-report) with the Python that ran `jb build`, giving it the build's start so it can tell an executed page from one taken from the cache (below):

```bash
since=$(date +%s)
jb build lectures …   # as above
python tools/execution-report --build-dir _build/sites/dp/_build --since "$since" --site dp
```

## Building a site in CI

[`site-build.yml`](../.github/workflows/site-build.yml) builds the sites named in its `SITES` list, today all six: on every push to `main` and every pull request that touches the pool, the sites, the tools a build runs, what `tools/sync` reads or the environment list in `_base/`; on demand; and on Mondays and Thursdays. Nothing is published. Each site joined the list when it was brought through (QuantEcon/project-monorepo#77). Every change to `lectures/` or `sites/` builds every named site, whatever it touched: no site is skipped yet because its toc does not reach the change.

A leg on `ubuntu-latest` runs in one of two images, by the site's `environment`: `ghcr.io/quantecon/quantecon-build:latest` (`series`) or `ghcr.io/quantecon/quantecon:latest` (`base`). Neither is public. The build job pulls with its own token and `packages: read`, as dp's own workflows do, and each package's Actions access list, in the QuantEcon organisation's package settings, must include QuantEcon/lectures; nothing in this repository can check that. Without it, the job fails in "Initialize containers" with `unauthorized`.

Each site is one leg of a matrix (`fail-fast: false`, so one site's failure stops no other). [`tools/site-matrix`](../tools/site-matrix) reads the leg's settings from `site.yml`:

| `site.yml` | What the leg takes from it |
| --- | --- |
| `runner` | `runs-on`. `ubuntu-latest` builds in a container. `g4dn.2xlarge` builds on a RunsOn machine with one NVIDIA T4, from QuantEcon's GPU machine image (by its AMI ID, as the GPU series' own `.github/runs-on.yml` give it; RunsOn reads that file from the default branch alone, and this repository has none), with no container, in the `base` environment alone: `setup-miniconda` creates `_base/environment.yml` (Python 3.13 and `anaconda=2026.07`, the full image's base), `conda env update` applies `_base/environment-update.yml`, and `jax[cuda13]` at the list's jax version is added, with a check that jax finds the GPU (the owner's choice of 2026-11-22, the shape the environment scan of 2026-11-19 proved) |
| `environment` | The container, and the file the execution cache's key hashes: `series` builds in `ghcr.io/quantecon/quantecon-build:latest`, as dp's own workflows do, keyed on `mirror/<key>/environment.yml`; `base` builds in `ghcr.io/quantecon/quantecon:latest` with `_base/environment-update.yml` applied by `QuantEcon/actions`' `setup-environment`, keyed on that list; on a GPU site, `base` is created on the machine instead, with no container (the `runner` row) |
| `cell_timeout` | The job's time limit, `timeout-minutes`: `cell_timeout` in whole minutes, the longest one cell may run, plus 150 minutes for the rest of a build from an empty cache, sized from the series' own builds (`tools/site-matrix` gives their times). `site.yml` holds no job limit of its own, since no series sets one. The per-cell limit itself stays where Jupyter Book reads it, `execute: timeout` in `_config.yml` |
| `type` | Only `series` has a leg so far |
| `publishes` | With `notebooks`, the leg also builds the site's notebooks (the `jupyter` builder, strict, from the cache the HTML build filled) and serves them at `_notebooks/`, where each page's "Download Notebook" button links. With `pdf`, it installs ImageMagick (for an SVG or GIF a page shows) and builds the site's PDF the same way (the `pdflatex` builder, strict, from the same cache) and serves it at `_pdf/`, where the theme's "Book (PDF)" link points, `/_pdf/<latex targetname>.pdf`; the leg checks that the file the pages link to is there |
| `extra_packages` | Installed with pip into the environment the build runs in, before the build, and hashed into the execution cache's key |

A leg checks the repository out with its full history. In the `series` environment it reconstructs `mirror/<key>/` at the series' pin (`tools/sync <key>`, a few seconds, for the one file the cache key hashes, `environment.yml`); in the `base` environment it applies `_base/environment-update.yml` instead (on a GPU site, after creating `_base/environment.yml` on the machine, and before adding `jax[cuda13]`), sets `PIP_ROOT_USER_ACTION=ignore` in a container (the full image runs as root, and without it every install cell's output carries pip's root-user warning, which the series' own builds do not print) and builds matplotlib's font cache, so no lecture's first plot prints that it is building it. It then installs the site's `extra_packages`, records the environment as installed (`pip freeze`), restores the site's execution cache, stages the site, and builds it with `QuantEcon/actions`' `build-lectures`: `builder: html`, `source-dir: lectures` and `extra-args: -W --keep-going` (`build-lectures` adds `-n`), with the staged `_config.yml` and `_toc.yml`. So a warning, a cell that raises, a reference that does not resolve, or a label that two of the site's lectures both define fails the build, and `--keep-going` lists every failure, not only the first. It then writes the execution report, keeps the HTML (`html-<key>`, after a green build, for 7 days) and the report with the environment record (`execution-status-<key>`) as artefacts, saves the cache and unstages the site. A failed build also uploads `build-lectures`' failure reports (`execution-reports-<key>`): each failed page's traceback, from `_build/html/reports/`. They do not include the site's execution cache: `build-lectures` collects `_build/.jupyter_cache`, and a site's cache is at `_build/jupyter_cache/<key>`.

**The execution cache** is `actions/cache`, one per site, at the path the site's `_config.yml` names, `_build/jupyter_cache/<key>` (rule 7). A cache is never overwritten, so each one is saved under a new key, `jb1-<key>-<tag><env hash>-<packages hash>-<image hash>-<run>`: the tag, empty in the `series` environment and `base-` in the `base` one, so the two never share a cache; the hash of `mirror/<key>/environment.yml`, whole (`series`), or of `_base/environment-update.yml`'s entries, its lines without comments or blank lines (`base`), so editing a comment there keeps the key; the hash of the site's `extra_packages` (`none` without them); the hash of the image's `/etc/quantecon-container`, which names the image and when it was built (the images are built only when their Dockerfiles change, so a new hash is a new image), or on a GPU site the hash of RunsOn's machine spec, which names the machine image by its AMI ID, and of `_base/environment.yml`'s entries; and the run. A restore takes the newest cache saved under the same tag and hashes; there is no fallback to another key's cache. A pull request only restores. A run on `main` saves after a green build that executed at least one page; one that took every page from the cache has nothing new to save. The twice-weekly run keeps each cache in use, since GitHub drops a cache that is not read for 7 days; with every page in the cache it executes nothing, so it checks the current image's Sphinx stack and the pages' rendering, not their execution.

- **What the key catches:** a change to the file it hashes (in `base`, to an entry of the list), to the site's `extra_packages` or to the image starts an empty cache, so every page is executed again. In the `series` environment the build never installs `environment.yml`, whose packages come from the image: the file only names the environment the series declares, as in dp's own cache keys. In the `base` environment the list it hashes is what the build installs.
- **What it does not catch:** an extra package such as jax comes from the newest release pip finds, so a new release keeps the key; and on a GPU site, the CUDA libraries `jax[cuda13]` brings are not pinned. A page is executed again only when its own code changes (jupyter-cache matches a page by its code cells) or the key does.
- **Cold builds:** until a run on `main` has saved a cache under the current key, every build of a site executes every page (dp: about 50 pages, 20 to 40 minutes). Every pull request before the workflow's first green run on `main` builds cold, every time it runs, and so does every build after the key changes, until `main` saves again.
- **Showing the restore** (QuantEcon/project-monorepo#25 asks for it): a pull request never saves, so its own runs cannot show one. It is shown after the merge: the merge's push to `main` builds cold and saves, then a manual run on `main` (or the schedule) restores that cache, which the run's summary names and the execution report counts, every page cached and none executed.

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
7. **The additions a build needs stay:** every site sets `only_build_toc_files: true`, its own cache, `execute.cache: _build/jupyter_cache/<key>`, and the theme's `repository_url: https://github.com/QuantEcon/lectures` with `path_to_docs: lectures` (the value the build reads, whatever the series' line says), and `_config.yml` is well formed where these rules read it.

## Keeping the copies true to the series

A site's files are copies of its series' files, so they follow the series until its cutover. After every sync the drift-check ([`tools/drift-check`](../tools/drift-check)) compares every file in each series' site folder but `site.yml` with the series' `lectures/<path>` at the pin: the pages and the `_static/` files byte for byte, and `_config.yml` and `_toc.yml` with every `# site addition` line removed. Each file that differs, or that the series no longer has, is `site-stale`, a `drift` finding: the nightly run opens an issue for it, with the diff, and closes the issue once the copy matches again. To settle one, copy the series' file at the pin over the site's and put back the lines marked `# site addition`. A change the site must not take is a decision to record here, as a marked addition, not a copy to leave stale.
