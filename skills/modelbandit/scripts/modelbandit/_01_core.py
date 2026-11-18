# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
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

# The skill's own policy.json: where it sits depends on how the script is
# deployed. The shipped layout is skill/scripts/modelbandit.py (policy two
# levels up), a flat copy is skill/modelbandit.py (policy beside the script),
# and either spelling may be reached through a link — so every spelling is
# offered and the first one that exists wins. When none exists the canonical
# two-up path is kept: that is the path --status and the status-4 messages
# name when the policy really is missing.
def _default_policy(script: str) -> str:
    """The first existing candidate for the policy `script` travels with."""
    bases = tuple(dict.fromkeys(
        (os.path.abspath(script), os.path.realpath(script))))
    candidates = [os.path.join(os.path.dirname(os.path.dirname(base)),
                               "policy.json") for base in bases]
    candidates += [os.path.join(os.path.dirname(base), "policy.json")
                   for base in bases]
    return next((path for path in candidates if os.path.exists(path)),
                candidates[0])


# The CLI entry is the launcher beside this package; the policy travels
# with it. `__file__` here is the package's own __init__, one level deeper
# than the launcher, so the launcher's path is reconstructed - two levels
# up from the launcher is the skill folder in the shipped layout, the flat
# copy keeps the launcher beside policy.json, and a link resolves through
# realpath inside _default_policy.
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "modelbandit.py")
DEFAULT_POLICY = _default_policy(_SCRIPT)


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


