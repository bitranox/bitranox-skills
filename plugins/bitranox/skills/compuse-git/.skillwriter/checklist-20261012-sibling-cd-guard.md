# checklist-20261012 - writing calls in one message inherit a sibling's `cd`

## What the change is

One row, "A bare `git` after an earlier `cd`": it now says that a WRITING call in a message starts
where the previous call left the shell (read-only calls run side by side and do not), and it names
the new `block-write-after-sibling-cd` guard for that same-message shape. Its old "No hook catches
this" became false with the guard, so the sentence is narrowed to the cross-message shape, which
stays unguarded.

## Ground truth behind the new sentences

- [x] Two parallel read-only probe calls in one message overlapped (started 2 ms apart, both ran
      3 s); a `cd` in one did not change the other's directory, with or without its own leading
      `cd`. A second call that wrote a file and had no `cd` ran in the first call's directory.
- [x] Both recorded wrong-repo incidents read from their transcripts: the misdirected call had NO
      `cd` and finished about 0.3 s after its writing sibling, in the sibling's directory.
- [x] The guard's rate is from a replay of 131,293 recorded Bash calls (33 refusals, 5 of them real
      wrong-repo writes); the row cites no figure for it.

## RED (pre-change row, haiku, `baseline-probe`, quote-back)

Scenario: one message, call 1 `cd /work/planning && git commit ...`, call 2 a bare `git commit`.

- [x] Q2 (does write vs read matter): "NONE. The row describes a bare git answering from the wrong
      repo, and it makes no claim that commits behave differently from status reads."
- [x] Q3 (will a hook refuse call 2): "No hook will refuse call 2", quoting "No hook catches this"
      - true before the guard, false after it, which is the defect the edit closes.
- [x] Skill gaps: "The text does not say how two parallel Bash calls in one message are ordered
      relative to each other's cd"; "The text does not separate read commands from write commands".
- [x] Inherited-context route: the answers are checked as QUOTES of the supplied row text, so a
      model's own knowledge cannot satisfy them; no behavioural arm was used.

## GREEN (new row, haiku, `baseline-probe`, same scenario plus a cross-message question)

- [x] Q2: quotes "a call that WRITES (commit, push, `make test`) runs after the call before it has
      finished" and "read-only calls run side by side and do not see each other's `cd`".
- [x] Q3: quotes "`block-write-after-sibling-cd` refuses the same-message shape ...".
- [x] Q5 (cd in an EARLIER message): "No hook refuses it", quoting "Nothing refuses the
      cross-message shape".
- [x] Q4 kept RED's correct answer (`git -C <repo>`); nothing RED got right was lost.

## Gaps GREEN reported, decided

- [x] The refusal's exit code and wording: declined - the hook's own message carries them, and the
      row's job is when the shape bites.
- [x] Whether a write waits for an earlier read-only call: declined - not measured, so the row
      makes no claim either way.
- [x] git-wrong-repo-nudge firing on the cross-message case: declined - the row names it only as the
      reason no refusal exists there; its own docstring owns its behaviour.

## Quality checks

- [x] Description and name unchanged; no trigger moved.
- [x] No private paths, hosts or addresses added (scenario paths are generic `/work/...`).
- [x] The guard it names ships in this same change, with tests and a registration in hooks.json.
