# CLI reference

The mechanism is one stdlib-only script:
`skills/modelbandit/scripts/modelbandit.py`. `--help` is the authoritative
reference; this page shows what a run looks like and the moves people reach
for daily. Commands run from the repo checkout.

## First run, annotated

Every run's header states the effective posture. Zones are open unless
declared, so on a first run with nothing declared everything is open and free
routes work without setup files
([ADR-0010, Open unless declared](adr/0010-open-unless-declared.md)).

```text
# Popularity ranking: writing

zone: /path/to/your/project (open)
profile=authoring (in=20,000 out=12,000 cached=40%) | effort=measured | basis=worst | policy: 0d old | source: OpenRouter (openrouter.ai/rankings), as of 2026-11-15

free quota: 0/1000 used (1000 left) | reserve 5 protected; plan size does not gate
```

The ranking table reports share, score, price, context window, and Exposure.
The [single interaction loop](../skills/modelbandit/SKILL.md#one-interaction-loop)
describes how the run proceeds.

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
says `allowed: <id>` or `blocked: free-use zone`, and either verdict
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
