# skill-writer checklist - files-edit-yml (layout no ruamel setting keeps)

- [x] Change: SKILL.md gains "When no setting keeps a line: edit that line, then compare the
      parse" (flow-sequence inner spaces, `lc.value` line-targeted edit, `safe_load` equality).
- [x] RED (text check): `grep -niE 'flow|\[ '` found no flow-sequence case; the reflow list named
      only indent, null spelling and width.
- [x] Run on ruamel.yaml 0.19.1: the unedited round trip with the skill's settings turns
      `branches: [ main, master ]` into `branches: [main, master]`; the emitter has no padding
      option for flow sequences (its only flow-sequence knob is
      `brace_single_entry_mapping_in_flow_sequence`).
- [x] The section's code block executed as written against a workflow file: only
      `timeout-minutes` changed, `[ main, master ]` kept, `safe_load` equality held;
      `lc.value("timeout-minutes")` gave (6, 21), `seq.lc.item(0)` gave (8, 8).
- [x] GREEN quote-back: "Let ruamel FIND the line, change only the value on it, and prove with a
      parser that nothing else moved".
- [x] Description: unchanged.
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
