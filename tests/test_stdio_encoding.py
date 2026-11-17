"""Regression pins for the CLI's own UTF-8 stdio guard.

The printed tables carry the `Δ` baseline column and other characters no
legacy console code page can encode: on a cp1250 pipe or a redirected file
the ranking died with a UnicodeEncodeError the moment its header was
written - unless the caller remembered to set PYTHONUTF8=1 first. The
guard is the program's own (modelbandit._harden_stdio, called as the first
statement of main): every end-to-end pin below runs a real subprocess with
PYTHONIOENCODING forced to cp1250, the environment that used to kill the
run, so the pins reproduce the crash on any machine regardless of its
locale. The remaining pins inject their streams, like the rest of the
suite injects its environment.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                "modelbandit", "scripts"))
import modelbandit  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "skills", "modelbandit", "scripts")

# The child runs the CLI through the same entry every invocation uses,
# then writes the very character cp1250 cannot encode. Without the guard
# the last line dies on the still-legacy stream and the process exits 1;
# with it, stdout speaks UTF-8 and the mark survives byte-exact.
CHILD = (
    "import sys\n"
    "sys.path.insert(0, %r)\n"
    "import modelbandit\n"
    "sys.argv = ['modelbandit', '--list-domains']\n"
    "modelbandit.main()\n"
    "print('\\u0394 baseline')\n"
) % SCRIPTS


class RecordingStream:
    """A stream double that records reconfigure calls, or refuses to be
    reconfigured the way a StringIO or an exotic wrapper would."""

    def __init__(self, encoding, error=None):
        self.encoding = encoding
        self.calls = []
        self._error = error

    def reconfigure(self, **kwargs):
        if self._error is not None:
            raise self._error
        self.calls.append(kwargs)


class StubbornStream:
    """A stream with an encoding but no reconfigure at all: attribute
    lookup itself fails, which the guard must swallow."""

    encoding = "cp1250"


class LegacyCodePageTests(unittest.TestCase):
    def child_env(self, home):
        env = dict(os.environ)
        # Drop the workaround, force the legacy code page: PYTHONIOENCODING
        # pins both the encoding and strict errors on every machine.
        env.pop("PYTHONUTF8", None)
        env["PYTHONIOENCODING"] = "cp1250"
        env["HOME"] = home
        env["USERPROFILE"] = home
        env["XDG_CONFIG_HOME"] = os.path.join(home, ".config")
        return env

    def test_the_cli_entry_speaks_utf8_on_a_cp1250_pipe(self):
        # The crash itself: a cp1250 pipe once killed the ranking at its
        # header line. The child calls main() for real - hermetic HOME, no
        # network in the --list-domains path - and then prints Δ on the
        # stream main() hardened.
        with tempfile.TemporaryDirectory() as home:
            completed = subprocess.run(
                [sys.executable, "-c", CHILD],
                capture_output=True, env=self.child_env(home))

        stderr = completed.stderr.decode("utf-8", "replace")
        self.assertEqual(completed.returncode, 0, stderr)
        self.assertNotIn("UnicodeEncodeError", stderr)
        out = completed.stdout.decode("utf-8")  # must decode strictly
        # The CLI itself ran (its domain list), and the mark survived.
        self.assertIn("research", out)
        self.assertIn("Δ baseline", out)


class HardenStdioTests(unittest.TestCase):
    def test_a_legacy_code_page_stream_is_reconfigured_to_utf8(self):
        out, err = RecordingStream("cp1250"), RecordingStream("cp1250")
        modelbandit._harden_stdio(stdout=out, stderr=err)
        expected = [{"encoding": "utf-8", "errors": "replace"}]
        self.assertEqual(out.calls, expected)
        self.assertEqual(err.calls, expected)

    def test_a_stream_already_speaking_utf8_is_left_alone(self):
        for encoding in ("utf-8", "UTF-8", "utf8"):
            with self.subTest(encoding=encoding):
                stream = RecordingStream(encoding)
                modelbandit._harden_stdio(stdout=stream, stderr=stream)
                self.assertEqual(stream.calls, [])

    def test_a_stream_without_an_encoding_is_left_alone(self):
        # StringIO (what every in-process CLI test redirects onto) has no
        # encoding at all: the guard must pass it through untouched.
        buf = io.StringIO()
        modelbandit._harden_stdio(stdout=buf, stderr=buf)
        self.assertEqual(buf.getvalue(), "")

    def test_a_stream_that_cannot_be_reconfigured_does_not_abort_the_run(self):
        # Reconfiguration refused (ValueError) or simply unavailable
        # (AttributeError): the guard swallows it and the run continues.
        refused = RecordingStream("cp1250", error=ValueError("closed"))
        modelbandit._harden_stdio(stdout=refused, stderr=refused)
        self.assertEqual(refused.calls, [])

        plain = StubbornStream()
        modelbandit._harden_stdio(stdout=plain, stderr=plain)
        self.assertEqual(getattr(plain, "calls", None), None)


if __name__ == "__main__":
    unittest.main()
