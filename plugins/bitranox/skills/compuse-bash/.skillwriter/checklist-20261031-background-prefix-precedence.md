# skill-writer checklist - compuse-bash (a shared prefix before several `&` jobs on one line)

Entry covered: `cd X && VAR=y && (job1) & (job2) &` applies the cd and the variable to job1 only,
because `&&` binds tighter than `&`.

- [x] Coverage check before editing: the SKILL.md had no text on how `&` groups against `&&`.
      The only nearby row, "Backgrounding a long job (run_in_background)", covers `cmd &` inside
      a background wrapper, not a shared prefix.
- [x] Change: one new quick-reference row after the run_in_background row, "Several jobs
      backgrounded on ONE line behind a shared prefix". It gives the parse, the effect (job2 runs
      in the old cwd without the variable, and its relative logs land there) and the fix (each job
      gets its own absolute cwd and environment, or one tool call per job).
- [x] Mechanism measured with a bash script that prints `pwd` and `${VAR-unset}` inside each job:
      broken form `cd X && VAR=y && (job1) & (job2) &`: job1 `pwd=<dir>/X VAR=y`, job2
      `pwd=<dir> VAR=unset`, the line after `wait` `pwd=<dir> VAR=unset`. Fixed one-line form
      `(cd <dir>/X && VAR=y bash -c '...') & (cd <dir>/X && VAR=y bash -c '...') &`: both jobs
      `pwd=<dir>/X VAR=y`.
- [x] `export` variant measured: `cd X && export VAR=y && (job1 > a.log) & (job2 > b.log) &` put
      `a.log` in `X` and `b.log` in the starting directory, and job2 printed `VAR=unset`.
- [x] RED (haiku baseline-probe, pre-edit rows pasted, scenario of two pytest lanes behind
      `cd /repo && export LANE_ENV=ci &&`): "NOT COVERED. The excerpt never says how & groups
      against &&". The answer is NOT COVERED from a text-only agent, so inherited context did not
      supply the lesson.
- [x] GREEN (haiku, edited row pasted, same scenario): "No, only to lane a", quoting "`&&` binds
      tighter than `&`, so bash reads the line as `(cd X && VAR=y && (job1)) &` followed by
      `(job2) &`", and it wrote the per-job fix with `cd /repo && LANE_ENV=ci` inside each
      parenthesis.
- [x] GREEN gap closed: the probe had to infer that `export` behaves the same. The measured
      `export` result was added to the row. Final probe (haiku, only the export question) quoted
      "with `export VAR=y` in the prefix, job2 still saw `VAR=unset` and its `> b.log` landed in
      the starting directory". 1 tier, 3 probes.
- [x] Remaining gaps declined: if the shell already sits in the target dir, job2 lands there by
      coincidence (declined: the fix's absolute cwd per job removes the dependence); `wait`
      covering both jobs (declined: unrelated to the prefix, and the measured line after `wait`
      shows it returned after both).
- [x] Table canonical (reformat_tables.py --strict: Unchanged); the diff adds 1 line.
- [x] ASCII only (non-ASCII line count 0), present tense (history finder: 0 hits in added lines),
      no private host or path.
