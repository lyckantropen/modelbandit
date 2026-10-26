"""Unit tests for the Nominal floor: the score's cost term for Free routes.

The floor is a policy fact (`scoring.free_floor`, $/M output) turned into a
ticket cost for the shape, then applied to every Free route in the pool — above
zero so the cost term can never divide by zero, below every paid ticket so a
Free route wins on fit and context instead of on arithmetic. Exposure does not
move it: that is the Sensitive gate's business.

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

# The default floor over the authoring profile (12,000 output tokens,
# `measured` effort -> multiplier 1.0): 12,000 * $0.01/M = $0.00012/ticket.
FLOOR = 0.00012

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


class NominalFloorPolicyTests(unittest.TestCase):
    """scoring.free_floor is a policy fact: configurable, and an unusable
    value stops the run instead of being clamped."""

    def test_default_is_one_cent_per_million_output(self):
        self.assertEqual(bind.load_policy_config(POLICY).free_floor, 0.01)

    def test_configured_floor_is_read(self):
        config = bind.load_policy_config(with_scoring(free_floor=0.25))
        self.assertEqual(config.free_floor, 0.25)

    def test_invalid_floor_fails_loudly(self):
        for value in (0, -0.01, "free", None, [], float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaisesRegex(
                    SystemExit, "scoring.free_floor"):
                bind.load_policy_config(with_scoring(free_floor=value))


class NominalFloorCostTests(unittest.TestCase):
    """The floor rate over a shape's output: a ticket cost for the score."""

    def test_prices_output_at_the_floor_rate(self):
        self.assertAlmostEqual(bind.nominal_floor_cost(0.01, 12_000), 0.00012)

    def test_effort_multiplier_scales_the_floor(self):
        self.assertAlmostEqual(bind.nominal_floor_cost(0.01, 12_000, 6.0),
                              0.00072)

    def test_floor_sits_below_a_cheap_paid_ticket(self):
        # $1/M output is the cheap end of the paid pool; the floor is 100x
        # under it — free can win, but not by more than the policy allows.
        paid = bind.blended_from_pricing(
            {"prompt": "0.0000001", "completion": "0.000001"},
            20_000, 12_000, 0.4, 1.0)
        self.assertLess(bind.nominal_floor_cost(0.01, 12_000), paid)

    def test_no_output_tokens_prices_no_floor(self):
        self.assertEqual(bind.nominal_floor_cost(0.01, 0), 0.0)


class FreeRouteIdsTests(unittest.TestCase):
    """Which of the pool's ids are Free routes: the serving rule, never the
    price — a Free route is what the harness serves for nothing."""

    def test_free_suffix_and_opencode_prefix_are_free_routes(self):
        self.assertEqual(
            bind.free_route_ids(["vendor/model:free", "opencode/flash",
                                 "vendor/model"], {"free_models": FREE_MODELS}),
            {"vendor/model:free", "opencode/flash"})

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
    """What the floor buys: a Free route outranks the same popularity at a
    paid price, and never divides by zero."""

    def test_free_route_scores_above_the_same_share_at_a_paid_price(self):
        free = bind.task_score(0.01, FLOOR, 0.7, 1.0)
        paid = bind.task_score(0.01, 0.02, 0.7, 1.0)
        self.assertGreater(free, paid)

    def test_floor_keeps_the_cost_term_above_zero(self):
        # The cost term is the denominator: a zero there is a division by
        # zero, so a Free route always prices above it.
        eff = bind.effective_costs({"vendor/model:free": 0.0, "paid": 0.02},
                                   free_floor=FLOOR,
                                   free={"vendor/model:free"})
        score = bind.task_score(0.01, eff["vendor/model:free"], 0.7, 1.0)
        self.assertGreater(eff["vendor/model:free"], 0.0)
        self.assertTrue(math.isfinite(score))


if __name__ == "__main__":
    unittest.main()
