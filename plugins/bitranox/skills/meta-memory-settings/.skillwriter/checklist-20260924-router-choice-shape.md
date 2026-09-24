# skill-writer checklist - meta-memory-settings (2026-09-24, router choice shape)

One cell corrected: the `classifier_skill_router` row's SENT statement. The hook now asks one
choice over the session's installed skills with a new-task question and context fields; the cell
said one yes/no question per shipped skill over the prompt alone.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario: what leaves the machine besides the
      prompt, which skills are asked about, and how many skill questions Jev gets per prompt.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe`
      type, the table rows pasted and Skill invocation forbidden, so neither arm could answer from
      the installed copy (which still carries the pre-change cell).
- [x] RED (pre-change cell): (1) NONE, (2) UNKNOWN - "does not specify the scope of shipped
      skills", (3) "one question per shipped skill". All three wrong against the code.
- [x] GREEN (new cell): all three answered with a direct quote - the context fields, "the skills
      installed in the session (this plugin's own when that list cannot be read)", and "ONE
      choice".
- [x] Both dispatches asked for a `Skill gaps` section. GREEN reported two: what the new-task
      question asks (CLOSED - now "one question whether the prompt starts a new task"), and what
      makes the installed list unreadable (DECLINED - a mechanism detail of `skill_roster.py`,
      not a settings consequence). Nothing RED produced is missing from GREEN.
- [x] The statement matches the code: `skill-router._router_fields` (prompt or notification
      fields, `project`, `recent_activity`, `skills_already_used`, `previous_assistant_message`),
      `classifier.skill_router_choice_questions` (the gate noul plus one `choice`),
      `skill_roster.installed_skills` (transcript listing, else per-project cache, else this
      plugin's skills dir), redaction and caps in `classifier.prepare_state`.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
