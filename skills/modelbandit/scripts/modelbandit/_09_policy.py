from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
def longest_prefix_match(mid: str, values: dict) -> tuple[str, object] | None:
    """Return the value for the longest key that prefixes ``mid``.

    A tie retains mapping iteration order, matching the prior lookup behavior.
    """
    best = None
    for key, value in values.items():
        if mid.startswith(key) and (best is None or len(key) > len(best[0])):
            best = (key, value)
    return best


def hint_for(mid: str, hints: dict) -> str | None:
    """Entries are structured ({note, fit, evidence}) or plain notes."""
    match = longest_prefix_match(mid, hints)
    if match is None:
        return None
    entry = match[1]
    return entry.get("note", "") if isinstance(entry, dict) else entry


def domain_weights(hints: dict, domain: str, factors: dict) -> dict[str, float]:
    """Derive one domain's affinity table from structured hints.

    A hint carries fit ({domain: favor|avoid}) and evidence
    (validated|suspected); the multiplier is factors[f"{fit}_{evidence}"].
    Nothing is stored per model — hints without a fit for this domain are
    neutral and stay out of the table (missing fit = neutral)."""
    out = {}
    for key, entry in hints.items():
        if not isinstance(entry, dict):
            continue
        fit = entry.get("fit", {}).get(domain)
        if fit not in ("favor", "avoid"):
            continue
        evidence = entry.get("evidence", "suspected")
        out[key] = float(factors[f"{fit}_{evidence}"])
    return out


@dataclasses.dataclass(frozen=True)
class DealParameters:
    blend_weight: float
    top_k: int
    seed: str
    tickets: int
    fit_adjusted_task_scores: dict | None = None
    admitted: frozenset | None = None
    # The standing favor (issue #69): {mid -> multiplier} folded into the
    # draw's pref beside the hint affinity — keyed by the caller's local
    # rows, so only a row the admission seam already passed (band gate
    # included) can be favored. None means no favor; the draw is the
    # affinity table alone.
    favor: dict | None = None


@dataclasses.dataclass(frozen=True)
class PolicyConfig:
    alpha: float
    beta: float
    thresholds: dict
    factors: dict
    blend_weight: float
    eligibility_top_k: int
    headroom: float = 2.0
    margin: float = 0.5
    free_risk: float = DEFAULT_FREE_RISK
    free_share_inheritance: float = DEFAULT_FREE_SHARE_INHERITANCE
    free_quota_reserve: int = DEFAULT_FREE_QUOTA_RESERVE


def load_policy_config(policy: dict) -> PolicyConfig:
    """Unpack scoring and deal policy values once for all policy paths."""
    def required(mapping: dict, key: str, path: str):
        if not isinstance(mapping, dict) or key not in mapping:
            raise SystemExit(f"policy missing required key: {path}")
        return mapping[key]

    scoring = required(policy, "scoring", "scoring")
    affinity = required(policy, "affinity", "affinity")
    scoring_thresholds = required(scoring, "thresholds", "scoring.thresholds")
    factor_values = required(affinity, "factors", "affinity.factors")
    threshold_keys = ("top1_min", "top1_max", "top2_max")
    factor_keys = ("favor_validated", "favor_suspected",
                   "avoid_validated", "avoid_suspected")
    thresholds = {key: float(required(scoring_thresholds, key,
                                      f"scoring.thresholds.{key}"))
                  for key in threshold_keys}
    factors = {key: float(required(factor_values, key, f"affinity.factors.{key}"))
               for key in factor_keys}
    context_values = policy.get("context_gate", {})
    if not isinstance(context_values, dict):
        raise SystemExit("policy context_gate must be an object")

    def context_value(key: str, default: float) -> float:
        value = context_values.get(key, default)
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise SystemExit(f"policy context_gate.{key} must be a number") from None
        if not math.isfinite(value):
            raise SystemExit(f"policy context_gate.{key} must be finite")
        return value

    headroom = context_value("headroom", 2.0)
    margin = context_value("margin", 0.5)
    if headroom < 1.0:
        raise SystemExit("policy context_gate.headroom must be at least 1")
    if not 0.0 < margin <= 1.0:
        raise SystemExit("policy context_gate.margin must be greater than 0 and at most 1")
    free_risk = scoring.get("free_risk", DEFAULT_FREE_RISK)
    try:
        free_risk = float(free_risk)
    except (TypeError, ValueError, OverflowError):
        raise SystemExit("policy scoring.free_risk must be a number") from None
    if not math.isfinite(free_risk) or not 0.0 < free_risk < 1.0:
        raise SystemExit("policy scoring.free_risk must be strictly between 0 and 1")
    inheritance = scoring.get("free_share_inheritance",
                              DEFAULT_FREE_SHARE_INHERITANCE)
    try:
        inheritance = float(inheritance)
    except (TypeError, ValueError, OverflowError):
        raise SystemExit(
            "policy scoring.free_share_inheritance must be a number") from None
    if not math.isfinite(inheritance) or not 0.0 < inheritance <= 1.0:
        raise SystemExit("policy scoring.free_share_inheritance must be "
                         "greater than 0 and at most 1")
    # The reserve is a count of requests held back from planning, so a
    # fractional or negative one is a misconfiguration, not a rounding.
    raw_reserve = scoring.get("free_quota_reserve", DEFAULT_FREE_QUOTA_RESERVE)
    quota_reserve = raw_reserve if _is_plain_int(raw_reserve) else None
    if quota_reserve is None and isinstance(raw_reserve, float) \
            and math.isfinite(raw_reserve) and raw_reserve.is_integer():
        quota_reserve = int(raw_reserve)
    if quota_reserve is None or quota_reserve < 0:
        raise SystemExit("policy scoring.free_quota_reserve must be a "
                         "non-negative integer")
    return PolicyConfig(
        alpha=float(required(scoring, "alpha", "scoring.alpha")),
        beta=float(required(scoring, "beta", "scoring.beta")),
        thresholds=thresholds,
        factors=factors,
        blend_weight=float(required(affinity, "blend_weight",
                                     "affinity.blend_weight")),
        eligibility_top_k=int(required(affinity, "eligibility_top_k",
                                       "affinity.eligibility_top_k")),
        headroom=headroom,
        margin=margin,
        free_risk=free_risk,
        free_share_inheritance=inheritance,
        free_quota_reserve=quota_reserve,
    )


def exposure_contradiction(mid: str, value: str) -> str | None:
    """Why a policy Exposure label contradicts the serving identity, or None.

    Localness is a serving fact, never a catalogue claim: the classifier
    answers the remote serving namespaces remote — the void rule
    (local_label_is_void) says so whatever a policy entry says — so a
    `local` label on one is a contradiction the policy stops loudly,
    naming the entry.
    """
    if value == "local" and local_label_is_void(mid):
        return (f"exposure 'local' contradicts the remote serving identity "
                f"'{mid}' (opencode/*, opencode-go/*, and :free routes are "
                f"remote)")
    return None


def _free_catalog_kind(prefix: str, exposure: str) -> str | None:
    """The Route kind a ``free_models`` entry declares, from its prefix alone.

    Namespace first: ``opencode-go/*`` is a plan serving whatever the entry
    says (plan has its own catalog), ``opencode/*`` is a harness serving, and
    ``lmstudio/*`` is the harness's local serving — a malformed local
    namespace fails closed through the classifier. The ``local`` annotation
    supplies the local serving fact for a prefix no remote namespace claims.
    A bare two-segment OpenRouter prefix is the family the catalog keys a
    ``:free`` route by, so it declares a free-slug serving. A ``:free``
    suffix on any other shape routes through the seam,
    which normalizes and classifies the whole prefix: a two-segment slug
    stays a free-slug serving, while a third segment or a plan namespace
    under the ``openrouter/`` qualifier is refused at load. Anything else
    falls to the classifier, which fails closed on an unknown namespace and
    names the market serving an ``openrouter/`` prefix hides.
    """
    if prefix.startswith("opencode-go/"):
        return "plan"
    if prefix.startswith(HARNESS_LOCAL_NAMESPACE):
        # The harness's local namespace is a serving fact of its own —
        # whatever the entry annotates, an `lmstudio/*` prefix declares a
        # local serving, and a malformed one fails closed through the seam.
        return classify_route(prefix)
    if exposure == "local":
        return "local"
    if prefix.startswith("opencode/"):
        return "harness"
    if prefix.endswith(":free"):
        return classify_route(prefix)
    parts = prefix.split("/")
    if len(parts) == 2 and all(parts):
        return "free-slug"
    return classify_route(prefix)


def load_free_models(policy: dict) -> dict:
    """Validate the curated Free route catalog at the policy boundary.

    A bad window or misspelled Exposure must stop the run: either could make a
    candidate look safer or more capable than the policy says. So must an entry
    whose Route kind is not Free: the hardcoded $0 of a Free record must never
    price a plan or market serving, so such an entry is refused at load with a
    loud config error naming it — nothing half-loaded (ADR-0002, ADR-0005).
    ``summary_ref`` remains optional in policy, but when present it must be a
    usable string.
    """
    catalog = policy.get("free_models", {})
    if not isinstance(catalog, dict):
        raise SystemExit("policy free_models must be an object")
    for prefix, entry in catalog.items():
        path = f"free_models.{prefix}"
        if not isinstance(prefix, str) or not prefix.strip():
            raise SystemExit(f"policy {path}: id-prefix must be a non-empty string")
        if not isinstance(entry, dict):
            raise SystemExit(f"policy {path} must be an object")
        window = entry.get("context_length")
        if not _is_plain_int(window) or window <= 0:
            raise SystemExit(f"policy {path}.context_length must be a positive integer")
        completion_cap = entry.get("max_completion_tokens")
        if (completion_cap is not None
                and (not _is_plain_int(completion_cap)
                     or completion_cap <= 0)):
            raise SystemExit(f"policy {path}.max_completion_tokens must be a positive integer")
        if "exposure" not in entry:
            raise SystemExit(f"policy missing required key: {path}.exposure")
        try:
            known_exposure(prefix, entry["exposure"])
        except SystemExit as exc:
            raise SystemExit(f"policy {path}.exposure: {exc}") from None
        if (contradiction := exposure_contradiction(prefix,
                                                    entry["exposure"])):
            raise SystemExit(f"policy {path}.exposure: {contradiction}")
        kind = _free_catalog_kind(prefix, entry["exposure"])
        if kind not in FREE_KINDS:
            raise SystemExit(
                f"policy {path}: route kind '{kind or 'unknown'}' is not a "
                f"Free route (free-slug, harness, or local); the free "
                f"catalog prices only Free servings")
        summary_ref = entry.get("summary_ref")
        if summary_ref is not None and (not isinstance(summary_ref, str)
                                        or not summary_ref.strip()):
            raise SystemExit(f"policy {path}.summary_ref must be a non-empty string")
    return catalog


# The three Allowance windows a plan entry must state caps for, in ledger
# order: the rolling 5-hour window, the week, the month (GLOSSARY,
# Allowance). The caps are dollar figures, so every one must be a positive
# real number — a zero or a misspelling would let a batch run past the
# plan's boundary unnoticed.
PLAN_CAP_WINDOWS = ("five_hour", "weekly", "monthly")

# The only fields a plans entry may state. An unknown key is a config error:
# a stray `caps` window would silently invent an unauthorized boundary (the
# crossing arithmetic iterates caps.items()), and a non-numeric one would
# surface as a TypeError instead of status 4.
PLAN_ENTRY_FIELDS = ("list_price", "caps", "exposure", "regions",
                     "family_ref")


def _is_finite_number(value) -> bool:
    """A real JSON number: an int or a float, never a bool, never NaN/inf."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def load_plans(policy: dict) -> dict:
    """Validate the plan catalog at the policy boundary.

    The `plans` section is the single source the ledger and the Exposure
    verdicts read a Plan route's facts from: its list price (the Draw's
    basis), its three Allowance window caps, its training/retention class,
    and an optional region opt-in. Each field could make a plan look safer
    or its Allowance look bigger than the policy says, so each refuses the
    load loudly, naming the entry — nothing half-loaded (ADR-0010,
    ADR-0005). An unknown key is refused the same way: `caps` must state
    exactly the three Allowance windows, because a stray window would
    silently invent an unauthorized boundary in the crossing arithmetic,
    and an entry may state only the known plan facts.

    The section is its own catalog: an entry whose id the Route-kind seam
    does not answer `plan` is refused here, while `free_models` keeps
    refusing plan-kind entries in parallel — each catalog prices only the
    servings it owns. A `list_price` of 0 is not bad: it is the zero-Draw,
    free-in-plan serving whose pricing falls back to the pool-cheapest
    basis (ADR-0006), so the price must be non-negative, not positive.

    Every entry also declares its family link: `family_ref`, the Twin's
    Metered serving id. Twins find each other through that declaration
    alone -- vendor prefixes differ per family, so no id shape derives one
    (the declaration is authoritative, never a slug heuristic). The link
    resolves when the Route-kind seam answers `market` for it -- a plan,
    harness, `:free` or unclassifiable id names no Metered row and is
    refused here, naming the entry, so a broken link never half-loads a
    catalog and never reaches resolution as a silent default.
    """
    catalog = policy.get("plans", {})
    if not isinstance(catalog, dict):
        raise SystemExit("policy plans must be an object")
    for mid, entry in catalog.items():
        path = f"plans.{mid}"
        if not isinstance(mid, str) or not mid.strip():
            raise SystemExit(f"policy {path}: id must be a non-empty string")
        if not isinstance(entry, dict):
            raise SystemExit(f"policy {path} must be an object")
        for key in entry:
            if key not in PLAN_ENTRY_FIELDS:
                raise SystemExit(
                    f"policy {path}: unknown key '{key}' (expected "
                    f"{', '.join(PLAN_ENTRY_FIELDS)})")
        kind = classify_route(mid)
        if kind != "plan":
            raise SystemExit(
                f"policy {path}: route kind '{kind or 'unknown'}' is not a "
                f"Plan route (opencode-go/*); the plans catalog prices only "
                f"Plan servings")
        if "list_price" not in entry:
            raise SystemExit(f"policy missing required key: {path}.list_price")
        if not _is_finite_number(entry["list_price"]) \
                or entry["list_price"] < 0:
            raise SystemExit(
                f"policy {path}.list_price must be a non-negative number")
        if "caps" not in entry:
            raise SystemExit(f"policy missing required key: {path}.caps")
        caps = entry["caps"]
        if not isinstance(caps, dict):
            raise SystemExit(f"policy {path}.caps must be an object")
        for window in PLAN_CAP_WINDOWS:
            if window not in caps:
                raise SystemExit(
                    f"policy missing required key: {path}.caps.{window}")
            if not _is_finite_number(caps[window]) or caps[window] <= 0:
                raise SystemExit(
                    f"policy {path}.caps.{window} must be a positive number")
        for window in caps:
            if window not in PLAN_CAP_WINDOWS:
                raise SystemExit(
                    f"policy {path}.caps: unknown window '{window}' "
                    f"(expected {', '.join(PLAN_CAP_WINDOWS)})")
        if "exposure" not in entry:
            raise SystemExit(f"policy missing required key: {path}.exposure")
        try:
            known_exposure(mid, entry["exposure"])
        except SystemExit as exc:
            raise SystemExit(f"policy {path}.exposure: {exc}") from None
        if (contradiction := exposure_contradiction(mid, entry["exposure"])):
            raise SystemExit(f"policy {path}.exposure: {contradiction}")
        regions = entry.get("regions")
        if regions is not None and (
                not isinstance(regions, list)
                or any(not isinstance(region, str) or not region.strip()
                       for region in regions)):
            raise SystemExit(
                f"policy {path}.regions must be a list of non-empty strings")
        if "family_ref" not in entry:
            raise SystemExit(
                f"policy missing required key: {path}.family_ref")
        family_ref = entry["family_ref"]
        if not isinstance(family_ref, str) or not family_ref.strip():
            raise SystemExit(
                f"policy {path}.family_ref must be a non-empty string")
        twin_kind = classify_route(family_ref)
        if twin_kind != "market":
            raise SystemExit(
                f"policy {path}.family_ref '{family_ref}': route kind "
                f"'{twin_kind or 'unknown'}' is not a Metered route "
                f"(market); the family link names the Twin's Metered serving")
    return catalog


def load_exposure_overrides(policy: dict) -> dict:
    """Validate the policy's `exposure` override map at the policy boundary.

    A misspelled class here would widen the gate exactly as a misspelled
    catalog entry would, so it stops the run the same way — loudly, naming
    the prefix, before any candidate is judged by it.
    """
    overrides = policy.get("exposure", {})
    if not isinstance(overrides, dict):
        raise SystemExit("policy exposure must be an object")
    for prefix, value in overrides.items():
        path = f"exposure.{prefix}"
        if not isinstance(prefix, str) or not prefix.strip():
            raise SystemExit(f"policy {path}: id-prefix must be a non-empty string")
        if not isinstance(value, str):
            raise SystemExit(f"policy {path}: exposure must be a string")
        try:
            known_exposure(prefix, value)
        except SystemExit as exc:
            raise SystemExit(f"policy {path}: {exc}") from None
        if contradiction := exposure_contradiction(prefix, value):
            raise SystemExit(f"policy {path}: {contradiction}")
    return overrides


def _free_summary(entry: dict, summaries: dict, mid: str | None = None) -> bool:
    """Whether a Free route has a resolvable explicit or prefix summary."""
    ref = entry.get("summary_ref")
    return ((isinstance(ref, str) and bool(summaries.get(ref)))
            or (mid is not None and bool(hint_for(mid, summaries))))


def _family_share(share: dict, entry: dict, inheritance: float) -> float:
    """A curated Free route's standing: a discount on its family's domain share.

    An ``opencode/*`` or local serving has no leaderboard row of its own; its
    popularity is the family's revealed preference. It inherits only
    ``inheritance`` of that share: the free serving is a limited-time,
    rate-limited surrogate for the family, so it does not carry the family's
    full standing. The family prefix is the summary reference with any trailing
    ``:free`` stripped, so a dated ``X-YYYYMMDD:free`` board row still counts
    toward it. No summary reference means no observable popularity — the
    standing stays zero.
    """
    ref = entry.get("summary_ref")
    if not isinstance(ref, str) or not ref.strip():
        return 0.0
    prefix = ref.removesuffix(":free")
    family = sum(s for key, s in share.items() if key.startswith(prefix))
    return family * inheritance


def _free_model_record(mid: str, entry: dict, source: dict | None = None) -> dict:
    """Build route-specific metadata; never inherit a sibling's paid price."""
    model = dict(source or {})
    model.update({
        "id": mid,
        "context_length": entry["context_length"],
        "pricing": {"prompt": "0", "completion": "0",
                    "input_cache_read": "0"},
    })
    model.setdefault("supported_parameters", [])
    return model


def merge_free_candidates(share: dict, models: dict, free_models: dict,
                          summaries: dict, *,
                          inheritance: float = DEFAULT_FREE_SHARE_INHERITANCE
                          ) -> tuple[dict, dict]:
    """Merge cataloged OpenCode models and ranked :free routes into candidates.

    OpenRouter :free rows retain their own slug even when the API only resolves
    them through a paid family model. Uncataloged or unsummarized ranked Free
    routes stay visible; a missing summary is marked as a Gap and does not keep
    a pool from playing the route. The plans catalog is separate and still
    decides which plan routes exist.
    OpenCode catalog entries are added with a discounted share of their family's
    domain share (the family's revealed preference standing in for a route with
    no board row); their context and Exposure remain curated facts, not inferred
    runtime data.
    """
    merged_share = dict(share)
    merged_models = {mid: dict(model) for mid, model in models.items()}

    for mid in list(merged_share):
        if not is_free_route(mid):
            continue
        match = longest_prefix_match(mid, free_models)
        if match is None:
            continue
        entry = match[1]
        source = merged_models.get(mid)
        if source is None:
            source = merged_models.get(mid.removesuffix(":free"))
        merged_models[mid] = _free_model_record(mid, entry, source)

    for prefix, entry in free_models.items():
        if classify_route(prefix) == "local":
            # A local-kind prefix never stands up its own row here: local
            # candidates exist only where the harness listing says they do
            # (merge_local_candidates), so a catalog entry alone raises none.
            continue
        if (not is_free_route(prefix)
                or not _free_summary(entry, summaries, prefix)):
            continue
        merged_share.setdefault(prefix, 0.0)
        if merged_share[prefix] == 0.0:
            merged_share[prefix] = _family_share(merged_share, entry,
                                                 inheritance)
        merged_models.setdefault(prefix, _free_model_record(prefix, entry))

    return merged_share, merged_models


def merge_local_candidates(share: dict, models: dict, listed, served: dict,
                           free_models: dict, *,
                           inheritance: float = DEFAULT_FREE_SHARE_INHERITANCE
                           ) -> tuple[dict, dict]:
    """Join this run's harness-listed local ids to the curated Free catalog.

    The harness listing is the sole source of existence and identity: an id
    the harness does not list never joins, whatever the probe reports or the
    catalog declares, and what joins is named exactly as the harness
    dispatches it. Each listed id still needs a catalog entry whose Exposure
    is ``local`` to be judged at all; cataloged listed ids remain visible
    even without a summary, but the admission seam requires that summary
    before they can be picked or dealt. The probe's contribution here is one
    narrow fact — the live context window judged by the Context gate — never
    existence: a missing server changes nothing about the candidate set.
    """
    merged_share = dict(share)
    merged_models = {mid: dict(model) for mid, model in models.items()}
    for mid in sorted(listed):
        match = longest_prefix_match(mid, free_models)
        if match is None:
            continue
        entry = match[1]
        if not isinstance(entry, dict) or entry.get("exposure") != "local":
            continue
        merged_share.setdefault(mid, 0.0)
        if merged_share[mid] == 0.0:
            merged_share[mid] = _family_share(merged_share, entry, inheritance)
        record = _free_model_record(mid, entry, served.get(mid))
        live = served.get(mid)
        if isinstance(live, dict) and live.get("context_length") is not None \
                and _is_plain_int(live["context_length"]) \
                and live["context_length"] > 0:
            # The curated window stays the record's policy fact; the window
            # the live serving reports is the capacity the Context gate is
            # judged against, for this invocation only.
            record["served_context_length"] = live["context_length"]
        merged_models[mid] = record
    return merged_share, merged_models


def local_candidate_ids(listed, free_models: dict) -> set[str]:
    """Harness-listed ids matched by a catalog entry whose Exposure is
    ``local`` — the serving fact set the run's local flags read from."""
    return {mid for mid in listed
            if (match := longest_prefix_match(mid, free_models)) is not None
            and isinstance(match[1], dict)
            and match[1].get("exposure") == "local"}


def _plan_model_record(mid: str) -> dict:
    """The minimal record a plan serving carries into the table and the gates.

    A plan serving never resolves in OpenRouter's models list, so the plans
    catalog supplies what the run consumes: the id and the $0 cash price one
    ticket costs within its Allowance. The plan's list price is a Draw basis
    (the cost seam's fact), never a per-1M market price, so no per-1M figure
    is stated here -- the table shows the unknowable columns as `?`/`—`.
    """
    return {"id": mid,
            "pricing": {"prompt": "0", "completion": "0",
                        "input_cache_read": "0"}}


def _family_board_share(share: dict, family: str, local: set[str]) -> float:
    """The family's board share: the largest figure the board reports for its
    full-quality servings.

    Twin rows report one family's traffic, so their sum would count it twice;
    the largest is the closest the board gets to the family's whole. A family
    the board does not name has no share.
    """
    return max((s for mid, s in share.items()
                if mid not in local and family_key(mid) == family
                and classify_route(mid) in _FULL_QUALITY_KINDS), default=0.0)


def merge_plan_candidates(share: dict, models: dict, plans: dict, *,
                          local=()) -> tuple[dict, dict]:
    """Join the validated plans catalog's servings to the candidate set.

    The plan namespace is not an OpenRouter serving, so a plan id never
    resolves in the models list; the catalog is its one surface. Each
    cataloged plan serving joins with the minimal record the table and the
    gates honestly consume (see _plan_model_record) -- no market models-list
    row is invented.

    Popularity is the family's: a family served twice -- its metered twin and
    its plan serving -- divides its board share across both full-quality
    rows, so the family's standing is counted once. A family with one
    full-quality serving keeps its share whole: the plan row is the family
    model at full quality, never a rate-limited surrogate, so no Free-route
    inheritance discount applies. The local serving fact outranks the plan
    shape: an id this machine serves joins as a local row
    (merge_local_candidates), never here.
    """
    merged_share = dict(share)
    merged_models = {mid: dict(model) for mid, model in models.items()}
    local = set(local)
    plan_ids = [mid for mid in plans
                if is_plan_route(mid) and mid not in local]
    if not plan_ids:
        return merged_share, merged_models
    for mid in plan_ids:
        merged_share.setdefault(mid, 0.0)
        merged_models.setdefault(mid, _plan_model_record(mid))
    families = sorted({family for family in map(family_key, plan_ids)
                       if family is not None})
    for family in families:
        rows = [mid for mid in merged_share
                if mid not in local and family_key(mid) == family
                and classify_route(mid) in _FULL_QUALITY_KINDS]
        if not rows:
            continue
        family_share = _family_board_share(merged_share, family, local)
        for mid in rows:
            merged_share[mid] = family_share / len(rows)
    return merged_share, merged_models


def free_candidate_details(mid: str, policy: dict, *, local: bool = False
                           ) -> tuple[int, str] | None:
    """Return the curated window and Exposure for a Free route, if cataloged."""
    if not is_free_route(mid, local=local):
        return None
    match = longest_prefix_match(mid, policy.get("free_models", {}))
    if match is None:
        return None
    entry = match[1]
    if local and entry.get("exposure") != "local":
        return None
    return entry["context_length"], entry["exposure"]


def summary_for_candidate(mid: str, policy: dict) -> str | None:
    """Resolve a Free route's explicit family summary, else its direct summary."""
    match = longest_prefix_match(mid, policy.get("free_models", {}))
    if match is not None and (is_free_route(mid)
                              or match[1].get("exposure") == "local"):
        ref = match[1].get("summary_ref")
        if ref:
            return policy.get("summaries", {}).get(ref)
    return hint_for(mid, policy.get("summaries", {}))


def task_score(share: float, cost: float, alpha: float, beta: float) -> float:
    """share^alpha / cost^beta. cost must already be floored (see
    effective_costs) so Free routes cannot win on division alone."""
    return share ** alpha / cost ** beta


def fit_for(mid: str, fit_map: dict) -> float | None:
    """The task-fit judgment (0-5); None means unscored, with no penalty."""
    match = longest_prefix_match(mid, fit_map)
    return match[1] if match is not None else None


def adjusted_score(score: float, fit: float | None) -> float:
    """Final standing = score * fit/5. Unscored = 5 = no judgment, no penalty."""
    return score * (5.0 if fit is None else fit) / 5.0


def standing(share: float, cost: float, fit: float | None,
             alpha: float, beta: float) -> float:
    """The task order's number for one candidate: its fit-adjusted task score.
    The one scoring path shared by the candidate table and the deal."""
    return adjusted_score(task_score(share, cost, alpha, beta), fit)


def parse_fit(spec: str) -> dict:
    """'mid=score,mid=score' -> {prefix: clamped 0-5 float}.

    A malformed entry raises ValueError naming it; the caller reports it as
    the usage error it is (status 2), before anything is fetched."""
    out = {}
    for part in spec.split(","):
        mid, eq, val = part.strip().partition("=")
        if mid and eq:
            try:
                score = float(val)
            except ValueError:
                raise ValueError(
                    f"--fit entry '{mid}={val}' is not a number on 0-5") \
                    from None
            if not math.isfinite(score):
                raise ValueError(
                    f"--fit entry '{mid}={val}' is not a number on 0-5")
            out[mid] = max(0.0, min(5.0, score))
    return out


def mass_balance(masses: list) -> tuple[float, float]:
    """(top-1, top-2) share of score mass in a pool. The balance criterion:
    top-1 within [top1_min, top1_max] (not uniform, not dominated) and top-2
    <= top2_max (not a two-entry race)."""
    total = sum(masses) or 1.0
    s = sorted(masses, reverse=True)
    top1 = s[0] / total
    top2 = (s[0] + s[1]) / total if len(s) > 1 else top1
    return top1, top2


def weight_for(mid: str, table: dict) -> float:
    """Longest matching affinity prefix wins; 1.0 = neutral."""
    match = longest_prefix_match(mid, table)
    return match[1] if match is not None else 1.0


