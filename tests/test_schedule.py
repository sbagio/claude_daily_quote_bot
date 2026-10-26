from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from src import main as bot
from src.main import time_until_due


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def _sent(iso: str) -> dict[str, Any]:
    return {"hash": "h", "text": "t", "author": "a", "sent_at": iso}


def test_before_send_at_in_summer_waits_until_seven_idt() -> None:
    assert time_until_due(_utc("2026-09-28T01:30:00"), []) == timedelta(hours=2, minutes=30)


def test_winter_uses_ist_offset() -> None:
    # 07:00 IST is 05:00 UTC after the Oct 25 switch.
    assert time_until_due(_utc("2026-10-27T04:00:00"), []) == timedelta(hours=1)


def test_after_send_at_is_due_now() -> None:
    assert time_until_due(_utc("2026-10-27T09:00:00"), []) == timedelta(0)


def test_already_sent_today_returns_none() -> None:
    history = [_sent("2026-10-27T05:00:05+00:00")]
    assert time_until_due(_utc("2026-10-27T09:00:00"), history) is None


def test_dedup_uses_israel_date_not_utc_date() -> None:
    # 22:30 UTC on the 26th is 00:30 IST on the 27th, so it counts as the 27th's send.
    history = [_sent("2026-10-26T22:30:00+00:00")]
    assert time_until_due(_utc("2026-10-27T04:00:00"), history) is None


def test_sent_yesterday_is_not_today() -> None:
    history = [_sent("2026-10-26T05:00:00+00:00")]
    assert time_until_due(_utc("2026-10-27T05:00:00"), history) == timedelta(0)


def test_unreadable_history_entry_is_ignored() -> None:
    assert time_until_due(_utc("2026-10-27T05:00:00"), [{"hash": "h"}]) == timedelta(0)


class _FrozenClock:
    def __init__(self, start: datetime) -> None:
        self.now = start
        self.slept: list[float] = []

    def datetime_now(self, tz: timezone) -> datetime:
        return self.now.astimezone(tz)

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += timedelta(seconds=seconds)


def _run_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, start: str, max_wait: int,
    history: list[dict[str, Any]] | None = None,
) -> tuple[int, _FrozenClock, str]:
    state = tmp_path / "state.json"
    state.write_text(json.dumps(history or []), encoding="utf-8")
    monkeypatch.setenv("STATE_PATH", str(state))
    clock = _FrozenClock(_utc(start))

    class _DT(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return clock.datetime_now(tz)

    monkeypatch.setattr(bot, "datetime", _DT)
    monkeypatch.setattr(bot.clock, "sleep", clock.sleep)
    captured: list[str] = []
    monkeypatch.setattr(bot, "format_plain", lambda text, author, label: captured.append(label) or "")
    code = bot.main(["--dry-run", "--max-wait-minutes", str(max_wait)])
    return code, clock, captured[0] if captured else ""


def test_main_sleeps_until_seven_within_window(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, clock, label = _run_main(monkeypatch, tmp_path, "2026-10-27T02:00:00", max_wait=330)
    assert code == 0
    assert clock.slept == [3 * 3600]
    assert clock.now == _utc("2026-10-27T05:00:00")
    assert label == "Tuesday, October 27, 2026"


def test_main_exits_without_sleeping_beyond_window(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, clock, label = _run_main(monkeypatch, tmp_path, "2026-10-26T22:00:00", max_wait=330)
    assert code == 0
    assert clock.slept == []
    assert label == ""


def test_main_default_never_sleeps(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, clock, label = _run_main(monkeypatch, tmp_path, "2026-10-27T04:59:00", max_wait=0)
    assert (code, clock.slept, label) == (0, [], "")


def test_main_skips_when_already_sent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, clock, label = _run_main(
        monkeypatch, tmp_path, "2026-10-27T03:00:00", max_wait=330,
        history=[_sent("2026-10-26T22:30:00+00:00")],
    )
    assert (code, clock.slept, label) == (0, [], "")
