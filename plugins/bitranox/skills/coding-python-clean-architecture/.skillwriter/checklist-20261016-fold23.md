# skill-writer checklist - coding-python-clean-architecture (2026-10-16, fold 23)

- [x] Change (contradiction, A6): the A6 paragraph in `review-checklists.md` claimed every
      `import <pkg>` from an adapter fails "as adapters-to-composition", while none of the skill's
      contracts listed `composition`. Rewritten to the measured condition: it breaks only when the
      root `__init__` re-exports from `<pkg>.composition` AND the contract lists `composition` above
      `adapters`; otherwise it stays green. The "Reading the result" bullet now says the same.
- [x] Change (adjacent defect found while resolving it): all three `layers` contracts (SKILL.md
      Import Enforcement, review-checklists multi-context and flat) were written domain-first.
      import-linter reads a `layers` list highest-first, so they forbade adapters importing the
      domain. Reordered to `composition, adapters, application, domain` (multi-context: adapters,
      application, domain), with a one-line "highest first" comment and a short SKILL.md paragraph
      explaining the inversion and why `composition` belongs in the list.
- [x] Ground truth (import-linter 2.15, scratch package): contract `["pkg.domain", "pkg.application",
      "pkg.adapters"]` with an adapter importing the domain -> "pkg.adapters is not allowed to import
      pkg.domain"; the reordered four-layer contract keeps that code and breaks a domain->adapters
      import. Adapter `import pkg` with root `__init__` importing composition: three-layer contract
      "1 kept, 0 broken"; four-layer contract "pkg.adapters is not allowed to import
      pkg.composition: pkg.adapters.thing -> pkg -> pkg.composition.compose"; the same contract with
      the adapter using `Path(__file__)` instead: kept.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit the A6 text asserted a contract failure no
      contract in the skill could produce, and the example contracts encoded the inverted layer
      order. Behavioural RED replaced on purpose because the A6 rule is in the always-loaded memory
      index of the authoring machine (inherited coverage); the layer-order defect was proven by
      running import-linter instead.
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): no rules to add;
      contradictions: A6 vs the skill's contracts -> resolved, review-checklists.md:132-137 "When that
      `__init__` re-exports from `<pkg>.composition` ... and the contract lists `composition` above
      `adapters`, `lint-imports` breaks ... A contract that omits `composition`, or a root `__init__`
      that imports nothing above `adapters` yet, stays green", and the contracts now list composition
      (SKILL.md:653, review-checklists.md:125); "Reading the result" bullet at :151-154 now conditional
      ("a root package that re-exports from `composition`"). Re-measured independently with
      import-linter 2.15 from pyproject.toml in a scratch package: SKILL.md:653 contract keeps
      adapters->domain ("Contracts: 1 kept, 0 broken.") and breaks domain->adapters ("pkg.domain is
      not allowed to import pkg.adapters"); the old domain-first list breaks correct code ("pkg.adapters
      is not allowed to import pkg.domain"); A6 arms: init imports composition + listed -> broken
      ("pkg.adapters.repo -> pkg / pkg -> pkg.composition.compose"), init imports composition + not
      listed -> kept, empty init + listed -> kept; zero contracts -> "Contracts: 0 kept, 0 broken.",
      exit 0. Step-4 scan of SKILL.md and review-checklists.md: no hit
- [x] Gaps closed or declined: the four-layer contract fails with "Missing layer 'pkg.composition'"
      (exit 1, measured) in a package without a `composition` package; closed: the layer-order
      paragraph now says to drop that entry when the package has none.
- [x] Description measured: unchanged (310 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
