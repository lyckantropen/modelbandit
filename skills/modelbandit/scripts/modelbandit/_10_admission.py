from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
# --- Admission seam --------------------------------------------------------
# What a candidate exposes of the material it is fed. Exposure is a property
# of the serving route, never inferred from price: free does not imply trains,
# paid does not imply no-retention. Unknown free defaults to trains.
EXPOSURES = ("no-retention", "trains", "local")


@dataclasses.dataclass(frozen=True)
class Shape:
    """A Ticket shape's admission-relevant elements.

    Sensitive is decided from the material (`--sensitive`, carried as
    `material_sensitive`) or the place (a closed zone) and stays derived,
    never stored: `sensitive` is a read-only property, so the verdict cannot
    drift from its causes, no caller can read the raw input as the verdict,
    and gates cannot re-derive the join differently from one another (ADR
    0012). An exclusion prints its banner whatever made the shape Sensitive.
    `posture` is the free-use zone the run works under — `open` unless a
    closed declaration covers the place (ADR 0010). `domain` and `intent`
    are the ticket facts the Local roster's band judges against: which
    domain the run works (None when nothing judges one) and which effort
    rung it asks for.
    """

    material_sensitive: bool = False
    input_tokens: int | None = None
    context_headroom: float = 2.0
    context_margin: float = 0.5
    output_tokens: int | None = None
    posture: str = "open"
    domain: str | None = None
    intent: str = "measured"

    @property
    def sensitive(self) -> bool:
        """The Sensitive verdict: the material flag or a closed place,
        either firing is enough (ADR 0008). Derived on read, never stored
        (ADR 0012)."""
        return self.material_sensitive or self.posture == "closed"


@dataclasses.dataclass(frozen=True)
class Candidate:
    """The candidate facts admission judges: Exposure, serving, Footprint
    and — for a rostered local row — its Capability band."""
    id: str
    exposure: str
    is_free: bool = False
    context_length: int | None = None
    completion_cap: int | None = None
    output_multiplier: float = 1.0
    local: bool = False
    band: dict | None = None
    summary_missing: bool = False


def _shown_mid(mid: str, candidate: Candidate) -> str:
    """Format a row id with the table's Gap mark, byte-identically everywhere."""
    return f"{'† ' if candidate.summary_missing else ''}{mid}"


def facets_for_candidate(candidate: Candidate) -> dict | None:
    """The facet contract for a candidate's Route kind, or None when no kind
    classifies it: the one seam question a gate asks about a candidate."""
    return facets_for(candidate.id, local=candidate.local)


def resolve_exposure(mid: str, *, free_models: dict | None = None,
                     overrides: dict | None = None, local: bool = False,
                     plans: dict | None = None,
                     loopback: bool = True) -> str:
    """One candidate's Exposure, by precedence:

    explicit policy override (prefix-keyed) > locally served on a loopback
    endpoint > curated free catalog entry > the plans catalog entry > the
    default-exposure facet (a free-slug or harness serving trains, a market
    or plan serving no-retention); an id outside every kind keeps the
    default no-retention assumption.

    The default is the no-retention assumption — the account's data policy
    already holds it. A free route the catalog does not carry is exposed until
    the user says otherwise. A Plan route's training/retention fact is a
    curated one: it comes from the plans section, the same surface its list
    price and caps come from.

    Localness is a serving fact, never a catalogue claim: a `local` label on
    a remote serving identity is void - the classifier decides, and it says
    the remote namespaces (`:free`, `opencode/*`, `opencode-go/*`) are
    remote - so the serving facts answer even when a stale policy reached
    this far without validation. The harness's `lmstudio/*` namespace
    classifies local by itself, but `local` resolves only for a loopback
    endpoint on this machine (`loopback`): a LAN-served instance fails
    closed to the unknown-free default (`trains`) whatever claims reach
    here, until the policy's exposure-override map — the one source allowed
    to declare `local` outright — states it.
    """
    def overridden(value) -> str | None:
        # The override map may name `local` itself: the operator's explicit
        # statement about a serving, the escape hatch for a non-loopback one
        # — still void on an identity whose local label is void.
        if value == "local" and local_label_is_void(mid):
            return None
        return known_exposure(mid, value)

    def catalog_stated(value) -> str | None:
        # Every other source — the free and plans catalogs alike — earns
        # `local` only from the serving being loopback on this machine;
        # what survives then answers under the override rule.
        if value == "local" and not loopback:
            return None
        return overridden(value)

    match = longest_prefix_match(mid, overrides or {})
    if match is not None and (value := overridden(match[1])) is not None:
        return value
    if local and loopback:
        return "local"
    for catalog in (free_models or {}, plans or {}):
        match = longest_prefix_match(mid, catalog)
        entry = match[1] if match is not None else {}
        if isinstance(entry, dict) and entry.get("exposure") \
                and (value := catalog_stated(entry["exposure"])) is not None:
            return value
    facets = facets_for(mid, local=local)
    default = facets["default_exposure"] if facets else "no-retention"
    if default == "local" and not loopback:
        # The local kind's own default cannot resolve without loopback;
        # unknown Exposure for a Free route defaults to trains.
        return "trains"
    return default


def known_exposure(mid: str, value: str) -> str:
    """A policy-named Exposure, or a loud stop: a misspelt class would
    silently widen the gate."""
    if value not in EXPOSURES:
        raise SystemExit(f"unknown exposure '{value}' for {mid}; "
                         f"known: {', '.join(EXPOSURES)}")
    return value


def row_exposure(mid: str, policy: dict, *, local_ids, loopback: bool) -> str:
    """One ranked table row's Exposure cell: the same precedence admission
    judged — override map, local serving, catalogs and the loopback fact
    included — so the column can never disagree with the gate."""
    return resolve_exposure(mid, free_models=policy["free_models"],
                            overrides=policy.get("exposure", {}),
                            local=mid in local_ids,
                            plans=policy["plans"],
                            loopback=loopback)


def candidate_for(mid: str, policy: dict, *, local: bool = False,
                  model: dict | None = None,
                  endpoints: list[dict] | None = None,
                  intent: str = "measured",
                  loopback: bool = True,
                  roster: dict | None = None) -> Candidate:
    """The candidate facts a policy implies for one model id: Exposure from
    the policy's `exposure` override map, `free_models` and `plans` catalogs,
    plus its Free price class (the seam's answer) and Footprint capacities.
    `loopback` is the serving fact behind `local` Exposure — see
    resolve_exposure. `roster` is this machine's Local roster (entries keyed
    by harness id): an exact key match attaches the entry's Capability band —
    judgment only, it changes no serving fact, and an id the roster does not
    carry simply has no band to judge."""
    catalog_match = longest_prefix_match(mid, policy.get("free_models", {}))
    catalog_entry = catalog_match[1] if catalog_match is not None else {}
    is_free = is_free_route(mid, local=local)
    context_length = None
    if model:
        # The window the live serving reported for this candidate (the
        # probe's one narrow contribution, see merge_local_candidates) is
        # what the Context gate is judged against: the server enforces its
        # own capacity, not the curated figure.
        context_length = model.get("served_context_length")
    if context_length is None:
        context_length = (catalog_entry.get("context_length")
                          if isinstance(catalog_entry, dict) else None)
    if context_length is None and model:
        context_length = model.get("context_length")
    completion_cap = endpoint_completion_cap(endpoints)
    if (completion_cap is None and is_free
            and isinstance(catalog_entry, dict)):
        completion_cap = catalog_entry.get("max_completion_tokens")
    roster_entry = roster.get(mid) if roster else None
    band = roster_entry.get("band") if isinstance(roster_entry, dict) else None
    return Candidate(id=mid,
                      exposure=resolve_exposure(
                          mid, free_models=policy.get("free_models", {}),
                          overrides=policy.get("exposure", {}), local=local,
                          plans=policy.get("plans", {}),
                          loopback=loopback),
                      is_free=is_free,
                      local=local,
                      band=band if isinstance(band, dict) else None,
                      context_length=context_length,
                      completion_cap=completion_cap,
                      output_multiplier=(mult_for(model, intent) if model
                                         else EFFORT_MULTIPLIERS[intent]),
                      summary_missing=(bool(is_free)
                                       and not _free_summary(
                                           catalog_entry,
                                           policy.get("summaries", {}), mid)))


def free_route_ids(mids, policy: dict, *, local=()) -> set[str]:
    """The Free routes among `mids` - the price class the seam derives (see
    is_free_route). Never the price a record shows: a paid route
    may be cheap, and Free is what the harness serves for nothing."""
    local = set(local)
    return {mid for mid in mids if is_free_route(mid, local=mid in local)}


def deal_free_share(rows: list[dict], policy: dict, *, local=()) -> tuple[int, int]:
    """Count tickets dealt to Free routes, independent of their Exposure."""
    free = free_route_ids((row["mid"] for row in rows), policy, local=local)
    total = sum(row["tickets"] for row in rows)
    return sum(row["tickets"] for row in rows if row["mid"] in free), total


def deal_local_share(rows: list[dict], *, local=()) -> tuple[int, int]:
    """Count tickets dealt to this machine's own servings — the harness's
    local rows (issue #69): how much of the deal stays on this hardware.
    The set is the run's local facts alone; no id shape is re-judged here,
    so a remote route can never be counted local."""
    local = set(local)
    total = sum(row["tickets"] for row in rows)
    return sum(row["tickets"] for row in rows if row["mid"] in local), total


def share_line(label: str, tickets: int, dealt: int) -> str:
    """The deal's share readout: `<label>: N/M tickets (P%)`, a zero
    denominator reading 0% rather than dividing by nothing."""
    share = tickets / dealt if dealt else 0.0
    return f"{label}: {tickets}/{dealt} tickets ({share:.0%})"


# The standing non-leak contract marker (ADR 0008): every deal touching
# Sensitive material carries this line in its output, for the harness to
# apply at prompt time. Prompt authoring itself stays with the harness —
# this line is the marker, never the prompt.
NON_LEAK_NOTE = (
    "non-leak note: Sensitive material never leaves the machine "
    "(standing contract marker — apply at prompt time; the harness "
    "authors the prompt)")


@dataclasses.dataclass(frozen=True)
class Decision:
    """An admission verdict: admitted, or excluded with a visible reason.

    An excluded candidate is never hidden — the ranked table marks it and the
    deal does not draw it.
    """
    admitted: bool
    reason: str = ""


ADMITTED = Decision(True)


# The one question every gate asks about a run's shape (ADR 0008) is the
# Shape's own property: `sensitive` is the material flag or a closed place,
# derived on read and never stored (ADR 0012) - nothing downstream re-derives
# the join, so an exclusion prints its banner whatever made the shape
# Sensitive.

def exposed_prohibition(shape: Shape, candidate: Candidate) -> str | None:
    """The Exposure clause: why a non-local candidate may not serve a
    Sensitive shape, or None.

    This is the clause's canonical statement in code (ADR 0008 is the
    decision; the Shape property is where the join lives): everything else
    - the pre-flight, the spares' fence, the substitution record - points
    here, never re-derives.

    Only Exposure `local` may serve Sensitive work, whether Sensitive came
    from place or material (ADR 0008): `no-retention` is a vendor promise
    about storage, not about transit - Sensitive material leaves the
    machine on any remote route - so it is excluded alike with `trains`.
    Exposure, never price, decides; an excluded candidate is marked with
    its Exposure in the table and never hidden. A closed place is Sensitive
    by definition, so it refuses every non-local route on top of every
    remote free one.
    """
    if not shape.sensitive:
        return None
    if candidate.exposure == "local":
        return None
    return f"exposed ({candidate.exposure})"


def exposure_gate(shape: Shape, candidate: Candidate) -> Decision:
    """The Exposure gate; see `exposed_prohibition`."""
    reason = exposed_prohibition(shape, candidate)
    return Decision(reason is None, reason or "")


def band_gate(shape: Shape, candidate: Candidate) -> Decision:
    """The Local roster's Capability band: hard exclusion, named per
    dimension — the binding judgment on the local row only.

    Only a rostered id carries a band (exact key match on the harness's own
    id, attached by candidate_for), so the gate judges exactly the rows the
    roster speaks for and never touches anyone else's admission. Each
    dimension excludes with its own named reason, in the spirit of the
    context gate's `over window`: the ticket's domain outside the band, the
    effort rung over the Difficulty ceiling, the shape's Footprint over the
    context-demand ceiling. Understating a band costs only reach;
    overstating one fails at the ticket — and never at the window: the
    Footprint is measured from the shape, the band ceiling is the number
    enforced, and the probed context window stays the Context gate's own
    (GLOSSARY, Capability band).
    """
    band = candidate.band
    if not isinstance(band, dict):
        return ADMITTED
    reasons = []
    domains = band.get("domains")
    if not isinstance(domains, list):
        domains = []
    if shape.domain is not None and shape.domain not in domains:
        if domains:
            reasons.append(f"outside band (domain '{shape.domain}' not in "
                           f"band: {', '.join(domains)})")
        else:
            reasons.append(f"outside band (domain '{shape.domain}' — the "
                           f"band admits no domain)")
    ceiling = band.get("difficulty")
    if ceiling in INTENTS and shape.intent in INTENTS \
            and INTENTS.index(shape.intent) > INTENTS.index(ceiling):
        # Same ladder, one comparison: the band's ceiling and the ticket's
        # effort rung are rungs of the one effort ladder (GLOSSARY,
        # Difficulty — deliberation judged, never measured against a window).
        reasons.append(f"over difficulty ceiling (effort {shape.intent} > "
                       f"{ceiling})")
    demand = band.get("context_demand")
    if shape.input_tokens is not None and _is_plain_int(demand) \
            and demand > 0:
        # The shape's Footprint (input x growth headroom), measured from the
        # token profile — the band ceiling is the enforced number, and no
        # window figures in this comparison at all (the probed window stays
        # the Context gate's own).
        footprint = shape.input_tokens * shape.context_headroom
        if footprint > demand:
            reasons.append(
                f"over band footprint (footprint {footprint:,.0f} over "
                f"context-demand ceiling {demand:,} tokens)")
    if not reasons:
        return ADMITTED
    return Decision(False, "; ".join(reasons))


def context_gate(shape: Shape, candidate: Candidate) -> Decision:
    """Compare both Footprint dimensions to capacity using shared policy.

    A Free route that overruns either dimension is excluded. Paid routes remain
    admitted, but return the same reasons for the ranked table to flag.
    """
    reasons = []
    if candidate.context_length is None:
        if candidate.is_free:
            reasons.append("unknown context window")
    elif shape.input_tokens is not None:
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


def zone_prohibition(posture: str, candidate: Candidate) -> str | None:
    """Why a closed posture forbids this candidate outright, or None.

    The one zone predicate, evaluated on the posture value: a closed place
    refuses exactly the remote, unaccountable servings - the free-slug and
    harness kinds - whatever their price, while a market or plan serving is
    accountable and a model this machine serves never leaves it and stays in.
    An open posture forbids nothing; Exposure and the quota answer for the
    rest. Four askers call it: the pre-flight block, the candidate source
    filter, the Zone gate, and provenance's closed-place question - the
    probe candidate there exists so this predicate's route-kind facets are
    the only judge.

    A candidate it names never enters the candidate set, so it is not ranked,
    scored, dealt or listed. The header states the zone that made it absent
    (`zone: <path> (closed)`), which is how the absence is explained without
    a row and without a reason column.
    """
    facets = facets_for_candidate(candidate)
    if (facets and facets["zone_refusable_in_closed_zones"]
            and posture == "closed"):
        return "remote free route is prohibited by the closed zone"
    return None


def filter_zone_candidates(share: dict, models: dict, policy: dict, *,
                           local_ids, posture: str, intent: str,
                           loopback: bool = True) -> dict:
    """Drop routes prohibited by a closed zone before ranking or scoring.

    The candidate built here carries the run's serving facts — the loopback
    fact among them — rather than defaulting a local row to loopback: a
    default that assumes the serving is this machine's fails open against
    what the run actually observed, and the row must read here exactly as the
    admission that judges it later reads it."""
    return {mid: value for mid, value in share.items()
            if zone_prohibition(posture, candidate_for(
                mid, policy, local=mid in local_ids, model=models.get(mid),
                intent=intent, loopback=loopback)) is None}


def zone_gate(shape: Shape, candidate: Candidate) -> Decision:
    """The zone clause behind the one decision; see `zone_prohibition`.

    Admission refuses too, though the source filter should never let such a
    candidate reach it: one verdict, whichever path asks.
    """
    reason = zone_prohibition(shape.posture, candidate)
    return Decision(reason is None, reason or "")


# The gates, in order, behind the one decision. The Zone gate comes first: a
# route a closed zone forbids outright does not need its Exposure, band or
# Footprint judged, and the first failing gate is the reason the table shows.
# The band sits beside them: judgment about the rostered local row, after the
# zone and Exposure facts, before the mechanical capacity checks. Editorial
# completeness is not an admission gate: a Free route without a resolving
# summary remains eligible and is marked in the table (ADR-0011).
GATES = (zone_gate, exposure_gate, band_gate, context_gate)


def quota_gate(candidate: Candidate, verdict: QuotaVerdict) -> Decision:
    """The Free-request quota gate: the counter's own facet answers.

    The counter is an OpenRouter account fact spent by the servings the
    facet contract charges to it - the free-slug kind alone. A
    harness-served model, a plan route or a model this machine serves
    spends none of it, so a spent counter says nothing about them; a paid
    route is charged credits, not free requests.
    """
    facets = facets_for_candidate(candidate)
    if (not verdict.eligible and facets
            and facets["spends_free_request_counter"]):
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


