"""The single local lane (issue #72): the deal states which tickets are
mutually exclusive — one strict lane, no two local runs concurrent — as
the local-dealt ticket ids ordered grouped-by-model, in the printed
readout and the budget `--json`, and substitution moves lane membership
with the served model while the published chain stays.

The seam is the deal/pick output contract: the printed readout and its
`--json` twin (spec Testing Decisions). Seeds are deterministic, so exact
assertions on lane membership, ordering and the ticket map are the point.

Ticket-id convention: id 1..N in the deal's assignment order — ticket
i+1 is the draw keyed `seed::i`, plan_deal's own vocabulary. The exact
expected literals below are the seeded draws' frozen ground truth (each
one cross-checked against the deal table's ticket counts).
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

QWEN = "lmstudio/qwen/qwen3-coder-30b"
ZAI = "lmstudio/zai-org/glm-4.7-flash"
GLM = "lmstudio/glm/glm-4.6"
CLOUD_A = "openrouter/deepseek/deepseek-v4-pro-0813"   # the 0813 serving
CLOUD_B = "openrouter/deepseek/deepseek-v4-pro"
LOCAL_FREE = {
    "lmstudio/qwen": {"context_length": 262_144, "exposure": "local",
                      "summary_ref": "deepseek/deepseek-v4-pro"},
    "lmstudio/zai": {"context_length": 262_144, "exposure": "local",
                     "summary_ref": "deepseek/deepseek-v4-pro"},
    "lmstudio/glm": {"context_length": 262_144, "exposure": "local",
                     "summary_ref": "deepseek/deepseek-v4-pro"},
}


class LaneCliMixin:
    """The shared CLI lifecycle (test_cli.CliTests): injected fetchers,
    patched local probe/cache/env, captured stdout/stderr, plus this
    suite's fixed roster/listing/shape fixtures."""

    def setUp(self):
        self.cli = test_cli.CliTests()
        self.cli.setUp()
        self.addCleanup(self.cli.tearDown)

    def run_cli(self, *argv, **kw):
        return self.cli.run_cli(*argv, **kw)

    def lane_lines(self, out):
        """The readout's lane block: every line the lane speaks through."""
        return [ln for ln in out.splitlines() if ln.startswith("lane: ")]

    def ticket_id_lines(self, out):
        """The readout's ticket map: `ticket ids: <ids> -> <model>`."""
        return [ln for ln in out.splitlines()
                if ln.startswith("ticket ids: ")]

    # --- fixed fixtures: roster + listing + shape + seed ---------------

    def write_policy(self, free_models):
        pol = json.loads(json.dumps(test_cli.POLICY))
        pol["free_models"] = free_models
        # Both fixture locals sit below the curated top-2 cut; the lane
        # fixtures need every declared candidate in the pool.
        pol["affinity"]["eligibility_top_k"] = 6
        with open(self.cli.policy_path, "w", encoding="utf-8") as f:
            json.dump(pol, f)

    def roster(self, *mids):
        self.cli.roster_file({
            mid: self.cli.band_entry(
                ["writing"], "Local writer on this machine.")
            for mid in mids})

    @staticmethod
    def local_models(*mids):
        return {mid: {"id": mid, "context_length": 262_144}
                for mid in mids}

    def one_local_sensitive_deal(self, *argv, **kw):
        """The Sensitive writing deal with one admitted local row: seed
        'exhaust' deals all 12 tickets to qwen, so the lane names the
        whole batch under the one served model."""
        self.write_policy({"lmstudio/qwen": LOCAL_FREE["lmstudio/qwen"]})
        self.roster(QWEN)
        return self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", "12", "--deal",
            "--seed", "exhaust", *argv, local_listing={QWEN},
            local_models=self.local_models(QWEN), **kw)

    def two_local_deal(self, *argv, seed="c1", tickets=6, **kw):
        """The two-local writing deal: seed 'c1' interleaves the draw
        across both locals and the cloud rows — qwen ids 1, 3, 4; zai ids
        2, 5; cloud pro id 6; 0813 and flash missed — so the grouped
        lane re-orders an interleaved batch."""
        self.write_policy({k: LOCAL_FREE[k]
                           for k in ("lmstudio/qwen", "lmstudio/zai")})
        self.roster(QWEN, ZAI)
        return self.run_cli(
            "--domain", "writing", "--tickets", str(tickets), "--deal",
            "--seed", seed, *argv, local_listing={QWEN, ZAI},
            local_models=self.local_models(QWEN, ZAI), **kw)

    def one_cloud_one_local_deal(self, *argv, seed="j4", tickets=3, **kw):
        """The trimmed writing pool — one cloud row and the local alone:
        seed 'j4' deals all 3 tickets to the cloud row, so the local is
        the only miss and the cloud's Spare is local (the join fixture).
        The classification is trimmed so no other cloud row ranks."""
        self.write_policy({"lmstudio/qwen": LOCAL_FREE["lmstudio/qwen"]})
        self.roster(QWEN)
        world = test_cli.build_world()
        world["classifications"]["classifications"] = [{
            "tag": "content_writing", "usage_share": 0.1,
            "models": [{"id": "deepseek/deepseek-v4-pro-20260813",
                        "tag_usage_share": 0.5}]}]
        return self.run_cli(
            "--domain", "writing", "--tickets", str(tickets), "--deal",
            "--seed", seed, *argv, world=world, local_listing={QWEN},
            local_models=self.local_models(QWEN), **kw)

    def three_local_sensitive_deal(self, *argv, seed="a3", tickets=5, **kw):
        """The Sensitive three-local writing deal: only locals admit, and
        seed 'a3' deals glm id 1 plus zai ids 2-5 while qwen misses — the
        local-to-local move fixture (the sole miss is the Spare)."""
        self.write_policy(LOCAL_FREE)
        self.roster(QWEN, ZAI, GLM)
        return self.run_cli(
            "--domain", "writing", "--sensitive", "--tickets", str(tickets),
            "--deal", "--seed", seed, *argv,
            local_listing={QWEN, ZAI, GLM},
            local_models=self.local_models(QWEN, ZAI, GLM), **kw)


class LaneReadoutTests(LaneCliMixin, unittest.TestCase):
    """AC1/AC2/AC4: the printed readout and the budget `--json` carry the
    machine-readable lane — the mutually exclusive local-dealt ticket
    ids, grouped by served model — for fixed roster, listing, shape and
    seed."""

    def test_the_readout_states_the_strict_lane_grouped_by_model(self):
        # One admitted local row holds every draw: the batch's ids 1..12
        # are exactly the lane, grouped under the one served model, and
        # the ticket map before it names the same ids for the model.
        out, _, code, _ = self.one_local_sensitive_deal()

        self.assertIsNone(code)
        self.assertEqual(
            self.ticket_id_lines(out),
            ["ticket ids: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 -> "
             + QWEN])
        self.assertEqual(
            self.lane_lines(out),
            ["lane: strict — one local run at a time (grouped by model)",
             f"lane: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 -> {QWEN}"])

    def test_the_budget_json_twin_carries_the_lane_and_the_ticket_map(self):
        # The machine-readable half of AC1: the dealt budgeted run's
        # verdict object carries the same lane the readout prints, plus
        # the full ticket id -> model map.
        out, _, code, _ = self.one_local_sensitive_deal(
            "--budget", "100", "--json")

        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["mode"], "budget")
        self.assertEqual(
            payload["lane"],
            [{"model": QWEN,
              "tickets": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}])
        self.assertEqual(
            payload["tickets_by_model"],
            {QWEN: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]})

    def test_the_lane_groups_an_interleaved_batch_by_served_model(self):
        # AC2's exact pin: seed 'c1' drew 1=qwen, 2=zai, 3=qwen, 4=qwen,
        # 5=zai, 6=cloud-pro (the table's counts confirm: qwen 3, zai 2,
        # pro 1). The lane regroups the ids so consecutive members share
        # a model — qwen's 1, 3, 4 together, then zai's 2, 5 — and the
        # cloud id stays out of the lane while the ticket map keeps it.
        out, _, code, _ = self.two_local_deal()

        self.assertIsNone(code)
        self.assertEqual(
            self.ticket_id_lines(out),
            [f"ticket ids: 1, 3, 4 -> {QWEN}",
             f"ticket ids: 2, 5 -> {ZAI}",
             f"ticket ids: 6 -> {CLOUD_B}"])
        self.assertEqual(
            self.lane_lines(out),
            ["lane: strict — one local run at a time (grouped by model)",
             f"lane: 1, 3, 4 -> {QWEN}",
             f"lane: 2, 5 -> {ZAI}"])

    def test_the_budget_json_carries_the_two_group_lane_exactly(self):
        out, _, code, _ = self.two_local_deal("--budget", "100", "--json")

        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(
            payload["lane"],
            [{"model": QWEN, "tickets": [1, 3, 4]},
             {"model": ZAI, "tickets": [2, 5]}])
        self.assertEqual(
            payload["tickets_by_model"],
            {QWEN: [1, 3, 4], ZAI: [2, 5], CLOUD_B: [6]})

    def test_a_cloud_deal_states_an_empty_lane(self):
        # Zero local tickets is an answer, not an absence: seed 'a3'
        # deals the one writing ticket to the cloud row, the map names it
        # and the lane says none — no local id may appear in it.
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "1", "--deal", "--seed", "a3")

        self.assertIsNone(code)
        self.assertEqual(
            self.ticket_id_lines(out),
            [f"ticket ids: 1 -> {CLOUD_A}"])
        self.assertEqual(self.lane_lines(out),
                         ["lane: none — no local-dealt tickets"])

    def test_the_budget_json_carries_the_empty_lane_too(self):
        out, _, code, _ = self.run_cli(
            "--domain", "writing", "--tickets", "1", "--deal", "--seed", "a3",
            "--budget", "100", "--json")

        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["lane"], [])
        self.assertEqual(payload["tickets_by_model"], {CLOUD_A: [1]})


class SubstitutionLaneTests(LaneCliMixin, unittest.TestCase):
    """AC3: lane membership follows the served model under substitution —
    a cloud Spare's tickets exit the lane, a local Spare's join it, a
    local-to-local takeover keeps them under the new serve — while the
    record (printed and `--json`) states the effect from the same seeded
    deal. The published chain is never rewritten: substitution is an
    invocation (issue #71), it only reports the movement."""

    def test_a_cloud_deal_substituted_onto_its_local_spare_joins_the_lane(self):
        # Seed 'j4' dealt all 3 tickets to the cloud row (lane: none);
        # the sole miss is local, so the Spare joins with the ids whole.
        out, _, code, _ = self.one_cloud_one_local_deal(
            "--substitute", CLOUD_A)

        self.assertEqual(code, 0)
        self.assertIn(
            f"lane: tickets 1, 2, 3 join the lane — served by {QWEN}", out)

        out, _, code, _ = self.one_cloud_one_local_deal(
            "--substitute", CLOUD_A, "--json")
        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(payload["lane"],
                         [{"model": QWEN, "tickets": [1, 2, 3]}])

    def test_a_local_row_substituted_onto_a_cloud_spare_exits_the_lane(self):
        # Seed 'c1' dealt qwen ids 1, 3, 4; its Spare is the no-load cloud
        # 0813 (the higher-Score miss). The takeover leaves the lane with
        # only zai's ids — the cloud serves 1, 3, 4 now, never the lane.
        out, _, code, _ = self.two_local_deal(
            "--substitute", QWEN)

        self.assertEqual(code, 0)
        self.assertIn(
            f"lane: tickets 1, 3, 4 exit the lane — {CLOUD_A} is not local",
            out)

        out, _, code, _ = self.two_local_deal("--substitute", QWEN,
                                              "--json")
        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(payload["lane"],
                         [{"model": ZAI, "tickets": [2, 5]}])

    def test_a_local_to_local_substitution_keeps_the_ids_in_the_lane(self):
        # Sensitive: seed 'a3' dealt glm id 1 and zai ids 2-5, qwen missed
        # and is the only Spare there may be. The ids move groups — still
        # lane members, because membership follows the served model.
        out, _, code, _ = self.three_local_sensitive_deal(
            "--substitute", ZAI)

        self.assertEqual(code, 0)
        self.assertIn(
            f"lane: tickets 2, 3, 4, 5 move to {QWEN} — membership follows "
            "the serve", out)

        out, _, code, _ = self.three_local_sensitive_deal(
            "--substitute", ZAI, "--json")
        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(payload["lane"],
                         [{"model": GLM, "tickets": [1]},
                          {"model": QWEN, "tickets": [2, 3, 4, 5]}])

    def test_a_cloud_to_cloud_substitution_leaves_the_lane_alone(self):
        # Seed 'c1' dealt cloud pro id 6; its Spare is cloud 0813. No
        # local serve is involved, so the lane the record carries is the
        # sealed deal's own — unchanged by the takeover.
        out, _, code, _ = self.two_local_deal(
            "--substitute", CLOUD_B)

        self.assertEqual(code, 0)
        self.assertIn("lane: unchanged — neither serve is local", out)

        out, _, code, _ = self.two_local_deal(
            "--substitute", CLOUD_B, "--json")
        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(
            payload["lane"],
            [{"model": QWEN, "tickets": [1, 3, 4]},
             {"model": ZAI, "tickets": [2, 5]}])

    def test_a_second_death_states_the_held_tickets_lane_effect(self):
        # The substituted row missed the draw (seed 'a3', tickets 0): it
        # holds a ticket through an earlier substitution, so no id of this
        # deal's assignment names it — the record says `the held ticket`,
        # and with the local Spare the effect is a join. The `--json`
        # `lane` stays the sealed deal's (stateless re-derivation has no
        # id to move); `tickets: 0` marks the held case for a consumer.
        out, _, code, _ = self.two_local_deal(
            "--substitute", CLOUD_B, seed="a3")

        self.assertEqual(code, 0)
        self.assertIn(
            f"lane: the held ticket joins the lane — served by {QWEN}", out)

        out, _, code, _ = self.two_local_deal(
            "--substitute", CLOUD_B, "--json", seed="a3")
        self.assertIn(code, (None, 0))
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["verdict"], "substituted")
        self.assertEqual(payload["tickets"], 0)
        self.assertEqual(payload["lane"],
                         [{"model": ZAI, "tickets": [3, 6]}])


class LaneUnitTests(unittest.TestCase):
    """The helpers' own contract (the CLI fixtures above carry admission
    and the draw; this pins the grouping and the map shapes directly)."""

    def test_groups_follow_first_assignment_and_name_only_local_ids(self):
        assign = ["openrouter/cloud", "lmstudio/a", "lmstudio/b", None,
                  "lmstudio/a"]
        lane = modelbandit.deal_lane(
            assign, local={"lmstudio/a", "lmstudio/b"})

        self.assertEqual(
            lane, [{"model": "lmstudio/a", "tickets": [2, 5]},
                   {"model": "lmstudio/b", "tickets": [3]}])

    def test_the_ticket_map_covers_every_dealt_row_in_deal_row_order(self):
        rows = [{"mid": "openrouter/cloud-heavy", "tickets": 2},
                {"mid": "lmstudio/local", "tickets": 1},
                {"mid": "lmstudio/missed", "tickets": 0}]
        assign = ["openrouter/cloud-heavy", "lmstudio/local",
                  "openrouter/cloud-heavy"]
        mapping = modelbandit.tickets_by_model(
            rows, assign=assign, local={"lmstudio/local"})

        self.assertEqual(
            mapping,
            {"openrouter/cloud-heavy": [1, 3], "lmstudio/local": [2]})
        # The row that missed the draw holds no id and keys nothing.
        self.assertNotIn("lmstudio/missed", mapping)


if __name__ == "__main__":
    unittest.main()
