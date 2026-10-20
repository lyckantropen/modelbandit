"""Packaging invariants for the skill subtree.

The skill folder is the unit of deployment: skills/openrouter-model-router/
carries exactly the deployable set (skill file, script directory, policy
file), the repository root keeps the research, tests and docs. Layout only —
no selection, pricing or deal behavior is asserted here.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "skills", "openrouter-model-router")


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
                             {"SKILL.md", "scripts", "policy.json"})
            self.assertEqual(inventory(SKILL_DIR),
                             {"SKILL.md", "policy.json", "scripts",
                              os.path.join("scripts", "bind.py")})

        with self.subTest("script directory contains the CLI"):
            self.assertTrue(
                os.path.isfile(os.path.join(SKILL_DIR, "scripts", "bind.py")))

        with self.subTest("no skill file at the repository root"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, "SKILL.md")))

        with self.subTest("root keeps research, tests, docs and README"):
            for name in ("research", "tests", "docs", "README.md"):
                self.assertTrue(os.path.exists(os.path.join(ROOT, name)),
                                f"missing at repository root: {name}")


if __name__ == "__main__":
    unittest.main()
