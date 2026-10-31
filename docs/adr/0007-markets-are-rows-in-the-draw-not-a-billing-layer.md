# Markets are rows in the draw, not a billing layer

A family served in two markets enters the pool twice — once per serving — at
split family share, and the seeded draw picks rows. The obvious simplification
— one row per family, market flipped at billing time — is rejected: rows carry
market-specific routing facts (a pinned provider on the metered row, the plan
slug itself), and a billing layer would silently override what the user
configured. The draw stays honest; economics tilts it (risk-of-Draw pricing
gives a plan row a ~1/risk edge while its Allowance holds), and the occasional
metered draw within Allowance is the price of respecting routing facts.

## Considered Options

- **Plan-first billing** (one family row; flip to the plan serving whenever it
  has headroom) — rejected: the market becomes a hidden post-process; a metered
  row's provider pins and endpoint choices grow unreachable whenever the plan
  has headroom, and the deal would name a serving the draw never chose.
- **Strict plan-until-cap mapping** — rejected: the same defect, harder — the
  metered Twin can never draw, so routing facts and Endpoint spread never
  apply.

## Consequences

- The deal names market-qualified ids; dispatch is a copy, not an
  interpretation.
- At cap the Twin absorbs the ticket (identity preserved) — the one direction
  the adapter forces; the reverse never.
- Doubly-served families show two rows; split family share keeps popularity
  honest across them.
