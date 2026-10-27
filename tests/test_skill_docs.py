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


if __name__ == "__main__":
    unittest.main()