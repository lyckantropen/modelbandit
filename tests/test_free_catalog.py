"""Contract tests for the curated Free route catalog."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


FREE_MODELS = {
    "opencode/flash": {"context_length": 262_144,
                       "exposure": "no-retention",
                       "summary_ref": "family/flash"},
    "vendor/model": {"context_length": 65_536,
                     "exposure": "trains",
                     "summary_ref": "family/model"},
}
SUMMARIES = {"family/flash": "Flash is suitable for short coding tasks.",
             "family/model": "Model summary."}


class FreeCatalogPolicyTests(unittest.TestCase):
    def test_catalog_entries_load_with_window_exposure_and_summary_ref(self):
        self.assertEqual(modelbandit.load_free_models({"free_models": FREE_MODELS}),
                         FREE_MODELS)

    def test_missing_window_fails_loudly(self):
        with self.assertRaisesRegex(SystemExit, "free_models.opencode/flash.context_length"):
            modelbandit.load_free_models({"free_models": {
                "opencode/flash": {"exposure": "trains"}}})

    def test_invalid_exposure_fails_loudly(self):
        with self.assertRaisesRegex(SystemExit, "free_models.vendor/model.exposure"):
            modelbandit.load_free_models({"free_models": {
                "vendor/model": {"context_length": 65536,
                                 "exposure": "maybe"}}})

    def test_non_integer_window_fails_loudly(self):
        with self.assertRaisesRegex(SystemExit, "free_models.vendor/model.context_length"):
            modelbandit.load_free_models({"free_models": {
                "vendor/model": {"context_length": "65536",
                                 "exposure": "trains"}}})

    def test_invalid_completion_cap_fails_loudly(self):
        with self.assertRaisesRegex(
                SystemExit, "free_models.vendor/model.max_completion_tokens"):
            modelbandit.load_free_models({"free_models": {
                "vendor/model": {"context_length": 65_536,
                                  "max_completion_tokens": 0,
                                  "exposure": "trains"}}})

    def test_local_exposure_on_a_remote_prefix_fails_loudly(self):
        # Localness is a serving fact, never a catalogue claim: an
        # `opencode/*` or `:free` prefix names a remote serving identity, so
        # a `local` label there is a contradiction the policy stops — loudly,
        # naming the entry.
        for prefix in ("opencode/flash", "vendor/model:free"):
            with self.subTest(prefix=prefix), self.assertRaisesRegex(
                    SystemExit, f"free_models.{prefix}.exposure"):
                modelbandit.load_free_models({"free_models": {
                    prefix: {"context_length": 65_536,
                             "exposure": "local"}}})

    def test_local_exposure_override_on_a_remote_prefix_fails_loudly(self):
        with self.assertRaisesRegex(
                SystemExit, r"exposure\.opencode/flash: exposure 'local'"):
            modelbandit.load_exposure_overrides(
                {"exposure": {"opencode/flash": "local"}})
        with self.assertRaisesRegex(
                SystemExit, r"exposure\.vendor/model:free: exposure 'local'"):
            modelbandit.load_exposure_overrides(
                {"exposure": {"vendor/model:free": "local"}})


class FreeCandidateTests(unittest.TestCase):
    def test_cataloged_opencode_route_is_merged_with_catalog_window(self):
        share, models = modelbandit.merge_free_candidates(
            {}, {}, FREE_MODELS, SUMMARIES)
        self.assertIn("opencode/flash", share)
        self.assertEqual(models["opencode/flash"]["context_length"], 262_144)

    def test_ranked_free_route_keeps_its_own_slug_and_catalog_window(self):
        share = {"vendor/model:free": 0.25}
        models = {"vendor/model": {"id": "vendor/model", "pricing": {
            "prompt": "0", "completion": "0"}}}
        got_share, got_models = modelbandit.merge_free_candidates(
            share, models,
            {"vendor/model": FREE_MODELS["vendor/model"]}, SUMMARIES)
        self.assertEqual(got_share, {"vendor/model:free": 0.25})
        self.assertIn("vendor/model:free", got_models)
        self.assertEqual(got_models["vendor/model:free"]["context_length"], 65_536)

    def test_free_slug_stays_its_own_id_when_canonical_map_points_to_paid_route(self):
        base_model = {"id": "vendor/model", "pricing": {
            "prompt": "0.1", "completion": "0.2"}}
        classif = {"classifications": [{"tag": "coding", "usage_share": 1,
                                        "models": [{"id": "vendor/model:free",
                                                    "tag_usage_share": 0.4}]}]}
        share, _, _ = modelbandit.domain_candidates(
            classif, ["coding"], {"vendor/model": base_model},
            {"vendor/model:free": base_model})
        self.assertEqual(share, {"vendor/model:free": 0.4})

    def test_uncatalogued_free_route_remains_visible(self):
        share = {"vendor/unknown:free": 0.8}
        models = {"vendor/unknown:free": {"id": "vendor/unknown:free"}}
        got_share, _ = modelbandit.merge_free_candidates(share, models, {}, SUMMARIES)
        self.assertIn("vendor/unknown:free", got_share)

    def test_catalog_entry_without_summary_does_not_enter_candidate_set(self):
        share, models = modelbandit.merge_free_candidates(
            {}, {}, {"opencode/no-summary": {
                "context_length": 65536, "exposure": "trains"}}, SUMMARIES)
        self.assertNotIn("opencode/no-summary", share)
        self.assertNotIn("opencode/no-summary", models)

    def test_ranked_free_route_admits_by_longest_prefix_summary(self):
        policy = {
            "free_models": {},
            "summaries": {"nvidia/nemotron-3-ultra-550b": "family summary"},
        }
        mid = "nvidia/nemotron-3-ultra-550b-a55b:free"
        share, models = modelbandit.merge_free_candidates(
            {mid: 0.2},
            {mid: {"id": mid, "context_length": 1_048_576,
                   "pricing": {"prompt": "0", "completion": "0"}}},
            policy["free_models"], policy["summaries"])
        facts = modelbandit.candidate_for(
            mid, policy, model=models[mid])
        self.assertEqual(share[mid], 0.2)
        self.assertEqual(facts.context_length, 1_048_576)
        self.assertTrue(modelbandit.admit(modelbandit.Shape(), facts).admitted)

    def test_opencode_catalog_entry_without_a_summary_ref_enters_nothing(self):
        # Standing needs a summary reference: with none there is no row to
        # rank, judge or mark — only the entry's own window and Exposure are
        # still read by whatever does carry it. The assembly seam stays; what
        # changed is that nothing downstream excludes on missing completeness.
        policy = {"free_models": {"opencode/model": {
            "context_length": 65_536, "exposure": "trains"}},
            "summaries": {}}
        share, models = modelbandit.merge_free_candidates(
            {}, {}, policy["free_models"], policy["summaries"])
        self.assertNotIn("opencode/model", share)
        self.assertNotIn("opencode/model", models)

    def test_table_free_candidate_shows_window_and_exposure(self):
        self.assertEqual(modelbandit.free_candidate_details(
            "opencode/flash", {"free_models": FREE_MODELS}),
            (262_144, "no-retention"))
        self.assertEqual(modelbandit.free_candidate_details(
            "vendor/model:free", {"free_models": FREE_MODELS}),
            (65_536, "trains"))


if __name__ == "__main__":
    unittest.main()
