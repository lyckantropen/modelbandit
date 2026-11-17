from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
# --- The output contract (spec #75): one printer, locked verdict strings ----
# Every full-sentence stop follows the one `blocked: <reason>` pattern and is
# emitted by _print_verdict and nowhere else, so the locked vocabulary cannot
# drift back through hand-rolled prints. The strings are pinned at the CLI
# seam on both faces: the printed stops and the `--json` values (outcome,
# verdict, reason) carry the same words.

# The pre-flight's default-deny verdict: an id outside every Route kind names
# no serving, so no zone, Exposure or policy label can speak for it. The same
# words are the reason the machine face carries.
UNKNOWN_SERVING_NAMESPACE = "unknown serving namespace"

# The locked stops.
STOP_FREE_USE_ZONE = "blocked: free-use zone"
STOP_UNKNOWN_SERVING_NAMESPACE = f"blocked: {UNKNOWN_SERVING_NAMESPACE}"
STOP_NO_ELIGIBLE_LOCAL_CANDIDATE = "blocked: no eligible local candidate"
STOP_NO_CANDIDATE_ADMITTED = "blocked: no candidate admitted"
STOP_NO_RANKED_CANDIDATES = "blocked: no ranked candidates"


def _print_verdict(verdict: str, *, zone: Zone | None = None,
                   model: str | None = None, reason: str | None = None,
                   rule: str | None = None) -> None:
    """Print one verdict with the verdict lines it owns.

    The one printer for the output contract: `verdict` is the verdict line
    itself — a full-sentence stop from the locked vocabulary above (the
    `blocked: <reason>` pattern) or the Secrets gate's outcome verdict — and
    the remaining arguments name the verdict lines that belong to it: the
    zone decided (`zone: <label>`), the model judged (`model: <id>`), the
    rule that tripped (`rule: <name>`) and the reason (`reason: <text>`).
    """
    print(verdict)
    if zone is not None:
        print(f"zone: {zone_label(zone)}")
    if model is not None:
        print(f"model: {model}")
    if rule is not None:
        print(f"rule: {rule}")
    if reason is not None:
        print(f"reason: {reason}")


def closed_place(sources, zones, *, environ=None, run=None) -> Zone | None:
    """The first named source whose place would refuse a remote free route.

    Provenance is the caller's own list of where the material came from
    (`--outside-file`), and it resolves the way a run resolves its working
    folder: the stricter of the source's folder and the repository it came
    from, so a source in a worktree carries the posture of the content it
    holds. The closed-path question is asked through the one zone predicate
    - the same ask the pre-flight block, the source filter and the Zone gate
    make - never by re-deriving the predicate here.
    """
    probe = candidate_for("provenance/model:free", {})
    for source in sources:
        folder = source if os.path.isdir(source) else os.path.dirname(source)
        zone = effective_zone(folder or os.curdir, zones=zones, run=run,
                              environ=environ)
        if zone_prohibition(zone.posture, probe) is not None:
            return zone
    return None


def run_secrets_check(*, working_dir: str | None = None,
                      material: str | None = None,
                      outside_files=(),
                      as_json: bool = False) -> int:
    """Print the Secrets gate's verdict for one shape's material.

    Material is read from stdin; the verdict and the rule that tripped it
    are printed. Every verdict exits 0 — safe, sensitive, not certified, or
    blocked on provenance — and the printed lines say which (exit contract
    v2, ADR-0004); 4 is a rules/config error and 2 a usage error. A shape
    with no material given cannot be certified — silence is never read as
    safe.

    Material questions only (the mode split, spec #75): the built-in rules
    over the given material, plus outside-file provenance against closed
    paths. Model-and-zone questions are the pre-flight's alone
    (`--assert-allowed`); the check reads no policy and runs no zone block.
    The zone of a provenance block is named; the material never is. With
    `as_json`, one JSON object replaces the lines (mode, ok, verdict,
    outcome, zone, reason, rule); the `outcome` values are the printed
    verdict words (safe / sensitive / not certified / blocked), and the
    blocked verdict is the locked `blocked: free-use zone` stop like every
    full-sentence stop.
    """
    if material is None:
        try:
            material = sys.stdin.read()
        except Exception:
            material = ""
    root = resolve_working_root(working_dir)
    path_base = os.path.abspath(working_dir or os.getcwd())
    outside_paths = [path if os.path.isabs(path)
                     else os.path.join(path_base, path)
                     for path in outside_files]
    try:
        zones = load_zones()
    except SystemExit as exc:
        print(f"secrets gate: rules/config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR
    zone = effective_zone(path_base, zones=zones)
    if not as_json:
        print(f"zone: {zone_label(zone)}")
    blocked, reason = None, None
    if outside_paths:
        blocked = closed_place(outside_paths, zones)
        if blocked is not None:
            reason = "material provenance from this zone"
    if reason is not None:
        # A provenance block is a verdict, not a failure: exit 0, the lines
        # say blocked (v2). The zone is named; the material never is.
        if as_json:
            emit_json({"mode": "check-secrets", "ok": True,
                       "outcome": "blocked", "verdict": False,
                       "zone": zone_payload(blocked),
                       "reason": reason, "rule": None})
        else:
            _print_verdict(STOP_FREE_USE_ZONE, zone=blocked, reason=reason)
        return 0
    if not isinstance(material, str) or not material.strip():
        if as_json:
            emit_json({"mode": "check-secrets", "ok": True,
                       "outcome": "not certified", "verdict": False,
                       "zone": zone_payload(zone),
                       "reason": "no material given", "rule": None})
        else:
            _print_verdict("secrets gate: not certified (no material given)")
        return 0
    sensitive, rule = secrets_check(material, root=root,
                                    outside_files=outside_paths)
    if sensitive:
        if as_json:
            emit_json({"mode": "check-secrets", "ok": True,
                       "outcome": "sensitive", "verdict": False,
                       "zone": zone_payload(zone),
                       "reason": None, "rule": rule})
        else:
            _print_verdict("secrets gate: sensitive", rule=rule)
    elif as_json:
        emit_json({"mode": "check-secrets", "ok": True,
                   "outcome": "safe", "verdict": True,
                   "zone": zone_payload(zone),
                   "reason": None, "rule": None})
    else:
        _print_verdict("secrets gate: safe")
    return 0


def run_zones_writer(*, payload: str | None = None) -> int:
    """Validate a zones proposal and write the machine's file.

    JSON comes in on stdin; zones are a whole-file declaration, so the
    submitted config goes through `validate_zones` **before** anything is
    written. Invalid config refuses with status 4 naming the offending entry
    and writes nothing: a pre-existing `zones.json` is left byte-identical.
    A valid config replaces the file atomically (temp file in the same
    directory, then `os.replace`), so a reader never sees a half-written
    zones file, and the path written is printed for the user's review. The
    writer is dumb: the schema is the bare opt-out list, and nothing beyond
    validation and the atomic write happens here.
    """
    if payload is None:
        try:
            payload = sys.stdin.read()
        except Exception as exc:
            print(f"zones writer: rules/config error (cannot read "
                  f"--write-zones input: {exc})", file=sys.stderr)
            return RULES_CONFIG_ERROR
    try:
        submitted = json.loads(payload)
    except (TypeError, ValueError):
        print("zones writer: rules/config error "
              "(invalid JSON for --write-zones)", file=sys.stderr)
        return RULES_CONFIG_ERROR
    try:
        validated = validate_zones(submitted, source="--write-zones input")
    except SystemExit as exc:
        print(f"zones writer: rules/config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR

    path = zones_path()
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=directory,
                                         prefix=ZONES_FILE + ".",
                                         suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as f:
            json.dump({ZONES_KEY: validated}, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(temp_path, path)
    except BaseException:
        # Never leave a half-written temp beside (or instead of) the file.
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
    print(f"zones: {path}")
    return 0


