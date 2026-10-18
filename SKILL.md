---
name: openrouter-model-router
description: Pick OpenRouter models by domain popularity and price them live. Use when choosing a model for a domain — research, writing, coding, orchestration, ops — when ranking candidates by what traffic actually runs, or when costing a batch of agent runs against a budget.
---

# OpenRouter Model Router

Selection is popularity: what real traffic actually runs in the domain, not
benchmarks, reputation, or curation. Prices are live; quality is not claimed.
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

3. **Pick by rank.** Rank 1 is the default pick. Budget pressure moves the pick
   within the ranking toward cheaper rows — never outside it. A rank outside
   the board's top models is not a candidate, whatever its qualities.
   Done when: one pick is named, with the cheaper alternative shown if one
   exists in the ranking.

4. **Resolve the rung.** Effort intent binds to a position on the pick's
   ladder: `glance`→floor, `measured`→default, `thorough`→above-default,
   `exhaustive`→ceiling. Default is `medium` when the ladder names it, else the
   middle rung rounded up; a rung the model lacks collapses to its nearest.
   Done when: the rung is a real setting of the picked model.

5. **Project and decide.** Per-ticket cost and run total against the budget.
   Over budget means a cheaper rank or a lower rung — reasoning tokens bill as
   output, so effort is a real cost lever here.
   Done when: the run total carries an explicit under/OVER verdict.

## Reference

- **Domains** — five, mapped to leaderboard tags in `policy.json`: research,
  writing, coding, orchestration, ops. A tag may serve two domains (a lens, not
  a partition). Edit the map there and nowhere else.

- **What popularity is** — revealed preference of real traffic: request share
  per task tag, with token share as the long-form weighting. It is not
  quality. The boards carry only each tag's top models, so the long tail is
  invisible and a miss there means "unranked", not "bad".

- **Hints** — tentative user observations in `policy.json`: tastes, suspicions,
  early trials. Weighed, not obeyed — a hint may contradict the crowd or age
  out. Shown beside the ranking; never a reordering force. Selection stays
  popularity.

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
