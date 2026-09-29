# skill-writer checklist - coding-python-send-mail (2026-09-29, btx_lib_mail 1.8.0 EHLO name mirror)

Source: the tool repo's python-send-mail skill as changed for btx_lib_mail 1.8.0. This mirror is
regenerated from that twin by applying the same three hunks; the by-convention divergences
(`name:`, the H1 echo, the repo-only self-install blockquote) are untouched, nothing else differs.

- [x] The skill teaches the EHLO name: `send(local_hostname=...)`, else
      `ConfMail.smtp_local_hostname` (on `conf` or `config=`); on the CLI `--local-hostname`, else
      `BTX_MAIL_SMTP_LOCAL_HOSTNAME`; available from 1.8.0; unset, the reverse-DNS name looked up
      once per process (per connection before 1.8.0); refused before a connection opens when it is
      not non-empty printable ASCII without spaces.
- [x] The skill says every recipient gets its own message over its own connection, even from one
      `send()` call with a list.
- [x] The skill says `ConfMail` field names carry an `smtp_` prefix where `send()` keywords do not,
      and that an unknown `ConfMail` key is silently ignored (verified: `ConfMail(use_starttls=False)`
      leaves `smtp_use_starttls` True).
- [x] Inherited-context check: `redcheck --corpus-cascade` reported STRONG overlap, adjudicated as
      vocabulary only - no cascade file or memory fact body contains `local_hostname`, `getfqdn`,
      `EHLO` or `HELO` - so the behavioural RED stands.
- [x] RED (inert probe, previous text; scenario: 35 s before the first byte, relay rejects
      "HELO/EHLO argument invalid"): the agent concluded the library has "no supported way" to set
      the EHLO name, proposed renaming the container, and batched recipients believing one `send()`
      is one connection.
- [x] GREEN (inert probe, new text, same scenario): the agent set `smtp_local_hostname` and did not
      rename the host.
- [x] GREEN `Skill gaps` worked: `use_starttls` passed to `ConfMail` and "every alert slow versus a
      once-per-process lookup" CLOSED in the text; the CLI falling back to
      `conf.smtp_local_hostname` DECLINED (a CLI process only sees the default `conf`, where it is
      None); the deployed-version precondition DECLINED (the text states "from 1.8.0"). RED results
      lost in GREEN: none.
- [x] Quote-back: both closed gaps answered with a direct quote of the new text.
- [x] Every new example executed against the library with output assertions (the config value and a
      `send()` keyword reach `DeliveryOptions.local_hostname`; a bad name raises `ValidationError`
      on `ConfMail` and `ValueError` from `send()`).
- [x] MIRRORED skill: `repo-gate.py --mirror-of` the tool repo reports in sync.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added; the only address is RFC 5737 documentation
      space.
