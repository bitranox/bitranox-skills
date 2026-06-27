# Bash 5.3 Shell Builtin Commands Reference

Builtin commands are contained within the shell itself. When the name of a builtin command is used as the first word of a simple command, the shell executes the command directly, without invoking another program. Builtin commands are necessary to implement functionality impossible or inconvenient to obtain with separate utilities.

**Option conventions:** Unless otherwise noted, each builtin accepting options preceded by `-` accepts `--` to signify the end of the options. The `:`, `true`, `false`, and `test`/`[` builtins do not accept options and do not treat `--` specially. The `exit`, `logout`, `return`, `break`, `continue`, `let`, and `shift` builtins accept and process arguments beginning with `-` without requiring `--`.

---

## 4.1 Bourne Shell Builtins

These commands are inherited from the Bourne Shell and implemented as specified by the POSIX standard.

---

### `: (colon)`

```bash
: [ARGUMENTS]
```

Do nothing beyond expanding ARGUMENTS and performing redirections. The return status is zero.

**Use cases:**
- Infinite loops: `while :; do ...; done`
- No-op placeholder in conditionals: `if condition; then :; fi`
- Variable expansion side effects: `: ${VAR:=default}`

---

### `. (dot)` / `source`

```bash
. [-p PATH] FILENAME [ARGUMENTS]
source [-p PATH] FILENAME [ARGUMENTS]
```

Read and execute commands from FILENAME in the current shell context.

| Option    | Description                                                                   |
|-----------|-------------------------------------------------------------------------------|
| `-p PATH` | Treat PATH as a colon-separated list of directories in which to find FILENAME |

**Behavior details:**
- If FILENAME does not contain a slash, `.` searches for it using `$PATH`.
- When not in POSIX mode, Bash searches the current directory if FILENAME is not found in `$PATH`, but does not search the current directory if `-p` is supplied.
- If the `sourcepath` shopt option is turned off, `.` does not search `PATH`.
- If ARGUMENTS are supplied, they become the positional parameters when FILENAME is executed. Otherwise positional parameters are unchanged.
- If the `-T` option is enabled, `.` inherits any trap on `DEBUG`; if not, any `DEBUG` trap string is saved and restored around the call, and `.` unsets the `DEBUG` trap while it executes. If `-T` is not set and the sourced file changes the `DEBUG` trap, the new value persists after `.` completes.
- **Return status:** Exit status of the last command executed from FILENAME, or zero if no commands are executed. Non-zero if FILENAME is not found or cannot be read.

---

### `break`

```bash
break [N]
```

Exit from a `for`, `while`, `until`, or `select` loop. If N is supplied, `break` exits the Nth enclosing loop. N must be >= 1.

**Return status:** Zero unless N is not >= 1.

---

### `cd`

```bash
cd [-L] [-@] [DIRECTORY]
cd -P [-e] [-@] [DIRECTORY]
```

Change the current working directory to DIRECTORY.

| Option | Description                                                                                                                 |
|--------|-----------------------------------------------------------------------------------------------------------------------------|
| `-L`   | (Default) Symbolic links in DIRECTORY are resolved after `cd` processes `..`                                                |
| `-P`   | Do not follow symbolic links; resolve them while traversing DIRECTORY and before processing `..`                            |
| `-e`   | With `-P`: return non-zero status if the current working directory cannot be determined after a successful directory change |
| `-@`   | On systems that support it, present extended attributes associated with a file as a directory                               |

**Behavior details:**
- If DIRECTORY is not supplied, the value of `$HOME` is used.
- If `$CDPATH` exists and DIRECTORY does not begin with a slash, `cd` searches each directory name in `CDPATH` (colon-separated). A null directory name in `CDPATH` means the current directory.
- If DIRECTORY is `-`, it is converted to `$OLDPWD`.
- If `cd` uses a non-empty directory name from `CDPATH`, or if `-` is the first argument, and the change is successful, `cd` writes the absolute pathname of the new working directory to stdout.
- On success, `cd` sets `PWD` to the new directory name and `OLDPWD` to the previous working directory.
- If `..` appears in DIRECTORY, `cd` processes it by removing the immediately preceding pathname component and verifying the resulting path is still a valid directory name.
- **Return status:** Zero if successfully changed, non-zero otherwise.

---

### `continue`

```bash
continue [N]
```

Resume the next iteration of an enclosing `for`, `while`, `until`, or `select` loop. If N is supplied, resume execution of the Nth enclosing loop. N must be >= 1.

**Return status:** Zero unless N is not >= 1.

---

### `eval`

```bash
eval [ARGUMENTS]
```

The ARGUMENTS are concatenated together into a single command, separated by spaces. Bash reads and executes this command and returns its exit status as the exit status of `eval`. If there are no arguments or only empty arguments, the return status is zero.

---

### `exec`

```bash
exec [-cl] [-a NAME] [COMMAND [ARGUMENTS]]
```

If COMMAND is supplied, it replaces the shell without creating a new process. COMMAND cannot be a shell builtin or function.

| Option    | Description                                                                                |
|-----------|--------------------------------------------------------------------------------------------|
| `-l`      | Place a dash at the beginning of the zeroth argument passed to COMMAND (like `login` does) |
| `-c`      | Execute COMMAND with an empty environment                                                  |
| `-a NAME` | Pass NAME as the zeroth argument to COMMAND                                                |

**Behavior details:**
- If COMMAND cannot be executed, a non-interactive shell exits unless the `execfail` shell option is enabled (in which case it returns non-zero). An interactive shell returns non-zero. A subshell exits unconditionally if `exec` fails.
- If COMMAND is not specified, redirections may be used to affect the current shell environment. Return status is zero if there are no redirection errors.

---

### `exit`

```bash
exit [N]
```

Exit the shell, returning a status of N to the shell's parent. If N is omitted, the exit status is that of the last command executed. Any trap on `EXIT` is executed before the shell terminates.

---

### `export`

```bash
export [-fn] [-p] [NAME[=VALUE]]
```

Mark each NAME to be passed to subsequently executed commands in the environment.

| Option | Description                                                                                         |
|--------|-----------------------------------------------------------------------------------------------------|
| `-f`   | NAMEs refer to shell functions (not variables)                                                      |
| `-n`   | Unexport each name; no longer mark it for export                                                    |
| `-p`   | Display a list of all exported variables in a reusable form. With `-f`, displays exported functions |

**Behavior details:**
- Allows setting a variable's value at the same time it is exported or unexported by following the name with `=VALUE`.
- If no NAMEs are supplied or only `-p` is given, displays a list of all exported variables.
- **Return status:** Zero unless an invalid option is supplied, one of the names is not a valid shell variable name, or `-f` is supplied with a name that is not a shell function.

---

### `false`

```bash
false
```

Does nothing; returns a non-zero (1) status.

---

### `getopts`

```bash
getopts OPTSTRING NAME [ARG ...]
```

Parse positional parameters to obtain options and their arguments.

**OPTSTRING:** Contains the option characters to be recognized. If a character is followed by a colon, the option expects an argument (separated by whitespace). The colon (`:`) and question mark (`?`) may not be used as option characters.

**Behavior details:**
- Each invocation places the next option in variable NAME and the next argument index in `OPTIND` (initialized to 1 on shell/script invocation).
- When an option requires an argument, `getopts` places it in `OPTARG`.
- `OPTIND` must be manually reset between multiple calls to parse a new set of parameters.
- At end of options: returns > 0, sets `OPTIND` to the first non-option argument index, sets NAME to `?`.
- If more arguments are supplied as ARG, `getopts` parses those instead of positional parameters.

**Error reporting modes:**

| Mode                                            | Invalid option                                         | Missing argument                                       |
|-------------------------------------------------|--------------------------------------------------------|--------------------------------------------------------|
| **Normal** (first char of OPTSTRING is not `:`) | NAME=`?`, prints error, unsets `OPTARG`                | NAME=`?`, prints error, unsets `OPTARG`                |
| **Silent** (first char of OPTSTRING is `:`)     | NAME=`?`, `OPTARG`=option char found, no error printed | NAME=`:`, `OPTARG`=option char found, no error printed |

- Setting `OPTERR` to 0 suppresses error messages even in normal mode.
- **Return status:** True (0) if an option is found. False when end of options is reached or an error occurs.

---

### `hash`

```bash
hash [-r] [-p FILENAME] [-dt] [NAME]
```

Remember the full filenames of commands so they need not be searched for on subsequent invocations.

| Option        | Description                                                                                        |
|---------------|----------------------------------------------------------------------------------------------------|
| `-r`          | Forget all remembered locations. Assigning to `PATH` also clears the hash table                    |
| `-p FILENAME` | Inhibit path search; use FILENAME as the location of NAME                                          |
| `-d`          | Forget the remembered location of each NAME                                                        |
| `-t`          | Print the full pathname for each NAME. With multiple NAMEs, print each NAME before its hashed path |
| `-l`          | Display output in a reusable format                                                                |

- With no arguments or only `-l`, prints information about remembered commands.
- `-t`, `-d`, and `-p` are mutually exclusive. Priority: `-t` > `-p` > `-d`.
- **Return status:** Zero unless a NAME is not found or an invalid option is supplied.

---

### `pwd`

```bash
pwd [-LP]
```

Print the absolute pathname of the current working directory.

| Option | Description                                              |
|--------|----------------------------------------------------------|
| `-L`   | Pathname may contain symbolic links (default)            |
| `-P`   | Pathname will not contain symbolic links (resolves them) |

**Return status:** Zero unless an error is encountered or an invalid option is supplied.

---

### `readonly`

```bash
readonly [-aAf] [-p] [NAME[=VALUE]] ...
```

Mark each NAME as readonly. Values may not be changed by subsequent assignment or `unset`.

| Option | Description                                                                    |
|--------|--------------------------------------------------------------------------------|
| `-f`   | Each NAME refers to a shell function                                           |
| `-a`   | Each NAME refers to an indexed array variable                                  |
| `-A`   | Each NAME refers to an associative array variable (takes precedence over `-a`) |
| `-p`   | Display all readonly names in a reusable format                                |

- Allows setting a variable's value at the same time as making it readonly by following the name with `=VALUE`.
- With no NAME arguments or with `-p`, prints a list of all readonly names. Other options may restrict output.
- **Return status:** Zero unless an invalid option is supplied, one of the NAMEs is not a valid shell variable or function name, or `-f` is supplied with a name that is not a shell function.

---

### `return`

```bash
return [N]
```

Stop executing a shell function or sourced file and return the value N to its caller.

**Behavior details:**
- If N is not supplied, the return value is the exit status of the last command executed.
- If `return` is executed by a trap handler, the last command used to determine the status is the last command executed before the trap handler.
- If `return` is executed during a `DEBUG` trap, the last command used is the last command executed by the trap handler before `return` was invoked.
- When used to terminate a script being executed with `.`/`source`, returns N or the exit status of the last command in the script.
- If N is supplied, the return value is its least significant 8 bits.
- Any command associated with the `RETURN` trap is executed before execution resumes after the function or script.
- **Return status:** Non-zero if a non-numeric argument is supplied or if used outside a function and not during `.`/`source` execution.

---

### `shift`

```bash
shift [N]
```

Shift the positional parameters to the left by N. Parameters from N+1 ... `$#` are renamed to `$1` ... `$#`-N. Parameters `$#` down to `$#`-N+1 are unset.

- N must be a non-negative number <= `$#`. If N is not supplied, it defaults to 1.
- If N is zero or greater than `$#`, positional parameters are not changed.
- **Return status:** Zero unless N > `$#` or N < 0.

---

### `test` / `[`

```bash
test EXPR
[ EXPR ]
```

Evaluate a conditional expression EXPR and return 0 (true) or 1 (false). Each operator and operand must be a separate argument. `test` does not accept options and does not treat `--` specially. When using `[`, the last argument must be `]`.

**Operators (decreasing precedence):**

| Operator         | Description                                          |
|------------------|------------------------------------------------------|
| `! EXPR`         | True if EXPR is false                                |
| `( EXPR )`       | Returns value of EXPR; overrides normal precedence   |
| `EXPR1 -a EXPR2` | True if both EXPR1 and EXPR2 are true *(deprecated)* |
| `EXPR1 -o EXPR2` | True if either EXPR1 or EXPR2 is true *(deprecated)* |

**Argument-count-based evaluation rules:**

| Arguments | Behavior                                                                                                                                                                                              |
|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0         | Expression is false                                                                                                                                                                                   |
| 1         | True if and only if the argument is not null                                                                                                                                                          |
| 2         | If first is `!`, true iff second is null. If first is a unary operator, result of unary test. Otherwise false                                                                                         |
| 3         | (1) If second is a binary operator, result of binary test. (2) If first is `!`, negation of two-argument test. (3) If first is `(` and third is `)`, one-argument test of second. (4) Otherwise false |
| 4         | (1) If first is `!`, negation of three-argument expression. (2) If first is `(` and fourth is `)`, two-argument test. (3) Otherwise parsed by precedence                                              |
| 5+        | Parsed and evaluated by precedence                                                                                                                                                                    |

**Notes:**
- In POSIX mode or within `[[`, `<` and `>` sort using the current locale. Otherwise they sort lexicographically using ASCII ordering.
- POSIX has deprecated `-a`, `-o`, and parenthesized expressions. Use `&&` and `||` list operators instead.

---

### `times`

```bash
times
```

Print the user and system times used by the shell and its children. Return status is zero.

---

### `trap`

```bash
trap [-lpP] [ACTION] [SIGSPEC ...]
```

The ACTION is a command executed when the shell receives any of the signals SIGSPEC.

| Option | Description                                                                                                                                   |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `-l`   | Print a list of signal names and their corresponding numbers                                                                                  |
| `-p`   | Display trap commands associated with each SIGSPEC (or all trapped signals if no SIGSPEC). May be used in subshells to display parent's traps |
| `-P`   | Display only the actions associated with each SIGSPEC argument (requires at least one SIGSPEC). May be used in subshells                      |

**Action handling:**
- If ACTION is absent (with a single SIGSPEC) or `-`, each SIGSPEC's disposition is reset to its value when the shell was started.
- If ACTION is the null string `''`, the signal specified by each SIGSPEC is ignored by the shell and commands it invokes.
- With no arguments, `trap` prints the actions associated with each trapped signal as reusable `trap` commands.

**Special SIGSPEC values:**

| SIGSPEC       | When ACTION is executed                                                                                                              |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `0` or `EXIT` | When the shell exits                                                                                                                 |
| `DEBUG`       | Before every simple command, `for`, `case`, `select`, `((`, `[[`, arithmetic `for`, and before the first command in a shell function |
| `RETURN`      | Each time a shell function or a script executed with `.`/`source` finishes                                                           |
| `ERR`         | When a pipeline, list, or compound command returns a non-zero exit status (subject to the same conditions as `errexit`/`-e`)         |

**Signal inheritance:**
- Non-interactive shells cannot trap or reset signals ignored upon entry.
- Interactive shells permit trapping signals ignored on entry.
- Trapped signals not being ignored are reset to their original values in a subshell or subshell environment.

**Return status:** Zero unless a SIGSPEC does not specify a valid signal.

---

### `true`

```bash
true
```

Does nothing; returns a 0 status.

---

### `umask`

```bash
umask [-p] [-S] [MODE]
```

Set the shell process's file creation mask to MODE.

| Option | Description                                                       |
|--------|-------------------------------------------------------------------|
| `-S`   | Print the mask in symbolic format (without MODE argument)         |
| `-p`   | Print output in a form that may be reused as input (without MODE) |

**Behavior details:**
- If MODE begins with a digit, it is interpreted as an octal number; otherwise as a symbolic mode mask (like `chmod`).
- If MODE is omitted, prints the current value (default octal).
- When the mode is interpreted as octal, each number of the umask is subtracted from 7. A umask of `022` results in permissions of `755`.
- **Return status:** Zero if the mode is successfully changed or if no MODE is supplied.

---

### `unset`

```bash
unset [-fnv] [NAME]
```

Remove each variable or function NAME.

| Option | Description                                                                                                                       |
|--------|-----------------------------------------------------------------------------------------------------------------------------------|
| `-v`   | Each NAME refers to a shell variable (default if no options supplied)                                                             |
| `-f`   | NAMEs refer to shell functions; function definitions are removed                                                                  |
| `-n`   | If NAME has the `nameref` attribute, unset NAME itself rather than the variable it references. No effect if `-f` is also supplied |

**Behavior details:**
- If no options are supplied, each NAME refers to a variable; if no such variable exists, a function with that name (if any) is unset.
- Readonly variables and functions may not be unset.
- Removed variables/functions are also removed from the environment passed to subsequent commands.
- Some shell variables may not be unset; some lose their special behavior when unset.
- **Return status:** Zero unless a NAME is readonly or may not be unset.

---

## 4.2 Bash Builtin Commands

These builtins are unique to or have been extended in Bash.

> **Note:** Directory stack builtins (`pushd`, `popd`, `dirs`) are documented in `bash-features.md` section 6.8.

---

### `alias`

```bash
alias [-p] [NAME[=VALUE] ...]
```

Define or display aliases.

| Option | Description                                    |
|--------|------------------------------------------------|
| `-p`   | Print the list of aliases in a reusable format |

**Behavior details:**
- Without arguments or with `-p`, prints all aliases.
- If arguments are supplied, define an alias for each NAME whose VALUE is given.
- If no VALUE is given for a NAME, print the name and value of that alias.
- A trailing space in VALUE causes the next word to be checked for alias substitution.
- **Return status:** True unless a NAME is given (without `=VALUE`) for which no alias has been defined.

---

### `bind`

```bash
bind [-m KEYMAP] [-lsvSVX]
bind [-m KEYMAP] [-q FUNCTION] [-u FUNCTION] [-r KEYSEQ]
bind [-m KEYMAP] -f FILENAME
bind [-m KEYMAP] -x KEYSEQ[: ]SHELL-COMMAND
bind [-m KEYMAP] KEYSEQ:FUNCTION-NAME
bind [-m KEYMAP] KEYSEQ:READLINE-COMMAND
bind [-m KEYMAP] -p|-P [READLINE-COMMAND]
bind READLINE-COMMAND-LINE
```

Display or modify Readline key bindings, bind key sequences to functions/macros/shell commands, or set Readline variables.

| Option                    | Description                                                                                                                                        |
|---------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `-m KEYMAP`               | Use KEYMAP for subsequent bindings. Valid names: `emacs`, `emacs-standard`, `emacs-meta`, `emacs-ctlx`, `vi`, `vi-move`, `vi-command`, `vi-insert` |
| `-l`                      | List the names of all Readline functions                                                                                                           |
| `-p`                      | Display Readline function names and bindings in reusable format. Arguments after options restrict output to those command names                    |
| `-P`                      | List current Readline function names and bindings. Arguments after options restrict output to those command names                                  |
| `-s`                      | Display key sequences bound to macros and their output strings (reusable format)                                                                   |
| `-S`                      | Display key sequences bound to macros and their output strings                                                                                     |
| `-v`                      | Display Readline variable names and values (reusable format)                                                                                       |
| `-V`                      | List current Readline variable names and values                                                                                                    |
| `-f FILENAME`             | Read key bindings from FILENAME                                                                                                                    |
| `-q FUNCTION`             | Display key sequences that invoke the named Readline FUNCTION                                                                                      |
| `-u FUNCTION`             | Unbind all key sequences bound to the named Readline FUNCTION                                                                                      |
| `-r KEYSEQ`               | Remove any current binding for KEYSEQ                                                                                                              |
| `-x KEYSEQ:SHELL-COMMAND` | Execute SHELL-COMMAND whenever KEYSEQ is entered (see below)                                                                                       |
| `-X`                      | List all key sequences bound to shell commands in reusable format                                                                                  |

**`-x` option details:**
- The separator between KEYSEQ and SHELL-COMMAND is either whitespace or a colon optionally followed by whitespace.
- If the separator is whitespace, SHELL-COMMAND must be enclosed in double quotes and Readline expands backslash-escapes before saving.
- If the separator is a colon, enclosing double quotes are optional and Readline does not expand the command string.
- The entire key binding expression should be enclosed in single quotes.
- When SHELL-COMMAND is executed, the shell sets: `READLINE_LINE` (line buffer contents), `READLINE_POINT` (insertion point), `READLINE_MARK` (saved insertion point), and `READLINE_ARGUMENT` (numeric argument, if supplied).
- If the command changes `READLINE_LINE`, `READLINE_POINT`, or `READLINE_MARK`, new values are reflected in the editing state.

**Return status:** Zero unless an invalid option is supplied or an error occurs.

---

### `builtin`

```bash
builtin [SHELL-BUILTIN [ARGS]]
```

Execute the specified shell builtin, passing it ARGS, and return its exit status. Useful when defining a shell function with the same name as a builtin, to retain the builtin's functionality within the function.

**Return status:** Non-zero if SHELL-BUILTIN is not a shell builtin command.

---

### `caller`

```bash
caller [EXPR]
```

Return the context of any active subroutine call (a shell function or a script executed with `.`/`source`).

- Without EXPR: displays the line number and source filename of the current subroutine call.
- With a non-negative integer EXPR: displays the line number, subroutine name, and source file corresponding to that position in the current execution call stack. The current frame is frame 0.
- **Return status:** 0 unless the shell is not executing a subroutine call or EXPR does not correspond to a valid position.

---

### `command`

```bash
command [-pVv] COMMAND [ARGUMENTS ...]
```

Run COMMAND with ARGUMENTS ignoring any shell function named COMMAND. Only shell builtins or commands found by searching `PATH` are executed.

| Option | Description                                                                      |
|--------|----------------------------------------------------------------------------------|
| `-p`   | Use a default value for `PATH` guaranteed to find all standard utilities         |
| `-v`   | Display a single word indicating the command or file name used to invoke COMMAND |
| `-V`   | Produce a more verbose description of COMMAND                                    |

- With `-v` or `-V`, return status is zero if COMMAND is found, non-zero if not.
- With `-p`, return status is 127 if COMMAND cannot be found or an error occurred, otherwise the exit status of COMMAND.

---

### `declare`

```bash
declare [-aAfFgiIlnrtux] [-p] [NAME[=VALUE] ...]
```

Declare variables and give them attributes. If no NAMEs are given, display variable values or shell functions.

**Display options:**

| Option | Description                                                                                                                                                    |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-p`   | Display attributes and values of each NAME. Without NAMEs, display all variables with specified attributes. Without other options, display all shell variables |
| `-f`   | Restrict display to shell functions                                                                                                                            |
| `-F`   | Display only function name and attributes (not definitions). If `extdebug` is enabled, also shows source file name and line number. Implies `-f`               |

**Scope options:**

| Option | Description                                                                                                                                 |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `-g`   | Force variables to be created/modified at global scope (even inside functions). Ignored when not in a function                              |
| `-I`   | Cause local variables to inherit attributes (except `nameref`) and value of any existing variable with the same NAME at a surrounding scope |

**Attribute options:**

| Option | Description                                                                                                            |
|--------|------------------------------------------------------------------------------------------------------------------------|
| `-a`   | Each NAME is an indexed array variable                                                                                 |
| `-A`   | Each NAME is an associative array variable                                                                             |
| `-f`   | Each NAME refers to a shell function                                                                                   |
| `-i`   | Treat variable as integer; arithmetic evaluation is performed on assignment                                            |
| `-l`   | Convert all upper-case characters to lower-case on assignment (disables upper-case attribute)                          |
| `-n`   | Give NAME the `nameref` attribute (name reference to another variable). Cannot be applied to arrays                    |
| `-r`   | Make NAMEs readonly (cannot be assigned or unset)                                                                      |
| `-t`   | Give NAME the `trace` attribute. Traced functions inherit `DEBUG` and `RETURN` traps. No special meaning for variables |
| `-u`   | Convert all lower-case characters to upper-case on assignment (disables lower-case attribute)                          |
| `-x`   | Mark NAME for export to subsequent commands via the environment                                                        |

**Behavior details:**
- Using `+` instead of `-` turns off the specified attribute, except: `+a` and `+A` may not destroy array variables, and `+r` will not remove the readonly attribute.
- When used in a function, `declare` makes each NAME local (like `local`), unless `-g` is supplied.
- When using `-a` or `-A` with compound assignment syntax to create arrays, additional attributes do not take effect until subsequent assignments.
- **Return status:** Zero unless an invalid option is encountered, an attempt is made to define a function using `-f foo=bar`, assign to a readonly variable, assign to an array without compound syntax, a NAME is not a valid variable name, an attempt to turn off readonly or array status, or displaying a non-existent function with `-f`.

---

### `echo`

```bash
echo [-neE] [ARG ...]
```

Output the ARGs, separated by spaces, terminated with a newline.

| Option | Description                                                                                |
|--------|--------------------------------------------------------------------------------------------|
| `-n`   | Do not print the trailing newline                                                          |
| `-e`   | Interpret backslash-escaped characters                                                     |
| `-E`   | Disable interpretation of escape characters (even if they would be interpreted by default) |

`echo` does not interpret `--` to mean the end of options. The `xpg_echo` shell option determines whether `echo` interprets any options and expands escape characters.

**Escape sequences (with `-e`):**

| Escape       | Description                                                    |
|--------------|----------------------------------------------------------------|
| `\a`         | Alert (bell)                                                   |
| `\b`         | Backspace                                                      |
| `\c`         | Suppress further output                                        |
| `\e`, `\E`   | Escape                                                         |
| `\f`         | Form feed                                                      |
| `\n`         | New line                                                       |
| `\r`         | Carriage return                                                |
| `\t`         | Horizontal tab                                                 |
| `\v`         | Vertical tab                                                   |
| `\\`         | Backslash                                                      |
| `\0NNN`      | Eight-bit character with octal value NNN (0-3 octal digits)    |
| `\xHH`       | Eight-bit character with hexadecimal value HH (1-2 hex digits) |
| `\uHHHH`     | Unicode character with hex value HHHH (1-4 hex digits)         |
| `\UHHHHHHHH` | Unicode character with hex value HHHHHHHH (1-8 hex digits)     |

Unrecognized backslash-escaped characters are written unchanged.

**Return status:** 0 unless a write error occurs.

---

### `enable`

```bash
enable [-a] [-dnps] [-f FILENAME] [NAME ...]
```

Enable and disable builtin shell commands. Disabling a builtin allows an executable with the same name to be executed without a full pathname.

| Option        | Description                                                                                                               |
|---------------|---------------------------------------------------------------------------------------------------------------------------|
| `-n`          | Disable the named builtins                                                                                                |
| `-p`          | Print a list of shell builtins (with no NAMEs: all enabled builtins)                                                      |
| `-a`          | List each builtin with an indication of whether it is enabled                                                             |
| `-s`          | Restrict to POSIX special builtins                                                                                        |
| `-f FILENAME` | Load new builtin NAME from shared object FILENAME (dynamic loading). If FILENAME has no slash, uses `BASH_LOADABLES_PATH` |
| `-d`          | Delete a builtin loaded with `-f`                                                                                         |

**Behavior details:**
- If `-s` is used with `-f`, the new builtin becomes a POSIX special builtin.
- If no options are supplied and NAME is not a shell builtin, `enable` attempts to load NAME from a shared object named NAME (as if `enable -f NAME NAME`).
- The `BASH_LOADABLES_PATH` variable is a colon-separated list of directories for searching; the default is system-dependent and may include `.`.
- **Return status:** Zero unless a NAME is not a shell builtin or there is an error loading from a shared object.

---

### `help`

```bash
help [-dms] [PATTERN]
```

Display helpful information about builtin commands.

| Option | Description                                          |
|--------|------------------------------------------------------|
| `-d`   | Display a short description of each PATTERN          |
| `-m`   | Display the description in a manpage-like format     |
| `-s`   | Display only a short usage synopsis for each PATTERN |

- If PATTERN contains pattern matching characters, it's treated as a shell pattern.
- If PATTERN exactly matches a help topic name, prints that topic's description.
- Otherwise, performs prefix matching and prints descriptions of all matching topics.
- **Return status:** Zero unless no command matches PATTERN.

---

### `let`

```bash
let EXPRESSION [EXPRESSION ...]
```

Perform arithmetic on shell variables. Each EXPRESSION is evaluated as an arithmetic expression according to Shell Arithmetic rules.

**Return status:** If the last EXPRESSION evaluates to 0, `let` returns 1; otherwise returns 0.

---

### `local`

```bash
local [OPTION] NAME[=VALUE] ...
```

Create a local variable named NAME within a function, with a visible scope restricted to that function and its children. The OPTION can be any of the options accepted by `declare`.

**Behavior details:**
- Can only be used within a function; it is an error to use `local` outside a function.
- If NAME is `-`, the set of shell options becomes local to the function: shell options changed using `set` inside the function after the call to `local` are restored to their original values when the function returns.
- With no operands, `local` writes a list of local variables to stdout.
- **Return status:** Zero unless `local` is used outside a function, an invalid NAME is supplied, or NAME is a readonly variable.

---

### `logout`

```bash
logout [N]
```

Exit a login shell, returning a status of N to the shell's parent.

---

### `mapfile`

```bash
mapfile [-d DELIM] [-n COUNT] [-O ORIGIN] [-s COUNT]
    [-t] [-u FD] [-C CALLBACK] [-c QUANTUM] [ARRAY]
```

Read lines from standard input (or file descriptor FD with `-u`) into the indexed array variable ARRAY. Default ARRAY is `MAPFILE`.

| Option        | Description                                                                                                     |
|---------------|-----------------------------------------------------------------------------------------------------------------|
| `-d DELIM`    | Use the first character of DELIM to terminate each input line instead of newline. Empty DELIM terminates on NUL |
| `-n COUNT`    | Copy at most COUNT lines. If COUNT is 0, copy all lines                                                         |
| `-O ORIGIN`   | Begin assigning to ARRAY at index ORIGIN (default 0)                                                            |
| `-s COUNT`    | Discard the first COUNT lines read                                                                              |
| `-t`          | Remove a trailing DELIM (default newline) from each line read                                                   |
| `-u FD`       | Read lines from file descriptor FD instead of stdin                                                             |
| `-C CALLBACK` | Evaluate CALLBACK each time QUANTUM lines are read                                                              |
| `-c QUANTUM`  | Specify the number of lines read between each call to CALLBACK (default 5000 if `-C` is specified without `-c`) |

**Behavior details:**
- CALLBACK is supplied the index of the next array element to be assigned and the line to be assigned as additional arguments.
- CALLBACK is evaluated after the line is read but before the array element is assigned.
- If not supplied with an explicit origin, `mapfile` clears ARRAY before assigning.
- **Return status:** Zero unless an invalid option/argument is supplied, ARRAY is invalid or unassignable, or ARRAY is not an indexed array.

---

### `printf`

```bash
printf [-v VAR] FORMAT [ARGUMENTS]
```

Write formatted ARGUMENTS to stdout under the control of FORMAT.

| Option   | Description                                                     |
|----------|-----------------------------------------------------------------|
| `-v VAR` | Assign the output to variable VAR instead of printing to stdout |

**FORMAT contains:**
- Plain characters (copied to output as-is)
- Character escape sequences (converted and copied)
- Format specifications (each causes printing of the next successive ARGUMENT)

**Standard format characters:** `c C s S n d i o u x X e E f F g G a A`

**Additional format specifiers:**

| Specifier     | Description                                                                                                                                                                                     |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `%b`          | Expand backslash escape sequences in ARGUMENT (same as `echo -e`)                                                                                                                               |
| `%q`          | Output ARGUMENT in a format reusable as shell input. Uses ANSI-C quoting style if needed, backslash quoting otherwise. Alternate form (`%#q`) uses single quotes                                |
| `%Q`          | Like `%q`, but applies any supplied precision to ARGUMENT before quoting                                                                                                                        |
| `%(DATEFMT)T` | Output date-time string using DATEFMT as `strftime(3)` format. ARGUMENT is seconds since epoch. Special values: `-1` = current time, `-2` = shell invocation time. No argument defaults to `-1` |

**Format modifier notes:**
- `%b`, `%q`, and `%T` use field width and precision from the format specification.
- `%n` accepts a corresponding argument treated as a shell variable name.
- `%s` and `%c` accept an `l` (long) modifier for wide-character string conversion; `%S` and `%C` are equivalent to `%ls` and `%lc`.
- Non-string format specifier arguments are treated as C language constants. A leading single or double quote means the value is the numeric value of the following character (using current locale).
- FORMAT is reused as necessary to consume all ARGUMENTS. Missing arguments default to zero or null string.
- **Return status:** Zero on success, non-zero on invalid option or write/assignment error.

---

### `read`

```bash
read [-Eers] [-a ANAME] [-d DELIM] [-i TEXT] [-n NCHARS]
    [-N NCHARS] [-p PROMPT] [-t TIMEOUT] [-u FD] [NAME ...]
```

Read one line from stdin (or file descriptor FD), split it into words, and assign them to NAMEs.

| Option       | Description                                                                                                                                                                                                                              |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-a ANAME`   | Assign words to sequential indices of array ANAME (starting at 0). All elements are removed first. Other NAMEs are ignored                                                                                                               |
| `-d DELIM`   | First character of DELIM terminates input instead of newline. Empty DELIM terminates on NUL                                                                                                                                              |
| `-e`         | Use Readline to obtain the line (from terminal). Uses Readline's default filename completion                                                                                                                                             |
| `-E`         | Use Readline to obtain the line (from terminal). Uses Bash's default completion including programmable completion                                                                                                                        |
| `-i TEXT`    | Place TEXT into the editing buffer before editing begins (requires Readline)                                                                                                                                                             |
| `-n NCHARS`  | Return after reading NCHARS characters (honors delimiter if fewer than NCHARS characters read before it)                                                                                                                                 |
| `-N NCHARS`  | Return after reading exactly NCHARS characters. Delimiter characters are not treated specially. Result is not split on IFS                                                                                                               |
| `-p PROMPT`  | Display PROMPT (without trailing newline) before reading; only if input is from a terminal                                                                                                                                               |
| `-r`         | Do not use backslash as an escape character; backslash is part of the line. Disables line continuation                                                                                                                                   |
| `-s`         | Silent mode; characters are not echoed (from terminal)                                                                                                                                                                                   |
| `-t TIMEOUT` | Time out and return failure if a complete line is not read within TIMEOUT seconds (may be decimal). Only effective for terminal, pipe, or special file input. If TIMEOUT is 0, returns immediately (exit status 0 if input is available) |
| `-u FD`      | Read from file descriptor FD instead of stdin                                                                                                                                                                                            |

**Behavior details:**
- Words are split using `IFS` (same rules as shell expansion). Backslash removes special meaning for next character and is used for line continuation.
- More words than names: remaining words and delimiters assigned to last NAME.
- Fewer words: remaining names assigned empty values.
- Other than empty DELIM, `read` ignores NUL characters in input.
- If no NAMEs are supplied, the line (without ending delimiter, otherwise unmodified) is assigned to `REPLY`.
- **Return status:** Zero unless EOF is encountered, `read` times out (status > 128), a variable assignment error occurs, or an invalid file descriptor is supplied to `-u`.

---

### `readarray`

```bash
readarray [-d DELIM] [-n COUNT] [-O ORIGIN] [-s COUNT]
    [-t] [-u FD] [-C CALLBACK] [-c QUANTUM] [ARRAY]
```

A synonym for `mapfile`. Read lines from stdin into indexed array variable ARRAY (or from FD with `-u`).

---

### `source`

```bash
source [-p PATH] FILENAME [ARGUMENTS]
```

A synonym for `.` (dot). See Bourne Shell Builtins.

---

### `type`

```bash
type [-afptP] [NAME ...]
```

Indicate how each NAME would be interpreted if used as a command name.

| Option | Description                                                                                                                                           |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-t`   | Print a single word: `alias`, `keyword`, `function`, `builtin`, or `file`. Prints nothing and returns failure if NAME not found                       |
| `-p`   | Return the name of the executable file found by searching `$PATH`, or nothing if `-t` would not return `file`                                         |
| `-P`   | Force a path search for each NAME, even if `-t` would not return `file`                                                                               |
| `-a`   | Return all places that contain a command named NAME (aliases, reserved words, functions, builtins, files). With `-p`, does not look in the hash table |
| `-f`   | Do not attempt to find shell functions (like the `command` builtin)                                                                                   |

**Notes:**
- If a NAME is in the hash table, `-p` and `-P` print the hashed value, which may not be the first file in `$PATH`.
- If `-a` is supplied with `-p`, `type` only performs a `PATH` search.
- **Return status:** Zero if all NAMEs are found, non-zero if any are not found.

---

### `typeset`

```bash
typeset [-afFgrxilnrtux] [-p] [NAME[=VALUE] ...]
```

A synonym for `declare` (supplied for Korn shell compatibility).

---

### `ulimit`

```bash
ulimit [-HS] -a
ulimit [-HS] [-bcdefiklmnpqrstuvxPRT] [LIMIT]
```

Control resources available to the shell and its child processes.

**General options:**

| Option | Description                                   |
|--------|-----------------------------------------------|
| `-S`   | Change and report the soft limit              |
| `-H`   | Change and report the hard limit              |
| `-a`   | Report all current limits (no limits are set) |

**Resource options:**

| Option | Resource                                                                    | Unit                                      |
|--------|-----------------------------------------------------------------------------|-------------------------------------------|
| `-b`   | Maximum socket buffer size                                                  | unscaled                                  |
| `-c`   | Maximum size of core files created                                          | 1024-byte blocks (512-byte in POSIX mode) |
| `-d`   | Maximum size of a process's data segment                                    | 1024-byte blocks                          |
| `-e`   | Maximum scheduling priority ("nice")                                        | unscaled                                  |
| `-f`   | Maximum size of files written by the shell and its children                 | 1024-byte blocks (512-byte in POSIX mode) |
| `-i`   | Maximum number of pending signals                                           | unscaled                                  |
| `-k`   | Maximum number of kqueues allocated                                         | unscaled                                  |
| `-l`   | Maximum size that may be locked into memory                                 | 1024-byte blocks                          |
| `-m`   | Maximum resident set size (many systems do not honor this)                  | 1024-byte blocks                          |
| `-n`   | Maximum number of open file descriptors (most systems do not allow setting) | unscaled                                  |
| `-p`   | Pipe buffer size                                                            | 512-byte blocks                           |
| `-q`   | Maximum number of bytes in POSIX message queues                             | 1024-byte blocks                          |
| `-r`   | Maximum real-time scheduling priority                                       | unscaled                                  |
| `-s`   | Maximum stack size                                                          | 1024-byte blocks                          |
| `-t`   | Maximum CPU time                                                            | seconds                                   |
| `-u`   | Maximum number of processes available to a single user                      | unscaled                                  |
| `-v`   | Maximum virtual memory available to the shell (and sometimes children)      | 1024-byte blocks                          |
| `-x`   | Maximum number of file locks                                                | 1024-byte blocks                          |
| `-P`   | Maximum number of pseudoterminals                                           | unscaled                                  |
| `-R`   | Maximum time a real-time process can run before blocking                    | microseconds                              |
| `-T`   | Maximum number of threads                                                   | unscaled                                  |

**LIMIT values:**
- `hard` -- the current hard limit
- `soft` -- the current soft limit
- `unlimited` -- no limit

**Behavior details:**
- A hard limit cannot be increased by a non-root user once set; a soft limit may be increased up to the hard limit.
- Without `-H` or `-S`, `ulimit` prints the current soft limit. When setting, both hard and soft limits are set unless one is specified.
- If no option is supplied, `-f` is assumed.
- When more than one resource is specified, the limit name and unit are printed before the value.
- **Return status:** Zero unless an invalid option or argument is supplied, or an error occurs while setting a new limit.

---

### `unalias`

```bash
unalias [-a] [NAME ...]
```

Remove each NAME from the list of aliases.

| Option | Description        |
|--------|--------------------|
| `-a`   | Remove all aliases |

**Return status:** True unless a supplied NAME is not a defined alias.

---

## 4.3 Modifying Shell Behavior

### 4.3.1 The `set` Builtin

`set` allows you to change shell option values, set positional parameters, or display the names and values of shell variables.

```bash
set [-abefhkmnptuvxBCEHPT] [-o OPTION-NAME] [--] [-] [ARGUMENT ...]
set [+abefhkmnptuvxBCEHPT] [+o OPTION-NAME] [--] [-] [ARGUMENT ...]
set -o
set +o
```

- With no options or arguments: display all shell variables and functions (sorted by locale) in a reusable format. In POSIX mode, only shell variables are listed.
- Using `+` rather than `-` turns options off.
- The current set of options may be found in `$-`.

#### Short Options

| Option | Name          | Description                                                                                                                                                                                                                                                                                                                                  |
|--------|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-a`   | `allexport`   | Each variable or function that is created or modified is given the export attribute and marked for export to the environment of subsequent commands                                                                                                                                                                                          |
| `-b`   | `notify`      | Report the status of terminated background jobs immediately, rather than before printing the next primary prompt. Effective only when job control is enabled                                                                                                                                                                                 |
| `-e`   | `errexit`     | Exit immediately if a pipeline, list, or compound command returns a non-zero status (see exceptions below)                                                                                                                                                                                                                                   |
| `-f`   | `noglob`      | Disable filename expansion (globbing)                                                                                                                                                                                                                                                                                                        |
| `-h`   | `hashall`     | Locate and remember (hash) commands as they are looked up for execution. Enabled by default                                                                                                                                                                                                                                                  |
| `-k`   | `keyword`     | All arguments in the form of assignment statements are placed in the environment for a command, not just those preceding the command name                                                                                                                                                                                                    |
| `-m`   | `monitor`     | Job control is enabled. All processes run in a separate process group. Background job completion prints exit status                                                                                                                                                                                                                          |
| `-n`   | `noexec`      | Read commands but do not execute them (syntax check). Ignored by interactive shells                                                                                                                                                                                                                                                          |
| `-o`   | --            | Set the option corresponding to OPTION-NAME (see table below)                                                                                                                                                                                                                                                                                |
| `-p`   | `privileged`  | Turn on privileged mode. `$BASH_ENV`, `$ENV` are not processed; shell functions not inherited; `SHELLOPTS`, `BASHOPTS`, `CDPATH`, `GLOBIGNORE` are ignored from environment. If effective user/group id differs from real, and `-p` is not supplied, effective uid is set to real uid. Turning off sets effective user/group ids to real ids |
| `-r`   | --            | Enable restricted shell mode. Cannot be unset once set                                                                                                                                                                                                                                                                                       |
| `-t`   | `onecmd`      | Exit after reading and executing one command                                                                                                                                                                                                                                                                                                 |
| `-u`   | `nounset`     | Treat unset variables and parameters (other than `@`, `*`, or arrays subscripted with `@`/`*`) as an error during parameter expansion. Writes error to stderr; non-interactive shell exits                                                                                                                                                   |
| `-v`   | `verbose`     | Print shell input lines to stderr as they are read                                                                                                                                                                                                                                                                                           |
| `-x`   | `xtrace`      | Print a trace of simple commands, `for`, `case`, `select`, and arithmetic `for` commands and their arguments after expansion, before execution. Prints expanded `PS4` before the command                                                                                                                                                     |
| `-B`   | `braceexpand` | The shell performs brace expansion. On by default                                                                                                                                                                                                                                                                                            |
| `-C`   | `noclobber`   | Prevent output redirection using `>`, `>&`, and `<>` from overwriting existing files. Use `>\|` to override                                                                                                                                                                                                                                  |
| `-E`   | `errtrace`    | Any trap on `ERR` is inherited by shell functions, command substitutions, and commands executed in a subshell environment                                                                                                                                                                                                                    |
| `-H`   | `histexpand`  | Enable `!` style history substitution. On by default for interactive shells                                                                                                                                                                                                                                                                  |
| `-P`   | `physical`    | Do not resolve symbolic links when executing commands like `cd` that change the current directory. Use the physical directory structure instead                                                                                                                                                                                              |
| `-T`   | `functrace`   | Any traps on `DEBUG` and `RETURN` are inherited by shell functions, command substitutions, and commands executed in a subshell environment                                                                                                                                                                                                   |

#### `-e` (`errexit`) Exception Details

The shell does NOT exit if the command that fails is:
- Part of the command list immediately following `while` or `until`
- Part of the test in an `if` statement
- Part of any command executed in a `&&` or `||` list except the command following the final `&&` or `||`
- Any command in a pipeline but the last (subject to `pipefail`)
- A command whose return status is being inverted with `!`

If a compound command other than a subshell returns non-zero because a command failed while `-e` was being ignored, the shell does not exit. A trap on `ERR` is executed before the shell exits.

This option applies to the shell environment and each subshell environment separately, and may cause subshells to exit before executing all commands.

If a compound command or shell function executes in a context where `-e` is being ignored, none of the commands within it are affected by `-e`, even if `-e` is set and a command returns failure. If `-e` is set while executing in a context where it is ignored, the setting has no effect until the compound command or function call completes.

#### `-o` Option Names

| Option Name   | Equivalent | Description                                                                                          |
|---------------|------------|------------------------------------------------------------------------------------------------------|
| `allexport`   | `-a`       | Mark all created/modified variables for export                                                       |
| `braceexpand` | `-B`       | Perform brace expansion                                                                              |
| `emacs`       | --         | Use emacs-style line editing interface (also affects `read -e`)                                      |
| `errexit`     | `-e`       | Exit on non-zero pipeline/command status                                                             |
| `errtrace`    | `-E`       | Inherit `ERR` trap in functions/subshells                                                            |
| `functrace`   | `-T`       | Inherit `DEBUG`/`RETURN` traps in functions/subshells                                                |
| `hashall`     | `-h`       | Hash commands on lookup                                                                              |
| `histexpand`  | `-H`       | Enable `!` style history substitution                                                                |
| `history`     | --         | Enable command history. On by default in interactive shells                                          |
| `ignoreeof`   | --         | An interactive shell will not exit upon reading EOF                                                  |
| `keyword`     | `-k`       | Place all assignment arguments in command environment                                                |
| `monitor`     | `-m`       | Enable job control                                                                                   |
| `noclobber`   | `-C`       | Prevent overwriting files with output redirection                                                    |
| `noexec`      | `-n`       | Read commands but do not execute                                                                     |
| `noglob`      | `-f`       | Disable filename expansion                                                                           |
| `nolog`       | --         | Currently ignored                                                                                    |
| `notify`      | `-b`       | Report terminated background jobs immediately                                                        |
| `nounset`     | `-u`       | Error on unset variable expansion                                                                    |
| `onecmd`      | `-t`       | Exit after one command                                                                               |
| `physical`    | `-P`       | Do not resolve symbolic links on directory changes                                                   |
| `pipefail`    | --         | Pipeline return value is the last non-zero exit status (or zero if all succeed). Disabled by default |
| `posix`       | --         | Enable POSIX mode; change Bash behavior to match the POSIX standard                                  |
| `privileged`  | `-p`       | Turn on privileged mode                                                                              |
| `verbose`     | `-v`       | Print shell input lines as read                                                                      |
| `vi`          | --         | Use vi-style line editing interface (also affects `read -e`)                                         |
| `xtrace`      | `-x`       | Print command traces                                                                                 |

#### Special Arguments

| Argument | Description                                                                                                                                                       |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--`     | If no arguments follow, unset the positional parameters. Otherwise, set positional parameters to the ARGUMENTS (even if some begin with `-`)                      |
| `-`      | Signal end of options. Assign remaining ARGUMENTS to positional parameters. `-x` and `-v` are turned off. If no arguments, positional parameters remain unchanged |

**Positional parameters:** The remaining N arguments are assigned in order to `$1`, `$2`, ... `$N`. The special parameter `#` is set to N.

**Return status:** Always zero unless an invalid option is supplied.

#### Viewing current options

```bash
set -o          # Print current shell option settings (human-readable)
set +o          # Print series of 'set' commands to recreate current settings
```

---

### 4.3.2 The `shopt` Builtin

```bash
shopt [-pqsu] [-o] [OPTNAME ...]
```

Toggle optional shell behavior settings.

| Option | Description                                                                                                                             |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `-p`   | Display all settable options with their status (reusable format). If OPTNAMEs are supplied, restrict output                             |
| `-s`   | Enable (set) each OPTNAME                                                                                                               |
| `-u`   | Disable (unset) each OPTNAME                                                                                                            |
| `-q`   | Suppress normal output; return status indicates whether OPTNAME is set. With multiple OPTNAMEs: zero if all enabled, non-zero otherwise |
| `-o`   | Restrict OPTNAME values to those defined for the `-o` option to `set`                                                                   |

- With no options: display all settable options with status.
- If `-s` or `-u` is used with no OPTNAMEs, shows only set or unset options respectively.
- Unless otherwise noted, shopt options are disabled (off) by default.
- **Return status (listing):** Zero if all OPTNAMEs are enabled, non-zero otherwise.
- **Return status (setting/unsetting):** Zero unless OPTNAME is not a valid shell option.

#### Complete shopt Options Table

| Option                    | Default              | Description                                                                                                                                                                                                                                                                                                                                                                                                                    |
|---------------------------|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `array_expand_once`       | off                  | Suppress multiple evaluation of associative and indexed array subscripts during arithmetic expression evaluation, while executing builtins that can perform variable assignments, and while executing builtins that perform array dereferencing                                                                                                                                                                                |
| `assoc_expand_once`       | off                  | Deprecated; a synonym for `array_expand_once`                                                                                                                                                                                                                                                                                                                                                                                  |
| `autocd`                  | off                  | A command name that is a directory name is executed as if it were the argument to `cd`. Only used by interactive shells                                                                                                                                                                                                                                                                                                        |
| `bash_source_fullpath`    | off                  | Filenames added to the `BASH_SOURCE` array variable are converted to full pathnames                                                                                                                                                                                                                                                                                                                                            |
| `cdable_vars`             | off                  | An argument to `cd` that is not a directory is assumed to be the name of a variable whose value is the directory to change to                                                                                                                                                                                                                                                                                                  |
| `cdspell`                 | off                  | `cd` attempts to correct minor spelling errors in directory components (transposed characters, missing character, extra character). Only used by interactive shells                                                                                                                                                                                                                                                            |
| `checkhash`               | off                  | Check that a command found in the hash table exists before trying to execute it. If not found, perform a normal path search                                                                                                                                                                                                                                                                                                    |
| `checkjobs`               | off                  | List the status of stopped and running jobs before exiting an interactive shell. If any are running, defer exit until a second exit attempt. Always postpone if any jobs are stopped                                                                                                                                                                                                                                           |
| `checkwinsize`            | **on**               | Check window size after each external command and update `LINES` and `COLUMNS` if necessary, using the file descriptor associated with stderr if it is a terminal                                                                                                                                                                                                                                                              |
| `cmdhist`                 | **on**               | Save all lines of a multi-line command in the same history entry. Only effective if command history is enabled                                                                                                                                                                                                                                                                                                                 |
| `compat31`                | off                  | Shell compatibility mode (see Shell Compatibility Mode)                                                                                                                                                                                                                                                                                                                                                                        |
| `compat32`                | off                  | Shell compatibility mode                                                                                                                                                                                                                                                                                                                                                                                                       |
| `compat40`                | off                  | Shell compatibility mode                                                                                                                                                                                                                                                                                                                                                                                                       |
| `compat41`                | off                  | Shell compatibility mode                                                                                                                                                                                                                                                                                                                                                                                                       |
| `compat42`                | off                  | Shell compatibility mode                                                                                                                                                                                                                                                                                                                                                                                                       |
| `compat43`                | off                  | Shell compatibility mode                                                                                                                                                                                                                                                                                                                                                                                                       |
| `compat44`                | off                  | Shell compatibility mode                                                                                                                                                                                                                                                                                                                                                                                                       |
| `complete_fullquote`      | **on**               | Quote all shell metacharacters in filenames and directory names when performing completion. If not set, dollar signs in variable references in words to be completed will not be quoted, but neither will dollar signs in filenames. Only active when using backslash quoting for completions                                                                                                                                  |
| `direxpand`               | off                  | Replace directory names with the results of word expansion when performing filename completion. Changes the contents of the Readline editing buffer                                                                                                                                                                                                                                                                            |
| `dirspell`                | off                  | Attempt spelling correction on directory names during word completion if the directory name initially supplied does not exist                                                                                                                                                                                                                                                                                                  |
| `dotglob`                 | off                  | Include filenames beginning with `.` in filename expansion results. `.` and `..` must always be matched explicitly                                                                                                                                                                                                                                                                                                             |
| `execfail`                | off                  | A non-interactive shell will not exit if it cannot execute the file specified as an argument to `exec`. An interactive shell does not exit if `exec` fails                                                                                                                                                                                                                                                                     |
| `expand_aliases`          | **on** (interactive) | Expand aliases as described in Aliases. Enabled by default for interactive shells                                                                                                                                                                                                                                                                                                                                              |
| `extdebug`                | off                  | Enable debugger behavior: (1) `declare -F` shows source file and line number. (2) `DEBUG` trap non-zero return skips next command. (3) `DEBUG` trap return of 2 simulates `return` in subroutines. (4) `BASH_ARGC` and `BASH_ARGV` are updated. (5) Function tracing enabled (command substitution, functions, and `( command )` subshells inherit `DEBUG` and `RETURN` traps). (6) Error tracing enabled (inherit `ERR` trap) |
| `extglob`                 | off                  | Enable extended pattern matching features: `?(pattern)`, `*(pattern)`, `+(pattern)`, `@(pattern)`, `!(pattern)`                                                                                                                                                                                                                                                                                                                |
| `extquote`                | **on**               | `$'string'` and `$"string"` quoting is performed within `${parameter}` expansions enclosed in double quotes                                                                                                                                                                                                                                                                                                                    |
| `failglob`                | off                  | Patterns which fail to match filenames during filename expansion result in an expansion error                                                                                                                                                                                                                                                                                                                                  |
| `force_fignore`           | **on**               | Suffixes specified by `FIGNORE` cause words to be ignored during word completion even if the ignored words are the only possible completions                                                                                                                                                                                                                                                                                   |
| `globasciiranges`         | off                  | Range expressions in pattern matching bracket expressions behave as if in the traditional C locale (not the current locale's collating sequence). Upper-case and lower-case ASCII characters collate together                                                                                                                                                                                                                  |
| `globskipdots`            | **on**               | Filename expansion will never match `.` and `..`, even if the pattern begins with `.`                                                                                                                                                                                                                                                                                                                                          |
| `globstar`                | off                  | The pattern `**` in filename expansion matches all files and zero or more directories and subdirectories. If followed by `/`, only directories and subdirectories match                                                                                                                                                                                                                                                        |
| `gnu_errfmt`              | off                  | Shell error messages are written in the standard GNU error message format                                                                                                                                                                                                                                                                                                                                                      |
| `histappend`              | off                  | Append the history list to `HISTFILE` when the shell exits, rather than overwriting it                                                                                                                                                                                                                                                                                                                                         |
| `histreedit`              | off                  | If Readline is being used, give the user the opportunity to re-edit a failed history substitution                                                                                                                                                                                                                                                                                                                              |
| `histverify`              | off                  | If Readline is being used, results of history substitution are loaded into the Readline editing buffer for further modification instead of being immediately passed to the parser                                                                                                                                                                                                                                              |
| `hostcomplete`            | **on**               | If Readline is being used, attempt hostname completion when a word containing `@` is being completed                                                                                                                                                                                                                                                                                                                           |
| `huponexit`               | off                  | Send `SIGHUP` to all jobs when an interactive login shell exits                                                                                                                                                                                                                                                                                                                                                                |
| `inherit_errexit`         | off                  | Command substitution inherits the value of the `errexit` option instead of unsetting it in the subshell environment. Enabled when POSIX mode is enabled                                                                                                                                                                                                                                                                        |
| `interactive_comments`    | **on**               | In an interactive shell, a word beginning with `#` causes that word and all remaining characters on that line to be ignored                                                                                                                                                                                                                                                                                                    |
| `lastpipe`                | off                  | If job control is not active, the shell runs the last command of a pipeline not executed in the background in the current shell environment                                                                                                                                                                                                                                                                                    |
| `lithist`                 | off                  | If `cmdhist` is also enabled, multi-line commands are saved to the history with embedded newlines rather than semicolon separators where possible                                                                                                                                                                                                                                                                              |
| `localvar_inherit`        | off                  | Local variables inherit the value and attributes of a variable of the same name at a previous scope before any new value is assigned. The `nameref` attribute is not inherited                                                                                                                                                                                                                                                 |
| `localvar_unset`          | off                  | Calling `unset` on local variables in previous function scopes marks them so subsequent lookups find them unset until that function returns. Same behavior as unsetting local variables at the current function scope                                                                                                                                                                                                          |
| `login_shell`             | (read-only)          | Set by the shell if started as a login shell. The value may not be changed                                                                                                                                                                                                                                                                                                                                                     |
| `mailwarn`                | off                  | If a file that Bash is checking for mail has been accessed since the last check, display the message "The mail in MAILFILE has been read"                                                                                                                                                                                                                                                                                      |
| `no_empty_cmd_completion` | off                  | If Readline is being used, do not search `PATH` for possible completions when completion is attempted on an empty line                                                                                                                                                                                                                                                                                                         |
| `nocaseglob`              | off                  | Match filenames in a case-insensitive fashion when performing filename expansion                                                                                                                                                                                                                                                                                                                                               |
| `nocasematch`             | off                  | Match patterns case-insensitively when performing `case` or `[[` conditional commands, pattern substitution word expansions, or filtering completions in programmable completion                                                                                                                                                                                                                                               |
| `noexpand_translation`    | off                  | Enclose the translated results of `$"..."` quoting in single quotes instead of double quotes. If the string is not translated, this has no effect                                                                                                                                                                                                                                                                              |
| `nullglob`                | off                  | Filename expansion patterns which match no files expand to nothing and are removed, rather than expanding to themselves                                                                                                                                                                                                                                                                                                        |
| `patsub_replacement`      | **on**               | Expand occurrences of `&` in the replacement string of pattern substitution to the text matched by the pattern                                                                                                                                                                                                                                                                                                                 |
| `progcomp`                | **on**               | Enable the programmable completion facilities                                                                                                                                                                                                                                                                                                                                                                                  |
| `progcomp_alias`          | off                  | If programmable completion is enabled, treat a command name that doesn't have completions as a possible alias and attempt alias expansion. If it has an alias, attempt programmable completion using the command word from the expanded alias                                                                                                                                                                                  |
| `promptvars`              | **on**               | Prompt strings undergo parameter expansion, command substitution, arithmetic expansion, and quote removal after being expanded                                                                                                                                                                                                                                                                                                 |
| `restricted_shell`        | (read-only)          | Set by the shell if started in restricted mode. The value may not be changed. Not reset when startup files are executed                                                                                                                                                                                                                                                                                                        |
| `shift_verbose`           | off                  | The `shift` builtin prints an error message when the shift count exceeds the number of positional parameters                                                                                                                                                                                                                                                                                                                   |
| `sourcepath`              | **on**               | The `.` (`source`) builtin uses `PATH` to find the directory containing the file argument when `-p` is not supplied                                                                                                                                                                                                                                                                                                            |
| `varredir_close`          | off                  | Automatically close file descriptors assigned using the `{varname}` redirection syntax instead of leaving them open when the command completes                                                                                                                                                                                                                                                                                 |
| `xpg_echo`                | off                  | The `echo` builtin expands backslash-escape sequences by default. If the `posix` shell option is also enabled, `echo` does not interpret any options                                                                                                                                                                                                                                                                           |

---

## 4.4 Special Builtins

For historical reasons, the POSIX standard classifies several builtin commands as _special_. When Bash is executing in POSIX mode, special builtins differ from other builtins in three respects:

1. **Lookup precedence:** Special builtins are found before shell functions during command lookup.
2. **Error handling:** If a special builtin returns an error status, a non-interactive shell exits.
3. **Assignment persistence:** Assignment statements preceding the command stay in effect in the shell environment after the command completes.

When Bash is NOT executing in POSIX mode, these builtins behave no differently than other Bash builtins.

### POSIX Special Builtins List

```
break  :  .  source  continue  eval  exec  exit  export
readonly  return  set  shift  times  trap  unset
```
