# Bash 5.3 Reference: Chapter 6 -- Bash Features

Complete reference for features unique to Bash, extracted from the Bash 5.3 Reference Manual.

---

## 6.1 Invoking Bash

### Synopsis

```
bash [long-opt] [-ir] [-abefhkmnptuvxdBCDHP] [-o OPTION]
    [-O SHOPT_OPTION] [ARGUMENT ...]
bash [long-opt] [-abefhkmnptuvxdBCDHP] [-o OPTION]
    [-O SHOPT_OPTION] -c STRING [ARGUMENT ...]
bash [long-opt] -s [-abefhkmnptuvxdBCDHP] [-o OPTION]
    [-O SHOPT_OPTION] [ARGUMENT ...]
```

All single-character options used with the `set` builtin can also be used at invocation. Multi-character options must appear on the command line before single-character options.

### Long Options

| Option                 | Description                                                                                                                                                 |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--debugger`           | Arrange for the debugger profile to execute before the shell starts. Turns on extended debugging mode (`extdebug` shopt option).                            |
| `--dump-po-strings`    | Print all double-quoted strings preceded by `$` on stdout in GNU gettext PO (portable object) file format. Equivalent to `-D` except for the output format. |
| `--dump-strings`       | Equivalent to `-D`.                                                                                                                                         |
| `--help`               | Display a usage message on stdout and exit successfully.                                                                                                    |
| `--init-file FILENAME` | Execute commands from FILENAME (instead of `~/.bashrc`) in an interactive shell.                                                                            |
| `--rcfile FILENAME`    | Synonym for `--init-file`.                                                                                                                                  |
| `--login`              | Equivalent to `-l`.                                                                                                                                         |
| `--noediting`          | Do not use the GNU Readline library to read command lines when the shell is interactive.                                                                    |
| `--noprofile`          | Do not load `/etc/profile` or any of `~/.bash_profile`, `~/.bash_login`, or `~/.profile` when invoked as a login shell.                                     |
| `--norc`               | Do not read `~/.bashrc` in an interactive shell. On by default if invoked as `sh`.                                                                          |
| `--posix`              | Enable POSIX mode. Change Bash behavior where defaults differ from the POSIX standard to match the standard.                                                |
| `--restricted`         | Equivalent to `-r`. Make the shell a restricted shell.                                                                                                      |
| `--verbose`            | Equivalent to `-v`. Print shell input lines as they are read.                                                                                               |
| `--version`            | Show version information on stdout and exit successfully.                                                                                                   |

### Single-Character Options (Invocation-Only)

These options are available at invocation but not with the `set` builtin:

| Option                 | Description                                                                                                                                                                                                                                                                                                             |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-c`                   | Read and execute commands from the first non-option argument COMMAND_STRING, then exit. If there are arguments after COMMAND_STRING, the first is assigned to `$0` and remaining arguments are assigned to positional parameters. The assignment to `$0` sets the name of the shell used in warning and error messages. |
| `-i`                   | Force the shell to run interactively.                                                                                                                                                                                                                                                                                   |
| `-l`                   | Make this shell act as if directly invoked by login. When interactive, equivalent to `exec -l bash`. When non-interactive, reads and executes login shell startup files. `exec bash -l` or `exec bash --login` replaces the current shell with a Bash login shell.                                                      |
| `-r`                   | Make the shell a restricted shell.                                                                                                                                                                                                                                                                                      |
| `-s`                   | If present, or if no arguments remain after option processing, Bash reads commands from stdin. Allows positional parameters to be set when invoking an interactive shell or reading input through a pipe.                                                                                                               |
| `-D`                   | Print all double-quoted strings preceded by `$` on stdout. These strings are subject to language translation when the current locale is not `C` or `POSIX`. Implies `-n`; no commands are executed.                                                                                                                     |
| `[-+]O [SHOPT_OPTION]` | SHOPT_OPTION is a shell option accepted by `shopt`. `-O` sets the value; `+O` unsets it. Without SHOPT_OPTION, prints names and values. With `+O`, output is in a format reusable as input.                                                                                                                             |
| `--`                   | Signals the end of options and disables further option processing. Arguments after `--` are treated as a script filename and arguments.                                                                                                                                                                                 |
| `-`                    | Equivalent to `--`.                                                                                                                                                                                                                                                                                                     |

### Key Definitions

- **Login shell**: One whose first character of argument zero is `-`, or one invoked with `--login`.
- **Interactive shell**: One started without non-option arguments (unless `-s` is specified), without `-c`, and whose stdin and stderr are both connected to terminals (as determined by `isatty(3)`), or one started with `-i`.

### Script Execution

If arguments remain after option processing and neither `-c` nor `-s` has been supplied, the first argument is treated as a file containing shell commands. `$0` is set to the filename, positional parameters are set to remaining arguments. Bash reads and executes commands from the file, then exits. Exit status is the exit status of the last command executed (0 if no commands are executed). Bash first attempts to open the file in the current directory; if not found, it searches `PATH`.

---

## 6.2 Bash Startup Files

If any startup file exists but cannot be read, Bash reports an error. Tildes are expanded in filenames.

### Invoked as an Interactive Login Shell (or with `--login`)

1. Reads and executes `/etc/profile` (if it exists).
2. Looks for `~/.bash_profile`, `~/.bash_login`, and `~/.profile` **in that order**; reads and executes the **first one** that exists and is readable.
3. `--noprofile` inhibits this behavior.
4. On exit (or when a non-interactive login shell executes `exit`), reads and executes `~/.bash_logout` if it exists.

### Invoked as an Interactive Non-Login Shell

1. Reads and executes `~/.bashrc` (if it exists).
2. `--norc` inhibits this behavior.
3. `--rcfile FILE` causes Bash to use FILE instead of `~/.bashrc`.

**Best practice**: Include this in `~/.bash_profile`:
```bash
if [ -f ~/.bashrc ]; then . ~/.bashrc; fi
```

### Invoked Non-Interactively

1. Looks for the variable `BASH_ENV` in the environment, expands its value, and uses the expanded value as a file to read and execute:
   ```bash
   if [ -n "$BASH_ENV" ]; then . "$BASH_ENV"; fi
   ```
2. Does **not** use `PATH` to search for the filename.
3. If invoked with `--login`, also attempts to read login shell startup files.

### Invoked with Name `sh`

Mimics historical `sh` startup behavior while conforming to POSIX:

- **Interactive login shell** (or with `--login`): reads `/etc/profile` and `~/.profile` in that order. `--noprofile` inhibits this.
- **Interactive shell**: looks for `ENV`, expands its value, and uses it as a file to read and execute. `--rcfile` has no effect.
- **Non-interactive shell**: does not attempt to read any startup files.
- Enters **POSIX mode** after reading startup files.

### Invoked in POSIX Mode

- Interactive shells expand `ENV` and read/execute the file whose name is the expanded value.
- **No other startup files are read.**

### Invoked by Remote Shell Daemon

When Bash determines it is run non-interactively with stdin connected to a network connection (e.g., via `rshd` or `sshd`):

- Reads and executes `~/.bashrc` (if it exists and is readable).
- Does **not** read `~/.bashrc` if invoked as `sh`.
- `--norc` inhibits this; `--rcfile` makes Bash use a different file.

### Invoked with Unequal Effective and Real UID/GIDs

If effective user (group) id does not equal real user (group) id and `-p` is not supplied:

- No startup files are read.
- Shell functions are not inherited from the environment.
- `SHELLOPTS`, `BASHOPTS`, `CDPATH`, and `GLOBIGNORE` are ignored if in the environment.
- Effective user id is set to the real user id.

If `-p` **is** supplied at invocation, startup behavior is the same but the effective user id is **not** reset.

---

## 6.3 Interactive Shells

### 6.3.1 What Is an Interactive Shell?

An interactive shell is one started:
- Without non-option arguments (unless `-s` is specified), and
- Without the `-c` option, and
- Whose input and error output are both connected to terminals (as determined by `isatty(3)`)

OR one started with the `-i` option.

An interactive shell generally reads from and writes to a user's terminal.

### 6.3.2 Detecting Interactive Mode

**Method 1** -- Check the `$-` special parameter (contains `i` when interactive):
```bash
case "$-" in
*i*)  echo This shell is interactive ;;
*)    echo This shell is not interactive ;;
esac
```

**Method 2** -- Check `PS1` (unset in non-interactive shells):
```bash
if [ -z "$PS1" ]; then
    echo This shell is not interactive
else
    echo This shell is interactive
fi
```

### 6.3.3 Interactive Shell Behavior

When running interactively, the shell changes behavior in these ways:

| #  | Behavior                                                                                                                                                                                 |
|----|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Startup files are read and executed.                                                                                                                                                     |
| 2  | Job Control is enabled by default. Bash ignores `SIGTTIN`, `SIGTTOU`, and `SIGTSTP`.                                                                                                     |
| 3  | Bash executes the values of the set elements of the `PROMPT_COMMAND` array as commands before printing `$PS1`.                                                                           |
| 4  | `PS1` is expanded and displayed before reading the first line of a command. `PS2` before subsequent lines of multi-line commands. `PS0` after reading a command but before executing it. |
| 5  | Readline is used to read commands from the terminal.                                                                                                                                     |
| 6  | Bash inspects `ignoreeof` (`set -o`) instead of exiting immediately on EOF.                                                                                                              |
| 7  | Command history and history expansion are enabled by default. On exit, history is saved to `$HISTFILE`.                                                                                  |
| 8  | Alias expansion is performed by default.                                                                                                                                                 |
| 9  | In the absence of traps, `SIGTERM` is ignored.                                                                                                                                           |
| 10 | In the absence of traps, `SIGINT` is caught and handled. `SIGINT` will interrupt some builtins.                                                                                          |
| 11 | An interactive login shell sends `SIGHUP` to all jobs on exit if `huponexit` is enabled.                                                                                                 |
| 12 | The `-n` option has no effect (neither at invocation nor with `set -n`).                                                                                                                 |
| 13 | Bash checks for mail periodically based on `MAIL`, `MAILPATH`, and `MAILCHECK`.                                                                                                          |
| 14 | The shell will not exit on expansion errors due to unbound variables after `set -u`.                                                                                                     |
| 15 | The shell will not exit on expansion errors from `${VAR:?WORD}` when VAR is unset/null.                                                                                                  |
| 16 | Redirection errors in builtins will not cause the shell to exit.                                                                                                                         |
| 17 | In POSIX mode, a special builtin returning error status will not cause exit.                                                                                                             |
| 18 | A failed `exec` will not cause exit.                                                                                                                                                     |
| 19 | Parser syntax errors will not cause exit.                                                                                                                                                |
| 20 | If `cdspell` is enabled, the shell attempts spelling correction for `cd` arguments. Only effective in interactive shells.                                                                |
| 21 | The shell checks `TMOUT` and exits if a command is not read within the specified seconds after printing `$PS1`.                                                                          |

---

## 6.4 Bash Conditional Expressions

Used by `[[` compound command, and the `test` and `[` builtin commands. The `test` and `[` commands determine behavior based on argument count.

Expressions may be unary or binary. Unary expressions examine file status or shell variables. Binary operators compare strings, numbers, and file attributes.

### Special Filenames

Bash handles these filenames specially in expressions:
- `/dev/fd/N` -- checks file descriptor N
- `/dev/stdin` -- checks file descriptor 0
- `/dev/stdout` -- checks file descriptor 1
- `/dev/stderr` -- checks file descriptor 2

If the OS provides these special files, Bash uses them; otherwise it emulates them internally.

### Sorting Behavior

- With `[[`, the `<` and `>` operators sort **lexicographically using the current locale**.
- The `test` command uses **ASCII ordering**.

### Symlink Behavior

Unless otherwise specified, primaries that operate on files follow symbolic links and operate on the target, not the link itself.

### File Test Operators

| Operator  | True if...                                                    |
|-----------|---------------------------------------------------------------|
| `-a FILE` | FILE exists.                                                  |
| `-b FILE` | FILE exists and is a block special file.                      |
| `-c FILE` | FILE exists and is a character special file.                  |
| `-d FILE` | FILE exists and is a directory.                               |
| `-e FILE` | FILE exists.                                                  |
| `-f FILE` | FILE exists and is a regular file.                            |
| `-g FILE` | FILE exists and its set-group-id bit is set.                  |
| `-h FILE` | FILE exists and is a symbolic link.                           |
| `-k FILE` | FILE exists and its "sticky" bit is set.                      |
| `-p FILE` | FILE exists and is a named pipe (FIFO).                       |
| `-r FILE` | FILE exists and is readable.                                  |
| `-s FILE` | FILE exists and has a size greater than zero.                 |
| `-t FD`   | File descriptor FD is open and refers to a terminal.          |
| `-u FILE` | FILE exists and its set-user-id bit is set.                   |
| `-w FILE` | FILE exists and is writable.                                  |
| `-x FILE` | FILE exists and is executable.                                |
| `-G FILE` | FILE exists and is owned by the effective group id.           |
| `-L FILE` | FILE exists and is a symbolic link.                           |
| `-N FILE` | FILE exists and has been modified since it was last accessed. |
| `-O FILE` | FILE exists and is owned by the effective user id.            |
| `-S FILE` | FILE exists and is a socket.                                  |

### File Comparison Operators

| Operator          | True if...                                                                            |
|-------------------|---------------------------------------------------------------------------------------|
| `FILE1 -ef FILE2` | FILE1 and FILE2 refer to the same device and inode numbers.                           |
| `FILE1 -nt FILE2` | FILE1 is newer (by modification date) than FILE2, or FILE1 exists and FILE2 does not. |
| `FILE1 -ot FILE2` | FILE1 is older than FILE2, or FILE2 exists and FILE1 does not.                        |

### Variable and Option Test Operators

| Operator     | True if...                                                                                                                                                                                                                                            |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-o OPTNAME` | Shell option OPTNAME is enabled (options as listed for `set -o`).                                                                                                                                                                                     |
| `-v VARNAME` | Shell variable VARNAME is set (has been assigned a value). If VARNAME is an indexed array subscripted by `@` or `*`, true if the array has any set elements. If associative array subscripted by `@` or `*`, true if an element with that key is set. |
| `-R VARNAME` | Shell variable VARNAME is set and is a name reference.                                                                                                                                                                                                |

### String Operators

| Operator             | True if...                                                    |
|----------------------|---------------------------------------------------------------|
| `-z STRING`          | Length of STRING is zero.                                     |
| `-n STRING`          | Length of STRING is non-zero.                                 |
| `STRING`             | (Unary) Length of STRING is non-zero (same as `-n`).          |
| `STRING1 == STRING2` | Strings are equal. With `[[`, performs pattern matching.      |
| `STRING1 = STRING2`  | Strings are equal. Use `=` with `test` for POSIX conformance. |
| `STRING1 != STRING2` | Strings are not equal.                                        |
| `STRING1 < STRING2`  | STRING1 sorts before STRING2 lexicographically.               |
| `STRING1 > STRING2`  | STRING1 sorts after STRING2 lexicographically.                |

**Note on `=~`**: Within `[[`, the `=~` operator performs regular expression matching (documented under Conditional Constructs). The string to the right is treated as a POSIX extended regular expression.

### Arithmetic Comparison Operators

| Operator        | True if...                             |
|-----------------|----------------------------------------|
| `ARG1 -eq ARG2` | ARG1 is equal to ARG2.                 |
| `ARG1 -ne ARG2` | ARG1 is not equal to ARG2.             |
| `ARG1 -lt ARG2` | ARG1 is less than ARG2.                |
| `ARG1 -le ARG2` | ARG1 is less than or equal to ARG2.    |
| `ARG1 -gt ARG2` | ARG1 is greater than ARG2.             |
| `ARG1 -ge ARG2` | ARG1 is greater than or equal to ARG2. |

ARG1 and ARG2 may be positive or negative integers. When used with `[[`, they are evaluated as arithmetic expressions. Empty strings from expansion are treated as evaluating to 0.

---

## 6.5 Shell Arithmetic

The shell allows arithmetic expressions to be evaluated via:
- Shell expansion (`$((...))`)
- The `((...))` compound command
- The `let` builtin
- The `declare` builtin (with `-i` option)
- The arithmetic `for` command
- The `[[` conditional command

Evaluation uses the **largest fixed-width integers** available, with **no overflow check**. Division by 0 is trapped and flagged as an error.

### Operators by Precedence (Highest to Lowest)

| Precedence | Operator                                                 | Description                             |
|------------|----------------------------------------------------------|-----------------------------------------|
| 1          | `ID++` `ID--`                                            | Variable post-increment, post-decrement |
| 2          | `++ID` `--ID`                                            | Variable pre-increment, pre-decrement   |
| 3          | `-` `+`                                                  | Unary minus, unary plus                 |
| 4          | `!` `~`                                                  | Logical negation, bitwise negation      |
| 5          | `**`                                                     | Exponentiation                          |
| 6          | `*` `/` `%`                                              | Multiplication, division, remainder     |
| 7          | `+` `-`                                                  | Addition, subtraction                   |
| 8          | `<<` `>>`                                                | Left and right bitwise shifts           |
| 9          | `<=` `>=` `<` `>`                                        | Comparison                              |
| 10         | `==` `!=`                                                | Equality, inequality                    |
| 11         | `&`                                                      | Bitwise AND                             |
| 12         | `^`                                                      | Bitwise exclusive OR (XOR)              |
| 13         | `\|`                                                     | Bitwise OR                              |
| 14         | `&&`                                                     | Logical AND                             |
| 15         | `\|\|`                                                   | Logical OR                              |
| 16         | `expr ? expr : expr`                                     | Conditional (ternary) operator          |
| 17         | `=` `*=` `/=` `%=` `+=` `-=` `<<=` `>>=` `&=` `^=` `\|=` | Assignment operators                    |
| 18         | `expr1 , expr2`                                          | Comma (evaluate both, return last)      |

### Variable References in Arithmetic

- Shell variables are allowed as operands; parameter expansion is performed before evaluation.
- Within an expression, shell variables may be referenced **by name** without `$` expansion syntax.
- A null or unset variable evaluates to **0** when referenced by name.
- A variable's value is evaluated as an arithmetic expression when referenced, or when a variable with the `integer` attribute (`declare -i`) is assigned.
- A variable need not have the `integer` attribute to be used in an expression.

### Integer Constants and Number Bases

| Format                              | Meaning                               |
|-------------------------------------|---------------------------------------|
| Plain number (e.g., `42`)           | Base 10                               |
| Leading `0` (e.g., `052`)           | Octal                                 |
| Leading `0x` or `0X` (e.g., `0x2A`) | Hexadecimal                           |
| `BASE#N` (e.g., `2#101010`)         | Number N in the specified BASE (2-64) |

For bases requiring non-digit characters (digits greater than 9), the representation uses: lowercase letters, uppercase letters, `@`, and `_`, in that order. If base is 36 or less, lowercase and uppercase may be used interchangeably for values 10-35.

Sub-expressions in parentheses are evaluated first and may override precedence rules.

---

## 6.6 Aliases

Aliases allow a string to be substituted for a word in a position where it can be the first word of a simple command. Created and managed with the `alias` and `unalias` builtins.

### Key Rules

- If the shell reads an unquoted word in the right position, it checks whether it matches an alias name. If so, it replaces the word with the alias value.
- The characters `/`, `$`, `` ` ``, `=` and any shell metacharacters or quoting characters **may not** appear in an alias name.
- The replacement text may contain any valid shell input, including metacharacters.
- The first word of the replacement text is tested for aliases, but a word identical to an alias being expanded is **not** expanded again (prevents infinite recursion). Example: aliasing `ls` to `"ls -F"` works correctly.
- If the **last character** of the alias value is a **blank**, the next command word following the alias is also checked for alias expansion.
- There is **no mechanism** for using arguments in the replacement text. Use shell functions instead.
- Aliases are **not expanded** in non-interactive shells unless `expand_aliases` is set via `shopt`.

### Timing of Alias Expansion

- Aliases are expanded **when a command is read**, not when it is executed.
- An alias definition on the same line as another command does not take effect until the next line of input is read.
- An alias defined in a compound command does not take effect until the entire compound command is parsed and executed.
- Aliases are expanded when a function **definition is read**, not when the function is executed.
- Aliases defined inside a function are not available until after that function is executed.

**Best practice**: Always put alias definitions on a separate line. Do not use `alias` in compound commands. For almost every purpose, shell functions are preferable to aliases.

---

## 6.7 Arrays

Bash provides **one-dimensional indexed** and **associative** array variables. There is no maximum limit on size, and members need not be indexed or assigned contiguously. Indexed arrays are zero-based; associative arrays use arbitrary strings as keys.

### Subscript Expansion

- **Indexed arrays**: The shell performs parameter/variable expansion, arithmetic expansion, command substitution, and quote removal on subscripts. Empty strings evaluate to 0.
- **Associative arrays**: The shell performs tilde expansion, parameter/variable expansion, arithmetic expansion, command substitution, and quote removal on subscripts. Empty strings **cannot** be used as associative array keys.

### Declaration

```bash
# Indexed array -- automatic creation
name[subscript]=value

# Indexed array -- explicit declaration
declare -a name

# Associative array -- must be explicitly declared
declare -A name
```

The syntax `declare -a name[subscript]` is accepted but the subscript is ignored.

Attributes may be specified with `declare` and `readonly`. Each attribute applies to all members.

### Assignment

**Compound assignment**:
```bash
name=(value1 value2 ...)
name=([subscript1]=value1 [subscript2]=value2 ...)
```

Each value undergoes shell expansions, but values that are valid variable assignments (including brackets and subscript) do not undergo brace expansion and word splitting.

**Indexed arrays**: If the optional subscript is supplied, that index is assigned. Otherwise, the index is the last assigned index plus one. Indexing starts at zero.

**Associative arrays**: Words may be either assignment statements (subscript required) or key/value pairs:
```bash
name=(key1 value1 key2 value2 ...)
# equivalent to:
name=([key1]=value1 [key2]=value2 ...)
```
The first word determines interpretation. All assignments must be the same type. Keys may not be missing or empty. A final missing value is treated as the empty string.

**Negative indices** (indexed arrays): Interpreted as relative to one greater than the maximum index. An index of -1 references the last element.

**Append operator**: `+=` appends when using compound assignment syntax.

### Referencing Elements

```bash
${name[subscript]}      # Single element (braces required)
${name[@]}              # All elements as separate words (in double quotes)
${name[*]}              # All elements as single word (in double quotes),
                        # separated by first character of IFS
${#name[subscript]}     # Length of element
${#name[@]}             # Number of elements in array
${#name[*]}             # Number of elements in array
${!name[@]}             # All indices/keys as separate words
${!name[*]}             # All indices/keys as single word
```

When there are no array members, `${name[@]}` expands to nothing.

Referencing an array variable **without a subscript** is equivalent to referencing subscript 0.

### Unsetting Array Elements

```bash
unset name[subscript]   # Unset element at index (quote to prevent globbing)
unset name              # Remove the entire array
unset 'name[subscript]' # Safer -- prevents filename expansion
```

- Unsetting the last element does **not** unset the variable.
- For associative arrays, `unset name[*]` or `unset name[@]` removes the element with key `*` or `@`.
- For indexed arrays, `unset name[*]` or `unset name[@]` removes all elements but does not remove the array itself.

### Related Builtins

- `declare -a` / `local -a` / `readonly -a` -- indexed array
- `declare -A` / `local -A` / `readonly -A` -- associative array (takes precedence if both `-a` and `-A` are supplied)
- `read -a` -- assign words from stdin to an array
- `mapfile` / `readarray` -- read lines from stdin into an array
- `set` and `declare` display array values in a reusable format

---

## 6.8 The Directory Stack

The directory stack is a list of recently-visited directories. The current directory is always the "top" of the stack. Contents are also visible as the `DIRSTACK` shell variable.

### `dirs`

```
dirs [-clpv] [+N | -N]
```

Without options, displays currently remembered directories.

| Option | Description                                                                  |
|--------|------------------------------------------------------------------------------|
| `-c`   | Clears the directory stack by deleting all elements.                         |
| `-l`   | Produces a listing using full pathnames (default uses `~` for home).         |
| `-p`   | Prints the directory stack with one entry per line.                          |
| `-v`   | Prints the directory stack with one entry per line, prefixed with its index. |
| `+N`   | Displays the Nth directory counting from the left (starting with zero).      |
| `-N`   | Displays the Nth directory counting from the right (starting with zero).     |

### `popd`

```
popd [-n] [+N | -N]
```

Removes elements from the directory stack. Elements are numbered from 0 starting at the first directory listed by `dirs`. `popd` alone is equivalent to `popd +0`.

| Option | Description                                                                                |
|--------|--------------------------------------------------------------------------------------------|
| `-n`   | Suppress the normal directory change when removing directories; only manipulate the stack. |
| `+N`   | Remove the Nth directory counting from the left (starting with zero).                      |
| `-N`   | Remove the Nth directory counting from the right (starting with zero).                     |

When no arguments are given, removes the top directory and changes to the new top. If `cd` fails, `popd` returns non-zero. On success, Bash runs `dirs` to show the final stack.

### `pushd`

```
pushd [-n] [+N | -N | DIR]
```

Adds a directory to the top of the stack, or rotates the stack. With no arguments, exchanges the top two elements.

| Option | Description                                                                                          |
|--------|------------------------------------------------------------------------------------------------------|
| `-n`   | Suppress the normal directory change when rotating or adding directories; only manipulate the stack. |
| `+N`   | Rotate the stack so the Nth directory from the left (starting with zero) is at the top.              |
| `-N`   | Rotate the stack so the Nth directory from the right (starting with zero) is at the top.             |
| `DIR`  | Make DIR the top of the stack.                                                                       |

After modification (unless `-n` is supplied), `pushd` uses `cd` to change to the top directory. On success, runs `dirs` to show the final stack.

---

## 6.9 Controlling the Prompt

The following escape sequences can appear in the prompt variables `PS0`, `PS1`, `PS2`, and `PS4`:

| Escape       | Description                                                                                                                                              |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `\a`         | Bell character (ASCII 07).                                                                                                                               |
| `\d`         | The date in "Weekday Month Date" format (e.g., "Tue May 26").                                                                                            |
| `\D{FORMAT}` | FORMAT is passed to `strftime(3)` and the result is inserted. An empty FORMAT results in a locale-specific time representation. The braces are required. |
| `\e`         | Escape character (ASCII 033).                                                                                                                            |
| `\h`         | The hostname, up to the first `.`.                                                                                                                       |
| `\H`         | The full hostname.                                                                                                                                       |
| `\j`         | The number of jobs currently managed by the shell.                                                                                                       |
| `\l`         | The basename of the shell's terminal device name (e.g., "ttys0").                                                                                        |
| `\n`         | A newline.                                                                                                                                               |
| `\r`         | A carriage return.                                                                                                                                       |
| `\s`         | The name of the shell: the basename of `$0` (portion after the final slash).                                                                             |
| `\t`         | The time in 24-hour `HH:MM:SS` format.                                                                                                                   |
| `\T`         | The time in 12-hour `HH:MM:SS` format.                                                                                                                   |
| `\@`         | The time in 12-hour am/pm format.                                                                                                                        |
| `\A`         | The time in 24-hour `HH:MM` format.                                                                                                                      |
| `\u`         | The username of the current user.                                                                                                                        |
| `\v`         | The Bash version (e.g., 2.00).                                                                                                                           |
| `\V`         | The Bash release: version + patchlevel (e.g., 2.00.0).                                                                                                   |
| `\w`         | The value of `$PWD`, with `$HOME` abbreviated as `~` (uses `$PROMPT_DIRTRIM`).                                                                           |
| `\W`         | The basename of `$PWD`, with `$HOME` abbreviated as `~`.                                                                                                 |
| `\!`         | The history number of this command.                                                                                                                      |
| `\#`         | The command number of this command.                                                                                                                      |
| `\$`         | If the effective UID is 0, `#`; otherwise `$`.                                                                                                           |
| `\nnn`       | The character whose ASCII code is the octal value nnn.                                                                                                   |
| `\\`         | A literal backslash.                                                                                                                                     |
| `\[`         | Begin a sequence of non-printing characters. Use to embed terminal control sequences into the prompt.                                                    |
| `\]`         | End a sequence of non-printing characters.                                                                                                               |

### Command Number vs. History Number

- **History number**: Position in the history list (may include commands restored from the history file).
- **Command number**: Position in the sequence of commands executed during the current shell session.

### Prompt Expansion

After the string is decoded, it is expanded via parameter expansion, command substitution, arithmetic expansion, and quote removal, subject to the `promptvars` shell option. This can have unwanted side effects if escaped portions appear within command substitution or contain characters special to word expansion.

---

## 6.10 The Restricted Shell

Bash becomes restricted when started with:
- The name `rbash`, OR
- The `--restricted` or `-r` option

A restricted shell behaves identically to `bash` except the following are **disallowed or not performed**:

| Restriction                                                                       |
|-----------------------------------------------------------------------------------|
| Changing directories with `cd`.                                                   |
| Setting or unsetting `SHELL`, `PATH`, `HISTFILE`, `ENV`, or `BASH_ENV`.           |
| Specifying command names containing slashes.                                      |
| Specifying a filename containing a slash as an argument to `.` (source).          |
| Using the `-p` option to `.` to specify a search path.                            |
| Specifying a filename containing a slash as an argument to `history`.             |
| Specifying a filename containing a slash as an argument to `-p` option of `hash`. |
| Importing function definitions from the shell environment at startup.             |
| Parsing the value of `SHELLOPTS` from the environment at startup.                 |
| Redirecting output using `>`, `>\|`, `<>`, `>&`, `&>`, and `>>`.                  |
| Using `exec` to replace the shell with another command.                           |
| Adding or deleting builtins with `-f` and `-d` options to `enable`.               |
| Using `enable` to enable disabled shell builtins.                                 |
| Specifying the `-p` option to `command`.                                          |
| Turning off restricted mode with `set +r` or `shopt -u restricted_shell`.         |

### Important Notes

- Restrictions are enforced **after** startup files are read.
- When a shell script is executed, `rbash` turns off restrictions in the spawned shell.
- For a useful restricted environment, also: set `PATH` to allow only verified commands, change to a non-writable directory after login, disallow shell script execution, and clean the environment of variables that modify command behavior (e.g., `VISUAL`, `PAGER`).
- Modern systems provide more secure alternatives: jails, zones, or containers.

---

## 6.11 Bash and POSIX

### 6.11.1 What Is POSIX?

POSIX is a family of standards based on Unix, maintained by the Austin Group (IEEE, The Open Group, ISO/IEC SC22/WG15). The Shell and Utilities volume is part of IEEE Std 1003.1-2024. Freely available at: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/contents.html

### 6.11.2 Bash POSIX Mode

Enter POSIX mode via `--posix` at invocation or `set -o posix` at runtime. When invoked as `sh`, Bash enters POSIX mode after reading startup files.

#### Complete List of POSIX Mode Behavior Changes

| #  | Behavior Change                                                                                                                                                                                                               |
|----|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Bash ensures `POSIXLY_CORRECT` is set.                                                                                                                                                                                        |
| 2  | Reads and executes POSIX startup files (`$ENV`) rather than normal Bash files.                                                                                                                                                |
| 3  | Alias expansion is always enabled, even in non-interactive shells.                                                                                                                                                            |
| 4  | Reserved words in recognized contexts do not undergo alias expansion.                                                                                                                                                         |
| 5  | Alias expansion is performed when initially parsing a command substitution (default mode defers it until execution).                                                                                                          |
| 6  | `time` may be used by itself as a simple command, displaying timing statistics for the shell and its children. `TIMEFORMAT` controls the format.                                                                              |
| 7  | The parser does not recognize `time` as a reserved word if the next token begins with `-`.                                                                                                                                    |
| 8  | When parsing `${...}` within double quotes, single quotes are no longer special and cannot quote a closing brace (unless the operator performs pattern removal).                                                              |
| 9  | Redirection operators do not perform filename expansion on the word unless the shell is interactive.                                                                                                                          |
| 10 | Redirection operators do not perform word splitting on the word.                                                                                                                                                              |
| 11 | Function names may not be the same as a POSIX special builtin.                                                                                                                                                                |
| 12 | Tilde expansion is only performed on assignments preceding a command name, not all assignments on the line.                                                                                                                   |
| 13 | Variable indirection may not be applied to the `#` and `?` special parameters.                                                                                                                                                |
| 14 | Expanding `*` in a pattern context where the expansion is double-quoted does not treat `$*` as if double-quoted.                                                                                                              |
| 15 | A double quote (`"`) is treated specially in a backquoted command substitution in an expanding here-document body (backslash before `"` escapes it).                                                                          |
| 16 | Command substitutions do not set the `?` special parameter. Exit status of a simple command without a command word is the exit status of the last command substitution, but not until after all assignments and redirections. |
| 17 | Literal tildes as the first character in `PATH` elements are not expanded.                                                                                                                                                    |
| 18 | Command lookup finds POSIX special builtins before shell functions (including `type` and `command` output).                                                                                                                   |
| 19 | The shell will not execute a function whose name contains slashes, even if defined before entering POSIX mode.                                                                                                                |
| 20 | When a hashed command no longer exists, Bash re-searches `$PATH`. (Also available with `shopt -s checkhash`.)                                                                                                                 |
| 21 | Bash will not insert a command without the execute bit into the hash table, even as a last-ditch `$PATH` search result.                                                                                                       |
| 22 | Job control message for non-zero exit: `Done(status)`.                                                                                                                                                                        |
| 23 | Job control message for stopped job: `Stopped(SIGNAME)`.                                                                                                                                                                      |
| 24 | Interactive shell does not perform job notifications between commands separated by `;` or newline. Non-interactive shells print status after foreground job completion.                                                       |
| 25 | Interactive shell waits until the next prompt before printing background job status changes. Non-interactive shells print after foreground job completion.                                                                    |
| 26 | Jobs are permanently removed from the table after user notification via `wait` or `jobs`. Status remains available via `wait` with a PID argument.                                                                            |
| 27 | `vi` editing mode invokes `vi` directly when `v` is pressed (ignores `$VISUAL` and `$EDITOR`).                                                                                                                                |
| 28 | Prompt expansion enables POSIX `PS1`/`PS2` expansions: `!` = history number, `!!` = literal `!`. Parameter expansion on `PS1`/`PS2` regardless of `promptvars`.                                                               |
| 29 | Default history file is `~/.sh_history`.                                                                                                                                                                                      |
| 30 | `!` does not introduce history expansion within double-quoted strings, even with `histexpand` enabled.                                                                                                                        |
| 31 | When printing function definitions (e.g., via `type`), `function` keyword is omitted unless necessary.                                                                                                                        |
| 32 | Non-interactive shells exit on syntax errors in arithmetic expansion.                                                                                                                                                         |
| 33 | Non-interactive shells exit on parameter expansion errors.                                                                                                                                                                    |
| 34 | Non-interactive shells exit if a POSIX special builtin returns error status (incorrect options, redirection errors, variable assignment errors, etc.).                                                                        |
| 35 | Non-interactive shells exit on variable assignment errors when no command name follows.                                                                                                                                       |
| 36 | Non-interactive shells exit on variable assignment errors preceding a special builtin. For other simple commands, execution of that command is aborted but the shell continues.                                               |
| 37 | Non-interactive shells exit if the iteration variable in `for` or selection variable in `select` is readonly or has an invalid name.                                                                                          |
| 38 | Non-interactive shells exit if FILENAME in `. FILENAME` is not found.                                                                                                                                                         |
| 39 | Non-interactive shells exit on syntax errors in scripts read with `.` / `source` or strings processed by `eval`.                                                                                                              |
| 40 | Non-interactive shells exit if `export`, `readonly`, or `unset` receive an argument that is not a valid identifier (when not operating on functions).                                                                         |
| 41 | Assignment statements preceding POSIX special builtins persist in the shell environment after the builtin completes.                                                                                                          |
| 42 | `command` does not prevent builtins that take assignment statements from expanding them as such. (In non-POSIX mode, declaration commands lose assignment expansion when preceded by `command`.)                              |
| 43 | Enables `inherit_errexit`: subshells for command substitutions inherit `-e` from the parent (normally Bash clears it).                                                                                                        |
| 44 | Enables `shift_verbose`: numeric arguments to `shift` that exceed positional parameter count produce an error.                                                                                                                |
| 45 | Enables `interactive_comments`.                                                                                                                                                                                               |
| 46 | `.` and `source` do not search the current directory if the filename is not found via `PATH`.                                                                                                                                 |
| 47 | `alias` does not display definitions with a leading `alias ` unless `-p` is supplied.                                                                                                                                         |
| 48 | `bg` uses the required format (no current/previous job indication).                                                                                                                                                           |
| 49 | `cd` in logical mode fails if the constructed pathname does not refer to an existing directory (no fallback to physical mode).                                                                                                |
| 50 | `cd` attempts the supplied directory name if the constructed pathname exceeds `PATH_MAX`.                                                                                                                                     |
| 51 | With `xpg_echo` enabled, `echo` does not interpret arguments as options; displays each argument after converting escape sequences.                                                                                            |
| 52 | `export` and `readonly` output uses POSIX-required format.                                                                                                                                                                    |
| 53 | `fc` history listing does not indicate modified entries.                                                                                                                                                                      |
| 54 | Default editor for `fc` is `ed`.                                                                                                                                                                                              |
| 55 | `fc` treats extra arguments as an error.                                                                                                                                                                                      |
| 56 | `fc -s` with too many arguments prints an error and returns failure.                                                                                                                                                          |
| 57 | `kill -l` prints signal names on a single line, separated by spaces, without `SIG` prefix.                                                                                                                                    |
| 58 | `kill` does not accept signal names with `SIG` prefix.                                                                                                                                                                        |
| 59 | `kill` returns failure if any pid/job argument is invalid or sending the signal fails. (Default mode returns success if the signal was sent to any specified process.)                                                        |
| 60 | `printf` uses `double` (via `strtod`) for floating point conversion. The `L` modifier forces `long double`.                                                                                                                   |
| 61 | `pwd` verifies the printed value matches the current directory, even without `-P`.                                                                                                                                            |
| 62 | `read` may be interrupted by a trapped signal; trap handler executes and `read` returns exit status > 128.                                                                                                                    |
| 63 | `set` without options does not display shell function names and definitions.                                                                                                                                                  |
| 64 | `set` without options displays variable values without quotes unless they contain metacharacters.                                                                                                                             |
| 65 | `test` compares strings using the current locale for `<` and `>`.                                                                                                                                                             |
| 66 | `test -t` requires an argument (Bash normally accommodates historical optional-argument behavior).                                                                                                                            |
| 67 | `trap` displays signal names without `SIG` prefix.                                                                                                                                                                            |
| 68 | `trap` first argument is only treated as a signal spec if it consists solely of digits that form a valid signal number. Use `-` to reset to original disposition.                                                             |
| 69 | `trap -p` without arguments displays signals with SIG_DFL disposition and those ignored at startup, not just trapped signals.                                                                                                 |
| 70 | `type` and `command` do not report non-executable files as found (though the shell may still try to execute them as a last resort).                                                                                           |
| 71 | `ulimit` uses 512-byte block size for `-c` and `-f`.                                                                                                                                                                          |
| 72 | `unset -v` returns a fatal error when attempting to unset a readonly or non-unsettable variable (causes non-interactive shell to exit).                                                                                       |
| 73 | `unset` on a variable in a preceding assignment statement also attempts to unset a same-named variable in the current or previous scope.                                                                                      |
| 74 | `SIGCHLD` arrival with a trap set does not interrupt `wait`. The trap runs once per exiting child.                                                                                                                            |
| 75 | Exited background process status is removed from the list after `wait` returns it.                                                                                                                                            |

#### Additional POSIX Behavior Not Implemented Even in POSIX Mode

1. **Byte-oriented word splitting**: POSIX requires each byte in `IFS` to potentially split a word. Bash treats valid multibyte characters in `IFS` as single delimiters and does not split valid multibyte characters. (POSIX interpretation 1560, modified by issue 1924.)
2. **`fc` editor fallback**: `fc` checks `$EDITOR` if `FCEDIT` is unset, rather than defaulting directly to `ed`. Uses `ed` only if `EDITOR` is also unset.
3. **`echo` conformance**: Requires `xpg_echo` option to be enabled.

Bash can be configured to be POSIX-conformant by default via `--enable-strict-posix-default` at build time.

---

## 6.12 Shell Compatibility Mode

Introduced in Bash 4.0. Specified as options to `shopt` (`compat31`, `compat32`, `compat40`, `compat41`, etc.) or via the `BASH_COMPAT` variable (introduced in Bash 4.3). Only one compatibility level is active at a time (mutually exclusive). The level allows users to select behavior from previous versions while migrating scripts.

### Configuration Methods

- **Bash < 5.0**: Use `shopt` options (e.g., `shopt -s compat43`) or `BASH_COMPAT`.
- **Bash 5.0**: Last version with an individual `shopt` option for the previous version.
- **Bash 5.1+**: `BASH_COMPAT` is the **only** mechanism. Set to a decimal version (e.g., `4.2`) or an integer (e.g., `42`).

### Important Note on Cascading

Enabling a compatibility level (e.g., `compat32`) may affect behavior of all levels up to and including the current level. Each level controls behavior that changed in that version, but the behavior may have been present in earlier versions.

### Compatibility Levels

#### `compat31`
- Quoting the RHS of `[[`'s `=~` operator has no special effect.

#### `compat40`
- `<` and `>` in `[[` do not consider the current locale; they use ASCII ordering. (Bash < 4.1 used `strcmp(3)`; Bash 4.1+ uses `strcoll(3)` with the current locale.)

#### `compat41`
- In POSIX mode, `time` may be followed by options and still be recognized as a reserved word (POSIX interpretation 267).
- In POSIX mode, the parser requires an even number of single quotes in the WORD portion of a double-quoted `${...}` expansion and treats them specially (POSIX interpretation 221).

#### `compat42`
- The replacement string in double-quoted pattern substitution does not undergo quote removal (as it does in versions after Bash 4.2).
- In POSIX mode, single quotes are special in the WORD portion of double-quoted `${...}` expansion and can quote a closing brace (part of POSIX interpretation 221). In later versions, single quotes are not special.

#### `compat43`
- Word expansion errors are non-fatal (cause the current command to fail), even in POSIX mode. (Default: fatal, causing shell exit.)
- When executing a shell function, the loop state (while/until/etc.) is **not** reset, so `break` or `continue` in a function will affect loops in the calling context. (Bash 4.4+ resets loop state.)

#### `compat44`
- `BASH_ARGV` and `BASH_ARGC` are set up to expand to positional parameters even without extended debugging mode.
- A subshell inherits loops from its parent, so `break` or `continue` causes the subshell to exit. (Bash 5.0+ resets loop state.)
- Variable assignments preceding `export` and `readonly` continue to affect variables with the same name in the calling environment even outside POSIX mode.

#### `compat50` (set using `BASH_COMPAT`)
- `$RANDOM` generation reverts to the Bash 5.0 method. Seeding by assigning to `RANDOM` produces the same sequence as in Bash 5.0.
- If the command hash table is empty, Bash prints an informational message (even with reusable output). Bash 5.1 suppresses this with `-l`.

#### `compat51` (set using `BASH_COMPAT`)
- `unset` with an argument like `a[@]` unsets the entire array. (Bash 5.2: unsets element with key `@` for associative arrays, or removes all elements without unsetting the array for indexed arrays.)
- Arithmetic commands (`((...))`) and arithmetic `for` expressions can be expanded more than once.
- Expressions in `[[` arithmetic operators can be expanded more than once.
- Substring parameter brace expansion expressions can be expanded more than once.
- `$((...))` word expansion expressions can be expanded more than once.
- Arithmetic expressions as indexed array subscripts can be expanded more than once.
- `test -v A[@]` returns true if associative array A has any set elements. (Bash 5.2: looks for key `@`.)
- `${PARAMETER[:]=VALUE}` returns VALUE before variable-specific transformations. (Bash 5.2: returns the final assigned value.)
- Parsing command substitutions behaves as if extended globbing is enabled, so extglob patterns within do not cause parse failures. (Assumes extglob will be enabled before execution.)

#### `compat52` (set using `BASH_COMPAT`)
- `test` uses its historical algorithm to parse parenthesized subexpressions with 5+ arguments.
- If `-p` or `-P` is supplied to `bind`, remaining arguments are treated as bindable command names (not key sequences), displaying bound key sequences for those commands.
- Interactive shells notify the user of completed jobs while sourcing a script. (Newer versions defer notification until script execution completes.)
