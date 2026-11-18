"""Unit tests for the Free-request quota gate.

The OpenRouter daily free-request counter is one shared figure across every
``:free`` route, reset at UTC midnight. It is read up front and decides one
thing: whether ``:free`` routes stay in the pool. Harness-served free models
(``opencode/*``, local) never spend it. No test here touches the network —
the key payload is injected.
"""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402
from policy_fixture import scoring_block  # noqa: E402


class FreeQuotaDecisionTests(unittest.TestCase):
    def decide(self, **kwargs):
        return modelbandit.free_quota_decision(**kwargs)

    def test_quota_that_covers_the_plan_keeps_free_routes(self):
        # 50/day tier, 12 spent, 38 left; a 6-ticket plan with a 5 reserve
        # needs 11. 38 >= 11.
        verdict = self.decide(used=12, limit=50, remaining=38,
                              reserve=5, planned_free=6)
        self.assertTrue(verdict.eligible)
        self.assertEqual(verdict.reason, "")

    def test_quota_exactly_covering_the_plan_keeps_free_routes(self):
        # "excluded when remaining is below the plan's demand plus the
        # reserve": equality is not below. 6 + 5 = 11, 11 left.
        self.assertTrue(self.decide(used=39, limit=50, remaining=11,
                                    reserve=5, planned_free=6).eligible)

    def test_thin_quota_excludes_free_routes_with_the_numbers_that_bound_it(self):
        # 48 of 50 spent, 2 left; the plan is 1 ticket and the reserve is 5,
        # so 6 are needed and 2 remain.
        verdict = self.decide(used=48, limit=50, remaining=2,
                              reserve=5, planned_free=1)
        self.assertFalse(verdict.eligible)
        self.assertEqual(verdict.reason,
                         "free quota thin (2 left < 1 planned + 5 reserve)")

    def test_exhausted_quota_excludes_free_routes(self):
        verdict = self.decide(used=50, limit=50, remaining=0,
                              reserve=5, planned_free=1)
        self.assertFalse(verdict.eligible)
        self.assertEqual(verdict.reason, "free quota exhausted (50/50 used)")

    def test_overspent_counter_reads_as_exhausted(self):
        verdict = self.decide(used=52, limit=50, remaining=-2,
                              reserve=0, planned_free=0)
        self.assertFalse(verdict.eligible)
        self.assertEqual(verdict.reason, "free quota exhausted (52/50 used)")

    def test_remaining_is_derived_when_only_used_and_limit_are_reported(self):
        self.assertTrue(self.decide(used=10, limit=50, remaining=None,
                                    reserve=5, planned_free=6).eligible)
        thin = self.decide(used=45, limit=50, remaining=None,
                           reserve=5, planned_free=1)
        self.assertEqual(thin.reason,
                         "free quota thin (5 left < 1 planned + 5 reserve)")

    def test_no_reportable_counter_leaves_free_routes_alone(self):
        # Nothing to judge: an unreachable endpoint or a payload without the
        # counter must never remove routes the run could otherwise use.
        self.assertTrue(self.decide(used=None, limit=None, remaining=None,
                                    reserve=5, planned_free=100).eligible)


CATALOG = {
    "free_models": {
        "vendor/model": {"context_length": 262_144,
                         "exposure": "no-retention",
                         "summary_ref": "vendor/paid"},
        "opencode/flash": {"context_length": 262_144,
                           "exposure": "no-retention",
                           "summary_ref": "vendor/paid"},
        "qwen/coder": {"context_length": 262_144, "exposure": "local",
                       "summary_ref": "vendor/paid"},
    },
    "summaries": {"vendor/paid": "the paid sibling's summary"},
}

THIN = modelbandit.QuotaVerdict(False, "free quota thin (2 left < 1 planned + 5 reserve)")


class FreeQuotaGateTests(unittest.TestCase):
    """Which candidates the counter removes, through the one admission seam."""

    def admit(self, mid, verdict, *, local=False):
        return modelbandit.admit(modelbandit.Shape(), modelbandit.candidate_for(mid, CATALOG,
                                                           local=local),
                          quota=verdict)

    def test_openrouter_free_route_leaves_with_the_quota_reason(self):
        decision = self.admit("vendor/model:free", THIN)
        self.assertFalse(decision.admitted)
        self.assertEqual(decision.reason, THIN.reason)

    def test_openrouter_free_route_stays_when_the_quota_covers_the_plan(self):
        self.assertTrue(self.admit("vendor/model:free",
                                   modelbandit.QuotaVerdict(True)).admitted)

    def test_harness_free_model_is_unaffected_by_the_counter(self):
        # An OpenCode 'opencode/*' model is served by the harness: it spends
        # no OpenRouter free requests, so an exhausted counter says nothing
        # about it.
        self.assertTrue(self.admit("opencode/flash-free", THIN).admitted)

    def test_locally_served_free_model_is_unaffected_by_the_counter(self):
        self.assertTrue(
            self.admit("qwen/coder-30b", THIN, local=True).admitted)

    def test_paid_route_is_unaffected_by_the_counter(self):
        self.assertTrue(self.admit("vendor/paid", THIN).admitted)

    def test_unreported_quota_leaves_the_pool_unchanged(self):
        self.assertTrue(self.admit("vendor/model:free", None).admitted)


class FreeQuotaPayloadTests(unittest.TestCase):
    """The key payload's ``free_model_daily_requests``, and nothing else."""

    def test_reads_the_counter_nested_under_data(self):
        quota = modelbandit.free_quota_from_payload(
            {"data": {"limit": None, "usage": 1.5,
                      "free_model_daily_requests": {"used": 12, "limit": 50}}})
        self.assertEqual((quota.used, quota.limit, quota.remaining),
                         (12, 50, None))

    def test_reads_remaining_when_reported(self):
        quota = modelbandit.free_quota_from_payload(
            {"free_model_daily_requests": {"used": 12, "limit": 50,
                                           "remaining": 38}})
        self.assertEqual((quota.used, quota.limit, quota.remaining),
                         (12, 50, 38))

    def test_absent_counter_is_no_counter(self):
        self.assertIsNone(modelbandit.free_quota_from_payload(
            {"data": {"limit": None, "usage": 3, "rate_limit": {"requests": 1}}}))

    def test_null_counter_is_no_counter(self):
        self.assertIsNone(modelbandit.free_quota_from_payload(
            {"data": {"free_model_daily_requests": None}}))

    def test_malformed_payloads_are_no_counter(self):
        for payload in (None, [], {"data": []},
                        {"data": {"free_model_daily_requests": "50"}},
                        {"data": {"free_model_daily_requests": {}}},
                        {"data": {"free_model_daily_requests": {
                            "used": True, "limit": 50}}},
                        {"data": {"free_model_daily_requests": {
                            "used": "12", "limit": 50}}}):
            with self.subTest(payload=payload):
                self.assertIsNone(modelbandit.free_quota_from_payload(payload))


RESERVE_POLICY = scoring_block(alpha=1, beta=1, favor_validated=3,
                               favor_suspected=2)


def with_scoring(**values):
    return {**RESERVE_POLICY,
            "scoring": {**RESERVE_POLICY["scoring"], **values}}


class FreeQuotaReservePolicyTests(unittest.TestCase):
    """scoring.free_quota_reserve: configurable, and unusable values stop
    the run instead of being clamped."""

    def test_default_reserve_is_small_and_positive(self):
        self.assertEqual(modelbandit.load_policy_config(RESERVE_POLICY)
                         .free_quota_reserve,
                         modelbandit.DEFAULT_FREE_QUOTA_RESERVE)
        self.assertGreater(modelbandit.DEFAULT_FREE_QUOTA_RESERVE, 0)
        self.assertLessEqual(modelbandit.DEFAULT_FREE_QUOTA_RESERVE, 10)

    def test_configured_reserve_is_read(self):
        self.assertEqual(modelbandit.load_policy_config(
            with_scoring(free_quota_reserve=2)).free_quota_reserve, 2)

    def test_zero_reserve_is_allowed(self):
        # "the last few requests are not consumed by planning" — but a user
        # may decide nothing is held back.
        self.assertEqual(modelbandit.load_policy_config(
            with_scoring(free_quota_reserve=0)).free_quota_reserve, 0)

    def test_invalid_reserve_fails_loudly(self):
        for value in (-1, 2.5, "five", None, True, [], float("inf")):
            with self.subTest(value=value), self.assertRaisesRegex(
                    SystemExit, "scoring.free_quota_reserve"):
                modelbandit.load_policy_config(with_scoring(free_quota_reserve=value))


PAYLOAD = {"data": {"limit": None, "usage": 0.42,
                    "free_model_daily_requests": {"used": 12, "limit": 50}}}


class FreeQuotaReadTests(unittest.TestCase):
    """Reading the counter: through the shared fetch seam, never blocking."""

    def test_reads_the_counter_through_the_shared_fetch_seam(self):
        captured = {}

        def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
            captured.update(url=url, cache_name=cache_name, auth=auth,
                            refresh=refresh, **kwargs)
            return PAYLOAD

        with mock.patch("modelbandit.fetch_json", side_effect=fake_fetch):
            quota = modelbandit.free_quota()
        self.assertEqual((quota.used, quota.limit), (12, 50))
        self.assertEqual(captured["url"], "https://openrouter.ai/api/v1/key")
        self.assertEqual(captured["cache_name"], "key.json")
        self.assertTrue(captured["auth"])
        self.assertEqual(captured["ttl"], modelbandit.KEY_CACHE_TTL)
        self.assertFalse(captured["stale_ok"])

    def test_the_counter_is_cached_briefly_not_for_a_day(self):
        self.assertLess(modelbandit.KEY_CACHE_TTL, modelbandit.CACHE_TTL)
        self.assertLessEqual(modelbandit.KEY_CACHE_TTL, 300)

    def test_unreachable_endpoint_reports_no_counter_and_warns_once(self):
        err = io.StringIO()
        with mock.patch("modelbandit.fetch_json",
                        side_effect=SystemExit("error code: 502")), \
                redirect_stderr(err):
            self.assertIsNone(modelbandit.free_quota())
        self.assertEqual(err.getvalue().count("free quota"), 1)
        self.assertIn("502", err.getvalue())
        self.assertNotIn("stay in the pool", err.getvalue())

    def test_a_payload_without_the_counter_is_not_a_failure(self):
        err = io.StringIO()
        with mock.patch("modelbandit.fetch_json",
                        return_value={"data": {"usage": 1}}), \
                redirect_stderr(err):
            self.assertIsNone(modelbandit.free_quota())
        self.assertEqual(err.getvalue(), "")

    def test_an_injected_payload_decides_the_pool(self):
        # 48 of 50 spent: a one-ticket plan plus the 5 reserve cannot be
        # covered, so ':free' routes leave and the harness free model stays.
        thin = {"data": {"free_model_daily_requests": {"used": 48,
                                                       "limit": 50}}}
        with mock.patch("modelbandit.fetch_json", return_value=thin):
            quota = modelbandit.free_quota()
        verdict = modelbandit.free_quota_decision(
            used=quota.used, limit=quota.limit, remaining=quota.remaining,
            reserve=5, planned_free=1)
        self.assertFalse(modelbandit.admit(modelbandit.Shape(), modelbandit.candidate_for(
            "vendor/model:free", CATALOG), quota=verdict).admitted)
        self.assertTrue(modelbandit.admit(modelbandit.Shape(), modelbandit.candidate_for(
            "opencode/flash-free", CATALOG), quota=verdict).admitted)


if __name__ == "__main__":
    unittest.main()
