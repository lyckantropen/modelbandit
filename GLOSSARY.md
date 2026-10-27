# OpenRouter Model Router

Selecting OpenRouter models for a unit of work by what real traffic runs in a
domain, with live per-endpoint pricing and deliberate model diversity across a
project.

## Language

**Domain**
One of five work kinds — research, writing, coding, orchestration, ops — mapped
to OpenRouter task-classification tags.
_Avoid_: category, task type

**Rank**
A model's position on a domain's popularity board. Popularity is request share
per task tag; it is revealed preference of real traffic, not quality.
_Avoid_: score, rating, standing

**Eligibility**
The set of models the selection may draw from. Decided by popularity alone.
_Avoid_: candidate pool, shortlist

**Deal**
The distribution of a batch's tickets across eligible models, drawn by a seeded
preference-tilted process. Exists so a project does not run one model for
everything.
_Avoid_: assignment plan, binding schedule

**Ticket shape**
A run's (domain, effort, token profile, `--fit`, `--sensitive`) combination.
One deal deals one shape; same-shape tickets share one task-fit assessment by
construction.
_Avoid_: batch, group

**Score**
A model's per-task baseline value: popularity share to the α power over priced
cost to the β power. Deterministic and taste-free; it orders candidates and
nothing more. The exponent ratio orders, the scale sharpens.
_Avoid_: ranking score, rating

**Score mass**
The share of total score a candidate holds in its pool. The balance criterion —
top-1 mass within 20–50%, top-2 ≤ 75% — keeps the order from going uniform or
winner-take-all.
_Avoid_: probability, weight

**Task fit**
An agent-assigned 0–5 judgment (fractions allowed) of how well a candidate
suits a specific task — context window, rung coverage, summary-backed domain
guidance. Judged per task from the summaries, never computed.
_Avoid_: quality, capability, fit (that is the hint direction)

**Projection**
The priced cost of a run: per ticket and total, at a stated pricing basis.
_Avoid_: estimate, quote

**Exposure**
A candidate's data-handling class: no-retention (input is neither stored nor
trained on), trains (input may be stored, collected, or trained on), or local
(runs on this machine — no training, no retention). The property that gates
sensitive work; never inferred from price — free does not imply trains, paid
does not imply no-retention. Unknown free defaults to trains.
_Avoid_: privacy, data policy (an account rule, not a model property), training flag

**Sensitive**
A ticket shape whose material trips the secrets gate; exposed candidates are
excluded from it. A join of the shape — the fifth shape element, bound per
invocation (`--sensitive`) — never a mood declared mid-run.
_Avoid_: confidential, "sensitive stuff" (fuzzy), secret material

**Zone**
The machine-wide declaration of where free models may run: a path with a
regime for everything under it, resolved by longest prefix, with anything
undeclared `closed`. A run's effective zone is the stricter of its working
folder's and its origin repository's, so a worktree carries the posture of the
content it holds. Additive-only: a file can open less, never more.
_Avoid_: allowlist, permission (it is a place, not a grant)

**Regime**
One of the three zone levels — `open`, `sensitive`, `closed` — ordered, with a
stricter regime dominating every milder one: `closed` excludes everything
`sensitive` excludes, plus every remote free route.
_Avoid_: level, tier (both suggest optional strength rather than order)

**Closed area**
A path whose effective regime is `closed`: no remote free route may serve it,
and it is never read, listed, grepped, summarised or copied for any reason.
Blocked work stops and reports the zone; it never substitutes a paid model or
reclassifies the shape.
_Avoid_: private folder (a folder name, not a posture), sensitive area

**Secrets gate**
The check run at collect-demand: the project's optional secrets file
(`modelrouter.secrets.json`), falling back to the built-in default — content
from a gitignored file inside the working folder, from files outside it
(including content supplied from named outside files), passwords/tokens/keys,
and identifiers readable from this machine's state — applied to the shape's
material. Content-inclusion, any-of; a mere path mention does not trip it.
Outcome: Sensitive when an inclusion is found, safe when provided material has
none, or not certified when no material is present.
_Avoid_: detector, classifier (suggests learned behaviour; it is a list)

**Footprint**
A Ticket shape's measured demand on a candidate — input tokens times growth
headroom, and output tokens times the rung's multiplier. Compared against the
candidate's context window and completion cap. Measured, never judged.
_Avoid_: complexity, size, difficulty (that is deliberation)

**Difficulty**
How much deliberation a ticket needs: the effort intent, plus the agent's
task-fit judgment. Judged, never measured — and never compared to a window.
_Avoid_: complexity (it names both halves at once and so neither)

**Context gate**
The mechanical exclusion of free candidates whose Footprint exceeds their
capacity, on either dimension — the input budget against a share of the context
window, the rung-priced output against a share of the completion cap. Free-tier
only: a free route has no paid tier to upgrade into, so an overrun is a hard
failure, not taste. The paid tier is flagged and stays judge-only.
_Avoid_: context flooring, token cap

**Free risk**
The policy fraction of a paid ticket that a Free route is charged in the score,
standing for the expected cost of its failure modes — a re-run after a rate
limit, a route withdrawn mid-run, an outage. It is why free wins sometimes but
not most of the time, and why it may win everything on a job it genuinely fits.
_Avoid_: penalty, handicap, discount

**Free share**
The fraction of a deal's tickets that Free routes drew. Reported, never capped
and never floored: some of the time on ordinary shapes, all of it on a shape
free genuinely serves best, none when it does not stack up.
_Avoid_: quota, free budget, cap

**Free quota**
OpenRouter's daily free-request counter: one figure shared by every `:free`
route on the account, reset at UTC midnight, spent only by the routes
OpenRouter serves for nothing. Read before a plan is priced and reported in the
run header; the reserve is protected, and `:free` routes leave the pool only
when remaining quota is below it. Plan size does not gate eligibility because
the deal may draw fewer Free tickets than planned. The provider's allowance,
never a judgement of Free share.
_Avoid_: free budget, cap, rate limit (that is per minute, and unqueryable)

### Taste

**Hint**
A user observation about a model: a note, its fit per domain, and its evidence.
Weighed, not obeyed; it annotates, never reorders.
_Avoid_: verdict, preference, taste

**Fit**
The direction of a hint for one domain: favor, avoid, or neutral (explicitly no
opinion). Omitted fit is an unanswered question; explicit neutral is an
answered one. Only favor and avoid tilt the deal.
_Avoid_: affinity score, weight (it is not numeric)

**Evidence**
How settled a hint is: validated (user-confirmed) or suspected (untested).
_Avoid_: confidence, certainty

**Affinity**
The derived numeric tilt of the deal toward or away from a model, computed at
run time from fit and evidence through the factors. Never stored.
_Avoid_: weight table, preference score

**Factors**
The four multipliers mapping fit × evidence to affinity.
_Avoid_: weights, coefficients

### Cost

**Rung**
A position on a model's effort ladder, bound from the effort intent. Reasoning
tokens bill as output, so the rung is a real cost lever.
_Avoid_: effort level, tier

**Endpoint spread**
The ratio between the cheapest and dearest provider price for one model.
_Avoid_: price range

**Baseline**
The price anchor model, used for Δ columns and nothing else.
_Avoid_: reference model, benchmark (quality connotations)

**Free route**
A candidate served at $0: an OpenRouter `:free` slug, an OpenCode
`opencode/*` free model, or a local model. The *serving* is free, not the
model family — the same family may serve paid routes with different exposure.
A curated serving (harness or local) inherits a discounted share of its
family's popularity: a limited-time, rate-limited surrogate does not carry the
family's full standing.
_Avoid_: free model (the model isn't free, the serving is)

**Nominal floor**
A Free route's effective ticket price in the score: Free risk times the pool's
cheapest paid ticket. Never zero, so free cannot win by division, and always
below a healthy paid row, so it can still win. Applied uniformly to Free routes
regardless of Exposure — the Exposure difference is decided by the Sensitive
gate, not by price. If the pool has no priced paid ticket, use the $1 nominal
reference ticket as the basis for Free risk.
_Avoid_: free price, effective cost, shadow price
