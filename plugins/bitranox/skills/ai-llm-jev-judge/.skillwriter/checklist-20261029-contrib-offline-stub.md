# Review: offline verification against a loopback stub (contrib entry)

Change: a paragraph under Commands telling the reader how to see what `run` sends without paying:
a loopback HTTP stub answering 400, `JEV_JUDGE_BASE_URL` plus a dummy `TYPESAFE_API_KEY`.

- [x] RED: `grep -c JEV_JUDGE_BASE_URL SKILL.md` on the pre-edit text returned 0; the method was
      only in the tool repo's `docs/skill-review.md`.
- [x] Mechanism checked against source: `adapters/jev/client.py:25` (`BASE_URL_ENV`),
      `client.py:81-112` (`resolve_base_url` honours only a loopback host, any other value falls
      back to the public API with no message), `client.py:32` (`RETRY_STATUSES` = 429 and 5xx,
      so a 400 is not retried); `composition/__init__.py:89-92` wires it with no warning.
- [x] Executed against the worktree (`uv run --project <tool repo> jev-judge run ...`) with a
      Python stub on 127.0.0.1 answering 400: exit 1, two items gave exactly two logged request
      bodies (a blank line in items.jsonl skipped), each row `ok: false`, `attempts: 1`,
      `reason: "http 400: ..."`.
- [x] GREEN: `grep -n "JEV_JUDGE_BASE_URL" SKILL.md` quotes the new paragraph (line 126).
- [x] Twin: tool copy regenerated from this one; `diff -r -x .skillwriter -x __pycache__` shows
      only the `name:` line.
- [x] ASCII only; no history wording; description untouched.
- [x] Declined, not run: subagent quote-back probes (this pass dispatched no subagents); the text was
      checked by grep and by executing the procedure it describes.
