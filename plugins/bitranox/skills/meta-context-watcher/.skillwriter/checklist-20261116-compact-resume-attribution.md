# checklist - the compaction resume hands back only the checkpoint this session wrote

`hooks/compact-resume.py` now hands back a checkpoint only when the session's own transcript shows
it writing that file with Write/Edit after the save request, unchanged since; a fresh checkpoint
file no record attributes is listed with path and age instead. The skill paragraph on the resume
block gains the rule for that listing block: what the block does and does not hand back, that a
listed file describing the summary's work is notes only, what proves a listed file is the
reader's own (its own Bash write of the path in the summary or transcript), and that without that
proof it is neither edited nor marked STALE.

Decisions: d-20261116-8f504808

## RED

- [x] Skill decisions read first: no rejected or removed entries for this skill.
- [x] Hook tests written first and run on the pre-change hook: worktree cwd with a newer tracked
      copy beside the main-checkout file the session wrote; a peer's newer handover in the shared
      checkout; a peer overwriting a file the session wrote earlier; the session's own worktree
      copy beside a newer peer file; a failed or pre-request write; no transcript and an
      unrecorded cwd file. All six failed on the assertion they were written for.
- [x] Text probe (haiku) on the pre-edit paragraph, shown the new listing block: it reached "not
      yours" only through the neighbouring "names work the summary never mentions" clause, and its
      gaps named the missing rule: "The skill has two branches that could fit this block ... The
      block is a hybrid." Nothing in the old text covered a listed file that DOES describe the
      summary's work.

## GREEN

- [x] Hook: 52 tests pass; three mutants of the attribution (drop the unchanged-since check,
      trust every path without a transcript, ignore is_error and the request time) each killed by
      the test written for it.
- [x] Hook run on a real 74 MB session transcript: own_checkpoint_writes found that session's two
      handover.md writes in 0.2 s.
- [x] First text revision, opus and haiku: both refused to mark the listed file STALE in both
      cases, quoting the new sentence.

## REFACTOR

- [x] Closed (opus, haiku): "may a listed file that the summary names have its next action
      taken?" - the text now says it is notes only: check against the summary and git, continue
      from the summary's step.
- [x] Closed (opus, haiku): "no test for 'you can tell it is yours'" - the text now names the proof
      (the summary or the named transcript shows this session writing the path through Bash after
      the request) and says a matching subject is no proof.
- [x] Closed (opus): "reading before knowing the content" - opening a listed file to see its
      subject is now stated as fine.
- [x] Closed (opus): where "otherwise" attached - the sentence is split into one per case.
- [x] Declined (opus): "the handed-back paragraph marks STALE in both branches" - by design: the
      STALE line marks the reader's own checkpoint as read, whichever next action follows; covered
      by checklist-20261115-compact-resume-check.md.
- [x] Width and fence check over the added lines printed nothing; no non-ASCII added.
- [x] Re-probe on the revised text, opus and haiku, three cases (a listed file about other work;
      one about the summary's work with no proof; the same with the session's own Bash write in
      the transcript): both tiers answered open / not the next action / no STALE, open / notes
      only / no STALE, and open / handled as a handed-back checkpoint, each quoting the new
      sentences verbatim.
- [x] Closed (opus): "unchanged since is not checked on the Bash path" - the proof now also needs
      the file's age to show no later change; re-probed on haiku with a quote-back: given an own
      Bash write at 10:08 and a listed change at 10:12, it answered not yours and no STALE, quoting "A listed file is yours only when the
      summary or the transcript the block names shows you writing that path through Bash after the
      save request, and the file's age shows no later change". Its remaining gaps are declined:
      "the block hands back only Write/Edit files yet a Bash write proves ownership" describes two
      different deciders (the hook, then the reader), not a conflict; "age is undefined" - the
      block prints each file's change time beside its path, which is the age meant.
- [x] Declined (opus, haiku): "mark it STALE as the block says points at nothing for a listed
      file" - the STALE line's form is stated in the skill itself, SKILL.md "When you are the one
      READING a handover" and the handover template line "replace the first line with
      `# STALE - read <date>, work continued`".
- [x] Declined (opus): "searching the transcript for the proof is implied, not instructed" - the
      sentence names the transcript the block names as where the proof lives, and the
      no-checkpoint sentence beside it names the reader; adding a search recipe is detail.
- [x] Declined (opus, haiku): "what the notes are for when their next action is ahead of the
      summary" - deliberately left to judgement: the notes inform, the summary's step decides.
- [x] Declined (haiku): "a self-written file about work the summary never names" - with the proof
      it is handled as a handed-back checkpoint, whose own rule for work the summary never
      mentions then applies; the two rules do not conflict.
