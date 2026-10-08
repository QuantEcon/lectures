# QuantEcon Lectures — monorepo

> **Status: being prepared — nothing here is published yet.** The QuantEcon lectures still live at their individual series sites, linked below: read and cite those. This repository holds a shared pool of lectures mirrored from those series, and the tooling that keeps the pool faithful to them, while the move into this repository is prepared one series at a time.

This repository is the future single source of truth for the QuantEcon lecture series. The goal is to hold every canonical lecture **exactly once** in a shared pool, and to build each published series or course from a thin configuration that selects and orders pool lectures — never from a copy.

It sits **downstream** of six live lecture repositories until each one deliberately cuts over. What exists today:

- **The pool:** 52 lectures in `lectures/`, promoted from the series together with the figures and files they use, each with its provenance recorded in [`sync/ledger.yml`](sync/ledger.yml).
- **The mirror:** every series' lectures, reconstructed on demand from commits pinned in [`sync/state.yml`](sync/state.yml), which a daily job keeps current.
- **The drift-check:** run after every sync, it proves each pool lecture still equals its source, opens a pull request to refresh the pool when a source moves, and opens an issue when another series' copy diverges.
- **The promote tool:** it brings lectures into the pool and refuses a lecture name that two series use for different lectures.

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

## The mirror → pool → products model

The repository is organised around three layers. The first two exist today.

| Layer | What it is | State today |
| --- | --- | --- |
| `mirror/<key>/` | A machine-reconstructed, verbatim copy of each live series' allowlisted paths, pinned to an exact commit. Never hand-edited, never committed. | Reconstructed on demand; **gitignored**. |
| `lectures/` | The curated **pool** — every canonical lecture, held exactly once. | 52 lectures and their assets, each recorded in [`sync/ledger.yml`](sync/ledger.yml). |
| `products/` | One folder per published product, each a thin **configuration** that selects and orders lectures from the pool. | Empty: each series' configuration arrives with the publishing workflow. |

### Why we commit only SHAs, not the mirror

`mirror/<key>/` is a pure function of three inputs: the source **repo**, a **pinned commit SHA**, and the **allowlist** of paths to take from it (`lectures/` and `environment.yml`). Because the mirror is fully determined by those inputs, we commit **only the pinned SHAs** (in [`sync/state.yml`](sync/state.yml)) and rebuild the mirror on demand. The repository therefore carries no heavy verbatim history, and the mirror can always be reconstructed byte-for-byte.

- **Human intent** — which repos feed the mirror — lives in [`sync/manifest.yml`](sync/manifest.yml).
- **Machine state** — the exact SHA each series is pinned to — lives in [`sync/state.yml`](sync/state.yml), written by the sync tool.

## Directory layout

```
.
├── _base/            # (later) shared toolchain defaults — placeholder
├── lectures/         # the pool: every canonical lecture once
│   └── _static/      #   their assets: _static/<slug>/ per lecture, _static/_shared/ for shared files
├── products/         # (later) one configuration per published product — empty
├── mirror/           # reconstructed, verbatim, GITIGNORED — never committed
├── docs/tech/        # the technology register (see below)
├── sync/
│   ├── manifest.yml  # human intent: which repos feed the mirror, and each series' class
│   ├── canonical.yml # human intent: the winning series for a same-name collision
│   ├── state.yml     # machine state: pinned SHAs (sync-written)
│   ├── ledger.yml    # machine state: provenance of every pool lecture and asset (promote-written)
│   └── toc.yml       # machine state: the watched _toc.yml baselines (drift-check-written)
├── tools/
│   ├── sync          # reconstructs the mirror from pinned SHAs
│   ├── promote       # promotes lectures + their asset closure into the pool; writes the ledger
│   ├── drift-check   # proves the pool still equals its sources; issues, refresh PR
│   └── tests/        # pytest suite for promote and drift-check (scratch repos)
└── .github/workflows/
    ├── sync.yml         # daily job that refreshes the pinned SHAs (pin-only)
    ├── drift-check.yml  # runs after sync: drift issues, refresh PR, red on a pool edit or a refused refresh
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
| `tools/promote --refresh` | Re-promote every entry whose canonical series has moved since it was promoted. CI runs it with `--exclude $PROMOTE_EXCLUDE`. |
| `tools/promote … --exclude SERIES …` | Leave the named series out of this run. |
| `tools/promote … --dry-run` | Print the full plan without writing anything. |

`tools/promote` refuses a lecture name held by two canonical-eligible series with different text, naming the lecture and every series involved. It does not pick a winner by run order. A rename or merge upstream fixes it; until then, [`sync/canonical.yml`](sync/canonical.yml) can name the winning series, and the entry is recorded as `interim`. A copy that is merely stale (a recorded source still at a version the pool already took, while the canonical copy moved on) is not a collision: it stays a source, and the refresh goes through. A `sync/canonical.yml` line that names such a stale copy is refused, though, since following it would take the pool back to the lagging text, so delete a line as soon as promote reports that it settles nothing.

## Running the drift-check

[`tools/drift-check`](tools/drift-check) proves the pre-cutover invariant: every pool lecture equals its canonical mirror copy modulo the rewrites recorded in `sync/ledger.yml`, and every other series' copy is where the ledger last saw it. Like `tools/sync` it is a self-contained uv script. It never writes to the pool or the mirror: the only repository file it writes is `sync/toc.yml`, under `--accept-toc`; `--json` writes its report wherever you point it, and under GitHub Actions it appends step outputs.

| Command | What it does |
| --- | --- |
| `tools/drift-check` | Report against the existing `mirror/`. Exit 0 clean, 1 findings, 2 a pool file was edited directly. |
| `tools/drift-check --reconstruct` | Rebuild `mirror/` for the series the ledger references first. |
| `tools/drift-check --print-issues` | Show the issues `--issues` would open, without touching GitHub. |
| `tools/drift-check --issues` | Open, update and close `drift` issues to match the findings (CI). |
| `tools/drift-check --accept-toc dp-test` | Record a series' `_toc.yml` at its current pin as the watched baseline. |

Four outcomes: **refresh** (the canonical copy moved upstream; CI runs `promote --refresh --exclude $PROMOTE_EXCLUDE` and opens a pull request; an entry the refresh refuses is listed with promote's reason, in that pull request when one is opened and always in the red run's refresh step; the usual reason is a same-name copy edited to differ, which `sync/canonical.yml` or upstream settles; while the entry's canonical copy differs from its ledger record the run stays red every night until it is settled, and a settlement applies the next night), **drift** (a non-canonical copy diverged from its canonical home, a copy was removed, or a watched toc changed; each becomes an issue that closes itself when the finding clears), **violation** (the pool itself was edited; the job goes red), and **info** (a copy is merely stale, or a divergence converged). [`drift-check.yml`](.github/workflows/drift-check.yml) runs it after every `sync`.

One kind of copy is never watched. A **consumer** series (`class: consumer` in `sync/manifest.yml`, today `dp`) only republishes other series' lectures, so its copies are recorded as `superseded` and are expected to go stale.

## The technology register

[`docs/tech/`](docs/tech/) is a standing record of technology options for improving the lectures: what was looked at, the named files where it would apply, and what was decided and why. An entry is not ready until it names the files it would change; [its README](docs/tech/README.md) sets out the format and the states an entry moves through.

## The plan

The move is planned in ten stages: reorganise first on today's toolchain (Jupyter Book 1), then switch the engine once, later.

1. **Set up** access and tracking.
2. **Sources in.** Bring every lecture of every series into the pool, reconciling differences in the series repositories.
3. **One publishing workflow** that builds any product on either engine, rehearsed end to end, including a rollback, on a sandbox series.
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
