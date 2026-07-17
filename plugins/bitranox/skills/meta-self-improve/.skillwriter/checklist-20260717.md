# skill-writer checklist - meta-self-improve (2026-07-17, hook script references state their home and launch)

Change: self_improve_signals.py / self-improve-audit.py were cited bare, with no home path or run-python.sh
launch - inconsistent with this same file's correct memory_engine.py pattern, and against the rule
meta-skill-writer teaches (a bare filename reads as NOT SHIPPED to an auditor).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: grepped the file: memory_engine.py is cited with `<plugin>/hooks/run-python.sh` while the signal
      scripts are bare - the same file uses both conventions
- [x] GREEN: each mention now names `<plugin>/hooks/` and the run-python.sh launch
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
