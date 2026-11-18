from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
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


# --- Cost seam -------------------------------------------------------------
# What a ticket costs, in one bounded region, answered three ways: the
# ticket cost (the endpoint bases worst/primary/best and the blended
# arithmetic behind them), the Draw (what one ticket burns of a plan's
# Allowance, at the plan's list price), and the at-cap verdict (whether a
# ticket's Draw would cross an Allowance window's cap). The pricing
# arithmetic, the effort rungs and their multipliers, the Nominal floor's
# pool-cheapest derivation and the one marginal-zero rule (ADR-0006) are
# internals: nothing outside re-derives a price -- the score and the deal
# ask the seam for an answer, never the arithmetic.


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


def priced_endpoints(mid: str, *, local_ids, refresh: bool) -> list[dict]:
    """Endpoint rows for the kinds Endpoint spread prices - the market kind
    alone (the seam's facet) - and none for any other row: a Free route
    prices from its zero record and a plan route from its own record when
    plan economics land, so nothing else fetches the endpoints catalog.
    ``local_ids`` are the ids this machine serves; the local serving fact
    outranks the id shape."""
    if not priced_by_endpoint_spread(mid, local=mid in local_ids):
        return []
    return endpoint_pricings(mid, refresh)


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
    return min(requested_rung_index(ladder, intent), len(ladder) - 1)


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


def ticket_draw(mid: str, plans: dict, *, local: bool = False) -> float | None:
    """The Draw one ticket of this route burns: what it consumes of an
    Allowance, counted at the plan's list price (GLOSSARY, Draw). A Plan
    route answers its catalog entry's list price -- the free-in-plan,
    zero-Draw serving answers 0 -- and every other serving answers None: a
    Free route, a metered route, or a plan-shaped id this machine serves
    has no Allowance to draw down (the local serving fact outranks the id
    shape). Plan-ness is the Route-kind seam's answer (is_plan_route), and
    the price comes from the validated plans catalog alone, so a plan route
    the catalog does not price has no Draw to answer."""
    if not is_plan_route(mid, local=local):
        return None
    entry = plans.get(mid)
    price = entry.get("list_price") if isinstance(entry, dict) else None
    return float(price) if _is_finite_number(price) and price >= 0 else None


def nominal_floor_cost(free_risk: float, cheapest_paid_ticket: float) -> float:
    """The Nominal floor: Free risk times the pool's cheapest paid ticket.
    The no-Draw case of the one marginal-zero rule (ADR-0006) -- a Free
    route's ticket cost, and a zero-Draw plan serving's fallback alike.
    """
    return free_risk * cheapest_paid_ticket


# Allowance caps are decimal dollar figures and the drawn sums are binary
# floats: an exactly-reaching decimal batch (0.2 + 0.1 against 0.3) lands a
# few ulps past its cap. The one crossing answer carries this money-noise
# tolerance so exactly-reaching never crosses, while any true crossing --
# a cent or a tenth of a cent -- still does.
CAP_MONEY_NOISE = 1e-9


def at_cap_verdict(mid: str, plans: dict, drawn: dict,
                   *, local: bool = False) -> dict[str, bool]:
    """The at-cap answer, per window: whether one more ticket of this route
    would cross each Allowance window's cap. `plans` is the policy's
    validated plan catalog -- the caps and the Draw both read from the
    route's own entry -- and `drawn` is the Draw the run has already
    allotted this route, per window (a window nothing is drawn against
    starts at zero). A window the entry states no cap for earns no verdict,
    and a route with no Allowance -- a metered route, a Free route, an
    uncataloged plan route -- earns none at all. The allowance ledger
    tracks the drawn totals live, prospective and in-run with no state
    across runs, and consumes this answer per ticket; eviction itself is
    the ledger's business, never the pricing's.

    The comparison carries a small money-noise tolerance
    (CAP_MONEY_NOISE): caps are decimal dollar figures, and the sums that
    reach them are binary floats -- 0.2 + 0.1 lands just past 0.3 -- so an
    exactly-reaching decimal batch must never read as crossing, while any
    true crossing (far above the noise) still does. This is the one
    crossing answer; the tolerance lives here, not in the score's
    risk-of-Draw arithmetic.
    """
    entry = plans.get(mid)
    caps = entry.get("caps") if isinstance(entry, dict) else None
    draw = ticket_draw(mid, plans, local=local)
    if not isinstance(caps, dict) or draw is None:
        return {}
    return {window: drawn.get(window, 0.0) + draw > cap + CAP_MONEY_NOISE
            for window, cap in caps.items()}


class AllowanceLedger:
    """The prospective allowance ledger: three windows, one burst, in-run.

    Every ticket the run assigns a Plan route draws that model's Allowance
    down in all three windows at once -- the batch is assumed to land in ONE
    5-hour burst, so a ticket counts against the rolling 5-hour window, the
    week and the month alike. That is the conservative read: a batch on
    course to cross a window is flagged by the run that would cross it, not
    discovered after the monthly total is gone.

    The ledger is prospective and in-run: it starts every run empty, reads
    no account state and writes none, so two identical runs answer
    identically and a plan other harnesses share is never planned against a
    local fiction. The caps are real boundaries -- no reserve is held back
    against usage this run cannot see, and no overflow flag exists: a row
    whose next ticket would cross a window leaves the draw for the tickets
    that remain, and the batch carries on with the rows that still fit.
    Substitution to the route's Metered Twin is the deal's market adapter
    (plan_deal), never the ledger's.

    The crossing arithmetic is the cost seam's (at_cap_verdict); the ledger
    owns only the drawn totals it feeds that answer, and a route with no
    Allowance -- a metered route, a Free route, a plan route the catalog
    does not price -- keeps no totals at all.
    """

    def __init__(self, plans: dict | None = None, *, local=()):
        self.plans = plans or {}
        self.local = frozenset(local)
        self._drawn: dict[str, dict[str, float]] = {}

    def _caps(self, mid: str) -> dict:
        """The window caps `mid` draws down, as its plans entry states them.
        A route with no Allowance -- a metered route, a Free route, a plan
        route the catalog does not price, a plan id this machine serves --
        keeps none, so the windows it cannot draw are not stated."""
        if ticket_draw(mid, self.plans, local=mid in self.local) is None:
            return {}
        entry = self.plans.get(mid)
        caps = entry.get("caps") if isinstance(entry, dict) else None
        return caps if isinstance(caps, dict) else {}

    def drawn(self, mid: str) -> dict[str, float]:
        """The Draw this run has allotted `mid` so far, per window -- zero
        where nothing has been drawn yet. A route with no Allowance keeps no
        windows and so answers nothing."""
        totals = self._drawn.get(mid, {})
        return {window: totals.get(window, 0.0) for window in self._caps(mid)}

    def readout(self, mid: str) -> dict[str, dict[str, float]]:
        """The figures an `allowance draw:` line states for `mid`, per window:
        what this run has drawn and the cap it draws against. `{}` for a
        route with no Allowance (no line is printed for it). A readout, not a
        verdict: the caller only formats these numbers."""
        caps = self._caps(mid)
        totals = self._drawn.get(mid, {})
        return {window: {"drawn": totals.get(window, 0.0), "cap": cap}
                for window, cap in caps.items()}

    def at_cap(self, mid: str) -> dict[str, bool]:
        """Whether one more ticket of `mid` would cross each window's cap:
        the seam's verdict over this ledger's own drawn totals."""
        return at_cap_verdict(mid, self.plans, self._drawn.get(mid, {}),
                              local=mid in self.local)

    def crosses(self, mid: str) -> bool:
        """Whether one more ticket of `mid` would cross any window's cap."""
        return any(self.at_cap(mid).values())

    def charge(self, mid: str) -> bool:
        """Allot one ticket of `mid` to every window it draws down.

        True when the route keeps an Allowance: the ticket's Draw is booked
        against all three windows alike, the one-burst read. False when it
        keeps none -- a metered route, a Free route, a plan route the
        catalog does not price never enters the ledger. The verdict that
        keeps a ticket out is the caller's ask (at_cap), never a refusal
        here: the ledger records what the draw assigned.
        """
        draw = ticket_draw(mid, self.plans, local=mid in self.local)
        if draw is None:
            return False
        totals = self._drawn.setdefault(mid, {})
        for window in self._caps(mid):
            totals[window] = totals.get(window, 0.0) + draw
        return True


def effective_costs(costs: dict, *, free_risk: float,
                    free: set[str] | frozenset[str] = frozenset(),
                    plans: dict | None = None) -> dict:
    """The score's cost term for one pool: the one marginal-zero rule
    (ADR-0006) -- a marginal-zero ticket prices as risk of its Draw, never
    at $0.

    `free` names the pool's Free routes (see free_route_ids), never inferred
    from a zero price, and carries the serving facts; `plans` is the
    policy's validated plan catalog, the facts the Draw reads. A Plan route
    prices as Free risk times its own list-priced Draw; where there is no
    Draw -- a Free route, a zero-Draw plan serving, a plan route the catalog
    does not price -- the Nominal floor answers: Free risk times the
    cheapest priced paid ticket, or the $1 reference when the pool has
    none. Paid tickets keep their own price, and a paid ticket that priced
    at nothing keeps the pool's cheapest paid ticket. A valid risk fraction
    keeps every marginal-zero answer positive -- the floor strictly below
    the pool's cheapest paid ticket when one exists -- so no ticket wins by
    dividing by zero.
    """
    catalog = plans or {}
    # Plan-ness is the Route-kind seam's answer (is_plan_route), never the
    # catalog's; a plan-shaped id the machine serves is a Free route (the
    # caller's `free` set carries the serving fact), never a plan one.
    plan_routes = {mid for mid in costs if is_plan_route(mid)} - set(free)
    draws, floor_ids = {}, set()
    for mid in costs:
        if mid in free:
            floor_ids.add(mid)
        elif mid in plan_routes:
            draw = ticket_draw(mid, catalog)
            if draw:
                draws[mid] = free_risk * draw
            else:
                floor_ids.add(mid)
    paid = [v for mid, v in costs.items()
            if mid not in free and mid not in plan_routes and v > 0]
    cheapest_paid = min(paid, default=NOMINAL_REFERENCE_TICKET)
    nominal_floor = (nominal_floor_cost(free_risk, cheapest_paid)
                     if floor_ids else None)
    return {mid: (draws[mid] if mid in draws else
                  nominal_floor if mid in floor_ids else
                  v if v > 0 else cheapest_paid)
            for mid, v in costs.items()}


