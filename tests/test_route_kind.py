"""Route-kind classification and facet contract."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402


class RouteKindClassificationTests(unittest.TestCase):
    def test_known_serving_id_shapes_have_one_route_kind(self):
        cases = (
            ("anthropic/claude", False, "market"),
            ("openrouter/anthropic/claude", False, "market"),
            ("anthropic/claude:free", False, "free-slug"),
            ("opencode/x", False, "harness"),
            ("opencode-go/x", False, "plan"),
            ("vendor/model", True, "local"),
        )
        for model_id, local, expected in cases:
            with self.subTest(model_id=model_id, local=local):
                self.assertEqual(modelbandit.classify_route(model_id, local=local),
                                 expected)

    def test_local_serving_fact_takes_precedence_over_id_shape(self):
        for model_id in ("anthropic/claude", "unknown/model", "malformed"):
            with self.subTest(model_id=model_id):
                self.assertEqual(modelbandit.classify_route(model_id, local=True),
                                 "local")

    def test_unrecognized_and_malformed_ids_fail_closed(self):
        for model_id in (
            "unknown",
            "anthropic",
            "anthropic//claude",
            "anthropic/claude/extra",
            "opencode/",
            "opencode-go/",
            "/model",
        ):
            with self.subTest(model_id=model_id):
                self.assertIsNone(modelbandit.classify_route(model_id))


class RouteKindFacetContractTests(unittest.TestCase):
    def test_every_kind_exposes_the_specified_facet_contract(self):
        expected = {
            "market": {
                "zone_refusable_in_closed_regimes": False,
                "default_exposure": "no-retention",
                "spends_free_request_counter": False,
                "needs_policy_catalog_entry": False,
                "priced_by_endpoint_spread": True,
                "standing_from": "boards",
            },
            "free-slug": {
                "zone_refusable_in_closed_regimes": True,
                "default_exposure": "trains",
                "spends_free_request_counter": True,
                "needs_policy_catalog_entry": False,
                "priced_by_endpoint_spread": False,
                "standing_from": "own board row",
            },
            "harness": {
                "zone_refusable_in_closed_regimes": True,
                "default_exposure": "trains",
                "spends_free_request_counter": False,
                "needs_policy_catalog_entry": True,
                "priced_by_endpoint_spread": False,
                "standing_from": "family share",
            },
            "plan": {
                "zone_refusable_in_closed_regimes": False,
                "default_exposure": "no-retention",
                "spends_free_request_counter": False,
                "needs_policy_catalog_entry": True,
                "priced_by_endpoint_spread": False,
                "standing_from": "deferred to plan economics",
            },
            "local": {
                "zone_refusable_in_closed_regimes": False,
                "default_exposure": "local",
                "spends_free_request_counter": False,
                "needs_policy_catalog_entry": True,
                "priced_by_endpoint_spread": False,
                "standing_from": "family share",
            },
        }
        for kind, expected_facets in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(modelbandit.route_facets(kind), expected_facets)


if __name__ == "__main__":
    unittest.main()
