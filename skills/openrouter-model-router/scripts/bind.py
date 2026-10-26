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
import datetime
import json
import os
import random
import re
import sys
import textwrap
import time
import urllib.request

MODELS_URL = "https://openrouter.ai/api/v1/models"
CLASS_URL = "https://openrouter.ai/api/v1/classifications/task?window=7d"
RANK_URL = "https://openrouter.ai/api/v1/datasets/rankings-daily"
BENCHMARKS_URL = "https://openrouter.ai/api/v1/benchmarks"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "modelbind")
CACHE_TTL = 24 * 3600

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


def fetch_json(url: str, cache_name: str, *, auth: bool, refresh: bool):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_name)
    if not refresh and os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < CACHE_TTL:
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
        if os.path.exists(cache_path):
            print(f"warning: fetch failed ({exc}); using stale cache", file=sys.stderr)
            with open(cache_path) as f:
                return json.load(f)
        raise SystemExit(f"cannot reach {url}: {exc}")
    with open(cache_path, "w") as f:
        json.dump(data, f)
    return data


def norm_id(model_id: str) -> str:
    return model_id.removeprefix("openrouter/")


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
class DealParameters:
    blend_weight: float
    top_k: int
    seed: str
    tickets: int
    fit_adjusted_task_scores: dict | None = None


@dataclasses.dataclass(frozen=True)
class PolicyConfig:
    alpha: float
    beta: float
    thresholds: dict
    factors: dict
    deal: DealPolicy


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
    )


def task_score(share: float, cost: float, alpha: float, beta: float) -> float:
    """share^alpha / cost^beta. cost must already be floored (see
    effective_costs) so free models cannot win on division alone."""
    return share ** alpha / cost ** beta


def effective_costs(costs: dict) -> dict:
    """Price free routes at the pool's cheapest paid ticket, never zero."""
    positive = [v for v in costs.values() if v > 0]
    floor = min(positive) if positive else 1.0
    return {mid: (v if v > 0 else floor) for mid, v in costs.items()}


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


def popularity_ranking(share: dict, models: dict) -> list[tuple[str, float]]:
    """Share-ranked selectable models: the popularity order every pool starts
    from. Unranked or unresolved models never play, so they drop out here."""
    return [(mid, s) for mid, s in sorted(share.items(), key=lambda kv: -kv[1])
            if mid in models]


def eligibility_pool(share: dict, models: dict, aff: dict,
                     top_k: int) -> list[tuple[str, float]]:
    """The deal's players, computed once for every consumer.

    Eligibility stays popularity: the top_k selectable models, plus ranked
    models the user favors (weight > 1) below the cut. Returns [(mid, share)]
    in popularity order; the candidate table prices these same players.
    """
    ranked = popularity_ranking(share, models)
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
    Returns one row per pool model:
    {"mid", "share", "base", "pref", "draw", "tickets"}.
    """
    blend_weight = parameters.blend_weight
    seed = parameters.seed
    tickets = parameters.tickets
    pool = eligibility_pool(share, models, aff, parameters.top_k)
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
            resolved, how = resolve_model(models, by_canon, norm_id(m["id"]))
            key = resolved["id"] if resolved else norm_id(m["id"])
            matches[key] = how if resolved else "unresolved"
            share[key] += c["usage_share"] * m["tag_usage_share"]
    return share, matches, known_tags


def drift_keys(all_ranked: set, summaries: dict, signals: dict):
    """The check's gap/stale derivation, shared by the scope report: ranked
    mids without a summary; summary and signal keys with no current rank
    among the top-cut mids."""
    gaps = sorted(mid for mid in all_ranked if not hint_for(mid, summaries))
    stale = sorted(k for k in summaries
                   if not any(mid.startswith(k) for mid in all_ranked))
    stale_signals = sorted(k for k in signals
                           if not any(mid.startswith(k) for mid in all_ranked))
    return gaps, stale, stale_signals


def board_hit(board: list, key: str, exact: bool):
    """(position, size) of the key's best match on a full share board, or
    None. Positions are over the whole board, not the --top cut, so a
    below-cut rank stays visible."""
    for pos, (mid, _) in enumerate(board, 1):
        if (mid == key) if exact else mid.startswith(key):
            return pos, len(board)
    return None


def catalog_row(model: dict | None) -> str:
    """Created date (ISO), context window and per-1M list price."""
    if model is None:
        return "not in model list"
    created = model.get("created")
    try:
        created_txt = datetime.datetime.fromtimestamp(
            int(created), datetime.timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        created_txt = "?"
    ctx = model.get("context_length")
    ctx_txt = f"{ctx / 1024:.0f}K" if ctx else "?"
    try:
        pricing = model["pricing"]
        price_txt = (f"${per_million(pricing['prompt']):.2f}/"
                     f"${per_million(pricing['completion']):.2f} per 1M in/out")
    except (KeyError, TypeError, ValueError):
        price_txt = "price ?"
    return f"created {created_txt}, context {ctx_txt}, {price_txt}"


def scope_facts(key: str, exact: bool, models: dict, by_canon: dict,
                classif: dict, domains: dict, share_by_domain: dict,
                ranks) -> list[str]:
    """The two wrapped fact lines under one gap/stale bullet.

    ranks: full-board per-domain positions (a stale key can only sit below
    the cut; a gap's own in-cut domains come with the bullet), then
    non-domain task tags, or the explicit absent phrase when nowhere.
    catalog: the model row plus daily-token window totals, the window taken
    from the rankings feed's meta when it states one. Facts only — the
    refresh-or-retire judgment stays human.
    """
    board = {name: sorted(share.items(), key=lambda kv: -kv[1])
             for name, share in share_by_domain.items()}
    dom_parts = [f"{name} #{hit[0]}/{hit[1]}"
                 for name in domains
                 if (hit := board_hit(board[name], key, exact))]
    domain_tags = {t for tags in domains.values() for t in tags}
    other_parts = []
    for c in classif["classifications"]:
        if c["tag"] in domain_tags:
            continue
        entries = sorted(c["models"], key=lambda m: -m["tag_usage_share"])
        for pos, m in enumerate(entries, 1):
            resolved, _ = resolve_model(models, by_canon, norm_id(m["id"]))
            mid = resolved["id"] if resolved else norm_id(m["id"])
            if (mid == key) if exact else mid.startswith(key):
                other_parts.append(f"{c['tag']} #{pos}/{len(entries)}")
                break
    if dom_parts or other_parts:
        parts = list(dom_parts)
        if other_parts:
            parts.append("other tags: " + ", ".join(other_parts))
        ranks_txt = "ranks: " + ", ".join(parts)
    else:
        ranks_txt = (f"ranks: absent from all {len(classif['classifications'])}"
                     f" tags and all {len(domains)} domains")

    model, _ = resolve_model(models, by_canon, key)
    if model is None and not exact:
        # Prefix keys (stale bullets) may resolve to their first listed
        # sibling; an exact gap mid never borrows another row's catalog.
        cands = sorted(mid for mid in models if mid.startswith(key))
        model = models[cands[0]] if cands else None
    tokens, days = 0, set()
    rows = ranks.get("data", []) if isinstance(ranks, dict) else (ranks or [])
    for row in rows:
        slug = norm_id(str(row.get("model_permaslug", "")))
        if slug == "other":
            continue
        resolved, _ = resolve_model(models, by_canon, slug)
        mid = resolved["id"] if resolved else slug
        if (mid == key) if exact else mid.startswith(key):
            tokens += int(row.get("total_tokens") or 0)
            if row.get("date"):
                days.add(row["date"])
    meta = ranks.get("meta", {}) if isinstance(ranks, dict) else {}
    span = (f"{meta['start_date']}..{meta['end_date']}"
            if meta.get("start_date") and meta.get("end_date") else "")
    window = None
    if span:
        # The feed's own window: inclusive of both end dates.
        try:
            window = ((datetime.date.fromisoformat(meta["end_date"])
                       - datetime.date.fromisoformat(meta["start_date"])).days + 1)
        except ValueError:
            window = None
    if window is None:
        # No meta (or unparseable dates): the observable window is the set of
        # days the feed itself carries rows for, so the denominator is that
        # count, "D/D days" — never a hardcoded 30.
        window = len({row.get("date") for row in rows if row.get("date")})
    window_txt = (f"window {span}: " if span else "window: ") \
        + f"{tokens / 1e12:.2f}T tokens, {len(days)}/{window} days"

    lines = []
    for text in (ranks_txt, f"catalog: {catalog_row(model)}, {window_txt}"):
        lines.extend(textwrap.wrap(text, width=88,
                                   initial_indent="  ", subsequent_indent="    "))
    return lines


def domain_rankings(classif: dict, domains: dict, models: dict,
                    by_canon: dict, top: int):
    """Per-domain share boards and their top-cut ranked mids, in popularity
    order — the shared input for the check's drift derivation and the
    anchors scope."""
    share_by_domain: dict[str, dict] = {}
    ranked_by_domain: dict[str, list[str]] = {}
    for name, tags in domains.items():
        share, _, _ = domain_candidates(classif, tags, models, by_canon)
        share_by_domain[name] = share
        ranked_by_domain[name] = [mid for mid, _ in
                                  sorted(share.items(), key=lambda kv: -kv[1])[:top]]
    return share_by_domain, ranked_by_domain


def run_check_policy(models: dict, by_canon: dict, classif: dict, domains: dict,
                     policy: dict, top: int, policy_path: str,
                     intent: str, basis: str, config: PolicyConfig,
                     ranks=None) -> None:
    summaries = policy.get("summaries", {})
    signals = {k: v for k, v in policy.get("hints", {}).items()
               if isinstance(v, dict) and v.get("fit")}
    pool_k = config.deal.eligibility_top_k
    share_by_domain, ranked_by_domain = domain_rankings(
        classif, domains, models, by_canon, top)
    all_ranked: set[str] = set()
    for ranked in ranked_by_domain.values():
        all_ranked.update(ranked)
    # The deal's players: the eligibility top-K of each domain, plus ranked
    # models the user favors (weight > 1) below the cut — the same pool
    # plan_deal admits. Coverage is judged only for those.
    eligible = set()
    for name in domains:
        table = domain_weights(signals, name, config.factors)
        eligible.update(mid for mid, _ in
                        eligibility_pool(share_by_domain[name], models,
                                         table, pool_k))

    gaps, stale, stale_signals = drift_keys(all_ranked, summaries, signals)

    def emit_scope_facts(key: str, exact: bool) -> None:
        if ranks is None:
            return
        for line in scope_facts(key, exact, models, by_canon, classif,
                                domains, share_by_domain, ranks):
            print(line)

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
        if mid != "— none":
            emit_scope_facts(mid, exact=True)
    print("\n## Stale summaries (no current rank)")
    for key in stale or ["— none"]:
        gone = "" if any(m.startswith(key) for m in models) else " — not in model list"
        print(f"- {key}{gone}")
        if key != "— none":
            emit_scope_facts(key, exact=False)
    print("\n## Stale signals (fit keys with no current rank)")
    for key in stale_signals or ["— none"]:
        print(f"- {key}")
        if key != "— none":
            emit_scope_facts(key, exact=False)
    print("\n## Signal coverage gaps (opinion elsewhere, silent here)")
    for line in sorted(coverage) or ["— none"]:
        print(f"- {line}")

    alpha, beta = config.alpha, config.beta
    thresholds = config.thresholds
    print(f"\n## Score balance (top-{pool_k} pool, {basis} basis)")
    re_tune = False
    judged = False
    for name in domains:
        pool = popularity_ranking(share_by_domain[name], models)[:pool_k]
        if not pool:
            continue
        if len(pool) < 3:
            # Below three candidates the balance criterion has nothing to
            # judge: a one-candidate pool is 100% top mass by definition,
            # not a tuning failure. Report and never trip the verdict.
            print(f"- {name}: {len(pool)} candidate"
                  f"{'s' if len(pool) != 1 else ''} — balance not judgeable "
                  f"(needs 3+)")
            continue
        in_tok, out_tok, cached = PROFILES[DOMAIN_PROFILE.get(name, "agentic")]
        costs = {}
        for mid, s in pool:
            m_mult = mult_for(models[mid], intent)
            pricing = price_model(models[mid], endpoint_pricings(mid, False),
                                  in_tok, out_tok, cached, m_mult)
            costs[mid] = pricing[basis]
        eff = effective_costs(costs)
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
        print("(no domain with 3+ candidates — balance not judgeable)")

    due = bool(gaps) or bool(stale) or bool(stale_signals) or bool(coverage) \
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
    if age is not None and age > 30:
        reasons.append(f"policy {age} days old")
    print(f"\nresearch cycle due: {'yes (' + ', '.join(reasons) + ')' if due else 'no'}")
    print(f"coefficient re-tune due: {'yes' if re_tune else 'no'}")


# The combined benchmarks feed's top-level meta carries source/citation null
# (it mixes all three), so per-source headers use the known citation strings
# and the feed-level as-of is stated once, in the main header.
SOURCE_ORDER = ("artificial-analysis", "design-arena", "openrouter")
SOURCE_HEADINGS = {
    "artificial-analysis": "Artificial Analysis",
    "design-arena": "Design Arena",
    "openrouter": "OpenRouter evals",
}
SOURCE_CITATIONS = {
    "artificial-analysis":
        "Source: Artificial Analysis (artificialanalysis.ai) via OpenRouter "
        "(openrouter.ai/rankings).",
    "design-arena":
        "Source: Design Arena (www.designarena.ai) via OpenRouter "
        "(openrouter.ai/rankings).",
    "openrouter":
        "Source: OpenRouter evals (openrouter.ai) via OpenRouter "
        "(openrouter.ai/rankings).",
}
SOURCE_COLUMNS = {
    "artificial-analysis":
        "| model | intelligence | coding | agentic | $/1M in/out |",
    "design-arena":
        "| model | arena | category | elo | win rate | $/1M in/out |",
    "openrouter":
        "| model | benchmark | accuracy | cost/task | latency (ms) | $/1M in/out |",
}


def anchor_scope(explicit: list, models: dict, by_canon: dict, classif: dict,
                 domains: dict, policy: dict, top: int) -> list[str]:
    """The anchor model set: explicit ids when given (deduplicated, in given
    order), else the check's drift set — gaps, then stale summaries, then
    stale signals, via the shared drift_keys helper.

    Explicit ids resolve through resolve_model like every other id in this
    file, so a dated-catalog form (…-0813) lands on the same id a gap would
    carry; an id that resolves to nothing keeps its given form and falls
    through to the no-rows line in the anchors output."""
    if explicit:
        out, seen = [], set()
        for mid in explicit:
            key = norm_id(mid)
            resolved, _ = resolve_model(models, by_canon, key)
            if resolved:
                key = resolved["id"]
            if key not in seen:
                seen.add(key)
                out.append(key)
        return out
    summaries = policy.get("summaries", {})
    signals = {k: v for k, v in policy.get("hints", {}).items()
               if isinstance(v, dict) and v.get("fit")}
    _, ranked_by_domain = domain_rankings(classif, domains, models, by_canon, top)
    all_ranked = {mid for ranked in ranked_by_domain.values() for mid in ranked}
    gaps, stale, stale_signals = drift_keys(all_ranked, summaries, signals)
    out, seen = [], set()
    for mid in (*gaps, *stale, *stale_signals):
        if mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


def anchor_cell(value, fmt) -> str:
    """Formatted number, or an em dash for missing/null — never 0."""
    return fmt(value) if isinstance(value, (int, float)) and not \
        isinstance(value, bool) else "—"


def anchor_price(row: dict) -> str:
    """Per-1M in/out price when the source provides pricing, else missing."""
    try:
        pricing = row["pricing"]
        return (f"${per_million(pricing['prompt']):.2f}/"
                f"${per_million(pricing['completion']):.2f}")
    except (KeyError, TypeError, ValueError):
        return "—"


def anchor_row(source: str, row: dict) -> str:
    """One table row in its source's own schema. The slug (dated permaslug)
    is what the feed carries; the scope id that matched it is implicit in the
    row's position."""
    slug = norm_id(str(row.get("model_permaslug", "")))
    if source == "artificial-analysis":
        cells = [anchor_cell(row.get(k), lambda v: f"{v:.1f}")
                 for k in ("intelligence_index", "coding_index",
                           "agentic_index")]
    elif source == "design-arena":
        cells = [str(row.get("arena", "?")), str(row.get("category", "?")),
                 anchor_cell(row.get("elo"), lambda v: f"{v:.0f}"),
                 anchor_cell(row.get("win_rate"), lambda v: f"{v:g}%")]
    else:  # openrouter
        # Latency replaces last run: the evals table's substance is accuracy,
        # cost and speed, and with latency added a seventh column read
        # unwieldy next to the other sources' five and six.
        cells = [str(row.get("benchmark_type", "?")),
                 anchor_cell(row.get("accuracy"), lambda v: f"{v:.1%}"),
                 anchor_cell(row.get("avg_cost_per_task"),
                             lambda v: f"${v:.4f}"),
                 anchor_cell(row.get("avg_latency_per_task_ms"),
                             lambda v: f"{v:.0f}")]
    return f"| {slug} | " + " | ".join(cells) + f" | {anchor_price(row)} |"


def run_anchors(explicit: list, models: dict, by_canon: dict, classif: dict,
                domains: dict, policy: dict, top: int, refresh: bool) -> None:
    """First-party benchmark anchors for the scope: one unfiltered,
    authenticated, cached fetch of the combined feed; one table per source
    in that source's own schema, rows in scope order; a trailing line naming
    scoped models the feed does not cover. Facts only — nothing persists."""
    scope = anchor_scope(explicit, models, by_canon, classif, domains,
                         policy, top)
    feed = fetch_json(BENCHMARKS_URL, "benchmarks.json", auth=True,
                      refresh=refresh)
    rows = feed.get("data", []) if isinstance(feed, dict) else (feed or [])
    meta = feed.get("meta", {}) if isinstance(feed, dict) else {}

    # Each feed row joins the first scope id it prefixes-matches (family
    # semantics, as for the policy keys); buckets keep feed order within
    # their id, so iterating scope order yields scope-ordered tables. Every
    # scope id matches on its given form and its canonical_slug: an id given
    # in dated-catalog form (deepseek/...-0813) reaches its permaslug rows
    # (…-20260813) through the same resolution the rest of the file uses.
    keys: dict[int, tuple] = {}
    for idx, sid in enumerate(scope):
        resolved, _ = resolve_model(models, by_canon, sid)
        canon = norm_id(resolved["canonical_slug"]) \
            if resolved and resolved.get("canonical_slug") else None
        keys[idx] = (sid, canon) if canon and canon != sid else (sid,)
    assigned: dict[tuple, list] = {}
    for row in rows:
        slug = norm_id(str(row.get("model_permaslug", "")))
        for idx, sid in enumerate(scope):
            if any(slug.startswith(k) for k in keys[idx]):
                assigned.setdefault((row.get("source"), idx), []).append(row)
                break
    matched = {idx for _, idx in assigned}

    print("# Benchmark anchors")
    print(f"feed as of {meta.get('as_of', '?')} — {len(matched)} of the "
          f"scope's models have rows; the feed carries "
          f"{meta.get('model_count', '?')} models")
    for source in SOURCE_ORDER:
        print(f"\n## {SOURCE_HEADINGS[source]}")
        print(f"{SOURCE_CITATIONS[source]}\n")
        body = [anchor_row(source, row)
                for idx, _ in enumerate(scope)
                for row in assigned.get((source, idx), [])]
        if body:
            print(SOURCE_COLUMNS[source])
            print("|---" * (SOURCE_COLUMNS[source].count("|") - 1) + "|")
            print("\n".join(body))
    missing = [sid for idx, sid in enumerate(scope) if idx not in matched]
    print(f"\nno benchmark rows: {', '.join(missing) if missing else '— none'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--domain", help="domain from policy.json (see --list-domains)")
    ap.add_argument("--list-domains", action="store_true",
                    help="show domains and their leaderboard tags")
    ap.add_argument("--check-policy", action="store_true",
                    help="report summary drift (ranked models without summaries, "
                         "stale summaries) and policy age; no --domain needed")
    ap.add_argument("--scope", action="store_true",
                    help="with the policy check (implied), print two fact lines "
                         "under each gap, stale-summary and stale-signal "
                         "bullet: where the model still ranks and its catalog "
                         "row with daily-token window totals; facts only")
    ap.add_argument("--anchors", nargs="*", metavar="MODEL_ID", default=None,
                    help="render first-party benchmark anchors as one table "
                         "per source (Artificial Analysis, Design Arena, "
                         "OpenRouter evals) for the refresh scope — the "
                         "policy's gaps then stale entries — or, when model "
                         "ids are given, for exactly those; one cached fetch "
                         "of the combined benchmarks feed; facts only")
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
    config = load_policy_config(policy)
    domains = policy.get("domains", {})

    if args.list_domains:
        for name, tags in domains.items():
            print(f"{name:14s} {', '.join(tags)}")
        return
    if (not args.domain and not args.check_policy and not args.scope
            and args.anchors is None):
        raise SystemExit("need --domain (or --list-domains / --check-policy "
                         "/ --scope / --anchors)")
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
    if args.anchors is not None:
        run_anchors(args.anchors, models, by_canon, classif, domains, policy,
                    args.top, args.refresh)
        return
    if args.check_policy or args.scope:
        # The scope path needs the daily token rankings for window totals; the
        # bare check never consults them and stays one fetch lighter.
        ranks = fetch_json(RANK_URL, "rankings.json", auth=True,
                           refresh=args.refresh) if args.scope else None
        run_check_policy(models, by_canon, classif, domains, policy,
                         args.top, args.policy,
                         args.effort, args.pricing_basis,
                         config, ranks=ranks)
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
    fit_map = parse_fit(args.fit) if args.fit else {}
    alpha, beta = config.alpha, config.beta
    aff = domain_weights(policy.get("hints", {}), args.domain, config.factors)
    # One eligibility pool: the deal plays it, and this run prices it, so a
    # favored model below --top still scores at the same scale as the rows
    # above it.
    pool = (eligibility_pool(share, models, aff, config.deal.eligibility_top_k)
            if args.deal else [])

    print("| # | model | share | score |" + (" fit | adj |" if fit_map else "")
          + " 30d tokens | $/1M out (floor–worst) | $/ticket | Δ baseline | "
          "ctx | rung |")
    print("|---" * (10 + (2 if fit_map else 0)) + "|")

    ranked = sorted(share.items(), key=lambda kv: -kv[1])[:args.top]
    table_mids = {mid for mid, _ in ranked}
    priced = {}
    pers = {}
    for mid, s in ranked + [(mid, s) for mid, s in pool
                            if mid not in table_mids]:
        m = models.get(mid)
        if not m:
            continue
        pr = price_model(m, endpoint_pricings(mid, args.refresh),
                         in_tok, out_tok, cached,
                         mult_for(m, args.effort))
        priced[mid] = pr
        pers[mid] = pr[args.pricing_basis]
    eff_costs = effective_costs(pers)

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
        ctx = f"{m['context_length'] / 1024:.0f}K" if m.get("context_length") else "?"
        ladder = effort_ladder(m)
        rung = resolve_rung(ladder, args.effort)
        if rung_collapsed(ladder, args.effort):
            rung = f"{rung} (collapsed)"
        fit_cell = ""
        if fit_map:
            shown = f"{fit:.1f}" if fit is not None else "—"
            fit_cell = f" {shown} | {adj:.2f} |"
        print(f"| {i} | {mid} | {s:.2%} | {sc:.2f} |{fit_cell} "
              f"{tokens_30d.get(mid, 0) / 1e9:.0f}B | {out_cell} | ${per:.4f} | "
              f"{delta} | {ctx} | {rung} |")
        if pick is None:
            pick = (mid, per, pr)
            floor_total = pr["best"] * args.tickets
        if cheapest is None or per < cheapest[1]:
            cheapest = (mid, per)
    for mid, s in sorted(((mid, s) for mid, s in ranked if mid not in priced),
                         key=lambda t: -t[1]):
        i += 1
        print(f"| {i} | {mid} | {s:.2%} | — | {tokens_30d.get(mid, 0) / 1e9:.0f}B | "
              f"— unresolved to a priced model | | | |")

    odd = {k: v for k, v in matches.items() if v in ("heuristic", "unresolved")}
    if odd:
        print(f"\nnote: leaderboard rows resolved without canonical match "
              f"(price unverified or unpriced): {', '.join(sorted(odd))}")

    for kind, header in (("hints", "hints (advisory; eligibility stays popularity "
                                   "— the deal tilts by preference)"),
                         ("summaries", "summaries (task-fit context; never taste)")):
        notes = policy.get(kind, {})
        shown = [(mid, hint_for(mid, notes)) for mid, _ in ranked]
        shown = [(mid, note) for mid, note in shown if note]
        if shown:
            print(f"\n{header}:")
            for mid, note in shown:
                print(f"  {mid}: {note}")

    if pick is None:
        raise SystemExit("domain has no ranked candidates in the model list")
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
