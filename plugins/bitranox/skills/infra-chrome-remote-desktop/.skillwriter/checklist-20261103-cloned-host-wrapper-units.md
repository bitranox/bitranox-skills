# skill-writer checklist - infra-chrome-remote-desktop (2026-11-03, cloned host: wrapper units)

Change: a new section "A cloned host: retire the inherited registration before the first start"
(archive `host#*.json` and `paired-clients`, disable every unit that can start the host found by
content, verify with `is-enabled`, register fresh after the start), a Common-mistakes row for
disabling only the per-user unit, and the "Remove them" sentence in "Verifying which PIN is
stored" now points clones at the archive instead of reading as delete.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Test approach: application scenario on a copy where only the
      per-user unit was disabled; RED on the pre-edit text, GREEN on the edited text, opus and
      haiku.
- [x] Ground truth: on a restored container copy a site unit `crd.service`
      (`Wants=chrome-remote-desktop@<user>.service`, `ExecStart=/bin/systemctl start
      chrome-remote-desktop@<user>.service`, `WantedBy=multi-user.target`) is enabled; it is not
      shipped by the chrome-remote-desktop package (`dpkg -S` finds no owner), and a grep of
      `/etc/systemd/system` and `/usr/lib/systemd/system` for `chrome-remote-desktop@` names only it.

## RED
- [x] `redcheck --corpus-cascade` named term-overlap documents only; a grep of every CLAUDE.md and
      memory fact for `crd.service` / wrapper units found only an unrelated journald fact.
- [x] RED opus: looked for other start paths by NAME (`list-unit-files 'chrome-remote-desktop*'`,
      SysV, user units), which misses a wrapper named otherwise; did not move `paired-clients`.
- [x] RED haiku: "the disable helps only for boot autostart"; checked only
      `multi-user.target.wants | grep chrome-remote`; no wrapper, no `paired-clients`.
- [x] Both RED arms flagged "moved aside" as leaving the source's `private_key` on the copy's
      disk; that fed the archive wording before GREEN.

## GREEN
- [x] Commands executed before the probes, on a fake rootfs with an enabled wrapper unit:
      `grep -rl` returned only `/etc/systemd/system/crd.service` (rc 0); `is-enabled` before the
      disable printed `enabled enabled` (rc 0); `disable` removed both `multi-user.target.wants`
      links (rc 0); `is-enabled` after printed `disabled disabled` with rc 1.
- [x] GREEN opus and haiku both: not safe yet; move `paired-clients` too; grep by content and
      disable each wrapper, quoting "Find them by content, not by name".

## REFACTOR
- [x] Every RED and GREEN dispatch asked for a `Skill gaps` section; all four lists read.
- [x] Closed: grep scope widened to `/usr/lib/systemd/system`; a verification step added
      (`is-enabled`, read the words, it exits 1 when nothing is enabled - measured above); the
      "Remove them" vs "keep the archive" contradiction GREEN opus found (now "Remove them from the
      config directory; on a clone, archive them").
- [x] Declined: `/run/systemd` (runtime only, empty in a stopped rootfs); a non-merged `/lib`
      (current Debian and Ubuntu are usr-merged); user units, cron, XDG autostart (no observed
      case; the content grep is the stated method); mask vs disable (`masked` is accepted by the
      check, choosing it is the operator's call); "leaves your control" undefined (judgement the
      skill leaves open); leftover files on a non-clone host (pre-existing guidance, outside this
      change); reading the source `host_id` from the archive (follows from step 1 "Keep the
      archive"); the window before registration (with every unit disabled nothing starts).
- [x] GREEN diffed against RED in both directions: RED's extra checks (other users, journal after
      start) are not prescribed by the new text but nothing the old text taught is lost.
- [x] Quote-back on the final text, opus (effort medium) and haiku: Q1 keep-and-archive, Q2
      is-enabled exit 1, Q3 grep directories all answered by direct quote on both tiers; no NONE.
- [x] Final re-probe found no new undecided gap.
- [x] Tiers: opus and haiku on RED, GREEN and quote-back; 6 cells.
- [x] Width and fence check over the added lines prints nothing; the paragraph after the new
      section ("Common mistakes") holds no back-reference it could re-bind.

## Quality
- [x] No session narrative or private paths; the example user is `<user>`, the rootfs `<rootfs>`.
- [x] History finder over the diff: no hit.
- [x] Address check over the added lines: no real address.
- [x] Frontmatter not touched.
