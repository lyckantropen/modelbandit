# Free-tier prices risk, not caps

The first free-tier delivery priced Free routes at a fixed Nominal floor,
gated the Context gate on the input dimension only, and measured the balance
criterion over every candidate. Run against live pools the three failed
together: the fixed floor priced Free roughly two orders of magnitude under a
real ticket (coding's Free route held the largest score in the domain — 66
against ~5 for the best paid row — and took about a third of a deal's draw),
so free-dominant pools read top-1 score mass of 66–99% across four of five
domains and no pairing of the exponents could bring them inside the 20–50%
band; and an authoring shape at `thorough` (30K rung-priced output) passed
the window check and then failed on a 65K completion cap the gate never
looked at.

## Considered Options

- **A hard cap on Free share** — rejected: it forbids the case the user
  wants. A job where 100% of the work genuinely belongs on free models must
  be dealable entirely to Free routes, and a cap forbids it by construction;
  it also forbids what the cheapest route should win, and it replaces one
  untuned constant (the fixed floor) with another (the cap itself).
- **A complexity-band gate** — rejected: the word it bands on folds two
  questions into one and so answers neither. Whether a shape is "small" is
  measured (its Footprint: tokens against capacity); whether it is "hard" is
  judged (its Difficulty: the effort intent plus task fit). Banding on the
  blend would gate judged deliberation mechanically — exactly what the skill
  refuses to do — while the measured half is already gated, on both
  dimensions, by the Context gate.
- **Chosen: risk pricing, measured gates, paid-only balance** — Free
  competes in the one ranking under a price that tells the truth about it:
  the Nominal floor is derived as `scoring.free_risk` (default 0.35) times
  the pool's cheapest priced paid ticket, recomputed per pool and shape —
  Free stays strictly cheapest, so it can win, but its standing now carries
  the expected cost of its failure modes (rate-limit re-runs, a route
  withdrawn mid-run, an outage). The balance criterion judges the paid
  competition only, where it still means what it meant — a Free-share
  signal, reported and never capped, answers Free's participation instead of
  a threshold.

## Consequences

- Free leadership is a tendency, not a guarantee: Free wins where its
  risk-priced standing and its Footprint say it should — some of the time on
  ordinary shapes, all of it on a shape free genuinely serves best, none
  when it does not stack up. Nothing in the deal reserves tickets for paid
  models or forbids free ones beyond the ordinary admission rules.
- The OpenRouter daily free-request counter is a cliff, not a rule: read up
  front, reported in the header, and `:free` routes leave the pool only when
  remaining quota is below the protected reserve. Plan size does not gate
  eligibility because the deal may draw fewer Free tickets than planned. It is
  the provider's allowance, never a judgement of Free share — harness-served
  `opencode/*` models and locally served models spend none of it and are never
  excluded by it.
- A misconfigured `scoring.free_risk` fails loudly: the derived floor must
  stay strictly positive and strictly below the cheapest paid ticket, so
  free can neither win by division nor be priced out of existence.
- When a pool has no priced paid ticket, Free risk uses a $1 nominal reference
  ticket; this keeps an all-Free pool's Nominal floor positive and scoreable.
- Supersedes, from the first free-tier delivery: the fixed
  `scoring.free_floor`, the input-only Context gate, and the all-candidate
  balance measurement. The rest of that decision stands — Exposure gates
  Sensitive shapes, the free catalog stays curated, and nothing stores
  derived per-model weights (ADR-0001).
