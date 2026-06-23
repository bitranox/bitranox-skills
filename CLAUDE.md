# bitranox-skills

Maintainer notes for this repo. This repo is both a Claude Code plugin marketplace
(`.claude-plugin/marketplace.json`) and the single plugin it ships (`plugins/bitranox/`).

## Do not rewrite history - `master` is force-push protected

Because this repo is a published marketplace, its history must stay **append-only**. Rewriting it
(squash, `git push --force`) breaks `/plugin marketplace update` for everyone who already added the
marketplace: Claude Code keeps a clone at `~/.claude/plugins/marketplaces/bitranox-skills` and the
update is a `git pull` there, which cannot fast-forward a rewritten history - so the update silently
does nothing and existing installs stay on the old version.

Ship changes with normal additive commits and a `version` bump in
`plugins/bitranox/.claude-plugin/plugin.json`.

`master` enforces this with GitHub branch protection: `allow_force_pushes: false`,
`allow_deletions: false`, `enforce_admins: true` (normal additive pushes stay free, no PR or
status-check requirement). Re-apply if it is ever cleared:

```bash
echo '{"required_status_checks":null,"enforce_admins":true,"required_pull_request_reviews":null,"restrictions":null,"allow_force_pushes":false,"allow_deletions":false}' \
  | gh api -X PUT repos/bitranox/bitranox-skills/branches/master/protection --input -
```

If a clone ever diverges (e.g. after an old force-push), recover by re-cloning, not merging:
`git reset --hard origin/master` in the marketplace clone then re-extract the version dir, or have
the user run `/plugin marketplace remove bitranox-skills` then
`/plugin marketplace add bitranox/bitranox-skills`.
