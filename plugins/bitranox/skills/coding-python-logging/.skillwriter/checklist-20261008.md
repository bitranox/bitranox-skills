# skill-writer checklist - coding-python-logging (2026-10-08, lib_log_rich 6.4.x)

New reference/hub skill for lib_log_rich: SKILL.md plus four distilled reference files
(configuration, sinks-and-deployment, runtime-and-integration, dumps-and-cli). Twin of
`libs/lib_log_rich/skills/python-logging`, identical apart from the `name:` line.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/hub. Test: ten application questions (systemd thresholds, Windows Event
      Log, Graylog TLS and UDP, secret scrubbing, config reload, stdlib bridge, lost lines at exit,
      container stdout, crash dump, multiprocessing), answered without the skill (RED) and from the
      skill files only (GREEN), model pinned to sonnet.
- [x] Scope: hub SKILL.md with a two-tier routing table (distilled file, upstream doc on the default
      branch) and four reference files; no bundled scripts.

## RED (no skill)
- [x] `redcheck --corpus-cascade` flagged the always-loaded memory index and the repo CLAUDE.md;
      the shared terms are vocabulary (console, journald, graylog, configuration), not the API
      facts asked for, so the behavioural arm stands. Contamination recorded: the probe's own
      git-log context named `validate_config`, so question 5 does not count for RED.
- [x] RED guessed or did not know: the console stream variable (`LOG_CONSOLE_STREAM_TARGET`, wrong),
      the journald and Event Log dependencies, what TLS over UDP does, the endpoint type, the scrub
      pattern shape, `dump()` parameter names, preset names, the platform guards, any
      multiprocessing support, and why a forked worker logs nothing.

## GREEN (skill files only)
- [x] All ten answered with quoted skill text: env file for systemd, platform guards, Graylog
      tuple vs `HOST:PORT`, TLS refusal, `scrub_patterns={"api_key": r".+"}` and its limits,
      `validate_config` reload, `attach_std_logging`, `shutdown()` in `finally`,
      `LOG_CONSOLE_STREAM=stdout`, the crash-dump recipe, spawn plus per-process `init()`.
- [x] The probe read only the five skill files (six tool calls, no commands).

## REFACTOR
- [x] Every dispatch asked for a `Skill gaps` section; each list is worked below.
- [x] Closed: systemd console/journal split (stderr is copied into the journal; set
      `LOG_CONSOLE_STREAM=none` or accept duplicates) and the deploy example now matches it.
- [x] Closed: reload snippet re-fetches loggers after `init()` (old proxies keep the old runtime),
      catches `RuntimeConfig` construction errors (pydantic `ValidationError` is a `ValueError`),
      and moves the restart out of the signal handler.
- [x] Closed: `propagate=False` third-party loggers need `attach_std_logging(logger=...)`; bridged
      extras go through the scrubber; a `dump()` right after a log call already holds the event
      (the ring buffer is written before the queue), each run against the library first.
- [x] Closed: the runtime file said the queue worker writes the ring buffer; corrected from the
      source (`_remember_event` runs in the caller before the enqueue).
- [x] Closed: TLS-over-UDP refusal is versioned (>= 6.4.2) in all three places.
- [x] Declined: Windows Event Log and Windows service behaviour is read from the source and marked
      so in the reference file; no Windows run backs it.
- [x] Declined: refreshing `os.environ` on reload and thread excepthooks are application concerns,
      not library behaviour.
- [x] RED vs GREEN diffed both ways: no answer RED had right is lost in GREEN.
- [x] Quote-back of the eight contested questions: each answered by a direct quote, none NONE.

## Quality
- [x] Description measured: 489 characters, trigger-first, third person, no workflow summary.
- [x] Every code example and quoted message was executed against the installed library.
- [x] Present tense; no session narrative, no scratch paths.
- [x] Only reserved example values (`graylog.example.com`, `192.0.2.10`, `/etc/myapp`, `/path/to/app`).
- [x] External docs are GitHub links on the default branch plus install-local `--help`/`help()`.
- [x] ASCII only; tables in canonical form.
