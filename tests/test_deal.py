"""Unit tests for the preference-tilted deal: admission, blend math, seeded draw.

plan_deal is the seam: eligibility (popularity floor, affinity admission), the
popularity/preference blend, and the seeded draw all live behind it.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bind  # noqa: E402

POOL = {"a/model-1": 6.0, "b/model-2": 3.0, "c/model-3": 1.0}
MODELS = {mid: {} for mid in POOL}


def plan(aff=None, **kw):
    params = dict(blend_weight=0.6, top_k=3, admit=False, seed="s", tickets=100)
    params.update(kw)
    return bind.plan_deal(POOL, MODELS, aff or {}, **params)


class WeightTests(unittest.TestCase):
    def test_longest_prefix_wins(self):
        table = {"z-ai/glm-5.3": 3.0, "z-ai/glm-5.3-flash": 0.5}
        self.assertEqual(bind.weight_for("z-ai/glm-5.3-flash-2026", table), 0.5)
        self.assertEqual(bind.weight_for("z-ai/glm-5.3-prime", table), 3.0)

    def test_neutral_default(self):
        self.assertEqual(bind.weight_for("openai/gpt-6-luna",
                                         {"z-ai/glm-5.3": 3.0}), 1.0)


class DerivationTests(unittest.TestCase):
    """Affinity is derived from structured hints, never stored as weights."""

    def test_favor_validated_derives_factor(self):
        hints = {"z-ai/glm-5.3": {"note": "n", "fit": {"writing": "favor"},
                                  "evidence": "validated"}}
        self.assertEqual(bind.domain_weights(hints, "writing",
                                             bind.DEFAULT_FACTORS),
                         {"z-ai/glm-5.3": 3.0})

    def test_missing_fit_is_neutral(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"}}
        self.assertEqual(bind.domain_weights(hints, "coding",
                                             bind.DEFAULT_FACTORS), {})

    def test_suspected_avoid_derives_weaker_avoidance(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "avoid"},
                         "evidence": "suspected"}}
        self.assertEqual(bind.domain_weights(hints, "writing",
                                             bind.DEFAULT_FACTORS)["a/m"], 0.5)

    def test_plain_string_hint_is_ignored(self):
        self.assertEqual(bind.domain_weights({"a/m": "just a note"}, "writing",
                                             bind.DEFAULT_FACTORS), {})

    def test_explicit_neutral_derives_no_weight(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "neutral"},
                         "evidence": "validated"}}
        self.assertEqual(bind.domain_weights(hints, "writing",
                                             bind.DEFAULT_FACTORS), {})

    def test_policy_factors_override(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"}}
        w = bind.domain_weights(hints, "writing", {"favor_validated": 9.0})
        self.assertEqual(w["a/m"], 9.0)


class BlendTests(unittest.TestCase):
    def test_zero_blend_is_pure_popularity(self):
        rows = plan(blend_weight=0.0)
        got = {r["mid"]: r["draw"] for r in rows}
        self.assertAlmostEqual(got["a/model-1"], 0.6)
        self.assertAlmostEqual(got["b/model-2"], 0.3)
        self.assertAlmostEqual(got["c/model-3"], 0.1)

    def test_full_blend_is_pure_preference(self):
        rows = plan({"a/model-1": 1.0, "b/model-2": 2.0, "c/model-3": 7.0},
                    blend_weight=1.0)
        got = {r["mid"]: r["draw"] for r in rows}
        self.assertAlmostEqual(got["c/model-3"], 0.7)
        self.assertAlmostEqual(got["b/model-2"], 0.2)

    def test_preference_upweights_favored_model(self):
        plain = {r["mid"]: r["draw"] for r in plan(blend_weight=0.6)}
        tilted = {r["mid"]: r["draw"] for r in
                  plan({"c/model-3": 5.0}, blend_weight=0.6)}
        self.assertGreater(tilted["c/model-3"], plain["c/model-3"])
        self.assertLess(tilted["a/model-1"], plain["a/model-1"])

    def test_draws_sum_to_one(self):
        rows = plan({"b/model-2": 2.5})
        self.assertAlmostEqual(sum(r["draw"] for r in rows), 1.0)


class AdmissionTests(unittest.TestCase):
    def test_favored_model_below_cut_is_admitted(self):
        rows = plan({"c/model-3": 3.0}, top_k=1, admit=True)
        self.assertEqual([r["mid"] for r in rows], ["a/model-1", "c/model-3"])

    def test_unfavored_model_below_cut_stays_out(self):
        rows = plan({}, top_k=1, admit=True)
        self.assertEqual([r["mid"] for r in rows], ["a/model-1"])

    def test_unranked_model_never_plays(self):
        aff = {"ghost/never-classified": 9.0}
        rows = plan(aff, top_k=1, admit=True)
        self.assertNotIn("ghost/never-classified", [r["mid"] for r in rows])

    def test_unresolved_row_never_plays(self):
        share = dict(POOL, **{"ghost/unresolved": 100.0})
        rows = bind.plan_deal(share, MODELS, {"ghost/unresolved": 9.0},
                              blend_weight=0.6, top_k=2, admit=True,
                              seed="s", tickets=10)
        self.assertNotIn("ghost/unresolved", [r["mid"] for r in rows])


class DrawTests(unittest.TestCase):
    def test_blend_uses_weights_over_share(self):
        share = {"a/1": 9.0, "b/2": 1.0}
        weights = {"a/1": 0.1, "b/2": 10.0}
        rows = bind.plan_deal(share, {m: {} for m in share}, {},
                              blend_weight=0.0, top_k=2, admit=False,
                              seed="s", tickets=100, weights=weights)
        draws = {r["mid"]: r["draw"] for r in rows}
        self.assertLess(draws["a/1"], draws["b/2"])  # weight, not share

    def test_deal_deterministic_per_seed(self):
        a = plan({"a/model-1": 2.0}, seed="proj", tickets=12)
        b = plan({"a/model-1": 2.0}, seed="proj", tickets=12)
        self.assertEqual(a, b)

    def test_deal_allocates_all_tickets(self):
        for seed in ("proj", "x", "y", "z"):
            rows = plan({"b/model-2": 3.0}, seed=seed, tickets=12)
            self.assertEqual(sum(r["tickets"] for r in rows), 12)

    def test_empty_pool(self):
        self.assertEqual(bind.plan_deal({}, {}, {}, blend_weight=0.6,
                                        top_k=5, admit=True, seed="s",
                                        tickets=12), [])


if __name__ == "__main__":
    unittest.main()
