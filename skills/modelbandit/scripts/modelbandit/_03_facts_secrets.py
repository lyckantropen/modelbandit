from __future__ import annotations

# Part of the modelbandit package: composed, in this file's original order, into
# one namespace by __init__.py - see that file's docstring for why.
def priced_by_endpoint_spread(mid: str, *, local: bool = False) -> bool:
    """Whether Endpoint spread prices this serving - the market kind's trait
    alone (the facet contract's `priced_by_endpoint_spread`). Non-market
    rows make no catalog fetch: a Free route prices from its zero record,
    and a plan route prices from its plans entry's Draw."""
    facets = facets_for(mid, local=local)
    return bool(facets and facets["priced_by_endpoint_spread"])


# The remote serving kinds: the contract-table kinds whose ids a policy
# `local` Exposure label can never claim - every kind but the two a
# slash-shaped id may legitimately carry (a market slug or a model this
# machine serves).
_REMOTE_KINDS = frozenset(_ROUTE_FACETS) - {"market", "local"}


def local_label_is_void(mid: str) -> bool:
    """Whether a policy `local` Exposure label is void for this id.

    Localness is a serving fact, never a catalogue claim: the classifier
    answers the remote serving namespaces remote whatever a label says - a
    `:free` slug, an `opencode/*` harness model, an `opencode-go/*` plan
    route - so a `local` label on one is void. The harness's `lmstudio/*`
    namespace classifies local by itself, and a market-shaped slash id is
    not voided either: a served model's id can be slash-shaped, so the
    label may claim one."""
    return classify_route(mid) in _REMOTE_KINDS


_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\b(?:password|passwd|token|api[_-]?key|access[_-]?token|"
               r"secret[_-]?key)\b\s*[:=]\s*['\"]?[^\s,'\"]{4,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def _string_values(value) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [part for part in value if isinstance(part, str) and part]
    if isinstance(value, dict):
        return [part for part in value.values() if isinstance(part, str) and part]
    return []


# Machine facts are matched as inclusions, so an identifier short enough to
# occur in ordinary prose would make every shape Sensitive.
MIN_IDENTIFIER_LEN = 4
_LOOPBACK = ("127.", "0.0.0.0", "::1", "localhost")
# Fact class -> the rule name reported when it trips. The class keys are what
# machine_facts gathers; `identifiers` stays the flat form the gate accepts.
_IDENTIFIER_CLASSES = (("hostname", "hostname"), ("username", "username"),
                       ("home", "home path"), ("addresses", "local address"),
                       ("identifiers", "identifier"),
                       ("outside_file_contents", "outside-file content"),
                       ("passwords", "password"), ("tokens", "token"),
                       ("keys", "key"))
# The built-in credential rules, each named so the verdict says which bound.
_CREDENTIAL_RULES = (
    ("password, token or key assignment", _SECRET_VALUE_PATTERNS[0]),
    ("bearer token", _SECRET_VALUE_PATTERNS[1]),
    ("private key block", _SECRET_VALUE_PATTERNS[2]),
)


def _gather(reader):
    """One fact from the machine, best effort: never crash, never block."""
    try:
        return reader()
    except Exception:
        return None


def _local_addresses() -> list[str]:
    """This machine's non-loopback address, without sending a packet."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return [sock.getsockname()[0]]
    finally:
        sock.close()


def machine_facts(*, hostname=None, username=None, home=None,
                  addresses=None) -> dict:
    """The identifiers readable from this machine, gathered for the gate.

    Hostname, login, home path and local addresses, each best effort: a source
    that fails contributes nothing and the run carries on. The readers are
    injectable so a test states the machine instead of borrowing this one.
    Values shorter than ``MIN_IDENTIFIER_LEN`` and loopback/root paths are
    dropped — they identify nothing a reader of the material does not know,
    and they trip on ordinary prose.
    """
    readers = {"hostname": hostname or socket.gethostname,
               "username": username or getpass.getuser,
               "home": home or (lambda: os.path.expanduser("~")),
               "addresses": addresses or _local_addresses}
    facts: dict = {"identifiers": []}
    for field, reader in readers.items():
        value = _gather(reader)
        if field == "addresses":
            value = [address for address in (value or [])
                     if isinstance(address, str) and len(address) >= MIN_IDENTIFIER_LEN
                     and not address.startswith(_LOOPBACK)]
        elif not isinstance(value, str):
            value = ""
        else:
            # A bare root ("/", "C:\") identifies nothing.
            value = value.rstrip("/\\")
            value = value if len(value) >= MIN_IDENTIFIER_LEN else ""
        if not value:
            continue
        facts[field] = value
        facts["identifiers"].extend(value if isinstance(value, list) else [value])
    return facts


# Gitignored content is read, never scanned: a capped slice of a capped number
# of files, enough to catch a shape quoting a line of one.
GITIGNORED_MAX_FILES = 20
GITIGNORED_MAX_BYTES = 8192
# Below this a line is a label, not content a shape could quote.
GITIGNORED_MIN_LINE = 8


def _run_git(root: str):
    """A `git` runner bound to `root`, or None when git is unavailable."""
    def run(args):
        completed = subprocess.run(["git", "-C", root, *args],
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   timeout=10, check=False)
        if completed.returncode != 0:
            raise OSError(completed.stderr.strip() or "git failed")
        return completed.stdout
    return run


def gitignored_facts(root: str, *, run=None, reader=None,
                     max_files: int = GITIGNORED_MAX_FILES,
                     max_bytes: int = GITIGNORED_MAX_BYTES) -> list[dict]:
    """Significant lines from this tree's gitignored untracked files.

    `.gitignore` is the repository's own maintained list of what must not
    leave it, so a shape quoting one of those lines is carrying outside
    content. `run(args)` lists the files (`git ls-files --others --ignored
    --exclude-standard` by default) and `reader(path)` returns a file's text;
    both are injectable and either failing is silent — a missing git costs the
    run a rule, never a crash. Comments and short lines are dropped, and each
    line is kept once.
    """
    if run is None:
        run = _run_git(root)
    if run is None:
        return []
    if reader is None:
        def reader(path):
            with open(os.path.join(root, path), "rb") as f:
                return f.read(max_bytes).decode("utf-8", "replace")
    try:
        listed = run(["ls-files", "--others", "--ignored", "--exclude-standard"])
    except Exception:
        return []
    if isinstance(listed, bytes):
        listed = listed.decode("utf-8", "replace")
    paths = [line.strip() for line in str(listed or "").splitlines() if line.strip()]
    facts, seen = [], set()
    for path in paths[:max_files]:
        try:
            text = reader(path)
        except Exception:
            continue
        if not isinstance(text, str):
            continue
        text = text[:max_bytes]
        if "\0" in text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if len(line) < GITIGNORED_MIN_LINE or line.startswith("#"):
                continue
            if line in seen:
                continue
            seen.add(line)
            facts.append({"path": path, "line": line})
    return facts


def outside_file_contents(root: str, paths, *,
                          max_files: int = GITIGNORED_MAX_FILES,
                          max_bytes: int = GITIGNORED_MAX_BYTES) -> list[str]:
    """Capped content from explicitly named outside files, by significant line."""
    contents, seen = [], set()
    for named_path in list(paths or ())[:max_files]:
        path = (named_path if os.path.isabs(named_path)
                else os.path.join(root, named_path))
        try:
            with open(path, "rb") as f:
                text = f.read(max_bytes).decode("utf-8", "replace")
        except (OSError, TypeError):
            continue
        if "\0" in text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                contents.append(line)
    return contents


def secrets_verdict(material: str, *, machine: dict | None = None,
                    rules: dict | None = None) -> tuple[bool, str]:
    """The Secrets gate's decision with the rule that tripped it.

    ``material`` is the shape's material; ``machine`` supplies content and
    identifiers readable from machine state under the fact classes above and
    under ``gitignored`` ([{"path", "line"}] from the tree's gitignored
    files); ``rules`` adds literal ``phrases`` and regular-expression
    ``patterns``. Content-inclusion, any-of: a path mention by itself is not a
    content inclusion. Returns (sensitive, rule) where rule names the class
    or the rule's index — never the matched value, which may itself be
    the secret.
    """
    if not isinstance(material, str) or not material:
        return False, ""
    machine = machine if isinstance(machine, dict) else {}
    for field, rule in _IDENTIFIER_CLASSES:
        if any(value in material
               for value in _string_values(machine.get(field))):
            return True, rule
    for entry in machine.get("gitignored") or []:
        if isinstance(entry, dict) and isinstance(entry.get("line"), str) \
                and entry["line"] in material:
            return True, f"gitignored content ({entry.get('path', '?')})"
    for rule, pattern in _CREDENTIAL_RULES:
        if pattern.search(material):
            return True, rule
    if isinstance(rules, dict):
        for index, value in enumerate(_string_values(rules.get("phrases")), 1):
            if value in material:
                return True, f"phrase #{index}"
        for index, source in enumerate(_string_values(rules.get("patterns")), 1):
            try:
                if re.search(source, material):
                    return True, f"pattern #{index}"
            except re.error:
                continue
    return False, ""


def secrets_gate(material: str, *, machine: dict | None = None,
                 rules: dict | None = None) -> bool:
    """Pure Secrets gate verdict: True when sensitive content is included.

    The boolean form of `secrets_verdict`; see it for the fact classes.
    """
    return secrets_verdict(material, machine=machine, rules=rules)[0]


def resolve_working_root(root: str | None = None, *, run=None) -> str:
    """The working folder whose gitignored files the gate reads.

    The git root when the folder is inside a repository — a project's
    gitignored content belongs to the project — else the folder itself. A
    missing or failing git leaves the folder as given, never blocks the
    check.
    """
    base = os.path.abspath(root or os.getcwd())
    if run is None:
        run = _run_git(base)
    if run is None:
        return base
    try:
        top = str(run(["rev-parse", "--show-toplevel"]) or "").strip()
    except Exception:
        return base
    return os.path.abspath(top) if top else base


def secrets_check(material: str, *, root: str | None = None,
                  machine: dict | None = None,
                  gitignored: list | None = None,
                  outside_files=()) -> tuple[bool, str]:
    """The one material-assessment entry point, assembled at the edge.

    The built-in rules only — credential patterns, this machine's
    identifiers, gitignored content from the tree, and the capped content
    of any named outside file — with no project rules file anywhere, so the
    deal-time automatic run and the manual mode cannot classify
    differently. Machine facts are gathered here; each part is injectable,
    keeping the decision itself pure. Returns (sensitive, rule) as
    `secrets_verdict` does.
    """
    working_root = resolve_working_root(root)
    facts = dict(machine_facts() if machine is None else machine)
    facts["gitignored"] = (gitignored_facts(working_root)
                           if gitignored is None else list(gitignored))
    facts["outside_file_contents"] = (
        _string_values(facts.get("outside_file_contents"))
        + outside_file_contents(working_root, outside_files))
    return secrets_verdict(material, machine=facts)


# Exit contract v2 (ADR-0004): status says whether the tool ran; the output
# says what's true. 0 is any completed verdict (the printed lines say which),
# 2 belongs to argparse's usage errors, 4 means rules/config stopped the tool
# before it could form a verdict. 1 is CPython's generic operational failure
# and is never assigned here; the answer codes 1 (sensitive), 3 (not
# certified) and 5 (zone block) are retired, as is the over-budget run's
# borrowed 2 — answers live in the output, never in a nonzero status.
RULES_CONFIG_ERROR = 4


def emit_json(payload: dict) -> None:
    """One JSON object per `--json` invocation on stdout — stdlib json only."""
    print(json.dumps(payload, ensure_ascii=False))


