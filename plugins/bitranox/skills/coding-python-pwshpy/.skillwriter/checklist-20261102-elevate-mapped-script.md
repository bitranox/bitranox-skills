# skill-writer checklist - coding-python-pwshpy, mirror of using-pwsh (elevate refuses a script on a mapped drive, [420])

- [x] Rule: on Windows `elevate()` raises `ElevationDirectoryError` before any prompt for the script of a
      `python Z:\tool.py` start when `EnableLinkedConnections` is not set. With the policy set and a reboot since,
      the script runs; set without a reboot, it gets the prompt and returns 2. A console-script `.exe`, or a
      `python.exe` running a local script, on the drive is not refused. A caller's own `argv` is not judged.
      Where: SKILL.md, the `ElevationDirectoryError` bullet and the exit-code paragraph (70).
      Backed by: src/pwshpy/adapters/native/elevation.py (`refuse_a_script_the_child_cannot_open`,
      `_script_being_relaunched`, `_linked_connections`).
- [x] Each stated behaviour executed on a throwaway Windows 11 guest with a real UAC consent from a non-elevated
      caller, against a share on the same machine: script on the drive, policy unset: refused, no prompt; started
      by its UNC path: rc 42; the CLI: exit 70 and the `pwshpy: cannot elevate:` line; policy set, no reboot: prompt,
      rc 2; policy set and rebooted: rc 42; console-script `.exe`: rc 42; interpreter on the drive with a local
      script: rc 42 (policy unset and set). A share on another machine is not measured, which is why the text says
      the elevated account must be able to reach it.
- [x] Receipt held (skill_receipt.py start meta-skill-writer before the first edit).
- [x] `redcheck --corpus-cascade` not used as the evidence: RED is a coverage check against the pre-edit text
      (`git show HEAD:skills/using-pwsh/SKILL.md`), pasted to a tool-less probe told not to load a skill.
- [x] RED, opus, pre-edit text, 7 questions: question 1 quoted "is not refused: it gets the prompt", now false; the
      other six answered NONE.
- [x] GREEN round 1, opus and haiku, same 7 questions: every answer correct and quoted. Tiers haiku and opus, one
      cell per question per tier.
- [x] Skill gaps from round 1 closed in the text: "before any prompt" for the script case, the policy set without a
      reboot, and a `python.exe` with a script also on the drive (the exemption now says "running a local script").
- [x] GREEN round 2, opus and haiku, 5 questions on the changed sentences: every answer correct and quoted, no NONE.
      Round 2 reported no gap in the changed sentences that needs text.
- [x] Declined, with reasons:
      - whether the policy lifts the directory refusal: stated in docs/power-tools.md, "with or without
        `EnableLinkedConnections`"; both tiers read the bullet that way.
      - how to set the policy or tell whether a reboot happened: Windows administration, not this library's surface.
      - the exit code of a wrapper script that catches the error: the caller's own code decides it.
      - a non-`net use` mapping: the code asks `WNetGetConnection`, the bullet's term is the one the docs use.
      - wait=False after the prompt: the bullet's rule on `wait` is the elevate signature, documented with it.
- [x] GREEN against RED in both directions: nothing the old text answered correctly is lost; the one sentence it
      answered with is replaced.
- [x] Decided beyond the reported defect: a value that cannot be read counts as set (the refusal stands only on a
      policy known to be unset). The skill text does not state it; docs and the docstring carry it.
- [x] Description unchanged (frontmatter not edited). Width: added prose wraps at the 118 columns of the surrounding
      bullet rather than 100, keeping the bullet uniform; fences unaffected.
- [x] Review round: "a caller's own `argv` is not judged" was false for `elevate(argv=sys.argv)`, which is the same
      relaunch and is refused. Reworded to "an `argv` that differs from `sys.argv`", pinned by a test, and `python -m`
      named as not judged. The sentence states what the code does; no new behaviour, so no third probe round.
- [x] ASCII only, present tense, no private host, address or path added; `Z:\tool.py` is an example path.
