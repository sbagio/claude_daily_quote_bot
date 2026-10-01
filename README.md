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
3. **Actions** tab → *Daily Quote* → **Run workflow**, tick **force**, to test a send.
4. Set up the 07:00 trigger (below). The `schedule` cron is only a late backup.

> **Delivery time**: GitHub starts scheduled runs hours late and drops many of them (Sep 2026:
> 2 of 7 hourly slots created per day), so it can't deliver at a set morning time. Instead an
> external cron calls the `workflow_dispatch` API, which starts within seconds.
> `should_send` in [`src/main.py`](src/main.py) still gates every non-forced run: it sends only
> at or after `EARLIEST_SEND` (06:30, `Asia/Jerusalem`) and once per Israel date, so the
> backup cron and any retry skip once today's quote is out.
>
> **External trigger setup** (cron-job.org, free):
> 1. GitHub → Settings → Developer settings → **Fine-grained token**: repository access
>    *Only* `claude_daily_quote_bot`, permission **Actions: Read and write**. Nothing else.
> 2. cron-job.org → new job, schedule daily **07:00**, timezone **Asia/Jerusalem**
>    (handles DST), method **POST**, URL
>    `https://api.github.com/repos/sbagio/claude_daily_quote_bot/actions/workflows/daily-quote.yml/dispatches`,
>    headers `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
>    body `{"ref":"main"}`. Success is HTTP 204.
> 3. Fine-grained tokens expire; set a calendar reminder for the expiry date.

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
