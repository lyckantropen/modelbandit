#!/usr/bin/env python3
"""Rank OpenRouter models by domain popularity and price them live.

Stdlib only. Reads OpenRouter's task-classification leaderboards and daily token
rankings (Data API; CC BY 4.0), maps them to a domain from policy.json, and
emits a popularity-ranked candidate table priced at live rates, with effort
rungs and a batch cost projection. Prices are per-endpoint, not the models-list
figure: the same model can span 20x on output across providers, so projection
defaults to the worst endpoint. Mechanics live in --help; SKILL.md holds the
policy.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import urllib.request

MODELS_URL = "https://openrouter.ai/api/v1/models"
LOCAL_MODELS_URL = "http://127.0.0.1:1234/v1/models"
CLASS_URL = "https://openrouter.ai/api/v1/classifications/task?window=7d"
RANK_URL = "https://openrouter.ai/api/v1/datasets/rankings-daily"
KEY_URL = "https://openrouter.ai/api/v1/key"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "modelbind")
CACHE_TTL = 24 * 3600
# The free-request counter is spent as a run proceeds, so it is cached for a
# minute rather than the day the catalogues get.
KEY_CACHE_TTL = 60
# Free requests planning must leave unspent: the last few are not the plan's.
DEFAULT_FREE_QUOTA_RESERVE = 5

# Effort intent -> output-token multiplier. Reasoning tokens bill as completion
# tokens, so deliberation is bought in output spend — the axis that dominates
# authoring cost. Heuristic; override per run with --out-tokens.
EFFORT_MULTIPLIERS = {"glance": 0.6, "measured": 1.0, "thorough": 2.5, "exhaustive": 6.0}
INTENTS = tuple(EFFORT_MULTIPLIERS)

# Effort intents map to structural rung slots — glance->floor, measured->
# default, thorough->above-default, exhaustive->ceiling (the documented rung
# rule). A rung the model lacks collapses to its nearest and discounts the
# multiplier toward glance's (requested_rung_index / effort_multiplier).

# Token profiles: (input tokens, output tokens, cached share of input).
# authoring is output-weighted: a .md research note is mostly completion tokens.
PROFILES = {
    "authoring": (20_000, 12_000, 0.4),
    "agentic": (40_000, 4_000, 0.75),
    "chat": (8_000, 2_000, 0.5),
}
DOMAIN_PROFILE = {
    "research": "authoring", "writing": "authoring",
    "coding": "agentic", "orchestration": "agentic", "ops": "agentic",
}
BASES = ("worst", "primary", "best")

# The Nominal floor is derived from this Free-risk fraction of the cheapest
# priced paid ticket in the same pool.
DEFAULT_FREE_RISK = 0.35
# All-Free pools need a positive price reference when no paid ticket is priced.
NOMINAL_REFERENCE_TICKET = 1.0
FREE_SHARE_CHECK_TICKETS = 100
FREE_SHARE_CHECK_SEED = "policy-check-free-share"
FREE_SHARE_HISTORY_LIMIT = 10

DEFAULT_POLICY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policy.json"
)


def api_key() -> str | None:
    env = os.environ.get("OPENROUTER_API_KEY")
    if env:
        return env
    for path in ("~/.local/share/opencode/auth.json", "~/.config/opencode/auth.json"):
        p = os.path.expanduser(path)
        if os.path.exists(p):
            try:
                auth = json.load(open(p)).get("openrouter", {})
            except Exception:
                continue
            for field in ("api_key", "access_token", "key"):
                if auth.get(field):
                    return auth[field]
    return None


def fetch_json(url: str, cache_name: str, *, auth: bool, refresh: bool,
               ttl: float | None = None, stale_ok: bool = True):
    """Decoded JSON from `url`, cached on disk for `ttl` seconds.

    `ttl` defaults to the daily catalogue window; a short-lived figure (the
    free-request counter) passes its own. `stale_ok=False` refuses to answer
    from a cache the fetch could not refresh: a stale figure is fine for a
    price list, never for a counter that has since been spent.
    """
    ttl = CACHE_TTL if ttl is None else ttl
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_name)
    if not refresh and os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < ttl:
            with open(cache_path) as f:
                return json.load(f)
    headers = {"Accept": "application/json"}
    if auth:
        key = api_key()
        if not key:
            raise SystemExit(
                "OpenRouter Data API needs a key: set OPENROUTER_API_KEY or keep "
                "an OpenCode auth.json with an openrouter entry")
        headers["Authorization"] = f"Bearer {key}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except Exception as exc:
        if stale_ok and os.path.exists(cache_path):
            print(f"warning: fetch failed ({exc}); using stale cache", file=sys.stderr)
            with open(cache_path) as f:
                return json.load(f)
        raise SystemExit(f"cannot reach {url}: {exc}")
    with open(cache_path, "w") as f:
        json.dump(data, f)
    return data


def probe_local_models(fetcher=None) -> dict[str, dict]:
    """Discover LM Studio models for this run; failures are silent.

    This is deliberately not cached: the local server and its loaded models can
    change between invocations. ``fetcher`` accepts the URL and returns decoded
    JSON, keeping the probe deterministic and network-free in unit tests.
    """
    if fetcher is None:
        def fetcher(url):
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.load(response)

    try:
        payload = fetcher(LOCAL_MODELS_URL)
    except Exception:
        return {}
    rows = payload.get("data", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    served = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        mid = row.get("id")
        if not isinstance(mid, str) or not mid.strip():
            continue
        model = {"id": mid}
        window = row.get("context_length")
        if _is_plain_int(window) and window > 0:
            model["context_length"] = window
        served[mid] = model
    return served


def norm_id(model_id: str) -> str:
    return model_id.removeprefix("openrouter/")


def _is_plain_int(value) -> bool:
    """True for integers, excluding bool (which is an int subclass)."""
    return isinstance(value, int) and not isinstance(value, bool)


def is_free_route(mid: str, *, local: bool = False) -> bool:
    """Whether this serving identity is Free, independent of its price."""
    return local or mid.startswith("opencode/") or mid.endswith(":free")


_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\b(?:password|passwd|token|api[_-]?key|access[_-]?token|"
               r"secret[_-]?key)\b\s*[:=]\s*['\"]?[^\s,'\"]{4,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def _string_values(value) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [part for part in value if isinstance(part, str) and part]
    if isinstance(value, dict):
        return [part for part in value.values() if isinstance(part, str) and part]
    return []


def secrets_gate(material: str, *, machine: dict, rules: dict | None = None) -> bool:
    """Pure Secrets gate verdict: True when sensitive content is included.

    ``machine`` supplies content and identifiers readable from machine state
    under ``outside_file_contents``, ``identifiers``, ``passwords``,
    ``tokens``, and ``keys``. Project ``rules`` may add literal ``phrases``
    and regular-expression ``patterns``; they cannot disable the built-ins.
    A path mention by itself is not a content inclusion.
    """
    if not isinstance(material, str) or not material:
        return False
    machine = machine if isinstance(machine, dict) else {}
    if any(value in material
           for field in ("outside_file_contents", "identifiers", "passwords",
                         "tokens", "keys")
           for value in _string_values(machine.get(field))):
        return True
    if any(pattern.search(material) for pattern in _SECRET_VALUE_PATTERNS):
        return True
    if isinstance(rules, dict):
        if any(value in material for value in _string_values(rules.get("phrases"))):
            return True
        for source in _string_values(rules.get("patterns")):
            try:
                if re.search(source, material):
                    return True
            except re.error:
                continue
    return False


def resolve_model(models: dict, by_canon: dict, permaslug: str):
    """Leaderboard rows are permaslugs. Resolve via canonical_slug; heuristic
    date-stripping misprices dated releases (v4-pro-0813 vs v4-pro) and is a
    last resort only. Returns (model_or_None, how)."""
    if permaslug in models:
        return models[permaslug], "exact"
    if permaslug in by_canon:
        return by_canon[permaslug], "canonical"
    stripped = re.sub(r"-\d{8}(:.*)?$", lambda m: m.group(1) or "", permaslug)
    if stripped in models:
        return models[stripped], "heuristic"
    return None, "unresolved"


def endpoint_pricings(slug: str, refresh: bool) -> list[dict]:
    """Per-provider pricing for one model. Failures return [] quietly."""
    safe = re.sub(r"[^a-zA-Z0-9._-]", "--", slug)
    try:
        data = fetch_json(f"{MODELS_URL}/{slug}/endpoints",
                          f"endpoints--{safe}.json", auth=True, refresh=refresh)
    except SystemExit:
        return []
    payload = data.get("data", {}) if isinstance(data, dict) else {}
    return payload.get("endpoints", []) or []


def endpoint_completion_cap(endpoints: list[dict] | None) -> int | None:
    """Use the tightest reported endpoint completion cap, if any is known."""
    caps = [endpoint.get("max_completion_tokens") for endpoint in endpoints or ()
            if isinstance(endpoint, dict)
            and _is_plain_int(endpoint.get("max_completion_tokens"))
            and endpoint["max_completion_tokens"] > 0]
    return min(caps) if caps else None


def per_million(price_str: str) -> float:
    return float(price_str) * 1_000_000


def effort_ladder(model: dict) -> list[str]:
    """Ladder assumption when the catalog does not name rungs:
    reasoning_effort models expose the full house; reasoning-only models are
    binary; anything else has no effort dial. Collapse-to-nearest makes an
    over-full assumption harmless."""
    params = model.get("supported_parameters") or []
    if "reasoning_effort" in params:
        return ["none", "low", "medium", "high", "xhigh", "max"]
    if "reasoning" in params:
        return ["none", "thinking"]
    return ["default"]


def resolve_rung_index(ladder: list[str], intent: str) -> int:
    n = len(ladder)
    if n == 1:
        return 0
    default_idx = ladder.index("medium") if "medium" in ladder else (n - 1 + 1) // 2
    return {"glance": 0, "measured": default_idx,
            "thorough": min(default_idx + 1, n - 1), "exhaustive": n - 1}[intent]


def resolve_rung(ladder: list[str], intent: str) -> str:
    return ladder[resolve_rung_index(ladder, intent)]


def requested_rung_index(ladder: list[str], intent: str) -> int:
    """The intent's structural slot on the ladder, uncapped: glance->floor,
    measured->default, thorough->above-default, exhaustive->ceiling. A slot the
    ladder provides resolves exactly; one it lacks collapses to its nearest
    rung."""
    n = len(ladder)
    if n == 1:
        return 0
    default_idx = ladder.index("medium") if "medium" in ladder else (n - 1 + 1) // 2
    return {"glance": 0, "measured": default_idx,
            "thorough": default_idx + 1, "exhaustive": n - 1}[intent]


def rung_collapsed(ladder: list[str], intent: str) -> bool:
    """True when the ladder lacked the requested rung and the nearest was taken."""
    return (len(ladder) > 1
            and resolve_rung_index(ladder, intent)
            < requested_rung_index(ladder, intent))


def effort_multiplier(ladder: list[str], intent: str) -> float:
    """Output multiplier for `intent` on this model's ladder.

    A rung the model lacks collapses to its nearest, and a collapsed rung is
    priced for the deliberation the ladder can deliver: the multiplier scales
    toward glance's in proportion to the resolved rung's slot over the
    requested one, never below glance's and never above the intent's own.
    Ladders that provide the requested rung — every intent on a full ladder —
    price the EFFORT_MULTIPLIERS table exactly. A one-rung ladder has no
    effort dial and delivers no deliberation above glance at any intent.
    """
    mult = EFFORT_MULTIPLIERS[intent]
    if len(ladder) == 1:
        return EFFORT_MULTIPLIERS["glance"] if intent != "glance" else mult
    requested = requested_rung_index(ladder, intent)
    resolved = resolve_rung_index(ladder, intent)
    if requested == 0 or resolved >= requested:
        return mult
    glance = EFFORT_MULTIPLIERS["glance"]
    return glance + (mult - glance) * (resolved / requested)


def mult_for(model: dict, intent: str) -> float:
    """The model's output multiplier at the intent's rung."""
    return effort_multiplier(effort_ladder(model), intent)


def blended_from_pricing(pricing: dict, in_tok: int, out_tok: int, cached: float,
                         multiplier: float) -> float:
    return (
        in_tok * (1 - cached) * float(pricing["prompt"])
        + in_tok * cached * float(pricing.get("input_cache_read", pricing["prompt"]))
        + out_tok * multiplier * float(pricing["completion"])
    )


def price_model(model: dict, eps: list[dict], in_tok: int, out_tok: int,
                cached: float, mult: float) -> dict:
    """Costs across endpoints: worst (budget-safe), primary (models list),
    best (floor). Output range is shown because it dominates authoring cost."""
    primary = blended_from_pricing(model["pricing"], in_tok, out_tok, cached, mult)
    if not eps:
        return {"worst": primary, "primary": primary, "best": primary,
                "worst_ep": None, "best_ep": None,
                "out_min": per_million(model["pricing"]["completion"]),
                "out_max": per_million(model["pricing"]["completion"]),
                "n_eps": 0}
    costs = [(blended_from_pricing(e["pricing"], in_tok, out_tok, cached, mult), e)
             for e in eps]
    outs = [per_million(e["pricing"]["completion"]) for e in eps]
    worst = max(costs, key=lambda t: t[0])
    best = min(costs, key=lambda t: t[0])
    return {"worst": worst[0], "primary": primary, "best": best[0],
            "worst_ep": worst[1].get("name", "?"), "best_ep": best[1].get("name", "?"),
            "out_min": min(outs), "out_max": max(outs), "n_eps": len(eps)}


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
class DealPolicy:
    blend_weight: float
    eligibility_top_k: int


@dataclasses.dataclass(frozen=True)
class ContextGatePolicy:
    headroom: float = 2.0
    margin: float = 0.5


@dataclasses.dataclass(frozen=True)
class DealParameters:
    blend_weight: float
    top_k: int
    seed: str
    tickets: int
    fit_adjusted_task_scores: dict | None = None
    admitted: frozenset | None = None


@dataclasses.dataclass(frozen=True)
class PolicyConfig:
    alpha: float
    beta: float
    thresholds: dict
    factors: dict
    deal: DealPolicy
    context: ContextGatePolicy
    free_risk: float = DEFAULT_FREE_RISK
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
        deal=DealPolicy(
            blend_weight=float(required(affinity, "blend_weight",
                                        "affinity.blend_weight")),
            eligibility_top_k=int(required(affinity, "eligibility_top_k",
                                           "affinity.eligibility_top_k")),
        ),
        context=ContextGatePolicy(headroom=headroom, margin=margin),
        free_risk=free_risk,
        free_quota_reserve=quota_reserve,
    )


def load_free_models(policy: dict) -> dict:
    """Validate the curated Free route catalog at the policy boundary.

    A bad window or misspelled Exposure must stop the run: either could make a
    candidate look safer or more capable than the policy says. ``summary_ref``
    remains optional in policy, but when present it must be a usable string.
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
        summary_ref = entry.get("summary_ref")
        if summary_ref is not None and (not isinstance(summary_ref, str)
                                        or not summary_ref.strip()):
            raise SystemExit(f"policy {path}.summary_ref must be a non-empty string")
    return catalog


def _free_summary(entry: dict, summaries: dict, mid: str | None = None) -> bool:
    """Whether a Free route has a resolvable explicit or prefix summary."""
    ref = entry.get("summary_ref")
    return ((isinstance(ref, str) and bool(summaries.get(ref)))
            or (mid is not None and bool(hint_for(mid, summaries))))


def _family_share(share: dict, entry: dict) -> float:
    """A curated Free route's standing: its family's domain share.

    An ``opencode/*`` or local serving has no leaderboard row of its own; its
    popularity is the family's revealed preference, exactly the board share an
    OpenRouter ``:free`` route would carry. The family prefix is the summary
    reference with any trailing ``:free`` stripped, so a dated
    ``X-YYYYMMDD:free`` board row still counts toward it. No summary reference
    means no observable popularity — the standing stays zero.
    """
    ref = entry.get("summary_ref")
    if not isinstance(ref, str) or not ref.strip():
        return 0.0
    prefix = ref.removesuffix(":free")
    return sum(s for key, s in share.items() if key.startswith(prefix))


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
                          summaries: dict) -> tuple[dict, dict]:
    """Merge cataloged OpenCode models and ranked :free routes into candidates.

    OpenRouter :free rows retain their own slug even when the API only resolves
    them through a paid family model. Uncataloged or unsummarized ranked routes
    stay visible but the catalog gate prevents the Deal from using them.
    OpenCode catalog entries are added with their family's domain share (the
    family's revealed preference standing in for a route with no board row);
    their context and Exposure remain curated facts, not inferred runtime data.
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
        if (not is_free_route(prefix)
                or not _free_summary(entry, summaries, prefix)):
            continue
        merged_share.setdefault(prefix, 0.0)
        if merged_share[prefix] == 0.0:
            merged_share[prefix] = _family_share(merged_share, entry)
        merged_models.setdefault(prefix, _free_model_record(prefix, entry))

    return merged_share, merged_models


def merge_local_candidates(share: dict, models: dict, served: dict,
                           free_models: dict) -> tuple[dict, dict]:
    """Join this run's served local ids to the curated Free catalog.

    Served ids without a local Exposure catalog entry are ignored. Cataloged
    served ids remain visible even without a summary, but the admission seam
    requires that summary before they can be picked or dealt.
    """
    merged_share = dict(share)
    merged_models = {mid: dict(model) for mid, model in models.items()}
    for mid in served:
        match = longest_prefix_match(mid, free_models)
        if match is None:
            continue
        entry = match[1]
        if not isinstance(entry, dict) or entry.get("exposure") != "local":
            continue
        merged_share.setdefault(mid, 0.0)
        if merged_share[mid] == 0.0:
            merged_share[mid] = _family_share(merged_share, entry)
        # The curated context window is policy; the probe establishes that this
        # candidate is currently served. Runtime metadata is not policy.
        merged_models[mid] = _free_model_record(mid, entry, served[mid])
    return merged_share, merged_models


def local_candidate_ids(served: dict, free_models: dict) -> set[str]:
    """Served ids matched by a catalog entry whose Exposure is ``local``."""
    return {mid for mid in served
            if (match := longest_prefix_match(mid, free_models)) is not None
            and isinstance(match[1], dict)
            and match[1].get("exposure") == "local"}


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


def nominal_floor_cost(free_risk: float, cheapest_paid_ticket: float) -> float:
    """A Free route's ticket cost: Free risk times the pool's cheapest paid
    ticket. One derived Nominal floor applies uniformly across Free routes.
    """
    return free_risk * cheapest_paid_ticket


def effective_costs(costs: dict, *, free_risk: float,
                    free: set[str] | frozenset[str] = frozenset()) -> dict:
    """The score's cost term for one pool: Free routes at derived Free risk,
    every paid ticket at its own price.

    `free` names the pool's Free routes — a serving fact (see free_route_ids),
    never inferred from a zero price. The Nominal floor is Free risk times the
    cheapest priced paid ticket, or a $1 fallback reference when the pool has
    no priced paid ticket. A valid risk fraction makes the floor positive and,
    when paid tickets exist, strictly below their cheapest ticket. A paid
    ticket that priced at nothing keeps the pool's cheapest paid ticket.
    """
    paid = [v for mid, v in costs.items() if mid not in free and v > 0]
    cheapest_paid = min(paid, default=NOMINAL_REFERENCE_TICKET)
    has_free = any(mid in free for mid in costs)
    nominal_floor = nominal_floor_cost(free_risk, cheapest_paid) if has_free else None
    return {mid: (nominal_floor if mid in free else (v if v > 0 else cheapest_paid))
            for mid, v in costs.items()}


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
    """'mid=score,mid=score' -> {prefix: clamped 0-5 float}."""
    out = {}
    for part in spec.split(","):
        mid, eq, val = part.strip().partition("=")
        if mid and eq:
            out[mid] = max(0.0, min(5.0, float(val)))
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


# --- Admission seam --------------------------------------------------------
# What a candidate exposes of the material it is fed. Exposure is a property
# of the serving route, never inferred from price: free does not imply trains,
# paid does not imply no-retention. Unknown free defaults to trains.
EXPOSURES = ("no-retention", "trains", "local")


@dataclasses.dataclass(frozen=True)
class Shape:
    """A Ticket shape's admission-relevant elements.

    Sensitive is the shape's fifth element: the Secrets gate's verdict on the
    material, bound per invocation, never a mood declared mid-run.
    """
    sensitive: bool = False
    input_tokens: int | None = None
    context_headroom: float = 2.0
    context_margin: float = 0.5
    output_tokens: int | None = None


@dataclasses.dataclass(frozen=True)
class Candidate:
    """The candidate facts admission judges: Exposure, serving and Footprint."""
    id: str
    exposure: str
    is_free: bool = False
    context_length: int | None = None
    cataloged: bool = True
    completion_cap: int | None = None
    output_multiplier: float = 1.0


def resolve_exposure(mid: str, *, free_models: dict | None = None,
                     overrides: dict | None = None, local: bool = False) -> str:
    """One candidate's Exposure, by precedence:

    explicit policy override (prefix-keyed) > locally served > curated free
    catalog entry > ':free'-suffixed slug => trains > default no-retention.

    The default is the paid route's assumption — the account's data policy
    already holds it. A free route the catalog does not carry is exposed until
    the user says otherwise.
    """
    match = longest_prefix_match(mid, overrides or {})
    if match is not None:
        return known_exposure(mid, match[1])
    if local:
        return "local"
    match = longest_prefix_match(mid, free_models or {})
    entry = match[1] if match is not None else {}
    if isinstance(entry, dict) and entry.get("exposure"):
        return known_exposure(mid, entry["exposure"])
    if is_free_route(mid):
        return "trains"
    return "no-retention"


def known_exposure(mid: str, value: str) -> str:
    """A policy-named Exposure, or a loud stop: a misspelt class would
    silently widen the gate."""
    if value not in EXPOSURES:
        raise SystemExit(f"unknown exposure '{value}' for {mid}; "
                         f"known: {', '.join(EXPOSURES)}")
    return value


def candidate_for(mid: str, policy: dict, *, local: bool = False,
                  model: dict | None = None,
                  endpoints: list[dict] | None = None,
                  intent: str = "measured") -> Candidate:
    """The candidate facts a policy implies for one model id: Exposure from
    the policy's `exposure` override map and `free_models` catalog, plus its
    serving price class and Footprint capacities."""
    catalog_match = longest_prefix_match(mid, policy.get("free_models", {}))
    catalog_entry = catalog_match[1] if catalog_match is not None else {}
    is_free = is_free_route(mid, local=local)
    context_length = (catalog_entry.get("context_length")
                      if isinstance(catalog_entry, dict) else None)
    if context_length is None and model:
        context_length = model.get("context_length")
    completion_cap = endpoint_completion_cap(endpoints)
    if (completion_cap is None and is_free
            and isinstance(catalog_entry, dict)):
        completion_cap = catalog_entry.get("max_completion_tokens")
    return Candidate(id=mid,
                      exposure=resolve_exposure(
                          mid, free_models=policy.get("free_models", {}),
                          overrides=policy.get("exposure", {}), local=local),
                      is_free=is_free,
                      context_length=context_length,
                      completion_cap=completion_cap,
                      output_multiplier=(mult_for(model, intent) if model
                                         else EFFORT_MULTIPLIERS[intent]),
                      cataloged=(not is_free or (
                           _free_summary(catalog_entry,
                                         policy.get("summaries", {}), mid)
                           and (not local and not mid.startswith("opencode/")
                                or catalog_match is not None))))


def free_route_ids(mids, policy: dict, *, local=()) -> set[str]:
    """The Free routes among `mids`, by the serving rule: a ':free' slug, an
    OpenCode 'opencode/' model, or one this machine serves (`local`) — the
    route predicate reports as Free. Never the price: a paid route
    may be cheap, and Free is what the harness serves for nothing."""
    local = set(local)
    return {mid for mid in mids if is_free_route(mid, local=mid in local)}


def _is_harness_free(mid: str, local_ids) -> bool:
    """Whether endpoint pricing is absent because the harness serves this id."""
    return mid.startswith("opencode/") or mid in local_ids


def deal_free_share(rows: list[dict], policy: dict, *, local=()) -> tuple[int, int]:
    """Count tickets dealt to Free routes, independent of their Exposure."""
    free = free_route_ids((row["mid"] for row in rows), policy, local=local)
    total = sum(row["tickets"] for row in rows)
    return sum(row["tickets"] for row in rows if row["mid"] in free), total


@dataclasses.dataclass(frozen=True)
class Decision:
    """An admission verdict: admitted, or excluded with a visible reason.

    An excluded candidate is never hidden — the ranked table marks it and the
    deal does not draw it.
    """
    admitted: bool
    reason: str = ""


ADMITTED = Decision(True)


def exposure_gate(shape: Shape, candidate: Candidate) -> Decision:
    """The Exposure<->Sensitive gate: exposed candidates never serve a
    Sensitive shape, whether free or paid. No-retention and local candidates
    are admitted — Exposure, not price, decides Eligibility."""
    if shape.sensitive and candidate.exposure == "trains":
        return Decision(False, f"exposed ({candidate.exposure})")
    return ADMITTED


def context_gate(shape: Shape, candidate: Candidate) -> Decision:
    """Compare both Footprint dimensions to capacity using shared policy.

    A Free route that overruns either dimension is excluded. Paid routes remain
    admitted, but return the same reasons for the ranked table to flag.
    """
    reasons = []
    if shape.input_tokens is not None and candidate.context_length is not None:
        required = shape.input_tokens * shape.context_headroom
        available = candidate.context_length * shape.context_margin
        if required > available:
            reasons.append(
                f"over window (context input budget {required:,.0f} exceeds "
                f"{available:,.0f} tokens)")
    if shape.output_tokens is not None and candidate.completion_cap is not None:
        required = shape.output_tokens * candidate.output_multiplier
        available = candidate.completion_cap * shape.context_margin
        if required > available:
            reasons.append(
                f"over completion cap (rung-priced output {required:,.0f} "
                f"exceeds {available:,.0f} tokens)")
    if not reasons:
        return ADMITTED
    reason = "; ".join(reasons)
    return Decision(not candidate.is_free, reason)


def catalog_gate(shape: Shape, candidate: Candidate) -> Decision:
    """Only curated, summary-backed Free routes can enter the Deal."""
    if candidate.is_free and not candidate.cataloged:
        return Decision(False, "free route requires a catalog entry and "
                        "summary where applicable (summary resolution is required)")
    return ADMITTED


# The gates, in order, behind the one decision. The Context and catalog gates
# join the existing Exposure gate.
GATES = (exposure_gate, context_gate, catalog_gate)


def quota_gate(candidate: Candidate, verdict: QuotaVerdict) -> Decision:
    """The Free-request quota gate: ':free' routes only.

    The counter is an OpenRouter account fact spent by the routes OpenRouter
    serves for nothing. A harness-served 'opencode/*' model or a model this
    machine serves spends none of it, so a spent counter says nothing about
    them; a paid route is charged credits, not free requests.
    """
    # This OpenRouter serving counter does not apply to harness-served Free routes.
    if not verdict.eligible and candidate.id.endswith(":free"):
        return Decision(False, verdict.reason)
    return ADMITTED


def admit(shape: Shape, candidate: Candidate, *,
          quota: QuotaVerdict | None = None) -> Decision:
    """Admission: may this candidate serve this shape? Pure, and the single
    decision both the ranked table and the deal consult.

    ``quota`` is the run's free-request verdict (see free_quota_decision);
    None means no counter was reported, which admits everything the shape
    admits."""
    flags = []
    for gate in GATES:
        decision = gate(shape, candidate)
        if not decision.admitted:
            return decision
        if decision.reason:
            flags.append(decision.reason)
    if quota is not None:
        decision = quota_gate(candidate, quota)
        if not decision.admitted:
            return decision
        if decision.reason:
            flags.append(decision.reason)
    return Decision(True, "; ".join(flags)) if flags else ADMITTED


# --- Free-request quota ----------------------------------------------------
# OpenRouter's daily free-request counter: one figure shared by every ':free'
# route on the account, reset at UTC midnight. The tier ceiling is set by
# all-time credits purchased, and no response header reports the running
# count, so it is read from the key payload up front. Harness-served free
# models — 'opencode/*' and local — never spend it.


@dataclasses.dataclass(frozen=True)
class FreeQuota:
    """The account's daily free-request counter: one figure for every ':free'
    route, or all-None when the payload carries no usable one."""
    used: int | None = None
    limit: int | None = None
    remaining: int | None = None

    @property
    def reported(self) -> bool:
        """Whether the endpoint reported a counter at all."""
        return not (self.used is None and self.limit is None
                    and self.remaining is None)


@dataclasses.dataclass(frozen=True)
class QuotaVerdict:
    """Whether ':free' routes stay eligible at this quota, and why not."""
    eligible: bool
    reason: str = ""


def _count(value) -> int | None:
    """A reported count, or None for anything that is not a plain integer."""
    if not _is_plain_int(value):
        return None
    return value


def free_quota_from_payload(payload) -> FreeQuota | None:
    """The key payload's ``free_model_daily_requests`` counter, or None.

    OpenRouter nests key fields under ``data``; the counter may carry ``used``,
    ``limit`` and ``remaining``. A payload without the counter — an older
    response, a key with no free tier, a different field name — reports no
    counter rather than an empty one, which leaves ':free' routes in the pool.
    """
    if not isinstance(payload, dict):
        return None
    holder = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    entry = holder.get("free_model_daily_requests")
    if not isinstance(entry, dict):
        return None
    counts = {}
    for key in ("used", "limit", "remaining"):
        raw = entry.get(key)
        if raw is not None and _count(raw) is None:
            return None  # a counter half-read is not a counter
        counts[key] = _count(raw)
    if all(value is None for value in counts.values()):
        return None
    return FreeQuota(**counts)


def _quota_unavailable(detail: str) -> None:
    """Say it once, and never decide anything from it."""
    suffix = f" ({detail})" if detail else ""
    print(f"warning: free quota unavailable{suffix}; :free routes stay in the pool",
          file=sys.stderr)


def free_quota(refresh: bool = False, fetcher=None) -> FreeQuota | None:
    """The account's daily free-request counter, or None when unavailable.

    Read through the shared fetch seam so it caches on disk like every other
    live figure — but for a minute, not a day, and never from a stale cache:
    the count is spent as the run proceeds. An unreachable endpoint, a missing
    key or a payload without the counter reports no counter and warns; it
    never stops a run and never removes a route.
    """
    if fetcher is None:
        def fetcher(url):
            return fetch_json(url, "key.json", auth=True, refresh=refresh,
                              ttl=KEY_CACHE_TTL, stale_ok=False)
    try:
        payload = fetcher(KEY_URL)
    except SystemExit as exc:
        _quota_unavailable(str(exc.code) if exc.code not in (None, 0) else "")
        return None
    except Exception as exc:
        _quota_unavailable(str(exc))
        return None
    return free_quota_from_payload(payload)


def free_quota_decision(*, used: int | None, limit: int | None,
                        remaining: int | None, reserve: int,
                        planned_free: int) -> QuotaVerdict:
    """Whether ':free' routes stay in the pool: pure, from the count alone.

    The plan needs ``planned_free`` requests plus a ``reserve`` the planning
    must not eat into. A route set that cannot cover that is a cliff, not a
    penalty: ':free' routes leave the pool rather than be assumed. When the
    endpoint reports no ceiling (``limit`` is None) there is no counter to
    judge and the pool is unchanged.
    """
    if remaining is None:
        remaining = (limit - used
                     if limit is not None and used is not None else None)
    need = planned_free + reserve
    if remaining is None or remaining >= need:
        return QuotaVerdict(True)
    if remaining <= 0:
        spent = (f" ({used}/{limit} used)"
                 if used is not None and limit is not None else "")
        return QuotaVerdict(False, f"free quota exhausted{spent}")
    return QuotaVerdict(False, f"free quota thin ({remaining} left < "
                               f"{planned_free} planned + {reserve} reserve)")


def popularity_ranking(share: dict, models: dict) -> list[tuple[str, float]]:
    """Share-ranked selectable models: the popularity order every pool starts
    from. Unranked or unresolved models never play, so they drop out here."""
    return [(mid, s) for mid, s in sorted(share.items(), key=lambda kv: -kv[1])
            if mid in models]


def paid_pool(share: dict, models: dict, free: set[str],
              top_k: int) -> list[tuple[str, float]]:
    """The balance criterion's players: the top_k most popular paid models.

    Score mass judges the paid competition — the band was calibrated for a
    landscape in which Free routes were not scored at all, and Free's
    participation is answered by the Free share signal, not by a threshold.
    Free routes leave before the cut, so a pool that Free dominates wholly
    still has a paid competition to judge.
    """
    return [entry for entry in popularity_ranking(share, models)
            if entry[0] not in free][:top_k]


def eligibility_pool(share: dict, models: dict, aff: dict, top_k: int,
                     admitted: frozenset | None = None) -> list[tuple[str, float]]:
    """The deal's players, computed once for every consumer.

    Eligibility stays popularity: the top_k selectable models, plus ranked
    models the user favors (weight > 1) below the cut — the admission seam's
    verdict applied first (``admitted``: the ids it admits; None admits all).
    An excluded player is never replaced by a lower-ranked one: popularity
    orders, admission only removes. Returns [(mid, share)] in popularity
    order; the candidate table prices these same players.
    """
    ranked = [entry for entry in popularity_ranking(share, models)
              if admitted is None or entry[0] in admitted]
    return ranked[:top_k] + [(mid, s) for mid, s in ranked[top_k:]
                             if weight_for(mid, aff) > 1.0]


def blend_bases(pool: list[tuple[str, float]],
                fit_adjusted_task_scores: dict | None) -> list[float]:
    """Each pool member's blend base: its fit-adjusted task score.

    Raw share is orders of magnitude below score scale, so substituting it for
    a missing entry would hand the model to the preference term alone. A pool
    member without a score is a caller bug and stops the deal instead.
    """
    scores = fit_adjusted_task_scores or {}
    missing = [mid for mid, _ in pool if mid not in scores]
    if missing:
        raise SystemExit("deal pool member(s) without a fit-adjusted task "
                         f"score: {', '.join(missing)}")
    return [scores[mid] for mid, _ in pool]


def plan_deal(share: dict, models: dict, aff: dict,
              parameters: DealParameters) -> list[dict]:
    """Multi-ticket deal over the eligible pool: seeded, preference-tilted.

    Eligibility is popularity (eligibility_pool). The draw blends the task
    baseline and preference:

        draw = (1 - blend_weight) * task_score + blend_weight * pref
        (each normalized)

    where every pool member's base is its fit-adjusted task score, supplied
    for the whole pool by the caller (blend_bases). Deterministic in seed.
    The pool is admission-filtered before the draw (parameters.admitted), so
    the deal and the ranked table agree about what may serve the shape.
    Returns one row per pool model:
    {"mid", "share", "base", "pref", "draw", "tickets"}.
    """
    blend_weight = parameters.blend_weight
    seed = parameters.seed
    tickets = parameters.tickets
    pool = eligibility_pool(share, models, aff, parameters.top_k,
                            parameters.admitted)
    if not pool:
        return []
    bases = blend_bases(pool, parameters.fit_adjusted_task_scores)
    prefs = [weight_for(mid, aff) for mid, _ in pool]
    pt, at = sum(bases) or 1.0, sum(prefs) or 1.0
    draws = [(1 - blend_weight) * (p / pt) + blend_weight * (a / at)
             for p, a in zip(bases, prefs)]
    dt = sum(draws) or 1.0
    draws = [d / dt for d in draws]
    counts = [0] * len(pool)
    cum, run = [], 0.0
    for d in draws:
        run += d
        cum.append(run)
    for i in range(tickets):
        r = random.Random(f"{seed}::{i}").random() * run
        for j, c in enumerate(cum):
            if r <= c:
                counts[j] += 1
                break
    return [{"mid": mid, "share": s, "base": b, "pref": pr, "draw": d,
             "tickets": n}
            for (mid, s), b, pr, d, n
            in zip(pool, bases, prefs, draws, counts)]


def policy_age_days(policy_path: str) -> int | None:
    try:
        return int((time.time() - os.path.getmtime(policy_path)) // 86400)
    except OSError:
        return None


def record_free_share_measurement(shape: dict, zero: bool) -> tuple[bool, int]:
    """Persist the last measurements for a non-Sensitive ticket shape.

    Returns (had_prior_measurement, trailing_zero_count). History is diagnostic
    cache data only; it never changes policy or Deal eligibility.
    """
    encoded = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "free-share-history.json")
    try:
        with open(path) as f:
            history = json.load(f)
        if not isinstance(history, dict):
            history = {}
    except (OSError, ValueError):
        history = {}
    previous = history.get(key, {})
    if isinstance(previous, list):
        # Accept an early list-only cache entry without losing its trend.
        measurements = previous
        previous_streak = 0
        for item in reversed(previous):
            if item is not True:
                break
            previous_streak += 1
    elif isinstance(previous, dict):
        measurements = previous.get("measurements", [])
        previous_streak = previous.get("zero_streak", 0)
        if not _is_plain_int(previous_streak):
            previous_streak = 0
        if not previous_streak and isinstance(measurements, list):
            for item in reversed(measurements):
                if item is not True:
                    break
                previous_streak += 1
    else:
        measurements, previous_streak = [], 0
    if not isinstance(measurements, list):
        measurements = []
    had_prior = bool(measurements)
    measurements = (measurements + [bool(zero)])[-FREE_SHARE_HISTORY_LIMIT:]
    zero_streak = previous_streak + 1 if zero else 0
    history[key] = {"measurements": measurements,
                    "zero_streak": zero_streak}
    pending = path + ".tmp"
    with open(pending, "w") as f:
        json.dump(history, f)
    os.replace(pending, path)
    return had_prior, zero_streak


def domain_candidates(classif: dict, tags: list, models: dict, by_canon: dict):
    """Rank models by their share of the domain's classified traffic."""
    share = collections.defaultdict(float)
    matches: dict[str, str] = {}
    known_tags = set()
    for c in classif["classifications"]:
        if c["tag"] not in tags:
            continue
        known_tags.add(c["tag"])
        for m in c["models"]:
            raw_id = norm_id(m["id"])
            if is_free_route(raw_id):
                # A Free route is its own serving identity, even if the API's
                # canonical map points it at the paid family model.
                resolved = models.get(raw_id)
                how = "exact" if resolved else "unresolved"
                key = raw_id
            else:
                resolved, how = resolve_model(models, by_canon, raw_id)
                key = resolved["id"] if resolved else raw_id
            matches[key] = how if resolved else "unresolved"
            share[key] += c["usage_share"] * m["tag_usage_share"]
    return share, matches, known_tags


def run_check_policy(models: dict, by_canon: dict, classif: dict, domains: dict,
                     policy: dict, top: int, policy_path: str,
                     intent: str, basis: str, config: PolicyConfig,
                     local_ids=()) -> None:
    summaries = policy.get("summaries", {})
    signals = {k: v for k, v in policy.get("hints", {}).items()
               if isinstance(v, dict) and v.get("fit")}
    pool_k = config.deal.eligibility_top_k
    ranked_by_domain: dict[str, list[str]] = {}
    share_by_domain: dict[str, dict] = {}
    all_ranked: set[str] = set()
    local_ids = set(local_ids)
    for name, tags in domains.items():
        share, _, _ = domain_candidates(classif, tags, models, by_canon)
        share, _ = merge_free_candidates(
            share, models, policy.get("free_models", {}), summaries)
        for mid in local_ids:
            if mid in models:
                share.setdefault(mid, 0.0)
        share_by_domain[name] = share
        ranked_by_domain[name] = [mid for mid, _ in
                                  sorted(share.items(), key=lambda kv: -kv[1])[:top]]
        all_ranked.update(ranked_by_domain[name])
    # The deal's players: the eligibility top-K of each domain, plus ranked
    # models the user favors (weight > 1) below the cut — the same pool
    # plan_deal admits. Coverage is judged only for those.
    eligible = set()
    for name in domains:
        table = domain_weights(signals, name, config.factors)
        eligible.update(mid for mid, _ in
                        eligibility_pool(share_by_domain[name], models,
                                         table, pool_k))

    gaps = sorted(mid for mid in all_ranked if not hint_for(mid, summaries))
    stale = sorted(k for k in summaries
                   if not any(mid.startswith(k) for mid in all_ranked))
    stale_signals = sorted(k for k in signals
                           if not any(mid.startswith(k) for mid in all_ranked))
    coverage = []
    for key, entry in signals.items():
        fits = entry.get("fit", {})
        if not any(v in ("favor", "avoid") for v in fits.values()):
            continue
        for name, ranked in ranked_by_domain.items():
            if name in fits:
                continue
            hit = next((mid for mid in ranked
                        if mid.startswith(key) and mid in eligible), None)
            if hit:
                coverage.append(f"{key} ranks in {name} ({hit}) but has no fit there")

    # The safe diagnostic Deal is report-only. Its per-shape history is cache
    # data and cannot mutate policy or eligibility.
    free_share_zeros = []
    for name in domains:
        profile_name = DOMAIN_PROFILE.get(name, "agentic")
        in_tok, out_tok, cached = PROFILES[profile_name]
        shape = Shape(sensitive=False, input_tokens=in_tok,
                      context_headroom=config.context.headroom,
                      context_margin=config.context.margin)
        aff = domain_weights(signals, name, config.factors)
        admitted = frozenset(
            mid for mid in share_by_domain[name]
            if admit(shape, candidate_for(
                mid, policy, local=mid in local_ids,
                model=models.get(mid))).admitted)
        pool = eligibility_pool(share_by_domain[name], models, aff, pool_k,
                                admitted)
        free = free_route_ids((mid for mid, _ in pool), policy,
                              local=local_ids)
        if not free:
            continue
        costs = {}
        for mid, _ in pool:
            model = models[mid]
            eps = ([] if _is_harness_free(mid, local_ids)
                   else endpoint_pricings(mid, False))
            pricing = price_model(model, eps,
                                  in_tok, out_tok, cached, mult_for(model, intent))
            costs[mid] = pricing[basis]
        effective = effective_costs(
            costs,
            free_risk=config.free_risk,
            free=free)
        scores = {mid: standing(share, effective[mid], None,
                                config.alpha, config.beta)
                  for (mid, share) in pool}
        rows = plan_deal(
            share_by_domain[name], models, aff,
            DealParameters(blend_weight=config.deal.blend_weight,
                           top_k=pool_k, seed=FREE_SHARE_CHECK_SEED,
                           tickets=FREE_SHARE_CHECK_TICKETS,
                           fit_adjusted_task_scores=scores,
                           admitted=admitted))
        free_tickets, dealt_tickets = deal_free_share(
            rows, policy, local=local_ids)
        shape_key = {"domain": name, "profile": profile_name,
                     "input_tokens": in_tok, "output_tokens": out_tok,
                     "cached_share": cached, "effort": intent,
                     "pricing_basis": basis, "sensitive": False,
                     "eligibility_top_k": pool_k,
                     "blend_weight": config.deal.blend_weight,
                     "scoring": {"alpha": config.alpha, "beta": config.beta,
                                 "free_risk": config.free_risk},
                     "context_gate": {
                         "headroom": config.context.headroom,
                         "margin": config.context.margin},
                     "eligible_free_routes": sorted(free),
                     "domain_hints": {
                         key: value for key, value in signals.items()
                         if name in value.get("fit", {})}}
        had_history, zero_streak = record_free_share_measurement(
            shape_key, dealt_tickets > 0 and free_tickets == 0)
        if dealt_tickets and free_tickets == 0:
            free_share_zeros.append((name, profile_name, dealt_tickets,
                                     had_history, zero_streak))
    age = policy_age_days(policy_path)

    print("# Policy check\n")
    age_txt = f"{age} day{'' if age == 1 else 's'} old" if age is not None \
        else "unknown (file missing)"
    print(f"policy.json last modified: {age_txt}\n")

    doms_of = {mid: ", ".join(n for n, r in ranked_by_domain.items() if mid in r)
               for mid in all_ranked}
    print("## Research gaps (ranked without summary)")
    for mid in gaps or ["— none"]:
        doms = doms_of.get(mid, "")
        print(f"- {mid}" + (f" ({doms})" if doms else ""))
    print("\n## Stale summaries (no current rank)")
    for key in stale or ["— none"]:
        gone = "" if any(m.startswith(key) for m in models) else " — not in model list"
        print(f"- {key}{gone}")
    print("\n## Stale signals (fit keys with no current rank)")
    for key in stale_signals or ["— none"]:
        print(f"- {key}")
    print("\n## Signal coverage gaps (opinion elsewhere, silent here)")
    for line in sorted(coverage) or ["— none"]:
        print(f"- {line}")

    print("\n## Free-share trends to zero (safe-shape history)")
    print(f"History retains the last {FREE_SHARE_HISTORY_LIMIT} measurements "
          "per shape; this report does not change policy.")
    for signal in free_share_zeros:
        name, profile_name, tickets, had_history, streak = signal
        if streak >= 2:
            detail = f"free share 0 for {streak} consecutive checks"
        elif not had_history:
            detail = "free share 0 (snapshot; no history)"
        else:
            detail = "free share 0 for 1 consecutive check"
        print(f"- free-share-trends-to-zero: {name} ({profile_name}, {intent}, "
              f"non-Sensitive) — {detail} (0/{tickets} tickets)")
    if not free_share_zeros:
        print("- — none")

    alpha, beta = config.alpha, config.beta
    thresholds = config.thresholds
    print(f"\n## Score balance (top-{pool_k} paid pool, {basis} basis)")
    re_tune = False
    judged = False
    for name in domains:
        # The band judges the paid competition. Free routes' participation is
        # answered by the Free share signal above, never by this threshold.
        free = free_route_ids(share_by_domain[name], policy, local=local_ids)
        pool = paid_pool(share_by_domain[name], models, free, pool_k)
        if not pool:
            continue
        if len(pool) < 3:
            # Below three paid candidates the balance criterion has nothing to
            # judge: a one-candidate pool is 100% top mass by definition, not a
            # tuning failure. Report and never trip the verdict.
            print(f"- {name}: {len(pool)} paid candidate"
                  f"{'s' if len(pool) != 1 else ''} — balance not judgeable "
                  f"(needs 3+)")
            continue
        in_tok, out_tok, cached = PROFILES[DOMAIN_PROFILE.get(name, "agentic")]
        costs = {}
        for mid, s in pool:
            m_mult = mult_for(models[mid], intent)
            eps = ([] if _is_harness_free(mid, local_ids)
                   else endpoint_pricings(mid, False))
            pricing = price_model(models[mid], eps,
                                  in_tok, out_tok, cached, m_mult)
            costs[mid] = pricing[basis]
        eff = effective_costs(
            costs,
            free_risk=config.free_risk,
            free=free_route_ids(costs, policy, local=local_ids))
        masses = [task_score(s, eff[mid], alpha, beta) for mid, s in pool]
        t1, t2 = mass_balance(masses)
        ok = (thresholds["top1_min"] <= t1 <= thresholds["top1_max"]
              and t2 <= thresholds["top2_max"])
        re_tune = re_tune or not ok
        judged = True
        print(f"- {name}: top-1 {t1:.0%}, top-2 {t2:.0%} "
              f"(limits {thresholds['top1_min']:.0%}–{thresholds['top1_max']:.0%} / "
              f"{thresholds['top2_max']:.0%}) — {'ok' if ok else 'OUT OF BALANCE'}")
    if not judged and any(popularity_ranking(share_by_domain[name], models)[:pool_k]
                          for name in domains):
        # Every non-empty pool was thin: no domain's balance was measurable.
        print("(no domain with 3+ paid candidates — balance not judgeable)")

    due = bool(gaps) or bool(stale) or bool(stale_signals) or bool(coverage) \
        or bool(free_share_zeros) \
        or (age is not None and age > 30)
    reasons = []
    if gaps:
        reasons.append(f"{len(gaps)} gap{'' if len(gaps) == 1 else 's'}")
    if stale:
        reasons.append(f"{len(stale)} stale")
    if stale_signals:
        reasons.append(f"{len(stale_signals)} stale signal{'' if len(stale_signals) == 1 else 's'}")
    if coverage:
        reasons.append(f"{len(coverage)} signal gap{'' if len(coverage) == 1 else 's'}")
    if free_share_zeros:
        reasons.append(f"{len(free_share_zeros)} zero Free-share signal"
                       f"{'s' if len(free_share_zeros) != 1 else ''}")
    if age is not None and age > 30:
        reasons.append(f"policy {age} days old")
    print(f"\nresearch cycle due: {'yes (' + ', '.join(reasons) + ')' if due else 'no'}")
    print(f"coefficient re-tune due: {'yes' if re_tune else 'no'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--domain", help="domain from policy.json (see --list-domains)")
    ap.add_argument("--list-domains", action="store_true",
                    help="show domains and their leaderboard tags")
    ap.add_argument("--check-policy", action="store_true",
                    help="report summary drift (ranked models without summaries, "
                         "stale summaries) and policy age; no --domain needed")
    ap.add_argument("--effort", default="measured", choices=INTENTS,
                    help="effort intent (default: measured); a rung the "
                         "model's ladder collapses discounts the output "
                         "multiplier toward glance's, in proportion to the "
                         "rung achieved")
    ap.add_argument("--profile", choices=PROFILES,
                    help="token profile (default: per-domain — authoring for "
                         "research/writing, agentic otherwise)")
    ap.add_argument("--pricing-basis", choices=BASES, default="worst",
                    help="worst=cheapest-provider-blind budget-safe projection "
                         "(default); primary=models-list figure; best=floor")
    ap.add_argument("--in-tokens", type=int, help="override profile input tokens")
    ap.add_argument("--out-tokens", type=int, help="override profile output tokens")
    ap.add_argument("--cached-share", type=float,
                    help="override profile cached share of input (0..1)")
    ap.add_argument("--tickets", type=int, default=1, help="runs to project for")
    ap.add_argument("--deal", action="store_true",
                    help="deal tickets across the eligible pool by seeded draw "
                         "from the preference-blended distribution")
    ap.add_argument("--seed", default="bind",
                    help="deal seed for reproducibility; use the project name")
    ap.add_argument("--fit", default=None, metavar="SPEC",
                    help="agent's task-fit judgments, 'mid=score,...' on 0-5; "
                         "composes as score * fit/5 (longest prefix wins)")
    ap.add_argument("--sensitive", action="store_true",
                    help="Sensitive ticket shape (the Secrets gate's verdict): "
                         "exposed candidates — trains — are excluded from the "
                         "pick and the deal, and marked with a reason in the "
                         "table; no-retention free and local routes stay in")
    ap.add_argument("--budget", type=float, help="run budget in USD")
    ap.add_argument("--top", type=int, default=8, help="ranking rows to show")
    ap.add_argument("--policy", default=DEFAULT_POLICY,
                    help="policy file: domains + baseline (default: beside script)")
    ap.add_argument("--refresh", action="store_true", help="bypass the 24h cache")
    args = ap.parse_args()

    policy: dict = {}
    if os.path.exists(args.policy):
        with open(args.policy) as f:
            policy = json.load(f)
    policy["free_models"] = load_free_models(policy)
    config = load_policy_config(policy)
    domains = policy.get("domains", {})

    if args.list_domains:
        for name, tags in domains.items():
            print(f"{name:14s} {', '.join(tags)}")
        return
    if not args.domain and not args.check_policy:
        raise SystemExit("need --domain (or --list-domains / --check-policy)")
    if args.domain and args.domain not in domains:
        raise SystemExit(
            f"no domain '{args.domain}'; known: {', '.join(domains) or 'none'}")

    models_raw = fetch_json(MODELS_URL, "models.json", auth=False, refresh=args.refresh)
    model_rows = models_raw["data"] if isinstance(models_raw, dict) else models_raw
    models = {norm_id(m["id"]): m for m in model_rows}
    by_canon = {}
    for m in models.values():
        if m.get("canonical_slug"):
            by_canon.setdefault(norm_id(m["canonical_slug"]), m)

    classif = fetch_json(CLASS_URL, "classifications.json", auth=True,
                         refresh=args.refresh)["data"]
    if args.check_policy:
        share, models = merge_free_candidates(
            {}, models, policy["free_models"], policy.get("summaries", {}))
        # Check-policy sees this invocation's same local candidates as a domain
        # run, but still performs no persistent policy update.
        served_local = probe_local_models()
        local_ids = local_candidate_ids(served_local, policy["free_models"])
        _, models = merge_local_candidates(
            share, models, served_local, policy["free_models"])
        run_check_policy(models, by_canon, classif, domains, policy,
                         args.top, args.policy,
                         args.effort, args.pricing_basis,
                         config, local_ids=local_ids)
        return

    tags = domains[args.domain]
    profile_name = args.profile or DOMAIN_PROFILE.get(args.domain, "agentic")
    in_tok, out_tok, cached = PROFILES[profile_name]
    if args.in_tokens is not None:
        in_tok = args.in_tokens
    if args.out_tokens is not None:
        out_tok = args.out_tokens
    if args.cached_share is not None:
        cached = args.cached_share

    ranks = fetch_json(RANK_URL, "rankings.json", auth=True, refresh=args.refresh)

    share, matches, known_tags = domain_candidates(classif, tags, models, by_canon)
    share, models = merge_free_candidates(
        share, models, policy["free_models"], policy.get("summaries", {}))
    # The local discovery is a live, per-run input, not persistent catalog
    # state. Only served ids matched to an Exposure=local policy entry join.
    served_local = probe_local_models()
    local_ids = local_candidate_ids(served_local, policy["free_models"])
    share, models = merge_local_candidates(
        share, models, served_local, policy["free_models"])
    for mid in share:
        if is_free_route(mid) and mid in models:
            matches[mid] = "catalog"
    missing = set(tags) - known_tags
    if missing:
        print(f"warning: tags absent from the current board: {', '.join(sorted(missing))}",
              file=sys.stderr)

    tokens_30d = collections.Counter()
    for row in ranks["data"]:
        if row["model_permaslug"] == "other":
            continue
        resolved, how = resolve_model(models, by_canon, norm_id(row["model_permaslug"]))
        key = resolved["id"] if resolved else norm_id(row["model_permaslug"])
        tokens_30d[key] += int(row["total_tokens"])

    baseline = policy.get("baseline", {})
    base_id = norm_id(baseline.get("id", ""))
    base_per = None
    if base_id in models:
        base_m = models[base_id]
        bp = price_model(base_m, endpoint_pricings(base_id, args.refresh),
                         in_tok, out_tok, cached,
                         mult_for(base_m, args.effort))
        base_per = bp[args.pricing_basis]

    print(f"# Popularity ranking: {args.domain}\n")
    age = policy_age_days(args.policy)
    age_txt = f"{age}d old" if age is not None else "unknown"
    print(f"profile={profile_name} (in={in_tok:,} out={out_tok:,} cached={cached:.0%}) "
          f"| effort={args.effort} | basis={args.pricing_basis} | policy: {age_txt} "
          f"| source: OpenRouter (openrouter.ai/rankings), as of "
          f"{classif.get('as_of', '?')}\n")
    # Protect the reserve before the deal; planned tickets are not known Free
    # demand until after the draw.
    quota = free_quota(args.refresh) or FreeQuota()
    verdict = free_quota_decision(used=quota.used, limit=quota.limit,
                                  remaining=quota.remaining,
                                  reserve=config.free_quota_reserve,
                                  planned_free=0)
    if quota.reported:
        left = quota.remaining
        if left is None and quota.limit is not None and quota.used is not None:
            left = quota.limit - quota.used
        used_txt = "?" if quota.used is None else str(quota.used)
        limit_txt = "?" if quota.limit is None else str(quota.limit)
        print(f"free quota: {used_txt}/{limit_txt} used"
              + (f" ({left} left)" if left is not None else "")
              + f" | reserve {config.free_quota_reserve} protected; "
                "plan size does not gate")
    else:
        print("free quota: unavailable | :free routes stay in the pool")
    if not verdict.eligible:
        print(f":free routes excluded from the pick and the deal — "
              f"{verdict.reason}")
    fit_map = parse_fit(args.fit) if args.fit else {}
    alpha, beta = config.alpha, config.beta
    aff = domain_weights(policy.get("hints", {}), args.domain, config.factors)
    ranked = sorted(share.items(), key=lambda kv: -kv[1])[:args.top]
    ranked_ids = {mid for mid, _ in ranked}
    ranked.extend((mid, share[mid]) for mid in sorted(share)
                  if is_free_route(mid, local=mid in local_ids)
                  and mid not in ranked_ids)

    # Admission needs the same endpoint facts that the table later displays.
    # Cache them here so an endpoint's completion cap gates Free routes and
    # flags paid rows without fetching its metadata twice.
    endpoint_cache = {}
    completion_fact_ids = {
        mid for mid in share if mid in models
        and is_free_route(mid, local=mid in local_ids)
    }
    completion_fact_ids.update(
        mid for mid, _ in ranked
        if mid in models and not is_free_route(mid, local=mid in local_ids))
    for mid in completion_fact_ids:
        endpoint_cache[mid] = ([] if _is_harness_free(mid, local_ids) else
                               endpoint_pricings(mid, args.refresh))

    # The one admission decision: the table marks with it, the deal draws
    # from it. Excluded rows stay visible; only the pick and the pool shun
    # them.
    shape = Shape(sensitive=args.sensitive, input_tokens=in_tok,
                  output_tokens=out_tok,
                  context_headroom=config.context.headroom,
                  context_margin=config.context.margin)
    decisions = {mid: admit(shape, candidate_for(
        mid, policy, local=mid in local_ids, model=models.get(mid),
        endpoints=endpoint_cache.get(mid, ()), intent=args.effort),
        quota=verdict)
        for mid in share}
    admitted = frozenset(mid for mid, d in decisions.items() if d.admitted)
    show_admission = shape.sensitive or any(
        not decisions[mid].admitted or decisions[mid].reason
        for mid, _ in ranked)
    # One eligibility pool: the deal plays it, and this run prices it, so a
    # favored model below --top still scores at the same scale as the rows
    # above it.
    pool = (eligibility_pool(share, models, aff, config.deal.eligibility_top_k,
                             admitted)
            if args.deal else [])

    if shape.sensitive:
        print("shape: sensitive — exposed candidates are excluded from the "
              "pick and the deal (marked below, never hidden)\n")
    print("| # | model | share | score |" + (" fit | adj |" if fit_map else "")
          + " 30d tokens | $/1M out (floor–worst) | $/ticket | Δ baseline | "
          "ctx | Exposure | rung |" + (" admit |" if show_admission else ""))
    print("|---" * (11 + (2 if fit_map else 0) + (1 if show_admission else 0))
          + "|")

    table_mids = {mid for mid, _ in ranked}
    priced = {}
    pers = {}
    for mid, s in ranked + [(mid, s) for mid, s in pool
                            if mid not in table_mids]:
        m = models.get(mid)
        if not m:
            continue
        if mid not in endpoint_cache:
            endpoint_cache[mid] = ([] if _is_harness_free(mid, local_ids) else
                                   endpoint_pricings(mid, args.refresh))
        eps = endpoint_cache[mid]
        pr = price_model(m, eps,
                         in_tok, out_tok, cached,
                         mult_for(m, args.effort))
        priced[mid] = pr
        pers[mid] = pr[args.pricing_basis]
    # Free routes price at the Nominal floor in the score's cost term — the
    # same floor for every Exposure — while the table's price columns keep
    # showing what the route actually costs to run.
    eff_costs = effective_costs(
        pers,
        free_risk=config.free_risk,
        free=free_route_ids(pers, policy, local=local_ids))

    rows_out = []
    for mid, s in ranked:
        if mid not in priced:
            continue
        pr = priced[mid]
        sc = task_score(s, eff_costs[mid], alpha, beta)
        fit = fit_for(mid, fit_map)
        rows_out.append((mid, s, models[mid], pr, sc, fit,
                         adjusted_score(sc, fit)))
    rows_out.sort(key=lambda r: -r[6])

    pick = None
    cheapest = None
    floor_total = 0.0
    i = 0
    for mid, s, m, pr, sc, fit, adj in rows_out:
        i += 1
        per = pr[args.pricing_basis]
        delta = f"{per / base_per:.2f}x" if base_per else "—"
        spread = "" if pr["n_eps"] <= 1 else \
            f" ({pr['n_eps']} eps)" if pr["out_max"] / max(pr["out_min"], 1e-9) < 2 else \
            f" ({pr['n_eps']} eps, wide)"
        out_cell = f"{pr['out_min']:.2f}–{pr['out_max']:.2f}{spread}"
        if pr["n_eps"] == 0:
            out_cell += " (no endpoint data)"
        free_details = free_candidate_details(mid, policy, local=mid in local_ids)
        context_length = free_details[0] if free_details else m.get("context_length")
        ctx = f"{context_length / 1024:.0f}K" if context_length else "?"
        exposure = (free_details[1] if free_details else
                    candidate_for(mid, policy, model=m).exposure
                    if is_free_route(mid, local=mid in local_ids)
                    else "—")
        ladder = effort_ladder(m)
        rung = resolve_rung(ladder, args.effort)
        if rung_collapsed(ladder, args.effort):
            rung = f"{rung} (collapsed)"
        fit_cell = ""
        if fit_map:
            shown = f"{fit:.1f}" if fit is not None else "—"
            fit_cell = f" {shown} | {adj:.2f} |"
        admit_cell = ""
        if show_admission:
            admit_cell = f" {decisions[mid].reason or '—'} |"
        print(f"| {i} | {mid} | {s:.2%} | {sc:.2f} |{fit_cell} "
              f"{tokens_30d.get(mid, 0) / 1e9:.0f}B | {out_cell} | ${per:.4f} | "
              f"{delta} | {ctx} | {exposure} | {rung} |{admit_cell}")
        if decisions[mid].admitted:
            if pick is None:
                pick = (mid, per, pr)
                floor_total = pr["best"] * args.tickets
            if cheapest is None or per < cheapest[1]:
                cheapest = (mid, per)
    excluded = sorted(mid for mid, d in decisions.items() if not d.admitted)
    for mid, s in sorted(((mid, s) for mid, s in ranked if mid not in priced),
                         key=lambda t: -t[1]):
        i += 1
        admit_cell = ""
        if show_admission:
            admit_cell = f" {decisions[mid].reason or '—'} |"
        free_details = free_candidate_details(mid, policy, local=mid in local_ids)
        context_length = free_details[0] if free_details else None
        ctx = f"{context_length / 1024:.0f}K" if context_length else "?"
        exposure = (free_details[1] if free_details else
                    resolve_exposure(mid, free_models=policy["free_models"],
                                     overrides=policy.get("exposure", {}))
                     if is_free_route(mid, local=mid in local_ids)
                     else "—")
        print(f"| {i} | {mid} | {s:.2%} | — | {tokens_30d.get(mid, 0) / 1e9:.0f}B | "
              f"— unresolved to a priced model | | | {ctx} | {exposure} | |{admit_cell}")

    odd = {k: v for k, v in matches.items() if v in ("heuristic", "unresolved")}
    if odd:
        print(f"\nnote: leaderboard rows resolved without canonical match "
              f"(price unverified or unpriced): {', '.join(sorted(odd))}")

    for kind, header in (("hints", "hints (advisory; eligibility stays popularity "
                                   "— the deal tilts by preference)"),
                         ("summaries", "summaries (task-fit context; never taste)")):
        notes = policy.get(kind, {})
        shown = [(mid, hint_for(mid, notes) if kind == "hints"
                  else summary_for_candidate(mid, policy)) for mid, _ in ranked]
        shown = [(mid, note) for mid, note in shown if note]
        if shown:
            print(f"\n{header}:")
            for mid, note in shown:
                print(f"  {mid}: {note}")

    if pick is None:
        if excluded:
            raise SystemExit(
                "shape: no candidate admitted — every ranked "
                f"candidate is excluded ({', '.join(excluded)}); drop "
                "the restrictive shape setting or pick another domain")
        raise SystemExit("domain has no ranked candidates in the model list")
    if excluded and rows_out \
            and not decisions[rows_out[0][0]].admitted:
        print(f"\nnote: top of task order {rows_out[0][0]} is excluded "
              f"({decisions[rows_out[0][0]].reason}) — not picked")
    print(f"\ndefault pick (top of task order): {pick[0]}")
    pr_pick = pick[2]
    if pr_pick.get("best_ep") and pr_pick.get("worst_ep") \
            and pr_pick["best_ep"] != pr_pick["worst_ep"]:
        print(f"route to floor: pin provider '{pr_pick['best_ep']}' via "
              f"body.provider.order (allow_fallbacks: false) — unpinned worst "
              f"endpoint is '{pr_pick['worst_ep']}' at ${pr_pick['worst']:.4f}/ticket")
    if cheapest and cheapest[0] != pick[0]:
        print(f"cheapest shown: {cheapest[0]} at ${cheapest[1]:.4f}/ticket "
              f"(budget pressure moves within the ranking, by price)")

    if args.deal:
        # Every pool member's base is the table's own scoring number: the
        # fit-adjusted task score, at score scale for the whole pool.
        fit_adjusted_task_scores = {
            mid: standing(s, eff_costs[mid], fit_for(mid, fit_map), alpha, beta)
            for mid, s in pool}
        deal_parameters = DealParameters(
            blend_weight=config.deal.blend_weight,
            top_k=config.deal.eligibility_top_k,
            seed=args.seed,
            tickets=args.tickets,
            fit_adjusted_task_scores=fit_adjusted_task_scores,
            admitted=admitted,
        )
        rows = plan_deal(share, models, aff, parameters=deal_parameters)
        print(f"\ndeal (seed '{args.seed}', blend {config.deal.blend_weight} from policy "
              f"affinity; eligibility stays popularity — the deal tilts by "
              f"preference):")
        print("| # | model | pop% | score | pref | draw% | tickets | $/ticket | "
              "subtotal |")
        print("|---|---|---|---|---|---|---|---|---|")
        total = floor_total = 0.0
        for i, row in enumerate(rows, 1):
            pr = priced.get(row["mid"])
            if pr is None:
                dm = models[row["mid"]]
                pr = price_model(dm, endpoint_pricings(row["mid"], args.refresh),
                                 in_tok, out_tok, cached,
                                 mult_for(dm, args.effort))
            per = pr[args.pricing_basis]
            total += per * row["tickets"]
            floor_total += pr["best"] * row["tickets"]
            print(f"| {i} | {row['mid']} | {row['share']:.2%} | "
                  f"{row['base']:.2f} | "
                  f"{row['pref']:.1f} | {row['draw']:.2%} | {row['tickets']} | "
                  f"${per:.4f} | ${per * row['tickets']:.4f} |")
        free_tickets, dealt_tickets = deal_free_share(
            rows, policy, local=local_ids)
        free_share = free_tickets / dealt_tickets if dealt_tickets else 0.0
        print(f"free share: {free_tickets}/{dealt_tickets} tickets "
              f"({free_share:.0%})")
    else:
        total = pick[1] * args.tickets
    print(f"projection at {args.tickets} ticket(s): ${total:.2f} "
          f"(floor ${floor_total:.2f})"
          + (f" | baseline anchor: ${base_per * args.tickets:.2f}" if base_per else ""))
    if args.budget is not None:
        verdict = "under" if total <= args.budget else "OVER"
        print(f"budget: ${args.budget:.2f} -> {verdict}")
        if total > args.budget:
            sys.exit(2)


if __name__ == "__main__":
    main()
