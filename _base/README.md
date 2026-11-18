# `_base/` — what every site shares

## `environment-update.yml`: the one environment

[`environment-update.yml`](environment-update.yml) is the environment the sites are to build in (QuantEcon/project-monorepo#77): what a build applies over the full image, `ghcr.io/quantecon/quantecon` (Python 3.13 and the `anaconda=2026.07` metapackage, the base every series' `environment.yml` names), with QuantEcon/actions' `setup-environment` (`environment-update:`). With one environment a pool lecture executes the same way in every site that lists it. Nothing builds with it yet: the site-build workflow moves to it in a later pull request, `dp` after its first shadow comparison.

- **One up-to-date baseline** (the owner's decisions of 2026-11-18 and -19). Every version is exact, for stability while the sites' builds are first developed, and is the newest release on 2026-11-19, except a package the `anaconda=2026.07` metapackage holds (at its version there, the base every series builds on), `jax` (0.11.0, as programming has it, since 0.11.1 hangs one of its lectures), `jupyter-book` (the newest 1.x, until the engine switch), and a version a lecture asks for (`"prettytable<3.18"`: the newest it allows). The six series are being brought to the same baseline upstream, one pull request each.
- **Where it moves the full image.** The build stack stays at the image's versions. `kaleido` goes from the image's 0.2.1 to 1.5.1, which needs a Chrome the image does not hold yet (QuantEcon/actions#85). sphinx, markdown-it-py and alabaster go back to what jupyter-book 1.x needs, as in every series' build.
- **A person changes a pin, after testing.** A workflow that watches for new releases of these packages and of the image is to be tracked on QuantEcon/project-monorepo#7. An entry without a version would not stay put: conda installs the pip list with `pip install -U`, so it would take the newest release on every build.
- **The lectures keep their install lines**, for readers running a notebook on Colab or at home. In a build a plain `!pip install` finds the package already here. An `--upgrade` line, or a `!conda install` of a package pinned here, replaces the pin for the rest of that build, since every lecture of a site runs in the same environment, so those lines are being removed upstream. When the three `!conda install … plotly-orca` lines are gone, `plotly-orca` leaves the list too.
- **`jax` is the CPU wheel.** A GPU build adds `jax[cuda13]==0.11.0` on top, the same version, which brings the CUDA plugin and the CUDA libraries it bundles (`nvidia-*` wheels, not pinned here). The GPU machine image holds no `anaconda` metapackage, so a GPU build needs that base as well; that is settled with the GPU leg.

## Keeping it whole

[`tools/pool-check`](../tools/pool-check) fails a pull request when a pool lecture's code cells install a package the file does not list, or a version limit in a lecture's install line does not allow the pinned version (`install-listed`), and when an entry is not pinned to one version, once (`environment`).

When a refresh brings in a lecture that installs something new, the refresh pull request fails its pool-check. Pin the package here **in a pull request of its own to `main`**, not on the refresh branch: `drift-check.yml` rebuilds `drift/refresh` from `main` on every run that still needs a refresh, so a commit pushed there is lost the next night. Once the pin has merged, the next scheduled run (or a manual run of `sync.yml`) rebuilds the refresh pull request on top of it, and its pool-check passes.

## Later

The shared theme and toolchain configuration (`myst.yml` defaults) that every site inherits, so that look, feel and build behaviour are defined once, comes with the engine switch. See the repository [README](../README.md).
