# skill-writer checklist - coding-python-rpyc (2026-08-27, audit findings)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. Every claim below was re-derived
from the INSTALLED rpyc 6.0.2 before anything was edited; the reviewer's quote was treated as a
claim, not as evidence.

Why a behavioural RED does not apply here: these are FACTUAL corrections to a reference skill, and
this skill is installed on the machine, so a subagent asked "what flag sets the registry log file?"
answers from the installed wording rather than from the file under test. The evidence is therefore
the executed ground truth - the real CLI, the real package metadata, the real source - which no
inherited context can fake. Each item below names the command and its output.

- [x] WRONG x10, each checked against the installed distribution:
      - `plumbum` was documented as optional ("None for core"). `importlib.metadata` reports
        `Requires-Dist: ['plumbum']` - unconditional, no extra and no marker - so `pip install
        rpyc` always installs it. Corrected in SKILL.md and, as an upstream-text note, install.md.
      - `rpyc_registry.py -f` / `--file` was documented as the log-file switch. The real CLI
        answers `Error: Unknown switch -f` (rc 2) and `Error: Unknown switch --file`; the switch
        is `--logfile`, with no short form.
      - `-q`/`--quiet` was documented as a bare toggle on the REGISTRY. It is a `SwitchAttr`
        there, so bare it fails `Error: Switch -q requires an argument`.
      - The same `-q` on `rpyc_classic.py` IS a bare toggle - the tool accepts it and starts the
        server. The two tools genuinely differ, so the classic table was left unchanged. Checked
        rather than assumed from the shared flag name.
      - `ThreadPoolServer` was documented as dropping connections once the pool is exhausted, in
        both the summary table and the servers doc. It queues them: `_active_connection_queue` is
        an unbounded `Queue.Queue()`, and `_drop_connection` is reached only from
        `_handle_poll_result` on an error or hangup event. Upstream's own `_accept_method`
        docstring claims an `AsynResultTimeout` "in case the queue is full", which an unbounded
        queue can never be.
      - `TlsliteVdbAuthenticator` was listed as an available authenticator in two files. It does
        not exist: `rpyc.utils.authenticators` exports `SSLAuthenticator` and
        `AuthenticationError` only, and a recursive grep for `tlslite` over the installed package
        returns nothing.
- [x] UNEXECUTABLE x2: the `rpyc_registry.py --listing` example is documented in two files and
      fails as written (`Error: Switch --listing requires an argument`). It takes a boolean, so
      both now read `--listing true`.
- [x] STALE x1: the monkey-patching example imports `telnetlib`, removed from the standard library
      in Python 3.13 (PEP 594) - `import telnetlib` raises `ModuleNotFoundError` on 3.13+. The
      example now states the version bound instead of failing silently on a current interpreter.
- [x] DANGLING x6, which is MORE than was filed and of a different kind. The report said the
      `_static` directory does not exist; it does. Four references were instead one level too
      high - `../_static/x.png` from inside `docs/`, where the image ships at `docs/_static/x.png`
      - and only `index.md`'s two were never vendored, so they now point at the upstream raw URLs
      (both verified HTTP 200, alongside an already-working URL as a control).
- [x] The previous artifact's claim "0 unresolved local links anywhere in the skill" did not hold:
      its check missed HTML `<img src=...>` tags and saw only Markdown link syntax. The resolver
      used now walks both, and is what found the four wrong-depth references. Re-run after the
      fixes: 74 local references resolve, 0 dangling.
- [x] Divergence from upstream is deliberate and recorded here, so a future re-vendor is a MERGE
      rather than a copy - re-apply this list, or re-run the audit after refreshing.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] No session narrative or private provenance; no machine paths; every value added is either
      measured output or an upstream URL.
- [x] Typographic tell scan clean over every changed file, with an em-dash control proving the
      scanner reports a positive.
