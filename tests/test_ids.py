"""Unit tests for identifier normalisation and permaslug resolution."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


class NormIdTests(unittest.TestCase):
    def test_strips_openrouter_prefix(self):
        self.assertEqual(modelbandit.norm_id("openrouter/anthropic/claude-x"),
                         "anthropic/claude-x")

    def test_leaves_plain_ids_untouched(self):
        self.assertEqual(modelbandit.norm_id("anthropic/claude-x"), "anthropic/claude-x")

    def test_strips_exactly_one_prefix(self):
        self.assertEqual(modelbandit.norm_id("openrouter/openrouter/x"), "openrouter/x")

    def test_empty_string(self):
        self.assertEqual(modelbandit.norm_id(""), "")


class ResolveModelTests(unittest.TestCase):
    """The canonical-beats-heuristic order is a named regression: heuristic
    date-stripping priced deepseek-v4-pro-20260813 as its cheaper April
    sibling deepseek-v4-pro ($0.42/M out instead of $1.98)."""

    def setUp(self):
        self.april = {"id": "deepseek/deepseek-v4-pro"}
        self.aug = {"id": "deepseek/deepseek-v4-pro-0813"}
        self.plain = {"id": "x/y"}
        self.models = {m["id"]: m for m in (self.april, self.aug, self.plain)}
        self.by_canon = {
            "deepseek/deepseek-v4-pro-20260423": self.april,
            "deepseek/deepseek-v4-pro-20260813": self.aug,
        }

    def test_exact_slug_hit(self):
        model, how = modelbandit.resolve_model(self.models, self.by_canon,
                                        "deepseek/deepseek-v4-pro-0813")
        self.assertIs(model, self.aug)
        self.assertEqual(how, "exact")

    def test_exact_beats_canonical(self):
        self.by_canon["deepseek/deepseek-v4-pro-0813"] = self.april
        model, how = modelbandit.resolve_model(self.models, self.by_canon,
                                        "deepseek/deepseek-v4-pro-0813")
        self.assertIs(model, self.aug)
        self.assertEqual(how, "exact")

    def test_canonical_hit_for_dated_permaslug(self):
        model, how = modelbandit.resolve_model(self.models, self.by_canon,
                                        "deepseek/deepseek-v4-pro-20260813")
        self.assertIs(model, self.aug)
        self.assertEqual(how, "canonical")

    def test_canonical_beats_heuristic_regression(self):
        # stripping the date would yield "deepseek/deepseek-v4-pro" (April):
        # the wrong, cheaper model. canonical_slug must win.
        model, how = modelbandit.resolve_model(self.models, self.by_canon,
                                        "deepseek/deepseek-v4-pro-20260813")
        self.assertIs(model, self.aug)
        self.assertNotIn("heuristic", how)

    def test_both_releases_resolve_distinctly(self):
        apr, _ = modelbandit.resolve_model(self.models, self.by_canon,
                                    "deepseek/deepseek-v4-pro-20260423")
        aug, _ = modelbandit.resolve_model(self.models, self.by_canon,
                                    "deepseek/deepseek-v4-pro-20260813")
        self.assertIsNot(apr, aug)

    def test_heuristic_strips_date_suffix(self):
        model, how = modelbandit.resolve_model(self.models, self.by_canon, "x/y-20260101")
        self.assertIs(model, self.plain)
        self.assertEqual(how, "heuristic")

    def test_heuristic_keeps_variant_suffix(self):
        models = dict(self.models)
        models["x/y:free"] = {"id": "x/y:free"}
        model, how = modelbandit.resolve_model(models, self.by_canon, "x/y-20260101:free")
        self.assertEqual(model["id"], "x/y:free")
        self.assertEqual(how, "heuristic")

    def test_unresolved_when_nothing_matches(self):
        model, how = modelbandit.resolve_model(self.models, self.by_canon, "ghost/unknown-20260101")
        self.assertIsNone(model)
        self.assertEqual(how, "unresolved")

    def test_mismatched_date_resolves_heuristic_not_canonical(self):
        # "x/y-20260102" strips to "x/y" even though x/y's real release is a
        # different date: the heuristic still resolves it, but must report
        # "heuristic" so the run flags the price as unverified.
        model, how = modelbandit.resolve_model(self.models, self.by_canon, "x/y-20260102")
        self.assertIs(model, self.plain)
        self.assertEqual(how, "heuristic")

    def test_undated_unknown_slug(self):
        model, how = modelbandit.resolve_model(self.models, self.by_canon, "nope/nope")
        self.assertIsNone(model)
        self.assertEqual(how, "unresolved")


if __name__ == "__main__":
    unittest.main()
