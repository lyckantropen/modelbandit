"""Exit contract v2, verdict matrix (issue #41): status says whether the
tool ran; output says what's true.

Every answer across every mode exits **0**: verdict lines, including ranking
stops, use stdout; operational failures retain their stderr payload. The
retired codes (1 sensitive, 3 not certified, 5 zone block, over-budget's
borrowed 2) are never assigned.
Usage stays 2 (argparse's own channel), rules/config stays 4, and a network
failure keeps its message payload — nonzero in a shell — pinned here as
*not* an answer.

`LineOutputParityTests` pins unchanged default (no `--json`) line output
byte-identical to the v1 egresses. The ranking stop lines intentionally use
the spec's unified printer instead of the old v1 stderr sentences; both their
stdout and JSON forms are pinned here. JSON mode is otherwise pinned in
`JsonModeTests`.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelbandit  # noqa: E402
from test_cli import POLICY, build_world  # noqa: E402


def policy_with(**overrides):
    """The fixture policy with whole keys replaced."""
    policy = json.loads(json.dumps(POLICY))
    policy.update(overrides)
    return policy


class ModelbanditCli(unittest.TestCase):
    """In-process CLI harness: fixture machine, temp XDG, no network."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.policy_path = os.path.join(self.root, "policy.json")
        self.write_policy(POLICY)

    def tearDown(self):
        self._tmp.cleanup()

    def write_policy(self, policy):
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(policy, f)
        return self.policy_path

    def place(self, folder=None):
        """The judged place as the header spells it — the folder, links
        resolved — for an undeclared open zone."""
        return modelbandit.display_path(folder or self.root)

    def run_cli(self, *argv, stdin="", world=None, zones=(), policy_path=None,
                fetch_error=False):
        world = build_world() if world is None else world
        config_home = os.path.join(self.root, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"zones": list(zones)}, f)

        def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
            if fetch_error:
                raise SystemExit(f"cannot reach {url}")
            if cache_name == "key.json":
                raise SystemExit("cannot reach https://openrouter.ai/api/v1/key")
            if cache_name == "models.json":
                return {"data": world["models"]}
            if cache_name == "classifications.json":
                return {"data": world["classifications"]}
            if cache_name == "rankings.json":
                return world["rankings"]
            if url.endswith("/endpoints"):
                slug = url[len(modelbandit.MODELS_URL) + 1:-len("/endpoints")]
                return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
            raise AssertionError(f"unexpected fetch: {url}")

        out, err = io.StringIO(), io.StringIO()
        code = None
        full_argv = ["modelbandit", "--policy",
                     policy_path or self.policy_path, *argv]
        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch), \
                mock.patch("modelbandit.probe_local_models", return_value={}), \
                mock.patch.object(modelbandit, "CACHE_DIR",
                                  os.path.join(self.root, "cache")), \
                mock.patch("modelbandit.machine_facts",
                           return_value={"identifiers": []}), \
                mock.patch("modelbandit.git_origin", return_value=None), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                mock.patch.object(sys, "argv", full_argv), \
                mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code


class VerdictMatrixTests(ModelbanditCli):
    """AC1: every answer in every mode exits 0 — red-first against the
    retired 1/3/5/over-budget-2 codes."""

    # --- --check-secrets: four verdicts, one status ----------------------

    def test_safe_is_a_completed_run_not_a_status(self):
        out, err, code = self.run_cli("--check-secrets", "--working-dir",
                                      self.root,
                                      stdin="Summarize the public API")
        self.assertEqual(code, 0)
        self.assertIn("secrets gate: safe", out)
        self.assertEqual(err, "")

    def test_sensitive_is_a_completed_run_not_a_status(self):
        out, err, code = self.run_cli("--check-secrets", "--working-dir",
                                      self.root,
                                      stdin="api_key: sk-1234567890abcdef")
        self.assertEqual(code, 0)
        self.assertIn("secrets gate: sensitive", out)
        self.assertIn("rule: password, token or key assignment", out)
        self.assertEqual(err, "")

    def test_not_certified_is_a_completed_run_not_a_status(self):
        for stdin in ("", "   \n\n"):
            with self.subTest(stdin=stdin):
                out, _, code = self.run_cli("--check-secrets",
                                            "--working-dir", self.root,
                                            stdin=stdin)
                self.assertEqual(code, 0)
                self.assertIn("secrets gate: not certified (no material given)",
                              out)
                self.assertNotIn("secrets gate: safe", out)

    def test_the_model_flag_is_a_usage_error_not_a_zone_verdict(self):
        # The mode split (spec #75): the check answers material questions
        # only, so `--model` is not read here at all — no zone verdict, a
        # usage error, exactly the refusal a silently ignored flag earns.
        out, err, code = self.run_cli("--check-secrets", "--working-dir",
                                      self.root, "--model", "vendor/model:free",
                                      stdin="Summarize the public API")
        self.assertEqual(code, 2)
        self.assertIn("--model", err)
        self.assertNotIn("secrets gate:", out)

    def test_provenance_block_is_a_completed_run_not_a_status(self):
        # The vault is declared closed; the outside file comes from it, so
        # provenance blocks before the content verdict — still a verdict:
        # exit 0.
        vault = os.path.join(self.root, "vault")
        os.makedirs(vault)
        path = os.path.join(vault, "notes.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("ORDINARY_PRIVATE_LINE_7f2a\n")

        out, _, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root, "--outside-file", path,
                                    zones=[vault],
                                    stdin="Summarize it.")

        self.assertEqual(code, 0)
        self.assertIn("blocked: free-use zone", out)
        # The zone line names the declared closed place, never the content.
        self.assertIn(f"zone: {self.place(vault)} (closed)", out)
        self.assertIn("reason: material provenance from this zone", out)

    # --- --assert-allowed: two verdicts, one status ----------------------

    def test_allowed_is_a_completed_run_not_a_status(self):
        # ADR 0008 moved the default: the assumed-Sensitive shape now blocks
        # every non-local route, so the allowed verdict comes from the
        # stated-plain shape — either way the answer is a completed run.
        out, err, code = self.run_cli("--assert-allowed", "--model",
                                      "deepseek/deepseek-v4-pro", "--plain",
                                      "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertIn("allowed: deepseek/deepseek-v4-pro", out)
        self.assertEqual(err, "")

        blocked, err, code = self.run_cli("--assert-allowed", "--model",
                                          "deepseek/deepseek-v4-pro",
                                          "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertIn("blocked: free-use zone", blocked)
        self.assertIn(
            "reason: only Exposure local may serve a Sensitive shape "
            "(no-retention)", blocked)
        self.assertEqual(err, "")

    def test_blocked_is_a_completed_run_not_a_status(self):
        out, _, code = self.run_cli("--assert-allowed", "--model",
                                    "vendor/model:free",
                                    "--working-dir", self.root,
                                    zones=[self.root])
        self.assertEqual(code, 0)
        self.assertIn("blocked: free-use zone", out)
        self.assertIn("model: vendor/model:free", out)

    # --- --status: already 0, pinned here for the matrix -----------------

    def test_status_is_a_completed_run(self):
        out, err, code = self.run_cli("--status", "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertIn(f"zone: {self.place()} (open)", out)
        self.assertEqual(err, "")

    # --- the ranking run's own verdicts ----------------------------------

    def test_over_budget_is_a_completed_run_not_a_status(self):
        out, _, code = self.run_cli("--domain", "writing", "--deal",
                                    "--budget", "0")
        self.assertEqual(code, 0)
        self.assertIn("budget: $0.00 -> OVER", out)

    def test_under_budget_completes_with_the_under_verdict(self):
        # Normal completion: no SystemExit in-process, exit 0 in a shell.
        out, _, code = self.run_cli("--domain", "writing", "--budget", "1000")
        self.assertIn(code, (None, 0))
        self.assertIn("budget: $1000.00 -> under", out)

    def test_a_sensitive_stop_reports_blocked_on_stdout_with_zero(self):
        # ADR 0008: a Sensitive shape with no eligible local candidate stops
        # with the blocked report on stdout — the report is the human
        # escalation, never a re-gate — and exits 0 like every verdict.
        self.write_policy(policy_with(exposure={"deepseek/": "trains"}))

        out, err, code = self.run_cli("--domain", "writing", "--sensitive")

        self.assertEqual(code, 0)
        self.assertIn("blocked: no eligible local candidate", out)
        self.assertNotIn("no candidate admitted", err)
        self.assertNotIn("no candidate admitted", out)

    def test_no_ranked_candidates_uses_the_blocked_printer_with_zero(self):
        # The domain's tag is known but ranks no model: an empty pool is a
        # completed run's answer, not a failure.
        self.write_policy(policy_with(domains={"writing": ["content_writing"]},
                                      hints={}, summaries={}))
        world = build_world()
        world["classifications"]["classifications"][0]["models"] = []

        out, err, code = self.run_cli("--domain", "writing", world=world)

        self.assertEqual(code, 0)
        self.assertNotIn("no ranked candidates", err)
        self.assertTrue(out.endswith("blocked: no ranked candidates\n"), out)

    def test_no_admitted_candidates_uses_the_blocked_printer_and_json_reason(self):
        # The Context gate excludes the only ranked Free route when its window
        # is unknown; the stop goes through the same printer and JSON contract.
        mid = "vendor/unknown:free"
        world = build_world()
        world["models"].append({
            "id": mid, "supported_parameters": [],
            "pricing": {"prompt": "0", "completion": "0",
                        "input_cache_read": "0"}})
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 1.0,
            "models": [{"id": mid, "tag_usage_share": 1.0}],
        }]

        out, err, code = self.run_cli("--domain", "writing", world=world)
        self.assertEqual(code, 0)
        self.assertNotIn("no candidate admitted", err)
        self.assertTrue(out.endswith("blocked: no candidate admitted\n"), out)
        self.assertIn("unknown context window", out)

        out, err, code = self.run_cli("--domain", "writing", "--budget",
                                      "1000", "--json", world=world)
        self.assertEqual(code, 0)
        self.assertNotIn("no candidate admitted", err)
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "blocked")
        self.assertEqual(payload["reason"], "no candidate admitted")

    # --- AC2: a failure is never an answer -------------------------------

    def test_a_network_failure_is_not_an_answer(self):
        # Operational failure: the message payload keeps its stderr line and
        # CPython's nonzero generic exit — never one of our codes, never an
        # answer.
        _, _, code = self.run_cli("--domain", "writing", fetch_error=True)
        self.assertIsInstance(code, str)
        self.assertIn("cannot reach", code)
        self.assertNotEqual(code, 0)


class LineOutputParityTests(ModelbanditCli):
    """AC4 parity, the line half: without --json the output for the same run
    is byte-identical to the v1 egresses (goldens captured from the
    pre-v2 script). The ranking table's bytes are pinned by test_cli's
    golden; --status's four lines are pinned there too."""

    def test_check_secrets_safe_lines_are_byte_identical(self):
        out, _, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root,
                                    stdin="Summarize the public API")
        self.assertEqual(code, 0)
        self.assertEqual(out, f"zone: {self.place()} (open)\n"
                              "secrets gate: safe\n")

    def test_the_sensitive_lines_are_byte_identical(self):
        out, _, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root,
                                    stdin="api_key: sk-1234567890abcdef")
        self.assertEqual(code, 0)
        self.assertEqual(out, f"zone: {self.place()} (open)\n"
                              "secrets gate: sensitive\n"
                              "rule: password, token or key assignment\n")

    def test_the_not_certified_lines_are_byte_identical(self):
        out, _, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root, stdin="")
        self.assertEqual(code, 0)
        self.assertEqual(out, f"zone: {self.place()} (open)\n"
                              "secrets gate: not certified (no material "
                              "given)\n")

    def test_the_provenance_block_lines_are_byte_identical(self):
        # An outside file from a declared closed place blocks on provenance —
        # the check's only zone answer (spec #75's mode split): the zone is
        # named, the material never is.
        vault = os.path.join(self.root, "vault")
        os.makedirs(vault)
        path = os.path.join(vault, "notes.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("ORDINARY_PRIVATE_LINE_7f2a\n")
        out, _, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root, "--outside-file", path,
                                    zones=[vault],
                                    stdin="Summarize the public API")
        self.assertEqual(code, 0)
        self.assertEqual(
            out, f"zone: {self.place()} (open)\n"
                 "blocked: free-use zone\n"
                 f"zone: {self.place(vault)} (closed)\n"
                 "reason: material provenance from this zone\n")

    def test_assert_allowed_allowed_lines_are_byte_identical(self):
        # ADR 0008 moved the default: the assumed-Sensitive shape blocks
        # every non-local route (the block's lines are byte-pinned too), and
        # the allowed verdict is the stated-plain shape's.
        out, _, code = self.run_cli("--assert-allowed", "--model",
                                    "deepseek/deepseek-v4-pro", "--plain",
                                    "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(out, f"zone: {self.place()} (open)\n"
                              "shape: plain (via --plain)\n"
                              "allowed: deepseek/deepseek-v4-pro\n")

        blocked, _, code = self.run_cli("--assert-allowed", "--model",
                                        "deepseek/deepseek-v4-pro",
                                        "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(blocked,
                         f"zone: {self.place()} (open)\n"
                         "shape: sensitive (assumed)\n"
                         "blocked: free-use zone\n"
                         "model: deepseek/deepseek-v4-pro\n"
                         "reason: only Exposure local may serve a Sensitive "
                         "shape (no-retention)\n")

    def test_assert_allowed_blocked_lines_are_byte_identical(self):
        out, _, code = self.run_cli("--assert-allowed", "--model",
                                    "vendor/model:free",
                                    "--working-dir", self.root,
                                    zones=[self.root])
        self.assertEqual(code, 0)
        self.assertEqual(
            out, f"zone: {self.place()} (closed)\n"
                 "shape: sensitive (assumed)\n"
                 "blocked: free-use zone\n"
                 "model: vendor/model:free\n"
                 "reason: remote free route is prohibited by the closed "
                 "zone\n")

    def test_the_budget_verdict_line_is_byte_identical(self):
        out, _, code = self.run_cli("--domain", "writing", "--tickets", "2",
                                    "--budget", "0.1")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-1], "budget: $0.10 -> OVER")


    def test_the_budgeted_run_is_byte_identical_to_the_verdict_line(self):
        # End-to-end byte parity (AC2): a budgeted run differs from the same
        # run without --budget in exactly one appended line - the v1-captured
        # verdict line - and in nothing else. (v1 printed this line to stdout
        # too; only its exit code changed, 2 -> 0.)
        base, _, base_code = self.run_cli("--domain", "writing",
                                          "--tickets", "2")
        self.assertIn(base_code, (None, 0))
        out, _, code = self.run_cli("--domain", "writing", "--tickets", "2",
                                    "--budget", "0.1")
        self.assertEqual(code, 0)
        self.assertEqual(out, base + "budget: $0.10 -> OVER\n")


class JsonModeTests(ModelbanditCli):
    """AC4, the JSON half: `--json` emits ONE object on stdout with the
    required keys per answer mode — `mode`, `ok` (always true — it ran),
    the `outcome` string (safe/sensitive/not certified/blocked) with
    its polarity `verdict`, or `allowed` (bool), `zone`, `reason`, `rule`,
    and for the budget verdict `over_budget` + the projection figures. The
    ranking table is never JSON-ized; anywhere the flag does not serve, it
    is the usage error it is."""

    def one_object(self, out):
        """stdout is exactly one JSON object — nothing else."""
        self.assertEqual(out.count("\n"), 1,
                         f"one line, one object expected:\n{out}")
        payload = json.loads(out)
        self.assertIsInstance(payload, dict)
        for key in ("mode", "ok"):
            self.assertIn(key, payload)
        self.assertIs(payload["ok"], True)
        return payload

    def zone_of(self, payload):
        self.assertEqual(set(payload["zone"]),
                         {"path", "posture", "declared", "resolved"})
        self.assertIn(payload["zone"]["posture"], ("open", "closed"))
        self.assertNotIn("regime", payload["zone"])
        return payload["zone"]

    def last_json_line_is_the_only_json_line(self, out):
        """stdout carries lines (the table) plus exactly one JSON object,
        on the last line."""
        parsed = []
        for line in out.splitlines():
            try:
                parsed.append(json.loads(line))
            except ValueError:
                pass
        self.assertEqual(len(parsed), 1,
                         f"exactly one JSON object among the lines:\n{out}")
        payload = parsed[0]
        self.assertEqual(json.loads(out.splitlines()[-1]), payload,
                         "the object is the last line")
        self.assertIsInstance(payload, dict)
        self.assertIn("mode", payload)
        self.assertIs(payload["ok"], True)
        return payload

    # --- --check-secrets --------------------------------------------------

    def test_check_secrets_safe_is_one_object(self):
        out, err, code = self.run_cli("--check-secrets", "--json",
                                      "--working-dir", self.root,
                                      stdin="Summarize the public API")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        payload = self.one_object(out)
        self.assertEqual(payload["mode"], "check-secrets")
        self.assertIs(payload["verdict"], True)   # the proceed polarity
        self.assertEqual(payload["outcome"], "safe")
        self.assertEqual(self.zone_of(payload),
                         {"path": self.place(), "posture": "open",
                          "declared": None, "resolved": None})
        self.assertIsNone(payload["reason"])
        self.assertIsNone(payload["rule"])

    def test_sensitive_json_carries_the_rule(self):
        out, _, code = self.run_cli("--check-secrets", "--json",
                                    "--working-dir", self.root,
                                    stdin="api_key: sk-1234567890abcdef")
        self.assertEqual(code, 0)
        payload = self.one_object(out)
        self.assertIs(payload["verdict"], False)
        self.assertEqual(payload["outcome"], "sensitive")
        self.assertEqual(payload["rule"],
                         "password, token or key assignment")
        self.assertIsNone(payload["reason"])

    def test_not_certified_is_one_object(self):
        out, _, code = self.run_cli("--check-secrets", "--json",
                                    "--working-dir", self.root, stdin="")
        self.assertEqual(code, 0)
        payload = self.one_object(out)
        self.assertIs(payload["verdict"], False)
        self.assertEqual(payload["outcome"], "not certified")
        self.assertEqual(payload["reason"], "no material given")
        self.assertIsNone(payload["rule"])

    def test_the_provenance_block_carries_the_reason_and_zone(self):
        # The outcome word is the stdout verdict word (`blocked`); the zone
        # is named, the material never is.
        vault = os.path.join(self.root, "vault")
        os.makedirs(vault)
        path = os.path.join(vault, "notes.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("ORDINARY_PRIVATE_LINE_7f2a\n")
        out, _, code = self.run_cli("--check-secrets", "--json",
                                    "--working-dir", self.root,
                                    "--outside-file", path,
                                    zones=[vault],
                                    stdin="Summarize the public API")
        self.assertEqual(code, 0)
        payload = self.one_object(out)
        self.assertIs(payload["verdict"], False)
        self.assertEqual(payload["outcome"], "blocked")
        self.assertEqual(self.zone_of(payload)["posture"], "closed")
        self.assertEqual(payload["reason"],
                         "material provenance from this zone")
        self.assertIsNone(payload["rule"])

    # --- --assert-allowed -------------------------------------------------

    def test_a_stopped_budgeted_run_still_answers_with_one_object(self):
        # Build 2 (review concession): one object per invocation - the
        # ranking's own stop included. The table stays lines; the object is
        # the last and only JSON line; stderr stays empty (json replaces the
        # stop message). Under ADR 0008 the Sensitive stop is the blocked
        # report, carried in the object as everywhere else.
        self.write_policy(policy_with(exposure={"deepseek/": "trains"}))
        out, err, code = self.run_cli("--domain", "writing", "--sensitive",
                                      "--budget", "1000", "--json")
        self.assertEqual(code, 0)
        # The stop message moved into the object; only the harness's quota
        # warning may remain on stderr.
        self.assertNotIn("no candidate admitted", err)
        payload = self.last_json_line_is_the_only_json_line(out)
        self.assertEqual(payload["mode"], "budget")
        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["verdict"], "blocked")
        self.assertEqual(payload["reason"], "no eligible local candidate")
        self.zone_of(payload)

    def test_an_empty_pool_stop_still_answers_with_one_object(self):
        self.write_policy(policy_with(domains={"writing": ["content_writing"]},
                                      hints={}, summaries={}))
        world = build_world()
        world["classifications"]["classifications"][0]["models"] = []
        out, err, code = self.run_cli("--domain", "writing", "--budget",
                                      "1000", "--json", world=world)
        self.assertEqual(code, 0)
        self.assertNotIn("no ranked candidates", err)
        payload = self.last_json_line_is_the_only_json_line(out)
        self.assertEqual(payload["mode"], "budget")
        self.assertEqual(payload["verdict"], "blocked")
        self.assertEqual(payload["reason"], "no ranked candidates")

    def test_json_alongside_a_losing_flag_is_a_usage_error(self):
        # The flag would be silently ignored - dispatch order decides which
        # mode wins - so the combination stops as the usage error it is
        # (review: --status + a writer passed the gate while the writer won).
        for argv in (("--json", "--status", "--list-domains"),
                     ("--json", "--check-secrets", "--write-zones"),
                     ("--json", "--assert-allowed", "--domain", "writing"),
                     ("--json", "--status", "--domain", "writing",
                      "--budget", "1000"),
                     ("--json", "--domain", "writing"),
                     ("--json",)):
            with self.subTest(argv=argv):
                _, err, code = self.run_cli(*argv,
                                            "--working-dir", self.root)
                self.assertEqual(code, 2)
                self.assertIn("--json", err)

    def test_assert_allowed_allowed_is_one_object(self):
        # The allowed verdict now belongs to the stated-plain shape (ADR
        # 0008 makes the assumed-Sensitive default local-only); the object
        # carries it with the shape it was judged under.
        out, err, code = self.run_cli("--assert-allowed", "--json", "--plain",
                                      "--model", "deepseek/deepseek-v4-pro",
                                      "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        payload = self.one_object(out)
        self.assertEqual(payload["mode"], "assert-allowed")
        self.assertIs(payload["allowed"], True)
        self.assertEqual(payload["model"], "deepseek/deepseek-v4-pro")
        self.assertEqual(payload["shape"], "plain")
        self.assertEqual(self.zone_of(payload)["posture"], "open")
        self.assertIsNone(payload["reason"])

    def test_assert_allowed_blocked_is_one_object(self):
        out, _, code = self.run_cli("--assert-allowed", "--json",
                                    "--model", "vendor/model:free",
                                    "--working-dir", self.root,
                                    zones=[self.root])
        self.assertEqual(code, 0)
        payload = self.one_object(out)
        self.assertIs(payload["allowed"], False)
        self.assertEqual(self.zone_of(payload)["posture"], "closed")
        self.assertIn("remote free route is prohibited", payload["reason"])

    def test_the_json_face_states_the_printed_verdict_vocabulary(self):
        # The output contract (spec #75): the machine face's values are the
        # printed verdict vocabulary, asserted at the same seam. Each blocked
        # stop is the locked `blocked: <reason>` pattern, and the object
        # carries the same verdict word and reason the lines print.
        out, _, code = self.run_cli("--assert-allowed", "--model",
                                    "vendor/model:free",
                                    "--working-dir", self.root,
                                    zones=[self.root])
        self.assertEqual(code, 0)
        stop = next(ln for ln in out.splitlines()
                    if ln.startswith("blocked: "))
        self.assertEqual(stop, "blocked: free-use zone")
        reason_line = next(ln for ln in out.splitlines()
                           if ln.startswith("reason: "))
        payload = json.loads(self.run_cli(
            "--assert-allowed", "--json", "--model", "vendor/model:free",
            "--working-dir", self.root, zones=[self.root])[0])
        self.assertIs(payload["allowed"], False)
        self.assertEqual(payload["reason"], reason_line[len("reason: "):])

        # The Exposure clause, same rule: the prose the lines print is the
        # reason the object carries, and the table's `exposed (<class>)`
        # mark appears in neither face.
        out, _, code = self.run_cli("--assert-allowed", "--model",
                                    "deepseek/deepseek-v4-pro",
                                    "--working-dir", self.root)
        self.assertEqual(code, 0)
        reason_line = next(ln for ln in out.splitlines()
                           if ln.startswith("reason: "))
        self.assertIn("(no-retention)", reason_line)
        self.assertNotIn("exposed (", out)
        payload = json.loads(self.run_cli(
            "--assert-allowed", "--json", "--model",
            "deepseek/deepseek-v4-pro", "--working-dir", self.root)[0])
        self.assertEqual(payload["reason"], reason_line[len("reason: "):])

        # The ranking's blocked stop: the object's verdict is the stop's own
        # word and its reason is the stop's reason.
        self.write_policy(policy_with(exposure={"deepseek/": "trains"}))
        out, _, code = self.run_cli("--domain", "writing", "--sensitive")
        self.assertEqual(code, 0)
        stop = next(ln for ln in out.splitlines()
                    if ln.startswith("blocked: "))
        self.assertEqual(stop, "blocked: no eligible local candidate")
        payload = json.loads(self.run_cli(
            "--domain", "writing", "--sensitive", "--budget", "1000",
            "--json")[0].splitlines()[-1])
        self.assertEqual(payload["verdict"], "blocked")
        self.assertEqual(payload["reason"], stop[len("blocked: "):])

    # --- --status ---------------------------------------------------------

    def test_status_is_one_object(self):
        out, err, code = self.run_cli("--status", "--json",
                                      "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        payload = self.one_object(out)
        self.assertEqual(payload["mode"], "status")
        self.assertEqual(self.zone_of(payload)["posture"], "open")
        self.assertTrue(payload["zones_file"]["present"])
        self.assertTrue(payload["zones_file"]["path"].endswith(
            "/config/modelbandit/zones.json"))
        # The secrets surface is the built-in rules in force — a note, not
        # a file to report on (spec #75).
        self.assertEqual(payload["secrets"], {"rules": "built-in"})
        self.assertNotIn("secrets_file", payload)
        self.assertEqual(payload["policy"]["path"], self.policy_path)
        self.assertEqual(payload["policy"]["age_days"], 0)

    # --- the deal/budget verdict inside a ranking run ---------------------

    def test_budget_over_is_one_object_after_the_table(self):
        out, _, code = self.run_cli("--domain", "writing", "--deal",
                                    "--budget", "0", "--json")
        self.assertEqual(code, 0)
        self.assertIn("| # | model |", out)        # the table stays lines
        self.assertNotIn("budget: $0.00 -> OVER", out)  # the line is replaced
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "budget")
        self.assertIs(payload["ok"], True)
        self.assertIs(payload["over_budget"], True)
        self.assertEqual(payload["budget"], 0.0)
        projection = payload["projection"]
        for key in ("tickets", "total", "floor", "baseline"):
            self.assertIn(key, projection)
        self.assertGreater(projection["total"], 0.0)
        self.assertEqual(self.zone_of(payload)["posture"], "open")

    def test_budget_under_is_one_object_and_completes(self):
        out, _, code = self.run_cli("--domain", "writing", "--budget",
                                    "1000", "--json")
        self.assertIn(code, (None, 0))
        self.assertNotIn("budget: $1000.00 -> under", out)
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "budget")
        self.assertIs(payload["over_budget"], False)

    # --- a mode it does not serve is a usage error ------------------------

    def test_json_outside_the_answer_modes_is_a_usage_error(self):
        for argv in (("--json",),
                     ("--json", "--check-policy"),
                     ("--json", "--list-domains"),
                     ("--json", "--write-zones"),
                     ("--json", "--domain", "writing"),
                     ("--json", "--domain", "writing", "--budget", "1",
                      "--check-policy")):
            with self.subTest(argv=argv):
                out, err, code = self.run_cli(*argv)
                self.assertEqual(code, 2)
                self.assertIn("--json is read only by", err)
                self.assertEqual(out, "")


class HelpRecitesV2StatusesTests(ModelbanditCli):
    """AC: `--help` recites only the v2 statuses — 0 for any verdict, 4
    rules/config, 2 usage — never a retired answer code."""

    def joined_help(self):
        out, err, code = self.run_cli("--help")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        return " ".join(out.split())

    def test_no_retired_code_appears_in_help(self):
        joined = self.joined_help()
        for retired in ("1 sensitive", "3 not certified",
                        "5 blocked by the free-use zone"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, joined)

    def test_help_states_the_v2_statuses_and_the_json_flag(self):
        joined = self.joined_help()
        self.assertIn("Exit 0 for every verdict", joined)   # check-secrets
        self.assertIn("Exit 0 either way", joined)          # assert-allowed
        self.assertIn("4 rules/config error", joined)
        self.assertIn("4 policy/config error", joined)
        self.assertIn("2 usage error", joined)
        self.assertIn("--json", joined)


if __name__ == "__main__":
    unittest.main()
