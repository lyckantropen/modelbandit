# Summaries refresh protocol

How `policy.json` `summaries` are produced and kept current. Read this only
when the skill offers a refresh and the user accepts — `SKILL.md` step 6 is
the trigger, this is the procedure.

## 1. Scope the cycle

- Run `python3 scripts/bind.py --check-policy --top 15` — 15 is the research
  depth; the default 8 is stricter than the research scope and over-reports
  stale.
- **Gap models** (ranked, no summary) are what to research. **Stale summaries**
  are what to retire or re-research. Models gone from the model list keep a
  summary only to document their exit (e.g. "not selectable").
- Fetch first-party anchors before briefing agents:
  `GET /api/v1/benchmarks?source=artificial-analysis` (and the OpenRouter
  sources if relevant). Embed the numbers in the briefs as facts to verify or
  extend — they also expose index rescales between research dates.

## 2. Research

- Split the models into groups of ~5, keeping families together (variants of
  one model belong in one group).
- One background agent per group, with the standard brief: for each model —
  **benchmark standing** (first-party numbers where possible), **opinions**
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
- **Never touch `hints`** in a refresh: those are user taste, not research.

## 4. Close the loop

- Re-run `--check-policy --top 15` until only accepted drift remains (models
  deliberately excluded, documented as such).
- Run the unit suite. Commit research files and `policy.json` together; tag a
  content drop (v1.4, v1.5, …).
