"""Entry point: select a quote, send it to Telegram, persist state."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time as clock
from datetime import datetime, time, timedelta, timezone
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

# GitHub starts scheduled runs hours late and skips many, so the cron only provides overnight
# wake-up slots: the first run that starts within the wait window sleeps until SEND_AT (Israel
# time) and sends, later runs see today's entry in the history and exit.
DELIVERY_TZ = ZoneInfo("Asia/Jerusalem")
SEND_AT = time(7, 0)


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


def time_until_due(now: datetime, history: list[dict[str, Any]]) -> timedelta | None:
    """None if today's quote (Israel date) already went out, else the wait until SEND_AT (>= 0)."""
    local_now = now.astimezone(DELIVERY_TZ)
    for entry in history:
        try:
            sent_at = datetime.fromisoformat(entry["sent_at"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Ignoring history entry with unreadable sent_at: %r", entry)
            continue
        if sent_at.astimezone(DELIVERY_TZ).date() == local_now.date():
            return None
    due_at = datetime.combine(local_now.date(), SEND_AT, tzinfo=DELIVERY_TZ)
    return max(due_at - local_now, timedelta(0))


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
    parser.add_argument(
        "--max-wait-minutes",
        type=int,
        default=0,
        help="If started before SEND_AT, sleep until then when it is at most this far away; "
        "otherwise exit and leave it to a later run.",
    )
    args = parser.parse_args(argv)

    config = load_config()
    now = datetime.now(timezone.utc)
    history = load_history(config.state_path)

    wait = time_until_due(now, history)
    if args.ignore_schedule:
        logger.info("Schedule gate bypassed.")
    elif wait is None:
        logger.info("Not sending: already sent today.")
        return 0
    elif wait > timedelta(minutes=args.max_wait_minutes):
        logger.info(
            "Not sending: %s until %s Israel time exceeds the %d-minute wait limit.",
            wait, SEND_AT.strftime("%H:%M"), args.max_wait_minutes,
        )
        return 0
    elif wait:
        logger.info("Waiting %s until %s Israel time.", wait, SEND_AT.strftime("%H:%M"))
        clock.sleep(wait.total_seconds())
        now = datetime.now(timezone.utc)

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
