# checklist - walk the unsettled points, one at a time

The review no longer ends at the list. Interactively it puts each surfaced point to the person as
its own question, with the options and their trade-offs and a recommendation, and gets a decision
back.

## RED

- [x] The gap is a property of the FILE, so the artifact is the evidence. A scan of the pre-change
      text finds no instruction to ask one at a time, to offer options, or to recommend, and the
      interactive path terminates: "say it, in the conversation, and stop."
- [x] The lesson under test is ALREADY in the always-loaded context of the machine this is authored
      on - a rule about putting one decision at a time with trade-offs and a recommendation.
      `redcheck.py --corpus-cascade` reports STRONG inherited coverage and names the document. A
      behavioural baseline dispatched there therefore cannot be assumed to fail honestly, and this
      is recorded rather than worked around.
- [x] The route taken is the one that inherited context cannot fake: quote-back against the
      artifact. A model cannot quote an instruction out of a file that does not contain it.
      On a weak literal tier, asked what to do after the list: `"say it, in the conversation, and
      stop. It is for the person reading."` Asked whether the text says to put the points one at a
      time: NONE. Asked whether it says to offer options with trade-offs and a recommendation:
      NONE.
- [x] The behavioural arm then ran in a GENUINE clean room, not merely in-harness: headless with
      `--safe-mode`, which disables CLAUDE.md, skills, plugins, hooks and MCP while leaving auth
      working, so no credential handling is involved. The instrument was validated first with a
      control probe, which came back free of the hook output that had polluted an earlier attempt.
      Scenario: a described work session of fourteen steps holding several genuinely unsettled calls
      mixed with clearly-right ones, with which are close calls never stated.
      **RED RESULT: a flat list of three points, no question put to anyone, no options, no
      recommendation.**
- [x] The residual floor is recorded rather than claimed away. The control shows the product's OWN
      system prompt asks for "a recommendation and the main tradeoff" on exploratory questions. No
      clean room removes that, and every reader of this skill has it. It teaches neither
      one-at-a-time, nor per-option trade-offs, nor the tool.
- [x] Baseline findings recorded for the both-directions diff: a default that breaks people who
      upgrade, a mechanism replaced outright where the old one had other callers, a flaky test
      waved off, and a declined escape hatch whose stated reason contradicts itself. The settled
      steps are correctly absent.

## GREEN

- [x] **The first GREEN FAILED, and that failure is the result worth having.** Given the new text,
      the weak tier emitted the framing question to the person and stopped - no list at all, all
      four baseline findings lost. Its own gaps section names the cause: it read "The question" as
      something to ask the user, and "put each point to the person and get an answer" confirmed
      that reading.
- [x] Root cause fixed rather than the symptom worked around: the ambiguity was already latent in
      "The question", which never said who answers it. The new section made it load-bearing. The
      section now states that the question is put to YOURSELF and that the list IS the answer.
- [x] Re-run with everything else held fixed - same tier, same scenario, same prompt - and the list
      is restored. GREEN then satisfies every pass criterion: one `AskUserQuestion` call rather
      than a batch, every option carrying an upside AND a downside, the recommended option first
      and labelled, and the settled decisions still absent.
- [x] GREEN re-run in the clean room too, and it found two things the in-harness runs had hidden,
      because in-harness the machine's own rule was propping the result up. First, the weak tier
      SKIPPED THE LIST and opened straight on question one, so the person never saw the count, the
      exit, or what the other points were. The text now requires both, in order, and says what
      skipping the list costs. Second, the weak tier wrote every question at once. A line naming
      that as the failure - if a second question is written before the first is answered, delete it
      - fixes it: the same run now leads with the count and exit, shows the list, sends one
      question and stops.
- [x] Both probes matched exactly before the two arms were compared. An earlier clean-room run
      differed from the in-harness prompt by one clause, and attributing its batching to the skill
      would have been reading a probe artifact as a defect.
- [x] Clean-room run on a CAPABLE tier passes every criterion on the skill text alone, with no
      machine context whatsoever: list first, count and exit, exactly one `AskUserQuestion` in the
      real schema, no invented "Other", recommended option first, both sides on every option, and
      it stops after one and says why. The tier split is recorded, not smoothed over: what the weak
      tier needed spelled out, the capable tier did unprompted.
- [x] Run again on a CAPABLE tier with a time pressure added (the person says they want to be done
      in two minutes), because that is where a one-at-a-time rule is most likely to be rationalised
      into a batch. It did not batch, it did not pre-trim the list to fit the deadline, and it said
      so: the pressure is named and refused rather than silently absorbed. The tool arguments came
      out in the real shape, `questions` array and `header` included.
- [x] The "put it to YOURSELF" fix is confirmed behaviourally as well as by quote: the capable run
      states that the opening question is answered internally to produce the list and is not sent
      to the user.

## REFACTOR

- [x] GREEN diffed against RED in BOTH directions. Nothing lost: all four baseline points survive.
      Gained the walk, plus a fifth genuine point the baseline had demoted - the version tier,
      which the skill's own bullet list names as a kind to look for.
- [x] The loss that was guarded against did not happen: "name the alternative you did not take, and
      what would settle it" survives INTO the option descriptions rather than being replaced by a
      bare menu. That is what the rule "The options ARE the alternatives you did not take" is for -
      without it the mechanical step of filling in options displaces the judgement it should carry.
- [x] Two gaps GREEN exposed, both closed in the text. It invented an "Other" option, because the
      text named `Other` without saying who supplies it; the text now forbids adding one. It
      omitted `header` entirely, because the text never named that field; it does now.
- [x] Each fix verified by quote-back, not by re-reading the edit. Four contested questions, four
      direct quotes, no NONE.
- [x] A third gap, from the capable run: "hardest-to-reverse first" carried no test for ranking
      hardness, and the run showed the ambiguity is live - it ranked a breaking default above an
      already-published version number while arguing the version number is the more literally
      permanent of the two. The text now says which reading wins (most expensive to undo once
      shipped, not most technically permanent) and gives a tiebreak (ask first the one whose answer
      changes the others). Verified by quote-back.
- [x] DECLINED: the capable run could not tell from the scenario whether the release was already
      published, what the other callers of the replaced function do, or whether the tool has
      downstream users. Those are properties of the scenario, not silences in the skill, and it
      flagged each rather than guessing - which is the behaviour wanted.
- [x] DECLINED: GREEN put the count-and-exit line after the list rather than opening with it. The
      list carries its own count, so nothing reaches the reader worse; more text to enforce the
      ordering costs more than the defect.
- [x] DECLINED: the body exceeds the 500-word target for a process skill. The walk is doctrine a
      reader must have loaded in order to act correctly, so moving it into a reference file would
      mean a reader who does not load it does the wrong thing - the opposite of the trade the
      budget is meant to buy.

## The automatic entry point

- [x] The Stop-hook reason describes the walk as well, so the path that fires on its own cannot
      promise behaviour the skill no longer has. Pinned by a test asserting the tool name, the
      one-per-point rule and the wait-for-the-answer clause, so it cannot silently drift back to
      asking for a bare list.
- [x] The two assertions that already pinned that text - the skill name and the suppression clause
      - both still hold. Whole hook suite green.

## Quality

- [x] Present tense throughout, no session narrative, no scratch paths, no machine-derived values.
- [x] Derived artifacts regenerated after the description changed, and both report in sync.
- [x] This skill has no mirrored twin, and the mirror audit reports 0 of 10 pairs drifted.
