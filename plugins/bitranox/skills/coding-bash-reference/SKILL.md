---
name: coding-bash-reference
description: Use when writing, reviewing, or debugging Bash scripts, when needing exact syntax for shell constructs, parameter expansions, redirections, builtins, test expressions, arrays, or any Bash 5.3 feature. Use when unsure about quoting rules, expansion order, conditional operators, trap behavior, shopt options, or specific builtin options and arguments.
---

# Bash 5.3 Reference

## Overview

Complete reference for GNU Bash 5.3 (May 2025). Covers all shell syntax, builtins, variables, expansions, redirections, and features. Use this skill whenever writing or reviewing bash scripts to ensure correctness.

**This file is a scannable hub.** Each section below summarizes key constructs with compact tables. Use the Read tool to load referenced files identified as relevant for full syntax, edge cases, and examples:

- **Syntax & commands** (quoting, compound commands, pipelines): `shell-syntax-and-commands.md`
- **Functions, parameters & expansions** (all expansion types, pattern matching): `functions-parameters-expansions.md`
- **Redirections & execution** (I/O, here docs, FDs, command search, signals): `redirections-and-execution.md`
- **Builtins** (`set`, `shopt`, `declare`, `read`, `printf`, `trap`, etc.): `shell-builtins.md`
- **Variables** (`BASH_REMATCH`, `PIPESTATUS`, `EPOCHSECONDS`, etc.): `shell-variables.md`
- **Bash features** (startup files, arrays, arithmetic, POSIX mode, conditionals): `bash-features.md`
- **Job control, readline & history** (bg/fg, completion, history expansion): `job-control-readline-history.md`

## When to Use

- Need exact syntax for any Bash construct (loops, conditionals, expansions, redirections)
- Writing, reviewing, or debugging Bash scripts
- Unsure about quoting rules, expansion order, or operator behavior
- Need to look up a specific builtin, variable, shopt option, or test operator
- Verifying Bash 5.3-specific features (`${ command; }`, `GLOBSORT`, `BASH_MONOSECONDS`)

## When NOT to Use

- Writing POSIX-portable `sh` scripts (this covers Bash-specific features beyond POSIX)
- Zsh, Fish, or other shell syntax
- Structuring multi-file Bash projects (use `bash_clean_architecture` instead)

## Reference Files

| File                                 | Contents                                                                                                                                                                                               |
|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `shell-syntax-and-commands.md`       | Quoting, comments, reserved words, pipelines, lists, compound commands (if/for/while/case/select/[[/(( ), grouping, coprocesses                                                                        |
| `functions-parameters-expansions.md` | Shell functions, positional/special parameters, ALL expansion types (brace, tilde, parameter, command substitution, arithmetic, process substitution, word splitting, globbing, pattern matching)      |
| `redirections-and-execution.md`      | All redirection types, here docs/strings, file descriptors, command search/execution, execution environment, exit status, signals, shell scripts                                                       |
| `shell-builtins.md`                  | All Bourne shell builtins, all Bash builtins, `set` options, `shopt` options, special builtins                                                                                                         |
| `shell-variables.md`                 | All Bourne shell variables, all Bash variables (BASH_*, COMP_*, HIST*, READLINE_*, etc.)                                                                                                               |
| `bash-features.md`                   | Invocation options, startup files, interactive shell behavior, conditional expressions, arithmetic, aliases, arrays, directory stack, prompt control, restricted shell, POSIX mode, compatibility mode |
| `job-control-readline-history.md`    | Job control (bg/fg/jobs/disown), readline configuration, all bindable commands, vi mode, programmable completion (complete/compgen/compopt), history expansion                                         |

### Which File Do I Need?

| I need to...                                                                         | Read                                 |
|--------------------------------------------------------------------------------------|--------------------------------------|
| Write a function, use parameters/expansions, do string manipulation                  | `functions-parameters-expansions.md` |
| Use `if`/`for`/`while`/`case`/`select`/`[[ ]]`/`(( ))`, or understand quoting        | `shell-syntax-and-commands.md`       |
| Redirect I/O, use here docs/strings, understand fd management                        | `redirections-and-execution.md`      |
| Look up a builtin (`set`, `shopt`, `declare`, `read`, `printf`, `trap`, etc.)        | `shell-builtins.md`                  |
| Check a shell variable (`BASH_REMATCH`, `PIPESTATUS`, `EPOCHSECONDS`, etc.)          | `shell-variables.md`                 |
| Understand startup files, arrays, arithmetic, POSIX mode, or conditional expressions | `bash-features.md`                   |
| Work with job control, readline, completion, or history expansion                    | `job-control-readline-history.md`    |


## Quick Reference: Most-Used Constructs

### Quoting

> Full details: `shell-syntax-and-commands.md` (section 1)

| Syntax    | Behavior                                                         |
|-----------|------------------------------------------------------------------|
| `\x`      | Escape single character                                          |
| `'text'`  | Literal string, no expansion                                     |
| `"text"`  | Allows `$`, `` ` ``, `\`, `!` expansion                          |
| `$'text'` | ANSI-C escapes: `\n`, `\t`, `\e`, `\xHH`, `\uHHHH`, `\UHHHHHHHH` |
| `$"text"` | Locale-specific translation                                      |

### Parameter Expansion

> Full details: `functions-parameters-expansions.md` (section 3.4)

| Syntax                 | Result                           |
|------------------------|----------------------------------|
| `${var:-default}`      | Use default if var unset/null    |
| `${var:=default}`      | Assign default if var unset/null |
| `${var:+alternate}`    | Use alternate if var IS set      |
| `${var:?error}`        | Error if var unset/null          |
| `${#var}`              | String length                    |
| `${var:offset:length}` | Substring                        |
| `${var#pattern}`       | Remove shortest prefix match     |
| `${var##pattern}`      | Remove longest prefix match      |
| `${var%pattern}`       | Remove shortest suffix match     |
| `${var%%pattern}`      | Remove longest suffix match      |
| `${var/pat/str}`       | Replace first match              |
| `${var//pat/str}`      | Replace all matches              |
| `${var/#pat/str}`      | Replace if matches beginning     |
| `${var/%pat/str}`      | Replace if matches end           |
| `${var^pattern}`       | Uppercase first char             |
| `${var^^pattern}`      | Uppercase all chars              |
| `${var,pattern}`       | Lowercase first char             |
| `${var,,pattern}`      | Lowercase all chars              |
| `${!prefix*}`          | Names matching prefix            |
| `${!name[@]}`          | Array indices/keys               |
| `${!var}`              | Indirect expansion               |
| `${var@Q}`             | Quote for reuse                  |
| `${var@E}`             | Expand escape sequences          |
| `${var@P}`             | Expand as prompt string          |
| `${var@A}`             | Assignment statement form        |
| `${var@a}`             | Attribute flags                  |
| `${var@U}`             | Uppercase all                    |
| `${var@u}`             | Uppercase first                  |
| `${var@L}`             | Lowercase all                    |
| `${var@K}`             | Key-value pairs (assoc arrays)   |

### Special Parameters

> Full details: `functions-parameters-expansions.md` (section 2)

| Param               | Meaning                                         |
|---------------------|-------------------------------------------------|
| `$0`                | Script/shell name                               |
| `$1`..`$9`, `${10}` | Positional parameters                           |
| `$#`                | Number of positional parameters                 |
| `$*`                | All positional params as single word (with IFS) |
| `$@`                | All positional params as separate words         |
| `"$*"`              | `"$1c$2c..."` where c = first char of IFS       |
| `"$@"`              | `"$1" "$2" ...` (preserves word boundaries)     |
| `$?`                | Exit status of last command                     |
| `$$`                | PID of the shell                                |
| `$!`                | PID of last background command                  |
| `$-`                | Current option flags                            |
| `$_`                | Last argument of previous command               |

### Compound Commands

> Full details: `shell-syntax-and-commands.md` (section 3)

```bash
# If
if cmd; then ...; elif cmd; then ...; else ...; fi

# For
for var in words; do ...; done
for (( init; test; step )); do ...; done

# While / Until
while cmd; do ...; done
until cmd; do ...; done

# Case
case word in
    pattern1|pattern2) commands ;;   # break
    pattern3) commands ;&            # fall-through
    pattern4) commands ;;&           # test next
esac

# Select (menu)
select var in words; do ...; done

# Test
[[ expression ]]    # Preferred (no word splitting/globbing)
(( expression ))    # Arithmetic evaluation

# Grouping
{ commands; }       # Current shell (note: space after {, ; before })
( commands )        # Subshell
```

### Test Operators (`[[ ]]` and `test`/`[ ]`)

> Full details: `bash-features.md` (section 4)

| Operator              | Test                             |
|-----------------------|----------------------------------|
| `-e file`             | Exists                           |
| `-f file`             | Regular file                     |
| `-d file`             | Directory                        |
| `-L file` / `-h file` | Symlink                          |
| `-s file`             | Non-zero size                    |
| `-r file`             | Readable                         |
| `-w file`             | Writable                         |
| `-x file`             | Executable                       |
| `-p file`             | Named pipe                       |
| `-S file`             | Socket                           |
| `-b file`             | Block device                     |
| `-c file`             | Character device                 |
| `-t fd`               | FD is terminal                   |
| `-O file`             | Owned by effective UID           |
| `-G file`             | Owned by effective GID           |
| `-N file`             | Modified since last read         |
| `f1 -nt f2`           | f1 newer than f2                 |
| `f1 -ot f2`           | f1 older than f2                 |
| `f1 -ef f2`           | Same inode                       |
| `-v var`              | Variable is set                  |
| `-R var`              | Variable is nameref              |
| `-z string`           | Zero length                      |
| `-n string`           | Non-zero length                  |
| `s1 == s2`            | Equal (pattern match in `[[ ]]`) |
| `s1 != s2`            | Not equal                        |
| `s1 < s2`             | Less than (lexicographic)        |
| `s1 > s2`             | Greater than (lexicographic)     |
| `s1 =~ regex`         | Regex match (`[[ ]]` only)       |
| `n1 -eq n2`           | Numeric equal                    |
| `n1 -ne n2`           | Numeric not equal                |
| `n1 -lt n2`           | Numeric less than                |
| `n1 -le n2`           | Numeric less/equal               |
| `n1 -gt n2`           | Numeric greater than             |
| `n1 -ge n2`           | Numeric greater/equal            |

### Redirections

> Full details: `redirections-and-execution.md` (section 1)

| Syntax                               | Operation                          |
|--------------------------------------|------------------------------------|
| `cmd < file`                         | Stdin from file                    |
| `cmd > file`                         | Stdout to file (truncate)          |
| `cmd >> file`                        | Stdout to file (append)            |
| `cmd 2> file`                        | Stderr to file                     |
| `cmd &> file` or `cmd > file 2>&1`   | Stdout+stderr to file              |
| `cmd &>> file` or `cmd >> file 2>&1` | Stdout+stderr append               |
| `cmd >&#124; file`                   | Force overwrite (noclobber)        |
| `cmd <<EOF`                          | Here document                      |
| `cmd <<-EOF`                         | Here document (strip leading tabs) |
| `cmd <<< "string"`                   | Here string                        |
| `cmd <&fd`                           | Duplicate input FD                 |
| `cmd >&fd`                           | Duplicate output FD                |
| `cmd fd<&-`                          | Close input FD                     |
| `cmd fd>&-`                          | Close output FD                    |
| `cmd n<>file`                        | Open for read+write on FD n        |
| `cmd {var}> file`                    | Auto-assign FD to var              |

Special filenames in redirections: `/dev/fd/N`, `/dev/stdin`, `/dev/stdout`, `/dev/stderr`, `/dev/tcp/host/port`, `/dev/udp/host/port`

### Arrays

> Full details: `bash-features.md` (section 6)

```bash
# Indexed arrays
declare -a arr=(one two three)
arr[0]="value"
arr+=(more items)

# Associative arrays (Bash 4.0+)
declare -A map=([key1]=val1 [key2]=val2)
map[key]="value"

# Access
${arr[0]}           # Single element
${arr[@]}           # All elements (separate words)
${arr[*]}           # All elements (single word with IFS)
${#arr[@]}          # Number of elements
${!arr[@]}          # All indices/keys
${arr[@]:off:len}   # Slice

# Unset
unset 'arr[2]'      # Remove element (quote to prevent glob)
unset arr            # Remove entire array
```

### Expansion Order

1. Brace expansion
2. Tilde expansion
3. Parameter and variable expansion
4. Arithmetic expansion
5. Command substitution (left-to-right)
6. Process substitution
7. Word splitting
8. Filename expansion (globbing)
9. Quote removal

Steps 2-6 happen left-to-right simultaneously. Full details with word-count impacts: `functions-parameters-expansions.md` (section 3.5).

### Common `set` Options

> Full details: `shell-builtins.md` (section 2, `set` builtin)

| Option                 | Effect                                         |
|------------------------|------------------------------------------------|
| `set -e` (`errexit`)   | Exit on error (with exceptions)                |
| `set -u` (`nounset`)   | Error on unset variables                       |
| `set -o pipefail`      | Pipeline fails if any command fails            |
| `set -x` (`xtrace`)    | Print commands before execution                |
| `set -f` (`noglob`)    | Disable filename expansion                     |
| `set -n` (`noexec`)    | Read commands without executing (syntax check) |
| `set -o posix`         | POSIX compliance mode                          |
| `set -E` (`errtrace`)  | ERR trap inherited by functions                |
| `set -T` (`functrace`) | DEBUG/RETURN traps inherited by functions      |

### Essential `shopt` Options

> Full details: `shell-builtins.md` (section 3, `shopt` options)

| Option              | Effect                                                          |
|---------------------|-----------------------------------------------------------------|
| `extglob`           | Extended patterns: `?(pat)` `*(pat)` `+(pat)` `@(pat)` `!(pat)` |
| `globstar`          | `**` matches directories recursively                            |
| `nullglob`          | Unmatched globs expand to nothing                               |
| `failglob`          | Unmatched globs cause error                                     |
| `nocaseglob`        | Case-insensitive globbing                                       |
| `nocasematch`       | Case-insensitive `case` and `[[ == ]]`                          |
| `dotglob`           | Globs match dotfiles                                            |
| `lastpipe`          | Last pipeline command runs in current shell                     |
| `inherit_errexit`   | Command substitutions inherit `errexit`                         |
| `assoc_expand_once` | Expand associative array subscripts once                        |

### Trap Signals

> Full details: `shell-builtins.md` (`trap` builtin) and `redirections-and-execution.md` (section 5, Signals)

```bash
trap 'cleanup' EXIT          # On shell exit
trap 'handle_err' ERR        # On command error (with set -e)
trap 'on_debug' DEBUG        # Before every command
trap 'on_return' RETURN      # After function/sourced script returns
trap 'handle_int' INT        # Ctrl-C
trap 'handle_term' TERM      # kill signal
trap '' SIGNAL               # Ignore signal
trap - SIGNAL                # Reset to default
```

### Arithmetic Operators (inside `(( ))` and `$(( ))`)

> Full details: `bash-features.md` (section 5)

All C-style operators: `+`, `-`, `*`, `/`, `%`, `**` (exponent), `<<`, `>>`, `&`, `|`, `^`, `~`, `!`, `&&`, `||`, `<`, `>`, `<=`, `>=`, `==`, `!=`, `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `<<=`, `>>=`, `&=`, `|=`, `^=`, `++`, `--`, `expr?expr:expr` (ternary), `expr,expr` (comma)

Bases: `0x` (hex), `0` (octal), `0b` (binary), `base#number` (arbitrary base 2-64)

### Prompt Escape Sequences

> Full details: `bash-features.md` (section 8, Controlling the Prompt)

| Escape    | Meaning                       |
|-----------|-------------------------------|
| `\u`      | Username                      |
| `\h`      | Hostname (short)              |
| `\H`      | Hostname (full)               |
| `\w`      | Working directory             |
| `\W`      | Basename of working directory |
| `\d`      | Date (Day Mon Date)           |
| `\t`      | Time (HH:MM:SS 24hr)          |
| `\T`      | Time (HH:MM:SS 12hr)          |
| `\@`      | Time (AM/PM)                  |
| `\A`      | Time (HH:MM 24hr)             |
| `\D{fmt}` | strftime format               |
| `\j`      | Number of jobs                |
| `\!`      | History number                |
| `\#`      | Command number                |
| `\$`      | `#` if root, `$` otherwise    |
| `\[`      | Begin non-printing chars      |
| `\]`      | End non-printing chars        |

## Definitions

| Term                 | Definition                                                                                                                                          |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **blank**            | Space or tab                                                                                                                                        |
| **word**             | Sequence of characters treated as a unit (no unquoted metacharacters)                                                                               |
| **token**            | A word or an operator                                                                                                                               |
| **metacharacter**    | Unquoted: space, tab, newline, `\|`, `&`, `;`, `(`, `)`, `<`, `>`                                                                                   |
| **control operator** | `\|\|`, `&&`, `&`, `;`, `;;`, `;&`, `;;&`, `\|`, `\|&`, `(`, `)`, newline                                                                           |
| **name/identifier**  | Letters, numbers, underscores; starts with letter or underscore                                                                                     |
| **exit status**      | 0-255; 0 = success, 1 = general error, 2 = usage error, 126 = not executable, 127 = not found, 128+N = killed by signal N                           |
| **special builtin**  | POSIX-designated builtins that have special properties (break, :, ., continue, eval, exec, exit, export, readonly, return, set, shift, trap, unset) |

## Common Patterns

### Safe Script Header
```bash
#!/usr/bin/env bash
set -euo pipefail
```

### Temporary Files
```bash
tmpfile=$(mktemp) || exit 1
trap 'rm -f "$tmpfile"' EXIT
```

### Read File Line by Line
```bash
while IFS= read -r line; do
    printf '%s\n' "$line"
done < "$file"
```

### Default Values
```bash
name="${1:-default}"        # Use default if $1 unset/empty
name="${1:?'missing arg'}"  # Exit with error if $1 unset/empty
```

### String Operations
```bash
# Lowercase / Uppercase
lower="${str,,}"
upper="${str^^}"
first_cap="${str^}"

# Trim prefix/suffix
filename="${path##*/}"      # basename
dir="${path%/*}"            # dirname
ext="${file##*.}"           # extension
noext="${file%.*}"          # remove extension
```

### Array Iteration
```bash
for item in "${arr[@]}"; do echo "$item"; done       # values
for i in "${!arr[@]}"; do echo "$i: ${arr[$i]}"; done # index: value
```

### Process Substitution
```bash
diff <(sort file1) <(sort file2)
while IFS= read -r line; do ...; done < <(cmd)  # avoid subshell
```

### Associative Array Check
```bash
declare -A map
if [[ -v map["key"] ]]; then echo "exists"; fi
```

## Common Mistakes

### Unquoted variables (word splitting + globbing)

```bash
# BAD: word splits and globs if file contains spaces or wildcards
for f in $files; do rm $f; done

# GOOD: always quote variable expansions
for f in "${files[@]}"; do rm "$f"; done
```

### `[ ]` vs `[[ ]]`

```bash
# BAD: word splitting inside [ ] can break with spaces in $var
[ $var == "hello" ]          # also: == is not POSIX in [ ]

# GOOD: [[ ]] prevents word splitting and supports == and =~
[[ $var == "hello" ]]
```

### `$@` vs `$*` quoting

```bash
# BAD: loses word boundaries
for arg in $@; do echo "$arg"; done

# GOOD: preserves each argument as a separate word
for arg in "$@"; do echo "$arg"; done

# "$*" joins all args into ONE word (separated by first char of IFS)
```

### `set -e` doesn't trigger everywhere

```bash
set -e
# These do NOT cause exit on failure:
if false; then :; fi           # test in 'if'
false || true                  # LHS of ||
false && true                  # LHS of &&
false | true                   # pipeline (without pipefail)
! false                        # negated command
```

### Missing `;` before `}` in brace groups

```bash
# BAD: syntax error
{ echo "hello" }

# GOOD: semicolon (or newline) required before }
{ echo "hello"; }
```

### Array access without braces

```bash
arr=(one two three)

# BAD: expands $arr (element 0) then appends literal [1]
echo $arr[1]      # prints: one[1]

# GOOD: braces required for array subscript
echo "${arr[1]}"  # prints: two
```

### Forgetting `declare -A` for associative arrays

```bash
# BAD: creates an indexed array, keys treated as arithmetic (0)
map=([foo]=1 [bar]=2)
echo "${map[foo]}"  # prints: 2 (both keys evaluated to index 0)

# GOOD: must declare associative arrays explicitly
declare -A map=([foo]=1 [bar]=2)
echo "${map[foo]}"  # prints: 1
```

### Using `=` vs `==` in the wrong context

```bash
# In [ ] / test: use = (POSIX). == works in Bash but is not portable.
[ "$a" = "$b" ]

# In [[ ]]: both = and == work; RHS is a pattern (quote for literal match)
[[ "$a" == "$b" ]]      # literal match (RHS quoted)
[[ "$a" == "$b"* ]]     # glob pattern (unquoted * appended)
[[ "$a" == $b ]]        # if $b contains *, it's a pattern (RHS unquoted)
```

### Subshell variable loss in pipes

```bash
# BAD: read runs in subshell, $var is lost after pipeline
echo "hello" | read var
echo "$var"    # empty

# GOOD: use process substitution or lastpipe
read var < <(echo "hello")
echo "$var"    # hello

# OR: enable lastpipe (non-interactive, no job control)
shopt -s lastpipe
echo "hello" | read var
```

### `local` variables use dynamic scoping

```bash
inner() { echo "$x"; }
outer() { local x=42; inner; }
outer  # prints: 42 (inner sees outer's local!)

# This is dynamic scoping, not lexical. Any function called
# from a scope with a local variable sees that variable.
```

### Here-strings always append a trailing newline

```bash
read -r var <<< "hello"
printf '%s' "$var" | xxd  # contains "hello\n"  -  trailing newline added
# Use printf instead when exact bytes matter:
read -r var < <(printf '%s' "hello")
```

### `declare -i` silently evaluates strings as arithmetic

```bash
declare -i num
num="1+1"
echo "$num"  # prints: 2 (string was evaluated!)
# WARNING: with untrusted input this is a code injection vector:
# declare -i x; x="a]$(cmd)" would execute cmd
```

### `trap EXIT` is reset in subshells

```bash
trap 'echo cleanup' EXIT
(echo "subshell")  # EXIT trap does NOT fire here
# Subshells inherit the parent's traps but reset EXIT/ERR/DEBUG/RETURN.
# If you need cleanup in a subshell, set a new trap inside it.
```
