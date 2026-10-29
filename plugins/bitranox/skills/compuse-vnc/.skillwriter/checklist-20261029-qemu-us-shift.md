# skill-writer checklist - compuse-vnc (QEMU console: --us-shift, socket, password)

- [x] Change: Commands table (`type ... [--us-shift]`), Gotchas (layout-aware wording scoped to
      such a server, new "QEMU's own VNC server needs `type --us-shift`" bullet), Authentication
      (None security scoped to openvmm), "Proxmox / no-network VMs" (the old claim that a plainer
      server types any US-layout text replaced by three QEMU differences: unix socket, VNC
      password via `set_password` + `expire_password vnc never`, `--us-shift`).
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the edit was committed.
- [x] Mechanism claims measured on a Proxmox QEMU console, not reasoned: `type 'x@A2Z|'` landed
      as `x2A2Z\` without the flag and intact with `--us-shift`; a password set without
      `expire_password` failed authentication, with it succeeded; the documented
      `printf 'set_password vnc %s\nexpire_password vnc never\n' "$(cat f)"` form authenticated
      with a file that has no trailing newline. Unmeasured scope is written into the text as
      untested (a `keyboard:` value other than en-us).
- [x] RED as a text check (opus, pre-edit text): Q1 typing '@' lands as '2' PARTIAL (only "fix
      the SERVER layout, never compensate", which contradicts the plain-server claim), Q2 reach
      and authenticate PARTIAL (`<console-port>` unfillable, None called the typical Proxmox
      case), Q3 German installer layout PARTIAL (no guest-side choice).
- [x] GREEN quote-back on the edited text: opus 6/6 stated (incl. a control: openvmm with a German
      guest -> leave `--us-shift` off, quoted), haiku all six found, PARTIALs only where the
      question's literal string is not in the file.
- [x] Skill gaps from GREEN, decided: auth contradiction (None "the typical Proxmox case") CLOSED;
      password file without trailing newline merging the two monitor commands CLOSED (printf
      form, verified); client command and same-password tie CLOSED; keymap scope CLOSED as
      "untested" in the text; where the file lives CLOSED ("on the machine you drive from");
      Proxmox bullet unconditional vs keymap caveat CLOSED ("with the default en-us keymap").
      DECLINED: option position before/after the text (click accepts both, standard CLI
      behaviour); a menu path for the installer's keyboard (installer-specific, out of scope);
      a `keyboard:` value for openvmm (owned by openvmm's own docs, unchanged by this edit); a
      rule for a QEMU VM with a non-en-us `keyboard:` (never measured, so the text says
      "untested" instead of guessing either way); a check that the password file is gone (one
      `rm`, no state to verify).
- [x] Re-probes after the fixes: opus + haiku on the touched questions (password commands, auth
      agreement, keymap, both arms quote the new text and report the sections agree); a final
      haiku run on the last two fixes (file location, keymap condition).
- [x] Mirror: edited in the vnc-remote-control repo and regenerated here (H1 parenthetical
      differs by convention); repo-gate --mirrors: 0 of 12 drifted.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, no version history, tables canonical, added prose wrapped.
- [x] Placeholders only (`<node>`, `<vmid>`, `<local-port>`, `pw.txt`); no host, address or path
      from this machine.
