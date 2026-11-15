# CLI reference

The mechanism is one stdlib-only script:
`skills/modelbandit/scripts/modelbandit.py`. `--help` is the authoritative
reference; this page shows what a run looks like and the moves people reach
for daily. Commands run from the repo checkout.

## First run, annotated

Before [Setup](../README.md#setup), the header of a first run reads:

```text
# Popularity ranking: writing

zone: undeclared (closed)
zones file: absent (~/.config/modelbandit/zones.json) — undeclared paths are closed
profile=authoring (in=20,000 out=12,000 cached=40%) | effort=measured | basis=worst | policy: 0d old | source: OpenRouter (openrouter.ai/rankings), as of 2026-10-26

free quota: unavailable | :free routes excluded by the closed zone
```

Every line of that output, in order (the blank lines are only spacing):

- `# Popularity ranking: writing` — the subject of the run: this domain's
  popularity ranking.
- `zone: undeclared (closed)` — the free-use zone that governed the run. No
  declared path matched, so the default applied, and the default is
  **closed**: every remote free route was already out of this run, removed at
  source rather than listed below with a mark. After [Setup](../README.md#setup)
  this line reads `zone: <path> (open)` — or names the resolved place when a
  junction or symlink moved the judgement.
- `zones file: absent (~/.config/modelbandit/zones.json) — undeclared paths are closed`
  — printed only while the zones file doesn't exist: the exact path to
  create, and what its absence means
  ([zones.json](../README.md#zonesjson)).
- `profile=authoring (in=20,000 out=12,000 cached=40%) | effort=measured | basis=worst | policy: 0d old | source: …`
  — the run's coordinates: the token profile for the domain (authoring work
  is output-heavy), the effort rung, the pricing basis, the age of
  `policy.json` (a fresh checkout reads `0d old`; past about one rankings
  window the run offers a refresh), and where the ranking data comes from and
  as of when.
- `free quota: unavailable | :free routes excluded by the closed zone` — the
  day's free-request counter, which no run waits on: here it was not reported
  (the key endpoint did not answer, or the payload carried no counter). The
  clause after `|` is the zone's doing — with the effective zone `closed`,
  every remote free route was excluded before this ranking began. With a
  reachable counter the same line carries the day's figures instead
  (`used`/`limit`, left, protected reserve).

The table that follows is the ranking itself — share, score, price, context
window, Exposure. No remote free route appears in it until a path is
declared: **free routes wait for [Setup](../README.md#setup)**.

## Command gallery

What domains exist and which leaderboard tags they map to:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --list-domains
```

Rank candidates for a domain, project 30 tickets against a budget:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --tickets 30 --budget 2
```

Effort intent binds to a rung on the picked model's ladder:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain research --effort thorough
```

Multi-ticket runs deal the tickets across the popular pool, preference-tilted
and reproducible per project seed:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --tickets 12 --deal --seed my-project
```

When a dealt model cannot serve, record its Spare taking the ticket over
whole — re-run the deal's own flags plus `--substitute`, so the same seed
re-derives the same deal. `--reason mechanical` (the default) covers
unreachable, out-of-quota or unloadable; a quality failure substitutes only
on an explicit dead-attempt report (`--reason dead-attempt`). Either way the
record — takeover, reason, restated fence — exits 0:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --tickets 12 --deal --seed my-project --substitute openrouter/deepseek/deepseek-v4-pro-0813 --reason mechanical
```

The agent's task-fit judgments (0-5) compose as score * fit/5:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --fit "z-ai/glm-5.3=4.5,openai/gpt-6-luna=1"
```

Local candidates come from the harness listing — pass the `lmstudio/*`
ids exactly as the harness dispatches them (e.g. from `opencode models`),
comma-separated and repeatable; without the flag the run claims no local
candidate:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --local-listing "lmstudio/qwen/qwen3.6-35b-a3b,lmstudio/zai-org/glm-4.7-flash"
```

Price at the floor instead of the budget-safe worst endpoint:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain coding --pricing-basis best
```

Summary drift and policy age:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --check-policy
```

The drift plus the facts behind each finding — where a summaries-refresh
cycle starts ([procedure](../research/README.md)):

```bash
python3 skills/modelbandit/scripts/modelbandit.py --check-policy --scope
```

Pre-flight a model against the machine's free-use zones
(`$XDG_CONFIG_HOME/modelbandit/zones.json`) before launching it — the output
says `allowed: <id>` or `blocked by the free-use zone`, and either verdict
exits 0, so read the verdict, not the status; no policy file, classification
or network needed:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --assert-allowed --model z-ai/glm-5.4:free --working-dir .
```

Offline setup report — zone, zones file, secrets file, policy age:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --status
```

Exit statuses: **0** is any verdict — safe, sensitive, not certified,
allowed, blocked, over budget; **2** is a usage error and **4** a
rules/config error, and neither is an answer. Read the verdict lines (or
`--json`), not `$?` — the full table lives in
[SKILL.md](../skills/modelbandit/SKILL.md#reference).