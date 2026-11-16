# Open unless declared

Free routes now work from the first run: a path nobody has declared anything
about is `open`. This supersedes ADR-0003's fail-closed default, and the
reversal is deliberate. The Zone is a binary posture — `open` or `closed`, no
ladder, no third value — and `open` unless declared: an absent zones file
means everything is open, and the zones file is only an opt-out list of the
paths declared `closed`. The file can add closures and can never reopen
anything. The stricter-of-two rule stays: the effective posture combines the
working folder's declarations with the origin repository's, taking the
stricter, so one closed declaration covers that repository's worktrees
without per-repository configuration. Fail-closed survives only inside the
checks, where it belongs: an unknown context window keeps a free route out,
an unknown serving namespace blocks at the pre-flight, and an unknown
exposure class defaults to `trains` and so cannot serve a Sensitive shape.

## Considered Options

- **Keep fail-closed-by-default (ADR-0003)** — rejected: it charges every
  user for a decision most never need to make. A new user must survive a
  zones interview or copy-paste a `zones.json` before a single free route
  appears, and the cost of forgetting is invisible until they wonder why
  free models never show up. The default should require no action from
  someone who has declared nothing.
- **Keep the three-regime ladder, or make the posture configurable both
  ways** — rejected: a per-path `sensitive` regime and a top-level `default`
  key keep `sensitive` as a place as well as a ticket shape, so one word
  means two things; and a configurable default is exactly how the
  fail-closed ceremony would return quietly. Sensitivity is a property of a
  ticket shape — material that trips the Secrets gate, an explicit flag, or
  a closed place — never a folder's declared state.
- **Chosen: open unless declared, an opt-out list of closed paths** — the
  only declaration the file accepts is `closed`, and the only way content is
  kept off remote free routes is to name its path. The posture is two
  words, the schema is a bare list, and the first run needs no file.

## Consequences

- The inverted posture — closed everywhere with a few declared-open
  exceptions — is deliberately not expressible. A user who wants that must
  enumerate the closed paths instead of the open ones. This is the trade:
  the opt-out list is the one the common case needs (protect what matters,
  leave the rest open), and expressing the inverse would require the
  configuration ceremony this decision removes. Here the smaller
  declaration wins over the expressive one.
- A path a user forgets to declare is open, and free routes may run on it.
  That is the accepted cost of requiring no setup; the closed declaration,
  once written, is durable, and `--write-zones` writes it validated and
  atomically.
- A closed declaration still covers the repository's worktrees, through the
  retained stricter-of-two join, so checking the same content out elsewhere
  does not escape it.
- The header states the effective posture truthfully on every run — `open`
  on a first run, with no warning and no nag — and only a derived `closed`
  stops remote free routes at the source.
- Paid models were never governed by the posture and still are not: the
  posture says where free routes may run, not where the user may work. The
  rest of ADR-0003's reasoning stands — a closed place is a safety
  declaration, not a permission grant.
