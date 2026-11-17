# Steering: gemma-4-12b-it-qat

Served id: `lmstudio/gemma-4-12b-it-qat`. Brief: paste
`operating-discipline.md`, then this block.

**Deal scope** — quick, bounded turns where speed matters more than depth.
Fastest green of the local benchmark (~70 tok/s, 4/4 in ~99 s) but the
thinnest artifact (Phase-4 2/3/2) and it **exits 0 on failure** — never use
where exit codes matter. Both real spec-ticket attempts (#85) failed; the
second one's hardening moved the failure without removing it.

**Bench standing** — fastest green run of the whole benchmark; artifacts
thin (broad `except`, 4 tests, zero exit codes).

## Observed failure modes (spec #75, 2026-11-16)

- **write-not-edit in the wrong root** — attempt 1 replaced the session
  checkout's 4,898-line script with a 34-line snippet via `write()` to a
  relative path (run `***REMOVED***`). It self-reported
  the damage honestly ("I have made a serious error…") and the file was
  git-restored with zero loss — honesty kept the recovery cheap, but the
  run made zero ticket progress.
- **Split-root confusion misread as discipline** — file-tool calls resolved
  to the session checkout while `cd`-prefixed shell ran in the worktree;
  all edits landed in the checkout, and it read the empty diff as proof its
  targeted-edits discipline was working. Twice.
- **Edit-anchor sloppiness** — attempt 2 (hardened: absolute paths, zero
  `write` calls) still failed 10 of 13 `edit` calls, five of them the
  identical non-unique `oldString: "\n"` retried verbatim. Two *successful*
  edits used a `newString` that did not contain the anchor, silently
  deleting constants and duplicating a block — each reported "1
  replacement", never re-read.
- **No git verification at the end** — asserted a clean tree while running
  zero git commands; left a scratch file in the worktree against its
  explicit zero-scratch rule; ended on an empty assistant message.

## Steering block

- Absolute paths everywhere; the declared worktree root is the only
  writable root. After any edit or write, run `git diff --stat` **in that
  root** — an empty diff means the edit went somewhere else, not that the
  tree is clean.
- Existing files are changed with `edit` only. `write` is for new files in
  the worktree, nothing else.
- Every `oldString` must be unique and non-empty. Three failed anchors on
  one region = stop and report the blocker.
- After each successful edit, re-read the edited region once. If the
  replacement did not contain the anchor text, revert via git immediately.
- The final claim about tree state quotes `git status --porcelain` output.
  No quoted output, no claim.

## Prompting and serving facts

- **Prompt template**: use the static Gemma preset, not "Infer from files"
  (the embedded Jinja template crashes on tool execution — the known
  `UndefinedValue` tool-calling failure). Same fix family as other Gemma
  GGUFs.
- Sampling knobs server-default in all bench passes; flat 70 tok/s across
  tuning probes.
- Exits 0 on script failure (persistent bench flaw, self-reported nothing):
  wrap its deliverables with an external exit-code check when correctness
  gates on it.
