# skill-writer checklist - compuse-ssh (2026-10-05, accept-new replaces no, D-1/D-11)

Replaced the "StrictHostKeyChecking no logs in and runs the command on a changed key" paragraph
with the accept-new paragraph (text supplied verbatim by D-1's reply for the fleet_ssh change):
accept-new REFUSES a changed/revoked key before the command runs; key the self-heal on ssh's own
messages (`-E <logfile>`), never on relayed remote stderr.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "Under the fleet config in this skill, does a changed host
      key stop the command from running?" - direct quote of the OLD paragraph: "logs in with the
      key and RUNS the command" (answer: no, it does not stop it).
- [x] GREEN (new text pasted): same question now answers with a direct quote of the NEW
      paragraph: "accept-new... REFUSES a changed or revoked key before anything runs... command
      not run" (answer: yes, it does stop it) - a reversed, correctly-sourced answer, not a
      vanished one.
- [x] Text matches the owning fixer's exact wording (D-1-reply.json, "D-11 ...compuse-ssh...
      lines 74-83"); not independently re-measured against OpenSSH 10.2 in this worktree, since
      the wording and the version claim were supplied by the group that implemented
      `fleet_ssh.py --trust-changing-host-keys`.
- [x] GREEN diffed against RED in both directions: nothing removed, the paragraph fully replaced
      per the dispatch instruction (scope limited to that one paragraph; the earlier setup
      example further up the file was left untouched, out of this group's scope).
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
