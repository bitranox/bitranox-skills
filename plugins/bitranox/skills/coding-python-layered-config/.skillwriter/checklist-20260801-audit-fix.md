# skill-writer checklist - coding-python-layered-config (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled, so no finding could come from
this machine's memory store. Ships with plugin 5.125.0.

- [x] WRONG, confirmed against the live CLI 5.6.0: `env-prefix --slug my-app` fails with
      `No such option '--slug'`; the usage line is `env-prefix [OPTIONS] SLUG`, positional. The
      documented output `MY_APP___` is correct and was kept.
- [x] UNEXECUTABLE: `deploy --profile production` omits five required flags (`--source`, `--vendor`,
      `--app`, `--slug`, `--target`), read off `deploy --help`. The example now shows the whole
      invocation and says `--profile` is an option on `deploy`, not a command.
- [x] MIRRORED skill: the same fix applied to
      `libs/lib_layered_config/skills/python-layered-config`, mirror gate clean.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every finding's QUOTE was checked against the real file before acting - a reviewer's quote is
      a claim, not evidence. All quotes verified.
- [x] No finding was accepted on the reviewer's say-so where it could be executed instead.
- [x] Fix is scoped to the defect; no adjacent rewriting.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
