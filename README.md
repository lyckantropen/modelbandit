# openrouter-model-router

Pick OpenRouter models by **domain popularity** and price them **live, per
endpoint**. An agent skill (`SKILL.md`) whose mechanism is one stdlib-only
Python script (`scripts/bind.py`) that also runs fine as a plain CLI.

Selection is revealed preference — what real traffic actually runs in a domain
(the OpenRouter Data API task-classification leaderboards and daily token
rankings) — never benchmarks or taste. Prices are per endpoint because the same
model can span 20x on output across providers (`deepseek-v4-pro-0813`: $0.40–8.00
per 1M out). User verdicts annotate the ranking and never reorder it.

## Install

Agent use — symlink (or copy) into your skills directory:

```bash
ln -s ~/openrouter-model-router ~/.agents/skills/openrouter-model-router
```

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

The agent resolves the domain (here: writing), binds the effort rung, shows
the popularity ranking with hints and research summaries beside it, projects
the run ("$0.036 worst / $0.003 floor") — and flags whether `policy.json` is
due for a research refresh.

**A set of tickets** — one binding per domain, whole-run budget:

> Work through the tickets in <directory>. Before starting, use
> the openrouter-model-router skill to plan model spend: group the tickets by domain
> (research, writing, coding, orchestration, ops), bind one model and effort
> rung per group, project the total against a $5 budget, and stop and tell me
> if the projection goes over.

The agent ranks candidates per group, binds each, and reports a projection
like "30 tickets: $1.08 worst / $0.10 floor" before any spend — moving down
the ranking or the rung if the budget binds.

Mechanics: `python3 scripts/bind.py --help`. Policy: `SKILL.md`.

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
