# skill-writer checklist - process-debug-systematic (20261109, outage trigger, discriminating test before approval)

Queue entries: A13.

- [x] Decisions: none - additive rules from queued items; no ledger rule was reversed or removed

- [x] Step 0b: `show --kind rejected,removed --full` read for this skill; no entry touched.
- [x] RED by text check against the pre-edit text (`git show HEAD:`): every distinctive phrase of
      the added rules was absent there (listed below). No behavioural RED: the session's always-
      loaded memory index states several of these lessons, so a probe could not fail honestly; the
      coverage check against the skill file is the evidence.
- [x] Phrases checked: "nearest rival", "outage".
- [x] GREEN: quote-back probe over the pasted new text, 27 scenarios covering every added rule,
      `opus` at effort `medium` and `haiku`, 2 cells. Both tiers answered every scenario with a
      direct quote of the governing sentence, none NONE. Two scope controls (a different defect
      class; a child process that needs no version-specific dependency) were both correctly outside
      the new rules, so the rules do not over-trigger.
- [x] Router replay over 1216 typed prompts for four candidate descriptions: the current one chosen
      ('... unexpected behavior or outage') fired 0 times against 0 for the old text; the
      alternatives naming service, fleet, deploy or restart fired 1, 3 and 9 times, all noise (a
      prompt saying deploy and test). The body's When to Use line carries the fleet-after-a-change
      case instead.
- [x] Gaps from GREEN: 'cheapest test' gives examples only (a judgement that depends on the system).
- [x] Width and fence check over the added lines printed nothing new beyond this file's own long
      lines; ASCII only; frontmatter parses with a YAML loader and its description is under 1024.
