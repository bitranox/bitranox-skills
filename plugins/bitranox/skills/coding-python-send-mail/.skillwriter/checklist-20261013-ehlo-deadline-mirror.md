# skill-writer checklist - coding-python-send-mail (2026-10-13, EHLO-name lookup under the delivery deadline)

The marketplace copy is brought level with its twin, `libs/btx_lib_mail/skills/python-send-mail`,
whose section "The EHLO name" now says what a delivery with `delivery_deadline` set does while the
default lookup of this host's own name is still running: it waits for it, before connecting, at
most half the time the deadline has left, then announces its connection's own address as an
address literal, and later deliveries announce the name once found. Without a deadline the lookup
is waited for.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval questions answered from the text alone, each
      answer a direct quote or the word NONE.

## RED
- [x] The previously shipped "deadline" and "EHLO name" sections, scenario: `delivery_deadline=0.5`,
      no EHLO name set, reverse DNS taking 3 s, first send of a process. "Does the first send return
      within about 0.5 s?" answered "the text does not say", quote NONE; the EHLO-name and
      second-send answers restated the once-per-process rule with no fallback and no late name.

## GREEN
- [x] The new text, the same three questions plus "without a deadline, is the lookup waited for?":
      4 of 4 answered with direct quotes of the new sentences.
- [x] Skill gaps reported by GREEN, each decided:
      - no end-to-end bound for `send()`, and when "the time left" is measured: CLOSED by the
        review round, which moved the wait before the connect; the text now says "before
        connecting".
      - several recipients or hosts, several local interfaces, a delivery starting after the wait
        was spent: DECLINED - each delivery is one connection and the rule is stated per delivery;
        "its connection's own address" names the address that connection uses.
- [x] GREEN diffed against RED in both directions: RED had no answer for the deadline question and
      the two others are still answered, now with the fallback.

## Execution
- [x] Every claim is backed by the library's tests over a real aiosmtpd server: a held lookup under
      a deadline announces the loopback literal and finishes inside the deadline; the next delivery
      announces the late name; without a deadline nothing connects until the name is known; with a
      deadline nothing connects before the wait ends; the literal is read from the socket (IPv6
      loopback included). Each test was seen failing against the code without the change.

## Mirror check
- [x] This copy and the twin are identical apart from the name field and the self-install
      blockquote (the commit gate's mirror check).

## Quality
- [x] Present tense; describes only current behaviour.
- [x] Addresses added are RFC 5737 / RFC 3849 documentation values (`192.0.2.7`, `2001:db8::7`).
