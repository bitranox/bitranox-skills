# Skill-writer checklist: Jev shadow on the stage-2 keep/discard (2026-10-02)

Scope: stage 2 (inspect) gains one nested bullet for the agent-built Jev shadow site
`collect-relevance`. The keep/discard is made by the stage-2 SUBAGENT, so the bullet has the
dispatch ask for two things beyond the scrubbed useful knowledge it already returns: an
`items.jsonl` at a path the main agent gives (state `project` and `candidate`, the note's full
text as read), and a keep or discard for every candidate. The MAIN agent records that
keep/discard as the verdict in `verdicts.jsonl` before `jev_shadow.py run`, and stage 3 imports
what the subagent kept. Gated on `jev_shadow.py status`; the procedure detail stays in
`meta-self-improve/references/jev-shadow.md`, cited with its home and launch shim. Technique
edit; no name, description, trigger or table row changed.

## Design decisions

- [x] Who builds the items: the subagent, because it already reads every candidate file for its
      judgement; the main agent building them would read every candidate into its own context,
      which stage 2 exists to avoid.
- [x] `candidate` holds the note's full text, not a summary: a summary is written by the judge
      and would carry its reading into what Jev is asked. The tool redacts secrets and caps the
      field before sending.
- [x] Every candidate gets a verdict, none left out: stage 2 decides every candidate (keep or
      discard), so no cut of `items.jsonl` is needed. Volume is the stage-1 candidate count,
      which stops the gather at 0 and is otherwise topic-dependent; the site is agent-built, so
      there is no `items` builder to measure against a store.

## PLAN

- [x] Skill type: technique step inside a process skill. Test approach: application scenario on
      haiku, inert probe type `bitranox:baseline-probe`, procedure stages 1-4 (and in GREEN the
      reference's procedure section) supplied in the prompt.
- [x] Fixture: a project with a scope descriptor (a PDF invoice generator), 20 stage-1
      candidates in one tree, and the subagent's reply fixed by the scenario: 6 kept, 14
      discarded. Settings: `classifier_backend = jev`, `classifier_skills = shadow`, a Jev key
      present.

## RED (current text)

- [x] Inherited coverage: `redcheck.py --corpus-cascade` flagged the scenario on function words
      only (`assume`, `decides`, `subagent`, `example`, `useful`); the lesson's own terms
      (`jev_shadow`, `verdicts.jsonl`, `collect-relevance`, `classifier_skills`) occur 0 times
      in the cascade and the fact bodies. The behavioural arm was kept.
- [x] One haiku arm on the old text: a `sonnet` dispatch asking for "USEFUL: each slug with
      reason + privacy-scrubbed summary" and "NOT_USEFUL: each slug"; subagent scratch lists
      `stage2_findings_useful.txt` and `stage2_rejected.txt`; no `items.jsonl`, no
      `verdicts.jsonl`, no `jev_shadow.py`. The 6 kept go to stage 3 on the subagent's
      judgement. `Skill gaps`: return format not prescribed, who scrubs, whether the main agent
      re-vets the kept ones.
- [x] RED outcome as predicted: with the knob on, no verdicts file and no shadow run.

## GREEN (new text, plus the reference's procedure section)

- [x] Arm 1 (first text: "also ask the subagent to write `items.jsonl` ... `<the note's
      text>`"): dispatch asks KEEP/DISCARD per candidate and an `items.jsonl` with a one-line
      summary per candidate; main agent writes `verdicts.jsonl` 20 lines (6 `true`, 14 `false`),
      then `bash /p/hooks/run-python.sh /p/skills/meta-self-improve/jev_shadow.py run --site
      collect-relevance ...`; the 6 kept go to stage 3. `Skill gaps`: file location, reply
      format, "note's text" undefined, `status` omitted, scrub scope, how `items.jsonl` is handed
      over.
- [x] Arm 2 (second text: "the dispatch still asks for the useful knowledge ... write
      `items.jsonl` at a path you give it ... the note's full text as read, not a summary"):
      `status` first, the main agent wrote BOTH files ("Interpreted as main agent writes both
      files"), 20 verdicts, `run`, and an "(Optional)" `report` in stage 2, with the gap "which 4
      of 20 Jev disagreed on ... might affect Stage 3 decisions".
- [x] Arm 3 (third text: "The SUBAGENT writes `items.jsonl` itself ... `report` waits until the
      gather is finished"): subagent writes `items.jsonl` (20 lines, full text), main agent writes
      `verdicts.jsonl` (20: 6/14), `run` through the shim with the right path, no `report`; it
      quoted "`report` waits until the gather is finished". But its dispatch asked only for
      KEEP/DISCARD, not the useful knowledge, and stage 3 took the content from `items.jsonl`.
- [x] Arm 4 (final text, the three asks numbered): the dispatch asks for (1) the useful
      knowledge, privacy-scrubbed, (2) `items.jsonl` with the full fact body, (3) keep or discard
      for every candidate; `verdicts.jsonl` 20 lines quoted in full (6 `true`, 14 `false`,
      counted), then `run`; stage 3 content "from subagent's scrubbed summary". It had the
      subagent RETURN the items as text for the main agent to save, on the belief that
      "cloud subagents typically lack local filesystem".
- [x] The documented shapes executed against the shipped tool: one item and one verdict in
      exactly the documented shape, read back by `jev_shadow.read_items` and
      `jev_shadow.read_verdicts` (`{'useful_here': False}`); `run` with no verdicts file exits 2
      and asks nothing. Nothing that costs money was run.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained: the per-candidate keep/discard, items, verdicts
      written by the main agent before `run`, `run` with the right site. Kept: the same 6
      candidates reach stage 3 in RED and every GREEN arm, decided by the subagent.
- [x] CLOSED, LOST result (reproduced in arms 1 and 3): RED's dispatch asked for "USEFUL: each
      slug with reason + privacy-scrubbed summary", the content stage 3 imports; the first and
      third texts let the shadow asks replace it. The final text numbers three asks, the first
      being "Its reply as above: the useful knowledge, privacy-scrubbed - what stage 3 imports";
      arm 4 asked for it and imported from it.
- [x] CLOSED, `candidate` content: arm 1 wrote a one-line summary. The text now says "the note's
      full text as read, not a summary"; arms 3 and 4 used the full body.
- [x] CLOSED, who writes `items.jsonl`: arm 2 had the main agent write both files. The text now
      says "written by the SUBAGENT itself ... so full texts never pass through your context";
      arm 3 complied, arm 4 had the subagent return the text instead.
- [x] CLOSED, `report` before stage 3: arm 2 listed an optional `report` with disagreements that
      "might affect Stage 3". The bullet now ends "`report` waits until the gather is finished";
      arm 3 quoted it and ran no `report`.
- [x] DECLINED, arm 4 returning the items as text: the bullet states the subagent writes the file
      itself and why; a subagent dispatched here shares the filesystem, so arm 4's premise is
      false, and the shadow data is correct either way (only the context cost differs).
- [x] DECLINED, scrubbing hostnames and paths in the dispatch (arms 3 and 4): RED's dispatch did
      the same ("privacy-scrub any credentials/PII/internal paths"), so it predates the edit;
      step 4 already says paths and hostnames are the useful part.
- [x] DECLINED, `status` not run (arms 1, 4): with shadow off `run` itself prints
      `shadow: off (<reason>)`, exits 0 and writes nothing.
- [x] DECLINED, the question id, the reply format and the stage-3 placement: `useful_here` is
      named in the bullet's verdict example; reply format and placement belong to stage 2's and
      stage 3's existing text.
- [x] Noted: arm 3 used bare filenames as ids where the bullet says `<candidate path>`; the tool
      accepts any unique id, and arm 4 used the path.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path. The
      candidate texts go to Jev only with both knobs on, and the tool redacts secrets first.
- [x] Added lines ASCII only and within 100 columns.
- [x] No session narrative or scratch path in the skill text or this artifact.
