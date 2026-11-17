from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
# --- Local roster ----------------------------------------------------------
# The author-owned record of judgment about this machine's local models —
# the Capability band (domains handled, Difficulty ceiling, context-demand
# ceiling) and prose, keyed by the harness's own model id — and only that
# (GLOSSARY, Local roster). Existence, ids and serving facts belong to the
# harness; the roster never restates them. It lives beside zones.json:
# machine-global, uncommitted, hand-maintained (ADR-0009).
ROSTER_FILE = "local-roster.json"
ROSTER_VERSION = 1
# The file's two top-level sections: an unknown key is a config error the
# way the plan catalog's unknown entry keys are — read by nobody, believed
# by somebody.
ROSTER_KEYS = ("version", "entries")
# An entry's three fields: band + prose is the whole judgment (spec #66,
# "kept thin"), provenance is the exporter's optional stamp (ADR-0009).
# Anything else — a stray `context_length`, a serving fact — would be a
# catalog claim in a judgment file, refused loudly like the plan catalog's
# unknown keys.
ROSTER_ENTRY_KEYS = ("band", "prose", "provenance")
ROSTER_BAND_KEYS = ("domains", "difficulty", "context_demand")
# The domain names a band may state: the modelbandit domain vocabulary
# spelled out, so a typo stops the run instead of silently never matching
# a ticket (understating a band costs reach; a typo would cost it all
# without a word).
ROSTER_DOMAINS = ("research", "writing", "coding", "orchestration", "ops")


def roster_path(*, environ=None) -> str:
    """`local-roster.json` under the machine's config root — the same
    directory as zones.json ($XDG_CONFIG_HOME/modelbandit/, else
    ~/.config/modelbandit/), honouring the environment it is given."""
    env = os.environ if environ is None else environ
    base = (env.get("XDG_CONFIG_HOME")
            or os.path.join(expand_path("~", environ=env), ".config"))
    return os.path.join(base, ZONES_CONFIG_DIR, ROSTER_FILE)


def load_local_roster(*, path: str | None = None, environ=None) -> dict:
    """Validate the Local roster at the config boundary: its entries, or an
    empty roster when the file is absent.

    Loud in the style of `load_free_models`: an unknown key or a bad type
    stops the run naming the entry — never a silent default, because a band
    the reader guessed is a judgment nobody made. A missing file is absent
    setup (the harness listing, not the roster, says what exists). The keys
    are the harness's own model ids: a key outside the harness's local
    namespace is refused here, so a roster entry can never speak for a
    remote serving — judgment binds only the local row (ADR-0005).
    """
    roster = path if path is not None else roster_path(environ=environ)
    if not os.path.exists(roster):
        return {}
    try:
        with open(roster, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise SystemExit(
            f"cannot read local roster file {roster}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"local roster file {roster} must be a JSON object")
    for key in data:
        if key not in ROSTER_KEYS:
            raise SystemExit(
                f"local roster: unknown top-level key '{key}' "
                f"(expected {', '.join(ROSTER_KEYS)})")
    if not _is_plain_int(data.get("version")) \
            or data["version"] != ROSTER_VERSION:
        raise SystemExit(f"local roster: version must be {ROSTER_VERSION} "
                         f"(got {data.get('version')!r})")
    if "entries" not in data:
        raise SystemExit("local roster missing required key: entries")
    entries = data["entries"]
    if not isinstance(entries, dict):
        raise SystemExit("local roster entries must be an object")
    for mid in entries:
        if not is_harness_local_id(mid):
            raise SystemExit(
                f"local roster entries.{mid}: key must be a harness model "
                f"id ({HARNESS_LOCAL_NAMESPACE}<model>), exactly as the "
                f"harness invokes it")
        entry = entries[mid]
        where = f"entries.{mid}"
        if not isinstance(entry, dict):
            raise SystemExit(f"local roster {where} must be an object")
        for key in entry:
            if key not in ROSTER_ENTRY_KEYS:
                raise SystemExit(
                    f"local roster {where}: unknown key '{key}' "
                    f"(expected {', '.join(ROSTER_ENTRY_KEYS)})")
        if "band" not in entry:
            raise SystemExit(f"local roster missing required key: "
                             f"{where}.band")
        band = entry["band"]
        if not isinstance(band, dict):
            raise SystemExit(f"local roster {where}.band must be an object")
        for key in band:
            if key not in ROSTER_BAND_KEYS:
                raise SystemExit(
                    f"local roster {where}.band: unknown key '{key}' "
                    f"(expected {', '.join(ROSTER_BAND_KEYS)})")
        for field in ROSTER_BAND_KEYS:
            if field not in band:
                raise SystemExit(
                    f"local roster missing required key: {where}.band.{field}")
        domains = band["domains"]
        if not isinstance(domains, list) \
                or not all(isinstance(name, str) for name in domains):
            raise SystemExit(f"local roster {where}.band.domains must be a "
                             f"list of domain names")
        for name in domains:
            if name not in ROSTER_DOMAINS:
                raise SystemExit(
                    f"local roster {where}.band.domains: unknown domain "
                    f"'{name}' (known: {', '.join(ROSTER_DOMAINS)})")
        difficulty = band["difficulty"]
        if difficulty not in INTENTS:
            raise SystemExit(
                f"local roster {where}.band.difficulty must be one of "
                f"{'|'.join(INTENTS)} (got {difficulty!r})")
        demand = band["context_demand"]
        if not _is_plain_int(demand) or demand <= 0:
            raise SystemExit(f"local roster {where}.band.context_demand "
                             f"must be a positive integer")
        if "prose" not in entry:
            raise SystemExit(
                f"local roster missing required key: {where}.prose")
        prose = entry["prose"]
        if not isinstance(prose, str) or not prose.strip():
            raise SystemExit(f"local roster {where}.prose must be a "
                             f"non-empty string")
        if "provenance" in entry and not isinstance(entry["provenance"],
                                                    dict):
            raise SystemExit(f"local roster {where}.provenance must be an "
                             f"object")
    return entries


def expand_path(text: str, *, environ=None) -> str:
    """`~` and environment variables, against the environment it is given."""
    env = os.environ if environ is None else environ
    if text == "~" or text.startswith(("~/", "~\\")):
        home = env.get("HOME") or env.get("USERPROFILE") or os.path.expanduser("~")
        text = home + text[1:]
    return _ENV_VAR.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)),
                        text)


def spelled_path(text: str, *, environ=None) -> str:
    """The path as spelled: `~` and variables expanded, absolute, and
    case-folded where the platform folds it — links left alone, so the
    spelling can be told apart from the place the path reaches."""
    return os.path.normcase(
        os.path.abspath(os.path.normpath(expand_path(text, environ=environ))))


def display_path(text: str, *, environ=None) -> str:
    """The place a path reaches: `~` and variables expanded, links resolved
    to the real filesystem place, the platform's own case kept. Strict
    resolution is off: a path that does not exist yet - a zone declared ahead
    of its folder - resolves to its written form and still compares.
    """
    return os.path.realpath(
        os.path.abspath(os.path.normpath(expand_path(text, environ=environ))),
        strict=False)


def compare_path(text: str, *, environ=None) -> str:
    """A path normalised for comparison on this platform: `~` and variables
    expanded, links resolved to the place the path reaches, absolute, and
    case-folded where the platform folds it. A zone is the place a path
    reaches, never the string it is spelled with."""
    return os.path.normcase(display_path(text, environ=environ))


def validate_zones(payload, *, source: str = ZONES_FILE, environ=None) -> list:
    """The zones file's contents, validated: the paths it declares closed.

    A bare list is the whole schema — no per-entry posture, no top-level
    `default` (ADR-0010). A payload still carrying either is refused with a
    corrective message showing the one-line form, never migrated: no
    compatibility shim exists. Two entries naming the same normalised path
    stop loudly: the declaration is a set, and a repeat would name nothing.
    """
    if not isinstance(payload, dict):
        raise SystemExit(f"{source} must be a JSON object: {ZONES_FORM} — "
                         "a bare list of the paths declared closed")
    unknown = sorted(set(payload) - {ZONES_KEY})
    if unknown:
        raise SystemExit(f"unknown key(s) in {source}: {', '.join(unknown)}; "
                         f"the zones file is a bare opt-out list now — write "
                         f"{ZONES_FORM} (closed paths only, no default key "
                         "and no per-entry posture)")
    entries = payload.get(ZONES_KEY, [])
    if not isinstance(entries, list):
        raise SystemExit(f"zones in {source} must be a list of paths: "
                         f"{ZONES_FORM}")
    paths = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(entries, 1):
        where = f"zone #{index} in {source}"
        if isinstance(entry, dict):
            raise SystemExit(
                f"{where} is {json.dumps(entry, ensure_ascii=False)} — entries "
                f"are bare closed paths now, so write {ZONES_FORM} instead")
        if not isinstance(entry, str) or not entry.strip():
            raise SystemExit(f"{where} must be a non-empty path string: "
                             f"{ZONES_FORM}")
        normalised = compare_path(entry, environ=environ)
        if normalised in seen:
            raise SystemExit(f"zone #{index} in {source} duplicates zone "
                             f"#{seen[normalised]} ({entry})")
        seen[normalised] = index
        paths.append(entry)
    return paths


def load_zones(path: str | None = None, *, environ=None) -> list:
    """The machine's closed declarations, validated. A missing file declares
    nothing — every path is open (ADR-0010)."""
    path = zones_path(environ=environ) if path is None else path
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"cannot read zones file {path}: {exc}") from None
    return validate_zones(payload, source=path, environ=environ)


def _covers(zone_path: str, folder: str) -> bool:
    """Whether a normalised zone path covers a normalised folder path."""
    return (folder == zone_path
            or folder.startswith(zone_path.rstrip(os.sep) + os.sep))


def resolve_zone(folder: str, zones, *, environ=None) -> Zone:
    """The zone governing `folder`: the longest declared path that covers it,
    else open. A declared path may name the folder exactly.

    Both sides compare the place the path reaches - links resolved - so a
    junction or symlink is judged by the content it leads to. When a link
    moved the judgement, the zone carries the resolved place for the header:
    the declaration itself spells one place and reaches another, or the
    working folder does while the place it reaches is not the declared path.
    """
    target = compare_path(folder, environ=environ)
    spelled = spelled_path(folder, environ=environ)
    place = display_path(folder, environ=environ)
    best = None
    for declared_path in zones:
        declared = compare_path(declared_path, environ=environ)
        if _covers(declared, target) and (best is None
                                          or len(declared) >= len(best[0])):
            best = (declared, declared_path)
    if best is None:
        return Zone(path=None, posture="open", place=place,
                    resolved=place if spelled != target else None)
    declared_spelled = spelled_path(best[1], environ=environ)
    moved = (declared_spelled != best[0]
             or (spelled != target
                 and os.path.normcase(place) != declared_spelled))
    return Zone(path=best[1], posture="closed", place=place,
                resolved=place if moved else None)


def _under_modules(common: str) -> bool:
    """Whether a git common dir is a submodule's, under a `.git/modules`
    directory — a path belonging to neither the submodule nor the
    superproject."""
    parts = common.split(os.sep)
    return any(parts[i] == ".git" and parts[i + 1] == "modules"
               for i in range(len(parts) - 1))


def _module_origin(common: str, root: str, run) -> str | None:
    """The submodule working tree a `.git/modules` git dir serves.

    `core.worktree` in the module's config names its working tree, relative
    to the git dir — the same answer whether git is asked from the module's
    own checkout or from a linked worktree of it. Without that setting,
    `--show-toplevel` answers for the checkout itself; nothing answerable
    means no origin, never the bogus `.git/modules` path.
    """
    try:
        worktree = str(run(["config", "core.worktree"]) or "").strip()
    except Exception:
        worktree = ""
    if worktree:
        return os.path.normpath(os.path.join(common, worktree))
    try:
        top = str(run(["rev-parse", "--show-toplevel"]) or "").strip()
    except Exception:
        return None
    if not top:
        return None
    return os.path.normpath(top if os.path.isabs(top)
                            else os.path.join(root, top))


def git_origin(root: str, *, run=None) -> str | None:
    """The repository a folder belongs to, from its shared `.git` directory.

    `git rev-parse --git-common-dir` reports the main worktree's `.git` for a
    linked worktree, so a ticket worktree resolves to the repository it came
    from rather than to where it happens to live. A submodule's git dir lives
    under the superproject's `.git/modules/<name>`, which belongs to neither
    repository, so there the origin is the submodule's own working tree — the
    repository whose content the folder holds. Git missing, failing or
    reporting nothing usable answers None — a run then carries only its
    working folder's zone.
    """
    run = _run_git(root) if run is None else run
    if run is None:
        return None
    try:
        common = run(["rev-parse", "--git-common-dir"])
    except Exception:
        return None
    common = str(common or "").strip()
    if not common:
        return None
    if not os.path.isabs(common):
        common = os.path.join(root, common)
    common = os.path.normpath(common)
    if _under_modules(common):
        return _module_origin(common, root, run)
    origin = os.path.dirname(common)
    if not origin or not os.path.dirname(origin):
        return None
    return origin


def effective_zone(folder: str | None = None, *, zones=None,
                   run=None, environ=None) -> Zone:
    """The zone a run works under: the stricter of the working folder's and
    its origin repository's declaration, so a worktree carries the posture of
    the content it holds — one closed declaration covers the repository's
    worktrees (ADR-0010). The zone that decided it answers for it."""
    folder = folder or os.getcwd()
    zones = load_zones(environ=environ) if zones is None else zones
    here = resolve_zone(folder, zones, environ=environ)
    origin = git_origin(folder, run=run)
    if origin is None or compare_path(origin, environ=environ) \
            == compare_path(folder, environ=environ):
        return here
    there = resolve_zone(origin, zones, environ=environ)
    return there if there.posture == "closed" and here.posture == "open" \
        else here


def load_policy_file(path: str | None) -> dict:
    """The policy read once, as UTF-8 JSON, by every entry point.

    The ranking run, the policy check, the pre-flight and the secrets check
    all decode this file the same way: explicitly UTF-8, never the console's
    locale codec — prose carrying non-ASCII must read the same everywhere.
    A missing file is an empty policy (the ranking path then reports the
    required keys it misses); a file that cannot be decoded or parsed is a
    policy/config error naming the file, never a mangled read and never an
    uncaught traceback.
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            policy = json.load(f)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"cannot read policy file {path}: {exc}") from None
    if not isinstance(policy, dict):
        raise SystemExit(f"policy file {path} must be a JSON object")
    return policy


def policy_facts(path: str | None) -> dict:
    """The policy's Exposure facts when the file exists, else none.

    The pre-flight and the secrets check read the local policy for its
    `exposure` overrides, its `free_models` catalog and its `plans` catalog
    when it is there, and work without it: a missing file is not an error,
    so the defaults answer (a ':free' or 'opencode/*' route exposed, a
    paid route no-retention). No board, no classification fetch, no network.
    """
    policy = load_policy_file(path)
    policy["free_models"] = load_free_models(policy)
    policy["plans"] = load_plans(policy)
    load_exposure_overrides(policy)
    return policy


