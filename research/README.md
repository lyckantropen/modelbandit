# Summaries refresh protocol

How `policy.json` `summaries` — and the free-tier catalog — are produced and
kept current. Read this only when the skill offers a refresh and the user
accepts — `SKILL.md` step 7 is the trigger, this is the procedure.

## 1. Scope the cycle

- Run `python3 skills/openrouter-model-router/scripts/bind.py --check-policy --top 15 --scope` — 15 is the research
  depth; the default 8 is stricter than the research scope and over-reports
  stale. `--scope` prints two fact lines under each gap, stale-summary and
  stale-signal bullet: where the model still ranks, and its catalog row with
  daily-token window totals.
- **Gap models** (ranked, no summary) are what to research. **Stale summaries**
  are what to retire or re-research. Models gone from the model list keep a
  summary only to document their exit (e.g. "not selectable"). The fact lines
  tell which case a model is before anything is researched.
- Fetch first-party anchors before briefing agents:
  `bind.py --anchors` renders the benchmark tables for the refresh scope —
  the policy's gaps then stale entries — one table per source (Artificial
  Analysis, Design Arena, OpenRouter evals), plus a closing line naming the
  scoped models the feed does not cover. Explicit model ids anchor just
  those instead. Embed the numbers in the briefs as facts to verify or
  extend — they also expose index rescales between research dates.
- The anchors command fetches the combined, unfiltered benchmarks feed once;
  do not fetch the sources one by one — one unfiltered fetch is fresher than
  per-source fetches. The data endpoints behind the check and the anchors
  need a key: `OPENROUTER_API_KEY`, or an OpenCode auth.json with an
  openrouter entry. The models catalog is keyless and needs nothing.

## 2. Research

- Split the models into groups of ~5, keeping families together (variants of
  one model belong in one group).
- One background agent per group, with the standard brief: for each model —
  **benchmark standing** (the step-1 anchor tables carry the first-party
  numbers; the agent verifies and extends them), **opinions**
  (community and press, every claim cited with a URL), **known for** (one
  sentence), **caveats** (quality, quantization, provider routing, licensing).
- The brief demands honesty over completeness: when sources disagree or a
  fact is unavailable (stealth and preview models often have none), the agent
  states that rather than guessing.
- Output: one file `research/<YYYY-MM>-top15-<group>.md`, per-model sections
  plus a final `## Policy summaries` section (2–3 sentences per model).

## 3. Distill into policy.json

- Replace or add `summaries` entries keyed by model-id prefix; longest-prefix
  matching keeps families apart (`z-ai/glm-5.3` vs `z-ai/glm-5.3-flash`).
- 2–3 sentences: what it is, where it stands, when to pick it, the caveats
  that change a decision. Prices and index numbers are dated snapshots —
  date them.
- Delete summaries that are stale beyond use; keep dated exclusions.
- **Never write `hints`** in a refresh: fit and evidence are user taste, not
  research. Do report what `--check-policy` says about them — stale fit keys
  and signal coverage gaps — and the user edits the taste. A refresh reconciles
  coverage; it never invents preference.

## 4. Free-tier maintenance

The free catalog (`policy.json` `free_models`) is the refresh cycle's to own:
both platforms document their free tiers as "limited time", so the catalog
churns with them instead of freezing.

- **Reconcile first.** Each cycle, check what the platforms still serve —
  OpenRouter's `:free` suffixes and OpenCode's free `opencode/*` models —
  against the catalog. A ranked OpenRouter `:free` route needs no entry (its
  window comes from the models list, its Exposure defaults to `trains`);
  entries exist for what the models list cannot describe — `opencode/*` and
  local models — and for any route whose documented data use departs from
  the default.
- **Admit with its facts.** An entry is keyed by id-prefix and carries
  `context_length`, `exposure`, and an optional `summary_ref` naming the
  `summaries` key that judges task fit for the family. Admission requires a
  resolving summary, found by longest-prefix match in `summaries` or by the
  entry's explicit `summary_ref`, researched per sections 1–3.
- **Exposure comes from the provider's own docs.** Take `exposure` from the
  provider's documented data use, cited in the summary — "collected data may
  be used to improve the model" or the verbatim quote from NVIDIA's endpoint
  terms, "do not submit personal or confidential data," is `trains`; a
  documented no-retention statement is `no-retention`;
  served on this machine is `local`. A route the catalog does not carry
  stays `trains` until documented otherwise. A user's explicit `exposure`
  override in `policy.json` outranks the catalog (longest prefix wins).
- **Retire with a documented exit.** When a platform stops serving a route,
  remove its `free_models` entry and leave the exit documented — a dated
  note in the family's summary, the space-bunny precedent of documenting
  exits. Free ends without warning; the note is how the churn stays
  legible.

## 5. Close the loop

- Re-run `--check-policy --top 15` until only accepted drift remains (models
  deliberately excluded, documented as such).
- If the check reports `coefficient re-tune due: yes`, the scoring exponents
  (`policy.json` `scoring`) no longer balance the pools — re-tune them against
  the thresholds there before shipping the cycle's content.
- Run the unit suite. Commit research files and `policy.json` together; tag a
  content drop (v1.4, v1.5, …).
