# skill-writer checklist - compuse-toolbox (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: `procsig.py`'s docstring claimed it "never puts the match string on a command line
      another pgrep could see". Its own argv carries the needle like any other command, so a third
      party's broad sweep can match procsig itself. Rewritten to state the guarantee that IS true
      and is one-directional: procsig will not kill you, and cannot stop someone else's sweep from
      killing procsig.
- [x] WRONG: the skill advertised handling an "IPv6-first" edge case. Grep confirms none of the six
      tools touches networking at all. Claim removed rather than reworded.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
