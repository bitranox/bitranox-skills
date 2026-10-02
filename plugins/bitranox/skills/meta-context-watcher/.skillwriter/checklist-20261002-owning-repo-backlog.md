# checklist-20261002-owning-repo-backlog

Change under test: an `OPEN-WORK.md` item is filed in the backlog of the repo whose code needs the
change, not the repo it was found from. Three places: the "Two files" section states the rule
(line carried unchanged with its first-raised date, file created in the target if missing, at most
a closed `moved to <repo>/OPEN-WORK.md` line left behind); procedure step 2 names the owning repo
as the reconcile target; "When you are the one READING" checks each item's owning repo before
working it and moves a misfiled one.

The failure behind it: items about a CLI template and its derived applications were filed in a
general-purpose library's backlog, and the next session, taking that backlog's top item as
instructed, began editing the template's email adapter from the library's repo.

## PLAN

- [x] Skill type: discipline (a filing rule followed under the "work the top-ranked item" rule).
- [x] Scope: `SKILL.md` only, three insertions; no hook change (the SessionStart backlog block
      reads whatever `OPEN-WORK.md` holds and needs no ownership logic).

## RED

- [x] Inherited-coverage check: `redcheck.py --corpus-cascade` on the library session's directory
      answered INHERITED COVERAGE (STRONG); that directory's memory store also holds a fact recording
      this exact lesson. A behavioural RED there cannot fail honestly, so the route taken is a TEXT
      CHECK of the artifact.
- [x] Text-check RED: the pre-change `SKILL.md` contains no rule about which repo an item belongs
      to - `grep -n -i "another repo\|owning\|owns"` returns no line, and step 2 says only "add it
      now" to `OPEN-WORK.md`, which with "sits at the repo root" resolves to the current repo.

## GREEN

- [x] Text-check GREEN: the rule is present in all three places (grep for "repo that owns the
      fix", "whose code needs the change", "check which repo its fix lands in" each hits once).
- [x] Behavioural arm on haiku, the least inferential tier, with the edited sections pasted
      (used for gaps, not as proof, given the inherited coverage). Writing scenario: a rounding bug
      in the library's own module went to the library's `OPEN-WORK.md`; a bug in a dependent
      application went to that application's `OPEN-WORK.md`, created new. Reading scenario: the
      misfiled top item was moved and closed as moved, and the library's own second item was
      worked. Both acted on the new sentences, quoted.
- [x] The arm was asked for a `Skill gaps` section; its list is worked below.

## REFACTOR - every gap closed or declined

- [x] GAP: whether a moved line keeps its date or is reformatted. CLOSED - "its line carried over
      unchanged with its first-raised date".
- [x] GAP: whether creating the target repo's `OPEN-WORK.md` needs a commit. CLOSED - "tracked or
      excluded the way that repo keeps its own working files".
- [x] GAP: `handover.md` structure, dating a newly found item, ranking two equal FOUND items.
      DECLINED - stated in sections of the full skill the probe excerpt omitted ("What belongs in
      it", "Never infer a date", "How rank is decided"); untouched by this change.
- [x] Quote-back on haiku for both closed gaps plus the left-behind line: all three answered with a
      direct quote of the new text, none with NONE.
- [x] GREEN diffed against the pre-change behaviour: the only change is where a foreign item is
      written and that a misfiled one is moved before work; reconcile-first, the overwrite and the
      ranking order are unaffected.
- [x] The exception for a user who asks for a moved item to be worked from the current repo is
      stated, so the rule does not refuse an explicit request.

## Quality

- [x] Description unchanged, so the trigger map needs no rebuild.
- [x] No narrative, no scratch paths, no addresses added; the failure is stated generically.
- [x] Added lines wrapped at 100 columns.

## Deployment

- [x] Version bumped to 7.36.0 in `plugin.json` and `pyproject.toml`; CHANGELOG entry added.
- [x] `repo-gate.py --ci` run before the push.
