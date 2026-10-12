# skill-writer checklist - coding-python-layered-config (2026-10-12, lib_layered_config 7.1.5)

Three sentences, identical in both copies of the skill:

- the logging paragraph: `read_config*` keeps the caller's bound trace id (7.1.5 drops the reset
  to `None` on entry);
- the same paragraph: `display_config` and the `read` command print different provenance comments,
  where the old text said `display_config` prints "the way the `read` command does";
- the ordered-YAML bullet: a plain mapping keeps the file's key order.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: one retrieval scenario with three questions (trace id around a
      `read_config` call, one parser for both provenance outputs, ordered YAML), answered only from
      the skill text, old text (RED) against new text (GREEN), inert text-only probe
      (`bitranox:baseline-probe`), model pinned to sonnet. Both arms received the same excerpt:
      the "Designing config files" bullets around the YAML rules and the "Display and logging"
      paragraph.
- [x] Inherited context checked with `redcheck --corpus-cascade` over the source repo: 1490
      documents read, verdict "inherited coverage" on shared vocabulary only. Adjudicated against
      the source: none of the named files contains `bind_trace_id`, a trace-id rule, `!!omap`,
      `# source: layer` or `display_config`, so the behavioural arm stands.
- [x] Scope: three sentences in two places; frontmatter untouched, no routing keyword moved.
- [x] Every claim executed against the 7.1.5 code before it was written: with an id bound,
      every `read_config` log record carries it and the binding survives the call (tests
      `test_read_config_tags_its_events_with_the_callers_trace_id`,
      `test_the_callers_trace_id_survives_read_config`); with nothing bound the records carry
      `None`; a `deploy_config` run with an id bound emitted 9 records, all carrying it;
      `display_config` printed `# layer:defaults profile:none (<path>)` above each key and
      `"a b" = 1` for a key needing quotes, while `read` printed
      `# source: layer=defaults, path=<path>`; a plain YAML mapping kept its key order in
      `as_dict()` and `as_dict(redact=True)`.

## RED (old text)
- [x] Trace id: answered `None` for the library's records (wrong for 7.1.5) and guessed `None`
      for the caller's records afterwards.
- [x] Parsers: answered "yes, probably one parser can handle both", governing line "prints a
      config the way the `read` command does"; comment lines NONE.
- [x] Order: NONE - the text does not say a plain mapping keeps its order.

## GREEN (new text)
- [x] Trace id: "req-42", governing line quoted: "`read_config*` and `deploy_config` tag their
      events with it and leave it bound".
- [x] Parsers: "No", governing line quoted: "The `read` command has its own renderer,
      `# source: layer=<layer>, path=<path>` above each key, so one parser does not fit both."
      Both comment shapes named.
- [x] Order: kept, governing line quoted: "a plain mapping keeps the file's key order through
      `read_config` and `as_dict()`".

## REFACTOR
- [x] Both arms asked for a `Skill gaps` section; both lists recorded here.
- [x] GREEN gap declined - how the caller's own log records pick up the id: that is the caller's
      logging setup, outside this library; the text says the binding stays.
- [x] GREEN gap declined - threads and async tasks: "a `ContextVar`" already names the scoping
      rule, which is Python's, not this library's.
- [x] GREEN gap declined - literal placeholder values (`profile:none` when no profile is set): the
      two shapes are what a parser keys on; values are whatever the run produced.
- [x] GREEN diffed against RED in both directions: every question RED answered GREEN answered,
      and no RED result is missing from GREEN.

## Quality
- [x] No session narrative or private provenance; no addresses, hosts or paths added.
- [x] Mirror level with the source repo's copy except the `name:` line.
- [x] Plugin version bumped (8.12.1 to 8.12.2) with a CHANGELOG entry.
