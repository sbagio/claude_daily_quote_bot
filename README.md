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

1. Push this repo to a **public** GitHub repo (see *Cost* below — public is what makes it free).
2. Repo → **Settings → Secrets and variables → Actions** → add two secrets:
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Secrets stay hidden on a public repo.
3. **Actions** tab → *Daily Quote* → **Run workflow**, tick **force**, to test a send.

> **Delivery time (07:00 Israel)**: GitHub starts scheduled runs 4–8h late and creates only
> some of them, so the cron is a set of hourly wake-up slots, evening through morning (UTC).
> `time_until_due` in [`src/main.py`](src/main.py) decides: the first run that starts within
> `MAX_WAIT_MINUTES` (330) of `SEND_AT` (07:00, `Asia/Jerusalem`, DST-aware) sleeps until 07:00
> and sends; earlier runs exit; later runs find today's send in `state/sent_history.json` and
> exit. If no run starts before 07:00, the first one after it sends late.

> **Cost: zero.** Standard GitHub-hosted runners are free and unlimited on public repos. The
> workflow checks the repo's visibility on every run and passes a wait of 0 if it is not
> public (or the check fails), so making it private again can't run up sleeping minutes; the
> short slot runs alone fit the free private allowance, and a $0 spending limit blocks rather
> than bills. Triggers are only `schedule` and `workflow_dispatch` (write access needed), so
> nobody else can run it.

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
