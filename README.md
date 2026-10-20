# openrouter-model-router

Pick OpenRouter models by **domain popularity** and price them **live, per
endpoint**. An agent skill (`skills/openrouter-model-router/SKILL.md`) whose mechanism is one stdlib-only
Python script (`skills/openrouter-model-router/scripts/bind.py`) that also runs fine as a plain CLI.

Selection is revealed preference — what real traffic actually runs in a domain
(the OpenRouter Data API task-classification leaderboards and daily token
rankings) — never benchmarks or taste. Prices are per endpoint because the same
model can span 20x on output across providers (`deepseek-v4-pro-0813`: $0.40–8.00
per 1M out). User verdicts annotate the ranking and never reorder it.

## Install

With the skills installer (the installer itself needs Node.js 22.20+):

```bash
npx skills add lyckantropen/openrouter-model-router
```

Requirements: Python 3 (3.10 and 3.13 tested), stdlib-only — no dependencies,
no environment to provision.

Consumer notes:

- For reproducible remote installs, pin a git ref.
- The installer sends anonymous telemetry; opt out with `DISABLE_TELEMETRY=1`
  or `DO_NOT_TRACK=1`.

Or, from your own checkout — clone anywhere, link from the checkout: a
location-independent symlink from the skill subtree into your skills directory:

```bash
ln -s /path/to/openrouter-model-router/skills/openrouter-model-router ~/.agents/skills/openrouter-model-router
```

Existing installs: re-point the symlink at the new `skills/openrouter-model-router`
subtree.

## Usage

The skill fires on model-choice questions; naming it is enough (it is
model-invoked). In OpenCode, invoke it as `@openrouter-model-router`; in other
harnesses, just say "use the openrouter-model-router skill". The natural
interface is a prompt — two shapes cover most use.

**Single task** — one piece of work, picked and costed before spending:

> I need to write a .md research note on <topic>, roughly 1500 words. Using
> the openrouter-model-router skill: pick the model for this, weigh the hints and
> summaries against the ranking, and tell me what the run will cost before
> starting.

The agent resolves the domain (here: writing), orders candidates by task score
(popularity priced at effort), judges task fit from the research summaries
(context window, rung coverage, domain guidance), projects the run ("$0.036
worst / $0.003 floor") — stepping down the order if the project already runs
the pick — and flags whether `policy.json` is due for a research refresh.

**A set of tickets** — one binding per domain, whole-run budget:

> Work through the tickets in <directory>. Before starting, use
> the openrouter-model-router skill to plan model spend: group the tickets by domain
> (research, writing, coding, orchestration, ops), deal each group's tickets
> across the popular models (preference-tilted), project the total against a $5
> budget, and stop and tell me if the projection goes over.

The agent ranks candidates per group, deals the tickets (`--deal`), and reports
a projection like "30 tickets: $1.08 worst / $0.10 floor" before any spend —
moving down the ranking or the rung if the budget binds. The deal spreads a
batch across the popular candidates instead of running one model for
everything: eligibility stays popularity, the deal tilts by preference
(`policy.json` `affinity`), and the seed makes the plan reproducible. One
`bind.py --deal` invocation deals one ticket shape — a run's domain, effort,
token profile and `--fit` combination — so tickets of the same shape share one
task-fit assessment: the judgments are made once for the run and every ticket
the deal draws inherits them. Groups that differ in any of the four are
separate shapes, each dealt by its own invocation.

### Directly

The mechanism is one stdlib script; `--help` is the full reference.

What domains exist and which leaderboard tags they map to:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --list-domains
```

Rank candidates for a domain, project 30 tickets against a budget:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --domain writing --tickets 30 --budget 2
```

Effort intent binds to a rung on the picked model's ladder:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --domain research --effort thorough
```

Multi-ticket runs deal the tickets across the popular pool, preference-tilted
and reproducible per project seed:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --domain writing --tickets 12 --deal --seed my-project
```

The agent's task-fit judgments (0-5) compose as score * fit/5:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --domain writing --fit "z-ai/glm-5.3=4.5,openai/gpt-6-luna=1"
```

Price at the floor instead of the budget-safe worst endpoint:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --domain coding --pricing-basis best
```

Summary drift and policy age:

```bash
python3 skills/openrouter-model-router/scripts/bind.py --check-policy
```

Policy: `skills/openrouter-model-router/SKILL.md`.

## Data

Two endpoints need an OpenRouter API key (`OPENROUTER_API_KEY`, or an OpenCode
`auth.json` with an `openrouter` entry is picked up automatically):

- `/api/v1/classifications/task` — task-tag leaderboards with per-tag model shares
- `/api/v1/datasets/rankings-daily` — daily token usage per model

`/api/v1/models` (and per-model `/endpoints`) is keyless. Everything is cached
24h in `~/.cache/modelbind/`; `--refresh` bypasses.

Rankings data is licensed **CC BY 4.0**. When quoting figures outside the tool's
own output, carry: `Source: OpenRouter (openrouter.ai/rankings), as of <as_of>`.

## policy.json

| key | purpose |
| --- | --- |
| `baseline.id` | price anchor for Δ columns; not a selection input |
| `domains` | five domains → leaderboard tags (a lens, not a partition) |
| `hints` | tentative user observations — advisory, shown beside rows, never reordering |

Personal by design: this repo is private and the verdicts are taste.

## Development

```bash
python3 -m unittest discover -s tests        # unit suite, no network, no deps
python3 tests/live_smoke.py                  # manual, hits the real API
```

CI runs the unit suite only.
