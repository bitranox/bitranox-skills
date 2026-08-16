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
available and this reads statement structure with a regex split. That instrument cannot model a
construct whose branches are alternatives or whose separators are required syntax: an `if`/`else`
runs exactly one branch, and a `for ... ; do ... ; done` needs its semicolons. A guess there
blocks correct work, so a command carrying a shell KEYWORD is left alone entirely.

A balanced brace group or subshell is different - it is self-contained, one statement seen from
outside, so it is MASKED rather than bailed on and the statements around it stay judgeable. The
distinction is worth the extra code: an error handler on its own line
(`pytest ... || { tail -10 log; exit 1; }`) was silencing the guard over a plain
`git commit` / `git push` pair further down.

That is still a deliberate accuracy-for-coverage trade. It gives up some real hits, and in
exchange every verdict it does give is one a flat statement list can actually support. The regions
it cannot see at all, and knowingly ignores: anything inside `eval`, `bash -c "..."`,
`ssh host '...'`, or a command substitution - it scans the LOCAL statement structure only.

THE TEST A FINDING HAS TO PASS
------------------------------
Would `&&` be correct advice here? If not, the guard must not fire, because its message says to
use `&&`. That is what rules out a REPEATED verb: `git push origin main ; git push origin topic`,
or a push to each of three repos, is parallel work over independent targets, and `&&` there is
actively wrong - you want the second attempted even when the first fails. A genuine dependency
chain moves through DIFFERENT verbs, which is the shape the incident had.

A repeat separated by a `cd` or a differing `git -C` is the same argument from the other side -
the same operation done in two places. That reading is limited to a REPEAT on purpose: a directory
change is not a repository change (a worktree and its main checkout are one repo), so applying it
to different verbs went silent on `cd ~/wt && git commit -m x ; cd "$MAIN" && git push`, which is
the incident itself.

Two further shapes are exempt because they already say "continue deliberately":

- errexit active at that point in the command (`set -e`, `-euo pipefail`, `-o errexit`), which
  makes the shell itself abort on the first failure. Tracked by POSITION and revocably: a
  `set -e` AFTER the chain protects nothing, and a later `set +e` turns it back off. Position is
  not reachability, and this does not try to be: a `set -e` in a branch that never runs
  (`false && set -e ; ...`) still exempts. Deciding that needs evaluation, not parsing, and the
  safe direction for a BLOCKING guard is to miss rather than to refuse `cd /repo && set -e ; ...`,
  where the command really is protected;
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
# Flags that make ANY verb a no-op, so its failure cannot invalidate a later step.
INERT_FLAGS = frozenset({"--help", "-h", "--dry-run"})
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
# Which of a wrapper's OWN options consume a following value. Keyed per wrapper, because the same
# letter means opposite things: `sudo -u <user>` takes one and `sudo -n` does not, `env -u <name>`
# takes one and `env -i` does not. A single shared set gets one of every pair wrong and then skips
# past the real command.
WRAPPER_VALUE_OPTS = {
    "sudo": frozenset({"-u", "-g", "-U", "-p", "-C", "-h", "-r", "-t", "--user", "--group"}),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}),
    "timeout": frozenset({"-s", "-k", "--signal", "--kill-after"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "-n", "-p", "-P"}),
    "stdbuf": frozenset({"-i", "-o", "-e", "--input", "--output", "--error"}),
    "command": frozenset(),
    "time": frozenset({"-f", "--format", "-o", "--output"}),
    "nohup": frozenset(),
}

# Block structure this guard will not judge, because a flat split cannot model a construct whose
# branches are alternatives or whose separators are required syntax. Keywords are matched as whole
# TOKENS. A balanced brace group or subshell is NOT here - it is self-contained, so `_mask_groups`
# turns it into one opaque token and the statements AROUND it stay judgeable. Only an UNBALANCED
# leftover reaches the bail, which means the command is something this parser does not understand.
BLOCK_KEYWORDS = frozenset(
    {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done",
     "case", "esac", "select", "function"}
)
BLOCK_CHARS = "(){}`"

# Repetition of these verbs is parallel work over independent targets - branches, remotes, repos,
# tags - so `&&` between them is wrong advice. Repetition of any OTHER verb can be a real chain:
# `git checkout master ; git checkout -b feature` branches off the wrong base when the first fails.
PER_TARGET_VERBS = frozenset({"push", "fetch", "tag"})

# A statement that moves the working directory, and the git options that name a tree explicitly.
# The trailing `(?:\s|$)` is what stops `cdrecord` and `cd-hook` reading as a directory change; a
# bare `\b` accepts both. The optional group captures the destination, because PRESENCE of a `cd`
# is not evidence of a MOVE - see `_directory_moves_between`.
CD_COMMAND = re.compile(r"^\s*(?:\w+=\S+\s+)*(?:cd|pushd|popd)(?:\s+(\S+))?(?:\s|$)")
DASHC_TARGET = re.compile(r"\bgit\s+(?:-c\s+\S+\s+)*(?:-C|--git-dir|--work-tree)\s+(\S+)")

# Destinations that do not move anywhere. `cd` with no argument goes HOME, which IS a move, but
# only from somewhere else - and a command that relied on that would not then run git in the repo
# it just left. Treating it as no-op keeps the pair blocked, which is the safe direction.
NON_MOVING_TARGETS = frozenset({None, "", ".", "./", "-", "$PWD", "${PWD}", "$(pwd)", "`pwd`"})

# `fetch` earns its place as the FIRST half of a pair (a failed fetch leaves origin stale and the
# `merge --ff-only` after it prints the very string this guard distrusts). As the SECOND half it is
# almost always post-push verification - `git push ... ; git fetch -q origin ; git rev-parse
# origin/main` - where `&&` is wrong advice and the fetch is the confirmation this guard's own
# message asks for.
NEVER_THE_SECOND_HALF = frozenset({"fetch"})

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
        name = token.rsplit("/", 1)[-1]
        if name in WRAPPERS:
            index += 1
            takes_value = WRAPPER_VALUE_OPTS.get(name, frozenset())
            # A wrapper's own options, and the value of only the ones that take one.
            while index < len(tokens) and tokens[index].startswith("-"):
                if tokens[index] in takes_value:
                    index += 1
                index += 1
            # `timeout 60 git push` - a bare duration before the wrapped command.
            if name == "timeout" and index < len(tokens) and re.fullmatch(r"[0-9.]+[smhd]?", tokens[index]):
                index += 1
            continue
        return index
    return index


def _is_read_only_form(verb: str, args: list[str]) -> bool:
    """True when this verb, with THESE arguments, changes nothing."""
    if INERT_FLAGS.intersection(args):
        return True
    if verb == "push" and "-n" in args:                        # push's short --dry-run
        return True
    if verb in PATH_SCOPED:
        return "--" in args
    if verb in ABORTABLE and ("--abort" in args or "--quit" in args):
        return True
    if verb == "tag":
        if not args:
            return True                                    # bare `git tag` lists tags
        return any(a.startswith(TAG_READ_ONLY_FLAGS) for a in args)
    return False


def _normalise_path(value: str | None) -> str | None:
    """Strip one layer of matching quotes and any trailing slash, so spellings of one path agree.

    `"/repo"`, `/repo` and `/repo/` all name the same directory, and comparing them as raw strings
    calls a repository two repositories. A SUBDIRECTORY (`/repo` vs `/repo/sub`) is deliberately
    left alone: it may be inside the same repo or inside another one, nothing in the text says
    which, and the guard does not block what it cannot determine.
    """
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    if value and len(value) > 1:
        value = value.rstrip("/") or "/"
    return value


def _directory_moves_between(raw: list[str], masked: list[str], start: int, stop: int) -> bool:
    """True when a `cd` strictly between the two statements actually CHANGES directory.

    Presence of a `cd` is not a move. Tracking the destination from the START of the command is
    what separates them: `cd /repo && git commit ; cd /repo && git commit --amend` re-enters the
    same directory, so the second commit amends the first one's repository - and amending a commit
    that never happened rewrites the PREVIOUS commit and exits 0, which is this guard's whole
    subject. A no-op `cd` on each step was overriding two shapes the tests declare must block.

    Structure is read from the MASKED text (a `cd` inside a quoted string is not a command) and the
    destination from the RAW text at the same offset, so `"$MAIN"` compares by name.
    """
    current: str | None = None
    moved = False
    for index in range(0, stop, 2):
        if not CD_COMMAND.match(masked[index]):
            continue
        found = CD_COMMAND.match(raw[index])
        target = _normalise_path(found.group(1)) if found else None
        if target in NON_MOVING_TARGETS or target == current:
            continue
        current = target
        if index > start:
            moved = True
    return moved


def _tree_may_have_changed(raw: list[str], parts: list[str], start: int, stop: int) -> bool:
    """True when the two statements might not be acting on the same repository.

    A `cd` between them, or a differing `git -C <path>`, means the second statement works in
    another directory. Committing to `provmm_planning` and then to `provmm_proxmox` is two pieces
    of work, not a chain, so `&&` is wrong advice: you want the second attempted when the first
    fails.

    ONLY consulted for a REPEATED verb, and that limit is load-bearing. A directory change is not
    a repository change: a worktree and its main checkout are different directories of the SAME
    repo, and nothing in the text distinguishes those two cases. Applied to every pair, this
    exempted the very command the guard was built for - `cd ~/wt && git commit -m x ;
    cd "$MAIN" && git push` went silent, which is the incident in two steps. A repeated verb has
    no such reading: doing the same operation in two places is parallel work either way.

    Measured on real command history: it clears 24 `commit`-then-`commit` blocks across a
    super-repo's separate sub-repos, and leaves every different-verb chain firing.
    """
    # EVEN indices are statements and odd ones are separators, so step from start + 2. Walking the
    # odd indices instead matches nothing at all, and the rule silently does half its job.
    first, second = DASHC_TARGET.search(raw[start]), DASHC_TARGET.search(raw[stop])
    target_a, target_b = _normalise_path(first.group(1) if first else None), _normalise_path(
        second.group(1) if second else None
    )
    # An identical ABSOLUTE `-C` on both is positive proof of one repository, and it outranks any
    # `cd` between them. Relative only resolves against the cwd, so it proves nothing. Reading this
    # AFTER the cd scan let weak evidence beat strong evidence purely by statement order.
    if target_a is not None and target_a == target_b and target_a.startswith(("/", "~")):
        return False
    if target_a != target_b:
        return True
    return _directory_moves_between(raw, parts, start, stop)


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


def _mask_groups(text: str, fill: str = "Q") -> str:
    """Mask balanced `{...}` brace groups and `(...)` subshells, keeping newlines.

    A group is ONE statement from the outside, so its internal `;` says nothing about the
    statements around it - and bailing on the whole command because one exists silences the guard
    where it still had a clear view. Measured: an error handler like
    `pytest ... || {{ tail -10 log; exit 1; }}` on its own line was hiding a plain
    `git commit` / `git push` pair further down.
    """
    out = list(text)
    depth, start = 0, -1
    for position, char in enumerate(text):
        if char in "({":
            if depth == 0:
                start = position
            depth += 1
        elif char in ")}" and depth > 0:
            depth -= 1
            if depth == 0:
                for index in range(start, position + 1):
                    if out[index] != "\n":
                        out[index] = fill
    return "".join(out)


def _unjudgeable(text: str) -> bool:
    """True when the command carries block structure a flat split cannot honestly model."""
    if any(char in text for char in BLOCK_CHARS):
        return True                                    # an UNBALANCED group survived the masking
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

    EVERY pair is examined, not just consecutive ones. Consecutive-only looked equivalent and is
    not: an exemption skips the PAIR, so an exempted middle verb hid the gap behind it.
    `git merge --ff-only origin/main ; git merge topic && git push` reported nothing, because
    (merge, merge) was exempt and (merge, push) is `&&`-joined - while the `;` that lets a failed
    ff-merge run the second merge on a stale base and push it sat right there.
    """
    stripped = strip_heredoc_bodies(command or "")
    text = _mask_groups(mask_data_regions(stripped))
    if _unjudgeable(text):
        return None

    parts = SEP_SPLIT.split(text)
    # Both masking passes preserve LENGTH, so the same offsets index the pre-mask text exactly.
    # The `-C` comparison needs the real path: masked, two different quoted paths of equal length
    # become the same run of filler, so the verdict turned on how many characters a variable name
    # had - `"$PLAN"` vs `"$PROX"` blocked while `"$PLANNING"` vs `"$PROX"` did not.
    raw_parts, offset = [], 0
    for part in parts:
        raw_parts.append(stripped[offset : offset + len(part)])
        offset += len(part)
    statements = list(range(0, len(parts), 2))

    errexit, active_before = 0, {}
    for index in statements:
        active_before[index] = errexit > 0
        errexit += _errexit_delta(parts[index])

    found = [(index, _git_verb(parts[index])) for index in statements]
    found = [(index, verb) for index, verb in found if verb]

    for position, (index_a, verb_a) in enumerate(found):
        if active_before[index_a]:
            continue                                       # the shell aborts on failure anyway
        # The bound matters: iterating EVERY statement (not consecutive pairs) means `index_a` can
        # be the last one, which has no following separator.
        if index_a + 1 < len(parts) and parts[index_a + 1] == "||":
            continue                                       # the author wrote the failure path
        for index_b, verb_b in found[position + 1 :]:
            if verb_b in NEVER_THE_SECOND_HALF:
                continue
            if verb_a == verb_b and (
                verb_a in PER_TARGET_VERBS
                or _tree_may_have_changed(raw_parts, parts, index_a, index_b)
            ):
                continue                                   # parallel work, not a pipeline
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
