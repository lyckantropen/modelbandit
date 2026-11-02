# Setup in detail

The expanded companion to the README's [Setup](../README.md#setup) section:
what each file is, the full zone rules, and the offline status mode. Both
files are normally written for you — the skill runs the two interviews that
produce them, linked from each section.

## API key

Live data — the task-classification leaderboards, the daily rankings,
endpoint pricing, the free-request counter — needs an OpenRouter key. Create
one at [openrouter.ai/keys](https://openrouter.ai/keys).

Pickup, in order, with no flag to pass:

1. the `OPENROUTER_API_KEY` environment variable;
2. an OpenCode `auth.json` carrying an `openrouter` entry.

Without a key the live fetches stop with `OpenRouter Data API needs a key:
…`. Nothing else breaks: the offline modes — `--list-domains`,
`--assert-allowed`, `--check-secrets`, `--status` — keep working, and the
models catalogue (`/api/v1/models`) is keyless.

## Free-use zones

The zones file lives at the machine's config root:
`$XDG_CONFIG_HOME/modelbandit/zones.json`, defaulting to
`~/.config/modelbandit/zones.json`. Its schema:

```json
{"zones": [{"path": "~/work", "free": "open"}], "default": "closed"}
```

`path` is a folder, `free` one of three regimes. `~` and environment
variables expand, and paths compare the way the platform does. The complete,
worked example lives in the [README](../README.md#zonesjson).

### The three regimes

- **`open`** — free models may run on content here, whatever a route retains.
- **`sensitive`** — a free route that may retain what you send (`trains`) is
  excluded; no-retention free routes and models served on this machine stay.
- **`closed`** — no remote free route may run here at all; models served on
  this machine never leave it and stay in.

The regimes order **`open` < `sensitive` < `closed`**, and a stricter regime
dominates every milder one in every dimension — `closed` implies
`sensitive`.

### Undeclared is closed

Anything the file does not name takes the default, and the default is
`closed` — including the whole file being absent. That is why
`"default": "closed"` is spelled out: the file opens what it names, and only
that. The longest covering prefix wins, so a nested path can only be stricter
than what covers it, and a path the file never names never opens.

### The effective regime: stricter of two

The regime a run works under is the **stricter of two**: the zone of its
working folder and the zone of the repository that folder came from (the
parent of `git rev-parse --git-common-dir`). Git missing or failing leaves
the working folder's zone alone.

An undeclared worktree root therefore stays closed however open its
repository is — to let the origin repository's zone decide, declare the
directory the worktrees live in:

```json
{"zones": [{"path": "~/.opencode/worktrees", "free": "open"}], "default": "closed"}
```

### Validation is loud

An unknown key or an unknown regime stops the run naming the offending key or
entry, two entries spelling the same place are refused, and the built-in
default is additive-only — no file can open what the machine closed. An
invalid config refuses with status 4 and writes nothing, so `--write-zones`
over an existing file cannot corrupt it.

### What the posture governs

The posture governs where free routes may run, not where you may work: zones
only ever remove remote free routes at source, and **paid routes work
from the first run**. Free routes wait: until a path is declared, remote free
routes are excluded — visibly, never silently. Why the default is `closed`
rather than an opening one is a recorded decision:
[ADR-0003, Fail closed by default](adr/0003-fail-closed-by-default.md).

### Writing the file

The skill's **"Set up the free-use zones"** interview asks, per folder,
*"may free models — some of which retain what you send — run on content
here?"*, proposes the resulting JSON in full, and writes it through
`--write-zones` — no mode ever needs this file hand-written. Then review the
printed path and the file's contents, and verify afterwards: the next run's
`zone:` header, or `--assert-allowed`, states the posture now in force.
[Interview](../skills/modelbandit/SKILL.md#set-up-the-free-use-zones).

## Secrets file

The Secrets gate reads the project's **`modelbandit.secrets.json`** — at the
folder's git root when it is in a repository, the folder itself otherwise —
for project-specific phrases and patterns.

- **Optional by design.** While the file is missing, the built-in credential
  rules alone decide, and the project's own rules are never applied until it
  exists.
- **Built by interview.** The skill's
  [Set up the secrets file](../skills/modelbandit/SKILL.md#set-up-the-secrets-file)
  interview scans the repository for candidate identifiers (not credential
  values), records your include/exclude decision per candidate, and writes
  the file through `--write-secrets`.
- **Additive merges.** Existing rules are never removed, exact duplicates are
  kept once, and the writer's report gives counts, never rule values. The
  built-in credential and machine-fact rules always apply and cannot be
  disabled.
- **Commit or gitignore.** If the confirmed entries identify a person, client
  or internal system — or you chose not to commit the file — the writer
  gitignores it once; a file that is already tracked is refused until you
  `git rm --cached` it.
- **Read at check time.** `--check-secrets` reads the file itself, with the
  shape's material on stdin and one `--outside-file PATH` per named outside
  source. It reports **safe**, **sensitive** or **not certified** and names
  the rule class that tripped it (`phrase #1`, `pattern #1`, a credential
  pattern, a machine fact) — never a rule's value.

## Checking your setup

```bash
python3 skills/modelbandit/scripts/modelbandit.py --status
```

The offline setup report: read-only, fully offline (no endpoint fetch, no
classification, no quota, no probe), and it prints the secrets file's
presence only, never its contents. One line each — zone, zones file, secrets
file, policy age — plus, while the zones file is absent, one actionable line:

```text
zone: undeclared (closed)
zones file: absent (~/.config/modelbandit/zones.json) — undeclared paths are closed
next: create ~/.config/modelbandit/zones.json — see the skill's setup interview
secrets file: absent (<working dir>/modelbandit.secrets.json) — built-in default rules apply
policy: <policy path> — 0d old
```

Exit status: **0** whenever setup files are absent — a missing zones or
secrets file is the documented default, not an answer the status must carry;
**4** only when a file that exists fails validation, named on stderr.
`--working-dir` judges the folder the way the pre-flight does. With
`--json`, one object replaces the lines (`mode`, `ok`, `zone`,
`zones_file`, `secrets_file`, `policy`).