# Sensitive work is local-only

Sensitive work — material that trips the secrets gate, or anything under a
`sensitive` or `closed` regime, whichever is stricter — is served only by
candidates whose Exposure is `local`. No-retention is a vendor promise about
storage, not about transit: Sensitive material leaves the machine on any
remote route, so the no-retention cloud routes that used to serve this work
(the Journal-vault precedent) are out, and a Sensitive ticket with no eligible
local candidate stops and reports rather than re-gating — the report is the
human escalation.

Considered: local-preferred with a no-retention cloud fallback. Rejected
because the secrets gate trips on real secrets (keys, tokens, identifiers) and
containment beats availability there; "prompted to never leak" stays as
defense-in-depth, never as the only line.

## Vocabulary note

This decision predates ADR-0010, and its wording predates the vocabulary
that replaced it: "regime" — including the `sensitive` regime named above —
is retired. The Zone is a binary posture (`open` / `closed`), and Sensitive
is a property of the ticket shape: material that trips the Secrets gate, an
explicit `--sensitive` flag, or a closed place. The rule this ADR states —
Sensitive work is served only by candidates whose Exposure is `local` —
stands unchanged; read the retired words through ADR-0010's.
