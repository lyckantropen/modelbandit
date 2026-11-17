"""Rank OpenRouter models by domain popularity and price them live.

Stdlib only. Reads OpenRouter's task-classification leaderboards and daily token
rankings (Data API; CC BY 4.0), maps them to a domain from policy.json, and
emits a popularity-ranked candidate table priced at live rates, with effort
rungs and a batch cost projection. Prices are per-endpoint, not the models-list
figure: the same model can span 20x on output across providers, so projection
defaults to the worst endpoint. Mechanics live in --help; SKILL.md holds the
policy.
"""

# One namespace, many files. The implementation is split across the `_NN_*.py`
# parts beside this file, and this package composes them, in their original
# order, into ONE shared namespace: each part is compiled with its own path
# (tracebacks and inspect.getsource resolve to the part) and executed into
# this module's globals, so the package's namespace is exactly the single
# module's was. That is deliberate, not a shortcut: the test suite pins the
# CLI and library seams by patching names on this top-level namespace
# (`modelbandit.fetch_json`, `CACHE_DIR`, ...), and cross-module references
# must keep resolving through it at call time for those pins to hold. A part
# therefore imports nothing from its siblings - order inside one namespace
# is what the single file's order always was.
import os as _os

_PARTS = [
    '_01_core.py',
    '_02_harness.py',
    '_03_facts_secrets.py',
    '_04_contract.py',
    '_05_zones.py',
    '_06_roster.py',
    '_07_entrypoints.py',
    '_08_cost.py',
    '_09_policy.py',
    '_10_admission.py',
    '_11_quota_deal.py',
    '_12_substitution.py',
    '_13_policycheck.py',
    '_14_cli.py',
]

_here = _os.path.dirname(_os.path.abspath(__file__))
for _name in _PARTS:
    _path = _os.path.join(_here, _name)
    with open(_path, encoding="utf-8") as _source_file:
        _source = _source_file.read()
    exec(compile(_source, _path, "exec"), globals())
