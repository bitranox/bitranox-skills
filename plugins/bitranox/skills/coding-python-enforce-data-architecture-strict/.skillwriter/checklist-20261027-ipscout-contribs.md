# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-10-27, contrib notes)

Seven queued notes folded into the workflow they qualify, not appended: fixed-shape tuple records
(Anti-Patterns, Instructions step 2, STEP A prompt, analysis template, STEP A candidate sweep,
STEP D grep); the `str`-parameter call-site sweep (Anti-Patterns, step 2, STEP A prompt, template,
a `sweep` count in the analyser JSON); reproduce a claimed runtime failure before briefing a fixer
(STEP B); a SCOPE rule with a `git blame` instrument and a `base` / `out_of_scope` state (state
file, STEP A, loop exit, DO NOT STOP); STEP C item 5 against HEAD and the last release, with
wrong-type inputs, a marked liveness control and never `python -I`; where the Enum's
import-linter layer decides where the helper lives (the str-to-Enum section).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`, checked fresh) and this skill
      loaded through the Skill tool before the first edit.
- [x] Skill type: technique (a workflow); the test is retrieval and application - which step,
      which command, which decision - answered by direct quote from the text.
- [x] RED by text check against the pre-change file: no line named a bare tuple record,
      `NamedTuple` as a fix, a call-site sweep for `str` parameters, `git blame`, a scope rule, the
      last release as a baseline, wrong-type inputs, `python -I`, or import-linter layers. The
      behavioural RED was replaced by this text check: `redcheck --corpus-cascade` named
      always-loaded documents for four of the seven scenarios (term overlaps in large memory
      indexes), so a no-skill arm could not fail honestly.
- [x] Claims verified by probe before writing them:
      - `python -I` ignores PYTHONPATH: the same import found the PYTHONPATH package plainly and
        raised `ModuleNotFoundError` under `-I`.
      - a `NamedTuple` stays tuple-compatible: `isinstance(p, tuple)`, unpacking, indexing,
        `p == ("h", None)` and equal hashes all held.
      - `git blame <base>..HEAD -- <file>` prefixes lines not changed since `base` (the base
        commit's own lines included) with `^`; a changed line carries its own commit.
      - import-linter counts an import under `if TYPE_CHECKING:` against a layers contract (exit
        1, "is not allowed to import"); with `exclude_type_checking_imports = True` the contract
        is kept.
      - pydantic 2.14.1 lax mode accepts `True` for an int (stored 1), `"1"` for a float and
        `3.0` for an int; `strict=True` refuses all three (`int_type` / `float_type`).
      - the measured layer example: the helper's callers sit in layers above `models` in that
        project's layers contract.
      - the candidate grep `grep -rnE -- '-> tuple\[|: dict|-> dict'` matched both a tuple return
        and a dict parameter in a scratch file.
- [x] GREEN by quote-back on the edited text (4 questions, 11 parts), opus at effort medium and
      haiku: every part answered with a direct quote, no NONE, both tiers correct. quotecheck: 11
      of 11 quotes OK, a planted invented sentence MISMATCH.
- [x] Gaps from GREEN, each decided:
      - `^` described as "older than base" while blame also marks the base commit's own lines -
        CLOSED: "prefixes each line NOT changed since `base` with `^`".
      - when the out-of-scope list goes to the user, what follows, whether it counts toward the
        loop exit (haiku read a contradiction) - CLOSED: "they do not count toward
        total_violations", "ONCE, when the in-scope count reaches zero", ruled-in findings move
        back to `violations`, and the loop exit names the step.
      - how to choose `base` - CLOSED: "the tag or commit it names when it asks about a change
        set (...), otherwise HEAD at INITIALIZATION" (wording as revised in the coordinator box
        below).
      - `//` comments make the state template invalid JSON - CLOSED: "the `//` notes explain
        fields; leave them out of the file".
      - moving the helper onto the Enum can break callers below the Enum's layer - CLOSED: "the
        second only when no caller of the helper sits below the Enum's layer", plus "Re-run
        `lint-imports` after the move".
      - no threshold for "small fixed set" - DECLINED: a judgement the skill leaves to the reader.
      - a nonzero `tuple_returns` with no violation - DECLINED: an excluded tuple is a judged hit;
        the candidate sweep re-dispatches only unjudged hits.
      - the referenced "Converting a `str` parameter" section and the Exceptions rule were not
        in the excerpt - DECLINED, covered elsewhere: both are in SKILL.md (the section heading
        "Converting a `str` parameter to an Enum changes its contract", and the Exceptions DoD
        item "Small local dicts (few items, single function scope) may remain").
      - how to read the layer order - DECLINED: owned by bitranox:coding-python-clean-architecture.
- [x] Re-probe on the final text (4 questions on the closed gaps), opus at effort medium and
      haiku: both correct with direct quotes (a base-commit line goes to `out_of_scope`; 12 out of
      scope -> asked once, 3 ruled in -> STEP B; `base` is HEAD at INITIALIZATION; the helper may
      not move onto the Enum with a low-layer caller, then `lint-imports`). quotecheck: 7 of 7 OK,
      a planted control MISMATCH. New gaps:
      - the measured example read as permission against its own caveat (both tiers) - CLOSED:
        "and every caller sat above `models`, so it became a method on that enum"; re-probed on
        the final text, recorded below.
      - whether a ruled-out finding is asked again, how whole-file scope is recorded, whether a
        user ruling resets "pass", what to do when the Enum can move nowhere - DECLINED: judgement
        and bookkeeping the skill leaves to the reader; STEP A increments "pass" on every entry.
- [x] Final re-probe of the example fix (2 questions), opus at effort medium and haiku: both
      answer "No" for a helper with a low-layer caller, quoting "the second only when no caller
      of the helper sits below the Enum's layer", and both read the example as consistent,
      quoting "every caller sat above `models`". No new undecided gap: "below" read as the
      layers-list order, sibling or independent layers, splitting the helper, the callers' new
      call form and whether the Enum's own imports fit lower down - DECLINED as judgement the
      skill leaves open, with the layer mechanics owned by
      bitranox:coding-python-clean-architecture.
- [x] Coordinator review revised SCOPE: as first written it counted only lines changed since
      `base` on EVERY pass, which on pass 1 of a whole-package request (base = HEAD) puts every
      finding out of scope. Now pass 1 of a whole-file or package request counts every finding;
      from pass 2 on, and on every pass of a change-set request, only lines changed since `base`
      count. Probe: an uncommitted fix shows as `00000000 (Not Committed Yet ...)` under
      `git blame <base>..HEAD`, never `^`, so a line edited but not yet committed stays in scope.
      Quote-back on the revised passage (3 questions: pass-1 whole-package finding, pass-3
      untouched line, "since v2.0.0"), opus at effort medium and haiku: both correct with direct
      quotes. quotecheck: 6 of 6 OK, a planted control MISMATCH. Gaps raised (deleted or moved
      lines, where a ruling is recorded) - DECLINED: blame bookkeeping the skill leaves to the
      reader.
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku, example re-probe opus + haiku, SCOPE
      revision opus + haiku - 8 cells.
- [x] Description unchanged - no routing keyword moved; trigger map not rebuilt.
- [x] ASCII only (0 non-ASCII bytes); no added line over 100 characters; tables canonical
      (`reformat_tables.py --check`: Unchanged); history finder over the added lines: no hit.
- [x] No address, MAC, hostname, user or machine path added; the measured examples name no
      project, host or module beyond generic `errors` / `models` layer names.
