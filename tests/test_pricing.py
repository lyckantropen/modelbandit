"""Unit tests for price arithmetic, endpoint spread pricing, and verdicts."""

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


class VerdictForTests(unittest.TestCase):
    VERDICTS = {"z-ai/glm-5.3": "family", "z-ai/glm-5.3-flash": "flash"}

    def test_no_match(self):
        self.assertIsNone(bind.verdict_for("anthropic/claude-x", self.VERDICTS))

    def test_empty_verdicts(self):
        self.assertIsNone(bind.verdict_for("z-ai/glm-5.3-flash", {}))

    def test_exact_match(self):
        self.assertEqual(bind.verdict_for("z-ai/glm-5.3", self.VERDICTS), "family")

    def test_prefix_match(self):
        self.assertEqual(bind.verdict_for("z-ai/glm-5.3-prime", self.VERDICTS),
                         "family")

    def test_longest_prefix_wins(self):
        self.assertEqual(bind.verdict_for("z-ai/glm-5.3-flash", self.VERDICTS),
                         "flash")
        self.assertEqual(bind.verdict_for("z-ai/glm-5.3-flash-20260826", self.VERDICTS),
                         "flash")


if __name__ == "__main__":
    unittest.main()
