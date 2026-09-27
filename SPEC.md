# Claude Daily Quote Bot — Specification

A personal app that delivers one quote to me every day via **Telegram**, for free.

## Why Telegram (not WhatsApp)

WhatsApp was the original ask, but every path has friction:

| Option | Cost | Notes |
|---|---|---|
| Twilio WhatsApp | ~$0.005/msg + Meta fees | Needs a Twilio + business account |
| Meta Cloud API | Free tier, then paid | Business account, number registration, review |
| whatsapp-web.js | Free | Violates WhatsApp ToS, breaks often, QR re-auth |
| **Telegram Bot** | **Free forever** | Official API, ~1 HTTP call, never breaks |

Telegram wins on cost, simplicity, and reliability. The only tradeoff: the message arrives
in Telegram instead of WhatsApp. The sender is isolated in one module, so a WhatsApp sender
could be added later behind the same interface.

## Architecture

- **Language**: Python 3.11+
- **Runtime**: GitHub Actions cron (serverless, free, private repo)
- **Delivery**: Telegram Bot API
- **Quotes**: hybrid — curated local `quotes.json` + a free public API, with fallback
- **State**: `state/sent_history.json`, committed back by the Action each run

---

## Requirements (Features)

### F1 — Daily scheduled delivery
- Sends exactly one quote per day, around 07:00 Israel time (first run at or after 06:30
  `Asia/Jerusalem`; `EARLIEST_SEND` in `src/main.py`).
- GitHub's scheduled-run queue delay varies from minutes to 5+ hours (observed Sep 2026), so
  the cron fires hourly slots overnight and `should_send` sends on the first slot past
  `EARLIEST_SEND` whose Israel date has no entry in `sent_history.json`; other slots exit 0.
- Manual trigger (`workflow_dispatch`) passes `--ignore-schedule` and sends immediately.

### F2 — Hybrid quote sourcing
- **Curated source**: `quotes.json` — a list I own (`{text, author, tags}` objects).
- **Web source**: free public API (default ZenQuotes; Quotable as an alternative). No key.
- **Selection**: configurable weight (`WEB_SOURCE_PROBABILITY`, default `0.0` = curated bank
  only). Raise toward 1.0 to mix in random web quotes; each run rolls the weight.
- **Fallback**: if the web API fails or times out, fall back to curated so a message is
  always sent.

### F3 — No-repeat window
- Avoids repeating any quote sent within the last `NO_REPEAT_DAYS` (default 30).
- Tracks a stable hash of each sent quote in state (F8).
- If every curated quote is inside the window, picks the least-recently-sent one.

### F4 — Telegram delivery
- Sends via `POST api.telegram.org/bot<token>/sendMessage`. No SDK — one `requests` call.
- Uses `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
- Verifies HTTP 200 / `ok:true`; non-OK is a hard error (F9).

### F5 — Message formatting
- MarkdownV2 format: `"<quote>"` newline `— <author>`, with a small date header.
- Handles missing author ("Unknown").
- Escapes reserved MarkdownV2 characters.

### F6 — Config & secrets
- All config via env vars, loaded by `src/config.py` (`python-dotenv` for local runs).
- Secrets never committed — `.env` locally (gitignored), Actions Secrets in CI.
- `.env.example` documents every variable.

### F7 — Scheduling on GitHub Actions
- `.github/workflows/daily-quote.yml`: `schedule` cron + `workflow_dispatch`.
- Private repo; ~7 short slot runs/day ≈ 210 billed min/month, well inside the free tier.
- **Caveat**: GitHub auto-disables cron workflows after 60 days of repo inactivity. Solved
  by F8's daily state commit, which counts as activity.

### F8 — State persistence
- `state/sent_history.json`: append-only log of `{hash, text, author, sent_at}`.
- The Action commits the updated state back to the repo after a successful send.

### F9 — Error handling & observability
- No silent failures: errors are logged with context and exit non-zero so the Action shows
  red (and emails on failure via repo notification settings).
- Web-API failure is *not* fatal (falls back). Telegram-send failure *is* fatal.

### F10 — Local run & dry-run mode
- `python -m src.main` runs the full flow.
- `--dry-run` selects and prints the quote without sending or writing state.
