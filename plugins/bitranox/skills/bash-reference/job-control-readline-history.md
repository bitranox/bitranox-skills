# Bash 5.3 Reference: Job Control, Command Line Editing, and History

## 7. Job Control

### 7.1 Job Control Basics

Job control is the ability to selectively stop (suspend) and resume process execution. The shell associates a **job** with each pipeline and maintains a table of currently executing jobs.

**Job identification:**
- When Bash starts an async job, it prints: `[1] 25647` (job number 1, last process PID 25647)
- All processes in a single pipeline are members of the same job
- Job numbers start at 1; when the table empties, numbering restarts at 1

**Process groups and terminals:**
- Each process has a process group ID; the terminal has a current terminal process group ID
- Foreground processes: process group ID equals terminal process group ID; receive keyboard signals (SIGINT, etc.)
- Background processes: immune to keyboard-generated signals
- Only foreground processes may read from the terminal
- Background processes reading from terminal receive SIGTTIN (suspends unless caught)
- If `stty tostop` is set, background writes to terminal receive SIGTTOU

**Suspending and resuming:**
- `^Z` (Control-Z): suspend character -- stops running process immediately, discards pending output and typeahead
- `^Y` (Control-Y): delayed suspend -- stops process when it attempts to read terminal input
- `bg`: continue suspended job in background
- `fg`: continue suspended job in foreground
- `kill`: send signal to job
- To stop a background process not on your terminal, send SIGSTOP via `kill`

**Job specifications (jobspecs):**

| Jobspec | Meaning                                          |
|---------|--------------------------------------------------|
| `%n`    | Job number n                                     |
| `%ce`   | Job whose command name begins with "ce"          |
| `%?ce`  | Job containing "ce" anywhere in its command line |
| `%%`    | Current job                                      |
| `%+`    | Current job (synonym for `%%`)                   |
| `%`     | Current job (bare `%` with no spec)              |
| `%-`    | Previous job                                     |

- **Current job**: becomes current when started in background, stopped in foreground, or resumed in background
- **Previous job**: the job that was current before the current one became current
- In `jobs` output: current job marked with `+`, previous job with `-`
- If only one job exists, both `%+` and `%-` refer to it

**Shortcuts:**
- `%1` alone is equivalent to `fg %1` (bring job 1 to foreground)
- `%1 &` is equivalent to `bg %1` (resume job 1 in background)

**Status notification:**
- Bash normally waits until about to print a prompt before notifying of job status changes
- Notifies after a foreground command in a list completes, before executing the next command
- `set -b`: report status changes immediately
- Bash executes any trap on SIGCHLD for each terminating child process
- When a job terminates, it is removed from the jobs table; `wait` can still report its exit status if given the PID

**Exit behavior:**
- Attempting to exit with stopped jobs (or running jobs if `checkjobs` is enabled) prints a warning
- If `checkjobs` is enabled, lists jobs and their statuses
- A second immediate exit attempt terminates any stopped jobs without warning

**wait and job control:**
- When job control is enabled, `wait` returns when a job changes state
- The `-f` option forces `wait` to wait until the job terminates

### 7.2 Job Control Builtins

#### bg

```
bg [JOBSPEC ...]
```

Resume each suspended job JOBSPEC in the background, as if started with `&`. Without JOBSPEC, uses the current job.

**Return**: 0 unless job control is disabled, JOBSPEC not found, or job was started without job control.

#### fg

```
fg [JOBSPEC]
```

Resume JOBSPEC in the foreground, making it the current job. Without JOBSPEC, resumes the current job.

**Return**: exit status of the foregrounded command, or non-zero if job control is disabled, JOBSPEC is invalid, or job was started without job control.

#### jobs

```
jobs [-lnprs] [JOBSPEC]
jobs -x COMMAND [ARGUMENTS]
```

**Options (first form):**

| Option | Effect                                                      |
|--------|-------------------------------------------------------------|
| `-l`   | List process IDs in addition to normal info                 |
| `-n`   | Show only jobs whose status changed since last notification |
| `-p`   | List only the process group leader's PID                    |
| `-r`   | Show only running jobs                                      |
| `-s`   | Show only stopped jobs                                      |

- With JOBSPEC: restrict output to that job
- Without JOBSPEC: list all jobs

**Second form (`-x`):** Replace any JOBSPEC in COMMAND/ARGUMENTS with the corresponding process group ID, execute COMMAND, return its exit status.

**Return**: 0 unless invalid option or invalid JOBSPEC.

#### kill

```
kill [-s SIGSPEC] [-n SIGNUM] [-SIGSPEC] ID [...]
kill -l|-L [EXIT_STATUS]
```

Send signal to processes named by each ID (jobspec or PID).

- SIGSPEC: case-insensitive signal name (with or without SIG prefix) or signal number
- SIGNUM: signal number
- Default signal: SIGTERM
- `-l`: list signal names; with arguments, list names for those signal numbers/exit statuses
- `-L`: equivalent to `-l`
- `kill` assumes process exit statuses > 128; anything less is a signal number

**Return**: 0 if at least one signal sent successfully.

#### wait

```
wait [-fn] [-p VARNAME] [ID ...]
```

Wait until each child process specified by ID (PID or jobspec) exits.

| Option | Effect                                                                                                      |
|--------|-------------------------------------------------------------------------------------------------------------|
| (none) | Wait for all running background jobs and last process substitution (if PID matches `$!`); return 0          |
| `-n`   | Wait for any one of the IDs (or any job/process substitution if no IDs) to complete; return its exit status |
| `-p`   | Assign the completed job/process identifier to VARNAME (useful with `-n`); variable is unset initially      |
| `-f`   | When job control is enabled, wait for each ID to terminate (not just change state)                          |

**Return**: exit status of last ID; 127 if no IDs specify active children; >128 if interrupted by signal.

**Note**: When job control is not active, `kill` and `wait` do not accept jobspec arguments -- they require PIDs.

#### disown

```
disown [-ar] [-h] [ID ...]
```

- Without options: remove each ID (jobspec or PID) from the active jobs table
- `-h`: mark jobs so the shell does not send SIGHUP on shell exit (does not remove from table)
- `-a`: apply to all jobs (when no ID supplied)
- `-r`: apply to running jobs only (when no ID supplied)
- Without ID and without `-a`/`-r`: applies to the current job

**Return**: 0 unless ID does not specify a valid job.

#### suspend

```
suspend [-f]
```

Suspend this shell until it receives SIGCONT. A login shell or shell without job control cannot be suspended; `-f` forces suspension.

**Return**: 0 unless login shell or job control disabled without `-f`.

### 7.3 Job Control Variables

#### auto_resume

Controls how the shell interacts with job control for simple single-word commands (without redirections):

| Value                           | Behavior                                                          |
|---------------------------------|-------------------------------------------------------------------|
| `exact`                         | Word must match stopped job name exactly                          |
| `substring`                     | Word must match a substring of stopped job name (like `%?string`) |
| Any other value (e.g. `prefix`) | Word must be a prefix of stopped job name (like `%string`)        |

If more than one job matches, the most recently accessed job is selected. The "name" is the command line as displayed by `jobs`.

---

## 8. Command Line Editing

Command line editing is provided by the **Readline** library. Enabled by default for interactive shells (disable with `--noediting`). Also used with `read -e`.

- Default mode: Emacs keybindings
- Toggle modes: `set -o emacs` / `set -o vi`
- Disable: `set +o emacs` / `set +o vi`

### 8.1 Introduction to Line Editing

**Notation:**
- `C-k`: Control-K (hold Control, press k)
- `M-k`: Meta-K (hold Meta/Alt/Option, press k; or press ESC then k)
- `M-C-k`: Meta-Control-k
- Meta key may produce chars with eighth bit set (controlled by `enable-meta-key` variable)
- If no Meta key: press ESC first, then the key (ESC is the "meta prefix")
- `force-meta-prefix` variable controls whether `M-key` bindings use meta prefix behavior

**Special key names:** DEL, ESC, LFD (C-j), SPC, RET (Return/Enter), TAB

### 8.2 Readline Interaction

Press RET at any cursor position to accept the entire line.

#### 8.2.1 Bare Essentials

| Key                | Action                                               |
|--------------------|------------------------------------------------------|
| `C-b`              | Move back one character                              |
| `C-f`              | Move forward one character                           |
| DEL / Backspace    | Delete character to left of cursor                   |
| `C-d`              | Delete character under cursor                        |
| Printing chars     | Insert at cursor                                     |
| `C-_` or `C-x C-u` | Undo last editing command (repeatable to empty line) |

#### 8.2.2 Movement Commands

| Key   | Action                                     |
|-------|--------------------------------------------|
| `C-a` | Move to start of line                      |
| `C-e` | Move to end of line                        |
| `M-f` | Move forward one word (letters and digits) |
| `M-b` | Move backward one word                     |
| `C-l` | Clear screen, reprint current line at top  |

Convention: Control operates on characters, Meta operates on words.

#### 8.2.3 Killing and Yanking

**Killing** = delete and save for later reinsertion. **Yanking** = reinserting killed text. (Cut and paste.)

Consecutive kills accumulate into the kill ring together. The kill ring is not line-specific.

**Kill commands:**

| Key     | Action                                             |
|---------|----------------------------------------------------|
| `C-k`   | Kill from cursor to end of line                    |
| `M-d`   | Kill from cursor to end of current/next word       |
| `M-DEL` | Kill from cursor to start of current/previous word |
| `C-w`   | Kill from cursor to previous whitespace            |

**Yank commands:**

| Key   | Action                                                 |
|-------|--------------------------------------------------------|
| `C-y` | Yank most recently killed text at cursor               |
| `M-y` | Rotate kill-ring, yank new top (only after C-y or M-y) |

#### 8.2.4 Numeric Arguments

Pass numeric arguments to Readline commands as repeat counts or direction modifiers.

- Type meta digits before the command: `M-1 0 C-d` deletes 10 characters
- `M--` starts a negative argument: `M-- C-k` kills backward to start of line
- Negative argument reverses direction of forward-acting commands

#### 8.2.5 Searching for Commands in the History

**Incremental search:**

| Key              | Action                                                    |
|------------------|-----------------------------------------------------------|
| `C-r`            | Search backward incrementally                             |
| `C-s`            | Search forward incrementally                              |
| `C-g`            | Abort search, restore original line                       |
| ESC or `C-j`     | Terminate search (configurable via `isearch-terminators`) |
| RET              | Terminate search and execute found line                   |
| Movement command | Terminate search, make found line current, begin editing  |

- Typing `C-r`/`C-s` again during search finds next match
- Two `C-r`s without intervening characters reuses last search string
- Any key bound to a Readline command terminates the search and executes that command

**Non-incremental search:** Read entire search string before searching. Search string may be typed or taken from current line.

### 8.3 Readline Init File

**Location priority:**
1. `$INPUTRC` environment variable
2. `~/.inputrc`
3. `/etc/inputrc`

The `bind` builtin can also set keybindings and variables. `C-x C-r` re-reads the init file.

#### 8.3.1 Readline Init File Syntax

- Blank lines: ignored
- Lines starting with `#`: comments
- Lines starting with `$`: conditional constructs
- Other lines: variable settings or key bindings

**Variable settings:**

```
set VARIABLE VALUE
```

- Variable names and values are case-insensitive where appropriate
- Unrecognized variable names are ignored
- Boolean variables: set to `on` if value is null/empty, "on" (case-insensitive), or 1; anything else sets to `off`
- `bind -V`: list current variable names and values

#### All Readline Variables

| Variable                           | Default                                | Description                                                                                                                                                                                    |
|------------------------------------|----------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `active-region-start-color`        | Terminal standout mode                 | Terminal escape sequence for active region text color. Reset on terminal type change. Example: `\e[01;33m`                                                                                     |
| `active-region-end-color`          | Terminal standout restore              | Terminal escape sequence to restore normal display after active region. Reset on terminal type change. Example: `\e[0m`                                                                        |
| `bell-style`                       | `audible`                              | Controls terminal bell: `none`, `visible`, or `audible`                                                                                                                                        |
| `bind-tty-special-chars`           | `on`                                   | Bind kernel terminal driver special control chars to Readline equivalents (overrides defaults)                                                                                                 |
| `blink-matching-paren`             | `off`                                  | Briefly move cursor to opening paren when closing paren inserted                                                                                                                               |
| `colored-completion-prefix`        | `off`                                  | Display common completion prefix in different color (from `LS_COLORS`; custom suffix `readline-colored-completion-prefix`)                                                                     |
| `colored-stats`                    | `off`                                  | Display completions with colors by file type (from `LS_COLORS`)                                                                                                                                |
| `comment-begin`                    | `"#"`                                  | String inserted by `insert-comment` command                                                                                                                                                    |
| `completion-display-width`         | `-1`                                   | Screen columns for completion display. 0 = one per line. Ignored if < 0 or > terminal width                                                                                                    |
| `completion-ignore-case`           | `off`                                  | Case-insensitive filename matching and completion                                                                                                                                              |
| `completion-map-case`              | `off`                                  | When `completion-ignore-case` is on, treat `-` and `_` as equivalent                                                                                                                           |
| `completion-prefix-display-length` | 0                                      | Max length of common prefix displayed without modification. Longer prefixes replaced with ellipsis (or `___` for filenames starting with `.`)                                                  |
| `completion-query-items`           | `100`                                  | Threshold for asking user before displaying completions. 0 = never ask. Negative treated as 0                                                                                                  |
| `convert-meta`                     | `on` (but `off` for multibyte locales) | Convert 8th-bit-set chars to ESC-prefixed sequences. Depends on `LC_CTYPE`. Affects key bindings (see `force-meta-prefix`)                                                                     |
| `disable-completion`               | `off`                                  | Inhibit word completion; completion chars act as `self-insert`                                                                                                                                 |
| `echo-control-characters`          | `on`                                   | Echo character corresponding to keyboard-generated signal                                                                                                                                      |
| `editing-mode`                     | `emacs`                                | Default keybinding set: `emacs` or `vi`                                                                                                                                                        |
| `emacs-mode-string`                | `@`                                    | String displayed before prompt in emacs mode when `show-mode-in-prompt` is on. Supports `\1`/`\2` for non-printing sequences                                                                   |
| `enable-active-region`             | `on`                                   | Highlight text between point and mark using `active-region-start-color`. Shows bracketed-paste and search matches                                                                              |
| `enable-bracketed-paste`           | `on`                                   | Terminal inserts paste as single string; prevents executing bindings in pasted text                                                                                                            |
| `enable-keypad`                    | `off`                                  | Enable application keypad (needed for arrow keys on some systems)                                                                                                                              |
| `enable-meta-key`                  | `on`                                   | Enable meta modifier key if terminal supports it                                                                                                                                               |
| `expand-tilde`                     | `off`                                  | Perform tilde expansion during word completion                                                                                                                                                 |
| `force-meta-prefix`                | `off`                                  | When on, `\M-`C bindings always use ESC C (two-char meta prefix). When off, behavior depends on `convert-meta`                                                                                 |
| `history-preserve-point`           | `off`                                  | Place cursor at same position on each retrieved history line                                                                                                                                   |
| `history-size`                     | `$HISTSIZE`                            | Max history entries. 0 = delete all, no new saves. < 0 = unlimited. Non-numeric = 500                                                                                                          |
| `horizontal-scroll-mode`           | `off`                                  | Scroll long lines horizontally instead of wrapping. Auto-set to on for terminals of height 1                                                                                                   |
| `input-meta`                       | `off` (but `on` for multibyte locales) | Enable 8-bit input (don't clear 8th bit). Synonym: `meta-flag`. Depends on `LC_CTYPE`                                                                                                          |
| `isearch-terminators`              | ESC, `C-j`                             | Characters that terminate incremental search without executing as a command                                                                                                                    |
| `keymap`                           | `emacs`                                | Current keymap. Built-in names: `emacs`, `emacs-standard`, `emacs-meta`, `emacs-ctlx`, `vi`, `vi-move`, `vi-command`, `vi-insert`. `vi` = `vi-command` = `vi-move`; `emacs` = `emacs-standard` |
| `keyseq-timeout`                   | `500`                                  | Milliseconds to wait for ambiguous key sequence input. <= 0 or non-numeric = wait for another key press                                                                                        |
| `mark-directories`                 | `on`                                   | Append slash to completed directory names                                                                                                                                                      |
| `mark-modified-lines`              | `off`                                  | Display `*` at start of modified history lines                                                                                                                                                 |
| `mark-symlinked-directories`       | `off`                                  | Append slash to completed symlinks-to-directories (subject to `mark-directories`)                                                                                                              |
| `match-hidden-files`               | `on`                                   | Match dotfiles during filename completion. Off = user must type leading `.`                                                                                                                    |
| `menu-complete-display-prefix`     | `off`                                  | Display common prefix before cycling through menu completions                                                                                                                                  |
| `output-meta`                      | `off` (but `on` for multibyte locales) | Display 8th-bit-set chars directly instead of meta-prefixed. Depends on `LC_CTYPE`                                                                                                             |
| `page-completions`                 | `on`                                   | Use internal pager (like `more`) for completion display                                                                                                                                        |
| `prefer-visible-bell`              | (see `bell-style`)                     | Alias for `bell-style`                                                                                                                                                                         |
| `print-completions-horizontally`   | `off`                                  | Sort completions horizontally rather than vertically down the screen                                                                                                                           |
| `revert-all-at-newline`            | `off`                                  | Undo all changes to history lines before returning on `accept-line`                                                                                                                            |
| `search-ignore-case`               | `off`                                  | Case-insensitive incremental and non-incremental history searches                                                                                                                              |
| `show-all-if-ambiguous`            | `off`                                  | List matches immediately on ambiguous completion instead of ringing bell                                                                                                                       |
| `show-all-if-unmodified`           | `off`                                  | List matches immediately when no partial completion possible (no common prefix)                                                                                                                |
| `show-mode-in-prompt`              | `off`                                  | Add editing mode indicator string before prompt                                                                                                                                                |
| `skip-completed-text`              | `off`                                  | When completing mid-word, skip chars after point that match completion (avoids duplication like "Makefilefile")                                                                                |
| `vi-cmd-mode-string`               | `(cmd)`                                | String displayed before prompt in vi command mode when `show-mode-in-prompt` is on. Supports `\1`/`\2`                                                                                         |
| `vi-ins-mode-string`               | `(ins)`                                | String displayed before prompt in vi insertion mode when `show-mode-in-prompt` is on. Supports `\1`/`\2`                                                                                       |
| `visible-stats`                    | `off`                                  | Append file type character when listing completions                                                                                                                                            |

#### Key Bindings Syntax

**Form 1 -- Key name:**

```
KEYNAME: FUNCTION-NAME or MACRO
```

Example:
```
Control-u: universal-argument
Meta-Rubout: backward-kill-word
Control-o: "> output"
```

Recognized symbolic names: DEL, ESC, ESCAPE, LFD, NEWLINE, RET, RETURN, RUBOUT, SPACE, SPC, TAB.

**Form 2 -- Key sequence:**

```
"KEYSEQ": FUNCTION-NAME or MACRO
```

Example:
```
"\C-u": universal-argument
"\C-x\C-r": re-read-init-file
"\e[11~": "Function Key 1"
```

**Escape sequences (GNU Emacs style):**

| Sequence | Meaning                                                                  |
|----------|--------------------------------------------------------------------------|
| `\C-`    | Control prefix                                                           |
| `\M-`    | Meta prefix (behavior depends on `force-meta-prefix` and `convert-meta`) |
| `\e`     | Escape character                                                         |
| `\\`     | Backslash                                                                |
| `\"`     | Double quote                                                             |
| `\'`     | Single quote                                                             |

**Additional backslash escapes:**

| Sequence | Meaning                            |
|----------|------------------------------------|
| `\a`     | Alert (bell)                       |
| `\b`     | Backspace                          |
| `\d`     | Delete                             |
| `\f`     | Form feed                          |
| `\n`     | Newline                            |
| `\r`     | Carriage return                    |
| `\t`     | Horizontal tab                     |
| `\v`     | Vertical tab                       |
| `\NNN`   | Octal value (1-3 digits)           |
| `\xHH`   | Hexadecimal value (1-2 hex digits) |

**Macros:** Enclose in single or double quotes. Unquoted text = function name. Backslash escapes are expanded in macro body. Backslash quotes any other character including `"` and `'`.

No space between key name and colon (space would be interpreted as part of key name).

#### 8.3.2 Conditional Init Constructs

Four parser directives:

**`$if`** -- Test editing mode, terminal, application, version, or variable:

```
$if mode=emacs
    ...bindings for emacs mode...
$endif

$if term=xterm
    ...terminal-specific bindings...
$endif

$if version >= 7.0
    set show-mode-in-prompt on
$endif

$if Bash
    ...Bash-specific bindings...
$endif

$if editing-mode == emacs
    set show-mode-in-prompt on
$endif
```

- **mode**: test `emacs` or `vi`
- **term**: test against full terminal name or portion before first `-` (e.g., `xterm` matches `xterm-256color`)
- **version**: comparison operators `=`, `==`, `!=`, `<=`, `>=`, `<`, `>`. Version format: `MAJOR.MINOR` (minor defaults to 0)
- **application**: test application name (e.g., `Bash`, `Ftp`)
- **variable**: equality tests (`=`, `==`, `!=`) on Readline variables. Boolean vars tested against `on`/`off`

**`$else`** -- Executed if `$if` test fails.

**`$endif`** -- Terminates `$if`.

**`$include`** -- Read commands/bindings from another file:

```
$include /etc/inputrc
```

### 8.4 Bindable Readline Commands

List bindings: `bind -P` (verbose) or `bind -p` (terse, suitable for inputrc).

**Terminology:**
- "point" = current cursor position
- "mark" = saved cursor position (set by `set-mark`)
- "region" = text between point and mark
- Active region: highlighted using `active-region-start-color`

#### 8.4.1 Commands For Moving

| Command                | Default Key | Description                                                                               |
|------------------------|-------------|-------------------------------------------------------------------------------------------|
| `beginning-of-line`    | `C-a`       | Move to start of line (also Home key)                                                     |
| `end-of-line`          | `C-e`       | Move to end of line (also End key)                                                        |
| `forward-char`         | `C-f`       | Move forward one character (also right arrow)                                             |
| `backward-char`        | `C-b`       | Move back one character (also left arrow)                                                 |
| `forward-word`         | `M-f`       | Move forward to end of next word (letters/digits)                                         |
| `backward-word`        | `M-b`       | Move back to start of current/previous word (letters/digits)                              |
| `shell-forward-word`   | `M-C-f`     | Move forward to end of next word (delimited by non-quoted shell metacharacters)           |
| `shell-backward-word`  | `M-C-b`     | Move back to start of current/previous word (shell metachar boundaries)                   |
| `previous-screen-line` | (unbound)   | Move to same screen column on previous physical screen line                               |
| `next-screen-line`     | (unbound)   | Move to same screen column on next physical screen line                                   |
| `clear-display`        | `M-C-l`     | Clear screen and scrollback buffer, redraw current line at top                            |
| `clear-screen`         | `C-l`       | Clear screen, redraw current line at top. With numeric arg: refresh line without clearing |
| `redraw-current-line`  | (unbound)   | Refresh current line                                                                      |

#### 8.4.2 Commands For Manipulating The History

| Command                                  | Default Key      | Description                                                                                                                                                                  |
|------------------------------------------|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `accept-line`                            | Newline / Return | Accept line, add to history per HISTCONTROL/HISTIGNORE. Modified history lines restored to original                                                                          |
| `previous-history`                       | `C-p`            | Fetch previous history entry (also up arrow)                                                                                                                                 |
| `next-history`                           | `C-n`            | Fetch next history entry (also down arrow)                                                                                                                                   |
| `beginning-of-history`                   | `M-<`            | Move to first line in history                                                                                                                                                |
| `end-of-history`                         | `M->`            | Move to end of input history (current line being entered)                                                                                                                    |
| `reverse-search-history`                 | `C-r`            | Incremental backward search. Sets region to matched text (active)                                                                                                            |
| `forward-search-history`                 | `C-s`            | Incremental forward search. Sets region to matched text (active)                                                                                                             |
| `non-incremental-reverse-search-history` | `M-p`            | Non-incremental backward search; string may match anywhere in line                                                                                                           |
| `non-incremental-forward-search-history` | `M-n`            | Non-incremental forward search; string may match anywhere in line                                                                                                            |
| `history-search-backward`                | (unbound)        | Search backward; string from start-of-line to point must match at beginning of history line (may bind to Page Down)                                                          |
| `history-search-forward`                 | (unbound)        | Search forward; string must match at beginning of history line (may bind to Page Up)                                                                                         |
| `history-substring-search-backward`      | (unbound)        | Search backward; string may match anywhere in history line                                                                                                                   |
| `history-substring-search-forward`       | (unbound)        | Search forward; string may match anywhere in history line                                                                                                                    |
| `yank-nth-arg`                           | `M-C-y`          | Insert first arg of previous command (word 1). With arg N: insert Nth word (0-based). Negative N: from end. Uses `!N` expansion                                              |
| `yank-last-arg`                          | `M-.` or `M-_`   | Insert last arg of previous command. With numeric arg: like `yank-nth-arg`. Successive calls move back through history. Negative arg reverses direction. Uses `!$` expansion |
| `operate-and-get-next`                   | `C-o`            | Accept line and fetch next history line for editing. Numeric arg specifies history entry                                                                                     |
| `fetch-history`                          | (unbound)        | With numeric arg: fetch that history entry. Without: move to first entry                                                                                                     |

#### 8.4.3 Commands For Changing Text

| Command                        | Default Key                       | Description                                                                                                                                               |
|--------------------------------|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `end-of-file`                  | usually `C-d`                     | EOF indicator. If read with no chars on line and point at beginning, returns EOF                                                                          |
| `delete-char`                  | `C-d`                             | Delete character at point (also Delete key). See `end-of-file` for empty-line behavior                                                                    |
| `backward-delete-char`         | Rubout                            | Delete character behind cursor. With numeric arg: kill (save to kill ring) instead of delete                                                              |
| `forward-backward-delete-char` | (unbound)                         | Delete char under cursor; at end of line, delete char behind cursor                                                                                       |
| `quoted-insert`                | `C-q` or `C-v`                    | Insert next character verbatim                                                                                                                            |
| `self-insert`                  | `a, b, A, 1, !, ...`              | Insert the typed character                                                                                                                                |
| `bracketed-paste-begin`        | (bound to bracketed paste escape) | Insert pasted text as unit via `self-insert`; sets active region to inserted text                                                                         |
| `transpose-chars`              | `C-t`                             | Drag char before cursor over char at cursor. At end of line: transpose last two chars. Negative args have no effect                                       |
| `transpose-words`              | `M-t`                             | Drag word before point past word after point. At end of line: transpose last two words                                                                    |
| `shell-transpose-words`        | `M-C-t`                           | Like `transpose-words` but uses shell metacharacter word boundaries                                                                                       |
| `upcase-word`                  | `M-u`                             | Uppercase current/following word. Negative arg: previous word without moving cursor                                                                       |
| `downcase-word`                | `M-l`                             | Lowercase current/following word. Negative arg: previous word without moving cursor                                                                       |
| `capitalize-word`              | `M-c`                             | Capitalize current/following word. Negative arg: previous word without moving cursor                                                                      |
| `overwrite-mode`               | (unbound, may bind to Insert key) | Toggle overwrite mode. Emacs mode only. Positive arg: overwrite. Non-positive: insert. `self-insert` replaces; `backward-delete-char` replaces with space |

#### 8.4.4 Killing And Yanking

| Command                    | Default Key  | Description                                                                       |
|----------------------------|--------------|-----------------------------------------------------------------------------------|
| `kill-line`                | `C-k`        | Kill from point to end of line. Negative arg: kill backward to beginning          |
| `backward-kill-line`       | `C-x Rubout` | Kill backward from cursor to beginning of line. Negative arg: kill forward to end |
| `unix-line-discard`        | `C-u`        | Kill backward from cursor to beginning of line                                    |
| `kill-whole-line`          | (unbound)    | Kill all characters on current line regardless of point position                  |
| `kill-word`                | `M-d`        | Kill from point to end of current/next word (same boundaries as `forward-word`)   |
| `backward-kill-word`       | `M-DEL`      | Kill word behind point (same boundaries as `backward-word`)                       |
| `shell-kill-word`          | `M-C-d`      | Kill from point to end of current/next word (shell metachar boundaries)           |
| `shell-backward-kill-word` | (unbound)    | Kill word behind point (shell metachar boundaries)                                |
| `unix-word-rubout`         | `C-w`        | Kill word behind point using whitespace boundary; save to kill ring               |
| `unix-filename-rubout`     | (unbound)    | Kill word behind point using whitespace and `/` boundaries; save to kill ring     |
| `delete-horizontal-space`  | (unbound)    | Delete all spaces and tabs around point                                           |
| `kill-region`              | (unbound)    | Kill text in current region                                                       |
| `copy-region-as-kill`      | (unbound)    | Copy region text to kill buffer (no delete)                                       |
| `copy-backward-word`       | (unbound)    | Copy word before point to kill buffer (same boundaries as `backward-word`)        |
| `copy-forward-word`        | (unbound)    | Copy word after point to kill buffer (same boundaries as `forward-word`)          |
| `yank`                     | `C-y`        | Yank top of kill ring at point                                                    |
| `yank-pop`                 | `M-y`        | Rotate kill-ring, yank new top (only after `yank` or `yank-pop`)                  |

#### 8.4.5 Specifying Numeric Arguments

| Command              | Default Key                | Description                                                                                                                                                                                                  |
|----------------------|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `digit-argument`     | `M-0` through `M-9`, `M--` | Add digit to accumulating argument or start new one. `M--` starts negative                                                                                                                                   |
| `universal-argument` | (unbound)                  | Specify argument. Followed by digits (optional leading minus): those digits define arg. Followed by non-digit/non-minus: multiply argument count by 4. Initial count is 1; first call = 4, second = 16, etc. |

#### 8.4.6 Letting Readline Type For You (Completion)

| Command                         | Default Key | Description                                                                                                                                                                                 |
|---------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `complete`                      | TAB         | Attempt completion. Bash order: programmable completions, then variable (`$`), username (`~`), hostname (`@`), command (aliases/functions/builtins), then filename                          |
| `possible-completions`          | `M-?`       | List possible completions. Column width: `completion-display-width`, then `$COLUMNS`, then screen width                                                                                     |
| `insert-completions`            | `M-*`       | Insert all completions separated by spaces                                                                                                                                                  |
| `menu-complete`                 | (unbound)   | Replace word with single match; repeat to cycle through matches. Bell at end of list, restores original. Arg N moves N positions forward; negative moves backward. Intended for TAB binding |
| `menu-complete-backward`        | (unbound)   | Like `menu-complete` but cycles backward                                                                                                                                                    |
| `export-completions`            | (unbound)   | Write completions to output: count N, word, S:E offsets, then each match one per line. 0 matches = just "0" and S:E. 1 match = single line. Multiple = common prefix line then matches      |
| `delete-char-or-list`           | (unbound)   | Delete char at point (not at beginning/end). At end of line: `possible-completions`                                                                                                         |
| `complete-filename`             | `M-/`       | Filename completion                                                                                                                                                                         |
| `possible-filename-completions` | `C-x /`     | List possible filename completions                                                                                                                                                          |
| `complete-username`             | `M-~`       | Username completion                                                                                                                                                                         |
| `possible-username-completions` | `C-x ~`     | List possible username completions                                                                                                                                                          |
| `complete-variable`             | `M-$`       | Shell variable completion                                                                                                                                                                   |
| `possible-variable-completions` | `C-x $`     | List possible variable completions                                                                                                                                                          |
| `complete-hostname`             | `M-@`       | Hostname completion                                                                                                                                                                         |
| `possible-hostname-completions` | `C-x @`     | List possible hostname completions                                                                                                                                                          |
| `complete-command`              | `M-!`       | Command name completion (aliases, reserved words, functions, builtins, executables)                                                                                                         |
| `possible-command-completions`  | `C-x !`     | List possible command completions                                                                                                                                                           |
| `dynamic-complete-history`      | `M-TAB`     | Complete against history list entries                                                                                                                                                       |
| `dabbrev-expand`                | (unbound)   | Menu completion against history list lines                                                                                                                                                  |
| `complete-into-braces`          | `M-{`       | Filename completion, insert list in braces for brace expansion                                                                                                                              |

#### 8.4.7 Keyboard Macros

| Command                | Default Key | Description                        |
|------------------------|-------------|------------------------------------|
| `start-kbd-macro`      | `C-x (`     | Begin recording keyboard macro     |
| `end-kbd-macro`        | `C-x )`     | Stop recording and save macro      |
| `call-last-kbd-macro`  | `C-x e`     | Re-execute last defined macro      |
| `print-last-kbd-macro` | (unbound)   | Print last macro in inputrc format |

#### 8.4.8 Miscellaneous Commands

| Command                         | Default Key                         | Description                                                                                                                                                                                              |
|---------------------------------|-------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `re-read-init-file`             | `C-x C-r`                           | Re-read inputrc file                                                                                                                                                                                     |
| `abort`                         | `C-g`                               | Abort current editing command, ring bell                                                                                                                                                                 |
| `do-lowercase-version`          | `M-A, M-B, M-X, ...`                | Run command bound to metafied lowercase equivalent                                                                                                                                                       |
| `prefix-meta`                   | ESC                                 | Metafy next character typed. `ESC f` = `M-f`                                                                                                                                                             |
| `undo`                          | `C-_` or `C-x C-u`                  | Incremental undo, separately remembered per line                                                                                                                                                         |
| `revert-line`                   | `M-r`                               | Undo all changes to current line (back to initial state)                                                                                                                                                 |
| `tilde-expand`                  | `M-&`                               | Perform tilde expansion on current word                                                                                                                                                                  |
| `set-mark`                      | `C-@`                               | Set mark to point. With numeric arg: set mark to that position                                                                                                                                           |
| `exchange-point-and-mark`       | `C-x C-x`                           | Swap point with mark                                                                                                                                                                                     |
| `character-search`              | `C-]`                               | Read a character, move to its next occurrence. Negative arg: search previous                                                                                                                             |
| `character-search-backward`     | `M-C-]`                             | Read a character, move to its previous occurrence. Negative arg: search subsequent                                                                                                                       |
| `skip-csi-sequence`             | (unbound, usually bound to `ESC [`) | Consume multi-key CSI sequence (e.g., Home, End keys)                                                                                                                                                    |
| `insert-comment`                | `M-#`                               | Insert `comment-begin` value at line start, accept line. With numeric arg: toggle (remove if present). When comment removed, line is executed                                                            |
| `dump-functions`                | (unbound)                           | Print all functions and bindings. With numeric arg: inputrc-compatible format                                                                                                                            |
| `dump-variables`                | (unbound)                           | Print all settable variables and values. With numeric arg: inputrc format                                                                                                                                |
| `dump-macros`                   | (unbound)                           | Print all macro bindings. With numeric arg: inputrc format                                                                                                                                               |
| `execute-named-command`         | `M-x`                               | Read command name from input, execute it. Passes numeric arg if supplied                                                                                                                                 |
| `spell-correct-word`            | `C-x s`                             | Spelling correction on current word as directory/filename (like `cdspell`). Shell metachar word boundaries                                                                                               |
| `glob-complete-word`            | `M-g`                               | Treat word before point as glob pattern (implicit `*` appended), generate completion matches                                                                                                             |
| `glob-expand-word`              | `C-x *`                             | Treat word as glob pattern, insert matching filenames. Numeric arg: append `*` first                                                                                                                     |
| `glob-list-expansions`          | `C-x g`                             | Display glob expansions. Numeric arg: append `*` first                                                                                                                                                   |
| `shell-expand-line`             | `M-C-e`                             | Expand line: alias, history, `$'...'`/`$"..."`, tilde, parameter/variable, arithmetic, command/process substitution, word splitting, quote removal. Explicit arg suppresses command/process substitution |
| `history-expand-line`           | `M-^`                               | Perform history expansion on current line                                                                                                                                                                |
| `magic-space`                   | (unbound)                           | Perform history expansion on current line and insert a space                                                                                                                                             |
| `alias-expand-line`             | (unbound)                           | Perform alias expansion on current line                                                                                                                                                                  |
| `history-and-alias-expand-line` | (unbound)                           | Perform history and alias expansion on current line                                                                                                                                                      |
| `insert-last-argument`          | `M-.` or `M-_`                      | Synonym for `yank-last-arg`                                                                                                                                                                              |
| `edit-and-execute-command`      | `C-x C-e`                           | Open current line in editor (`$VISUAL`, `$EDITOR`, or `emacs`), execute result                                                                                                                           |
| `display-shell-version`         | `C-x C-v`                           | Display Bash version information                                                                                                                                                                         |

### 8.5 Readline vi Mode

- Readline vi mode behaves as specified in the POSIX `sh` description
- Switch modes: `set -o vi` / `set -o emacs`
- Default is emacs mode
- When entering a line in vi mode, you start in **insertion** mode (as if `i` was typed)
- Press ESC to switch to **command** mode
- In command mode: standard vi movement keys, `k`/`j` for history navigation, etc.

### 8.6 Programmable Completion

When word completion is attempted for a command with a defined **compspec** (completion specification via `complete`), Readline invokes programmable completion.

**Compspec resolution order:**
1. Identify command name
2. Look for compspec for that command
3. If empty command line: use compspec defined with `complete -E`
4. If first word on line (or after `;`/`|`): use compspec from `complete -I`
5. If command is full pathname: search for compspec for full path, then for portion after final `/`
6. If no compspec found: use default compspec from `complete -D`
7. As final resort: perform alias expansion, look for compspec on expanded command
8. If still no compspec: fall back to default Bash completion

**Compspec evaluation order:**
1. **Actions** specified by compspec -- returns only matches that are prefixes of word being completed. With `-f`/`-d`, uses `FIGNORE` to filter
2. **`-G GLOBPAT`** -- pathname expansion pattern; generated words need not match the word being completed. Uses `FIGNORE` (not `GLOBIGNORE`) to filter
3. **`-W WORDLIST`** -- split by IFS (honors quoting), each word expanded (brace, tilde, parameter, command substitution, arithmetic), results split, prefix-matched against word
4. **`-F FUNCTION`** -- invoked first among function/command options. Sets `COMP_LINE`, `COMP_POINT`, `COMP_KEY`, `COMP_TYPE`, `COMP_WORDS`, `COMP_CWORD`. Args: `$1` = command name, `$2` = word being completed, `$3` = preceding word. Must set `COMPREPLY` array. No filtering against word -- function has complete freedom
5. **`-C COMMAND`** -- run in subshell; print completions one per line. Backslash escapes newline. Args same as `-F`. Added to possible completions set
6. **`-X FILTERPAT`** -- filter pattern applied to all generated completions. `&` in pattern = word being completed. Matching completions removed. Leading `!` negates (removes non-matching). Respects `nocasematch` shopt
7. **`-P PREFIX` / `-S SUFFIX`** -- prepended/appended to each completion

**Fallback behavior:**
- `-o dirnames`: attempt directory completion if no matches generated
- `-o plusdirs`: add directory completion matches to results
- `-o bashdefault`: attempt default Bash completions if no matches
- `-o default`: attempt Readline default filename completion if still no matches

**Dynamic completion:**
- Shell function returning exit status 124 triggers retry from beginning
- Function can change compspec for the command before returning 124
- Useful with `complete -D` for lazy-loading completions:

```bash
_completion_loader()
{
    . "/etc/bash_completion.d/$1.sh" >/dev/null 2>&1 && return 124
}
complete -D -F _completion_loader -o bashdefault -o default
```

**Directory completion and symlinks:**
When compspec indicates directory name completion, programmable completion forces Readline to append `/` to completed symlinks-to-directories, subject to `mark-directories`, regardless of `mark-symlinked-directories`.

### 8.7 Programmable Completion Builtins

#### compgen

```
compgen [-V VARNAME] [OPTION] [WORD]
```

Generate completion matches for WORD according to OPTIONs (same as `complete` except `-p`, `-r`, `-D`, `-E`, `-I`). Write matches to stdout.

- `-V VARNAME`: store completions in indexed array variable VARNAME instead of stdout
- With `-F`/`-C`: shell completion variables are available but won't have useful values
- If WORD specified: only matching completions displayed/stored

**Return**: true unless invalid option or no matches.

#### complete

```
complete [-abcdefgjksuv] [-o COMP-OPTION] [-DEI] [-A ACTION]
         [-G GLOBPAT] [-W WORDLIST] [-F FUNCTION] [-C COMMAND]
         [-X FILTERPAT] [-P PREFIX] [-S SUFFIX] NAME [NAME ...]
complete -pr [-DEI] [NAME ...]
```

**Management options:**
- `-p`: print existing compspecs in reusable format (default if no options/names)
- `-r`: remove compspec for each NAME (or all if no NAMEs)

**Scope options:**
- `-D`: apply to default command completion (no prior compspec defined)
- `-E`: apply to empty command line completion
- `-I`: apply to initial non-assignment word (usually command name completion)
- Precedence: `-D` > `-E` > `-I`. When any of these supplied, NAME arguments are ignored

**Completion options (`-o COMP-OPTION`):**

| Option        | Effect                                                                                                           |
|---------------|------------------------------------------------------------------------------------------------------------------|
| `bashdefault` | Fall back to default Bash completions if no matches                                                              |
| `default`     | Fall back to Readline default filename completion if no matches                                                  |
| `dirnames`    | Fall back to directory name completion if no matches                                                             |
| `filenames`   | Treat completions as filenames (add slash to dirs, quote special chars, suppress trailing spaces). Use with `-F` |
| `fullquote`   | Quote all completed words even if not filenames                                                                  |
| `noquote`     | Don't quote completed filenames (quoting is default)                                                             |
| `nosort`      | Don't sort completions alphabetically                                                                            |
| `nospace`     | Don't append space after completion at end of line                                                               |
| `plusdirs`    | Add directory name completion matches to other results                                                           |

**Action options (`-A ACTION`):**

| Action      | Short | Generates                         |
|-------------|-------|-----------------------------------|
| `alias`     | `-a`  | Alias names                       |
| `arrayvar`  |       | Array variable names              |
| `binding`   |       | Readline key binding names        |
| `builtin`   | `-b`  | Shell builtin names               |
| `command`   | `-c`  | Command names                     |
| `directory` | `-d`  | Directory names                   |
| `disabled`  |       | Disabled shell builtins           |
| `enabled`   |       | Enabled shell builtins            |
| `export`    | `-e`  | Exported variable names           |
| `file`      | `-f`  | File and directory names          |
| `function`  |       | Shell function names              |
| `group`     | `-g`  | Group names                       |
| `helptopic` |       | Help topics (accepted by `help`)  |
| `hostname`  |       | Hostnames (from `$HOSTFILE`)      |
| `job`       | `-j`  | Job names (if job control active) |
| `keyword`   | `-k`  | Shell reserved words              |
| `running`   |       | Running job names                 |
| `service`   | `-s`  | Service names                     |
| `setopt`    |       | Valid `set -o` option arguments   |
| `shopt`     |       | Shell option names for `shopt`    |
| `signal`    |       | Signal names                      |
| `stopped`   |       | Stopped job names                 |
| `user`      | `-u`  | User names                        |
| `variable`  | `-v`  | All shell variable names          |

**Other options:**

| Option         | Description                                                                                                 |
|----------------|-------------------------------------------------------------------------------------------------------------|
| `-C COMMAND`   | Execute COMMAND in subshell; output = completions. Args: $1=command, $2=word, $3=preceding word             |
| `-F FUNCTION`  | Execute FUNCTION in current shell. Must set `COMPREPLY` array. Args: $1=command, $2=word, $3=preceding word |
| `-G GLOBPAT`   | Pathname expansion pattern to generate completions                                                          |
| `-P PREFIX`    | Prepend to each completion after all other processing                                                       |
| `-S SUFFIX`    | Append to each completion after all other processing                                                        |
| `-W WORDLIST`  | Split by IFS (honors quoting), expand each word, prefix-match against word being completed                  |
| `-X FILTERPAT` | Pattern filter: matching completions removed. Leading `!` negates. `&` = word being completed               |

#### compopt

```
compopt [-o OPTION] [-DEI] [+o OPTION] [NAME]
```

Modify completion options for each NAME, or for the currently-executing completion if no NAMEs.

- Without OPTIONs: display current options for NAME or current completion
- `-o OPTION`: enable option
- `+o OPTION`: disable option
- `-D`/`-E`/`-I`: same scope as `complete`. Precedence: `-D` > `-E` > `-I`
- OPTION values: same as `complete -o`

**Return**: true unless invalid option or no compspec exists for NAME.

---

## 9. Using History Interactively

### 9.1 Bash History Facilities

**How history works:**
- Enabled with `set -o history`
- Saves last `$HISTSIZE` commands (default 500)
- Commands stored prior to parameter/variable expansion but after history expansion
- Subject to `HISTIGNORE` and `HISTCONTROL` filtering

**History file:**
- At startup: read from `$HISTFILE` (default `~/.bash_history`)
- Truncated to `$HISTFILESIZE` entries (unset/null/non-numeric/negative = no truncation)
- Lines beginning with history comment char + digit = timestamps for following entry
- Timestamps displayed if `HISTTIMEFORMAT` is set; they delimit multi-line entries

**On exit:**
- Copy last `$HISTSIZE` entries to `$HISTFILE`
- If `histappend` shopt is set: append; otherwise: overwrite
- If `HISTFILE` unset/null or file unwritable: history not saved
- After saving: truncate to `$HISTFILESIZE` lines

**Timestamp persistence:**
- If `HISTTIMEFORMAT` set: timestamps written to file (marked with history comment char)
- Preserved across shell sessions

**History control:**
- `HISTCONTROL` and `HISTIGNORE`: filter which commands are saved
- `cmdhist` shopt: save multi-line command in same history entry (add semicolons)
- `lithist` shopt: save with embedded newlines instead of semicolons

### 9.2 Bash History Builtins

#### fc

```
fc [-e ENAME] [-lnr] [FIRST] [LAST]
fc -s [PAT=REP] [COMMAND]
```

**First form:** Select range FIRST to LAST from history; display or edit and re-execute.

- FIRST/LAST: string (most recent command beginning with it) or number (history index; negative = offset from current)
- When listing: FIRST/LAST of 0 = -1; -0 = current command. Otherwise 0 = -1, -0 is invalid
- Without LAST: set to current command (listing) or FIRST (editing)
- Without FIRST: set to previous command (editing) or -16 (listing)

| Option     | Effect                                |
|------------|---------------------------------------|
| `-l`       | List commands on stdout               |
| `-n`       | Suppress command numbers when listing |
| `-r`       | Reverse listing order                 |
| `-e ENAME` | Use ENAME as editor                   |

Without `-l`: invoke editor on file containing commands. Editor selection: `${FCEDIT:-${EDITOR:-vi}}`. After editing, read and execute edited commands.

**Second form (`-s`):** Re-execute COMMAND after replacing each instance of PAT with REP. COMMAND interpreted like FIRST.

**Useful alias:** `r='fc -s'` -- `r cc` runs last command starting with "cc"; `r` re-executes last command.

**Return:** 0 unless invalid option or FIRST/LAST out of range. For re-execution: exit status of last executed command. For second form: exit status of re-executed command.

#### history

```
history [N]
history -c
history -d OFFSET
history -d START-END
history [-anrw] [FILENAME]
history -ps ARG
```

Without options: display history with numbers. `*` prefix = modified entry. Argument N: show last N entries.

If `HISTTIMEFORMAT` set and non-null: used as `strftime(3)` format string for timestamps (no intervening space).

| Option         | Effect                                                                                                          |
|----------------|-----------------------------------------------------------------------------------------------------------------|
| `-c`           | Clear history list. May combine with other options to replace                                                   |
| `-d OFFSET`    | Delete entry at OFFSET. Positive = as displayed. Negative = relative to end (-1 = current `history -d` command) |
| `-d START-END` | Delete range START to END inclusive. Positive/negative interpreted as above                                     |
| `-a`           | Append new history lines (since session start, not yet appended) to history file                                |
| `-n`           | Read lines not already read from history file; add to current list                                              |
| `-r`           | Read history file, append contents to history list                                                              |
| `-w`           | Write current history list to history file (overwrite)                                                          |
| `-p`           | Perform history substitution on ARGs; display result without storing in history                                 |
| `-s`           | Add ARGs to history list as single entry. Removes last command first                                            |

- With `-w`/`-r`/`-a`/`-n` and FILENAME: use FILENAME as history file
- Without FILENAME: use `$HISTFILE`; if unset/null, options have no effect
- If `HISTTIMEFORMAT` set: timestamps written/read using history comment character

**Return:** 0 unless invalid option, read/write error, invalid OFFSET/range for `-d`, or `-p` expansion fails.

### 9.3 History Expansion

History expansion introduces words from the history list into input. Enabled by default for interactive shells.

- Disable: `set +H`
- Enable for non-interactive: `set -H`
- Performed immediately after complete line read, before word splitting, on each line individually

**Structure:** event designator + optional word designator + optional modifiers.

**History expansion character:** `!` (default, configurable via `histchars`).

**Quoting rules:**
- Backslash removes special handling for next character
- Single quotes enclose verbatim text (inhibit history expansion)
- Within double quotes: backslash can escape `!`, but single quotes cannot (not treated specially inside double quotes)
- In the shell: only `\` and `'` escape `!`; also treated as quoted if immediately before closing `"` in double-quoted string

**Characters that inhibit expansion after `!`:** space, tab, newline, carriage return, `=`, and shell metacharacters.

**Quick substitution:** When the quick substitution character (from `histchars`) is the first character on the line, selects previous entry (like `!!`) and substitutes. This is the only expansion not starting with `!`.

**Shell options affecting behavior:**
- `histverify`: expanded line reloaded into Readline buffer for review before execution
- `histreedit`: failed expansion reloaded into buffer for correction

**Testing:** `history -p` shows expansion result without executing. `history -s` adds to history without executing.

#### 9.3.1 Event Designators

| Designator          | Meaning                                                                                                                                                 |
|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `!`                 | Start history substitution (except when followed by space, tab, newline, CR, `=`, or metacharacters)                                                    |
| `!N`                | History entry N                                                                                                                                         |
| `!-N`               | History entry minus N (relative to current)                                                                                                             |
| `!!`                | Previous entry (synonym for `!-1`)                                                                                                                      |
| `!string`           | Most recent command starting with string                                                                                                                |
| `!?string[?]`       | Most recent command containing string. Trailing `?` optional if string is followed by newline. Missing string: reuse last search string (error if none) |
| `^string1^string2^` | Quick substitution: repeat last command, replace string1 with string2. Equivalent to `!!:s^string1^string2^`                                            |
| `!#`                | Entire command line typed so far                                                                                                                        |

#### 9.3.2 Word Designators

Word designators select words from the event. Optional; if omitted, the entire event is used. Separated from event by `:` (may be omitted if designator begins with `^`, `$`, `*`, `-`, or `%`).

Words numbered from 0 (usually the command word). Arguments begin at word 1. Inserted into current line separated by single spaces.

**Examples:**
- `!!` -- repeats preceding command in toto
- `!!:$` -- last word of preceding command (shortened to `!$`)
- `!fi:2` -- second argument of most recent command starting with "fi"

| Designator | Meaning                                                                                |
|------------|----------------------------------------------------------------------------------------|
| `0`        | The command word (0th word)                                                            |
| `N`        | The Nth word                                                                           |
| `^`        | The first argument (word 1)                                                            |
| `$`        | The last word. Expands to word 0 if only one word in line                              |
| `%`        | First word matched by most recent `?string?` search (closest to end of line)           |
| `X-Y`      | Range of words. `-Y` abbreviates `0-Y`                                                 |
| `*`        | All words except 0th. Synonym for `1-$`. Not an error with one word (expands to empty) |
| `X*`       | Abbreviates `X-$`                                                                      |
| `X-`       | Like `X*` but omits last word. Missing X defaults to 0                                 |

If word designator supplied without event specification, previous command is used (like `!!`).

#### 9.3.3 Modifiers

After the optional word designator, add one or more modifiers each preceded by `:`.

| Modifier     | Effect                                                                                                                                                                                                                                                                                                                        |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `h`          | Remove trailing filename component (head: like `dirname`)                                                                                                                                                                                                                                                                     |
| `t`          | Remove all leading filename components (tail: like `basename`)                                                                                                                                                                                                                                                                |
| `r`          | Remove trailing `.SUFFIX` (root/basename without extension)                                                                                                                                                                                                                                                                   |
| `e`          | Remove all but trailing suffix (extension only)                                                                                                                                                                                                                                                                               |
| `p`          | Print but do not execute                                                                                                                                                                                                                                                                                                      |
| `q`          | Quote substituted words, escaping further substitutions                                                                                                                                                                                                                                                                       |
| `x`          | Quote like `q` but break into words at spaces/tabs/newlines. `q` and `x` are mutually exclusive; last one supplied wins                                                                                                                                                                                                       |
| `s/OLD/NEW/` | Substitute NEW for first occurrence of OLD. Any delimiter may replace `/`. Delimiter can be escaped with `\` in OLD and NEW. `&` in NEW replaced with OLD (escape with `\`). Null OLD = last OLD substituted or last `!?string?` search string. Null NEW = delete matching OLD. Final delimiter optional if last char on line |
| `&`          | Repeat previous substitution                                                                                                                                                                                                                                                                                                  |
| `g` or `a`   | Apply `s` or `&` over entire event line (e.g., `gs/OLD/NEW/`)                                                                                                                                                                                                                                                                 |
| `G`          | Apply following `s` or `&` once to each word in the event                                                                                                                                                                                                                                                                     |
