# skill-writer checklist - coding-python-send-mail (2026-10-02, ASCII-digit port, latest-version-only text)

Source: the tool repo's python-send-mail skill as changed for btx_lib_mail 3.1.0 (`validate_smtp_host`,
and so `ConfMail.smtphosts`, refuses a port that is not plain ASCII digits). This mirror carries the
same one-sentence change; the by-convention divergences (`name:`, the H1 echo, the repo-only
self-install blockquote) are untouched, nothing else differs.

- [x] The malformed-host list says a port that is not plain ASCII digits (`:58o7`, `:+25`, `:2_5`) is
      refused.
- [x] The skill describes the latest version only: every version-history sentence ("From 2.0.0",
      "Before 2.0.0", "From 3.0.0", "Before 3.0.0", "Available from 1.8.0", "before 1.8.0 it was
      looked up again") is rewritten in present tense. Text check of the artifact: a grep for
      `X.Y.Z`, `before N`, `from N`, `since N`, `previously`, `no longer`, `used to`, `legacy`
      returned 8 history hits before and 0 after (one remaining match is the RFC 5737 address
      `192.0.2.7`).
- [x] Inherited-context check: the lesson under test is a library behaviour change of this release,
      so no cascade file or memory fact can already teach it; the behavioural RED stands.
- [x] RED (inert probe, haiku, previous text; question: does `ConfMail(smtphosts=["smtp.example.com:+25"])`
      raise on 3.1.0, and on 3.0.1?): UNKNOWN for both, quote NONE; its gaps named that signed ports
      are not covered and that `58o7` is the only rejected-port example.
- [x] GREEN (inert probe, haiku, present-tense text): `:+25` RAISES at construction, `:0025` is
      accepted, `ConfMail(timeout=5)` raises `ValidationError` (`extra_forbidden`), the EHLO reverse
      DNS runs once per process - each with a direct quote. Gaps DECLINED: leading zeros and `0000`
      are already decided by "not plain ASCII digits" and "outside 1-65535"; exact message text is
      not a contract (branch on `type` and `loc`). RED gaps (signed ports undocumented, `58o7` the
      only example) CLOSED by the new list. RED results lost in GREEN: none.
- [x] Quote-back satisfied: every GREEN answer quotes the governing text.
- [x] The claim executed against the library: `+25`, `2_5` and Arabic-Indic `25` each raise
      `ValidationError` with `loc` `("smtphosts",)` and the host not repeated; `0025` is accepted.
- [x] MIRRORED skill: `repo-gate.py --mirror-of` reports the pair in sync.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added; addresses are `example.com` only.
