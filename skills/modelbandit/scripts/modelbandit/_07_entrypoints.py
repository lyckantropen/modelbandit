from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
def zone_block(model_id: str, zone: Zone, *, policy: dict | None = None,
               material_sensitive: bool = False,
               loopback: bool = True) -> str | None:
    """The effective zone's reason this model may not serve here, or None.

    The whole pre-flight rule, and the pre-flight's caller of the one zone
    predicate: the candidate facts are the policy's Exposure facts plus the
    serving endpoint's loopback status (an empty policy and an undeclared
    endpoint keep the safe defaults). Blocked means a prohibition the zone
    states outright — a remote free route in a closed place (the predicate's
    clause), a non-local route on a Sensitive shape (the Exposure clause,
    ADR 0008: only Exposure `local` serves Sensitive work) — never a
    Footprint, catalog or quota exclusion. The Exposure clause answers in
    words (`only Exposure local may serve a Sensitive shape (<class>)`); the
    `exposed (<class>)` mark itself stays the ranked table's own.

    The candidate is judged by its serving identity alone: localness is a
    serving fact, never a catalogue claim, and this guard observes no serving
    — so a policy label cannot make a remote id (`opencode/*`, `:free`) local
    here, and a remote Free route is refused in a closed place whatever the
    catalog says. The harness's `lmstudio/*` namespace classifies local, but
    `local` still resolves only for a loopback endpoint: the pre-flight
    reads the harness's declared endpoint (a file read, still no serving
    observed) and a non-loopback serving fails closed as exposed.
    """
    shape = Shape(material_sensitive=material_sensitive, posture=zone.posture)
    model_id = norm_id(model_id)
    policy = policy or {}
    candidate = candidate_for(model_id, policy, loopback=loopback)
    reason = zone_prohibition(shape.posture, candidate)
    if reason is None:
        # The Exposure clause answers in words here: the `exposed (<class>)`
        # mark stays the ranked table's own, and the pre-flight states the
        # clause (ADR 0008: only Exposure `local` serves Sensitive work)
        # with the route's class named for the human.
        mark = exposed_prohibition(shape, candidate)
        if mark is not None:
            reason = (f"only Exposure local may serve a Sensitive shape "
                      f"({candidate.exposure})")
    return reason


def _print_preflight_posture(zone: Zone, *, plain: bool,
                             restated: bool) -> None:
    """The effective zone, then the shape the pre-flight judges the id as."""
    print(f"zone: {zone_label(zone)}")
    if plain:
        print("shape: plain (via --plain)")
    elif restated:
        print("shape: sensitive (via --sensitive)")
    else:
        print("shape: sensitive (assumed)")


def run_assert_allowed(*, model: str, working_dir: str | None = None,
                       policy_path: str | None = None,
                       plain: bool = False, restated: bool = False,
                       as_json: bool = False) -> int:
    """Pre-flight: may this model serve in this folder's zone?

    The dispatch contract fails closed: an unstated shape is **Sensitive**,
    and the output states the assumption (`shape: sensitive (assumed)`) —
    only a route whose Exposure is `local` is allowed by default (ADR 0008:
    Sensitive material leaves the machine on any remote route, no-retention
    alike), never allowed because nobody said otherwise. A caller that knows the material is not
    Sensitive must say so explicitly (`--plain`, printed as
    `shape: plain (via --plain)`); `--sensitive` restates the default and is
    accepted with the same verdict.

    Prints the effective posture (`zone: <path> (open|closed)`) and either the
    model as allowed (`allowed: <id>`) or a free-use zone block — both
    verdicts exit 0 and the lines say which (exit contract v2, ADR-0004:
    launch only on `allowed`; the status says the tool ran). An id outside
    every Route kind is refused first and on its own terms
    (`blocked: unknown serving namespace`, the model named): kind is decided
    from the id alone, so an unclassifiable id is blocked in an open zone
    exactly as in a closed one, and no policy prefix map grants it one. The
    zone is named; the shape's content never is. No policy file,
    classification fetch or network is needed, so an orchestrator can refuse
    to launch a model the plan should not have produced before anything is
    fetched. With `as_json`, one JSON object replaces the lines (mode, ok,
    allowed, model, shape, zone, reason).
    """
    # One policy default for every entry point (run_status spells it the
    # same way): None means "not stated", never "no policy" — the skill's
    # own policy.json answers.
    policy_path = policy_path or DEFAULT_POLICY
    try:
        zone = effective_zone(working_dir)
        facts = policy_facts(policy_path)
    except SystemExit as exc:
        print(f"pre-flight: policy/config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR
    model_id = norm_id(model)
    if classify_route(model_id) is None:
        # Route kind is decided from the id alone, before the zone: an
        # id outside every kind has no serving fact, so the pre-flight refuses
        # it in an open zone exactly as in a closed one. The block is a
        # verdict, not a failure (ADR-0004): the lines carry it, the status
        # only says the tool ran.
        if as_json:
            emit_json({"mode": "assert-allowed", "ok": True,
                       "allowed": False,
                       "model": model_id,
                       "shape": "plain" if plain else "sensitive",
                       "zone": zone_payload(zone),
                       "reason": UNKNOWN_SERVING_NAMESPACE})
            return 0
        _print_preflight_posture(zone, plain=plain, restated=restated)
        _print_verdict(STOP_UNKNOWN_SERVING_NAMESPACE, model=model_id)
        return 0
    reason = zone_block(model_id, zone, policy=facts,
                        material_sensitive=not plain,
                        loopback=loopback_endpoint(harness_serving_endpoint()))
    if as_json:
        emit_json({"mode": "assert-allowed", "ok": True,
                   "allowed": reason is None,
                   "model": model_id,
                   "shape": "plain" if plain else "sensitive",
                   "zone": zone_payload(zone),
                   "reason": reason})
        return 0
    _print_preflight_posture(zone, plain=plain, restated=restated)
    if reason is not None:
        # A block is a verdict, not a failure: exit 0, the lines say blocked.
        _print_verdict(STOP_FREE_USE_ZONE, model=model_id, reason=reason)
        return 0
    _print_verdict(f"allowed: {model_id}")
    return 0


def load_policy_bundle(policy_path: str | None) -> dict:
    """The one policy load every entry point shares: the file read as
    UTF-8, the free catalog, the plan catalog, and the exposure overrides.
    Validation and unpacking stay with each caller — it knows what it can
    tolerate (a missing file is absent setup for the status report, an
    existing one must be one the ranking trusts) and maps every failure to
    status 4, never a traceback or a Secrets verdict."""
    policy = load_policy_file(policy_path)
    policy["free_models"] = load_free_models(policy)
    policy["plans"] = load_plans(policy)
    load_exposure_overrides(policy)
    return policy


# The pre-flight and the secrets check ask this same load under the older name.
policy_facts = load_policy_bundle


def run_status(*, working_dir: str | None = None,
               policy_path: str | None = None, as_json: bool = False) -> int:
    """The offline setup report: zone, zones file, built-in secrets rules,
    policy age.

    The machine-readable companion to the README Setup section — read-only
    and fully offline: no endpoint fetch, no classification, no quota. The
    secrets surface is the built-in rules now in force — a note, never a
    file: the project rules file is gone (spec #75). `--working-dir`
    judges the folder the way the pre-flight does, and the zones path is
    spelled the way the run header spells it.

    Exit status: 0 whenever the zones file is absent — a missing zones file
    is the documented default, not an answer the status must carry; 4 only
    when a file that exists fails validation (zones or policy), named on
    stderr. With `as_json`, one JSON object replaces the lines (mode, ok,
    zone, zones_file, secrets, policy).
    """
    policy_path = policy_path or DEFAULT_POLICY
    try:
        zone = effective_zone(working_dir)
        zones_present = os.path.exists(zones_path())
        # A missing file is absent setup (age `unknown`), not a failure;
        # only an existing policy must be one the ranking would trust.
        policy_exists = os.path.exists(policy_path)
        policy = load_policy_bundle(policy_path)
        if policy_exists:
            load_policy_config(policy)
    except SystemExit as exc:
        print(f"status: config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR
    label = zones_file_label()
    age = policy_age_days(policy_path)
    if as_json:
        emit_json({"mode": "status", "ok": True,
                   "zone": zone_payload(zone),
                   "zones_file": {"path": label, "present": zones_present},
                   "secrets": {"rules": "built-in"},
                   "policy": {"path": policy_path, "age_days": age}})
        return 0
    print(f"zone: {zone_label(zone)}")
    if zones_present:
        print(f"zones file: present ({label})")
    # An absent file declares nothing, so the zone line above already says
    # everything there is to say: no warning and no nag on a first run
    # (ADR-0010).
    # The built-in rules are the whole secrets surface now in force — the
    # report states them instead of a file it would have to find (spec #75).
    print("secrets: built-in rules apply")
    age_txt = f"{age}d old" if age is not None else "unknown"
    print(f"policy: {policy_path} — {age_txt}")
    return 0


