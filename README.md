# QuantEcon Lectures — monorepo

> **Status: early, under-construction scaffolding.** This repository is being stood up. It does **not** yet host any published lectures. For now, the authoritative QuantEcon lectures still live at their individual series sites (linked below). Treat everything here as work in progress.

This repository is the future single source of truth for the QuantEcon lecture series. The goal is to hold every canonical lecture **exactly once** in a shared pool, and to build each published series or course from a thin manifest that selects and orders pool lectures — never from a copy.

It begins life **downstream** of six existing, live lecture repositories, which it **mirrors read-only** until a future, deliberate, per-series cutover. This scaffold is the very first milestone: the repository skeleton plus the mirror-sync groundwork. Later capabilities (a curated pool, product manifests, promotion and provenance tracking, drift checks) are not built yet — see [Roadmap](#roadmap--coming-next).

## Where the lectures actually live (for now)

Until each series is deliberately cut over, the live sites below remain authoritative. Read and cite those, not this repository.

| Key | Live site | Source series |
| --- | --- | --- |
| `intro` | https://intro.quantecon.org | QuantEcon/lecture-python-intro |
| `programming` | https://python-programming.quantecon.org | QuantEcon/lecture-python-programming |
| `intermediate` | https://python.quantecon.org | QuantEcon/lecture-python.myst |
| `advanced` | https://python-advanced.quantecon.org | QuantEcon/lecture-python-advanced.myst |
| `dp` | GitHub Pages today (planned: https://dynamic-programming.quantecon.org) | QuantEcon/lecture-dp |
| `jax` | https://jax.quantecon.org | QuantEcon/lecture-jax |

## The four posture rules

These rules govern how this repository relates to the six live series during the pre-cutover period. They are deliberate constraints, not temporary shortcuts.

1. **Read-only until the technical solution is proven.** The monorepo only *reads* from the live repositories. It opens no pull requests, pushes nothing, and edits nothing upstream. There is no write path today.
2. **The live repos remain the source of truth.** Each live series stays authoritative until a deliberate, per-series cutover moves that series into this monorepo. Nothing is migrated implicitly.
3. **Upstream-first editing is the steady-state model — not active now.** Once a series begins cutover, edits will land here first and flow outward. That model is described for orientation only; it is switched on per series, and no series has begun.
4. **Prove, then flip.** A dynamic-programming (`dp`) pilot is the evidence gate. We prove the pool-and-product approach on `dp` before any series is cut over.

## The mirror → pool → products model

The repository is organised around three layers. Only the first exists in a meaningful form today.

| Layer | What it is | State today |
| --- | --- | --- |
| `mirror/<key>/` | A machine-reconstructed, verbatim copy of each live series' allowlisted paths, pinned to an exact commit. Never hand-edited, never committed. | Reconstructed on demand; **gitignored**. |
| `lectures/` | The curated **pool** — every canonical lecture, held exactly once. | Empty placeholder. |
| `products/` | One folder per published product, each a thin **manifest** that selects and orders lectures from the pool. | Empty placeholder. |

### Why we commit only SHAs, not the mirror

`mirror/<key>/` is a pure function of three inputs: the source **repo**, a **pinned commit SHA**, and the **allowlist** of paths to take from it (`lectures/` and `environment.yml`). Because the mirror is fully determined by those inputs, we commit **only the pinned SHAs** (in [`sync/state.yml`](sync/state.yml)) and rebuild the mirror on demand. The repository therefore carries no heavy verbatim history, and the mirror can always be reconstructed byte-for-byte.

- **Human intent** — which repos feed the mirror — lives in [`sync/manifest.yml`](sync/manifest.yml).
- **Machine state** — the exact SHA each series is pinned to — lives in [`sync/state.yml`](sync/state.yml), written by the sync tool.

## Directory layout

```
.
├── _base/            # (later) shared theme + toolchain (myst.yml) defaults — placeholder
├── lectures/         # (future) the curated pool — every canonical lecture once — empty
│   └── _static/
├── products/         # (future) one manifest per published product — empty
├── mirror/           # reconstructed, verbatim, GITIGNORED — never committed
├── sync/
│   ├── manifest.yml  # human intent: which repos feed the mirror
│   └── state.yml     # machine state: pinned SHAs (bot-written)
├── tools/
│   └── sync          # reconstructs the mirror from pinned SHAs
└── .github/workflows/
    └── sync.yml      # weekly job that refreshes the pinned SHAs
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

## Roadmap / coming next

This milestone is intentionally small. Planned follow-on work, roughly in order:

- **The curated pool** — populate `lectures/` with canonical lectures, held exactly once.
- **Product manifests** — thin per-product folders under `products/` that select and order pool lectures.
- **Promotion + provenance ledger** — a tool and record for promoting a mirrored lecture into the pool, tracking where each pool lecture came from.
- **Drift check** — detect when a mirrored series has diverged from its pooled counterpart.
- **The `dp` pilot** — prove the whole pool-and-product approach on dynamic programming, the evidence gate before any cutover.

## Licence

To be confirmed; the mirrored content remains under the licences of its respective source series until cutover.
