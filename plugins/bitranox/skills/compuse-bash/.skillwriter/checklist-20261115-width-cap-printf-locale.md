# skill-writer checklist - compuse-bash (2026-11-15, width-capped listings and printf locale)

- [x] Receipt issued; Step 0b `show` run: the rejected rows (grep shim, BSD grep escapes, awk
      END) are about other commands; nothing covers `cut -c` or `printf` float formats.
- [x] Premise checked: `printf '%.3f' .5` under `LC_ALL=de_AT.UTF-8` reproduced locally -
      printed `0,000`, a localized "invalid number" on stderr, rc 1; with `LC_ALL=C` in front it
      printed `0.500`. The width-cap case is the queued incident (`x.zfs` shown, `x.zfs.gz` real).
- [x] RED (no skill, opus and haiku `baseline-probe`): asked directly, both named the printf
      locale cause and the `cut -c` truncation. The incidents happened in-session anyway, so the
      gap is applying a known fact at the moment of use; the rows are keyed on that moment (the
      command being built) and kept to one line each rather than explaining the mechanism.
- [x] GREEN (new rows pasted, opus and haiku quote-back): both answered from the rows with the
      fix (`LC_ALL=C printf`, print the uncut field and test against a control).
- [x] Gaps declined: haiku noted no exclude-glob syntax is given - the row is about where the
      name came from, not about rsync's glob rules.
- [x] Rows fit the existing column widths (no re-padding of the table); width and fence check
      over the added lines printed nothing.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-a302c8cd
