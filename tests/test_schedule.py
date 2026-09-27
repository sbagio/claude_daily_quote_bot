from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.main import should_send


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def _sent(iso: str) -> dict[str, Any]:
    return {"hash": "h", "text": "t", "author": "a", "sent_at": iso}


def test_before_earliest_send_in_summer_skips() -> None:
    due, reason = should_send(_utc("2026-09-28T03:29:00"), [])  # 06:29 IDT
    assert not due
    assert "too early" in reason


def test_at_earliest_send_in_summer_sends() -> None:
    due, _ = should_send(_utc("2026-09-28T03:30:00"), [])  # 06:30 IDT
    assert due


def test_winter_uses_ist_offset() -> None:
    assert not should_send(_utc("2026-12-01T04:15:00"), [])[0]  # 06:15 IST
    assert should_send(_utc("2026-12-01T04:45:00"), [])[0]  # 06:45 IST


def test_already_sent_today_skips() -> None:
    history = [_sent("2026-09-28T03:50:00+00:00")]
    due, reason = should_send(_utc("2026-09-28T04:50:00"), history)
    assert not due
    assert reason == "already sent today"


def test_dedup_uses_israel_date_not_utc_date() -> None:
    # 21:30 UTC on the 27th is 00:30 IDT on the 28th, so it counts as the 28th's send.
    history = [_sent("2026-09-27T21:30:00+00:00")]
    assert not should_send(_utc("2026-09-28T04:00:00"), history)[0]


def test_sent_yesterday_sends() -> None:
    history = [_sent("2026-09-27T09:41:46.063833+00:00")]
    assert should_send(_utc("2026-09-28T03:45:00"), history)[0]


def test_unreadable_history_entry_is_ignored() -> None:
    assert should_send(_utc("2026-09-28T04:00:00"), [{"hash": "h"}])[0]
