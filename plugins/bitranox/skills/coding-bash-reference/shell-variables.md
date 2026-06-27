# Bash 5.3 Shell Variables Reference

Comprehensive reference for all shell variables in Bash 5.3. Bash automatically assigns default values to a number of variables.

---

## 1. Bourne Shell Variables

These variables are used by Bash in the same way as the Bourne shell. In some cases, Bash assigns a default value to the variable.

### CDPATH

| Property | Value                         |
|----------|-------------------------------|
| Type     | Settable                      |
| Value    | String (colon-separated list) |

A colon-separated list of directories used as a search path for the `cd` builtin command.

---

### HOME

| Property | Value                   |
|----------|-------------------------|
| Type     | Settable                |
| Value    | String (directory path) |

The current user's home directory; the default for the `cd` builtin command. The value of this variable is also used by tilde expansion.

---

### IFS

| Property | Value                       |
|----------|-----------------------------|
| Type     | Settable                    |
| Default  | Space, Tab, Newline         |
| Value    | String (list of characters) |

A list of characters that separate fields; used when the shell splits words as part of expansion and by the `read` builtin to split lines into words. See Word Splitting for a description of word splitting.

---

### MAIL

| Property | Value                               |
|----------|-------------------------------------|
| Type     | Settable                            |
| Value    | String (filename or directory path) |

If the value is set to a filename or directory name and the `MAILPATH` variable is not set, Bash informs the user of the arrival of mail in the specified file or Maildir-format directory.

---

### MAILPATH

| Property | Value                         |
|----------|-------------------------------|
| Type     | Settable                      |
| Value    | String (colon-separated list) |

A colon-separated list of filenames which the shell periodically checks for new mail. Each list entry can specify the message that is printed when new mail arrives in the mail file by separating the filename from the message with a `?`. When used in the text of the message, `$_` expands to the name of the current mail file.

---

### OPTARG

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

The value of the last option argument processed by the `getopts` builtin.

---

### OPTIND

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | Integer      |

The index of the next argument to be processed by the `getopts` builtin.

---

### PATH

| Property | Value                                                                                     |
|----------|-------------------------------------------------------------------------------------------|
| Type     | Settable                                                                                  |
| Default  | System-dependent (common: `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin`) |
| Value    | String (colon-separated list)                                                             |

A colon-separated list of directories in which the shell looks for commands. A zero-length (null) directory name in the value of `PATH` indicates the current directory. A null directory name may appear as two adjacent colons, or as an initial or trailing colon. The default path is system-dependent, and is set by the administrator who installs Bash.

---

### PS1

| Property | Value                  |
|----------|------------------------|
| Type     | Settable               |
| Default  | `\s-\v\$ `             |
| Value    | String (prompt string) |

The primary prompt string. The default value is `\s-\v\$ `. See Controlling the Prompt for the complete list of escape sequences that are expanded before `PS1` is displayed.

---

### PS2

| Property | Value                  |
|----------|------------------------|
| Type     | Settable               |
| Default  | `> `                   |
| Value    | String (prompt string) |

The secondary prompt string. The default value is `> `. `PS2` is expanded in the same way as `PS1` before being displayed.

---

## 2. Bash Variables

These variables are set or used by Bash, but other shells do not normally treat them specially. A few variables used by Bash are described in different chapters: variables for controlling the job control facilities (see Job Control Variables).

---

### _ (Underscore)

| Property | Value                    |
|----------|--------------------------|
| Type     | Set by shell (automatic) |
| Value    | String                   |

(`$_`, an underscore.) This has a number of meanings depending on context:
- **At shell startup**: set to the pathname used to invoke the shell or shell script being executed as passed in the environment or argument list.
- **After command execution**: expands to the last argument to the previous simple command executed in the foreground, after expansion.
- **In command environment**: set to the full pathname used to invoke each command executed and placed in the environment exported to that command.
- **When checking mail**: expands to the name of the mail file.

---

### BASH

| Property | Value             |
|----------|-------------------|
| Type     | Set by shell      |
| Value    | String (pathname) |

The full pathname used to execute the current instance of Bash.

---

### BASHOPTS

| Property | Value                         |
|----------|-------------------------------|
| Type     | **Read-only**                 |
| Value    | String (colon-separated list) |

A colon-separated list of enabled shell options. Each word in the list is a valid argument for the `-s` option to the `shopt` builtin command. The options appearing in `BASHOPTS` are those reported as `on` by `shopt`. If this variable is in the environment when Bash starts up, the shell enables each option in the list before reading any startup files. If this variable is exported, child shells will enable each option in the list.

---

### BASHPID

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Set by shell (assignments have no effect) |
| Value    | Integer (process ID)                      |

Expands to the process ID of the current Bash process. This differs from `$$` under certain circumstances, such as subshells that do not require Bash to be re-initialized. Assignments to `BASHPID` have no effect. If `BASHPID` is unset, it loses its special properties, even if it is subsequently reset.

---

### BASH_ALIASES

| Property | Value                        |
|----------|------------------------------|
| Type     | Settable (associative array) |
| Value    | Associative array            |

An associative array variable whose members correspond to the internal list of aliases as maintained by the `alias` builtin. Elements added to this array appear in the alias list; however, unsetting array elements currently does not cause aliases to be removed from the alias list. If `BASH_ALIASES` is unset, it loses its special properties, even if it is subsequently reset.

---

### BASH_ARGC

| Property | Value                                                       |
|----------|-------------------------------------------------------------|
| Type     | Set by shell (assignments have no effect; may not be unset) |
| Requires | `extdebug` shell option                                     |
| Value    | Array of integers                                           |

An array variable whose values are the number of parameters in each frame of the current Bash execution call stack. The number of parameters to the current subroutine (shell function or script executed with `.` or `source`) is at the top of the stack. When a subroutine is executed, the number of parameters passed is pushed onto `BASH_ARGC`. The shell sets `BASH_ARGC` only when in extended debugging mode (see the `extdebug` option to the `shopt` builtin). Setting `extdebug` after the shell has started to execute a subroutine, or referencing this variable when `extdebug` is not set, may result in inconsistent values.

---

### BASH_ARGV

| Property | Value                                                       |
|----------|-------------------------------------------------------------|
| Type     | Set by shell (assignments have no effect; may not be unset) |
| Requires | `extdebug` shell option                                     |
| Value    | Array of strings                                            |

An array variable containing all of the parameters in the current Bash execution call stack. The final parameter of the last subroutine call is at the top of the stack; the first parameter of the initial call is at the bottom. When a subroutine is executed, the shell pushes the supplied parameters onto `BASH_ARGV`. The shell sets `BASH_ARGV` only when in extended debugging mode. Setting `extdebug` after the shell has started to execute a script, or referencing this variable when `extdebug` is not set, may result in inconsistent values.

---

### BASH_ARGV0

| Property | Value    |
|----------|----------|
| Type     | Settable |
| Value    | String   |

When referenced, this variable expands to the name of the shell or shell script (identical to `$0`; see Special Parameters for the description of special parameter 0). Assigning a value to `BASH_ARGV0` sets `$0` to the same value. If `BASH_ARGV0` is unset, it loses its special properties, even if it is subsequently reset.

---

### BASH_CMDS

| Property | Value                        |
|----------|------------------------------|
| Type     | Settable (associative array) |
| Value    | Associative array            |

An associative array variable whose members correspond to the internal hash table of commands as maintained by the `hash` builtin. Adding elements to this array makes them appear in the hash table; however, unsetting array elements currently does not remove command names from the hash table. If `BASH_CMDS` is unset, it loses its special properties, even if it is subsequently reset.

---

### BASH_COMMAND

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

Expands to the command currently being executed or about to be executed, unless the shell is executing a command as the result of a trap, in which case it is the command executing at the time of the trap. If `BASH_COMMAND` is unset, it loses its special properties, even if it is subsequently reset.

---

### BASH_COMPAT

| Property | Value                                            |
|----------|--------------------------------------------------|
| Type     | Settable                                         |
| Value    | Decimal number (e.g., 4.2) or integer (e.g., 42) |

The value is used to set the shell's compatibility level. The value may be a decimal number (e.g., 4.2) or an integer (e.g., 42) corresponding to the desired compatibility level. If `BASH_COMPAT` is unset or set to the empty string, the compatibility level is set to the default for the current version. If `BASH_COMPAT` is set to a value that is not one of the valid compatibility levels, the shell prints an error message and sets the compatibility level to the default for the current version. A subset of the valid values correspond to the compatibility levels described in Shell Compatibility Mode. For example, 4.2 and 42 are valid values that correspond to the `compat42` `shopt` option and set the compatibility level to 42. The current version is also a valid value.

---

### BASH_ENV

| Property | Value             |
|----------|-------------------|
| Type     | Settable          |
| Value    | String (filename) |

If this variable is set when Bash is invoked to execute a shell script, its value is expanded and used as the name of a startup file to read before executing the script. Bash does not use `PATH` to search for the resultant filename. See Bash Startup Files.

---

### BASH_EXECUTION_STRING

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

The command argument to the `-c` invocation option.

---

### BASH_LINENO

| Property | Value                                                       |
|----------|-------------------------------------------------------------|
| Type     | Set by shell (assignments have no effect; may not be unset) |
| Value    | Array of integers                                           |

An array variable whose members are the line numbers in source files where each corresponding member of `FUNCNAME` was invoked. `${BASH_LINENO[$i]}` is the line number in the source file (`${BASH_SOURCE[$i+1]}`) where `${FUNCNAME[$i]}` was called (or `${BASH_LINENO[$i-1]}` if referenced within another shell function). Use `LINENO` to obtain the current line number.

---

### BASH_LOADABLES_PATH

| Property | Value                         |
|----------|-------------------------------|
| Type     | Settable                      |
| Value    | String (colon-separated list) |

A colon-separated list of directories in which the `enable` command looks for dynamically loadable builtins.

---

### BASH_MONOSECONDS

| Property | Value                  |
|----------|------------------------|
| Type     | Set by shell (dynamic) |
| Value    | Integer                |

Each time this variable is referenced, it expands to the value returned by the system's monotonic clock, if one is available. If there is no monotonic clock, this is equivalent to `EPOCHSECONDS`. If `BASH_MONOSECONDS` is unset, it loses its special properties, even if it is subsequently reset.

**Note**: This is a Bash 5.3 addition.

---

### BASH_REMATCH

| Property | Value            |
|----------|------------------|
| Type     | Set by shell     |
| Value    | Array of strings |

An array variable whose members are assigned by the `=~` binary operator to the `[[` conditional command. The element with index 0 is the portion of the string matching the entire regular expression. The element with index N is the portion of the string matching the Nth parenthesized subexpression.

---

### BASH_SOURCE

| Property | Value                                                       |
|----------|-------------------------------------------------------------|
| Type     | Set by shell (assignments have no effect; may not be unset) |
| Value    | Array of strings (filenames)                                |

An array variable whose members are the source filenames where the corresponding shell function names in the `FUNCNAME` array variable are defined. The shell function `${FUNCNAME[$i]}` is defined in the file `${BASH_SOURCE[$i]}` and called from `${BASH_SOURCE[$i+1]}`.

---

### BASH_SUBSHELL

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Default  | 0            |
| Value    | Integer      |

Incremented by one within each subshell or subshell environment when the shell begins executing in that environment. The initial value is 0. If `BASH_SUBSHELL` is unset, it loses its special properties, even if it is subsequently reset.

---

### BASH_TRAPSIG

| Property | Value                   |
|----------|-------------------------|
| Type     | Set by shell            |
| Value    | Integer (signal number) |

Set to the signal number corresponding to the trap action being executed during its execution. See the description of `trap` for information about signal numbers and trap execution.

**Note**: This is a Bash 5.3 addition.

---

### BASH_VERSINFO

| Property | Value               |
|----------|---------------------|
| Type     | **Read-only**       |
| Value    | Array (indexed 0-5) |

A readonly array variable whose members hold version information for this instance of Bash. The values assigned to the array members are:

| Index              | Member         | Description                              |
|--------------------|----------------|------------------------------------------|
| `BASH_VERSINFO[0]` | Major version  | The major version number (the "release") |
| `BASH_VERSINFO[1]` | Minor version  | The minor version number (the "version") |
| `BASH_VERSINFO[2]` | Patch level    | The patch level                          |
| `BASH_VERSINFO[3]` | Build version  | The build version                        |
| `BASH_VERSINFO[4]` | Release status | The release status (e.g., `beta`)        |
| `BASH_VERSINFO[5]` | Machine type   | The value of `MACHTYPE`                  |

---

### BASH_VERSION

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

Expands to a string describing the version of this instance of Bash (e.g., `5.2.37(3)-release`).

---

### BASH_XTRACEFD

| Property | Value                     |
|----------|---------------------------|
| Type     | Settable                  |
| Value    | Integer (file descriptor) |

If set to an integer corresponding to a valid file descriptor, Bash writes the trace output generated when `set -x` is enabled to that file descriptor, instead of the standard error. This allows tracing output to be separated from diagnostic and error messages. The file descriptor is closed when `BASH_XTRACEFD` is unset or assigned a new value. Unsetting `BASH_XTRACEFD` or assigning it the empty string causes the trace output to be sent to the standard error. Note that setting `BASH_XTRACEFD` to 2 (the standard error file descriptor) and then unsetting it will result in the standard error being closed.

---

### CHILD_MAX

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Settable                                  |
| Maximum  | 8192                                      |
| Minimum  | System-dependent (POSIX-mandated minimum) |
| Value    | Integer                                   |

Set the number of exited child status values for the shell to remember. Bash will not allow this value to be decreased below a POSIX-mandated minimum, and there is a maximum value (currently 8192) that this may not exceed. The minimum value is system-dependent.

---

### COLUMNS

| Property | Value                        |
|----------|------------------------------|
| Type     | Settable (auto-set by shell) |
| Value    | Integer                      |

Used by the `select` command to determine the terminal width when printing selection lists. Automatically set if the `checkwinsize` option is enabled (see The Shopt Builtin), or in an interactive shell upon receipt of a `SIGWINCH`.

---

### COMP_CWORD

| Property | Value                        |
|----------|------------------------------|
| Type     | Set by shell                 |
| Context  | Programmable completion only |
| Value    | Integer (index)              |

An index into `${COMP_WORDS}` of the word containing the current cursor position. This variable is available only in shell functions invoked by the programmable completion facilities.

---

### COMP_KEY

| Property | Value                        |
|----------|------------------------------|
| Type     | Set by shell                 |
| Context  | Programmable completion only |
| Value    | Integer (key code)           |

The key (or final key of a key sequence) used to invoke the current completion function. This variable is available only in shell functions and external commands invoked by the programmable completion facilities.

---

### COMP_LINE

| Property | Value                        |
|----------|------------------------------|
| Type     | Set by shell                 |
| Context  | Programmable completion only |
| Value    | String                       |

The current command line. This variable is available only in shell functions and external commands invoked by the programmable completion facilities.

---

### COMP_POINT

| Property | Value                        |
|----------|------------------------------|
| Type     | Set by shell                 |
| Context  | Programmable completion only |
| Value    | Integer                      |

The index of the current cursor position relative to the beginning of the current command. If the current cursor position is at the end of the current command, the value of this variable is equal to `${#COMP_LINE}`. This variable is available only in shell functions and external commands invoked by the programmable completion facilities.

---

### COMP_TYPE

| Property | Value                        |
|----------|------------------------------|
| Type     | Set by shell                 |
| Context  | Programmable completion only |
| Value    | Integer                      |

Set to an integer value corresponding to the type of attempted completion that caused a completion function to be called:

| Value | Meaning                                         |
|-------|-------------------------------------------------|
| TAB   | Normal completion                               |
| `?`   | Listing completions after successive tabs       |
| `!`   | Listing alternatives on partial word completion |
| `@`   | List completions if the word is not unmodified  |
| `%`   | Menu completion                                 |

This variable is available only in shell functions and external commands invoked by the programmable completion facilities.

---

### COMP_WORDBREAKS

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (set of characters) |

The set of characters that the Readline library treats as word separators when performing word completion. If `COMP_WORDBREAKS` is unset, it loses its special properties, even if it is subsequently reset.

---

### COMP_WORDS

| Property | Value                        |
|----------|------------------------------|
| Type     | Set by shell                 |
| Context  | Programmable completion only |
| Value    | Array of strings             |

An array variable consisting of the individual words in the current command line. The line is split into words as Readline would split it, using `COMP_WORDBREAKS` as described above. This variable is available only in shell functions invoked by the programmable completion facilities.

---

### COMPREPLY

| Property | Value                   |
|----------|-------------------------|
| Type     | Settable (array)        |
| Context  | Programmable completion |
| Value    | Array of strings        |

An array variable from which Bash reads the possible completions generated by a shell function invoked by the programmable completion facility. Each array element contains one possible completion.

---

### COPROC

| Property | Value                    |
|----------|--------------------------|
| Type     | Set by shell             |
| Value    | Array (file descriptors) |

An array variable created to hold the file descriptors for output from and input to an unnamed coprocess. See Coprocesses.

---

### DIRSTACK

| Property | Value                                                                                 |
|----------|---------------------------------------------------------------------------------------|
| Type     | Settable (partial: can modify existing entries, but use `pushd`/`popd` to add/remove) |
| Value    | Array of strings (directory paths)                                                    |

An array variable containing the current contents of the directory stack. Directories appear in the stack in the order they are displayed by the `dirs` builtin. Assigning to members of this array variable may be used to modify directories already in the stack, but the `pushd` and `popd` builtins must be used to add and remove directories. Assigning to this variable does not change the current directory. If `DIRSTACK` is unset, it loses its special properties, even if it is subsequently reset.

---

### EMACS

| Property | Value                |
|----------|----------------------|
| Type     | Environment variable |
| Value    | String               |

If Bash finds this variable in the environment when the shell starts, and its value is `t`, Bash assumes that the shell is running in an Emacs shell buffer and disables line editing.

---

### ENV

| Property | Value             |
|----------|-------------------|
| Type     | Settable          |
| Value    | String (filename) |

Expanded and executed similarly to `BASH_ENV` when an interactive shell is invoked in POSIX mode.

---

### EPOCHREALTIME

| Property | Value                                           |
|----------|-------------------------------------------------|
| Type     | Set by shell (dynamic; assignments are ignored) |
| Value    | Floating-point number (microsecond granularity) |

Each time this parameter is referenced, it expands to the number of seconds since the Unix Epoch as a floating-point value with micro-second granularity (see the documentation for the C library function `time` for the definition of Epoch). Assignments to `EPOCHREALTIME` are ignored. If `EPOCHREALTIME` is unset, it loses its special properties, even if it is subsequently reset.

---

### EPOCHSECONDS

| Property | Value                                           |
|----------|-------------------------------------------------|
| Type     | Set by shell (dynamic; assignments are ignored) |
| Value    | Integer                                         |

Each time this parameter is referenced, it expands to the number of seconds since the Unix Epoch (see the documentation for the C library function `time` for the definition of Epoch). Assignments to `EPOCHSECONDS` are ignored. If `EPOCHSECONDS` is unset, it loses its special properties, even if it is subsequently reset.

---

### EUID

| Property | Value         |
|----------|---------------|
| Type     | **Read-only** |
| Value    | Integer       |

The numeric effective user id of the current user.

---

### EXECIGNORE

| Property | Value                                           |
|----------|-------------------------------------------------|
| Type     | Settable                                        |
| Value    | String (colon-separated list of shell patterns) |

A colon-separated list of shell patterns defining the set of filenames to be ignored by command search using `PATH`. Files whose full pathnames match one of these patterns are not considered executable files for the purposes of completion and command execution via `PATH` lookup. This does not affect the behavior of the `[`, `test`, and `[[` commands. Full pathnames in the command hash table are not subject to `EXECIGNORE`. Use this variable to ignore shared library files that have the executable bit set, but are not executable files. The pattern matching honors the setting of the `extglob` shell option.

---

### FCEDIT

| Property | Value                   |
|----------|-------------------------|
| Type     | Settable                |
| Value    | String (editor command) |

The editor used as a default by the `fc` builtin command.

---

### FIGNORE

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Settable                                  |
| Value    | String (colon-separated list of suffixes) |

A colon-separated list of suffixes to ignore when performing filename completion. A filename whose suffix matches one of the entries in `FIGNORE` is excluded from the list of matched filenames. A sample value is `.o:~`.

---

### FUNCNAME

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Set by shell (assignments have no effect) |
| Value    | Array of strings                          |

An array variable containing the names of all shell functions currently in the execution call stack. The element with index 0 is the name of any currently-executing shell function. The bottom-most element (the one with the highest index) is `"main"`. This variable exists only when a shell function is executing. If `FUNCNAME` is unset, it loses its special properties, even if it is subsequently reset.

This variable can be used with `BASH_LINENO` and `BASH_SOURCE`. Each element of `FUNCNAME` has corresponding elements in `BASH_LINENO` and `BASH_SOURCE` to describe the call stack. For instance, `${FUNCNAME[$i]}` was called from the file `${BASH_SOURCE[$i+1]}` at line number `${BASH_LINENO[$i]}`. The `caller` builtin displays the current call stack using this information.

---

### FUNCNEST

| Property | Value                    |
|----------|--------------------------|
| Type     | Settable                 |
| Value    | Integer (greater than 0) |

A numeric value greater than 0 defines a maximum function nesting level. Function invocations that exceed this nesting level cause the current command to abort.

---

### GLOBIGNORE

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Settable                                  |
| Value    | String (colon-separated list of patterns) |

A colon-separated list of patterns defining the set of file names to be ignored by filename expansion. If a file name matched by a filename expansion pattern also matches one of the patterns in `GLOBIGNORE`, it is removed from the list of matches. The pattern matching honors the setting of the `extglob` shell option.

---

### GLOBSORT

| Property | Value                                                                    |
|----------|--------------------------------------------------------------------------|
| Type     | Settable                                                                 |
| Default  | Sort by name, ascending lexicographic order (determined by `LC_COLLATE`) |
| Value    | String (sort specifier)                                                  |

Controls how the results of filename expansion are sorted. If this variable is unset or set to the null string, filename expansion uses the historical behavior of sorting by name, in ascending lexicographic order as determined by the `LC_COLLATE` shell variable.

If set, a valid value begins with an optional `+` (ignored) or `-` (reverses sort order from ascending to descending), followed by a sort specifier:

| Specifier | Sorts by                                                                       |
|-----------|--------------------------------------------------------------------------------|
| `name`    | Name (lexicographic order)                                                     |
| `numeric` | Names as numbers (digits-only names sorted numerically; e.g., "2" before "10") |
| `size`    | File size                                                                      |
| `mtime`   | Modification time                                                              |
| `atime`   | Access time                                                                    |
| `ctime`   | Inode change time                                                              |
| `blocks`  | Number of blocks                                                               |
| `nosort`  | Disables sorting; returns results in filesystem order (ignores leading `-`)    |

If any of the non-name keys compare as equal, sorting uses the name as a secondary sort key. When using `numeric`, names containing non-digits sort after all-digit names using traditional behavior.

If the sort specifier is missing, it defaults to `name`, so `+` is equivalent to the null string, and `-` sorts by name in descending order. Any invalid value restores the historical sorting behavior.

**Example**: `-mtime` sorts results in descending order by modification time (newest first).

**Note**: This is a Bash 5.3 addition.

---

### GROUPS

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Set by shell (assignments have no effect) |
| Value    | Array of integers                         |

An array variable containing the list of groups of which the current user is a member. Assignments to `GROUPS` have no effect. If `GROUPS` is unset, it loses its special properties, even if it is subsequently reset.

---

### histchars

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Default  | `!^#`                      |
| Value    | String (2 or 3 characters) |

The two or three characters which control history expansion, quick substitution, and tokenization:

| Position       | Name                         | Default | Description                                                                                                                                                                                                                                                       |
|----------------|------------------------------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1st            | History expansion character  | `!`     | Begins a history expansion                                                                                                                                                                                                                                        |
| 2nd            | Quick substitution character | `^`     | When appearing as the first character on the line, repeats the previous command replacing one string with another                                                                                                                                                 |
| 3rd (optional) | History comment character    | `#`     | Indicates that the remainder of the line is a comment when it appears as the first character of a word. Disables history substitution for the remaining words on the line. Does not necessarily cause the shell parser to treat the rest of the line as a comment |

---

### HISTCMD

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Set by shell (assignments have no effect) |
| Value    | Integer                                   |

The history number, or index in the history list, of the current command. If `HISTCMD` is unset, it loses its special properties, even if it is subsequently reset.

---

### HISTCONTROL

| Property | Value                                   |
|----------|-----------------------------------------|
| Type     | Settable                                |
| Value    | String (colon-separated list of values) |

A colon-separated list of values controlling how commands are saved on the history list:

| Value         | Effect                                                                                                   |
|---------------|----------------------------------------------------------------------------------------------------------|
| `ignorespace` | Lines beginning with a space character are not saved                                                     |
| `ignoredups`  | Lines matching the previous history entry are not saved                                                  |
| `ignoreboth`  | Shorthand for `ignorespace` and `ignoredups`                                                             |
| `erasedups`   | All previous lines matching the current line are removed from the history list before that line is saved |

If `HISTCONTROL` is unset or does not include a valid value, Bash saves all lines read by the shell parser on the history list, subject to the value of `HISTIGNORE`. If the first line of a multi-line compound command was saved, the second and subsequent lines are not tested and are added to the history regardless of the value of `HISTCONTROL`. If the first line was not saved, the second and subsequent lines of the command are not saved either.

---

### HISTFILE

| Property | Value             |
|----------|-------------------|
| Type     | Settable          |
| Default  | `~/.bash_history` |
| Value    | String (filename) |

The name of the file to which the command history is saved. Bash assigns a default value of `~/.bash_history`. If `HISTFILE` is unset or null, the shell does not save the command history when it exits.

---

### HISTFILESIZE

| Property | Value                                                 |
|----------|-------------------------------------------------------|
| Type     | Settable                                              |
| Default  | Value of `HISTSIZE` (set after reading startup files) |
| Value    | Integer                                               |

The maximum number of lines contained in the history file. When this variable is assigned a value, the history file is truncated, if necessary, to contain no more than the number of history entries that total no more than that number of lines by removing the oldest entries. If the history list contains multi-line entries, the history file may contain more lines than this maximum to avoid leaving partial history entries. The history file is also truncated to this size after writing it when a shell exits or by the `history` builtin. If the value is 0, the history file is truncated to zero size. Non-numeric values and numeric values less than zero inhibit truncation.

---

### HISTIGNORE

| Property | Value                                     |
|----------|-------------------------------------------|
| Type     | Settable                                  |
| Value    | String (colon-separated list of patterns) |

A colon-separated list of patterns used to decide which command lines should be saved on the history list. If a command line matches one of the patterns, it is not saved. Each pattern is anchored at the beginning of the line and must match the complete line (Bash does not implicitly append a `*`). Each pattern is tested against the line after the checks specified by `HISTCONTROL` are applied. In addition to the normal shell pattern matching characters, `&` matches the previous history line. A backslash escapes the `&`; the backslash is removed before attempting a match. The pattern matching honors the setting of the `extglob` shell option.

If the first line of a multi-line compound command was saved, the second and subsequent lines are not tested, and are added to the history regardless of the value of `HISTIGNORE`. If the first line was not saved, the second and subsequent lines of the command are not saved either.

`HISTIGNORE` subsumes some of the function of `HISTCONTROL`. A pattern of `&` is identical to `ignoredups`, and a pattern of `[ ]*` is identical to `ignorespace`. Combining these two patterns, separating them with a colon, provides the functionality of `ignoreboth`.

---

### HISTSIZE

| Property | Value                                 |
|----------|---------------------------------------|
| Type     | Settable                              |
| Default  | 500 (set after reading startup files) |
| Value    | Integer                               |

The maximum number of commands to remember on the history list. If the value is 0, commands are not saved in the history list. Numeric values less than zero result in every command being saved on the history list (there is no limit).

---

### HISTTIMEFORMAT

| Property | Value                                |
|----------|--------------------------------------|
| Type     | Settable                             |
| Value    | String (`strftime(3)` format string) |

If this variable is set and not null, its value is used as a format string for `strftime(3)` to print the time stamp associated with each history entry displayed by the `history` builtin. If this variable is set, the shell writes time stamps to the history file so they may be preserved across shell sessions. This uses the history comment character to distinguish timestamps from other history lines.

---

### HOSTFILE

| Property | Value             |
|----------|-------------------|
| Type     | Settable          |
| Value    | String (filename) |

Contains the name of a file in the same format as `/etc/hosts` that should be read when the shell needs to complete a hostname. The list of possible hostname completions may be changed while the shell is running; the next time hostname completion is attempted after the value is changed, Bash adds the contents of the new file to the existing list. If `HOSTFILE` is set but has no value, or does not name a readable file, Bash attempts to read `/etc/hosts` to obtain the list of possible hostname completions. When `HOSTFILE` is unset, Bash clears the hostname list.

---

### HOSTNAME

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

The name of the current host.

---

### HOSTTYPE

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

A string describing the machine Bash is running on.

---

### IGNOREEOF

| Property | Value                                 |
|----------|---------------------------------------|
| Type     | Settable                              |
| Default  | 10 (when set but non-numeric or null) |
| Context  | Interactive shells only               |
| Value    | Integer                               |

Controls the action of the shell on receipt of an `EOF` character as the sole input. If set, the value is the number of consecutive `EOF` characters that can be read as the first character on an input line before Bash exits. If the variable is set but does not have a numeric value, or the value is null, then the default is 10. If the variable is unset, then `EOF` signifies the end of input to the shell. This is only in effect for interactive shells.

---

### INPUTRC

| Property | Value             |
|----------|-------------------|
| Type     | Settable          |
| Default  | `~/.inputrc`      |
| Value    | String (filename) |

The name of the Readline initialization file, overriding the default of `~/.inputrc`.

---

### INSIDE_EMACS

| Property | Value                |
|----------|----------------------|
| Type     | Environment variable |
| Value    | String               |

If Bash finds this variable in the environment when the shell starts, it assumes that the shell is running in an Emacs shell buffer and may disable line editing depending on the value of `TERM`.

---

### LANG

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

Used to determine the locale category for any category not specifically selected with a variable starting with `LC_`.

---

### LC_ALL

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

This variable overrides the value of `LANG` and any other `LC_` variable specifying a locale category.

---

### LC_COLLATE

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

This variable determines the collation order used when sorting the results of filename expansion, and determines the behavior of range expressions, equivalence classes, and collating sequences within filename expansion and pattern matching.

---

### LC_CTYPE

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

This variable determines the interpretation of characters and the behavior of character classes within filename expansion and pattern matching.

---

### LC_MESSAGES

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

This variable determines the locale used to translate double-quoted strings preceded by a `$` (see Locale Translation).

---

### LC_NUMERIC

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

This variable determines the locale category used for number formatting.

---

### LC_TIME

| Property | Value                      |
|----------|----------------------------|
| Type     | Settable                   |
| Value    | String (locale identifier) |

This variable determines the locale category used for data and time formatting.

---

### LINENO

| Property | Value                  |
|----------|------------------------|
| Type     | Set by shell (dynamic) |
| Value    | Integer                |

The line number in the script or shell function currently executing. Line numbers start with 1. When not in a script or function, the value is not guaranteed to be meaningful. If `LINENO` is unset, it loses its special properties, even if it is subsequently reset.

---

### LINES

| Property | Value                        |
|----------|------------------------------|
| Type     | Settable (auto-set by shell) |
| Value    | Integer                      |

Used by the `select` command to determine the column length for printing selection lists. Automatically set if the `checkwinsize` option is enabled (see The Shopt Builtin), or in an interactive shell upon receipt of a `SIGWINCH`.

---

### MACHTYPE

| Property | Value                                  |
|----------|----------------------------------------|
| Type     | Set by shell                           |
| Value    | String (GNU CPU-COMPANY-SYSTEM format) |

A string that fully describes the system type on which Bash is executing, in the standard GNU CPU-COMPANY-SYSTEM format.

---

### MAILCHECK

| Property | Value             |
|----------|-------------------|
| Type     | Settable          |
| Default  | 60                |
| Value    | Integer (seconds) |

How often (in seconds) that the shell should check for mail in the files specified in the `MAILPATH` or `MAIL` variables. The default is 60 seconds. When it is time to check for mail, the shell does so before displaying the primary prompt. If this variable is unset, or set to a value that is not a number greater than or equal to zero, the shell disables mail checking.

---

### MAPFILE

| Property | Value            |
|----------|------------------|
| Type     | Set by shell     |
| Value    | Array of strings |

An array variable created to hold the text read by the `mapfile` builtin when no variable name is supplied.

---

### OLDPWD

| Property | Value                   |
|----------|-------------------------|
| Type     | Set by shell            |
| Value    | String (directory path) |

The previous working directory as set by the `cd` builtin.

---

### OPTERR

| Property | Value                                          |
|----------|------------------------------------------------|
| Type     | Settable                                       |
| Default  | 1 (initialized each time the shell is invoked) |
| Value    | Integer                                        |

If set to the value 1, Bash displays error messages generated by the `getopts` builtin command. `OPTERR` is initialized to 1 each time the shell is invoked.

---

### OSTYPE

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

A string describing the operating system Bash is running on.

---

### PIPESTATUS

| Property | Value                                  |
|----------|----------------------------------------|
| Type     | Set by shell                           |
| Value    | Array of integers (exit status values) |

An array variable containing a list of exit status values from the commands in the most-recently-executed foreground pipeline, which may consist of only a simple command. Bash sets `PIPESTATUS` after executing multi-element pipelines, timed and negated pipelines, simple commands, subshells created with the `(` operator, the `[[` and `((` compound commands, and after error conditions that result in the shell aborting command execution.

---

### POSIXLY_CORRECT

| Property | Value                           |
|----------|---------------------------------|
| Type     | Settable / Environment variable |
| Value    | String (any value)              |

If this variable is in the environment when Bash starts, the shell enters POSIX mode before reading the startup files, as if the `--posix` invocation option had been supplied. If it is set while the shell is running, Bash enables POSIX mode, as if the command `set -o posix` had been executed. When the shell enters POSIX mode, it sets this variable if it was not already set.

---

### PPID

| Property | Value                |
|----------|----------------------|
| Type     | **Read-only**        |
| Value    | Integer (process ID) |

The process ID of the shell's parent process.

---

### PROMPT_COMMAND

| Property | Value           |
|----------|-----------------|
| Type     | Settable        |
| Value    | String or Array |

If this variable is set, and is an array, the value of each set element is interpreted as a command to execute before printing the primary prompt (`$PS1`). If this is set but not an array variable, its value is used as a command to execute instead.

---

### PROMPT_DIRTRIM

| Property | Value                       |
|----------|-----------------------------|
| Type     | Settable                    |
| Value    | Integer (greater than zero) |

If set to a number greater than zero, the value is used as the number of trailing directory components to retain when expanding the `\w` and `\W` prompt string escapes. Characters removed are replaced with an ellipsis.

---

### PS0

| Property | Value                  |
|----------|------------------------|
| Type     | Settable               |
| Value    | String (prompt string) |

The value of this parameter is expanded like `PS1` and displayed by interactive shells after reading a command and before the command is executed.

---

### PS3

| Property | Value                  |
|----------|------------------------|
| Type     | Settable               |
| Default  | `#? `                  |
| Value    | String (prompt string) |

The value of this variable is used as the prompt for the `select` command. If this variable is not set, the `select` command prompts with `#? `.

---

### PS4

| Property | Value                  |
|----------|------------------------|
| Type     | Settable               |
| Default  | `+ `                   |
| Value    | String (prompt string) |

The value of this parameter is expanded like `PS1` and the expanded value is the prompt printed before the command line is echoed when the `-x` option is set (see The Set Builtin). The first character of the expanded value is replicated multiple times, as necessary, to indicate multiple levels of indirection. The default is `+ `.

---

### PWD

| Property | Value                   |
|----------|-------------------------|
| Type     | Set by shell            |
| Value    | String (directory path) |

The current working directory as set by the `cd` builtin.

---

### RANDOM

| Property | Value                                                                           |
|----------|---------------------------------------------------------------------------------|
| Type     | Settable (dynamic; reading returns random value, assigning seeds the generator) |
| Range    | 0 to 32767                                                                      |
| Value    | Integer                                                                         |

Each time this parameter is referenced, it expands to a random integer between 0 and 32767. Assigning a value to `RANDOM` initializes (seeds) the sequence of random numbers. Seeding the random number generator with the same constant value produces the same sequence of values. If `RANDOM` is unset, it loses its special properties, even if it is subsequently reset.

---

### READLINE_ARGUMENT

| Property | Value              |
|----------|--------------------|
| Type     | Set by shell       |
| Context  | `bind -x` commands |
| Value    | Integer            |

Any numeric argument given to a Readline command that was defined using `bind -x` when it was invoked.

---

### READLINE_LINE

| Property | Value              |
|----------|--------------------|
| Type     | Settable           |
| Context  | `bind -x` commands |
| Value    | String             |

The contents of the Readline line buffer, for use with `bind -x`.

---

### READLINE_MARK

| Property | Value              |
|----------|--------------------|
| Type     | Settable           |
| Context  | `bind -x` commands |
| Value    | Integer (position) |

The position of the "mark" (saved insertion point) in the Readline line buffer, for use with `bind -x`. The characters between the insertion point and the mark are often called the "region".

---

### READLINE_POINT

| Property | Value              |
|----------|--------------------|
| Type     | Settable           |
| Context  | `bind -x` commands |
| Value    | Integer (position) |

The position of the insertion point in the Readline line buffer, for use with `bind -x`.

---

### REPLY

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | String       |

The default variable for the `read` builtin; set to the line read when `read` is not supplied a variable name argument.

---

### SECONDS

| Property | Value              |
|----------|--------------------|
| Type     | Settable (dynamic) |
| Value    | Integer            |

This variable expands to the number of seconds since the shell was started. Assignment to this variable resets the count to the value assigned, and the expanded value becomes the value assigned plus the number of seconds since the assignment. The number of seconds at shell invocation and the current time are always determined by querying the system clock at one-second resolution. If `SECONDS` is unset, it loses its special properties, even if it is subsequently reset.

---

### SHELL

| Property | Value                           |
|----------|---------------------------------|
| Type     | Settable / Environment variable |
| Value    | String (pathname)               |

This environment variable expands to the full pathname to the shell. If it is not set when the shell starts, Bash assigns to it the full pathname of the current user's login shell.

---

### SHELLOPTS

| Property | Value                         |
|----------|-------------------------------|
| Type     | **Read-only**                 |
| Value    | String (colon-separated list) |

A colon-separated list of enabled shell options. Each word in the list is a valid argument for the `-o` option to the `set` builtin command. The options appearing in `SHELLOPTS` are those reported as `on` by `set -o`. If this variable is in the environment when Bash starts up, the shell enables each option in the list before reading any startup files. If this variable is exported, child shells will enable each option in the list.

---

### SHLVL

| Property | Value        |
|----------|--------------|
| Type     | Set by shell |
| Value    | Integer      |

Incremented by one each time a new instance of Bash is started. This is intended to be a count of how deeply your Bash shells are nested.

---

### SRANDOM

| Property | Value                                              |
|----------|----------------------------------------------------|
| Type     | Set by shell (dynamic; assignments have no effect) |
| Value    | Integer (32-bit)                                   |

This variable expands to a 32-bit pseudo-random number each time it is referenced. The random number generator is not linear on systems that support `/dev/urandom` or `arc4random`, so each returned number has no relationship to the numbers preceding it. The random number generator cannot be seeded, so assignments to this variable have no effect. If `SRANDOM` is unset, it loses its special properties, even if it is subsequently reset.

---

### TIMEFORMAT

| Property | Value                                    |
|----------|------------------------------------------|
| Type     | Settable                                 |
| Default  | `$'\nreal\t%3lR\nuser\t%3lU\nsys\t%3lS'` |
| Value    | String (format string)                   |

The value of this parameter is used as a format string specifying how the timing information for pipelines prefixed with the `time` reserved word should be displayed. The `%` character introduces an escape sequence that is expanded to a time value or other information.

**Escape sequences:**

| Sequence   | Description                                    |
|------------|------------------------------------------------|
| `%%`       | A literal `%`                                  |
| `%[P][l]R` | The elapsed time in seconds                    |
| `%[P][l]U` | The number of CPU seconds spent in user mode   |
| `%[P][l]S` | The number of CPU seconds spent in system mode |
| `%P`       | The CPU percentage, computed as (%U + %S) / %R |

**Optional modifiers:**

| Modifier    | Description                                                                                                                                                                                                                                                                                                        |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `P` (digit) | Precision: the number of fractional digits after a decimal point. A value of 0 causes no decimal point or fraction to be output. `time` prints at most six digits after the decimal point; values of P greater than 6 are changed to 6. If P is not specified, `time` prints three digits after the decimal point. |
| `l`         | Longer format, including minutes, of the form `MMmSS.FFs`. The value of P determines whether the fraction is included.                                                                                                                                                                                             |

If this variable is not set, Bash acts as if it had the value `$'\nreal\t%3lR\nuser\t%3lU\nsys\t%3lS'`. If the value is null, Bash does not display any timing information. A trailing newline is added when the format string is displayed.

---

### TMOUT

| Property | Value                                |
|----------|--------------------------------------|
| Type     | Settable                             |
| Value    | Integer (seconds, greater than zero) |

If set to a value greater than zero, the `read` builtin uses the value as its default timeout. The `select` command terminates if input does not arrive after `TMOUT` seconds when input is coming from a terminal.

In an interactive shell, the value is interpreted as the number of seconds to wait for a line of input after issuing the primary prompt. Bash terminates after waiting for that number of seconds if a complete line of input does not arrive.

---

### TMPDIR

| Property | Value                   |
|----------|-------------------------|
| Type     | Settable                |
| Value    | String (directory path) |

If set, Bash uses its value as the name of a directory in which Bash creates temporary files for the shell's use.

---

### UID

| Property | Value         |
|----------|---------------|
| Type     | **Read-only** |
| Value    | Integer       |

The numeric real user id of the current user.

---

## Quick Reference: Read-Only Variables

These variables cannot be assigned to:

| Variable        | Description                                      |
|-----------------|--------------------------------------------------|
| `BASHOPTS`      | Colon-separated list of enabled `shopt` options  |
| `BASH_VERSINFO` | Array of version information                     |
| `EUID`          | Effective user ID                                |
| `PPID`          | Parent process ID                                |
| `SHELLOPTS`     | Colon-separated list of enabled `set -o` options |
| `UID`           | Real user ID                                     |

## Quick Reference: Variables That Lose Special Properties When Unset

If any of these variables are unset, they lose their special properties even if subsequently reset:

`BASH_ALIASES`, `BASH_ARGV0`, `BASH_CMDS`, `BASH_COMMAND`, `BASH_MONOSECONDS`, `BASH_SUBSHELL`, `BASHPID`, `COMP_WORDBREAKS`, `DIRSTACK`, `EPOCHREALTIME`, `EPOCHSECONDS`, `FUNCNAME`, `GROUPS`, `HISTCMD`, `LINENO`, `RANDOM`, `SECONDS`, `SRANDOM`

## Quick Reference: Variables That Cannot Be Unset

These variables may not be unset:

`BASH_ARGC`, `BASH_ARGV`, `BASH_LINENO`, `BASH_SOURCE`

## Quick Reference: Variables Where Assignments Have No Effect

| Variable        | Notes                                  |
|-----------------|----------------------------------------|
| `BASHPID`       | Assignments ignored                    |
| `BASH_ARGC`     | Assignments ignored                    |
| `BASH_ARGV`     | Assignments ignored                    |
| `BASH_LINENO`   | Assignments ignored                    |
| `BASH_SOURCE`   | Assignments ignored                    |
| `EPOCHREALTIME` | Assignments ignored                    |
| `EPOCHSECONDS`  | Assignments ignored                    |
| `FUNCNAME`      | Assignments ignored                    |
| `GROUPS`        | Assignments ignored                    |
| `HISTCMD`       | Assignments ignored                    |
| `SRANDOM`       | Assignments ignored (cannot be seeded) |

## Quick Reference: Dynamic Variables

These variables return a new/computed value each time they are referenced:

| Variable           | Returns                                                            |
|--------------------|--------------------------------------------------------------------|
| `BASH_MONOSECONDS` | System monotonic clock value                                       |
| `EPOCHREALTIME`    | Seconds since Unix Epoch (floating-point, microsecond granularity) |
| `EPOCHSECONDS`     | Seconds since Unix Epoch (integer)                                 |
| `LINENO`           | Current line number                                                |
| `RANDOM`           | Random integer 0-32767 (seedable)                                  |
| `SECONDS`          | Seconds since shell start (resettable)                             |
| `SRANDOM`          | 32-bit pseudo-random number (not seedable)                         |

## Quick Reference: Programmable Completion Variables

Available only in shell functions/commands invoked by the programmable completion facilities:

| Variable          | Description                                     |
|-------------------|-------------------------------------------------|
| `COMP_CWORD`      | Index into `COMP_WORDS` of word at cursor       |
| `COMP_KEY`        | Key used to invoke completion                   |
| `COMP_LINE`       | Current command line                            |
| `COMP_POINT`      | Cursor position relative to command start       |
| `COMP_TYPE`       | Type of completion attempted                    |
| `COMP_WORDBREAKS` | Word separator characters for completion        |
| `COMP_WORDS`      | Array of words in current command line          |
| `COMPREPLY`       | Array of possible completions (set by function) |

## Quick Reference: Call Stack Variables

Used together to describe the execution call stack:

| Variable      | Description                                                     |
|---------------|-----------------------------------------------------------------|
| `FUNCNAME`    | Array of function names in call stack                           |
| `BASH_SOURCE` | Array of source filenames for each function                     |
| `BASH_LINENO` | Array of line numbers where each function was called            |
| `BASH_ARGC`   | Array of parameter counts per stack frame (requires `extdebug`) |
| `BASH_ARGV`   | Array of all parameters in call stack (requires `extdebug`)     |

**Usage pattern**: `${FUNCNAME[$i]}` was called from file `${BASH_SOURCE[$i+1]}` at line `${BASH_LINENO[$i]}`.

## Quick Reference: Locale Variables

| Variable      | Controls                                         |
|---------------|--------------------------------------------------|
| `LANG`        | Default locale for unspecified categories        |
| `LC_ALL`      | Overrides `LANG` and all other `LC_*` variables  |
| `LC_COLLATE`  | Collation order for sorting and pattern matching |
| `LC_CTYPE`    | Character interpretation and character classes   |
| `LC_MESSAGES` | Locale for `$"..."` string translation           |
| `LC_NUMERIC`  | Number formatting                                |
| `LC_TIME`     | Date and time formatting                         |

## Quick Reference: Prompt Variables

| Variable         | Default    | Description                                            |
|------------------|------------|--------------------------------------------------------|
| `PS0`            | (none)     | Displayed after reading command, before execution      |
| `PS1`            | `\s-\v\$ ` | Primary prompt                                         |
| `PS2`            | `> `       | Secondary/continuation prompt                          |
| `PS3`            | `#? `      | Prompt for `select` command                            |
| `PS4`            | `+ `       | Debug trace prompt (first char replicated for nesting) |
| `PROMPT_COMMAND` | (none)     | Command(s) executed before `PS1` is displayed          |
| `PROMPT_DIRTRIM` | (none)     | Number of trailing directory components in `\w`/`\W`   |

## Bash 5.3 New Variables

These variables are new additions in Bash 5.3:

| Variable           | Description                                          |
|--------------------|------------------------------------------------------|
| `BASH_MONOSECONDS` | Monotonic clock value (falls back to `EPOCHSECONDS`) |
| `BASH_TRAPSIG`     | Signal number of currently executing trap            |
| `GLOBSORT`         | Controls filename expansion sort order and criteria  |
