from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import Config
from src.quotes import Quote, get_quote

NOW = datetime(2026, 1, 15, tzinfo=timezone.utc)


def _make_config(quotes_path: Path, **overrides: object) -> Config:
    base: dict[str, object] = dict(
        telegram_bot_token="x",
        telegram_chat_id="y",
        quotes_path=quotes_path,
        state_path=quotes_path.parent / "state.json",
        web_source_probability=0.0,
        no_repeat_days=30,
        web_timeout_seconds=5,
        web_source_url="http://example.invalid",
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _write_quotes(path: Path, items: list[dict[str, str]]) -> None:
    path.write_text(json.dumps(items), encoding="utf-8")


def _history_entry(quote: Quote, days_ago: int) -> dict[str, str]:
    return {
        "hash": quote.hash,
        "text": quote.text,
        "author": quote.author,
        "sent_at": (NOW - timedelta(days=days_ago)).isoformat(),
    }


def test_hash_normalizes_whitespace_and_case() -> None:
    assert Quote(" A quote. ", "x").hash == Quote("a quote.", "y").hash


def test_no_repeat_excludes_recent(tmp_path: Path) -> None:
    qpath = tmp_path / "quotes.json"
    _write_quotes(qpath, [{"text": "A", "author": "x"}, {"text": "B", "author": "y"}])
    cfg = _make_config(qpath)
    history = [_history_entry(Quote("A", "x"), days_ago=1)]

    quote, source = get_quote(cfg, history, now=NOW, rng=random.Random(0))

    assert source == "curated"
    assert quote.text == "B"


def test_all_blocked_picks_least_recently_sent(tmp_path: Path) -> None:
    qpath = tmp_path / "quotes.json"
    _write_quotes(qpath, [{"text": "A", "author": "x"}, {"text": "B", "author": "y"}])
    cfg = _make_config(qpath)
    history = [
        _history_entry(Quote("A", "x"), days_ago=5),  # older
        _history_entry(Quote("B", "y"), days_ago=1),  # newer
    ]

    quote, _ = get_quote(cfg, history, now=NOW, rng=random.Random(0))

    assert quote.text == "A"


def test_web_source_used_when_probability_one(tmp_path: Path) -> None:
    qpath = tmp_path / "quotes.json"
    _write_quotes(qpath, [{"text": "A", "author": "x"}])
    cfg = _make_config(qpath, web_source_probability=1.0)

    quote, source = get_quote(
        cfg,
        [],
        now=NOW,
        rng=random.Random(0),
        web_fetcher=lambda: Quote("web quote", "web author"),
    )

    assert source == "web"
    assert quote.text == "web quote"


def test_web_failure_falls_back_to_curated(tmp_path: Path) -> None:
    qpath = tmp_path / "quotes.json"
    _write_quotes(qpath, [{"text": "A", "author": "x"}])
    cfg = _make_config(qpath, web_source_probability=1.0)

    def boom() -> Quote:
        raise RuntimeError("network down")

    quote, source = get_quote(
        cfg, [], now=NOW, rng=random.Random(0), web_fetcher=boom
    )

    assert source == "curated"
    assert quote.text == "A"


def test_missing_author_defaults_to_unknown(tmp_path: Path) -> None:
    qpath = tmp_path / "quotes.json"
    _write_quotes(qpath, [{"text": "A"}])
    cfg = _make_config(qpath)

    quote, _ = get_quote(cfg, [], now=NOW, rng=random.Random(0))

    assert quote.author == "Unknown"
