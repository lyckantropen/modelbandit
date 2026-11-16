"""A plan serving enters the pool through its plans catalog, and only there.

The classifier knows the plan kind (`opencode-go/*`) and the facet table
spells its column. Plan economics now have one facts surface — the validated
`plans` policy section — so a plan row the section catalogs is admitted:

- the assembly step joins a board-named plan id with the minimal record the
  table and the gates consume (no market models-list row exists for it), and
  the pools' plan filters release for cataloged rows;
- no plans entry still means the pools and the deal never play this id, even
  when admit would otherwise take it — which plan routes exist is a separate
  question from whether they are served (ADR-0011);
- the free catalog still refuses plan-kind entries at load (pinned by
  test_free_catalog_kinds.py), and the free merge still drops a plan prefix
  even when a raw, unvalidated dict tries to feed it one;
- a locally served id joins through its local serving fact, which the seam
  ranks above any id shape, so a plan-shaped id served on this machine
  assembles as a local candidate, never a plan one.

Fixture style follows test_free_candidates.py and test_cli.py: plain dicts,
an injected fetch recorder, no network.
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

PLAN = "opencode-go/plan-model"
MARKET = "vendor/model"


def market_model(mid=MARKET):
    return {"id": mid, "supported_parameters": ["reasoning_effort"],
            "pricing": {"prompt": "0.0000002", "completion": "0.000001",
                        "input_cache_read": "0"}}


def plan_entry(**overrides):
    entry = {"list_price": 0.5,
             "caps": {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0},
             "exposure": "no-retention", "family_ref": MARKET}
    entry.update(overrides)
    return entry


def board(*models):
    return {"as_of": "2026-10-17", "classifications": [
        {"tag": "content_writing", "usage_share": 1.0, "models": [
            {"id": mid, "tag_usage_share": share}
            for mid, share in models]}]}


def deal_parameters(scores):
    return modelbandit.DealParameters(
        blend_weight=0.6, top_k=5, seed="plan-pool", tickets=12,
        fit_adjusted_task_scores=scores,
        admitted=frozenset(scores))


class PlanEntersThroughItsCatalogTests(unittest.TestCase):
    """The pool builders' output: market, Free, local and cataloged plan rows."""

    def test_a_board_named_plan_id_reaches_the_pools_and_the_deal(self):
        # The board names the plan id with the biggest share; OpenRouter's
        # models list carries no such model, so the assembly step joins the
        # cataloged plan row itself. The assembly joins its catalog facts,
        # so the pools and the deal can play it through the plans entry.
        plans = {PLAN: plan_entry()}
        classif = board((PLAN, 0.6), (MARKET, 0.4))
        models = {MARKET: market_model()}
        share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                            models, {})
        self.assertIn(PLAN, share)
        share, models = modelbandit.merge_plan_candidates(share, models, plans)
        self.assertIn(PLAN, models)

        pool = modelbandit.eligibility_pool(share, models, {}, 5, plans=plans)
        self.assertIn(PLAN, [mid for mid, _ in pool])
        paid = modelbandit.paid_pool(share, models, set(), 5, plans=plans)
        self.assertIn(PLAN, [mid for mid, _ in paid])
        rows = modelbandit.plan_deal(
            share, models, {}, deal_parameters({MARKET: 1.0, PLAN: 1.0}),
            plans=plans)
        self.assertIn(PLAN, [row["mid"] for row in rows])

        facts = modelbandit.candidate_for(PLAN, {"plans": plans})
        self.assertTrue(facts.cataloged)
        # Admit never refuses on completeness: a cataloged plan row is admitted
        # with its reason empty, and the pools decide its play instead.
        decision = modelbandit.admit(modelbandit.Shape(), facts)
        self.assertTrue(decision.admitted)
        self.assertEqual(decision.reason, "")

    def test_the_plan_id_cannot_sneak_in_through_the_model_list(self):
        # The same assembly with the plan id absent from the board entirely:
        # nothing reintroduces it from the models side either.
        classif = board((MARKET, 1.0))
        models = {MARKET: market_model(), PLAN: market_model(PLAN)}
        share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                            models, {})
        self.assertNotIn(PLAN, share)

    def test_a_plan_id_the_model_list_carries_still_needs_its_plans_entry(self):
        # Belt and braces: even with the board AND the models list both
        # carrying the plan id, no plans entry means no play. The pool
        # builders drop the plan kind — the plans catalog still decides which
        # plan routes exist (ADR-0011), so nothing admits a row it cannot price.
        classif = board((PLAN, 0.6), (MARKET, 0.4))
        models = {MARKET: market_model(), PLAN: market_model(PLAN)}
        share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                            models, {})
        self.assertIn(PLAN, share)

        pool = modelbandit.eligibility_pool(share, models, {}, 5)
        self.assertEqual([mid for mid, _ in pool], [MARKET])
        paid = modelbandit.paid_pool(share, models, set(), 5)
        self.assertEqual([mid for mid, _ in paid], [MARKET])
        rows = modelbandit.plan_deal(
            share, models, {},
            deal_parameters({MARKET: 1.0, PLAN: 1.0}))
        self.assertEqual([row["mid"] for row in rows], [MARKET])

        facts = modelbandit.candidate_for(PLAN, {})
        self.assertFalse(facts.cataloged)
        # The verdict is what disappears (the gate), not the requirement — no
        # plans entry still means the pools and the deal never play this id.
        decision = modelbandit.admit(modelbandit.Shape(), facts)
        self.assertTrue(decision.admitted)

    def test_a_raw_plan_catalog_prefix_cannot_enter_the_free_merge(self):
        # The load refuses a plan-kind entry (test_free_catalog_kinds.py);
        # the merge itself drops one even when a raw dict bypasses that
        # boundary, so no half-validated policy edit can price a plan route
        # from a Free record.
        entry = {"context_length": 1000, "exposure": "trains",
                 "summary_ref": "s"}
        share, models = modelbandit.merge_free_candidates(
            {}, {}, {PLAN: entry}, {"s": "fixture summary"})
        self.assertNotIn(PLAN, share)
        self.assertNotIn(PLAN, models)

    def test_a_locally_served_plan_shaped_id_assembles_as_local(self):
        # The local serving fact outranks the id shape at the seam: a machine
        # whose harness lists an `opencode-go/*`-shaped id offers a LOCAL
        # candidate, never a plan one — even when a plans entry catalogues
        # the id.
        listed = [PLAN]
        served = {PLAN: {"id": PLAN, "context_length": 8192}}
        free_models = {PLAN: {"context_length": 8192, "exposure": "local",
                              "summary_ref": "s"}}
        share, models = modelbandit.merge_local_candidates(
            {}, {}, listed, served, free_models)
        self.assertIn(PLAN, share)
        facts = modelbandit.candidate_for(
            PLAN, {"free_models": free_models, "summaries": {"s": "x"},
                   "plans": {PLAN: plan_entry(exposure="trains")}},
            local=True)
        self.assertTrue(facts.is_free)
        self.assertTrue(facts.local)
        self.assertEqual(facts.exposure, "local")
        self.assertEqual(modelbandit.classify_route(PLAN, local=True), "local")

    def test_a_listed_plan_shaped_id_without_a_local_entry_is_ignored(self):
        # In service the catalog cannot carry a plan prefix (the load refuses
        # it), so a listed plan-shaped id matches no entry and is ignored.
        listed = [PLAN]
        share, models = modelbandit.merge_local_candidates({}, {}, listed, {}, {})
        self.assertNotIn(PLAN, share)
        self.assertNotIn(PLAN, models)


class PlanReachesTheDealCliTests(unittest.TestCase):
    """The deal output itself: a cataloged `opencode-go/*` row is drawn."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        with open(self.policy_path, "w") as f:
            json.dump({
                "baseline": {"id": "xiaomi/mimo-v2.6-pro"},
                "summaries": {},
                "plans": {PLAN: plan_entry()},
                "domains": {"writing": ["content_writing"]},
                "scoring": {"alpha": 1.0, "beta": 0.0,
                            "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                                           "top2_max": 0.75}},
                "affinity": {
                    "blend_weight": 0.6,
                    "eligibility_top_k": 5,
                    "factors": {"favor_validated": 3.0,
                                "favor_suspected": 2.0,
                                "avoid_validated": 0.3,
                                "avoid_suspected": 0.5},
                },
            }, f)
        config_home = os.path.join(self._tmp.name, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": []}, f)
        self.config_home = config_home

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_deal_draws_a_board_named_plan_id_its_plans_section_catalogs(self):
        world = {
            "models": [market_model()],
            "classifications": board((PLAN, 0.9), (MARKET, 0.1)),
            "rankings": {"data": []},
            "endpoints": {},
        }
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
            if url.endswith("/endpoints"):
                slug = url[len(modelbandit.MODELS_URL) + 1:-len("/endpoints")]
                return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
            raise AssertionError(f"unexpected fetch: {url}")

        out, err = io.StringIO(), io.StringIO()
        argv = ["modelbandit", "--policy", self.policy_path, "--domain",
                "writing", "--tickets", "12", "--deal", "--seed", "proj"]
        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch), \
                mock.patch("modelbandit.probe_local_models",
                           return_value={}), \
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
        printed = out.getvalue()
        deal_block = printed[printed.index("deal (seed"):
                             printed.index("projection at")]
        self.assertIn(PLAN, deal_block)
        self.assertIn(MARKET, deal_block)
        self.assertIn("default pick (top of task order): " + PLAN, printed)


if __name__ == "__main__":
    unittest.main()
