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

## Steps

1. **Collect the demand.** Domain (one of the five in `policy.json`), effort
   intent, tickets, budget. The token profile defaults to the domain; output
   volume is the cost driver for authoring work and is stated before pricing.
   Apply the Secrets gate to the shape's material — always, before choosing a
   model. Run `scripts/modelbandit.py --check-secrets --working-dir <folder>` with the
   shape's material on stdin; add a repeatable `--outside-file PATH` for each
   named outside source that contributes content. Each named file contributes
   only a capped slice. The gate does the mechanics itself: it reads the
   project's `modelbandit.secrets.json` (at the folder's git root, when it is
   in a repository), gathers this machine's hostname, login, home path and
   local address, reads content from the folder's **gitignored** files, and
   checks the named outside files — no assembly by you. It reports safe,
   sensitive or **not certified**, and names a rule when one trips it
   (`hostname`, `username`, `home path`, `local address`, `gitignored content
   (.env)`, outside-file content, a credential pattern, `phrase #N`,
   `pattern #N`). Every verdict exits **0** — safe, sensitive, **not
   certified** (no material given, never read as safe), or **blocked by the
   free-use zone**: a named outside source whose effective regime is closed
   (including the undeclared closed default), or a `--model` its effective
   zone cannot admit — and the printed lines say which: status says the
   check ran, output says what's true (ADR-0004). **2** is a usage error,
   **4** a rules/config error. A block is a stop, never a Sensitive verdict —
   see **Closed-zone protocol** below.
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

2. **Pull popularity.** Run `scripts/modelbandit.py` (mechanics: `--help`). It reads
   the task-classification leaderboards and the daily token rankings, cached
   24h, and prices every candidate at live rates. Every run's header states
   the free-use zone that governed it - `zone: <path> (<regime>)`, or
   `zone: undeclared (closed)` when no declared path matched. If `--sensitive`
   tightens an open zone, the header says `(open; sensitive via --sensitive)`.
   A zone is the place a path reaches, not the string it is spelled with:
   junctions and symlinks are resolved before matching, and when the resolved
   place differs from the declared path the header names it -
   `zone: <resolved> (<regime>) (declared: <path>)`, or `(... ) (undeclared)`
   when no declaration matched.
   `--check-policy` and `--assert-allowed` report the same effective posture.
   A closed effective regime removes every remote Free route before anything
   else happens: those
   candidates are never ranked, scored, dealt or listed, and the `zone:` line
   is the explanation for their absence. Locally served models stay; Exposure,
   Footprint, quota and catalog exclusions keep their marked, never hidden
   behaviour.
   When the zones file is absent or the effective posture is `zone:
   undeclared (closed)`, surface that to the user and offer to run **Set up
   the free-use zones** below before this run relies on free routes: with
   nothing declared, remote free routes (`:free`, `opencode/*`) are excluded
   from this run. Offered every time it applies, never silently skipped —
   the same discipline as the due policy in step 7.
   Done when: candidates are ranked by their share of the domain's traffic,
    prices and data timestamp shown. Cataloged
    OpenCode `opencode/*` models
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
   alone. Exposure does not move it; the Sensitive gate does. A Plan route
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
   counted metered — so the market mix is visible at a glance. A plan row at
   its cap hands its ticket to its family's **Twin** — the same model served
   metered, resolved through the `plans` entry's declared `family_ref` — and
   the flip is plan → metered only, never the reverse; only when no Twin
   resolves does the ticket fall through to the next row that still fits.
   The pick follows the same rule degenerately: an at-cap top pick names its
   Twin. Plan tickets carry their budget facts: the deal prints an
   `allowance draw:` line per plan model and the pick names the Draw beside
   the cash price (see **Plan readout**).
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

## Closed-zone protocol

The machine-wide `zones.json` decides where free models may run: a path
declares `open`, `sensitive` or `closed` for everything under it, the three
order `open` < `sensitive` < `closed`, and anything undeclared is `closed`. The
regime a run works under is the **stricter** of its working folder's zone and
the zone of the repository the folder came from (the parent of
`git rev-parse --git-common-dir`), so `closed` implies `sensitive` and every
stricter regime dominates the milder ones in every dimension.
Headers state the effective posture; an open zone tightened by `--sensitive`
is shown as `zone: <path> (open; sensitive via --sensitive)`.

A **closed area** is a path whose effective regime is `closed`. In a closed
area:

1. **Never read, list, grep, summarise or copy anything for any reason.**
   Not to answer a question, not to check whether something is there, not
   "just the headings". A closed zone is closed to free *and* to your own
   reading — the free-route exclusion in the ranking is one consequence, not
   the rule.
2. **When a task cannot be completed without it, stop.** Say which zone blocks
   it (`zone: <path> (closed)`) and why the content is unavoidable, and wait
   for the user to open the zone or move the task. An undeclared path has the
   default `closed` regime and blocks in the same way.
3. **Never route around the block.** Do not substitute a paid model for a
   closed zone — a closed zone is closed because of where the content is, not
   because of what the route costs. Do not reclassify the shape (`--sensitive`
   cannot loosen a zone, and asking is not a substitute for opening it), do not
   copy the material elsewhere to get it out, and do not treat a Sensitive
   verdict as permission.
4. **Check before launching.** The ranking's header names the zone; when an
   orchestrator holds a model id — from a plan, a previous run, another
   agent — run the pre-flight below before launching it:

   ```bash
   scripts/modelbandit.py --assert-allowed --model <id> --working-dir <folder>
   ```

   Launch only when the pre-flight says `allowed` — an error, a missing
   field, a malformed response, anything else means do not launch. The
   verdict lines carry the answer, and every answer exits **0**: `allowed:
   <id>`, `blocked by the free-use zone`, or `blocked: unknown serving
   namespace` — with effective posture and regime named (never content) —
   status says the pre-flight ran, the lines say what's true. The dispatch fails closed: with no shape stated the pre-flight assumes the
   material is Sensitive and says so (`shape: sensitive (assumed)`), so a
   route that retains training data is refused by default; when you know the
   material is not Sensitive, say so explicitly with `--plain`
   (`shape: plain (via --plain)`), and `--sensitive` merely restates the
   default. The pre-flight reads
   the zones file and, when present, the local policy's Exposure facts: no
   policy file, no classification fetch, no network. Status **4** is a
   policy/config error and **2** a usage error — neither is an answer, and
   neither launches.

Exposure exclusions stay visible: in a `sensitive` or `closed` zone the table
marks an exposed (`trains`) route with its reason and never picks or deals it,
because that is the shape's decision, not the zone's prohibition.

### Worktrees

Worktrees are created by the harness, outside their repository. An **undeclared
worktree root stays closed**: undeclared is closed and the stricter of the two
zones wins, so a worktree living under an undeclared path is closed no matter
how open its repository is. To let the origin repository's zone decide —
package work should be judged by the content it holds — declare the directory
the worktrees live in `open`:

```json
{"zones": [{"path": "~/.opencode/worktrees", "free": "open"}], "default": "closed"}
```

The effective regime is then the origin repository's (`closed` for a private
repository, `open` or `sensitive` for one declared so), never the bare
worktree path.

## Set up the secrets file

When `modelbandit.secrets.json` is missing, or the user wants to tighten it,
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

   Run `scripts/modelbandit.py --write-secrets --working-dir <folder>` with that JSON
   on stdin. It writes `modelbandit.secrets.json` at the folder's git root (or
   the folder itself outside a repository), reports rules added and already
   present, and merges on every re-run: existing rules are never removed and
   exact duplicates are kept once. Its report gives counts, never rule values.
   If `identifying` is true **or** `commit` is false, it appends the file path
   to `.gitignore` once; if the rules file is already tracked, it refuses and
   tells you to run `git rm --cached modelbandit.secrets.json` first.
   Otherwise it leaves `.gitignore` alone and says the rules file is meant to
   be committed.
4. Review the writer's report and show the resulting diff. Before a re-run,
   retain the previous rules-file contents; afterwards show a unified
   before/after diff as well as the `.gitignore` diff. An ignored, untracked
   rules file will not appear in ordinary `git diff`.
5. Run `scripts/modelbandit.py --check-secrets --working-dir <folder>` with the actual
   shape material on stdin, adding `--outside-file PATH` for each named outside
   source. The gate reads the rules file itself. Every verdict exits 0 and the
   printed line says which — safe, Sensitive, **not certified** — **2** is a
   usage error and **4** a rules/config error: empty material is not safe by
   default, so obtain the material before claiming a safe shape.

## Set up the free-use zones

When `zones.json` is absent, or the user wants to move a folder's posture,
conduct this interview before a run relies on free routes — the machine
starts closed everywhere, so this is the interview's only opening move:

1. Discover candidate folders: the working folder, its repositories, and
   the worktree roots this machine's harnesses create ticket worktrees
   under. Ask one question per folder, in the user's own terms: *"may free
   models — some of which retain what you send — run on content here?"*
   and record one of the three answers:
   - `open` — free models may run on content here, whatever a route retains.
   - `sensitive` — a free route that may retain what you send (`trains`) is
     excluded; no-retention free routes and models served on this machine
     stay.
   - `closed` — no remote free route may run here at all; models served on
     this machine never leave it and stay in.
2. Carry the worktree-root rule from **Closed-zone protocol** into the
   answers: an **undeclared worktree root stays closed** however open its
   repository, so ask about the directory the worktrees live in and declare
   it — that lets the origin repository's zone decide the worktree's
   posture, never the bare path the worktree happens to sit on.
3. Anything unasked stays `closed`: the interview can open less, never
   more. `"default"` stays `"closed"` and the file lists only the folders
   the user actually answered for.
4. Propose the resulting JSON in full:

   ```json
   {"zones": [{"path": "~/work", "free": "open"}], "default": "closed"}
   ```

   Write it with `scripts/modelbandit.py --write-zones`, the JSON on stdin —
   no mode ever needs this file hand-written. It validates before it writes:
   an invalid config refuses with status 4 naming the offending entry and
   writes nothing, so an attempt over an existing file cannot corrupt it.
   Then have the user review the printed path and the file's contents before
   anything relies on them, and verify afterwards — the next run's `zone:`
   header, or `scripts/modelbandit.py --assert-allowed --model <id>
   --working-dir <folder>`, states the posture now in force.

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
  A `local` exposure on an `opencode/*` or `:free` entry is a contradiction —
  those are remote serving identities — and stops the run naming the entry.
  Ranked OpenRouter `:free` routes use their own slug and may resolve a summary
  by longest prefix without a `free_models` entry; their context window comes
  from the OpenRouter model catalog when available. A Free route without a
  resolving summary is never admitted. OpenCode entries are listed from this
  catalog. Entries with `local` Exposure are listed only while a matching id is
  served by the silent LM Studio probe; their context window and summary remain
  curated policy facts. Probe results join the in-memory model catalog for that
  invocation only. A missing server has no effect on output.

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

- **Free-use zones** — `zones.json` at the machine's config root
  (`$XDG_CONFIG_HOME/modelbandit/zones.json`, else
  `~/.config/modelbandit/zones.json`): `{"zones": [{"path": ..., "free":
  "open" | "sensitive" | "closed"}], "default": "closed"}`. `~` and
  environment variables expand, paths compare the way the platform does, and
  the longest covering prefix wins; anything undeclared takes `default`. A
  missing file means the default everywhere. Validation is loud — an unknown
  key, a non-list `zones`, a non-string path or an unknown regime stops the
  run naming the entry index — and the built-in default is additive-only, so
  no file can open what the machine closed. The regime a run works under is
  the stricter of the working folder's zone and the origin repository's
  (`git rev-parse --git-common-dir`, its parent); git missing or failing
  leaves the working folder's zone alone. `open` and `sensitive` are today's
  behaviour. A `closed` zone removes every remote Free route (`:free`,
  `opencode/*`) at source — never ranked, scored, dealt or listed — and admits
  locally served models, which never leave the machine; a paid no-retention
  route still serves. Exposure exclusions are the shape's, not the zone's, so
  they mark and never hide, and because `closed` implies `sensitive` an
  exposed *paid* route is excluded there exactly as under `sensitive`. For
  setup, follow **Set up the free-use zones**; `--write-zones` reads the
  interview's proposal from stdin, validates it through this loader's
  rules, and writes the file atomically — no mode needs `zones.json`
  hand-written.

- **Pre-flight (`--assert-allowed`)** — `scripts/modelbandit.py --assert-allowed
  --model <id> --working-dir <folder>` answers one question for an
  orchestrator: may this model serve in that folder's effective zone? The
  output answers — `allowed: <id>`, `blocked by the free-use zone`, or
  `blocked: unknown serving namespace` — and every verdict exits **0**
  (status says the tool ran; output says what's
  true); **4** is a policy/config error and **2** a usage error, and neither
  is an answer: default-deny, launch only on `allowed`. `--json` answers
  with one object (`allowed`, `zone`, `reason`) instead of the lines. The
  output names the effective zone (`zone: <path> (<regime>)`, with
  `sensitive via --sensitive` when the flag tightens `open`, and the resolved
  place named when a link moved the judgement), states the shape
  it judged — `shape: sensitive (assumed)` with none stated, because the
  dispatch fails closed; `shape: plain (via --plain)` when `--plain` states
  the material is not Sensitive; `shape: sensitive (via --sensitive)` when the
  default is restated — and then
  `allowed: <id>`, `blocked by the free-use zone`, or `blocked: unknown
  serving namespace` with model and reason; it
  never carries the shape's content. It needs no policy file, no classification
  fetch and no network —
  a missing policy is an empty policy, so a route the file does not describe
  resolves by the defaults (a `:free` or `opencode/*` route exposed, a paid
  route no-retention, a cataloged `local` entry local). Localness is a serving
  fact, never a catalogue claim: a `local` label counts only for an id the
  Route kind does not classify as a remote serving — a `:free` slug, an
  `opencode/*` model, an `opencode-go/*` plan route — so a catalogue label
  cannot make a remote route local or skip the Sensitive gate.
  `--plain` states a shape, never a zone — it cannot open a closed area.
  Refuse to launch a model the pre-flight
  blocks instead of substituting one.

- **Exit statuses** — **0** ran to completion: any verdict — safe,
  sensitive, not certified, allowed, blocked by the free-use zone, unknown
  serving namespace, over-budget, empty pool, no candidate admitted. **1** carries no contract
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
  avoid/suspected ×0.5). Longest prefix wins. The deal is the only place taste
  acts — the ranking itself is never reordered. Every dealt row is named by
  its provider-qualified id (see **Pick line**), so a row is a dispatch,
  not an interpretation. Its Free share — the fraction
  of tickets Free routes drew — is a report, never a cap and never a floor:
  some tickets, all of them, or none, as the draw falls. Beside it, the deal
  always prints `plan share: N/M tickets (P%)` — plan tickets over dealt
  tickets, an absorbed ticket counted metered.

- **Plan readout** — a deal that drew plan tickets prints, per plan row with
  tickets, `allowance draw: <model> $X of $Y (Z% of monthly; W% of 5h)` — `$X`
  the Draw this run allotted the model and `$Y` its monthly cap. When the pick
  is a plan row its line names the Draw beside the cash price — `default pick
  (top of task order): <model> ($X/ticket; Draw $Y/ticket)`. A pick whose plan
  row is at cap names the family's Metered Twin instead — same model, metered
  market — with its own cash price and no Draw: `default pick (top of task
  order): <model> ($X/ticket)`. The projection keeps its dollar total
  unchanged: plan-aware totals come later.

- **Pick line** — the pick names its market as the provider-qualified id a
  model config dispatches (`<provider>/<model>`): `openrouter/<slug>` for an
  OpenRouter serving (a `:free` slug included), and `opencode/*`,
  `opencode-go/*` or a local id unchanged. The deal's model column uses the
  same form; a pick that lands on a Twin names the Twin's qualified id.

- **Secrets gate** — the collect-demand check that makes a shape Sensitive,
  run as `scripts/modelbandit.py --check-secrets [--working-dir PATH]` with the
  material on stdin and repeatable `--outside-file PATH` arguments for named
  outside content. It needs no policy and no network; the material is the
  agent's to supply (the tool never reads it for you). It prints the zone it
  judged by (`zone: <path> (<regime>)`, with the resolved place named when a
  link moved the judgement) and names the rule that tripped it.
  Exit status (**0** for every verdict, **2** usage error, **4**
  rules/config error; see **Exit statuses**) — the printed lines say which:
  safe, sensitive, not certified (**not certified** = no material given,
  never "safe"), or blocked by the free-use zone. The zone answer comes
  before the content does and names the zone, never the material: a named
  `--outside-file` whose effective regime is `closed` (declared or the default,
  resolved with origin included), or a `--model` the effective zone cannot
  admit. The tool assembles
  everything mechanical: the project's `modelbandit.secrets.json` at the
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
  defaults to trains. Localness is a serving fact, never a catalogue claim: a
  `local` label counts only for an id the route predicate does not classify as
  remote. On a Sensitive shape the exposed — `trains` — are
  excluded from the pick and the deal, marked in the table with the reason
  (`exposed (trains)`), never hidden; no-retention free routes and local
  models stay admitted. Exposure, not price, decides — and one admission
  verdict serves both the table and the deal, so the two never disagree
  about what may serve a shape. A `sensitive` zone is the `--sensitive` flag
  by another name, and a `closed` zone is at least that strict: it refuses
  every exposed route a sensitive zone refuses — including an exposed *paid*
  route — on top of every remote free one. The flag can only tighten a zone;
  it can never loosen one.

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
