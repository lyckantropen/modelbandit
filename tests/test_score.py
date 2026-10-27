"""Unit tests for the task-order equation and its composition with task fit.

score = share^alpha / cost^beta (Free routes priced by Free risk);
standing = score * fit/5. The exponents' ratio orders, their scale
concentrates; mass_balance is the acceptance criterion for any coefficient.
"""

import json
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
    """Free risk times the pool's cheapest paid ticket; paid costs stay intact."""

    FREE_RISK = 0.35

    def test_free_route_prices_at_risk_fraction_of_the_cheapest_paid_ticket(self):
        eff = bind.effective_costs({"vendor/model:free": 0.0, "b": 0.02,
                                    "c": 0.05},
                                   free_risk=self.FREE_RISK,
                                   free={"vendor/model:free"})
        self.assertAlmostEqual(eff["vendor/model:free"], 0.007)
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
                    free_risk=self.FREE_RISK, free={"vendor/model:free"})
                for mid, cost in basis.items():
                    self.assertEqual(eff[mid], cost)

    def test_free_route_price_tracks_the_cheapest_paid_ticket_at_each_basis(self):
        # worst/primary/best change the paid tickets a pool carries; Free risk
        # remains a fixed fraction of the cheapest priced paid ticket.
        bases = {"worst": 0.0984, "primary": 0.0322, "best": 0.0064}
        for basis, ticket in bases.items():
            with self.subTest(basis=basis):
                eff = bind.effective_costs({"vendor/model:free": 0.0,
                                           "paid": ticket},
                                           free_risk=self.FREE_RISK,
                                           free={"vendor/model:free"})
                self.assertAlmostEqual(eff["vendor/model:free"],
                                       self.FREE_RISK * ticket)
                self.assertEqual(eff["paid"], ticket)

    def test_free_route_price_stays_below_every_paid_ticket_in_the_pool(self):
        eff = bind.effective_costs({"vendor/model:free": 0.0, "b": 0.02,
                                    "c": 0.0984},
                                   free_risk=self.FREE_RISK,
                                   free={"vendor/model:free"})
        paid = [v for mid, v in eff.items() if mid != "vendor/model:free"]
        self.assertLess(eff["vendor/model:free"], min(paid))

    def test_all_free_pool_uses_one_dollar_reference_ticket(self):
        eff = bind.effective_costs({"a": 0.0, "b": 0.0},
                                   free_risk=self.FREE_RISK, free={"a", "b"})
        self.assertEqual(eff, {"a": 0.35, "b": 0.35})

    def test_derived_nominal_floor_never_warns_against_cheapest_paid(self):
        import io
        from contextlib import redirect_stderr

        err = io.StringIO()
        with redirect_stderr(err):
            result = bind.effective_costs(
                {"vendor/model:free": 0.0, "paid": 0.02},
                free_risk=self.FREE_RISK, free={"vendor/model:free"})
        self.assertAlmostEqual(result["vendor/model:free"], 0.007)
        self.assertLess(result["vendor/model:free"], result["paid"])
        self.assertEqual(err.getvalue(), "")

    def test_a_pool_without_a_free_route_is_unpriced_by_the_floor(self):
        # No Free route, no Free risk to apply: paid tickets keep their own price
        # and the pool's own fallback for a ticket that priced at nothing.
        eff = bind.effective_costs({"a": 0.0, "b": 0.02}, free_risk=0.0)
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

    def test_parse_fit_refuses_a_non_numeric_score(self):
        # ValueError, not SystemExit: the caller reports it as the usage
        # error (status 2) it is, naming the entry.
        with self.assertRaises(ValueError) as caught:
            bind.parse_fit("mid=high")
        self.assertIn("is not a number on 0-5", str(caught.exception))
        self.assertIn("'mid=high'", str(caught.exception))

    def test_parse_fit_refuses_an_empty_value(self):
        # A trailing 'mid=' passes no guard today: float('') raises.
        with self.assertRaises(ValueError) as caught:
            bind.parse_fit("a=1,b=")
        self.assertIn("is not a number on 0-5", str(caught.exception))
        self.assertIn("'b='", str(caught.exception))

    def test_parse_fit_refuses_a_non_finite_score(self):
        # float() accepts nan/inf, but neither is a number on 0-5.
        for val in ("nan", "inf", "-inf"):
            with self.subTest(val=val):
                with self.assertRaises(ValueError):
                    bind.parse_fit(f"a={val}")


class BalanceTests(unittest.TestCase):
    def test_mass_balance(self):
        t1, t2 = bind.mass_balance([3.0, 1.0, 1.0])
        self.assertAlmostEqual(t1, 0.6)
        self.assertAlmostEqual(t2, 0.8)

    def test_single_candidate(self):
        self.assertEqual(bind.mass_balance([2.0]), (1.0, 1.0))


# A domain's candidates with two Free routes outranking every paid row: the
# case the balance criterion must stop seeing.
BALANCE_SHARE = {"vendor/free:free": 9.5, "opencode/free-model": 9.2,
                 "a/paid-1": 9.0, "b/paid-2": 4.0, "c/paid-3": 2.0,
                 "d/paid-4": 1.0}
BALANCE_MODELS = {mid: {} for mid in BALANCE_SHARE}
BALANCE_FREE = {"vendor/free:free", "opencode/free-model"}


class PaidBalancePoolTests(unittest.TestCase):
    """Score mass is measured over the paid competition: Free routes' share is
    the Free share signal's answer, never a threshold's."""

    def test_free_routes_leave_before_the_cut(self):
        # Filtering after the cut would leave one paid row here; the paid pool
        # is the top-K among paid candidates.
        pool = bind.paid_pool(BALANCE_SHARE, BALANCE_MODELS, BALANCE_FREE, 3)
        self.assertEqual([mid for mid, _ in pool],
                         ["a/paid-1", "b/paid-2", "c/paid-3"])

    def test_pool_is_popularity_ordered_and_capped(self):
        pool = bind.paid_pool(BALANCE_SHARE, BALANCE_MODELS, BALANCE_FREE, 2)
        self.assertEqual([mid for mid, _ in pool], ["a/paid-1", "b/paid-2"])

    def test_no_free_routes_leaves_the_popularity_pool_unchanged(self):
        self.assertEqual(
            bind.paid_pool(BALANCE_SHARE, BALANCE_MODELS, frozenset(), 5),
            bind.popularity_ranking(BALANCE_SHARE, BALANCE_MODELS)[:5])

    def test_all_free_pool_is_empty(self):
        self.assertEqual(bind.paid_pool(BALANCE_SHARE, BALANCE_MODELS,
                                        set(BALANCE_SHARE), 5), [])

    def test_unresolved_rows_still_never_play(self):
        share = dict(BALANCE_SHARE, **{"ghost/unresolved": 100.0})
        pool = bind.paid_pool(share, BALANCE_MODELS, BALANCE_FREE, 3)
        self.assertNotIn("ghost/unresolved", [mid for mid, _ in pool])


class ShippedPolicyTests(unittest.TestCase):
    """The shipped policy's balance criterion: the band is the calibrated one,
    and the exponents carry a dated tuning record that names them."""

    POLICY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "skills", "openrouter-model-router",
                               "policy.json")

    def setUp(self):
        with open(self.POLICY_PATH, encoding="utf-8") as f:
            self.scoring = json.load(f)["scoring"]

    def test_thresholds_are_the_calibrated_band(self):
        self.assertEqual(self.scoring["thresholds"],
                         {"top1_min": 0.2, "top1_max": 0.5, "top2_max": 0.75})

    def test_scoring_notes_date_the_coefficient_tuning(self):
        self.assertRegex(self.scoring["notes"], r"Re-tuned \d{4}-\d{2}-\d{2}")

    def test_the_dated_retune_names_the_shipped_exponents(self):
        notes = self.scoring["notes"]
        latest = notes[notes.rindex("Re-tuned"):]
        self.assertIn(f"alpha {self.scoring['alpha']:.1f}", latest)
        self.assertIn(f"beta {self.scoring['beta']:.1f}", latest)


if __name__ == "__main__":
    unittest.main()
