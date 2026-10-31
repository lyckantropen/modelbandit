"""Plan is inert by construction: pool assembly never emits a plan candidate.

The classifier knows the plan kind (`opencode-go/*`) and the facet table
spells its column, but no plan economics exist yet - so no pool-assembly
path may fabricate a plan candidate. Assembly builds its pools from three
channels only - the OpenRouter market rows (models list and boards), the
curated free catalog, and the local probe - and none of them can make an
`opencode-go/*` id a candidate:

- the free catalog refuses plan-kind entries at load (pinned by
  test_free_catalog_kinds.py), and the free merge drops a plan prefix even
  when a raw, unvalidated dict tries to feed it one;
- a board may name an `opencode-go/*` id - the traffic feed is OpenRouter's
  and the plan namespace is not an OpenRouter serving, so the models list
  carries no such model. An unresolved model never plays: it drops before
  any pool or the deal is built. Even when a models list does carry the id
  (a fixture can supply one; OpenRouter's own never will), the pool builders
  drop the plan kind outright and the catalog gate refuses the plan row - no
  plan catalog exists to satisfy its needs-catalog facet - so the id still
  reaches no pool, no admission and no deal;
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


def board(*models):
    return {"as_of": "2026-10-17", "classifications": [
        {"tag": "content_writing", "usage_share": 1.0, "models": [
            {"id": mid, "tag_usage_share": share}
            for mid, share in models]}]}


def deal_parameters(scores):
    return modelbandit.DealParameters(
        blend_weight=0.6, top_k=5, seed="plan-inert", tickets=12,
        fit_adjusted_task_scores=scores,
        admitted=frozenset(scores))


class PlanNeverEntersThePoolTests(unittest.TestCase):
    """The pool builders' output: market, free-catalog and local rows only."""

    def test_a_board_named_plan_id_drops_before_the_pools_and_the_deal(self):
        # The board names the plan id with the biggest share; the models list
        # (OpenRouter's catalog of what it serves) carries no such model. The
        # id stays visible as an unresolved board row, but no pool and no
        # deal is built from it.
        classif = board((PLAN, 0.6), (MARKET, 0.4))
        models = {MARKET: market_model()}
        share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                            models, {})
        self.assertIn(PLAN, share)

        pool = modelbandit.eligibility_pool(share, models, {}, 5)
        self.assertEqual([mid for mid, _ in pool], [MARKET])
        paid = modelbandit.paid_pool(share, models, set(), 5)
        self.assertEqual([mid for mid, _ in paid], [MARKET])
        rows = modelbandit.plan_deal(
            share, models, {}, deal_parameters({MARKET: 1.0}))
        self.assertEqual([row["mid"] for row in rows], [MARKET])

    def test_the_plan_id_cannot_sneak_in_through_the_model_list(self):
        # The same assembly with the plan id absent from the board entirely:
        # nothing reintroduces it from the models side either.
        classif = board((MARKET, 1.0))
        models = {MARKET: market_model(), PLAN: market_model(PLAN)}
        share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                            models, {})
        self.assertNotIn(PLAN, share)

    def test_a_plan_id_the_model_list_carries_never_pools_admits_or_deals(self):
        # Belt and braces: even with the board AND the models list both
        # carrying the plan id, it stays only a named, visible share row.
        # The pool builders drop the plan kind (a plan-shaped id this
        # machine serves is a local row - the seam's precedence), and the
        # catalog gate refuses the plan row because no plan catalog exists
        # to satisfy its needs-catalog facet: never in any pool, never
        # admitted, never dealt.
        classif = board((PLAN, 0.6), (MARKET, 0.4))
        models = {MARKET: market_model(), PLAN: market_model(PLAN)}
        share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                            models, {})
        self.assertIn(PLAN, share)

        pool = modelbandit.eligibility_pool(share, models, {}, 5)
        self.assertEqual([mid for mid, _ in pool], [MARKET])
        paid = modelbandit.paid_pool(share, models, set(), 5)
        self.assertEqual([mid for mid, _ in paid], [MARKET])
        parameters = modelbandit.DealParameters(
            blend_weight=0.6, top_k=5, seed="plan-inert", tickets=12,
            fit_adjusted_task_scores={MARKET: 1.0, PLAN: 1.0},
            admitted=frozenset({MARKET, PLAN}))
        rows = modelbandit.plan_deal(share, models, {}, parameters)
        self.assertEqual([row["mid"] for row in rows], [MARKET])

        facts = modelbandit.candidate_for(PLAN, {})
        self.assertFalse(facts.cataloged)
        decision = modelbandit.admit(modelbandit.Shape(), facts)
        self.assertFalse(decision.admitted)
        self.assertIn("requires a policy catalog entry", decision.reason)

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
        # that serves an `opencode-go/*`-shaped id offers a LOCAL candidate,
        # never a plan one.
        served = {PLAN: {"id": PLAN, "context_length": 8192}}
        free_models = {PLAN: {"context_length": 8192, "exposure": "local",
                              "summary_ref": "s"}}
        share, models = modelbandit.merge_local_candidates(
            {}, {}, served, free_models)
        self.assertIn(PLAN, share)
        facts = modelbandit.candidate_for(
            PLAN, {"free_models": free_models}, local=True)
        self.assertTrue(facts.is_free)
        self.assertTrue(facts.local)
        self.assertEqual(facts.exposure, "local")
        self.assertEqual(modelbandit.classify_route(PLAN, local=True), "local")

    def test_a_served_plan_shaped_id_without_a_local_entry_is_ignored(self):
        # In service the catalog cannot carry a plan prefix (the load refuses
        # it), so a served plan-shaped id matches no entry and is ignored.
        served = {PLAN: {"id": PLAN, "context_length": 8192}}
        share, models = modelbandit.merge_local_candidates({}, {}, served, {})
        self.assertNotIn(PLAN, share)
        self.assertNotIn(PLAN, models)


class PlanNeverReachesTheDealCliTests(unittest.TestCase):
    """The deal output itself: no `opencode-go/*` row, whatever the board."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        with open(self.policy_path, "w") as f:
            json.dump({
                "baseline": {"id": "xiaomi/mimo-v2.6-pro"},
                "summaries": {},
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
            json.dump({"zones": [], "default": "open"}, f)
        self.config_home = config_home

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_deal_never_draws_a_board_named_plan_id(self):
        world = {
            "models": [market_model()],
            "classifications": board((PLAN, 0.9), (MARKET, 0.1)),
            "rankings": {"data": []},
            "endpoints": {},
            "benchmarks": {"meta": {"as_of": "2026-10-26T00:01:10.159Z",
                                    "source": None, "citation": None,
                                    "model_count": 1},
                           "data": []},
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
            if cache_name == "benchmarks.json":
                return world["benchmarks"]
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
        self.assertNotIn(PLAN, deal_block)
        self.assertIn(MARKET, deal_block)
        self.assertIn("default pick (top of task order): " + MARKET, printed)


if __name__ == "__main__":
    unittest.main()
