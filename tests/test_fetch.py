"""Unit tests for key discovery, cache behaviour, and endpoint fetching."""

import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


class CacheDirMixin(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_cache = modelbandit.CACHE_DIR
        modelbandit.CACHE_DIR = self._tmp.name

    def tearDown(self):
        modelbandit.CACHE_DIR = self._old_cache
        self._tmp.cleanup()


class ApiKeyTests(unittest.TestCase):
    def test_environment_wins(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key",
                                          "HOME": "/nonexistent"}, clear=True):
            self.assertEqual(modelbandit.api_key(), "env-key")

    def _key_from_auth(self, auth_entry):
        home = tempfile.mkdtemp()
        path = os.path.join(home, ".local", "share", "opencode")
        os.makedirs(path)
        with open(os.path.join(path, "auth.json"), "w") as f:
            json.dump(auth_entry, f)
        with mock.patch.dict(os.environ, {"HOME": home}, clear=True):
            return modelbandit.api_key()

    def test_reads_opencode_auth_api_key(self):
        self.assertEqual(
            self._key_from_auth({"openrouter": {"api_key": "k1"}}), "k1")

    def test_reads_access_token_fallback(self):
        self.assertEqual(
            self._key_from_auth({"openrouter": {"access_token": "k2"}}), "k2")

    def test_reads_key_fallback(self):
        self.assertEqual(
            self._key_from_auth({"openrouter": {"key": "k3"}}), "k3")

    def test_other_provider_entries_ignored(self):
        self.assertIsNone(self._key_from_auth({"anthropic": {"api_key": "nope"}}))

    def test_malformed_json_returns_none(self):
        home = tempfile.mkdtemp()
        path = os.path.join(home, ".local", "share", "opencode")
        os.makedirs(path)
        with open(os.path.join(path, "auth.json"), "w") as f:
            f.write("{not json")
        with mock.patch.dict(os.environ, {"HOME": home}, clear=True):
            self.assertIsNone(modelbandit.api_key())

    def test_no_key_anywhere(self):
        with mock.patch.dict(os.environ, {"HOME": "/nonexistent"}, clear=True):
            self.assertIsNone(modelbandit.api_key())


class FetchJsonTests(CacheDirMixin):
    def test_fresh_cache_skips_network(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"cached": True}, f)
        with mock.patch("modelbandit.urllib.request.urlopen") as urlopen:
            self.assertEqual(modelbandit.fetch_json("http://x", "x.json",
                                             auth=False, refresh=False),
                             {"cached": True})
            urlopen.assert_not_called()

    def test_stale_cache_refetches(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"cached": True}, f)
        old = time.time() - modelbandit.CACHE_TTL - 10
        os.utime(path, (old, old))
        with mock.patch("modelbandit.urllib.request.urlopen",
                        return_value=FakeResp({"fresh": True})) as urlopen:
            out = modelbandit.fetch_json("http://x", "x.json", auth=False, refresh=False)
        self.assertEqual(out, {"fresh": True})
        urlopen.assert_called_once()

    def test_refresh_bypasses_fresh_cache(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"cached": True}, f)
        with mock.patch("modelbandit.urllib.request.urlopen",
                        return_value=FakeResp({"fresh": True})):
            out = modelbandit.fetch_json("http://x", "x.json", auth=False, refresh=True)
        self.assertEqual(out, {"fresh": True})

    def test_fetch_writes_cache(self):
        with mock.patch("modelbandit.urllib.request.urlopen",
                        return_value=FakeResp({"fresh": True})):
            modelbandit.fetch_json("http://x", "x.json", auth=False, refresh=True)
        with open(os.path.join(modelbandit.CACHE_DIR, "x.json")) as f:
            self.assertEqual(json.load(f), {"fresh": True})

    def test_failure_falls_back_to_stale_cache(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"stale": True}, f)
        old = time.time() - modelbandit.CACHE_TTL - 10
        os.utime(path, (old, old))
        err = io.StringIO()
        with mock.patch("modelbandit.urllib.request.urlopen",
                        side_effect=OSError("boom")), redirect_stderr(err):
            out = modelbandit.fetch_json("http://x", "x.json", auth=False, refresh=False)
        self.assertEqual(out, {"stale": True})
        self.assertIn("stale cache", err.getvalue())

    def test_failure_without_cache_exits(self):
        with mock.patch("modelbandit.urllib.request.urlopen",
                        side_effect=OSError("boom")):
            with self.assertRaises(SystemExit):
                modelbandit.fetch_json("http://x", "x.json", auth=False, refresh=False)

    def test_auth_without_key_exits(self):
        with mock.patch("modelbandit.api_key", return_value=None):
            with self.assertRaises(SystemExit):
                modelbandit.fetch_json("http://x", "x.json", auth=True, refresh=False)

    def test_a_shorter_ttl_refetches_an_older_cache(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"cached": True}, f)
        old = time.time() - 120
        os.utime(path, (old, old))
        with mock.patch("modelbandit.urllib.request.urlopen",
                        return_value=FakeResp({"fresh": True})) as urlopen:
            out = modelbandit.fetch_json("http://x", "x.json", auth=False,
                                  refresh=False, ttl=60)
        self.assertEqual(out, {"fresh": True})
        urlopen.assert_called_once()

    def test_cache_inside_the_shorter_ttl_skips_network(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"cached": True}, f)
        with mock.patch("modelbandit.urllib.request.urlopen") as urlopen:
            out = modelbandit.fetch_json("http://x", "x.json", auth=False,
                                  refresh=False, ttl=60)
        self.assertEqual(out, {"cached": True})
        urlopen.assert_not_called()

    def test_failure_without_a_stale_fallback_never_serves_stale_cache(self):
        path = os.path.join(modelbandit.CACHE_DIR, "x.json")
        with open(path, "w") as f:
            json.dump({"stale": True}, f)
        old = time.time() - modelbandit.CACHE_TTL - 10
        os.utime(path, (old, old))
        err = io.StringIO()
        with mock.patch("modelbandit.urllib.request.urlopen",
                        side_effect=OSError("boom")), redirect_stderr(err):
            with self.assertRaises(SystemExit):
                modelbandit.fetch_json("http://x", "x.json", auth=False,
                                refresh=False, stale_ok=False)
        self.assertNotIn("stale cache", err.getvalue())

    def test_auth_sends_bearer_header(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["auth"] = req.get_header("Authorization")
            return FakeResp({"ok": True})

        with mock.patch("modelbandit.api_key", return_value="secret"), \
                mock.patch("modelbandit.urllib.request.urlopen", side_effect=fake_urlopen):
            modelbandit.fetch_json("http://x", "x.json", auth=True, refresh=True)
        self.assertEqual(captured["auth"], "Bearer secret")

    def test_no_auth_sends_no_bearer_header(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["auth"] = req.get_header("Authorization")
            return FakeResp({"ok": True})

        with mock.patch("modelbandit.urllib.request.urlopen", side_effect=fake_urlopen):
            modelbandit.fetch_json("http://x", "x.json", auth=False, refresh=True)
        self.assertIsNone(captured["auth"])


class EndpointPricingsTests(CacheDirMixin):
    def test_returns_endpoints(self):
        payload = {"data": {"endpoints": [{"name": "P", "pricing": {}}]}}
        with mock.patch("modelbandit.fetch_json", return_value=payload):
            out = modelbandit.endpoint_pricings("a/b", False)
        self.assertEqual(len(out), 1)

    def test_fetch_failure_returns_empty(self):
        with mock.patch("modelbandit.fetch_json", side_effect=SystemExit("no")):
            self.assertEqual(modelbandit.endpoint_pricings("a/b", False), [])

    def test_missing_endpoints_returns_empty(self):
        with mock.patch("modelbandit.fetch_json", return_value={"data": {}}):
            self.assertEqual(modelbandit.endpoint_pricings("a/b", False), [])

    def test_list_payload_returns_empty(self):
        with mock.patch("modelbandit.fetch_json", return_value=[]):
            self.assertEqual(modelbandit.endpoint_pricings("a/b", False), [])

    def test_cache_name_is_sanitized(self):
        captured = {}

        def fake_fetch(url, cache_name, *, auth, refresh):
            captured["cache_name"] = cache_name
            return {"data": {"endpoints": []}}

        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch):
            modelbandit.endpoint_pricings("a/b~c", False)
        self.assertEqual(captured["cache_name"], "endpoints--a--b--c.json")


if __name__ == "__main__":
    unittest.main()
