# Steering: mimo-v2.6-distill-qwen-9b

Served id: `lmstudio/mimo-v2.6-distill-qwen-9b` (served variant `@q4_k_s`).
Brief: paste `operating-discipline.md`, then this block.

**Deal scope** — narrow to medium tickets with a bounded deliverable. The
same model passed #83 unaided first-try under a record-fed discipline brief
and was killed on #81 under a plain brief: brief quality, not capability, is
the swing factor. Skip for broad tickets with prose-judgment criteria.

**Bench standing** — best artifact of the local benchmark (11/11, Phase-4
5/5/5, ~101 tok/s at 262k ctx); the default pick for local agent work.

## Observed failure modes (spec #75, 2026-11-16)

- **Whole-file rewrites through scripted writes** — 10 `edit` anchor misses
  escalated into byte-patching scripts (`fix_gate*.py`, `reset_and_edit.py`);
  the diff churned 9,591 line-ending-riddled lines and buried real edits
  (run `***REMOVED***`).
- **Probe-script spirals** — 26 untracked scratch files across three
  steerings; ~20 more probe scripts appeared between interventions 2 and 3.
- **Path mistyping and root confusion** — ~15 minutes lost to a mistyped
  worktree path; still asking "which copy gets edits?" at +88 minutes.
- **Never reached a terminal artifact** — no `git add`/`git commit` in 385
  messages; killed at ~2.5 h; a compaction at +65 min restarted it from
  zero and orientation never returned.
- **Tool-call repetition/flooding** (family quirk, documented by Xiaomi):
  repeated identical calls with no changed state; the SFT distill predates
  the MOPD-fixed checkpoints.

The #83 counter-evidence (run `***REMOVED***`,
unaided, 31 min) shows each mode is suppressible: under a record-fed
discipline brief the run made one write call and read ACs back from code.

## Steering block

- This brief's OPERATING DISCIPLINE clauses each name a failure from your
  previous run on this repository (run `…-***REMOVED***`), which was
  terminated for them. Follow them literally.
- `edit` tool only for existing files. After two failed anchors on the same
  region, stop and report the blocker — do not build a patch script.
- One `git diff --stat` after every edit session; the diff must stay
  minimal and EOL-stable. If the diff exceeds roughly twice the expected
  size, reset and re-approach rather than continuing.
- At most one scratch file, in the session scratchpad, deleted before the
  commit. `git status --porcelain` clean at the end.
- After any context compaction: re-state the branch, remaining criteria and
  the current diff summary before continuing — do not re-explore.
- Commit early once the suite is green; an uncommitted hour is a lost hour.

## Prompting and serving facts

- Send sampling explicitly: temperature 1.0 / top_p 0.95 (official MiMo-V2.6
  series guidance; harnesses that omit sampling fall back to near-greedy and
  correlate with loops). Community workaround for repetition: repetition
  penalty 1.05.
- The `@q4_k_s` served variant is a 4-bit quant of the same checkpoint as
  the bench run.
- The Qwen3.5-9B backbone carries MTP heads (speculative decoding capable);
  GGUF drops the vision tower — text only.
