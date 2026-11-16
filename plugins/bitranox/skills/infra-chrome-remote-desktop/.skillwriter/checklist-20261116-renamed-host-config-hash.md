# skill-writer checklist - infra-chrome-remote-desktop (2026-11-16, renamed host: config hash)

- [x] Receipt fresh; Step 0b `show` printed nothing (no ledger yet for this skill).
- [x] Premise checked against the source, not the report: the installed chrome-remote-desktop
      151.0.7922.13 start script (`/opt/google/chrome-remote-desktop/chrome-remote-desktop`)
      sets `g_host_hash = hashlib.md5(socket.gethostname().encode()).hexdigest()` and opens
      `host#<hash>.json` (also `host#<hash>.display_layout.pb`); a missing file prints
      `Failed to load config: ...` to stderr, which the unit sends to the journal, and returns 1.
      The upstream Chromium source was not fetched; the installed script is that file.
      `printf %s "$(hostname)" | md5sum` equals the script's hash on the test box.
- [x] Corrected from the report: it said the unit exits "with no error line"; the 151 script
      prints one, so the text says "at most" that line and keeps the 142.0.7444.18 observation
      as the reason to confirm by hash. Line numbers from the report are not used.
- [x] Inherited, not re-measured: that `host_id` and `private_key` stay valid after the move and
      the host logs `Host ready to receive connections` (no CRD host was available to rename).
- [x] The shipped bash block executed against scratch config dirs (getent, the backup dir and
      systemctl substituted): renamed (moved `.json` and `.display_layout.pb`, backup made),
      none, already matching, two files - each of the last three refused with rc 1.
- [x] RED (pre-edit excerpt, opus and haiku `baseline-probe`): haiku found no cause and would
      have run the binary by hand; opus knew the hash from its own knowledge but quoted NONE from
      the text. Both noted the offline row restates the symptom.
- [x] GREEN (new rows and section, opus and haiku quote-back): both named the hash cause, moved
      the file, refused a fresh code, and refused to move it on a renamed clone, each quoted.
- [x] GREEN gaps closed: the old hash is derived, not typed; the block refuses unless exactly one
      config exists and when the hash already matches; `hostname` stated to print the same name;
      a `host_id` comparison for an unknown history; the offline row points at the new row.
      Re-probe on the final section, haiku: all four touched questions answered from quotes.
- [x] Gaps declined: the journal command (Step 1, SKILL.md line 19); what to do with several
      configs (the "exactly one" rule, line 186); the `\|` in the table cell (markdown escaping,
      the code block holds the runnable form); deleting the backup (left to the operator).
- [x] Width and fence check over the added lines printed nothing; ASCII only; no host name,
      address or private path; description unchanged.
- [x] Decisions: d-20261116-fe6b5ae8
