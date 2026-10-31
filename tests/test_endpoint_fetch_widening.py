"""Endpoint spread prices market servings only; non-market rows fetch nothing.

The one deliberate widening of the route-kind consolidation (issue #53): the
endpoint-fetch skip was harness-and-local only, so a ranked `:free` row still
fetched the endpoints catalog redundantly - its price comes from its zero
record either way. The facet contract's `priced_by_endpoint_spread` names the
market kind as the only kind Endpoint spread prices, so free-slug rows stop
fetching too. The output is byte-identical: only the fetch counts change.

Fixture style follows test_cli.py: a plain-dict world, an injected fetch
recorder, no network.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


def make_model(mid, prompt, completion, cache_read, context=None):
    m = {"id": mid, "supported_parameters": ["reasoning_effort"],
         "pricing": {"prompt": prompt, "completion": completion,
                     "input_cache_read": cache_read}}
    if context:
        m["context_length"] = context
    return m


POLICY = {
    "baseline": {"id": "xiaomi/mimo-v2.6-pro"},
    "summaries": {"family/flash": "flash family summary"},
    "domains": {"writing": ["content_writing"]},
    "scoring": {"alpha": 1.0, "beta": 0.0,
                "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                               "top2_max": 0.75}},
    "affinity": {
        "blend_weight": 0.6,
        "eligibility_top_k": 5,
        "factors": {"favor_validated": 3.0, "favor_suspected": 2.0,
                    "avoid_validated": 0.3, "avoid_suspected": 0.5},
    },
    "free_models": {
        "opencode/flash-free": {"context_length": 262_144,
                                "exposure": "no-retention",
                                "summary_ref": "family/flash"},
    },
}

MARKET = "deepseek/deepseek-v4-pro-0813"
FREE = "vendor/model:free"
HARNESS = "opencode/flash-free"


def build_world():
    return {
        "models": [make_model(MARKET, "0.00000066", "0.00000198",
                              "0.000000066"),
                   make_model(FREE, "0", "0", "0")],
        "classifications": {"as_of": "2026-10-17", "classifications": [
            {"tag": "content_writing", "usage_share": 0.1, "models": [
                {"id": MARKET, "tag_usage_share": 0.5},
                {"id": FREE, "tag_usage_share": 0.5},
            ]},
        ]},
        "rankings": {"data": []},
        "endpoints": {MARKET: [
            {"name": "Baidu", "pricing": {"prompt": "0.00000013",
                                          "completion": "0.0000004",
                                          "input_cache_read": "0"}},
        ]},
        "benchmarks": {"meta": {"as_of": "2026-10-26T00:01:10.159Z",
                                "source": None, "citation": None,
                                "model_count": 1},
                       "data": []},
    }


class EndpointFetchWideningTests(unittest.TestCase):
    """A ranking run fetches endpoint pricings for market-kind rows only."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        with open(self.policy_path, "w") as f:
            json.dump(POLICY, f)
        config_home = os.path.join(self._tmp.name, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": [], "default": "open"}, f)
        self.config_home = config_home

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *argv):
        world = build_world()
        calls = []

        def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
            calls.append(url)
            if cache_name == "key.json":
                raise SystemExit("cannot reach the key endpoint")
            if cache_name == "models.json":
                return {"data": world["models"]}
            if cache_name == "classifications.json":
                return {"data": world["classifications"]}
            if cache_name == "rankings.json":
                return world["rankings"]
            if cache_name == "benchmarks.json":
                return world["benchmarks"]
            if url.endswith("/endpoints"):
                slug = url[len(modelbandit.MODELS_URL) + 1:-len("/endpoints")]
                return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
            raise AssertionError(f"unexpected fetch: {url}")

        out, err = io.StringIO(), io.StringIO()
        argv = ["modelbandit", "--policy", self.policy_path, *argv]
        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch), \
                mock.patch("modelbandit.probe_local_models", return_value={}), \
                mock.patch.object(modelbandit, "CACHE_DIR",
                                  os.path.join(self._tmp.name, "cache")), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME":
                                             self.config_home}), \
                mock.patch("modelbandit.git_origin", return_value=None), \
                mock.patch.object(sys, "argv", argv), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                self.assertIsNone(exc.code, err.getvalue())
        return out.getvalue(), calls

    def endpoint_fetches(self, calls, mid):
        return [url for url in calls
                if url.endswith(f"/{mid}/endpoints")]

    def test_a_free_slug_row_makes_no_endpoint_fetch(self):
        # The widening: a ranked ':free' row prices from its zero record, so
        # the endpoints catalog fetch for it was redundant. It stops.
        out, calls = self.run_cli("--domain", "writing")
        self.assertEqual(self.endpoint_fetches(calls, FREE), [], out)

    def test_a_harness_row_makes_no_endpoint_fetch(self):
        # Unchanged by the widening: the harness kind never fetched either.
        out, calls = self.run_cli("--domain", "writing")
        self.assertEqual(self.endpoint_fetches(calls, HARNESS), [], out)

    def test_a_market_row_still_fetches_endpoint_pricings(self):
        # The trait stays the market kind's: its row still prices from the
        # per-endpoint spread.
        out, calls = self.run_cli("--domain", "writing")
        self.assertTrue(self.endpoint_fetches(calls, MARKET), out)

    def test_the_free_row_prices_from_its_zero_record(self):
        # Byte-identical output: the free row's price cells are what its zero
        # record yields, with no endpoint data behind them.
        out, _ = self.run_cli("--domain", "writing")
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{FREE} |" in ln)
        # The spread separator is the table's own dash (U+2013), as pinned by
        # the golden CLI output in test_cli.py.
        self.assertIn("0.00\u20130.00 (no endpoint data)", row)
        self.assertIn("$0.0000", row)


if __name__ == "__main__":
    unittest.main()
