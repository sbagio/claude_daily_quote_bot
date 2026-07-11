# Daily Quote Bot

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
3. **Actions** tab → *Daily Quote* → **Run workflow** to test the manual trigger.
4. The `schedule` cron then fires daily. Edit the cron in
   [`.github/workflows/daily-quote.yml`](.github/workflows/daily-quote.yml) to your time.

> **Timezone**: cron is UTC. `0 6 * * *` = 06:00 UTC. For 08:00 in Israel (UTC+3) use
> `0 5 * * *`. DST shifts local time by an hour since UTC offset is fixed.

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
