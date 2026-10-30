# skill-writer checklist - coding-python-pwshpy (sweep 2: ACL on macOS, Secret Service refusal, .ps1 POSIX relaunch)

- [x] Rule 1 ([230]): `get_acl`, `add_acl_ace`, `remove_acl_ace` and `set_owner` support Windows and
      Linux; on macOS each raises `PlatformUnsupportedError` at the call.
      Where: SKILL.md, the ACLs line of the command list. Backed by: src/pwshpy/composition/facade.py
      (`_require_acl`, called first in each of the four methods, before any Pipeline is built).
- [x] Rule 2 ([170]): a Secret Service D-Bus `AccessDenied` or `InteractiveAuthorizationRequired` is a
      `NativeAccessDeniedError` (so `except PermissionError` catches it); any other Secret Service error
      stays a plain `NativeCallError`.
      Where: SKILL.md, the `NativeAccessDeniedError` parenthesis and the plain-`NativeCallError` list of the
      error-model bullet. Backed by: src/pwshpy/adapters/native/dbus_errors.py (`_DENIED_ERROR_NAMES`,
      `reply_error`) and its use in adapters/native/secret_service.py `_Session.call`.
- [x] Rule 3 ([220], [280]): on Linux and macOS the `.ps1` `-PwshPyElevate` relaunches root pwsh through a
      fixed `/bin/sh` stub with root's passwd home; root pwsh writes nothing into the caller's home and keeps
      the caller's module directory out of its module path; the script sees the home variables sudo passed;
      the runner's silent no-password check runs the same `/bin/sh` command, so a NOPASSWD rule naming only
      `pwsh` does not spare the `sudo -v` prompt (no terminal: exit 77); no root home or no `/bin/sh`: exit 70.
      Where: SKILL.md, end of the packed-runner paragraph, and the exit-70 clause of the exit-code paragraph.
      Backed by: src/pwshpy/adapters/native/templates/pack_runner.ps1 (`Get-PwshPySudoCommandPrefix`, used by
      both the probe and the relaunch; the stub text; the two `cannot elevate` exits) and the runner tests
      tests/test_pack_e2e.py (relaunch argv, hand-back under env_reset and env_keep, refusal) on the merged
      tree; the real-sudo behaviour is re-measured on a Linux container in the same release cycle.
- [x] Receipt held (skill_receipt.py start meta-skill-writer before the first edit).
- [x] Inherited context: this machine's project instructions already state rules 1-3, so a behavioural RED
      could pass from context. Route taken: a coverage check against the skill FILE - every answer had to
      be a verbatim quote of the given file or NONE, and each quote was checked against the file.
- [x] RED, opus, pre-edit text, 5 questions: NONE on rule 1 (macOS get_acl), rule 3 relaunch home and the
      pwsh-only NOPASSWD case; WRONG on rule 2 (answered "plain NativeCallError, except PermissionError does
      NOT catch it", quoting the old list); partial on exit 70 (no `cannot elevate` case).
- [x] GREEN round 1, opus and haiku, same 5 questions: all correct and quoted on both tiers.
      Gaps closed in the text: when macOS raises (at the call); which HOME the script sees (named);
      what happens with no terminal (exit 77); what "no home for root" means (passwd database); the runner's
      probe named as the runner's own. Declined: the full D-Bus error name (the text's `AccessDenied` is
      unambiguous in context); the stderr lines of the other exit-70 cases (outside this change).
- [x] GREEN round 2, opus and haiku, 5 questions (Q3 rewritten to the realistic shape: stock `%sudo ALL`
      plus a NOPASSWD rule for pwsh, terminal and no-terminal): all correct and quoted on both tiers.
      Gap closed: "no longer spares" (history phrasing) rewritten as current behaviour, and the prompt named
      as the one `sudo -v`. Declined: CLI exit code of macOS get_acl (a PwshPyError, exit 1, in the
      exit-code list); errno of a D-Bus refusal (not material); root pwsh's own cache location (covered by
      "root's own home"); the exact HOME/XDG name list (outside the skill's scope).
- [x] GREEN round 3 (the questions the round-2 fix touched: Q3), opus and haiku, final text: both correct and
      quoted. Gaps declined: sudoers path form, why sudo -v prompts beside a NOPASSWD rule, cached credentials
      (sudo semantics, out of scope); `elevate()`'s probe vs the runner's probe read as two accounts by haiku,
      which still answered from the right one - the text names the runner's check as the runner's own and the
      two are different entry points. No new undecided gap.
- [x] Tiers haiku and opus; cells: RED 5 (opus), round 1 10, round 2 10, round 3 2.
- [x] Width check over the added lines: none over 100 columns; no fence touched. Paragraph after each
      insertion point read: no re-bound back-reference, no duplicated bullet.
- [x] History-phrase finder over the added lines: no hit.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense; no address, hostname or private path added.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
