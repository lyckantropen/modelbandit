"""SKILL.md contract pins (issue #36 originally; #78 rewrote the flow).

The skill's flow is one interaction loop — assess, deal, present, offer
changes — with the closed-area rule stated once and the mechanical floor as
the loop's one-line rule. The setup interviews and the five-rule closed-zone
protocol are deleted; the doc-contract tests that pinned them (the interview
sections, step 2's offer, the protocol launch) left with the prose they
pinned, not updated. The Reference keeps operational readout shapes only —
the glossary owns term definitions. Document reads only — no behaviour, no
network, no machine state.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_PATH = os.path.join(ROOT, "skills", "modelbandit", "SKILL.md")

with open(SKILL_PATH, encoding="utf-8") as f:
    TEXT = f.read()

HEADINGS = [part for part in re.split(r"(?m)^(?=## )", TEXT)
            if part.startswith("## ")]


def flat(text):
    """Whitespace-normalised prose: SKILL.md wraps lines anywhere, the
    contract is the words — an em-dashed question quoted by the README must
    match whether or not it wraps across a line."""
    return " ".join(text.split())


def section(title):
    """The body of one `## <title>` section, through the next `##` heading."""
    for part in HEADINGS:
        if part.startswith(f"## {title}\n"):
            return flat(part)
    raise AssertionError(f"SKILL.md has no section {title!r}")


def step(number, title):
    """One numbered step of ## Steps, from its marker to the next step."""
    start = TEXT.index(f"{number}. **{title}**")
    following = re.search(rf"(?m)^{number + 1}\. \*\*", TEXT[start:])
    body = TEXT[start:start + following.start()] if following else TEXT[start:]
    return flat(body)


class OneInteractionLoopTests(unittest.TestCase):
    """Ticket #78: one interaction loop replaces the setup interviews and
    the closed-zone protocol. The loop is stated once as short prose; the
    closed-area rule is one sentence, no five-rule ceremony; the mechanical
    floor is the loop section's one-line rule, exactly once in the file."""

    def test_the_loop_is_stated_once_in_its_own_section(self):
        body = section("One interaction loop")
        for word in ("assess", "deal", "present", "offer changes"):
            self.assertIn(word, body)
        self.assertEqual(TEXT.count("## One interaction loop"), 1)

    def test_the_mechanical_floor_sentence_appears_exactly_once(self):
        sentence = ("facts and arithmetic stay mechanical; "
                    "editorial completeness is a mark in the table.")
        self.assertEqual(flat(TEXT).count(sentence), 1)
        self.assertIn(sentence, section("One interaction loop"))

    def test_the_closed_area_rule_is_stated_once_without_ceremony(self):
        self.assertEqual(
            flat(TEXT).count("names the zone, stops, and asks"), 1)
        self.assertNotIn("Closed-zone protocol", TEXT)

    def test_no_setup_interviews_or_worktree_interview_prose_remain(self):
        flat_text = flat(TEXT)
        for gone in ("## Set up the secrets file",
                     "## Set up the free-use zones",
                     "### Worktrees",
                     "undeclared worktree root stays closed",
                     "may free models — some of which retain what you send",
                     "--write-secrets",
                     "modelbandit.secrets.json"):
            self.assertNotIn(gone, flat_text)

    def test_the_steps_use_the_automatic_assessment_vocabulary(self):
        collect = step(1, "Collect the demand.")
        self.assertIn("names its ticket files", collect)
        self.assertIn("held:", collect)
        self.assertIn("follow-up local-only run", collect)
        # The deal-time check is the run's own work: no manual pre-flight
        # choreography is instructed any more.
        self.assertNotIn("--check-secrets", collect)


class ReferenceDefinitionOwnershipTests(unittest.TestCase):
    """The definition-ownership split: the glossary owns term definitions;
    the Reference keeps operational readout shapes only."""

    def test_no_regime_vocabulary_survives_anywhere(self):
        # Regime folded into Zone (glossary): the binary posture replaced
        # the ladder everywhere, so the word has no home in the skill file.
        self.assertNotIn("regime", flat(TEXT).lower())

    def test_the_zones_reference_keeps_the_operational_shapes_only(self):
        body = section("Reference")
        self.assertIn("$XDG_CONFIG_HOME/modelbandit/zones.json", body)
        self.assertIn('{"zones": ["', body)
        self.assertIn("--write-zones", body)
        self.assertIn("atomically", body)
        # The exception list is the whole schema: no per-entry posture key
        # and no default key survive in prose.
        flat_text = flat(TEXT)
        self.assertNotIn('"free":', flat_text)
        self.assertNotIn('"default"', flat_text)
        # The old zone-header shapes are gone with the ladder.
        self.assertNotIn("zone: undeclared (closed)", flat_text)
        self.assertNotIn("sensitive via --sensitive", flat_text)


class MigrationRoutingTests(unittest.TestCase):
    """The caution: SKILL.md carries exactly the two migration-routing lines
    #40 added — the frontmatter keyword sentence and one body pointer —
    never duplicated, never extended here."""

    def test_frontmatter_carries_one_migration_keyword_sentence(self):
        self.assertEqual(TEXT.count("migrate from the old names"), 1)

    def test_body_carries_one_migration_pointer(self):
        self.assertEqual(TEXT.count("read `migrate.md` and follow it"), 1)


class ExitContractV2WordingTests(unittest.TestCase):
    """Issue #41 pins: the exit-status reference carries the v2 table —
    status says the tool ran, output says what's true. (The protocol-launch
    pins left with the closed-zone protocol they pinned — #78 deleted it.)"""

    def test_the_exit_statuses_reference_is_the_v2_table(self):
        body = section("Reference")
        self.assertIn("ran to completion: any verdict", body)
        self.assertIn("carries no contract meaning", body)
        self.assertIn("could not form a verdict", body)
        self.assertIn("read the verdict lines (or `--json`), not `$?` "
                      "(ADR-0004)", body)
        self.assertNotIn("**1** Secrets gate sensitive", body)
        self.assertNotIn("**5** blocked by the free-use zone", body)


class Adr0004Tests(unittest.TestCase):
    """AC6: ADR-0004 is present."""

    ADR = os.path.join(ROOT, "docs", "adr",
                       "0004-status-says-if-the-tool-ran.md")

    def test_adr_0004_exists(self):
        self.assertTrue(os.path.isfile(self.ADR))

    def test_structure_mirrors_the_earlier_adrs(self):
        def structure(path):
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertTrue(lines[0].startswith("# "), path)
            self.assertFalse(lines[0].startswith("## "), path)
            return [line for line in lines if line.startswith("## ")]

        self.assertEqual(structure(self.ADR),
                         structure(os.path.join(ROOT, "docs", "adr",
                                                "0003-fail-closed-by-default"
                                                ".md")))

    def test_the_decision_and_both_rejected_alternatives_are_recorded(self):
        with open(self.ADR, encoding="utf-8") as f:
            text = flat(f.read())
        # The v2 table, decision and retirement.
        self.assertIn("ran to completion", text)
        self.assertIn("no contract meaning", text)
        self.assertIn("could not form a verdict", text)
        self.assertIn("Retired: **3** (not-certified), **5** (zone-block), "
                      "**1** (sensitive)", text)
        # Rejected: keep the integer enum — every verdict burns a code and
        # the 1-collision stays.
        self.assertIn("Keep the integer enum", text)
        self.assertIn("every new verdict burns a code", text)
        # Rejected: a --gate boolean — no honest nonzero for "false", and
        # jq -e already owns shell booleans.
        self.assertIn("`--gate` boolean flag", text)
        self.assertIn("no honest nonzero remains for", text)
        self.assertIn("`jq -e '.allowed'` already owns shell booleans", text)


class PlanEconomicsWordingTests(unittest.TestCase):
    """Issue #60: the skill prose tells the shipped plan-economics truth —
    the plans catalog, the prospective ledger, risk-of-Draw and the readout
    lines, each pinned to the code's own shapes and vocabulary."""

    def test_reference_names_the_plan_catalog_and_its_facts(self):
        body = section("Reference")
        self.assertIn("**Plan catalog (`plans`)**", body)
        for fact in ("list_price", "five_hour", "weekly", "monthly",
                     "exposure", "regions", "status 4"):
            self.assertIn(fact, body)

    def test_reference_states_the_ledger_and_risk_of_draw(self):
        body = section("Reference")
        self.assertIn("**Allowance & Draw**", body)
        self.assertIn("one 5-hour burst", body)
        self.assertIn("stateless", body)
        self.assertIn("**Risk of Draw**", body)
        self.assertIn("ADR-0006", body)

    def test_reference_names_the_declared_family_link(self):
        # Issue #61: each plans entry declares its Twin; the link is the
        # declaration (never a slug derivation), and a link that names no
        # Metered route refuses the load.
        body = section("Reference")
        self.assertIn("`family_ref`", body)
        self.assertIn("the Twin's Metered serving id", body)
        self.assertIn("nothing derives a Twin from an id's shape", body)
        self.assertIn("a `family_ref` that names no Metered route", body)

    def test_reference_carries_the_readout_shapes(self):
        body = section("Reference")
        self.assertIn("**Plan readout**", body)
        self.assertIn("allowance draw: <model> $X of $Y "
                      "(Z% of monthly; W% of 5h)", body)
        self.assertIn("Draw $Y/ticket", body)

    def test_the_pick_step_names_the_plan_readout(self):
        self.assertIn("Plan tickets carry their budget facts",
                      step(5, "Pick — or deal."))
        self.assertIn("risk of its list-priced Draw",
                      step(3, "Order by task score."))


class MarketResolutionWordingTests(unittest.TestCase):
    """Issue #64: the skill tells the market-resolution truth the wave made
    real — provider-qualified ids in the deal and the pick, the Twin at cap
    (plan → metered, one direction), the plan-share line, and the catalog
    check as the residual, market-named and agent-side. Every claim pinned
    here is honoured by the code on this branch."""

    def test_the_deal_step_names_qualified_ids_for_deal_and_pick(self):
        body = step(5, "Pick — or deal.")
        self.assertIn("provider-qualified", body)
        self.assertIn("`openrouter/<slug>`", body)
        self.assertIn("no slug archaeology", body)

    def test_the_deal_step_states_the_plan_share_line_beside_free_share(self):
        body = step(5, "Pick — or deal.")
        self.assertIn("plan share: N/M tickets (P%)", body)
        self.assertIn("Beside it", body)
        # Absorbed tickets are metered: the plan share never counts them.
        self.assertIn("absorbed counted metered", body)

    def test_the_deal_step_states_the_twin_rule_one_direction_only(self):
        body = step(5, "Pick — or deal.")
        self.assertIn("**Twin**", body)
        self.assertIn("same model served metered", body)
        self.assertIn("plan → metered only, never the reverse", body)
        self.assertIn("no Twin resolves", body)

    def test_the_residual_check_is_market_named_and_agent_side(self):
        body = step(5, "Pick — or deal.")
        self.assertIn("market each row names", body)
        self.assertIn("`opencode models`", body)
        self.assertIn("never shells out to a harness", body)

    def test_the_allowance_reference_brings_twin_substitution_present_tense(self):
        body = section("Reference")
        self.assertNotIn("market resolution's later work", body)
        self.assertIn("hands its ticket to its **Twin**", body)
        self.assertIn("never the ledger's", body)

    def test_the_deal_reference_names_the_plan_share_readout(self):
        body = section("Reference")
        self.assertIn("plan share: N/M tickets (P%)", body)
        self.assertIn("Every dealt row is named by its provider-qualified id",
                      body)

    def test_no_plan_first_billing_or_reverse_flip_is_claimed(self):
        # The adapter forces one direction; billing-layer semantics stay out.
        self.assertNotIn("plan-first", TEXT)
        self.assertNotIn("metered → plan", TEXT)
        self.assertNotIn("metered to plan", TEXT)


class SparesWordingTests(unittest.TestCase):
    """Issue #71: the skill tells the spares/substitution truth — a named
    Spare per dealt row, the no-load/local-only preferences, the invocation
    shape (`--substitute`, the reason classes), the fenced record and the
    exit-0 exhaustion. Every claim pinned here is honoured by the code on
    this branch."""

    def test_the_deal_step_names_the_spare_and_the_substitution_invocation(self):
        body = step(5, "Pick — or deal.")
        self.assertIn("**Spare**", body)
        self.assertIn("highest-Score eligible", body)
        self.assertIn("--substitute <model>", body)
        self.assertIn("no-load failover preferred", body)

    def test_the_reference_carries_the_record_shape_and_the_reason_classes(self):
        body = section("Reference")
        self.assertIn("**Spares & substitution**", body)
        self.assertIn("substitution: <model> -> <spare>", body)
        self.assertIn("restarts the ticket whole", body)
        self.assertIn("--reason dead-attempt", body)
        self.assertIn("substitution refused", body)
        self.assertIn("`spare` column", body)

    def test_the_reference_states_the_fence_and_the_exit_zero_exhaustion(self):
        body = section("Reference")
        self.assertIn("never re-gated", body)
        self.assertIn("sensitive — local-only (ADR 0008)", body)
        self.assertIn("Blocked and substituted outcomes exit 0", body)
        self.assertIn("no-load failover preference", body)
        # The stateless invocation contract: no stored state, same seed.
        self.assertIn("Substitution is an invocation, not stored state", body)
        self.assertIn("seed-deterministic", body)


if __name__ == "__main__":
    unittest.main()