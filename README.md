# Claude Daily Quote Bot

Telegram: [@claude_daily_quote_bot](https://t.me/claude_daily_quote_bot)

Sends one quote a day to your Telegram, for free, via GitHub Actions cron.
See [SPEC.md](SPEC.md) for the full feature list.

## How it works

`python -m src.main` picks a quote (curated list + free web API, no-repeat window),
formats it, sends it via the Telegram Bot API, and appends to `state/sent_history.json`.
GitHub Actions runs it daily and commits the updated state back.

## Setup

### 1. Create your Telegram bot (you do this — I can't touch your token)

1. Open Telegram, message **[@BotFather](https://t.me/BotFather)**, send `/newbot`.
2. Follow the prompts; it gives you a **bot token** like `123456:ABC-DEF...`.
3. **Message your new bot** anything (say "hi") so it can message you back.
4. Get your **chat id**: open in a browser
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   and copy `result[0].message.chat.id` (a number).

### 2. Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # or: uv venv && source .venv/bin/activate
pip install -r requirements-dev.txt                 # or: uv pip install -r requirements-dev.txt

cp .env.example .env       # then paste your token + chat id into .env

python -m src.main --dry-run   # prints the quote, sends nothing
python -m src.main             # actually sends to your Telegram
```

### 3. Deploy on GitHub Actions (free)

1. Push this repo to a **private** GitHub repo.
2. Repo → **Settings → Secrets and variables → Actions** → add two secrets:
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
3. **Actions** tab → *Daily Quote* → **Run workflow** to test the manual trigger. Manual runs
   send immediately, even if today's quote already went out.
4. The `schedule` cron then wakes the job hourly overnight; the quote lands between about
   06:30 and 07:30 Israel time.

> **Delivery time**: GitHub starts scheduled runs anywhere from minutes to 5+ hours late, so the
> cron in [`.github/workflows/daily-quote.yml`](.github/workflows/daily-quote.yml) is a set of
> hourly wake-up slots, not the send time. `should_send` in [`src/main.py`](src/main.py) sends on
> the first slot at or after `EARLIEST_SEND` (06:30, `Asia/Jerusalem`, DST-aware) and skips the
> rest of the day. To move delivery, change `EARLIEST_SEND` and shift the cron slots so they
> still span "target minus the worst queue delay" through the target.

> **60-day caveat**: GitHub disables scheduled workflows after 60 days of no repo activity.
> The daily state commit counts as activity, so this stays alive on its own.

## Tests

```bash
pytest                 # offline, deterministic (stubbed web source + injected RNG/clock)
```

## Configuration

All optional knobs are env vars — see [.env.example](.env.example). Notably
`WEB_SOURCE_PROBABILITY` (curated vs web mix) and `NO_REPEAT_DAYS`.

## Adding your own quotes

Edit [quotes.json](quotes.json): objects of `{ "text", "author", "tags" }`. `tags` is
optional and currently informational.
