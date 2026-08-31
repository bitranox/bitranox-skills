#!/usr/bin/env python3
"""Audit shipped skills AND shipped scripts in a clean room, one reviewer per unit, in parallel.

Two mechanics this encodes, both of which are easy to get wrong and silent when you do:

- The isolation that matters is from the MEMORY STORE, not from the plugin. A reviewer running
  anywhere on a machine that has a curated store is handed matching entries by the recall hook, so
  it cannot tell whether the SKILL taught it something or the store did. Wall recall for the run
  (`cross_tree_search: false` with the room outside the tree) and restore it afterwards.
- The INSTALL UNIT is the plugin, not the skill directory. A skill legitimately points at sibling
  skills and at the plugin's own hooks; judging reachability against one skill directory reports
  every such reference as dangling.

Two sweeps live here. The SKILL sweep (`audit_all`) judges prose claims and wants a verbatim quote
per finding. The SCRIPT sweep (`audit_scripts`) judges code and wants executable evidence, because
a quote cannot discriminate a real bug from a misread: the quote is genuine and only the inference
is invented. Their reviewer contracts share no paragraph, so they are two prompt constants rather
than one parameterised template - a merged template gets edited for one caller and silently breaks
the other.

Run with `--jobs` reviewers at a time; each writes `<room>/reports/<stem>.audit.txt`.

Pure standard library.
"""

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROMPT = """You are auditing ONE Claude Code skill for defects: `skills/{name}/`.

Read `skills/{name}/SKILL.md` fully, and every supporting file it references.

WHAT SHIPS: this whole directory is the installed plugin. The reader who installs it gets every
skill under `skills/`, the hooks under `hooks/`, and nothing outside this directory. So a reference
to a sibling skill (`{prefix}:<name>`) or to a plugin hook IS reachable - verify it resolves to a
real path here rather than assuming either way. What is NOT reachable is anything outside this
directory: a source repo, a package's `docs/`, a path on the author's machine.

Judge only from what is here. Do not search the wider filesystem and do not rely on knowledge of
any repository this plugin came from.

Report defects in these classes, most severe first:

1. WRONG - a claim, command, flag, API signature or code sample that is incorrect, or that
   contradicts another part of the same skill. Verify it if you can: run the command, check the
   help, execute the snippet.
2. DANGLING - a reference that does not resolve: a sibling skill or hook path that is NOT in this
   directory, a bare script filename with no stated home, a `docs/x.md` or README that ships
   nowhere and is not a URL.
3. UNEXECUTABLE - an instruction a competent reader cannot carry out as written because a required
   value, path, order or precondition is missing.
4. STALE - a claim that reads as version-bound or time-bound and carries no version, date, or way
   to check it.

For EVERY finding, output exactly this shape, one per finding:

FINDING: <class> | <file> | <one-line claim>
QUOTE: <the exact offending line, copied verbatim from the file>
WHY: <what a reader does wrong because of it>

Copy the quote character for character. If you cannot produce a verbatim quote, you do not have a
finding - drop it. Before reporting a DANGLING finding, actually check the path exists or does not:
`ls skills/<name>/SKILL.md`, `ls hooks/<file>`. Do not report style, tone, formatting, or
"could be clearer" opinions, and do not report the absence of things a skill of this kind need not
have.

If the skill has no defects in these classes, output the single line: NO FINDINGS

Then end with a section headed "Skill gaps": what you could not turn into a concrete action, what
you had to guess, and anywhere the text was silent or said two different things.
"""

# ---------------------------------------------------------------------------------------------
# Script sweep
# ---------------------------------------------------------------------------------------------

KIND_HOOK = "hook"
KIND_HOOK_LIB = "hook-lib"
KIND_SHIM = "shim"
KIND_SKILL_SCRIPT = "skill-script"
KIND_JS = "js"
KIND_VENDORED = "vendored"

SCRIPT_CLASSES = ("BUG", "FAILMODE", "PORTABILITY", "UNGUARDED-DEP", "CONTRACT-DRIFT",
                  "UNTESTED-BRANCH", "SECURITY", "DEAD")

# Anything whose name says it mutates a real host, store, or process. A reviewer told to "verify by
# running it" is a live hazard: these reconfigure firewalls and speakers, rmtree caches and
# worktrees, and rewrite the curated memory store. The deny is interpolated into the prompt so it is
# visible in the report rather than being an unstated hope.
DO_NOT_RUN_RX = re.compile(
    r"(ssh|transfer|prune|clean|migrate|preset|onboard|service|pfsense|reconcile|procsig"
    r"|soundtouch|fleet|wtclean|dream_state|contrib_queue)", re.I)

# Fallback only. The live values are imported from the plugin's own harness_checks so this cannot
# drift from the gate that enforces the same rule; see _exclusions().
_FALLBACK_EXCLUDE_DIRS = frozenset({"tests", "demos", "examples", "__pycache__", "scripts_examples"})
_FALLBACK_EXCLUDE_FILES = frozenset({"conftest.py", "__init__.py"})
_EXTRA_EXCLUDE_DIRS = frozenset({".skillwriter", ".pytest_cache", ".git", "node_modules"})
_VENDORED_DIRS = frozenset({"demos", "examples"})

_HOOK_CONVENTIONS = """THE FAIL-OPEN CONVENTION - READ THIS BEFORE REPORTING ANY ERROR HANDLING.
A hook must never wedge a turn, so every hook here fails OPEN by design: 46 of the 63 hooks in this
plugin end their entry point with a broad `except Exception` that exits 0. THAT IS CORRECT, IT IS
THE HOUSE STYLE, AND IT IS NOT A FINDING. Do not report it. Exactly two shapes ARE defects:
  (a) a guard's BLOCKING decision (exit 2, or a permissionDecision of "deny") is computed INSIDE a
      `try:` whose `except` returns 0 - the BLOCK is what gets lost, not merely the crash; the guard
      then silently approves the thing it exists to stop.
  (b) a tool that is not a hook swallows a real error and exits 0, so its caller reads failure as
      success.
Report (a) or (b) if you find them. Report nothing else about broad exception handling.

A hook also gets NO dependency provisioning: it is launched by `run-python.sh`, which execs a plain
`python3` with no venv and no PEP 723 resolution. A non-stdlib import at module level with no
`ImportError` fallback is therefore a real defect - but check the guard degrades to a sane value,
not merely that it does not raise.

HOW TO RUN A HOOK: every hyphenated hook reads a JSON event on stdin. A bare `python3 hooks/x.py`
BLOCKS FOREVER and will burn your entire time budget. Always pipe an event:
    echo '{}' | python3 hooks/x.py
"""

_TOOL_CONVENTIONS = """THIS IS A USER-INVOKED TOOL, NOT A HOOK. It must fail LOUD: a real error has
to reach a non-zero exit, because its caller reads the exit code as the verdict. Swallowing an error
into exit 0 is a defect here, which is the opposite of the rule for hooks - do not carry a hook
habit across.

Many of these declare PEP 723 inline metadata and are launched with `uv run`, which resolves those
dependencies. An import declared in the script's own `# /// script` block is therefore fine.
"""

SCRIPT_PROMPT = """You are auditing ONE shipped script for defects: `%(rel)s` (kind: %(kind)s).

Read it fully. Then read the test modules and documentation anchors listed below - they are the
cheapest available statement of what this script is SUPPOSED to do, and a bug claim that ignores
them is a guess.

WHAT SHIPS: this whole directory is the installed plugin. Everything under `skills/` and `hooks/`
travels together and is reachable from any of it. What is NOT reachable is anything outside this
directory. Judge only from what is here; do not rely on knowledge of the repository it came from.

%(conventions)s
REQUIRED READING
  script:  %(rel)s
  tests:   %(tests)s
  anchors: %(anchors)s
%(registration)s
WHERE THE SHIPPED DOCUMENTATION NAMES THIS FILE
Each line below is a place the docs make a claim about this script. Check every one against the
code - a flag that argparse does not accept, a default that differs, an exit code that does not
match. This is the highest-yield question in the sweep and it costs you a few lines of reading.
%(mentions)s
ALREADY KNOWN - DO NOT RE-REPORT
A deterministic pre-pass already scanned this file. These are its hits. Reporting them again is
noise, and every reviewer in this sweep has been told the same:
%(prepass)s

LEADS - THESE ARE NOT SETTLED, JUDGE EACH ONE
The same pre-pass flagged the lines below mechanically, but it cannot tell a real defect from a
deliberate choice: that depends on what this file does with the result, which is your job and no
script's. Do NOT treat these as known. For each, say either that it is a defect on this file's real
execution path - with the input that breaks it - or that it is correct as written, and why.
%(leads)s
HOW TO VERIFY WITHOUT BREAKING THE MACHINE
%(donotrun)s
Verify with `--help`, or against a fixture you create inside this room. NEVER against a real path,
host, process or repository outside this directory, and never without `--dry-run` where the script
offers one. Do not install anything: if a dependency is missing, that is UNMEASURED, not a finding.
Do not edit any file in this room - a later reviewer reads the same copy and must see the same
program. Pass `-p no:cacheprovider` if you run pytest.

REPORT DEFECTS IN THESE CLASSES, MOST SEVERE FIRST
1. BUG - a concrete input for which this code returns a wrong value, raises, or hangs. State the
   input and the actual wrong output.
2. FAILMODE - the failure DIRECTION contradicts the contract above (a lost block, or a swallowed
   error exiting 0).
3. PORTABILITY - works on POSIX and provably breaks under Windows or Git Bash: path shape,
   subprocess decoding, shlex on a backslash path, os.access X_OK, a hard-coded /tmp, CRLF.
4. UNGUARDED-DEP - a non-stdlib import reachable on this file's real execution path with no
   fallback, in something that gets no dependency provisioning.
5. CONTRACT-DRIFT - the docstring, --help, the owning SKILL.md, or the hooks.json registration says
   X and the code does Y: a flag name, a default, an exit code, an event, an output shape.
6. UNTESTED-BRANCH - a named branch or error path that no test reaches, or whose test asserts
   nothing about it (asserts only "did not raise", or re-implements the code under test).
7. SECURITY - a NAMED untrusted source reaching a NAMED sink. Hook stdin is model-controlled JSON
   and is the one genuinely untrusted boundary here. A generic "shell=True is dangerous" with no
   traced source is not a finding.
8. DEAD - code no caller can reach. Paste the grep proving zero non-definition references.
   "Only used by tests" is normal here and is NOT a finding.

EVIDENCE CONTRACT - this is what separates a finding from an assertion
For EVERY finding output exactly this shape:

FINDING: <class> | <path>:<line> | <one-line claim>
EXHIBIT:
  <line-no>: <source line, copied character for character>
  <line-no>: <the next relevant line, and so on - between 2 and 8 lines>
REPRO: <the exact command you ran, in this room>
  ---> <its actual output, pasted, not paraphrased>
TRACE: <input> -> <value at line N> -> <value at line M> -> <wrong output>
WHY: <what breaks, and for whom>
CONFIDENCE: VERIFIED or TRACED

Rules, all of them checked mechanically after you finish:
  - every EXHIBIT line must match the named file AT THE NAMED LINE NUMBER, character for character.
    A line number past end-of-file, or a path not in this room, invalidates the finding.
  - give EXACTLY ONE of REPRO or TRACE. Use REPRO (CONFIDENCE: VERIFIED) whenever you could actually
    run something. Use TRACE (CONFIDENCE: TRACED) only when you could not, and then it must name at
    least TWO intermediate line numbers - a trace stating only input and output is an assertion
    wearing evidence's clothes, and it will be dropped.
  - at most 6 findings per class. If you have more, report the 6 that matter most.

DO NOT REPORT: style, naming, formatting, missing type hints, "extract this function", "use
pathlib", performance, or the absence of a tests directory - all of those are either already gated
elsewhere or unactionable in this repo.

If this script has no defects in these classes, output the single line: NO FINDINGS

Then end with a section headed "Unmeasured": what you could not verify and why - needed a host, a
browser, a network, root, or a dependency you were told not to install. A reviewer that could not
run anything must say so here rather than return a clean report.
"""


def build_prompt(name, prefix="bitranox"):
    """The reviewer contract for one skill. `prefix` is the plugin's skill namespace."""
    return PROMPT.format(name=name, prefix=prefix)


def _bullets(items, empty="(none)"):
    """Render a list into the prompt's indented block form."""
    items = [str(i) for i in items if str(i).strip()]
    if not items:
        return "  " + empty
    return "\n".join("  " + i for i in items)


def build_script_prompt(rel, kind, anchors=(), mentions="", registration=None, tests=(),
                        prepass=(), prefix="bitranox", leads=()):
    """The reviewer contract for one script.

    Deliberately `%`-formatted, not `str.format`: a script prompt quotes a hook's JSON output
    (`{"hookSpecificOutput": ...}`) and `.format` raises KeyError on those braces."""
    if kind in (KIND_HOOK, KIND_HOOK_LIB, KIND_SHIM):
        conventions = _HOOK_CONVENTIONS
    else:
        conventions = _TOOL_CONVENTIONS
    if registration:
        reg = ("\nHOW THIS HOOK IS REGISTERED (from hooks/hooks.json - the contract it must honour)\n"
               + _bullets("%s | matcher: %s | %s" % r for r in registration) + "\n")
    elif kind == KIND_HOOK:
        reg = ("\nHOW THIS HOOK IS REGISTERED: it is NOT registered in hooks/hooks.json, so it can\n"
               "never fire. Treat that as a finding unless the file itself explains why.\n")
    else:
        reg = ""
    return SCRIPT_PROMPT % {
        "rel": rel,
        "kind": kind,
        "prefix": prefix,
        "conventions": conventions,
        "tests": ", ".join(str(t) for t in tests) or "(none found - do not report that as a finding)",
        "anchors": ", ".join(str(a) for a in anchors) or "(none)",
        "registration": reg,
        "mentions": mentions.rstrip() or "  (the shipped docs never name this file)",
        "prepass": _bullets(prepass, "(nothing - the pre-pass found no mechanical hits here)"),
        "leads": _bullets(leads, "(nothing - the pre-pass raised no leads on this file)"),
        "donotrun": ("DO NOT RUN THIS SCRIPT AT ALL beyond `--help`. Its name says it mutates a real\n"
                     "host, store, or process, and this room cannot contain that."
                     if DO_NOT_RUN_RX.search(str(rel)) else
                     "This script may be run inside the room."),
    }


def skill_names(plugin_dir, only=()):
    """Every skill in `plugin_dir/skills` that ships a SKILL.md, sorted. `only` filters by name."""
    skills = Path(plugin_dir) / "skills"
    wanted = {s for s in only if s}
    if not skills.is_dir():
        return []
    return sorted(d.name for d in skills.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file() and (not wanted or d.name in wanted))


def _exclusions(room, log=None):
    """The gate's own exclusion sets, so this sweep cannot drift from the rule it enforces.

    A room staged from a loose `--skills-dir` has no `hooks/`, so a fallback copy exists - but a
    silently-degraded exclusion rule is how a sweep quietly reviews 300 vendored examples, so the
    fallback announces itself."""
    hooks = Path(room) / "hooks"
    if hooks.is_dir():
        sys.path.insert(0, str(hooks))
        try:
            import harness_checks  # noqa: PLC0415 - loaded from the room, not importable at module scope
            return frozenset(harness_checks.EXCLUDE_DIRS), frozenset(harness_checks.EXCLUDE_FILES)
        except Exception:
            pass
    if log:
        log("NOTE: harness_checks not importable from the room - using the fallback exclusion sets")
    return _FALLBACK_EXCLUDE_DIRS, _FALLBACK_EXCLUDE_FILES


def classify_script(rel):
    """What kind of unit a room-relative script path is.

    The hyphen/underscore split mirrors `harness_checks.orphan_scripts`: in `hooks/`, a hyphenated
    name is an entry point that hooks.json invokes, an underscored one is an importable module."""
    rel = str(rel).replace("\\", "/")
    parts = rel.split("/")
    stem, suffix = parts[-1].rsplit(".", 1) if "." in parts[-1] else (parts[-1], "")
    if any(p in _VENDORED_DIRS for p in parts):
        return KIND_VENDORED
    if parts[0] == "hooks":
        if suffix == "sh":
            return KIND_SHIM
        return KIND_HOOK if "-" in stem else KIND_HOOK_LIB
    if suffix == "js":
        return KIND_JS
    return KIND_SKILL_SCRIPT


def report_stem(rel):
    """A PATH-derived report name.

    Basenames collide: `gate.py` exists twice and `client.py` six times under the vendored demos.
    Naming a report after the basename writes 120 files for 134 targets while printing 134 - the
    same silent shadowing `repo_gate.check_duplicate_basenames` exists to prevent, reproduced inside
    the auditor."""
    rel = str(rel).replace("\\", "/")
    if rel.endswith(".py") or rel.endswith(".js") or rel.endswith(".sh"):
        rel = rel.rsplit(".", 1)[0]
    return rel.replace("/", "__")


def script_targets(room, only=(), include_vendored=False, kinds=(), log=None):
    """Every reviewable script in the room, sorted. Returns [(rel, kind)].

    `only` matches path substrings, so `--only repo-gate,compuse-toolbox/scripts` works."""
    room = Path(room)
    ex_dirs, ex_files = _exclusions(room, log)
    ex_dirs = (ex_dirs | _EXTRA_EXCLUDE_DIRS) - (_VENDORED_DIRS if include_vendored else frozenset())
    wanted = {s.strip() for s in only if str(s).strip()}
    kinds = {k.strip() for k in kinds if str(k).strip()}
    found = []
    for base, patterns in (("hooks", ("*.py", "*.sh")), ("skills", ("*.py", "*.js"))):
        root = room / base
        if not root.is_dir():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                rel = path.relative_to(room).as_posix()
                parts = rel.split("/")
                if any(p in ex_dirs for p in parts[:-1]) or parts[-1] in ex_files:
                    continue
                kind = classify_script(rel)
                if kind == KIND_VENDORED and not include_vendored:
                    continue
                if kinds and kind not in kinds:
                    continue
                if wanted and not any(w in rel for w in wanted):
                    continue
                found.append((rel, kind))
    return sorted(set(found))


def doc_anchors(room, rel, kind, limit=6):
    """The room-relative docs that make claims about `rel`, most authoritative first."""
    room, rel = Path(room), str(rel).replace("\\", "/")
    parts = rel.split("/")
    out = []
    if kind in (KIND_HOOK, KIND_HOOK_LIB, KIND_SHIM):
        out = ["hooks/hooks.json", "hooks/CLAUDE.md", "CLAUDE.md",
               "skills/meta-claude-hooks/SKILL.md"]
    elif len(parts) > 1 and parts[0] == "skills":
        own = "skills/%s" % parts[1]
        out = ["%s/SKILL.md" % own]
        out += sorted(p.relative_to(room).as_posix() for p in (room / own).rglob("*.md")
                      if p.name != "SKILL.md")
    return [a for a in out if (room / a).is_file()][:limit]


def hook_registration(room, rel):
    """The hooks.json entries that invoke `rel`, as [(event, matcher, command)], or None."""
    path = Path(room) / "hooks" / "hooks.json"
    name = str(rel).replace("\\", "/").split("/")[-1]
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    out = []
    for event, groups in (data.get("hooks") or data).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for entry in group.get("hooks") or []:
                command = str(entry.get("command", ""))
                if name in command:
                    out.append((event, str(group.get("matcher", "*")), command))
    return out or None


def mention_block(room, rel, anchors, limit=40):
    """Every line in `anchors` naming this file, `path:line: text`, capped.

    This is what turns "does this script match its documentation" from `read the plugin` into
    `check six lines` - and it is why the reviewer never needs the whole catalogue."""
    room = Path(room)
    name = str(rel).replace("\\", "/").split("/")[-1]
    lines = []
    for anchor in anchors:
        try:
            text = (room / anchor).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if name in line:
                lines.append("  %s:%d: %s" % (anchor, n, line.strip()[:200]))
                if len(lines) >= limit:
                    return "\n".join(lines) + "\n  ... (truncated at %d mentions)" % limit
    return "\n".join(lines)


def sibling_tests(room, rel, limit=3):
    """Test modules that name this script's stem, nearest package first."""
    room, rel = Path(room), str(rel).replace("\\", "/")
    parts = rel.split("/")
    stem = parts[-1].rsplit(".", 1)[0]
    out = []
    for depth in range(len(parts) - 1, 0, -1):
        tests = room.joinpath(*parts[:depth]) / "tests"
        if not tests.is_dir():
            continue
        for path in sorted(tests.rglob("test_*.py")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if stem in text or stem.replace("-", "_") in text:
                out.append(path.relative_to(room).as_posix())
        if out:
            break
    return out[:limit]


_FINDING_RX = re.compile(r"^FINDING:\s*([A-Z-]+)\s*\|\s*([^|]+?)\s*\|", re.M)
_EXHIBIT_LINE_RX = re.compile(r"^\s+(\d+):\s?(.*)$")


def count_findings(text):
    """How many findings a report claims. `NO FINDINGS` and an empty report both count 0."""
    return (text or "").count("FINDING:")


# Written as the first line of a stored report whose reviewer never produced one, so the file is
# self-describing and every later reader - the run summary, --skip-existing, a person - sees it.
REPORT_MISSING_MARKER = "REPORT MISSING:"


def report_is_complete(text):
    """Does this stored text carry a reviewer REPORT, rather than whatever else was said last?

    A report is `NO FINDINGS` or at least one `FINDING:` line. Nothing else counts, and the
    marker below explicitly does not: a clobbered report is non-empty, which is the only thing
    `--skip-existing` used to ask, so a resume skipped exactly the targets that were never
    reviewed.
    """
    body = text or ""
    if body.startswith(REPORT_MISSING_MARKER):
        return False
    return "FINDING:" in body or "NO FINDINGS" in body


def store_report(path, name, out):
    """Write a reviewer's output as the report for `name`, and say so when it is not one.

    The decision-review Stop hook fires on each reviewer subagent, so its final stdout can be a
    decision review instead of the report. Stored wholesale that text counts 0 findings and reads
    exactly like a clean skill. Measured over one 47-target sweep: 6 clobbered, one of them a
    target whose transcript carried 9 findings.

    A missing report is itself a defect, so it is recorded as a finding: the run summary then
    cannot call the target clean, and the raw reply is kept underneath because it is the only copy
    outside the reviewer's transcript.
    """
    body = out or ""
    if not report_is_complete(body):
        body = (
            "%s the reviewer's final message carried no report block (no FINDING: line, no "
            "NO FINDINGS). A Stop-hook decision review replaces it. Raw reply kept below.\n"
            "FINDING: REPORT-MISSING | %s | the reviewer produced no report; re-run this target\n\n"
            % (REPORT_MISSING_MARKER, name)
        ) + body
    Path(path).write_text(body, encoding="utf-8")
    return body


def count_by_class(text):
    """Findings per class, so a prompt that stopped producing a class is visible."""
    out = {c: 0 for c in SCRIPT_CLASSES}
    for cls, _path in _FINDING_RX.findall(text or ""):
        out[cls] = out.get(cls, 0) + 1
    return out


def evidence_problems(text, room):
    """Every EXHIBIT line that does not match its file at its stated line number.

    The skill sweep needs a human to `grep -F` each quote; at 134 targets that does not happen, so
    the same rule is enforced here mechanically. The result is APPENDED to the report and never used
    to delete a finding: deleting hides a reviewer that is malfunctioning, and the count of
    unverifiable findings is itself the signal for whether the prompt is working."""
    room = Path(room)
    problems, current, cache = [], None, {}
    for raw in (text or "").splitlines():
        head = _FINDING_RX.match(raw)
        if head:
            current = head.group(2).rsplit(":", 1)[0] if ":" in head.group(2) else head.group(2)
            current = current.strip()
            continue
        hit = _EXHIBIT_LINE_RX.match(raw)
        if not hit or current is None or not raw.strip():
            continue
        n, body = int(hit.group(1)), hit.group(2)
        if current not in cache:
            path = room / current
            try:
                cache[current] = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                cache[current] = None
        lines = cache[current]
        if lines is None:
            problems.append("%s: no such file in the room" % current)
        elif n < 1 or n > len(lines):
            problems.append("%s:%d: line number past end of file (%d lines)" % (current, n, len(lines)))
        elif lines[n - 1].rstrip() != body.rstrip():
            problems.append("%s:%d: exhibit does not match the file" % (current, n))
    return problems


def prepare_room(plugin_src, room_root, reuse=False):
    """Copy the plugin into `<room_root>/plugin` and make `<room_root>/reports`. Returns the copy.

    The room belongs OUTSIDE the knowledge tree: a reviewer whose cwd sits inside it also picks up
    the tree's CLAUDE.md cascade, which is a second contamination route on top of recall."""
    room_root = Path(room_root)
    room = room_root / "plugin"
    (room_root / "reports").mkdir(parents=True, exist_ok=True)
    if room.exists() and not reuse:
        shutil.rmtree(room)
    if not room.exists():
        shutil.copytree(Path(plugin_src), room,
                        ignore=shutil.ignore_patterns(".skillwriter", "__pycache__", "*.pyc"))
    return room


def room_manifest(room):
    """sha256 per file in the room, so a reviewer that edits it is caught.

    A reviewer that "fixes" a shared module makes every later reviewer of an importing file review a
    different program, and nothing else would show it."""
    room = Path(room)
    out = {}
    for path in sorted(room.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[path.relative_to(room).as_posix()] = digest
    return out


def manifest_drift(before, after):
    """What changed between two `room_manifest` snapshots, as sorted human lines."""
    out = []
    for rel in sorted(set(before) | set(after)):
        if rel not in after:
            out.append("REMOVED %s" % rel)
        elif rel not in before:
            out.append("ADDED   %s" % rel)
        elif before[rel] != after[rel]:
            out.append("CHANGED %s" % rel)
    return out


def _subprocess_runner(prompt, cwd, model, timeout):
    """Default reviewer: a headless `claude -p` whose cwd is the clean room.

    `encoding` is explicit: `text=True` alone decodes with the machine's locale codec, which on a
    non-UTF-8 Windows returns stdout=None from a reader thread and raises on POSIX."""
    try:
        proc = subprocess.run(["claude", "-p", "--model", model], cwd=str(cwd), input=prompt,
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout)
        return (proc.stdout or "").strip() or ("(no stdout) " + (proc.stderr or "").strip()[:400])
    except subprocess.TimeoutExpired:
        return "(TIMEOUT after %ss)" % timeout


def audit_one(name, room, reports_dir, model="sonnet", timeout=900, prefix="bitranox",
              runner=_subprocess_runner):
    """Review one skill and write its report. `runner` is the injectable reviewer seam."""
    out = runner(build_prompt(name, prefix), room, model, timeout)
    path = Path(reports_dir) / ("%s.audit.txt" % name)
    stored = store_report(path, name, out)
    return name, count_findings(stored)


def audit_one_script(target, room, reports_dir, model="opus", timeout=1500, prefix="bitranox",
                     runner=_subprocess_runner, prepass=None, leads=None):
    """Review one script and write its report, with the evidence post-pass appended."""
    rel, kind = target
    anchors = doc_anchors(room, rel, kind)
    prompt = build_script_prompt(
        rel, kind,
        anchors=anchors,
        mentions=mention_block(room, rel, anchors),
        registration=hook_registration(room, rel) if kind in (KIND_HOOK, KIND_SHIM) else None,
        tests=sibling_tests(room, rel),
        prepass=(prepass or {}).get(rel, ()),
        leads=(leads or {}).get(rel, ()),
        prefix=prefix,
    )
    out = runner(prompt, room, model, timeout)
    problems = evidence_problems(out, room)
    if problems:
        out = out + "\n\nUNVERIFIABLE EVIDENCE:\n" + "\n".join("  " + p for p in problems) + "\n"
    stored = store_report(Path(reports_dir) / ("%s.audit.txt" % report_stem(rel)), rel, out)
    return rel, count_findings(stored)


def prepare_room_from_skills(skills_dir, room_root, hooks_dir=None, reuse=False):
    """Stage a loose `skills/` dir as a plugin-shaped room. Returns the room's plugin dir.

    `prepare_room` copies the WHOLE plugin dir, which is right for a plugin and ruinous for a
    skills dir whose parent is `~/.claude`: reviewing two personal skills would copy gigabytes of
    transcripts, caches and installed plugins. Stage only what a reviewer reads."""
    room_root = Path(room_root)
    room = room_root / "plugin"
    (room_root / "reports").mkdir(parents=True, exist_ok=True)
    if room.exists() and not reuse:
        shutil.rmtree(room)
    room.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns(".skillwriter", "__pycache__", "*.pyc", ".pytest_cache", ".git")
    if not (room / "skills").exists():
        shutil.copytree(Path(skills_dir), room / "skills", ignore=ignore)
    if hooks_dir and Path(hooks_dir).is_dir() and not (room / "hooks").exists():
        shutil.copytree(Path(hooks_dir), room / "hooks", ignore=ignore)
    return room


def _run_pool(jobs, items, work, log):
    """Run `work` over `items` at `jobs` concurrency, logging each result. Returns {key: count}."""
    results = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = {ex.submit(work, item): item for item in items}
        for fut in cf.as_completed(futs):
            key, n = fut.result()
            results[key] = n
            log("%-52s %s" % (key, "clean" if not n else "%d finding(s)" % n))
    return results


def audit_all(plugin_src, room_root, model="sonnet", jobs=6, timeout=900, only=(),
              prefix="bitranox", reuse=False, runner=_subprocess_runner, log=print,
              skills_dir=None, hooks_dir=None):
    """Audit every selected skill. Returns {skill: finding_count}."""
    if skills_dir:
        room = prepare_room_from_skills(skills_dir, room_root, hooks_dir, reuse=reuse)
    else:
        room = prepare_room(plugin_src, room_root, reuse=reuse)
    reports = Path(room_root) / "reports"
    names = skill_names(room, only)
    log("auditing %d skill(s) in %s with %d job(s)" % (len(names), room, jobs))
    results = _run_pool(jobs, names,
                        lambda n: audit_one(n, room, reports, model, timeout, prefix, runner), log)
    log("DONE: %d finding(s) across %d skill(s)" % (sum(results.values()), len(names)))
    return results


def _default_prepass(room, targets):
    """The real pre-pass over the room, as (facts, leads, summary)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import script_prepass  # noqa: PLC0415 - sibling script, resolved from this file's own dir
    vendored = script_prepass.vendored_targets(sys.modules[__name__], room)
    return script_prepass.run_prepass(room, targets, vendored=vendored)


def _prepass_maps(room, targets, log=print, compute=None):
    """The deterministic pre-pass, run over the same room the reviewers read.

    Computed HERE rather than handed down from `main()`, because it was handed down from nowhere:
    `prepass=` was threaded through three signatures and no caller ever supplied one, so every
    reviewer read "(nothing - the pre-pass found no mechanical hits here)" while the pre-pass sat
    unused and 133 reviewers re-derived the same 28 lines. A producer with no consumer passes its
    own unit tests. The parameters stay, as the injection seam the tests use.

    RAISES rather than degrading. Fail-open is wrong here specifically because the degraded output
    is INDISTINGUISHABLE from success: an empty map renders as "the pre-pass found no mechanical
    hits here", so a broken pre-pass would send every reviewer out to re-derive the same hits at
    full price, and the only trace would be one NOTE scrolling past in a run that prints hundreds.
    A hook fails open because a wedged turn is worse than a missed check; a sweep is the opposite
    trade - it is long, it is paid for per target, and it is trivial to restart.

    `compute` is the injection seam, defaulting to the real pre-pass - the same shape as `runner`
    here and `run` in script_prepass. Injected rather than reached for directly so the abort path
    can be tested with a collaborator that genuinely fails: a broken ROOM does not raise (rglob
    over a non-directory returns empty), so a fixture built that way asserts nothing."""
    compute = _default_prepass if compute is None else compute
    try:
        facts, leads, summary = compute(room, targets)
    except Exception as exc:
        raise RuntimeError(
            "the pre-pass could not run over %s (%s) - refusing to start the sweep, because every "
            "reviewer would be told nothing is already known and would re-derive it" % (room, exc)
        ) from exc
    for line in summary:
        log("  pre-pass: " + line)
    return facts, leads


def audit_scripts(plugin_src, room_root, model="opus", jobs=4, timeout=1500, only=(),
                  prefix="bitranox", reuse=False, runner=_subprocess_runner, log=print,
                  kinds=(), include_vendored=False, skip_existing=False, prepass=None,
                  leads=None):
    """Audit every selected script. Returns {rel: finding_count}.

    A sibling of `audit_all` rather than a mode flag on it: `audit_all` already takes twelve
    parameters whose positional order is baked into `main()` and into the existing tests, and
    inserting anything before `runner` would silently shift a caller's `only` into `prefix`."""
    room = prepare_room(plugin_src, room_root, reuse=reuse)
    reports = Path(room_root) / "reports"
    targets = script_targets(room, only, include_vendored, kinds, log)
    if skip_existing:
        keep = []
        for rel, kind in targets:
            report = reports / ("%s.audit.txt" % report_stem(rel))
            # Non-empty is not reviewed: a clobbered report is non-empty by construction, which is
            # how a resume skipped precisely the targets that never got a report.
            if report.is_file() and report_is_complete(report.read_text(encoding="utf-8")):
                continue
            keep.append((rel, kind))
        log("resuming: %d of %d target(s) still need a reviewer" % (len(keep), len(targets)))
        targets = keep
    if prepass is None and leads is None:
        prepass, leads = _prepass_maps(room, targets, log)
    log("auditing %d script(s) in %s with %d job(s)" % (len(targets), room, jobs))
    before = room_manifest(room)
    results = _run_pool(jobs, targets,
                        lambda t: audit_one_script(t, room, reports, model, timeout, prefix,
                                                   runner, prepass, leads), log)
    drift = manifest_drift(before, room_manifest(room))
    if drift:
        log("WARNING: the room changed under the sweep - later reviewers read a different program:")
        for line in drift[:20]:
            log("  " + line)
    log("DONE: %d finding(s) across %d script(s)" % (sum(results.values()), len(targets)))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit shipped skills or scripts in a clean room.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--plugin", help="the plugin dir to audit (holds skills/, hooks/)")
    src.add_argument("--skills-dir", dest="skills_dir",
                     help="a loose skills/ dir to audit - staged into the room on its own, so a "
                          "huge parent like ~/.claude is never copied")
    ap.add_argument("--hooks-dir", dest="hooks_dir", default="",
                    help="with --skills-dir: a hooks dir to stage alongside, so a skill's "
                         "reference to a sibling hook still resolves in the room")
    ap.add_argument("--room", required=True, help="clean-room root, OUTSIDE the knowledge tree")
    ap.add_argument("--model", default="")
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated skill names, or path substrings "
                                               "in --scripts mode; else all")
    ap.add_argument("--prefix", default="bitranox", help="the plugin's skill namespace")
    ap.add_argument("--reuse-room", action="store_true", help="keep an existing plugin copy")
    ap.add_argument("--scripts", action="store_true",
                    help="review shipped scripts instead of skills")
    ap.add_argument("--kind", action="append", default=[],
                    help="with --scripts: restrict to hook/hook-lib/shim/skill-script/js "
                         "(repeatable) - this is how a 134-target run becomes survivable slices")
    ap.add_argument("--include-vendored", action="store_true",
                    help="with --scripts: also review demos/ and examples/ (upstream sample code, "
                         "excluded by default because a fix there diverges from upstream)")
    ap.add_argument("--skip-existing", action="store_true",
                    help="with --scripts: skip a target whose report already exists and is "
                         "non-empty - the resume switch; pairs with --reuse-room")
    ap.add_argument("--list", action="store_true",
                    help="print the enumerated corpus and exit without spending a reviewer")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    only = tuple(s.strip() for s in args.only.split(","))

    if args.list:
        room = Path(args.room) / "plugin"
        room = room if room.is_dir() else Path(args.plugin or args.skills_dir or ".")
        if args.scripts:
            targets = script_targets(room, only, args.include_vendored, tuple(args.kind))
            for rel, kind in targets:
                print("%-12s %-58s -> %s" % (kind, rel, report_stem(rel)))
            print("TOTAL: %d script(s)" % len(targets))
        else:
            names = skill_names(room, only)
            for name in names:
                print(name)
            print("TOTAL: %d skill(s)" % len(names))
        return 0

    if args.scripts:
        audit_scripts(args.plugin, args.room, args.model or "opus", args.jobs or 4,
                      args.timeout or 1500, only, args.prefix, args.reuse_room,
                      kinds=tuple(args.kind), include_vendored=args.include_vendored,
                      skip_existing=args.skip_existing)
        return 0
    audit_all(args.plugin, args.room, args.model or "sonnet", args.jobs or 6, args.timeout or 900,
              only, args.prefix, args.reuse_room,
              skills_dir=args.skills_dir, hooks_dir=args.hooks_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
