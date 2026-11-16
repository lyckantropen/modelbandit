"""The `plans` policy section: the plan catalog, validated loud (status 4).

`plans` is the single catalog every consumer reads a plan's facts from:
per model its list price, its three Allowance window caps (rolling 5-hour,
weekly, monthly), its training/retention fact (Exposure), and an optional
region opt-in. It is validated at the policy boundary exactly like
`free_models`: an unknown shape, a bad number, a misspelt Exposure or an id
that is not a Plan serving stops the run with a config error naming the
offending entry — nothing half-loaded, never a traceback, never a silent
default.

Both shared loaders (`policy_facts` for the pre-flight and the secrets
check, `load_policy_bundle` for the ranking run and the status report) run
the validation, so all four entry points stop with status 4 on a malformed
plans edit. The section is its own catalog: `free_models` keeps refusing
plan-kind entries unchanged (test_free_catalog_kinds), and `plans` refuses
anything that is not a Plan serving.

Fixtures are plain dicts; the entry-point matrix reuses test_cli's harness
(injected fetchers, temp policy, no network).
"""

import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
import modelbandit  # noqa: E402
import test_cli  # noqa: E402


PLAN_ID = "opencode-go/plan-model"
TWIN = "deepseek/deepseek-v4-pro"


def plan_entry(**overrides):
    """One plan entry's facts: list price, the three window caps, Exposure,
    and the declared family link to the Twin's Metered serving."""
    entry = {
        "list_price": 1.25,
        "caps": {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0},
        "exposure": "no-retention",
        "family_ref": TWIN,
    }
    entry.update(overrides)
    return entry


class PlansCatalogTests(unittest.TestCase):
    """load_plans: every field validated loudly, naming the entry."""

    def load(self, plans):
        return modelbandit.load_plans({"plans": plans})

    def test_a_valid_entry_loads_with_its_plan_facts_intact(self):
        # The catalog surfaces as the single source consumers read: the
        # loader validates without rewriting a fact.
        self.assertEqual(self.load({PLAN_ID: plan_entry()}),
                         {PLAN_ID: plan_entry()})

    def test_an_absent_section_loads_as_an_empty_catalog(self):
        self.assertEqual(modelbandit.load_plans({}), {})

    def test_a_non_object_section_is_refused(self):
        with self.assertRaisesRegex(
                SystemExit, r"policy plans must be an object"):
            modelbandit.load_plans({"plans": [plan_entry()]})

    def test_a_non_object_entry_is_refused_naming_it(self):
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy plans\.{re.escape(PLAN_ID)} must be an object"):
            self.load({PLAN_ID: "1.25"})

    def test_a_missing_list_price_is_refused(self):
        entry = plan_entry()
        del entry["list_price"]
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy missing required key: plans\."
                rf"{re.escape(PLAN_ID)}\.list_price"):
            self.load({PLAN_ID: entry})

    def test_a_bad_list_price_is_refused(self):
        # A price is money: a non-number, a negative number or a bool each
        # stop the load. Zero is not bad — it is the zero-Draw serving
        # (ADR-0006) — so the message says non-negative, not positive.
        for price in ("1.25", -0.01, True, float("nan")):
            with self.subTest(price=price), self.assertRaisesRegex(
                    SystemExit,
                    rf"plans\.{re.escape(PLAN_ID)}\.list_price must be "
                    rf"a non-negative number"):
                self.load({PLAN_ID: plan_entry(list_price=price)})

    def test_a_zero_list_price_loads_the_zero_draw_serving(self):
        # A free-in-plan, zero-Draw serving is a legitimate entry: its facts
        # load untouched so the pricing rule can fall back to the pool
        # cheapest basis (ADR-0006).
        self.assertEqual(self.load({PLAN_ID: plan_entry(list_price=0)}),
                         {PLAN_ID: plan_entry(list_price=0)})

    def test_a_missing_caps_object_is_refused(self):
        entry = plan_entry()
        del entry["caps"]
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy missing required key: plans\."
                rf"{re.escape(PLAN_ID)}\.caps"):
            self.load({PLAN_ID: entry})

    def test_a_non_object_caps_is_refused(self):
        with self.assertRaisesRegex(
                SystemExit,
                rf"plans\.{re.escape(PLAN_ID)}\.caps must be an object"):
            self.load({PLAN_ID: plan_entry(caps=[20.0, 100.0, 200.0])})

    def test_each_window_cap_is_required(self):
        # The ledger draws down all three windows; an entry missing one is
        # refused, naming the exact window key.
        for window in ("five_hour", "weekly", "monthly"):
            caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0}
            del caps[window]
            with self.subTest(window=window), self.assertRaisesRegex(
                    SystemExit,
                    rf"policy missing required key: plans\."
                    rf"{re.escape(PLAN_ID)}\.caps\.{window}"):
                self.load({PLAN_ID: plan_entry(caps=caps)})

    def test_a_window_cap_must_be_a_positive_number(self):
        # A cap is a real dollar allowance: zero, negative, non-numeric or
        # bool each stop the load, naming the window.
        for window in ("five_hour", "weekly", "monthly"):
            for cap in (0, -5, "20", None, True):
                caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0}
                caps[window] = cap
                with self.subTest(window=window, cap=cap), \
                        self.assertRaisesRegex(
                            SystemExit,
                            rf"plans\.{re.escape(PLAN_ID)}\.caps\."
                            rf"{window} must be a positive number"):
                    self.load({PLAN_ID: plan_entry(caps=caps)})

    def test_a_missing_training_retention_value_is_refused(self):
        entry = plan_entry()
        del entry["exposure"]
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy missing required key: plans\."
                rf"{re.escape(PLAN_ID)}\.exposure"):
            self.load({PLAN_ID: entry})

    def test_an_unknown_training_retention_value_is_refused(self):
        # A misspelt class would silently widen the Sensitive gate, so it
        # stops the load exactly as a misspelt free_models Exposure does.
        with self.assertRaisesRegex(
                SystemExit,
                rf"plans\.{re.escape(PLAN_ID)}\.exposure: unknown exposure"):
            self.load({PLAN_ID: plan_entry(exposure="exposd")})

    def test_a_local_label_on_a_plan_serving_is_a_contradiction(self):
        # Localness is a serving fact, never a catalogue claim: an
        # opencode-go/* id is remote whatever the entry says.
        with self.assertRaisesRegex(
                SystemExit,
                rf"plans\.{re.escape(PLAN_ID)}\.exposure: exposure 'local' "
                rf"contradicts the remote serving identity"):
            self.load({PLAN_ID: plan_entry(exposure="local")})

    def test_a_malformed_region_opt_in_is_refused(self):
        # The region opt-in is optional, but when present it is a list of
        # region names — anything else stops the load, naming the entry.
        for regions in ("eu", [1], [""], {"eu": True}):
            with self.subTest(regions=regions), self.assertRaisesRegex(
                    SystemExit,
                    rf"plans\.{re.escape(PLAN_ID)}\.regions must be a "
                    rf"list of non-empty strings"):
                self.load({PLAN_ID: plan_entry(regions=regions)})

    def test_region_opt_ins_may_be_omitted_or_stated(self):
        self.assertEqual(self.load({PLAN_ID: plan_entry()}),
                         {PLAN_ID: plan_entry()})
        stated = plan_entry(regions=["eu", "us"])
        self.assertEqual(self.load({PLAN_ID: stated}), {PLAN_ID: stated})

    def test_an_id_that_is_not_a_plan_serving_is_refused(self):
        # The seam decides what serves an id: a market slug, a harness
        # model, a free slug or an unclassifiable namespace each stop the
        # load, naming the entry — the plans catalog prices only Plan
        # servings, and free_models keeps refusing them in parallel.
        for mid in ("vendor/model", "opencode/flash", "vendor/model:free",
                    "vendor/team/model"):
            with self.subTest(mid=mid), self.assertRaisesRegex(
                    SystemExit,
                    rf"policy plans\.{re.escape(mid)}: route kind "
                    rf"'.+' is not a Plan route"):
                self.load({mid: plan_entry()})

    def test_nothing_is_half_loaded(self):
        # A refused entry after a good one still stops the whole load, so
        # the caller never sees a partial catalog.
        catalog = {PLAN_ID: plan_entry(), "vendor/model": plan_entry()}
        with self.assertRaises(SystemExit):
            self.load(catalog)


class SharedLoaderSurfaceTests(unittest.TestCase):
    """Both shared loaders surface the valid catalog: the one facts source."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        self.catalog = {PLAN_ID: plan_entry(regions=["eu"])}
        policy = json.loads(json.dumps(test_cli.POLICY))
        policy["plans"] = self.catalog
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(policy, f)

    def test_policy_facts_and_load_policy_bundle_both_surface_the_catalog(self):
        # policy_facts serves the pre-flight and the secrets check,
        # load_policy_bundle the ranking run and the status report: every
        # consumer reads plan facts off the same validated section.
        facts = modelbandit.policy_facts(self.policy_path)
        bundle = modelbandit.load_policy_bundle(self.policy_path)
        self.assertEqual(facts["plans"], self.catalog)
        self.assertEqual(bundle["plans"], self.catalog)


class PlansStatus4MatrixTests(unittest.TestCase):
    """A malformed plans edit stops the policy-reading entry points with
    status 4.

    The PolicyFileTests.assert_status_4_everywhere pattern, pointed at the
    plans section: ranking run, status report and pre-flight each answer 4
    with the message naming the offending entry — no traceback, no exit 1,
    no verdict. The secrets check is absent by design: the mode split
    (spec #75) leaves it answering material questions only, reading no
    policy.
    """

    ENTRY_POINTS = (
        ["--domain", "writing"],                    # the ranking run
        ["--status"],                               # the status report
        ["--assert-allowed",
         "--model", "deepseek/deepseek-v4-pro"],    # the pre-flight
    )

    def setUp(self):
        # test_cli's own harness: injected fetchers, temp policy, a zones
        # file declaring the machine open, no network.
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)
        self.policy_path = self.cli.policy_path

    def with_plans(self, plans):
        policy = json.loads(json.dumps(test_cli.POLICY))
        policy["plans"] = plans
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(policy, f)

    def run_gate(self, *argv):
        """A guard run with stdin and machine facts pinned: no console, no
        real machine, no network (the PolicyFileTests.run_gate pattern)."""
        with mock.patch.object(sys, "stdin", io.StringIO("")), \
                mock.patch("modelbandit.machine_facts",
                           return_value={"identifiers": []}):
            return self.cli.run_cli(*argv)

    def assert_status_4_everywhere(self, needle):
        for argv in self.ENTRY_POINTS:
            with self.subTest(entry=argv[0]):
                out, err, code, _ = self.run_gate(*argv)
                self.assertEqual(code, 4)
                self.assertIn(needle, err)
                self.assertNotIn("Traceback", err)

    def test_a_non_object_plans_section_stops_every_entry_point_with_status_4(self):
        self.with_plans([plan_entry()])
        self.assert_status_4_everywhere("policy plans must be an object")

    def test_a_malformed_entry_stops_every_entry_point_naming_the_offending_entry(self):
        entry = plan_entry()
        entry["caps"]["weekly"] = 0
        self.with_plans({PLAN_ID: entry})
        self.assert_status_4_everywhere(
            f"plans.{PLAN_ID}.caps.weekly must be a positive number")

    def test_a_valid_plans_section_loads_on_every_entry_point(self):
        self.with_plans({PLAN_ID: plan_entry()})
        expectations = (
            (["--domain", "writing"], "# Popularity ranking"),
            (["--status"], "policy: "),
            # --plain states the shape: under ADR 0008 the default
            # (Sensitive) shape would block this non-local route, which is
            # a verdict rather than a load failure either way.
            (["--assert-allowed", "--model", "deepseek/deepseek-v4-pro",
              "--plain"], "allowed: deepseek/deepseek-v4-pro"),
        )
        for argv, line in expectations:
            with self.subTest(entry=argv[0]):
                out, err, code, _ = self.run_gate(*argv)
                self.assertNotEqual(code, 4)
                self.assertNotIn("Traceback", err)
                self.assertIn(line, out)


class UnknownPlansKeyTests(unittest.TestCase):
    """An unknown key is a config error, never a later crash or a silently
    invented window: `caps` must state exactly the three Allowance windows,
    and an entry only the known plan facts."""

    def load(self, plans):
        return modelbandit.load_plans({"plans": plans})

    def test_an_unknown_caps_key_is_refused_naming_it(self):
        # A stray window key would otherwise invent an unauthorized boundary
        # (at_cap_verdict iterates caps.items()) or raise a traceback from
        # the crossing arithmetic: it stops the load instead.
        caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0,
                "daily": 5.0}
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy plans\.{re.escape(PLAN_ID)}\.caps: unknown window "
                rf"'daily'"):
            self.load({PLAN_ID: plan_entry(caps=caps)})

    def test_a_non_numeric_unknown_caps_key_is_refused_naming_it(self):
        # The same stray key with a non-numeric value must not reach
        # at_cap_verdict as a TypeError: the load names the key.
        caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0,
                "daily": "lots"}
        with self.assertRaisesRegex(
                SystemExit,
                rf"plans\.{re.escape(PLAN_ID)}\.caps: unknown window 'daily'"):
            self.load({PLAN_ID: plan_entry(caps=caps)})

    def test_an_unknown_entry_key_is_refused_naming_it(self):
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy plans\.{re.escape(PLAN_ID)}: unknown key 'budget'"):
            self.load({PLAN_ID: plan_entry(budget=10.0)})

    def test_an_unknown_key_refuses_the_whole_load(self):
        # Nothing half-loaded: a good entry before the offending one still
        # never reaches the caller.
        catalog = {PLAN_ID: plan_entry(),
                   "opencode-go/other-plan": plan_entry(regions=["eu"],
                                                        daily=1.0)}
        with self.assertRaises(SystemExit):
            self.load(catalog)


class UnknownPlansKeyStatus4Tests(unittest.TestCase):
    """An unknown plans key stops all four entry points with status 4.

    Reuses PlansStatus4MatrixTests' harness and entry-point matrix: the
    section validates on the shared loaders, so no entry point sees a
    traceback or a half-loaded catalog.
    """

    def setUp(self):
        self.matrix = PlansStatus4MatrixTests()
        self.matrix.setUp()
        self.addCleanup(self.matrix.tearDown)

    def test_an_unknown_caps_key_stops_every_entry_point_with_status_4(self):
        caps = {"five_hour": 20.0, "weekly": 100.0, "monthly": 200.0,
                "daily": 5.0}
        self.matrix.with_plans({PLAN_ID: plan_entry(caps=caps)})
        self.matrix.assert_status_4_everywhere(
            f"plans.{PLAN_ID}.caps: unknown window 'daily'")

    def test_an_unknown_entry_key_stops_every_entry_point_with_status_4(self):
        self.matrix.with_plans({PLAN_ID: plan_entry(budget=10.0)})
        self.matrix.assert_status_4_everywhere(
            f"plans.{PLAN_ID}: unknown key 'budget'")


class FamilyLinkTests(unittest.TestCase):
    """load_plans: every entry declares its Twin — the family link is the
    declaration, never derived, and a link that does not resolve refuses the
    load naming the entry (status 4), so no half-loaded catalog ships."""

    def load(self, plans):
        return modelbandit.load_plans({"plans": plans})

    def test_a_declared_family_link_loads_and_stays_available_downstream(self):
        # Load acceptance only: the loader validates without rewriting the
        # declared link, so downstream resolution reads the declaration.
        catalog = {PLAN_ID: plan_entry()}
        self.assertEqual(self.load(catalog)[PLAN_ID]["family_ref"], TWIN)

    def test_a_missing_family_link_is_refused_naming_the_entry(self):
        entry = plan_entry()
        del entry["family_ref"]
        with self.assertRaisesRegex(
                SystemExit,
                rf"policy missing required key: plans\."
                rf"{re.escape(PLAN_ID)}\.family_ref"):
            self.load({PLAN_ID: entry})

    def test_a_family_link_must_be_a_non_empty_string(self):
        # A link is an id, exactly as `summary_ref` is a key: anything else
        # would resolve to nothing at run time.
        for ref in ("", "   ", 42, None, [TWIN], {"id": TWIN}):
            with self.subTest(ref=ref), self.assertRaisesRegex(
                    SystemExit,
                    rf"plans\.{re.escape(PLAN_ID)}\.family_ref must be "
                    rf"a non-empty string"):
                self.load({PLAN_ID: plan_entry(family_ref=ref)})

    def test_a_family_link_that_is_not_a_metered_route_is_refused_naming_the_entry(self):
        # The Twin is the family's Metered serving. A plan id, a harness
        # model, a :free slug or an unclassifiable namespace names no
        # metered row, so the link cannot resolve: the load stops.
        for ref in ("opencode-go/other-plan", "opencode/flash",
                    "vendor/model:free", "vendor/team/model", "nope"):
            with self.subTest(ref=ref), self.assertRaisesRegex(
                    SystemExit,
                    rf"policy plans\.{re.escape(PLAN_ID)}\.family_ref "
                    rf"'{re.escape(ref)}': route kind '.+' is not a "
                    rf"Metered route"):
                self.load({PLAN_ID: plan_entry(family_ref=ref)})

    def test_the_link_is_the_declaration_never_a_slug_derivation(self):
        # The declared Twin shares no slug with the plan id and is not the
        # family the plan's own shape would suggest: vendor prefixes differ
        # per family, so only the declaration may say where the Twin is.
        plan = "opencode-go/vendor-suite"
        catalog = {plan: plan_entry(family_ref=TWIN)}
        self.assertEqual(self.load(catalog)[plan]["family_ref"], TWIN)

    def test_a_refused_link_leaves_nothing_half_loaded(self):
        catalog = {PLAN_ID: plan_entry(),
                   "opencode-go/other-plan": plan_entry(family_ref="nope")}
        with self.assertRaises(SystemExit):
            self.load(catalog)


class FamilyLinkSurfaceTests(unittest.TestCase):
    """Both shared loaders surface the declared link: one validated catalog."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.policy_path = os.path.join(self._tmp.name, "policy.json")
        self.catalog = {PLAN_ID: plan_entry(family_ref=TWIN)}
        policy = json.loads(json.dumps(test_cli.POLICY))
        policy["plans"] = self.catalog
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(policy, f)

    def test_policy_facts_and_load_policy_bundle_both_surface_the_link(self):
        facts = modelbandit.policy_facts(self.policy_path)
        bundle = modelbandit.load_policy_bundle(self.policy_path)
        for loaded in (facts, bundle):
            self.assertEqual(loaded["plans"][PLAN_ID]["family_ref"], TWIN)


class FamilyLinkStatus4Tests(unittest.TestCase):
    """A link that does not resolve stops all four entry points with status 4.

    Reuses PlansStatus4MatrixTests' harness and entry-point matrix: the link
    validates on the shared loaders, so no entry point half-loads a catalog.
    """

    def setUp(self):
        self.matrix = PlansStatus4MatrixTests()
        self.matrix.setUp()
        self.addCleanup(self.matrix.tearDown)

    def test_an_unresolvable_family_link_stops_every_entry_point_with_status_4(self):
        self.matrix.with_plans({PLAN_ID: plan_entry(family_ref="opencode-go/other")})
        self.matrix.assert_status_4_everywhere(
            f"plans.{PLAN_ID}.family_ref 'opencode-go/other': route kind "
            f"'plan' is not a Metered route")

    def test_a_missing_family_link_stops_every_entry_point_with_status_4(self):
        entry = plan_entry()
        del entry["family_ref"]
        self.matrix.with_plans({PLAN_ID: entry})
        self.matrix.assert_status_4_everywhere(
            f"missing required key: plans.{PLAN_ID}.family_ref")


if __name__ == "__main__":
    unittest.main()
