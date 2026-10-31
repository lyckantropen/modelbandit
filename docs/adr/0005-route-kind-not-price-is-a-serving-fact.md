# Route kind, not price, is a serving fact

A candidate's Route kind — market, free-slug, harness, plan, or local — answers
*what serves the id*, and is decided by the id and the serving alone: policy
may annotate a route (exposure, summaries) but never classify it, and an
unrecognized namespace fails closed. The kind, not the price, drives the
safety gates: closed zones refuse unaccountable free servings (free-slug,
harness) whatever they cost, while retention stays Exposure's verdict —
Sensitive shapes refuse `trains` whatever they cost. The split anticipates
subscription-plan servings (`opencode-go/*`), where price and identity diverge:
$0 marginal, paid accountability, per-model retention terms.

## Considered Options

- **Zone refusal keyed on price class** (closed regimes refuse every $0
  serving) — rejected: identical verdicts for every route in service today,
  diverging only on a hypothetical $0, no-retention plan model, and dragging
  price arithmetic (ADR-0002's territory) into a safety gate. Price is a
  scoring concern; accountability is the zone's.
- **Kinds declared by policy** — rejected: a catalogue label cannot make a
  remote id local (serving facts, never catalogue claims), and a policy that
  could reclassify would be a policy that could open a closed zone.

## Consequences

- `opencode-go/*` is its own kind from the first day it appears: it never
  inherits Free-route treatment by prefix accident, and it serves in closed
  zones as a paid, accountable serving while its retention terms arrive as
  exposure facts.
- The free catalog refuses plan and market entries (status 4, loud): a plan
  route has its own catalog, and the hardcoded $0 of a Free record must never
  price one.
- The preflight answers `blocked: unknown serving namespace` for ids outside
  every kind — default-deny at the one surface that owes a launch verdict.
