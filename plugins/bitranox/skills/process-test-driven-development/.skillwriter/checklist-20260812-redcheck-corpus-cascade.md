# skill-writer checklist - process-test-driven-development (2026-08-12, redcheck --corpus-cascade)

Change: `redcheck.py` gains `--corpus-cascade DIR`, which assembles the always-loaded context an
agent dispatched in DIR inherits (every `CLAUDE.md` and `CLAUDE.local.md` from DIR up to the
filesystem root, plus every memory fact body under a `.claude-memory/facts/` on that chain) and
hands it to the existing inherited-coverage check. `--corpus-cascade-top` bounds the walk to a
fixture tree; `--rarity-max-fraction` exposes the corpus-shape cutoff. The verdict now reports how
many documents it read, states that an inherited hit is STRONG and a clean result WEAK, and treats
a zero-document corpus as its own outcome (`unchecked`, exit 3) rather than a quiet pass. The
SKILL.md redcheck section documents the mode, the exit table and the asymmetry.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. This edit is to the tool section of an existing skill,
      not a new skill.
- [x] Not a new section. The redcheck section already existed and already named "the config
      cascade" as an intended corpus; what was missing was anything that ASSEMBLES it, so the
      enumeration was being redone by hand each time.
- [x] NO BEHAVIOURAL RED WAS STAGED, and the reason is the rule this tool enforces: the lesson
      (inherited context voids a behavioural RED) is already in this machine's always-loaded index
      AND, since 5.196.0, in the skill text itself, so a behavioural arm on it cannot fail
      honestly. Declared route: the evidence is a CODE red-green cycle plus a mutation check,
      neither of which an agent's inherited context can forge.
- [x] RED OBSERVED, unfiltered, no `-k`: 12 failed / 16 passed on the first run, every failure a
      missing feature (`module 'redcheck' has no attribute 'load_cascade_corpus'`, `audit() got an
      unexpected keyword argument 'require_corpus'`, `'Audit' object has no attribute
      'corpus_documents'`, `KeyError: 'inherited_evidence'`, argparse rejecting
      `--corpus-cascade`), never a typo or an import error. GREEN: 32 passed.
- [x] A SECOND RED, found by running the finished tool on real content rather than by reasoning:
      over a live 608-document cascade the rarity cutoff filtered out every one of the 16 terms the
      scenario shared with the fact that teaches it, so the tool reported CLEAN on a lesson sitting
      in the corpus. Measured: lesson-carrying terms occupy roughly the 1 to 5 percent
      document-frequency band, boilerplate sits at 36 and 54 percent, and the shipped cutoff of 1
      percent sat below the entire signal band. Cutoff moved to 5 percent, between the two bands,
      and exposed as `--rarity-max-fraction`.
- [x] The fixture for that second RED was caught being VACUOUS before it was believed. The first
      version passed at the old cutoff, because it left some shared terms at one-document
      frequency and those survive any cutoff. Rebuilt so every shared term sits in the measured
      band, which reproduced the real miss (`inherited: []`), and a guard test now fails if any
      term drifts back to a frequency the narrow cutoff would have admitted.
- [x] VACUITY CHECK on the whole set: 12 mutations applied to a COPY of the skill, each
      reintroducing the exact defect one test claims to guard - walk stops at the start dir,
      enumeration made gitignore-aware, decode error made fatal, empty corpus reported clean,
      memory bodies not collected, clean run claiming strong evidence, caveat text dropped, help
      hiding the memory store, cascade mode disabled, cutoff back below the signal band, rarity
      gate disabled entirely, and the fixture guard itself. 12 of 12 detected, 0 absorbed.
- [x] GITIGNORED FILES PROVEN INCLUDED, with a control: the test inits a real git repo, ignores
      the fixture `CLAUDE.local.md`, requires `git check-ignore` to exit 0 (so the file is really
      ignored and the test cannot pass vacuously), then requires it in the assembled corpus. The
      matching mutation makes enumeration gitignore-aware and that test alone goes red.
- [x] DETECTOR SEEN SAYING BOTH ANSWERS on real content, not only in fixtures: a scenario about a
      lesson this machine's context carries came back exit 1, naming the memory fact body and the
      pointer block that teach it; an unrelated scenario over the same 608-document corpus came
      back exit 0; a mistyped start directory came back exit 3 with `corpus_empty: true`.
- [x] CLEAN IS DECLARED WEAK in both output paths, because the tool must not imply a guarantee it
      cannot make: the text render and the JSON envelope both carry `inherited_evidence` saying a
      hit is strong and names the file, while a clean result means NOT CAUGHT rather than absent,
      since term overlap cannot see a paraphrase. Two mutations (strength hardcoded, caveat text
      dropped) prove that claim is tested and not decorative.
- [x] Zero-document corpus is loud and distinct, never a quiet clean: its own verdict
      (`unchecked`), its own exit code (3), an explicit `corpus_empty` boolean, a stderr warning,
      and a document count printed on every run.
- [x] Enumeration is a filesystem walk with direct reads, never a search tool, and the docstring
      says why: project `CLAUDE.md` files and memory stores are routinely gitignored, so a
      gitignore-aware search returns a small corpus in which everything looks clean.
- [x] Installed plugin skills DECLINED rather than guessed. Their on-disk location depends on the
      reader's plugin cache and installed versions, so a built-in path would report a falsely
      clean corpus on someone else's machine. SKILL.md says so and points at `--corpus` instead.
- [x] No path from this machine is hardcoded anywhere in the tool or its tests. Every fixture is
      built under `tmp_path` and bounded with `--corpus-cascade-top`, so no test reads the cascade
      of whatever machine runs it.
- [x] Cross-platform: no bare `python3` (tests spawn `sys.executable`), every read is explicit
      `encoding="utf-8"`, a decode error skips one file with a reported warning instead of killing
      the run, and the walk uses `Path.parents` rather than string splitting.
- [x] House CLI contract kept: `--json` envelope with `ok`/`command`/`data`/`skipped`, warnings to
      stderr only so stdout stays parseable, typed errors (a `top` that is not an ancestor raises
      `ValueError` and exits 2 with a JSON envelope, not a traceback), format-independent exit
      codes.
- [x] EXISTING BEHAVIOUR UNCHANGED: all 16 pre-existing tests stayed green throughout. The
      `unchecked` outcome is scoped to the new mode, so `--corpus <empty dir>` still exits 0 as
      before.
- [x] Token budget: the SKILL.md section grew by the mode, a four-row exit table and the
      strong-versus-weak paragraph; the mechanics stay in `--help` and the module docstring.
- [x] Frontmatter description unchanged, so the generated skill docs need no new description text.
- [x] No session narrative, no memory-fact slug and no machine path in the skill text. The
      measured corpus shape is described generically in a source comment as the WHY behind the
      cutoff; the specifics live in this artifact only.
- [x] No addresses, MACs, hostnames or machine paths added.
