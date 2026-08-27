# checklist-20260827 - the TCP-check adapter's example is command-injectable

## What the change is

The skill's TCP-check adapter, in both `SKILL.md` and `canonical-example.md`, built its probe by
interpolating a caller-supplied host into a double-quoted `bash -c` body. `bash -c` re-parses that
body as code, so a host value from a config file executes. The domain layer validated the port
numerically and the host only for non-emptiness, so a hostile host passed validation and reached the
shell.

Both layers change: the domain gains a hostname character rule, and the adapter passes host and port
as positional arguments into a single-quoted body.

## RED

- [x] The defect is present in the shipped text. `SKILL.md:180` and `canonical-example.md:182` both
      read `bash -c "echo >/dev/tcp/$host/$port"`, host interpolated into a re-parsed body.
- [x] The defect is reachable through the skill's own domain layer.
      `domain__validate_service_def` checks the host with `[[ -n "$host" ]]` only, so the config
      line `web:a;id;x:443` validates and reaches the adapter.
- [x] The injection executes. With `host='a;touch $D/PWNED;x'`, the pre-change form creates the
      file: `INJECTION EXECUTED`. This is the failing test.
- [x] Behavioural arm run and it did NOT flip: a subagent asked to write the two functions while
      following this skill produced the positional-argument form instead of copying the example.
      Recorded rather than escalated. Its own gaps list confirms the defect from the other side:
      "The skill's own adapter example is injectable ... The skill text does not itself flag or fix
      this in its own example."
- [x] Because the behavioural arm cannot flip, the evidence is the artifact check plus the
      mechanical proof above, per "make the coverage check against the skill FILE the evidence".

## GREEN

- [x] Same hostile input against the post-change form: `no injection`; the file is not created.
- [x] The happy path survives: `bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ github.com 443` connects.
- [x] The new domain rule accepts `example.com` and `db.internal.example`, and rejects
      `a;echo INJECTED;x` and `-leading-dash`.
- [x] Both files carry the fix; neither is left as a copyable vulnerable example.
- [x] Each fixed site states WHY in a comment, so the next editor does not revert it to the
      shorter interpolated form.

## REFACTOR

- [x] Gaps from the behavioural run reviewed. Closed: the injection itself, and the host-validation
      gap in the domain layer.
- [x] Declined, with reasons: IPv6 hosts in a colon-delimited `name:host:port` format (a format
      question this skill does not own, and the example is explicitly hostname/IPv4);
      which layer owns timing (a judgement the skill should leave open); the default timeout value
      (illustrative, and already exposed as a parameter in the canonical example).
- [x] Declined as not a defect: a report that the inline examples contain literal placeholder words
      (`local port="the"`) where positional parameters belong. Checked against both the repo copy
      and the installed copy, which are byte-identical: the string does not occur, and no verbatim
      quote accompanied the claim.
- [x] No result lost against the baseline: the pre-change arm produced no finding this change
      removes.

## Quality

- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] Values added are reserved documentation names (`example.com`, `db.internal.example`).
- [x] `name` and `description` unchanged; no routing keyword moved.
- [x] Change is confined to the two code examples and their comments.
