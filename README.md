# modelbandit

Pick OpenRouter models by **domain popularity** and price them **live, per
endpoint**. An agent skill (`skills/modelbandit/SKILL.md`) whose mechanism is one stdlib-only
Python script (`skills/modelbandit/scripts/modelbandit.py`) that also runs fine as a plain CLI.

The name: a bandit is the CS problem of choosing among options by observed payoff rather than benchmarks — which is this repo's thesis.

Selection is revealed preference — what real traffic actually runs in a domain
(the OpenRouter Data API task-classification leaderboards and daily token
rankings) — never benchmarks or taste. Prices are per endpoint because the same
model can span 20x on output across providers (`deepseek-v4-pro-0813`: $0.40–8.00
per 1M out). User verdicts annotate the ranking and never reorder it.

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

Or, from your own checkout — clone anywhere, link from the checkout: a
location-independent symlink from the skill subtree into your skills directory:

```bash
ln -s /path/to/modelbandit/skills/modelbandit ~/.agents/skills/modelbandit
```

Existing installs: re-point the symlink at the new `skills/modelbandit`
subtree.

## Quick start

One command ranks a domain (run it from the repo checkout — `--help` is the
full reference):

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing
```

Live ranking needs an OpenRouter API key — [API key](#api-key) if you don't
have one yet. Before [Setup](#setup), the header of a first run reads:

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
  source rather than listed below with a mark. [Setup](#setup) turns this line
  into the declaring path and its regime — `zone: <path> (open)`.
- `zones file: absent (~/.config/modelbandit/zones.json) — undeclared paths are closed`
  — printed only while the zones file doesn't exist: the exact path to create,
  and what its absence means ([zones.json](#zonesjson)).
- `profile=authoring (in=20,000 out=12,000 cached=40%) | effort=measured | basis=worst | policy: 0d old | source: …`
  — the run's coordinates: the token profile for the domain (authoring work is
  output-heavy), the effort rung, the pricing basis, the age of `policy.json`
  (a fresh checkout reads `0d old`; past about one rankings window the run
  offers a refresh), and where the ranking data comes from and as of when.
- `free quota: unavailable | :free routes excluded by the closed zone` — the
  day's free-request counter, which no run waits on: here it was not reported
  (the key endpoint did not answer, or the payload carried no counter). The
  clause after `|` is the zone's doing — with the effective zone `closed`,
  every remote free route was excluded before this ranking began. With a
  reachable counter the same line carries the day's figures instead
  (`used`/`limit`, left, protected reserve).

The table that follows is the ranking itself — share, score, price, context
window, Exposure. No remote free route appears in it until a path is
declared: **free routes wait for [Setup](#setup)**.

## Setup

Three things decide what this tool does on your machine: a key to read the
data, a zones file that says where free models may run, and — per project —
a secrets file the gate reads.

### API key

Live data — the task-classification leaderboards, the daily rankings, endpoint
pricing, the free-request counter — needs one: create it at
[openrouter.ai/keys](https://openrouter.ai/keys). The script picks it up on
its own, from the `OPENROUTER_API_KEY` environment variable or from an OpenCode
`auth.json` carrying an `openrouter` entry; there is no flag to pass. Without
one, the live fetches stop (`OpenRouter Data API needs a key: …`) while the
offline modes — `--list-domains`, `--assert-allowed`, `--check-secrets` — keep
working without it.

### zones.json

Free routes can retain what you send, so where they may run is opt-in, path
by path. The file lives at the machine's config root —
`$XDG_CONFIG_HOME/modelbandit/zones.json`, defaulting to
`~/.config/modelbandit/zones.json` — and a complete, general-purpose one looks
like this:

```json
{
  "zones": [
    {"path": "~/work", "free": "open"},
    {"path": "~/work/acme", "free": "sensitive"},
    {"path": "~/work/acme/payroll", "free": "closed"}
  ],
  "default": "closed"
}
```

Read it as: free models may run under `~/work`, except that a route which may
retain what it sees (`trains`) is excluded on content under `~/work/acme`, and
no remote free route may run under `~/work/acme/payroll` at all (models served
on this machine never leave it and stay in). The rules behind the example:

- The three regimes order **`open` < `sensitive` < `closed`**, and a stricter
  regime dominates every milder one in every dimension — `closed` implies
  `sensitive`.
- **Anything undeclared is `closed`** — including the whole file being absent.
  The longest covering prefix wins, so a nested path can only be stricter than
  what covers it, and a path the file never names never opens. That is why
  `"default": "closed"` is spelled out: the file opens what it names, and only
  that.
- The regime a run works under is the **stricter of two**: the zone of its
  working folder and the zone of the repository that folder came from (the
  parent of `git rev-parse --git-common-dir`). An undeclared worktree root
  therefore stays closed however open its repository is — declare the
  worktrees directory to let the origin repository decide.
- Validation is loud: an unknown key or an unknown regime stops the run naming
  the offending key or entry, and two entries spelling the same place are
  refused.

**Paid models are unaffected by this default** — the posture governs where
free routes may run, not where you may work: zones only ever remove remote
free routes at source, and paid routes work from the first run. **Free routes
wait for setup**: until a path is declared, remote free routes are excluded —
visibly, never silently downgraded. (What a route's own Exposure does to a
Sensitive shape is the next section's question, not the zone's.) Why the
default is `closed` rather than an opening one is a recorded decision:
[ADR-0003, Fail closed by default](docs/adr/0003-fail-closed-by-default.md).

Rather not hand-write JSON? The skill's **"Set up the free-use zones"**
interview asks, per folder, *"may free models — some of which retain what you
send — run on content here?"*, writes the file through `--write-zones`, and
has you review the result:
[Set up the free-use zones](skills/modelbandit/SKILL.md#set-up-the-free-use-zones).

Arriving from this project's earlier names? Every old name has a new one, and
old paths and old invocations have no compatibility fallback —
[migrate.md](skills/modelbandit/migrate.md) lists what each became and what
silently breaks if a step is skipped.

### Secrets file

The Secrets gate reads the project's **`modelbandit.secrets.json`** — at the
folder's git root when it is in a repository — for project-specific phrases
and patterns. The file is optional: while it is missing, the built-in
credential rules alone decide, and the project's own rules are never applied
until it exists. To create or extend one, run the skill's interview:
[Set up the secrets file](skills/modelbandit/SKILL.md#set-up-the-secrets-file)
— it proposes candidate identifiers, records your include/exclude decisions,
and writes the file through `--write-secrets`.

## Keeping your data safe with free models

Free routes can retain what you send — an unknown free route defaults to
`trains` — so what happens to your material is decided by five links, in
order, each pointing at where its rule lives:

1. **Secrets gate — what the material is.** Before any model is chosen, the
   shape's material goes through `--check-secrets` and comes back **safe**,
   **sensitive** or **not certified** — decided once, at collection, never
   mid-run. The verdict comes from the project's `modelbandit.secrets.json`
   plus this machine's own facts and the built-in credential rules
   ([setup interview](skills/modelbandit/SKILL.md#set-up-the-secrets-file)).
2. **Zones — where free may run.** `zones.json` marks paths `open`,
   `sensitive` or `closed`; undeclared is `closed`, and a run takes the
   stricter of its working folder's zone and its origin repository's
   ([Setup](#setup)).
3. **Exposure marks — which routes retain.** Every candidate carries its
   serving route's Exposure — `no-retention`, `trains` or `local` — a property
   of the route, never inferred from price. On a Sensitive shape a `trains`
   route is marked in the table (`exposed (trains)`) and never picked or
   dealt: marked, never hidden
   ([SKILL.md reference](skills/modelbandit/SKILL.md#reference)).
4. **`--assert-allowed` pre-flight — before launch.** An orchestrator holding
   a model id — from a plan, another agent, a previous run — asks the zone
   first: exit **0** means it may serve in that folder's effective zone, exit
   **5** means the free-use zone blocks it. No policy file, no classification
   fetch, no network, and it fails closed: with no shape stated it assumes
   Sensitive and says so ([command](#directly)).
5. **Closed-zone protocol — what the agent does when a zone blocks.** The
   rules live in the skill and are deliberately not copied into this README:
   [Closed-zone protocol](skills/modelbandit/SKILL.md#closed-zone-protocol).

## Usage

The skill fires on model-choice questions; naming it is enough (it is
model-invoked). In OpenCode, invoke it as `@modelbandit`; in other
harnesses, just say "use the modelbandit skill". The natural
interface is a prompt — two shapes cover most use.

**Single task** — one piece of work, picked and costed before spending:

> I need to write a .md research note on <topic>, roughly 1500 words. Using
> the modelbandit skill: pick the model for this, weigh the hints and
> summaries against the ranking, and tell me what the run will cost before
> starting.

The agent resolves the domain (here: writing), orders candidates by task score
(popularity priced at effort), judges task fit from the research summaries
(context window, rung coverage, domain guidance), projects the run ("$0.036
worst / $0.003 floor") — stepping down the order if the project already runs
the pick — and flags whether `policy.json` is due for a research refresh.

**A set of tickets** — one binding per domain, whole-run budget:

> Work through the tickets in <directory>. Before starting, use
> the modelbandit skill to plan model spend: group the tickets by domain
> (research, writing, coding, orchestration, ops), deal each group's tickets
> across the popular models (preference-tilted), project the total against a $5
> budget, and stop and tell me if the projection goes over.

The agent ranks candidates per group, deals the tickets (`--deal`), and reports
a projection like "30 tickets: $1.08 worst / $0.10 floor" before any spend —
moving down the ranking or the rung if the budget binds. The deal spreads a
batch across the popular candidates instead of running one model for
everything: eligibility stays popularity, the deal tilts by preference
(`policy.json` `affinity`), and the seed makes the plan reproducible. One
`modelbandit.py --deal` invocation deals one ticket shape — a run's domain, effort,
token profile, `--fit` and `--sensitive` combination — so tickets of the same
shape share one task-fit assessment: the judgments are made once for the run
and every ticket the deal draws inherits them. Groups that differ in any of
the five are separate shapes, each dealt by its own invocation. A Sensitive
shape (its material trips the Secrets gate — SKILL.md step 1) is dealt with
`--sensitive`: exposed candidates are excluded from its pick and deal,
marked in the table, never hidden.

## Reference

### Directly

The mechanism is one stdlib script; `--help` is the full reference.

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

The agent's task-fit judgments (0-5) compose as score * fit/5:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain writing --fit "z-ai/glm-5.3=4.5,openai/gpt-6-luna=1"
```

Price at the floor instead of the budget-safe worst endpoint:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --domain coding --pricing-basis best
```

Summary drift and policy age:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --check-policy
```

Pre-flight a model against the machine's free-use zones
(`$XDG_CONFIG_HOME/modelbandit/zones.json`) before launching it — exit 0 when
it may serve, 5 when the zone blocks it; no policy file, classification or
network needed:

```bash
python3 skills/modelbandit/scripts/modelbandit.py --assert-allowed --model z-ai/glm-5.4:free --working-dir .
```

Policy: [`skills/modelbandit/SKILL.md`](skills/modelbandit/SKILL.md).

### Data

These endpoints need an OpenRouter API key (`OPENROUTER_API_KEY`, or an OpenCode
`auth.json` with an `openrouter` entry is picked up automatically):

- `/api/v1/classifications/task` — task-tag leaderboards with per-tag model shares
- `/api/v1/datasets/rankings-daily` — daily token usage per model
- `/api/v1/key` — the account's daily `free_model_daily_requests` quota counter
- per-model `/api/v1/models/{slug}/endpoints` — provider pricing and capacity

`/api/v1/models` is keyless. The model catalogue, leaderboards and endpoint
details are cached for 24h in `~/.cache/modelbandit/`; the key payload is cached
for 60 seconds and is never served stale. `--refresh` bypasses either cache.

Rankings data is licensed **CC BY 4.0**. When quoting figures outside the tool's
own output, carry: `Source: OpenRouter (openrouter.ai/rankings), as of <as_of>`.

### policy.json

| key | purpose |
| --- | --- |
| `baseline.id` | price anchor for Δ columns; not a selection input |
| `domains` | five domains → leaderboard tags (a lens, not a partition) |
| `hints` | tentative user observations — advisory, shown beside rows, never reordering |

Personal by design: this repo is private and the verdicts are taste.

### Development

```bash
python3 -m unittest discover -s tests        # unit suite, no network, no deps
python3 tests/live_smoke.py                  # manual, hits the real API
```

CI runs the unit suite only.