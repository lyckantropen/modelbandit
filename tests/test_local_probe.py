"""Local LM Studio discovery and candidate merge, using fixtures only."""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402


class LocalProbeTests(unittest.TestCase):
    def test_probe_reads_served_model_ids_and_context_windows(self):
        calls = []
        payload = {"data": [
            {"id": "qwen/qwen3-coder-30b", "context_length": 65_536},
            {"id": "google/gemma-4-31b-it", "context_length": 262_144},
        ]}

        served = bind.probe_local_models(
            lambda url: calls.append(url) or payload)

        self.assertEqual(calls, ["http://127.0.0.1:1234/v1/models"])
        self.assertEqual(served, {
            "qwen/qwen3-coder-30b": {
                "id": "qwen/qwen3-coder-30b", "context_length": 65_536},
            "google/gemma-4-31b-it": {
                "id": "google/gemma-4-31b-it", "context_length": 262_144},
        })

    def test_unreachable_server_is_empty_and_silent(self):
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            served = bind.probe_local_models(
                lambda _url: (_ for _ in ()).throw(OSError("connection refused")))

        self.assertEqual(served, {})
        self.assertEqual(stderr.getvalue(), "")

    def test_invalid_probe_payload_is_empty_and_silent(self):
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            served = bind.probe_local_models(lambda _url: {"unexpected": []})

        self.assertEqual(served, {})
        self.assertEqual(stderr.getvalue(), "")

    def test_only_served_local_catalog_entries_are_merged(self):
        catalog = {
            "qwen/qwen3-coder": {"context_length": 65_536,
                                  "exposure": "local",
                                  "summary_ref": "qwen-coder"},
            "google/gemma-4-31b-it": {"context_length": 262_144,
                                      "exposure": "local",
                                      "summary_ref": "gemma"},
            "mistral/nemo": {"context_length": 131_072,
                             "exposure": "local",
                             "summary_ref": "mistral"},
        }
        served = {
            "qwen/qwen3-coder-30b": {"id": "qwen/qwen3-coder-30b"},
            "google/gemma-4-31b-it": {"id": "google/gemma-4-31b-it"},
            "uncataloged/model": {"id": "uncataloged/model"},
        }
        share, models = bind.merge_local_candidates(
            {"vendor/ranked": 0.5}, {}, served, catalog)

        self.assertEqual(share, {"vendor/ranked": 0.5,
                                 "qwen/qwen3-coder-30b": 0.0,
                                 "google/gemma-4-31b-it": 0.0})
        self.assertEqual(models["qwen/qwen3-coder-30b"]["context_length"], 65_536)
        self.assertEqual(models["google/gemma-4-31b-it"]["context_length"], 262_144)
        self.assertNotIn("mistral/nemo", share)
        self.assertNotIn("uncataloged/model", share)

    def test_served_catalog_entry_needs_summary_for_admission(self):
        policy = {"free_models": {
            "local/qwen": {"context_length": 65_536, "exposure": "local"}},
            "summaries": {}}
        served = {"local/qwen-30b": {"id": "local/qwen-30b"}}
        share, models = bind.merge_local_candidates(
            {}, {}, served, policy["free_models"])
        facts = bind.candidate_for("local/qwen-30b", policy,
                                   local=True, model=models["local/qwen-30b"])

        self.assertIn("local/qwen-30b", share)
        self.assertEqual(facts.exposure, "local")
        self.assertFalse(bind.admit(bind.Shape(), facts).admitted)
        self.assertIn("catalog", bind.admit(bind.Shape(), facts).reason)


if __name__ == "__main__":
    unittest.main()
