"""The harness listing flag, the harness-declared serving endpoint, and the
loopback fact `local` Exposure stands on. Fixtures only — no harness, no
network, no real config read."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


class LocalListingFlagTests(unittest.TestCase):
    """`--local-listing` is passed in by the harness; the namespace filter
    inside is what makes it a local universe, whatever the caller spells."""

    def test_an_unpassed_flag_is_unknown_not_empty(self):
        # Absent means the harness did not speak: the run cannot judge which
        # local models exist, distinct from a listing that says none do.
        self.assertIsNone(modelbandit.parse_local_listing(None))
        self.assertIsNone(modelbandit.parse_local_listing([]))

    def test_ids_are_taken_verbatim_and_comma_chunks_flatten(self):
        self.assertEqual(
            modelbandit.parse_local_listing(
                ["lmstudio/qwen/qwen3.6-35b-a3b, lmstudio/zai-org/glm-4.7-flash"]),
            {"lmstudio/qwen/qwen3.6-35b-a3b", "lmstudio/zai-org/glm-4.7-flash"})
        self.assertEqual(
            modelbandit.parse_local_listing(["lmstudio/a", "lmstudio/b"]),
            {"lmstudio/a", "lmstudio/b"})

    def test_foreign_namespaces_never_seed_a_local_candidate(self):
        # The filter is the invariant: only the harness's local namespace can
        # claim local existence, so another provider's id in the flag is
        # dropped, not adopted.
        self.assertEqual(
            modelbandit.parse_local_listing(
                ["openrouter/qwen/qwen3-4b,opencode/flash,lmstudio/x"]),
            {"lmstudio/x"})

    def test_a_malformed_local_id_is_dropped(self):
        self.assertEqual(
            modelbandit.parse_local_listing(["lmstudio/,lmstudio,//x,lmstudio"]),
            set())

    def test_a_flag_that_states_nothing_is_an_empty_universe(self):
        self.assertEqual(modelbandit.parse_local_listing([""]), set())


class HarnessEndpointTests(unittest.TestCase):
    """The serving endpoint is read from the harness's own config — JSONC
    comments included — and defaults to LM Studio's loopback binding."""

    def write(self, directory, name, text):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_jsonc_comments_are_stripped_but_urls_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "opencode.jsonc", """{
              // a line comment
              "provider": {
                "lmstudio": {
                  /* block comment */
                  "options": {
                    "baseURL": "http://127.0.0.1:1234/v1", // trailing
                    "apiKey": "local-dummy-key" // LM Studio ignores this
                  }
                }
              },
              "references": {"memory": {"path": "https://example.com/x"}}
            }""")
            self.assertEqual(
                modelbandit.read_local_endpoint(path),
                "http://127.0.0.1:1234/v1")

    def test_a_file_without_a_local_provider_says_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "opencode.json", json.dumps(
                {"provider": {"openai": {"options": {"baseURL": "http://x"}}}}))
            self.assertIsNone(modelbandit.read_local_endpoint(path))

    def test_an_unparseable_file_says_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "opencode.jsonc", "{ not json // broken")
            self.assertIsNone(modelbandit.read_local_endpoint(path))

    def test_the_first_declaring_config_wins_and_default_when_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            global_cfg = self.write(tmp, "global.jsonc", json.dumps(
                {"provider": {"lmstudio": {"options": {
                    "baseURL": "http://10.0.0.5:1234/v1"}}}}))
            project_cfg = self.write(tmp, "project.jsonc", json.dumps(
                {"provider": {"lmstudio": {"options": {
                    "baseURL": "http://127.0.0.1:9999/v1"}}}}))
            other = self.write(tmp, "other.json", "{}")
            self.assertEqual(
                modelbandit.harness_serving_endpoint(
                    paths=[other, project_cfg, global_cfg]),
                "http://127.0.0.1:9999/v1")
            self.assertEqual(
                modelbandit.harness_serving_endpoint(paths=[global_cfg]),
                "http://10.0.0.5:1234/v1")
            self.assertEqual(
                modelbandit.harness_serving_endpoint(paths=[]),
                modelbandit.DEFAULT_LOCAL_ENDPOINT)


class LoopbackEndpointTests(unittest.TestCase):
    """`local` Exposure's loopback rule: on this machine, or not at all."""

    def test_the_loopback_rule_accepts_loopback_endpoints(self):
        for url in ("http://127.0.0.1:1234/v1",
                    "http://localhost:1234/v1",
                    "http://LOCALHOST:1234/v1",
                    "http://127.0.1.2:1234/v1",
                    "http://[::1]:1234/v1",
                    modelbandit.DEFAULT_LOCAL_ENDPOINT):
            with self.subTest(url=url):
                self.assertTrue(modelbandit.loopback_endpoint(url))

    def test_the_loopback_rule_rejects_non_loopback_endpoints(self):
        for url in ("http://desktop-rme135a.tail409f29.ts.net:1234/v1",
                    "http://192.168.1.10:1234/v1",
                    "http://10.0.0.5:1234/v1",
                    "https://lmstudio.internal:1234/v1",
                    "http://0.0.0.0:1234/v1",
                    "",
                    "not a url"):
            with self.subTest(url=url):
                self.assertFalse(modelbandit.loopback_endpoint(url))

    def test_the_probe_url_is_the_serving_endpoint_plus_models_path(self):
        self.assertEqual(
            modelbandit.models_url("http://127.0.0.1:1234/v1"),
            "http://127.0.0.1:1234/v1/models")
        self.assertEqual(
            modelbandit.models_url("http://127.0.0.1:1234/v1/"),
            "http://127.0.0.1:1234/v1/models")
        self.assertEqual(modelbandit.models_url(None),
                         modelbandit.LOCAL_MODELS_URL)


if __name__ == "__main__":
    unittest.main()
