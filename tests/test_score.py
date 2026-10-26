"""Unit tests for the task-order equation and its composition with task fit.

score = share^alpha / cost^beta (free routes priced at the Nominal floor);
standing = score * fit/5. The exponents' ratio orders, their scale
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
    """The score's cost term for one pool: Free routes at the Nominal floor,
    every paid ticket at its own price. The floor is above zero, so the term
    can never divide by zero, and below every paid ticket in the pool; a
    configured floor that breaks either bound is a loud error, never a clamp."""

    FLOOR = 0.00012  # $0.01/M output over the authoring profile's 12K out

    def test_free_route_prices_at_the_nominal_floor(self):
        eff = bind.effective_costs({"vendor/model:free": 0.0, "b": 0.02,
                                    "c": 0.05},
                                   free_floor=self.FLOOR,
                                   free={"vendor/model:free"})
        self.assertEqual(eff["vendor/model:free"], self.FLOOR)
        self.assertEqual(eff["b"], 0.02)
        self.assertEqual(eff["c"], 0.05)

    def test_paid_tickets_price_exactly_as_before(self):
        # Paid pricing is untouched: the pool's own numbers, whatever the
        # calculation basis handed in.
        for basis in ({}, {"worst": 0.0984, "primary": 0.0322,
                           "best": 0.0064}):
            with self.subTest(basis=basis):
                eff = bind.effective_costs(
                    {"vendor/model:free": 0.0, **basis},
                    free_floor=self.FLOOR, free={"vendor/model:free"})
                for mid, cost in basis.items():
                    self.assertEqual(eff[mid], cost)

    def test_free_route_prices_the_floor_at_every_calculation_basis(self):
        # worst/primary/best change the paid tickets a pool carries; the Free
        # route's cost term is the same floor under each.
        bases = {"worst": 0.0984, "primary": 0.0322, "best": 0.0064}
        for basis, ticket in bases.items():
            with self.subTest(basis=basis):
                eff = bind.effective_costs({"vendor/model:free": 0.0,
                                            "paid": ticket},
                                           free_floor=self.FLOOR,
                                           free={"vendor/model:free"})
                self.assertEqual(eff["vendor/model:free"], self.FLOOR)
                self.assertEqual(eff["paid"], ticket)

    def test_floor_stays_below_every_paid_ticket_in_the_pool(self):
        eff = bind.effective_costs({"vendor/model:free": 0.0, "b": 0.02,
                                    "c": 0.0984},
                                   free_floor=self.FLOOR,
                                   free={"vendor/model:free"})
        paid = [v for mid, v in eff.items() if mid != "vendor/model:free"]
        self.assertLess(eff["vendor/model:free"], min(paid))

    def test_all_free_pool_prices_at_the_floor(self):
        eff = bind.effective_costs({"a": 0.0, "b": 0.0},
                                   free_floor=self.FLOOR, free={"a", "b"})
        self.assertEqual(eff, {"a": self.FLOOR, "b": self.FLOOR})

    def test_floor_at_or_above_the_cheapest_paid_ticket_fails_loudly(self):
        for floor in (0.02, 0.5):
            with self.subTest(floor=floor), self.assertRaisesRegex(
                    SystemExit, "nominal floor"):
                bind.effective_costs({"vendor/model:free": 0.0, "paid": 0.02},
                                     free_floor=floor,
                                     free={"vendor/model:free"})

    def test_non_positive_or_unusable_floor_fails_loudly(self):
        for floor in (0.0, -0.01, float("inf"), float("nan")):
            with self.subTest(floor=floor), self.assertRaisesRegex(
                    SystemExit, "nominal floor"):
                bind.effective_costs({"vendor/model:free": 0.0, "paid": 0.02},
                                     free_floor=floor,
                                     free={"vendor/model:free"})

    def test_a_pool_without_a_free_route_is_unpriced_by_the_floor(self):
        # No Free route, no floor to judge: paid tickets keep their own price
        # and the pool's own fallback for a ticket that priced at nothing.
        eff = bind.effective_costs({"a": 0.0, "b": 0.02}, free_floor=0.0)
        self.assertEqual(eff, {"a": 0.02, "b": 0.02})


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
