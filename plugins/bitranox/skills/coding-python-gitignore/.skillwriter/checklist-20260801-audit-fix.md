# skill-writer checklist - coding-python-gitignore (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled, so no finding could come from
this machine's memory store. Ships with plugin 5.125.0.

- [x] UNEXECUTABLE x2, both confirmed by running them: `igittigitt config-deploy` exits 2 with
      "Missing option '--target'", and `config-generate-examples` exits 2 with "Missing option
      '--destination'". Both were shown as bare runnable commands. Now carry their required option.
- [x] MIRRORED skill: the same fix applied to `libs/igittigitt/skills/python-gitignore`, and the
      mirror gate re-run clean.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every finding's QUOTE was checked against the real file before acting - a reviewer's quote is
      a claim, not evidence. All quotes verified.
- [x] No finding was accepted on the reviewer's say-so where it could be executed instead.
- [x] Fix is scoped to the defect; no adjacent rewriting.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
