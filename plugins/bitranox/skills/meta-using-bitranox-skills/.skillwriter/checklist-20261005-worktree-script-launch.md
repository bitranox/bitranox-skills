# skill-writer checklist - meta-using-bitranox-skills (2026-10-05, worktree script launch, contrib C11)

New section: in a worktree-isolated session, Claude Code's own isolation guard (not a bitranox
hook) refuses compound Bash forms launching a script; launch with `python3 <script>` instead.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Test approach: application - one question answered with a direct
      quote or NONE.
- [x] RED (pre-change text, pasted): "In a worktree-isolated session, `bash
      <plugin>/hooks/run-python.sh <script>` is refused - what should be run instead?" - NONE;
      the file has no section about worktree isolation or script launch forms.
- [x] Reproduced this session: the harness's worktree-isolation guard refused a multi-command
      Bash call in this very worktree with the message "too complex to verify that it stays
      inside the worktree"; a plain `python3 <script>` form and single `git -C <path> <verb>`
      commands ran without being refused, matching the contrib finding verbatim.
- [x] GREEN (new section pasted): same question now answers with a direct quote ("Launch the
      script directly instead: `python3 <script>` runs fine there").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
