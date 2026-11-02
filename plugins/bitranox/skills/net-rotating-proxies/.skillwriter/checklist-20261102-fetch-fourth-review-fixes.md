# skill-writer checklist - net-rotating-proxies (2026-11-02, `fetch` fourth review fixes)

Section `## One large file across proxies` and the `fetch` exit codes rewritten for the new resume
contract: a rerun that finds `FILE.part.json` resumes from it with no probe and takes size,
identity and plan from it; proxies agreeing on another view, and a file that really changed, both
end the rerun with exit 1 and keep both files, the resumed run's message adding the two files to
delete if the file changed; exit 2 is local (bad argument, no proxies, a damaged manifest or one
for another URL or `--chunk-size`, an unwritable output) plus a hash mismatch, the one exit 2 a
proxy can cause. Also: a page for a range is named `HTTP 200 without the requested range`, and a
`--chunk-timeout` of 15 s or less never bans a proxy whose connect never completes. Description
unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval, answered by direct quote or
      NONE, `bitranox:baseline-probe` on opus and haiku, the section text pasted.
- [x] RED (section text at HEAD), four questions, both tiers. Q1 (rerun, unchanged origin, two
      page-injecting proxies): opus found two answers in the text, exit 1 by the exit-code
      promise and exit 2 by the vote plus manifest rules, and quoted both; haiku answered exit 1
      through "the probe settled nothing", a reason the code at HEAD does not support (HEAD
      exits 2 there: the vote decides no Range and `_fetch_whole` refuses the manifest). Q2
      (file really changed): both answered exit 2, refused manifest. Q3 (causes of exit 2): both
      listed the manifest refusal and flagged "No combination of proxy answers makes exit 2" as
      contradicted by the hash mismatch (opus also by the vote-driven manifest refusal). Q4
      (`--chunk-timeout 10`, connect never completes): both answered "rotated" by inference,
      and both reported that the text never states the case.
- [x] Each new sentence checked against the code: `fetch` loads the manifest before any probe
      when `out + ".part.json"` exists and builds `_Probe` from it; `_load_manifest` compares only
      `url` and `chunk_size` and refuses a damaged one (`_plan_problem`, `_received_problem`)
      before the part is opened, so both files stay; the exit-1 note adds the delete clause only
      when the run resumed and `counts` holds `wrong-object` or `identity`; `ranged_verdict`
      returns `HTTP 200 without the requested range` for a 200; `_client` sets
      `connect=min(timeout, 15.0)` and `_bounded` raises `BudgetSpent` (a cut) whenever that
      timeout exceeds what is left of the budget; `_finish` raises `HashMismatch` (exit 2).
- [x] Tests cover the documented behaviour: the page-injecting rerun and the rewritten-ETag rerun
      end to end through `proxy_pool.main` (exit 1, manifest kept, received counts kept, a third
      run with honest proxies exits 0 with the sha256 matching), the changed-file contract on the
      CLI and engine level, no `bytes=0-0` probe on a resume, no clause on a first run or on a
      resume that only ran out on cuts, the new manifest checks; each mutation-checked.
- [x] GREEN (new section), same four questions, both tiers: 4 of 4 by quote on each. Q1 exit 1,
      both files kept; Q2 exit 1 with the delete clause, delete both and rerun with the new
      `--sha256`; Q3 the five local causes plus the hash mismatch as the only proxy-caused one;
      Q4 rotated, by the quoted 15-second sentence.
- [x] Gaps closed: the delete clause prints after any answer about another object, whether or
      not the file changed, so delete only once the change is known from outside (GREEN opus);
      rerun with the new file's `--sha256` after deleting (RED opus); a refused manifest leaves
      both files, and a rerun with the original URL and `--chunk-size` resumes instead (re-probe,
      both tiers).
- [x] Gaps declined: where a new digest or size is published (outside the tool); how rotation
      picks the next proxy and whether a dropped proxy returns on the next run (stated in the
      earlier rules: dropped for the run, not written to `bad.txt`); a change that keeps size,
      ETag and Last-Modified (the `--sha256` bullet: only the hash catches it); a second Ctrl-C
      (out of scope); exit codes of the first run and of a mid-run empty pool (stated in the
      exit-code list and the odd-answers bullet, outside the re-probed excerpt); recovering a
      damaged manifest (there is no such path, the refusal names both files to delete); the
      loose antecedent of "whether or not it did" (both final arms read it as the file having
      changed).
- [x] Final re-probe of the reworded Resume bullet, four questions, both tiers: 4 of 4 by quote
      on each, no new undecided gap.
- [x] Added lines under 100 columns; no code fence added or opened; file ASCII-only; history
      finder clean; no address, MAC, hostname or machine path added; present tense.
- [x] `build_skill_triggers.py` and `build_skill_docs.py` regenerated with no change, and both
      `--check` runs report in sync.
