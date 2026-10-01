# skill-writer checklist - coding-python-send-mail (2026-10-01, btx_lib_mail 2.0.0 unknown keys mirror)

Source: the tool repo's python-send-mail skill as changed for btx_lib_mail 2.0.0 (`ConfMail` refuses
a key that is not a field). This mirror is regenerated from that twin; the by-convention divergences
(`name:`, the H1 echo, the repo-only self-install blockquote) are untouched, nothing else differs.

- [x] The skill says that from 2.0.0 a key that is not a `ConfMail` field is refused: one
      `pydantic.ValidationError` listing every unknown key, each entry `extra_forbidden` with the key
      as `loc` and never the value; before 2.0.0 it was silently ignored.
- [x] The skill shows a loader that maps config keys onto field names and drops only keys it knows
      are not SMTP settings, and says never to pass the rest through nor filter down to
      `model_fields`; it states the `smtp_timeout` default (30.0) and that a `credentials` pair is
      split into `smtp_username` and `smtp_password`.
- [x] The attachment `build_conf` example now says its mapping is already keyed by field names.
- [x] Inherited-context check: the lesson under test is a library behaviour change of this release,
      so no cascade file or memory fact can already teach the 2.0.0 refusal; the behavioural RED
      stands.
- [x] RED (inert probe, haiku, previous text; scenario: a TOML `[email]` section with `use_starttls`,
      `timeout`, `sender`, `recipients` on 2.0.0): the agent said `model_validate` returns a
      `ConfMail` with STARTTLS still on, quoting "An unknown key is silently IGNORED", and shipped a
      loader that passed unmapped keys through as-is.
- [x] GREEN (inert probe, haiku, new text, same scenario plus "what does 1.8.0 do"): the agent said
      the call raises `ValidationError` (`extra_forbidden`), shipped the mapping loader, and answered
      the 1.8.0 case as a silent drop with STARTTLS on and a 30.0 s timeout.
- [x] GREEN `Skill gaps` worked: one exception or several, and what to branch on, CLOSED in the text;
      the exact message text DECLINED (callers branch on `type` and `loc`, not text); the
      `smtp_use_starttls` default DECLINED (the example already states it). RED gaps: timeout
      default and the `credentials` key CLOSED; field list answered by `sorted(ConfMail.model_fields)`.
      RED results lost in GREEN: none (the rename map and the sender/recipients drop survive).
- [x] Quote-back: the closed gap answered with a direct quote of the new text.
- [x] Every new example executed against the library with output assertions (mapped values arrive,
      a misspelled key raises `extra_forbidden` naming it, the raw section is refused on four keys in
      one error, the default timeout is 30.0).
- [x] MIRRORED skill: `repo-gate.py --mirrors` reports 0 of 10 pairs drifted.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added; addresses are `example.com` only.
