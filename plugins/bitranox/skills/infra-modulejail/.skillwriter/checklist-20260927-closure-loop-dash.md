# skill-writer checklist - infra-modulejail (2026-09-27, closure loop under dash)

Two defects: the dependency-closure loop never grows on a Debian or Proxmox host, and the Verify
comment describes a blocked name by the form step 3 no longer generates.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique/reference. Both defects are corrected command lines and comments, so
      the test is an executed probe: the documented form fails, the fixed form works.
- [x] Scope: correction only. No new capability, no step reordered.

## RED
- [x] Behavioural RED not used: the skill is installed on this machine, so a subagent answers
      from the shipped wording. Route taken: executed ground-truth probes, immune to inherited
      context.
- [x] Closure loop, copied verbatim from the skill, run in bash with a stub `modprobe` first on
      PATH (emits a fixed dependency graph: zram needs lz4_compress and lz4_common, snd_hda_intel
      needs snd-hda-codec and snd; refuses any call other than `--show-depends`), on a host where
      `/bin/sh` is dash. Output: `_: 1: resolve: not found` once per name, xargs warning that
      `--max-args` and `-I` are mutually exclusive, loop stops after one pass, closure = the three
      seed names only. `comm` then puts lz4_common, lz4_compress, snd and snd_hda_codec into
      block.list - the "Unknown symbol" failure the skill warns about.
- [x] Verify comment: `modprobe -n -v` dry run against a scratch base dir (`-d`, `-S`) and a
      scratch config (`-C`) holding the step-3 logger line prints
      `install /bin/sh -c '/usr/bin/logger -t modulejail "blocked: dccp" ...'`, not `/bin/true`
      as the comment claimed. The same with `install dccp /bin/true` prints `install /bin/true`.

## GREEN
- [x] The loop now calls `resolve` in the current shell through `while read -r m; ... done`,
      with no child shell and no `export -f`. Extracted verbatim from the edited SKILL.md and run
      under bash AND under dash against the same stub: both reach the full seven-name closure,
      and block.list holds only the two genuinely unneeded modules.
- [x] The `bash -c` variant (the alternative fix) also converges under bash; the `while read`
      form was chosen because it removes the child shell entirely, so it works whichever shell
      runs the block and needs no exported function.
- [x] Checked the rest of the procedure for a shell function passed through a child shell: the
      only other `sh -c` is the step-3 install line, which runs the external `/usr/bin/logger`.
      `xargs -rn1 basename` in `resolve` calls an external binary. No other instance.
- [x] Verify comment now says a blocked name dry-runs to an `install` line (the logger command,
      or /bin/true), never an insmod path.

## Quality
- [x] Present tense; no session narrative, no scratch paths in the skill.
- [x] Frontmatter unchanged; no table edited.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
