"""Packaging invariants for the skill subtree.

The skill folder is the unit of deployment: skills/modelbandit/
carries exactly the deployable set (skill file, script directory, policy
file, migration file), the repository root keeps the research, tests and
docs. Layout only — no selection, pricing or deal behavior is asserted here.

Policy resolution belongs to layout too: the deployed skill must read its
own policy.json from wherever the script landed, so each deployment shape
the CLI can be copied into (shipped scripts/ layout, flat copy, a script
reached through a link) is pinned here against `_default_policy`.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "skills", "modelbandit")


def inventory(root):
    """Relative paths of everything under root, minus bytecode caches."""
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in dirnames:
            found.add(os.path.relpath(os.path.join(dirpath, name), root))
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            found.add(os.path.relpath(os.path.join(dirpath, name), root))
    return found


class PackagingInvariantTests(unittest.TestCase):
    def test_skill_subtree_is_exactly_the_deployable_set(self):
        with self.subTest("subtree top level is exactly the deployables"):
            self.assertEqual(set(os.listdir(SKILL_DIR)),
                             {"SKILL.md", "scripts", "policy.json",
                              "migrate.md"})
            self.assertEqual(inventory(SKILL_DIR),
                             {"SKILL.md", "policy.json", "scripts",
                              "migrate.md",
                              os.path.join("scripts", "modelbandit.py")})

        with self.subTest("script directory contains the CLI"):
            self.assertTrue(
                os.path.isfile(os.path.join(SKILL_DIR, "scripts", "modelbandit.py")))

        with self.subTest("no skill file at the repository root"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, "SKILL.md")))

        with self.subTest("root keeps research, tests, docs and README"):
            for name in ("research", "tests", "docs", "README.md"):
                self.assertTrue(os.path.exists(os.path.join(ROOT, name)),
                                f"missing at repository root: {name}")


class PolicyResolutionTests(unittest.TestCase):
    """The deployed skill reads its own policy.json — the path the gate,
    the pre-flight and --status judge by default. The shipped layout puts
    the policy two directories up from the script; a flat copy puts it
    beside the script; either may be reached through a link. Before this
    was pinned, a flat deployment computed a path outside the skill folder
    and the sensitive gate silently judged with an empty policy."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write_policy(self, folder):
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "policy.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{}")
        return path

    def link(self, link_path, target):
        """A junction on Windows (`mklink /J` needs no privileges), a symlink
        elsewhere — the same helper shape the secrets-wiring suite uses."""
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", link_path, target],
                capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
        else:
            os.symlink(target, link_path, target_is_directory=True)
        return link_path

    def test_the_shipped_layout_resolves_the_skills_own_policy(self):
        script = os.path.join(SKILL_DIR, "scripts", "modelbandit.py")
        expected = os.path.join(SKILL_DIR, "policy.json")
        self.assertEqual(modelbandit._default_policy(script), expected)
        # The module's own default is that path — the checkout's, whether
        # or not it was reached through the skills-directory link.
        self.assertEqual(modelbandit.DEFAULT_POLICY, expected)

    def test_a_flat_copy_resolves_the_policy_beside_the_script(self):
        # Regression: two levels up from a flat copy lands OUTSIDE the
        # skill folder (~/.agents/skills/policy.json), so the sensitive
        # gate judged with an empty policy while the real file sat beside
        # the script, unread.
        skill = os.path.join(self.root, "flat")
        expected = self.write_policy(skill)
        self.assertEqual(
            modelbandit._default_policy(os.path.join(skill, "modelbandit.py")),
            expected)

    def test_a_script_reached_through_a_link_resolves_the_target_skill(self):
        skill = os.path.join(self.root, "real")
        os.makedirs(os.path.join(skill, "scripts"))
        expected = self.write_policy(skill)
        linked = self.link(os.path.join(self.root, "link-scripts"),
                           os.path.join(skill, "scripts"))
        self.assertEqual(
            modelbandit._default_policy(os.path.join(linked, "modelbandit.py")),
            expected)

    def test_no_policy_anywhere_keeps_the_canonical_two_up_path(self):
        # Nothing exists to find: the path --status and the status-4
        # messages name is the shipped layout's — where it looked first.
        root = os.path.join(self.root, "bare")
        os.makedirs(os.path.join(root, "scripts"))
        self.assertEqual(
            modelbandit._default_policy(
                os.path.join(root, "scripts", "modelbandit.py")),
            os.path.join(root, "policy.json"))


if __name__ == "__main__":
    unittest.main()
