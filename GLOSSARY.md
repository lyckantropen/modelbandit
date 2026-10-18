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

**Projection**
The priced cost of a run: per ticket and total, at a stated pricing basis.
_Avoid_: estimate, quote

### Taste

**Hint**
A user observation about a model: a note, its fit per domain, and its evidence.
Weighed, not obeyed; it annotates, never reorders.
_Avoid_: verdict, preference, taste

**Fit**
The direction of a hint for one domain: favor or avoid. Absent fit is neutral.
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
