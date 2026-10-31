"""Plan rows enter the pool at split family share.

A plan serving never resolves in OpenRouter's models list — the namespace is
not an OpenRouter serving — so no assembly path built from the market rows,
the Free catalog or the local probe can carry it. The validated `plans`
policy section is its one catalog: the assembly step joins a cataloged plan
row with the minimal record the table and the gates honestly consume (the $0
cash price within its Allowance; no per-1M market price, no endpoint spread,
no context window), the pools' plan filters release for the rows that section
catalogs, and the catalog gate asks it instead of refusing every plan id. An
uncataloged plan id still refuses with the catalog reason, and the Free
catalog keeps refusing plan entries (test_free_catalog_kinds.py).

Popularity is the family's: a family served twice — its metered twin and its
plan serving — divides its board share across the two full-quality rows, so
the family's standing is counted once and the plan row carries no surrogate
discount. The Free catalog's `free_share_inheritance` discount keeps its
current numbers.

Fixture style follows test_plan_inert.py: plain dicts, no network. The
whole-run cases below reuse test_cli's CLI lifecycle (an injected fetch
recorder, patched probe/cache/env, captured output); their scenario
fixtures — ids, plan entries, boards — stay this suite's own.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
import modelbandit  # noqa: E402
import test_cli  # noqa: E402

PLAN = "opencode-go/deepseek-v4-pro"
TWIN = "deepseek/deepseek-v4-pro"
OTHER = "z-ai/glm-5.3"
GHOST = "opencode-go/ghost-model"
FREE = "opencode/deepseek-v4-pro"


def market_model(mid=TWIN):
    return {"id": mid, "supported_parameters": ["reasoning_effort"],
            "pricing": {"prompt": "0.0000002", "completion": "0.000001",
                        "input_cache_read": "0"}}


def plan_entry(**overrides):
    """One plans entry: the list price (the Draw's basis), three window caps,
    the training/retention fact and an optional region opt-in."""
    entry = {"list_price": 0.5,
             "caps": {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0},
             "exposure": "no-retention"}
    entry.update(overrides)
    return entry


def board(*models):
    return {"as_of": "2026-10-17", "classifications": [
        {"tag": "content_writing", "usage_share": 1.0, "models": [
            {"id": mid, "tag_usage_share": share}
            for mid, share in models]}]}


def assemble(classif, models, plans):
    """The main run's assembly order: the board, the Free catalog, the local
    probe (no served ids here) and finally the plans catalog."""
    share, _, _ = modelbandit.domain_candidates(classif, ["content_writing"],
                                                models, {})
    share, models = modelbandit.merge_free_candidates(
        share, models, {}, {})
    return modelbandit.merge_plan_candidates(share, models, plans)


def deal_parameters(scores, top_k=5):
    return modelbandit.DealParameters(
        blend_weight=0.6, top_k=top_k, seed="plan-pool", tickets=24,
        fit_adjusted_task_scores=scores, admitted=frozenset(scores))


class FamilyIdentityTests(unittest.TestCase):
    """One helper states a serving's family: the model, not its market."""

    def test_a_plan_serving_and_its_metered_twin_are_one_family(self):
        self.assertEqual(modelbandit.family_key(PLAN),
                         modelbandit.family_key(TWIN))

    def test_a_free_slug_belongs_to_its_family(self):
        self.assertEqual(modelbandit.family_key(TWIN + ":free"),
                         modelbandit.family_key(TWIN))

    def test_another_model_is_another_family(self):
        self.assertNotEqual(modelbandit.family_key(OTHER),
                            modelbandit.family_key(TWIN))


class PlanRowAssemblyTests(unittest.TestCase):
    """The assembly step joins cataloged plan rows the models list lacks."""

    def test_a_policy_without_plans_leaves_the_assembly_untouched(self):
        # Runs without plan rows stay byte-identical: no plan entry, no
        # reshaped share and no synthesized record.
        share = {TWIN: 0.6, OTHER: 0.4}
        models = {TWIN: market_model(TWIN), OTHER: market_model(OTHER)}
        got_share, got_models = modelbandit.merge_plan_candidates(
            share, models, {})
        self.assertEqual(got_share, share)
        self.assertEqual(got_models, models)

    def test_a_family_served_twice_divides_its_board_share(self):
        # The board names the family's metered twin once; the family is
        # served twice — its metered row and its plan serving — so the
        # family's board share is divided across both and never counted
        # twice.
        share, models = assemble(board((TWIN, 0.6), (OTHER, 0.4)),
                                 {TWIN: market_model(TWIN),
                                  OTHER: market_model(OTHER)},
                                 {PLAN: plan_entry()})
        self.assertIn(PLAN, share)
        self.assertIn(PLAN, models)
        self.assertAlmostEqual(share[TWIN], 0.3)
        self.assertAlmostEqual(share[PLAN], 0.3)
        self.assertAlmostEqual(share[TWIN] + share[PLAN], 0.6)
        self.assertAlmostEqual(share[OTHER], 0.4)

    def test_a_family_with_one_full_quality_serving_keeps_the_family_share(self):
        # The only full-quality serving of its family is the plan row: no
        # surrogate discount applies — it carries the family's share whole.
        share, models = assemble(board((PLAN, 0.5), (OTHER, 0.4)),
                                 {OTHER: market_model(OTHER)},
                                 {PLAN: plan_entry()})
        self.assertAlmostEqual(share[PLAN], 0.5)
        self.assertAlmostEqual(share[OTHER], 0.4)

    def test_the_board_reporting_both_servings_still_counts_the_family_once(self):
        # Twin rows report one family's traffic, so their sum would count it
        # twice; the family's share is the largest figure the board reports
        # for it, divided across the servings.
        share, models = assemble(board((TWIN, 0.6), (PLAN, 0.2)),
                                 {TWIN: market_model(TWIN)},
                                 {PLAN: plan_entry()})
        self.assertAlmostEqual(share[TWIN], 0.3)
        self.assertAlmostEqual(share[PLAN], 0.3)
        self.assertAlmostEqual(share[TWIN] + share[PLAN], 0.6)

    def test_a_family_no_board_row_names_joins_at_zero_share(self):
        # A cataloged plan serving with no revealed popularity is visible and
        # honest: it takes no share it was never given.
        share, models = assemble(board((OTHER, 1.0)),
                                 {OTHER: market_model(OTHER)},
                                 {PLAN: plan_entry()})
        self.assertEqual(share[PLAN], 0.0)

    def test_a_locally_served_plan_shaped_id_is_not_split_as_a_plan_family(self):
        # The local serving fact outranks the id shape: a machine serving an
        # opencode-go/*-shaped id offers a local row, and the plans catalog
        # cannot turn it into a plan serving.
        share = {PLAN: 0.18}
        share, models = modelbandit.merge_plan_candidates(
            share, {}, {PLAN: plan_entry()}, local={PLAN})
        self.assertAlmostEqual(share[PLAN], 0.18)
        self.assertNotIn(PLAN, models)

    def test_a_free_family_share_keeps_its_current_numbers(self):
        # The Free discount is computed from the family's board share exactly
        # as today; a plans catalog beside it moves neither the discount nor
        # the free row's standing.
        free_models = {FREE: {"context_length": 128000, "exposure": "trains",
                              "summary_ref": "deepseek/deepseek"}}
        share, models = modelbandit.merge_free_candidates(
            {TWIN: 0.6}, {TWIN: market_model(TWIN)}, free_models,
            {"deepseek/deepseek": "a summary"}, inheritance=0.5)
        self.assertAlmostEqual(share[FREE], 0.3)
        share, models = modelbandit.merge_plan_candidates(
            share, models, {PLAN: plan_entry()})
        self.assertAlmostEqual(share[FREE], 0.3)
        self.assertAlmostEqual(share[TWIN], 0.3)
        self.assertAlmostEqual(share[PLAN], 0.3)


class PlanPoolTests(unittest.TestCase):
    """The pool choke points release for rows the plans section catalogs."""

    def setUp(self):
        self.plans = {PLAN: plan_entry()}
        self.share, self.models = assemble(
            board((TWIN, 0.6), (OTHER, 0.4)),
            {TWIN: market_model(TWIN), OTHER: market_model(OTHER)},
            self.plans)

    def test_the_eligibility_pool_plays_a_cataloged_plan_row(self):
        pool = modelbandit.eligibility_pool(self.share, self.models, {}, 5,
                                            plans=self.plans)
        self.assertIn(PLAN, [mid for mid, _ in pool])

    def test_the_balance_pool_plays_a_cataloged_plan_row(self):
        paid = modelbandit.paid_pool(self.share, self.models, set(), 5,
                                     plans=self.plans)
        self.assertIn(PLAN, [mid for mid, _ in paid])

    def test_the_deal_draws_the_cataloged_plan_row(self):
        rows = modelbandit.plan_deal(
            self.share, self.models, {},
            deal_parameters({TWIN: 2.0, PLAN: 2.0, OTHER: 1.0}),
            plans=self.plans)
        self.assertIn(PLAN, [row["mid"] for row in rows])
        self.assertEqual(sum(row["tickets"] for row in rows), 24)

    def test_an_uncataloged_plan_row_still_leaves_the_pool(self):
        # A fixture models list can carry the id (OpenRouter's never will);
        # without a plans entry no pool may play it.
        share = {PLAN: 0.6, OTHER: 0.4}
        models = {PLAN: market_model(PLAN), OTHER: market_model(OTHER)}
        pool = modelbandit.eligibility_pool(share, models, {}, 5)
        self.assertEqual([mid for mid, _ in pool], [OTHER])
        paid = modelbandit.paid_pool(share, models, set(), 5)
        self.assertEqual([mid for mid, _ in paid], [OTHER])
        rows = modelbandit.plan_deal(share, models, {},
                                     deal_parameters({PLAN: 2.0,
                                                      OTHER: 1.0}))
        self.assertEqual([row["mid"] for row in rows], [OTHER])


class PlanCatalogGateTests(unittest.TestCase):
    """The catalog gate's plan branch asks the plans section."""

    def test_a_plans_cataloged_plan_row_is_admitted(self):
        candidate = modelbandit.candidate_for(
            PLAN, {"plans": {PLAN: plan_entry()}})
        self.assertTrue(candidate.cataloged)
        self.assertTrue(modelbandit.admit(modelbandit.Shape(),
                                          candidate).admitted)

    def test_an_uncataloged_plan_row_refuses_with_the_catalog_reason(self):
        candidate = modelbandit.candidate_for(PLAN, {})
        self.assertFalse(candidate.cataloged)
        decision = modelbandit.admit(modelbandit.Shape(), candidate)
        self.assertFalse(decision.admitted)
        self.assertIn("plan route requires a plans catalog entry",
                      decision.reason)

    def test_a_plan_rows_exposure_comes_from_its_plans_entry(self):
        candidate = modelbandit.candidate_for(
            PLAN, {"plans": {PLAN: plan_entry(exposure="trains")}})
        self.assertEqual(candidate.exposure, "trains")
        sensitive = modelbandit.Shape(sensitive=True)
        self.assertFalse(modelbandit.admit(sensitive, candidate).admitted)

    def test_resolve_exposure_reads_the_plans_fact(self):
        self.assertEqual(
            modelbandit.resolve_exposure(PLAN,
                                         plans={PLAN: plan_entry(
                                             exposure="trains")}),
            "trains")

    def test_an_override_outranks_the_plans_entry(self):
        candidate = modelbandit.candidate_for(
            PLAN, {"plans": {PLAN: plan_entry(exposure="trains")},
                   "exposure": {"opencode-go/": "no-retention"}})
        self.assertEqual(candidate.exposure, "no-retention")

    def test_a_locally_served_plan_shaped_id_still_assembles_as_local(self):
        free_models = {PLAN: {"context_length": 8192, "exposure": "local",
                              "summary_ref": "s"}}
        policy = {"free_models": free_models, "summaries": {"s": "a summary"},
                  "plans": {PLAN: plan_entry(exposure="trains")}}
        candidate = modelbandit.candidate_for(PLAN, policy, local=True)
        self.assertTrue(candidate.local)
        self.assertTrue(candidate.is_free)
        self.assertTrue(candidate.cataloged)
        self.assertEqual(candidate.exposure, "local")
        self.assertTrue(modelbandit.admit(modelbandit.Shape(),
                                          candidate).admitted)


class PlanRowCliTests(unittest.TestCase):
    """The whole run: a cataloged plan row in the table and in the deal."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        # The shared CLI lifecycle (test_cli.CliTests): injected fetchers,
        # patched local probe/cache/env, captured stdout/stderr. The scenario
        # fixtures below (policy, world, plan entry) stay this suite's own.
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)

    def with_policy(self, plans):
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump({
                "baseline": {"id": TWIN},
                "summaries": {},
                "free_models": {},
                "plans": plans,
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

    def run_main(self, world):
        out, err, code, _ = self.cli.run_cli(
            "--domain", "writing", "--tickets", "12", "--deal",
            "--seed", "proj", world=world, policy_path=self.policy_path)
        self.assertIsNone(code, err)
        return out, err

    def world(self, models, classified):
        return {
            "models": models,
            "classifications": board(*classified),
            "rankings": {"data": []},
            "endpoints": {},
        }

    def test_a_cataloged_plan_row_reaches_the_table_and_the_deal(self):
        # The board names the family's metered twin and the plan serving; the
        # family's share is split across them (0.5 -> 0.25 each), and the
        # plan row carries no market price facts.
        self.with_policy({PLAN: plan_entry()})
        printed, err = self.run_main(self.world(
            [market_model(TWIN), market_model(OTHER)],
            [(TWIN, 0.5), (PLAN, 0.2), (OTHER, 0.3)]))
        plan_row = ("| 3 | opencode-go/deepseek-v4-pro | 25.00% | 0.25 | 0B | "
                    "— | $0.0000 | 0.00x | ? | no-retention | — |")
        self.assertIn(plan_row, printed)
        # A non-plan row's price cells keep their exact current shape.
        self.assertIn("| 2 | deepseek/deepseek-v4-pro | 25.00% | 0.25 | 0B | "
                      "1.00–1.00 (no endpoint data) | $", printed)
        deal_block = printed[printed.index("deal (seed"):
                             printed.index("projection at")]
        self.assertIn(PLAN, deal_block)

    def test_an_uncataloged_plan_row_still_refuses_in_the_run(self):
        self.with_policy({PLAN: plan_entry()})
        printed, err = self.run_main(self.world(
            [market_model(OTHER)], [(GHOST, 0.9), (OTHER, 0.1)]))
        self.assertIn(f" {GHOST} | 90.00% | — | 0B | "
                      "— unresolved to a priced model", printed)
        self.assertIn("plan route requires a plans catalog entry", printed)
        deal_block = printed[printed.index("deal (seed"):
                             printed.index("projection at")]
        self.assertNotIn(GHOST, deal_block)
        self.assertIn(f"default pick (top of task order): {OTHER}", printed)


if __name__ == "__main__":
    unittest.main()
