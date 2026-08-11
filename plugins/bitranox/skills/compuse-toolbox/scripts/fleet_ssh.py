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
you reimage, where a changed key is expected rather than an attack: it turns strict checking off,
keeps that churn in a SEPARATE known-hosts file instead of polluting your real one, and heals a
changed key by dropping the stale entry and retrying exactly once. Pointing a known-hosts file at
/dev/null is refused, because ssh then records every key "permanently" into the bit bucket, making
every connect a first connect - that is the cause of a "Permanently added ..." warning that repeats
forever and lands in the output of any helper that merges stderr into stdout.

Run:
  uv run scripts/fleet_ssh.py HOST uptime                       # ssh, as the current user
  uv run scripts/fleet_ssh.py --user root HOST 'systemctl is-active sshd'
  uv run scripts/fleet_ssh.py --scp --user root ./f HOST:/tmp/f # user is written into the path
  uv run scripts/fleet_ssh.py --scp HOST:/etc/os-release ./f    # remote source works too
  uv run scripts/fleet_ssh.py --dry-run --json HOST uptime      # the argv, without running it

Key resolution: the first READABLE of FLEET_SSH_KEY_CANDIDATES (os.pathsep-separated templates
taking {user} and {home}), else `--key`, else none - in which case ssh uses its own identities.

Exit status is ssh's or scp's own, so the caller keeps the remote command's exit code; 255 is
ssh itself failing (unreachable, auth, host key), and 2 is a usage error from this script.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Templates, not paths: {user} matters because a fleet key is usually per-login, and the FIRST
# READABLE one wins (see the module docstring). Override with FLEET_SSH_KEY_CANDIDATES.
DEFAULT_KEY_CANDIDATES = ("{home}/.ssh/{user}@anyhost_nopass.key",)

# Where churny host keys go when --trust-changing-host-keys is on. Deliberately NOT the real
# known_hosts: these are hosts that get cloned, rebuilt and re-IPed, and that churn should not
# pollute the file you rely on for everything else.
DEFAULT_FLEET_KNOWN_HOSTS = "{home}/.ssh/known_hosts_fleet"

# ssh's two ways of saying "the key on file is not the key I was offered".
HOST_KEY_CHANGED = re.compile(
    r"REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed", re.I
)
# Pure noise once the key is on file, and the line that leaks into merged-output parses.
_ADDED_NOISE = re.compile(r"^Warning: Permanently added .*to the list of known hosts\.?\s*$")


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
        path = template.format(user=user, home=home)
        if os.access(path, os.R_OK) and Path(path).is_file():
            return path
    return None


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
        opts += ["-o", "StrictHostKeyChecking=no"]
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


def is_remote_side(side: str) -> bool:
    """Does this half of an scp pair name a host?

    A bare local path has no colon before any slash, and a path whose colon comes AFTER a slash
    (`/mnt/c:/weird`) is local too.
    """
    head = side.split(":", 1)[0]
    return ":" in side and "/" not in head and bool(head)


def scp_remote(src: str, dst: str) -> str | None:
    """The `[user@]host` part of whichever side is remote, or None for a local-to-local copy."""
    for side in (dst, src):
        if is_remote_side(side):
            return side.split(":", 1)[0]
    return None


def scp_host(src: str, dst: str) -> str | None:
    """Just the host, so a changed host key can be healed in scp mode too."""
    remote = scp_remote(src, dst)
    return remote.split("@", 1)[-1] if remote else None


def scp_user(src: str, dst: str) -> str | None:
    """The user named inside the scp path, if it names one."""
    remote = scp_remote(src, dst)
    return remote.split("@", 1)[0] if remote and "@" in remote else None


def with_scp_user(side: str, user: str) -> str:
    """Name the login user on a remote scp path that does not already carry one (trap 1)."""
    if not is_remote_side(side) or "@" in side.split(":", 1)[0]:
        return side
    return f"{user}@{side}"


def forward_stderr(text: str, stream=sys.stderr) -> None:
    """Pass ssh's stderr through, minus the once-per-host known-hosts noise."""
    kept = [ln for ln in text.splitlines(True) if not _ADDED_NOISE.match(ln.strip("\n"))]
    if kept:
        stream.write("".join(kept))


def run_with_host_key_healing(argv: list[str], *, host: str | None, known_hosts: str | None,
                              heal: bool, run=subprocess.run) -> int:
    """Run `argv`; on a host-key mismatch drop the stale entry and retry EXACTLY once.

    stdout is inherited so large command output still streams; only stderr is captured, and only
    so the mismatch can be detected and the noise line filtered.

    The retry guard is deliberately four-part - healing enabled, a non-zero exit, a known host, and
    stderr that really is a mismatch - because `argv` can be a MUTATING remote command and a
    spurious second run would apply it twice. `run` is injected so that is testable without a live
    host and a real changed key.
    """
    proc = run(argv, stderr=subprocess.PIPE, text=True)
    err = proc.stderr or ""
    if heal and proc.returncode != 0 and host and known_hosts and HOST_KEY_CHANGED.search(err):
        run(["ssh-keygen", "-R", host, "-f", known_hosts],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        print(f"fleet_ssh: host key for {host} changed; dropped the stale entry and retried",
              file=sys.stderr)
        proc = run(argv, stderr=subprocess.PIPE, text=True)
        err = proc.stderr or ""
    forward_stderr(err)
    return proc.returncode


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run ssh/scp with one option set, one resolved key, and no interactive prompt.")
    ap.add_argument("--scp", action="store_true", help="scp mode: the positionals are <src> <dst>")
    ap.add_argument("--user", help="login user (default: the current local user)")
    ap.add_argument("--key", help="use this key instead of resolving one")
    ap.add_argument("--timeout", type=int, default=10, help="ConnectTimeout seconds")
    ap.add_argument("--trust-changing-host-keys", action="store_true",
                    help="for a fleet you reimage: accept a changed host key, keep it in a "
                         "separate known-hosts file, and heal a mismatch once")
    ap.add_argument("--known-hosts", help="known-hosts file (default with --trust-changing-host-"
                                          "keys: ~/.ssh/known_hosts_fleet)")
    ap.add_argument("--dry-run", action="store_true", help="print the argv instead of running it")
    ap.add_argument("--json", action="store_true", help="with --dry-run: print the argv as JSON")
    ap.add_argument("rest", nargs=argparse.REMAINDER,
                    help="HOST [command...] or, with --scp, SRC DST")
    return ap.parse_args(argv)


def plan(args: argparse.Namespace, *, home: str | None = None,
         default_user: str | None = None) -> tuple[list[str], str | None, str | None]:
    """Work out (argv, host, known_hosts) without running anything. Raises UsageError.

    Split from main() because this is where the wiring lives, and the scp-user trap was a wiring
    bug: both halves were right on their own and only their join was wrong.
    """
    home = home if home is not None else os.path.expanduser("~")
    known_hosts = args.known_hosts
    if args.trust_changing_host_keys and not known_hosts:
        known_hosts = DEFAULT_FLEET_KNOWN_HOSTS.format(home=home)

    if args.scp:
        if len(args.rest) < 2:
            raise UsageError("--scp needs <src> <dst>")
        src_in, dst_in = args.rest[0], args.rest[1]
        # A user named in the path wins: someone who wrote root@host meant root. --user only fills
        # in a side that names nobody, and it fills in the same identity the key is resolved for.
        user = scp_user(src_in, dst_in) or args.user or default_user or ""
        key = args.key or (resolve_key(user, home=home) if user else None)
        src, dst = (with_scp_user(side, user) for side in (src_in, dst_in)) if user else (src_in, dst_in)
        options = build_options(key=key, timeout=args.timeout,
                                trust_changing_host_keys=args.trust_changing_host_keys,
                                known_hosts=known_hosts)
        return build_scp_argv(src, dst, key=key, options=options), scp_host(src, dst), known_hosts

    if not args.rest:
        raise UsageError("need a <host>")
    user = args.user or default_user
    key = args.key or (resolve_key(user, home=home) if user else None)
    host, cmd = args.rest[0], (" ".join(args.rest[1:]) or None)
    options = build_options(key=key, timeout=args.timeout,
                            trust_changing_host_keys=args.trust_changing_host_keys,
                            known_hosts=known_hosts)
    return build_ssh_argv(host, cmd, user=user, key=key, options=options), host, known_hosts


def main(argv: list[str] | None = None, *, run=subprocess.run) -> int:
    args = parse_args(argv)
    try:
        import getpass
        built, host, known_hosts = plan(args, default_user=getpass.getuser())
    except UsageError as exc:
        print(f"fleet_ssh: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"argv": built}) if args.json else " ".join(built))
        return 0
    if known_hosts:
        # The directory must exist or ssh cannot create the file and warns on every call.
        Path(known_hosts).parent.mkdir(parents=True, exist_ok=True)
    return run_with_host_key_healing(built, host=host, known_hosts=known_hosts,
                                     heal=args.trust_changing_host_keys, run=run)


if __name__ == "__main__":
    sys.exit(main())
