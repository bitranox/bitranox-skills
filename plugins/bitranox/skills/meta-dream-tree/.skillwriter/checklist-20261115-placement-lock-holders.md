# Checklist 2026-11-15: placement-lock holders in step 5

One paragraph in `SKILL.md` step 5 changes. The list of verbs that hold the tree's placement lock
now also names `topics-set-list`, `set-level-topics` and `set-top-topics`, which take the lock
(`memory_engine.set_topic_list`, `set_level_topics`). It names the three verbs that have a dry run
(`set-topics`, `render-topics`, `reconcile_memory_index.py --archive`) and says a dry run takes no
lock. It also says the lock-busy error names the lock file and the age at which a crashed holder's
lock is reclaimed. The engine's lock-busy message and `references/memory-backend.md` that quotes it
now name `set-top-topics` among the possible holders.

- [x] Step 0b: `skill_decisions.py show meta-dream-tree --kind rejected,removed --full` read; the
      two rejected entries (ref-map-after-dropped-move, rederive-batch-after-scratch-review) are
      unrelated to this edit.
- [x] Decisions: none - a factual correction of the lock-holder list and the dry-run scope to
      match the engine; no rule is added, removed or reversed.
- [x] Claims checked against the code before probing: `placement_lock(anchor, "topics-set-list")`
      in `set_topic_list`, `placement_lock(anchor, "set-top-topics" if top else
      "set-level-topics")` in `set_level_topics`; `--dry-run` exists only on `set-topics`,
      `render-topics` and `reconcile_memory_index.py` (argparse), and `archive_entry` uses a null
      context for a dry run; `PlacementLockBusy` prints the lock path and the reclaim age.

## RED (pre-edit paragraph, text-only baseline-probe, quote or NONE)

- [x] Do `topics-set-list`, `set-level-topics`, `set-top-topics` hold the lock: opus NONE x3,
      haiku NONE x3. Both noted "every write that could change a placed line" might cover them
      but would not apply it without knowing what the verbs do.

## GREEN (edited paragraph, opus and haiku)

- [x] Round 1: both tiers quoted the new sentence for all three verbs and the retry rule.
      Opus added "a dry run of any of them takes no lock", a claim the text then implied but the
      code does not support (the three have no `--dry-run`). Both tiers asked how stale a lock
      must be before it is reclaimed.
- [x] Round 2 (after naming the dry-run verbs and the reclaim): both tiers quoted the dry-run
      sentence and answered that `set-top-topics` has none; both quoted "never delete the lock
      file" for a suspected crashed holder and found the reclaim age in the error.
- [x] Round 3 delta: "and it takes none" was read as ambiguous by both tiers; reworded to "a dry
      run takes no lock". The width and fence check over the added lines printed nothing.

## Gaps declined

- How to tell when the other session has finished, and a retry bound: the text says to run the
  verb again once the holder finishes; the engine reclaims a crashed holder's lock by age, which
  the error prints (`PlacementLockBusy` in `hooks/memory_engine.py`). Judgement left open.
- Whether exit 2 means only a lock timeout: exit 2 is the engine-wide `! error` code, covered in
  `references/memory-backend.md`; out of scope for this paragraph.
- How to tell whether a fact is bound or the tree has a topic list: covered elsewhere in step 5
  and in `references/memory-backend.md` (`set-topics`, `topics-show`).
