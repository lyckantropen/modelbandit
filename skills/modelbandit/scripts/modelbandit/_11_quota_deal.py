from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
# --- Free-request quota ----------------------------------------------------
# OpenRouter's daily free-request counter: one figure shared by every ':free'
# route on the account, reset at UTC midnight. The tier ceiling is set by
# all-time credits purchased, and no response header reports the running
# count, so it is read from the key payload up front. The counter's facet
# charges the free-slug kind alone; harness, plan and local servings never
# spend it.


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
    """Say it once, and never decide anything from it.

    The pool verdict belongs to the run's header, which knows the zone; this
    warning states the quota fact and nothing about where routes stand."""
    suffix = f" ({detail})" if detail else ""
    print(f"warning: free quota unavailable{suffix}", file=sys.stderr)


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
              top_k: int, local=(), plans=None) -> list[tuple[str, float]]:
    """The balance criterion's players: the top_k most popular paid models.

    Score mass judges the paid competition — the band was calibrated for a
    landscape in which Free routes were not scored at all, and Free's
    participation is answered by the Free share signal, not by a threshold.
    Free routes leave before the cut, so a pool that Free dominates wholly
    still has a paid competition to judge. Plan rows the plans catalog
    prices play: they are paid servings with a Draw. A plan id the catalog
    does not price leaves — no pool builder may fabricate an uncataloged
    plan row; a plan-shaped id this machine serves is a local row (the
    seam's precedence).
    """
    local = set(local)
    catalog = plans or {}
    return [entry for entry in popularity_ranking(share, models)
            if entry[0] not in free
            and (not is_plan_route(entry[0], local=entry[0] in local)
                 or entry[0] in catalog)][:top_k]


def eligibility_pool(share: dict, models: dict, aff: dict, top_k: int,
                     admitted: frozenset | None = None,
                     local=(), plans=None) -> list[tuple[str, float]]:
    """The deal's players, computed once for every consumer.

    Eligibility stays popularity: the top_k selectable models, plus ranked
    models the user favors (weight > 1) below the cut — the admission seam's
    verdict applied first (``admitted``: the ids it admits; None admits all).
    An excluded player is never replaced by a lower-ranked one: popularity
    orders, admission only removes. Plan rows the plans catalog prices play;
    an uncataloged plan id leaves (a plan-shaped id this machine serves is a
    local row — the seam's precedence — and the board may still name one).
    Returns [(mid, share)] in popularity order; the candidate table prices
    these same players.
    """
    local = set(local)
    catalog = plans or {}
    ranked = [entry for entry in popularity_ranking(share, models)
              if (admitted is None or entry[0] in admitted)
              and (not is_plan_route(entry[0], local=entry[0] in local)
                   or entry[0] in catalog)]
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


def _twin_index(mid: str, pool: list[tuple[str, float]], plans: dict,
                *, local=frozenset()) -> int | None:
    """The pool row that absorbs an at-cap Plan route's ticket: the family's
    Twin, resolved through the plans entry's declared `family_ref` alone.

    The market adapter is internal to the deal (issue #65): a Plan row at cap
    hands its ticket to the same model's Metered serving -- identity
    preserved, market flipped -- so the batch keeps the model and pays
    metered instead of falling through to a different one. Resolution reads
    the declaration, never an id shape: `family_key` is the split family
    share's heuristic, and vendor prefixes differ per family, so no slug
    derives a Twin. A row answers only when the declaration names a Metered
    serving this run actually plays: an absent, uncataloged, admission-
    excluded or non-metered link (a plan-shaped or served-here id) resolves
    nothing, and the caller's circular fall-through stands. One direction
    only -- the link is read from a Plan row and lands on its Metered Twin,
    never the reverse (ADR-0007).
    """
    if not is_plan_route(mid, local=mid in local):
        return None
    entry = plans.get(mid)
    ref = entry.get("family_ref") if isinstance(entry, dict) else None
    if not isinstance(ref, str) or not ref.strip():
        return None
    if classify_route(ref, local=ref in local) != "market":
        return None
    return next((j for j, (row, _) in enumerate(pool) if row == ref), None)


def plan_deal(share: dict, models: dict, aff: dict,
              parameters: DealParameters, local=(), plans=None,
              ledger: AllowanceLedger | None = None,
              assign: list | None = None) -> list[dict]:
    """Multi-ticket deal over the eligible pool: seeded, preference-tilted.

    Eligibility is popularity (eligibility_pool). The draw blends the task
    baseline and preference:

        draw = (1 - blend_weight) * task_score + blend_weight * pref
        (each normalized)

    where every pool member's base is its fit-adjusted task score, supplied
    for the whole pool by the caller (blend_bases). Deterministic in seed.
    The standing favor (issue #69) multiplies into a row's pref —
    ``pref = weight_for(mid, aff) * favor.get(mid, 1.0)`` — so the caller's
    band-passing local rows tilt the draw through the same affinity
    machinery that reads the hints, while the seeded draw still decides
    which tickets land where. The favor moves preference alone: eligibility
    (the pool), the bases, Nominal-floor pricing and the ledger never read
    it. The pool is admission-filtered before the draw (parameters.admitted),
    so the deal and the ranked table agree about what may serve the shape.
    Plan rows the plans catalog prices draw here too; the second brace keeps
    an uncataloged plan id out whatever reaches it.

    The one-burst ledger draws each ticket down from the plan rows'
    Allowances as the loop assigns it (`ledger`, built from the plans
    catalog when the caller passes none). A plan row whose next ticket's
    Draw would cross a window's cap hands its slot to its family's Twin --
    the pool row its `family_ref` declares: same model, market flipped plan
    to metered, no Draw charged to the exhausted windows -- so the family's
    drawn share stays whole while the batch pays cash for what the Allowance
    can no longer carry (the market adapter, issue #65). Only a row whose
    declared link resolves no eligible pool row leaves the draw for the
    tickets that remain; its ticket falls through to the next row that still
    fits, wrapping to the start of the draw's order at the end -- the batch
    keeps assigning. Rows that hold no Allowance -- metered, Free, an
    uncataloged plan id -- keep drawing and never enter the ledger.
    Returns one row per pool model:
    {"mid", "share", "base", "pref", "draw", "tickets"}.

    `assign` is an optional out-list (issue #72): when the caller passes
    one, every draw appends the mid the batch's ticket landed on — or None
    when the draw left the ticket unassigned (every row at cap) — so
    position i records which model took ticket i+1, the draw keyed
    `seed::i`. The lane and the ticket map read that record; callers that
    pass none are untouched.
    """
    blend_weight = parameters.blend_weight
    seed = parameters.seed
    tickets = parameters.tickets
    local = set(local)
    catalog = plans or {}
    ledger = ledger if ledger is not None else AllowanceLedger(
        catalog, local=local)
    pool = eligibility_pool(share, models, aff, parameters.top_k,
                            parameters.admitted, local=local, plans=catalog)
    # The second brace on this function's own output: an uncataloged plan id
    # that reached the pool any other way is dropped before the draw.
    pool = [(mid, s) for mid, s in pool
            if not is_plan_route(mid, local=mid in local)
            or mid in catalog]
    if not pool:
        return []
    bases = blend_bases(pool, parameters.fit_adjusted_task_scores)
    favor = parameters.favor or {}
    prefs = [weight_for(mid, aff) * favor.get(mid, 1.0)
             for mid, _ in pool]
    pt, at = sum(bases) or 1.0, sum(prefs) or 1.0
    draws = [(1 - blend_weight) * (p / pt) + blend_weight * (a / at)
             for p, a in zip(bases, prefs)]
    dt = sum(draws) or 1.0
    draws = [d / dt for d in draws]
    counts = [0] * len(pool)
    evicted = [False] * len(pool)
    # A plan row that crosses a cap has its slot continue as its Metered
    # Twin: the ticket it would have taken lands on the Twin, and so does
    # every later ticket the same slot draws -- identity preserved, market
    # flipped, the family's drawn share unchanged (issue #65). -1 is "no
    # Twin resolved"; such a row leaves the draw as before.
    twins = [-1] * len(pool)
    cum, run = [], 0.0
    for d in draws:
        run += d
        cum.append(run)
    # The ledger's draw loop: the batch is assumed to land in ONE 5-hour
    # burst, so each ticket is booked against the 5-hour, weekly and monthly
    # windows alike and judged as it is assigned -- a row whose next ticket
    # would cross a window's cap hands its slot to its family's Twin, and
    # only a row whose declared link resolves no eligible Twin leaves the
    # draw for the tickets that remain, the ticket falling through to the
    # next row that still fits. The fall-through is circular, still the
    # draw's own order: a ticket drawn past an at-cap last row wraps to the
    # start and takes the first non-evicted row, so no ticket is abandoned
    # while any row still fits (US6 -- the batch continues within the plan).
    # Only when every row is evicted does a ticket go unassigned. The draw
    # itself stays keyed as it was -- ticket i's number is still seed::i --
    # so an at-cap row changes who takes a ticket, never the seeded order
    # they are offered in; no re-deal and no renormalization.
    for i in range(tickets):
        r = random.Random(f"{seed}::{i}").random() * run
        start = next((j for j, c in enumerate(cum) if r <= c), None)
        if start is None:
            if assign is not None:
                assign.append(None)
            continue
        for step in range(len(cum)):
            j = (start + step) % len(cum)
            if evicted[j]:
                continue
            if twins[j] >= 0:
                k = twins[j]
                counts[k] += 1
                ledger.charge(pool[k][0])
                if assign is not None:
                    assign.append(pool[k][0])
                break
            mid = pool[j][0]
            if ledger.crosses(mid):
                k = _twin_index(mid, pool, catalog, local=local)
                if k is not None and k != j:
                    twins[j] = k
                    counts[k] += 1
                    ledger.charge(pool[k][0])
                    if assign is not None:
                        assign.append(pool[k][0])
                    break
                evicted[j] = True
                continue
            counts[j] += 1
            ledger.charge(mid)
            if assign is not None:
                assign.append(mid)
            break
        else:
            # Every row evicted: the draw left this ticket unassigned, and
            # the record keeps its position honest — None, no lane, no map.
            if assign is not None:
                assign.append(None)
    return [{"mid": mid, "share": s, "base": b, "pref": pr, "draw": d,
             "tickets": n}
            for (mid, s), b, pr, d, n
            in zip(pool, bases, prefs, draws, counts)]


def _spare_candidates(rows: list[dict], *, local=(),
                      sensitive=False) -> list[dict]:
    """The rows that missed the draw, in Spare order (issue #71, GLOSSARY
    "Spare"): the candidates the deal did not deal, best first.

    Two preferences order them, and Score breaks every tie:

    - Sensitive draws spares from local candidates only — the fence is
      admission's, so the Spare selection re-states it rather than trusting
      it: a non-local row is never a Sensitive Spare, whatever it scores
      (the run then finds itself exhausted instead of re-gated).
    - A non-sensitive ticket prefers a candidate that serves without a model
      load (a non-local route: failover is seconds, a local swap is minutes),
      Score breaking ties inside that class; only when no no-load candidate
      missed the draw does a load-required one stand.

    Score is the deal table's own number — the fit-adjusted task score
    (standing), the same `score` column the readout prints. The sort is
    stable, so equal scores fall back to the pool's own order.
    """
    local = set(local)
    missed = [row for row in rows if row["tickets"] == 0]
    if sensitive:
        missed = [row for row in missed if row["mid"] in local]
        missed.sort(key=lambda row: -row["base"])
        return missed
    missed.sort(key=lambda row: -row["base"])
    missed.sort(key=lambda row: 0 if row["mid"] not in local else 1)
    return missed


def spare_for(mid: str, rows: list[dict], *, local=(),
              sensitive=False) -> str | None:
    """`mid`'s Spare: the best candidate that missed the draw, never `mid`
    itself (issue #71). None means exhausted — every eligible candidate is
    dealt (or, Sensitive, every local one), and the caller reports that
    instead of reaching outside the fence for a taker."""
    for row in _spare_candidates(rows, local=local, sensitive=sensitive):
        if row["mid"] != mid:
            return row["mid"]
    return None


def deal_spares(rows: list[dict], *, local=(), sensitive=False) -> dict:
    """One named Spare per dealt model (issue #71): {dealt mid -> spare mid
    or None}. Rows that missed the draw are spares themselves and key
    nothing — every dealt row names exactly one candidate from behind the
    draw, and None records an exhausted deal."""
    return {row["mid"]: spare_for(row["mid"], rows, local=local,
                                  sensitive=sensitive)
            for row in rows if row["tickets"]}


def deal_lane(assign: list, *, local=()) -> list[dict]:
    """The single strict local lane (issue #72): one group per local-served
    model, its dealt ticket ids in assignment order, groups ordered by each
    model's first assignment — consecutive lane members share a served
    model, so the batch runs one model load at a time with minimal
    load/unload churn (spec US25).

    `assign` is plan_deal's out-record: position i is the mid that took
    ticket i+1 (the draw keyed `seed::i`), None when a draw went
    unassigned. Membership follows the served model alone — the harness's
    local facts, never an id's spelling (the ADR-0005 invariant), so a
    cloud ticket is absent from the lane whatever it draws. The result is
    stable for a fixed roster, listing, shape and seed.
    """
    groups: dict[str, list[int]] = {}
    local = set(local)
    for i, mid in enumerate(assign, 1):
        if mid is None or mid not in local:
            continue
        groups.setdefault(mid, []).append(i)
    return [{"model": qualified_id(mid, local=True), "tickets": ids}
            for mid, ids in groups.items()]


def tickets_by_model(rows: list[dict], *, assign: list, local=()) -> dict:
    """The batch's ticket id → model map, keyed by provider-qualified id in
    deal-row order: the ids each dealt row actually drew (issue #72). Rows
    that missed the draw key nothing; together with the lane — which names
    the local ids per model — the map makes every ticket id's model
    recoverable from the deal output. Unassigned draws (None in `assign`)
    name no model and so appear under no key."""
    dealt = [row for row in rows if row["tickets"]]
    local = set(local)
    return {qualified_id(row["mid"], local=row["mid"] in local):
            [i for i, mid in enumerate(assign, 1) if mid == row["mid"]]
            for row in dealt}


def spare_exhaustion_text(mid: str, *, sensitive: bool) -> str:
    """Why a ticket has no Spare left — the one sentence the readout's
    `spare:` note and a substitution's `blocked:` report share (issue #71).
    The parenthetical states the fence: Sensitive stops because the
    local-only rule is never re-gated, a non-sensitive run only fails after
    the no-load failover preference has had its pick."""
    if sensitive:
        return (f"no eligible local candidate missed the draw for {mid} "
                "(local-only fence holds; never re-gated)")
    return (f"no eligible candidate missed the draw for {mid} "
            "(no-load failover preferred first)")


# The reason classes a substitution records (issue #71): mechanical failures
# substitute automatically; a quality failure substitutes only on the
# harness's explicit dead-attempt report, so taste never reshuffles work
# mid-run (`--reason quality` alone is refused before anything is fetched).
SUBSTITUTION_REASONS = {
    "mechanical": ("mechanical — unreachable, out of quota or allowance, "
                   "unloadable (substituted automatically)"),
    "dead-attempt": ("dead-attempt — the harness's explicit failed-attempt "
                     "report (quality; substituted on the report alone)"),
}


