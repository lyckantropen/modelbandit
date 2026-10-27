"""Tests for free-use zones: the machine-wide file, its resolver, the
origin-aware effective regime and the closed-zone admission gate.

Fixtures only: every test injects its environment and its git runner, so no
test reads this machine's `$HOME`, runs git, or touches the network.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "openrouter-model-router", "scripts"))
import bind  # noqa: E402

HOME = os.path.join(os.sep, "home", "fixture-user") if os.name != "nt" \
    else r"C:\Users\fixture-user"
ENV = {"HOME": HOME, "USERPROFILE": HOME,
       "XDG_CONFIG_HOME": os.path.join(HOME, ".config")}
REPO = os.path.join(HOME, "vault")
PRIVATE = os.path.join(REPO, "private")
NOTES = os.path.join(REPO, "notes")
WORKTREE = os.path.join(HOME, ".worktrees", "t-1")


def zone(path, free):
    return {"path": path, "free": free}


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
    """`zones.json` at the machine's config root, validated loudly."""

    import json as _json

    def write_zones(self, payload):
        return self.write("zones.json", self._json.dumps(payload))

    def test_zones_path_follows_xdg_config_home(self):
        self.assertEqual(bind.zones_path(environ=dict(ENV)),
                         os.path.join(ENV["XDG_CONFIG_HOME"], "modelrouter",
                                      "zones.json"))

    def test_zones_path_falls_back_to_dot_config(self):
        environ = {"HOME": HOME, "USERPROFILE": HOME}
        self.assertEqual(bind.zones_path(environ=environ),
                         os.path.join(HOME, ".config", "modelrouter",
                                      "zones.json"))

    def test_missing_file_means_the_default_everywhere(self):
        self.assertEqual(
            bind.load_zones(os.path.join(self.root, "absent.json")),
            {"zones": [], "default": "closed"})

    def test_loads_zones_and_the_declared_default(self):
        path = self.write_zones({"zones": [zone(PRIVATE, "closed"),
                                           zone(NOTES, "sensitive")],
                                 "default": "open"})
        self.assertEqual(bind.load_zones(path),
                         {"zones": [zone(PRIVATE, "closed"),
                                    zone(NOTES, "sensitive")],
                          "default": "open"})

    def test_unknown_top_level_key_fails_loudly(self):
        path = self.write_zones({"zones": [], "defaults": "open"})
        with self.assertRaisesRegex(SystemExit, "defaults"):
            bind.load_zones(path)

    def test_zones_must_be_a_list(self):
        path = self.write_zones({"zones": {"path": PRIVATE, "free": "closed"}})
        with self.assertRaisesRegex(SystemExit, "zones"):
            bind.load_zones(path)

    def test_invalid_regime_names_the_entry_index(self):
        path = self.write_zones({"zones": [zone(PRIVATE, "closed"),
                                           zone(NOTES, "opened")]})
        with self.assertRaisesRegex(SystemExit, "zone #2"):
            bind.load_zones(path)
        with self.assertRaisesRegex(SystemExit, "opened"):
            bind.load_zones(path)

    def test_invalid_default_fails_loudly(self):
        path = self.write_zones({"zones": [], "default": "shut"})
        with self.assertRaisesRegex(SystemExit, "default"):
            bind.load_zones(path)

    def test_zone_path_must_be_a_non_empty_string(self):
        for payload in ({"zones": [zone(7, "closed")]},
                        {"zones": [zone("", "closed")]},
                        {"zones": [{"free": "closed"}]}):
            with self.subTest(payload=payload):
                path = self.write_zones(payload)
                with self.assertRaisesRegex(SystemExit, "zone #1"):
                    bind.load_zones(path)

    def test_unknown_keys_inside_an_entry_name_the_index(self):
        path = self.write_zones({"zones": [{"path": PRIVATE, "free": "closed",
                                            "reason": "vault"}]})
        with self.assertRaisesRegex(SystemExit, "zone #1"):
            bind.load_zones(path)

    def test_a_zone_entry_must_be_an_object(self):
        path = self.write_zones({"zones": ["not-a-zone"]})
        with self.assertRaisesRegex(SystemExit, "zone #1"):
            bind.load_zones(path)


class DuplicateZoneTests(TempDirMixin):
    """Two entries naming the same normalised path stop loudly: last-wins
    would silently reopen a closed declaration — the one direction a
    fail-closed resolver must never take."""

    import json as _json

    def write_zones(self, payload):
        return self.write("zones.json", self._json.dumps(payload))

    def load(self, payload):
        return bind.load_zones(self.write_zones(payload))

    def test_an_identical_path_declared_twice_stops(self):
        payload = {"zones": [zone(PRIVATE, "closed"), zone(PRIVATE, "open")]}
        with self.assertRaisesRegex(SystemExit, r"zone #2 .* zone #1"):
            self.load(payload)

    def test_the_stop_names_the_source_and_the_path(self):
        payload = {"zones": [zone(PRIVATE, "closed"), zone(PRIVATE, "sensitive")]}
        with self.assertRaisesRegex(SystemExit, "zones.json"):
            self.load(payload)
        with self.assertRaisesRegex(SystemExit, "private"):
            self.load(payload)

    def test_a_path_that_only_normalises_the_same_stops(self):
        twin = PRIVATE + os.sep + "."
        payload = {"zones": [zone(PRIVATE, "closed"), zone(twin, "open")]}
        with self.assertRaisesRegex(SystemExit, r"zone #2 .* zone #1"):
            self.load(payload)

    def test_paths_fold_case_where_the_platform_does(self):
        payload = {"zones": [zone(PRIVATE, "closed"),
                             zone(PRIVATE.upper(), "open")]}
        if os.name == "nt":
            with self.assertRaisesRegex(SystemExit, "zone #2"):
                self.load(payload)
        else:
            self.assertEqual(len(self.load(payload)["zones"]), 2)


class ZoneResolverTests(unittest.TestCase):
    """Longest declared prefix wins; `~` and variables expand; the comparison
    follows this platform; anything uncovered takes the default."""

    ZONES = {"zones": [zone(REPO, "open"), zone(NOTES, "sensitive"),
                       zone(PRIVATE, "closed")],
             "default": "closed"}

    def resolve(self, folder, zones=None):
        return bind.resolve_zone(folder, zones or self.ZONES, environ=dict(ENV))

    def test_longest_prefix_wins(self):
        self.assertEqual(self.resolve(os.path.join(PRIVATE, "keys", "a.md")),
                         bind.Zone(path=PRIVATE, regime="closed"))
        self.assertEqual(self.resolve(os.path.join(NOTES, "todo.md")),
                         bind.Zone(path=NOTES, regime="sensitive"))
        self.assertEqual(self.resolve(os.path.join(REPO, "README.md")),
                         bind.Zone(path=REPO, regime="open"))

    def test_no_match_uses_the_default(self):
        self.assertEqual(self.resolve(os.path.join(HOME, "elsewhere", "x")),
                         bind.Zone(path=None, regime="closed"))
        open_by_default = {"zones": [], "default": "open"}
        self.assertEqual(self.resolve(PRIVATE, open_by_default),
                         bind.Zone(path=None, regime="open"))

    def test_a_declared_path_matches_the_folder_itself(self):
        self.assertEqual(self.resolve(PRIVATE),
                         bind.Zone(path=PRIVATE, regime="closed"))

    def test_a_prefix_must_end_on_a_path_boundary(self):
        sibling = PRIVATE + "-ish"
        self.assertEqual(self.resolve(os.path.join(sibling, "x")),
                         bind.Zone(path=REPO, regime="open"))

    def test_tilde_expands_against_the_given_environment(self):
        zones = {"zones": [zone("~/vault/private", "closed")],
                 "default": "open"}
        self.assertEqual(self.resolve(os.path.join(PRIVATE, "x"), zones),
                         bind.Zone(path="~/vault/private", regime="closed"))

    def test_environment_variables_expand(self):
        zones = {"zones": [zone("${VAULT}/private", "closed"),
                           zone("$VAULT/notes", "sensitive")],
                 "default": "open"}
        environ = dict(ENV, VAULT=REPO)
        self.assertEqual(
            bind.resolve_zone(os.path.join(PRIVATE, "x"), zones,
                              environ=environ),
            bind.Zone(path="${VAULT}/private", regime="closed"))
        self.assertEqual(
            bind.resolve_zone(os.path.join(NOTES, "x"), zones, environ=environ),
            bind.Zone(path="$VAULT/notes", regime="sensitive"))

    def test_an_unknown_variable_is_left_as_written(self):
        zones = {"zones": [zone("$NOT_SET_ANYWHERE/x", "closed")],
                 "default": "open"}
        self.assertEqual(self.resolve(os.path.join(REPO, "x"), zones),
                         bind.Zone(path=None, regime="open"))

    def test_paths_compare_case_insensitively_where_the_platform_does(self):
        zones = {"zones": [zone(PRIVATE.upper(), "closed")], "default": "open"}
        resolved = self.resolve(PRIVATE, zones)
        if os.name == "nt":
            self.assertEqual(resolved, bind.Zone(path=PRIVATE.upper(),
                                                 regime="closed"))
        else:
            self.assertEqual(resolved, bind.Zone(path=None, regime="open"))

    def test_stricter_orders_open_sensitive_closed(self):
        self.assertEqual(bind.stricter("open", "sensitive"), "sensitive")
        self.assertEqual(bind.stricter("sensitive", "closed"), "closed")
        self.assertEqual(bind.stricter("closed", "open"), "closed")
        self.assertEqual(bind.stricter("open", "open"), "open")

    def test_stricter_rejects_an_unknown_regime(self):
        with self.assertRaisesRegex(SystemExit, "shut"):
            bind.stricter("open", "shut")

    def test_declared_regimes_are_the_three_levels(self):
        self.assertEqual(bind.REGIMES, ("open", "sensitive", "closed"))
        self.assertEqual(bind.DEFAULT_REGIME, "closed")


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

    def zones(self, entries, default="open"):
        return {"zones": [{"path": path, "free": free}
                          for path, free in entries],
                "default": default}

    @staticmethod
    def no_git(args):
        raise OSError("not a repository")

    def test_a_link_inside_an_open_zone_into_a_closed_area_is_judged_closed(self):
        link = os.path.join(self.open_dir, "shortcut")
        self.assertTrue(make_link(link, self.closed_dir))
        zones = self.zones([(self.open_dir, "open"),
                            (self.closed_dir, "closed")])
        self.assertEqual(
            bind.effective_zone(link, zones=zones, run=self.no_git),
            bind.Zone(path=self.closed_dir, regime="closed"))

    def test_a_link_outside_the_open_zone_pointing_at_it_is_judged_open(self):
        link = os.path.join(self.root, "elsewhere", "to-open")
        os.makedirs(os.path.dirname(link))
        self.assertTrue(make_link(link, self.open_dir))
        zones = self.zones([(self.open_dir, "open")])
        self.assertEqual(
            bind.effective_zone(link, zones=zones, run=self.no_git),
            bind.Zone(path=self.open_dir, regime="open"))

    def test_a_declaration_spelled_through_a_link_names_the_resolved_place(self):
        # The declaration names the link; the zone governs the folder it
        # reaches, and the header says so instead of the link's spelling.
        vault = os.path.join(self.root, "vault")
        os.makedirs(vault)
        link = os.path.join(self.root, "vault-link")
        self.assertTrue(make_link(link, vault))
        resolved = bind.resolve_zone(vault, self.zones([(link, "open")],
                                                      default="closed"))
        self.assertEqual(resolved.path, link)
        self.assertEqual(resolved.regime, "open")
        self.assertEqual(bind.zone_label(resolved),
                         f"{vault} (open) (declared: {link})")

    def test_a_link_out_of_every_declared_place_reports_the_resolved_place(self):
        # The spelled path sits inside the open zone; the place it reaches is
        # undeclared and closed. `undeclared (closed)` alone would read as if
        # the open zone had been left by choice.
        link = os.path.join(self.open_dir, "shortcut")
        elsewhere = os.path.join(self.root, "elsewhere")
        os.makedirs(elsewhere)
        self.assertTrue(make_link(link, elsewhere))
        resolved = bind.resolve_zone(link, self.zones([(self.open_dir, "open")],
                                                      default="closed"))
        self.assertIsNone(resolved.path)
        self.assertEqual(resolved.regime, "closed")
        self.assertEqual(bind.zone_label(resolved),
                         f"{elsewhere} (closed) (undeclared)")

    def test_a_declared_zone_path_that_does_not_exist_yet_still_applies(self):
        # Resolution is not existence: a zone declared ahead of its folder
        # validates and compares against the paths spelled under it.
        ghost = os.path.join(self.root, "not-built-yet")
        zones = self.zones([(ghost, "closed")])
        self.assertEqual(bind.validate_zones(dict(zones))["zones"],
                         [{"path": ghost, "free": "closed"}])
        self.assertEqual(
            bind.resolve_zone(os.path.join(ghost, "x"), zones),
            bind.Zone(path=ghost, regime="closed"))

    def test_two_declarations_of_one_place_through_a_link_stop_loudly(self):
        # The link and its target are one place: declaring it open in one
        # spelling and closed in the other is the duplicate a fail-closed
        # resolver stops, not a last-wins reopening.
        link = os.path.join(self.root, "vault-link")
        self.assertTrue(make_link(link, self.closed_dir))
        payload = {"zones": [{"path": self.closed_dir, "free": "closed"},
                             {"path": link, "free": "open"}],
                   "default": "open"}
        with self.assertRaisesRegex(SystemExit, "zone #2"):
            bind.validate_zones(payload)


class OriginZoneTests(unittest.TestCase):
    """A worktree carries the posture of the repository it came from."""

    ZONES = {"zones": [zone(REPO, "closed"), zone(WORKTREE, "open")],
             "default": "closed"}

    def test_git_common_dir_resolves_to_the_origin_repository(self):
        self.assertEqual(
            bind.git_origin(WORKTREE,
                            run=lambda args: os.path.join(REPO, ".git") + "\n"),
            REPO)

    def test_a_relative_common_dir_resolves_against_the_folder(self):
        self.assertEqual(bind.git_origin(REPO, run=lambda args: ".git\n"), REPO)

    def test_git_missing_or_failing_answers_none(self):
        def boom(args):
            raise OSError("not a git repository")
        self.assertIsNone(bind.git_origin(WORKTREE, run=boom))
        self.assertIsNone(bind.git_origin(WORKTREE, run=lambda args: "\n"))

    def test_effective_zone_takes_the_stricter_of_folder_and_origin(self):
        # The worktree declares itself open; its origin repository is closed.
        zone_here = bind.effective_zone(
            os.path.join(WORKTREE, "pkg"), zones=self.ZONES,
            run=lambda args: os.path.join(REPO, ".git"), environ=dict(ENV))
        self.assertEqual(zone_here, bind.Zone(path=REPO, regime="closed"))

    def test_the_folder_zone_answers_when_it_is_the_stricter(self):
        zones = {"zones": [zone(REPO, "open"),
                           zone(os.path.join(WORKTREE, "private"), "closed")],
                 "default": "open"}
        self.assertEqual(
            bind.effective_zone(os.path.join(WORKTREE, "private"), zones=zones,
                                run=lambda args: os.path.join(REPO, ".git"),
                                environ=dict(ENV)),
            bind.Zone(path=os.path.join(WORKTREE, "private"), regime="closed"))

    def test_git_absent_leaves_the_working_folder_zone_alone(self):
        def boom(args):
            raise OSError("git is not installed")
        self.assertEqual(
            bind.effective_zone(WORKTREE, zones=self.ZONES, run=boom,
                                environ=dict(ENV)),
            bind.Zone(path=WORKTREE, regime="open"))

    def test_an_undeclared_folder_inherits_its_closed_origin(self):
        # The worktree lives outside anything declared; its repository is
        # declared closed, so the run is closed and the origin answers for it.
        zones = {"zones": [zone(REPO, "closed")], "default": "open"}
        self.assertEqual(
            bind.effective_zone(os.path.join(HOME, "elsewhere", "wt"),
                                zones=zones,
                                run=lambda args: os.path.join(REPO, ".git"),
                                environ=dict(ENV)),
            bind.Zone(path=REPO, regime="closed"))

    def test_an_undeclared_folder_stays_closed_even_under_an_open_origin(self):
        # Undeclared is closed, and stricter wins: a worktree inherits a
        # closed repository's posture, but a machine that wants an open
        # repository's worktrees usable must declare the worktree root open.
        zones = {"zones": [zone(REPO, "open")], "default": "closed"}
        self.assertEqual(
            bind.effective_zone(os.path.join(HOME, "elsewhere", "wt"),
                                zones=zones,
                                run=lambda args: os.path.join(REPO, ".git"),
                                environ=dict(ENV)),
            bind.Zone(path=None, regime="closed"))

    def test_equal_regimes_report_the_working_folder(self):
        zones = {"zones": [zone(REPO, "closed")], "default": "closed"}
        self.assertEqual(
            bind.effective_zone(os.path.join(HOME, "tmp", "x"), zones=zones,
                                run=lambda args: os.path.join(HOME, "tmp", ".git"),
                                environ=dict(ENV)),
            bind.Zone(path=None, regime="closed"))

    def test_an_origin_equal_to_the_folder_is_not_asked_twice(self):
        calls = []

        def run(args):
            calls.append(args)
            return os.path.join(REPO, ".git")
        bind.effective_zone(REPO, zones=self.ZONES, run=run,
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
        self.assertEqual(bind.git_origin(SUBMODULE, run=module_run()),
                         SUBMODULE)

    def test_a_worktree_of_the_submodule_resolves_to_the_submodule_root(self):
        self.assertEqual(bind.git_origin(SUB_WORKTREE, run=module_run()),
                         SUBMODULE)

    def test_an_unset_core_worktree_falls_back_to_the_toplevel(self):
        self.assertEqual(
            bind.git_origin(SUBMODULE, run=module_run(worktree=None)),
            SUBMODULE)

    def test_an_unanswerable_module_git_dir_answers_none(self):
        # neither core.worktree nor a toplevel: no origin, not the bogus
        # `.git/modules` path a bare parent would give.
        self.assertIsNone(
            bind.git_origin(SUBMODULE,
                            run=module_run(worktree=None, toplevel=None)))

    def test_a_plain_common_dir_is_never_rerouted(self):
        self.assertEqual(bind.git_origin(REPO, run=lambda args: ".git\n"),
                         REPO)

    def test_a_folder_inside_the_submodule_is_governed_by_its_zone(self):
        # the zone declared on the submodule's path covers the folder; the
        # bogus `.git/modules` origin used to out-vote it with the closed
        # default.
        zones = {"zones": [zone(SUBMODULE, "open")], "default": "closed"}
        self.assertEqual(
            bind.effective_zone(os.path.join(SUBMODULE, "deep"), zones=zones,
                                run=module_run(), environ=dict(ENV)),
            bind.Zone(path=SUBMODULE, regime="open"))

    def test_a_worktree_of_the_submodule_honours_the_submodule_zone(self):
        zones = {"zones": [zone(SUBMODULE, "open"), zone(SUB_WORKTREE, "open")],
                 "default": "closed"}
        self.assertEqual(
            bind.effective_zone(SUB_WORKTREE, zones=zones, run=module_run(),
                                environ=dict(ENV)),
            bind.Zone(path=SUB_WORKTREE, regime="open"))


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
        zones = {"zones": [zone(self.sub, "open")], "default": "closed"}
        self.assertEqual(bind.effective_zone(self.sub, zones=zones),
                         bind.Zone(path=self.sub, regime="open"))

    def test_a_folder_inside_the_submodule_honours_the_declaration(self):
        deep = os.path.join(self.sub, "deep")
        os.makedirs(deep)
        zones = {"zones": [zone(self.sub, "open")], "default": "closed"}
        self.assertEqual(bind.effective_zone(deep, zones=zones),
                         bind.Zone(path=self.sub, regime="open"))

    def test_a_worktree_of_the_submodule_honours_the_submodule_zone(self):
        zones = {"zones": [zone(self.sub, "open"), zone(self.sub_wt, "open")],
                 "default": "closed"}
        self.assertEqual(bind.effective_zone(self.sub_wt, zones=zones),
                         bind.Zone(path=self.sub_wt, regime="open"))

    def test_a_plain_repo_resolves_itself(self):
        zones = {"zones": [zone(self.super_root, "open")], "default": "closed"}
        self.assertEqual(bind.effective_zone(self.super_root, zones=zones),
                         bind.Zone(path=self.super_root, regime="open"))

    def test_a_plain_worktree_still_inherits_its_repository(self):
        zones = {"zones": [zone(self.super_root, "closed"),
                           zone(self.super_wt, "open")],
                 "default": "closed"}
        self.assertEqual(bind.effective_zone(self.super_wt, zones=zones),
                         bind.Zone(path=self.super_root, regime="closed"))

    def test_a_closed_submodule_blocks_remote_free_and_admits_local(self):
        zones = {"zones": [zone(self.sub, "closed")], "default": "open"}
        resolved = bind.effective_zone(self.sub, zones=zones)
        self.assertEqual(resolved, bind.Zone(path=self.sub, regime="closed"))
        self.assertIn("remote free route is prohibited",
                      bind.zone_block("z-ai/glm-5.4:free", resolved, policy={}))
        local_policy = {"free_models": {"qwen3-coder-30b": {"exposure": "local"}}}
        self.assertIsNone(bind.zone_block("qwen3-coder-30b", resolved,
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
        closed = bind.Zone(path="z", regime="closed")
        self.assertIn("remote free route is prohibited",
                      bind.zone_block("qwen/qwen3-coder-30b:free", closed,
                                      policy=policy))
        sensitive = bind.Zone(path="z", regime="sensitive")
        self.assertIn("exposed (trains)",
                      bind.zone_block("qwen/qwen3-coder-30b:free", sensitive,
                                      policy=policy, sensitive=True))

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
        zones = {"zones": [zone(self.super_root, "closed")], "default": "open"}
        self.assertEqual(
            bind.effective_zone(link, zones=zones),
            bind.Zone(path=self.super_root, regime="closed"))


def candidate(mid, *, exposure="no-retention", is_free=False, local=False):
    return bind.Candidate(id=mid, exposure=exposure, is_free=is_free,
                          local=local)


def shape(regime, *, sensitive=False):
    return bind.Shape(sensitive=sensitive, regime=regime)


class ClosedZoneGateTests(unittest.TestCase):
    """closed: no remote free route at all, and everything sensitive refuses —
    locally served models stay. open and sensitive behave exactly as today."""

    def test_closed_excludes_an_openrouter_free_route(self):
        decision = bind.admit(shape("closed"),
                              candidate("z-ai/glm-5.4:free", is_free=True))
        self.assertFalse(decision.admitted)
        self.assertIn("remote free route is prohibited", decision.reason)

    def test_closed_excludes_a_harness_free_route(self):
        for mid in ("opencode/glm-5.3-flash-free", "opencode/nemotron-3-ultra-free"):
            with self.subTest(mid=mid):
                self.assertFalse(bind.admit(shape("closed"),
                                            candidate(mid, is_free=True)).admitted)

    def test_closed_admits_a_locally_served_model(self):
        decision = bind.admit(shape("closed"),
                              candidate("qwen3-coder-30b", exposure="local",
                                        is_free=True, local=True))
        self.assertTrue(decision.admitted)

    def test_closed_admits_a_paid_no_retention_route(self):
        self.assertTrue(bind.admit(
            shape("closed"),
            candidate("deepseek/deepseek-v4-pro", exposure="no-retention")).admitted)

    def test_closed_excludes_an_exposed_paid_route(self):
        # closed implies sensitive: the exposed route a sensitive zone refuses
        # is refused here too, whatever it costs.
        paid_trains = candidate("deepseek/deepseek-v4-pro", exposure="trains")
        self.assertFalse(bind.admit(shape("sensitive"), paid_trains).admitted)
        self.assertFalse(bind.admit(shape("closed"), paid_trains).admitted)

    def test_open_is_todays_behaviour(self):
        self.assertTrue(bind.admit(
            shape("open"), candidate("z-ai/glm-5.4:free", is_free=True)).admitted)
        self.assertTrue(bind.admit(
            shape("open"), candidate("opencode/x-free", is_free=True)).admitted)

    def test_sensitive_is_todays_sensitive(self):
        # Exposure decides, as it does for --sensitive today: exposed routes
        # out, no-retention free routes in — no zone exclusion on top.
        self.assertFalse(bind.admit(
            shape("sensitive"),
            candidate("z-ai/glm-5.4:free", exposure="trains", is_free=True)
        ).admitted)
        self.assertTrue(bind.admit(
            shape("sensitive"),
            candidate("opencode/x-free", is_free=True)).admitted)

    def test_sensitive_zone_matches_the_sensitive_flag(self):
        self.assertEqual(bind.admit(shape("sensitive"),
                                    candidate("a/b:free", is_free=True)),
                         bind.admit(shape("open", sensitive=True),
                                    candidate("a/b:free", is_free=True)))

    def test_closed_excludes_free_that_sensitive_would_admit(self):
        no_retention_free = candidate("opencode/x-free", is_free=True)
        self.assertTrue(bind.admit(shape("sensitive"), no_retention_free).admitted)
        self.assertFalse(bind.admit(shape("closed"), no_retention_free).admitted)

    def test_the_shape_defaults_to_open(self):
        self.assertEqual(bind.Shape(), bind.Shape(sensitive=False, regime="open"))

    def test_the_sensitive_flag_still_applies_inside_a_closed_zone(self):
        # The flag tightens content posture and cannot move the zone: both
        # exclusions hold at once.
        regime = bind.shape_regime(bind.Zone(PRIVATE, "closed"), sensitive=True)
        self.assertEqual(regime, "closed")
        paid_trains = candidate("deepseek/x", exposure="trains")
        self.assertFalse(bind.admit(bind.Shape(sensitive=True, regime=regime),
                                    paid_trains).admitted)

    def test_the_flag_cannot_loosen_a_closed_zone(self):
        self.assertEqual(bind.shape_regime(bind.Zone(PRIVATE, "closed"),
                                           sensitive=True), "closed")
        self.assertEqual(bind.shape_regime(bind.Zone(PRIVATE, "closed"),
                                           sensitive=False), "closed")

    def test_the_flag_tightens_an_open_zone(self):
        self.assertEqual(bind.shape_regime(bind.Zone(REPO, "open"),
                                           sensitive=True), "sensitive")
        self.assertEqual(bind.shape_regime(bind.Zone(REPO, "open"),
                                           sensitive=False), "open")
        self.assertEqual(bind.shape_regime(bind.Zone(NOTES, "sensitive"),
                                           sensitive=False), "sensitive")

    def test_the_gate_is_on_the_admission_path(self):
        self.assertIn(bind.zone_gate, bind.GATES)


class RegimeOrderingTests(unittest.TestCase):
    """open < sensitive < closed, honestly: a stricter regime forbids
    everything every milder one forbids, in every dimension."""

    MATRIX = (
        candidate("z-ai/glm-5.4:free", exposure="trains", is_free=True),
        candidate("opencode/x-free", exposure="no-retention", is_free=True),
        candidate("qwen3-coder-30b", exposure="local", is_free=True, local=True),
        candidate("deepseek/x", exposure="no-retention"),
        candidate("deepseek/x", exposure="trains"),
    )

    def test_regime_at_least_orders_the_three_levels(self):
        self.assertTrue(bind.regime_at_least("sensitive", "open"))
        self.assertTrue(bind.regime_at_least("closed", "sensitive"))
        self.assertTrue(bind.regime_at_least("closed", "open"))
        self.assertFalse(bind.regime_at_least("open", "sensitive"))
        self.assertFalse(bind.regime_at_least("sensitive", "closed"))

    def test_regime_at_least_rejects_an_unknown_regime(self):
        with self.assertRaisesRegex(SystemExit, "shut"):
            bind.regime_at_least("shut", "open")

    def test_a_stricter_regime_dominates_every_milder_one(self):
        for candidate_ in self.MATRIX:
            with self.subTest(candidate=candidate_):
                admitted = [bind.admit(shape(regime), candidate_).admitted
                            for regime in bind.REGIMES]
                self.assertLessEqual(int(admitted[2]), int(admitted[1]))
                self.assertLessEqual(int(admitted[1]), int(admitted[0]))

    def test_the_zone_prohibition_is_the_zone_clause_alone(self):
        # The source filter drops what the zone forbids; Exposure exclusions
        # stay in the table, marked with their reason.
        self.assertIn("remote free route is prohibited",
                      bind.zone_prohibition(
                          shape("closed"),
                          candidate("a/b:free", is_free=True)))
        self.assertIsNone(bind.zone_prohibition(
            shape("closed"), candidate("a/b", exposure="trains")))
        for regime in ("open", "sensitive"):
            with self.subTest(regime=regime):
                self.assertIsNone(bind.zone_prohibition(
                    shape(regime), candidate("a/b:free", is_free=True)))

    def test_the_regime_prohibition_is_the_pre_flight_yardstick(self):
        # What the guard refuses: the zone's free clause and the Exposure
        # clause a regime at least as strict as sensitive states.
        exposed_paid = candidate("deepseek/x", exposure="trains")
        remote_free = candidate("a/b:free", is_free=True)
        self.assertIsNone(bind.regime_prohibition(shape("open"), exposed_paid))
        self.assertIn("exposed",
                      bind.regime_prohibition(shape("sensitive"), exposed_paid))
        self.assertIn("exposed",
                      bind.regime_prohibition(shape("closed"), exposed_paid))
        self.assertIn("remote free route is prohibited",
                      bind.regime_prohibition(shape("closed"), remote_free))
        self.assertIsNone(bind.regime_prohibition(shape("sensitive"),
                                                  remote_free))


if __name__ == "__main__":
    unittest.main()
