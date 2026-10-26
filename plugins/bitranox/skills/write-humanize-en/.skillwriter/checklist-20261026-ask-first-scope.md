# skill-writer checklist - write-humanize-en (2026-10-26, ask-first scope)

- [x] Change: the scope guard's unconditional "always ask the user first" becomes a "When to ask
      first" rule. Text the user wrote stays theirs: shown for an opinion or review, give what they
      asked for, then ask before changing it; asked only to send it, send it as written. Outgoing
      prose the agent wrote at the user's request, or a request for the humanizing itself, is
      humanized without asking; a standing humanize-before-sending rule counts as that request for
      the agent's own text only. The in-scope list names PR descriptions and comments and issue
      replies. The write-humanize-de twin carries the same rule in German.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, 4 cells (opus + haiku x 2 scenarios), pre-edit guard pasted:
      - Agent-written PR thank-you the user asked for: opus A, haiku A (asks "Should I humanize
        this text?" and waits), both quoting "When this skill is triggered, **always ask the user
        first**". Both Skill-gaps sections name the conflict with a standing humanize-outgoing-prose
        rule and say PR comments are not in the scope list.
      - Control, user's own blog intro shown for an opinion: opus A, haiku A (opinion, then ask).
- [x] redcheck --corpus-cascade reported INHERITED COVERAGE (STRONG) on the tree-top
      CLAUDE.local.md (shared terms: asking, contributor, humanize, pull, yourself). Adjudicated as
      term overlap, not the lesson: that file says to humanize outgoing prose, never to skip the
      question, and the behavioural RED failed on both tiers with it loaded. Behavioural arms kept.
- [x] GREEN, 5 cells on the edited text (told the pasted text is the skill under test):
      agent-written PR comment opus B, haiku B (humanize, post, no question); user-written email
      "send this to Bob" with a standing humanize rule opus B, haiku B (user's words not rewritten);
      opinion control haiku A.
- [x] Skill gaps requested from every RED, GREEN and REFACTOR dispatch; closed in the text:
      heading read as describing the agent's own text (renamed "When to ask first"); send request
      order (ask-then-send vs send-then-ask split the tiers: now "When they only ask you to send it,
      send it as written"); "that request" could cover user text (now "for text you wrote, never
      for text the user wrote"); PR comments missing from the scope list (added).
- [x] Declined gaps, with reason: mixed requests ("send it, looks ok?", "what do you think, and
      send it") and partial yes ("only fix the dashes") - judgement left to the agent; whether to
      show the humanized text before posting - governed by the user's posting authorization, not
      this skill; how much rewriting is allowed - covered by "Preserve meaning - Keep the core
      message intact" under "Your Task"; what to do on yes - covered by "## Output Format";
      user-pasted text that may be AI-drafted - out of scope, authorship as stated by the user
      decides; mentioning tells after sending - judgement.
- [x] REFACTOR re-run on the final text, 3 cells: user email opus C, haiku C, each quoting "When
      they only ask you to send it, send it as written."; haiku combined author + opinion: B
      quoting "Do **NOT** ask when YOU wrote the outgoing prose the user asked for ..." and A
      quoting "When they show it to you for another purpose (an opinion, a review), give what they
      asked for, then ask ...". No new undecided gap.
- [x] GREEN diffed against RED both ways: the control behaviour (opinion, then ask) is kept on both
      tiers; nothing the baseline produced is lost.
- [x] Tiers and cells: opus and haiku, 4 RED + 5 GREEN + 3 REFACTOR = 12 cells, plus 1 haiku cell
      (3 situations) on the German twin.
- [x] Frontmatter description unchanged (497 chars); trigger map needs no rebuild
- [x] Latest-release finder over the added lines: no hits. No typographic tells in the added lines.
- [x] No addresses, hostnames or paths added. Security scan: prose edit only, no secrets or PII.

- [x] Partly superseded the same day by checklist-20261026-user-text-standing-rule.md: a
      standing humanize rule now covers user-written text sent at their request, so the GREEN
      cell "user-written email ... (user's words not rewritten)" describes the earlier rule.
