"""The dispatch contract: the pre-flight never answers looser than the plan.

An orchestrator that asks `--assert-allowed` whether a model may serve gets an
answer no more permissive than the plan's admission, in both dimensions the
mechanism promises — Exposure and the free-use zone. The property is pinned
across a small matrix of Exposure, regime and route kind (paid, `:free`,
`opencode/*`, locally served), with the plan's verdict taken through the same
admission seam the ranked table and the deal consult (`admit`), its catalog
and Footprint clauses neutralized so the two gates judge the same clauses.

The matrix includes the stale-policy cells a `local` catalogue label on a
remote serving identity would produce (constructed directly, bypassing the
policy boundary on purpose): localness is a serving fact, never a catalogue
claim, so neither gate may let such a label skip the Sensitive gate or the
closed-zone prohibition.

The one deliberate exception to the property is the explicit `--plain`
statement on the pre-flight, which is the caller vouching that the material is
not Sensitive — an unstated shape is Sensitive for both gates, and a stated
shape is judged as stated on both sides.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402

ENTRY = {"context_length": 262_144, "summary_ref": "s"}
SUMMARIES = {"s": "fixture summary"}
REGIMES = ("open", "sensitive", "closed")

# (route kind, mid, catalog prefix, constructible Exposures, plan-local).
# The `local` Exposure on a remote kind is the stale-policy cell: the policy
# boundary rejects it, and the gates must refuse it anyway.
CELLS = [
    ("paid", "vendor/paid", "vendor/paid",
     ("no-retention", "trains", "local"), False),
    (":free", "vendor/free:free", "vendor/free",
     ("no-retention", "trains", "local"), False),
    ("opencode/*", "opencode/glm", "opencode/glm",
     ("no-retention", "trains", "local"), False),
    ("locally served", "lm/qwen-30b", "lm/qwen", ("local",), True),
]


def policy_for(prefix: str, exposure: str) -> dict:
    return {"free_models": {prefix: dict(ENTRY, exposure=exposure)},
            "summaries": SUMMARIES}


class PreflightNeverLooserThanPlanTests(unittest.TestCase):
    """zone_block is None (the pre-flight allows) only where the plan's
    admission admits the same route and shape."""

    def assert_never_looser(self, mid, policy, *, local, sensitive_plan,
                            sensitive_preflight):
        for regime in REGIMES:
            zone = bind.Zone(path="z", regime=regime)
            with self.subTest(mid=mid, regime=regime,
                              sensitive_plan=sensitive_plan,
                              sensitive_preflight=sensitive_preflight):
                preflight = bind.zone_block(mid, zone, policy=policy,
                                            sensitive=sensitive_preflight)
                shape = bind.Shape(
                    sensitive=sensitive_plan,
                    regime=bind.shape_regime(zone,
                                             sensitive=sensitive_plan))
                plan = bind.admit(shape, bind.candidate_for(mid, policy,
                                                            local=local))
                if preflight is None:
                    self.assertTrue(plan.admitted, (
                        f"pre-flight allows {mid} at regime {regime} "
                        f"(preflight sensitive={sensitive_preflight}) but the "
                        f"plan refuses it (plan sensitive={sensitive_plan}, "
                        f"reason: {plan.reason})"))

    def test_the_same_shape_never_loses_to_the_pre_flight(self):
        for kind, mid, prefix, exposures, local in CELLS:
            for exposure in exposures:
                policy = policy_for(prefix, exposure)
                for sensitive in (False, True):
                    with self.subTest(kind=kind, exposure=exposure,
                                      sensitive=sensitive):
                        self.assert_never_looser(
                            mid, policy, local=local,
                            sensitive_plan=sensitive,
                            sensitive_preflight=sensitive)

    def test_the_assumed_shape_is_never_looser_than_a_plain_plan(self):
        # The fail-closed default: an orchestrator that states no shape is
        # answered for Sensitive, which must not allow anything the plan would
        # refuse for the loosest (plain) shape either.
        for kind, mid, prefix, exposures, local in CELLS:
            for exposure in exposures:
                with self.subTest(kind=kind, exposure=exposure):
                    self.assert_never_looser(
                        mid, policy_for(prefix, exposure), local=local,
                        sensitive_plan=False, sensitive_preflight=True)


class LocalLabelRefusedByBothGatesTests(unittest.TestCase):
    """A remote Free route labelled `local` is refused for a Sensitive shape
    and refused in a closed regime — by the plan's source filter and by the
    pre-flight alike; the two gates cannot disagree about the same route."""

    def test_both_gates_refuse_the_labelled_remote_route(self):
        for kind, mid, prefix, exposure, local in (
                (":free", "qwen/qwen3-coder-30b:free",
                 "qwen/qwen3-coder-30b", "local", False),
                ("opencode/*", "opencode/qwen3-coder-30b",
                 "opencode/qwen3-coder-30b", "local", False)):
            policy = policy_for(prefix, exposure)
            with self.subTest(kind=kind):
                # The plan's source filter: the route never enters the pool.
                shape = bind.Shape(sensitive=True, regime="sensitive")
                plan = bind.admit(shape, bind.candidate_for(mid, policy,
                                                            local=local))
                self.assertFalse(plan.admitted)
                self.assertIn("exposed (trains)", plan.reason)
                closed = bind.Shape(regime="closed")
                source = bind.zone_prohibition(
                    closed, bind.candidate_for(mid, policy, local=local))
                self.assertIn("remote free route is prohibited", source)
                # The pre-flight: the same refusals, zone_block answering.
                self.assertIn(
                    "remote free route is prohibited",
                    bind.zone_block(mid, bind.Zone(path="z", regime="closed"),
                                    policy=policy))
                self.assertIn(
                    "exposed (trains)",
                    bind.zone_block(mid, bind.Zone(path="z",
                                                   regime="sensitive"),
                                    policy=policy, sensitive=True))


if __name__ == "__main__":
    unittest.main()
