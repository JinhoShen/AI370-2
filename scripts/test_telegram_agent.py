#!/usr/bin/env python3
import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("telegram_agent.py")
SPEC = importlib.util.spec_from_file_location("telegram_agent", SCRIPT)
bot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bot)


class FakeAPI:
    def __init__(self):
        self.messages = []

    def send(self, chat_id, text):
        self.messages.append((chat_id, text))


class TelegramPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        bot.STATE_DIR = root
        bot.STATE_FILE = root / "state.json"
        bot.PAIR_FILE = root / "pairing-code"
        bot.ensure_pairing_code()
        self.code = bot.PAIR_FILE.read_text().strip()
        self.api = FakeAPI()
        self.agent = bot.Agent(self.api)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_pairing_binds_only_private_user_and_consumes_code(self):
        await self.agent.handle({"message": {"text": f"/pair {self.code}", "chat": {"id": 71, "type": "private"}, "from": {"id": 71}}})
        self.assertEqual(self.agent.state["allowed_user_id"], 71)
        self.assertEqual(self.agent.state["chat_id"], 71)
        self.assertFalse(bot.PAIR_FILE.exists())
        self.assertIn("已綁定", self.api.messages[-1][1])

    async def test_group_pairing_is_rejected(self):
        await self.agent.handle({"message": {"text": f"/pair {self.code}", "chat": {"id": -20, "type": "group"}, "from": {"id": 71}}})
        self.assertNotIn("allowed_user_id", self.agent.state)
        self.assertEqual(self.api.messages, [])

    async def test_unauthorized_user_is_ignored(self):
        self.agent.state.update(allowed_user_id=71, chat_id=71)
        await self.agent.handle({"message": {"text": "/status", "chat": {"id": 72, "type": "private"}, "from": {"id": 72}}})
        self.assertEqual(self.api.messages, [])

    async def test_secret_redaction(self):
        self.assertNotIn("123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", bot._redact("123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"))
        self.assertIn("[REDACTED", bot._redact("password=hunter2"))


if __name__ == "__main__":
    unittest.main()
