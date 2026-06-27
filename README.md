# claude4nblm

Drive **Claude Code** with your **NotebookLM** knowledge base from your **phone**, over
**Telegram**. Send a question or task to your private Telegram bot; a small Python bridge
runs it through Claude (with NotebookLM available as an MCP tool) and streams the answer
back to your chat — including 24/7 from a VPS, with no desktop left running.

## How it works

```
Phone (Telegram app)
   │  text message
   ▼
Telegram Bot API  ──►  Python bridge (python-telegram-bot)
                          │  prompt
                          ▼
                       Claude Agent SDK (ClaudeSDKClient)
                          │  mcp_servers={"notebooklm": npx notebooklm-mcp}
                          ▼
                       NotebookLM MCP server ──► Chrome ──► NotebookLM
```

- **Telegram** is the mobile interface — you chat with a bot you create via @BotFather.
- A **Python bridge** receives messages and drives Claude headlessly through the
  [Claude Agent SDK for Python](https://github.com/anthropics/claude-agent-sdk-python)
  (`claude-agent-sdk`, which bundles the Claude Code CLI).
- The bridge configures the SDK to launch the community
  [`notebooklm-mcp`](https://github.com/PleasePrompto/notebooklm-mcp) server, giving Claude
  tools such as `ask_question`, `list_notebooks`, and `add_source`.
- A **pairing-code + allowlist** flow keeps the bot private to you.

## Quickstart

```bash
# 1. Install (Python 3.10+, Node.js, and Chrome must be present)
pip install -e .

# 2. Configure
cp .env.example .env
#   then edit .env: set TELEGRAM_BOT_TOKEN and ANTHROPIC_API_KEY

# 3. One-time NotebookLM login (opens a visible Chrome; persists cookies)
npx notebooklm-mcp@latest   # run its setup_auth, log into Google, then quit

# 4. Run
python -m claude4nblm
```

Then, from your phone: open your bot in Telegram, send "hi", and you'll get a **pairing
code**. Type that code into the terminal where the bridge is running to authorize your
chat. After that, just send tasks like *"List my NotebookLM notebooks"* or
*"Summarize the key risks in my research notebook."*

Full step-by-step guides:

- 🇹🇭 **[ภาษาไทย — docs/SETUP.th.md](docs/SETUP.th.md)**
- 🇬🇧 **[English — docs/SETUP.en.md](docs/SETUP.en.md)**
- 🖥️ **[24/7 VPS deployment — docs/vps-deployment.md](docs/vps-deployment.md)**

## Configuration

All settings come from environment variables (see [`.env.example`](.env.example)):

| Variable | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather. |
| `ANTHROPIC_API_KEY` | ✅* | Anthropic API key. *Optional if the bundled Claude CLI is already logged into a subscription on this machine; required for unattended/VPS use. |
| `ALLOWED_CHAT_IDS` | — | Comma-separated chat IDs to pre-authorize (skip pairing). |
| `ALLOWLIST_PATH` | — | Where the allowlist JSON is stored (default `./state/allowlist.json`). |
| `WORKDIR` | — | Directory Claude runs in (file reads/writes). |
| `CLAUDE_SYSTEM_PROMPT` | — | Override the assistant's system prompt. |
| `NOTEBOOKLM_NOTEBOOK` | — | Default notebook to research against. |
| `NOTEBOOKLM_MCP_COMMAND` / `NOTEBOOKLM_MCP_ARGS` | — | Override how the NotebookLM MCP server is launched. |

## Commands (in Telegram)

- Any text → run it through Claude and reply.
- `/start` → help.
- `/reset` → start a fresh conversation (clears session context).
- `/allowlist` → list authorized chats (authorized chats only).

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Known limitations

NotebookLM has **no official public API**. This project relies on the community
`notebooklm-mcp` server, which automates a real Chrome session. Reliability therefore
depends on that project and on a valid, persisted Google login. Treat it as best-effort
automation, not a supported API.

## Security

`.env` and the allowlist state are git-ignored — never commit your tokens. The bot only
responds to chats on the allowlist; everyone else only ever receives a pairing code.

## License

MIT
