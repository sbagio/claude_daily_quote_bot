"""Entry point: select a quote, send it to Telegram, persist state."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import load_config
from .quotes import Quote, get_quote
from .telegram import format_message, format_plain, send_message

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("daily_quote")

DATE_FORMAT = "%A, %B %d, %Y"

# GitHub's scheduled-run queue delay swings from minutes to 5+ hours, so the cron only provides
# hourly wake-up slots and this gate picks the first one at or after EARLIEST_SEND, Israel time.
DELIVERY_TZ = ZoneInfo("Asia/Jerusalem")
EARLIEST_SEND = time(6, 30)


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("State file %s is corrupt; starting fresh.", path)
        return []
    return data if isinstance(data, list) else []


def append_history(
    path: Path, quote: Quote, source: str, now: datetime
) -> None:
    history = load_history(path)
    history.append(
        {
            "hash": quote.hash,
            "text": quote.text,
            "author": quote.author,
            "source": source,
            "sent_at": now.isoformat(),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def should_send(now: datetime, history: list[dict[str, Any]]) -> tuple[bool, str]:
    local_now = now.astimezone(DELIVERY_TZ)
    for entry in history:
        try:
            sent_at = datetime.fromisoformat(entry["sent_at"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Ignoring history entry with unreadable sent_at: %r", entry)
            continue
        if sent_at.astimezone(DELIVERY_TZ).date() == local_now.date():
            return False, "already sent today"
    if local_now.time() < EARLIEST_SEND:
        return False, f"too early ({local_now:%H:%M} Israel time); a later slot will send"
    return True, "due"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a daily quote to Telegram.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Select and print the quote without sending or writing state.",
    )
    parser.add_argument(
        "--ignore-schedule",
        action="store_true",
        help="Send now regardless of the time of day or whether today's quote already went out.",
    )
    args = parser.parse_args(argv)

    config = load_config()
    now = datetime.now(timezone.utc)
    history = load_history(config.state_path)

    due, reason = should_send(now, history)
    if args.ignore_schedule:
        logger.info("Schedule gate bypassed (would have been: %s).", reason)
    elif not due:
        logger.info("Not sending: %s.", reason)
        return 0

    quote, source = get_quote(config, history, now=now)
    date_label = now.astimezone(DELIVERY_TZ).strftime(DATE_FORMAT)

    if args.dry_run:
        logger.info("[dry-run] source=%s", source)
        print(format_plain(quote.text, quote.author, date_label))
        return 0

    if not config.telegram_bot_token or not config.telegram_chat_id:
        logger.error(
            "Missing TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID. "
            "Set them in .env (local) or Actions Secrets (CI)."
        )
        return 1

    message = format_message(quote.text, quote.author, date_label)
    send_message(config.telegram_bot_token, config.telegram_chat_id, message)
    append_history(config.state_path, quote, source, now)
    logger.info("Sent quote (source=%s) to chat %s.", source, config.telegram_chat_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
