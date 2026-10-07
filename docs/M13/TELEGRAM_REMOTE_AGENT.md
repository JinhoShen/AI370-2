# Telegram Remote Agent

**Status: INSTALLED LOCALLY / BLOCKED pending BotFather credential and live pairing. Telegram end-to-end behavior is NOT TESTED.**

The minimal user-level service is `scripts/ai370-telegram-agent.service`; the stdlib-only controller is `scripts/telegram_agent.py`. It uses Telegram Bot API long polling, does not install a Python package, and launches the existing Codex CLI in the AI370-2 repository with `workspace-write` sandbox plus Codex automatic approval review. The CLI's configured model/provider is used (currently `gpt-6-luna`); this does not claim the Telegram requests use local Qwen.

Supported private-chat interactions:

- `/status` — Git branch/HEAD, short project status and agent queue state.
- `/work <request>` or plain text — submit work to Codex.
- `/continue <request>` — queue additional instructions; queued work resumes the same Codex session when available.
- `/cancel` — send an interrupt to the active Codex process.
- `/help` — command list.

Only a private chat can pair. The first pairing requires the locally generated one-time code. The paired Telegram user/chat identifiers and Codex session id are stored with mode 0600 under `~/.local/state/ai370-telegram/`; the bot token is loaded from a systemd credential sourced at `~/.config/ai370-telegram/bot-token`, outside Git. The controller does not execute Telegram text as a shell command. Work is delegated as a Codex prompt under the repository workspace sandbox.

## Install and activate

Create a bot with Telegram `@BotFather`, then store its token locally without putting it in Git or a chat:

```bash
install -d -m 700 ~/.config/ai370-telegram
read -rsp 'Bot token: ' t; printf '\n'
printf '%s' "$t" > ~/.config/ai370-telegram/bot-token
chmod 600 ~/.config/ai370-telegram/bot-token
unset t
```

Install the unit with `scripts/install_telegram_agent.sh`. Once the token is present, the installer enables the service. Get the local pairing code with:

```bash
python3 scripts/telegram_agent.py --show-pairing-code
```

In the bot's private chat, send `/pair <code>`. Check service state with `systemctl --user status ai370-telegram-agent.service` and logs with `journalctl --user -u ai370-telegram-agent.service`.

## Current evidence and limitation

Inventory on 2026-10-07 found no pre-existing Telegram bot, token environment variable, Telegram systemd service, or Telegram connector. Codex CLI 0.159.2 is installed and supports `codex exec resume <session-id>`; its current configured default is `gpt-6-luna`. Local Qwen tool-loop evidence remains separate and does not establish this Telegram integration's provider.

Local policy tests cover private-chat pairing, group rejection, unauthorized-user rejection, and basic token redaction. Since no bot token is configured, the unit remains installed but disabled and the following are **NOT TESTED**: Telegram API authentication, phone-to-host message delivery, live Codex execution from Telegram, session continuation through Telegram, and result delivery. Do not mark this integration PASS until those are exercised with the owner's bot and paired private chat.
