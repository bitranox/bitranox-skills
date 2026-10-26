# skill-writer checklist - write-humanize-en (2026-10-26, user text under a standing rule)

- [x] Change: a standing rule to humanize outgoing prose before sending covers text the USER wrote
      and asks you to send (post, comment, email), not only the agent's own; it fixes mistakes
      and AI tells and keeps their meaning, facts and voice. Only an explicit opt-out for that
      message sends it as written: a request not to change the wording ("send it unchanged",
      "as is", "verbatim", "don't touch it") or a "no" to the review question. "Post this" or
      "post/send exactly this" only names the text, and an unsure phrase is no opt-out. Without a
      standing rule, user text is still sent as written; text shown for an opinion still gets the
      question first. Replaces "When they only ask you to send it, send it as written" and "...
      counts as that request for text you wrote, never for text the user wrote". The
      write-humanize-de twin carries the same rule in German.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, 2 cells (opus + haiku), pre-edit guard pasted, standing rule in context, scenarios
      A user text to post / B user draft for a tone opinion / C send without a rule / D agent-
      written comment: both tiers A = send as written, quoting "When they only ask you to send it,
      send it as written." and "never for text the user wrote". B, C, D as intended on both.
- [x] redcheck not run as a gate for the RED: the behavioural arms failed on both tiers with the
      machine's cascade loaded, so inherited context did not supply the new rule.
- [x] GREEN, 3 cells on the edited text (told the pasted text is the skill under test): opus EN,
      haiku EN, haiku DE, scenarios A-D plus E (standing rule, "don't touch it"): all five as
      intended on every cell - A humanize then post, B answer then ask, C send as written, D
      humanize then post, E post unchanged.
- [x] Skill gaps requested from every RED, GREEN and REFACTOR dispatch; closed in the text:
      whether posting or emailing counts as sending (now "(post it, comment it, email it)");
      unclear antecedent of "Do NOT ask then" (now "when that rule applies"); "exactly as it
      covers yours" collided with "send exactly this" (now "just as"); whether a "no" to the
      review question opts out (now listed); open opt-out list - the tiers split on "post exactly
      this" (opus opt-out, haiku not), so the text now defines the opt-out as a request not to
      change the wording, says "post/send exactly this" only names the text, and makes an unsure
      phrase no opt-out.
- [x] Declined gaps, with reason: where a standing rule lives and which channels it names - the
      rule's own text decides, not this skill; mistake versus voice ("thx", "lgtm") - covered by
      "Preserve meaning" and "Maintain voice" under "Your Task", judgement beyond that; whether
      to show or report the humanized text before or after posting - governed by the user's
      posting authorization, not this skill; how to send (gh, mail tool, address) - out of scope;
      a factual error in the user's text - "keep their ... facts" covers it; mixed show-and-send
      requests and forwarded third-party text - judgement, authorship as stated by the user
      decides; language choice for mixed-language text - the two skills' descriptions decide.
- [x] REFACTOR re-runs on the final text, 5 cells: opus (medium effort, quote-back) and haiku on
      user text to post / "no" then "post it" / "post exactly this" / no rule - both tiers
      humanize, post unchanged after the "no", send as written without a rule; they split on
      "post exactly this", closed as above. Opus and haiku on "post exactly this" / "verbatim" /
      "like that" / "post this" after the opt-out fix: both tiers humanize, post unchanged,
      humanize, humanize, each quoting the opt-out sentences. Final haiku quote-back on the
      unsure-phrase tie-break: "like that", "this exact text" and "post this" humanize, "word for
      word" posts unchanged as a request not to change the wording; no new undecided gap.
- [x] GREEN diffed against RED both ways: B (answer, then ask), C (no rule: send as written) and D
      (agent-written: humanize without asking) are kept on every tier; A flipped from send as
      written to humanize then post, which is the change.
- [x] Tiers and cells: opus and haiku, 2 RED + 3 GREEN + 5 REFACTOR = 10 cells (1 of them on the
      German twin).
- [x] Frontmatter description unchanged; trigger map needs no rebuild.
- [x] Latest-release finder over the added lines: no hits. No typographic tells in the added
      lines.
- [x] No addresses, hostnames or paths added. Security scan: prose edit only, no secrets or PII.
