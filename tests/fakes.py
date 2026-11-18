"""Shared fixture seams for the CLI harnesses: the one dispatch on
`cache_name` every suite's fake_fetch used to repeat, and the junction
builder the link-resolution suites share."""

import os
import subprocess

import modelbandit

KEY_URL = "cannot reach https://openrouter.ai/api/v1/key"
KEY_ENDPOINT = "cannot reach the key endpoint"


def world_fetch(world, *, calls=None, key=KEY_URL, benchmarks=False,
                fetch_error=False):
    """The fixture world's fetch dispatcher: `calls` records each url, `key`
    is the key endpoint's failure payload, `benchmarks` serves the
    benchmarks cache, `fetch_error` fails every fetch up front."""
    def fake_fetch(url, cache_name, *, auth, refresh, **kwargs):
        if fetch_error:
            raise SystemExit(f"cannot reach {url}")
        if calls is not None:
            calls.append(url)
        if cache_name == "key.json":
            raise SystemExit(key)
        if cache_name == "models.json":
            return {"data": world["models"]}
        if cache_name == "classifications.json":
            return {"data": world["classifications"]}
        if cache_name == "rankings.json":
            return world["rankings"]
        if benchmarks and cache_name == "benchmarks.json":
            return world["benchmarks"]
        if url.endswith("/endpoints"):
            slug = url[len(modelbandit.MODELS_URL) + 1:-len("/endpoints")]
            return {"data": {"endpoints": world["endpoints"].get(slug, [])}}
        raise AssertionError(f"unexpected fetch: {url}")
    return fake_fetch


def make_junction(link, target):
    """A directory junction on Windows (`mklink /J` needs no privileges), a
    symlink elsewhere: (ok, error) so each suite keeps its own verdict."""
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", link, target],
            capture_output=True, text=True)
        return completed.returncode == 0, completed.stderr
    try:
        os.symlink(target, link, target_is_directory=True)
        return True, ""
    except (OSError, NotImplementedError) as exc:
        return False, str(exc)