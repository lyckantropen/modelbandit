# Affinity as signals, not stored weights

The multi-ticket deal tilts by user preference, but preference is stored only
as structured hints (fit per domain + evidence) and the numeric affinity is
derived at run time through `affinity.factors`. We decided this after a review
showed that a stored per-domain weight matrix is a derived artifact pretending
to be source data: it drifts from the hints it was derived from, and drifts
again as the model landscape moves.

## Considered Options

- **Stored per-domain weight matrix in policy.json** — rejected: hand-maintained
  parallel list; nothing checks it; re-derivation is manual whenever a hint or
  the model landscape changes. (This was v1.5's first draft.)
- **Storing the models in popularity order in policy.json so affinity could be
  generated from it** — rejected: popularity order is live data that moves
  daily; storing it relocates staleness into the policy file instead of
  removing it. Eligibility is re-derived from the live boards every run.
- **Chosen: structured hints + derived factors** — the irreducible user input
  (direction, per domain, with evidence strength) is stored once; the numeric
  projection is a four-constant convention in policy.json.

## Consequences

- Taste is expressed at favor/avoid granularity — graded preferences between
  two favored models are not representable (ranked multipliers were mostly
  invented precision).
- `--check-policy` must police both drift directions: stale fit keys, and
  signal coverage gaps (opinion in one domain, silence in another where the
  model ranks). Signal drift is reported to the user, never auto-fixed: a
  refresh may reconcile coverage but never writes taste.
