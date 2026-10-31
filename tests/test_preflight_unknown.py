"""The pre-flight's default-deny: an id outside every Route kind is blocked.

Route kind is the serving fact every gate derives a verdict from, and a
namespace the classifier does not recognize has no kind — so no zone regime,
Exposure fact or policy label can speak for it. The pre-flight is the one
surface that owes a launch verdict, so it answers the block itself:
`blocked: unknown serving namespace` with the model named, a verdict rather
than a failure (exit contract v2, ADR-0004: exit 0, the status says the tool
ran, the line says what's true), and the same block in the `--json` object's
reason.

The verdict is decided from the id alone, before the zone regime: an
unclassifiable id is refused in an open zone exactly as in a closed one. The
policy's prefix maps stay annotation-only — an `exposure` override may name a
namespace without granting it a kind, so it never turns the block into an
allow.

Known kinds keep today's verdicts byte for byte; the pre-flight-contract and
exit-contract suites pin that, untouched.
"""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

UNKNOWN = "blocked: unknown serving namespace"

# Ids the classifier answers None for: outside every kind.
UNCLASSIFIABLE = ("anthropic", "anthropic//claude", "opencode-go/", "/model")


def preflight(mid, zone, policy=None, *, plain=False, as_json=False):
    """The pre-flight's answer for one id, read at its egress.

    The zone and the policy facts are injected the way a caller supplies
    them; nothing is fetched. Returns the exit status, the printed lines and
    the reason the block carried, if the block is the one under test.
    """
    printed = io.StringIO()
    with mock.patch.object(modelbandit, "effective_zone", return_value=zone), \
            mock.patch.object(modelbandit, "policy_facts",
                              return_value=policy or {}), \
            redirect_stdout(printed):
        code = modelbandit.run_assert_allowed(model=mid, plain=plain,
                                              as_json=as_json)
    return code, printed.getvalue()


class UnknownNamespaceIsBlockedTests(unittest.TestCase):
    def test_an_unclassifiable_id_is_blocked_and_the_lines_say_why(self):
        zone = modelbandit.Zone(path="z", regime="open")
        for mid in UNCLASSIFIABLE:
            with self.subTest(mid=mid):
                code, out = preflight(mid, zone)
                lines = out.splitlines()
                self.assertEqual(code, 0, out)
                self.assertIn(UNKNOWN, lines, out)
                self.assertIn(f"model: {mid}", lines, out)
                self.assertFalse([ln for ln in lines
                                  if ln.startswith("allowed: ")], out)

    def test_the_block_holds_whatever_the_regime(self):
        # Classification is decided before the zone regime: an unclassifiable
        # id is refused in an open zone exactly as in a closed one, and the
        # verdict is the unknown namespace — never the zone's own reason.
        for regime in ("open", "sensitive", "closed"):
            zone = modelbandit.Zone(path="z", regime=regime)
            for plain in (False, True):
                with self.subTest(regime=regime, plain=plain):
                    code, out = preflight("anthropic", zone, plain=plain)
                    self.assertEqual(code, 0, out)
                    self.assertIn(UNKNOWN, out.splitlines(), out)
                    self.assertNotIn("blocked by the free-use zone", out)

    def test_the_json_answer_carries_the_same_block(self):
        zone = modelbandit.Zone(path="z", regime="open")
        code, out = preflight("opencode-go/", zone, as_json=True)
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertEqual(payload["mode"], "assert-allowed")
        self.assertIs(payload["ok"], True)
        self.assertIs(payload["allowed"], False)
        self.assertEqual(payload["model"], "opencode-go/")
        self.assertIn("unknown serving namespace", payload["reason"])
        self.assertEqual(payload["zone"]["regime"], "open")


class PolicyPrefixesCannotGrantAKindTests(unittest.TestCase):
    def test_an_exposure_override_on_the_namespace_leaves_it_blocked(self):
        # The override annotates a route; it never classifies one.
        policy = {"exposure": {"anthropic/": "no-retention"}}
        for regime in ("open", "closed"):
            with self.subTest(regime=regime):
                code, out = preflight(
                    "anthropic//claude",
                    modelbandit.Zone(path="z", regime=regime), policy)
                self.assertEqual(code, 0, out)
                self.assertIn(UNKNOWN, out.splitlines(), out)
                self.assertNotIn("allowed:", out)

    def test_a_catalog_entry_on_the_namespace_leaves_it_blocked(self):
        # A curated entry is a claim about a route's facts, not a kind either.
        policy = {"free_models": {"anthropic/": {"context_length": 4096,
                                                 "summary_ref": "s",
                                                 "exposure": "local"}},
                  "summaries": {"s": "fixture summary"}}
        code, out = preflight(
            "anthropic//claude", modelbandit.Zone(path="z", regime="open"),
            policy, as_json=True)
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertIs(payload["allowed"], False)
        self.assertIn("unknown serving namespace", payload["reason"])


if __name__ == "__main__":
    unittest.main()
