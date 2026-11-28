# Contributing

How this repository is laid out, and what each tool does, is in [README.md](README.md); the rules for a site's folder are in [sites/README.md](sites/README.md). This page says what runs on a pull request, and what its previews show.

## What runs on a pull request

| Workflow | When | What it checks |
| --- | --- | --- |
| [`pool-check.yml`](.github/workflows/pool-check.yml) | the pull request touches the pool, the sites, the environment list, the ledger, the manifest or the tools it runs | the pool's and the sites' rules (`tools/pool-check`) and the `_shared/` index |
| [`tests.yml`](.github/workflows/tests.yml) | it touches `tools/`, a site's `site.yml` or the workflows the tests read | `tools/tests` |
| [`site-build.yml`](.github/workflows/site-build.yml) | it touches the pool, the sites or an input of the build | builds each site the change reaches, strictly: its HTML, and the notebooks and the PDF it publishes. Then it previews each site it built (below) |

A lecture's change builds the sites whose `_toc.yml` lists it, and a site's own file builds that site; [README.md](README.md) says which paths build which sites. No check is required to merge, since `main` has no branch protection, so read the checks before you merge.

## Previews

Each site the pull request builds gets a preview on Cloudflare Pages, at `https://pr-<number>.qe-preview-<site>.pages.dev`, and a comment of its own on the pull request, headed `☁️ Cloudflare Preview Ready! (<site>)`, with the address and a link to each changed page the site lists. A later push updates the same comment, and the address always shows the newest push that deployed.

- **HTML and notebooks, no PDF.** Cloudflare takes no file over 25 MiB, and the PDFs are up to 68 MiB, so a preview leaves the PDF out, and its "Book (PDF)" link answers 404. The PDF is still built, strictly, as the pull request's check: to read it, download the run's `html-<site>` artefact (kept for 7 days), which has it under `_pdf/`.
- **After every site's build.** The previews start when every site the pull request builds has finished, so a change that reaches intermediate waits for intermediate's build.
- **Addresses.** Cloudflare drops `.html` from a page's address, so `…/mccall_model.html` opens as `…/mccall_model`. An address the preview has no file for answers 404, with a page that says so.
- **A site whose build failed gets no preview.** If an earlier push deployed one, its comment and address still show that push.
- **Links to another site** go to that site's live pages, as they do on the published sites, not to another preview.
- **A pull request from a fork** runs only once a maintainer approves its run, and gets no preview: a fork's run gets no secrets. A pull request opened by Dependabot gets none either.

Previews are the monorepo's own: each series keeps its own previews of its own pull requests until its cutover.
