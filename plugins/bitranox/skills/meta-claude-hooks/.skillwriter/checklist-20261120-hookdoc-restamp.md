# checklist - re-stamp after upstream hooks.md added two H4 sections and an output value

`hookdoc_stamp check` reported STRUCTURAL: added H4 "Get terminal notifications inside tmux or GNU
screen", H4 "Limit HTTP hooks", output field `all`. Read both upstream sections and updated the
references: configuration.md says where the two HTTP allowlists are set (managed settings for
hooks the organization deploys, any settings file for other hooks; the old text said they apply
to every source), io-contract.md says what terminalSequence needs inside tmux (allow-passthrough
`on`, or `all` on 3.4+) and GNU screen (the window must be showing). Then `stamp --write` and
`baseline --write`.

Decisions: none - references synced to upstream; no rule of the skill changed

## RED

- [x] `check` STRUCTURAL with the three names above; `allow-passthrough` had 0 hits in references/.

## GREEN

- [x] `coverage` complete (33 events, 86 required names), `selftest` 3 of 3, `check` CURRENT,
      125 tests pass.
- [x] Quote-back probe (haiku): tmux fix, `all` and its version, screen behaviour and the managed
      settings answer all quoted.
- [x] Not reviewed line by line: 50 upstream sections changed wording since the 2026-11-08 stamp
      (COSMETIC by the tool's own test); listed in the delivery report.

## REFACTOR

- [x] ASCII check on the added text clean.
