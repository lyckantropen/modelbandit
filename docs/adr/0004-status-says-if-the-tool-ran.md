# Status says if the tool ran, output says what's true

The exit contract had been encoding domain **answers** in a channel whose
universal meaning is failure. `1` meant "sensitive" while CPython uses `1`
for *the program crashed* — to every wrapper an answer and a disaster are one
byte — and this session shipped two live bugs from exactly that collision:
`load_policy_config` failures and `need --domain` both surfaced as shell exit
1, indistinguishable from a crash. `2` meant both "usage error" and
"over-budget": an answer sharing a failure's code, so `cmd && next` skipped
`next` for a perfectly healthy verdict. Codes `3` (not certified) and `5`
(zone block) were answers wearing nonzero for the same reason. Decision
(user, 2026-10-27): **exit 1 carries no contract meaning ever**; answers move
to output.

## Considered Options

- **Keep the integer enum and allocate more codes for new verdicts** —
  rejected: every new verdict burns a code, the table grows with each answer,
  and the 1-collision stays — a wrapper still cannot tell "sensitive" from a
  crash by `$?` alone.
- **Add a `--gate` boolean flag** — rejected: no honest nonzero remains for
  "false" — the gate would have to lie about running to say "no", or exit 0
  twice — and `jq -e '.allowed'` already owns shell booleans; `$?` after
  `jq -e` is the branch shell code actually wants.
- **Chosen: status for the run, output for the verdict** — the tool's status
  answers only "did it run"; every answer moves to the printed output (the
  verdict lines, or one `--json` object for the answer modes).

The contract:

| status | meaning |
|---|---|
| **0** | ran to completion — **any verdict**: safe, sensitive, not-certified, allowed, blocked by the zone, over-budget, empty pool, no candidate admitted |
| **1** | no contract meaning: what CPython and generic operational failures (network unreachable, unreadable input) produce — never an answer |
| **2** | usage errors (argparse's own channel) |
| **4** | rules/config — the tool could not form a verdict; stays nonzero so `&&`-chains remain fail-closed on errors |

Retired: **3** (not-certified), **5** (zone-block), **1** (sensitive), and
over-budget's borrowed **2**. The verdict lines (`allowed:` / `blocked by
the free-use zone`, `secrets gate: …`, `budget: … -> OVER`) keep their
bytes and their streams; only the statuses under them moved.

## Consequences

- Consumers read verdicts, not `$?`: the printed lines or `--json` say what
  is true; the status only says the tool ran. The pre-flight's contract is
  "launch only when the output says `allowed`" — an error, a missing field, a
  malformed response, anything else means do not launch (default-deny).
- Errors still fail closed: 4 stays nonzero for rules/config, 2 for usage,
  and 1 is whatever CPython assigns to an operational failure — a stopped
  run is never mistaken for a verdict, and a verdict never masquerades as a
  stop.
- Shell branching on an answer moves to the consumer side of the pipe
  (`jq -e '.allowed'`, `grep`, `jq -r '.status'`) instead of a case on `$?`.
- Supersedes the status assignments in SKILL.md's exit table as shipped with
  the five-code enum (issue #41); ADR-0003's fail-closed default is untouched
  — the posture still answers `closed` before anything runs.