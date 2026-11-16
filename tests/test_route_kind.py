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

    def test_the_harness_local_namespace_is_local_claiming_by_itself(self):
        # The namespace is a serving fact: `lmstudio/*` is the harness's own
        # local id, exactly as it dispatches it, so the classifier answers
        # `local` with no serving fact and no catalogue consulted.
        for model_id in (
            "lmstudio/qwen/qwen3.6-35b-a3b",
            "lmstudio/abliterated-mimo-v2.6-distill-qwen-9b",
            "lmstudio/qwen36-35b-a3b-distill@iq4_xs",
        ):
            with self.subTest(model_id=model_id):
                self.assertEqual(modelbandit.classify_route(model_id),
                                 "local")

    def test_the_openrouter_namespace_is_not_hijacked_by_the_local_one(self):
        # An `openrouter/lmstudio/*` id dispatches through OpenRouter: the
        # `lmstudio/` namespace claims local only at the top of the id the
        # harness invokes, never as a market slug underneath `openrouter/`.
        self.assertEqual(modelbandit.classify_route(
            "openrouter/lmstudio/served-locally"), "market")

    def test_a_malformed_local_namespace_fails_closed(self):
        for model_id in ("lmstudio", "lmstudio/", "lmstudio//x", "/lmstudio/x"):
            with self.subTest(model_id=model_id):
                self.assertIsNone(modelbandit.classify_route(model_id))

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
                "zone_refusable_in_closed_zones": False,
                "default_exposure": "no-retention",
                "spends_free_request_counter": False,
                "priced_by_endpoint_spread": True,
                "standing_from": "boards",
            },
            "free-slug": {
                "zone_refusable_in_closed_zones": True,
                "default_exposure": "trains",
                "spends_free_request_counter": True,
                "priced_by_endpoint_spread": False,
                "standing_from": "own board row",
            },
            "harness": {
                "zone_refusable_in_closed_zones": True,
                "default_exposure": "trains",
                "spends_free_request_counter": False,
                "priced_by_endpoint_spread": False,
                "standing_from": "family share",
            },
            "plan": {
                "zone_refusable_in_closed_zones": False,
                "default_exposure": "no-retention",
                "spends_free_request_counter": False,
                "priced_by_endpoint_spread": False,
                "standing_from": "deferred to plan economics",
            },
            "local": {
                "zone_refusable_in_closed_zones": False,
                "default_exposure": "local",
                "spends_free_request_counter": False,
                "priced_by_endpoint_spread": False,
                "standing_from": "family share",
            },
        }
        for kind, expected_facets in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(modelbandit.route_facets(kind), expected_facets)


if __name__ == "__main__":
    unittest.main()
