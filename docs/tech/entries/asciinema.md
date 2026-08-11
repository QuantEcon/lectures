---
name: asciinema
category: authoring
state: declined
last_reviewed: 2026-08-07
reviewed_by: mmcky
origin:
  - QuantEcon/meta#53
---

# asciinema

## What it is

[asciinema](https://asciinema.org) records a terminal session as a replayable *text* cast rather than a video, and embeds it in a web page via a JavaScript player. Because the recording is a byte stream and not pixels, the text stays selectable and the file stays small.

The project is healthy. Version 3.0.0 — a complete rewrite in Rust — shipped 2025-09-15, with v3.2.1 following on 2026-06-16; the CLI repository has 17.6k stars and was last pushed 2026-07-28, and asciinema.org remains a free, operating hosted service with no licence or hosting change since the option was first raised. **This entry is a considered decline, not a dead-technology decline.**

The 2026 alternative worth naming alongside it is [charmbracelet/vhs](https://github.com/charmbracelet/vhs), which generates a recording from a committed script. That difference matters here: a vhs tape is reviewable in a pull request and reproducible from source, where a cast is an opaque artifact hosted elsewhere.

## Where it would apply

Three concrete sites, all verified 2026-08-07.

| File | What is there now |
|---|---|
| `QuantEcon/lecture-python-programming/lectures/workspace.md` | Two sections headed *"Using the terminal"* (lines 189 and 301). `jupyter_lab_cmd.png` is **1,399,850 bytes** — a raster screenshot whose entire content is a terminal printing the Jupyter server URL that the next line of prose refers to. Its alt text is `_images/jupyter_lab_cmd.png`, so a screen-reader user receives a filename where the instruction lives |
| `QuantEcon/lecture-python-programming/lectures/getting_started.md` | `starting_nb.png`, carried by a bespoke `.terminal` CSS class applied through `:figclass: terminal` |
| `QuantEcon/actions/docs/FUTURE-DEVELOPMENT.md` | Lines 98–101 ask for a container workflow walkthrough, a migration guide screencast, and troubleshooting videos. Written in 2026, still unclaimed |

The first two are the reason this option kept looking attractive. The third is the only one where it might still win.

## Decision

**Declined, 2026-08-07 (@mmcky).**

The terminal moments in the lectures are one-shot, non-interactive commands with static output — `pip install jupyterlab`, `jupyter-lab`, `conda update conda`. For that shape, a plain fenced code block beats a hosted player on every axis that matters to us: it is smaller, it is copy-pasteable and greppable, it is readable by a screen reader, and it survives the PDF and downloadable-notebook builds that a JavaScript embed does not reach.

Worth recording that Hugo — cited in QuantEcon/meta#53 as the demonstration of the technique, and embedding five casts in its quick-start guide at the time — reached the same conclusion. It removed its `asciicast` shortcode entirely in November 2022 and now teaches every command-line step with static code fences. The casts it had published still resolve; it was the technique that was abandoned, not the service.

This decision is about fit, not quality, and it does not rest on any claim that our build pipeline forbids rich embeds. It does not: `sphinxcontrib-youtube` is pinned across the lecture repos and live video ships today, and the data-science lectures serve multi-hundred-frame animated GIFs.

## Revisit if

We commit to producing genuinely multi-step, interactive command-line walkthroughs — the `QuantEcon/actions` screencast asks above are the live candidate. At that point evaluate `vhs` alongside asciinema rather than defaulting to either, on the committed-artifact argument.

## Follow-on, independent of this decision

Replacing the raster terminal screenshots in `workspace.md` and `getting_started.md` with fenced text is worth doing on its own merits — roughly 1.7 MB of payload, plus the alt-text gap, plus commands that become copy-pasteable and survive every output format. That change needs no recording technology at all, and it is the actual defect this option was circling.
