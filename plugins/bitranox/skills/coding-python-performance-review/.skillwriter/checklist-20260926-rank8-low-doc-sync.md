# skill-writer checklist - coding-python-performance-review (2026-09-26, doc sync for the 7.25.6 script fixes)

setup_env.py is launched with the user's own Python first and `uv run` only as the fallback; find_cache_candidates never reports a function returning a new list/dict/set/ndarray; an `ERROR` line in hotspots.txt or priority_cache_candidates.txt is not a result; compare_performance's stash-collision recovery is described.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed behaviour, answered ONLY from pasted passages, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.
- [x] Inherited-context route: the arms are pasted text on an inert probe type told not to invoke
      a skill, so the answer is a text check of the passages, not of the installed skill.

## RED
- [x] Old passages (built from the porcelain word diff, not retyped), haiku, inert probe type:
      Q1 no project venv: which launcher first, which interpreter recorded: uv run first, its throwaway env (wrong).
      Q2 a function returning a new list: reported?: NONE.
      Q3 an ERROR-only profile section in hotspots.txt: nothing hot?: NONE.
- [x] Skill gaps asked for: the RED reply listed every question above as unaddressed or
      only partly covered.

## GREEN
- [x] New passages, same model and questions:
      Q1 no project venv: which launcher first, which interpreter recorded: "`bx_py` runs it first ... That is the user's own interpreter (an activated venv or conda env included)".
      Q2 a function returning a new list: reported?: "A function that returns a list, dict, set or ndarray it builds is never reported".
      Q3 an ERROR-only profile section in hotspots.txt: nothing hot?: "Such a section is NOT a result: no hotspots there means the profile was never read".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right;
      nothing a baseline answered was lost.
- [x] Skill gaps asked for again. One reported: what the license gate does after reading a
      `SEE LICENSE IN` file - declined, the full sentence in the file continues "and one copyleft
      id rejects" and lists an unrecognised license text as a stop; the probe saw a cropped
      excerpt.
- [x] Every stated behaviour checked against the script it describes, and each script change is
      pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Tables re-padded by the formatter where a row changed (`reformat_tables.py --check` clean).
