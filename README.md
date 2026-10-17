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

```bash
# what domains exist and which leaderboard tags they map to
python3 scripts/bind.py --list-domains

# rank candidates for a domain, project 30 tickets against a budget
python3 scripts/bind.py --domain writing --tickets 30 --budget 2

# effort intent binds to a rung on the picked model's ladder
python3 scripts/bind.py --domain research --effort thorough

# price at the floor instead of the budget-safe worst endpoint
python3 scripts/bind.py --domain coding --pricing-basis best
```

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
| `verdicts` | user-validated notes, shown beside rows, never reordering |

Personal by design: this repo is private and the verdicts are taste.

## Development

```bash
python3 -m unittest discover -s tests        # unit suite, no network, no deps
python3 tests/live_smoke.py                  # manual, hits the real API
```

CI runs the unit suite only.
