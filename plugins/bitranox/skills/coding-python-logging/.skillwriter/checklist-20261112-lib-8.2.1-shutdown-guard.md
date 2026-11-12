# skill-writer checklist - coding-python-logging (2026-11-12, lib_log_rich 8.2.1)

Edit: `SKILL.md` gains a paragraph under "The correct shape" (guard `shutdown()` in a CLI's
`main()`), and `runtime-and-integration.md` a subsection "A failed shutdown must not replace the
exit code" (the guard, what a failed shutdown leaves, how to test it). Twin of
`libs/lib_log_rich/skills/python-logging`, identical apart from the conventional divergences.
Frontmatter unchanged.

## PLAN
- [x] Skill type: reference. Test: RED as a retrieval probe on the pre-edit text, GREEN as the same
      probe on the edited text (opus, text-only baseline-probe agents, same CLI `main()` task).

## RED
- [x] Each claim checked against the running library first (lib_log_rich 8.2.0, a probe with a
      console sink stalled 3 s against `queue_stop_timeout=0.5`, arms interleaved ok/stall twice):
      a stalled `shutdown()` raises `RuntimeError: Queue worker failed to stop within the allotted
      timeout`; `is_initialised()` stays True; `init()` is refused; a retry at once fails, a retry
      4 s later succeeds and `init()` then works. `lib_log_rich.shutdown is
      lib_log_rich.runtime.shutdown` is True, and after patching `runtime.shutdown` the root name no
      longer matches (separate bindings), measured. The guard pattern was run as
      `examples/cli_exit_code.py` under an injected shutdown failure, guarded vs bare arms
      interleaved twice: guarded rc 0 with the warning and no traceback, bare rc 1 with a traceback.
- [x] RED probe (opus) on the pre-edit text: it ALREADY guarded `shutdown()` and kept the exit code,
      because the lifecycle table named the `RuntimeError` and the initialised-runtime state. So the
      baseline did not fail the core behaviour; its test plan was looser (no "call the real shutdown
      first", no `Traceback` assertion, binding chosen by luck).

## GREEN
- [x] Same probe on the edited text (opus): the guard by quote, exit code kept, runtime state and
      retry by quote, and the test recipe with the correct binding (`lib_log_rich.shutdown` patched
      because `main()` calls it), real shutdown first, `Traceback` asserted absent.
- [x] Gaps the probes raised and why they stay out: how click ends a run and which `RuntimeConfig`
      fields enable Graylog are outside this excerpt (other sections and files cover Graylog;
      click is not this skill's subject). Both probes added an `is_initialised()` check before the
      guarded call; the section already says to guard teardown with it when it may run twice.
- [x] Non-ASCII: none added. No added line over 120 characters. Frontmatter untouched.
- [x] `repo-gate.py --mirror-of <lib_log_rich worktree>` reports `in sync`.
- [x] No address, hostname or private path added.
- [x] Decisions: none - the edit records measured library behaviour and a guard the template
      already ships (bitranox_template_py_cli d087cfb); the RED result shows it sharpens existing
      guidance rather than reversing any earlier choice.
