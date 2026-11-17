# The gates

One inventory, derived from the code's canonical gate tuple and pinned to it
by a doc-contract test (`tests/test_skill_docs.py`): every gate, the clause
it judges, what it excludes, and which entry points run it. Term definitions
belong to the glossary; this document is the mechanical map, so no other doc
re-narrates it.

## The one decision

`GATES = (zone_gate, exposure_gate, band_gate, context_gate)` — the tuple
`admit()` consults, in order, for the one Decision both the ranked table and
the deal read. The first failing gate's reason is what the table shows.
Three more surfaces sit outside the tuple, each for a stated reason:

- **Quota gate** (`quota_gate`) — the free-request counter check. Outside
  the tuple because it runs only when the run holds a counter verdict:
  `admit()` applies it after the four, and a run without a verdict (the
  policy check's diagnostic deal) never runs it.
- **Secrets gate** (`secrets_check`) — not a gate inside the decision at
  all: it produces the shape's input. It classifies the material a run is
  given (the built-in credential, identifier, machine-fact and
  gitignored-content rules) at deal time — the run reads its own ticket
  files — and on demand via `--check-secrets`; its verdict is what a caller
  passes back as the shape's material flag.
- **Namespace fail-closed** (`classify_route` at the pre-flight) — an id
  outside every Route kind is blocked at the pre-flight and nowhere else:
  the one surface that owes a launch verdict is the one that answers it,
  before anything is fetched.

## The gates

| Gate | Code | Clause | Excludes |
|---|---|---|---|
| Zone gate | `zone_gate` (predicate: `zone_prohibition`) | a closed place refuses the remote, unaccountable servings | free-slug and harness routes in a closed posture, dropped at source |
| Exposure gate | `exposure_gate` (predicate: `exposed_prohibition`) | only Exposure `local` may serve a Sensitive shape (ADR 0008) | every non-local route on a Sensitive shape, paid included |
| Band gate | `band_gate` | the Local roster's Capability band binds the rostered local row | local rows whose band does not cover the ticket |
| Context gate | `context_gate` | a Free route's Footprint must fit the capacity, fail closed on unknown | Free candidates over capacity or with an unknown window |
| Quota gate | `quota_gate` | the counter's own facet answers; a spent counter says nothing about routes that spend none of it | free-slug routes when the counter is spent |

## Which entry point runs what

| Entry point | Zone predicate | GATES | Quota gate | Secrets gate | Namespace |
|---|---|---|---|---|---|
| ranking run (`--domain`, `--deal`) | source filter + Zone gate | yes | yes, with a counter verdict | deal time, via `--ticket-files` | — |
| `--check-policy` / `--scope` | source filter + Zone gate | yes | never — no counter verdict | — | — |
| `--assert-allowed` | `zone_block`: the predicate plus the Exposure clause in words | — | — | — | yes |
| `--check-secrets` | provenance's closed-place ask | — | — | yes, the material | — |
| `--anchors` | source filter only — empty locals, measured intent | — | — | — | — |
| `--substitute` | — | — | — | — | — |

`--substitute` runs no gate: the fence is restated, never re-gated — a
substitution's Spare came from the deal's own admitted set, and a Sensitive
Spare from local candidates only. `--status`, `--write-zones` and
`--list-domains` run no gate; they report and write configuration.
