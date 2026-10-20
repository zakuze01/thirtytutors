"""Bounded local chat-token counters. Never accepts prompts, keys or profile IDs."""

import sqlite3
import time
from contextvars import ContextVar

from . import memory

MAX_RECORDS = 500
_current = ContextVar("chat_token_usage", default=None)


def begin():
    _current.set(None)


def latest():
    return _current.get()


def count(value):
    return value if type(value) is int and 0 <= value <= 1_000_000_000 else None


def record(provider, usage):
    if provider not in ("groq", "deepseek") or not isinstance(usage, dict):
        return None
    incoming, outgoing = count(usage.get("prompt_tokens")), count(usage.get("completion_tokens"))
    if incoming is None or outgoing is None:
        return None  # Missing usage is unknown, never a synthetic zero.
    details = usage.get("prompt_tokens_details")
    cached = (
        count(usage.get("prompt_cache_hit_tokens"))
        if provider == "deepseek"
        else (count(details.get("cached_tokens")) if isinstance(details, dict) else None)
    )
    missed = count(usage.get("prompt_cache_miss_tokens"))
    if cached is not None and (
        cached > incoming or (provider == "deepseek" and missed is not None and cached + missed != incoming)
    ):
        cached = None
    completion = usage.get("completion_tokens_details")
    reasoning = count(completion.get("reasoning_tokens")) if isinstance(completion, dict) else None
    if reasoning is not None and reasoning > outgoing:
        reasoning = None
    item = {
        "at": int(time.time()),
        "provider": provider,
        "input_tokens": incoming,
        "output_tokens": outgoing,
        "cached_input_tokens": cached,
        "reasoning_tokens": reasoning,
    }
    try:
        with memory._transaction() as conn:
            conn.execute(
                "INSERT INTO token_usage(at,provider,input_tokens,output_tokens,cached_input_tokens,reasoning_tokens) VALUES(?,?,?,?,?,?)",
                tuple(item.values()),
            )
            conn.execute(
                "DELETE FROM token_usage WHERE id NOT IN (SELECT id FROM token_usage ORDER BY id DESC LIMIT ?)", (MAX_RECORDS,)
            )
    except sqlite3.Error:
        item["saved"] = False  # Optional accounting must never replay or fail a paid request.
    else:
        item["saved"] = True
    _current.set(item)
    return item


def overview():
    with memory._transaction() as conn:
        rows = conn.execute(
            "SELECT provider,COUNT(*) AS calls,SUM(input_tokens) AS input_tokens,SUM(output_tokens) AS output_tokens,"
            "SUM(cached_input_tokens) AS cached_input_tokens,COUNT(cached_input_tokens) AS cache_reported_calls "
            "FROM token_usage GROUP BY provider ORDER BY provider"
        ).fetchall()
    return {"providers": [dict(row) for row in rows], "max_records": MAX_RECORDS}


def clear():
    with memory._transaction() as conn:
        conn.execute("DELETE FROM token_usage")
