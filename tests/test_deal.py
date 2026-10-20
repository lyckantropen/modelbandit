"""Unit tests for the preference-tilted deal: admission, blend math, seeded draw.

plan_deal is the seam: eligibility (popularity floor, affinity admission), the
popularity/preference blend, and the seeded draw all live behind it.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402

POOL = {"a/model-1": 6.0, "b/model-2": 3.0, "c/model-3": 1.0}
MODELS = {mid: {} for mid in POOL}
# Score-scale bases for the fixture pool: task scores live at 1-10, popularity
# shares at 0.0x. The deal must never pass one off as the other.
SCORES = {"a/model-1": 8.0, "b/model-2": 3.5, "c/model-3": 1.2}
FACTORS = {"favor_validated": 3.0, "favor_suspected": 2.0,
           "avoid_validated": 0.3, "avoid_suspected": 0.5}
POLICY_CONFIG = {
    "scoring": {
        "alpha": 0.7,
        "beta": 1.0,
        "thresholds": {"top1_min": 0.2, "top1_max": 0.5, "top2_max": 0.75},
    },
    "affinity": {
        "blend_weight": 0.6,
        "eligibility_top_k": 5,
        "factors": {"favor_validated": 3.0, "favor_suspected": 2.0,
                    "avoid_validated": 0.3, "avoid_suspected": 0.5},
    },
}


def plan(aff=None, **kw):
    params = dict(blend_weight=0.6, top_k=3, seed="s", tickets=100)
    params.update(kw)
    weights = params.pop("weights", SCORES)
    return bind.plan_deal(POOL, MODELS, aff or {},
                          bind.DealParameters(fit_adjusted_task_scores=weights,
                                              **params))


class WeightTests(unittest.TestCase):
    def test_longest_prefix_wins(self):
        table = {"z-ai/glm-5.3": 3.0, "z-ai/glm-5.3-flash": 0.5}
        self.assertEqual(bind.weight_for("z-ai/glm-5.3-flash-2026", table), 0.5)
        self.assertEqual(bind.weight_for("z-ai/glm-5.3-prime", table), 3.0)

    def test_neutral_default(self):
        self.assertEqual(bind.weight_for("openai/gpt-6-luna",
                                         {"z-ai/glm-5.3": 3.0}), 1.0)


class PolicyConfigTests(unittest.TestCase):
    def test_missing_scoring_block_fails_with_key(self):
        policy = dict(POLICY_CONFIG)
        del policy["scoring"]
        with self.assertRaisesRegex(SystemExit, "scoring"):
            bind.load_policy_config(policy)

    def test_missing_factors_map_fails_with_key(self):
        policy = {**POLICY_CONFIG, "affinity": dict(POLICY_CONFIG["affinity"])}
        del policy["affinity"]["factors"]
        with self.assertRaisesRegex(SystemExit, "affinity.factors"):
            bind.load_policy_config(policy)

    def test_missing_blend_weight_fails_with_key(self):
        policy = {**POLICY_CONFIG, "affinity": dict(POLICY_CONFIG["affinity"])}
        del policy["affinity"]["blend_weight"]
        with self.assertRaisesRegex(SystemExit, "affinity.blend_weight"):
            bind.load_policy_config(policy)


class DerivationTests(unittest.TestCase):
    """Affinity is derived from structured hints, never stored as weights."""

    def test_favor_validated_derives_factor(self):
        hints = {"z-ai/glm-5.3": {"note": "n", "fit": {"writing": "favor"},
                                  "evidence": "validated"}}
        self.assertEqual(bind.domain_weights(hints, "writing",
                                             FACTORS),
                         {"z-ai/glm-5.3": 3.0})

    def test_missing_fit_is_neutral(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"}}
        self.assertEqual(bind.domain_weights(hints, "coding",
                                             FACTORS), {})

    def test_suspected_avoid_derives_weaker_avoidance(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "avoid"},
                         "evidence": "suspected"}}
        self.assertEqual(bind.domain_weights(hints, "writing",
                                             FACTORS)["a/m"], 0.5)

    def test_plain_string_hint_is_ignored(self):
        self.assertEqual(bind.domain_weights({"a/m": "just a note"}, "writing",
                                             FACTORS), {})

    def test_explicit_neutral_derives_no_weight(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "neutral"},
                         "evidence": "validated"}}
        self.assertEqual(bind.domain_weights(hints, "writing",
                                             FACTORS), {})

    def test_policy_factors_override(self):
        hints = {"a/m": {"note": "n", "fit": {"writing": "favor"},
                         "evidence": "validated"}}
        w = bind.domain_weights(hints, "writing", {"favor_validated": 9.0})
        self.assertEqual(w["a/m"], 9.0)


class BlendTests(unittest.TestCase):
    def test_zero_blend_is_pure_task_score(self):
        # λ=0 leaves only the task baseline — the fit-adjusted score, which is
        # what popularity becomes once priced at cost, not the raw share.
        rows = plan(blend_weight=0.0)
        got = {r["mid"]: r["draw"] for r in rows}
        total = sum(SCORES.values())
        for mid, score in SCORES.items():
            self.assertAlmostEqual(got[mid], score / total)

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
        rows = plan({"c/model-3": 3.0}, top_k=1)
        self.assertEqual([r["mid"] for r in rows], ["a/model-1", "c/model-3"])

    def test_unfavored_model_below_cut_stays_out(self):
        rows = plan({}, top_k=1)
        self.assertEqual([r["mid"] for r in rows], ["a/model-1"])

    def test_unranked_model_never_plays(self):
        aff = {"ghost/never-classified": 9.0}
        rows = plan(aff, top_k=1)
        self.assertNotIn("ghost/never-classified", [r["mid"] for r in rows])

    def test_unresolved_row_never_plays(self):
        share = dict(POOL, **{"ghost/unresolved": 100.0})
        rows = bind.plan_deal(share, MODELS, {"ghost/unresolved": 9.0},
                              bind.DealParameters(blend_weight=0.6, top_k=2,
                                                  seed="s",
                                                  tickets=10,
                                                  fit_adjusted_task_scores=SCORES))
        self.assertNotIn("ghost/unresolved", [r["mid"] for r in rows])


class EligibilityPoolTests(unittest.TestCase):
    """One pool construction for the candidate table and the deal."""

    def test_top_k_plus_favored_below_cut(self):
        rows = bind.eligibility_pool(POOL, MODELS, {"c/model-3": 3.0}, 2)
        self.assertEqual([mid for mid, _ in rows],
                         ["a/model-1", "b/model-2", "c/model-3"])

    def test_unfavored_below_cut_and_unresolved_stay_out(self):
        share = dict(POOL, **{"ghost/unresolved": 100.0})
        rows = bind.eligibility_pool(share, MODELS,
                                     {"ghost/unresolved": 9.0}, 1)
        self.assertEqual([mid for mid, _ in rows], ["a/model-1"])


class BaseScaleTests(unittest.TestCase):
    """Every pool member blends at its fit-adjusted task score, never share."""

    def test_admitted_below_cut_favorite_blends_at_score_scale(self):
        # top_k=1 leaves only a/model-1 on the cut; c/model-3 is admitted by
        # the user's favor (pref 3.0). Its base is its score (2.0), not its
        # 1.0 share — share scale would let preference carry it almost alone.
        scores = {"a/model-1": 6.0, "c/model-3": 2.0}
        rows = plan({"c/model-3": 3.0}, top_k=1, weights=scores)
        row = next(r for r in rows if r["mid"] == "c/model-3")
        self.assertEqual(row["base"], 2.0)
        # draw = 0.4 * score share + 0.6 * preference share
        self.assertAlmostEqual(row["draw"],
                               0.4 * (2.0 / 8.0) + 0.6 * (3.0 / 4.0))
        self.assertAlmostEqual(sum(r["draw"] for r in rows), 1.0)

    def test_missing_pool_score_is_never_substituted_with_share(self):
        # A caller that scored only the table's top rows must not leave an
        # admitted below-cut favorite blending at raw-share scale.
        with self.assertRaisesRegex(SystemExit, "c/model-3"):
            plan({"c/model-3": 3.0}, top_k=1, weights={"a/model-1": 6.0})


class DrawTests(unittest.TestCase):
    def test_blend_uses_weights_over_share(self):
        share = {"a/1": 9.0, "b/2": 1.0}
        weights = {"a/1": 0.1, "b/2": 10.0}
        rows = bind.plan_deal(share, {m: {} for m in share}, {},
                              bind.DealParameters(blend_weight=0.0, top_k=2,
                                                  seed="s",
                                                  tickets=100,
                                                  fit_adjusted_task_scores=weights))
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
        self.assertEqual(bind.plan_deal(
            {}, {}, {}, bind.DealParameters(blend_weight=0.6, top_k=5,
                                            seed="s",
                                            tickets=12)), [])


if __name__ == "__main__":
    unittest.main()
