# Steering: deepseek-v4-pro-qwen3.5-9b-uncensored-heretic-mtp

Served id: `lmstudio/deepseek-v4-pro-qwen3.5-9b-uncensored-heretic-mtp`.
Brief: paste `operating-discipline.md`, then this block.

**Deal scope** — speed-scoped mechanical steps, not prose-judgment work. On
glossary/prose tickets (#76) three consecutive sessions overclaimed and the
ticket needed a strong-model finish. The bench ranks it fastest honest
runner-up (107 tok/s) but weakest design among greens.

**Bench standing** — 5/5 at 262k ctx in about a minute; Phase-4 2/3/2
(fallback can print fabricated data, broad `except`, no exit codes): use it
for speed, not design quality.

## Observed failure modes (spec #76, 2026-11-16)

- **Self-certified reports over absent checks** — the fixer session stamped
  "✓ Met" on all seven gap-list items while the transcript contains no
  duplicate-headword check of any kind, and criterion 3 was silently
  renumbered into an unrelated item and reported met while the required
  headword stayed missing (session `…-***REMOVED***` fixer round).
- **Word-level verification of prose** — the punch-list session's four
  self-verify checks (no duplicate tokens, no retired words, suite green)
  all passed while the Zone entry still said the wrong thing, the Secrets
  gate still referenced a deleted file, and another entry's causes were
  broken. Its predicate was a grep, not a reading (punch-list round).
- **Edit-escalation** — consecutive anchor misses escalate into a
  whole-file rewrite plus stray temp files (`…​.tmp` waved off as
  ignorable) (attempt-1 round).
- **Asserting against its own probe output** — probes printed `False`, the
  report asserted the opposite; "evidence" for a criterion was a vacuous
  probe checking only that a substring exists somewhere in the file
  (attempt-1 round).
- **Prose-file thrash** — 4.2 M input tokens over 44 minutes re-reading one
  prose file (attempt-1 round).

Mechanics that *did* work (fixer round): opened with `read` +
`git status --porcelain`, targeted edits, removed its own stray tmp,
committed clean (`98e166e`), suite green at 1100 tests. Same model, same
ticket: the mechanics hold when the criteria are mechanical.

## Steering block

- Every MET line quotes the check that proves it **and reads the prose it
  judges**. For any criterion about wording: paste the exact sentence and
  argue it. A token-level grep may never stand in for reading.
- Criteria are addressed by their original numbers. A criterion you did not
  complete is reported as *not met* — it is never renumbered, merged, or
  replaced with an easier one.
- Your own probes' output is binding: a probe printing `False` means the
  criterion is not met. A probe that checks only substring presence proves
  nothing; quote the full sentence instead.
- Two failed edit anchors on one region = report the blocker. No whole-file
  rewrites; delete every temp file you create before the commit.

## Prompting and serving facts

- **Temperature is the loop switch**: the fix-loop at server UI temperature
  0.1 (repeated identical failing edits) turned into a pass at 0.7. The UI
  value is the operative control — request-body temperature overrides do
  not reach the server (config hot-reload is ineffective). Set UI
  temperature to ~0.7 before dispatch.
- The Qwen3.5-9B backbone with MTP heads; static prompt-template preset
  (ChatML/Qwen family) recommended over template inference.
