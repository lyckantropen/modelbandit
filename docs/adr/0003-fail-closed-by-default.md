# Fail closed by default

> **Superseded by [ADR-0010, Open unless declared](0010-open-unless-declared.md).**
> The record below is kept as written; the default it describes is no longer
> in force. Fail-closed survives only inside the checks — an unknown window,
> an unknown serving namespace, an unknown exposure class.

Free routes touch user content — prompts, files, the working tree — so where
they may run must be opt-in, path by path, declared by somebody. The posture
is enforced in code (`DEFAULT_REGIME = "closed"`) and
recorded in prose (SKILL.md's closed-zone protocol, the Zone entry in
GLOSSARY.md): any path undeclared in `zones.json` is `closed`, and a missing
`zones.json` closes everything. What is missing is the decision itself. A new
user reasonably expects free models to work out of the box, and they will
not — the wait for explicit setup is surprising without context, hard to
reverse silently, and the result of a real trade-off. It deserves the ADR
treatment.

## Considered Options

- **An opening default (e.g. common workspace dirs declared `open`) for
  onboarding convenience** — rejected: a path nobody declared must never
  serve free routes, and an implicit default is precisely a path declaring
  itself. Onboarding friction is real, but it is fixed by documentation and
  tooling — the README restructure (#35), the zones interview →
  `--write-zones` setup (#36), `--status` (#37) — not by loosening the
  default.
- **Chosen: undeclared is `closed`** — any path not declared in
  `zones.json` is `closed`, and a missing `zones.json` closes every path.
  Setup — the skill's zones interview, writing `zones.json` via
  `--write-zones` — is the explicit, visible step that opens zones. Paid
  models are unaffected by the default: the posture governs where free
  routes may run, not where the user may work.

## Consequences

- Remote free routes are absent until setup: before `--write-zones` has
  written a `zones.json`, no path resolves to anything but `closed` and no
  free route is offered. Paid models work from the first run.
- Setup is documented front-and-center: the walk from a closed first run to
  an open zone is the first thing a new user is shown, not a
  troubleshooting find.
- First-run output must state the posture truthfully — the header reports
  `closed` while the default applies and never implies an opening
  (companion ticket #38).