# skill-writer checklist - infra-modulejail (2026-10-05, WPA worked example, contrib C76)

New worked example in "The closure misses runtime-loaded modules", alongside the existing zram
one: WPA with `ccm` blocked fails as `Failed to set PTK` / `4-Way Handshake failed`, and only
`journalctl -t modulejail` shows `blocked: ccm`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Test approach: retrieval - one question answered with a
      direct quote or NONE.
- [x] RED (pre-change text, pasted): "A WPA handshake fails with 'pre-shared key may be
      incorrect' but the password is right - what else could this be?" - NONE; the only worked
      example present is zram/zstd, a different symptom shape.
- [x] This is a factual addition consistent with the section's own stated mechanism (runtime
      `request_module()` lookups via the crypto API, already documented for zstd): `ccm`/`cmac`/
      `gcm` are the crypto-API AEAD/MAC primitives WPA's 4-way handshake and PTK installation
      need, so a blocked `ccm` failing silently through the same `install X /bin/true`/logger
      mechanism already described is the same class of defect, not a new mechanism. Not
      independently reproducible in this environment (no wireless hardware); flagged as such.
- [x] GREEN (new example pasted): same question now answers with a direct quote ("Only
      `journalctl -t modulejail` shows `blocked: ccm`").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
