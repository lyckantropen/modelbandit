"""CLI-level tests for main(): ranking, pricing bases, output, and exit codes.

Hand-computed expectations use the authoring profile (in=20,000 out=12,000
cached=40%, effort multiplier 1.0 at `measured`) unless stated.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


def make_model(mid, prompt, completion, cache_read, canonical=None,
               params=("reasoning_effort",), created=None, context=None):
    m = {"id": mid, "supported_parameters": list(params),
         "pricing": {"prompt": prompt, "completion": completion,
                     "input_cache_read": cache_read}}
    if canonical:
        m["canonical_slug"] = canonical
    if created:
        m["created"] = created
    if context:
        m["context_length"] = context
    return m


def build_world():
    # Hand-computed $/ticket at the authoring profile (mult 1.0):
    #   v4-pro-0813 Baidu:  20000*0.6*1.3e-7 + 20000*0.4*0 + 12000*4e-7 = 0.00636
    #   v4-pro-0813 Relace: 20000*0.6*1.2e-7 + 20000*0.4*1.2e-7 + 12000*8e-6 = 0.0984
    #   v4-pro-0813 primary: 20000*0.6*6.6e-7 + 20000*0.4*6.6e-8 + 12000*1.98e-6 = 0.032208
    #   v4-pro (no eps):    20000*0.6*2.1e-7 + 20000*0.4*2e-8 + 12000*4.2e-7 = 0.00772
    #   mimo baseline:      20000*0.6*4.35e-7 + 20000*0.4*3.6e-9 + 12000*8.7e-7 = 0.0156688
    models = [
        make_model("deepseek/deepseek-v4-pro", "0.00000021", "0.00000042",
                   "0.00000002", canonical="deepseek/deepseek-v4-pro-20260423"),
        make_model("deepseek/deepseek-v4-pro-0813", "0.00000066", "0.00000198",
                   "0.000000066", canonical="deepseek/deepseek-v4-pro-20260813"),
        make_model("deepseek/deepseek-v4-flash", "0.0000002", "0.000001",
                   "0.00000002"),
        make_model("xiaomi/mimo-v2.6-pro", "0.000000435", "0.00000087",
                   "0.0000000036", canonical="xiaomi/mimo-v2.6-pro-20260921",
                   params=("reasoning",)),
    ]
    classifications = {"as_of": "2026-10-17", "classifications": [
        {"tag": "content_writing", "usage_share": 0.1, "models": [
            {"id": "deepseek/deepseek-v4-pro-20260813", "tag_usage_share": 0.5},
            {"id": "deepseek/deepseek-v4-pro-20260423", "tag_usage_share": 0.25},
            {"id": "ghost/unknown-20260101", "tag_usage_share": 0.1},
            {"id": "deepseek/deepseek-v4-flash-20260101", "tag_usage_share": 0.05},
        ]},
        {"tag": "roleplay_fiction", "usage_share": 0.05, "models": [
            {"id": "deepseek/deepseek-v4-pro-20260813", "tag_usage_share": 0.2},
        ]},
        {"tag": "math", "usage_share": 0.2, "models": [
            {"id": "xiaomi/mimo-v2.6-pro-20260921", "tag_usage_share": 1.0},
        ]},
        {"tag": "translation", "usage_share": 0.03, "models": [
            {"id": "deepseek/deepseek-v4-flash-20260101", "tag_usage_share": 0.6},
            {"id": "xiaomi/mimo-v2.6-pro-20260921", "tag_usage_share": 0.4},
        ]},
    ]}
    rankings = {"data": [
        {"date": "2026-10-24",
         "model_permaslug": "deepseek/deepseek-v4-pro-20260813",
         "total_tokens": "2000000000"},
        {"date": "2026-10-24",
         "model_permaslug": "deepseek/deepseek-v4-pro-20260423",
         "total_tokens": "3000000000"},
        {"date": "2026-10-24",
         "model_permaslug": "ghost/unknown-20260101", "total_tokens": "100"},
        {"model_permaslug": "other", "total_tokens": "9999999"},
    ]}
    endpoints = {
        "deepseek/deepseek-v4-pro-0813": [
            {"name": "Baidu", "pricing": {"prompt": "0.00000013",
                                          "completion": "0.0000004",
                                          "input_cache_read": "0"}},
            {"name": "Relace", "pricing": {"prompt": "0.00000012",
                                           "completion": "0.000008",
                                           "input_cache_read": "0.00000012"}},
        ],
    }
    # Real feed shapes (unfiltered https://openrouter.ai/api/v1/benchmarks):
    # {"data": [rows from all three sources], "meta": {as_of, source: null,
    # citation: null, model_count}}; the per-row "source" field discriminates.
    benchmarks = {
        "meta": {"as_of": "2026-10-26T00:01:10.159Z", "source": None,
                 "citation": None, "model_count": 419},
        "data": [
            {"source": "artificial-analysis",
             "model_permaslug": "deepseek/deepseek-v4-flash-20260101",
             "display_name": "DeepSeek V4 Flash",
             "intelligence_index": 40.2, "coding_index": None,
             "agentic_index": None,
             "pricing": {"prompt": "0.0000002", "completion": "0.000001"}},
            {"source": "artificial-analysis",
             "model_permaslug": "xiaomi/mimo-v2.6-pro-20260921",
             "display_name": "Xiaomi MiMo v2.6 Pro",
             "intelligence_index": 55.1, "coding_index": 48.0,
             "agentic_index": 41.3,
             "pricing": {"prompt": "0.0000005", "completion": "0.000001"}},
            {"source": "artificial-analysis",
             "model_permaslug": "deepseek/deepseek-v4-pro-20260813",
             "display_name": "DeepSeek V4 Pro (Aug)",
             "intelligence_index": 57.6, "coding_index": 52.4,
             "agentic_index": 49.9,
             "pricing": {"prompt": "0.00000066", "completion": "0.00000198"}},
            {"source": "artificial-analysis",
             "model_permaslug": "openai/gpt-5.6-sol-20261001",
             "display_name": "GPT-5.6 Sol",
             "intelligence_index": 60.0, "coding_index": 58.0,
             "agentic_index": 55.0,
             "pricing": {"prompt": "0.000001", "completion": "0.000004"}},
            {"source": "design-arena",
             "model_permaslug": "deepseek/deepseek-v4-flash-20260101",
             "display_name": "DeepSeek V4 Flash",
             "arena": "models", "category": "writing", "elo": 1180,
             "win_rate": 55,
             "pricing": {"prompt": "0.0000002", "completion": "0.000001"}},
            {"source": "design-arena",
             "model_permaslug": "deepseek/deepseek-v4-flash-20260101",
             "display_name": "DeepSeek V4 Flash",
             "arena": "models", "category": "3d", "elo": 1102,
             "win_rate": 48,
             "pricing": {"prompt": "0.0000002", "completion": "0.000001"}},
            {"source": "design-arena",
             "model_permaslug": "xiaomi/mimo-v2.6-pro-20260921",
             "display_name": "Xiaomi MiMo v2.6 Pro",
             "arena": "models", "category": "coding", "elo": 1301,
             "win_rate": 61,
             "pricing": {"prompt": "0.0000005", "completion": "0.000001"}},
            {"source": "openrouter",
             "model_permaslug": "deepseek/deepseek-v4-flash-20260101",
             "display_name": "DeepSeek V4 Flash",
             "benchmark_type": "gpqa_diamond", "accuracy": 0.62,
             "avg_cost_per_task": 0.011,
             "last_run_timestamp": "2026-10-14T15:00:03.588Z"},
            {"source": "openrouter",
             "model_permaslug": "xiaomi/mimo-v2.6-pro-20260921",
             "display_name": "Xiaomi MiMo v2.6 Pro",
             "benchmark_type": "math_agent", "accuracy": 0.9,
             "avg_cost_per_task": 0.02,
             "avg_latency_per_task_ms": 15000,
             "last_run_timestamp": "2026-10-20T09:00:00.000Z",
             "pricing": {"prompt": "0.0000005", "completion": "0.000001"}},
        ],
    }
    return {"models": models, "classifications": classifications,
            "rankings": rankings, "endpoints": endpoints,
            "benchmarks": benchmarks}


POLICY = {
    "baseline": {"id": "xiaomi/mimo-v2.6-pro", "notes": "anchor"},
    "hints": {
        "deepseek/deepseek-v4-pro": {"note": "skipped on output cost",
                                     "fit": {"coding": "favor"},
                                     "evidence": "validated"},
        "deepseek/deepseek-v4-flash": {"note": "felt good for bulk writing",
                                       "fit": {"writing": "favor"},
                                       "evidence": "validated"},
        "ghost/unknown-20260101": {"note": "try it for code",
                                   "fit": {"coding": "favor"},
                                   "evidence": "validated"},
        "gone/hinted": {"note": "vanished", "fit": {"writing": "favor"},
                        "evidence": "validated"},
    },
    "summaries": {"deepseek/deepseek-v4-pro-0813": "eol sibling summary",
                  "deepseek/deepseek-v4-pro": "eol summary",
                  "stale/model": "gone summary"},
    "domains": {
        "writing": ["content_writing", "roleplay_fiction", "gone_tag"],
        "coding": ["math"],
    },
    "scoring": {"alpha": 1.0, "beta": 0.0,
                "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                               "top2_max": 0.75}},
    "affinity": {
        "blend_weight": 0.6,
        "eligibility_top_k": 2,
        "factors": {"favor_validated": 3.0, "favor_suspected": 2.0,
                    "avoid_validated": 0.3, "avoid_suspected": 0.5},
    },
}


# Golden stdout for `run_cli("--domain", "writing")` on the fixture machine
# with its zones.json present (declaring nothing closed), captured before
# issue #38. A present zones file may not move a single byte: no advisory
# line, and no reworded pool claim where free routes genuinely remain. The
# `{cwd}` slot is the working folder the header names.
PRESENT_ZONES_GOLDEN = """\
# Popularity ranking: writing

zone: {cwd} (open)
profile=authoring (in=20,000 out=12,000 cached=40%) | effort=measured | basis=worst | policy: 0d old | source: OpenRouter (openrouter.ai/rankings), as of 2026-10-17

free quota: unavailable | :free routes stay in the pool
| # | model | share | score | 30d tokens | $/1M out (floor–worst) | $/ticket | Δ baseline | ctx | Exposure | rung |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | deepseek/deepseek-v4-pro-0813 | 6.00% | 0.06 | 2B | 0.40–8.00 (2 eps, wide) | $0.0984 | 6.27x | ? | — | medium |
| 2 | deepseek/deepseek-v4-pro | 2.50% | 0.03 | 3B | 0.42–0.42 (no endpoint data) | $0.0077 | 0.49x | ? | — | medium |
| 3 | deepseek/deepseek-v4-flash | 0.50% | 0.01 | 0B | 1.00–1.00 (no endpoint data) | $0.0146 | 0.93x | ? | — | medium |
| 4 | ghost/unknown-20260101 | 1.00% | — | 0B | — unresolved to a priced model | | | ? | — | |

note: leaderboard rows resolved without canonical match (price unverified or unpriced): deepseek/deepseek-v4-flash, ghost/unknown-20260101

hints (advisory; eligibility stays popularity — the deal tilts by preference):
  deepseek/deepseek-v4-pro-0813: skipped on output cost
  deepseek/deepseek-v4-pro: skipped on output cost
  ghost/unknown-20260101: try it for code
  deepseek/deepseek-v4-flash: felt good for bulk writing

summaries (task-fit context; never taste):
  deepseek/deepseek-v4-pro-0813: eol sibling summary
  deepseek/deepseek-v4-pro: eol summary

default pick (top of task order): openrouter/deepseek/deepseek-v4-pro-0813
route to floor: pin provider 'Baidu' via body.provider.order (allow_fallbacks: false) — unpinned worst endpoint is 'Relace' at $0.0984/ticket
cheapest shown: deepseek/deepseek-v4-pro at $0.0077/ticket (budget pressure moves within the ranking, by price)
projection at 1 ticket(s): $0.10 (floor $0.01) | baseline anchor: $0.02
"""


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        with open(self.policy_path, "w") as f:
            json.dump(POLICY, f)

    def tearDown(self):
        self._tmp.cleanup()

    def zones_file(self, zones):
        """This fixture machine's free-use zones: the bare list of paths
        declared closed (ADR-0010). A test about pricing, quota or the deal
        declares the machine open — an empty list — so the zone gate stays
        out of its way; a test about the gate declares exactly the paths it
        closes."""
        declared = []
        for entry in zones or []:
            if isinstance(entry, dict):
                # The retired per-entry form: only `closed` is a declaration
                # under the bare list, so an `open` entry declares nothing.
                if entry.get("free", "open") == "closed":
                    declared.append(entry["path"])
                continue
            declared.append(entry)
        config_home = os.path.join(self._tmp.name, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": declared}, f)
        return config_home

    def roster_file(self, entries):
        """This fixture machine's Local roster, beside its zones.json: the
        band + prose keyed by harness id, exactly as the contract spells it."""
        config_home = os.path.join(self._tmp.name, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit",
                               "local-roster.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"version": 1, "entries": entries}, f)
        return config_home

    def run_cli(self, *argv, world=None, local_models=None, local_listing=None,
                listing_absent=False, serving_endpoint=None, key_payload=None,
                zones=None, policy_path=None,
                zones_absent=False, real_benchmarks=False):
        world = world if world is not None else build_world()
        local_models = local_models if local_models is not None else {}
        # The harness passes its local universe in with --local-listing: a
        # fixture's served ids are exactly what this fixture machine's
        # harness lists, `listing_absent` models a harness that never spoke,
        # and a present flag with no ids is a listing that runs nothing.
        if listing_absent:
            listing_flag = []
        elif local_listing is None:
            listing_flag = ["--local-listing", ",".join(sorted(local_models))]
        else:
            listing_flag = ["--local-listing", ",".join(sorted(local_listing))]
        if zones_absent:
            # A fresh install: no zones.json exists anywhere the loader
            # looks, so the config root falls back to ~/.config against a
            # throwaway home and nothing ever creates it.
            home = os.path.join(self._tmp.name, "home")
            env = {"XDG_CONFIG_HOME": "", "HOME": home, "USERPROFILE": home}
        else:
            config_home = self.zones_file(zones)
            env = {"XDG_CONFIG_HOME": config_home}
        calls = []
        real_fetch = modelbandit.fetch_json  # captured before the mock patches it

        def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
            calls.append((url, cache_name, auth, refresh))
            if real_benchmarks and cache_name == "benchmarks.json":
                # Deliberate seam widening beyond the mocked-fetch decision:
                # these two anchors tests exercise the real fetch_json path
                # (offline-safe: patched cache dir + api key, no network).
                return real_fetch(url, cache_name, auth=auth,
                                  refresh=refresh)
            if cache_name == "key.json":
                if key_payload is None:
                    # No key, or an unreachable endpoint: the counter is not
                    # reported and the run carries on without it.
                    raise SystemExit("cannot reach https://openrouter.ai/api/v1/key")
                return key_payload
            if cache_name == "benchmarks.json":
                return world["benchmarks"]
            if cache_name == "models.json":
                return {"data": world["models"]}
            if cache_name == "classifications.json":
                return {"data": world["classifications"]}
            if cache_name == "rankings.json":
                return world["rankings"]
            if url.endswith("/endpoints"):
                slug = url[len(modelbandit.MODELS_URL) + 1:-len("/endpoints")]
                return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
            raise AssertionError(f"unexpected fetch: {url}")

        out, err = io.StringIO(), io.StringIO()
        code = None
        argv = ["modelbandit", "--policy", policy_path or self.policy_path,
                *listing_flag, *argv]
        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch), \
                mock.patch("modelbandit.probe_local_models", return_value=local_models), \
                mock.patch("modelbandit.harness_serving_endpoint",
                           return_value=serving_endpoint or
                           modelbandit.DEFAULT_LOCAL_ENDPOINT), \
                mock.patch.object(modelbandit, "CACHE_DIR",
                                  os.path.join(self._tmp.name, "cache")), \
                mock.patch.dict(os.environ, env), \
                mock.patch("modelbandit.git_origin", return_value=None), \
                mock.patch.object(sys, "argv", argv), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code, calls

    # --- domain and policy plumbing -------------------------------------

    def test_list_domains(self):
        out, _, code, _ = self.run_cli("--list-domains")
        self.assertIsNone(code)
        self.assertIn("writing", out)
        self.assertIn("content_writing", out)
        self.assertIn("coding", out)

    def test_check_policy_reports_gaps_and_stale(self):
        out, _, code, _ = self.run_cli("--check-policy")
        self.assertIsNone(code)
        self.assertIn("# Policy check", out)
        self.assertIn("policy.json last modified: 0 days old", out)
        gaps = out[out.index("Research gaps"):out.index("Stale summaries")]
        self.assertIn("deepseek/deepseek-v4-flash", gaps)
        self.assertNotIn("deepseek/deepseek-v4-pro-0813", gaps)
        stale = out[out.index("Stale summaries"):out.index("research cycle due")]
        self.assertIn("stale/model", stale)
        self.assertIn("not in model list", stale)
        self.assertIn("research cycle due: yes", out)

    def test_check_policy_reports_signal_drift(self):
        out, _, code, _ = self.run_cli("--check-policy")
        self.assertIsNone(code)
        stale = out[out.index("Stale signals"):out.index("Signal coverage gaps")]
        self.assertIn("gone/hinted", stale)
        gaps = out[out.index("Signal coverage gaps"):out.index("research cycle due")]
        self.assertIn("deepseek/deepseek-v4-pro ranks in writing", gaps)
        self.assertNotIn("ghost/unknown-20260101", gaps)  # outside eligibility
        self.assertIn("research cycle due: yes", out)

    def test_a_catalog_summary_ref_closes_its_gap(self):
        # An opencode/* id can never prefix-match its family summary key,
        # but it resolves one through summary_ref everywhere else in the
        # file (catalog gate, table column) — so the drift set counts it
        # as having a summary too. The route must actually rank for the
        # assertion to mean anything, hence the ranking run first.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {
            "opencode/deepseek-v4-pro-free": {
                "context_length": 65_536, "exposure": "no-retention",
                "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        ranked, _, rank_code, _ = self.run_cli("--domain", "writing")
        self.assertIsNone(rank_code)
        self.assertIn("opencode/deepseek-v4-pro-free", ranked)

        out, _, code, _ = self.run_cli("--check-policy")
        self.assertIsNone(code)
        gaps = out[out.index("Research gaps"):out.index("Stale summaries")]
        self.assertNotIn("opencode/deepseek-v4-pro-free", gaps)

    def test_a_summary_a_ranked_route_references_is_not_stale(self):
        # Stale is the mirror of the gap: without the summary_ref seam,
        # "stale/model" would retire here even though a ranked cataloged
        # route still serves it — the ref is how the family summary
        # reaches an opencode/* id.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {
            "opencode/stale-model-free": {
                "context_length": 65_536, "exposure": "no-retention",
                "summary_ref": "stale/model"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        out, _, code, _ = self.run_cli("--check-policy")
        self.assertIsNone(code)
        stale = out[out.index("Stale summaries"):out.index("Stale signals")]
        self.assertNotIn("stale/model", stale)

    def test_an_unresolvable_summary_ref_does_not_close_the_gap(self):
        # Only a ref that resolves silences the drift: this ranked :free
        # board row's entry points at a summaries key that does not exist.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {
            "vendor/model": {"context_length": 65_536,
                             "exposure": "no-retention",
                             "summary_ref": "missing/family"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        out, _, code, _ = self.run_cli("--check-policy",
                                       world=self.free_world(("vendor/model:free",
                                                              0.5)))
        self.assertIsNone(code)
        gaps = out[out.index("Research gaps"):out.index("Stale summaries")]
        self.assertIn("vendor/model:free", gaps)

    def test_check_policy_reports_zero_free_share_for_an_eligible_safe_shape(self):
        pol = json.loads(json.dumps(POLICY))
        pol["domains"] = {"writing": ["content_writing"]}
        pol["scoring"].update(alpha=1.0, beta=0.0)
        pol["affinity"].update(blend_weight=0.0, eligibility_top_k=5)
        pol["free_models"] = {"vendor/model": {
            "context_length": 262_144, "exposure": "trains",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        with open(self.policy_path, "rb") as f:
            before = f.read()

        world = build_world()
        world["models"] = [
            make_model(f"m{i}/model", "0.000001", "0.000002", "0.000001")
            for i in range(4)] + [make_model("vendor/model:free", "0", "0", "0")]
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 1.0,
            "models": ([{"id": f"m{i}/model", "tag_usage_share": 0.25}
                        for i in range(4)]
                       + [{"id": "vendor/model:free", "tag_usage_share": 1e-30}]),
        }]

        out, _, code, _ = self.run_cli("--check-policy", world=world)

        self.assertIsNone(code)
        self.assertIn("free-share-trends-to-zero", out)
        self.assertIn("writing", out)
        self.assertIn("0/100", out)
        self.assertIn("no history", out)
        with open(self.policy_path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_check_policy_tracks_zero_free_share_for_served_local_candidate(self):
        pol = json.loads(json.dumps(POLICY))
        pol["domains"] = {"writing": ["content_writing"]}
        pol["affinity"].update(blend_weight=0.0, eligibility_top_k=5)
        # A family with no ranked share in this fixture keeps the free
        # candidates genuinely share-less, so the zero-trend signal fires
        # (family-share inheritance would otherwise give them real rotation).
        pol["summaries"]["ghost/family"] = "family summary"
        pol["free_models"] = {
            "lmstudio/local-coder": {"context_length": 262_144,
                                      "exposure": "local",
                                      "summary_ref": "ghost/family"},
            "opencode/free-coder": {
                "context_length": 262_144, "exposure": "no-retention",
                "summary_ref": "ghost/family"},
        }
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        local = {"lmstudio/local-coder": {"id": "lmstudio/local-coder",
                                           "context_length": 262_144}}
        world = build_world()
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 1.0,
            "models": [
                {"id": "deepseek/deepseek-v4-pro-20260813",
                 "tag_usage_share": 0.5},
                {"id": "deepseek/deepseek-v4-pro-20260423",
                 "tag_usage_share": 0.3},
                {"id": "deepseek/deepseek-v4-flash-20260101",
                 "tag_usage_share": 0.2},
            ]}]

        first, _, code, _ = self.run_cli("--check-policy", world=world,
                                        local_models=local)
        second, _, code2, _ = self.run_cli("--check-policy", world=world,
                                           local_models=local)
        table, _, table_code, _ = self.run_cli("--domain", "writing",
                                               world=world, local_models=local)

        self.assertIsNone(code)
        self.assertIsNone(code2)
        self.assertIsNone(table_code)
        # Both routes resolve their family summary through summary_ref, so
        # the drift set no longer names them as gaps; the ranking's summary
        # block names them with that same resolved summary — one ref, one
        # answer on both surfaces.
        self.assertIn("local-coder: family summary", table)
        self.assertIn("opencode/free-coder: family summary", table)
        self.assertNotIn("local-coder", first[first.index("Research gaps"):
                                              first.index("Stale summaries")])
        self.assertIn("no history", first)
        self.assertIn("free share 0 for 2 consecutive checks", second)

    def test_check_policy_does_not_flag_a_free_route_that_gets_share(self):
        pol = json.loads(json.dumps(POLICY))
        pol["domains"] = {"writing": ["content_writing"]}
        pol["scoring"].update(alpha=1.0, beta=0.0)
        pol["affinity"].update(blend_weight=0.0, eligibility_top_k=1)
        pol["free_models"] = {"vendor/model": {
            "context_length": 262_144, "exposure": "trains",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        world = build_world()
        world["models"] = [make_model("vendor/model:free", "0", "0", "0")]
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 1.0,
            "models": [{"id": "vendor/model:free", "tag_usage_share": 1.0}],
        }]

        out, _, code, _ = self.run_cli("--check-policy", world=world)

        self.assertIsNone(code)
        self.assertNotIn("- free-share-trends-to-zero:", out)

    def test_signal_coverage_gap_closed_by_explicit_neutral(self):
        pol = json.loads(json.dumps(POLICY))
        pol["hints"]["ghost/unknown-20260101"]["fit"]["writing"] = "neutral"
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, _, _ = self.run_cli("--check-policy")
        gaps = out[out.index("Signal coverage gaps"):out.index("research cycle due")]
        self.assertNotIn("ghost/unknown-20260101", gaps)

    def test_thin_pool_balance_not_judgeable(self):
        # A pool with fewer than three candidates has nothing to judge: a
        # one-candidate pool is 100% top mass by definition, not a tuning
        # failure. Balance says so and never trips the re-tune verdict.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=0.0)  # mass ~ shares as computed below
        pol["domains"] = {"coding": ["math"]}  # single candidate in this domain
        pol["hints"] = {
            "ghost/unknown-20260101": {"note": "try it for code",
                                       "fit": {"coding": "favor"},
                                       "evidence": "validated"},
            "gone/hinted": {"note": "vanished", "fit": {"writing": "favor"},
                            "evidence": "validated"},
        }
        pol["summaries"] = {
            "deepseek/deepseek-v4-pro-0813": "eol sibling summary",
            "deepseek/deepseek-v4-pro": "eol summary",
            "stale/model": "gone summary",
        }
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.run_cli("--check-policy")
        self.assertIsNone(code)
        balance = out[out.index("## Score balance"):]
        self.assertIn("not judgeable", balance)       # says so instead of judging
        self.assertNotIn("OUT OF BALANCE", balance)   # never a balance failure
        self.assertIn("coefficient re-tune due: no", out)

    def test_signal_coverage_gap_only_inside_eligibility_top_k(self):
        # A coverage gap needs two things: silence about the domain the model
        # ranks in, and a rank inside the eligibility top-K (a deal player).
        # m4 is silent about writing and inside the cut -> gaps; m5 is equally
        # silent but below the cut -> never gaps; m0-m3 name writing -> no gap.
        pol = json.loads(json.dumps(POLICY))
        pol["affinity"]["eligibility_top_k"] = 5
        pol["domains"] = {"writing": ["content_writing"]}
        pol["summaries"] = {}
        pol["hints"] = {}
        for i in range(4):
            pol["hints"][f"m{i}/model"] = {"note": "n",
                                           "fit": {"writing": "favor"},
                                           "evidence": "validated"}
        for i in (4, 5):
            pol["hints"][f"m{i}/model"] = {"note": "n",
                                           "fit": {"coding": "favor"},
                                           "evidence": "validated"}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["models"] += [make_model(f"m{i}/model", "0.000001", "0.000002",
                                       "0.000001") for i in range(6)]
        world["classifications"]["classifications"][0]["models"] = [
            {"id": f"m{i}/model", "tag_usage_share": share}
            for i, share in enumerate((0.3, 0.25, 0.2, 0.15, 0.08, 0.02))]
        out, _, code, _ = self.run_cli("--check-policy", world=world)
        self.assertIsNone(code)
        gaps = out[out.index("Signal coverage gaps"):out.index("research cycle due")]
        self.assertIn("m4/model ranks in writing", gaps)  # silent, in the cut
        self.assertNotIn("m5/model", gaps)                # silent, below the cut
        self.assertNotIn("m0/model", gaps)                # names writing
        self.assertNotIn("m3/model", gaps)
        self.assertIn("research cycle due: yes", out)

    def test_five_candidate_pool_balance_behaves_as_before(self):
        # A normal five-candidate pool is judged as before: measured top-1 /
        # top-2 against the thresholds and the same OUT OF BALANCE verdict.
        pol = json.loads(json.dumps(POLICY))
        pol["affinity"]["eligibility_top_k"] = 5
        pol["domains"] = {"writing": ["content_writing"]}
        pol["summaries"] = {}
        pol["hints"] = {
            "m0/model": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"},
            "m1/model": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"},
            "m2/model": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"},
            "m3/model": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"},
            "m4/model": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"},
        }
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["models"] += [make_model(f"m{i}/model", "0.000001", "0.000002",
                                       "0.000001") for i in range(5)]
        world["classifications"]["classifications"][0]["models"] = [
            {"id": f"m{i}/model", "tag_usage_share": share}
            for i, share in enumerate((0.6, 0.2, 0.1, 0.06, 0.04))]
        out, _, code, _ = self.run_cli("--check-policy", world=world)
        self.assertIsNone(code)
        balance = out[out.index("## Score balance"):]
        self.assertIn("writing: top-1 60%, top-2 80%", balance)
        self.assertIn("OUT OF BALANCE", balance)      # as before: 60/80 breaches
        self.assertIn("coefficient re-tune due: yes", out)
        self.assertNotIn("not judgeable", balance)    # five candidates are judgeable

    # --- scope facts ------------------------------------------------------

    def test_scope_alone_implies_the_check(self):
        out, _, code, calls = self.run_cli("--scope")
        self.assertIsNone(code)
        self.assertIn("# Policy check", out)
        self.assertIn("research cycle due:", out)
        self.assertIn("rankings.json", [c[1] for c in calls])

    def test_bare_check_fetches_no_rankings_and_prints_no_facts(self):
        out, _, code, calls = self.run_cli("--check-policy")
        self.assertIsNone(code)
        self.assertNotIn("ranks:", out)
        self.assertNotIn("catalog:", out)
        self.assertNotIn("rankings.json", [c[1] for c in calls])

    def test_gap_bullets_carry_catalog_and_ranks_facts(self):
        out, _, code, _ = self.run_cli("--scope")
        self.assertIsNone(code)
        flash = out[out.index("- deepseek/deepseek-v4-flash (writing)"):
                    out.index("- ghost/unknown-20260101")]
        self.assertIn("  ranks: writing #4/4, other tags: translation #1/2",
                      flash)
        self.assertIn("catalog: created ?, context ?, "
                      "$0.20/$1.00 per 1M in/out, "
                      "window: 0.00T tokens, 0/1 days",
                      " ".join(flash.split()))
        mimo = out[out.index("- xiaomi/mimo-v2.6-pro (coding)"):
                   out.index("## Stale summaries")]
        self.assertIn("  ranks: coding #1/1, other tags: translation #2/2",
                      mimo)
        self.assertIn("$0.43/$0.87 per 1M in/out", mimo)
        ghost = out[out.index("- ghost/unknown-20260101"):
                    out.index("- xiaomi/mimo-v2.6-pro (coding)")]
        self.assertIn("  ranks: writing #3/4", ghost)
        self.assertIn("  catalog: not in model list, "
                      "window: 0.00T tokens, 1/1 days", ghost)

    def test_stale_bullets_carry_absent_phrase_and_keep_the_note(self):
        out, _, _, _ = self.run_cli("--scope")
        stale = out[out.index("## Stale summaries"):out.index("## Stale signals")]
        self.assertIn("- stale/model — not in model list", stale)
        self.assertIn("  ranks: absent from all 4 tags and all 2 domains",
                      stale)
        self.assertIn("  catalog: not in model list, "
                      "window: 0.00T tokens, 0/1 days", stale)

    def test_stale_signal_bullets_carry_the_same_facts(self):
        out, _, _, _ = self.run_cli("--scope")
        sig = out[out.index("## Stale signals"):out.index("## Signal coverage gaps")]
        self.assertIn("- gone/hinted", sig)
        self.assertIn("  ranks: absent from all 4 tags and all 2 domains", sig)
        self.assertIn("  catalog: not in model list", sig)

    def test_scope_writes_nothing_to_the_policy(self):
        before = open(self.policy_path).read()
        self.run_cli("--scope")
        self.assertEqual(open(self.policy_path).read(), before)

    def test_scope_adds_only_indented_fact_lines_to_the_check(self):
        bare, _, _, _ = self.run_cli("--check-policy")
        scoped, _, _, _ = self.run_cli("--scope")
        kept = [ln for ln in scoped.splitlines() if not ln.startswith(" ")]
        self.assertEqual(kept, bare.splitlines())

    def test_window_line_carries_dates_tokens_and_days(self):
        world = build_world()
        world["models"].append(make_model("acme/acme-star", "0.00000125",
                                          "0.000005", "0", created=1768435200,
                                          context=262144))
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "acme/acme-star", "tag_usage_share": 0.02})
        world["rankings"] = {
            "meta": {"start_date": "2026-09-25", "end_date": "2026-10-24"},
            "data": world["rankings"]["data"] + [
                {"date": "2026-10-01", "model_permaslug": "acme/acme-star",
                 "total_tokens": "5000000000000"},
                {"date": "2026-10-15", "model_permaslug": "acme/acme-star",
                 "total_tokens": "5000000000000"},
                {"date": "2026-10-24", "model_permaslug": "acme/acme-star",
                 "total_tokens": "5000000000000"},
            ],
        }
        out, _, code, _ = self.run_cli("--scope", world=world)
        self.assertIsNone(code)
        block = out[out.index("- acme/acme-star (writing)"):
                    out.index("## Stale summaries")]
        self.assertIn("  ranks: writing #3/5", block)
        self.assertIn("catalog: created 2026-01-15, context 256K, "
                      "$1.25/$5.00 per 1M in/out, "
                      "window 2026-09-25..2026-10-24: 15.00T tokens, 3/30 days",
                      " ".join(block.split()))

    def test_below_cut_positions_come_from_the_full_board(self):
        # Ten candidates on the writing board with the default --top 8: the
        # stale summary at #9 and the stale signal at #10 sit below the cut,
        # and their scope facts must still show the position and size of the
        # whole board.
        world = build_world()
        names = ["acme/one", "acme/two", "acme/three", "acme/four",
                 "acme/five", "acme/six", "acme/seven", "acme/eight",
                 "acme/nine", "acme/ten"]
        world["models"] += [make_model(n, "0.000001", "0.000002", "0")
                            for n in names[:8]]
        world["models"] += [
            make_model("acme/nine", "0.000002", "0.000006", "0",
                       created=1769904000, context=131072),
            make_model("acme/ten", "0.000002", "0.000006", "0",
                       created=1769904000, context=131072),
        ]
        world["classifications"]["classifications"][0]["models"] = [
            {"id": n, "tag_usage_share": (10 - i) / 100}
            for i, n in enumerate(names)]
        world["rankings"]["data"] += [
            {"date": "2026-10-20", "model_permaslug": "acme/nine",
             "total_tokens": "3000000000000"},
            {"date": "2026-10-23", "model_permaslug": "acme/nine",
             "total_tokens": "2500000000000"},
        ]
        pol = json.loads(json.dumps(POLICY))
        pol["domains"] = {"writing": ["content_writing"]}
        pol["summaries"] = {n: "s" for n in names[:8]}
        pol["summaries"]["acme/nine"] = "s"
        pol["hints"] = {"acme/ten": {"note": "n", "fit": {"writing": "favor"},
                                     "evidence": "validated"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.run_cli("--scope", world=world)
        self.assertIsNone(code)
        stale = out[out.index("## Stale summaries"):out.index("## Stale signals")]
        self.assertIn("- acme/nine\n", stale)
        self.assertNotIn("not in model list", stale)  # it is listed, just below cut
        self.assertIn("  ranks: writing #9/10", stale)
        self.assertIn("catalog: created 2026-02-01, context 128K, "
                      "$2.00/$6.00 per 1M in/out, "
                      "window: 5.50T tokens, 2/3 days",
                      " ".join(stale.split()))
        sig = out[out.index("## Stale signals"):out.index("## Signal coverage gaps")]
        self.assertIn("- acme/ten", sig)
        self.assertIn("  ranks: writing #10/10", sig)
        # No meta in this fixture: the window denominator is the days the
        # feed itself carries (10-20, 10-23, 10-24), not a hardcoded 30.

    def test_none_placeholder_carries_no_facts(self):
        # "— none" is a placeholder, not a model: no facts hang off it.
        pol = json.loads(json.dumps(POLICY))
        pol["summaries"].update({
            "ghost/unknown-20260101": "s", "deepseek/deepseek-v4-flash": "s",
            "xiaomi/mimo-v2.6-pro": "s"})
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, _, _ = self.run_cli("--scope")
        gaps = out[out.index("## Research gaps"):out.index("## Stale summaries")]
        self.assertIn("- — none\n", gaps)
        self.assertNotIn("ranks:", gaps)
        self.assertNotIn("catalog:", gaps)

    def test_unresolved_gap_catalog_does_not_borrow_a_prefix_sibling(self):
        # A gap is an exact mid: if it is not in the model list, its catalog
        # line says so — it never borrows the row of a prefix sibling.
        world = build_world()
        world["models"].append(make_model("ghost/unknown-20260101-lite",
                                          "0.000001", "0.000002", "0"))
        out, _, _, _ = self.run_cli("--scope", world=world)
        ghost = out[out.index("- ghost/unknown-20260101"):
                    out.index("- xiaomi/mimo-v2.6-pro (coding)")]
        self.assertIn("  catalog: not in model list", ghost)

    # --- anchors -----------------------------------------------------------

    def test_anchors_derives_scope_gaps_then_stale(self):
        # Derived scope: gaps (flash, ghost, mimo), then stale summaries
        # (stale/model), then stale signals (gone/hinted) — the check's
        # section order. Table rows follow that same scope order.
        out, _, code, _ = self.run_cli("--anchors")
        self.assertIsNone(code)
        self.assertIn("# Benchmark anchors", out)
        self.assertIn("feed as of 2026-10-26T00:01:10.159Z — 2 of the "
                      "scope's models have rows; the feed carries 419 models",
                      out)
        aa = out[out.index("## Artificial Analysis"):out.index("## Design Arena")]
        self.assertLess(aa.index("deepseek/deepseek-v4-flash"),
                        aa.index("xiaomi/mimo-v2.6-pro"))
        tail = out[out.index("no benchmark rows:"):].splitlines()[0]
        self.assertIn("stale/model", tail)
        self.assertIn("gone/hinted", tail)

    def test_anchors_explicit_ids_override_the_derived_set(self):
        out, _, code, _ = self.run_cli("--anchors", "deepseek/deepseek-v4-pro")
        self.assertIsNone(code)
        self.assertIn("deepseek/deepseek-v4-pro-20260813", out)
        self.assertIn("1 of the scope's models have rows; the feed carries "
                      "419 models", out)
        self.assertNotIn("deepseek/deepseek-v4-flash", out)
        self.assertNotIn("xiaomi/mimo-v2.6-pro", out)
        self.assertNotIn("stale/model", out)
        self.assertIn("no benchmark rows: — none", out)

    def test_anchors_explicit_dated_catalog_id_finds_permaslug_rows(self):
        # A dated-catalog id (…-0813) does not prefix-match the feed's
        # permaslug (…-20260813); it must resolve through canonical_slug like
        # every other id and reach the rows under that permaslug.
        out, _, code, _ = self.run_cli("--anchors", "deepseek/deepseek-v4-pro-0813")
        self.assertIsNone(code)
        self.assertIn("deepseek/deepseek-v4-pro-20260813", out)
        self.assertIn("57.6", out)  # the AA row under the permaslug renders
        self.assertIn("1 of the scope's models have rows; the feed carries "
                      "419 models", out)
        self.assertIn("no benchmark rows: — none", out)

    def test_anchors_prints_three_source_tables_with_citations(self):
        out, _, _, _ = self.run_cli("--anchors")
        for heading, cite in (
                ("## Artificial Analysis",
                 "Source: Artificial Analysis (artificialanalysis.ai) via "
                 "OpenRouter (openrouter.ai/rankings)."),
                ("## Design Arena",
                 "Source: Design Arena (www.designarena.ai) via OpenRouter "
                 "(openrouter.ai/rankings)."),
                ("## OpenRouter evals",
                 "Source: OpenRouter evals (openrouter.ai) via OpenRouter "
                 "(openrouter.ai/rankings).")):
            self.assertIn(heading, out)
            self.assertIn(cite, out)

    def test_anchors_null_indexes_render_missing_and_prices_per_1m(self):
        out, _, _, _ = self.run_cli("--anchors")
        aa = out[out.index("## Artificial Analysis"):out.index("## Design Arena")]
        flash = next(ln for ln in aa.splitlines() if "v4-flash" in ln)
        self.assertIn("| 40.2 | — | — | $0.20/$1.00 |", flash)
        mimo = next(ln for ln in aa.splitlines() if "mimo" in ln)
        self.assertIn("| 55.1 | 48.0 | 41.3 | $0.50/$1.00 |", mimo)

    def test_anchors_design_arena_rows_carry_arena_elo_win_rate(self):
        out, _, _, _ = self.run_cli("--anchors")
        da = out[out.index("## Design Arena"):out.index("## OpenRouter evals")]
        self.assertIn("| models | writing | 1180 | 55% | $0.20/$1.00 |", da)
        self.assertIn("| models | 3d | 1102 | 48% | $0.20/$1.00 |", da)
        self.assertIn("| models | coding | 1301 | 61% | $0.50/$1.00 |", da)

    def test_anchors_openrouter_rows_carry_accuracy_cost_and_latency(self):
        out, _, _, _ = self.run_cli("--anchors")
        orr = out[out.index("## OpenRouter evals"):out.index("no benchmark rows:")]
        # No latency in the feed row renders an em dash, like any missing number.
        self.assertIn("| gpqa_diamond | 62.0% | $0.0110 | — | — |", orr)
        self.assertIn("| math_agent | 90.0% | $0.0200 | 15000 | $0.50/$1.00 |", orr)

    def test_anchors_names_models_without_rows(self):
        out, _, _, _ = self.run_cli("--anchors")
        line = out[out.index("no benchmark rows:"):].splitlines()[0]
        self.assertIn("ghost/unknown-20260101", line)
        self.assertIn("stale/model", line)
        self.assertIn("gone/hinted", line)
        self.assertNotIn("deepseek/deepseek-v4-flash", line)

    def test_anchors_makes_one_unfiltered_authenticated_fetch(self):
        _, _, _, calls = self.run_cli("--anchors")
        bench = [c for c in calls if c[1] == "benchmarks.json"]
        self.assertEqual(len(bench), 1)
        self.assertEqual(bench[0][0], modelbandit.BENCHMARKS_URL)
        self.assertTrue(bench[0][2])   # authenticated

    def test_anchors_writes_nothing_to_the_policy(self):
        before = open(self.policy_path).read()
        self.run_cli("--anchors")
        self.assertEqual(open(self.policy_path).read(), before)

    def test_anchors_works_from_cache_without_a_key(self):
        # Deliberate seam widening beyond the spec's mocked-fetch decision:
        # these two tests drive the real fetch_json offline (patched cache
        # dir + api key, no network) to pin the cache-before-key ordering.
        # A fresh cached feed must render with no key at all: the real
        # fetch path returns the cache before consulting api_key.
        world = build_world()
        cache = os.path.join(self._tmp.name, "cache")
        os.makedirs(cache)
        with open(os.path.join(cache, "benchmarks.json"), "w") as f:
            json.dump(world["benchmarks"], f)
        with mock.patch.object(modelbandit, "CACHE_DIR", cache), \
                mock.patch.object(modelbandit, "api_key", return_value=None):
            out, _, code, _ = self.run_cli("--anchors", real_benchmarks=True)
        self.assertIsNone(code)
        self.assertIn("# Benchmark anchors", out)
        self.assertIn("| 55.1 | 48.0 | 41.3 | $0.50/$1.00 |", out)

    def test_anchors_keyless_without_cache_surfaces_the_fetch_error(self):
        # Same deliberate seam widening as above: real fetch_json, offline
        # (patched cache dir + api key, no network).
        cache = os.path.join(self._tmp.name, "empty-cache")
        os.makedirs(cache)
        with mock.patch.object(modelbandit, "CACHE_DIR", cache), \
                mock.patch.object(modelbandit, "api_key", return_value=None):
            _, _, code, _ = self.run_cli("--anchors", real_benchmarks=True)
        self.assertIn("OpenRouter Data API needs a key", code)

    # --- preference-tilted deal -----------------------------------------

    def test_deal_admits_favored_and_deals_all_tickets(self):
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "12",
                                       "--deal", "--seed", "proj")
        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("eligibility stays popularity", block)
        # rank 3 on the board, admitted because the user favors it (pref 3.0)
        self.assertIn("deepseek/deepseek-v4-flash", block)
        self.assertIn("| 3.0 |", block)
        rows = [ln for ln in block.splitlines()
                if ln.startswith("| ") and ln.split("|")[1].strip().isdigit()]
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(int(ln.split("|")[7].strip()) for ln in rows), 12)
        self.assertIn("projection at 12 ticket(s)", out)

    def test_deal_reports_free_share_by_serving_route(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/other"]},
                              alpha=1.0, beta=1.0)
        world = self.free_world(("vendor/model:free", 1.0))
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 1.0,
            "models": [{"id": "vendor/model:free", "tag_usage_share": 1.0}],
        }]

        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "12",
                                       "--deal", "--seed", "proj", world=world)

        self.assertIsNone(code)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("vendor/model:free", deal)
        self.assertIn("free share: 12/12 tickets (100%)", deal)

    def test_deal_base_uses_the_same_risk_price_as_the_ranked_table(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]},
                              alpha=1.0, beta=1.0)
        world = self.free_world(("vendor/model:free", 0.5))

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "risk-path", world=world)

        self.assertIsNone(code)
        table_row = next(line for line in out.splitlines()
                         if line.startswith("|") and "vendor/model:free |" in line)
        deal_block = out[out.index("deal (seed"):out.index("projection at")]
        deal_row = next(line for line in deal_block.splitlines()
                        if line.startswith("|") and "vendor/model:free |" in line)
        self.assertEqual(table_row.split("|")[4].strip(),
                         deal_row.split("|")[4].strip())

    def test_deal_is_deterministic_per_seed(self):
        args = ("--domain", "writing", "--tickets", "12", "--deal")
        out1 = self.run_cli(*args, "--seed", "proj")[0]
        out2 = self.run_cli(*args, "--seed", "proj")[0]
        self.assertEqual(out1[out1.index("deal (seed"):],
                         out2[out2.index("deal (seed"):])

    def test_deal_below_cut_favorite_scores_at_score_scale(self):
        # --top 2 prices two rows; the deal still plays v4-flash, admitted
        # below the cut on the user's favor. Its base is its fit-adjusted task
        # score — 0.005 share / $0.01456 = 0.34 — never its 0.5% share.
        # Hand-computed (alpha=1, beta=1, blend 0.6, pref 3.0, floor $0.00772):
        #   score 0813 0.06/0.0984 = 0.6098, v4-pro 0.025/0.00772 = 3.2383,
        #   v4-flash 0.005/0.01456 = 0.3434; prefs 1, 1, 3
        #   draw flash = 0.4*(0.3434/4.1915) + 0.6*(3/5) = 39.28%
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.run_cli("--domain", "writing", "--top", "2",
                                       "--tickets", "12", "--deal",
                                       "--seed", "proj")
        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        flash = next(ln for ln in block.splitlines() if "v4-flash" in ln)
        cols = [c.strip() for c in flash.split("|")]
        self.assertEqual(cols[4], "0.34")     # score, not the 0.01 share
        self.assertEqual(cols[6], "39.28%")   # draw from score + preference
        self.assertEqual(sum(int(ln.split("|")[7].strip())
                             for ln in block.splitlines()
                             if ln.startswith("| ")
                             and ln.split("|")[1].strip().isdigit()), 12)

    def test_plan_pick_and_deal_report_the_draw_against_fixture_caps(self):
        plan = "opencode-go/plan-model"
        policy = json.loads(json.dumps(POLICY))
        policy["baseline"] = {"id": "z-ai/glm-5.3"}
        policy["plans"] = {
            plan: {
                "list_price": 0.5,
                "caps": {"five_hour": 2.5, "weekly": 5.0,
                         "monthly": 10.0},
                "exposure": "no-retention",
                "family_ref": "deepseek/deepseek-v4-pro",
            },
        }
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        world = {
            "models": [make_model("z-ai/glm-5.3", "0.0000002",
                                   "0.000001", "0")],
            "classifications": {"as_of": "2026-10-17", "classifications": [
                {"tag": "content_writing", "usage_share": 1.0,
                 "models": [{"id": plan, "tag_usage_share": 1.0}]},
            ]},
            "rankings": {"data": []},
            "endpoints": {},
            "benchmarks": {"data": []},
        }

        out, err, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "allowance-readout", world=world)

        self.assertIsNone(code, err)
        self.assertIn("default pick (top of task order): "
                      f"{plan} ($0.0000/ticket; Draw $0.50/ticket)", out)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("allowance draw: opencode-go/plan-model $2.50 of $10.00 "
                      "(25.0% of monthly; 100.0% of 5h)", block)
        self.assertEqual(block.count("allowance draw:"), 1)
        self.assertIn("projection at 12 ticket(s): $0.00", out)

    def test_deal_emits_provider_qualified_ids(self):
        # Every dealt row id is the provider-qualified form a model config
        # consumes: `openrouter/` re-added to the normalized OpenRouter slug
        # (issue #63). Namespaced ids are already qualified.
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "12",
                                       "--deal", "--seed", "proj")
        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("openrouter/deepseek/deepseek-v4-pro", block)
        self.assertIn("openrouter/deepseek/deepseek-v4-flash", block)
        self.assertNotIn("| deepseek/deepseek-v4-pro ", block)
        self.assertNotIn("| deepseek/deepseek-v4-flash ", block)

    def test_deal_prints_the_plan_share_line_unconditionally(self):
        # The market mix is always visible: the plan share line joins the
        # free share line even when no plan tickets drew (issue #63).
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "12",
                                       "--deal", "--seed", "proj")
        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("free share: 0/12 tickets (0%)", block)
        self.assertIn("plan share: 0/12 tickets (0%)", block)

    def test_deal_plan_share_counts_only_plan_tickets(self):
        # The plan row takes the whole draw within its Allowance: the readout
        # names the plan tickets against the total dealt (issue #63).
        plan = "opencode-go/plan-model"
        policy = json.loads(json.dumps(POLICY))
        policy["baseline"] = {"id": "z-ai/glm-5.3"}
        policy["plans"] = {
            plan: {
                "list_price": 0.5,
                "caps": {"five_hour": 6.0, "weekly": 12.0,
                         "monthly": 12.0},
                "exposure": "no-retention",
                "family_ref": "deepseek/deepseek-v4-pro",
            },
        }
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        world = {
            "models": [make_model("z-ai/glm-5.3", "0.0000002",
                                   "0.000001", "0")],
            "classifications": {"as_of": "2026-10-17", "classifications": [
                {"tag": "content_writing", "usage_share": 1.0,
                 "models": [{"id": plan, "tag_usage_share": 1.0}]},
            ]},
            "rankings": {"data": []},
            "endpoints": {},
            "benchmarks": {"data": []},
        }

        out, err, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "allowance-readout", world=world)

        self.assertIsNone(code, err)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("plan share: 12/12 tickets (100%)", block)
        self.assertIn("free share: 0/12 tickets (0%)", block)

    # --- Sensitive shape: the admission seam in the output --------------

    def sensitive_policy(self, exposure):
        pol = json.loads(json.dumps(POLICY))
        pol["exposure"] = exposure
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

    def test_sensitive_marks_the_exposed_row_and_keeps_it_visible(self):
        # ADR 0008: every non-local Exposure is marked with its reason on a
        # Sensitive shape — `trains` and `no-retention` alike — the rows
        # stay visible, and with no local candidate the run stops blocked.
        self.sensitive_policy({"deepseek/deepseek-v4-flash": "trains"})
        out, _, code, _ = self.run_cli("--domain", "writing", "--sensitive")
        self.assertEqual(code, 0)
        self.assertIn("| admit |", out)
        row = next(ln for ln in out.splitlines()
                   if "deepseek/deepseek-v4-flash |" in ln)
        self.assertIn("exposed (trains)", row)      # visible with a reason
        other = next(ln for ln in out.splitlines()
                     if "deepseek/deepseek-v4-pro |" in ln)
        self.assertIn("exposed (no-retention)", other)
        self.assertIn("blocked: no eligible local candidate", out)

    def test_sensitive_pick_shuns_the_exposed_top_row(self):
        # v4-pro tops the cloud rows at alpha .7 / beta 1, but exposure
        # excludes it: with an eligible local candidate in the run the pick
        # is the local row — the exposed top row is marked in the table,
        # never picked — and the same run without the flag picks the top
        # row, as today.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=0.7, beta=1.0)
        pol["exposure"] = {"deepseek/deepseek-v4-pro": "trains"}
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})
        self.assertIsNone(code)
        top_row = next(ln for ln in out.splitlines()
                        if "deepseek/deepseek-v4-pro |" in ln)
        self.assertIn("exposed (trains)", top_row)
        self.assertIn(f"default pick (top of task order): {mid}", out)
        self.assertNotIn("default pick (top of task order): "
                         "openrouter/deepseek/deepseek-v4-pro", out)
        # the same run without the flag picks the top row, as today
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("default pick (top of task order): "
                      "openrouter/deepseek/deepseek-v4-pro", out)

    def test_ordinary_shape_prints_no_admission_column(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertNotIn("| admit |", out)
        self.assertNotIn("exposed", out)

    def test_context_exclusion_is_visible_on_an_ordinary_shape(self):
        world = build_world()
        free_model = make_model("nvidia/nemotron:free", "0.000001",
                                "0.000001", "0.000001")
        free_model["context_length"] = 65_536
        world["models"].append(free_model)
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "nvidia/nemotron:free", "tag_usage_share": 0.25})

        out, _, code, _ = self.run_cli("--domain", "writing", world=world)

        self.assertIsNone(code)
        self.assertIn("| admit |", out)
        row = next(ln for ln in out.splitlines()
                   if "nvidia/nemotron:free |" in ln)
        self.assertIn("context", row)

    def test_paid_candidate_over_completion_cap_is_flagged_but_kept(self):
        world = build_world()
        for endpoint in world["endpoints"]["deepseek/deepseek-v4-pro-0813"]:
            endpoint["max_completion_tokens"] = 16_000

        out, _, code, _ = self.run_cli("--domain", "writing", "--effort",
                                       "thorough", "--out-tokens", "12_000",
                                       world=world)

        self.assertIsNone(code)
        self.assertIn("| admit |", out)
        row = next(ln for ln in out.splitlines()
                   if "deepseek/deepseek-v4-pro-0813 |" in ln)
        self.assertIn("over completion cap", row)
        self.assertIn("default pick (top of task order):", out)

    def test_paid_candidate_over_window_is_flagged_but_kept(self):
        world = build_world()
        target = next(model for model in world["models"]
                      if model["id"] == "deepseek/deepseek-v4-pro-0813")
        target["context_length"] = 65_536

        out, _, code, _ = self.run_cli("--domain", "writing", "--in-tokens",
                                       "40_000", world=world)

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if "deepseek/deepseek-v4-pro-0813 |" in ln)
        self.assertIn("over window", row)
        self.assertNotIn("over completion cap", row)
        self.assertIn("default pick (top of task order):", out)

    def test_free_candidate_over_catalog_completion_cap_is_excluded_from_deal(self):
        policy = json.loads(json.dumps(POLICY))
        policy["free_models"] = {"vendor/model": {
            "context_length": 262_144, "max_completion_tokens": 16_000,
            "exposure": "no-retention",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        world = build_world()
        world["models"].append(make_model("vendor/model:free", "0", "0", "0"))
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "vendor/model:free", "tag_usage_share": 0.25})

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--effort", "thorough", "--deal",
            "--tickets", "8", world=world)

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if "vendor/model:free |" in ln)
        self.assertIn("over completion cap", row)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertNotIn("vendor/model:free", deal)

    def test_sensitive_deal_never_draws_an_exposed_candidate(self):
        # The exposed candidate stays out of the deal even when it is the
        # only free cloud route left: the eligible local candidate takes
        # every ticket (ADR 0008).
        pol = json.loads(json.dumps(POLICY))
        pol["exposure"] = {"deepseek/deepseek-v4-flash": "trains"}
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12",
            "--deal", "--seed", "proj", "--sensitive",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertNotIn("deepseek/deepseek-v4-flash", block)
        self.assertIn(f"| {mid} |", block)
        self.assertEqual(sum(int(ln.split("|")[7].strip())
                             for ln in block.splitlines()
                             if ln.startswith("| ")
                             and ln.split("|")[1].strip().isdigit()), 12)

    def test_sensitive_shape_with_no_admitted_candidate_stops_with_zero(self):
        # ADR 0008: no eligible local candidate is the Sensitive run's own
        # stop — the blocked report on stdout, status 0 (US13) — replacing
        # the generic all-excluded answer on stderr.
        self.sensitive_policy({"deepseek/": "trains"})
        out, err, code, _ = self.run_cli("--domain", "writing", "--sensitive")
        self.assertEqual(code, 0)
        self.assertIn("blocked: no eligible local candidate", out)
        self.assertNotIn("no candidate admitted", err)

    # --- Sensitive is local-only (ADR 0008) ------------------------------

    def sensitive_local_policy(self, exposure=None):
        """The fixture machine's policy carrying one harness-listed local
        candidate (no roster: the band gate has nothing to judge), plus an
        optional exposure override for the cloud rows."""
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        if exposure:
            pol["exposure"] = exposure
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        return "lmstudio/qwen/qwen3-coder-30b"

    def test_sensitive_admits_only_local_and_marks_every_non_local_row(self):
        # ADR 0008: a Sensitive shape (material) admits only Exposure
        # `local` — no-retention leaves the machine like trains does, so it
        # is excluded alike, marked with its reason in the table and never
        # hidden. The pick and the deal take the local candidate alone: the
        # invariant pinned at the output seam.
        mid = self.sensitive_local_policy(
            {"deepseek/deepseek-v4-flash": "trains"})

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--deal", "--seed",
            "local-only", local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertIn("| admit |", out)
        flash = next(ln for ln in out.splitlines()
                     if "deepseek/deepseek-v4-flash |" in ln)
        self.assertIn("exposed (trains)", flash)
        for cloud in ("deepseek/deepseek-v4-pro |",
                      "deepseek/deepseek-v4-pro-0813 |"):
            row = next(ln for ln in out.splitlines() if cloud in ln)
            self.assertIn("exposed (no-retention)", row)
        local_row = next(ln for ln in out.splitlines() if f"{mid} |" in ln)
        self.assertNotIn("exposed (", local_row)
        self.assertIn(f"default pick (top of task order): {mid}", out)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn(f"| {mid} |", deal)
        self.assertNotIn("deepseek/", deal)      # never a cloud row

    def test_sensitive_with_no_eligible_local_candidate_blocks_and_stops(self):
        # Deal-time emptiness is a report, never a re-gate (US13): the run
        # stops with the blocked line on stdout and exits 0 like every
        # other verdict — in pick mode and deal mode alike.
        for extra in ((), ("--deal", "--seed", "blocked")):
            with self.subTest(extra=extra):
                out, err, code, _ = self.run_cli(
                    "--domain", "writing", "--sensitive", *extra)

                self.assertEqual(code, 0)
                self.assertIn("blocked: no eligible local candidate", out)
                self.assertNotIn("no candidate admitted", err)
                self.assertNotIn("deal (seed", out)

    def test_a_sensitive_deal_carries_the_standing_non_leak_note(self):
        # The note is a contract marker for the harness to apply at prompt
        # time — prompt authoring itself stays with the harness (US14);
        # an ordinary deal prints no such note.
        mid = self.sensitive_local_policy()

        sensitive, _, _, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--deal", "--seed", "note",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})
        ordinary, _, _, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "note",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        note = next(ln for ln in sensitive.splitlines()
                    if ln.startswith("non-leak note:"))
        self.assertIn("contract marker", note)
        self.assertLess(sensitive.index("non-leak note:"),
                        sensitive.index("projection at"))
        self.assertNotIn("non-leak note:", ordinary)

    def test_missing_scoring_block_exits_with_key(self):
        pol = json.loads(json.dumps(POLICY))
        del pol["scoring"]
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        _, err, code, calls = self.run_cli("--domain", "writing")
        # Rules/config error, status 4 — not the raw SystemExit payload,
        # which a shell would report as 1 (the generic failure code).
        self.assertEqual(code, 4)
        self.assertIn("scoring", err)
        self.assertEqual(calls, [])

    def test_score_orders_by_popularity_priced_at_cost(self):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=0.7, beta=1.0)
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, _, _ = self.run_cli("--domain", "writing")
        body = out[out.index("| # |") :]
        # v4-pro is ~13x cheaper per ticket than the share leader -> tops the order
        self.assertIn("default pick (top of task order): openrouter/deepseek/deepseek-v4-pro\n", out)
        self.assertLess(body.index("deepseek/deepseek-v4-pro |"),
                        body.index("deepseek/deepseek-v4-pro-0813 |"))

    def test_fit_composes_and_reorders(self):
        out, _, _, _ = self.run_cli("--domain", "writing",
                                    "--fit", "deepseek/deepseek-v4-pro-0813=0")
        self.assertIn("default pick (top of task order): openrouter/deepseek/deepseek-v4-pro\n", out)
        self.assertIn("| fit | adj |", out)

    def test_score_balance_section_and_retune_verdict(self):
        pol = json.loads(json.dumps(POLICY))
        pol["affinity"]["eligibility_top_k"] = 5  # 3 selectable writers -> judged
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, _, _ = self.run_cli("--check-policy")
        block = out[out.index("## Score balance"):]
        self.assertIn("writing:", block)
        self.assertIn("OUT OF BALANCE", block)  # fixture shares are top-heavy
        self.assertIn("coefficient re-tune due: yes", out)

    def test_every_required_policy_key_fails_loudly_when_missing(self):
        cases = [("scoring", "alpha"), ("scoring", "beta"),
                 ("scoring.thresholds", "top1_min"),
                 ("scoring.thresholds", "top1_max"),
                 ("scoring.thresholds", "top2_max"),
                 ("affinity.factors", "favor_validated"),
                 ("affinity.factors", "favor_suspected"),
                 ("affinity.factors", "avoid_validated"),
                 ("affinity.factors", "avoid_suspected"),
                 ("affinity", "blend_weight"),
                 ("affinity", "eligibility_top_k")]
        for path, key in cases:
            pol = json.loads(json.dumps(POLICY))
            node = pol
            for part in path.split("."):
                node = node[part]
            del node[key]
            with open(self.policy_path, "w") as f:
                json.dump(pol, f)
            _, err, code, _ = self.run_cli("--domain", "writing")
            # Loudly = named on stderr with status 4; the raw payload
            # would exit 1 in a shell, the generic failure code.
            self.assertEqual(code, 4)
            self.assertIn(f"{path}.{key}", err)

    def test_missing_domain_exits(self):
        # Usage error, status 2 - argparse's own channel; a bare string
        # SystemExit would exit 1 in a shell (the generic-failure code).
        _, err, code, _ = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("need --domain", err)

    def test_unknown_domain_exits(self):
        _, err, code, _ = self.run_cli("--domain", "nope")
        self.assertEqual(code, 2)
        self.assertIn("no domain", err)

    def test_missing_policy_file_exits(self):
        out, err, code, _ = None, None, None, None
        argv = ["modelbandit", "--policy", "/nonexistent/policy.json",
                "--domain", "writing"]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit):
                modelbandit.main()

    def test_profile_defaults_per_domain(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("profile=authoring (in=20,000 out=12,000 cached=40%)", out)
        out, _, _, _ = self.run_cli("--domain", "coding")
        self.assertIn("profile=agentic (in=40,000 out=4,000 cached=75%)", out)

    def test_missing_tag_warns_on_stderr(self):
        _, err, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("gone_tag", err)

    # --- ranking and resolution -----------------------------------------

    def test_rows_ranked_by_traffic_share(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        body = out[out.index("| # |"):]
        i_aug = body.index("deepseek/deepseek-v4-pro-0813")
        i_apr = body.index("| deepseek/deepseek-v4-pro |")
        i_ghost = body.index("ghost/unknown-20260101")
        self.assertTrue(i_aug < i_apr < i_ghost)

    def test_cataloged_opencode_candidate_shows_window_and_exposure(self):
        policy = json.loads(json.dumps(POLICY))
        policy["free_models"] = {
            "opencode/flash": {"context_length": 262144,
                               "exposure": "no-retention",
                               "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        out, _, code, _ = self.run_cli("--domain", "writing")
        self.assertIsNone(code)
        self.assertIn("opencode/flash", out)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and "opencode/flash" in line)
        self.assertIn("256K | no-retention |", row)
        self.assertIn("opencode/flash: eol summary", out)

    def test_served_cataloged_local_candidate_uses_local_exposure_and_window(self):
        policy = json.loads(json.dumps(POLICY))
        policy["free_models"] = {
            "lmstudio/qwen/qwen3-coder": {"context_length": 65_536,
                                          "exposure": "local",
                                          "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"
        served = {mid: {"id": mid, "context_length": 32_768}}

        out, _, code, calls = self.run_cli(
            "--domain", "writing", local_models=served)

        self.assertIsNone(code)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and mid in line)
        self.assertIn("64K | local |", row)
        self.assertIn(f"{mid}: eol summary", out)
        self.assertFalse(any(url.endswith("/endpoints") and mid in url
                             for url, *_ in calls))
        self.assertFalse(any(url.endswith("/endpoints")
                             and "qwen/qwen3-coder" in url for url, *_ in calls))

    def test_served_local_candidate_without_summary_is_visible_but_not_admitted(self):
        policy = json.loads(json.dumps(POLICY))
        policy["free_models"] = {
            "lmstudio/local/qwen": {"context_length": 262_144, "exposure": "local"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        mid = "lmstudio/local/qwen-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_models={mid: {"id": mid}})

        self.assertIsNone(code)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and mid in line)
        self.assertIn("local |", row)
        self.assertIn("free route requires a catalog entry and summary", row)

    def test_absent_local_server_keeps_cli_output_and_stderr_unchanged(self):
        baseline = self.run_cli("--domain", "writing")
        def connection_refused(_url):
            raise OSError("connection refused")

        # The probe absorbs the unavailable-server result; main receives the
        # same empty per-run catalog it had before the probe existed.
        absent_models = modelbandit.probe_local_models(connection_refused)
        absent = self.run_cli("--domain", "writing",
                              local_models=absent_models)

        self.assertEqual(absent, baseline)

    # --- harness listing: local existence and identity --------------------

    def test_check_policy_cannot_judge_local_models_without_a_listing(self):
        # The flag omitted means the harness never spoke: the report says
        # so rather than claiming every rostered model is unrunnable.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"lmstudio/dead/model": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        out, _, code, _ = self.run_cli("--check-policy", listing_absent=True)

        self.assertIsNone(code)
        section = out[out.index("## Local models the harness cannot run"):
                      out.index("## Free-share trends")]
        self.assertIn("not provided", section)

    def test_check_policy_reports_local_models_the_harness_cannot_run(self):
        # A local entry ahead of the harness: named by the policy check,
        # and never dealt — the listing is the only existence there is, so
        # the same fixture's ranking run carries no row for it while the
        # entry the harness does run stays.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {
            "lmstudio/dead/model": {
                "context_length": 262_144, "exposure": "local",
                "summary_ref": "deepseek/deepseek-v4-pro"},
            "lmstudio/live/model": {
                "context_length": 262_144, "exposure": "local",
                "summary_ref": "deepseek/deepseek-v4-pro"},
        }
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        live = "lmstudio/live/model"
        listing = {live}

        checked, _, code, _ = self.run_cli(
            "--check-policy", local_listing=listing,
            local_models={live: {"id": live, "context_length": 262_144}})
        ranked, _, r_code, _ = self.run_cli(
            "--domain", "writing", local_listing=listing,
            local_models={live: {"id": live, "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertIsNone(r_code)
        section = checked[checked.index("## Local models the harness cannot run"):
                          checked.index("## Free-share trends")]
        self.assertIn("lmstudio/dead/model", section)
        self.assertIn("never dealt", section)
        self.assertNotIn(live, section)
        self.assertNotIn("lmstudio/dead/model", ranked)
        self.assertIn(f"{live} |", ranked)

    def test_a_local_entry_the_harness_cannot_run_is_never_dealt(self):
        # Deal-shaped run of the same rule: no listing match, no row, no
        # pick, no deal — reported, never dealt.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"lmstudio/dead/model": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        other = "lmstudio/other/model"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "stranded",
            local_listing={other},
            local_models={other: {"id": other, "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertNotIn("lmstudio/dead/model", out)

    def test_a_harness_listed_local_candidate_is_dealt_as_the_harness_dispatches_it(self):
        # The listing the harness passes in is the candidate's existence and
        # identity: the row, the pick and the deal all name the id verbatim,
        # provider-qualified — never re-prefixed with `openrouter/`, exactly
        # what the harness dispatches.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "listing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("256K | local |", row)
        self.assertIn(f"default pick (top of task order): {mid}", out)
        deal_block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn(f"| {mid} |", deal_block)

    def test_local_rows_are_absent_without_a_harness_listing(self):
        # No flag means the harness never spoke: the run cannot invent local
        # candidates from the probe alone, whatever the catalog declares.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 65_536, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", listing_absent=True,
            local_models={mid: {"id": mid, "context_length": 65_536}})

        self.assertIsNone(code)
        # Neither the probe's ids nor the catalog's own prefix may stand up
        # a local row: no listing, no local existence at all.
        self.assertNotIn("lmstudio", out)

    def listed_local_policy(self, window=262_144):
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": window, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        return "lmstudio/qwen/qwen3-coder-30b"

    def test_the_probed_window_backs_the_context_gate(self):
        # The probe's one narrow fact: the window the live serving reports
        # is what the Context gate judges. The curated 256K cannot rescue a
        # candidate whose serving states an 8K window — the row is excluded
        # with the gate's named reason, not picked.
        mid = self.listed_local_policy()

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 8_192}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("over window", row)
        self.assertIn("4,096 tokens", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", out)

    def test_the_probed_window_can_widen_admission_to_the_live_capacity(self):
        # The other direction of the same fact: a serving that reports a
        # wider window than the curated one admits the shape the live
        # capacity can actually take.
        mid = self.listed_local_policy(window=8_192)

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertNotIn("over window", row)

    # --- Local roster: the binding Capability band ------------------------

    def test_the_band_excludes_a_local_candidate_with_a_named_reason(self):
        # The roster's Capability band is binding: a ticket domain outside
        # the band is hard-excluded at admission with the band's own named
        # reason — visible in the admit column, never picked.
        mid = self.listed_local_policy()
        self.roster_file({mid: {
            "band": {"domains": ["coding"], "difficulty": "measured",
                     "context_demand": 65_536},
            "prose": "Serviceable prose, weak for writing."}})

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("outside band", row)
        self.assertIn("domain 'writing'", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", out)

    def test_the_difficulty_ceiling_excludes_only_above_the_rung(self):
        # The band's difficulty is a ceiling on the effort rung: a ticket
        # at or below the ceiling admits (the ceiling costs no reach),
        # a rung above it is excluded with the named reason.
        mid = self.listed_local_policy()
        self.roster_file({mid: {
            "band": {"domains": ["writing"], "difficulty": "measured",
                     "context_demand": 65_536},
            "prose": "Fine for measured writing, not for deep runs."}})

        at_ceiling, _, code, _ = self.run_cli(
            "--domain", "writing", "--effort", "measured",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})
        over_ceiling, _, o_code, _ = self.run_cli(
            "--domain", "writing", "--effort", "thorough",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertIsNone(o_code)
        admitted_row = next(ln for ln in at_ceiling.splitlines()
                            if ln.startswith("|") and f"{mid} |" in ln)
        self.assertNotIn("over difficulty ceiling", admitted_row)
        excluded_row = next(ln for ln in over_ceiling.splitlines()
                            if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("over difficulty ceiling", excluded_row)
        self.assertIn("thorough > measured", excluded_row)
        self.assertNotIn(f"default pick (top of task order): {mid}",
                         over_ceiling)

    def test_the_context_demand_ceiling_is_enforced_from_the_footprint(self):
        # The band ceiling is judged against the shape's Footprint (input x
        # growth headroom from the token profile) — never against the
        # window: the serving reports 256K, the footprint of an authoring
        # ticket (20,000 x 2.0 = 40,000) is over the roster's 8K ceiling,
        # and the exclusion says so in the band's own terms.
        mid = self.listed_local_policy()
        self.roster_file({mid: {
            "band": {"domains": ["writing"], "difficulty": "exhaustive",
                     "context_demand": 8_192},
            "prose": "Small-context model; short tickets only."}})

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("context-demand ceiling 8,192", row)
        self.assertNotIn("over window", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", out)

    def test_the_probed_window_still_backs_the_context_gate_with_a_roster(self):
        # A generous band does not stand in for capacity: the roster's
        # ceiling passes (footprint under 1M), but the serving reports an
        # 8K window and the Context gate still excludes it — the probed
        # window remains the Context gate's own number.
        mid = self.listed_local_policy()
        self.roster_file({mid: {
            "band": {"domains": ["writing"], "difficulty": "exhaustive",
                     "context_demand": 1_048_576},
            "prose": "Enormous appetite, whatever the serving reports."}})

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 8_192}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("over window", row)
        self.assertNotIn("context-demand ceiling", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", out)

    def band_entry(self, domains, prose):
        return {"band": {"domains": domains, "difficulty": "measured",
                         "context_demand": 65_536},
                "prose": prose}

    def test_one_admission_verdict_serves_both_the_table_and_the_deal(self):
        # The band's verdict is the admission decision itself: the table
        # marks the excluded local row with the band's reason and the deal
        # draws from the admitted set — same fixture the deal previously
        # dealt, now rostered out, so the two surfaces cannot disagree.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"
        self.roster_file({mid: self.band_entry(
            ["coding"], "A coder, not a writer.")})

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "listing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("outside band", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", out)
        deal_block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertNotIn(f"| {mid} |", deal_block)

    def test_a_band_passing_rostered_candidate_keeps_both_surfaces_unchanged(self):
        # The other half of one verdict: a band the ticket fits costs
        # nothing — with the roster present and the band passing, the readout
        # is byte-identical to the run without one (understating a band
        # costs reach; a passing band costs nothing).
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"
        args = ("--domain", "writing", "--deal", "--seed", "listing")
        listing = {mid}
        models = {mid: {"id": mid, "context_length": 262_144}}

        unrostered = self.run_cli(*args, local_listing=listing,
                                  local_models=models)
        self.roster_file({mid: self.band_entry(
            ["writing", "coding"], "Does everything on this machine.")})
        rostered = self.run_cli(*args, local_listing=listing,
                                local_models=models)

        self.assertIsNone(unrostered[2])
        self.assertIsNone(rostered[2])
        self.assertEqual(unrostered, rostered)
        deal_block = rostered[0][rostered[0].index("deal (seed"):
                                 rostered[0].index("projection at")]
        self.assertIn(f"| {mid} |", deal_block)

    def test_check_policy_reports_rostered_models_the_harness_cannot_run(self):
        # The roster is the rostered source the section names: its keys
        # ahead of the harness listing land there — reported, never dealt —
        # while a roster key the harness actually runs stays out.
        mid = self.listed_local_policy()
        stranded = "lmstudio/qwen/bench-only-30b"
        self.roster_file({
            mid: self.band_entry(["writing", "coding"], "Servable today."),
            stranded: self.band_entry(["writing", "coding"],
                                      "Bench-only; not enabled in the harness."),
        })

        out, _, code, _ = self.run_cli(
            "--check-policy", local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        section = out[out.index("## Local models the harness cannot run"):
                      out.index("## Free-share trends")]
        self.assertIn(stranded, section)
        self.assertIn("not in the harness listing; never dealt", section)
        self.assertNotIn(mid, section)

    def test_check_policy_names_unconfirmed_roster_bands(self):
        # US8's second half: exporter-stamped `suspected` bands are visible
        # to the operator on the diagnostic surface — a count and the ids
        # only, never a prose dump — while admission stays untouched (a
        # suspected band binds exactly like a confirmed one, ADR-0009).
        mid = self.listed_local_policy()
        seeded = "lmstudio/qwen/bench-only-30b"
        stamp = {"source": "local-llm-bench", "dossier": "qwen", "evidence":
                 "suspected", "seeded": True, "date": "2026-11-15"}
        self.roster_file({
            mid: {**self.band_entry(["writing", "coding"], "Servable today."),
                  "provenance": dict(stamp, dossier="qwen")},
            seeded: {**self.band_entry(["writing"], "Seeded, unconfirmed."),
                     "provenance": dict(stamp, dossier="bench-only")},
        })

        out, _, code, _ = self.run_cli(
            "--check-policy", local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        section = out[out.index("## Roster bands awaiting confirmation"):
                      out.index("## Local models the harness cannot run")]
        self.assertIn("2 suspected", section)
        self.assertIn(mid, section)
        self.assertIn(seeded, section)
        # Ids and the count only: the roster's prose never rides along.
        self.assertNotIn("Servable", section)
        self.assertNotIn("unconfirmed.", section)

    def test_check_policy_says_none_when_every_band_is_confirmed(self):
        # The other half of the seam: a roster whose entries the exporter
        # never stamped (hand-authored, or edited to evidence validated)
        # reports zero unconfirmed bands rather than a section that reads
        # as if something were pending.
        mid = self.listed_local_policy()
        self.roster_file({
            mid: self.band_entry(["writing", "coding"], "Hand-confirmed."),
            **{"lmstudio/qwen/other-30b": {
                **self.band_entry(["writing"], "Edited after seeding."),
                "provenance": {"source": "local-llm-bench",
                               "evidence": "validated", "seeded": True,
                               "date": "2026-11-15"}}},
        })

        out, _, code, _ = self.run_cli(
            "--check-policy", local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        section = out[out.index("## Roster bands awaiting confirmation"):
                      out.index("## Local models the harness cannot run")]
        self.assertIn("- — none", section)
        self.assertNotIn("suspected", section)

    def test_a_malformed_roster_stops_the_run_with_status_4(self):
        # Loud validation reaches the CLI: a band the loader cannot trust
        # stops the run at the rules/config status with a message naming
        # the entry — on the ranking path and the policy check alike,
        # never a traceback and never a silently guessed band.
        mid = "lmstudio/qwen/qwen3-coder-30b"
        self.roster_file({mid: {
            "band": {"domains": ["writing"], "difficulty": "brutal",
                     "context_demand": 65_536},
            "prose": "Everything, allegedly."}})

        for argv in (["--domain", "writing"], ["--check-policy"]):
            with self.subTest(argv=argv):
                out, err, code, _ = self.run_cli(*argv)
                self.assertEqual(code, 4)
                self.assertIn(f"entries.{mid}.band.difficulty", err)
                self.assertIn("local roster", err)

    def test_a_never_deal_band_excludes_every_ticket(self):
        # The empty domain list is the valid never-deal band: the model
        # stays rostered (visible, reported) but admits no ticket — the
        # unusable-verdict seed the contract describes.
        mid = self.listed_local_policy()
        self.roster_file({mid: self.band_entry(
            [], "Bench verdict: unusable for agent work.")})

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("the band admits no domain", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", out)

    # --- Standing favor for band-passing locals + local share (issue #69) --

    def test_a_band_passing_local_row_carries_the_standing_favor(self):
        # The favor enters through the hint/affinity machinery: on a
        # qualifying shape (the deal holds an admitted local row) that
        # row's pref reads the affinity factors' validated favor (3.0),
        # while every cloud row keeps exactly the pref its own hint earns —
        # score, Nominal floor and paid-pool balance untouched. Hand-
        # computed (blend 0.6, bases = share at alpha 1 / beta 0:
        # 0.06/0.0425/0.005, prefs 1/3/3): draws 30.90% / 41.53% / 27.57%
        # — the favor tilts the seeded draw toward the local row without
        # deciding it, and the same seed replays the same deal.
        mid = self.listed_local_policy()
        self.roster_file({mid: self.band_entry(
            ["writing", "coding"], "Does everything on this machine.")})
        args = ("--domain", "writing", "--tickets", "12", "--deal",
                "--seed", "listing")
        models = {mid: {"id": mid, "context_length": 262_144}}

        out, _, code, _ = self.run_cli(*args, local_listing={mid},
                                       local_models=models)
        replay = self.run_cli(*args, local_listing={mid},
                              local_models=models)

        self.assertIsNone(code)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        rows = [ln for ln in deal.splitlines()
                if ln.startswith("| ") and ln.split("|")[1].strip().isdigit()]
        self.assertEqual(len(rows), 3)
        local_row = next(ln for ln in rows if mid in ln)
        self.assertEqual(local_row.split("|")[5].strip(), "3.0")
        self.assertEqual(local_row.split("|")[6].strip(), "41.53%")
        flash_row = next(ln for ln in rows if "deepseek-v4-flash" in ln)
        self.assertEqual(flash_row.split("|")[5].strip(), "3.0")  # its hint
        pro_row = next(ln for ln in rows if "deepseek-v4-pro-0813" in ln)
        self.assertEqual(pro_row.split("|")[5].strip(), "1.0")  # no hint
        self.assertEqual(pro_row.split("|")[6].strip(), "30.90%")
        self.assertEqual(flash_row.split("|")[6].strip(), "27.57%")
        # Exact seeded draw for seed 'listing': 3 / 3 / 6 tickets in pool
        # order (the local row lands three of the twelve).
        self.assertEqual([int(ln.split("|")[7].strip()) for ln in rows],
                         [3, 3, 6])
        # Deterministic in the seed: the same invocation replays the deal.
        again = replay[0]
        self.assertEqual(out[out.index("deal (seed"):],
                         again[again.index("deal (seed"):])

    def test_the_deal_prints_the_local_share_beside_free_and_plan(self):
        # The readout gains a third share line (issue #69): how much of the
        # deal stays on this machine, printed beside the free and plan
        # shares with the same `<label>: N/M tickets (P%)` shape — and the
        # line always prints, a run with no local row reading 0 rather
        # than vanishing (as the plan share already does).
        mid = self.listed_local_policy()
        self.roster_file({mid: self.band_entry(
            ["writing", "coding"], "Does everything on this machine.")})
        models = {mid: {"id": mid, "context_length": 262_144}}

        dealt, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "listing", local_listing={mid}, local_models=models)
        cloud, _, c_code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "listing", local_listing=set(), local_models={})

        self.assertIsNone(code)
        self.assertIsNone(c_code)
        block = dealt[dealt.index("deal (seed"):dealt.index("projection at")]
        lines = [ln for ln in block.splitlines() if " share:" in ln]
        self.assertEqual(lines, ["free share: 3/12 tickets (25%)",
                                 "plan share: 0/12 tickets (0%)",
                                 "local share: 3/12 tickets (25%)"])
        c_block = cloud[cloud.index("deal (seed"):cloud.index("projection at")]
        self.assertIn("local share: 0/12 tickets (0%)", c_block)

    def test_the_standing_favor_never_reaches_a_row_the_band_excluded(self):
        # The band ceilings are what make this "small tickets": a shape
        # outside the band loses its local row at admission, so there is
        # no admitted row to favor — the draw runs the cloud pool alone
        # and the local share reads zero. The favor rides the admit chain,
        # never bypasses it.
        mid = self.listed_local_policy()
        self.roster_file({mid: self.band_entry(
            ["coding"], "A coder, not a writer.")})

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "listing", local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("outside band", row)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertNotIn(f"| {mid} |", deal)
        self.assertIn("local share: 0/12 tickets (0%)", deal)

    def test_the_budget_json_run_carries_the_local_share(self):
        # The machine-readable half of the readout (issue #69): a dealt
        # budgeted run's verdict object carries the same figures the
        # printed `local share:` line shows — and a budgeted run without
        # --deal carries no share at all (no deal to count).
        mid = self.listed_local_policy()
        self.roster_file({mid: self.band_entry(
            ["writing", "coding"], "Does everything on this machine.")})
        models = {mid: {"id": mid, "context_length": 262_144}}
        args = ("--domain", "writing", "--tickets", "12", "--budget", "100",
                "--json", "--seed", "listing")

        out, _, code, _ = self.run_cli(*args, "--deal",
                                       local_listing={mid}, local_models=models)
        plain, _, p_code, _ = self.run_cli(*args,
                                           local_listing={mid},
                                           local_models=models)

        self.assertIsNone(code)
        self.assertIsNone(p_code)
        self.assertIn("local share: 3/12 tickets (25%)", out)
        payload = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(payload["local_share"],
                         {"tickets": 3, "dealt": 12, "percent": 25.0})
        self.assertEqual(json.loads(plain.strip().splitlines()[-1]).get(
            "local_share"), None)

    def test_probe_identity_never_reaches_the_readout(self):
        # The probe reports what serves; the listing says what exists. An id
        # the harness never listed is not adopted, however loudly the probe
        # names it — and the listed candidate still stands on the catalog's
        # own facts when the probe knows nothing about it.
        listed_mid = self.listed_local_policy()
        foreign_mid = "lmstudio/other/unlisted-model"

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_listing={listed_mid},
            local_models={foreign_mid: {"id": foreign_mid,
                                        "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertNotIn(foreign_mid, out)
        self.assertIn(f"{listed_mid} |", out)

    def test_the_budget_json_run_shares_the_table_with_local_candidates(self):
        # The deal/pick seam has two halves: this pins the machine-readable
        # verdict object beside the printed readout that carries the local
        # row — same run, both surfaces.
        mid = self.listed_local_policy()

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--budget", "100", "--json",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        payload = json.loads(out.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["over_budget"])
        self.assertIn(f"{mid} |", out)

    def test_a_missing_serving_stack_has_no_effect_on_output(self):
        # Listing present, server down: the candidates, their facts and the
        # whole readout are what a serving that reports its window would
        # have produced - the probe adds no identity and, when it has
        # nothing new to say, no difference.
        mid = self.listed_local_policy()

        down = self.run_cli("--domain", "writing",
                            local_listing={mid}, local_models={})
        serving = self.run_cli(
            "--domain", "writing",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIn(f"{mid} |", down[0])
        self.assertEqual(down, serving)

    LAN_ENDPOINT = "http://desktop-rme135a.tail409f29.ts.net:1234/v1"

    def test_a_non_loopback_serving_fails_closed_as_exposed(self):
        # `local` Exposure resolves only for loopback on this machine: a
        # LAN-served instance is exposed (`trains`, the unknown-free
        # default), so Sensitive excludes it with the named reason and the
        # pick never names it — nothing about it may masquerade as local.
        mid = self.listed_local_policy()

        plain, _, code, _ = self.run_cli(
            "--domain", "writing", serving_endpoint=self.LAN_ENDPOINT,
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})
        sensitive, _, s_code, _ = self.run_cli(
            "--domain", "writing", "--sensitive",
            serving_endpoint=self.LAN_ENDPOINT,
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertEqual(s_code, 0)   # blocked stop: nothing local may serve
        plain_row = next(ln for ln in plain.splitlines()
                         if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("256K | trains |", plain_row)
        sensitive_row = next(ln for ln in sensitive.splitlines()
                             if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("exposed (trains)", sensitive_row)
        self.assertNotIn(f"default pick (top of task order): {mid}", sensitive)
        self.assertIn("blocked: no eligible local candidate", sensitive)

    def test_one_loopback_fact_agrees_across_both_surfaces(self):
        # One serving fact, one answer, whichever surface asks (ADR-0003,
        # ADR-0008): with the serving off this machine, a Sensitive shape
        # resolves `local` Exposure nowhere. The ranking run marks the row
        # exposed and never serves it; --check-policy admits it into its
        # diagnostic deal neither — the free-share measurement record (the
        # one place that surface reports what its deal admitted) stays
        # unwritten, where the loopback control writes it. Both halves
        # matter: without the control the fixture could simply never have
        # measured.
        mid = self.listed_local_policy()
        models = {mid: {"id": mid, "context_length": 262_144}}
        history = os.path.join(self._tmp.name, "cache",
                               "free-share-history.json")
        if os.path.exists(history):
            os.remove(history)
        ranked, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive",
            serving_endpoint=self.LAN_ENDPOINT,
            local_listing={mid}, local_models=models)
        checked, _, check_code, _ = self.run_cli(
            "--check-policy", "--sensitive",
            serving_endpoint=self.LAN_ENDPOINT,
            local_listing={mid}, local_models=models)

        row = next(ln for ln in ranked.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("exposed (trains)", row)
        self.assertNotIn(f"default pick (top of task order): {mid}", ranked)
        self.assertEqual(code, 0)
        self.assertIsNone(check_code)
        self.assertFalse(
            os.path.exists(history),
            "check-policy measured a free share from a deal that "
            f"admitted a row the ranking run excludes:\n{checked}")

        self.run_cli("--check-policy", "--sensitive",
                     local_listing={mid}, local_models=models)
        self.assertTrue(os.path.exists(history),
                        "the loopback control never measured — the "
                        "fixture cannot tell the surfaces apart")

    def test_the_exposure_override_can_declare_a_non_loopback_local_serving(self):
        # The one escape hatch: the policy's exposure-override map declares
        # the serving local explicitly, and it is then judged local — the
        # operator's statement, not the catalogue's or the namespace's.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        pol["exposure"] = {"lmstudio/qwen": "local"}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"

        sensitive, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive",
            serving_endpoint=self.LAN_ENDPOINT,
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in sensitive.splitlines()
                   if ln.startswith("|") and f"{mid} |" in ln)
        self.assertIn("256K | local |", row)
        self.assertNotIn("exposed", row)

    def test_ranked_free_slug_is_not_replaced_by_paid_family(self):
        policy = json.loads(json.dumps(POLICY))
        policy["free_models"] = {
            "vendor/model": {"context_length": 65536,
                             "exposure": "trains",
                             "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        world = build_world()
        world["models"].append(make_model("vendor/model:free", "0", "0", "0",
                                           canonical="vendor/model"))
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "vendor/model:free", "tag_usage_share": 0.01})
        out, _, code, _ = self.run_cli("--domain", "writing", "--top", "1",
                                       world=world)
        self.assertIsNone(code)
        self.assertIn("| vendor/model:free |", out)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and "vendor/model:free" in line)
        self.assertIn("64K | trains |", row)
        self.assertNotIn("| vendor/model |", out)

    # --- Free risk: the Nominal floor is derived per priced pool ----------

    FREE_CATALOG = {
        "vendor/model": {"context_length": 262_144, "exposure": "no-retention",
                         "summary_ref": "deepseek/deepseek-v4-pro"},
        "vendor/other": {"context_length": 262_144, "exposure": "trains",
                         "summary_ref": "deepseek/deepseek-v4-pro"},
    }

    def free_risk_policy(self, free_models, alpha=1.0, beta=1.0, risk=0.35):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=alpha, beta=beta, free_risk=risk)
        pol["free_models"] = free_models
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

    def free_world(self, *shares, models=()):
        world = build_world()
        for mid, share in shares:
            world["models"].append(make_model(mid, "0", "0", "0"))
            world["classifications"]["classifications"][0]["models"].append(
                {"id": mid, "tag_usage_share": share})
        world["models"] += list(models)
        return world

    def test_free_route_uses_risk_price_for_score_and_pick(self):
        # The cheapest paid ticket is $0.00772, so default Free risk prices
        # this route at 35% × $0.00772 = $0.002702. Its 0.05 share scores 18.50.
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))
        out, _, code, _ = self.run_cli("--domain", "writing", world=world)
        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "vendor/model:free |" in ln)
        self.assertIn("| 18.50 |", row)
        self.assertIn("$0.0000", row)
        self.assertIn("default pick (top of task order): openrouter/vendor/model:free", out)
        pick_line = next(line for line in out.splitlines()
                         if line.startswith("default pick (top of task order):"))
        self.assertEqual(pick_line,
                         "default pick (top of task order): "
                         "openrouter/vendor/model:free")

    # --- free-use zones: main wires the posture into admission --------

    def zone_of(self, posture):
        """The fixture's own folder, declared closed or left open. A closed
        declaration is the bare path; `sensitive` was never a place."""
        return [self._tmp.name] if posture == "closed" else []

    def test_a_closed_zone_filters_remote_free_routes_at_source(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))

        open_run, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name, world=world)
        self.assertIsNone(code)
        self.assertNotIn("| admit |", open_run)
        self.assertIn("default pick (top of task order): openrouter/vendor/model:free",
                      open_run)

        closed, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("closed"))
        # ADR 0008: with no eligible local candidate the closed run stops
        # blocked (exit 0) — and the source filter still removed the remote
        # free route before the table was built.
        self.assertEqual(code, 0)
        self.assertNotIn("vendor/model:free", closed)
        self.assertIn("| admit |", closed)   # the non-local rows are marked
        self.assertIn(f"zone: {self._tmp.name} (closed)", closed)
        self.assertIn("blocked: no eligible local candidate", closed)

    def test_a_closed_zone_keeps_remote_free_out_of_the_deal(self):
        # The deal still runs in a closed zone once an eligible local
        # candidate serves it (ADR 0008), and the source filter keeps the
        # remote free route out of the whole output.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0, free_risk=0.35)
        pol["free_models"] = {
            "vendor/model": self.FREE_CATALOG["vendor/model"],
            "lmstudio/qwen": {"context_length": 262_144,
                              "exposure": "local",
                              "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"
        world = self.free_world(("vendor/model:free", 1.0))
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 1.0,
            "models": [{"id": "vendor/model:free", "tag_usage_share": 1.0},
                       {"id": "deepseek/deepseek-v4-pro-20260813",
                        "tag_usage_share": 0.5}],
        }]

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal", "--seed", "proj",
            "--working-dir", self._tmp.name, world=world,
            zones=self.zone_of("closed"),
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        self.assertNotIn("vendor/model:free", out)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn(f"| {mid} |", deal)
        self.assertEqual(sum(int(ln.split("|")[7].strip())
                             for ln in deal.splitlines()
                             if ln.startswith("| ")
                             and ln.split("|")[1].strip().isdigit()), 12)

    def test_a_closed_zone_still_admits_a_locally_served_model(self):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0, free_risk=0.35)
        pol["free_models"] = {"lmstudio/qwen/qwen3-coder": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "lmstudio/qwen/qwen3-coder-30b", "tag_usage_share": 0.5})
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("closed"),
            local_models={mid: {"id": mid}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "qwen/qwen3-coder-30b |" in ln)
        self.assertNotIn("remote free route is prohibited", row)
        self.assertIn(f"default pick (top of task order): {mid}",
                      out)

    def test_the_sensitive_flag_cannot_loosen_a_closed_zone(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/other"]})
        world = self.free_world(("vendor/model:free", 0.5))

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--working-dir",
            self._tmp.name, world=world, zones=self.zone_of("closed"))

        # Still closed, not merely sensitive: the remote free route is
        # absent at source, and with no eligible local candidate the run
        # stops blocked (exit 0).
        self.assertEqual(code, 0)
        self.assertNotIn("vendor/model:free", out)
        self.assertNotIn("default pick (top of task order): vendor/model:free",
                         out)
        self.assertIn("blocked: no eligible local candidate", out)

    def test_a_sensitive_zone_triggers_local_only_like_the_flag(self):
        # Place and material are separate facts now (ADR-0010): a closed
        # place drops remote Free routes at source, while only `--sensitive`
        # (or the material's own verdict) makes every non-local row exposed.
        # Both runs mark the rows; the flag alone excludes them.
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/other"]})
        world = self.free_world(("vendor/model:free", 0.5))

        zone_only, _, z_code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("closed"))
        flagged, _, f_code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", world=world)

        self.assertEqual(z_code, 0)
        self.assertEqual(f_code, 0)
        self.assertIn("exposed (trains)",
                      next(ln for ln in flagged.splitlines()
                           if ln.startswith("|") and "vendor/model:free |" in ln))
        self.assertNotIn("vendor/model:free", zone_only)
        self.assertIn("blocked: no eligible local candidate", flagged)
        self.assertIn(f"zone: {self._tmp.name} (closed)", zone_only)
        self.assertNotIn("default pick", flagged)

    def test_the_run_header_names_the_zone_and_its_posture(self):
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            zones=self.zone_of("closed"))
        self.assertEqual(code, 0)   # no eligible local candidate: blocked
        self.assertIn(f"zone: {self._tmp.name} (closed)", out)

    def test_sensitive_flag_is_shown_as_the_shape_in_every_header(self):
        zones = self.zone_of("open")
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--working-dir",
            self._tmp.name, zones=zones)
        self.assertEqual(code, 0)   # blocked stop still prints the header
        expected = f"zone: {self._tmp.name} (open)"
        self.assertIn(expected, out)

        checked, _, check_code, _ = self.run_cli(
            "--check-policy", "--sensitive", "--working-dir", self._tmp.name,
            zones=zones)
        self.assertIsNone(check_code)
        self.assertIn(expected, checked)

        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        guarded, _, guard_code, _ = self.guard(
            "deepseek/deepseek-v4-pro", sensitive=True, zones=zones)
        self.assertEqual(guard_code, 0)
        self.assertIn(expected, guarded)

    def test_an_undeclared_folder_reports_open(self):
        out, _, code, _ = self.run_cli("--domain", "writing",
                                       "--working-dir", self._tmp.name)
        self.assertIsNone(code)   # open zone: the run completes
        self.assertIn(f"zone: {self._tmp.name} (open)", out)

    # --- Header truth: the quota line answers to the zone (issue #38) ----

    def test_a_fresh_world_header_states_the_open_zone_and_keeps_free_routes(self):
        # An absent zones file is open (ADR-0010): the header says so and
        # the quota line agrees — remote Free routes genuinely stay in the
        # pool, so the run must not claim a closed zone removed them.
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))

        out, _, code, _ = self.run_cli("--domain", "writing", world=world,
                                       zones_absent=True)

        self.assertIsNone(code)
        lines = out.splitlines()
        zone_line = next(ln for ln in lines if ln.startswith("zone: "))
        quota_line = next(ln for ln in lines if ln.startswith("free quota: "))
        self.assertEqual(zone_line, f"zone: {os.getcwd()} (open)")
        self.assertEqual(quota_line,
                         "free quota: unavailable | :free routes stay in the pool")
        self.assertNotIn("excluded by the closed zone", out)
        self.assertIn("vendor/model:free", out)

    def test_an_absent_zones_file_prints_no_line_of_its_own(self):
        # AC: no warning and no nag on a first run — the zone line states
        # open and nothing points at setup.
        out, err, code, _ = self.run_cli("--domain", "writing",
                                         zones_absent=True)

        self.assertIsNone(code)
        self.assertNotIn("zones file:", out)
        for nag in ("setup", "next:", "absent"):
            self.assertNotIn(nag, out.lower())
        self.assertNotIn("zones", err.lower())

    def test_a_present_zones_file_keeps_the_whole_output_byte_identical(self):
        # AC2 golden: zones.json present -> not one byte moves: no
        # advisory line, no reworded pool claim. The fixture machine
        # declares nothing closed, where free routes genuinely remain.
        out, _, code, _ = self.run_cli("--domain", "writing")

        self.assertIsNone(code)
        self.assertEqual(out, PRESENT_ZONES_GOLDEN.format(cwd=os.getcwd()))

    def test_check_policy_header_names_the_zone(self):
        out, _, code, _ = self.run_cli(
            "--check-policy", "--working-dir", self._tmp.name,
            zones=self.zone_of("closed"))
        self.assertIsNone(code)
        self.assertIn(f"zone: {self._tmp.name} (closed)", out)

    def test_check_policy_filters_zone_prohibited_free_routes_before_gaps(self):
        pol = json.loads(json.dumps(POLICY))
        pol["domains"] = {"writing": ["content_writing"]}
        pol["free_models"] = {"vendor/model": {
            "context_length": 262_144, "exposure": "no-retention"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = self.free_world(("vendor/model:free", 0.5))

        closed, _, code, _ = self.run_cli(
            "--check-policy", "--top", "8", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("closed"))
        opened, _, open_code, _ = self.run_cli(
            "--check-policy", "--top", "8", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("open"))

        self.assertIsNone(code)
        self.assertIsNone(open_code)
        gaps_closed = closed[closed.index("Research gaps"):closed.index("Stale summaries")]
        gaps_open = opened[opened.index("Research gaps"):opened.index("Stale summaries")]
        self.assertNotIn("vendor/model:free", gaps_closed)
        self.assertIn("vendor/model:free", gaps_open)

    def test_a_closed_zone_excludes_an_exposed_paid_route(self):
        # closed implies sensitive: Exposure is the shape's exclusion and
        # stays marked in the table, never hidden — and with no eligible
        # local candidate the run stops blocked (exit 0).
        self.sensitive_policy({"deepseek/deepseek-v4-pro-0813": "trains"})
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn("| admit |", out)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "deepseek/deepseek-v4-pro-0813 |" in ln)
        self.assertIn("exposed (trains)", row)
        self.assertNotIn("default pick (top of task order): "
                         "deepseek/deepseek-v4-pro-0813", out)
        self.assertIn("blocked: no eligible local candidate", out)

    # --- pre-flight: --assert-allowed -----------------------------------

    def guard(self, model, *, zones=None, sensitive=False,
              plain=False, policy_path=None, working_dir=None):
        argv = ["--assert-allowed", "--model", model,
                "--working-dir", working_dir or self._tmp.name]
        if sensitive:
            argv.append("--sensitive")
        if plain:
            argv.append("--plain")
        return self.run_cli(*argv, zones=zones, policy_path=policy_path)

    def test_assert_allowed_blocks_a_paid_route_in_a_closed_zone(self):
        # ADR 0008: closed implies sensitive, so only a local serving may
        # serve here — the block comes from the Exposure clause (the zone
        # clause alone never refuses an accountable market route), and it
        # exits 0 like every verdict.
        out, _, code, calls = self.guard("deepseek/deepseek-v4-pro",
                                         zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn(f"zone: {self._tmp.name} (closed)", out)
        self.assertIn("blocked by the free-use zone", out)
        self.assertIn("reason: exposed (no-retention)", out)
        self.assertEqual(calls, [])          # no board, no classification fetch

    def test_assert_allowed_blocks_a_remote_free_route_in_a_closed_zone(self):
        for model in ("vendor/model:free", "opencode/glm-5.3-flash"):
            with self.subTest(model=model):
                out, _, code, calls = self.guard(model,
                                                 zones=self.zone_of("closed"))
                self.assertEqual(code, 0)
                self.assertIn("blocked", out)
                self.assertIn("blocked by the free-use zone", out)
                self.assertIn(f"zone: {self._tmp.name} (closed)", out)
                self.assertIn(self._tmp.name, out)   # the zone is named
                self.assertEqual(calls, [])

    def test_assert_allowed_blocks_an_exposed_paid_route_on_a_sensitive_shape(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     sensitive=True)
        self.assertEqual(code, 0)
        self.assertIn("exposed (trains)", out)

    def test_assert_allowed_blocks_an_exposed_paid_route_in_a_closed_zone(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn("exposed (trains)", out)

    def test_an_unstated_shape_is_sensitive_and_the_output_says_so(self):
        # The dispatch contract fails closed: an unstated shape means
        # Sensitive, so a route that retains training data is refused by
        # default and the output states the shape it assumed.
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     zones=self.zone_of("open"))
        self.assertEqual(code, 0)
        self.assertIn("exposed (trains)", out)
        self.assertIn("shape: sensitive (assumed)", out)

    def test_plain_states_the_shape_and_admits_the_trains_route(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro", plain=True,
                                     zones=self.zone_of("open"))
        self.assertEqual(code, 0)
        self.assertIn("shape: plain (via --plain)", out)
        self.assertIn("allowed: deepseek/deepseek-v4-pro", out)

    def test_plain_states_a_shape_never_opens_a_zone(self):
        out, _, code, _ = self.guard("vendor/model:free", plain=True,
                                     zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn("remote free route is prohibited", out)
        self.assertIn("shape: plain (via --plain)", out)

    def test_sensitive_restatement_is_accepted_with_the_same_verdict(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     sensitive=True,
                                     zones=self.zone_of("open"))
        self.assertEqual(code, 0)
        self.assertIn("exposed (trains)", out)
        self.assertIn("shape: sensitive (via --sensitive)", out)

    def test_plain_and_sensitive_contradict_as_a_usage_error(self):
        _, _, code, calls = self.run_cli("--assert-allowed",
                                         "--model", "vendor/model",
                                         "--plain", "--sensitive")
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])

    def test_plain_is_read_only_by_the_pre_flight(self):
        _, _, code, calls = self.run_cli("--plain")
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])

    def test_usage_prog_is_fixed_regardless_of_argv0(self):
        # prog is a literal: usage names the tool, never argv[0].
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv",
                               ["not-the-tool-name", "--no-such-flag"]), \
                redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as exc:
                modelbandit.main()
        self.assertEqual(exc.exception.code, 2)
        self.assertIn("usage: modelbandit", err.getvalue())
        self.assertNotIn("not-the-tool-name", err.getvalue())

    def test_assert_allowed_needs_no_policy_file(self):
        absent = os.path.join(self._tmp.name, "absent.json")
        blocked, _, code, calls = self.guard("vendor/model:free",
                                             zones=self.zone_of("closed"),
                                             policy_path=absent)
        self.assertEqual(code, 0)
        self.assertIn("blocked by the free-use zone", blocked)
        self.assertEqual(calls, [])

        out, err, code, calls = self.guard("deepseek/deepseek-v4-pro",
                                           zones=self.zone_of("open"),
                                           plain=True, policy_path=absent)
        self.assertEqual(code, 0)
        self.assertIn("allowed: deepseek/deepseek-v4-pro", out)
        self.assertEqual(err, "")
        self.assertEqual(calls, [])

        # ...and without a policy file the assumed-Sensitive shape still
        # blocks a non-local route on the default no-retention assumption
        # (ADR 0008).
        guarded, _, code, calls = self.guard("deepseek/deepseek-v4-pro",
                                             zones=self.zone_of("closed"),
                                             policy_path=absent)
        self.assertEqual(code, 0)
        self.assertIn("reason: exposed (no-retention)", guarded)
        self.assertEqual(calls, [])

    def test_assert_allowed_reports_a_broken_zones_file_as_a_config_error(self):
        config_home = os.path.join(self._tmp.name, "broken-config")
        os.makedirs(os.path.join(config_home, "modelbandit"))
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": [{"path": self._tmp.name, "free": "opened"}]}, f)
        out, err, code = io.StringIO(), io.StringIO(), None
        argv = ["modelbandit", "--policy", self.policy_path, "--assert-allowed",
                "--model", "deepseek/deepseek-v4-pro", "--working-dir",
                self._tmp.name]
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                mock.patch("modelbandit.fetch_json",
                           side_effect=AssertionError("no network in a guard")), \
                mock.patch.object(sys, "argv", argv), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, 4)
        self.assertIn("opened", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_assert_allowed_treats_an_undeclared_folder_as_open(self):
        out, _, code, _ = self.guard("vendor/model:free", plain=True)
        self.assertEqual(code, 0)
        self.assertIn(f"zone: {self._tmp.name} (open)", out)
        self.assertIn("allowed: vendor/model:free", out)

    def test_assert_allowed_admits_a_local_catalog_entry_in_a_closed_zone(self):
        # A genuinely served local route is catalogued under a non-remote
        # prefix; the closed zone does not refuse what never leaves the machine.
        pol = json.loads(json.dumps(POLICY))
        model = "qwen/qwen3-coder-30b"
        pol["free_models"] = {"qwen/qwen3-coder-30b": {
            "context_length": 262_144, "exposure": "local"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.guard(model,
                                     zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn(f"allowed: {model}", out)

    def test_a_remote_free_route_labelled_local_is_refused_by_the_pre_flight(self):
        # The catalog's label is not a serving fact: a `:free` id labelled
        # `local` is a remote serving identity, and the pre-flight refuses it
        # in a closed zone exactly as the plan's source filter does.
        pol = json.loads(json.dumps(POLICY))
        model = "qwen/qwen3-coder-30b:free"
        pol["free_models"] = {"qwen/qwen3-coder-30b": {
            "context_length": 262_144, "exposure": "local"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.guard(model,
                                     zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn("remote free route is prohibited", out)
        self.assertIn(f"model: {model}", out)

    def test_assert_allowed_help_documents_policy_config_status(self):
        out, _, code, _ = self.run_cli("--assert-allowed", "--help")
        self.assertEqual(code, 0)
        self.assertIn("--assert-allowed", out)
        self.assertIn("4 policy/config error", " ".join(out.split()))

    def test_assert_allowed_requires_a_model_and_a_mode_to_read_it(self):
        _, _, code, calls = self.run_cli("--assert-allowed")
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        _, _, code, calls = self.run_cli("--model", "vendor/model:free")
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])

    # --- zones judge the place a path reaches: links resolved ------------

    def link(self, link, target):
        """A junction on Windows (`mklink /J` needs no privileges), a symlink
        elsewhere."""
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", link, target],
                capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
        else:
            os.symlink(target, link)
        return link

    def test_pre_flight_judges_a_link_by_the_place_it_reaches(self):
        # A junction inside an open zone pointing into a closed area is
        # judged closed: the pre-flight blocks the remote free route, names
        # the zone, and never echoes content.
        open_dir = os.path.join(self._tmp.name, "open-zone")
        closed_dir = os.path.join(self._tmp.name, "closed-zone")
        os.makedirs(open_dir)
        os.makedirs(closed_dir)
        link = self.link(os.path.join(open_dir, "shortcut"), closed_dir)

        out, _, code, calls = self.guard("vendor/model:free",
                                         zones=[closed_dir],
                                         working_dir=link)

        self.assertEqual(code, 0)
        self.assertIn("blocked by the free-use zone", out)
        self.assertIn(f"zone: {closed_dir} (closed)", out)
        self.assertEqual(calls, [])

    def test_pre_flight_admits_work_that_reaches_an_open_zone_through_a_link(self):
        # The mirror direction: a link outside the open zone pointing at the
        # open package is judged open - no false negative for allowed work.
        # The shape is stated (the material is not Sensitive) so the free
        # route's Exposure does not decide this; the zone does.
        open_dir = os.path.join(self._tmp.name, "open-zone")
        os.makedirs(open_dir)
        link = self.link(os.path.join(self._tmp.name, "to-open"), open_dir)

        out, _, code, _ = self.guard("vendor/model:free", plain=True,
                                     working_dir=link)

        self.assertEqual(code, 0)
        self.assertIn(f"zone: {open_dir} (open)", out)
        self.assertIn("allowed: vendor/model:free", out)

    def test_pre_flight_names_the_resolved_place_of_a_declared_link(self):
        # A closed declaration spelled through a link governs the place it
        # reaches, and the header says so instead of the link's spelling.
        target = os.path.join(self._tmp.name, "free-zone")
        os.makedirs(target)
        link = self.link(os.path.join(self._tmp.name, "free-link"), target)

        out, _, code, _ = self.guard("vendor/model:free",
                                     zones=[link],
                                     working_dir=link)

        self.assertEqual(code, 0)
        self.assertIn(f"zone: {target} (closed) (declared: {link})", out)
        self.assertIn("blocked by the free-use zone", out)

    def test_a_link_into_a_closed_zone_removes_remote_free_routes_from_a_ranking(self):
        self.free_risk_policy(
            {"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))
        open_dir = os.path.join(self._tmp.name, "open-zone")
        closed_dir = os.path.join(self._tmp.name, "closed-zone")
        os.makedirs(open_dir)
        os.makedirs(closed_dir)
        link = self.link(os.path.join(open_dir, "shortcut"), closed_dir)

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", link, world=world,
            zones=[closed_dir])

        self.assertEqual(code, 0)   # closed through the link: blocked stop
        self.assertIn(f"zone: {closed_dir} (closed)", out)
        self.assertNotIn("vendor/model:free", out)
        self.assertIn("| admit |", out)   # the non-local rows are marked
        self.assertIn("blocked: no eligible local candidate", out)

    def test_free_risk_price_is_uniform_across_exposure(self):
        # Same share, different Exposure, same risk-derived price and score.
        # Exposure decides admission, never the price.
        self.free_risk_policy(self.FREE_CATALOG)
        world = self.free_world(("vendor/model:free", 0.5),
                               ("vendor/other:free", 0.5))
        out, _, code, _ = self.run_cli("--domain", "writing", world=world)
        self.assertIsNone(code)
        rows = {mid: next(ln for ln in out.splitlines()
                          if ln.startswith("|") and f"{mid} |" in ln)
                for mid in ("vendor/model:free", "vendor/other:free")}
        self.assertIn("| 18.50 |", rows["vendor/model:free"])
        self.assertIn("| 18.50 |", rows["vendor/other:free"])
        self.assertIn("no-retention", rows["vendor/model:free"])
        self.assertIn("trains", rows["vendor/other:free"])

    def test_free_risk_tracks_cheapest_paid_ticket_at_every_basis(self):
        # The floor derives from the cheapest paid ticket under each basis:
        # v4-pro is cheapest for worst/primary, while 0813 is cheapest for best.
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))
        for basis, cheapest, cheapest_model, expected_score in (
                ("worst", 0.00772, "| deepseek/deepseek-v4-pro |", "18.50"),
                ("primary", 0.00772, "| deepseek/deepseek-v4-pro |", "18.50"),
                ("best", 0.00636, "deepseek/deepseek-v4-pro-0813 |", "22.46")):
            with self.subTest(basis=basis):
                out, _, code, _ = self.run_cli("--domain", "writing",
                                               "--pricing-basis", basis,
                                               world=world)
                self.assertIsNone(code)
                free_row = next(ln for ln in out.splitlines()
                                if ln.startswith("|")
                                and "vendor/model:free |" in ln)
                paid_row = next(ln for ln in out.splitlines()
                                if ln.startswith("|")
                                and cheapest_model in ln)
                self.assertIn(f"| {expected_score} |", free_row)
                self.assertIn(f"${cheapest:.4f}", paid_row)

    def test_served_local_route_scores_at_the_derived_nominal_floor(self):
        # A model this machine serves is a Free route by where it runs, not by
        # its id: Free risk applies to it like any other Free route.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0, free_risk=0.35)
        pol["free_models"] = {"lmstudio/qwen/qwen3-coder": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "lmstudio/qwen/qwen3-coder-30b", "tag_usage_share": 0.5})
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", world=world,
            local_models={mid: {"id": mid}})
        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "qwen/qwen3-coder-30b |" in ln)
        self.assertIn("| 18.50 |", row)
        self.assertIn("| local |", row)

    def test_free_risk_is_derived_below_the_cheapest_paid_ticket_without_warning(self):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0, free_risk=0.75)
        pol["free_models"] = {"vendor/model": self.FREE_CATALOG["vendor/model"]}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = self.free_world(("vendor/model:free", 0.5))
        out, err, code, _ = self.run_cli("--domain", "writing", world=world)
        self.assertIsNone(code)
        self.assertNotIn("Nominal floor", err)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "vendor/model:free |" in ln)
        self.assertIn("| 8.64 |", row)
        self.assertIn("default pick", out)

    def balance_world(self, free_share, paid_shares):
        """One writing pool: `vendor/model:free` beside priced paid models."""
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
        pol["affinity"]["eligibility_top_k"] = 5
        pol["domains"] = {"writing": ["content_writing"]}
        pol["hints"] = {}
        pol["summaries"] = {}
        pol["free_models"] = {"vendor/model": self.FREE_CATALOG["vendor/model"]}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["models"] = [make_model(f"m{i}/model", "0.000001", "0.000002",
                                      "0.000001")
                           for i in range(len(paid_shares))]
        world["models"].append(make_model("vendor/model:free", "0", "0", "0"))
        world["classifications"]["classifications"][0]["models"] = (
            [{"id": "vendor/model:free", "tag_usage_share": free_share}]
            + [{"id": f"m{i}/model", "tag_usage_share": share}
               for i, share in enumerate(paid_shares)])
        return world

    def test_free_dominant_pool_reads_ok_on_the_paid_competition(self):
        # Four paid models at one price are in balance (top-1 25%, top-2 50%).
        # A Free route at five times any paid share would top the combined
        # pool (~63% mass) — the balance criterion now judges the paid
        # competition, so the verdict is the paid reading, not Free's share.
        out, _, code, _ = self.run_cli(
            "--check-policy",
            world=self.balance_world(1.25, (0.25, 0.25, 0.25, 0.25)))
        self.assertIsNone(code)
        balance = out[out.index("## Score balance"):]
        self.assertIn("writing: top-1 25%, top-2 50%", balance)
        self.assertIn("— ok", balance)
        self.assertNotIn("OUT OF BALANCE", balance)
        self.assertIn("coefficient re-tune due: no", out)

    def test_pool_with_fewer_than_three_paid_candidates_is_not_judgeable(self):
        # Five candidates, two of them paid: Free's participation cannot trip
        # a criterion meant for the paid ranking.
        out, _, code, _ = self.run_cli(
            "--check-policy",
            world=self.balance_world(0.9, (0.6, 0.05)))
        self.assertIsNone(code)
        balance = out[out.index("## Score balance"):]
        self.assertIn("writing: 2 paid candidates — balance not judgeable "
                      "(needs 3+)", balance)
        self.assertNotIn("OUT OF BALANCE", balance)
        self.assertIn("coefficient re-tune due: no", out)

    def test_uncatalogued_free_route_is_visible_but_never_picked(self):
        world = build_world()
        world["models"].append(make_model("vendor/unknown:free", "0", "0", "0"))
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "vendor/unknown:free", "tag_usage_share": 0.2})
        out, _, _, _ = self.run_cli("--domain", "writing", "--deal",
                                    "--tickets", "12", world=world)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and "vendor/unknown:free" in line)
        self.assertIn("catalog", row)
        self.assertNotIn("default pick (top of task order): vendor/unknown:free", out)
        deal = out.split("\ndeal (", 1)[1]
        self.assertNotIn("vendor/unknown:free", deal)

    def test_canonical_resolution_regression_prices_august_endpoints(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("0.40–8.00 (2 eps, wide)", out)

    def test_unresolved_row_rendered(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("ghost/unknown-20260101", out)
        self.assertIn("unresolved to a priced model", out)

    def test_odd_resolution_note_lists_heuristic_and_unresolved(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        note = out[out.index("note: leaderboard rows"):]
        self.assertIn("deepseek/deepseek-v4-flash", note)
        self.assertIn("ghost/unknown-20260101", note)

    def test_domain_filtering_excludes_other_tags(self):
        out, _, _, _ = self.run_cli("--domain", "coding")
        self.assertIn("xiaomi/mimo-v2.6-pro", out)
        self.assertNotIn("deepseek/deepseek-v4-pro-0813 |", out)

    def test_top_limits_rows(self):
        out, _, _, _ = self.run_cli("--domain", "writing", "--top", "1")
        body = out[out.index("| # |"):]
        self.assertIn("| 1 |", body)
        self.assertNotIn("| 2 |", body)

    # --- pricing bases and effort ---------------------------------------

    def test_worst_basis_is_default(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("basis=worst", out)
        self.assertIn("policy: 0d old", out)
        self.assertIn("$0.0984", out)

    def test_best_basis_shows_floor(self):
        out, _, _, _ = self.run_cli("--domain", "writing", "--pricing-basis", "best")
        row = next(ln for ln in out.splitlines()
                   if "deepseek/deepseek-v4-pro-0813" in ln and ln.startswith("|"))
        self.assertIn("$0.0064", row)
        self.assertNotIn("$0.0984", row)

    def test_primary_basis_uses_models_list_price(self):
        out, _, _, _ = self.run_cli("--domain", "writing",
                                    "--pricing-basis", "primary")
        self.assertIn("$0.0322", out)

    def test_effort_exhaustive_multiplies_output(self):
        out, _, _, _ = self.run_cli("--domain", "writing", "--effort", "exhaustive")
        # Relace worst at mult 6: 0.0024 + 12000*6*8e-6 = 0.5784
        self.assertIn("$0.5784", out)
        self.assertIn("| max |", out)

    def test_collapsed_rung_prices_below_full_ladder(self):
        # Same pricing, different ladders: acme-x carries the full
        # reasoning_effort ladder, acme-x-lite only none/thinking. At
        # `thorough` the lite's rung collapses to `thinking`, and a collapsed
        # model must price strictly below its full-ladder twin at the same
        # intent.
        world = build_world()
        world["models"] += [
            make_model("acme/acme-x", "0.000001", "0.00001", "0"),
            make_model("acme/acme-x-lite", "0.000001", "0.00001", "0",
                       params=("reasoning",)),
        ]
        world["classifications"]["classifications"][0]["models"] += [
            {"id": "acme/acme-x", "tag_usage_share": 0.3},
            {"id": "acme/acme-x-lite", "tag_usage_share": 0.3},
        ]
        out, _, _, _ = self.run_cli("--domain", "writing", "--effort",
                                    "thorough", world=world)
        full_row = next(ln for ln in out.splitlines()
                        if ln.startswith("|") and "acme/acme-x |" in ln)
        lite_row = next(ln for ln in out.splitlines()
                        if ln.startswith("|") and "acme/acme-x-lite |" in ln)

        def per_ticket(row):
            return float(row.split("|")[7].strip().lstrip("$"))

        # Hand-computed at the authoring profile (in=20,000 out=12,000
        # cached=40%), thorough:
        #   full ladder resolves `high` -> table multiplier 2.5:
        #     20000*0.6*1e-6 + 12000*2.5*1e-5 = 0.012 + 0.30 = $0.3120
        #   binary ladder lacks above-default: `thinking` is the nearest rung
        #   (slot 1 of 2) -> mult 0.6 + (2.5-0.6)*(1/2) = 31/20:
        #     0.012 + 12000*(31/20)*1e-5 = 0.012 + 0.186 = $0.1980
        self.assertLess(per_ticket(lite_row), per_ticket(full_row))
        self.assertIn("$0.3120", full_row)
        self.assertIn("$0.1980", lite_row)
        # the collapse is visible in the rung column, and only there
        self.assertIn("thinking (collapsed)", lite_row)
        self.assertNotIn("(collapsed)", full_row)

    def test_full_ladder_unchanged_at_glance(self):
        # At `glance` nothing collapses (target 0.0): both ladders price the
        # glance multiplier 0.6 exactly, and no row carries the marker.
        world = build_world()
        world["models"] += [
            make_model("acme/acme-x", "0.000001", "0.00001", "0"),
            make_model("acme/acme-x-lite", "0.000001", "0.00001", "0",
                       params=("reasoning",)),
        ]
        world["classifications"]["classifications"][0]["models"] += [
            {"id": "acme/acme-x", "tag_usage_share": 0.3},
            {"id": "acme/acme-x-lite", "tag_usage_share": 0.3},
        ]
        out, _, _, _ = self.run_cli("--domain", "writing", "--effort", "glance",
                                    world=world)
        # 20000*0.6*1e-6 + 12000*0.6*1e-5 = 0.012 + 0.072 = $0.0840
        self.assertEqual(out.count("$0.0840"), 2)
        self.assertNotIn("(collapsed)", out)

    def test_delta_against_baseline(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        # The baseline (mimo, none/thinking ladder) resolves `measured` ->
        # default exactly: no collapse, table multiplier 1.0.
        # baseline = 20000*0.6*4.35e-7 + 20000*0.4*3.6e-9 + 12000*8.7e-7
        #          = 0.00522 + 0.0000288 + 0.01044 = 0.0156888
        # 0.0984 / 0.0156888 = 6.27x ; 0.00772 / 0.0156888 = 0.49x
        self.assertIn("6.27x", out)
        self.assertIn("0.49x", out)

    def test_no_endpoint_data_flagged(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("0.42–0.42 (no endpoint data)", out)

    # --- verdicts, pick, projection, budget -----------------------------

    def test_hints_annotate_by_prefix(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        block = out[out.index("hints (advisory"):]
        self.assertIn("deepseek/deepseek-v4-pro: skipped on output cost", block)
        self.assertIn("deepseek/deepseek-v4-pro-0813: skipped on output cost", block)

    def test_hints_absent_when_no_match(self):
        out, _, _, _ = self.run_cli("--domain", "coding")
        self.assertNotIn("hints (advisory", out)

    def test_summaries_annotate_by_longest_prefix(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        block = out[out.index("summaries (task-fit context"):]
        aug = next(ln for ln in block.splitlines() if "v4-pro-0813" in ln)
        apr = next(ln for ln in block.splitlines()
                   if ln.strip().startswith("deepseek/deepseek-v4-pro:"))
        self.assertIn("eol sibling summary", aug)
        self.assertIn("eol summary", apr)

    def test_summaries_absent_when_no_match(self):
        out, _, _, _ = self.run_cli("--domain", "coding")
        self.assertNotIn("summaries (task-fit context", out)

    def test_default_pick_and_route_to_floor(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("default pick (top of task order): openrouter/deepseek/deepseek-v4-pro-0813", out)
        self.assertIn("route to floor: pin provider 'Baidu'", out)
        self.assertIn("'Relace'", out)

    def test_cheapest_alternative_shown(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("cheapest shown: deepseek/deepseek-v4-pro at $0.0077/ticket",
                      out)

    def test_projection_with_tickets_and_floor(self):
        out, _, _, _ = self.run_cli("--domain", "writing", "--tickets", "2")
        # worst 0.0984*2 = 0.1968 -> $0.20 ; floor 0.00636*2 = 0.01272 -> $0.01
        self.assertIn("projection at 2 ticket(s): $0.20 (floor $0.01)", out)
        self.assertIn("baseline anchor: $0.03", out)

    def test_budget_under_exits_cleanly(self):
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "2",
                                       "--budget", "1")
        self.assertIsNone(code)
        self.assertIn("budget: $1.00 -> under", out)

    def test_budget_over_exits_zero_with_the_over_verdict(self):
        # Over budget is a verdict on stdout, not a failure: exit 0 (v2).
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "2",
                                       "--budget", "0.1")
        self.assertEqual(code, 0)
        self.assertIn("budget: $0.10 -> OVER", out)

    def test_token_overrides_change_projection(self):
        out, _, _, _ = self.run_cli("--domain", "writing",
                                    "--in-tokens", "0", "--out-tokens", "0")
        self.assertIn("projection at 1 ticket(s): $0.00", out)

    # --- malformed ranking inputs stop with a message, never a traceback --

    def test_fit_non_numeric_score_exits_naming_the_entry(self):
        _, err, code, _ = self.run_cli("--domain", "writing", "--fit", "mid=high")
        self.assertIn("is not a number on 0-5", err)
        self.assertIn("'mid=high'", err)
        self.assertEqual(code, 2)

    def test_fit_empty_value_exits_naming_the_entry(self):
        _, err, code, _ = self.run_cli("--domain", "writing", "--fit", "a=1,b=")
        self.assertIn("is not a number on 0-5", err)
        self.assertIn("'b='", err)
        self.assertEqual(code, 2)

    def test_cached_share_outside_0_1_exits_naming_the_flag(self):
        # A percentage-style 12 must not price a ticket below zero.
        for share in ("12", "1.5", "-0.5"):
            with self.subTest(share=share):
                _, err, code, _ = self.run_cli("--domain", "writing",
                                               "--cached-share", share)
                self.assertIn("--cached-share", err)
                self.assertIn("between 0 and 1", err)
                self.assertEqual(code, 2)

    def test_negative_token_overrides_exit_naming_the_flag(self):
        for flag in ("--in-tokens", "--out-tokens"):
            with self.subTest(flag=flag):
                _, err, code, _ = self.run_cli("--domain", "writing", flag, "-5")
                self.assertIn(flag, err)
                self.assertIn("must not be negative", err)
                self.assertEqual(code, 2)

    def test_cached_share_boundaries_are_accepted(self):
        # 0 and 1 are fractions, not percentage slips: both stay accepted.
        for share in ("0", "1"):
            out, _, code, _ = self.run_cli("--domain", "writing",
                                           "--cached-share", share)
            self.assertIsNone(code)
            self.assertNotIn("-$", out)

    def test_cached_share_zero_boundary_prices_uncached_input(self):
        # Hand-computed at the models-list figure, all input uncached:
        # 20000*6.6e-7 + 12000*1.98e-6 = 0.03696 -> $0.0370
        out, _, code, _ = self.run_cli("--domain", "writing", "--cached-share",
                                       "0", "--pricing-basis", "primary")
        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "deepseek/deepseek-v4-pro-0813" in ln)
        self.assertIn("$0.0370", row)

    def test_profile_equivalent_overrides_keep_output_byte_identical(self):
        baseline = self.run_cli("--domain", "writing")
        overridden = self.run_cli("--domain", "writing", "--cached-share", "0.4",
                                  "--in-tokens", "20000", "--out-tokens", "12000")
        self.assertEqual(overridden, baseline)

    def test_over_budget_still_exits_zero_at_an_accepted_boundary(self):
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "2",
                                       "--budget", "0.1", "--cached-share", "0")
        self.assertEqual(code, 0)
        self.assertIn("budget: $0.10 -> OVER", out)

    # --- Free-request quota: a cliff before the plan is drawn --------------

    QUOTA_CATALOG = {
        "vendor/model": {"context_length": 262_144, "exposure": "no-retention",
                         "summary_ref": "deepseek/deepseek-v4-pro"},
        "opencode/flash": {"context_length": 262_144,
                           "exposure": "no-retention",
                           "summary_ref": "deepseek/deepseek-v4-pro"},
    }

    def quota_policy(self, reserve=None, catalog=None):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
        if reserve is not None:
            pol["scoring"]["free_quota_reserve"] = reserve
        pol["affinity"]["eligibility_top_k"] = 5
        pol["free_models"] = (catalog if catalog is not None
                              else self.QUOTA_CATALOG)
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

    def free_only_policy(self, reserve=None):
        self.quota_policy(reserve=reserve,
                          catalog={"vendor/model":
                                   self.QUOTA_CATALOG["vendor/model"]})

    def quota_world(self):
        """A ':free' route and a harness 'opencode/*' free model together."""
        return self.free_world(("vendor/model:free", 0.5))

    @staticmethod
    def key_counter(used, limit):
        return {"data": {"free_model_daily_requests": {"used": used,
                                                       "limit": limit}}}

    def test_exhausted_quota_removes_free_routes_from_the_table_and_deal(self):
        self.quota_policy()
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--tickets", "12",
            world=self.quota_world(),
            key_payload=self.key_counter(50, 50))

        self.assertIsNone(code)
        self.assertIn("free quota: 50/50 used (0 left)", out)
        self.assertIn("reserve 5 protected; plan size does not gate", out)
        free_row = next(ln for ln in out.splitlines()
                        if ln.startswith("|") and "vendor/model:free |" in ln)
        self.assertIn("free quota exhausted (50/50 used)", free_row)
        # The excluded route leaves the pick and the deal; the table keeps
        # the row and states why it cannot serve.
        self.assertNotIn("default pick (top of task order): vendor/model:free",
                         out)
        deal = out.split("\ndeal (", 1)[1]
        self.assertNotIn("vendor/model:free", deal)

        # A harness-served free model spends no OpenRouter free requests.
        opencode_row = next(ln for ln in out.splitlines()
                            if ln.startswith("|")
                            and "opencode/flash |" in ln)
        self.assertNotIn("free quota", opencode_row)
        self.assertIn("opencode/flash", deal)

    def test_covered_quota_keeps_the_free_route_in_the_pool(self):
        self.free_only_policy()
        out, err, code, _ = self.run_cli(
            "--domain", "writing",
            world=self.free_world(("vendor/model:free", 0.5)),
            key_payload=self.key_counter(12, 50))

        self.assertIsNone(code)
        self.assertIn("free quota: 12/50 used (38 left)", out)
        self.assertNotIn("free quota", err)
        self.assertIn("default pick (top of task order): "
                      "openrouter/vendor/model:free", out)

    def test_plan_size_does_not_gate_when_reserve_is_available(self):
        # Plan size is not known Free demand before drawing: at the reserve
        # boundary, the route remains eligible regardless of ticket count.
        self.free_only_policy(reserve=10)
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "3",
            world=self.free_world(("vendor/model:free", 0.5)),
            key_payload=self.key_counter(40, 50))

        self.assertIsNone(code)
        self.assertIn("reserve 10 protected; plan size does not gate", out)
        free_row = next(ln for ln in out.splitlines()
                        if ln.startswith("|") and "vendor/model:free |" in ln)
        self.assertNotIn("free quota", free_row)
        self.assertIn("default pick (top of task order): "
                      "openrouter/vendor/model:free", out)

    def test_quota_below_reserve_excludes_openrouter_free_routes(self):
        self.free_only_policy(reserve=10)
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "3",
            world=self.free_world(("vendor/model:free", 0.5)),
            key_payload=self.key_counter(41, 50))

        self.assertIsNone(code)
        self.assertIn("reserve 10 protected; plan size does not gate", out)
        free_row = next(ln for ln in out.splitlines()
                        if ln.startswith("|") and "vendor/model:free |" in ln)
        self.assertIn("free quota thin (9 left < 0 planned + 10 reserve)",
                      free_row)

    def test_unreachable_quota_warns_once_and_leaves_the_pool_unchanged(self):
        self.free_only_policy()
        out, err, code, _ = self.run_cli(
            "--domain", "writing",
            world=self.free_world(("vendor/model:free", 0.5)))

        self.assertIsNone(code)
        self.assertEqual(err.count("free quota"), 1)
        # The warning states the quota fact only: the pool verdict is the
        # header's job, and here the open zone does keep free routes in it.
        self.assertNotIn("stay in the pool", err)
        self.assertIn("free quota: unavailable | :free routes stay in the pool",
                      out)
        self.assertIn("default pick (top of task order): "
                      "openrouter/vendor/model:free", out)

    def test_check_policy_plans_no_tickets_and_reads_no_counter(self):
        _, err, code, calls = self.run_cli("--check-policy")

        self.assertIsNone(code)
        self.assertFalse(any(name == "key.json" for _, name, *_ in calls))
        self.assertNotIn("free quota", err)

    def test_deal_can_send_all_tickets_to_free_when_paid_candidates_are_inadmissible(self):
        # The deal's free share survives the ADR 0008 rule: paid candidates
        # are inadmissible (trains), the no-retention cloud free route is
        # excluded alike but stays marked, and the eligible local candidate
        # — itself a Free route — takes every ticket.
        pol = json.loads(json.dumps(POLICY))
        pol["exposure"] = {"deepseek/": "trains"}
        pol["free_models"] = {
            "vendor/model": {"context_length": 262_144,
                             "exposure": "no-retention",
                             "summary_ref": "deepseek/deepseek-v4-pro"},
            "lmstudio/qwen": {"context_length": 262_144, "exposure": "local",
                              "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        mid = "lmstudio/qwen/qwen3-coder-30b"

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "12",
            "--deal", "--seed", "all-free-valid",
            world=self.free_world(("vendor/model:free", 0.5)),
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if "vendor/model:free |" in ln)
        self.assertIn("exposed (no-retention)", row)   # marked, never dealt
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn(f"| {mid} |", deal)
        self.assertNotIn("vendor/model:free", deal)
        self.assertIn("free share: 12/12 tickets (100%)", out)
        self.assertNotIn("deepseek/deepseek-v4-pro |", deal)

    # --- setup posture report: --status (issue #37) ----------------------
    #
    # The machine-readable companion to the README Setup section: read-only
    # and fully offline. Exit 0 whenever setup files are absent (the
    # documented default), 4 only when a file that exists fails validation —
    # never an answer code, never a traceback.

    def status(self, *, working_dir=None, policy_path=None, zones=None,
               zones_absent=False):
        argv = ["--status"]
        if working_dir:
            argv += ["--working-dir", working_dir]
        return self.run_cli(*argv, zones=zones,
                            zones_absent=zones_absent, policy_path=policy_path)

    def test_status_reports_the_setup_lines_for_a_provisioned_setup(self):
        # AC1: one line each — zone, zones file, the built-in secrets rules
        # note, policy age — for a machine with zones.json in place. The
        # zones line names this fixture's file (the exact spelling of
        # that path — zones_file_label()'s — is pinned by the absent-state
        # test below, whose home the helper can resolve).

        out, err, code, calls = self.status(working_dir=self._tmp.name)

        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"zone: {self._tmp.name} (open)")
        self.assertTrue(lines[1].startswith("zones file: present ("), lines[1])
        self.assertTrue(lines[1].endswith("/config/modelbandit/zones.json)"),
                        lines[1])
        self.assertEqual(lines[2], "secrets: built-in rules apply")
        policy = os.path.join(self._tmp.name, "policy.json")
        self.assertEqual(lines[3], f"policy: {policy} — 0d old")
        self.assertEqual(err, "")
        self.assertEqual(calls, [])

    def test_status_names_no_secrets_file_surface(self):
        # The rules file is gone (spec #75): no file path, no presence
        # line, and no setup-interview pointer anywhere in the report.
        out, err, code, calls = self.status(working_dir=self._tmp.name,
                                            zones_absent=True)

        self.assertEqual(code, 0)
        self.assertIn("secrets: built-in rules apply", out)
        for gone in ("secrets file:", "modelbandit.secrets.json",
                     "setup interview", "next:"):
            self.assertNotIn(gone, out)
        self.assertEqual(err, "")
        self.assertEqual(calls, [])

    def test_status_empty_setup_reports_the_open_zone_and_exits_zero(self):
        # AC2: no zones file — every path is open (ADR-0010), so exit 0 and
        # three lines: the zone states open, the built-in rules note, the
        # policy age. No zones-file line, no nag, no setup pointer.
        out, err, code, calls = self.status(working_dir=self._tmp.name,
                                            zones_absent=True)

        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"zone: {self._tmp.name} (open)")
        self.assertEqual(lines[1], "secrets: built-in rules apply")
        policy = os.path.join(self._tmp.name, "policy.json")
        self.assertEqual(lines[2], f"policy: {policy} — 0d old")
        self.assertEqual(len(lines), 3)
        self.assertNotIn("zones file:", out)
        self.assertEqual(err, "")
        self.assertEqual(calls, [])

    def test_status_reports_an_absent_policy_as_unknown_and_exits_zero(self):
        # 0 whenever files are absent: a policy file that is not there is
        # `unknown` age, never an error.
        absent = os.path.join(self._tmp.name, "absent-policy.json")

        out, err, code, calls = self.status(working_dir=self._tmp.name,
                                            policy_path=absent)

        self.assertEqual(code, 0)
        self.assertIn(f"policy: {absent} — unknown", out)
        self.assertEqual(err, "")
        self.assertEqual(calls, [])

    def test_status_exits_four_naming_an_existing_invalid_zones_file(self):
        # AC3: a zones file that exists but fails validation is a config
        # error (exit 4) naming the file — nothing else is printed.
        config_home = os.path.join(self._tmp.name, "broken-config")
        os.makedirs(os.path.join(config_home, "modelbandit"))
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": [{"path": self._tmp.name, "free": "opened"}]}, f)
        out, err, code = io.StringIO(), io.StringIO(), None
        argv = ["modelbandit", "--policy", self.policy_path, "--status",
                "--working-dir", self._tmp.name]
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                mock.patch("modelbandit.fetch_json",
                           side_effect=AssertionError("no network in --status")), \
                mock.patch.object(sys, "argv", argv), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, 4)
        self.assertIn("zones.json", err.getvalue())
        self.assertIn("opened", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_status_exits_four_naming_an_existing_invalid_policy_file(self):
        # AC3: an existing policy that cannot be trusted stops the report
        # with exit 4 naming the file; the stdout report never starts.
        with open(self.policy_path, "w", encoding="utf-8") as f:
            f.write("{oops")

        out, err, code, calls = self.status(working_dir=self._tmp.name)

        self.assertEqual(code, 4)
        self.assertIn("cannot read policy file", err)
        self.assertIn("policy.json", err)
        self.assertEqual(out, "")
        self.assertEqual(calls, [])

    def test_status_is_offline_when_every_fetch_raises(self):
        # AC2/AC4: no endpoint fetch, no classification, no quota — the
        # mode must pass when every fetch raises, with zero fetch calls
        # recorded.
        calls = []

        def exploding_fetch(*args, **kwargs):
            calls.append(args)
            raise AssertionError("network in --status")

        config_home = self.zones_file([])
        out, err = io.StringIO(), io.StringIO()
        code = None
        argv = ["modelbandit", "--policy", self.policy_path, "--status",
                "--working-dir", self._tmp.name]
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                mock.patch("modelbandit.fetch_json", side_effect=exploding_fetch), \
                mock.patch("modelbandit.probe_local_models",
                           side_effect=AssertionError("local probe in --status")), \
                mock.patch("modelbandit.free_quota",
                           side_effect=AssertionError("quota in --status")), \
                mock.patch.object(sys, "argv", argv), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn(f"zone: {self._tmp.name} (open)", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_status_help_documents_the_flag(self):
        out, _, code, _ = self.run_cli("--status", "--help")
        self.assertEqual(code, 0)
        joined = " ".join(out.split())
        self.assertIn("--status", joined)
        self.assertIn("offline", joined)


class PolicyFileTests(CliTests):
    """One policy loader: every entry point reads the policy file the same
    way, as UTF-8, and a policy that cannot be read or trusted is a
    policy/config error (status 4) — never a locale-dependent mangle, never
    an uncaught traceback, never a Secrets-gate verdict."""

    def write_policy(self, policy):
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(policy, f)

    def non_ascii_policy(self, summary):
        pol = json.loads(json.dumps(POLICY))
        pol["summaries"] = {"deepseek/deepseek-v4-pro-0813": summary}
        self.write_policy(pol)

    def locale_console(self, policy_path):
        """A console whose preferred encoding is not UTF-8: an open() of the
        policy file without an explicit encoding is decoded with the console's
        codec (cp1252 here), exactly as an unpatched run would be on one."""
        real_open = open

        def open_with_console_codec(file, mode="r", *args, **kwargs):
            if (os.path.abspath(os.fspath(file))
                    == os.path.abspath(policy_path)
                    and "b" not in mode and "encoding" not in kwargs):
                return real_open(file, mode, *args, encoding="cp1252", **kwargs)
            return real_open(file, mode, *args, **kwargs)

        return mock.patch("builtins.open", open_with_console_codec)

    def run_gate(self, *argv):
        """A guard run with stdin and machine facts pinned: no console, no
        real machine, no network."""
        with mock.patch.object(sys, "stdin", io.StringIO("")), \
                mock.patch("modelbandit.machine_facts",
                           return_value={"identifiers": []}):
            return self.run_cli(*argv)

    def assert_status_4_everywhere(self):
        """A policy no entry point can trust stops them all with status 4 and
        a message naming the file — no traceback, no exit 1. The secrets
        check is absent by design (the mode split): it answers material
        questions only and reads no policy."""
        for argv in (["--domain", "writing"],           # the ranking run
                     ["--check-policy"],                # the policy check
                     ["--assert-allowed",
                      "--model", "deepseek/deepseek-v4-pro"]):  # pre-flight
            with self.subTest(entry=argv[0]):
                out, err, code, _ = self.run_gate(*argv)
                self.assertEqual(code, 4)
                self.assertIn("cannot read policy file", err)
                self.assertIn("policy.json", err)
                self.assertNotIn("Traceback", err)

    def test_loader_decodes_non_ascii_utf8_exactly(self):
        self.non_ascii_policy("żółw őrizetlenül")
        policy = modelbandit.load_policy_file(self.policy_path)
        self.assertEqual(policy["summaries"]["deepseek/deepseek-v4-pro-0813"],
                         "żółw őrizetlenül")

    def test_non_ascii_prose_prints_the_same_on_a_non_utf8_console(self):
        summary = "żółw ścieżką"
        self.non_ascii_policy(summary)
        with self.locale_console(self.policy_path):
            out, _, code, _ = self.run_cli("--domain", "writing")
        self.assertIsNone(code)
        self.assertIn(summary, out)

    def test_a_console_undecodable_character_does_not_abort_the_ranking(self):
        # "ő" is at home in UTF-8 but undefined in the simulated console's
        # codec: a locale-decoded read would abort the run mid-table.
        self.non_ascii_policy("widoczny őrizetlenül")
        with self.locale_console(self.policy_path):
            out, _, code, _ = self.run_cli("--domain", "writing")
        self.assertIsNone(code)
        self.assertIn("őrizetlenül", out)

    def test_an_undecodable_policy_stops_every_entry_point_with_status_4(self):
        with open(self.policy_path, "wb") as f:
            f.write(b'{"scoring": "\xff\xfe"}')
        self.assert_status_4_everywhere()

    def test_a_policy_that_is_not_json_stops_every_entry_point_with_status_4(self):
        with open(self.policy_path, "w", encoding="utf-8") as f:
            f.write("{oops")
        self.assert_status_4_everywhere()

    def test_an_untrustworthy_policy_stops_the_ranking_with_status_4(self):
        # A policy that parses and loads but cannot be trusted is a
        # rules/config error on the ranking path too: an uncaught
        # SystemExit from load_policy_config would fall through as status 1,
        # a generic operational failure rather than any verdict, which is
        # exactly what this class pins against.
        self.write_policy({"domains": {}})
        for argv in (["--domain", "writing"], ["--check-policy"]):
            with self.subTest(entry=argv[0]):
                out, err, code, _ = self.run_gate(*argv)
                self.assertEqual(code, 4)
                self.assertIn("policy/config error", err)
                self.assertIn("scoring", err)
                self.assertNotIn("Traceback", err)

    def test_an_unknown_exposure_override_stops_the_guards_with_status_4(self):
        pol = json.loads(json.dumps(POLICY))
        pol["exposure"] = {"deepseek/": "exposd"}
        self.write_policy(pol)
        out, err, code, _ = self.run_gate("--assert-allowed",
                                          "--model", "deepseek/deepseek-v4-pro")
        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertIn("pre-flight: policy/config error", err)
        self.assertIn("unknown exposure", err)
        self.assertIn("deepseek/", err)

    def test_a_local_label_on_a_remote_prefix_stops_the_guards_with_status_4(self):
        # Localness is a serving fact, never a catalogue claim: the policy
        # stops the contradiction loudly, naming the entry, before any run.
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"opencode/flash-free": {
            "context_length": 262_144, "exposure": "local"}}
        self.write_policy(pol)
        out, err, code, _ = self.run_gate("--assert-allowed",
                                          "--model", "opencode/flash-free")
        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertIn("contradicts the remote serving identity", err)
        self.assertIn("opencode/flash-free", err)

    def test_an_unknown_exposure_in_the_catalog_stops_the_guards_with_status_4(self):
        pol = json.loads(json.dumps(POLICY))
        pol["free_models"] = {"deepseek/": {"context_length": 262_144,
                                            "exposure": "exposd"}}
        self.write_policy(pol)
        out, err, code, _ = self.run_gate("--assert-allowed",
                                          "--model", "deepseek/deepseek-v4-pro")
        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertIn("unknown exposure", err)


if __name__ == "__main__":
    unittest.main()
