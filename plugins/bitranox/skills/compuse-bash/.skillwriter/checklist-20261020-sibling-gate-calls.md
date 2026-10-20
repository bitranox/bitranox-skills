# skill-writer checklist - compuse-bash (2026-10-20, two calls in one message are not a chain)

Two additions:

- a paragraph under "Why exit codes get misread": two calls in ONE message are not a chain, so a
  red or refused gate in the first does not stop a commit or push in the second; the two allowed
  shapes (one `&&` call, or the commit in the next message after reading the gate's exit code);
  the guard `block-commit-beside-sibling-gate` and its blind spot (a commit sent BEFORE its gate);
- a citation of that guard in the hooks section, renamed "Hook" to "Hooks" since it now lists two.

## PLAN
- [x] Receipt issued by the coordinator (`skill_receipt.py start meta-skill-writer`); this skill
      loaded by the editing agent before the first SKILL.md edit.
- [x] Skill type: technique/reference. Test: a retrieval scenario in which an agent would send a
      gate and a commit as two calls of one message, old text (RED) against new text (GREEN).
- [x] Scope: one paragraph and one citation line, plus the section heading. Frontmatter
      untouched, so no routing keyword moved and the description cap is unaffected. No table
      touched, so the markdown table formatter was not needed.
- [x] Every claim checked against the hook source, `plugins/bitranox/hooks/block-commit-beside-sibling-gate.py`:
  - [x] "each call is decided before any of them runs ... does not stop" - module docstring
        lines 4-7; refusal text lines 127-128.
  - [x] It refuses a commit, push or `gh pr create` - `is_gated_command` (docstring lines 15-16;
        early return line 147; `verdict` line 114); `shell_text.is_gated_command` docstring says
        "a git commit, a git push, or a gh pr create".
  - [x] ... when an EARLIER shell call of the same message runs a gate - docstring lines 16-17;
        `verdict` lines 112-116 over `siblings_for_event` (`transcript_siblings.py`, "The earlier
        shell siblings of the call").
  - [x] The gate must be the PROGRAM a statement runs, not text - `runs_a_gate` lines 96-109
        (`_program_at` skips launchers and assignments; a gate in a heredoc, quotes or as an
        argument does not count).
  - [x] Named gates (`make test`, `pytest`, `ruff check`, `pyright`, gate.py) - all match
        `shell_text.GATE_RE` (`make\s+\S*(?:test|check|lint)`, `pytest`, `ruff`, `pyright`) or
        `GATE_JIG_RE` (`gate\.py`); line 107. The list is examples, not the whole vocabulary
        (`GATE_RE` also holds mypy, tsc, bandit, cargo, go, npm, dotnet).
  - [x] The two allowed shapes - docstring lines 17-19; refusal text lines 130-132.
  - [x] "cannot see a commit sent BEFORE its gate" - docstring lines 29-30 ("probed on 2.1.296").
  - [x] Exit 2 on refusal (line 153); fail-open on bad stdin (lines 138-140) and on any error
        (lines 158-160). Not restated in the skill; recorded here as checked.
  - [x] "PreToolUse on Bash and PowerShell" - `hooks/hooks.json` matcher `Bash|PowerShell`
        (line 42) holds the registration (line 82). `hooks/tests/test_hook_docstring_registrations.py`
        reads the new citation and passes (47 passed).
- [x] ASCII only; no address, MAC, hostname or machine path added.

## RED (old text)
- [x] Scenario (inert text-only probe, opus; same excerpt of "Why exit codes get misread", "Never
      quirk an error" and the Hook section in both arms): an agent sends `make test` and
      `git add -A && git commit -F msg.txt && git push` as two Bash calls of one reply. Q1 safe?
      Q2 how instead? Q3 does anything stop call 2? The scenario does not name the trap.
- [x] Q1: governing line NONE ("No line covers two calls in one reply"); reasoned unsafe from
      "Run the critical command alone".
- [x] Q3: answered "Not according to the text" - the only named hook is the pgrep one.

## GREEN (new text)
- [x] Q1: not safe; quoted "Two calls in ONE message are not a chain: each call is decided before
      any of them runs, so a red or refused gate in the first does not stop a `git commit` or
      `git push` in the second."
- [x] Q2: one `&&` call or the commit in the next message; quoted "Put the gate and the commit in
      one call joined by `&&`, or send the commit in the next message after reading the gate's
      real exit code."
- [x] Q3: yes, the guard refuses call 2; quoted "`block-commit-beside-sibling-gate` refuses a
      commit, push or `gh pr create` sent after a gate call in the same message."

## REFACTOR
- [x] Both arms asked for a `Skill gaps` section; both lists recorded here.
- [x] GREEN gap declined - whether the hook is installed in a given session: the Hooks section
      names its registration; installation is the plugin's, not this skill's.
- [x] GREEN gap declined - whether the guard refuses call 2 even when the gate passes, and whether
      `git add -A` still runs: the refusal text the hook prints says "Nothing in this call ran",
      and the rule already tells the reader to chain or wait, which is right either way.
- [x] GREEN gap declined - that a single `&&` call passes the guard: the guard describes "an
      earlier call", and the paragraph prescribes exactly that form.
- [x] GREEN gap declined - reading `make test`'s exit code: the paragraph above says to run the
      critical command alone for a clean status.
- [x] GREEN diffed against RED in both directions: RED's `&&` and next-message answers both
      survive in GREEN; RED produced nothing GREEN lost.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No plugin version bump or CHANGELOG entry in this change (left to the coordinator).
