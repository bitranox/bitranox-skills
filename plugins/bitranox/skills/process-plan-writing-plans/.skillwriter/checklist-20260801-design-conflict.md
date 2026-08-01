# skill-writer checklist - process-plan-writing-plans (2026-08-01, design conflict resolved)

Source: a design conflict surfaced by the clean-room sweep and decided by the operator, one at a
time, on the verbatim text of both sides. Ships with plugin 5.133.0.

- [x] CONTRADICTION: the Capability check offered to "delegate the design/decomposition (or a
      critical self-review pass) to a pinned sonnet/opus subagent", while the Self-Review section
      states "This is a checklist you run yourself, not a subagent dispatch." A reader on a weaker
      tier was told both to delegate the self-review and never to delegate it.
- [x] DECIDED: self-review is never delegable. The Capability check now offers delegation for the
      design/decomposition only, and says WHY the review is different - it is a fresh-eyes pass over
      the plan you just wrote against the spec, and a subagent that never watched the plan take
      shape cannot know what was considered and rejected.
- [x] The cost of the choice is stated rather than hidden: a genuinely weak session now self-reviews
      with the same judgement that wrote the plan, which is the case the delegation clause existed
      for. The remaining escape hatch is switch-model-or-continue.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Both sides were quoted verbatim to the operator before the choice; the decision is theirs and
      the reasoning is recorded here rather than inferred later from the diff.
- [x] No session narrative or private provenance added; no machine paths added.
