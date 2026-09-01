"""Entry point: start the Telegram bridge and a terminal pairing-code reader.

Run with ``python -m claude4nblm`` (or the ``claude4nblm`` console script).
While running, paste a pairing code at this terminal and press Enter to
authorize the chat that requested it.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from telegram.ext import Application

from .bot import TelegramBridge
from .config import ConfigError, load_settings

log = logging.getLogger("claude4nblm")


async def _stdin_pairing_loop(bridge: TelegramBridge) -> None:
    """Read pairing codes from stdin and authorize the matching chats."""
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:  # EOF — e.g. no TTY (systemd). Stop reading silently.
            return
        code = line.strip()
        if not code:
            continue
        chat_id = await bridge.authorize_via_code(code)
        if chat_id is not None:
            print(f"✅ Authorized chat {chat_id}", flush=True)
        else:
            print("❌ No active pairing matches that code.", flush=True)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    log.info("Model auth — %s", settings.auth_summary())
    if not settings.anthropic_api_key:
        log.warning(
            "ANTHROPIC_API_KEY is not set; relying on an existing Claude Code "
            "CLI login. Set it in .env for unattended/VPS use."
        )

    bridge = TelegramBridge(settings)

    async def _preflight() -> None:
        """Verify model access once at startup; log the real cause on failure."""
        try:
            reply = await bridge.runner.ping()
            log.info("Model preflight OK (%r)", reply[:40])
        except Exception:  # noqa: BLE001 — non-fatal; keep the bot up for /diag
            log.exception(
                "Model preflight FAILED — the bot is up but model calls will error. "
                "Check ANTHROPIC_API_KEY (valid & funded) and that ANTHROPIC_BASE_URL "
                "is unset unless you intend to use a gateway."
            )

    async def _post_init(app: Application) -> None:
        app.create_task(_stdin_pairing_loop(bridge))
        app.create_task(_preflight())

    bridge.app.post_init = _post_init

    print(
        "Listening for channel messages… "
        "(enter a pairing code here to authorize a chat)",
        flush=True,
    )
    bridge.app.run_polling()


if __name__ == "__main__":
    main()
