# Bash 5.3 Reference: Shell Functions, Parameters, and Expansions

Source: GNU Bash 5.3 Reference Manual (Chapters 3.3, 3.4, 3.5)

---

## 3.3 Shell Functions

Shell functions group commands for later execution using a single name. They execute in the **current shell context** -- no new process is created.

### Declaration Syntax

```bash
# Form 1: POSIX-compatible
fname () compound-command [redirections]

# Form 2: Using 'function' keyword (parentheses optional)
function fname [()] compound-command [redirections]
```

- The `function` keyword is optional. If `function` is supplied, the parentheses are optional.
- The body is a compound command -- usually a `{ list; }` block, but any compound command is valid.
- If `function` is used without parentheses, braces are recommended.
- In POSIX mode, `fname` must be a valid shell name and cannot be a special builtin.
- Outside POSIX mode, a function name can be any unquoted shell word not containing `$`.

### Function Body Rules

- Braces surrounding the body must be separated from the body by blanks or newlines (they are reserved words).
- When using braces, the list must be terminated by a semicolon `;`, `&`, or a newline.
- Redirections associated with the function definition are performed when the function is executed.

### Exit Status

| Situation           | Exit Status                                                           |
|---------------------|-----------------------------------------------------------------------|
| Function definition | Zero (unless syntax error or readonly function with same name exists) |
| Function execution  | Exit status of the last command executed in the body                  |

### Deleting Functions

```bash
unset -f fname
```

### Positional Parameters in Functions

When a function executes, the arguments to the function become the positional parameters during its execution. `$#` is updated to reflect the new positional parameters. `$0` is **unchanged**. The first element of the `FUNCNAME` variable is set to the function name while executing.

When the function completes, positional parameters and `$#` are restored to their pre-call values.

### Traps in Functions

| Trap     | Inherited?                                                                            |
|----------|---------------------------------------------------------------------------------------|
| `DEBUG`  | No, unless function has `trace` attribute (`declare -t`) or `-o functrace` is enabled |
| `RETURN` | No, unless function has `trace` attribute or `-o functrace` is enabled                |
| `ERR`    | No, unless `-o errtrace` is enabled                                                   |

### The `return` Builtin

- Causes the function to complete; execution resumes after the function call.
- Any command associated with the `RETURN` trap executes before resumption.
- If `return N` is given, `N` is the function's return status.
- Without a numeric argument, the return status is the exit status of the last command executed before `return`.

### FUNCNEST -- Recursion Limit

```bash
FUNCNEST=100   # Set maximum function nesting depth
```

- If set to a numeric value greater than 0, defines the maximum function nesting level.
- Invocations exceeding the limit cause the **entire command** to abort.
- By default, Bash places **no limit** on recursive calls.

### Local Variables

```bash
func() {
    local var="value"
    declare var2="value2"    # Also creates a local variable inside functions
}
```

- Declared with `local` or `declare` builtins.
- Visible only to the function and the commands it invokes.
- **Shadow** variables with the same name at previous scopes (including global).
- When the function returns, the shadowed variable becomes visible again.

### Dynamic Scoping

Bash uses **dynamic scoping**: a variable's visibility depends on the sequence of function calls, not lexical scope.

```bash
func1() {
    local var='func1 local'
    func2
}
func2() {
    echo "In func2, var = $var"
}
var=global
func1
# Output: In func2, var = func1 local
```

- `func2` sees `var` from `func1`'s scope, not the global `var`.
- `unset` also acts using dynamic scope: it unsets the variable at the current scope first.
- If a local variable is unset, it remains unset until reset in that scope or the function returns.
- The `localvar_unset` shell option changes `unset` behavior for local variables.

### Listing and Exporting Functions

```bash
declare -f            # List function names and definitions
declare -F            # List function names only (with extdebug: also source file and line number)
export -f fname       # Export function to child shell processes
unset -f fname        # Delete a function definition
```

---

## 3.4 Shell Parameters

A **parameter** is an entity that stores values. It can be a name, a number, or a special character.

A **variable** is a parameter denoted by a name. Variables have a value and zero or more attributes (set via `declare`).

### Variable Assignment

```bash
name=[value]
```

- If `value` is not given, the variable is assigned the null string.
- Values undergo: tilde expansion, parameter/variable expansion, command substitution, arithmetic expansion, and quote removal.
- Word splitting and filename expansion are **not** performed on assignment values.
- If the variable has the `integer` attribute, value is evaluated as an arithmetic expression even without `$((...))`.

### The `+=` Operator

| Variable Type                           | Behavior of `+=`                                 |
|-----------------------------------------|--------------------------------------------------|
| String                                  | Appends expanded value to current value          |
| Integer (`declare -i`)                  | Adds arithmetic result of value to current value |
| Indexed array (compound assignment)     | Appends new values starting at max_index + 1     |
| Associative array (compound assignment) | Adds new key-value pairs                         |

### Nameref Variables

```bash
declare -n ref=$1     # Create a nameref to the variable named by $1
```

- Created with `declare -n` or `local -n`.
- All operations on the nameref (reference, assignment, unset, attribute modification) act on the referenced variable.
- In a `for` loop, a nameref control variable establishes a reference for each word in the list.
- Array variables **cannot** be given the nameref attribute, but namerefs can reference arrays and subscripted array variables.
- Unset a nameref itself (not its target) with `unset -n`.

### Declaration Commands

Assignment statements may appear as arguments to: `alias`, `declare`, `typeset`, `export`, `readonly`, `local`.

---

## 3.4.1 Positional Parameters

A positional parameter is denoted by one or more digits (other than single digit `0`).

```bash
$1  $2  ... $9       # Single-digit: braces optional
${10} ${11} ...      # Multi-digit: braces REQUIRED
```

- Assigned from the shell's arguments at invocation.
- Reassigned with `set` builtin; shifted with `shift` builtin.
- Cannot be assigned with assignment statements (`=`).
- Temporarily replaced when a shell function is executed.
- Without braces, `$10` is interpreted as `${1}0`, not `${10}`.

---

## 3.4.2 Special Parameters

Special parameters may only be referenced; assignment to them is not allowed.

| Parameter | Name       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|-----------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `$*`      | Star       | Expands to all positional parameters starting from 1. Unquoted: each parameter is a separate word subject to further splitting and globbing. **In double quotes** (`"$*"`): expands to a single word with parameters separated by the first character of `IFS`. If `IFS` is unset, separated by spaces. If `IFS` is null, joined with no separator. Equivalent to `"$1c$2c..."` where `c` is `IFS[0]`.                                                                                                                                     |
| `$@`      | At         | Expands to all positional parameters starting from 1. **In double quotes** (`"$@"`): each parameter expands to a separate word -- equivalent to `"$1" "$2" ...`. In non-word-splitting contexts (e.g., assignments), expands to a single word with parameters separated by spaces. When there are no positional parameters, `"$@"` and `$@` expand to nothing (removed). If the double-quoted expansion occurs within a word, the first parameter joins with the beginning and the last parameter joins with the end of the original word. |
| `$#`      | Hash       | Number of positional parameters (decimal).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `$?`      | Question   | Exit status of the most recently executed command.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `$-`      | Hyphen     | Current option flags (as specified upon invocation, by `set`, or set by the shell itself, such as `-i`).                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `$$`      | Dollar     | Process ID of the shell. In a subshell, expands to the PID of the **invoking** shell, not the subshell.                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `$!`      | Bang       | Process ID of the job most recently placed into the background (via `&` or the `bg` builtin).                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `$0`      | Zero       | Name of the shell or shell script. Set at shell initialization. With a file of commands: set to the filename. With `-c`: set to the first argument after the command string (if present). Otherwise: set to the filename used to invoke Bash.                                                                                                                                                                                                                                                                                              |
| `$_`      | Underscore | Context-dependent: at shell startup, set to the pathname used to invoke the shell. Subsequently, expands to the last argument of the previous simple command executed in the foreground (after expansion). Also set to the full pathname of each command executed and placed in the environment exported to that command. When checking mail, expands to the name of the mail file.                                                                                                                                                        |

### `$*` vs `$@` Quick Reference

```bash
set -- "hello world" "foo bar"

# Unquoted: both undergo word splitting
for w in $*;  do echo "[$w]"; done   # [hello] [world] [foo] [bar]
for w in $@;  do echo "[$w]"; done   # [hello] [world] [foo] [bar]

# Quoted: critical difference
for w in "$*"; do echo "[$w]"; done  # [hello world foo bar]  (single word)
for w in "$@"; do echo "[$w]"; done  # [hello world] [foo bar]  (preserves each)
```

---

## 3.5 Shell Expansions

### Order of Expansion

Expansions are performed in this order after the command line is split into tokens:

| Step | Expansion                              | Can increase word count?          |
|------|----------------------------------------|-----------------------------------|
| 1    | Brace expansion                        | Yes                               |
| 2    | Tilde expansion                        | No                                |
| 2    | Parameter and variable expansion       | No (except `"$@"`, `"${arr[@]}"`) |
| 2    | Arithmetic expansion                   | No                                |
| 2    | Command substitution                   | No                                |
| 2    | Process substitution (where supported) | No                                |
| 3    | Word splitting                         | Yes                               |
| 4    | Filename expansion                     | Yes                               |
| 5    | Quote removal (always last)            | No                                |

Steps 2 are performed left-to-right simultaneously (including process substitution on supported systems). Quote removal removes quote characters from the original word, not ones produced by other expansions.

---

## 3.5.1 Brace Expansion

Generates arbitrary strings sharing a common prefix and/or suffix.

### Comma-Separated Form

```bash
{string1,string2,...}

# Examples:
echo a{d,c,b}e                      # ade ace abe
mkdir /usr/local/src/bash/{old,new,dist,bugs}
chown root /usr/{ucb/{ex,edit},lib/{ex?.?*,how_ex}}
```

- Results are **not sorted**; left-to-right order is preserved.
- Nesting is supported: `a{b{1,2},c}d` produces `ab1d ab2d acd`.
- Preamble is prefixed to each string; postscript is appended to each result.

### Sequence Expression Form

```bash
{x..y[..incr]}
```

| Component | Description                                                  |
|-----------|--------------------------------------------------------------|
| `x`, `y`  | Integers or single letters (both must be same type)          |
| `incr`    | Optional integer increment (default: 1 or -1 as appropriate) |

```bash
echo {1..5}         # 1 2 3 4 5
echo {a..f}         # a b c d e f
echo {1..10..2}     # 1 3 5 7 9
echo {10..1..3}     # 10 7 4 1
echo {01..10}       # 01 02 03 04 05 06 07 08 09 10  (zero-padded)
```

- When either `x` or `y` begins with a zero, generated terms are zero-padded to the same width.
- Letter sequences use the C locale.

### Rules and Notes

- Brace expansion is performed **before all other expansions**.
- Characters special to other expansions are preserved in the result.
- A correctly-formed brace expansion requires unquoted `{` and `}` plus at least one unquoted comma or valid sequence expression.
- Incorrectly formed brace expansions are left unchanged.
- `{` or `,` may be quoted with backslash to prevent brace interpretation.
- `${` is not eligible for brace expansion (avoids conflict with parameter expansion); inhibits brace expansion until the closing `}`.
- Disable with `set +B` or start Bash with `+B`.

---

## 3.5.2 Tilde Expansion

All characters from the unquoted `~` up to the first unquoted slash (or end of word) form the **tilde-prefix**.

### Tilde Prefix Table

| Prefix      | Expansion                                                |
|-------------|----------------------------------------------------------|
| `~`         | `$HOME` (if unset: home directory of the executing user) |
| `~/foo`     | `$HOME/foo`                                              |
| `~user/foo` | Home directory of `user` + `/foo`                        |
| `~+`        | `$PWD`                                                   |
| `~+/foo`    | `$PWD/foo`                                               |
| `~-`        | `$OLDPWD` (if set)                                       |
| `~-/foo`    | `${OLDPWD-'~-'}/foo`                                     |
| `~N`        | Same as `dirs +N`                                        |
| `~+N`       | Same as `dirs +N`                                        |
| `~-N`       | Same as `dirs -N`                                        |

### Rules

- If the tilde-prefix characters (after `~`) are all unquoted, they are treated as a login name.
- If the login name is invalid or expansion fails, the tilde-prefix is left unchanged.
- Results of tilde expansion are treated as quoted (no further word splitting or filename expansion).
- Tilde expansion also occurs in variable assignments after `:` or the first `=`:
  ```bash
  PATH=~/bin:~user/bin:/usr/local/bin
  ```
- When words satisfy variable assignment conditions, tilde expansion occurs as arguments to simple commands (except in POSIX mode, where only declaration commands get this treatment).

---

## 3.5.3 Shell Parameter Expansion

The `$` character introduces parameter expansion, command substitution, or arithmetic expansion.

### Basic Form

```bash
${parameter}
$parameter       # Braces optional for simple names
```

- Braces are required when the parameter is a multi-digit positional parameter, or when followed by characters that could be part of the name.
- The matching closing `}` is the first `}` not escaped by backslash, not within a quoted string, and not within an embedded arithmetic expansion, command substitution, or parameter expansion.

### Indirect Expansion

```bash
${!parameter}
```

- If the first character of `parameter` is `!` (and it is not a nameref), Bash uses the expanded value of the rest of `parameter` as the new parameter name, then expands that.
- The intermediate value undergoes tilde expansion, parameter expansion, command substitution, and arithmetic expansion.
- If `parameter` is a nameref, expands to the **name** of the referenced variable (not full indirect expansion).
- Exceptions: `${!prefix*}`, `${!prefix@}`, `${!name[@]}`, `${!name[*]}` (described below).
- The `!` must immediately follow the `{`.

```bash
var="hello"
ref="var"
echo ${!ref}     # hello
```

### Colon Modifier Semantics

For the forms below using `:-`, `:=`, `:?`, `:+`:
- **With colon**: Tests whether parameter is **unset or null**.
- **Without colon** (omitting `:`): Tests only whether parameter is **unset**.

### Default Value -- `${parameter:-word}`

```bash
${parameter:-word}    # Substitute word if parameter is unset or null
${parameter-word}     # Substitute word if parameter is unset
```

The expansion of `word` is substituted if the test is true; otherwise the value of `parameter` is substituted.

```bash
v=123
echo ${v-unset}              # 123
echo ${v:-unset-or-null}     # 123
unset v
echo ${v-unset}              # unset
v=
echo ${v-unset}              # (empty -- v is set)
echo ${v:-unset-or-null}     # unset-or-null
```

### Assign Default -- `${parameter:=word}`

```bash
${parameter:=word}    # Assign word to parameter if unset or null, then substitute
${parameter=word}     # Assign word to parameter if unset, then substitute
```

- The expansion of `word` is assigned to `parameter`, and the result is that final value.
- **Positional parameters and special parameters may not be assigned this way.**

```bash
unset var
: ${var:=DEFAULT}
echo $var             # DEFAULT
```

### Error on Unset -- `${parameter:?word}`

```bash
${parameter:?word}    # Error if parameter is unset or null
${parameter?word}     # Error if parameter is unset
```

- If the test is true, the expansion of `word` (or a default message) is written to stderr.
- Non-interactive shell exits with non-zero status.
- Interactive shell does not exit but does not execute the command.

```bash
unset var
: ${var:?var is unset or null}     # bash: var: var is unset or null
var=123
echo ${var:?var is unset or null}  # 123
```

### Alternate Value -- `${parameter:+word}`

```bash
${parameter:+word}    # Substitute word if parameter is set and not null
${parameter+word}     # Substitute word if parameter is set
```

- If the test is true (parameter IS set/non-null), the expansion of `word` is substituted.
- The value of `parameter` itself is **not used**.
- If the test is false, nothing is substituted.

```bash
var=123
echo ${var:+is set}   # is set
unset var
echo ${var:+is set}   # (empty)
```

### Substring Expansion -- `${parameter:offset}` and `${parameter:offset:length}`

```bash
${parameter:offset}
${parameter:offset:length}
```

Extracts up to `length` characters starting at position `offset`. Both `offset` and `length` are arithmetic expressions.

| Condition                            | Behavior                                                                                                  |
|--------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `offset` omitted                     | Treated as 0                                                                                              |
| `length` omitted (no colon)          | Extends to end of value                                                                                   |
| `length` omitted (colon present)     | Treated as 0                                                                                              |
| Negative `offset`                    | Offset from the end of the value (**must be separated from `:` by a space** to avoid confusion with `:-`) |
| Negative `length` (strings)          | Interpreted as offset from the end; expansion is characters between `offset` and that position            |
| Negative `length` (`@`, `*`, arrays) | Expansion error                                                                                           |

```bash
string=01234567890abcdefgh
echo ${string:7}        # 7890abcdefgh
echo ${string:7:2}      # 78
echo ${string:7:-2}     # 7890abcdef
echo ${string: -7}      # bcdefgh       (space before - is required)
echo ${string: -7:2}    # bc
echo ${string: -7:-2}   # bcdef
```

#### Substring Expansion with `$@` and `$*`

- Result is `length` positional parameters beginning at `offset`.
- Negative offset is relative to one greater than the greatest positional parameter.
- If `offset` is 0, `$0` is prefixed to the list.
- Negative `length` is an expansion error.
- Indexing starts at 1 (not 0) for positional parameters.

```bash
set -- 1 2 3 4 5 6 7 8 9 0 a b c d e f g h
echo ${@:7}       # 7 8 9 0 a b c d e f g h
echo ${@:7:2}     # 7 8
echo ${@:0}       # ./bash 1 2 3 4 5 6 7 8 9 0 a b c d e f g h  ($0 included)
echo ${@:0:2}     # ./bash 1
echo ${@: -7:2}   # b c
```

#### Substring Expansion with Arrays

- Result is `length` members beginning with `${array[offset]}`.
- Negative offset is relative to one greater than the maximum index.
- Negative `length` is an expansion error.
- Associative arrays produce **undefined results**.

```bash
array=(0 1 2 3 4 5 6 7 8 9 0 a b c d e f g h)
echo ${array[@]:7}      # 7 8 9 0 a b c d e f g h
echo ${array[@]:7:2}    # 7 8
echo ${array[@]: -7:2}  # b c
```

### Variable Name Expansion -- `${!prefix*}` and `${!prefix@}`

```bash
${!prefix*}
${!prefix@}
```

- Expands to the **names** of variables whose names begin with `prefix`.
- Separated by the first character of `IFS`.
- With `@` inside double quotes, each name expands to a separate word.

```bash
MYAPP_NAME="test"
MYAPP_VERSION="1.0"
echo ${!MYAPP_*}    # MYAPP_NAME MYAPP_VERSION
```

### Array Key Expansion -- `${!name[@]}` and `${!name[*]}`

```bash
${!name[@]}
${!name[*]}
```

- If `name` is an array, expands to the list of indices (keys) assigned in `name`.
- If `name` is not an array, expands to `0` if `name` is set, null otherwise.
- With `@` inside double quotes, each key expands to a separate word.

### String/Array Length -- `${#parameter}`

```bash
${#parameter}
```

| Parameter                         | Result                                                                                 |
|-----------------------------------|----------------------------------------------------------------------------------------|
| Ordinary variable                 | Length in characters of its value                                                      |
| `*` or `@`                        | Number of positional parameters                                                        |
| Array subscripted with `*` or `@` | Number of elements in the array                                                        |
| Array with negative subscript     | Index relative to one greater than max index (counts back from end; -1 = last element) |

```bash
var="hello"
echo ${#var}       # 5
set -- a b c
echo ${#@}         # 3
```

### Prefix Removal (Shortest / Longest) -- `${parameter#word}` and `${parameter##word}`

```bash
${parameter#word}     # Remove shortest match from BEGINNING
${parameter##word}    # Remove longest match from BEGINNING
```

- `word` is expanded to produce a pattern (see Pattern Matching).
- Pattern is matched against the beginning of the expanded value.
- With `@` or `*`: applied to each positional parameter or array member in turn.

```bash
path="/home/user/file.txt"
echo ${path#*/}      # home/user/file.txt  (shortest prefix match)
echo ${path##*/}     # file.txt            (longest prefix match)
```

### Suffix Removal (Shortest / Longest) -- `${parameter%word}` and `${parameter%%word}`

```bash
${parameter%word}     # Remove shortest match from END
${parameter%%word}    # Remove longest match from END
```

- Pattern is matched against a trailing portion of the expanded value.
- With `@` or `*`: applied to each positional parameter or array member in turn.

```bash
file="archive.tar.gz"
echo ${file%.*}      # archive.tar   (shortest suffix match)
echo ${file%%.*}     # archive       (longest suffix match)
```

### Pattern Substitution -- `${parameter/pattern/string}`

```bash
${parameter/pattern/string}     # Replace first match
${parameter//pattern/string}    # Replace ALL matches
${parameter/#pattern/string}    # Replace match at BEGINNING only
${parameter/%pattern/string}    # Replace match at END only
```

- The **longest match** of `pattern` is replaced with `string`.
- `string` undergoes tilde expansion, parameter/variable expansion, arithmetic expansion, command and process substitution, and quote removal.
- If the expansion of `string` is null, matches are deleted (the trailing `/` may be omitted).
- With `@` or `*`: applied to each positional parameter or array member in turn.
- If `nocasematch` is enabled, matching is case-insensitive.

#### The `patsub_replacement` Option and `&`

When `patsub_replacement` is enabled (via `shopt`), unquoted `&` in `string` is replaced with the matching portion of `pattern` (similar to `sed`).

```bash
shopt -s patsub_replacement
var=abcdef
echo ${var/abc/& }           # abc def   (& replaced with "abc")
echo ${var/abc/\& }          # & def     (backslash escapes &)
echo ${var/abc/"& "}         # & def     (quoting inhibits & replacement)
```

- Backslash escapes `&` (the backslash is removed).
- Quoting any part of `string` inhibits `&` replacement in the quoted portion.
- `\\` inserts a literal backslash.

```bash
var=abcdef
rep='\\&xyz'
echo ${var/abc/\\&xyz}       # \abcxyzdef
echo ${var/abc/$rep}         # \abcxyzdef
```

### Case Modification -- `${parameter^pattern}`, `${parameter,,pattern}`

```bash
${parameter^pattern}     # Uppercase FIRST character if it matches pattern
${parameter^^pattern}    # Uppercase ALL characters matching pattern
${parameter,pattern}     # Lowercase FIRST character if it matches pattern
${parameter,,pattern}    # Lowercase ALL characters matching pattern
```

- `pattern` is expanded to produce a pattern; should match at most one character.
- If `pattern` is omitted, treated as `?` (matches every character).
- With `@` or `*`: applied to each positional parameter or array member in turn.

```bash
var="hello world"
echo ${var^}       # Hello world
echo ${var^^}      # HELLO WORLD
VAR="HELLO WORLD"
echo ${VAR,}       # hELLO WORLD
echo ${VAR,,}      # hello world
echo ${var^^[aeiou]}   # hEllO wOrld  (uppercase only vowels)
```

### Transformation -- `${parameter@operator}`

```bash
${parameter@operator}
```

Each operator is a single letter:

| Operator | Description                                                                                                    | Example    |
|----------|----------------------------------------------------------------------------------------------------------------|------------|
| `U`      | Convert all to uppercase                                                                                       | `${var@U}` |
| `u`      | Convert first character to uppercase (if alphabetic)                                                           | `${var@u}` |
| `L`      | Convert all to lowercase                                                                                       | `${var@L}` |
| `Q`      | Quote the value in a format reusable as input                                                                  | `${var@Q}` |
| `E`      | Expand backslash escape sequences (as with `$'...'`)                                                           | `${var@E}` |
| `P`      | Expand as a prompt string                                                                                      | `${var@P}` |
| `A`      | Produce an assignment statement or `declare` command that recreates the variable with its attributes and value | `${var@A}` |
| `K`      | Print indexed and associative arrays as quoted key-value pairs (reusable as input)                             | `${arr@K}` |
| `a`      | Produce flag values representing the variable's attributes                                                     | `${var@a}` |
| `k`      | Like `K`, but expands keys and values to separate words after word splitting                                   | `${arr@k}` |

- With `@` or `*`: applied to each positional parameter or array member in turn.
- Result is subject to word splitting and filename expansion.

```bash
var="hello"
echo ${var@U}    # HELLO
echo ${var@u}    # Hello
echo ${var@Q}    # 'hello'
declare -i num=42
echo ${num@a}    # i
echo ${num@A}    # declare -i num='42'
```

### Complete Parameter Expansion Quick Reference

| Syntax                         | Description                                   |
|--------------------------------|-----------------------------------------------|
| `${parameter}`                 | Value of parameter                            |
| `${!parameter}`                | Indirect expansion                            |
| `${!prefix*}` / `${!prefix@}`  | Variable names starting with prefix           |
| `${!name[@]}` / `${!name[*]}`  | Array indices/keys                            |
| `${#parameter}`                | Length of value (or count of elements)        |
| `${parameter:-word}`           | Default value (unset or null)                 |
| `${parameter-word}`            | Default value (unset only)                    |
| `${parameter:=word}`           | Assign default (unset or null)                |
| `${parameter=word}`            | Assign default (unset only)                   |
| `${parameter:?word}`           | Error if unset or null                        |
| `${parameter?word}`            | Error if unset                                |
| `${parameter:+word}`           | Alternate value if set and not null           |
| `${parameter+word}`            | Alternate value if set                        |
| `${parameter:offset}`          | Substring from offset to end                  |
| `${parameter:offset:length}`   | Substring from offset for length chars        |
| `${parameter#pattern}`         | Remove shortest prefix match                  |
| `${parameter##pattern}`        | Remove longest prefix match                   |
| `${parameter%pattern}`         | Remove shortest suffix match                  |
| `${parameter%%pattern}`        | Remove longest suffix match                   |
| `${parameter/pattern/string}`  | Replace first match                           |
| `${parameter//pattern/string}` | Replace all matches                           |
| `${parameter/#pattern/string}` | Replace match at beginning                    |
| `${parameter/%pattern/string}` | Replace match at end                          |
| `${parameter^pattern}`         | Uppercase first matching char                 |
| `${parameter^^pattern}`        | Uppercase all matching chars                  |
| `${parameter,pattern}`         | Lowercase first matching char                 |
| `${parameter,,pattern}`        | Lowercase all matching chars                  |
| `${parameter@operator}`        | Transformation (U, u, L, Q, E, P, A, K, a, k) |

---

## 3.5.4 Command Substitution

Replaces the command with its standard output.

### Standard Forms

```bash
$(command)       # Preferred form
`command`        # Deprecated (old-style backquote form)
```

- Bash executes `command` in a **subshell** environment.
- Trailing newlines are deleted from the output; embedded newlines are preserved (but may be removed by word splitting).
- `$(cat file)` can be replaced by the faster `$(< file)`.

### Backquote Form Differences

- Backslash retains literal meaning except when followed by `$`, `` ` ``, or `\`.
- The first unescaped backquote terminates the substitution.
- Nesting requires escaping inner backquotes with backslashes.

### `$(command)` Form

- All characters between parentheses form the command; none are treated specially.
- Nesting is straightforward: `$(echo $(date))`.

### Current-Execution-Environment Form (Bash 5.3)

```bash
${ command; }
```

- Executes `command` in the **current execution environment** (not a subshell).
- Trailing newlines are removed.
- The character after `{` must be a space, tab, newline, or `|`.
- The closing `}` must appear where a reserved word is expected (preceded by a command terminator like `;`).
- Side effects persist in the current environment (variable assignments, `exit` exits the shell).
- Local variables are created as in a shell function.
- `return` forces `command` to complete.

### REPLY Variant

```bash
${| command; }
```

- When the first character after `{` is `|`, the construct expands to the value of the `REPLY` variable after `command` executes.
- Trailing newlines are **not** removed.
- Standard output remains the same as the calling shell (not captured).
- `REPLY` is created as an initially-unset local variable; restored after completion.

```bash
${ local X=12345; echo $X; }    # Expands to "12345" (captured stdout)
${| REPLY=12345; }               # Expands to "12345" (via REPLY, no stdout needed)
```

### Double-Quote Behavior

If the substitution appears within double quotes, Bash does **not** perform word splitting and filename expansion on the results.

---

## 3.5.5 Arithmetic Expansion

```bash
$(( expression ))
```

- Evaluates an arithmetic expression and substitutes the integer result.
- The expression undergoes parameter/variable expansion, command substitution, and quote removal.
- Unescaped double quote characters within the expression are removed (not treated specially).
- Empty strings from double-quote handling evaluate to 0.
- Arithmetic expansions may be nested.
- If the expression is invalid, Bash prints an error and does not execute the command.

```bash
echo $(( 5 + 3 ))              # 8
x=10; echo $(( x * 2 ))        # 20
echo $(( (5 + 3) * 2 ))        # 16
echo $(( 2 ** 10 ))            # 1024
```

---

## 3.5.6 Process Substitution

```bash
<(list)     # Reading from the file obtains the output of list
>(list)     # Writing to the file provides input for list
```

- The process `list` runs **asynchronously**.
- Its input or output appears as a filename (e.g., `/dev/fd/63`).
- This filename is passed as an argument to the current command.
- **No space may appear between `<` or `>` and `(`** -- otherwise it is interpreted as a redirection.
- Supported on systems with named pipes (FIFOs) or `/dev/fd`.
- Performed simultaneously with parameter/variable expansion, command substitution, and arithmetic expansion.

```bash
diff <(sort file1) <(sort file2)
tee >(grep ERROR > errors.log) >(grep WARN > warnings.log) < input.log
```

---

## 3.5.7 Word Splitting

After parameter expansion, command substitution, and arithmetic expansion (when **not** within double quotes), the shell splits results into fields.

### IFS Rules

| IFS Value               | Behavior                                                                                                                  |
|-------------------------|---------------------------------------------------------------------------------------------------------------------------|
| Default (unset)         | Behaves as if `IFS=$' \t\n'`; space, tab, newline delimit fields                                                          |
| Null (`IFS=''`)         | No word splitting occurs (implicit null arguments still removed)                                                          |
| Whitespace only         | Any sequence of IFS whitespace delimits a field; no null fields from whitespace                                           |
| Contains non-whitespace | Non-whitespace char + any adjacent IFS whitespace = one delimiter. Adjacent non-whitespace delimiters produce null fields |

**IFS whitespace** is space, tab, and newline -- always considered IFS whitespace even if not in the locale's space category.

### Splitting Process

1. Sequences of IFS whitespace are removed from the beginning and end of the result.
2. Remaining words are split at IFS delimiters.

### Null Arguments

| Type                                                                    | Behavior                                      |
|-------------------------------------------------------------------------|-----------------------------------------------|
| Explicit null (`""` or `''`)                                            | Retained; passed to commands as empty strings |
| Implicit null (expansion of unset/null parameter, unquoted)             | Removed                                       |
| Implicit null (expansion of unset/null parameter, within double quotes) | Retained as empty string                      |
| Quoted null as part of a non-null word                                  | Null portion removed: `-d''` becomes `-d`     |

---

## 3.5.8 Filename Expansion (Globbing)

After word splitting, unless `set -f` (noglob) is active, Bash scans each word for `*`, `?`, and `[`. If any unquoted pattern character is found, the word is treated as a pattern and replaced with a sorted list of matching filenames.

### Shell Options Affecting Globbing

| Option                     | Effect                                                                                             |
|----------------------------|----------------------------------------------------------------------------------------------------|
| `nullglob`                 | No matches: word is removed                                                                        |
| `failglob`                 | No matches: error message, command not executed                                                    |
| `nocaseglob`               | Case-insensitive matching                                                                          |
| `dotglob`                  | Patterns match files beginning with `.` (but `.` and `..` still require explicit pattern match)    |
| `globskipdots`             | `.` and `..` never match, even with leading `.` in pattern                                         |
| `globstar`                 | `**` matches all files and zero or more directories/subdirectories; `**/` matches only directories |
| `globasciiranges`          | Range expressions in bracket expressions use C locale ordering                                     |
| `extglob`                  | Enable extended pattern matching operators                                                         |
| `set -f` / `set -o noglob` | Disable filename expansion entirely                                                                |

### GLOBIGNORE Variable

- Colon-separated list of patterns.
- Matching filenames are removed from glob results.
- Respects `nocaseglob` setting.
- `.` and `..` are always ignored when `GLOBIGNORE` is set and not null.
- Setting `GLOBIGNORE` to a non-null value enables `dotglob`; to ignore dotfiles, add `.*` to `GLOBIGNORE`.
- `GLOBIGNORE` pattern matching honors the `extglob` setting.
- Disabled (and `dotglob` reset) when `GLOBIGNORE` is unset.

### GLOBSORT Variable

Controls how pathname expansion results are sorted (see Bash Variables for details).

### Dot File Rules

- `.` at the start of a filename (or immediately after a slash) must be matched explicitly, unless `dotglob` is set.
- Even with `dotglob`, matching `.` and `..` requires a pattern beginning with `.` (e.g., `.?`).
- With `globskipdots`, `.` and `..` never appear in results.

---

## 3.5.8.1 Pattern Matching

Characters match themselves unless they are special pattern characters. NUL cannot appear in a pattern. A backslash escapes the following character (the backslash is discarded when matching).

### Basic Pattern Characters

| Character | Meaning                                                                                                                                                                  |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `*`       | Matches any string, including the null string. With `globstar` in filename context: `**` matches all files and zero or more directories; `**/` matches only directories. |
| `?`       | Matches any single character.                                                                                                                                            |
| `[...]`   | Bracket expression: matches any one of the enclosed characters.                                                                                                          |

### Bracket Expressions `[...]`

| Syntax               | Meaning                                                                   |
|----------------------|---------------------------------------------------------------------------|
| `[abc]`              | Matches `a`, `b`, or `c`                                                  |
| `[a-z]`              | Range expression: any character between `a` and `z` (collation-dependent) |
| `[!...]` or `[^...]` | Negation: matches any character NOT in the set                            |
| `[-...]` or `[...-]` | Literal `-`: include as first or last character                           |
| `[]...]`             | Literal `]`: include as first character                                   |

#### Character Classes

```
[[:class:]]
```

Available POSIX classes:

| Class    | Matches                              |
|----------|--------------------------------------|
| `alnum`  | Letters and digits                   |
| `alpha`  | Letters                              |
| `ascii`  | ASCII characters                     |
| `blank`  | Space and tab                        |
| `cntrl`  | Control characters                   |
| `digit`  | Digits                               |
| `graph`  | Non-space printable characters       |
| `lower`  | Lowercase letters                    |
| `print`  | Printable characters including space |
| `punct`  | Punctuation                          |
| `space`  | Whitespace characters                |
| `upper`  | Uppercase letters                    |
| `word`   | Letters, digits, and `_`             |
| `xdigit` | Hexadecimal digits                   |

```bash
[[:space:]][[:upper:]!].[-[:lower:]]
# Matches: space-class char, then uppercase or !, then dot, then lowercase or hyphen
```

#### Equivalence Classes

```
[=c=]
```
Matches all characters with the same collation weight as `c` (locale-dependent).

#### Collating Symbols

```
[.symbol.]
```
Matches the collating symbol `symbol`.

### Range Expression Locale Considerations

- In the C locale, `[a-dx-z]` equals `[abcdxyz]`.
- In dictionary-order locales, `[a-dx-z]` might equal `[aBbCcDdxYyZz]`.
- Force C locale behavior with `LC_COLLATE=C`, `LC_ALL=C`, or `shopt -s globasciiranges`.

### Extended Globbing (`extglob`)

Enable with `shopt -s extglob`. These operators use pattern-lists (patterns separated by `|`):

| Pattern           | Meaning                                                    |
|-------------------|------------------------------------------------------------|
| `?(pattern-list)` | Matches **zero or one** occurrence of the given patterns   |
| `*(pattern-list)` | Matches **zero or more** occurrences of the given patterns |
| `+(pattern-list)` | Matches **one or more** occurrences of the given patterns  |
| `@(pattern-list)` | Matches **exactly one** of the given patterns              |
| `!(pattern-list)` | Matches anything **except** one of the given patterns      |

```bash
shopt -s extglob
ls *.!(txt)              # Files not ending in .txt
ls +(ab|cd)              # Matches: ab, cd, abab, abcd, cdab, cdcd, etc.
echo @(foo|bar)          # Matches exactly "foo" or "bar"
```

- `extglob` changes the parser behavior (parentheses normally have syntactic meaning).
- Ensure `extglob` is enabled **before** parsing constructs containing these patterns (including shell functions and command substitutions).
- Complex extended pattern matching against long strings is slow; prefer shorter strings or arrays.

### Filename vs. Non-Filename Matching

- When matching filenames, `/` must always be matched explicitly by `/` in the pattern.
- In other matching contexts (e.g., `case`, `[[`), `/` can be matched by special pattern characters.

---

## 3.5.9 Quote Removal

After all preceding expansions, all **unquoted** occurrences of `\`, `'`, and `"` that did not result from one of the above expansions are removed.

- Quote characters produced by expansions are **not** removed (unless they were themselves quoted).
- This is always the final step of expansion processing.

---

## Common Patterns and Idioms

### Safe Default Values

```bash
name="${1:-default}"              # Use default if $1 is unset or empty
dir="${TMPDIR:-/tmp}"             # Fallback to /tmp
: "${CONFIG:=/etc/app.conf}"     # Set CONFIG if not already set
```

### Required Variables

```bash
: "${DATABASE_URL:?DATABASE_URL must be set}"    # Exit if not set
```

### String Manipulation Without External Commands

```bash
file="/path/to/archive.tar.gz"
echo "${file##*/}"       # archive.tar.gz  (basename)
echo "${file%/*}"        # /path/to        (dirname)
echo "${file%%.*}"       # /path/to/archive
echo "${file##*.}"       # gz              (extension)

url="https://example.com/page"
echo "${url#*://}"       # example.com/page  (strip protocol)
echo "${url%%/*}"        # https:            (protocol only -- note the result)
```

### String Replacement

```bash
str="hello-world-foo-bar"
echo "${str//-/_}"       # hello_world_foo_bar  (replace all - with _)
echo "${str/#hello/HI}"  # HI-world-foo-bar     (replace at start)
echo "${str/%bar/BAZ}"   # hello-world-foo-BAZ  (replace at end)
```

### Case Conversion

```bash
var="Hello World"
echo "${var^^}"          # HELLO WORLD
echo "${var,,}"          # hello world
echo "${var^}"           # Hello World  (first char only -- already uppercase)
lc="hello"
echo "${lc^}"            # Hello
```

### Array Operations

```bash
arr=(one two three four five)
echo "${arr[@]:1:3}"     # two three four   (slice)
echo "${#arr[@]}"        # 5                (count)
echo "${!arr[@]}"        # 0 1 2 3 4        (indices)
echo "${arr[@]/#/prefix_}"   # prefix_one prefix_two ...  (prefix each)
echo "${arr[@]/%/_suffix}"   # one_suffix two_suffix ...  (suffix each)
echo "${arr[@]^^}"       # ONE TWO THREE FOUR FIVE
```
