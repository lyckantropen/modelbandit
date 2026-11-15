"""Family-share inheritance for curated Free routes (the opencode/* and local tracks).

Catalog entries have no leaderboard row of their own, so their standing in a
domain is the family's revealed preference — the same popularity discipline the
OpenRouter :free track gets from the boards. Every other rule (Exposure gate,
Context gate, Nominal floor) already runs through the shared admission seam.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


def catalog(entries):
    return {k: {"context_length": 1048576, "exposure": "trains", **v}
            for k, v in entries.items()}


SHARE = {
    "deepseek/deepseek-v4.1-flash": 0.008,
    "deepseek/deepseek-v4.1-flash-1017": 0.0172,
    "z-ai/glm-5.3-flash": 0.003,
    "openai/gpt-6-luna": 0.0044,
}
SUMMARIES = {
    "deepseek/deepseek-v4.1-flash": "family summary",
    "z-ai/glm-5.3-flash": "family summary",
    "nvidia/nemotron-3-ultra-550b-a55b": "family summary",
}


class OpenCodeInheritanceTests(unittest.TestCase):
    def test_entry_inherits_family_total_across_variants(self):
        cat = catalog({
            "opencode/deepseek-v4.1-flash-free": {
                "exposure": "no-retention",
                "summary_ref": "deepseek/deepseek-v4.1-flash",
            },
            "opencode/glm-5.3-flash-free": {
                "exposure": "no-retention",
                "summary_ref": "z-ai/glm-5.3-flash",
            },
        })
        share, _ = modelbandit.merge_free_candidates(dict(SHARE), {}, cat, SUMMARIES,
                                             inheritance=1.0)
        self.assertAlmostEqual(
            share["opencode/deepseek-v4.1-flash-free"], 0.008 + 0.0172)
        self.assertAlmostEqual(share["opencode/glm-5.3-flash-free"], 0.003)

    def test_unranked_family_stays_zero(self):
        cat = catalog({"opencode/nope-free": {
            "exposure": "trains",
            "summary_ref": "deepseek/deepseek-v4.1-flash",
        }})
        share, _ = modelbandit.merge_free_candidates(
            {"z-ai/glm-5.3-flash": 0.003}, {}, cat, SUMMARIES)
        self.assertEqual(share["opencode/nope-free"], 0.0)

    def test_dated_free_row_counts_toward_family(self):
        share2 = dict(SHARE)
        share2["nvidia/nemotron-3-ultra-550b-a55b-20260604:free"] = 0.0018
        cat = catalog({"opencode/nemotron-3-ultra-free": {
            "exposure": "trains",
            "summary_ref": "nvidia/nemotron-3-ultra-550b-a55b",
        }})
        share, _ = modelbandit.merge_free_candidates(share2, {}, cat, SUMMARIES,
                                             inheritance=1.0)
        self.assertAlmostEqual(share["opencode/nemotron-3-ultra-free"], 0.0018)

    def test_entry_without_summary_ref_is_not_merged(self):
        cat = catalog({"opencode/unknown-free": {"exposure": "trains"}})
        share, _ = modelbandit.merge_free_candidates(dict(SHARE), {}, cat, SUMMARIES)
        self.assertNotIn("opencode/unknown-free", share)


class LocalInheritanceTests(unittest.TestCase):
    def test_listed_local_entry_inherits_family_share(self):
        free_models = catalog({
            "lmstudio/qwen/qwen3-4b": {
                "exposure": "local",
                "summary_ref": "deepseek/deepseek-v4.1-flash",
            },
        })
        listed = ["lmstudio/qwen/qwen3-4b"]
        served = {"lmstudio/qwen/qwen3-4b": {"context_length": 131072}}
        share, _ = modelbandit.merge_local_candidates(
            dict(SHARE), {}, listed, served, free_models, inheritance=1.0)
        self.assertAlmostEqual(share["lmstudio/qwen/qwen3-4b"],
                               0.008 + 0.0172)


class InheritanceDiscountTests(unittest.TestCase):
    """A free serving is a limited-time surrogate: it inherits part of the
    family's standing, not all of it."""

    def test_default_discounts_the_family_share(self):
        cat = catalog({"opencode/deepseek-v4.1-flash-free": {
            "exposure": "no-retention",
            "summary_ref": "deepseek/deepseek-v4.1-flash",
        }})
        share, _ = modelbandit.merge_free_candidates(dict(SHARE), {}, cat, SUMMARIES)
        self.assertAlmostEqual(share["opencode/deepseek-v4.1-flash-free"],
                               (0.008 + 0.0172)
                               * modelbandit.DEFAULT_FREE_SHARE_INHERITANCE)

    def test_lower_inheritance_lowers_standing(self):
        cat = catalog({"opencode/deepseek-v4.1-flash-free": {
            "summary_ref": "deepseek/deepseek-v4.1-flash",
        }})
        half, _ = modelbandit.merge_free_candidates(dict(SHARE), {}, cat, SUMMARIES,
                                             inheritance=0.5)
        tenth, _ = modelbandit.merge_free_candidates(dict(SHARE), {}, cat, SUMMARIES,
                                              inheritance=0.1)
        self.assertLess(tenth["opencode/deepseek-v4.1-flash-free"],
                        half["opencode/deepseek-v4.1-flash-free"])
        self.assertGreater(tenth["opencode/deepseek-v4.1-flash-free"], 0.0)

    def test_out_of_range_inheritance_fails_loudly(self):
        for bad in (0.0, -0.5, 1.5):
            scoring = {"alpha": 0.4, "beta": 1.0,
                       "thresholds": {"top1_min": 0.2, "top1_max": 0.5,
                                      "top2_max": 0.75},
                       "free_share_inheritance": bad}
            policy = {"scoring": scoring,
                      "affinity": {"blend_weight": 0.6, "eligibility_top_k": 5,
                                   "factors": {"favor_validated": 3.0,
                                               "favor_suspected": 2.0,
                                               "avoid_validated": 0.3,
                                               "avoid_suspected": 0.5}}}
            with self.assertRaisesRegex(SystemExit,
                                        "free_share_inheritance"):
                modelbandit.load_policy_config(policy)


if __name__ == "__main__":
    unittest.main()