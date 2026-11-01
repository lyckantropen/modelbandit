"""The prospective allowance ledger: three windows, one burst, in-run.

A Plan route's ticket is paid for by the subscription, not by cash: one
ticket draws down that model's Allowance — the flat fee's dollar budget
across three windows (rolling 5-hour, weekly, monthly). The ledger is
prospective and in-run: it starts every run empty, allots each ticket the
deal assigns in all three windows at once (the batch is assumed to land in
ONE 5-hour burst — the conservative read, so a run that would cross the
5-hour window is flagged here and not only at the month), and answers the
cost seam's at-cap verdict from its own drawn totals. Nothing is read from
the account and nothing persists: two identical runs answer identically, and
a plan other harnesses share is never planned against a fiction.

A row whose next ticket's Draw would cross a window's cap leaves the draw
for the tickets that remain — the batch carries on with the rows that still
fit — and a single-task pick whose plan row is at cap hands the pick to the
family's Metered Twin when the declared link resolves one; otherwise the next
admitted row takes it, as before. A plan row whose declared family link
resolves gets the market adapter (TwinAbsorptionTests): its slot continues as
the family's Metered Twin, so its windows are charged only for the tickets the
plan row itself took. Caps are real boundaries: no reserve is held back and
no overflow flag exists. Metered and Free routes keep no totals at all, and
the zero-Draw serving books nothing.

The crossing arithmetic is the cost seam's (at_cap_verdict); the ledger owns
only the drawn totals it feeds that answer.

Fixture style follows test_plan_pool.py: plain dicts, no network. The
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

PLAN = "opencode-go/deepseek-v4-pro"    # a Plan route: it draws an Allowance
SECOND = "opencode-go/glm-5.3"          # a second Plan route, its own window
TWIN = "deepseek/deepseek-v4-pro"       # the metered twin: cash, no Allowance
OTHER = "z-ai/glm-5.3"                  # another metered route
FREE = "opencode/deepseek-v4-pro"       # a Free route
ZERO = "opencode-go/unlimited-serving"  # the zero-Draw, free-in-plan serving
GHOST = "opencode-go/ghost-model"       # a plan route the catalog omits

WINDOWS = ("five_hour", "weekly", "monthly")


def plan_entry(list_price=1.0, **windows):
    """One plans entry: the list price (the Draw's basis) and the three
    Allowance window caps, generous by default so only the window under test
    binds."""
    caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0}
    caps.update(windows)
    return {"list_price": list_price, "caps": caps,
            "exposure": "no-retention", "family_ref": TWIN}


def ledger(plans, **kw):
    return modelbandit.AllowanceLedger(plans, **kw)


class LedgerTotalsTests(unittest.TestCase):
    """What the ledger books: every ticket's Draw, in every window at once."""

    PLANS = {PLAN: plan_entry(1.0)}

    def test_a_run_starts_with_nothing_drawn(self):
        # Prospective and in-run: no account state is read, so the windows
        # start empty whatever the plan has been used for elsewhere.
        self.assertEqual(
            ledger(self.PLANS).drawn(PLAN),
            {"five_hour": 0.0, "weekly": 0.0, "monthly": 0.0})

    def test_one_ticket_draws_down_every_window(self):
        # The one-burst assumption: the batch lands inside one 5-hour window,
        # so a single ticket counts against the 5-hour window, the week and
        # the month alike.
        led = ledger(self.PLANS)
        self.assertTrue(led.charge(PLAN))
        self.assertEqual(
            led.drawn(PLAN), {"five_hour": 1.0, "weekly": 1.0,
                              "monthly": 1.0})

    def test_three_tickets_book_three_times_the_draw(self):
        led = ledger({PLAN: plan_entry(2.0)})
        for _ in range(3):
            led.charge(PLAN)
        self.assertEqual(
            led.drawn(PLAN), {"five_hour": 6.0, "weekly": 6.0,
                              "monthly": 6.0})

    def test_each_plan_model_keeps_its_own_totals(self):
        led = ledger({PLAN: plan_entry(1.0), SECOND: plan_entry(5.0)})
        led.charge(PLAN)
        led.charge(PLAN)
        led.charge(SECOND)
        self.assertEqual(led.drawn(PLAN)["monthly"], 2.0)
        self.assertEqual(led.drawn(SECOND)["monthly"], 5.0)

    def test_a_metered_route_never_enters_the_ledger(self):
        # Cash is not an Allowance: the metered twin buys its tickets.
        led = ledger(self.PLANS)
        self.assertFalse(led.charge(TWIN))
        self.assertEqual(led.drawn(TWIN), {})
        self.assertFalse(led.crosses(TWIN))

    def test_a_free_route_never_enters_the_ledger(self):
        led = ledger(self.PLANS)
        self.assertFalse(led.charge(FREE))
        self.assertEqual(led.drawn(FREE), {})
        self.assertFalse(led.crosses(FREE))

    def test_a_plan_route_the_catalog_omits_never_enters_the_ledger(self):
        led = ledger(self.PLANS)
        self.assertFalse(led.charge(GHOST))
        self.assertEqual(led.drawn(GHOST), {})
        self.assertFalse(led.crosses(GHOST))

    def test_a_plan_id_this_machine_serves_never_enters_the_ledger(self):
        # The local serving fact outranks the id shape: served here means no
        # plan Allowance to draw, whatever the catalog says.
        led = ledger(self.PLANS, local=(PLAN,))
        self.assertFalse(led.charge(PLAN))
        self.assertEqual(led.drawn(PLAN), {})
        self.assertFalse(led.crosses(PLAN))

    def test_the_zero_draw_serving_books_nothing_and_never_crosses(self):
        # Free in the plan: it burns no Allowance, so no cap can bind however
        # small the window is.
        led = ledger({ZERO: plan_entry(0, five_hour=0.01, weekly=0.01,
                                       monthly=0.01)})
        for _ in range(50):
            led.charge(ZERO)
        self.assertEqual(led.drawn(ZERO)["five_hour"], 0.0)
        self.assertFalse(led.crosses(ZERO))


class LedgerVerdictTests(unittest.TestCase):
    """The ledger's at-cap answer: the seam's verdict over the totals it
    keeps — the ticket that would spend the last of a window still draws."""

    def test_the_verdict_is_per_window(self):
        # $1 a ticket, $2.50 in the 5-hour window: the third ticket of the
        # burst would cross it, while the week and the month hold.
        led = ledger({PLAN: plan_entry(1.0, five_hour=2.5)})
        led.charge(PLAN)
        self.assertEqual(led.at_cap(PLAN), {"five_hour": False,
                                            "weekly": False,
                                            "monthly": False})
        led.charge(PLAN)
        self.assertEqual(led.at_cap(PLAN), {"five_hour": True,
                                            "weekly": False,
                                            "monthly": False})

    def test_each_window_crosses_on_its_own(self):
        for window in WINDOWS:
            with self.subTest(window=window):
                led = ledger({PLAN: plan_entry(1.0, **{window: 2.5})})
                led.charge(PLAN)
                led.charge(PLAN)
                self.assertTrue(led.at_cap(PLAN)[window])
                self.assertFalse(
                    any(led.at_cap(PLAN)[w] for w in WINDOWS if w != window))
                self.assertTrue(led.crosses(PLAN))

    def test_the_ticket_that_spends_the_last_of_a_window_still_draws(self):
        # Crossing is over the cap, not up to it: $1 drawn of a $2 window
        # leaves the next ticket (which lands exactly on $2) in the draw.
        led = ledger({PLAN: plan_entry(1.0, five_hour=2.0)})
        led.charge(PLAN)
        self.assertFalse(led.crosses(PLAN))
        led.charge(PLAN)
        self.assertEqual(led.drawn(PLAN)["five_hour"], 2.0)
        self.assertTrue(led.crosses(PLAN))

    def test_a_window_the_batch_has_not_touched_is_not_at_cap(self):
        led = ledger({PLAN: plan_entry(1.0, monthly=1.5)})
        self.assertFalse(led.crosses(PLAN))
        led.charge(PLAN)
        self.assertTrue(led.crosses(PLAN))


class StatelessnessTests(unittest.TestCase):
    """Nothing crosses between runs: the ledger is built fresh, every time."""

    PLANS = {PLAN: plan_entry(1.0, five_hour=2.5)}

    def test_the_next_run_starts_empty(self):
        spent = ledger(self.PLANS)
        spent.charge(PLAN)
        spent.charge(PLAN)
        self.assertTrue(spent.crosses(PLAN))
        fresh = ledger(self.PLANS)
        self.assertEqual(fresh.drawn(PLAN)["five_hour"], 0.0)
        self.assertFalse(fresh.crosses(PLAN))

    def test_two_ledgers_over_the_same_plans_agree(self):
        one, two = ledger(self.PLANS), ledger(self.PLANS)
        for _ in range(2):
            one.charge(PLAN)
            two.charge(PLAN)
        self.assertEqual(one.drawn(PLAN), two.drawn(PLAN))
        self.assertEqual(one.at_cap(PLAN), two.at_cap(PLAN))


def deal(share, plans, scores, tickets=12, seed="ledger", ledger=None,
         admitted=None):
    """A deal over `share` with the plans catalog carrying the caps.

    `admitted` narrows the pool exactly as the admission seam does; the
    default admits every fixture row."""
    models = {mid: {} for mid in share}
    return modelbandit.plan_deal(
        share, models, {},
        modelbandit.DealParameters(
            blend_weight=0.0, top_k=5, seed=seed, tickets=tickets,
            fit_adjusted_task_scores=scores,
            admitted=frozenset(share) if admitted is None else admitted),
        plans=plans, ledger=ledger)


def tickets_of(rows):
    return {row["mid"]: row["tickets"] for row in rows}


class DealEvictionTests(unittest.TestCase):
    """At-cap eviction in the deal: a row whose next ticket would cross a
    window's cap leaves the draw for the tickets that remain, and the batch
    carries on with the rows that still fit."""

    # The plan row takes the whole draw (bases 1.0 / 0.0), so every ticket
    # reaches it first: how many it gets is the cap's arithmetic alone, not
    # the seed's.
    SHARE = {PLAN: 0.6, OTHER: 0.4}
    SCORES = {PLAN: 1.0, OTHER: 0.0}

    def plans(self, list_price=1.0, **windows):
        return {PLAN: plan_entry(list_price, **windows)}

    def test_a_row_crossing_the_five_hour_window_leaves_the_draw(self):
        # $1 a ticket, $2.50 in the 5-hour window: two tickets draw, the
        # third would cross, so the row leaves and the metered row takes the
        # rest of the batch.
        rows = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES)
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 10})

    def test_a_row_crossing_the_weekly_window_leaves_the_draw(self):
        rows = deal(self.SHARE, self.plans(weekly=2.5), self.SCORES)
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 10})

    def test_a_row_crossing_the_monthly_window_leaves_the_draw(self):
        rows = deal(self.SHARE, self.plans(monthly=2.5), self.SCORES)
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 10})

    def test_the_ticket_that_spends_the_last_of_a_window_still_draws(self):
        # Crossing is over the cap: three tickets of $1 in a $3 window all
        # draw, and the row leaves before the fourth.
        rows = deal(self.SHARE, self.plans(five_hour=3.0), self.SCORES,
                    tickets=3)
        self.assertEqual(tickets_of(rows), {PLAN: 3, OTHER: 0})
        rows = deal(self.SHARE, self.plans(five_hour=3.0), self.SCORES,
                    tickets=4)
        self.assertEqual(tickets_of(rows), {PLAN: 3, OTHER: 1})

    def test_a_row_at_cap_before_the_first_ticket_takes_none_of_the_batch(self):
        # One ticket's Draw alone crosses the window: the row never draws.
        rows = deal(self.SHARE, self.plans(list_price=2.0, five_hour=1.0),
                    self.SCORES)
        self.assertEqual(tickets_of(rows), {PLAN: 0, OTHER: 12})

    def test_the_ticket_falls_to_the_next_row_that_still_fits(self):
        # Eviction is a fall-through in the draw's own order, never a
        # re-deal: the third-ranked row is not handed shares of the tickets
        # the at-cap row gave up. The third row is a Metered id that is not
        # the plan row's declared Twin (TwinAbsorptionTests covers the
        # declared link); here nothing resolves, so the fall-through stands.
        share = {PLAN: 0.5, OTHER: 0.3, "mistral/mistral-large": 0.2}
        rows = deal(share, self.plans(five_hour=2.5),
                    {PLAN: 1.0, OTHER: 0.0, "mistral/mistral-large": 0.0})
        self.assertEqual(tickets_of(rows),
                         {PLAN: 2, OTHER: 10, "mistral/mistral-large": 0})

    def test_a_metered_row_never_enters_the_ledger(self):
        # Cash buys its tickets: the metered row keeps drawing, and the
        # ledger books nothing against it.
        led = modelbandit.AllowanceLedger(self.plans(five_hour=2.5))
        rows = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES,
                    ledger=led)
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 10})
        self.assertEqual(led.drawn(OTHER), {})
        self.assertEqual(led.drawn(PLAN)["five_hour"], 2.0)

    def test_a_free_row_never_enters_the_ledger(self):
        led = modelbandit.AllowanceLedger(self.plans(list_price=2.0,
                                                     five_hour=1.0))
        share = {PLAN: 0.6, FREE: 0.4}
        rows = deal(share, self.plans(list_price=2.0, five_hour=1.0),
                    {PLAN: 1.0, FREE: 0.0}, ledger=led)
        self.assertEqual(tickets_of(rows), {PLAN: 0, FREE: 12})
        self.assertEqual(led.drawn(FREE), {})

    def test_the_zero_draw_serving_keeps_drawing(self):
        # Free in the plan: it burns nothing, so no window evicts it.
        share = {ZERO: 0.6, OTHER: 0.4}
        rows = deal(share, {ZERO: plan_entry(0, five_hour=0.01)},
                    {ZERO: 1.0, OTHER: 0.0})
        self.assertEqual(tickets_of(rows), {ZERO: 12, OTHER: 0})

    def test_every_row_at_cap_leaves_the_batch_unassigned(self):
        # The existing stop semantics, never a new failure: the deal runs,
        # no row takes a ticket, and nothing raises.
        share = {PLAN: 0.6, SECOND: 0.4}
        plans = {PLAN: plan_entry(1.0, five_hour=0.5),
                 SECOND: plan_entry(1.0, weekly=0.5)}
        rows = deal(share, plans, {PLAN: 1.0, SECOND: 0.0})
        self.assertEqual(sum(row["tickets"] for row in rows), 0)
        self.assertEqual(sorted(row["mid"] for row in rows),
                         [PLAN, SECOND])

    def test_the_batch_keeps_assigning_while_any_row_fits(self):
        # Two plan rows at their caps and one metered row: the metered row
        # takes the whole batch.
        share = {PLAN: 0.5, SECOND: 0.3, OTHER: 0.2}
        plans = {PLAN: plan_entry(1.0, five_hour=0.5),
                 SECOND: plan_entry(1.0, monthly=0.5)}
        rows = deal(share, plans,
                    {PLAN: 1.0, SECOND: 0.0, OTHER: 0.0})
        self.assertEqual(tickets_of(rows), {PLAN: 0, SECOND: 0, OTHER: 12})

    def test_a_deal_row_carries_no_allowance_figures(self):
        # No reserve, no overflow flag: the row the deal returns is the row
        # it always returned.
        rows = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES)
        self.assertEqual(set(rows[0]),
                         {"mid", "share", "base", "pref", "draw", "tickets"})

    def test_two_identical_runs_give_identical_verdicts(self):
        # Stateless across runs: the same seed evicts the same rows, and the
        # draw for a ticket stays keyed as it was before the ledger existed.
        one = deal({PLAN: 0.5, OTHER: 0.5}, self.plans(five_hour=2.5),
                   {PLAN: 1.0, OTHER: 1.0}, tickets=24, seed="proj")
        two = deal({PLAN: 0.5, OTHER: 0.5}, self.plans(five_hour=2.5),
                   {PLAN: 1.0, OTHER: 1.0}, tickets=24, seed="proj")
        self.assertEqual(one, two)
        self.assertEqual(sum(row["tickets"] for row in one), 24)
        self.assertLessEqual(tickets_of(one)[PLAN], 2)


class EvictionFallThroughWrapsTests(unittest.TestCase):
    """The fall-through is circular, still the draw's own order: a ticket
    whose drawn row is at cap is offered to the rows after it and then wraps
    to the rows before it, so no ticket is abandoned while any row fits."""

    def test_a_ticket_past_an_at_cap_last_row_wraps_to_an_earlier_row(self):
        # The metered row ranks first on popularity but draws a thin slice
        # (score 0.1 against the plan row's 1.0); the plan row ranks last and
        # crosses its 5-hour window after two tickets. Every ticket drawn
        # past the metered row's slice reaches the at-cap last row first,
        # wraps, and lands on the metered row: the batch continues instead of
        # dropping those tickets.
        share = {OTHER: 0.6, PLAN: 0.4}
        rows = deal(share, {PLAN: plan_entry(1.0, five_hour=2.0)},
                    {PLAN: 1.0, OTHER: 0.1})
        self.assertEqual(tickets_of(rows), {OTHER: 10, PLAN: 2})
        self.assertEqual(sum(row["tickets"] for row in rows), 12)


class TwinAbsorptionTests(unittest.TestCase):
    """Market resolution in the deal (issue #65): an at-cap Plan row's ticket
    lands on the family's Metered Twin — same model, same slot, the market
    flipped plan → metered — and nothing is charged to the plan's windows for
    it. The ticket re-enters the draw's circular fall-through only when the
    declared family link resolves no eligible row."""

    # The plan row takes the whole draw (base 1.0 against 0.0), so every
    # ticket reaches it first: how many it keeps is the cap's arithmetic, and
    # where the rest land is the market adapter's answer. The unrelated
    # metered row ranks ahead of the Twin, so a plain fall-through would hand
    # it the tickets the at-cap plan row gives up.
    SHARE = {PLAN: 0.5, OTHER: 0.3, TWIN: 0.2}
    SCORES = {PLAN: 1.0, OTHER: 0.0, TWIN: 0.0}

    def plans(self, list_price=1.0, **windows):
        return {PLAN: plan_entry(list_price, **windows)}

    def test_an_at_cap_plan_ticket_lands_on_its_metered_twin(self):
        rows = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES)
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 0, TWIN: 10})

    def test_an_absorbed_ticket_draws_nothing_from_the_plan_windows(self):
        # The readout states only what the plan rows actually charged: two
        # tickets, never the ten the Twin absorbed.
        led = modelbandit.AllowanceLedger(self.plans(five_hour=2.5))
        rows = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES,
                    ledger=led)
        self.assertEqual(sum(row["tickets"] for row in rows), 12)
        self.assertEqual(tickets_of(rows)[TWIN], 10)
        self.assertEqual(led.drawn(PLAN), {"five_hour": 2.0, "weekly": 2.0,
                                           "monthly": 2.0})
        self.assertEqual(led.readout(TWIN), {})

    def test_the_twin_keeps_the_at_cap_rows_slot(self):
        # Identity preserved, market flipped: the tickets the plan's slot
        # would have drawn are the Twin's, so the doubly-served family's
        # presence is exactly what it was before the cap bound (US15), never
        # re-dealt to unrelated rows and never counted twice.
        wide = deal(self.SHARE, self.plans(), self.SCORES)
        tight = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES)
        self.assertEqual((tickets_of(wide)[PLAN], tickets_of(wide)[TWIN]),
                         (12, 0))
        self.assertEqual((tickets_of(tight)[PLAN], tickets_of(tight)[TWIN]),
                         (2, 10))
        self.assertEqual(tickets_of(tight)[PLAN] + tickets_of(tight)[TWIN], 12)
        self.assertEqual(tickets_of(tight)[OTHER], 0)

    def test_an_unresolved_family_link_still_falls_through(self):
        # The declared link names a Metered id this run does not play: the
        # ticket re-enters the draw's circular fall-through as before.
        share = {PLAN: 0.5, OTHER: 0.5}
        plans = {PLAN: dict(plan_entry(five_hour=2.5),
                            family_ref="mistral/mistral-large")}
        rows = deal(share, plans, {PLAN: 1.0, OTHER: 0.0})
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 10})

    def test_an_ineligible_twin_is_no_twin(self):
        # The link resolves a row admission excluded: no Twin may absorb.
        rows = deal(self.SHARE, self.plans(five_hour=2.5), self.SCORES,
                    admitted=frozenset({PLAN, OTHER}))
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 10})

    def test_a_metered_rows_tickets_never_flip_to_the_plan(self):
        # One direction only (ADR-0007): the draw reads the link from Plan
        # rows and lands on Metered ones; a Metered row's tickets never
        # return to the plan's Allowance.
        rows = deal(self.SHARE, self.plans(), {PLAN: 0.0, OTHER: 0.0,
                                               TWIN: 1.0})
        self.assertEqual(tickets_of(rows), {PLAN: 0, OTHER: 0, TWIN: 12})

    def test_the_seeded_draw_is_byte_identical_without_absorption(self):
        # US14/US16: with caps nowhere near, no ticket is absorbed, and the
        # deal's seeded draw is the one pinned before market resolution
        # (seed "pin", 24 tickets, the shipped blend).
        share = {PLAN: 0.6, TWIN: 0.3, OTHER: 0.2}
        rows = modelbandit.plan_deal(
            share, {mid: {} for mid in share}, {},
            modelbandit.DealParameters(
                blend_weight=0.6, top_k=5, seed="pin", tickets=24,
                fit_adjusted_task_scores={PLAN: 2.0, TWIN: 1.5, OTHER: 1.0},
                admitted=frozenset(share)),
            plans={PLAN: plan_entry(0.5)})
        self.assertEqual(tickets_of(rows), {PLAN: 10, TWIN: 7, OTHER: 7})


class DecimalEvictionTests(unittest.TestCase):
    """A decimal cap is a real boundary: a batch that reaches it exactly is
    never evicted, while any true crossing still is — binary float noise is
    not a boundary."""

    SHARE = {PLAN: 0.6, OTHER: 0.4}
    SCORES = {PLAN: 1.0, OTHER: 0.0}

    def test_three_ten_cent_tickets_fit_a_thirty_cent_cap_exactly(self):
        # In binary, 0.2 + 0.1 lands just past 0.3: the third ticket reaches
        # the decimal cap exactly and must stay in the draw.
        plans = {PLAN: plan_entry(0.10, five_hour=0.30)}
        rows = deal(self.SHARE, plans, self.SCORES, tickets=3)
        self.assertEqual(tickets_of(rows), {PLAN: 3, OTHER: 0})

    def test_a_decimal_cap_below_the_sum_still_evicts_the_third(self):
        plans = {PLAN: plan_entry(0.10, five_hour=0.29)}
        rows = deal(self.SHARE, plans, self.SCORES, tickets=3)
        self.assertEqual(tickets_of(rows), {PLAN: 2, OTHER: 1})

    def test_a_decimal_cap_past_the_sum_evicts_the_next_ticket(self):
        # 0.31 admits the three 0.10 tickets and stops the fourth: the
        # tolerance never widens a window past its decimal boundary.
        plans = {PLAN: plan_entry(0.10, five_hour=0.31)}
        rows = deal(self.SHARE, plans, self.SCORES, tickets=4)
        self.assertEqual(tickets_of(rows), {PLAN: 3, OTHER: 1})


class LedgerReadoutTests(unittest.TestCase):
    """The readout snapshot the CLI line formats: per window, what this run
    has drawn and the cap it draws against."""

    PLANS = {PLAN: plan_entry(2.0, five_hour=5.0, monthly=10.0)}

    def test_the_readout_states_each_windows_drawn_and_cap(self):
        led = ledger(self.PLANS)
        led.charge(PLAN)
        self.assertEqual(led.readout(PLAN), {
            "five_hour": {"drawn": 2.0, "cap": 5.0},
            "weekly": {"drawn": 2.0, "cap": 100.0},
            "monthly": {"drawn": 2.0, "cap": 10.0}})

    def test_a_route_without_an_allowance_has_no_readout(self):
        # The CLI line is not printed for it: no Allowance, nothing to state.
        led = ledger(self.PLANS)
        self.assertEqual(led.readout(TWIN), {})
        self.assertEqual(led.readout(GHOST), {})


def market_model(mid=OTHER):
    return {"id": mid, "supported_parameters": ["reasoning_effort"],
            "pricing": {"prompt": "0.0000002", "completion": "0.000001",
                        "input_cache_read": "0"}}


def board(*models):
    return {"as_of": "2026-10-17", "classifications": [
        {"tag": "content_writing", "usage_share": 1.0, "models": [
            {"id": mid, "tag_usage_share": share}
            for mid, share in models]}]}


class PickEvictionCliTests(unittest.TestCase):
    """The whole run: a single-task pick whose Draw crosses a window's cap is
    not picked — the next admitted row takes it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        # The shared CLI lifecycle (test_cli.CliTests): injected fetchers,
        # patched local probe/cache/env, captured stdout/stderr. The scenario
        # fixtures below (policy, world, boards) stay this suite's own.
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)

    def with_policy(self, plans):
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump({
                "baseline": {"id": OTHER},
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
        self.assertIn(code, (None, 0), err)
        return out, err

    def world(self, models, classified):
        return {"models": models, "classifications": board(*classified),
                "rankings": {"data": []}, "endpoints": {}}

    def deal_tickets(self, printed):
        """The deal block's ticket column, per row."""
        block = printed[printed.index("deal (seed"):
                        printed.index("projection at")]
        return {cells[1].strip(): cells[6].strip()
                for line in block.splitlines()
                if line.startswith("| ") and "---" not in line
                for cells in [line.split(" | ")]
                if cells[1].strip() != "model"}

    def test_a_pick_at_its_cap_is_not_picked(self):
        # The plan row is the top of the task order, but one ticket's Draw
        # ($2) crosses its 5-hour window ($1): the next admitted row takes
        # the pick, and the batch assigns to it alone.
        self.with_policy({PLAN: plan_entry(2.0, five_hour=1.0)})
        printed, err = self.run_main(self.world(
            [market_model()], [(PLAN, 0.6), (OTHER, 0.4)]))
        self.assertIn("| 1 | " + PLAN, printed)
        self.assertIn(f"default pick (top of task order): openrouter/{OTHER}",
                      printed)
        self.assertNotIn(f"default pick (top of task order): {PLAN}", printed)
        self.assertEqual(self.deal_tickets(printed), {PLAN: "0", OTHER: "12"})

    def test_a_pick_within_its_allowance_is_still_picked(self):
        # The row is not shunned for being a plan row: within its Allowance
        # it takes the pick and its tickets.
        self.with_policy({PLAN: plan_entry()})
        printed, err = self.run_main(self.world(
            [market_model()], [(PLAN, 0.6), (OTHER, 0.4)]))
        self.assertIn(f"default pick (top of task order): {PLAN}", printed)
        self.assertGreater(int(self.deal_tickets(printed)[PLAN]), 0)

    def test_every_row_at_cap_stops_the_run_as_an_excluded_one(self):
        # No new failure is invented for the ledger's verdict: nothing can be
        # picked, so the run stops with the existing all-excluded answer and
        # status 0.
        self.with_policy({PLAN: plan_entry(2.0, five_hour=1.0),
                          SECOND: plan_entry(2.0, weekly=1.0)})
        printed, err = self.run_main(self.world(
            [market_model()], [(PLAN, 0.6), (SECOND, 0.4)]))
        self.assertNotIn("default pick", printed)
        self.assertIn("no candidate admitted", err)
        self.assertIn(PLAN, err)


if __name__ == "__main__":
    unittest.main()
