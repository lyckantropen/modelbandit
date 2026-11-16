# Setup in detail

The expanded companion to the README's [Setup](../README.md#setup) section:
the API key, optional zones file, and offline status mode.

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

Free routes work from the first run with no setup files. The zones posture is
open unless declared; an absent file means everything is open. The optional
file at `$XDG_CONFIG_HOME/modelbandit/zones.json` (default
`~/.config/modelbandit/zones.json`) is only an opt-out list of paths declared
`closed`:

```json
{"zones": ["~/work/acme/payroll"]}
```

The effective posture is the stricter of the working folder and its origin
repository, so one closed declaration covers that repository's worktrees.
The default-posture decision is recorded in
[ADR-0010, Open unless declared](adr/0010-open-unless-declared.md); ADR-0003
is its superseded predecessor. More on the run itself:
[the single interaction loop](../skills/modelbandit/SKILL.md#one-interaction-loop).

### Writing the file

`--write-zones` is a validated, atomic writer that reads JSON from stdin.
Review the file, then confirm the posture with the next run's `zone:` header
or `--assert-allowed`.

## Secrets gate

At deal time, the Secrets gate automatically applies the built-in credential,
identifier, machine-fact, and gitignored-content rules to the material a run
is given. `--check-secrets` manually inspects a single material.

## Checking your setup

```bash
python3 skills/modelbandit/scripts/modelbandit.py --status
```

The offline setup report is read-only and fully offline (no endpoint fetch,
classification, quota, or probe). Its header states the effective posture;
with nothing declared on a first run, everything is open and no action is
needed:

```text
zone: <working folder> (open)
zones file: absent (~/.config/modelbandit/zones.json)
secrets: built-in rules apply
policy: <policy path> - 0d old
```

Exit status: **0** when optional setup files are absent; **4** when a file
that exists fails validation, named on stderr.
`--working-dir` judges the folder the way the pre-flight does. With
`--json`, one object replaces the lines (`mode`, `ok`, `zone`,
`zones_file`, `secrets`, `policy`).
