# Migrating to modelbandit

Everything converged on one name — `modelbandit`: the GitHub repo, the skill
folder and its frontmatter `name:`, the script
(`skills/modelbandit/scripts/modelbandit.py`, module `modelbandit`), the
config prefix (`~/.config/modelbandit/`), the cache (`~/.cache/modelbandit/`)
— and **the secrets file is retired**: old `modelrouter.secrets.json` /
`modelbandit.secrets.json` files are inert weight where they exist, delete
them. The old names — `openrouter-model-router`, `modelrouter`, `modelbind`,
`bind.py` — are gone
with **no compatibility fallback**: nothing reads an old path, nothing accepts
an old invocation. This file lists the old names on purpose.

## Failure modes — what silently breaks if you skip a step

- **Zones config not moved** (`~/.config/modelrouter/` →
  `~/.config/modelbandit/`): the tool never finds a zones file, every path
  reads as undeclared, and undeclared is `closed` — **zones fall back to
  `closed` everywhere**. No error names the move; runs just stop at the zone
  gate with `blocked by the free-use zone` in the output — an answer, exit 0
  like any verdict, not a failure (ADR-0004).
- **Secrets file not renamed** (`modelrouter.secrets.json` → `modelbandit.secrets.json` in each project): delete them — the gate applies built-in credential/identifier/machine-fact/gitignored-content rules to the material a run is given, automatically at deal time and via `--check-secrets` on a single material. No project rules file participates, by design (spec #75's mode split).
- **Skill symlink not re-pointed** (`~/.agents/skills/openrouter-model-router`
  → `~/.agents/skills/modelbandit` → the repo's `skills/modelbandit/`): the
  old link's target no longer exists, so the link **hard-breaks** — the skill
  does not load at all, in any harness.
- **Stale cache left behind** (`~/.cache/modelbind/`): it is no longer read.
  The only cost is an orphaned directory — it expires after 24h and
  refetching is free. Delete it.
- **Old invocation kept** (`@openrouter-model-router`, "use the
  openrouter-model-router skill"): it names nothing any more; the skill
  answers to `@modelbandit` / "the modelbandit skill". The agent falls back
  to guessing instead of ranking.

## Checklist A — your machine

- [ ] Move the zones config dir: `mv ~/.config/modelrouter ~/.config/modelbandit`.
       Skipped → zones fall back to `closed` everywhere.
- [ ] Delete any secrets file: `rm -f modelrouter.secrets.json modelbandit.secrets.json`. The gate applies built-in credential/identifier/machine-fact/gitignored-content rules to the material a run is given, automatically at deal time and via `--check-secrets` on a single material. No project rules file participates, by design (spec #75's mode split).
- [ ] Delete the stale cache: `rm -rf ~/.cache/modelbind`. Skipped → the
       orphaned directory lingers; nothing else breaks (24h TTL, refetches
       free).
- [ ] Re-create the skill symlink: remove the old link first
       (`rm ~/.agents/skills/openrouter-model-router` — it hard-breaks on the
       folder rename), then
       `ln -s /path/to/modelbandit/skills/modelbandit ~/.agents/skills/modelbandit`.
       Skipped → the skill symlink hard-breaks and the skill never loads.
- [ ] Use the new invocation: `@modelbandit` / "the modelbandit skill". Any
       personal alias, wrapper or muscle memory that calls
       `@openrouter-model-router` names nothing — it must be updated.

## Checklist B — your checkout / install

- [ ] Git remote URL: `git remote set-url origin
       git@github.com:lyckantropen/modelbandit.git`. GitHub redirects the old
       URL meanwhile, so fetches keep working — but the remote still says the
       old name. Skipped → you keep relying on a redirect GitHub may drop.
- [ ] Installer command: `npx skills add lyckantropen/modelbandit`. Any
       documented install command, script or doc that still carries
       `lyckantropen/openrouter-model-router` fails outright once the
       redirect goes away. Skipped → fresh installs from those docs break.
- [ ] Folder renames: the clone directory `openrouter-model-router` →
       `modelbandit`, the skill subtree `skills/openrouter-model-router/` →
       `skills/modelbandit/`, the script `scripts/bind.py` →
       `scripts/modelbandit.py`. Local instructions, task files, direnv and
       editor bindings that spell the old paths point at nothing. Skipped →
       every local reference to the old paths keeps failing file-not-found.
- [ ] Local callers of `bind.py`: any script, cron job, task or alias that
       runs `.../bind.py` must run `.../modelbandit.py` instead, and any code
       doing `import bind` or `mock.patch("bind.…")` must switch to
       `modelbandit` — the old module does not exist. Skipped → those callers
       fail with file-not-found / ImportError the next time they run.

The rename changed identifiers only: same ranking, same prices, same zones. Secrets rules-file semantics were RETIRED — old `modelrouter.secrets.json` / `modelbandit.secrets.json` files are inert weight; delete them where they exist. One behavior exception — **the default deal seed**:
`--seed` used to default to `bind` and now defaults to `modelbandit`, so an
unseeded `--deal` draws a different (equally valid) distribution than before
the rename. To reproduce a pre-rename plan exactly, pass the old seed
explicitly: `--seed bind`.