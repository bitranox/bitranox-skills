# skill-writer checklist - coding-python-layered-config (2026-07-13, new skill)

- [x] Change: new skill - marketplace mirror of the lib_layered_config repo's python-layered-config usage skill (install, use, CLI, provenance, per-OS paths on Linux/macOS/Windows, profiles, designing config files). Marketplace copy carries the taxonomy-prefixed name; body kept in sync with the repo copy.
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED baseline (sonnet, no skill): agent missed the `defaults` layer, guessed a single-underscore env prefix, could not name the provenance API.
- [x] GREEN (sonnet, with skill): every baseline gap answered correctly - six-layer precedence with `defaults`, verbatim vendor/app paths, the triple-underscore `MY_APP___DATABASE__HOST`, and `config.origin` / `read-json` for provenance.
- [x] CSO: description is a single-line trigger-first "Use when ..." with config-design triggers and distinctive keywords (layered config, provenance, env-var prefix, profiles, per-OS paths).
- [x] Security scan: prose/frontmatter/table only; only public GitHub/PyPI URLs; no secrets, private paths, IPs, or PII.
