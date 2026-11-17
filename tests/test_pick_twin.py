"""The pick names a market: an at-cap plan row hands the pick to its Twin.

A single-task pick follows the deal's market rule degenerately (issue #44,
US4/US5): when the top admitted row is a Plan route whose Draw would cross a
window's cap, the pick is the family's Metered Twin -- same model, market
flipped plan to metered -- so identity survives the cap and the run simply
pays cash for one task instead of stepping down to a different model. The
Twin is the one the plans entry's declared `family_ref` names, never one
derived from an id shape, and it must be a metered row this run actually
plays: absent from the ranking, admission-excluded, or not a market serving,
and the declaration resolves nothing -- the next admitted row takes the pick,
exactly as before.

The pick line emits the provider-qualified id a model config consumes
(`openrouter/<slug>`, or the id's own namespace unchanged), and a metered
pick carries no price and no Draw beside it: only a Plan route has an
Allowance to draw down, and the qualified id itself names the market.

The fixtures rank the Twin last behind a third metered row, so a pick that
lands on the Twin proves the declared link was followed rather than the order
walked.

Fixture style follows test_allowance_ledger.py: plain dicts, no network, the
whole run through test_cli's CLI lifecycle (injected fetchers, patched
probe/cache/env, captured output).
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
import test_cli  # noqa: E402

PLAN = "opencode-go/deepseek-v4-pro"    # a Plan route: it draws an Allowance
TWIN = "deepseek/deepseek-v4-pro"       # its Metered Twin: cash, no Allowance
OTHER = "z-ai/glm-5.3"                  # another metered route, ranked between
GHOST = "ghost/absent-model"            # a market-shaped id no run plays


def plan_entry(list_price=0.01, family_ref=TWIN, **windows):
    """One plans entry: the Draw's list price, generous caps (so only the
    window under test binds) and the declared family link."""
    caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0}
    caps.update(windows)
    return {"list_price": list_price, "caps": caps,
            "exposure": "no-retention", "family_ref": family_ref}


def market_model(mid):
    # $0.2/1M in, $1/1M out: the authoring profile (20k in, 40% cached at
    # $0/1M, 12k out) prices one ticket at $0.0024 + $0.0120 = $0.0144.
    return {"id": mid, "supported_parameters": ["reasoning_effort"],
            "pricing": {"prompt": "0.0000002", "completion": "0.000001",
                        "input_cache_read": "0"}}


class PickTwinCliTests(unittest.TestCase):
    """The whole run: which id the pick line names, and what sits beside it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        # The shared CLI lifecycle (test_cli.CliTests): injected fetchers,
        # patched local probe/cache/env, captured stdout/stderr. The scenario
        # fixtures below (policy, world, plan entries) stay this suite's own.
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)

    def with_policy(self, plans, exposure=None):
        # beta 1 prices the cost term, so the plan's risk-of-Draw keeps it on
        # top: a $0.01 Draw at default Free risk costs a third of a metered
        # ticket at $0.0144.
        policy = {
            "baseline": {"id": OTHER},
            "summaries": {},
            "free_models": {},
            "plans": plans,
            "domains": {"writing": ["content_writing"]},
            "scoring": {"alpha": 1.0, "beta": 1.0,
                        "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                                       "top2_max": 0.75}},
            "affinity": {
                "blend_weight": 0.6,
                "eligibility_top_k": 5,
                "factors": {"favor_validated": 3.0, "favor_suspected": 2.0,
                            "avoid_validated": 0.3, "avoid_suspected": 0.5},
            },
        }
        if exposure is not None:
            policy["exposure"] = exposure
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(policy, f)

    def run_pick(self, world, *argv):
        out, err, code, _ = self.cli.run_cli(
            "--domain", "writing", *argv, world=world,
            policy_path=self.policy_path)
        self.assertIn(code, (None, 0), err)
        return out, err

    def world(self, models, classified):
        return {"models": models, "classifications": {
            "as_of": "2026-10-17", "classifications": [
                {"tag": "content_writing", "usage_share": 1.0, "models": [
                    {"id": mid, "tag_usage_share": share}
                    for mid, share in classified]}]},
            "rankings": {"data": []}, "endpoints": {}}

    def twin_world(self):
        # Plan row 1, OTHER row 2, the Twin row 3: the order alone would pick
        # OTHER when the plan row is at cap.
        return self.world([market_model(TWIN), market_model(OTHER)],
                          [(PLAN, 0.6), (TWIN, 0.2), (OTHER, 0.35)])

    def test_an_at_cap_plan_row_names_its_twin_on_the_pick_line(self):
        # The plan row tops the task order, but one ticket's Draw ($0.01)
        # crosses its 5-hour window ($0.005): the pick is the family's
        # Metered Twin -- the pick line names its qualified id and nothing
        # else: the id names the market, so a metered pick states no price
        # and no Draw.
        self.with_policy({PLAN: plan_entry(five_hour=0.005)})
        printed, _ = self.run_pick(self.twin_world())
        self.assertIn(f"| 1 | {PLAN}", printed)
        self.assertIn(f"| 3 | {TWIN}", printed)
        pick_line = next(line for line in printed.splitlines()
                         if line.startswith("default pick (top of task order):"))
        self.assertEqual(f"default pick (top of task order): openrouter/{TWIN}",
                         pick_line)
        self.assertNotIn("$", pick_line)

    def test_a_plan_row_within_its_allowance_still_picks_itself(self):
        # The same order without the cap: the plan row is the pick, named in
        # its own namespace with the Draw beside the cash price, as today.
        self.with_policy({PLAN: plan_entry()})
        printed, _ = self.run_pick(self.twin_world())
        self.assertIn("default pick (top of task order): "
                      f"{PLAN} ($0.0000/ticket; Draw $0.01/ticket)", printed)

    def test_a_twin_cannot_rescue_a_sensitive_run_of_non_local_rows(self):
        # The declared link can never bypass the Exposure gate (ADR 0008):
        # under --sensitive every non-local row — the at-cap plan row, its
        # metered Twin and the fallback alike — is excluded, so nothing may
        # serve and the run stops with the blocked report instead of
        # picking. (The fall-through branch this test used to exercise — an
        # admission-excluded Twin resolving nothing while other rows are
        # admitted — is pinned at the deal seam by
        # test_allowance_ledger.test_an_ineligible_twin_is_no_twin; ADR 0008
        # makes the pick-side scenario unreachable with cloud rows only.)
        self.with_policy({PLAN: plan_entry(five_hour=0.005)},
                         exposure={TWIN: "trains"})
        printed, _ = self.run_pick(self.twin_world(), "--sensitive")
        self.assertNotIn("default pick", printed)
        self.assertIn("blocked: no eligible local candidate", printed)
        twin_row = next(ln for ln in printed.splitlines()
                        if ln.startswith("|") and f"{TWIN} |" in ln)
        self.assertIn("exposed (trains)", twin_row)

    def test_a_twin_the_run_does_not_play_resolves_nothing(self):
        # The declaration points at a market-shaped id the ranking never
        # lists: no row absorbs the ticket, so the next admitted row takes it.
        self.with_policy({PLAN: plan_entry(five_hour=0.005,
                                           family_ref=GHOST)})
        printed, _ = self.run_pick(
            self.world([market_model(TWIN), market_model(OTHER)],
                       [(PLAN, 0.6), (TWIN, 0.2), (OTHER, 0.35)]))
        self.assertIn(f"default pick (top of task order): openrouter/{OTHER}",
                      printed)

    def test_a_metered_pick_names_the_openrouter_namespace(self):
        # No plan rows in play: the pick line is still dispatch-ready --
        # `openrouter/` re-added to the normalized slug.
        self.with_policy({})
        printed, _ = self.run_pick(
            self.world([market_model(OTHER)], [(OTHER, 1.0)]))
        self.assertIn(f"default pick (top of task order): openrouter/{OTHER}",
                      printed)


if __name__ == "__main__":
    unittest.main()
