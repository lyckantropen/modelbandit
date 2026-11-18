from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
# --- Free-use zones --------------------------------------------------------
# Where free models may run, machine-wide: open unless declared, and the
# zones file is a bare opt-out list of the paths declared closed. Only a
# closed place stops remote free routes at the source, and a run takes the
# stricter of its working folder's and its origin repository's declaration
# (ADR-0010).
ZONES_FILE = "zones.json"
ZONES_CONFIG_DIR = "modelbandit"
# The file's whole schema: `{"zones": ["path", ...]}` — a bare list of the
# paths declared closed. The per-entry posture key and the top-level `default`
# key are retired, and open-unless-declared is not configurable (ADR-0010).
ZONES_KEY = "zones"
ZONES_FORM = '{"zones": ["<path>", ...]}'
_ENV_VAR = re.compile(r"\$\{(\w+)\}|\$(\w+)")


@dataclasses.dataclass(frozen=True)
class Zone:
    """The zone that decided a run: the declaration that matched, or None
    when nothing covered the place, and the binary posture it lands on.

    `place` is the judged folder as the header spells it; `resolved` carries
    the place a link reached when the judgement moved - the working folder or
    the declaration itself spells one place and reaches another. None when
    nothing moved.
    """
    path: str | None
    posture: str
    place: str | None = None
    resolved: str | None = None

    def label(self) -> str:
        if self.path is not None:
            return self.path
        return self.place or "undeclared"


def zone_label(zone: Zone) -> str:
    """The run header's statement: `<path> (<posture>)` - the place the
    judgement landed and the binary `open` / `closed` posture, never the
    shape. When a link moved the judgement, the header names the resolved
    place - with the declared path noted, or `undeclared` when no
    declaration matched - so a declaration cannot silently cover content it
    did not name.
    """
    if zone.resolved is None:
        return f"{zone.label()} ({zone.posture})"
    declared = f"declared: {zone.path}" if zone.path else "undeclared"
    return f"{zone.resolved} ({zone.posture}) ({declared})"


@dataclasses.dataclass(frozen=True)
class RunContext:
    """The run's posture, built once in the dispatch and passed whole: the
    zone it works under, the local candidates the harness listed, the
    serving endpoint's loopback fact, the Local roster, and the effort
    intent the run asks for. One value, so an entry point cannot re-spell a
    subset of the posture from loose scalars and have two surfaces disagree
    about where the run stands. The data inputs - models, policy,
    configuration, ranks, the listing - stay separate parameters: they are
    what the run judges, not where it stands. A surface that deliberately
    scopes differently (the anchors' drift set works with empty locals and
    measured intent) states its own overrides at its call, visibly.
    """
    zone: Zone
    local_ids: tuple = ()
    loopback: bool = True
    roster: dict | None = None
    intent: str = "measured"


def zone_payload(zone: Zone) -> dict:
    """The `zone` object every `--json` verdict carries: the place the
    judgement landed (`path`), the binary posture, the declaration (null when
    no declaration matched) and the resolved place when a link moved it — the
    same facts the human `zone:` line spells."""
    return {"path": zone.resolved if zone.resolved else zone.label(),
            "posture": zone.posture,
            "declared": zone.path,
            "resolved": zone.resolved}


def zones_path(*, environ=None) -> str:
    """`zones.json` under the machine's config root ($XDG_CONFIG_HOME or
    ~/.config), honouring the environment it is given."""
    env = os.environ if environ is None else environ
    base = (env.get("XDG_CONFIG_HOME")
            or os.path.join(expand_path("~", environ=env), ".config"))
    return os.path.join(base, ZONES_CONFIG_DIR, ZONES_FILE)


def zones_file_label(*, environ=None) -> str:
    """The zones file's path as the header spells it: `~` for the home it
    sits under, forward slashes after - the path to create reads the same
    on every machine, and names wherever the loader actually looks."""
    path = zones_path(environ=environ)
    home = expand_path("~", environ=environ)
    if os.path.normcase(path).startswith(os.path.normcase(home) + os.sep):
        path = "~" + path[len(home):]
    return path.replace(os.sep, "/")


