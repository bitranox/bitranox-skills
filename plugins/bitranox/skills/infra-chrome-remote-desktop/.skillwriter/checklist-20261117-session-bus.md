# skill-writer checklist - infra-chrome-remote-desktop (2026-11-17, session bus)

- [x] Receipt fresh; Step 0b `show --kind rejected,removed --full` printed nothing; the one live
      decision (d-20261116-fe6b5ae8, renamed host) is untouched by this change.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
- [x] Premise checked against the skill: its own session-file example is `exec /usr/bin/mate-session`
      with no bus line, so the skill never prescribed `dbus-launch`; the defect is the missing
      symptom row and Session note. The full pre-edit SKILL.md has 0 matches for `dbus|session bus`.
- [x] Premise checked against the launcher source (chrome-remote-desktop 151.0.7922.13,
      `/opt/google/chrome-remote-desktop/chrome-remote-desktop`): `_init_child_env` forwards
      `DBUS_SESSION_BUS_ADDRESS` and the X desktop copies the full environment into the session;
      `bash_invocation_for_script` starts the file with `/bin/sh -c <file>` (executable) or
      `/bin/sh <file>`, not bash; it sets `CHROME_REMOTE_DESKTOP_SESSION=1` in the session.
- [x] Measured on a host with a `dbus-launch` session file: the desktop's bus is a `/tmp/dbus-...`
      address while the CRD unit's own environment holds `unix:path=/run/user/<uid>/bus`;
      `org.freedesktop.secrets` is owned on the user bus and activatable but unowned on the private
      one. The shipped confirm block, run as root with `<user>` substituted, printed the marker,
      then NoReply after 25.03 s on the desktop bus and 0.015 s on the user bus.
- [x] Marker line controls: present in the CRD desktop's environment, absent from PID 1 and from
      the CRD launcher process (grep rc 1 on both). A process started from inside the CRD desktop
      inherits it, so the marker separates the CRD desktop from a local login, not its children.
- [x] The shipped fix block executed under `/bin/sh` (dash) with stubbed `dbus-launch`,
      `dbus-update-activation-environment` and session binary: socket present exports the user-bus
      address and calls the updater; socket absent takes the `dbus-launch` fallback. The updater
      skips an unset `XAUTHORITY` with rc 0 (run on a throwaway `dbus-run-session` bus). It ships
      in `dbus-bin` (`dpkg -S`).
- [x] redcheck `--corpus-cascade .`: verdict inherited, but the shared terms are ordinary
      (chrome, desktop, mate); neither named document states the bus split. Behavioural RED kept.
- [x] RED (pre-edit excerpt: symptom table and Session section; opus and haiku `baseline-probe`):
      both quoted NONE for cause and fix. haiku listed DNS, the bus and the session script as
      guesses and tested the bus with `ListNames`; opus named the 25 s D-Bus timeout but proposed
      setting `XDG_CURRENT_DESKTOP` or starting `gnome-keyring-daemon` in the session file and
      never checked which bus the desktop is on.
- [x] GREEN (edited excerpt, same question plus a disproof question; opus and haiku): both named
      the private bus, ran the shipped check, applied the fallback-only session file, said it takes
      effect at the next session start, and refused a keyring daemon in the session file, each
      quoted. Nothing from RED was lost.
- [x] GREEN gaps closed: several `mate-session` PIDs (`pgrep -n` plus the
      `CHROME_REMOTE_DESKTOP_SESSION=1` marker line); a fast `ServiceUnknown` read as healthy (the
      prose and the disproof cell now require an answer with no error); the updater's package; the
      re-check now times the browser's first window; the disproof cell covers a private bus that
      answers fast.
- [x] Gaps declined: diagnosing a keyring that is slow on the user bus too (a keyring problem, not
      a CRD one; the row and the control Ping hand it off); a desktop-portal 25 s stall (not
      measured here); whether a reconnect starts a new session (not verified, so the text names
      only the unit restart); site deployment from a machine repo (site-specific); the unit name
      and session-file path (stated earlier in the same section, SKILL.md lines 255 and 267);
      `--password-store=basic` as an A/B (not needed once the Ping pair answers).
- [x] Quote-back on the final text (six questions, opus at effort medium and haiku): every answer
      a verbatim quote. The marker line added after it was re-probed on haiku (which PID is the
      CRD desktop, what a missing marker means, what a healthy user-bus answer is): all three
      quoted. Its one new gap, what to do when the marker is missing, is closed by a comment
      naming the other `pgrep` PIDs; thresholds beyond "about 25 s" against "milliseconds" and an
      exit-code contract for the check are declined (the two outcomes are three orders apart).
- [x] Width and fence check over the added lines printed nothing; ASCII only; tables reformatted;
      no host name, private path or CRD version in the new text; description unchanged (the skill
      already loaded for this symptom).
- [x] Cases decided beyond the report: fallback to `dbus-launch` when the user-bus socket is
      missing (the entry's own fix), and `-n` for several desktops (newest) with the marker as the
      check. Neither overrides a user ruling.
- [x] Decisions: d-20261117-a42932af
