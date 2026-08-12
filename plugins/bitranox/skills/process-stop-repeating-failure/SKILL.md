---
name: process-stop-repeating-failure
description: Use when the action about to run re-attempts a target that already had to be undone (rollback, snapshot restore, revert, git reset, manual repair), when the next attempt differs from the damaging one only by an added flag, option or guard, when a second undo of the same target is on the table, or when a fix is justified by what the documentation says rather than by a test.
---

# Stop Repeating a Failure

## Decide before you run

The last attempt on this target had to be UNDONE. That is the strongest signal in a session that the approach is wrong, and the easiest to walk past, because recovering feels like progress.

First, was it an undo at all? A reset-to-baseline that runs before every attempt is method, not damage, and none of this applies; see Not every recovery counts before you stop anything.

Pick one. There is no fourth option.

- **A. Change the instrument.** A different tool with different semantics, not the same one configured differently.
- **B. Prove the modification on a scratch fixture first**, with a before/after count.
- **C. Stop and report.**

Re-running the failed command with a flag added is not on the list. If the next command is the last command plus an option, this is you. Correcting a different, identified defect each time is ordinary iteration, not this.

## A flag is not a new attempt

An option bolted onto the command that just caused damage is the same attempt wearing a different hat. The flag gets picked because a MECHANISM STORY sounds right, and docs say what a flag governs, never that it governs the phase that hurt you.

Worked example. A mirror-purge walked a `SYMLINKD` (`Users\All Users` to `C:\ProgramData`) out of the target tree and emptied live system state; the guest lost its host keys. Recovered by rollback. The manual says `/XJ` excludes junctions, so the same command plus `/XJ` was run as the fix. `/XJ` governs SOURCE traversal; the purge walks the DESTINATION and follows reparse points regardless. It destroyed the same guest a SECOND time. Three attempts had been spent guessing; a throwaway directory with one junction, one symlink and 5 files settled it in minutes.

## The counters

| What you are about to think           | What is true                                                             |
|---------------------------------------|--------------------------------------------------------------------------|
| "The fix is documented"               | A doc sentence is a story until a fixture runs it.                       |
| "A colleague reviewed it"             | Review propagates the story, it does not execute it.                     |
| "The rollback is there if I am wrong" | The rollback is why you are here. Recovery being available is not a fix. |
| "No time to verify"                   | The fixture costs minutes. The second recovery costs the window.         |
| "We already lost two hours"           | Sunk time argues for the cheap test, never the expensive guess.          |

## The fixture, and the stop

Build the smallest throwaway thing carrying the hazard, run the modified command on it, COUNT the victim before and after. A fixture that cannot lose anything proves nothing. A fixture that fails is an answer, not a setback: that modification is dead, so go to A or C, never to a further tweak.

Two undos of the same target is a hard stop. The target is what you undid, this host or this repo, not the whole fleet. Report what is known and what is untested; a third attempt belongs to someone outside the loop.

## Not every recovery counts

Restoring to a known baseline before each run (`qm rollback <vmid> clean` ahead of every redeploy, a database reloaded between tests, `git stash` inside a red-green loop) is METHOD, not damage undone, and does not trigger any of this.

The test: was state restored because the attempt harmed something it was not aiming at, or because restoring is the first step of every attempt? Planned and unconditional = method, wherever it sits in the loop. Unplanned, to undo harm the attempt did not intend = an undo. A scheduled reset-to-baseline stays method however often it repeats and even when the run before it failed, and the hard stop counts undos only, never method resets.
