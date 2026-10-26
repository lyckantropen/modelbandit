---
name: openrouter-model-router
description: Pick OpenRouter models by domain popularity and price them live. Use when choosing a model for a domain — research, writing, coding, orchestration, ops — when ranking candidates by what traffic actually runs, or when costing a batch of agent runs against a budget.
compatibility: "Python 3, stdlib only — no dependencies, no environment to provision. The summaries-refresh procedure and the unit test suite live in the repository checkout (research/, tests/), not in this skill folder: with a skill-folder-only install the refresh offer reports what is due and where the procedure lives instead of running it."
---

# OpenRouter Model Router

The ranking is popularity — what real traffic actually runs in the domain, not
benchmarks, reputation, or curation. The task order is that ranking priced at
effort. Task fit is judged from the research summaries; user taste tilts only
the multi-ticket deal. Prices are live; quality is claimed only where the
research cites it. The work also carries one effort coordinate — how hard the
mind deliberates (`glance` / `measured` / `thorough` / `exhaustive`) — resolved
to a rung on each candidate's ladder.

## Steps

1. **Collect the demand.** Domain (one of the five in `policy.json`), effort
   intent, tickets, budget. The token profile defaults to the domain; output
   volume is the cost driver for authoring work and is stated before pricing.
   Apply the Secrets gate to the shape's material: consult the project's
   optional secrets file
   (`modelrouter.secrets.json` — a gitignoreable file in the working tree),
   falling back to the built-in default. Content-inclusion, any-of: the shape
   is **Sensitive** when its material carries content drawn from files
   outside the working folder, or passwords/tokens/keys, or identifiers
   readable from this machine's state — a mere path mention does not trip
   it; any one item does. The project file can tighten the default, never
   silently loosen it. The verdict is decided at collection — never a mood
   declared mid-run.
   Done when: each input is stated or defaulted and none is guessed — the
   Secrets gate's verdict included; a Sensitive shape goes to the script as
   `--sensitive`.

2. **Pull popularity.** Run `scripts/bind.py` (mechanics: `--help`). It reads
   the task-classification leaderboards and the daily token rankings, cached
   24h, and prices every candidate at live rates.
   Done when: candidates are ranked by their share of the domain's traffic,
    prices and data timestamp shown. Cataloged OpenCode `opencode/*` models
    also appear; OpenRouter `:free` routes retain their own slug. The script
    silently probes LM Studio at `127.0.0.1:1234` each run; currently served
    local ids matched by `free_models` join that run's candidate set with the
    cataloged window and `local` Exposure. Probe results are not cached or
    written to policy. An uncataloged or unsummarized Free route remains
    visible but is not selectable.

3. **Order by task score.** Each candidate scores `share^α / cost^β` —
   popularity priced at its rung for the effort intent (α, β from `policy.json`
   `scoring`; free routes priced at the pool's cheapest paid ticket, never
   zero). The candidate set stays the popularity top; the score orders it.
   Rung rules: `glance`→floor, `measured`→default, `thorough`→above-default,
   `exhaustive`→ceiling; a rung the model lacks collapses to its nearest, and
   the output multiplier discounts toward `glance`'s in proportion to the rung
   achieved.
   Done when: candidates are in task order with share, score, price, context
    window, Exposure and rung visible (Exposure is `—` for paid routes).

4. **Judge task fit.** Score every candidate 0–5 for THIS task (fractions
   fine), from the summaries: 5 = summaries explicitly endorse it here;
   3 = no evidence either way; 1 = summaries warn against; 0 = cannot do the
    task. Context window and rung coverage are judged too; for Free routes,
    the Context gate mechanically excludes a candidate when the input budget
    times `context_gate.headroom` exceeds its window times
    `context_gate.margin` (defaults: 2× and half-window). Paid candidates remain
    judge-only for context. Standing = score × fit/5 (unscored = 5). Pass the
    fit judgments to the script (`--fit`) so the order and the deal use them.
   Done when: every considered candidate carries a fit score and a one-line
   reason.

5. **Pick — or deal.** A single task takes the top of the fit-adjusted order —
   unless the project already has that model bound, in which case deliberately
   step down: switching models across a project is good for the project. A
   multi-ticket run gets a deal instead of a monoculture — `bind.py --deal
   --seed <project-name>` spreads tickets per ticket shape across the eligible
   pool by seeded draw from a preference-tilted blend of the fit-adjusted
   scores (`policy.json` `affinity`). Deterministic in the seed: the same
   project replays the same deal. Budget pressure moves within the order
   toward cheaper rows — never outside the popularity set.
   One invocation deals one ticket shape — a run's domain, effort, token
   profile, `--fit` and `--sensitive` combination — so tickets of the same
   shape share one task-fit assessment by construction: the step-4 judgments
   are made once for the run and every ticket the deal draws inherits them.
   A run of a different shape is a different invocation.
   Done when: a single task names one pick (score and fit both shown), or a
   batch names its deal with per-model ticket counts and a combined projection.

6. **Project and decide.** Per-ticket cost and run total against the budget.
   Over budget means a cheaper rank or a lower rung — reasoning tokens bill as
   output, so effort is a real cost lever here.
   Done when: the run total carries an explicit under/OVER verdict.

7. **Offer to refresh stale policy.** Every run prints `policy.json`'s age in
   the header — check it. `--check-policy` adds the drift detail: ranked models
   without summaries, summaries no longer ranked, stale fit keys, and signal
   coverage gaps (a hint that favors or avoids a model in one domain while the
   model ranks in another where the hint is silent). It also re-measures score
   balance against `scoring.thresholds` — a `coefficient re-tune due: yes`
   verdict is coefficient work; surface it with the same offer. When the policy
   is older than one rankings window (~30 days) or the check reports drift, tell
   the user and offer to run a summaries refresh — the summaries-refresh
   procedure; when you have the repository checkout, its path is
   `research/README.md`. With only the skill
   folder installed (no checkout) the offer degrades: report what is due and
   name the summaries-refresh procedure — it lives in the repository
   checkout, beyond this skill folder — and never emit a path that cannot
   resolve. Signal drift is taste maintenance: report it, never fix it — the
   user edits fit and evidence.
   Done when: a due policy has been surfaced to the user with an offer to
   update — never silently ignored.

## Reference

- **Domains** — five, mapped to leaderboard tags in `policy.json`: research,
  writing, coding, orchestration, ops. A tag may serve two domains (a lens, not
  a partition). Edit the map there and nowhere else.

- **Free catalog** — `policy.json`'s `free_models` maps id prefixes to
  `context_length` (positive tokens), `exposure` (`no-retention`, `trains`, or
  `local`), and optional `summary_ref` (an exact key in `summaries`). A catalog
  entry without a resolving summary is never admitted. Ranked
  OpenRouter `:free` routes use their own slug and need a catalog window;
  unknown Free routes never play. OpenCode entries are listed from this
  catalog. Entries with `local` Exposure are listed only while a matching id is
  served by the silent LM Studio probe; their context window and summary remain
  curated policy facts. Probe results join the in-memory model catalog for that
  invocation only. A missing server has no effect on output.

- **What popularity is** — revealed preference of real traffic: request share
  per task tag, with token share as the long-form weighting. It is not
  quality. The boards carry only each tag's top models, so the long tail is
  invisible and a miss there means "unranked", not "bad".

- **Score** — the task order: `share^α / cost^β`, cost at the candidate's rung
  for the effort intent. The exponent *ratio* decides the ordering, their
  *scale* the sharpness. α, β live in `policy.json` `scoring` and are accepted
  only against the balance thresholds (top-1 score mass 20–50%, top-2 ≤ 75% per
  pool): neither uniform nor dominated by one or two entries.
  `--check-policy` re-measures and calls for a re-tune when the balance
  drifts.

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
  cut — unranked or unresolved models never play. The draw blends the
  fit-adjusted task score and preference:
  `w = (1−λ)·score + λ·pref`, λ = `affinity.blend_weight`, seeded per ticket
  for a reproducible deal. **Affinity** is derived at run time, never stored: a
  hint's fit for the domain and its evidence map through `affinity.factors`
  (favor/validated ×3.0, favor/suspected ×2.0, avoid/validated ×0.3,
  avoid/suspected ×0.5). Longest prefix wins. The deal is the only place taste
  acts — the ranking itself is never reordered.

- **Exposure & Sensitive** — Sensitive is the Ticket shape's fifth element,
  bound per invocation (`--sensitive`) from the Secrets gate's verdict at
  demand collection. Exposure is a candidate's data-handling class —
  no-retention (input neither stored nor trained on), trains (input may be
  stored, collected, or trained on), local (runs on this machine) — a
  property of the serving route, never inferred from price: free does not
  imply trains, paid does not imply no-retention, an unknown free route
  defaults to trains. On a Sensitive shape the exposed — `trains` — are
  excluded from the pick and the deal, marked in the table with the reason
  (`exposed (trains)`), never hidden; no-retention free routes and local
  models stay admitted. Exposure, not price, decides — and one admission
  verdict serves both the table and the deal, so the two never disagree
  about what may serve a shape.

- **Token profiles** — cost is output-weighted for authoring: a `.md` research
  note is mostly completion tokens (authoring: 20K in / 12K out / 40% cached),
  while tool loops are input-heavy and cached (agentic: 40K in / 4K out / 75%).
  Output price, not input price, decides who is expensive at authoring.

- **Prices** — per 1M tokens: input, output, cache-read, cache-write. Some
  models tier prices by context size; the table prices the base tier. The
  effort rung multiplies output spend (glance 0.6×, measured 1×, thorough 2.5×,
  exhaustive 6×); a collapsed rung discounts toward glance 0.6× in proportion
  to the rung achieved, so a short-ladder model provably costs less than a
  full-ladder model at the same intent, and full ladders price the table
  exactly. The baseline (`policy.json`) is the price anchor for Δ
  columns and nothing else.

- **Attribution** — rankings data is CC BY 4.0. When quoting figures outside
  the table, carry "Source: OpenRouter (openrouter.ai/rankings), as of
  `<meta.as_of>`".

- **Tests** — repository-checkout material: the suite lives in `tests/` at the
  repo root, beyond this skill folder. stdlib unittest; run
  `python3 -m unittest discover -s tests` from the repo root before shipping
  any script change. `tests/live_smoke.py` is a manual check against the real
  API.
