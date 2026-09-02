# skill-writer checklist - compuse-toolbox (2026-09-02, five tools added)

Change: five rows added to the tool table - `pushcheck` (new), `backstop`, `enforced`, `confound`
and `transcript_index` (each with `scripts/<name>.py` and `tests/test_<name>.py`). `anchor_edit`
gains a refusal for a relative path; `mem_levels` prunes suffixed virtualenvs.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] RED route: BEHAVIOURAL, one question per agent, the whole index shown, `NONE` stated as an
      acceptable answer. Asked the `pushcheck` question against the index WITHOUT the row: the
      agent answered `NONE`, reached for `git diff ... | grep -inE` with a hand-built pattern
      list, and named the gap itself - "git-range diff scanned against a sensitivity pattern
      list, covering both diff and commit messages". The test can fail, and the row is what
      changes the answer.
- [x] GREEN: five questions, one agent each, phrased as a user's symptom rather than the tool's
      jargon. All five retrieved the intended tool: `pushcheck`, `backstop`, `enforced`,
      `confound`, `transcript_index`.
- [x] Every dispatch asked for a `Skill gaps` section, and every reply's list is recorded below.
- [x] REFACTOR applied from a gap: the `pushcheck` GREEN reported that "confirming *which*
      repo/remote you are actually pushing to isn't something any listed tool does". That is half
      of what the tool does, and it sat in the row's second sentence where retrieval does not read
      it. The first clause now names both halves.
- [x] Gaps DECLINED, with reasons: three replies asked for invocation syntax
      (`backstop`'s finished-signal, `enforced`'s detection method, `transcript_index`'s query
      syntax). The table's Invoke column and each script's `--help` carry these; the probes were
      shown a symptom-column-only index, so the absence is a property of the probe format and not
      of the row. One reply asked whether transcript retention could make a search come back
      empty - out of scope for an index row, and the row already states the tool indexes narrated
      prose only, so a miss is not evidence of absence.
- [x] Scope: shared. Nothing here is specific to one machine or repo - visibility resolution,
      deadline arming, declared-vs-enforced, A/B confounds and transcript search apply anywhere.
- [x] Security scan: the five scripts and their tests carry no hostname, username, absolute local
      path or non-documentation address (`grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/'`
      returns only RFC5737 documentation ranges and the `/home/user/` placeholder, both of which
      are the values the scanner treats as NOT findings).
- [x] Tests ship and pass for every added script: 23 (`pushcheck`) plus the 127 that came with
      `backstop`, `enforced`, `confound` and `transcript_index`; `anchor_edit` 26; `mem_levels` 12.
- [x] `pushcheck` verified against reality, not only fixtures: it resolves `private` for a repo
      whose directory sits under a folder named `public/` - the case the row cites - and `public`
      for this repo.
- [x] Token budget: reference/hub skill; the body stays a table and each row carries its own
      Invoke example.
- [x] CSO description: MEASURED and deliberately left unchanged. The field is 1009 of its 1024
      characters, so five new triggers need roughly 250 characters that do not exist. Appending
      would land them in the truncated tail, and inserting early would push an existing trigger
      out, so covering them needs a REWRITE of the whole description carrying its own RED/GREEN -
      a change to how 24 existing tools route, which does not belong in the same commit as adding
      five. Consequence, stated rather than left to be discovered: the four tools that fall under
      the existing "hand-roll a one-off utility for a recurring chore" trigger stay reachable,
      while `pushcheck`'s pre-push situation has no routing trigger of its own and is found only
      once the skill is loaded. Tracked as a follow-up with the measurement.
- [x] `pushcheck` run against its OWN pending push, and every hit adjudicated against its source
      rather than its matched text: all 16 sat in `tests/test_pushcheck.py` and are the fixture
      strings the tool must detect by construction; nothing fired in the other ~5,000 added lines.
      That surfaced a real usability defect - a security-fixture project cannot push at all - so
      `--exclude` was added, with an unmatched exclusion reported rather than ignored.
