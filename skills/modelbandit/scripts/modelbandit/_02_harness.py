from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
# --- Harness listing seam --------------------------------------------------
# What local models exist belongs to the harness: this run's local universe
# is passed in with --local-listing (the harness's own `opencode models`
# output), and the serving endpoint is read from the harness's config. The
# script never discovers a local model on its own — the probe below is two
# narrow facts about an already-listed candidate, never identity.


def is_harness_local_id(mid) -> bool:
    """Whether `mid` is exactly a harness-local id: the harness's own local
    namespace followed by a non-empty model path — no empty segment, no
    bare namespace.

    The one spelling of the namespace rule every consumer answers to: the
    --local-listing filter (what may seed a local candidate), the route
    classifier (what classifies `local`) and the Local roster loader (what
    keys an entry). A malformed namespace fails closed everywhere — it is
    never local, whatever asks."""
    return isinstance(mid, str) \
        and mid.startswith(HARNESS_LOCAL_NAMESPACE) \
        and all(mid[len(HARNESS_LOCAL_NAMESPACE):].split("/"))


def parse_local_listing(values) -> set[str] | None:
    """The local universe the harness passed in, or None when it did not.

    Each --local-listing value may carry comma-separated ids. Absent means
    unknown — the harness never spoke, so nothing joins and nothing is
    judged unrunnable — while a flag that states no local id is an empty
    universe the report may judge. Only the harness's local namespace
    survives the filter: a foreign id can never seed a local candidate, so
    what joins is exactly what the harness dispatches as `lmstudio/*`.
    """
    if not values:
        return None
    if isinstance(values, str):
        values = [values]
    ids = set()
    for chunk in values:
        for mid in str(chunk).split(","):
            mid = mid.strip()
            if is_harness_local_id(mid):
                ids.add(mid)
    return ids


def _strip_json_comments(text: str) -> str:
    """JSONC to JSON: drop `//` and `/* */` comments outside string literals,
    so a `//` inside a URL value survives while the harness's comments do
    not."""
    out = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def read_local_endpoint(path: str) -> str | None:
    """The harness local provider's baseURL from one config file, or None.

    Any unreadable or unparseable file says nothing rather than failing the
    run: the endpoint is one fact, and its absence falls back to the next
    config source and finally the loopback default.
    """
    try:
        with open(path, encoding="utf-8") as f:
            config = json.loads(_strip_json_comments(f.read()))
    except (OSError, ValueError):
        return None
    if not isinstance(config, dict):
        return None
    provider = config.get("provider")
    entry = provider.get("lmstudio") if isinstance(provider, dict) else None
    options = entry.get("options") if isinstance(entry, dict) else None
    base = options.get("baseURL") if isinstance(options, dict) else None
    return base.strip() if isinstance(base, str) and base.strip() else None


def harness_config_paths(cwd: str | None = None) -> list[str]:
    """Where the harness declares its providers: the project config first,
    then the user config (XDG_CONFIG_HOME when the machine states it, else
    `~/.config`), both spellings the harness accepts."""
    cwd = os.getcwd() if cwd is None else cwd
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    root = os.path.join(config_home, "opencode")
    return [os.path.join(cwd, "opencode.json"),
            os.path.join(cwd, "opencode.jsonc"),
            os.path.join(root, "opencode.json"),
            os.path.join(root, "opencode.jsonc")]


def harness_serving_endpoint(paths: list[str] | None = None) -> str:
    """The baseURL the harness's local provider serves on — the endpoint
    `local` Exposure's loopback rule judges — defaulting to LM Studio's
    loopback binding when no config declares one."""
    for path in harness_config_paths() if paths is None else paths:
        if (base := read_local_endpoint(path)) is not None:
            return base
    return DEFAULT_LOCAL_ENDPOINT


def loopback_endpoint(url: str | None) -> bool:
    """Whether the serving endpoint is loopback on this machine — the one
    condition `local` Exposure resolves under. Anything unparseable, empty,
    or bound elsewhere (a LAN or tailnet name, `0.0.0.0`) is not loopback,
    so a non-local serving fails closed until the policy's exposure-override
    map declares it."""
    if not isinstance(url, str) or not url:
        return False
    try:
        host = urllib.parse.urlparse(url).hostname
    except ValueError:
        return False
    if not host:
        return False
    return host == "localhost" or host == "::1" or host.startswith("127.")


def models_url(endpoint: str | None) -> str:
    """The probe's URL: the serving endpoint's `/v1/models` document."""
    if not endpoint:
        return LOCAL_MODELS_URL
    return endpoint.rstrip("/") + "/models"


def norm_id(model_id: str) -> str:
    return model_id.removeprefix("openrouter/")


_ROUTE_FACETS = {
    "market": {
        "zone_refusable_in_closed_zones": False,
        "default_exposure": "no-retention",
        "spends_free_request_counter": False,
        "priced_by_endpoint_spread": True,
        "standing_from": "boards",
    },
    "free-slug": {
        "zone_refusable_in_closed_zones": True,
        "default_exposure": "trains",
        "spends_free_request_counter": True,
        "priced_by_endpoint_spread": False,
        "standing_from": "own board row",
    },
    "harness": {
        "zone_refusable_in_closed_zones": True,
        "default_exposure": "trains",
        "spends_free_request_counter": False,
        "priced_by_endpoint_spread": False,
        "standing_from": "family share",
    },
    "plan": {
        "zone_refusable_in_closed_zones": False,
        "default_exposure": "no-retention",
        "spends_free_request_counter": False,
        "priced_by_endpoint_spread": False,
        "standing_from": "deferred to plan economics",
    },
    "local": {
        "zone_refusable_in_closed_zones": False,
        "default_exposure": "local",
        "spends_free_request_counter": False,
        "priced_by_endpoint_spread": False,
        "standing_from": "family share",
    },
}


def classify_route(mid: str, *, local: bool = False) -> str | None:
    """Classify a serving identity from its normalized id and local-serving fact."""
    if local:
        return "local"
    if not isinstance(mid, str):
        return None

    # The harness's own local namespace claims local by itself: the id shape
    # is a serving fact, so `lmstudio/*` classifies without the serving flag
    # and without any catalogue consulted — checked before norm_id so an
    # `openrouter/lmstudio/*` market slug stays the remote serving it is.
    # A malformed namespace (no model path, an empty segment) fails closed
    # — is_harness_local_id is the one spelling of that rule.
    if mid.startswith(HARNESS_LOCAL_NAMESPACE):
        return "local" if is_harness_local_id(mid) else None

    mid = norm_id(mid)
    if mid.startswith("opencode-go/"):
        return "plan" if all(mid[len("opencode-go/"):].split("/")) else None
    if mid.startswith("opencode/"):
        return "harness" if all(mid[len("opencode/"):].split("/")) else None

    parts = mid.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    if parts[1].endswith(":free"):
        return "free-slug" if parts[1][:-len(":free")] else None
    return "market"


def route_facets(kind: str) -> dict | None:
    """Return the serving-facet contract for a kind, or None if it is unknown."""
    facets = _ROUTE_FACETS.get(kind)
    return dict(facets) if facets is not None else None


def facets_for(mid: str, *, local: bool = False) -> dict | None:
    """The facet contract for one id's Route kind, or None when no kind
    classifies it: the one seam question a bare-id site asks."""
    return route_facets(classify_route(mid, local=local))


def _is_plain_int(value) -> bool:
    """True for integers, excluding bool (which is an int subclass)."""
    return isinstance(value, int) and not isinstance(value, bool)


# The Free price class: the kinds that serve at $0 (GLOSSARY, Free route) -
# every contract-table kind but the two priced ones, so membership is tied
# to the facet table.
FREE_KINDS = frozenset(_ROUTE_FACETS) - {"market", "plan"}


def is_free_route(mid: str, *, local: bool = False) -> bool:
    """The Free price class (GLOSSARY): a $0 serving - an OpenRouter `:free`
    slug, an OpenCode `opencode/*` model, or a model this machine serves.
    Derived from the Route-kind seam, never re-spelled from the id's shape:
    what serves an id is the classifier's answer alone. This is what the
    Nominal floor, the Context gate and the Free share count - not the zone
    or quota question; those gates ask their own facets."""
    return classify_route(mid, local=local) in FREE_KINDS


def is_plan_route(mid: str, *, local: bool = False) -> bool:
    """Whether the seam answers the plan kind for this id - the check the
    pool choke points use to release only the plan rows the plans catalog
    prices. The local serving fact outranks the id shape, so a plan-shaped
    id this machine serves is a local row, never a plan one."""
    return classify_route(mid, local=local) == "plan"


# The full-quality serving kinds: the kinds that serve a family's model at its
# own quality, so a family's board share is split across them. A Free serving
# is a rate-limited surrogate and keeps its discounted inheritance instead
# (see _family_share). The kind comes from the classifier, never the id shape.
_FULL_QUALITY_KINDS = frozenset({"market", "plan"})


def family_key(mid: str) -> str | None:
    """The model family a serving identity belongs to.

    A family is the model, not its market: `deepseek/deepseek-v4-pro` and its
    plan serving `opencode-go/deepseek-v4-pro` are one family because they
    serve one model. The family is the last path segment of the normalized id
    with any `:free` suffix removed, and an id no Route kind classifies has no
    family. The one place family identity is derived — the split family share
    reads it, never the id's spelling.
    """
    if classify_route(mid) is None:
        return None
    name = norm_id(mid).rsplit("/", 1)[-1].removesuffix(":free")
    return name or None


# The kinds OpenRouter serves: their ids dispatch through the `openrouter/`
# namespace a model config consumes. A `:free` slug is an OpenRouter serving
# too -- the same route's rate-limited variant, not another provider's.
_OPENROUTER_KINDS = frozenset({"market", "free-slug"})


def qualified_id(mid: str, *, local: bool = False) -> str:
    """The provider-qualified id a model config consumes: `<provider>/<model>`.

    The deal and the pick name a market, so an OpenRouter serving is
    re-prefixed with the namespace its configs dispatch through --
    `openrouter/` plus the normalized slug (norm_id) -- and every id already
    carrying its provider namespace (`opencode/*`, `opencode-go/*`,
    `lmstudio/*`) or a model this machine serves passes through unchanged.
    The Route kind is the classifier's answer, never the id's spelling; an
    id no kind classifies is left as written, since nothing in the run can
    dispatch it.
    """
    if classify_route(mid, local=local) in _OPENROUTER_KINDS:
        return "openrouter/" + norm_id(mid)
    return mid


