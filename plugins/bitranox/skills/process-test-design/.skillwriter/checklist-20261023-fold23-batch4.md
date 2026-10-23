# skill-writer checklist - process-test-design (fold of memory rules into the skill)

- [x] Change: ## Determinism and environment -> new ### A check-then-open race: make `stat` answer
      for another file (after 'Pin the environment an output premise depends on'). Verified against
      ground truth: Path subclass needed before 3.12 -> ran sub.py under uv CPython 3.10/3.11: 'Path
      subclass FAILS: AttributeError ... _flavour'; 3.12 'Path subclass OK'; `type(fifo)` subclass
      OK on all three. Whole technique -> scratchpad race.py: load_buggy refuses a direct FIFO
      ('refused') but hangs on Swapped(fifo); load_fixed (os.open O_RDONLY|O_NONBLOCK + os.fstat
      S_ISREG) refuses both. Signal-based timeout interrupts plain join() -> race.py: SIGALRM
      handler raising TimeoutError interrupted t.join() after 2.0 s; finally with os.open(fifo,
      O_WRONLY|O_NONBLOCK) released the blocked reader ('thread alive: False').
- [x] Change: new ## Damaging the installed package: run a copy, with an intact copy as control
      (directly after the Windows permission-wall section, before 'Prune low-value tests'). Verified
      against ground truth: PYTHONPATH at the copy's parent -> a package dir is importable from its
      parent directory (standard import semantics). -m prepends cwd -> sys.path of a plain
      interpreter starts with '' (printed from /usr/bin/python3 and a venv: ['',
      '/usr/lib/python314.zip', ...]); documented for -m/-c. -I ignores PYTHONPATH -> CPython
      isolated mode (skeptic note). Fits existing rules: 'Prefer real over mocked' and checklist
      line 'A test that builds a precondition ... asserts it holds before relying on it' (the RED
      quote; this text adds only the missing technique).
- [x] Change: ## Per-language mechanics - new paragraph directly after the per-language table,
      before 'Mark the tiers'. Verified against ground truth: Existing coverage only for Bash ->
      SKILL.md table row 'a stub binary earlier on `PATH`' (RED quote; this generalises it).
      Compatible with references 'Patching `pkg.mod.subprocess.run` patches every caller in the
      process' (prefer injecting the runner). monkeypatch.setenv changes os.environ of the parent,
      so a child spawned without env= inherits the prepended PATH (skeptic analysis, consistent with
      POSIX execvp). Windows: CreateProcess appends .exe to an extension-less name and falls back to
      the parent's PATH (documented Win32 behaviour; not run here), consistent with the tree-level
      rule to resolve argv[0] with shutil.which(name, path=PATH).
- [x] Change: references: ### Pin the environment an output premise depends on (new paragraph);
      SKILL.md: ## Deterministic and order-independent, first bullet. Verified against ground truth:
      _pytest/monkeypatch.py:294-306 (installed pytest): delitem appends to self._setitem only in
      the else branch (key present); absent key with raising=False does nothing. :328-335 delenv
      calls delitem on os.environ. setenv records the original (NOTSET when absent), so the
      setenv-then-delenv sequence restores to absent at undo (skeptic CONFIRMED from same source).
      Reconciled with the existing reference text that prescribes 'monkeypatch.setenv / delenv' (it
      now carries the absent-variable caveat right below it).
- [x] Change: ### Pin the environment an output premise depends on (COLORTERM added to the variable
      list; new paragraph on spawned children). Verified against ground truth: rich/console.py
      (installed rich in a project venv): :793 `if not self.is_terminal or self.is_dumb_terminal:
      return None`; :987 `is_dumb = _term.lower() in ("dumb", "unknown")`; :805-810 COLORTERM
      truecolor/24bit -> TRUECOLOR, otherwise TERM suffix lookup defaulting to ColorSystem.STANDARD
      (so an unset or unrecognised TERM still colours); :964 FORCE_COLOR read. COLORTERM is read by
      rich (:805), so adding it to the list is correct.
- [x] Change: ## Gates and guards -> new ### A "did it run" marker the platform can silence (after
      'An environment-isolation test must expect what only the right repository holds'). Verified
      against ground truth: ls: /usr/lib/python3.11, 3.13 and 3.14/sitecustomize.py exist on a
      Debian-family host. Experiment in scratchpad: venv from /usr/bin/python3 with sitecustomize.py
      + planted.pth in its site-packages -> `import sitecustomize; sitecustomize.__file__` =
      /usr/lib/python3.14/sitecustomize.py, only marker_pth written (sitecustomize marker never
      fired); with `-S` no marker at all. Venv sys.path = ['', '/usr/lib/python314.zip',
      '/usr/lib/python3.14', '/usr/lib/python3.14/lib-dynload', '<venv>/site-packages'] (stdlib dir
      before site-packages). Venv `site.ENABLE_USER_SITE` -> False (usercustomize never runs).
- [x] Change: ## Determinism and environment -> new ### A blocking stub must `exec` its blocker
      (after the check-then-open race entry). Verified against ground truth: Scratchpad stub.py: a
      Python 'tool' running the stub via subprocess.run(['dash','-c', ...]) and receiving SIGINT;
      test blocked on open(fifo).read() as the start event, then communicate() with no timeout ->
      'sleep 5': returned after 5.02 s; 'exec sleep 5': 0.32 s. Shell behaviour: `dash -c 'touch m;
      sleep 3'` -> comm=dash with child sleep (forks); `bash -c '...'` -> comm=sleep, no child (bash
      5.3.9 execs the last command). Real-world shape: a public tool's test uses `touch <marker>;
      exec sleep 30` with an in-code comment that the killed process is then the sleep itself, and
      skips on win32 because 'a parent's terminate() is TerminateProcess on Windows'.
- [x] Added after review: a test that enumerates repository files asks git (`git ls-files -z
      --cached --others --exclude-standard`, NUL split, skip paths gone from disk); the FIFO cleanup
      is guarded with `thread.is_alive()` plus an ENXIO catch; the forced fix refuses a non-regular
      file after `fstat`.
- [x] Claims the source contradicts were dropped or corrected; machine-local figures, private names
      and incident history were not carried over.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against the pre-edit snapshot (NONE for scenario 1;
      partial for scenario 2; partial for scenario 3; partial for scenario 4; partial for scenario
      5; partial for scenario 6; partial for scenario 7). Only a verbatim quote from the snapshot
      counts, so context inherited from this machine cannot satisfy it; redcheck --corpus-cascade
      was not run.
- [x] GREEN quote-back on haiku and opus against the edited files, in four rounds: after the edit,
      after the first review's fixes, after the delta review's fixes, and a final round on the
      questions the last fixes touched. Every scenario was answered with a quote from the new text
      on both tiers in every round; no NONE.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or recorded below.
- [x] Gaps closed or declined: closed - ENXIO-safe cleanup, refuse a non-regular file after fstat,
      the exact git enumeration flags (each re-tested by quote-back on haiku and opus, all quoted);
      declined - a project with no per-test timeout (SKILL.md already says to configure one
      suite-wide), a Windows shape for the FIFO race (FIFOs are POSIX; the section is scoped to
      them), the unreadable arm under root or Windows (the existing permission-wall section owns
      it), how the elevation check is forced for the sudo stand-in (the code's own seam, outside the
      stand-in rule), how the Swapped instance reaches the loader (the code's seam), a daemon thread
      left blocked after an ENXIO skip (a daemon thread ends with the process), clearing O_NONBLOCK
      after the fstat (a detail of the fix).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, repo file paths or reserved examples.
