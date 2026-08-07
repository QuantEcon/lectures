---
name: Mito
category: authoring
state: declined
last_reviewed: 2026-08-07
reviewed_by: mmcky
origin:
  - QuantEcon/meta#59
---

# Mito

## What it is

[Mito](https://www.trymito.io) renders a spreadsheet interface over a pandas DataFrame inside Jupyter and writes the equivalent pandas code as you edit — the pitch being a bridge for analysts who have outgrown Excel.

That was the 2022 product. **In 2026 it leads with a Jupyter AI agent**, and the repository's own description lists the spreadsheet last, behind AI chat and autocomplete. A separate `mito-ai` package has existed since September 2024. The original framing of this option — "data tables" — no longer names the thing.

The project is alive: `mito-ds/mito` has 2.6k stars, ships roughly monthly, and released 0.2.69 on 2026-07-21, with the spreadsheet frontend itself touched as recently as May 2026. **Viability is not why this is declined.**

Licence is AGPL-3.0 with proprietary carve-outs — the `pro` and `enterprise` directories carry per-seat commercial licences, and GitHub reports the repository as NOASSERTION. That is out of step with the permissive stack the lectures otherwise stand on (pandas and numpy are BSD-3). Worth noting the move to AGPL happened in February 2022, *before* this option was raised, so nothing degraded after the fact.

## Where it would apply

The pandas teaching material, principally `lecture-datascience.myst/lectures/pandas/` and `lecture-python-programming.myst/lectures/pandas.md`.

## Decision

**Declined, 2026-08-07 (@mmcky).** The decision is about delivery surfaces, and it does not depend on any pedagogical argument.

QuantEcon reaches readers through four surfaces. Mito works on none of them.

1. **Colab — where we actively send people.** `mitosheet` raises `Exception("The mitosheet currently only works in JupyterLab.")` when it detects Colab. Our own `getting_started.md` calls Colab "both free and reliable", and every lecture page carries a Colab button. The upstream request for Colab support has been open since December 2022
2. **The published static site.** Worse than useless here: the frontend renders the grid from embedded data *unconditionally*, then silently ignores every interaction because there is no Jupyter frontend behind it. That is a fully painted spreadsheet that does nothing — the same failure class as QuantEcon/meta#355 — and it costs 2.36 MB per cell
3. **Live in-browser compute** (`lecture-wasm`, and the per-lecture live-compute work in `quantecon-theme.mystmd#114`). Mito does support JupyterLite, deliberately. But its frontend is a JupyterLab **application extension**, and our live compute is thebe embedded in a MyST page with no Lab shell. A kernel is necessary but not sufficient
4. **Downloadable notebooks.** Requires the reader to install a JupyterLab extension. Our one precedent for asking that — `lecture-datascience.myst/lectures/introduction/local_install.md` — has been broken since JupyterLab 4 removed the source-build path

## Revisit if

QuantEcon ever ships a full JupyterLab-based JupyterLite deployment — the direction implied by the Jupyteach delivery work. At that point the mechanical objection lapses and the question becomes a genuinely pedagogical one, which is worth asking fresh rather than inheriting this answer.

## The want was real; the tool was wrong

What this option was reaching for — showing a DataFrame as something better than a truncated repr or a screenshot — is a live gap. `lecture-datascience.myst/lectures/pandas/groupby.md:565` still ships a table result as a stale static PNG, reported in `lecture-datascience.myst#214` on 2022-11-13 and unfixed since.

**`itables`** answers it and clears both constraints Mito fails: MIT, zero runtime dependencies, works in Colab, and verified by execution to survive `nbconvert` into self-contained static HTML at 276 KB against Mito's 2.36 MB. Proposed in `lecture-datascience.myst#282`.

This entry should not be read as "interactive tables were considered and rejected". They were not. Mito was.

## What this decision must not be read as saying

- **Not** that Mito is abandoned or unmaintained — it shipped last month
- **Not** that its licence changed for the worse after we looked — the AGPL move predates the issue
- **Not** that its telemetry cannot be switched off without paying. An environment-variable opt-out exists; Mito's own documentation on this is stale. What is true is that telemetry is **on by default**
