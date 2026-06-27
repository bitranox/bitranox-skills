# Bash 5.3 Reference: Redirections, Executing Commands, and Shell Scripts

Source: GNU Bash 5.3 Reference Manual -- Chapters 3.6, 3.7, 3.8

---

## 3.6 Redirections

Before a command is executed, its input and output may be **redirected** using special notation interpreted by the shell. Redirection allows commands' file handles to be duplicated, opened, closed, made to refer to different files, and can change the files the command reads from and writes to.

### General Rules

- When used with the `exec` builtin, redirections modify file handles in the **current shell execution environment**.
- Redirection operators may **precede** or appear **anywhere within** a simple command, or may **follow** a command.
- Redirections are processed in the order they appear, **from left to right**.
- If the file descriptor number is omitted and the operator starts with `<`, the redirection refers to **stdin (fd 0)**.
- If the file descriptor number is omitted and the operator starts with `>`, the redirection refers to **stdout (fd 1)**.

### WORD Expansion in Redirections

The WORD following a redirection operator (unless otherwise noted) is subjected to:

1. Brace expansion
2. Tilde expansion
3. Parameter and variable expansion
4. Command substitution
5. Arithmetic expansion
6. Quote removal
7. Filename expansion
8. Word splitting

If WORD expands to **more than one word**, Bash reports an error.

### Automatic File Descriptor Allocation with `{VARNAME}`

Each redirection that may be preceded by a file descriptor number may instead be preceded by a word of the form `{VARNAME}`.

| Operator                   | Behavior                                                  |
|----------------------------|-----------------------------------------------------------|
| Any except `>&-` and `<&-` | Shell allocates an fd >= 10 and assigns it to `{VARNAME}` |
| `>&-` or `<&-`             | The value of VARNAME defines the fd to close              |

When `{VARNAME}` is supplied, the redirection **persists beyond the scope of the command**, allowing manual fd lifetime management without `exec`. The `varredir_close` shell option manages this behavior.

```bash
# Automatic fd allocation
exec {myfd}> /tmp/output.txt
echo "hello" >&$myfd
exec {myfd}>&-   # close it

# Equivalent to manually choosing an fd
exec 10> /tmp/output.txt
echo "hello" >&10
exec 10>&-
```

### Redirection Order Matters

```bash
# Redirects BOTH stdout and stderr to DIRLIST
ls > DIRLIST 2>&1

# Redirects ONLY stdout to DIRLIST (stderr goes to original stdout)
ls 2>&1 > DIRLIST
```

In the second example, stderr was made a copy of stdout **before** stdout was redirected to DIRLIST.

### Special Filenames in Redirections

Bash handles the following filenames specially. If the OS provides them, Bash uses them; otherwise Bash emulates them internally.

| Special Filename     | Behavior                                                                                       |
|----------------------|------------------------------------------------------------------------------------------------|
| `/dev/fd/FD`         | Duplicates file descriptor FD (FD must be a valid integer)                                     |
| `/dev/stdin`         | Duplicates file descriptor 0 (stdin)                                                           |
| `/dev/stdout`        | Duplicates file descriptor 1 (stdout)                                                          |
| `/dev/stderr`        | Duplicates file descriptor 2 (stderr)                                                          |
| `/dev/tcp/HOST/PORT` | Opens the corresponding TCP socket (HOST = hostname or IP, PORT = port number or service name) |
| `/dev/udp/HOST/PORT` | Opens the corresponding UDP socket (HOST = hostname or IP, PORT = port number or service name) |

**Warning:** File descriptors greater than 9 should be used with care, as they may conflict with file descriptors the shell uses internally.

A failure to open or create a file causes the redirection to fail.

---

### 3.6.1 Redirecting Input (`<`)

Opens the file for **reading** on file descriptor `n`, or stdin (fd 0) if `n` is not specified.

**Syntax:**

```
[n]<WORD
```

**Examples:**

```bash
# Read from file on stdin
cat < input.txt

# Read from file on fd 3
exec 3< input.txt
read -u 3 line
exec 3<&-
```

---

### 3.6.2 Redirecting Output (`>`, `>|`)

Opens the file for **writing** on file descriptor `n`, or stdout (fd 1) if `n` is not specified. If the file does not exist, it is **created**. If it does exist, it is **truncated to zero size**.

**Syntax:**

```
[n]>[|]WORD
```

| Operator | Behavior                                                                                               |
|----------|--------------------------------------------------------------------------------------------------------|
| `>`      | Redirects output; **fails** if `noclobber` is set and the file exists as a regular file                |
| `>\|`    | Redirects output; **overrides `noclobber`** -- always attempts the redirection even if the file exists |

**Examples:**

```bash
# Basic output redirection (truncates if exists)
echo "hello" > output.txt

# Redirect stderr to a file
command 2> errors.log

# Force overwrite even with noclobber set
set -o noclobber
echo "data" >| protected_file.txt
```

---

### 3.6.3 Appending Redirected Output (`>>`)

Opens the file for **appending** on file descriptor `n`, or stdout (fd 1) if `n` is not specified. If the file does not exist, it is **created**.

**Syntax:**

```
[n]>>WORD
```

**Examples:**

```bash
# Append to a log file
echo "$(date): event occurred" >> app.log

# Append stderr to a file
command 2>> errors.log
```

---

### 3.6.4 Redirecting Standard Output and Standard Error (`&>`, `>&`)

Redirects **both** stdout (fd 1) and stderr (fd 2) to the file whose name is the expansion of WORD.

**Syntax (two forms):**

```
&>WORD        # Preferred form
>&WORD        # Alternate form (see caveats below)
```

**Semantic equivalence:**

```bash
&>WORD
# is equivalent to:
>WORD 2>&1
```

**Caveats for `>&WORD`:** When using the second form (`>&WORD`), WORD may **not** expand to a number or `-`. If it does, the operator is interpreted as a file descriptor duplication operator instead (see Duplicating File Descriptors). This is for compatibility reasons.

**Examples:**

```bash
# Redirect both stdout and stderr to file (preferred)
command &> /tmp/all_output.log

# Equivalent long form
command > /tmp/all_output.log 2>&1

# Discard all output
command &> /dev/null
```

---

### 3.6.5 Appending Standard Output and Standard Error (`&>>`)

**Appends** both stdout (fd 1) and stderr (fd 2) to the file whose name is the expansion of WORD.

**Syntax:**

```
&>>WORD
```

**Semantic equivalence:**

```bash
&>>WORD
# is equivalent to:
>>WORD 2>&1
```

**Examples:**

```bash
# Append all output (stdout + stderr) to log
command &>> /var/log/combined.log
```

---

### 3.6.6 Here Documents (`<<`, `<<-`)

Instructs the shell to read input from the current source until it reads a line containing **only** DELIMITER (with no trailing blanks). All lines read up to that point become stdin (or fd `n` if specified) for the command.

**Syntax:**

```
[n]<<[-]WORD
        HERE-DOCUMENT
DELIMITER
```

**Expansion Rules:**

| WORD Quoting                                         | DELIMITER                       | Here-document body expansion                                                                                                                                                                                                       |
|------------------------------------------------------|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Any part quoted** (e.g., `'EOF'`, `"EOF"`, `\EOF`) | Result of quote removal on WORD | **No expansion** -- lines are literal                                                                                                                                                                                              |
| **Unquoted**                                         | WORD itself                     | Treated like a double-quoted string: parameter expansion, command substitution, arithmetic expansion are performed. `\newline` is literal. `\` must be used to quote `\`, `$`, and `` ` ``. Double quotes have no special meaning. |

**Tab stripping with `<<-`:**

When the operator is `<<-`, the shell strips **leading tab characters** from input lines and the line containing DELIMITER. This allows here-documents within shell scripts to be indented naturally.

**Line continuation:** If the delimiter is not quoted, the `\<newline>` sequence is treated as a line continuation: the two lines are joined and the backslash-newline is removed. This happens while reading the here-document, **before** the check for the ending delimiter, so joined lines can form the end delimiter.

**Examples:**

```bash
# Basic here document (with expansion)
cat <<EOF
Hello, $USER
Today is $(date)
Your home is $HOME
EOF

# Quoted delimiter -- no expansion
cat <<'EOF'
This $variable is not expanded
Neither is $(this command)
EOF

# Tab-stripped here document (<<-)
if true; then
	cat <<-EOF
	This text has leading tabs stripped.
	The delimiter line's tabs are also stripped.
	EOF
fi

# Here document on a specific fd
exec 3<<EOF
Data for fd 3
EOF
read -u 3 line

# Partial quoting also suppresses expansion
cat <<\EOF
No $expansion here either
EOF
```

---

### 3.6.7 Here Strings (`<<<`)

A variant of here documents providing a single string as input.

**Syntax:**

```
[n]<<<WORD
```

**Expansion applied to WORD:**

| Expansion                        | Applied? |
|----------------------------------|----------|
| Tilde expansion                  | Yes      |
| Parameter and variable expansion | Yes      |
| Command substitution             | Yes      |
| Arithmetic expansion             | Yes      |
| Quote removal                    | Yes      |
| Filename expansion               | **No**   |
| Word splitting                   | **No**   |

The result is supplied as a single string, **with a newline appended**, to the command on its stdin (or fd `n` if specified).

**Examples:**

```bash
# Pass a string as stdin
cat <<< "Hello, World"

# With variable expansion
greeting="Hello"
cat <<< "$greeting, World"

# Read into a variable
read -r var <<< "some value"

# Use with word splitting disabled
while IFS=: read -r user pass uid gid desc home shell; do
    echo "$user -> $home"
done <<< "$(getent passwd root)"

# Redirect here string to a specific fd
exec 3<<< "data for fd 3"
```

---

### 3.6.8 Duplicating File Descriptors (`<&`, `>&`)

#### Duplicating Input File Descriptors

**Syntax:**

```
[n]<&WORD
```

| WORD value         | Behavior                                                                                   |
|--------------------|--------------------------------------------------------------------------------------------|
| One or more digits | fd `n` becomes a copy of that fd. Error if the digits do not specify an fd open for input. |
| `-`                | fd `n` is **closed**                                                                       |
| _(n omitted)_      | Defaults to stdin (fd 0)                                                                   |

#### Duplicating Output File Descriptors

**Syntax:**

```
[n]>&WORD
```

| WORD value                               | Behavior                                                                                    |
|------------------------------------------|---------------------------------------------------------------------------------------------|
| One or more digits                       | fd `n` becomes a copy of that fd. Error if the digits do not specify an fd open for output. |
| `-`                                      | fd `n` is **closed**                                                                        |
| _(n omitted)_                            | Defaults to stdout (fd 1)                                                                   |
| _(n omitted, WORD is not digits or `-`)_ | **Special case:** redirects both stdout and stderr (same as `&>WORD`)                       |

**Examples:**

```bash
# Duplicate stdout to stderr
echo "error message" >&2

# Duplicate fd 3 to stdin
exec 0<&3

# Close stdin
exec 0<&-

# Close stdout
exec 1>&-

# Save and restore stdout
exec 3>&1          # save stdout to fd 3
exec 1> output.txt # redirect stdout to file
echo "to file"
exec 1>&3          # restore stdout from fd 3
exec 3>&-          # close fd 3
```

---

### 3.6.9 Moving File Descriptors

#### Moving Input File Descriptors

**Syntax:**

```
[n]<&DIGIT-
```

Moves file descriptor DIGIT to file descriptor `n` (or stdin, fd 0, if `n` is not specified). DIGIT is **closed** after being duplicated to `n`.

#### Moving Output File Descriptors

**Syntax:**

```
[n]>&DIGIT-
```

Moves file descriptor DIGIT to file descriptor `n` (or stdout, fd 1, if `n` is not specified). DIGIT is **closed** after being duplicated to `n`.

**Examples:**

```bash
# Move fd 3 to stdin (fd 3 is closed after)
exec 0<&3-

# Move fd 4 to stdout (fd 4 is closed after)
exec 1>&4-
```

---

### 3.6.10 Opening File Descriptors for Reading and Writing (`<>`)

**Syntax:**

```
[n]<>WORD
```

Opens the file for **both reading and writing** on file descriptor `n`, or on fd 0 if `n` is not specified. If the file does not exist, it is **created**.

**Examples:**

```bash
# Open a file for reading and writing on fd 4
exec 4<> /tmp/data.txt
echo "hello" >&4
# Seek back to beginning would require external tools
exec 4>&-

# Open on stdin (default when n is omitted)
exec <> /tmp/data.txt
```

---

### Redirections Quick Reference Table

| Syntax         | Operation                                   | Default fd |
|----------------|---------------------------------------------|------------|
| `[n]<WORD`     | Redirect input (read from file)             | 0 (stdin)  |
| `[n]>WORD`     | Redirect output (write to file, truncate)   | 1 (stdout) |
| `[n]>\|WORD`   | Redirect output (force, override noclobber) | 1 (stdout) |
| `[n]>>WORD`    | Append output                               | 1 (stdout) |
| `&>WORD`       | Redirect stdout + stderr to file            | 1 + 2      |
| `>&WORD`       | Redirect stdout + stderr to file (alt form) | 1 + 2      |
| `&>>WORD`      | Append stdout + stderr to file              | 1 + 2      |
| `[n]<<[-]WORD` | Here document                               | 0 (stdin)  |
| `[n]<<<WORD`   | Here string                                 | 0 (stdin)  |
| `[n]<&WORD`    | Duplicate input fd                          | 0 (stdin)  |
| `[n]>&WORD`    | Duplicate output fd                         | 1 (stdout) |
| `[n]<&DIGIT-`  | Move input fd (close source)                | 0 (stdin)  |
| `[n]>&DIGIT-`  | Move output fd (close source)               | 1 (stdout) |
| `[n]<>WORD`    | Open for reading and writing                | 0 (stdin)  |
| `[n]<&-`       | Close input fd                              | 0 (stdin)  |
| `[n]>&-`       | Close output fd                             | 1 (stdout) |

---

## 3.7 Executing Commands

### 3.7.1 Simple Command Expansion

When the shell executes a simple command, it performs the following expansions, assignments, and redirections, **from left to right**, in this order:

1. **Save assignments and redirections:** Words marked as variable assignments (those preceding the command name) and redirections are saved for later processing.

2. **Expand non-assignment, non-redirection words:** Words that are not variable assignments or redirections are expanded (Shell Expansions). If any words remain, the **first word** is the command name and the remaining words are the arguments.

3. **Perform redirections:** Redirections are performed as described in the Redirections section.

4. **Process variable assignments:** The text after `=` in each variable assignment undergoes:
   - Tilde expansion
   - Parameter expansion
   - Command substitution
   - Arithmetic expansion
   - Quote removal

#### When No Command Name Results

| Condition                                  | Behavior                                                                                                                           |
|--------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| Only assignments, no command name          | Variable assignments affect the **current shell environment**. Assignment statements are performed **before** redirections.        |
| Only redirections, no command name         | Redirections are performed but do **not** affect the current shell environment. A redirection error causes a non-zero exit status. |
| With a command name                        | Variables are added to the **environment of the executed command** and do not affect the current shell environment.                |
| Readonly variable assignment attempt       | An error occurs and the command exits with a non-zero status.                                                                      |
| No command name, has command substitutions | Exit status is the exit status of the **last command substitution** performed.                                                     |
| No command name, no command substitutions  | Command exits with **zero** status.                                                                                                |

---

### 3.7.2 Command Search and Execution

After a command has been split into words, if it results in a simple command and an optional list of arguments, the shell performs the following actions:

| Step | Condition                                                | Action                                                                                                                                                                                                                                                                                                   |
|------|----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Command name contains **no slashes**                     | Shell attempts to locate the command. If a **shell function** exists by that name, the function is invoked.                                                                                                                                                                                              |
| 2    | Name does not match a function                           | Shell searches the list of **shell builtins**. If a match is found, that builtin is invoked.                                                                                                                                                                                                             |
| 3    | Name is not a function or builtin, contains no slashes   | Bash searches each element of `$PATH` for a directory containing an executable file by that name. Uses a **hash table** to cache full pathnames (see `hash` builtin). Full `$PATH` search only if not found in hash table.                                                                               |
| 3a   | `$PATH` search unsuccessful                              | Shell searches for a function named `command_not_found_handle`. If found, it is invoked in a separate execution environment with the original command and arguments. The function's exit status becomes the subshell's exit status. If not found, shell prints an error and returns exit status **127**. |
| 4    | Search successful, or name contains slashes              | Shell executes the named program in a separate execution environment. Argument 0 is the command name; remaining arguments are passed as supplied.                                                                                                                                                        |
| 5    | Execution fails (not executable format, not a directory) | File is assumed to be a **shell script** and executed as described in Shell Scripts.                                                                                                                                                                                                                     |
| 6    | Command not begun asynchronously                         | Shell **waits** for the command to complete and collects its exit status.                                                                                                                                                                                                                                |

---

### 3.7.3 Command Execution Environment

The shell's **execution environment** consists of:

- **Open files** inherited by the shell at invocation, as modified by redirections supplied to `exec`.
- **Current working directory** as set by `cd`, `pushd`, or `popd`, or inherited at invocation.
- **File creation mode mask** as set by `umask` or inherited from the shell's parent.
- **Current traps** set by `trap`.
- **Shell parameters** set by variable assignment, `set`, or inherited from the parent environment.
- **Shell functions** defined during execution or inherited from the parent environment.
- **Options** enabled at invocation (by default or with command-line arguments) or by `set`.
- **Options** enabled by `shopt`.
- **Shell aliases** defined with `alias`.
- **Various process IDs**, including background jobs, `$$`, and `$PPID`.

#### Separate Execution Environment (for external commands)

When a simple command other than a builtin or shell function is executed, it runs in a **separate execution environment** consisting of (inherited from the shell unless otherwise noted):

- The shell's **open files**, plus modifications/additions from redirections.
- The **current working directory**.
- The **file creation mode mask**.
- Shell **variables and functions marked for export**, plus variables exported for the command, passed in the environment.
- **Traps caught** by the shell are reset to values inherited from the shell's parent. **Traps ignored** by the shell remain ignored.

**Key rule:** A command invoked in this separate environment **cannot affect** the shell's execution environment.

#### Subshell Environment

A **subshell** is a copy of the shell process.

The following are invoked in a subshell environment (a duplicate of the shell environment):

| Construct                                   | Notes                                                                             |
|---------------------------------------------|-----------------------------------------------------------------------------------|
| Command substitution (`$(...)`)             | Traps caught by the shell are reset to values inherited from parent at invocation |
| Commands grouped with parentheses (`(...)`) | Same trap reset behavior                                                          |
| Asynchronous commands (`command &`)         | Same trap reset behavior                                                          |
| Builtin commands in a pipeline              | Except possibly the **last element** (depends on `lastpipe` shell option)         |

**Changes made to the subshell environment cannot affect the shell's execution environment.**

#### POSIX Mode and `-e` Option in Subshells

| Mode           | Behavior                                                                                                   |
|----------------|------------------------------------------------------------------------------------------------------------|
| POSIX mode     | Subshells spawned for command substitution **inherit** the `-e` option from the parent shell               |
| Non-POSIX mode | Bash **clears** the `-e` option in such subshells. Use the `inherit_errexit` shell option to control this. |

#### Asynchronous Commands and Standard Input

If a command is followed by `&` and **job control is not active**, the default stdin for the command is `/dev/null`. Otherwise, the invoked command inherits the file descriptors of the calling shell as modified by redirections.

---

### 3.7.4 Environment

When a program is invoked, it is given an array of strings called the **environment** -- a list of name-value pairs of the form `name=value`.

#### How Bash Manages the Environment

| Action                          | Effect                                                                                                                          |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| Shell invocation                | Bash scans its own environment, creates a parameter for each name found, automatically marks it for `export` to child processes |
| `export VAR` / `declare -x VAR` | Adds or marks a variable for export                                                                                             |
| `unset VAR`                     | Removes a variable from the environment                                                                                         |
| `export -n VAR`                 | Removes the export attribute (variable stays but is not passed to children)                                                     |
| Modifying an exported variable  | New value automatically becomes part of the environment                                                                         |

#### The Inherited Environment of Executed Commands

The environment inherited by any executed command consists of:

1. The shell's **initial environment** (values may be modified in the shell)
2. **Minus** any pairs removed by `unset` and `export -n`
3. **Plus** any additions via `export` and `declare -x`

#### Prefix Assignments Before Commands

```bash
# VAR is part of command's environment only while it executes
VAR=value command arg1 arg2
```

- These variable assignments affect **only the environment seen by that command**.
- If the assignments precede a call to a **shell function**, the variables are **local to the function** and **exported to that function's children**.

#### The `-k` Option

If the `-k` option is set (see `set` builtin), then **all** parameter assignments are placed in the environment for a command, not just those that precede the command name.

```bash
set -k
command arg1 VAR=value arg2  # VAR is in the environment of command
```

#### The `$_` Variable

When Bash invokes an external command, the variable `$_` is set to the full pathname of the command and passed to that command in its environment.

---

### 3.7.5 Exit Status

The exit status of an executed command is the value returned by the `waitpid` system call or equivalent function.

#### Exit Status Ranges and Special Values

| Exit Status | Meaning                                                             |
|-------------|---------------------------------------------------------------------|
| **0**       | Success                                                             |
| **1-125**   | Failure (command-specific meaning)                                  |
| **2**       | Incorrect usage of a builtin (invalid options or missing arguments) |
| **126**     | Command found but **not executable**                                |
| **127**     | Command **not found**                                               |
| **128+N**   | Command terminated by fatal **signal number N**                     |
| **> 125**   | Reserved by the shell for special failure modes                     |

#### Key Rules

- Exit statuses fall between **0 and 255** (though the shell may use values above 125 specially).
- Exit statuses from shell builtins and compound commands are also limited to the 0-255 range.
- A **zero** exit status indicates **success**; a **non-zero** exit status indicates **failure**.
- If a command fails due to an error during **expansion or redirection**, the exit status is greater than zero.
- All Bash builtins return **0** on success and **non-zero** on failure.
- The exit status of the **last command** is available in the special parameter `$?`.
- Bash itself returns the exit status of the **last command executed**, unless a syntax error occurs (exits with non-zero).

**Examples:**

```bash
# Check exit status
command
echo $?      # prints the exit status

# Signal-based exit: killed by SIGKILL (signal 9)
# Exit status would be 128 + 9 = 137

# Command not found
nonexistent_command
echo $?      # prints 127

# Command not executable
chmod -x some_script.sh
./some_script.sh
echo $?      # prints 126
```

---

### 3.7.6 Signals

#### Interactive Shell Signal Handling

| Signal    | Behavior in Interactive Shell                                                       |
|-----------|-------------------------------------------------------------------------------------|
| `SIGTERM` | **Ignored** (so `kill 0` does not kill an interactive shell)                        |
| `SIGINT`  | **Caught and handled** (so `wait` is interruptible). Breaks out of executing loops. |
| `SIGQUIT` | **Ignored** (in all cases)                                                          |
| `SIGTTIN` | **Ignored** (when job control is in effect)                                         |
| `SIGTTOU` | **Ignored** (when job control is in effect)                                         |
| `SIGTSTP` | **Ignored** (when job control is in effect)                                         |

The `trap` builtin modifies the shell's signal handling.

#### Signal Handlers for Child Processes

- Non-builtin commands executed by Bash have signal handlers set to the values **inherited by the shell from its parent**, unless `trap` sets them to be ignored (in which case the child ignores them too).
- When job control is **not** in effect, asynchronous commands ignore `SIGINT` and `SIGQUIT` in addition to inherited handlers.
- Commands run via **command substitution** ignore the keyboard-generated job control signals: `SIGTTIN`, `SIGTTOU`, `SIGTSTP`.

#### SIGHUP Handling

| Event                              | Behavior                                                                              |
|------------------------------------|---------------------------------------------------------------------------------------|
| Shell receives `SIGHUP`            | Shell exits by default                                                                |
| Before exiting (interactive shell) | Resends `SIGHUP` to all jobs (running or stopped)                                     |
| Stopped jobs                       | Shell sends `SIGCONT` first to ensure they receive the `SIGHUP`                       |
| Prevent `SIGHUP` to a job          | Use `disown` (removes from jobs table) or `disown -h` (marks to not receive `SIGHUP`) |
| `huponexit` shell option set       | Bash sends `SIGHUP` to all jobs when an interactive login shell exits                 |

#### Trap Execution Timing

- If Bash is **waiting for a command** to complete and receives a signal with a trap set, the trap is **not executed until the command completes**.
- If Bash is waiting for an asynchronous command via `wait`, and receives a trapped signal, `wait` returns immediately with an exit status **greater than 128**, and then the trap is executed.

#### SIGINT Behavior When Waiting for Foreground Commands

**When job control is NOT enabled** (most common in non-interactive shells):

The shell and the command are in the **same process group** as the terminal, so `^C` sends `SIGINT` to all processes in that group.

When Bash receives `SIGINT` while waiting for a foreground command, it waits until the command terminates, then:

| Scenario | Condition                                    | Bash Behavior                                                                                                                                                             |
|----------|----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1        | Command **terminates due to SIGINT**         | Bash concludes the user intended SIGINT for the shell too. Acts on it: runs SIGINT trap, exits a non-interactive shell, or returns to top level.                          |
| 2        | Command **does not terminate due to SIGINT** | Bash assumes the program handled SIGINT as normal operation (e.g., `emacs` abort). Bash does not treat SIGINT as fatal, but still runs any SIGINT trap for compatibility. |

**When job control IS enabled** (most common in interactive shells):

- Bash is in a **different process group** from the terminal, so it does **not receive** keyboard-generated signals while waiting for a foreground command.
- An interactive shell does not pay attention to `SIGINT` even if the foreground command terminates as a result (other than noting its exit status).
- A **non-interactive shell** with job control enabled: if the foreground command terminates due to `SIGINT`, Bash pretends it received the `SIGINT` itself (scenario 1 above), for compatibility.

---

## 3.8 Shell Scripts

A shell script is a text file containing shell commands.

### Invocation

When a file is used as the **first non-option argument** when invoking Bash, and neither `-c` nor `-s` is supplied:

1. Bash reads and executes commands from the file, then exits.
2. This creates a **non-interactive shell**.
3. If the filename contains **no slashes**, the shell first searches the **current directory**, then looks in `$PATH`.

### Binary Detection

Bash tries to determine whether the file is a text file or a binary, and **will not execute files it determines to be binaries**.

### Parameter Setup

| Parameter        | Value                                                          |
|------------------|----------------------------------------------------------------|
| `$0`             | Set to the name of the script file (not the name of the shell) |
| `$1`, `$2`, ...  | Set to the remaining arguments, if any                         |
| _(no arguments)_ | Positional parameters are **unset**                            |

### Making Scripts Executable

A shell script may be made executable using `chmod` to turn on the execute bit. When Bash finds such a file while searching `$PATH`:

```bash
# These are equivalent:
filename ARGUMENTS
bash filename ARGUMENTS
```

The subshell reinitializes itself so the effect is as if a new shell had been invoked, **except** that command locations remembered by the parent (via `hash`) are retained by the child.

### The `#!` (Shebang) Line

If the first line of a script begins with `#!`, the remainder of the line specifies an **interpreter** for the program and, depending on the OS, one or more optional arguments for that interpreter.

**Interpreter argument processing order:**

1. Optional arguments following the interpreter name on the first line
2. The name of the script file
3. The rest of the arguments supplied to the script

**Portability note:** Some older versions of Unix limit the interpreter name and a single argument to a maximum of **32 characters**. It is not portable to assume that using more than one argument will work.

Bash will perform shebang handling on operating systems that do not handle it themselves.

### Common Shebang Patterns

```bash
#!/bin/bash
# Ensures Bash is used (assumes Bash is installed in /bin)

#!/usr/bin/env bash
# Common idiom: uses env to find bash in $PATH
# More portable -- works regardless of where bash is installed
```

### Best Practices Summary

| Practice                      | Reason                                                                         |
|-------------------------------|--------------------------------------------------------------------------------|
| Always include a shebang line | Ensures the correct interpreter is used even when executed under another shell |
| Use `#!/usr/bin/env bash`     | More portable than hardcoding `/bin/bash`                                      |
| Use `chmod +x script.sh`      | Makes the script directly executable                                           |
| Set `$0` to the script name   | Allows the script to know its own name for error messages                      |
