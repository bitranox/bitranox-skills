# Bash 5.3 Reference: Shell Syntax and Commands

> Extracted from the GNU Bash 5.3 Reference Manual -- Chapters 3.1 and 3.2

---

## 3.1 Shell Syntax

When the shell reads input, it proceeds through a sequence of operations. If the input indicates the beginning of a comment, the shell ignores the comment symbol (`#`) and the rest of that line.

Otherwise, the shell reads its input and divides it into words and operators, employing the quoting rules to select which meanings to assign various words and characters.

The shell then parses these tokens into commands and other constructs, removes the special meaning of certain words or characters, expands others, redirects input and output as needed, executes the specified command, waits for the command's exit status, and makes that exit status available for further inspection or processing.

---

### 3.1.1 Shell Operation

The shell performs the following steps when it reads and executes a command:

| Step | Operation                                                                                                                                                |
|------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Reads input from a file (shell script), from a string supplied via the `-c` invocation option, or from the user's terminal.                              |
| 2    | Breaks the input into words and operators, obeying quoting rules. Tokens are separated by **metacharacters**. Alias expansion is performed at this step. |
| 3    | Parses the tokens into **simple commands** and **compound commands**.                                                                                    |
| 4    | Performs shell expansions, breaking expanded tokens into lists of filenames, commands, and arguments.                                                    |
| 5    | Performs any necessary **redirections** and removes redirection operators and their operands from the argument list.                                     |
| 6    | **Executes** the command.                                                                                                                                |
| 7    | Optionally **waits** for the command to complete and collects its **exit status**.                                                                       |

---

### 3.1.2 Quoting

Quoting removes the special meaning of certain characters or words to the shell. Quoting can be used to:

- Disable special treatment for special characters.
- Prevent reserved words from being recognized as such.
- Prevent parameter expansion.

Each shell **metacharacter** has special meaning and must be quoted to represent itself literally.

When command history expansion is enabled, the history expansion character (usually `!`) must be quoted to prevent history expansion.

There are **four quoting mechanisms**:

1. Escape character
2. Single quotes
3. Double quotes
4. Dollar-single quotes (ANSI-C quoting)

#### 3.1.2.1 Escape Character

A non-quoted backslash `\` is the Bash escape character. It preserves the literal value of the next character that follows, removing any special meaning, **with the exception of newline**.

If a `\newline` pair appears and the backslash itself is not quoted, the `\newline` is treated as a **line continuation** -- it is removed from the input stream and effectively ignored.

```bash
# Escape a space in a filename
ls my\ file.txt

# Line continuation
echo "this is a \
long command"
```

#### 3.1.2.2 Single Quotes

Enclosing characters in single quotes (`'...'`) preserves the **literal value of each character** within the quotes. A single quote **may not occur** between single quotes, even when preceded by a backslash.

```bash
echo 'Hello $USER'       # prints: Hello $USER (no expansion)
echo 'It'\''s a test'    # workaround: end quote, escaped quote, start quote
```

#### 3.1.2.3 Double Quotes

Enclosing characters in double quotes (`"..."`) preserves the literal value of all characters within the quotes, **with the following exceptions**:

| Character | Behavior inside double quotes                                                                                                                                                                      |
|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `$`       | Retains its special meaning (expansions)                                                                                                                                                           |
| `` ` ``   | Retains its special meaning (command substitution)                                                                                                                                                 |
| `\`       | Retains special meaning **only** when followed by: `$`, `` ` ``, `"`, `\`, or `newline`. Backslashes before these characters are removed. Backslashes before other characters are left unmodified. |
| `!`       | Retains special meaning when history expansion is enabled (except in POSIX mode)                                                                                                                   |

A double quote may be quoted within double quotes by preceding it with a backslash:

```bash
echo "She said \"hello\""
```

If enabled, history expansion will be performed unless `!` is escaped with a backslash. The backslash preceding `!` is **not** removed.

The special parameters `*` and `@` have special meaning when in double quotes (see Shell Parameter Expansion).

#### 3.1.2.4 ANSI-C Quoting

Character sequences of the form `$'STRING'` are treated as a special kind of single quotes. The sequence expands to STRING with backslash-escaped characters replaced as specified by the ANSI C standard.

| Escape Sequence | Meaning                                                               |
|-----------------|-----------------------------------------------------------------------|
| `\a`            | Alert (bell)                                                          |
| `\b`            | Backspace                                                             |
| `\e`, `\E`      | Escape character (not in ANSI C)                                      |
| `\f`            | Form feed                                                             |
| `\n`            | Newline                                                               |
| `\r`            | Carriage return                                                       |
| `\t`            | Horizontal tab                                                        |
| `\v`            | Vertical tab                                                          |
| `\\`            | Backslash                                                             |
| `\'`            | Single quote                                                          |
| `\"`            | Double quote                                                          |
| `\?`            | Question mark                                                         |
| `\NNN`          | Eight-bit character with octal value NNN (one to three octal digits)  |
| `\xHH`          | Eight-bit character with hexadecimal value HH (one or two hex digits) |
| `\uHHHH`        | Unicode character with hex value HHHH (one to four hex digits)        |
| `\UHHHHHHHH`    | Unicode character with hex value HHHHHHHH (one to eight hex digits)   |
| `\cX`           | A control-X character                                                 |

The expanded result is single-quoted, as if the dollar sign had not been present.

```bash
echo $'\t'          # horizontal tab
echo $'\e[31mRed\e[0m'   # ANSI color escape
echo $'\x41'        # prints: A
echo $'\u00e9'      # prints: e with acute accent
```

#### 3.1.2.5 Locale-Specific Translation

Prefixing a double-quoted string with a dollar sign (`$"hello, world"`) causes the string to be **translated according to the current locale**. The `gettext` infrastructure performs the lookup and translation, using the following shell variables:

| Variable        | Purpose                                                   |
|-----------------|-----------------------------------------------------------|
| `LC_MESSAGES`   | Selects the desired language                              |
| `TEXTDOMAIN`    | The script's message domain (arbitrary identifier string) |
| `TEXTDOMAINDIR` | Directory where message catalog files are stored          |

If the current locale is `C` or `POSIX`, if there are no translations available, or if the string is not translated, the dollar sign is ignored and the string is treated as a regular double-quoted string.

Since this is a form of double quoting, the string remains double-quoted by default, whether or not it is translated and replaced. If the `noexpand_translation` option is enabled using `shopt`, translated strings are single-quoted instead of double-quoted.

**Creating translations for a shell script:**

1. Mark translatable strings in your script using `$"..."`.
2. Create a gettext template file:
   ```bash
   bash --dump-po-strings SCRIPTNAME > DOMAIN.pot
   ```
3. Copy the template to a PO file for each target language:
   ```bash
   cp example.pot es.po    # Spanish translations
   ```
4. Manually translate the strings in the PO files.
5. Compile PO files to MO (message catalog) files:
   ```bash
   msgfmt -o es.mo es.po
   ```
6. Install MO files in the correct directory structure:
   ```bash
   TEXTDOMAIN=example
   TEXTDOMAINDIR=/usr/local/share/locale
   cp es.mo ${TEXTDOMAINDIR}/es/LC_MESSAGES/${TEXTDOMAIN}.mo
   ```

Common directory convention: `$TEXTDOMAINDIR/$LC_MESSAGES/LC_MESSAGES/$TEXTDOMAIN.mo`

Users select the desired language by setting the `LANG` or `LC_MESSAGES` environment variables before running the script.

---

### 3.1.3 Comments

In a **non-interactive** shell, or an interactive shell with the `interactive_comments` option enabled (via `shopt`), a word beginning with `#` introduces a comment.

A word begins at:
- The beginning of a line
- After unquoted whitespace
- After an operator

The `#` and all remaining characters on that line are ignored.

An interactive shell **without** `interactive_comments` enabled does not allow comments. The `interactive_comments` option is **enabled by default** in interactive shells.

```bash
echo "hello"   # This is a comment
# This entire line is a comment
```

---

## 3.2 Shell Commands

A simple shell command such as `echo a b c` consists of the command itself followed by arguments, separated by spaces.

More complex shell commands are composed of simple commands arranged together in a variety of ways: in a pipeline, in a loop or conditional construct, or in some other grouping.

---

### 3.2.1 Reserved Words

Reserved words are words that have special meaning to the shell. They are used to begin and end the shell's compound commands.

The following words are recognized as reserved when **unquoted** and the **first word** of a command (see below for exceptions):

|        |        |          |          |            |        |
|--------|--------|----------|----------|------------|--------|
| `if`   | `then` | `elif`   | `else`   | `fi`       | `time` |
| `for`  | `in`   | `until`  | `while`  | `do`       | `done` |
| `case` | `esac` | `coproc` | `select` | `function` |        |
| `{`    | `}`    | `[[`     | `]]`     | `!`        |        |

**Exceptions for positional recognition:**

- `in` is recognized as reserved if it is the **third word** of a `case` or `select` command.
- `in` and `do` are recognized as reserved if they are the **third word** in a `for` command.

---

### 3.2.2 Simple Commands

A simple command is the kind of command executed most often. It is a sequence of words separated by **blanks**, terminated by one of the shell's **control operators**.

- The **first word** generally specifies a command to be executed.
- The remaining words are that command's **arguments**.

**Return status:** The exit status as provided by the POSIX 1003.1 `waitpid` function, or **128+N** if the command was terminated by signal N.

```bash
ls -la /tmp
grep -r "pattern" ./src
```

---

### 3.2.3 Pipelines

A pipeline is a sequence of one or more commands separated by the control operators `|` or `|&`.

**Syntax:**

```
[time [-p]] [!] COMMAND1 [ | or |& COMMAND2 ] ...
```

**How pipes work:**

- The output of each command is connected via a pipe to the input of the next command.
- Each command reads the previous command's output.
- The connection is performed **before** any redirections specified by COMMAND1.

#### The `|&` Operator

If `|&` is the pipeline operator, COMMAND1's **standard error**, in addition to its standard output, is connected to COMMAND2's standard input through the pipe. It is shorthand for `2>&1 |`.

This implicit redirection of stderr to stdout is performed **after** any redirections specified by COMMAND1, consistent with the `2>&1 |` shorthand.

```bash
# Standard pipe
ls /nonexistent | grep "error"      # stderr not piped

# Pipe both stdout and stderr
ls /nonexistent |& grep "error"     # stderr IS piped
# equivalent to:
ls /nonexistent 2>&1 | grep "error"
```

#### The `time` Reserved Word

When `time` precedes the pipeline, Bash prints **timing statistics** once the pipeline finishes:

- Elapsed (wall-clock) time
- User time consumed
- System time consumed

| Option / Detail       | Description                                                                                 |
|-----------------------|---------------------------------------------------------------------------------------------|
| `-p`                  | Changes output format to POSIX-specified format                                             |
| `TIMEFORMAT` variable | Format string controlling how timing information is displayed                               |
| POSIX mode behavior   | `time` is not recognized as a reserved word if the next token begins with `-`               |
| POSIX mode standalone | `time` by itself displays total user and system time consumed by the shell and its children |

`time` as a reserved word permits timing of **shell builtins**, **shell functions**, and **pipelines** -- an external `time` command cannot time these easily.

```bash
time sleep 2
time -p find / -name "*.log" 2>/dev/null
```

#### Subshells in Pipelines

Each command in a multi-command pipeline (where pipes are created) is executed in its own **subshell** (a separate process).

**Exception:** If the `lastpipe` option is enabled using `shopt` **and** job control is not active, the **last element** of a pipeline may be run by the shell process (not in a subshell).

```bash
# Without lastpipe: variable set in subshell, lost after pipeline
echo "hello" | read var
echo "$var"    # empty

# With lastpipe enabled (and job control off):
shopt -s lastpipe
echo "hello" | read var
echo "$var"    # hello
```

#### Pipeline Exit Status

| Condition                              | Exit status                                                                                                         |
|----------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| Default                                | Exit status of the **last command** in the pipeline                                                                 |
| `pipefail` enabled (`set -o pipefail`) | Value of the **last (rightmost) command to exit with a non-zero status**, or zero if all commands exit successfully |
| `!` precedes the pipeline              | **Logical negation** of the exit status described above                                                             |
| Asynchronous pipeline                  | Always **0**                                                                                                        |

If a pipeline is not executed asynchronously, the shell waits for **all commands** in the pipeline to terminate before returning a value.

```bash
# Default: exit status of last command
false | true
echo $?    # 0

# With pipefail: catches earlier failures
set -o pipefail
false | true
echo $?    # 1

# Negation
! false | true
echo $?    # 1 (negation of 0)
```

---

### 3.2.4 Lists of Commands

A **list** is a sequence of one or more pipelines separated by one of the operators `;`, `&`, `&&`, or `||`, and optionally terminated by `;`, `&`, or a newline.

#### Operator Precedence

| Precedence | Operators                        |
|------------|----------------------------------|
| Higher     | `&&`, `||` (equal to each other) |
| Lower      | `;`, `&` (equal to each other)   |

A sequence of one or more newlines may appear in a list to delimit commands, equivalent to a semicolon.

#### Operator Details

##### `;` -- Sequential Execution

Commands separated by `;` are executed **sequentially**; the shell waits for each command to terminate in turn. The return status is the exit status of the **last command** executed.

```bash
echo "first"; echo "second"; echo "third"
```

##### `&` -- Asynchronous Execution (Background)

If a command is terminated by `&`, the shell executes the command **asynchronously in a subshell** (in the background).

- The shell **does not wait** for the command to finish.
- The return status is **0** (true).
- When job control is not active, the standard input for asynchronous commands (in the absence of explicit redirections) is redirected from `/dev/null`.

```bash
long_running_task &
echo "This runs immediately"
```

##### `&&` -- AND List

```
COMMAND1 && COMMAND2
```

COMMAND2 is executed **if, and only if**, COMMAND1 returns an exit status of **zero** (success). Executed with **left associativity**.

```bash
mkdir /tmp/test && cd /tmp/test && echo "Success"
```

##### `||` -- OR List

```
COMMAND1 || COMMAND2
```

COMMAND2 is executed **if, and only if**, COMMAND1 returns a **non-zero** exit status (failure). Executed with **left associativity**.

```bash
cd /nonexistent || echo "Directory not found"
```

The return status of AND and OR lists is the exit status of the **last command executed** in the list.

---

### 3.2.5 Compound Commands

Compound commands are the shell programming language constructs. Each construct begins with a **reserved word or control operator** and is terminated by a corresponding reserved word or operator.

**Key properties:**

- Any **redirections** associated with a compound command apply to **all commands within** that compound command unless explicitly overridden.
- In most cases, a list of commands in a compound command's description may be separated from the rest of the command by one or more **newlines**, and may be followed by a newline in place of a semicolon.

Bash provides:
- **Looping constructs**
- **Conditional commands**
- **Mechanisms to group commands** and execute them as a unit

---

#### 3.2.5.1 Looping Constructs

Wherever a `;` appears in the syntax descriptions below, it may be replaced with one or more **newlines**.

Use the `break` and `continue` builtins to control loop execution.

##### `until`

```bash
until TEST-COMMANDS; do CONSEQUENT-COMMANDS; done
```

Execute CONSEQUENT-COMMANDS as long as TEST-COMMANDS has an exit status which is **not zero** (i.e., loop while the test fails).

**Return status:** Exit status of the last command executed in CONSEQUENT-COMMANDS, or **zero** if none was executed.

```bash
count=0
until [ $count -ge 5 ]; do
    echo "Count: $count"
    ((count++))
done
```

##### `while`

```bash
while TEST-COMMANDS; do CONSEQUENT-COMMANDS; done
```

Execute CONSEQUENT-COMMANDS as long as TEST-COMMANDS has an exit status of **zero** (i.e., loop while the test succeeds).

**Return status:** Exit status of the last command executed in CONSEQUENT-COMMANDS, or **zero** if none was executed.

```bash
count=0
while [ $count -lt 5 ]; do
    echo "Count: $count"
    ((count++))
done

# Reading lines from a file
while IFS= read -r line; do
    echo "$line"
done < input.txt
```

##### `for` (Standard Form)

```bash
for NAME [ [in WORDS ...] ; ] do COMMANDS; done
```

Expand WORDS, then execute COMMANDS once for each word in the resultant list, with NAME bound to the current word.

- If `in WORDS` is **not present**, the `for` command executes COMMANDS once for each **positional parameter** that is set, as if `in "$@"` had been specified.
- **Return status:** Exit status of the last command that executes. If there are no items in the expansion of WORDS, no commands are executed and the return status is **zero**.

```bash
for file in *.txt; do
    echo "Processing: $file"
done

for arg; do    # equivalent to: for arg in "$@"; do
    echo "Argument: $arg"
done
```

##### `for` (C-style / Arithmetic Form)

```bash
for (( EXPR1 ; EXPR2 ; EXPR3 )) [;] do COMMANDS; done
```

1. First, evaluate the arithmetic expression EXPR1.
2. Repeatedly evaluate EXPR2 until it evaluates to **zero**.
3. Each time EXPR2 evaluates to a **non-zero** value, execute COMMANDS and evaluate EXPR3.
4. If any expression is omitted, it behaves as if it evaluates to **1**.

**Return value:** Exit status of the last command in COMMANDS that is executed, or non-zero if any of the expressions is invalid.

```bash
for (( i=0; i<10; i++ )); do
    echo "Iteration: $i"
done

for (( ;; )); do    # infinite loop (all expressions omitted, default to 1)
    echo "forever"
    break
done
```

##### `select`

```bash
select NAME [in WORDS ...]; do COMMANDS; done
```

The `select` construct allows easy generation of **menus**. It has almost the same syntax as the `for` command.

**How it works:**

1. Expand the list of words following `in`, generating a list of items.
2. Print the expanded words on **standard error**, each preceded by a number.
3. If `in WORDS` is omitted, print the **positional parameters** (as if `in "$@"` had been specified).
4. Display the `PS3` prompt and read a line from standard input.
5. If the line consists of a number corresponding to one of the displayed words, set NAME to that word.
6. If the line is **empty**, display the words and prompt again.
7. If **EOF** is read, `select` completes and returns **1**.
8. Any other value read causes NAME to be set to **null**.
9. The line read is saved in the variable `REPLY`.
10. COMMANDS are executed after each selection until a `break` command is executed.

```bash
select fname in *; do
    echo "You picked $fname ($REPLY)"
    break
done
```

---

#### 3.2.5.2 Conditional Constructs

##### `if`

```bash
if TEST-COMMANDS; then
    CONSEQUENT-COMMANDS;
[elif MORE-TEST-COMMANDS; then
    MORE-CONSEQUENTS;]
[else ALTERNATE-CONSEQUENTS;]
fi
```

1. Execute TEST-COMMANDS list.
2. If return status is **zero**, execute CONSEQUENT-COMMANDS.
3. If return status is non-zero, execute each `elif` list in turn; if its exit status is zero, execute the corresponding MORE-CONSEQUENTS and complete.
4. If `else ALTERNATE-CONSEQUENTS` is present and the final command in the final `if` or `elif` clause has a non-zero exit status, execute ALTERNATE-CONSEQUENTS.

**Return status:** Exit status of the last command executed, or **zero** if no condition tested true.

```bash
if [ -f "$file" ]; then
    echo "File exists"
elif [ -d "$file" ]; then
    echo "Directory exists"
else
    echo "Not found"
fi
```

##### `case`

```bash
case WORD in
    [ [(] PATTERN [| PATTERN]...) COMMAND-LIST ;;]...
esac
```

`case` selectively executes the COMMAND-LIST corresponding to the **first PATTERN that matches WORD**, proceeding from the first pattern to the last.

**Pattern matching rules:**

- The match follows Pattern Matching rules.
- If the `nocasematch` shell option is enabled (via `shopt`), the match is case-insensitive.
- `|` separates multiple patterns in a pattern list.
- `)` terminates the pattern list.
- A pattern list and its associated COMMAND-LIST is known as a **clause**.
- `*` as the final pattern defines the default case (always matches).

**Expansions applied to WORD:** tilde expansion, parameter expansion, command substitution, process substitution, arithmetic expansion, and quote removal.

**Expansions applied to each PATTERN:** tilde expansion, parameter expansion, command substitution, arithmetic expansion, process substitution, and quote removal.

**Clause terminators:**

| Terminator | Behavior                                                                                                                                     |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `;;`       | Completes the `case` command after the first match (standard behavior).                                                                      |
| `;&`       | **Fall-through:** continues execution with the COMMAND-LIST of the **next clause** (without testing its pattern).                            |
| `;;&`      | **Test-next:** tests the patterns in the **next clause** and executes its COMMAND-LIST if the match succeeds, continuing the case statement. |

**Return status:** Zero if no pattern matches. Otherwise, the exit status of the last COMMAND-LIST executed.

```bash
case $ANIMAL in
    horse | dog | cat) echo "four legs";;
    man | kangaroo)    echo "two legs";;
    *)                 echo "unknown";;
esac

# Fall-through with ;&
case $val in
    1) echo "one";&
    2) echo "two";;     # also prints "two" if val=1
    3) echo "three";;
esac

# Test-next with ;;&
case $val in
    *a*) echo "contains a";;&
    *b*) echo "contains b";;&
    *c*) echo "contains c";;
esac
```

##### `(( ))` -- Arithmetic Evaluation

```bash
(( EXPRESSION ))
```

The arithmetic EXPRESSION is evaluated according to Shell Arithmetic rules.

- The EXPRESSION undergoes the same expansions as if it were within double quotes, but **unescaped double quote characters** in EXPRESSION are not treated specially and are removed.
- Empty strings (potentially resulting from expansion) are treated as expressions that evaluate to **0**.
- If the value of the expression is **non-zero**, the return status is **0** (true).
- If the value of the expression is **zero**, the return status is **1** (false).

```bash
(( x = 5 + 3 ))
echo $x          # 8

if (( x > 5 )); then
    echo "x is greater than 5"
fi

(( count++ ))    # increment
```

##### `[[ ]]` -- Conditional Expression

```bash
[[ EXPRESSION ]]
```

Evaluate the conditional expression EXPRESSION and return a status of **zero** (true) or **non-zero** (false).

**Key properties:**

- Words between `[[` and `]]` do **not** undergo word splitting or filename expansion.
- The shell **does** perform: tilde expansion, parameter and variable expansion, arithmetic expansion, command substitution, process substitution, and quote removal.
- Conditional operators such as `-f` must be **unquoted** to be recognized as primaries.

**String comparison operators:**

| Operator  | Behavior                                                                                                             |
|-----------|----------------------------------------------------------------------------------------------------------------------|
| `==`, `=` | Pattern match (right side is a pattern, as if `extglob` were enabled). Returns 0 if match. `=` is identical to `==`. |
| `!=`      | Negated pattern match. Returns 0 if no match.                                                                        |
| `<`       | Lexicographic less-than (using current locale).                                                                      |
| `>`       | Lexicographic greater-than (using current locale).                                                                   |
| `=~`      | POSIX extended regular expression match (see below).                                                                 |

If the `nocasematch` shell option is enabled, `==`, `!=`, and `=~` matches are **case-insensitive**.

**Quoting the pattern:** If you quote any part of the pattern (right-hand side of `==`, `!=`, or `=~`), the quoted portion is matched **literally** instead of as a pattern or regex.

**The `=~` operator (regex matching):**

- The string to the right is a **POSIX extended regular expression** (matched using `regcomp`/`regexec`).
- Returns **0** if the string matches, **1** if it does not, **2** if the regex is syntactically incorrect.
- The match succeeds if the pattern matches **any part** of the string. Use `^` and `$` anchors to force a full-string match.

```bash
[[ $line =~ [[:space:]]*(a)?b ]]    # regex match
[[ $line =~ ^"initial string" ]]     # anchored with literal portion

# Store regex in a variable to avoid quoting issues
pattern='[[:space:]]*(a)?b'
[[ $line =~ $pattern ]]
```

**`BASH_REMATCH` array:**

- `BASH_REMATCH[0]` contains the portion of the string matching the **entire** regular expression.
- `BASH_REMATCH[N]` contains the portion matching the **Nth parenthesized subexpression**.
- Bash sets `BASH_REMATCH` in the **global scope**; declaring it as a local variable will lead to unexpected results.

```bash
if [[ "2025-01-15" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})$ ]]; then
    echo "Year:  ${BASH_REMATCH[1]}"
    echo "Month: ${BASH_REMATCH[2]}"
    echo "Day:   ${BASH_REMATCH[3]}"
fi
```

**Regex quoting pitfalls:**

Backslashes are used by both the shell and regex to remove special meaning. After shell expansion, unquoted backslashes remaining in the pattern can remove the special meaning of regex characters.

```bash
pattern='\.'

[[ . =~ $pattern ]]     # MATCHES: pattern is \. (regex literal dot)
[[ . =~ \. ]]           # MATCHES: same -- shell passes \. to regex

[[ . =~ "$pattern" ]]   # DOES NOT MATCH: pattern is \\. (literal backslash + any char)
[[ . =~ '\.' ]]         # DOES NOT MATCH: same -- quoted, so backslash is literal

# Bracket expressions can match special characters without quoting:
[[ . =~ [.] ]]          # MATCHES: dot in bracket is literal
```

**Compound expressions in `[[ ]]`** (listed in decreasing precedence):

| Expression                     | Meaning                                                       |
|--------------------------------|---------------------------------------------------------------|
| `( EXPRESSION )`               | Returns the value of EXPRESSION. Overrides normal precedence. |
| `! EXPRESSION`                 | True if EXPRESSION is false.                                  |
| `EXPRESSION1 && EXPRESSION2`   | True if both are true.                                        |
| `EXPRESSION1 \|\| EXPRESSION2` | True if either is true.                                       |

The `&&` and `||` operators use **short-circuit evaluation**: EXPRESSION2 is not evaluated if EXPRESSION1 is sufficient to determine the result.

```bash
[[ -f "$file" && -r "$file" ]]       # file exists AND is readable
[[ -z "$var" || "$var" == "default" ]]  # var is empty OR equals "default"
[[ ! -d "$dir" ]]                     # directory does NOT exist
```

---

#### 3.2.5.3 Grouping Commands

Bash provides two ways to group a list of commands to be executed as a unit. When commands are grouped, redirections may be applied to the entire command list.

##### `()` -- Subshell Group

```bash
( LIST )
```

Placing a list of commands between parentheses forces the shell to create a **subshell**, and each of the commands in LIST is executed in that subshell environment. Since LIST is executed in a subshell, **variable assignments do not remain in effect** after the subshell completes.

The parentheses are **operators** and are recognized as separate tokens even without whitespace separation from the list.

```bash
(cd /tmp && tar cf archive.tar .)   # cd does not affect parent shell
echo "Still in: $PWD"

# Redirect all output from a group
( echo "stdout"; echo "stderr" >&2 ) > output.log 2>&1
```

##### `{}` -- Current Shell Group

```bash
{ LIST; }
```

Placing a list of commands between curly braces causes the list to be executed in the **current shell environment**. No subshell is created.

**Important syntax requirements:**

- The **semicolon** (or newline) following LIST is **required**.
- The braces are **reserved words**, so they must be separated from LIST by **blanks** or other shell metacharacters.

```bash
{ echo "one"; echo "two"; echo "three"; } > output.txt
# All three echo commands write to output.txt

# Variable assignments persist:
{ x=42; y=99; }
echo "$x $y"    # 42 99
```

**Key differences between `()` and `{}`:**

| Feature               | `( LIST )`                               | `{ LIST; }`                                          |
|-----------------------|------------------------------------------|------------------------------------------------------|
| Execution environment | Subshell (separate process)              | Current shell                                        |
| Variable persistence  | No (lost after subshell exits)           | Yes                                                  |
| Syntax                | Operators; no whitespace or `;` required | Reserved words; whitespace and trailing `;` required |
| Exit status           | Exit status of LIST                      | Exit status of LIST                                  |

---

### 3.2.6 Coprocesses

A **coprocess** is a shell command preceded by the `coproc` reserved word. A coprocess is executed **asynchronously in a subshell**, as if terminated with the `&` control operator, with a **two-way pipe** established between the executing shell and the coprocess.

**Syntax:**

```bash
coproc [NAME] COMMAND [REDIRECTIONS]
```

This creates a coprocess named NAME. COMMAND may be either a simple command or a compound command. NAME is a shell variable name. If NAME is not supplied, the default name is `COPROC`.

**Recommended form:**

```bash
coproc NAME { COMMAND; }
```

This form is preferred because simple commands always result in the coprocess being named `COPROC`, and this form is simpler and more complete than other compound commands.

**Other valid forms:**

```bash
coproc NAME COMPOUND-COMMAND
coproc COMPOUND-COMMAND
coproc SIMPLE-COMMAND
```

**NAME rules:**

- If COMMAND is a **compound command**, NAME is optional. The word following `coproc` is interpreted as NAME if it is not a reserved word that introduces a compound command.
- If COMMAND is a **simple command**, NAME is **not allowed** (to avoid confusion between NAME and the first word of the simple command).

**File descriptor array:**

When the coprocess is executed, the shell creates an **array variable** named NAME in the context of the executing shell:

| Array Element | Connected To                                                                          |
|---------------|---------------------------------------------------------------------------------------|
| `NAME[0]`     | File descriptor connected to the **standard output** of COMMAND (read from coprocess) |
| `NAME[1]`     | File descriptor connected to the **standard input** of COMMAND (write to coprocess)   |

This pipe is established **before** any redirections specified by the command. The file descriptors can be used as arguments to shell commands and redirections using standard word expansions. The file descriptors are **not available in subshells** (other than those created for command and process substitutions).

**Process ID:**

The PID of the shell spawned to execute the coprocess is available as the variable `NAME_PID`. The `wait` builtin may be used to wait for the coprocess to terminate.

**Return status:**

Since the coprocess is created as an asynchronous command, `coproc` always returns **success** (0). The return status of the coprocess itself is the exit status of COMMAND.

```bash
# Start a coprocess running bc (calculator)
coproc BC { bc -l; }

# Send a calculation
echo "scale=4; 22/7" >&${BC[1]}

# Read the result
read result <&${BC[0]}
echo "Result: $result"    # 3.1428

# Get the PID
echo "Coprocess PID: $BC_PID"

# Close the input to signal EOF
exec {BC[1]}>&-

# Wait for it to finish
wait $BC_PID
```

---

### 3.2.7 GNU Parallel

There are ways to run commands in parallel that are not built into Bash. **GNU Parallel** is a tool to do just that.

GNU Parallel can be used to build and run commands in parallel. You may run the same command with different arguments, whether they are filenames, usernames, hostnames, or lines read from files.

**Capabilities:**

- Shorthand references to many common operations (input lines, various portions of the input line, different input sources).
- Can replace `xargs` or feed commands from its input sources to several different instances of Bash.

**Documentation:** <https://www.gnu.org/software/parallel/parallel_tutorial.html>

```bash
# Run gzip on all .log files, 4 jobs at a time
parallel -j4 gzip ::: *.log

# Process lines from a file
parallel echo "Processing {}" :::: filelist.txt

# Replace xargs
find . -name "*.txt" | parallel grep "pattern"
```
