---
name: Plotly Dash
category: publishing
state: declined
last_reviewed: 2026-08-07
reviewed_by: mmcky
origin:
  - QuantEcon/meta#54
  - QuantEcon/meta discussion #278
---

# Plotly Dash

> **Scope.** This entry is about **Dash, the web application framework**. It is not about **plotly.py figures**, which QuantEcon uses and the style guide endorses. The two share a vendor and nothing else. Conflating them is the main way to get this decision wrong.

## What it is

[Dash](https://dash.plotly.com) builds analytical web applications in pure Python — a Flask server, a React front end, and callbacks that route user interaction back to Python. The project is in robust health: MIT, 24.4k stars, v4.4.1 on 2026-07-21, active weekly commits. The open-source library has not been narrowed since this was first raised; Plotly added paid hosting (Plotly Cloud, from $0 for a single app) rather than restricting the framework. **Health is not why this is declined.**

Dash requires a running Python process, and this is categorical rather than incidental: hard dependencies on `Flask` and `Werkzeug`, every interaction issuing a POST to `_dash-update-component`, and `app.run()` starting a Flask server. There is no serverless path — the request for a Pyodide backend, [plotly/dash#1559](https://github.com/plotly/dash/issues/1559), has been open since February 2021 at low priority and has seen no activity since 2024.

## Where it would apply

The genuine need behind this option is real and recurring — showing a reader a model at parameter values they choose. It has been raised at least twice, in QuantEcon/meta#54 (2022) and again in QuantEcon/meta discussion #278 (December 2025), and it currently ships broken in two places:

| Site | State |
|---|---|
| `lecture-dynamics/lectures/black_litterman.md` | Three `FloatSlider`s that render as draggable controls with no kernel behind them — one frozen PNG per output. Tracked at QuantEcon/meta#355 |
| `lecture-python-advanced.myst/lectures/matsuyama.md` | Widget disabled, with an honest note saying so |

## Decision

**Declined, 2026-08-07 (@mmcky).**

Every QuantEcon public site is served from GitHub Pages. There is no Python process, so a Dash app cannot be hosted, and a Dash app cannot be embedded inside a MyST lecture page in any case — it owns a whole page, and it would produce nothing in the pdflatex and downloadable-notebook builds that every lecture also ships.

The decisive point is proportion rather than principle. Every live instance of the need is a one-dimensional grid of 14 to 21 discrete parameter values. That precomputes into plotly animation frames or `updatemenus`, which are fully interactive **client-side on a static page** — no server, no new infrastructure, and it survives our build. Dash earns its complexity when arbitrary Python must run on a value the reader just chose: re-solving a model off-grid, querying a database, authentication, shared server-side state. None of that is what these lectures need.

**This decision covers the category, not just the product.** Streamlit, Shiny for Python in its server mode, Panel in server mode and Gradio all require the same running process and are declined on the same ground. Note the qualifiers: several of these have static export paths — `shinylive`, `stlite`, `panel convert`, and `marimo export html-wasm` — which are *not* covered here and are evaluated separately under WASM.

## What this decision must not be read as saying

- **Not** that QuantEcon's rendering model excludes interactivity. It does not. [manual.quantecon.org/styleguide/figures.html](https://manual.quantecon.org/styleguide/figures.html) serves a live, interactive plotly figure from GitHub Pages today. Static hosting and interactivity are orthogonal
- **Not** that we can never run a server. QuantEcon has run them before, and other initiatives actively plan serverless backend functions. This is a standing cost and operations preference, not an architectural law
- **Not** a judgement on Dash's quality or maintenance

## Revisit if

A use case appears that genuinely needs arbitrary Python on user input — off-grid model solving, a database-backed tool, anything requiring authentication — **and** someone accepts the operational commitment to run it. At that point reassess against the static-export alternatives first, since they cost no infrastructure.

## Related

- QuantEcon/meta#354 — the plotly renderer inconsistency; four different answers to "interactive figure", two broken
- QuantEcon/meta#355 — sliders that look interactive but are not
- QuantEcon/meta#143 and discussion #106 — WASM, the serverless route to the same need
