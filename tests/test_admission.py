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
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402

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

SENSITIVE = bind.Shape(sensitive=True)
ORDINARY = bind.Shape(sensitive=False)


def candidate(mid, exposure):
    return bind.Candidate(id=mid, exposure=exposure)


class ExposureResolutionTests(unittest.TestCase):
    """Exposure precedence: override > curated entry > ':free' => trains >
    default no-retention; a locally served model is local."""

    def test_paid_candidate_defaults_to_no_retention(self):
        self.assertEqual(bind.resolve_exposure("deepseek/deepseek-v4-pro"),
                         "no-retention")

    def test_free_suffixed_slug_is_trains(self):
        self.assertEqual(bind.resolve_exposure("z-ai/glm-5.4:free"), "trains")

    def test_curated_free_entry_beats_the_free_suffix(self):
        # A curated no-retention Free route is not exposed by its slug alone.
        self.assertEqual(
            bind.resolve_exposure("opencode/glm-5.3-flash", free_models=FREE_MODELS),
            "no-retention")

    def test_uncatalogued_free_slug_stays_trains(self):
        # The safe assumption holds for a route the catalog does not carry.
        self.assertEqual(
            bind.resolve_exposure("z-ai/glm-5.4:free", free_models=FREE_MODELS),
            "trains")

    def test_explicit_override_beats_curated_entry(self):
        # The catalog says this route trains; the override says otherwise.
        self.assertEqual(
            bind.resolve_exposure("z-ai/glm-5.3", free_models=FREE_MODELS),
            "trains")
        self.assertEqual(
            bind.resolve_exposure("z-ai/glm-5.3", free_models=FREE_MODELS,
                                  overrides=OVERRIDES),
            "no-retention")

    def test_explicit_override_beats_the_free_suffix(self):
        self.assertEqual(
            bind.resolve_exposure("z-ai/glm-5.3-flash:free",
                                  free_models=FREE_MODELS, overrides=OVERRIDES),
            "no-retention")

    def test_overrides_are_prefix_keyed_longest_wins(self):
        overrides = {"z-ai/glm-5.3": "trains", "z-ai/glm-5.3-flash": "local"}
        self.assertEqual(bind.resolve_exposure("z-ai/glm-5.3-prime",
                                               overrides=overrides), "trains")
        self.assertEqual(bind.resolve_exposure("z-ai/glm-5.3-flash-2026",
                                               overrides=overrides), "local")

    def test_local_candidate_is_local(self):
        self.assertEqual(bind.resolve_exposure("qwen3-coder-30b", local=True),
                         "local")

    def test_unknown_exposure_value_fails_loudly(self):
        with self.assertRaisesRegex(SystemExit, "z-ai/glm-5.3"):
            bind.resolve_exposure("z-ai/glm-5.3-x",
                                  overrides={"z-ai/glm-5.3": "no-retain"})


class AdmissionTests(unittest.TestCase):
    """admit(shape, candidate): the pure decision shared by the table and the
    deal. Exposure gates Sensitive shapes only — price never decides."""

    def test_exposed_candidate_excluded_from_sensitive_shape(self):
        decision = bind.admit(SENSITIVE, candidate("z-ai/glm-5.3:free", "trains"))
        self.assertFalse(decision.admitted)
        self.assertIn("exposed", decision.reason)

    def test_exclusion_reason_names_the_exposure(self):
        decision = bind.admit(SENSITIVE, candidate("z-ai/glm-5.3:free", "trains"))
        self.assertIn("trains", decision.reason)

    def test_no_retention_free_candidate_admitted_to_sensitive_shape(self):
        decision = bind.admit(SENSITIVE,
                              candidate("opencode/glm-5.3-flash", "no-retention"))
        self.assertTrue(decision.admitted)

    def test_paid_candidate_admitted_to_sensitive_shape(self):
        self.assertTrue(bind.admit(
            SENSITIVE, candidate("deepseek/deepseek-v4-pro", "no-retention")))

    def test_local_candidate_admitted_to_sensitive_shape(self):
        self.assertTrue(bind.admit(
            SENSITIVE, candidate("qwen3-coder-30b", "local")))

    def test_ordinary_shape_admits_the_exposed_candidate(self):
        decision = bind.admit(ORDINARY, candidate("z-ai/glm-5.3:free", "trains"))
        self.assertTrue(decision.admitted)
        self.assertEqual(decision.reason, "")


class CandidateFactsTests(unittest.TestCase):
    """candidate_for binds the policy's override map and free catalog into the
    candidate the gate judges; an empty policy is the safe default."""

    POLICY = {"exposure": OVERRIDES, "free_models": FREE_MODELS}

    def test_unknown_free_route_binds_as_trains(self):
        facts = bind.candidate_for("z-ai/glm-5.4:free", self.POLICY)
        self.assertEqual(facts.exposure, "trains")
        self.assertFalse(bind.admit(SENSITIVE, facts).admitted)

    def test_curated_no_retention_route_binds_admitted(self):
        facts = bind.candidate_for("opencode/glm-5.3-flash", self.POLICY)
        self.assertEqual(facts.exposure, "no-retention")
        self.assertTrue(bind.admit(SENSITIVE, facts).admitted)

    def test_policy_override_is_read(self):
        facts = bind.candidate_for("z-ai/glm-5.3-flash:free", self.POLICY)
        self.assertEqual(facts.exposure, "no-retention")

    def test_local_flag_binds_local(self):
        facts = bind.candidate_for("qwen3-coder-30b", self.POLICY, local=True)
        self.assertEqual(facts.exposure, "local")

    def test_policy_without_exposure_facts_still_resolves(self):
        self.assertEqual(bind.candidate_for("a/b:free", {}).exposure, "trains")
        self.assertEqual(bind.candidate_for("a/b", {}).exposure, "no-retention")


if __name__ == "__main__":
    unittest.main()
