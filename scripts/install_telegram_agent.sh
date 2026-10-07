#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
unit_dir="$HOME/.config/systemd/user"
credential_dir="$HOME/.config/ai370-telegram"
state_dir="$HOME/.local/state/ai370-telegram"

install -d -m 700 "$credential_dir" "$state_dir" "$unit_dir"
install -m 644 "$repo_root/scripts/ai370-telegram-agent.service" \
  "$unit_dir/ai370-telegram-agent.service"
chmod 700 "$repo_root/scripts/telegram_agent.py"
systemctl --user daemon-reload
"$repo_root/scripts/telegram_agent.py" --show-pairing-code >/dev/null

if [[ -s "$credential_dir/bot-token" ]]; then
  chmod 600 "$credential_dir/bot-token"
  systemctl --user enable --now ai370-telegram-agent.service
  echo "Telegram agent enabled. Pair from a private chat using the local pairing code."
else
  systemctl --user disable --now ai370-telegram-agent.service >/dev/null 2>&1 || true
  echo "Unit installed but not started: local BotFather token is missing."
  echo "Store it at $credential_dir/bot-token with mode 0600, then run:"
  echo "  systemctl --user enable --now ai370-telegram-agent.service"
fi
