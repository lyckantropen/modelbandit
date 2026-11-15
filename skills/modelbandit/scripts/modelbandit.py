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
import getpass
import hashlib
import json
import math
import os
import random
import re
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.parse
import urllib.request

MODELS_URL = "https://openrouter.ai/api/v1/models"
# The harness's local serving endpoint: LM Studio's own loopback default,
# overridden for this run by the baseURL the harness config declares.
DEFAULT_LOCAL_ENDPOINT = "http://127.0.0.1:1234/v1"
LOCAL_MODELS_URL = DEFAULT_LOCAL_ENDPOINT + "/models"
# The harness's local namespace — the ids it dispatches local models by
# (`lmstudio/<model>`), passed into the run as the listing that decides
# which local candidates exist. One spelling, shared by the classifier and
# the --local-listing filter.
HARNESS_LOCAL_NAMESPACE = "lmstudio/"
CLASS_URL = "https://openrouter.ai/api/v1/classifications/task?window=7d"
RANK_URL = "https://openrouter.ai/api/v1/datasets/rankings-daily"
KEY_URL = "https://openrouter.ai/api/v1/key"
BENCHMARKS_URL = "https://openrouter.ai/api/v1/benchmarks"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "modelbandit")
CACHE_TTL = 24 * 3600
# The free-request counter is spent as a run proceeds, so it is cached for a
# minute rather than the day the catalogues get.
KEY_CACHE_TTL = 60
# Free requests planning must leave unspent: the last few are not the plan's.
DEFAULT_FREE_QUOTA_RESERVE = 5
# A curated Free route inherits this fraction of its family's board share: the
# free serving is a limited-time, rate-limited surrogate, so it does not carry
# the family's full standing.
DEFAULT_FREE_SHARE_INHERITANCE = 0.5

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


def probe_local_models(fetcher=None, *, url: str = LOCAL_MODELS_URL
                       ) -> dict[str, dict]:
    """Probe the serving endpoint for its live models; failures are silent.

    Demoted to two narrow facts about candidates the harness listing
    already made real: the context window the Context gate is judged
    against, and whether a listed id is being served right now. It never
    establishes existence or identity — the harness's listing does — so a
    missing server has no effect on the candidate set or the readout.

    This is deliberately not cached: the local server and its loaded models
    can change between invocations. ``fetcher`` accepts the URL and returns
    decoded JSON, keeping the probe deterministic and network-free in unit
    tests.
    """
    if fetcher is None:
        def fetcher(fetch_url):
            with urllib.request.urlopen(fetch_url, timeout=1) as response:
                return json.load(response)

    try:
        payload = fetcher(url)
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


# --- Harness listing seam --------------------------------------------------
# What local models exist belongs to the harness: this run's local universe
# is passed in with --local-listing (the harness's own `opencode models`
# output), and the serving endpoint is read from the harness's config. The
# script never discovers a local model on its own — the probe below is two
# narrow facts about an already-listed candidate, never identity.


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
            if not mid.startswith(HARNESS_LOCAL_NAMESPACE):
                continue
            rest = mid[len(HARNESS_LOCAL_NAMESPACE):]
            if all(rest.split("/")):
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
        "zone_refusable_in_closed_regimes": False,
        "default_exposure": "no-retention",
        "spends_free_request_counter": False,
        "needs_policy_catalog_entry": False,
        "priced_by_endpoint_spread": True,
        "standing_from": "boards",
    },
    "free-slug": {
        "zone_refusable_in_closed_regimes": True,
        "default_exposure": "trains",
        "spends_free_request_counter": True,
        "needs_policy_catalog_entry": False,
        "priced_by_endpoint_spread": False,
        "standing_from": "own board row",
    },
    "harness": {
        "zone_refusable_in_closed_regimes": True,
        "default_exposure": "trains",
        "spends_free_request_counter": False,
        "needs_policy_catalog_entry": True,
        "priced_by_endpoint_spread": False,
        "standing_from": "family share",
    },
    "plan": {
        "zone_refusable_in_closed_regimes": False,
        "default_exposure": "no-retention",
        "spends_free_request_counter": False,
        "needs_policy_catalog_entry": True,
        "priced_by_endpoint_spread": False,
        "standing_from": "deferred to plan economics",
    },
    "local": {
        "zone_refusable_in_closed_regimes": False,
        "default_exposure": "local",
        "spends_free_request_counter": False,
        "needs_policy_catalog_entry": True,
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
    # A malformed namespace (no model path, an empty segment) fails closed.
    if mid.startswith(HARNESS_LOCAL_NAMESPACE):
        rest = mid[len(HARNESS_LOCAL_NAMESPACE):]
        return "local" if all(rest.split("/")) else None

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
    Nominal floor, the Context gate, the catalog gate and the Free share
    count - not the zone or quota question; those gates ask their own
    facets."""
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


def priced_by_endpoint_spread(mid: str, *, local: bool = False) -> bool:
    """Whether Endpoint spread prices this serving - the market kind's trait
    alone (the facet contract's `priced_by_endpoint_spread`). Non-market
    rows make no catalog fetch: a Free route prices from its zero record,
    and a plan route prices from its plans entry's Draw."""
    facets = facets_for(mid, local=local)
    return bool(facets and facets["priced_by_endpoint_spread"])


# The remote serving kinds: the contract-table kinds whose ids a policy
# `local` Exposure label can never claim - every kind but the two a
# slash-shaped id may legitimately carry (a market slug or a model this
# machine serves).
_REMOTE_KINDS = frozenset(_ROUTE_FACETS) - {"market", "local"}


def local_label_is_void(mid: str) -> bool:
    """Whether a policy `local` Exposure label is void for this id.

    Localness is a serving fact, never a catalogue claim: the classifier
    answers the remote serving namespaces remote whatever a label says - a
    `:free` slug, an `opencode/*` harness model, an `opencode-go/*` plan
    route - so a `local` label on one is void. The harness's `lmstudio/*`
    namespace classifies local by itself, and a market-shaped slash id is
    not voided either: a served model's id can be slash-shaped, so the
    label may claim one."""
    return classify_route(mid) in _REMOTE_KINDS


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


RULES_FILE = "modelbandit.secrets.json"
RULES_KEYS = ("phrases", "patterns")


def validate_secrets_rules(payload, *, writer: bool = False,
                           source: str = RULES_FILE) -> dict:
    """Validate rule values once for both file loading and the writer."""
    if not isinstance(payload, dict):
        raise SystemExit(f"secrets rules {source} must be a JSON object with "
                         f"{' / '.join(RULES_KEYS)}")
    allowed = set(RULES_KEYS) | ({"identifying", "commit"} if writer else set())
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise SystemExit(f"unknown secret rule key(s) in {source}: "
                         f"{', '.join(unknown)}; known: "
                         f"{', '.join(sorted(allowed))}")

    rules: dict = {}
    for key in RULES_KEYS:
        if key not in payload and not writer:
            continue
        values = payload.get(key, [])
        if not isinstance(values, list):
            raise SystemExit(f"{key} in {source} must be a list of strings")
        for index, entry in enumerate(values, 1):
            kind = "phrase" if key == "phrases" else "pattern"
            if not isinstance(entry, str) or not entry.strip():
                raise SystemExit(f"{kind} #{index} is not a non-empty string")
            if key == "patterns":
                try:
                    re.compile(entry)
                except re.error:
                    raise SystemExit(f"pattern #{index} is not a valid regex") \
                        from None
        rules[key] = list(values)

    if writer:
        # Either switch may stand alone: "identifying" implies gitignore, and
        # plain rules mean a committed file. Only a present, non-boolean value
        # is an error.
        defaults = {"identifying": False, "commit": True}
        for key, default in defaults.items():
            value = payload.get(key, default)
            if not isinstance(value, bool):
                raise SystemExit(f"{key} must be a boolean")
            rules[key] = value
    return rules


def load_secrets_rules(path: str) -> dict:
    """The project's Secrets rules, validated — additive only.

    `phrases` are literal inclusions, `patterns` regular expressions; both
    tighten the built-in default and neither can disable it, so an empty or
    absent file changes nothing. Anything else in the file is a loud stop:
    a rule the tool silently ignores is a rule the user believes in.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError):
        raise SystemExit(f"cannot read secrets rules file {path}") from None
    return validate_secrets_rules(payload, source=path)


# Machine facts are matched as inclusions, so an identifier short enough to
# occur in ordinary prose would make every shape Sensitive.
MIN_IDENTIFIER_LEN = 4
_LOOPBACK = ("127.", "0.0.0.0", "::1", "localhost")
# Fact class -> the rule name reported when it trips. The class keys are what
# machine_facts gathers; `identifiers` stays the flat form the gate accepts.
_IDENTIFIER_CLASSES = (("hostname", "hostname"), ("username", "username"),
                       ("home", "home path"), ("addresses", "local address"),
                       ("identifiers", "identifier"),
                       ("outside_file_contents", "outside-file content"),
                       ("passwords", "password"), ("tokens", "token"),
                       ("keys", "key"))
# The built-in credential rules, each named so the verdict says which bound.
_CREDENTIAL_RULES = (
    ("password, token or key assignment", _SECRET_VALUE_PATTERNS[0]),
    ("bearer token", _SECRET_VALUE_PATTERNS[1]),
    ("private key block", _SECRET_VALUE_PATTERNS[2]),
)


def _gather(reader):
    """One fact from the machine, best effort: never crash, never block."""
    try:
        return reader()
    except Exception:
        return None


def _local_addresses() -> list[str]:
    """This machine's non-loopback address, without sending a packet."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return [sock.getsockname()[0]]
    finally:
        sock.close()


def machine_facts(*, hostname=None, username=None, home=None,
                  addresses=None) -> dict:
    """The identifiers readable from this machine, gathered for the gate.

    Hostname, login, home path and local addresses, each best effort: a source
    that fails contributes nothing and the run carries on. The readers are
    injectable so a test states the machine instead of borrowing this one.
    Values shorter than ``MIN_IDENTIFIER_LEN`` and loopback/root paths are
    dropped — they identify nothing a reader of the material does not know,
    and they trip on ordinary prose.
    """
    readers = {"hostname": hostname or socket.gethostname,
               "username": username or getpass.getuser,
               "home": home or (lambda: os.path.expanduser("~")),
               "addresses": addresses or _local_addresses}
    facts: dict = {"identifiers": []}
    for field, reader in readers.items():
        value = _gather(reader)
        if field == "addresses":
            value = [address for address in (value or [])
                     if isinstance(address, str) and len(address) >= MIN_IDENTIFIER_LEN
                     and not address.startswith(_LOOPBACK)]
        elif not isinstance(value, str):
            value = ""
        else:
            # A bare root ("/", "C:\") identifies nothing.
            value = value.rstrip("/\\")
            value = value if len(value) >= MIN_IDENTIFIER_LEN else ""
        if not value:
            continue
        facts[field] = value
        facts["identifiers"].extend(value if isinstance(value, list) else [value])
    return facts


# Gitignored content is read, never scanned: a capped slice of a capped number
# of files, enough to catch a shape quoting a line of one.
GITIGNORED_MAX_FILES = 20
GITIGNORED_MAX_BYTES = 8192
# Below this a line is a label, not content a shape could quote.
GITIGNORED_MIN_LINE = 8


def _run_git(root: str):
    """A `git` runner bound to `root`, or None when git is unavailable."""
    def run(args):
        completed = subprocess.run(["git", "-C", root, *args],
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   timeout=10, check=False)
        if completed.returncode != 0:
            raise OSError(completed.stderr.strip() or "git failed")
        return completed.stdout
    return run


def _rules_file_is_tracked(root: str) -> bool:
    """Whether Git already tracks the project rules file in its index."""
    try:
        tracked = _run_git(root)(["ls-files", "--error-unmatch", "--",
                                 RULES_FILE])
    except Exception:
        return False
    return RULES_FILE in str(tracked or "").splitlines()


def gitignored_facts(root: str, *, run=None, reader=None,
                     max_files: int = GITIGNORED_MAX_FILES,
                     max_bytes: int = GITIGNORED_MAX_BYTES) -> list[dict]:
    """Significant lines from this tree's gitignored untracked files.

    `.gitignore` is the repository's own maintained list of what must not
    leave it, so a shape quoting one of those lines is carrying outside
    content. `run(args)` lists the files (`git ls-files --others --ignored
    --exclude-standard` by default) and `reader(path)` returns a file's text;
    both are injectable and either failing is silent — a missing git costs the
    run a rule, never a crash. Comments and short lines are dropped, and each
    line is kept once.
    """
    if run is None:
        run = _run_git(root)
    if run is None:
        return []
    if reader is None:
        def reader(path):
            with open(os.path.join(root, path), "rb") as f:
                return f.read(max_bytes).decode("utf-8", "replace")
    try:
        listed = run(["ls-files", "--others", "--ignored", "--exclude-standard"])
    except Exception:
        return []
    if isinstance(listed, bytes):
        listed = listed.decode("utf-8", "replace")
    paths = [line.strip() for line in str(listed or "").splitlines() if line.strip()]
    facts, seen = [], set()
    for path in paths[:max_files]:
        try:
            text = reader(path)
        except Exception:
            continue
        if not isinstance(text, str):
            continue
        text = text[:max_bytes]
        if "\0" in text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if len(line) < GITIGNORED_MIN_LINE or line.startswith("#"):
                continue
            if line in seen:
                continue
            seen.add(line)
            facts.append({"path": path, "line": line})
    return facts


def outside_file_contents(root: str, paths, *,
                          max_files: int = GITIGNORED_MAX_FILES,
                          max_bytes: int = GITIGNORED_MAX_BYTES) -> list[str]:
    """Capped content from explicitly named outside files, by significant line."""
    contents, seen = [], set()
    for named_path in list(paths or ())[:max_files]:
        path = (named_path if os.path.isabs(named_path)
                else os.path.join(root, named_path))
        try:
            with open(path, "rb") as f:
                text = f.read(max_bytes).decode("utf-8", "replace")
        except (OSError, TypeError):
            continue
        if "\0" in text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                contents.append(line)
    return contents


def secrets_verdict(material: str, *, machine: dict | None = None,
                    rules: dict | None = None) -> tuple[bool, str]:
    """The Secrets gate's decision with the rule that tripped it.

    ``material`` is the shape's material; ``machine`` supplies content and
    identifiers readable from machine state under the fact classes above and
    under ``gitignored`` ([{"path", "line"}] from the tree's gitignored
    files); ``rules`` adds literal ``phrases`` and regular-expression
    ``patterns``. Content-inclusion, any-of: a path mention by itself is not a
    content inclusion. Returns (sensitive, rule) where rule names the class or
    the project rule's index — never the matched value, which may itself be
    the secret.
    """
    if not isinstance(material, str) or not material:
        return False, ""
    machine = machine if isinstance(machine, dict) else {}
    for field, rule in _IDENTIFIER_CLASSES:
        if any(value in material
               for value in _string_values(machine.get(field))):
            return True, rule
    for entry in machine.get("gitignored") or []:
        if isinstance(entry, dict) and isinstance(entry.get("line"), str) \
                and entry["line"] in material:
            return True, f"gitignored content ({entry.get('path', '?')})"
    for rule, pattern in _CREDENTIAL_RULES:
        if pattern.search(material):
            return True, rule
    if isinstance(rules, dict):
        for index, value in enumerate(_string_values(rules.get("phrases")), 1):
            if value in material:
                return True, f"phrase #{index}"
        for index, source in enumerate(_string_values(rules.get("patterns")), 1):
            try:
                if re.search(source, material):
                    return True, f"pattern #{index}"
            except re.error:
                continue
    return False, ""


def secrets_gate(material: str, *, machine: dict | None = None,
                 rules: dict | None = None) -> bool:
    """Pure Secrets gate verdict: True when sensitive content is included.

    The boolean form of `secrets_verdict`; see it for the fact classes.
    """
    return secrets_verdict(material, machine=machine, rules=rules)[0]


def resolve_working_root(root: str | None = None, *, run=None) -> str:
    """The working folder whose rules and gitignored files the gate reads.

    The git root when the folder is inside a repository — a project's rules
    file belongs to the project — else the folder itself. A missing or failing
    git leaves the folder as given, never blocks the check.
    """
    base = os.path.abspath(root or os.getcwd())
    if run is None:
        run = _run_git(base)
    if run is None:
        return base
    try:
        top = str(run(["rev-parse", "--show-toplevel"]) or "").strip()
    except Exception:
        return base
    return os.path.abspath(top) if top else base


def secrets_check(material: str, *, root: str | None = None,
                  rules: dict | None = None, machine: dict | None = None,
                  gitignored: list | None = None,
                  outside_files=()) -> tuple[bool, str]:
    """The collect-demand verdict, assembled at the edge.

    Rules come from `modelbandit.secrets.json` at the working-folder root,
    machine facts are gathered here, and gitignored content is read from the
    tree — so the gate holds without the agent assembling anything. Each part
    is injectable, keeping the decision itself pure. Returns
    (sensitive, rule) as `secrets_verdict` does.
    """
    working_root = resolve_working_root(root)
    if rules is None:
        rules = load_secrets_rules(os.path.join(working_root, RULES_FILE))
    facts = dict(machine_facts() if machine is None else machine)
    facts["gitignored"] = (gitignored_facts(working_root)
                           if gitignored is None else list(gitignored))
    facts["outside_file_contents"] = (
        _string_values(facts.get("outside_file_contents"))
        + outside_file_contents(working_root, outside_files))
    return secrets_verdict(material, machine=facts, rules=rules)


# Exit contract v2 (ADR-0004): status says whether the tool ran; the output
# says what's true. 0 is any completed verdict (the printed lines say which),
# 2 belongs to argparse's usage errors, 4 means rules/config stopped the tool
# before it could form a verdict. 1 is CPython's generic operational failure
# and is never assigned here; the answer codes 1 (sensitive), 3 (not
# certified) and 5 (zone block) are retired, as is the over-budget run's
# borrowed 2 — answers live in the output, never in a nonzero status.
RULES_CONFIG_ERROR = 4


def emit_json(payload: dict) -> None:
    """One JSON object per `--json` invocation on stdout — stdlib json only."""
    print(json.dumps(payload, ensure_ascii=False))


def closed_regime_provenance(sources, zones: dict, *, environ=None,
                             run=None) -> Zone | None:
    """The first named source whose effective regime is closed.

    Provenance is the caller's own list of where the material came from
    (`--outside-file`), and it resolves the way a run resolves its working
    folder: the stricter of the source's folder and the repository it came
    from, so a source in a worktree carries the posture of the content it
    holds. The closed default applies just as a declared closed zone does, so
    undeclared provenance is blocked too.
    """
    for source in sources:
        folder = source if os.path.isdir(source) else os.path.dirname(source)
        zone = effective_zone(folder or os.curdir, zones=zones, run=run,
                              environ=environ)
        if zone.regime == "closed":
            return zone
    return None


def run_secrets_check(*, working_dir: str | None = None,
                      material: str | None = None,
                      outside_files=(), model: str | None = None,
                      policy_path: str | None = None,
                      sensitive: bool = False, as_json: bool = False) -> int:
    """Print the Secrets gate's verdict for one shape's material.

    Material is read from stdin; the zone the check judged by, the verdict,
    the rule that tripped and the rules file in force are printed. Every
    verdict exits 0 — safe, sensitive, not certified, or blocked by the
    free-use zone — and the printed lines say which (exit contract v2,
    ADR-0004); 4 is a rules/config error and 2 a usage error. A shape with
    no material given cannot be certified — silence is never read as safe.

    The zone answers ahead of the content verdict: material whose
    provenance has the effective closed regime, or a `--model` the
    effective zone's regime cannot admit. The zone is named; the material
    never is. With `as_json`, one JSON object replaces the lines (mode,
    ok, verdict, outcome, zone, reason, rule).
    """
    if material is None:
        try:
            material = sys.stdin.read()
        except Exception:
            material = ""
    root = resolve_working_root(working_dir)
    path_base = os.path.abspath(working_dir or os.getcwd())
    outside_paths = [path if os.path.isabs(path)
                     else os.path.join(path_base, path)
                     for path in outside_files]
    rules_path = os.path.join(root, RULES_FILE)
    try:
        rules = load_secrets_rules(rules_path)
        zones = load_zones()
    except SystemExit as exc:
        print(f"secrets gate: rules/config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR
    zone = effective_zone(path_base, zones=zones)
    if not as_json:
        print(f"zone: {zone_label(zone, sensitive=sensitive)}")
    blocked, reason = None, None
    if outside_paths:
        blocked = closed_regime_provenance(outside_paths, zones)
        if blocked is not None:
            reason = "material provenance from this zone"
    if reason is None and model:
        try:
            facts = policy_facts(policy_path)
        except SystemExit as exc:
            print(f"secrets gate: rules/config error ({exc.code})",
                  file=sys.stderr)
            return RULES_CONFIG_ERROR
        reason = zone_block(model, zone, policy=facts, sensitive=sensitive)
        blocked = zone
    if reason is not None:
        # A zone block is a verdict, not a failure: exit 0, the lines say
        # blocked (v2). The zone is named; the material never is.
        if as_json:
            emit_json({"mode": "check-secrets", "ok": True,
                       "outcome": "zone-blocked", "verdict": False,
                       "zone": zone_payload(blocked),
                       "reason": reason, "rule": None})
        else:
            print("secrets gate: blocked by the free-use zone")
            print(f"zone: {zone_label(blocked, sensitive=sensitive)}")
            print(f"reason: {reason}")
        return 0
    if not isinstance(material, str) or not material.strip():
        if as_json:
            emit_json({"mode": "check-secrets", "ok": True,
                       "outcome": "not-certified", "verdict": False,
                       "zone": zone_payload(zone),
                       "reason": "no material given", "rule": None})
        else:
            print("secrets gate: not certified (no material given)")
        return 0
    sensitive, rule = secrets_check(material, root=root, rules=rules,
                                    outside_files=outside_paths)
    if sensitive:
        if as_json:
            emit_json({"mode": "check-secrets", "ok": True,
                       "outcome": "sensitive", "verdict": False,
                       "zone": zone_payload(zone),
                       "reason": None, "rule": rule})
        else:
            print("secrets gate: sensitive")
            print(f"rule: {rule}")
    elif as_json:
        emit_json({"mode": "check-secrets", "ok": True,
                   "outcome": "safe", "verdict": True,
                   "zone": zone_payload(zone),
                   "reason": None, "rule": None})
    else:
        print("secrets gate: safe")
    if not as_json and os.path.exists(rules_path):
        print(f"rules: {rules_path}")
    return 0


def run_secrets_writer(*, working_dir: str | None = None,
                       payload: str | None = None) -> int:
    """Write or merge confirmed project rules and apply the gitignore choice."""
    if payload is None:
        try:
            payload = sys.stdin.read()
        except Exception as exc:
            raise SystemExit(f"cannot read --write-secrets input: {exc}") from None
    try:
        submitted = json.loads(payload)
    except (TypeError, ValueError):
        raise SystemExit("invalid JSON for --write-secrets") from None
    submitted = validate_secrets_rules(
        submitted, writer=True, source="--write-secrets input")
    incoming = {key: submitted[key] for key in RULES_KEYS}

    root = resolve_working_root(working_dir)
    rules_path = os.path.join(root, RULES_FILE)
    existing = load_secrets_rules(rules_path)
    if (submitted["identifying"] or not submitted["commit"]) \
            and _rules_file_is_tracked(root):
        raise SystemExit(f"{RULES_FILE} is already tracked; first run "
                         f"`git rm --cached {RULES_FILE}`, then rerun "
                         "--write-secrets")
    merged = {}
    added, present = {}, {}
    for key in RULES_KEYS:
        merged[key] = []
        seen = set()
        for value in existing.get(key, []):
            if value not in seen:
                seen.add(value)
                merged[key].append(value)
        added[key], present[key] = [], []
        added_seen, present_seen = set(), set()
        for value in incoming[key]:
            if value in seen:
                if value not in present_seen:
                    present[key].append(value)
                    present_seen.add(value)
                continue
            seen.add(value)
            merged[key].append(value)
            if value not in added_seen:
                added[key].append(value)
                added_seen.add(value)

    with open(rules_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    def counts(values):
        return ", ".join(
            f"{len(values[key])} {key[:-1] if len(values[key]) == 1 else key}"
            for key in RULES_KEYS)

    # Keep the summary at the level of kinds and counts, never rule values.
    print(f"added {counts(added)}; already present {counts(present)}")
    print(f"secrets rules: {rules_path}")

    ignore_path = os.path.join(root, ".gitignore")
    try:
        with open(ignore_path, encoding="utf-8") as f:
            ignored_lines = f.read().splitlines()
    except FileNotFoundError:
        ignored_lines = []
    already_ignored = any(line.strip() == RULES_FILE for line in ignored_lines)

    if submitted["identifying"] or not submitted["commit"]:
        if already_ignored:
            print(f"gitignore: already contains {RULES_FILE}")
        else:
            with open(ignore_path, "a+b") as f:
                f.seek(0, os.SEEK_END)
                if f.tell():
                    f.seek(-1, os.SEEK_END)
                    if f.read(1) not in (b"\n", b"\r"):
                        f.write(b"\n")
                f.write((RULES_FILE + "\n").encode("utf-8"))
            print(f"gitignore: appended {RULES_FILE} (identifying rules or commit=false)")
    elif already_ignored:
        # A later run does not re-assert the commit decision; say what is true.
        print(f"gitignore: already lists {RULES_FILE}; left unchanged")
    else:
        print(f"gitignore: unchanged; {RULES_FILE} is meant to be committed")
    return 0


def run_zones_writer(*, payload: str | None = None) -> int:
    """Validate the interview's zones proposal and write the machine's file.

    The contract mirrors `--write-secrets`'s invocation — JSON on stdin —
    but not its merge: zones are a whole-file posture, so the submitted
    config goes through `validate_zones` **before** anything is written.
    Invalid config refuses with status 4 naming the offending entry and
    writes nothing: a pre-existing `zones.json` is left byte-identical.
    A valid config replaces the file atomically (temp file in the same
    directory, then `os.replace`), so a reader never sees a half-written
    zones file, and the path written is printed for the user's review.
    """
    if payload is None:
        try:
            payload = sys.stdin.read()
        except Exception as exc:
            print(f"zones writer: rules/config error (cannot read "
                  f"--write-zones input: {exc})", file=sys.stderr)
            return RULES_CONFIG_ERROR
    try:
        submitted = json.loads(payload)
    except (TypeError, ValueError):
        print("zones writer: rules/config error "
              "(invalid JSON for --write-zones)", file=sys.stderr)
        return RULES_CONFIG_ERROR
    try:
        validated = validate_zones(submitted, source="--write-zones input")
    except SystemExit as exc:
        print(f"zones writer: rules/config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR

    path = zones_path()
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=directory,
                                         prefix=ZONES_FILE + ".",
                                         suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as f:
            json.dump(validated, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(temp_path, path)
    except BaseException:
        # Never leave a half-written temp beside (or instead of) the file.
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
    print(f"zones: {path}")
    return 0


# --- Free-use zones --------------------------------------------------------
# Where free models may run, machine-wide: a path declares the regime for
# everything under it, and anything undeclared is closed. The three regimes
# order open < sensitive < closed; a run takes the stricter of its working
# folder and the repository that folder came from, and a shape may tighten
# that but never loosen it.
ZONES_FILE = "zones.json"
ZONES_CONFIG_DIR = "modelbandit"
REGIMES = ("open", "sensitive", "closed")
DEFAULT_REGIME = "closed"
# A zone entry carries its path and its regime, nothing else: a field the tool
# silently ignored would be a rule the user believes in.
ZONE_KEYS = ("path", "free")
ZONES_KEYS = ("zones", "default")
_ENV_VAR = re.compile(r"\$\{(\w+)\}|\$(\w+)")


@dataclasses.dataclass(frozen=True)
class Zone:
    """The zone that decided a run: the declared path, or None undeclared.

    `resolved` carries the place the run was judged at when a link moved the
    judgement - the working folder or the declaration itself spells one place
    and reaches another. None when nothing moved, so every existing header
    keeps its shape.
    """
    path: str | None
    regime: str
    resolved: str | None = None

    def label(self) -> str:
        return "undeclared" if self.path is None else self.path


def zone_label(zone: Zone, *, sensitive: bool = False) -> str:
    """The run header's statement: `<path> (<regime>)`, or
    `undeclared (closed)` when no declared path matched. An open zone tightened
    by `--sensitive` names both the declared and effective posture. When a
    link moved the judgement, the header names the resolved place - with the
    declared path noted, or `undeclared` when no declaration matched - so a
    declaration cannot silently cover content it did not name.
    """
    if sensitive and zone.regime == "open":
        posture = "open; sensitive via --sensitive"
    else:
        posture = zone.regime
    if zone.resolved is None:
        return f"{zone.label()} ({posture})"
    declared = f"declared: {zone.path}" if zone.path else "undeclared"
    return f"{zone.resolved} ({posture}) ({declared})"


def zone_payload(zone: Zone) -> dict:
    """The `zone` object every `--json` verdict carries: the place the
    judgement landed (`path`), the regime, the declaration (null when no
    declaration matched) and the resolved place when a link moved it — the
    same facts the human `zone:` line spells."""
    return {"path": zone.resolved if zone.resolved else zone.path,
            "regime": zone.regime,
            "declared": zone.path,
            "resolved": zone.resolved}


def zones_path(*, environ=None) -> str:
    """`zones.json` under the machine's config root ($XDG_CONFIG_HOME or
    ~/.config), honouring the environment it is given."""
    env = os.environ if environ is None else environ
    base = (env.get("XDG_CONFIG_HOME")
            or os.path.join(expand_path("~", environ=env), ".config"))
    return os.path.join(base, ZONES_CONFIG_DIR, ZONES_FILE)


def zones_file_label(*, environ=None) -> str:
    """The zones file's path as the header spells it: `~` for the home it
    sits under, forward slashes after - the path to create reads the same
    on every machine, and names wherever the loader actually looks."""
    path = zones_path(environ=environ)
    home = expand_path("~", environ=environ)
    if os.path.normcase(path).startswith(os.path.normcase(home) + os.sep):
        path = "~" + path[len(home):]
    return path.replace(os.sep, "/")


def zones_absent_line(*, environ=None) -> str:
    """The one sentence every mode prints when no zones file exists —
    built once so the ranking header, the status report and the README
    example can never drift apart."""
    return (f"zones file: absent ({zones_file_label(environ=environ)}) "
            "— undeclared paths are closed")


# --- Local roster ----------------------------------------------------------
# The author-owned record of judgment about this machine's local models —
# the Capability band (domains handled, Difficulty ceiling, context-demand
# ceiling) and prose, keyed by the harness's own model id — and only that
# (GLOSSARY, Local roster). Existence, ids and serving facts belong to the
# harness; the roster never restates them. It lives beside zones.json:
# machine-global, uncommitted, hand-maintained (ADR-0009).
ROSTER_FILE = "local-roster.json"
ROSTER_VERSION = 1
# The file's two top-level sections: an unknown key is a config error the
# way the plan catalog's unknown entry keys are — read by nobody, believed
# by somebody.
ROSTER_KEYS = ("version", "entries")
# An entry's three fields: band + prose is the whole judgment (spec #66,
# "kept thin"), provenance is the exporter's optional stamp (ADR-0009).
# Anything else — a stray `context_length`, a serving fact — would be a
# catalog claim in a judgment file, refused loudly like the plan catalog's
# unknown keys.
ROSTER_ENTRY_KEYS = ("band", "prose", "provenance")
ROSTER_BAND_KEYS = ("domains", "difficulty", "context_demand")
# The domain names a band may state: the modelbandit domain vocabulary
# spelled out, so a typo stops the run instead of silently never matching
# a ticket (understating a band costs reach; a typo would cost it all
# without a word).
ROSTER_DOMAINS = ("research", "writing", "coding", "orchestration", "ops")


def roster_path(*, environ=None) -> str:
    """`local-roster.json` under the machine's config root — the same
    directory as zones.json ($XDG_CONFIG_HOME/modelbandit/, else
    ~/.config/modelbandit/), honouring the environment it is given."""
    env = os.environ if environ is None else environ
    base = (env.get("XDG_CONFIG_HOME")
            or os.path.join(expand_path("~", environ=env), ".config"))
    return os.path.join(base, ZONES_CONFIG_DIR, ROSTER_FILE)


def load_local_roster(*, path: str | None = None, environ=None) -> dict:
    """Validate the Local roster at the config boundary: its entries, or an
    empty roster when the file is absent.

    Loud in the style of `load_free_models`: an unknown key or a bad type
    stops the run naming the entry — never a silent default, because a band
    the reader guessed is a judgment nobody made. A missing file is absent
    setup (the harness listing, not the roster, says what exists). The keys
    are the harness's own model ids: a key outside the harness's local
    namespace is refused here, so a roster entry can never speak for a
    remote serving — judgment binds only the local row (ADR-0005).
    """
    roster = path if path is not None else roster_path(environ=environ)
    if not os.path.exists(roster):
        return {}
    try:
        with open(roster, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise SystemExit(
            f"cannot read local roster file {roster}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"local roster file {roster} must be a JSON object")
    for key in data:
        if key not in ROSTER_KEYS:
            raise SystemExit(
                f"local roster: unknown top-level key '{key}' "
                f"(expected {', '.join(ROSTER_KEYS)})")
    if not _is_plain_int(data.get("version")) \
            or data["version"] != ROSTER_VERSION:
        raise SystemExit(f"local roster: version must be {ROSTER_VERSION} "
                         f"(got {data.get('version')!r})")
    if "entries" not in data:
        raise SystemExit("local roster missing required key: entries")
    entries = data["entries"]
    if not isinstance(entries, dict):
        raise SystemExit("local roster entries must be an object")
    for mid in entries:
        if not isinstance(mid, str) or classify_route(mid) != "local":
            raise SystemExit(
                f"local roster entries.{mid}: key must be a harness model "
                f"id ({HARNESS_LOCAL_NAMESPACE}<model>), exactly as the "
                f"harness invokes it")
        entry = entries[mid]
        where = f"entries.{mid}"
        if not isinstance(entry, dict):
            raise SystemExit(f"local roster {where} must be an object")
        for key in entry:
            if key not in ROSTER_ENTRY_KEYS:
                raise SystemExit(
                    f"local roster {where}: unknown key '{key}' "
                    f"(expected {', '.join(ROSTER_ENTRY_KEYS)})")
        if "band" not in entry:
            raise SystemExit(f"local roster missing required key: "
                             f"{where}.band")
        band = entry["band"]
        if not isinstance(band, dict):
            raise SystemExit(f"local roster {where}.band must be an object")
        for key in band:
            if key not in ROSTER_BAND_KEYS:
                raise SystemExit(
                    f"local roster {where}.band: unknown key '{key}' "
                    f"(expected {', '.join(ROSTER_BAND_KEYS)})")
        for field in ROSTER_BAND_KEYS:
            if field not in band:
                raise SystemExit(
                    f"local roster missing required key: {where}.band.{field}")
        domains = band["domains"]
        if not isinstance(domains, list) \
                or not all(isinstance(name, str) for name in domains):
            raise SystemExit(f"local roster {where}.band.domains must be a "
                             f"list of domain names")
        for name in domains:
            if name not in ROSTER_DOMAINS:
                raise SystemExit(
                    f"local roster {where}.band.domains: unknown domain "
                    f"'{name}' (known: {', '.join(ROSTER_DOMAINS)})")
        difficulty = band["difficulty"]
        if difficulty not in INTENTS:
            raise SystemExit(
                f"local roster {where}.band.difficulty must be one of "
                f"{'|'.join(INTENTS)} (got {difficulty!r})")
        demand = band["context_demand"]
        if not _is_plain_int(demand) or demand <= 0:
            raise SystemExit(f"local roster {where}.band.context_demand "
                             f"must be a positive integer")
        if "prose" not in entry:
            raise SystemExit(
                f"local roster missing required key: {where}.prose")
        prose = entry["prose"]
        if not isinstance(prose, str) or not prose.strip():
            raise SystemExit(f"local roster {where}.prose must be a "
                             f"non-empty string")
        if "provenance" in entry and not isinstance(entry["provenance"],
                                                    dict):
            raise SystemExit(f"local roster {where}.provenance must be an "
                             f"object")
    return entries


def expand_path(text: str, *, environ=None) -> str:
    """`~` and environment variables, against the environment it is given."""
    env = os.environ if environ is None else environ
    if text == "~" or text.startswith(("~/", "~\\")):
        home = env.get("HOME") or env.get("USERPROFILE") or os.path.expanduser("~")
        text = home + text[1:]
    return _ENV_VAR.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)),
                        text)


def spelled_path(text: str, *, environ=None) -> str:
    """The path as spelled: `~` and variables expanded, absolute, and
    case-folded where the platform folds it — links left alone, so the
    spelling can be told apart from the place the path reaches."""
    return os.path.normcase(
        os.path.abspath(os.path.normpath(expand_path(text, environ=environ))))


def display_path(text: str, *, environ=None) -> str:
    """The place a path reaches: `~` and variables expanded, links resolved
    to the real filesystem place, the platform's own case kept. Strict
    resolution is off: a path that does not exist yet - a zone declared ahead
    of its folder - resolves to its written form and still compares.
    """
    return os.path.realpath(
        os.path.abspath(os.path.normpath(expand_path(text, environ=environ))),
        strict=False)


def compare_path(text: str, *, environ=None) -> str:
    """A path normalised for comparison on this platform: `~` and variables
    expanded, links resolved to the place the path reaches, absolute, and
    case-folded where the platform folds it. A zone is the place a path
    reaches, never the string it is spelled with."""
    return os.path.normcase(display_path(text, environ=environ))


def known_regime(value, *, where: str) -> str:
    """A regime the tool knows, or a loud stop naming where it came from."""
    if value not in REGIMES:
        raise SystemExit(f"{where}: unknown free-use regime {value!r}; "
                         f"known: {', '.join(REGIMES)}")
    return value


def validate_zones(payload, *, source: str = ZONES_FILE, environ=None) -> dict:
    """The zones file's contents, validated — additive against the default.

    Two entries naming the same normalised path stop loudly: the resolver
    would take the last one, and a later entry could silently reopen a path
    an earlier one closed — the one direction a fail-closed resolver must
    never take.
    """
    if not isinstance(payload, dict):
        raise SystemExit(f"{source} must be a JSON object with "
                         f"{' / '.join(ZONES_KEYS)}")
    unknown = sorted(set(payload) - set(ZONES_KEYS))
    if unknown:
        raise SystemExit(f"unknown key(s) in {source}: {', '.join(unknown)}; "
                         f"known: {', '.join(ZONES_KEYS)}")
    entries = payload.get("zones", [])
    if not isinstance(entries, list):
        raise SystemExit(f"zones in {source} must be a list of "
                         f"{{{' / '.join(ZONE_KEYS)}}} objects")
    zones = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(entries, 1):
        where = f"zone #{index} in {source}"
        if not isinstance(entry, dict):
            raise SystemExit(f"{where} must be an object with "
                             f"{' / '.join(ZONE_KEYS)}")
        extra = sorted(set(entry) - set(ZONE_KEYS))
        if extra:
            raise SystemExit(f"unknown key(s) in {where}: {', '.join(extra)}; "
                             f"known: {', '.join(ZONE_KEYS)}")
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            raise SystemExit(f"{where} needs a non-empty string path")
        normalised = compare_path(path, environ=environ)
        if normalised in seen:
            raise SystemExit(f"zone #{index} in {source} duplicates zone "
                             f"#{seen[normalised]} ({path})")
        seen[normalised] = index
        zones.append({"path": path,
                      "free": known_regime(entry.get("free"), where=where)})
    default = known_regime(payload.get("default", DEFAULT_REGIME),
                           where=f"default in {source}")
    return {"zones": zones, "default": default}


def load_zones(path: str | None = None, *, environ=None) -> dict:
    """The machine's zones, validated. A missing file means the default
    everywhere — nothing declared, nothing open."""
    path = zones_path(environ=environ) if path is None else path
    if not os.path.exists(path):
        return {"zones": [], "default": DEFAULT_REGIME}
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"cannot read zones file {path}: {exc}") from None
    return validate_zones(payload, source=path, environ=environ)


def stricter(left: str, right: str) -> str:
    """The stricter of two regimes: open < sensitive < closed."""
    both = (known_regime(left, where="regime"), known_regime(right, where="regime"))
    return max(both, key=REGIMES.index)


def regime_at_least(regime: str, floor: str) -> bool:
    """Whether `regime` is at least as strict as `floor`.

    The dimension a gate asks about: a gate that excludes under `sensitive`
    excludes under `closed` too, because a stricter regime dominates every
    milder one — `closed` implies `sensitive`, never the other way round.
    """
    return (REGIMES.index(known_regime(regime, where="regime"))
            >= REGIMES.index(known_regime(floor, where="floor")))


def _covers(zone_path: str, folder: str) -> bool:
    """Whether a normalised zone path covers a normalised folder path."""
    return (folder == zone_path
            or folder.startswith(zone_path.rstrip(os.sep) + os.sep))


def resolve_zone(folder: str, zones: dict, *, environ=None) -> Zone:
    """The zone governing `folder`: the longest declared path that covers it,
    else the file's default. A declared path may name the folder exactly.

    Both sides compare the place the path reaches - links resolved - so a
    junction or symlink is judged by the content it leads to. When a link
    moved the judgement, the zone carries the resolved place for the header:
    the declaration itself spells one place and reaches another, or the
    working folder does while the place it reaches is not the declared path.
    """
    target = compare_path(folder, environ=environ)
    spelled = spelled_path(folder, environ=environ)
    best = None
    for entry in zones.get("zones", []):
        declared = compare_path(entry["path"], environ=environ)
        if _covers(declared, target) and (best is None
                                          or len(declared) >= len(best[0])):
            best = (declared, entry)
    if best is None:
        if spelled == target:
            return Zone(path=None, regime=zones.get("default", DEFAULT_REGIME))
        return Zone(path=None, regime=zones.get("default", DEFAULT_REGIME),
                    resolved=display_path(folder, environ=environ))
    entry = best[1]
    declared_spelled = spelled_path(entry["path"], environ=environ)
    declared_moved = declared_spelled != best[0]
    place = display_path(folder, environ=environ)
    if declared_moved or (spelled != target
                          and os.path.normcase(place) != declared_spelled):
        return Zone(path=entry["path"], regime=entry["free"], resolved=place)
    return Zone(path=entry["path"], regime=entry["free"])


def _under_modules(common: str) -> bool:
    """Whether a git common dir is a submodule's, under a `.git/modules`
    directory — a path belonging to neither the submodule nor the
    superproject."""
    parts = common.split(os.sep)
    return any(parts[i] == ".git" and parts[i + 1] == "modules"
               for i in range(len(parts) - 1))


def _module_origin(common: str, root: str, run) -> str | None:
    """The submodule working tree a `.git/modules` git dir serves.

    `core.worktree` in the module's config names its working tree, relative
    to the git dir — the same answer whether git is asked from the module's
    own checkout or from a linked worktree of it. Without that setting,
    `--show-toplevel` answers for the checkout itself; nothing answerable
    means no origin, never the bogus `.git/modules` path.
    """
    try:
        worktree = str(run(["config", "core.worktree"]) or "").strip()
    except Exception:
        worktree = ""
    if worktree:
        return os.path.normpath(os.path.join(common, worktree))
    try:
        top = str(run(["rev-parse", "--show-toplevel"]) or "").strip()
    except Exception:
        return None
    if not top:
        return None
    return os.path.normpath(top if os.path.isabs(top)
                            else os.path.join(root, top))


def git_origin(root: str, *, run=None) -> str | None:
    """The repository a folder belongs to, from its shared `.git` directory.

    `git rev-parse --git-common-dir` reports the main worktree's `.git` for a
    linked worktree, so a ticket worktree resolves to the repository it came
    from rather than to where it happens to live. A submodule's git dir lives
    under the superproject's `.git/modules/<name>`, which belongs to neither
    repository, so there the origin is the submodule's own working tree — the
    repository whose content the folder holds. Git missing, failing or
    reporting nothing usable answers None — a run then carries only its
    working folder's zone.
    """
    run = _run_git(root) if run is None else run
    if run is None:
        return None
    try:
        common = run(["rev-parse", "--git-common-dir"])
    except Exception:
        return None
    common = str(common or "").strip()
    if not common:
        return None
    if not os.path.isabs(common):
        common = os.path.join(root, common)
    common = os.path.normpath(common)
    if _under_modules(common):
        return _module_origin(common, root, run)
    origin = os.path.dirname(common)
    if not origin or not os.path.dirname(origin):
        return None
    return origin


def effective_zone(folder: str | None = None, *, zones: dict | None = None,
                   run=None, environ=None) -> Zone:
    """The regime a run works under: the stricter of the working folder's zone
    and its origin repository's, so a worktree carries the posture of the
    content it holds. The zone that decided it answers for it."""
    folder = folder or os.getcwd()
    zones = load_zones(environ=environ) if zones is None else zones
    here = resolve_zone(folder, zones, environ=environ)
    origin = git_origin(folder, run=run)
    if origin is None or compare_path(origin, environ=environ) \
            == compare_path(folder, environ=environ):
        return here
    there = resolve_zone(origin, zones, environ=environ)
    return there if REGIMES.index(there.regime) > REGIMES.index(here.regime) \
        else here


def shape_regime(zone: Zone, *, sensitive: bool) -> str:
    """The regime a shape works under: the zone's, tightened by --sensitive.

    A flag may only tighten: `--sensitive` in a closed zone leaves it closed.
    """
    return stricter(zone.regime, "sensitive" if sensitive else "open")


def load_policy_file(path: str | None) -> dict:
    """The policy read once, as UTF-8 JSON, by every entry point.

    The ranking run, the policy check, the pre-flight and the secrets check
    all decode this file the same way: explicitly UTF-8, never the console's
    locale codec — prose carrying non-ASCII must read the same everywhere.
    A missing file is an empty policy (the ranking path then reports the
    required keys it misses); a file that cannot be decoded or parsed is a
    policy/config error naming the file, never a mangled read and never an
    uncaught traceback.
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            policy = json.load(f)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"cannot read policy file {path}: {exc}") from None
    if not isinstance(policy, dict):
        raise SystemExit(f"policy file {path} must be a JSON object")
    return policy


def policy_facts(path: str | None) -> dict:
    """The policy's Exposure facts when the file exists, else none.

    The pre-flight and the secrets check read the local policy for its
    `exposure` overrides, its `free_models` catalog and its `plans` catalog
    when it is there, and work without it: a missing file is not an error,
    so the defaults answer (a ':free' or 'opencode/*' route exposed, a
    paid route no-retention). No board, no classification fetch, no network.
    """
    policy = load_policy_file(path)
    policy["free_models"] = load_free_models(policy)
    policy["plans"] = load_plans(policy)
    load_exposure_overrides(policy)
    return policy


def zone_block(model_id: str, zone: Zone, *, policy: dict | None = None,
               sensitive: bool = False, loopback: bool = True) -> str | None:
    """The effective zone's reason this model may not serve here, or None.

    The whole pre-flight rule: the shape's regime is the zone's, tightened by
    `--sensitive` and never loosened, and the candidate facts are the policy's
    Exposure facts plus the serving endpoint's loopback status (an empty
    policy and an undeclared endpoint keep the safe defaults). Blocked
    means a prohibition the regime states outright — a remote free route in a
    closed zone, an exposed route at a sensitive regime or stricter — never a
    Footprint, catalog or quota exclusion.

    The candidate is judged by its serving identity alone: localness is a
    serving fact, never a catalogue claim, and this guard observes no serving
    — so a policy label cannot make a remote id (`opencode/*`, `:free`) local
    here, and a remote Free route is refused in a closed zone whatever the
    catalog says. The harness's `lmstudio/*` namespace classifies local, but
    `local` still resolves only for a loopback endpoint: the pre-flight
    reads the harness's declared endpoint (a file read, still no serving
    observed) and a non-loopback serving fails closed as exposed.
    """
    shape = Shape(sensitive=sensitive,
                  regime=shape_regime(zone, sensitive=sensitive))
    model_id = norm_id(model_id)
    policy = policy or {}
    return regime_prohibition(shape, candidate_for(model_id, policy,
                                                   loopback=loopback))


# The pre-flight's default-deny verdict: an id outside every Route kind names
# no serving, so no zone, Exposure or policy label can speak for it.
UNKNOWN_SERVING_NAMESPACE = "unknown serving namespace"


def _print_preflight_posture(zone: Zone, *, plain: bool,
                             restated: bool) -> None:
    """The effective zone, then the shape the pre-flight judges the id as."""
    print(f"zone: {zone_label(zone, sensitive=restated)}")
    if plain:
        print("shape: plain (via --plain)")
    elif restated:
        print("shape: sensitive (via --sensitive)")
    else:
        print("shape: sensitive (assumed)")


def run_assert_allowed(*, model: str, working_dir: str | None = None,
                       policy_path: str | None = None,
                       plain: bool = False, restated: bool = False,
                       as_json: bool = False) -> int:
    """Pre-flight: may this model serve in this folder's zone?

    The dispatch contract fails closed: an unstated shape is **Sensitive**,
    and the output states the assumption (`shape: sensitive (assumed)`) — a
    route that retains training data is refused by default, never allowed
    because nobody said otherwise. A caller that knows the material is not
    Sensitive must say so explicitly (`--plain`, printed as
    `shape: plain (via --plain)`); `--sensitive` restates the default and is
    accepted with the same verdict.

    Prints the effective posture (`zone: <path> (<regime>)`) and either the
    model as allowed (`allowed: <id>`) or a free-use zone block — both
    verdicts exit 0 and the lines say which (exit contract v2, ADR-0004:
    launch only on `allowed`; the status says the tool ran). An id outside
    every Route kind is refused first and on its own terms
    (`blocked: unknown serving namespace`, the model named): kind is decided
    from the id alone, so an unclassifiable id is blocked in an open zone
    exactly as in a closed one, and no policy prefix map grants it one. The
    zone is named; the shape's content never is. No policy file,
    classification fetch or network is needed, so an orchestrator can refuse
    to launch a model the plan should not have produced before anything is
    fetched. With `as_json`, one JSON object replaces the lines (mode, ok,
    allowed, model, shape, zone, reason).
    """
    try:
        zone = effective_zone(working_dir)
        facts = policy_facts(policy_path)
    except SystemExit as exc:
        print(f"pre-flight: policy/config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR
    model_id = norm_id(model)
    if classify_route(model_id) is None:
        # Route kind is decided from the id alone, before the zone regime: an
        # id outside every kind has no serving fact, so the pre-flight refuses
        # it in an open zone exactly as in a closed one. The block is a
        # verdict, not a failure (ADR-0004): the lines carry it, the status
        # only says the tool ran.
        if as_json:
            emit_json({"mode": "assert-allowed", "ok": True,
                       "allowed": False,
                       "model": model_id,
                       "shape": "plain" if plain else "sensitive",
                       "zone": zone_payload(zone),
                       "reason": UNKNOWN_SERVING_NAMESPACE})
            return 0
        _print_preflight_posture(zone, plain=plain, restated=restated)
        print(f"blocked: {UNKNOWN_SERVING_NAMESPACE}")
        print(f"model: {model_id}")
        return 0
    reason = zone_block(model_id, zone, policy=facts, sensitive=not plain,
                        loopback=loopback_endpoint(harness_serving_endpoint()))
    if as_json:
        emit_json({"mode": "assert-allowed", "ok": True,
                   "allowed": reason is None,
                   "model": model_id,
                   "shape": "plain" if plain else "sensitive",
                   "zone": zone_payload(zone),
                   "reason": reason})
        return 0
    _print_preflight_posture(zone, plain=plain, restated=restated)
    if reason is not None:
        # A block is a verdict, not a failure: exit 0, the lines say blocked.
        print("blocked by the free-use zone")
        print(f"model: {model_id}")
        print(f"reason: {reason}")
        return 0
    print(f"allowed: {model_id}")
    return 0


def load_policy_bundle(policy_path: str | None) -> dict:
    """The one policy load every entry point shares: the file read as
    UTF-8, the free catalog, the plan catalog, and the exposure overrides.
    Validation and unpacking stay with each caller — it knows what it can
    tolerate (a missing file is absent setup for the status report, an
    existing one must be one the ranking trusts) and maps every failure to
    status 4, never a traceback or a Secrets verdict."""
    policy = load_policy_file(policy_path)
    policy["free_models"] = load_free_models(policy)
    policy["plans"] = load_plans(policy)
    load_exposure_overrides(policy)
    return policy


def run_status(*, working_dir: str | None = None,
               policy_path: str | None = None,
               sensitive: bool = False, as_json: bool = False) -> int:
    """The offline setup report: zone, zones file, secrets file, policy age.

    The machine-readable companion to the README Setup section — read-only
    and fully offline: no endpoint fetch, no classification, no quota, and
    the secrets file's presence only, never its contents. `--working-dir`
    judges the folder the way the pre-flight does, and the zones path is
    spelled the way the run header spells it.

    Exit status: 0 whenever the setup files are absent — a missing zones or
    secrets file is the documented default, not an answer the status must
    carry; 4 only when a file that exists fails validation (zones or
    policy), named on stderr. With `as_json`, one JSON object replaces the
    lines (mode, ok, zone, zones_file, secrets_file, policy).
    """
    policy_path = policy_path or DEFAULT_POLICY
    try:
        zone = effective_zone(working_dir)
        zones_present = os.path.exists(zones_path())
        # A missing file is absent setup (age `unknown`), not a failure;
        # only an existing policy must be one the ranking would trust.
        policy_exists = os.path.exists(policy_path)
        policy = load_policy_bundle(policy_path)
        if policy_exists:
            load_policy_config(policy)
    except SystemExit as exc:
        print(f"status: config error ({exc.code})", file=sys.stderr)
        return RULES_CONFIG_ERROR
    label = zones_file_label()
    root = resolve_working_root(working_dir)
    secrets_path = os.path.join(root, RULES_FILE)
    secrets_present = os.path.exists(secrets_path)
    age = policy_age_days(policy_path)
    if as_json:
        emit_json({"mode": "status", "ok": True,
                   "zone": zone_payload(zone),
                   "zones_file": {"path": label, "present": zones_present},
                   "secrets_file": {"path": secrets_path,
                                    "present": secrets_present},
                   "policy": {"path": policy_path, "age_days": age}})
        return 0
    print(f"zone: {zone_label(zone, sensitive=sensitive)}")
    if zones_present:
        print(f"zones file: present ({label})")
    else:
        # Absent is the documented default (exit 0), never silence: the
        # same line the ranking header prints (issue #38), plus the one
        # action that changes it — create the file, via the skill's setup
        # interview.
        print(zones_absent_line())
        print(f"next: create {label} — see the skill's setup interview")
    if secrets_present:
        # Presence only: the report never reads, parses or prints contents.
        print(f"secrets file: present ({secrets_path})")
    else:
        print(f"secrets file: absent ({secrets_path}) — "
              f"built-in default rules apply")
    age_txt = f"{age}d old" if age is not None else "unknown"
    print(f"policy: {policy_path} — {age_txt}")
    return 0


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
    free_share_inheritance: float = DEFAULT_FREE_SHARE_INHERITANCE
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
    inheritance = scoring.get("free_share_inheritance",
                              DEFAULT_FREE_SHARE_INHERITANCE)
    try:
        inheritance = float(inheritance)
    except (TypeError, ValueError, OverflowError):
        raise SystemExit(
            "policy scoring.free_share_inheritance must be a number") from None
    if not math.isfinite(inheritance) or not 0.0 < inheritance <= 1.0:
        raise SystemExit("policy scoring.free_share_inheritance must be "
                         "greater than 0 and at most 1")
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
        free_share_inheritance=inheritance,
        free_quota_reserve=quota_reserve,
    )


def exposure_contradiction(mid: str, value: str) -> str | None:
    """Why a policy Exposure label contradicts the serving identity, or None.

    Localness is a serving fact, never a catalogue claim: the classifier
    answers the remote serving namespaces remote — the void rule
    (local_label_is_void) says so whatever a policy entry says — so a
    `local` label on one is a contradiction the policy stops loudly,
    naming the entry.
    """
    if value == "local" and local_label_is_void(mid):
        return (f"exposure 'local' contradicts the remote serving identity "
                f"'{mid}' (opencode/*, opencode-go/*, and :free routes are "
                f"remote)")
    return None


def _free_catalog_kind(prefix: str, exposure: str) -> str | None:
    """The Route kind a ``free_models`` entry declares, from its prefix alone.

    Namespace first: ``opencode-go/*`` is a plan serving whatever the entry
    says (plan has its own catalog), ``opencode/*`` is a harness serving, and
    ``lmstudio/*`` is the harness's local serving — a malformed local
    namespace fails closed through the classifier. The ``local`` annotation
    supplies the local serving fact for a prefix no remote namespace claims.
    A bare two-segment OpenRouter prefix is the family the catalog keys a
    ``:free`` route by, so it declares a free-slug serving. A ``:free``
    suffix on any other shape routes through the seam,
    which normalizes and classifies the whole prefix: a two-segment slug
    stays a free-slug serving, while a third segment or a plan namespace
    under the ``openrouter/`` qualifier is refused at load. Anything else
    falls to the classifier, which fails closed on an unknown namespace and
    names the market serving an ``openrouter/`` prefix hides.
    """
    if prefix.startswith("opencode-go/"):
        return "plan"
    if prefix.startswith(HARNESS_LOCAL_NAMESPACE):
        # The harness's local namespace is a serving fact of its own —
        # whatever the entry annotates, an `lmstudio/*` prefix declares a
        # local serving, and a malformed one fails closed through the seam.
        return classify_route(prefix)
    if exposure == "local":
        return "local"
    if prefix.startswith("opencode/"):
        return "harness"
    if prefix.endswith(":free"):
        return classify_route(prefix)
    parts = prefix.split("/")
    if len(parts) == 2 and all(parts):
        return "free-slug"
    return classify_route(prefix)


def load_free_models(policy: dict) -> dict:
    """Validate the curated Free route catalog at the policy boundary.

    A bad window or misspelled Exposure must stop the run: either could make a
    candidate look safer or more capable than the policy says. So must an entry
    whose Route kind is not Free: the hardcoded $0 of a Free record must never
    price a plan or market serving, so such an entry is refused at load with a
    loud config error naming it — nothing half-loaded (ADR-0002, ADR-0005).
    ``summary_ref`` remains optional in policy, but when present it must be a
    usable string.
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
        if (contradiction := exposure_contradiction(prefix,
                                                    entry["exposure"])):
            raise SystemExit(f"policy {path}.exposure: {contradiction}")
        kind = _free_catalog_kind(prefix, entry["exposure"])
        if kind not in FREE_KINDS:
            raise SystemExit(
                f"policy {path}: route kind '{kind or 'unknown'}' is not a "
                f"Free route (free-slug, harness, or local); the free "
                f"catalog prices only Free servings")
        summary_ref = entry.get("summary_ref")
        if summary_ref is not None and (not isinstance(summary_ref, str)
                                        or not summary_ref.strip()):
            raise SystemExit(f"policy {path}.summary_ref must be a non-empty string")
    return catalog


# The three Allowance windows a plan entry must state caps for, in ledger
# order: the rolling 5-hour window, the week, the month (GLOSSARY,
# Allowance). The caps are dollar figures, so every one must be a positive
# real number — a zero or a misspelling would let a batch run past the
# plan's boundary unnoticed.
PLAN_CAP_WINDOWS = ("five_hour", "weekly", "monthly")

# The only fields a plans entry may state. An unknown key is a config error:
# a stray `caps` window would silently invent an unauthorized boundary (the
# crossing arithmetic iterates caps.items()), and a non-numeric one would
# surface as a TypeError instead of status 4.
PLAN_ENTRY_FIELDS = ("list_price", "caps", "exposure", "regions",
                     "family_ref")


def _is_finite_number(value) -> bool:
    """A real JSON number: an int or a float, never a bool, never NaN/inf."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def load_plans(policy: dict) -> dict:
    """Validate the plan catalog at the policy boundary.

    The `plans` section is the single source the ledger and the Exposure
    verdicts read a Plan route's facts from: its list price (the Draw's
    basis), its three Allowance window caps, its training/retention class,
    and an optional region opt-in. Each field could make a plan look safer
    or its Allowance look bigger than the policy says, so each refuses the
    load loudly, naming the entry — nothing half-loaded (ADR-0003,
    ADR-0005). An unknown key is refused the same way: `caps` must state
    exactly the three Allowance windows, because a stray window would
    silently invent an unauthorized boundary in the crossing arithmetic,
    and an entry may state only the known plan facts.

    The section is its own catalog: an entry whose id the Route-kind seam
    does not answer `plan` is refused here, while `free_models` keeps
    refusing plan-kind entries in parallel — each catalog prices only the
    servings it owns. A `list_price` of 0 is not bad: it is the zero-Draw,
    free-in-plan serving whose pricing falls back to the pool-cheapest
    basis (ADR-0006), so the price must be non-negative, not positive.

    Every entry also declares its family link: `family_ref`, the Twin's
    Metered serving id. Twins find each other through that declaration
    alone -- vendor prefixes differ per family, so no id shape derives one
    (the declaration is authoritative, never a slug heuristic). The link
    resolves when the Route-kind seam answers `market` for it -- a plan,
    harness, `:free` or unclassifiable id names no Metered row and is
    refused here, naming the entry, so a broken link never half-loads a
    catalog and never reaches resolution as a silent default.
    """
    catalog = policy.get("plans", {})
    if not isinstance(catalog, dict):
        raise SystemExit("policy plans must be an object")
    for mid, entry in catalog.items():
        path = f"plans.{mid}"
        if not isinstance(mid, str) or not mid.strip():
            raise SystemExit(f"policy {path}: id must be a non-empty string")
        if not isinstance(entry, dict):
            raise SystemExit(f"policy {path} must be an object")
        for key in entry:
            if key not in PLAN_ENTRY_FIELDS:
                raise SystemExit(
                    f"policy {path}: unknown key '{key}' (expected "
                    f"{', '.join(PLAN_ENTRY_FIELDS)})")
        kind = classify_route(mid)
        if kind != "plan":
            raise SystemExit(
                f"policy {path}: route kind '{kind or 'unknown'}' is not a "
                f"Plan route (opencode-go/*); the plans catalog prices only "
                f"Plan servings")
        if "list_price" not in entry:
            raise SystemExit(f"policy missing required key: {path}.list_price")
        if not _is_finite_number(entry["list_price"]) \
                or entry["list_price"] < 0:
            raise SystemExit(
                f"policy {path}.list_price must be a non-negative number")
        if "caps" not in entry:
            raise SystemExit(f"policy missing required key: {path}.caps")
        caps = entry["caps"]
        if not isinstance(caps, dict):
            raise SystemExit(f"policy {path}.caps must be an object")
        for window in PLAN_CAP_WINDOWS:
            if window not in caps:
                raise SystemExit(
                    f"policy missing required key: {path}.caps.{window}")
            if not _is_finite_number(caps[window]) or caps[window] <= 0:
                raise SystemExit(
                    f"policy {path}.caps.{window} must be a positive number")
        for window in caps:
            if window not in PLAN_CAP_WINDOWS:
                raise SystemExit(
                    f"policy {path}.caps: unknown window '{window}' "
                    f"(expected {', '.join(PLAN_CAP_WINDOWS)})")
        if "exposure" not in entry:
            raise SystemExit(f"policy missing required key: {path}.exposure")
        try:
            known_exposure(mid, entry["exposure"])
        except SystemExit as exc:
            raise SystemExit(f"policy {path}.exposure: {exc}") from None
        if (contradiction := exposure_contradiction(mid, entry["exposure"])):
            raise SystemExit(f"policy {path}.exposure: {contradiction}")
        regions = entry.get("regions")
        if regions is not None and (
                not isinstance(regions, list)
                or any(not isinstance(region, str) or not region.strip()
                       for region in regions)):
            raise SystemExit(
                f"policy {path}.regions must be a list of non-empty strings")
        if "family_ref" not in entry:
            raise SystemExit(
                f"policy missing required key: {path}.family_ref")
        family_ref = entry["family_ref"]
        if not isinstance(family_ref, str) or not family_ref.strip():
            raise SystemExit(
                f"policy {path}.family_ref must be a non-empty string")
        twin_kind = classify_route(family_ref)
        if twin_kind != "market":
            raise SystemExit(
                f"policy {path}.family_ref '{family_ref}': route kind "
                f"'{twin_kind or 'unknown'}' is not a Metered route "
                f"(market); the family link names the Twin's Metered serving")
    return catalog


def load_exposure_overrides(policy: dict) -> dict:
    """Validate the policy's `exposure` override map at the policy boundary.

    A misspelled class here would widen the gate exactly as a misspelled
    catalog entry would, so it stops the run the same way — loudly, naming
    the prefix, before any candidate is judged by it.
    """
    overrides = policy.get("exposure", {})
    if not isinstance(overrides, dict):
        raise SystemExit("policy exposure must be an object")
    for prefix, value in overrides.items():
        path = f"exposure.{prefix}"
        if not isinstance(prefix, str) or not prefix.strip():
            raise SystemExit(f"policy {path}: id-prefix must be a non-empty string")
        if not isinstance(value, str):
            raise SystemExit(f"policy {path}: exposure must be a string")
        try:
            known_exposure(prefix, value)
        except SystemExit as exc:
            raise SystemExit(f"policy {path}: {exc}") from None
        if contradiction := exposure_contradiction(prefix, value):
            raise SystemExit(f"policy {path}: {contradiction}")
    return overrides


def _free_summary(entry: dict, summaries: dict, mid: str | None = None) -> bool:
    """Whether a Free route has a resolvable explicit or prefix summary."""
    ref = entry.get("summary_ref")
    return ((isinstance(ref, str) and bool(summaries.get(ref)))
            or (mid is not None and bool(hint_for(mid, summaries))))


def _family_share(share: dict, entry: dict, inheritance: float) -> float:
    """A curated Free route's standing: a discount on its family's domain share.

    An ``opencode/*`` or local serving has no leaderboard row of its own; its
    popularity is the family's revealed preference. It inherits only
    ``inheritance`` of that share: the free serving is a limited-time,
    rate-limited surrogate for the family, so it does not carry the family's
    full standing. The family prefix is the summary reference with any trailing
    ``:free`` stripped, so a dated ``X-YYYYMMDD:free`` board row still counts
    toward it. No summary reference means no observable popularity — the
    standing stays zero.
    """
    ref = entry.get("summary_ref")
    if not isinstance(ref, str) or not ref.strip():
        return 0.0
    prefix = ref.removesuffix(":free")
    family = sum(s for key, s in share.items() if key.startswith(prefix))
    return family * inheritance


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
                          summaries: dict, *,
                          inheritance: float = DEFAULT_FREE_SHARE_INHERITANCE
                          ) -> tuple[dict, dict]:
    """Merge cataloged OpenCode models and ranked :free routes into candidates.

    OpenRouter :free rows retain their own slug even when the API only resolves
    them through a paid family model. Uncataloged or unsummarized ranked routes
    stay visible but the catalog gate prevents the Deal from using them.
    OpenCode catalog entries are added with a discounted share of their family's
    domain share (the family's revealed preference standing in for a route with
    no board row); their context and Exposure remain curated facts, not inferred
    runtime data.
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
        if classify_route(prefix) == "local":
            # A local-kind prefix never stands up its own row here: local
            # candidates exist only where the harness listing says they do
            # (merge_local_candidates), so a catalog entry alone raises none.
            continue
        if (not is_free_route(prefix)
                or not _free_summary(entry, summaries, prefix)):
            continue
        merged_share.setdefault(prefix, 0.0)
        if merged_share[prefix] == 0.0:
            merged_share[prefix] = _family_share(merged_share, entry,
                                                 inheritance)
        merged_models.setdefault(prefix, _free_model_record(prefix, entry))

    return merged_share, merged_models


def merge_local_candidates(share: dict, models: dict, listed, served: dict,
                           free_models: dict, *,
                           inheritance: float = DEFAULT_FREE_SHARE_INHERITANCE
                           ) -> tuple[dict, dict]:
    """Join this run's harness-listed local ids to the curated Free catalog.

    The harness listing is the sole source of existence and identity: an id
    the harness does not list never joins, whatever the probe reports or the
    catalog declares, and what joins is named exactly as the harness
    dispatches it. Each listed id still needs a catalog entry whose Exposure
    is ``local`` to be judged at all; cataloged listed ids remain visible
    even without a summary, but the admission seam requires that summary
    before they can be picked or dealt. The probe's contribution here is one
    narrow fact — the live context window judged by the Context gate — never
    existence: a missing server changes nothing about the candidate set.
    """
    merged_share = dict(share)
    merged_models = {mid: dict(model) for mid, model in models.items()}
    for mid in sorted(listed):
        match = longest_prefix_match(mid, free_models)
        if match is None:
            continue
        entry = match[1]
        if not isinstance(entry, dict) or entry.get("exposure") != "local":
            continue
        merged_share.setdefault(mid, 0.0)
        if merged_share[mid] == 0.0:
            merged_share[mid] = _family_share(merged_share, entry, inheritance)
        record = _free_model_record(mid, entry, served.get(mid))
        live = served.get(mid)
        if isinstance(live, dict) and live.get("context_length") is not None \
                and _is_plain_int(live["context_length"]) \
                and live["context_length"] > 0:
            # The curated window stays the record's policy fact; the window
            # the live serving reports is the capacity the Context gate is
            # judged against, for this invocation only.
            record["served_context_length"] = live["context_length"]
        merged_models[mid] = record
    return merged_share, merged_models


def local_candidate_ids(listed, free_models: dict) -> set[str]:
    """Harness-listed ids matched by a catalog entry whose Exposure is
    ``local`` — the serving fact set the run's local flags read from."""
    return {mid for mid in listed
            if (match := longest_prefix_match(mid, free_models)) is not None
            and isinstance(match[1], dict)
            and match[1].get("exposure") == "local"}


def _plan_model_record(mid: str) -> dict:
    """The minimal record a plan serving carries into the table and the gates.

    A plan serving never resolves in OpenRouter's models list, so the plans
    catalog supplies what the run consumes: the id and the $0 cash price one
    ticket costs within its Allowance. The plan's list price is a Draw basis
    (the cost seam's fact), never a per-1M market price, so no per-1M figure
    is stated here -- the table shows the unknowable columns as `?`/`—`.
    """
    return {"id": mid,
            "pricing": {"prompt": "0", "completion": "0",
                        "input_cache_read": "0"}}


def _family_board_share(share: dict, family: str, local: set[str]) -> float:
    """The family's board share: the largest figure the board reports for its
    full-quality servings.

    Twin rows report one family's traffic, so their sum would count it twice;
    the largest is the closest the board gets to the family's whole. A family
    the board does not name has no share.
    """
    return max((s for mid, s in share.items()
                if mid not in local and family_key(mid) == family
                and classify_route(mid) in _FULL_QUALITY_KINDS), default=0.0)


def merge_plan_candidates(share: dict, models: dict, plans: dict, *,
                          local=()) -> tuple[dict, dict]:
    """Join the validated plans catalog's servings to the candidate set.

    The plan namespace is not an OpenRouter serving, so a plan id never
    resolves in the models list; the catalog is its one surface. Each
    cataloged plan serving joins with the minimal record the table and the
    gates honestly consume (see _plan_model_record) -- no market models-list
    row is invented.

    Popularity is the family's: a family served twice -- its metered twin and
    its plan serving -- divides its board share across both full-quality
    rows, so the family's standing is counted once. A family with one
    full-quality serving keeps its share whole: the plan row is the family
    model at full quality, never a rate-limited surrogate, so no Free-route
    inheritance discount applies. The local serving fact outranks the plan
    shape: an id this machine serves joins as a local row
    (merge_local_candidates), never here.
    """
    merged_share = dict(share)
    merged_models = {mid: dict(model) for mid, model in models.items()}
    local = set(local)
    plan_ids = [mid for mid in plans
                if is_plan_route(mid) and mid not in local]
    if not plan_ids:
        return merged_share, merged_models
    for mid in plan_ids:
        merged_share.setdefault(mid, 0.0)
        merged_models.setdefault(mid, _plan_model_record(mid))
    families = sorted({family for family in map(family_key, plan_ids)
                       if family is not None})
    for family in families:
        rows = [mid for mid in merged_share
                if mid not in local and family_key(mid) == family
                and classify_route(mid) in _FULL_QUALITY_KINDS]
        if not rows:
            continue
        family_share = _family_board_share(merged_share, family, local)
        for mid in rows:
            merged_share[mid] = family_share / len(rows)
    return merged_share, merged_models


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
    """'mid=score,mid=score' -> {prefix: clamped 0-5 float}.

    A malformed entry raises ValueError naming it; the caller reports it as
    the usage error it is (status 2), before anything is fetched."""
    out = {}
    for part in spec.split(","):
        mid, eq, val = part.strip().partition("=")
        if mid and eq:
            try:
                score = float(val)
            except ValueError:
                raise ValueError(
                    f"--fit entry '{mid}={val}' is not a number on 0-5") \
                    from None
            if not math.isfinite(score):
                raise ValueError(
                    f"--fit entry '{mid}={val}' is not a number on 0-5")
            out[mid] = max(0.0, min(5.0, score))
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
    material, bound per invocation, never a mood declared mid-run. `regime` is
    the free-use zone the run works under (see shape_regime), `open` unless a
    zone or the flag says otherwise. `domain` and `intent` are the ticket
    facts the Local roster's band judges against: which domain the run works
    (None when nothing judges one) and which effort rung it asks for.
    """
    sensitive: bool = False
    input_tokens: int | None = None
    context_headroom: float = 2.0
    context_margin: float = 0.5
    output_tokens: int | None = None
    regime: str = "open"
    domain: str | None = None
    intent: str = "measured"


@dataclasses.dataclass(frozen=True)
class Candidate:
    """The candidate facts admission judges: Exposure, serving, Footprint
    and — for a rostered local row — its Capability band."""
    id: str
    exposure: str
    is_free: bool = False
    context_length: int | None = None
    cataloged: bool = True
    completion_cap: int | None = None
    output_multiplier: float = 1.0
    local: bool = False
    band: dict | None = None


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
    def declared(value) -> str | None:
        # The override map may name `local` itself: the operator's explicit
        # statement about a serving, the escape hatch for a non-loopback one.
        if value == "local" and local_label_is_void(mid):
            return None
        return known_exposure(mid, value)

    def stated(value) -> str | None:
        # Every other source earns `local` only from the serving being
        # loopback on this machine.
        if value == "local" and not loopback:
            return None
        return declared(value)

    match = longest_prefix_match(mid, overrides or {})
    if match is not None and (value := declared(match[1])) is not None:
        return value
    if local and loopback:
        return "local"
    for catalog in (free_models or {}, plans or {}):
        match = longest_prefix_match(mid, catalog)
        entry = match[1] if match is not None else {}
        if isinstance(entry, dict) and entry.get("exposure") \
                and (value := stated(entry["exposure"])) is not None:
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
    plan_match = longest_prefix_match(mid, policy.get("plans", {}))
    is_free = is_free_route(mid, local=local)
    facets = facets_for(mid, local=local)
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
    # The catalog-entry facet: a harness or local serving is admitted only
    # through its own catalog entry; a free-slug serving may ride a family
    # summary without one; a plan serving needs its plans entry. Each
    # catalog prices only the servings it owns (its load rule refuses every
    # other kind), so the plan catalog satisfies the plan kind alone and the
    # free catalog the Free kinds alone.
    needs_catalog_entry = (facets["needs_policy_catalog_entry"]
                           if facets else True)
    is_plan = is_plan_route(mid, local=local)
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
                      cataloged=((not needs_catalog_entry
                                  or (is_free
                                      and catalog_match is not None)
                                  or (is_plan and plan_match is not None))
                                 and (not is_free
                                      or _free_summary(catalog_entry,
                                                       policy.get("summaries",
                                                                  {}), mid))))


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


def share_line(label: str, tickets: int, dealt: int) -> str:
    """The deal's share readout: `<label>: N/M tickets (P%)`, a zero
    denominator reading 0% rather than dividing by nothing."""
    share = tickets / dealt if dealt else 0.0
    return f"{label}: {tickets}/{dealt} tickets ({share:.0%})"


@dataclasses.dataclass(frozen=True)
class Decision:
    """An admission verdict: admitted, or excluded with a visible reason.

    An excluded candidate is never hidden — the ranked table marks it and the
    deal does not draw it.
    """
    admitted: bool
    reason: str = ""


ADMITTED = Decision(True)


def exposed_prohibition(shape: Shape, candidate: Candidate) -> str | None:
    """The Exposure clause: why an exposed candidate may not serve, or None.

    Exposed — `trains` — candidates never serve a Sensitive shape, whether
    free or paid; no-retention and local candidates stay — Exposure, not
    price, decides. A `sensitive` zone is the flag by another name, and a
    `closed` zone is at least that strict (see regime_at_least), so it refuses
    the same exposed routes on top of every remote free one.
    """
    if candidate.exposure != "trains":
        return None
    if not (shape.sensitive or regime_at_least(shape.regime, "sensitive")):
        return None
    return f"exposed ({candidate.exposure})"


def exposure_gate(shape: Shape, candidate: Candidate) -> Decision:
    """The Exposure<->Sensitive gate; see `exposed_prohibition`."""
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
    """Only curated, summary-backed Free routes and plans-cataloged Plan
    routes can enter the Deal.

    The catalog-entry facet decides: a Free route needs its free catalog
    entry (and its family summary where the entry rides one), and a Plan
    route needs its plans entry — the one surface its list price, caps and
    training/retention fact come from. A plan row the plans section does not
    catalog stays visible and refused with this reason.
    """
    if candidate.is_free and not candidate.cataloged:
        return Decision(False, "free route requires a catalog entry and "
                        "summary where applicable (summary resolution is required)")
    if (is_plan_route(candidate.id, local=candidate.local)
            and not candidate.cataloged):
        return Decision(False, "plan route requires a plans catalog entry "
                               "(the plans section does not price this id)")
    return ADMITTED


def zone_prohibition(shape: Shape, candidate: Candidate) -> str | None:
    """Why the free-use zone forbids this candidate outright, or None.

    The zone-refusable facet answers: a closed regime refuses exactly the
    remote, unaccountable servings - the free-slug and harness kinds -
    whatever their price, while a market or plan serving is accountable and
    a model this machine serves never leaves it and stays in. `open` and
    `sensitive` forbid nothing here - Exposure and the quota answer for
    them.

    This is the source filter: a candidate it names never enters the candidate
    set, so it is not ranked, scored, dealt or listed. The header states the
    zone that made it absent (`zone: <path> (<regime>)`), which is how the
    absence is explained without a row and without a reason column.
    """
    facets = facets_for_candidate(candidate)
    if (facets and facets["zone_refusable_in_closed_regimes"]
            and regime_at_least(shape.regime, "closed")):
        return "remote free route is prohibited by the effective regime"
    return None


def filter_zone_candidates(share: dict, models: dict, policy: dict, *,
                           local_ids, regime: str, intent: str) -> dict:
    """Drop routes prohibited by this free-use regime before ranking or scoring."""
    zone_shape = Shape(regime=regime)
    return {mid: value for mid, value in share.items()
            if zone_prohibition(zone_shape, candidate_for(
                mid, policy, local=mid in local_ids, model=models.get(mid),
                intent=intent)) is None}


def zone_gate(shape: Shape, candidate: Candidate) -> Decision:
    """The zone clause behind the one decision; see `zone_prohibition`.

    Admission refuses too, though the source filter should never let such a
    candidate reach it: one verdict, whichever path asks.
    """
    reason = zone_prohibition(shape, candidate)
    return Decision(reason is None, reason or "")


def regime_prohibition(shape: Shape, candidate: Candidate) -> str | None:
    """What the shape's regime forbids outright, or None.

    The pre-flight's yardstick, and the only two clauses a zone states: no
    remote free route in a closed zone, no exposed route at a regime at least
    as strict as `sensitive`. Everything else — Footprint, quota, an
    uncataloged Free route — is a shape-level exclusion the table marks, so it
    is not a zone block.
    """
    return zone_prohibition(shape, candidate) \
        or exposed_prohibition(shape, candidate)


# The gates, in order, behind the one decision. The zone comes first: a route a
# closed zone forbids outright does not need its Exposure, band or Footprint
# judged, and the first failing gate is the reason the table shows. The band
# sits beside them: judgment about the rostered local row, after the regime
# and Exposure facts, before the mechanical capacity checks.
GATES = (zone_gate, exposure_gate, band_gate, context_gate, catalog_gate)


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
              ledger: AllowanceLedger | None = None) -> list[dict]:
    """Multi-ticket deal over the eligible pool: seeded, preference-tilted.

    Eligibility is popularity (eligibility_pool). The draw blends the task
    baseline and preference:

        draw = (1 - blend_weight) * task_score + blend_weight * pref
        (each normalized)

    where every pool member's base is its fit-adjusted task score, supplied
    for the whole pool by the caller (blend_bases). Deterministic in seed.
    The pool is admission-filtered before the draw (parameters.admitted), so
    the deal and the ranked table agree about what may serve the shape.
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
    prefs = [weight_for(mid, aff) for mid, _ in pool]
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
            continue
        for step in range(len(cum)):
            j = (start + step) % len(cum)
            if evicted[j]:
                continue
            if twins[j] >= 0:
                k = twins[j]
                counts[k] += 1
                ledger.charge(pool[k][0])
                break
            mid = pool[j][0]
            if ledger.crosses(mid):
                k = _twin_index(mid, pool, catalog, local=local)
                if k is not None and k != j:
                    twins[j] = k
                    counts[k] += 1
                    ledger.charge(pool[k][0])
                    break
                evicted[j] = True
                continue
            counts[j] += 1
            ledger.charge(mid)
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
                    policy: dict, local_ids=(), regime: str = "open",
                    intent: str = "measured"):
    """Per-domain share boards (free candidates merged, zone-filtered — the
    same source the check and a ranking run judge), their top-cut ranked mids
    and the union of ranked mids. The shared input for the check's drift
    derivation, the --scope facts and the --anchors scope."""
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
            regime=regime, intent=intent)
        share_by_domain[name] = share
        ranked_by_domain[name] = [mid for mid, _ in
                                  sorted(share.items(), key=lambda kv: -kv[1])[:top]]
        all_ranked.update(ranked_by_domain[name])
    return share_by_domain, ranked_by_domain, all_ranked


def drift_keys(all_ranked: set, summaries: dict, signals: dict,
               free_models: dict | None = None):
    """The check's gap/stale derivation, shared by the scope report and the
    anchors scope: ranked mids without a summary; summary and signal keys
    with no current rank among the top-cut mids.

    A cataloged Free route's ``summary_ref`` is how its family summary
    reaches it everywhere else in this file — the catalog gate
    (``_free_summary``) and the table's summary column
    (``summary_for_candidate``) both resolve it — and an ``opencode/*`` or
    local id can never prefix-match the family key. So the ref counts here
    too: a gap is a summary the route does not have, not one spelled in
    another namespace. Symmetrically, a summary key a ranked route
    references is not stale — it is still serving. An unresolvable ref
    silences neither side."""
    free_models = free_models or {}

    def catalog_ref(mid: str) -> str | None:
        """The resolvable family summary a ranked cataloged route stands on,
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
                 zone: Zone, regime: str) -> list[str]:
    """The anchor model set: explicit ids when given (deduplicated, in given
    order), else the check's drift set — gaps, then stale summaries, then
    stale signals, via the shared drift_keys helper over the same
    free-merged, zone-filtered boards the check judges.

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
    _, _, all_ranked = domain_rankings(
        classif, domains, models, by_canon, top, config, policy,
        local_ids=(), regime=regime, intent="measured")
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
                config: PolicyConfig, zone: Zone, regime: str) -> None:
    """First-party benchmark anchors for the scope: one unfiltered,
    authenticated, cached fetch of the combined feed; one table per source
    in that source's own schema, rows in scope order; a trailing line naming
    scoped models the feed does not cover. Facts only — nothing persists."""
    scope = anchor_scope(explicit, models, by_canon, classif, domains,
                         policy, top, config, zone, regime)
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
                     intent: str, basis: str, config: PolicyConfig,
                     local_ids=(), regime: str = "open",
                     zone: Zone | None = None,
                     sensitive: bool = False,
                     ranks=None, local_listing=None,
                     roster=None) -> None:
    zone = zone if zone is not None else Zone(path=None, regime=regime)
    summaries = policy.get("summaries", {})
    signals = {k: v for k, v in policy.get("hints", {}).items()
               if isinstance(v, dict) and v.get("fit")}
    pool_k = config.deal.eligibility_top_k
    # The same source filter as a ranking run: a route the zone forbids is
    # not a candidate here either, so the diagnostic deal plays only what may
    # serve and no Free-share signal is claimed for routes that cannot draw.
    share_by_domain, ranked_by_domain, all_ranked = domain_rankings(
        classif, domains, models, by_canon, top, config, policy,
        local_ids=local_ids, regime=regime, intent=intent)
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
    # data and cannot mutate policy or eligibility.
    free_share_zeros = []
    for name in domains:
        profile_name = DOMAIN_PROFILE.get(name, "agentic")
        in_tok, out_tok, cached = PROFILES[profile_name]
        shape = Shape(sensitive=False, input_tokens=in_tok,
                      context_headroom=config.context.headroom,
                      context_margin=config.context.margin,
                      regime=regime, domain=name, intent=intent)
        aff = domain_weights(signals, name, config.factors)
        admitted = frozenset(
            mid for mid in share_by_domain[name]
            if admit(shape, candidate_for(
                mid, policy, local=mid in local_ids,
                model=models.get(mid), roster=roster)).admitted)
        pool = eligibility_pool(share_by_domain[name], models, aff, pool_k,
                                admitted, local=local_ids)
        free = free_route_ids((mid for mid, _ in pool), policy,
                              local=local_ids)
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
            DealParameters(blend_weight=config.deal.blend_weight,
                           top_k=pool_k, seed=FREE_SHARE_CHECK_SEED,
                           tickets=FREE_SHARE_CHECK_TICKETS,
                           fit_adjusted_task_scores=scores,
                           admitted=admitted), local=local_ids)
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
    print(f"zone: {zone_label(zone, sensitive=sensitive)}")
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
        free = free_route_ids(share_by_domain[name], policy, local=local_ids)
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
            free=free_route_ids(costs, policy, local=local_ids),
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
    ap = argparse.ArgumentParser(prog="modelbandit",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--domain", help="domain from policy.json (see --list-domains)")
    ap.add_argument("--list-domains", action="store_true",
                    help="show domains and their leaderboard tags")
    ap.add_argument("--check-secrets", action="store_true",
                    help="Secrets gate check: reads the shape's material from "
                         "stdin and prints the verdict and rule; repeat "
                         "--outside-file PATH for named outside content. "
                         "Exit 0 for every verdict — safe, sensitive, not "
                         "certified, or blocked by the free-use zone — the "
                         "printed lines say which; 4 rules/config error, "
                         "2 usage errors. --json answers with one object.")
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
                         "`blocked by the free-use zone`, so launch only on "
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
                    help="the model a --assert-allowed or --check-secrets run "
                         "will use (checked against the effective zone)")
    ap.add_argument("--write-secrets", action="store_true",
                    help="write or merge confirmed Secrets gate rules from "
                         "JSON on stdin; apply the commit/gitignore decision")
    ap.add_argument("--write-zones", action="store_true",
                    help="write the machine's zones file from JSON on stdin "
                         "(the Set up the free-use zones interview's "
                         "proposal): validated before anything is written — "
                         "an invalid config refuses with status 4 naming the "
                         "entry and writes nothing; a valid one is written "
                         "atomically and the path written is printed")
    ap.add_argument("--working-dir", default=None, metavar="PATH",
                    help="working folder (default: cwd). Secrets gate "
                         "commands read modelbandit.secrets.json and "
                         ".gitignore from its git root; every run reads its "
                         "free-use zone from the machine's zones file")
    ap.add_argument("--check-policy", action="store_true",
                    help="report summary drift (ranked models without summaries, "
                         "stale summaries) and policy age; no --domain needed")
    ap.add_argument("--status", action="store_true",
                    help="offline setup report for this folder "
                         "(--working-dir): the effective zone, the zones "
                         "file, the secrets file (presence only, never "
                         "contents) and the policy age. No fetch, no "
                         "classification, no quota. Exit 0 even when setup "
                         "files are absent (the documented default); 4 only "
                         "when an existing zones or policy file fails "
                         "validation. --json answers with one object.")
    ap.add_argument("--json", action="store_true",
                    help="answer with one JSON object on stdout instead of "
                         "the human lines: --check-secrets, --assert-allowed, "
                         "--status, and a budgeted ranking run (--domain with "
                         "--budget); a usage error anywhere else. `ok` is "
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
    ap.add_argument("--tickets", type=int, default=1, help="runs to project for")
    ap.add_argument("--deal", action="store_true",
                    help="deal tickets across the eligible pool by seeded draw "
                         "from the preference-blended distribution")
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
                         "exposed candidates — trains — are excluded from the "
                         "pick and the deal, and marked with a reason in the "
                         "table; no-retention free and local routes stay in")
    ap.add_argument("--budget", type=float, help="run budget in USD")
    ap.add_argument("--top", type=int, default=8, help="ranking rows to show")
    ap.add_argument("--policy", default=DEFAULT_POLICY,
                    help="policy file: domains + baseline (default: beside script)")
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

    # --json answers the verdict modes only; the ranking table is never
    # JSON-ized (issue #41), so anywhere else the flag would be silently
    # ignored — it stops as the usage error it is.
    if args.json:
        domain_served = bool(args.domain) and args.budget is not None
        served = (int(args.check_secrets) + int(args.assert_allowed)
                  + int(args.status) + int(domain_served))
        riders = (args.write_secrets or args.write_zones or args.list_domains
                  or args.check_policy or args.scope
                  or args.anchors is not None
                  or (args.domain and not domain_served))
        if served != 1 or riders:
            ap.error("--json is read only by --check-secrets, --assert-allowed, "
                     "--status and a budgeted ranking run (--domain with "
                     "--budget), each on its own")

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
                                           model=args.model,
                                           policy_path=args.policy,
                                           sensitive=args.sensitive,
                                           as_json=args.json))
    if args.write_secrets:
        raise SystemExit(run_secrets_writer(working_dir=args.working_dir))
    if args.write_zones:
        # The machine's zones file: the interview's proposal on stdin,
        # validated before anything is written — status 4 with the offending
        # entry named writes nothing, a valid config replaces the file
        # atomically. Needs no policy and no network.
        raise SystemExit(run_zones_writer())
    if args.model:
        ap.error("--model is read only by --assert-allowed and --check-secrets")
    if args.status:
        # The setup report reads the folder and the machine's files, never
        # the network: absent setup files are the documented default (exit
        # 0), and only a file that exists and fails validation stops the
        # report (exit 4).
        raise SystemExit(run_status(working_dir=args.working_dir,
                                    policy_path=args.policy,
                                    sensitive=args.sensitive,
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
    # folder and the repository it came from, then tightened by --sensitive.
    zone = effective_zone(args.working_dir)
    regime = shape_regime(zone, sensitive=args.sensitive)

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
                    args.top, args.refresh, config, zone, regime)
        return
    # The local universe arrives from the harness — passed in with
    # --local-listing — and the serving endpoint from the harness's config:
    # one fact each, no discovery channel of our own (the probe below stays
    # two narrow facts about already-listed candidates: is it serving, at
    # what window). `loopback` is the condition `local` Exposure resolves
    # under, and `listed` is empty whenever the harness never spoke.
    serving_endpoint = harness_serving_endpoint()
    loopback = loopback_endpoint(serving_endpoint)
    local_listing = parse_local_listing(args.local_listing)
    listed = sorted(local_listing) if local_listing is not None else []
    served_local = probe_local_models(url=models_url(serving_endpoint))
    local_ids = local_candidate_ids(listed, policy["free_models"])
    if args.check_policy or args.scope:
        # The scope path needs the daily token rankings for window totals; the
        # bare check never consults them and stays one fetch lighter.
        ranks = (fetch_json(RANK_URL, "rankings.json", auth=True,
                            refresh=args.refresh)
                 if args.scope else None)
        share, models = merge_free_candidates(
            {}, models, policy["free_models"], policy.get("summaries", {}),
            inheritance=config.free_share_inheritance)
        # Check-policy sees this invocation's same local candidates as a domain
        # run, but still performs no persistent policy update.
        _, models = merge_local_candidates(
            share, models, listed, served_local, policy["free_models"],
            inheritance=config.free_share_inheritance)
        run_check_policy(models, by_canon, classif, domains, policy,
                         args.top, args.policy,
                         args.effort, args.pricing_basis,
                         config, local_ids=local_ids, regime=regime, zone=zone,
                         sensitive=args.sensitive, ranks=ranks,
                         local_listing=local_listing, roster=roster)
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
    shape = Shape(sensitive=args.sensitive, input_tokens=in_tok,
                  output_tokens=out_tok,
                  context_headroom=config.context.headroom,
                  context_margin=config.context.margin,
                  regime=regime,
                  domain=args.domain, intent=args.effort)
    # Zone prohibitions filter at source: a candidate the zone forbids outright
    # never enters the candidate set — not ranked, not scored, not dealt, not
    # listed, and its endpoints never priced. The header states the zone that
    # made it absent. Shape-level exclusions (Exposure, Footprint, quota,
    # catalog) still mark, never hide.
    share = filter_zone_candidates(
        share, models, policy, local_ids=local_ids,
        regime=regime, intent=args.effort)
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
    print(f"zone: {zone_label(zone, sensitive=args.sensitive)}")
    if not os.path.exists(zones_path()):
        # Absent has always been silent in every mode: the loader returns
        # the closed default without a word, so a fresh install never
        # learns setup is missing. One line, only when the file is truly
        # absent - a present file stays byte-identical, and a corrupt one
        # already stopped loudly when the zone was resolved above
        # (issue #38).
        print(zones_absent_line())
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
        # Same yardstick as filter_zone_candidates: a closed effective
        # regime has already dropped every remote Free route at source, so
        # the pool clause says so instead of claiming they stayed (issue
        # #38). Where free routes genuinely remain - open or sensitive -
        # the line is unchanged, as are the quota figures above.
        pool = (":free routes excluded by the closed zone"
                if regime_at_least(regime, "closed")
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
    decisions = {mid: admit(shape, candidate_for(
        mid, policy, local=mid in local_ids, model=models.get(mid),
        endpoints=endpoint_cache.get(mid, ()), intent=args.effort,
        loopback=loopback, roster=roster),
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
                             admitted, local=local_ids, plans=policy["plans"])
            if args.deal else [])
    # The run's allowance ledger: prospective and in-run, so it starts empty
    # and nothing leaves this process. The pick asks it (one task) and the
    # deal draws it down (the whole batch).
    ledger = AllowanceLedger(policy["plans"], local=local_ids)

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
        ctx = f"{context_length / 1024:.0f}K" if context_length else "?"
        if free_details or is_free_route(mid, local=mid in local_ids) or plan_row:
            # The column shows the exposure admission judged: resolved
            # through the same precedence, loopback fact included — a
            # cataloged `local` the endpoint cannot back reads as the
            # exposed fallback it was refused as.
            exposure = resolve_exposure(mid, free_models=policy["free_models"],
                                        overrides=policy.get("exposure", {}),
                                        local=mid in local_ids,
                                        plans=policy["plans"],
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
        print(f"| {i} | {mid} | {s:.2%} | {sc:.2f} |{fit_cell} "
              f"{tokens_30d.get(mid, 0) / 1e9:.0f}B | {out_cell} | ${per:.4f} | "
              f"{delta} | {ctx} | {exposure} | {rung} |{admit_cell}")
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
        ctx = f"{context_length / 1024:.0f}K" if context_length else "?"
        exposure = (resolve_exposure(mid, free_models=policy["free_models"],
                                     overrides=policy.get("exposure", {}),
                                     local=mid in local_ids,
                                     plans=policy["plans"],
                                     loopback=loopback)
                    if free_details or is_free_route(mid, local=mid in local_ids)
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
        # A completed run that found nothing to pick: the answer (why there
        # is no pick) goes to stderr on its own line — byte-identical to the
        # v1 message — and the status stays 0 (exit contract v2, ADR-0004).
        # A --json run answers with the object instead: one object per
        # invocation, every verdict included (issue #41, Build 2).
        if excluded:
            stop_reason = ("shape: no candidate admitted — every ranked "
                           f"candidate is excluded ({', '.join(excluded)}); drop "
                           "the restrictive shape setting or pick another domain")
            stop_verdict = "no-candidate-admitted"
        else:
            stop_reason = "domain has no ranked candidates in the model list"
            stop_verdict = "no-ranked-candidates"
        if args.json:
            emit_json({"mode": "budget", "ok": True,
                       "verdict": stop_verdict, "reason": stop_reason,
                       "rule": None, "zone": zone_payload(zone)})
        else:
            print(stop_reason, file=sys.stderr)
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
        rows = plan_deal(share, models, aff, parameters=deal_parameters,
                         local=local_ids, plans=policy["plans"],
                         ledger=ledger)
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
            out_mid = qualified_id(row["mid"], local=row["mid"] in local_ids)
            print(f"| {i} | {out_mid} | {row['share']:.2%} | "
                  f"{row['base']:.2f} | "
                  f"{row['pref']:.1f} | {row['draw']:.2%} | {row['tickets']} | "
                  f"${per:.4f} | ${per * row['tickets']:.4f} |")
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
            # JSON-ized — issue #41).
            emit_json({"mode": "budget", "ok": True,
                       "over_budget": over_budget,
                       "budget": args.budget,
                       "projection": {"tickets": args.tickets,
                                      "total": total,
                                      "floor": floor_total,
                                      "baseline": (base_per * args.tickets
                                                   if base_per else None)},
                       "zone": zone_payload(zone)})
        else:
            verdict = "under" if not over_budget else "OVER"
            print(f"budget: ${args.budget:.2f} -> {verdict}")
        if over_budget:
            # Over budget is a verdict, not a failure: exit 0 with the OVER
            # line (v2 retires the borrowed usage status; ADR-0004).
            sys.exit(0)


if __name__ == "__main__":
    main()
