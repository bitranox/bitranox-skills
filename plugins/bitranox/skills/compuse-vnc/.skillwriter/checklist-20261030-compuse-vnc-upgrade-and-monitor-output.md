# Review checklist 2026-10-30: install-or-upgrade, and silencing qm monitor

Entries covered:

- E1: the `qm monitor` password command printed the monitor's output, which carries the password.
- E2: Step 0 kept an old install (`command -v ... || uv tool install`), so documented options
  such as `type --us-shift` were missing.

Files: `SKILL.md` (Step 0 install line plus one paragraph; the Proxmox password bullet).

## Claims and their evidence

- [x] E2: PyPI lists releases up to 1.2.0. `uvx --from vnc-remote-control==1.1.4
      vnc-remote-control type --help` shows `--enter` only; 1.2.0 shows `--us-shift`. 1.1.4
      run with `--us-shift`: `Error: No such option '--us-shift'.` `uv tool upgrade <absent>`
      fails ("is not installed"), so the install line is `uv tool install --upgrade`: in a
      sandboxed UV_TOOL_DIR, 1.1.4 installed, then `uv tool install --upgrade vnc-remote-control`
      -> `+ vnc-remote-control==1.2.0`. `vnc-remote-control --version` prints
      `vnc-remote-control version 1.2.0`. No per-flag version list was added (the skill describes
      the latest release only).
- [x] E1: qemu-server `src/PVE/CLI/qm.pm` monitor: `my $term = Term::ReadLine->new('qm');
      while (defined(my $input = $term->readline('qm> ')))`, so input is read through readline
      with a `qm> ` prompt; the echo of piped input itself is the reporter's observation, not
      reproduced here (no Proxmox host touched). Redirecting both streams is safe either way: the
      result is judged by the client's login, which the skill already uses.

## Mechanical checks

- [x] Added lines ASCII only, under 100 columns, no history-finder hit, no private path.
- [x] The paragraph after each insertion point read: "For a one-off without a persistent
      install" and "Without `expire_password` ..." still read correctly.

## Probes (bitranox:baseline-probe, text only)

- [x] RED (opus, pre-edit text): Q1 NONE ("says nothing about the monitor's output"); Q2 quoted
      "skip if already installed" and reported "the `command -v ||` guard keeps a stale version
      silently".
- [x] GREEN (opus): Q1 quoted "Send ALL of the monitor's output to `/dev/null` ..."; Q2 quoted
      "Do not skip the install because `vnc-remote-control` is already on PATH ...".
- [x] GREEN (haiku): Q1 "Not OK. Do not pipe the output through `grep -v '^qm>'`" with the same
      quote; Q2 "Yes, install" with the same quote.
- [x] Gaps declined: "judge by the client's login cannot tell a failed set_password from a wrong
      password in pw.txt" (both come from the same file in the same command, so a login failure
      means the monitor step failed or expired; the existing text names the expiry case); the
      tesseract line is apt-only (pre-existing, other platforms are in its trailing comment).
