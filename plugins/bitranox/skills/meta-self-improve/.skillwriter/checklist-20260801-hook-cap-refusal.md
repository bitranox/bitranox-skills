# skill-writer checklist - meta-self-improve (2026-08-01, hook hard cap refuses)

Change: the 500-char hook cap is described as a refusal rather than a truncation, in the hook
guidance bullet, the deliverables checklist line, and `references/memory-backend.md`. The engine
now raises `HookTooLong` before the lock and the CLI exits 1; nothing is written. Ships with
plugin 5.120.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] RED, and it FAILED as predicted. A haiku subagent was given the PRE-CHANGE
      `references/memory-backend.md` as its only source of truth and a realistic scenario: a
      complete trigger-first hook that came out at 560 chars, every clause load-bearing. Asked what
      `add` does, what to do next, and whether the resulting pointer line is safe. It answered that
      the fact IS stored with the hook "TRUNCATED ... any load-bearing clauses that fall after the
      500-char boundary are LOST from the pointer line", and prescribed a recovery the store
      forbids: "Delete the truncated pointer line from CLAUDE.local.md". A PreToolUse guard denies
      exactly that edit, so the instruction is unexecutable. Its own gaps section named the hole:
      "That a truncated hook with missing load-bearing info is an error state, not an acceptable
      end state (inferred from the 'self-sufficient' and 'hard cap' language, not stated explicitly
      as a rejection rule)" and "unclear if there is any stderr warning".
- [x] Weak model used for RED (haiku), per the rule that a capable model routes around a rigid
      rule and masks the gap. The scenario withheld the answer: it stated the length and that the
      content was load-bearing, never what the engine does about it.
- [x] GREEN: the same scenario against the post-change file. Correct on all three - "fails with
      exit code 1. Nothing is written to the store", "Rewrite the hook to fit under 500 characters.
      Move the non-load-bearing detail ... into the body", and the pointer line "does not exist
      until a successful add".
- [x] GREEN's own gaps treated as REFACTOR input, not a pass. It reported inferring atomicity:
      "does not explicitly clarify whether a partial write can occur (e.g., body file created but
      pointer not written) ... I treated it as fully atomic." Atomicity is load-bearing and was a
      deliberate design choice (the check sits ahead of the lock), so the text now states it, names
      the `! refused:` output, and says an update keeps its old hook and nothing needs cleaning up.
- [x] The claim matches the shipped code: `memory_engine.add_or_update_entry` raises `HookTooLong`
      before `sig.memory_lock`, and the CLI `add` catches it and returns 1. Five tests cover the
      predicate, the refusal writing nothing, an existing entry surviving a refused update, the
      mover escape hatch, and the CLI exit code; each verified RED against the pre-fix source.
- [x] No session narrative or private provenance: no operator instruction, no scratch path, no
      account of how the file read before the edit beyond the tested claim itself.
- [x] No addresses, MACs, hostnames or machine paths added.
- [x] Cross-references unchanged; no new script or doc reference introduced.
