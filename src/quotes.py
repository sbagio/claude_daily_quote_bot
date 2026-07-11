"""Quote sourcing: curated file + web API, weighted selection, no-repeat window."""

from __future__ import annotations

import hashlib
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from .config import Config

logger = logging.getLogger(__name__)

_HASH_LENGTH = 16


@dataclass(frozen=True)
class Quote:
    text: str
    author: str

    @property
    def hash(self) -> str:
        # Normalize so trivial whitespace/case differences don't dodge the no-repeat window.
        normalized = self.text.strip().lower()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return digest[:_HASH_LENGTH]


def load_curated(path: Path) -> list[Quote]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    quotes: list[Quote] = []
    for item in raw:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        author = str(item.get("author") or "Unknown").strip() or "Unknown"
        quotes.append(Quote(text=text, author=author))
    if not quotes:
        raise ValueError(f"No usable quotes found in {path}")
    return quotes


def _parse_sent_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def recent_hashes(
    history: list[dict[str, Any]], no_repeat_days: int, now: datetime
) -> set[str]:
    cutoff = now - timedelta(days=no_repeat_days)
    recent: set[str] = set()
    for entry in history:
        ts = _parse_sent_at(entry.get("sent_at"))
        if ts is not None and ts >= cutoff:
            recent.add(str(entry.get("hash")))
    return recent


def _last_sent_map(history: list[dict[str, Any]]) -> dict[str, datetime]:
    last: dict[str, datetime] = {}
    for entry in history:
        ts = _parse_sent_at(entry.get("sent_at"))
        h = str(entry.get("hash"))
        if ts is not None and (h not in last or ts > last[h]):
            last[h] = ts
    return last


def select_curated(
    quotes: list[Quote],
    history: list[dict[str, Any]],
    no_repeat_days: int,
    now: datetime,
    rng: random.Random,
) -> Quote:
    blocked = recent_hashes(history, no_repeat_days, now)
    candidates = [q for q in quotes if q.hash not in blocked]
    if candidates:
        return rng.choice(candidates)
    # Everything is inside the no-repeat window: fall back to the least-recently-sent quote.
    logger.info("All curated quotes are within the no-repeat window; picking oldest.")
    last_sent = _last_sent_map(history)
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return min(quotes, key=lambda q: last_sent.get(q.hash, epoch))


def fetch_web(url: str, timeout: int) -> Quote:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    item = data[0] if isinstance(data, list) else data
    # ZenQuotes uses q/a; Quotable uses content/author.
    text = str(item.get("q") or item.get("content") or "").strip()
    author = str(item.get("a") or item.get("author") or "Unknown").strip() or "Unknown"
    if not text:
        raise ValueError(f"Web source returned no quote text: {item!r}")
    return Quote(text=text, author=author)


def get_quote(
    config: Config,
    history: list[dict[str, Any]],
    now: datetime | None = None,
    rng: random.Random | None = None,
    web_fetcher: Callable[[], Quote] | None = None,
) -> tuple[Quote, str]:
    """Return (quote, source) where source is "web" or "curated"."""
    now = now or datetime.now(timezone.utc)
    rng = rng or random.Random()
    web_fetcher = web_fetcher or (
        lambda: fetch_web(config.web_source_url, config.web_timeout_seconds)
    )
    curated = load_curated(config.quotes_path)

    if rng.random() < config.web_source_probability:
        try:
            return web_fetcher(), "web"
        except Exception as exc:  # noqa: BLE001 - fall back to curated, never fail the send
            logger.warning("Web source failed (%s); falling back to curated.", exc)

    return select_curated(curated, history, config.no_repeat_days, now, rng), "curated"
