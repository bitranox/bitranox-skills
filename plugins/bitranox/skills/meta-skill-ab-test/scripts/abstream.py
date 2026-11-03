"""Accounting for a `claude -p --output-format stream-json` stream, and the input-side price table.

Ported from the prototype's abxlib.StreamAccount and fixeslib.input_usage. The main model must be
an opus id (the run is void otherwise); delegation to haiku inside the arm is allowed and counted
per model (user decision 2026-11-03).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "FORBIDDEN_MODEL_SUBSTRINGS",
    "INPUT_CLASSES",
    "OPUS_PREFIX",
    "PRICES",
    "StreamAccount",
    "UnknownModel",
    "account_stream_file",
    "input_units",
    "input_usage",
    "price_input",
]

OPUS_PREFIX = "claude-opus"
FORBIDDEN_MODEL_SUBSTRINGS = ("fable", "mythos")
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
    cc = usage.get("cache_creation") or {}
    five, one_h = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
    if five is None and one_h is None:
        # Without the split the whole creation count takes the 5m rate, the cheaper one.
        five, one_h = usage.get("cache_creation_input_tokens") or 0, 0
    return {"input": int(usage.get("input_tokens") or 0), "cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_write_5m": int(five or 0), "cache_write_1h": int(one_h or 0)}


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
    new_tokens: int = 0
    cache_read: int = 0
    output_tokens: int = 0
    assistant_messages: int = 0
    first_cache_read: int | None = None
    # Lines a saved stream held that were not a JSON object: a killed arm tears its last line,
    # and a count that is not zero says the account may be missing what that line carried.
    skipped_lines: int = 0
    seen_ids: set[str] = field(default_factory=set)
    per_message_model: dict[str, int] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    void_reasons: list[str] = field(default_factory=list)

    def feed(self, record: dict[str, Any]) -> None:
        """Account one stream record; a record of any other type is ignored."""
        kind = record.get("type")
        if kind == "system" and record.get("subtype") == "init":
            self._feed_init(record)
        elif kind == "assistant":
            self._feed_assistant(record.get("message") or {})
        elif kind == "result":
            self._feed_result(record)

    def _feed_init(self, record: dict[str, Any]) -> None:
        self.model = record.get("model")
        self.claude_version = record.get("claude_code_version")
        self.session_id = record.get("session_id")
        self.permission_mode = record.get("permissionMode")
        self.plugins = [str(p.get("name", p)) if isinstance(p, dict) else str(p) for p in record.get("plugins") or []]
        self.skill_count = len(record.get("skills") or [])
        if not str(self.model or "").startswith(OPUS_PREFIX):
            self.void_reasons.append(f"session model is {self.model!r}, not an opus id")

    def _feed_assistant(self, message: dict[str, Any]) -> None:
        mid = message.get("id")
        if mid and mid in self.seen_ids:
            return
        if mid:
            self.seen_ids.add(mid)
        usage = message.get("usage") or {}
        cache_read = int(usage.get("cache_read_input_tokens") or 0)
        if self.first_cache_read is None:
            self.first_cache_read = cache_read
        self.new_tokens += int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0)
        self.cache_read += cache_read
        self.output_tokens += int(usage.get("output_tokens") or 0)
        self.assistant_messages += 1
        model = str(message.get("model") or "")
        self.per_message_model[model] = self.per_message_model.get(model, 0) + 1

    def _feed_result(self, record: dict[str, Any]) -> None:
        self.result = record
        for model_id in record.get("modelUsage") or {}:
            if any(s in model_id for s in FORBIDDEN_MODEL_SUBSTRINGS):
                self.void_reasons.append(f"model {model_id} appears in modelUsage")

    def per_model(self) -> dict[str, dict[str, Any]]:
        """Tokens and cost per model id, from the result record's modelUsage (empty without one)."""
        out: dict[str, dict[str, Any]] = {}
        for model_id, u in ((self.result or {}).get("modelUsage") or {}).items():
            out[model_id] = {"new_tokens": int(u.get("inputTokens") or 0) + int(u.get("cacheCreationInputTokens") or 0),
                             "cache_read": int(u.get("cacheReadInputTokens") or 0),
                             "output_tokens": int(u.get("outputTokens") or 0), "cost_usd": float(u.get("costUSD") or 0.0)}
        return out

    def summary(self) -> dict[str, Any]:
        """Everything the account knows, as one JSON-ready dict."""
        r = self.result or {}
        return {"model": self.model, "claude_version": self.claude_version, "session_id": self.session_id,
                "permission_mode": self.permission_mode, "plugins": self.plugins, "skill_count": self.skill_count,
                "main_new_tokens": self.new_tokens, "main_cache_read": self.cache_read,
                "main_output_tokens": self.output_tokens, "assistant_messages": self.assistant_messages,
                "first_cache_read": self.first_cache_read, "per_message_model": self.per_message_model,
                "per_model": self.per_model(), "total_cost_usd": r.get("total_cost_usd"), "num_turns": r.get("num_turns"),
                "duration_ms": r.get("duration_ms"), "result_subtype": r.get("subtype"),
                "has_result": self.result is not None, "skipped_lines": self.skipped_lines,
                "void_reasons": list(self.void_reasons)}


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
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                acct.skipped_lines += 1
                continue
            if isinstance(record, dict):
                acct.feed(record)
            else:
                acct.skipped_lines += 1
    return acct
