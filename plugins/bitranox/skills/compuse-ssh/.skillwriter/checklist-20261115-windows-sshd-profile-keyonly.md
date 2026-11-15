# skill-writer checklist - compuse-ssh (2026-11-15, Windows sshd: rule profile, key-only, restart)

- [x] Receipt issued; Step 0b `show` run: the skill had no ledger yet, so nothing rejected.
- [x] Premise checked against the old text: the setup block created the firewall rule only "if
      the rule is missing", under a different name (`sshd`) from the one the capability install
      creates (`OpenSSH-Server-In-TCP`), and said nothing about profiles, key-only settings or
      how to restart sshd. The new block enables the install's rule for every profile, or
      creates it with `-Profile Any`; it parses under pwsh.
- [x] RED (no skill, opus and haiku `baseline-probe`): both named the profile mismatch and the
      two sshd_config settings when asked directly. For the restart, opus recommended a detached
      `Start-Process` running `Restart-Service sshd` from inside the session - the route the
      incident showed never completes - and haiku was unsure whether a restart ends the session.
- [x] GREEN (new text excerpt, opus and haiku quote-back): all four questions answered from the
      new paragraphs.
- [x] GREEN gaps closed: both tiers had no command for the WinRM or scheduled-task routes, and
      opus noted the lockout risk of an administrator's key living outside the profile. Added
      `Invoke-Command`, "a one-shot SYSTEM scheduled task (registered with no trigger, as in
      `bitranox:coding-python-pwshpy`)" and "Confirm a key login works first" with the
      `administrators_authorized_keys` location. Re-probe on the final paragraph, haiku: answered
      the admin-key, restart and verify questions from the quotes.
- [x] Gaps declined: whether to switch a Public NIC to Private instead of widening the rule is a
      site decision; the text keeps `-Profile Any`, which is what makes a fresh host reachable.
- [x] Width and fence check over the added lines printed nothing.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-96797719
