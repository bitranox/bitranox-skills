"""Accounting for a `claude -p --output-format stream-json` stream, and the input-side price table.

Ported from the prototype's abxlib.StreamAccount and fixeslib.input_usage. The main model must be
an opus id (the run is void otherwise); delegation to haiku inside the arm is allowed and counted
per model (user decision 2026-11-03). Every other model voids the arm, a claude-sonnet-* id and a
fable id (fable only authors) included, so the check is an allowlist, not a list of names to refuse.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "ALLOWED_MODEL_PREFIXES",
    "FORBIDDEN_MODEL_SUBSTRINGS",
    "INPUT_CLASSES",
    "NO_INIT_REASON",
    "OPUS_PREFIX",
    "PRICES",
    "SYNTHETIC_MODEL",
    "SYNTHETIC_REASON_PREFIX",
    "StreamAccount",
    "UnknownModel",
    "account_stream_file",
    "input_units",
    "input_usage",
    "price_input",
]

OPUS_PREFIX = "claude-opus"
# The models an arm may run on, matched against the lowercased id. A denylist let every model
# nobody had listed through (any claude-sonnet-* id, and fable spelt in another case).
ALLOWED_MODEL_PREFIXES = (OPUS_PREFIX, "claude-haiku")
# Kept for importers; the void check reads ALLOWED_MODEL_PREFIXES, which already refuses these.
FORBIDDEN_MODEL_SUBSTRINGS = ("fable", "mythos")
NO_INIT_REASON = "no init record (main model not asserted)"
# The CLI writes its own notices (a usage limit hit, an API error) as assistant records under this
# model id. It names no model, so the allowlist skips it; the notice itself voids the arm, with its
# text, because a run that hit a limit or lost its connection did not do the work it was given.
SYNTHETIC_MODEL = "<synthetic>"
SYNTHETIC_REASON_PREFIX = "CLI synthetic message: "
SYNTHETIC_TEXT_LIMIT = 80
INPUT_CLASSES = ("input", "cache_read", "cache_write_5m", "cache_write_1h")
# USD per million tokens. Add a row from the published price list, never from memory.
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write_5m": 5.00, "cache_write_1h": 8.00},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write_5m": 0.125, "cache_write_1h": 0.20},
}
# Thousandths of a dollar per million tokens, so every sum is an exact integer in 1e-9 USD: a
# float sum in another order reads equal token counts as "above" by a rounding error.
PRICE_MILLI = {m: {k: round(v * 1000) for k, v in p.items()} for m, p in PRICES.items()}
NANO = 1e9


class UnknownModel(KeyError):
    """A model id with no row in PRICES; pricing it would be a guess."""


def input_usage(usage: dict[str, Any]) -> dict[str, int]:
    """The INPUT side of one message's usage, split by price class.

    Args:
        usage: an assistant message's ``usage`` object as the stream carries it.

    Returns:
        Token counts keyed by every name in INPUT_CLASSES.
    """
    cc = usage.get("cache_creation")
    cc = cc if isinstance(cc, dict) else {}
    five = int(cc.get("ephemeral_5m_input_tokens") or 0)
    one_h = int(cc.get("ephemeral_1h_input_tokens") or 0)
    # Whatever the split does not explain (no split at all, or only one class reported) takes the
    # 5m rate, the cheaper one, so the total is never lost and never priced above what it was.
    five += max(0, int(usage.get("cache_creation_input_tokens") or 0) - five - one_h)
    return {"input": int(usage.get("input_tokens") or 0), "cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_write_5m": five, "cache_write_1h": one_h}


def input_units(model: str, usage: dict[str, int]) -> int:
    """The input side of one message in 1e-9 USD, priced by its own model.

    Args:
        model: the model id the message ran on.
        usage: token counts as input_usage() returns them.

    Returns:
        The price as an exact integer count of 1e-9 USD.

    Raises:
        UnknownModel: the model has no row in PRICES.
    """
    if model not in PRICES:
        raise UnknownModel(model)
    p = PRICE_MILLI[model]
    return sum(int(usage.get(k, 0)) * p[k] for k in INPUT_CLASSES)


def price_input(model: str, usage: dict[str, int]) -> float:
    """The input side of one message in USD; see input_units() for the exact integer form.

    Args:
        model: the model id the message ran on.
        usage: token counts as input_usage() returns them.

    Returns:
        The price in USD.

    Raises:
        UnknownModel: the model has no row in PRICES.
    """
    return input_units(model, usage) / NANO


@dataclass
class StreamAccount:
    """What one stream says about one run; feed() is idempotent per assistant message id."""

    model: str | None = None
    claude_version: str | None = None
    session_id: str | None = None
    permission_mode: str | None = None
    plugins: list[str] = field(default_factory=list)
    skill_count: int = 0
    saw_init: bool = False
    # New input (input_tokens + cache_creation_input_tokens) summed over EVERY model's assistant
    # messages, delegated haiku ones included: the token cap is per arm (design S4).
    new_tokens: int = 0
    cache_read: int = 0
    output_tokens: int = 0
    assistant_messages: int = 0
    first_cache_read: int | None = None
    # Lines a saved stream held that were not a JSON object: a killed arm tears its last line,
    # and a count that is not zero says the account may be missing what that line carried.
    skipped_lines: int = 0
    seen_ids: set[str] = field(default_factory=set)
    # The largest output_tokens seen per message id: the first record of a message is the
    # message_start partial, so its output count is low.
    output_by_id: dict[str, int] = field(default_factory=dict)
    per_message_model: dict[str, int] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    void_reasons: list[str] = field(default_factory=list)

    def feed_line(self, line: str) -> None:
        """Account one line of a stream, as saved or as it arrives from a live arm.

        Args:
            line: one stream line; surrounding whitespace is stripped and a blank line ignored.
                A line that is not JSON, or JSON that is not an object, counts in skipped_lines.
        """
        text = line.strip()
        if not text:
            return
        try:
            record = json.loads(text)
        except (ValueError, RecursionError):
            record = None
        if isinstance(record, dict):
            self.feed(record)
        else:
            self.skipped_lines += 1

    def feed(self, record: dict[str, Any]) -> None:
        """Account one stream record; a record of any other type is ignored."""
        kind = record.get("type")
        if kind == "system" and record.get("subtype") == "init":
            self._feed_init(record)
        elif kind == "assistant":
            self._feed_assistant(record.get("message"))
        elif kind == "result":
            self._feed_result(record)

    def _void(self, reason: str) -> None:
        if reason not in self.void_reasons:
            self.void_reasons.append(reason)

    def _check_model(self, model_id: str, where: str) -> None:
        if model_id == SYNTHETIC_MODEL:
            return
        if model_id and not model_id.lower().startswith(ALLOWED_MODEL_PREFIXES):
            self._void(f"model {model_id} appears in {where}, not an opus or haiku id")

    def _feed_init(self, record: dict[str, Any]) -> None:
        self.saw_init = True
        self.model = record.get("model")
        self.claude_version = record.get("claude_code_version")
        self.session_id = record.get("session_id")
        self.permission_mode = record.get("permissionMode")
        self.plugins = [str(p.get("name", p)) if isinstance(p, dict) else str(p) for p in record.get("plugins") or []]
        self.skill_count = len(record.get("skills") or [])
        if not str(self.model or "").startswith(OPUS_PREFIX):
            self.void_reasons.append(f"session model is {self.model!r}, not an opus id")

    def _feed_assistant(self, message: object) -> None:
        if not isinstance(message, dict):
            self.skipped_lines += 1
            return
        if message.get("model") == SYNTHETIC_MODEL:
            # A CLI notice charges no tokens and is no model message: it only voids the arm.
            self._void(SYNTHETIC_REASON_PREFIX + _text_of(message)[:SYNTHETIC_TEXT_LIMIT])
            return
        usage = message.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        mid = message.get("id") if isinstance(message.get("id"), str) else None
        self._note_output(mid, int(usage.get("output_tokens") or 0))
        # A message without an id is counted every time it appears (accepted: real CLI records
        # always carry one, so there is nothing to deduplicate on).
        if mid and mid in self.seen_ids:
            return
        if mid:
            self.seen_ids.add(mid)
        self._count_input(usage)
        self._count_model(str(message.get("model") or ""))

    def _count_model(self, model: str) -> None:
        self.assistant_messages += 1
        self.per_message_model[model] = self.per_message_model.get(model, 0) + 1
        self._check_model(model, "an assistant message")

    def _note_output(self, mid: str | None, output: int) -> None:
        if not mid:
            self.output_tokens += output
            return
        previous = self.output_by_id.get(mid, 0)
        if output > previous:
            self.output_tokens += output - previous
            self.output_by_id[mid] = output

    def _count_input(self, usage: dict[str, Any]) -> None:
        cache_read = int(usage.get("cache_read_input_tokens") or 0)
        if self.first_cache_read is None:
            self.first_cache_read = cache_read
        self.new_tokens += int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0)
        self.cache_read += cache_read

    def _feed_result(self, record: dict[str, Any]) -> None:
        self.result = record
        if not self.saw_init:
            self._void(NO_INIT_REASON)
        for model_id in _model_usage(record):
            self._check_model(model_id, "modelUsage")

    def per_model(self) -> dict[str, dict[str, Any]]:
        """Tokens and cost per model id, from the result record's modelUsage (empty without one).

        A model whose entry is not an object is left out; its id is still checked by the void rule.
        """
        out: dict[str, dict[str, Any]] = {}
        for model_id, u in _model_usage(self.result or {}).items():
            if not isinstance(u, dict):
                continue
            out[model_id] = {"new_tokens": int(u.get("inputTokens") or 0) + int(u.get("cacheCreationInputTokens") or 0),
                             "cache_read": int(u.get("cacheReadInputTokens") or 0),
                             "output_tokens": int(u.get("outputTokens") or 0), "cost_usd": float(u.get("costUSD") or 0.0)}
        return out

    def summary(self) -> dict[str, Any]:
        """Everything the account knows, as one JSON-ready dict.

        ``main_new_tokens`` is ``new_tokens``: EVERY model's new input, not the main model's alone.
        ``void_reasons`` names a missing init record even when no result record arrived.
        """
        r = self.result or {}
        void_reasons = list(self.void_reasons)
        if not self.saw_init and NO_INIT_REASON not in void_reasons:
            void_reasons.append(NO_INIT_REASON)
        return {"model": self.model, "claude_version": self.claude_version, "session_id": self.session_id,
                "permission_mode": self.permission_mode, "plugins": self.plugins, "skill_count": self.skill_count,
                "main_new_tokens": self.new_tokens, "main_cache_read": self.cache_read,
                "main_output_tokens": self.output_tokens, "assistant_messages": self.assistant_messages,
                "first_cache_read": self.first_cache_read, "per_message_model": self.per_message_model,
                "per_model": self.per_model(), "total_cost_usd": r.get("total_cost_usd"), "num_turns": r.get("num_turns"),
                "duration_ms": r.get("duration_ms"), "result_subtype": r.get("subtype"),
                "has_result": self.result is not None, "skipped_lines": self.skipped_lines,
                "void_reasons": void_reasons}


def _text_of(message: dict[str, Any]) -> str:
    """The text content blocks of a message joined on one line ("" when it carries none)."""
    content = message.get("content")
    if isinstance(content, str):
        return " ".join(content.split())
    blocks = content if isinstance(content, list) else []
    texts = [b["text"] for b in blocks if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    return " ".join(" ".join(texts).split())


def _model_usage(record: dict[str, Any]) -> dict[str, Any]:
    usage = record.get("modelUsage")
    return usage if isinstance(usage, dict) else {}


def account_stream_file(path: Path) -> StreamAccount:
    """Account every JSON line of a saved stream; a non-JSON line is counted and skipped, never fatal.

    A torn final line (an arm killed mid-write) is the expected case: the records before it still
    account, and ``has_result`` False plus ``skipped_lines`` say what was lost.

    Args:
        path: the saved stream.jsonl.

    Returns:
        The account of every JSON-object line, in file order.
    """
    acct = StreamAccount()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            acct.feed_line(line)
    return acct
