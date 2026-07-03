# meta-dream-project v2 (B2 draft - WIP)

## Section 1 - Call the memory scripts (fail LOUD)

Set strict. Capture output + rc. Require the success line. On any miss: STOP the dream, print the output.

    export BITRANOX_RUN_PYTHON_STRICT=1
    RP="$CLAUDE_PLUGIN_ROOT/hooks/run-python.sh"; HK="$CLAUDE_PLUGIN_ROOT/hooks"
    out=$(bash "$RP" "$HK/memory_engine.py" heal --proj "$CWD" 2>&1) \
      && printf '%s' "$out" | grep -q 'healed .* across .* level' \
|| { printf 'DREAM ABORTED:\n%s\n' "$out" >&2; exit 1; }

| Command                             | Require                               |
|-------------------------------------|---------------------------------------|
| `memory_engine.py heal`             | `healed N file(s) across M level(s)`  |
| `memory_engine.py set-scope`        | `scope updated:` / `scope unchanged:` |
| `reconcile_memory_index.py --check` | `TOTAL problems: 0`                   |

- Call via `run-python.sh`, never raw `python3`.
- Never swallow stderr. Never hand-edit `index.md`/`facts/`. Never skip a failed step.

Checklist: [ ] strict set  [ ] output+rc captured  [ ] success line present  [ ] fail -> abort + show output
