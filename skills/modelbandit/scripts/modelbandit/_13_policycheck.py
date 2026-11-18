from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
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


def domain_rankings(classif: dict, domains: dict, models: dict,
                    by_canon: dict, top: int, config: PolicyConfig,
                    policy: dict, local_ids=(), posture: str = "open",
                    intent: str = "measured", loopback: bool = True):
    """Per-domain share boards (free candidates merged, zone-filtered — the
    same source the check and a ranking run judge), their top-cut ranked mids
    and the union of ranked mids. The shared input for the check's drift
    derivation, the --scope facts and the --anchors scope. The loopback fact
    reaches the zone filter so the candidates it builds read as the run's."""
    summaries = policy.get("summaries", {})
    local_ids = set(local_ids)
    share_by_domain: dict[str, dict] = {}
    ranked_by_domain: dict[str, list[str]] = {}
    all_ranked: set[str] = set()
    for name, tags in domains.items():
        share, _, _ = domain_candidates(classif, tags, models, by_canon)
        share, _ = merge_free_candidates(
            share, models, policy.get("free_models", {}), summaries,
            inheritance=config.free_share_inheritance)
        for mid in local_ids:
            if mid in models:
                share.setdefault(mid, 0.0)
        share = filter_zone_candidates(
            share, models, policy, local_ids=local_ids,
            posture=posture, intent=intent, loopback=loopback)
        share_by_domain[name] = share
        ranked_by_domain[name] = [mid for mid, _ in
                                  sorted(share.items(), key=lambda kv: -kv[1])[:top]]
        all_ranked.update(ranked_by_domain[name])
    return share_by_domain, ranked_by_domain, all_ranked


def drift_keys(all_ranked: set, summaries: dict, signals: dict,
               free_models: dict | None = None):
    """The check's Gap/Stale derivation, shared by the scope report and the
    anchors scope: ranked mids without a summary; summary and signal keys
    with no current rank among the top-cut mids.

    A Free route's ``summary_ref`` is how its family summary
    reaches it everywhere else in this file — the summary resolver
    (``_free_summary``) and the table's summary column
    (``summary_for_candidate``) both resolve it — and an ``opencode/*`` or
    local id can never prefix-match the family key. So the ref counts here
    too: a Gap is a summary the route does not have, not one spelled in
    another namespace. Symmetrically, a summary key a ranked route
    references is not stale — it is still serving. An unresolvable ref
    silences neither side."""
    free_models = free_models or {}

    def catalog_ref(mid: str) -> str | None:
        """The resolvable family summary a ranked Free route stands on,
        gated the way ``summary_for_candidate`` gates it: a paid mid sharing
        the entry's prefix does not borrow the ref."""
        match = longest_prefix_match(mid, free_models)
        if match is None:
            return None
        if not (is_free_route(mid) or match[1].get("exposure") == "local"):
            return None
        ref = match[1].get("summary_ref")
        return ref if isinstance(ref, str) and summaries.get(ref) else None

    referenced = {ref for mid in all_ranked
                  if (ref := catalog_ref(mid)) is not None}
    gaps = sorted(mid for mid in all_ranked
                  if not hint_for(mid, summaries) and catalog_ref(mid) is None)
    stale = sorted(k for k in summaries
                   if k not in referenced
                   and not any(mid.startswith(k) for mid in all_ranked))
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


def anchor_scope(explicit: list, models: dict, by_canon: dict, classif: dict,
                 domains: dict, policy: dict, top: int, config: PolicyConfig,
                 posture: str) -> list[str]:
    """The anchor model set: explicit ids when given (deduplicated, in given
    order), else the check's drift set — gaps, then stale summaries, then
    stale signals, via the shared drift_keys helper over the same
    free-merged, zone-filtered boards the check judges.

    The scope is deliberately not the run's full posture: it judges with
    empty locals and measured intent, stated here rather than smuggled in
    through the context. Explicit ids resolve through resolve_model like
    every other id in this file, so a dated-catalog form (…-0813) lands on
    the same id a gap would carry; an id that resolves to nothing keeps its
    given form and falls through to the no-rows line in the anchors
    output."""
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
    _, _, all_ranked = domain_rankings(
        classif, domains, models, by_canon, top, config, policy,
        local_ids=(), posture=posture, intent="measured")
    gaps, stale, stale_signals = drift_keys(
        all_ranked, summaries, signals, policy.get("free_models", {}))
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
                domains: dict, policy: dict, top: int, refresh: bool,
                config: PolicyConfig, ctx: RunContext) -> None:
    """First-party benchmark anchors for the scope: one unfiltered,
    authenticated, cached fetch of the combined feed; one table per source
    in that source's own schema, rows in scope order; a trailing line naming
    scoped models the feed does not cover. Facts only — nothing persists."""
    scope = anchor_scope(explicit, models, by_canon, classif, domains,
                         policy, top, config, posture=ctx.zone.posture)
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


def run_check_policy(models: dict, by_canon: dict, classif: dict, domains: dict,
                     policy: dict, top: int, policy_path: str,
                     basis: str, config: PolicyConfig,
                     ctx: RunContext, material_sensitive: bool = False,
                     ranks=None, local_listing=None) -> None:
    # The posture facts travel as one context; bind the names the body
    # already reads, so the single source stays visible at the signature.
    zone, local_ids = ctx.zone, ctx.local_ids
    roster, loopback, intent = ctx.roster, ctx.loopback, ctx.intent
    summaries = policy.get("summaries", {})
    signals = {k: v for k, v in policy.get("hints", {}).items()
               if isinstance(v, dict) and v.get("fit")}
    pool_k = config.eligibility_top_k
    # The same source filter as a ranking run: a route the zone forbids is
    # not a candidate here either, so the diagnostic deal plays only what may
    # serve and no Free-share signal is claimed for routes that cannot draw.
    share_by_domain, ranked_by_domain, all_ranked = domain_rankings(
        classif, domains, models, by_canon, top, config, policy,
        local_ids=local_ids, posture=zone.posture, intent=intent,
        loopback=loopback)
    # The deal's players: the eligibility top-K of each domain, plus ranked
    # models the user favors (weight > 1) below the cut — the same pool
    # plan_deal admits. Coverage is judged only for those.
    eligible = set()
    for name in domains:
        table = domain_weights(signals, name, config.factors)
        eligible.update(mid for mid, _ in
                        eligibility_pool(share_by_domain[name], models,
                                         table, pool_k, local=local_ids))

    gaps, stale, stale_signals = drift_keys(
        all_ranked, summaries, signals, policy.get("free_models", {}))

    # The --scope report also prints two fact lines under each gap/stale
    # bullet — where the model still ranks, and its catalog row with daily
    # token-window totals — fed by the daily-token rankings the scope path
    # fetches. The bare check passes ranks=None and stays one fetch lighter.
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

    # The safe diagnostic Deal is report-only. Its per-shape history is cache
    # data and cannot mutate policy or eligibility. The deal itself judges the
    # run's own shape - one serving fact, one answer, whichever surface asks -
    # while the record carries that shape honestly in its key.
    free_share_zeros = []
    for name in domains:
        profile_name = DOMAIN_PROFILE.get(name, "agentic")
        in_tok, out_tok, cached = PROFILES[profile_name]
        shape = Shape(material_sensitive=material_sensitive, input_tokens=in_tok,
                      context_headroom=config.headroom,
                      context_margin=config.margin,
                      posture=zone.posture, domain=name, intent=intent)
        aff = domain_weights(signals, name, config.factors)
        admitted = frozenset(
            mid for mid in share_by_domain[name]
            if admit(shape, candidate_for(
                mid, policy, local=mid in local_ids,
                model=models.get(mid), roster=roster,
                loopback=loopback)).admitted)
        pool = eligibility_pool(share_by_domain[name], models, aff, pool_k,
                                admitted, local=local_ids)
        free = free_route_ids((mid for mid, _ in pool), local=local_ids)
        if not free:
            continue
        costs = {}
        for mid, _ in pool:
            model = models[mid]
            eps = priced_endpoints(mid, local_ids=local_ids, refresh=False)
            pricing = price_model(model, eps,
                                  in_tok, out_tok, cached, mult_for(model, intent))
            costs[mid] = pricing[basis]
        effective = effective_costs(
            costs,
            free_risk=config.free_risk,
            free=free,
            plans=policy["plans"])
        scores = {mid: standing(share, effective[mid], None,
                                config.alpha, config.beta)
                  for (mid, share) in pool}
        rows = plan_deal(
            share_by_domain[name], models, aff,
            DealParameters(blend_weight=config.blend_weight,
                           top_k=pool_k, seed=FREE_SHARE_CHECK_SEED,
                           tickets=FREE_SHARE_CHECK_TICKETS,
                           fit_adjusted_task_scores=scores,
                           admitted=admitted), local=local_ids)
        free_tickets, dealt_tickets = deal_free_share(rows, local=local_ids)
        shape_key = {"domain": name, "profile": profile_name,
                     "input_tokens": in_tok, "output_tokens": out_tok,
                     "cached_share": cached, "effort": intent,
                     "pricing_basis": basis, "sensitive": material_sensitive,
                     "eligibility_top_k": pool_k,
                     "blend_weight": config.blend_weight,
                     "scoring": {"alpha": config.alpha, "beta": config.beta,
                                 "free_risk": config.free_risk},
                     "context_gate": {
                         "headroom": config.headroom,
                         "margin": config.margin},
                     "eligible_free_routes": sorted(free),
                     "domain_hints": {
                         key: value for key, value in signals.items()
                         if name in value.get("fit", {})}}
        # A Sensitive deal's remote-free zero is structural - only Exposure
        # local may serve a Sensitive shape - so it is drift for no series:
        # the report below is a plain-shape instrument and never lists one.
        # The measurement itself still lands, under its honest key.
        zero = dealt_tickets > 0 and free_tickets == 0
        had_history, zero_streak = record_free_share_measurement(shape_key, zero)
        if zero and not material_sensitive:
            free_share_zeros.append((name, profile_name, dealt_tickets,
                                     had_history, zero_streak))
    age = policy_age_days(policy_path)

    print("# Policy check\n")
    print(f"zone: {zone_label(zone)}")
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

    # Spec #66 US8's second half: seeded bands the operator has not
    # confirmed are exporter-stamped `suspected` evidence, and the
    # diagnostic surface is where the operator meets them. Ids and a count
    # only — the prose is the roster's own, and this report never restates
    # it. Reporting changes nothing: a suspected band still binds exactly
    # like a confirmed one (ADR-0009), it just says so.
    print("\n## Roster bands awaiting confirmation")
    unconfirmed = sorted(
        mid for mid, entry in (roster or {}).items()
        if isinstance(entry, dict)
        and isinstance(entry.get("provenance"), dict)
        and entry["provenance"].get("evidence") == "suspected")
    if unconfirmed:
        print(f"- {len(unconfirmed)} suspected (exporter-stamped, "
              f"unconfirmed): {', '.join(unconfirmed)}")
    else:
        print("- — none")

    # Rostered ahead of the harness: a local entry no listing id reaches is
    # reported here, never dealt — existence comes from the listing alone,
    # so this is the one surface that can speak for an entry the ranking
    # cannot show. Both sources speak: the free catalog's local entries
    # (a policy-side claim about existence) and the Local roster's own
    # keys (judgment ahead of the harness). No flag means the harness
    # never spoke: say that instead of judging what was never given.
    print("\n## Local models the harness cannot run")
    if local_listing is None:
        print("- — harness listing not provided; not judgeable")
    else:
        stranded = sorted(
            {prefix for prefix, entry in policy.get("free_models", {}).items()
             if isinstance(entry, dict) and entry.get("exposure") == "local"
             and not any(mid.startswith(prefix) for mid in local_listing)}
            | {mid for mid in (roster or {}) if mid not in local_listing})
        for prefix in stranded:
            print(f"- {prefix} — not in the harness listing; never dealt")
        if not stranded:
            print("- — none")

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
        free = free_route_ids(share_by_domain[name], local=local_ids)
        pool = paid_pool(share_by_domain[name], models, free, pool_k,
                         local=local_ids)
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
            eps = priced_endpoints(mid, local_ids=local_ids, refresh=False)
            pricing = price_model(models[mid], eps,
                                  in_tok, out_tok, cached, m_mult)
            costs[mid] = pricing[basis]
        eff = effective_costs(
            costs,
            free_risk=config.free_risk,
            free=free_route_ids(costs, local=local_ids),
            plans=policy["plans"])
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

    reasons = [text for keep, text in (
        (gaps, f"{len(gaps)} gap{'' if len(gaps) == 1 else 's'}"),
        (stale, f"{len(stale)} stale"),
        (stale_signals,
         f"{len(stale_signals)} stale signal{'' if len(stale_signals) == 1 else 's'}"),
        (coverage, f"{len(coverage)} signal gap{'' if len(coverage) == 1 else 's'}"),
        (free_share_zeros,
         f"{len(free_share_zeros)} zero Free-share signal"
         f"{'s' if len(free_share_zeros) != 1 else ''}"),
        (age is not None and age > 30, f"policy {age} days old"),
    ) if keep]
    print(f"\nresearch cycle due: {'yes (' + ', '.join(reasons) + ')' if reasons else 'no'}")
    print(f"coefficient re-tune due: {'yes' if re_tune else 'no'}")


