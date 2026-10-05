# /// script
# requires-python = ">=3.10"
# ///
"""Run ssh or scp against a host with one option set, one resolved key, and no interactive prompt.

Why: driving a fleet from scripts means retyping `-i <key> -o BatchMode=yes -o ConnectTimeout=N`
on every call, and three traps sit in that one-liner.

1. scp carries the login user INSIDE the path (`root@host:/p`) and has no `--user` flag. A wrapper
   that reads `--user` only to pick the key hands scp a destination naming nobody, so it logs in as
   the LOCAL user while offering the other user's key. On a host that accepts root and refuses the
   local account that is `Permission denied (publickey)` from a command line where the flag looks
   honoured. Here `--user` fills in a remote side that names no user, on either side of the pair,
   so the key and the login are always the same identity.
2. `-i <key>` alone still PROMPTS for a password when the key is rejected, which hangs an
   unattended run instead of failing. `BatchMode=yes` is therefore not optional and is always on.
3. A shared key path can EXIST but be unreadable (root-only on one box, yours on another). Chosen
   by existence, ssh then fails `Permission denied (publickey)` with EMPTY stdout, and the cause
   surfaces far downstream as "the command returned nothing". Keys are picked by READABILITY.

Host-key checking is left at ssh's own strict default. `--trust-changing-host-keys` is for a fleet
you reimage, where a changed key is expected rather than an attack. It sets
StrictHostKeyChecking=accept-new and keeps the fleet's keys in a SEPARATE known-hosts file instead
of polluting your real one. accept-new records a NEW host and REFUSES a changed (or @revoked) key
before anything runs - measured on OpenSSH 10.2: the banner, "Host key verification failed.", exit
255, and the command never ran. So a changed key is healed by dropping the stale entry and
retrying ONCE, and that retry is the command's first and only run. The entry is dropped under the
name ssh says it recorded, which for an ssh_config alias or a non-default port is not the name
typed; a drop that removed nothing is reported and not retried, and neither is a second refusal.

The retry is keyed on ssh's OWN messages, never on what reaches stderr: a remote command that
itself runs ssh or rsync relays its inner ssh's banner, offending entry, removal advice, refusal
and exit 255 through the remote command's stderr, and on a fleet running the same tooling it can
name the same known-hosts path. So in ssh mode `-E <file of ours>` sends ssh's own messages to a
file this tool reads (and then forwards), and the remote command's stderr cannot reach it. scp has
no `-E` and runs no remote command, so there its own stderr is ssh's. A key marked @revoked names
no offending entry, so it is refused and never healed into acceptance.

Pointing a known-hosts file at
/dev/null is refused, because ssh then records every key "permanently" into the bit bucket, making
every connect a first connect - that is the cause of a "Permanently added ..." warning that repeats
forever and lands in the output of any helper that merges stderr into stdout.

Run:
  uv run scripts/fleet_ssh.py HOST uptime                       # ssh, as the current user
  uv run scripts/fleet_ssh.py --user root HOST 'systemctl is-active sshd'
  uv run scripts/fleet_ssh.py --scp --user root ./f HOST:/tmp/f # user is written into the path
  uv run scripts/fleet_ssh.py --scp HOST:/etc/os-release ./f    # remote source works too
  uv run scripts/fleet_ssh.py --dry-run --json HOST uptime      # the argv, without running it

An unstated user is never written into the argv, because `user@host` on a command line OVERRIDES a
`User` directive in ssh_config: filling in the local account by default would silently log a
config-driven `User root` host in as the wrong one. The key is still resolved for the right
identity, by asking ssh itself (`ssh -G <host>`, which reads the config without connecting).

Key resolution: `--key` when given, else the first READABLE of FLEET_SSH_KEY_CANDIDATES
(os.pathsep-separated templates taking {user} and {home}), else none - in which case ssh uses its
own identities.

scp takes exactly one SRC and one DST. More paths are refused rather than guessed at: scp reads the
LAST path as the destination, so silently keeping the first two would turn `f1 f2 host:/dir/` into
a local copy that overwrites f2. A bracketed IPv6 literal (`[fe80::1]:/p`, `root@[::1]:/p`) names
that address, and a Windows drive path (`C:\\dir\\f`, `C:/dir/f`) is local, not a host called C.

Exit status is ssh's or scp's own, so the caller keeps the remote command's exit code; 255 is
ssh itself failing (unreachable, auth, host key). This script's own failures are 2: a usage error,
ssh or scp not installed, a known-hosts directory it cannot create, no local user name to resolve
a key for, or a crash. (A remote command that exits 2 is passed through as 2 as well; the stderr
line `fleet_ssh: ...` is what marks one of ours.) `--json` with `--dry-run` prints the envelope
`{ok, command, data: {argv}, skipped}`, and any exit 2 under `--json` prints one too; a `--json`
written after the host belongs to the remote command, never to this script.
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from _cli_envelope import EXIT_ERROR, emit

# Templates, not paths: {user} matters because a fleet key is usually per-login, and the FIRST
# READABLE one wins (see the module docstring). Override with FLEET_SSH_KEY_CANDIDATES.
DEFAULT_KEY_CANDIDATES = ("{home}/.ssh/{user}@anyhost_nopass.key",)

# Where churny host keys go when --trust-changing-host-keys is on. Deliberately NOT the real
# known_hosts: these are hosts that get cloned, rebuilt and re-IPed, and that churn should not
# pollute the file you rely on for everything else.
DEFAULT_FLEET_KNOWN_HOSTS = "{home}/.ssh/known_hosts_fleet"

# ssh's line naming the stale entry in its changed-key banner: `Offending ED25519 key in
# /home/u/.ssh/known_hosts_fleet:3`. Captured stderr also carries the REMOTE command's stderr, and
# a command that itself runs ssh or rsync relays that inner ssh's banner and its "Host key
# verification failed." with them - phrase, frame and exit 255 alike. Only the FILE tells the two
# apart: ours is the known-hosts file this run handed ssh, the inner one is the peer's.
OFFENDING_KEY = re.compile(r"^Offending \S+ key in (?P<path>.+):\d+\s*$", re.MULTILINE)
# ssh's own removal advice under that banner: `ssh-keygen -f '<file>' -R '<name>'`. The NAME is
# what ssh recorded - `[10.0.0.5]:2222` for an ssh_config alias with a Port, never the alias - so
# it is the one name `ssh-keygen -R` can actually find.
_REMOVE_HINT = re.compile(r"ssh-keygen -f '(?P<path>[^']+)' -R '(?P<name>[^']+)'")
# `user@[v6addr]:path` - the address holds colons, so it cannot be split off at the first one.
_BRACKETED_REMOTE = re.compile(r"^((?:[^@/\[\]:]+@)?\[[^\]/]+\]):")
# `C:\dir` is a Windows drive path on every platform: no remote scp path starts with a backslash.
_DRIVE_BACKSLASH = re.compile(r"^[A-Za-z]:\\")
# `C:/dir` is one ONLY on Windows, where scp itself reads it as local; elsewhere `h:/p` is the
# ordinary spelling of host h, and scp reads it that way too.
_DRIVE_SLASH = re.compile(r"^[A-Za-z]:/")
_ON_WINDOWS = os.name == "nt"
# Pure noise once the key is on file, and the line that leaks into merged-output parses.
_ADDED_NOISE = re.compile(r"^Warning: Permanently added .*to the list of known hosts\.?\s*$")
# ssh's own words for a changed key it refused. All three must be in ITS OWN messages (the -E log),
# with exit 255: the banner, the refusal, and an offending entry in our known-hosts file.
_CHANGED_BANNER = "REMOTE HOST IDENTIFICATION HAS CHANGED"
_REFUSED = "Host key verification failed."
_SSH_FAILED = 255


class UsageError(Exception):
    """A caller mistake that must not be turned into an ssh attempt."""


def key_candidates() -> tuple[str, ...]:
    """The key templates to try, from the environment or the built-in default."""
    raw = os.environ.get("FLEET_SSH_KEY_CANDIDATES")
    if not raw:
        return DEFAULT_KEY_CANDIDATES
    return tuple(part for part in raw.split(os.pathsep) if part)


def resolve_key(user: str, candidates=None, home: str | None = None) -> str | None:
    """First READABLE candidate, not merely the first that exists.

    A shared key directory can be mounted on several boxes and be root-only on some of them, so an
    existence test picks a key this process cannot load; see trap 3 in the module docstring.
    """
    home = home if home is not None else os.path.expanduser("~")
    for template in (candidates if candidates is not None else key_candidates()):
        # normpath because the templates spell their separator "/" so one string works
        # everywhere; without it a Windows home yields "C:\Users\me/.ssh/key" - functional,
        # since both ssh and Path accept it, but it is what the tool then PRINTS and returns,
        # so every caller comparing it against a native path sees two different strings.
        path = os.path.normpath(template.format(user=user, home=home))
        # os.path.isfile, not Path.is_file: before Python 3.14 the latter RAISES PermissionError
        # for a candidate inside a root-only directory - the very case this function skips.
        if os.path.isfile(path) and _can_open(path):
            return path
    return None


def _can_open(path: str) -> bool:
    """Readable means it OPENS. os.access(R_OK) on Windows checks only the read-only attribute and
    answers True for a file whose ACL refuses this user, so it cannot make the selection there."""
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


def build_options(*, key: str | None, timeout: int, trust_changing_host_keys: bool,
                  known_hosts: str | None) -> list[str]:
    """The shared option block for both ssh and scp. Pure, so the policy is testable."""
    if known_hosts == "/dev/null":
        raise UsageError("known-hosts /dev/null makes every connect a first connect; use a file")
    opts: list[str] = ["-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout}"]
    if key:
        # Without this the agent's keys are offered first and the one just resolved may never be
        # tried, which reads as a key that "does not work".
        opts += ["-o", "IdentitiesOnly=yes"]
    if trust_changing_host_keys:
        # accept-new, never `no`: under `no` a changed key is only a warning and ssh RUNS the
        # command, so no retry is ever safe; accept-new refuses first, so one retry is.
        opts += ["-o", "StrictHostKeyChecking=accept-new"]
    if known_hosts:
        opts += ["-o", f"UserKnownHostsFile={known_hosts}"]
    return opts


def build_ssh_argv(host: str, cmd: str | None = None, *, user: str | None = None,
                   key: str | None = None, options=()) -> list[str]:
    """`ssh -i KEY <opts> [user@]host [cmd]`."""
    argv = ["ssh"]
    if key:
        argv += ["-i", key]
    argv += list(options)
    argv.append(f"{user}@{host}" if user else host)
    if cmd:
        argv.append(cmd)
    return argv


def build_scp_argv(src: str, dst: str, *, key: str | None = None, options=()) -> list[str]:
    """`scp -i KEY <opts> src dst`."""
    argv = ["scp"]
    if key:
        argv += ["-i", key]
    argv += list(options)
    argv += [src, dst]
    return argv


def remote_prefix(side: str, *, windows: bool = _ON_WINDOWS) -> str | None:
    """The `[user@]host` text before the path colon of an scp side, or None for a local path.

    A bare local path has no colon before any slash, a path whose colon comes AFTER a slash
    (`/mnt/c:/weird`) is local too, and so is a Windows drive path: `C:\\dir` everywhere, `C:/dir`
    on Windows (`windows` is a parameter so both platforms' reading is testable on either). A
    bracketed IPv6 literal keeps its brackets here; scp_host strips them.
    """
    bracketed = _BRACKETED_REMOTE.match(side)
    if bracketed:
        return bracketed.group(1)
    if _DRIVE_BACKSLASH.match(side) or (windows and _DRIVE_SLASH.match(side)):
        return None
    head = side.split(":", 1)[0]
    return head if ":" in side and "/" not in head and head else None


def is_remote_side(side: str) -> bool:
    """Does this half of an scp pair name a host?"""
    return remote_prefix(side) is not None


def scp_remote(src: str, dst: str) -> str | None:
    """The `[user@]host` part of whichever side is remote, or None for a local-to-local copy."""
    for side in (dst, src):
        prefix = remote_prefix(side)
        if prefix is not None:
            return prefix
    return None


def scp_host(src: str, dst: str) -> str | None:
    """Just the host, so a changed host key can be healed in scp mode too.

    An IPv6 literal comes back without its brackets, the spelling `ssh-keygen -R` and `ssh -G`
    take for port 22.
    """
    remote = scp_remote(src, dst)
    if not remote:
        return None
    host = remote.split("@", 1)[-1]
    return host[1:-1] if host.startswith("[") and host.endswith("]") else host


def scp_user(src: str, dst: str) -> str | None:
    """The user named inside the scp path, if it names one."""
    remote = scp_remote(src, dst)
    return remote.split("@", 1)[0] if remote and "@" in remote else None


def with_scp_user(side: str, user: str) -> str:
    """Name the login user on a remote scp path that does not already carry one (trap 1)."""
    prefix = remote_prefix(side)
    if prefix is None or "@" in prefix:
        return side
    return f"{user}@{side}"


def forward_stderr(text: str, stream=None) -> None:
    """Pass ssh's stderr through, minus the once-per-host known-hosts noise.

    The default stream is looked up per call, not bound at import, so a replaced sys.stderr (a
    test's capture, a caller's redirect) receives it."""
    kept = [ln for ln in text.splitlines(True) if not _ADDED_NOISE.match(ln.strip("\n"))]
    if kept:
        (stream if stream is not None else sys.stderr).write("".join(kept))


def run_with_host_key_healing(argv: list[str], *, host: str | None, known_hosts: str | None,
                              heal: bool, run=subprocess.run) -> int:
    """Run `argv`; when ssh REFUSED a changed host key, drop the stale entry and retry ONCE.

    stdout is inherited so large command output still streams; only stderr is captured, so the
    noise line can be filtered. It is decoded as UTF-8 with replacement, because what arrives
    there is partly the REMOTE command's stderr, in whatever encoding the remote wrote, and a
    strict locale decode would crash after the command ran.

    Healing runs under StrictHostKeyChecking=accept-new (see build_options), which refuses a
    changed key BEFORE running anything: exit 255, "Host key verification failed.". The retry is
    therefore the command's first run, never a second one - but only when ssh ITSELF said so. In
    ssh mode its own messages go to a `-E` log of ours, which the remote command's stderr cannot
    reach, so an inner ssh's banner relayed through that stderr is never mistaken for ours; scp
    runs no remote command, so its stderr is its own.

    Retried only when the status is 255 and ssh's own messages hold the banner, the refusal and
    an offending entry in `known_hosts`, and only when the drop actually changed the file - a drop
    that removed nothing would just be refused again. At most once. A key marked @revoked names no
    offending entry, so it is never dropped. `run` is injected so this is testable without a live
    host and a real changed key.

    Returns ssh's (or the retry's) status, or 2 when ssh/scp could not be started at all.
    """
    healing = bool(heal and host and known_hosts)
    first = _run_once(argv, run, own_log=healing and argv[:1] == ["ssh"])
    if first is None:
        return EXIT_ERROR
    status, own = first
    if not (healing and _refused_changed_key(status, own, known_hosts)):
        return status
    if not _drop_stale_entry(recorded_name(own, known_hosts) or host, known_hosts, run):
        return status
    print("fleet_ssh: retrying once - ssh refused the changed key, so the command has not run yet",
          file=sys.stderr)
    second = _run_once(argv, run, own_log=argv[:1] == ["ssh"])
    return EXIT_ERROR if second is None else second[0]


def _refused_changed_key(status: int, own: str, known_hosts: str) -> bool:
    return (status == _SSH_FAILED and _CHANGED_BANNER in own and _REFUSED in own
            and offends_known_hosts(own, known_hosts))


def _run_once(argv: list[str], run, *, own_log: bool) -> tuple[int, str] | None:
    """(status, ssh's own messages) for one run, both streams forwarded; None if it cannot start.

    With `own_log`, ssh writes its own messages to a temp file through `-E` and the captured
    stderr is the REMOTE command's alone; without it, the captured stderr is all there is.
    """
    log_fd, log_path = tempfile.mkstemp(prefix="fleet_ssh-", suffix=".log") if own_log else (None, "")
    if log_fd is not None:
        os.close(log_fd)
    try:
        full = [argv[0], "-E", log_path, *argv[1:]] if own_log else list(argv)
        try:
            proc = _run_capturing_stderr(full, run)
        except OSError as exc:
            print(f"fleet_ssh: cannot run {argv[0]}: {exc}", file=sys.stderr)
            return None
        err = proc.stderr or ""
        own = (_read_or_none(log_path) or b"").decode("utf-8", "replace") if own_log else err
        if own_log:
            forward_stderr(own)
        forward_stderr(err)
        return proc.returncode, own
    finally:
        if own_log:
            try:
                os.unlink(log_path)
            except OSError:
                pass


def recorded_name(err: str, known_hosts: str) -> str | None:
    """The name ssh recorded the host under in THIS known-hosts file, from its removal advice.

    An ssh_config alias or a non-default port is stored under the resolved name, so dropping the
    name the caller typed removes nothing and the banner repeats on every later call. Advice about
    another file is an inner ssh's, relayed through the remote command's stderr, and is skipped.
    """
    ours = _comparable_path(known_hosts)
    for m in _REMOVE_HINT.finditer(err):
        if _comparable_path(m.group("path")) == ours:
            return m.group("name")
    return None


def _drop_stale_entry(name: str, known_hosts: str, run) -> bool:
    """`ssh-keygen -R`, then say what happened to the FILE - a claim checked, not assumed.

    Returns whether the file changed: only then can a retry find anything different. ssh-keygen
    missing is reported and counts as no change, keeping ssh's own 255 for the caller.
    """
    before = _read_or_none(known_hosts)
    try:
        run(["ssh-keygen", "-R", name, "-f", known_hosts],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError as exc:
        print(f"fleet_ssh: host key for {name} changed, but ssh-keygen could not run ({exc}); "
              f"remove the entry by hand: ssh-keygen -R {name} -f {known_hosts}", file=sys.stderr)
        return False
    if before is not None and _read_or_none(known_hosts) != before:
        print(f"fleet_ssh: host key for {name} changed; dropped the stale entry", file=sys.stderr)
        return True
    print(f"fleet_ssh: host key for {name} changed, but `ssh-keygen -R {name} -f {known_hosts}` "
          f"removed nothing, so ssh will refuse it again - remove the entry ssh names above by "
          f"hand (the command did not run)", file=sys.stderr)
    return False


def _read_or_none(path: str) -> bytes | None:
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def offends_known_hosts(err: str, known_hosts: str) -> bool:
    """Does ssh's stderr name an offending entry in THIS known-hosts file?

    Compared as paths, since ssh prints the file after expanding it and the caller may have
    spelled it with `~` or a `./`."""
    ours = _comparable_path(known_hosts)
    return any(_comparable_path(m.group("path")) == ours for m in OFFENDING_KEY.finditer(err))


def _comparable_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.expanduser(path.strip())))


def _run_capturing_stderr(argv: list[str], run):
    return run(argv, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")


class _Parser(argparse.ArgumentParser):
    """A usage error becomes a UsageError, so main can print the --json envelope for it."""

    def error(self, message):
        raise UsageError(message)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = _Parser(
        description="Run ssh/scp with one option set, one resolved key, and no interactive prompt.")
    ap.add_argument("--scp", action="store_true", help="scp mode: the positionals are <src> <dst>")
    ap.add_argument("--user", help="login user; unset leaves the host bare so ssh_config decides")
    ap.add_argument("--key", help="use this key instead of resolving one")
    ap.add_argument("--timeout", type=int, default=10, help="ConnectTimeout seconds")
    ap.add_argument("--trust-changing-host-keys", action="store_true",
                    help="for a fleet you reimage: keep host keys in a separate known-hosts "
                         "file (accept-new), and on a CHANGED key that ssh refused, drop the "
                         "stale entry and retry once")
    ap.add_argument("--known-hosts", help="known-hosts file (default with --trust-changing-host-"
                                          "keys: ~/.ssh/known_hosts_fleet)")
    ap.add_argument("--dry-run", action="store_true", help="print the argv instead of running it")
    ap.add_argument("--json", action="store_true", help="with --dry-run: print the argv as JSON")
    ap.add_argument("rest", nargs=argparse.REMAINDER,
                    help="HOST [command...] or, with --scp, SRC DST")
    return ap.parse_args(argv)


def ssh_config_user(host: str, run=subprocess.run) -> str | None:
    """Whom ssh WOULD log in as for this host, per ssh_config. None if it cannot be asked.

    `ssh -G` resolves the config without connecting, so this is a local question with a local
    answer. It exists so a key can be resolved for the right identity WITHOUT writing that identity
    into the argv, which is the part that would override the config.
    """
    try:
        done = run(["ssh", "-G", host], capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    for line in (done.stdout or "").splitlines():
        if line.startswith("user "):
            return line.split(" ", 1)[1].strip() or None
    return None


def plan(args: argparse.Namespace, *, home: str | None = None, default_user: str | None = None,
         config_user=ssh_config_user) -> tuple[list[str], str | None, str | None]:
    """Work out (argv, host, known_hosts) without running anything. Raises UsageError.

    Split from main() because this is where the wiring lives, and the scp-user trap was a wiring
    bug: both halves were right on their own and only their join was wrong.

    Two identities, deliberately not the same one:

    - the LOGIN user is written into the argv only when it was stated (--user, or already inside an
      scp path). An unstated one stays out, because `user@host` on the command line OVERRIDES a
      `User` directive in ssh_config - so filling in the local account by default would silently
      log a config-driven `User root` host in as the wrong account.
    - the KEY user is who ssh will actually be, asked of ssh itself when it was not stated, so the
      key still resolves for the right identity. Guessing the local account here instead would
      offer one user's key while connecting as another, which is the mismatch this jig exists to
      prevent, just moved one step along.
    """
    home = home if home is not None else os.path.expanduser("~")
    known_hosts = args.known_hosts
    if args.trust_changing_host_keys and not known_hosts:
        known_hosts = os.path.normpath(DEFAULT_FLEET_KNOWN_HOSTS.format(home=home))

    def key_for(host: str | None, stated: str | None) -> str | None:
        if args.key:
            return args.key
        user = stated or (config_user(host) if host else None) or default_user
        return resolve_key(user, home=home) if user else None

    if args.scp:
        if len(args.rest) != 2:
            # Never keep the first two of three: scp reads the LAST path as the destination, so
            # `f1 f2 host:/dir/` cut to `f1 f2` is a local copy that overwrites f2.
            raise UsageError(f"--scp needs <src> <dst>: exactly 2 paths, got {len(args.rest)} "
                             "(copy several files with one call each, or a directory with scp -r)")
        src_in, dst_in = args.rest[0], args.rest[1]
        # A user named in the path wins: someone who wrote root@host meant root. --user only fills
        # in a side that names nobody.
        stated = scp_user(src_in, dst_in) or args.user
        key = key_for(scp_host(src_in, dst_in), stated)
        src, dst = ((with_scp_user(side, stated) for side in (src_in, dst_in)) if stated
                    else (src_in, dst_in))
        options = build_options(key=key, timeout=args.timeout,
                                trust_changing_host_keys=args.trust_changing_host_keys,
                                known_hosts=known_hosts)
        return build_scp_argv(src, dst, key=key, options=options), scp_host(src, dst), known_hosts

    if not args.rest:
        raise UsageError("need a <host>")
    host, cmd = args.rest[0], (" ".join(args.rest[1:]) or None)
    key = key_for(host, args.user)
    options = build_options(key=key, timeout=args.timeout,
                            trust_changing_host_keys=args.trust_changing_host_keys,
                            known_hosts=known_hosts)
    return build_ssh_argv(host, cmd, user=args.user, key=key, options=options), host, known_hosts


def tolerate_unencodable_stdout(stream=None) -> None:
    """A Windows pipe is cp1252; a path it cannot encode must print as '?', not crash the run."""
    stream = stream if stream is not None else sys.stdout
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):
        pass


_VALUED = ("--user", "--key", "--timeout", "--known-hosts")


def json_requested(argv: list[str]) -> bool:
    """Whether `--json` is one of THIS script's options: written before the host, never after it.

    Everything from the first positional on is the remote command's (argparse.REMAINDER), so a
    `--json` there is the remote tool's flag, and an envelope from us would corrupt its stdout.
    """
    skip = False
    for token in argv:
        if skip:
            skip = False
            continue
        if token == "--json":
            return True
        if token == "--" or not token.startswith("-"):
            return False
        skip = token in _VALUED
    return False


def _local_user() -> str:
    """The local account name. Raises UsageError: no key can be resolved without one."""
    try:
        return getpass.getuser()
    except (OSError, KeyError) as exc:     # OSError from 3.13, KeyError (pwd lookup) before
        raise UsageError(f"cannot tell the local user name ({exc}); pass --user and --key") from exc


def _fail(message: str, as_json: bool) -> int:
    if as_json:
        emit(EXIT_ERROR, "fleet_ssh", error=message)
    print(f"fleet_ssh: {message}", file=sys.stderr)
    return EXIT_ERROR


def main(argv: list[str] | None = None, *, run=subprocess.run) -> int:
    """The CLI: ssh's or scp's own status, or 2 for this script's own failures (see the module)."""
    tolerate_unencodable_stdout()
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = json_requested(raw)
    try:
        return _main(raw, run, as_json)
    except UsageError as exc:
        return _fail(str(exc), as_json)
    except Exception as exc:  # noqa: BLE001 - a crash must not pass for the remote command's code
        return _fail(f"internal error: {type(exc).__name__}: {exc}", as_json)


def _main(raw: list[str], run, as_json: bool) -> int:
    args = parse_args(raw)
    built, host, known_hosts = plan(args, default_user=_local_user())
    if args.dry_run:
        if as_json:
            return emit(0, "fleet_ssh", {"argv": built})
        print(" ".join(built))
        return 0
    if known_hosts:
        # The directory must exist or ssh cannot create the file and warns on every call.
        try:
            Path(known_hosts).parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise UsageError(f"cannot create the known-hosts directory "
                             f"{Path(known_hosts).parent}: {exc}") from exc
    return run_with_host_key_healing(built, host=host, known_hosts=known_hosts,
                                     heal=args.trust_changing_host_keys, run=run)


if __name__ == "__main__":
    sys.exit(main())
