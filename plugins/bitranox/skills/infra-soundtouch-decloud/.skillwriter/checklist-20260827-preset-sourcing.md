# skill-writer checklist - infra-soundtouch-decloud (preset sourcing, and measuring before automating)

Two changes to a shipped skill. The skill gains the step it never had - where a station's stream URL
comes from, and proving it plays before it reaches a button - and its preset-repair guidance is
corrected against 18.7 days of measurement. Scripts and tests grow to match.

## PLAN

- [x] Change type: a factual correction plus a new capability. The correction's failure mode is a
      FALSE STATEMENT, so its instrument is ground truth; the new capability is technique, so its
      instrument is an application scenario.
- [x] Scope unchanged: SKILL.md as an index, five reference files, `scripts/` and `tests/`.
- [x] Ground truth chosen up front: the retired restore timer's own journal, and a real
      pre-shutdown preset backup fetched from a live installation rather than a retyped sample.

## RED

Four baseline runs against the shipped text. Two passed, two failed, and the two that passed are
recorded as what they are rather than counted as evidence.

- [x] VOID, telegraphed: an owner scenario that states the presets survived a power cut, asks
      whether to automate. The scenario contains its own answer, so the pass proves nothing about
      compliance. Its gaps list is kept because it is not affected by the telegraphing: it reports
      that the measured boot trace "never says what did the rewriting there, whether that's the
      manual/scripted restore being demonstrated, or the speaker or service quietly self-healing",
      and that a read-only monitoring job is "never as its own recurring job with a recommended
      interval, logging, or alerting".
- [x] PASSED honestly: asked whether a rebooted speaker's blank buttons mean the service copy is
      also gone, an agent answered correctly and separated migration from reboot without help. The
      claim that the SKILL.md mistakes row is REFUTED by `presets.md` does not hold - they describe
      two different events - so that row is corrected for precision rather than removed.
- [x] FAILED: on the ordinary "setup finished, anything left?" path, an agent installed the
      two-minute restore timer on every speaker before any wipe was observed, reasoning explicitly
      past the file's own hedge and asserting "it costs you nothing to have running even before
      you've proven the wipe happens". That is false, and the code says so: `slots_to_write`
      returns any button whose stream differs from the template, so the timer reverts a station
      retuned on the speaker within one interval.
- [x] FAILED: asked to set up detection of a quiet failure, an agent had to invent the whole
      mechanism, and reported its cadence and its mail path as unsourced. Its script branches on
      success or failure alone, so it collapses "presets missing" and "speaker asleep" into one
      alert - the shipped `check` already separates them as exit 1 and exit 2.
- [x] The contamination check names this machine's cascade as covering the general lesson. The two
      failing arms stand regardless: inherited context can only push an agent TOWARD the correct
      answer, so it cannot manufacture a failure. Only the passing arms are discounted, and they
      are.

## GREEN

- [x] The false claim is gone. "The restore has to run on a schedule, or the presets vanish again
      at the next power cut" is replaced by what the journal shows: 11692 runs over 18.7 days wrote
      presets exactly once, in the first hour, cleaning up a loss that predated the timer, and no
      speaker ever answered while short of its presets. Stated as a reason to measure this
      installation, never as a result to copy.
- [x] The boot-wipe trace carries its version and date, and says the rewrite in its last line is a
      restore run rather than the speaker healing itself.
- [x] Both costs of an always-on repair loop are stated: it reverts a station the owner retuned,
      and it hides the event the owner wanted to know about.
- [x] Alerting is a section rather than an absence, built on the exit codes the scripts already
      return, with the two failures kept apart and the measured reason why: at one site a single
      sleeping speaker produced 1303 unreadable readings out of 11692 while never once being short.
- [x] Sourcing a stream is now four steps: harvest, ask the owner which stations they still want,
      research what is left, prove every URL before it reaches a button. An application scenario
      run against the new text follows all four in order, asks the owner the choice question at the
      right point, and refuses to write until every button validates.
- [x] Re-run on the corrected text, the arm that had to invent an alerting mechanism now builds an
      alert-only watcher on the documented exit codes, holds exit 2 for a long streak, and declines
      the repair timer explicitly.
- [x] Re-run on the corrected text, the arm that installed the timer now declines to, quoting the
      governing lines rather than paraphrasing them.
- [x] `SKILL.md` advertised a `template` subcommand the parser does not implement. Found by a
      baseline run, removed.

## REFACTOR

- [x] Every RED and GREEN dispatch is asked for a `Skill gaps` section, and every reply's list is
      recorded and worked.
- [x] GREEN opened a gap the edit itself created: the text asks for a week of read-only measurement
      but showed a schedule only for the WRITE path, so an agent correctly refused to invent one.
      A logging `check` schedule and the one-line way to read the week back are added.
- [x] GREEN opened a second gap the new capability created, reported independently by two runs:
      neither could say what `validate` does with a hole `harvest` left. It called it `dead`, which
      is the wrong instruction - `dead` sends the reader to find a replacement stream, when nobody
      has looked for one yet. A `missing` verdict is added, documented, and pinned by a test whose
      injected fetch FAILS if it is called at all, so the verdict cannot come from a network answer.
- [x] A GREEN run found a real limit nothing had stated: `check` compares the speaker's stored
      presets against the template and never contacts the service, so a service that died after a
      `:latest` pull leaves it reporting 0 on every speaker. Read from the code, then written down,
      together with what covers that gap instead.
- [x] Declined, with reason: no reboot mechanism is named for a speaker (out of scope for this
      file, and a power cycle needs no instruction); the systemd pair is written for one speaker
      and readers extend it per speaker correctly without being told; `soundtouch_service.py` has
      no exit-code contract in this file, which belongs to the service reference, not this one;
      editing a harvested template is ordinary JSON editing and both runs did it unprompted.
- [x] Each fix is verified by quote-back, not by paraphrase.
- [x] GREEN is diffed against RED in both directions. The baseline's correct results - pinning the
      service address, backing up before migrating, the reboot acceptance step - all survive.

## Quality

- [x] The new detector is verified against controls that must answer differently: an `.m3u`
      playlist served as `audio/x-mpegurl` is NOT reported as audio, an HLS segment list is
      separated from a stream, a landing page served as `text/html` is not a station, and a 404 is
      dead. A bare `audio/` test passes the first of those, which is why the test exists.
- [x] A template with an unresolved hole cannot be written to a speaker: the writing path refuses
      it and names the button, while `validate` reads it, because reporting holes is its job.
- [x] The usage-line contract test stopped at a pipe but not at a shell redirect, so a documented
      line that logs to a file parsed its redirect as arguments. The matcher is fixed and pinned by
      a test, checked against a control: a line whose arguments are `<placeholder>` values, which
      also contain angle brackets, parses identically before and after.
- [x] Every address, MAC, host and path added here is a reserved documentation value.
- [x] No session narrative, operator instruction, scratch path or private infrastructure in the
      skill or in this artifact.
- [x] Tables reformatted, typographic tells stripped.
- [x] Reference table topics updated so the new material is reachable from the index.
- [x] Description stays trigger-first and under the 500-character target, measured rather than
      eyeballed.

## Deployment

- [x] Frontmatter parses.
- [x] `tests/` covers every new function, and passes.
- [x] Full CI-parity gate green.
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs or personal data.
- [x] Plugin version bumped, derived catalogue and trigger map regenerated.
