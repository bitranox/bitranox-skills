#!/usr/bin/env bash
# Gated Stop hook for the universal self-improve skill.
#
# Runs after every turn, in every project. It does a CHEAP check: did the
# just-finished turn likely produce a learning (a user correction, an explicit
# "remember", a self-admitted miss)? Only then does it block the stop and nudge
# Claude to run the self-improve skill. On a normal turn it exits silently at
# near-zero cost. Every failure path exits 0, so a broken hook never wedges a turn.
#
# Loop safety: it blocks at most once per user message. It records the processed
# message's hash in a per-project state file and also honors stop_hook_active, so
# the follow-up stop (after Claude runs the skill) is allowed through.

set -uo pipefail

input="$(cat)" || exit 0
command -v jq >/dev/null 2>&1 || exit 0

# Already continuing from a previous block -> let this stop through.
active="$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)"
[ "$active" = "true" ] && exit 0

transcript="$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)"
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

proj="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$proj" ] || proj="${CLAUDE_PROJECT_DIR:-$PWD}"
proj_key="$(printf '%s' "$proj" | cksum | awk '{print $1}')"
state="${TMPDIR:-/tmp}/claude-self-improve-${proj_key}.state"

# Last user + last assistant text from the transcript tail (cheap).
last_user="$(tail -n 400 "$transcript" 2>/dev/null \
  | jq -rc 'select(.type=="user")      | .message.content' 2>/dev/null | tail -n 1)"
last_asst="$(tail -n 400 "$transcript" 2>/dev/null \
  | jq -rc 'select(.type=="assistant") | .message.content' 2>/dev/null | tail -n 1)"
slice="${last_user}
${last_asst}"
[ -n "$(printf '%s' "$slice" | tr -d '[:space:]')" ] || exit 0

# Block at most once per user message.
sig_hash="$(printf '%s' "$last_user" | cksum | awk '{print $1}')"
[ -f "$state" ] && [ "$(cat "$state" 2>/dev/null)" = "$sig_hash" ] && exit 0

# The gate: high-precision learning signals (corrections, "remember", admitted miss).
pat='no,|nope|that.?s wrong|that is wrong|incorrect|don.?t do|do not do|stop doing'
pat="$pat"'|you (forgot|missed|should have|shouldn.?t)|not what i|instead of'
pat="$pat"'|that.?s not right|isn.?t right|you.?re right|you are right|my mistake'
pat="$pat"'|i was wrong|apolog|remember|note that|keep in mind|for next time'
pat="$pat"'|for the future|from now on|make a (memory|rule|note)'
pat="$pat"'|falsch|nein,|stattdessen|merke? dir|in zukunft|denk dran'

if printf '%s' "$slice" | grep -iqE "$pat"; then
  printf '%s' "$sig_hash" > "$state" 2>/dev/null || true
  jq -n '{
    decision: "block",
    reason: "A learning signal was detected this turn (a correction, an explicit \"remember\", or a self-admitted miss). Before you stop: invoke the self-improve skill (Skill tool, name \"self-improve\") to capture this session'\''s learnings into memory/CLAUDE.md per its procedure. If a project-specific extension skill exists (a repo-local *-self-improve), follow its bindings too. If on reflection there is genuinely nothing worth recording, say so in one line and then stop."
  }'
  exit 0
fi

exit 0
