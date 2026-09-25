# Jev classifier: design

The design of the opt-in Jev experiment: what it may send, where it fits, how it is wired and how it
is evaluated. The live record - what has shipped, every measurement, and what is next - is rank 12
in `OPEN-WORK.md`, and each release is in `CHANGELOG.md` from 7.1.0 on.

## Context

TypeSafe's Jev is a "System One" model. It takes text as state, is asked typed questions, and returns
typed answers with probabilities instead of generating text.

- **Question types:** `choice` (one of up to 255 options), `noul` (the probability of yes) and
  `score` (a position on 2-10 described levels).
- **Speed and cost:** typically ~100 ms (70-500 ms), $0.042 per million input tokens, output free.

Today no bitranox hook calls a model. Every hook-time classification is a regex or a word list. The
sites with a documented false-positive/negative history classify prose intent, which regex handles
poorly. The model judgements that do exist run in dream skills on sonnet or the session model.

The goal is to add Jev as an OPTION BESIDE the existing code:
- nothing is deleted;
- it is off by default;
- shadow mode comes first (log only, behaviour unchanged);
- a site moves to Jev only after a replay shows it is better there.

User decisions (2026-09-21):

- **What may be sent:** prompts, the last assistant message and memory text may go to TypeSafe. So
  may tool output and file contents, when a site needs them.
- **Secrets:** they are REDACTED in place before sending. A secret never causes a call to be skipped.
- **HTTP client:** the standard library (`urllib.request`), not httpx2 and not the `typesafe-sdk`.
  That means no third-party dependency, no PEP 723 script and no `uv` requirement. (This replaces an
  earlier httpx2 decision from the same day.)

## Review against the installed TypeSafe skill and live docs (plugin typesafe 0.5.7, 2026-09-21)

Sources read: the `typesafe:typesafe-ai` skill, and on docs.typesafe.ai the pages api, state,
confidence, legal, patterns/intent-routing, and the cookbooks rerank_typesafe,
hierarchical_classification, entity_alignment and parallel_questions. Each finding below changed
the plan.

| #  | Finding in the docs                                                                                                                                                                              | Change to the plan                                                                                                                                                                                                                                                    |
|----|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | The request body is `{model: "jev-latest", state, questions}`, and `model` is REQUIRED                                                                                                           | The adapter always sends `model`, taken from config (default `jev-latest`)                                                                                                                                                                                            |
| 2  | Errors are 401, 422, 429 and 529, with exponential backoff prescribed for 429/529                                                                                                                | A HOOK never retries: it falls back to the regex at once. Only `classifier_eval.py` backs off                                                                                                                                                                         |
| 3  | "English is primary. Other languages ... currently have lower accuracy"                                                                                                                          | The Stop-gate regexes cover English AND German, and the user writes German. So: evaluate per language, never let Jev REPLACE the German regex, and keep UNION as the Stop gate's only decide mode (the regex OR Jev fires)                                            |
| 4  | State should be an OBJECT with named fields; content goes in state, the judgment in questions; Question IDs are not sent to the model                                                            | State is always a named object, e.g. `{"user_message": ..., "previous_assistant_message": ...}`. Every question carries its full meaning and references fields as backticked paths                                                                                    |
| 5  | "Use one Noul per label when several may apply"                                                                                                                                                  | Stop gate: one `noul` per signal family. Router: a new-task `noul` plus ONE `choice` over the installed skills - replayed and blind-judged, it was more accurate than a `noul` per skill, which let one number gate the turn and set every skill's bar                |
| 6  | Batching questions over the same state does not change the answers (sd 0.0) and is 12x cheaper and 10x faster                                                                                    | All questions for one site go in ONE request. At $0.042 per million input tokens even a 14k-token request costs under $0.001, so arms are chosen on accuracy, not cost                                                                                                |
| 7  | The rerank cookbook scores one query/candidate PAIR per request (noul), run concurrently; a shared state holding all candidates adds irrelevant context                                          | Recall rerank: the keyword scan keeps a wide shortlist of ~30, then ~30 concurrent pair requests through a small thread pool. Batching does NOT apply here, because each candidate is different state. The eval also measures the one-request `candidates[i]` variant |
| 8  | The entity-alignment cookbook judges pairs with a 3-level `score` (different / related-uncertain / same) and escalates the middle level to a human, because a wrong merge is the expensive error | The dedup scorer becomes a 3-level `score`. "same" and "related" both go to the existing adversarial second pass, and "different" is dropped. This matches the memory rule "topic match is not redundancy"                                                            |
| 9  | Hierarchical classification (choice per level, beam search) helps with large taxonomies                                                                                                          | Skill names already form a two-level tree (process-, coding-, meta-, ...). This is recorded as the fallback if the flat noul-per-skill router scores poorly, not built up front (YAGNI)                                                                               |
| 10 | Thresholds are risk-scaled and tuned on your own data; confidence is not permission to act                                                                                                       | Every Jev use here is a nudge or a ranking, and none is destructive. The thresholds start conservative and are tuned from the eval. Blocking stays with the regex-or-Jev union                                                                                        |
| 11 | Legal: no training on user data; retention is set by the DPA; zero data retention only for enterprise, via privacy@typesafe.ai                                                                   | This goes into the results doc as the privacy posture. Redaction plus field minimisation stay mandatory. A ZDR request is the user's call                                                                                                                             |
| 12 | Weak at counting, dates and indirection; can be steered by text in the state                                                                                                                     | statusrot's date and version logic stays in regex, and Jev only judges "does this line assert a mutable status". State is the user's own text, so the steering risk is low, and it is still logged                                                                    |

## Live smoke test (2026-09-21, key from `~/.credentials/typesafe.key`)

| Measured                                   | Value                                                        | Consequence                                                                                                                               |
|--------------------------------------------|--------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| status / model                             | 200, `jev-1.13.0`                                            | endpoint, bearer auth and the `model: "jev-latest"` body field are confirmed                                                              |
| verdict                                    | English correction: `correction` noul 0.97, `none` noul 0.02 | noul-per-family separates the classes on this example                                                                                     |
| latency, one COLD call incl. TLS handshake | 860 ms                                                       | above the documented ~100 ms. Keep the 1.5 s hook timeout; measure warm latency p50/p95 in the eval before choosing a decide-mode timeout |
| usage                                      | 322 input tokens for 2 short questions                       | question text dominates tiny states; budget per site from the eval's measured tokens                                                      |
| key format                                 | not `sk-`-prefixed (108 chars)                               | never validate the key by prefix; a third-party write-up's `sk-...` claim is wrong                                                        |

## Where Jev fits (ranked), and where it does not

**First wave: prose intent inside a live hook.**

| Site                                                                                                                                                                                                                                                            | Now                                                           | Jev request                                                                                                                                                                                                                                                         |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Stop-gate learning signal. `hooks/self_improve_signals.py` USER/ASST/REALIZATION/ENDORSE patterns, used by `hooks/self-improve-gate.py:237` and `hooks/subagent-capture.py:67`. Runs every turn and can block. The CHANGELOG records its misses and false fires | English and German regexes                                    | 1 request, 5 nouls (correction, remember-rule, self-admission, realization, endorsement; endorsement is logged but never counts as a firing) over `{previous_assistant_message, user_message, assistant_reply}`                                                     |
| Skill router. `hooks/skill-router.py:44`, every prompt                                                                                                                                                                                                          | keyword hits over `skill_triggers.json`, needs 2 or more hits | 1 request: a new-task gate noul plus ONE choice over the session's installed skills, over the prompt, the reply it answers, the project, recent tool activity and the skills already used. A pick is the gate passing, or the winner's own probability reaching 0.7 |
| Recall relevance, i.e. searching the CLAUDE.local.md index. `hooks/recall-memory.py:152-184`                                                                                                                                                                    | IDF keyword ranking                                           | keyword shortlist of 30, then 30 concurrent pair nouls over `{user_prompt, memory_pointer}`                                                                                                                                                                         |

**Second wave: batch or dream work done today by sonnet or the session model.** It starts only
after the first wave's eval shows value.

| Site                                                                                                                                                                                                                    | Now              | Jev request                                                                                                                                                            |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Filler/topical keyword labelling (`dream-passes.md:114`)                                                                                                                                                                | sonnet subagent  | `choice` filler/topical, with the keyword plus the prompts it came from as state                                                                                       |
| Fact type at capture (`memory_engine.py --type`)                                                                                                                                                                        | session model    | `choice` user/feedback/project/reference, as a suggestion only                                                                                                         |
| statusrot candidates (`skills/meta-dream-tree/statusrot.py:50-77`)                                                                                                                                                      | regex            | `noul` "asserts a mutable status" on the regex hits only                                                                                                               |
| Dedup candidates (`dedup_scan.run(scorer=)`, a seam that already exists)                                                                                                                                                | Jaccard          | 3-level `score` different / related / same. Only "different" is dropped                                                                                                |
| Advisory nudges: `missing-mechanism-nudge.py:30`, `capture_constraints.py:26`, `jig-repetition-nudge.py` (32% false by its own measurement; its state is the redacted `{script_text, prior_script_text}`)               | regex / shingles | one `noul` per advisory, on the regex hits only, as a precision filter                                                                                                 |
| Tool-failure and missed-learning candidates: `self-improve-audit.py:138` `find_candidates` (`BROAD_*` minus strict, `TOOL_SIGNAL_PATTERN`), also `subagent-capture.py:67`. Now possible because tool output may be sent | regex            | one `noul` "is this a real failure or a mistake worth a lesson?" over the redacted `{command, tool_output_tail, next_assistant_message}`, on the regex candidates only |

**Stays deterministic:**
- tell-char sweeps and secret scanning;
- command-shape guards (a structural parse is exact, and they run on every tool call);
- the context watcher (numbers);
- dream merge and placement verdicts (multi-hop reasoning);
- the skill audit (generation).

## Design

### 1. Classifier port: `plugins/bitranox/hooks/classifier.py`, stdlib only

Hooks run on a bare `python3` through `run-python.sh`. Nothing provisions their dependencies, and
they fail open. The client is therefore the standard library, `urllib.request` plus `json`, by user
decision. That brings three consequences:

- Shadow mode and decide mode both work on any `python3`, with no install step and no `uv`.
- The detached shadow child is a plain `python3` run of `classifier.py` (a `__main__` entry that
  reads the redacted payload on stdin).
- httpx2 would buy nothing here. Every hook invocation is a new process, so a pooled `Client` never
  gets reused between calls.

How the stdlib covers what httpx2 would have provided:

- **Overall deadline:** the `urlopen(timeout=)` timeout is per socket operation, not a total. The
  adapter runs the request in a `ThreadPoolExecutor` and waits with `future.result(timeout=deadline)`,
  so a slow trickle cannot exceed the hook budget. A late thread is abandoned, and its result
  discarded.
- **Concurrency:** the recall rerank's pair requests run through the same `ThreadPoolExecutor`
  (default 8 workers), under one overall deadline.
- **HTTP errors:** `urllib.error.HTTPError` carries the status code (401, 422, 429, 529), which is
  logged as the skip reason.
- **TLS:** certificate checking stays at the default (`ssl.create_default_context()`), and there is
  no option to turn it off.

- A `Question` dataclass: `id`, `type` (noul / choice / score), `instructions`, `criteria`.
- An `Answer` dataclass: `value` (a float for noul and score, a key for choice), `probabilities`,
  `confidence | None`.
- A `Result` dataclass: `answers: dict[id, Answer]`, `latency_ms`, `input_tokens`, `model`.
- A `Classifier` protocol with `ask(state: dict, questions: list[Question]) -> Result | None`.
- `NullClassifier` always returns None, so the caller keeps its regex verdict.
- `JevClassifier` sends `urllib.request` POSTs to `{base_url}/v1/systemone`, with an overall
  deadline (default 1.5 s) and `model` from config. Any error, timeout, non-200 response or schema mismatch
  returns None. It never raises into a hook.
- `ask_many(pairs, workers=8)` runs concurrent requests for the recall rerank.
- `get_classifier(site)` reads config and the key.
- The key is read in this order:
  1. the `TYPESAFE_API_KEY` env var, which is also the name the TypeSafe SDK and docs use;
  2. the keyfile `~/.credentials/typesafe.key`.

  It is never logged, echoed or put on a command line, and the detached shadow child gets it from
  the same lookup, never via argv.
- The keyfile must be owned by the user and mode 600. With any group or other permission bit set,
  the adapter refuses the file and reports `skipped: keyfile permissions`.
- The keyfile is read as UTF-8, with or without a BOM. A file in another encoding (UTF-16 from
  Notepad's "Unicode", latin-1) is refused as `unreadable keyfile`, and a key that is not
  printable ASCII, from either source, as `api key is not printable ascii`: it could only ever
  fail in the request header.
- **Getting the key:** sign in at https://console.typesafe.ai/keys (the docs quickstart links it as
  "dashboard") and generate a key.
- **Setting it (recommended: the keyfile):** the file works however Claude Code was launched (IDE,
  terminal, systemd), and hooks inherit whatever env Claude Code started with. Setup:
  `install -m 600 /dev/null ~/.credentials/typesafe.key`, then paste the key into it with an
  editor. Do not use `echo`, and do not use Claude Code's `!` shell, which has no TTY for
  `read -s`.
- **Not in `settings.json` "env":** the key would sit in plaintext in a file that tools read and
  edit. Not in any repo file either.
- `base_url` is injectable, which is the test seam.

### 2. Redaction before egress

`redact(text) -> (text, n)` in the new `hooks/secret_patterns.py`.

- Extract `recall-memory.py:54 holds_a_credential` and the `repo-gate.py:586/621 check_secrets`
  patterns into one span-returning helper. Both existing callers keep their behaviour.
- Replace each matched span with `[REDACTED]` and send the result. Log the count only.
- Field minimisation: send only the named fields each site needs, each capped at about 4k chars.
  Tool output and file contents are allowed, but only as a named field of a site that needs them
  (e.g. `{failed_command, tool_output_tail}`, `{script_text}`), and always redacted. Nothing is sent
  just because it happens to be in the transcript.
- Redaction runs on EVERY field, including tool output and file contents. These are the fields most
  likely to hold a token, a `.env` line or a private key block. Add the PEM block pattern
  (`-----BEGIN ... PRIVATE KEY----- ... -----END ...-----`) and a `KEY=value` rule for
  secret-looking env lines to the shared patterns, with tests.

### 3. Config knobs

Add them to `self_improve_signals.py` `DEFAULT_CONFIG`, `settings.py` `ENUM_CHOICES` and the
meta-memory-settings docs.

- `classifier_backend`: `off` (default) or `jev`.
- `classifier_model`: default `jev-latest`.
- One flat knob per site, `classifier_<site>`: `off` (default) or `shadow`, with `decide` joining
  the enum when a site is wired for it (the settings CLI validates flat enums, not dicts). First-wave
  sites: `stop_signal`, `skill_router`, `recall_rerank`. Second-wave site ids: `filler_topical`,
  `fact_type`, `statusrot`, `dedup`, `advisories`, `tool_failure`.
- `BITRANOX_HOOKS_OFF` still disables everything.

### 4. Modes

Each site gets one wrapper, and its regex function is not touched.

- **shadow:** the regex decides as today. A DETACHED child (`Popen(start_new_session=True)`,
  redacted payload in a mode-600 temp file) calls Jev and appends a line to
  `~/.claude/self-improve-audit/classifier-shadow-<UTC date>.jsonl`, keeping the last 30 days and at
  most 200 MB. The line holds:
  - site, ts, session_id and the detected language;
  - the regex verdict and every Jev answer with its probabilities;
  - latency and tokens;
  - the redacted state, for adjudication;
  - the plugin version, and the transcript path and offset the prompt sits at.

  The hook adds no latency.
- **decide:** a synchronous call within the timeout.
  - Stop gate: UNION, meaning it blocks if the regex OR Jev (noul >= threshold) fires.
  - Router: Jev's top 2 above the threshold, falling back to the keyword match.
  - Recall: Jev's order over the keyword shortlist, falling back to the keyword order.

  Both verdicts are always logged. Decide mode goes live per site only after section 5 shows a win.

### 5. Evaluation

`plugins/bitranox/skills/meta-self-improve/classifier_eval.py`

- **Sources:**
  - a replay of `~/.claude/projects`, walked with `rglob`, deduped by tool_use id, and restricted to
    the eligible subset;
  - the shadow log.
- **Method:** per site, run regex and Jev, and report the FIRING-SET diff (regex-only, Jev-only,
  both), split by language (en/de). Disagreements go to a file for adjudication against the source
  transcript.
- **Controls:** each site gets a planted positive and a planted negative.
- **Rates:** backoff on 429/529; stay under 1200 requests per minute.
- **Variants measured:**
  - router: noul-per-skill vs a single `choice`;
  - recall: pair requests vs one request with `candidates[i]`.
- **Accuracy:** a disagreement is not a Jev error, so every decide-mode question is settled by a
  blind panel (five judges who never see which side fired) over the rows, with the outcome per
  branch pre-registered before any judge runs.
- **Output:** a results doc giving go/no-go per site and per language, cost and latency
  percentiles, and the privacy posture from finding 11.

## Critical files

- **New:**
  - `plugins/bitranox/hooks/classifier.py` and `plugins/bitranox/hooks/secret_patterns.py`;
  - `plugins/bitranox/skills/meta-self-improve/classifier_eval.py`;
  - sibling tests `hooks/tests/test_classifier.py`, `hooks/tests/test_secret_patterns.py` and
    `skills/meta-self-improve/tests/test_classifier_eval.py`.
- **Edited:**
  - `hooks/self_improve_signals.py` (config);
  - `skills/meta-memory-settings/settings.py` plus its SKILL.md (through meta-skill-writer);
  - `hooks/self-improve-gate.py`, `hooks/skill-router.py` and `hooks/recall-memory.py` (the site
    wrappers);
  - `hooks/recall-memory.py` and `hooks/repo-gate.py` (moved to the shared secret patterns);
  - `CHANGELOG.md` and `plugin.json` (the bump).
- **Reused:** `self_improve_signals.load_config`, `sig._audit_dir()`, `dedup_scan.run(scorer=)`
  (second wave), and compuse-toolbox `guard_replay` / `jsonl_grep` for the corpus walk.

## Build order

1. `secret_patterns.py` plus `redact()`, with tests. RED: a planted token must come out
   `[REDACTED]`.
2. The `classifier.py` port, with the Null and Jev adapters. Tests run against a local fake HTTP
   server through the injected `base_url`: request shape including `model`; each of 401, 422, 429
   and 529, a timeout and a malformed body returns None; a missing key returns Null. The fake is a
   real local `http.server` on a thread, not a patched urllib. The tests also cover:
   - a fake that trickles its response slower than the deadline, which proves the OVERALL deadline
     holds and not just the socket timeout;
   - a bare-environment run (subprocess `python3 -I`, empty site-packages), which proves
     `classifier.py` imports nothing outside the standard library.
3. Config knobs and docs.
4. Shadow wrappers for the three first-wave sites. Tests: hook output and exit code are unchanged in
   shadow mode, and the detached child writes a log line.
5. `classifier_eval.py`, then a first replay run, then the results doc.
6. Decide wiring behind the knob, still off by default. The second wave only after step 5.

Work in a dedicated git worktree. Commit, bump, push and watch CI as one action.

## Verification

- Run the CI dependency set:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ plugins/bitranox/skills/meta-self-improve/tests/ -q`,
  then `python3 plugins/bitranox/hooks/repo-gate.py --ci`.
- Fail-open: with `classifier_backend=jev` and a bad key or an unreachable host, every hook exits 0
  with unchanged output.
- Egress: a prompt holding a fake `ghp_...` token reaches the fake server as `[REDACTED]`, and the
  request carries only the named fields. The same applies to a tool-output field holding a PEM
  private-key block and a `.env` line (`API_KEY=...`).
- Bare interpreter: with the backend set to `jev`, shadow and decide mode both work under a plain
  `python3 -I` with no third-party packages and no `uv` on PATH.
- Live smoke test with a real key, `stop_signal: shadow`. Type one English correction and one German
  correction. Both shadow-log lines appear with nouls and the regex verdict, and the turn latency is
  unchanged.

## Status

Tracked in `OPEN-WORK.md` rank 12, not here.
