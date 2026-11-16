# skill-writer checklist - process-debug-systematic (20261116, earlier runs as a peer in time)

- [x] Decisions: d-20261116-30e1ec36

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill; no entry
      touched.
- [x] Premise check: the working-peer material (Phase 2 step 1, "Diff a working peer before
      calling a fault external") compared only against a comparable HOST; nothing named the same
      system's earlier runs. Not covered, so the lesson ships, generalised from boots to earlier
      CI runs and older logs, keeping the boot example.
- [x] RED: text-only probe (`bitranox:baseline-probe`, `opus`) over the pre-edit excerpts asked
      what to check before a lasting ordering fix after one bad boot, and whether the text says
      anything about earlier runs of the same system. Answer: NONE for earlier runs ("The excerpt
      only ever compares against a comparable host"). The probe inferred "read earlier boots" on
      its own; the always-loaded memory index carries a related lesson (a constant cannot explain
      an intermittent fault), so the behavioural answer is contaminated and the text check (NONE)
      is the evidence.
- [x] GREEN: same question over the new text, `opus` and `haiku`, 2 cells. Both quoted "the same
      system's earlier runs are a working peer in time" and the read-earlier-boots sentence.
- [x] Gaps from GREEN, decided: the text could read as advising against declaring a genuinely
      missing dependency (closed: "find it, and do not present the ordering change as its fix");
      no earlier run kept (closed: "say the cause is unproven"); how many earlier runs are enough
      and what "usual margin" means (declined: judgement that depends on the system).
- [x] Re-probe of the touched sentences on the final text, `haiku`: quoted "find it, and do not
      present the ordering change as its fix" and "If no earlier run was kept, say the cause is
      unproven."; no new undecided gap (whether to ship an ordering change as a hypothesis is left
      to Phase 3, which already governs testing a hypothesis).
- [x] Width and fence check over the added lines printed nothing; ASCII only; no description
      change.
