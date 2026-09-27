# skill-writer checklist - infra-modulejail (2026-09-27, gate before write)

The invariant gate ran AFTER the file was written into `/etc/modprobe.d`, and it gated a
different file from the one written.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. The defect is in the procedure's order and in the file the gate
      reads, so the test is an executed probe of the document itself: extract its code blocks,
      run them in a scratch dir, and check the order of the gate and the write.
- [x] Scope: steps 3 to 6 restructured; wording that described the block by one form only,
      and the Verify commands, corrected. No new capability.

## RED
- [x] Behavioural RED not used: the skill is installed on this machine, so a subagent answers
      from the shipped wording. Route taken: executed ground-truth probes.
- [x] Order probe on the old file: first write into `/etc/modprobe.d` at line 133, first gate
      heading at line 144 - the write came first, so a failing gate found the host already
      changed (the override takes effect on the next load attempt).
- [x] Both install-line generators in the old file run on a fixed `block.list`: the one that
      writes `/etc` produced the logger form, the one the gate counted produced
      `install dccp /bin/true`. The gate checked a file that was never applied.
- [x] `modprobe -n -v` against a scratch root (`-d`, `-S`) prints NOTHING and exits 0 for a
      kept module that is already loaded (veth, loaded on this kernel), while
      `modprobe --show-depends` prints its insmod path. The Verify step's "a KEPT name ->
      resolves to a real insmod path" was false for the usual case on a live host.

## GREEN
- [x] Step 3 now writes `candidate.conf` in the working directory, in the logger form. Step 4
      gates that file, reading the blocked names back OUT of it; step 5 installs it unchanged
      with `install -m 0644`; step 6 is the reboot gate. No code in steps 3 and 4 names `/etc`.
- [x] Order probe on the new file: first gate heading line 140, first write line 187.
- [x] Steps 3 and 4 extracted verbatim from the new file and run in a scratch dir, with
      `modprobe` pinned to a scratch module root and a stub `lsmod`:
  - a good list: counts 2/2, logger count 2, both `comm` checks print nothing, the dry run
    shows the logger `install` line for dccp and an insmod path for veth;
  - known-negative, veth dropped from KEEP: counts 3/3, both `comm` checks print `veth`, and
    its dry run shows the `install` line;
  - a `/bin/true`-form file: logger count 0 against 2, dry run shows `install /bin/true`;
  - a file that lost a line between `block.list` and the file: counts 2 against 1.
- [x] The silent-block paragraph now describes an `install X <command>` line (the logger
      command or a bare `/bin/true`) and what trace each leaves. The discovery comment points
      at step 3's logger form. Verify uses `--show-depends` and says why.
- [x] Common-mistakes table gains a row for writing to `/etc/modprobe.d` before the gate;
      the table is reformatted with the docs-md-table-formatting script.

## Quality
- [x] Present tense; no session narrative, no scratch paths in the skill.
- [x] Frontmatter unchanged.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
