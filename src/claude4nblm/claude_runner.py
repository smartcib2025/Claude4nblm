"""Drive Claude headlessly via the Claude Agent SDK, wired to NotebookLM.

NotebookLM is used as a retrieval (RAG) backend through the ``notebooklm-py``
**CLI** (``notebooklm ask``/``list``/``source add`` …), which Claude invokes via
the Bash tool. That version of the toolkit integrates with Claude Code as a CLI
plus a bundled skill rather than as a local MCP server, and its file/env-based
auth makes it well-suited to a headless VPS.

Each authorized chat gets its own :class:`ClaudeSDKClient` session so follow-up
messages keep conversation context. Tools are pre-approved so the bot can run
unattended.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolUseBlock,
)

from .config import Settings

# Core Claude Code tools. Bash is what lets Claude call the `notebooklm` CLI.
_CORE_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]

_DEFAULT_SYSTEM_PROMPT = (
    "You are a research and coding assistant operated from a phone over Telegram. "
    "Your NotebookLM knowledge base is your retrieval (RAG) source. Access it with "
    "the `notebooklm` command-line tool via Bash rather than guessing:\n"
    "  • `notebooklm list` — list notebooks\n"
    "  • `notebooklm use <notebook-id>` — set the active notebook\n"
    "  • `notebooklm ask \"<question>\"` — ask the active notebook (cited answers)\n"
    "  • `notebooklm source add <url|file>` — add a source\n"
    "  • `notebooklm generate audio` / `notebooklm summary` — studio artifacts\n"
    "Prefer `notebooklm ask` for grounded answers and pass through the citations it "
    "returns. Keep replies concise and readable on a small screen."
)


def build_options(settings: Settings) -> ClaudeAgentOptions:
    """Build :class:`ClaudeAgentOptions` for the NotebookLM-CLI research role."""
    system_prompt = settings.system_prompt or _DEFAULT_SYSTEM_PROMPT
    if settings.notebooklm_notebook:
        system_prompt += (
            f"\n\nDefault NotebookLM notebook to research against: "
            f"{settings.notebooklm_notebook}. Run `notebooklm use "
            f"{settings.notebooklm_notebook}` before asking if no other notebook "
            f"is specified."
        )

    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(settings.workdir),
        permission_mode="acceptEdits",
        allowed_tools=_CORE_TOOLS,
    )


class ClaudeRunner:
    """Maintains per-chat Claude sessions and streams responses."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._options = build_options(settings)
        self._clients: dict[int, ClaudeSDKClient] = {}
        # Ensure the SDK / bundled CLI can see the API key for unattended use.
        if settings.anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    async def _client_for(self, chat_id: int) -> ClaudeSDKClient:
        client = self._clients.get(chat_id)
        if client is None:
            client = ClaudeSDKClient(options=self._options)
            await client.connect()
            self._clients[chat_id] = client
        return client

    async def run(self, chat_id: int, prompt: str) -> AsyncIterator[str]:
        """Send ``prompt`` for ``chat_id`` and yield reply text as it arrives.

        Yields assistant text blocks, and lightweight progress notes when a tool
        (e.g. a NotebookLM CLI call) runs, so the user sees activity on long runs.
        """
        client = await self._client_for(chat_id)
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        yield block.text
                    elif isinstance(block, ToolUseBlock):
                        yield _progress_note(block)

    async def ping(self) -> str:
        """Run a trivial one-shot query to verify model access.

        Uses a throwaway client so it never disturbs a chat session. Returns the
        model's reply text; lets any exception (auth/provider/gateway failure)
        propagate so callers can surface the real cause.
        """
        client = ClaudeSDKClient(options=self._options)
        await client.connect()
        try:
            await client.query("Reply with the single word OK.")
            parts: list[str] = []
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            parts.append(block.text)
            return "".join(parts).strip() or "(no text returned)"
        finally:
            await client.disconnect()

    async def reset(self, chat_id: int) -> None:
        """Drop the session for ``chat_id`` so the next message starts fresh."""
        client = self._clients.pop(chat_id, None)
        if client is not None:
            await client.disconnect()

    async def shutdown(self) -> None:
        """Disconnect all sessions (call on bot shutdown)."""
        for client in list(self._clients.values()):
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
        self._clients.clear()


def _progress_note(block: ToolUseBlock) -> str:
    """Human-friendly one-liner shown while a tool runs."""
    command = ""
    if isinstance(block.input, dict):
        command = str(block.input.get("command", ""))
    if "notebooklm" in command:
        return "🔎 Querying NotebookLM…"
    return f"⚙️ Running `{block.name}`…"
