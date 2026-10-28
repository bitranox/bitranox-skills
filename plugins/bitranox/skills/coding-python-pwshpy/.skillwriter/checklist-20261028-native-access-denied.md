# skill-writer checklist - coding-python-pwshpy (2026-10-28, NativeAccessDeniedError and .hresult)

Change: the "Errors, timeouts and exit codes" section names `NativeAccessDeniedError` (a
`NativeCallError` and a `PermissionError`), states that the type follows the code a failure
carried (so a D-Bus error reply, a polkit refusal included, stays the plain `NativeCallError`),
documents `.hresult` (unsigned HRESULT, Win32 codes via `HRESULT_FROM_WIN32`, `None` on Linux and
macOS), and adds exit 13 (5 on Windows) to the exit-code list. Frontmatter unchanged; no other
section touched. The tool repo's `skills/using-pwsh/SKILL.md` carries the same text; the two
differ only in the `name:` line.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: RED as a text check of the pre-edit file (an EDIT; the
      installed copy is the old text), GREEN as quote-back retrieval probes.
- [x] RED (text, pre-edit file): the section read "A control the OS refuses (a service stop
      denied, a missing executable) is the plain `NativeCallError`", which the change makes false
      for a denied service stop, and it named no `.hresult` and no exit 13.
- [x] Mechanism claims checked against the code, not the prose:
      `adapters/native/marshal.py` `_DENIED_ERRNOS = {EACCES, EPERM}`, `_judge` (HRESULT decides
      when present, errno otherwise, a pwshpy error taken as is), `_cause_hresult` (pywin32 code or
      an OSError's `winerror` only, so `None` on Linux and macOS), `_win32_to_hresult`;
      `adapters/native/systemd_dbus.py` raises a plain `NativeCallError` for every D-Bus error
      reply; `adapters/cli/main.py` maps the type to PermissionError's exit code. Measured on a
      Windows host: a denied `HKLM\SAM\SAM` open raised `NativeAccessDeniedError` with
      `.hresult` 0x80070005, and the CLI exit test passed natively there (exit 5).
- [x] GREEN quote-back, round 1 (`opus` effort medium and `haiku`, 6 questions each, 12 cells):
      both quoted the governing sentences for the type, `except PermissionError`, `.hresult`,
      exit 5 on Windows and the catch order, and answered NONE for a `.winerror` attribute.
      Gaps both tiers reported, CLOSED: a polkit refusal was unnamed, and the `.hresult` advice
      said nothing for Linux and macOS.
- [x] Round 2 (both tiers, 4 questions, 8 cells): correct quotes. Gaps CLOSED: the text read as
      two rules for a rights refusal (definition by reason vs the D-Bus sentence), now "The type
      follows the code the failure carried, not the reason" with the reason a D-Bus reply carries
      no code; the Win32-to-HRESULT conversion was unstated.
- [x] Round 3 (both tiers, 3 questions, 6 cells) on the final text: both quoted "The type follows
      the code the failure carried, not the reason", typed a Win32 error 5 registry refusal as
      `NativeAccessDeniedError` from "reads `0x80070005`, `E_ACCESSDENIED`", and said a polkit
      refusal is the plain `NativeCallError` because the reply carries no errno and no HRESULT.
      No new undecided gap.
- [x] Gaps DECLINED:
      - no programmatic way to tell a polkit refusal from another D-Bus error: a behaviour gap in
        the library, not the text; the skill states what the library does;
      - `errno` on a Windows denial and on the plain `NativeCallError`: the text attaches `errno`
        to the `PermissionError` subclass "when the failure carried one" and names `.hresult` as
        the Windows signal;
      - `ElevationDeclinedError` in the catch order: covered by "catch a subclass before its
        parent" at the head of the same section;
      - `OperationTimeoutError`'s parent and the exit-77 scope: stated earlier in the same section
        and exit list (the probes saw an excerpt);
      - psutil `AccessDenied` `.hresult` on Windows and the matching mechanics per code kind:
        implementation detail the reader does not branch on.
- [x] Version-history finder over the added lines: no hit (control phrase hits).
- [x] Address sweep over the added lines: no address, MAC, home or temp path.
- [x] No session narrative or private provenance in the skill or this artifact.
