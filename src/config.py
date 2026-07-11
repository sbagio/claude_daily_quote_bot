"""Configuration loading. All tunables come from env vars with sane defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUOTES_PATH = ROOT / "quotes.json"
DEFAULT_STATE_PATH = ROOT / "state" / "sent_history.json"

DEFAULT_WEB_SOURCE_PROBABILITY = 0.5
DEFAULT_NO_REPEAT_DAYS = 30
DEFAULT_WEB_TIMEOUT_SECONDS = 10
# ZenQuotes needs no API key. Quotable (https://api.quotable.io/random) is a drop-in
# alternative — the web parser understands both response shapes.
DEFAULT_WEB_SOURCE_URL = "https://zenquotes.io/api/random"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    quotes_path: Path
    state_path: Path
    web_source_probability: float
    no_repeat_days: int
    web_timeout_seconds: int
    web_source_url: str


def load_config() -> Config:
    load_dotenv()
    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        quotes_path=Path(os.getenv("QUOTES_PATH", str(DEFAULT_QUOTES_PATH))),
        state_path=Path(os.getenv("STATE_PATH", str(DEFAULT_STATE_PATH))),
        web_source_probability=float(
            os.getenv("WEB_SOURCE_PROBABILITY", str(DEFAULT_WEB_SOURCE_PROBABILITY))
        ),
        no_repeat_days=int(os.getenv("NO_REPEAT_DAYS", str(DEFAULT_NO_REPEAT_DAYS))),
        web_timeout_seconds=int(
            os.getenv("WEB_TIMEOUT_SECONDS", str(DEFAULT_WEB_TIMEOUT_SECONDS))
        ),
        web_source_url=os.getenv("WEB_SOURCE_URL", DEFAULT_WEB_SOURCE_URL),
    )
