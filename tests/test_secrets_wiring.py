"""Tests for the Secrets gate's wiring: the rules file, machine facts,
gitignored content, and the CLI check that turns material into a verdict.

The decision stays pure (`secrets_gate`/`secrets_verdict`); the file reads and
git calls live at the edges and are injected here, so every test is
deterministic and network-free. The loader, the machine facts and the
gitignored content are what give the project's rules file teeth.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402


class TempDirMixin(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path) or self.root, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def write_rules(self, payload):
        return self.write("modelrouter.secrets.json", json.dumps(payload))


class SecretsRulesLoaderTests(TempDirMixin):
    """`modelrouter.secrets.json` at the working-folder root, validated."""

    def test_loads_phrases_and_patterns(self):
        path = self.write_rules({"phrases": ["acme-internal", "Project Bluebird"],
                                 "patterns": [r"ACME-\d{4}"]})
        rules = bind.load_secrets_rules(path)
        self.assertEqual(rules["phrases"],
                         ["acme-internal", "Project Bluebird"])
        self.assertEqual(rules["patterns"], [r"ACME-\d{4}"])

    def test_missing_file_is_a_no_op(self):
        self.assertEqual(
            bind.load_secrets_rules(os.path.join(self.root, "absent.json")), {})

    def test_unknown_top_level_key_fails_loudly(self):
        path = self.write_rules({"phrase": ["typo"]})
        with self.assertRaisesRegex(SystemExit, "phrase"):
            bind.load_secrets_rules(path)

    def test_phrases_must_be_non_empty_strings(self):
        for payload in ({"phrases": "a string"}, {"phrases": [""]},
                        {"phrases": ["ok", 7]}):
            with self.subTest(payload=payload):
                path = self.write_rules(payload)
                with self.assertRaisesRegex(SystemExit, "phrases"):
                    bind.load_secrets_rules(path)

    def test_patterns_must_be_strings(self):
        path = self.write_rules({"patterns": [42]})
        with self.assertRaisesRegex(SystemExit, "patterns"):
            bind.load_secrets_rules(path)

    def test_invalid_regex_fails_loudly_naming_it(self):
        path = self.write_rules({"patterns": [r"ok-\d+", r"broken-([unclosed"]})
        with self.assertRaisesRegex(SystemExit, r"broken-\(\[unclosed"):
            bind.load_secrets_rules(path)

    def test_loaded_rules_tighten_but_never_disable_the_built_ins(self):
        path = self.write_rules({"phrases": ["ordinary fixture phrase"]})
        rules = bind.load_secrets_rules(path)
        self.assertTrue(bind.secrets_gate("ordinary fixture phrase",
                                          rules=rules))
        self.assertTrue(bind.secrets_gate("password=still-sensitive",
                                          rules=rules))


HOST = "buildbox-7f2a"
USER = "katarzyna"
HOME = "/home/katarzyna"
ADDRESS = "192.168.1.42"
MATERIAL = f"Deploy to {HOST} tonight, then report back."


def facts(**overrides):
    """Machine facts from injected readers: deterministic, no real machine."""
    readers = dict(hostname=lambda: HOST, username=lambda: USER,
                   home=lambda: HOME, addresses=lambda: [ADDRESS])
    readers.update(overrides)
    return bind.machine_facts(**readers)


class MachineFactsTests(unittest.TestCase):
    """The tool gathers machine identifiers itself; no caller assembly."""

    def test_gathers_hostname_username_home_and_addresses(self):
        machine = facts()
        self.assertEqual(machine["hostname"], HOST)
        self.assertEqual(machine["username"], USER)
        self.assertEqual(machine["home"], HOME)
        self.assertEqual(machine["addresses"], [ADDRESS])
        for value in (HOST, USER, HOME, ADDRESS):
            self.assertIn(value, machine["identifiers"])

    def test_hostname_in_the_material_trips_without_caller_assembly(self):
        self.assertTrue(bind.secrets_gate(MATERIAL, machine=facts()))

    def test_bare_gate_without_gathered_facts_stays_inert(self):
        # The regression this ticket closes: the decision alone, with nothing
        # gathered, cannot see a hostname.
        self.assertFalse(bind.secrets_gate(MATERIAL, machine={}))
        self.assertFalse(bind.secrets_gate(MATERIAL))

    def test_failing_readers_never_crash(self):
        def boom():
            raise OSError("no such source")
        machine = facts(hostname=boom, username=boom, home=boom, addresses=boom)
        self.assertEqual(machine["identifiers"], [])
        self.assertFalse(bind.secrets_gate(MATERIAL, machine=machine))

    def test_short_or_trivial_values_are_not_identifiers(self):
        # A four-character floor: a login short enough to occur in ordinary
        # prose would make every shape Sensitive.
        machine = facts(username=lambda: "al", home=lambda: "/")
        self.assertNotIn("al", machine["identifiers"])
        self.assertNotIn("/", machine["identifiers"])
        self.assertFalse(bind.secrets_gate("We shell into al and read /",
                                           machine=machine))

    def test_loopback_addresses_are_not_identifiers(self):
        machine = facts(addresses=lambda: ["127.0.0.1", "::1"])
        self.assertEqual(machine["identifiers"], [HOST, USER, HOME])


class GitignoredContentTests(TempDirMixin):
    """A repository's `.gitignore` is its own list of what must not leak, so
    content from a gitignored file is outside content by default."""

    ENV = ("# deployment notes\n"
           "DATABASE_URL=postgres://acme:hunter2@db.internal/acme\n"
           "short\n"
           "ACME_SSO_TENANT=bluebird-prod\n")

    def gather(self, files=(".env",), env=ENV):
        return bind.gitignored_facts(self.root,
                                     run=lambda argv: "\n".join(files),
                                     reader=lambda path: env)

    def test_significant_lines_become_candidate_facts(self):
        self.assertEqual(self.gather(), [
            {"path": ".env",
             "line": "DATABASE_URL=postgres://acme:hunter2@db.internal/acme"},
            {"path": ".env", "line": "ACME_SSO_TENANT=bluebird-prod"},
        ])

    def test_material_quoting_a_gitignored_line_trips_and_names_the_file(self):
        facts_ = self.gather()
        material = "Set ACME_SSO_TENANT=bluebird-prod before the migration."
        self.assertTrue(bind.secrets_gate(material,
                                          machine={"gitignored": facts_}))
        self.assertEqual(bind.secrets_verdict(material,
                                              machine={"gitignored": facts_}),
                         (True, "gitignored content (.env)"))

    def test_material_about_the_file_without_its_content_is_safe(self):
        self.assertFalse(bind.secrets_gate("Read the .env for the URL",
                                           machine={"gitignored": self.gather()}))

    def test_git_absent_or_failing_is_silent(self):
        def boom(argv):
            raise FileNotFoundError("git")
        self.assertEqual(bind.gitignored_facts(self.root, run=boom), [])
        self.assertEqual(bind.gitignored_facts(self.root,
                                               run=lambda argv: ""), [])

    def test_unreadable_files_are_skipped(self):
        def reader(path):
            raise OSError("permission denied")
        self.assertEqual(
            bind.gitignored_facts(self.root, run=lambda argv: ".env",
                                  reader=reader), [])

    def test_file_count_and_bytes_are_capped(self):
        facts_ = bind.gitignored_facts(
            self.root, run=lambda argv: "\n".join(f"f{i}.env" for i in range(30)),
            reader=lambda path: "SECRET_" + path + "_VALUE_IS_LONG",
            max_files=3)
        self.assertEqual({fact["path"] for fact in facts_},
                         {"f0.env", "f1.env", "f2.env"})
        capped = bind.gitignored_facts(
            self.root, run=lambda argv: ".env",
            reader=lambda path: "A" * 100, max_bytes=8)
        self.assertEqual([fact["line"] for fact in capped], ["A" * 8])

    def test_default_reader_reads_a_capped_slice_of_a_real_file(self):
        self.write(".env", "ACME_SSO_TENANT=bluebird-prod\n")
        facts_ = bind.gitignored_facts(self.root, run=lambda argv: ".env",
                                       max_bytes=8)
        self.assertEqual([fact["line"] for fact in facts_], ["ACME_SSO"])

    def test_the_same_line_in_two_files_is_kept_once(self):
        facts_ = self.gather(files=(".env", "secrets.yaml"))
        paths = {fact["path"] for fact in facts_}
        self.assertEqual(paths, {".env"})


class VerdictRuleTests(unittest.TestCase):
    """The verdict names the rule that tripped, without echoing its value."""

    def test_machine_fact_names_its_class(self):
        cases = (("hostname", HOST, "hostname"), ("username", USER, "username"),
                 ("home", HOME, "home path"),
                 ("addresses", [ADDRESS], "local address"))
        for field, value, rule in cases:
            with self.subTest(field=field):
                sensitive, named = bind.secrets_verdict(
                    f"the material mentions {ADDRESS if field == 'addresses' else value}",
                    machine={field: value})
                self.assertTrue(sensitive)
                self.assertEqual(named, rule)

    def test_safe_material_has_no_rule(self):
        self.assertEqual(bind.secrets_verdict("Summarize the public API",
                                              machine={}), (False, ""))

    def test_credential_pattern_is_named(self):
        sensitive, named = bind.secrets_verdict("api_key: sk-1234567890abcdef",
                                                machine={})
        self.assertTrue(sensitive)
        self.assertEqual(named, "password, token or key assignment")

    def test_project_phrase_is_named_by_index_not_echoed(self):
        rules = {"phrases": ["acme-internal", "Project Bluebird"]}
        sensitive, named = bind.secrets_verdict(
            "Publish the Project Bluebird notes", machine={}, rules=rules)
        self.assertTrue(sensitive)
        self.assertEqual(named, "phrase #2")
        self.assertNotIn("Bluebird", named)

    def test_project_pattern_is_named_by_index(self):
        rules = {"patterns": [r"zen-\d{4}"]}
        sensitive, named = bind.secrets_verdict("ticket zen-1042", machine={},
                                                rules=rules)
        self.assertTrue(sensitive)
        self.assertEqual(named, "pattern #1")

    def test_gate_is_the_verdict_boolean(self):
        self.assertTrue(bind.secrets_gate("host " + HOST,
                                          machine={"hostname": HOST}))
        self.assertFalse(bind.secrets_gate("host " + HOST, machine={}))


class WorkingRootTests(TempDirMixin):
    """The working-folder root is the git root when in a repo, else cwd."""

    def test_git_root_wins_inside_a_repository(self):
        top = os.path.join(self.root, "top")
        self.assertEqual(
            bind.resolve_working_root(os.path.join(self.root, "deep", "down"),
                                      run=lambda args: top + "\n"),
            os.path.abspath(top))

    def test_git_absent_or_failing_leaves_the_given_folder(self):
        def boom(args):
            raise FileNotFoundError("git")
        self.assertEqual(bind.resolve_working_root(self.root, run=boom),
                         os.path.abspath(self.root))

    def test_no_git_reports_no_root(self):
        self.assertEqual(bind.resolve_working_root(self.root, run=lambda a: "\n"),
                         os.path.abspath(self.root))


class SecretsCheckTests(TempDirMixin):
    """The edge composer: rules file, machine facts and gitignored content,
    each injectable, assembled into one verdict."""

    def test_a_rules_file_changes_the_verdict_for_the_same_material(self):
        material = "Ship the Project Bluebird notes."
        self.assertEqual(bind.secrets_check(material, root=self.root,
                                            machine={}, gitignored=[]),
                         (False, ""))
        self.write_rules({"phrases": ["Project Bluebird"]})
        self.assertEqual(bind.secrets_check(material, root=self.root,
                                            machine={}, gitignored=[]),
                         (True, "phrase #1"))

    def test_machine_facts_are_gathered_when_not_injected(self):
        with mock.patch("bind.machine_facts",
                        return_value={"hostname": HOST, "identifiers": [HOST]}):
            self.assertEqual(bind.secrets_check(MATERIAL, root=self.root,
                                                gitignored=[]),
                             (True, "hostname"))

    def test_gitignored_content_is_gathered_when_not_injected(self):
        with mock.patch("bind.machine_facts", return_value={"identifiers": []}), \
                mock.patch("bind.gitignored_facts",
                           return_value=[{"path": ".env",
                                          "line": "ACME_TOKEN=abc123"}]):
            self.assertEqual(bind.secrets_check(
                "ACME_TOKEN=abc123 is the value", root=self.root),
                (True, "gitignored content (.env)"))


class SecretsCliTests(TempDirMixin):
    """`--check-secrets`: material on stdin, verdict and rule out, exit status
    distinguishing safe from sensitive."""

    def run_cli(self, *argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        code = None
        with mock.patch.object(sys, "argv", ["bind.py", *argv]), \
                mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch("bind.machine_facts", return_value={"identifiers": []}), \
                mock.patch("bind.fetch_json",
                           side_effect=AssertionError("no network in a gate")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                bind.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code

    def test_safe_material_exits_zero(self):
        out, _, code = self.run_cli("--check-secrets",
                                    stdin="Summarize the public API")
        self.assertEqual(code, 0)
        self.assertIn("secrets gate: safe", out)

    def test_sensitive_material_exits_one_and_names_the_rule(self):
        out, _, code = self.run_cli("--check-secrets",
                                    stdin="api_key: sk-1234567890abcdef")
        self.assertEqual(code, 1)
        self.assertIn("secrets gate: sensitive", out)
        self.assertIn("rule: password, token or key assignment", out)

    def test_empty_material_is_not_certified(self):
        for stdin in ("", "   \n\n"):
            with self.subTest(stdin=stdin):
                out, _, code = self.run_cli("--check-secrets", stdin=stdin)
                self.assertEqual(code, 3)
                self.assertIn("not certified", out)
                self.assertNotIn("secrets gate: safe", out)

    def test_project_rules_file_at_the_working_dir_applies(self):
        self.write_rules({"phrases": ["Project Bluebird"]})
        out, _, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root,
                                    stdin="Ship the Project Bluebird notes.")
        self.assertEqual(code, 1)
        self.assertIn("rule: phrase #1", out)
        self.assertIn(os.path.join(self.root, "modelrouter.secrets.json"), out)

    def test_another_working_dir_does_not_see_those_rules(self):
        self.write_rules({"phrases": ["Project Bluebird"]})
        with tempfile.TemporaryDirectory() as other:
            out, _, code = self.run_cli("--check-secrets", "--working-dir", other,
                                        stdin="Ship the Project Bluebird notes.")
        self.assertEqual(code, 0)
        self.assertIn("secrets gate: safe", out)

    def test_a_malformed_rules_file_stops_the_check_loudly(self):
        self.write_rules({"phrase": ["typo"]})
        _, _, code = self.run_cli("--check-secrets", "--working-dir",
                                  self.root, stdin="anything at all")
        self.assertIn("unknown secret rule key(s)", str(code))
        self.assertIn("phrase", str(code))


class SecretsWriterCliTests(TempDirMixin):
    """`--write-secrets` merges confirmed rules without removing prior rules."""

    def run_writer(self, payload):
        out, err, code = io.StringIO(), io.StringIO(), None
        with mock.patch.object(sys, "argv", [
                "bind.py", "--write-secrets", "--working-dir", self.root]), \
                mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                mock.patch("bind.fetch_json",
                           side_effect=AssertionError("no network in writer")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                bind.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code

    def test_rerun_keeps_existing_rules_and_deduplicates_exact_repeats(self):
        self.write_rules({"phrases": ["existing client name"],
                          "patterns": [r"old-key-\d+"]})
        payload = json.dumps({
            "phrases": ["existing client name", "new client name",
                        "new client name"],
            "patterns": [r"old-key-\d+", r"new-key-\d+",
                         r"new-key-\d+"],
            "identifying": False, "commit": True,
        })

        first, _, code = self.run_writer(payload)
        second, _, second_code = self.run_writer(payload)

        self.assertEqual(code, 0)
        self.assertEqual(second_code, 0)
        rules = bind.load_secrets_rules(
            os.path.join(self.root, "modelrouter.secrets.json"))
        self.assertEqual(rules["phrases"],
                         ["existing client name", "new client name"])
        self.assertEqual(rules["patterns"],
                         [r"old-key-\d+", r"new-key-\d+"])
        self.assertIn("added phrase", first)
        self.assertIn("already present phrase", second)

    def test_identifying_rules_add_gitignore_entry_only_once(self):
        self.write(".gitignore", "cache")
        payload = json.dumps({"phrases": ["client codename"], "patterns": [],
                              "identifying": True, "commit": True})

        first, _, code = self.run_writer(payload)
        second, _, second_code = self.run_writer(payload)

        self.assertEqual(code, 0)
        self.assertEqual(second_code, 0)
        with open(os.path.join(self.root, ".gitignore"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(lines, ["cache", "modelrouter.secrets.json"])
        self.assertIn("gitignore: appended modelrouter.secrets.json", first)
        self.assertIn("gitignore: already contains modelrouter.secrets.json", second)

    def test_committed_rules_leave_gitignore_untouched(self):
        original = "# Existing ignores\n.env\n"
        self.write(".gitignore", original)
        payload = json.dumps({"phrases": ["public codename"], "patterns": [],
                              "identifying": False, "commit": True})

        out, _, code = self.run_writer(payload)

        self.assertEqual(code, 0)
        with open(os.path.join(self.root, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read(), original)
        self.assertIn("meant to be committed", out)

    def test_commit_false_adds_gitignore_entry_even_when_not_identifying(self):
        payload = json.dumps({"phrases": ["local project alias"], "patterns": [],
                              "identifying": False, "commit": False})

        out, _, code = self.run_writer(payload)

        self.assertEqual(code, 0)
        with open(os.path.join(self.root, ".gitignore"), encoding="utf-8") as f:
            self.assertIn("modelrouter.secrets.json", f.read().splitlines())
        self.assertIn("gitignore: appended", out)

    def test_invalid_json_and_rule_shapes_fail_loudly(self):
        cases = (("{", "invalid JSON"),
                 (json.dumps({"phrases": "not a list", "patterns": [],
                              "identifying": False, "commit": True}), "phrases"),
                 (json.dumps({"phrases": [], "patterns": ["("],
                              "identifying": False, "commit": True}), "patterns"))
        for payload, problem in cases:
            with self.subTest(problem=problem):
                _, _, code = self.run_writer(payload)
                self.assertIn(problem, str(code))
                self.assertFalse(os.path.exists(
                    os.path.join(self.root, "modelrouter.secrets.json")))


class SecretsEndToEndTests(TempDirMixin):
    """The whole mechanism, unpatched: real machine facts, real files, real
    git. A file on disk changes the verdict for the same material — the gap
    that reopened because no such test existed."""

    def run_check(self, working_dir, material):
        out, err, code = io.StringIO(), io.StringIO(), None
        with mock.patch.object(sys, "argv", ["bind.py", "--check-secrets",
                                             "--working-dir", working_dir]), \
                mock.patch.object(sys, "stdin", io.StringIO(material)), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                bind.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), code

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, *args], check=True,
                       capture_output=True, text=True)

    def test_a_rules_file_written_to_the_folder_changes_the_verdict(self):
        material = "Ship the Project Bluebird notes to the client."
        before, code = self.run_check(self.root, material)
        self.assertEqual(code, 0, before)
        self.assertIn("secrets gate: safe", before)

        self.write_rules({"phrases": ["Project Bluebird"]})

        after, code = self.run_check(self.root, material)
        self.assertEqual(code, 1, after)
        self.assertIn("secrets gate: sensitive", after)
        self.assertIn("rule: phrase #1", after)

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_a_gitignored_env_file_trips_the_gate_end_to_end(self):
        self.git("init", "-q")
        self.write(".gitignore", ".env\n")
        self.write(".env", "# live credentials\n"
                           "ACME_SSO_TENANT=bluebird-prod-7f2a\n")
        material = "Set ACME_SSO_TENANT=bluebird-prod-7f2a for the migration."

        out, code = self.run_check(self.root, material)

        self.assertEqual(code, 1, out)
        self.assertIn("rule: gitignored content (.env)", out)

    def test_the_real_hostname_trips_without_caller_assembly(self):
        import socket
        host = socket.gethostname()
        if len(host) < bind.MIN_IDENTIFIER_LEN:
            self.skipTest(f"hostname {host!r} is too short to identify")
        out, code = self.run_check(self.root, f"Deploy to {host} tonight.")
        self.assertEqual(code, 1, out)
        self.assertIn("rule: hostname", out)

    def test_material_matching_nothing_is_safe_on_this_machine(self):
        out, code = self.run_check(self.root, "Summarize the public API docs.")
        self.assertEqual(code, 0, out)
        self.assertIn("secrets gate: safe", out)


if __name__ == "__main__":
    unittest.main()

