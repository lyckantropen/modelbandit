# Operating discipline — the shared brief skeleton

Paste this into every implementer brief for a local model, then splice in the
model's own block from `<model>.md`. Provenance: the spec #75 transcript
post-mortem (2026-11-16). The record-fed discipline brief that made mimo
pass #83 first-try with zero interventions is this skeleton's origin — every
clause names a failure mode that was actually observed.

## The block

### Roots and scope

- The worktree root named below is the **only** writable location. Every
  other tree — including any session checkout — is read-only. Use absolute
  paths in every tool call; a relative path is a bug.
- Before any statement about file state, run `git status --porcelain` and
  `git diff --stat` **in the declared worktree root** and quote the output.
  Evidence gathered in another root is not evidence.

### Edits

- Targeted edits only. Never rewrite a whole file to change a few lines.
- If an edit's anchor text is not found, try at most **two** variations,
  then report it as a blocker. No whole-file rewrites, ever.
- For replacements, the new text must contain the anchor you replaced. If a
  successful edit does not behave as expected, re-read the region once
  before editing again — never edit twice blind.

### Baseline first

- Run the test suite **before** the first edit and report the measured
  count. If it differs from the count stated in this brief, report the
  difference and your diagnosis. Never round a number to match the brief.

### Scratch discipline

- Zero scratch files in any tree. Scratch goes to the session scratchpad
  directory and is deleted before the end. A worktree with scratch in it is
  a failed deliverable — check `git status --porcelain` before claiming
  done.

### Verification and report

- Report shape: **one line per acceptance criterion**, each line quoting the
  command and its output that proves it. A criterion you did not check is
  listed as *unverified*. Never renumber, merge, or drop a criterion.
- A WARN from your own checker is a FAIL until proven otherwise.
  Explaining away adverse output is a report failure.
- Read the prose you are graded on. A word-level grep is not proof that a
  sentence is correct; quote the sentence and judge it.

### Honest stop

- An honest blocker report is an accepted ending. If something resists two
  attempts, say so plainly and stop — do not claim done.
- Silent endings are failures: the final message must contain the report.

### Terminal artifact

- End with exactly one commit — or a blocker report — and show
  `git status --porcelain` clean in the worktree afterwards.

## Environment workarounds (pwsh on Windows)

Prescribe these in the brief; do not let the run spend turns rediscovering
them:

- Multiline commit messages: write the message to a file and use
  `git commit -F <file>`. Heredocs do not exist in pwsh.
- `grep`, `sed`, `wc`, `tail` are not installed: use `Select-String`,
  `Get-Content`, `Measure-Object`.
- `2>/dev/null` does not discard stderr — it writes a file named `null` in
  the current directory. Silence errors by filtering output instead.
- Python one-liners printing non-ASCII hit the console's legacy codec and
  crash: force UTF-8 (`$env:PYTHONUTF8 = '1'` or `python -X utf8`), and do
  not re-run a command that failed on encoding — change it.
- Commands blocked by the portable shell scanner run through
  `pwsh -NoProfile -File <script>` instead.

## Orchestrator checkpoints (pre-agreed stop rules)

Verification against the acceptance criteria is the only delivery signal.
A harness `succeeded` outcome is telemetry, never proof — treat "succeeded
with no commit and no suite run" as an automatic verification trigger.
Spot-check mid-run and steer or kill when any of these fire:

- No visible diff at the brief's first checkpoint
  (`git diff --stat` in the worktree root).
- More than 10 minutes or 50 tool calls with zero writes to the target root.
- Consecutive identical edit failures (three or more).
- Any scratch file in the worktree.
- Reasoning-dominant steps with no tool calls (long monologues that draft
  work in reasoning and never write it).
- A compaction followed by re-exploration from zero: re-send the state
  (branch, remaining ACs, diff summary) immediately.
