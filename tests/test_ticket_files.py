"""Deal-time material assessment and the held lane (spec #75, ticket #86).

The run names its ticket files; the script reads them itself at deal time
and applies the built-in credential, identifier, machine-fact and
gitignored-content rules to each one — scoped to that file's own directory
through the shared material-assessment entry point, with no project rules
file anywhere. The verdict splits the batch at collection: ordinary tickets
deal across the eligible pool; tripped tickets print `held: <ids>
(sensitive)` and are excluded from this invocation's deal — never silently
dropped, never escalated to a cloud route. The held lane is dealt by its
own follow-up invocation, local-only, preserving the deal's seed math: one
invocation still deals one shape.

The seam is the CLI output contract: the printed held line, the dealt
batch, and the exit statuses (spec Testing Decisions). Ticket ids are the
positions of the named files — id 1..N in `--ticket-files` order.
"""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cli  # noqa: E402

QWEN = "lmstudio/qwen/qwen3-coder-30b"
LOCAL_FREE = {"lmstudio/qwen": {
    "context_length": 262_144, "exposure": "local",
    "summary_ref": "deepseek/deepseek-v4-pro"}}

# A ticket whose material trips a built-in credential rule — a password
# assignment — and one that passes it.
SECRET_TICKET = "Deploy checklist — database password: correct-horse-battery\n"
CLEAN_TICKET = "Draft the sprint's release notes: what shipped, what broke.\n"


class TicketFilesCliMixin:
    """The shared CLI lifecycle (test_cli.CliTests): injected fetchers,
    patched local probe/cache/env, captured stdout/stderr, plus this
    suite's temp-dir ticket fixtures."""

    def setUp(self):
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)

    def run_cli(self, *argv, **kw):
        return self.cli.run_cli(*argv, **kw)

    def ticket_files(self, *contents):
        """Temp-dir ticket files under this suite's scratch root, one per
        ticket, named in order — the ids the readout reports."""
        paths = []
        for index, content in enumerate(contents, 1):
            path = os.path.join(self.cli._tmp.name, f"ticket-{index}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            paths.append(path)
        return paths

    @staticmethod
    def dealt_tickets(out):
        """The deal table's total: the batch this invocation dealt."""
        block = out[out.index("deal (seed"):out.index("projection at")]
        return sum(int(line.split("|")[7].strip())
                   for line in block.splitlines()
                   if line.startswith("| ")
                   and line.split("|")[1].strip().isdigit())

    def local_policy(self):
        """This fixture machine's policy carrying one harness-listed local
        candidate (no roster: the band gate has nothing to judge)."""
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = dict(LOCAL_FREE)
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)


class SplitDealTests(TicketFilesCliMixin, unittest.TestCase):
    """The named-AC test: temp-dir ticket files drive the split deal and
    the held line — ordinary tickets deal, tripped ones are reported held."""

    def test_ticket_files_split_the_batch_at_collection_and_report_held(self):
        clean, secret = self.ticket_files(CLEAN_TICKET, SECRET_TICKET)

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "split",
            "--ticket-files", clean, "--ticket-files", secret)

        self.assertIsNone(code)
        # The tripped ticket is named by its collection id, held for the
        # local-only follow-up run — never silently dropped.
        self.assertIn("held: 2 (sensitive)", out)
        self.assertNotIn("held: 1", out)
        # The ordinary ticket alone dealt across the eligible pool: the
        # split was decided at collection, before the draw.
        self.assertEqual(self.dealt_tickets(out), 1)
        self.assertIn("projection at 1 ticket(s):", out)

    def test_the_budget_json_twin_carries_the_held_ids(self):
        # The machine-readable half of the held report: the budgeted run's
        # verdict object carries the same ids the readout prints.
        clean, secret = self.ticket_files(CLEAN_TICKET, SECRET_TICKET)

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "split",
            "--ticket-files", clean, "--ticket-files", secret,
            "--budget", "100", "--json")

        self.assertIn(code, (None, 0))
        self.assertIn("held: 2 (sensitive)", out)
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "budget")
        self.assertEqual(payload["held"], [2])

    def test_the_substitution_rederives_the_split_deal(self):
        # The substitution re-derives this seeded deal from the same flags —
        # the split included — so its record speaks the dealt batch, and the
        # held report still names the collection's split.
        clean, secret = self.ticket_files(CLEAN_TICKET, SECRET_TICKET)
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "split",
            "--ticket-files", clean, "--ticket-files", secret)
        self.assertIsNone(code)
        block = out[out.index("deal (seed"):out.index("projection at")]
        dealt = next(line for line in block.splitlines()
                     if line.startswith("| ")
                     and line.split("|")[7].strip().isdigit()
                     and int(line.split("|")[7].strip()) > 0)
        mid = dealt.split("|")[2].strip()

        sub_out, _, sub_code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "split",
            "--ticket-files", clean, "--ticket-files", secret,
            "--substitute", mid)

        self.assertEqual(sub_code, 0)
        self.assertIn("held: 2 (sensitive)", sub_out)
        self.assertIn(f"substitution: {mid} -> ", sub_out)

    def test_a_batch_that_all_trips_holds_every_ticket_and_deals_none(self):
        # Nothing passed: the whole batch is held for its follow-up run and
        # this invocation deals no tickets — the report, not a crash.
        secret1, secret2 = self.ticket_files(SECRET_TICKET, SECRET_TICKET)

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "all-held",
            "--ticket-files", secret1, "--ticket-files", secret2)

        self.assertIsNone(code)
        self.assertIn("held: 1, 2 (sensitive)", out)
        self.assertIn("projection at 0 ticket(s):", out)


class HeldLaneTests(TicketFilesCliMixin, unittest.TestCase):
    """The follow-up invocation: the held files re-named under the
    Sensitive shape deal local-only — one invocation, one shape."""

    def test_the_held_lane_reruns_local_only_with_the_same_seed_derivation(self):
        secret1, secret2 = self.ticket_files(SECRET_TICKET, SECRET_TICKET)
        self.local_policy()
        listing = dict(local_listing={QWEN},
                       local_models={QWEN: {"id": QWEN,
                                            "context_length": 262_144}})

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "held-lane",
            "--ticket-files", secret1, "--ticket-files", secret2,
            "--sensitive", **listing)

        self.assertIsNone(code)
        # This run IS the held lane: the trips deal under the local-only
        # fence instead of holding — nothing is reported held.
        self.assertNotIn("held:", out)
        # Both tickets dealt, every one of them to the local candidate:
        # no held ticket is ever dealt to a non-local route.
        self.assertEqual(self.dealt_tickets(out), 2)
        block = out[out.index("deal (seed"):out.index("projection at")]
        self.assertIn(f"| {QWEN} |", block)
        self.assertNotIn("openrouter/", block)
        # The same seed derivation the deal always had: identical flags
        # re-derive the identical held-lane deal.
        out2, _, _, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "held-lane",
            "--ticket-files", secret1, "--ticket-files", secret2,
            "--sensitive", **listing)
        self.assertEqual(out[out.index("deal (seed"):],
                         out2[out2.index("deal (seed"):])

    def test_held_tickets_with_no_eligible_local_candidate_stop_through_printer(self):
        # The real decision the held lane can face: no local candidate can
        # serve the held tickets, so the run stops through the one printer
        # with the locked blocked line — exit 0, like every verdict.
        secret, = self.ticket_files(SECRET_TICKET)

        out, err, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "held-lane",
            "--ticket-files", secret, "--sensitive")

        self.assertEqual(code, 0)
        self.assertIn("blocked: no eligible local candidate", out)
        self.assertNotIn("deal (seed", out)
        self.assertNotIn("no candidate admitted", err)


class ScopedRulesTests(TicketFilesCliMixin, unittest.TestCase):
    """The gitignored-content rule reads the ticket file's own tree —
    scoped to that file's directory, never the run's working folder."""

    def git_env(self):
        config = os.path.join(self.cli._tmp.name, "git-config")
        with open(config, "w", encoding="utf-8") as f:
            f.write("")
        return dict(os.environ,
                    GIT_CONFIG_GLOBAL=config, GIT_CONFIG_SYSTEM=config,
                    GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                    GIT_AUTHOR_NAME="Fixture",
                    GIT_AUTHOR_EMAIL="fixture@example.invalid",
                    GIT_COMMITTER_NAME="Fixture",
                    GIT_COMMITTER_EMAIL="fixture@example.invalid")

    def test_a_ticket_quoting_its_own_trees_gitignored_content_is_held(self):
        root = os.path.join(self.cli._tmp.name, "repo")
        os.makedirs(root)
        env = self.git_env()

        def git(*args):
            completed = subprocess.run(["git", "-C", root, *args], env=env,
                                       capture_output=True, text=True,
                                       encoding="utf-8", errors="replace")
            self.assertEqual(completed.returncode, 0,
                             f"git {args} failed: {completed.stderr}")

        git("init", "-q")
        with open(os.path.join(root, ".gitignore"), "w",
                  encoding="utf-8") as f:
            f.write("ignored-notes.txt\n")
        waivered = "the waiver passphrase is quarry-lantern-mica\n"
        with open(os.path.join(root, "ignored-notes.txt"), "w",
                  encoding="utf-8") as f:
            f.write(waivered)
        git("add", ".")
        git("commit", "-qm", "fixture")
        # The ticket quotes the gitignored line whole — its own tree's
        # maintained list of what must not leave it.
        waivered_ticket = os.path.join(root, "ticket-waiver.txt")
        with open(waivered_ticket, "w", encoding="utf-8") as f:
            f.write("Quote the waiver line whole: "
                    "the waiver passphrase is quarry-lantern-mica\n")
        clean_ticket = os.path.join(root, "ticket-clean.txt")
        with open(clean_ticket, "w", encoding="utf-8") as f:
            f.write(CLEAN_TICKET)

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "scoped",
            "--ticket-files", waivered_ticket, "--ticket-files", clean_ticket)

        self.assertIsNone(code)
        self.assertIn("held: 1 (sensitive)", out)
        self.assertEqual(self.dealt_tickets(out), 1)

    def test_without_a_tree_the_gitignored_rule_costs_the_run_nothing(self):
        # The same quoted line in a plain temp directory — no git, no
        # gitignored facts — deals: a missing tree costs a rule, never a
        # crash and never a false hold.
        clean, quoted = self.ticket_files(
            CLEAN_TICKET, "the waiver passphrase is quarry-lantern-mica\n")

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--seed", "no-tree",
            "--ticket-files", clean, "--ticket-files", quoted)

        self.assertIsNone(code)
        self.assertNotIn("held:", out)
        self.assertEqual(self.dealt_tickets(out), 2)


class UsageGuardTests(TicketFilesCliMixin, unittest.TestCase):
    """A flag silently ignored is a rule the user believes in: the
    ticket-file flag is refused where it would say nothing."""

    def test_ticket_files_is_read_only_by_deal(self):
        clean, = self.ticket_files(CLEAN_TICKET)

        _, err, code, _ = self.run_cli("--domain", "writing",
                                       "--ticket-files", clean)

        self.assertEqual(code, 2)
        self.assertIn("--ticket-files is read only by --deal", err)

    def test_tickets_is_refused_when_the_files_name_the_batch(self):
        clean, secret = self.ticket_files(CLEAN_TICKET, SECRET_TICKET)

        _, err, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--tickets", "3",
            "--ticket-files", clean, "--ticket-files", secret)

        self.assertEqual(code, 2)
        self.assertIn("--tickets is read only without --ticket-files", err)

    def test_a_named_path_that_is_not_a_ticket_file_is_a_usage_error(self):
        absent = os.path.join(self.cli._tmp.name, "absent.txt")

        _, err, code, calls = self.run_cli(
            "--domain", "writing", "--deal", "--ticket-files", absent)

        self.assertEqual(code, 2)
        self.assertIn(f"--ticket-files: not a ticket file: {absent}", err)
        # Named before anything is fetched: the batch is collected first.
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
