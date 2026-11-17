"""Tests for free-use zones: the machine-wide bare opt-out list, its
resolver, the origin-aware effective zone and the closed-zone admission gate.

Fixtures only: every test injects its environment and its git runner, so no
test reads this machine's `$HOME` or touches the network. The submodule
fixtures are the deliberate exception: they run real `git` against
repositories built under a temporary directory, because the origin a
submodule reports is exactly what the resolver must interpret.
"""

import inspect
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelbandit  # noqa: E402
from test_cli import POLICY, build_world, make_model  # noqa: E402

HOME = os.path.join(os.sep, "home", "fixture-user") if os.name != "nt" \
    else r"C:\Users\fixture-user"
ENV = {"HOME": HOME, "USERPROFILE": HOME,
       "XDG_CONFIG_HOME": os.path.join(HOME, ".config")}
REPO = os.path.join(HOME, "vault")
PRIVATE = os.path.join(REPO, "private")
NOTES = os.path.join(REPO, "notes")
WORKTREE = os.path.join(HOME, ".worktrees", "t-1")


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


class ZonesFileTests(TempDirMixin):
    """`zones.json` at the machine's config root: a bare opt-out list of the
    paths declared closed, validated loudly (ADR-0010)."""

    import json as _json

    def write_zones(self, payload):
        return self.write("zones.json", self._json.dumps(payload))

    def test_zones_path_follows_xdg_config_home(self):
        self.assertEqual(modelbandit.zones_path(environ=dict(ENV)),
                         os.path.join(ENV["XDG_CONFIG_HOME"], "modelbandit",
                                      "zones.json"))

    def test_zones_path_falls_back_to_dot_config(self):
        environ = {"HOME": HOME, "USERPROFILE": HOME}
        self.assertEqual(modelbandit.zones_path(environ=environ),
                         os.path.join(HOME, ".config", "modelbandit",
                                      "zones.json"))

    def test_missing_file_declares_nothing(self):
        self.assertEqual(
            modelbandit.load_zones(os.path.join(self.root, "absent.json")),
            [])

    def test_loads_the_declared_closed_paths(self):
        path = self.write_zones({"zones": [PRIVATE, NOTES]})
        self.assertEqual(modelbandit.load_zones(path), [PRIVATE, NOTES])

    def test_unknown_top_level_key_fails_loudly(self):
        path = self.write_zones({"zones": [], "defaults": "open"})
        with self.assertRaisesRegex(SystemExit, "defaults"):
            modelbandit.load_zones(path)
        # ...and shows the one-line form instead of migrating the file.
        with self.assertRaisesRegex(SystemExit, r'\{"zones": \["'):
            modelbandit.load_zones(path)

    def test_the_retired_default_key_is_named(self):
        path = self.write_zones({"zones": [], "default": "closed"})
        with self.assertRaisesRegex(SystemExit, "default"):
            modelbandit.load_zones(path)

    def test_zones_must_be_a_list(self):
        path = self.write_zones({"zones": {"path": PRIVATE}})
        with self.assertRaisesRegex(SystemExit, "zones"):
            modelbandit.load_zones(path)

    def test_a_per_entry_posture_is_refused_and_the_entry_named(self):
        path = self.write_zones({"zones": [{"path": PRIVATE, "free": "closed"},
                                           {"path": NOTES, "free": "open"}]})
        with self.assertRaisesRegex(SystemExit, "zone #1"):
            modelbandit.load_zones(path)
        with self.assertRaisesRegex(SystemExit, "free"):
            modelbandit.load_zones(path)

    def test_zone_path_must_be_a_non_empty_string(self):
        for payload in ({"zones": [7]}, {"zones": [""]}, {"zones": [" "]},
                        {"zones": [{"free": "closed"}]}):
            with self.subTest(payload=payload):
                path = self.write_zones(payload)
                with self.assertRaisesRegex(SystemExit, "zone #1"):
                    modelbandit.load_zones(path)

    def test_the_payload_itself_must_be_an_object(self):
        path = self.write_zones([PRIVATE])
        with self.assertRaisesRegex(SystemExit, r'\{"zones": \["'):
            modelbandit.load_zones(path)


class DuplicateZoneTests(TempDirMixin):
    """Two entries naming the same normalised path stop loudly: a repeat
    would name nothing — the declaration is a set."""

    import json as _json

    def write_zones(self, payload):
        return self.write("zones.json", self._json.dumps(payload))

    def load(self, payload):
        return modelbandit.load_zones(self.write_zones(payload))

    def test_an_identical_path_declared_twice_stops(self):
        payload = {"zones": [PRIVATE, PRIVATE]}
        with self.assertRaisesRegex(SystemExit, r"zone #2 .* zone #1"):
            self.load(payload)

    def test_the_stop_names_the_source_and_the_path(self):
        payload = {"zones": [PRIVATE, PRIVATE]}
        with self.assertRaisesRegex(SystemExit, "zones.json"):
            self.load(payload)
        with self.assertRaisesRegex(SystemExit, "private"):
            self.load(payload)

    def test_a_path_that_only_normalises_the_same_stops(self):
        twin = PRIVATE + os.sep + "."
        payload = {"zones": [PRIVATE, twin]}
        with self.assertRaisesRegex(SystemExit, r"zone #2 .* zone #1"):
            self.load(payload)

    def test_paths_fold_case_where_the_platform_does(self):
        payload = {"zones": [PRIVATE, PRIVATE.upper()]}
        if os.name == "nt":
            with self.assertRaisesRegex(SystemExit, "zone #2"):
                self.load(payload)
        else:
            self.assertEqual(len(self.load(payload)), 2)


class ZoneResolverTests(unittest.TestCase):
    """Longest declared prefix wins; `~` and variables expand; the comparison
    follows this platform; anything uncovered is open."""

    ZONES = [REPO, PRIVATE]

    def resolve(self, folder, zones=None):
        return modelbandit.resolve_zone(folder, zones or self.ZONES,
                                        environ=dict(ENV))

    def test_longest_prefix_wins(self):
        deep = self.resolve(os.path.join(PRIVATE, "keys", "a.md"))
        self.assertEqual(deep.path, PRIVATE)
        self.assertEqual(deep.posture, "closed")
        top = self.resolve(os.path.join(REPO, "README.md"))
        self.assertEqual(top.path, REPO)
        self.assertEqual(top.posture, "closed")

    def test_no_match_is_open(self):
        resolved = self.resolve(os.path.join(HOME, "elsewhere", "x"))
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")

    def test_a_declared_path_matches_the_folder_itself(self):
        self.assertEqual(self.resolve(PRIVATE).path, PRIVATE)

    def test_a_prefix_must_end_on_a_path_boundary(self):
        sibling = PRIVATE + "-ish"
        resolved = self.resolve(os.path.join(sibling, "x"), [PRIVATE])
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")

    def test_tilde_expands_against_the_given_environment(self):
        resolved = self.resolve(os.path.join(PRIVATE, "x"), ["~/vault/private"])
        self.assertEqual(resolved.path, "~/vault/private")
        self.assertEqual(resolved.posture, "closed")

    def test_environment_variables_expand(self):
        environ = dict(ENV, VAULT=REPO)
        resolved = modelbandit.resolve_zone(os.path.join(NOTES, "x"),
                                            ["$VAULT/notes"], environ=environ)
        self.assertEqual(resolved.path, "$VAULT/notes")
        self.assertEqual(resolved.posture, "closed")

    def test_an_unknown_variable_is_left_as_written(self):
        resolved = self.resolve(os.path.join(REPO, "x"), ["$NOT_SET_ANYWHERE/x"])
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")

    def test_paths_compare_case_insensitively_where_the_platform_does(self):
        resolved = self.resolve(PRIVATE, [PRIVATE.upper()])
        if os.name == "nt":
            self.assertEqual(resolved.path, PRIVATE.upper())
            self.assertEqual(resolved.posture, "closed")
        else:
            self.assertIsNone(resolved.path)
            self.assertEqual(resolved.posture, "open")

    def test_the_shape_of_a_zone_is_binary_and_open_unless_declared(self):
        self.assertEqual(self.resolve(os.path.join(HOME, "x")).posture, "open")
        self.assertEqual(self.resolve(PRIVATE).posture, "closed")


def make_link(link, target):
    """A junction on Windows (`mklink /J` needs no privileges), a symlink
    elsewhere. Answers False when the platform cannot build one."""
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", link, target],
            capture_output=True, text=True)
        return completed.returncode == 0
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        return False
    return True


class LinkZoneTests(TempDirMixin):
    """A zone governs the place a path reaches, not the string it is spelled
    with: a junction or symlink is judged by the content it leads to, in both
    directions - a link inside an open zone into a closed area borrows
    nothing, and a link to an open package is not refused."""

    def setUp(self):
        super().setUp()
        self.open_dir = os.path.join(self.root, "open-zone")
        self.closed_dir = os.path.join(self.root, "closed-vault")
        os.makedirs(self.open_dir)
        os.makedirs(self.closed_dir)

    @staticmethod
    def no_git(args):
        raise OSError("not a repository")

    def test_a_link_inside_an_open_zone_into_a_closed_area_is_judged_closed(self):
        link = os.path.join(self.open_dir, "shortcut")
        self.assertTrue(make_link(link, self.closed_dir))
        resolved = modelbandit.effective_zone(link, zones=[self.closed_dir],
                                              run=self.no_git)
        self.assertEqual(resolved.path, self.closed_dir)
        self.assertEqual(resolved.posture, "closed")

    def test_a_link_outside_the_open_zone_pointing_at_it_is_judged_open(self):
        link = os.path.join(self.root, "elsewhere", "to-open")
        os.makedirs(os.path.dirname(link))
        self.assertTrue(make_link(link, self.open_dir))
        resolved = modelbandit.effective_zone(link, zones=[], run=self.no_git)
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")

    def test_a_declaration_spelled_through_a_link_names_the_resolved_place(self):
        # The declaration names the link; the zone governs the folder it
        # reaches, and the header says so instead of the link's spelling.
        vault = os.path.join(self.root, "vault")
        os.makedirs(vault)
        link = os.path.join(self.root, "vault-link")
        self.assertTrue(make_link(link, vault))
        resolved = modelbandit.resolve_zone(vault, [link])
        self.assertEqual(resolved.path, link)
        self.assertEqual(resolved.posture, "closed")
        self.assertEqual(modelbandit.zone_label(resolved),
                         f"{vault} (closed) (declared: {link})")

    def test_a_link_out_of_every_declared_place_reports_the_resolved_place(self):
        # The spelled path sits inside a declared closed zone; the place it
        # reaches is undeclared and open. The header names the place, not
        # the spelling, so the absence cannot be read as the declaration's.
        link = os.path.join(self.open_dir, "shortcut")
        elsewhere = os.path.join(self.root, "elsewhere")
        os.makedirs(elsewhere)
        self.assertTrue(make_link(link, elsewhere))
        resolved = modelbandit.resolve_zone(link, [self.open_dir])
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")
        self.assertEqual(modelbandit.zone_label(resolved),
                         f"{elsewhere} (open) (undeclared)")

    def test_a_declared_zone_path_that_does_not_exist_yet_still_applies(self):
        # Resolution is not existence: a zone declared ahead of its folder
        # validates and compares against the paths spelled under it.
        ghost = os.path.join(self.root, "not-built-yet")
        self.assertEqual(modelbandit.validate_zones({"zones": [ghost]}), [ghost])
        resolved = modelbandit.resolve_zone(os.path.join(ghost, "x"), [ghost])
        self.assertEqual(resolved.path, ghost)
        self.assertEqual(resolved.posture, "closed")

    def test_two_declarations_of_one_place_through_a_link_stop_loudly(self):
        # The link and its target are one place: declaring both is the
        # duplicate the resolver stops, not a last-wins repeat.
        link = os.path.join(self.root, "vault-link")
        self.assertTrue(make_link(link, self.closed_dir))
        with self.assertRaisesRegex(SystemExit, "zone #2"):
            modelbandit.validate_zones({"zones": [self.closed_dir, link]})


class OriginZoneTests(unittest.TestCase):
    """A worktree carries the posture of the repository it came from."""

    ZONES = [REPO]  # WORKTREE itself is undeclared, hence open

    def test_git_common_dir_resolves_to_the_origin_repository(self):
        self.assertEqual(
            modelbandit.git_origin(WORKTREE,
                            run=lambda args: os.path.join(REPO, ".git") + "\n"),
            REPO)

    def test_a_relative_common_dir_resolves_against_the_folder(self):
        self.assertEqual(modelbandit.git_origin(REPO, run=lambda args: ".git\n"), REPO)

    def test_git_missing_or_failing_answers_none(self):
        def boom(args):
            raise OSError("not a git repository")
        self.assertIsNone(modelbandit.git_origin(WORKTREE, run=boom))
        self.assertIsNone(modelbandit.git_origin(WORKTREE, run=lambda args: "\n"))

    def test_effective_zone_takes_the_stricter_of_folder_and_origin(self):
        # The worktree itself is open; its origin repository is closed.
        resolved = modelbandit.effective_zone(
            os.path.join(WORKTREE, "pkg"), zones=self.ZONES,
            run=lambda args: os.path.join(REPO, ".git"), environ=dict(ENV))
        self.assertEqual(resolved.path, REPO)
        self.assertEqual(resolved.posture, "closed")

    def test_the_folder_zone_answers_when_it_is_the_closed_one(self):
        zones = [os.path.join(WORKTREE, "private")]
        resolved = modelbandit.effective_zone(
            os.path.join(WORKTREE, "private"), zones=zones,
            run=lambda args: os.path.join(REPO, ".git"), environ=dict(ENV))
        self.assertEqual(resolved.path, os.path.join(WORKTREE, "private"))
        self.assertEqual(resolved.posture, "closed")

    def test_git_absent_leaves_the_working_folder_zone_alone(self):
        def boom(args):
            raise OSError("git is not installed")
        resolved = modelbandit.effective_zone(WORKTREE, zones=self.ZONES,
                                              run=boom, environ=dict(ENV))
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")

    def test_an_undeclared_folder_inherits_its_closed_origin(self):
        # The worktree lives outside anything declared; its repository is
        # declared closed, so the run is closed and the origin answers for it.
        resolved = modelbandit.effective_zone(
            os.path.join(HOME, "elsewhere", "wt"), zones=[REPO],
            run=lambda args: os.path.join(REPO, ".git"), environ=dict(ENV))
        self.assertEqual(resolved.path, REPO)
        self.assertEqual(resolved.posture, "closed")

    def test_an_undeclared_folder_stays_open_under_an_open_origin(self):
        # Open unless declared: neither the folder nor its repository is
        # declared, so nothing closes the run.
        resolved = modelbandit.effective_zone(
            os.path.join(HOME, "elsewhere", "wt"), zones=[],
            run=lambda args: os.path.join(REPO, ".git"), environ=dict(ENV))
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.posture, "open")

    def test_equal_postures_report_the_working_folder(self):
        zones = [os.path.join(HOME, "tmp")]
        resolved = modelbandit.effective_zone(
            os.path.join(HOME, "tmp", "x"), zones=zones,
            run=lambda args: os.path.join(HOME, "tmp", ".git"),
            environ=dict(ENV))
        self.assertEqual(resolved.path, os.path.join(HOME, "tmp"))
        self.assertEqual(resolved.posture, "closed")

    def test_an_origin_equal_to_the_folder_is_not_asked_twice(self):
        calls = []

        def run(args):
            calls.append(args)
            return os.path.join(REPO, ".git")
        modelbandit.effective_zone(REPO, zones=self.ZONES, run=run,
                                   environ=dict(ENV))
        self.assertEqual(len(calls), 1)  # one git call, no duplicate lookup


SUPER = os.path.join(HOME, "super")
SUBMODULE = os.path.join(SUPER, "sub")
# A submodule's git dir lives under the superproject's `.git/modules/<name>`,
# whatever folder git is asked from.
SUB_COMMON = os.path.join(SUPER, ".git", "modules", "sub")
SUB_WORKTREE = os.path.join(HOME, "elsewhere", "sub-wt")
# `core.worktree` in the module's config names its working tree, relative to
# the git dir.
MODULE_WORKTREE = ".." + os.sep + ".." + os.sep + ".." + os.sep + "sub"


def module_run(common_dir=SUB_COMMON, *, worktree=MODULE_WORKTREE,
               toplevel=SUBMODULE):
    """A git runner shaped like the submodule case: the common dir sits under
    `.git/modules`, `core.worktree` names the module's working tree."""
    def run(args):
        if args == ["rev-parse", "--git-common-dir"]:
            return common_dir + "\n"
        if args == ["config", "core.worktree"]:
            if worktree is None:
                raise OSError("core.worktree is unset")
            return worktree + "\n"
        if args == ["rev-parse", "--show-toplevel"]:
            if toplevel is None:
                raise OSError("not a working tree")
            return toplevel + "\n"
        raise OSError(f"unexpected git call: {args}")
    return run


class SubmoduleOriginTests(unittest.TestCase):
    """A submodule is judged by the repository whose working tree it is — its
    own root — never by the superproject's `.git/modules` directory."""

    def test_a_submodule_checkout_resolves_to_its_own_root(self):
        self.assertEqual(modelbandit.git_origin(SUBMODULE, run=module_run()),
                         SUBMODULE)

    def test_a_worktree_of_the_submodule_resolves_to_the_submodule_root(self):
        self.assertEqual(modelbandit.git_origin(SUB_WORKTREE, run=module_run()),
                         SUBMODULE)

    def test_an_unset_core_worktree_falls_back_to_the_toplevel(self):
        self.assertEqual(
            modelbandit.git_origin(SUBMODULE, run=module_run(worktree=None)),
            SUBMODULE)

    def test_an_unanswerable_module_git_dir_answers_none(self):
        # neither core.worktree nor a toplevel: no origin, not the bogus
        # `.git/modules` path a bare parent would give.
        self.assertIsNone(
            modelbandit.git_origin(SUBMODULE,
                            run=module_run(worktree=None, toplevel=None)))

    def test_a_plain_common_dir_is_never_rerouted(self):
        self.assertEqual(modelbandit.git_origin(REPO, run=lambda args: ".git\n"),
                         REPO)

    def test_a_folder_inside_the_submodule_is_governed_by_its_zone(self):
        # the zone declared on the submodule's path covers the folder, and
        # the submodule is its own origin.
        resolved = modelbandit.effective_zone(
            os.path.join(SUBMODULE, "deep"), zones=[SUBMODULE],
            run=module_run(), environ=dict(ENV))
        self.assertEqual(resolved.path, SUBMODULE)
        self.assertEqual(resolved.posture, "closed")

    def test_a_worktree_of_the_submodule_honours_the_submodule_zone(self):
        resolved = modelbandit.effective_zone(SUB_WORKTREE, zones=[SUBMODULE],
                                              run=module_run(),
                                              environ=dict(ENV))
        self.assertEqual(resolved.path, SUBMODULE)
        self.assertEqual(resolved.posture, "closed")


class SubmoduleFixtureTests(TempDirMixin):
    """Real repositories under a temporary directory: a superproject, a
    submodule in it, a linked worktree of that submodule, and a linked
    worktree of the superproject. Local file protocol only — no network —
    and zones are passed in, so no machine config is read."""

    def setUp(self):
        super().setUp()
        config = self.write("git-config", "")
        self.env = dict(os.environ,
                        GIT_CONFIG_GLOBAL=config, GIT_CONFIG_SYSTEM=config,
                        GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="Fixture",
                        GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Fixture",
                        GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.subrepo = self.make_repo("subrepo")
        self.super_root = self.make_repo("super")
        self.sub = os.path.join(self.super_root, "sub")
        self.super_wt = os.path.join(self.root, "wt-super")
        self.sub_wt = os.path.join(self.root, "wt-sub")
        self.git(self.super_root, "-c", "protocol.file.allow=always",
                 "submodule", "add", "-q", self.subrepo, "sub")
        self.git(self.super_root, "commit", "-qm", "add sub")
        self.git(self.sub, "worktree", "add", self.sub_wt, "-b", "sub-wt")
        self.git(self.super_root, "worktree", "add", self.super_wt,
                 "-b", "super-wt")

    def make_repo(self, name):
        path = os.path.join(self.root, name)
        os.makedirs(path)
        self.git(path, "init", "-q")
        self.git(path, "commit", "--allow-empty", "-qm", name)
        return path

    def git(self, cwd, *args):
        completed = subprocess.run(["git", "-C", cwd, *args], env=self.env,
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
        self.assertEqual(completed.returncode, 0,
                         f"git {' '.join(args)} failed: {completed.stderr}")
        return completed.stdout

    def test_a_submodule_honours_its_own_declaration(self):
        resolved = modelbandit.effective_zone(self.sub, zones=[self.sub])
        self.assertEqual(resolved.path, self.sub)
        self.assertEqual(resolved.posture, "closed")

    def test_a_folder_inside_the_submodule_honours_the_declaration(self):
        deep = os.path.join(self.sub, "deep")
        os.makedirs(deep)
        resolved = modelbandit.effective_zone(deep, zones=[self.sub])
        self.assertEqual(resolved.path, self.sub)
        self.assertEqual(resolved.posture, "closed")

    def test_a_worktree_of_the_submodule_honours_the_submodule_zone(self):
        resolved = modelbandit.effective_zone(self.sub_wt, zones=[self.sub])
        self.assertEqual(resolved.path, self.sub)
        self.assertEqual(resolved.posture, "closed")

    def test_a_plain_repo_resolves_itself(self):
        resolved = modelbandit.effective_zone(self.super_root,
                                              zones=[self.super_root])
        self.assertEqual(resolved.path, self.super_root)
        self.assertEqual(resolved.posture, "closed")

    def test_a_plain_worktree_still_inherits_its_repository(self):
        resolved = modelbandit.effective_zone(self.super_wt,
                                              zones=[self.super_root])
        self.assertEqual(resolved.path, self.super_root)
        self.assertEqual(resolved.posture, "closed")

    def test_a_closed_submodule_blocks_remote_free_and_admits_local(self):
        resolved = modelbandit.effective_zone(self.sub, zones=[self.sub])
        self.assertEqual(resolved.path, self.sub)
        self.assertEqual(resolved.posture, "closed")
        self.assertIn("remote free route is prohibited",
                      modelbandit.zone_block("z-ai/glm-5.4:free", resolved, policy={}))
        local_policy = {"free_models": {"qwen3-coder-30b": {"exposure": "local"}}}
        self.assertIsNone(modelbandit.zone_block("qwen3-coder-30b", resolved,
                                          policy=local_policy))

    def test_a_local_label_never_overrides_the_remote_predicate(self):
        # The pre-flight observes no serving, so localness is a serving fact
        # it cannot grant: a remote Free route labelled `local` is judged
        # remote whatever a stale policy says — refused in a closed zone, and
        # refused for a Sensitive shape with the reason naming Exposure.
        policy = {"free_models": {"qwen/qwen3-coder-30b": {
            "context_length": 262_144, "exposure": "local",
            "summary_ref": "qwen"}},
            "summaries": {"qwen": "fixture summary"}}
        closed = modelbandit.Zone(path="z", posture="closed")
        self.assertIn("remote free route is prohibited",
                      modelbandit.zone_block("qwen/qwen3-coder-30b:free", closed,
                                      policy=policy))
        open_zone = modelbandit.Zone(path=None, posture="open")
        self.assertIn("only Exposure local may serve a Sensitive shape "
                      "(trains)",
                      modelbandit.zone_block("qwen/qwen3-coder-30b:free",
                                             open_zone,
                                             policy=policy,
                                             material_sensitive=True))

    def make_link(self, link, target):
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", link, target],
                capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
        else:
            os.symlink(target, link)
        return link

    def test_a_link_to_the_repository_resolves_to_the_same_origin(self):
        # A junction placed outside the repository, pointing at it, is judged
        # by the repository it reaches: the folder's resolved place and the
        # git origin agree, so a closed repository stays closed either way.
        link = self.make_link(os.path.join(self.root, "repo-link"),
                              self.super_root)
        resolved = modelbandit.effective_zone(link, zones=[self.super_root])
        self.assertEqual(resolved.path, self.super_root)
        self.assertEqual(resolved.posture, "closed")


def candidate(mid, *, exposure="no-retention", is_free=False, local=False):
    # These tests isolate Zone and Exposure behavior; use a known window so
    # the independent Context gate does not decide their verdicts.
    return modelbandit.Candidate(id=mid, exposure=exposure, is_free=is_free,
                                 local=local, context_length=262_144)


def shape(posture="open", *, sensitive=False):
    return modelbandit.Shape(material_sensitive=sensitive, posture=posture)


class BinaryZoneGateTests(unittest.TestCase):
    """closed: no remote free route at all. The zone predicate itself names
    only those rows — a locally served model and every paid route stay in the
    candidate set — and the Exposure clause separately treats a closed place
    as Sensitive (ADR-0008, retained by ADR-0010), so a paid remote route is
    marked `exposed` rather than dropped. `open` forbids nothing."""

    def test_closed_excludes_an_openrouter_free_route(self):
        decision = modelbandit.admit(shape("closed"),
                              candidate("z-ai/glm-5.4:free", is_free=True))
        self.assertFalse(decision.admitted)
        self.assertIn("remote free route is prohibited", decision.reason)

    def test_closed_excludes_a_harness_free_route(self):
        for mid in ("opencode/glm-5.3-flash-free", "opencode/nemotron-3-ultra-free"):
            with self.subTest(mid=mid):
                self.assertFalse(modelbandit.admit(shape("closed"),
                                            candidate(mid, is_free=True)).admitted)

    def test_closed_admits_a_locally_served_model(self):
        decision = modelbandit.admit(shape("closed"),
                              candidate("qwen3-coder-30b", exposure="local",
                                        is_free=True, local=True))
        self.assertTrue(decision.admitted)

    def test_closed_excludes_a_paid_no_retention_route_through_exposure(self):
        # ADR 0008/0010: a closed place is Sensitive, so only Exposure `local`
        # serves it. The zone predicate itself names no paid route — the
        # Exposure clause excludes it, with the table's own mark.
        paid = candidate("deepseek/deepseek-v4-pro", exposure="no-retention")
        self.assertIsNone(modelbandit.zone_prohibition("closed", paid))
        decision = modelbandit.admit(shape("closed"), paid)
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, "exposed (no-retention)")

    def test_closed_excludes_a_paid_exposed_route_through_exposure(self):
        paid = candidate("deepseek/deepseek-v4-pro", exposure="trains")
        self.assertIsNone(modelbandit.zone_prohibition("closed", paid))
        decision = modelbandit.admit(shape("closed"), paid)
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, "exposed (trains)")

    def test_open_is_todays_behaviour(self):
        self.assertTrue(modelbandit.admit(
            shape("open"), candidate("z-ai/glm-5.4:free", is_free=True)).admitted)
        self.assertTrue(modelbandit.admit(
            shape("open"), candidate("opencode/x-free", is_free=True)).admitted)

    def test_sensitive_excludes_every_non_local_route(self):
        # ADR 0008: on a Sensitive shape only Exposure `local` may serve —
        # trains out, no-retention out alike, local in — and the open zone
        # adds no exclusion of its own.
        self.assertFalse(modelbandit.admit(
            shape("open", sensitive=True),
            candidate("z-ai/glm-5.4:free", exposure="trains", is_free=True)
        ).admitted)
        self.assertFalse(modelbandit.admit(
            shape("open", sensitive=True),
            candidate("opencode/x-free", is_free=True)).admitted)
        self.assertTrue(modelbandit.admit(
            shape("open", sensitive=True),
            candidate("qwen3-coder-30b", exposure="local",
                      is_free=True, local=True)).admitted)

    def test_the_sensitive_flag_still_applies_inside_a_closed_zone(self):
        # The flag states the shape and cannot move the zone: both
        # exclusions hold at once.
        paid_trains = candidate("deepseek/x", exposure="trains")
        decision = modelbandit.admit(shape("closed", sensitive=True),
                                     paid_trains)
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, "exposed (trains)")
        remote_free = candidate("a/b:free", is_free=True)
        self.assertIn("remote free route is prohibited",
                      modelbandit.admit(shape("closed", sensitive=True),
                                        remote_free).reason)

    def test_the_shape_defaults_to_open(self):
        self.assertEqual(modelbandit.Shape(),
                         modelbandit.Shape(material_sensitive=False,
                                           posture="open"))

    def test_sensitive_does_not_move_the_zone_posture(self):
        # A shape's sensitivity is not a place: the zone payload stays
        # binary whatever the shape.
        zone = modelbandit.Zone(path=REPO, posture="open")
        self.assertEqual(modelbandit.zone_label(zone), f"{REPO} (open)")
        self.assertEqual(modelbandit.zone_payload(zone)["posture"], "open")
        self.assertEqual(
            modelbandit.zone_block("deepseek/deepseek-v4-pro", zone,
                                   material_sensitive=True),
            "only Exposure local may serve a Sensitive shape (no-retention)")

    def test_the_gate_is_on_the_admission_path(self):
        self.assertIn(modelbandit.zone_gate, modelbandit.GATES)


class ZonePredicateTests(unittest.TestCase):
    """The one zone predicate, binary: a closed posture refuses the remote,
    unaccountable servings and nothing else. Exactly three askers — the
    pre-flight block, the candidate source filter and the Zone gate."""

    MATRIX = (
        candidate("z-ai/glm-5.4:free", exposure="trains", is_free=True),
        candidate("opencode/x-free", exposure="no-retention", is_free=True),
        candidate("qwen3-coder-30b", exposure="local", is_free=True, local=True),
        candidate("deepseek/x", exposure="no-retention"),
        candidate("deepseek/x", exposure="trains"),
    )

    def test_the_zone_prohibition_is_the_zone_clause_alone(self):
        # The source filter drops what the zone forbids; Exposure exclusions
        # stay in the table, marked with their reason.
        self.assertIn("remote free route is prohibited",
                      modelbandit.zone_prohibition(
                          "closed", candidate("a/b:free", is_free=True)))
        self.assertIsNone(modelbandit.zone_prohibition(
            "closed", candidate("a/b", exposure="trains")))
        self.assertIsNone(modelbandit.zone_prohibition(
            "open", candidate("a/b:free", is_free=True)))

    def test_closed_forbids_exactly_the_remote_free_kinds(self):
        for candidate_ in self.MATRIX:
            with self.subTest(candidate=candidate_):
                reason = modelbandit.zone_prohibition("closed", candidate_)
                remote_free = candidate_.is_free and not candidate_.local
                self.assertEqual(reason is not None, remote_free)

    def test_the_source_filter_and_the_gate_agree(self):
        for candidate_ in self.MATRIX:
            with self.subTest(candidate=candidate_):
                filtered = modelbandit.filter_zone_candidates(
                    {candidate_.id: 1.0}, {candidate_.id: {}}, {},
                    local_ids={candidate_.id} if candidate_.local else (),
                    posture="closed", intent="measured")
                gated = modelbandit.zone_gate(shape("closed"), candidate_)
                self.assertEqual(bool(filtered), gated.admitted)

    def test_exactly_four_callers_ask_the_predicate(self):
        # The reconciliation constraint (ticket #82, amended by spec #90):
        # the pre-flight block, the candidate source filter, the Zone gate
        # and provenance's closed-place question - the ask is direct there,
        # without a fabricated shape walking through the gate, and it is
        # still the one predicate, never a re-derivation.
        source = inspect.getsource(modelbandit)
        self.assertEqual(source.count("zone_prohibition("), 5)  # def + four
        for name in ("zone_block", "filter_zone_candidates", "zone_gate",
                     "closed_place"):
            self.assertIn("zone_prohibition(", inspect.getsource(
                getattr(modelbandit, name)))

    def test_the_retired_regime_vocabulary_is_gone(self):
        source = inspect.getsource(modelbandit)
        for gone in ("REGIMES", "DEFAULT_REGIME", "known_regime",
                     "regime_at_least", "shape_regime",
                     "closed_regime_provenance", "def stricter", "stricter("):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, source)


class ZonesWriterCliTests(TempDirMixin):
    """`--write-zones` is the interview's writer: JSON on stdin, validated
    through `validate_zones` before anything is written. A valid config lands
    atomically at the machine's zones path with that path printed; an invalid
    one refuses with status 4 naming the offending entry and writes nothing —
    a pre-existing file is left byte-identical. Temp XDG, no network."""

    def run_writer(self, payload):
        out, err, code = io.StringIO(), io.StringIO(), None
        config_home = os.path.join(self.root, "config")
        with mock.patch.object(sys, "argv", ["modelbandit", "--write-zones"]), \
                mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}), \
                mock.patch("modelbandit.fetch_json",
                           side_effect=AssertionError("no network in writer")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code

    @property
    def zones_path(self):
        return os.path.join(self.root, "config", "modelbandit", "zones.json")

    def seed_zones(self, payload_text):
        os.makedirs(os.path.dirname(self.zones_path), exist_ok=True)
        with open(self.zones_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(payload_text)
        with open(self.zones_path, "rb") as f:
            return f.read()

    def test_a_valid_config_is_written_atomically_and_the_path_is_printed(self):
        payload = json.dumps({"zones": ["~/work"]})

        out, err, code = self.run_writer(payload)

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn(self.zones_path, out)      # the path written is printed
        # load_zones accepts exactly what was written
        self.assertEqual(modelbandit.load_zones(self.zones_path), ["~/work"])
        # ...and the bare opt-out list is the whole file
        with open(self.zones_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"zones": ["~/work"]})
        # atomic: the file appears complete and no temp residue is left
        self.assertEqual(os.listdir(os.path.dirname(self.zones_path)),
                         ["zones.json"])

    def test_an_old_schema_entry_refuses_with_status_4_naming_it(self):
        payload = json.dumps({"zones": [{"path": "~/work", "free": "opened"}]})

        out, err, code = self.run_writer(payload)

        self.assertEqual(code, 4)
        self.assertIn("zone #1", err)            # the offending entry, named
        self.assertIn("opened", err)
        self.assertIn('{"zones": ["', err)       # the one-line new form
        self.assertEqual(out, "")                # nothing reported as written
        self.assertFalse(os.path.exists(self.zones_path))

    def test_the_retired_default_key_refuses_with_status_4(self):
        payload = json.dumps({"zones": [], "default": "closed"})

        _, err, code = self.run_writer(payload)

        self.assertEqual(code, 4)
        self.assertIn("default", err)
        self.assertFalse(os.path.exists(self.zones_path))

    def test_invalid_json_is_a_config_error_and_writes_nothing(self):
        out, err, code = self.run_writer("{")

        self.assertEqual(code, 4)
        self.assertIn("invalid JSON", err)
        self.assertEqual(out, "")
        self.assertFalse(os.path.exists(self.zones_path))

    def test_a_refusal_leaves_a_pre_existing_file_byte_identical(self):
        before = self.seed_zones(json.dumps({"zones": ["~/old"]}))
        payload = json.dumps({"zones": [{"path": "~/work", "free": "opened"}]})

        out, err, code = self.run_writer(payload)

        self.assertEqual(code, 4)
        self.assertIn("zone #1", err)
        with open(self.zones_path, "rb") as f:
            self.assertEqual(f.read(), before)   # pinned: not one byte moves

    def test_a_valid_proposal_replaces_an_existing_file(self):
        self.seed_zones(json.dumps({"zones": ["~/old"]}))
        payload = json.dumps({"zones": []})

        out, err, code = self.run_writer(payload)

        self.assertEqual(code, 0)
        self.assertEqual(modelbandit.load_zones(self.zones_path), [])
        self.assertIn(self.zones_path, out)

    def test_duplicate_paths_are_refused_on_overwrite_too(self):
        # Writing over an existing file goes through the same validation:
        # the duplicate the loader would reject never reaches disk.
        before = self.seed_zones(json.dumps({"zones": []}))
        payload = json.dumps({"zones": ["~/same", "~/same"]})

        _, err, code = self.run_writer(payload)

        self.assertEqual(code, 4)
        self.assertIn("duplicate", err)
        with open(self.zones_path, "rb") as f:
            self.assertEqual(f.read(), before)


class BinaryZonesCliTests(TempDirMixin):
    """The binary posture at the CLI seam (spec #75, ADR-0010): free routes
    work from the first run with no zones file, the file is a bare opt-out
    list, an old-schema file refuses with status 4, and one closed
    declaration covers the repository's worktrees. Every assertion is a
    printed line or a `--json` object — nothing below the CLI."""

    GIT_ENV = None

    def setUp(self):
        super().setUp()
        self.policy_path = os.path.join(self.root, "policy.json")
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(POLICY, f)
        self.config_home = os.path.join(self.root, "config")

    def write_zones(self, payload):
        os.makedirs(os.path.join(self.config_home, "modelbandit"),
                    exist_ok=True)
        with open(os.path.join(self.config_home, "modelbandit", "zones.json"),
                  "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def write_raw_zones(self, text):
        os.makedirs(os.path.join(self.config_home, "modelbandit"),
                    exist_ok=True)
        path = os.path.join(self.config_home, "modelbandit", "zones.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def run_cli(self, *argv, zones_absent=False, world=None, config_home=None):
        world = build_world() if world is None else world
        config_home = config_home or self.config_home
        if zones_absent:
            home = os.path.join(self.root, "home")
            env = {"XDG_CONFIG_HOME": "", "HOME": home, "USERPROFILE": home}
        else:
            env = {"XDG_CONFIG_HOME": config_home}

        def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
            if cache_name == "key.json":
                raise SystemExit("cannot reach https://openrouter.ai/api/v1/key")
            if cache_name == "models.json":
                return {"data": world["models"]}
            if cache_name == "classifications.json":
                return {"data": world["classifications"]}
            if cache_name == "rankings.json":
                return world["rankings"]
            if url.endswith("/endpoints"):
                slug = url[len(modelbandit.MODELS_URL) + 1:-len("/endpoints")]
                return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
            raise AssertionError(f"unexpected fetch: {url}")

        out, err = io.StringIO(), io.StringIO()
        code = None
        argv = ["modelbandit", "--policy", self.policy_path, *argv]
        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch), \
                mock.patch("modelbandit.probe_local_models", return_value={}), \
                mock.patch.object(modelbandit, "CACHE_DIR",
                                  os.path.join(self.root, "cache")), \
                mock.patch("modelbandit.machine_facts",
                           return_value={"identifiers": []}), \
                mock.patch.dict(os.environ, env), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sys, "stdin", io.StringIO("")), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                modelbandit.main()
            except SystemExit as exc:
                code = exc.code
        return out.getvalue(), err.getvalue(), code

    def zone_line(self, out):
        return next(ln for ln in out.splitlines() if ln.startswith("zone: "))

    def test_no_zones_file_states_open_with_no_warning_or_nag(self):
        # AC: an absent zones file is open — the header names the working
        # folder and the posture, and nothing warns, nags or points at
        # setup.
        out, err, code = self.run_cli("--status", "--working-dir", self.root,
                                      zones_absent=True)

        self.assertEqual(code, 0)
        self.assertEqual(self.zone_line(out), f"zone: {self.root} (open)")
        self.assertEqual(err, "")
        self.assertNotIn("zones file:", out)
        self.assertNotIn("warning", out.lower())
        self.assertNotIn("setup", out.lower())
        # A ranking run on the same machine says the same thing, and the
        # remote free routes are in the pool.
        world = build_world()
        world["models"].append(make_model("vendor/model:free", "0", "0", "0"))
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "vendor/model:free", "tag_usage_share": 0.5})
        ranked, err, code = self.run_cli("--domain", "writing", "--working-dir",
                                         self.root, zones_absent=True,
                                         world=world)
        self.assertIn(code, (None, 0))
        self.assertEqual(self.zone_line(ranked), f"zone: {self.root} (open)")
        self.assertIn("vendor/model:free", ranked)
        self.assertNotIn("zones file:", ranked)

    def test_a_bare_list_closes_exactly_the_declared_paths(self):
        closed = os.path.join(self.root, "vault", "private")
        opened = os.path.join(self.root, "vault", "notes")
        os.makedirs(closed)
        os.makedirs(opened)
        self.write_zones({"zones": [closed]})

        blocked, _, code = self.run_cli(
            "--assert-allowed", "--model", "vendor/model:free",
            "--working-dir", closed)
        self.assertEqual(code, 0)
        self.assertEqual(self.zone_line(blocked), f"zone: {closed} (closed)")
        self.assertIn("blocked: free-use zone", blocked)

        allowed, _, code = self.run_cli(
            "--assert-allowed", "--model", "vendor/model:free", "--plain",
            "--working-dir", opened)
        self.assertEqual(code, 0)
        self.assertEqual(self.zone_line(allowed), f"zone: {opened} (open)")
        self.assertIn("allowed: vendor/model:free", allowed)

    def test_an_old_schema_file_exits_4_and_writes_nothing(self):
        # The retired per-entry posture key: the reader refuses with status
        # 4, names the offending entry and shows the one-line new form.
        old = json.dumps({"zones": [{"path": os.path.join(self.root, "x"),
                                     "free": "closed"}]})
        path = self.write_raw_zones(old)
        with open(path, "rb") as f:
            before = f.read()

        out, err, code = self.run_cli("--status", "--working-dir", self.root)

        self.assertEqual(code, 4)
        self.assertIn("zone #1", err)
        self.assertIn('{"zones": ["', err)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)   # nothing is written

        # The retired top-level default key is named too.
        self.write_raw_zones(json.dumps({"zones": [],
                                         "default": "closed"}))
        _, err, code = self.run_cli("--status", "--working-dir", self.root)
        self.assertEqual(code, 4)
        self.assertIn("default", err)
        self.assertIn('{"zones": ["', err)

    def test_a_ranking_run_refuses_an_old_schema_file_with_4(self):
        # The same config error on the ranking path: status 4, nothing on
        # stdout, the offending entry and the one-line form on stderr.
        old = json.dumps({"zones": [{"path": os.path.join(self.root, "x"),
                                     "free": "closed"}]})
        path = self.write_raw_zones(old)
        with open(path, "rb") as f:
            before = f.read()

        out, err, code = self.run_cli("--domain", "writing", "--working-dir",
                                      self.root)

        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertIn("zone #1", err)
        self.assertIn('{"zones": ["', err)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_a_closed_repository_covers_its_worktrees(self):
        # Stricter-of-two kept: declaring the repository covers a linked
        # worktree, so the exception cannot be bypassed by checking the same
        # content out elsewhere. Real git, local only.
        if not shutil.which("git"):
            self.skipTest("git is not installed")
        repo = os.path.join(self.root, "repo")
        worktree = os.path.join(self.root, "wt")
        os.makedirs(repo)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.path.join(self.root, "git-config"),
                   GIT_CONFIG_SYSTEM=os.path.join(self.root, "git-config"),
                   GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                   GIT_AUTHOR_NAME="Fixture",
                   GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture",
                   GIT_COMMITTER_EMAIL="fixture@example.invalid")
        open(env["GIT_CONFIG_GLOBAL"], "w").close()

        def git(cwd, *args):
            completed = subprocess.run(["git", "-C", cwd, *args], env=env,
                                       capture_output=True, text=True,
                                       encoding="utf-8", errors="replace")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return completed.stdout

        git(repo, "init", "-q")
        git(repo, "commit", "--allow-empty", "-qm", "seed")
        git(repo, "worktree", "add", worktree, "-b", "wt")
        # Only the repository is declared: the worktree itself is undeclared.
        self.write_zones({"zones": [repo]})

        out, _, code = self.run_cli(
            "--assert-allowed", "--model", "vendor/model:free",
            "--working-dir", worktree)

        self.assertEqual(code, 0)
        self.assertEqual(self.zone_line(out), f"zone: {repo} (closed)")
        self.assertIn("blocked: free-use zone", out)

    def test_the_json_zone_object_carries_the_binary_posture(self):
        out, err, code = self.run_cli("--status", "--json", "--working-dir",
                                      self.root, zones_absent=True)

        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(set(payload["zone"]),
                         {"path", "posture", "declared", "resolved"})
        self.assertEqual(payload["zone"]["posture"], "open")
        self.assertNotIn("regime", payload["zone"])
        # Declared closed: the same key set, the other posture.
        self.write_zones({"zones": [self.root]})
        out, _, code = self.run_cli("--status", "--json", "--working-dir",
                                    self.root)
        self.assertEqual(code, 0)
        zone = json.loads(out)["zone"]
        self.assertEqual(zone["posture"], "closed")
        self.assertEqual(zone["declared"], self.root)
        self.assertNotIn("regime", zone)

    def test_a_closed_path_drops_remote_free_rows_at_source(self):
        closed = os.path.join(self.root, "closed")
        os.makedirs(closed)
        self.write_zones({"zones": [closed]})
        world = build_world()
        world["models"].append(make_model("vendor/model:free", "0", "0", "0"))
        world["classifications"]["classifications"][0]["models"].append(
            {"id": "vendor/model:free", "tag_usage_share": 0.5})

        out, _, code = self.run_cli("--domain", "writing", "--working-dir",
                                    closed, world=world)

        self.assertEqual(code, 0)
        self.assertEqual(self.zone_line(out), f"zone: {closed} (closed)")
        self.assertNotIn("vendor/model:free", out)

    def test_no_printed_zone_ever_says_sensitive(self):
        # Sensitivity is a shape property: `--sensitive` states the shape,
        # and the zone line stays the binary posture.
        self.write_zones({"zones": []})
        out, _, code = self.run_cli("--status", "--sensitive",
                                    "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(self.zone_line(out), f"zone: {self.root} (open)")

        out, _, code = self.run_cli("--assert-allowed", "--sensitive",
                                    "--model", "deepseek/deepseek-v4-pro",
                                    "--working-dir", self.root)
        self.assertEqual(code, 0)
        self.assertNotIn("sensitive", self.zone_line(out))
        self.assertIn("shape: sensitive (via --sensitive)", out)


if __name__ == "__main__":
    unittest.main()
