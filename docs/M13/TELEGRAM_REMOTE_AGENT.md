# Telegram Remote Local Agent

**Status: Local Agent integration IMPLEMENTED; Telegram E2E BLOCKED pending BotFather credential and private-chat pairing.** No token is stored in Git and none was inspected during this work.

The user-level service `scripts/ai370-telegram-agent.service` runs the stdlib controller `scripts/telegram_agent.py`. For `/work`, `/continue`, or ordinary text, the controller launches `scripts/local_agent.py` in the AI370-2 repository. The Local Agent calls the already loaded Qwen3.8 model through the local Lemonade endpoint `127.0.0.1:13305`; it does not launch Codex CLI, call OpenAI APIs, or use a cloud model. The code execution and patch boundaries are defined in [M13 RESULT](RESULT.md) and the [Local Agent source](../../scripts/local_agent.py).

Telegram is only the remote transport. It requires Internet access to the Telegram Bot API and cannot transport messages while the host is offline. The Local Agent itself supports local inference and sandboxed tools without Internet. Telegram's long-poll process never executes message text as a shell command. Model-generated patches are restricted by the Local Agent's path and patch policy; verification commands are selected from a fixed allowlist. The Local Agent's RTL/XSim flow exposes only a fixed Vivado runner, with host NIC identity visible because the existing license is host-MAC-bound.

Supported private-chat interactions:

- `/status` — Git branch/HEAD, short project status and Local Agent queue state.
- `/work <request>` or plain text — start a local Qwen-backed task.
- `/continue <request>` — queue an additional task for the Local Agent after the active job.
- `/cancel` — interrupt the active Local Agent process group.
- `/help` — list commands.

Only a private chat can pair. The first pairing requires the locally generated one-time code. Paired Telegram user/chat identifiers are stored with mode 0600 under `~/.local/state/ai370-telegram/`; the bot token is loaded from a systemd credential sourced at `~/.config/ai370-telegram/bot-token`, outside Git. The controller stores no Codex session and does not save full model traces for Telegram requests.

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

## Current verification and limits

The standalone Local Agent's bounded Qwen → RTL → XSim error-feedback repair passed, and its policy suite passed 4/4. Telegram controller policy tests passed 4/4. These checks do not prove Telegram API access. No BotFather credential is currently configured, so the user service remains disabled; bot authentication, phone-to-host message delivery, private pairing, remote task execution, queued follow-up delivery and result delivery are **NOT TESTED / WAITING_USER**.

A separate offline smoke confirmed local Qwen inference plus a local read-only tool result with Bubblewrap external network access blocked. The host was not physically disconnected, and the Telegram transport requires Internet by design. Do not mark Telegram E2E or full system air-gap PASS until independently exercised with the owner's bot and paired private chat.

## Historical note

Inventory on 2026-10-07 found no pre-existing Telegram bot, token environment variable, Telegram systemd service, or Telegram connector. The first controller prototype delegated to Codex CLI; that implementation is superseded by the current direct Local Agent path. The historical implementation and tests remain in Git history.
