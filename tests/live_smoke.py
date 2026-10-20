#!/usr/bin/env python3
"""Manual live smoke test — hits the real OpenRouter API. Not run in CI.

Needs OPENROUTER_API_KEY or an OpenCode auth.json with an openrouter entry.
"""

import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "skills", "openrouter-model-router", "scripts",
                      "bind.py")


def main() -> int:
    result = subprocess.run(
        [sys.executable, SCRIPT, "--domain", "writing", "--top", "3"],
        capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    checks = {
        "exit 0": result.returncode == 0,
        "ranking header": "Popularity ranking: writing" in result.stdout,
        "ranked rows": "| 1 |" in result.stdout,
        "projection": "projection at" in result.stdout,
    }
    for name, ok in checks.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    passed = all(checks.values())
    print("LIVE SMOKE:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
