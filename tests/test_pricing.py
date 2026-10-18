"""Unit tests for price arithmetic, endpoint spread pricing, effort
multipliers, and user hints."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bind  # noqa: E402


class PerMillionTests(unittest.TestCase):
    def test_converts_per_token_price(self):
        self.assertEqual(bind.per_million("0.000002"), 2.0)

    def test_zero(self):
        self.assertEqual(bind.per_million("0"), 0.0)


class BlendedFromPricingTests(unittest.TestCase):
    def test_uncached_input_and_output(self):
        p = {"prompt": "0.000002", "completion": "0.00001"}
        # 1000 * 2e-6 + 500 * 1e-5 = 0.002 + 0.005
        self.assertAlmostEqual(
            bind.blended_from_pricing(p, 1000, 500, 0.0, 1.0), 0.007)

    def test_cached_share_uses_cache_read_price(self):
        p = {"prompt": "0.000002", "completion": "0.00001",
             "input_cache_read": "0.0000001"}
        # 500 * 2e-6 + 500 * 1e-7 + 500 * 1e-5 = 0.001 + 0.00005 + 0.005
        self.assertAlmostEqual(
            bind.blended_from_pricing(p, 1000, 500, 0.5, 1.0), 0.00605)

    def test_missing_cache_read_falls_back_to_prompt(self):
        p = {"prompt": "0.000002", "completion": "0.00001"}
        self.assertAlmostEqual(
            bind.blended_from_pricing(p, 1000, 500, 0.5, 1.0), 0.007)

    def test_multiplier_applies_to_output_only(self):
        p = {"prompt": "0.000002", "completion": "0.00001",
             "input_cache_read": "0.0000001"}
        # 0.00605 with mult 1 -> out doubles: 0.001 + 0.00005 + 0.01
        self.assertAlmostEqual(
            bind.blended_from_pricing(p, 1000, 500, 0.5, 2.0), 0.01105)

    def test_zero_cached_share_ignores_cache_read(self):
        p = {"prompt": "0.000002", "completion": "0.00001",
             "input_cache_read": "0.0000001"}
        self.assertAlmostEqual(
            bind.blended_from_pricing(p, 1000, 500, 0.0, 1.0), 0.007)


class PriceModelTests(unittest.TestCase):
    PRICING = {"prompt": "0.000002", "completion": "0.00001",
               "input_cache_read": "0.0000001"}

    def test_without_endpoints_all_bases_agree(self):
        model = {"pricing": self.PRICING}
        pr = bind.price_model(model, [], 1000, 500, 0.5, 1.0)
        self.assertEqual(pr["n_eps"], 0)
        self.assertAlmostEqual(pr["worst"], 0.00605)
        self.assertAlmostEqual(pr["primary"], 0.00605)
        self.assertAlmostEqual(pr["best"], 0.00605)
        self.assertEqual(pr["out_min"], 10.0)
        self.assertEqual(pr["out_max"], 10.0)
        self.assertIsNone(pr["worst_ep"])
        self.assertIsNone(pr["best_ep"])

    def test_endpoints_set_worst_best_and_names(self):
        model = {"pricing": self.PRICING}
        eps = [
            {"name": "Cheap", "pricing": {"prompt": "0.000001",
                                          "completion": "0.000002",
                                          "input_cache_read": "0"}},
            {"name": "Pricey", "pricing": {"prompt": "0.000001",
                                           "completion": "0.00008",
                                           "input_cache_read": "0"}},
            {"name": "Mid", "pricing": {"prompt": "0.000001",
                                        "completion": "0.00001",
                                        "input_cache_read": "0"}},
        ]
        pr = bind.price_model(model, eps, 1000, 500, 0.5, 1.0)
        self.assertEqual(pr["n_eps"], 3)
        self.assertEqual(pr["worst_ep"], "Pricey")
        self.assertEqual(pr["best_ep"], "Cheap")
        # input is half-uncached: 500 * prompt for either endpoint
        self.assertAlmostEqual(pr["worst"], 500 * 0.00008 + 500 * 0.000001)
        self.assertAlmostEqual(pr["best"], 500 * 0.000002 + 500 * 0.000001)
        # primary stays the models-list figure regardless of endpoints
        self.assertAlmostEqual(pr["primary"], 0.00605)
        self.assertEqual(pr["out_min"], 2.0)
        self.assertEqual(pr["out_max"], 80.0)

    def test_output_range_spans_endpoints(self):
        model = {"pricing": self.PRICING}
        eps = [{"name": "A", "pricing": {"prompt": "0", "completion": "0.0000004",
                                         "input_cache_read": "0"}},
               {"name": "B", "pricing": {"prompt": "0", "completion": "0.000008",
                                         "input_cache_read": "0"}}]
        pr = bind.price_model(model, eps, 1, 1, 0.0, 1.0)
        self.assertAlmostEqual(pr["out_min"], 0.4)
        self.assertAlmostEqual(pr["out_max"], 8.0)


FULL = ["none", "low", "medium", "high", "xhigh", "max"]
BINARY = ["none", "thinking"]


class EffortMultiplierTests(unittest.TestCase):
    """The output multiplier a ladder earns per intent: a full ladder prices
    the table exactly; a rung short of the intent's share of the effort scale
    discounts toward glance's, never past it in either direction."""

    def test_full_ladder_prices_the_table_at_every_intent(self):
        for intent in bind.INTENTS:
            self.assertEqual(bind.effort_multiplier(FULL, intent),
                             bind.EFFORT_MULTIPLIERS[intent])

    def test_binary_ladder_collapses_toward_glance(self):
        # `thinking` is rung index 1 = 1/3 of the four-level effort scale.
        # measured targets 1/2: 0.6 + (1.0-0.6)*((1/3)/(1/2)) = 13/15
        self.assertAlmostEqual(bind.effort_multiplier(BINARY, "measured"),
                               13 / 15, places=12)
        # thorough targets 3/4: 0.6 + (2.5-0.6)*((1/3)/(3/4)) = 13/9
        self.assertAlmostEqual(bind.effort_multiplier(BINARY, "thorough"),
                               13 / 9, places=12)
        # exhaustive targets 1: 0.6 + (6.0-0.6)*((1/3)/1) = 2.4
        self.assertAlmostEqual(bind.effort_multiplier(BINARY, "exhaustive"),
                               2.4, places=12)

    def test_glance_never_collapses(self):
        for ladder in (FULL, BINARY, ["default"]):
            self.assertEqual(bind.effort_multiplier(ladder, "glance"), 0.6)

    def test_single_rung_ladder_stays_at_glance(self):
        # A one-rung ladder delivers rung 0 of the effort scale: nothing above
        # glance, at any intent.
        for intent in bind.INTENTS:
            self.assertEqual(bind.effort_multiplier(["default"], intent), 0.6)

    def test_collapsed_multiplier_never_leaves_glance_intent_bounds(self):
        for intent in bind.INTENTS:
            m = bind.effort_multiplier(BINARY, intent)
            self.assertGreaterEqual(m, bind.EFFORT_MULTIPLIERS["glance"])
            self.assertLessEqual(m, bind.EFFORT_MULTIPLIERS[intent])

    def test_collapsed_rung_prices_strictly_below_full_ladder(self):
        for intent in ("measured", "thorough", "exhaustive"):
            self.assertLess(bind.effort_multiplier(BINARY, intent),
                            bind.effort_multiplier(FULL, intent))


class HintForTests(unittest.TestCase):
    HINTS = {"z-ai/glm-5.3": "family", "z-ai/glm-5.3-flash": "flash"}

    def test_no_match(self):
        self.assertIsNone(bind.hint_for("anthropic/claude-x", self.HINTS))

    def test_empty_verdicts(self):
        self.assertIsNone(bind.hint_for("z-ai/glm-5.3-flash", {}))

    def test_exact_match(self):
        self.assertEqual(bind.hint_for("z-ai/glm-5.3", self.HINTS), "family")

    def test_prefix_match(self):
        self.assertEqual(bind.hint_for("z-ai/glm-5.3-prime", self.HINTS),
                         "family")

    def test_longest_prefix_wins(self):
        self.assertEqual(bind.hint_for("z-ai/glm-5.3-flash", self.HINTS),
                         "flash")
        self.assertEqual(bind.hint_for("z-ai/glm-5.3-flash-20260826", self.HINTS),
                         "flash")


if __name__ == "__main__":
    unittest.main()
