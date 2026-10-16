# skill-writer checklist - meta-context-watcher (2026-10-16, rules folded into the skill)

- [x] Change, one line per rule:
  - Two files / closing rule: a pass that closes several items tags each reason `measured:` or
    `argued:`.
  - Rank rule 4: several items parked behind ONE resource get a one-time durability check, recorded
    in each `open:` field.
  - What belongs / In flight: a background subagent still running at `/clear` is in flight; name
    it, its branch, and what to do with its report.
  - What belongs / How to verify: never write HEAD's sha, "tree is clean" or "CI is green on HEAD"
    as a result in a committed handover; state the property plus the command, or quote an earlier
    final sha.
  - Procedure step 2: decisions and trap notes in the outgoing handover are grepped for in code,
    tests and `OPEN-WORK.md`, and any with no other home is re-homed into the code as a WHY comment
    before the overwrite.
  - Procedure step 3: dropped "replacing any older copy"; copy only before a WHOLESALE rewrite,
    never before an in-place edit such as the STALE line, and check an existing
    `handover.prev.md` before replacing it.
  - READING section: classify EVERY open `OPEN-WORK.md` line (blocked / deferred / other-repo /
    workable) before naming the next item or claiming nothing is workable.
  - READING section: a recorded "blocked on the maintainer" PR line is a snapshot; pointer to
    `references/stale-pr-verdict.md` (previously linked from nowhere).
  - READING section: a background agent the handover names as running is LIVE; check its branch
    and origin, and wait for or message it instead of duplicating its fix.
  - Contradictions: none listed for this skill.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the
      skill through the Skill tool before its first edit
- [x] RED (text check of the artifact): before this edit the skill had no text for any of the nine
      points above. Verifier gaps, quoted: "Nothing says that committing the handover moves HEAD";
      "Step 2 only carries UNFINISHED items into OPEN-WORK.md. It does not say to grep code, tests
      and backlog for each DECISION or trap note"; "Step 3 instead says 'copy it, replacing any
      older copy'"; "SKILL.md has no link to it ('stale-pr-verdict' and 'references/' do not appear
      in SKILL.md)"; "The skill never says that a background agent running at /clear stays LIVE";
      "No instruction to list EVERY open line"; "it never asks for each closure to be tagged
      measured or argued"; "No instruction to check once that the shared resource is durable".
      A behavioural RED was replaced on purpose: these rules are in the always-loaded memory index
      of the authoring machine (inherited coverage), so a behavioural arm answers from that context
      with or without this text.
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): committed HEAD
      claim -> SKILL.md:135 "Never write HEAD's sha, "tree is clean" or "CI is green on HEAD" as a
      result"; trap-note audit -> SKILL.md:175 "Decisions and trap notes get the same audit";
      .prev copy -> SKILL.md:188 "Copy only before a WHOLESALE rewrite, never before an in-place
      edit such as the STALE line"; stale PR verdict -> SKILL.md:262 "A line saying a PR is blocked
      on the maintainer, with nothing open, is a snapshot." plus SKILL.md:264 pointer to
      references/stale-pr-verdict.md; live background agent -> SKILL.md:115-118 (In flight) and
      SKILL.md:268 "A background agent the handover names as running is LIVE."; classify every
      open line -> SKILL.md:257 "Before naming the next item, or saying nothing here can be worked,
      classify EVERY open line."; measured vs argued -> SKILL.md:57 "When you close several items
      in one pass, tag each reason `measured:` or `argued:`"; durable shared resource ->
      SKILL.md:101 "When you park several items behind ONE resource ... check once that the
      resource is durable"; contradictions: none listed; unlinked md: references/stale-pr-verdict.md
      -> SKILL.md:264
- [x] Gaps closed or declined: the "How to verify" line said "the command that checks it" without
      naming one; it now names `ci_wait.py --ref HEAD` from `bitranox:compuse-toolbox` (closed).
      "message it" for a live background agent relies on the writer naming the agent, which the
      "In flight" bullet requires (declined, covered).
- [x] Description measured: unchanged, 708 characters
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
