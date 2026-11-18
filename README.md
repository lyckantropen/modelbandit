# modelbandit

Pick OpenRouter models by **domain popularity** and price them **live, per
endpoint**. It is an agent skill (`skills/modelbandit/SKILL.md`) built on one
stdlib-only Python script (`skills/modelbandit/scripts/modelbandit.py`) that
also runs as a plain CLI.

Selection is revealed preference — what real traffic actually runs in a
domain, never benchmarks or taste. Prices are per endpoint, because the same
model can span 20x on output across providers (`deepseek-v4-pro-0813`:
$0.40–8.00 per 1M out). User verdicts annotate the ranking and never reorder
it.

## Install

With the skills installer (the installer itself needs Node.js 22.20+):

```bash
npx skills add lyckantropen/modelbandit
```

Requirements: Python 3 (3.10 and 3.13 tested), stdlib-only — no dependencies,
no environment to provision.

Consumer notes:

- For reproducible remote installs, pin a git ref.
- The installer sends anonymous telemetry; opt out with `DISABLE_TELEMETRY=1`
  or `DO_NOT_TRACK=1`.

Or, from your own checkout — a location-independent symlink from the skill
subtree into your skills directory:

```bash
ln -s /path/to/modelbandit/skills/modelbandit ~/.agents/skills/modelbandit
```

Existing installs: re-point the symlink at the new `skills/modelbandit`
subtree.

Arriving from this project's earlier names (`modelrouter`, `modelbind`,
`bind.py`)? Every old name has a new one, and old paths and invocations have
no compatibility fallback — [migrate.md](skills/modelbandit/migrate.md) lists
what each became and what silently breaks if a step is skipped.

## Quick start

The natural interface is a prompt. Once the skill is installed, it fires on
model-choice questions — naming it is enough (in OpenCode, invoke it as
`@modelbandit`; in other harnesses, say "use the modelbandit skill"):

> I need to write a .md research note on <topic>, roughly 1500 words. Using
> the modelbandit skill: pick the model for this, weigh the hints and
> summaries against the ranking, and tell me what the run will cost before
> starting.

The agent resolves the domain (here: `writing`), orders the candidates by what
traffic actually runs there, judges task fit from the research summaries, and
projects the run — `"$0.036 worst / $0.003 floor"` — before you spend
anything.

Prefer the raw CLI? One command ranks a domain (live data needs an
[API key](#api-key)):

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing
```

A first run opens with a header — the zone that governed it, the token
profile, the age of `policy.json`, where the ranking data comes from — then
the ranking table: share, score, price, context window, Exposure. Every line
of that first-run output, annotated:
[docs/cli.md](docs/cli.md#first-run-annotated). `--help` is the full
reference.

Free routes work from the first run with no setup files. Zones are open unless declared ([ADR-0010](docs/adr/0010-open-unless-declared.md)) and every run's header states the effective posture. The [single interaction loop](skills/modelbandit/SKILL.md#one-interaction-loop) describes the run.

## Setup

Live data uses an API key. Free routes work on the first run without setup
files; a zones file is optional and lists only paths declared `closed`.

Check where you stand at any point — offline, read-only, never prints file
contents:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --status
```

### API key

Live data — the task-classification leaderboards, the daily rankings, endpoint
pricing, the free-request counter — needs one: create it at
[openrouter.ai/keys](https://openrouter.ai/keys). The script picks it up on
its own, from the `OPENROUTER_API_KEY` environment variable or from an OpenCode
`auth.json` carrying an `openrouter` entry; there is no flag to pass. Without
one, the live fetches stop (`OpenRouter Data API needs a key: …`) while the
offline modes — `--list-domains`, `--assert-allowed`, `--check-secrets`,
`--status` — keep working. Details: [docs/setup.md](docs/setup.md#api-key).

### zones.json

The optional file lives at `$XDG_CONFIG_HOME/modelbandit/zones.json`,
defaulting to `~/.config/modelbandit/zones.json`. It is an opt-out list of
paths declared `closed`:

```json
{"zones": ["~/work/acme/payroll"]}
```

With nothing declared, everything is open, including when the file is absent.
The effective posture is the stricter of the working folder and origin
repository, so one closed declaration covers that repository's worktrees.
Free routes work from the first run; the default-posture decision is recorded
in [ADR-0010](docs/adr/0010-open-unless-declared.md). More:
[docs/setup.md](docs/setup.md#free-use-zones).

Write the JSON on stdin with `--write-zones`, then review the file and confirm
the posture with the next run's `zone:` header or `--assert-allowed`.

### Secrets gate

At deal time the Secrets gate applies the built-in rules to the material a run
is given; `--check-secrets` inspects one material. Inventory:
[docs/gates.md](docs/gates.md).

## Keeping your data safe with free models

Free routes can retain what you send - an unknown free route defaults to
`trains` - so five parts decide what happens to your material:

1. **Secrets gate — what the material is.** Before any model is chosen, the
   shape's material goes through `--check-secrets` and comes back **safe**,
   **sensitive** or **not certified** — decided once at collection; the loop runs this automatically.
2. **Zones - where free may run.** `open` unless declared, stricter of working
   folder and origin repository ([zones.json](#zonesjson)).
3. **Exposure marks — which routes retain.** Every candidate carries its
   serving route's Exposure — `no-retention`, `trains` or `local` — a property
   of the route, never inferred from price. On a Sensitive shape a `trains`
   route is marked in the table (`exposed (trains)`) and never picked or
   dealt: marked, never hidden
   ([SKILL.md reference](skills/modelbandit/SKILL.md#reference)).
4. **`--assert-allowed` pre-flight — before launch.** An orchestrator holding a
   model id — from a plan, another agent, a previous run — asks the zone first:
   launch only when the pre-flight says `allowed`. An error, a missing field, a
   malformed response — anything else means do not launch. No policy file, no
   classification fetch, no network, and it fails closed
   ([command](#directly)).
5. **When a zone blocks.** A blocked ticket names its zone, stops, and asks.
   How it looks in practice is one sentence in [the single interaction loop](skills/modelbandit/SKILL.md#one-interaction-loop).

## Usage

Quick start showed the single-task prompt; a whole batch is the other shape
that covers most use — one binding per domain, whole-run budget:

> Work through the tickets in <directory>. Before starting, use
> the modelbandit skill to plan model spend: group the tickets by domain
> (research, writing, coding, orchestration, ops), deal each group's tickets
> across the popular models (preference-tilted), project the total against a
> $5 budget, and stop and tell me if the projection goes over.

The agent ranks candidates per group, deals the tickets (`--deal`), and
reports a projection like "30 tickets: $1.08 worst / $0.10 floor" before any
spend — moving down the ranking or the rung if the budget binds. The deal
spreads a batch across the popular candidates instead of running one model for
everything: eligibility stays popularity, the deal tilts by preference
(`policy.json` `affinity`), and the seed makes the plan reproducible. A
Sensitive shape is dealt with
`--sensitive`: only candidates whose Exposure is `local` are admitted (ADR
0008 — no-retention leaves the machine too), the rest marked in the table
with their reason, never hidden, and a run with no eligible local candidate
stops with `blocked: no eligible local candidate` (exit 0). Mechanics:
[SKILL.md](skills/modelbandit/SKILL.md#reference).

One task? See [Quick start](#quick-start).

## Reference

### Directly

The mechanism is one stdlib script; `--help` is the full reference. The moves
people reach for daily:

```bash
# What domains exist and which leaderboard tags they map to
python3 skills/modelbandit/scripts/modelbandit.py --list-domains

# Rank a domain, project 30 tickets against a $2 budget
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --tickets 30 --budget 2

# Deal 12 tickets across the popular pool, reproducible per project seed
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --tickets 12 --deal --seed my-project

# Pre-flight a model against the machine's free-use zones before launching it
python3 skills/modelbandit/scripts/modelbandit.py --assert-allowed --model z-ai/glm-5.4:free --working-dir .
```

The pre-flight's output says `allowed: <id>` or `blocked by the free-use
zone` — either verdict exits 0, so read the verdict, not the status. The full
gallery — effort rungs, `--fit` scores, `--pricing-basis`, `--check-policy` —
is [in docs/cli.md](docs/cli.md#command-gallery).

### Data

These endpoints need an OpenRouter API key (`OPENROUTER_API_KEY`, or an
OpenCode `auth.json` with an `openrouter` entry is picked up automatically):

- `/api/v1/classifications/task` — task-tag leaderboards with per-tag model shares
- `/api/v1/datasets/rankings-daily` — daily token usage per model
- `/api/v1/key` — the account's daily `free_model_daily_requests` quota counter
- per-model `/api/v1/models/{slug}/endpoints` — provider pricing and capacity

`/api/v1/models` is keyless. The model catalogue, leaderboards and endpoint
details are cached for 24h in `~/.cache/modelbandit/`; the key payload is
cached for 60 seconds and is never served stale. `--refresh` bypasses either
cache.

Rankings data is licensed **CC BY 4.0**. When quoting figures outside the
tool's own output, carry: `Source: OpenRouter (openrouter.ai/rankings), as of
<as_of>`.

### policy.json

| key | purpose |
| --- | --- |
| `baseline.id` | price anchor for Δ columns; not a selection input |
| `domains` | five domains → leaderboard tags (a lens, not a partition) |
| `hints` | tentative user observations — advisory, shown beside rows, never reordering |
| `summaries` | one research summary per model, claims cited; filled by the summaries-refresh procedure |

Personal by design: `hints` and `summaries` are your verdicts and
your research — the shipped policy carries one clearly labeled
example entry in each section and nothing else. Write your own;
the summaries-refresh procedure fills `summaries`.

### Development

```bash
python3 -m unittest discover -s tests        # unit suite, no network, no deps
python3 tests/live_smoke.py                  # manual, hits the real API
```

CI runs the unit suite only.

## Documentation

Where everything else lives:

- [`skills/modelbandit/SKILL.md`](skills/modelbandit/SKILL.md) — the skill's
  full policy: one interaction loop, how a blocked ticket behaves, the reference.
- [`docs/setup.md`](docs/setup.md) - setup in detail: zones and the
  `--status` mode.
- [`docs/cli.md`](docs/cli.md) — the annotated first run and the command
  gallery.
- [`GLOSSARY.md`](GLOSSARY.md) and [`docs/adr/`](docs/adr/) — vocabulary and
  recorded decisions.
- [`research/README.md`](research/README.md) — how `policy.json`'s summaries
  are produced and refreshed.

## License

MIT — see [LICENSE](LICENSE).
