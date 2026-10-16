# Rendering a ValidationError for the caller

Read this when code refuses input because a Pydantic model rejected it: a config loader, a store
that reads a file back, a CLI argument model, or a library that re-raises a `ValidationError`
inside its own exception.

## The rule

Never interpolate `str(ValidationError)` (or `f"invalid file: {exc}"`) into a refusal, in new code
as much as in a refactor. That text is written for the model's author: it names pydantic's
internal union-arm tags, links a docs URL carrying the pinned pydantic version, and quotes a
truncated slice of the caller's own input back at them. The fields and reasons inside it are the
answer; the packaging around them is noise.

## The shape to emit

```text
<your own sentence saying which file or input was refused>
  <dotted loc>: <reason>
  <dotted loc>: <reason>
```

- Walk `error.errors()` and emit one `<dotted loc>: <reason>` line per problem.
- Raise your own exception with the original kept as `__cause__` (`raise ConfigError(text) from
  exc`), so a `--traceback` flag still reaches the full pydantic report.
- When a second store or loader of the same kind appears, share ONE formatter between them. Two
  copies drift, and the later one usually ships with the raw `str(exc)` the first one fixed.

## A library that wraps the ValidationError

Some libraries catch the model's refusal and re-raise their own exception, with the
`ValidationError` one or more levels down. `isinstance(exc, ValidationError)` on what you caught is
then False. Walk the chain:

```python
def find_validation_error(exc: BaseException) -> ValidationError | None:
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, ValidationError):
            return cause
        cause = cause.__cause__ or cause.__context__
    return None
```

Fall back to the library's own first message line only when no `ValidationError` turns up.

## Two traps inside `errors()`

**A union field is refused once PER ARM.** Each arm's `loc` carries pydantic's tag for that arm as
an extra part, for example `('styles', 'dict[str,str]', 'INFO')`, plus a `'[key]'` part when the
mapping KEY rather than the value was refused. Joined naively that prints one line per arm, naming
keys nobody wrote. Do not guess the tag grammar: a bare `str` or `int` tag looks exactly like a
key. Instead walk `loc` against the INPUT the caller supplied, and keep a part only where the
current node is a mapping holding that key (or a list holding that index). Render a refused
`'[key]'` part as a ` (key)` suffix on the line, then drop duplicate lines: the arms usually fail
for the same reason.

**A validator's message carries a prefix.** A `ValueError` raised in a validator arrives as
`msg == "Value error, <message>"`. When `item["type"] == "value_error"`, show
`str(item["ctx"]["error"])`, which is the message exactly as the validator wrote it, instead of
string-stripping the prefix.

## Check it

Feed the loader an empty object, a union field with a wrong value type, a refused mapping key, and
a value a validator rejects. Each refusal should read as your sentence plus one line per real
problem, with no union tag, no docs URL and no echoed input slice.
