#!/usr/bin/env python3
"""PreToolUse(Write|Bash) nudge: you may be solving one job over and over. Judge, then build a jig.

Why this exists, next to toolbox-nudge.py: that hook matches a fixed catalogue of signatures for
chores a jig ALREADY exists for, so it answers "do we have a tool for this?". It cannot fire for a
chore with no jig yet - there is no signature to match - which is exactly when a jig is most worth
building. Measured: six scripts that solved ONE job (delete C:\\Windows.old) were authored in one
session, each rewriting the previous approach, and the catalogue hook stayed silent through all six.

DIVISION OF LABOUR - the point of the design. "Is this the same job again?" is a SEMANTIC question,
and a lexical rule cannot answer it with both recall and precision, because a REWRITE is defined by
looking different while meaning the same. Three purely-lexical designs were measured against that
real 86-script session and all three failed: 3-gram shingle similarity peaked at 0.30 across the
delete lineage and never reached three kin; rare-token overlap fired on the first cluster of the
session and was then spent; per-cluster dedup smeared transitively until one nudge covered
everything. So the division is inverted here: the LEXICAL layer is only a loose RECALL filter that
deliberately over-triggers, and the MODEL supplies precision by reading the session LEDGER this
hook hands it and judging which entries are the same job. A hook is a shell command and cannot
dispatch a subagent; it can only hand over the context and say that dispatching one is an option.

TWO TRACKS, because one budget gets spent early. A session's read-only probes repeat constantly, so
a single-budget policy exhausts itself in the first quarter and is silent for the lineage that
matters. Measured by replaying that corpus through this module: a single clock-paced budget reached
the delete lineage in 0% of unperturbed replays and 45-66% with a tenth to a fifth of the session
dropped at random; these two budgets reach it in 100%, and in 96.7% at the heaviest perturbation.
A script that CHANGES state gets the looser gate and the larger budget - it is where a rewrite
costs a machine rather than a wrong answer.

WHAT COUNTS AS A JOB, which is where the noise was. Replaying 2689 script writes from 98 sessions
(one session had supplied every constant here) said the pacing was about right and the IDENTITY of
a variant was not: a group of three reached three by counting things that are not three attempts
at one job. Two spellings of one path are one file, and a pytest module is not a one-off script at
all - it is the very artefact the message asks for, and test-suite files are a quarter of all
script writes. In the other direction a numbered family - `probe.ps1`, `probe2.ps1`, `probe3.ps1` -
was invisible, because a short shared stem yields ONE name token where the topic channel needs two.
See same_file, is_test_suite_file, numbered_retry.

Non-blocking (additionalContext), capped per session, silent on any error.
"""
import json
import re
import sys
from pathlib import Path

from shell_text import HEREDOC_OPEN               # noqa: E402 - shared with the other command guards

SCRIPT_SUFFIXES = {".ps1", ".py", ".sh", ".bash", ".psm1"}
VARIANTS_BEFORE_NUDGE = 3        # a group of three is the smallest that shows a PATTERN, not a retry
# Jaccard over 3-token shingles; unrelated scripts score ~0. This is the narrowest of the three
# recall channels by a wide margin: over 98 replayed sessions, moving it anywhere from 0.25 to 0.5
# changes no session's nudges at all, because a true near-COPY is rarer than a rewrite and the
# topic channel already has those. Kept because it is the only channel that survives a rename.
SIMILARITY = 0.25

# How many of the group's scripts must not have been named in an earlier nudge. Without it, one
# nudge's group grows by a script at a time and re-fires on every write; with it, a repeat costs
# three genuinely new scripts. This, not a clock, is what paces the hook.
FRESH_SCRIPTS_PER_NUDGE = 3

# Separate budgets. CHANGE = the script being written mutates state; OBSERVE = it only reads.
# Both BIND, so they are policy rather than a runaway guard: across 98 replayed sessions they
# withheld 27 and 365 further nudges. 12 is not slack on the change track either - it is the
# smallest value that still reaches the destructive lineage this hook was built for, which arrives
# as that session's 11th change nudge; at 8 the lineage is never reported.
CHANGE_NUDGE_CAP = 12
# The observe track is where a session's repetition is cheap and constant, so it stays tight: the
# evidence justified 620 observe nudges across those sessions and this cap withheld 365 of them.
OBSERVE_NUDGE_CAP = 3
OBSERVE_COOLDOWN = 15            # scripts between observe-track nudges; repeated probes are cheap

LEDGER_LIMIT = 200               # bound the state file on a marathon session
LEDGER_WINDOW = 20               # ledger entries handed to the model; older work is rarely the job
PURPOSE_WIDTH = 100
# Per-entry cap on the stored shingle sample, because the state file is read AND rewritten on every
# script write and the shingles dominate its size. 120 was measured, not guessed: over all 6903
# pairs of the real corpus it reproduces the full-fidelity near-copy verdict exactly - 0 near-copies
# missed and 0 invented - while storing 68% of the shingles. Dropping to 80 starts missing them.
SHINGLE_LIMIT = 120

# `cat > x.ps1 <<'EOS'` / `cat >> x.py <<EOF` - the redirect target on a heredoc opener line.
_REDIRECT = re.compile(r">>?\s*(['\"]?)([^\s'\";|&<>]+)\1")


def heredoc_writes(command):
    """[(path, body)] for every heredoc in `command` that writes a SCRIPT file. PURE.

    A guard is only as wide as its matcher, and a Bash event carries `command`, not a file_path.
    Scripts authored as `cat > f.ps1 <<'EOS' ... EOS` are therefore invisible to a Write-only
    hook - which is how six near-duplicate scripts were authored past this very nudge, since
    heredocs were how nearly all of them were written.
    """
    out = []
    lines = (command or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        opener = HEREDOC_OPEN.search(line)
        i += 1
        if not opener:
            continue
        delimiter = opener.group(2)
        body = []
        while i < len(lines) and lines[i].strip() != delimiter:
            body.append(lines[i])
            i += 1
        i += 1                                        # drop the terminator
        # The redirect target must come from the text BEFORE the `<<`, or `<<'EOS'` itself and any
        # redirect inside the body would be mistaken for the destination.
        #
        # Take the LAST redirect whose target is a SCRIPT, not the first redirect of any kind.
        # Real command lines routinely carry an unrelated redirect ahead of the heredoc -
        # `D=$(ls ... 2>/dev/null); cd "$D" && cat > probe.sh <<'EOS'` - and matching the first
        # hands back /dev/null, whose suffix is not a script, so the write is dropped in silence.
        # Measured live: three scripts authored, one recorded, no nudge. Filtering by suffix also
        # makes the ORDER of the redirects irrelevant (`cat > f.sh 2>/dev/null <<EOS` works too).
        head = line[:opener.start()]
        targets = [m.group(2) for m in _REDIRECT.finditer(head)
                   if Path(m.group(2)).suffix.lower() in SCRIPT_SUFFIXES]
        if targets:
            out.append((targets[-1], "\n".join(body)))
    return out


_COMMENT = re.compile(r"(^\s*#.*$)|(^\s*//.*$)", re.M)
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]{2,}")


def shingles(text):
    """Set of 3-token shingles from `text`, comments stripped. PURE - unit-testable.

    Shingles rather than a bag of words: two unrelated PowerShell scripts share plenty of single
    tokens (param, foreach, Write-Host) but almost no ordered triples, so this separates
    copy-paste lineage from "same language" instead of firing on every script pair.
    """
    body = _COMMENT.sub("", text or "")
    toks = [t.lower() for t in _TOKEN.findall(body)]
    return {tuple(toks[i:i + 3]) for i in range(len(toks) - 2)}


def similarity(a, b):
    """Jaccard overlap of two shingle sets. PURE."""
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


# ----------------------------------------------------------------------------- purpose + topic

_SHEBANG = re.compile(r"^\s*#!")
_LINE_COMMENT = re.compile(r"^\s*(?:\#|//|<\#|\"\"\"|''')\s*(.*)$")
# Preamble a script opens with that says nothing about its JOB. Skipping it matters twice over: it
# is what the model is shown as the script's purpose, and every script that opens the same way
# would otherwise look like every other one.
_BOILERPLATE = re.compile(r"""(?xi) ^\s* (?:
      \$(?:ErrorActionPreference|ProgressPreference|WarningPreference|VerbosePreference|PSStyle)\b
    | set \s+ -[eux]+ \b | set \s+ -o \s+ pipefail
    | \#\s*-\*-\s*coding | from \s+ __future__ | \#\s*noqa | \#\s*type:
    | (?:import|from) \s+ [\w.]+ | using \s+ namespace
    | \[CmdletBinding | param \s* \( | \#\s*$
    ) """)


def purpose(text, width=PURPOSE_WIDTH):
    """One line saying what this script is FOR. PURE.

    The first real comment line, else the opening lines of code. This is the only part of a script
    the model is shown for every ledger entry, so it has to survive being the ONLY thing shown:
    a shebang or an $ErrorActionPreference line is skipped because it identifies nothing.
    """
    opener = []
    for line in (text or "").replace("\r\n", "\n").split("\n")[:15]:
        stripped = line.strip()
        if not stripped or _SHEBANG.match(line):
            continue
        commented = _LINE_COMMENT.match(line)
        if commented:
            said = commented.group(1).strip()
            if said and not _BOILERPLATE.match(line):
                return said[:width]
            continue
        if _BOILERPLATE.match(line):
            continue
        opener.append(stripped)
        if len(opener) >= 3 or sum(len(x) for x in opener) >= width:
            break
    return " ".join(opener)[:width]


_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_.]{2,}")
_STOPWORDS = frozenset("""the a an and or of to in for on at by with from into out this that these
those it its is are was were be been being do does did done not no yes if then else when while how
why what which who run runs running use uses using make makes made get gets got set sets take takes
only just also very so but as can could will would should must may might one two three first second
next last same other each every all any some more most less least here there now than per via even
still both after before during until since again another new old real actually really actual write
host echo print true false null none elif endif fi esac""".split())


def _stem(word):
    """Crude 5-character stem: delete/deleted/deleting collapse, delrobo/delsafe do not. PURE."""
    return word.lower().strip(".")[:5]


def basename(path):
    """The final component of `path`, whichever separator it uses. PURE.

    Not Path(...).name: a Windows event carries `C:\\scratch\\del.ps1`, and a POSIX interpreter
    does not treat the backslash as a separator, so the DIRECTORY would be read as part of the
    topic - and every script written into one scratch directory would share a token with every
    other one, on Windows only.
    """
    return re.split(r"[\\/]", str(path or ""))[-1]


def _file_stem(path):
    """The basename of `path` without its suffix. PURE."""
    return basename(path).rsplit(".", 1)[0]


def same_file(a, b):
    """Two paths that name ONE file. PURE.

    The ledger is keyed by path precisely so that iterating on a script is not counted as writing
    another variant of it - but the same file gets written as `tests/t.py` from the repo root and
    as `/abs/repo/tests/t.py` a minute later, and a string key cannot see that. Measured over 2689
    real script writes in 98 sessions: 133 respell a path already in the ledger, and 12 nudges
    named one file twice as though it were two attempts at a job.
    """
    parts_a = [p for p in re.split(r"[\\/]+", str(a or "")) if p not in ("", ".")]
    parts_b = [p for p in re.split(r"[\\/]+", str(b or "")) if p not in ("", ".")]
    if not parts_a or not parts_b:
        return False
    short, long_ = (parts_a, parts_b) if len(parts_a) <= len(parts_b) else (parts_b, parts_a)
    return long_[-len(short):] == short


_TRAILING_DIGITS = re.compile(r"\d+$")


def numbered_retry(a, b):
    """`probe.ps1` and `probe2.ps1`, `diag3.ps1` and `diag7.ps1`: the same script, attempt N. PURE.

    The strongest same-job signal the corpus has, and the topic channel cannot use it: a numbered
    family's shared stem is by construction NOT rare in that session, so the rarity gate that
    stops the junk group also discards the one name pattern that means "this again". Whole families
    stayed silent for it - nine `testN.sh`, seven `*_testN.py`, `probe1` through `probe9`.
    """
    stem_a, stem_b = _file_stem(a), _file_stem(b)
    if stem_a == stem_b:
        return False
    bare = _TRAILING_DIGITS.sub("", stem_a)
    return len(bare) >= 3 and bare == _TRAILING_DIGITS.sub("", stem_b)


def is_test_suite_file(path):
    """A pytest module rather than a one-off script. PURE.

    Restricted to `.py`, to the `test_` prefix pytest actually collects on, to `conftest.py` and to
    a `tests/` directory. Deliberately NOT the `_test` suffix: real one-off probes get called
    `era_test.py`, and suppressing those loses the repeats this hook exists to catch.
    """
    name = basename(path)
    if not name.lower().endswith(".py"):
        return False
    parts = [p for p in re.split(r"[\\/]+", str(path or "")) if p]
    return (name.startswith("test_") or name == "conftest.py"
            or any(p in ("tests", "test") for p in parts[:-1]))


def distinct_jobs(paths):
    """`paths` folded to one entry per JOB a jig could replace. PURE.

    Two spellings of one file are one job however many events they arrive as, and a pytest module
    is not a job at all: this hook's own remedy is "build it once as a TESTED JIG - a script with
    pytest cases", so a session filling up tests/ is producing the END STATE it asks for, and
    counting that as a repeated job nudges the one behaviour it wants. A quarter of the 2689
    script writes measured across 98 real sessions are test-suite files, and every session this
    rule silenced had been nudged for writing a module beside its tests.

    The unfolded group is still what the message shows: the model is handed evidence, so it should
    see the files it was actually given.
    """
    kept = []
    for path in paths:
        if is_test_suite_file(path) or any(same_file(path, other) for other in kept):
            continue
        kept.append(path)
    return kept


def name_tokens(name):
    """Topic tokens from a FILENAME. PURE.

    The 3-character prefix is the load-bearing one: delwinold / delrobo / delsafe / delprogress
    share no whole word and no 4-character prefix, but they are visibly one family, and on the real
    corpus adding it moved the delete lineage's first nudge six scripts earlier.
    """
    out = set()
    for part in re.split(r"[^A-Za-z0-9]+", Path(basename(name)).stem):
        part = re.sub(r"\d+$", "", part)          # delsafe2 is the same topic as delsafe
        if len(part) >= 3:
            out.add(_stem(part))
        if len(part) >= 5:
            out.add("~" + part[:3].lower())
        if len(part) >= 6:
            out.add(part[:4].lower())
    return out


def topic_tokens(name, script_purpose):
    """The loose topic signature of a script: what it is called plus what it says it does. PURE.

    Deliberately NOT the body. The body is where two scripts that solve one job by different means
    diverge most - that is what a rewrite IS - and body tokens measured as pure noise: every
    PowerShell script shares Get-ChildItem and Write-Host.
    """
    out = {"n:" + t for t in name_tokens(name)}
    for word in _WORD.findall(script_purpose or ""):
        stem = _stem(word)
        if len(stem) >= 4 and stem not in _STOPWORDS:
            out.add("p:" + stem)
    return out


# A script that CHANGES the machine. Deliberately broad - a false "this mutates" costs one extra
# consultation of the ledger, while a false "this only reads" is how a rewrite lineage stays silent.
CHANGES_STATE = re.compile(r"""(?xi) \b (?:
      remove-item | remove-itemproperty | move-item | rename-item | clear-content | new-itemproperty
    | set-acl | set-service | stop-service | start-service | restart-service | set-itemproperty
    | add-appxpackage | remove-appxpackage | restart-computer | stop-computer
    | takeown | icacls | robocopy | rd \s+ /s | rmdir | del \s+ / | erase \s+ /
    | reg \s+ (?:add|delete|import) | sc \s+ config | net \s+ (?:stop|start)
    | schtasks \s+ /(?:create|delete|change) | dism | mkfs | dd \s+ if=
    | rm \s+ -[rf] | systemctl \s+ (?:start|stop|restart|enable|disable|mask)
    | apt-get | apt \s+ (?:install|remove|upgrade) | pip \s+ install | chmod | chown
    | zfs \s+ (?:set|destroy|rollback) | zpool \s+ (?:destroy|replace)
    | qm \s+ (?:set|destroy|stop|start) | pct \s+ (?:set|destroy|stop|start)
) \b """)


def changes_state(text):
    """True when the script mutates machine state rather than only reading it. PURE."""
    return bool(CHANGES_STATE.search(text or ""))


# ----------------------------------------------------------------------------- kin detection

def _document_frequency(entries):
    df = {}
    for entry in entries:
        for token in entry.get("t") or []:
            df[token] = df.get(token, 0) + 1
    return df


def _shares_topic(tokens, entry, df, ledger_size, rare_shared_needed):
    """Two scripts look like the same topic. PURE.

    Two shared tokens, of which at least `rare_shared_needed` are rare in THIS session. The rarity
    gate is what stops the junk group: every script that opens with the same boilerplate shares
    those words, and without the gate they all read as one lineage.
    """
    shared = tokens & set(entry.get("t") or [])
    if len(shared) < 2:
        return False
    rare_max = max(2, int(ledger_size * 0.15))
    return sum(1 for token in shared if df.get(token, 0) <= rare_max) >= rare_shared_needed


def sketch(sh):
    """The bounded, deterministic shingle sample that gets stored AND compared. PURE.

    Both sides of every comparison must go through this. Comparing a live FULL set against a
    stored TRUNCATED one inflates the union without the intersection and silently biases the score
    down: measured on the real corpus, delrobo/delrobo_xj fell from 0.298 to 0.234 and stopped
    registering as the near-copy it is.
    """
    return set(sorted(sh)[:SHINGLE_LIMIT])


def _shares_text(sh, entry):
    """Two scripts are near-COPIES. PURE. The original signal, kept as a second recall channel."""
    return similarity(sketch(sh), {tuple(x) for x in entry.get("s") or []}) >= SIMILARITY


def find_kin(path, tokens, sh, entries, rare_shared_needed):
    """Every earlier script that might be the same job. PURE - the loose RECALL filter.

    Any channel is enough: topic (name plus stated purpose) catches a REWRITE, shingles catch a
    near-COPY, a numbered stem catches the retry that says so in its own filename. Keyed by file
    so iterating on ONE script replaces its entry instead of counting as a new variant - editing a
    script is not the same act as writing another one.
    """
    df = _document_frequency(entries)                 # once, not per candidate: this is a hot path
    kin = []
    for entry in entries:
        if same_file(entry.get("p"), path):
            continue
        if (_shares_topic(tokens, entry, df, len(entries), rare_shared_needed)
                or _shares_text(sh, entry)
                or numbered_retry(path, entry.get("p"))):
            kin.append(entry)
    return kin


def count_kin(store, path, sh):
    """Paths in `store` whose shingles resemble `sh`. PURE. Kept for the near-copy channel."""
    return [p for p, s in store.items()
            if p != path and similarity(sh, {tuple(x) for x in s}) >= SIMILARITY]


# ----------------------------------------------------------------------------- session state

def _state_path(session):
    from self_improve_signals import _audit_dir           # noqa: PLC0415 - shared audit dir helper
    return _audit_dir() / (str(session) + ".jig-ledger.json")


def _load(session):
    try:
        state = json.loads(_state_path(session).read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except Exception:                                     # noqa: BLE001 - absent/corrupt: start fresh
        return {}


def _save(session, state):
    try:
        path = _state_path(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
    except Exception:                                     # noqa: BLE001 - state must never break the hook
        pass


def _record(state, path, script_purpose, tokens, sh, mutates):
    entries = [e for e in state.get("entries") or [] if not same_file(e.get("p"), path)]
    entries.append({"p": path, "d": script_purpose, "t": sorted(tokens),
                    "s": [list(x) for x in sorted(sketch(sh))], "m": bool(mutates)})
    state["entries"] = entries[-LEDGER_LIMIT:]
    return state


def budget_allows(state, track, written):
    """Is this track allowed to spend a nudge now? PURE.

    Split by track so a session full of repeated read-only probes cannot exhaust the budget the
    destructive lineage needs - replaying the real corpus, one shared clock-paced budget reached
    that lineage in 0% of unperturbed runs and these two reach it in 100%.
    """
    if track == "change":
        return int(state.get("n_change") or 0) < CHANGE_NUDGE_CAP
    return (int(state.get("n_observe") or 0) < OBSERVE_NUDGE_CAP
            and written - int(state.get("last_observe") or -10 ** 6) >= OBSERVE_COOLDOWN)


def should_nudge(group, covered, state, track, written):
    """The whole firing rule, in one PURE place: enough JOBS, enough of them NEW, budget left.

    Counted in JOBS rather than paths, because a group of three has to be three attempts at one
    job before it is worth a word: two spellings of one file are one of them, and a pytest module
    is none.
    """
    jobs = distinct_jobs(group)
    fresh = distinct_jobs([p for p in group if not any(same_file(p, seen) for seen in covered)])
    return (len(jobs) >= VARIANTS_BEFORE_NUDGE
            and len(fresh) >= FRESH_SCRIPTS_PER_NUDGE
            and budget_allows(state, track, written))


# ----------------------------------------------------------------------------- the handover

def _ledger_lines(entries, limit=LEDGER_WINDOW):
    out = []
    for entry in entries[-limit:]:
        said = (entry.get("d") or "").strip() or "(no stated purpose)"
        out.append("  %s%s - %s" % (basename(entry.get("p") or "?"),
                                    " [changes state]" if entry.get("m") else "", said[:80]))
    return out


def build_message(group, entries, nth):
    """The additionalContext handed to the model. PURE - so its content is testable.

    It hands over EVIDENCE and a question, not a verdict. The lexical trigger below is loose on
    purpose and is wrong often; the model is the part of this system that can tell "the same job
    again" from "two scripts that happen to share a word", so it gets the ledger and decides.
    """
    names = ", ".join(basename(p) for p in group[:6])
    head = ("Possible REPEATED JOB (%s). These look related: %s.\n"
            "Scripts written this session (name - stated purpose):\n%s\n"
            % (("nudge %d this session" % nth) if nth > 1 else "first time this session", names,
               "\n".join(_ledger_lines(entries))))
    ask = ("JUDGE this yourself - the match above is LEXICAL and over-triggers by design. Read the "
           "purposes and decide whether THREE OR MORE of them are the same job solved again. "
           "Dispatch a cheap subagent for that judgement if you prefer to keep this off your own "
           "context.\n"
           "If they are: stop rewriting and build it once as a TESTED JIG - a script with pytest "
           "cases in the owning skill (bitranox:compuse-toolbox for a computer-use chore) - then "
           "call that. If a jig is already close, ENHANCE it rather than forking a variant. Each "
           "rewrite so far has carried the previous one's defects forward, and a rewrite that "
           "CHANGES STATE carries them onto a real machine.\n"
           "If they are NOT the same job, ignore this and carry on; say nothing about it.")
    return head + ask


# ----------------------------------------------------------------------------- entry point

def _written_scripts(event):
    """[(path, content)] of the script files this tool call authors. PURE."""
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    if tool == "Write":
        written = [(str(tool_input.get("file_path") or ""), tool_input.get("content") or "")]
    elif tool == "Bash":
        written = heredoc_writes(tool_input.get("command") or "")
    else:
        return []
    return [(p, c) for p, c in written if Path(p).suffix.lower() in SCRIPT_SUFFIXES]


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    candidates = _written_scripts(event)
    session = event.get("session_id") or ""
    if not candidates or not session:
        return 0

    state = _load(session)
    path, content = candidates[-1]                        # judge the last script this call writes
    for earlier, body in candidates[:-1]:                 # a multi-heredoc call still records them
        state = _record(state, earlier, purpose(body), topic_tokens(earlier, purpose(body)),
                        shingles(body), changes_state(body))

    said = purpose(content)
    tokens = topic_tokens(path, said)
    sh = shingles(content)
    mutates = changes_state(content)
    track = "change" if mutates else "observe"
    # A state-changing script needs only ONE rare shared token to count as kin: the cost of being
    # wrong is one extra look at the ledger, and the cost of missing is a machine.
    entries = state.get("entries") or []
    kin = find_kin(path, tokens, sh, entries, rare_shared_needed=1 if mutates else 2)
    group = [e.get("p") for e in kin] + [path]
    covered = set(state.get("covered") or [])
    written = len(entries) + 1

    fire = should_nudge(group, covered, state, track, written)
    if fire:
        state["covered"] = sorted(covered | set(group))
        key = "n_change" if track == "change" else "n_observe"
        state[key] = int(state.get(key) or 0) + 1
        if track == "observe":
            state["last_observe"] = written
        nth = int(state.get("n_change") or 0) + int(state.get("n_observe") or 0)
    state = _record(state, path, said, tokens, sh, mutates)
    _save(session, state)

    if fire:
        message = build_message(group, state.get("entries") or [], nth)
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": message}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                     # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
