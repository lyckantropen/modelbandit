"""Spares and substitution (issue #71): every dealt row names its Spare, and
a substitution is an invocation, not stored state — the same seeded deal
re-derived, the takeover and reason recorded, the fence restated.

The seam is the deal/pick output contract: the printed readout, its `--json`
twin, and the substitution record. Seeded draws are deterministic, so exact
assertions on rows, spares and report texts are the point (spec Testing
Decisions).
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cli  # noqa: E402
import modelbandit  # noqa: E402


class SpareCliMixin:
    """The shared CLI lifecycle (test_cli.CliTests): injected fetchers,
    patched local probe/cache/env, captured stdout/stderr. The scenario
    fixtures below stay this suite's own."""

    def setUp(self):
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)

    def run_cli(self, *argv, **kw):
        return self.cli.run_cli(*argv, **kw)

    def deal_rows(self, out):
        """The deal table's data rows as split cells: [0]/[-1] are the
        pipes, cell 1 is `#`, cell 7 tickets, cell 8 the spare (issue #71)."""
        deal = out[out.index("deal (seed"):out.index("projection at")]
        return [ln.split("|") for ln in deal.splitlines()
                if ln.startswith("| ") and ln.split("|")[1].strip().isdigit()]

    def plain_deal(self, *argv, **kw):
        """The plain writing pool — 0813 (score 0.06), pro (0.025), flash
        (0.005) — one ticket, seed 'a3' deals it to 0813."""
        base = ("--domain", "writing", "--tickets", "1", "--deal",
                "--seed", "a3")
        return self.run_cli(*base, *argv, **kw)


class SpareDealTests(SpareCliMixin, unittest.TestCase):

    def test_every_dealt_row_names_exactly_one_spare(self):
        # The two rows that missed the draw are both no-load, so Score
        # decides: the Spare is pro, the higher-Score miss. Every dealt row
        # names exactly one Spare; a row that missed the draw names none
        # (`-`).
        out, _, code, _ = self.plain_deal()

        self.assertIsNone(code)
        rows = self.deal_rows(out)
        dealt = [cells for cells in rows if int(cells[7].strip())]
        missed = [cells for cells in rows if not int(cells[7].strip())]
        self.assertEqual(len(dealt), 1)
        for cells in dealt:
            spare = cells[8].strip()
            self.assertNotIn(spare, ("-", "none", ""))
            self.assertNotEqual(spare, cells[2].strip())   # never itself
            # The named Spare missed the draw: its own row shows 0 tickets.
            spare_row = next(r for r in rows if r[2].strip() == spare)
            self.assertEqual(spare_row[7].strip(), "0")
        for cells in missed:
            self.assertEqual(cells[8].strip(), "-")
        self.assertEqual(dealt[0][8].strip(),
                         "openrouter/deepseek/deepseek-v4-pro")

    def test_the_budget_json_twin_carries_the_spares(self):
        # The machine-readable half: a dealt budgeted run's verdict object
        # carries the same Spare the readout's column shows, keyed by the
        # provider-qualified ids a model config dispatches.
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "1", "--deal", "--seed", "a3",
            "--budget", "100", "--json")

        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "budget")
        self.assertEqual(
            payload["spares"],
            {"openrouter/deepseek/deepseek-v4-pro-0813":
             "openrouter/deepseek/deepseek-v4-pro"})


class SparePreferenceTests(SpareCliMixin, unittest.TestCase):
    """AC2: a non-sensitive Spare prefers a no-model-load candidate (Score
    breaking the ties inside that class); a Sensitive Spare is drawn from
    local candidates only."""

    def local_policy(self, prose_hint=False):
        """The fixture machine's policy with one harness-listed local
        candidate; `prose_hint` also favors pro in writing so the pool holds
        four rows: 0813 (0.06), local (0.0425), pro (0.025), flash (0.005)."""
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        if prose_hint:
            fit = pol["hints"]["deepseek/deepseek-v4-pro"]["fit"]
            fit["writing"] = "favor"
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)
        return "lmstudio/qwen/qwen3-coder-30b"

    def test_a_non_sensitive_spare_prefers_a_no_load_candidate_score_breaking_ties(self):
        # Seed 'b1' deals the one ticket to 0813; the local row (0.0425)
        # missed the draw and outscores both cloud misses — but it is
        # load-required (a local swap is minutes), so the Spare is the
        # no-load pro (0.025), and pro itself outranks flash (0.005) by
        # Score inside the no-load class.
        mid = self.local_policy(prose_hint=True)
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "1", "--deal", "--seed", "b1",
            local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        rows = self.deal_rows(out)
        dealt = [cells for cells in rows if int(cells[7].strip())]
        self.assertEqual(len(dealt), 1)
        self.assertEqual(dealt[0][2].strip(),
                         "openrouter/deepseek/deepseek-v4-pro-0813")
        self.assertEqual(dealt[0][8].strip(),
                         "openrouter/deepseek/deepseek-v4-pro")
        local_row = next(r for r in rows if mid in r[2])
        pro_row = next(r for r in rows if "deepseek-v4-pro |" in r[2] + "|")
        # The preference outranks Score: the local miss scores higher...
        self.assertGreater(float(local_row[4]), float(pro_row[4]))
        # ...and Score still breaks the ties inside the no-load class.
        flash_row = next(r for r in rows if "deepseek-v4-flash" in r[2])
        self.assertGreater(float(pro_row[4]), float(flash_row[4]))

    def test_a_sensitive_spare_is_drawn_from_local_candidates_only(self):
        # ADR 0008 at the Spare seam: the sensitive pool holds the two
        # harness-listed locals alone (seed 'c1' deals the ticket to qwen),
        # so the Spare is the other local — no cloud id can even appear in
        # the spare column, whatever it would score.
        qwen = "lmstudio/qwen/qwen3-coder-30b"
        zai = "lmstudio/zai-org/glm-4.7-flash"
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = {
            "lmstudio/qwen": {"context_length": 262_144, "exposure": "local",
                              "summary_ref": "deepseek/deepseek-v4-pro"},
            "lmstudio/zai": {"context_length": 262_144, "exposure": "local",
                             "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)
        models = {m: {"id": m, "context_length": 262_144}
                  for m in (qwen, zai)}

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "1", "--deal",
            "--seed", "c1", local_listing={qwen, zai}, local_models=models)

        self.assertIsNone(code)
        rows = self.deal_rows(out)
        dealt = [cells for cells in rows if int(cells[7].strip())]
        self.assertEqual(len(dealt), 1)
        self.assertEqual(dealt[0][2].strip(), qwen)
        self.assertEqual(dealt[0][8].strip(), zai)
        for cells in rows:
            if cells[8].strip() not in ("-", "none"):
                self.assertTrue(cells[8].strip().startswith("lmstudio/"))

    def test_a_spare_falls_back_to_a_load_required_candidate_before_failing(self):
        # The pool here is one cloud row and the local; seed 'e1' deals the
        # ticket to the cloud row, leaving only the load-required local as a
        # miss. Non-sensitive prefers no-load, but a load-required Spare is
        # still named — the run only fails when no candidate is left at all.
        mid = self.local_policy()
        world = test_cli.build_world()
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 0.1,
            "models": [{"id": "deepseek/deepseek-v4-pro-20260813",
                        "tag_usage_share": 0.5}]}]

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "1", "--deal", "--seed", "e1",
            world=world, local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertIsNone(code)
        rows = self.deal_rows(out)
        dealt = [cells for cells in rows if int(cells[7].strip())]
        self.assertEqual(len(dealt), 1)
        self.assertEqual(dealt[0][8].strip(), mid)
        self.assertNotIn("spare: no eligible", out)


class SubstitutionTests(SpareCliMixin, unittest.TestCase):
    """AC3/AC4/AC7: a substitution is an invocation in the deal's shape —
    the same seed re-derives the same deal, the reason class decides whether
    the takeover may happen, and the record (takeover + reason + fence)
    replaces the deal readout's tail — exit 0 either way."""

    DEAD = "openrouter/deepseek/deepseek-v4-pro-0813"   # seed 'a3' dealt it
    SPARE = "openrouter/deepseek/deepseek-v4-pro"        # its named Spare

    def test_a_mechanical_substitution_records_the_takeover_and_the_reason(self):
        out, err, code, _ = self.plain_deal(
            "--substitute", self.DEAD, "--reason", "mechanical")

        self.assertEqual(code, 0)
        self.assertIn(f"substitution: {self.DEAD} -> {self.SPARE}", out)
        self.assertIn("reason: mechanical — unreachable, out of quota or "
                      "allowance, unloadable", out)
        self.assertIn("takeover: openrouter/deepseek/deepseek-v4-pro takes "
                      "the ticket over whole (1 ticket)", out)
        self.assertIn("fence: band", out)
        # The record is this invocation's answer: no deal readout, no
        # projection — one question, one output.
        self.assertNotIn("deal (seed", out)
        self.assertNotIn("projection at", out)
        # No substitution trouble on the usage channel (the fixture's own
        # board/quota warnings aside).
        self.assertNotIn("substitute", err)

    def test_the_default_reason_is_mechanical(self):
        out, _, code, _ = self.plain_deal("--substitute", self.DEAD)

        self.assertEqual(code, 0)
        self.assertIn(f"substitution: {self.DEAD} -> {self.SPARE}", out)
        self.assertIn("reason: mechanical", out)

    def test_an_explicit_dead_attempt_report_substitutes_for_a_quality_failure(self):
        out, _, code, _ = self.plain_deal(
            "--substitute", self.DEAD, "--reason", "dead-attempt")

        self.assertEqual(code, 0)
        self.assertIn(f"substitution: {self.DEAD} -> {self.SPARE}", out)
        self.assertIn("reason: dead-attempt — the harness's explicit "
                      "failed-attempt report", out)
        self.assertIn("takeover:", out)

    def test_a_bare_quality_reason_is_refused_without_a_takeover(self):
        # Quality never reshuffles work mid-run: `--reason quality` alone is
        # refused — no takeover record, exit 0, the refusal says why.
        out, _, code, _ = self.plain_deal(
            "--substitute", self.DEAD, "--reason", "quality")

        self.assertEqual(code, 0)
        self.assertIn("substitution refused: quality failure substitutes "
                      "only on the harness's explicit dead-attempt report",
                      out)
        self.assertNotIn("takeover:", out)
        self.assertNotIn(f"substitution: {self.DEAD} ->", out)

    def test_the_refusal_answers_json_too(self):
        out, _, code, _ = self.plain_deal(
            "--substitute", self.DEAD, "--reason", "quality", "--json")

        self.assertEqual(code, 0)
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "substitution")
        self.assertEqual(payload["verdict"], "refused")
        self.assertIn("dead-attempt report", payload["reason"])

    def test_the_substitution_json_record_carries_the_takeover(self):
        out, _, code, _ = self.plain_deal(
            "--substitute", self.DEAD, "--budget", "100", "--json")

        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "substitution")
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(payload["from"], self.DEAD)
        self.assertEqual(payload["to"], self.SPARE)
        self.assertEqual(payload["reason"], "mechanical")
        self.assertEqual(payload["reason_class"], "automatic")
        self.assertEqual(payload["tickets"], 1)
        self.assertIs(payload["sensitive"], False)

    def test_substitute_and_reason_misuse_is_a_usage_error(self):
        out, err, code, _ = self.run_cli(
            "--domain", "writing", "--substitute", self.DEAD)
        self.assertEqual(code, 2)
        self.assertIn("--substitute is read only by --deal", err)

        out, err, code, _ = self.run_cli(
            "--domain", "writing", "--deal", "--reason", "mechanical")
        self.assertEqual(code, 2)
        self.assertIn("--reason is read only by --substitute", err)

        out, err, code, _ = self.plain_deal(
            "--substitute", "openrouter/not-in-this-deal")
        self.assertEqual(code, 2)
        self.assertIn("is not part of this deal", err)
        self.assertNotIn("takeover:", out)


class SubstitutionFenceTests(SpareCliMixin, unittest.TestCase):
    """AC5: a spare inherits the ticket's fence — band ceiling, Sensitive
    local-only, the non-leak note — so a substitution can never loosen the
    gate (AC7's output-seam pin)."""

    QWEN = "lmstudio/qwen/qwen3-coder-30b"
    ZAI = "lmstudio/zai-org/glm-4.7-flash"

    def sensitive_two_local_setup(self):
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = {
            "lmstudio/qwen": {"context_length": 262_144, "exposure": "local",
                              "summary_ref": "deepseek/deepseek-v4-pro"},
            "lmstudio/zai": {"context_length": 262_144, "exposure": "local",
                             "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)
        self.cli.roster_file({
            self.QWEN: self.cli.band_entry(
                ["writing"], "Local writer on this machine."),
            self.ZAI: self.cli.band_entry(
                ["writing"], "Local writer on this machine.")})
        return {m: {"id": m, "context_length": 262_144}
                for m in (self.QWEN, self.ZAI)}

    def test_a_sensitive_substitution_restates_the_whole_fence(self):
        # Seed 'c1' dealt the ticket to qwen; its Spare is the other local.
        # The record carries the takeover, the Spare's own band (it passed
        # the same band gate this invocation re-ran), the local-only line
        # and the standing non-leak note — and names no cloud id anywhere.
        models = self.sensitive_two_local_setup()

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "1", "--deal",
            "--seed", "c1", "--substitute", self.QWEN,
            local_listing={self.QWEN, self.ZAI}, local_models=models)

        self.assertEqual(code, 0)
        self.assertIn(f"substitution: {self.QWEN} -> {self.ZAI}", out)
        self.assertIn(f"fence: band — {self.ZAI}: domains writing; "
                      "difficulty ceiling measured", out)
        self.assertIn("fence: sensitive — local-only (ADR 0008)", out)
        self.assertIn(modelbandit.NON_LEAK_NOTE, out)
        self.assertIn("takeover:", out)
        # The taker is local, whatever a cloud route would have offered:
        # substitution never loosens the gate.
        self.assertNotIn("openrouter/", out.split("substitution:")[1])

    def test_the_sensitive_substitution_json_carries_the_fence(self):
        models = self.sensitive_two_local_setup()

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "1", "--deal",
            "--seed", "c1", "--substitute", self.QWEN, "--json",
            local_listing={self.QWEN, self.ZAI}, local_models=models)

        self.assertEqual(code, 0)
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(payload["to"], self.ZAI)
        self.assertIs(payload["sensitive"], True)
        self.assertEqual(payload["band"]["domains"], ["writing"])
        self.assertEqual(payload["non_leak_note"], modelbandit.NON_LEAK_NOTE)


class SpareExhaustionTests(SpareCliMixin, unittest.TestCase):
    """AC6: exhaustion stops and reports — terminal for a Sensitive ticket
    (never re-gated), a non-sensitive one only after the no-load failover
    preference — and blocked outcomes exit 0 (AC7)."""

    QWEN = "lmstudio/qwen/qwen3-coder-30b"

    def one_local_sensitive_setup(self):
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)
        return {self.QWEN: {"id": self.QWEN, "context_length": 262_144}}

    def test_the_deal_readout_says_so_when_no_spare_is_left(self):
        # Deal-time exhaustion (the one admitted local took all 12 tickets):
        # the deal still prints — `none` in the spare column plus the
        # fence's own sentence where a Spare would be named.
        models = self.one_local_sensitive_setup()

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "12", "--deal",
            "--seed", "exhaust", local_listing={self.QWEN},
            local_models=models)

        self.assertIsNone(code)
        rows = self.deal_rows(out)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][7].strip(), "12")
        self.assertEqual(rows[0][8].strip(), "none")
        self.assertIn("spare: no eligible local candidate missed the draw for "
                      f"{self.QWEN} (local-only fence holds; never re-gated)",
                      out)

    def test_exhaustion_on_a_sensitive_ticket_reports_blocked_and_exits_zero(self):
        # The same deal substituted: nothing may take over, so the
        # substitution answers `blocked:` — terminal, exit 0, never
        # re-gated onto a cloud route.
        models = self.one_local_sensitive_setup()

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "12", "--deal",
            "--seed", "exhaust", "--substitute", self.QWEN,
            local_listing={self.QWEN}, local_models=models)

        self.assertEqual(code, 0)
        self.assertIn("blocked: no eligible local candidate missed the draw "
                      "for " + self.QWEN + " (local-only fence holds; "
                      "never re-gated)", out)
        self.assertNotIn("takeover:", out)

    def test_the_blocked_substitution_answers_json_too(self):
        models = self.one_local_sensitive_setup()

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "12", "--deal",
            "--seed", "exhaust", "--substitute", self.QWEN, "--json",
            local_listing={self.QWEN}, local_models=models)

        self.assertEqual(code, 0)
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "substitution")
        self.assertEqual(payload["verdict"], "blocked")
        self.assertIsNone(payload["to"])
        self.assertIn("never re-gated", payload["reason"])

    def test_a_non_sensitive_exhaustion_fails_only_after_the_no_load_preference(self):
        # Both pool rows drew a ticket (seed 'x2'), so no candidate missed
        # the draw — the non-sensitive rule states its preference in the
        # report and fails there, exit 0 like every other verdict.
        mid = self.QWEN
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = {"lmstudio/qwen": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "deepseek/deepseek-v4-pro"}}
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)
        world = test_cli.build_world()
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 0.1,
            "models": [{"id": "deepseek/deepseek-v4-pro-20260813",
                        "tag_usage_share": 0.5}]}]

        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "2", "--deal", "--seed", "x2",
            "--substitute", "openrouter/deepseek/deepseek-v4-pro-0813",
            world=world, local_listing={mid},
            local_models={mid: {"id": mid, "context_length": 262_144}})

        self.assertEqual(code, 0)
        self.assertIn("blocked: no eligible candidate missed the draw for "
                      "openrouter/deepseek/deepseek-v4-pro-0813 (no-load "
                      "failover preferred first)", out)
        self.assertNotIn("takeover:", out)


class SpareFenceUnitTests(unittest.TestCase):
    """The fence stated at the Spare seam itself: deal_spares never re-gates
    (the CLI fixtures above carry admission's verdict; this pins the rule
    the selection would break if it ever trusted it)."""

    def rows(self):
        return [
            {"mid": "openrouter/cloud-heavy", "tickets": 1, "base": 9.0},
            {"mid": "lmstudio/local-light", "tickets": 0, "base": 1.0},
            {"mid": "lmstudio/local-mid", "tickets": 0, "base": 5.0},
        ]

    def test_sensitive_never_names_a_non_local_spare_even_at_the_top_score(self):
        spares = modelbandit.deal_spares(
            self.rows(), local={"lmstudio/local-light", "lmstudio/local-mid"},
            sensitive=True)
        self.assertEqual(spares,
                         {"openrouter/cloud-heavy": "lmstudio/local-mid"})

    def test_sensitive_with_no_local_miss_is_exhausted_not_re_gated(self):
        # The only candidate that missed the draw is a cloud row: a
        # Sensitive Spare must not reach for it — the deal reports exhaustion
        # instead of re-gating (the non-sensitive rule would name it).
        rows = [{"mid": "openrouter/cloud-heavy", "tickets": 0, "base": 9.0},
                {"mid": "lmstudio/local-only", "tickets": 1, "base": 1.0}]
        spares = modelbandit.deal_spares(
            rows, local={"lmstudio/local-only"}, sensitive=True)
        self.assertEqual(spares, {"lmstudio/local-only": None})

    def test_non_sensitive_orders_no_load_first_then_score(self):
        rows = [{"mid": "openrouter/a-cloud", "tickets": 1, "base": 9.0},
                {"mid": "lmstudio/hot", "tickets": 0, "base": 8.0},
                {"mid": "openrouter/b-cloud", "tickets": 0, "base": 2.0}]
        spares = modelbandit.deal_spares(rows,
                                         local={"lmstudio/hot"})
        self.assertEqual(spares, {"openrouter/a-cloud": "openrouter/b-cloud"})


if __name__ == "__main__":
    unittest.main()
