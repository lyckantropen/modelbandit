# Steering: qwen36-35b-a3b-distill

Served id: `lmstudio/qwen36-35b-a3b-distill` (served quants `@q4_k_s`,
`@iq4_xs`). Brief: paste `operating-discipline.md`, then this block.

**Deal scope** — bounded deliverables with an explicit recipe. This is the
model's demonstrated strength: the #84 pin sub-run passed unaided first try
when the brief named one artifact, copied a neighboring idiom, gave an exact
suite count and fixed report fields. On broad acceptance criteria the same
model self-certified twice (#79, #84) and neither run survived verification.

**Bench standing** — strongest structured work of the local lineup
(Phase-4 5/4/4 at `@iq4_xs`; 30–33 tok/s at 262k ctx). Pin a known-good
quant: the f16 MTP-merged file crashes the server on load.

## Observed failure modes (spec #75, 2026-11-16)

- **Confirmatory verification** — built a real checker, got `WARN` on AC3,
  dismissed it over four messages ("So criterion 3 is PASS"), reported
  MET — and quoted as proof of passing its own committed edit that *was* the
  violation (run `***REMOVED***`, `@q4_k_s`).
- **Prose blindness under mechanical diligence** — read the offending
  three-regime ladder and the superseded ADR citation in its own
  verification passes and moved on; `git log` showed the ADR superseded
  while it stayed cited as live (same run).
- **Polishing its own inventions** — invented a slogan and flag
  instructions, then featured them in the final report while the acceptance
  criteria got the benefit of the doubt (same run).
- **Silent end + overclaimed criterion** — `#84`'s main run ended "completed
  without a response" with one uncommitted fix; its report had marked AC2
  "MET … byte-identical output verified" with no cross-entry-point pin ever
  grepped, and read "Delta: 0" as success where the criterion demanded a
  new test (run `***REMOVED***`, `@iq4_xs`).
- **Root mixing** — alternated between the session checkout and the
  worktree until it caught itself mid-run ("THIS IS THE CHECKOUT COPY!"),
  producing momentarily wrong conclusions in both directions (same run).

The counter-evidence (run `***REMOVED***-pinfinish`,
unaided pass, 19 min): bounded recipe, edge cases researched before coding,
first failure self-corrected within two messages, and — the key habit —
verified empirically and reported the discrepancy it found (suite 1081 vs
the briefed 1080, root-caused with `-v` output instead of rounded to fit).

## Steering block

- A WARN from your own checker is a FAIL. You may downgrade it only by
  quoting the exact text that proves the checker wrong; "the regex is too
  broad" without the quoted counterexample is not a downgrade.
- Every MET line quotes the command output that proves it. Judged prose
  criteria quote the prose sentence and argue it — a grep hit is not proof.
- If `git log` shows an ADR or document superseded, stop and re-check every
  citation you are leaving in place.
- Before reporting done, grep every acceptance criterion's surface once —
  literally the criterion's own terms — and paste the grep results, even
  (especially) when you believe they are clean.
- Work in the declared worktree root only. One `git status --porcelain` in
  that root before any state claim.
- Never end without a final message: a silent completion is a failed run.

## Prompting and serving facts

- Thinking mode on by default (reasoning channel with `think` tags).
- Recommended sampling for precise coding: temp 0.6 / top_p 0.95 / top_k 20
  (instruct mode: 0.7 / 0.80 / 20).
- MTP layer enables speculative decoding; GGUF needs a recent llama.cpp.
- The run-2/3 fix-loop at `@q4_k_s` was config-luck (UI temperature 0.1),
  not capability — sampling must be sent explicitly.
