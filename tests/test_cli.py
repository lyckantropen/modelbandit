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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
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
    "hints": {"deepseek/deepseek-v4-pro": "skipped on output cost"},
    "summaries": {"deepseek/deepseek-v4-pro-0813": "eol sibling summary",
                  "deepseek/deepseek-v4-pro": "eol summary"},
    "domains": {
        "writing": ["content_writing", "roleplay_fiction", "gone_tag"],
        "coding": ["math"],
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

    def run_cli(self, *argv, world=None):
        world = world if world is not None else build_world()
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

    def test_delta_against_baseline(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        # baseline = 12000*4.35e-7 + 8000*3.6e-9 + 12000*8.7e-7 = 0.0156888
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
        block = out[out.index("summaries (context only"):]
        aug = next(ln for ln in block.splitlines() if "v4-pro-0813" in ln)
        apr = next(ln for ln in block.splitlines()
                   if ln.strip().startswith("deepseek/deepseek-v4-pro:"))
        self.assertIn("eol sibling summary", aug)
        self.assertIn("eol summary", apr)

    def test_summaries_absent_when_no_match(self):
        out, _, _, _ = self.run_cli("--domain", "coding")
        self.assertNotIn("summaries (context only", out)

    def test_default_pick_and_route_to_floor(self):
        out, _, _, _ = self.run_cli("--domain", "writing")
        self.assertIn("default pick (rank 1): deepseek/deepseek-v4-pro-0813", out)
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
