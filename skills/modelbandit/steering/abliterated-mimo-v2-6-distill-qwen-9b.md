# Steering: abliterated-mimo-v2.6-distill-qwen-9b

Served id: `lmstudio/abliterated-mimo-v2.6-distill-qwen-9b`. Brief: paste
`operating-discipline.md`, then this block.

**Deal scope** — narrow tickets only, and only with a hard tool-cadence
contract. Its failure shape is not incompetence but *stall*: the work gets
fully drafted in reasoning and never reaches the tree. On #86 it produced
zero worktree output in ~1.5 h and was operator-cancelled; its bench
redemption (8/8) shows it delivers when the deliverable is small and the
loop is tight.

**Bench standing** — 8/8 at the locked 160k context (knee: 120k→96,
160k→91, 200k→79 tok/s), Phase-4 4/4/4; but one prior false green
(python-style test functions with unimported `assertRaises` — claimed 4/4
while unittest collected 0).

## Observed failure modes (spec #86, 2026-11-16)

- **Reasoning black hole** — 92.5% of measured step time spent streaming
  reasoning (181,430 chars of reasoning vs 463 chars of user-visible
  prose), one 337-second monologue alone = a third of all step time; 0.9%
  tool execution (run `***REMOVED***`).
- **Plans drafted, never executed** — the same plan fully drafted in
  reasoning three separate times ("Now write the code") and converted to a
  tool write once — in the wrong directory.
- **Write into the session checkout** — its only write targeted the
  read-only checkout against the brief's rule; directory mixing persisted
  through compaction. (Git-restored by the parent; its draft was salvaged.)
- **Compaction amnesia** — auto-compaction fired seconds after that write;
  the next step announced a fresh start, 33 re-exploration calls followed,
  and it read the worktree lines proving its edit was missing without
  reacting.
- **No terminal stop** — 47/48 steps ended `finish=tool-calls`; no final
  answer was ever produced; cache read 0 across ~105k-token prompts (every
  step paid full re-read).
- **False-green test collection** (bench run 4): pytest-style functions and
  unimported `assertRaises` collect 0 under `unittest` while the report
  claimed 4/4.

## Steering block

- **Tool-cadence contract**: every reasoning block ends in a tool call.
  Drafting the same plan twice without a tool call between is a failure —
  write it or report the blocker. Aim for tool calls within the first two
  minutes and every couple of minutes thereafter.
- The declared worktree root is the only writable root. Write-target
  declaration: before the first write, state its absolute path and check it
  against the brief's root, out loud.
- After any compaction: state the branch, the diff summary and the next
  criterion **from the tree** (one `git diff --stat`) before any further
  exploration.
- Test claims must quote the suite's *collected* count (`unittest -v`
  output showing N tests run), not the number of test functions written.
  A suite that collects 0 while you wrote tests is RED.
- No final answer is a failed run: the last message always contains the
  report or the blocker.

## Prompting and serving facts

- Load with **explicit offload flags**: LM Studio's stored per-model offload
  was observed stale at 9 of 32 layers — plain loads underperform.
- Locked context 160k is the speed knee (200k costs ~15% tok/s).
- Sibling of the mimo distill family: same tool-call repetition risk — send
  sampling explicitly (temperature 1.0 / top_p 0.95 per the MiMo-V2.6
  series guidance).
