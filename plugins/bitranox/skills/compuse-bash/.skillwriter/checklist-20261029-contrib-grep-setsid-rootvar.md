# skill-writer checklist - compuse-bash (three quick-reference rows)

- [x] Change: rows "A grep for a whole sentence in hard-wrapped prose ... finds NOTHING",
      "An absolute path built from a variable", "`setsid cmd > log; echo RC=$?`".
- [x] Mechanism claims measured in a throwaway shell: `grep -c 'the gate reads the index'` printed
      0 on a two-line file holding the sentence split after "gate"; `grep -c 'reads the index'`
      and the `tr -s '[:space:]' ' '` join both printed 1. `R=""; ls -d $R/etc/hostname` listed
      the local /etc/hostname; `: "${R:?root is empty}"` exited 1. In the Bash tool shell (`$-` =
      `hmtBc`, job control on) `setsid sh -c 'sleep 2; exit 7' > log; echo RC=$?` printed RC=0
      after 0.004 s with nothing written and the child's file appeared later; `setsid --wait`
      gave RC=7 after 2.0 s; inside `bash -c '...; ...'` (not a group leader) setsid waited (7).
- [x] RED text check: `tr -s` 0, `setsid` 0, `${R:?` 0 in origin/master's SKILL.md.
- [x] GREEN quote-back: "Before concluding "missing", search a SHORT fragment that cannot span a
      line"; "Guard the variable before the first use: `: "${R:?root is empty}"`"; "Pass
      `--wait` (`-w`) when you want the command's real exit status".
- [x] Description: unchanged (265 chars).
- [x] Table re-padded by the formatter; every row has two cells (unescaped-pipe count checked).
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
