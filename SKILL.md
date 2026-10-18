---
name: openrouter-model-router
description: Pick OpenRouter models by domain popularity and price them live. Use when choosing a model for a domain — research, writing, coding, orchestration, ops — when ranking candidates by what traffic actually runs, or when costing a batch of agent runs against a budget.
---

# OpenRouter Model Router

Selection is popularity: what real traffic actually runs in the domain, not
benchmarks, reputation, or curation. Eligibility stays popularity; the
multi-ticket deal tilts by preference. Prices are live; quality is not claimed.
The work also carries one effort coordinate — how hard the mind deliberates
(`glance` / `measured` / `thorough` / `exhaustive`) — resolved to a rung on
whatever the ranking picks.

## Steps

1. **Collect the demand.** Domain (one of the five in `policy.json`), effort
   intent, tickets, budget. The token profile defaults to the domain; output
   volume is the cost driver for authoring work and is stated before pricing.
   Done when: each input is stated or defaulted and none is guessed.

2. **Pull popularity.** Run `scripts/bind.py` (mechanics: `--help`). It reads
   the task-classification leaderboards and the daily token rankings, cached
   24h, and prices every candidate at live rates.
   Done when: candidates are ranked by their share of the domain's traffic,
   prices and data timestamp shown.

3. **Pick — or deal.** A single task gets rank 1 — unless the project already
   has that model bound, in which case deliberately step down to the next rank:
   switching models across a project is good for the project. A multi-ticket run
   gets a deal instead of a monoculture — `bind.py --deal --seed <project-name>`
   spreads tickets across the eligible pool by seeded draw from a
   preference-blended distribution (`policy.json` `affinity`). Deterministic in
   the seed: the same project replays the same deal. Budget pressure moves
   within the ranking toward cheaper rows — never outside it.
   Done when: a single task names one pick (with the cheaper alternative shown
   if one exists in the ranking), or a batch names its deal with per-model
   ticket counts and a combined projection.

4. **Resolve the rung.** Effort intent binds to a position on the pick's
   ladder — each dealt model resolves its own: `glance`→floor,
   `measured`→default, `thorough`→above-default, `exhaustive`→ceiling. Default
   is `medium` when the ladder names it, else the middle rung rounded up; a rung
   the model lacks collapses to its nearest.
   Done when: the rung is a real setting of every picked model.

5. **Project and decide.** Per-ticket cost and run total against the budget.
   Over budget means a cheaper rank or a lower rung — reasoning tokens bill as
   output, so effort is a real cost lever here.
   Done when: the run total carries an explicit under/OVER verdict.

6. **Offer to refresh stale policy.** Every run prints `policy.json`'s age in
   the header — check it. `--check-policy` adds the drift detail: ranked models
   without summaries, summaries no longer ranked, stale fit keys, and signal
   coverage gaps (a hint that favors or avoids a model in one domain while the
   model ranks in another where the hint is silent). When the policy is older
   than one rankings window (~30 days) or the check reports drift, tell the
   user and offer to run a summaries refresh; the procedure is
   `research/README.md`. Signal drift is taste maintenance: report it, never
   fix it — the user edits fit and evidence.
   Done when: a due policy has been surfaced to the user with an offer to
   update — never silently ignored.

## Reference

- **Domains** — five, mapped to leaderboard tags in `policy.json`: research,
  writing, coding, orchestration, ops. A tag may serve two domains (a lens, not
  a partition). Edit the map there and nowhere else.

- **What popularity is** — revealed preference of real traffic: request share
  per task tag, with token share as the long-form weighting. It is not
  quality. The boards carry only each tag's top models, so the long tail is
  invisible and a miss there means "unranked", not "bad".

- **Hints** — user observations in `policy.json`, structured: a `note` (shown
  beside the ranking), `fit` (favor/avoid/neutral, per domain), and `evidence`
  (validated/suspected). Weighed, not obeyed — a hint may contradict the crowd
  or age out. Shown beside the ranking; never a reordering force. A domain the
  hint names — including an explicit `neutral`, "no opinion here" — is an
  answered question; a domain it omits is an open one, flagged by
  `--check-policy` until the user answers. Either way a non-favor/avoid fit
  tilts nothing.

- **Deal (multi-ticket diversity)** — a project that runs one model for
  everything carries one model's failure modes, so batches are spread across
  the popular candidates. Eligibility stays popularity: the top-K selectable
  models (`affinity.eligibility_top_k`), plus favored models ranked below the
  cut if `admit_favored_outside_top_k` is set — unranked or unresolved models
  never play. The draw blends popularity and preference:
  `w = (1−λ)·pop + λ·pref`, λ = `affinity.blend_weight`, seeded per ticket for
  a reproducible deal. **Affinity** is derived at run time, never stored: a
  hint's fit for the domain and its evidence map through `affinity.factors`
  (favor/validated ×3.0, favor/suspected ×2.0, avoid/validated ×0.3,
  avoid/suspected ×0.5). Longest prefix wins. The deal is the only place taste
  acts — the ranking itself is never reordered.

- **Token profiles** — cost is output-weighted for authoring: a `.md` research
  note is mostly completion tokens (authoring: 20K in / 12K out / 40% cached),
  while tool loops are input-heavy and cached (agentic: 40K in / 4K out / 75%).
  Output price, not input price, decides who is expensive at authoring.

- **Prices** — per 1M tokens: input, output, cache-read, cache-write. Some
  models tier prices by context size; the table prices the base tier. The
  effort rung multiplies output spend (glance 0.6×, measured 1×, thorough 2.5×,
  exhaustive 6×). The baseline (`policy.json`) is the price anchor for Δ
  columns and nothing else.

- **Attribution** — rankings data is CC BY 4.0. When quoting figures outside
  the table, carry "Source: OpenRouter (openrouter.ai/rankings), as of
  `<meta.as_of>`".

- **Tests** — stdlib unittest; run `python3 -m unittest discover -s tests` from
  the repo root before shipping any script change. `tests/live_smoke.py` is a
  manual check against the real API.
