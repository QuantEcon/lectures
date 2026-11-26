# QuantEcon Lectures — monorepo

> **Status: being prepared — nothing here is published yet.** The QuantEcon lectures still live at their individual series sites, linked below: read and cite those. This repository holds a shared pool of lectures mirrored from those series, and the tooling that keeps the pool faithful to them, while the move into this repository is prepared one series at a time.

This repository is the future single source of truth for the QuantEcon lecture series. The goal is to hold every canonical lecture **exactly once** in a shared pool, and to build each published series or course from a thin configuration that selects and orders pool lectures — never from a copy.

It sits **downstream** of six live lecture repositories until each one deliberately cuts over. What exists today:

- **The pool:** 335 lectures in `lectures/`, promoted from the series together with the figures and files they use, each with its provenance recorded in [`sync/ledger.yml`](sync/ledger.yml).
- **The mirror:** every series' lectures, reconstructed on demand from commits pinned in [`sync/state.yml`](sync/state.yml), which a daily job keeps current.
- **The drift-check:** run after every sync, it proves each pool lecture still equals its source, opens a pull request to refresh the pool when a source moves, and opens an issue when another series' copy diverges.
- **The promote tool:** it brings lectures into the pool and refuses a lecture name that two series use for different lectures.
- **The merged bibliography:** one [`lectures/_static/quant-econ.bib`](lectures/_static/quant-econ.bib), generated from the series' own files and the rulings in [`sync/bib.yml`](sync/bib.yml), and refreshed with the pool.
- **The assets report:** after every sync, an audit of the files beside the lectures, in every series and in the pool, and a generated index of who uses each shared file, [`lectures/_static/_shared/README.md`](lectures/_static/_shared/README.md).
- **The sites:** one folder per published site in [`sites/`](sites/README.md), each holding its series' `_config.yml` and `_toc.yml` verbatim with the few additions a build from the pool needs, its own pages and branding, and the fields the build workflow reads.

See [The plan](#the-plan) for what comes next.

## Where the lectures actually live (for now)

Until each series is deliberately cut over, the live sites below remain authoritative. Read and cite those, not this repository.

| Key | Live site | Source series |
| --- | --- | --- |
| `intro` | https://intro.quantecon.org | QuantEcon/lecture-python-intro |
| `programming` | https://python-programming.quantecon.org | QuantEcon/lecture-python-programming |
| `intermediate` | https://python.quantecon.org | QuantEcon/lecture-python.myst |
| `advanced` | https://python-advanced.quantecon.org | QuantEcon/lecture-python-advanced.myst |
| `dp` | https://quantecon.github.io/lecture-dp/ (planned: https://dynamic-programming.quantecon.org) | QuantEcon/lecture-dp |
| `jax` | https://jax.quantecon.org | QuantEcon/lecture-jax |

## The four posture rules

These rules govern how this repository relates to the six live series until each one cuts over.

1. **Read-only, with stated exceptions.** This repository only reads from the live series. Changes in the series themselves are limited to ordinary lecture maintenance, the renames that make every lecture name unique across the published sites (each with a redirect from the old address), and two merges that reconcile lectures two series share. Each is its own reviewed pull request in that series. A series receives the workflow that publishes it from here at its cutover and not before, and no engine or layout change is made in a live series before its own cutover.
2. **The live repos remain the source of truth.** Each live series stays authoritative until a deliberate, per-series cutover moves it here. Nothing is migrated implicitly.
3. **After its cutover, a series is edited here.** Until then, its lectures are edited in the series repository and reach the pool by sync. At its cutover, the pool becomes its source of truth.
4. **Shadow build, then cut over.** Before a series moves, this repository builds it from the pool and compares the result with the series' own published build, with nothing going live. Each cutover is decided once the builds match.

## The mirror → pool → sites model

The repository is organised around three layers.

| Layer | What it is | State today |
| --- | --- | --- |
| `mirror/<key>/` | A machine-reconstructed, verbatim copy of each live series' allowlisted paths, pinned to an exact commit. Never hand-edited, never committed. | Reconstructed on demand; **gitignored**. |
| `lectures/` | The curated **pool** — every canonical lecture, held exactly once. | 335 lectures and their assets, each recorded in [`sync/ledger.yml`](sync/ledger.yml). |
| `sites/` | One folder per published site, each a thin **configuration** that selects and orders lectures from the pool. | One per series, six in all, with the rules in [`sites/README.md`](sites/README.md); [`site-build.yml`](.github/workflows/site-build.yml) builds `dp`, `intro`, `advanced` and `programming` from them, and the other two follow. |

### Why we commit only SHAs, not the mirror

`mirror/<key>/` is a pure function of three inputs: the source **repo**, a **pinned commit SHA**, and the **allowlist** of paths to take from it (`lectures/` and `environment.yml`). Because the mirror is fully determined by those inputs, we commit **only the pinned SHAs** (in [`sync/state.yml`](sync/state.yml)) and rebuild the mirror on demand. The repository therefore carries no heavy verbatim history, and the mirror can always be reconstructed byte-for-byte.

- **Human intent** — which repos feed the mirror — lives in [`sync/manifest.yml`](sync/manifest.yml).
- **Machine state** — the exact SHA each series is pinned to — lives in [`sync/state.yml`](sync/state.yml), written by the sync tool.

## Directory layout

```
.
├── _base/            # what every site shares: environment-update.yml, the one pinned environment
│                     #   the sites are to build in (see _base/README.md)
├── lectures/         # the pool: every canonical lecture once
│   └── _static/      #   their assets: _static/<slug>/ per lecture, _static/_shared/ for shared files
│                     #   (with README.md, its generated index of users), and quant-econ.bib, the
│                     #   merged bibliography (bib-merge-written)
├── sites/            # one folder per published site: its _config.yml, _toc.yml, site.yml,
│                     #   own pages and branding (see sites/README.md)
├── mirror/           # reconstructed, verbatim, GITIGNORED — never committed
├── docs/tech/        # the technology register (see below)
├── sync/
│   ├── manifest.yml  # human intent: which repos feed the mirror, and each series' class
│   ├── canonical.yml # human intent: the winning series for a same-name collision
│   ├── bib.yml       # human intent: the rulings that settle the bibliographies' conflicts
│   ├── state.yml     # machine state: pinned SHAs (sync-written)
│   ├── ledger.yml    # machine state: provenance of every pool lecture and asset (promote-written)
│   └── toc.yml       # machine state: the watched _toc.yml baselines (drift-check-written)
├── tools/
│   ├── sync          # reconstructs the mirror from pinned SHAs
│   ├── promote       # promotes lectures + their asset closure into the pool; writes the ledger
│   ├── drift-check   # proves the pool still equals its sources; issues, refresh PR
│   ├── bib-merge     # merges the series' bibliographies into the pool's one file; checks it
│   ├── pool-check    # checks the pool keeps its layout conventions, and the environment lists what it installs
│   ├── assets-report # audits the files beside the lectures; writes and checks the _shared/ index
│   ├── stage-site    # copies one site's pages, files, _config.yml and _toc.yml into lectures/ for a build, and out again
│   ├── site-matrix   # reads each built site's site.yml into the build workflow's matrix
│   ├── execution-report # after a build: what it executed or took from the cache, page by page
│   └── tests/        # pytest suite for the tools above (scratch repos)
└── .github/workflows/
    ├── sync.yml         # daily job that refreshes the pinned SHAs (pin-only)
    ├── drift-check.yml  # runs after sync: drift issues, refresh PR (pool and bibliography), red on a pool edit or a refused refresh; the assets report
    ├── pool-check.yml   # runs tools/pool-check and the _shared/ index check on pull requests that touch the pool or the sites
    ├── publish.yml      # by hand: builds one site with site-build.yml and releases it in its target repository with the App's token (a test double until the site's cutover)
    ├── site-build.yml   # builds the sites it names (four today) from the pool, strict, HTML; keeps the HTML and the execution report; publishes nothing
    └── tests.yml        # runs tools/tests on pull requests
```

## Running the sync

[`tools/sync`](tools/sync) reconstructs the mirror and refreshes the pinned SHAs. It is a self-contained script run via [uv](https://docs.astral.sh/uv/) — its dependencies are declared inline (PEP 723), so there is nothing to install first. Invoke it either directly (`./tools/sync …`, once the executable bit is set) or through uv (`uv run --script tools/sync …`), which needs no executable bit.

The tool **never commits anything**; committing a refreshed `sync/state.yml` is CI's job.

| Command | What it does |
| --- | --- |
| `tools/sync` | Reconstruct **every** series into `mirror/<key>/` at its already-pinned SHA. |
| `tools/sync dp` | Reconstruct only the `dp` series. Any subset of keys works. |
| `tools/sync --update` | Re-resolve each series' `HEAD`, re-pin the SHA (with a UTC timestamp) into `sync/state.yml` when it has moved, then reconstruct. |
| `tools/sync --update --pin-only` | Re-resolve and re-pin SHAs but **skip** reconstruction — no downloads. This is what CI runs. |
| `tools/sync --update dp jax` | Re-pin and reconstruct just `dp` and `jax`. |
| `tools/sync -h` | Full help. |

A series' pin (and its timestamp) is only rewritten when the upstream `HEAD` has actually moved, so a re-pin run over unchanged series leaves `sync/state.yml` untouched. If a series has no pinned SHA yet, a plain `tools/sync` reports a clear error and suggests running `--update` first. Failures are per-series: the tool logs each and carries on, then prints a `PASS`/`FAIL` summary and exits non-zero if any series failed.

## Promoting lectures

[`tools/promote`](tools/promote) copies lectures from the mirror into the pool together with their asset closure — the figures, includes and data files a lecture actually references — and records where each came from in `sync/ledger.yml`. Asset references are rewritten to the pool's `_static/` layout, and every rewrite is recorded, so the pool copy can always be reproduced from its source. Like the other tools it is a self-contained uv script, and it never commits anything or touches the mirror.

| Command | What it does |
| --- | --- |
| `tools/promote SLUG …` | Promote the named lectures, each from the highest-priority series that holds it. |
| `tools/promote --toc SERIES` | Promote every lecture in a series' `_toc.yml`. For a consumer series (`dp`), each lecture comes from its home series. |
| `tools/promote --refresh` | Re-promote every entry whose canonical series has moved since it was promoted. CI adds `--exclude $PROMOTE_EXCLUDE` when that list names a series; it is empty now that every series is promoted. |
| `tools/promote --retire SLUG …` | Take the named lectures out of the pool: the pool file and its ledger entry, with the assets no other pool lecture uses. |
| `tools/promote … --exclude SERIES …` | Leave the named series out of this run. |
| `tools/promote … --dry-run` | Print the full plan without writing anything. |

`tools/promote` refuses a lecture name held by two canonical-eligible series with different text, naming the lecture and every series involved. It does not pick a winner by run order. A rename or merge upstream fixes it; until then, [`sync/canonical.yml`](sync/canonical.yml) can name the winning series, and the entry is recorded as `interim`. A copy that is merely stale (a recorded source still at a version the pool already took, while the canonical copy moved on) is not a collision: it stays a source, and the refresh goes through. A `sync/canonical.yml` line that names such a stale copy is refused, though, since following it would take the pool back to the lagging text, so delete a line as soon as promote reports that it settles nothing.

### A lecture renamed or removed upstream

A pool lecture whose canonical copy is gone upstream is reported by the drift-check as `canonical-removed`. The daily refresh skips it and refreshes the rest; it never removes a lecture. The lecture leaves the pool by being **retired**:

- `tools/promote --toc SERIES` retires, on its own, each entry canonical in `SERIES` whose lecture has left that series' `_toc.yml`, whose canonical copy is gone, and whose name no series in the manifest still holds. A renamed lecture is retired under its old name and promoted under its new one by the same run. At most five lectures are retired this way in one run: more than that retires none and fails, naming them, since a toc or folder lost upstream by mistake must not empty the pool.
- `tools/promote --retire SLUG …` retires by name, for anything the rule above leaves alone, such as a lecture a consumer series still holds. It refuses a lecture its canonical series' toc still lists.

Afterwards re-accept the toc with `tools/drift-check --accept-toc SERIES`. Retirement only ever acts on an entry whose canonical series is in `sync/manifest.yml`, so it never touches the lectures of a series the pool has taken over. Git history and the run's summary are the record of a retirement.

### A file that lectures share

The pool keeps one copy of an asset, used by every pool lecture that refers to it, while the series those lectures come from each carry their own. Today that is the `_admonition/gpu.md` include (55 lectures from three series), `duopoly_mpe.py` (a lecture from intermediate and one from advanced) and the four `arellano` figures (advanced and jax). An asset's ledger record lists as `sources` its copies in the series its user lectures come from, and only those: a series that merely has a file of the same name is not watched.

- **One series changes the file first.** When a series whose copy was the pool's version changes it, the refresh takes the new version for every lecture that uses the file, whether or not those lectures are in the refresh. The other series' copies are recorded on the asset as stale, each with its own `digest` and a `stale_since` time. The drift-check reports a stale copy as information for seven days and as drift, with an issue, after that; the copy is current again at the first refresh after its series makes the same change (the drift-check asks for that refresh, as `asset-caught-up`, so the record never goes on calling a copy stale that has caught up).
- **A different file under the same name.** A copy that was never the pool's version, because it already differs when it is first seen, is not a lagging copy. It is recorded on the asset with `differs: true`, reported as information (`differing-copy`), and never followed; a lecture that comes only from that series and uses the name gets its own series' file, at its own pool path.
- **Only copies behind a lecture count.** A series' copy is followed while its copy of a user lecture is still the lecture the pool recorded. If that lecture copy is edited to differ, the drift-check reports the lecture, and the series' copy of the file is not followed until the lecture is settled.
- **What is refused.** Two series that change the file differently; a stale copy that changes to anything but the pool's version (a copy that is behind may only catch up); a copy in a series not yet recorded that differs; and overwriting or moving a shared pool file that was edited by hand (a lecture's own file, with nothing else changing, is restored by re-promoting that lecture).
- **Lectures that share a file stay together.** A shared file is never split across two pool paths: a lecture outside the batch counts as a user of the version the batch brings. When a file's pool path must change, because a second lecture starts to use it, promote pulls the lectures that already use it into the batch and re-promotes them with it; if one of them cannot be re-promoted, the lecture that needed the move is refused too, with the reason.
- **Two lectures that bring different bytes to one new pool path** are both refused, naming both, whatever order they were given in.

One consequence of keeping a single file: a lecture whose own refresh is refused keeps its old text while a file it shares moves on with the lectures that did refresh. For a `.py` file a lecture loads, that pairs text and code no series published together, until the refused lecture is settled.

## Running the drift-check

[`tools/drift-check`](tools/drift-check) proves the pre-cutover invariant: every pool lecture equals its canonical mirror copy modulo the rewrites recorded in `sync/ledger.yml`, and every other series' copy is where the ledger last saw it. Like `tools/sync` it is a self-contained uv script. It never writes to the pool or the mirror: the only repository file it writes is `sync/toc.yml`, under `--accept-toc`; `--json` writes its report wherever you point it, and under GitHub Actions it appends step outputs.

| Command | What it does |
| --- | --- |
| `tools/drift-check` | Report against the existing `mirror/`. Exit 0 clean, 1 findings, 2 a pool file was edited directly. |
| `tools/drift-check --reconstruct` | Rebuild `mirror/` first, for every series the check reads: every canonical-eligible series, and a consumer whose toc is watched. |
| `tools/drift-check --print-issues` | Show the issues `--issues` would open, without touching GitHub. |
| `tools/drift-check --issues` | Open, update and close `drift` issues to match the findings (CI). |
| `tools/drift-check --accept-toc dp` | Record a series' `_toc.yml` at its current pin as the watched baseline. |

Four outcomes: **refresh** (the canonical copy moved upstream; CI runs `promote --refresh` and opens a pull request; an entry the refresh refuses is listed with promote's reason, in that pull request when one is opened and always in the red run's refresh step; the usual reason is a same-name copy edited to differ, which `sync/canonical.yml` or upstream settles; while the entry's canonical copy differs from its ledger record the run stays red every night until it is settled, and a settlement applies the next night), **drift** (a non-canonical copy diverged from its canonical home, a copy was removed, a watched toc changed or lists a lecture the pool does not hold, or two published sites hold different lectures under one name, or a site's copy of its series' files no longer matches them, `site-stale`, described in [`sites/README.md`](sites/README.md); each becomes an issue that closes itself when the finding clears), **violation** (the pool itself was edited; the job goes red), and **info** (a copy is merely stale, or a divergence converged). [`drift-check.yml`](.github/workflows/drift-check.yml) runs it after every `sync`.

One kind of copy is never watched. A **consumer** series (`class: consumer` in `sync/manifest.yml`, today `dp`) only republishes other series' lectures, so its copies are recorded as `superseded` and are expected to go stale. Its `_toc.yml` is watched, though: the pool's `dp` selection is promoted from it, so a change there means re-running that promotion with the refresh's exclusions (`PROMOTE_EXCLUDE` in [`drift-check.yml`](.github/workflows/drift-check.yml); today `tools/promote --toc dp --exclude jax`), then `--accept-toc dp`. Accepting alone clears that issue but leaves a newly listed lecture out of the pool, which the check then reports as `toc-unpromoted`.

Lecture names are unique across the published sites, not only in the pool: a link that leaves a site resolves by name, so two sites that publish different lectures under one name send readers to the wrong one. The check reads every canonical-eligible series' `_toc.yml`, whether its lectures are in the pool yet or not, and a name two of them list must be one lecture in both, by promote's rule (`name-shared`). A consumer's toc is not read for this: it only republishes.

## Checking the pool's layout

[`tools/pool-check`](tools/pool-check) checks that the pool keeps the layout `tools/promote` writes, whoever edits it next. `lectures/` holds lectures (`<slug>.md`, no name starting with `_`, no two names that differ only in case) and `_static/`. Every folder at the top of `_static/` is a lecture's own (`_static/<slug>/`, beside `<slug>.md`) or `_shared/`, and the merged bibliography is the one file there. A file in `_static/<slug>/` is used by `<slug>.md` alone, so an asset two lectures use goes in `_shared/`. Every asset reference is file-relative (`_static/<slug>/fig.png`, never `/_static/...`) and stays inside `lectures/`. Every `{doc}` link resolves: a plain target names a pool lecture or a site page, and a prefixed one (`intro:cobweb`) has a series key from `sync/manifest.yml` as its prefix and, after it, a site page or a pool lecture that series holds by the ledger. Three older prefixes (`dynam`, `pyprog`, `tools`) are accepted until the cross-reference policy settles what a link that leaves the site is written as. So a refresh that brings in a link to a lecture the pool does not hold yet fails this check until that lecture is promoted. It finds asset references with promote's own parser and `{doc}` links with its own pattern (text in code cells, literal blocks, inline literals and comments is not read as a link), reads `lectures/`, the series keys in `sync/manifest.yml` and the ledger's record of which series hold a lecture, and needs no mirror. Exit 0 clean, 1 a rule broken, 2 an error.

It also counts the labels that more than one pool lecture defines, targets (`(name)=`, `:name:`) and equation labels (`:label:`, `$$ … $$ (name)`) apart, and `tools/pool-check --labels` lists them. That is information, never a failure: labels must be unique within a site, which is checked where a site is built.

It checks the sites too, so each folder in `sites/` stays true to the pool: every entry in a site's `_toc.yml` is a pool lecture or a page of the site; a site page never has a pool lecture's name, and no file under a site's `_static/` is a pool file, since staging would overwrite it; the branding a site's `_config.yml` names is in the site; the site sets `only_build_toc_files: true`, its own execution cache (`_build/jupyter_cache/<key>`) and `intersphinx_disabled_reftypes: []`, maps no consumer series and, unless it is one, maps itself; and `site.yml` has the fields the build reads, each with a valid value. The rules and the fields are in [`sites/README.md`](sites/README.md). [`pool-check.yml`](.github/workflows/pool-check.yml) runs it on every pull request that touches the pool or the sites. Run it with no site staged: a staged site's pages in `lectures/` read as pool lectures.

And it keeps the one environment the sites are to build in, [`_base/environment-update.yml`](_base/environment-update.yml), whole: every package a pool lecture's code cells install (`!pip install`, `%pip install`, `!conda install`, and the other forms its docstring lists) is listed there, pinned to one version that a pip install line's own version limit allows, and every entry is pinned to one version, once. So a refresh that brings in a lecture installing a new package turns this check red (a red check, since `main` has no branch protection) until a person pins it there, in a pull request of its own to `main`. It also counts, as information, the installs in executed cells that would replace a pin during a build (`--upgrade`, `-U`, a conda install), and `tools/pool-check --installs` lists them. Why the list is pinned, where each pin comes from, and how to add one, is in [`_base/README.md`](_base/README.md).

## The assets report

[`tools/assets-report`](tools/assets-report) is the audit of static assets, regenerated after every sync rather than written once. [`drift-check.yml`](.github/workflows/drift-check.yml) runs it on the mirror the drift-check rebuilds and puts the report in the run's summary and in an `assets-report` artefact (Markdown and JSON). It is information and never fails that run. It reports:

- **Per series,** every file under the series' `lectures/` that is not a lecture or its `_config.yml` or `_toc.yml`: used by a lecture (by promote's parser, including through an include), linked by address (a lecture links to it in the series' own repository on GitHub), used by the configuration (named in `_config.yml`, branding, or the bibliography), or orphaned. Orphaned figure sources are counted apart: a `.tex`, `.gv` or `.dot` file, a file named like an image a lecture uses in the same folder, less the extension, or a notebook in a folder that holds such an image.
- **Collisions:** one path in two or more series with different bytes.
- **The largest files,** the candidates for trimming a dataset.
- **The pool:** every file under `lectures/_static/`, the lectures that use it (by its text, or by the asset list in its ledger entry), the orphans and the `_shared/` files one lecture alone uses. Files under a name starting with `.`, such as `.DS_Store`, are not the pool's and are skipped.
- **Files on GitHub, by address:** every link in a pool lecture to a file on GitHub, by repository and the ref it names. Most are data the lectures read from [QuantEcon/data-lectures](https://github.com/QuantEcon/data-lectures) on its default branch; a link into a series' own repository breaks if the series moves the file at its cutover.

It also writes [`lectures/_static/_shared/README.md`](lectures/_static/_shared/README.md): for each shared file, the pool lectures that use it and the series that publish them, by the ledger. GitHub shows it under the folder, so whoever changes a shared file sees what it reaches. It is generated, never edited by hand: [`pool-check.yml`](.github/workflows/pool-check.yml) regenerates it and fails a pull request whose copy differs, and fails on an orphan, a file under `_static/` that no pool lecture uses. Its path is reserved: if the ledger records an asset there, the tool stops with an error. A `_shared/` file that one lecture alone uses is listed, not failed: promote places a family folder's files and the `_admonition/` includes there whatever their count. The nightly refresh regenerates the index with the pool; after promoting by hand, run `tools/assets-report --write-index` and commit the result.

| Command | What it does |
| --- | --- |
| `tools/assets-report` | Print the report as Markdown. It needs the mirror. |
| `tools/assets-report --out report.md --json report.json` | Write the report to files. |
| `tools/assets-report --reconstruct` | Rebuild `mirror/` first. |
| `tools/assets-report --write-index` | Regenerate `lectures/_static/_shared/README.md`. It reads the pool and the ledger only. |
| `tools/assets-report --check-index` | Exit 1 if the index is stale or missing, or the pool holds an orphan; 0 clean, 2 an error. |

## The sites

Each published site is a folder in [`sites/`](sites/README.md): its series' `_config.yml` and `_toc.yml`, verbatim but for the additions recorded there, its own pages (`intro`, `status` and the like, which are never pool lectures), its branding, and `site.yml`, the fields the build workflow reads (type, runner class, `cell_timeout`, the per-cell execution limit, what it publishes, its address). A site is built from the pool after [`tools/stage-site`](tools/stage-site) copies its own pages and files, its `_config.yml` and its `_toc.yml` into `lectures/`, since Sphinx reads only inside its source folder:

| Command | What it does |
| --- | --- |
| `tools/stage-site dp` | Copy dp's pages, `_static/` files, `_config.yml` and `_toc.yml` into `lectures/`, recording what it copied in `_build/stage-site.json`. It refuses, copying nothing, if any destination already exists, or if a site is staged already. |
| `tools/stage-site --clean dp` | Remove them again: only the files the record lists, each while its bytes are still the ones copied, then the record. |

[`site-build.yml`](.github/workflows/site-build.yml) builds the sites it names, today `dp`, `intro`, `advanced` and `programming`, on every push to `main` and pull request that touches the pool, the sites, the tools a build runs or the environment list in `_base/`, on demand and twice a week. Each site is a leg of one matrix whose runner, container and time limit [`tools/site-matrix`](tools/site-matrix) reads from `site.yml`. A leg builds in the site's environment: dp in its series' own image, with the site's `extra_packages` (jax) installed; intro and advanced in the full image with the one package list, `_base/environment-update.yml`, applied; programming on a RunsOn GPU machine with the same base and list, and `jax[cuda13]` (see [`_base/README.md`](_base/README.md)). It stages the site, builds its HTML strictly (`-n -W --keep-going`) with `QuantEcon/actions`' `build-lectures`, restoring and, on `main`, saving the site's own execution cache, and keeps the HTML and the execution report as artefacts. It publishes nothing. A pull request only restores the cache, so until `main` has saved one, every build executes every page.

| Command | What it does |
| --- | --- |
| `tools/site-matrix dp` | Print the matrix entry for each site named, as JSON. It refuses a site whose runner class or type has no leg yet. |
| `python tools/execution-report --since "$since" --site dp` | After `jb build`, write `_build/execution_status.json`: one row per page the build executed or took from the cache, with its status, seconds, kernel and which of the two. Run it with the Python that ran the build: it reads Sphinx's environment. |

[`sites/README.md`](sites/README.md) has the `jb build` command, the build in CI and its cache, the execution report's fields, every deviation from the series' files and why, and the cross-reference rules.

## Running the bibliography merge

[`tools/bib-merge`](tools/bib-merge) builds the pool's one bibliography, `lectures/_static/quant-econ.bib`, from the `quant-econ.bib` of each series listed in [`sync/bib.yml`](sync/bib.yml). A consumer series such as `dp` is never a source, and the tool refuses one that is listed: its lectures are copies of other series' lectures, and its bibliography is a copy too. Each series' copy of an entry is normalised to the house style's mechanical rules ([Writing a bibliography entry](https://manual.quantecon.org/styleguide/references.html#writing-a-bibliography-entry)): page ranges with `--`, no `month`, a bare DOI, no fields a reader never sees, one field per line. Nothing else in a value changes. Copies that then agree are merged into one entry. Copies that still differ are a conflict, and `sync/bib.yml` must rule on it: which series' copy to take, any fields to set or drop, why, and a seal recording each copy as it was. If a series later edits a sealed copy, the copy the ruling takes included, the ruling reopens; the change is never folded in silently. The file is generated, never edited by hand: its header records digests of the series' entries, of `sync/bib.yml` and of its own entries, so the check tells a series that moved (a refresh) from a hand edit or a ruling that was not regenerated (a violation).

| Command | What it does |
| --- | --- |
| `tools/bib-merge` | Regenerate in memory and check. Exit 0 clean, 1 the series' files moved (run `--write`), 2 a refused key, a failed check, or a committed file that differs from what the same inputs generate. |
| `tools/bib-merge --write` | Write `lectures/_static/quant-econ.bib`. |
| `tools/bib-merge --report` | Print every conflict side by side, with its ruling or why it was refused. |
| `tools/bib-merge --propose` | Print a `sync/bib.yml` stub, sealed against the current copies, for every refused key. |
| `tools/bib-merge --reconstruct` | Rebuild `mirror/` for every series first. |

Its checks: every key a pool lecture cites resolves (in the nightly check, `--refresh-follows` makes one exception: a key cited only by lectures whose canonical copies have dropped the citation upstream is information, because the refresh that follows removes it and the write after it checks again); the entries keep the house-style rules the normalising cannot apply (the fields each entry type needs, names joined by `and`, keys unique when case is ignored); and pybtex, the reader Jupyter Book 1 uses, reads every merged entry as it reads the series copy it came from. It reads the series' files exactly or refuses them: a syntax error, a duplicate key or field, `@string`, a `#` concatenation, or a file in which bibtexparser and pybtex find different keys stops the run, and nothing is written that does not read back as the same entries. [`drift-check.yml`](.github/workflows/drift-check.yml) runs it after every sync and refreshes the file into the same pull request as the pool; anything it fails on turns that workflow's `bibliography` job red, which never holds back the pool's refresh.

## The technology register

[`docs/tech/`](docs/tech/) is a standing record of technology options for improving the lectures: what was looked at, the named files where it would apply, and what was decided and why. An entry is not ready until it names the files it would change; [its README](docs/tech/README.md) sets out the format and the states an entry moves through.

## The plan

The move is planned in ten stages: reorganise first on today's toolchain (Jupyter Book 1), then switch the engine once, later.

1. **Set up** access and tracking.
2. **Sources in.** Bring every lecture of every series into the pool, reconciling differences in the series repositories.
3. **One publishing workflow** that builds any site on either engine, rehearsed end to end, including a rollback, on a sandbox series.
4. **Shadow builds.** Build each series here from the pool and compare it with its own published build, with nothing going live.
5. **Cutovers, one series at a time.** Each series is published through a release in its own repository, so every earlier release is a rollback.
6. **The order of cutovers:** `dp` (a publishing-only move, since it owns no lectures), programming, a go/no-go review, then intro, intermediate, advanced and JAX.
7. **A relay** that keeps the translated editions fed from here.
8. **Page history**, carried across at each cutover.
9. **mystmd builds alongside**, from stage 3, publishing nothing.
10. **One engine switch** for all series and editions together, after full testing.

As of October 2026, stage 2 is under way. The promote tool is ready, and the renames that make lecture names unique come next.

## Licence

To be confirmed; the mirrored content remains under the licences of its respective source series until cutover.
