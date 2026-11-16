# Modelbandit

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

**ordinary ticket**
A ticket that is not sensitive: the default posture for most work, with no
special constraints at any gate — only what every ticket has.
_Avoid_: ordinary request (it names a class of ticket; this defines the shape)

**Spare**
A candidate the deal names but does not deal: the highest-Score eligible
candidate that missed the draw behind a dealt model, standing by to take the
ticket over whole when the dealt model cannot serve — unreachable, out of
quota or allowance, unloadable, or reported dead. It inherits every
constraint of the ticket it backs: substitution swaps the model, never the
fence.
_Avoid_: fallback, backup, alternate

**Concurrency lane**
The deal's statement of mutual exclusion: every local-dealt ticket id in
one strict lane — no two local runs concurrent, same model or not. Printed
as `lane: strict — one local run at a time (grouped by model)` plus one
`lane: <ids> -> <model>` line per served model (or `lane: none — no
local-dealt tickets`), and carried in the budget `--json` as `lane` groups
with `tickets_by_model`. Membership follows the served model under
substitution, while the published blocking edges stay put: the chain a
ticket workflow enforces is conservative enforcement of the lane, never a
dependency claim — the lane record is the truth.
_Avoid_: dependency chain, execution order (those say why tickets wait;
the lane says what may not run together)

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
(runs on this machine — no training, no retention) — the only class that may
serve Sensitive work. The property that gates sensitive work; never inferred
from price — free does not imply trains, paid
does not imply no-retention. Unknown free defaults to trains.
_Avoid_: privacy, data policy (an account rule, not a model property), training flag

**Sensitive**
A ticket only a local candidate may serve — because its material trips the
Secrets gate, because of an explicit `--sensitive` flag, or because its place
is `closed`, whichever is stricter. Every non-local Exposure is excluded alike:
no-retention is a promise about storage, not about transit. A join of those
three causes and a property of the ticket shape only — never a place, since
zones are binary — computed once when the run's shape is constructed and
derived thereafter; never a mood declared mid-run.
_Avoid_: confidential, "sensitive stuff" (fuzzy), secret material

**Local roster**
The author-owned record of the local models' judgment, keyed by the harness's
own model id: each model's Capability band and its prose — and only that.
What exists and how it is served belongs to the harness that serves it;
the roster never restates it. Hand-maintained — the only source a local
candidate's band may come from.
_Avoid_: registry, catalogue, inventory

**Zone**
The machine-wide declaration of where free models may run, in a binary
posture: `open` or `closed` — two words, no ladder, no third value. Open
unless declared: anything undeclared is `open`, and an absent zones file
means everything is open. The zones file is only an opt-out list of paths
declared `closed` — it can add closures and can never reopen anything, so
the inverted posture (closed everywhere, open exceptions) is not expressible.
Each declaration is a path declared `closed` for everything under it,
resolved by longest prefix. The effective posture at any path combines all
applicable declarations — from working folder settings and origin repository
stance — taking the stricter (most restrictive) one, so one closed
declaration covers that repository's worktrees without needing
per-repository configuration.
_Avoid_: allowlist, permission (it is a place, not a grant)

**Secrets gate**
The check that applies the built-in credential, identifier, machine-fact, and
gitignored-content rules to the material a run is given — run automatically at
deal time (the run reads its own ticket material), and manually via the check
mode for a single material. Content-inclusion, any-of; a mere path mention
does not trip it.
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

**Capability band**
What a local model's roster entry claims it may serve: the domains it handles,
and ceilings on Difficulty and on context demand, set as a thin structured
header beside its prose. Author-owned and binding — the Band gate enforces the
band, so understating it costs only reach, while overstating it fails at the
ticket.
_Avoid_: description, profile, skill

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

**Share**
The fraction of a deal's tickets drawn by each class — Free routes, this machine's own servings, or plan rows. Reported as `free share: N/M tickets (P%)`, `local share: N/M tickets (P%)`, or `plan share: N/M tickets (P%)`; never capped and never floored: some of the time on ordinary shapes, all of it on a shape that genuinely serves best, none when it does not stack up. The plan share is printed by code but has no dedicated entry here — this is where its concept lives.
_Avoid_: quota, free budget, cap, local quota, hardware budget (the draw reports itself, never gates)

**Free route**
A price class: a candidate served at $0 — an OpenRouter `:free` slug, an
OpenCode `opencode/*` model, or a local model. The *serving* is free, not the
model family — the same family may serve paid routes with different exposure.
A curated serving (harness or local) inherits a discounted share of its
family's popularity: a limited-time, rate-limited surrogate does not carry the
family's full standing.
_Avoid_: free model (the model isn't free, the serving is), route kind

**Route kind**
What serves a candidate — a serving identity, decided by the id and the
serving alone: market (an OpenRouter paid slug), free-slug (an OpenRouter
`:free` slug), harness (an OpenCode `opencode/*` model), plan (an OpenCode Go
`opencode-go/*` model), or local (served on this machine). Never a price,
never a policy claim; an unrecognized namespace fails closed. Plan and metered routes are captured here as route kinds — they're not separate concepts. The free-slug kind is also the Free route category.
_Plan route_: A candidate served through a subscription plan (Route kind `plan`): $0 cash within its Allowance, scored as risk of its Draw. Not a Free route — the Zone gate does not refuse it, the free counter does not count it, and it is the family model at full quality, not a rate-limited surrogate._
_Metered route_: A candidate billed per ticket at its list price (Route kind `market`): Plan route's price-class counterpart, Free route's opposite. The default economics — nothing prepaid, every ticket on the bill._
_Avoid_: provider, price class (that is Free route), catalogue label

**Twin**
The same family's serving in another market: a Plan route's Twin is its
family's Metered route, and the reverse. Twins substitute for each other at
cap — the model identity is preserved while the market flips.
_Avoid_: alias, duplicate, fallback (substitution is one behaviour of a Twin)

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
The derived numeric tilt of the deal toward or away from a model, computed at run time from fit and evidence through the factors. Never stored. The four multipliers mapping fit × evidence to affinity are part of this concept.
_Avoid_: weight table, preference score, factor weights (they multiply into affinity)

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

**Nominal floor**
A marginal-zero ticket's effective price in the score: Free risk times the Draw
it would burn — one rule, two cases. A Plan route prices as risk of its own
list-priced Draw; a Free route has no Draw and prices against the pool's
cheapest paid ticket. Never zero, so marginal zero cannot win by division, and
always below a healthy paid row, so it can still win. Applied uniformly to Free
routes regardless of Exposure — the Exposure difference is decided by
the Exposure gate, not by price. If the pool has no priced paid ticket, use
the $1
nominal reference ticket as the basis for Free risk.
_Avoid_: free price, effective cost, shadow price

**Allowance**
The dollar budget a subscription plan grants per model, per window (a rolling
5-hour window, a week, a month). Drawn down by use; not readable from an
account balance. A plan route serves at $0 marginal only while its Allowance
holds.
_Avoid_: cap (the window is a property of the Allowance), quota (that counts
free requests), budget (that is the user's spending limit)

**Draw**
What one ticket consumes of an Allowance: its cost counted at the plan's list
price, independent of the $0 cash its Draw actually charges. The opportunity
cost of a plan ticket — burning cheap Draw on one ticket leaves less for the
next.
_Avoid_: cost (that is cash or blended price), usage, spend

**Anchor**
A benchmark row carried into a research brief as a fact to verify or extend:
first-party numbers for a model under review. Not the Baseline — that is the
price anchor for Δ columns; anchors serve the research. Keep the two distinct.
_Avoid_: price anchor, baseline

**Gap**
A model ranked on a domain board without a summary. Work the cycle should
do, not a fault in the policy.
_Avoid_: missing entry (implies error)

**Stale**
A summary or signal whose key no longer ranks on any domain board. The model
may still rank below the depth the boards show; whether and where it does is
something to look up at run time, not part of the state. A drift state of the
policy, not of the model.
_Avoid_: expired, deprecated (those are vendor statuses, not drift states)

**Zone gate**
The mechanical check at the source: free-slug and harness candidates are dropped when the effective posture is `closed`. This is how zones prevent remote free routes from running.
_Avoid_: route kind, admission (those say what survives; this says where it starts)

**Exposure gate**
The sensitivity filter: non-local Exposures (`no-retention` and `trains`) are excluded whenever the shape is sensitive, so only Exposure `local` may serve it. This is how Exposure enforces local-only for sensitive work.
_Avoid_: capability band, admission (those say what survives; this says where it starts)

**Band gate**
The domain check at pick time: a candidate's Capability band must include the ticket's domain. If not, the candidate is excluded with `band: {domains}` in the reason. This is how bands enforce domain boundaries.
_Avoid_: eligibility (that's what survives; this says where it starts)

**Quota gate**
The free-request counter check at plan time: when remaining Free quota falls below a route's Draw, that free-slug candidate leaves the pool and exits with `quota exceeded`. This is how quotas enforce rate limits.
_Avoid_: cap (that's what survives; this says where it starts)
