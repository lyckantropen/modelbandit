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
import json
import os
import random
import re
import sys
import time
import urllib.request

MODELS_URL = "https://openrouter.ai/api/v1/models"
CLASS_URL = "https://openrouter.ai/api/v1/classifications/task?window=7d"
RANK_URL = "https://openrouter.ai/api/v1/datasets/rankings-daily"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "modelbind")
CACHE_TTL = 24 * 3600

# Effort intent -> output-token multiplier. Reasoning tokens bill as completion
# tokens, so deliberation is bought in output spend — the axis that dominates
# authoring cost. Heuristic; override per run with --out-tokens.
EFFORT_MULTIPLIERS = {"glance": 0.6, "measured": 1.0, "thorough": 2.5, "exhaustive": 6.0}
INTENTS = tuple(EFFORT_MULTIPLIERS)

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


def resolve_rung(ladder: list[str], intent: str) -> str:
    n = len(ladder)
    if n == 1:
        return ladder[0]
    default_idx = ladder.index("medium") if "medium" in ladder else (n - 1 + 1) // 2
    idx = {"glance": 0, "measured": default_idx,
           "thorough": min(default_idx + 1, n - 1), "exhaustive": n - 1}[intent]
    return ladder[idx]


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


def hint_for(mid: str, hints: dict) -> str | None:
    """Longest matching prefix wins so family hints cover dated slugs.
    Entries are structured ({note, fit, evidence}) or plain notes."""
    best = None
    for key, note in hints.items():
        if mid.startswith(key) and (best is None or len(key) > len(best[0])):
            best = (key, note)
    if not best:
        return None
    entry = best[1]
    return entry.get("note", "") if isinstance(entry, dict) else entry


DEFAULT_FACTORS = {"favor_validated": 3.0, "favor_suspected": 2.0,
                   "avoid_validated": 0.3, "avoid_suspected": 0.5}


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
        out[key] = float(factors.get(f"{fit}_{evidence}",
                                     DEFAULT_FACTORS.get(f"{fit}_{evidence}", 1.0)))
    return out


def weight_for(mid: str, table: dict) -> float:
    """Longest matching prefix wins (same semantics as hint_for); 1.0 = neutral."""
    best = None
    for key, w in table.items():
        if mid.startswith(key) and (best is None or len(key) > len(best[0])):
            best = (key, w)
    return best[1] if best else 1.0


def plan_deal(share: dict, models: dict, aff: dict, *, blend_weight: float,
              top_k: int, admit: bool, seed: str, tickets: int) -> list[dict]:
    """Multi-ticket deal over the eligible pool: seeded, preference-tilted.

    Eligibility stays popularity — the top_k selectable models. When admit is
    set, ranked models the user favors (weight > 1) join the pool even below
    the cut; popularity remains the floor, so unranked or unresolved models
    never play. The draw blends popularity and preference:

        w = (1 - blend_weight) * pop + blend_weight * pref   (each normalized)

    Deterministic in seed. Returns one row per pool model:
    {"mid", "share", "pref", "draw", "tickets"}.
    """
    ranked = [(mid, s) for mid, s in sorted(share.items(), key=lambda kv: -kv[1])
              if mid in models]
    pool = ranked[:top_k]
    if admit:
        in_pool = {mid for mid, _ in pool}
        pool += [(mid, s) for mid, s in ranked[top_k:]
                 if mid not in in_pool and weight_for(mid, aff) > 1.0]
    if not pool:
        return []
    pops = [s for _, s in pool]
    prefs = [weight_for(mid, aff) for mid, _ in pool]
    pt, at = sum(pops) or 1.0, sum(prefs) or 1.0
    draws = [(1 - blend_weight) * (p / pt) + blend_weight * (a / at)
             for p, a in zip(pops, prefs)]
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
    return [{"mid": mid, "share": s, "pref": pr, "draw": d, "tickets": n}
            for (mid, s), pr, d, n in zip(pool, prefs, draws, counts)]


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


def run_check_policy(models: dict, by_canon: dict, classif: dict, domains: dict,
                     policy: dict, top: int, policy_path: str) -> None:
    summaries = policy.get("summaries", {})
    signals = {k: v for k, v in policy.get("hints", {}).items()
               if isinstance(v, dict) and v.get("fit")}
    ranked_by_domain: dict[str, list[str]] = {}
    all_ranked: set[str] = set()
    for name, tags in domains.items():
        share, _, _ = domain_candidates(classif, tags, models, by_canon)
        ranked_by_domain[name] = [mid for mid, _ in
                                  sorted(share.items(), key=lambda kv: -kv[1])[:top]]
        all_ranked.update(ranked_by_domain[name])

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
            hit = next((mid for mid in ranked if mid.startswith(key)), None)
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--domain", help="domain from policy.json (see --list-domains)")
    ap.add_argument("--list-domains", action="store_true",
                    help="show domains and their leaderboard tags")
    ap.add_argument("--check-policy", action="store_true",
                    help="report summary drift (ranked models without summaries, "
                         "stale summaries) and policy age; no --domain needed")
    ap.add_argument("--effort", default="measured", choices=INTENTS,
                    help="effort intent (default: measured)")
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
        run_check_policy(models, by_canon, classif, domains,
                         policy, args.top, args.policy)
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

    mult = EFFORT_MULTIPLIERS[args.effort]
    base = policy.get("baseline", {})
    base_id = norm_id(base.get("id", ""))
    base_per = None
    if base_id in models:
        bp = price_model(models[base_id],
                         endpoint_pricings(base_id, args.refresh),
                         in_tok, out_tok, cached, mult)
        base_per = bp[args.pricing_basis]

    print(f"# Popularity ranking: {args.domain}\n")
    age = policy_age_days(args.policy)
    age_txt = f"{age}d old" if age is not None else "unknown"
    print(f"profile={profile_name} (in={in_tok:,} out={out_tok:,} cached={cached:.0%}) "
          f"| effort={args.effort} | basis={args.pricing_basis} | policy: {age_txt} "
          f"| source: OpenRouter (openrouter.ai/rankings), as of "
          f"{classif.get('as_of', '?')}\n")
    print("| # | model | share | 30d tokens | $/1M out (floor–worst) | "
          "$/ticket | Δ baseline | rung |")
    print("|---|---|---|---|---|---|---|---|")

    ranked = sorted(share.items(), key=lambda kv: -kv[1])[:args.top]
    pick = None
    cheapest = None
    floor_total = 0.0
    priced = {}
    for i, (mid, s) in enumerate(ranked, 1):
        m = models.get(mid)
        if not m:
            print(f"| {i} | {mid} | {s:.2%} | {tokens_30d.get(mid, 0) / 1e9:.0f}B | "
                  f"— unresolved to a priced model | | | |")
            continue
        pr = price_model(m, endpoint_pricings(mid, args.refresh),
                         in_tok, out_tok, cached, mult)
        priced[mid] = pr
        per = pr[args.pricing_basis]
        delta = f"{per / base_per:.2f}x" if base_per else "—"
        spread = "" if pr["n_eps"] <= 1 else \
            f" ({pr['n_eps']} eps)" if pr["out_max"] / max(pr["out_min"], 1e-9) < 2 else \
            f" ({pr['n_eps']} eps, wide)"
        out_cell = f"{pr['out_min']:.2f}–{pr['out_max']:.2f}{spread}"
        if pr["n_eps"] == 0:
            out_cell += " (no endpoint data)"
        print(f"| {i} | {mid} | {s:.2%} | {tokens_30d.get(mid, 0) / 1e9:.0f}B | "
              f"{out_cell} | ${per:.4f} | {delta} | "
              f"{resolve_rung(effort_ladder(m), args.effort)} |")
        if pick is None:
            pick = (mid, per, pr)
            floor_total = pr["best"] * args.tickets
        if cheapest is None or per < cheapest[1]:
            cheapest = (mid, per)

    odd = {k: v for k, v in matches.items() if v in ("heuristic", "unresolved")}
    if odd:
        print(f"\nnote: leaderboard rows resolved without canonical match "
              f"(price unverified or unpriced): {', '.join(sorted(odd))}")

    for kind, header in (("hints", "hints (advisory; eligibility stays popularity "
                                   "— the deal tilts by preference)"),
                         ("summaries", "summaries (context only; same rule)")):
        notes = policy.get(kind, {})
        shown = [(mid, hint_for(mid, notes)) for mid, _ in ranked]
        shown = [(mid, note) for mid, note in shown if note]
        if shown:
            print(f"\n{header}:")
            for mid, note in shown:
                print(f"  {mid}: {note}")

    if pick is None:
        raise SystemExit("domain has no ranked candidates in the model list")
    print(f"\ndefault pick (rank 1): {pick[0]}")
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
        aff_conf = policy.get("affinity", {})
        blend_weight = float(aff_conf.get("blend_weight", 0.5))
        rows = plan_deal(share, models,
                         domain_weights(policy.get("hints", {}), args.domain,
                                        aff_conf.get("factors", {})),
                         blend_weight=blend_weight,
                         top_k=int(aff_conf.get("eligibility_top_k", 5)),
                         admit=bool(aff_conf.get("admit_favored_outside_top_k", True)),
                         seed=args.seed, tickets=args.tickets)
        print(f"\ndeal (seed '{args.seed}', blend {blend_weight} from policy "
              f"affinity; eligibility stays popularity — the deal tilts by "
              f"preference):")
        print("| # | model | pop% | pref | draw% | tickets | $/ticket | subtotal |")
        print("|---|---|---|---|---|---|---|---|")
        total = floor_total = 0.0
        for i, row in enumerate(rows, 1):
            pr = priced.get(row["mid"])
            if pr is None:
                pr = price_model(models[row["mid"]],
                                 endpoint_pricings(row["mid"], args.refresh),
                                 in_tok, out_tok, cached, mult)
            per = pr[args.pricing_basis]
            total += per * row["tickets"]
            floor_total += pr["best"] * row["tickets"]
            print(f"| {i} | {row['mid']} | {row['share']:.2%} | {row['pref']:.1f} | "
                  f"{row['draw']:.2%} | {row['tickets']} | ${per:.4f} | "
                  f"${per * row['tickets']:.4f} |")
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
