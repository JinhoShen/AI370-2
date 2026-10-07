#!/usr/bin/env python3
"""Allow one paired Telegram private chat to operate a sandboxed Codex session."""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path.home() / ".local/state/ai370-telegram"
STATE_FILE = STATE_DIR / "state.json"
PAIR_FILE = STATE_DIR / "pairing-code"
_credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "/nonexistent")
TOKEN_FILE = Path(os.environ.get("AI370_TELEGRAM_TOKEN_FILE") or (Path(_credential_dir) / "telegram_bot_token"))
CODEX = os.environ.get("AI370_CODEX_BIN", "/usr/local/bin/codex")
MAX_MESSAGE = 3500


def _private_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE_DIR.chmod(0o700)


def _read_state() -> dict[str, Any]:
    _private_state_dir()
    try:
        value = json.loads(STATE_FILE.read_text())
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_state(state: dict[str, Any]) -> None:
    _private_state_dir()
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(STATE_FILE)


def ensure_pairing_code() -> str:
    _private_state_dir()
    if not PAIR_FILE.exists() and not _read_state().get("allowed_user_id"):
        PAIR_FILE.write_text(secrets.token_urlsafe(12) + "\n")
        PAIR_FILE.chmod(0o600)
    try:
        return PAIR_FILE.read_text().strip()
    except FileNotFoundError:
        return ""


def _token() -> str:
    try:
        token = TOKEN_FILE.read_text().strip()
    except OSError as exc:
        raise RuntimeError(
            f"Telegram credential unavailable at {TOKEN_FILE}; install the bot token outside Git first"
        ) from exc
    if not re.fullmatch(r"\d{5,15}:[A-Za-z0-9_-]{20,}", token):
        raise RuntimeError("Telegram credential has an invalid Bot API token format")
    return token


class TelegramAPI:
    def __init__(self, token: str):
        self._token = token
        self._base = f"https://api.telegram.org/bot{token}/"

    def call(self, method: str, params: dict[str, Any] | None = None, timeout: int = 45) -> Any:
        body = urllib.parse.urlencode(params or {}).encode()
        request = urllib.request.Request(self._base + method, data=body)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Telegram API {method} failed: {exc.reason}") from exc
        if not result.get("ok"):
            raise RuntimeError(f"Telegram API {method} returned error code {result.get('error_code')}")
        return result.get("result")

    def send(self, chat_id: int, text: str) -> None:
        self.call("sendMessage", {"chat_id": chat_id, "text": text[:MAX_MESSAGE]})


def _safe_git_status() -> str:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "-C", str(ROOT), "branch", "--show-current"],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    progress = ROOT / "docs/BUILD_PROGRESS.md"
    snippet = ""
    if progress.exists():
        for line in progress.read_text(errors="replace").splitlines():
            if line.strip().startswith("#") or "Current status" in line or "目前狀態" in line:
                snippet = line.strip()[:220]
                break
    return f"AI370-2 狀態\nbranch: {branch}\nHEAD: {head}\n{snippet}"


def _redact(text: str) -> str:
    text = re.sub(r"\b\d{5,15}:[A-Za-z0-9_-]{20,}\b", "[REDACTED TELEGRAM TOKEN]", text)
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(api[_ -]?key|password|token|secret)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
    return text[:MAX_MESSAGE]


class Agent:
    def __init__(self, api: TelegramAPI):
        self.api = api
        self.state = _read_state()
        self.offset = int(self.state.get("update_offset", 0))
        self.job: asyncio.Task[None] | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue()
        self.stop = asyncio.Event()

    async def send(self, chat_id: int, text: str) -> None:
        await asyncio.to_thread(self.api.send, chat_id, _redact(text))

    async def handle(self, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message or not isinstance(message.get("text"), str):
            return
        chat = message.get("chat", {})
        sender = message.get("from", {})
        if chat.get("type") != "private" or not sender.get("id") or sender.get("id") != chat.get("id"):
            return
        user_id = int(sender["id"])
        chat_id = int(chat["id"])
        text = message["text"].strip()
        if not text:
            return

        allowed = self.state.get("allowed_user_id")
        if not allowed:
            if text.startswith("/pair ") and secrets.compare_digest(text[6:].strip(), ensure_pairing_code()):
                self.state["allowed_user_id"] = user_id
                self.state["chat_id"] = chat_id
                self.state.pop("pairing_code", None)
                _write_state(self.state)
                PAIR_FILE.unlink(missing_ok=True)
                await self.send(chat_id, "AI370-2 遠端 Agent 已綁定此私聊。輸入 /help 查看指令。")
            return
        if user_id != int(allowed) or chat_id != int(self.state.get("chat_id", -1)):
            return

        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0].lower()
        if command in {"/start", "/help"}:
            await self.send(chat_id, "可用指令：/status、/work <工作>、/continue <追加要求>、/cancel。一般文字也會作為工作要求。Codex 僅在 AI370-2 workspace-write sandbox 執行。")
        elif command == "/status":
            state = "Codex 工作執行中" if self.job and not self.job.done() else "Codex 閒置"
            await self.send(chat_id, f"{await asyncio.to_thread(_safe_git_status)}\nAgent: {state}\n待處理要求: {self.queue.qsize()}")
        elif command == "/cancel":
            if self.process and self.process.returncode is None:
                self.process.send_signal(signal.SIGINT)
                await self.send(chat_id, "已送出 Codex 中斷要求；sandbox 中的工作可能需要數秒結束。")
            else:
                await self.send(chat_id, "目前沒有執行中的 Codex 工作。")
        elif command in {"/work", "/continue"}:
            if not argument.strip():
                await self.send(chat_id, f"用法：{command} <工作要求>")
                return
            await self.enqueue(chat_id, argument.strip())
        elif text.startswith("/"):
            await self.send(chat_id, "未知指令；輸入 /help。")
        else:
            await self.enqueue(chat_id, text)

    async def enqueue(self, chat_id: int, prompt: str) -> None:
        if len(prompt) > 12000:
            await self.send(chat_id, "工作要求過長，請分段傳送（每則上限 12,000 字元）。")
            return
        await self.queue.put((chat_id, prompt))
        position = self.queue.qsize()
        if self.job and not self.job.done():
            await self.send(chat_id, f"已排入 Codex 工作佇列（第 {position} 項）；目前工作完成後會接續同一 session。")
        else:
            await self.send(chat_id, "已接收工作要求，開始交由 Codex 執行。")
            self.job = asyncio.create_task(self.run_queue())

    async def run_queue(self) -> None:
        while not self.queue.empty() and not self.stop.is_set():
            chat_id, prompt = await self.queue.get()
            await self.run_codex(chat_id, prompt)

    async def run_codex(self, chat_id: int, prompt: str) -> None:
        _private_state_dir()
        output_file = STATE_DIR / f"last-message-{int(time.time())}.txt"
        session_id = self.state.get("codex_session_id")
        system_prompt = (
            "You are the AI370-2 engineering agent. Work only in the repository at /home/shen/AI370-2. "
            "Respect repository instructions, preserve protected GPU/NPU/FPGA stacks, do not run hardware programming "
            "or destructive operations unless the user explicitly requested that exact action, keep evidence truthful, "
            "and report changes and verification. This Telegram message is the user's task."
        )
        full_prompt = f"{system_prompt}\n\nUser request:\n{prompt}" if not session_id else prompt
        if session_id:
            args = [CODEX, "exec", "resume", session_id, "--json", "--output-last-message", str(output_file), full_prompt]
        else:
            args = [CODEX, "exec", "--json", "--sandbox", "workspace-write", "--approve-for-me", "--cd", str(ROOT), "--output-last-message", str(output_file), full_prompt]
        started = time.monotonic()
        try:
            self.process = await asyncio.create_subprocess_exec(
                *args, cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                start_new_session=True, limit=4 * 1024 * 1024,
            )
            async def collect_session_id() -> None:
                async for raw_line in self.process.stdout:
                    try:
                        event = json.loads(raw_line)
                        if event.get("type") in {"thread.started", "thread.resumed"}:
                            tid = event.get("thread_id") or event.get("thread", {}).get("id")
                            if tid:
                                self.state["codex_session_id"] = tid
                                _write_state(self.state)
                    except (json.JSONDecodeError, AttributeError):
                        continue

            stdout_task = asyncio.create_task(collect_session_id())
            stderr_task = asyncio.create_task(self.process.stderr.read())
            last_ping = started
            while self.process.returncode is None:
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=30)
                except asyncio.TimeoutError:
                    pass
                now = time.monotonic()
                if now - last_ping >= 120 and self.process.returncode is None:
                    await self.send(chat_id, "Codex 仍在執行；完成或遇到阻礙時會回報。")
                    last_ping = now
            await stdout_task
            stderr = (await stderr_task).decode(errors="replace")
            result = output_file.read_text(errors="replace").strip() if output_file.exists() else ""
            output_file.unlink(missing_ok=True)
            if not result:
                result = f"Codex 結束，exit={self.process.returncode}，但沒有 final response。\n{stderr[-1200:]}"
            elapsed = int(time.monotonic() - started)
            await self.send(chat_id, f"Codex 完成（exit {self.process.returncode}，{elapsed}s）：\n{result}")
        except Exception as exc:  # report controller failures without exposing traceback or credentials
            await self.send(chat_id, f"Codex 啟動/執行失敗：{type(exc).__name__}: {exc}")
        finally:
            self.process = None

    async def poll(self) -> None:
        while not self.stop.is_set():
            try:
                updates = await asyncio.to_thread(
                    self.api.call, "getUpdates", {"offset": self.offset, "timeout": 30, "allowed_updates": '["message","edited_message"]'}, 40,
                )
                for update in updates:
                    self.offset = int(update["update_id"]) + 1
                    self.state["update_offset"] = self.offset
                    _write_state(self.state)
                    await self.handle(update)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"poll error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                await asyncio.sleep(5)


async def main() -> None:
    if sys.argv[1:] == ["--show-pairing-code"]:
        code = ensure_pairing_code()
        if code:
            print(code)
        else:
            print("Already paired or pairing code unavailable")
        return
    code = ensure_pairing_code()
    if code:
        print("Telegram agent requires private-chat pairing. Retrieve code locally with:", flush=True)
        print(f"  {sys.executable} {Path(__file__).resolve()} --show-pairing-code", flush=True)
    api = TelegramAPI(_token())
    me = await asyncio.to_thread(api.call, "getMe")
    print(f"Telegram bot ready: @{me.get('username', 'unknown')} (token not logged)", flush=True)
    agent = Agent(api)
    await agent.poll()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
