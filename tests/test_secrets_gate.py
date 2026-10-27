"""Pure fixture tests for the Secrets gate decision."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


class SecretsGateTests(unittest.TestCase):
    def test_content_from_outside_file_trips_by_inclusion(self):
        machine = {"outside_file_contents": ["distinctive private paragraph"]}
        self.assertTrue(modelbandit.secrets_gate(
            "Please summarize: distinctive private paragraph", machine=machine))

    def test_password_token_and_key_material_trip(self):
        for material in ("password=correct-horse", "Bearer eyJhbGciOiJIUzI1NiJ9",
                         "api_key: sk-1234567890abcdef"):
            with self.subTest(material=material):
                self.assertTrue(modelbandit.secrets_gate(material, machine={}))

    def test_machine_identifiers_trip_only_when_included(self):
        machine = {"identifiers": ["machine-user-7f2a"]}
        self.assertTrue(modelbandit.secrets_gate("Account: machine-user-7f2a",
                                          machine=machine))
        self.assertFalse(modelbandit.secrets_gate("Use the account identifier",
                                           machine=machine))

    def test_a_path_mention_alone_does_not_trip(self):
        self.assertFalse(modelbandit.secrets_gate(
            "Read C:/Users/alex/.ssh/id_ed25519 in the example", machine={}))

    def test_project_rules_can_tighten_but_not_disable_defaults(self):
        self.assertTrue(modelbandit.secrets_gate(
            "ordinary fixture phrase", machine={},
            rules={"phrases": ["ordinary fixture phrase"]}))
        self.assertTrue(modelbandit.secrets_gate(
            "password=still-sensitive", machine={},
            rules={"phrases": []}))

    def test_empty_or_unrelated_material_is_safe(self):
        self.assertFalse(modelbandit.secrets_gate("Summarize the public API", machine={}))
        self.assertFalse(modelbandit.secrets_gate("", machine={}))


if __name__ == "__main__":
    unittest.main()
