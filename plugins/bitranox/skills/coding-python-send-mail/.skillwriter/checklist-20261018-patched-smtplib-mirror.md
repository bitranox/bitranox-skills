# skill-writer checklist - coding-python-send-mail (2026-10-18, patched-smtplib)

- [x] Change: one paragraph after the transport testing section: a test that patches
      `smtplib.SMTP` intercepts nothing, because the library connects through its own subclass
      created at import; the symptom (`DeliveryError` "following recipients failed ... on all of
      following hosts" after one log line per host); a host that answers gets a real SMTP
      session; the fix (forward `transport` through the app's wrappers, import `Transport` from the
      package root, assert on the recording) and why `is True` proves nothing.
- [x] Every claim measured against the btx_lib_mail source (4.5.0, `_transport.py`: the session
      class subclasses `smtplib.SMTP` at import) and a probe: with `patch("smtplib.SMTP")` active and
      `smtphosts` pointing at a local listening socket, the mock reported `called == False`, the
      socket accepted a connection, and `send` raised `DeliveryError` with the quoted text.
      `Transport` is in the package's `__all__`; `send` returns `True` and raises on every failure
      (the skill's existing parameter section).
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route recorded: `redcheck --corpus-cascade` reported INHERITED COVERAGE naming the memory
      fact this change folds. Replaced by a text check: before the change the skill taught the
      transport seam but held neither the symptom nor why a patch fails (grep for
      `following recipients`, `MagicMock`, `patch("smtplib`: no hit in the testing section).
- [x] GREEN quote-back on opus and haiku, five questions (why the tests fail, whether a better
      mock fixes them, risk with a real relay, the app change, what to assert): 10 of 10 correct,
      each with a quote.
- [x] Gaps closed after GREEN: `send` returns `True` versus never asserting a bare `True` (now
      reconciled in the sentence); where `Transport` is imported from (now named). Re-tested on
      haiku for both: 2 of 2 quoted.
- [x] Gaps declined: whether mail is actually delivered (measured only up to the SMTP session, so
      the text says that and no more); why an unchanged suite went red on a schedule (dependency
      drift, owned by the floors note in Install and not this library's history); what the app's
      wrapper should return (the application's contract); threading `transport` through several
      wrapper layers (the existing sentence covers every wrapper).
- [x] GREEN diffed against RED both ways: the existing testing section is unchanged; nothing lost.
- [x] Description measured: unchanged (737 characters).
- [x] Mirror: the same hunk applied to the btx_lib_mail repo's `skills/python-send-mail/SKILL.md`;
      the paragraph is byte-identical between the two.
- [x] Security scan: prose only; no secrets, hostnames or addresses.
