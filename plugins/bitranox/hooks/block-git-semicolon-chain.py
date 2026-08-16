#!/usr/bin/env python3
"""PreToolUse(Bash) guard: two or more state-changing git verbs joined by `;` instead of `&&`.

`;` means "run the next one regardless". Chain `git commit ; git merge ; git push` and a commit
that refused still lets the merge and the push run - and those two answer a no-op with git's
calmest output, `Already up to date` and `Everything up-to-date`, both exit 0. The failure is
loud at step one and invisible everywhere after it, so the transcript reads like a completed
ship while the working tree never moved.

`&&` stops the chain where it broke. That is the whole fix, and it costs one character.

WHAT THIS GUARD REFUSES TO JUDGE
--------------------------------
A hook runs on a bare interpreter with no third-party packages, so there is no bash parser
available and this reads statement structure with a regex split. That instrument cannot model
block structure, and a guess there blocks correct work: an `if`/`else` runs exactly one branch,
a `for ... ; do ... ; done` needs its semicolons, and a subshell's internal `;` says nothing
about the statements around it. So when the command contains ANY block structure - a shell
keyword, a brace group, or a subshell paren - the guard stays SILENT rather than guess.

That is a deliberate accuracy-for-coverage trade. It gives up some real hits, and in exchange
every verdict it does give is one a flat statement list can actually support. The regions it
cannot see at all, and knowingly ignores: anything inside `eval`, `bash -c "..."`,
`ssh host '...'`, or a command substitution - it scans the LOCAL statement structure only.

THE TEST A FINDING HAS TO PASS
------------------------------
Would `&&` be correct advice here? If not, the guard must not fire, because its message says to
use `&&`. That is what rules out a REPEATED verb: `git push origin main ; git push origin topic`,
or a push to each of three repos, is parallel work over independent targets, and `&&` there is
actively wrong - you want the second attempted even when the first fails. A genuine dependency
chain moves through DIFFERENT verbs, which is the shape the incident had.

Two further shapes are exempt because they already say "continue deliberately":

- errexit active at that point in the command (`set -e`, `-euo pipefail`, `-o errexit`), which
  makes the shell itself abort on the first failure. Tracked positionally and revocably: a
  `set -e` AFTER the chain protects nothing, and a later `set +e` turns it back off;
- any `||` handler immediately after the state-changing statement - `|| true`, `|| exit 1`,
  `|| die "..."`. The author wrote the failure path, so the `;` after it is intentional.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and shows
stderr to the model; every other path (including any error) exits 0 so a broken guard never wedges
a turn.
"""
import json
import re
import sys

# Shared with the other command-scanning guards. `mask_data_regions` replaces quoted strings,
# command substitutions and comments INCLUDING their delimiters, so each becomes a single token -
# without that, `git -C "$MAIN" commit` splits into two bare `"` tokens and the verb is lost.
from shell_text import mask_data_regions, strip_heredoc_bodies

# Verbs whose failure invalidates whatever the author wrote next. Read-only verbs (status, log,
# diff, rev-parse) are deliberately absent: a failed `git log` does not make the following step
# wrong, so chaining those with `;` is ordinary and must not be blocked.
#
# `fetch` earns its place for the same reason as the rest: a failed fetch leaves `origin/main`
# stale, and the `git merge --ff-only origin/main` after it then prints the very string this
# guard exists to distrust. `pull` and `add` are deliberately NOT here - both usually make the
# next step fail loudly too, so the premise (loud at step one, invisible after) does not hold,
# and both are common enough that the false-positive volume would swamp the signal.
STATE_CHANGING = frozenset(
    {
        "commit",
        "merge",
        "push",
        "tag",
        "reset",
        "rebase",
        "revert",
        "cherry-pick",
        "checkout",
        "switch",
        "fetch",
        "apply",
        "am",
        "restore",
        "update-index",
        "update-ref",
    }
)

# A verb in the set above is still read-only in these forms, and blocking them is a pure false
# positive: `git checkout -- Makefile` restores a path and moves no branch, `git merge --abort`
# is the cleanup you run precisely when the merge failed, and `git tag -l` only lists.
PATH_SCOPED = frozenset({"checkout", "switch"})           # a `--` makes it a path restore
ABORTABLE = frozenset({"merge", "rebase", "cherry-pick", "revert", "am"})
TAG_READ_ONLY_FLAGS = ("-l", "--list", "-n", "-v", "--verify", "--contains", "--points-at",
                       "--sort", "--merged", "--no-merged", "--format")

# git global options that consume a SEPARATE following token, so the subcommand search does not
# mistake their value for the subcommand (`git -C /repo commit` must read as `commit`).
GIT_VALUE_OPTS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)

# Transparent command prefixes: they exec or fork the real program, so `sudo git push` IS a push.
WRAPPERS = frozenset(
    {"sudo", "env", "command", "time", "nice", "ionice", "nohup", "stdbuf", "timeout", "doas"}
)
# Of those, the ones that take a positional value before the wrapped command.
WRAPPER_VALUE_OPTS = frozenset({"-u", "-g", "-n", "-o", "-i", "--user", "--group"})

# Block structure this guard will not judge. Keywords are matched as whole TOKENS; the brace and
# paren characters are matched anywhere, because after masking none can survive as data.
BLOCK_KEYWORDS = frozenset(
    {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done",
     "case", "esac", "select", "function"}
)
BLOCK_CHARS = "(){}`"

# Split while KEEPING the separators, because which one joined two statements is the entire
# question. `&&` and `||` must be tried before the single `|`. A bare `&` backgrounds, which is
# the strongest continue-regardless there is, but the lookarounds keep `2>&1` and `&>log` out.
SEP_SPLIT = re.compile(r"(&&|\|\||[;\n|]|(?<![>&])&(?![>&]))")

# Only these continue past a failure. `&&` stops, `||` runs only ON failure, `|` is a pipeline.
CONTINUES_AFTER_FAILURE = frozenset({";", "\n", "&"})
JOINS_ON_SUCCESS = frozenset({"&&", "||", "|"})


def _skip_wrappers(tokens: list[str], index: int) -> int:
    """Advance past leading `VAR=value` assignments and transparent wrapper commands."""
    while index < len(tokens):
        token = tokens[index]
        if "=" in token and not token.startswith("-"):
            index += 1
            continue
        if token.rsplit("/", 1)[-1] in WRAPPERS:
            index += 1
            # A wrapper's own options, and the value of the ones that take one.
            while index < len(tokens) and tokens[index].startswith("-"):
                if tokens[index] in WRAPPER_VALUE_OPTS:
                    index += 1
                index += 1
            # `timeout 60 git push` - a bare duration before the wrapped command.
            if index < len(tokens) and re.fullmatch(r"[0-9]+[smhd]?", tokens[index]):
                index += 1
            continue
        return index
    return index


def _is_read_only_form(verb: str, args: list[str]) -> bool:
    """True when this verb, with THESE arguments, changes nothing."""
    if verb in PATH_SCOPED:
        return "--" in args
    if verb in ABORTABLE and ("--abort" in args or "--quit" in args):
        return True
    if verb == "tag":
        if not args:
            return True                                    # bare `git tag` lists tags
        return any(a.startswith(TAG_READ_ONLY_FLAGS) for a in args)
    return False


def _git_verb(segment: str) -> str | None:
    """The state-changing git subcommand this statement runs, or None.

    None covers everything that is not one: another program, a read-only git verb, a
    read-only FORM of a state-changing verb, and a `git` appearing only inside data (masking
    has already removed those regions, so what reaches here is a real statement).
    """
    tokens = segment.split()
    index = _skip_wrappers(tokens, 0)
    if index >= len(tokens) or tokens[index].rsplit("/", 1)[-1] != "git":
        return None
    index += 1
    while index < len(tokens) and tokens[index].startswith("-"):
        if tokens[index] in GIT_VALUE_OPTS:
            index += 1
        index += 1
    if index >= len(tokens):
        return None
    verb = tokens[index]
    if verb not in STATE_CHANGING or _is_read_only_form(verb, tokens[index + 1 :]):
        return None
    return verb


def _errexit_delta(segment: str) -> int:
    """+1 when this statement enables errexit, -1 when it disables it, 0 when it is not a `set`.

    Positional and revocable on purpose: errexit is shell STATE, not a property of the string, so
    a `set -e` after the chain protects nothing and a later `set +e` takes it away again.
    """
    tokens = segment.split()
    if not tokens or tokens[0] != "set":
        return 0
    delta, index = 0, 1
    while index < len(tokens):
        token = tokens[index]
        if token in ("-o", "+o") and index + 1 < len(tokens):
            if tokens[index + 1] == "errexit":
                delta = 1 if token == "-o" else -1
            index += 2
            continue
        if token.startswith("-") and not token.startswith("--") and "e" in token[1:]:
            delta = 1
        elif token.startswith("+") and "e" in token[1:]:
            delta = -1
        index += 1
    return delta


def _unjudgeable(text: str) -> bool:
    """True when the command carries block structure a flat split cannot honestly model."""
    if any(char in text for char in BLOCK_CHARS):
        return True
    return any(token in BLOCK_KEYWORDS for token in text.split())


def _gap_continues_after_failure(parts: list[str], start: int, stop: int) -> bool:
    """True when reaching `stop` from `start` crosses a separator that runs regardless.

    A newline directly after `&&`, `||` or `|` is a LINE CONTINUATION, not a separator - the
    author already wrote the correct form and split it over lines. Treating it as `;` blocks a
    correct command with a message telling the author to do what they just did.
    """
    joined_on_success = False
    for index in range(start, stop, 2):
        separator = parts[index]
        preceding = parts[index - 1].strip()
        if separator in JOINS_ON_SUCCESS:
            joined_on_success = True
            continue
        if separator == "\n" and joined_on_success and not preceding:
            continue                                       # continuation line, still guarded
        if separator in CONTINUES_AFTER_FAILURE:
            return True
    return False


def chained_state_changes(command: str) -> list[str] | None:
    """The first pair of state-changing git verbs joined across an unguarded `;`, or None.

    Consecutive pairs are enough to cover every pair: any two state-changing statements are
    separated by at least one adjacent gap, so if every adjacent gap is guarded there is no
    unguarded one between any of them.
    """
    text = mask_data_regions(strip_heredoc_bodies(command or ""))
    if _unjudgeable(text):
        return None

    parts = SEP_SPLIT.split(text)
    statements = list(range(0, len(parts), 2))

    errexit, active_before = 0, {}
    for index in statements:
        active_before[index] = errexit > 0
        errexit += _errexit_delta(parts[index])

    found = [(index, _git_verb(parts[index])) for index in statements]
    found = [(index, verb) for index, verb in found if verb]

    for (index_a, verb_a), (index_b, verb_b) in zip(found, found[1:]):
        if active_before[index_a]:
            continue                                       # the shell aborts on failure anyway
        if parts[index_a + 1] in ("||",):
            continue                                       # the author wrote the failure path
        if verb_a == verb_b:
            continue                                       # parallel work, not a pipeline
        if _gap_continues_after_failure(parts, index_a + 1, index_b):
            return [verb_a, verb_b]
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    verbs = chained_state_changes(command)
    if not verbs:
        return 0
    sys.stderr.write(
        f"`git {verbs[0]}` and `git {verbs[1]}` are joined by `;`, so the second runs even when "
        f"the first FAILED.\n"
        "The steps after it then report their no-op as success - `Already up to date`, "
        "`Everything up-to-date`, exit 0 - and the transcript reads like a completed ship while "
        "nothing landed.\n"
        "Fix: join them with `&&` so the chain stops where it broke. If a step is genuinely "
        "allowed to fail, write its failure path (`|| true`, `|| exit 1`); if the whole command "
        "should abort on any failure, start it with `set -e`.\n"
        "Then confirm the END STATE (`git rev-parse --verify -q origin/master`, "
        "`git show --name-only`), not the messages.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
