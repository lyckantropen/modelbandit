"""Unit tests for Free risk: the score's cost term for Free routes.

Free risk is a policy fraction (`scoring.free_risk`) of the pool's cheapest
paid ticket, applied to every Free route in the pool. It stays above zero and
below that paid ticket. Exposure does not move it: that is the Sensitive gate's
business.

Fixture style follows test_score.py: plain dicts for the policy, literal
expectations for the arithmetic.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402

FREE_RISK = 0.35
CHEAPEST_PAID = 0.02
FREE_COST = FREE_RISK * CHEAPEST_PAID

POLICY = {
    "scoring": {"alpha": 1, "beta": 1,
                "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                               "top2_max": 0.75}},
    "affinity": {"blend_weight": 0.6, "eligibility_top_k": 5,
                 "factors": {"favor_validated": 3, "favor_suspected": 2,
                             "avoid_validated": 0.3, "avoid_suspected": 0.5}},
}

FREE_MODELS = {
    "opencode/flash": {"context_length": 262_144, "exposure": "no-retention",
                       "summary_ref": "family/flash"},
    "vendor/model": {"context_length": 262_144, "exposure": "trains",
                     "summary_ref": "family/model"},
}


def with_scoring(**values):
    return {**POLICY, "scoring": {**POLICY["scoring"], **values}}


class FreeRiskPolicyTests(unittest.TestCase):
    """scoring.free_risk is configurable and strictly between zero and one."""

    def test_default_is_35_percent(self):
        self.assertEqual(bind.load_policy_config(POLICY).free_risk, 0.35)

    def test_configured_free_risk_is_read(self):
        config = bind.load_policy_config(with_scoring(free_risk=0.25))
        self.assertEqual(config.free_risk, 0.25)

    def test_free_risk_outside_open_unit_interval_fails_loudly(self):
        for value in (0, 1, -0.01, 1.01, "free", None, [],
                      float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaisesRegex(
                    SystemExit, "scoring.free_risk"):
                bind.load_policy_config(with_scoring(free_risk=value))


class NominalFloorCostTests(unittest.TestCase):
    """Free risk derives a ticket cost from the cheapest priced paid ticket."""

    def test_nominal_floor_is_free_risk_times_cheapest_paid_ticket(self):
        self.assertAlmostEqual(
            bind.nominal_floor_cost(FREE_RISK, CHEAPEST_PAID), FREE_COST)

    def test_risk_fraction_stays_below_the_paid_ticket(self):
        self.assertGreater(FREE_COST, 0.0)
        self.assertLess(FREE_COST, CHEAPEST_PAID)

    def test_effective_cost_uses_the_cheapest_paid_ticket_in_each_pool(self):
        costs = {"free-a": 0.0, "paid-a": 0.08, "paid-b": 0.02}
        effective = bind.effective_costs(costs, free_risk=FREE_RISK,
                                         free={"free-a"})
        self.assertEqual(effective["free-a"], FREE_COST)
        self.assertEqual(effective["paid-a"], 0.08)
        self.assertEqual(effective["paid-b"], CHEAPEST_PAID)

    def test_invalid_risk_fails_at_the_scoring_seam(self):
        for risk in (0, 1, -0.2, float("inf"), float("nan")):
            with self.subTest(risk=risk), self.assertRaisesRegex(
                    SystemExit, "free_risk"):
                bind.effective_costs({"free": 0.0, "paid": 0.02},
                                     free_risk=risk, free={"free"})


class FreeRouteIdsTests(unittest.TestCase):
    """Which of the pool's ids are Free routes: the serving rule, never the
    price — a Free route is what the harness serves for nothing."""

    def test_free_suffix_and_opencode_prefix_are_free_routes(self):
        self.assertEqual(
            bind.free_route_ids(["vendor/model:free", "opencode/flash",
                                 "vendor/model"], {"free_models": FREE_MODELS}),
            {"vendor/model:free", "opencode/flash"})

    def test_shared_free_route_predicate(self):
        self.assertTrue(bind.is_free_route("vendor/model:free"))
        self.assertTrue(bind.is_free_route("opencode/flash"))
        self.assertTrue(bind.is_free_route("local-coder", local=True))
        self.assertFalse(bind.is_free_route("local-coder"))

    def test_a_paid_route_is_never_a_free_route(self):
        self.assertEqual(bind.free_route_ids(["vendor/model"],
                                             {"free_models": FREE_MODELS}),
                         set())

    def test_an_unrelated_route_is_paid_whatever_it_costs(self):
        # The rule is given no prices at all: Free is a serving fact.
        self.assertEqual(bind.free_route_ids(["vendor/cheap"], {}), set())

    def test_a_locally_served_model_is_a_free_route(self):
        # A local route is Free by where it runs, not by its id: the same id
        # is a paid route when this machine is not serving it.
        self.assertEqual(bind.free_route_ids(["qwen3-coder-30b"], {},
                                             local={"qwen3-coder-30b"}),
                         {"qwen3-coder-30b"})
        self.assertEqual(bind.free_route_ids(["qwen3-coder-30b"], {}), set())


class FreeFloorScoreTests(unittest.TestCase):
    """Free's standing uses its risk-priced ticket, never zero cost."""

    def test_raising_free_risk_lowers_free_standing_monotonically(self):
        cheap_risk_cost = bind.nominal_floor_cost(0.2, 0.02)
        high_risk_cost = bind.nominal_floor_cost(0.6, 0.02)
        cheap_risk_score = bind.task_score(0.01, cheap_risk_cost, 0.7, 1.0)
        high_risk_score = bind.task_score(0.01, high_risk_cost, 0.7, 1.0)
        self.assertGreater(cheap_risk_score, high_risk_score)

    def test_free_risk_keeps_the_cost_term_above_zero(self):
        # The cost term is the denominator: a zero there is a division by
        # zero, so a Free route always prices above it.
        eff = bind.effective_costs({"vendor/model:free": 0.0, "paid": 0.02},
                                   free_risk=FREE_RISK,
                                   free={"vendor/model:free"})
        score = bind.task_score(0.01, eff["vendor/model:free"], 0.7, 1.0)
        self.assertEqual(eff["vendor/model:free"], FREE_COST)
        self.assertTrue(math.isfinite(score))


if __name__ == "__main__":
    unittest.main()
