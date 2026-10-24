# skill-writer checklist - coding-python-send-mail (2026-10-24, smtp-credentials)

- [x] Change: the transport testing section replaces the bare `DeliveryOptions` field list with a
      table of each field's type and default; says `credentials` is `SmtpCredentials | None`, read
      by name (`.username`, `.password`, both `str`); names the `SmtpCredentials(username,
      password)` constructor; shows a `DeliveryOptions` built with keywords, the first four
      required; and lists the tuple forms that still expose the password (indexing, unpacking,
      `"%s %s" % creds`, `*creds`, `tuple()`, `_asdict()`). The Reference list names
      `SmtpCredentials`.
- [x] Every claim executed against btx_lib_mail 4.6.0: `dataclasses.fields(DeliveryOptions)` gives
      the table's types and required/default split; the shown constructor call runs; omitting
      `starttls_verify` raises `TypeError`; the instance is frozen; `repr`, `str` and an f-string of
      both types hide the password, while `%`-spread, `*`-spread, indexing, `_asdict()` and
      `tuple()` contain it.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: behavioural. `SmtpCredentials` is a new public name in 4.6.0, so no cascade or
      memory text can teach it. RED on opus and haiku with the pre-change section and an
      application task (a custom `Transport` recording the user name, and a test building
      `DeliveryOptions` directly): opus built `credentials=("mailer", "pw")` and unpacked it by
      position (the form 4.6.0 refuses); haiku invented `Credentials(user=..., ...)` and read
      `credentials.user`. Both quoted NONE for the credentials type.
- [x] GREEN on opus and haiku with the edited section pasted: both used `SmtpCredentials`, read
      `.username` and `.password` by name and passed the four required fields, quoting the table
      row for every type.
- [x] Gaps closed after GREEN and re-probed on the final text: whether "plain str" covered
      `.username` (cell now types both fields); the constructor's parameter names and keyword form
      (named); whether `str()`/f-strings are safe (stated); the tuple forms that leak (listed, after
      an opus quote-back showed "never log it" and "str() hides it" read two ways). Final opus
      quote-back judged five logging calls SAFE or LEAKS correctly, each with a quote; final haiku
      re-probe built the credentials with keywords, each value quoted.
- [x] Gaps declined: the `Transport` import path and the `deliver` parameter types (stated in the
      skill's example code and patched-smtplib paragraph, outside the probed excerpt); what an empty
      password means and how a transport fails a host (caller policy, not this change); a handler
      that serialises `record.args` (covered by "log `.username`, never the tuple's contents");
      pickling, `vars()`, tracebacks (out of scope); a project file loaded at the probe's session
      start that predated the change (stale context, not the skill).
- [x] GREEN diffed against RED both ways: the recording-transport example and every other
      paragraph of the section are unchanged; nothing lost.
- [x] Description measured: unchanged.
- [x] Latest-release finder over the skill: no hits. Addresses in the skill are RFC 5737 / 3849
      documentation values.
- [x] Mirror: regenerated from btx_lib_mail's `skills/python-send-mail/SKILL.md`; the two differ
      only in the `name:` line and the self-install blockquote.
- [x] Security scan: prose and a dummy password only; no secrets, hostnames or addresses.
