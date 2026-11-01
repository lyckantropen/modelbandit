"""SKILL.md contract pins for the free-use zones setup (issue #36).

The README links `SKILL.md#set-up-the-free-use-zones` and quotes the
interview question verbatim, so the section heading, the interview's
substance and step 2's offer are a contract, not prose that may drift.
Document reads only — no behaviour, no network, no machine state.
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


class ZonesSetupSectionTests(unittest.TestCase):
    """AC1: the interview section exists with the retention-aware question,
    the worktree-root rule, the default-closed statement and the review
    step — beside the secrets interview, mirroring its shape."""

    def setUp(self):
        self.body = section("Set up the free-use zones")

    def test_the_heading_is_exact_so_the_readme_anchor_resolves(self):
        self.assertEqual(TEXT.count("## Set up the free-use zones"), 1)
        self.assertEqual(TEXT.count("## Set up the secrets file"), 1)
        # ...and it sits beside the secrets interview, before Reference
        titles = [h.splitlines()[0] for h in HEADINGS]
        self.assertEqual(
            titles[titles.index("## Set up the secrets file") + 1],
            "## Set up the free-use zones")
        self.assertEqual(
            titles[titles.index("## Set up the free-use zones") + 1],
            "## Reference")

    def test_the_question_asks_about_retention_in_user_terms(self):
        self.assertIn("may free models — some of which retain what you "
                      "send — run on content here?", self.body)
        for regime in ("open", "sensitive", "closed"):
            self.assertIn(regime, self.body)

    def test_candidate_folders_are_discovered_not_invented(self):
        self.assertIn("working folder", self.body)
        self.assertIn("repositories", self.body)
        self.assertIn("worktree", self.body)

    def test_the_worktree_root_rule_is_carried_into_the_interview(self):
        # An undeclared worktree root stays closed; declaring the directory
        # the worktrees live in lets the origin repository's zone decide.
        self.assertIn("undeclared worktree root stays closed", self.body)
        self.assertIn("origin repository", self.body)

    def test_anything_unasked_stays_closed_and_the_interview_opens_less(self):
        self.assertRegex(self.body, r"(?i)unasked.*closed")
        self.assertIn("never more", self.body)

    def test_the_proposal_is_written_via_write_zones_then_reviewed(self):
        self.assertIn("--write-zones", self.body)
        self.assertRegex(self.body, r"(?i)\breview\b")
        self.assertRegex(self.body, r"(?i)\bverify\b")


class Step2OfferTests(unittest.TestCase):
    """AC4: step 2 surfaces absent/undeclared zones with an offer to run the
    interview, naming the consequence — remote free routes excluded —
    surfaced every time it applies, never silently skipped."""

    def setUp(self):
        self.body = step(2, "Pull popularity.")

    def test_step2_offers_the_interview_for_absent_or_undeclared_zones(self):
        self.assertIn("Set up the free-use zones", self.body)
        self.assertRegex(self.body, r"(?i)zones file.*absent")
        self.assertRegex(self.body, r"zone: undeclared \(closed\)")

    def test_the_offer_names_the_consequence(self):
        # Wording names what absence costs this run: remote free routes
        # are excluded.
        self.assertRegex(self.body, r"(?i)remote free routes.*excluded")

    def test_the_offer_is_made_never_silently_skipped(self):
        self.assertRegex(self.body, r"(?i)never silently skipped")


class MigrationRoutingTests(unittest.TestCase):
    """The caution: SKILL.md carries exactly the two migration-routing lines
    #40 added — the frontmatter keyword sentence and one body pointer —
    never duplicated, never extended here."""

    def test_frontmatter_carries_one_migration_keyword_sentence(self):
        self.assertEqual(TEXT.count("migrate from the old names"), 1)

    def test_body_carries_one_migration_pointer(self):
        self.assertEqual(TEXT.count("read `migrate.md` and follow it"), 1)


class ExitContractV2WordingTests(unittest.TestCase):
    """Issue #41 pins: the closed-zone protocol launches only on the
    `allowed` verdict (default-deny), and the exit-status reference carries
    the v2 table — status says the tool ran, output says what's true."""

    def test_protocol_step4_launches_only_on_the_allowed_verdict(self):
        body = section("Closed-zone protocol")
        self.assertIn("Launch only when the pre-flight says `allowed`",
                      body)
        self.assertIn("anything else means do not launch", body)
        self.assertNotIn("exit **5**", body)
        self.assertNotIn("Exit **0** means", body)

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


if __name__ == "__main__":
    unittest.main()