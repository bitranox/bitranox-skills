# compuse-toolbox: adding `ci_wait` (5.236.0)

Skill type: REFERENCE (a routing table over bundled scripts). Test approach: retrieval scenarios -
can an agent with the table find the tool from the symptom, in a user's words, with NONE allowed?

## PLAN

- [x] Skill type identified: reference/hub. The failure mode is a jig nobody finds, so the test is
      retrieval, not pressure.
- [x] Scenario drafted before the row was written: "I just pushed a commit. Before I cut the release
      tag I need to wait until GitHub Actions has actually finished on that exact commit - all of
      the workflows, not just whichever one shows up first - and then tell me whether it went green."
- [x] Scope: one script plus one table row in an existing skill. No new skill, no supporting files.

## RED

- [x] Scenario run against the table WITHOUT a `ci_wait` row, whole table shown, NONE stated as an
      acceptable answer. Result: **NONE.** The agent hand-rolled the loop
      (`while true; ... gh run list --json ... | jq 'select(.headSha == $sha)' ... sleep 60`) and
      explicitly rejected the nearest row: "the closest-sounding one is `ci_triage`, but that only
      extracts error lines out of an already-finished, already-fetched CI log - it doesn't identify
      runs, doesn't poll, and doesn't know about 'all workflows for one commit'."
- [x] Baseline contamination ruled out for the part that matters: the RED agent DID reproduce the
      standing sha rule from its inherited context, and still answered NONE. So the inherited
      context teaches the RULE and not the TOOL, which is exactly the gap the row closes - the
      baseline could and did fail honestly on retrieval.
- [x] Pattern in the failure: the rule was known, the remedy was hand-rolled anyway. A rule without
      a findable tool gets re-implemented.

## GREEN

- [x] Row written from the RED agent's own nouns (wait, GitHub Actions, that exact commit, every
      workflow, before tagging a release), with the trap named and the neighbour disambiguated.
- [x] Scenario re-run against the SHIPPED table (this repo's `SKILL.md`, not the local toolbox copy
      the tool was prototyped in - the two rows are worded differently). Result: **`ci_wait`**, with
      the correct command, and an explicit refusal to hand-roll: "I would not write a one-off
      `gh run list` / `gh run watch` script here - the packaged tool already encodes the exact
      failure modes that a hand-rolled version would need to reinvent."
- [x] Description line extended with the chore ("is CI finished on the commit I just pushed, and did
      it pass"), since the router retrieves on that field.
- [x] Both dispatches asked for a `Skill gaps` section; both replies' lists recorded below.

## REFACTOR - every reported gap closed or declined

- [x] **CLOSED** - "could not confirm whether `ci_wait` auto-detects `--repo` from the current git
      remote when the flag is omitted; the table shows it as optional but does not document the
      fallback." The row now says `--repo` falls back to the current directory's repo.
- [x] **DECLINED** - "the exact `--repo OWNER/REPO` value is a guess." That is a property of the
      reader's task, not of the skill; the row cannot know it and `--help` already names the flag.
- [x] **DECLINED** - "the task doesn't say whether a public PR is open, in which case the review
      loop also applies." Correct, and owned by a different rule; `ci_wait` answers "did CI pass",
      which the GREEN agent stated unprompted.
- [x] RED/GREEN diffed in BOTH directions. Nothing the baseline produced was lost: the RED's
      substantive output was the hand-rolled loop plus the four traps it encoded, and GREEN names
      the same four traps as reasons to use the tool. No baseline result is missing from GREEN.
- [x] Fix verified by quote-back, as a separate dispatch answering only with a verbatim quote or
      NONE. Asked "if I omit `--repo`, which repository does this tool look at?", the reply was the
      governing sentence itself: "`--repo` is optional and falls back to the current directory's
      repo" - a quote, not a paraphrase, so the row states the rule rather than merely permitting
      it to be inferred.

## Quality

- [x] No narrative or private provenance in the skill or this artifact.
- [x] Every value in the shipped files is generic: examples take `OWNER/REPO`.
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over `scripts/ci_wait.py` and `tests/test_ci_wait.py`: no matches.
- [x] Cross-platform: argv list never a shell string, no `shell=True`, `encoding="utf-8"` and
      `errors="replace"` explicit on the one `subprocess.run` (an unencoded `text=True` fails
      differently on Windows and POSIX and returns `stdout=None` on Windows).
- [x] Import-safe: all run-time work behind `if __name__ == "__main__":`; the core takes `fetch` and
      `sleep` as parameters, so the loop is tested without a network or a clock.
- [x] Stdlib only, so it imports in a BARE environment - verified in a fresh venv holding only
      pytest: 18 passed.
- [x] LF line endings, ASCII, index mode `100644` (interpreter-run, no shebang, never `./`-run).
- [x] Security review of the diff: no secrets, credentials, hostnames, IPs, internal paths or PII;
      no `eval`/`exec`, no `shell=True`, no unpinned fetch-and-run.

## Tests

- [x] `tests/test_ci_wait.py` covers every main function: `require_full_sha` (short, non-hex, and
      the lowercasing pass-through), `verdict` (all five states including a completed run with a
      null conclusion), `wait_for` (polls to terminal, the deadline, the appear grace, and that the
      grace is a DURATION so a short `--interval` cannot shrink it), `exit_code_for`, and `gh_runs`
      (client-side filtering, a non-zero `gh` exit, unparseable output). 18 passed.
- [x] Whole-repo CI-parity gate green: `repo-gate.py --ci` with the full CI dependency set.

## Deployment

- [x] MINOR bump to 5.236.0 - a backward-compatible capability addition.
- [x] `build_skill_docs.py` and `build_skill_triggers.py` re-run; skill count unchanged (no new
      skill), so the README counts need no edit.
- [x] CHANGELOG entry under 5.236.0.
