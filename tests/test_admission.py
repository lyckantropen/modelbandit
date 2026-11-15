"""Unit tests for the admission seam: Exposure resolution and the Sensitive gate.

`admit(shape, candidate)` is the seam: one pure decision shared by the ranked
table and the Deal path. Behind it sits the Exposure<->Sensitive gate; excluded
candidates stay visible with a reason, never hidden.

Fixture style follows test_deal.py: plain dicts for the policy facts
(EXPOSURE overrides, FREE catalog), frozen Shape/Candidate values for the
shape and the candidate under judgment.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

# Curated free-candidate catalog, id-prefix keyed (the policy's `free_models`).
FREE_MODELS = {
    "opencode/glm-5.3-flash": {"context_length": 262_144,
                               "exposure": "no-retention",
                               "summary_ref": "glm-5.3"},
    "z-ai/glm-5.3": {"context_length": 204_800,
                     "exposure": "trains",
                     "summary_ref": "glm-5.3"},
}
# Explicit per-prefix exposure overrides (the policy's `exposure` map).
OVERRIDES = {"z-ai/glm-5.3-flash:free": "no-retention",
             "z-ai/glm-5.3": "no-retention"}

SENSITIVE = modelbandit.Shape(sensitive=True)
ORDINARY = modelbandit.Shape(sensitive=False)


def candidate(mid, exposure):
    return modelbandit.Candidate(id=mid, exposure=exposure)


class ExposureResolutionTests(unittest.TestCase):
    """Exposure precedence: override > curated entry > ':free' => trains >
    default no-retention; a locally served model is local."""

    def test_paid_candidate_defaults_to_no_retention(self):
        self.assertEqual(modelbandit.resolve_exposure("deepseek/deepseek-v4-pro"),
                         "no-retention")

    def test_free_suffixed_slug_is_trains(self):
        self.assertEqual(modelbandit.resolve_exposure("z-ai/glm-5.4:free"), "trains")

    def test_curated_free_entry_beats_the_free_suffix(self):
        # A curated no-retention Free route is not exposed by its slug alone.
        self.assertEqual(
            modelbandit.resolve_exposure("opencode/glm-5.3-flash", free_models=FREE_MODELS),
            "no-retention")

    def test_uncatalogued_free_slug_stays_trains(self):
        # The safe assumption holds for a route the catalog does not carry.
        self.assertEqual(
            modelbandit.resolve_exposure("z-ai/glm-5.4:free", free_models=FREE_MODELS),
            "trains")

    def test_explicit_override_beats_curated_entry(self):
        # The catalog says this route trains; the override says otherwise.
        self.assertEqual(
            modelbandit.resolve_exposure("z-ai/glm-5.3", free_models=FREE_MODELS),
            "trains")
        self.assertEqual(
            modelbandit.resolve_exposure("z-ai/glm-5.3", free_models=FREE_MODELS,
                                  overrides=OVERRIDES),
            "no-retention")

    def test_explicit_override_beats_the_free_suffix(self):
        self.assertEqual(
            modelbandit.resolve_exposure("z-ai/glm-5.3-flash:free",
                                  free_models=FREE_MODELS, overrides=OVERRIDES),
            "no-retention")

    def test_overrides_are_prefix_keyed_longest_wins(self):
        overrides = {"z-ai/glm-5.3": "trains", "z-ai/glm-5.3-flash": "local"}
        self.assertEqual(modelbandit.resolve_exposure("z-ai/glm-5.3-prime",
                                               overrides=overrides), "trains")
        self.assertEqual(modelbandit.resolve_exposure("z-ai/glm-5.3-flash-2026",
                                               overrides=overrides), "local")

    def test_local_candidate_is_local(self):
        self.assertEqual(modelbandit.resolve_exposure("qwen3-coder-30b", local=True),
                         "local")

    def test_the_local_serving_fact_needs_loopback(self):
        # The serving flag says a candidate is served; only a loopback
        # endpoint makes that *this machine's* serving. A LAN-served
        # instance fails closed as exposed — unknown free defaults to
        # trains — until the policy's exposure-override map declares it,
        # and the namespace claim alone never changes that.
        self.assertEqual(
            modelbandit.resolve_exposure("lmstudio/qwen/qwen3-4b", local=True,
                                  loopback=False),
            "trains")
        self.assertEqual(
            modelbandit.resolve_exposure("lmstudio/qwen/qwen3-4b",
                                  free_models={"lmstudio/qwen": {
                                      "context_length": 65_536,
                                      "exposure": "local"}},
                                  loopback=False),
            "trains")
        self.assertEqual(
            modelbandit.resolve_exposure("lmstudio/qwen/qwen3-4b",
                                  overrides={"lmstudio/qwen": "local"},
                                  free_models={"lmstudio/qwen": {
                                      "context_length": 65_536,
                                      "exposure": "local"}},
                                  loopback=False),
            "local")
        # Loopback is the default: the normal serving resolves local.
        self.assertEqual(
            modelbandit.resolve_exposure("lmstudio/qwen/qwen3-4b",
                                  free_models={"lmstudio/qwen": {
                                      "context_length": 65_536,
                                      "exposure": "local"}}),
            "local")

    def test_candidate_for_carries_the_loopback_fact_into_admission(self):
        policy = {"free_models": {"lmstudio/qwen": {
            "context_length": 65_536, "exposure": "local",
            "summary_ref": "qwen"}},
            "summaries": {"qwen": "fixture summary"}}
        facts = modelbandit.candidate_for("lmstudio/qwen/qwen3-4b", policy,
                                   local=True, loopback=False)
        self.assertEqual(facts.exposure, "trains")
        decision = modelbandit.admit(modelbandit.Shape(sensitive=True), facts)
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, "exposed (trains)")

    def test_a_local_label_cannot_make_a_remote_identity_local(self):
        # Localness is a serving fact, never a catalogue claim: the route
        # predicate says an `opencode/*` or `:free` id is remote, so a policy
        # label is void there and the free-suffix default answers.
        label = {"context_length": 65_536, "exposure": "local"}
        self.assertEqual(
            modelbandit.resolve_exposure("vendor/model:free",
                                  free_models={"vendor/model": dict(label)}),
            "trains")
        self.assertEqual(
            modelbandit.resolve_exposure("opencode/flash",
                                  free_models={"opencode/flash": dict(label)}),
            "trains")
        self.assertEqual(
            modelbandit.resolve_exposure("vendor/model:free",
                                  overrides={"vendor/model": "local"}),
            "trains")

    def test_a_remote_free_route_labelled_local_is_refused_for_sensitive(self):
        # The same admission call the ranking uses: a stale policy's label
        # must not slip a remote Free route past the Sensitive gate.
        for mid, prefix in (("qwen/qwen3-coder-30b:free",
                             "qwen/qwen3-coder-30b"),
                            ("opencode/qwen3-coder-30b",
                             "opencode/qwen3-coder-30b")):
            policy = {"free_models": {prefix: {
                "context_length": 262_144, "exposure": "local",
                "summary_ref": "qwen"}},
                "summaries": {"qwen": "fixture summary"}}
            with self.subTest(mid=mid):
                facts = modelbandit.candidate_for(mid, policy)
                decision = modelbandit.admit(modelbandit.Shape(sensitive=True), facts)
                self.assertFalse(decision.admitted)
                self.assertIn("exposed (trains)", decision.reason)

    def test_unknown_exposure_value_fails_loudly(self):
        with self.assertRaisesRegex(SystemExit, "z-ai/glm-5.3"):
            modelbandit.resolve_exposure("z-ai/glm-5.3-x",
                                  overrides={"z-ai/glm-5.3": "no-retain"})


class AdmissionTests(unittest.TestCase):
    """admit(shape, candidate): the pure decision shared by the table and the
    deal. Exposure gates Sensitive shapes only — price never decides."""

    def test_exposed_candidate_excluded_from_sensitive_shape(self):
        decision = modelbandit.admit(SENSITIVE, candidate("z-ai/glm-5.3:free", "trains"))
        self.assertFalse(decision.admitted)
        self.assertIn("exposed", decision.reason)

    def test_exclusion_reason_names_the_exposure(self):
        decision = modelbandit.admit(SENSITIVE, candidate("z-ai/glm-5.3:free", "trains"))
        self.assertIn("trains", decision.reason)

    def test_no_retention_free_candidate_is_excluded_from_sensitive_shape(self):
        # ADR 0008: no-retention is a promise about storage, not about
        # transit — it leaves the machine like trains does, so Sensitive
        # refuses it alike, marked with the named reason.
        decision = modelbandit.admit(SENSITIVE,
                              candidate("opencode/glm-5.3-flash", "no-retention"))
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, "exposed (no-retention)")

    def test_paid_no_retention_candidate_is_excluded_from_sensitive_shape(self):
        # ADR 0008 applies to paid routes too: Exposure decides, never
        # price, and only `local` may serve a Sensitive shape.
        decision = modelbandit.admit(
            SENSITIVE, candidate("deepseek/deepseek-v4-pro", "no-retention"))
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, "exposed (no-retention)")

    def test_local_candidate_admitted_to_sensitive_shape(self):
        self.assertTrue(modelbandit.admit(
            SENSITIVE, candidate("qwen3-coder-30b", "local")))

    def test_ordinary_shape_admits_the_exposed_candidate(self):
        decision = modelbandit.admit(ORDINARY, candidate("z-ai/glm-5.3:free", "trains"))
        self.assertTrue(decision.admitted)
        self.assertEqual(decision.reason, "")

    def test_free_candidate_that_cannot_fit_is_excluded_with_context_reason(self):
        shape = modelbandit.Shape(input_tokens=20_000)
        facts = modelbandit.Candidate("nvidia/nemotron:free", "trains",
                               is_free=True, context_length=65_536)

        decision = modelbandit.admit(shape, facts)

        self.assertFalse(decision.admitted)
        self.assertIn("context", decision.reason)
        self.assertIn("over window", decision.reason)

    def test_free_candidate_over_rung_priced_completion_cap_is_excluded(self):
        shape = modelbandit.Shape(output_tokens=12_000)
        facts = modelbandit.Candidate("nvidia/nemotron:free", "trains",
                               is_free=True, completion_cap=16_000,
                               output_multiplier=2.5)

        decision = modelbandit.admit(shape, facts)

        self.assertFalse(decision.admitted)
        self.assertIn("over completion cap", decision.reason)

    def test_paid_candidate_over_completion_cap_is_admitted_with_flag(self):
        shape = modelbandit.Shape(output_tokens=12_000)
        facts = modelbandit.Candidate("vendor/model", "no-retention",
                               completion_cap=16_000, output_multiplier=2.5)

        decision = modelbandit.admit(shape, facts)

        self.assertTrue(decision.admitted)
        self.assertIn("over completion cap", decision.reason)

    def test_paid_candidate_over_window_is_admitted_with_flag(self):
        shape = modelbandit.Shape(input_tokens=40_000)
        facts = modelbandit.Candidate("vendor/model", "no-retention",
                               context_length=65_536)

        decision = modelbandit.admit(shape, facts)

        self.assertTrue(decision.admitted)
        self.assertIn("over window", decision.reason)

    def test_paid_candidate_is_not_context_gated(self):
        shape = modelbandit.Shape(input_tokens=40_000)
        facts = modelbandit.Candidate("vendor/model", "no-retention",
                               is_free=False, context_length=65_536)

        self.assertTrue(modelbandit.admit(shape, facts).admitted)

    def test_context_gate_calibration_for_all_profiles_and_windows(self):
        expected = {
            65_536: {"authoring": False, "agentic": False, "chat": True},
            262_144: {"authoring": True, "agentic": True, "chat": True},
            1_048_576: {"authoring": True, "agentic": True, "chat": True},
        }
        for window, profiles in expected.items():
            for profile, (input_tokens, _, _) in modelbandit.PROFILES.items():
                with self.subTest(window=window, profile=profile):
                    shape = modelbandit.Shape(input_tokens=input_tokens)
                    facts = modelbandit.Candidate("provider/route:free", "trains",
                                           is_free=True,
                                           context_length=window)
                    self.assertEqual(modelbandit.admit(shape, facts).admitted,
                                     profiles[profile])


class ContextPolicyTests(unittest.TestCase):
    POLICY = {
        "scoring": {"alpha": 1, "beta": 1,
                    "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                                   "top2_max": 0.75}},
        "affinity": {"blend_weight": 0.6, "eligibility_top_k": 5,
                     "factors": {"favor_validated": 3, "favor_suspected": 2,
                                 "avoid_validated": 0.3, "avoid_suspected": 0.5}},
    }

    def test_context_policy_defaults(self):
        config = modelbandit.load_policy_config(self.POLICY)
        self.assertEqual(config.context.headroom, 2.0)
        self.assertEqual(config.context.margin, 0.5)

    def test_context_policy_is_configurable(self):
        config = modelbandit.load_policy_config(
            {**self.POLICY,
             "context_gate": {"headroom": 3, "margin": 0.75}})
        self.assertEqual(config.context.headroom, 3.0)
        self.assertEqual(config.context.margin, 0.75)

    def test_configured_context_policy_changes_admission(self):
        config = modelbandit.load_policy_config(
            {**self.POLICY,
             "context_gate": {"headroom": 1, "margin": 0.75}})
        shape = modelbandit.Shape(input_tokens=20_000,
                           context_headroom=config.context.headroom,
                           context_margin=config.context.margin)
        free_route = modelbandit.Candidate("provider/route:free", "trains",
                                    is_free=True, context_length=65_536)

        self.assertTrue(modelbandit.admit(shape, free_route).admitted)

    def test_configured_context_margin_applies_to_completion_cap(self):
        config = modelbandit.load_policy_config(
            {**self.POLICY,
             "context_gate": {"headroom": 1, "margin": 0.75}})
        shape = modelbandit.Shape(output_tokens=20_000,
                           context_headroom=config.context.headroom,
                           context_margin=config.context.margin)
        free_route = modelbandit.Candidate("provider/route:free", "trains",
                                    is_free=True, completion_cap=25_000)

        decision = modelbandit.admit(shape, free_route)

        self.assertFalse(decision.admitted)
        self.assertIn("over completion cap", decision.reason)

    def test_invalid_context_policy_boundaries_fail_loudly(self):
        for policy in (
                {"context_gate": {"headroom": 0.99}},
                {"context_gate": {"headroom": float("inf")}},
                {"context_gate": {"margin": 0}},
                {"context_gate": {"margin": 1.01}},
                {"context_gate": {"margin": float("nan")}},):
            with self.subTest(policy=policy), self.assertRaisesRegex(
                    SystemExit, "context_gate"):
                modelbandit.load_policy_config({**self.POLICY, **policy})


class CandidateFactsTests(unittest.TestCase):
    """candidate_for binds the policy's override map and free catalog into the
    candidate the gate judges; an empty policy is the safe default."""

    POLICY = {"exposure": OVERRIDES, "free_models": FREE_MODELS,
              "summaries": {"glm-5.3": "fixture summary"}}

    def test_unknown_free_route_binds_as_trains(self):
        facts = modelbandit.candidate_for("z-ai/glm-5.4:free", self.POLICY)
        self.assertEqual(facts.exposure, "trains")
        self.assertFalse(modelbandit.admit(SENSITIVE, facts).admitted)

    def test_curated_no_retention_route_is_excluded_from_sensitive(self):
        # The binding still resolves the curated fact — and under ADR 0008
        # that fact is exactly what a Sensitive shape refuses: no local
        # Exposure, no admission. An ordinary shape admits it as before.
        facts = modelbandit.candidate_for("opencode/glm-5.3-flash", self.POLICY)
        self.assertEqual(facts.exposure, "no-retention")
        self.assertFalse(modelbandit.admit(SENSITIVE, facts).admitted)
        self.assertEqual(modelbandit.admit(SENSITIVE, facts).reason,
                         "exposed (no-retention)")
        self.assertTrue(modelbandit.admit(ORDINARY, facts).admitted)

    def test_candidate_binds_free_serving_and_catalog_window(self):
        facts = modelbandit.candidate_for("opencode/glm-5.3-flash", self.POLICY)
        self.assertTrue(facts.is_free)
        self.assertEqual(facts.context_length, 262_144)

    def test_free_route_uses_model_window_when_not_in_catalog(self):
        facts = modelbandit.candidate_for("vendor/model:free", {},
                                  model={"context_length": 65_536})
        self.assertTrue(facts.is_free)
        self.assertEqual(facts.context_length, 65_536)

    def test_endpoint_completion_cap_overrides_catalog_cap(self):
        policy = {"free_models": {"vendor/model": {
            "context_length": 65_536, "max_completion_tokens": 65_536,
            "exposure": "trains"}}}
        facts = modelbandit.candidate_for(
            "vendor/model:free", policy, model={},
            endpoints=[{"max_completion_tokens": 32_000},
                       {"max_completion_tokens": 16_000}])

        self.assertEqual(facts.completion_cap, 16_000)

    def test_catalog_completion_cap_is_fallback_without_endpoint_cap(self):
        policy = {"free_models": {"vendor/model": {
            "context_length": 65_536, "max_completion_tokens": 24_000,
            "exposure": "trains"}}}
        facts = modelbandit.candidate_for("vendor/model:free", policy, model={},
                                   endpoints=[{"pricing": {}}])

        self.assertEqual(facts.completion_cap, 24_000)

    def test_policy_override_is_read(self):
        facts = modelbandit.candidate_for("z-ai/glm-5.3-flash:free", self.POLICY)
        self.assertEqual(facts.exposure, "no-retention")

    def test_local_flag_binds_local(self):
        facts = modelbandit.candidate_for("qwen3-coder-30b", self.POLICY, local=True)
        self.assertEqual(facts.exposure, "local")

    def test_policy_without_exposure_facts_still_resolves(self):
        self.assertEqual(modelbandit.candidate_for("a/b:free", {}).exposure, "trains")
        self.assertEqual(modelbandit.candidate_for("a/b", {}).exposure, "no-retention")


if __name__ == "__main__":
    unittest.main()
