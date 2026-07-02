# Changelog

All notable changes to the bitranox plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Versioning (SemVer): how to pick the next number

Versions track `plugins/bitranox/.claude-plugin/plugin.json`. Installed copies only re-fetch
when that version changes, so every change under `plugins/bitranox/` must bump it (see
`CONTRIBUTING.md`). Pick the bump by impact on the published surface:

- MAJOR (`X.0.0`): breaking change. Removing/renaming a skill, or changing a skill's
  invocation or behaviour incompatibly.
- MINOR (`x.Y.0`): backward-compatible addition. A new skill, hook, or capability.
- PATCH (`x.y.Z`): backward-compatible fix. A bug fix, wording/doc fix in a skill, added tests.

Repo-meta outside the plugin tree (this file, `README`, `CONTRIBUTING.md`, CI) does not ship to
installed copies and needs no bump.

## [5.12.0] - 2026-07-02

### Added
- `coding-resilience`: new reference skill on never assuming an external resource is available and
  designing for self-healing. Covers retry with backoff + jitter under a hard timeout (tenacity),
  health-check/evict/replace, maintaining a pool at a target size with margin (net-rotating-proxies
  as the worked example), rediscover-do-not-cache, background top-up-to-target, circuit breaker,
  graceful degradation (partial result + warning + non-zero exit), and resource guards
  (bound concurrency/memory/payload, disk/CPU headroom checks). Cross-referenced from
  `coding-python-clean-architecture`, `coding-python-use-modern-libraries`, `compuse-ssh`,
  `compuse-vnc`, `infra-proxmox`, and `coding-input-sanitization`.

## [5.11.0] - 2026-07-02

### Added
- `net-rotating-proxies`: self-optimizing proxy pool. `run` now holds an in-memory working set of the
  `--need` fastest healthy proxies (`ProxyPool`) that maintains itself while the job runs:
  - Rotation so no exit-IP is hammered - a `--cooldown` rest (weighted-LRU) holds a just-used proxy out
    of the next pick, spreading load across the fast half of the pool while still favouring speed;
    relaxes oldest-rested-first so a small pool never starves.
  - Background benchmark + swap-up (with `--background-discovery`, every `--bench-interval` seconds):
    re-times in-pool proxies, trials fresh candidates, and swaps a faster fresh proxy in for the
    slowest IDLE in-pool one (never one mid-request), so steady state stays the N fastest.
  - Flaky eviction: per-proxy success/failure is tracked; a proxy whose failure fraction exceeds
    `--flaky-fail-ratio` is evicted and replaced like a hard-dead one, not just connection-dead ones.
  The pure decision logic (`_weighted_lru_pick`, `_swap_candidate`, `_is_flaky`) is separated from the
  locked, threaded pool state and unit-tested. Existing right-size (`--need`), top-up-to-target, and the
  100% margin behaviour are kept intact. (+20 tests.)

## [5.10.0] - 2026-06-30

### Added
- `net-rotating-proxies`: `validate --need N` early-stop - stop as soon as N live proxies are found (and
  cancel the rest) instead of testing the whole pool, so a small job validates a handful, not thousands.
  The background refresh (`run --need N`) tops the pool back up to N when proxies die, instead of
  re-validating everything. SKILL.md sizing rule: `N ~= 2 x concurrency` (a ~100% margin) so the
  speed-weighted pick runs the fastest while the slower half stays as warm backup. (+2 tests.)
- `sec-appsec-web-baseline`: the scanner detects a same-subnet / internal target - if the URL resolves to
  a private (RFC1918/loopback/link-local) IP and no `--proxy` is given, it warns that the scan measures
  the internal path (origin / split-horizon edge), not what external visitors get, and steers to an
  external egress via net-rotating-proxies. (+2 tests.)

## [5.9.0] - 2026-06-30

### Added
- `files-edit-toml` skill: edit TOML (`pyproject.toml`, config TOML) via a Python library, never
  sed/regex. Routes by whether comments must survive - `tomlkit` for a style-preserving round-trip edit
  (the right tool for `pyproject.toml`), `tomllib` for read (stdlib, read-only), `rtoml`/`tomli_w` for
  machine-owned data. Listed under "Editing structured files and docs" in the orientation index.

### Changed
- `meta-skill-writer`: add a design-time rule - before settling on a single-process tool, decide WHETHER
  the authored skill should fan its heavy / parallelizable / context-bloating work across subagents
  (context isolation + parallel speed), baking the fan-out into the workflow, then pin the model tier.

## [5.8.0] - 2026-06-30

### Added
- New always-active hook **`block-sed-structured-files`** (PreToolUse Bash): BLOCKS an in-place text
  editor (`sed -i` / `gsed -i` / `perl -i`) whose argv targets a `.json/.yaml/.yml/.toml/.xml` file -
  editing structured config as raw text is the `no-hand-edit-config` footgun - and steers to the
  `files-edit-json` / `files-edit-yml` / `files-edit-xml` / `files-edit-toml` skills (load -> edit ->
  dump -> re-validate). WARNs on a `>`/`>>` redirect onto such a file. Command-position anchored (a
  quoted `sed -i x.json` inside an `echo` does not trip it) and fail-open. (+19 tests.)

## [5.7.0] - 2026-06-30

### Fixed
- `sec-appsec-web-baseline`: fix blocking bugs found in review of the 5.6.0 debut. The scanner now
  imports `httpx2` (it had imported `httpx`, which breaks in a clean `uv run`); mixed-content detection no
  longer false-positives on a plain `<a href="http://">` link (only subresource-loading elements count)
  and now also catches `srcset`; a report-only CSP is graded MINOR (not OK) and never counts as
  clickjacking protection; `no-referrer-when-downgrade` is no longer graded OK; the server-version check
  no longer false-fires on a product name with a digit (e.g. `AmazonS3`).

### Added
- `sec-appsec-web-baseline`: a `Cross-Origin-Opener-Policy` check + reference entry; a `--proxy URL` egress
  on `audit_headers.py` and a workflow note to audit PUBLIC sites from OUTSIDE the internal network (route
  via `net-rotating-proxies`, ideally in subagents) so the edge is measured, not the internal origin.
  (+9 tests, 39 total.)

## [5.6.3] - 2026-06-30

### Fixed
- `repo-gate` commit-detection no longer false-fires on the literal text `git commit` inside a quoted
  string or heredoc body (e.g. a Bash command that writes a CHANGELOG line about committing). Detection
  is now anchored at a command position (statement start, after a shell separator) instead of a loose
  substring search - over-matching was not harmless, it false-fired the version-bump BLOCK because
  plugins/ is normally dirty-and-not-yet-bumped mid-work. Real commits (incl. `-C`, `--no-pager`, an
  env-assignment prefix, a subshell) still match. (+6 detector test cases.)

## [5.6.2] - 2026-06-30

### Changed
- `compuse-git` (shared-checkout section): add the pathspec-commit defense - staging only your own paths
  is NOT enough, because a commit records the WHOLE index, so a sibling session's already-staged files
  get swept in. Commit only your paths with a pathspec (`-- <paths>`, the `-m` message before `--`). Notes
  that the branch-guard does not catch this (HEAD is not behind). Generalized from the 5.6.1 incident.

## [5.6.1] - 2026-06-30

### Fixed
- Restore master consistency after a shared-checkout sweep in 5.6.0 (`c5ad104` accidentally committed
  foreign already-staged files): removed the superseded opt-in copy
  `skills/compuse-git/scripts/git-commit-branch-guard.py` (it shipped without tests -> tests-exist fail;
  the real hook lives at `hooks/git-commit-branch-guard.py`), and added the `sec-appsec-web-baseline`
  entry to the `meta-using-bitranox-skills` catalog (it was shipped without its catalog line ->
  skills-index fail).

## [5.6.0] - 2026-06-30

### Added
- `sec-appsec-web-baseline` skill: audit + harden a site's HTTP web-security baseline - security headers
  (CSP, HSTS, X-Content-Type-Options, X-Frame-Options/`frame-ancestors`, Referrer-Policy,
  Permissions-Policy, `X-XSS-Protection: 0`), cookie `Secure`/`HttpOnly`/`SameSite` flags, the
  HTTP->HTTPS redirect, TLS, mixed content, and server-version leakage. Ships `audit_headers.py` (httpx2,
  one GET + a plain-HTTP HEAD, grades SEVERE/MEDIUM/MINOR/OK, no external grading service) with pure
  testable graders + 30 pytest tests, `references/security-headers.md` (values, nginx snippets, safe
  rollout, and gotchas such as the nginx `add_header` inheritance reset), and the safe-rollout discipline
  (staged HSTS, CSP report-only first). Added a new "Security" grouping to the orientation index.
- New always-active hook **`git-commit-branch-guard`** (PreToolUse Bash, warn-only, fail-open): warns
  before a `git commit` when local HEAD is behind/diverged from its upstream (origin advanced under you -
  the shared-checkout / multi-session hazard). Low-noise everywhere - the behind/diverged check runs in
  every repo but fires only when origin moved under you (silent in normal feature-branch work); the louder
  "not on the default branch / detached HEAD" check is OFF by default and enabled per-repo via
  `GIT_GUARD_STRICT_REPOS="repoA,repoB"`. Default branch auto-detected from `origin/HEAD`. (+11 tests.)
  `compuse-git` documents it.

## [5.5.0] - 2026-06-30

### Changed
- `compuse-git`: new section "Committing safely when sessions/agents share a checkout" (+ quick-ref row) -
  when multiple agents/sessions share ONE working copy, branch/HEAD/index can change under you, so a commit
  lands on the wrong branch or a stale base. Verify `git branch --show-current` + `git rev-list --left-right
  --count HEAD...@{upstream}` and stage only your own files (never `git add -A`); durable fix is a `git
  worktree` per session; optional warn-only PreToolUse guard, scoped to single-branch repos (an unscoped
  "off default branch" warning is noise in feature-branch workflows). Generic - the universal half of the
  machine-local git-commit-branch-guard.

## [5.4.4] - 2026-06-30

### Fixed
- self-improve gate now catches a NAMED guard blocking the assistant. `ASST_PATTERN` matched
  "gate blocked me" but missed "rejected by the repo-gate hook" / "the venv-guard hook flagged my
  command" - the old patterns assumed `by the hook` (no name between) or `<guard> ... verb ... me`.
  Replaced with bidirectional proximity (`<guard> ... <verb>` OR `<verb> ... <guard>`, within 30 chars),
  so a named guard in either order fires. "gateway" still does not match "gate" (word boundary). (+1 test.)

## [5.4.3] - 2026-06-30

### Changed
- `meta-self-improve`: the public-contribution path now covers a universal rule that does NOT fit any
  existing skill - if it is substantial enough to warrant a NEW skill domain, propose one (built with
  `bitranox:meta-skill-writer`, named per the taxonomy in `skill-taxonomy.json` / `CONTRIBUTING.md`;
  the gated step-5 path - propose first, scaffold only on explicit permission), not only "enrich an
  existing skill".

## [5.4.2] - 2026-06-30

### Changed
- `web-frontend-responsive-ux`: corrected the thumbnail-rail drag-pan pattern (do NOT
  `setPointerCapture` on pointerdown - it redirects the click to the rail and kills the thumbnail
  link's navigation; gate dragging on actual movement and persist a `dragged` flag). Added patterns and
  common-mistakes for: pre-mounting a deferred heavy viewer hidden (`opacity:0`, still interactive) so
  the first gesture works without owning the LCP; compacting content-rich pages on phones (shrink, do
  not just reflow); keeping a shared element the same rendered size across pages; phantom scroll (an
  unreset `<body>` margin under `min-height:100svh/vh` overflows every profile by a constant); an
  always-open `<details>` menu (an explicit `display` overrides the native closed-hide); and the CSS
  source-order trap (a `@media` override placed before its base rule loses by source order).

## [5.4.1] - 2026-06-30

### Changed
- `meta-self-improve`: reworded the public-contribution criterion - sensitivity is NOT a disqualifier but
  a SCRUB step. If a universal rule still teaches its lesson once private specifics (paths, hosts, secrets,
  org/setup details) are removed or replaced with placeholders, clean it and contribute the scrubbed
  version; only a rule USELESS without those specifics stays private. (Was: "clearly universal AND
  non-sensitive", which wrongly excluded a useful rule that merely carried strippable specifics.)

## [5.4.0] - 2026-06-30

### Changed
- `meta-self-improve`: per-turn capture of a clearly-universal, non-sensitive rule whose topic matches a
  shipped skill's domain now also SURFACES it as a public-contribution candidate (route via the upstream
  self-PR loop, self-contained + provenance-free) - opt-in and propose-first, never auto-publish. Closes
  a gap where a universal rule stopped silently at the machine-local global layer (`~/.claude/rules/bitranox/`,
  which teaches only the maintainer) and the public-skill option was only raised by the dream's batch
  skill-fit pass or a manual nudge. The machine-local layer is your brain; a shipped skill is the shared brain.

## [5.3.0] - 2026-06-30

### Changed
- `compuse-bash`: new Quick-reference row "Keep / prune the NEWEST timestamped file(s)" - sort by MTIME
  (`ls -t`, or `find ... -printf '%T@ %p\n' | sort -zrn`), never by name/glob order. A varying prefix
  breaks lexical order, so a stale file is kept and a newer one deleted. (Surfaced by a real mis-prune
  of timestamped backups.)

## [5.2.1] - 2026-06-30

### Fixed
- `gather_scan.extract_keywords` (recall + cross-tree gather) now drops opaque identifiers that slipped
  past the token regex - Claude tool-use IDs (`toolu_...`), session UUIDs, long hex hashes, pure digits,
  and path slugs (>=4 hyphens) - which were polluting recall ranking and the per-project pending-keyword
  queue. Conservative: real hyphenated terms (`meta-dream-global-deep`, `px-websrv-media`) are kept. (+2 tests.)
- `git-footgun-guard` no longer false-fires on a valid single-revision `git rev-parse --short` that has a
  shell redirection: a redirection like `2>/dev/null` (or its space-separated target) was miscounted as a
  second revision. Redirections are now stripped before counting operands; a genuine 2-revision command
  still blocks. (+2 tests.)

## [5.2.0] - 2026-06-30

### Changed
- self-improve gate now catches the "I forgot a rule, now applying it" turn, which slipped through
  entirely. STRICT `ASST_PATTERN` gains assistant forward-commitment / rule-adoption ("from now on /
  going forward / next time I'll|will|should ...", "I'll make sure/remember to ..."). BROAD SessionEnd
  audit (`BROAD_ASST_PATTERN`) gains rule-citation ("per the <...> rule", the "<...>" rule, "following
  the <...> rule/convention") - a judgement-call signal routed to next-session review, not a live nudge.
  A bare "understood" stays excluded by design (it acknowledges a directive; the directive is the signal).
  `meta-self-improve` examples document forward-commitment + the understood/rule-citation rule. (+2 tests.)

## [5.1.0] - 2026-06-30

### Changed
- self-improve SessionEnd audit (broad recall) now flags mid-course inspection pauses ("let me stop and
  inspect", "let me double-check", "let me inspect/look again/take a closer look") as review candidates.
  These are deliberately BROAD-audit-only, NOT live-gate triggers: a pause only hints at a lesson, which
  resolves later into a discovery ("found it") or self-admission ("I should have") that the strict gate
  already catches. So they surface for next-session human review (lesson? anti-pattern?), never a
  premature per-turn nudge. `meta-self-improve` audit section documents the precursor-vs-resolved rule.
- self-improve strict USER gate now also fires on "rather than X, do Y" (+ German "anstatt"/"anstelle"),
  the synonym of the already-recognized "instead of"/"stattdessen" - a user directive that was slipping
  through. Assistant-side "rather than" is intentionally NOT a trigger (ordinary planning prose, too
  noisy). (+2 tests total.)

## [5.0.0] - 2026-06-30

### Changed
- BREAKING: renamed skill `web-frontend-responsive-audit` -> `web-frontend-responsive-ux`. It covers
  responsive layout plus cross-device usability/UX (no overflow, vertical fit, touch targets, gestures,
  safe-area, responsive images, i18n layout), so "ux" fits the breadth better than "audit", which
  undersold its fix-and-prescribe role. Invoke it as `bitranox:web-frontend-responsive-ux` and update
  any reference to the old name; the skill's content is otherwise unchanged.

## [4.25.0] - 2026-06-30

### Changed
- self-improve LIVE gate now fires on hindsight self-admissions, not just explicit ones.
  `self_improve_signals.py` `ASST_PATTERN` (strict Stop-gate) gains "I should have / I should've",
  "I missed / overlooked / forgot / misread / misunderstood", "I didn't realize/notice/account/
  consider/catch", and "in hindsight" - previously these surfaced only via the SessionEnd audit
  (`BROAD_ASST_PATTERN`), so the per-turn nudge missed them. "you should ..." (not a self-admission)
  is not matched. `meta-self-improve` self-admitted-miss examples updated. (+1 strict test; the two
  audit tests' broad-only example swapped to "let me reconsider".)

## [4.24.1] - 2026-06-30

### Changed
- `web-frontend-responsive-audit`: enforce iterate-on-overlay and release-once; add a large-surface
  spacing pattern. (Changelog entry backfilled - the version was bumped without one.)

## [4.24.0] - 2026-06-29

### Added
- New skill **`web-frontend-responsive-audit`**: responsive/usability audit for web frontends across
  device viewports, with detectors, device profiles, and verification engines. (Changelog entry
  backfilled - the version was bumped without one.)

## [4.23.0] - 2026-06-29

### Changed
- self-improve gate now recognizes "found it" / discovery phrasing as a realization signal.
  `self_improve_signals.py`: `REALIZATION_PATTERN` (live strict gate) gains `found it`, `found the
  bug/cause/culprit/...`, `found out why/how`, `the culprit is/was`, and German `<x> gefunden` / `da ist
  es` - with a negative lookbehind so "haven't found it" / "could not find it" do NOT trip it;
  `BROAD_ASST_PATTERN` (SessionEnd audit) gains the looser `found it/the/out`, `culprit`, `gefunden`.
  `meta-self-improve` realization examples updated to include "found it / found the root cause". (+1 test.)

## [4.22.0] - 2026-06-29

### Changed
- "Never track `.venv` / local build artifacts" is now a tool-agnostic git-hygiene rule with one
  canonical home and cross-refs (no duplication). `compuse-git` carries the full rule (new "Don't track
  local build artifacts" section + quick-ref row): a `.venv` from python -m venv / virtualenv / poetry /
  uv is equally off-limits, as are `__pycache__/`/`*.pyc`/`*.egg-info/`/`node_modules/`/`dist/`/`build/`;
  gitignore them and `git rm -r --cached` if already tracked (gitignore does not untrack). `coding-python-uv`
  and `process-test-design` now carry a one-line cross-ref to it instead of restating it.

## [4.21.0] - 2026-06-29

### Changed
- `coding-python-uv`: the venv section now states `.venv/` is a per-machine build artifact - never commit
  it; ensure it (plus `__pycache__/`, `*.pyc`, `*.egg-info/`) is in `.gitignore`, and if already tracked,
  untrack with `git rm -r --cached .venv`. Completes the test-venv-isolation guidance.

## [4.20.0] - 2026-06-29

### Changed
- `compuse-git`: new "Private git deps in CI need a read-only token" section (+ quick-ref row). A private
  repo depending on other private `git+https://github.com/<Org>/...` repos fails CI install with
  `could not read Username for 'https://github.com'`; fix = a read-only PAT Actions secret + a
  `git config url.insteadOf` rewrite. The token is loaded from a password file via stdin (gh secret set),
  never read or echoed by the agent; ask the user for the directory where their password files live, and
  to create the file if missing. Generic (no org/host names).

## [4.19.0] - 2026-06-29

### Changed
- Test-venv isolation made a first-class rule (the recurring "wrong interpreter under PyCharm" bug).
  `process-test-design`: new "Run in a clean, project-correct environment" section + checklist item -
  run in the project's own venv not the IDE's (`env -u VIRTUAL_ENV uv run pytest`); a ModuleNotFound /
  phantom type-error / pip-audit-noise failure is a WRONG-VENV smell, verify the interpreter before
  trusting it. `coding-python-uv`: the stray-VIRTUAL_ENV gotcha is sharpened into a DEFAULT (strip the
  ambient env for every local test/lint/build, do not wait for it to break) with the bmk variant and
  the interpreter-check one-liner; "fresh" = isolate to the project venv, recreate only when debugging
  corruption.

## [4.18.0] - 2026-06-29

### Changed
- Missing-rung detection now handles the "no shared/tracked home" case. When the folder that should hold
  a department/HQ rung is not itself a tracked shareable repo (a plain dir whose members are each their
  own repo), `meta-dream-global-deep` no longer proposes a bare untracked rung or an unsafe trim; it
  PROPOSES an umbrella repo named `umbrella-<topic>` (e.g. `umbrella-machines`) that version-controls
  only the rung CLAUDE.md files and ignores the nested member repos, and ASKS private or public
  (default private) and local-only vs remote. `meta-dream-project`'s reconciliation guard gains the
  matching trim-safety rule: never trim a tracked/shared lower copy into a less-durable broader home;
  propose the umbrella first.

## [4.17.0] - 2026-06-29

### Changed
- `infra-proxmox` 7.3: new "Running Docker on a Proxmox host / inside an LXC (host-ops)" note - Docker in
  an unprivileged LXC needs nesting+keyctl + iptables-legacy; kernel-global sysctls set inside an LXC are
  ignored (set them on the host under root_volume/etc/sysctl.d/); a wrapper that restarts Docker uses
  Wants=docker.service not Requires=; use `docker compose` v2 not `docker-compose` v1. Surfaced by the
  deep dream as shared fleet host-ops; folded into the shared skill (the host tree had no umbrella repo,
  so a tree rung could not be shared and trimming the per-host repos would have lost version-controlled
  knowledge).

## [4.16.0] - 2026-06-29

### Changed
- `coding-bash-reference`: new "Before you reach for Bash (and before you ship)" section - prefer a
  Python script over shell for real logic (the global working rule, woven in), and gate every Bash
  script you do ship with `shellcheck -x` + `bash -n` (required checks) before committing. Surfaced by
  the deep dream as a fleet-wide host-ops practice; it is good practice everywhere, so it lives in the
  skill rather than in any one project rung.

## [4.15.0] - 2026-06-29

### Changed
- **`meta-dream-global-deep` org-chart audit now detects MISSING rungs (departments and HQ)**,
  evidence-gated. A missing department = the nearest common-ancestor folder of >= 2 RELATED projects has
  no `CLAUDE.md`; a missing HQ = the top of the tree has no head-office rung. Trigger is evidence (a rule
  duplicated across related siblings that wants to consolidate into a rung that does not exist), not bare
  structure - placed at the lowest common ancestor whose children share a domain, never a generic bucket;
  structural-only look-alikes are surfaced as a question. The deep dream MAY propose a brand-new
  workspace-root HQ above the current highest `CLAUDE.md` (the one exception to gap-fill's conservative
  rule); the machine-global layer auto-creates on first promotion. Propose-only, user-gated; creating a
  rung is light (a new `CLAUDE.md`, no slug migration) but adds a tier to children's ancestor chain.
- `meta-self-improve`: noted that descriptor gap-fill stays conservative (never above the highest
  existing `CLAUDE.md`); proposing a new top-level HQ is the deep dream's job, user-gated.

### Docs
- `docs/self-learning-memory.md`: the departments section now covers the deep dream spotting a missing
  department / head office (a related cluster whose folder has no shared shelf) and offering to create it.

## [4.14.0] - 2026-06-29

### Changed
- **CLAUDE.md tiers are treated as altitudes; dreams now RECONCILE them to save context** instead of just
  flagging duplicates. The ancestor `CLAUDE.md` chain + memory + global form one altitude lattice under
  the existing reference+delta model, decided by "reduce total always-loaded context". When a rule is
  found duplicated: covered by a broader tier -> propose DELETING the lower copy (now valid at
  intermediate altitudes too, not just project-root/global); belongs higher -> lift up + leave the delta;
  only-here -> keep; contradiction -> fix memory, not the rule. Runs in both `meta-dream-project` (own
  chain) and `meta-dream-global` / `meta-dream-global-deep` (consolidate sibling duplicates UP across
  trees). All `CLAUDE.md` edits stay propose-first, never without confirmation.
- **`meta-dream-global-deep` gains an org-chart audit** (deep dream only, propose-only): assess whether
  the directory structure still fits and propose moving a drifted project to another department, creating
  a department folder for a flat cluster, or splitting an incoherent one - with the slug-migration +
  ancestor-chain + repo-path consequences spelled out. The dream never relocates a directory itself.

### Docs
- `docs/self-learning-memory.md`: new section "Group your projects like departments in a company"
  (HQ = global, grouping folder = department, project = desk; group related projects so shared rules live
  once at the department altitude). Section 1 now covers that a dream may take several cycles to converge
  (recurring-dream analogy), escalates a non-converging loop to you (intervention), and asks you for
  genuinely-yours decisions (therapist).

## [4.13.0] - 2026-06-29

### Added
- New skill **`meta-dream-global-deep`** - the exhaustive cross-project dream that ALWAYS runs the full
  semantic fan-out scan (every store + every CLAUDE.md), no convergence shortcut, no asking. The normal
  `meta-dream-global` now convergence-checks cheaply first and ASKS before launching the expensive scan;
  `-deep` is for when you want the thorough read regardless.

### Changed
- **Dreams now dedup promotions against CLAUDE.md, not only memory stores.** During the conversion phase
  many cross-project rules still live in `CLAUDE.md`; promoting one already there would duplicate it.
  `meta-dream-global` (step 4 gate) and `meta-dream-project` (promotion step) now grep each candidate
  against the project + ancestor + workspace `CLAUDE.md` before promoting: already-there -> do NOT
  duplicate, FLAG for the user; never edit `CLAUDE.md` without confirmation.
- `meta-dream-global` step 3: cheap convergence/integrity pre-check, then ask before the deep fan-out
  (was: unconditional fan-out).
- Skill content from the cross-project scan: `compuse-ssh` (long remote reload outlives the SSH timeout
  -> verify real state, never infer failure from a dropped connection); `coding-python-clean-architecture`
  (no concrete paths/URLs/hostnames in the domain - config flows from the composition root; a no-env-read
  test proves layer purity); `coding-python-use-modern-libraries` (httpx2 is the legit Pydantic-org
  successor, scanner typosquat flags are false positives - re-verify, do not auto-swap).

## [4.12.0] - 2026-06-29

### Changed
- **Recall hook now also searches other projects' `CLAUDE.md`**, not only their Auto-memory. A lot of
  cross-project knowledge still lives in `CLAUDE.md` (conversion phase), so the per-prompt "check the
  notebook" pass would otherwise miss it. New `gather_scan.discover_claude_md(cwd)` walks up to the
  workspace root (highest ancestor holding a CLAUDE.md), finds every CLAUDE.md under it, EXCLUDES the
  current project's ancestor chain (already loaded in-session) and vendored dirs, and caches the file
  list per root with a 1h TTL so the per-prompt cost stays grep-only. The recall hook injects a snippet
  CENTERED on the first matched keyword (large CLAUDE.md files would miss the match under head-trunc)
  and labels each as `<parent-dir>/CLAUDE.md`. (+4 tests.)

## [4.11.0] - 2026-06-29

### Added
- New skill **`process-test-design`** - the WHAT-to-write companion to `process-test-driven-development`
  (which owns red-green). Consolidates the scattered test-quality rules: prefer real/integration/e2e
  over mocks; dependency injection over monkeypatching (patch only a true external edge); the
  adversarial boundary-input battery (unusual UTF, emoji, CJK, binary, wrong types, oversized, edge
  numbers - the test side of `coding-input-sanitization`); determinism + order-independence (no
  execution-order dependence, no real `sleep`, injected clock/seed, offline unit suite); and pruning
  low-value tests (assert-nothing, impl-mirroring, mock-testing, duplicate). Added to the catalog;
  cross-referenced from `process-test-driven-development` and `coding-input-sanitization`.

## [4.10.0] - 2026-06-29

### Added
- New skill **`coding-input-sanitization`** - the single canonical home for untrusted-input handling,
  scoped to the TRUST BOUNDARY (application / facing-API edge), explicitly NOT the libraries between
  boundaries. Two directions: validate-and-bound on the way IN (typed model, length/size limits,
  charset), escape-per-sink on the way OUT - parametrized SQL (SQL injection), HTML autoescape (XSS),
  argv-not-shell (command injection), path-traversal, deserialization, SSRF, header/log injection.
  Five skills now cross-reference it instead of restating the rules: `coding-python-clean-architecture`,
  `coding-python-enforce-data-architecture-strict`, `process-review-enhance-code-quality`,
  `coding-rust`, `coding-bash-reference`. (The always-on baseline lives in the machine-local global
  rules layer, not shipped here.)

## [4.9.2] - 2026-06-29

### Fixed
- `reconcile_memory_index` reference resolver now also matches a note's frontmatter `name:`, not only
  its filename stem. So a `[[ref]]` resolves whether it used the filename
  (`feedback_generalize_learnings`) or the note's declared name (`generalize-learnings`) - the
  name-vs-filename mismatch class no longer becomes a false orphan. A new `_entry_slugs()` indexes each
  note by stem AND name (both `_canon`-folded); `check_references` and the demotion-safety
  `has_inbound_refs` (which now expands the queried note to all the slugs it answers to) route through
  it. (+2 tests.)

## [4.9.1] - 2026-06-29

### Fixed
- `reconcile_memory_index` reference resolver is now SEPARATOR-INSENSITIVE: a `[[ref]]` matches its
  target note regardless of hyphen/underscore drift (`[[feedback-no-em-dashes]]` resolves to
  `feedback_no_em_dashes.md` and vice versa). A `-` vs `_` mismatch was the single biggest source of
  false orphan refs across the stores. A new `_canon()` folds case and `-`/`_`; `_ref_slug`, the target
  index, the self-ref skip, and `has_inbound_refs` all route through it. (+2 tests.)

## [4.9.0] - 2026-06-29

### Added
- **Pathfinder discipline** woven into the marketplace skills: leave every file better than you found it,
  accept no technical debt (point mistakes out clearly, never "works anyway"), route an out-of-scope fix
  to its own worktree, and clean up temporary scaffolding when done. Canonical statement is a new
  "Pathfinder discipline" section in `meta-self-improve`; an always-on reminder is in the
  SessionStart-loaded `meta-using-bitranox-skills`; and one-line cross-references are in
  `process-review-enhance-code-quality`, `process-review-receiving-code-review`, and
  `process-agents-subagent-driven-development` (with the out-of-scope-fix rule cross-linking
  `git-worktrees`).

## [4.8.2] - 2026-06-29

### Changed
- Dream skills: make dedup/normalize an explicit **final sweep after promotion**, not only a pre-pass.
  Promotion is what *creates* duplication (a rule lifted up now overlaps the note it came from and any
  sibling holding the same lesson), so a dedup that runs only before promoting leaves the just-promoted
  general duplicated below it. `meta-dream-project` step 8 now re-dedups the promotion-touched notes
  before reconcile (and step 4 notes that dedup runs twice); `meta-dream-global` step 6 is now an
  explicit "re-dedup after promotion (required final sweep)". Net per-note bytes can be a wash; the win
  is one source of truth instead of restating the general in every note.

## [4.8.1] - 2026-06-29

### Changed
- Folded two universal learnings from the global-dream scan into their right skills:
  - **`compuse-bash`**: exit 0 is necessary but NOT sufficient - ALSO verify the real artifact/output
    (some tools exit 0 while writing nothing or silently ignoring options, e.g. `vips out.tif[opts]`).
  - **`coding-python-uv`**: gotcha - a stray `VIRTUAL_ENV` (IDE / other project) hijacks `uv` /
    `pip-audit` / `tox` / Makefile targets; unset it (`env -u VIRTUAL_ENV`) or pin the project venv.
- The remaining cross-cutting working rules from the scan (no secrets in tracked files, read-before-Edit,
  docs-describe-current-state, inline-comments-explain-WHY) were promoted to the machine-local global
  rules layer (`~/.claude/rules/bitranox/`), which is not shipped in this repo.

## [4.8.0] - 2026-06-29

### Added
- New skill **`coding-rust`** - Rust idioms / review checks distilled from real review learnings
  (surfaced by a global-dream scan across all project memory stores): no `std::io::Error` for non-IO
  conditions (add a `thiserror` variant), preserve the error chain, constant-time secret comparison,
  `--password-file` over inline `--password`, minimal purpose-specific crates + feature-gating heavy
  optional deps, and making invalid states unrepresentable. Added to the skills catalog.

### Notes
- This release is the productive output of testing `meta-dream-global`: the cross-project scan
  (12 sonnet readers over 32 stores, privacy scrub excluding all domain-private content) found that
  almost all universal knowledge is already encoded in skills/hooks, so it proposed no new global-rule
  bloat - except the user-stated "no Claude/AI commit attribution" rule, promoted to the machine-local
  global layer (`~/.claude/rules/bitranox/`, not shipped in this repo), and the Rust idioms above, which
  belong in a skill rather than the always-loaded global layer.

## [4.7.0] - 2026-06-28

### Changed
- Split the dream skill by scope into two explicit commands (the word "dream" alone was ambiguous):
  - **`meta-dream-project`** - the frequent, cheap consolidation of the CURRENT project (the old
    `meta-dream`, renamed). Keeps `dream_state.py`, the SessionStart "consolidation due" nudge, and the
    behavioral passes (demotion, obsolete-prune, override, CLAUDE.md reconcile, per-project
    filler-classification, model-review). Triggers: "dream", "dream project", "/dream-project",
    "consolidate memory".
  - **`meta-dream-global`** (NEW) - the occasional, expensive cross-project pass: the global-dream scan
    across all project stores (sonnet fan-out -> opus promotion gate), inbound gather, outbound
    cross-pollination. Triggers: "dream global", "/dream-global", "consolidate across projects".
  Renaming `meta-dream` -> `meta-dream-project` removes the old `/meta-dream` skill name (the "dream"
  natural-language trigger is preserved). Updated every cross-reference: `meta-self-improve`,
  `meta-collect-knowledge` (its inbound-pass pointer now targets `meta-dream-global`), the skills
  catalog in `meta-using-bitranox-skills`, the SessionStart / PostCompact nudge text, `README.md`, and
  `docs/self-learning-memory.md` (added the "short nap vs deep sleep" analogy for the two dreams).

## [4.6.0] - 2026-06-28

### Changed
- Recall filler/topical lists are now **per-project** (were machine-global). The shipped
  `filler_words.json` baseline stays **global** (universal generic-English filler, PR-only); the
  **learned filler blacklist**, the **topical whitelist**, and the **pending classification queue** are
  now keyed per project (`~/.claude/self-improve-audit/<proj_key>.{filler,topical,recall-unknown}`).
  This fixes a cross-project contamination bug: a word a dream classified as filler in one project no
  longer suppresses recall of that word in another project where it is a real topic (e.g. `compression`
  is noise in a docs project but a topic in a codec project). The effective blacklist for a prompt is
  `global baseline UNION the current project's learned filler`. `extract_keywords`, `load_filler_words`,
  `add_filler_words`, `load_topical_words`, `add_topical_words`, `note_unknown_keywords`,
  `load_pending_keywords`, `clear_pending_keywords` now take the project; the recall hook and gather CLI
  pass the current `cwd`. The meta-dream filler-classification pass writes per-project.
- Legacy machine-global learned lists (`~/.claude/.bitranox-filler-words.json` etc., a 4.5.x artifact)
  are NOT auto-migrated - the next per-project dream re-learns them. (On the maintainer machine they
  were migrated into the originating project by hand.)

## [4.5.3] - 2026-06-28

### Added
- End-to-end integration test for the memory system (`hooks/tests/test_e2e_memory_system.py`). Unlike
  the per-script unit tests, it drives every component through its REAL entry point - subprocess
  stdin/stdout for the hooks (`recall-memory`, `session-start`, `self-improve-gate`) and CLI argv for
  the helpers (`settings`, `dream_state`, `gather_scan`, `reconcile_memory_index`) - against an
  isolated sandbox HOME, proving they are wired together (settings round-trip, model-review marker,
  new-project nudge self-silencing, recall surfacing + session-dedup + filler/corpus-common
  suppression + self-exclusion, filler-classification queue, cross-tree gather, dream cadence, index
  backfill + dangling-reference `--check`, learning-signal detection). Runs in CI with the unit suite.

## [4.5.2] - 2026-06-28

### Fixed
- Memory-recall precision, round 2 - corpus-stopwording. A keyword can carry no signal yet not be
  generic-English filler: a word common in YOUR store (e.g. "memory" in a memory-centric knowledge
  base - 83% of notes) is a de-facto stopword the static filler list cannot catch. Recall now drops
  such corpus-common keywords (present in > 25% of the store AND not absolutely rare, `df > 6`) from
  both the qualify gate and the inverse-frequency score, so a note matching ONLY corpus-common words
  is no longer surfaced. The absolute-rarity floor keeps a tiny store (where any word is a big
  fraction) from misfiring. Ranking remains an additive IDF sum (one independent weight per useful
  keyword - no combinatorial scoring).

## [4.5.1] - 2026-06-28

### Fixed
- Memory-recall precision. A conversational prompt (e.g. "i got again hits on my previous answer - is
  that normal?") surfaced several unrelated notes. Two causes: (1) keyword matching was SUBSTRING-based,
  so "again" matched "against" and "test" matched "latest" - switched to WORD-BOUNDARY matching;
  (2) generic/conversational words became search keywords - added a filler-word blacklist.

### Added
- Filler-word blacklist for recall keyword extraction: a shipped baseline (`hooks/filler_words.json`)
  unioned with a machine-local list. The per-prompt recall hook stays deterministic / model-free - it
  drops known filler and QUEUES any not-yet-classified keyword; the new `meta-dream` filler-classification
  pass (a `sonnet` subagent) drains the queue, appending confirmed filler to the machine-local list and
  topical words to a known-good cache (conservative: unsure -> topical). Classification is off the
  per-prompt hot path (sleep-time only).
- `self_improve_signals` helpers: `load_filler_words` / `add_filler_words`, `load_topical_words` /
  `add_topical_words`, `note_unknown_keywords` / `load_pending_keywords` / `clear_pending_keywords`,
  plus `model_review_due` / `mark_model_reviewed` (the 4.5.0 model-hierarchy-review marker).

### Changed
- `docs/self-learning-memory.md`: expanded the notebook-recall reflex with the token-economy rationale
  (re-deriving costs more than reading a note; the glance gets cheaper and saves tokens over time) and
  the dream-offload of slow learning; corrected the forgetting section to the no-usage/age-based-decay
  reality (removal = dedup + obsolete-prune + manual only); added the "right tool for the right job"
  model-tier analogy.

## [4.5.0] - 2026-06-28

### Added
- Subagent model-tier doctrine. A canonical "Concrete tiers" mapping in
  `process-agents-subagent-driven-development`: `opus` for deep reasoning / synthesis / adversarial
  correctness-verify / architecture; `sonnet` as the default fan-out workhorse (bounded extraction,
  relevance, per-dimension/per-file/per-store reviewers); `haiku` for mechanical work. Dispatches use the
  stable tier ALIASES so a new model version is picked up with no edit. Cross-referenced from
  `process-agents-dispatching-parallel` and baked into `meta-skill-writer` scaffolding (a skill that
  dispatches subagents must pin a tier).
- Pinned model tiers in the existing dispatchers (`process-review-requesting-code-review`,
  `coding-python-enforce-data-architecture-strict`, `process-agents-dispatching-parallel`,
  `meta-skill-writer`).
- Added subagent fan-out (with tiers) to skills that did heavy/parallel/judgment work inline:
  `process-review-enhance-code-quality` (parallel `sonnet` per rubric dimension -> `opus` synthesis),
  `meta-dream` global scan (`sonnet` per-store -> `opus` judgment), `meta-collect-knowledge` inspect
  (`sonnet`), `process-review-verification-before-completion` (`opus` adversarial verifier),
  `coding-python-performance-review` (`sonnet`), `process-debug-systematic` Phase 2 (`sonnet` finders),
  `meta-adopting-external-skills` (`sonnet` repo analysis, `haiku` license map).
- Periodic model-hierarchy review in `meta-dream` (time-gated via `model_review_due` /
  `mark_model_reviewed`): asks the `claude-code-guide` agent for the current lineup and proposes a
  re-tier via the self-PR loop when the capability/cost ordering shifts. Model releases are infrequent,
  so it runs monthly-ish, not every dream.

### Changed
- `docs-convert-markitdown` default model is now `anthropic/claude-sonnet-4.5` (cheaper/faster);
  opus remains recommended for hard vision / presentations / OCR.

## [4.4.2] - 2026-06-28

### Changed
- Forgetting is gone as an automatic mechanism, because usage cannot be measured (a note sits in
  context and the model reasons over it silently, so absence of a signal does not mean unused) and age
  and detail/size are not valid forget metrics. Removed the dead idle helpers
  (`bump_idle`/`reset_idle`/`should_archive` + the idle file) and the `forgetting` / `forget_idle_dreams`
  config knobs. Memory removal is now ONLY: dedup/merge, obsolete/superseded pruning (model-judged on
  content - a deleted file/flag, a resolved issue, a superseded entry - propose-first), or a manual
  request. `archive_entry` and `has_inbound_refs` are kept (mechanical move + demotion safety).
- Recall hook precision: candidates are ranked by keyword RARITY (inverse document frequency) instead
  of a flat >= 2-keyword filter. A note matching one rare/specific term outranks one matching only a
  common token like "test"; common-only matches are dropped; a lone specific keyword still surfaces.

## [4.4.1] - 2026-06-28

### Fixed
- Reference-integrity `--check` no longer hangs or false-positives. `altitude_chain` previously walked
  to `/` and the check `rglob`'d every ancestor (scanning the whole filesystem for `*.md`). Now: the
  chain is the contiguous set from the project up to the HIGHEST existing `CLAUDE.md` (gap levels
  included, never above it); only the project memory (flat) and the global layer (recursive) are scanned
  for slugged entries; ancestor `CLAUDE.md` altitudes and non-entry files (`CLAUDE.md`, `CHANGELOG.md`,
  `README.md`, ...) are excluded - so code like `Callable[[...]]` or a CHANGELOG mention of `[[general]]`
  is no longer mis-read as a dangling reference.
- Recall precision: the per-prompt recall hook now requires >= 2 keyword hits (or the single keyword
  when only one is significant), so a common token like "test" no longer surfaces dozens of weak matches.

### Changed
- Forgetting is OFF by default and must be USAGE-based, never age/dream-count, never detail-level/size.
  The accidental age-based archive pass is removed from the dream; detail still goes to pulled bodies
  (representation, not deletion). A real usage meter (recall hits + an in-project memory-read signal +
  inbound references) is required before any usage-based, propose-first forgetting is enabled.
- The dream's descriptor step fills `CLAUDE.md` scope-descriptor GAPS up to the highest existing
  `CLAUDE.md` (create the missing levels, propose-first) so the classifier has a descriptor at every
  altitude, rather than skipping gaps.

## [4.4.0] - 2026-06-28

### Added
- Per-prompt memory recall: a `UserPromptSubmit` hook (`recall-memory.py`) that, on each prompt, does a
  fast keyword grep across your OTHER projects' memory and the global rules layer (reusing the existing
  `gather_scan.py` engine; the current project is excluded, so what it draws in is de-duplicated against
  your own memory) and injects the strongest matching notes' bodies as advisory context - once per
  session. The "look in my notebook before reinventing" reflex on top of the always-present index.
  Read-only (it surfaces; it does not copy/promote - that stays meta-collect-knowledge). Fail-open.

## [4.3.1] - 2026-06-28

### Fixed
- Renamed the two duplicate-basename `test_strip_typographic_tells.py` files (write-humanize-en/-de) to
  `_en`/`_de` suffixes so a plain `pytest` over the tree collects without an import-file-mismatch. The
  CI gate was unaffected (it already runs `--import-mode=importlib`); this fixes the naive developer run.

## [4.3.0] - 2026-06-28

### Added
- Layered memory, Phase 2 (cross-tree): knowledge can now flow between sibling project trees, not just
  down one ancestor chain.
- New skill `meta-collect-knowledge` (`/collect-knowledge`): the inbound cross-tree gather via a
  grep -> inspect -> gather funnel. Ships `gather_scan.py` (deterministic stage-1: derive keywords,
  grep other projects' memory + the global rules layer, excluding the current project) so the model
  step runs only on a hit. Brings knowledge in by lifting to a common ancestor or a self-contained
  copy - never a cross-tree reference - with a secret/PII scrub on cross-boundary writes. Also runs as
  meta-dream's inbound pass, and powers the new-project bootstrap nudge (now active).
- New skill `meta-memory-settings` (`/memory-settings`): view/set/reset the informed-consent knobs
  (dream mode, privacy, promotion eagerness, forgetting, nudges) in `~/.claude/.bitranox-memory.json`,
  via a small `settings.py` CLI. A recorded choice is applied automatically, never re-asked.
- `meta-dream` gains the cross-tree passes: inbound gather (delegated), outbound cross-pollination
  (promote to the lowest common ancestor; native cascade delivers it; rare self-contained copy), and a
  global-dream cross-project scan with a cross-project corroboration path. All honor the `privacy` knob.

## [4.2.1] - 2026-06-28

### Added
- Layered memory, Phase 1.5 (counter-gated behavioral passes; counters live outside the dreamed store
  so consolidation stays a no-op on an unchanged store):
  - Forgetting / decay: out-of-store per-entry idle counter (`bump_idle`/`reset_idle`),
    `should_archive` honoring a `forgetting` knob (off / conservative / aggressive), and
    `reconcile_memory_index.archive_entry` that moves an idle non-must-always body to a cold `.archive/`
    and drops its index line (bias toward keeping; must-always is never archived).
  - Demotion safety: `reconcile_memory_index.has_inbound_refs` so an entry that lower entries still
    reference upward is never demoted; demotion reuses the promotion dwell/hysteresis.
- `meta-dream` gains the behavioral passes: demotion, forgetting/decay, contradiction/override
  (CLAUDE.md authoritative; memory override = more-specific wins), and CLAUDE.md reconciliation
  (back up before edit; integrate overlap into a same-scope always-present home and propose deletion;
  intermediate-altitude overlaps are flag-only).

## [4.2.0] - 2026-06-28

### Added
- Layered memory, Phase 1 (core). Knowledge is now placed by SCOPE across always-present homes:
  per-project Auto memory, a global cross-project layer at `~/.claude/rules/bitranox/` (native
  whole-loaded user rules, recursion confirmed; never touches the user's hand-written CLAUDE.md), and
  CLAUDE.md only for must-hold intermediate-subtree rules. Concrete-but-universal facts are promoted
  KEPT CONCRETE, not abstracted away.
- Normalization instead of duplication: a specialized entry `references [[general]]` and adds only its
  delta; references point UPWARD only (deletion-safe). `reconcile_memory_index.py --check` verifies
  reference integrity (orphans, downward refs) across the altitude chain and warns on an over-cap
  `MEMORY.md`.
- Quality/dwell gate before global promotion (the global layer loads into every session): user-stated
  concrete rules promote eagerly; model-inferred generalizations need corroboration across >= 2 dreams.
  Counters live outside the dreamed store, so consolidation stays convergent.
- One machine-local config `~/.claude/.bitranox-memory.json` (`load_config`/`save_config`) for the
  informed-consent knobs (dream mode, promotion eagerness, forgetting, nudges), migrating the legacy
  `.bitranox-dream-*` sentinels one-way. A `nudges` flag can switch session nudges off.
- Per-level scope descriptor support (a bounded, diff-free `<!-- bitranox:self-learning -->` block) and
  new helpers in `self_improve_signals.py`: `global_rules_dir`, `altitude_chain`, project seeding, and a
  "store changed under me" signature.
- A dormant new-project bootstrap nudge (activates only once the Phase-2 `meta-collect-knowledge` skill
  is installed and there is knowledge to seed from).

### Changed
- `meta-self-improve` and `meta-dream` rewritten to the scope-based multi-altitude model (concrete
  homes, normalization, upward-only references, descriptor-guided classification, config as the single
  source of truth for modes/knobs); `self-improve-gate.py` nudge text updated to match.

## [4.1.0] - 2026-06-27

### Added
- `meta-dream` skill: periodic memory consolidation ("sleep" to self-improve's per-turn capture). It
  backs up the memory store, then dedups/merges/generalizes/re-wires/prunes it and the session,
  routes generalized must-hold rules to the right-altitude CLAUDE.md (creating it if missing) with
  dual representation (combine general+specific, or split across altitudes, cross-linked), and batches
  skill-worthy generalizations into one self-PR via self-improve's upstream loop. A tri-state mode
  (opt-out sentinels in ~/.claude) controls it: `off` (no nudges; memory-only), `auto` (apply without
  asking), `propose` (default). Ships `dream_state.py` (due/done/mode cadence marker).
- Trigger wiring: a self-silencing SessionStart nudge when a consolidation is due
  (`dream_due` in `self_improve_signals.py`); the SessionEnd audit hook now also runs at **PreCompact**
  to salvage candidate learnings from the still-full transcript before compaction; a new
  **PostCompact** hook (`post-compact-nudge.py`) injects a capture/consolidate reminder afterward.

## [4.0.1] - 2026-06-27

### Changed
- Stripped pre-existing typographic AI-writing tells (em/en dashes, curly quotes, ellipsis,
  non-breaking/zero-width spaces) to ASCII across 135 shipped reference docs and a few code
  comments/strings, using the `write-humanize-en` strip tool. The two humanize SKILLs (which teach
  about tells) and the `coding-python-textual` screenshot SVG are intentionally left as-is.

## [4.0.0] - 2026-06-27

### Changed (BREAKING) - every skill renamed to the category-prefix scheme

All skills now carry a category prefix (`<category>-[<sub>-]<name>`). Invocation names changed,
so update any saved references to the new names below. The full current catalog is the
`bitranox:meta-using-bitranox-skills` domains list; categories live in `skill-taxonomy.json`.

New invocation names:

- `bitranox:process-plan-brainstorming` (brainstorming)
- `bitranox:process-plan-writing-plans` (writing-plans)
- `bitranox:process-plan-executor` (plan-executor)
- `bitranox:process-agents-dispatching-parallel` (dispatching-parallel-agents)
- `bitranox:process-agents-subagent-driven-development` (subagent-driven-development)
- `bitranox:process-debug-systematic` (systematic-debugging)
- `bitranox:process-test-driven-development` (test-driven-development)
- `bitranox:process-review-requesting-code-review` (requesting-code-review)
- `bitranox:process-review-receiving-code-review` (receiving-code-review)
- `bitranox:process-review-verification-before-completion` (verification-before-completion)
- `bitranox:process-review-enhance-code-quality` (enhance-code-quality)
- `bitranox:process-ship-finishing-development-branch` (finishing-development-branch)
- `bitranox:coding-python-clean-architecture` (python-clean-architecture)
- `bitranox:coding-python-enforce-data-architecture-strict` (python-enforce-data-architecture-strict)
- `bitranox:coding-python-performance-review` (python-performance-review)
- `bitranox:coding-python-use-modern-libraries` (python-use-modern-libraries)
- `bitranox:coding-python-gitignore` (python-gitignore)
- `bitranox:coding-python-rpyc` (rpyc), `bitranox:coding-python-textual` (textual),
  `bitranox:coding-python-uv` (uv)
- `bitranox:coding-bash-clean-architecture` (bash-clean-architecture),
  `bitranox:coding-bash-reference` (bash-reference)
- `bitranox:files-edit-json` (edit-json), `bitranox:files-edit-xml` (edit-xml),
  `bitranox:files-edit-yml` (edit-yml)
- `bitranox:docs-md-table-formatting` (md-table-formatting),
  `bitranox:docs-convert-markitdown` (markitdown)
- `bitranox:compuse-bash` (computer-use-bash), `bitranox:compuse-git` (computer-use-git),
  `bitranox:compuse-ssh` (computer-use-ssh), `bitranox:compuse-vnc` (computer-use-vnc)
- `bitranox:git-worktrees` (unchanged)
- `bitranox:infra-proxmox` (proxmox), `bitranox:infra-proxmox-bindsnap` (proxmox-bindsnap)
- `bitranox:net-rotating-proxies` (rotating-proxies)
- `bitranox:write-humanize-en` (humanize-en), `bitranox:write-humanize-de` (humanize-de)
- `bitranox:marketing-rory` (rory)
- `bitranox:meta-self-improve` (self-improve), `bitranox:meta-skill-writer` (skill-writer),
  `bitranox:meta-adopting-external-skills` (adopting-external-skills),
  `bitranox:meta-using-bitranox-skills` (using-bitranox-skills)

The `skill-taxonomy.json` registry's `legacy`/`retrofit` migration data is removed now that the
rename is applied; the registry is just the forward category vocabulary.

## [3.14.0] - 2026-06-27

### Added
- Category-prefix naming scheme for skills: `<category>-[<sub>-]<name>` (e.g.
  `coding-python-clean-architecture`, `compuse-ssh`, `marketing-rory`). A new
  `plugins/bitranox/skill-taxonomy.json` registry defines 26 top-level categories (with seed
  sub-prefixes), grounded in real-world skill directories. `repo-gate.py` `check_skill_naming`
  forces every NEW skill's top-level prefix to be a registry category (sub-prefixes free-form);
  `adopt_skill.py` validates the same on adoption. Opening a new category is a deliberate registry
  edit. The 41 existing flat names are grandfathered (`legacy`) until a future retrofit MAJOR, whose
  full rename map is prepared in the registry (`retrofit`). CONTRIBUTING documents the scheme and
  tie-break rules; skill-writer points authors at a marketplace's naming registry.

## [3.13.0] - 2026-06-27

### Added
- SessionStart auto-update reminder: when marketplace auto-update is OFF for `bitranox-skills`,
  `session-start.py` emits a one-line `systemMessage` explaining how to enable it (`/plugin` UI or
  `extraKnownMarketplaces.<name>.autoUpdate` in settings.json). It is **self-silencing** - it stops
  once auto-update is enabled in user/project settings - and can be dismissed without enabling by
  creating `~/.claude/.bitranox-no-autoupdate-nudge`. A plugin cannot set auto-update itself; this
  only reminds. README gained an "Enable auto-update (recommended)" section.

## [3.12.0] - 2026-06-27

### Changed
- `self-improve` is now **native-first** about memory. Durable learnings are written to `MEMORY.md`
  (one-line index entry) + a topic-file body - the index line is what makes a learning present.
  A memory MCP server (`basic-memory`/`server-memory`) is no longer treated as a write path or home:
  routing learnings through it skips the `MEMORY.md` index (not present) and a pull store is not
  searched (lost). An MCP now earns its place only at genuine scale AND with a real recall mechanism,
  indexing the native dirs as a search augmentation - never the sole store.

### Added
- `self-improve/reconcile_memory_index.py`: a maintenance utility that backfills a `MEMORY.md` index
  line for every topic file that lacks one (additive, idempotent, never deletes; reports orphans).
  Repairs an index that drifted from its topic files after out-of-band/MCP writes.

## [3.11.0] - 2026-06-27

### Added
- `self-improve` end-of-session miss audit (self-tuning loop): a new **SessionEnd** hook
  (`self-improve-audit.py`) scans the whole transcript and records **candidate misses** - turns a
  broad recall pattern flags but the precision-tuned gate did not catch - to a per-project audit
  file. The **SessionStart** hook (`session-start.py`) surfaces that audit once next session so the
  model reviews the misses, captures their learnings, and extends the gate. SessionEnd cannot nudge
  the model, so the analysis is deterministic and the review is deferred to the next start.
- `self_improve_signals.py`: shared single source of truth for the strict gate patterns (now
  imported by the gate) plus the broader recall patterns and the audit-file location, so the gate
  and the audit can never drift.

## [3.10.3] - 2026-06-27

### Changed
- `self-improve` gate: idea endorsement is now detected from **either side**. The high-signal case
  is the assistant judging the user's suggestion good ("good idea", "good call" -> the user found the
  better path, adopt it); it still also fires when the user endorses the assistant's proposal (a
  confirmed approach). Factored into a shared `_ENDORSE_PATTERN` checked against both messages; a
  bare "ok/thanks/nice" still does not fire. (Corrects 3.10.2, which only checked the user side.)

## [3.10.2] - 2026-06-27

### Changed
- `self-improve` gate: user endorsement of a proposed idea is now a learning signal ("good idea",
  "good call", "nice catch", "let's do that") - it marks a confirmed approach worth recording. A
  bare "ok/thanks/looks good" still does not fire. The skill and gate now frame signals as families
  (user correction / remember / endorsement; assistant self-admission / realization) and say to
  extend the whole family rather than one phrase at a time.

## [3.10.1] - 2026-06-27

### Changed
- `self-improve` gate: broadened the realization signal to the "clear" family - "now it's clear",
  "I have a clearer picture", "the full picture", "makes sense now" - while still not firing on a
  plain "the requirements are clear" / "is that clear?".

## [3.10.0] - 2026-06-27

### Added
- `adopting-external-skills` skill: a playbook plus a `adopt_skill.py` helper for bringing a useful
  third-party Claude Code skill (a repo URL, an installed plugin path, or a pasted `SKILL.md`) up to
  bitranox standards and into this marketplace. It runs a blocking license gate (accept the permissive
  family MIT/BSD/ISC/Apache-2.0, reject copyleft, never assume MIT when a license is absent), normalizes
  naming and cross-references, scaffolds tests, and records attribution. It is upstream-first - push the
  improvement to the original author first - and never removes or disables the user's other plugins.
- `plugins/bitranox/THIRD_PARTY_NOTICES.md`: per-skill attribution and license texts for adapted skills,
  shipped with the plugin so the notice travels with every install. Seeded with the existing adaptations.
- `repo-gate.py` `check_attribution`: keeps every `> Adapted from ...` credit line in sync with a
  `THIRD_PARTY_NOTICES.md` entry (no orphan credit lines or notices).

### Changed
- `self-improve`: realizations now count as a learning signal. The gated Stop hook fires on
  discovery phrasings ("now I understand the real ...", "I figured out ...", "it turns out ..."),
  and the skill routes a discovered infrastructure/architecture/topology/data-flow fact at the
  right altitude (own infra spanning projects -> top-level CLAUDE.md; one project -> its
  CLAUDE.md/memory; unsure -> ask). The memory backend is framed as a push/pull choice: must-hold
  standing rules stay in `MEMORY.md`/CLAUDE.md, the episodic tail can live in an installed memory
  MCP server (`basic-memory` or `server-memory`).
- `skill-writer`: new rule "Persisting durable state: choose a memory backend" - a skill that stores
  durable facts must treat the backend as a push/pull choice (standing rules in `MEMORY.md`/CLAUDE.md,
  episodic tail in a memory MCP server) rather than hard-coding `MEMORY.md`.

## [3.9.0] - 2026-06-26

### Added
- `python-gitignore` skill: git-exact `.gitignore` parsing and path filtering (include/whitelist mode,
  memory-bounded for millions of paths) via the `igittigitt` library/CLI - install, config, library
  API, CLI, and bash piping. Added the matching row to `python-use-modern-libraries` (prefer
  `igittigitt` over hand-rolled fnmatch/glob/re, `gitignore_parser`, or `pathspec`).
- `self-improve`: a "Scaling memory as it grows" section - keep entries lean (one-line index, edit over
  append); when the index gets too big, add the `basic-memory` MCP for semantic search over the existing
  markdown memory files (with the caveat to disable its frontmatter-rewriting flags first and back up +
  diff). Keeps must-hold rules in MEMORY.md/CLAUDE.md (push, always loaded) and uses basic-memory for the episodic tail (pull, on-demand search); `@modelcontextprotocol/server-memory` noted as a knowledge-graph alternative.

## [3.8.0] - 2026-06-26

### Added
- `proxmox-bindsnap`: install, verify, configure and operate pve-bindsnap on a Proxmox VE node -
  snapshot and clone LXC containers that have bind/device mounts (the `BINDSNAP-FORCE-RUNNING`,
  `BINDSNAP-UNSUPPORTED`, `BINDSNAP-EXCLUDE` markers, the checksum guard / untested-build workflow,
  cloning, and uninstall).

## [3.7.0] - 2026-06-26

### Changed
- `python-use-modern-libraries`: sharpened the structured-data guidance - `pydantic` to parse
  untrusted input at every boundary, `dataclasses` for pure internal layers, and `attrs` /
  hand-woven classes / raw `dict`s added to what to avoid. Cross-links the
  `python-enforce-data-architecture-strict` skill for the full end-to-end discipline.

## [3.6.0] - 2026-06-25

### Added
- `computer-use-git`: a "review for leaked data before push / PR / publish" section - scan the WHOLE
  push range (every unpushed commit, plus `--all`/`--tags`/side branches), not just the last diff, for
  secrets, private infrastructure, and personal data; use documentation-safe placeholders; history is
  hard to scrub once pushed. Brief cross-referencing gates added to `finishing-development-branch`
  (before a push/PR option) and `requesting-code-review` (before merging).

## [3.5.0] - 2026-06-25

### Added
- `reformat-md-tables` hook (`PostToolUse(Write|Edit|MultiEdit)`): after a markdown file is written
  or edited, it auto-realigns the file's tables in place (reusing the md-table-formatting skill's
  `reformat_file`), so a table can never ship misaligned. Silent, safe-by-design (bails on malformed
  tables), exits 0 on every failure path.

## [3.4.0] - 2026-06-25

### Added
- `computer-use-vnc` skill: drive a target's screen over plain VNC/RFB with the `vnc-remote-control`
  CLI (type, key, click, screenshot, OCR, click-text) when the target has no network/SSH/agent/API -
  Proxmox/hypervisor VM consoles (incl. first boot before networking), legacy GUI software, and old
  TUI apps. Pure client: nothing on the target except its VNC server (Proxmox ships noVNC). The skill
  installs the tool via uv and drives it; click coordinates are absolute native pixels (no scaling).

## [3.3.0] - 2026-06-25

### Added
- `computer-use-ssh`: an Authentication and host keys section - never ask for / type / accept an SSH
  password (it leaks into transcript, history, logs); log in with a key by PATH (`ssh -i <keypath>`,
  never reading the key or a passphrase), proposing the user set up passwordless key auth if a host
  still wants a password; on the user's OWN/trusted subnet accept new AND changed
  host keys (reimaged hosts), scoped via `~/.ssh/config` to the subnet ranges (`StrictHostKeyChecking=no`
  + `UserKnownHostsFile=/dev/null`), while untrusted hosts use `accept-new`. Includes per-OS walkthroughs
  for setting up key auth (client, incl. Windows OpenSSH via winget/Add-WindowsCapability) and an SSH
  server (Linux/macOS/Windows).

## [3.2.1] - 2026-06-25

### Fixed
- `computer-use-git`: the `repo-gate` hook description now lists all of its checks - the
  using-bitranox-skills index sync and the secrets/private-data scan, alongside tests/pytest/JSON/LF.

## [3.2.0] - 2026-06-25

### Added
- `python-performance-review`, `python-clean-architecture`, `enhance-code-quality`: a third
  robustness rule - never trust structured input. Structured data passed in (dict, JSON, API/IPC
  payload, deserialized object) must have its structure parsed/validated into a typed model before
  use, never assumed correct - unless the user deliberately opts out of the check.

## [3.1.0] - 2026-06-25

### Added
- `python-performance-review`, `python-clean-architecture`, `enhance-code-quality`: two robustness
  rules - (1) keep memory bounded on large/unbounded data (big files, huge DB result sets, huge log
  files must stream/chunk/paginate, not load whole, unless provably bounded), and (2) sanitize and
  bound all external input (lengths/overflow, types, encoding; non-ASCII/emoji/CJK/binary handled
  safely and tested). `enhance-code-quality` gains a Resource Safety rubric dimension.
- `python-performance-review`: `find_unbounded_memory.py` AST detector (with tests) that flags
  whole-file/DB/log reads (`read()`/`readlines()`/`read_text()`, `fetchall()`, un-chunked pandas
  readers), wired into the analysis pipeline as Step 4f.

## [3.0.0] - 2026-06-25

### Changed (BREAKING)
- Renamed skill `python-performance-reviewer` -> `python-performance-review` (the invocation name
  changes; update any references).

### Added
- `python-enforce-data-architecture-strict` skill: an iterative, subagent-driven workflow that
  refactors Python to a strict data architecture - Pydantic models at every external boundary,
  typed models (never raw dicts) internally, Enums/IntEnum for fixed string values, compatibility
  shims removed, and conversions minimized to one parse in / one dump out.

## [2.0.0] - 2026-06-25

### Changed (BREAKING)
- Renamed two skills (the invocation names change, so any references must update):
  `force-using-skills` -> `using-bitranox-skills`, and `plan-writer` -> `writing-plans`
  (matching the upstream superpowers name). All in-repo cross-links, the SessionStart hook,
  and the README were updated.

### Added
- Adopted the remaining four superpowers skills so bitranox fully covers them and the
  superpowers marketplace can be dropped: `dispatching-parallel-agents` (fan out 2+ independent
  tasks), `requesting-code-review` and `receiving-code-review` (the two halves of a review
  cycle, with a `code-reviewer.md` subagent template), and `subagent-driven-development`
  (drive a plan through implementer/reviewer subagents in one session, with `task-brief` /
  `review-package` / `sdd-workspace` helper scripts).
- `session-start.py` hook (SessionStart, matcher `startup|clear|compact`): injects the
  `using-bitranox-skills` skill as session context on startup, `/clear`, and after compaction -
  bitranox's replacement for the superpowers SessionStart bootstrap, so the skills-first
  discipline is active from the first turn without dropping when superpowers is removed.

### Changed
- `using-bitranox-skills` (renamed from `force-using-skills`) enhanced with concepts carried over
  from superpowers `using-superpowers`: a SUBAGENT-STOP guard, an Instruction Priority section
  (user instructions / CLAUDE.md outrank skills outrank the default prompt), a "never read a
  skill's SKILL.md by hand - invoke it" rule, and a brainstorm-before-plan-mode branch.
- `writing-plans` (renamed from `plan-writer`) reconciled with superpowers `writing-plans`, adding
  the Scope Check, File Structure, Task Right-Sizing, Global Constraints, Interfaces block,
  checkbox steps, No Placeholders, and Self-Review sections it was missing.
- Cross-links in the adopted skills now point at their bitranox equivalents
  (superpowers `writing-plans` -> `bitranox:process-plan-writing-plans`, `executing-plans` -> `plan-executor`,
  `using-git-worktrees` -> `git-worktrees`,
  `finishing-a-development-branch` -> `finishing-development-branch`). The SDD workspace dir
  moved from `.superpowers/sdd` to `.bitranox/sdd`. `plan-executor` gained a reciprocal link to
  `subagent-driven-development` as the in-session execution alternative.

## [1.8.0] - 2026-06-25

### Added
- `computer-use-bash`, `computer-use-git`, `computer-use-ssh` skills: consolidate the global
  shell/git/ssh mechanics that were scattered across project notes. Bash: never dismiss a
  non-zero exit as a quirk, isolate a mutation from a trailing check (exit-code masking),
  pipeline `PIPESTATUS`, pgrep/pkill self-match, don't over-wait. Git: `rev-parse --short`
  takes one rev, the `core.fileMode=false` exec-bit trap (`git update-index --chmod=+x`),
  CRLF/LF, no interactive flags. SSH: remote pgrep/pkill self-match, inline-quoting layers,
  backgrounding drops the session, remote PowerShell needs `-File` not inline.
- `git-footgun-guard` hook: a `PreToolUse(Bash)` guard that blocks the always-broken
  `git rev-parse --short <2+ revs>` (it fails `fatal: needed a single commit`) before it
  produces the confusing error, naming the fix.

## [1.7.0] - 2026-06-24

### Added
- `tell-sweep` hook: a `PostToolUse(Write|Edit|MultiEdit)` guard that flags AI-writing
  typographic and invisible tells (em/en-dashes, curly quotes, ellipsis, guillemets, NBSP,
  ZWSP, BOM, bidi controls) just written to a prose file (`*.md`, `*.markdown`, `*.txt`,
  `CLAUDE.md`). Tells inside inline-code spans and fenced code blocks are ignored, so a file
  that documents the tells does not false-positive on its own examples. Code files are
  skipped; allowed symbols (arrow, multiplication, comparison, check, bullet) never trip it.

## [1.6.0] - 2026-06-24

### Added
- `validate-structured-files` hook: a `PostToolUse(Write|Edit|MultiEdit)` guard that re-parses
  the resulting JSON/YAML/XML and blocks the write (with the parse error fed back) when it no
  longer parses. Skips templates, JSONC, multi-doc YAML, empty stubs, and missing libraries;
  parses XML XXE/billion-laughs-safe.
- `repo-gate` hook: a pre-commit / CI gate. As `PreToolUse(Bash)` it blocks a local
  `git commit` / `gh pr create` on a violation (and no-ops outside this repo); as `--ci` it runs
  the same checks for GitHub Actions. Enforces tests-exist, pytest passes, JSON valid, and LF
  endings; version-bump is enforced in the local pre-commit only, never on a contributor PR.
- GitHub Actions workflow (`.github/workflows/ci.yml`): reporting check that runs the gate.
- Tests for every shipped hook (previously only skill scripts had them), enforced by a new
  CLAUDE.md guardrail.

### Changed
- `rotating-proxies`: dropped the `import httpx2 as httpx` alias; the script uses `httpx2`
  throughout.

## [1.5.0] - 2026-06-24

### Added
- `edit-json`, `edit-yml`, `edit-xml` skills: edit structured files through a library
  (round-trip + re-validate) instead of by hand or with `sed`/regex.
- Listed `lxml` in `python-use-modern-libraries`.

## [1.4.0] - 2026-06-24

### Added
- `block-pgrep-self-match` hook: blocks the `pgrep`/`pkill` bracket-trick self-match.

### Changed
- `self-improve`: require a version bump when propagating shared artifacts.
- Documented the semver versioning rule in `CONTRIBUTING.md`.

## [1.3.0] - 2026-06-24

### Added
- Skills audit pass: new skills, performance-reviewer merge, added tests and fixes.
- `rory`: wove the distilled corpus into its references.

## [1.2.2] - 2026-06-23

### Fixed
- `self-improve`: close the git-config gap when shipping a guard script.

## [1.2.1] - 2026-06-23

### Changed
- `skill-writer`: document cross-platform rules for bundled scripts and hooks.

## [1.2.0] - 2026-06-23

### Fixed
- `self-improve` hook: cut Windows false positives and hardened the gate launcher
  (LF endings, UTF-8, Git-Bash-only guard, 64 KiB transcript-tail read).

## [1.1.0] - 2026-06-23

### Added
- Cross-platform hook support, the count-then-enforce escalation ladder, Python helper
  ports, and documentation.

## [1.0.0] - 2026-06-23

### Added
- Initial marketplace release: the bitranox skill collection (invoked as `/bitranox:<skill>`)
  plus the `self-improve` Stop hook, `CONTRIBUTING.md`, and the upstream-propagation workflow.
