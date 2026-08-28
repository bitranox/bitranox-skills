---
name: infra-chrome-remote-desktop
description: Use when installing, registering, or repairing a Chrome Remote Desktop host on Linux (a VM, an LXC container, or a workstation) - the web client answers "PIN is not valid" although the PIN is right, a session connects and drops straight away, the host shows offline, start-host dies with "Failed to set new config" or "Failed to start host", sudo refuses with "The \"no new privileges\" flag is set", or the host journal logs "pam_acct_mgmt() returned error 7" or "Local login check for <user> failed". Covers the per-connection PAM account check, /etc/shadow group ownership and unix_chkpwd, registering as the target user, single-use OAuth codes, the stored PIN hash, and the chrome-remote-desktop@<user> service.
---

# Chrome Remote Desktop on Linux (infra-chrome-remote-desktop)

Installing a Chrome Remote Desktop (CRD) host is the small half of this. The large half is that
CRD reports several unrelated failures through one misleading message, so the repair path starts
by finding out which failure you actually have.

**The web client names the wrong subsystem.** CRD runs a PAM account check for the connecting
user on every incoming connection, as the unprivileged desktop user. A rejected account check is
rendered in the browser as "PIN is not valid". The PIN is not involved.

## Step 1 (always first): read the host journal during a connection attempt

```bash
journalctl -u chrome-remote-desktop@<user> -f
```

Leave that running, have the user connect, and read what appears. This costs seconds and it is
the only thing that distinguishes the causes below from each other.

**Do not re-register the host, reset the PIN, delete the device entry, or spend an OAuth code
before you have read this.** Those actions are the expensive wrong turn: a host that is already
registered correctly will re-register correctly and fail in exactly the same way, and each
attempt consumes a single-use code that only the end user can replace.

An account-check failure looks like this:

```
pam_unix(chrome-remote-desktop:account): setuid failed: Operation not permitted
pam_utils.cc:72  pam_acct_mgmt() returned error 7
pam_utils.cc:78  Local login check for <user> failed.
jingle_session.cc:428  Session closed with error 4: Local login check failed.
```

## Symptom to cause

| Symptom the user reports                             | Real cause                                                                                                    | Confirm with                                                                                                                     | Disproved if                                                                                      |
|------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| "PIN is not valid" every time, host listed as online | PAM account check rejects the user                                                                            | journal shows `pam_acct_mgmt() returned error 7`                                                                                 | journal shows no `pam_` line during the attempt - the PIN may be genuinely wrong, verify the hash |
| Connects, then drops immediately                     | Same account-check failure, later in the handshake                                                            | journal shows `Session closed with error 4`                                                                                      | journal shows a network or relay error instead                                                    |
| Host shows offline in the device list                | The service is not running                                                                                    | `systemctl status chrome-remote-desktop@<user>`                                                                                  | the unit is `active (running)` - the host is registered to a different account or machine         |
| `sudo: The "no new privileges" flag is set`          | `start-host` ran as root (the binary sets the flag on itself), or the target user's shell already carries NNP | `whoami` in the shell that ran it; if that was already the target user, `runuser -u <user> -- grep NoNewPrivs /proc/self/status` | you ran as the target user AND that reads `0` - the flag is not the obstacle, look elsewhere      |
| `Failed to set new config` / `Failed to start host`  | The run died after the OAuth code was already spent                                                           | `ls ~<user>/.config/chrome-remote-desktop/host#*.json`                                                                           | no config file was written at all                                                                 |
| Two device entries, one permanently dead             | A cloned image inherited the source host's config                                                             | more than one `host#*.json`, or a `private_key` from the source                                                                  | exactly one config whose `host_id` matches the live entry                                         |

## The account-check failure: /etc/shadow group ownership

`pam_unix` does not read `/etc/shadow` directly for an unprivileged caller. It delegates to
`unix_chkpwd`, which is **setgid `shadow`, not setuid root**:

```bash
ls -l /sbin/unix_chkpwd     # -rwxr-sr-x 1 root shadow
```

So the helper's only claim on the file is its group. When `/etc/shadow` is owned `root:root`
instead of `root:shadow`, the helper cannot read it and `pam_acct_mgmt` fails for every non-root
caller. Many container and VM base images ship it that way.

```bash
stat -c '%n %U:%G %a' /etc/shadow /etc/shadow- /etc/gshadow /etc/gshadow-
# healthy: root:shadow 640 on all four

chgrp shadow /etc/shadow /etc/shadow- /etc/gshadow /etc/gshadow-
chmod 0640   /etc/shadow /etc/shadow- /etc/gshadow /etc/gshadow-
```

### Verify as the unprivileged user, never as root

Root passes the account check whether the ownership is fixed or not, so a check run as root
returns success in both worlds and therefore asserts nothing. Install `pamtester`
(`apt install pamtester`) and drop privileges:

```bash
runuser -u <user> -- pamtester chrome-remote-desktop <user>     acct_mgmt   # expect rc 0
runuser -u <user> -- pamtester chrome-remote-desktop nosuchuser acct_mgmt   # expect rc 1
```

The second line is not decoration. It is the control that proves the first line could have
failed. A check that cannot fail asserts nothing, and a PAM stack misconfigured to permit
everything passes the first line exactly like a healthy one.

**What disproves the fix:** the first command returning non-zero. **What invalidates the test
itself:** the second command returning 0.

`stat` tells you whether the cause is present. Only the `runuser` pair tells you whether the
effect is gone.

If `pamtester` cannot be installed, the fallback effect check is a real connection attempt with
the journal open (Step 1): the `pam_` lines stop appearing. It is slower and needs the user, so
prefer `pamtester` where you can install it.

**No restart is needed.** The account check runs per incoming connection, in a freshly spawned
`unix_chkpwd`, so the next connection attempt picks up the new file mode. Have the user retry and
confirm from the journal rather than restarting the service and assuming.

## Registration: run start-host as the target user

```bash
# as <user>, NOT as root
/opt/google/chrome-remote-desktop/start-host \
    --code="<code>" \
    --redirect-url="<redirect-url>" \
    --name="<host-name>" \
    --pin=<pin>
```

Run as root, the Chromium binary sets `PR_SET_NO_NEW_PRIVS` on itself. The `sudo` call it then
makes to write the config is refused outright:

```
sudo: The "no new privileges" flag is set, which prevents sudo from running as root.
```

`--user-name=<user>` does **not** avoid this. The obstacle is the flag on the running process,
not the account being targeted.

**If you saw that message and you ran `start-host` as root, that is the cause and there is
nothing to probe.** The flag is set by the spawned binary on itself, so the root shell you
launched it from still reads `NoNewPrivs: 0`. Probing the invoking shell here answers a question
you did not ask and points away from the real cause.

The same message has a second, unrelated source: an interactive shell inside some containers
already carries the flag, so the run fails even as the right user. That is the case the probe is
for, and it is run as the target user, not as yourself:

```bash
runuser -u <user> -- grep NoNewPrivs /proc/self/status    # must read 0
```

**A run that reached this message has already spent the OAuth code.** The token exchange happens
before the config write, so `Failed to set new config` is downstream of it. Fixing the invocation
and retrying with the same `--code` fails again on a dead code. Line up a fresh one before the
next attempt, and clear the half-written config first (see below).

As the target user, the remaining obstacle is that `sudo` wants a password. Grant it for the
duration of the run and make the cleanup unconditional, so the grant cannot outlive the command
that needed it:

```bash
#!/bin/bash
set -euo pipefail
GRANT=/etc/sudoers.d/crd-register-tmp
trap 'rm -f "$GRANT"' EXIT
printf '%s ALL=(ALL) NOPASSWD: ALL\n' "<user>" > "$GRANT"
chmod 0440 "$GRANT"
visudo -cf "$GRANT"
runuser -u <user> -- /opt/google/chrome-remote-desktop/start-host --code="<code>" ...
```

## The OAuth code is single-use, and a failed run still spends it

The code is consumed by the token exchange, which happens *before* the config is written. A run
that dies at `Failed to set new config` has already burned it, and the user has to return to the
browser for another.

Check every precondition **before** spending one:

- [ ] The journal has been read and the failure is understood (Step 1).
- [ ] `runuser -u <user> -- grep NoNewPrivs /proc/self/status` reads `0`.
- [ ] `runuser -u <user> -- sudo -n true` succeeds (the grant is in place).
- [ ] `runuser -u <user> -- pamtester chrome-remote-desktop <user> acct_mgmt` returns 0.
- [ ] The command runs as `<user>`, not as root.

A run that ends `Host started successfully.` with rc 0 registered both sides. A run that dies
later leaves a local config whose `host_id` may not match the directory entry. Clear that slot
before the next attempt rather than layering one on top of it - and move the file aside instead
of deleting it, because it is the only record of what the failed run wrote:

```bash
CRD_DIR="$(getent passwd <user> | cut -d: -f6)/.config/chrome-remote-desktop"
KEEP="$CRD_DIR/failed-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$KEEP"
mv "$CRD_DIR"/host#*.json "$KEEP"/
```

Resolve the home directory with `getent` rather than writing `~<user>`, which is not expanded
inside quotes or in a variable and silently becomes a literal path component.

## Verifying which PIN is stored

The config lives at `~<user>/.config/chrome-remote-desktop/host#*.json`, and **there must be
exactly one**. Extra files from earlier registrations, and the `host_id` plus `private_key` a
cloned image inherits from the machine it was cloned from, produce a device entry that can never
connect. Remove them.

The stored value is `"hmac:" + base64(HMAC_SHA256(key=host_id, message=pin))`. This is an
internal, undocumented format, read off chrome-remote-desktop 151.0.7922.13 (2026-08-28);
Google can change it in any release. Check your own build with
`dpkg -l chrome-remote-desktop`, and run the positive control below before trusting a
verdict - a changed construction shows up there as a control that no longer passes.

```python
import base64, hashlib, hmac, json, sys


def matches(cfg, pin):
    computed = "hmac:" + base64.b64encode(
        hmac.new(cfg["host_id"].encode(), pin.encode(), hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(computed, cfg["host_secret_hash"])


# Guarded so this file can be imported by the control below without reading a real config.
if __name__ == "__main__" and len(sys.argv) > 2:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    print(sys.argv[2], matches(cfg, sys.argv[2]))
```

Save that as `crdpin.py`.

**The argument order carries the whole result.** `host_id` is the key and the PIN is the
message. Swap them and the comparison fails for every possible input, so the check reports a
mismatch whatever is stored - a false negative that reads exactly like a real finding, and one
that invites you to "fix" a PIN that was never wrong. The same is true of the other plausible
constructions (a plain `SHA256(host_id + pin)` concatenation is not what CRD stores).

Because of that, one run proves nothing. Run two:

- a PIN you know is right **must** print `True` - this is what catches the swapped key and
  message;
- a PIN you know is wrong **must** print `False` - this is what catches an implementation that
  cannot report a mismatch.

Only both together make a single result meaningful.

When you have no known-good PIN - the usual case, since the stored PIN is the unknown you are
resolving - manufacture one. Build a config of your own with a `host_id` and a PIN you choose,
and require the same function to return `True` on it:

```python
# Same directory as crdpin.py above. Needs no config file and no argv, so it runs
# BEFORE you touch the real one - which is the whole point of a positive control.
from crdpin import base64, hashlib, hmac, matches

host_id, pin = "test-host-id", "999000"
probe = {"host_id": host_id,
         "host_secret_hash": "hmac:" + base64.b64encode(
             hmac.new(host_id.encode(), pin.encode(), hashlib.sha256).digest()).decode()}
assert matches(probe, pin) and not matches(probe, "111222")
print("control OK: matches() reports True for the right PIN and False for a wrong one")
```

That is the positive control, and it needs no network and no correct answer in advance. Run it
before you believe anything the real config says.

## Session and service

The desktop that a connection lands in is chosen by `~<user>/.chrome-remote-desktop-session`:

```bash
SESSION="$(getent passwd <user> | cut -d: -f6)/.chrome-remote-desktop-session"
echo 'exec /usr/bin/mate-session' > "$SESSION"     # or the session binary this box has
chmod +x "$SESSION"
chown <user>: "$SESSION"
```

Enable the unit so the host survives a reboot, and read its journal, not the browser, for what
it does next:

```bash
systemctl enable --now chrome-remote-desktop@<user>
systemctl status chrome-remote-desktop@<user>
```

## Common mistakes

| Mistake                                                  | Why it goes wrong                                                                          |
|----------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Treating "PIN is not valid" as a PIN problem             | It is the rendering of a failed PAM account check. The PIN is never consulted.             |
| Re-registering before reading the journal                | A correctly registered host re-registers correctly and fails identically, one code poorer. |
| Testing the PAM fix as root                              | Root passes either way. The result is the same before and after the fix.                   |
| Running the positive pamtester case only                 | It passes against a permit-everything PAM stack too.                                       |
| Running `start-host` as root                             | The binary sets `PR_SET_NO_NEW_PRIVS` on itself and its own `sudo` call is refused.        |
| Reaching for `--user-name` to avoid running as the user  | The flag is on the process; the target account is not the problem.                         |
| Leaving the NOPASSWD grant in place                      | A registration convenience becomes a standing privilege escalation.                        |
| Retrying the fixed command with the same `--code`        | A run that reached the config write already spent it. The retry dies on a dead code.       |
| Probing the root shell for `NoNewPrivs` after a root run | The binary sets the flag on itself, so the invoking shell reads `0` and looks innocent.    |
| Stacking a second `start-host` on a half-written config  | The local `host_id` and the directory entry disagree and the host never connects.          |
| Trusting one PIN-hash comparison                         | The swapped-argument form returns `False` for every input.                                 |
| Cloning a machine that already had CRD registered        | The clone inherits `host_id` and `private_key` and fights the original for the entry.      |

## Red flags - stop

- About to ask the user for a fresh code, and `journalctl -u chrome-remote-desktop@<user>` has
  not been read during a failed attempt.
- About to report the PIN as wrong on the strength of a single `False`, with no run that has
  been seen to return `True`.
- About to report the PAM fix as verified, from a check that ran as root.
- About to re-run `start-host` with a code a previous run already reached the config write with.
- More than one `host#*.json` in the config directory.
- A `/etc/sudoers.d/` grant still on disk after registration finished.
