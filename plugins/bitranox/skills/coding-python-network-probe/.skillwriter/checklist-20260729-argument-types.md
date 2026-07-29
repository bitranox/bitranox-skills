# skill-writer checklist - coding-python-network-probe (2026-07-29, argument types)

Change: name `AddressFamily` and `IPScoutError` in the error-contract section. Shipped in 5.101.3.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, from a release documentation audit run against the live code: the skill named every
      command and every callable but not two names a caller has to TYPE - `AddressFamily`, which
      the `family=` argument takes, and `IPScoutError`, the base its own error-contract section
      tells the reader to catch while listing only the three subclasses.
- [x] Both are exactly the case the sharpened coverage rule (5.101.3) is built to catch: not
      exported surface in general, but a name the user must write. An agent told to catch
      `IPScoutError` and never shown it is being asked to guess.
- [x] GREEN: 18/18 commands, 30/30 callables, and both argument/exception types now named,
      verified by script against the live `--help` output and `__all__`.
- [x] Placed in the error-contract section rather than the quick reference, because that is where
      a reader meets both: the family argument and the exception hierarchy are contract, not a
      call to be looked up.
- [x] Scope: shared/general. Security scan: one sentence, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description unchanged; token budget one sentence.
- [x] Kept in step with the copy in the ipscout repo.
