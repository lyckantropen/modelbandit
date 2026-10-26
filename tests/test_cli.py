"""CLI-level tests for main(): ranking, pricing bases, output, and exit codes.

Hand-computed expectations use the authoring profile (in=20,000 out=12,000
cached=40%, effort multiplier 1.0 at `measured`) unless stated.
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
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402


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


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        with open(self.policy_path, "w") as f:
            json.dump(POLICY, f)

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *argv, world=None, local_models=None):
        world = world if world is not None else build_world()
        local_models = local_models if local_models is not None else {}
        calls = []

        def fake_fetch(url, cache_name, *, auth, refresh):
            calls.append((url, cache_name, auth, refresh))
            if cache_name == "models.json":
                return {"data": world["models"]}
            if cache_name == "classifications.json":
                return {"data": world["classifications"]}
            if cache_name == "rankings.json":
                return world["rankings"]
            if url.endswith("/endpoints"):
                slug = url[len(bind.MODELS_URL) + 1:-len("/endpoints")]
                return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
            raise AssertionError(f"unexpected fetch: {url}")

        out, err = io.StringIO(), io.StringIO()
        code = None
        argv = ["bind.py", "--policy", self.policy_path, *argv]
        with mock.patch("bind.fetch_json", side_effect=fake_fetch), \
                mock.patch("bind.probe_local_models", return_value=local_models), \
                mock.patch.object(bind, "CACHE_DIR",
                                  os.path.join(self._tmp.name, "cache")), \
                mock.patch.object(sys, "argv", argv), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                bind.main()
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
        self.floor_policy({"vendor/model": self.FREE_CATALOG["vendor/other"]},
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
        argv = ["bind.py", "--policy", "/nonexistent/policy.json",
                "--domain", "writing"]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit):
                bind.main()

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
        absent_models = bind.probe_local_models(connection_refused)
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

    # --- Nominal floor: Free routes in the score's cost term -------------

    FREE_CATALOG = {
        "vendor/model": {"context_length": 262_144, "exposure": "no-retention",
                         "summary_ref": "deepseek/deepseek-v4-pro"},
        "vendor/other": {"context_length": 262_144, "exposure": "trains",
                         "summary_ref": "deepseek/deepseek-v4-pro"},
    }

    def floor_policy(self, free_models, alpha=1.0, beta=1.0):
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=alpha, beta=beta)
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

    def test_free_route_scores_at_the_floor_and_takes_the_pick(self):
        # Authoring profile, measured effort: the floor is 12,000 output
        # tokens at $0.01/M = $0.00012/ticket. At alpha=beta=1 the Free
        # route's score is 0.05 / 0.00012 = 416.67 against the share leader's
        # 0.05 / $0.0984 = 0.51 — free can win where fit and context allow.
        # The projected price stays $0.0000: only the cost term is shadowed.
        self.floor_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))
        out, _, code, _ = self.run_cli("--domain", "writing", world=world)
        self.assertIsNone(code)
        row = next(ln for ln in out.splitlines()
                   if ln.startswith("|") and "vendor/model:free |" in ln)
        self.assertIn("| 416.67 |", row)
        self.assertIn("$0.0000", row)
        self.assertIn("default pick (top of task order): vendor/model:free", out)

    def test_floor_is_uniform_across_exposure(self):
        # Same share, different Exposure, same floor: the score is identical.
        # Exposure decides admission, never the price.
        self.floor_policy(self.FREE_CATALOG)
        world = self.free_world(("vendor/model:free", 0.5),
                               ("vendor/other:free", 0.5))
        out, _, code, _ = self.run_cli("--domain", "writing", world=world)
        self.assertIsNone(code)
        rows = {mid: next(ln for ln in out.splitlines()
                          if ln.startswith("|") and f"{mid} |" in ln)
                for mid in ("vendor/model:free", "vendor/other:free")}
        self.assertIn("| 416.67 |", rows["vendor/model:free"])
        self.assertIn("| 416.67 |", rows["vendor/other:free"])
        self.assertIn("no-retention", rows["vendor/model:free"])
        self.assertIn("trains", rows["vendor/other:free"])

    def test_free_floor_holds_at_every_calculation_basis(self):
        # The basis moves the paid tickets the pool carries — 0813 is
        # $0.0984 worst, $0.0322 primary, $0.0064 best — and leaves the Free
        # route's cost term at the floor.
        self.floor_policy({"vendor/model": self.FREE_CATALOG["vendor/model"]})
        world = self.free_world(("vendor/model:free", 0.5))
        for basis, ticket in (("worst", "$0.0984"), ("primary", "$0.0322"),
                              ("best", "$0.0064")):
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
                                and "deepseek/deepseek-v4-pro-0813 |" in ln)
                self.assertIn("| 416.67 |", free_row)
                self.assertIn(ticket, paid_row)

    def test_served_local_route_scores_at_the_floor(self):
        # A model this machine serves is a Free route by where it runs, not by
        # its id: the score prices it at the Nominal floor like any other Free
        # route (0.05 share / $0.00012 = 416.67).
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"].update(alpha=1.0, beta=1.0)
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
        self.assertIn("| 416.67 |", row)
        self.assertIn("| local |", row)

    def test_a_floor_above_the_cheapest_paid_ticket_warns_and_continues(self):
        # A configured floor of $5/M output is $0.06/ticket at the authoring
        # profile — above the pool's cheapest paid ticket. The run warns and
        # continues with that configured value, never clamping it downward.
        pol = json.loads(json.dumps(POLICY))
        pol["scoring"]["free_floor"] = 5.0
        pol["free_models"] = {"vendor/model": self.FREE_CATALOG["vendor/model"]}
        with open(self.policy_path, "w") as f:
            json.dump(pol, f)
        world = self.free_world(("vendor/model:free", 0.5))
        out, err, code, _ = self.run_cli("--domain", "writing", world=world)
        self.assertIsNone(code)
        self.assertIn("Nominal floor", err)
        self.assertIn("default pick", out)

    def test_free_route_in_the_pool_trips_the_re_tune_verdict(self):
        # Four paid models at one price are in balance (top-1 25%, top-2 50%).
        # The same pool with a Free route at the Nominal floor is not — the
        # check says so and calls the re-tune, which is the expected drift.
        paid = [make_model(f"m{i}/model", "0.000001", "0.000002", "0.000001")
                for i in range(4)]
        board = ([{"id": "vendor/model:free", "tag_usage_share": 0.3}]
                 + [{"id": f"m{i}/model", "tag_usage_share": 0.25}
                    for i in range(4)])

        def run(with_free):
            pol = json.loads(json.dumps(POLICY))
            pol["scoring"].update(alpha=1.0, beta=1.0)
            pol["affinity"]["eligibility_top_k"] = 5
            pol["domains"] = {"writing": ["content_writing"]}
            pol["hints"] = {}
            pol["summaries"] = {}
            pol["free_models"] = ({"vendor/model":
                                   self.FREE_CATALOG["vendor/model"]}
                                  if with_free else {})
            with open(self.policy_path, "w") as f:
                json.dump(pol, f)
            world = build_world()
            world["models"] = paid + ([make_model("vendor/model:free", "0",
                                                  "0", "0")]
                                      if with_free else [])
            world["classifications"]["classifications"][0]["models"] = (
                board[1:] if not with_free else board)
            out, _, code, _ = self.run_cli("--check-policy", world=world)
            self.assertIsNone(code)
            return out

        balanced = run(False)
        self.assertIn("writing: top-1 25%, top-2 50%", balanced)
        self.assertIn("coefficient re-tune due: no", balanced)

        drifted = run(True)
        balance = drifted[drifted.index("## Score balance"):]
        self.assertIn("OUT OF BALANCE", balance)
        self.assertIn("coefficient re-tune due: yes", drifted)

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


if __name__ == "__main__":
    unittest.main()
