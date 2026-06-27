"""Drive Claude headlessly via the Claude Agent SDK, wired to NotebookLM.

Each authorized chat gets its own :class:`ClaudeSDKClient` session so follow-up
messages keep conversation context. The NotebookLM MCP server is launched as a
stdio subprocess and its tools are pre-approved so the bot can run unattended.
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

# NotebookLM MCP tools we auto-approve, plus core Claude Code tools.
_NOTEBOOKLM_TOOLS = [
    "mcp__notebooklm__ask_question",
    "mcp__notebooklm__list_notebooks",
    "mcp__notebooklm__search_notebooks",
    "mcp__notebooklm__add_notebook",
    "mcp__notebooklm__add_source",
    "mcp__notebooklm__generate_audio",
]
_CORE_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

_DEFAULT_SYSTEM_PROMPT = (
    "You are a research and coding assistant operated from a phone over Telegram. "
    "When the user asks about documents, sources, or knowledge that may live in "
    "NotebookLM, use the NotebookLM MCP tools (ask_question, list_notebooks, etc.) "
    "to retrieve grounded, citation-backed answers rather than guessing. Keep "
    "replies concise and readable on a small screen; include citations when the "
    "NotebookLM tools provide them."
)


def build_options(settings: Settings) -> ClaudeAgentOptions:
    """Build :class:`ClaudeAgentOptions` configured with the NotebookLM MCP server."""
    system_prompt = settings.system_prompt or _DEFAULT_SYSTEM_PROMPT
    if settings.notebooklm_notebook:
        system_prompt += (
            f"\n\nDefault NotebookLM notebook to research against: "
            f"{settings.notebooklm_notebook}."
        )

    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(settings.workdir),
        permission_mode="acceptEdits",
        allowed_tools=[*_NOTEBOOKLM_TOOLS, *_CORE_TOOLS],
        mcp_servers={
            "notebooklm": {
                "type": "stdio",
                "command": settings.notebooklm_mcp_command,
                "args": settings.notebooklm_mcp_args,
            }
        },
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
        (e.g. a NotebookLM query) is invoked, so the user sees activity on long runs.
        """
        client = await self._client_for(chat_id)
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        yield block.text
                    elif isinstance(block, ToolUseBlock):
                        yield _progress_note(block.name)

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


def _progress_note(tool_name: str) -> str:
    """Human-friendly one-liner shown while a tool runs."""
    if "notebooklm" in tool_name:
        return "🔎 Querying NotebookLM…"
    short = tool_name.split("__")[-1]
    return f"⚙️ Running `{short}`…"
