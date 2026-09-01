"""Telegram bridge: routes phone messages to Claude and streams replies back."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .auth import Allowlist
from .claude_runner import ClaudeRunner
from .config import Settings
from .util import chunk_text

log = logging.getLogger(__name__)

_START_TEXT = (
    "👋 This is your private Claude Code + NotebookLM assistant.\n\n"
    "Send me a question or task and I'll run it with access to your NotebookLM "
    "knowledge base.\n\n"
    "Commands:\n"
    "• /reset — start a fresh conversation\n"
    "• /diag — check the model connection\n"
    "• /allowlist — show authorized chats (admins only)"
)

# Substrings that mark a model-access (auth/provider/gateway) failure.
_MODEL_ERROR_MARKERS = (
    "provider",
    "gateway",
    "auth",
    "credit",
    "quota",
    "401",
    "403",
    "api key",
    "api_key",
)


class TelegramBridge:
    """Wires together the allowlist, the Claude runner, and the Telegram app."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.allowlist = Allowlist(settings.allowlist_path)
        # Pre-authorize any chat IDs supplied via configuration.
        for chat_id in settings.allowed_chat_ids:
            if not self.allowlist.is_allowed(chat_id):
                self.allowlist.add(chat_id, name="preauthorized")
        self.runner = ClaudeRunner(settings)

        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self.app.add_handler(CommandHandler("start", self._on_start))
        self.app.add_handler(CommandHandler("reset", self._on_reset))
        self.app.add_handler(CommandHandler("diag", self._on_diag))
        self.app.add_handler(CommandHandler("allowlist", self._on_allowlist))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        self.app.post_shutdown = self._post_shutdown

    # --- command handlers ------------------------------------------------
    async def _on_start(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(_START_TEXT)

    async def _on_reset(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        if not self.allowlist.is_allowed(chat_id):
            return
        await self.runner.reset(chat_id)
        await update.message.reply_text("🧹 Conversation reset.")

    async def _on_diag(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        if not self.allowlist.is_allowed(chat_id):
            return
        await update.effective_chat.send_action(ChatAction.TYPING)
        lines = [f"🔧 Model config: {self.settings.auth_summary()}"]
        try:
            reply = await self.runner.ping()
            lines.append(f"✅ Model OK — replied: {reply[:60]}")
        except Exception as exc:  # noqa: BLE001 — report the real cause to the user
            log.exception("Model diagnostic failed for chat %s", chat_id)
            lines.append(f"⚠️ Model error: {exc}")
            lines.append(
                "Fix: check ANTHROPIC_API_KEY (valid & funded) and that "
                "ANTHROPIC_BASE_URL is unset unless you use a gateway."
            )
        await update.message.reply_text("\n".join(lines))

    async def _on_allowlist(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        if not self.allowlist.is_allowed(chat_id):
            return
        ids = self.allowlist.all_ids()
        await update.message.reply_text(
            "Authorized chats:\n" + "\n".join(f"• {i}" for i in ids)
        )

    # --- message handler -------------------------------------------------
    async def _on_message(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        chat_id = chat.id

        if not self.allowlist.is_allowed(chat_id):
            name = chat.full_name or chat.title or chat.username or ""
            code = self.allowlist.start_pairing(chat_id, name=name)
            log.info("Pairing requested by chat %s (%s): code %s", chat_id, name, code)
            await update.message.reply_text(
                f"🔐 Your pairing code is *{code}*\n\n"
                "Enter it in the bridge terminal to authorize this chat.",
                parse_mode="Markdown",
            )
            return

        prompt = update.message.text
        await chat.send_action(ChatAction.TYPING)
        try:
            async for piece in self.runner.run(chat_id, prompt):
                await chat.send_action(ChatAction.TYPING)
                for part in chunk_text(piece):
                    await update.message.reply_text(part)
        except Exception as exc:  # noqa: BLE001 — surface failures to the user
            log.exception("Claude run failed for chat %s", chat_id)
            reply = f"⚠️ Error: {exc}"
            if any(m in str(exc).lower() for m in _MODEL_ERROR_MARKERS):
                reply += (
                    "\n\nThis looks like a model-access problem. Run /diag, and check "
                    "ANTHROPIC_API_KEY (valid & funded) plus that ANTHROPIC_BASE_URL is "
                    "unset unless you intend a gateway. Full traceback: "
                    "`journalctl -u claude4nblm`."
                )
            await update.message.reply_text(reply)

    # --- pairing from the terminal --------------------------------------
    async def authorize_via_code(self, code: str) -> int | None:
        """Redeem a pairing ``code`` entered at the terminal.

        On success, authorizes the chat, notifies it, and returns the chat ID.
        """
        chat_id = self.allowlist.redeem(code)
        if chat_id is None:
            return None
        try:
            await self.app.bot.send_message(
                chat_id, "✅ This chat is now authorized. Send me a task!"
            )
        except Exception:  # noqa: BLE001 — notification is best-effort
            log.warning("Could not notify chat %s after authorization", chat_id)
        return chat_id

    async def _post_shutdown(self, _app: Application) -> None:
        await self.runner.shutdown()
