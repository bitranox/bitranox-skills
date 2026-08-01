# /// script
# requires-python = ">=3.10"
# ///
"""Find or signal processes safely - the self-match-proof replacement for `pgrep -f` / `pkill -f`.

Why: `pgrep -f X` / `pkill -f X` match against /proc/<pid>/cmdline, and the shell running the very
command holds X in its own cmdline, so it matches (and kills) itself - the classic
pgrep-self-match footgun, where a stray match kills your own shell. This tool
reads /proc directly and ALWAYS excludes its own process and every ancestor (the caller's shell),
so it structurally cannot signal the caller. What it does NOT do is hide the needle: procsig's own
argv carries the match string like any other command, so somebody else's broad cmdline sweep can
still match THIS process. The guarantee is one-directional - procsig will not kill you; it cannot
stop a third party's sweep from killing procsig.

Match by (pick one):
  --exe PATH_OR_BASENAME   the /proc/<pid>/exe target (cannot self-match a command line at all)
  --comm NAME              the process name in /proc/<pid>/comm
  --cmdline SUBSTR         a substring of the command line, excluding any shell's command
                           string (the safe `pgrep -f` replacement)

What `--cmdline` searches, exactly:

  * a process that is not a shell: its WHOLE argv. A non-shell's argv is its identity. The
    only programs stepped over to reach it are these eleven, the whole recognised wrapper set:
    `env`, `setsid`, `timeout`, `nice`, `ionice`, `chrt`, `taskset`, `stdbuf`, `nohup`, `sudo`,
    `doas`. There is no rule beyond that list.
  * a shell running a SCRIPT (`bash deploy.sh`, `bash -x deploy.sh`, `bash -- deploy.sh`): its
    whole argv too. The script path and its arguments are identity, not text.
  * a shell handed a command STRING (`bash -c '<text>'`, `bash -lc`, `fish --command`, and the
    same behind one of the eleven wrappers, e.g. `setsid bash -c`): only the tokens up to and
    including the flag that introduces the string. The string itself, and anything after it, is
    never searched.
  * an argv that might hold a command string but cannot be classified: NOTHING. The process is
    SKIPPED - it can neither match nor be signaled (see below). Three independent signals raise
    that doubt, any one of them enough:
      - the shell is recognised but an option in front of its command string is not modelled
        (`bash --not-modelled -c ...`);
      - ANY token anywhere in the argv reads like a shell or remote-shell name, or names a
        multi-call binary that could run one. That covers a shell reached through a program
        outside the eleven wrappers (`flock ... bash -c`, `xargs bash -c`, `strace -f bash -c`,
        `systemd-run --scope bash -c`, `runuser -u u -- bash -c`), a shell or remote-shell
        client under a name this tool does not model (`rbash`, `ksh93`, `sh.distrib`,
        `bash-static`, `pwsh`, `ssh host '<cmd>'`), and the same behind a FORKING wrapper, which
        keeps its own argv in /proc (`timeout 30 ssh host '<cmd>'`, `sudo ssh host '<cmd>'`,
        `sshpass -f /k ssh host '<cmd>'`);
      - a `-c`/`--command` flag whose VALUE carries whitespace or a shell metacharacter, which
        is the only trace left when the program running the shell names no shell at all
        (`su root -c '<text>'`, `flock /tmp/lock -c 'a && b'`).

What `--cmdline` does NOT cover - stated here so this file never promises more than it delivers:

  * a `-c`/`--command` value that is ONE WORD with no shell metacharacter reads as an ordinary
    option value, so `flock /tmp/lock -c /opt/deploy.sh` and `runuser -u root -c /opt/deploy.sh`
    are SEARCHED IN FULL. Deliberate: refusing every `-c` value would make `gcc -c foo.c`,
    `ip -c addr` and `grep -c pattern file` unmatchable, and a one-word value is the path of the
    very program being hunted, which is real identity rather than quoted text.
  * a launcher that hands its last argument to a shell with NO `-c` flag and no shell named
    anywhere in its argv: `watch -n 5 '<cmd>'`, `tmux new-session -d '<cmd>'`, `entr -s '<cmd>'`,
    `parallel '<cmd>'`. Nothing in those argvs distinguishes the string from an ordinary operand,
    and listing their names would be the same losing game described below. They are SEARCHED IN
    FULL; when a needle could be quoted inside one of them, read the listing before `--kill`.

Why the carve-out: self/ancestor exclusion only protects the caller's own shell chain, not an
unrelated SIBLING shell that happens to quote the needle inside the text it was handed to
interpret. In this harness every tool call runs as `bash -c '<the whole command text>'`, so a
needle merely TYPED is live in some shell's argv.

Why the skipping: knowing where a shell's command string starts means walking its options, and
every shell has its own option table (`bash -O extglob -c ...`, `zsh -o pipefail -c ...`,
`bash --rcfile FILE -c ...`), where an option's VALUE looks exactly like a script path. The same
holds one level up: every launcher that can put a shell further along the argv has its own option
table too. Depending on exhaustive tables is the wrong correctness dependency, so the known sets
here are deliberately small and an argv outside them is skipped rather than assumed harmless -
absence from a list is never evidence that a process is NOT a shell. The bias is one-way on
purpose: a miss costs the user one `kill <pid>`, a false match kills the wrong process. If a
process you expect is missing from the output, match it with `--exe` or `--comm`, or use its PID.
The same bias costs the occasional false skip: a token whose basename merely READS like a shell
name raises doubt even where it is plain data (`rsync -av /data/wash /backup` is skipped, because
the basename `wash` is short and ends in `sh`). A dot-prefixed basename is exempted from this
(`/home/u/.ssh` is never read as a shell name - no shell is ever called `.ssh`), so an ordinary
path operand under a dotdir does not poison the whole argv.

Default action lists matches; `--kill` (with `--signal`, default TERM) signals them. Excluded
matches (self/ancestors, or an unreadable proc) are shown but never signaled.

Run: `uv run scripts/procsig.py --exe myserver`
     `uv run scripts/procsig.py --kill --signal TERM --cmdline job-1234`
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import sys
from pathlib import Path
from typing import NamedTuple

PROC = Path("/proc")                                          # overridden in tests with a fake tree


def _read_exe(pdir: Path) -> str:
    """Resolved target of /proc/<pid>/exe, or '' if unreadable (kernel thread, permission)."""
    try:
        return os.readlink(pdir / "exe")
    except OSError:
        return ""


def _read_comm(pdir: Path) -> str:
    try:
        return (pdir / "comm").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


class _ShellOptions(NamedTuple):
    """One shell family's invocation options, split by what each does to the argv walk.

    Only what is needed to find where a command STRING starts is modelled: whether a flag is
    followed by its own value, and whether it introduces the command string. These sets are
    deliberately NOT exhaustive - an option outside them makes the argv unclassifiable and the
    process is skipped, which is the safe direction (see the module docstring).
    """
    short_command: frozenset            # single letters that introduce the command string
    short_valueless: frozenset          # single letters that stand alone
    short_value: frozenset              # single letters whose value is the NEXT token
    long_command: frozenset
    long_valueless: frozenset
    long_value: frozenset


# The Bourne family (sh/bash/dash/ash/ksh/mksh/zsh). `-o` takes a set-option name and bash's `-O`
# takes a shopt name, so both consume the token after them - that token is an option VALUE, and
# mistaking it for a script path is exactly how the previous attempt leaked `bash -O extglob -c`.
_BOURNE = _ShellOptions(
    short_command=frozenset("c"),
    short_valueless=frozenset("abDefhiklmnprstuvxBCEHPT"),
    short_value=frozenset("oO"),
    long_command=frozenset(),
    long_valueless=frozenset({
        "login", "noprofile", "norc", "posix", "restricted", "verbose", "debugger",
        "dump-strings", "dump-po-strings", "help", "version", "noediting", "protected",
        "pretty-print",
    }),
    long_value=frozenset({"rcfile", "init-file", "wordexp"}),
)

# csh/tcsh have no long options at all and no value-taking invocation options.
_CSH = _ShellOptions(
    short_command=frozenset("c"),
    short_valueless=frozenset("bdefilmnqstvxVX"),
    short_value=frozenset(),
    long_command=frozenset(),
    long_valueless=frozenset(),
    long_value=frozenset(),
)

# fish spells the command string `-c`/`--command`, and `-C`/`--init-command` is a second command
# string (run before the main one), so both are treated as introducing one.
_FISH = _ShellOptions(
    short_command=frozenset("cC"),
    short_valueless=frozenset("ilNnPv"),
    short_value=frozenset("dp"),
    long_command=frozenset({"command", "init-command"}),
    long_valueless=frozenset({
        "interactive", "login", "no-execute", "no-config", "private", "version", "help",
    }),
    long_value=frozenset({"debug", "debug-output", "debug-stack-frames", "features",
                          "profile", "profile-startup"}),
)

_SHELL_OPTIONS = {
    **{name: _BOURNE for name in ("sh", "bash", "zsh", "dash", "ash", "ksh", "mksh")},
    **{name: _CSH for name in ("csh", "tcsh")},
    "fish": _FISH,
}
_SHELL_BASENAMES = frozenset(_SHELL_OPTIONS)
_MULTICALL_BASENAMES = frozenset({"busybox", "toybox"})         # argv[1] names the real applet

# Programs that run ANOTHER program: the real command (possibly a shell) is further along the
# argv, so a shell hiding behind one of these must not slip past the carve-out. `setsid <shell>
# -c ...` is this workspace's standard detach form.
_WRAPPER_BASENAMES = frozenset({
    "env", "setsid", "timeout", "nice", "ionice", "chrt", "taskset", "stdbuf", "nohup",
    "sudo", "doas",
})
_MAX_WRAPPER_HOPS = 8                                          # bounds the chain walk; nothing real nests deeper

# Signals that an argv nobody could classify may still carry a command string. Kept as small
# tables on purpose: they add DOUBT (which only ever skips a process), never certainty.
_SHELL_NAME_MAX_CORE = 5                        # sh, ash, ksh, zsh, yash, posh, lksh, rbash, pdksh
# What may be cut off a program name before it is tested as a shell name: a packaging VARIANT
# suffix (`bash-static`, `sh.distrib`) or a VERSION (`ksh93`, `bash-5.2`, `wish8.6`) - and
# nothing else. Cutting an arbitrary trailing word instead reduced `ssh-agent` to `ssh`, which
# made the whole OpenSSH toolchain (`ssh-agent`, `ssh-add`, `ssh-keygen`, `ssh-keyscan`,
# `ssh-copy-id`, `ssh-import-id`, `ssh-argv0`, `ssh-askpass`) unfindable although not one of
# them is a shell or hands anything to one. `-agent` is part of the name, not a variant of ssh.
_NAME_SUFFIX_RE = re.compile(r"(?:[.\-](?:static|distrib|real))?(?:[.\-]?\d+(?:\.\d+)*)?$")
_COMMAND_STRING_FLAGS = frozenset({"-c", "--command"})
_COMMAND_STRING_MARKS = ";|&$<>()`"                            # shell metacharacters

_UNCERTAIN = "uncertain"                                       # sentinel: cannot classify -> never match
_NO_SHELL = "no-shell"                                         # sentinel: plain argv -> search all of it


def _read_cmdline_parts(pdir: Path) -> list[str]:
    """/proc/<pid>/cmdline split on its NUL separators (the real argv), or [] if unreadable."""
    try:
        raw = (pdir / "cmdline").read_bytes()
    except OSError:
        return []
    text = raw.decode("utf-8", errors="replace")
    parts = text.split("\0")
    if parts and parts[-1] == "":                              # trailing NUL leaves an empty tail
        parts.pop()
    return parts


def _program_name(token: str) -> str:
    """The basename of an argv token, with any leading '-' stripped.

    sshd (and every other login invocation) sets argv[0] to `-bash`/`-sh` by convention to mark
    a login shell; that leading '-' is the convention, not an option, and the program is still
    bash."""
    return os.path.basename(token).lstrip("-")


def _mentions_a_shell(tokens: list[str]) -> bool:
    """True if any token could name a shell. Used only to decide whether an argv we already
    cannot parse is DANGEROUS (a command string may be in there) or merely unfamiliar.

    Recognition is `_looks_like_a_shell_name`, the SAME test applied to the process's own names,
    and deliberately NOT the closed `_SHELL_BASENAMES` table. Testing tokens against that table
    while testing names against the name rule made one wrapper token reopen the whole hole: a
    shell-ish program the name rule catches as argv[0] (`ssh`, `ksh93`, `rbash`, `pwsh`) went
    unseen here the moment a forking wrapper put it one token further along, so `ssh host
    '<cmd>'` was skipped while `timeout 30 ssh host '<cmd>'` - the standard fleet-probe form -
    was searched in full and `--kill` signaled it. One shared test closes that; growing the
    table never could, because the next unlisted name reopens it.
    """
    names = [_program_name(t) for t in tokens]
    return any(_looks_like_a_shell_name(n) or n in _MULTICALL_BASENAMES for n in names)


def _looks_like_a_shell_name(name: str) -> bool:
    """True if `name` plausibly names a shell (or a remote shell client) this tool does not model.

    Distributions ship shells under variant and versioned names - `rbash`, `bash-static`,
    `sh.distrib`, `ksh93`, `yash`, `posh`, `lksh` - and none of them is in `_SHELL_BASENAMES`,
    yet every one takes `-c '<command string>'`. Listing them is the losing game this module
    refuses to play, so the NAME is tested instead: cut a variant or version suffix, then ask
    whether what is left is a modelled shell name or a short word in the sh family. The length
    bound keeps longer words that merely end in the same two letters out (`publish`, `refresh`),
    and hyphenated program names stay matchable because nothing is cut from them at all
    (`containerd-shim`, `docker-proxy`).

    `ssh` (and `rsh`) match, which is correct rather than incidental: a remote shell client hands
    its last argument to a shell on the far side, and `ssh host '<cmd>'` killing the caller's own
    SSH shell is one of the incidents in the module docstring.

    A dot-prefixed basename is excluded before anything else: no shell is ever called `.ssh`,
    `.sh`, or the like, so a token that is really a PATH OPERAND (`/home/u/.ssh`, a dotfile or
    dotdir) must never be read as a shell name just because its basename ends in the same two
    letters. Without this, `rsync -av /home/u/.ssh /backup`, `tar czf /b/bk.tgz /home/u/.ssh`
    and `find /home/u/.ssh -name id_*` were all skipped - unfindable by `--cmdline` - because the
    `.ssh` operand alone poisoned the whole argv, and fleet commands routinely carry such paths.
    """
    if name.startswith("."):
        return False
    core = _NAME_SUFFIX_RE.sub("", name, count=1)
    return core in _SHELL_BASENAMES or (len(core) <= _SHELL_NAME_MAX_CORE and core.endswith("sh"))


def _is_command_string(value: str) -> bool:
    """True if `value` reads like a whole command rather than an ordinary option value.

    A command string is a command with its arguments or operators, so it carries whitespace or a
    shell metacharacter. An option value does not, and the difference is what keeps `gcc -c
    foo.c`, `ip -c addr` and `grep -c pattern file` matchable while `su root -c '<text>'` is not.
    """
    return any(ch.isspace() or ch in _COMMAND_STRING_MARKS for ch in value)


def _carries_a_command_string(tokens: list[str]) -> bool:
    """True if some token hands a command STRING to a program whose options are not modelled.

    `su`, `runuser`, and every unmodelled shell spell it `-c`/`--command`, so the flag followed
    by a command-shaped value is the only signal available once the program itself is unknown.
    """
    for i, tok in enumerate(tokens):
        if tok in _COMMAND_STRING_FLAGS:
            if i + 1 < len(tokens) and _is_command_string(tokens[i + 1]):
                return True
        elif tok.startswith("--command=") and _is_command_string(tok.partition("=")[2]):
            return True
    return False


def _may_hide_a_command_string(rest: list[str], names: tuple[str, ...]) -> bool:
    """True when an argv this tool could not classify might still hand a shell a command string.

    Any ONE of three independent signals is enough, because the cost of the two outcomes is not
    symmetric (see the module docstring). The first two apply the SAME name test, one to the
    argv and one to the kernel's names, so neither position is blind to what the other catches:
      * a token names a shell or a multi-call binary, so a shell invocation sits further along
        the argv behind a launcher that is not one of the recognised wrappers (`flock ... bash
        -c`, `xargs bash -c`, `strace -f bash -c`, `busybox setsid sh -c`, `timeout 30 ssh host
        '<cmd>'`);
      * one of the process's own names looks like an unmodelled shell or remote shell client
        (`rbash`, `ksh93`, `sh.distrib`, `bash-static`, `pwsh`, `ssh`);
      * a `-c`/`--command` flag is followed by a whole command (`su root -c '<text>'`), which is
        the only trace left when the program running the shell names no shell at all. A ONE-WORD
        value is not one (see `_is_command_string`), so `flock /tmp/lock -c /opt/deploy.sh` does
        NOT raise doubt - the documented residual in the module docstring.
    """
    return (_mentions_a_shell(rest)
            or any(_looks_like_a_shell_name(n) for n in names if n)
            or _carries_a_command_string(rest))


def _classify_unmodelled(rest: list[str], names: tuple[str, ...]) -> str:
    """`_NO_SHELL` (search the whole argv) only when nothing suggests a command string.

    Absence from the name tables is NOT evidence of 'definitely not a shell': returning
    `_NO_SHELL` on that alone made `flock`/`xargs`/`su`/`runuser`/`ssh` argvs searchable in full,
    which is how a caller's own shell gets signaled. Uncertainty must fall to `_UNCERTAIN`.
    """
    return _UNCERTAIN if _may_hide_a_command_string(rest, names) else _NO_SHELL


def _shell_option_region_start(parts: list[str], exe: str = "", comm: str = "") -> int | str:
    """Index in `parts` where a shell's OWN options begin, or `_NO_SHELL` / `_UNCERTAIN`.

    A wrapper chain is walked first (`setsid bash -c ...`, `sudo bash -c ...`): each wrapper
    hands off to the next token, bounded by _MAX_WRAPPER_HOPS. A wrapper's own options and
    values (`timeout 5`, `nice -n 10`, `env VAR=1`) are NOT modelled - their arity is the same
    open-ended table we refuse to depend on for shells.

    Everything the walk does not recognise as a shell goes to `_classify_unmodelled`, which
    searches the whole argv only when no signal suggests a command string is in it: an argv[0]
    outside the tables says nothing on its own. `exe` and `comm` are the kernel's own names for
    the process, and they are the only way to spot a shell invoked under a name the tables do
    not carry (a symlink such as `rbash` or `sh.distrib` resolves to the real shell in `exe`).

    A busybox/toybox multi-call binary names the real applet in the NEXT token
    (`busybox sh -c ...`), so a shell applet's own options start one slot further in.
    """
    names = (_program_name(parts[0]) if parts else "", os.path.basename(exe), comm)
    i = hops = 0
    while i < len(parts):
        name = _program_name(parts[i])
        if name in _SHELL_BASENAMES:
            return i + 1
        if name in _MULTICALL_BASENAMES:
            nxt = i + 1
            if nxt < len(parts) and _program_name(parts[nxt]) in _SHELL_BASENAMES:
                return nxt + 1
            # From the APPLET on: the multi-call token itself always reads as 'a shell is
            # mentioned', which would make every busybox process unmatchable; it is the applet
            # and what follows it that decide (`busybox httpd -f` is a plain command,
            # `busybox setsid sh -c ...` hides a shell one token further along).
            return _classify_unmodelled(parts[nxt:], names)
        if name in _WRAPPER_BASENAMES:
            hops += 1
            if hops > _MAX_WRAPPER_HOPS:
                return _UNCERTAIN                               # absurd nesting: refuse rather than guess
            i += 1
            continue
        return _classify_unmodelled(parts[i:], names)
    return _classify_unmodelled([], names)                      # empty argv, or wrappers all the way down


def _shell_family(parts: list[str], start: int) -> _ShellOptions:
    """Option table for the shell whose options begin at `start` (the token just before it)."""
    return _SHELL_OPTIONS[_program_name(parts[start - 1])]


def _searchable_token_count(parts: list[str], start: int) -> int | str:
    """How many leading tokens of a shell argv are the shell's IDENTITY, or `_UNCERTAIN`.

    Walking from `start` (just after the shell name) until the command string is located:
      * a flag introducing the command string -> the string is the next token, so everything up
        to and including this flag counts, and the string plus its arguments are dropped. A
        short-option CLUSTER counts too: `bash -lc '...'` and `sh -ec '...'` are the standard
        systemd/ssh/wrapper forms, and only looking for a standalone `-c` leaks all of them;
      * `--`, or any token that does not start with '-'/'+' -> options are over and the rest is
        a script path with its arguments, which IS identity: the whole argv counts;
      * a known valueless option -> step over it; a known value-taking option -> step over it
        and its value (that value is not a script path, however much it looks like one);
      * anything else -> _UNCERTAIN, and the caller must not match this process at all.
    """
    opts = _shell_family(parts, start)
    i = start
    while i < len(parts):
        tok = parts[i]
        if tok == "--" or tok[:1] not in ("-", "+"):
            return len(parts)                                   # end of options: script + args are identity
        flag = tok.partition("=")[0]                            # `--rcfile=FILE` carries its value inline
        if tok.startswith("--"):
            name = flag[2:]
            if name in opts.long_command:
                # `--command=<string>` carries the string INSIDE this token, so this token is
                # opaque too and must be dropped along with it.
                return i if flag != tok else i + 1
            if name in opts.long_valueless:
                i += 1
            elif name in opts.long_value:
                i += 1 if flag != tok else 2                    # inline value, or the next token
            else:
                return _UNCERTAIN
            continue
        letters = tok[1:]
        if not letters:
            return _UNCERTAIN                                   # a lone '-' or '+' means different things per shell
        if any(c not in opts.short_command and c not in opts.short_valueless
               and c not in opts.short_value for c in letters):
            return _UNCERTAIN
        takes_value = [c for c in letters if c in opts.short_value]
        if any(c in opts.short_command for c in letters):
            # A cluster carrying BOTH a command flag and a value-taking flag (`-oc`) makes the
            # order of the two following tokens shell-specific: refuse rather than guess wrong.
            return _UNCERTAIN if takes_value else i + 1
        if len(takes_value) > 1:
            return _UNCERTAIN                                   # two values from one cluster: same ambiguity
        i += 2 if takes_value else 1
    return len(parts)                                           # options ran out: no command string here


def _cmdline_search_text(parts: list[str], exe: str = "", comm: str = "") -> str | None:
    """The text `--cmdline` searches, or None when this argv cannot be classified confidently.

    None means the process is skipped entirely - it can neither match nor be signaled. That is
    the deliberate bias: a missed match costs one `kill <pid>`, a wrong match kills the wrong
    process (see the module docstring). `exe`/`comm` are the kernel's names for the process; they
    let a shell running under a name the tables do not carry be recognised as one."""
    start = _shell_option_region_start(parts, exe, comm)
    if start == _UNCERTAIN:
        return None
    if start == _NO_SHELL:
        return " ".join(parts).strip()                          # a plain command: its argv is its identity
    count = _searchable_token_count(parts, int(start))
    if count == _UNCERTAIN:
        return None
    return " ".join(parts[: int(count)]).strip()


def _ppid(pdir: Path) -> int | None:
    """Parent pid from /proc/<pid>/stat. The comm field can hold spaces/parens, so split after the
    LAST ')': fields then are [state, ppid, ...]."""
    try:
        stat = (pdir / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    rparen = stat.rfind(")")
    if rparen == -1:
        return None
    rest = stat[rparen + 1:].split()
    return int(rest[1]) if len(rest) >= 2 and rest[1].lstrip("-").isdigit() else None


def scan(proc_root, *, exe=None, comm=None, cmdline=None) -> list[dict]:
    """Processes under `proc_root` matching the one given filter. PURE over proc_root - unit-testable.

    exe matches the exe path OR its basename; comm matches exactly; cmdline matches as a
    substring of the process's IDENTITY tokens - never of a command string a shell was handed,
    and never at all for a shell argv that cannot be classified (see _cmdline_search_text).
    """
    hits = []
    for pdir in sorted(Path(proc_root).glob("[0-9]*"), key=lambda p: int(p.name)):
        pid = int(pdir.name)
        p_exe, p_comm = _read_exe(pdir), _read_comm(pdir)
        parts = _read_cmdline_parts(pdir)
        p_cmd = " ".join(parts).strip()                         # full cmdline, for display/self-check
        if exe is not None:
            ok = p_exe == exe or os.path.basename(p_exe) == exe
        elif comm is not None:
            ok = p_comm == comm
        else:
            searchable = _cmdline_search_text(parts, p_exe, p_comm)
            ok = bool(cmdline) and searchable is not None and cmdline in searchable
        if ok:
            hits.append({"pid": pid, "exe": p_exe, "comm": p_comm, "cmdline": p_cmd})
    return hits


def ancestors(pid: int, proc_root) -> set[int]:
    """`pid` plus every ancestor pid, walking the ppid chain. Cycle/So-missing-safe. PURE."""
    seen: set[int] = set()
    cur: int | None = pid
    while cur is not None and cur not in seen:
        seen.add(cur)
        cur = _ppid(Path(proc_root) / str(cur))
    return seen


def resolve_targets(procs: list[dict], exclude: set[int]) -> list[int]:
    """PIDs of `procs` that are not in `exclude` (self/ancestors). PURE - the safety gate."""
    return [p["pid"] for p in procs if p["pid"] not in exclude]


def _self_and_ancestors() -> set[int]:
    """This process plus its ancestors (the caller shell chain) - the live exclusion set."""
    return ancestors(os.getpid(), PROC)


def _kill(pid: int, sig: int) -> None:                        # seam: monkeypatched in tests
    os.kill(pid, sig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find or signal processes without self-matching.")
    m = ap.add_mutually_exclusive_group(required=True)
    m.add_argument("--exe", help="match /proc/<pid>/exe path or basename")
    m.add_argument("--comm", help="match the process name (/proc/<pid>/comm) exactly")
    m.add_argument("--cmdline", help="match a substring of the command line (safe pgrep -f). A "
                                     "shell's command string (bash -c '<text>' and every "
                                     "equivalent) is never searched, so text merely quoted "
                                     "inside it cannot match. The recognised wrappers in front "
                                     "of a shell are exactly env, setsid, timeout, nice, ionice, "
                                     "chrt, taskset, stdbuf, nohup, sudo, doas - and nothing "
                                     "else: any other argv that might hold a command string is "
                                     "skipped entirely and never matches. Doubt is raised by a "
                                     "token that reads like a shell or remote-shell name "
                                     "anywhere in the argv (ssh, ksh93, rbash, pwsh, and the "
                                     "same behind a forking wrapper such as timeout/sudo/"
                                     "sshpass), by a multi-call binary, or by a -c/--command "
                                     "value carrying whitespace or a shell metacharacter. NOT "
                                     "covered, so still searched in full: a -c value that is "
                                     "one word (flock /tmp/lock -c /opt/deploy.sh) and a "
                                     "launcher naming no shell and using no -c flag (watch, "
                                     "tmux, entr, parallel). Use --exe, --comm or the PID for a "
                                     "process that was skipped")
    ap.add_argument("--kill", action="store_true", help="signal the matches (default: just list)")
    ap.add_argument("--signal", default="TERM", help="signal name for --kill (default TERM)")
    args = ap.parse_args(argv)

    procs = scan(PROC, exe=args.exe, comm=args.comm, cmdline=args.cmdline)
    excluded = _self_and_ancestors()
    targets = resolve_targets(procs, excluded)

    for p in procs:
        tag = "  [self/ancestor - skipped]" if p["pid"] in excluded else ""
        print(f"{p['pid']:>8}  {p['exe'] or p['comm'] or '?':40.40}  {p['cmdline'][:60]}{tag}")

    if not args.kill:
        return 0 if procs else 1
    try:
        sig = getattr(signal, args.signal if args.signal.startswith("SIG") else "SIG" + args.signal)
    except AttributeError:
        print(f"unknown signal: {args.signal}", file=sys.stderr)
        return 2
    for pid in targets:
        try:
            _kill(pid, int(sig))
            print(f"signaled {pid} with {args.signal}")
        except OSError as exc:
            print(f"failed to signal {pid}: {exc}", file=sys.stderr)
    return 0 if targets else 1


if __name__ == "__main__":
    sys.exit(main())
