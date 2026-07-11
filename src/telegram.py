"""Telegram Bot API delivery and message formatting."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
# Reserved characters that must be backslash-escaped in Telegram MarkdownV2.
_MARKDOWN_V2_SPECIAL = set(r"_*[]()~`>#+-=|{}.!")


def escape_markdown_v2(text: str) -> str:
    return "".join("\\" + c if c in _MARKDOWN_V2_SPECIAL else c for c in text)


def format_message(text: str, author: str, date_label: str) -> str:
    header = escape_markdown_v2(f"🗓 {date_label}")
    body = escape_markdown_v2(f"“{text}”")
    signature = escape_markdown_v2(f"— {author}")
    return f"*{header}*\n\n{body}\n\n_{signature}_"


def format_plain(text: str, author: str, date_label: str) -> str:
    return f"🗓 {date_label}\n\n“{text}”\n\n— {author}"


def send_message(token: str, chat_id: str, text: str, timeout: int = 10) -> None:
    url = f"{API_BASE}/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram API HTTP {resp.status_code}: {resp.text}")
    payload = resp.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API returned an error: {payload}")
