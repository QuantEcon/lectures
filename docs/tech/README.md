---
title: Technology register
---

# Technology register

A standing record of technology options for improving the lectures — what we looked at, **where it would apply**, and what we decided.

This exists because a link on its own decays into nothing. QuantEcon/meta#53 is the worked example: a 2022 note pointing at [asciinema](https://asciinema.org) sat untouched for four and a half years, while the thing it would have improved — a 1.4 MB screenshot of a terminal in `workspace.md` — shipped in a lecture created two years *after* the note was filed. The tool was recorded; the application was not; nobody could act on either.

## What an entry must contain

Three parts, all required.

| Part | Rule |
|---|---|
| **What it is** | What the option is, and a link, plus current project health — release cadence, last activity — so a future reader can tell a considered decline from a dead-technology decline. Two or three short paragraphs at most; if the option has an obvious current alternative, name it here |
| **Where it would apply** | **Named files.** Never "the lectures", never "our docs". If you cannot name a file, the entry is not ready |
| **Decision** | The call, the date, who made it, and the reason. Required whenever `state` is `adopted`, `declined` or `superseded` |

The middle row is the one that carries the value. It is also the one that is easiest to skip.

## States

| State | Meaning |
|---|---|
| `candidate` | Noted, not yet assessed |
| `evaluating` | Someone is actively looking at it |
| `adopted` | In use — the entry names where |
| `declined` | Looked at, decided against. **Reason and date required** |
| `superseded` | A different option won — the entry names it |

`declined` is a first-class terminal state, not an absence. An option we considered and rejected, with the reason written down, is more useful than one that was never recorded — it stops the next person redoing the assessment, and it stops them avoiding the idea without knowing why.

## Categories

`authoring` · `plotting` · `notebooks` · `execution` · `environments` · `publishing` · `tooling` · `ai`

Add one if none fits.

## Adding an entry

One file per technology in `entries/`, named for the technology. Copy the frontmatter block below, write the three sections, then add a row to [index.md](index.md).

The index's **Applies to** column names the primary file or files, repo-qualified — it is a pointer, not the full list, and the entry itself carries every site. The same rule applies as in the entry: name files, not areas. An index row that reads "the pandas lectures" tells a reader nothing they could act on.

```yaml
---
name: <technology>
category: <from the list above>
state: candidate
last_reviewed: <YYYY-MM-DD>
reviewed_by: <github handle>
origin:
  - <issue or PR that raised it, if any>
---
```

Revisiting an entry means updating `state` and `last_reviewed` and appending to the decision section — not overwriting it. The history of a call is part of the record.

## A note on paths, pre-cutover

The pool in `lectures/` is empty until the per-series cutovers happen, so "where it would apply" currently points at files in the live series repositories — for example `QuantEcon/lecture-python-programming/lectures/workspace.md`. Those paths should be repointed at pool paths as each series moves. Until then, prefer a full `owner/repo/path` reference over a bare path, so an entry is never ambiguous about which tree it means.

## Scope

Technology options for the lectures and the machinery that builds them. Editorial questions about a specific lecture — is this one worth converting, is it style-guide compliant — belong with the per-lecture state discussed in QuantEcon/project-monorepo#1, not here. The two share the same `declined`-with-a-reason discipline deliberately, so the records can be read together.
