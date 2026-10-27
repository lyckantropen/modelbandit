"""Unit tests for price arithmetic, endpoint spread pricing, effort
multipliers, and user hints."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


class PerMillionTests(unittest.TestCase):
    def test_converts_per_token_price(self):
        self.assertEqual(modelbandit.per_million("0.000002"), 2.0)

    def test_zero(self):
        self.assertEqual(modelbandit.per_million("0"), 0.0)


class BlendedFromPricingTests(unittest.TestCase):
    def test_uncached_input_and_output(self):
        p = {"prompt": "0.000002", "completion": "0.00001"}
        # 1000 * 2e-6 + 500 * 1e-5 = 0.002 + 0.005
        self.assertAlmostEqual(
            modelbandit.blended_from_pricing(p, 1000, 500, 0.0, 1.0), 0.007)

    def test_cached_share_uses_cache_read_price(self):
        p = {"prompt": "0.000002", "completion": "0.00001",
             "input_cache_read": "0.0000001"}
        # 500 * 2e-6 + 500 * 1e-7 + 500 * 1e-5 = 0.001 + 0.00005 + 0.005
        self.assertAlmostEqual(
            modelbandit.blended_from_pricing(p, 1000, 500, 0.5, 1.0), 0.00605)

    def test_missing_cache_read_falls_back_to_prompt(self):
        p = {"prompt": "0.000002", "completion": "0.00001"}
        self.assertAlmostEqual(
            modelbandit.blended_from_pricing(p, 1000, 500, 0.5, 1.0), 0.007)

    def test_multiplier_applies_to_output_only(self):
        p = {"prompt": "0.000002", "completion": "0.00001",
             "input_cache_read": "0.0000001"}
        # 0.00605 with mult 1 -> out doubles: 0.001 + 0.00005 + 0.01
        self.assertAlmostEqual(
            modelbandit.blended_from_pricing(p, 1000, 500, 0.5, 2.0), 0.01105)

    def test_zero_cached_share_ignores_cache_read(self):
        p = {"prompt": "0.000002", "completion": "0.00001",
             "input_cache_read": "0.0000001"}
        self.assertAlmostEqual(
            modelbandit.blended_from_pricing(p, 1000, 500, 0.0, 1.0), 0.007)


class PriceModelTests(unittest.TestCase):
    PRICING = {"prompt": "0.000002", "completion": "0.00001",
               "input_cache_read": "0.0000001"}

    def test_without_endpoints_all_bases_agree(self):
        model = {"pricing": self.PRICING}
        pr = modelbandit.price_model(model, [], 1000, 500, 0.5, 1.0)
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
        pr = modelbandit.price_model(model, eps, 1000, 500, 0.5, 1.0)
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
        pr = modelbandit.price_model(model, eps, 1, 1, 0.0, 1.0)
        self.assertAlmostEqual(pr["out_min"], 0.4)
        self.assertAlmostEqual(pr["out_max"], 8.0)


FULL = ["none", "low", "medium", "high", "xhigh", "max"]
BINARY = ["none", "thinking"]


class EffortMultiplierTests(unittest.TestCase):
    """The output multiplier a ladder earns per intent: a full ladder prices
    the table exactly; a rung short of the intent's share of the effort scale
    discounts toward glance's, never past it in either direction."""

    def test_full_ladder_prices_the_table_at_every_intent(self):
        for intent in modelbandit.INTENTS:
            self.assertEqual(modelbandit.effort_multiplier(FULL, intent),
                             modelbandit.EFFORT_MULTIPLIERS[intent])

    def test_binary_ladder_discounts_only_where_a_rung_is_lacked(self):
        # `measured`->default and `exhaustive`->ceiling both resolve exactly on
        # a binary ladder: the table value, no collapse.
        self.assertEqual(modelbandit.effort_multiplier(BINARY, "measured"),
                         modelbandit.EFFORT_MULTIPLIERS["measured"])
        self.assertEqual(modelbandit.effort_multiplier(BINARY, "exhaustive"),
                         modelbandit.EFFORT_MULTIPLIERS["exhaustive"])
        # `thorough`->above-default is lacking: nearest rung `thinking` (slot 1
        # of 2) -> 0.6 + (2.5-0.6)*(1/2) = 31/20
        self.assertAlmostEqual(modelbandit.effort_multiplier(BINARY, "thorough"),
                               31 / 20, places=12)

    def test_ladder_providing_every_slot_prices_unchanged(self):
        # three rungs give floor, default, above-default and (shared) ceiling:
        # nothing the intents ask for is lacking -> table values throughout
        ladder = ["low", "medium", "high"]
        for intent in modelbandit.INTENTS:
            self.assertEqual(modelbandit.effort_multiplier(ladder, intent),
                             modelbandit.EFFORT_MULTIPLIERS[intent])
            self.assertFalse(modelbandit.rung_collapsed(ladder, intent))

    def test_glance_never_collapses(self):
        for ladder in (FULL, BINARY, ["default"]):
            self.assertEqual(modelbandit.effort_multiplier(ladder, "glance"), 0.6)

    def test_single_rung_ladder_stays_at_glance(self):
        # A one-rung ladder has no effort dial: no deliberation is deliverable
        # above glance, at any intent.
        for intent in modelbandit.INTENTS:
            self.assertEqual(modelbandit.effort_multiplier(["default"], intent), 0.6)

    def test_collapsed_multiplier_never_leaves_glance_intent_bounds(self):
        for intent in modelbandit.INTENTS:
            m = modelbandit.effort_multiplier(BINARY, intent)
            self.assertGreaterEqual(m, modelbandit.EFFORT_MULTIPLIERS["glance"])
            self.assertLessEqual(m, modelbandit.EFFORT_MULTIPLIERS[intent])

    def test_collapsed_rung_prices_strictly_below_full_ladder(self):
        self.assertLess(modelbandit.effort_multiplier(BINARY, "thorough"),
                        modelbandit.EFFORT_MULTIPLIERS["thorough"])
        for intent in ("measured", "thorough", "exhaustive"):
            self.assertLess(modelbandit.effort_multiplier(["default"], intent),
                            modelbandit.effort_multiplier(FULL, intent))


class HintForTests(unittest.TestCase):
    HINTS = {"z-ai/glm-5.3": "family", "z-ai/glm-5.3-flash": "flash"}

    def test_no_match(self):
        self.assertIsNone(modelbandit.hint_for("anthropic/claude-x", self.HINTS))

    def test_empty_verdicts(self):
        self.assertIsNone(modelbandit.hint_for("z-ai/glm-5.3-flash", {}))

    def test_exact_match(self):
        self.assertEqual(modelbandit.hint_for("z-ai/glm-5.3", self.HINTS), "family")

    def test_prefix_match(self):
        self.assertEqual(modelbandit.hint_for("z-ai/glm-5.3-prime", self.HINTS),
                         "family")

    def test_longest_prefix_wins(self):
        self.assertEqual(modelbandit.hint_for("z-ai/glm-5.3-flash", self.HINTS),
                         "flash")
        self.assertEqual(modelbandit.hint_for("z-ai/glm-5.3-flash-20260826", self.HINTS),
                         "flash")


if __name__ == "__main__":
    unittest.main()
