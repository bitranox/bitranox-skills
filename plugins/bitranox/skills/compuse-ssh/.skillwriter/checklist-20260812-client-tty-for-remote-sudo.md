# skill-writer checklist - compuse-ssh (a client-side TTY for remote interactive sudo)

Change: one Quick reference row plus one Authentication bullet - why remote interactive `sudo`
cannot prompt when the CLIENT's stdin is not a terminal, and how the first key reaches a fresh
Ubuntu host whose sshd refuses a root password but accepts a root key. Reference-skill edit, no
scripts.

## PLAN
- [x] Skill type: reference (a symptom-indexed table). Test approach: retrieval - given the failure,
      does an agent holding the text reach the cause and a working next step?
- [x] Trigger is measured, not hypothetical: two compounding blockers during a key bootstrap, each
      presenting as a rejected password - a `sudo` prompt with no tty to write to, and root password
      auth refused by the distro default while a root key would have been accepted.
- [x] Checked it is not already shipped: `claim_check.py --pattern 'controlling TTY|no pty|allocate a
      pty|ssh -t|prohibit-password|PermitRootLogin' --control 'ssh'` reports ABSENT with the control
      matching 53 times, so the file was read. The nearest rows are "Host wants a password" (key
      auth, `BatchMode`) and "Backgrounding a remote command" (a remote process holding the tty);
      neither is the client-side pty condition.
- [x] Scope: one row among the other auth-failure rows, one bullet in the section that already owns
      key installation.

## RED
- [x] Retrieval baseline, an agent given the pre-change text and an unattended job whose
      `ssh -t ... sudo ...` fails with repeated `Permission denied` while the same password works
      from a terminal, asked to quote the governing sentence or answer NONE: it answers "On that
      specific point: NONE."
- [x] Its gaps list names the missing content exactly: "The text never explains why an interactive
      terminal session succeeds with the identical password while a non-tty pipe fails - no
      discussion of `sudo`'s own tty/askpass requirement or of ssh password-prompt behavior on
      non-interactive stdin."
- [x] Contamination recorded rather than claimed away, two sources. The arm reasons a mechanism out
      of model knowledge ("the process's stdin is a pipe with no terminal behind it, so neither
      ssh's own password prompt nor a subsequent `sudo` prompt ... can be answered") and marks it as
      its own inference, not as something the text says. Always-loaded project docs in the authoring
      environment carry the same lesson, so a from-scratch RED cannot be isolated here. The arm that
      survives both is the COVERAGE question - what does the SKILL say - and that answers NONE.
- [x] Both probe arms run with no tools at all, so nothing was explored or read into the answer.

## GREEN
- [x] Same scenario with the new text: the arm quotes the new row verbatim, states the cause ("the
      `-t` flag needs a real controlling TTY on my end ... so remote `sudo` has nothing to prompt
      on"), rejects the credential reading ("The password rotation is irrelevant to this failure"),
      and lands a compliant command - no `-t`, `sudo -n`, `BatchMode=yes`,
      `PreferredAuthentications=publickey`.
- [x] It reaches the second half from the new bullet too: install into the sudo user's OWN
      `authorized_keys`, "not root's - only devuser exists".
- [x] Every dispatch asked for a `Skill gaps` section, and every reply's list is recorded here.

## REFACTOR
- [x] GREEN gap, CLOSED: an arm read the `/dev/tty` clause as permission-adjacent and reported it as
      a conflict - "reads almost like a usable path, while the Authentication section
      unconditionally bans any password use ... the text does not itself say which should win". The
      clause now states its purpose and defers: it is a diagnostic, never a licence to feed a
      password in, and the no-password rule still binds.
- [x] GREEN gap, CLOSED: the same arm could not tell which no-tty condition applies ("The text does
      not say whether a process with 'no terminal attached' still has a `/dev/tty` to open at all").
      The row now names the condition as the client's own stdin and says `/dev/tty` survives a
      redirected stdin.
- [x] Quote-back on both fixes, re-asking only the questions the fix touched. "Does the text permit
      using the password you hold" answers with the quote "it is a diagnostic, never a licence to
      feed a password in; the no-password rule below still binds". "stdin, or no controlling terminal
      at all" answers with "`-t` allocates a pty only when the CLIENT's own stdin is a terminal". The
      same arm reports "No contradiction between the three rows".
- [x] Gaps DECLINED with a reason: how the very first key reaches a fresh host when no human is
      reachable, and how a NOPASSWD rule is configured without existing privileged access. Both are
      the escalation this skill deliberately keeps ("If a host still needs a password, STOP and
      propose the setup"), and the bullet already names the console route. Answering them means
      prescribing a provisioning pipeline, which is another skill's subject.
- [x] GREEN diffed against RED in BOTH directions. Gained: the cause, the refusal to blame the
      credential, `sudo -n`, and the sudo-user key target. LOST: the baseline arm additionally
      re-derives evidence first - it runs `ssh -v host 'echo ok'` and declines to assume exit 255 -
      where the GREEN arm goes straight from symptom to cause. Declined rather than traded away: the
      new row supplies the diagnosis that probe was hunting for, the "ROOT-CAUSE it" row that
      mandates the probe is untouched and still in the table, and GREEN is strictly better on both
      goals. Recorded as a single-run observation, not established as stable.

## Quality
- [x] Present tense in the row, the bullet and this artifact; no narrative, no scratch paths.
- [x] Every value added is generic or reserved: `host.example`, `devuser`, `~/.ssh/authorized_keys`,
      `/dev/tty`. Verified - the added lines match no IPv4, MAC, `/home/`, `/Users/` or `/tmp/`
      pattern.
- [x] The row keeps the table's shape and sits with the other auth-failure rows; the table is
      realigned by the formatting hook.
- [x] No scripts added, so there is nothing to test beyond the repo suite, which the gate runs green
      with the CI dependency set.
- [x] Frontmatter description untouched, so the derived trigger map needs no rebuild.
- [x] Security review of the diff: no secrets, credentials, private hostnames or paths, and no code.

## Deliverables
- [x] `SKILL.md`: the "Remote interactive `sudo`, or `ssh -t`" row, and the "Installing a key for
      root when only the sudo user can log in" bullet under Authentication and host keys.
- [x] `plugin.json` 5.180.0 -> 5.180.1 (wording and content inside an existing skill), CHANGELOG
      entry added.
