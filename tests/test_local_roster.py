"""The Local roster loader: loud validation in the style of the curated
catalog loaders (secondary seam per spec #66 Testing Decisions), plus the
band verdicts admission draws from it.

The roster is judgment only — Capability band + prose, keyed by the harness's
own model id (roster-contract.md). A bad band must stop the run naming the
entry, never become a silent default: a guessed band is a judgment nobody
made.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

# The contract's example entry, byte-shaped as the exporter writes it.
CONTRACT_ENTRY = {
    "band": {
        "domains": ["coding", "orchestration"],
        "difficulty": "measured",
        "context_demand": 32768,
    },
    "prose": ("Clean structured work at 30-33 tok/s; fourth practical pick "
              "for agent work."),
    "provenance": {
        "source": "local-llm-bench",
        "dossier": "qwen-qwen3-6-35b-a3b",
        "evidence": "suspected",
        "seeded": True,
        "date": "2026-11-15",
    },
}
MID = "lmstudio/qwen/qwen3.6-35b-a3b"


def roster_file(payload, directory):
    """Write a roster document (the whole file) and return its path."""
    path = os.path.join(directory, modelbandit.ROSTER_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def entries(entries_obj):
    return {"version": 1, "entries": entries_obj}


class RosterLoaderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def load(self, payload):
        path = roster_file(payload, self._tmp.name)
        return modelbandit.load_local_roster(path=path)

    def test_a_valid_roster_loads_its_entries_verbatim(self):
        got = self.load(entries({MID: CONTRACT_ENTRY}))
        self.assertEqual(got, {MID: CONTRACT_ENTRY})

    def test_a_missing_roster_file_is_silent_empty_setup(self):
        absent = os.path.join(self._tmp.name, "no-such-file.json")
        self.assertEqual(modelbandit.load_local_roster(path=absent), {})

    def test_an_unknown_top_level_key_stops_the_run_naming_it(self):
        with self.assertRaisesRegex(
                SystemExit, "unknown top-level key 'entries_v2'"):
            self.load({"version": 1, "entries": {}, "entries_v2": {}})

    def test_the_version_must_be_the_stated_one(self):
        for version in (2, "1", True, None):
            with self.subTest(version=version), self.assertRaisesRegex(
                    SystemExit, "version must be 1"):
                self.load({"version": version, "entries": {}})
        with self.assertRaisesRegex(SystemExit, "version must be 1"):
            self.load({"entries": {}})

    def test_entries_is_required_and_must_be_an_object(self):
        with self.assertRaisesRegex(
                SystemExit, "missing required key: entries"):
            self.load({"version": 1})
        with self.assertRaisesRegex(SystemExit, "entries must be an object"):
            self.load({"version": 1, "entries": []})

    def test_a_key_outside_the_harness_namespace_stops_the_run(self):
        # The roster speaks for harness-invoked ids only — a remote key
        # could never be a candidate it matches anyway, and refusing it at
        # load keeps a roster entry from ever naming a remote serving.
        for key in ("opencode/qwen", "vendor/model", "lmstudio/",
                    "lmstudio//x", "openrouter/lmstudio/qwen"):
            with self.subTest(key=key), self.assertRaisesRegex(
                    SystemExit, f"entries\\.{key}: key must be a harness"):
                self.load(entries({key: CONTRACT_ENTRY}))

    def edit_entry(self, mutate):
        """A roster whose MID entry is mutated by `mutate` (band untouched)."""
        entry = json.loads(json.dumps(CONTRACT_ENTRY))
        mutate(entry)
        return entries({MID: entry})

    def test_an_entry_may_carry_only_the_band_prose_and_provenance(self):
        with self.assertRaisesRegex(
                SystemExit, f"entries\\.{MID}: unknown key 'window'"):
            self.load(self.edit_entry(lambda e: e.update(window=65536)))
        with self.assertRaisesRegex(
                SystemExit, f"entries\\.{MID} must be an object"):
            self.load(entries({MID: "just prose"}))

    def test_a_malformed_band_stops_the_run_naming_the_entry(self):
        with self.assertRaisesRegex(
                SystemExit, f"missing required key: entries\\.{MID}\\.band"):
            self.load(self.edit_entry(lambda e: e.pop("band")))
        with self.assertRaisesRegex(
                SystemExit, f"entries\\.{MID}\\.band must be an object"):
            self.load(self.edit_entry(lambda e: e.update(band="coding")))
        with self.assertRaisesRegex(
                SystemExit,
                f"entries\\.{MID}\\.band: unknown key 'contexts'"):
            self.load(self.edit_entry(
                lambda e: e["band"].update(contexts=32768)))

    def test_band_fields_are_required(self):
        for field in ("domains", "difficulty", "context_demand"):
            with self.subTest(field=field), self.assertRaisesRegex(
                    SystemExit,
                    f"missing required key: entries\\.{MID}\\.band\\.{field}"):
                self.load(self.edit_entry(lambda e, f=field:
                                          e["band"].pop(f)))

    def test_an_unknown_domain_stops_the_run_naming_the_entry(self):
        with self.assertRaisesRegex(
                SystemExit,
                f"entries\\.{MID}\\.band\\.domains: unknown domain "
                f"'translation'"):
            self.load(self.edit_entry(
                lambda e: e["band"].update(domains=["coding", "translation"])))
        for domains in ("coding", {"coding": True}, [42]):
            with self.subTest(domains=domains), self.assertRaisesRegex(
                    SystemExit, r"band\.domains must be"):
                self.load(self.edit_entry(
                    lambda e, d=domains: e["band"].update(domains=d)))

    def test_a_non_rung_difficulty_stops_the_run(self):
        for rung in ("hard", "MAXIMUM", 3, None):
            with self.subTest(rung=rung), self.assertRaisesRegex(
                    SystemExit,
                    f"entries\\.{MID}\\.band\\.difficulty must be one of"):
                self.load(self.edit_entry(
                    lambda e, r=rung: e["band"].update(difficulty=r)))

    def test_context_demand_must_be_a_positive_integer(self):
        for demand in (0, -1, "32768", 32768.5, True, None):
            with self.subTest(demand=demand), self.assertRaisesRegex(
                    SystemExit,
                    f"entries\\.{MID}\\.band\\.context_demand must be a "
                    f"positive integer"):
                self.load(self.edit_entry(
                    lambda e, d=demand: e["band"].update(context_demand=d)))

    def test_prose_is_required_and_must_be_non_empty(self):
        for prose in ("", 42, ["clean"], None, "   "):
            with self.subTest(prose=prose), self.assertRaisesRegex(
                    SystemExit, f"entries\\.{MID}\\.prose must be a "
                    f"non-empty string"):
                self.load(self.edit_entry(lambda e, p=prose:
                                          e.update(prose=p)))
        with self.assertRaisesRegex(
                SystemExit, f"missing required key: entries\\.{MID}\\.prose"):
            self.load(self.edit_entry(lambda e: e.pop("prose")))

    def test_provenance_is_optional_but_must_be_an_object_when_present(self):
        # Hand-authored entries may omit provenance entirely; the exporter
        # always stamps it. Whatever form it takes, a non-object provenance
        # is a bad type, not a suggestion.
        without = self.edit_entry(lambda e: e.pop("provenance"))
        self.assertEqual(self.load(without)[MID]["band"],
                         CONTRACT_ENTRY["band"])
        with self.assertRaisesRegex(
                SystemExit, f"entries\\.{MID}\\.provenance must be an "
                f"object"):
            self.load(self.edit_entry(lambda e: e.update(provenance="seeded")))

    def test_an_empty_never_deal_band_is_valid(self):
        # The empty domain list is the valid never-deal band: rostered
        # (visible, reported) but admits no ticket.
        never = json.loads(json.dumps(CONTRACT_ENTRY))
        never["band"]["domains"] = []
        self.assertEqual(self.load(entries({MID: never}))[MID], never)

    def test_the_roster_file_sits_beside_zones_json(self):
        self.assertEqual(
            modelbandit.roster_path(environ={"XDG_CONFIG_HOME": "/cfg"}),
            os.path.join("/cfg", "modelbandit", "local-roster.json"))
        self.assertEqual(
            modelbandit.roster_path(
                environ={"XDG_CONFIG_HOME": "", "HOME": "/home/u"}),
            os.path.join("/home/u", ".config", "modelbandit",
                         "local-roster.json"))


if __name__ == "__main__":
    unittest.main()
