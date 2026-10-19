# skill-writer checklist - coding-python-layered-config (2026-10-19, lib_layered_config 7.3.0)

Two additions, identical in both copies of the skill:

- a "Designing config files" bullet: write an integer outside `-2**63` to `2**64-1` as a string,
  because a TOML or YAML file holding one is refused whole;
- the `LayerLoadError` bullet under "Errors" also covers a file the loader refused under one of
  the "Designing config files" rules.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: one retrieval scenario with two questions (a TOML integer of
      2**64 and a 96-bit YAML hex literal, then `config.to_json()`: does `read_config` load the
      files, and how should the values be written), answered only from the skill text, old text
      (RED) against new text (GREEN), inert text-only probe (`bitranox:baseline-probe`), model
      pinned to opus. Both arms received the same excerpt: "Designing config files" and the
      "Errors" list.
- [x] Inherited context checked with `redcheck --corpus-cascade` over the source repo: 1569
      documents read, verdict "inherited" on shared vocabulary (`read_config`, `to_json`, `yaml`,
      `settings`). Adjudicated against the source: the three named files carry no rule about an
      integer's range or width (a grep for `64-bit`, `2**63`/`2**64`, `bits)` hits only an
      unrelated ctypes pointer), so the behavioural arm stands.
- [x] Scope: one bullet and one clause; frontmatter untouched, no routing keyword moved.
- [x] Every claim executed against the 7.3.0 code before it was written: through `read_config`,
      a TOML `2**64` and a YAML 80-bit hex literal raise `LayerLoadError` naming the file, the
      position and the width (`metrics.seed (int, 65 bits)`), while `-2**63`, `-1`, `0` and
      `2**64-1` load (`tests/adapters/test_loader_wide_int_refusal.py`); a non-string YAML key,
      `!!omap`, `!!set` and `!!binary` raise `LayerLoadError` through `read_config` too, and a
      plain TOML file loads as the control.
- [x] The bounds sit in code spans: a bare `-2**63` inside the bold span would close it early.

## RED (old text)
- [x] Does `read_config` load the files: NONE - guessed a refusal by analogy with `!!set`, and
      could not tell load-time refusal from a later `to_json()` failure.
- [x] How to write the values: NONE - extrapolated "as a string" from the base64 pattern.

## GREEN (new text)
- [x] Does `read_config` load the files: no, the whole file is refused, naming position and
      width, before `to_json()` is reached; governing line quoted: "**Write an integer outside
      `-2**63` to `2**64-1` as a string**: no JSON view can write one, so a TOML or YAML file
      holding it is refused whole, naming each integer's position and width."
- [x] How to write the values: as strings, `seed = "18446744073709551616"` and
      `id: "0xFFFFFFFFFFFFFFFFFFFFFFFF"`; same governing line.

## REFACTOR
- [x] Both arms asked for a `Skill gaps` section; both lists recorded here.
- [x] GREEN gap closed - which exception the refusal raises, and whether it raises or drops the
      file: the `LayerLoadError` bullet now names a refused file. Quote-back: the probe answered
      "raises `LayerLoadError`" quoting "or the loader refused one (a rule under "Designing config
      files")".
- [x] GREEN gap declined - whether a YAML `0x...` scalar is an integer: quoting the value, which
      the rule prescribes, gives a string either way.
- [x] GREEN gap declined - whether both refusals or only the first reach the caller: one file
      refuses the read; the order of layers is documented elsewhere in the skill.
- [x] GREEN gap declined - whether the range ends are inclusive: the reader took them as
      inclusive, which is what the code does (`2**64-1` and `-2**63` load).
- [x] GREEN gap declined - how the application turns the string back into a number: the
      application's own parsing, not this library's.
- [x] Quote-back gap declined - the message shape (how the position and width are written): the
      skill states what the error names; the exact text is the library's API reference.
- [x] GREEN diffed against RED in both directions: RED produced no answer GREEN lost.

## Quality
- [x] No session narrative or private provenance; no addresses, hosts or paths added.
- [x] Mirror level with the source repo's copy except the `name:` line.
- [x] Plugin version bumped with a CHANGELOG entry.
