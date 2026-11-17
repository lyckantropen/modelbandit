---
name: modelbandit
description: Pick OpenRouter models by domain popularity and price them live. Use when choosing a model for a domain — research, writing, coding, orchestration, ops — when ranking candidates by what traffic actually runs, or when costing a batch of agent runs against a budget. Use when asked to migrate from the old names — `modelrouter`, `modelbind`, `bind.py`, old paths.
compatibility: "Python 3, stdlib only — no dependencies, no environment to provision. The summaries-refresh procedure and the unit test suite live in the repository checkout (research/, tests/), not in this skill folder: with a skill-folder-only install the refresh offer reports what is due and where the procedure lives instead of running it."
---

# Modelbandit

The ranking is popularity — what real traffic actually runs in the domain, not
benchmarks, reputation, or curation. The task order is that ranking priced at
effort. Task fit is judged from the research summaries; user taste tilts only
the multi-ticket deal. Prices are live; quality is claimed only where the
research cites it. The work also carries one effort coordinate — how hard the
mind deliberates (`glance` / `measured` / `thorough` / `exhaustive`) — resolved
to a rung on each candidate's ladder.

On a migrate request or old-name keywords, read `migrate.md` and follow it.

## One interaction loop

The skill runs one loop, stated once: **assess** silently, **deal**,
**present** the deal, and **offer changes**. Assessing is the run's own
work — you name the run's ticket files and the script reads them itself,
applying the built-in checks at deal time: the Secrets gate's credential,
identifier, machine-fact and gitignored-content rules over the material
each ticket carries, with no pre-flight choreography and no setup files.
Tickets that are not Sensitive are ordinary tickets and are dealt across the
eligible pool; tickets that trip are reported held — `held: <ids> (sensitive)` —
never silently dropped and never escalated to a cloud route; a follow-up
run deals them local-only, one shape per invocation. Presenting and
offering changes are the only places you are asked: when a held ticket has
no eligible local candidate, or when you want a change to the presented
deal.

Two one-line rules hold the loop. The mechanical floor (ADR-0011) decides
forever where a future check belongs: facts and arithmetic stay mechanical;
editorial completeness is a mark in the table. And the closed-area rule is
short — a blocked task names the zone, stops, and asks: the run's header
states the posture in force and `blocked: free-use zone` says why the
remote routes are absent. No ceremony beyond that.

## Steps

1. **Collect the demand.** Domain (one of the five in `policy.json`), effort
   intent, tickets, budget. The token profile defaults to the domain; output
   volume is the cost driver for authoring work and is stated before pricing.
   The run names its ticket files and the script reads them itself: the
   built-in credential, identifier, machine-fact and gitignored-content
   rules apply at deal time to the material each ticket carries — no
   invocation choreography, no project rules file, nothing to remember
   before a model is chosen. Sensitivity is computed once, when the run's
   shape is constructed, and derived thereafter — never a mood declared
   mid-run. A ticket the rules trip is reported held (`held: <ids>
   (sensitive)`), kept out of the ordinary deal, and waits for a follow-up
   local-only run — never sent to a cloud route, never silently dropped.
   Done when: each input is stated or defaulted and none is guessed — the
   ticket files named, the assessment left to the deal-time check.

2. **Pull popularity.** Run `scripts/modelbandit.py` (mechanics: `--help`). It reads
   the task-classification leaderboards and the daily token rankings, cached
   24h, and prices every candidate at live rates. Every run's header states
   the effective zone posture — `zone: open` or `zone: closed` — and a run
   on an undeclared machine states `open` with no warning and no nag: open
   unless declared is the default, and the zones file is only an opt-out
   list of closed paths. A closed posture removes every remote Free route
   before anything else happens: those candidates are never ranked, scored,
   dealt or listed, and the `zone:` line is the explanation for their
   absence, the reason named `blocked: free-use zone`. Locally served
   models stay; the Exposure, Footprint and quota gates keep their marked,
   never hidden behaviour. `--check-policy` and `--assert-allowed` report
   the same effective posture.
   Done when: candidates are ranked by their share of the domain's traffic,
    prices and data timestamp shown. Cataloged
    OpenCode `opencode/*` models
    also appear; OpenRouter `:free` routes retain their own slug. Local
    models come from the harness alone: pass the harness's `lmstudio/*`
    ids with `--local-listing` (comma-separated, e.g. from
    `opencode models`), and each id matched by a `free_models` entry with
    `local` Exposure joins that run's candidate set exactly as the harness
    dispatches it — no flag, no local candidate, whatever the probe sees.
    The script silently probes the serving endpoint the harness config
    declares for two narrow facts only (the live context window the Context
    gate judges, and whether a listed id serves right now); probe results
    are not cached or written to policy, and a missing server has no effect
    on output. `local` Exposure resolves only for a loopback endpoint on
    this machine: a LAN-served instance reads as exposed (`trains`) until
    the policy's `exposure` override map declares it. A Free route without
    a resolving summary stays in the table, marked as a Gap with one prose
    line — editorial completeness is never an admission verdict (the
    mechanical floor in **One interaction loop**). The same run reads the
    account's daily free-request
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
   alone. Exposure does not move it; the Exposure gate does. A Plan route
   prices as risk of its list-priced Draw by the same one rule (ADR-0006);
   only where there is no Draw does the Nominal floor answer.
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
   multi-ticket run gets a deal instead of a monoculture — `modelbandit.py --deal
   --seed <project-name>` spreads tickets per ticket shape across the eligible
   pool by seeded draw from a preference-tilted blend of the fit-adjusted
   scores (`policy.json` `affinity`). Deterministic in the seed: the same
   project replays the same deal. Budget pressure moves within the order
   toward cheaper rows — never outside the popularity set. The deal reports
   its Free share — the fraction of tickets Free routes drew — reported,
   never capped and never floored: a shape may be dealt entirely to Free
   routes. Beside it the deal always prints `plan share: N/M tickets (P%)`
   — the plan rows' tickets over the dealt tickets, a ticket a Twin absorbed
   counted metered — so the market mix is visible at a glance, and
   `local share: N/M tickets (P%)` — the tickets this machine's own
   servings drew — so how much of the deal stays on local hardware reads
   at the same glance. On a shape a band-passing local candidate fits,
   that local row carries a **standing favor** in the draw — the affinity
   factors' validated favor multiplied into its pref — so small tickets
   genuinely land on local hardware instead of losing to discounted
   popularity; the seeded draw still decides which row takes each ticket,
   and score, Nominal floor and balance are untouched. A plan row at
   its cap hands its ticket to its family's **Twin** — the same model served
   metered, resolved through the `plans` entry's declared `family_ref` — and
   the flip is plan → metered only, never the reverse; only when no Twin
   resolves does the ticket fall through to the next row that still fits.
   The pick follows the same rule degenerately: an at-cap top pick names its
   Twin. Plan tickets carry their budget facts: the deal prints an
   `allowance draw:` line per plan model and the pick names the Draw beside
   the cash price (see **Plan readout**).
   Every dealt row also names its **Spare** — the highest-Score eligible
   candidate that missed the draw (no-load failover preferred on
   non-sensitive shapes, local candidates only on Sensitive ones) — so a
   dead model never strands the ticket; when the served model fails,
   re-run the deal's own flags with `--substitute <model>` to record the
   Spare taking the ticket over whole, reason and fence restated (see
   **Spares & substitution**). The deal also states the **lane**: one
   strict lane, no two local runs concurrent — `ticket ids: <ids> ->
   <model>` lines map the batch (numbered from 1 in the deal's assignment
   order) to its models, and `lane: <ids> -> <model>` lines group the
   local-dealt ids by served model, so execution runs one model load at
   a time (see **Concurrency lane**). Substitution moves lane membership
   with the serve — a cloud Spare's ids exit the lane, a local Spare's
   join — and the record says which.
   One invocation deals one ticket shape — a run's domain, effort, token
   profile, `--fit` and `--sensitive` combination — so tickets of the same
   shape share one task-fit assessment by construction: the step-4 judgments
   are made once for the run and every ticket the deal draws inherits them.
    A run of a different shape is a different invocation. Every dealt and
    picked id is provider-qualified in the form a model config dispatches —
    `openrouter/<slug>` for an OpenRouter serving (a `:free` slug included),
    and `opencode/*`, `opencode-go/*` or a local id unchanged — so no slug
    archaeology stands between the deal and the run. That qualification never
    vouches for the harness's catalog: before assigning a dealt id, verify it
    resolves there, checking the market each row names (for example,
    `opencode models` for a harness id); if it does not, substitute the
    nearest cataloged sibling of the same family. The script never shells out
    to a harness — this residual check is yours.
    A local row that survives to a run is briefed from `steering/` beside
    this file: `steering/operating-discipline.md` — the shared skeleton
    (edit discipline, evidence-per-criterion reporting, environment
    workarounds, orchestrator stop rules) — plus `steering/<model>.md` for
    that row's failure-mode clauses and prompting facts. Compose the spawn
    brief from both, citing the run record the clauses come from, and treat
    a local model's self-reported success as telemetry: verification
    against the ticket's criteria is the only delivery signal.
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
   `research/README.md`, and the offer names the scope command —
   `modelbandit.py --check-policy --scope`, which reports the drift plus the facts
   behind each finding — as where the cycle starts. With only the skill
   folder installed (no checkout) the offer degrades: report what is due and
   name the summaries-refresh procedure — it lives in the repository
   checkout, beyond this skill folder — and never emit a path that cannot
   resolve. Signal drift is taste maintenance: report it, never fix it — the
   user edits fit and evidence.
   Done when: a due policy has been surfaced to the user with an offer to
   update — never silently ignored.

## Reference

The glossary owns what the terms mean; the entries below keep the
operational shapes only — readouts, flags, exit statuses — so no term is
defined twice.

- **Domains** — five, mapped to leaderboard tags in `policy.json`: research,
  writing, coding, orchestration, ops. A tag may serve two domains (a lens, not
  a partition). Edit the map there and nowhere else.

- **Free catalog** — `policy.json`'s `free_models` maps id prefixes to
  `context_length` (positive tokens), `exposure` (`no-retention`, `trains`, or
  `local`), optional `summary_ref` (an exact key in `summaries`), and optional
  `max_completion_tokens` (a Free entry's completion cap when no endpoint
  reports one).
  `opencode/*` and local entries carry their own window in the catalog; a
  missing summary marks the route, it does not exclude it.
  A `local` exposure on an `opencode/*` or `:free` entry is a contradiction —
  those are remote serving identities — and stops the run naming the entry.
  Ranked OpenRouter `:free` routes use their own slug and may resolve a summary
  by longest prefix without a `free_models` entry; their context window comes
  from the OpenRouter model catalog when available. A Free route without a
  resolving summary is marked in the table plus one prose line, never
  excluded. OpenCode entries are listed from this
  catalog. An entry with `local` Exposure raises a candidate only for an id
  the harness listing carries (`lmstudio/*` classifies local by the namespace
  itself); its curated window and summary remain policy facts, while the
  probe contributes only the live window the Context gate is judged against
  and the live-serving fact — never identity, never existence. Probe results
  join the in-memory model catalog for that invocation only. A missing server
  has no effect on output. The policy check names local entries the harness
  cannot run (`## Local models the harness cannot run`): reported, never
  dealt.

- **Plan catalog (`plans`)** — `policy.json`'s optional `plans` maps a Plan
  route's id (`opencode-go/*`) to the facts the ledger and the Exposure
  verdicts read: `list_price` (the Draw's basis — a non-negative number, where
  `0` is the free-in-plan, zero-Draw serving), `caps` carrying a positive
  `five_hour`, `weekly` and `monthly` dollar figure, `exposure` (`no-retention`
  or `trains`; `local` contradicts the remote serving identity), `family_ref`
  (the family link: the Twin's Metered serving id, e.g.
  `deepseek/deepseek-v4-pro` for its `opencode-go/*` plan serving), and
  optional `regions` (a list of non-empty strings). It is validated loud at
  both shared loaders, exactly like `free_models`: an unknown shape, a bad
  number, a misspelt Exposure, an id the Route kind does not answer `plan`, or
  a `family_ref` that names no Metered route stops the run naming the entry
  (status 4), never a silent default. Twins are found through that declaration
  alone — vendor prefixes differ per family, so nothing derives a Twin from an
  id's shape. The section is its own catalog — `free_models` keeps refusing
  plan-kind entries in parallel.

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

- **Risk of Draw** — the one marginal-zero rule at the score (ADR-0006): a
  marginal-zero ticket prices as risk of its Draw, never at $0. A Plan route
  prices at `scoring.free_risk` times its own list-priced Draw, so a cheap-Draw
  serving outscores a dear-Draw one at equal share and fit and scarce Allowance
  flows to the workhorse. Where there is no Draw — a Free route, a zero-Draw
  plan serving, a plan route the catalog does not price — the **Nominal floor**
  answers (Free risk times the pool's cheapest paid ticket, or the $1 reference
  when the pool has none). The Free case keeps its exact current numbers.

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

- **Allowance & Draw** — a Plan route serves at $0 cash only while its
  **Allowance** holds: the dollar budget the `plans` section states per model
  across three windows — the rolling 5-hour window, the week and the month.
  One ticket burns its own list price (its **Draw**) from all three windows at
  once, because the batch is assumed to land in one 5-hour burst: a run on
  course to cross a window is flagged by the run that would cross it, not
  discovered after the monthly total is gone. The ledger is prospective,
  in-run and stateless — it starts every run empty, reads no account state and
  writes none, so two identical runs answer identically and a plan other
  harnesses share is never planned against a local fiction. The caps are real
  boundaries: no reserve is held back, no overflow flag exists, and a row
  whose next ticket's Draw would cross any window hands its ticket to its
  **Twin** — the family's Metered serving the `family_ref` declaration
  names: same model, identity preserved, market flipped plan → metered, one
  direction only, the reverse never (ADR-0007). The Twin's tickets charge
  cash, not Allowance, and count metered on the `plan share:` line; only a
  row whose declared link resolves no eligible Twin leaves the pick and the
  deal for the tickets that remain, the batch continuing with the rows that
  still fit. The ledger itself never substitutes — resolution is the deal's
  market adapter (and the pick's degenerate form of it), never the ledger's.
  A plan row enters the pool at split family
  share: a family served twice — its Metered twin and its plan serving —
  divides its board share across both full-quality rows, so the family's
  standing is counted once, while a family with one full-quality serving keeps
  its share whole. A Plan route is not a Free route: the zone gate does not
  refuse it and the free counter does not count it.

- **Free-use zones** — the zones file lives at the machine's config root
  (`$XDG_CONFIG_HOME/modelbandit/zones.json`, else
  `~/.config/modelbandit/zones.json`) and is a bare list of closed paths —
  `{"zones": ["<path>", ...]}` — so the exception list is the whole schema.
  `~` and environment variables expand, paths compare the way the platform
  does, and the longest covering prefix wins. `--write-zones` reads that
  JSON from stdin and writes the file validated and atomically — an invalid
  file refuses with status 4 naming the offending entry and writes
  nothing; no mode needs the file hand-written. The header states the
  effective posture (`zone: open`, `zone: closed`) on every run; a closed
  posture drops every remote Free route (`:free`, `opencode/*`) at source —
  never ranked, scored, dealt or listed — and the `zone:` line is the
  explanation for their absence, the reason named `blocked: free-use zone`.

- **Pre-flight (`--assert-allowed`)** — `scripts/modelbandit.py --assert-allowed
  --model <id> --working-dir <folder>` answers one question for an
  orchestrator: may this model serve in that folder's effective zone? The
  output answers — `allowed: <id>`, `blocked: free-use zone`, or
  `blocked: unknown serving namespace` — and every verdict exits **0**
  (status says the tool ran; output says what's
  true); **4** is a policy/config error and **2** a usage error, and neither
  is an answer: default-deny, launch only on `allowed`. `--json` answers
  with one object (`allowed`, `zone`, `reason`) instead of the lines. The
  output names the effective posture (`zone: open`, `zone: closed`) and
  states the shape it judged — `shape: sensitive (assumed)` with none
  stated, because the dispatch fails closed; `shape: plain (via --plain)`
  when `--plain` states the material is not Sensitive;
  `shape: sensitive (via --sensitive)` when the default is restated — and
  then the verdict with model and reason; it
  never carries the shape's content. It needs no policy file, no classification
  fetch and no network —
  a missing policy is an empty policy, so a route the file does not describe
  resolves by the defaults (a `:free` or `opencode/*` route exposed, a paid
  route no-retention, a cataloged `local` entry local).
  `--plain` states a shape, never a zone — it cannot open a closed place.
  Refuse to launch a model the pre-flight
  blocks instead of substituting one.

- **Exit statuses** — **0** ran to completion: any verdict — safe,
  sensitive, not certified, allowed, blocked: free-use zone, blocked:
  unknown serving namespace, over-budget, empty pool, blocked: no eligible
  local candidate. **1** carries no contract
  meaning: what CPython and generic operational failures (network
  unreachable, unreadable input) produce — never an answer. **2** usage
  errors (argparse's own channel). **4** rules/config error (secrets rules,
  zones file or policy): the tool could not form a verdict, so it stays
  nonzero and `&&`-chains stay fail-closed on errors. The retired answers —
  1 for Sensitive, 3 for not certified, 5 for the zone block, 2 for
  over-budget — live in the output now: read the verdict lines (or
  `--json`), not `$?` (ADR-0004). A block is never reported as sensitive,
  safe or over budget.

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
  avoid/suspected ×0.5). Longest prefix wins. A band-passing local row
  additionally carries a **standing favor**: the factors' validated favor
  multiplied into its pref by the deal (the caller's local rows only —
  never eligibility, never score), so a qualifying shape genuinely deals
  local hardware while the seeded draw still picks the row. The deal is the
  only place taste acts — the ranking itself is never reordered. Every dealt
  row is named by its provider-qualified id (see **Pick line**), so a row is
  a dispatch, not an interpretation. Its Free share — the fraction
  of tickets Free routes drew — is a report, never a cap and never a floor:
  some tickets, all of them, or none, as the draw falls. Beside it, the deal
  always prints `plan share: N/M tickets (P%)` — plan tickets over dealt
  tickets, an absorbed ticket counted metered — and
  `local share: N/M tickets (P%)` — this machine's own servings over dealt
  tickets.

- **Spares & substitution** — every dealt row names exactly one **Spare**:
  the highest-Score eligible candidate that missed the draw, shown in the
  deal table's `spare` column (`-` on a row that missed the draw itself,
  `none` plus a `spare:` note when every eligible candidate is dealt) and,
  on a budgeted `--json` run, in `spares` keyed by provider-qualified id.
  Score is the table's own fit-adjusted number. On a non-sensitive shape
  the Spare prefers a candidate that serves without a model load — a cloud
  route fails over in seconds where a local swap is minutes — Score
  breaking the ties inside that class, and a load-required local candidate
  standing only when no no-load candidate missed the draw. On a Sensitive
  shape the Spare is drawn from local candidates only: the fence is
  restated, never re-gated, so substitution can never loosen the gate.
  Substitution is an invocation, not stored state — modelbandit is
  stateless and the draw is seed-deterministic, so re-run the deal's own
  flags plus `--substitute <dealt-id>` and the identical deal re-derives;
  the record replaces the deal readout's tail and the run exits 0:
  `substitution: <model> -> <spare>`, then indented `reason:` (mechanical —
  unreachable, out of quota or allowance, unloadable, substituted
  automatically; or dead-attempt — the harness's explicit failed-attempt
  report), `takeover:` (the spare restarts the ticket whole) and `fence:`
  lines — the Spare's band, `sensitive — local-only (ADR 0008)` and the
  non-leak note on a Sensitive ticket. Reasons distinguish class:
  `--reason mechanical` (the default — unreachable, out of quota or
  allowance, unloadable) substitutes automatically; `--reason dead-attempt`
  carries the harness's explicit failed-attempt report — the only way a
  quality failure substitutes. `--reason quality` alone is refused
  (`substitution refused: …`, exit 0, `refused` in `--json`), so taste
  never reshuffles work mid-run. Exhaustion — no candidate missed the
  draw — answers `blocked: no eligible … missed the draw for <model> (…)`,
  exit 0: terminal for Sensitive (the local-only fence is never re-gated),
  a non-sensitive run failing only after the no-load failover preference
  has had its pick. Blocked and substituted outcomes exit 0; a target
  outside the re-derived deal is a usage error (2). The record is the
  audit trail: modelbandit deliberately stores no substitution state
  (the draw is seed-deterministic and re-derivable), so the harness
  records each substitution record the invocation prints in its own run
  log — substitution, reason, takeover and fence together — and that
  record is what makes every takeover auditable.

- **Concurrency lane** — the deal's statement of mutual exclusion: one
  strict lane of the local-dealt ticket ids, no two local runs concurrent,
  same model or not (the single lane is the whole answer; load management
  stays with the serving stack). Ticket ids number the batch from 1 in the
  deal's assignment order — ticket i+1 is the draw keyed `seed::i`. The
  readout maps every dealt id with `ticket ids: <ids> -> <model>` lines
  (deal-row order) and prints the lane: `lane: strict — one local run at a
  time (grouped by model)` followed by one `lane: <ids> -> <model>` line per
  local-served group — groups ordered by each model's first assignment, ids
  ascending inside a group — or `lane: none — no local-dealt tickets`. The
  budget `--json` carries `lane` as a list of `{model, tickets}` groups
  (empty when no local drew) and `tickets_by_model`, the full id → model
  map; non-local tickets never appear in the lane. Membership follows the
  served model under substitution: a substitution record prints `lane:` —
  ids exit when the Spare is cloud, join when it is local, move between
  groups when both are local, `unchanged` when neither serves local — and
  its `--json` answers with the post-substitution lane, computed from the
  same seeded deal with the new serve swapped in. The published chain stays
  put: the lane record is the truth that substitution follows.

- **Plan readout** — a deal that drew plan tickets prints, per plan row with
  tickets, `allowance draw: <model> $X of $Y (Z% of monthly; W% of 5h)` — `$X`
  the Draw this run allotted the model and `$Y` its monthly cap. When the pick
  is a plan row its line names the Draw beside the cash price — `default pick
  (top of task order): <model> ($X/ticket; Draw $Y/ticket)`. A pick whose plan
  row is at cap names the family's Metered Twin instead — same model, metered
  market — and the pick line names the Twin's qualified id: the id shows the
  market, so a metered pick states no price and no Draw — `default pick (top of
  task order): <model>`. The projection keeps its dollar total unchanged:
  plan-aware totals come later.

- **Pick line** — the pick names its market as the provider-qualified id a
  model config dispatches (`<provider>/<model>`): `openrouter/<slug>` for an
  OpenRouter serving (a `:free` slug included), and `opencode/*`,
  `opencode-go/*` or a local id unchanged. The deal's model column uses the
  same form; a pick that lands on a Twin names the Twin's qualified id.

- **Secrets gate** — the built-in credential, identifier, machine-fact and
  gitignored-content rules, applied to the material a run is given:
  automatically at deal time, when the run reads its own ticket files, and
  manually via `scripts/modelbandit.py --check-secrets
  [--working-dir PATH]` for a single material on stdin, with repeatable
  `--outside-file PATH` arguments for named outside content. It needs no
  policy and no network; the material is the agent's to supply (the tool
  never reads it for you). The check assembles everything mechanical: this
  machine's identifiers (hostname, login, home path, non-loopback local
  address, each best effort and never shorter than four characters), the
  significant lines of the working folder's gitignored untracked files
  (`git ls-files --others --ignored --exclude-standard`, twenty files of up
  to 8 KB each), and the capped content of every named outside file. It
  names the rule that tripped it and echoes no rule *value*, only its class
  or index (`phrase #1`), so its output is safe to quote back. A named
  `--outside-file` from a closed place is refused, and the refusal names
  the zone, never the material. Exit status (**0** for every verdict, **2**
  usage error, **4** rules/config error; see **Exit statuses**) — the
  printed lines say which: safe, sensitive, not certified (**not
  certified** = no material given, never "safe").

- **Exposure & Sensitive** — on a sensitive shape only Exposure `local` may
  serve (ADR 0008): every non-local route — `no-retention` alike with
  `trains`, paid included — is excluded from the pick and the deal, marked
  in the table with the reason (`exposed (no-retention)`, `exposed
  (trains)`), never hidden; only local models stay admitted, and a
  sensitive shape with no eligible local candidate stops with `blocked: no
  eligible local candidate` (exit 0 — the report is the human escalation,
  never a re-gate). A deal touching Sensitive material carries the standing
  non-leak note — a contract marker for the harness to apply at prompt
  time; the prompt itself stays the harness's to author. One admission
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
