"""Unit tests for effort-ladder construction and rung resolution."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bind  # noqa: E402

FULL = ["none", "low", "medium", "high", "xhigh", "max"]
BINARY = ["none", "thinking"]


class EffortLadderTests(unittest.TestCase):
    def test_reasoning_effort_gives_full_house(self):
        model = {"supported_parameters": ["tools", "reasoning_effort", "reasoning"]}
        self.assertEqual(bind.effort_ladder(model), FULL)

    def test_reasoning_only_gives_binary(self):
        model = {"supported_parameters": ["reasoning", "tools"]}
        self.assertEqual(bind.effort_ladder(model), BINARY)

    def test_no_reasoning_gives_single_rung(self):
        model = {"supported_parameters": ["tools", "response_format"]}
        self.assertEqual(bind.effort_ladder(model), ["default"])

    def test_missing_supported_parameters(self):
        self.assertEqual(bind.effort_ladder({}), ["default"])

    def test_empty_supported_parameters(self):
        self.assertEqual(bind.effort_ladder({"supported_parameters": []}), ["default"])


class ResolveRungTests(unittest.TestCase):
    def test_single_rung_always_resolves(self):
        for intent in bind.INTENTS:
            self.assertEqual(bind.resolve_rung(["default"], intent), "default")

    def test_full_ladder_binds_by_position(self):
        self.assertEqual(bind.resolve_rung(FULL, "glance"), "none")
        self.assertEqual(bind.resolve_rung(FULL, "measured"), "medium")
        self.assertEqual(bind.resolve_rung(FULL, "thorough"), "high")
        self.assertEqual(bind.resolve_rung(FULL, "exhaustive"), "max")

    def test_binary_ladder_collapses_to_nearest(self):
        self.assertEqual(bind.resolve_rung(BINARY, "glance"), "none")
        self.assertEqual(bind.resolve_rung(BINARY, "measured"), "thinking")
        self.assertEqual(bind.resolve_rung(BINARY, "thorough"), "thinking")
        self.assertEqual(bind.resolve_rung(BINARY, "exhaustive"), "thinking")

    def test_medium_named_wins_over_position(self):
        ladder = ["minimal", "low", "medium", "high", "xhigh"]
        self.assertEqual(bind.resolve_rung(ladder, "measured"), "medium")
        self.assertEqual(bind.resolve_rung(ladder, "thorough"), "high")
        self.assertEqual(bind.resolve_rung(ladder, "glance"), "minimal")
        self.assertEqual(bind.resolve_rung(ladder, "exhaustive"), "xhigh")

    def test_middle_rung_rounds_up_without_medium(self):
        ladder = ["low", "high", "max"]
        self.assertEqual(bind.resolve_rung(ladder, "glance"), "low")
        self.assertEqual(bind.resolve_rung(ladder, "measured"), "high")
        self.assertEqual(bind.resolve_rung(ladder, "thorough"), "max")
        self.assertEqual(bind.resolve_rung(ladder, "exhaustive"), "max")

    def test_unknown_intent_raises(self):
        with self.assertRaises(KeyError):
            bind.resolve_rung(FULL, "ultra")


if __name__ == "__main__":
    unittest.main()
