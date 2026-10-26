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
                      "window: 0.00T tokens, 0/30 days",
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
                      "window: 0.00T tokens, 1/30 days", ghost)

    def test_stale_bullets_carry_absent_phrase_and_keep_the_note(self):
        out, _, _, _ = self.run_cli("--scope")
        stale = out[out.index("## Stale summaries"):out.index("## Stale signals")]
        self.assertIn("- stale/model — not in model list", stale)
        self.assertIn("  ranks: absent from all 4 tags and all 2 domains",
                      stale)
        self.assertIn("  catalog: not in model list, "
                      "window: 0.00T tokens, 0/30 days", stale)

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
                      "window: 5.50T tokens, 2/30 days",
                      " ".join(stale.split()))
        sig = out[out.index("## Stale signals"):out.index("## Signal coverage gaps")]
        self.assertIn("- acme/ten", sig)
        self.assertIn("  ranks: writing #10/10", sig)

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
