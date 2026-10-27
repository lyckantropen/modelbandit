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
               params=("reasoning_effort",)):
    m = {"id": mid, "supported_parameters": list(params),
         "pricing": {"prompt": prompt, "completion": completion,
                     "input_cache_read": cache_read}}
    if canonical:
        m["canonical_slug"] = canonical
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
    ]}
    rankings = {"data": [
        {"model_permaslug": "deepseek/deepseek-v4-pro-20260813",
         "total_tokens": "2000000000"},
        {"model_permaslug": "deepseek/deepseek-v4-pro-20260423",
         "total_tokens": "3000000000"},
        {"model_permaslug": "ghost/unknown-20260101", "total_tokens": "100"},
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
    return {"models": models, "classifications": classifications,
            "rankings": rankings, "endpoints": endpoints}


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
# with its zones.json present (declares the default open), captured before
# issue #38. A present zones file may not move a single byte: no advisory
# line, and no reworded pool claim where free routes genuinely remain.
PRESENT_ZONES_GOLDEN = """\
# Popularity ranking: writing

zone: undeclared (open)
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

default pick (top of task order): deepseek/deepseek-v4-pro-0813
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

    def zones_file(self, zones, default="open"):
        """This fixture machine's free-use zones. A test about pricing, quota
        or the deal declares the machine open, so the zone gate stays out of
        its way; the machine default (closed) is covered in test_zones.py."""
        config_home = os.path.join(self._tmp.name, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": list(zones or []), "default": default}, f)
        return config_home

    def run_cli(self, *argv, world=None, local_models=None, key_payload=None,
                zones=None, zones_default="open", policy_path=None,
                zones_absent=False):
        world = world if world is not None else build_world()
        local_models = local_models if local_models is not None else {}
        if zones_absent:
            # A fresh install: no zones.json exists anywhere the loader
            # looks, so the config root falls back to ~/.config against a
            # throwaway home and nothing ever creates it.
            home = os.path.join(self._tmp.name, "home")
            env = {"XDG_CONFIG_HOME": "", "HOME": home, "USERPROFILE": home}
        else:
            config_home = self.zones_file(zones, default=zones_default)
            env = {"XDG_CONFIG_HOME": config_home}
        calls = []

        def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
            calls.append((url, cache_name, auth, refresh))
            if cache_name == "key.json":
                if key_payload is None:
                    # No key, or an unreachable endpoint: the counter is not
                    # reported and the run carries on without it.
                    raise SystemExit("cannot reach https://openrouter.ai/api/v1/key")
                return key_payload
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
        argv = ["modelbandit", "--policy", policy_path or self.policy_path, *argv]
        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch), \
                mock.patch("modelbandit.probe_local_models", return_value=local_models), \
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
            "local-coder": {"context_length": 262_144, "exposure": "local",
                            "summary_ref": "ghost/family"},
            "opencode/free-coder": {
                "context_length": 262_144, "exposure": "no-retention",
                "summary_ref": "ghost/family"},
        }
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        local = {"local-coder": {"id": "local-coder",
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

        self.assertIsNone(code)
        self.assertIsNone(code2)
        self.assertIn("local-coder", first)
        self.assertIn("opencode/free-coder", first)
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

    # --- Sensitive shape: the admission seam in the output --------------

    def sensitive_policy(self, exposure):
        pol = json.loads(json.dumps(POLICY))
        pol["exposure"] = exposure
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

    def test_sensitive_marks_the_exposed_row_and_keeps_it_visible(self):
        self.sensitive_policy({"deepseek/deepseek-v4-flash": "trains"})
        out, _, code, _ = self.run_cli("--domain", "writing", "--sensitive")
        self.assertIsNone(code)
        self.assertIn("| admit |", out)
        row = next(ln for ln in out.splitlines()
                   if "deepseek/deepseek-v4-flash |" in ln)
        self.assertIn("exposed (trains)", row)      # visible with a reason
        other = next(ln for ln in out.splitlines()
                     if "deepseek/deepseek-v4-pro |" in ln)
        self.assertNotIn("exposed", other)

    def test_sensitive_pick_shuns_the_exposed_top_row(self):
        # v4-pro tops the task order at alpha .7 / beta 1 (0.005^... priced at
        # $0.0077), but exposure excludes it: the pick falls to the best
        # admitted row and the exclusion is stated.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=0.7, beta=1.0)
        pol["exposure"] = {"deepseek/deepseek-v4-pro": "trains"}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.run_cli("--domain", "writing", "--sensitive")
        self.assertIsNone(code)
        self.assertIn("top of task order deepseek/deepseek-v4-pro is excluded",
                      out)
        self.assertIn("default pick (top of task order): "
                      "deepseek/deepseek-v4-flash", out)
        # the same run without the flag picks the top row, as today
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("default pick (top of task order): "
                      "deepseek/deepseek-v4-pro", out)

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
        self.sensitive_policy({"deepseek/deepseek-v4-flash": "trains"})
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "12",
                                       "--deal", "--seed", "proj",
                                       "--sensitive")
        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertNotIn("deepseek/deepseek-v4-flash", block)
        self.assertEqual(sum(int(ln.split("|")[7].strip())
                             for ln in block.splitlines()
                             if ln.startswith("| ")
                             and ln.split("|")[1].strip().isdigit()), 12)

    def test_sensitive_shape_with_no_admitted_candidate_exits(self):
        self.sensitive_policy({"deepseek/": "trains"})
        _, _, code, _ = self.run_cli("--domain", "writing", "--sensitive")
        self.assertIn("no candidate admitted", code)

    def test_missing_scoring_block_exits_with_key(self):
        pol = json.loads(json.dumps(POLICY))
        del pol["scoring"]
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        _, _, code, calls = self.run_cli("--domain", "writing")
        self.assertIn("scoring", code)
        self.assertEqual(calls, [])

    def test_score_orders_by_popularity_priced_at_cost(self):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=0.7, beta=1.0)
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, _, _ = self.run_cli("--domain", "writing")
        body = out[out.index("| # |") :]
        # v4-pro is ~13x cheaper per ticket than the share leader -> tops the order
        self.assertIn("default pick (top of task order): deepseek/deepseek-v4-pro\n", out)
        self.assertLess(body.index("deepseek/deepseek-v4-pro |"),
                        body.index("deepseek/deepseek-v4-pro-0813 |"))

    def test_fit_composes_and_reorders(self):
        out, _, _, _ = self.run_cli("--domain", "writing",
                                    "--fit", "deepseek/deepseek-v4-pro-0813=0")
        self.assertIn("default pick (top of task order): deepseek/deepseek-v4-pro\n", out)
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
            _, _, code, _ = self.run_cli("--domain", "writing")
            self.assertIn(f"{path}.{key}", code)

    def test_missing_domain_exits(self):
        _, _, code, _ = self.run_cli()
        self.assertIn("need --domain", code)

    def test_unknown_domain_exits(self):
        _, _, code, _ = self.run_cli("--domain", "nope")
        self.assertIn("no domain", code)

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
            "qwen/qwen3-coder": {"context_length": 65_536,
                                  "exposure": "local",
                                  "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)
        served = {"qwen/qwen3-coder-30b": {
            "id": "qwen/qwen3-coder-30b", "context_length": 32_768}}

        out, _, code, calls = self.run_cli(
            "--domain", "writing", local_models=served)

        self.assertIsNone(code)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and "qwen/qwen3-coder-30b" in line)
        self.assertIn("64K | local |", row)
        self.assertIn("qwen/qwen3-coder-30b: eol summary", out)
        self.assertFalse(any(url.endswith("/endpoints")
                             and "qwen/qwen3-coder" in url for url, *_ in calls))

    def test_served_local_candidate_without_summary_is_visible_but_not_admitted(self):
        policy = json.loads(json.dumps(POLICY))
        policy["free_models"] = {
            "local/qwen": {"context_length": 262_144, "exposure": "local"}}
        with open(self.policy_path, "w") as f:
            json.dump(policy, f)

        out, _, code, _ = self.run_cli(
            "--domain", "writing",
            local_models={"local/qwen-30b": {"id": "local/qwen-30b"}})

        self.assertIsNone(code)
        row = next(line for line in out.splitlines()
                   if line.startswith("|") and "local/qwen-30b" in line)
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
        self.assertIn("default pick (top of task order): vendor/model:free", out)

    # --- free-use zones: main wires the regime into admission --------

    def zone_of(self, free):
        return [{"path": self._tmp.name, "free": free}]

    def test_a_closed_zone_filters_remote_free_routes_at_source(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))

        open_run, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name, world=world)
        self.assertIsNone(code)
        self.assertIn("default pick (top of task order): vendor/model:free",
                      open_run)

        closed, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("closed"))
        self.assertIsNone(code)
        # Never ranked, never listed: the zone's prohibition removes the
        # candidate before the table is built, so there is no row to mark.
        self.assertNotIn("vendor/model:free", closed)
        self.assertNotIn("| admit |", closed)
        self.assertIn(f"zone: {self._tmp.name} (closed)", closed)

    def test_a_closed_zone_keeps_remote_free_out_of_the_deal(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
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
            zones=self.zone_of("closed"))

        self.assertIsNone(code)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertNotIn("vendor/model:free", deal)
        self.assertEqual(sum(int(ln.split("|")[7].strip())
                             for ln in deal.splitlines()
                             if ln.startswith("| ")
                             and ln.split("|")[1].strip().isdigit()), 12)

    def test_a_closed_zone_still_admits_a_locally_served_model(self):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0, free_risk=0.35)
        pol["free_models"] = {"qwen/qwen3-coder": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "qwen/qwen3-coder-30b", "tag_usage_share": 0.5})

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("closed"),
            local_models={"qwen/qwen3-coder-30b": {"id": "qwen/qwen3-coder-30b"}})

        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "qwen/qwen3-coder-30b |" in ln)
        self.assertNotIn("remote free route is prohibited", row)
        self.assertIn("default pick (top of task order): qwen/qwen3-coder-30b",
                      out)

    def test_the_sensitive_flag_cannot_loosen_a_closed_zone(self):
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/other"]})
        world = self.free_world(("vendor/model:free", 0.5))

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--working-dir",
            self._tmp.name, world=world, zones=self.zone_of("closed"))

        self.assertIsNone(code)
        # Still closed, not merely sensitive: the remote free route is absent.
        self.assertNotIn("vendor/model:free", out)
        self.assertNotIn("default pick (top of task order): vendor/model:free",
                         out)

    def test_a_sensitive_zone_keeps_todays_sensitive_behaviour(self):
        # No --sensitive flag: the zone alone excludes the exposed free route.
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/other"]})
        world = self.free_world(("vendor/model:free", 0.5))

        zone_only, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            world=world, zones=self.zone_of("sensitive"))
        flagged, _, _, _ = self.run_cli(
            "--domain", "writing", "--sensitive", world=world)

        self.assertIsNone(code)
        self.assertIn("exposed (trains)",
                      next(ln for ln in zone_only.splitlines()
                           if ln.startswith("|") and "vendor/model:free |" in ln))
        self.assertEqual(self.pick_of(zone_only), self.pick_of(flagged))

    def pick_of(self, out):
        tail = out.split("default pick", 1)[1]
        return tail.splitlines()[0]

    def test_the_run_header_names_the_zone_and_its_regime(self):
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            zones=self.zone_of("sensitive"))
        self.assertIsNone(code)
        self.assertIn(f"zone: {self._tmp.name} (sensitive)", out)

    def test_sensitive_flag_is_shown_as_the_effective_posture_in_every_header(self):
        zones = self.zone_of("open")
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--working-dir",
            self._tmp.name, zones=zones)
        self.assertIsNone(code)
        expected = f"zone: {self._tmp.name} (open; sensitive via --sensitive)"
        self.assertIn(expected, out)

        checked, _, check_code, _ = self.run_cli(
            "--check-policy", "--sensitive", "--working-dir", self._tmp.name,
            zones=zones)
        self.assertIsNone(check_code)
        self.assertIn(expected, checked)

        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        guarded, _, guard_code, _ = self.guard(
            "deepseek/deepseek-v4-pro", sensitive=True, zones=zones)
        self.assertEqual(guard_code, 5)
        self.assertIn(expected, guarded)

    def test_an_undeclared_folder_reports_undeclared_and_closed(self):
        out, _, code, _ = self.run_cli("--domain", "writing",
                                       zones_default="closed")
        self.assertIsNone(code)
        self.assertIn("zone: undeclared (closed)", out)

    # --- Header truth: the quota line answers to the zone (issue #38) ----

    def test_a_fresh_world_header_never_claims_free_routes_stayed(self):
        # AC1: no key and no zones file - the closed default has already
        # removed every remote Free route at source, so the quota line must
        # not say they stayed in the pool. Both header lines are pinned
        # together: the zone states the judgement, the pool clause answers
        # for it instead of contradicting it.
        self.free_risk_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))

        out, _, code, _ = self.run_cli("--domain", "writing", world=world,
                                       zones_absent=True)

        self.assertIsNone(code)
        lines = out.splitlines()
        zone_line = next(ln for ln in lines if ln.startswith("zone: "))
        quota_line = next(ln for ln in lines if ln.startswith("free quota: "))
        self.assertEqual(zone_line, "zone: undeclared (closed)")
        self.assertEqual(
            quota_line,
            "free quota: unavailable | :free routes excluded by the closed zone")
        self.assertNotIn("stay in the pool", out)
        # The claim is true: the zone removed the route before the table.
        self.assertNotIn("vendor/model:free", out)

    def test_an_absent_zones_file_gets_one_advisory_after_the_zone_header(self):
        # AC2: a missing zones file has never had a line of its own - the
        # loader returns the closed default in silence. One line now, right
        # under the zone header, naming the path to create as the default
        # machine spells it (~/.config against the config-dir constants).
        out, _, code, _ = self.run_cli("--domain", "writing", zones_absent=True)

        self.assertIsNone(code)
        lines = out.splitlines()
        zone_at = next(i for i, ln in enumerate(lines)
                       if ln.startswith("zone: "))
        self.assertEqual(
            lines[zone_at + 1],
            "zones file: absent (~/.config/modelbandit/zones.json) — "
            "undeclared paths are closed")
        self.assertEqual(out.count("zones file:"), 1)

    def test_a_present_zones_file_keeps_the_whole_output_byte_identical(self):
        # AC2 golden: zones.json present -> not one byte moves: no
        # advisory line, no reworded pool claim. The fixture machine
        # declares open, where free routes genuinely remain in the pool.
        out, _, code, _ = self.run_cli("--domain", "writing")

        self.assertIsNone(code)
        self.assertEqual(out, PRESENT_ZONES_GOLDEN)

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
        # stays marked in the table, never hidden.
        self.sensitive_policy({"deepseek/deepseek-v4-pro-0813": "trains"})
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--working-dir", self._tmp.name,
            zones=self.zone_of("closed"))
        self.assertIsNone(code)
        self.assertIn("| admit |", out)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "deepseek/deepseek-v4-pro-0813 |" in ln)
        self.assertIn("exposed (trains)", row)
        self.assertNotIn("default pick (top of task order): "
                         "deepseek/deepseek-v4-pro-0813", out)

    # --- pre-flight: --assert-allowed -----------------------------------

    def guard(self, model, *, zones=None, zones_default="open", sensitive=False,
              plain=False, policy_path=None, working_dir=None):
        argv = ["--assert-allowed", "--model", model,
                "--working-dir", working_dir or self._tmp.name]
        if sensitive:
            argv.append("--sensitive")
        if plain:
            argv.append("--plain")
        return self.run_cli(*argv, zones=zones, zones_default=zones_default,
                            policy_path=policy_path)

    def test_assert_allowed_admits_a_paid_route_in_a_closed_zone(self):
        out, _, code, calls = self.guard("deepseek/deepseek-v4-pro",
                                         zones=self.zone_of("closed"))
        self.assertEqual(code, 0)
        self.assertIn(f"zone: {self._tmp.name} (closed)", out)
        self.assertIn("allowed: deepseek/deepseek-v4-pro", out)
        self.assertEqual(calls, [])          # no board, no classification fetch

    def test_assert_allowed_blocks_a_remote_free_route_in_a_closed_zone(self):
        for model in ("vendor/model:free", "opencode/glm-5.3-flash"):
            with self.subTest(model=model):
                out, _, code, calls = self.guard(model,
                                                 zones=self.zone_of("closed"))
                self.assertEqual(code, 5)
                self.assertIn("blocked", out)
                self.assertIn("blocked by the free-use zone", out)
                self.assertIn(f"zone: {self._tmp.name} (closed)", out)
                self.assertIn(self._tmp.name, out)   # the zone is named
                self.assertEqual(calls, [])

    def test_assert_allowed_blocks_an_exposed_paid_route_in_a_sensitive_zone(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     zones=self.zone_of("sensitive"))
        self.assertEqual(code, 5)
        self.assertIn("exposed (trains)", out)

    def test_assert_allowed_blocks_an_exposed_paid_route_in_a_closed_zone(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     zones=self.zone_of("closed"))
        self.assertEqual(code, 5)
        self.assertIn("exposed (trains)", out)

    def test_an_unstated_shape_is_sensitive_and_the_output_says_so(self):
        # The dispatch contract fails closed: an unstated shape means
        # Sensitive, so a route that retains training data is refused by
        # default and the output states the shape it assumed.
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     zones=self.zone_of("open"))
        self.assertEqual(code, 5)
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
        self.assertEqual(code, 5)
        self.assertIn("remote free route is prohibited", out)
        self.assertIn("shape: plain (via --plain)", out)

    def test_sensitive_restatement_is_accepted_with_the_same_verdict(self):
        self.sensitive_policy({"deepseek/deepseek-v4-pro": "trains"})
        out, _, code, _ = self.guard("deepseek/deepseek-v4-pro",
                                     sensitive=True,
                                     zones=self.zone_of("open"))
        self.assertEqual(code, 5)
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
        _, _, code, calls = self.guard("vendor/model:free",
                                       zones=self.zone_of("closed"),
                                       policy_path=absent)
        self.assertEqual(code, 5)
        self.assertEqual(calls, [])

        out, err, code, calls = self.guard("deepseek/deepseek-v4-pro",
                                           zones=self.zone_of("closed"),
                                           policy_path=absent)
        self.assertEqual(code, 0)
        self.assertIn("allowed: deepseek/deepseek-v4-pro", out)
        self.assertEqual(err, "")
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

    def test_assert_allowed_treats_an_undeclared_folder_as_closed(self):
        out, _, code, _ = self.guard("vendor/model:free", zones_default="closed")
        self.assertEqual(code, 5)
        self.assertIn("zone: undeclared (closed)", out)

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
        # in a closed regime exactly as the plan's source filter does.
        pol = json.loads(json.dumps(POLICY))
        model = "qwen/qwen3-coder-30b:free"
        pol["free_models"] = {"qwen/qwen3-coder-30b": {
            "context_length": 262_144, "exposure": "local"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        out, _, code, _ = self.guard(model,
                                     zones=self.zone_of("closed"))
        self.assertEqual(code, 5)
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
                                         zones=[{"path": open_dir,
                                                 "free": "open"},
                                                {"path": closed_dir,
                                                 "free": "closed"}],
                                         working_dir=link)

        self.assertEqual(code, 5)
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
                                     zones=[{"path": open_dir,
                                             "free": "open"}],
                                     working_dir=link)

        self.assertEqual(code, 0)
        self.assertIn(f"zone: {open_dir} (open)", out)
        self.assertIn("allowed: vendor/model:free", out)

    def test_pre_flight_names_the_resolved_place_of_a_declared_link(self):
        # A declaration spelled through a link governs the place it reaches,
        # and the header says so instead of the link's spelling.
        target = os.path.join(self._tmp.name, "free-zone")
        os.makedirs(target)
        link = self.link(os.path.join(self._tmp.name, "free-link"), target)

        out, _, code, _ = self.guard("vendor/model:free", plain=True,
                                     zones=[{"path": link, "free": "open"}],
                                     working_dir=link)

        self.assertEqual(code, 0)
        self.assertIn(f"zone: {target} (open) (declared: {link})", out)
        self.assertIn("allowed: vendor/model:free", out)

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
            zones=[{"path": open_dir, "free": "open"},
                   {"path": closed_dir, "free": "closed"}])

        self.assertIsNone(code)
        self.assertIn(f"zone: {closed_dir} (closed)", out)
        self.assertNotIn("vendor/model:free", out)
        self.assertNotIn("| admit |", out)

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
        pol["free_models"] = {"qwen/qwen3-coder": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = build_world()
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "qwen/qwen3-coder-30b", "tag_usage_share": 0.5})
        out, _, code, _ = self.run_cli(
            "--domain", "writing", world=world,
            local_models={"qwen/qwen3-coder-30b":
                          {"id": "qwen/qwen3-coder-30b"}})
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
        self.assertIn("default pick (top of task order): deepseek/deepseek-v4-pro-0813", out)
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

    def test_budget_over_exits_2(self):
        out, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "2",
                                       "--budget", "0.1")
        self.assertEqual(code, 2)
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

    def test_over_budget_still_exits_2_at_an_accepted_boundary(self):
        _, _, code, _ = self.run_cli("--domain", "writing", "--tickets", "2",
                                     "--budget", "0.1", "--cached-share", "0")
        self.assertEqual(code, 2)

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
        self.assertIn("default pick (top of task order): vendor/model:free", out)

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
        self.assertIn("default pick (top of task order): vendor/model:free", out)

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
        self.assertIn(":free routes stay in the pool", err)
        self.assertIn("free quota: unavailable", out)
        self.assertIn("default pick (top of task order): vendor/model:free", out)

    def test_check_policy_plans_no_tickets_and_reads_no_counter(self):
        _, err, code, calls = self.run_cli("--check-policy")

        self.assertIsNone(code)
        self.assertFalse(any(name == "key.json" for _, name, *_ in calls))
        self.assertNotIn("free quota", err)

    def test_deal_can_send_all_tickets_to_free_when_paid_candidates_are_inadmissible(self):
        pol = json.loads(json.dumps(POLICY))
        pol["exposure"] = {"deepseek/": "trains"}
        pol["free_models"] = {"vendor/model": {
            "context_length": 262_144, "exposure": "no-retention",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "12",
            "--deal", "--seed", "all-free-valid",
            world=self.free_world(("vendor/model:free", 0.5)))

        self.assertIsNone(code)
        self.assertIn("vendor/model:free", out)
        deal = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn("vendor/model:free", deal)
        self.assertIn("free share: 12/12 tickets (100%)", out)
        self.assertNotIn("deepseek/deepseek-v4-pro |", deal)


class PolicyFileTests(CliTests):
    """One policy loader: every entry point reads the policy file the same
    way, as UTF-8, and a policy that cannot be read or trusted is a
    policy/config error (status 4) — never a locale-dependent mangle, never
    an uncaught traceback, never a Secrets-gate verdict (1)."""

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
        a message naming the file — no traceback, no exit 1."""
        for argv in (["--domain", "writing"],           # the ranking run
                     ["--check-policy"],                # the policy check
                     ["--assert-allowed",
                      "--model", "deepseek/deepseek-v4-pro"],
                     ["--check-secrets",
                      "--model", "deepseek/deepseek-v4-pro"]):
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

        out, err, code, _ = self.run_gate("--check-secrets",
                                          "--model", "deepseek/deepseek-v4-pro")
        self.assertEqual(code, 4)
        self.assertNotIn("secrets gate: sensitive", out)
        self.assertIn("secrets gate: rules/config error", err)
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

        out, err, code, _ = self.run_gate("--check-secrets",
                                          "--model", "deepseek/deepseek-v4-pro")
        self.assertEqual(code, 4)
        self.assertNotIn("secrets gate: sensitive", out)
        self.assertIn("secrets gate: rules/config error", err)
        self.assertIn("unknown exposure", err)


if __name__ == "__main__":
    unittest.main()
