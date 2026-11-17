from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
def band_line(mid: str, band: dict | None) -> str:
    """The fence's band restatement in a substitution record: the Spare's
    own Capability band when the roster speaks for it, or the honest
    absence — the band is the roster's judgment on a local row and never
    binds a cloud route (GLOSSARY, Capability band)."""
    if not isinstance(band, dict):
        return (f"none binds {mid} (the Capability band judges a rostered "
                "local row only)")
    domains = ", ".join(str(d) for d in band.get("domains") or []) or "none"
    parts = [f"domains {domains}"]
    difficulty = band.get("difficulty")
    if difficulty:
        parts.append(f"difficulty ceiling {difficulty}")
    demand = band.get("context_demand")
    if _is_plain_int(demand):
        parts.append(f"context-demand ceiling {demand:,} tokens")
    return f"{mid}: " + "; ".join(parts)


def run_substitution(target: str, reason: str, rows: list[dict], *,
                     ctx: RunContext, sensitive: bool = False,
                     as_json: bool = False,
                    assign: list | None = None) -> int:
    """The substitution record (issue #71): the named model's Spare takes
    the ticket over whole, the fence restated, the reason recorded — and
    the lane effect stated (issue #72): lane membership follows the served
    model, so a cloud Spare's tickets exit the strict lane, a local one's
    join it, and the record carries the post-substitution lane computed
    from the same seeded deal with this serve swapped in.

    Stateless by construction — the caller has re-derived the same seeded
    deal from the same flags, so this only reports the takeover the draw
    already named; nothing is stored, and the next invocation re-derives
    again (the AllowanceLedger's ethos: two identical runs answer
    identically). The fence is re-stated, never re-gated: a Sensitive
    substitution's Spare came from local candidates only, whatever a
    cloud route would have scored. A target outside this deal is a usage
    error (2); exhaustion is a verdict like any other — `blocked:`, exit 0,
    terminal for Sensitive (never re-gated), reported only after the
    no-load preference has had its pick elsewhere.
    """
    # The posture facts travel as one context; bind the names the body
    # already reads, so the single source stays visible at the signature.
    local, roster, zone = ctx.local_ids, ctx.roster, ctx.zone
    local = set(local)
    mid = norm_id(target)
    by_id = {row["mid"]: row for row in rows}
    if mid not in by_id:
        print(f"substitute: '{target}' is not part of this deal "
              "(the same seed and shape flags re-derive the same deal)",
              file=sys.stderr)
        return 2
    frm = qualified_id(mid, local=mid in local)
    to_mid = spare_for(mid, rows, local=local, sensitive=sensitive)
    if to_mid is None:
        text = spare_exhaustion_text(frm, sensitive=sensitive)
        if as_json:
            emit_json({"mode": "substitution", "ok": True,
                       "verdict": "blocked", "from": frm, "to": None,
                       "reason": text, "sensitive": sensitive,
                       "zone": zone_payload(zone)})
        else:
            _print_verdict(f"blocked: {text}")
        return 0
    to = qualified_id(to_mid, local=to_mid in local)
    entry = (roster or {}).get(to_mid)
    band = entry.get("band") if isinstance(entry, dict) else None
    tickets = by_id[mid]["tickets"]
    # The lane effect (issue #72): the ids this substitution moved are the
    # target row's own draws from the seeded assignment, and the emitted
    # lane is the seeded deal's lane with this serve swapped in — the same
    # record's takeover section states the move in words. A target that
    # missed the draw holds a ticket through an earlier substitution: no id
    # of this deal's assignment names it, so the words say `the held
    # ticket` and the lane (no id of it to move) stays as dealt.
    held = [i for i, m in enumerate(assign or [], 1) if m == mid]
    lane = deal_lane([to_mid if m == mid else m for m in (assign or [])],
                     local=local)
    ids = ", ".join(str(i) for i in held)
    if held:
        who, many = f"tickets {ids}", True
    else:
        who, many = "the held ticket", False
    if mid in local and to_mid in local:
        effect = (f"{who} {'move' if many else 'moves'} to {to} — "
                  "membership follows the serve")
    elif mid in local:
        effect = (f"{who} {'exit' if many else 'exits'} the lane — "
                  f"{to} is not local")
    elif to_mid in local:
        effect = (f"{who} {'join' if many else 'joins'} the lane — "
                  f"served by {to}")
    else:
        effect = "unchanged — neither serve is local"
    if as_json:
        emit_json({"mode": "substitution", "ok": True,
                   "verdict": "substituted", "from": frm, "to": to,
                   "reason": reason,
                   "reason_class": ("quality" if reason == "dead-attempt"
                                    else "automatic"),
                   "tickets": tickets, "sensitive": sensitive, "band": band,
                   "non_leak_note": (NON_LEAK_NOTE if sensitive else None),
                   "lane": lane,
                   "zone": zone_payload(zone)})
        return 0
    print(f"substitution: {frm} -> {to}")
    print(f"  reason: {SUBSTITUTION_REASONS[reason]}")
    if tickets:
        plural = "" if tickets == 1 else "s"
        print(f"  takeover: {to} takes the ticket over whole "
              f"({tickets} ticket{plural})")
    else:
        # The substituted model was itself a Spare already holding the
        # ticket (a second death): the held ticket still moves whole.
        print(f"  takeover: {to} takes the held ticket over whole")
    print(f"  lane: {effect}")
    print(f"  band: {band_line(to, band)}")
    if sensitive:
        # The fence label is the sensitive local-only rule's alone (spec #75,
        # output contract): the standing ADR 0008 citation lives in this
        # comment, never in a printed line.
        print("  fence: sensitive — local-only")
        print(NON_LEAK_NOTE)
    return 0


def policy_age_days(policy_path: str) -> int | None:
    try:
        return int((time.time() - os.path.getmtime(policy_path)) // 86400)
    except OSError:
        return None


def record_free_share_measurement(shape: dict, zero: bool) -> tuple[bool, int]:
    """Persist the last measurements for one ticket shape, keyed honestly.

    Returns (had_prior_measurement, trailing_zero_count). History is diagnostic
    cache data only; it never changes policy or Deal eligibility. Whether a
    shape's zero reaches the report is the caller's ruling - a Sensitive
    deal's remote-free zero is structural, not drift.
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


