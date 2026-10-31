"""Kind validation at the free catalog's policy boundary.

The free catalog may carry only Free-route servings — a harness
(`opencode/*`) model, a free-slug (`:free`) route, or a locally served id.
An entry whose kind is a plan serving (the `opencode-go/*` namespace, which
has its own catalog) or a market serving is refused at load with a loud
config error naming the entry, so the hardcoded $0 of a Free record can
never price one. Kind is decided from the prefix and the serving alone;
an unknown namespace fails closed. The load stays a single config error
(status 4); nothing is half-loaded.

The pinned suites key an OpenRouter `:free` route by its family prefix
(`vendor/model` for `vendor/model:free`), so a bare two-segment prefix is
the free-slug family the catalog has always accepted.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


def entry(exposure="trains", **extra):
    """One catalog entry's curated facts, with a window always present."""
    return {"context_length": 262_144, "exposure": exposure, **extra}


class FreeCatalogKindTests(unittest.TestCase):
    def test_plan_namespace_is_refused_whatever_its_exposure(self):
        # Namespace first: a plan serving has its own catalog, so the free
        # catalog refuses it however the entry is annotated — no policy edit
        # can make a plan route look Free.
        for exposure in ("no-retention", "trains", "local"):
            with self.subTest(exposure=exposure), self.assertRaisesRegex(
                    SystemExit, r"free_models\.opencode-go/plan-model"):
                modelbandit.load_free_models({"free_models": {
                    "opencode-go/plan-model": entry(exposure)}})

    def test_market_serving_prefix_is_refused_at_load(self):
        with self.assertRaisesRegex(
                SystemExit, r"free_models\.openrouter/anthropic/claude"):
            modelbandit.load_free_models({"free_models": {
                "openrouter/anthropic/claude": entry("no-retention")}})

    def test_namespace_outside_every_kind_is_refused_fail_closed(self):
        with self.assertRaisesRegex(
                SystemExit, r"free_models\.vendor/team/model"):
            modelbandit.load_free_models({"free_models": {
                "vendor/team/model": entry()}})

    def test_free_slug_and_harness_entries_load_exactly_as_today(self):
        catalog = {
            "opencode/flash": entry("no-retention", summary_ref="family/flash"),
            "vendor/model:free": entry(),
        }
        self.assertEqual(modelbandit.load_free_models({"free_models": catalog}),
                         catalog)

    def test_market_family_prefix_still_loads_for_its_free_slug(self):
        # The pinned suites key an OpenRouter ':free' route by its family
        # prefix; that shape keeps loading, its curated facts intact.
        catalog = {"vendor/model": entry("no-retention",
                                         summary_ref="family/model")}
        self.assertEqual(modelbandit.load_free_models({"free_models": catalog}),
                         catalog)

    def test_local_exposure_on_a_prefix_no_remote_namespace_claims_loads(self):
        # The `local` annotation supplies the local serving fact for a prefix
        # no remote namespace claims, so a locally served slash-shaped id
        # keeps its curated window and summary.
        catalog = {"qwen/qwen3-4b": entry("local", summary_ref="family/qwen")}
        self.assertEqual(modelbandit.load_free_models({"free_models": catalog}),
                         catalog)

    def test_a_refused_entry_after_a_good_one_stops_the_whole_load(self):
        # Nothing half-loaded: a later bad entry still stops the run, so the
        # caller never sees a partial catalog.
        catalog = {"opencode/flash": entry("no-retention"),
                   "opencode-go/plan-model": entry("trains")}
        with self.assertRaises(SystemExit):
            modelbandit.load_free_models({"free_models": catalog})


class LocalExposureContradictionTests(unittest.TestCase):
    def test_local_exposure_on_a_remote_namespace_stays_a_contradiction(self):
        # Unchanged: `opencode/*` and `:free` are remote serving identities,
        # so a `local` label there still stops the run naming the entry,
        # before any kind is read from it.
        for prefix in ("opencode/flash", "vendor/model:free"):
            with self.subTest(prefix=prefix), self.assertRaisesRegex(
                    SystemExit, f"free_models.{prefix}.exposure"):
                modelbandit.load_free_models({"free_models": {
                    prefix: entry("local")}})


if __name__ == "__main__":
    unittest.main()
