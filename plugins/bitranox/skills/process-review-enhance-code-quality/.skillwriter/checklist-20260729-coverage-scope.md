# skill-writer checklist - process-review-enhance-code-quality (2026-07-29, coverage scope)

Change: the shipped-skill coverage rule said "every public name from `__all__`". It now names three
sets - CLI subcommands, public callables, and the types a caller must WRITE (argument enums and
caught exceptions) - and says explicitly that payload/result types are out. Shipped in 5.101.3.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, found by applying the rule to its own first subject during a release documentation
      audit: ipscout's skill scores 30/30 on callables but 39/55 on `__all__`, because it does not
      name ResponseObject, TraceHop, ReverseDnsReport and thirteen other payload types. Read
      literally, the rule I shipped fails the artifact I ship.
- [x] Fixed the rule rather than the artifact, because the artifact was right: a caller reads
      `result.reached` without ever typing `ResponseObject`. Demanding every export would turn a
      usage skill into a second API reference, and the second one is the one nobody updates.
- [x] The line drawn is behavioural - "would the user have to type this name" - which keeps the
      genuinely missing cases in scope. Applying it immediately found two real gaps in that same
      skill: `AddressFamily`, which the `family=` argument takes, and `IPScoutError`, the base the
      error contract tells readers to catch. Both added.
- [x] Verified after: 18/18 commands, 30/30 callables, and both argument/exception types named.
- [x] Scope: shared/general. Security scan: prose only, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description unchanged; token budget one paragraph replacing a sentence.
