# skill-writer checklist - coding-data-architecture (2026-11-09, new generic skill)

A new language-neutral data-architecture skill. Its rules come out of the Python skill (now
`coding-python-data-architecture`): Core Principles 1-7 stated without Pydantic, "validated type
or plain record", the anti-pattern list in prose, "declare what the consumer must distinguish",
"ask the tool, do not re-derive its choice", define-the-types with its preference order, the
Instructions checklist, the Workflow (state file, SCOPE via git blame, partitioned parallel
analysis and refactor, reproduce claims, error-surface diff, final verify), the generic
rationalization rows and the execution summary. A "Route by language" table sends Python to
`coding-python-data-architecture` and Rust to `coding-rust-data-architecture`.

Decisions: d-20261109-06f0b30f

- [x] Receipt started (`skill_receipt.py start meta-skill-writer`), skill loaded via the Skill tool.
      Step 0b: the skill is new and has no ledger; the source skill's `show --kind rejected,removed
      --full` printed nothing.
- [x] Not mirrored: the skill is new and ships only from this marketplace.
- [x] Skill type: discipline plus technique; the test is an application scenario under pressure:
      a TypeScript handler with `Record<string, any>`, string status and mode, a lead asking to keep
      plain strings "so old clients still work" and ship in 20 minutes. Four questions: what to
      change, keep a both-forms layer, how to verify malformed-request behaviour, the deadline.
- [x] RED (opus, baseline-probe, no skill): strong. It types the boundary, refuses a both-forms
      layer ("`"loyal" | "new" | string` collapses to plain `string`"), builds a golden-master
      matrix and proves the diff can fail. It differs from GREEN in two places: it compares
      against one recorded release only, and on the deadline it recommends "release as-is ...
      Then write the rest into the backlog as concrete items", where GREEN refuses a ticket and
      asks. Recorded as a near-tie; the scenario was not escalated.
- [x] GREEN opus (skill file read, Skill tool forbidden): typed `Order`, string enums whose wire
      form is the old string, parse at the handler, no shim (quotes Principle 7), STEP C item 5
      with two baselines and a liveness control, deadline put to the lead quoting "that trade is
      the HUMAN's to make", "Finish the rest next sprint is refused as a ticket", route table
      quoted "anything else | nothing: this skill alone".
- [x] GREEN haiku (same prompt): same five answers with quotes, including "Converting under
      deadline pressure is riskier ... the HUMAN's to make" and the liveness control.
- [x] Skill gaps reported by GREEN, decided:
  - Input the old code ACCEPTED and the boundary now refuses (both tiers): CLOSED, STEP C item 5
    now says it is a change listed the same way.
  - "Exit code" over HTTP (both tiers): CLOSED, the TYPE bullet names an HTTP status.
  - "The language skill" supplies gate, greps and own-code proof, but TypeScript has none (opus):
    CLOSED, a paragraph under the route table says to take each from the project itself.
  - No TS validation library, enum versus literal union, TS checker spellings: DECLINED, language
    mechanisms belong to a language skill; Go and TypeScript skills are out of scope in the plan.
  - No small-scope path for a one-function change: DECLINED, judgement the skill leaves open; the
    workflow is the same in the source skill.
  - Deadline rows "ask the human" and "never a ticket" could conflict: DECLINED, both rows are the
    source skill's pressure-tested text, unchanged in meaning.
  - Money rounding, echoed unknown keys, full status set: DECLINED, outside data architecture.
- [x] Quote-back: every GREEN answer quoted a line that is in the file (checked by grep for
      "the HUMAN's to make", "No compatibility shims", "anything else", "an arm that silently
      imports the working tree").
- [x] Re-probe after the fixes: the three closing edits were checked by text (grep finds "the old
      code ACCEPTED", "an HTTP STATUS", "take each from the project itself"); no new probe was run
      on the final text, recorded here as a limit.
- [x] Tiers and cells: RED opus x1, GREEN opus x1, GREEN haiku x1 for the generic scenario.
- [x] Description: starts "Use when", triggers only, 457 characters measured with `len()` through
      `skill_frontmatter.description`. Routing is a text check only (keywords: dict or map
      parameters, raw JSON values, stringly-typed status, Model->dict->Model, bare tuples,
      compatibility shims); a live routing answer cannot be taken where the old skill is installed.
- [x] Width and fence check: no prose line over 100 columns past the front matter, 5 fences all
      closed, no non-ASCII byte.
- [x] History-phrase finder ran over the skill dir; its three hits ("since v2.0.0" as a request
      example, "used to refuse", "used to fall through") describe behaviour, not history.
- [x] No address, hostname or private path added (grep for IPv4, /home/, /Users/, /tmp/ empty).
- [x] Generated artifacts rebuilt in the same change: `build_skill_triggers.py`,
      `build_skill_docs.py`, README and docs/installation.md counts 85 -> 86.
- [x] Security review of the diff: documentation and one test; no secrets, no commands that run on
      untrusted input.
