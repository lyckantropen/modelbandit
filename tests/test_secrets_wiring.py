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
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


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
        return self.write("modelbandit.secrets.json", json.dumps(payload))


class SecretsRulesLoaderTests(TempDirMixin):
    """`modelbandit.secrets.json` at the working-folder root, validated."""

    def test_loads_phrases_and_patterns(self):
        path = self.write_rules({"phrases": ["acme-internal", "Project Bluebird"],
                                 "patterns": [r"ACME-\d{4}"]})
        rules = modelbandit.load_secrets_rules(path)
        self.assertEqual(rules["phrases"],
                         ["acme-internal", "Project Bluebird"])
        self.assertEqual(rules["patterns"], [r"ACME-\d{4}"])

    def test_missing_file_is_a_no_op(self):
        self.assertEqual(
            modelbandit.load_secrets_rules(os.path.join(self.root, "absent.json")), {})

    def test_unknown_top_level_key_fails_loudly(self):
        path = self.write_rules({"phrase": ["typo"]})
        with self.assertRaisesRegex(SystemExit, "phrase"):
            modelbandit.load_secrets_rules(path)

    def test_phrases_must_be_non_empty_strings(self):
        cases = (({"phrases": "a string"}, "phrases"),
                 ({"phrases": [""]}, "phrase #1"),
                 ({"phrases": ["ok", 7]}, "phrase #2"))
        for payload, expected in cases:
            with self.subTest(payload=payload):
                path = self.write_rules(payload)
                with self.assertRaisesRegex(SystemExit, expected):
                    modelbandit.load_secrets_rules(path)

    def test_patterns_must_be_strings(self):
        path = self.write_rules({"patterns": [42]})
        with self.assertRaisesRegex(SystemExit, "pattern #1"):
            modelbandit.load_secrets_rules(path)

    def test_invalid_regex_reports_its_index_without_echoing_the_value(self):
        invalid = r"broken-([unclosed"
        path = self.write_rules({"patterns": [r"ok-\d+", invalid]})
        with self.assertRaisesRegex(SystemExit,
                                    "pattern #2 is not a valid regex") as raised:
            modelbandit.load_secrets_rules(path)
        self.assertNotIn(invalid, str(raised.exception))

    def test_invalid_rule_value_is_never_echoed(self):
        secret = "classified-project-code-9721"
        path = self.write_rules({"phrases": [{"value": secret}]})

        with self.assertRaisesRegex(SystemExit, "phrase #1") as raised:
            modelbandit.load_secrets_rules(path)

        self.assertNotIn(secret, str(raised.exception))

    def test_loaded_rules_tighten_but_never_disable_the_built_ins(self):
        path = self.write_rules({"phrases": ["ordinary fixture phrase"]})
        rules = modelbandit.load_secrets_rules(path)
        self.assertTrue(modelbandit.secrets_gate("ordinary fixture phrase",
                                          rules=rules))
        self.assertTrue(modelbandit.secrets_gate("password=still-sensitive",
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
    return modelbandit.machine_facts(**readers)


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
        self.assertTrue(modelbandit.secrets_gate(MATERIAL, machine=facts()))

    def test_bare_gate_without_gathered_facts_stays_inert(self):
        # The regression this ticket closes: the decision alone, with nothing
        # gathered, cannot see a hostname.
        self.assertFalse(modelbandit.secrets_gate(MATERIAL, machine={}))
        self.assertFalse(modelbandit.secrets_gate(MATERIAL))

    def test_failing_readers_never_crash(self):
        def boom():
            raise OSError("no such source")
        machine = facts(hostname=boom, username=boom, home=boom, addresses=boom)
        self.assertEqual(machine["identifiers"], [])
        self.assertFalse(modelbandit.secrets_gate(MATERIAL, machine=machine))

    def test_short_or_trivial_values_are_not_identifiers(self):
        # A four-character floor: a login short enough to occur in ordinary
        # prose would make every shape Sensitive.
        machine = facts(username=lambda: "al", home=lambda: "/")
        self.assertNotIn("al", machine["identifiers"])
        self.assertNotIn("/", machine["identifiers"])
        self.assertFalse(modelbandit.secrets_gate("We shell into al and read /",
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
        return modelbandit.gitignored_facts(self.root,
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
        self.assertTrue(modelbandit.secrets_gate(material,
                                          machine={"gitignored": facts_}))
        self.assertEqual(modelbandit.secrets_verdict(material,
                                              machine={"gitignored": facts_}),
                         (True, "gitignored content (.env)"))

    def test_material_about_the_file_without_its_content_is_safe(self):
        self.assertFalse(modelbandit.secrets_gate("Read the .env for the URL",
                                           machine={"gitignored": self.gather()}))

    def test_git_absent_or_failing_is_silent(self):
        def boom(argv):
            raise FileNotFoundError("git")
        self.assertEqual(modelbandit.gitignored_facts(self.root, run=boom), [])
        self.assertEqual(modelbandit.gitignored_facts(self.root,
                                               run=lambda argv: ""), [])

    def test_unreadable_files_are_skipped(self):
        def reader(path):
            raise OSError("permission denied")
        self.assertEqual(
            modelbandit.gitignored_facts(self.root, run=lambda argv: ".env",
                                  reader=reader), [])

    def test_file_count_and_bytes_are_capped(self):
        facts_ = modelbandit.gitignored_facts(
            self.root, run=lambda argv: "\n".join(f"f{i}.env" for i in range(30)),
            reader=lambda path: "SECRET_" + path + "_VALUE_IS_LONG",
            max_files=3)
        self.assertEqual({fact["path"] for fact in facts_},
                         {"f0.env", "f1.env", "f2.env"})
        capped = modelbandit.gitignored_facts(
            self.root, run=lambda argv: ".env",
            reader=lambda path: "A" * 100, max_bytes=8)
        self.assertEqual([fact["line"] for fact in capped], ["A" * 8])

    def test_default_reader_reads_a_capped_slice_of_a_real_file(self):
        self.write(".env", "ACME_SSO_TENANT=bluebird-prod\n")
        facts_ = modelbandit.gitignored_facts(self.root, run=lambda argv: ".env",
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
                sensitive, named = modelbandit.secrets_verdict(
                    f"the material mentions {ADDRESS if field == 'addresses' else value}",
                    machine={field: value})
                self.assertTrue(sensitive)
                self.assertEqual(named, rule)

    def test_safe_material_has_no_rule(self):
        self.assertEqual(modelbandit.secrets_verdict("Summarize the public API",
                                              machine={}), (False, ""))

    def test_credential_pattern_is_named(self):
        sensitive, named = modelbandit.secrets_verdict("api_key: sk-1234567890abcdef",
                                                machine={})
        self.assertTrue(sensitive)
        self.assertEqual(named, "password, token or key assignment")

    def test_project_phrase_is_named_by_index_not_echoed(self):
        rules = {"phrases": ["acme-internal", "Project Bluebird"]}
        sensitive, named = modelbandit.secrets_verdict(
            "Publish the Project Bluebird notes", machine={}, rules=rules)
        self.assertTrue(sensitive)
        self.assertEqual(named, "phrase #2")
        self.assertNotIn("Bluebird", named)

    def test_project_pattern_is_named_by_index(self):
        rules = {"patterns": [r"zen-\d{4}"]}
        sensitive, named = modelbandit.secrets_verdict("ticket zen-1042", machine={},
                                                rules=rules)
        self.assertTrue(sensitive)
        self.assertEqual(named, "pattern #1")

    def test_gate_is_the_verdict_boolean(self):
        self.assertTrue(modelbandit.secrets_gate("host " + HOST,
                                          machine={"hostname": HOST}))
        self.assertFalse(modelbandit.secrets_gate("host " + HOST, machine={}))


class WorkingRootTests(TempDirMixin):
    """The working-folder root is the git root when in a repo, else cwd."""

    def test_git_root_wins_inside_a_repository(self):
        top = os.path.join(self.root, "top")
        self.assertEqual(
            modelbandit.resolve_working_root(os.path.join(self.root, "deep", "down"),
                                      run=lambda args: top + "\n"),
            os.path.abspath(top))

    def test_git_absent_or_failing_leaves_the_given_folder(self):
        def boom(args):
            raise FileNotFoundError("git")
        self.assertEqual(modelbandit.resolve_working_root(self.root, run=boom),
                         os.path.abspath(self.root))

    def test_no_git_reports_no_root(self):
        self.assertEqual(modelbandit.resolve_working_root(self.root, run=lambda a: "\n"),
                         os.path.abspath(self.root))


class SecretsCheckTests(TempDirMixin):
    """The edge composer: rules file, machine facts and gitignored content,
    each injectable, assembled into one verdict."""

    def test_a_rules_file_changes_the_verdict_for_the_same_material(self):
        material = "Ship the Project Bluebird notes."
        self.assertEqual(modelbandit.secrets_check(material, root=self.root,
                                            machine={}, gitignored=[]),
                         (False, ""))
        self.write_rules({"phrases": ["Project Bluebird"]})
        self.assertEqual(modelbandit.secrets_check(material, root=self.root,
                                            machine={}, gitignored=[]),
                         (True, "phrase #1"))

    def test_machine_facts_are_gathered_when_not_injected(self):
        with mock.patch("modelbandit.machine_facts",
                        return_value={"hostname": HOST, "identifiers": [HOST]}):
            self.assertEqual(modelbandit.secrets_check(MATERIAL, root=self.root,
                                                gitignored=[]),
                             (True, "hostname"))

    def test_gitignored_content_is_gathered_when_not_injected(self):
        with mock.patch("modelbandit.machine_facts", return_value={"identifiers": []}), \
                mock.patch("modelbandit.gitignored_facts",
                           return_value=[{"path": ".env",
                                          "line": "ACME_TOKEN=abc123"}]):
            self.assertEqual(modelbandit.secrets_check(
                "ACME_TOKEN=abc123 is the value", root=self.root),
                (True, "gitignored content (.env)"))


class SecretsCliTests(TempDirMixin):
    """`--check-secrets`: material on stdin, verdict and rule out, exit status
    distinguishing safe from sensitive."""

    def run_cli(self, *argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        code = None
        config_home = os.path.join(self.root, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": [], "default": "open"}, f)
        with mock.patch.object(sys, "argv", ["modelbandit", *argv]), \
                mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch("modelbandit.machine_facts", return_value={"identifiers": []}), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                mock.patch("modelbandit.fetch_json",
                           side_effect=AssertionError("no network in a gate")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
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
        self.assertIn(os.path.join(self.root, "modelbandit.secrets.json"), out)

    def test_another_working_dir_does_not_see_those_rules(self):
        self.write_rules({"phrases": ["Project Bluebird"]})
        with tempfile.TemporaryDirectory() as other:
            out, _, code = self.run_cli("--check-secrets", "--working-dir", other,
                                        stdin="Ship the Project Bluebird notes.")
        self.assertEqual(code, 0)
        self.assertIn("secrets gate: safe", out)

    def test_a_malformed_rules_file_stops_the_check_loudly(self):
        self.write_rules({"phrase": ["typo"]})
        _, err, code = self.run_cli("--check-secrets", "--working-dir",
                                    self.root, stdin="anything at all")
        self.assertEqual(code, 4)
        self.assertIn("secrets gate: rules/config error", err)
        self.assertIn("unknown secret rule key(s)", err)

    def test_malformed_rules_file_is_reported_even_without_material(self):
        self.write_rules({"patterns": ["invalid-([regex"]})
        out, err, code = self.run_cli("--check-secrets", "--working-dir",
                                      self.root, stdin="")

        self.assertEqual(code, 4)
        self.assertIn("pattern #1 is not a valid regex", err)
        self.assertNotIn("not certified", out)
        self.assertNotIn("invalid-([regex", err)

    def test_named_outside_file_content_trips_the_gate(self):
        with tempfile.TemporaryDirectory() as outside:
            paths = [os.path.join(outside, f"deployment-notes-{i}.txt")
                     for i in range(2)]
            line = "OUTSIDE_DEPLOYMENT_TENANT=rare-tenant-7291"
            with open(paths[0], "w", encoding="utf-8") as f:
                f.write("unrelated notes\n")
            with open(paths[1], "w", encoding="utf-8") as f:
                f.write(line + "\n")
            out, _, code = self.run_cli(
                "--check-secrets", "--working-dir", self.root,
                "--outside-file", paths[0], "--outside-file", paths[1],
                stdin=f"Use {line} in deployment.")

        self.assertEqual(code, 1)
        self.assertIn("rule: outside-file content", out)
        self.assertNotIn(line, out)

    def test_named_outside_file_is_capped_to_eight_kilobytes(self):
        with tempfile.TemporaryDirectory() as outside:
            path = os.path.join(outside, "long-source.txt")
            beyond_cap = "SECRET_BEYOND_OUTSIDE_FILE_CAP_79d2"
            with open(path, "w", encoding="utf-8") as f:
                f.write("A" * modelbandit.GITIGNORED_MAX_BYTES + "\n" + beyond_cap)

            out, _, code = self.run_cli(
                "--check-secrets", "--working-dir", self.root,
                "--outside-file", path, stdin=f"Quote {beyond_cap}.")

        self.assertEqual(code, 0)
        self.assertIn("secrets gate: safe", out)


class ZoneBlockedCheckTests(TempDirMixin):
    """The check's free-use zone status: 5 when material provenance lies in a
    path the zones file declares closed, or when the model the shape will use
    is one the effective zone cannot admit. Statuses 0/1/3/4 keep their
    meanings, and the material is never echoed."""

    def setUp(self):
        super().setUp()
        self.config = os.path.join(self.root, "config")
        self.work = os.path.join(self.root, "work")
        self.sensitive = os.path.join(self.root, "sensitive-notes")
        self.closed = os.path.join(self.root, "closed-vault")
        os.makedirs(self.work)
        os.makedirs(self.sensitive)
        os.makedirs(self.closed)
        self.write_zones({"zones": [{"path": self.work, "free": "open"},
                                    {"path": self.sensitive,
                                     "free": "sensitive"},
                                    {"path": self.closed, "free": "closed"}],
                          "default": "closed"})

    def write_zones(self, payload):
        os.makedirs(os.path.join(self.config, "modelbandit"), exist_ok=True)
        with open(os.path.join(self.config, "modelbandit", "zones.json"), "w",
                  encoding="utf-8") as f:
            json.dump(payload, f)

    def run_check(self, *argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        code = None
        with mock.patch.object(sys, "argv", ["modelbandit", "--check-secrets",
                                             *argv]), \
                mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch("modelbandit.machine_facts",
                           return_value={"identifiers": []}), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.config}), \
                mock.patch("modelbandit.fetch_json",
                           side_effect=AssertionError("no network in a gate")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code

    def source(self, folder, line):
        path = os.path.join(folder, "notes.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(line + "\n")
        return path

    def test_provenance_inside_a_declared_closed_zone_blocks(self):
        line = "ORDINARY_PRIVATE_LINE_7f2a"
        path = self.source(self.closed, line)

        out, err, code = self.run_check("--working-dir", self.work,
                                        "--outside-file", path,
                                        stdin="Summarize it.")

        self.assertEqual(code, 5)
        self.assertIn("secrets gate: blocked by the free-use zone", out)
        self.assertIn(f"zone: {self.closed} (closed)", out)
        self.assertNotIn(line, out + err)        # the content never is
        self.assertNotIn("outside-file content", out)

    def test_a_broken_zones_file_is_a_config_error(self):
        self.write_zones({"zones": [{"path": self.work, "free": "opened"}]})

        out, err, code = self.run_check("--working-dir", self.work,
                                        stdin="Summarize it.")

        self.assertEqual(code, 4)
        self.assertIn("rules/config error", err)
        self.assertIn("opened", err)

    def test_the_check_states_the_zone_it_judged_by(self):
        out, _, code = self.run_check("--working-dir", self.work,
                                      stdin="Summarize the public API.")
        self.assertEqual(code, 0)
        self.assertIn(f"zone: {self.work} (open)", out)

    def test_a_source_in_an_open_zone_keeps_the_content_verdict(self):
        line = "OPEN_ZONE_TENANT_7291"
        path = self.source(self.work, line)

        out, _, code = self.run_check("--working-dir", self.work,
                                      "--outside-file", path,
                                      stdin=f"Use {line} in deployment.")

        self.assertEqual(code, 1)
        self.assertIn("rule: outside-file content", out)

    def test_a_source_in_a_sensitive_zone_keeps_the_content_verdict(self):
        line = "SENSITIVE_ZONE_TENANT_7291"
        path = self.source(self.sensitive, line)

        out, _, code = self.run_check("--working-dir", self.work,
                                      "--outside-file", path,
                                      stdin=f"Use {line} in deployment.")

        self.assertEqual(code, 1)
        self.assertIn("rule: outside-file content", out)

    def test_an_undeclared_source_is_blocked_by_the_closed_default(self):
        # The machine-wide default closes undeclared paths, so provenance
        # blocks before the Secrets gate judges the material.
        other = os.path.join(self.root, "undeclared")
        os.makedirs(other)
        line = "UNDECLARED_ZONE_LINE_5c0d"
        path = self.source(other, line)

        out, _, code = self.run_check("--working-dir", self.work,
                                      "--outside-file", path,
                                      stdin="Summarize it.")
        self.assertEqual(code, 5)
        self.assertIn("secrets gate: blocked by the free-use zone", out)
        self.assertIn("zone: undeclared (closed)", out)
        self.assertNotIn(line, out)

    def test_sensitive_material_in_a_closed_folder_still_exits_one(self):
        out, _, code = self.run_check("--working-dir", self.closed,
                                      stdin="api_key: sk-1234567890abcdef")
        self.assertEqual(code, 1)
        self.assertIn("secrets gate: sensitive", out)

    def test_sensitive_zone_block_uses_the_same_free_use_status_name(self):
        self.write_zones({"zones": [{"path": self.work, "free": "sensitive"}],
                          "default": "closed"})
        policy = os.path.join(self.root, "policy.json")
        with open(policy, "w", encoding="utf-8") as f:
            json.dump({"exposure": {"deepseek/": "trains"}}, f)

        out, _, code = self.run_check("--working-dir", self.work,
                                      "--model", "deepseek/model",
                                      "--policy", policy,
                                      stdin="Summarize the public API.")

        self.assertEqual(code, 5)
        self.assertIn("secrets gate: blocked by the free-use zone", out)
        self.assertIn(f"zone: {self.work} (sensitive)", out)
        self.assertIn("reason: exposed (trains)", out)

    def test_the_model_the_shape_will_use_is_checked_against_the_zone(self):
        out, _, code = self.run_check("--working-dir", self.closed,
                                      "--model", "z-ai/glm-5.4:free",
                                      stdin="Summarize the public API.")
        self.assertEqual(code, 5)
        self.assertIn("secrets gate: blocked by the free-use zone", out)
        self.assertIn(f"zone: {self.closed} (closed)", out)
        self.assertIn("remote free route is prohibited", out)

    def test_a_paid_model_in_a_closed_zone_is_not_blocked(self):
        out, _, code = self.run_check("--working-dir", self.closed,
                                      "--model", "deepseek/deepseek-v4-pro",
                                      stdin="Summarize the public API.")
        self.assertEqual(code, 0)
        self.assertIn("secrets gate: safe", out)

    def test_a_blocked_shape_is_not_certified_either(self):
        # The zone answers before the content does: an empty shape in a
        # closed folder with a free route is blocked (5), not uncertified (3).
        _, _, code = self.run_check("--working-dir", self.closed,
                                    "--model", "opencode/glm-5.3-flash",
                                    stdin="")
        self.assertEqual(code, 5)

    # --- provenance judges the place a path reaches: links resolved ------

    def link(self, link, target):
        """A junction on Windows (`mklink /J` needs no privileges), a symlink
        elsewhere."""
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", link, target],
                capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
        else:
            os.symlink(target, link)
        return link

    def test_a_source_named_through_a_link_into_a_closed_zone_blocks(self):
        # The source is named through a junction that sits in the open work
        # zone and points into the closed vault: the place it reaches
        # governs, the zone is named and the content never is.
        line = "PROVENANCE_BEHIND_LINK_3c9a"
        self.source(self.closed, line)
        link = self.link(os.path.join(self.work, "shortcut"), self.closed)

        out, err, code = self.run_check("--working-dir", self.work,
                                        "--outside-file",
                                        os.path.join(link, "notes.txt"),
                                        stdin="Summarize it.")

        self.assertEqual(code, 5)
        self.assertIn("secrets gate: blocked by the free-use zone", out)
        self.assertIn(f"zone: {self.closed} (closed)", out)
        self.assertNotIn(line, out + err)

    def test_a_source_through_a_link_into_an_open_zone_keeps_the_verdict(self):
        # The mirror direction: a link outside the open zone pointing at it
        # reaches open content, so the zone does not block and the Secrets
        # gate answers for the material itself.
        line = "OPEN_CONTENT_THROUGH_LINK_5d1b"
        self.source(self.work, line)
        link = self.link(os.path.join(self.root, "to-work"), self.work)

        out, _, code = self.run_check("--working-dir", self.work,
                                      "--outside-file",
                                      os.path.join(link, "notes.txt"),
                                      stdin=f"Use {line} in deployment.")

        self.assertEqual(code, 1)
        self.assertIn("rule: outside-file content", out)

    def test_a_provenance_block_names_the_resolved_place_of_a_declared_link(self):
        # A zone declared through a link governs the place it reaches; the
        # block names both the resolved place and the declared path.
        link = self.link(os.path.join(self.root, "closed-link"), self.closed)
        self.write_zones({"zones": [{"path": self.work, "free": "open"},
                                    {"path": link, "free": "closed"}],
                          "default": "closed"})
        line = "DECLARED_LINK_PROVENANCE_8e4f"
        self.source(self.closed, line)

        out, err, code = self.run_check("--working-dir", self.work,
                                        "--outside-file",
                                        os.path.join(self.closed, "notes.txt"),
                                        stdin="Summarize it.")

        self.assertEqual(code, 5)
        self.assertIn(f"zone: {self.closed} (closed) (declared: {link})", out)
        self.assertNotIn(line, out + err)


class SecretsWriterCliTests(TempDirMixin):
    """`--write-secrets` merges confirmed rules without removing prior rules."""

    def run_writer(self, payload):
        out, err, code = io.StringIO(), io.StringIO(), None
        with mock.patch.object(sys, "argv", [
                "modelbandit", "--write-secrets", "--working-dir", self.root]), \
                mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                mock.patch("modelbandit.fetch_json",
                           side_effect=AssertionError("no network in writer")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code

    def test_writer_reports_rule_counts_without_echoing_values(self):
        phrase = "rare-client-codename-7f2a"
        pattern = r"private-case-\d{4}"
        payload = json.dumps({"phrases": [phrase], "patterns": [pattern],
                              "identifying": False, "commit": True})

        out, _, code = self.run_writer(payload)

        self.assertEqual(code, 0)
        self.assertIn("added 1 phrase, 1 pattern", out)
        self.assertNotIn(phrase, out)
        self.assertNotIn(pattern, out)

    def test_writer_invalid_regex_reports_index_without_echoing_value(self):
        invalid = "client-regex-([secret"
        payload = json.dumps({"phrases": [], "patterns": ["ok", invalid],
                              "identifying": False, "commit": True})

        _, _, code = self.run_writer(payload)

        self.assertIn("pattern #2 is not a valid regex", str(code))
        self.assertNotIn(invalid, str(code))

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
        rules = modelbandit.load_secrets_rules(
            os.path.join(self.root, "modelbandit.secrets.json"))
        self.assertEqual(rules["phrases"],
                         ["existing client name", "new client name"])
        self.assertEqual(rules["patterns"],
                         [r"old-key-\d+", r"new-key-\d+"])
        self.assertIn("added 1 phrase, 1 pattern", first)
        self.assertIn("already present 2 phrases, 2 patterns", second)

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
        self.assertEqual(lines, ["cache", "modelbandit.secrets.json"])
        self.assertIn("gitignore: appended modelbandit.secrets.json", first)
        self.assertIn("gitignore: already contains modelbandit.secrets.json", second)

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
            self.assertIn("modelbandit.secrets.json", f.read().splitlines())
        self.assertIn("gitignore: appended", out)

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_writer_refuses_to_gitignore_a_tracked_rules_file(self):
        subprocess.run(["git", "-C", self.root, "init", "-q"], check=True,
                       capture_output=True)
        self.write_rules({"phrases": ["old phrase"]})
        subprocess.run(["git", "-C", self.root, "add", "modelbandit.secrets.json"],
                       check=True, capture_output=True)
        rules_path = os.path.join(self.root, "modelbandit.secrets.json")
        with open(rules_path, encoding="utf-8") as f:
            original = f.read()
        payload = json.dumps({"phrases": ["new phrase"], "patterns": [],
                              "identifying": True, "commit": True})

        _, _, code = self.run_writer(payload)

        self.assertIn("git rm --cached modelbandit.secrets.json", str(code))
        with open(rules_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), original)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".gitignore")))

    def test_invalid_json_and_rule_shapes_fail_loudly(self):
        cases = (("{", "invalid JSON"),
                 (json.dumps({"phrases": "not a list", "patterns": [],
                              "identifying": False, "commit": True}), "phrases"),
                 (json.dumps({"phrases": [], "patterns": ["("],
                              "identifying": False, "commit": True}), "pattern #1"))
        for payload, problem in cases:
            with self.subTest(problem=problem):
                _, _, code = self.run_writer(payload)
                self.assertIn(problem, str(code))
                self.assertFalse(os.path.exists(
                    os.path.join(self.root, "modelbandit.secrets.json")))


class SecretsEndToEndTests(TempDirMixin):
    """The whole mechanism with deterministic machine facts and real files/git."""

    def run_check(self, working_dir, material, *, machine=None, outside_files=()):
        out, err, code = io.StringIO(), io.StringIO(), None
        argv = ["modelbandit", "--check-secrets", "--working-dir", working_dir]
        for path in outside_files:
            argv.extend(("--outside-file", path))
        config_home = os.path.join(self.root, "config")
        os.makedirs(os.path.join(config_home, "modelbandit"), exist_ok=True)
        with open(os.path.join(config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"zones": [], "default": "open"}, f)
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sys, "stdin", io.StringIO(material)), \
                mock.patch("modelbandit.machine_facts",
                           return_value=machine or {"identifiers": []}), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
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

    def test_injected_machine_identifier_trips_end_to_end(self):
        out, code = self.run_check(
            self.root, f"Deploy to {HOST} tonight.",
            machine={"hostname": HOST, "identifiers": [HOST]})
        self.assertEqual(code, 1, out)
        self.assertIn("rule: hostname", out)

    def test_material_matching_nothing_is_safe_with_empty_machine_facts(self):
        out, code = self.run_check(self.root, "Summarize the public API docs.")
        self.assertEqual(code, 0, out)
        self.assertIn("secrets gate: safe", out)


if __name__ == "__main__":
    unittest.main()

