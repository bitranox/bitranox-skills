# Re-checking a recorded PR verdict

A handover or `OPEN-WORK.md` line that says a pull request "waits on the maintainer, nothing is
open from our side" is a snapshot taken when it was written. Reviewers, the maintainer and the user
can all post again afterwards, and the record cannot gain what the source gained. The framing makes
it worse, because a line saying "blocked on them" tells the next session that reading the PR is
unnecessary.

The usual signals all miss it. PR state, the check list and `reviewDecision` show neither a later
review's inline finding nor an unresolved review thread. A review that reports no findings can
be followed by a second review that has an open one.

## What to read before acting on the line

Compare everything below against the date of the line's last edit
(`git log -1 --format=%cI -S '<a phrase from the line>' -- OPEN-WORK.md`). Treat anything newer
as unread.

1. **Reviews, with their timestamps:**

   ```bash
   gh api repos/<owner>/<repo>/pulls/<n>/reviews \
     --jq '.[] | "\(.submitted_at) \(.user.login) \(.state)"'
   ```

2. **Review threads and whether each is resolved.** Neither the REST comment list nor PR state
   shows this:

   ```bash
   gh api graphql -f query='
     query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
       reviewThreads(first:100){nodes{isResolved
         comments(last:1){nodes{author{login} createdAt body}}}}}}}' \
     -F o=<owner> -F r=<repo> -F n=<n> \
     --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved|not)'
   ```

3. **Top-level comments, read in full,** including the user's own replies:

   ```bash
   gh pr view <n> --repo <owner>/<repo> --json comments \
     --jq '.comments[-6:][] | "\(.author.login) \(.createdAt)\n\(.body)"'
   ```

## What to do with what you find

- An unresolved thread or a later review finding is open work. Reopen the item or add one, and do
  not repeat the "blocked on the maintainer" line.
- A maintainer request posted after the line is open work too, even when it arrived as a plain
  comment and not as a review.
- **A promise the user made publicly on the PR** ("on it, will do it this weekend") is a dated
  commitment that no session recorded, because it was typed outside one. Add it to
  `OPEN-WORK.md` as a `USER:` item with the date it is due.
