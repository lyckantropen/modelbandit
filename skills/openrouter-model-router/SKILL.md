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
   Apply the Secrets gate to the shape's material — always, before choosing a
   model. Run `scripts/bind.py --check-secrets --working-dir <folder>` with the
   shape's material on stdin; add a repeatable `--outside-file PATH` for each
   named outside source that contributes content. Each named file contributes
   only a capped slice. The gate does the mechanics itself: it reads the
   project's `modelrouter.secrets.json` (at the folder's git root, when it is
   in a repository), gathers this machine's hostname, login, home path and
   local address, reads content from the folder's **gitignored** files, and
   checks the named outside files — no assembly by you. It reports safe,
   sensitive or **not certified**, and names a rule when one trips it
   (`hostname`, `username`, `home path`, `local address`, `gitignored content
   (.env)`, outside-file content, a credential pattern, `phrase #N`,
   `pattern #N`). Exit status is 0 for safe, 1 for sensitive, 2 for usage
   errors, 3 for **not certified** — no material given, never read as safe —
   or 4 for a rules/config error.
   Content-inclusion, any-of: the shape is **Sensitive** when its material
   carries content drawn from a file outside the working folder, or from a
   gitignored file inside it, or passwords/tokens/keys, or identifiers
   readable from this machine's state — a mere path mention does not trip
   it; any one item does. The project file can tighten the default, never
   silently loosen it. The verdict is decided at collection — never a mood
   declared mid-run — and a Sensitive shape goes to the ranking run as
   `--sensitive`.
   If the rules file needs creating or updating, complete **Set up the secrets
   file** below before relying on project-specific rules.
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
    written to policy. A Free route without a resolving summary remains
    visible but is not selectable; OpenCode and local routes also need their
    own catalog entries. The same run reads the account's daily free-request
    counter and reports it in the header (`free quota: used/limit`): the
    configured `scoring.free_quota_reserve` is protected, and `:free` routes
    leave the pick and deal only when remaining quota is below that reserve.
    Plan size does not gate eligibility because the draw may use fewer Free
    tickets than the plan size. Harness `opencode/*`
    models and locally served models spend none of it. An unreachable key
    endpoint warns once and leaves the pool unchanged.

3. **Order by task score.** Each candidate scores `share^α / cost^β` —
   popularity priced at its rung for the effort intent (α, β from `policy.json`
   `scoring`). Free routes are priced at the **Nominal floor**
   (`scoring.free_risk`, default 0.35): that fraction of the pool's cheapest
   priced paid ticket, recomputed for each pool and shape. It is always above
   zero and below that paid ticket, so Free can win without winning by division
   alone. Exposure does not move it; the Sensitive gate does.
   The candidate set stays the popularity top; the score orders it.
   Rung rules: `glance`→floor, `measured`→default, `thorough`→above-default,
   `exhaustive`→ceiling; a rung the model lacks collapses to its nearest, and
   the output multiplier discounts toward `glance`'s in proportion to the rung
   achieved.
   Done when: candidates are in task order with share, score, price, context
    window, Exposure and rung visible (Exposure is `—` for paid routes).

4. **Judge task fit.** Score every candidate 0–5 for THIS task (fractions
   fine), from the summaries: 5 = summaries explicitly endorse it here;
   3 = no evidence either way; 1 = summaries warn against; 0 = cannot do the
   task. That judgment plus the effort intent is the shape's **Difficulty** —
   judged, never measured. Its counterpart is **Footprint**, measured, never
   judged: input × `context_gate.headroom` against the context window, and
   rung-priced output (profile output × the rung's multiplier) against the
   completion cap — each against a `context_gate.margin` share of capacity
   (defaults: headroom 2×, margin half). Headroom applies only to input growth;
    output demand is already inflated by its rung multiplier. For Free routes,
    the Context gate mechanically excludes on either dimension, the reason
    naming the bound
   (`over window`, `over completion cap`); a paid candidate that overruns is
   flagged with the same reason and stays in — capacity can be bought
   deliberately, and the judgment decides. Standing = score × fit/5
   (unscored = 5). Pass the fit judgments to the script (`--fit`) so the
   order and the deal use them.
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
   toward cheaper rows — never outside the popularity set. The deal reports
   its Free share — the fraction of tickets Free routes drew — reported,
   never capped and never floored: a shape may be dealt entirely to Free
   routes.
   One invocation deals one ticket shape — a run's domain, effort, token
   profile, `--fit` and `--sensitive` combination — so tickets of the same
   shape share one task-fit assessment by construction: the step-4 judgments
   are made once for the run and every ticket the deal draws inherits them.
    A run of a different shape is a different invocation. Before assigning a
    dealt Free slug, verify it resolves in the harness's model catalog (for
    example, with `opencode models`); if it does not, substitute the nearest
    cataloged sibling of the same family.
   Done when: a single task names one pick (score and fit both shown), or a
   batch names its deal with per-model ticket counts and a combined projection.

6. **Project and decide.** Per-ticket cost and run total against the budget.
   Over budget means a cheaper rank or a lower rung — reasoning tokens bill as
   output, so effort is a real cost lever here.
   Done when: the run total carries an explicit under/OVER verdict.

7. **Offer to refresh stale policy.** Every run prints `policy.json`'s age in
   the header — check it. `--check-policy` adds the drift detail: ranked models
   without summaries, summaries no longer ranked, stale fit keys, signal
   coverage gaps (a hint that favors or avoids a model in one domain while the
   model ranks in another where the hint is silent), and Free-share zeros
   (deals that drew no Free tickets, watched across checks). It also re-measures
   score balance against `scoring.thresholds` — a `coefficient re-tune due: yes`
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

## Set up the secrets file

When `modelrouter.secrets.json` is missing, or the user wants to tighten it,
conduct this interview before relying on project-specific rules:

1. Scan the repository for candidate identifiers, not credential values:
   `.gitignore` entries, `.env*` and key-material filenames, plus internal
   hostnames and client codenames that appear in configuration and docs. Do not
   assume a candidate is sensitive just because it appears; propose each one to
   the user individually and record an explicit include/exclude decision.
2. Ask for any additional free-form phrases or regex patterns. Phrases match
   literally; patterns must be valid regular expressions. The built-in
   credential and machine-fact rules already apply and cannot be disabled.
3. Ask whether the confirmed entries identify a person, client, or internal
   system, then ask directly: “Should this rules file be committed, or should
   it be gitignored?” Send the confirmed rules and both decisions to the writer
   as JSON on stdin:

   ```json
   {
     "phrases": ["confirmed literal"],
     "patterns": ["confirmed-regex"],
     "identifying": false,
     "commit": true
   }
   ```

   Run `scripts/bind.py --write-secrets --working-dir <folder>` with that JSON
   on stdin. It writes `modelrouter.secrets.json` at the folder's git root (or
   the folder itself outside a repository), reports rules added and already
   present, and merges on every re-run: existing rules are never removed and
   exact duplicates are kept once. Its report gives counts, never rule values.
   If `identifying` is true **or** `commit` is false, it appends the file path
   to `.gitignore` once; if the rules file is already tracked, it refuses and
   tells you to run `git rm --cached modelrouter.secrets.json` first.
   Otherwise it leaves `.gitignore` alone and says the rules file is meant to
   be committed.
4. Review the writer's report and show the resulting diff. Before a re-run,
   retain the previous rules-file contents; afterwards show a unified
   before/after diff as well as the `.gitignore` diff. An ignored, untracked
   rules file will not appear in ordinary `git diff`.
5. Run `scripts/bind.py --check-secrets --working-dir <folder>` with the actual
   shape material on stdin, adding `--outside-file PATH` for each named outside
   source. The gate reads the rules file itself. Exit 0 is safe, 1 is Sensitive,
   2 is a usage error, 3 means **not certified**, and 4 means a rules/config
   error: empty material is not safe by default, so obtain the material before
   claiming a safe shape.

## Reference

- **Domains** — five, mapped to leaderboard tags in `policy.json`: research,
  writing, coding, orchestration, ops. A tag may serve two domains (a lens, not
  a partition). Edit the map there and nowhere else.

- **Free catalog** — `policy.json`'s `free_models` maps id prefixes to
  `context_length` (positive tokens), `exposure` (`no-retention`, `trains`, or
  `local`), optional `summary_ref` (an exact key in `summaries`), and optional
  `max_completion_tokens` (a Free entry's completion cap when no endpoint
  reports one).
  `opencode/*` and local entries need their own window and a resolving summary.
  Ranked OpenRouter `:free` routes use their own slug and may resolve a summary
  by longest prefix without a `free_models` entry; their context window comes
  from the OpenRouter model catalog when available. A Free route without a
  resolving summary is never admitted. OpenCode entries are listed from this
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
  paid pool): neither uniform nor dominated by one or two entries. Balance is
  measured on the paid competition — a Free route enters no balance pool, its
  participation is the Free share signal's answer, and a pool with fewer than
  three paid candidates is reported not judgeable rather than judged.
  `--check-policy` re-measures and calls for a re-tune when the paid balance
  drifts; that drift is a diagnosed re-tune.

- **Nominal floor** — the score's cost term for a Free route:
  `scoring.free_risk` times the pool's cheapest priced paid ticket (default
  0.35), recomputed per pool and shape and applied to every Free route whatever
  its Exposure. The risk must be strictly between zero and one, which keeps the
  derived floor positive and strictly below the paid ticket. Only the score
  uses it — price columns and projections still report what a route costs to
  run.

- **Free quota** — OpenRouter's daily free-request counter
  (`free_model_daily_requests` on the key payload): one figure shared by every
  `:free` route, reset at UTC midnight, cached for a minute and never answered
  from a stale copy. The header reports `free quota: used/limit` and the
  protected reserve. `scoring.free_quota_reserve` (default 5; a negative or
  fractional reserve stops the run) protects the last few requests; plan size
  does not gate eligibility because a deal may draw fewer Free tickets than
  its ticket count. If remaining quota is below the reserve, `:free` routes
  are excluded from the pick and deal with the numbers stated (`free quota
  exhausted (50/50 used)`, `free quota thin (2 left < 0 planned + 5 reserve)`).
  Harness `opencode/*` models and
  locally served models never spend the counter, so this gate never removes
  them; a paid route is charged credits instead. An unreachable endpoint or a
  missing key reports `free quota: unavailable`, warns once, and leaves the
  pool unchanged; so does a payload that carries no counter, silently. No
  network failure blocks a run.

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
  acts — the ranking itself is never reordered. Its Free share — the fraction
  of tickets Free routes drew — is a report, never a cap and never a floor:
  some tickets, all of them, or none, as the draw falls.

- **Secrets gate** — the collect-demand check that makes a shape Sensitive,
  run as `scripts/bind.py --check-secrets [--working-dir PATH]` with the
  material on stdin and repeatable `--outside-file PATH` arguments for named
  outside content. It needs no policy and no network; the material is the
  agent's to supply (the tool never reads it for you). The verdict names the
  rule that tripped it and sets the exit status: **0** safe, **1** sensitive,
  **2** usage error, **3** not certified — no material given, never "safe" —
  **4** rules/config error. The tool assembles
  everything mechanical: the project's `modelrouter.secrets.json` at the
  working-folder root (the git root when in a repository, else the folder),
  this machine's identifiers (hostname, login, home path, non-loopback local
  address, each best effort and never shorter than four characters), and the
  significant lines of the folder's gitignored untracked files
  (`git ls-files --others --ignored --exclude-standard`, twenty files of up
  to 8 KB each), plus the capped content of every named outside file —
  `.gitignore` is the repository's own list of what must not leave it. Rules
  are additive only: `phrases` are literal inclusions,
  `patterns` are regular expressions, both validated at load — an unknown key,
  an empty phrase or a broken regex stops the check with status 4, and the
  built-in credential rules always apply. The verdict echoes no rule *value*,
  only its class or index (`phrase #1`), so its output is safe to quote back.
  For setup or updates, follow **Set up the secrets file**; `--write-secrets` reads
  confirmed JSON from stdin, merges additively, and applies the commit/gitignore
  decision.

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

- **Footprint & Difficulty** — two words for two different questions, never
  one word for both. Footprint is a Ticket shape's measured demand on a
  candidate — input × `context_gate.headroom` against the context window,
  rung-priced output against the completion cap, each against a
  `context_gate.margin` share of capacity. Headroom applies only to input
  growth; output demand is already inflated by the rung multiplier. Footprint
  is measured, never judged; a Free route's exclusion reason names the bound (`over window`,
  `over completion cap`). A paid route is flagged with the same reasons and
  stays in — capacity is buyable. Difficulty is how much deliberation a
  ticket needs — the effort intent plus the task-fit judgment; judged, never
  measured, and never compared to a window.

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
