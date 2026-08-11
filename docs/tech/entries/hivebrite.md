---
name: Hivebrite
category: community
state: declined
last_reviewed: 2026-08-07
reviewed_by: mmcky
origin:
  - QuantEcon/meta#65
---

# Hivebrite

## What it is

[Hivebrite](https://hivebrite.io) is a white-label platform for building private, gated online communities. Stripped of the marketing language, it is a **membership-administration system with a discussion forum attached** — its distinctive capabilities are member directories with role-based permissions, membership tiers and dues, paid event ticketing, donations, mentoring programmes and a job board. Its four verticals are associations, higher education, non-profits and business.

The company is healthy and independent — Paris-based, around 146 employees, and the acquirer rather than the target in its one M&A event since this was raised (Orbiit, July 2024). The original link now redirects from `hivebrite.com` to `hivebrite.io`; that is a domain consolidation, not a rebrand. **Vendor risk is not why this is declined.**

Pricing is published, which it was not in 2022: **Core from $895/month billed annually ($10,740/year)** and **Flex from $1,995/month ($23,940/year)**, then Prime and Custom Fit by quote. Seat caps apply to administrators, not members. There is no free tier and no trial.

A non-profit discount exists but is **unquantified** — the vendor states only that it offers "flexible pricing options with discounts for qualifying organizations", with no rate, floor or eligibility criteria published. There is **no academic or education discount**: higher education is a full-price vertical, since alumni relations is a core market Hivebrite sells into.

> **Beware the secondary sources.** Numerous current-looking pages describe tiers named "Connect / Scale / Enterprise" from $799/month, and a 1.5% platform commission. None of that appears in vendor material. Those pages are mostly competitor-owned or generated. Check `hivebrite.io/pricing` directly.

## Where it would apply

There is no current QuantEcon surface this would attach to. The closest thing that ever existed was `discourse.quantecon.org`.

## Decision

**Declined, 2026-08-07 (@mmcky).** On measured demand and product shape — not on cost, and not on hosting.

**We ran this experiment to completion.** `discourse.quantecon.org` operated from November 2016 until March 2025, when it was retired in QuantEcon/website#157. The published reason was that "the forum was not seeing high usage rates" and "the maintenance cost was higher than the benefit it was bringing to the broader community". Hivebrite is the same bet with an invoice attached: it would reprovision a surface that was retired for want of demand, and it would still require the staffing whose absence ended the free one.

**Separately, the shape is wrong.** Membership administration assumes an enumerable, gateable, usually dues-paying roster. QuantEcon has an open, anonymous, global readership of static lecture sites. The features that differentiate Hivebrite would be dead weight, and the gating would work against open access.

Cost is deliberately not the lead. At $10,740/year this is affordable for a NumFOCUS-supported project, so declining on price would invite "then buy a cheaper one" — and the cheaper one is exactly what was tried and closed.

## Revisit if

QuantEcon acquires a genuine membership — an enumerable roster with a reason to log in — **and** someone is accountable for running the community day to day. Both conditions matter; the second is what actually ended the last attempt.

`QuantEcon/community-library`, created 2026-08-03 for the SCE Working Group, is association-shaped and worth watching: participating projects, a member roster, contributed content, an events cadence. It does not reopen the decision — the roster is currently empty and the initiative chose GitHub Pages plus issue forms at zero cost — but it means "QuantEcon has an audience, not a membership" should not be treated as a permanent property of the organisation.

## This is not a decision against community

Two live threads sit alongside this and are unaffected: QuantEcon/meta#153 evaluates Ghost as a platform for quantecon.org, and the Discourse closure announcement itself committed to "evaluating new platforms and opportunities" and to AI tutors on the lecture sites.

Also worth knowing before anyone prices a replacement: **GitHub Discussions is free, already owned, and currently disabled on every public QuantEcon repository except `meta`.**
