# skill-writer checklist - meta-self-improve (2026-11-06, read a skill's declined decisions before queueing)

Step 2 gains a paragraph after the cases-1-and-2 paragraph: before queueing against
`skill:<name>`, run `skill_decisions.py show <name> --skill-dir <plugin>/skills/<name> --kind
rejected,removed --full`; a lesson that re-proposes a listed entry is queued only with a `--why`
that answers its `reopen_if` and names its id, otherwise it is not queued and the step 7 report
says so. It also says which `<name>` and `<plugin>` to use and that empty output means nothing was
declined. Step 3b's contribution paragraph gains, after the `drop --match ... --reason ...`
sentence: a skill-targeted entry dropped as disproven, or declined for a reason that will still
hold, is also recorded as a `rejected` entry in that skill's ledger in the source repo through
`skill_decisions.py add --from-file`, with the fields it carries; a close because it shipped or
duplicates another entry records nothing. Description unchanged.

Decisions: d-20261106-f1d066f6, d-20261106-0231555d

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`); Step 0b `show meta-self-improve
      --all --full` printed one live `rejected` entry (d-20261106-4cb9268c, name-based
      misplacement signal); the new text neither touches nor contradicts it.
- [x] Not mirrored: `repo-gate.py --mirrors` lists 12 pairs, meta-self-improve not among them
      (one DRIFT, `coding-python-layered-config`, unrelated to this change).
- [x] Skill type: technique; test is application - what a capture runs before queueing a skill
      fix, and what it records when it drops a skill-targeted entry for good.
- [x] Inherited-coverage check: `redcheck --corpus-cascade .` reported hits on term overlap; a
      grep of the cascade for `skill_decisions|reopen_if|decisions.jsonl` found only the repo
      CLAUDE.md section on the ledger, which covers reading it before a SKILL.md edit and never
      before queueing or at a drop. The behavioural RED stands, plus a text check: the pre-edit
      SKILL.md (`git show HEAD:`) mentions `skill_decisions`, `decisions.jsonl` and `reopen_if`
      zero times.
- [x] RED, pre-edit text pasted (installed copy byte-identical to HEAD). Scenario A: queue
      "compuse-git should tell agents to rebase instead of merge" under case 1; B: close
      "always prefer anyhow over thiserror in library crates" as wrong for good.
  - opus x2, with the environment fact that `skill_decisions.py` exists: both looked anyway, from
    always-loaded memory rules, not the skill; both quoted NONE for that step and both had to
    guess the arguments ("I would find its arguments rather than invent them"). For B both said
    the skill records nothing beyond the queue reason; adding a ledger entry was "my judgement and
    not the skill's instruction".
  - haiku x1, de-telegraphed (no mention of the ledger): first and only command for A was
    `contrib_queue.py add --target skill:compuse-git ...`; B was `list` then `drop`, "per the
    excerpt, only the queue's drop row with its reason". RED.
- [x] Commands the edit adds were executed: `show compuse-git --skill-dir ... --kind
      rejected,removed --full` printed nothing, rc 0; `show meta-self-improve ...` printed the one
      rejected entry, rc 0; `add --from-file` of a rejected entry with the listed fields into a
      scratch git copy of a skill wrote `d-...`, rc 0. The same entry without `supersedes` and
      `refs` was refused ("supersedes: must be a list of strings"), so the text names all three
      empty lists.
- [x] GREEN (opus x2, haiku x1, edited text pasted; scenario C added as the over-trigger control:
      close an entry that shipped). All three: A1 first command
      `python3 plugins/bitranox/hooks/skill_decisions.py show compuse-git --skill-dir
      plugins/bitranox/skills/compuse-git --kind rejected,removed --full`; A2 (a listed rejected
      entry whose reopen_if the case does not meet) did not queue and wrote the step 7 report line
      naming the id; B wrote a rejected entry with the full field set and ran `add --from-file`
      from the marketplace checkout; C closed with `ship` and recorded no ledger entry, quoting
      "A drop because it already shipped or duplicates another entry records nothing".
- [x] RED-to-GREEN diff, both directions: GREEN kept the RED arms' checks (skills-in-use, split,
      `--match` not `--index`, no memory fact, verify shipped before `ship`); nothing lost.
- [x] Gaps from GREEN, decided:
  - CLOSED: which `<plugin>` `show` reads (opus x2) - now "the marketplace checkout when the
    session has one (it holds entries newer than the installed copy), else the installed plugin".
  - CLOSED: `decision` "the proposal" versus the "Rejected:" form of listed entries (opus x2) -
    now "the proposal prefixed `Rejected:` as `decision`".
  - CLOSED: evidence tier vocabulary not in the excerpt (all three) - the four tiers are listed.
  - CLOSED: "drop the candidate" read against the queue verb `drop` (opus) - now "drop the
    candidate (do not queue it)".
  - CLOSED: "A drop because it already shipped" against `ship` for delivered work (opus x2) - now
    "A close because the entry already shipped or duplicates another entry records nothing".
  - DECLINED, covered elsewhere: whether `ship`/`drop` take the queue argument - SKILL.md:326-327,
    "Run one `ship --match <unique text> --note "<repo> <commit>" <queue>` per entry, the queue
    last as on `add`"; ambiguous `--match` - SKILL.md:327, "`--match` refuses an ambiguous match
    rather than guess".
  - DECLINED, covered elsewhere: where `contrib_queue.py` lives - "home
    `<plugin>/skills/meta-self-improve/`" is the script's directory (`ls` shows it there), the
    plugin-wide script-home convention.
  - DECLINED, owned by the repo: committing, bumping and pushing a ledger write, and doing it in a
    worktree - the marketplace repo's CLAUDE.md governs how a `plugins/` change ships.
  - DECLINED, judgement: write the ledger entry before or after the `drop`; whether to look for
    a different lesson in a dropped candidate's observation; what `reopen_if` to write for a
    rejection expected to hold - `reopen_if` is required and defined in meta-skill-writer Step 0b.
  - DECLINED, pre-existing and outside this change: checking a lesson's truth before queueing
    (RED and GREEN), a target naming a skill that does not exist, CLI versus MCP queueing, which
    queue verb closes a duplicate.
- [x] Re-probe on the final text (haiku, the questions the fixes touched): no checkout -> `show`
      on the installed plugin path, quoting "else the installed plugin"; B JSON with
      `"decision": "Rejected: ..."` and a tier from the list; a duplicate close records no ledger
      entry, quoting "A close because the entry already shipped or duplicates another entry
      records nothing". New gaps were repeats of the declined ones above (script home, schema
      detail in Step 0b, duplicate-close verb); no new undecided gap.
- [x] Width and fence check over the added lines printed nothing; no non-ASCII in added lines;
      the paragraph after each insertion (the routing table; the "ANOTHER repo" paragraph) reads
      unchanged. History finder over the added lines: no hit.
- [x] Ledger: two `rule` entries, tier `user`, origin `authored`, each anchored on its own new
      sentence; `skill_decisions.py check meta-self-improve`: "checked 1 ledger(s), 0
      finding(s)", rc 0.

## Follow-up: the real path of the ledger tool, and the no-checkout drop

Wording fix, no decision changed; both anchored sentences are unchanged and the ledger ids above
stay valid. Step 2 now says `<plugin>` is `plugins/bitranox` inside the marketplace checkout,
else the installed plugin directory, and points at "Resolving `<plugin>`" under step 4. Step 3b
says the `add --from-file` runs from the checkout root, and that without a checkout the
`drop --reason` is the only record: no ledger entry, and the report says so.

- [x] RED, text check of the pre-edit file: step 2 said "`<plugin>` is the marketplace checkout",
      which makes the command `<checkout>/hooks/skill_decisions.py`; `ls hooks/skill_decisions.py`
      at the checkout root: no such file. Step 4 defines `<plugin>` as the plugin directory ("In
      the source repo the same path is `plugins/bitranox`"), so the two disagreed. Step 3b named
      only the checkout route and said nothing for a session without one.
- [x] Command the edit names, executed from the checkout root:
      `python3 plugins/bitranox/hooks/skill_decisions.py show compuse-git --skill-dir
      plugins/bitranox/skills/compuse-git --kind rejected,removed --full` printed nothing, rc 0.
- [x] GREEN (haiku x1, edited text pasted with the step 4 definition). (a) at the checkout root:
      the command above, quoting "`<plugin>` is `plugins/bitranox` inside the marketplace checkout
      when the session has one". (b1) no checkout: `<cache>/bitranox/<version>/hooks/
      skill_decisions.py show compuse-git --skill-dir <cache>/bitranox/<version>/skills/
      compuse-git ...`, derived from the announced base directory per step 4. (b2) no ledger
      entry and no `add`, quoting "Without a checkout, the `drop --reason` is the only record:
      write no ledger entry, and say so in the report (step 7)".
- [x] Gaps from GREEN, decided:
  - DECLINED, covered elsewhere: the queue command (SKILL.md, step 3b, "`contrib_queue.py add
    --what ... --target skill:<name> --why ... "<cwd>"`") and the entry fields (step 3b, the
    "The entry carries `skill` ..." sentence); both were cut from the excerpt.
  - DECLINED, the text ties them: "source repo", "marketplace checkout" and `plugins/bitranox`
    name one place - step 4, "In the source repo the same path is `plugins/bitranox`".
  - DECLINED, ships together: an installed copy without the script - `skill_decisions.py` is
    tracked at `plugins/bitranox/hooks/` (`git ls-files`), so any installed version carrying
    this text carries the script.
  - DECLINED, by design: a no-checkout drop leaves no durable ledger record; that is the case
    this fix states, and the report line is what surfaces it.
  - DECLINED, judgement and outside this fix: how a session finds a checkout, and a checkout
    that is not the session's own.
- [x] Width and fence check over the added lines printed nothing (longest 97 columns); no
      non-ASCII; the paragraphs after both insertions (the routing table; the "ANOTHER repo"
      paragraph) read unchanged. `skill_decisions.py check meta-self-improve`: "checked 1
      ledger(s), 0 finding(s)", rc 0.
