# skill-writer checklist - coding-python-layered-config (2026-10-12, lib_layered_config 7.1.4)

lib_layered_config 7.1.4 refuses a YAML `!!omap` or `!!pairs` value with entries: PyYAML's safe
loader builds both as a list of `(key, value)` tuples, so a key such as `password` inside one was
never seen by redaction. This change adds one bullet under "Designing config files", identical in
both copies of the skill.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: one application scenario (a `.d` YAML file with a password,
      written as `!!omap` to keep key order) answered only from the skill text, old text (RED)
      against new text (GREEN), inert text-only probe (`bitranox:baseline-probe`), model pinned
      to sonnet. Both arms received the same excerpt: the "Designing config files" section, the
      YAML install line and the two error entries, the only YAML guidance in the skill.
- [x] Inherited context checked with `redcheck --corpus-cascade` over the marketplace checkout:
      verdict clean, 1490 documents read (weak evidence: not caught, not proven absent).
- [x] Scope: one bullet, two lines; frontmatter untouched, no routing keyword moved.
- [x] Every claim executed against the 7.1.4 code before it was written: a non-empty `!!omap` and
      `!!pairs` value refuses the file (`InvalidFormatError`, `LayerLoadError` from
      `read_config`); both load as lists of `(key, value)` tuples under `yaml.safe_load`; a plain
      YAML mapping keeps its key order through `read_config`, in `as_dict()` and in
      `as_dict(redact=True)`.

## RED (old text)
- [x] Governing line: NONE. The probe decided against `!!omap` only by analogy with the
      non-string-key bullet and from repository context outside the skill text; it could not
      say what the loader does.

## GREEN (new text)
- [x] Governing line quoted directly: "**Write ordered YAML as a plain mapping, never `!!omap` or
      `!!pairs`**: those load as `(key, value)` tuples whose keys redaction cannot see, so the
      loader refuses the whole file." Decision: rewrite as a plain mapping.

## REFACTOR
- [x] Both arms asked for a `Skill gaps` section; both lists recorded here.
- [x] GREEN gap deferred to its own change: the text does not say a plain mapping keeps its order,
      which was the developer's goal (verified true through `read_config`). The fix, "Write
      ordered YAML as a plain mapping (it keeps its order)", edits both copies of the pair at once,
      which the installed repo-gate (8.11.0) cannot commit on either side; it ships as a separate
      edit to both copies under a gate that accepts a pair changed together (8.11.1).
- [x] GREEN gap declined - which exception the refusal raises: the "Errors" section already says a
      layer that cannot be parsed surfaces as `LayerLoadError`, which is what this refusal is.
- [x] GREEN gap declined - whether a refused `.d` fragment aborts the whole read: true of every
      refusal the skill lists, not specific to this bullet.
- [x] GREEN gap declined - whether the refusal needs the `yaml` extra: a YAML file loads only with
      the extra, as the Install section says.
- [x] GREEN diffed against RED in both directions: both arms kept the advice to move the password
      to the `env` layer or `.env`; nothing RED produced is missing from GREEN.

## Quality
- [x] No session narrative or private provenance; no addresses, hosts or paths added (the
      scenario's `mail.example.com` stays in this artifact only).
- [x] Mirror level with the source repo's copy except the `name:` line.
- [x] Plugin version bumped (8.11.1 to 8.11.2) with a CHANGELOG entry.
