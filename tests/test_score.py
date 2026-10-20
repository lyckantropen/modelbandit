"""Unit tests for the task-order equation and its composition with task fit.

score = share^alpha / cost^beta (free routes priced at the pool's cheapest paid
ticket); standing = score * fit/5. The exponents' ratio orders, their scale
concentrates; mass_balance is the acceptance criterion for any coefficient.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402


class TaskScoreTests(unittest.TestCase):
    def test_beta_zero_is_pure_popularity(self):
        self.assertAlmostEqual(bind.task_score(0.07, 0.0984, 1.0, 0.0), 0.07)

    def test_priced_at_cost(self):
        self.assertAlmostEqual(bind.task_score(0.07, 0.0984, 0.7, 1.0),
                               0.07 ** 0.7 / 0.0984)

    def test_higher_cost_scores_lower(self):
        self.assertGreater(bind.task_score(0.02, 0.01, 0.7, 1.0),
                           bind.task_score(0.02, 0.10, 0.7, 1.0))

    def test_alpha_flattens_popularity_dominance(self):
        sharp = bind.task_score(0.07, 0.01, 1.0, 1.0) / bind.task_score(0.02, 0.01, 1.0, 1.0)
        flat = bind.task_score(0.07, 0.01, 0.7, 1.0) / bind.task_score(0.02, 0.01, 0.7, 1.0)
        self.assertGreater(sharp, flat)


class EffectiveCostTests(unittest.TestCase):
    def test_free_priced_at_cheapest_paid(self):
        eff = bind.effective_costs({"a": 0.0, "b": 0.02, "c": 0.05})
        self.assertEqual(eff["a"], 0.02)
        self.assertEqual(eff["b"], 0.02)

    def test_all_free_gets_nominal_floor(self):
        self.assertEqual(bind.effective_costs({"a": 0.0, "b": 0.0}),
                         {"a": 1.0, "b": 1.0})


class FitTests(unittest.TestCase):
    def test_longest_prefix_wins(self):
        m = {"z-ai/glm-5.3": 3.0, "z-ai/glm-5.3-flash": 4.5}
        self.assertEqual(bind.fit_for("z-ai/glm-5.3-flash-x", m), 4.5)
        self.assertEqual(bind.fit_for("z-ai/glm-5.3-prime", m), 3.0)

    def test_unscored_is_none(self):
        self.assertIsNone(bind.fit_for("openai/gpt-6-luna", {"z-ai/glm-5.3": 3.0}))

    def test_adjusted_score_composition(self):
        self.assertAlmostEqual(bind.adjusted_score(2.0, 5.0), 2.0)
        self.assertAlmostEqual(bind.adjusted_score(2.0, None), 2.0)
        self.assertAlmostEqual(bind.adjusted_score(2.0, 2.5), 1.0)
        self.assertAlmostEqual(bind.adjusted_score(2.0, 0.0), 0.0)

    def test_parse_fit_clamps_to_0_5(self):
        self.assertEqual(bind.parse_fit("a/model=7,b/model=-1,c/model=2.5"),
                         {"a/model": 5.0, "b/model": 0.0, "c/model": 2.5})


class BalanceTests(unittest.TestCase):
    def test_mass_balance(self):
        t1, t2 = bind.mass_balance([3.0, 1.0, 1.0])
        self.assertAlmostEqual(t1, 0.6)
        self.assertAlmostEqual(t2, 0.8)

    def test_single_candidate(self):
        self.assertEqual(bind.mass_balance([2.0]), (1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
