# Sensitive is derived, not stored

A Shape's Sensitive verdict has two causes — the material (`--sensitive`,
carried as `material_sensitive`) and the place (a closed zone posture) — and
either firing is enough (ADR-0008). The verdict is a read-only property
computed from those causes on read, never a stored field and never a
post-construction copy: a stored verdict can drift from its causes the moment
either is set after the fact, and a second spelling of the join (a free
accessor, a per-gate re-derivation) lets two call sites disagree — which is
exactly the bug class that once left the gates excluding every non-local row
while the banner, reading the raw flag, never printed. With the verdict as a
property, the raw-vs-derived divergence is unwritable by construction: the
input keeps its own name (`material_sensitive`), the verdict owns
`sensitive`, and there is nothing left to re-derive.

## Considered Options

- **Store the verdict at construction (`__post_init__`)** — rejected: the
  stored value was reachable only under a private name, so callers were
  tempted to read the raw field instead, and equality, repr and
  serialization all needed care to keep the copy consistent. The copy bought
  nothing the property does not provide, because the causes of a frozen
  shape never change after construction.
- **Keep the raw flag under the name `sensitive`** — rejected: that is the
  bug class itself. Two concepts, one name — the material flag and the
  flag-or-place verdict — made every `shape.sensitive` read a guess about
  which one the author meant.

## Consequences

- Everything that judges sensitivity reads `shape.sensitive` and gets one
  answer; the banner, the gates and the spares' fence cannot disagree.
- A caller who wants to know what made a shape Sensitive reads the causes —
  `material_sensitive` and `posture` — which are the only stored truth.
- The former accessor spelling (`sensitive_shape(shape)`) is gone; code
  review treats any re-derivation of "flag or closed place" outside the
  property as a defect, not a convenience.
- Dataclass equality and serialization compare the stored fields alone, so
  the derived verdict never appears in JSON payloads or cache keys except
  where a caller states it explicitly (as the free-share record does).
