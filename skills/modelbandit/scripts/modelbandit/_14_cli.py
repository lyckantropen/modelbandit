from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
def _harden_stdio(stdout=None, stderr=None) -> None:
    """Make this run speak UTF-8 on stdout and stderr, whatever the
    machine's code page says.

    The printed tables carry the `Δ` baseline column and other characters no
    legacy console code page can encode: on a cp1250 pipe or a redirected
    file the ranking died with a UnicodeEncodeError the moment the header
    line was written - the crash the PYTHONUTF8=1 environment workaround
    existed for. The CLI owns its encoding instead: any stream not already
    speaking UTF-8 is reconfigured to UTF-8 (lossless), with replacement
    characters as the last resort so no byte can abort a run. A stream that
    already speaks UTF-8, or one that cannot be reconfigured at all
    (StringIO, a test double), is left untouched - this is a guard, not a
    policy for anything but the process running this script.
    """
    for stream in (sys.stdout if stdout is None else stdout,
                   sys.stderr if stderr is None else stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding is None or encoding.lower().replace("-", "") == "utf8":
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            # A stream that refuses reconfiguration keeps its own encoding;
            # the run is no worse off than before the guard ran.
            pass


def main() -> None:
    # Before anything prints: the tables carry `Δ`, which cp1250 and
    # friends cannot encode - the run sets its own encoding, never the
    # console's code page (see _harden_stdio).
    _harden_stdio()
    ap = argparse.ArgumentParser(prog="modelbandit",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--domain", help="domain from policy.json (see --list-domains)")
    ap.add_argument("--list-domains", action="store_true",
                    help="show domains and their leaderboard tags")
    ap.add_argument("--check-secrets", action="store_true",
                    help="Secrets gate check: reads the shape's material from "
                         "stdin and prints the verdict and rule; repeat "
                         "--outside-file PATH for named outside content. "
                         "Material questions only — the built-in rules over "
                         "the material, plus provenance against closed "
                         "paths; model-and-zone questions belong to "
                         "--assert-allowed. It needs no policy and no "
                         "network. Exit 0 for every verdict — safe, "
                         "sensitive, not certified, or blocked: free-use "
                         "zone — the printed lines say which; "
                         "4 rules/config error, 2 usage errors. --json "
                         "answers with one object.")
    ap.add_argument("--outside-file", action="append", default=[], metavar="PATH",
                    help="include this outside file's capped content in --check-secrets "
                         "(repeatable; relative paths use --working-dir)")
    ap.add_argument("--assert-allowed", action="store_true",
                    help="pre-flight for an orchestrator: may --model serve in "
                         "the folder's effective zone? An unstated shape is "
                         "assumed Sensitive (printed as `shape: sensitive "
                         "(assumed)`); --plain states the material is not "
                         "Sensitive, --sensitive restates the default. Exit 0 "
                         "either way — the output says `allowed: <id>` or "
                         "`blocked: free-use zone`, so launch only on "
                         "allowed; 4 policy/config error. The zone is named, "
                         "the shape's content never is. No board or "
                         "classification is fetched; no network is needed.")
    ap.add_argument("--plain", action="store_true",
                    help="with --assert-allowed: state that the shape's "
                         "material is not Sensitive — the pre-flight assumes "
                         "Sensitive when no shape is stated, so a route that "
                         "retains training data is refused by default. "
                         "Contradicts --sensitive.")
    ap.add_argument("--model", default=None, metavar="ID",
                    help="the model a --assert-allowed run will use (checked "
                         "against the effective zone); read by no other mode")
    ap.add_argument("--write-zones", action="store_true",
                    help="write the machine's zones file from JSON on stdin "
                         "(the Set up the free-use zones interview's "
                         "proposal): validated before anything is written — "
                         "an invalid config refuses with status 4 naming the "
                         "entry and writes nothing; a valid one is written "
                         "atomically and the path written is printed")
    ap.add_argument("--working-dir", default=None, metavar="PATH",
                    help="working folder (default: cwd). Secrets gate "
                         "commands gather machine facts and gitignored "
                         "content from its git root; every run reads its "
                         "free-use zone from the machine's zones file")
    ap.add_argument("--check-policy", action="store_true",
                    help="report summary drift (ranked models without summaries, "
                         "stale summaries) and policy age; no --domain needed")
    ap.add_argument("--status", action="store_true",
                    help="offline setup report for this folder "
                         "(--working-dir): the effective zone, the zones "
                         "file, the built-in secrets rules in force and the "
                         "policy age. No fetch, no "
                         "classification, no quota. Exit 0 even when setup "
                         "files are absent (the documented default); 4 only "
                         "when an existing zones or policy file fails "
                         "validation. --json answers with one object.")
    ap.add_argument("--json", action="store_true",
                    help="answer with one JSON object on stdout instead of "
                         "the human lines: --check-secrets, --assert-allowed, "
                         "--status, a budgeted ranking run (--domain with "
                         "--budget), and a substitution (--deal "
                         "--substitute); a usage error anywhere else. `ok` is "
                         "always true — the status says the tool ran, the "
                         "object says what's true. The ranking table itself "
                         "is never JSON-ized.")
    ap.add_argument("--scope", action="store_true",
                    help="with the policy check (implied), print two fact lines "
                         "under each gap, stale-summary and stale-signal "
                         "bullet: where the model still ranks and its catalog "
                         "row with daily-token window totals; facts only")
    ap.add_argument("--anchors", nargs="*", metavar="MODEL_ID", default=None,
                    help="render first-party benchmark anchors as one table "
                         "per source (Artificial Analysis, Design Arena, "
                         "OpenRouter evals) for the refresh scope - the "
                         "policy's gaps then stale entries - or, when model "
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
    ap.add_argument("--tickets", type=int, default=None,
                    help="runs to project for")
    ap.add_argument("--deal", action="store_true",
                    help="deal tickets across the eligible pool by seeded draw "
                         "from the preference-blended distribution; with "
                         "--ticket-files the batch splits at collection — "
                         "ordinary tickets are dealt and tripped ones are "
                         "reported held, so the held lane runs again in one "
                         "invocation")
    ap.add_argument("--ticket-files", action="append", metavar="PATH",
                    help="one per ticket: name this run's ticket files "
                         "(repeatable); the script reads them itself at deal "
                         "time and applies the built-in credential, "
                         "identifier, machine-fact and gitignored-content "
                         "rules to each one — scoped to that file's own "
                         "directory — with no project rules file anywhere. A "
                         "tripped ticket is reported `held: <ids> (sensitive)` "
                         "for its local-only follow-up run; the rest of the "
                         "batch is dealt across the eligible pool")
    ap.add_argument("--substitute", default=None, metavar="ID",
                    help="with --deal: re-derive this seeded deal and print "
                         "the substitution record — the named model's Spare "
                         "takes the ticket over whole, fence restated, "
                         "reason recorded (exit 0); pass the same seed and "
                         "shape flags the deal ran with")
    ap.add_argument("--reason", default=None,
                    choices=("mechanical", "quality", "dead-attempt"),
                    help="with --substitute: why the model failed — "
                         "'mechanical' (unreachable, out of quota or "
                         "allowance, unloadable; the default, substitutes "
                         "automatically), 'dead-attempt' (the harness's "
                         "explicit failed-attempt report — the only way a "
                         "quality failure substitutes), or 'quality' alone, "
                         "which is refused")
    ap.add_argument("--seed", default="modelbandit",
                    help="deal seed for reproducibility; use the project name")
    ap.add_argument("--fit", default=None, metavar="SPEC",
                    help="agent's task-fit judgments, 'mid=score,...' on 0-5; "
                         "composes as score * fit/5 (longest prefix wins)")
    ap.add_argument("--local-listing", action="append", metavar="IDS",
                    help="the harness's local model ids ('lmstudio/...', "
                         "comma-separated, repeatable): the sole source of "
                         "local candidate existence and identity; omitted, "
                         "the run claims no local candidate at all")
    ap.add_argument("--sensitive", action="store_true",
                    help="Sensitive ticket shape (the Secrets gate's verdict): "
                         "only Exposure 'local' candidates are admitted — every "
                         "non-local route (no-retention and trains alike) is "
                         "excluded from the pick and the deal, marked with a "
                         "reason in the table; no eligible local candidate "
                         "stops the run with 'blocked: no eligible local "
                         "candidate' (exit 0)")
    ap.add_argument("--budget", type=float, help="run budget in USD")
    ap.add_argument("--top", type=int, default=8, help="ranking rows to show")
    ap.add_argument("--policy", default=DEFAULT_POLICY,
                    help="policy file: domains + baseline "
                         "(default: the skill's own policy.json)")
    ap.add_argument("--refresh", action="store_true", help="bypass the 24h cache")
    args = ap.parse_args()

    # Malformed ranking inputs are usage errors (status 2), named and stopped
    # before any plan is produced: a percentage-style cached share would price
    # tickets negative and flip the budget verdict to "under".
    if args.cached_share is not None and not 0.0 <= args.cached_share <= 1.0:
        ap.error(f"--cached-share {args.cached_share} must be between 0 and 1")
    for flag, tokens in (("--in-tokens", args.in_tokens),
                         ("--out-tokens", args.out_tokens)):
        if tokens is not None and tokens < 0:
            ap.error(f"{flag} {tokens} must not be negative")
    try:
        fit_map = parse_fit(args.fit) if args.fit else {}
    except ValueError as exc:
        ap.error(str(exc))

    # --plain states a shape, and only the pre-flight takes one stated: a
    # flag silently ignored elsewhere would be a rule the user believes in.
    if args.plain and not args.assert_allowed:
        ap.error("--plain is read only by --assert-allowed")
    if args.plain and args.sensitive:
        ap.error("--plain and --sensitive contradict; state one shape")

    # Same rule for the substitution flags: a flag silently ignored is a
    # rule the user believes in. `--substitute` lives in the deal's shape —
    # it re-derives the seeded deal — and `--reason` names only why.
    if args.reason is not None and not args.substitute:
        ap.error("--reason is read only by --substitute")
    if args.substitute is not None and not args.deal:
        ap.error("--substitute is read only by --deal")

    # --ticket-files lives in the deal's shape too (the automatic material
    # assessment runs at deal time): refused where it would say nothing, and
    # a named path that is no ticket file is named before anything is
    # fetched. The named files are the batch — one file, one ticket — so
    # --tickets would restate the count the collection computes; it is
    # refused rather than silently ignored.
    if args.ticket_files and not args.deal:
        ap.error("--ticket-files is read only by --deal")
    if args.ticket_files and args.tickets is not None:
        ap.error("--tickets is read only without --ticket-files "
                 "(the named files are the batch)")
    if args.tickets is None:
        args.tickets = 1
    if args.ticket_files:
        for path in args.ticket_files:
            if not os.path.isfile(path):
                ap.error(f"--ticket-files: not a ticket file: {path}")

    # --json answers the verdict modes only; the ranking table is never
    # JSON-ized (issue #41), so anywhere else the flag would be silently
    # ignored — it stops as the usage error it is. A substitution answers
    # with its own record (issue #71), so it counts as served beside the
    # budgeted ranking run.
    if args.json:
        domain_served = bool(args.domain) and (args.budget is not None
                                               or args.substitute is not None)
        served = (int(args.check_secrets) + int(args.assert_allowed)
                  + int(args.status) + int(domain_served))
        riders = (args.write_zones or args.list_domains
                  or args.check_policy or args.scope
                  or args.anchors is not None
                  or (args.domain and not domain_served))
        if served != 1 or riders:
            ap.error("--json is read only by --check-secrets, --assert-allowed, "
                     "--status, a budgeted ranking run (--domain with "
                     "--budget) and a substitution (--deal --substitute), "
                     "each on its own")

    if args.reason == "quality":
        # The quality class refuses at the flag (issue #71): taste never
        # reshuffles work mid-run — a quality failure substitutes only on
        # the harness's explicit dead-attempt report. The refusal is this
        # run's verdict, like any other: it prints (or answers --json) and
        # exits 0, before anything is fetched.
        refusal = ("quality failure substitutes only on the harness's "
                   "explicit dead-attempt report "
                   "(state --reason dead-attempt)")
        if args.json:
            emit_json({"mode": "substitution", "ok": True,
                       "verdict": "refused", "substitute": args.substitute,
                       "reason": refusal, "zone": None})
        else:
            print(f"substitution refused: {refusal}")
        raise SystemExit(0)

    # `--model` is the pre-flight's question (the mode split, spec #75): the
    # check answers material questions only, so the flag is refused here
    # rather than silently ignored.
    if args.model and not args.assert_allowed:
        ap.error("--model is read only by --assert-allowed")
    if args.assert_allowed:
        # The pre-flight reads the zone and the local policy, never the board:
        # an orchestrator refuses a model the plan should not have produced
        # before anything is fetched. The dispatch contract fails closed: an
        # unstated shape is Sensitive, --plain states it is not, and
        # --sensitive restates the default.
        if not args.model:
            ap.error("--assert-allowed needs --model <id>")
        raise SystemExit(run_assert_allowed(
            model=args.model, working_dir=args.working_dir,
            policy_path=args.policy, plain=args.plain,
            restated=args.sensitive, as_json=args.json))
    if args.check_secrets:
        # The gate reads the working folder, never the network: no policy and
        # no board are needed to decide whether a shape is Sensitive.
        raise SystemExit(run_secrets_check(working_dir=args.working_dir,
                                           outside_files=args.outside_file,
                                           as_json=args.json))
    if args.write_zones:
        # The machine's zones file: the interview's proposal on stdin,
        # validated before anything is written — status 4 with the offending
        # entry named writes nothing, a valid config replaces the file
        # atomically. Needs no policy and no network.
        raise SystemExit(run_zones_writer())
    if args.status:
        # The setup report reads the folder and the machine's files, never
        # the network: absent setup files are the documented default (exit
        # 0), and only a file that exists and fails validation stops the
        # report (exit 4).
        raise SystemExit(run_status(working_dir=args.working_dir,
                                    policy_path=args.policy,
                                    as_json=args.json))

    # One policy loader for every entry point: the ranking path reports a
    # policy/config error (status 4) instead of letting an unreadable or
    # untrustworthy policy escape as a traceback or a Secrets verdict.
    try:
        policy = load_policy_bundle(args.policy)
        config = load_policy_config(policy)
    except SystemExit as exc:
        print(f"policy/config error: {exc}", file=sys.stderr)
        raise SystemExit(RULES_CONFIG_ERROR) from None
    domains = policy.get("domains", {})
    # The Local roster travels the same status-4 road as the policy it sits
    # beside: a malformed entry stops the run naming it, never reaching
    # admission as a guessed band.
    try:
        roster = load_local_roster()
    except SystemExit as exc:
        print(f"local roster/config error: {exc}", file=sys.stderr)
        raise SystemExit(RULES_CONFIG_ERROR) from None

    if args.list_domains:
        for name, tags in domains.items():
            print(f"{name:14s} {', '.join(tags)}")
        return
    if not args.domain and not args.check_policy and not args.scope \
            and args.anchors is None:
        ap.error("need --domain (or --list-domains / --check-policy "
                 "/ --scope / --anchors)")
    if args.domain and args.domain not in domains:
        ap.error(
            f"no domain '{args.domain}'; known: {', '.join(domains) or 'none'}")

    # Where free may run: the machine's zones file, judged for this working
    # folder and the repository it came from. The posture is binary and the
    # run works under it; --sensitive no longer tightens it (ADR-0010). A
    # zones file that exists but fails validation is a rules/config error
    # (status 4), named instead of escaping as a generic failure.
    try:
        zone = effective_zone(args.working_dir)
    except SystemExit as exc:
        print(f"zones/config error: {exc}", file=sys.stderr)
        raise SystemExit(RULES_CONFIG_ERROR) from None
    models_raw = fetch_json(MODELS_URL, "models.json", auth=False, refresh=args.refresh)
    model_rows = models_raw["data"] if isinstance(models_raw, dict) else models_raw
    models = {norm_id(m["id"]): m for m in model_rows}
    by_canon = {}
    for m in models.values():
        if m.get("canonical_slug"):
            by_canon.setdefault(norm_id(m["canonical_slug"]), m)

    classif = fetch_json(CLASS_URL, "classifications.json", auth=True,
                         refresh=args.refresh)["data"]
    # The local universe arrives from the harness - passed in with
    # --local-listing - and the serving endpoint from the harness's config:
    # one fact each, no discovery channel of our own (the probe below stays
    # two narrow facts about already-listed candidates: is it serving, at
    # what window). `loopback` is the condition `local` Exposure resolves
    # under, and `listed` is empty whenever the harness never spoke. These
    # are file and config reads, so they precede every dispatch that needs
    # them - the run's posture is built once, here, and passed whole.
    serving_endpoint = harness_serving_endpoint()
    loopback = loopback_endpoint(serving_endpoint)
    local_listing = parse_local_listing(args.local_listing)
    listed = sorted(local_listing) if local_listing is not None else []
    local_ids = local_candidate_ids(listed, policy["free_models"])
    ctx = RunContext(zone=zone, local_ids=local_ids, loopback=loopback,
                     roster=roster, intent=args.effort)
    if args.anchors is not None:
        run_anchors(args.anchors, models, by_canon, classif, domains, policy,
                    args.top, args.refresh, config, ctx)
        return
    served_local = probe_local_models(url=models_url(serving_endpoint))
    if args.check_policy or args.scope:
        # The scope path needs the daily token rankings for window totals; the
        # bare check never consults them and stays one fetch lighter.
        ranks = (fetch_json(RANK_URL, "rankings.json", auth=True,
                            refresh=args.refresh)
                 if args.scope else None)
        share, models = merge_free_candidates(
            {}, models, policy["free_models"], policy.get("summaries", {}),
            inheritance=config.free_share_inheritance)
        # Check-policy sees this invocation's same local candidates and
        # serving facts (the loopback condition included) as a domain run,
        # but still performs no persistent policy update.
        _, models = merge_local_candidates(
            share, models, listed, served_local, policy["free_models"],
            inheritance=config.free_share_inheritance)
        run_check_policy(models, by_canon, classif, domains, policy,
                         args.top, args.policy,
                         args.pricing_basis,
                         config, ctx, material_sensitive=args.sensitive,
                         ranks=ranks,
                         local_listing=local_listing)
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
        share, models, policy["free_models"], policy.get("summaries", {}),
        inheritance=config.free_share_inheritance)
    # The listing is the live, per-run input, not persistent catalog state:
    # only harness-listed ids matched to an Exposure=local policy entry join.
    share, models = merge_local_candidates(
        share, models, listed, served_local, policy["free_models"],
        inheritance=config.free_share_inheritance)
    # The plans catalog is a plan serving's only way in: its id never resolves
    # in the models list. A cataloged plan row joins here, at split family
    # share; the local serving fact outranks it.
    share, models = merge_plan_candidates(share, models, policy["plans"],
                                          local=local_ids)
    for mid in share:
        if mid in models and (is_free_route(mid) or is_plan_route(mid)):
            matches[mid] = "catalog"
    shape = Shape(material_sensitive=args.sensitive, input_tokens=in_tok,
                  output_tokens=out_tok,
                  context_headroom=config.context.headroom,
                  context_margin=config.context.margin,
                  posture=ctx.zone.posture,
                  domain=args.domain, intent=args.effort)
    # Zone prohibitions filter at source: a candidate the zone forbids outright
    # never enters the candidate set — not ranked, not scored, not dealt, not
    # listed, and its endpoints never priced. The header states the zone that
    # made it absent. Shape-level exclusions (Exposure, Footprint, quota,
    # catalog) still mark, never hide. The loopback fact travels with the
    # candidate so the row the table later marks is the row admission judged.
    share = filter_zone_candidates(
        share, models, policy, local_ids=ctx.local_ids,
        posture=ctx.zone.posture, intent=ctx.intent, loopback=ctx.loopback)
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
    print(f"zone: {zone_label(zone)}")
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
        # Same yardstick as filter_zone_candidates: a closed posture has
        # already dropped every remote Free route at source, so the pool
        # clause says so instead of claiming they stayed (issue #38). Where
        # free routes genuinely remain, the line is unchanged, as are the
        # quota figures above.
        pool = (":free routes excluded by the closed zone"
                if ctx.zone.posture == "closed"
                else ":free routes stay in the pool")
        print(f"free quota: unavailable | {pool}")
    if not verdict.eligible:
        print(f":free routes excluded from the pick and the deal — "
              f"{verdict.reason}")
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
        endpoint_cache[mid] = priced_endpoints(mid, local_ids=local_ids,
                                               refresh=args.refresh)

    # The one admission decision: the table marks with it, the deal draws
    # from it. Excluded rows stay visible; only the pick and the pool shun
    # them. A candidate the zone forbids never got this far.
    candidates = {mid: candidate_for(
        mid, policy, local=mid in local_ids, model=models.get(mid),
        endpoints=endpoint_cache.get(mid, ()), intent=args.effort,
        loopback=loopback, roster=roster)
        for mid in share}
    decisions = {mid: admit(shape, candidate, quota=verdict)
                 for mid, candidate in candidates.items()}
    admitted = frozenset(mid for mid, d in decisions.items() if d.admitted)
    show_admission = shape.sensitive or any(
        not decisions[mid].admitted or decisions[mid].reason
        for mid, _ in ranked)
    # One eligibility pool: the deal plays it, and this run prices it, so a
    # favored model below --top still scores at the same scale as the rows
    # above it.
    pool = (eligibility_pool(share, models, aff, config.deal.eligibility_top_k,
                             admitted, local=local_ids, plans=policy["plans"])
            if args.deal else [])
    # The run's allowance ledger: prospective and in-run, so it starts empty
    # and nothing leaves this process. The pick asks it (one task) and the
    # deal draws it down (the whole batch).
    ledger = AllowanceLedger(policy["plans"], local=local_ids)

    if shape.sensitive:
        # ADR 0008: a Sensitive shape with no eligible local candidate is
        # announced up front - whatever made it Sensitive.
        print("shape: sensitive — non-local candidates are excluded from the "
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
            endpoint_cache[mid] = priced_endpoints(mid, local_ids=local_ids,
                                                   refresh=args.refresh)
        eps = endpoint_cache[mid]
        pr = price_model(m, eps,
                         in_tok, out_tok, cached,
                         mult_for(m, args.effort))
        priced[mid] = pr
        pers[mid] = pr[args.pricing_basis]
    # Free routes price at the Nominal floor in the score's cost term — the
    # same floor for every Exposure — and a plan route prices as risk of its
    # list-priced Draw (ADR-0006) — while the table's price columns keep
    # showing what the route actually costs to run.
    eff_costs = effective_costs(
        pers,
        free_risk=config.free_risk,
        free=free_route_ids(pers, policy, local=local_ids),
        plans=policy["plans"])

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
    # The pick's eligible set: the run's priced, displayed rows that passed
    # admission -- the degenerate form of the deal's pool, so the Twin rule
    # reads the same declarations against the same gates.
    pick_rows = {row[0]: row for row in rows_out}
    pick_pool = [(mid, s) for mid, s, *_ in rows_out if decisions[mid].admitted]

    pick = None
    cheapest = None
    floor_total = 0.0
    at_cap_rows = []
    i = 0
    for mid, s, m, pr, sc, fit, adj in rows_out:
        i += 1
        per = pr[args.pricing_basis]
        delta = f"{per / base_per:.2f}x" if base_per else "—"
        plan_row = is_plan_route(mid, local=mid in local_ids)
        if plan_row:
            # A plan serving states no per-1M market price and no endpoint
            # spread: the plan catalog's list price is a Draw basis, not a
            # per-token one. The cells say so; no figure is invented.
            out_cell = "—"
        else:
            spread = "" if pr["n_eps"] <= 1 else \
                f" ({pr['n_eps']} eps)" if pr["out_max"] / max(pr["out_min"], 1e-9) < 2 else \
                f" ({pr['n_eps']} eps, wide)"
            out_cell = f"{pr['out_min']:.2f}–{pr['out_max']:.2f}{spread}"
            if pr["n_eps"] == 0:
                out_cell += " (no endpoint data)"
        free_details = free_candidate_details(mid, policy, local=mid in local_ids)
        context_length = free_details[0] if free_details else m.get("context_length")
        ctx_cell = f"{context_length / 1024:.0f}K" if context_length else "?"
        if free_details or is_free_route(mid, local=mid in local_ids) or plan_row:
            # The column shows the exposure admission judged: resolved
            # through the same precedence, loopback fact included — a
            # cataloged `local` the endpoint cannot back reads as the
            # exposed fallback it was refused as.
            exposure = row_exposure(mid, policy, local_ids=local_ids,
                                    loopback=loopback)
        else:
            exposure = "—"
        if plan_row:
            # The catalog states no effort ladder for a plan serving.
            rung = "—"
        else:
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
        shown_mid = _shown_mid(mid, candidates[mid])
        print(f"| {i} | {shown_mid} | {s:.2%} | {sc:.2f} |{fit_cell} "
              f"{tokens_30d.get(mid, 0) / 1e9:.0f}B | {out_cell} | ${per:.4f} | "
              f"{delta} | {ctx_cell} | {exposure} | {rung} |{admit_cell}")
        if decisions[mid].admitted:
            if pick is None:
                # The pick is one task: it takes the top of the task order
                # unless its Draw would cross a window's cap, in which case
                # the family's Metered Twin takes it -- same model, market
                # flipped plan to metered, named by its qualified id alone
                # (the id names the market: no price, no Draw) --
                # and only a link that resolves no eligible row falls through
                # to the next admitted row, as before (the ledger is the
                # run's; nothing has been drawn yet at this point).
                if ledger.crosses(mid):
                    k = _twin_index(mid, pick_pool, policy["plans"],
                                    local=local_ids)
                    if k is None:
                        at_cap_rows.append(mid)
                    else:
                        twin = pick_pool[k][0]
                        twin_pr = pick_rows[twin][3]
                        pick = (twin, twin_pr[args.pricing_basis], twin_pr)
                        floor_total = twin_pr["best"] * args.tickets
                else:
                    pick = (mid, per, pr)
                    floor_total = pr["best"] * args.tickets
            if cheapest is None or per < cheapest[1]:
                cheapest = (mid, per)
    excluded = sorted(mid for mid, d in decisions.items() if not d.admitted)
    if pick is None and at_cap_rows:
        # Every row that could have been picked is at its cap: the ledger's
        # verdict rides the existing all-excluded stop -- the rows it kept
        # out of the pick are named with them -- rather than inventing a
        # failure of its own.
        excluded = sorted(set(excluded) | set(at_cap_rows))
    for mid, s in sorted(((mid, s) for mid, s in ranked if mid not in priced),
                         key=lambda t: -t[1]):
        i += 1
        admit_cell = ""
        if show_admission:
            admit_cell = f" {decisions[mid].reason or '—'} |"
        free_details = free_candidate_details(mid, policy, local=mid in local_ids)
        context_length = free_details[0] if free_details else None
        ctx_cell = f"{context_length / 1024:.0f}K" if context_length else "?"
        exposure = (row_exposure(mid, policy, local_ids=local_ids,
                                 loopback=loopback)
                    if free_details or is_free_route(mid, local=mid in local_ids)
                    else "—")
        shown_mid = _shown_mid(mid, candidates[mid])
        print(f"| {i} | {shown_mid} | {s:.2%} | — | {tokens_30d.get(mid, 0) / 1e9:.0f}B | "
              f"— unresolved to a priced model | | | {ctx_cell} | {exposure} | |{admit_cell}")

    if any(candidate.summary_missing for candidate in candidates.values()):
        print("\n† Gap: editorial completeness is not an admission verdict.")

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
        if shape.sensitive:
            # ADR 0008: a Sensitive shape with no eligible local candidate
            # stops with the blocked report — the report is the human
            # escalation, never a re-gate — and, like every verdict, exits
            # 0 (the table above has already marked every exclusion's
            # reason, so nothing is hidden by the stop).
            if args.json:
                emit_json({"mode": "budget", "ok": True,
                           "verdict": "blocked",
                           "reason": "no eligible local candidate",
                           "rule": None, "zone": zone_payload(zone)})
            else:
                _print_verdict(STOP_NO_ELIGIBLE_LOCAL_CANDIDATE)
            raise SystemExit(0)
        # A completed run that found nothing to pick: the stop uses the
        # one blocked-verdict printer and the status stays 0 (exit contract
        # v2, ADR-0004). A --json run answers with the same verdict and reason
        # in its one object (issue #41, Build 2).
        stop_line = (STOP_NO_CANDIDATE_ADMITTED if excluded
                     else STOP_NO_RANKED_CANDIDATES)
        if args.json:
            emit_json({"mode": "budget", "ok": True,
                       "verdict": "blocked",
                       "reason": stop_line.removeprefix("blocked: "),
                       "rule": None, "zone": zone_payload(zone)})
        else:
            _print_verdict(stop_line)
        raise SystemExit(0)
    if excluded and rows_out \
            and not decisions[rows_out[0][0]].admitted:
        print(f"\nnote: top of task order {rows_out[0][0]} is excluded "
              f"({decisions[rows_out[0][0]].reason}) — not picked")
    pick_line = (f"\ndefault pick (top of task order): "
                 f"{qualified_id(pick[0], local=pick[0] in local_ids)}")
    pick_draw = ticket_draw(pick[0], policy["plans"],
                            local=pick[0] in local_ids)
    if pick_draw is not None:
        pick_line += (f" (${pick[1]:.4f}/ticket; "
                      f"Draw ${pick_draw:.2f}/ticket)")
    print(pick_line)
    pr_pick = pick[2]
    if pr_pick.get("best_ep") and pr_pick.get("worst_ep") \
            and pr_pick["best_ep"] != pr_pick["worst_ep"]:
        print(f"route to floor: pin provider '{pr_pick['best_ep']}' via "
              f"body.provider.order (allow_fallbacks: false) — unpinned worst "
              f"endpoint is '{pr_pick['worst_ep']}' at ${pr_pick['worst']:.4f}/ticket")
    if cheapest and cheapest[0] != pick[0]:
        print(f"cheapest shown: {cheapest[0]} at ${cheapest[1]:.4f}/ticket "
              f"(budget pressure moves within the ranking, by price)")

    local_share = None
    held_ids: list[int] = []
    if args.deal:
        # Deal-time material assessment (spec #75, ticket #86): the named
        # ticket files are read here and each is assessed through the shared
        # material-assessment entry point — built-in credential, identifier,
        # machine-fact and gitignored-content rules, scoped to that file's
        # own directory, with no project rules file anywhere. US9 reports a
        # tripped ticket as held when excluded from this invocation's ordinary
        # deal; US10 assigns it to its own follow-up Sensitive run, local-only.
        # In that follow-up the ticket is dealt, not held or excluded, so a
        # held line would contradict US9. A run that already states the
        # Sensitive shape (the flag, or a closed place) is that follow-up.
        # The deal's seed math is untouched — one invocation still deals one
        # shape.
        if args.ticket_files:
            ordinary = 0
            for index, path in enumerate(args.ticket_files, 1):
                try:
                    with open(path, "rb") as f:
                        material = f.read().decode("utf-8", "replace")
                except OSError:
                    ap.error(f"--ticket-files: cannot read: {path}")
                tripped, _rule = secrets_check(
                    material, root=os.path.dirname(os.path.abspath(path)))
                if tripped and not shape.sensitive:
                    held_ids.append(index)
                else:
                    ordinary += 1
            # The dealt batch is the tickets that passed, so the draw, the
            # projection and the budget verdict speak this invocation's
            # dealt count.
            args.tickets = ordinary
            if held_ids:
                print(f"held: {', '.join(str(i) for i in held_ids)} "
                      "(sensitive)")
        # Every pool member's base is the table's own scoring number: the
        # fit-adjusted task score, at score scale for the whole pool.
        fit_adjusted_task_scores = {
            mid: standing(s, eff_costs[mid], fit_for(mid, fit_map), alpha, beta)
            for mid, s in pool}
        # The standing favor (issue #69): an admitted local row — the band
        # gate has already passed it — tilts the draw's pref by the
        # affinity factors' validated favor, so a qualifying shape
        # genuinely deals local hardware while the seeded draw still
        # chooses the row. Cloud rows are never keyed here, so score,
        # Nominal floor, family-share inheritance and paid-pool balance
        # stand untouched; a shape that loses its locals at the band gate
        # has no admitted row to favor.
        favor = {mid: config.factors["favor_validated"]
                 for mid in local_ids if mid in admitted}
        deal_parameters = DealParameters(
            blend_weight=config.deal.blend_weight,
            top_k=config.deal.eligibility_top_k,
            seed=args.seed,
            tickets=args.tickets,
            fit_adjusted_task_scores=fit_adjusted_task_scores,
            admitted=admitted,
            favor=favor,
        )
        # plan_deal's out-record of the draw (issue #72): position i is
        # the mid that took ticket i+1, feeding the ticket map and the
        # lane printed below.
        assign: list = []
        rows = plan_deal(share, models, aff, parameters=deal_parameters,
                         local=local_ids, plans=policy["plans"],
                         ledger=ledger, assign=assign)
        if args.substitute is not None:
            # The substitution record is this invocation's whole answer
            # (issue #71): the same seed and shape flags above re-derived
            # the identical deal, so the Spare the record names is the one
            # the original readout named — and the record, not the deal
            # table, is what prints (exit 0 for substituted and blocked
            # alike).
            raise SystemExit(run_substitution(
                args.substitute, args.reason or "mechanical", rows,
                ctx=ctx, sensitive=shape.sensitive, as_json=args.json,
                assign=assign))
        print(f"\ndeal (seed '{args.seed}', blend {config.deal.blend_weight} from policy "
              f"affinity; eligibility stays popularity — the deal tilts by "
              f"preference):")
        # Every dealt row names its Spare (issue #71): the best candidate
        # that missed the draw, no-load preferred off-Sensitive, local-only
        # on it. `-` marks the rows that missed the draw themselves; `none`
        # (and a `spare:` note below) records a dealt row with no Spare left.
        spares = deal_spares(rows, local=local_ids,
                             sensitive=shape.sensitive)
        print("| # | model | pop% | score | pref | draw% | tickets | spare | "
              "$/ticket | subtotal |")
        print("|---|---|---|---|---|---|---|---|---|---|")
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
            out_mid = qualified_id(row["mid"], local=row["mid"] in local_ids)
            spare_mid = spares.get(row["mid"])
            spare_cell = ("-" if not row["tickets"] else
                          (qualified_id(spare_mid,
                                        local=spare_mid in local_ids)
                           if spare_mid else "none"))
            print(f"| {i} | {out_mid} | {row['share']:.2%} | "
                  f"{row['base']:.2f} | "
                  f"{row['pref']:.1f} | {row['draw']:.2%} | {row['tickets']} | "
                  f"{spare_cell} | ${per:.4f} | ${per * row['tickets']:.4f} |")
        for row in rows:
            # An exhausted dealt row says so where the Spare column reads
            # `none`: a substitution would report blocked, and the fence
            # that keeps it from reaching outside the pool stands either way.
            if row["tickets"] and spares.get(row["mid"]) is None:
                print("spare: " + spare_exhaustion_text(
                    qualified_id(row["mid"], local=row["mid"] in local_ids),
                    sensitive=shape.sensitive))
        # The batch's ticket map and the single strict lane (issue #72):
        # every ticket id's model, then the local-dealt ids grouped by
        # served model — one local run at a time, minimal load churn.
        # Both lines speak `prefix: … -> <model>` so the readout parses.
        ticket_map = tickets_by_model(rows, assign=assign, local=local_ids)
        for model, ids in ticket_map.items():
            print(f"ticket ids: {', '.join(str(i) for i in ids)} -> {model}")
        lane = deal_lane(assign, local=local_ids)
        if lane:
            print("lane: strict — one local run at a time (grouped by model)")
            for group in lane:
                print(f"lane: {', '.join(str(i) for i in group['tickets'])} "
                      f"-> {group['model']}")
        else:
            print("lane: none — no local-dealt tickets")
        for row in rows:
            mid = row["mid"]
            readout = ledger.readout(mid)
            if row["tickets"] == 0 or not readout:
                continue
            monthly, five_hour = readout["monthly"], readout["five_hour"]
            print(f"allowance draw: {mid} ${monthly['drawn']:.2f} of "
                  f"${monthly['cap']:.2f} "
                  f"({monthly['drawn'] / monthly['cap']:.1%} of monthly; "
                  f"{five_hour['drawn'] / five_hour['cap']:.1%} of 5h)")
        free_tickets, dealt_tickets = deal_free_share(
            rows, policy, local=local_ids)
        print(share_line("free share", free_tickets, dealt_tickets))
        plan_tickets = sum(row["tickets"] for row in rows
                           if is_plan_route(row["mid"],
                                            local=row["mid"] in local_ids))
        print(share_line("plan share", plan_tickets, dealt_tickets))
        # The local share (issue #69): the third readout line, beside free
        # and plan — how many of the batch's tickets never leave the
        # machine. It always prints; zero is an answer, not an absence.
        local_tickets, local_dealt = deal_local_share(rows, local=local_ids)
        print(share_line("local share", local_tickets, local_dealt))
        local_share = {"tickets": local_tickets, "dealt": local_dealt,
                       "percent": (100.0 * local_tickets / local_dealt
                                   if local_dealt else 0.0)}
        if shape.sensitive:
            # Standing contract marker for a deal touching Sensitive
            # material (ADR 0008): the harness applies it at prompt time —
            # the prompt itself stays the harness's to author.
            print(NON_LEAK_NOTE)
    else:
        total = pick[1] * args.tickets
    print(f"projection at {args.tickets} ticket(s): ${total:.2f} "
          f"(floor ${floor_total:.2f})"
          + (f" | baseline anchor: ${base_per * args.tickets:.2f}" if base_per else ""))
    if args.budget is not None:
        over_budget = total > args.budget
        if args.json:
            # The budget verdict is this run's answer, in place of the human
            # line; the ranking table above stays line output (never
            # JSON-ized — issue #41). A dealt run also carries its local
            # share (issue #69): the machine-readable twin of the printed
            # readout's third share line, present only when a deal ran.
            payload = {"mode": "budget", "ok": True,
                       "over_budget": over_budget,
                       "budget": args.budget,
                       "projection": {"tickets": args.tickets,
                                      "total": total,
                                      "floor": floor_total,
                                      "baseline": (base_per * args.tickets
                                                   if base_per else None)},
                       "zone": zone_payload(zone)}
            if held_ids:
                # The held report's machine twin (ticket #86): the ids this
                # invocation held at collection, as the readout printed.
                payload["held"] = held_ids
            if local_share is not None:
                payload["local_share"] = local_share
                # The Spares twin of the readout's spare column (issue #71):
                # one entry per dealt model, keyed by provider-qualified id;
                # null records the exhausted row the column shows as `none`.
                payload["spares"] = {
                    qualified_id(mid, local=mid in local_ids):
                        (qualified_id(spare, local=spare in local_ids)
                         if spare else None)
                    for mid, spare in spares.items()}
                # The lane twin of the readout's lane block (issue #72):
                # groups of mutually exclusive local-dealt ticket ids per
                # served model (grouped-by-model order), plus the full
                # ticket id -> model map the readout's `ticket ids:` lines
                # carry — empty lane when no local row drew.
                payload["lane"] = lane
                payload["tickets_by_model"] = ticket_map
            emit_json(payload)
        else:
            verdict = "under" if not over_budget else "OVER"
            print(f"budget: ${args.budget:.2f} -> {verdict}")
        if over_budget:
            # Over budget is a verdict, not a failure: exit 0 with the OVER
            # line (v2 retires the borrowed usage status; ADR-0004).
            sys.exit(0)


if __name__ == "__main__":
    main()
