# skill-writer checklist - infra-swap-tuning (2026-09-27, rank 20)

Two defects in shipped snippets: a zram-generator.conf the generator refuses, and an idempotency
guard that fails open on a non-numeric `zram-size`.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Both defects are runnable snippets, so the RED/GREEN is an
      executed probe against the real tool (the generator binary, bash), not a pressure scenario.
- [x] Scope: correction only. The config and the guard keep their meaning; no procedure reshaped.

## RED
- [x] Behavioural RED not used: the skill is installed on this machine, so a subagent answers from
      the shipped wording, and the question is what the parser and the shell DO, which an
      execution answers directly. The ground truth below is immune to inherited context.
- [x] Config: zram-generator 1.2.1 built from its crates.io source with `--locked` (Cargo.lock pins
      rust-ini 0.18.0, no `inline-comment` feature) and run in generator mode against the skill's
      own `ini` block, extracted from SKILL.md, in a scratch root (`ZRAM_GENERATOR_ROOT` = fake
      mode: no modprobe, no hot_add, nothing under /etc or /sys). Result: exit 1,
      `Error: zram-size zram0 ... UnparsedTokensRemaining("# MB, uncompressed capacity; about 25%
      of RAM")`, zero unit files written. The `zram-size` line fails before `swap-priority` is
      even reached.
- [x] Guard: the skill's own bash block, extracted and pointed at scratch files, run per value
      with a mismatching disksize. `min(ram / 10, 2048)`, the old inline-comment line and a
      leading-zero `08192` each print an arithmetic error, exit 0, and leave `need_reset` UNSET
      (fail open). An empty or absent `zram-size` sets `need_reset=1`, which would reset on every
      run although zram-generator applies its default there.

## GREEN
- [x] Config: comments moved onto their own lines, plus a one-paragraph rule saying why. Same
      generator run: exit 0, writes `dev-zram0.swap` (`What=/dev/zram0`, `Priority=100`), its
      `swap.target.wants` link and the setup-service drop-in; the trace reads
      `Creating unit file dev-zram0.swap (/dev/zram0 with 16384MB)`.
- [x] Guard: a `case` refuses anything but a plain number with exit 2 before the arithmetic, and
      `10#` stops octal parsing. Same probe: 16384 vs a 16384 MB device leaves `need_reset`
      unset; 16384 vs an 8192 MB device sets it; expression, empty, absent and inline-comment all
      exit 2 with a message naming the value; `08192` vs an 8192 MB device leaves it unset.
- [x] Decision recorded in the text: refuse rather than reset. Skipping hides a changed size, and
      resetting on an unreadable value is the swapoff/reset the section warns destroys zram.

## REFACTOR
- [x] No subagent dispatched, so no Skill gaps list to work; the probe covered every input class
      the new text names (plain same, plain different, expression, empty, absent, leading zero).
- [x] Nothing lost against RED: the two plain-number cases give the same verdicts as before.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md` (no hits).
- [x] Frontmatter and description untouched.
