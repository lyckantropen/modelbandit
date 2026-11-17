"""The dispatch contract: the pre-flight never answers looser than the plan.

An orchestrator that asks `--assert-allowed` whether a model may serve gets an
answer no more permissive than the plan's admission, in both dimensions the
mechanism promises — Exposure and the free-use zone. The plan's verdict is
taken through the same admission seam the ranked table and the deal consult
(`admit`), its catalog and Footprint clauses neutralized so the two gates
judge the same clauses; the pre-flight's verdict is read at its **egress**
(issue #41, exit contract v2): the printed `allowed:` / `blocked by the
free-use zone` lines say which answer came back, and the status is pinned to
0 for either — status says the tool ran, the line says what's true, so the
property can never lean on a status code again.

The property is pinned across a small matrix of Exposure, zone posture and
route kind (paid, `:free`, `opencode/*`, locally served).

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

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

ENTRY = {"context_length": 262_144, "summary_ref": "s"}
SUMMARIES = {"s": "fixture summary"}
POSTURES = ("open", "closed")

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


class EgressVerdictMixin:
    """Read the pre-flight's verdict at its egress — never from a status."""

    def preflight_answer(self, mid, zone, policy, *, sensitive_preflight,
                         endpoint=None):
        """The pre-flight's verdict for one cell.

        Runs `run_assert_allowed` for the cell's zone and policy (both
        injected the way a caller supplies them) and reads the printed
        verdict lines: exactly one of `allowed: <id>` or `blocked by the
        free-use zone` must come back, and the exit contract v2 pins the
        status to 0 for either answer — the status never carries the
        verdict. The harness endpoint is pinned to the fixture machine's
        loopback default (a `local` Exposure's condition), so the verdict
        never depends on this machine's real config; `endpoint` states
        another serving for the loopback cells.
        """
        printed = io.StringIO()
        with mock.patch.object(modelbandit, "effective_zone",
                               return_value=zone), \
                mock.patch.object(modelbandit, "policy_facts",
                                  return_value=policy), \
                mock.patch.object(modelbandit, "harness_serving_endpoint",
                                  return_value=endpoint or
                                  modelbandit.DEFAULT_LOCAL_ENDPOINT), \
                redirect_stdout(printed):
            code = modelbandit.run_assert_allowed(
                model=mid, plain=not sensitive_preflight)
        out = printed.getvalue()
        allowed = [line for line in out.splitlines()
                   if line.startswith("allowed: ")]
        blocked = [line for line in out.splitlines()
                   if line == "blocked: free-use zone"]
        self.assertEqual(len(allowed) + len(blocked), 1,
                         f"exactly one verdict line expected, got:\n{out}")
        self.assertEqual(
            code, 0, f"any verdict exits 0 (issue #41), got {code!r}:\n{out}")
        return bool(allowed), out


class PreflightNeverLooserThanPlanTests(EgressVerdictMixin,
                                        unittest.TestCase):
    """The pre-flight's `allowed:` verdict only where the plan's admission
    admits the same route and shape."""

    def assert_never_looser(self, mid, policy, *, local, sensitive_plan,
                            sensitive_preflight):
        for posture in POSTURES:
            zone = modelbandit.Zone(path="z", posture=posture)
            with self.subTest(mid=mid, posture=posture,
                              sensitive_plan=sensitive_plan,
                              sensitive_preflight=sensitive_preflight):
                allowed, printed = self.preflight_answer(
                    mid, zone, policy, sensitive_preflight=sensitive_preflight)
                shape = modelbandit.Shape(
                    material_sensitive=sensitive_plan, posture=zone.posture)
                plan = modelbandit.admit(shape, modelbandit.candidate_for(mid, policy,
                                                            local=local))
                if allowed:
                    self.assertTrue(plan.admitted, (
                        f"pre-flight allows {mid} at posture {posture} "
                        f"(preflight sensitive={sensitive_preflight}) but the "
                        f"plan refuses it (plan sensitive={sensitive_plan}, "
                        f"reason: {plan.reason}); pre-flight output:\n"
                        f"{printed}"))

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


class LocalLabelRefusedByBothGatesTests(EgressVerdictMixin,
                                        unittest.TestCase):
    """A remote Free route labelled `local` is refused for a Sensitive shape
    and refused in a closed zone — by the plan's source filter and by the
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
                shape = modelbandit.Shape(material_sensitive=True,
                                          posture="open")
                plan = modelbandit.admit(shape, modelbandit.candidate_for(mid, policy,
                                                            local=local))
                self.assertFalse(plan.admitted)
                self.assertIn("exposed (trains)", plan.reason)
                closed = modelbandit.Shape(posture="closed")
                source = modelbandit.zone_prohibition(
                    closed.posture,
                    modelbandit.candidate_for(mid, policy, local=local))
                self.assertIn("remote free route is prohibited", source)
                # The pre-flight, read at its egress: the same refusals.
                allowed, printed = self.preflight_answer(
                    mid, modelbandit.Zone(path="z", posture="closed"), policy,
                    sensitive_preflight=False)
                self.assertFalse(allowed)
                self.assertIn("remote free route is prohibited", printed)
                allowed, printed = self.preflight_answer(
                    mid, modelbandit.Zone(path="z", posture="open"),
                    policy, sensitive_preflight=True)
                self.assertFalse(allowed)
                self.assertIn(
                    "only Exposure local may serve a Sensitive shape (trains)",
                    printed)


class SensitivePreflightIsLocalOnlyTests(EgressVerdictMixin,
                                         unittest.TestCase):
    """ADR 0008 at the pre-flight: a Sensitive-shape answer blocks every
    non-local route, no-retention alike — a vendor promise about storage is
    not containment in transit — and both gates judge the same route the
    same way, whether Sensitive came from material (`--sensitive`, or the
    assumed default) or from place (a closed zone)."""

    def test_a_no_retention_route_is_blocked_for_a_sensitive_shape(self):
        policy = policy_for("vendor/paid", "no-retention")
        for zone, sensitive_preflight in (
                (modelbandit.Zone(path="z", posture="open"), True),
                (modelbandit.Zone(path="z", posture="closed"), False)):
            with self.subTest(posture=zone.posture,
                              sensitive_preflight=sensitive_preflight):
                allowed, printed = self.preflight_answer(
                    "vendor/paid", zone, policy,
                    sensitive_preflight=sensitive_preflight)
                self.assertFalse(allowed)
                self.assertIn(
                    "only Exposure local may serve a Sensitive shape "
                    "(no-retention)", printed)
                # The plan's admission refuses the same route for the same
                # shape: the pre-flight never answers looser than the plan.
                shape = modelbandit.Shape(
                    material_sensitive=sensitive_preflight, posture=zone.posture)
                plan = modelbandit.admit(
                    shape, modelbandit.candidate_for("vendor/paid", policy,
                                                     local=False))
                self.assertFalse(plan.admitted)
                self.assertEqual(plan.reason, "exposed (no-retention)")

    def test_plain_states_the_shape_and_the_route_is_allowed(self):
        # The one deliberate exception: `--plain` vouches the material is
        # not Sensitive, and an open zone judges the route as stated.
        policy = policy_for("vendor/paid", "no-retention")
        allowed, _ = self.preflight_answer(
            "vendor/paid", modelbandit.Zone(path="z", posture="open"),
            policy, sensitive_preflight=False)
        self.assertTrue(allowed)


class LoopbackServingTests(EgressVerdictMixin, unittest.TestCase):
    """`local` Exposure's loopback rule at the pre-flight: the harness's
    `lmstudio/*` namespace classifies local, but only a loopback endpoint
    makes the serving this machine's — a LAN-served instance is refused as
    exposed until the policy's exposure-override map declares it."""

    LAN = "http://desktop-rme135a.tail409f29.ts.net:1234/v1"

    def test_local_exposure_survives_the_pre_flight_only_on_loopback(self):
        zone = modelbandit.Zone(path="z", posture="open")
        policy = policy_for("lmstudio/qwen", "local")

        allowed, printed = self.preflight_answer(
            "lmstudio/qwen/qwen3-4b", zone, policy,
            sensitive_preflight=True, endpoint=self.LAN)
        self.assertFalse(allowed)
        self.assertIn(
            "only Exposure local may serve a Sensitive shape (trains)",
            printed)

        allowed, _ = self.preflight_answer(
            "lmstudio/qwen/qwen3-4b", zone, policy, sensitive_preflight=True)
        self.assertTrue(allowed)

        declared = dict(policy, exposure={"lmstudio/qwen": "local"})
        allowed, _ = self.preflight_answer(
            "lmstudio/qwen/qwen3-4b", zone, declared,
            sensitive_preflight=True, endpoint=self.LAN)
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
