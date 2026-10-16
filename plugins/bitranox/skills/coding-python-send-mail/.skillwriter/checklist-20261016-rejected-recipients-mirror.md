# skill-writer checklist - coding-python-send-mail (2026-10-16, DeliveryError.rejected_recipients)

The marketplace copy is brought level with its twin, `libs/btx_lib_mail/skills/python-send-mail`,
which documents the new `DeliveryError.rejected_recipients` of btx_lib_mail 4.4.0: the failed
recipients every host refused permanently, which a caller drops instead of retrying.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval questions answered from the text alone, each
      answer a direct quote or the word NONE, by a text-only probe agent (no file tools).
- [x] Ordering: the new text was drafted before the RED run. RED was run against the published,
      pre-change text, so it still measures the old behaviour.

## Contamination
- [x] `redcheck --corpus-cascade` reported "inherited" on shared vocabulary (btx_lib_mail,
      DeliveryError). The new field name occurs nowhere in the inherited cascade or the memory facts
      (searched; the new SKILL.md, as positive control, contains it), so the behavioural RED can fail.

## RED
- [x] Pre-change errors section, scenario: one recipient refused with 550 by every host, another
      failed because no host was reachable; "which attribute names the recipients that will never
      succeed?" Answer: NONE; the agent would retry `failed_recipients` whole, the 550 address
      included.

## GREEN
- [x] New text, same question: answered with a direct quote of the DeliveryError row naming
      `rejected_recipients`, and code that drops those and retries the rest.
- [x] Gaps reported by GREEN, each decided:
      - a 4xx reply, a host that disagrees (550 on one, timeout on another), subset of
        `failed_recipients`: CLOSED by a sentence after the table; re-asked, all three answered by
        direct quote.
      - "a host never tried": DECLINED - delivery tries every configured host for each recipient
        until one accepts, so a failed recipient was tried on all of them.
      - SMTPUTF8 counted as a rejection though it is not a 5xx: DECLINED - the body names it
        explicitly; a relay without SMTPUTF8 refuses that message for good, which is what
        "refused permanently" means in the row.
- [x] GREEN diffed against RED in both directions: RED's only answer (retry everything failed) is
      still available, now narrowed to the recipients worth retrying.

## Execution
- [x] Every claim is backed by btx_lib_mail tests through a per-host transport double: 550 and 554
      on every host are rejected; 451 on every host, 550 plus a timeout, a refused sender, and no
      host reachable are failed but not rejected. Each test was seen failing against mutated code
      (classifier always true, always false, and 4xx counted as permanent).

## Mirror check
- [x] This copy and the twin are identical apart from the name field and the self-install
      blockquote (the commit gate's mirror check).

## Quality
- [x] Present tense; describes only current behaviour.
- [x] No addresses beyond `example.com` documentation values.
