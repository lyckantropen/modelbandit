"""The three answers at the cost seam.

The seam answers what a ticket costs three ways: the ticket cost (the
cash/blended price, as today), the Draw (what one ticket burns of a plan's
Allowance, counted at the plan's list price), and the at-cap verdict
(whether one more ticket's Draw would cross an Allowance window's cap --
computed live by the allowance ledger when it lands). The score's cost
term applies the one marginal-zero pricing rule (ADR-0006): a
marginal-zero ticket prices as risk of its Draw -- Free risk times the
ticket's own list-priced Draw for a Plan route; where there is no Draw
(Free routes, zero-Draw plan servings) Free risk times the pool's
cheapest paid ticket. Never zero, so no code path divides by zero; Free
routes keep their exact current numbers.

Fixture style follows test_score.py: plain dicts, literal expectations,
no network.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

FREE_RISK = 0.35
PLAN_ID = "opencode-go/plan-model"
CHEAP_PLAN = "opencode-go/flash-plan"
DEAR_PLAN = "opencode-go/pro-plan"
ZERO_PLAN = "opencode-go/unlimited"


def plans_of(**prices):
    """A validated-shaped plans catalog: one entry per id, the list price
    given and the three Allowance window caps the loader requires."""
    return {mid: {"list_price": price,
                  "caps": {"five_hour": 20.0, "weekly": 100.0,
                           "monthly": 200.0},
                  "exposure": "no-retention"}
            for mid, price in prices.items()}


class TicketDrawTests(unittest.TestCase):
    """The Draw answer: what one ticket of a route burns of an Allowance."""

    def test_a_cataloged_plan_route_draws_its_list_price(self):
        self.assertEqual(
            modelbandit.ticket_draw(PLAN_ID, plans_of(**{PLAN_ID: 2.0})), 2.0)

    def test_the_zero_draw_serving_draws_zero(self):
        # The free-in-plan serving exists in the catalog and states a real
        # Allowance; one ticket of it consumes nothing of that Allowance.
        self.assertEqual(
            modelbandit.ticket_draw(ZERO_PLAN, plans_of(**{ZERO_PLAN: 0})),
            0.0)

    def test_an_uncataloged_plan_route_has_no_draw(self):
        # The price comes from the validated plans catalog alone: a plan
        # route it does not price has no Draw to answer.
        self.assertIsNone(
            modelbandit.ticket_draw(PLAN_ID,
                                    plans_of(**{"opencode-go/other": 2.0})))

    def test_no_other_serving_has_a_draw(self):
        # Only a Plan route draws an Allowance: a metered route pays cash,
        # a Free route serves for nothing, and neither holds a plan.
        for mid in ("vendor/model", "vendor/model:free", "opencode/flash"):
            with self.subTest(mid=mid):
                self.assertIsNone(
                    modelbandit.ticket_draw(mid, plans_of(**{PLAN_ID: 2.0})))

    def test_the_local_serving_fact_outranks_the_plan_shape(self):
        # A plan-shaped id this machine serves is a local row: it draws
        # nothing of any plan's Allowance.
        self.assertIsNone(
            modelbandit.ticket_draw(PLAN_ID, plans_of(**{PLAN_ID: 2.0}),
                                    local=True))


class PlanDrawPricingTests(unittest.TestCase):
    """The score's cost term: a Plan route prices as risk of its own
    list-priced Draw (ADR-0006) -- the one marginal-zero rule's Plan case."""

    def test_a_plan_route_prices_as_free_risk_times_its_own_list_price(self):
        eff = modelbandit.effective_costs(
            {PLAN_ID: 0.0, "b": 0.02, "c": 0.05},
            free_risk=FREE_RISK, plans=plans_of(**{PLAN_ID: 2.0}))
        self.assertAlmostEqual(eff[PLAN_ID], FREE_RISK * 2.0)
        self.assertEqual(eff["b"], 0.02)
        self.assertEqual(eff["c"], 0.05)

    def test_the_plan_price_ignores_the_cash_figure_the_pool_carries(self):
        # A plan ticket's cash price within its Allowance is $0; the Draw
        # rule answers the score term either way, so whatever cash figure
        # the pool carries cannot leak into the plan's price.
        for cash in (0.0, 2.0):
            with self.subTest(cash=cash):
                eff = modelbandit.effective_costs(
                    {PLAN_ID: cash}, free_risk=FREE_RISK,
                    plans=plans_of(**{PLAN_ID: 2.0}))
                self.assertAlmostEqual(eff[PLAN_ID], FREE_RISK * 2.0)

    def test_a_plan_tickets_price_never_joins_the_pool_cheapest_basis(self):
        # The Nominal floor's basis is the pool's cheapest metered ticket:
        # a plan route's price is the Draw rule's business, never the cash
        # floor's -- here a plan cash figure of $0.01 would otherwise drag
        # the Free route's floor below its pinned $0.007.
        eff = modelbandit.effective_costs(
            {PLAN_ID: 0.01, "vendor/model:free": 0.0, "b": 0.02},
            free_risk=FREE_RISK, free={"vendor/model:free"},
            plans=plans_of(**{PLAN_ID: 2.0}))
        self.assertAlmostEqual(eff["vendor/model:free"], FREE_RISK * 0.02)
        self.assertAlmostEqual(eff[PLAN_ID], FREE_RISK * 2.0)

    def test_a_cheaper_draw_outscores_a_dearer_one_at_equal_share_and_fit(self):
        # The plan's advantage appears exactly where it exists in the
        # wallet: burning cheap Allowance outscores burning dear Allowance.
        plans = plans_of(**{CHEAP_PLAN: 0.5, DEAR_PLAN: 2.0})
        eff = modelbandit.effective_costs(
            {CHEAP_PLAN: 0.0, DEAR_PLAN: 0.0}, free_risk=FREE_RISK,
            plans=plans)
        cheap = modelbandit.standing(0.07, eff[CHEAP_PLAN], 4.0, 0.7, 1.0)
        dear = modelbandit.standing(0.07, eff[DEAR_PLAN], 4.0, 0.7, 1.0)
        self.assertGreater(cheap, dear)
        self.assertAlmostEqual(cheap / dear, 2.0 / 0.5)

    def test_a_zero_draw_plan_serving_prices_at_the_pool_cheapest_basis(self):
        # The free-in-plan serving has no Draw: the no-Draw case of the one
        # rule answers, exactly as it does for the Free route beside it.
        plans = plans_of(**{ZERO_PLAN: 0, PLAN_ID: 2.0})
        eff = modelbandit.effective_costs(
            {ZERO_PLAN: 0.0, "vendor/model:free": 0.0, PLAN_ID: 0.0,
             "b": 0.02},
            free_risk=FREE_RISK, free={"vendor/model:free"}, plans=plans)
        self.assertAlmostEqual(eff[ZERO_PLAN], eff["vendor/model:free"])
        self.assertAlmostEqual(eff[ZERO_PLAN], FREE_RISK * 0.02)
        self.assertAlmostEqual(eff[PLAN_ID], FREE_RISK * 2.0)

    def test_a_zero_draw_serving_floors_even_without_a_free_route(self):
        # The no-Draw case does not need a Free route in the pool to fire:
        # the plan serving itself has no Draw.
        eff = modelbandit.effective_costs(
            {ZERO_PLAN: 0.0, "b": 0.02}, free_risk=FREE_RISK,
            plans=plans_of(**{ZERO_PLAN: 0}))
        self.assertAlmostEqual(eff[ZERO_PLAN], FREE_RISK * 0.02)
        self.assertEqual(eff["b"], 0.02)

    def test_a_plan_route_outside_the_catalog_has_no_draw(self):
        # An uncataloged plan route answers the no-Draw case -- never a $0,
        # never a crash.
        eff = modelbandit.effective_costs(
            {PLAN_ID: 0.0, "b": 0.02}, free_risk=FREE_RISK,
            plans=plans_of(**{"opencode-go/other": 2.0}))
        self.assertAlmostEqual(eff[PLAN_ID], FREE_RISK * 0.02)

    def test_no_marginal_zero_answer_ever_prices_at_zero(self):
        # Free risk is validated strictly inside (0, 1), so every Draw-rule
        # answer is positive and the score it feeds stays finite.
        plans = plans_of(**{PLAN_ID: 0.01, ZERO_PLAN: 0})
        eff = modelbandit.effective_costs(
            {PLAN_ID: 0.0, ZERO_PLAN: 0.0, "vendor/model:free": 0.0,
             "b": 0.02},
            free_risk=FREE_RISK, free={"vendor/model:free"}, plans=plans)
        for mid, cost in eff.items():
            with self.subTest(mid=mid):
                self.assertGreater(cost, 0.0)
        self.assertTrue(
            math.isfinite(modelbandit.task_score(0.07, eff[PLAN_ID],
                                                 0.7, 1.0)))


class FreeNumbersUnchangedTests(unittest.TestCase):
    """ADR-0006's Free case: the Nominal floor stays exactly what it was,
    whatever plans facts the caller passes."""

    POOL = {"vendor/model:free": 0.0, "b": 0.02, "c": 0.05}
    FREE = {"vendor/model:free"}

    def test_the_free_and_paid_answers_are_identical_with_and_without_plans(self):
        without = modelbandit.effective_costs(self.POOL, free_risk=FREE_RISK,
                                              free=self.FREE)
        with_facts = modelbandit.effective_costs(
            self.POOL, free_risk=FREE_RISK, free=self.FREE,
            plans=plans_of(**{PLAN_ID: 2.0}))
        self.assertEqual(with_facts, without)
        self.assertAlmostEqual(with_facts["vendor/model:free"], 0.007)
        self.assertEqual(with_facts["b"], 0.02)
        self.assertEqual(with_facts["c"], 0.05)

    def test_a_pool_without_free_or_plan_routes_stays_unpriced_by_the_floor(self):
        # The degenerate paid zero keeps the pool's own fallback, and a
        # plans section beside the pool cannot change that.
        eff = modelbandit.effective_costs({"a": 0.0, "b": 0.02},
                                          free_risk=0.0,
                                          plans=plans_of(**{PLAN_ID: 2.0}))
        self.assertEqual(eff, {"a": 0.02, "b": 0.02})

    def test_a_catalog_entry_for_a_non_plan_id_is_ignored(self):
        # Plan-ness is the Route-kind seam's answer, never the catalog's:
        # a market id prices as the paid ticket it is, whatever a catalog
        # row claims.
        plans = {"vendor/model": {"list_price": 1.0}}
        eff = modelbandit.effective_costs({"vendor/model": 0.0984},
                                          free_risk=FREE_RISK, plans=plans)
        self.assertEqual(eff["vendor/model"], 0.0984)


class AtCapVerdictTests(unittest.TestCase):
    """The at-cap answer, per window: whether one more ticket's Draw would
    cross an Allowance window's cap. The ledger tracks the drawn totals;
    the verdict is the seam's answer."""

    PLANS = plans_of(**{PLAN_ID: 2.0})

    def test_a_ticket_crossing_a_window_is_verdicted_per_window(self):
        # 19 drawn + 2 more = 21 over the 5-hour cap; the week and the
        # month hold.
        verdict = modelbandit.at_cap_verdict(
            PLAN_ID, self.PLANS,
            {"five_hour": 19.0, "weekly": 40.0, "monthly": 60.0})
        self.assertEqual(verdict, {"five_hour": True, "weekly": False,
                                   "monthly": False})

    def test_each_window_crosses_on_its_own(self):
        for window, drawn in (("five_hour", 19.0), ("weekly", 99.0),
                              ("monthly", 199.0)):
            with self.subTest(window=window):
                verdict = modelbandit.at_cap_verdict(
                    PLAN_ID, self.PLANS, {window: drawn})
                self.assertTrue(verdict[window])
                others = [w for w in ("five_hour", "weekly", "monthly")
                          if w != window]
                self.assertFalse(any(verdict[w] for w in others))

    def test_a_ticket_that_exactly_reaches_a_cap_does_not_cross_it(self):
        # The ticket that spends the last of the window's Allowance is
        # still within it; crossing is over the cap, not up to it.
        verdict = modelbandit.at_cap_verdict(PLAN_ID, self.PLANS,
                                             {"monthly": 197.0})
        self.assertFalse(verdict["monthly"])

    def test_an_undrawn_window_starts_from_zero(self):
        verdict = modelbandit.at_cap_verdict(PLAN_ID, self.PLANS, {})
        self.assertEqual(verdict, {"five_hour": False, "weekly": False,
                                   "monthly": False})

    def test_windows_cross_together_when_the_draw_is_wide(self):
        verdict = modelbandit.at_cap_verdict(
            PLAN_ID, self.PLANS,
            {"five_hour": 19.0, "weekly": 99.0, "monthly": 199.0})
        self.assertEqual(verdict, {"five_hour": True, "weekly": True,
                                   "monthly": True})

    def test_the_verdict_covers_the_plans_stated_windows(self):
        caps = self.PLANS[PLAN_ID]["caps"]
        verdict = modelbandit.at_cap_verdict(PLAN_ID, self.PLANS, {})
        self.assertEqual(set(verdict), set(caps))

    def test_a_route_without_an_allowance_earns_no_verdict(self):
        # A metered route has no Allowance to cross: no window, no verdict.
        self.assertEqual(
            modelbandit.at_cap_verdict("vendor/model", self.PLANS, {}), {})

    def test_an_uncataloged_plan_route_earns_no_verdict(self):
        # The verdict reads the validated plans catalog alone; a plan route
        # it does not price states no boundary to cross.
        self.assertEqual(
            modelbandit.at_cap_verdict(PLAN_ID,
                                       plans_of(**{"opencode-go/other": 2.0}),
                                       {}), {})


if __name__ == "__main__":
    unittest.main()
